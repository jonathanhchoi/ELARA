"""Durable admission for host-native workers; never launches an agent or changes research.

Tickets reserve work, not attempts. Only an accepted native launch or a worker's
exclusive start record establishes launch evidence. Missing evidence never proves
nonexecution. The native host owns scheduling; short SQLite transactions protect
one persistent session owner without leases or a background service.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True

VERSION = "1.0"
DEFAULT_TARGET = 6
DEFAULT_MAXIMUM = 12
HASH = re.compile(r"[0-9a-f]{64}\Z")
ACTIVE_STATES = {"intent", "acknowledged", "started"}
FINAL_STATES = {"reconciled", "never_started"}


class DispatchError(ValueError):
    """Closed operational failure with no research content."""


def require(condition, code):
    if not condition:
        raise DispatchError(code)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _sha(value):
    return hashlib.sha256(_bytes(value)).hexdigest()


def _digest(path):
    with Path(path).open("rb") as stream:
        value = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise DispatchError("invalid_operational_record") from exc


def _publish(path, value):
    """Create once and fsync; a partial publication fails closed on every later read."""
    path = Path(path)
    raw = _bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        require(path.read_bytes() == raw, "immutable_record_conflict")


def _positive(value, field):
    require(type(value) is int and value > 0, "invalid_" + field)
    return value


def _directory(run_dir):
    return Path(run_dir).resolve() / "batch_checks" / "dispatch"


def _db_path(run_dir):
    return _directory(run_dir) / "dispatch.sqlite3"


def _policy(run_dir):
    path = Path(run_dir).resolve() / "dispatch_policy.json"
    if not path.exists():
        return None
    policy = _read(path)
    require(policy.get("schema_version") == VERSION and policy.get("mode") in {"adaptive", "fixed"}, "invalid_dispatch_policy")
    _positive(policy.get("initial_target"), "initial_target")
    _positive(policy.get("maximum"), "maximum")
    require(policy["initial_target"] <= policy["maximum"], "invalid_dispatch_policy")
    return policy


def initialize_policy(run_dir, concurrency=None):
    """Called only by new-run preparation or an authorized migration."""
    if concurrency is not None:
        _positive(concurrency, "concurrency")
    policy = {"schema_version": VERSION, "mode": "fixed" if concurrency is not None else "adaptive",
              "initial_target": concurrency if concurrency is not None else DEFAULT_TARGET,
              "maximum": concurrency if concurrency is not None else DEFAULT_MAXIMUM,
              "increase": 1, "decrease_factor": 0.5, "cooldown_checkpoints": 2}
    existing = _policy(run_dir)
    if existing is not None:
        require(existing == policy, "dispatch_policy_already_fixed")
        return existing
    _publish(Path(run_dir).resolve() / "dispatch_policy.json", policy)
    return policy


def _seed_database(path):
    """Publish a closed, valid empty SQLite image only when the target is absent.

    Some virtual filesystems return IOERR_READ for a newly created empty file.
    Build the initial header locally, then publish complete bytes on the target
    filesystem. The local file never contains run state. Neither this operation
    nor the later connection retries a transaction or replaces an existing DB.
    """
    if path.exists():
        return
    with tempfile.TemporaryDirectory(prefix="elara-dispatch-seed-") as temporary:
        local = Path(temporary) / "empty.sqlite3"
        db = sqlite3.connect(str(local), isolation_level=None)
        try:
            db.execute("VACUUM")
        finally:
            db.close()
        raw = local.read_bytes()
    candidate = path.with_name(".dispatch-seed-" + uuid.uuid4().hex + ".sqlite3")
    try:
        with candidate.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            if os.name == "nt":
                # Windows rename is atomic and refuses an existing destination.
                os.rename(candidate, path)
            else:
                # POSIX rename replaces a destination; an exclusive link does not.
                os.link(candidate, path)
        except FileExistsError:
            pass
    finally:
        candidate.unlink(missing_ok=True)


@contextmanager
def _db(run_dir, *, write=False, create=False):
    path = _db_path(run_dir)
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
        _seed_database(path)
    require(create or path.is_file(), "dispatch_not_initialized")
    uri = path.as_uri() + ("?mode=rw" if write or create else "?mode=ro")
    db = sqlite3.connect(uri, uri=True, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        if write or create:
            db.execute("PRAGMA synchronous=FULL")
        db.execute("BEGIN IMMEDIATE" if write or create else "BEGIN")
        if create:
            for sql in (
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, owner TEXT NOT NULL, host TEXT NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL, binding TEXT NOT NULL, target INTEGER NOT NULL, maximum INTEGER NOT NULL, fixed INTEGER NOT NULL, created TEXT NOT NULL)",
                "CREATE TABLE IF NOT EXISTS tickets (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, position INTEGER NOT NULL, assignment_id TEXT NOT NULL, attempt INTEGER NOT NULL, path TEXT NOT NULL, sha256 TEXT NOT NULL, state TEXT NOT NULL, evidence TEXT, UNIQUE(session_id,assignment_id,attempt))",
                "CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY, event TEXT NOT NULL, previous TEXT NOT NULL, sha256 TEXT NOT NULL)",
            ):
                db.execute(sql)
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('version',?)", (VERSION,))
        require(_meta(db, "version") == VERSION, "unsupported_dispatch_database")
        if write:
            _verify_events(db)
        _verify_policy(db, run_dir, writable=write or create)
        yield db
        if write or create:
            _event(db, "state_snapshot", state_sha256=_state_digest(db))
        db.execute("COMMIT")
    except Exception:
        if db.in_transaction:
            db.execute("ROLLBACK")
        raise
    finally:
        db.close()


def _meta(db, key, default=None):
    row = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def _set_meta(db, key, value):
    db.execute("INSERT INTO metadata VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def _event(db, kind, **fields):
    previous = db.execute("SELECT sha256 FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
    previous = previous[0] if previous else "0" * 64
    raw = _bytes({"kind": kind, "at": _now(), **fields}).decode()
    sha = hashlib.sha256((previous + raw).encode()).hexdigest()
    db.execute("INSERT INTO events(event,previous,sha256) VALUES (?,?,?)", (raw, previous, sha))


def _verify_events(db):
    previous = "0" * 64
    latest = None
    for row in db.execute("SELECT event,previous,sha256 FROM events ORDER BY sequence"):
        require(row[1] == previous and hashlib.sha256((previous + row[0]).encode()).hexdigest() == row[2], "dispatch_history_changed")
        previous = row[2]
        latest = json.loads(row[0])
    if latest is not None:
        require(latest.get("kind") == "state_snapshot" and latest.get("state_sha256") == _state_digest(db), "dispatch_database_view_changed")


def _state_digest(db):
    return _sha({table: [list(row) for row in db.execute("SELECT * FROM " + table + " ORDER BY 1")]
                 for table in ("metadata", "sessions", "tickets")})


def _verify_policy(db, run_dir, *, writable):
    path = Path(run_dir).resolve() / "dispatch_policy.json"
    expected = _meta(db, "policy_sha256")
    if expected is not None:
        require(path.is_file() and _digest(path) == expected, "dispatch_policy_changed")
        return
    if not path.exists():
        require(_meta(db, "migration_state") in (None, "paused"), "dispatch_policy_missing")
        return
    has_history = db.execute("SELECT COUNT(*) FROM events").fetchone()[0] > 0
    if has_history:
        require(_meta(db, "migration_state") == "paused", "dispatch_policy_binding_missing")
        policy = _policy(run_dir)
        require(policy == {"schema_version": VERSION, "mode": "adaptive", "initial_target": DEFAULT_TARGET,
                           "maximum": DEFAULT_MAXIMUM, "increase": 1, "decrease_factor": 0.5,
                           "cooldown_checkpoints": 2}, "migration_policy_changed")
    require(writable, "dispatch_policy_binding_not_initialized")
    _set_meta(db, "policy_sha256", _digest(path))


def _metrics(db, session):
    events = [json.loads(row[0]) for row in db.execute("SELECT event FROM events ORDER BY sequence")]
    ticket_ids = {row[0] for row in db.execute("SELECT id FROM tickets WHERE session_id=?", (session["id"],))}
    selected = [event for event in events if event.get("session_id") == session["id"] or event.get("ticket_id") in ticket_ids]
    origin = datetime.fromisoformat(session["created"])
    ending = next((datetime.fromisoformat(event["at"]) for event in reversed(selected) if event["kind"] == "session_closed"), datetime.now(timezone.utc))
    active, peak, total, previous = set(), 0, 0.0, origin
    reconciled = 0
    for event in selected:
        moment = min(datetime.fromisoformat(event["at"]), ending)
        total += max(0.0, (moment - previous).total_seconds()) * len(active)
        previous = moment
        if event["kind"] == "worker_started":
            active.add(event["ticket_id"])
            peak = max(peak, len(active))
        elif event["kind"] in {"worker_returned", "return_reconciled"}:
            active.discard(event["ticket_id"])
        if event["kind"] == "return_reconciled":
            reconciled += 1
    total += max(0.0, (ending - previous).total_seconds()) * len(active)
    elapsed = max(0.0, (ending - origin).total_seconds())
    return {"elapsed_seconds": round(elapsed, 6), "registered_worker_seconds": round(total, 6),
            "peak_registered_workers": peak, "average_registered_workers": round(total / elapsed, 6) if elapsed else 0.0,
            "reconciled_attempts_per_minute": round(reconciled * 60 / elapsed, 6) if elapsed else 0.0,
            "activity_basis": "worker start-to-return registrations; not direct model or host liveness telemetry"}


def _current(db):
    rows = db.execute("SELECT * FROM sessions WHERE state!='closed'").fetchall()
    require(len(rows) <= 1, "multiple_dispatch_owners")
    return rows[0] if rows else None


def _owned(db, owner):
    row = _current(db)
    require(row is not None and row["owner"] == owner, "dispatch_owner_mismatch")
    return row


def _controller(run_dir, kind):
    if kind == "coding":
        from unit_fanout import verify_run_integrity, status
        manifest = verify_run_integrity(Path(run_dir))
        return manifest, status(Path(run_dir), include_pending=True)
    require(kind == "research", "invalid_dispatch_kind")
    from research_fanout import verify_integrity, status
    manifest = verify_integrity(Path(run_dir))
    return manifest, status(Path(run_dir), include_pending=True, include_exhausted=True)


def _binding(manifest):
    return _sha(manifest)


def _worker_bindings(run_dir, manifest, kind):
    """Freeze common bytes once; workers rehash them without scanning siblings' returns."""
    if kind == "coding":
        paths = [run_dir / "run_manifest.json", Path(manifest["spec_path"]),
                 *[Path(item["path"]) for item in manifest["frozen_inputs"]]]
        seal = run_dir / "run_seal.json"
    else:
        paths = [run_dir / "manifest.json", run_dir / "spec.json"]
        seal = run_dir / "seal.json"
    if seal.exists():
        paths.append(seal)
    return {str(path.resolve()): _digest(path) for path in paths}


