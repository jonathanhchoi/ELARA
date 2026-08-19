"""Prepare, validate, retry, resume, and merge one-unit subagent assignments.

This module is deliberately provider-neutral. It never spawns an agent or calls a model.
Claude workflows and Codex sub-agents consume the same immutable assignment files and write
one return file per attempt; the parent keeps the host-native stage plan and goal, and this
script is the serial controller around the workers.

Contract invariants:

- Hash-sealing: ``prepare`` seals ``run_manifest.json`` in ``run_seal.json`` and
  ``verify_run_integrity`` fails closed when a sealed manifest changes. Run directories
  created by older kit versions have no seal and remain readable (reported as
  ``absent_legacy_run``).
- Blinding: status output is operational only, and validator error strings are
  sanitized so label values never leak.
- Strict submission: ``submit`` validates a worker envelope before creating its
  assigned return path and refuses every overwrite. Workers do not need to edit
  the shared run directory directly.
- Retry policy: ``retry`` issues the one linked second attempt (at most
  ``MAX_ATTEMPTS`` = 2 attempts per slot) and archives the superseded return for audit.
- Section 10 reconciliation: ``merge`` writes a ``merge_receipt.json`` so merged counts and
  hashes can be re-verified before unblinding.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "1.0"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
ATTEMPT_SUFFIX = re.compile(r"^(?P<base>.+?)-attempt(?P<number>\d{3,})$")
MAX_ATTEMPTS = 2
MAX_SUBMISSION_BYTES = 10 * 1024 * 1024
SUCCESS_STATUS = "succeeded"
FAILURE_STATUSES = {
    "schema_failed",
    "quote_failed",
    "refused",
    "unreadable",
    "wrong_document",
    "exhausted_retry",
    "worker_error",
}
TERMINAL_STATUSES = {SUCCESS_STATUS, *FAILURE_STATUSES}
FORBIDDEN_RETURN_NAMES = {
    "PROJECT_STATE.md",
    "RUN_LEDGER.md",
    "DECISIONS.md",
    "DEVIATIONS.md",
    "run_manifest.json",
    "run_seal.json",
    "merge_receipt.json",
    "unit_ledger.jsonl",
    "coding_dataset.jsonl",
}
SEAL_ABSENT = "absent_legacy_run"
SEAL_VERIFIED = "verified"


class FanoutError(ValueError):
    """A fail-closed contract or reconciliation error."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FanoutError(f"cannot read valid JSON from {path}: {exc}") from exc


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _safe_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise FanoutError(f"{field} must match {SAFE_ID.pattern}: {value!r}")
    return value


def _safe_reason(value: Any) -> str:
    """Validate an audit reason string recorded on a superseded row.

    Kept deliberately narrow: a short, single-line, printable label such as
    ``parse_failure: $.rationale violates maxLength``. It is an audit note, never a
    substantive coding outcome, so it must not carry a label value or newline.
    """
    if not isinstance(value, str):
        raise FanoutError(f"reason must be a string: {value!r}")
    reason = value.strip()
    if not reason or len(reason) > 200 or any(ch in reason for ch in "\r\n\t"):
        raise FanoutError(
            "reason must be a non-empty single-line string of at most 200 characters"
        )
    return reason


def _return_contract() -> dict[str, Any]:
    return {
        "required": [
            "contract_version",
            "assignment_id",
            "unit_id",
            "attempt",
            "status",
            "result",
            "error",
            "provenance",
        ],
        "terminal_statuses": sorted(TERMINAL_STATUSES),
        "substantive_result_only_when": SUCCESS_STATUS,
    }


def _read_seal(run_dir: Path) -> dict[str, Any] | None:
    """Load run_seal.json if present; fail closed if it is not a JSON object."""
    seal_path = run_dir / "run_seal.json"
    if not seal_path.is_file():
        return None
    seal = load_json(seal_path)
    if not isinstance(seal, dict):
        raise FanoutError(f"run seal is not a JSON object: {seal_path}")
    return seal


