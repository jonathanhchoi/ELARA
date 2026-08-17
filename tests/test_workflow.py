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

    def test_manuscript_stages_reference_contract_and_publication_profile(self) -> None:
        template = ROOT / "workflow" / "templates" / "publication_profile_template.md"
        contract = ROOT / "workflow" / "shared" / "manuscript-editing-contract.md"
        self.assertTrue(template.is_file())
        self.assertTrue(contract.is_file())
        template_text = template.read_text(encoding="utf-8")
        self.assertIn("project/PUBLICATION_PROFILE_v001.md", template_text)
        self.assertIn("cannot relax", template_text)
        contract_text = contract.read_text(encoding="utf-8")
        self.assertIn("publication profile", contract_text.lower())
        self.assertIn("first draft", contract_text)
        stages = {meta["stage_id"]: body for _, meta, body in load_stages(ROOT)}
        for stage_id in ("17-integrate-manuscript", "19-revise-and-respond"):
            body = stages[stage_id]
            self.assertIn("workflow/shared/manuscript-editing-contract.md", body, stage_id)
            self.assertIn("PUBLICATION_PROFILE_vNNN.md", body, stage_id)
            self.assertIn("hash", body.lower(), stage_id)
        # Stage 00 may offer to create the profile; no coding or analysis stage reads it.
        for stage_id, body in stages.items():
            if stage_id in ("00-initialize", "17-integrate-manuscript", "19-revise-and-respond"):
                continue
            self.assertNotIn("PUBLICATION_PROFILE", body, stage_id)
        for platform in (".agents", ".claude"):
            for stage_id in ("17-integrate-manuscript", "19-revise-and-respond"):
                wrapper = ROOT / platform / "skills" / f"elr-{stage_id}" / "SKILL.md"
                self.assertIn("manuscript-editing-contract.md", wrapper.read_text(encoding="utf-8"))
        # The profile is loaded on demand only; never from the always-on instructions.
        for always_on in ("AGENTS.md", "CLAUDE.md"):
            text = (ROOT / always_on).read_text(encoding="utf-8")
            self.assertNotIn("@project/PUBLICATION_PROFILE", text)

    def test_manuscript_utilities_have_canonical_files_and_wrappers(self) -> None:
        from sync_skill_wrappers import UTILITY_SKILLS

        self.assertEqual(
            set(UTILITY_SKILLS), {"elr-add-citations", "elr-proofread", "elr-apply-markup"}
        )
        for name, spec in UTILITY_SKILLS.items():
            canonical = ROOT / spec["canonical"]
            self.assertTrue(canonical.is_file(), canonical)
            text = canonical.read_text(encoding="utf-8")
            self.assertIn("workflow/shared/manuscript-editing-contract.md", text)
            self.assertIn("Do not change `current_stage`", text)
            self.assertIn("manuscript-edit-permission", text)
            self.assertTrue((ROOT / spec["route"]).is_file(), spec["route"])
            for platform in (".agents", ".claude"):
                wrapper = ROOT / platform / "skills" / name / "SKILL.md"
                wrapper_text = wrapper.read_text(encoding="utf-8")
                self.assertIn(spec["canonical"], wrapper_text)
                self.assertIn(spec["route"], wrapper_text)
                self.assertLess(len(wrapper_text.splitlines()), 30)
            yaml = ROOT / ".agents" / "skills" / name / "agents" / "openai.yaml"
            self.assertIn("allow_implicit_invocation: false", yaml.read_text(encoding="utf-8"))

    def test_fresh_review_protocol_is_shared(self) -> None:
        protocol = ROOT / "workflow" / "shared" / "fresh-review.md"
        self.assertTrue(protocol.is_file())
        guardrails = (ROOT / "workflow" / "shared" / "guardrails.md").read_text(encoding="utf-8")
        self.assertIn("workflow/shared/fresh-review.md", guardrails)
        referencing = [
            meta["stage_id"]
            for _, meta, body in load_stages(ROOT)
            if "workflow/shared/fresh-review.md" in body
        ]
        for stage_id in ("02-preemption-review", "12-interpretive-verification", "18-cite-check"):
            self.assertIn(stage_id, referencing)

    def test_stage_00_has_orientation_and_adoption_path(self) -> None:
        path, meta, body = next(
            entry for entry in load_stages(ROOT) if entry[1]["stage_id"] == "00-initialize"
        )
        lowered = body.lower()
        self.assertIn("## orientation", lowered)
        self.assertIn("one question at a time", lowered)
        self.assertIn("don't know", lowered)
        self.assertIn("adoption path", lowered)
        self.assertIn("adoption map", lowered)
        self.assertIn("researcher-asserted", lowered)
        for preset in ("question only", "design in hand", "data in hand", "results in hand", "publication only"):
            self.assertIn(preset, lowered, preset)
        for output in (
            "project/artifacts/adoption_map_vNNN.md",
            "project/artifacts/imported_vNNN/",
            "project/PUBLICATION_PROFILE_vNNN.md",
        ):
            self.assertIn(output, meta["declared_outputs"], output)
        # Adoption cannot silently launder these facts.
        self.assertIn("not preregistered", lowered)
        self.assertIn("not held out", lowered)
        # The usage-mode question and the installer's report.
        self.assertIn("## usage mode", lowered)
        self.assertIn("whole pipeline", lowered)
        self.assertIn("specific tools", lowered)
        self.assertIn("project/bootstrap.md", lowered)
        self.assertIn("never ask the researcher to move or rename anything", lowered)

    def test_router_names_start_adopt_menu_resume_status_help(self) -> None:
        for platform in (".agents", ".claude"):
            text = (ROOT / platform / "skills" / "elr" / "SKILL.md").read_text(encoding="utf-8")
            for verb in ("`start`", "`adopt`", "`menu`", "`resume`", "`status`", "`help`"):
                self.assertIn(verb, text, (platform, verb))
            self.assertIn("researcher-asserted", text)
            self.assertIn("project/BOOTSTRAP.md", text)
            self.assertIn("`pipeline` mode", text)
            self.assertIn("`specific tools` mode", text)
            self.assertIn("not gate approval", text)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("researcher-asserted", agents)
        self.assertIn("## Working with the researcher", agents)
        self.assertIn("usage mode", agents)
        self.assertIn("do not stop silently", agents)
        readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("## start here", readme)
        self.assertIn("paste this message", readme)
        self.assertIn("scripts/bootstrap.py --into .", readme)
        self.assertIn("git clone --depth 1 https://github.com/jonathanhchoi/elara.git .elara-kit", readme)
        self.assertIn("whole pipeline", readme)
        self.assertIn("specific tools", readme)
        self.assertIn("elr adopt", readme)
        self.assertIn("elr menu", readme)
        self.assertIn("elr help", readme)
        self.assertIn("what to expect in your first session", readme)
        pipeline = (ROOT / "PIPELINE.md").read_text(encoding="utf-8").lower()
        self.assertIn("adopting an existing project", pipeline)
        self.assertIn("what elara can do: the menu", pipeline)
        self.assertIn("| `menu`, `tools` |", pipeline)
        for stage_id in EXPECTED_STAGE_IDS[1:]:
            self.assertIn(f"`elr-{stage_id}`", pipeline, stage_id)
        for utility in ("elr-add-citations", "elr-proofread", "elr-apply-markup"):
            self.assertIn(f"| `{utility}` |", pipeline, utility)
        contract = (ROOT / "workflow" / "shared" / "artifact-contract.md").read_text(encoding="utf-8")
        self.assertIn("researcher-asserted", contract)
        self.assertIn("## Usage mode", contract)
        guardrails = (ROOT / "workflow" / "shared" / "guardrails.md").read_text(encoding="utf-8")
        self.assertIn("agreement to continue", guardrails)
        self.assertIn("project/BOOTSTRAP.md", guardrails)

    def test_stage_wrappers_allow_explicitly_chosen_stages(self) -> None:
        checked = 0
        for path, content in expected_files(ROOT).items():
            name = path.parent.name
            if path.name == "SKILL.md" and name.startswith("elr-") and name[4:6].isdigit():
                self.assertIn("adoption path", content, path)
                self.assertIn("usage mode", content, path)
                checked += 1
        self.assertEqual(checked, 2 * len(EXPECTED_STAGE_IDS))

    def test_scale_up_forbids_multiple_units_not_multiple_documents(self) -> None:
        body = next(body for _, meta, body in load_stages(ROOT) if meta["stage_id"] == "11-scale-up")
        self.assertIn("Never pack multiple coding units into one prompt", body)
        self.assertNotIn("Never pack multiple documents or units into one prompt", body)
        self.assertIn("several related documents", body)

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