def _archive_closed(db, run_dir):
    """Rotate closed evidence out of the hot database; its hash chain remains immutable."""
    sessions = db.execute("SELECT * FROM sessions WHERE state='closed' ORDER BY created").fetchall()
    if not sessions:
        return
    require(_current(db) is None, "cannot_archive_live_session")
    previous = json.loads(_meta(db, "history_anchor", "null"))
    value = {"schema_version": VERSION, "previous": previous,
             "sessions": [dict(row) for row in sessions],
             "tickets": [dict(row) for row in db.execute("SELECT * FROM tickets ORDER BY session_id,position")],
             "events": [dict(row) for row in db.execute("SELECT * FROM events ORDER BY sequence")]}
    path = _directory(run_dir) / "segments" / (_sha(value) + ".json")
    _publish(path, value)
    anchor = {"path": path.relative_to(_directory(run_dir)).as_posix(), "sha256": _digest(path)}
    db.execute("DELETE FROM tickets")
    db.execute("DELETE FROM sessions")
    db.execute("DELETE FROM events")
    db.execute("DELETE FROM metadata WHERE key LIKE 'throttled:%' OR key LIKE 'unclean:%' OR key LIKE 'policy_applied:%'")
    _set_meta(db, "history_anchor", json.dumps(anchor, sort_keys=True))
    _event(db, "closed_history_archived", anchor=anchor)


