from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
E2E = FIXTURES / "public_domain_e2e"
sys.path.insert(0, str(ROOT / "scripts"))

LOCAL_ONLY_DIRECTORY_NAMES = {
    ".git",
    "__pycache__",
    "raw_documents",
    "qa_previews",
    "ocr",
}

from workflow_lib import load_stages, parse_frontmatter  # noqa: E402


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): file_hash(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in LOCAL_ONLY_DIRECTORY_NAMES for part in path.parts)
        and not any(part.startswith("ocr_v") for part in path.parts)
    }


def copy_kit(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            "__pycache__",
            "*.pyc",
            "raw_documents",
            "qa_previews",
            "ocr",
            "ocr_v*",
        ),
    )


def numeric_leaves(value: Any, prefix: str = "") -> dict[str, int | float]:
    leaves: dict[str, int | float] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            leaves.update(numeric_leaves(child, child_prefix))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        leaves[prefix] = value
    return leaves


def run_rebuild(fixture: Path, output: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "PIP_NO_INDEX": "1",
            "NO_PROXY": "*",
            "no_proxy": "*",
        }
    )
    return subprocess.run(
        [sys.executable, "rebuild.py", "--output", str(output)],
        cwd=fixture,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


class RecordedStageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.record = json.loads(
            (FIXTURES / "stage_contract_cases.json").read_text(encoding="utf-8")
        )
        cls.stages = {
            meta["stage_id"]: (path, meta, body)
            for path, meta, body in load_stages(ROOT)
        }

    def test_record_has_one_matching_case_for_every_stage_00_through_19(self) -> None:
        cases = self.record["cases"]
        expected_ids = [f"{number:02d}-" for number in range(20)]
        self.assertEqual(len(cases), 20)
        self.assertEqual(len({case["stage_id"] for case in cases}), 20)
        for prefix, case in zip(expected_ids, cases, strict=True):
            self.assertTrue(case["stage_id"].startswith(prefix))
            self.assertIn(case["stage_id"], self.stages)

    def test_recorded_profiles_gates_transitions_and_failure_routes_match_prompts(self) -> None:
        for case in self.record["cases"]:
            _, meta, _ = self.stages[case["stage_id"]]
            self.assertEqual(case["interaction_profile"], meta["interaction_profile"])
            self.assertEqual(case["human_gate"], meta["human_gate"])
            self.assertEqual(case["next_stage"], meta["next_stage"])
            self.assertIn(case["recorded_failure_route"], meta["failure_routes"])

    def test_every_recorded_stage_has_codex_and_claude_discovery_wrapper(self) -> None:
        for case in self.record["cases"]:
            stage_id = case["stage_id"]
            codex = ROOT / ".agents" / "skills" / f"elr-{stage_id}" / "SKILL.md"
            claude = ROOT / ".claude" / "skills" / f"elr-{stage_id}" / "SKILL.md"
            for wrapper in (codex, claude):
                self.assertTrue(wrapper.is_file(), wrapper)
                text = wrapper.read_text(encoding="utf-8")
                self.assertIn(f"workflow/stages/{stage_id}.md", text)

    def test_plan_handoffs_are_read_only(self) -> None:
        before = tree_hashes(ROOT)
        for case in self.record["cases"]:
            if case["interaction_profile"] != "plan_then_execute":
                continue
            _, _, body = self.stages[case["stage_id"]]
            lowered = body.lower()
            self.assertIn("plan mode", lowered)
            self.assertTrue(
                "do not write" in lowered
                or "do not alter" in lowered
                or "leaves all files and state unchanged" in lowered
            )
        self.assertEqual(before, tree_hashes(ROOT))
        self.assertFalse(self.record["shared_expectations"]["plan_phase_writes"])

    def test_missing_prerequisite_contract_keeps_state_unchanged(self) -> None:
        state = ROOT / "project" / "PROJECT_STATE.md"
        before = state.read_bytes()
        _, meta, body = self.stages["11-scale-up"]
        missing = [item for item in meta["required_inputs"] if "vNNN" in item]
        self.assertTrue(missing)
        self.assertIn("make no writes and leave state unchanged", body.lower())
        self.assertEqual(before, state.read_bytes())
        shared = self.record["shared_expectations"]
        self.assertEqual(shared["missing_prerequisite_status"], "waiting_for_user")
        self.assertTrue(shared["state_unchanged_before_execution"])

    def test_rerun_versioning_selects_v002_without_overwriting_v001(self) -> None:
        contract = (ROOT / "workflow" / "shared" / "artifact-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Begin at `v001` and select the next\nunused integer", contract)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = directory / "pilot_report_v001.md"
            first.write_text("approved immutable result\n", encoding="utf-8")
            first_hash = file_hash(first)
            version = 1
            while (directory / f"pilot_report_v{version:03d}.md").exists():
                version += 1
            second = directory / f"pilot_report_v{version:03d}.md"
            second.write_text("rerun result\n", encoding="utf-8")
            self.assertEqual(second.name, "pilot_report_v002.md")
            self.assertEqual(file_hash(first), first_hash)
            self.assertNotEqual(first.read_bytes(), second.read_bytes())
        self.assertFalse(
            self.record["shared_expectations"]["rerun_overwrites_prior_version"]
        )

    def test_authorization_refusal_blocks_processing(self) -> None:
        _, meta, body = self.stages["06-data-authorization"]
        self.assertEqual(meta["human_gate"], "data-authorization")
        self.assertIn("denial blocks all corpus processing", body.lower())
        self.assertIn("05-codebook-and-schema", meta["failure_routes"])

    def test_material_corpus_deviation_routes_to_preregistration_without_activation(self) -> None:
        _, meta, body = self.stages["10-corpus-acquisition"]
        self.assertIn("09-freeze-and-preregister", meta["failure_routes"])
        lowered = body.lower()
        self.assertIn("preregistration amendments to stage 09", lowered)
        self.assertIn("do not activate the proposed corpus", lowered)

    def test_validation_failure_backtracks_before_analysis(self) -> None:
        _, meta, body = self.stages["13-human-validation"]
        self.assertIn("05-codebook-and-schema", meta["failure_routes"])
        self.assertIn("08-pilot", meta["failure_routes"])
        self.assertIn("routes the defect to stage 05 or stage 08", body.lower())
        self.assertIn("advance only after the researcher records a pass", body.lower())

    def test_preregistration_amendment_contract_is_explicit(self) -> None:
        _, _, freeze_body = self.stages["09-freeze-and-preregister"]
        _, acquire_meta, acquire_body = self.stages["10-corpus-acquisition"]
        self.assertIn("amendment_policy_vnnn.md", freeze_body.lower())
        self.assertEqual(acquire_meta["human_gate"], "material-corpus-deviation")
        self.assertIn("approved amendment", acquire_body.lower())


class DiscoveryAcceptanceTests(unittest.TestCase):
    def assert_discoverable(self, kit: Path, expected_stage: str) -> None:
        state, _ = parse_frontmatter(kit / "project" / "PROJECT_STATE.md")
        self.assertEqual(state["current_stage"], expected_stage)
        self.assertTrue((kit / "workflow" / "stages" / f"{expected_stage}.md").is_file())
        for platform in (".agents", ".claude"):
            router = kit / platform / "skills" / "elr" / "SKILL.md"
            self.assertTrue(router.is_file())
            text = router.read_text(encoding="utf-8").lower()
            self.assertIn("project/project_state.md", text)
            self.assertIn("resume", text)

    def set_resumable_state(self, kit: Path) -> None:
        path = kit / "project" / "PROJECT_STATE.md"
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            'current_stage: "00-initialize"', 'current_stage: "11-scale-up"'
        ).replace('status: "ready"', 'status: "running"')
        text = text.replace(
            "last_run_id: null",
            'last_run_id: "20260710T120000Z_11-scale-up_r001"',
        )
        path.write_text(text, encoding="utf-8")

    def test_clean_copy_start_and_interrupted_resume_on_both_platforms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp) / "kit"
            copy_kit(ROOT, kit)
            self.assert_discoverable(kit, "00-initialize")
            readme = (kit / "README.md").read_text(encoding="utf-8")
            self.assertIn("$elr", readme)
            self.assertIn("/elr", readme)
            self.set_resumable_state(kit)
            self.assert_discoverable(kit, "11-scale-up")
            state, _ = parse_frontmatter(kit / "project" / "PROJECT_STATE.md")
            self.assertEqual(state["status"], "running")
            self.assertEqual(state["last_run_id"], "20260710T120000Z_11-scale-up_r001")

    def test_download_zip_start_and_resume_preserve_both_platform_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source" / "kit"
            copy_kit(ROOT, source)
            archive = tmp_path / "kit.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as handle:
                for path in sorted(item for item in source.rglob("*") if item.is_file()):
                    handle.write(path, Path("kit") / path.relative_to(source))
            extracted = tmp_path / "extracted"
            with zipfile.ZipFile(archive) as handle:
                handle.extractall(extracted)
            kit = extracted / "kit"
            self.assert_discoverable(kit, "00-initialize")
            self.set_resumable_state(kit)
            self.assert_discoverable(kit, "11-scale-up")


