"""Install ELARA into the folder you are working in and check that it is ready.

An assistant such as Claude Code or Codex normally runs this for the researcher:

    python bootstrap.py                 # install ELARA into the current folder
    python bootstrap.py --into PATH     # install it somewhere else
    python scripts/bootstrap.py         # inside a downloaded kit: check this copy

The script copies the kit into the target folder without overwriting anything
that is already there, merges the few files that must be shared (.gitignore,
requirements.txt, and any AGENTS.md or CLAUDE.md the folder already has),
installs the kit's one Python dependency, runs scripts/doctor.py, writes
project/BOOTSTRAP.md, and prints what the assistant should do next. It needs
only the Python standard library. When it is run from inside a kit copy it
installs from that copy; otherwise it downloads the kit from GitHub.

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
LOOSE_SCRIPT_NAMES = ("bootstrap.py", "elara_bootstrap.py")

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
# Kit files that may collide with a file the researcher already has. The kit
# copy is installed under an alternate name so nothing of theirs is touched.
ALIASES = {"README.md": "ELARA_README.md", "LICENSE": "LICENSE.ELARA"}
MERGED = {".gitignore", "requirements.txt"}

MARK_BEGIN = "<!-- elara:begin (installed by scripts/bootstrap.py; keep this block first) -->"
MARK_END = "<!-- elara:end -->"
LINE_MARK_BEGIN = "# >>> ELARA (added by scripts/bootstrap.py) >>>"
LINE_MARK_END = "# <<< ELARA <<<"

CLOUD_SYNC_HINTS = (
    "google drive",
    "googledrive",
    "my drive",
    "onedrive",
    "dropbox",
    "icloud",
    "mobile documents",
    "box sync",
)


class BootstrapError(Exception):
    """A problem the researcher or assistant must resolve; explained in plain words."""


# --------------------------------------------------------------------------- helpers


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    slug = state_field(root, "project_slug")
    return slug is None or slug == "null"


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
        + "\n  If the repository is private, you need access to it and Git (or the gh CLI) signed in.\n"
        + "  Otherwise check the internet connection, or download the kit by hand from\n  "
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
            for _directory, subdirectories, filenames in os.walk(str(entry)):
                subdirectories[:] = [
                    sub for sub in subdirectories if sub not in EXCLUDED_DIRECTORIES
                ]
                count += len(filenames)
                if count > 5000:
                    break
            record["files"] = count
        else:
            try:
                record["bytes"] = entry.stat().st_size
            except OSError:
                record["bytes"] = None
        entries.append(record)
    return entries


def install(source, target, update):
    """Copy the kit into target. Returns the per-file outcome lists."""
    source = Path(source)
    target = Path(target)
    outcome = {
        "installed": [],
        "unchanged": [],
        "kept": [],
        "aliased": [],
        "merged": [],
        "updated": [],
        "prepended": [],
    }
    for relative, absolute in kit_files(source):
        destination = target / relative
        kit_bytes = absolute.read_bytes()
        if not destination.exists():
            if relative in ALIASES and (target / ALIASES[relative]).exists():
                # The researcher's own file was replaced or removed since the
                # first install, but the alias exists: keep the alias current.
                destination = target / ALIASES[relative]
                relative = ALIASES[relative]
                if destination.read_bytes() == kit_bytes:
                    outcome["unchanged"].append(relative)
                    continue
                if update:
                    destination.write_bytes(kit_bytes)
                    outcome["updated"].append(relative)
                else:
                    outcome["kept"].append(relative + " (differs from this kit version; --update refreshes it)")
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(kit_bytes)
            outcome["installed"].append(relative)
            continue
        existing_bytes = destination.read_bytes()
        if existing_bytes == kit_bytes:
            outcome["unchanged"].append(relative)
            continue
        if relative in PROJECT_OWNED:
            outcome["kept"].append(relative + " (project state or ledger; never replaced)")
            continue
        if relative in MERGED:
            existing_text = existing_bytes.decode("utf-8", errors="replace")
            kit_text = kit_bytes.decode("utf-8", errors="replace")
            if relative == "requirements.txt":
                merged_text, added = merge_requirements(existing_text, kit_text)
            else:
                merged_text, added = merge_line_file(existing_text, kit_text)
            if added:
                write_text(destination, merged_text)
                outcome["merged"].append(relative + " (+" + str(len(added)) + " line(s))")
            else:
                outcome["unchanged"].append(relative + " (already contains the kit's lines)")
            continue
        existing_text = existing_bytes.decode("utf-8", errors="replace")
        kit_text = kit_bytes.decode("utf-8", errors="replace")
        if relative == "AGENTS.md":
            if is_kit_agents(existing_text):
                if update:
                    destination.write_bytes(kit_bytes)
                    outcome["updated"].append(relative)
                else:
                    outcome["kept"].append(relative + " (an earlier kit version; --update refreshes it)")
                continue
            merged_text, how = merge_agents(existing_text, kit_text, update)
            if how == "already merged":
                outcome["unchanged"].append(relative + " (kit constitution already merged)")
            else:
                write_text(destination, merged_text)
                outcome["prepended"].append(relative + " (" + how + "; your text follows the ELARA block)")
            continue
        if relative == "CLAUDE.md":
            if is_kit_claude(existing_text):
                if update:
                    destination.write_bytes(kit_bytes)
                    outcome["updated"].append(relative)
                else:
                    outcome["kept"].append(relative + " (an earlier kit version; --update refreshes it)")
                continue
            merged_text, how = merge_claude(existing_text, kit_text, update)
            if how == "already merged":
                outcome["unchanged"].append(relative + " (kit adapter already merged)")
            else:
                write_text(destination, merged_text)
                outcome["prepended"].append(relative + " (" + how + "; your text follows the ELARA block)")
            continue
        if relative in ALIASES:
            if relative == "README.md" and is_kit_readme(existing_text):
                if update:
                    destination.write_bytes(kit_bytes)
                    outcome["updated"].append(relative)
                else:
                    outcome["kept"].append(relative + " (an earlier kit version; --update refreshes it)")
                continue
            alias = target / ALIASES[relative]
            if alias.exists() and alias.read_bytes() == kit_bytes:
                outcome["unchanged"].append(ALIASES[relative])
                continue
            if alias.exists() and not update:
                outcome["kept"].append(ALIASES[relative] + " (differs from this kit version; --update refreshes it)")
                continue
            alias.write_bytes(kit_bytes)
            outcome["aliased"].append(relative + " -> " + ALIASES[relative] + " (your " + relative + " was left alone)")
            continue
        # Every other kit-owned file (workflow/, scripts/, tests/, .agents/, .claude/,
        # PIPELINE.md, project READMEs, ...): refreshed only with --update.
        if update:
            destination.write_bytes(kit_bytes)
            outcome["updated"].append(relative)
        else:
            outcome["kept"].append(relative + " (differs from this kit version; --update refreshes it)")
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


def run_doctor(target, python):
    command = [python, str(Path(target) / "scripts" / "doctor.py"), "--json", "--platform", "none", "--root", str(target)]
    result = run_command(command, timeout=600)
    record = {"command": " ".join(command), "returncode": result["returncode"], "ok": False, "failures": [], "report": None}
    try:
        report = json.loads(result["stdout"])
    except (ValueError, TypeError):
        report = None
    if isinstance(report, dict):
        record["report"] = report
        record["ok"] = bool(report.get("ok"))
        record["failures"] = list(report.get("failures") or [])
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


def cloud_sync_warning(target):
    lowered = str(target).lower()
    for hint in CLOUD_SYNC_HINTS:
        if hint in lowered:
            return (
                "This folder looks like it is inside a cloud-synced location (" + hint + "). "
                "ELARA works, but sync services can interfere with its append-only logs and "
                "may copy restricted source material to the cloud; a local, non-synced folder is safer."
            )
    return None


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
        "Stage 00 one question at a time. Speak to a legal scholar who may never have used a "
        "terminal; run every command yourself."
    )
    existing = summary.get("existing_materials") or []
    if existing:
        steps.append(
            str(len(existing))
            + " item(s) were already in this folder before ELARA was installed (listed in this report). "
            "Ask whether they belong to the project; if so, use Stage 00's adoption path and do not ask "
            "the researcher to move or rename anything."
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


def researcher_notes():
    return [
        "Later, open this same folder in Claude Code or Codex and type /elr resume (Claude Code) or "
        "$elr resume (Codex), or simply say \"continue\". /elr menu shows the tools; /elr help explains "
        "everything again; /elr status says where things stand.",
        "If /elr (or $elr) is not recognized, restart the app in this folder once; skills load at start.",
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
                lines.append("- `" + record["name"] + "/` (folder, " + str(record.get("files")) + " file(s))")
            else:
                lines.append("- `" + record["name"] + "` (" + str(record.get("bytes")) + " bytes)")
        if len(existing) > 200:
            lines.append("- ... and " + str(len(existing) - 200) + " more")
    else:
        lines.append("- nothing (empty folder): this is a fresh project unless the researcher says otherwise")
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
        lines.append("- Command: `" + doctor["command"] + "`")
        lines.append("- Result: " + ("PASS" if doctor["ok"] else "FAIL"))
        if doctor["failures"]:
            lines.append(format_list(doctor["failures"]))
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
        "already_installed": summary.get("already_installed", False),
        "files": {key: len(value) for key, value in summary["files"].items()},
        "kept": summary["files"]["kept"] + summary["files"]["aliased"],
        "merged": summary["files"]["merged"] + summary["files"]["prepended"],
        "existing_materials": summary.get("existing_materials") or [],
        "python": summary["python"],
        "python_for_kit": summary["python_for_kit"],
        "dependency": {
            "status": summary["dependency"].get("status"),
            "how": summary["dependency"].get("how"),
            "advice": summary["dependency"].get("advice"),
        },
        "hosts": summary["hosts"],
        "warnings": summary.get("warnings") or [],
        "doctor": {
            "skipped": bool(doctor.get("skipped")),
            "ok": bool(doctor.get("ok")),
            "failures": doctor.get("failures") or [],
        },
        "report_path": REPORT_RELATIVE,
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
    print("ELARA bootstrap")
    print("  Folder:      " + summary["target"])
    source = summary["source"]
    print("  Kit source:  " + str(source.get("kind")) + " " + str(source.get("location")))
    print(
        "  Files:       "
        + str(len(files["installed"])) + " installed, "
        + str(len(files["unchanged"])) + " unchanged, "
        + str(len(files["updated"])) + " updated, "
        + str(len(files["kept"]) + len(files["aliased"])) + " kept as yours, "
        + str(len(files["merged"]) + len(files["prepended"])) + " merged"
    )
    for item in files["aliased"] + files["kept"] + files["merged"] + files["prepended"]:
        print("               - " + item)
    existing = summary.get("existing_materials") or []
    print("  Already here: " + (str(len(existing)) + " item(s) (see " + REPORT_RELATIVE + ")" if existing else "nothing; empty folder"))
    print("  Python:      " + summary["python"]["version"] + " (" + summary["python"]["executable"] + ")")
    dependency = summary["dependency"]
    print("  jsonschema:  " + str(dependency.get("status")) + (" via " + dependency["how"] if dependency.get("how") else ""))
    print("  Use for ELARA scripts: " + str(summary["python_for_kit"]))
    hosts = summary["hosts"]
    print("  Assistant:   " + (", ".join(hosts["running_inside"]) or "not detected from the environment"))
    for warning in summary.get("warnings") or []:
        print("  WARNING:     " + warning)
    doctor = summary["doctor"]
    if doctor.get("skipped"):
        print("  Doctor:      skipped")
    else:
        print("  Doctor:      " + ("PASS" if doctor["ok"] else "FAIL"))
        for failure in doctor["failures"]:
            print("               - " + str(failure))
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


# --------------------------------------------------------------------------- main


def bootstrap(args):
    target = Path(args.into).expanduser().resolve()
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
        existing_materials = snapshot_existing(target, ignore_names)
        if already_installed:
            # Report only what is not part of the kit itself.
            kit_top = set(relative.split("/", 1)[0] for relative, _absolute in kit_files(source))
            existing_materials = [
                record for record in existing_materials
                if record["name"] not in kit_top and record["name"] not in ALIASES.values()
            ]
        if target == source:
            # "python scripts/bootstrap.py" inside a downloaded kit: nothing to copy.
            files = {"installed": [], "unchanged": [], "kept": [], "aliased": [], "merged": [], "updated": [], "prepended": []}
            files["unchanged"] = [relative for relative, _absolute in kit_files(source)]
        else:
            target.mkdir(parents=True, exist_ok=True)
            files = install(source, target, args.update)
        summary = {
            "timestamp": utc_now(),
            "target": str(target),
            "target_is_git_repository": (target / ".git").exists(),
            "temporary_source": temporary_source,
            "source": source_info,
            "kit_version": kit_version(target) or kit_version(source),
            "update": bool(args.update),
            "already_installed": already_installed,
            "files": files,
            "existing_materials": existing_materials,
            "python": {
                "executable": sys.executable,
                "version": ".".join(str(part) for part in sys.version_info[:3]),
            },
            "os": platform.platform(),
            "hosts": detect_hosts(),
            "warnings": [],
        }
    warning = cloud_sync_warning(target)
    if warning:
        summary["warnings"].append(warning)
    dependency = ensure_dependency(target, sys.executable, args.no_install)
    summary["dependency"] = dependency
    summary["python_for_kit"] = dependency.get("python") or sys.executable
    if args.skip_doctor:
        summary["doctor"] = {"skipped": True, "ok": False, "failures": [], "command": None}
    else:
        summary["doctor"] = run_doctor(target, summary["python_for_kit"])
        summary["doctor"]["skipped"] = False
    summary["ok"] = bool(
        (summary["doctor"].get("skipped") or summary["doctor"].get("ok"))
        and dependency.get("status") in ("present", "installed")
    )
    report_path = append_report(target, render_report(summary))
    summary["report_path"] = str(report_path)
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
        help="refresh kit-owned files that differ from this kit version (never project state or ledgers)",
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
        "--keep",
        action="store_true",
        help="keep a downloaded loose copy of this script instead of removing it after installation",
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
