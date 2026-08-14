"""Preflight check: confirm this computer and this kit copy are ready to use.

Run it as:

    python scripts/doctor.py

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
from pathlib import Path  # noqa: E402


DISCOVERY_SURFACES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "PIPELINE.md",
    "workflow/shared/guardrails.md",
    "workflow/shared/artifact-contract.md",
    "workflow/templates/preregistration_template.md",
    "project/PROJECT_STATE.md",
    ".agents/skills/elr/SKILL.md",
    ".claude/skills/elr/SKILL.md",
)

EXPECTED_STAGE_COUNT = 20


def run_doctor(root):
    """Return a list of failure messages; an empty list means the kit is healthy."""

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
    # Everything substantive is delegated to the repository validator; this
    # script only adds the version gate and the surface-existence checks above.
    from validate_workflow import validate_repository
    from workflow_lib import FrontmatterError

    try:
        failures.extend(validate_repository(root))
    except (FrontmatterError, ValueError, UnicodeDecodeError, OSError) as exc:
        failures.append(str(exc))
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    failures = run_doctor(root)
    if failures:
        print("FAIL: this kit copy has " + str(len(failures)) + " problem(s):")
        for failure in failures:
            print("- " + str(failure))
        return 1
    print("PASS: Python and the kit look ready. Open your agent and run /elr to begin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
