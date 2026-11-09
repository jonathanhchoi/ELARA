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
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path


BINDING = "project/ELARA_STORAGE.json"
OPERATIONS = "project/storage"
EXPORTS = "ELARA_Results"
# A stage-end export carries the deliverables as files and each run as one zip,
# never thousands of loose run files (2.19.0).
RECORDS = ("project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md", "project/DEVIATIONS.md")
SKIPPED_PARTS = {".git", ".venv", "__pycache__", "node_modules", EXPORTS}
LOOSE_FILE_LIMIT = 200
FOLDER_AS_FILES_LIMIT = 50
# The researcher's working draft in the project home, consulted for intended methods (2.21.0).
DRAFT_NAME = "current_draft.docx"


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


def current_draft(root: Path) -> dict:
    """Read only: report the researcher's current_draft.docx in the project home.

    ``changed`` is true when the file exists and its SHA-256 differs from the copy ELARA last
    reconciled (``active_artifacts.current_draft`` in the working root's state); the
    draft-reconciliation utility then runs before the next stage. A file that cannot be read
    is reported, never raised, so status keeps working while the file syncs or is open.
    """
    from workflow_lib import parse_frontmatter

    root = root.resolve()
    record = status(root)
    working = Path(record["working_root"])
    home = Path(record["project_home"]) if record["status"] == "managed" else root
    result: dict = {"present": False, "changed": False, "reconciled_sha256": None}
    try:
        state, _ = parse_frontmatter(inside(working, "project/PROJECT_STATE.md"))
        entry = (state.get("active_artifacts") or {}).get("current_draft")
    except (OSError, ValueError):
        entry = None
    if isinstance(entry, dict) and entry.get("sha256"):
        result["reconciled_sha256"] = str(entry["sha256"]).casefold()
    elif isinstance(entry, str):
        path = inside(working, entry)
        result["reconciled_sha256"] = digest(path) if path.is_file() else None
    try:
        matches = sorted(p for p in home.iterdir() if p.is_file() and p.name.casefold() == DRAFT_NAME)
    except OSError as exc:
        return {**result, "error": str(exc)}
    if not matches:
        return {**result, "removed": result["reconciled_sha256"] is not None}
    if len(matches) > 1:
        return {**result, "present": True, "error": "keep one file named current_draft.docx: "
                + ", ".join(p.name for p in matches)}
    result.update(present=True, path=str(matches[0]))
    try:
        result["sha256"] = digest(matches[0])
    except OSError as exc:
        return {**result, "readable": False, "error": str(exc)}
    result["changed"] = result["sha256"] != result["reconciled_sha256"]
    return result


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


def _skipped(relative: str) -> bool:
    """Storage records, earlier exports, Git metadata, and disposable environments."""
    parts = Path(relative).parts
    return (relative == BINDING or relative == OPERATIONS or relative.startswith(OPERATIONS + "/")
            or any(part in SKIPPED_PARTS for part in parts) or Path(relative).name.endswith(".partial"))


def _relative_list(values, kind: str) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("List the " + kind + " as relative paths")
    paths = [Path(value).as_posix() for value in values]
    if len(set(paths)) != len(paths):
        raise ValueError("Each of the " + kind + " may be listed once")
    return paths


def _files_under(working: Path, relative: str) -> list[str]:
    folder = inside(working, relative)
    found = []
    for path in sorted(folder.rglob("*")):
        name = path.relative_to(working).as_posix()
        if path.is_file() and not _skipped(name):
            inside(working, name)
            found.append(name)
    return found


def _active_paths(working: Path) -> tuple[dict, list[str]]:
    from workflow_lib import parse_frontmatter

    state, _ = parse_frontmatter(inside(working, "project/PROJECT_STATE.md"))
    active = state.get("active_artifacts") or {}
    paths = []
    for value in (active.values() if isinstance(active, dict) else []):
        path = value.get("path") if isinstance(value, dict) else value
        if isinstance(path, str) and path.strip():
            paths.append(path.replace("\\", "/").strip().rstrip("/"))
    return state, list(dict.fromkeys(paths))


def _already_exported(working: Path) -> tuple[dict[str, set], set]:
    """Folders in a completed export, by (file count, bytes); older loose rows by (path, size)."""
    archived: dict[str, set] = {}
    loose: set = set()
    for manifest_path in sorted(inside(working, OPERATIONS + "/exports").glob("*/manifest.json")):
        receipts = sorted((manifest_path.parent / "receipts").glob("*.json"))
        if not receipts or read_json(receipts[-1]).get("status") != "copied_to_sync_folder":
            continue
        manifest = read_json(manifest_path)
        for row in manifest.get("archives", []):
            archived.setdefault(row["path"], set()).add((row["file_count"], row["total_size"]))
        for row in manifest.get("files", []):
            loose.add((row["path"], row["size"]))
    return archived, loose


