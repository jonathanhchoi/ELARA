"""Resolve a pristine ELARA source tree for the maintainer test suite.

ELARA installs its tests into project folders, while four files under
``project/`` deliberately become mutable project records.  Tests must not use
those live records as distribution templates.  In an initialized project this
module reconstructs a clean, local-only source tree from the bootstrap
manifest and immutable blank-record fixtures.  A pristine maintainer checkout
continues to run directly from its repository root.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path


PROJECT_RECORDS = (
    "project/PROJECT_STATE.md",
    "project/DECISIONS.md",
    "project/RUN_LEDGER.md",
    "project/DEVIATIONS.md",
)
ALIASES_TO_DISTRIBUTION = {
    "ELARA_README.md": "README.md",
    "LICENSE.ELARA": "LICENSE",
}

_temporary_source: tempfile.TemporaryDirectory[str] | None = None
_resolved_roots: dict[Path, Path] = {}


def _state_slug(root: Path) -> str | None:
    state = root / "project" / "PROJECT_STATE.md"
    if not state.is_file():
        return None
    for line in state.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("project_slug:"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def _is_pristine_checkout(root: Path) -> bool:
    return (
        _state_slug(root) in (None, "null")
        and (root / "README.md").is_file()
        and not (root / "project" / "ELARA_MANIFEST.json").exists()
    )


def _manifest_paths(source: Path) -> list[str]:
    manifest_path = source / "project" / "ELARA_MANIFEST.json"
    if not manifest_path.is_file():
        raise RuntimeError(
            "The ELARA test suite is running outside a pristine checkout, but "
            "project/ELARA_MANIFEST.json is missing; a clean test source cannot be reconstructed."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    paths: set[str] = set()
    for key in ("kit_paths", "shared_paths"):
        values = manifest.get(key)
        if not isinstance(values, list):
            raise RuntimeError(f"ELARA manifest field {key!r} is missing or malformed")
        paths.update(str(value).replace("\\", "/") for value in values)
    return sorted(paths)


def materialize_clean_kit(source: Path, destination: Path) -> None:
    """Build a clean distribution view from an initialized ELARA project."""

    source = source.resolve()
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(destination)

    paths = _manifest_paths(source)
    destination.mkdir(parents=True)
    for relative in paths:
        if relative in PROJECT_RECORDS:
            continue
        source_path = source / relative
        if not source_path.is_file():
            raise RuntimeError(f"ELARA manifest path is missing: {relative}")
        distribution_relative = ALIASES_TO_DISTRIBUTION.get(relative, relative)
        destination_path = destination / distribution_relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)

    fixtures = source / "tests" / "fixtures" / "clean_project_records"
    for relative in PROJECT_RECORDS:
        fixture = fixtures / Path(relative).name
        if not fixture.is_file():
            raise RuntimeError(f"clean project-record fixture is missing: {fixture}")
        destination_path = destination / relative
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixture, destination_path)


def resolve_test_root(actual_root: Path) -> Path:
    """Return the real pristine root or one shared reconstructed clean root."""

    global _temporary_source

    actual_root = actual_root.resolve()
    if _is_pristine_checkout(actual_root):
        return actual_root
    if actual_root in _resolved_roots:
        return _resolved_roots[actual_root]

    if _temporary_source is None:
        _temporary_source = tempfile.TemporaryDirectory(prefix="elara-clean-test-source-")
    clean_root = Path(_temporary_source.name) / ("ELARA-" + str(len(_resolved_roots) + 1))
    materialize_clean_kit(actual_root, clean_root)
    _resolved_roots[actual_root] = clean_root
    return clean_root