class PublicDomainEndToEndTests(unittest.TestCase):
    def test_rebuild_covers_core_stages_and_fresh_package_reproduces_every_number(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fixture = tmp_path / "fixture"
            copy_kit(E2E, fixture)
            output = tmp_path / "build"
            first = run_rebuild(fixture, output)
            self.assertEqual(first.returncode, 0, first.stderr)

            expected = json.loads(
                (fixture / "expected" / "reported_numbers.json").read_text(encoding="utf-8")
            )
            reported = json.loads(
                (output / "16-replication-package" / "reported_numbers.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(numeric_leaves(reported), numeric_leaves(expected))
            self.assertEqual(reported, expected)
            for stage in (
                "08-pilot",
                "10-corpus-acquisition",
                "11-scale-up",
                "12-interpretive-verification",
                "13-human-validation",
                "14-analysis-and-correction",
                "15-robustness",
                "16-replication-package",
            ):
                self.assertTrue((output / stage).is_dir(), stage)

            manifest = json.loads(
                (output / "16-replication-package" / "replication_manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            package = output / "16-replication-package" / "package"
            for row in manifest:
                path = package / row["path"]
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_size, row["bytes"])
                self.assertEqual(file_hash(path), row["sha256"])

            fresh_package = tmp_path / "fresh" / "package"
            shutil.copytree(package, fresh_package)
            rebuilt_output = tmp_path / "fresh" / "rebuild_out"
            second = run_rebuild(fresh_package, rebuilt_output)
            self.assertEqual(second.returncode, 0, second.stderr)
            rebuilt = json.loads(
                (
                    rebuilt_output
                    / "16-replication-package"
                    / "reported_numbers.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(numeric_leaves(rebuilt), numeric_leaves(reported))
            self.assertEqual(rebuilt, reported)

    def test_rebuild_fails_closed_on_quote_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fixture = tmp_path / "fixture"
            copy_kit(E2E, fixture)
            source = fixture / "inputs" / "corpus" / "u08_article_vi_clause_3.txt"
            source.write_text("Tampered source text.\n", encoding="utf-8")
            result = run_rebuild(fixture, tmp_path / "build")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("schema or exact-quote verification failed", result.stderr)

    def test_rebuild_refuses_to_overwrite_an_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fixture = tmp_path / "fixture"
            copy_kit(E2E, fixture)
            output = tmp_path / "build"
            output.mkdir()
            marker = output / "approved.txt"
            marker.write_text("preserve me\n", encoding="utf-8")
            marker_hash = file_hash(marker)
            result = run_rebuild(fixture, output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output already exists", result.stderr)
            self.assertEqual(file_hash(marker), marker_hash)

    def test_fixture_rebuild_has_no_network_client(self) -> None:
        source = (E2E / "rebuild.py").read_text(encoding="utf-8")
        for forbidden in (
            "import requests",
            "import urllib",
            "import socket",
            "http.client",
            "urlopen(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