def default_selection(root: Path) -> dict:
    """What a stage-end export carries: the deliverables as files, each run as one archive.

    Deliverables are the project records, kit issue reports, and every active
    output. Researcher originals and their input copies stay where they are.
    A run already in a completed export, unchanged, is not sent again; a run
    still being written is left out with that reason.
    """
    _, working = managed(root)
    state, active = _active_paths(working)
    deliverables = [name for name in RECORDS if inside(working, name).is_file()]
    if inside(working, "project/kit_issues").is_dir():
        deliverables += _files_under(working, "project/kit_issues")
    archives, omissions = [], []
    for relative in active:
        try:
            path = inside(working, relative)
        except ValueError:
            omissions.append({"path": relative, "reason": "active output path is outside the project"})
            continue
        if relative.startswith("project/inputs/") or relative.startswith("project/artifacts/imported_"):
            omissions.append({"path": relative, "reason": "input copy; the original stays where the researcher keeps it"})
        elif _skipped(relative):
            continue
        elif path.is_file():
            deliverables.append(relative)
        elif path.is_dir() and relative.startswith("project/runs/"):
            continue  # a run's own archive carries it
        elif path.is_dir():
            files = _files_under(working, relative)
            if len(files) > FOLDER_AS_FILES_LIMIT:
                archives.append(relative)
            else:
                deliverables += files
        else:
            omissions.append({"path": relative, "reason": "active output not found"})
    runs = inside(working, "project/runs")
    live = state.get("last_run_id") if state.get("status") == "running" else None
    archived, loose = _already_exported(working)
    for run in (sorted(p for p in runs.iterdir() if p.is_dir()) if runs.is_dir() else []):
        relative = run.relative_to(working).as_posix()
        if run.name == live:
            omissions.append({"path": relative, "reason": "run still in progress; exported when it ends"})
            continue
        sizes = [(name, inside(working, name).stat().st_size) for name in _files_under(working, relative)]
        if not sizes:
            continue
        if ((len(sizes), sum(size for _, size in sizes)) in archived.get(relative, set())
                or all(row in loose for row in sizes)):
            continue
        archives.append(relative)
    return {"deliverables": list(dict.fromkeys(deliverables)), "archives": list(dict.fromkeys(archives)),
            "omissions": omissions}


