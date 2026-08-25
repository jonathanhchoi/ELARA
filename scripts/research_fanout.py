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
    manifest.json      sealed by ``prepare``: one row per allowed attempt with the brief's hash,
                       attempt number, and unique return path; immutable afterwards
    manifest.csv       the same attempt rows as CSV (for audit and parent tooling; it is not a
                       dispatch list because it includes unused retry slots)
    seal.json          sha256 of manifest.json; ``status`` fails closed when it drifts
    returns/<id>__attempt-NNN.json
                       written incrementally by one worker: {"assignment_id", "attempt",
                       "complete", ...}; prior attempts are never overwritten
    attempts.jsonl     append-only launch rows written by ``status --record-launch``
    dispositions.jsonl append-only parent judgments that a launched attempt is unusable or failed

Contract invariants:

- One assignment, one brief, and one unique return path per allowed attempt inside ``returns/``;
  identifiers and attempt numbers are validated and duplicates refused before anything is written.
- Briefs and the manifest are hashed and sealed; ``status`` refuses drift.
- A return counts as complete only when it is a JSON object whose ``assignment_id`` and ``attempt``
  match and whose ``complete`` field is exactly ``true``. The parent may record a stage-schema
  rejection without changing that raw file; the next attempt then receives a different path.
- Attempts are bounded: an assignment launched ``max_attempts`` times without completing is
  reported as ``exhausted`` and never put back on the pending list. ``--include-exhausted`` adds
  diagnostics; additional work requires a new explicitly versioned fan-out wave.
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
MANIFEST_FORMAT = "1.1"
DEFAULT_TIME_BOX_MINUTES = 12
DEFAULT_MAX_ATTEMPTS = 3
FORBIDDEN_RETURN_NAMES = {
    "spec.json",
    "manifest.json",
    "manifest.csv",
    "seal.json",
    "attempts.jsonl",
    "dispositions.jsonl",
}
MANIFEST_COLUMNS = (
    "position",
    "assignment_id",
    "attempt",
    "kind",
    "brief_path",
    "brief_sha256",
    "return_path",
)


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
        brief_sha256 = sha256_file(brief_path)
        for attempt in range(1, max_attempts + 1):
            return_path = (returns_dir / f"{assignment_id}__attempt-{attempt:03d}.json").resolve()
            if not _inside(return_path, returns_dir) or return_path.name in FORBIDDEN_RETURN_NAMES:
                raise FanoutError(f"unsafe return path: {return_path}")
            if return_path in seen_returns:
                raise FanoutError(f"duplicate return path: {return_path}")
            seen_returns.add(return_path)
            rows.append(
                {
                    "position": position,
                    "assignment_id": assignment_id,
                    "attempt": attempt,
                    "kind": kind,
                    "brief_path": str(brief_path),
                    "brief_sha256": brief_sha256,
                    "return_path": str(return_path),
                }
            )

    returns_dir.mkdir(parents=True, exist_ok=True)
    if any(returns_dir.iterdir()):
        raise FanoutError(f"returns/ must be empty before prepare: {returns_dir}")
    manifest = {
        "contract_version": CONTRACT_VERSION,
        "manifest_format": MANIFEST_FORMAT,
        "fanout_id": fanout_id,
        "kind": kind,
        "time_box_minutes": time_box,
        "max_attempts": max_attempts,
        "spec_sha256": sha256_file(spec_path),
        "expected_assignments": len(seen_ids),
        "expected_attempts": len(rows),
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
    if not isinstance(rows, list):
        raise FanoutError("manifest assignments must be a list")
    modern = manifest.get("manifest_format") == MANIFEST_FORMAT
    expected_rows = manifest.get("expected_attempts") if modern else manifest.get("expected_assignments")
    if len(rows) != expected_rows:
        raise FanoutError("manifest rows do not match their declared denominator")
    seen_attempts: set[tuple[str, int]] = set()
    seen_returns: set[Path] = set()
    assignment_attempts: dict[str, set[int]] = {}
    for row in rows:
        brief_path = Path(row["brief_path"])
        if not brief_path.is_file() or sha256_file(brief_path) != row["brief_sha256"]:
            raise FanoutError(f"brief missing or changed after prepare: {brief_path}")
        assignment_id = _safe_identifier(row.get("assignment_id"), "assignment_id")
        attempt = row.get("attempt", 1)
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise FanoutError(f"manifest attempt is invalid: {assignment_id}: {attempt!r}")
        key = (assignment_id, attempt)
        if key in seen_attempts:
            raise FanoutError(f"duplicate manifest attempt: {assignment_id} attempt {attempt}")
        seen_attempts.add(key)
        assignment_attempts.setdefault(assignment_id, set()).add(attempt)
        return_path = Path(row["return_path"]).resolve()
        if not _inside(return_path, fanout_dir / "returns") or return_path in seen_returns:
            raise FanoutError(f"unsafe or duplicate manifest return path: {return_path}")
        seen_returns.add(return_path)
    if len(assignment_attempts) != manifest.get("expected_assignments"):
        raise FanoutError("manifest assignment IDs do not match expected_assignments")
    if modern:
        expected_attempt_numbers = set(range(1, int(manifest["max_attempts"]) + 1))
        for assignment_id, attempts in assignment_attempts.items():
            if attempts != expected_attempt_numbers:
                raise FanoutError(f"manifest attempts are incomplete for {assignment_id}: {sorted(attempts)}")
    return manifest


def _attempt_rows(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for source_row in manifest["assignments"]:
        row = dict(source_row)
        row.setdefault("attempt", 1)
        grouped.setdefault(row["assignment_id"], []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: item["attempt"])
    return grouped


def _launches(fanout_dir: Path, manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped_rows = _attempt_rows(manifest)
    row_index = {
        (row["assignment_id"], row["attempt"]): row
        for rows in grouped_rows.values()
        for row in rows
    }
    launches: dict[str, list[dict[str, Any]]] = {assignment_id: [] for assignment_id in grouped_rows}
    path = fanout_dir / "attempts.jsonl"
    if not path.is_file():
        return launches
    seen: set[tuple[str, int]] = set()
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
            assignment_id = row["assignment_id"]
            if assignment_id not in grouped_rows:
                raise FanoutError(f"attempts.jsonl line {number} names an unknown assignment")
            attempt = row.get("attempt")
            if attempt is None and manifest.get("manifest_format") != MANIFEST_FORMAT:
                attempt = len(launches[assignment_id]) + 1
            if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
                raise FanoutError(f"attempts.jsonl line {number} has an invalid attempt")
            key = (assignment_id, attempt)
            expected_row = row_index.get(key)
            if expected_row is None:
                if manifest.get("manifest_format") != MANIFEST_FORMAT:
                    raise FanoutError(
                        "legacy research fan-out cannot allocate an immutable retry path; "
                        "prepare a new fan-out directory"
                    )
                raise FanoutError(f"attempts.jsonl line {number} exceeds the sealed retry policy")
            if key in seen:
                raise FanoutError(f"duplicate launch record: {assignment_id} attempt {attempt}")
            seen.add(key)
            if row.get("return_path") not in (None, expected_row["return_path"]):
                raise FanoutError(f"attempts.jsonl line {number} has the wrong return path")
            normalized = dict(row)
            normalized["attempt"] = attempt
            normalized["return_path"] = expected_row["return_path"]
            launches[assignment_id].append(normalized)
    for assignment_id, rows in launches.items():
        rows.sort(key=lambda item: item["attempt"])
        actual = [item["attempt"] for item in rows]
        if actual != list(range(1, len(rows) + 1)):
            raise FanoutError(f"launch attempts are not contiguous for {assignment_id}: {actual}")
    return launches


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


def _dispositions(fanout_dir: Path, manifest: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
    expected = {
        (row["assignment_id"], row.get("attempt", 1)): row for row in manifest["assignments"]
    }
    dispositions: dict[tuple[str, int], dict[str, Any]] = {}
    path = fanout_dir / "dispositions.jsonl"
    if not path.is_file():
        return dispositions
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise FanoutError(f"dispositions.jsonl line {number} is not JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise FanoutError(f"dispositions.jsonl line {number} is malformed")
            key = (row.get("assignment_id"), row.get("attempt"))
            if key not in expected:
                raise FanoutError(f"dispositions.jsonl line {number} names an unknown attempt")
            if key in dispositions:
                raise FanoutError(f"duplicate disposition: {key[0]} attempt {key[1]}")
            if row.get("terminal") not in {"failed", "unusable"}:
                raise FanoutError(f"dispositions.jsonl line {number} has an invalid terminal status")
            if not isinstance(row.get("reason"), str) or not row["reason"].strip():
                raise FanoutError(f"dispositions.jsonl line {number} has no reason")
            return_path = Path(expected[key]["return_path"])
            if row.get("return_path") != str(return_path):
                raise FanoutError(f"dispositions.jsonl line {number} has the wrong return path")
            if not isinstance(row.get("recorded_utc"), str) or not row["recorded_utc"]:
                raise FanoutError(f"dispositions.jsonl line {number} has no timestamp")
            recorded_hash = row.get("return_sha256")
            if recorded_hash is not None:
                if not return_path.is_file() or sha256_file(return_path) != recorded_hash:
                    raise FanoutError(f"disposed return changed after disposition: {return_path}")
            elif return_path.exists():
                raise FanoutError(f"a return appeared after its missing attempt was disposed: {return_path}")
            dispositions[key] = row
    return dispositions


def _classify_return(row: dict[str, Any], *, require_attempt: bool) -> tuple[str, str | None]:
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
    if require_attempt and returned.get("attempt") != row["attempt"]:
        return "invalid", "attempt in the return does not match the manifest"
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
    grouped_rows = _attempt_rows(manifest)
    launches = _launches(fanout_dir, manifest)
    dispositions = _dispositions(fanout_dir, manifest)
    max_attempts = int(manifest["max_attempts"])
    counts: Counter[str] = Counter()
    pending: list[dict[str, Any]] = []
    exhausted: list[str] = []
    invalid: list[dict[str, Any]] = []
    attempt_counts: Counter[str] = Counter()
    expected_returns = {Path(row["return_path"]).resolve() for row in manifest["assignments"]}
    ordered_assignments = sorted(grouped_rows, key=lambda item: grouped_rows[item][0]["position"])
    exhausted_details: list[dict[str, Any]] = []
    for assignment_id in ordered_assignments:
        rows = grouped_rows[assignment_id]
        row_by_attempt = {row["attempt"]: row for row in rows}
        launched = launches[assignment_id]
        state = "missing"
        problem = None
        observed_invalid: list[dict[str, Any]] = []
        for launch in launched:
            attempt = launch["attempt"]
            row = row_by_attempt[attempt]
            disposition = dispositions.get((assignment_id, attempt))
            if disposition is not None:
                attempt_state = disposition["terminal"]
                attempt_problem = disposition["reason"]
            else:
                attempt_state, attempt_problem = _classify_return(
                    row, require_attempt=manifest.get("manifest_format") == MANIFEST_FORMAT
                )
            attempt_counts["attempted"] += 1
            if attempt_state == "complete":
                attempt_counts["succeeded"] += 1
            elif attempt_state in {"failed", "unusable"}:
                attempt_counts[attempt_state] += 1
            else:
                attempt_counts["outstanding"] += 1
            if attempt_state == "complete":
                state = "complete"
                problem = None
                break
            state = attempt_state
            problem = attempt_problem
            if attempt_state == "invalid":
                observed_invalid.append(
                    {"assignment_id": assignment_id, "attempt": attempt, "problem": attempt_problem}
                )
        invalid.extend(observed_invalid)
        counts[state] += 1
        if state == "complete":
            continue
        used = len(launched)
        if used >= max_attempts:
            exhausted.append(assignment_id)
            exhausted_details.append(
                {
                    "assignment_id": assignment_id,
                    "attempts_used": used,
                    "terminal_state": state,
                    "problem": problem,
                }
            )
            continue
        if used and (assignment_id, used) not in dispositions:
            # A launched attempt is still live until the parent accepts its complete return or
            # records a failed/unusable disposition. Never launch a retry merely because a worker
            # is still writing, was interrupted, or produced an operationally invalid file.
            continue
        next_attempt = used + 1
        row = row_by_attempt.get(next_attempt)
        if row is None:
            raise FanoutError(
                "legacy research fan-out cannot allocate an immutable retry path; "
                "prepare a new fan-out directory"
            )
        pending.append(
            {
                "assignment_id": assignment_id,
                "brief_path": row["brief_path"],
                "return_path": row["return_path"],
                "attempts_so_far": used,
                "attempt": next_attempt,
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
        "failed_assignments": counts["failed"],
        "unusable_assignments": counts["unusable"],
        "exhausted": len(exhausted),
        "pending": len(pending),
        "time_box_minutes": manifest["time_box_minutes"],
        "max_attempts": max_attempts,
        "seal": "verified",
        "invalid_returns": invalid,
        "stray_files": stray,
        "exhausted_assignments": exhausted,
        "attempt_counts": {
            "attempted": attempt_counts["attempted"],
            "succeeded": attempt_counts["succeeded"],
            "failed": attempt_counts["failed"],
            "unusable": attempt_counts["unusable"],
            "outstanding": attempt_counts["outstanding"],
        },
    }
    if include_exhausted:
        result["exhausted_attempts"] = exhausted_details
    if include_pending:
        result["pending_assignments"] = pending
        if record_launch:
            launched_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            _record_launches(
                fanout_dir,
                [
                    {
                        "assignment_id": item["assignment_id"],
                        "attempt": item["attempt"],
                        "return_path": item["return_path"],
                        "launched_utc": launched_utc,
                    }
                    for item in pending
                ],
            )
            for item in pending:
                item["attempts_so_far"] = item["attempt"]
            result["attempt_counts"]["attempted"] += len(pending)
            result["attempt_counts"]["outstanding"] += len(pending)
            result["launches_recorded"] = len(pending)
    return result


def record_disposition(
    fanout_dir: Path,
    *,
    assignment_id: str,
    attempt: int,
    terminal: str,
    reason: str,
) -> dict[str, Any]:
    """Record a parent's terminal rejection without changing the worker's raw return."""
    fanout_dir = fanout_dir.resolve()
    manifest = verify_integrity(fanout_dir)
    grouped_rows = _attempt_rows(manifest)
    assignment_id = _safe_identifier(assignment_id, "assignment_id")
    if assignment_id not in grouped_rows:
        raise FanoutError(f"unknown assignment_id: {assignment_id}")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        raise FanoutError(f"attempt must be a positive integer: {attempt!r}")
    if terminal not in {"failed", "unusable"}:
        raise FanoutError("terminal must be 'failed' or 'unusable'")
    if not isinstance(reason, str) or not reason.strip():
        raise FanoutError("reason must be nonempty")
    row = next((item for item in grouped_rows[assignment_id] if item["attempt"] == attempt), None)
    if row is None:
        raise FanoutError(f"attempt exceeds the sealed retry policy: {assignment_id} attempt {attempt}")
    launches = _launches(fanout_dir, manifest)
    if attempt not in {item["attempt"] for item in launches[assignment_id]}:
        raise FanoutError(f"attempt was not launched: {assignment_id} attempt {attempt}")
    existing = _dispositions(fanout_dir, manifest)
    if (assignment_id, attempt) in existing:
        raise FanoutError(f"attempt already has a disposition: {assignment_id} attempt {attempt}")
    return_path = Path(row["return_path"])
    if terminal == "unusable" and not return_path.is_file():
        raise FanoutError(f"cannot mark a missing return unusable: {return_path}")
    disposition = {
        "assignment_id": assignment_id,
        "attempt": attempt,
        "terminal": terminal,
        "reason": reason.strip(),
        "return_path": str(return_path),
        "return_sha256": sha256_file(return_path) if return_path.is_file() else None,
        "recorded_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    path = fanout_dir / "dispositions.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(disposition, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return disposition


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
        help="include diagnostic details for assignments that used all sealed attempts",
    )
    status_parser.add_argument(
        "--record-launch",
        action="store_true",
        help="append a launch row for every pending assignment returned (with --include-pending)",
    )
    status_parser.add_argument("--limit", type=int, default=None, help="return at most this many pending assignments")

    disposition_parser = subparsers.add_parser(
        "record-disposition", help="record a failed or unusable attempt without overwriting its return"
    )
    disposition_parser.add_argument("--fanout-dir", type=Path, required=True)
    disposition_parser.add_argument("--assignment-id", required=True)
    disposition_parser.add_argument("--attempt", type=int, required=True)
    disposition_parser.add_argument("--terminal", choices=("failed", "unusable"), required=True)
    disposition_parser.add_argument("--reason", required=True)

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
        elif args.command == "record-disposition":
            result = record_disposition(
                args.fanout_dir,
                assignment_id=args.assignment_id,
                attempt=args.attempt,
                terminal=args.terminal,
                reason=args.reason,
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
