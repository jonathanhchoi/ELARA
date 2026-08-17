"""Generate thin Codex and Claude skill wrappers from canonical stage metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from workflow_lib import FrontmatterError, load_stages, repository_root, skill_name


OBSERVATION_SKILL = "elr-code-observations"

# Manuscript stages also read the manuscript-editing contract and the active
# publication profile. The profile is loaded only here, on demand, never from
# AGENTS.md or CLAUDE.md, so style rules stay out of coding and analysis runs.
MANUSCRIPT_CONTRACT = "workflow/shared/manuscript-editing-contract.md"
MANUSCRIPT_STAGE_IDS = ("17-integrate-manuscript", "19-revise-and-respond")
MANUSCRIPT_EXTRA_READ = (
    f"   Then read `{MANUSCRIPT_CONTRACT}` and the active publication profile pinned in\n"
    "   `project/PROJECT_STATE.md` (`project/PUBLICATION_PROFILE_vNNN.md`), if any.\n"
)

# Optional manuscript utilities. Each maps to a canonical file under
# workflow/utilities/ and a stage it routes through, so the wrapper still names
# the canonical stage that governs what happens after the utility runs.
UTILITY_SKILLS = {
    "elr-add-citations": {
        "canonical": "workflow/utilities/add-citations.md",
        "route": "workflow/stages/18-cite-check.md",
        "description": (
            "Research, retrieve, and add only the citations the researcher marked as needed, "
            "in the publication profile's citation style, then route the new manuscript "
            "version through the audit-only Stage 18. Use when the researcher asks to add or "
            "supply citations for specific passages."
        ),
        "display_name": "ELARA Add Citations",
        "short_description": "Add only requested, retrieved citations",
        "default_prompt": "Use $elr-add-citations for the marked passages in the current manuscript.",
    },
    "elr-proofread": {
        "canonical": "workflow/utilities/proofread.md",
        "route": "workflow/stages/19-revise-and-respond.md",
        "description": (
            "Proofread the manuscript against the publication profile and report typos, grammar, "
            "clarity, tone, style tells, internal consistency, and venue compliance without "
            "rewriting; fix only uncontroversial errors when permitted. Use when the researcher "
            "asks for a proofread, a consistency check, or a venue-format check."
        ),
        "display_name": "ELARA Proofread",
        "short_description": "Flag proofreading issues; fix only clear errors",
        "default_prompt": "Use $elr-proofread on the current manuscript version.",
    },
    "elr-apply-markup": {
        "canonical": "workflow/utilities/apply-markup.md",
        "route": "workflow/stages/19-revise-and-respond.md",
        "description": (
            "Transcribe the researcher's hand markup on a PDF into a reviewable edit list, stop "
            "for approval, then apply exactly the approved edits to a versioned manuscript copy. "
            "Use when the researcher supplies a marked-up PDF."
        ),
        "display_name": "ELARA Apply Markup",
        "short_description": "Transcribe hand markup, then apply approved edits",
        "default_prompt": "Use $elr-apply-markup on the marked-up PDF under project/inputs/manuscript/markup/.",
    },
}


def stage_description(title: str, stage_id: str) -> str:
    return (
        f"Run ELR stage {stage_id}: {title}. Use when this is the current stage in "
        "project/PROJECT_STATE.md or when the researcher explicitly requests this recovery stage."
    )


def wrapper_text(
    name: str, description: str, canonical: str, *, claude: bool, extra_read: str = ""
) -> str:
    extra = "disable-model-invocation: true\n" if claude else ""
    return f'''---
name: {json.dumps(name)}
description: {json.dumps(description)}
{extra}---

# Run {name}

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, and
   `workflow/shared/artifact-contract.md` completely.
{extra_read}2. Read `{canonical}` completely and follow it as the single source of substantive
   instructions for this stage.
3. Confirm that the stage is current and its prerequisites and approvals are satisfied
   (imported artifacts and researcher-asserted approvals count). If the project is
   uninitialized (`project_slug` is null), run Stage 00 first, from its orientation, with this
   stage as the aim. If it is not current and the researcher chose it explicitly (this skill,
   the menu, or by name), first satisfy its prerequisites through Stage 00's adoption path,
   then run it; otherwise stop.
4. Honor the stage's mode handoff. A skill cannot switch Plan or Goal mode by itself.
5. Do not cross the stage's human gate. Update state and append the run ledger only as the
   canonical stage directs. At the end, summarize plainly and offer the next step per the
   usage mode (`usage` in `project/PROJECT_STATE.md`): the next stage in `pipeline` mode,
   the menu in `specific tools` mode.
'''


def utility_wrapper_text(name: str, spec: dict[str, str], *, claude: bool) -> str:
    extra = "disable-model-invocation: true\n" if claude else ""
    return f'''---
name: {json.dumps(name)}
description: {json.dumps(spec["description"])}
{extra}---

# Run {name}

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`,
   `workflow/shared/artifact-contract.md`, and `{MANUSCRIPT_CONTRACT}` completely,
   then the active publication profile pinned in `project/PROJECT_STATE.md`
   (`project/PUBLICATION_PROFILE_vNNN.md`), if any.
2. Read `{spec["canonical"]}` completely and follow it as the single source of
   substantive instructions for this utility.
3. This is an optional manuscript utility, not a pipeline stage: never change `current_stage`,
   and append the run ledger and decisions only as the canonical file directs. If the project
   is uninitialized (`project_slug` is null), first run Stage 00's two-question specific-tools
   setup (`workflow/stages/00-initialize.md`, "Usage mode"), then continue.
4. Honor the utility's phases. Do not edit any manuscript file before the researcher grants
   the permission the canonical file names; a skill cannot switch Plan or Goal mode by itself.
5. Afterwards follow the route the canonical file names (`{spec["route"]}`) rather than
   treating the utility's output as final.
'''


def utility_openai_yaml(name: str, spec: dict[str, str]) -> str:
    return f'''interface:
  display_name: {json.dumps(spec["display_name"])}
  short_description: {json.dumps(spec["short_description"])}
  default_prompt: {json.dumps(spec["default_prompt"])}
policy:
  allow_implicit_invocation: false
'''


def router_text() -> str:
    # The router deliberately omits disable-model-invocation so /elr stays
    # model-invocable; only the per-stage wrappers are researcher-invoked.
    return '''---
name: "elr"
description: "Start a new project, adopt an existing one, show the menu of tools, resume, report status, or explain the empirical legal research pipeline. Use when the researcher says start, adopt, menu, tools, resume, continue, next, status, help, or tour, asks what ELARA can do, or asks which workflow stage to run."
---

# Route the empirical legal research workflow

1. Read `AGENTS.md`, `PIPELINE.md`, and `project/PROJECT_STATE.md` completely (its `usage` key
   records the usage mode: `pipeline`, or `tools` for specific tools; absent means `pipeline`),
   and `project/BOOTSTRAP.md` if it exists. Speak in plain language to a legal scholar who may
   never have used a terminal, and run every command yourself.
2. `help` or `tour`: without touching any file, give the orientation in
   `workflow/stages/00-initialize.md` (what ELARA does and does not do, the six steps, gates,
   the commands, the menu, the publication profile), say where this project stands, and stop.
   `status`: without touching any file, report the current stage and status, the usage mode,
   approvals and their basis (verified or researcher-asserted), active artifact versions, the
   last run, and outstanding researcher inputs, then stop.
3. `start` on an uninitialized template: read and follow `workflow/stages/00-initialize.md`,
   fresh path, beginning with its orientation and the usage-mode question (whole pipeline or
   specific tools). `adopt`, or an uninitialized template with existing materials (under
   `project/inputs/existing/`, listed in `project/BOOTSTRAP.md`, or described by the
   researcher): follow the same file's adoption path.
4. `menu` or `tools`, or a named stage or utility: present the menu in `PIPELINE.md` in plain
   language and run what the researcher picks. On an uninitialized template, Stage 00 runs
   first, from its orientation, with the tool as the aim (its two-question specific-tools
   setup). If the tool's prerequisites are not recorded, first satisfy them through Stage 00's
   adoption path (import what exists, record researcher-asserted approvals, note
   limitations), then run it; a utility never changes `current_stage`; an earlier stage runs
   as a versioned recovery route.
5. If state is `awaiting_approval` or `waiting_for_user`, report the exact gate or input and
   stop. Never infer approval from silence or from an earlier, different decision.
6. Otherwise (`resume`, `continue`, `next`): in `specific tools` mode (`usage: tools`), reopen
   the menu and offer to continue `current_stage` as one of the choices; in `pipeline` mode
   read the canonical file named by `current_stage`, verify its prerequisites (imported
   artifacts and researcher-asserted approvals recorded at adoption satisfy them), and follow
   it. If the required Plan or Goal mode is not active, give the researcher the exact mode
   command and stage invocation instead of imitating it.
7. When a stage ends with no gate or input pending, summarize plainly what was produced and
   what comes next, then offer it: the next stage in `pipeline` mode (run it on the
   researcher's agreement, in this session), the menu in `specific tools` mode. Agreement to
   continue is not gate approval. Run only one bounded stage at a time; never one Goal for
   the whole pipeline.
'''


def observation_skill_text(*, claude: bool) -> str:
    invocation = f"/{OBSERVATION_SKILL}" if claude else f"${OBSERVATION_SKILL}"
    platform = "Claude workflow" if claude else "Codex Goal"
    return f'''---
name: "{OBSERVATION_SKILL}"
description: "Fan out frozen empirical legal research coding or audit work with exactly one observation or unit per isolated subagent. Use during Stages 08, 11, 12, or 15 after the unit manifest, prompt, schema, retry rule, and output paths are fixed."
---

# Code observations with isolated subagents

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, and
   `workflow/shared/observation-fanout.md` completely.
2. Read the active canonical file under `workflow/stages/`; this skill implements its
   per-unit execution contract and never changes stage gates or frozen instruments.
3. Validate the immutable assignment manifest and its canonical visible-prompt and response-schema
   hashes before spawning anything. Give each fresh worker exactly one assignment and one unique
   return path; workers never edit shared files.
4. Require workers to send their return envelope through `python scripts/unit_fanout.py submit`;
   they do not write the worker-return path directly or expose substantive labels in receipts.
5. Use the {platform} adapter specified by the shared contract. If its required mode is not
   active, issue the exact handoff for `{invocation}` instead of imitating that mode.
6. Validate returns and update ledgers serially after each bounded wave. Resume from files,
   preserve every attempt, expose only operational progress, and reconcile before merging.
'''


def observation_openai_yaml() -> str:
    return '''interface:
  display_name: "ELARA Code Observations"
  short_description: "Code each observation in an isolated subagent"
  default_prompt: "Use $elr-code-observations on the frozen assignment manifest."
policy:
  allow_implicit_invocation: false
'''


def add_codex_policy(openai_yaml: Path, allow_implicit: bool) -> str:
    text = openai_yaml.read_text(encoding="utf-8") if openai_yaml.exists() else ""
    text = re.sub(r"\npolicy:\n(?:  .*\n?)*\Z", "\n", text.rstrip() + "\n")
    value = "true" if allow_implicit else "false"
    return text.rstrip() + f"\npolicy:\n  allow_implicit_invocation: {value}\n"


def expected_files(root: Path) -> dict[Path, str]:
    files: dict[Path, str] = {}
    codex_root = root / ".agents" / "skills"
    claude_root = root / ".claude" / "skills"

    files[codex_root / "elr" / "SKILL.md"] = router_text()
    files[claude_root / "elr" / "SKILL.md"] = router_text()
    files[codex_root / OBSERVATION_SKILL / "SKILL.md"] = observation_skill_text(
        claude=False
    )
    files[claude_root / OBSERVATION_SKILL / "SKILL.md"] = observation_skill_text(
        claude=True
    )
    files[codex_root / OBSERVATION_SKILL / "agents" / "openai.yaml"] = (
        observation_openai_yaml()
    )

    for path, meta, _body in load_stages(root):
        stage_id = meta["stage_id"]
        name = skill_name(stage_id)
        description = stage_description(meta["title"], stage_id)
        canonical = path.relative_to(root).as_posix()
        extra_read = MANUSCRIPT_EXTRA_READ if stage_id in MANUSCRIPT_STAGE_IDS else ""
        files[codex_root / name / "SKILL.md"] = wrapper_text(
            name, description, canonical, claude=False, extra_read=extra_read
        )
        files[claude_root / name / "SKILL.md"] = wrapper_text(
            name, description, canonical, claude=True, extra_read=extra_read
        )

    for name, spec in UTILITY_SKILLS.items():
        files[codex_root / name / "SKILL.md"] = utility_wrapper_text(name, spec, claude=False)
        files[claude_root / name / "SKILL.md"] = utility_wrapper_text(name, spec, claude=True)
        files[codex_root / name / "agents" / "openai.yaml"] = utility_openai_yaml(name, spec)

    return files


def sync(root: Path, *, check: bool) -> list[str]:
    problems: list[str] = []
    expected = expected_files(root)
    for path, content in expected.items():
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        if check:
            problems.append(f"out of sync: {path.relative_to(root)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")

    codex_root = root / ".agents" / "skills"
    for directory in sorted(p for p in codex_root.glob("elr*") if p.is_dir()):
        yaml_path = directory / "agents" / "openai.yaml"
        desired = add_codex_policy(yaml_path, directory.name == "elr")
        if yaml_path.exists() and yaml_path.read_text(encoding="utf-8") == desired:
            continue
        if check:
            problems.append(f"policy out of sync: {yaml_path.relative_to(root)}")
        else:
            yaml_path.parent.mkdir(parents=True, exist_ok=True)
            yaml_path.write_text(desired, encoding="utf-8", newline="\n")

    # Report elr* skill directories the generator no longer produces. Orphans are
    # never deleted automatically: they may hold researcher work or manual
    # experiments, so removal stays a deliberate human action. Skills with other
    # names belong to the researcher (the kit may be installed into their own
    # folder) and are not the kit's concern.
    for skills_root in (codex_root, root / ".claude" / "skills"):
        if not skills_root.is_dir():
            continue
        for directory in sorted(p for p in skills_root.glob("elr*") if p.is_dir()):
            if directory / "SKILL.md" in expected:
                continue
            relative = directory.relative_to(root).as_posix()
            if check:
                problems.append(f"orphan wrapper: {relative}")
            else:
                print(f"WARNING: orphan wrapper left in place (delete by hand if unwanted): {relative}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        root = repository_root(args.root) if args.root else repository_root()
        problems = sync(root, check=args.check)
    except FrontmatterError as exc:
        print(exc, file=sys.stderr)
        return 1
    if problems:
        print("\n".join(problems))
        return 1
    print("Skill wrappers are synchronized." if args.check else "Skill wrappers synchronized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
