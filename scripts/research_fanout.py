"""Prepare and track one-assignment research fan-outs (searches, retrieval, cite-checks, reviews).

This module is the research counterpart of ``unit_fanout.py`` and is just as provider-neutral:
it never spawns an agent or calls a model. The host's own orchestrator launches one restricted
research worker per pending assignment — on Claude Code the kit's saved workflow
``.claude/workflows/elr-research-fanout.js``, on Codex the kit's custom sub-agent
``elr_research_worker`` (``.codex/agents/elr-research-worker.toml``) — and this controller fixes
the manifest, says what is still pending, and records launches, so that a fan-out resumes from
disk in any later session and no assignment is silently dropped.

Layout of one fan-out directory (always under the stage's run directory, never a session
scratchpad; a stage may run several fan-outs per run, one directory each):

    spec.json          written by the parent before ``prepare``: contract_version, fanout_id,
                       kind, time_box_minutes, max_attempts, assignments [{assignment_id, brief}]
    briefs/<id>.md     one brief per assignment, written by the parent before ``prepare``
    manifest.json      sealed by ``prepare``: one row per assignment with the brief's hash and
                       one unique return path; immutable afterwards
    manifest.csv       the same rows as CSV (for humans and CSV batch tools)
    seal.json          sha256 of manifest.json; ``status`` fails closed when it drifts
    returns/<id>.json  written incrementally by the worker: {"assignment_id", "complete", ...}
    attempts.jsonl     append-only launch rows written by ``status --record-launch``

Contract invariants:

- One assignment, one brief, one unique return path inside ``returns/``; identifiers are
  validated and duplicates refused before anything is written.
- Briefs and the manifest are hashed and sealed; ``status`` refuses drift.
- A return counts as complete only when it is a JSON object whose ``assignment_id`` matches
  and whose ``complete`` field is exactly ``true``; anything else is pending or invalid.
- Attempts are bounded: an assignment launched ``max_attempts`` times without completing is
  reported as ``exhausted`` and left out of the pending list unless the parent asks for it
  back with ``--include-exhausted`` (its decision, recorded in the ledger).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from unit_fanout import (
    FanoutError,
    _inside,
    _safe_identifier,
    atomic_json,
    load_json,
    sha256_file,
)

CONTRACT_VERSION = "1.0"
DEFAULT_TIME_BOX_MINUTES = 12
DEFAULT_MAX_ATTEMPTS = 3
FORBIDDEN_RETURN_NAMES = {
    "spec.json",
    "manifest.json",
    "manifest.csv",
    "seal.json",
    "attempts.jsonl",
}
MANIFEST_COLUMNS = ("position", "assignment_id", "kind", "brief_path", "brief_sha256", "return_path")


def _positive_int(value: Any, field: str, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise FanoutError(f"{field} must be a positive integer: {value!r}")
    return value


def _read_seal(fanout_dir: Path) -> dict[str, Any]:
    seal_path = fanout_dir / "seal.json"
    if not seal_path.is_file():
        raise FanoutError(f"fan-out directory has no seal.json (run prepare first): {fanout_dir}")
    seal = load_json(seal_path)
    if not isinstance(seal, dict) or not isinstance(seal.get("manifest_sha256"), str):
        raise FanoutError(f"seal.json is malformed: {seal_path}")
    return seal


def prepare(fanout_dir: Path) -> dict[str, Any]:
    """Validate spec.json and the briefs, then write and seal the immutable manifest."""
    fanout_dir = fanout_dir.resolve()
    spec_path = fanout_dir / "spec.json"
    if not spec_path.is_file():
        raise FanoutError(f"fan-out directory has no spec.json: {fanout_dir}")
    if (fanout_dir / "manifest.json").exists():
        raise FanoutError(f"fan-out directory is already prepared: {fanout_dir}")

    spec = load_json(spec_path)
    if not isinstance(spec, dict):
        raise FanoutError("spec.json must be a JSON object")
    if spec.get("contract_version") != CONTRACT_VERSION:
        raise FanoutError(f"contract_version must be {CONTRACT_VERSION!r}")
    fanout_id = _safe_identifier(spec.get("fanout_id"), "fanout_id")
    kind = _safe_identifier(spec.get("kind"), "kind")
    time_box = _positive_int(spec.get("time_box_minutes"), "time_box_minutes", DEFAULT_TIME_BOX_MINUTES)
    max_attempts = _positive_int(spec.get("max_attempts"), "max_attempts", DEFAULT_MAX_ATTEMPTS)
    assignments = spec.get("assignments")
    if not isinstance(assignments, list) or not assignments:
        raise FanoutError("assignments must be a nonempty list")

    briefs_dir = fanout_dir / "briefs"
    returns_dir = fanout_dir / "returns"
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_returns: set[Path] = set()
    for position, item in enumerate(assignments):
        if not isinstance(item, dict):
            raise FanoutError(f"assignment {position} must be an object")
        assignment_id = _safe_identifier(item.get("assignment_id"), "assignment_id")
        if assignment_id in seen_ids:
            raise FanoutError(f"duplicate assignment_id: {assignment_id}")
        seen_ids.add(assignment_id)
        raw_brief = item.get("brief")
        if not isinstance(raw_brief, str) or not raw_brief:
            raise FanoutError(f"assignment {assignment_id} has no brief path")
        brief_path = (fanout_dir / raw_brief).resolve()
        if not _inside(brief_path, briefs_dir):
            raise FanoutError(f"brief must live under briefs/: {assignment_id}: {raw_brief}")
        if not brief_path.is_file():
            raise FanoutError(f"brief does not exist: {brief_path}")
        return_path = (returns_dir / f"{assignment_id}.json").resolve()
        if not _inside(return_path, returns_dir) or return_path.name in FORBIDDEN_RETURN_NAMES:
            raise FanoutError(f"unsafe return path: {return_path}")
        if return_path in seen_returns:
            raise FanoutError(f"duplicate return path: {return_path}")
        seen_returns.add(return_path)
        rows.append(
            {
                "position": position,
                "assignment_id": assignment_id,
                "kind": kind,
                "brief_path": str(brief_path),
                "brief_sha256": sha256_file(brief_path),
                "return_path": str(return_path),
            }
        )

    returns_dir.mkdir(parents=True, exist_ok=True)
    if any(returns_dir.iterdir()):
        raise FanoutError(f"returns/ must be empty before prepare: {returns_dir}")
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "fanout_id": fanout_id,
        "kind": kind,
        "time_box_minutes": time_box,
        "max_attempts": max_attempts,
        "spec_sha256": sha256_file(spec_path),
        "expected_assignments": len(rows),
        "assignments": rows,
    }
    manifest_path = fanout_dir / "manifest.json"
    atomic_json(manifest_path, manifest)
    csv_path = fanout_dir / "manifest.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in MANIFEST_COLUMNS})
    atomic_json(fanout_dir / "seal.json", {"manifest_sha256": sha256_file(manifest_path)})
    return manifest


def verify_integrity(fanout_dir: Path) -> dict[str, Any]:
    """Load the manifest, failing closed on seal, spec, or brief drift."""
    fanout_dir = fanout_dir.resolve()
    manifest_path = fanout_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FanoutError(f"fan-out directory is not prepared (no manifest.json): {fanout_dir}")
    seal = _read_seal(fanout_dir)
    if sha256_file(manifest_path) != seal["manifest_sha256"]:
        raise FanoutError(f"manifest.json changed after sealing: {manifest_path}")
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("contract_version") != CONTRACT_VERSION:
        raise FanoutError(f"manifest.json is not a contract {CONTRACT_VERSION} manifest")
    spec_path = fanout_dir / "spec.json"
    if not spec_path.is_file() or sha256_file(spec_path) != manifest.get("spec_sha256"):
        raise FanoutError(f"spec.json is missing or changed after prepare: {spec_path}")
    rows = manifest.get("assignments")
    if not isinstance(rows, list) or len(rows) != manifest.get("expected_assignments"):
        raise FanoutError("manifest assignment rows do not match expected_assignments")
    for row in rows:
        brief_path = Path(row["brief_path"])
        if not brief_path.is_file() or sha256_file(brief_path) != row["brief_sha256"]:
            raise FanoutError(f"brief missing or changed after prepare: {brief_path}")
    return manifest


def _attempt_counts(fanout_dir: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    path = fanout_dir / "attempts.jsonl"
    if not path.is_file():
        return counts
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise FanoutError(f"attempts.jsonl line {number} is not JSON: {exc}") from exc
            if not isinstance(row, dict) or not isinstance(row.get("assignment_id"), str):
                raise FanoutError(f"attempts.jsonl line {number} is malformed")
            counts[row["assignment_id"]] += 1
    return counts


def _record_launches(fanout_dir: Path, launches: list[dict[str, Any]]) -> None:
    """Append one launch row per assignment; the file is append-only and fsynced."""
    if not launches:
        return
    path = fanout_dir / "attempts.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for launch in launches:
            handle.write(json.dumps(launch, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _classify_return(row: dict[str, Any]) -> tuple[str, str | None]:
    """Return (state, problem) for one assignment's return file, without reading findings."""
    return_path = Path(row["return_path"])
    if not return_path.is_file():
        return "missing", None
    try:
        returned = load_json(return_path)
    except FanoutError as exc:
        return "invalid", str(exc)
    if not isinstance(returned, dict):
        return "invalid", "return is not a JSON object"
    if returned.get("assignment_id") != row["assignment_id"]:
        return "invalid", "assignment_id in the return does not match the manifest"
    if returned.get("complete") is True:
        return "complete", None
    return "incomplete", None


