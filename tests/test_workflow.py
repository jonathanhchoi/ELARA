from __future__ import annotations

import csv
import json
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "scripts"))

from sync_skill_wrappers import add_codex_policy, expected_files  # noqa: E402
from validate_workflow import (  # noqa: E402
    EXPECTED_STAGE_IDS,
    HARD_GATES,
    validate_repository,
    validate_state,
)
from workflow_lib import load_stages, parse_frontmatter  # noqa: E402


class WorkflowContractTests(unittest.TestCase):
    def test_ci_uses_an_explicit_read_only_token(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("\npermissions:\n  contents: read\n", workflow)

    def test_codex_policy_replacement_uses_one_trailing_policy_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "openai.yaml"
            config.write_text(
                'interface:\n  display_name: "ELARA"\npolicy:\n'
                "  allow_implicit_invocation: true\n  note: retained nowhere\n",
                encoding="utf-8",
            )

            updated = add_codex_policy(config, allow_implicit=False)

            self.assertEqual(updated.count("\npolicy:\n"), 1)
            self.assertNotIn("note: retained nowhere", updated)
            self.assertTrue(updated.endswith("  allow_implicit_invocation: false\n"))

    def test_repository_contract(self) -> None:
        self.assertEqual(validate_repository(ROOT), [])

    def test_researcher_facing_language_contract(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        definition = (
            "the software infrastructure surrounding an LLM that enables it to operate "
            "as an agent (the agent harness)"
        )
        flat_agents = " ".join(agents.split())
        self.assertIn(definition, flat_agents)
        for concrete_rule in (
            "Unnecessary, invented, or purely internal jargon is prohibited",
            "confirmatory core",
            "parallel sub-agents",
            "the complete list of documents or other units eligible for coding",
            "Preserve literal filenames, commands, state fields, and code values",
        ):
            self.assertIn(concrete_rule, flat_agents)

        selected_headings = {
            "Objective",
            "Researcher decisions",
            "Mode handoff",
            "Orientation (first session)",
            "Usage mode: the whole pipeline or specific tools",
            "Artifacts",
            "Next-stage handoff",
        }

        def selected_sections(body: str) -> str:
            matches = list(re.finditer(r"(?m)^## ([^\r\n]+)\r?$", body))
            parts: list[str] = []
            for index, match in enumerate(matches):
                if match.group(1) not in selected_headings:
                    continue
                end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
                parts.append(body[match.start() : end])
            return "\n".join(parts)

        surfaces: dict[str, str] = {
            "README.md": (ROOT / "README.md").read_text(encoding="utf-8"),
            "PIPELINE.md": (ROOT / "PIPELINE.md").read_text(encoding="utf-8"),
            "project/PROJECT_STATE.md": parse_frontmatter(
                ROOT / "project" / "PROJECT_STATE.md"
            )[1],
        }
        for path in sorted((ROOT / "workflow" / "templates").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            if text.startswith("---"):
                text = re.sub(r"\A---\r?\n.*?\r?\n---\r?\n", "", text, count=1, flags=re.DOTALL)
            surfaces[str(path.relative_to(ROOT))] = text
        for path, _meta, body in load_stages(ROOT):
            surfaces[str(path.relative_to(ROOT))] = selected_sections(body)
        for path in sorted((ROOT / "workflow" / "utilities").glob("*.md")):
            _meta, body = parse_frontmatter(path)
            surfaces[str(path.relative_to(ROOT))] = selected_sections(body)

        prohibited = {
            "fan-out": r"\bfan[- ]outs?\b",
            "typed gap": r"\btyped gaps?\b",
            "unit-space manifest": r"\bunit[- ]space manifests?\b",
            "front matter": r"\bfront[- ]matter\b",
            "pinned": r"\bpinned\b",
            "quarantine": r"\bquarantin(?:e|ed|es|ing)\b",
            "serial writer": r"\bserial writers?\b",
            "confirmatory core": r"\bconfirmatory core\b",
            "goal_condition": r"\bgoal_condition\b",
            "interaction_profile": r"\binteraction_profile\b",
            "active_artifacts": r"\bactive_artifacts\b",
        }
        for label, text in surfaces.items():
            prose = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
            prose = re.sub(r"`[^`\r\n]+`", "", prose)
            for term, pattern in prohibited.items():
                self.assertIsNone(
                    re.search(pattern, prose, flags=re.IGNORECASE),
                    f"{label} exposes prohibited researcher-facing shorthand: {term}",
                )
            if re.search(r"\bagent harness\b", prose, flags=re.IGNORECASE):
                self.assertIn(definition, " ".join(prose.split()), label)

    def test_generated_wrappers_inherit_plain_language_rule(self) -> None:
        prohibited = re.compile(
            r"\b(?:fan[- ]outs?|typed gaps?|unit[- ]space manifests?|front[- ]matter|"
            r"serial writers?|confirmatory core|goal_condition|interaction_profile|active_artifacts)\b",
            flags=re.IGNORECASE,
        )
        wrappers = sorted((ROOT / ".agents" / "skills").glob("elr-*/SKILL.md"))
        wrappers += sorted((ROOT / ".claude" / "skills").glob("elr-*/SKILL.md"))
        self.assertTrue(wrappers)
        for path in wrappers:
            text = path.read_text(encoding="utf-8")
            self.assertIn("AGENTS.md", text, path)
            match = re.match(r"---\r?\n(.*?)\r?\n---", text, flags=re.DOTALL)
            self.assertIsNotNone(match, path)
            self.assertIsNone(prohibited.search(match.group(1)), path)
        for path in sorted((ROOT / ".agents" / "skills").glob("elr-*/agents/openai.yaml")):
            self.assertIsNone(prohibited.search(path.read_text(encoding="utf-8")), path)

    def test_stage_inventory_and_hard_gates(self) -> None:
        loaded = load_stages(ROOT)
        self.assertEqual([meta["stage_id"] for _, meta, _ in loaded], EXPECTED_STAGE_IDS)
        by_id = {meta["stage_id"]: meta for _, meta, _ in loaded}
        for stage_id, gate in HARD_GATES.items():
            self.assertEqual(by_id[stage_id]["human_gate"], gate)

    def test_feasibility_gates_use_plain_questions_and_default_to_subagents(self) -> None:
        body = next(
            body for _, meta, body in load_stages(ROOT) if meta["stage_id"] == "03-feasibility-audit"
        )
        headings = (
            "Is the coding task one that LLMs are good at?",
            "Can a careful human verify each coding decision from the source?",
            "Would this be an interesting contribution to the literature regardless of the direction of the results?",
            "Can we obtain and use the data the project needs?",
            "Will there be enough usable data to answer the research question?",
            "Can the project be completed in a reasonable amount of time with the available resources?",
            "Could coding errors change the answer, and can the analysis account for them?",
            "Does a legal, ethical, data-use, or spending issue require the researcher’s decision?",
        )
        for number, heading in enumerate(headings, start=1):
            self.assertIn(f"**Gate {number}: {heading}**", body)
        for internal_id in (
            "task-type",
            "variable-verifiability",
            "either-way-contribution",
            "data-access",
            "base-rate-and-power",
            "time-and-resources",
            "measurement-error",
            "researcher-decision",
        ):
            self.assertIn(f"stable internal ID is `{internal_id}`", body)
        self.assertNotIn("Write a gate-by-gate table", body)

        flat = " ".join(body.split())
        for requirement in (
            "software for coordinating parallel sub-agents as the default route",
            "low, central, and high scenarios",
            "Do not assign a dollar value to subscription-backed sub-agent use",
            "comparison of what the same work would cost through the optional API route in every audit",
            "current provider prices",
            "available batch discounts",
            "Mark the sub-agent dollar cost as not estimated, not zero",
            "one prose section for each gate",
            "Do not use a gate table",
            "project/artifacts/feasibility_audit_vNNN.pdf",
            "ask all still-needed questions in one chat message",
            "feasibility-report-consultation",
            "Do not draft or build the final report yet",
            "This is the full feasibility analysis",
            "every material analysis performed during the audit",
            "Researcher consultation and decisions",
        ):
            self.assertIn(requirement, flat)

        readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
        pipeline = " ".join((ROOT / "PIPELINE.md").read_text(encoding="utf-8").split())
        for public_doc in (readme, pipeline):
            self.assertIn("sub-agent", public_doc)
            self.assertIn("API", public_doc)
            self.assertIn("consult", public_doc.lower())
            self.assertIn("full", public_doc.lower())

    def test_skeleton_stage_contract_and_public_routes(self) -> None:
        stages = {meta["stage_id"]: (meta, body) for _, meta, body in load_stages(ROOT)}
        metadata, body = stages["17-skeleton-draft"]
        self.assertEqual(metadata["paper_steps"], ["6"])
        self.assertFalse(metadata["core"])
        self.assertEqual(metadata["interaction_profile"], "plan_then_execute")
        self.assertFalse(metadata["long_running"])
        self.assertEqual(metadata["prerequisites"], ["16-replication-package"])
        self.assertEqual(metadata["human_gate"], "skeleton-draft-approval")
        self.assertEqual(metadata["next_stage"], "18-integrate-manuscript")
        flat_body = " ".join(body.split())
        for phrase in (
            "create the skeleton draft",
            "skip",
            "recommended output is a LaTeX-generated PDF",
            "request_user_input",
            "AskUserQuestion",
            "LaTeX",
            "Markdown",
            "article prose",
            "waiting_for_user",
            "law_review_v1",
            "journal_of_legal_analysis_v1",
            "Never silently apply the JLA template",
            "Word comments",
            "Alt text:",
        ):
            self.assertIn(phrase.lower(), flat_body.lower())
        execution_control = (
            ROOT / "workflow" / "shared" / "execution-control.md"
        ).read_text(encoding="utf-8")
        skeleton_template = (
            ROOT / "workflow" / "templates" / "skeleton_draft_template.md"
        ).read_text(encoding="utf-8")
        for researcher_facing_surface in (body, execution_control, skeleton_template):
            self.assertNotIn("approximate length", researcher_facing_surface.lower())
            self.assertNotIn("target_length", researcher_facing_surface.lower())
        self.assertIn("target venue", flat_body.lower())
        registry = json.loads(
            (ROOT / "workflow" / "templates" / "word" / "profiles.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            set(registry["profiles"]),
            {"law_review_v1", "journal_of_legal_analysis_v1"},
        )
        profile_template = (
            ROOT / "workflow" / "templates" / "publication_profile_template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Official requirements checked", profile_template)
        self.assertIn("Approved template fallback", profile_template)
        self.assertEqual(stages["16-replication-package"][0]["next_stage"], "17-skeleton-draft")
        self.assertEqual(stages["18-integrate-manuscript"][0]["prerequisites"], ["17-skeleton-draft"])
        stage_eighteen = stages["18-integrate-manuscript"][1]
        self.assertIn("planning context", stage_eighteen)
        self.assertIn("waiting_for_user", stage_eighteen)
        pipeline = (ROOT / "PIPELINE.md").read_text(encoding="utf-8")
        self.assertIn("elr-17-skeleton-draft", pipeline)
        self.assertIn("Workflow 2.0 state compatibility", pipeline)

        artifact_contract = (ROOT / "workflow" / "shared" / "artifact-contract.md").read_text(
            encoding="utf-8"
        )
        artifact_contract_flat = " ".join(artifact_contract.split())
        self.assertIn(
            "default active artifact is a PDF compiled from a versioned LaTeX source",
            artifact_contract_flat,
        )
        self.assertIn("only when the researcher expressly asks for it", artifact_contract_flat)
        self.assertIn("CSV", artifact_contract_flat)

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

    def test_decision_stages_use_plan_mode_to_elicit_researcher_preferences(self) -> None:
        stages = {meta["stage_id"]: (meta, body) for _, meta, body in load_stages(ROOT)}
        interview_stages = {
            "01-conceive",
            "04-methods-design",
            "05-codebook-and-schema",
            "07-adversarial-review",
            "08-pilot",
            "09-freeze-and-preregister",
            "17-skeleton-draft",
        }
        control = (ROOT / "workflow" / "shared" / "execution-control.md").read_text(
            encoding="utf-8"
        )
        guardrails = (ROOT / "workflow" / "shared" / "guardrails.md").read_text(
            encoding="utf-8"
        )
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        pipeline = (ROOT / "PIPELINE.md").read_text(encoding="utf-8")
        flat_guardrails = " ".join(guardrails.split())

        for stage_id in interview_stages:
            meta, stage = stages[stage_id]
            flat_stage = " ".join(stage.split())
            self.assertEqual(meta["interaction_profile"], "plan_then_execute", stage_id)
            for needle in ("Plan Mode", "request_user_input", "AskUserQuestion", "approval"):
                self.assertIn(needle.lower(), flat_stage.lower(), (stage_id, needle))

        stage_four = " ".join(stages["04-methods-design"][1].split())
        for needle in (
            "Always enter the host's read-only Plan Mode",
            "one to three plain-language questions per round",
            '"go with the recommendations"',
            '"don\'t know"',
            "it does not approve the final `methods-plan-approval` gate",
        ):
            self.assertIn(needle, stage_four, needle)

        self.assertIn("### Interactive Plan-Mode decision interviews", control)
        for stage_id in ("01", "04", "05", "07", "08", "09", "17"):
            self.assertIn(f"#### Stage {stage_id}", control)
        self.assertIn("`request_user_input`", control)
        self.assertIn("`AskUserQuestion`", control)
        self.assertIn("Stages 01, 04, 05, 07, 08, 09, and 17", flat_guardrails)
        self.assertIn("Stages 01, 04, 05, 07, 08, 09, and 17", agents)
        self.assertIn("Stages 01, 04, 05, 07, 08, 09, and 17", claude)
        self.assertIn("Stages 01, 04, 05, 07, 08, 09, and 17", pipeline)
        self.assertIn("Use Plan Mode twice", control)
        self.assertIn("Run the independent critiques first", control)
        self.assertIn("rather than reopening it", control)
        self.assertIn("external submission", control)
        self.assertNotIn("Plan acceptance is the final methods approval", stage_four)

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
        for stage_id in ("18-integrate-manuscript", "20-revise-and-respond"):
            body = stages[stage_id]
            self.assertIn("workflow/shared/manuscript-editing-contract.md", body, stage_id)
            self.assertIn("PUBLICATION_PROFILE_vNNN.md", body, stage_id)
            self.assertIn("hash", body.lower(), stage_id)
        # Stage 00 may offer to create the profile; no coding or analysis stage reads it.
        for stage_id, body in stages.items():
            if stage_id in ("00-initialize", "18-integrate-manuscript", "20-revise-and-respond"):
                continue
            self.assertNotIn("PUBLICATION_PROFILE", body, stage_id)
        for platform in (".agents", ".claude"):
            for stage_id in ("18-integrate-manuscript", "20-revise-and-respond"):
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
        for stage_id in ("02-preemption-review", "12-interpretive-verification", "19-cite-check"):
            self.assertIn(stage_id, referencing)

    def test_long_work_requires_progress_and_eta_updates(self) -> None:
        def compact(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        agents = compact(ROOT / "AGENTS.md")
        guardrails = compact(ROOT / "workflow" / "shared" / "guardrails.md")
        fanout = compact(ROOT / "workflow" / "shared" / "observation-fanout.md")
        execution_control = compact(ROOT / "workflow" / "shared" / "execution-control.md")

        for text in (agents, guardrails):
            self.assertIn("about two minutes", text)
            self.assertIn("about every five minutes", text)
            self.assertIn("eta range", text)
            self.assertIn("elapsed time", text)
        self.assertIn("observed wall-clock wave throughput", fanout)
        self.assertIn("actual remaining waves", fanout)
        self.assertIn("never expose interim labels", fanout)
        self.assertIn("pair plan creation", execution_control)
        self.assertIn("revised eta range", execution_control)

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
        self.assertIn("not kept separate", lowered)
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
        # The nine plan-then-execute stages that end at their own gate continue into
        # execution; the two manuscript stages keep their stop, which is the gate.
        for stage_id in ("01-conceive", "04-methods-design", "05-codebook-and-schema", "07-adversarial-review",
                         "08-pilot", "09-freeze-and-preregister", "13-human-validation", "14-analysis-and-correction",
                         "17-skeleton-draft"):
            body = (ROOT / "workflow" / "stages" / f"{stage_id}.md").read_text(encoding="utf-8")
            self.assertIn("continue into execution in the same session", " ".join(body.split()), stage_id)
        for stage_id in ("18-integrate-manuscript", "20-revise-and-respond"):
            body = (ROOT / "workflow" / "stages" / f"{stage_id}.md").read_text(encoding="utf-8")
            self.assertIn("manuscript-edit-permission", body, stage_id)
            self.assertNotIn("continue into execution in the same session", body, stage_id)

    def test_stage_00_records_usage_in_state_settings_and_has_a_two_question_tools_setup(self) -> None:
        body = next(body for _, meta, body in load_stages(ROOT) if meta["stage_id"] == "00-initialize")
        lowered = body.lower()
        for needle in (
            "`usage` setting",
            "usage: pipeline",
            "usage: tools",
            "two questions",
            "workspace charter",
            "recorded verbatim",
        ):
            self.assertIn(needle, lowered, needle)
        self.assertNotIn("body of project_state.md", lowered)
        pipeline = (ROOT / "PIPELINE.md").read_text(encoding="utf-8")
        self.assertIn("`usage` setting", pipeline)
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
        for stage_id in ("02-preemption-review", "07-adversarial-review", "19-cite-check"):
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

    def test_stage_02_uses_parent_browser_fallback_without_broadening_workers(self) -> None:
        stage = (ROOT / "workflow" / "stages" / "02-preemption-review.md").read_text(
            encoding="utf-8"
        )
        guardrails = (ROOT / "workflow" / "shared" / "guardrails.md").read_text(
            encoding="utf-8"
        )
        contract = (ROOT / "workflow" / "shared" / "observation-fanout.md").read_text(
            encoding="utf-8"
        )
        flat_stage = " ".join(stage.split())
        flat_contract = " ".join(contract.split())
        self.assertIn("parent-only browser fallback", flat_stage)
        self.assertIn("parent_browser_fallback", stage)
        self.assertIn("browser control in the researcher's main authorized session", flat_stage)
        self.assertIn("Parent-only browser fallback for Stage 02", contract)
        self.assertIn("never a worker tool", flat_contract)
        self.assertIn("one bounded ordinary-UI attempt", flat_contract)
        self.assertIn("Never inspect credentials or session stores", contract)
        self.assertIn("parent-only browser fallback", guardrails)
        for relative in (
            ".claude/agents/elr-research-worker.md",
            ".codex/agents/elr-research-worker.toml",
        ):
            worker = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("no browser", worker.lower(), relative)
            self.assertIn("never escalate", worker.lower(), relative)
        for relative in ("README.md", "PIPELINE.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("parent", text.lower(), relative)
            self.assertIn("browser-control", text.lower(), relative)

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

    def test_stage_zero_running_state_is_valid_before_slug_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            text = (ROOT / "project" / "PROJECT_STATE.md").read_text(encoding="utf-8")
            text = text.replace('status: "ready"', 'status: "running"')
            text = text.replace(
                "last_run_id: null",
                'last_run_id: "20260825T140537Z_00-initialize_r001"',
            ).replace("updated_at: null", 'updated_at: "2026-08-25T14:05:37Z"')
            (project / "PROJECT_STATE.md").write_text(text, encoding="utf-8")
            self.assertEqual(validate_state(root), [])

    def test_stage_zero_charter_gate_is_valid_before_slug_approval(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            text = (ROOT / "project" / "PROJECT_STATE.md").read_text(encoding="utf-8")
            text = text.replace('status: "ready"', 'status: "awaiting_approval"')
            text = text.replace(
                "active_artifacts: {}",
                'active_artifacts: {"project_charter": "project/PROJECT_CHARTER_v001.md"}',
            ).replace(
                "outstanding_user_inputs: []",
                'outstanding_user_inputs: ["Approve the project charter"]',
            )
            text = text.replace(
                "last_run_id: null",
                'last_run_id: "20260825T140537Z_00-initialize_r001"',
            ).replace("updated_at: null", 'updated_at: "2026-08-25T14:09:02Z"')
            (project / "PROJECT_STATE.md").write_text(text, encoding="utf-8")
            self.assertEqual(validate_state(root), [])

    def test_stage_zero_waiting_for_user_is_valid_before_run_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            text = (ROOT / "project" / "PROJECT_STATE.md").read_text(encoding="utf-8")
            text = text.replace('status: "ready"', 'status: "waiting_for_user"')
            text = text.replace(
                "outstanding_user_inputs: []",
                'outstanding_user_inputs: ["Resolve the project-folder conflict"]',
            ).replace("updated_at: null", 'updated_at: "2026-08-25T14:01:00Z"')
            (project / "PROJECT_STATE.md").write_text(text, encoding="utf-8")
            self.assertEqual(validate_state(root), [])

    def test_null_slug_cannot_route_outside_stage_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            text = (ROOT / "project" / "PROJECT_STATE.md").read_text(encoding="utf-8")
            text = text.replace(
                'current_stage: "00-initialize"', 'current_stage: "01-question-scope"'
            )
            (project / "PROJECT_STATE.md").write_text(text, encoding="utf-8")
            errors = validate_state(root)
            self.assertTrue(any("null project_slug" in error for error in errors), errors)

    def test_stage_zero_charter_gate_requires_outputs_and_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            project.mkdir()
            text = (ROOT / "project" / "PROJECT_STATE.md").read_text(encoding="utf-8")
            text = text.replace('status: "ready"', 'status: "awaiting_approval"')
            text = text.replace(
                "last_run_id: null",
                'last_run_id: "20260825T140537Z_00-initialize_r001"',
            ).replace("updated_at: null", 'updated_at: "2026-08-25T14:09:02Z"')
            (project / "PROJECT_STATE.md").write_text(text, encoding="utf-8")
            errors = validate_state(root)
            self.assertTrue(any("active artifact" in error for error in errors), errors)
            self.assertTrue(any("outstanding request" in error for error in errors), errors)

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