def _write_seal(run_dir: Path) -> None:
    """Seal the current run manifest under the shared fan-out contract.

    Foreign seal keys written by wrapping drivers are preserved; only
    ``run_manifest_sha256`` is set here.
    """
    seal_path = run_dir / "run_seal.json"
    seal: dict[str, Any] = {}
    if seal_path.is_file():
        existing = _read_seal(run_dir)
        if existing is not None:
            seal = existing
    seal["run_manifest_sha256"] = sha256_file(run_dir / "run_manifest.json")
    atomic_json(seal_path, seal)


def _seal_state(run_dir: Path) -> str:
    """Report the fanout-layer seal state without re-verifying it."""
    seal = _read_seal(run_dir)
    if seal is None or "run_manifest_sha256" not in seal:
        return SEAL_ABSENT
    return SEAL_VERIFIED


def _validate_result(schema_path: Path, result: Any) -> list[str]:
    """Validate a worker result and return blinded messages only.

    Validator error strings are sanitized so label values do not leak. Messages carry only
    the JSON path and the failed validator keyword, never instance values or enum contents.
    """
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - environment-dependent guard
        raise FanoutError("install jsonschema to validate worker results") from exc
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema)
    messages: list[str] = []
    for error in validator.iter_errors(result):
        location = "/".join(str(part) for part in error.absolute_path)
        location = f"result/{location}" if location else "result"
        messages.append(f"invalid at {location}: {error.validator} constraint failed")
    return sorted(messages)


