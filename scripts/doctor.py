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


# A tuple entry lists alternatives, any one of which satisfies the check: the kit
# README is README.md in a clone of the kit and ELARA_README.md in a project
# folder scripts/bootstrap.py installed into.
DISCOVERY_SURFACES = (
    "AGENTS.md",
    "CLAUDE.md",
    ("ELARA_README.md", "README.md"),
    "PIPELINE.md",
    "requirements.txt",
    "scripts/bootstrap.py",
    "workflow/shared/guardrails.md",
    "workflow/shared/artifact-contract.md",
    "workflow/shared/execution-control.md",
    "workflow/shared/observation-fanout.md",
    "workflow/templates/preregistration_template.md",
    "workflow/templates/preemption_review_template.md",
    "workflow/templates/feasibility_audit_template.md",
    "project/PROJECT_STATE.md",
    ".agents/skills/elr/SKILL.md",
    ".agents/skills/elr-code-observations/SKILL.md",
    ".claude/skills/elr/SKILL.md",
    ".claude/skills/elr-code-observations/SKILL.md",
    ".claude/workflows/elr-observation-fanout.js",
    ".claude/workflows/elr-research-fanout.js",
    ".claude/agents/elr-worker.md",
    ".claude/agents/elr-research-worker.md",
    ".codex/agents/elr-worker.toml",
    ".codex/agents/elr-research-worker.toml",
    "scripts/unit_fanout.py",
    "scripts/research_fanout.py",
    "scripts/build_preemption_review.py",
    "scripts/build_feasibility_audit.py",
    "scripts/latex_report.py",
)

# The restricted worker subagent types every fan-out must use (see
# workflow/shared/observation-fanout.md, "Worker tool surface"). Each Claude file's front matter
# must carry a `tools:` allowlist and a `disallowedTools:` line that removes every MCP tool; a
# worker that inherits the host's interactive tools can crash the host (observed 2026-08-17).
WORKER_AGENT_FILES = (
    ".claude/agents/elr-worker.md",
    ".claude/agents/elr-research-worker.md",
)
# The Codex custom sub-agents that play the same roles (workflow/shared/observation-fanout.md,
# "Codex adapter"). Each TOML file must name the agent, carry developer_instructions and a
# sandbox_mode, and declare no MCP server; the coding worker's instructions must forbid the web.
CODEX_WORKER_AGENT_FILES = (
    (".codex/agents/elr-worker.toml", "elr_worker"),
    (".codex/agents/elr-research-worker.toml", "elr_research_worker"),
)
# The kit's saved Claude workflows, and the restricted agent type each must launch its workers as.
CLAUDE_WORKFLOW_FILES = (
    (".claude/workflows/elr-observation-fanout.js", "elr-worker"),
    (".claude/workflows/elr-research-fanout.js", "elr-research-worker"),
)

EXPECTED_STAGE_COUNT = 21
JSONSCHEMA_RANGE = ">=4.18,<5"
PYTHON_DOCX_RANGE = ">=1.1,<2"
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


