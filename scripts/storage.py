"""Small file primitives for agent-managed local work and verified cloud exports.

The agent chooses inputs, checkpoint contents, timing, and recovery. This module
only binds roots, copies bytes, and records evidence. It never launches research,
migrates a run, changes Drive settings, or treats a sync-folder copy as an upload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


BINDING = "project/ELARA_STORAGE.json"
OPERATIONS = "project/storage"
EXPORTS = "ELARA_Results"


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def inside(root: Path, relative: str) -> Path:
    """Reject traversal and links out of a recorded root, including junctions."""
    name = Path(relative)
    if name.is_absolute() or not name.parts or ".." in name.parts:
        raise ValueError("Expected a relative path inside the recorded folder: " + relative)
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path leaves the recorded folder: " + str(path))
    return path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def capacity(path: Path, size: int) -> None:
    parent = path
    while not parent.exists():
        parent = parent.parent
    if shutil.disk_usage(parent).free < size:
        raise OSError("Not enough space for the selected files in " + str(path))


def copy_verified(source: Path, destination: Path, expected: str | None = None) -> dict:
    """Idempotent under the contract's serial writer; never replace conflicting bytes."""
    expected = expected or digest(source)
    size = source.stat().st_size
    if destination.exists():
        if destination.is_file() and digest(destination) == expected:
            return {"size": size, "sha256": expected}
        raise ValueError("Existing destination differs; preserve it and choose a new version: " + str(destination))
    capacity(destination.parent, size)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name("." + destination.name + "." + uuid.uuid4().hex + ".partial")
    try:
        with source.open("rb") as incoming, partial.open("xb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        if digest(partial) != expected or digest(source) != expected:
            raise ValueError("Source changed or copy verification failed: " + str(source))
        if destination.exists():
            raise ValueError("Destination appeared during copying: " + str(destination))
        partial.rename(destination)
    finally:
        partial.unlink(missing_ok=True)
    return {"size": size, "sha256": expected}


def local_base() -> Path:
    override = os.environ.get("ELARA_WORKSPACE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "ELARA/workspaces"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/ELARA/workspaces"
    return Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "elara/workspaces"


def status(root: Path) -> dict:
    """Read only. A missing companion is recovery work, never a fresh project."""
    root = root.resolve()
    record = inside(root, BINDING)
    if not record.exists():
        return {"status": "unmanaged", "working_root": str(root)}
    value = read_json(record)
    if not isinstance(value, dict) or value.get("schema_version") != "1.0":
        raise ValueError("Unsupported storage record")
    home, working = Path(value["project_home"]), Path(value["working_root"])
    if not home.is_absolute() or not working.is_absolute() or root not in (home, working):
        raise ValueError("Storage record belongs to a different location; reconcile before resuming")
    if home == working or home in working.parents or working in home.parents:
        raise ValueError("Project home and working folder must be separate")
    companion = inside(working, BINDING)
    if not companion.is_file() or read_json(companion) != value:
        raise ValueError("Recorded local workspace is missing or differs; recover it without reinitializing")
    if not inside(working, "project/PROJECT_STATE.md").is_file():
        raise ValueError("Recorded local project state is missing; recover it without reinitializing")
    return {**value, "status": "managed", "exports_root": str(inside(home, EXPORTS))}


def bind(home: Path, working: Path) -> dict:
    """Record an agent-verified transition; this does not migrate or approve research."""
    from bootstrap import cloud_sync_service, is_kit_root

    home, working = home.resolve(), working.resolve()
    if inside(home, BINDING).exists():
        current = status(home)
        if current["working_root"] != str(working):
            raise ValueError("A different working folder is already recorded")
        return current
    if home == working or home in working.parents or working in home.parents:
        raise ValueError("Project home and working folder must be separate")
    if cloud_sync_service(working):
        raise ValueError("Choose a local working folder outside known synchronization roots")
    if not is_kit_root(working) or not inside(working, "project/PROJECT_STATE.md").is_file():
        raise ValueError("Install and verify the local project before binding it")
    if inside(working, BINDING).exists():
        # Complete an interrupted bind only if its reciprocal identity agrees.
        value = read_json(inside(working, BINDING))
        if value.get("project_home") != str(home) or value.get("working_root") != str(working):
            raise ValueError("Local workspace belongs to another project")
    else:
        value = {"schema_version": "1.0", "project_id": uuid.uuid4().hex,
                 "project_home": str(home), "working_root": str(working)}
        write_new(inside(working, BINDING), value)
    write_new(inside(home, BINDING), value)
    return status(home)


def setup(home: Path, kit: Path, *, no_install: bool = False, dry_run: bool = False) -> dict:
    """Fresh setup only; an existing scientific history stays with the agent."""
    from bootstrap import PROJECT_TEMPLATE_FILES, cloud_sync_service, source_is_clean_template

    home, kit = home.resolve(), kit.resolve()
    if inside(home, BINDING).exists():
        return status(home)
    if not source_is_clean_template(home):
        return {"status": "needs_transition", "working_root": str(home)}
    # A blank routing pointer alone does not prove absence of project history.
    for name in ("DECISIONS.md", "RUN_LEDGER.md", "DEVIATIONS.md"):
        if (home / "project" / name).read_bytes() != (kit / "project" / name).read_bytes():
            return {"status": "needs_transition", "working_root": str(home)}
    permitted = {Path(p).name for p in PROJECT_TEMPLATE_FILES if Path(p).parent == Path("project")}
    permitted.update({"inputs", "BOOTSTRAP.md", "ELARA_MANIFEST.json", "ELARA_UPDATE_PENDING.json"})
    if any(p.name not in permitted for p in (home / "project").iterdir()):
        return {"status": "needs_transition", "working_root": str(home)}
    if (kit / "project/ELARA_MANIFEST.json").exists() or not source_is_clean_template(kit):
        raise ValueError("Use a clean kit source, not a mixed installed project")
    base = local_base().resolve()
    if cloud_sync_service(base) or home == base or home in base.parents or base in home.parents:
        raise ValueError("Choose an unsynced ELARA_WORKSPACE_HOME outside the project")
    # Stable on retries, different for two project folders with the same name.
    working = base / ("project-" + hashlib.sha256(os.fsencode(home)).hexdigest()[:16])
    if dry_run:
        return {"status": "planned", "working_root": str(working)}
    if working.exists() and any(working.iterdir()):
        raise ValueError("Unbound local folder already exists; inspect it before reusing: " + str(working))
    capacity(base, sum(p.stat().st_size for p in kit.rglob("*") if p.is_file() and ".git" not in p.parts))
    command = [sys.executable, str(kit / "scripts/bootstrap.py"), "--into", str(working),
               "--source", str(kit), "--skip-doctor", "--json"]
    if no_install:
        command.append("--no-install")
    result = subprocess.run(command, text=True, capture_output=True, check=False, timeout=1200)
    installed = json.loads(result.stdout)
    if result.returncode or not installed.get("installation_complete"):
        raise ValueError("Local installation needs repair: " + str(installed.get("error", working)))
    return {**bind(home, working), "python_for_kit": installed["python_for_kit"], "created": True}


def managed(root: Path) -> tuple[dict, Path]:
    value = status(root)
    if value["status"] != "managed":
        raise ValueError("Set up the local workspace first")
    return value, Path(value["working_root"])


def stage(root: Path, source: Path, relative: str) -> dict:
    _, working = managed(root)
    if not relative.replace("\\", "/").startswith("project/inputs/"):
        raise ValueError("Stage inputs under project/inputs/ using a new version")
    destination = inside(working, relative)
    row = {"source": str(source.resolve()), "destination": str(destination),
           **copy_verified(source, destination)}
    write_new(inside(working, OPERATIONS + "/imports/" + stamp() + ".json"), row)
    return row


def snapshot(root: Path, selection: dict, label: str) -> dict:
    value, working = managed(root)
    paths = selection["files"]
    if not isinstance(paths, list) or not paths:
        raise ValueError("Select a nonempty list of unique relative file paths")
    paths = [Path(path).as_posix() for path in paths]
    if len(set(paths)) != len(paths):
        raise ValueError("Select a nonempty list of unique relative file paths")
    rows = []
    for relative in paths:
        source = inside(working, relative)
        parts = Path(relative).parts
        if (source.resolve().is_relative_to(inside(working, OPERATIONS).resolve())
                or relative.replace("\\", "/") == BINDING
                or any(p in (".git", ".venv", "__pycache__", EXPORTS) for p in parts)):
            raise ValueError("Exclude storage records, previous exports, and disposable files: " + relative)
        rows.append({"path": Path(relative).as_posix(), "size": source.stat().st_size, "sha256": digest(source)})
    capacity(working, sum(row["size"] for row in rows))
    identity = stamp() + "-" + uuid.uuid4().hex[:8]
    directory = inside(working, OPERATIONS + "/exports/" + identity)
    for row in rows:
        copy_verified(inside(working, row["path"]), inside(directory, "files/" + row["path"]), row["sha256"])
    # Verify the whole selected checkpoint remained stable, not just each file's copy.
    for row in rows:
        if digest(inside(working, row["path"])) != row["sha256"]:
            raise ValueError("Selected files changed during the snapshot; stop their writers and try again")
    manifest = {"schema_version": "1.0", "snapshot_id": identity, "project_id": value["project_id"],
                "working_root": str(working), "label": label, "files": rows,
                "omissions": selection.get("omissions", [])}
    write_new(directory / "manifest.json", manifest)
    return {"snapshot_id": identity, "snapshot": str(directory), "status": "pending"}


def publish(root: Path, identity: str, name: str | None = None) -> dict:
    value, working = managed(root)
    if Path(identity).name != identity or not identity or identity in (".", ".."):
        raise ValueError("Expected a snapshot identifier")
    directory = inside(working, OPERATIONS + "/exports/" + identity)
    manifest = read_json(directory / "manifest.json")
    if manifest["project_id"] != value["project_id"] or manifest["snapshot_id"] != identity:
        raise ValueError("Snapshot belongs to a different project")
    export_name = name or identity
    if Path(export_name).name != export_name or export_name in (".", ".."):
        raise ValueError("Expected one export folder name")
    receipt = {"snapshot_id": identity, "export_name": export_name, "time": stamp(), "status": "pending"}
    try:
        home = Path(value["project_home"])
        # Do not recreate an offline mount at an ordinary local path.
        if read_json(inside(home, BINDING)) != {k: value[k] for k in ("schema_version", "project_id", "project_home", "working_root")}:
            raise ValueError("Project home differs; reconcile before exporting")
        destination = inside(home, EXPORTS + "/" + export_name)
        for row in manifest["files"]:
            source = inside(directory, "files/" + row["path"])
            if source.stat().st_size != row["size"] or digest(source) != row["sha256"]:
                raise ValueError("Local snapshot verification failed: " + row["path"])
            copy_verified(source, inside(destination, "files/" + row["path"]), row["sha256"])
        copy_verified(directory / "manifest.json", destination / "manifest.json")
        # Re-read destination bytes before publishing the final completion record.
        for row in manifest["files"]:
            if digest(inside(destination, "files/" + row["path"])) != row["sha256"]:
                raise ValueError("Destination verification failed: " + row["path"])
        complete = {"snapshot_id": identity, "manifest_sha256": digest(directory / "manifest.json"),
                    "status": "copied_to_sync_folder", "upload_confirmed": False}
        marker = destination / "COMPLETE.json"
        if marker.exists():
            if read_json(marker) != complete:
                raise ValueError("Export completion record differs")
        else:
            write_new(marker, complete)
        receipt.update(complete, destination=str(destination))
    except (OSError, ValueError, KeyError) as exc:
        receipt["error"] = str(exc)
    write_new(directory / "receipts" / (stamp() + ".json"), receipt)
    return receipt


def retry(root: Path) -> list[dict]:
    _, working = managed(root)
    results = []
    for manifest in sorted(inside(working, OPERATIONS + "/exports").glob("*/manifest.json")):
        receipts = sorted((manifest.parent / "receipts").glob("*.json"))
        latest = read_json(receipts[-1]) if receipts else {}
        if latest.get("status") != "copied_to_sync_folder":
            results.append(publish(root, manifest.parent.name, latest.get("export_name")))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("status", "setup", "bind", "stage", "snapshot", "publish", "retry"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--kit", type=Path)
    parser.add_argument("--working-root", type=Path)
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--into")
    parser.add_argument("--selection", type=Path, help='JSON object: {"files": [relative files], "omissions": [...]}')
    parser.add_argument("--label")
    parser.add_argument("--snapshot")
    parser.add_argument("--name", help="new destination name if an earlier export conflicts")
    args = parser.parse_args()
    try:
        if args.dry_run and args.command != "setup":
            raise ValueError("Only setup supports --dry-run; status is read-only")
        if args.command == "status":
            result = status(args.root)
        elif args.command == "setup" and args.kit:
            result = setup(args.root, args.kit, no_install=args.no_install, dry_run=args.dry_run)
        elif args.command == "bind" and args.working_root:
            result = bind(args.root, args.working_root)
        elif args.command == "stage" and args.source and args.into:
            result = stage(args.root, args.source, args.into)
        elif args.command == "snapshot" and args.selection and args.label:
            result = snapshot(args.root, read_json(args.selection), args.label)
        elif args.command == "publish" and args.snapshot:
            result = publish(args.root, args.snapshot, args.name)
        elif args.command == "retry":
            result = retry(args.root)
        else:
            raise ValueError("Missing arguments for " + args.command)
        print(json.dumps(result, indent=2))
        pending = any(r.get("status") == "pending" for r in result) if isinstance(result, list) else result.get("status") == "pending"
        return 1 if pending and args.command in ("publish", "retry") else 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "needs_recovery", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
