"""Run a pilot, coding, audit, or robustness run from one settings file.

Stages 08, 11, 12, and 15 use this runner instead of project-written drivers.
A project supplies a settings file (see ``workflow/templates/coding_run_settings.md``)
and a unit list; the runner does the rest around ``scripts/unit_fanout.py``:

    sample   --settings S --units U.csv --out SAMPLE.csv
             reproducible hash-ranked draw (strata, exclusions, filters)
    prepare  --settings S --units U --run-dir project/runs/<run_id> [--dry-run]
             source views (full, line-numbered, or windows), one assignment per
             unit x condition x replicate, sealed run manifest
    check    --run-dir D [--apply] [--skip-retry ID ...] [--decided-by WHO]
             output-format and quotation checks, the frozen retry rule, the
             failure-decision log, the stopping rule, and the next step
    close    --run-dir D [--version NNN] [--artifacts-dir A]
             the stage's dataset, ledger, and check files plus a receipt
    review   --run-dir D [--version NNN] [--human-codes H.csv] [--blind]
             the researcher review sheet (blinded with a separate key if asked)
    compare  --run-dir D [--version NNN] [--human-codes H.csv]
             agreement and disagreement tables across conditions, replicates,
             and human codes

The runner never calls a model. The host's saved workflow (Claude Code) or the
kit's custom sub-agents (Codex) run the workers on the run directory that
``prepare`` creates; ``check`` prints the exact launch arguments. Every command
reads the run's files only, so any command can be repeated after an
interruption. Status output is operational: counts, statuses, and paths, never
coded values. ``review`` and ``compare`` show coded values and refuse to run
before ``close``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import unit_fanout as fanout  # noqa: E402

FanoutError = fanout.FanoutError


RUNNER_VERSION = "1.0"
SETTINGS_VERSION = "1.0"
AUDIT_STAGE = "12-interpretive-verification"
STAGES = ("08-pilot", "11-scale-up", AUDIT_STAGE, "15-robustness")
VIEW_MODES = ("full", "lines", "window")
NORMALIZE_MODES = ("exact", "whitespace", "alphanumeric")
LOCATOR_MODES = ("none", "line", "offset")
RETRYABLE = ("schema_failed", "quote_failed", "worker_error", "refused", "unreadable", "wrong_document")
FAILING_ANCHOR = {"empty", "too_short", "too_long", "unknown_source", "bad_locator", "not_found"}
AUDIT_DISPOSITIONS = ("supported", "unsupported", "ambiguous")
DEFAULT_REVIEW_COLUMNS = (
    "researcher_valid (yes/no)",
    "problem_kind (coder error / codebook ambiguity / construct disagreement / source problem / unusable source)",
    "reason",
    "adjudicator",
)
DISAGREEMENT_COLUMNS = (
    "kind (label disagreement / missed observation / unsupported quote / attribution error / unit error / ambiguity / unusable source)",
    "disposition",
)
PATH_RE = re.compile(r"^(?:[A-Za-z0-9_-]+(?:\[\])?|\[\])(?:\.[A-Za-z0-9_-]+(?:\[\])?)*$")
LINE_LOCATOR = re.compile(r"^\s*L(\d+)(?:\s*[-\u2013]\s*L?(\d+))?\s*$")
VERSION_RE = re.compile(r"^\d{3}$")
SAFE = {"type": "string", "pattern": fanout.SAFE_ID.pattern}
TEXT = {"type": "string", "minLength": 1}

TASK_CODING = (
    "Code this one unit. Read every file in read_in_order, in that order, then every file in "
    "sources, and apply them exactly as written. Put the coded output in the envelope's result "
    "field so that it matches the result_schema file. Quote evidence exactly as it appears in the "
    "source text, without the line labels (such as 'L12: ') and without the target markers."
)
TASK_AUDIT = (
    "Audit this one coded observation. Read every file in read_in_order, in that order, then the "
    "observation below and every file in sources. Decide only whether the observation's evidence "
    "supports its label under the codebook definition: disposition is supported, unsupported, or "
    "ambiguous. Give your reasoning and every source location you inspected, in a result that "
    "matches the result_schema file. Do not propose a different label."
)

ANCHOR_SCHEMA = {
    "type": "object",
    "required": ["path"],
    "additionalProperties": False,
    "properties": {
        "path": TEXT,
        "quote_field": TEXT,
        "source_field": TEXT,
        "locator_field": TEXT,
        "start_field": TEXT,
        "end_field": TEXT,
    },
}
SETTINGS_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["settings_version", "stage", "inputs"],
    "additionalProperties": False,
    "properties": {
        "settings_version": {"const": SETTINGS_VERSION},
        "stage": {"enum": list(STAGES)},
        "description": {"type": "string"},
        "inputs": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["role", "path"],
                "additionalProperties": False,
                "properties": {
                    "role": SAFE,
                    "path": TEXT,
                    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                },
            },
        },
        "read": {"type": "array", "minItems": 1, "items": SAFE},
        "units": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "id_column": TEXT,
                "fields": {"type": "array", "items": TEXT},
                "sources": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "type": "object",
                        "required": ["source_id", "path_column"],
                        "additionalProperties": False,
                        "properties": {
                            "source_id": SAFE,
                            "path_column": TEXT,
                            "sha256_column": TEXT,
                            "root": TEXT,
                        },
                    },
                },
                "max_chars": {"type": "integer", "minimum": 1},
            },
        },
        "view": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "mode": {"enum": list(VIEW_MODES)},
                "words_before": {"type": "integer", "minimum": 0},
                "words_after": {"type": "integer", "minimum": 0},
                "target_start_column": TEXT,
                "target_end_column": TEXT,
                "target_pattern": TEXT,
                "target_ignore_case": {"type": "boolean"},
                "marker_before": {"type": "string"},
                "marker_after": {"type": "string"},
            },
        },
        "conditions": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_]{0,39}$"},
                    "replicates": {"type": "integer", "minimum": 1, "maximum": 10},
                    "model": TEXT,
                    "effort": TEXT,
                    "replace": {"type": "object", "additionalProperties": SAFE},
                    "description": {"type": "string"},
                },
            },
        },
        "batch_size": {"type": "integer", "minimum": 1, "maximum": 998},
        "time_box_minutes": {"type": "integer", "minimum": 1, "maximum": 240},
        "quotes": {
            "type": "object",
            "required": ["anchors"],
            "additionalProperties": False,
            "properties": {
                "anchors": {"type": "array", "minItems": 1, "items": ANCHOR_SCHEMA},
                "normalize": {"enum": list(NORMALIZE_MODES)},
                "case_sensitive": {"type": "boolean"},
                "fold_quotes": {"type": "boolean"},
                "whole_words": {"type": "boolean"},
                "locator": {"enum": list(LOCATOR_MODES)},
                "line_tolerance": {"type": "integer", "minimum": 0, "maximum": 50},
                "wrong_location": {"enum": ["fail", "pass"]},
                "min_words": {"type": "integer", "minimum": 0},
                "max_words": {"type": "integer", "minimum": 1},
                "unchecked_sources": {"type": "array", "items": TEXT},
            },
        },
        "retry": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "on": {"type": "array", "items": {"enum": list(RETRYABLE)}},
                "max_attempts": {"type": "integer", "minimum": 1, "maximum": fanout.MAX_ATTEMPTS},
            },
        },
        "stop": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "batch_failure_rate": {"type": "number", "minimum": 0, "maximum": 1},
                "cumulative_failure_rate": {"type": "number", "minimum": 0, "maximum": 1},
                "consecutive_same_failure": {"type": "integer", "minimum": 2},
            },
        },
        "sample": {
            "type": "object",
            "required": ["salt"],
            "additionalProperties": False,
            "properties": {
                "salt": TEXT,
                "size": {"type": "integer", "minimum": 1},
                "per_stratum": {"type": "integer", "minimum": 1},
                "strata": {"type": "array", "items": TEXT},
                "exclude": {"type": "array", "items": TEXT},
                "exclude_id_column": TEXT,
                "require": {
                    "type": "object",
                    "additionalProperties": {"type": "array", "items": {"type": "string"}},
                },
                "one_per": TEXT,
                "min_chars": {"type": "integer", "minimum": 0},
                "max_chars": {"type": "integer", "minimum": 1},
            },
        },
        "review": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "columns": {"type": "array", "minItems": 1, "items": TEXT},
                "blind_seed": {"type": "integer"},
                "human_id_column": TEXT,
            },
        },
        "compare": {
            "type": "object",
            "required": ["fields"],
            "additionalProperties": False,
            "properties": {
                "fields": {"type": "array", "minItems": 1, "items": TEXT},
                "human_codes": TEXT,
                "human_id_column": TEXT,
                "human_coder_column": TEXT,
                "human_columns": {"type": "object", "additionalProperties": TEXT},
                "reference": TEXT,
                "bootstrap": {
                    "type": "object",
                    "required": ["seed"],
                    "additionalProperties": False,
                    "properties": {
                        "resamples": {"type": "integer", "minimum": 100, "maximum": 100000},
                        "seed": {"type": "integer"},
                    },
                },
            },
        },
        "audit": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "observations": TEXT,
                "observation_id_field": TEXT,
                "show_fields": {"type": "array", "items": TEXT},
                "hide_fields": {"type": "array", "items": TEXT},
            },
        },
        "project_code": TEXT,
    },
}

CLOSE_OUTPUTS: dict[str, dict[str, tuple[str, str]]] = {
    "08-pilot": {
        "dataset": ("run", "normalized_outputs.jsonl"),
        "ledger": ("run", "pilot_ledger.csv"),
        "checks": ("run", "schema_quote_compliance.csv"),
        "quotes": ("run", "quote_checks.csv"),
    },
    "11-scale-up": {
        "dataset": ("artifact", "coding_dataset_v{v}.jsonl"),
        "ledger": ("artifact", "coding_ledger_v{v}.csv"),
        "checks": ("artifact", "schema_validation_v{v}.csv"),
        "quotes": ("artifact", "quote_verification_v{v}.csv"),
    },
    AUDIT_STAGE: {
        "dataset": ("artifact", "interpretive_audit_v{v}.jsonl"),
        "coverage": ("artifact", "interpretive_audit_coverage_v{v}.csv"),
        "queue": ("artifact", "interpretive_recoding_queue_v{v}.csv"),
        "ledger": ("run", "audit_ledger.csv"),
        "checks": ("run", "audit_checks.csv"),
    },
    "15-robustness": {
        "dataset": ("artifact", "robustness_dataset_v{v}.jsonl"),
        "ledger": ("run", "robustness_ledger.csv"),
        "checks": ("run", "schema_quote_checks.csv"),
        "quotes": ("run", "quote_checks.csv"),
    },
}
REVIEW_OUTPUTS: dict[str, tuple[str, str]] = {"08-pilot": ("artifact", "pilot_researcher_review_v{v}.csv")}
COMPARE_OUTPUTS: dict[str, dict[str, tuple[str, str]]] = {
    "08-pilot": {
        "metrics": ("run", "agreement.json"),
        "disagreements": ("artifact", "pilot_disagreements_v{v}.csv"),
        "disagreeing_units": ("run", "disagreeing_units.csv"),
    },
    "15-robustness": {
        "metrics": ("artifact", "robustness_metrics_v{v}.json"),
        "disagreements": ("run", "condition_disagreements.csv"),
        "disagreeing_units": ("run", "disagreeing_units.csv"),
    },
}
DEFAULT_COMPARE_OUTPUTS = {
    "metrics": ("run", "agreement.json"),
    "disagreements": ("run", "disagreements.csv"),
    "disagreeing_units": ("run", "disagreeing_units.csv"),
}


class RunnerError(ValueError):
    """A settings, input, or reconciliation problem; nothing was written."""


# --------------------------------------------------------------------------- helpers


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_text(text: str) -> str:
    return _sha_bytes(text.encode("utf-8"))


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot read JSON from {path}: {exc}") from exc


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = [dict(row) for row in reader]
            return list(reader.fieldnames or []), rows
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise RunnerError(f"cannot read CSV from {path}: {exc}") from exc


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise RunnerError(f"{path} line {number} is not a JSON object")
                rows.append(value)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot read JSONL from {path}: {exc}") from exc
    return rows


def _refuse_existing(paths: Iterable[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise RunnerError("refusing to overwrite: " + ", ".join(existing))


def _write_exclusive(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def _csv_text(header: list[str], rows: list[dict[str, Any]]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=header, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _cell(row.get(key)) for key in header})
    return "\ufeff" + buffer.getvalue()


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _jsonl_text(rows: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)


def _relative(path: Path | str, start: Path) -> str:
    try:
        return Path(os.path.relpath(Path(path), start)).as_posix()
    except ValueError:  # different drives on Windows
        return str(path)


def _resolve(base: Path, value: str) -> Path:
    candidate = Path(value)
    return (candidate if candidate.is_absolute() else base / candidate).resolve()


def _walk(value: Any, path: str) -> list[tuple[str, Any]]:
    """Return (location, value) pairs for a simple path such as ``obs[].anchors[].quote``."""

    found: list[tuple[str, Any]] = []

    def visit(current: Any, segments: list[str], location: str) -> None:
        if not segments:
            found.append((location, current))
            return
        segment = segments[0]
        many = segment.endswith("[]")
        key = segment[:-2] if many else segment
        if key:
            if not isinstance(current, dict) or key not in current:
                return
            current = current[key]
            location = f"{location}.{key}" if location else key
        if many:
            if not isinstance(current, list):
                return
            for index, item in enumerate(current):
                visit(item, segments[1:], f"{location}[{index}]")
        else:
            visit(current, segments[1:], location)

    visit(value, path.split("."), "")
    return found


def _get_field(value: Any, path: str) -> Any:
    current = value
    for key in path.split("."):
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, item in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, dict):
                flat.update(_flatten(item, name))
            else:
                flat[name] = item
    elif prefix:
        flat[prefix] = value
    return flat


def _read_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _git(directory: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(directory), *args],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _project_code_record(path: Path) -> dict[str, Any]:
    if not path.is_dir():
        raise RunnerError(f"project_code folder does not exist: {path}")
    lines: list[str] = []
    count = 0
    for file in sorted(path.rglob("*")):
        if not file.is_file() or any(part in {".git", "__pycache__"} for part in file.parts):
            continue
        lines.append(f"{file.relative_to(path).as_posix()}\0{fanout.sha256_file(file)}\n")
        count += 1
    record: dict[str, Any] = {
        "path": str(path),
        "files": count,
        "tree_sha256": _sha_text("".join(lines)),
    }
    commit = _git(path, "rev-parse", "HEAD")
    if commit:
        record["git_commit"] = commit
        porcelain = _git(path, "status", "--porcelain", "--", ".")
        record["git_uncommitted_changes"] = bool(porcelain)
    return record


# --------------------------------------------------------------------------- settings


def load_settings(path: Path) -> tuple[dict[str, Any], bytes]:
    """Read and validate a settings file; every problem is reported at once."""

    path = path.resolve()
    try:
        raw = path.read_bytes()
        settings = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot read settings JSON from {path}: {exc}") from exc
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:  # pragma: no cover - environment guard
        raise RunnerError("install jsonschema (pip install -r requirements.txt)") from exc
    problems = []
    for error in Draft202012Validator(SETTINGS_SCHEMA).iter_errors(settings):
        location = "/".join(str(part) for part in error.absolute_path) or "(top level)"
        problems.append(f"{location}: {error.message}")
    if isinstance(settings, dict):
        try:
            problems.extend(_semantic_problems(settings))
        except (KeyError, TypeError, AttributeError):
            pass  # structural errors are already reported above
    if problems:
        raise RunnerError("settings file is not valid:\n  " + "\n  ".join(sorted(problems)))
    return settings, raw


def _semantic_problems(settings: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    roles = [item["role"] for item in settings["inputs"]]
    if len(roles) != len(set(roles)):
        problems.append("inputs: roles must be unique")
    if "result_schema" not in roles:
        problems.append("inputs: one input must have the role result_schema")
    for role in settings.get("read", []):
        if role not in roles:
            problems.append(f"read: unknown input role {role!r}")
    conditions = settings.get("conditions", [])
    ids = [condition["id"] for condition in conditions]
    if len(ids) != len(set(ids)):
        problems.append("conditions: ids must be unique")
    for condition in conditions:
        for old, new in condition.get("replace", {}).items():
            if old not in roles or new not in roles:
                problems.append(f"conditions/{condition['id']}: replace names an unknown role")
    stage = settings["stage"]
    if stage == AUDIT_STAGE:
        if "audit" not in settings:
            problems.append("audit: required for Stage 12 settings")
    else:
        units = settings.get("units") or {}
        if not units.get("sources"):
            problems.append("units/sources: name at least one source column")
    view = settings.get("view", {})
    if view.get("mode") == "window":
        has_offsets = "target_start_column" in view and "target_end_column" in view
        if has_offsets == ("target_pattern" in view):
            problems.append(
                "view: a window needs target_start_column and target_end_column, or target_pattern"
            )
    for anchor in settings.get("quotes", {}).get("anchors", []):
        if not PATH_RE.fullmatch(anchor["path"]):
            problems.append(f"quotes/anchors: unsupported path {anchor['path']!r}")
    locator = settings.get("quotes", {}).get("locator", "none")
    if locator == "offset" and view.get("mode") == "lines":
        problems.append("quotes: offset locators need a full or window view")
    for field in settings.get("compare", {}).get("fields", []):
        if "[" in field:
            problems.append(f"compare/fields: use a plain dotted path, not {field!r}")
    if settings.get("compare", {}).get("reference") and settings["compare"]["reference"] not in (
        ids or ["base"]
    ):
        problems.append("compare/reference: not a condition id")
    sample = settings.get("sample")
    if sample and ("size" in sample) == ("per_stratum" in sample):
        problems.append("sample: give exactly one of size or per_stratum")
    if sample and "per_stratum" in sample and not sample.get("strata"):
        problems.append("sample: per_stratum needs strata")
    return problems


def _conditions(settings: dict[str, Any]) -> list[dict[str, Any]]:
    conditions = settings.get("conditions") or [{"id": "base"}]
    return [
        {
            "id": item["id"],
            "replicates": item.get("replicates", 1),
            "model": item.get("model"),
            "effort": item.get("effort"),
            "replace": item.get("replace", {}),
        }
        for item in conditions
    ]


def _read_roles(settings: dict[str, Any], condition: dict[str, Any]) -> list[str]:
    roles = [item["role"] for item in settings["inputs"]]
    if "read" in settings:
        base = list(settings["read"])
    else:
        replacements = {
            new for item in _conditions(settings) for new in item["replace"].values()
        }
        base = [role for role in roles if role not in replacements]
    return [condition["replace"].get(role, role) for role in base]


def _resolve_inputs(settings: dict[str, Any], base: Path) -> list[dict[str, str]]:
    resolved = []
    for item in settings["inputs"]:
        path = _resolve(base, item["path"])
        if not path.is_file():
            raise RunnerError(f"input {item['role']} does not exist: {path}")
        digest = fanout.sha256_file(path)
        if item.get("sha256") and item["sha256"] != digest:
            raise RunnerError(f"input {item['role']} does not match its recorded sha256: {path}")
        resolved.append({"role": item["role"], "path": str(path), "sha256": digest})
    return resolved


# --------------------------------------------------------------------------- source views


def _window(text: str, start: int, end: int, view: dict[str, Any]) -> tuple[str, dict[str, int]]:
    """Return the shown excerpt around text[start:end] and where its target sits."""

    before = view.get("words_before", 40)
    after = view.get("words_after", 40)
    tokens = [match.span() for match in re.finditer(r"\S+", text)]
    left = [span for span in tokens if span[1] <= start]
    right = [span for span in tokens if span[0] >= end]
    if before and left:
        window_start = left[-before][0] if len(left) >= before else left[0][0]
    else:
        window_start = start
    if after and right:
        window_end = right[after - 1][1] if len(right) >= after else right[-1][1]
    else:
        window_end = end
    marker_before = view.get("marker_before", ">>> ")
    marker_after = view.get("marker_after", " <<<")
    shown = text[window_start:start] + marker_before + text[start:end] + marker_after + text[end:window_end]
    return shown, {
        "offset": start - window_start,
        "length": end - start,
        "marker_before": len(marker_before),
        "marker_after": len(marker_after),
    }


def _target_span(text: str, row: dict[str, str], view: dict[str, Any]) -> tuple[int, int] | None:
    if "target_pattern" in view:
        flags = re.IGNORECASE if view.get("target_ignore_case") else 0
        match = re.search(view["target_pattern"], text, flags)
        return match.span() if match else None
    try:
        start = int(row.get(view["target_start_column"], ""))
        end = int(row.get(view["target_end_column"], ""))
    except ValueError:
        return None
    if 0 <= start < end <= len(text):
        return start, end
    return None


def _line_view(text: str) -> str:
    return "".join(f"L{number}: {line}\n" for number, line in enumerate(text.splitlines(), 1))


# --------------------------------------------------------------------------- units


def _coding_units(
    settings: dict[str, Any], units_path: Path, base: Path
) -> tuple[list[dict[str, Any]], str]:
    unit_settings = settings["units"]
    id_column = unit_settings.get("id_column", "unit_id")
    header, rows = _read_csv(units_path)
    missing = [
        column
        for column in [id_column, *unit_settings.get("fields", [])]
        + [source["path_column"] for source in unit_settings["sources"]]
        + [source["sha256_column"] for source in unit_settings["sources"] if "sha256_column" in source]
        if column not in header
    ]
    if missing:
        raise RunnerError(f"unit list {units_path} lacks columns: {', '.join(sorted(set(missing)))}")
    seen: set[str] = set()
    units = []
    for number, row in enumerate(rows, 2):
        unit_id = (row.get(id_column) or "").strip()
        if not fanout.SAFE_ID.fullmatch(unit_id):
            raise RunnerError(f"{units_path} row {number}: unit ID {unit_id!r} is not a safe identifier")
        if unit_id in seen:
            raise RunnerError(f"{units_path}: duplicate unit ID {unit_id}")
        seen.add(unit_id)
        sources = []
        for source in unit_settings["sources"]:
            root = _resolve(base, source["root"]) if "root" in source else units_path.parent
            value = (row.get(source["path_column"]) or "").strip()
            entry: dict[str, Any] = {
                "source_id": source["source_id"],
                "original_path": str(_resolve(root, value)) if value else "",
                "expected_sha256": (row.get(source.get("sha256_column", "")) or "").strip().lower(),
            }
            sources.append(entry)
        units.append(
            {
                "unit_id": unit_id,
                "row": row,
                "fields": {field: row.get(field, "") for field in unit_settings.get("fields", [])},
                "sources": sources,
            }
        )
    return units, id_column


def _audit_units(settings: dict[str, Any], units_path: Path) -> list[dict[str, Any]]:
    audit = settings["audit"]
    rows = _read_jsonl(units_path)
    units = []
    seen: set[str] = set()
    for row in rows:
        if row.get("status") != fanout.SUCCESS_STATUS or not isinstance(row.get("result"), dict):
            continue
        slot_id = row.get("slot_id")
        if not isinstance(slot_id, str):
            raise RunnerError(f"{units_path}: rows must come from coding_run.py close (slot_id missing)")
        if audit.get("observations"):
            found = _walk(row["result"], audit["observations"])
            observations = []
            for index, (_location, item) in enumerate(found, 1):
                if not isinstance(item, dict):
                    raise RunnerError(f"{units_path}: observation in {slot_id} is not an object")
                identifier = item.get(audit.get("observation_id_field", "observation_id"))
                observations.append((str(identifier) if identifier else f"{slot_id}--o{index:03d}", item))
        else:
            observations = [(slot_id, row["result"])]
        for observation_id, observation in observations:
            if not fanout.SAFE_ID.fullmatch(observation_id) or observation_id in seen:
                raise RunnerError(f"observation ID {observation_id!r} is unsafe or duplicated")
            seen.add(observation_id)
            shown = dict(observation)
            if audit.get("show_fields"):
                shown = {key: shown[key] for key in audit["show_fields"] if key in shown}
            for key in audit.get("hide_fields", []):
                shown.pop(key, None)
            sources = [
                {
                    "source_id": source["source_id"],
                    "original_path": str(_resolve(units_path.parent, source["path"])),
                    "expected_sha256": source.get("sha256", ""),
                }
                for source in row.get("sources", [])
            ]
            units.append(
                {
                    "unit_id": observation_id,
                    "fields": {"coded_unit_id": row.get("unit_id")},
                    "observation": shown,
                    "sources": sources,
                    "link": {
                        "slot_id": slot_id,
                        "unit_id": row.get("unit_id"),
                        "assignment_id": row.get("assignment_id"),
                        "return_sha256": row.get("return_sha256"),
                    },
                }
            )
    if not units:
        raise RunnerError(f"{units_path} has no succeeded coded rows to audit")
    return units


def _build_views(
    units: list[dict[str, Any]], settings: dict[str, Any], run_dir: Path
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    """Read sources, check hashes, and build view files (kept in memory until written)."""

    view = settings.get("view", {})
    mode = view.get("mode", "full")
    max_chars = (settings.get("units") or {}).get("max_chars")
    files: dict[str, dict[str, str]] = {}
    gaps = []
    for unit in units:
        reason = None
        for source in unit["sources"]:
            path = Path(source["original_path"]) if source["original_path"] else None
            if path is None or not path.is_file():
                reason = f"source {source['source_id']} file is missing"
                break
            digest = fanout.sha256_file(path)
            if source["expected_sha256"] and source["expected_sha256"] != digest:
                raise RunnerError(
                    f"unit {unit['unit_id']}: source {source['source_id']} does not match its recorded sha256 ({path})"
                )
            try:
                text = _read_text(path)
            except UnicodeDecodeError:
                reason = f"source {source['source_id']} is not UTF-8 text"
                break
            if max_chars and len(text) > max_chars:
                reason = f"source {source['source_id']} exceeds max_chars ({len(text)} > {max_chars})"
                break
            source["original_sha256"] = digest
            source["view"] = mode
            if mode == "full":
                source["path"] = str(path)
                source["sha256"] = digest
                continue
            if mode == "lines":
                shown = _line_view(text)
            else:
                span = _target_span(text, unit.get("row", {}), view)
                if span is None:
                    reason = f"window target not found in source {source['source_id']}"
                    break
                shown, source["target"] = _window(text, span[0], span[1], view)
            view_path = run_dir / "sources" / unit["unit_id"] / f"{source['source_id']}.{mode}.txt"
            files[str(view_path)] = {"text": shown}
            source["path"] = str(view_path)
            source["sha256"] = _sha_text(shown)
        if reason:
            unit["gap"] = {"status": "unreadable", "reason": reason}
            gaps.append({"unit_id": unit["unit_id"], "status": "unreadable", "reason": reason})
            for source in unit["sources"]:
                files.pop(str(run_dir / "sources" / unit["unit_id"] / f"{source['source_id']}.{mode}.txt"), None)
    return files, gaps


def _payload_sources(unit: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for source in unit["sources"]:
        entry = {
            "source_id": source["source_id"],
            "path": source["path"],
            "sha256": source["sha256"],
            "view": source["view"],
        }
        if "target" in source:
            entry["target"] = source["target"]
        entries.append(entry)
    return entries


# --------------------------------------------------------------------------- sample


def sample(settings_path: Path, units_path: Path, out: Path) -> dict[str, Any]:
    """Draw a reproducible sample: rank by SHA-256(salt|unit_id) within each stratum."""

    settings, _raw = load_settings(settings_path)
    if "sample" not in settings:
        raise RunnerError("settings have no sample section")
    plan = settings["sample"]
    base = settings_path.resolve().parent
    units_path = units_path.resolve()
    out = out.resolve()
    _refuse_existing([out])
    unit_settings = settings.get("units") or {}
    id_column = unit_settings.get("id_column", "unit_id")
    header, rows = _read_csv(units_path)
    needed = [id_column, *plan.get("strata", []), *plan.get("require", {}).keys()]
    if plan.get("one_per"):
        needed.append(plan["one_per"])
    missing = sorted({column for column in needed if column not in header})
    if missing:
        raise RunnerError(f"unit list lacks columns: {', '.join(missing)}")

    excluded_ids: set[str] = set()
    for item in plan.get("exclude", []):
        path = _resolve(base, item)
        excl_header, excl_rows = _read_csv(path)
        column = plan.get("exclude_id_column", id_column)
        if column not in excl_header:
            raise RunnerError(f"exclusion list {path} lacks column {column}")
        excluded_ids.update((row.get(column) or "").strip() for row in excl_rows)

    reasons: Counter[str] = Counter()
    eligible = []
    for row in rows:
        unit_id = (row.get(id_column) or "").strip()
        if unit_id in excluded_ids:
            reasons["excluded_by_earlier_list"] += 1
            continue
        if any(row.get(column, "") not in allowed for column, allowed in plan.get("require", {}).items()):
            reasons["failed_require"] += 1
            continue
        if "min_chars" in plan or "max_chars" in plan:
            sources = unit_settings.get("sources") or []
            if not sources:
                raise RunnerError("min_chars/max_chars need units.sources")
            source = sources[0]
            root = _resolve(base, source["root"]) if "root" in source else units_path.parent
            path = _resolve(root, (row.get(source["path_column"]) or "").strip() or ".")
            try:
                length = len(_read_text(path)) if path.is_file() else None
            except UnicodeDecodeError:
                length = None
            if length is None:
                reasons["source_unreadable"] += 1
                continue
            if length < plan.get("min_chars", 0) or length > plan.get("max_chars", length):
                reasons["outside_length_limits"] += 1
                continue
        rank = hashlib.sha256(f"{plan['salt']}|{unit_id}".encode("utf-8")).hexdigest()
        eligible.append((rank, unit_id, row))

    if plan.get("one_per"):
        best: dict[str, tuple[str, str, dict[str, str]]] = {}
        for item in eligible:
            key = item[2].get(plan["one_per"], "")
            if key not in best or item[0] < best[key][0]:
                best[key] = item
        reasons["not_first_in_group"] += len(eligible) - len(best)
        eligible = list(best.values())

    strata_columns = plan.get("strata", [])
    groups: dict[tuple[str, ...], list[tuple[str, str, dict[str, str]]]] = defaultdict(list)
    for item in eligible:
        groups[tuple(item[2].get(column, "") for column in strata_columns)].append(item)
    for members in groups.values():
        members.sort()
    keys = sorted(groups)
    if "per_stratum" in plan:
        quotas = {key: min(plan["per_stratum"], len(groups[key])) for key in keys}
    else:
        size = plan["size"]
        if size > len(eligible):
            raise RunnerError(f"sample size {size} exceeds the {len(eligible)} eligible units")
        total = len(eligible)
        exact = {key: size * len(groups[key]) / total for key in keys}
        quotas = {key: int(exact[key]) for key in keys}
        remainder = size - sum(quotas.values())
        for key in sorted(keys, key=lambda item: (-(exact[item] - quotas[item]), item))[:remainder]:
            quotas[key] += 1

    selected = []
    for key in keys:
        for position, (rank, _unit_id, row) in enumerate(groups[key][: quotas[key]], 1):
            chosen = dict(row)
            chosen["selection_stratum"] = "|".join(key)
            chosen["selection_rank"] = position
            chosen["selection_hash"] = rank
            chosen["selection_reason"] = f"hash-ranked draw with salt {plan['salt']!r}"
            selected.append(chosen)
    columns = header + ["selection_stratum", "selection_rank", "selection_hash", "selection_reason"]
    _write_exclusive(out, _csv_text(columns, selected))
    return {
        "out": str(out),
        "selected": len(selected),
        "eligible": len(eligible),
        "listed": len(rows),
        "not_eligible": dict(sorted(reasons.items())),
        "per_stratum": {"|".join(key): quotas[key] for key in keys},
        "out_sha256": fanout.sha256_file(out),
    }


# --------------------------------------------------------------------------- prepare


def _check_run_dir_free(run_dir: Path) -> None:
    if run_dir.exists():
        extra = [child.name for child in run_dir.iterdir() if child.name != "kit_update_check.json"]
        if extra:
            raise RunnerError(
                f"run directory already has content ({', '.join(sorted(extra)[:5])}); "
                "every run gets a new run ID"
            )


def prepare(
    settings_path: Path, units_path: Path, run_dir: Path, *, dry_run: bool = False
) -> dict[str, Any]:
    settings_path = settings_path.resolve()
    units_path = units_path.resolve()
    run_dir = run_dir.resolve()
    settings, raw = load_settings(settings_path)
    base = settings_path.parent
    stage = settings["stage"]
    run_id = run_dir.name
    if not fanout.SAFE_ID.fullmatch(run_id):
        raise RunnerError(f"run directory name is not a safe run ID: {run_id!r}")
    _check_run_dir_free(run_dir)
    if not units_path.is_file():
        raise RunnerError(f"unit list does not exist: {units_path}")
    inputs = _resolve_inputs(settings, base)
    by_role = {item["role"]: item for item in inputs}
    conditions = _conditions(settings)
    audit = stage == AUDIT_STAGE
    if audit:
        units = _audit_units(settings, units_path)
    else:
        units, _id_column = _coding_units(settings, units_path, base)
    files, gaps = _build_views(units, settings, run_dir)
    batch_size = settings.get("batch_size") or len(units) or 1
    time_box = settings.get("time_box_minutes", 10)
    assignable = [unit for unit in units if "gap" not in unit]
    if not assignable:
        raise RunnerError("no unit can be assigned: " + "; ".join(gap["reason"] for gap in gaps[:3]))

    spec_units = []
    blocks = []
    links = {}
    originals = {
        unit["unit_id"]: [
            {
                "source_id": source["source_id"],
                "original_path": source["original_path"],
                "original_sha256": source["original_sha256"],
            }
            for source in unit["sources"]
        ]
        for unit in assignable
    }
    block = 0
    for condition in conditions:
        read = [
            {"role": role, "path": by_role[role]["path"], "sha256": by_role[role]["sha256"]}
            for role in _read_roles(settings, condition)
        ]
        for start in range(0, len(assignable), batch_size):
            block += 1
            chunk = assignable[start : start + batch_size]
            blocks.append(
                {
                    "block": block,
                    "condition": condition["id"],
                    "model": condition["model"],
                    "effort": condition["effort"],
                    "units": len(chunk),
                    "assignments": len(chunk) * condition["replicates"],
                }
            )
            for unit in chunk:
                for replicate in range(1, condition["replicates"] + 1):
                    slot_id = f"{unit['unit_id']}--{condition['id']}--r{replicate}"
                    assignment_id = f"{slot_id}-attempt001"
                    if not fanout.SAFE_ID.fullmatch(assignment_id):
                        raise RunnerError(
                            f"unit ID {unit['unit_id']!r} is too long for an assignment ID; use shorter IDs"
                        )
                    payload: dict[str, Any] = {
                        "block": block,
                        "condition": condition["id"],
                        "replicate": replicate,
                        "task": TASK_AUDIT if audit else TASK_CODING,
                        "time_box_minutes": time_box,
                        "unit": {"unit_id": unit["unit_id"], **unit["fields"]},
                        "read_in_order": read,
                        "sources": _payload_sources(unit),
                    }
                    if audit:
                        payload["observation"] = unit["observation"]
                        links[unit["unit_id"]] = unit["link"]
                    spec_units.append(
                        {
                            "unit_id": unit["unit_id"],
                            "assignment_id": assignment_id,
                            "attempt": 1,
                            "payload": payload,
                        }
                    )

    scripts_dir = Path(__file__).resolve().parent
    kit_check = run_dir / "kit_update_check.json"
    runner: dict[str, Any] = {
        "runner_version": RUNNER_VERSION,
        "stage": stage,
        "prepared_utc": _now(),
        "settings_path": str(settings_path),
        "settings_sha256": _sha_bytes(raw),
        "units_path": str(units_path),
        "units_sha256": fanout.sha256_file(units_path),
        "scripts": {
            "coding_run.py": fanout.sha256_file(scripts_dir / "coding_run.py"),
            "unit_fanout.py": fanout.sha256_file(scripts_dir / "unit_fanout.py"),
        },
        "kit_update_check": (
            {"path": str(kit_check), "sha256": fanout.sha256_file(kit_check)} if kit_check.is_file() else None
        ),
        "project_code": (
            _project_code_record(_resolve(base, settings["project_code"])) if settings.get("project_code") else None
        ),
        "conditions": conditions,
        "blocks": blocks,
        "unit_sources": originals,
        "units_listed": len(units),
        "units_assigned": len(assignable),
        "gaps": gaps,
        "slots_expected": len(spec_units),
    }
    if audit:
        runner["audit_links"] = links
    spec = {
        "contract_version": fanout.CONTRACT_VERSION,
        "run_id": run_id,
        "assignment_kind": "audit_observation" if audit else "coding_unit",
        "frozen_inputs": inputs,
        "units": spec_units,
        "runner": runner,
    }
    summary = {
        "run_id": run_id,
        "stage": stage,
        "dry_run": dry_run,
        "units_listed": len(units),
        "units_assigned": len(assignable),
        "gaps": len(gaps),
        "gap_reasons": dict(Counter(gap["reason"] for gap in gaps)),
        "assignments": len(spec_units),
        "conditions": [condition["id"] for condition in conditions],
        "blocks": blocks,
        "source_view_files": len(files),
    }
    if dry_run:
        return summary

    run_dir.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        _write_exclusive(Path(path), content["text"])
    with (run_dir / "run_settings.json").open("xb") as handle:
        handle.write(raw)
    _write_exclusive(run_dir / "run_spec.json", json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    fanout.prepare(run_dir / "run_spec.json", run_dir)
    state = _evaluate(run_dir)
    summary["next"] = _next_step(state)
    return summary


# --------------------------------------------------------------------------- quote checks


TYPOGRAPHIC = str.maketrans(
    {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "}
)


def _normalize(text: str, rules: dict[str, Any]) -> str:
    mode = rules.get("normalize", "whitespace")
    if rules.get("fold_quotes"):
        text = text.translate(TYPOGRAPHIC)
    if mode == "alphanumeric":
        text = re.sub(r"(\w)-[ \t]*\r?\n\s*", r"\1", text)
        text = unicodedata.normalize("NFKC", text).casefold()
        return "".join(character for character in text if character.isalnum())
    if mode == "whitespace":
        text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()
    if not rules.get("case_sensitive", True):
        text = text.casefold()
    return text


def _contains(haystack: str, needle: str, rules: dict[str, Any]) -> bool:
    if not needle:
        return False
    whole = rules.get("whole_words", False) and rules.get("normalize", "whitespace") != "alphanumeric"
    start = haystack.find(needle)
    while start != -1:
        if not whole:
            return True
        end = start + len(needle)
        before_ok = start == 0 or not haystack[start - 1].isalnum()
        after_ok = end == len(haystack) or not haystack[end].isalnum()
        if before_ok and after_ok:
            return True
        start = haystack.find(needle, start + 1)
    return False


class _SourceText:
    """Lazily loaded, hash-checked text of one source as the worker saw it."""

    def __init__(self, entry: dict[str, Any]):
        self.entry = entry
        self._shown: str | None = None

    @property
    def shown(self) -> str:
        if self._shown is None:
            path = Path(self.entry["path"])
            if not path.is_file() or fanout.sha256_file(path) != self.entry["sha256"]:
                raise RunnerError(f"source changed after preparation: {path}")
            self._shown = _read_text(path)
        return self._shown

    def lines(self) -> list[str]:
        """Source lines without the ``L<n>: `` labels of a line-numbered view."""

        if self.entry["view"] != "lines":
            return self.shown.splitlines()
        return [line.partition(": ")[2] for line in self.shown.split("\n")[:-1]]

    def plain(self) -> str:
        """The text quotes are matched against: the source without labels or markers."""

        if self.entry["view"] == "lines":
            return "\n".join(self.lines())
        target = self.entry.get("target")
        if self.entry["view"] != "window" or not target:
            return self.shown
        shown = self.shown
        start = target["offset"]
        inner = start + target["marker_before"]
        after = inner + target["length"]
        return shown[:start] + shown[inner:after] + shown[after + target["marker_after"] :]


def check_quotes(
    result: Any, payload: dict[str, Any], rules: dict[str, Any], cache: dict[str, _SourceText]
) -> list[dict[str, Any]]:
    """Check every evidence anchor in one result; returns one row per anchor (no quote text)."""

    sources: dict[str, _SourceText] = {}
    for entry in payload["sources"]:
        if entry["path"] not in cache:
            cache[entry["path"]] = _SourceText(entry)
        sources[entry["source_id"]] = cache[entry["path"]]
    locator_mode = rules.get("locator", "none")
    rows = []
    for anchor in rules["anchors"]:
        for location, value in _walk(result, anchor["path"]):
            if value is None:
                continue
            source_id = locator = offsets = None
            if isinstance(value, dict):
                quote = value.get(anchor.get("quote_field", "quote"))
                if "source_field" in anchor:
                    source_id = value.get(anchor["source_field"])
                if locator_mode == "line":
                    locator = value.get(anchor.get("locator_field", "locator"))
                elif locator_mode == "offset":
                    offsets = (
                        value.get(anchor.get("start_field", "start")),
                        value.get(anchor.get("end_field", "end")),
                    )
                mode = locator_mode
            else:
                quote, mode = value, "none"
            rows.append(
                {
                    "anchor": location,
                    "source_id": "" if source_id is None else str(source_id),
                    "locator": "" if locator is None else str(locator),
                    "words": len(quote.split()) if isinstance(quote, str) else 0,
                    "status": _anchor_status(quote, source_id, locator, offsets, mode, sources, rules),
                }
            )
    return rows


def _strip_markers(quote: str, rules: dict[str, Any]) -> str:
    for marker in (rules.get("_marker_before", ">>> "), rules.get("_marker_after", " <<<")):
        for form in (marker, marker.strip()):
            if form:
                quote = quote.replace(form, "")
    return quote


def _anchor_status(
    quote: Any,
    source_id: Any,
    locator: Any,
    offsets: tuple[Any, Any] | None,
    mode: str,
    sources: dict[str, _SourceText],
    rules: dict[str, Any],
) -> str:
    if not isinstance(quote, str) or not quote.strip():
        return "empty"
    words = len(quote.split())
    if words < rules.get("min_words", 1):
        return "too_short"
    if "max_words" in rules and words > rules["max_words"]:
        return "too_long"
    if source_id is not None:
        if str(source_id) in set(rules.get("unchecked_sources", [])):
            return "unchecked"
        if str(source_id) not in sources:
            return "unknown_source"
        candidates = [sources[str(source_id)]]
    else:
        candidates = list(sources.values())
    if any(source.entry["view"] == "window" for source in candidates):
        quote = _strip_markers(quote, rules)
    needle = _normalize(quote, rules)
    if mode == "offset":
        start, end = offsets if offsets else (None, None)
        if any(not isinstance(item, int) or isinstance(item, bool) for item in (start, end)):
            return "bad_locator"
        for source in candidates:
            shown = source.shown
            if 0 <= start < end <= len(shown) and _normalize(shown[start:end], rules) == needle:
                return "ok"
        return _misplaced(candidates, needle, rules)
    if mode == "line":
        match = LINE_LOCATOR.fullmatch(str(locator)) if locator is not None else None
        if not match:
            return "bad_locator"
        first = int(match.group(1))
        last = int(match.group(2) or first)
        if last < first:
            return "bad_locator"
        tolerance = rules.get("line_tolerance", 0)
        in_range = False
        for source in candidates:
            lines = source.lines()
            if first < 1 or last > len(lines):
                continue
            in_range = True
            window = "\n".join(lines[max(0, first - 1 - tolerance) : min(len(lines), last + tolerance)])
            if _contains(_normalize(window, rules), needle, rules):
                return "ok"
        return _misplaced(candidates, needle, rules) if in_range else "bad_locator"
    if any(_contains(_normalize(source.plain(), rules), needle, rules) for source in candidates):
        return "ok"
    return "not_found"


def _misplaced(candidates: list[_SourceText], needle: str, rules: dict[str, Any]) -> str:
    """A quote that is not at its locator: found elsewhere in the unit, or not at all."""

    if not any(_contains(_normalize(source.plain(), rules), needle, rules) for source in candidates):
        return "not_found"
    return "ok_elsewhere" if rules.get("wrong_location", "fail") == "pass" else "wrong_location"


def _anchor_fails(status: str) -> bool:
    return status in FAILING_ANCHOR or status == "wrong_location"


# --------------------------------------------------------------------------- run evaluation


def _load_run(run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    run_dir = run_dir.resolve()
    try:
        manifest = fanout.verify_run_integrity(run_dir)
    except (FanoutError, KeyError, OSError) as exc:
        raise RunnerError(f"run directory failed its integrity check: {exc}") from exc
    spec_path = run_dir / "run_spec.json"
    if Path(manifest["spec_path"]).resolve() != spec_path.resolve():
        raise RunnerError("this run was not prepared by scripts/coding_run.py (no run_spec.json)")
    spec = _load_json(spec_path)
    settings_raw = (run_dir / "run_settings.json").read_bytes()
    if _sha_bytes(settings_raw) != spec["runner"]["settings_sha256"]:
        raise RunnerError("run_settings.json changed after preparation")
    settings = json.loads(settings_raw.decode("utf-8-sig"))
    return manifest, spec, settings



def _logged_decisions(run_dir: Path) -> set[str]:
    path = run_dir / "failure_decisions.jsonl"
    if not path.is_file():
        return set()
    logged = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and isinstance(row.get("assignment_id"), str):
            logged.add(row["assignment_id"])
    return logged


def _evaluate(run_dir: Path, skip_retry: Iterable[str] = ()) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    manifest, spec, settings = _load_run(run_dir)
    runner = spec["runner"]
    rules = dict(settings.get("quotes") or {})
    view = settings.get("view", {})
    rules["_marker_before"] = view.get("marker_before", ">>> ")
    rules["_marker_after"] = view.get("marker_after", " <<<")
    retry_rules = settings.get("retry", {})
    retry_on = set(retry_rules.get("on", []))
    max_attempts = min(retry_rules.get("max_attempts", fanout.MAX_ATTEMPTS), fanout.MAX_ATTEMPTS)
    skip = set(skip_retry)
    cache: dict[str, _SourceText] = {}
    attempts = []
    rows = [(row, True) for row in manifest["assignments"]] + [
        (row, False) for row in manifest.get("superseded", [])
    ]
    for row, active in rows:
        assignment = fanout.load_json(Path(row["assignment_path"]))
        payload = assignment["payload"]
        return_path = Path(row["return_path"] if active else row["archived_return_path"])
        record: dict[str, Any] = {
            "assignment_id": row["assignment_id"],
            "unit_id": row["unit_id"],
            "attempt": row["attempt"],
            "position": row.get("position", 0),
            "active": active,
            "block": payload.get("block"),
            "condition": payload.get("condition"),
            "replicate": payload.get("replicate"),
            "slot_id": f"{row['unit_id']}--{payload.get('condition')}--r{payload.get('replicate')}",
            "superseded_by": row.get("superseded_by"),
            "return_path": str(return_path),
            "payload": payload,
            "anchors": [],
            "result": None,
            "error": None,
        }
        if not return_path.is_file():
            record.update(outcome="pending", return_status=None, envelope_valid=None)
            attempts.append(record)
            continue
        record["return_sha256"] = fanout.sha256_file(return_path)
        try:
            returned = fanout.load_json(return_path)
            errors = fanout.validate_return(assignment, returned)
        except FanoutError as exc:
            returned, errors = None, [str(exc)]
        if errors:
            record.update(outcome="invalid", return_status=None, envelope_valid=False, error_count=len(errors))
            attempts.append(record)
            continue
        status = returned["status"]
        record.update(return_status=status, envelope_valid=True, error=returned.get("error"))
        record["provenance"] = returned.get("provenance")
        if status == fanout.SUCCESS_STATUS:
            record["result"] = returned.get("result")
            if rules.get("anchors"):
                record["anchors"] = check_quotes(record["result"], payload, rules, cache)
            failed = sum(1 for anchor in record["anchors"] if _anchor_fails(anchor["status"]))
            record["quote_failed"] = failed
            record["outcome"] = "quote_failed" if failed else fanout.SUCCESS_STATUS
        else:
            record["outcome"] = status
        attempts.append(record)

    # A logged decision on an active failed attempt means it was kept as final.
    logged = _logged_decisions(run_dir)
    for record in attempts:
        record["retry_eligible"] = False
        if not record["active"] or record["outcome"] in {"pending", fanout.SUCCESS_STATUS}:
            continue
        kind = "schema_failed" if record["outcome"] == "invalid" else record["outcome"]
        if (
            kind in retry_on
            and record["attempt"] < max_attempts
            and record["assignment_id"] not in skip
            and record["assignment_id"] not in logged
        ):
            record["retry_eligible"] = True

    for record in attempts:
        failed = record["outcome"] not in {"pending", fanout.SUCCESS_STATUS}
        record["needs_decision"] = failed and record["assignment_id"] not in logged
    return {
        "run_dir": run_dir,
        "manifest": manifest,
        "spec": spec,
        "settings": settings,
        "runner": runner,
        "attempts": attempts,
        "max_attempts": max_attempts,
        "retry_on": sorted(retry_on),
    }


def _final_status(record: dict[str, Any]) -> str:
    return "schema_failed" if record["outcome"] == "invalid" else record["outcome"]


def _block_table(state: dict[str, Any]) -> list[dict[str, Any]]:
    table = []
    for block in state["runner"]["blocks"]:
        members = [
            record for record in state["attempts"] if record["active"] and record["block"] == block["block"]
        ]
        pending = sum(1 for record in members if record["outcome"] == "pending")
        waiting = sum(1 for record in members if record["retry_eligible"])
        failures = sum(
            1
            for record in members
            if record["outcome"] not in {"pending", fanout.SUCCESS_STATUS} and not record["retry_eligible"]
        )
        table.append(
            {
                "block": block["block"],
                "condition": block["condition"],
                "slots": len(members),
                "pending": pending,
                "awaiting_retry": waiting,
                "final_failures": failures,
                "complete": pending == 0 and waiting == 0,
            }
        )
    return table


def _stop_rule(state: dict[str, Any], blocks: list[dict[str, Any]]) -> dict[str, Any]:
    rules = state["settings"].get("stop", {})
    reasons = []
    complete = [block for block in blocks if block["complete"]]
    if "batch_failure_rate" in rules:
        for block in complete:
            if block["slots"] and block["final_failures"] / block["slots"] > rules["batch_failure_rate"]:
                reasons.append(
                    f"block {block['block']}: {block['final_failures']} of {block['slots']} units failed "
                    f"(limit {rules['batch_failure_rate']:.0%})"
                )
    if "cumulative_failure_rate" in rules and complete:
        slots = sum(block["slots"] for block in complete)
        failures = sum(block["final_failures"] for block in complete)
        if slots and failures / slots > rules["cumulative_failure_rate"]:
            reasons.append(
                f"completed blocks: {failures} of {slots} units failed (limit {rules['cumulative_failure_rate']:.0%})"
            )
    if "consecutive_same_failure" in rules:
        ordered = sorted(
            (record for record in state["attempts"] if record["outcome"] != "pending"),
            key=lambda record: (record["block"] or 0, record["position"], record["attempt"]),
        )
        run_status, run_length = None, 0
        for record in ordered:
            status = None if record["outcome"] == fanout.SUCCESS_STATUS else _final_status(record)
            if status is not None and status == run_status:
                run_length += 1
            else:
                run_status, run_length = status, 1 if status else 0
            if run_status and run_length >= rules["consecutive_same_failure"]:
                reasons.append(f"{run_length} consecutive attempts ended as {run_status}")
                break
    return {"met": bool(reasons), "reasons": reasons}


def _latest_checkpoint(run_dir: Path) -> dict[str, Any] | None:
    files = sorted((run_dir / "checks").glob("check_*.json")) if (run_dir / "checks").is_dir() else []
    return _load_json(files[-1]) if files else None


def _next_step(state: dict[str, Any], blocks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    run_dir = state["run_dir"]
    blocks = blocks if blocks is not None else _block_table(state)
    stop = _stop_rule(state, blocks)
    apply_command = f'python scripts/coding_run.py check --run-dir "{run_dir}" --apply'
    if stop["met"]:
        return {"action": "stop", "reasons": stop["reasons"]}
    if any(record["retry_eligible"] for record in state["attempts"]) or any(
        record["needs_decision"] and not record["retry_eligible"] for record in state["attempts"]
    ):
        return {"action": "check_apply", "command": apply_command}
    pending_blocks = [block for block in blocks if block["pending"]]
    if pending_blocks:
        current = pending_blocks[0]
        completed = [block["block"] for block in blocks if block["complete"]]
        checkpoint = _latest_checkpoint(run_dir)
        recorded = set(checkpoint.get("complete_blocks", [])) if checkpoint else set()
        if any(number < current["block"] and number not in recorded for number in completed):
            return {"action": "check_apply", "command": apply_command}
        spec_block = next(item for item in state["runner"]["blocks"] if item["block"] == current["block"])
        args: dict[str, Any] = {"run_dir": str(run_dir), "block": current["block"]}
        if spec_block.get("model"):
            args["model"] = spec_block["model"]
        if spec_block.get("effort"):
            args["effort"] = spec_block["effort"]
        return {
            "action": "launch",
            "block": current["block"],
            "condition": current["condition"],
            "pending": current["pending"],
            "claude_code": {"workflow": "elr-observation-fanout", "args": args},
            "codex": {
                "discover": f'python scripts/unit_fanout.py status --run-dir "{run_dir}" --record-launch --block {current["block"]}',
                "agent": "elr_worker",
                "model": spec_block.get("model"),
                "effort": spec_block.get("effort"),
            },
        }
    stage = state["runner"]["stage"]
    version = " --version NNN" if any(kind == "artifact" for kind, _ in CLOSE_OUTPUTS[stage].values()) else ""
    return {"action": "close", "command": f'python scripts/coding_run.py close --run-dir "{run_dir}"{version}'}


def _operational_summary(state: dict[str, Any], blocks: list[dict[str, Any]]) -> dict[str, Any]:
    active = [record for record in state["attempts"] if record["active"]]
    returned = [record for record in state["attempts"] if record["outcome"] != "pending"]
    return {
        "run_id": state["manifest"]["run_id"],
        "stage": state["runner"]["stage"],
        "units_listed": state["runner"]["units_listed"],
        "gaps": len(state["runner"]["gaps"]),
        "slots": len(active),
        "pending": sum(1 for record in active if record["outcome"] == "pending"),
        "attempts_returned": len(returned),
        "attempt_outcomes": dict(sorted(Counter(_final_status(record) for record in returned).items())),
        "final": sum(
            1 for record in active if record["outcome"] != "pending" and not record["retry_eligible"]
        ),
        "awaiting_retry": [record["assignment_id"] for record in active if record["retry_eligible"]],
        "blocks": blocks,
        "stop_rule": _stop_rule(state, blocks),
    }


# --------------------------------------------------------------------------- check


def check(
    run_dir: Path,
    *,
    apply: bool = False,
    skip_retry: Iterable[str] = (),
    decided_by: str = "assistant",
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    skip = list(skip_retry)
    state = _evaluate(run_dir, skip)
    undecided = {record["assignment_id"] for record in state["attempts"] if record["needs_decision"]}
    unknown = sorted(set(skip) - undecided)
    if unknown:
        raise RunnerError(
            "--skip-retry names no failed attempt awaiting a decision: " + ", ".join(unknown)
        )
    retried = []
    logged = 0
    if apply:
        decisions = []
        rule = (
            f"frozen retry rule: retry {', '.join(state['retry_on']) or 'nothing'}; "
            f"at most {state['max_attempts']} attempt(s)"
        )
        for record in state["attempts"]:
            if not record["needs_decision"]:
                continue
            what = _final_status(record)
            if record["anchors"]:
                what += f" ({record.get('quote_failed', 0)} of {len(record['anchors'])} quotation checks failed)"
            if record["retry_eligible"]:
                reason = None
                if record["outcome"] == "quote_failed":
                    reason = f"quote_failed: {record['quote_failed']} of {len(record['anchors'])} quotation checks failed"
                result = fanout.retry(run_dir, record["assignment_id"], downstream_failure_reason=reason)
                retried.append({"from": record["assignment_id"], "to": result["assignment_id"]})
                disposition = f"retried as {result['assignment_id']}"
            elif record["assignment_id"] in skip:
                disposition = f"kept as final {_final_status(record)} (retry declined)"
            else:
                disposition = f"kept as final {_final_status(record)}"
            decisions.append(
                {
                    "assignment_id": record["assignment_id"],
                    "unit_id": record["unit_id"],
                    "slot_id": record["slot_id"],
                    "attempt": record["attempt"],
                    "what_happened": what,
                    "disposition": disposition,
                    "decided_by": decided_by,
                    "rationale": rule if record["assignment_id"] not in skip else "researcher declined the retry",
                    "recorded_utc": _now(),
                }
            )
        if decisions:
            with (run_dir / "failure_decisions.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
                for row in decisions:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        logged = len(decisions)
        state = _evaluate(run_dir, skip)
    blocks = _block_table(state)
    summary = _operational_summary(state, blocks)
    summary["retried"] = retried
    summary["decisions_logged"] = logged
    if apply:
        checks_dir = run_dir / "checks"
        checks_dir.mkdir(exist_ok=True)
        number = len(list(checks_dir.glob("check_*.json"))) + 1
        checkpoint = {
            "checked_utc": _now(),
            "complete_blocks": [block["block"] for block in blocks if block["complete"]],
            **summary,
        }
        path = checks_dir / f"check_{number:03d}.json"
        _write_exclusive(path, json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
        summary["checkpoint"] = str(path)
    summary["next"] = _next_step(state, blocks)
    return summary


# --------------------------------------------------------------------------- close


def _destination(
    kind: str, template: str, run_dir: Path, artifacts_dir: Path | None, version: str | None
) -> Path:
    if kind == "run":
        return run_dir / template
    if version is None or not VERSION_RE.fullmatch(version):
        raise RunnerError("--version NNN (three digits) is required for this stage's versioned files")
    if artifacts_dir is None:
        if run_dir.parent.name != "runs":
            raise RunnerError("--artifacts-dir is required when the run is not under project/runs/")
        artifacts_dir = run_dir.parent.parent / "artifacts"
    return artifacts_dir.resolve() / template.format(v=version)


def _close_state(run_dir: Path) -> dict[str, Any]:
    state = _evaluate(run_dir)
    active = [record for record in state["attempts"] if record["active"]]
    pending = [record for record in active if record["outcome"] == "pending"]
    if pending:
        raise RunnerError(f"{len(pending)} assignment(s) are still pending; launch them before closing")
    if any(record["retry_eligible"] for record in active) or any(
        record["needs_decision"] for record in state["attempts"]
    ):
        raise RunnerError("failures are not yet decided; run check --apply first")
    return state


def close(run_dir: Path, *, version: str | None = None, artifacts_dir: Path | None = None) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    receipt_path = run_dir / "close_receipt.json"
    if receipt_path.exists():
        raise RunnerError("this run is already closed")
    state = _close_state(run_dir)
    stage = state["runner"]["stage"]
    targets = {
        name: _destination(kind, template, run_dir, artifacts_dir, version)
        for name, (kind, template) in CLOSE_OUTPUTS[stage].items()
    }
    _refuse_existing([*targets.values(), receipt_path])
    run_id = state["manifest"]["run_id"]
    active = sorted(
        (record for record in state["attempts"] if record["active"]),
        key=lambda record: (record["block"] or 0, record["position"]),
    )
    by_slot: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in state["attempts"]:
        by_slot[record["slot_id"]].append(record)

    originals = state["runner"]["unit_sources"]

    def sources_for(record: dict[str, Any], start: Path) -> list[dict[str, Any]]:
        by_id = {item["source_id"]: item for item in originals[record["unit_id"]]}
        return [
            {
                "source_id": source["source_id"],
                "path": _relative(by_id[source["source_id"]]["original_path"], start),
                "sha256": by_id[source["source_id"]]["original_sha256"],
                "view": source["view"],
                "view_path": _relative(source["path"], start),
                "view_sha256": source["sha256"],
            }
            for source in record["payload"]["sources"]
        ]

    dataset_dir = targets["dataset"].parent
    final_counts: Counter[str] = Counter()
    dataset_rows: list[dict[str, Any]] = []
    audit = stage == AUDIT_STAGE
    links = state["runner"].get("audit_links", {})
    for record in active:
        status = _final_status(record)
        final_counts[status] += 1
        history = sorted(by_slot[record["slot_id"]], key=lambda item: item["attempt"])
        base_row: dict[str, Any] = {
            "run_id": run_id,
            "slot_id": record["slot_id"],
            "unit_id": record["unit_id"],
            "condition": record["condition"],
            "replicate": record["replicate"],
            "block": record["block"],
            "status": status,
            "retries_exhausted": status != fanout.SUCCESS_STATUS and record["attempt"] >= state["max_attempts"],
            "assignment_id": record["assignment_id"],
            "attempt": record["attempt"],
            "error": record["error"] if status != fanout.SUCCESS_STATUS else None,
            "return_path": _relative(record["return_path"], dataset_dir),
            "return_sha256": record.get("return_sha256"),
            "superseded": [item["assignment_id"] for item in history if not item["active"]],
            "quote_checks": (
                {"anchors": len(record["anchors"]), "failed": record.get("quote_failed", 0)}
                if record["anchors"] or record["outcome"] == "quote_failed"
                else None
            ),
            "sources": sources_for(record, dataset_dir),
        }
        if audit:
            result = record["result"] if status == fanout.SUCCESS_STATUS else None
            disposition = result.get("disposition") if isinstance(result, dict) else None
            if status == fanout.SUCCESS_STATUS and disposition not in AUDIT_DISPOSITIONS:
                raise RunnerError(
                    f"{record['assignment_id']}: the audit result needs disposition supported, unsupported, or ambiguous"
                )
            base_row.update(
                {
                    "observation_id": record["unit_id"],
                    "coded": links.get(record["unit_id"]),
                    "disposition": disposition,
                    "reasoning": result.get("reasoning") if isinstance(result, dict) else None,
                    "locations_inspected": result.get("locations_inspected") if isinstance(result, dict) else None,
                }
            )
        else:
            base_row["unit"] = record["payload"].get("unit")
            base_row["result"] = record["result"] if status == fanout.SUCCESS_STATUS else None
        dataset_rows.append(base_row)
    for gap in state["runner"]["gaps"]:
        final_counts[gap["status"]] += 1
        dataset_rows.append(
            {
                "run_id": run_id,
                "slot_id": None,
                "unit_id": gap["unit_id"],
                "condition": None,
                "replicate": None,
                "status": gap["status"],
                "error": gap["reason"],
                "result": None,
                "assignment_id": None,
                "attempt": None,
                "note": "not assigned: the source could not be prepared",
            }
        )

    expected = state["runner"]["slots_expected"] + len(state["runner"]["gaps"])
    if sum(final_counts.values()) != expected or len(active) != state["runner"]["slots_expected"]:
        raise RunnerError("counts do not reconcile with the prepared run; nothing was written")

    # One ledger row per unit, condition, and replicate (one per unit in Stage 11), so
    # scripts/validate_run.py coding can reconcile it with the corpus manifest; each
    # attempt has its own row in the checks file.
    ledger_rows = []
    for record in active:
        history = sorted(by_slot[record["slot_id"]], key=lambda item: item["attempt"])
        ledger_rows.append(
            {
                "run_id": run_id,
                "unit_id": record["unit_id"],
                "status": _final_status(record),
                "slot_id": record["slot_id"],
                "condition": record["condition"],
                "replicate": record["replicate"],
                "block": record["block"],
                "attempts": len(history),
                "attempt_outcomes": "; ".join(f"{item['attempt']}:{_final_status(item)}" for item in history),
                "final_assignment_id": record["assignment_id"],
                "return_sha256": record.get("return_sha256"),
            }
        )
    check_rows = []
    quote_rows = []
    for record in sorted(
        state["attempts"], key=lambda item: (item["block"] or 0, item["position"], item["attempt"])
    ):
        check_rows.append(
            {
                "run_id": run_id,
                "assignment_id": record["assignment_id"],
                "unit_id": record["unit_id"],
                "condition": record["condition"],
                "replicate": record["replicate"],
                "attempt": record["attempt"],
                "envelope_valid": "yes" if record["envelope_valid"] else "no",
                "return_status": record["return_status"],
                "schema_valid": (
                    "yes"
                    if record["return_status"] == fanout.SUCCESS_STATUS
                    else ("no" if record["outcome"] == "invalid" else "not_applicable")
                ),
                "quote_anchors": len(record["anchors"]),
                "quote_failed": record.get("quote_failed", 0),
                "quote_result": (
                    ("failed" if record.get("quote_failed") else "passed") if record["anchors"] else "not_applicable"
                ),
            }
        )
        for anchor in record["anchors"]:
            quote_rows.append(
                {
                    "run_id": run_id,
                    "assignment_id": record["assignment_id"],
                    "unit_id": record["unit_id"],
                    "attempt": record["attempt"],
                    **anchor,
                    "passes": "no" if _anchor_fails(anchor["status"]) else "yes",
                }
            )
    for gap in state["runner"]["gaps"]:
        ledger_rows.append(
            {"run_id": run_id, "unit_id": gap["unit_id"], "status": gap["status"], "attempts": 0, "note": gap["reason"]}
        )

    texts: dict[str, str] = {"dataset": _jsonl_text(dataset_rows)}
    ledger_header = [
        "run_id", "unit_id", "status", "slot_id", "condition", "replicate", "block", "attempts",
        "attempt_outcomes", "final_assignment_id", "return_sha256", "note",
    ]
    texts["ledger"] = _csv_text(ledger_header, ledger_rows)
    texts["checks"] = _csv_text(
        [
            "run_id", "assignment_id", "unit_id", "condition", "replicate", "attempt",
            "envelope_valid", "return_status", "schema_valid", "quote_anchors", "quote_failed",
            "quote_result",
        ],
        check_rows,
    )
    if "quotes" in targets:
        texts["quotes"] = _csv_text(
            ["run_id", "assignment_id", "unit_id", "attempt", "anchor", "source_id", "locator", "words", "status", "passes"],
            quote_rows,
        )
    if audit:
        coverage = []
        queue = []
        for row in dataset_rows:
            if row["slot_id"] is None:
                audit_status = f"failed:{row['status']}"
            elif row["status"] == fanout.SUCCESS_STATUS:
                audit_status = row["disposition"]
            else:
                audit_status = f"failed:{row['status']}"
            coverage.append(
                {
                    "observation_id": row.get("observation_id") or row["unit_id"],
                    "unit_id": (row.get("coded") or {}).get("unit_id"),
                    "audit_status": audit_status,
                    "assignment_id": row["assignment_id"],
                    "attempt": row["attempt"],
                }
            )
            if audit_status != "supported":
                locations = row.get("locations_inspected")
                queue.append(
                    {
                        "observation_id": row.get("observation_id") or row["unit_id"],
                        "unit_id": (row.get("coded") or {}).get("unit_id"),
                        "coded_assignment_id": (row.get("coded") or {}).get("assignment_id"),
                        "finding": audit_status,
                        "reasoning": row.get("reasoning") or row.get("error"),
                        "locations_inspected": "; ".join(locations) if isinstance(locations, list) else locations,
                        "route": "11-scale-up",
                        "disposition": "",
                    }
                )
        texts["coverage"] = _csv_text(["observation_id", "unit_id", "audit_status", "assignment_id", "attempt"], coverage)
        texts["queue"] = _csv_text(
            ["observation_id", "unit_id", "coded_assignment_id", "finding", "reasoning", "locations_inspected", "route", "disposition"],
            queue,
        )

    for name, path in targets.items():
        _write_exclusive(path, texts[name])
    receipt = {
        "run_id": run_id,
        "stage": stage,
        "closed_utc": _now(),
        "units_listed": state["runner"]["units_listed"],
        "units_assigned": state["runner"]["units_assigned"],
        "gaps": len(state["runner"]["gaps"]),
        "slots_expected": state["runner"]["slots_expected"],
        "attempts": len(state["attempts"]),
        "superseded": sum(1 for record in state["attempts"] if not record["active"]),
        "final_status_counts": dict(sorted(final_counts.items())),
        "reconciles": True,
        "settings_sha256": state["runner"]["settings_sha256"],
        "run_manifest_sha256": fanout.sha256_file(run_dir / "run_manifest.json"),
        "failure_decisions": len(_logged_decisions(run_dir)),
        "outputs": {
            name: {"path": str(path), "sha256": fanout.sha256_file(path)} for name, path in targets.items()
        },
    }
    _write_exclusive(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return {key: receipt[key] for key in ("run_id", "stage", "slots_expected", "gaps", "final_status_counts", "outputs")}


def _closed(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    run_dir = run_dir.resolve()
    receipt_path = run_dir / "close_receipt.json"
    if not receipt_path.is_file():
        raise RunnerError("close the run first: coded values stay hidden until every unit is final")
    receipt = _load_json(receipt_path)
    _manifest, spec, settings = _load_run(run_dir)
    dataset_path = Path(receipt["outputs"]["dataset"]["path"])
    if not dataset_path.is_file() or fanout.sha256_file(dataset_path) != receipt["outputs"]["dataset"]["sha256"]:
        raise RunnerError(f"the closed dataset changed or is missing: {dataset_path}")
    return receipt, _read_jsonl(dataset_path), spec, settings


# --------------------------------------------------------------------------- review


def _canon(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        return text.lower() if text.lower() in {"true", "false"} else text
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _coder_names(spec: dict[str, Any]) -> dict[tuple[str, int], str]:
    names = {}
    for condition in spec["runner"]["conditions"]:
        for replicate in range(1, condition["replicates"] + 1):
            names[(condition["id"], replicate)] = (
                condition["id"] if condition["replicates"] == 1 else f"{condition['id']}.r{replicate}"
            )
    return names


def review(
    run_dir: Path,
    *,
    version: str | None = None,
    artifacts_dir: Path | None = None,
    human_codes: Path | None = None,
    blind: bool = False,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    _receipt, rows, spec, settings = _closed(run_dir)
    stage = spec["runner"]["stage"]
    review_settings = settings.get("review", {})
    kind, template = REVIEW_OUTPUTS.get(stage, ("run", "researcher_review.csv"))
    out = _destination(kind, template, run_dir, artifacts_dir, version)
    key_path = run_dir / "researcher_review_key.csv"
    _refuse_existing([out, key_path] if blind else [out])
    names = _coder_names(spec)
    human: dict[str, dict[str, str]] = {}
    human_columns: list[str] = []
    if human_codes:
        header, human_rows = _read_csv(human_codes.resolve())
        id_column = review_settings.get("human_id_column", "unit_id")
        if id_column not in header:
            raise RunnerError(f"human codes lack column {id_column}")
        human_columns = [column for column in header if column != id_column]
        for row in human_rows:
            human[(row.get(id_column) or "").strip()] = row
    flat_rows = []
    result_columns: list[str] = []
    for row in rows:
        values = _flatten(row.get("result") or {}) if stage != AUDIT_STAGE else {
            "disposition": row.get("disposition"),
            "reasoning": row.get("reasoning"),
            "locations_inspected": row.get("locations_inspected"),
        }
        for column in values:
            if column not in result_columns:
                result_columns.append(column)
        coder = names.get((row.get("condition"), row.get("replicate")), "") if row.get("slot_id") else ""
        entry: dict[str, Any] = {
            "unit_id": row["unit_id"],
            "coder": coder,
            "status": row["status"],
            "quote_checks": (
                f"{row['quote_checks']['anchors'] - row['quote_checks']['failed']} of {row['quote_checks']['anchors']} passed"
                if row.get("quote_checks")
                else ""
            ),
            "sources": "; ".join(source["path"] for source in row.get("sources") or []),
            "error": row.get("error"),
            "_slot": row.get("slot_id"),
            "_assignment": row.get("assignment_id"),
            **{f"result.{key}": value for key, value in values.items()},
        }
        lookup = (row.get("coded") or {}).get("unit_id") if stage == AUDIT_STAGE else row["unit_id"]
        for column in human_columns:
            entry[f"human.{column}"] = human.get(lookup or "", {}).get(column, "")
        flat_rows.append(entry)
    researcher_columns = list(review_settings.get("columns", DEFAULT_REVIEW_COLUMNS))
    header = ["unit_id", "coder", "status", "quote_checks", "sources", "error"]
    header += [f"result.{column}" for column in result_columns]
    header += [f"human.{column}" for column in human_columns] + researcher_columns
    key_rows = []
    if blind:
        seed = review_settings.get("blind_seed")
        if seed is None:
            raise RunnerError("blind review needs review.blind_seed in the settings")
        rng = random.Random(seed)
        order = [(rng.random(), index) for index in range(len(flat_rows))]
        flat_rows = [flat_rows[index] for _value, index in sorted(order)]
        letters: dict[str, int] = defaultdict(int)
        for number, entry in enumerate(flat_rows, 1):
            letters[entry["unit_id"]] += 1
            entry["review_id"] = f"R{number:04d}"
            key_rows.append(
                {
                    "review_id": entry["review_id"],
                    "unit_id": entry["unit_id"],
                    "coder": entry["coder"],
                    "slot_id": entry["_slot"],
                    "assignment_id": entry["_assignment"],
                }
            )
            entry["coder"] = chr(ord("A") + letters[entry["unit_id"]] - 1) if entry["coder"] else ""
        header = ["review_id"] + header
    _write_exclusive(out, _csv_text(header, flat_rows))
    result = {"review_sheet": str(out), "rows": len(flat_rows), "researcher_columns": researcher_columns}
    if blind:
        _write_exclusive(key_path, _csv_text(["review_id", "unit_id", "coder", "slot_id", "assignment_id"], key_rows))
        result["key"] = str(key_path)
    return result


# --------------------------------------------------------------------------- compare


def _kappa(pairs: list[tuple[str, str]]) -> tuple[float | None, str | None]:
    n = len(pairs)
    if not n:
        return None, "no units coded by both"
    observed = sum(1 for a, b in pairs if a == b) / n
    left = Counter(a for a, _ in pairs)
    right = Counter(b for _, b in pairs)
    expected = sum(left[key] * right.get(key, 0) for key in left) / (n * n)
    if expected >= 1:
        return None, "undefined: both coders used one identical category"
    return (observed - expected) / (1 - expected), None


def compare(
    run_dir: Path,
    *,
    version: str | None = None,
    artifacts_dir: Path | None = None,
    human_codes: Path | None = None,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    _receipt, rows, spec, settings = _closed(run_dir)
    stage = spec["runner"]["stage"]
    plan = settings.get("compare")
    if not plan:
        raise RunnerError("settings have no compare section")
    outputs = COMPARE_OUTPUTS.get(stage, DEFAULT_COMPARE_OUTPUTS)
    targets = {name: _destination(kind, template, run_dir, artifacts_dir, version) for name, (kind, template) in outputs.items()}
    _refuse_existing(targets.values())
    names = _coder_names(spec)
    values: dict[str, dict[str, dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
    model_coders = list(dict.fromkeys(names.values()))
    for row in rows:
        if row.get("status") != fanout.SUCCESS_STATUS or not row.get("slot_id"):
            continue
        coder = names[(row["condition"], row["replicate"])]
        source = row.get("result") if stage != AUDIT_STAGE else {"disposition": row.get("disposition")}
        for field in plan["fields"]:
            value = _canon(_get_field(source, field))
            if value is not None:
                values[field][coder][row["unit_id"]] = value
    human_coders: list[str] = []
    human_path = human_codes.resolve() if human_codes else (
        _resolve(Path(spec["runner"]["settings_path"]).parent, plan["human_codes"]) if plan.get("human_codes") else None
    )
    if human_path:
        header, human_rows = _read_csv(human_path)
        id_column = plan.get("human_id_column", "unit_id")
        coder_column = plan.get("human_coder_column")
        mapping = plan.get("human_columns", {})
        needed = [id_column] + ([coder_column] if coder_column else []) + [mapping.get(field, field) for field in plan["fields"]]
        missing = [column for column in needed if column not in header]
        if missing:
            raise RunnerError(f"human codes lack columns: {', '.join(missing)}")
        for row in human_rows:
            coder = f"human:{row[coder_column]}" if coder_column else "human"
            if coder not in human_coders:
                human_coders.append(coder)
            for field in plan["fields"]:
                value = _canon(row.get(mapping.get(field, field)))
                if value is not None:
                    values[field][coder][(row.get(id_column) or "").strip()] = value
    coders = model_coders + human_coders
    metrics: dict[str, Any] = {"run_id": spec["run_id"], "fields": {}, "coders": coders}
    disagreements = []
    model_disagreeing: set[str] = set()
    reference = plan.get("reference")
    reference_coder = next(
        (name for (condition, _replicate), name in names.items() if condition == reference), model_coders[0]
    )
    boot = plan.get("bootstrap")
    for field in plan["fields"]:
        pairs_out = []
        for index, left in enumerate(coders):
            for right in coders[index + 1 :]:
                shared = sorted(set(values[field][left]) & set(values[field][right]))
                pairs = [(values[field][left][unit], values[field][right][unit]) for unit in shared]
                kappa, note = _kappa(pairs)
                table: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
                for a, b in pairs:
                    table[a][b] += 1
                agree = sum(1 for a, b in pairs if a == b)
                pairs_out.append(
                    {
                        "a": left,
                        "b": right,
                        "n": len(pairs),
                        "agree": agree,
                        "raw_agreement": agree / len(pairs) if pairs else None,
                        "kappa": kappa,
                        "kappa_note": note,
                        "table": {key: dict(sorted(inner.items())) for key, inner in sorted(table.items())},
                    }
                )
                for unit in shared:
                    a, b = values[field][left][unit], values[field][right][unit]
                    if a != b:
                        disagreements.append(
                            {"unit_id": unit, "field": field, "coder_a": left, "value_a": a, "coder_b": right, "value_b": b}
                        )
                        if left in model_coders and right in model_coders:
                            model_disagreeing.add(unit)
        field_metrics: dict[str, Any] = {"pairs": pairs_out}
        if human_coders and len(model_coders) > 1:
            gold = values[field][human_coders[0]]
            differences = []
            for coder in model_coders:
                if coder == reference_coder:
                    continue
                units = sorted(set(gold) & set(values[field][coder]) & set(values[field][reference_coder]))
                if not units:
                    continue
                hits = [
                    (values[field][coder][unit] == gold[unit], values[field][reference_coder][unit] == gold[unit])
                    for unit in units
                ]
                difference = (sum(a for a, _ in hits) - sum(b for _, b in hits)) / len(hits)
                entry: dict[str, Any] = {
                    "coder": coder,
                    "versus": reference_coder,
                    "benchmark": human_coders[0],
                    "n": len(hits),
                    "accuracy": sum(a for a, _ in hits) / len(hits),
                    "reference_accuracy": sum(b for _, b in hits) / len(hits),
                    "difference": difference,
                }
                if boot:
                    rng = random.Random(boot["seed"])
                    resamples = boot.get("resamples", 2000)
                    draws = []
                    for _ in range(resamples):
                        picked = [hits[int(rng.random() * len(hits))] for _ in hits]
                        draws.append((sum(a for a, _ in picked) - sum(b for _, b in picked)) / len(picked))
                    draws.sort()
                    entry["ci95"] = [draws[int(0.025 * (resamples - 1))], draws[int(0.975 * (resamples - 1))]]
                    entry["bootstrap"] = {"resamples": resamples, "seed": boot["seed"], "unit": "unit_id"}
                differences.append(entry)
            field_metrics["paired_differences"] = differences
        metrics["fields"][field] = field_metrics

    researcher = list(DISAGREEMENT_COLUMNS)
    disagreement_text = _csv_text(["unit_id", "field", "coder_a", "value_a", "coder_b", "value_b", *researcher], disagreements)
    roster_path = Path(spec["runner"]["units_path"])
    subset_text = None
    if stage != AUDIT_STAGE and roster_path.is_file():
        header, roster = _read_csv(roster_path)
        id_column = (settings.get("units") or {}).get("id_column", "unit_id")
        subset = [row for row in roster if (row.get(id_column) or "").strip() in model_disagreeing]
        subset_text = _csv_text(header, subset)
    _write_exclusive(targets["metrics"], json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    _write_exclusive(targets["disagreements"], disagreement_text)
    result = {
        "metrics": str(targets["metrics"]),
        "disagreements": str(targets["disagreements"]),
        "disagreement_rows": len(disagreements),
        "coders": coders,
    }
    if subset_text is not None:
        _write_exclusive(targets["disagreeing_units"], subset_text)
        result["disagreeing_units"] = str(targets["disagreeing_units"])
        result["units_with_model_disagreement"] = len(model_disagreeing)
    return result


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    sample_parser = commands.add_parser("sample", help="draw a reproducible sample")
    sample_parser.add_argument("--settings", type=Path, required=True)
    sample_parser.add_argument("--units", type=Path, required=True)
    sample_parser.add_argument("--out", type=Path, required=True)

    prepare_parser = commands.add_parser("prepare", help="build and seal a run directory")
    prepare_parser.add_argument("--settings", type=Path, required=True)
    prepare_parser.add_argument("--units", type=Path, required=True)
    prepare_parser.add_argument("--run-dir", type=Path, required=True)
    prepare_parser.add_argument("--dry-run", action="store_true", help="check everything and write nothing")

    check_parser = commands.add_parser("check", help="check returns and say what to do next")
    check_parser.add_argument("--run-dir", type=Path, required=True)
    check_parser.add_argument("--apply", action="store_true", help="apply the retry rule and log decisions")
    check_parser.add_argument("--skip-retry", action="append", default=[], metavar="ASSIGNMENT_ID")
    check_parser.add_argument("--decided-by", default="assistant", choices=["assistant", "researcher"])

    close_parser = commands.add_parser("close", help="write the stage's dataset, ledger, and checks")
    close_parser.add_argument("--run-dir", type=Path, required=True)
    close_parser.add_argument("--version")
    close_parser.add_argument("--artifacts-dir", type=Path)

    review_parser = commands.add_parser("review", help="write the researcher review sheet")
    review_parser.add_argument("--run-dir", type=Path, required=True)
    review_parser.add_argument("--version")
    review_parser.add_argument("--artifacts-dir", type=Path)
    review_parser.add_argument("--human-codes", type=Path)
    review_parser.add_argument("--blind", action="store_true")

    compare_parser = commands.add_parser("compare", help="agreement and disagreement tables")
    compare_parser.add_argument("--run-dir", type=Path, required=True)
    compare_parser.add_argument("--version")
    compare_parser.add_argument("--artifacts-dir", type=Path)
    compare_parser.add_argument("--human-codes", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.command == "sample":
            result = sample(args.settings, args.units, args.out)
        elif args.command == "prepare":
            result = prepare(args.settings, args.units, args.run_dir, dry_run=args.dry_run)
        elif args.command == "check":
            result = check(args.run_dir, apply=args.apply, skip_retry=args.skip_retry, decided_by=args.decided_by)
        elif args.command == "close":
            result = close(args.run_dir, version=args.version, artifacts_dir=args.artifacts_dir)
        elif args.command == "review":
            result = review(
                args.run_dir,
                version=args.version,
                artifacts_dir=args.artifacts_dir,
                human_codes=args.human_codes,
                blind=args.blind,
            )
        else:
            result = compare(
                args.run_dir, version=args.version, artifacts_dir=args.artifacts_dir, human_codes=args.human_codes
            )
    except (RunnerError, FanoutError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