def _document_dependency_report():
    report = {
        "name": "python-docx",
        "required": PYTHON_DOCX_RANGE,
        "installed": False,
        "version": None,
        "ready": False,
    }
    try:
        from docx import Document  # noqa: F401
    except ImportError:
        return report, [
            "missing Python dependency python-docx; run: "
            + sys.executable
            + " -m pip install -r requirements.txt"
        ]
    try:
        version = metadata.version("python-docx")
    except metadata.PackageNotFoundError:
        return report, ["python-docx imports but its installed version cannot be identified"]
    parsed = _version_tuple(version)
    report["installed"] = True
    report["version"] = version
    report["ready"] = bool(parsed and parsed >= (1, 1, 0) and parsed < (2, 0, 0))
    if not report["ready"]:
        return report, [
            "python-docx " + version + " is outside the supported range " + PYTHON_DOCX_RANGE
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


def _worker_agent_failures(root):
    """Check that the restricted worker subagent definitions still restrict what they must."""
    failures = []
    for relative in WORKER_AGENT_FILES:
        path = root / relative
        if not path.is_file():
            continue  # already reported as a missing discovery surface
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(relative + " is unreadable: " + str(exc))
            continue
        head = text.split("---", 2)
        front = head[1] if len(head) >= 3 else ""
        tools_line = next((line for line in front.splitlines() if line.strip().startswith("tools:")), "")
        deny_line = next(
            (line for line in front.splitlines() if line.strip().startswith("disallowedTools:")), ""
        )
        if not tools_line.split(":", 1)[-1].strip():
            failures.append(relative + " has no `tools:` allowlist in its front matter")
        elif "mcp__" in tools_line:
            failures.append(relative + " allowlists an MCP tool in `tools:`")
        if "mcp__*" not in deny_line:
            failures.append(relative + " does not carry `disallowedTools: mcp__*`")
        if relative.endswith("elr-worker.md") and re.search(r"\bWeb(Fetch|Search)\b", tools_line):
            failures.append(relative + " grants web tools to the coding worker")

    for relative, expected_name in CODEX_WORKER_AGENT_FILES:
        path = root / relative
        if not path.is_file():
            continue  # already reported as a missing discovery surface
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(relative + " is unreadable: " + str(exc))
            continue
        try:
            import tomllib  # Python 3.11+; older interpreters skip the parse and keep the line checks
        except ImportError:  # pragma: no cover - depends on the interpreter
            tomllib = None
        if tomllib is not None:
            try:
                tomllib.loads(text)
            except tomllib.TOMLDecodeError as exc:
                failures.append(relative + " is not valid TOML: " + str(exc))
        name_match = re.search(r'^name\s*=\s*"([^"]+)"', text, re.MULTILINE)
        if not name_match or name_match.group(1) != expected_name:
            failures.append(relative + ' must set name = "' + expected_name + '"')
        if not re.search(r"^developer_instructions\s*=", text, re.MULTILINE):
            failures.append(relative + " has no developer_instructions")
        if not re.search(r'^sandbox_mode\s*=\s*"[^"]+"', text, re.MULTILINE):
            failures.append(relative + " has no sandbox_mode")
        if re.search(r"^\[mcp_servers\.", text, re.MULTILINE):
            failures.append(relative + " declares an MCP server for a worker")
        if relative.endswith("elr-worker.toml") and not re.search(r"no web", text, re.IGNORECASE):
            failures.append(relative + " does not forbid the web for the coding worker")

    for relative, agent_type in CLAUDE_WORKFLOW_FILES:
        path = root / relative
        if not path.is_file():
            continue  # already reported as a missing discovery surface
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(relative + " is unreadable: " + str(exc))
            continue
        if "agentType: '" + agent_type + "'" not in text:
            failures.append(relative + " does not launch its workers as agentType " + agent_type)
        if re.search(r"agentType:\s*['\"]general-purpose['\"]", text):
            failures.append(relative + " launches a general-purpose agent")
    return failures


def _offline_research_fanout_smoke(root):
    """Exercise research_fanout prepare and status without a model or network."""
    from research_fanout import prepare, status

    with tempfile.TemporaryDirectory(prefix="elara-doctor-research-") as temporary:
        fanout_dir = Path(temporary) / "fanout"
        (fanout_dir / "briefs").mkdir(parents=True)
        (fanout_dir / "briefs" / "unit-1.md").write_text(
            "# Doctor fixture brief\nNo network; return {\"complete\": true}.\n", encoding="utf-8"
        )
        spec = {
            "contract_version": "1.0",
            "fanout_id": "doctor-offline-fixture",
            "kind": "doctor_fixture",
            "time_box_minutes": 1,
            "max_attempts": 1,
            "assignments": [{"assignment_id": "unit-1", "brief": "briefs/unit-1.md"}],
        }
        (fanout_dir / "spec.json").write_text(json.dumps(spec), encoding="utf-8")
        prepare(fanout_dir)
        before = status(fanout_dir, include_pending=True, record_launch=True)
        if before["pending"] != 1 or before.get("launches_recorded") != 1:
            raise ValueError("research fan-out status did not report one pending launch")
        return_path = Path(before["pending_assignments"][0]["return_path"])
        return_path.write_text(
            json.dumps({"assignment_id": "unit-1", "complete": True, "result": {}}),
            encoding="utf-8",
        )
        after = status(fanout_dir, include_pending=True)
        if after["complete"] != 1 or after["pending"] != 0 or after["exhausted"] != 0:
            raise ValueError("research fan-out status did not reconcile one complete return")
    return {"ready": True, "model_calls": 0, "network_calls": 0, "assignments": 1}


def build_report(root, platform="auto", smoke=True):
    """Return a complete machine-readable preflight report."""
    root = root.resolve()
    failures = []
    for relative in DISCOVERY_SURFACES:
        alternatives = relative if isinstance(relative, tuple) else (relative,)
        if not any((root / candidate).is_file() for candidate in alternatives):
            failures.append("missing " + " or ".join(alternatives))
    worker_agent_failures = _worker_agent_failures(root)
    failures.extend(worker_agent_failures)
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
    document_dependency, document_dependency_failures = _document_dependency_report()
    failures.extend(document_dependency_failures)
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

    research_smoke_report = {"ready": False, "skipped": not smoke}
    if smoke:
        try:
            research_smoke_report = _offline_research_fanout_smoke(root)
            research_smoke_report["skipped"] = False
        except Exception as exc:  # fail closed and preserve a useful diagnostic
            research_smoke_report = {"ready": False, "skipped": False, "error": str(exc)}
            failures.append("offline research fan-out smoke test failed: " + str(exc))

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
        "document_dependency": document_dependency,
        "platform_selection": platform,
        "hosts": hosts,
        "checks": {
            "discovery_surfaces": "passed" if not any(
                failure.startswith("missing ") for failure in failures
            ) else "failed",
            "stage_count": stage_count,
            "repository_contract": "passed" if not repository_failures else "failed",
            "worker_agent_definitions": "passed" if not worker_agent_failures else "failed",
            "offline_fanout_smoke": smoke_report,
            "offline_research_fanout_smoke": research_smoke_report,
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
    document_dependency = report["document_dependency"]
    if document_dependency["installed"]:
        print("CHECK: python-docx " + str(document_dependency["version"]))
    else:
        print("CHECK: python-docx not installed")
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
    research_smoke = report["checks"].get("offline_research_fanout_smoke", {})
    if research_smoke.get("skipped"):
        print("CHECK: offline research fan-out smoke skipped")
    elif research_smoke.get("ready"):
        print("CHECK: offline research fan-out smoke passed")
    else:
        print("CHECK: offline research fan-out smoke failed")
    if report["checks"].get("worker_agent_definitions") == "passed":
        print(
            "CHECK: restricted worker definitions and saved workflows present "
            "(Claude: elr-worker, elr-research-worker; Codex: elr_worker, elr_research_worker)"
        )
    else:
        print("CHECK: restricted worker definitions or saved workflows missing or unrestricted")

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
