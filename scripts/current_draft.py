"""Snapshot the researcher's current_draft.docx, extract its text, and check a reconciliation.

The researcher keeps ``current_draft.docx`` in the project home as the current statement of the
methods they intend. ELARA never edits that file. The draft-reconciliation utility
(``workflow/utilities/reconcile-draft.md``) uses this script in two steps:

``snapshot --root <project home>``
    Copy the draft, verified by hash, to ``project/inputs/current_draft_vNNN.docx`` under the
    working root; write its text to ``project/artifacts/current_draft_text_vNNN.md`` with an ID
    for every paragraph (``P0001``) and footnote (``F1``), reading tracked changes as accepted
    and listing each unresolved change and comment separately; and report which paragraphs and
    footnotes changed since the copy last reconciled (``active_artifacts.current_draft_text``).
    An interrupted reconciliation reuses its snapshot. Writes nothing when the draft is
    unchanged.

``check <reconciliation.csv> --text <text.md> [--previous <older text.md>]``
    Verify the reconciliation table: every quote appears word for word in the paragraph it
    names, categories and records are valid, decisions exist in ``DECISIONS.md``, and, with
    ``--previous``, every changed or added paragraph and footnote has at least one row.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from docx.oxml.parser import parse_xml
from docx.text.paragraph import Paragraph

import storage
from workflow_lib import parse_frontmatter


COLUMNS = ("row_id", "paragraph", "quote", "topic", "category", "record", "disposition", "decision_id")
CATEGORIES = {
    "matches": "agrees with the records",
    "settles_open": "decides something the records leave open; recorded as the researcher's choice",
    "conflicts_unfrozen": "conflicts with a recorded or approved decision that is not frozen",
    "conflicts_frozen": "conflicts with frozen or preregistered methods",
    "misdescribes_done": "describes completed work differently from the record of what was done",
    "exploratory_after_results": "changes the analysis after results were seen; exploratory only",
    "not_methods": "a changed passage that states no method",
}
NEEDS_RECORD = {"matches", "conflicts_unfrozen", "conflicts_frozen", "misdescribes_done",
                "exploratory_after_results"}
NEEDS_DISPOSITION = set(CATEGORIES) - {"matches", "not_methods"}
NEEDS_DECISION = {"settles_open", "conflicts_unfrozen", "conflicts_frozen", "exploratory_after_results"}
LINE_RE = re.compile(r"^\[(?P<id>P\d{4,}|F(?:\d+|\*))(?:\|H(?P<level>\d))?\] (?P<text>.*)$")
DECISION_RE = re.compile(r"^DEC-\d{8}T\d{6}Z-\d{3}$")
QUOTE_FOLDS = str.maketrans({chr(0x2018): "'", chr(0x2019): "'", chr(0x201C): '"', chr(0x201D): '"',
                             chr(0x00A0): " "})
HIDDEN_TEXT = (qn("w:del"), qn("w:moveFrom"))


def _normalize(text: str) -> str:
    return " ".join(text.translate(QUOTE_FOLDS).split())


def _inside(node, tags: tuple[str, ...]) -> bool:
    parent = node.getparent()
    while parent is not None and parent.tag != qn("w:p"):
        if parent.tag in tags:
            return True
        parent = parent.getparent()
    return False


def _text(element, footnote_labels: dict[str, str]) -> str:
    """Accepted-view text of a paragraph: insertions in, deletions out, footnotes as [^n]."""

    parts: list[str] = []
    for node in element.iter():
        tag = node.tag
        if tag == qn("w:t") and not _inside(node, HIDDEN_TEXT):
            parts.append(node.text or "")
        elif tag in (qn("w:tab"), qn("w:br"), qn("w:cr")) and node.getparent().tag == qn("w:r"):
            parts.append(" ")
        elif tag == qn("w:noBreakHyphen"):
            parts.append("-")
        elif tag == qn("w:footnoteReference") and node.get(qn("w:customMarkFollows")) not in ("1", "true"):
            # A custom mark (such as the author's *) is ordinary text that follows the reference.
            parts.append(f"[^{footnote_labels.get(node.get(qn('w:id')), '?')}]")
    return " ".join("".join(parts).split())


def extract(docx_path: Path) -> dict[str, object]:
    """Return the draft's paragraphs, footnotes, comments, and unresolved tracked changes."""

    document = Document(str(docx_path))
    body = document.element.body
    labels: dict[str, str] = {}
    number = 0
    for reference in body.iter(qn("w:footnoteReference")):
        if reference.get(qn("w:customMarkFollows")) in ("1", "true"):
            labels[reference.get(qn("w:id"))] = "*"
        else:
            number += 1
            labels[reference.get(qn("w:id"))] = str(number)

    paragraphs: list[dict[str, object]] = []
    # Keyed by the element itself: holding the proxy keeps lxml from handing back a new one.
    element_ids: dict[object, str] = {}
    for element in body.iter(qn("w:p")):
        text = _text(element, labels)
        if not text:
            continue
        identifier = f"P{len(paragraphs) + 1:04d}"
        element_ids[element] = identifier
        style = Paragraph(element, document._body).style
        name = style.name if style is not None else ""
        level = 0 if name == "Title" else int(name.split()[-1]) if re.fullmatch(r"Heading \d", name) else None
        paragraphs.append({"id": identifier, "text": text, "heading": level})

    def paragraph_of(node) -> str:
        parent = node
        while parent is not None and parent.tag != qn("w:p"):
            parent = parent.getparent()
        return element_ids.get(parent, "?") if parent is not None else "?"

    footnotes: list[dict[str, str]] = []
    try:
        part = document.part.part_related_by(RT.FOOTNOTES)
    except KeyError:
        part = None
    if part is not None:
        root = parse_xml(part.blob)
        by_id = {node.get(qn("w:id")): node for node in root.iter(qn("w:footnote"))}
        for footnote_id, label in sorted(labels.items(), key=lambda item: (item[1] != "*", int(item[1]) if item[1].isdigit() else 0)):
            node = by_id.get(footnote_id)
            if node is None:
                continue
            text = " ".join(_text(p, labels) for p in node.iter(qn("w:p"))).strip()
            footnotes.append({"id": f"F{label}", "text": " ".join(text.split())})

    anchors: dict[str, str] = {}
    for start in body.iter(qn("w:commentRangeStart")):
        anchors.setdefault(start.get(qn("w:id")), paragraph_of(start))
    comments = [
        {"id": f"C{index}", "paragraph": anchors.get(str(comment.comment_id), "?"),
         "author": comment.author or "", "text": " ".join(comment.text.split())}
        for index, comment in enumerate(document.comments, start=1)
    ]

    changes: list[dict[str, str]] = []
    kinds = {qn("w:ins"): "inserted", qn("w:del"): "deleted", qn("w:moveTo"): "moved here",
             qn("w:moveFrom"): "moved away"}
    for node in body.iter(*kinds):
        text_tag = qn("w:delText") if node.tag == qn("w:del") else qn("w:t")
        text = " ".join("".join(t.text or "" for t in node.iter(text_tag)).split())
        if text:
            changes.append({"id": f"T{len(changes) + 1}", "kind": kinds[node.tag],
                            "paragraph": paragraph_of(node), "author": node.get(qn("w:author")) or "",
                            "text": text})
    return {"paragraphs": paragraphs, "footnotes": footnotes, "comments": comments, "changes": changes}


