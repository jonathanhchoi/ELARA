"""Install ELARA into the folder you are working in and check that it is ready.

An assistant such as Claude Code or Codex normally runs this for the researcher:

    python bootstrap.py                 # install ELARA into the current folder
    python bootstrap.py --into PATH     # install it somewhere else
    python scripts/bootstrap.py         # inside a downloaded kit: check this copy

The script copies the kit into the target folder without overwriting anything
that is already there, merges the few files that must be shared (.gitignore,
requirements.txt, and any AGENTS.md or CLAUDE.md the folder already has),
installs the kit's one Python dependency, runs scripts/doctor.py, writes
project/BOOTSTRAP.md (the report) and project/ELARA_MANIFEST.json (which
files are the kit's, which are shared, and which were the researcher's before
the kit arrived), removes a temporary `.elara-kit` copy it was run from, and
prints what the assistant should do next. `--dry-run` shows the whole plan
without writing, installing, or removing anything. It needs only the Python
standard library. When it is run from inside a kit copy it installs from that
copy; otherwise it downloads the kit from GitHub.

Like scripts/doctor.py, this file avoids newer Python syntax (no f-strings, no
modern type annotations) so that an old interpreter can still parse it far
enough to print the version advice below instead of a confusing SyntaxError.
"""

import sys

if sys.version_info < (3, 10):
    sys.stderr.write(
        "ELARA needs Python 3.10 or newer; you are running Python "
        + ".".join(str(part) for part in sys.version_info[:3])
        + ".\n"
        "Please install a current Python from https://www.python.org/downloads/\n"
        "Windows users: if you have several Pythons installed, try the 'py'\n"
        "launcher, for example: py bootstrap.py\n"
    )
    sys.exit(1)

import argparse  # noqa: E402
import datetime  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import platform  # noqa: E402
import shutil  # noqa: E402
import stat  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402
from urllib.error import URLError  # noqa: E402
from urllib.request import Request, urlopen  # noqa: E402


REPOSITORY = "jonathanhchoi/ELARA"
DEFAULT_REF = "main"
ARCHIVE_URLS = (
    "https://github.com/%s/archive/refs/heads/%s.zip",
    "https://github.com/%s/archive/refs/tags/%s.zip",
)
KIT_TITLE = "# ELARA: Empirical Legal Analysis with Research Agents"
REPORT_RELATIVE = "project/BOOTSTRAP.md"
MANIFEST_RELATIVE = "project/ELARA_MANIFEST.json"
MANIFEST_SCHEMA_VERSION = "1.0"
LOOSE_SCRIPT_NAMES = ("bootstrap.py", "elara_bootstrap.py")

# Stop counting a pre-existing folder's files past this many; the report then
# says "more than" rather than printing the cap as if it were exact.
FOLDER_COUNT_CAP = 5000
# At most this many of the researcher's files are listed by name for a folder
# the kit also uses (the rest are counted); the manifest is not a file index.
SHARED_FOLDER_LIST_CAP = 500
# Folders whose contents the kit governs by contract rather than by ownership
# (stages write there); they are not listed in the shared-folder breakdown.
SHARED_FOLDER_SKIP = {"project"}
# Kit files ELARA needs in order to run at all. A file of the researcher's at one
# of these paths is left alone, and the report says ELARA is incomplete here.
ESSENTIAL_PREFIXES = ("scripts/", "workflow/", ".agents/", ".claude/", ".codex/")
ESSENTIAL_FILES = {"PIPELINE.md"}

# Never copied into a project folder.
EXCLUDED_DIRECTORIES = {".git", "__pycache__", ".pytest_cache", ".github", ".venv", "build"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_NAMES = {".DS_Store", "Thumbs.db", "Desktop.ini", "desktop.ini", "settings.local.json"}
EXCLUDED_PREFIXES = ("tests/tmp/", "tests/.tmp/")

# Under project/, only the blank templates travel. Anything else there belongs
# to whatever project the source copy was used for and must never be copied.
PROJECT_TEMPLATE_FILES = {
    "project/README.md",
    "project/inputs/README.md",
    "project/PROJECT_STATE.md",
    "project/DECISIONS.md",
    "project/RUN_LEDGER.md",
    "project/DEVIATIONS.md",
}

# Files that belong to the researcher once they exist. Never overwritten, even
# with --update; a new kit version of them is not installed alongside either.
PROJECT_OWNED = {
    "project/PROJECT_STATE.md",
    "project/DECISIONS.md",
    "project/RUN_LEDGER.md",
    "project/DEVIATIONS.md",
}
# The kit's README and license are installed under these names in a project
# folder, so that README.md and LICENSE there stay the researcher's (or free for
# their own use: a replication package wants a README of its own). A kit README
# that an earlier version installed as plain README.md is refreshed in place.
ALIASES = {"README.md": "ELARA_README.md", "LICENSE": "LICENSE.ELARA"}
MERGED = {".gitignore", "requirements.txt"}

MARK_BEGIN = "<!-- elara:begin (installed by scripts/bootstrap.py; keep this block first) -->"
MARK_END = "<!-- elara:end -->"
LINE_MARK_BEGIN = "# >>> ELARA (added by scripts/bootstrap.py) >>>"
LINE_MARK_END = "# <<< ELARA <<<"

# A path component that starts with one of these names marks a folder that a
# sync service manages ("OneDrive - University", "My Drive", "Dropbox (Personal)",
# "GoogleDrive-name@example.org", "Mobile Documents", macOS "CloudStorage").
CLOUD_SYNC_HINTS = (
    ("onedrive", "OneDrive"),
    ("google drive", "Google Drive"),
    ("googledrive", "Google Drive"),
    ("my drive", "Google Drive"),
    ("dropbox", "Dropbox"),
    ("icloud", "iCloud"),
    ("mobile documents", "iCloud"),
    ("box sync", "Box"),
    ("cloudstorage", "a cloud storage service"),
)
# Windows records where OneDrive lives; a folder under it is synced whatever it is called.
ONEDRIVE_VARIABLES = ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")


class BootstrapError(Exception):
    """A problem the researcher or assistant must resolve; explained in plain words."""


# --------------------------------------------------------------------------- helpers


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _force_writable(function, path, _excinfo):
    # Git checkouts contain read-only pack files, which shutil.rmtree cannot
    # delete on Windows without clearing the flag first.
    os.chmod(path, stat.S_IWRITE)
    function(path)


def remove_tree(path):
    """Delete a directory tree, including read-only files; return True on success."""
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_force_writable)
        else:
            shutil.rmtree(path, onerror=_force_writable)
    except OSError:
        return False
    return not Path(path).exists()


def is_temporary_kit_name(name):
    """A kit copy cloned or unzipped just to install from, by the README's convention."""
    return str(name).startswith(".elara")


def is_kit_root(path):
    path = Path(path)
    return (
        (path / "AGENTS.md").is_file()
        and (path / "workflow" / "stages").is_dir()
        and (path / "scripts" / "doctor.py").is_file()
        and (path / "project").is_dir()
    )


def read_text(path):
    return Path(path).read_text(encoding="utf-8-sig")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def own_kit_root():
    """Return the kit root that contains this script, if it is inside a kit."""
    try:
        here = Path(__file__).resolve()
    except NameError:  # run from stdin
        return None
    candidate = here.parent.parent
    if here.parent.name == "scripts" and is_kit_root(candidate):
        return candidate
    return None


def loose_script_path():
    """Return this script's path when it is a loose downloaded copy, else None."""
    try:
        here = Path(__file__).resolve()
    except NameError:
        return None
    if here.parent.name == "scripts" and is_kit_root(here.parent.parent):
        return None
    if here.name in LOOSE_SCRIPT_NAMES:
        return here
    return None


