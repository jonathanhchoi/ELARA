"""Tests for the research fan-out controller (scripts/research_fanout.py).

The controller is provider-neutral: it never spawns an agent. These tests check the contract the
kit's saved Claude workflow and Codex sub-agent adapter rely on — a sealed manifest with one unique
return path per allowed attempt, a pending list derived from the files on disk, launches recorded so
that attempts are bounded, and fail-closed drift detection.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "scripts"))

from research_fanout import FanoutError, prepare, record_disposition, status  # noqa: E402


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
    def write_return(path: Path, assignment_id: str, attempt: int, *, complete: bool) -> None:
        path.write_text(
            json.dumps(
                {"assignment_id": assignment_id, "attempt": attempt, "complete": complete, "result": {"hits": []}}
            ),
            encoding="utf-8",
        )

    def test_prepare_seals_one_unique_return_path_per_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp))
            manifest = prepare(fanout)
            self.assertEqual(manifest["expected_assignments"], 3)
            self.assertEqual(manifest["expected_attempts"], 6)
            rows = manifest["assignments"]
            self.assertEqual(len(rows), 6)
            self.assertEqual(len({row["return_path"] for row in rows}), 6)
            self.assertEqual(
                {(row["assignment_id"], row["attempt"]) for row in rows},
                {(f"q{index:02d}", attempt) for index in range(3) for attempt in (1, 2)},
            )
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
            self.assertEqual({item["attempt"] for item in first["pending_assignments"]}, {1})
            by_id = {item["assignment_id"]: Path(item["return_path"]) for item in first["pending_assignments"]}
            self.write_return(by_id["q00"], "q00", 1, complete=True)
            self.write_return(by_id["q01"], "q01", 1, complete=False)  # partial: still pending
            by_id["q02"].write_text(
                json.dumps({"assignment_id": "wrong", "attempt": 1, "complete": True}), encoding="utf-8"
            )
            second = status(fanout, include_pending=True, record_launch=True)
            self.assertEqual(second["complete"], 1)
            self.assertEqual(second["incomplete"], 1)
            self.assertEqual(second["invalid"], 1)
            self.assertEqual(second["pending"], 0)
            self.assertEqual(second["launches_recorded"], 0)
            self.assertEqual(second["invalid_returns"][0]["assignment_id"], "q02")
            record_disposition(
                fanout,
                assignment_id="q01",
                attempt=1,
                terminal="failed",
                reason="worker stopped with an incomplete return",
            )
            record_disposition(
                fanout,
                assignment_id="q02",
                attempt=1,
                terminal="unusable",
                reason="assignment identity failed operational validation",
            )
            retry_status = status(fanout, include_pending=True, record_launch=True)
            self.assertEqual(
                sorted(item["assignment_id"] for item in retry_status["pending_assignments"]), ["q01", "q02"]
            )
            self.assertEqual({item["attempt"] for item in retry_status["pending_assignments"]}, {2})
            self.assertTrue(
                all(
                    Path(item["return_path"]) != by_id[item["assignment_id"]]
                    for item in retry_status["pending_assignments"]
                )
            )
            # Both remaining assignments have now been launched twice: exhausted, not pending.
            third = status(fanout, include_pending=True)
            self.assertEqual(third["pending"], 0)
            self.assertEqual(sorted(third["exhausted_assignments"]), ["q01", "q02"])
            # Exhausted attempts remain immutable; asking for details does not reopen a path.
            fourth = status(fanout, include_pending=True, include_exhausted=True)
            self.assertEqual(fourth["pending"], 0)
            self.assertEqual(fourth["exhausted"], 2)
            self.assertEqual(len(fourth["exhausted_attempts"]), 2)
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
            first_path = Path(limited["pending_assignments"][0]["return_path"])
            self.write_return(first_path, "q00", 1, complete=True)
            text = json.dumps(status(fanout, include_pending=True))
            self.assertNotIn("hits", text)

    def test_stage_schema_rejection_preserves_raw_attempt_and_routes_retry_to_new_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp), count=1, max_attempts=2)
            prepare(fanout)
            first = status(fanout, include_pending=True, record_launch=True)["pending_assignments"][0]
            first_path = Path(first["return_path"])
            self.write_return(first_path, "q00", 1, complete=True)
            first_bytes = first_path.read_bytes()
            self.assertEqual(status(fanout)["complete"], 1)

            disposition = record_disposition(
                fanout,
                assignment_id="q00",
                attempt=1,
                terminal="unusable",
                reason="stage-specific result schema failed",
            )
            self.assertEqual(disposition["return_sha256"], hashlib.sha256(first_bytes).hexdigest())
            retry_status = status(fanout, include_pending=True, record_launch=True)
            retry = retry_status["pending_assignments"][0]
            self.assertEqual(
                retry_status["attempt_counts"],
                {"attempted": 2, "succeeded": 0, "failed": 0, "unusable": 1, "outstanding": 1},
            )
            self.assertEqual(retry["attempt"], 2)
            self.assertNotEqual(Path(retry["return_path"]), first_path)
            self.assertEqual(first_path.read_bytes(), first_bytes)

            second_path = Path(retry["return_path"])
            self.write_return(second_path, "q00", 2, complete=True)
            final = status(fanout)
            self.assertEqual((final["complete"], final["exhausted"]), (1, 0))
            self.assertEqual(
                final["attempt_counts"],
                {"attempted": 2, "succeeded": 1, "failed": 0, "unusable": 1, "outstanding": 0},
            )
            self.assertEqual(first_path.read_bytes(), first_bytes)
            with self.assertRaisesRegex(FanoutError, "already has a disposition"):
                record_disposition(
                    fanout,
                    assignment_id="q00",
                    attempt=1,
                    terminal="unusable",
                    reason="duplicate",
                )

    def test_failed_missing_attempt_rejects_a_late_return(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fanout = self.make_fanout(Path(tmp), count=1, max_attempts=2)
            prepare(fanout)
            first = status(fanout, include_pending=True, record_launch=True)["pending_assignments"][0]
            first_path = Path(first["return_path"])
            record_disposition(
                fanout,
                assignment_id="q00",
                attempt=1,
                terminal="failed",
                reason="worker exited before writing a return",
            )
            self.write_return(first_path, "q00", 1, complete=True)
            with self.assertRaisesRegex(FanoutError, "appeared after its missing attempt was disposed"):
                status(fanout)

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
