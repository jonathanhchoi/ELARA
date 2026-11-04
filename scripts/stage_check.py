"""Report, mechanically, whether one stage is done.

    python scripts/stage_check.py --stage 08-pilot [--root <project folder>]

A long-running stage's completion condition is that this command prints
``"done": true``. It reads only the project's files: the stage's declared
outputs (``workflow/stages/<stage>.md``), ``project/PROJECT_STATE.md``, the
stage's latest run directory, and ``project/RUN_LEDGER.md``. It never changes
anything.

``done`` is true when the stage's result is one of:

- ``complete``: state has moved past the stage, every required output exists
  and is recorded in ``active_artifacts``, and the stage's gate (if it has one)
  is approved;
- ``awaiting_approval``: the stage is current with status
  ``awaiting_approval`` and every required output exists and is active, so the
  next step is the researcher's;
- ``failure_route``: the stage is current with status ``failed`` (its failure
  route is the next step);
- ``stopped``: the stage is current with status ``waiting_for_user`` (a
  section 11 stop condition is waiting for the researcher).

Otherwise ``done`` is false and ``missing``, ``not_active``, and ``problems``
say exactly what is left. An output written ``path (condition)`` in a stage's
declared outputs is conditional: it is reported but never required, except
that ``(after the <gate> gate)`` outputs are required once that gate is
approved. The exit status is 0 when done, 1 when not, and 2 on a usage error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from workflow_lib import FrontmatterError, load_stages, parse_frontmatter  # noqa: E402


PROJECT_LOGS = (
    "project/PROJECT_STATE.md",
    "project/DECISIONS.md",
    "project/RUN_LEDGER.md",
    "project/DEVIATIONS.md",
)
APPROVED = {"approved", "conditionally-approved"}
CONDITIONAL_GATES = {"material-corpus-deviation"}
AFTER_GATE = re.compile(r"^after the ([a-z0-9-]+) gate\b")
DONE_RESULTS = {"complete", "awaiting_approval", "failure_route", "stopped"}
RUNNER_STAGES = {"08-pilot", "11-scale-up", "12-interpretive-verification", "15-robustness"}


class CheckError(ValueError):
    """The command could not run (unknown stage, unreadable state)."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _find_stage(kit_root: Path, name: str) -> tuple[list[str], dict[str, Any]]:
    stages = load_stages(kit_root)
    ids = [meta["stage_id"] for _path, meta, _body in stages]
    wanted = name.strip()
    if re.fullmatch(r"\d{1,2}", wanted):
        wanted = f"{int(wanted):02d}"
        matches = [stage_id for stage_id in ids if stage_id.startswith(wanted + "-")]
    else:
        matches = [stage_id for stage_id in ids if stage_id == wanted]
    if len(matches) != 1:
        raise CheckError(f"unknown stage {name!r}; use a stage ID such as 08-pilot or its number")
    meta = next(meta for _path, meta, _body in stages if meta["stage_id"] == matches[0])
    return ids, meta


def split_output(item: str) -> tuple[str, str | None]:
    """Split ``path (condition)`` into the path and its condition (None if required)."""

    if " (" in item:
        path, condition = item.split(" (", 1)
        return path.strip(), condition.rstrip(")").strip()
    return item.strip(), None


def _active_paths(state: dict[str, Any]) -> list[tuple[str, str | None]]:
    """(normalized path, recorded sha256 or None) for every active artifact."""

    found: list[tuple[str, str | None]] = []
    active = state.get("active_artifacts") or {}
    if not isinstance(active, dict):
        return found
    for value in active.values():
        if isinstance(value, str):
            found.append((value.replace("\\", "/").rstrip("/"), None))
        elif isinstance(value, dict) and isinstance(value.get("path"), str):
            digest = value.get("sha256") if isinstance(value.get("sha256"), str) else None
            found.append((value["path"].replace("\\", "/").rstrip("/"), digest))
    return found


def _latest_run(project_root: Path, stage_id: str, last_run_id: Any) -> str | None:
    runs = project_root / "project" / "runs"
    if isinstance(last_run_id, str) and f"_{stage_id}_r" in last_run_id and (runs / last_run_id).is_dir():
        return last_run_id
    if not runs.is_dir():
        return None
    candidates = sorted(path.name for path in runs.iterdir() if path.is_dir() and f"_{stage_id}_r" in path.name)
    return candidates[-1] if candidates else None


def _exists(path: Path, directory: bool) -> bool:
    return path.is_dir() if directory else path.is_file()


def _check_output(
    project_root: Path,
    output: str,
    run_id: str | None,
    active: list[tuple[str, str | None]],
) -> tuple[str, str]:
    """Return (status, detail): ok, missing, not_active, problem, or unchecked."""

    directory = output.endswith("/")
    path = output.rstrip("/")
    if "<run_id>" in path:
        if run_id is None:
            return "missing", f"{output} (no run directory for this stage)"
        path = path.replace("<run_id>", run_id)
    if "<" in path or re.search(r"\s", path):
        return "unchecked", output
    if "vNNN" not in path:
        target = project_root / path
        return ("ok", path) if _exists(target, directory) else ("missing", path + ("/" if directory else ""))
    pattern = re.compile("^" + re.escape(path).replace("vNNN", r"v(\d{3,})") + "$")
    matches = [(item, digest) for item, digest in active if pattern.fullmatch(item)]
    if matches:
        item, digest = max(matches, key=lambda entry: int(pattern.fullmatch(entry[0]).group(1)))
        target = project_root / item
        if not _exists(target, directory):
            return "problem", f"{item} is recorded as active but does not exist"
        if digest and target.is_file() and _sha256(target) != digest:
            return "problem", f"{item} does not match the sha256 recorded in active_artifacts"
        return "ok", item
    parent = (project_root / path).parent
    name_pattern = re.compile("^" + re.escape(Path(path).name).replace("vNNN", r"v\d{3,}") + "$")
    on_disk = sorted(
        child.name for child in parent.iterdir() if name_pattern.fullmatch(child.name) and _exists(child, directory)
    ) if parent.is_dir() else []
    if on_disk:
        found = (Path(path).parent / on_disk[-1]).as_posix()
        return "not_active", found
    return "missing", output


