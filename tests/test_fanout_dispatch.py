"""Synthetic host admission, interruption, policy, and migration tests; no models."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import test_unit_fanout as coding_fixtures
import test_research_fanout as research_fixtures
from fanout_dispatch import (
    DispatchError, acknowledge, assert_drained, checkpoint, close_session,
    finish, initialize_policy, inspect, migrate, open_session, reconcile,
    record_intent, recover_session, resolve_backoff, start,
)
from recovery_decision import REQUIREMENTS
from unit_fanout import prepare, submit, retry
from research_fanout import prepare as prepare_research, record_disposition, status as research_status


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        self.fixture = coding_fixtures.UnitFanoutTests()

    def coding(self, count=15, concurrency=None):
        spec_path = self.fixture.make_spec(self.root / "inputs", count)
        if concurrency is not None:
            spec = json.loads(spec_path.read_text())
            spec["concurrency"] = concurrency
            spec_path.write_text(json.dumps(spec))
        prepare(spec_path, self.run)
        return self.run

    def research(self, count=3):
        fixture = research_fixtures.ResearchFanoutTests()
        self.run = fixture.make_fanout(self.root, count=count)
        prepare_research(self.run)
        return self.run

    def open(self, kind="coding", **changes):
        args = {"kind": kind, "host": "codex", "owner": "native-parent-1", "capacity": 12}
        args.update(changes)
        return open_session(self.run, **args)

    def complete(self, ticket):
        start(ticket["ticket_path"])
        returned, _ = self.fixture.base_return(Path(ticket["assignment_path"]))
        receipt = submit(self.run, ticket["assignment_id"], returned)
        return {"ticket_id": ticket["ticket_id"], "status": "completed", "evidence_sha256": receipt["sha256"]}

    def complete_session(self, session, partial=False):
        evidence = []
        for ticket in session["tickets"]:
            item = self.complete(ticket)
            evidence.append(item)
            if partial:
                reconcile(self.run, session["owner"], outcomes=[item])
        value = reconcile(self.run, session["owner"], outcomes=evidence)
        self.assertTrue(value["can_close"])
        return close_session(self.run, session["owner"])

    def proof_request(self, plan, action):
        evidence_root = self.root / "evidence"
        evidence_root.mkdir(exist_ok=True)

        def write(name, value):
            path = evidence_root / name
            raw = value.encode() if isinstance(value, str) else json.dumps(value, sort_keys=True).encode()
            path.write_bytes(raw)
            return {"path": path.relative_to(self.root).as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}

        quote = "I authorize the reviewed operational migration and resumption under unchanged research rules."
        request = {"schema_version": "1.0", "run_id": plan["run_id"], "action": action,
                   "binding_sha256": plan["binding_sha256"], "candidate_sha256": plan["candidate_sha256"],
                   "authorities": [{"id": "researcher", "source_kind": "researcher_instruction", "source": write("authority.md", quote),
                                    "quote": quote, "run_id": plan["run_id"], "binding_sha256": plan["binding_sha256"],
                                    "actions": ["operational_migration", "resume_dispatch"]}],
                   "restrictions": [], "evidence": {}}
        for requirement in REQUIREMENTS[action]:
            request["evidence"][requirement] = write(requirement + ".json", {
                "requirement": requirement, "status": "passed", "run_id": plan["run_id"],
                "binding_sha256": plan["binding_sha256"], "candidate_sha256": plan["candidate_sha256"]})
        return request

    def test_missing_owner_and_legacy_inspection_never_initialize_dispatch(self):
        self.coding()
        with self.assertRaisesRegex(DispatchError, "native_session_owner_required"):
            self.open(owner=None)
        self.assertFalse((self.run / "batch_checks").exists())
        (self.run / "dispatch_policy.json").unlink()
        value = self.open(owner=None)
        self.assertEqual(value["mode"], "legacy")
        self.assertEqual(value["tickets"], [])
        self.assertFalse((self.run / "batch_checks").exists())

    def test_same_owner_reopen_emits_no_tickets_and_other_owner_cannot_steal(self):
        self.coding()
        original = self.open(limit=6)
        repeated = self.open(limit=12)
        self.assertEqual(original["session_id"], repeated["session_id"])
        self.assertTrue(repeated["reused_session"])
        self.assertEqual(repeated["tickets"], [])
        with self.assertRaisesRegex(DispatchError, "dispatch_owner_exists"):
            self.open(owner="new-native-parent")

    def test_duplicate_worker_start_and_capacity_are_atomic_across_threads(self):
        self.coding(concurrency=1)
        session = self.open(limit=2)
        paths = [item["ticket_path"] for item in session["tickets"]]

        def attempt(path):
            try:
                return start(path)["status"]
            except DispatchError:
                return "refused"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, paths))
        self.assertEqual(sorted(results), ["refused", "started"])
        active = inspect(self.run)
        self.assertEqual(active["active"], 1)
        admitted = paths[results.index("started")]
        with self.assertRaisesRegex(DispatchError, "attempt_already_started"):
            start(admitted)

    def test_large_manifest_workers_never_call_parent_full_status_under_admission_lock(self):
        self.coding(count=1500)
        session = self.open(limit=6)
        with patch("fanout_dispatch._controller", side_effect=AssertionError("worker called parent status")):
            with ThreadPoolExecutor(max_workers=6) as pool:
                started = list(pool.map(lambda item: start(item["ticket_path"]), session["tickets"]))
            self.assertEqual(len(started), 6)
            ticket = session["tickets"][0]
            returned, path = self.fixture.base_return(Path(ticket["assignment_path"]))
            path.write_text(json.dumps(returned))
            self.assertEqual(finish(ticket["ticket_path"])["status"], "returned")
        self.assertEqual(inspect(self.run)["metrics"]["peak_registered_workers"], 6)

    def test_parent_full_verification_does_not_hold_the_worker_admission_lock(self):
        import fanout_dispatch
        self.coding(count=1500)
        session = self.open(limit=6)
        evidence = self.complete(session["tickets"][0])
        entered, release = threading.Event(), threading.Event()
        original = fanout_dispatch._controller

        def delayed_parent(*args, **kwargs):
            entered.set()
            if not release.wait(10):
                raise AssertionError("parent verification was not released")
            return original(*args, **kwargs)

        with patch("fanout_dispatch._controller", side_effect=delayed_parent):
            with ThreadPoolExecutor(max_workers=2) as pool:
                parent = pool.submit(reconcile, self.run, session["owner"], outcomes=[evidence])
                try:
                    self.assertTrue(entered.wait(5))
                    worker = pool.submit(start, session["tickets"][1]["ticket_path"])
                    self.assertEqual(worker.result(timeout=5)["status"], "started")
                finally:
                    release.set()
                self.assertEqual(parent.result(timeout=20)["reconciled"], 1)

    def test_return_frees_admission_but_native_finality_controls_retry_and_close(self):
        self.coding(count=3, concurrency=1)
        session = self.open(limit=2)
        first, second = session["tickets"]
        evidence = self.complete(first)
        start(second["ticket_path"])
        self.assertEqual(inspect(self.run)["active"], 1)
        value = reconcile(self.run, session["owner"])
        self.assertEqual(value["reconciled"], 0)
        with self.assertRaisesRegex(DispatchError, "dispatch_finality_unresolved"):
            close_session(self.run, session["owner"])
        with self.assertRaisesRegex(DispatchError, "must_close_before_retry"):
            assert_drained(self.run)
        value = reconcile(self.run, session["owner"], outcomes=[evidence])
        self.assertEqual(value["reconciled"], 1)
        self.assertEqual(value["active"], 1)

    def test_intent_acknowledgement_and_unknowns_never_turn_into_unused_work(self):
        self.coding(count=3)
        session = self.open()
        ticket = session["tickets"][0]
        record_intent(ticket["ticket_path"], session["owner"])
        acknowledge(ticket["ticket_path"], session["owner"], "a" * 64)
        value = reconcile(self.run, session["owner"], stop_admissions=True)
        self.assertEqual(value["unknown"], 3)
        self.assertTrue(value["admission_stopped"])
        with self.assertRaisesRegex(DispatchError, "accepted_attempt_cannot_be_unstarted"):
            reconcile(self.run, session["owner"], outcomes=[{
                "ticket_id": ticket["ticket_id"], "status": "never_started", "evidence_sha256": "b" * 64}])
        with self.assertRaisesRegex(DispatchError, "dispatch_admission_stopped"):
            start(session["tickets"][1]["ticket_path"])

    def test_positive_native_nonexecution_can_release_only_unaccepted_ticket(self):
        self.coding(count=1)
        session = self.open()
        ticket = session["tickets"][0]
        record_intent(ticket["ticket_path"], session["owner"])
        value = reconcile(self.run, session["owner"], outcomes=[{
            "ticket_id": ticket["ticket_id"], "status": "never_started", "evidence_sha256": "a" * 64}])
        self.assertTrue(value["can_close"])
        close_session(self.run, session["owner"])
        another = self.open(owner="native-parent-2")
        self.assertNotEqual(ticket["ticket_id"], another["tickets"][0]["ticket_id"])
        self.assertEqual(ticket["attempt"], another["tickets"][0]["attempt"])

    def test_partial_reconciliation_is_not_failure_and_growth_needs_explicit_checkpoint(self):
        self.coding(count=30)
        session = self.open(limit=6)
        self.complete_session(session, partial=True)
        self.assertEqual(inspect(self.run)["next_target"], 6)
        snapshot = checkpoint(self.run, session["owner"])
        self.assertEqual(snapshot["next_target"], 6)
        accepted = checkpoint(self.run, session["owner"], passed=True)
        self.assertEqual(accepted["next_target"], 7)
        checkpoint(self.run, session["owner"], passed=True)
        self.assertEqual(inspect(self.run)["next_target"], 7)
        next_session = self.open(owner="native-parent-2", limit=7)
        self.assertEqual(next_session["target"], 7)

    def test_insufficient_backlog_does_not_promote(self):
        self.coding(count=7)
        session = self.open(limit=6)
        self.complete_session(session)
        checkpoint(self.run, session["owner"], passed=True)
        self.assertEqual(inspect(self.run)["next_target"], 6)

    def test_fixed_limit_cannot_be_overridden_and_throttle_still_lowers_target(self):
        self.coding(count=12, concurrency=2)
        session = self.open(concurrency=12, limit=2)
        self.assertEqual((session["target"], session["maximum"]), (2, 2))
        evidence = [self.complete(ticket) for ticket in session["tickets"]]
        reconcile(self.run, session["owner"], outcomes=evidence, throttled=True, retry_after_seconds=0)
        close_session(self.run, session["owner"])
        checkpoint(self.run, session["owner"])
        next_session = self.open(owner="native-parent-2", concurrency=12, limit=1)
        self.assertEqual(next_session["target"], 1)

    def test_throttle_backoff_is_persisted_and_cooldown_prevents_immediate_growth(self):
        self.coding(count=30)
        session = self.open(limit=6)
        evidence = [self.complete(ticket) for ticket in session["tickets"]]
        reconcile(self.run, session["owner"], outcomes=evidence, throttled=True, retry_after_seconds=0)
        close_session(self.run, session["owner"])
        value = checkpoint(self.run, session["owner"], passed=True)
        self.assertEqual((value["next_target"], value["cooldown_checkpoints"]), (3, 2))
        for n in range(2):
            session = self.open(owner=f"next-parent-{n}", limit=3)
            self.complete_session(session)
            value = checkpoint(self.run, session["owner"], passed=True)
            self.assertEqual(value["next_target"], 3)
        session = self.open(owner="recovered-parent", limit=3)
        self.complete_session(session)
        self.assertEqual(checkpoint(self.run, session["owner"], passed=True)["next_target"], 4)

    def test_ticket_policy_and_database_view_tampering_fail_closed(self):
        self.coding()
        session = self.open(limit=1)
        path = Path(session["tickets"][0]["ticket_path"])
        original = path.read_bytes()
        altered = json.loads(original)
        altered["attempt"] = 9
        path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(DispatchError, "dispatch_ticket_changed"):
            start(path)
        path.write_bytes(original)
        policy_path = self.run / "dispatch_policy.json"
        policy = policy_path.read_bytes()
        value = json.loads(policy)
        value["maximum"] = 200
        policy_path.write_text(json.dumps(value))
        with self.assertRaisesRegex(DispatchError, "dispatch_policy_changed"):
            start(path)
        policy_path.write_bytes(policy)
        policy_path.unlink()
        with self.assertRaisesRegex(DispatchError, "dispatch_policy_missing"):
            self.open()
        with self.assertRaisesRegex(DispatchError, "dispatch_policy_missing"):
            inspect(self.run)
        policy_path.write_bytes(policy)
        with sqlite3.connect(self.run / "batch_checks/dispatch/dispatch.sqlite3") as db:
            db.execute("UPDATE sessions SET target=200")
        db.close()
        with self.assertRaisesRegex(DispatchError, "dispatch_database_view_changed"):
            inspect(self.run)

    def test_closed_history_is_archived_and_authenticated_before_the_next_session(self):
        self.coding(count=4, concurrency=1)
        first = self.open(limit=1)
        self.complete_session(first)
        second = self.open(owner="second-parent", limit=1)
        self.complete_session(second)
        database = self.run / "batch_checks/dispatch/dispatch.sqlite3"
        with sqlite3.connect(database) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM tickets").fetchone()[0], 1)
        db.close()
        segment = next((self.run / "batch_checks/dispatch/segments").glob("*.json"))
        segment.write_text("{}")
        with self.assertRaisesRegex(DispatchError, "closed_dispatch_history_changed"):
            self.open(owner="third-parent", limit=1)

    def test_invalid_open_does_not_poison_later_archive_after_an_accepted_checkpoint(self):
        self.coding(count=15)
        session = self.open(limit=6)
        self.complete_session(session)
        with self.assertRaisesRegex(DispatchError, "invalid_limit"):
            self.open(owner="next-parent", limit=0)
        checkpoint(self.run, session["owner"], passed=True)
        self.assertEqual(self.open(owner="next-parent", limit=7)["target"], 7)

    def test_confirmed_provider_wait_and_unknown_wait_block_admission_until_evidence(self):
        self.coding(count=2)
        session = self.open()
        with patch("fanout_dispatch._now", return_value="2026-09-07T12:00:00+00:00"):
            reconcile(self.run, session["owner"], throttled=True, retry_after_seconds=60)
        with patch("fanout_dispatch._now", return_value="2026-09-07T12:00:30+00:00"):
            with self.assertRaisesRegex(DispatchError, "provider_backoff_active"):
                start(session["tickets"][0]["ticket_path"])
            with self.assertRaisesRegex(DispatchError, "provider_backoff_active"):
                resolve_backoff(self.run, session["owner"], "a" * 64)
        with patch("fanout_dispatch._now", return_value="2026-09-07T12:01:01+00:00"):
            reconcile(self.run, session["owner"], throttled=True)
            with self.assertRaisesRegex(DispatchError, "provider_backoff_unknown"):
                start(session["tickets"][0]["ticket_path"])
            resolve_backoff(self.run, session["owner"], "a" * 64)
            self.assertEqual(start(session["tickets"][0]["ticket_path"])["status"], "started")

    def test_invalid_coding_return_can_reconcile_failure_then_follow_frozen_retry(self):
        self.coding(count=1)
        session = self.open()
        ticket = session["tickets"][0]
        start(ticket["ticket_path"])
        Path(ticket["return_path"]).write_text("{malformed")
        value = reconcile(self.run, session["owner"], outcomes=[{
            "ticket_id": ticket["ticket_id"], "status": "completed", "evidence_sha256": "a" * 64}])
        self.assertTrue(value["can_close"])
        close_session(self.run, session["owner"])
        linked = retry(self.run, ticket["assignment_id"])
        self.assertEqual(linked["attempt"], 2)
        self.assertEqual(Path(linked["archived_return_path"]).read_text(), "{malformed")

    def test_research_attempt_is_recorded_at_start_and_disposition_can_close_failure(self):
        self.research()
        session = self.open(kind="research")
        self.assertEqual(research_status(self.run)["attempt_counts"]["attempted"], 0)
        ticket = session["tickets"][0]
        start(ticket["ticket_path"])
        self.assertEqual(research_status(self.run)["attempt_counts"]["attempted"], 1)
        research_fixtures.ResearchFanoutTests.write_return(Path(ticket["return_path"]), ticket["assignment_id"], ticket["attempt"], complete=False)
        record_disposition(self.run, assignment_id=ticket["assignment_id"], attempt=1, terminal="failed", reason="native worker ended with partial output")
        evidence = [{"ticket_id": ticket["ticket_id"], "status": "completed", "evidence_sha256": "a" * 64}]
        evidence.extend({"ticket_id": item["ticket_id"], "status": "never_started", "evidence_sha256": "b" * 64} for item in session["tickets"][1:])
        self.assertTrue(reconcile(self.run, session["owner"], outcomes=evidence)["can_close"])
        close_session(self.run, session["owner"])
        next_session = self.open(kind="research", owner="parent-2")
        retried = next(item for item in next_session["tickets"] if item["assignment_id"] == ticket["assignment_id"])
        self.assertEqual(retried["attempt"], 2)
        self.assertNotEqual(retried["return_path"], ticket["return_path"])

    def test_completed_metrics_are_stable_operational_registration_estimates(self):
        self.coding(count=1)
        session = self.open()
        self.complete_session(session)
        first = checkpoint(self.run, session["owner"])
        second = checkpoint(self.run, session["owner"])
        self.assertEqual(first["metrics"], second["metrics"])
        self.assertEqual(first["metrics"]["peak_registered_workers"], 1)
        self.assertGreater(first["metrics"]["registered_worker_seconds"], 0)
        self.assertIn("not direct model", first["metrics"]["activity_basis"])
        self.assertNotIn("label", json.dumps(first))

    def test_migration_is_read_only_until_bound_approval_and_remains_paused(self):
        self.coding(count=2)
        (self.run / "dispatch_policy.json").unlink()
        before = {path.relative_to(self.run).as_posix(): path.read_bytes() for path in self.run.rglob("*") if path.is_file()}
        plan = migrate(self.run, kind="coding", host="codex", capacity=12)
        self.assertFalse((self.run / "batch_checks").exists())
        request = self.proof_request(plan, "operational_migration")
        changed = dict(request, candidate_sha256="0" * 64)
        with self.assertRaisesRegex(DispatchError, "migration_request_binding_mismatch"):
            migrate(self.run, kind="coding", host="codex", capacity=12, request=changed, request_root=self.root, dry_run=False)
        value = migrate(self.run, kind="coding", host="codex", capacity=12, request=request, request_root=self.root, dry_run=False)
        self.assertEqual(value["state"], "paused")
        for relative, raw in before.items():
            self.assertEqual((self.run / relative).read_bytes(), raw)
        with self.assertRaisesRegex(DispatchError, "reviewed_recovery_request_required"):
            self.open()
        resume = self.proof_request(plan, "resume_dispatch")
        self.assertEqual(self.open(resume_request=resume, request_root=self.root)["state"], "active")

    def test_migration_resume_rejects_added_history_files(self):
        self.coding(count=1)
        (self.run / "dispatch_policy.json").unlink()
        plan = migrate(self.run, kind="coding", host="codex", capacity=12)
        migrate(self.run, kind="coding", host="codex", capacity=12, request=self.proof_request(plan, "operational_migration"), request_root=self.root, dry_run=False)
        (self.run / "unexpected-old-worker-output.json").write_text("{}")
        with self.assertRaisesRegex(DispatchError, "migration_history_changed"):
            self.open(resume_request=self.proof_request(plan, "resume_dispatch"), request_root=self.root)

    def test_owner_recovery_requires_finality_and_exact_resume_evidence(self):
        self.coding(count=2)
        session = self.open(limit=1)
        plan = recover_session(self.run, expected_owner=session["owner"], owner="new-parent")
        request = self.proof_request(plan, "resume_dispatch")
        with self.assertRaisesRegex(DispatchError, "dispatch_finality_unresolved"):
            recover_session(self.run, expected_owner=session["owner"], owner="new-parent", request=request, request_root=self.root, dry_run=False)
        evidence = self.complete(session["tickets"][0])
        reconcile(self.run, session["owner"], outcomes=[evidence])
        refreshed = recover_session(self.run, expected_owner=session["owner"], owner="new-parent")
        with self.assertRaisesRegex(DispatchError, "migration_request_binding_mismatch"):
            recover_session(self.run, expected_owner=session["owner"], owner="new-parent", request=request, request_root=self.root, dry_run=False)
        recovered = recover_session(self.run, expected_owner=session["owner"], owner="new-parent", request=self.proof_request(refreshed, "resume_dispatch"), request_root=self.root, dry_run=False)
        self.assertEqual(recovered["status"], "owner_recovered")
        self.assertEqual(self.open(owner="new-parent")["owner"], "new-parent")

    def test_cli_native_evidence_uses_stdin_and_closed_errors_have_reason_codes(self):
        self.coding(count=1)
        session = self.open()
        evidence = self.complete(session["tickets"][0])
        script = coding_fixtures.ROOT / "scripts/fanout_dispatch.py"
        result = subprocess.run([sys.executable, "-B", str(script), "reconcile", "--run-dir", str(self.run), "--owner", session["owner"], "--host-evidence", "-"],
                                input=json.dumps([evidence]), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["can_close"])
        result = subprocess.run([sys.executable, "-B", str(script), "intent", "--ticket", session["tickets"][0]["ticket_path"], "--owner", "wrong-owner"], text=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout)["reason_code"], "dispatch_owner_mismatch")


if __name__ == "__main__":
    unittest.main()