def prepare(spec_path: Path, run_dir: Path) -> dict[str, Any]:
    """Freeze a run directory and seal its manifest."""
    spec_path = spec_path.resolve()
    run_dir = run_dir.resolve()
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FanoutError(f"run directory is not empty: {run_dir}")

    spec = load_json(spec_path)
    if not isinstance(spec, dict):
        raise FanoutError("run specification must be a JSON object")
    if spec.get("contract_version") != CONTRACT_VERSION:
        raise FanoutError(f"contract_version must be {CONTRACT_VERSION!r}")
    run_id = _safe_identifier(spec.get("run_id"), "run_id")
    assignment_kind = _safe_identifier(spec.get("assignment_kind"), "assignment_kind")

    frozen_inputs = spec.get("frozen_inputs")
    if not isinstance(frozen_inputs, list) or not frozen_inputs:
        raise FanoutError("frozen_inputs must be a nonempty list")
    resolved_inputs: list[dict[str, str]] = []
    roles: set[str] = set()
    for item in frozen_inputs:
        if not isinstance(item, dict):
            raise FanoutError("each frozen input must be an object")
        role = _safe_identifier(item.get("role"), "frozen input role")
        if role in roles:
            raise FanoutError(f"duplicate frozen input role: {role}")
        roles.add(role)
        raw_path = item.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            raise FanoutError(f"frozen input {role} has no path")
        source = (spec_path.parent / raw_path).resolve()
        if not source.is_file():
            raise FanoutError(f"frozen input does not exist: {source}")
        actual_hash = sha256_file(source)
        declared_hash = item.get("sha256")
        if declared_hash is not None and declared_hash != actual_hash:
            raise FanoutError(f"frozen input hash mismatch for {role}: {source}")
        resolved_inputs.append(
            {"role": role, "path": str(source), "sha256": actual_hash}
        )
    if "result_schema" not in roles:
        raise FanoutError("frozen_inputs must contain the result_schema role")

    units = spec.get("units")
    if not isinstance(units, list) or not units:
        raise FanoutError("units must be a nonempty list")

    # Validate the complete roster before creating the run directory so a duplicate or
    # malformed late row cannot leave a misleading partially prepared run.
    preflight_ids: set[str] = set()
    for position, unit in enumerate(units):
        if not isinstance(unit, dict):
            raise FanoutError(f"unit {position} must be an object")
        _safe_identifier(unit.get("unit_id"), "unit_id")
        assignment_id = _safe_identifier(
            unit.get("assignment_id", unit.get("unit_id")), "assignment_id"
        )
        if assignment_id in preflight_ids:
            raise FanoutError(f"duplicate assignment_id: {assignment_id}")
        preflight_ids.add(assignment_id)
        attempt = unit.get("attempt", 1)
        if not isinstance(attempt, int) or attempt < 1:
            raise FanoutError(f"attempt must be a positive integer: {assignment_id}")
        if not isinstance(unit.get("payload"), dict):
            raise FanoutError(f"payload must be an object: {assignment_id}")

    run_dir.mkdir(parents=True, exist_ok=True)
    assignments_dir = run_dir / "assignments"
    returns_dir = run_dir / "worker_returns"
    assignments_dir.mkdir()
    returns_dir.mkdir()
    assignment_rows: list[dict[str, Any]] = []
    seen_assignments: set[str] = set()
    seen_returns: set[Path] = set()
    for position, unit in enumerate(units):
        if not isinstance(unit, dict):
            raise FanoutError(f"unit {position} must be an object")
        unit_id = _safe_identifier(unit.get("unit_id"), "unit_id")
        assignment_id = _safe_identifier(
            unit.get("assignment_id", unit_id), "assignment_id"
        )
        if assignment_id in seen_assignments:
            raise FanoutError(f"duplicate assignment_id: {assignment_id}")
        seen_assignments.add(assignment_id)
        attempt = unit.get("attempt", 1)
        if not isinstance(attempt, int) or attempt < 1:
            raise FanoutError(f"attempt must be a positive integer: {assignment_id}")
        payload = unit.get("payload")
        if not isinstance(payload, dict):
            raise FanoutError(f"payload must be an object: {assignment_id}")

        return_path = (returns_dir / f"{assignment_id}.json").resolve()
        if not _inside(return_path, run_dir):
            raise FanoutError(f"return path escapes run directory: {return_path}")
        if return_path.name in FORBIDDEN_RETURN_NAMES or return_path in seen_returns:
            raise FanoutError(f"unsafe or duplicate return path: {return_path}")
        seen_returns.add(return_path)
        assignment_path = assignments_dir / f"{assignment_id}.json"
        assignment = {
            "contract_version": CONTRACT_VERSION,
            "run_id": run_id,
            "assignment_kind": assignment_kind,
            "assignment_id": assignment_id,
            "unit_id": unit_id,
            "attempt": attempt,
            "frozen_inputs": resolved_inputs,
            "payload": payload,
            "allowed_write_path": str(return_path),
            "return_contract": _return_contract(),
        }
        atomic_json(assignment_path, assignment)
        assignment_rows.append(
            {
                "position": position,
                "assignment_id": assignment_id,
                "unit_id": unit_id,
                "attempt": attempt,
                "assignment_path": str(assignment_path.resolve()),
                "assignment_sha256": sha256_file(assignment_path),
                "return_path": str(return_path),
            }
        )

    manifest = {
        "contract_version": CONTRACT_VERSION,
        "run_id": run_id,
        "assignment_kind": assignment_kind,
        "spec_path": str(spec_path),
        "spec_sha256": sha256_file(spec_path),
        "frozen_inputs": resolved_inputs,
        "expected_assignments": len(assignment_rows),
        "assignments": assignment_rows,
    }
    atomic_json(run_dir / "run_manifest.json", manifest)
    ledger_lines = [
        json.dumps(
            {
                "assignment_id": row["assignment_id"],
                "unit_id": row["unit_id"],
                "attempt": row["attempt"],
                "status": "pending",
            },
            sort_keys=True,
        )
        for row in assignment_rows
    ]
    (run_dir / "unit_ledger.jsonl").write_text(
        "\n".join(ledger_lines) + "\n", encoding="utf-8", newline="\n"
    )
    # Seal last: the manifest hash is frozen before any model call.
    _write_seal(run_dir)
    return manifest


