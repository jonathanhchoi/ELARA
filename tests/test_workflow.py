from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from sync_skill_wrappers import expected_files  # noqa: E402
from validate_workflow import (  # noqa: E402
    EXPECTED_STAGE_IDS,
    HARD_GATES,
    validate_repository,
    validate_state,
)
from workflow_lib import load_stages, parse_frontmatter  # noqa: E402


class WorkflowContractTests(unittest.TestCase):
    def test_repository_contract(self) -> None:
        self.assertEqual(validate_repository(ROOT), [])

    def test_stage_inventory_and_hard_gates(self) -> None:
        loaded = load_stages(ROOT)
        self.assertEqual([meta["stage_id"] for _, meta, _ in loaded], EXPECTED_STAGE_IDS)
        by_id = {meta["stage_id"]: meta for _, meta, _ in loaded}
        for stage_id, gate in HARD_GATES.items():
            self.assertEqual(by_id[stage_id]["human_gate"], gate)

    def test_plan_profiles_cannot_claim_automatic_mode_switching(self) -> None:
        for path, meta, body in load_stages(ROOT):
            if meta["interaction_profile"] in {"plan", "plan_then_execute"}:
                self.assertIn("do not write", body.lower(), path)
                self.assertIn("approval", body.lower(), path)

    def test_wrappers_are_thin_and_canonical(self) -> None:
        expected = expected_files(ROOT)
        for path, content in expected.items():
            self.assertEqual(path.read_text(encoding="utf-8"), content)
            if path.name == "SKILL.md" and path.parent.name.startswith("elr-"):
                self.assertLess(len(content.splitlines()), 30)
                self.assertIn("workflow/stages/", content)

    def test_fresh_state_is_safe(self) -> None:
        state, _ = parse_frontmatter(ROOT / "project" / "PROJECT_STATE.md")
        self.assertEqual(state["current_stage"], "00-initialize")
        self.assertEqual(state["status"], "ready")
        self.assertEqual(state["approvals"], {})

    def test_initialized_running_state_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            text = (ROOT / "project" / "PROJECT_STATE.md").read_text(encoding="utf-8")
            text = text.replace("project_slug: null", 'project_slug: "fixture-project"')
            text = text.replace(
                'current_stage: "00-initialize"', 'current_stage: "11-scale-up"'
            ).replace('status: "ready"', 'status: "running"')
            text = text.replace(
                "last_run_id: null",
                'last_run_id: "20260710T120000Z_11-scale-up_r001"',
            ).replace("updated_at: null", 'updated_at: "2026-07-10T12:05:00Z"')
            (project / "PROJECT_STATE.md").write_text(text, encoding="utf-8")
            self.assertEqual(validate_state(root), [])

    def test_download_zip_preserves_discovery_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "kit.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in ROOT.rglob("*"):
                    if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                        zf.write(path, Path("kit") / path.relative_to(ROOT))
            extract = tmp_path / "extract"
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extract)
            kit = extract / "kit"
            self.assertTrue((kit / "AGENTS.md").is_file())
            self.assertTrue((kit / ".agents" / "skills" / "elr" / "SKILL.md").is_file())
            self.assertTrue((kit / ".claude" / "skills" / "elr" / "SKILL.md").is_file())
            self.assertEqual(validate_repository(kit), [])

    def test_public_domain_fixture_is_internally_consistent(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "minimal_public_domain"
        schema = json.loads((fixture / "expected" / "schema.json").read_text(encoding="utf-8"))
        self.assertIn("exact_quote", schema["required"])
        with (fixture / "metadata.csv").open(encoding="utf-8", newline="") as handle:
            metadata = {row["unit_id"]: row for row in csv.DictReader(handle)}
        with (fixture / "human_codes.csv").open(encoding="utf-8", newline="") as handle:
            codes = list(csv.DictReader(handle))
        self.assertEqual(set(metadata), {row["unit_id"] for row in codes})
        for row in codes:
            text = (fixture / "inputs" / metadata[row["unit_id"]]["file"]).read_text(
                encoding="utf-8"
            )
            self.assertEqual(row["has_shall"], str("shall" in text.lower()).lower())
            self.assertIn(row["assigned_institution"], text)


if __name__ == "__main__":
    unittest.main()
