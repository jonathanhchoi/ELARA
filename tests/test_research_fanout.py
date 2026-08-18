"""Tests for the research fan-out controller (scripts/research_fanout.py).

The controller is provider-neutral: it never spawns an agent. These tests check the contract the
kit's saved Claude workflow and Codex sub-agent adapter rely on — a sealed manifest with one unique
return path per brief, a pending list derived from the files on disk, launches recorded so that
attempts are bounded, and fail-closed drift detection.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "scripts"))

from research_fanout import FanoutError, prepare, status  # noqa: E402


class ResearchFanoutTests(unittest.TestCase):
    def make_fanout(self, root: Path, count: int = 3, max_attempts: int = 2) -> Path:
        fanout = root / "fanout" / "queries_w1"
        (fanout / "briefs").mkdir(parents=True)
        assignments = []
        for index in range(count):
            brief = fanout / "briefs" / f"q{index:02d}.md"
            brief.write_text(f"# Brief q{index:02d}\nRun exactly one query.\n", encoding="utf-8")
            assignments.append({"assignment_id": f"q{index:02d}", "brief": f"briefs/q{index:02d}.md"})
        (fanout / "spec.json").write_text(
            json.dumps(
                {
                    "contract_version": "1.0",
                    "fanout_id": "fixture-queries-w1",
                    "kind": "search_query",
                    "time_box_minutes": 12,
                    "max_attempts": max_attempts,
                    "assignments": assignments,
                }
            ),
            encoding="utf-8",
        )
        return fanout

    @staticmethod
    def write_return(path: Path, assignment_id: str, *, complete: bool) -> None:
        path.write_text(
            json.dumps({"assignment_id": assignment_id, "complete": complete, "result": {"hits": []}}),
            encoding="utf-8",
        )

    def test_prepare_seals_one_unique_return_path_per_brief(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp))
            manifest = prepare(fanout)
            self.assertEqual(manifest["expected_assignments"], 3)
            rows = manifest["assignments"]
            self.assertEqual(len({row["return_path"] for row in rows}), 3)
            for row in rows:
                self.assertTrue(Path(row["return_path"]).resolve().is_relative_to((fanout / "returns").resolve()))
                self.assertEqual(len(row["brief_sha256"]), 64)
            self.assertTrue((fanout / "manifest.csv").is_file())
            self.assertTrue((fanout / "seal.json").is_file())
            with self.assertRaises(FanoutError):
                prepare(fanout)  # immutable once sealed

    def test_prepare_rejects_duplicates_missing_briefs_and_briefs_outside_the_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp))
            spec_path = fanout / "spec.json"
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["assignments"].append({"assignment_id": "q00", "brief": "briefs/q00.md"})
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaisesRegex(FanoutError, "duplicate assignment_id"):
                prepare(fanout)
            spec["assignments"][-1] = {"assignment_id": "q99", "brief": "briefs/q99.md"}
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaisesRegex(FanoutError, "does not exist"):
                prepare(fanout)
            outside = fanout.parent / "outside.md"
            outside.write_text("not a brief in briefs/\n", encoding="utf-8")
            spec["assignments"][-1] = {"assignment_id": "q99", "brief": "../outside.md"}
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaisesRegex(FanoutError, "must live under briefs/"):
                prepare(fanout)
            self.assertFalse((fanout / "manifest.json").exists())

    def test_status_derives_pending_from_disk_records_launches_and_bounds_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp), max_attempts=2)
            prepare(fanout)
            first = status(fanout, include_pending=True, record_launch=True)
            self.assertEqual((first["expected"], first["missing"], first["pending"]), (3, 3, 3))
            self.assertEqual(first["launches_recorded"], 3)
            self.assertEqual([item["attempts_so_far"] for item in first["pending_assignments"]], [1, 1, 1])
            by_id = {item["assignment_id"]: Path(item["return_path"]) for item in first["pending_assignments"]}
            self.write_return(by_id["q00"], "q00", complete=True)
            self.write_return(by_id["q01"], "q01", complete=False)  # partial: still pending
            by_id["q02"].write_text(json.dumps({"assignment_id": "wrong", "complete": True}), encoding="utf-8")
            second = status(fanout, include_pending=True, record_launch=True)
            self.assertEqual(second["complete"], 1)
            self.assertEqual(second["incomplete"], 1)
            self.assertEqual(second["invalid"], 1)
            self.assertEqual(sorted(item["assignment_id"] for item in second["pending_assignments"]), ["q01", "q02"])
            self.assertEqual(second["invalid_returns"][0]["assignment_id"], "q02")
            # Both remaining assignments have now been launched twice: exhausted, not pending.
            third = status(fanout, include_pending=True)
            self.assertEqual(third["pending"], 0)
            self.assertEqual(sorted(third["exhausted_assignments"]), ["q01", "q02"])
            # The parent may deliberately ask for them back, and that is visible in the counts.
            fourth = status(fanout, include_pending=True, include_exhausted=True)
            self.assertEqual(fourth["pending"], 2)
            self.assertEqual(fourth["exhausted"], 0)
            self.assertEqual({item["attempts_so_far"] for item in fourth["pending_assignments"]}, {2})
            rows = [json.loads(line) for line in (fanout / "attempts.jsonl").read_text(encoding="utf-8").splitlines() if line]
            self.assertEqual(len(rows), 5)
            self.assertEqual({row["assignment_id"] for row in rows}, {"q00", "q01", "q02"})

    def test_status_limit_and_stray_files_and_no_findings_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp), count=5)
            prepare(fanout)
            limited = status(fanout, include_pending=True, record_launch=True, limit=2)
            self.assertEqual(limited["pending"], 2)
            self.assertEqual(limited["launches_recorded"], 2)
            self.assertEqual(len((fanout / "attempts.jsonl").read_text(encoding="utf-8").splitlines()), 2)
            (fanout / "returns" / "notes.txt").write_text("stray\n", encoding="utf-8")
            report = status(fanout)
            self.assertEqual(len(report["stray_files"]), 1)
            # A finding written by a worker never appears in status output.
            self.write_return(fanout / "returns" / "q00.json", "q00", complete=True)
            text = json.dumps(status(fanout, include_pending=True))
            self.assertNotIn("hits", text)

    def test_status_fails_closed_on_manifest_brief_or_spec_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp))
            prepare(fanout)
            brief = fanout / "briefs" / "q01.md"
            brief.write_text(brief.read_text(encoding="utf-8") + "changed after sealing\n", encoding="utf-8")
            with self.assertRaisesRegex(FanoutError, "changed after prepare"):
                status(fanout)
            fanout2 = self.make_fanout(Path(tmp) / "second")
            prepare(fanout2)
            manifest_path = fanout2 / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["max_attempts"] = 99
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(FanoutError, "changed after sealing"):
                status(fanout2)

    def test_cli_prints_json_and_returns_nonzero_on_contract_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp))
            script = ROOT / "scripts" / "research_fanout.py"
            prepared = subprocess.run(
                [sys.executable, str(script), "prepare", "--fanout-dir", str(fanout)],
                text=True, capture_output=True, timeout=120, check=False,
            )
            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            self.assertEqual(json.loads(prepared.stdout)["expected"], 3)
            listed = subprocess.run(
                [sys.executable, str(script), "status", "--fanout-dir", str(fanout), "--include-pending", "--record-launch", "--limit", "1"],
                text=True, capture_output=True, timeout=120, check=False,
            )
            self.assertEqual(listed.returncode, 0, listed.stderr)
            payload = json.loads(listed.stdout)
            self.assertEqual(payload["pending"], 1)
            self.assertEqual(payload["pending_assignments"][0]["assignment_id"], "q00")
            broken = subprocess.run(
                [sys.executable, str(script), "status", "--fanout-dir", str(Path(tmp) / "nowhere")],
                text=True, capture_output=True, timeout=120, check=False,
            )
            self.assertEqual(broken.returncode, 1)
            self.assertIn("ERROR:", broken.stderr)


if __name__ == "__main__":
    unittest.main()
