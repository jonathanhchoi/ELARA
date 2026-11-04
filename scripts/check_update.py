"""Read-only GitHub currency and installation check before a new ELARA stage.

Updates never hold up research (2.19.0). Exit 0 (`ready: true`) means the stage
may start: on the current kit, on a newly installed update, or on the installed
version when an update cannot install cleanly, GitHub is unreachable, or ELARA's
own files here differ from their installed record. Those last cases carry a
one-sentence `notice` to tell the researcher once. Exit 2 means an update is
available (run --auto-update when writes are authorized). Exit 4 means an
update was interrupted part-way, the one case that waits: re-run the same
update once, then report it under workflow/shared/operational-recovery.md.
--auto-update installs an exact update only when its preview is conflict-free.
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


UNFINISHED = ("An ELARA update stopped part-way. Re-run the same update command once; if it still does not "
              "finish, report it under 'When something breaks' in workflow/shared/operational-recovery.md.")


def _continue_on_installed(result: dict, status: str, notice: str) -> dict:
    """Run the stage on the installed kit, recorded as such; the researcher hears it once."""
    result.update(ready=True, status=status, installation_verified=False, next_action="continue", notice=notice)
    return result


def check(root: Path, stage: str) -> dict:
    root = root.resolve()
    result = {
        "schema_version": "1.1", "check_id": str(uuid.uuid4()),
        "checked_at": bootstrap.utc_now(), "stage": stage,
        "repository": bootstrap.REPOSITORY, "ref": bootstrap.DEFAULT_REF,
        "ready": False, "status": "unverified", "installation_verified": False,
        "installed_commit": None, "latest_commit": None, "problems": [],
    }
    try:
        if (root / "project/ELARA_STORAGE.json").exists():
            from storage import status
            try:
                root = Path(status(root)["working_root"])
            except (ValueError, OSError, KeyError, TypeError) as exc:
                # A workspace that cannot be resolved is storage recovery, never "run as installed".
                result.update(status="storage_unresolved", next_action="resolve_storage", problems=[str(exc)])
                return result
        result["working_root"] = str(root)
        if (re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", stage) is None
                or not any((root / "workflow" / folder / (stage + ".md")).is_file()
                           for folder in ("stages", "utilities"))):
            result.update(status="invalid_stage", problems=["Name an existing canonical stage or utility."])
            return result
        manifest_path = root / bootstrap.MANIFEST_RELATIVE
        if ((root / bootstrap.UPDATE_PENDING_RELATIVE).exists()
                or (manifest_path.exists() and isinstance(record := json.loads(bootstrap.read_text(manifest_path)), dict)
                    and record.get("installation_complete") is False and not record.get("update_conflicts"))):
            result.update(status="unfinished_update", next_action="rerun_update", problems=[UNFINISHED])
            return result
        manifest, problems = installation_evidence(root)
        result["installed_commit"] = (manifest or {}).get("installed_commit")
        result["installed_version"] = (manifest or {}).get("kit_version")
        if problems:
            result["problems"] = problems
            return _continue_on_installed(result, "installed_modified",
                "Some of ELARA's own files in this project differ from the installed version, so this stage "
                "runs on them as they are and updates wait; nothing needs to be done now.")
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
        except bootstrap.BootstrapError as exc:
            result.update(upstream_checked=False, retry_at="next_stage_boundary")
            if installed is not None:
                result.update(ready=True, status="verified_installed", installation_verified=True,
                              identity_basis="current installed file verification", next_action="continue",
                              notice="GitHub could not be reached to check for an ELARA update; this stage "
                                     "runs on the installed version, and the check repeats at the next stage.")
                return result
            result["problems"] = [str(exc)]
            return _continue_on_installed(result, "unverified",
                "GitHub could not be reached and this installation has no recorded identity to verify, so "
                "this stage runs on ELARA as installed; the check repeats at the next stage.")
        result.update(latest_commit=upstream["commit"], latest_change=upstream["subject"],
                      latest_url=upstream["url"], upstream_checked=True)
        if installed is not None:
            current = installed == upstream["commit"]
            result.update(ready=current, status="current" if current else "update_available",
                          installation_verified=True, next_action="continue" if current else "auto_update")
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
                              installation_verified=True, identity_basis="live content comparison",
                              next_action="continue")
            elif preview["update_conflicts"] or bootstrap.essential_conflicts(preview["researcher_paths"]):
                result["problems"] = preview["update_conflicts"] or ["A required ELARA file belongs to the researcher."]
                _continue_on_installed(result, "update_deferred",
                    "An ELARA update is available but would change files that differ here, so it was not "
                    "installed; this stage runs on the installed version and nothing needs to be done now.")
            else:
                result.update(status="update_available", next_action="auto_update")
        return result
    except bootstrap.BootstrapError as exc:
        result["problems"] = [str(exc)]
        return _continue_on_installed(result, "unverified",
            "The ELARA update check could not finish, so this stage runs on ELARA as installed; "
            "the check repeats at the next stage.")
    except (ValueError, OSError, TypeError, KeyError):
        result["problems"] = ["Installation evidence is incomplete, invalid, or inaccessible."]
        return _continue_on_installed(result, "unverified",
            "ELARA's installation record here could not be verified, so this stage runs on ELARA as "
            "installed and updates wait; nothing needs to be done now.")


def prepare(root: Path, stage: str) -> dict:
    """Apply the automatic-update policy, with the existing protected installer.

    Call only when writes are authorized. The inspected upstream commit is the
    exact target; moving main does not produce an approval or recheck loop.
    The installer performs clean preflight, preserves ownership/protections,
    records interruptions, and runs its doctor on the installed code.
    """
    result = check(root, stage)
    if result["status"] == "unfinished_update":
        # Finish the interrupted update at the exact commit it recorded, once per call.
        root = Path(result["working_root"])
        try:
            pending = json.loads(bootstrap.read_text(root / bootstrap.UPDATE_PENDING_RELATIVE))
        except (OSError, ValueError):
            return result
        target, installed = pending.get("requested_commit"), pending.get("previous_commit")
        if not isinstance(target, str) or re.fullmatch(r"[0-9a-f]{40}", target) is None:
            return result
    elif result["status"] != "update_available":
        return result
    else:
        root = Path(result["working_root"])
        target = result["latest_commit"]
        installed = result["installed_commit"]
    args = argparse.Namespace(into=str(root), update=True, require_clean=True,
                              ref=target, source=None, dry_run=False, no_install=False,
                              skip_doctor=False, keep=True, platform="auto", model_evidence=None)
    try:
        report = bootstrap.bootstrap(args)
        manifest, problems = installation_evidence(root.resolve())
        if (not report["ok"] or not report["installation_complete"] or problems
                or (manifest or {}).get("installed_commit") != target
                or (root / bootstrap.UPDATE_PENDING_RELATIVE).exists()):
            return _after_failed_update(root, result, installed, problems or ["Update verification did not finish."])
        result.update(status="updated", ready=True, installed_commit=target, installation_verified=True, problems=[],
                      installed_version=manifest["kit_version"], next_action="reload_instructions")
    except (bootstrap.BootstrapError, OSError, ValueError, TypeError, KeyError) as exc:
        return _after_failed_update(root, result, installed, [str(exc)])
    return result


def _after_failed_update(root: Path, result: dict, installed: str | None, problems: list) -> dict:
    """A conflicted preview writes nothing: keep working on the installed kit. Only a part-way write waits."""
    result["problems"] = problems
    try:
        manifest, evidence = installation_evidence(root.resolve())
        untouched = (not (root / bootstrap.UPDATE_PENDING_RELATIVE).exists() and not evidence
                     and (manifest or {}).get("installed_commit") == installed)
    except (ValueError, OSError, TypeError, KeyError):
        untouched = False
    if untouched:
        _continue_on_installed(result, "update_deferred",
            "An ELARA update is available but could not be installed cleanly here, so this stage runs on the "
            "installed version and nothing needs to be done now.")
        result["installation_verified"] = installed is not None
        return result
    result.update(status="unfinished_update", ready=False, next_action="rerun_update",
                  problems=problems + [UNFINISHED])
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
        if result.get("notice"):
            print(result["notice"])
        if result["ready"]:
            print("Continue under the stage's existing approvals.")
        else:
            print("Follow workflow/shared/kit-updates.md before starting the stage.")
        for problem in result["problems"]:
            print(json.dumps(problem) if isinstance(problem, dict) else problem)
        if result["latest_commit"]:
            print("Latest commit: " + result["latest_commit"])
    return 0 if result["ready"] else {"update_available": 2}.get(result["status"], 4)


if __name__ == "__main__":
    sys.exit(main())
