"""Preflight check: confirm this computer and this kit copy are ready to use.

Run it as:

    python scripts/doctor.py

By default the doctor detects installed Codex and Claude Code hosts. Use
``--platform codex`` or ``--platform claude`` to require one route, ``all`` to
require both, or ``none`` for repository-maintenance checks that do not launch
an agent host. ``--json`` emits a machine-readable capability record suitable
for the Stage 00 access snapshot.

This file deliberately avoids newer Python syntax (no f-strings, no modern
type annotations, no ``from __future__ import annotations``) so that an old
interpreter can still parse it far enough to print the version advice below
instead of a confusing SyntaxError.
"""

import sys

if sys.version_info < (3, 10):
    sys.stderr.write(
        "This kit needs Python 3.10 or newer; you are running Python "
        + ".".join(str(part) for part in sys.version_info[:3])
        + ".\n"
        "Please install a current Python from https://www.python.org/downloads/\n"
        "Windows users: if you have several Pythons installed, try running the\n"
        "same command with the 'py' launcher, for example: py scripts/doctor.py\n"
    )
    sys.exit(1)

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
from importlib import metadata  # noqa: E402
from pathlib import Path  # noqa: E402


DISCOVERY_SURFACES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "PIPELINE.md",
    "requirements.txt",
    "workflow/shared/guardrails.md",
    "workflow/shared/artifact-contract.md",
    "workflow/shared/observation-fanout.md",
    "workflow/templates/preregistration_template.md",
    "project/PROJECT_STATE.md",
    ".agents/skills/elr/SKILL.md",
    ".agents/skills/elr-code-observations/SKILL.md",
    ".claude/skills/elr/SKILL.md",
    ".claude/skills/elr-code-observations/SKILL.md",
    ".claude/workflows/elr-observation-fanout.js",
)

EXPECTED_STAGE_COUNT = 20
JSONSCHEMA_RANGE = ">=4.18,<5"
MIN_CLAUDE_WORKFLOW_VERSION = (2, 1, 154)
VERSION_PATTERN = re.compile(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)")


def _version_tuple(text):
    match = VERSION_PATTERN.search(text or "")
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _dependency_report():
    report = {
        "name": "jsonschema",
        "required": JSONSCHEMA_RANGE,
        "installed": False,
        "version": None,
        "ready": False,
    }
    try:
        from jsonschema import Draft202012Validator  # noqa: F401
    except ImportError:
        return report, [
            "missing Python dependency jsonschema; run: "
            + sys.executable
            + " -m pip install -r requirements.txt"
        ]
    try:
        version = metadata.version("jsonschema")
    except metadata.PackageNotFoundError:
        return report, ["jsonschema imports but its installed version cannot be identified"]
    parsed = _version_tuple(version)
    report["installed"] = True
    report["version"] = version
    report["ready"] = bool(parsed and parsed >= (4, 18, 0) and parsed < (5, 0, 0))
    if not report["ready"]:
        return report, [
            "jsonschema " + version + " is outside the supported range " + JSONSCHEMA_RANGE
        ]
    return report, []


