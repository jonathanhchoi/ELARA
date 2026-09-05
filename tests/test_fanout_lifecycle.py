from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_unit_fanout as fixtures
from fanout_lifecycle import Journal, LifecycleError, VerificationTransaction, digest, identity
from unit_fanout import prepare, submit, status, retry, merge, FanoutError

H = "a" * 64
J = "b" * 64


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.journal = Journal(self.root / "journal")
        self.journal.initialize(scientific_sha256=H, operational_sha256=J, concurrency=3)

    def finish(self, assignment, outcome="succeeded"):
        self.journal.advance(assignment, "returned", evidence_sha256=H)
        self.journal.advance(assignment, "validated", evidence_sha256=J, outcome=outcome)
        self.journal.advance(assignment, "reconciled", evidence_sha256=J, outcome=outcome)

    def test_partial_wave_is_unknown_not_dispatchable_in_fresh_session(self):
        with self.journal.ownership():
            self.journal.intent("a1", "u1", 1)
            self.journal.intent("a2", "u2", 1)
            self.journal.advance("a2", "acknowledged", evidence_sha256=H)
            self.journal.intent("a3", "u3", 1)
            self.finish("a3")
        fresh = Journal(self.root / "journal")
        self.assertEqual(fresh.inspect()["unknown_finality"], 2)
        self.assertEqual(fresh.inspect()["next_action"], "resolve_unknown_finality")
        with fresh.ownership(), self.assertRaises(LifecycleError):
            fresh.intent("a1", "u1", 1)

    def test_retries_require_reconciled_failure_and_controller_receipt(self):
        with self.journal.ownership():
            self.journal.intent("a1", "u", 1)
            with self.assertRaises(LifecycleError):
                self.journal.intent("a2", "u", 2, retry_receipt_sha256=H)
            self.finish("a1", "retryable")
            with self.assertRaises(LifecycleError):
                self.journal.intent("a2", "u", 2)
            self.journal.intent("a2", "u", 2, retry_receipt_sha256=H)
            self.finish("a2", "exhausted")
            with self.assertRaises(LifecycleError):
                self.journal.intent("a3", "u", 3, retry_receipt_sha256=H)
        self.assertEqual(self.journal.inspect()["reconciled_attempts"]["exhausted"], 1)

    def test_concurrency_and_double_owner_are_blocked(self):
        with self.journal.ownership():
            with self.assertRaises(LifecycleError), self.journal.ownership():
                pass
            for n in range(3):
                self.journal.intent(f"a{n}", f"u{n}", 1)
            with self.assertRaises(LifecycleError):
                self.journal.intent("a4", "u4", 1)

    def test_owner_recovery_checks_creation_identity_not_pid_alone(self):
        token = identity(os.getpid())
        with self.journal.connection(write=True) as db:
            db.execute("INSERT INTO owner VALUES (1,?)", (token,))
            self.journal._append(db, {"kind": "owner_acquired", "identity": token})
        with self.assertRaises(LifecycleError):
            self.journal.recover_owner(expected_identity=token, review_sha256=H)
        with patch("fanout_lifecycle.identity", return_value="reused-pid-new-creation"):
            self.journal.recover_owner(expected_identity=token, review_sha256=H)
        self.assertIsNone(self.journal.inspect()["owner_identity"])

    def test_invalid_transition_and_conflicting_evidence(self):
        with self.journal.ownership():
            self.journal.intent("a", "u", 1)
            with self.assertRaises(LifecycleError):
                self.journal.advance("a", "reconciled", evidence_sha256=H, outcome="succeeded")
            self.journal.advance("a", "acknowledged", evidence_sha256=H)
            self.journal.advance("a", "acknowledged", evidence_sha256=H)
            with self.assertRaises(LifecycleError):
                self.journal.advance("a", "acknowledged", evidence_sha256=J)

    def test_identical_failures_do_not_repeat_a_launch(self):
        with self.journal.ownership():
            for _ in range(2):
                self.journal.progress("stopped", failure_class="infrastructure", fingerprint=H)
        self.assertEqual(self.journal.inspect()["next_action"], "diagnose_new_evidence")
        self.assertEqual(self.journal.inspect()["acknowledged_launches"], 0)

    def test_checkpoint_is_immutable_and_inspection_read_only(self):
        checkpoint = self.root / "checkpoint.json"
        self.journal.checkpoint(checkpoint)
        first = digest(self.journal.path)
        self.journal.inspect()
        self.assertEqual(first, digest(self.journal.path))
        self.journal.checkpoint(checkpoint)
        with self.journal.ownership():
            self.journal.progress("verifying")
        with self.assertRaises(LifecycleError):
            self.journal.checkpoint(checkpoint)

    def test_derived_table_drift_blocks_mutation_as_well_as_inspection(self):
        with self.journal.ownership():
            self.journal.intent("first", "unit", 1)
        with sqlite3.connect(self.journal.path) as db:
            db.execute("DELETE FROM launches")
        db.close()
        with self.assertRaises(LifecycleError), self.journal.ownership():
            self.journal.intent("duplicate", "unit", 1)
        with self.assertRaises(LifecycleError):
            self.journal.inspect()

    def test_settings_and_owner_drift_fail_closed(self):
        with sqlite3.connect(self.journal.path) as db:
            db.execute("UPDATE settings SET value='200' WHERE key='concurrency'")
        db.close()
        with self.assertRaises(LifecycleError), self.journal.ownership():
            pass

    def test_real_process_crashes_and_fresh_process_recovery(self):
        fixture = fixtures.UnitFanoutTests()
        stages = ("intent", "acknowledged", "submitted", "returned", "validated", "reconciled")
        for stage in stages:
            with self.subTest(stage=stage):
                folder = self.root / stage
                run = folder / "run"
                manifest = prepare(fixture.make_spec(folder / "input", 1), run)
                row = manifest["assignments"][0]
                response, output = fixture.base_return(Path(row["assignment_path"]))
                journal = Journal(folder / "journal")
                journal.initialize(scientific_sha256=H, operational_sha256=J, concurrency=3)
                code = '''import json,os,sys
from pathlib import Path
from fanout_lifecycle import Journal,digest
from unit_fanout import submit
j=Journal(sys.argv[1]); run=Path(sys.argv[2]); stage=sys.argv[3]
response=json.loads(sys.argv[4]); assignment=response['assignment_id']
with j.ownership():
 j.intent(assignment,response['unit_id'],1)
 if stage=='intent': os._exit(23)
 j.advance(assignment,'acknowledged',evidence_sha256='a'*64)
 if stage=='acknowledged': os._exit(23)
 receipt=submit(run,assignment,response)
 if stage=='submitted': os._exit(23)
 h=receipt['sha256']
 j.advance(assignment,'returned',evidence_sha256=h)
 if stage=='returned': os._exit(23)
 j.advance(assignment,'validated',evidence_sha256=h,outcome='succeeded')
 if stage=='validated': os._exit(23)
 j.advance(assignment,'reconciled',evidence_sha256=h,outcome='succeeded')
 os._exit(23)
'''
                env = dict(os.environ, PYTHONPATH=str(fixtures.ROOT / "scripts"))
                child = subprocess.run([sys.executable, "-c", code, str(journal.directory), str(run), stage,
                                        json.dumps(response)], env=env, capture_output=True, text=True)
                self.assertEqual(child.returncode, 23, child.stderr)
                # The inspection itself is a fresh Python process, not another object.
                inspected = subprocess.run([sys.executable, str(fixtures.ROOT / "scripts/fanout_lifecycle.py"),
                    "inspect", "--directory", str(journal.directory)], capture_output=True, text=True)
                self.assertEqual(inspected.returncode, 0, inspected.stdout)
                saved = json.loads(inspected.stdout)
                self.assertEqual(saved["next_action"], "review_owner")
                journal.recover_owner(expected_identity=saved["owner_identity"], review_sha256=H)
                if stage in ("intent", "acknowledged"):
                    self.assertFalse(output.exists())
                    self.assertEqual(journal.inspect()["next_action"], "resolve_unknown_finality")
                else:
                    with journal.ownership():
                        phase = next(iter(journal.inspect()["launch_states"]))
                        if phase in ("intent", "acknowledged"):
                            journal.advance(row["assignment_id"], "returned", evidence_sha256=digest(output))
                            phase = "returned"
                        if phase == "returned":
                            journal.advance(row["assignment_id"], "validated", evidence_sha256=digest(output), outcome="succeeded")
                            phase = "validated"
                        if phase == "validated":
                            journal.advance(row["assignment_id"], "reconciled", evidence_sha256=digest(output), outcome="succeeded")
                    self.assertEqual(status(run)["terminal"], 1)
                    journal.checkpoint(folder / "checkpoint.json")

    def test_verification_reuses_proof_not_unchecked_bytes(self):
        file = self.root / "frozen.txt"
        file.write_text("same")
        transaction = VerificationTransaction(self.root, {"frozen.txt": digest(file)})
        calls = []
        transaction.verify(lambda: calls.append(1))
        transaction.verify(lambda: calls.append(2))
        self.assertEqual(calls, [1])
        file.write_text("drift")
        with self.assertRaises(LifecycleError):
            transaction.verify(lambda: calls.append(3))

    def test_real_controller_fake_host_complete_and_interrupted_multiwave(self):
        fixture = fixtures.UnitFanoutTests()
        run = self.root / "run"
        manifest = prepare(fixture.make_spec(self.root / "input", 12), run)
        for offset in range(0, 12, 3):
            # A new parent process object reconstructs from disk every wave.
            self.journal = Journal(self.root / "journal")
            with self.journal.ownership():
                for row in manifest["assignments"][offset:offset + 3]:
                    assignment = row["assignment_id"]
                    self.journal.intent(assignment, row["unit_id"], row["attempt"])
                    self.journal.advance(assignment, "acknowledged", evidence_sha256=H)
                    returned, output = fixture.base_return(Path(row["assignment_path"]))
                    submit(run, assignment, returned)
                    # Simulate crash after strict submit but before journal return event.
                    with self.assertRaises(FanoutError):
                        submit(run, assignment, returned)
                    self.journal.advance(assignment, "returned", evidence_sha256=digest(output))
                    self.journal.advance(assignment, "validated", evidence_sha256=digest(output), outcome="succeeded")
                    self.journal.advance(assignment, "reconciled", evidence_sha256=digest(output), outcome="succeeded")
            self.journal.checkpoint(self.root / f"wave-{offset}.json")
        self.assertEqual(status(run)["terminal"], 12)
        self.assertEqual(self.journal.inspect()["reconciled_attempts"]["succeeded"], 12)
        merge(run, self.root / "merged.jsonl")


if __name__ == "__main__":
    unittest.main()