def _history_attempts(db, run_dir):
    """Authenticate closed segments at session boundaries, not every worker call."""
    anchor = json.loads(_meta(db, "history_anchor", "null"))
    seen, attempts = set(), {}
    while anchor is not None:
        require(isinstance(anchor, dict) and set(anchor) == {"path", "sha256"}, "invalid_history_anchor")
        path = (_directory(run_dir) / anchor["path"]).resolve()
        require(path.is_relative_to(_directory(run_dir) / "segments") and str(path) not in seen, "invalid_history_anchor")
        require(_digest(path) == anchor["sha256"], "closed_dispatch_history_changed")
        seen.add(str(path))
        value = _read(path)
        require(value.get("schema_version") == VERSION and all(row["state"] == "closed" for row in value["sessions"]), "closed_dispatch_history_invalid")
        for row in value["tickets"]:
            require(row["state"] in FINAL_STATES, "archived_attempt_not_terminal")
            attempts.setdefault((row["assignment_id"], row["attempt"]), []).append(row["state"])
        anchor = value["previous"]
    return attempts


def _candidates(manifest, status, kind, assignments=None, block=None, limit=None):
    if kind == "coding":
        pending = set(status["pending_assignments"])
        rows = [dict(row) for row in manifest["assignments"] if row["assignment_path"] in pending]
        rows.sort(key=lambda row: (row.get("position", 0), row["assignment_id"]))
        if block is not None:
            rows = [row for row in rows if _read(row["assignment_path"]).get("payload", {}).get("block") == block]
    else:
        rows = [dict(row) for row in status["pending_assignments"]]
    if assignments is not None:
        require(isinstance(assignments, list), "invalid_assignment_selection")
        selected = set()
        for value in assignments:
            if isinstance(value, str):
                selected.add(value)
            else:
                require(isinstance(value, dict), "invalid_assignment_selection")
                selected.add((value["assignment_id"], int(value["attempt"])))
        chosen = [row for row in rows if (row["assignment_id"], int(row["attempt"])) in selected
                  or row["assignment_id"] in selected or row.get("assignment_path") in selected]
        require(len(chosen) == len(selected), "selection_is_not_eligible")
        rows = chosen
    if limit is not None:
        rows = rows[:_positive(limit, "limit")]
    return rows


def _ticket_view(row):
    value = _read(row["path"])
    require(_digest(row["path"]) == row["sha256"], "dispatch_ticket_changed")
    return {"ticket_id": row["id"], "ticket_path": row["path"], "assignment_id": row["assignment_id"],
            "attempt": row["attempt"], "return_path": value["return_path"],
            **{key: value[key] for key in ("assignment_path", "brief_path", "unit_id") if key in value}}


def _session_view(db, session, *, include_tickets=True):
    rows = db.execute("SELECT * FROM tickets WHERE session_id=? ORDER BY position", (session["id"],)).fetchall()
    counts = {name: sum(row["state"] == name for row in rows) for name in {"planned", *ACTIVE_STATES, "returned", "reconciled", "never_started", "unknown"}}
    active = sum(counts[state] for state in ACTIVE_STATES)
    result = {"mode": "continuous", "schema_version": VERSION, "session_id": session["id"],
              "owner": session["owner"], "state": session["state"], "target": session["target"],
              "maximum": session["maximum"], "queued": counts["planned"], "active": active,
              "unknown": counts["unknown"], "returned": counts["returned"],
              "reconciled": counts["reconciled"], "never_started": counts["never_started"],
              "admission_stopped": session["state"] != "active", "can_close": all(row["state"] in FINAL_STATES for row in rows),
              "payload_values_included": False}
    result["metrics"] = _metrics(db, session)
    result["backoff_unknown"] = _meta(db, "backoff_unknown") == "1"
    result["backoff_until"] = _meta(db, "backoff_until")
    if include_tickets:
        result["tickets"] = [_ticket_view(row) for row in rows]
    return result


def open_session(run_dir, *, kind, owner=None, host, capacity=DEFAULT_TARGET, concurrency=None,
                 assignments=None, block=None, limit=None, include_exhausted=False,
                 resume_request=None, request_root=None):
    run_dir = Path(run_dir).resolve()
    policy = _policy(run_dir)
    manifest, report = _controller(run_dir, kind)
    if policy is None:
        require(not _db_path(run_dir).exists(), "dispatch_policy_missing")
        return {**report, "mode": "legacy", "tickets": [], "payload_values_included": False}
    require(isinstance(owner, str) and 0 < len(owner) <= 240, "native_session_owner_required")
    require(host in {"codex", "claude"}, "invalid_dispatch_host")
    _positive(capacity, "capacity")
    if concurrency is not None:
        _positive(concurrency, "concurrency")
    binding = _binding(manifest)
    selected = _candidates(manifest, report, kind, assignments, block, limit)
    with _db(run_dir, write=True, create=True) as db:
        prior = _current(db)
        if prior is not None:
            require(prior["owner"] == owner, "dispatch_owner_exists_reconcile_before_recovery")
            require(prior["kind"] == kind and prior["host"] == host and prior["binding"] == binding, "dispatch_session_binding_mismatch")
            # Reopening an existing session never creates, restarts, or reassigns work.
            return {**report, **_session_view(db, prior, include_tickets=False), "tickets": [],
                    "existing_session": True, "reused_session": True, "admission_stopped": True}
        if _meta(db, "migration_state") == "paused":
            _authorize_migration(db, run_dir, resume_request, request_root, "resume_dispatch")
            _set_meta(db, "migration_state", "activated")
        _check_backoff(db)
        _archive_closed(db, run_dir)
        historical_attempts = _history_attempts(db, run_dir)
        fixed = concurrency is not None or policy["mode"] == "fixed"
        ceiling = min(capacity, concurrency if concurrency is not None else policy["maximum"])
        if policy["mode"] == "fixed":
            ceiling = min(ceiling, policy["maximum"])
        initial = concurrency if concurrency is not None else policy["initial_target"]
        desired = min(initial, int(_meta(db, "next_target", initial))) if fixed else int(_meta(db, "next_target", initial))
        target = min(desired, ceiling)
        session_id = uuid.uuid4().hex
        db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)", (session_id, owner, host, kind, "active", binding, target, ceiling, int(fixed), _now()))
        _event(db, "session_opened", session_id=session_id, owner=owner, host=host, binding=binding, target=target, maximum=ceiling)
        common_bindings = _worker_bindings(run_dir, manifest, kind)
        for position, item in enumerate(selected):
            assignment_id, attempt = item["assignment_id"], int(item["attempt"])
            previous = db.execute("SELECT state FROM tickets WHERE assignment_id=? AND attempt=?", (assignment_id, attempt)).fetchall()
            require(all(row[0] == "never_started" for row in previous), "attempt_already_reserved")
            require(all(state == "never_started" for state in historical_attempts.get((assignment_id, attempt), [])), "attempt_already_reserved")
            ticket_id = uuid.uuid4().hex
            ticket_path = _directory(run_dir) / "tickets" / session_id / (ticket_id + ".json")
            value = {"schema_version": VERSION, "run_dir": str(run_dir), "session_id": session_id,
                     "ticket_id": ticket_id, "kind": kind, "binding_sha256": binding,
                     "assignment_id": assignment_id, "attempt": attempt, "return_path": item["return_path"],
                     **{key: item[key] for key in ("assignment_path", "brief_path", "unit_id") if key in item}}
            own_path = Path(item["assignment_path"] if kind == "coding" else item["brief_path"])
            value["binding_files"] = {**common_bindings, str(own_path.resolve()): _digest(own_path)}
            _publish(ticket_path, value)
            db.execute("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,NULL)", (ticket_id, session_id, position, assignment_id, attempt, str(ticket_path), _digest(ticket_path), "planned"))
            _event(db, "ticket_reserved", ticket_id=ticket_id, session_id=session_id, assignment_id=assignment_id, attempt=attempt, sha256=_digest(ticket_path))
        return {**report, **_session_view(db, _current(db)), "reused_session": False}