def status(
    fanout_dir: Path,
    *,
    include_pending: bool = False,
    include_exhausted: bool = False,
    record_launch: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Report operational counts and, on request, the pending assignments to launch next.

    ``record_launch`` appends a launch row for every pending assignment this call returns, so a
    later ``status`` can bound attempts; it is meaningful only with ``include_pending``.
    """
    fanout_dir = fanout_dir.resolve()
    manifest = verify_integrity(fanout_dir)
    attempts = _attempt_counts(fanout_dir)
    max_attempts = int(manifest["max_attempts"])
    counts: Counter[str] = Counter()
    pending: list[dict[str, Any]] = []
    exhausted: list[str] = []
    invalid: list[dict[str, Any]] = []
    expected_returns = {Path(row["return_path"]).resolve() for row in manifest["assignments"]}
    for row in manifest["assignments"]:
        state, problem = _classify_return(row)
        counts[state] += 1
        if problem:
            invalid.append({"assignment_id": row["assignment_id"], "problem": problem})
        if state == "complete":
            continue
        used = attempts[row["assignment_id"]]
        if used >= max_attempts and not include_exhausted:
            exhausted.append(row["assignment_id"])
            continue
        pending.append(
            {
                "assignment_id": row["assignment_id"],
                "brief_path": row["brief_path"],
                "return_path": row["return_path"],
                "attempts_so_far": used,
            }
        )
    returns_dir = fanout_dir / "returns"
    stray = [
        str(path.resolve())
        for path in sorted(returns_dir.glob("*"))
        if path.is_file() and path.resolve() not in expected_returns
    ]
    if limit is not None:
        if limit < 1:
            raise FanoutError("limit must be a positive integer")
        pending = pending[:limit]

    result: dict[str, Any] = {
        "fanout_id": manifest["fanout_id"],
        "kind": manifest["kind"],
        "expected": manifest["expected_assignments"],
        "complete": counts["complete"],
        "incomplete": counts["incomplete"],
        "missing": counts["missing"],
        "invalid": counts["invalid"],
        "exhausted": len(exhausted),
        "pending": len(pending),
        "time_box_minutes": manifest["time_box_minutes"],
        "max_attempts": max_attempts,
        "seal": "verified",
        "invalid_returns": invalid,
        "stray_files": stray,
        "exhausted_assignments": exhausted,
    }
    if include_pending:
        result["pending_assignments"] = pending
        if record_launch:
            launched_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            _record_launches(
                fanout_dir,
                [
                    {
                        "assignment_id": item["assignment_id"],
                        "attempt": item["attempts_so_far"] + 1,
                        "launched_utc": launched_utc,
                    }
                    for item in pending
                ],
            )
            for item in pending:
                item["attempts_so_far"] += 1
            result["launches_recorded"] = len(pending)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="seal spec.json and the briefs into a manifest")
    prepare_parser.add_argument("--fanout-dir", type=Path, required=True)

    status_parser = subparsers.add_parser("status", help="operational counts; optionally the pending list")
    status_parser.add_argument("--fanout-dir", type=Path, required=True)
    status_parser.add_argument("--include-pending", action="store_true")
    status_parser.add_argument(
        "--include-exhausted",
        action="store_true",
        help="also list assignments that used up max_attempts (a parent decision to record)",
    )
    status_parser.add_argument(
        "--record-launch",
        action="store_true",
        help="append a launch row for every pending assignment returned (with --include-pending)",
    )
    status_parser.add_argument("--limit", type=int, default=None, help="return at most this many pending assignments")

    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = prepare(args.fanout_dir)
            result: dict[str, Any] = {
                "fanout_id": manifest["fanout_id"],
                "kind": manifest["kind"],
                "expected": manifest["expected_assignments"],
                "manifest": str((args.fanout_dir / "manifest.json").resolve()),
            }
        elif args.command == "status":
            result = status(
                args.fanout_dir,
                include_pending=args.include_pending,
                include_exhausted=args.include_exhausted,
                record_launch=args.record_launch,
                limit=args.limit,
            )
        else:  # argparse constrains the command; defensive fail-closed guard
            raise FanoutError(f"unsupported command: {args.command}")
    except FanoutError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