def kit_files(source):
    """Yield (relative_posix_path, absolute_path) for every installable kit file."""
    source = Path(source)
    for directory, subdirectories, filenames in os.walk(str(source)):
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in EXCLUDED_DIRECTORIES
        )
        for filename in sorted(filenames):
            if filename in EXCLUDED_NAMES:
                continue
            absolute = Path(directory) / filename
            if absolute.suffix in EXCLUDED_SUFFIXES:
                continue
            relative = absolute.relative_to(source).as_posix()
            if relative == REPORT_RELATIVE or relative.startswith(EXCLUDED_PREFIXES):
                continue
            if relative.startswith("project/") and relative not in PROJECT_TEMPLATE_FILES:
                continue
            yield relative, absolute


def state_field(root, field):
    """Return a top-level scalar from PROJECT_STATE.md front matter, unquoted, or None."""
    state = Path(root) / "project" / "PROJECT_STATE.md"
    if not state.is_file():
        return None
    for line in read_text(state).splitlines():
        if line.startswith(field + ":"):
            return line.split(":", 1)[1].strip().strip('"')
    return None


def kit_version(root):
    """Return workflow_version from the kit's PROJECT_STATE.md template, if readable."""
    return state_field(root, "workflow_version")


def source_is_clean_template(root):
    """A kit copy is a valid source only while its project state is the blank template."""
    expected = {
        "project_slug": "null",
        "current_stage": "00-initialize",
        "status": "ready",
        "active_artifacts": "{}",
        "approvals": "{}",
        "outstanding_user_inputs": "[]",
        "last_run_id": "null",
        "updated_at": "null",
    }
    return all(state_field(root, field) == value for field, value in expected.items())


def git_commit(root):
    if not (Path(root) / ".git").exists() or not shutil.which("git"):
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def is_kit_agents(text):
    return text.lstrip().startswith(KIT_TITLE)


def is_kit_claude(text):
    return text.startswith("@AGENTS.md") and "Claude Code adapter" in text and MARK_BEGIN not in text


def is_kit_readme(text):
    return text.lstrip().startswith(KIT_TITLE)


# --------------------------------------------------------------------------- source


def download_kit(ref, workdir):
    """Fetch the kit for ``ref`` from GitHub; return (kit_root, source description).

    Tries, in order: the public archive URL; the same archive with a GitHub token
    from GH_TOKEN or GITHUB_TOKEN (private repositories); a shallow ``git clone``
    using whatever credentials Git already has; and the ``gh`` CLI. The first
    route that yields a kit wins.
    """
    errors = []
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    for template in ARCHIVE_URLS:
        url = template % (REPOSITORY, ref)
        for use_token in (False, True):
            if use_token and not token:
                continue
            headers = {"User-Agent": "elara-bootstrap"}
            if use_token:
                headers["Authorization"] = "Bearer " + token
            try:
                request = Request(url, headers=headers)
                with urlopen(request, timeout=120) as response:
                    payload = response.read()
            except (URLError, OSError, ValueError) as exc:
                errors.append(url + (" (with token)" if use_token else "") + " -> " + str(exc))
                continue
            root = extract_archive(io.BytesIO(payload), workdir)
            return root, {"kind": "download", "location": url, "ref": ref}
    if shutil.which("git"):
        clone_dir = Path(workdir) / "clone"
        environment = dict(os.environ)
        environment["GIT_TERMINAL_PROMPT"] = "0"
        command = [
            "git", "clone", "--quiet", "--depth", "1", "--branch", ref,
            "https://github.com/" + REPOSITORY + ".git", str(clone_dir),
        ]
        try:
            completed = subprocess.run(
                command, text=True, capture_output=True, timeout=600, check=False, env=environment
            )
        except (OSError, subprocess.SubprocessError) as exc:
            completed = None
            errors.append("git clone -> " + str(exc))
        if completed is not None and completed.returncode == 0 and is_kit_root(clone_dir):
            return clone_dir, {
                "kind": "git clone",
                "location": "https://github.com/" + REPOSITORY + ".git",
                "ref": ref,
                "commit": git_commit(clone_dir),
            }
        if completed is not None:
            errors.append("git clone -> " + (completed.stderr or completed.stdout or "failed").strip()[-400:])
    else:
        errors.append("git clone -> git is not installed")
    if shutil.which("gh"):
        command = ["gh", "api", "repos/" + REPOSITORY + "/zipball/" + ref]
        try:
            completed = subprocess.run(command, capture_output=True, timeout=600, check=False)
        except (OSError, subprocess.SubprocessError) as exc:
            completed = None
            errors.append("gh api zipball -> " + str(exc))
        if completed is not None and completed.returncode == 0 and completed.stdout:
            try:
                root = extract_archive(io.BytesIO(completed.stdout), workdir)
                return root, {"kind": "download (gh)", "location": " ".join(command), "ref": ref}
            except BootstrapError as exc:
                errors.append("gh api zipball -> " + str(exc))
        elif completed is not None:
            errors.append("gh api zipball -> " + completed.stderr.decode("utf-8", "replace").strip()[-400:])
    raise BootstrapError(
        "Could not fetch ELARA from GitHub.\n  Tried:\n    "
        + "\n    ".join(errors)
        + "\n  Check the internet connection, or download the kit by hand from\n  "
        + "https://github.com/" + REPOSITORY
        + " (Code > Download ZIP), unzip it, and run\n  "
        + "python <unzipped-folder>/scripts/bootstrap.py --into <your project folder>"
    )


def extract_archive(archive, workdir):
    """Extract a kit ZIP (GitHub archive or hand-made) and return its kit root."""
    extract_root = Path(workdir) / "extracted"
    extract_root.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise BootstrapError("The kit archive contains an unsafe path: " + member.filename)
            bundle.extractall(str(extract_root))
    except zipfile.BadZipFile as exc:
        raise BootstrapError("The kit archive is not a valid ZIP file: " + str(exc))
    if is_kit_root(extract_root):
        return extract_root
    for candidate in sorted(extract_root.iterdir()):
        if candidate.is_dir() and is_kit_root(candidate):
            return candidate
    raise BootstrapError(
        "The archive did not contain an ELARA kit (no AGENTS.md next to workflow/stages/)."
    )


def resolve_source(args, workdir):
    """Return (kit_root, description dict) for the kit to install from."""
    if args.source:
        source = Path(args.source).expanduser().resolve()
        if source.is_file():
            root = extract_archive(str(source), workdir)
            return root, {"kind": "archive", "location": str(source)}
        if is_kit_root(source):
            check_clean_source(source)
            return source, {
                "kind": "local copy",
                "location": str(source),
                "commit": git_commit(source),
            }
        raise BootstrapError("--source is neither a kit folder nor a ZIP archive: " + str(source))
    own = own_kit_root()
    if own is not None and not args.update:
        # --update always fetches a fresh kit: the copy this script sits in is
        # usually the installed project itself.
        check_clean_source(own)
        return own, {"kind": "local copy", "location": str(own), "commit": git_commit(own)}
    return download_kit(args.ref, workdir)


def check_clean_source(root):
    if not source_is_clean_template(root):
        raise BootstrapError(
            "The kit copy at " + str(root) + " already holds an initialized project, so it cannot be "
            "used as an installation source (that would copy one project's state into another). "
            "Install from a clean copy instead: run this script without --source to download one, "
            "or download the kit ZIP from https://github.com/" + REPOSITORY + "."
        )


# --------------------------------------------------------------------------- planning


def merge_line_file(existing_text, kit_text):
    """Return existing_text with the kit's non-comment lines it lacks appended in a marked block."""
    present = set(line.strip() for line in existing_text.splitlines())
    kit_text = kit_text.lstrip("\ufeff")
    missing = [
        line
        for line in kit_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and line.strip() not in present
    ]
    if not missing:
        return existing_text, []
    return append_marked_lines(existing_text, missing), missing