def _locate(ticket_path, db=None):
    path = Path(ticket_path).resolve()
    value = _read(path)
    require(value.get("schema_version") == VERSION, "invalid_dispatch_ticket")
    root = Path(value["run_dir"]).resolve()
    require(path.is_relative_to(_directory(root) / "tickets"), "dispatch_ticket_path_escape")
    if db is None:
        return root, value
    row = db.execute("SELECT * FROM tickets WHERE id=?", (value["ticket_id"],)).fetchone()
    require(row is not None and Path(row["path"]) == path and row["sha256"] == _digest(path), "dispatch_ticket_changed")
    session = _current(db)
    require(session is not None and session["id"] == row["session_id"], "dispatch_session_inactive")
    require(session["binding"] == value["binding_sha256"], "dispatch_scientific_binding_changed")
    for path, expected in value["binding_files"].items():
        require(Path(path).is_file() and _digest(path) == expected, "dispatch_scientific_binding_changed")
    return root, value, row, session


def _marker_path(run_dir, ticket_id, phase):
    return _directory(run_dir) / "markers" / (ticket_id + "." + phase + ".json")


def _research_launch(root, value):
    from research_fanout import _launches, _record_launches
    # start() has just checked the exact sealed manifest/spec/own-brief bytes.
    manifest = _read(root / "manifest.json")
    launches = _launches(root, manifest)[value["assignment_id"]]
    require(not any(row["attempt"] == value["attempt"] for row in launches), "research_attempt_already_launched")
    require(len(launches) + 1 == value["attempt"], "research_attempt_not_contiguous")
    _record_launches(root, [{"assignment_id": value["assignment_id"], "attempt": value["attempt"],
                           "return_path": value["return_path"], "launched_utc": _now()}])


def start(ticket_path):
    root, _ = _locate(ticket_path)
    with _db(root, write=True) as db:
        root, value, row, session = _locate(ticket_path, db)
        require(session["state"] == "active", "dispatch_admission_stopped")
        _check_backoff(db)
        require(row["state"] in {"planned", "intent", "acknowledged"}, "attempt_already_started")
        marker = _marker_path(root, row["id"], "started")
        require(not marker.exists(), "attempt_start_marker_exists_reconcile")
        occupied = db.execute("SELECT COUNT(*) FROM tickets WHERE session_id=? AND state IN ('intent','acknowledged','started') AND id!=?", (session["id"], row["id"])).fetchone()[0]
        require(occupied < session["target"], "dispatch_concurrency_limit")
        # The start marker precedes all scientific input reads by the worker.
        _publish(marker, {"ticket_id": row["id"], "session_id": session["id"], "phase": "started", "at": _now(), "ticket_sha256": row["sha256"]})
        if session["kind"] == "research":
            _research_launch(root, value)
        db.execute("UPDATE tickets SET state='started',evidence=? WHERE id=?", (_digest(marker), row["id"]))
        _event(db, "worker_started", ticket_id=row["id"], evidence_sha256=_digest(marker))
        return {"status": "started", **_ticket_view(row), "payload_values_included": False}


def record_intent(ticket_path, owner):
    root, _ = _locate(ticket_path)
    with _db(root, write=True) as db:
        _, _, row, session = _locate(ticket_path, db)
        _owned(db, owner)
        _check_backoff(db)
        require(session["state"] == "active" and row["state"] == "planned", "dispatch_intent_not_eligible")
        occupied = db.execute("SELECT COUNT(*) FROM tickets WHERE session_id=? AND state IN ('intent','acknowledged','started')", (session["id"],)).fetchone()[0]
        require(occupied < session["target"], "dispatch_concurrency_limit")
        db.execute("UPDATE tickets SET state='intent' WHERE id=?", (row["id"],))
        _event(db, "launch_intent", ticket_id=row["id"])
    return {"status": "intent", "ticket_id": row["id"], "payload_values_included": False}


def acknowledge(ticket_path, owner, evidence):
    require(isinstance(evidence, str) and HASH.fullmatch(evidence), "host_evidence_required")
    root, _ = _locate(ticket_path)
    with _db(root, write=True) as db:
        _, _, row, _ = _locate(ticket_path, db)
        _owned(db, owner)
        require(row["state"] in {"intent", "started", "returned"}, "dispatch_ack_not_eligible")
        if row["state"] == "intent":
            db.execute("UPDATE tickets SET state='acknowledged',evidence=? WHERE id=?", (evidence, row["id"]))
        _event(db, "launch_acknowledged", ticket_id=row["id"], evidence_sha256=evidence)
    return {"status": "acknowledged", "ticket_id": row["id"], "payload_values_included": False}


def _validate_canonical(root, value):
    path = Path(value["return_path"])
    require(path.is_file(), "worker_return_missing")
    if value["kind"] == "coding":
        from unit_fanout import validate_return
        returned = _read(path)
        require(not validate_return(_read(value["assignment_path"]), returned), "worker_return_invalid")
        succeeded = returned["status"] == "succeeded"
    else:
        from research_fanout import _classify_return
        state, _ = _classify_return(value, require_attempt=True)
        require(state == "complete", "worker_return_incomplete_or_invalid")
        succeeded = True
    return {"status": "returned", "assignment_id": value["assignment_id"], "attempt": value["attempt"],
            "output_path": str(path), "sha256": _digest(path), "succeeded": succeeded,
            "complete": True, "payload_values_included": False}


