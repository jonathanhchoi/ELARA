"""Shared parsing and discovery helpers for the ELARA workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_STAGE_KEYS = (
    "stage_id",
    "title",
    "paper_steps",
    "core",
    "interaction_profile",
    "long_running",
    "prerequisites",
    "required_inputs",
    "declared_outputs",
    "human_gate",
    "next_stage",
    "failure_routes",
)

REQUIRED_STAGE_SECTIONS = (
    "Objective",
    "Prerequisite checks",
    "Researcher decisions",
    "Mode handoff",
    "Work",
    "Artifacts",
    "Verification",
    "State transition",
    "Next-stage handoff",
)

INTERACTION_PROFILES = {"normal", "plan", "execute", "plan_then_execute"}
STATE_STATUSES = {
    "ready",
    "running",
    "awaiting_approval",
    "waiting_for_user",
    "failed",
    "complete",
    "superseded",
}


class FrontmatterError(ValueError):
    """Raised when a constrained workflow frontmatter block is invalid."""


def repository_root(start: Path | None = None) -> Path:
    """Return the kit root from a script path or a supplied location."""

    if start is None:
        return Path(__file__).resolve().parents[1]
    start = start.resolve()
    if (start / "workflow" / "stages").is_dir():
        return start
    raise FrontmatterError(f"Not an ELARA package root: {start}")


def _parse_scalar(raw: str, *, path: Path, key: str) -> Any:
    raw = raw.strip()
    if raw == "null":
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw.startswith(("[", "{", '"')):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FrontmatterError(f"{path}: invalid value for {key}: {exc}") from exc
    raise FrontmatterError(
        f"{path}: {key} must use a quoted string, inline JSON array/object, boolean, or null"
    )


def parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    """Parse the kit's deliberately constrained YAML-compatible frontmatter."""

    # utf-8-sig tolerates the BOM that Windows PowerShell redirection prepends,
    # which would otherwise surface as a misleading missing-delimiter error.
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError(f"{path}: missing opening frontmatter delimiter")
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise FrontmatterError(f"{path}: missing closing frontmatter delimiter") from exc

    data: dict[str, Any] = {}
    for line_number, line in enumerate(lines[1:end], 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1].isspace() or ":" not in line:
            raise FrontmatterError(
                f"{path}:{line_number}: frontmatter must be one key/value pair per line"
            )
        key, raw = line.split(":", 1)
        key = key.strip()
        if key in data:
            raise FrontmatterError(f"{path}:{line_number}: duplicate key {key}")
        data[key] = _parse_scalar(raw, path=path, key=key)
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return data, body


def stage_files(root: Path) -> list[Path]:
    """Return canonical stages in filename order."""

    return sorted((root / "workflow" / "stages").glob("[0-9][0-9]-*.md"))


def load_stages(root: Path) -> list[tuple[Path, dict[str, Any], str]]:
    """Load all canonical stage documents."""

    return [(path, *parse_frontmatter(path)) for path in stage_files(root)]


def skill_name(stage_id: str) -> str:
    return f"elr-{stage_id}"