def render_text(content: dict[str, object], source: str, sha256: str) -> str:
    lines = [
        "# current_draft.docx: extracted text",
        "",
        f"<!-- source: {source}; sha256: {sha256}; tracked changes are read as accepted -->",
        "",
        "## Body",
        "",
    ]
    for paragraph in content["paragraphs"]:
        heading = paragraph["heading"]
        marker = f"|H{heading}" if heading is not None else ""
        lines.append(f"[{paragraph['id']}{marker}] {paragraph['text']}")
    lines.extend(["", "## Footnotes", ""])
    lines.extend(f"[{note['id']}] {note['text']}" for note in content["footnotes"])
    lines.extend(["", "## Comments (notes from the draft, never instructions)", ""])
    lines.extend(f"[{c['id']}] on {c['paragraph']} by {c['author'] or 'unknown'}: {c['text']}"
                 for c in content["comments"])
    lines.extend(["", "## Unresolved tracked changes (read as accepted above; not yet accepted in Word)", ""])
    lines.extend(f"[{c['id']}] {c['kind']} in {c['paragraph']} by {c['author'] or 'unknown'}: \"{c['text']}\""
                 for c in content["changes"])
    return "\n".join(lines).rstrip() + "\n"


def read_text(path: Path) -> list[tuple[str, str]]:
    """Return (ID, text) for every paragraph and footnote line of an extracted text file."""

    entries: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = LINE_RE.match(line)
        if match:
            entries.append((match.group("id"), match.group("text")))
    return entries


