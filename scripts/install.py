"""Install ELARA into the folder you are working in.

Run it from the folder where you want to work (empty, or already holding your
draft, data, or notes), pointing at a downloaded copy of the kit:

    git clone --depth 1 https://github.com/jonathanhchoi/ELARA.git .elara-src
    python .elara-src/scripts/install.py

It copies the kit into the current folder without overwriting anything you
already have, installs the kit's one Python dependency, runs the preflight
doctor, removes the temporary download, and tells the assistant to read
START_HERE.md next. Running it again is safe: files that are already in place
are left alone, and an initialized project under project/ is never touched.

Options:
    --target DIR    install into DIR instead of the current directory
    --overwrite     replace kit files that already exist and differ (a backup
                    of each replaced file is kept under .elara-backup/); this
                    is also how you upgrade the kit; project/ is never replaced
    --skip-install  do not run pip
    --skip-doctor   do not run scripts/doctor.py afterwards
    --keep-source   leave the downloaded copy in place

This file deliberately avoids newer Python syntax so that an old interpreter
prints the version advice below instead of a SyntaxError.
"""

import sys

if sys.version_info < (3, 10):
    sys.stderr.write(
        "ELARA needs Python 3.10 or newer; you are running Python "
        + ".".join(str(part) for part in sys.version_info[:3])
        + ".\n"
        "Please install a current Python from https://www.python.org/downloads/\n"
        "then run this command again (on Windows the launcher 'py' may help:\n"
        "py .elara-src/scripts/install.py).\n"
    )
    sys.exit(1)

import argparse  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import shutil  # noqa: E402
import stat  # noqa: E402
import subprocess  # noqa: E402
from pathlib import Path  # noqa: E402


# Directories that belong to the download, not to a research workspace.
SKIP_DIRS = frozenset(
    [".git", ".github", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "build"]
)
SKIP_SUFFIXES = (".pyc", ".pyo")
NOISE_NAMES = frozenset([".DS_Store", "Thumbs.db", "Desktop.ini", "desktop.ini"])
BACKUP_DIR = ".elara-backup"

# Kit files a workspace cannot do without. A conflict on one of these blocks a
# clean install; a conflict on anything else (README.md, LICENSE, .gitignore,
# requirements.txt) is reported but does not.
ESSENTIAL_ROOT_FILES = frozenset(["AGENTS.md", "CLAUDE.md", "START_HERE.md", "PIPELINE.md"])
ESSENTIAL_DIRS = frozenset(["workflow", "scripts", ".agents", ".claude", "tests"])

CLOUD_SYNC_MARKERS = ("google drive", "googledrive", "onedrive", "dropbox", "icloud", "box sync")

HOST_NOT_DETECTED = "no supported agent host was detected"


def _is_essential(relative):
    parts = relative.parts
    if len(parts) == 1:
        return parts[0] in ESSENTIAL_ROOT_FILES
    return parts[0] in ESSENTIAL_DIRS


def _skip(relative):
    if any(part in SKIP_DIRS for part in relative.parts):
        return True
    return relative.parts[-1].endswith(SKIP_SUFFIXES)


def _same_bytes(first, second):
    try:
        if first.stat().st_size != second.stat().st_size:
            return False
        return first.read_bytes() == second.read_bytes()
    except OSError:
        return False


def _force_writable(function, path, _excinfo):
    os.chmod(path, stat.S_IWRITE)
    function(path)


def _rmtree(path):
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_force_writable)
    else:
        shutil.rmtree(path, onerror=_force_writable)


def _cloud_synced(path):
    lowered = str(path).lower()
    return any(marker in lowered for marker in CLOUD_SYNC_MARKERS)


def copy_kit(source, target, overwrite=False):
    """Copy the kit from source into target and return a summary dictionary.

    Existing files are never silently replaced. Files under project/ are the
    researcher's once they exist and are never replaced, even with overwrite.
    """
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = target / BACKUP_DIR / stamp
    summary = {
        "copied": 0,
        "already_present": 0,
        "kept_project_files": 0,
        "replaced": [],
        "conflicts": [],
        "essential_conflicts": [],
        "backup_dir": None,
    }
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if _skip(relative) or relative.parts[0] == BACKUP_DIR:
            continue
        destination = target / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if not path.is_file():
            continue
        if destination.exists():
            if _same_bytes(path, destination):
                summary["already_present"] += 1
                continue
            if relative.parts[0] == "project":
                summary["kept_project_files"] += 1
                continue
            if overwrite:
                backup = backup_root / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
                shutil.copy2(path, destination)
                summary["replaced"].append(relative.as_posix())
                summary["backup_dir"] = backup_root
                continue
            summary["conflicts"].append(relative.as_posix())
            if _is_essential(relative):
                summary["essential_conflicts"].append(relative.as_posix())
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        summary["copied"] += 1
    return summary