def _host_report(name, executable, minimum):
    path = shutil.which(executable)
    report = {
        "name": name,
        "command": executable,
        "path": path,
        "installed": bool(path),
        "version": None,
        "version_output": None,
        "minimum_for_elara": (
            ".".join(str(part) for part in minimum) if minimum else None
        ),
        "ready": False,
    }
    if not path:
        return report
    try:
        completed = subprocess.run(
            [path, "--version"],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        report["version_output"] = "version check failed: " + str(exc)
        return report
    output = (completed.stdout or completed.stderr or "").strip()
    report["version_output"] = output
    parsed = _version_tuple(output)
    if parsed:
        report["version"] = ".".join(str(part) for part in parsed)
    report["ready"] = bool(
        completed.returncode == 0 and parsed and (minimum is None or parsed >= minimum)
    )
    return report


def _host_reports(platform):
    reports = {
        "codex": _host_report("Codex", "codex", None),
        "claude": _host_report(
            "Claude Code", "claude", MIN_CLAUDE_WORKFLOW_VERSION
        ),
    }
    failures = []
    if platform == "none":
        required = []
    elif platform == "all":
        required = ["codex", "claude"]
    elif platform in ("codex", "claude"):
        required = [platform]
    else:
        required = [name for name, report in reports.items() if report["installed"]]
        if not required:
            failures.append(
                "no supported agent host was detected; install Codex or Claude Code, or use "
                "--platform none only for repository-maintenance checks"
            )

    for name, report in reports.items():
        report["required"] = name in required
        if name not in required:
            continue
        if not report["installed"]:
            failures.append("required agent host is not installed or not on PATH: " + name)
        elif not report["ready"]:
            if name == "claude" and report["version"]:
                failures.append(
                    "Claude Code "
                    + report["version"]
                    + " is older than ELARA's dynamic-workflow minimum 2.1.154"
                )
            else:
                failures.append(
                    "could not verify a usable " + report["name"] + " version with --version"
                )
    return reports, failures


def _offline_fanout_smoke(root):
    """Exercise prepare, strict submit, status, and merge without a model or network."""
    from unit_fanout import load_json, merge, prepare, status, submit

    fixture = root / "tests" / "fixtures" / "one_unit_fanout" / "spec.json"
    with tempfile.TemporaryDirectory(prefix="elara-doctor-") as temporary:
        temporary_root = Path(temporary)
        run_dir = temporary_root / "run"
        manifest = prepare(fixture, run_dir)
        row = manifest["assignments"][0]
        assignment = load_json(Path(row["assignment_path"]))
        returned = {
            "contract_version": assignment["contract_version"],
            "assignment_id": assignment["assignment_id"],
            "unit_id": assignment["unit_id"],
            "attempt": assignment["attempt"],
            "status": "succeeded",
            "result": {"label": "yes"},
            "error": None,
            "provenance": {
                "route": "doctor-offline-fixture",
                "model_call": False,
            },
        }
        receipt = submit(run_dir, assignment["assignment_id"], returned)
        operational = status(run_dir)
        merged = merge(run_dir, temporary_root / "merged.jsonl")
        if receipt["status"] != "succeeded":
            raise ValueError("strict submission did not report succeeded")
        if operational["terminal"] != 1 or operational["invalid"] != 0:
            raise ValueError("fan-out status did not reconcile one terminal assignment")
        if merged["merged"] != 1:
            raise ValueError("fan-out merge did not contain exactly one assignment")
    return {
        "ready": True,
        "fixture": "tests/fixtures/one_unit_fanout/spec.json",
        "model_calls": 0,
        "network_calls": 0,
        "assignments": 1,
    }


def build_report(root, platform="auto", smoke=True):
    """Return a complete machine-readable preflight report."""
    root = root.resolve()
    failures = []
    for relative in DISCOVERY_SURFACES:
        if not (root / relative).is_file():
            failures.append("missing " + relative)
    stage_count = len(sorted((root / "workflow" / "stages").glob("[0-9][0-9]-*.md")))
    if stage_count != EXPECTED_STAGE_COUNT:
        failures.append(
            "workflow/stages/ has "
            + str(stage_count)
            + " stage files; expected exactly "
            + str(EXPECTED_STAGE_COUNT)
        )

    repository_failures = []
    try:
        from validate_workflow import validate_repository
        from workflow_lib import FrontmatterError

        try:
            repository_failures.extend(validate_repository(root))
        except (FrontmatterError, ValueError, UnicodeDecodeError, OSError) as exc:
            repository_failures.append(str(exc))
    except (ImportError, OSError) as exc:
        repository_failures.append("cannot load repository validator: " + str(exc))
    failures.extend(repository_failures)

    dependency, dependency_failures = _dependency_report()
    failures.extend(dependency_failures)
    hosts, host_failures = _host_reports(platform)
    failures.extend(host_failures)

    smoke_report = {"ready": False, "skipped": not smoke}
    if smoke:
        if dependency["ready"]:
            try:
                smoke_report = _offline_fanout_smoke(root)
                smoke_report["skipped"] = False
            except Exception as exc:  # fail closed and preserve a useful diagnostic
                smoke_report = {
                    "ready": False,
                    "skipped": False,
                    "error": str(exc),
                }
                failures.append("offline fan-out smoke test failed: " + str(exc))
        else:
            smoke_report = {
                "ready": False,
                "skipped": True,
                "reason": "jsonschema dependency is unavailable or unsupported",
            }

    return {
        "schema_version": "1.0",
        "ok": not failures,
        "kit_root": str(root),
        "python": {
            "executable": sys.executable,
            "version": ".".join(str(part) for part in sys.version_info[:3]),
            "ready": True,
        },
        "dependency": dependency,
        "platform_selection": platform,
        "hosts": hosts,
        "checks": {
            "discovery_surfaces": "passed" if not any(
                failure.startswith("missing ") for failure in failures
            ) else "failed",
            "stage_count": stage_count,
            "repository_contract": "passed" if not repository_failures else "failed",
            "offline_fanout_smoke": smoke_report,
        },
        "failures": failures,
    }


def run_doctor(root, platform="auto", smoke=True):
    """Compatibility helper returning failure messages only."""
    return build_report(root, platform=platform, smoke=smoke)["failures"]


def _print_human_report(report):
    print("CHECK: Python " + report["python"]["version"])
    dependency = report["dependency"]
    if dependency["installed"]:
        print("CHECK: jsonschema " + str(dependency["version"]))
    else:
        print("CHECK: jsonschema not installed")
    for name in ("codex", "claude"):
        host = report["hosts"][name]
        if host["installed"]:
            suffix = host["version_output"] or "version unknown"
            print("CHECK: " + host["name"] + " - " + suffix)
        elif host["required"]:
            print("CHECK: " + host["name"] + " not found")
    smoke = report["checks"]["offline_fanout_smoke"]
    if smoke.get("skipped"):
        print("CHECK: offline one-unit fan-out smoke skipped")
    elif smoke.get("ready"):
        print("CHECK: offline one-unit fan-out smoke passed")
    else:
        print("CHECK: offline one-unit fan-out smoke failed")

    if report["failures"]:
        print("FAIL: this installation has " + str(len(report["failures"])) + " problem(s):")
        for failure in report["failures"]:
            print("- " + str(failure))
        return

    available = [
        name for name, host in report["hosts"].items() if host["installed"] and host["ready"]
    ]
    if report["platform_selection"] == "none":
        print("PASS: Python, dependencies, kit contract, and offline fan-out are ready.")
    elif available == ["codex"]:
        print("PASS: ELARA is ready for Codex. Open this repository and run $elr start.")
    elif available == ["claude"]:
        print("PASS: ELARA is ready for Claude Code. Open this repository and run /elr start.")
    else:
        print(
            "PASS: ELARA is ready. Run $elr start in Codex or /elr start in Claude Code."
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--platform",
        choices=("auto", "codex", "claude", "all", "none"),
        default="auto",
        help="agent host to require; auto accepts every detected supported host",
    )
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="skip the temporary one-unit offline prepare/submit/status/merge test",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit a machine-readable capability and readiness report",
    )
    args = parser.parse_args()
    report = build_report(
        args.root.resolve(), platform=args.platform, smoke=not args.skip_smoke
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print_human_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