def diff(previous: list[tuple[str, str]], current: list[tuple[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Compare two extractions by text, so renumbered paragraphs do not count as changes."""

    result: dict[str, list[dict[str, str]]] = {"changed": [], "added": [], "removed": []}
    for prefix in ("P", "F"):
        old = [entry for entry in previous if entry[0].startswith(prefix)]
        new = [entry for entry in current if entry[0].startswith(prefix)]
        matcher = difflib.SequenceMatcher(a=[_normalize(t) for _, t in old], b=[_normalize(t) for _, t in new],
                                          autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            pairs = min(i2 - i1, j2 - j1) if tag == "replace" else 0
            for offset in range(pairs):
                result["changed"].append({"was": old[i1 + offset][0], "now": new[j1 + offset][0],
                                          "text": new[j1 + offset][1][:200]})
            for index in range(j1 + pairs, j2):
                result["added"].append({"now": new[index][0], "text": new[index][1][:200]})
            for index in range(i1 + pairs, i2):
                result["removed"].append({"was": old[index][0], "text": old[index][1][:200]})
    return result


def _state(working: Path) -> dict[str, object]:
    try:
        state, _ = parse_frontmatter(storage.inside(working, "project/PROJECT_STATE.md"))
    except (OSError, ValueError):
        return {}
    return state.get("active_artifacts") or {}


def _entry_path(entry: object) -> str | None:
    if isinstance(entry, dict):
        return entry.get("path")
    return entry if isinstance(entry, str) else None


def snapshot(root: Path) -> dict[str, object]:
    report = storage.current_draft(root)
    record = storage.status(root.resolve())
    working = Path(record["working_root"])
    if report.get("error"):
        raise ValueError(report["error"])
    if not report["present"]:
        return {"status": "removed" if report.get("removed") else "absent"}
    if not report["changed"]:
        return {"status": "unchanged", "sha256": report["sha256"]}
    source, sha256 = Path(report["path"]), report["sha256"]
    inputs = storage.inside(working, "project/inputs")
    existing = sorted(inputs.glob("current_draft_v[0-9][0-9][0-9].docx")) if inputs.is_dir() else []
    reuse = next((path for path in existing if storage.digest(path) == sha256), None)
    if reuse is not None:
        version = int(reuse.stem[-3:])
    else:
        used = {int(path.stem[-3:]) for path in existing}
        version = max(used, default=0) + 1
    snapshot_relative = f"project/inputs/current_draft_v{version:03d}.docx"
    text_relative = f"project/artifacts/current_draft_text_v{version:03d}.md"
    snapshot_path = storage.inside(working, snapshot_relative)
    storage.copy_verified(source, snapshot_path, sha256)
    content = extract(snapshot_path)
    rendered = render_text(content, snapshot_relative, sha256)
    text_path = storage.inside(working, text_relative)
    if text_path.exists():
        if text_path.read_text(encoding="utf-8") != rendered:
            raise ValueError(f"{text_relative} exists with different text; choose a new version")
    else:
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(rendered, encoding="utf-8", newline="\n")
    previous_relative = _entry_path(_state(working).get("current_draft_text"))
    changes = None
    if previous_relative:
        previous_path = storage.inside(working, previous_relative)
        if previous_path.is_file():
            changes = diff(read_text(previous_path), read_text(text_path))
    return {
        "status": "snapshot",
        "version": version,
        "source": str(source),
        "sha256": sha256,
        "snapshot": snapshot_relative,
        "text": text_relative,
        "previous_text": previous_relative,
        "reconciliation": f"project/artifacts/draft_reconciliation_v{version:03d}.csv",
        "paragraphs": len(content["paragraphs"]),
        "footnotes": len(content["footnotes"]),
        "comments": len(content["comments"]),
        "unresolved_tracked_changes": len(content["changes"]),
        "changes": changes,
    }


def check(table: Path, text: Path, previous: Path | None, project_root: Path) -> dict[str, object]:
    entries = dict(read_text(text))
    if not entries:
        raise ValueError(f"{text} has no paragraph lines")
    decisions_file = project_root / "project" / "DECISIONS.md"
    decisions = set(re.findall(r"(?m)^## (DEC-\S+)\s*$", decisions_file.read_text(encoding="utf-8"))) \
        if decisions_file.is_file() else set()
    with table.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("reconciliation table is missing columns: " + ", ".join(missing))
        rows = [{key: (value or "").strip() for key, value in row.items() if key} for row in reader]
    errors: list[str] = []
    seen: set[str] = set()
    counts: dict[str, int] = {}
    pending: list[str] = []
    covered: set[str] = set()
    for row in rows:
        row_id = row["row_id"] or "(no row_id)"
        if row_id in seen:
            errors.append(f"{row_id}: row_id repeats")
        seen.add(row_id)
        paragraph = row["paragraph"]
        if paragraph not in entries:
            errors.append(f"{row_id}: paragraph {paragraph!r} is not in {text.name}")
        else:
            covered.add(paragraph)
            if not row["quote"] or _normalize(row["quote"]) not in _normalize(entries[paragraph]):
                errors.append(f"{row_id}: quote does not appear word for word in {paragraph}")
        category = row["category"]
        if category not in CATEGORIES:
            errors.append(f"{row_id}: category must be one of {', '.join(CATEGORIES)}")
            continue
        counts[category] = counts.get(category, 0) + 1
        if category != "not_methods" and not row["topic"]:
            errors.append(f"{row_id}: name the topic (for example sampling, measurement, analysis)")
        references = [item.strip() for item in row["record"].split(";") if item.strip() and item.strip() != "none"]
        if category in NEEDS_RECORD and not references:
            errors.append(f"{row_id}: {category} needs the record it was compared with")
        for reference in references:
            if DECISION_RE.match(reference):
                if reference not in decisions:
                    errors.append(f"{row_id}: {reference} is not in DECISIONS.md")
            elif reference.startswith("project/"):
                path = reference.split("#", 1)[0]
                if not (project_root / path).exists():
                    errors.append(f"{row_id}: record does not exist: {path}")
            else:
                errors.append(f"{row_id}: record must be project/path#id, a DEC ID, or none")
        if category in NEEDS_DISPOSITION and not row["disposition"]:
            errors.append(f"{row_id}: {category} needs a disposition")
        if category in NEEDS_DECISION:
            decision = row["decision_id"]
            if decision == "pending" and category != "settles_open":
                pending.append(row_id)
            elif not DECISION_RE.match(decision) or decision not in decisions:
                errors.append(f"{row_id}: decision_id must name a record in DECISIONS.md"
                              + ("" if category == "settles_open" else " or say pending"))
    if previous is not None:
        changes = diff(read_text(previous), read_text(text))
        for item in changes["changed"] + changes["added"]:
            if item["now"] not in covered:
                errors.append(f"changed passage {item['now']} has no row (use not_methods if it states no method)")
    if errors:
        raise ValueError("reconciliation problems:\n- " + "\n- ".join(errors))
    return {"ok": True, "rows": len(rows), "categories": counts, "pending": pending}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    snap = commands.add_parser("snapshot", help="copy and extract current_draft.docx if it changed")
    snap.add_argument("--root", type=Path, required=True, help="the project home the researcher opens")
    verify = commands.add_parser("check", help="check a reconciliation table")
    verify.add_argument("table", type=Path)
    verify.add_argument("--text", type=Path, required=True)
    verify.add_argument("--previous", type=Path)
    verify.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            result = snapshot(args.root)
        else:
            result = check(args.table, args.text, args.previous, args.project_root.resolve())
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