def pre_existing_entries(source, target, source_top):
    """Names already in target that are not part of the kit or the download."""
    kit_names = set()
    for child in source.iterdir():
        if child.name in SKIP_DIRS:
            continue
        kit_names.add(child.name)
    entries = []
    for child in sorted(target.iterdir(), key=lambda item: item.name.lower()):
        if child.name in kit_names or child.name in NOISE_NAMES:
            continue
        if child.name in (".git", BACKUP_DIR):
            continue
        if source_top is not None and child == source_top:
            continue
        entries.append(child.name + ("/" if child.is_dir() else ""))
    return entries


def install_dependency(requirements):
    """Install the kit's Python dependency; return (ok, message)."""
    base = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(requirements)]
    attempts = [base, base[:5] + ["--user"] + base[5:]]
    last = ""
    for command in attempts:
        try:
            completed = subprocess.run(
                command, text=True, capture_output=True, timeout=600, check=False
            )
        except (OSError, subprocess.SubprocessError) as exc:
            last = str(exc)
            continue
        if completed.returncode == 0:
            return True, "jsonschema is installed"
        last = (completed.stderr or completed.stdout or "").strip().splitlines()
        last = "\n".join(last[-8:])
    advice = (
        "pip could not install the dependency. Common fixes: check the internet connection; "
        "or create a private environment with\n"
        "    " + sys.executable + " -m venv .venv\n"
        "and then run the kit's scripts with .venv/bin/python (macOS/Linux) or "
        ".venv\\Scripts\\python (Windows), starting with\n"
        "    <that python> -m pip install -r requirements.txt\n"
        "    <that python> scripts/doctor.py"
    )
    return False, "pip failed:\n" + last + "\n" + advice