def append_marked_lines(existing_text, lines):
    """Add lines inside the existing ELARA block if there is one, else append a new block."""
    if LINE_MARK_BEGIN in existing_text and LINE_MARK_END in existing_text:
        head, tail = existing_text.rsplit(LINE_MARK_END, 1)
        if head and not head.endswith("\n"):
            head += "\n"
        return head + "\n".join(lines) + "\n" + LINE_MARK_END + tail
    body = existing_text
    if body and not body.endswith("\n"):
        body += "\n"
    return body + "\n" + LINE_MARK_BEGIN + "\n" + "\n".join(lines) + "\n" + LINE_MARK_END + "\n"


def merge_requirements(existing_text, kit_text):
    """Like merge_line_file, but a package already pinned by the researcher is not re-added."""

    def package_name(line):
        name = line.strip()
        for separator in ("<", ">", "=", "!", "~", ";", "[", " ", "#"):
            name = name.split(separator, 1)[0]
        return name.lower()

    present = set(package_name(line) for line in existing_text.splitlines() if line.strip())
    kept = []
    for line in kit_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if package_name(line) in present:
            continue
        kept.append(line)
    if not kept:
        return existing_text, []
    return append_marked_lines(existing_text, kept), kept


def marked_block(text):
    return "\n".join([MARK_BEGIN, text.rstrip("\n"), MARK_END]) + "\n"


def merge_agents(existing_text, kit_text, update):
    """Put the kit constitution first in a researcher's AGENTS.md; keep their text after it."""
    if MARK_BEGIN in existing_text and MARK_END in existing_text:
        if not update:
            return existing_text, "already merged"
        head, rest = existing_text.split(MARK_BEGIN, 1)
        _old, tail = rest.split(MARK_END, 1)
        refreshed = head + marked_block(kit_text) + tail
        if refreshed == existing_text:
            return existing_text, "already merged"
        return refreshed, "updated merged block"
    body = existing_text
    if body and not body.startswith("\n"):
        body = "\n" + body
    return marked_block(kit_text) + body, "merged"


def merge_claude(existing_text, kit_text, update):
    """Keep ``@AGENTS.md`` as the first line of a researcher's CLAUDE.md, then the kit adapter."""
    lines = kit_text.lstrip("\ufeff").splitlines()
    first = lines[0] if lines else "@AGENTS.md"
    adapter = "\n".join(lines[1:]).strip("\n")
    kit_block = first + "\n" + marked_block(adapter)
    if MARK_BEGIN in existing_text and MARK_END in existing_text:
        if not update:
            return existing_text, "already merged"
        _head, rest = existing_text.split(MARK_BEGIN, 1)
        _old, tail = rest.split(MARK_END, 1)
        refreshed = kit_block + tail
        if refreshed == existing_text:
            return existing_text, "already merged"
        return refreshed, "updated merged block"
    body = existing_text
    if body.startswith("@AGENTS.md"):
        body = body[len("@AGENTS.md"):]
    if body and not body.startswith("\n"):
        body = "\n" + body
    return kit_block + body, "merged"


def snapshot_existing(target, ignore_names):
    """List what the folder held before installation, so Stage 00 can offer adoption."""
    target = Path(target)
    if not target.exists():
        return []
    entries = []
    for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        name = entry.name
        if name in ignore_names or name in EXCLUDED_NAMES or name in (".git", ".venv", "__pycache__"):
            continue
        record = {"name": name, "kind": "folder" if entry.is_dir() else "file"}
        if entry.is_dir():
            count = 0
            truncated = False
            for _directory, subdirectories, filenames in os.walk(str(entry)):
                subdirectories[:] = [
                    sub for sub in subdirectories if sub not in EXCLUDED_DIRECTORIES
                ]
                count += len(filenames)
                if count > FOLDER_COUNT_CAP:
                    truncated = True
                    break
            record["files"] = FOLDER_COUNT_CAP if truncated else count
            record["files_truncated"] = truncated
        else:
            try:
                record["bytes"] = entry.stat().st_size
            except OSError:
                record["bytes"] = None
        entries.append(record)
    return entries


def kit_top_level(source):
    """The top-level folder and file names the kit installs (e.g. scripts, workflow, AGENTS.md)."""
    return set(relative.split("/", 1)[0] for relative, _absolute in kit_files(source))


def shared_folder_snapshot(target, kit_top, ignore_names):
    """List the files already inside each top-level folder the kit also uses.

    Returns {folder name: {"files": [relative POSIX paths], "truncated": bool}} for
    every folder of the target that shares its name with a kit folder (scripts/,
    tests/, .claude/, ...). Taken before installation, so the report and the
    manifest can say by name which files in such a folder are the researcher's.
    """
    target = Path(target)
    if not target.exists():
        return {}
    shared = {}
    for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        name = entry.name
        if not entry.is_dir() or name in ignore_names or name in SHARED_FOLDER_SKIP:
            continue
        if name not in kit_top:
            continue
        files = []
        truncated = False
        for directory, subdirectories, filenames in os.walk(str(entry)):
            subdirectories[:] = sorted(
                sub for sub in subdirectories if sub not in EXCLUDED_DIRECTORIES
            )
            for filename in sorted(filenames):
                if len(files) >= SHARED_FOLDER_LIST_CAP:
                    truncated = True
                    break
                files.append((Path(directory) / filename).relative_to(target).as_posix())
            if truncated:
                break
        shared[name] = {"files": files, "truncated": truncated}
    return shared


def describe_shared_folders(shared_before, files):
    """Split each shared folder's contents into the researcher's files and the kit's."""
    kit_owned = set(files["kit_paths"]) | set(files["shared_paths"]) | set(files["project_paths"])
    kit_owned.update((REPORT_RELATIVE, MANIFEST_RELATIVE))
    described = []
    for folder in sorted(shared_before):
        record = shared_before[folder]
        yours = [path for path in record["files"] if path not in kit_owned]
        prefix = folder + "/"
        described.append({
            "folder": folder,
            "yours": yours,
            "yours_truncated": bool(record["truncated"]),
            "kit_files": sum(1 for path in files["kit_paths"] if path.startswith(prefix)),
        })
    return described


def essential_conflicts(researcher_paths):
    """The researcher's files that sit exactly where ELARA keeps a file it needs to run."""
    return sorted(
        path for path in set(researcher_paths)
        if path in ESSENTIAL_FILES or path.startswith(ESSENTIAL_PREFIXES)
    )


def essential_conflict_warning(conflicts):
    return (
        "These files of yours sit exactly where ELARA keeps files it needs in order to run: "
        + ", ".join(conflicts)
        + ". They were left untouched and ELARA's own copies were not installed, so ELARA is "
        "incomplete in this folder. The clean fix is to install ELARA into a different folder "
        "(a new, empty one is simplest) and let Stage 00 import your materials from here by "
        "path; nothing of yours has to move. Alternatively, rename those files yourself and run "
        "the installer again."
    )


def read_manifest(target):
    """Return the manifest the previous bootstrap run wrote, or None if there is none."""
    path = Path(target) / MANIFEST_RELATIVE
    if not path.is_file():
        return None
    try:
        manifest = json.loads(read_text(path))
    except (ValueError, OSError):
        return None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("kit_paths"), list):
        return None
    return manifest


def build_manifest(summary):
    """The ownership record: which files in the folder are the kit's, shared, or the researcher's."""
    files = summary["files"]
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "written": summary["timestamp"],
        "kit_version": summary.get("kit_version"),
        "kit_source": summary["source"],
        "kit_paths": sorted(set(files["kit_paths"])),
        "shared_paths": sorted(set(files["shared_paths"])),
        "project_paths": sorted(set(files["project_paths"])),
        "researcher_paths": sorted(set(files["researcher_paths"])),
        "researcher_files_in_kit_folders": {
            record["folder"]: record["yours"] for record in summary.get("shared_folders") or []
        },
        "note": (
            "Written by scripts/bootstrap.py on every run. kit_paths are ELARA's own files "
            "(refreshed only by --update). shared_paths hold the kit's lines and the researcher's "
            "(.gitignore, requirements.txt, a merged AGENTS.md or CLAUDE.md). project_paths are "
            "state and ledgers the project fills in. researcher_paths are the researcher's files "
            "that sit where a kit file would go; they are never replaced, not even by --update. "
            "Any other file in this folder is not the kit's."
        ),
    }


