"""Generate thin Codex and Claude skill wrappers from canonical stage metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from workflow_lib import FrontmatterError, load_stages, repository_root, skill_name


OBSERVATION_SKILL = "elr-code-observations"


def stage_description(title: str, stage_id: str) -> str:
    return (
        f"Run ELR stage {stage_id}: {title}. Use when this is the current stage in "
        "project/PROJECT_STATE.md or when the researcher explicitly requests this recovery stage."
    )


def wrapper_text(name: str, description: str, canonical: str, *, claude: bool) -> str:
    extra = "disable-model-invocation: true\n" if claude else ""
    return f'''---
name: {json.dumps(name)}
description: {json.dumps(description)}
{extra}---

# Run {name}

1. Read `AGENTS.md`, `project/PROJECT_STATE.md`, `workflow/shared/guardrails.md`, and
   `workflow/shared/artifact-contract.md` completely.
2. Read `{canonical}` completely and follow it as the single source of substantive
   instructions for this stage.
3. Confirm that the stage is current and its prerequisites and approvals are satisfied.
   If it is not current, stop unless the researcher explicitly authorized a recovery route.
4. Honor the stage's mode handoff. A skill cannot switch Plan or Goal mode by itself.
5. Do not cross the stage's human gate. Update state and append the run ledger only as the
   canonical stage directs.
'''


def router_text() -> str:
    # The router deliberately omits disable-model-invocation so /elr stays
    # model-invocable; only the per-stage wrappers are researcher-invoked.
    return '''---
name: "elr"
description: "Start, resume, or report status for the empirical legal research pipeline. Use when the researcher says start, resume, continue, next, status, or asks which workflow stage to run."
---

# Route the empirical legal research workflow

1. Read `AGENTS.md`, `PIPELINE.md`, and `project/PROJECT_STATE.md` completely.
2. If no initialized state exists, read and follow `workflow/stages/00-initialize.md`.
3. If state is `awaiting_approval` or `waiting_for_user`, report the exact gate or input and
   stop. Never infer approval from silence or from an earlier, different decision.
4. Otherwise read the canonical file named by `current_stage`, verify its prerequisites,
   and follow it. If the required Plan or Goal mode is not active, give the researcher the
   exact mode command and stage invocation instead of imitating that mode.
5. Run only one bounded stage at a time. Do not use one Goal for the whole pipeline.
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
        files[codex_root / name / "SKILL.md"] = wrapper_text(
            name, description, canonical, claude=False
        )
        files[claude_root / name / "SKILL.md"] = wrapper_text(
            name, description, canonical, claude=True
        )

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

    # Report skill directories the generator no longer produces. Orphans are
    # never deleted automatically: they may hold researcher work or manual
    # experiments, so removal stays a deliberate human action.
    for skills_root in (codex_root, root / ".claude" / "skills"):
        if not skills_root.is_dir():
            continue
        for directory in sorted(p for p in skills_root.iterdir() if p.is_dir()):
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
