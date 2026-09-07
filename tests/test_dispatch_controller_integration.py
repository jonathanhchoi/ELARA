"""Exercise dispatch guards through the real coding and research controllers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "scripts"))

import fanout_dispatch as dispatch
import research_fanout as research
import unit_fanout as coding
import test_unit_fanout as coding_fixtures
import test_research_fanout as research_fixtures


class DispatchControllerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def coding_run(self, count=3):
        fixture = coding_fixtures.UnitFanoutTests()
        run = self.root / "coding"
        manifest = coding.prepare(fixture.make_spec(self.root / "input", count), run)
        return run, manifest, fixture

    def test_new_policy_is_additive_and_legacy_reads_do_not_create_it(self):
        run, manifest, _ = self.coding_run()
        self.assertTrue((run / "dispatch_policy.json").is_file())
        original = (run / "run_seal.json").read_bytes()
        self.assertEqual(coding.verify_run_integrity(run), manifest)
        (run / "dispatch_policy.json").unlink()  # An explicitly constructed pre-2.9 fixture.
        coding.status(run, include_pending=True)
        self.assertFalse((run / "dispatch_policy.json").exists())
        self.assertEqual((run / "run_seal.json").read_bytes(), original)

    def test_active_dispatch_requires_start_and_submit_records_completion(self):
        run, manifest, fixture = self.coding_run(2)
        before = {name: (run / name).read_bytes() for name in ("run_manifest.json", "run_seal.json")}
        session = dispatch.open_session(run, kind="coding", owner="fixture-parent", host="claude", capacity=2)
        row = manifest["assignments"][0]
        returned, output = fixture.base_return(Path(row["assignment_path"]))
        with self.assertRaises(coding.FanoutError):
            coding.submit(run, row["assignment_id"], returned)
        self.assertFalse(output.exists())
        ticket = Path(session["tickets"][0]["ticket_path"])
        dispatch.start(ticket)
        receipt = coding.submit(run, row["assignment_id"], returned)
        self.assertEqual(receipt["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertEqual(dispatch.finish(ticket)["status"], "returned")
        with self.assertRaises(ValueError):
            dispatch.start(ticket)
        with self.assertRaises(coding.FanoutError):
            coding.submit(run, row["assignment_id"], returned)
        self.assertEqual(coding.status(run)["terminal"], 1)
        for name, raw in before.items():
            self.assertEqual((run / name).read_bytes(), raw)

    def test_retry_cannot_reseal_manifest_while_siblings_are_active(self):
        run, manifest, fixture = self.coding_run(2)
        session = dispatch.open_session(run, kind="coding", owner="fixture-parent", host="claude", capacity=2)
        for ticket in session["tickets"]:
            dispatch.start(Path(ticket["ticket_path"]))
        row = manifest["assignments"][0]
        returned, _ = fixture.base_return(Path(row["assignment_path"]))
        returned.update(status="worker_error", result=None, error="fixture terminal failure")
        coding.submit(run, row["assignment_id"], returned)
        before = (run / "run_manifest.json").read_bytes()
        with self.assertRaises(coding.FanoutError):
            coding.retry(run, row["assignment_id"])
        self.assertEqual((run / "run_manifest.json").read_bytes(), before)
        self.assertEqual(len(list((run / "assignments").glob("*.json"))), 2)

    def test_research_records_only_started_attempts_and_blocks_bulk_launches(self):
        fixture = research_fixtures.ResearchFanoutTests()
        run = fixture.make_fanout(self.root, count=8)
        research.prepare(run)
        session = dispatch.open_session(run, kind="research", owner="fixture-parent", host="claude", capacity=3)
        self.assertEqual(research.status(run)["attempt_counts"]["attempted"], 0)
        with self.assertRaises(coding.FanoutError):
            research.status(run, include_pending=True, record_launch=True)
        item = session["tickets"][0]
        ticket = Path(item["ticket_path"])
        dispatch.start(ticket)
        current = research.status(run)
        self.assertEqual(current["attempt_counts"]["attempted"], 1)
        self.assertEqual(current["attempt_counts"]["outstanding"], 1)
        manifest = research.verify_integrity(run)
        row = next(row for row in manifest["assignments"]
                   if row["assignment_id"] == item["assignment_id"] and row["attempt"] == item["attempt"])
        fixture.write_return(Path(row["return_path"]), item["assignment_id"], item["attempt"], complete=True)
        dispatch.finish(ticket)
        current = research.status(run)
        self.assertEqual(current["complete"], 1)
        self.assertEqual(current["attempt_counts"]["attempted"], 1)
        self.assertEqual(len((run / "attempts.jsonl").read_text().splitlines()), 1)

    def test_explicit_fixed_ceiling_is_recorded_without_changing_assignment_schema(self):
        fixture = coding_fixtures.UnitFanoutTests()
        spec_path = fixture.make_spec(self.root / "input", 2)
        spec = json.loads(spec_path.read_text())
        spec["concurrency"] = 2
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        run = self.root / "coding"
        manifest = coding.prepare(spec_path, run)
        session = dispatch.open_session(run, kind="coding", owner="fixture-parent", host="claude", capacity=12)
        self.assertEqual(session["target"], 2)
        assignment = json.loads(Path(manifest["assignments"][0]["assignment_path"]).read_text())
        self.assertNotIn("concurrency", assignment)
        self.assertNotIn("dispatch", assignment)


if __name__ == "__main__":
    unittest.main()