def empty_outcome(researcher_paths=()):
    return {
        "installed": [],
        "unchanged": [],
        "kept": [],
        "aliased": [],
        "merged": [],
        "updated": [],
        "prepended": [],
        # Where every kit file ended up, by installed name (see build_manifest).
        "kit_paths": [],
        "shared_paths": [],
        "project_paths": [],
        "researcher_paths": sorted(set(researcher_paths)),
    }


def install(source, target, update, already_installed=False, researcher_paths=(), dry_run=False):
    """Copy the kit into target. Returns the per-file outcome lists.

    Besides the outcome lists, the result records ownership: ``kit_paths`` are
    the kit's own files by installed name, ``shared_paths`` hold both the kit's
    lines and the researcher's, ``project_paths`` are the state and ledgers the
    project fills in, and ``researcher_paths`` are files of the researcher's
    that sit where a kit file would go. Those last are never replaced, not even
    by --update: on a first install into a folder that is not yet a kit copy,
    whatever already sits at a kit path is the researcher's, and the previous
    manifest carries that knowledge into later runs. With ``dry_run`` nothing
    is written; the lists describe what a real run would do.
    """
    source = Path(source)
    target = Path(target)
    outcome = empty_outcome(researcher_paths)
    theirs = set(researcher_paths)

    def put(destination, data):
        if dry_run:
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    def put_text(destination, text):
        if not dry_run:
            write_text(destination, text)

    def owned(relative, kind="kit"):
        outcome[kind + "_paths"].append(relative)

    def keep_researcher_file(relative):
        theirs.add(relative)
        outcome["researcher_paths"] = sorted(theirs)
        outcome["kept"].append(
            relative + " (yours: it was here before the kit; the kit's version of this file "
            "is not installed, and --update will not touch it)"
        )

    for relative, absolute in kit_files(source):
        destination = target / relative
        kit_bytes = absolute.read_bytes()
        if relative in theirs and destination.exists():
            keep_researcher_file(relative)
            continue
        if relative in ALIASES:
            # The kit README and license live under their kit names in a project
            # folder; README.md and LICENSE there are the researcher's to use.
            alias_relative = ALIASES[relative]
            alias = target / alias_relative
            if alias.exists():
                if alias.read_bytes() == kit_bytes:
                    outcome["unchanged"].append(alias_relative)
                elif update:
                    put(alias, kit_bytes)
                    outcome["updated"].append(alias_relative)
                else:
                    outcome["kept"].append(alias_relative + " (differs from this kit version; --update refreshes it)")
                owned(alias_relative)
                continue
            if destination.exists():
                existing_bytes = destination.read_bytes()
                legacy_kit_file = existing_bytes == kit_bytes or (
                    relative == "README.md"
                    and is_kit_readme(existing_bytes.decode("utf-8", errors="replace"))
                )
                if legacy_kit_file:
                    # An earlier kit version installed this file under its plain
                    # name; keep that location rather than leaving two copies.
                    if existing_bytes == kit_bytes:
                        outcome["unchanged"].append(relative + " (this kit file, where an earlier kit version put it)")
                    elif update:
                        put(destination, kit_bytes)
                        outcome["updated"].append(relative)
                    else:
                        outcome["kept"].append(relative + " (an earlier kit version; --update refreshes it)")
                    owned(relative)
                    continue
                put(alias, kit_bytes)
                outcome["aliased"].append(relative + " -> " + alias_relative + " (your " + relative + " was left alone)")
                owned(alias_relative)
                continue
            put(alias, kit_bytes)
            outcome["installed"].append(alias_relative)
            owned(alias_relative)
            continue
        if not destination.exists():
            put(destination, kit_bytes)
            outcome["installed"].append(relative)
            owned(relative, "project" if relative in PROJECT_OWNED else "kit")
            continue
        existing_bytes = destination.read_bytes()
        if existing_bytes == kit_bytes:
            outcome["unchanged"].append(relative)
            owned(relative, "project" if relative in PROJECT_OWNED else "kit")
            continue
        if relative in PROJECT_OWNED:
            outcome["kept"].append(relative + " (project state or ledger; never replaced)")
            owned(relative, "project")
            continue
        if relative in MERGED:
            existing_text = existing_bytes.decode("utf-8", errors="replace")
            kit_text = kit_bytes.decode("utf-8", errors="replace")
            if relative == "requirements.txt":
                merged_text, added = merge_requirements(existing_text, kit_text)
            else:
                merged_text, added = merge_line_file(existing_text, kit_text)
            if added:
                put_text(destination, merged_text)
                outcome["merged"].append(relative + " (+" + str(len(added)) + " line(s))")
            else:
                outcome["unchanged"].append(relative + " (already contains the kit's lines)")
            owned(relative, "shared")
            continue
        existing_text = existing_bytes.decode("utf-8", errors="replace")
        kit_text = kit_bytes.decode("utf-8", errors="replace")
        if relative == "AGENTS.md":
            if is_kit_agents(existing_text):
                if update:
                    put(destination, kit_bytes)
                    outcome["updated"].append(relative)
                else:
                    outcome["kept"].append(relative + " (an earlier kit version; --update refreshes it)")
                owned(relative)
                continue
            merged_text, how = merge_agents(existing_text, kit_text, update)
            if how == "already merged":
                outcome["unchanged"].append(relative + " (kit constitution already merged)")
            else:
                put_text(destination, merged_text)
                outcome["prepended"].append(relative + " (" + how + "; your text follows the ELARA block)")
            owned(relative, "shared")
            continue
        if relative == "CLAUDE.md":
            if is_kit_claude(existing_text):
                if update:
                    put(destination, kit_bytes)
                    outcome["updated"].append(relative)
                else:
                    outcome["kept"].append(relative + " (an earlier kit version; --update refreshes it)")
                owned(relative)
                continue
            merged_text, how = merge_claude(existing_text, kit_text, update)
            if how == "already merged":
                outcome["unchanged"].append(relative + " (kit adapter already merged)")
            else:
                put_text(destination, merged_text)
                outcome["prepended"].append(relative + " (" + how + "; your text follows the ELARA block)")
            owned(relative, "shared")
            continue
        # Every other kit-owned file (workflow/, scripts/, tests/, .agents/, .claude/,
        # PIPELINE.md, project READMEs, ...): refreshed only with --update.
        if not already_installed:
            # First install into a folder that is not a kit copy: whatever already
            # sits at this path is the researcher's, not an older kit file.
            keep_researcher_file(relative)
            continue
        if update:
            put(destination, kit_bytes)
            outcome["updated"].append(relative)
        else:
            outcome["kept"].append(relative + " (differs from this kit version; --update refreshes it)")
        owned(relative)
    return outcome


# --------------------------------------------------------------------------- environment


def run_command(command, timeout):
    try:
        completed = subprocess.run(
            command, text=True, capture_output=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"command": command, "returncode": None, "stdout": "", "stderr": str(exc)}
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
    }


def can_import(python, module):
    result = run_command([python, "-c", "import " + module], timeout=120)
    return result["returncode"] == 0