def _terminal_receipt(root, value, research_dispositions=None):
    """Only existing controller rules establish terminal success or retryable failure."""
    path = Path(value["return_path"])
    if value["kind"] == "research":
        if research_dispositions is None:
            from research_fanout import _dispositions, verify_integrity
            research_dispositions = _dispositions(Path(root), verify_integrity(Path(root)))
        dispositions = research_dispositions
        disposition = dispositions.get((value["assignment_id"], value["attempt"]))
        if disposition is not None:
            return {"kind": "research_disposition", "succeeded": False,
                    "return_sha256": _digest(path) if path.is_file() else None,
                    "disposition_sha256": _sha(disposition)}
    try:
        receipt = _validate_canonical(root, value)
        return {"kind": "valid_return", "succeeded": receipt["succeeded"], "return_sha256": receipt["sha256"]}
    except DispatchError:
        # The coding controller's frozen retry operation accepts existing invalid
        # returns. It explicitly refuses missing ones. Preserve that distinction.
        if value["kind"] == "coding" and path.is_file():
            return {"kind": "invalid_return", "succeeded": False, "return_sha256": _digest(path)}
        return None


def _verify_reconciled(db, run_dir, session, receipts=None):
    for row in db.execute("SELECT * FROM tickets WHERE session_id=? AND state='reconciled'", (session["id"],)):
        marker = _marker_path(run_dir, row["id"], "reconciled")
        require(marker.is_file() and _digest(marker) == row["evidence"], "reconciliation_receipt_changed")
        preserved = _read(marker)
        current = receipts[row["id"]] if receipts is not None else _terminal_receipt(Path(run_dir), _read(row["path"]))
        require(current == preserved["controller_receipt"], "reconciled_return_changed")


def _parent_preflight(run_dir, owner, *, allow_closed=False, terminal_ids=()):
    """Do corpus-wide/controller work without holding a SQLite read or writer lock."""
    run_dir = Path(run_dir).resolve()
    with _db(run_dir) as db:
        session = _current(db)
        if session is None and allow_closed:
            session = db.execute("SELECT * FROM sessions WHERE owner=? ORDER BY created DESC LIMIT 1", (owner,)).fetchone()
        require(session is not None and session["owner"] == owner, "dispatch_owner_mismatch")
        session = dict(session)
        rows = [dict(row) for row in db.execute("SELECT * FROM tickets WHERE session_id=? ORDER BY position", (session["id"],))]
    manifest, report = _controller(run_dir, session["kind"])
    require(_binding(manifest) == session["binding"], "dispatch_scientific_binding_changed")
    guards = _worker_bindings(run_dir, manifest, session["kind"])
    dispositions = None
    if session["kind"] == "research":
        from research_fanout import _dispositions
        dispositions = _dispositions(run_dir, manifest)
        path = run_dir / "dispositions.jsonl"
        guards[str(path)] = _digest(path) if path.exists() else None
    receipts = {}
    for row in rows:
        if row["state"] == "reconciled" or row["id"] in terminal_ids:
            value = _read(row["path"])
            require(_digest(row["path"]) == row["sha256"], "dispatch_ticket_changed")
            receipts[row["id"]] = _terminal_receipt(run_dir, value, dispositions)
            path = Path(value["return_path"])
            guards[str(path)] = _digest(path) if path.exists() else None
    return session, manifest, report, guards, receipts


def _check_parent_preflight(session, prepared, guards):
    require(session is not None and session["id"] == prepared["id"] and session["binding"] == prepared["binding"], "dispatch_changed_during_parent_verification")
    for raw_path, expected in guards.items():
        path = Path(raw_path)
        require((not path.exists()) if expected is None else path.is_file() and _digest(path) == expected, "controller_evidence_changed")


def finish(ticket_path):
    root, _ = _locate(ticket_path)
    with _db(root, write=True) as db:
        root, value, row, _ = _locate(ticket_path, db)
        require(row["state"] in {"started", "returned", "reconciled"}, "worker_was_not_admitted")
        receipt = _validate_canonical(root, value)
        marker = _marker_path(root, row["id"], "returned")
        marker_value = {"ticket_id": row["id"], "phase": "returned", "receipt": receipt}
        _publish(marker, marker_value)
        if row["state"] == "started":
            db.execute("UPDATE tickets SET state='returned',evidence=? WHERE id=?", (_digest(marker), row["id"]))
            _event(db, "worker_returned", ticket_id=row["id"], evidence_sha256=_digest(marker))
        return receipt


def _active_assignment(run_dir, assignment_id, attempt=None):
    if not _db_path(run_dir).is_file():
        return None
    with _db(run_dir) as db:
        session = _current(db)
        if session is None:
            return None
        rows = db.execute("SELECT * FROM tickets WHERE session_id=? AND assignment_id=?", (session["id"], assignment_id)).fetchall()
        if attempt is not None:
            rows = [row for row in rows if row["attempt"] == attempt]
        require(len(rows) == 1, "assignment_not_in_active_dispatch")
        return dict(rows[0])


def assert_submission_allowed(run_dir, assignment_id, attempt=None):
    row = _active_assignment(run_dir, assignment_id, attempt)
    if row is not None:
        require(row["state"] == "started", "worker_was_not_admitted")


def finish_assignment(run_dir, assignment_id, attempt=None):
    row = _active_assignment(run_dir, assignment_id, attempt)
    return finish(row["path"]) if row is not None else None


def assert_drained(run_dir):
    """Manifest-rewriting retry requires an explicitly closed dispatch session."""
    if _db_path(run_dir).is_file():
        with _db(run_dir) as db:
            require(_current(db) is None, "dispatch_session_must_close_before_retry")


def assert_legacy_launch_allowed(run_dir):
    if _db_path(run_dir).is_file():
        with _db(run_dir) as db:
            require(_current(db) is None, "research_launches_owned_by_dispatch")


def inspect(run_dir):
    policy = _policy(run_dir)
    if policy is None:
        require(not _db_path(run_dir).exists(), "dispatch_policy_missing")
        return {"mode": "legacy", "payload_values_included": False}
    if not _db_path(run_dir).is_file():
        return {"mode": "continuous", "policy": policy, "state": "ready", "payload_values_included": False}
    with _db(run_dir) as db:
        _verify_events(db)
        session = _current(db)
        return ({"policy": policy, **_session_view(db, session)} if session is not None else
                {"mode": "continuous", "policy": policy, "state": _meta(db, "migration_state", "ready"),
                 "next_target": int(_meta(db, "next_target", policy["initial_target"])),
                 "backoff_unknown": _meta(db, "backoff_unknown") == "1", "backoff_until": _meta(db, "backoff_until"),
                 "payload_values_included": False})


