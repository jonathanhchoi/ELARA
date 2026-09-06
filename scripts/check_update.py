"""Read-only GitHub currency and installation check before a new ELARA stage.

Exit 0 only when current; 2 means an update is available, 3 means GitHub could
not be checked, and 4 means installation evidence needs attention. This does
not install anything, grant consent, or authorize research work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
import uuid
from pathlib import Path, PurePosixPath

import bootstrap


def owned_paths(root: Path, manifest: dict) -> set[str]:
    paths: set[str] = set()
    for key in ("kit_paths", "shared_paths"):
        values = manifest.get(key, [])
        if not isinstance(values, list):
            raise ValueError("Invalid installation path list.")
        for relative in values:
            if (not isinstance(relative, str) or not relative or "\\" in relative
                    or ":" in relative or PurePosixPath(relative).is_absolute()
                    or ".." in PurePosixPath(relative).parts
                    or PurePosixPath(relative).as_posix() != relative
                    or not (root / relative).resolve().is_relative_to(root)):
                raise ValueError("Invalid installation path.")
            if relative not in bootstrap.PROJECT_OWNED:
                paths.add(relative)
    return paths


def installation_evidence(root: Path) -> tuple[dict | None, list[str]]:
    """Validate the modern receipt, or return legacy evidence for comparison."""
    path = root / bootstrap.MANIFEST_RELATIVE
    if not path.exists():
        return None, []
    manifest = json.loads(bootstrap.read_text(path))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("kit_paths"), list):
        raise ValueError("Invalid installation manifest.")
    paths = owned_paths(root, manifest)
    if manifest.get("update_conflicts"):
        return manifest, ["The previous update retained conflicting files."]
    if manifest.get("installation_complete") is False:
        return manifest, ["The installation was not completed."]
    commit = manifest.get("installed_commit")
    if commit is None:
        return manifest, []  # A ZIP or legacy installation needs a live content comparison.
    hashes = manifest.get("installed_hashes")
    if (not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None
            or manifest.get("installation_complete") is not True
            or not paths or not isinstance(hashes, dict) or set(hashes) != paths):
        raise ValueError("Incomplete installation identity or file inventory.")
    problems = []
    for relative in sorted(paths):
        expected = hashes[relative]
        if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            raise ValueError("Invalid installed file hash.")
        file = root / relative
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            problems.append("Modified or missing ELARA file: " + relative)
    return manifest, problems


def check(root: Path, stage: str) -> dict:
    root = root.resolve()
    result = {
        "schema_version": "1.0", "check_id": str(uuid.uuid4()),
        "checked_at": bootstrap.utc_now(), "stage": stage,
        "repository": bootstrap.REPOSITORY, "ref": bootstrap.DEFAULT_REF,
        "ready": False, "status": "unverified", "installed_commit": None,
        "latest_commit": None, "problems": [],
    }
    try:
        if (re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", stage) is None
                or not any((root / "workflow" / folder / (stage + ".md")).is_file()
                           for folder in ("stages", "utilities"))):
            result["problems"] = ["Name an existing canonical stage or utility."]
            return result
        if (root / bootstrap.UPDATE_PENDING_RELATIVE).exists():
            result["problems"] = ["An update is unfinished. Verify or complete it before starting a new stage."]
            return result
        manifest, problems = installation_evidence(root)
        result["installed_commit"] = (manifest or {}).get("installed_commit")
        result["installed_version"] = (manifest or {}).get("kit_version")
        if problems:
            result.update(status="conflict", problems=problems)
            return result
        upstream = bootstrap.github_commit()
        result.update(latest_commit=upstream["commit"], latest_change=upstream["subject"],
                      latest_url=upstream["url"])
        installed = result["installed_commit"]
        if installed is None and manifest is None:
            local = bootstrap.local_source_info(root)
            installed = local.get("verified_commit")
            result["installed_commit"] = installed
            result["installed_version"] = bootstrap.kit_version(root)
        if installed is not None:
            current = installed == upstream["commit"]
            result.update(ready=current, status="current" if current else "update_available")
            return result
        # A branch ZIP has no Git history; an old project may have only a
        # release label. Compare against exact upstream bytes without writing
        # to the project or inventing historical installation provenance.
        with tempfile.TemporaryDirectory(prefix="elara-update-check-") as temporary:
            source, info = bootstrap.download_kit(upstream["commit"], temporary)
            if info.get("verified_commit") != upstream["commit"]:
                raise ValueError("Downloaded revision does not match the checked revision.")
            preview = bootstrap.install(source, root, True, already_installed=True,
                                        researcher_paths=(manifest or {}).get("researcher_paths", []),
                                        dry_run=True)
            result["latest_version"] = bootstrap.kit_version(source)
            if bootstrap.installation_matches(preview):
                result.update(ready=True, status="current", installed_commit=upstream["commit"],
                              identity_basis="live content comparison")
            elif preview["update_conflicts"] or bootstrap.essential_conflicts(preview["researcher_paths"]):
                result.update(status="conflict", problems=preview["update_conflicts"] or
                              ["A required ELARA file belongs to the researcher."])
            else:
                result["status"] = "update_available"
        return result
    except bootstrap.BootstrapError as exc:
        result.update(status="unavailable", problems=[str(exc)])
    except (ValueError, OSError, TypeError, KeyError):
        result.update(status="unverified", problems=[
            "Installation evidence is incomplete, invalid, or inaccessible. Inspect it before updating; the new stage remains paused."
        ])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stage", required=True, help="canonical stage or utility identifier")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check(args.root, args.stage)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("ELARA: " + result["status"].replace("_", " "))
        if result["ready"]:
            print("Current on GitHub at " + result["checked_at"] + ". Continue under the stage's existing approvals.")
        else:
            print("The new stage remains paused. Follow workflow/shared/kit-updates.md.")
        for problem in result["problems"]:
            print(json.dumps(problem) if isinstance(problem, dict) else problem)
        if result["latest_commit"]:
            print("Latest commit: " + result["latest_commit"])
    return {"current": 0, "update_available": 2, "unavailable": 3}.get(result["status"], 4)


if __name__ == "__main__":
    sys.exit(main())