def venv_python(venv_dir):
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def ensure_dependency(target, python, no_install):
    """Make jsonschema importable; return a record naming the interpreter to use."""
    if can_import(python, "jsonschema"):
        return {"status": "present", "python": python, "attempts": []}
    if no_install:
        return {
            "status": "missing",
            "python": python,
            "attempts": [],
            "advice": python + " -m pip install -r requirements.txt",
        }
    requirements = str(Path(target) / "requirements.txt")
    attempts = []
    # Say what is about to happen before it happens (stderr keeps --json output clean).
    sys.stderr.write(
        "Installing the kit's one Python dependency (jsonschema) with " + python
        + "; if that is not allowed here, a virtual environment .venv is tried next.\n"
    )
    base = [python, "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", requirements]
    for extra in ([], ["--user"]):
        result = run_command(base + extra, timeout=900)
        attempts.append(
            {"command": " ".join(base + extra), "returncode": result["returncode"], "stderr": result["stderr"][-1500:]}
        )
        if result["returncode"] == 0 and can_import(python, "jsonschema"):
            return {"status": "installed", "python": python, "how": "pip" + (" --user" if extra else ""), "attempts": attempts}
    venv_dir = Path(target) / ".venv"
    result = run_command([python, "-m", "venv", str(venv_dir)], timeout=900)
    attempts.append({"command": python + " -m venv .venv", "returncode": result["returncode"], "stderr": result["stderr"][-1500:]})
    candidate = venv_python(venv_dir)
    if result["returncode"] == 0 and candidate.exists():
        result = run_command(
            [str(candidate), "-m", "pip", "install", "--disable-pip-version-check", "-q", "-r", requirements],
            timeout=900,
        )
        attempts.append({"command": str(candidate) + " -m pip install -r requirements.txt", "returncode": result["returncode"], "stderr": result["stderr"][-1500:]})
        if result["returncode"] == 0 and can_import(str(candidate), "jsonschema"):
            return {"status": "installed", "python": str(candidate), "how": "virtual environment .venv", "attempts": attempts}
    return {
        "status": "failed",
        "python": python,
        "attempts": attempts,
        "advice": "install the Python package jsonschema (>=4.18,<5) for " + python
        + ", for example: " + python + " -m pip install jsonschema",
    }


def doctor_platform(hosts, requested="auto"):
    """The agent host the doctor should check: the one this script runs inside, if its
    command is on PATH; otherwise none (a maintenance check that requires no host)."""
    if requested != "auto":
        return requested
    running = hosts.get("running_inside") or []
    on_path = hosts.get("on_path") or {}
    if "Claude Code" in running and on_path.get("Claude Code"):
        return "claude"
    if "Codex" in running and on_path.get("Codex"):
        return "codex"
    return "none"


def run_doctor(target, python, platform="none"):
    command = [python, str(Path(target) / "scripts" / "doctor.py"), "--json", "--platform", platform, "--root", str(target)]
    result = run_command(command, timeout=600)
    record = {
        "command": " ".join(command),
        "platform": platform,
        "returncode": result["returncode"],
        "ok": False,
        "failures": [],
        "warnings": [],
        "report": None,
    }
    try:
        report = json.loads(result["stdout"])
    except (ValueError, TypeError):
        report = None
    if isinstance(report, dict):
        record["report"] = report
        record["ok"] = bool(report.get("ok"))
        record["failures"] = list(report.get("failures") or [])
        record["warnings"] = list(report.get("warnings") or [])
    else:
        record["failures"] = ["doctor produced no readable report: " + (result["stderr"] or result["stdout"])[-1500:]]
    return record


def detect_hosts():
    environment = []
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        environment.append("Claude Code")
    if any(key.startswith("CODEX_") for key in os.environ):
        environment.append("Codex")
    on_path = {}
    for name, executable in (("Claude Code", "claude"), ("Codex", "codex")):
        on_path[name] = shutil.which(executable)
    return {"running_inside": environment, "on_path": on_path}


def cloud_sync_service(target):
    """Name the sync service this folder appears to live under, or return None.

    Looks at the OneDrive locations Windows records in the environment and at the
    folder's path components (not mere substrings of the path, so a folder whose
    name happens to contain "onedrive" is not flagged).
    """
    target = Path(target)
    try:
        resolved = target.resolve()
    except OSError:
        resolved = target
    for variable in ONEDRIVE_VARIABLES:
        root = os.environ.get(variable)
        if not root:
            continue
        try:
            root_path = Path(root).resolve()
        except OSError:
            continue
        if resolved == root_path or root_path in resolved.parents:
            return "OneDrive"
    for part in resolved.parts:
        lowered = part.lower()
        for hint, label in CLOUD_SYNC_HINTS:
            if lowered.startswith(hint):
                return label
    return None


def unsynced_folder_suggestion():
    """A concrete unsynced location to suggest: directly under the home folder."""
    try:
        home = Path.home()
    except (RuntimeError, OSError):
        return "a folder directly under your home folder"
    return str(home / "elara" / "<project-name>")


def cloud_sync_warning(target):
    service = cloud_sync_service(target)
    if not service:
        return None
    windows_note = (
        " On Windows 11, Desktop and Documents are usually inside OneDrive."
        if os.name == "nt" else ""
    )
    return (
        "This folder is inside a cloud-synced location (" + service + "). ELARA works here, but "
        "sync services can corrupt append-only logs and Git repositories mid-write, restore "
        "superseded files, and copy restricted source material to the cloud. A local, unsynced "
        "folder is safer, for example " + unsynced_folder_suggestion() + "." + windows_note
        + " Stage 00 offers, before it writes any project state, to set ELARA up in such a folder "
        "instead and import your materials from here by path; nothing of yours has to move."
    )


# --------------------------------------------------------------------------- report


def format_list(items, empty="none"):
    if not items:
        return "- " + empty
    return "\n".join("- " + str(item) for item in items)


def next_steps(summary):
    steps = []
    steps.append(
        "Read AGENTS.md (the standing rules) and PIPELINE.md (the map and the menu of tools), "
        "then " + REPORT_RELATIVE + " (this report)."
    )
    steps.append(
        'Follow workflow/stages/00-initialize.md from its "Orientation (first session)" section: '
        "explain ELARA in plain language, ask whether the researcher wants to go through the whole "
        "pipeline or use specific tools now (show the menu from PIPELINE.md), then continue with "
        "Stage 00: work out what the folder already answers and ask the rest in one message, each "
        "question with a suggested default. Speak to a legal scholar who may never have used a "
        "terminal; run every command yourself; and be low-touch from then on: "
        "workflow/shared/guardrails.md section 11 lists the only reasons to stop and ask."
    )
    if not summary.get("already_installed"):
        steps.append(
            "Do not invoke /elr or $elr in this session: repository skills load when the app starts, "
            "and a skill announced from a temporary kit copy no longer exists once that copy is "
            "removed. Follow the stage file directly; the commands work after the researcher "
            "restarts the app in this folder."
        )
    existing = summary.get("existing_materials") or []
    if existing:
        step = (
            str(len(existing))
            + " item(s) were already in this folder before ELARA was installed (listed in this report). "
            "Ask whether they belong to the project; if so, use Stage 00's adoption path and do not ask "
            "the researcher to move or rename anything."
        )
        shared = [record for record in summary.get("shared_folders") or [] if record["yours"]]
        if shared:
            step += (
                " Their files inside folders the kit also uses ("
                + ", ".join("`" + record["folder"] + "/`" for record in shared)
                + ") are listed by name above and in `" + MANIFEST_RELATIVE + "`; those are theirs, "
                "not the kit's."
            )
        steps.append(step)
    if summary.get("cloud_sync_service"):
        steps.append(
            "This folder is inside a cloud-synced location (" + str(summary["cloud_sync_service"])
            + "; see Warnings). Right after the orientation, and before any project state is "
            "written, say so plainly and offer once to set ELARA up in an unsynced folder instead "
            "(for example " + unsynced_folder_suggestion() + "): run `python scripts/bootstrap.py "
            "--into <that folder>` yourself, tell the researcher to reopen the app there, and let "
            "Stage 00 import their materials from here by path. Record their choice as a decision "
            "either way. If they stay here, do not recommend `git init` in this folder, and say why."
        )
    conflicts = summary.get("essential_conflicts") or []
    if conflicts:
        steps.append(
            str(len(conflicts))
            + " file(s) of the researcher's sit at paths ELARA needs in order to run ("
            + ", ".join(conflicts)
            + "; see Warnings). ELARA is incomplete in this folder. Explain that plainly and "
            "recommend installing ELARA into a different folder (a new, empty one is simplest) "
            "and importing the materials from here by path at Stage 00; never move or rename "
            "their files without asking."
        )
    dependency = summary.get("dependency") or {}
    if dependency.get("status") in ("missing", "failed"):
        steps.append(
            "The Python package jsonschema is not available yet: " + str(dependency.get("advice"))
            + ". It is needed for the fan-out controller and validators, not for the first interview; "
            "Stage 00's environment check will ask for it again."
        )
    steps.append("Use this Python for ELARA scripts: " + str(summary.get("python_for_kit")))
    if summary.get("temporary_source"):
        if summary.get("temporary_source_removed"):
            steps.append(
                "The temporary kit copy ./" + str(summary["temporary_source"]) + " was only needed for "
                "installation and has been removed; everything is installed here."
            )
        else:
            steps.append(
                "The kit copy at ./" + str(summary["temporary_source"]) + " was only needed for installation; "
                "delete that folder now (everything is installed here)."
            )
    doctor = summary.get("doctor") or {}
    if doctor and not doctor.get("skipped") and not doctor.get("ok"):
        steps.append(
            "The doctor reported problems (listed above). Explain them plainly and help fix them; "
            "the interview can start meanwhile, but no research work should proceed on a broken setup."
        )
    return steps