def reconcile(run_dir, owner, *, outcomes=None, throttled=False, stop_admissions=False, retry_after_seconds=None):
    """Parent-only reconciliation; host receipt hashes are references, not inferred facts."""
    outcomes = [] if outcomes is None else outcomes
    require(isinstance(outcomes, list), "invalid_host_evidence")
    require(retry_after_seconds is None or throttled and type(retry_after_seconds) is int and retry_after_seconds >= 0,
            "invalid_provider_retry_after")
    terminal_ids = {item.get("ticket_id") for item in outcomes if isinstance(item, dict) and item.get("status") == "completed"}
    prepared, manifest, _, guards, receipts = _parent_preflight(run_dir, owner, terminal_ids=terminal_ids)
    with _db(run_dir, write=True) as db:
        session = _owned(db, owner)
        _check_parent_preflight(session, prepared, guards)
        rows = db.execute("SELECT * FROM tickets WHERE session_id=? ORDER BY position", (session["id"],)).fetchall()
        known = {row["id"] for row in rows}
        evidence = {}
        for item in outcomes:
            require(isinstance(item, dict) and set(item) == {"ticket_id", "status", "evidence_sha256"}, "invalid_host_evidence")
            require(item["ticket_id"] in known and item["ticket_id"] not in evidence and item["status"] in {"completed", "never_started", "unknown"}
                    and isinstance(item["evidence_sha256"], str) and HASH.fullmatch(item["evidence_sha256"]), "invalid_host_evidence")
            evidence[item["ticket_id"]] = item
        clean = True
        for row in rows:
            if row["state"] in FINAL_STATES:
                continue
            value = _read(row["path"])
            require(_digest(row["path"]) == row["sha256"], "dispatch_ticket_changed")
            started_path = _marker_path(run_dir, row["id"], "started")
            host = evidence.get(row["id"])
            if host and host["status"] == "never_started":
                require(row["state"] in {"planned", "intent", "unknown"} and not started_path.exists()
                        and not Path(value["return_path"]).exists(), "accepted_attempt_cannot_be_unstarted")
                # An acknowledgement remains decisive even after an unknown-state pause.
                for event in db.execute("SELECT event FROM events"):
                    event = json.loads(event[0])
                    require(not (event.get("ticket_id") == row["id"] and event["kind"] == "launch_acknowledged"), "accepted_attempt_cannot_be_unstarted")
                db.execute("UPDATE tickets SET state='never_started',evidence=? WHERE id=?", (host["evidence_sha256"], row["id"]))
                _event(db, "native_nonexecution_verified", ticket_id=row["id"], evidence_sha256=host["evidence_sha256"])
                continue
            if started_path.exists():
                marker = _read(started_path)
                require(marker.get("ticket_id") == row["id"] and marker.get("ticket_sha256") == row["sha256"], "worker_start_marker_changed")
                # Recover a crash between the durable start marker and launch-ledger append.
                if session["kind"] == "research":
                    from research_fanout import _launches
                    launches = _launches(Path(run_dir), manifest)[row["assignment_id"]]
                    if not any(item["attempt"] == row["attempt"] for item in launches):
                        _research_launch(Path(run_dir), value)
                receipt = receipts.get(row["id"])
                # A return file alone is insufficient while the native worker may still write.
                if receipt is not None and host and host["status"] == "completed":
                    clean = clean and receipt["succeeded"]
                    marker = _marker_path(run_dir, row["id"], "reconciled")
                    _publish(marker, {"ticket_id": row["id"], "controller_receipt": receipt,
                                      "host_evidence_sha256": host["evidence_sha256"]})
                    db.execute("UPDATE tickets SET state='reconciled',evidence=? WHERE id=?", (_digest(marker), row["id"]))
                    _event(db, "return_reconciled", ticket_id=row["id"], evidence_sha256=_digest(marker),
                           host_evidence_sha256=host["evidence_sha256"], succeeded=receipt["succeeded"])
                    continue
            if stop_admissions or host is not None:
                clean = False
                db.execute("UPDATE tickets SET state='unknown' WHERE id=?", (row["id"],))
                _event(db, "launch_finality_unknown", ticket_id=row["id"], evidence_sha256=host["evidence_sha256"] if host else None)
        has_unknown = db.execute("SELECT COUNT(*) FROM tickets WHERE session_id=? AND state='unknown'", (session["id"],)).fetchone()[0]
        if stop_admissions or has_unknown:
            db.execute("UPDATE sessions SET state='paused' WHERE id=?", (session["id"],))
        # Store observations now; adjust at close, once, for the next accepted batch.
        if throttled:
            _set_meta(db, "throttled:" + session["id"], "1")
            if retry_after_seconds is None:
                _set_meta(db, "backoff_unknown", "1")
            else:
                deadline = datetime.fromisoformat(_now()) + timedelta(seconds=retry_after_seconds)
                prior = _meta(db, "backoff_until")
                if prior is not None:
                    deadline = max(deadline, datetime.fromisoformat(prior))
                _set_meta(db, "backoff_until", deadline.isoformat())
            _event(db, "provider_throttled", session_id=session["id"], retry_after_seconds=retry_after_seconds,
                   not_before=_meta(db, "backoff_until"), wait_unknown=_meta(db, "backoff_unknown") == "1")
        if not clean:
            _set_meta(db, "unclean:" + session["id"], "1")
        _event(db, "checkpoint_reconciled", session_id=session["id"], throttled=bool(throttled), stopped=bool(stop_admissions))
        return _session_view(db, _current(db))


def _check_backoff(db):
    require(_meta(db, "backoff_unknown") != "1", "provider_backoff_unknown_requires_evidence")
    deadline = _meta(db, "backoff_until")
    require(deadline is None or datetime.fromisoformat(_now()) >= datetime.fromisoformat(deadline), "provider_backoff_active")