def _receipt_problems(run_dir: Path) -> list[str]:
    """A coding-runner run must be closed and its outputs unchanged since closing."""

    if not (run_dir / "run_spec.json").is_file():
        return []
    receipt_path = run_dir / "close_receipt.json"
    if not receipt_path.is_file():
        return [f"run {run_dir.name} is not closed (run scripts/coding_run.py close)"]
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read {receipt_path}: {exc}"]
    problems = []
    if receipt.get("reconciles") is not True:
        problems.append(f"run {run_dir.name}: close receipt does not reconcile")
    for name, item in (receipt.get("outputs") or {}).items():
        path = Path(item.get("path", ""))
        if not path.is_file() or _sha256(path) != item.get("sha256"):
            problems.append(f"run {run_dir.name}: {name} output changed or missing since close ({path})")
    return problems


def check_stage(project_root: Path, stage: str, kit_root: Path | None = None) -> dict[str, Any]:
    project_root = project_root.resolve()
    kit_root = (kit_root or project_root).resolve()
    ids, meta = _find_stage(kit_root, stage)
    stage_id = meta["stage_id"]
    gate = meta.get("human_gate")
    state_path = project_root / "project" / "PROJECT_STATE.md"
    try:
        state, _body = parse_frontmatter(state_path)
    except (OSError, FrontmatterError) as exc:
        raise CheckError(f"cannot read project state: {exc}") from exc
    current = state.get("current_stage")
    status = state.get("status")
    approvals = state.get("approvals") if isinstance(state.get("approvals"), dict) else {}
    gate_record = approvals.get(gate) if gate else None
    gate_decision = gate_record.get("decision") if isinstance(gate_record, dict) else None
    run_id = _latest_run(project_root, stage_id, state.get("last_run_id"))

    problems: list[str] = []
    if current not in ids:
        problems.append(f"PROJECT_STATE.md current_stage {current!r} is not a canonical stage")
        result = "in_progress"
    elif ids.index(current) > ids.index(stage_id):
        result = "complete" if run_id or gate_decision else "not_run"
    elif current == stage_id:
        result = {
            "awaiting_approval": "awaiting_approval",
            "failed": "failure_route",
            "waiting_for_user": "stopped",
            "complete": "complete",
        }.get(status, "in_progress")
    else:
        result = "not_started"

    active = _active_paths(state)
    missing: list[str] = []
    not_active: list[str] = []
    conditional: list[dict[str, Any]] = []
    unchecked: list[str] = []
    checked = 0
    for item in meta.get("declared_outputs", []):
        output, condition = split_output(item)
        required = condition is None
        if condition:
            after = AFTER_GATE.match(condition)
            required = bool(after and isinstance(approvals.get(after.group(1)), dict)
                            and approvals[after.group(1)].get("decision") in APPROVED)
        outcome, detail = _check_output(project_root, output, run_id, active)
        if outcome == "unchecked":
            unchecked.append(item)
            continue
        if not required:
            conditional.append({"output": output, "condition": condition, "present": outcome == "ok"})
            continue
        checked += 1
        if outcome == "missing":
            missing.append(detail)
        elif outcome == "not_active":
            not_active.append(detail)
        elif outcome == "problem":
            problems.append(detail)

    if run_id:
        run_dir = project_root / "project" / "runs" / run_id
        ledger = project_root / "project" / "RUN_LEDGER.md"
        if not ledger.is_file() or run_id not in ledger.read_text(encoding="utf-8-sig", errors="replace"):
            problems.append(f"run {run_id} has no entry in project/RUN_LEDGER.md")
        if stage_id in RUNNER_STAGES:
            problems.extend(_receipt_problems(run_dir))
    if result == "complete" and gate and gate not in CONDITIONAL_GATES and gate_decision not in APPROVED:
        problems.append(f"state has moved past {stage_id} but the {gate} gate is not approved")

    outputs_ok = not missing and not not_active and not problems
    if result in {"failure_route", "stopped"}:
        done = True
    elif result in {"complete", "awaiting_approval"}:
        done = outputs_ok
    else:
        done = False
    return {
        "stage": stage_id,
        "done": done,
        "result": result,
        "state": {
            "current_stage": current,
            "status": status,
            "outstanding_user_inputs": len(state.get("outstanding_user_inputs") or []),
        },
        "gate": {"id": gate, "decision": gate_decision} if gate else None,
        "run_id": run_id,
        "required_outputs_checked": checked,
        "missing": missing,
        "not_active": not_active,
        "problems": problems,
        "conditional": conditional,
        "unchecked": unchecked,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--stage", required=True, help="stage ID (08-pilot) or number (8)")
    parser.add_argument("--root", type=Path, default=Path("."), help="project folder (default: current)")
    parser.add_argument("--kit-root", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        report = check_stage(args.root, args.stage, args.kit_root)
    except CheckError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["done"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