def dry_run_steps(summary):
    """What to do after a dry run: it only showed the plan."""
    steps = [
        "This was a dry run: nothing was written, installed, or removed. The lists above are what "
        "a real run would do. Check them against the researcher's files, then run the same command "
        "again without --dry-run to install."
    ]
    conflicts = summary.get("essential_conflicts") or []
    if conflicts:
        steps.append(
            "A real run would leave these files of the researcher's alone but ELARA would be "
            "incomplete here (" + ", ".join(conflicts) + "); prefer installing into a different "
            "folder and importing the materials by path at Stage 00."
        )
    return steps


def rollup(paths):
    """Summarize many paths as top-level names with counts, e.g. 'workflow/ (58)'."""
    counts = {}
    for path in paths:
        head, sep, _rest = str(path).partition("/")
        key = head + ("/" if sep else "")
        counts[key] = counts.get(key, 0) + 1
    return [key + (" (" + str(count) + ")" if key.endswith("/") else "") for key, count in sorted(counts.items())]


def researcher_notes():
    return [
        "Later, open this same folder in Claude Code or Codex and type /elr resume (Claude Code) or "
        "$elr resume (Codex), or simply say \"continue\". /elr menu shows the tools; /elr help explains "
        "everything again; /elr status says where things stand.",
        "If /elr (or $elr) is not recognized, restart the app in this folder once; skills load at start. "
        "The same restart loads ELARA's worker definitions (.claude/agents/ and .claude/workflows/ in "
        "Claude Code, .codex/agents/ in Codex), which the kit uses to run searches and coding in "
        "parallel; do it before the first long stage.",
    ]


def render_report(summary):
    lines = []
    lines.append("# ELARA bootstrap report")
    lines.append("")
    lines.append(
        "Written by `scripts/bootstrap.py`. Each run appends a section; the last section is the "
        "current one. Stage 00 reads this file to learn how the kit was installed, what the folder "
        "already contained, which Python to use, and what the doctor found."
    )
    lines.append("")
    lines.append("## Bootstrap run " + summary["timestamp"])
    lines.append("")
    source = summary["source"]
    lines.append("- Target folder: `" + summary["target"] + "`")
    source_line = "- Kit source: " + source.get("kind", "?") + " `" + str(source.get("location")) + "`"
    if source.get("ref"):
        source_line += " (ref `" + str(source["ref"]) + "`)"
    if source.get("commit"):
        source_line += " (commit `" + str(source["commit"]) + "`)"
    lines.append(source_line)
    lines.append("- Kit workflow version: " + str(summary.get("kit_version")))
    lines.append("- Mode: " + ("update" if summary["update"] else "install"))
    lines.append(
        "- Git: "
        + ("this folder is already a Git repository" if summary.get("target_is_git_repository") else "no .git folder here (Stage 00 may offer to create one)")
    )
    if summary.get("already_installed"):
        lines.append("- ELARA was already installed in this folder before this run.")
    lines.append("")
    lines.append("### Files")
    lines.append("")
    files = summary["files"]
    lines.append("- Installed: " + str(len(files["installed"])))
    lines.append("- Unchanged: " + str(len(files["unchanged"])))
    lines.append("- Updated: " + str(len(files["updated"])))
    lines.append(
        "- Which files are the kit's, which are shared, and which were yours before the kit "
        "arrived: `" + MANIFEST_RELATIVE + "` (rewritten on every run; anything not listed "
        "there is not the kit's)"
    )
    lines.append("")
    lines.append("Kept as yours (the kit's version was installed under another name or not at all):")
    lines.append(format_list(files["aliased"] + files["kept"]))
    lines.append("")
    lines.append("Merged (kit lines appended in a marked block; your lines untouched):")
    lines.append(format_list(files["merged"]))
    lines.append("")
    lines.append("Prepended (kit block first, your text after it):")
    lines.append(format_list(files["prepended"]))
    lines.append("")
    lines.append("### What the folder already contained")
    lines.append("")
    existing = summary.get("existing_materials") or []
    if existing:
        lines.append(
            "These items were present before installation. Stage 00 should ask whether they belong "
            "to the project and, if so, treat them as existing materials without moving them."
        )
        lines.append("")
        for record in existing[:200]:
            if record["kind"] == "folder":
                count = ("more than " if record.get("files_truncated") else "") + str(record.get("files"))
                lines.append("- `" + record["name"] + "/` (folder, " + count + " file(s))")
            else:
                lines.append("- `" + record["name"] + "` (" + str(record.get("bytes")) + " bytes)")
        if len(existing) > 200:
            lines.append("- ... and " + str(len(existing) - 200) + " more")
    else:
        lines.append("- nothing (empty folder): this is a fresh project unless the researcher says otherwise")
    lines.append("")
    lines.append("### Folders you already had that the kit also uses")
    lines.append("")
    shared = summary.get("shared_folders") or []
    if shared:
        lines.append(
            "The kit keeps its own files in these folders next to yours. Yours are listed by name "
            "so nobody has to guess later; everything else in them is the kit's (`"
            + MANIFEST_RELATIVE + "` lists every kit path)."
        )
        lines.append("")
        for record in shared:
            yours = record["yours"]
            shown = ", ".join("`" + path + "`" for path in yours[:50])
            more = len(yours) - 50
            if more > 0:
                shown += ", and " + str(more) + " more"
            if record.get("yours_truncated"):
                shown += " (list cut off at " + str(SHARED_FOLDER_LIST_CAP) + " files)"
            lines.append(
                "- `" + record["folder"] + "/`: " + str(len(yours)) + " file(s) of yours"
                + (": " + shown if yours else "")
                + "; " + str(record["kit_files"]) + " kit file(s)"
            )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("### Environment")
    lines.append("")
    lines.append("- Python running bootstrap: " + summary["python"]["version"] + " at `" + summary["python"]["executable"] + "`")
    lines.append("- Python to use for ELARA scripts: `" + str(summary["python_for_kit"]) + "`")
    dependency = summary["dependency"]
    lines.append("- jsonschema: " + str(dependency.get("status")) + (" (" + dependency["how"] + ")" if dependency.get("how") else ""))
    hosts = summary["hosts"]
    lines.append("- Running inside: " + (", ".join(hosts["running_inside"]) or "not detected"))
    for name, path in hosts["on_path"].items():
        lines.append("- " + name + " command on PATH: " + (path or "not found"))
    lines.append("- Operating system: " + summary["os"])
    if summary.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        lines.append(format_list(summary["warnings"]))
    lines.append("")
    lines.append("### Doctor")
    lines.append("")
    doctor = summary["doctor"]
    if doctor.get("skipped"):
        lines.append("- skipped")
    else:
        if doctor.get("command"):
            lines.append("- Command: `" + doctor["command"] + "`")
        if doctor.get("platform"):
            lines.append(
                "- Agent host checked: " + doctor["platform"]
                + (" (none: no host command was on PATH, so only Python, the dependency, the kit "
                   "contract, and the offline fan-out were checked; Stage 00 runs the doctor "
                   "again for the active platform)" if doctor["platform"] == "none" else "")
            )
        lines.append("- Result: " + ("PASS" if doctor["ok"] else "FAIL"))
        if doctor["failures"]:
            lines.append(format_list(doctor["failures"]))
        if doctor.get("warnings"):
            lines.append("- Notes that do not block research:")
            lines.append(format_list(doctor["warnings"]))
    lines.append("")
    lines.append("### Next steps for the assistant")
    lines.append("")
    for index, step in enumerate(next_steps(summary), 1):
        lines.append(str(index) + ". " + step)
    lines.append("")
    lines.append("### For the researcher")
    lines.append("")
    lines.append(format_list(researcher_notes()))
    lines.append("")
    lines.append("### Machine-readable summary")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(machine_summary(summary), indent=2, sort_keys=True))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def machine_summary(summary):
    doctor = summary["doctor"]
    return {
        "schema_version": "1.0",
        "timestamp": summary["timestamp"],
        "target": summary["target"],
        "source": summary["source"],
        "kit_version": summary.get("kit_version"),
        "update": summary["update"],
        "dry_run": bool(summary.get("dry_run")),
        "already_installed": summary.get("already_installed", False),
        "files": {
            key: len(value)
            for key, value in summary["files"].items()
            if not key.endswith("_paths")
        },
        "kept": summary["files"]["kept"] + summary["files"]["aliased"],
        "merged": summary["files"]["merged"] + summary["files"]["prepended"],
        "researcher_paths": sorted(set(summary["files"]["researcher_paths"])),
        "essential_conflicts": summary.get("essential_conflicts") or [],
        "manifest_path": None if summary.get("dry_run") else MANIFEST_RELATIVE,
        "existing_materials": summary.get("existing_materials") or [],
        "shared_folders": summary.get("shared_folders") or [],
        "python": summary["python"],
        "python_for_kit": summary["python_for_kit"],
        "dependency": {
            "status": summary["dependency"].get("status"),
            "how": summary["dependency"].get("how"),
            "advice": summary["dependency"].get("advice"),
        },
        "hosts": summary["hosts"],
        "cloud_sync_service": summary.get("cloud_sync_service"),
        "warnings": summary.get("warnings") or [],
        "doctor": {
            "skipped": bool(doctor.get("skipped")),
            "ok": bool(doctor.get("ok")),
            "platform": doctor.get("platform"),
            "failures": doctor.get("failures") or [],
            "warnings": doctor.get("warnings") or [],
        },
        "report_path": None if summary.get("dry_run") else REPORT_RELATIVE,
        "temporary_source": summary.get("temporary_source"),
        "temporary_source_removed": summary.get("temporary_source_removed"),
        "ok": summary["ok"],
    }


