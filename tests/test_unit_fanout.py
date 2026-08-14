from __future__ import annotations

import hashlib
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from unit_fanout import FanoutError, merge, prepare, retry, status, submit  # noqa: E402


class UnitFanoutTests(unittest.TestCase):
    def make_spec(self, root: Path, count: int = 4) -> Path:
        root.mkdir(parents=True, exist_ok=True)
        instructions = root / "instructions.md"
        instructions.write_text("Classify exactly one item.\n", encoding="utf-8")
        schema = root / "schema.json"
        schema.write_text(
            json.dumps(
                {
                    "type": "object",
                    "required": ["label"],
                    "properties": {"label": {"enum": ["yes", "no"]}},
                    "additionalProperties": False,
                }
            ),
            encoding="utf-8",
        )
        spec = root / "spec.json"
        spec.write_text(
            json.dumps(
                {
                    "contract_version": "1.0",
                    "run_id": "fixture-run",
                    "assignment_kind": "coding_unit",
                    "frozen_inputs": [
                        {"role": "instructions", "path": "instructions.md"},
                        {"role": "result_schema", "path": "schema.json"},
                    ],
                    "units": [
                        {
                            "unit_id": f"u{index}",
                            "assignment_id": f"u{index}-attempt001",
                            "attempt": 1,
                            "payload": {"text": f"item {index}"},
                        }
                        for index in range(count)
                    ],
                }
            ),
            encoding="utf-8",
        )
        return spec

    def base_return(self, assignment_path: Path) -> tuple[dict, Path]:
        assignment = json.loads(assignment_path.read_text(encoding="utf-8"))
        returned = {
            "contract_version": assignment["contract_version"],
            "assignment_id": assignment["assignment_id"],
            "unit_id": assignment["unit_id"],
            "attempt": assignment["attempt"],
            "status": "succeeded",
            "result": {"label": "yes"},
            "error": None,
            "provenance": {"route": "fixture"},
        }
        return returned, Path(assignment["allowed_write_path"])

    def write_success(self, assignment_path: Path) -> None:
        returned, return_path = self.base_return(assignment_path)
        return_path.write_text(json.dumps(returned), encoding="utf-8")

    def write_disallowed_label(self, assignment_path: Path, label: str) -> None:
        returned, return_path = self.base_return(assignment_path)
        returned["result"] = {"label": label}
        return_path.write_text(json.dumps(returned), encoding="utf-8")

    def write_terminal_failure(self, assignment_path: Path) -> None:
        returned, return_path = self.base_return(assignment_path)
        returned["status"] = "worker_error"
        returned["result"] = None
        returned["error"] = "transport timeout before any model output"
        return_path.write_text(json.dumps(returned), encoding="utf-8")

    def test_prepare_gives_every_worker_one_unit_and_a_unique_scoped_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root), run)
            self.assertEqual(manifest["expected_assignments"], 4)
            output_paths = set()
            for row in manifest["assignments"]:
                assignment = json.loads(Path(row["assignment_path"]).read_text(encoding="utf-8"))
                self.assertIsInstance(assignment["payload"], dict)
                self.assertNotIn("units", assignment["payload"])
                output = Path(assignment["allowed_write_path"])
                output.relative_to(run.resolve())
                output_paths.add(output)
            self.assertEqual(len(output_paths), 4)

    def test_strict_submit_validates_creates_once_and_returns_blinded_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 1), run)
            assignment_path = Path(manifest["assignments"][0]["assignment_path"])
            returned, return_path = self.base_return(assignment_path)

            receipt = submit(run, returned["assignment_id"], returned)

            self.assertTrue(return_path.is_file())
            self.assertEqual(receipt["assignment_id"], returned["assignment_id"])
            self.assertEqual(receipt["unit_id"], returned["unit_id"])
            self.assertEqual(receipt["status"], "succeeded")
            self.assertEqual(receipt["output_path"], str(return_path.resolve()))
            self.assertNotIn("result", receipt)
            self.assertNotIn("label", receipt)
            self.assertEqual(status(run)["terminal"], 1)

            with self.assertRaisesRegex(FanoutError, "refusing to overwrite"):
                submit(run, returned["assignment_id"], returned)

    def test_strict_submit_rejects_invalid_result_without_persisting_or_leaking_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 1), run)
            assignment_path = Path(manifest["assignments"][0]["assignment_path"])
            returned, return_path = self.base_return(assignment_path)
            secret = "TOP_SECRET_INVALID_LABEL_ZQX"
            returned["result"] = {"label": secret}

            with self.assertRaises(FanoutError) as raised:
                submit(run, returned["assignment_id"], returned)

            self.assertFalse(return_path.exists())
            self.assertNotIn(secret, str(raised.exception))
            self.assertIn("enum constraint failed", str(raised.exception))

    def test_submit_cli_accepts_json_on_stdin_and_prints_only_operational_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 1), run)
            assignment_path = Path(manifest["assignments"][0]["assignment_path"])
            returned, return_path = self.base_return(assignment_path)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "unit_fanout.py"),
                    "submit",
                    "--run-dir",
                    str(run),
                    "--assignment-id",
                    returned["assignment_id"],
                ],
                input=json.dumps(returned),
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertTrue(return_path.is_file())
            self.assertEqual(receipt["assignment_id"], returned["assignment_id"])
            self.assertEqual(receipt["status"], "succeeded")
            self.assertNotIn("result", receipt)
            self.assertNotIn("label", receipt)

    def test_random_completion_order_merges_in_manifest_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 8), run)
            assignments = [Path(row["assignment_path"]) for row in manifest["assignments"]]
            random.Random(7).shuffle(assignments)
            for path in assignments:
                self.write_success(path)
            self.assertEqual(status(run)["terminal"], 8)
            output = root / "merged.jsonl"
            merge(run, output)
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(
                [row["assignment_id"] for row in rows],
                [row["assignment_id"] for row in manifest["assignments"]],
            )

    def test_missing_invalid_and_unknown_returns_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 2), run)
            first = json.loads(Path(manifest["assignments"][0]["assignment_path"]).read_text())
            bad = {
                "contract_version": "1.0",
                "assignment_id": first["assignment_id"],
                "unit_id": "wrong-unit",
                "attempt": 1,
                "status": "succeeded",
                "result": {"label": "maybe"},
                "error": None,
                "provenance": {},
            }
            Path(first["allowed_write_path"]).write_text(json.dumps(bad), encoding="utf-8")
            (run / "worker_returns" / "unknown.json").write_text("{}", encoding="utf-8")
            observed = status(run)
            self.assertEqual(observed["pending"], 1)
            self.assertEqual(observed["invalid"], 2)
            with self.assertRaises(FanoutError):
                merge(run, root / "must-not-exist.jsonl")

    def test_duplicate_assignment_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec_path = self.make_spec(root, 2)
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            spec["units"][1]["assignment_id"] = spec["units"][0]["assignment_id"]
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(FanoutError):
                prepare(spec_path, root / "run")

    def test_status_refuses_spec_frozen_input_or_assignment_drift(self) -> None:
        for target in ("spec", "instructions", "assignment"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                spec_path = self.make_spec(root, 1)
                run = root / "run"
                manifest = prepare(spec_path, run)
                if target == "spec":
                    spec_path.write_text("{}", encoding="utf-8")
                elif target == "instructions":
                    (root / "instructions.md").write_text(
                        "Changed after freezing.\n", encoding="utf-8"
                    )
                else:
                    assignment_path = Path(manifest["assignments"][0]["assignment_path"])
                    assignment = json.loads(assignment_path.read_text(encoding="utf-8"))
                    assignment["payload"]["text"] = "changed after freezing"
                    assignment_path.write_text(json.dumps(assignment), encoding="utf-8")
                with self.assertRaises(FanoutError):
                    status(run)

    def test_seal_catches_manifest_rewrites_that_per_file_hashes_miss(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            prepare(self.make_spec(root, 2), run)
            manifest_path = run / "run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            # Dropping a roster row keeps every remaining per-file hash valid; only the
            # seal can detect this manifest rewrite.
            manifest["assignments"] = manifest["assignments"][:1]
            manifest["expected_assignments"] = 1
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True), encoding="utf-8"
            )
            with self.assertRaisesRegex(FanoutError, "run_seal.json"):
                status(run)

    def test_legacy_run_without_seal_still_reports_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 2), run)
            (run / "run_seal.json").unlink()
            observed = status(run)
            self.assertEqual(observed["seal"], "absent_legacy_run")
            self.assertEqual(observed["pending"], 2)
            for row in manifest["assignments"]:
                self.write_success(Path(row["assignment_path"]))
            self.assertEqual(status(run)["terminal"], 2)

    def test_retry_archives_supersedes_and_merges_the_second_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 1), run)
            first_row = manifest["assignments"][0]
            self.write_disallowed_label(Path(first_row["assignment_path"]), "maybe")
            self.assertEqual(status(run)["invalid"], 1)

            issued = retry(run, "u0-attempt001")
            self.assertEqual(issued["assignment_id"], "u0-attempt002")
            self.assertEqual(issued["attempt"], 2)
            self.assertEqual(issued["superseded"], "u0-attempt001")

            archive_path = run / "worker_returns" / "archive" / "u0-attempt001.attempt1.json"
            self.assertTrue(archive_path.is_file())
            self.assertFalse(Path(first_row["return_path"]).exists())

            rewritten = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(
                [row["assignment_id"] for row in rewritten["assignments"]],
                ["u0-attempt002"],
            )
            self.assertEqual(rewritten["expected_assignments"], 1)
            self.assertEqual(
                [row["assignment_id"] for row in rewritten["superseded"]],
                ["u0-attempt001"],
            )
            self.assertEqual(rewritten["superseded"][0]["superseded_by"], "u0-attempt002")

            new_assignment_path = Path(rewritten["assignments"][0]["assignment_path"])
            new_assignment = json.loads(new_assignment_path.read_text(encoding="utf-8"))
            self.assertEqual(new_assignment["unit_id"], "u0")
            self.assertEqual(new_assignment["attempt"], 2)
            self.assertEqual(new_assignment["payload"], {"text": "item 0"})

            ledger_rows = [
                json.loads(line)
                for line in (run / "unit_ledger.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(ledger_rows[-1]["assignment_id"], "u0-attempt002")
            self.assertEqual(ledger_rows[-1]["status"], "pending")
            self.assertEqual(ledger_rows[-1]["superseded"], "u0-attempt001")

            observed = status(run)
            self.assertEqual(observed["expected"], 1)
            self.assertEqual(observed["pending"], 1)
            self.assertEqual(observed["invalid"], 0)
            self.assertEqual(observed["superseded"], 1)
            self.assertEqual(observed["seal"], "verified")

            self.write_success(new_assignment_path)
            self.assertEqual(status(run)["terminal"], 1)
            output = root / "merged.jsonl"
            merge(run, output)
            rows = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["assignment_id"], "u0-attempt002")
            self.assertEqual(rows[0]["attempt"], 2)
            self.assertTrue((root / "merge_receipt.json").is_file())

    def test_retry_refuses_pending_succeeded_superseded_and_capped_slots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_a = root / "run_a"
            manifest = prepare(self.make_spec(root / "case_a", 1), run_a)
            first_path = Path(manifest["assignments"][0]["assignment_path"])
            with self.assertRaisesRegex(FanoutError, "pending"):
                retry(run_a, "u0-attempt001")
            self.write_terminal_failure(first_path)
            issued = retry(run_a, "u0-attempt001")
            self.assertEqual(issued["attempt"], 2)
            with self.assertRaisesRegex(FanoutError, "not in the active manifest"):
                retry(run_a, "u0-attempt001")
            second_path = Path(
                json.loads((run_a / "run_manifest.json").read_text(encoding="utf-8"))[
                    "assignments"
                ][0]["assignment_path"]
            )
            self.write_terminal_failure(second_path)
            with self.assertRaisesRegex(FanoutError, "attempt cap"):
                retry(run_a, "u0-attempt002")

            run_b = root / "run_b"
            manifest_b = prepare(self.make_spec(root / "case_b", 1), run_b)
            self.write_success(Path(manifest_b["assignments"][0]["assignment_path"]))
            with self.assertRaisesRegex(FanoutError, "valid terminal success"):
                retry(run_b, "u0-attempt001")

    def test_disallowed_label_value_never_appears_in_status_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 1), run)
            secret = "TOP_SECRET_LABEL_ZQX"
            self.write_disallowed_label(
                Path(manifest["assignments"][0]["assignment_path"]), secret
            )
            observed = status(run)
            self.assertEqual(observed["invalid"], 1)
            dumped = json.dumps(observed)
            self.assertNotIn(secret, dumped)
            self.assertIn(
                "result invalid at result/label: enum constraint failed",
                observed["invalid_returns"][0]["errors"],
            )

    def test_merge_receipt_records_hashes_and_counts_and_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / "run"
            manifest = prepare(self.make_spec(root, 4), run)
            for row in manifest["assignments"]:
                self.write_success(Path(row["assignment_path"]))
            output = root / "merged.jsonl"
            result = merge(run, output)
            receipt_path = root / "merge_receipt.json"
            self.assertEqual(result["receipt"], str(receipt_path.resolve()))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(
                receipt["output_sha256"],
                hashlib.sha256(output.read_bytes()).hexdigest(),
            )
            self.assertEqual(receipt["merged"], 4)
            self.assertEqual(receipt["status_counts"], {"succeeded": 4})
            self.assertEqual(
                sorted(receipt["return_sha256"]),
                sorted(row["assignment_id"] for row in manifest["assignments"]),
            )
            for row in manifest["assignments"]:
                self.assertEqual(
                    receipt["return_sha256"][row["assignment_id"]],
                    hashlib.sha256(Path(row["return_path"]).read_bytes()).hexdigest(),
                )
            with self.assertRaisesRegex(FanoutError, "merge receipt"):
                merge(run, root / "merged_again.jsonl")


if __name__ == "__main__":
    unittest.main()