def run_doctor(target):
    """Run scripts/doctor.py --json in target; return (ok, hard_failures, notes)."""
    doctor = target / "scripts" / "doctor.py"
    if not doctor.is_file():
        return False, ["scripts/doctor.py is missing from " + str(target)], []
    try:
        completed = subprocess.run(
            [sys.executable, str(doctor), "--json", "--platform", "auto"],
            cwd=str(target),
            text=True,
            capture_output=True,
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, ["could not run scripts/doctor.py: " + str(exc)], []
    try:
        report = json.loads(completed.stdout)
    except ValueError:
        text = (completed.stderr or completed.stdout or "").strip()
        return False, ["scripts/doctor.py did not produce a report:\n" + text[-2000:]], []
    hard = []
    notes = []
    for failure in report.get("failures", []):
        if str(failure).startswith(HOST_NOT_DETECTED):
            notes.append(
                "no Claude Code or Codex command was found on PATH from this Python; if you "
                "are running inside one of them that is fine (Stage 00 checks again)"
            )
        else:
            hard.append(str(failure))
    hosts = report.get("hosts", {})
    for key in ("claude", "codex"):
        host = hosts.get(key) or {}
        if host.get("installed") and host.get("version"):
            notes.append(host.get("name", key) + " " + host["version"] + " detected")
    return not hard, hard, notes


def source_top_level(source, target):
    """Return the entry directly under target that contains source, or None."""
    try:
        relative = source.relative_to(target)
    except ValueError:
        return None
    if not relative.parts:
        return None
    return target / relative.parts[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", type=Path, default=None, help="folder to install into (default: current folder)")
    parser.add_argument("--overwrite", action="store_true", help="replace differing kit files, keeping backups; never touches project/")
    parser.add_argument("--skip-install", action="store_true", help="do not run pip")
    parser.add_argument("--skip-doctor", action="store_true", help="do not run scripts/doctor.py")
    parser.add_argument("--keep-source", action="store_true", help="leave the downloaded copy in place")
    args = parser.parse_args()

    source = Path(__file__).resolve().parents[1]
    target = (args.target or Path.cwd()).resolve()
    if not (source / "workflow" / "stages").is_dir() or not (source / "AGENTS.md").is_file():
        print("ERROR: " + str(source) + " does not look like a downloaded ELARA kit.")
        return 2
    if target != source and target.is_relative_to(source):
        print("ERROR: the target folder must not be inside the downloaded kit. Run this from the folder you want to work in.")
        return 2
    target.mkdir(parents=True, exist_ok=True)

    print("ELARA install")
    print("  from: " + str(source))
    print("  into: " + str(target))
    if _cloud_synced(target):
        print(
            "WARNING: this folder looks cloud-synced (Google Drive, OneDrive, Dropbox, or iCloud). "
            "ELARA works here, but sync services can corrupt append-only logs mid-write and copy "
            "restricted material to the cloud. A local folder is safer; if you stay here, decline "
            "Stage 00's offer to start Git change tracking."
        )

    exit_code = 0
    source_top = None
    if source == target:
        print("COPY: the kit is already in place (this folder is the download); nothing to copy.")
        already_initialized = False
    else:
        source_top = source_top_level(source, target)
        state = target / "project" / "PROJECT_STATE.md"
        already_initialized = state.is_file() and not _same_bytes(state, source / "project" / "PROJECT_STATE.md")
        existing = pre_existing_entries(source, target, source_top)
        summary = copy_kit(source, target, overwrite=args.overwrite)
        print(
            "COPY: copied "
            + str(summary["copied"])
            + " file(s); already present "
            + str(summary["already_present"])
            + "; kept your project/ files "
            + str(summary["kept_project_files"])
            + "; replaced "
            + str(len(summary["replaced"]))
            + "; conflicts "
            + str(len(summary["conflicts"]))
        )
        if summary["replaced"]:
            print("REPLACED (backups under " + str(summary["backup_dir"]) + "):")
            for item in summary["replaced"]:
                print("  - " + item)
        if summary["conflicts"]:
            print("CONFLICT: these files already exist here and differ from the kit's; they were left as they are:")
            for item in summary["conflicts"]:
                marker = "  (needed by ELARA)" if item in summary["essential_conflicts"] else ""
                print("  - " + item + marker)
            if summary["essential_conflicts"]:
                exit_code = 1
                print(
                    "  ELARA needs its own copy of the file(s) marked above. Either rerun with "
                    "--overwrite (each replaced file is backed up under " + BACKUP_DIR + "/), "
                    "or merge by hand: for CLAUDE.md, make '@AGENTS.md' its first line and append "
                    "the kit's CLAUDE.md; for AGENTS.md, keep the kit's text and add yours below it."
                )
            else:
                print("  None of them is needed by ELARA; nothing to do unless you want the kit's version.")
        if already_initialized:
            print("KEPT: an initialized ELARA project already lives in project/; its state, ledgers, and artifacts were not touched.")
        if existing:
            shown = existing[:8]
            more = "" if len(existing) <= 8 else " ... (" + str(len(existing)) + " in total)"
            print(
                "EXISTING: this folder already held "
                + str(len(existing))
                + " item(s) that are not part of ELARA: "
                + ", ".join(shown)
                + more
            )
            print(
                "  Nothing was moved or changed. Stage 00 offers to copy what is relevant into "
                "project/inputs/ (or project/inputs/existing/ for work already done)."
            )
        if (target / ".git").is_dir():
            print("NOTE: this folder is already a Git repository; Stage 00 will not offer to create one.")

    if args.skip_install:
        print("PIP: skipped")
    else:
        ok, message = install_dependency(source / "requirements.txt")
        print("PIP: " + message)
        if not ok:
            exit_code = 1

    if args.skip_doctor:
        print("DOCTOR: skipped")
    else:
        ok, hard, notes = run_doctor(target)
        for note in notes:
            print("DOCTOR: note: " + note)
        if ok:
            print("DOCTOR: PASS (Python, dependency, kit files, and the offline fan-out check are ready)")
        else:
            exit_code = 1
            print("DOCTOR: FAIL")
            for failure in hard:
                print("  - " + failure)
            print("  Fix the problems above, then run: python scripts/doctor.py")

    if source != target and source_top is not None:
        if args.keep_source:
            print("SOURCE: kept " + str(source_top))
        elif source_top.name.startswith(".elara"):
            try:
                _rmtree(source_top)
                print("SOURCE: removed the temporary download " + source_top.name)
            except OSError as exc:
                print("SOURCE: could not remove " + str(source_top) + " (" + str(exc) + "); delete it by hand, it is no longer needed")
        else:
            print("SOURCE: the download at " + str(source_top) + " is no longer needed; delete it when convenient")
    elif source != target:
        print("SOURCE: the download at " + str(source) + " is no longer needed; delete it when convenient")

    if exit_code == 0:
        print("RESULT: ELARA is installed in " + str(target))
    else:
        print("RESULT: installation needs attention (see the lines marked CONFLICT, PIP, or DOCTOR above)")
    print("NEXT: read START_HERE.md in " + str(target) + " and follow it.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