def resolve_backoff(run_dir, owner, evidence_sha256):
    """Parent reports newly verified provider availability; no guessed timeout or lease."""
    require(isinstance(evidence_sha256, str) and HASH.fullmatch(evidence_sha256), "provider_availability_evidence_required")
    with _db(run_dir, write=True) as db:
        session = _current(db)
        if session is None:
            session = db.execute("SELECT * FROM sessions ORDER BY created DESC LIMIT 1").fetchone()
        require(session is not None and session["owner"] == owner, "dispatch_owner_mismatch")
        deadline = _meta(db, "backoff_until")
        require(deadline is None or datetime.fromisoformat(_now()) >= datetime.fromisoformat(deadline), "provider_backoff_active")
        _set_meta(db, "backoff_unknown", "0")
        _event(db, "provider_availability_verified", session_id=session["id"], evidence_sha256=evidence_sha256)
    return {"status": "backoff_resolved", "payload_values_included": False}


def checkpoint(run_dir, owner, *, passed=False):
    prepared, _, report, guards, receipts = _parent_preflight(run_dir, owner, allow_closed=True)
    with _db(run_dir, write=True) as db:
        session = _current(db)
        if session is None:
            session = db.execute("SELECT * FROM sessions WHERE owner=? ORDER BY created DESC LIMIT 1", (owner,)).fetchone()
        require(session is not None and session["owner"] == owner, "dispatch_owner_mismatch")
        _check_parent_preflight(session, prepared, guards)
        _verify_reconciled(db, run_dir, session, receipts)
        value = _session_view(db, session, include_tickets=False)
        # The host's end-of-workflow report is not the researcher's accepted
        # scientific/budget validation checkpoint. Only an explicit parent
        # assertion after those checks may promote the next target.
        if session["state"] == "closed" and _meta(db, "policy_applied:" + session["id"]) is None:
            throttled = _meta(db, "throttled:" + session["id"]) == "1"
            target = session["target"]
            cooldown = int(_meta(db, "cooldown", 0))
            if passed or throttled:
                backlog = report["pending"] >= session["target"] + 1
                if throttled:
                    target = max(1, target // 2)
                    cooldown = 2
                elif cooldown:
                    cooldown -= 1
                elif not session["fixed"] and backlog and _meta(db, "unclean:" + session["id"]) != "1" and value["reconciled"] >= session["target"]:
                    target = min(session["maximum"], target + 1)
                _set_meta(db, "next_target", target)
                _set_meta(db, "cooldown", cooldown)
                _set_meta(db, "policy_applied:" + session["id"], "1")
                _event(db, "policy_checkpoint", session_id=session["id"], passed=bool(passed), backlog=backlog,
                       throttled=throttled, next_target=target, cooldown=cooldown)
            value.update(next_target=target, cooldown_checkpoints=cooldown)
        require(not passed or session["state"] == "closed", "accepted_checkpoint_requires_closed_session")
        event = db.execute("SELECT sequence,sha256 FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        value["event_head_sha256"] = event[1] if event else "0" * 64
        path = _directory(run_dir) / "checkpoints" / (session["id"] + "-" + str(event[0] if event else 0) + ".json")
        _publish(path, value)
        return {**value, "path": str(path), "sha256": _digest(path)}


def close_session(run_dir, owner):
    prepared, _, _, guards, receipts = _parent_preflight(run_dir, owner)
    with _db(run_dir, write=True) as db:
        session = _owned(db, owner)
        _check_parent_preflight(session, prepared, guards)
        _verify_reconciled(db, run_dir, session, receipts)
        value = _session_view(db, session, include_tickets=False)
        require(value["can_close"], "dispatch_finality_unresolved")
        cooldown = int(_meta(db, "cooldown", 0))
        target = session["target"]
        db.execute("UPDATE sessions SET state='closed' WHERE id=?", (session["id"],))
        _event(db, "session_closed", session_id=session["id"], next_target=target, cooldown=cooldown)
        return {**value, "state": "closed", "next_target": target, "cooldown_checkpoints": cooldown, "admission_stopped": True}


def _migration_plan(run_dir, kind, host, capacity):
    manifest, report = _controller(run_dir, kind)
    require(host in {"codex", "claude"}, "invalid_dispatch_host")
    _positive(capacity, "capacity")
    inventory = {path.relative_to(run_dir).as_posix(): _digest(path)
                 for path in sorted(run_dir.rglob("*")) if path.is_file() and not path.is_relative_to(_directory(run_dir))
                 and path.name != "dispatch_policy.json"}
    binding = _binding(manifest)
    candidate = {"schema_version": VERSION, "kind": kind, "host": host, "capacity": capacity,
                 "binding_sha256": binding, "history_sha256": _sha(inventory),
                 "adapter_sha256": _digest(Path(__file__)), "policy": {"initial_target": DEFAULT_TARGET, "maximum": DEFAULT_MAXIMUM}}
    return {"status": "planned", "state": "paused", "run_id": manifest.get("run_id", manifest.get("fanout_id")),
            "binding_sha256": binding, "candidate_sha256": _sha(candidate), "candidate": candidate,
            "history_inventory": inventory, "controller_counts": {key: value for key, value in report.items() if isinstance(value, int)},
            "payload_values_included": False}


def _authorize_request(run_dir, request, request_root, action, plan):
    from recovery_decision import decide
    require(request is not None, "reviewed_recovery_request_required")
    value = _read(request) if isinstance(request, (str, Path)) else request
    require(isinstance(value, dict) and value.get("action") == action and value.get("run_id") == plan["run_id"]
            and value.get("binding_sha256") == plan["binding_sha256"] and value.get("candidate_sha256") == plan["candidate_sha256"], "migration_request_binding_mismatch")
    result = decide(Path(request_root or run_dir), value)
    require(result["outcome"] == "proceed", "recovery_decision_" + result["outcome"])
    return value, result


def _authorize_migration(db, run_dir, request, request_root, action):
    plan = json.loads(_meta(db, "migration_plan"))
    current = _migration_plan(Path(run_dir), plan["candidate"]["kind"], plan["candidate"]["host"], plan["candidate"]["capacity"])
    require(current["binding_sha256"] == plan["binding_sha256"], "migration_scientific_binding_changed")
    require(current["history_inventory"] == plan["history_inventory"], "migration_history_changed")
    require(current["candidate_sha256"] == plan["candidate_sha256"], "migration_candidate_changed")
    _authorize_request(run_dir, request, request_root, action, plan)


def migrate(run_dir, *, kind, owner=None, host, capacity=DEFAULT_TARGET, request=None, request_root=None, dry_run=True):
    """Opt-in operational migration; migration approval alone never resumes dispatch."""
    run_dir = Path(run_dir).resolve()
    plan = _migration_plan(run_dir, kind, host, capacity)
    if dry_run:
        return plan
    require(_policy(run_dir) is None and not _db_path(run_dir).exists(), "migration_requires_legacy_run")
    value, decision = _authorize_request(run_dir, request, request_root, "operational_migration", plan)
    # Preserve authority and all old run bytes before publishing any activation marker.
    _publish(_directory(run_dir) / "migration_plan.json", plan)
    _publish(_directory(run_dir) / "migration_authority.json", {"request": value, "decision": decision})
    with _db(run_dir, write=True, create=True) as db:
        _set_meta(db, "migration_plan", json.dumps(plan, sort_keys=True))
        _set_meta(db, "migration_state", "paused")
        _event(db, "migration_staged", candidate_sha256=plan["candidate_sha256"], binding_sha256=plan["binding_sha256"])
    initialize_policy(run_dir)
    # Bind the additive policy to the staged migration in the same guarded store.
    with _db(run_dir, write=True) as db:
        pass
    return {**plan, "status": "migrated", "state": "paused", "resume_requires": "resume_dispatch"}


def recover_session(run_dir, *, expected_owner, owner, request=None, request_root=None, dry_run=True):
    """Reviewed owner recovery. It never resolves finality by elapsed time or PID reuse."""
    run_dir = Path(run_dir).resolve()
    require(isinstance(owner, str) and 0 < len(owner) <= 240 and owner != expected_owner, "new_native_session_owner_required")
    with _db(run_dir, write=not dry_run) as db:
        session = _owned(db, expected_owner)
        _verify_reconciled(db, run_dir, session)
        manifest, _ = _controller(run_dir, session["kind"])
        binding = _binding(manifest)
        require(binding == session["binding"], "dispatch_scientific_binding_changed")
        head = db.execute("SELECT sha256 FROM events ORDER BY sequence DESC LIMIT 1").fetchone()[0]
        candidate = {"schema_version": VERSION, "session_id": session["id"], "expected_owner": expected_owner,
                     "new_owner": owner, "host": session["host"], "binding_sha256": binding,
                     "adapter_sha256": _digest(Path(__file__)), "policy_sha256": _meta(db, "policy_sha256"),
                     "event_head_sha256": head}
        plan = {"run_id": manifest.get("run_id", manifest.get("fanout_id")), "binding_sha256": binding,
                "candidate_sha256": _sha(candidate), "candidate": candidate, "state": "paused",
                "status": "recovery_planned", "payload_values_included": False}
        value = _session_view(db, session, include_tickets=False)
        plan["unresolved_attempts"] = value["active"] + value["unknown"] + value["queued"] + value["returned"]
        if dry_run:
            return plan
        _authorize_request(run_dir, request, request_root, "resume_dispatch", plan)
        require(value["can_close"], "dispatch_finality_unresolved")
        db.execute("UPDATE sessions SET state='closed' WHERE id=?", (session["id"],))
        _event(db, "ownership_recovered", session_id=session["id"], old_owner=expected_owner,
               new_owner=owner, candidate_sha256=plan["candidate_sha256"])
        _event(db, "session_closed", session_id=session["id"], recovered=True)
        return {**plan, "status": "owner_recovered", "state": "ready", "owner": owner}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["open-session", "start", "finish", "intent", "ack", "inspect", "reconcile", "checkpoint", "close-session", "migrate", "recover-session", "resolve-backoff"])
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--ticket", type=Path)
    parser.add_argument("--kind", choices=["coding", "research"])
    parser.add_argument("--owner")
    parser.add_argument("--expected-owner")
    parser.add_argument("--host", choices=["codex", "claude"])
    parser.add_argument("--capacity", type=int, default=DEFAULT_TARGET)
    parser.add_argument("--concurrency", type=int)
    parser.add_argument("--block", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--include-exhausted", action="store_true")
    parser.add_argument("--evidence-sha256")
    parser.add_argument("--host-evidence", type=Path)
    parser.add_argument("--throttled", action="store_true")
    parser.add_argument("--retry-after-seconds", type=int)
    parser.add_argument("--stop-admissions", action="store_true")
    parser.add_argument("--passed", action="store_true")
    parser.add_argument("--request", type=Path)
    parser.add_argument("--request-root", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command in {"start", "finish", "intent", "ack"}:
            require(args.ticket is not None, "ticket_required")
            result = (start(args.ticket) if args.command == "start" else finish(args.ticket) if args.command == "finish" else
                      record_intent(args.ticket, args.owner) if args.command == "intent" else acknowledge(args.ticket, args.owner, args.evidence_sha256))
        else:
            require(args.run_dir is not None, "run_directory_required")
            if args.command == "open-session":
                result = open_session(args.run_dir, kind=args.kind, owner=args.owner, host=args.host, capacity=args.capacity,
                                      concurrency=args.concurrency, block=args.block, limit=args.limit, include_exhausted=args.include_exhausted,
                                      resume_request=args.request, request_root=args.request_root)
            elif args.command == "inspect":
                result = inspect(args.run_dir)
            elif args.command == "reconcile":
                evidence = json.load(sys.stdin) if args.host_evidence == Path("-") else _read(args.host_evidence) if args.host_evidence else None
                result = reconcile(args.run_dir, args.owner, outcomes=evidence,
                                   throttled=args.throttled, stop_admissions=args.stop_admissions, retry_after_seconds=args.retry_after_seconds)
            elif args.command == "checkpoint":
                result = checkpoint(args.run_dir, args.owner, passed=args.passed)
            elif args.command == "close-session":
                result = close_session(args.run_dir, args.owner)
            elif args.command == "migrate":
                result = migrate(args.run_dir, kind=args.kind, owner=args.owner, host=args.host, capacity=args.capacity,
                                 request=args.request, request_root=args.request_root, dry_run=args.dry_run)
            elif args.command == "resolve-backoff":
                result = resolve_backoff(args.run_dir, args.owner, args.evidence_sha256)
            else:
                result = recover_session(args.run_dir, expected_owner=args.expected_owner, owner=args.owner,
                                         request=args.request, request_root=args.request_root, dry_run=args.dry_run)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError) as exc:
        reason = str(exc) if isinstance(exc, DispatchError) else "invalid_or_unavailable_dispatch_evidence"
        print(json.dumps({"error": "dispatch_failed_closed", "reason_code": reason, "payload_values_included": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
