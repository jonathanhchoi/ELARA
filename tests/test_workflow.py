from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
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

    def test_native_plan_and_goal_control_is_stage_scoped(self) -> None:
        control_path = ROOT / "workflow" / "shared" / "execution-control.md"
        self.assertTrue(control_path.is_file())
        control = control_path.read_text(encoding="utf-8")
        for heading in (
            "## One stage, one native plan",
            "## Plan profiles and Plan Mode",
            "## Long-running stages use one goal",
            "## Codex adapter",
            "## Claude Code adapter",
        ):
            self.assertIn(heading, control)
        for needle in (
            "`update_plan`",
            "`get_goal`",
            "`update_goal`",
            "`TaskCreate`",
            "`TaskUpdate`",
            "`TaskList`",
            "one goal per stage",
            "never one goal for the whole pipeline",
        ):
            self.assertIn(needle, control, needle)

        conditions: list[str] = []
        for path, meta, body in load_stages(ROOT):
            self.assertIn("workflow/shared/execution-control.md", body, path)
            condition = meta["goal_condition"]
            if meta["long_running"]:
                self.assertIsInstance(condition, str, path)
                self.assertTrue(condition.startswith("Run Stage "), path)
                self.assertIn(meta["stage_id"][:2], condition, path)
                self.assertIn("section 11", condition, path)
                self.assertIn("<goal_condition>", body, path)
                self.assertIn("/goal", body, path)
                conditions.append(condition)
            else:
                self.assertIsNone(condition, path)
        self.assertEqual(len(conditions), len(set(conditions)))
        self.assertEqual(len(conditions), 12)

        codex_wrapper = (ROOT / ".agents" / "skills" / "elr-11-scale-up" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        claude_wrapper = (ROOT / ".claude" / "skills" / "elr-11-scale-up" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`update_plan`", codex_wrapper)
        for tool in ("`TaskCreate`", "`TaskUpdate`", "`TaskList`"):
            self.assertIn(tool, claude_wrapper)
        for wrapper in (codex_wrapper, claude_wrapper):
            self.assertIn("`/goal <goal_condition>`", wrapper)
            self.assertIn("never replace another active goal", wrapper)

        from doctor import DISCOVERY_SURFACES

        self.assertIn("workflow/shared/execution-control.md", DISCOVERY_SURFACES)
        observation = (ROOT / "workflow" / "shared" / "observation-fanout.md").read_text(
            encoding="utf-8"
        )
        flat_observation = " ".join(observation.split())
        self.assertIn("do not create a narrower fan-out goal", flat_observation)
        self.assertIn("Workers never create goals or plans", flat_observation)

        guardrails = (ROOT / "workflow" / "shared" / "guardrails.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`/goal <goal_condition>`", guardrails)
        self.assertIn("do not replace or clear it", guardrails)
        self.assertIn("native plan", (ROOT / "README.md").read_text(encoding="utf-8"))
        self.assertIn("`TaskCreate`", (ROOT / "PIPELINE.md").read_text(encoding="utf-8"))

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
        # Low-touch by design: infer first, then ask what remains in one message.
        self.assertIn("in one message", lowered)
        self.assertIn("go with the defaults", lowered)
        self.assertNotIn("one question at a time", lowered)
        self.assertIn("checkpoints", lowered)
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
        # The paste-in start downloads the installer alone; the public archive supplies the kit.
        self.assertIn("https://raw.githubusercontent.com/jonathanhchoi/elara/main/scripts/bootstrap.py", readme)
        self.assertIn("python bootstrap.py", readme)
        self.assertNotIn("if the repository is public", readme)
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
        self.assertIn("`usage` (optional)", contract)
        self.assertNotIn("## Usage mode", contract, "usage mode lives in the front matter, not the state body")
        guardrails = (ROOT / "workflow" / "shared" / "guardrails.md").read_text(encoding="utf-8")
        self.assertIn("agreement to continue", guardrails)
        self.assertIn("project/BOOTSTRAP.md", guardrails)

    def test_stage_wrappers_allow_explicitly_chosen_stages(self) -> None:
        from sync_skill_wrappers import UTILITY_SKILLS

        checked = 0
        for path, content in expected_files(ROOT).items():
            name = path.parent.name
            if path.name == "SKILL.md" and name.startswith("elr-") and name[4:6].isdigit():
                self.assertIn("adoption path", content, path)
                self.assertIn("usage mode", content, path)
                self.assertIn("`project_slug` is null", content, path)
                checked += 1
            elif path.name == "SKILL.md" and name in UTILITY_SKILLS:
                # A utility on a fresh template first runs the two-question setup.
                self.assertIn("`project_slug` is null", content, path)
                self.assertIn("workflow/stages/00-initialize.md", content, path)
        self.assertEqual(checked, 2 * len(EXPECTED_STAGE_IDS))

    def test_state_usage_key_is_optional_and_validated(self) -> None:
        template = (ROOT / "project" / "PROJECT_STATE.md").read_text(encoding="utf-8")
        self.assertIn('usage: "pipeline"', template)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project").mkdir()
            state = root / "project" / "PROJECT_STATE.md"
            # A schema-1.0 state file without the key still validates.
            state.write_text(template.replace('usage: "pipeline"\n', ""), encoding="utf-8")
            self.assertEqual(validate_state(root), [])
            initialized = template.replace("project_slug: null", 'project_slug: "fixture"').replace(
                "updated_at: null", 'updated_at: "2026-08-16T00:00:00Z"'
            )
            state.write_text(initialized.replace('usage: "pipeline"', 'usage: "tools"'), encoding="utf-8")
            self.assertEqual(validate_state(root), [])
            state.write_text(initialized.replace('usage: "pipeline"', 'usage: "specific tools"'), encoding="utf-8")
            errors = validate_state(root)
            self.assertTrue(any("usage must be one of" in error for error in errors), errors)
            state.write_text(initialized.replace('usage: "pipeline"', 'mode: "tools"'), encoding="utf-8")
            errors = validate_state(root)
            self.assertTrue(any("public state contract" in error for error in errors), errors)

    def test_state_checkpoints_key_is_optional_and_validated(self) -> None:
        template = (ROOT / "project" / "PROJECT_STATE.md").read_text(encoding="utf-8")
        self.assertIn('checkpoints: "none"', template)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project").mkdir()
            state = root / "project" / "PROJECT_STATE.md"
            # A schema-1.1 state file without the key still validates: absent means none.
            state.write_text(template.replace('checkpoints: "none"\n', ""), encoding="utf-8")
            self.assertEqual(validate_state(root), [])
            initialized = template.replace("project_slug: null", 'project_slug: "fixture"').replace(
                "updated_at: null", 'updated_at: "2026-08-16T00:00:00Z"'
            )
            for value in ("stages", "plans", "all"):
                state.write_text(initialized.replace('checkpoints: "none"', f'checkpoints: "{value}"'), encoding="utf-8")
                self.assertEqual(validate_state(root), [], value)
            state.write_text(initialized.replace('checkpoints: "none"', 'checkpoints: "always"'), encoding="utf-8")
            errors = validate_state(root)
            self.assertTrue(any("checkpoints must be one of" in error for error in errors), errors)

    def test_kit_is_low_touch_between_gates(self) -> None:
        guardrails = (ROOT / "workflow" / "shared" / "guardrails.md").read_text(encoding="utf-8")
        self.assertIn("## 11. Autonomy", guardrails)
        self.assertIn("assistant-default", guardrails)
        self.assertIn("Never decide provisionally", guardrails)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Be low-touch", agents)
        self.assertNotIn("one question at a time", agents)
        pipeline = (ROOT / "PIPELINE.md").read_text(encoding="utf-8")
        self.assertIn("Low-touch by default", pipeline)
        self.assertIn("`checkpoints`", pipeline)
        decisions = (ROOT / "project" / "DECISIONS.md").read_text(encoding="utf-8")
        self.assertIn("assistant-default", decisions)
        for platform in (".agents", ".claude"):
            router = (ROOT / platform / "skills" / "elr" / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("section 11", router)
        # The eight plan-then-execute stages that end at their own gate continue into
        # execution; the two manuscript stages keep their stop, which is the gate.
        for stage_id in ("01-conceive", "04-methods-design", "05-codebook-and-schema", "07-adversarial-review",
                         "08-pilot", "09-freeze-and-preregister", "13-human-validation", "14-analysis-and-correction"):
            body = (ROOT / "workflow" / "stages" / f"{stage_id}.md").read_text(encoding="utf-8")
            self.assertIn("continue into execution in the same session", body, stage_id)
        for stage_id in ("17-integrate-manuscript", "19-revise-and-respond"):
            body = (ROOT / "workflow" / "stages" / f"{stage_id}.md").read_text(encoding="utf-8")
            self.assertIn("manuscript-edit-permission", body, stage_id)
            self.assertNotIn("continue into execution in the same session", body, stage_id)

    def test_stage_00_records_usage_in_front_matter_and_has_a_two_question_tools_setup(self) -> None:
        body = next(body for _, meta, body in load_stages(ROOT) if meta["stage_id"] == "00-initialize")
        lowered = body.lower()
        for needle in (
            "`usage` key",
            "usage: pipeline",
            "usage: tools",
            "two questions",
            "workspace charter",
            "recorded verbatim",
        ):
            self.assertIn(needle, lowered, needle)
        self.assertNotIn("body of project_state.md", lowered)
        pipeline = (ROOT / "PIPELINE.md").read_text(encoding="utf-8")
        self.assertIn("`usage` key", pipeline)
        self.assertNotIn("## Usage mode", pipeline)

    def test_fan_outs_are_run_by_the_host_orchestrator_on_both_hosts(self) -> None:
        # Claude Code: every fan-out is one of the kit's saved workflows, launched by the
        # assistant; Codex: the kit's custom sub-agents. Never a hand-launched worker loop, never
        # an all-tools agent (2026-08-17 incident), on either host.
        from doctor import DISCOVERY_SURFACES  # noqa: PLC0415

        observation = (ROOT / ".claude" / "workflows" / "elr-observation-fanout.js").read_text(encoding="utf-8")
        research = (ROOT / ".claude" / "workflows" / "elr-research-fanout.js").read_text(encoding="utf-8")
        self.assertIn("agentType: 'elr-worker'", observation)
        self.assertIn("agentType: 'elr-research-worker'", research)
        self.assertIn("agentType: 'elr-worker'", research)  # controller status steps
        self.assertIn("scripts/research_fanout.py status", research)
        for text in (observation, research):
            self.assertNotIn("general-purpose", text)
            self.assertIn("export const meta", text)
        for relative, name in (
            (".codex/agents/elr-worker.toml", "elr_worker"),
            (".codex/agents/elr-research-worker.toml", "elr_research_worker"),
        ):
            toml = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(f'name = "{name}"', toml)
            self.assertIn("developer_instructions", toml)
            self.assertIn("sandbox_mode", toml)
            self.assertNotIn("[mcp_servers.", toml)
        for relative in (
            ".claude/workflows/elr-research-fanout.js",
            ".codex/agents/elr-worker.toml",
            ".codex/agents/elr-research-worker.toml",
            "scripts/research_fanout.py",
        ):
            self.assertIn(relative, DISCOVERY_SURFACES)
        contract = (ROOT / "workflow" / "shared" / "observation-fanout.md").read_text(encoding="utf-8")
        for heading in (
            "## The host orchestrates; the kit validates",
            "## Research fan-outs",
            "## Codex adapter",
            "## Claude Code adapter",
        ):
            self.assertIn(heading, contract)
        flat_contract = " ".join(contract.split())
        for needle in ("elr-observation-fanout", "elr-research-fanout", "elr_worker", "elr_research_worker",
                       "scripts/research_fanout.py", "never by the assistant launching workers one at a time"):
            self.assertIn(needle, flat_contract, needle)
        guardrails = (ROOT / "workflow" / "shared" / "guardrails.md").read_text(encoding="utf-8")
        self.assertIn(".codex/agents/", guardrails)
        self.assertIn("host's own orchestrator runs every fan-out", guardrails)
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("elr-research-fanout", claude)
        self.assertIn("elr-observation-fanout", claude)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(".codex/agents/", agents)
        self.assertIn("## How parallel work runs", (ROOT / "PIPELINE.md").read_text(encoding="utf-8"))
        stages = {meta["stage_id"]: body for _, meta, body in load_stages(ROOT)}
        for stage_id in ("02-preemption-review", "07-adversarial-review", "18-cite-check"):
            self.assertIn("elr-research-fanout", stages[stage_id], stage_id)
            self.assertIn("elr_research_worker", stages[stage_id], stage_id)
        for stage_id in ("08-pilot", "11-scale-up", "12-interpretive-verification", "15-robustness"):
            self.assertIn("elr-observation-fanout", stages[stage_id], stage_id)
            self.assertIn("elr_worker", stages[stage_id], stage_id)
        claude_skill = (ROOT / ".claude" / "skills" / "elr-code-observations" / "SKILL.md").read_text(encoding="utf-8")
        codex_skill = (ROOT / ".agents" / "skills" / "elr-code-observations" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Workflow tool", claude_skill)
        self.assertIn("elr_worker", codex_skill)
        for text in (claude_skill, codex_skill):
            self.assertIn("never one hand-launched worker at a time", " ".join(text.split()))

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
