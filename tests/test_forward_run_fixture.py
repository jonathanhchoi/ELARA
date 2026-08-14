"""Replay test for the checked-in Claude forward-run fixture.

tests/tmp/claude_forward_run_v002 was produced on 2026-08-04 by running the saved
`/elr-observation-fanout` dynamic workflow (discovery agent, one worker, verifier)
against `tests/fixtures/one_unit_fanout/spec.json` under the current sealed
controller. This test replays controller verification on the archived run so the
"fixture-tested" claim stays mechanically checked: if the controller's manifest,
seal, or return contract changes incompatibly, this test fails instead of the
claim silently going stale (as happened to the retired v001 fixture run).
"""

import importlib.util
import json
import unittest
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RUN = KIT_ROOT / "tests" / "tmp" / "claude_forward_run_v002"


def _load_unit_fanout():
    module_path = KIT_ROOT / "scripts" / "unit_fanout.py"
    spec = importlib.util.spec_from_file_location("unit_fanout_fixture_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ForwardRunFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not FIXTURE_RUN.exists():
            raise unittest.SkipTest("forward-run fixture not present in this checkout")
        cls.unit_fanout = _load_unit_fanout()

    def test_fixture_run_replays_under_current_controller(self):
        report = self.unit_fanout.status(FIXTURE_RUN)
        self.assertEqual(report["expected"], 1)
        self.assertEqual(report["terminal"], 1)
        self.assertEqual(report["invalid"], 0)
        self.assertEqual(report["pending"], 0)
        self.assertEqual(report["seal"], "verified")
        self.assertEqual(report["terminal_status_counts"], {"succeeded": 1})

    def test_fixture_return_carries_verified_frozen_hashes(self):
        return_path = FIXTURE_RUN / "worker_returns" / "fixture-alpha-attempt001.json"
        record = json.loads(return_path.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "succeeded")
        self.assertTrue(record["provenance"]["frozen_input_hashes_verified"])
        for frozen in record["provenance"]["frozen_inputs"]:
            self.assertEqual(frozen["sha256_expected"], frozen["sha256_observed"])

    def test_fixture_merge_receipt_matches_output(self):
        receipt = json.loads((FIXTURE_RUN / "merge_receipt.json").read_text(encoding="utf-8"))
        output = FIXTURE_RUN / "merged_v001.jsonl"
        self.assertTrue(output.exists())
        self.assertEqual(
            receipt["output_sha256"], self.unit_fanout.sha256_file(output)
        )


if __name__ == "__main__":
    unittest.main()