def _write_archive(working: Path, relative: str, destination: Path) -> dict:
    """One reproducible zip of a folder; member hashes come from the bytes written."""
    files = _files_under(working, relative)
    if not files:
        raise ValueError("Nothing to archive in " + relative)
    before = {name: inside(working, name).stat() for name in files}
    capacity(destination.parent, sum(stat.st_size for stat in before.values()))
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name("." + destination.name + "." + uuid.uuid4().hex + ".partial")
    parent = Path(relative).parent
    members = []
    try:
        with zipfile.ZipFile(partial, "x", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
            for name in files:
                info = zipfile.ZipInfo(Path(name).relative_to(parent).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                value = hashlib.sha256()
                with inside(working, name).open("rb") as incoming, archive.open(info, "w", force_zip64=True) as outgoing:
                    for block in iter(lambda: incoming.read(1024 * 1024), b""):
                        value.update(block)
                        outgoing.write(block)
                members.append({"path": name, "size": before[name].st_size, "sha256": value.hexdigest()})
        for name in files:
            now = inside(working, name).stat()
            if (now.st_size, now.st_mtime_ns) != (before[name].st_size, before[name].st_mtime_ns):
                raise ValueError("Files changed while " + relative + " was archived; stop their writers and try again")
        with zipfile.ZipFile(partial) as archive:
            if archive.testzip() is not None:
                raise ValueError("Archive verification failed: " + relative)
        partial.rename(destination)
    finally:
        partial.unlink(missing_ok=True)
    return {"path": relative, "archive": "archives/" + relative + ".zip", "size": destination.stat().st_size,
            "sha256": digest(destination), "file_count": len(members),
            "total_size": sum(row["size"] for row in members), "members": members}


def _export_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:40].strip("-") or "export"
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + slug + "-" + uuid.uuid4().hex[:6]


def snapshot(root: Path, selection: dict | None, label: str) -> dict:
    """Freeze a local copy: deliverable files as they are, each listed folder as one zip."""
    value, working = managed(root)
    selection = default_selection(root) if selection is None else selection
    if (not isinstance(selection, dict) or "files" in selection
            or set(selection) - {"deliverables", "archives", "omissions"}):
        raise ValueError('A selection lists "deliverables" (files copied as they are) and "archives" '
                         '(folders, normally one per finished run, each copied as one zip)')
    deliverables = _relative_list(selection.get("deliverables", []), "deliverables")
    archives = _relative_list(selection.get("archives", []), "archives")
    if not deliverables and not archives:
        raise ValueError("Select at least one deliverable or archive")
    if len(deliverables) > LOOSE_FILE_LIMIT:
        raise ValueError("More than " + str(LOOSE_FILE_LIMIT) + " loose files; list their folders under archives")
    rows = []
    for relative in deliverables:
        source = inside(working, relative)
        if _skipped(relative) or not source.is_file():
            raise ValueError("A deliverable must be a project file, not a storage record, export, or disposable file: " + relative)
        rows.append({"path": relative, "size": source.stat().st_size, "sha256": digest(source)})
    for relative in archives:
        if _skipped(relative) or not inside(working, relative).is_dir():
            raise ValueError("An archive must be a project folder, not a storage record or export: " + relative)
    capacity(working, sum(row["size"] for row in rows))
    identity = _export_id(label)
    directory = inside(working, OPERATIONS + "/exports/" + identity)
    for row in rows:
        copy_verified(inside(working, row["path"]), inside(directory, "deliverables/" + row["path"]), row["sha256"])
    # Verify the selected deliverables stayed stable as a set, not just each file's copy.
    for row in rows:
        if digest(inside(working, row["path"])) != row["sha256"]:
            raise ValueError("Selected files changed during the snapshot; stop their writers and try again")
    archived = [_write_archive(working, relative, inside(directory, "archives/" + relative + ".zip"))
                for relative in archives]
    manifest = {"schema_version": "2.0", "snapshot_id": identity, "project_id": value["project_id"],
                "working_root": str(working), "label": label, "deliverables": rows,
                "archives": archived, "omissions": selection.get("omissions", [])}
    write_new(directory / "manifest.json", manifest)
    return {"snapshot_id": identity, "snapshot": str(directory), "status": "pending",
            "deliverables": len(rows), "archives": len(archived)}


def _payload(manifest: dict) -> list[tuple[str, int, str]]:
    """(path inside the export, size, sha256) for every copied file, in either format."""
    if manifest.get("schema_version") == "2.0":
        return ([("deliverables/" + row["path"], row["size"], row["sha256"]) for row in manifest["deliverables"]]
                + [(row["archive"], row["size"], row["sha256"]) for row in manifest["archives"]])
    return [("files/" + row["path"], row["size"], row["sha256"]) for row in manifest["files"]]


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
        payload = _payload(manifest)
        for relative, size, expected in payload:
            source = inside(directory, relative)
            if source.stat().st_size != size or digest(source) != expected:
                raise ValueError("Local snapshot verification failed: " + relative)
            copy_verified(source, inside(destination, relative), expected)
        copy_verified(directory / "manifest.json", destination / "manifest.json")
        # Re-read destination bytes before publishing the final completion record.
        for relative, _, expected in payload:
            if digest(inside(destination, relative)) != expected:
                raise ValueError("Destination verification failed: " + relative)
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


def export(root: Path, label: str, selection: dict | None = None) -> dict:
    """The stage-end export: snapshot the default (or a given) selection, then publish it."""
    if status(root)["status"] != "managed":
        return {"status": "not_needed", "reason": "the project home is also the working folder"}
    snap = snapshot(root, selection, label)
    return {**publish(root, snap["snapshot_id"]), "deliverables": snap["deliverables"], "archives": snap["archives"]}


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
    parser.add_argument("command", choices=("status", "setup", "bind", "stage", "export", "snapshot", "publish", "retry"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--kit", type=Path)
    parser.add_argument("--working-root", type=Path)
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--into")
    parser.add_argument("--selection", type=Path, help='optional JSON object: {"deliverables": [files], "archives": [folders], "omissions": [...]}')
    parser.add_argument("--label")
    parser.add_argument("--snapshot")
    parser.add_argument("--name", help="new destination name if an earlier export conflicts")
    args = parser.parse_args()
    try:
        if args.dry_run and args.command != "setup":
            raise ValueError("Only setup supports --dry-run; status is read-only")
        if args.command == "status":
            result = {**status(args.root), "current_draft": current_draft(args.root)}
        elif args.command == "setup" and args.kit:
            result = setup(args.root, args.kit, no_install=args.no_install, dry_run=args.dry_run)
        elif args.command == "bind" and args.working_root:
            result = bind(args.root, args.working_root)
        elif args.command == "stage" and args.source and args.into:
            result = stage(args.root, args.source, args.into)
        elif args.command == "export" and args.label:
            result = export(args.root, args.label, read_json(args.selection) if args.selection else None)
        elif args.command == "snapshot" and args.label:
            result = snapshot(args.root, read_json(args.selection) if args.selection else None, args.label)
        elif args.command == "publish" and args.snapshot:
            result = publish(args.root, args.snapshot, args.name)
        elif args.command == "retry":
            result = retry(args.root)
        else:
            raise ValueError("Missing arguments for " + args.command)
        print(json.dumps(result, indent=2))
        pending = any(r.get("status") == "pending" for r in result) if isinstance(result, list) else result.get("status") == "pending"
        return 1 if pending and args.command in ("export", "publish", "retry") else 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "needs_recovery", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