def append_report(target, text):
    path = Path(target) / REPORT_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = read_text(path)
        # Drop the header of the new text; keep one header per file.
        marker = "## Bootstrap run "
        new_section = text[text.index(marker):] if marker in text else text
        combined = existing.rstrip("\n") + "\n\n" + new_section
        write_text(path, combined)
    else:
        write_text(path, text)
    return path


def print_human(summary):
    files = summary["files"]
    dry_run = bool(summary.get("dry_run"))
    print("ELARA bootstrap" + (" (DRY RUN: nothing was written, installed, or removed)" if dry_run else ""))
    print("  Folder:      " + summary["target"])
    source = summary["source"]
    print("  Kit source:  " + str(source.get("kind")) + " " + str(source.get("location")))
    verb = "would be " if dry_run else ""
    print(
        "  Files:       "
        + str(len(files["installed"])) + " " + verb + "installed, "
        + str(len(files["unchanged"])) + " unchanged, "
        + str(len(files["updated"])) + " " + verb + "updated, "
        + str(len(files["kept"]) + len(files["aliased"])) + " kept as yours, "
        + str(len(files["merged"]) + len(files["prepended"])) + " " + verb + "merged"
    )
    if dry_run and files["installed"]:
        print("               would install: " + ", ".join(rollup(files["installed"])))
    for item in files["aliased"] + files["kept"] + files["merged"] + files["prepended"]:
        print("               - " + item)
    existing = summary.get("existing_materials") or []
    where = "below" if dry_run else "see " + REPORT_RELATIVE
    print("  Already here: " + (str(len(existing)) + " item(s) (" + where + ")" if existing else "nothing; empty folder"))
    if dry_run:
        for record in existing[:200]:
            if record["kind"] == "folder":
                count = ("more than " if record.get("files_truncated") else "") + str(record.get("files"))
                print("               - " + record["name"] + "/ (folder, " + count + " file(s))")
            else:
                print("               - " + record["name"] + " (" + str(record.get("bytes")) + " bytes)")
    shared = [record for record in summary.get("shared_folders") or [] if record["yours"]]
    if shared:
        print(
            "  Shared folders: "
            + ", ".join(
                record["folder"] + "/ (" + str(len(record["yours"])) + " of yours)" for record in shared
            )
            + (" (each file named in " + REPORT_RELATIVE + ")" if not dry_run else "")
        )
        if dry_run:
            for record in shared:
                print("               - " + record["folder"] + "/: " + ", ".join(record["yours"][:50]))
    if not dry_run:
        print("  Manifest:    " + MANIFEST_RELATIVE + " (which files are the kit's, shared, or yours)")
    print("  Python:      " + summary["python"]["version"] + " (" + summary["python"]["executable"] + ")")
    dependency = summary["dependency"]
    status = str(dependency.get("status"))
    if dry_run and status != "present":
        status += " (a real run installs it)"
    print("  jsonschema:  " + status + (" via " + dependency["how"] if dependency.get("how") else ""))
    print("  Use for ELARA scripts: " + str(summary["python_for_kit"]))
    hosts = summary["hosts"]
    print("  Assistant:   " + (", ".join(hosts["running_inside"]) or "not detected from the environment"))
    for warning in summary.get("warnings") or []:
        print("  WARNING:     " + warning)
    doctor = summary["doctor"]
    if doctor.get("skipped"):
        print("  Doctor:      skipped" + (" (" + doctor["reason"] + ")" if doctor.get("reason") else ""))
    else:
        checked = " (checked for " + doctor["platform"] + ")" if doctor.get("platform") and doctor["platform"] != "none" else ""
        print("  Doctor:      " + ("PASS" if doctor["ok"] else "FAIL") + checked)
        for failure in doctor["failures"]:
            print("               - " + str(failure))
        for warning in doctor.get("warnings") or []:
            print("               - (not blocking) " + str(warning))
    if dry_run:
        temporary = summary.get("temporary_source")
        if temporary and is_temporary_kit_name(temporary):
            print("  Would remove: the temporary kit copy ./" + str(temporary) + " after installing")
        print("")
        print("NEXT STEPS FOR THE ASSISTANT")
        for index, step in enumerate(dry_run_steps(summary), 1):
            print("  " + str(index) + ". " + step)
        return
    print("  Report:      " + REPORT_RELATIVE)
    print("")
    print("NEXT STEPS FOR THE ASSISTANT")
    for index, step in enumerate(next_steps(summary), 1):
        print("  " + str(index) + ". " + step)
    print("")
    print("FOR THE RESEARCHER")
    for note in researcher_notes():
        print("  - " + note)
    if summary.get("removed_loose_script"):
        print("")
        print("  (The downloaded bootstrap script " + summary["removed_loose_script"] + " removed itself; a copy lives at scripts/bootstrap.py.)")
    if summary.get("temporary_source_removed"):
        print("")
        print("  (The temporary kit copy ./" + str(summary["temporary_source"]) + " was removed; everything is installed here.)")


