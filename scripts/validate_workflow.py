"""Validate the canonical ELARA workflow and its generated agent wrappers."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from check_docs import validate_docs
from sync_skill_wrappers import sync
from workflow_lib import (
    INTERACTION_PROFILES,
    REQUIRED_STAGE_KEYS,
    REQUIRED_STAGE_SECTIONS,
    STATE_STATUSES,
    FrontmatterError,
    load_stages,
    parse_frontmatter,
    repository_root,
    skill_name,
)


EXPECTED_STAGE_IDS = [
    "00-initialize",
    "01-conceive",
    "02-preemption-review",
    "03-feasibility-audit",
    "04-methods-design",
    "05-codebook-and-schema",
    "06-data-authorization",
    "07-adversarial-review",
    "08-pilot",
    "09-freeze-and-preregister",
    "10-corpus-acquisition",
    "11-scale-up",
    "12-interpretive-verification",
    "13-human-validation",
    "14-analysis-and-correction",
    "15-robustness",
    "16-replication-package",
    "17-skeleton-draft",
    "18-integrate-manuscript",
    "19-cite-check",
    "20-revise-and-respond",
]

HARD_GATES = {
    "00-initialize": "project-charter-approval",
    "01-conceive": "project-selection",
    "02-preemption-review": "preemption-disposition",
    "03-feasibility-audit": "feasibility-go-no-go",
    "04-methods-design": "methods-plan-approval",
    "05-codebook-and-schema": "codebook-schema-approval",
    "06-data-authorization": "data-authorization",
    "07-adversarial-review": "design-freeze",
    "08-pilot": "pilot-acceptance",
    "09-freeze-and-preregister": "preregistration-confirmation",
    "10-corpus-acquisition": "material-corpus-deviation",
    "13-human-validation": "validation-disposition",
    "17-skeleton-draft": "skeleton-draft-approval",
    "18-integrate-manuscript": "manuscript-edit-permission",
    "20-revise-and-respond": "manuscript-edit-permission",
}

UNVERSIONED_OUTPUTS = {
    "project/PROJECT_STATE.md",
    "project/DECISIONS.md",
    "project/RUN_LEDGER.md",
    "project/DEVIATIONS.md",
}

# Optional state keys added after schema 1.0, and their allowed values.
OPTIONAL_STATE_KEYS = {"usage", "checkpoints"}
STATE_USAGES = {"pipeline", "tools"}
STATE_CHECKPOINTS = {"none", "stages", "plans", "all"}

# Every numeric guard below (int(stage_id[:2]) and friends) relies on this
# pattern having been checked first.
STAGE_ID_RE = re.compile(r"\d{2}-[a-z0-9-]+")

# required_inputs roots the researcher supplies rather than an earlier stage:
# raw inputs under project/inputs and the bare run-directory root.
RESEARCHER_SUPPLIED_INPUT_PREFIX = "project/inputs"
RESEARCHER_SUPPLIED_INPUT_ROOTS = {"project/runs/"}


def _require_type(
    errors: list[str], path: Path, key: str, value: object, expected: type
) -> None:
    if type(value) is not expected:  # bool is an int subclass; exactness is intentional.
        errors.append(f"{path}: {key} must be {expected.__name__}")


def validate_stage(
    root: Path,
    path: Path,
    meta: dict[str, object],
    body: str,
    known_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    keys = tuple(meta.keys())
    if set(keys) != set(REQUIRED_STAGE_KEYS):
        missing = sorted(set(REQUIRED_STAGE_KEYS) - set(keys))
        extra = sorted(set(keys) - set(REQUIRED_STAGE_KEYS))
        if missing:
            errors.append(f"{path}: missing frontmatter keys: {', '.join(missing)}")
        if extra:
            errors.append(f"{path}: unexpected frontmatter keys: {', '.join(extra)}")
        return errors

    stage_id = meta["stage_id"]
    _require_type(errors, path, "stage_id", stage_id, str)
    _require_type(errors, path, "title", meta["title"], str)
    _require_type(errors, path, "paper_steps", meta["paper_steps"], list)
    _require_type(errors, path, "core", meta["core"], bool)
    _require_type(errors, path, "interaction_profile", meta["interaction_profile"], str)
    _require_type(errors, path, "long_running", meta["long_running"], bool)
    if meta["goal_condition"] is not None:
        _require_type(errors, path, "goal_condition", meta["goal_condition"], str)
    for key in ("prerequisites", "required_inputs", "declared_outputs", "failure_routes"):
        _require_type(errors, path, key, meta[key], list)
    if meta["human_gate"] is not None and not isinstance(meta["human_gate"], str):
        errors.append(f"{path}: human_gate must be a quoted string or null")
    if meta["next_stage"] is not None and not isinstance(meta["next_stage"], str):
        errors.append(f"{path}: next_stage must be a quoted string or null")

    if not isinstance(stage_id, str):
        return errors
    if not STAGE_ID_RE.fullmatch(stage_id):
        errors.append(
            f"{path}: stage_id must be two digits, a hyphen, and a lowercase slug: {stage_id!r}"
        )
        return errors
    if path.stem != stage_id:
        errors.append(f"{path}: filename must match stage_id {stage_id}")
    if meta["interaction_profile"] not in INTERACTION_PROFILES:
        errors.append(f"{path}: invalid interaction_profile {meta['interaction_profile']}")
    expected_core = int(stage_id[:2]) <= 16
    if meta["core"] is not expected_core:
        errors.append(f"{path}: core must be {str(expected_core).lower()}")

    for key in ("paper_steps", "prerequisites", "required_inputs", "declared_outputs", "failure_routes"):
        if isinstance(meta[key], list):
            for item in meta[key]:
                if not isinstance(item, str) or not item:
                    errors.append(f"{path}: every {key} item must be a nonempty string")

    for key in ("prerequisites", "failure_routes"):
        for target in meta[key] if isinstance(meta[key], list) else []:
            if target not in known_ids:
                errors.append(f"{path}: unknown {key} target {target}")
    next_stage = meta["next_stage"]
    if next_stage is not None and next_stage not in known_ids:
        errors.append(f"{path}: unknown next_stage {next_stage}")
    outputs = meta["declared_outputs"] if isinstance(meta["declared_outputs"], list) else []
    if len(outputs) != len(set(item for item in outputs if isinstance(item, str))):
        errors.append(f"{path}: declared_outputs contains duplicates")
    for output in outputs:
        if not isinstance(output, str) or not output.startswith("project/"):
            errors.append(f"{path}: declared output must be under project/: {output!r}")
        elif (
            output not in UNVERSIONED_OUTPUTS
            and "_vNNN" not in output
            and "<run_id>" not in output
        ):
            errors.append(
                f"{path}: rerunnable output must be versioned or run-scoped: {output!r}"
            )

    expected_gate = HARD_GATES.get(stage_id)
    if meta["human_gate"] != expected_gate:
        errors.append(f"{path}: human_gate must be {expected_gate!r}")

    stage_number = int(stage_id[:2])
    if stage_number >= len(EXPECTED_STAGE_IDS):
        errors.append(f"{path}: stage number {stage_number} is outside the 00-20 pipeline")
        return errors
    if stage_number == 0:
        expected_prerequisites = []
    elif stage_number == 2:
        # Stage 01 is optional; Stage 02 may start from an initialized project
        # carrying a researcher-supplied, logged project-selection decision.
        expected_prerequisites = ["00-initialize"]
    else:
        expected_prerequisites = [EXPECTED_STAGE_IDS[stage_number - 1]]
    if meta["prerequisites"] != expected_prerequisites:
        errors.append(
            f"{path}: prerequisites must be the immediate prior stage {expected_prerequisites}"
        )
    expected_next = (
        EXPECTED_STAGE_IDS[stage_number + 1]
        if stage_number + 1 < len(EXPECTED_STAGE_IDS)
        else None
    )
    if meta["next_stage"] != expected_next:
        errors.append(f"{path}: next_stage must be {expected_next!r}")
    if not meta["failure_routes"]:
        errors.append(f"{path}: failure_routes must name at least one recovery stage")
    for target in meta["failure_routes"] if isinstance(meta["failure_routes"], list) else []:
        if (
            isinstance(target, str)
            and target in known_ids
            and STAGE_ID_RE.fullmatch(target)
            and int(target[:2]) > stage_number
        ):
            errors.append(f"{path}: failure route may not skip forward to {target}")
    if meta["interaction_profile"] == "normal" and meta["long_running"] is not False:
        errors.append(f"{path}: normal interaction stages cannot be long_running")
    if meta["long_running"] is True:
        condition = meta["goal_condition"]
        if not isinstance(condition, str) or not condition.strip():
            errors.append(f"{path}: long_running stages require a nonempty goal_condition")
        elif not condition.startswith("Run Stage "):
            errors.append(f"{path}: goal_condition must begin with 'Run Stage '")
    elif meta["goal_condition"] is not None:
        errors.append(f"{path}: bounded stages must set goal_condition to null")

    headings = set(re.findall(r"^## (.+)$", body, flags=re.MULTILINE))
    for section in REQUIRED_STAGE_SECTIONS:
        if section not in headings:
            errors.append(f"{path}: missing section '## {section}'")
    if "TODO" in body:
        errors.append(f"{path}: unresolved TODO")
    if "AGENTS.md" not in body or "PROJECT_STATE.md" not in body:
        errors.append(f"{path}: stage must route through AGENTS.md and PROJECT_STATE.md")
    if "workflow/shared/execution-control.md" not in body:
        errors.append(f"{path}: stage must route through the native plan/goal contract")
    if meta["long_running"] is True and "<goal_condition>" not in body:
        errors.append(f"{path}: long_running stage must use its exact goal_condition handoff")
    return errors


def validate_artifact_chain(loaded: list) -> list[str]:
    """Check that every path-shaped required input is produced by an earlier stage.

    A required_inputs item is path-shaped when it starts with ``project/`` and
    contains no whitespace; prose descriptions of researcher-supplied material
    are exempt, as are researcher-supplied roots (``project/inputs...`` and the
    bare ``project/runs/``). This catches misspelled or renamed artifact names
    that would otherwise strand a stage waiting on an input nothing produces.
    """

    errors: list[str] = []
    produced: set[str] = set()
    for path, meta, _body in loaded:
        inputs = meta.get("required_inputs")
        for item in inputs if isinstance(inputs, list) else []:
            if not isinstance(item, str) or not item.startswith("project/"):
                continue
            if re.search(r"\s", item):
                continue
            if item.startswith(RESEARCHER_SUPPLIED_INPUT_PREFIX):
                continue
            if item in RESEARCHER_SUPPLIED_INPUT_ROOTS:
                continue
            if item not in produced:
                errors.append(
                    f"{path}: required input {item!r} is not a declared output of any earlier stage"
                )
        outputs = meta.get("declared_outputs")
        produced.update(
            item for item in (outputs if isinstance(outputs, list) else []) if isinstance(item, str)
        )
    return errors


def validate_state(root: Path) -> list[str]:
    path = root / "project" / "PROJECT_STATE.md"
    if not path.exists():
        return [f"missing {path}"]
    meta, _body = parse_frontmatter(path)
    required = {
        "schema_version",
        "workflow_version",
        "project_slug",
        "current_stage",
        "status",
        "active_artifacts",
        "approvals",
        "outstanding_user_inputs",
        "last_run_id",
        "updated_at",
    }
    errors: list[str] = []
    # `usage` (schema 1.1) and `checkpoints` (schema 1.2) are optional so that
    # state files written under earlier schemas stay valid; absent means the
    # whole pipeline and no extra pauses.
    if not required <= set(meta) <= required | OPTIONAL_STATE_KEYS:
        errors.append(f"{path}: state keys do not match the public state contract")
    if "usage" in meta and meta["usage"] not in STATE_USAGES:
        errors.append(f"{path}: usage must be one of {sorted(STATE_USAGES)}, not {meta['usage']!r}")
    if "checkpoints" in meta and meta["checkpoints"] not in STATE_CHECKPOINTS:
        errors.append(
            f"{path}: checkpoints must be one of {sorted(STATE_CHECKPOINTS)}, not {meta['checkpoints']!r}"
        )
    if meta.get("status") not in STATE_STATUSES:
        errors.append(f"{path}: invalid status {meta.get('status')!r}")
    current_stage = meta.get("current_stage")
    if current_stage not in EXPECTED_STAGE_IDS:
        errors.append(f"{path}: unknown current_stage {current_stage!r}")
    if not isinstance(meta.get("active_artifacts"), dict):
        errors.append(f"{path}: active_artifacts must be an inline object")
    if not isinstance(meta.get("approvals"), dict):
        errors.append(f"{path}: approvals must be an inline object")
    if not isinstance(meta.get("outstanding_user_inputs"), list):
        errors.append(f"{path}: outstanding_user_inputs must be an inline array")
    elif not all(isinstance(item, str) and item for item in meta["outstanding_user_inputs"]):
        errors.append(f"{path}: every outstanding_user_inputs item must be a nonempty string")
    for key in ("schema_version", "workflow_version"):
        if not isinstance(meta.get(key), str) or not meta[key]:
            errors.append(f"{path}: {key} must be a nonempty quoted string")
    for key in ("project_slug", "last_run_id", "updated_at"):
        if meta.get(key) is not None and not isinstance(meta[key], str):
            errors.append(f"{path}: {key} must be a quoted string or null")

    # A null project slug identifies the untouched distribution template. Once
    # Stage 00 initializes a project, valid active states may route anywhere.
    if meta.get("project_slug") is None:
        fresh_expectations = {
            "current_stage": "00-initialize",
            "status": "ready",
            "active_artifacts": {},
            "approvals": {},
            "outstanding_user_inputs": [],
            "last_run_id": None,
            "updated_at": None,
        }
        for key, expected in fresh_expectations.items():
            if meta.get(key) != expected:
                errors.append(
                    f"{path}: uninitialized state requires {key}={expected!r}"
                )
    elif meta.get("status") == "running" and not meta.get("last_run_id"):
        errors.append(f"{path}: running state requires last_run_id")
    return errors


def validate_repository(root: Path) -> list[str]:
    errors: list[str] = []
    loaded = load_stages(root)
    ids = [meta.get("stage_id") for _path, meta, _body in loaded]
    if ids != EXPECTED_STAGE_IDS:
        errors.append(f"stage inventory mismatch: expected {EXPECTED_STAGE_IDS}, found {ids}")
    if len(ids) != len(set(ids)):
        errors.append("stage IDs must be unique")
    known = {item for item in ids if isinstance(item, str)}
    for path, meta, body in loaded:
        errors.extend(validate_stage(root, path, meta, body, known))

    numbered = [
        entry
        for entry in loaded
        if isinstance(entry[1].get("stage_id"), str)
        and STAGE_ID_RE.fullmatch(entry[1]["stage_id"])
    ]
    for prior, current in zip(numbered, numbered[1:]):
        prior_id = prior[1]["stage_id"]
        current_id = current[1]["stage_id"]
        if int(current_id[:2]) != int(prior_id[:2]) + 1:
            errors.append(f"non-sequential stage numbers: {prior_id}, {current_id}")

    errors.extend(validate_artifact_chain(loaded))
    errors.extend(validate_state(root))
    errors.extend(sync(root, check=True))
    errors.extend(validate_docs(root))

    agents = root / "AGENTS.md"
    if not agents.exists():
        errors.append("missing AGENTS.md")
    elif agents.stat().st_size > 32 * 1024:
        errors.append("AGENTS.md exceeds Codex's default 32 KiB project-guidance budget")
    claude = root / "CLAUDE.md"
    if not claude.exists() or not claude.read_text(encoding="utf-8").startswith("@AGENTS.md"):
        errors.append("CLAUDE.md must import AGENTS.md on its first line")

    # The kit README is README.md in a clone and ELARA_README.md in a project folder
    # that scripts/bootstrap.py installed into; either satisfies the check.
    if not any((root / name).exists() for name in ("ELARA_README.md", "README.md")):
        errors.append("missing ELARA_README.md or README.md")
    for required in (
        "PIPELINE.md",
        "workflow/shared/guardrails.md",
        "workflow/shared/artifact-contract.md",
        "workflow/shared/manuscript-editing-contract.md",
        "workflow/shared/fresh-review.md",
        "workflow/templates/publication_profile_template.md",
        "workflow/templates/skeleton_draft_template.md",
        "workflow/utilities/add-citations.md",
        "workflow/utilities/proofread.md",
        "workflow/utilities/apply-markup.md",
        "project/DECISIONS.md",
        "project/RUN_LEDGER.md",
        "project/DEVIATIONS.md",
        "project/inputs/README.md",
        "scripts/bootstrap.py",
        "scripts/doctor.py",
        "scripts/build_skeleton_draft.py",
    ):
        if not (root / required).exists():
            errors.append(f"missing {required}")

    for path in (root / ".agents" / "skills").glob("elr*/SKILL.md"):
        if "TODO" in path.read_text(encoding="utf-8"):
            errors.append(f"{path}: unresolved scaffold TODO")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    try:
        root = repository_root(args.root) if args.root else repository_root()
        errors = validate_repository(root)
    except (FrontmatterError, ValueError, UnicodeDecodeError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 1
    if errors:
        print("Workflow validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Workflow validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
