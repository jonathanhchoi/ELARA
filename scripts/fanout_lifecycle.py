"""Payload-free, provider-neutral launch journal. Never calls a model or changes a return.

The host owns dispatch. This module owns durable intent/acknowledgement records and
replay, not scientific validation or retry eligibility. An absent acknowledgement
is UNKNOWN FINALITY, not permission to dispatch the same attempt again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

VERSION = "1.0"
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
TRANSITIONS = {"intent": {"acknowledged", "returned"},
               "acknowledged": {"returned"}, "returned": {"validated"},
               "validated": {"reconciled"}, "reconciled": set()}
PHASES = {"paused", "verifying", "dispatching", "waiting", "reconciling", "stopped", "complete"}


class LifecycleError(ValueError):
    """Closed operational failure; no underlying exception is exposed."""


def require(test, code):
    if not test:
        raise LifecycleError(code)


def digest(path):
    with Path(path).open("rb") as stream:
        h = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
        return h.hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n").encode()


def publish(path, value):
    """Create once; identical retry is safe. Never replace prior checkpoint evidence."""
    path = Path(path)
    data = json_bytes(value)
    if path.exists():
        require(path.read_bytes() == data, "checkpoint_conflict")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    import tempfile
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".checkpoint-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(name, path)
        except FileExistsError:
            require(path.read_bytes() == data, "checkpoint_conflict")
    finally:
        os.unlink(name)


def identity(pid):
    """PID plus OS creation identity; unsupported/ambiguous is never 'dead'."""
    require(type(pid) is int and pid > 0, "invalid_pid")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)
        if not handle:
            if ctypes.get_last_error() == 87:
                return None
            raise LifecycleError("process_identity_unavailable")
        try:
            state = kernel.WaitForSingleObject(handle, 0)
            if state == 0:
                return None
            require(state == 258, "process_identity_unavailable")
            values = [wintypes.FILETIME() for _ in range(4)]
            require(kernel.GetProcessTimes(handle, *(ctypes.byref(x) for x in values)), "process_identity_unavailable")
            return f"{pid}:{values[0].dwHighDateTime << 32 | values[0].dwLowDateTime}"
        finally:
            kernel.CloseHandle(handle)
    if sys.platform == "darwin":
        import ctypes
        import errno
        # Apple's public proc_bsdinfo ABI (xnu/bsd/sys/proc_info.h): the
        # creation timeval follows a 120-byte prefix. Do not use ps's
        # second-resolution lstart string for PID-reuse decisions.
        class BsdInfo(ctypes.Structure):
            _fields_ = [("prefix", ctypes.c_ubyte * 120),
                        ("start_seconds", ctypes.c_uint64), ("start_microseconds", ctypes.c_uint64)]
        lib = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
        lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
        lib.proc_pidinfo.restype = ctypes.c_int
        value = BsdInfo()
        result = lib.proc_pidinfo(pid, 3, 0, ctypes.byref(value), ctypes.sizeof(value))
        if result == 0 and ctypes.get_errno() == errno.ESRCH:
            return None
        require(result == ctypes.sizeof(value), "process_identity_unavailable")
        return f"{pid}:{value.start_seconds}:{value.start_microseconds}"
    stat = Path(f"/proc/{pid}/stat")
    if not stat.exists():
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return None
        except PermissionError:
            pass
        raise LifecycleError("process_identity_unavailable")
    start = stat.read_text().rsplit(")", 1)[1].split()[19]
    boot = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    return f"{pid}:{boot}:{start}"


class VerificationTransaction:
    """Reuse costly proof computation only while EVERY bound byte still hashes identically.

    Process-local only: no stat-only trust, persistent bypass, or cross-wave cache.
    Hash checks remain mandatory; recursive proof work runs once per fingerprint.
    """
    def __init__(self, root, bindings):
        self.root, self.bindings, self.proven = Path(root).resolve(), dict(bindings), False

    def verify(self, proof):
        for relative, expected in self.bindings.items():
            path = (self.root / relative).resolve()
            require(not Path(relative).is_absolute() and path.is_relative_to(self.root), "binding_path_escape")
            require(DIGEST.fullmatch(expected) and digest(path) == expected, "binding_drift")
        if not self.proven:
            proof()
            # Proof may itself have observed or caused an intervening write.
            for relative, expected in self.bindings.items():
                require(digest(self.root / relative) == expected, "binding_drift")
            self.proven = True


class Journal:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / "lifecycle.sqlite3"

    def initialize(self, *, scientific_sha256, operational_sha256, concurrency, max_attempts=2):
        require(DIGEST.fullmatch(scientific_sha256) and DIGEST.fullmatch(operational_sha256), "invalid_binding")
        require(type(concurrency) is int and concurrency > 0 and type(max_attempts) is int and 1 <= max_attempts <= 2, "invalid_limits")
        self.directory.mkdir(parents=True, exist_ok=True)
        require(not self.path.exists(), "already_initialized")
        # O_EXCL also prevents two initializers from adopting one another's journal.
        with self.path.open("xb"):
            pass
        with self.connection(write=True, initializing=True) as db:
            db.executescript("""
                CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE owner (singleton INTEGER PRIMARY KEY CHECK(singleton=1), identity TEXT NOT NULL);
                CREATE TABLE launches (assignment TEXT PRIMARY KEY, unit TEXT NOT NULL, attempt INTEGER NOT NULL,
                    phase TEXT NOT NULL, outcome TEXT, UNIQUE(unit, attempt));
                CREATE TABLE events (seq INTEGER PRIMARY KEY, event TEXT NOT NULL, previous TEXT NOT NULL, sha256 TEXT NOT NULL);
            """)
            initial = dict(version=VERSION, scientific_sha256=scientific_sha256,
                             operational_sha256=operational_sha256, concurrency=concurrency,
                             max_attempts=max_attempts, phase="paused")
            for k, v in initial.items():
                db.execute("INSERT INTO settings VALUES (?,?)", (k, str(v)))
            self._append(db, {"kind": "initialized", "settings": {k: str(v) for k, v in initial.items()}})

    @contextmanager
    def connection(self, *, write=False, initializing=False):
        require(self.path.is_file(), "not_initialized")
        uri = self.path.resolve().as_uri() + ("?mode=rw" if write else "?mode=ro")
        db = sqlite3.connect(uri, uri=True, timeout=5)
        try:
            if write:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("BEGIN IMMEDIATE")
            else:
                db.execute("BEGIN")
            if not initializing:
                require(dict(db.execute("SELECT key,value FROM settings")).get("version") == VERSION, "unsupported_journal")
                if write:
                    self._inspect(db)
            yield db
            if write:
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _append(self, db, event):
        row = db.execute("SELECT sha256 FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        previous = row[0] if row else "0" * 64
        raw = json_bytes(event).decode()
        sha = hashlib.sha256((previous + raw).encode()).hexdigest()
        db.execute("INSERT INTO events(event,previous,sha256) VALUES (?,?,?)", (raw, previous, sha))

    def _owned(self, db):
        row = db.execute("SELECT identity FROM owner WHERE singleton=1").fetchone()
        require(row is not None and row[0] == identity(os.getpid()), "not_owner")

    @contextmanager
    def ownership(self):
        token = identity(os.getpid())
        with self.connection(write=True) as db:
            require(db.execute("SELECT COUNT(*) FROM owner").fetchone()[0] == 0, "owner_exists_review_before_recovery")
            db.execute("INSERT INTO owner VALUES (1,?)", (token,))
            self._append(db, {"kind": "owner_acquired", "identity": token})
        try:
            yield self
        finally:
            with self.connection(write=True) as db:
                self._owned(db)
                self._append(db, {"kind": "owner_released", "identity": token})
                db.execute("DELETE FROM owner WHERE singleton=1")

    def recover_owner(self, *, expected_identity, review_sha256):
        require(DIGEST.fullmatch(review_sha256), "review_required")
        with self.connection(write=True) as db:
            row = db.execute("SELECT identity FROM owner WHERE singleton=1").fetchone()
            require(row is not None and row[0] == expected_identity, "owner_mismatch")
            pid = int(expected_identity.split(":", 1)[0])
            require(identity(pid) != expected_identity, "owner_still_alive")
            self._append(db, {"kind": "owner_recovery", "identity": expected_identity, "review_sha256": review_sha256})
            db.execute("DELETE FROM owner WHERE singleton=1")

    def intent(self, assignment, unit, attempt, *, retry_receipt_sha256=None):
        require(IDENTIFIER.fullmatch(assignment) and IDENTIFIER.fullmatch(unit), "invalid_identifier")
        require(type(attempt) is int and attempt in (1, 2), "invalid_attempt")
        with self.connection(write=True) as db:
            self._owned(db)
            settings = dict(db.execute("SELECT key,value FROM settings"))
            require(attempt <= int(settings["max_attempts"]), "attempt_limit")
            require(not db.execute("SELECT 1 FROM launches WHERE assignment=? OR (unit=? AND attempt=?)", (assignment, unit, attempt)).fetchone(), "attempt_already_recorded")
            prior = db.execute("SELECT attempt,phase,outcome FROM launches WHERE unit=? ORDER BY attempt DESC LIMIT 1", (unit,)).fetchone()
            if attempt == 2:
                require(prior == (1, "reconciled", "retryable") and isinstance(retry_receipt_sha256, str)
                        and DIGEST.fullmatch(retry_receipt_sha256), "linked_retry_not_proven")
            else:
                require(prior is None, "unit_already_recorded")
            active = db.execute("SELECT COUNT(*) FROM launches WHERE phase!='reconciled'").fetchone()[0]
            require(active < int(settings["concurrency"]), "concurrency_limit")
            db.execute("INSERT INTO launches VALUES (?,?,?,'intent',NULL)", (assignment, unit, attempt))
            self._append(db, {"kind": "intent", "assignment": assignment, "unit": unit,
                              "attempt": attempt, "retry_receipt_sha256": retry_receipt_sha256})

    def advance(self, assignment, phase, *, evidence_sha256, outcome=None):
        require(phase in {"acknowledged", "returned", "validated", "reconciled"}
                and DIGEST.fullmatch(evidence_sha256), "invalid_transition")
        require(outcome in (None, "succeeded", "retryable", "exhausted"), "invalid_outcome")
        with self.connection(write=True) as db:
            self._owned(db)
            row = db.execute("SELECT phase,outcome,attempt FROM launches WHERE assignment=?", (assignment,)).fetchone()
            require(row is not None, "unknown_assignment")
            if row[0] == phase:
                prior = db.execute("SELECT event FROM events ORDER BY seq DESC").fetchall()
                expected = {"kind": phase, "assignment": assignment, "evidence_sha256": evidence_sha256, "outcome": outcome}
                require(any(json.loads(x[0]) == expected for x in prior), "event_conflict")
                return
            require(phase in TRANSITIONS[row[0]], "transition_out_of_order")
            if phase == "validated":
                require(outcome is not None and not (outcome == "retryable" and row[2] == 2), "invalid_validation_disposition")
            elif phase == "reconciled":
                require(outcome == row[1] and outcome is not None, "reconciliation_mismatch")
            else:
                require(outcome is None, "premature_outcome")
            db.execute("UPDATE launches SET phase=?,outcome=? WHERE assignment=?", (phase, outcome, assignment))
            self._append(db, {"kind": phase, "assignment": assignment, "evidence_sha256": evidence_sha256, "outcome": outcome})

    def progress(self, phase, *, failure_class=None, fingerprint=None):
        require(phase in PHASES, "invalid_phase")
        require(failure_class in (None, "unit", "infrastructure", "scientific", "authorization"), "invalid_failure_class")
        require(fingerprint is None or DIGEST.fullmatch(fingerprint), "invalid_fingerprint")
        with self.connection(write=True) as db:
            self._owned(db)
            db.execute("UPDATE settings SET value=? WHERE key='phase'", (phase,))
            self._append(db, {"kind": "phase", "phase": phase, "failure_class": failure_class,
                              "fingerprint": fingerprint, "at": datetime.now(timezone.utc).isoformat()})

    def inspect(self):
        with self.connection() as db:
            return self._inspect(db)

    def _inspect(self, db):
        settings = dict(db.execute("SELECT key,value FROM settings"))
        counts = dict(db.execute("SELECT phase,COUNT(*) FROM launches GROUP BY phase"))
        outcomes = dict(db.execute("SELECT outcome,COUNT(*) FROM launches WHERE phase='reconciled' GROUP BY outcome"))
        owner = db.execute("SELECT identity FROM owner").fetchone()
        events = db.execute("SELECT event,previous,sha256 FROM events ORDER BY seq").fetchall()
        actual = {a: (u, n, p, o) for a, u, n, p, o in db.execute("SELECT assignment,unit,attempt,phase,outcome FROM launches")}
        previous, repeated, last_failure = "0" * 64, 0, None
        replay, replay_phase = {}, "paused"
        replay_owner, initial = None, None
        for index, (raw, prev, sha) in enumerate(events):
            require(prev == previous and hashlib.sha256((prev + raw).encode()).hexdigest() == sha, "journal_chain_invalid")
            previous = sha
            event = json.loads(raw)
            kind = event["kind"]
            if kind == "initialized":
                require(index == 0 and initial is None, "duplicate_initialization")
                initial = event["settings"]
            elif kind == "owner_acquired":
                require(replay_owner is None, "overlapping_owners")
                replay_owner = event["identity"]
            elif kind in {"owner_released", "owner_recovery"}:
                require(replay_owner == event["identity"], "owner_history_invalid")
                replay_owner = None
            elif kind == "intent":
                key = event["assignment"]
                require(key not in replay, "duplicate_journal_intent")
                replay[key] = (event["unit"], event["attempt"], "intent", None)
            elif kind in {"acknowledged", "returned", "validated", "reconciled"}:
                key = event["assignment"]
                require(key in replay and kind in TRANSITIONS[replay[key][2]], "journal_transition_invalid")
                u, n, _, _ = replay[key]
                replay[key] = (u, n, kind, event["outcome"])
            elif kind == "phase":
                replay_phase = event["phase"]
            else:
                raise LifecycleError("unknown_journal_event")
            if event["kind"] == "reconciled":
                repeated, last_failure = 0, None
            elif event["kind"] == "phase" and event["fingerprint"]:
                repeated = repeated + 1 if last_failure == event["fingerprint"] else 1
                last_failure = event["fingerprint"]
        require(actual == replay and settings["phase"] == replay_phase, "journal_view_drift")
        require(initial is not None and {k: v for k, v in settings.items() if k != "phase"}
                == {k: v for k, v in initial.items() if k != "phase"}, "journal_settings_drift")
        require((owner[0] if owner else None) == replay_owner, "journal_owner_drift")
        unknown = counts.get("intent", 0) + counts.get("acknowledged", 0)
        action = ("review_owner" if owner else "diagnose_new_evidence" if repeated >= 2 else
                  "resolve_unknown_finality" if unknown else "validate_existing_returns" if counts.get("returned", 0) else
                  "reconcile_existing_validation" if counts.get("validated", 0) else "consult_controller_pending")
        return {"schema_version": VERSION, "phase": settings["phase"], "launch_states": counts,
                "reconciled_attempts": outcomes, "acknowledged_launches": sum(1 for raw, _, _ in events if json.loads(raw)["kind"] == "acknowledged"),
                "owner_identity": owner[0] if owner else None, "unknown_finality": unknown,
                "repeated_failure_count": repeated, "next_action": action, "event_count": len(events),
                "event_head_sha256": previous, "scientific_sha256": settings["scientific_sha256"],
                "operational_sha256": settings["operational_sha256"], "payload_values_included": False}

    def checkpoint(self, path):
        with self.connection() as db:
            value = self._inspect(db)
            require(value["owner_identity"] is None, "checkpoint_requires_quiescence")
            publish(path, value)
        return {"status": "checkpointed", "sha256": digest(path), "payload_values_included": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inspect", "checkpoint", "resume-plan"])
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        journal = Journal(args.directory)
        result = journal.checkpoint(args.output) if args.command == "checkpoint" and args.output else journal.inspect()
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except Exception:
        print('{"error":"lifecycle_failed_closed","payload_values_included":false}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