# --------------------------------------------------------------------------- main


def bootstrap(args):
    target = Path(args.into).expanduser().resolve()
    dry_run = bool(getattr(args, "dry_run", False))
    loose = loose_script_path()
    ignore_names = set()
    if loose is not None and loose.parent == target:
        ignore_names.add(loose.name)
    with tempfile.TemporaryDirectory(prefix="elara-bootstrap-") as workdir:
        source, source_info = resolve_source(args, workdir)
        source = Path(source).resolve()
        if source in target.parents:
            raise BootstrapError(
                "The target folder is inside the kit copy you are installing from. "
                "Choose a project folder outside it, or run this from the kit root itself."
            )
        temporary_source = None
        if source != target and source.parent == target:
            # A kit copy cloned or unzipped inside the project folder just to
            # install from: not one of the researcher's materials.
            ignore_names.add(source.name)
            temporary_source = source.name
        already_installed = is_kit_root(target)
        previous_manifest = read_manifest(target)
        kit_top = kit_top_level(source)
        existing_materials = snapshot_existing(target, ignore_names)
        shared_before = shared_folder_snapshot(target, kit_top, ignore_names)
        if target == source:
            # "python scripts/bootstrap.py" inside a downloaded kit: nothing to copy.
            files = empty_outcome()
            for relative, _absolute in kit_files(source):
                files["unchanged"].append(relative)
                files["project_paths" if relative in PROJECT_OWNED else "kit_paths"].append(relative)
        else:
            if not dry_run:
                target.mkdir(parents=True, exist_ok=True)
            files = install(
                source,
                target,
                args.update,
                already_installed=already_installed,
                researcher_paths=(previous_manifest or {}).get("researcher_paths") or [],
                dry_run=dry_run,
            )
        if already_installed:
            # Report only what is not part of the kit itself: whatever the kit
            # actually owns here at top level (a researcher's README.md is theirs).
            kit_names = set(
                path.split("/", 1)[0]
                for path in files["kit_paths"] + files["shared_paths"] + files["project_paths"]
            )
            existing_materials = [
                record for record in existing_materials if record["name"] not in kit_names
            ]
        summary = {
            "timestamp": utc_now(),
            "target": str(target),
            "target_is_git_repository": (target / ".git").exists(),
            "temporary_source": temporary_source,
            "source": source_info,
            "kit_version": kit_version(target) or kit_version(source),
            "update": bool(args.update),
            "dry_run": dry_run,
            "already_installed": already_installed,
            "files": files,
            "existing_materials": existing_materials,
            "shared_folders": describe_shared_folders(shared_before, files),
            "python": {
                "executable": sys.executable,
                "version": ".".join(str(part) for part in sys.version_info[:3]),
            },
            "os": platform.platform(),
            "hosts": detect_hosts(),
            "warnings": [],
        }
    summary["cloud_sync_service"] = cloud_sync_service(target)
    warning = cloud_sync_warning(target)
    if warning:
        summary["warnings"].append(warning)
    conflicts = essential_conflicts(files["researcher_paths"])
    summary["essential_conflicts"] = conflicts
    if conflicts:
        summary["warnings"].append(essential_conflict_warning(conflicts))
    # A dry run only checks whether the dependency is present; it installs nothing.
    dependency = ensure_dependency(target, sys.executable, args.no_install or dry_run)
    summary["dependency"] = dependency
    summary["python_for_kit"] = dependency.get("python") or sys.executable
    summary["doctor_platform"] = doctor_platform(summary["hosts"], getattr(args, "platform", "auto"))
    if dry_run:
        summary["doctor"] = {
            "skipped": True,
            "ok": False,
            "failures": [],
            "command": None,
            "reason": "dry run: nothing was installed, so there is nothing to check yet",
        }
    elif args.skip_doctor:
        summary["doctor"] = {"skipped": True, "ok": False, "failures": [], "command": None}
    elif "scripts/doctor.py" in conflicts:
        # Never run a file of the researcher's as if it were the kit's doctor.
        summary["doctor"] = {
            "skipped": False,
            "ok": False,
            "failures": [
                "scripts/doctor.py here is your own file, not ELARA's, so ELARA's preflight "
                "check could not run in this folder"
            ],
            "command": None,
            "report": None,
        }
    else:
        summary["doctor"] = run_doctor(target, summary["python_for_kit"], summary["doctor_platform"])
        summary["doctor"]["skipped"] = False
    if dry_run:
        # The plan itself is the result; nothing was written, so nothing can be broken yet.
        summary["ok"] = True
        summary["temporary_source_removed"] = None
        summary["report_path"] = None
        summary["manifest_path"] = None
        return summary
    summary["ok"] = bool(
        (summary["doctor"].get("skipped") or summary["doctor"].get("ok"))
        and dependency.get("status") in ("present", "installed")
    )
    # A kit copy cloned or unzipped inside the project folder under the README's
    # `.elara-kit` convention was only needed to install from: remove it now, so
    # the researcher's folder holds one ELARA and nobody has to delete anything.
    # A copy under any other name (a full clone the researcher may want) stays.
    summary["temporary_source_removed"] = None
    if temporary_source and not args.keep and is_temporary_kit_name(temporary_source):
        summary["temporary_source_removed"] = remove_tree(target / temporary_source)
    report_path = append_report(target, render_report(summary))
    summary["report_path"] = str(report_path)
    write_text(
        target / MANIFEST_RELATIVE,
        json.dumps(build_manifest(summary), indent=2, sort_keys=True) + "\n",
    )
    summary["manifest_path"] = MANIFEST_RELATIVE
    if loose is not None and loose.parent == target and not args.keep:
        try:
            loose.unlink()
            summary["removed_loose_script"] = loose.name
        except OSError:
            summary["removed_loose_script"] = None
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--into",
        default=".",
        help="folder to install ELARA into (default: the current folder)",
    )
    parser.add_argument(
        "--source",
        help="install from this kit folder or ZIP archive instead of downloading",
    )
    parser.add_argument(
        "--ref",
        default=DEFAULT_REF,
        help="branch or tag to download when no local kit is available (default: main)",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="refresh kit-owned files that differ from this kit version (never project state, ledgers, or a file that was yours before the kit)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be installed, kept, merged, or aliased, and what the folder already holds; write, install, and remove nothing",
    )
    parser.add_argument(
        "--no-install",
        action="store_true",
        help="do not try to install the Python dependency",
    )
    parser.add_argument(
        "--skip-doctor",
        action="store_true",
        help="do not run scripts/doctor.py afterwards",
    )
    parser.add_argument(
        "--platform",
        choices=("auto", "codex", "claude", "all", "none"),
        default="auto",
        help="agent host the doctor should check; auto means the host this script runs inside (if its command is on PATH), else none",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep a downloaded loose copy of this script, and a temporary .elara-kit copy, instead of removing them after installation",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print a machine-readable summary instead of the human report",
    )
    args = parser.parse_args()
    for stream in (sys.stdout, sys.stderr):
        # Windows consoles may not be UTF-8; never crash on a path with unusual characters.
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="replace")
            except (ValueError, OSError):
                pass
    try:
        summary = bootstrap(args)
    except BootstrapError as exc:
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        else:
            print("ELARA bootstrap could not finish:\n  " + str(exc).replace("\n", "\n  "))
        return 2
    if args.json:
        record = machine_summary(summary)
        record["removed_loose_script"] = summary.get("removed_loose_script")
        print(json.dumps(record, indent=2, sort_keys=True))
    else:
        print_human(summary)
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