def verify_run_integrity(run_dir: Path) -> dict[str, Any]:
    """Fail closed if any prepared input, assignment, or sealed manifest has changed.

    If ``run_seal.json`` carries ``run_manifest_sha256``, the manifest must match it
    exactly; a seal file without that key (a foreign wrapper seal) or no seal file at all
    is treated as a legacy run and verification proceeds on the per-file hashes alone.
    """
    run_dir = run_dir.resolve()
    manifest_path = run_dir / "run_manifest.json"
    seal = _read_seal(run_dir)
    if seal is not None and "run_manifest_sha256" in seal:
        if not manifest_path.is_file() or sha256_file(manifest_path) != seal["run_manifest_sha256"]:
            raise FanoutError(
                "run manifest does not match run_seal.json: the manifest was rewritten "
                "outside the sealed prepare/retry protocol"
            )
    manifest = load_json(manifest_path)

    spec_path = Path(manifest["spec_path"])
    if not spec_path.is_file() or sha256_file(spec_path) != manifest["spec_sha256"]:
        raise FanoutError("run specification changed after preparation")

    for item in manifest["frozen_inputs"]:
        source = Path(item["path"])
        if not source.is_file() or sha256_file(source) != item["sha256"]:
            raise FanoutError(
                f"frozen input changed after preparation: {item['role']} ({source})"
            )

    for row in [*manifest["assignments"], *manifest.get("superseded", [])]:
        assignment_path = Path(row["assignment_path"])
        declared_hash = row.get("assignment_sha256")
        if not declared_hash:
            raise FanoutError(
                f"assignment has no frozen hash: {row.get('assignment_id')!r}"
            )
        if (
            not assignment_path.is_file()
            or sha256_file(assignment_path) != declared_hash
        ):
            raise FanoutError(
                f"assignment changed after preparation: {row.get('assignment_id')!r}"
            )
    return manifest


def validate_return(assignment: dict[str, Any], returned: Any) -> list[str]:
    """Validate one worker return with blinded error messages.

    Messages never echo worker-supplied values (labels could hide in any returned field),
    only field names, JSON paths, failed validator keywords, and expected values already
    frozen in the assignment.
    """
    errors: list[str] = []
    if not isinstance(returned, dict):
        return ["worker return is not a JSON object"]
    required = assignment["return_contract"]["required"]
    missing = [field for field in required if field not in returned]
    if missing:
        errors.append(f"missing return fields: {', '.join(missing)}")
    for field in ("contract_version", "assignment_id", "unit_id", "attempt"):
        if returned.get(field) != assignment.get(field):
            errors.append(f"{field} mismatch: expected {assignment.get(field)!r}")
    status = returned.get("status")
    if status not in TERMINAL_STATUSES:
        errors.append("unknown or nonterminal status")
    provenance = returned.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object")
    if status == SUCCESS_STATUS:
        for item in assignment["frozen_inputs"]:
            source = Path(item["path"])
            if not source.is_file() or sha256_file(source) != item["sha256"]:
                errors.append(
                    f"frozen input hash changed after assignment preparation: {item['role']}"
                )
        schema_items = [
            item for item in assignment["frozen_inputs"] if item["role"] == "result_schema"
        ]
        if len(schema_items) != 1:
            errors.append("assignment does not name exactly one result schema")
        else:
            schema_path = Path(schema_items[0]["path"])
            if sha256_file(schema_path) != schema_items[0]["sha256"]:
                errors.append("result schema hash changed after assignment preparation")
            else:
                errors.extend(
                    f"result {message}"
                    for message in _validate_result(schema_path, returned.get("result"))
                )
        if returned.get("error") is not None:
            errors.append("a succeeded return must have error=null")
    else:
        if returned.get("result") is not None:
            errors.append("a failed return must have result=null")
        if not isinstance(returned.get("error"), str) or not returned["error"].strip():
            errors.append("a failed return must include a nonempty error")
    return errors


