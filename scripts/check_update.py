"""Read-only GitHub currency and installation check before a new ELARA stage.

Exit 0 means verified usable installed bytes; 2 means an update is available,
3 means no usable installation could be verified, and 4 means installation
evidence needs repair. --auto-update installs an exact, conflict-free update.
Neither mode authorizes research or changes frozen run bindings.
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
        installed = result["installed_commit"]
        if installed is None and manifest is None:
            local = bootstrap.local_source_info(root)
            installed = local.get("verified_commit")
            result["installed_commit"] = installed
            result["installed_version"] = bootstrap.kit_version(root)
        # Reverify bytes on every call; a previous successful network result is
        # never the basis of offline fallback. Legacy labels alone do not pass.
        try:
            upstream = bootstrap.github_commit()
        except bootstrap.BootstrapError:
            if installed is not None:
                result.update(ready=True, status="verified_installed", retry_at="next_stage_boundary",
                              identity_basis="current installed file verification", upstream_checked=False)
                return result
            raise
        result.update(latest_commit=upstream["commit"], latest_change=upstream["subject"],
                      latest_url=upstream["url"], upstream_checked=True)
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


def prepare(root: Path, stage: str) -> dict:
    """Apply the automatic-update policy, with the existing protected installer.

    Call only when writes are authorized. The inspected upstream commit is the
    exact target; moving main does not produce an approval or recheck loop.
    The installer performs clean preflight, preserves ownership/protections,
    records interruptions, and runs its doctor on the installed code.
    """
    result = check(root, stage)
    if result["status"] != "update_available":
        return result
    target = result["latest_commit"]
    args = argparse.Namespace(into=str(root), update=True, require_clean=True,
                              ref=target, source=None, dry_run=False, no_install=False,
                              skip_doctor=False, keep=True, platform="auto", model_evidence=None)
    try:
        report = bootstrap.bootstrap(args)
        manifest, problems = installation_evidence(root.resolve())
        if (not report["ok"] or not report["installation_complete"] or problems
                or (manifest or {}).get("installed_commit") != target
                or (root / bootstrap.UPDATE_PENDING_RELATIVE).exists()):
            result.update(status="conflict", ready=False, next_action="repair",
                          problems=problems or ["Update verification did not finish."])
            return result
        result.update(status="updated", ready=True, installed_commit=target,
                      installed_version=manifest["kit_version"], next_action="reload_instructions")
    except (bootstrap.BootstrapError, OSError, ValueError, TypeError, KeyError):
        result.update(status="conflict", ready=False, next_action="repair",
                      problems=["Inspect the protected installation and complete or repair the exact update; no researcher decision is implied."])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--stage", required=True, help="canonical stage or utility identifier")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--auto-update", action="store_true", help="install a verified compatible update when writes are authorized")
    args = parser.parse_args()
    result = prepare(args.root, args.stage) if args.auto_update else check(args.root, args.stage)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("ELARA: " + result["status"].replace("_", " "))
        if result["ready"]:
            print("Installed bytes verified at " + result["checked_at"] + ". Continue under the stage's existing approvals.")
        else:
            print("The new stage remains paused. Follow workflow/shared/kit-updates.md.")
        for problem in result["problems"]:
            print(json.dumps(problem) if isinstance(problem, dict) else problem)
        if result["latest_commit"]:
            print("Latest commit: " + result["latest_commit"])
    return 0 if result["ready"] else {"update_available": 2, "unavailable": 3}.get(result["status"], 4)


if __name__ == "__main__":
    sys.exit(main())
