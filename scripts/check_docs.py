"""Check Markdown discovery surfaces, links, fences, and release placeholders."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
ALLOWED_SCHEMES = ("http://", "https://", "mailto:")
FORBIDDEN_PLACEHOLDERS = (
    "github.com/" + "USERNAME",
    "TODO:" + " Replace",
    "TODO:" + " describe",
)

# The content scan covers only surfaces the kit ships and maintains. Everything
# else — researcher content under project/ (inputs, artifacts, runs, corpus) and,
# when the kit is installed into a researcher's own folder by
# scripts/bootstrap.py, the researcher's own notes, drafts, and README at the
# root — must never fail kit validation, whatever its encoding or formatting.
KIT_MARKDOWN_DIRECTORIES = ("workflow", "tests", "scripts", ".claude/workflows")
# Only ELARA's own skill directories are kit surfaces; a researcher's other
# skills in the same .agents/ or .claude/ tree are theirs and are not scanned.
KIT_SKILL_ROOTS = (".agents/skills", ".claude/skills")
KIT_TOP_LEVEL_FILES = ("AGENTS.md", "CLAUDE.md", "PIPELINE.md")
KIT_README_TITLE = "# ELARA: Empirical Legal Analysis with Research Agents"
KIT_PROJECT_FILES = (
    "project/README.md",
    "project/inputs/README.md",
    "project/PROJECT_STATE.md",
    "project/DECISIONS.md",
    "project/RUN_LEDGER.md",
    "project/DEVIATIONS.md",
)


def _kit_readmes(root: Path) -> list[Path]:
    """The kit README, wherever bootstrap put it: README.md when that is the kit's own file,
    ELARA_README.md when the researcher's README.md was kept."""
    paths: list[Path] = []
    readme = root / "README.md"
    if readme.is_file():
        try:
            if readme.read_text(encoding="utf-8-sig").lstrip().startswith(KIT_README_TITLE):
                paths.append(readme)
        except UnicodeDecodeError:
            pass
    alias = root / "ELARA_README.md"
    if alias.is_file():
        paths.append(alias)
    return paths


def _kit_skill_files(root: Path, pattern: str) -> list[Path]:
    paths: list[Path] = []
    for skills_root in KIT_SKILL_ROOTS:
        paths.extend(sorted((root / skills_root).glob(f"elr*/{pattern}")))
    return paths


def _kit_markdown(root: Path) -> list[Path]:
    paths = [root / name for name in KIT_TOP_LEVEL_FILES]
    paths.extend(_kit_readmes(root))
    for directory in KIT_MARKDOWN_DIRECTORIES:
        paths.extend(sorted(path for path in (root / directory).rglob("*.md")))
    paths.extend(_kit_skill_files(root, "**/*.md"))
    paths.extend(root / relative for relative in KIT_PROJECT_FILES)
    return [path for path in paths if path.is_file() and ".git" not in path.parts]


def _local_target(raw: str) -> str | None:
    target = raw.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " \"" in target:
        target = target.split(" \"", 1)[0]
    if not target or target.startswith(("#", *ALLOWED_SCHEMES)):
        return None
    return unquote(target.split("#", 1)[0])


def _skill_frontmatter(path: Path) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0] != "---":
        return {}, [f"{path}: skill is missing opening frontmatter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, [f"{path}: skill is missing closing frontmatter"]
    meta: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:end], 2):
        if not line.strip():
            continue
        if ":" not in line:
            errors.append(f"{path}:{line_number}: malformed skill frontmatter")
            continue
        key, value = line.split(":", 1)
        if key in meta:
            errors.append(f"{path}:{line_number}: duplicate skill key {key}")
        value = value.strip()
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                errors.append(f"{path}:{line_number}: invalid quoted skill value")
        meta[key] = value
    return meta, errors


def validate_docs(root: Path) -> list[str]:
    errors: list[str] = []
    for path in _kit_markdown(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{path}: not valid UTF-8")
            continue
        if sum(1 for line in text.splitlines() if line.lstrip().startswith("```")) % 2:
            errors.append(f"{path}: unbalanced fenced code block")
        for placeholder in FORBIDDEN_PLACEHOLDERS:
            if placeholder in text:
                errors.append(f"{path}: unresolved release placeholder {placeholder!r}")
        for match in LINK_RE.finditer(text):
            target = _local_target(match.group(1))
            if target is None:
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                errors.append(f"{path}: broken local link {match.group(1)!r}")

    # Only the kit's own elr* skills are checked; a researcher's other skills in
    # the same folder are theirs.
    for path in _kit_skill_files(root, "SKILL.md"):
        meta, skill_errors = _skill_frontmatter(path)
        errors.extend(skill_errors)
        if meta.get("name") != path.parent.name:
            errors.append(f"{path}: skill name must match its directory")
        if not meta.get("description"):
            errors.append(f"{path}: skill description is required")

    for directory in sorted((root / ".agents" / "skills").glob("elr*")):
        if not directory.is_dir():
            continue
        yaml_path = directory / "agents" / "openai.yaml"
        if not yaml_path.exists():
            errors.append(f"{yaml_path}: missing Codex skill interface metadata")
            continue
        yaml = yaml_path.read_text(encoding="utf-8")
        for field in ("interface:", "display_name:", "short_description:", "default_prompt:", "policy:", "allow_implicit_invocation:"):
            if field not in yaml:
                errors.append(f"{yaml_path}: missing {field}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate_docs(args.root.resolve())
    if errors:
        print("Documentation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Documentation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