def submit(
    run_dir: Path, assignment_id: str, returned: Any
) -> dict[str, Any]:
    """Validate and create one worker return without ever overwriting a file.

    The active sealed manifest, frozen assignment hash, schema, identifiers, and
    unique return path are checked before bytes are written. The create-exclusive
    file operation is intentionally fail-closed: simultaneous or repeated
    submissions for the same assignment cannot replace the first return.
    """
    run_dir = run_dir.resolve()
    assignment_id = _safe_identifier(assignment_id, "assignment_id")
    manifest = verify_run_integrity(run_dir)
    matches = [
        row for row in manifest["assignments"] if row["assignment_id"] == assignment_id
    ]
    if len(matches) != 1:
        raise FanoutError(
            f"assignment_id is not in the active manifest: {assignment_id}"
        )
    row = matches[0]
    assignment = load_json(Path(row["assignment_path"]))
    return_path = Path(row["return_path"]).resolve()
    assignment_return_path = Path(assignment["allowed_write_path"]).resolve()
    returns_dir = (run_dir / "worker_returns").resolve()
    if return_path != assignment_return_path:
        raise FanoutError("manifest and assignment disagree about the worker return path")
    if not _inside(return_path, returns_dir) or return_path.parent != returns_dir:
        raise FanoutError(f"worker return path is outside its strict directory: {return_path}")
    if return_path.name in FORBIDDEN_RETURN_NAMES:
        raise FanoutError(f"unsafe worker return path: {return_path}")
    if return_path.exists():
        raise FanoutError(f"refusing to overwrite worker return: {return_path}")

    errors = validate_return(assignment, returned)
    if errors:
        raise FanoutError(
            "worker return rejected ("
            + str(len(errors))
            + " error(s)): "
            + "; ".join(errors)
        )

    text = json.dumps(returned, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with return_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise FanoutError(f"refusing to overwrite worker return: {return_path}") from exc

    # Re-read through the same parser so a reported receipt is evidence that the
    # on-disk return, not merely the in-memory candidate, is valid JSON.
    persisted = load_json(return_path)
    persisted_errors = validate_return(assignment, persisted)
    if persisted_errors:
        raise FanoutError(
            "persisted worker return failed post-write validation: "
            + "; ".join(persisted_errors)
        )
    return {
        "assignment_id": assignment["assignment_id"],
        "unit_id": assignment["unit_id"],
        "status": persisted["status"],
        "output_path": str(return_path),
        "sha256": sha256_file(return_path),
    }


def _read_submission_input(source: str) -> Any:
    """Read a bounded UTF-8 JSON submission without echoing its contents on error."""
    if source == "-":
        data = sys.stdin.buffer.read(MAX_SUBMISSION_BYTES + 1)
        label = "standard input"
    else:
        path = Path(source)
        try:
            if path.stat().st_size > MAX_SUBMISSION_BYTES:
                raise FanoutError(
                    f"worker submission exceeds {MAX_SUBMISSION_BYTES} bytes"
                )
            data = path.read_bytes()
        except OSError as exc:
            raise FanoutError(f"cannot read worker submission file: {path}") from exc
        label = str(path)
    if len(data) > MAX_SUBMISSION_BYTES:
        raise FanoutError(f"worker submission exceeds {MAX_SUBMISSION_BYTES} bytes")
    try:
        return json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FanoutError(f"worker submission from {label} is not valid UTF-8 JSON") from exc


def status(run_dir: Path, *, include_pending: bool = False) -> dict[str, Any]:
    """Report operational counts only while outcomes remain blinded.

    Superseded assignments (replaced by a linked retry) are excluded from the expected
    and terminal counts and reported in their own non-terminal ``superseded`` count.
    """
    run_dir = run_dir.resolve()
    manifest = verify_run_integrity(run_dir)
    counts: Counter[str] = Counter()
    pending: list[str] = []
    invalid: list[dict[str, Any]] = []
    expected_return_paths = {
        Path(row["return_path"]).resolve() for row in manifest["assignments"]
    }
    for row in manifest["assignments"]:
        assignment_path = Path(row["assignment_path"])
        assignment = load_json(assignment_path)
        return_path = Path(row["return_path"])
        if not return_path.is_file():
            counts["pending"] += 1
            pending.append(str(assignment_path))
            continue
        try:
            returned = load_json(return_path)
            errors = validate_return(assignment, returned)
        except FanoutError as exc:
            errors = [str(exc)]
        if errors:
            counts["invalid"] += 1
            invalid.append({"assignment_id": row["assignment_id"], "errors": errors})
        else:
            counts[returned["status"]] += 1

    returns_dir = run_dir / "worker_returns"
    for stray in sorted(returns_dir.glob("*.json")):
        if stray.resolve() not in expected_return_paths:
            counts["invalid"] += 1
            invalid.append(
                {
                    "assignment_id": None,
                    "errors": [f"unknown worker return: {stray.resolve()}"],
                }
            )

    terminal = sum(counts[name] for name in TERMINAL_STATUSES)
    result: dict[str, Any] = {
        "expected": manifest["expected_assignments"],
        "terminal": terminal,
        "invalid": counts["invalid"],
        "pending": counts["pending"],
        "superseded": len(manifest.get("superseded", [])),
        "seal": _seal_state(run_dir),
        "terminal_status_counts": {
            name: counts[name] for name in sorted(TERMINAL_STATUSES) if counts[name]
        },
        "invalid_returns": invalid,
    }
    if include_pending:
        result["pending_assignments"] = pending
    return result


def _next_assignment_id(assignment_id: str, next_attempt: int) -> str:
    """Derive the linked-attempt assignment_id following the ``-attemptNNN`` convention.

    ``u07-attempt001`` becomes ``u07-attempt002``; an id without the suffix gains one
    (``u07`` becomes ``u07-attempt002``). The attempt field, not the embedded digits, is
    authoritative for the new number.
    """
    match = ATTEMPT_SUFFIX.fullmatch(assignment_id)
    base = match.group("base") if match else assignment_id
    return _safe_identifier(f"{base}-attempt{next_attempt:03d}", "retry assignment_id")


def retry(
    run_dir: Path,
    assignment_id: str,
    *,
    downstream_failure_reason: str | None = None,
) -> dict[str, Any]:
    """Archive a failed or invalid return and issue the one linked second attempt.

    The retry policy allows each planned slot at most ``MAX_ATTEMPTS`` (2) linked attempts.
    The superseded assignment moves to the manifest's
    ``superseded`` audit array, its return is archived under ``worker_returns/archive/``
    (never overwritten), a fresh pending assignment with ``attempt + 1`` is appended, and
    the manifest is rewritten atomically and resealed in the same operation.

    A return can satisfy this contract and still be a terminal non-success downstream: the
    fan-out contract validates the return envelope, while a downstream consumer may also
    validate ``result`` against a frozen per-item response schema. The shared contract makes
    a parse failure retryable, but this function cannot observe the consumer's verdict.
    ``downstream_failure_reason`` is the opt-in path for that case: the caller supplies the consumer's typed reason, it is
    recorded on the superseded row and the ledger, and the linked attempt reuses the frozen
    payload byte-for-byte. Default behaviour is unchanged: without it, a contract-valid
    terminal success is still refused.
    """
    run_dir = run_dir.resolve()
    manifest = verify_run_integrity(run_dir)
    _safe_identifier(assignment_id, "assignment_id")
    active_rows = manifest["assignments"]
    matches = [row for row in active_rows if row["assignment_id"] == assignment_id]
    if not matches:
        raise FanoutError(
            f"assignment_id is not in the active manifest: {assignment_id}"
        )
    row = matches[0]
    attempt = int(row["attempt"])
    if attempt >= MAX_ATTEMPTS:
        raise FanoutError(
            f"attempt cap reached for {assignment_id}: the fan-out contract allows at "
            f"most {MAX_ATTEMPTS} attempts per slot"
        )
    return_path = Path(row["return_path"])
    if not return_path.is_file():
        raise FanoutError(
            f"cannot retry {assignment_id}: no worker return exists (still pending)"
        )
    assignment = load_json(Path(row["assignment_path"]))
    try:
        returned = load_json(return_path)
        errors = validate_return(assignment, returned)
    except FanoutError as exc:
        returned = None
        errors = [str(exc)]
    if not errors and isinstance(returned, dict) and returned.get("status") == SUCCESS_STATUS:
        if not downstream_failure_reason:
            raise FanoutError(
                f"refusing to retry {assignment_id}: its return is a valid terminal success"
            )
        _safe_reason(downstream_failure_reason)

    next_attempt = attempt + 1
    new_id = _next_assignment_id(assignment_id, next_attempt)
    known_ids = {existing["assignment_id"] for existing in active_rows}
    known_ids.update(
        existing["assignment_id"] for existing in manifest.get("superseded", [])
    )
    if new_id in known_ids:
        raise FanoutError(f"retry assignment_id already exists: {new_id}")

    returns_dir = run_dir / "worker_returns"
    new_return_path = (returns_dir / f"{new_id}.json").resolve()
    if not _inside(new_return_path, run_dir):
        raise FanoutError(f"return path escapes run directory: {new_return_path}")
    if new_return_path.name in FORBIDDEN_RETURN_NAMES:
        raise FanoutError(f"unsafe return path: {new_return_path}")
    if new_return_path.exists():
        raise FanoutError(f"return path already occupied: {new_return_path}")
    assignments_dir = run_dir / "assignments"
    new_assignment_path = assignments_dir / f"{new_id}.json"
    if new_assignment_path.exists():
        raise FanoutError(f"assignment path already occupied: {new_assignment_path}")

    # 1. Archive the superseded return; never overwrite inside the archive.
    archive_dir = returns_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{return_path.stem}.attempt{attempt}.json"
    if archive_path.exists():
        raise FanoutError(f"refusing to overwrite archived return: {archive_path}")
    os.replace(return_path, archive_path)

    # 2. Write the immutable linked-attempt assignment.
    new_assignment = {
        "contract_version": CONTRACT_VERSION,
        "run_id": manifest["run_id"],
        "assignment_kind": manifest["assignment_kind"],
        "assignment_id": new_id,
        "unit_id": row["unit_id"],
        "attempt": next_attempt,
        "frozen_inputs": manifest["frozen_inputs"],
        "payload": assignment["payload"],
        "allowed_write_path": str(new_return_path),
        "return_contract": _return_contract(),
    }
    atomic_json(new_assignment_path, new_assignment)
    new_row: dict[str, Any] = {
        "assignment_id": new_id,
        "unit_id": row["unit_id"],
        "attempt": next_attempt,
        "assignment_path": str(new_assignment_path.resolve()),
        "assignment_sha256": sha256_file(new_assignment_path),
        "return_path": str(new_return_path),
    }
    if "position" in row:
        new_row["position"] = row["position"]

    # 3. Move the superseded row to the audit array and append the new active row.
    superseded_row = dict(row)
    superseded_row["superseded_by"] = new_id
    superseded_row["archived_return_path"] = str(archive_path.resolve())
    if downstream_failure_reason:
        superseded_row["downstream_failure_reason"] = _safe_reason(
            downstream_failure_reason
        )
    manifest["assignments"] = [
        existing for existing in active_rows if existing["assignment_id"] != assignment_id
    ] + [new_row]
    manifest.setdefault("superseded", []).append(superseded_row)
    manifest["expected_assignments"] = len(manifest["assignments"])

    # 4. Append the pending ledger row for the linked attempt.
    ledger_row = {
        "assignment_id": new_id,
        "unit_id": row["unit_id"],
        "attempt": next_attempt,
        "status": "pending",
        "superseded": assignment_id,
    }
    if downstream_failure_reason:
        ledger_row["downstream_failure_reason"] = _safe_reason(
            downstream_failure_reason
        )
    with (run_dir / "unit_ledger.jsonl").open(
        "a", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(json.dumps(ledger_row, sort_keys=True) + "\n")

    # 5. Rewrite the manifest atomically and reseal in the same operation.
    atomic_json(run_dir / "run_manifest.json", manifest)
    _write_seal(run_dir)
    return {
        "run_id": manifest["run_id"],
        "assignment_id": new_id,
        "unit_id": row["unit_id"],
        "attempt": next_attempt,
        "superseded": assignment_id,
        "assignment_path": str(new_assignment_path.resolve()),
        "return_path": str(new_return_path),
        "archived_return_path": str(archive_path.resolve()),
    }


def merge(run_dir: Path, output: Path) -> dict[str, Any]:
    """Merge validated returns in manifest order and write a reconciliation receipt.

    ``merge_receipt.json`` beside the output records the output hash, each merged return's
    hash, and terminal-status counts so the merge can be re-verified before unblinding.
    Refuses to overwrite either file.
    """
    run_dir = run_dir.resolve()
    output = output.resolve()
    receipt_path = output.parent / "merge_receipt.json"
    if output.exists():
        raise FanoutError(f"refusing to overwrite merged output: {output}")
    if receipt_path.exists():
        raise FanoutError(f"refusing to overwrite merge receipt: {receipt_path}")
    operational = status(run_dir)
    if operational["pending"] or operational["invalid"]:
        raise FanoutError(
            "cannot merge an unreconciled run: "
            f"pending={operational['pending']}, invalid={operational['invalid']}"
        )
    manifest = load_json(run_dir / "run_manifest.json")
    rows = [load_json(Path(item["return_path"])) for item in manifest["assignments"]]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    receipt = {
        "output_path": str(output),
        "output_sha256": sha256_file(output),
        "merged": len(rows),
        "return_sha256": {
            item["assignment_id"]: sha256_file(Path(item["return_path"]))
            for item in manifest["assignments"]
        },
        "status_counts": dict(sorted(Counter(row["status"] for row in rows).items())),
    }
    atomic_json(receipt_path, receipt)
    return {"merged": len(rows), "output": str(output), "receipt": str(receipt_path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--spec", type=Path, required=True)
    prepare_parser.add_argument("--run-dir", type=Path, required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--run-dir", type=Path, required=True)
    status_parser.add_argument("--include-pending", action="store_true")

    submit_parser = subparsers.add_parser(
        "submit", help="validate and create one assigned worker return"
    )
    submit_parser.add_argument("--run-dir", type=Path, required=True)
    submit_parser.add_argument("--assignment-id", required=True)
    submit_parser.add_argument(
        "--input",
        default="-",
        help="UTF-8 JSON candidate path, or - (the default) to read standard input",
    )

    retry_parser = subparsers.add_parser("retry")
    retry_parser.add_argument("--run-dir", type=Path, required=True)
    retry_parser.add_argument("--assignment-id", required=True)
    retry_parser.add_argument(
        "--downstream-failure-reason",
        default=None,
        help=(
            "opt-in: permit retrying a return that is contract-valid here but a terminal "
            "non-success for the consumer (e.g. the launcher's frozen per-item response "
            "schema). Records the typed reason on the superseded row and the ledger."
        ),
    )

    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument("--run-dir", type=Path, required=True)
    merge_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.spec, args.run_dir)
            result = {
                "run_id": result["run_id"],
                "expected": result["expected_assignments"],
                "run_manifest": str((args.run_dir / "run_manifest.json").resolve()),
            }
        elif args.command == "status":
            result = status(args.run_dir, include_pending=args.include_pending)
        elif args.command == "submit":
            result = submit(
                args.run_dir,
                args.assignment_id,
                _read_submission_input(args.input),
            )
        elif args.command == "retry":
            result = retry(
                args.run_dir,
                args.assignment_id,
                downstream_failure_reason=args.downstream_failure_reason,
            )
        elif args.command == "merge":
            result = merge(args.run_dir, args.output)
        else:  # argparse requires and constrains the command; defensive fail-closed guard
            raise FanoutError(f"unsupported command: {args.command}")
    except FanoutError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
