"""Validate and render an illustrative law review article draft from one Markdown source.

The draft-article utility (``workflow/utilities/draft-article.md``) writes the source; this
builder checks its structure, footnotes, citations, values, and cross-references, then renders
either a Word document on the bundled law-review template (real footnotes, a contents page, and
law-review Part numbering) or a Markdown copy for review. It never overwrites an existing file.

Source conventions (``workflow/templates/article_draft_template.md`` shows them in place):

- ``#`` Parts, ``##`` subparts, ``###`` and ``####`` deeper levels. ``# Abstract``,
  ``# Introduction``, ``# Conclusion``, and ``# Appendix A. Title`` take those roles; every
  other top-level heading is a numbered Part. ``{#anchor}`` after a heading names it.
- ``[^label]`` marks a footnote; ``[^label]: text`` defines it anywhere in the source.
- ``{{src:ID}}`` ties a citation in a footnote to the source register; ``{{value:key}}``
  inserts a number from the values table; ``{{part:anchor}}``, ``{{display:ID}}``, and
  ``{{fn:label}}`` insert "Part II.A", "Table 2", and a footnote number.
- ``[[citation needed: claim]]`` and ``[[pending: what goes here]]`` stay visible and
  highlighted; ``[[note: text]]`` becomes a Word comment for the researcher.
- ``!display table|project/path#ID|caption`` places a verified table, figure, or equation;
  ``!pending table|ID|caption`` reserves a numbered place for one still to come.
- ``*italic*``, ``**bold**``, ``[small caps]{.sc}``, and ``> `` block quotations.
"""

from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.image.image import Image
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.oxml.parser import parse_xml
from docx.shared import Inches
from docx.text.paragraph import Paragraph
from lxml import etree

from build_skeleton_draft import (  # noqa: I001 - shared Word and path helpers
    DISPLAY_SUFFIXES,
    PROJECT_REF_RE,
    WHITE,
    Display,
    _add_toc_field,
    _clear_body_after,
    _content_sensitive_widths,
    _content_width_dxa,
    _embed_alt_text,
    _load_template_without_prototype_comments,
    _load_word_profiles,
    _read_equation,
    _read_table,
    _replace_header_placeholder,
    _replace_visible_text,
    _repeat_header,
    _repository_root,
    _request_field_updates,
    _resolve_project_path,
    _roman,
    _set_article_table_geometry,
    _set_cell_shading,
    _sha256,
)


SUPPORTED_SUFFIXES = (".docx", ".md")
SUPPORTED_WORD_TEMPLATES = ("law_review_v1",)
REQUIRED_METADATA = ("title", "target_venue", "sources", "values", "source_versions")
OPTIONAL_METADATA = (
    "authors",
    "author_note",
    "running_title",
    "word_template",
    "abstract_word_limit",
    "draft_label",
)
DEFAULT_ABSTRACT_WORD_LIMIT = 250
DEFAULT_DRAFT_LABEL = (
    "This is an illustrative draft prepared from the project's research records for the "
    "author to rewrite; it is not for circulation."
)
SOURCE_COLUMNS = ("source_id", "citation", "url", "access_date", "local_path", "sha256", "origin")
VALUE_COLUMNS = ("key", "value", "status", "source", "description")
VALUE_STATUSES = ("verified", "pending")
DISPLAY_KINDS = ("table", "figure", "equation")
TEMPLATE_MARKER = "TODO-DRAFT"

EM_DASH = chr(0x2014)
EN_DASH = chr(0x2013)
SECTION_SIGN = chr(0xA7)
RIGHT_QUOTE = chr(0x2019)

COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+\{#([A-Za-z][A-Za-z0-9_-]*)\})?\s*$")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$")
DISPLAY_LINE_RE = re.compile(r"^!(display|pending)\s+(.+?)\s*$")
APPENDIX_RE = re.compile(r"^(?i:appendix)(?:\s+[A-Z])?(?:\s*[.:" + EM_DASH + r"-]\s*|\s+|$)(.*)$")
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
INLINE_RE = re.compile(
    r"(?P<escape>\\[\\*\[\]{}])"
    r"|\[\[(?P<bkind>[^:\]\[]+):\s*(?P<btext>(?:(?!\]\]).)+?)\s*\]\]"
    r"|\{\{(?P<ckind>[a-z]+):(?P<carg>[^{}\s]+)\}\}"
    r"|\[\^(?P<fn>[^\]\s]+)\]"
    r"|\[(?P<sc>[^\[\]]+)\]\{\.sc\}"
    r"|(?P<bold>\*\*)"
    r"|(?P<ital>\*)"
)
WORD_RE = re.compile(r"[\w" + RIGHT_QUOTE + r"'-]+")

# Footnote classification. A footnote that cites nothing must not look like a citation.
SIGNAL_START_RE = re.compile(
    r"^\W*(?:see|e\.g\.|cf\.|compare|but see|but cf\.|accord|contra|id\.|ibid)\b", re.IGNORECASE
)
EXTERNAL_CITATION_RE = re.compile(
    r"\sv\.\s|U\.S\.C\.|\b\d+\s+U\.S\.\s+\d|\bF\.\s?(?:Supp\.\s?)?(?:\d[a-z]{1,2}\s)?\d"
    r"|S\.\s?Ct\.|L\.\s?Rev\.|\bL\.J\.|\bStat\.\s|C\.F\.R\.|Fed\.\s?Reg\.|https?://|supra\W+notes?\b",
    re.IGNORECASE,
)
ID_START_RE = re.compile(r"^\W*id\.", re.IGNORECASE)
SUPRA_NOTE_RE = re.compile(r"supra\W+notes?\s+\{\{fn:([^{}\s]+)\}\}", re.IGNORECASE)

# Style warnings for the self-review. They never block a build.
LONG_SENTENCE_WORDS = 40
LONG_PARAGRAPH_WORDS = 220
HYPE_TERMS = (
    "groundbreaking", "revolutionary", "unprecedented", "paradigm shift", "game-changer",
    "game changer", "seismic", "cutting-edge", "state-of-the-art", "delve", "delves",
    "tapestry", "landscape", "underscore", "underscores", "pivotal", "crucial", "utilize",
    "utilizes", "leverage", "leverages", "it is important to note", "it is worth noting",
    "needless to say", "very", "extremely", "incredibly", "remarkably", "dramatically",
    "profoundly", "plethora", "myriad", "stunning", "striking", "shed light", "sheds light",
)
HYPE_RE = re.compile(r"\b(?:" + "|".join(re.escape(term) for term in HYPE_TERMS) + r")\b", re.I)
ACRONYM_RE = re.compile(r"(?<![\w(])\(?\b([A-Z]{2,6})s?\b")
ROMAN_RE = re.compile(r"^M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$")
NUMBER_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?%?")
NUMBER_PREFIX_RE = re.compile(
    r"(?:" + SECTION_SIGN + r"{1,2}|\b(?:section|sections|rule|rules|title|article|amendment|"
    r"chapter|no\.|part|note|notes|table|figure|equation|appendix))\s*$",
    re.IGNORECASE,
)
ABBREVIATIONS = ("e.g.", "i.e.", "v.", "U.S.", "Mr.", "Ms.", "Dr.", "No.", "et al.", "cf.", "Id.", "id.")


@dataclass
class Heading:
    level: int
    title: str
    anchor: str | None
    role: str
    line: int
    visible: str = ""
    ref: str = ""
    letter: str = ""
    order: int = 0


@dataclass
class Block:
    kind: str  # paragraph, quote, display, pending
    text: str
    heading: Heading
    line: int
    index: int = 0
    display: Display | None = None
    pending: tuple[str, str, str] | None = None


@dataclass
class Footnote:
    label: str
    text: str
    line: int
    number: int = 0


@dataclass
class Piece:
    kind: str  # text, fnref
    text: str = ""
    italic: bool = False
    bold: bool = False
    smallcaps: bool = False
    highlight: bool = False
    label: str = ""


@dataclass
class Lexed:
    pieces: list[Piece]
    sources: list[str] = field(default_factory=list)
    citation_needed: int = 0
    internal_refs: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def plain(self) -> str:
        return "".join(piece.text for piece in self.pieces if piece.kind == "text")


@dataclass
class Draft:
    metadata: dict[str, str]
    headings: list[Heading]
    blocks: list[Block]
    footnotes: dict[str, Footnote]


class Context:
    """Resolves tokens and collects what the manifest reports."""

    def __init__(
        self,
        draft: Draft,
        sources: dict[str, dict[str, str]],
        values: dict[str, dict[str, str]],
    ) -> None:
        self.draft = draft
        self.sources = sources
        self.values = values
        self.anchors = {heading.anchor: heading for heading in draft.headings if heading.anchor}
        self.displays: dict[str, tuple[str, int]] = {}
        self.errors: list[str] = []
        self.placeholders: list[dict[str, str]] = []
        self.notes: list[dict[str, str]] = []
        self.values_used: dict[str, list[str]] = {}
        self.sources_used: dict[str, list[str]] = {}

    def lex(
        self,
        text: str,
        location: str,
        *,
        allow_footnotes: bool = False,
        allow_sources: bool = False,
        allow_notes: bool = False,
    ) -> Lexed:
        result = Lexed(pieces=[])
        italic = False
        bold = False
        position = 0

        def literal(value: str) -> None:
            if not value:
                return
            for stray in ("[[", "]]", "{{", "}}"):
                if stray in value:
                    self.errors.append(
                        f"{location}: unrecognized markup near {stray!r}; use [[citation needed: ...]], "
                        "[[pending: ...]], [[note: ...]], or a {{src|value|part|display|fn:...}} token"
                    )
                    break
            result.pieces.append(Piece("text", value, italic=italic, bold=bold))

        def trim_before_hidden() -> None:
            # A hidden token ({{src:...}}, [[note: ...]]) takes the space before it with it.
            if result.pieces and result.pieces[-1].kind == "text" and not result.pieces[-1].highlight:
                result.pieces[-1].text = result.pieces[-1].text.rstrip(" ")

        def placeholder(kind: str, value: str) -> None:
            shown = f"[[{kind}: {value}]]"
            result.pieces.append(Piece("text", shown, italic=italic, bold=bold, highlight=True))
            self.placeholders.append({"kind": "citation_needed" if kind == "citation needed" else "pending_text",
                                      "location": location, "text": value})

        for match in INLINE_RE.finditer(text):
            literal(text[position : match.start()])
            position = match.end()
            if match.group("escape"):
                result.pieces.append(Piece("text", match.group("escape")[1], italic=italic, bold=bold))
            elif match.group("bkind"):
                kind = match.group("bkind").strip().casefold()
                value = " ".join(match.group("btext").split())
                if kind in ("citation needed", "pending"):
                    if kind == "citation needed":
                        result.citation_needed += 1
                    placeholder(kind, value)
                elif kind == "note":
                    trim_before_hidden()
                    if not allow_notes:
                        self.errors.append(f"{location}: [[note: ...]] is allowed only in body paragraphs")
                    result.notes.append(value)
                    self.notes.append({"location": location, "text": value})
                else:
                    self.errors.append(f"{location}: unknown bracket note [[{kind}: ...]]")
            elif match.group("ckind"):
                if match.group("ckind") == "src":
                    trim_before_hidden()
                self._token(match.group("ckind"), match.group("carg"), location, result, allow_sources,
                            italic, bold, placeholder)
            elif match.group("fn"):
                label = match.group("fn")
                if not allow_footnotes:
                    self.errors.append(f"{location}: footnote [^{label}] is not allowed here")
                elif label not in self.draft.footnotes:
                    self.errors.append(f"{location}: footnote [^{label}] has no definition")
                result.pieces.append(Piece("fnref", label=label))
            elif match.group("sc") is not None:
                result.pieces.append(
                    Piece("text", match.group("sc"), italic=italic, bold=bold, smallcaps=True)
                )
            elif match.group("bold"):
                bold = not bold
            elif match.group("ital"):
                italic = not italic
        literal(text[position:])
        trim_before_hidden()
        if italic or bold:
            self.errors.append(f"{location}: unbalanced * or ** emphasis")
        return result

    def _token(self, kind, argument, location, result, allow_sources, italic, bold, placeholder) -> None:
        if kind == "src":
            if not allow_sources:
                self.errors.append(f"{location}: {{{{src:{argument}}}}} belongs in a footnote")
            elif argument not in self.sources:
                self.errors.append(f"{location}: source {argument} is not in the source register")
            else:
                result.sources.append(argument)
                self.sources_used.setdefault(argument, []).append(location)
        elif kind == "value":
            row = self.values.get(argument)
            if row is None:
                self.errors.append(f"{location}: value {argument} is not in the values table")
                return
            self.values_used.setdefault(argument, []).append(location)
            if row["status"] == "verified":
                result.pieces.append(Piece("text", row["value"], italic=italic, bold=bold))
            else:
                placeholder("pending", row["description"])
                self.placeholders[-1]["kind"] = "pending_value"
                self.placeholders[-1]["key"] = argument
        elif kind == "part":
            heading = self.anchors.get(argument)
            if heading is None or not heading.ref:
                self.errors.append(f"{location}: no heading has anchor {{#{argument}}}")
                return
            result.internal_refs += 1
            result.pieces.append(Piece("text", heading.ref, italic=italic, bold=bold))
        elif kind == "display":
            display = self.displays.get(argument)
            if display is None:
                self.errors.append(f"{location}: no display has ID {argument}")
                return
            result.internal_refs += 1
            display_kind, number = display
            shown = f"Equation ({number})" if display_kind == "equation" else f"{display_kind.capitalize()} {number}"
            result.pieces.append(Piece("text", shown, italic=italic, bold=bold))
        elif kind == "fn":
            footnote = self.draft.footnotes.get(argument)
            if footnote is None or not footnote.number:
                self.errors.append(f"{location}: no footnote has label {argument}")
                return
            result.internal_refs += 1
            result.pieces.append(Piece("text", str(footnote.number), italic=italic, bold=bold))
        else:
            self.errors.append(f"{location}: unknown token {{{{{kind}:...}}}}")


# --------------------------------------------------------------------------------------------
# Parsing


def _decode_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid quoted metadata value: {value}") from exc
        if not isinstance(parsed, str):
            raise ValueError("metadata values must be strings")
        return parsed.strip()
    if value.startswith("'") and value.endswith("'") and len(value) >= 2:
        return value[1:-1].replace("''", "'").strip()
    return value


def parse_display_spec(spec: str, line_number: int) -> Display:
    """Parse ``kind|project/path#ID|caption`` with an optional fourth ``|alt text`` for figures."""

    parts = [part.strip() for part in spec.split("|", 3)]
    if len(parts) not in (3, 4) or not all(parts[:3]):
        raise ValueError(f"line {line_number}: use !display kind|project/path#ID|caption[|alt text]")
    kind, reference, caption = parts[0].lower(), parts[1], parts[2]
    alt_text = parts[3] if len(parts) == 4 else None
    if kind not in DISPLAY_KINDS:
        raise ValueError(f"line {line_number}: unsupported display kind {kind}")
    match = PROJECT_REF_RE.fullmatch(reference)
    if not match:
        raise ValueError(f"line {line_number}: display reference must be project/path#ID: {reference}")
    suffix = Path(match.group("path")).suffix.lower()
    if suffix not in DISPLAY_SUFFIXES[kind]:
        raise ValueError(f"line {line_number}: a {kind} cannot come from a {suffix or 'extensionless'} file")
    if alt_text is not None and kind != "figure":
        raise ValueError(f"line {line_number}: alt text is for figures only")
    return Display(kind, reference, match.group("path"), match.group("id"), caption, alt_text)


def _top_role(title: str) -> str:
    folded = title.strip().casefold()
    if folded == "abstract":
        return "abstract"
    if folded == "introduction":
        return "introduction"
    if folded == "conclusion":
        return "conclusion"
    if APPENDIX_RE.match(title.strip()):
        return "appendix"
    return "part"


def parse_source(text: str) -> Draft:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if CONTROL_RE.search(normalized):
        raise ValueError("source contains a control character that Word cannot store")
    lines = normalized.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("source must begin with a metadata block")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise ValueError("metadata block has no closing --- line") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, raw = line.partition(":")
        key = key.strip().lower()
        if not separator or not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ValueError(f"invalid metadata line: {line}")
        if key in metadata:
            raise ValueError(f"duplicate metadata key: {key}")
        if key not in REQUIRED_METADATA and key not in OPTIONAL_METADATA:
            raise ValueError(f"unknown metadata key: {key}")
        metadata[key] = _decode_value(raw)
    missing = [key for key in REQUIRED_METADATA if not metadata.get(key)]
    if missing:
        raise ValueError("missing required metadata: " + ", ".join(missing))

    # Line numbers survive comment removal because comments are blanked line for line.
    body = "\n".join(lines[end + 1 :])
    body = COMMENT_RE.sub(lambda match: "\n" * match.group(0).count("\n"), body)
    if TEMPLATE_MARKER in body or any(TEMPLATE_MARKER in value for value in metadata.values()):
        raise ValueError(f"source still contains {TEMPLATE_MARKER} template markers")

    headings: list[Heading] = []
    blocks: list[Block] = []
    footnotes: dict[str, Footnote] = {}
    paragraph: list[str] = []
    paragraph_kind = "paragraph"
    paragraph_line = 0
    open_footnote: Footnote | None = None
    paragraph_counts: dict[int, int] = {}

    def flush() -> None:
        nonlocal paragraph, paragraph_kind
        if not paragraph:
            return
        if not headings:
            raise ValueError(f"line {paragraph_line}: text appears before the first heading")
        heading = headings[-1]
        paragraph_counts[heading.order] = paragraph_counts.get(heading.order, 0) + 1
        blocks.append(
            Block(paragraph_kind, " ".join(paragraph), heading, paragraph_line,
                  paragraph_counts[heading.order])
        )
        paragraph = []
        paragraph_kind = "paragraph"

    for offset, raw_line in enumerate(body.split("\n")):
        line_number = end + 2 + offset
        stripped = raw_line.strip()
        if not stripped:
            flush()
            open_footnote = None
            continue
        if open_footnote is not None and not (
            HEADING_RE.match(stripped) or FOOTNOTE_DEF_RE.match(stripped) or DISPLAY_LINE_RE.match(stripped)
        ):
            open_footnote.text = f"{open_footnote.text} {stripped}".strip()
            continue
        open_footnote = None
        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            flush()
            level = len(heading_match.group(1))
            if level > 4:
                raise ValueError(f"line {line_number}: headings go at most four levels deep (####)")
            if not headings and level != 1:
                raise ValueError(f"line {line_number}: the first heading must be a top-level # heading")
            if headings and level > headings[-1].level + 1:
                raise ValueError(f"line {line_number}: heading skips a level")
            title = heading_match.group(2).strip()
            if level == 1:
                role = _top_role(title)
            else:
                role = next(item for item in reversed(headings) if item.level == 1).role
            headings.append(Heading(level, title, heading_match.group(3), role, line_number,
                                    order=len(headings) + 1))
            continue
        footnote_match = FOOTNOTE_DEF_RE.match(stripped)
        if footnote_match:
            flush()
            label = footnote_match.group(1)
            if label in footnotes:
                raise ValueError(f"line {line_number}: footnote [^{label}] is defined twice")
            open_footnote = Footnote(label, footnote_match.group(2).strip(), line_number)
            footnotes[label] = open_footnote
            continue
        display_match = DISPLAY_LINE_RE.match(stripped)
        if display_match:
            flush()
            if not headings:
                raise ValueError(f"line {line_number}: a display appears before the first heading")
            heading = headings[-1]
            spec = display_match.group(2)
            if display_match.group(1) == "display":
                display = parse_display_spec(spec, line_number)
                blocks.append(Block("display", spec, heading, line_number, display=display))
            else:
                parts = [part.strip() for part in spec.split("|", 2)]
                if len(parts) != 3 or not all(parts):
                    raise ValueError(f"line {line_number}: use !pending kind|ID|caption")
                kind, identifier, caption = parts
                if kind.lower() not in DISPLAY_KINDS:
                    raise ValueError(f"line {line_number}: unsupported pending display kind {kind}")
                if not IDENTIFIER_RE.fullmatch(identifier):
                    raise ValueError(f"line {line_number}: invalid pending display ID {identifier}")
                blocks.append(Block("pending", spec, heading, line_number,
                                    pending=(kind.lower(), identifier, caption)))
            continue
        kind = "quote" if stripped.startswith(">") else "paragraph"
        content = stripped[1:].strip() if kind == "quote" else stripped
        if paragraph and kind != paragraph_kind:
            flush()
        if not paragraph:
            paragraph_line = line_number
            paragraph_kind = kind
        paragraph.append(content)
    flush()

    if not headings:
        raise ValueError("source has no headings")
    return Draft(metadata, headings, blocks, footnotes)


# --------------------------------------------------------------------------------------------
# Registers


def _read_csv(path: Path, columns: tuple[str, ...], label: str) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(name.strip() for name in (reader.fieldnames or ()))
        missing = [column for column in columns if column not in header]
        if missing:
            raise ValueError(f"{label} is missing columns: {', '.join(missing)}")
        rows = [
            {key.strip(): (value or "").strip() for key, value in row.items() if key is not None}
            for row in reader
        ]
    if any(CONTROL_RE.search(value) for row in rows for value in row.values()):
        raise ValueError(f"{label} contains a control character that Word cannot store")
    return rows


def load_sources(path: Path) -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for row in _read_csv(path, SOURCE_COLUMNS, "source register"):
        identifier = row["source_id"]
        if not IDENTIFIER_RE.fullmatch(identifier):
            raise ValueError(f"source register has an invalid source_id: {identifier!r}")
        if identifier in sources:
            raise ValueError(f"source register repeats source_id {identifier}")
        sources[identifier] = row
    return sources


def check_cited_sources(
    sources: dict[str, dict[str, str]], cited: set[str], repository_root: Path
) -> list[str]:
    errors: list[str] = []
    for identifier in sorted(cited):
        row = sources[identifier]
        if not row["citation"]:
            errors.append(f"source {identifier} has no citation")
        if not row["local_path"] and not row["url"]:
            errors.append(f"source {identifier} needs a local_path to the archived copy or a url")
        if row["url"] and not DATE_RE.fullmatch(row["access_date"]):
            errors.append(f"source {identifier} has a url but no YYYY-MM-DD access_date")
        if row["local_path"]:
            try:
                local = _resolve_project_path(repository_root, row["local_path"])
            except ValueError as exc:
                errors.append(f"source {identifier}: {exc}")
                continue
            if not local.is_file():
                errors.append(f"source {identifier}: archived copy does not exist: {row['local_path']}")
            elif row["sha256"] and _sha256(local) != row["sha256"].casefold():
                errors.append(f"source {identifier}: archived copy does not match its sha256")
    return errors


def load_values(path: Path, repository_root: Path) -> dict[str, dict[str, str]]:
    values: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for row in _read_csv(path, VALUE_COLUMNS, "values table"):
        key = row["key"]
        if not IDENTIFIER_RE.fullmatch(key):
            raise ValueError(f"values table has an invalid key: {key!r}")
        if key in values:
            raise ValueError(f"values table repeats key {key}")
        status = row["status"].casefold()
        row["status"] = status
        if status not in VALUE_STATUSES:
            errors.append(f"value {key}: status must be verified or pending")
        elif status == "verified":
            if not row["value"]:
                errors.append(f"value {key}: a verified value cannot be empty")
            match = PROJECT_REF_RE.fullmatch(row["source"])
            if not match:
                errors.append(f"value {key}: source must be project/path#id naming the result it came from")
            else:
                try:
                    if not _resolve_project_path(repository_root, match.group("path")).is_file():
                        errors.append(f"value {key}: source file does not exist: {match.group('path')}")
                except ValueError as exc:
                    errors.append(f"value {key}: {exc}")
        else:
            if row["value"]:
                errors.append(f"value {key}: a pending value must leave value empty")
            if not row["description"]:
                errors.append(f"value {key}: a pending value needs a description of what will go there")
        values[key] = row
    if errors:
        raise ValueError("values table problems:\n- " + "\n- ".join(errors))
    return values


# --------------------------------------------------------------------------------------------
# Numbering and validation


def number_headings(headings: list[Heading]) -> None:
    part_number = 0
    appendix_number = 0
    top: Heading | None = None
    counters = [0, 0, 0, 0]
    symbols: list[str] = []
    for heading in headings:
        if heading.level == 1:
            top = heading
            counters = [0, 0, 0, 0]
            symbols = []
            if heading.role == "part":
                part_number += 1
                numeral = _roman(part_number)
                heading.visible = f"{numeral}. {heading.title}"
                heading.ref = f"Part {numeral}"
            elif heading.role == "appendix":
                appendix_number += 1
                heading.letter = chr(64 + appendix_number)
                rest = APPENDIX_RE.match(heading.title).group(1).strip()
                heading.visible = f"Appendix {heading.letter}" + (f". {rest}" if rest else "")
                heading.ref = f"Appendix {heading.letter}"
            elif heading.role in ("introduction", "conclusion"):
                heading.visible = heading.title
                heading.ref = heading.role.capitalize()
            continue
        assert top is not None
        depth = heading.level - 1
        counters[depth] += 1
        for index in range(depth + 1, len(counters)):
            counters[index] = 0
        if top.role == "appendix":
            trail = ".".join(str(counters[index]) for index in range(1, depth + 1))
            heading.visible = f"{top.letter}.{trail}. {heading.title}"
            heading.ref = f"Appendix {top.letter}.{trail}"
            continue
        symbol = {1: chr(64 + counters[1]), 2: str(counters[2]), 3: chr(96 + counters[3])}[depth]
        symbols = symbols[: depth - 1] + [symbol]
        heading.visible = f"{symbol}. {heading.title}"
        heading.ref = f"{top.ref}." + ".".join(symbols) if top.ref else ".".join(symbols)


def number_displays(context: Context) -> None:
    counters = {kind: 0 for kind in DISPLAY_KINDS}
    for block in context.draft.blocks:
        if block.kind == "display":
            kind, identifier = block.display.kind, block.display.artifact_id
        elif block.kind == "pending":
            kind, identifier, _caption = block.pending
        else:
            continue
        counters[kind] += 1
        if identifier in context.displays:
            context.errors.append(f"line {block.line}: display ID {identifier} is used twice")
        context.displays[identifier] = (kind, counters[kind])


def number_footnotes(draft: Draft) -> list[str]:
    errors: list[str] = []
    seen: list[str] = []
    for block in draft.blocks:
        if block.kind not in ("paragraph", "quote"):
            continue
        for label in re.findall(r"\[\^([^\]\s]+)\]", block.text):
            if label in seen:
                errors.append(f"line {block.line}: footnote [^{label}] is referenced twice; "
                              "cite again in a new footnote with a short form")
                continue
            seen.append(label)
            if label in draft.footnotes:
                draft.footnotes[label].number = len(seen)
    for label, footnote in draft.footnotes.items():
        if not footnote.number:
            errors.append(f"line {footnote.line}: footnote [^{label}] is defined but never referenced")
    return errors


def check_structure(draft: Draft) -> list[str]:
    errors: list[str] = []
    top = [heading for heading in draft.headings if heading.level == 1]
    roles = [heading.role for heading in top]
    if not roles or roles[0] != "abstract":
        errors.append("the first heading must be # Abstract")
    if roles.count("abstract") > 1 or roles.count("introduction") != 1 or roles.count("conclusion") != 1:
        errors.append("the draft needs exactly one Abstract, one Introduction, and one Conclusion")
    if len(roles) > 1 and roles[1] != "introduction":
        errors.append("the Introduction must follow the Abstract")
    if roles.count("part") < 2:
        errors.append("the draft needs at least two numbered Parts between the Introduction and Conclusion")
    if "appendix" not in roles:
        errors.append("the draft needs at least one Appendix with the technical details")
    if "conclusion" in roles:
        conclusion = roles.index("conclusion")
        if any(role == "part" for role in roles[conclusion + 1 :]):
            errors.append("every numbered Part must come before the Conclusion")
        if any(role != "appendix" for role in roles[conclusion + 1 :]):
            errors.append("only appendices may follow the Conclusion")
        if any(role == "appendix" for role in roles[:conclusion]):
            errors.append("appendices must follow the Conclusion")
    anchors = [heading.anchor for heading in draft.headings if heading.anchor]
    for anchor in sorted({anchor for anchor in anchors if anchors.count(anchor) > 1}):
        errors.append(f"anchor {{#{anchor}}} is used twice")
    abstract = top[0] if top and top[0].role == "abstract" else None
    if abstract is not None:
        if any(heading.level > 1 and heading.role == "abstract" for heading in draft.headings):
            errors.append("the Abstract cannot have subheadings")
        if any(block.heading is abstract and block.kind != "paragraph" for block in draft.blocks):
            errors.append("the Abstract holds paragraphs only")
    with_content = {block.heading.order for block in draft.blocks}
    for index, heading in enumerate(draft.headings):
        following = draft.headings[index + 1] if index + 1 < len(draft.headings) else None
        has_child = following is not None and following.level > heading.level
        if heading.order not in with_content and not has_child:
            errors.append(f"line {heading.line}: heading {heading.title!r} has no content")
    return errors


def _location(block: Block) -> str:
    base = block.heading.ref or block.heading.title
    if block.kind in ("paragraph", "quote"):
        return f"{base}, paragraph {block.index}"
    return base


def analyze_footnotes(context: Context, lexed: dict[str, Lexed]) -> tuple[list[dict[str, object]], list[str]]:
    errors: list[str] = []
    citations: list[dict[str, object]] = []
    ordered = sorted(
        (footnote for footnote in context.draft.footnotes.values() if footnote.number),
        key=lambda footnote: footnote.number,
    )
    by_number = {footnote.number: footnote for footnote in ordered}
    for footnote in ordered:
        result = lexed[footnote.label]
        sources = list(dict.fromkeys(result.sources))
        location = f"note {footnote.number}"
        if sources or result.citation_needed:
            kind = "cited" if sources else "citation_needed"
        elif EXTERNAL_CITATION_RE.search(result.plain) or (
            SIGNAL_START_RE.search(result.plain) and not result.internal_refs
        ):
            errors.append(
                f"{location} looks like a citation but has no {{{{src:ID}}}} or [[citation needed: ...]]"
            )
            kind = "uncited"
        else:
            kind = "internal" if result.internal_refs else "explanatory"
        if ID_START_RE.search(footnote.text):
            previous = by_number.get(footnote.number - 1)
            previous_sources = list(dict.fromkeys(lexed[previous.label].sources)) if previous else []
            if len(previous_sources) != 1:
                errors.append(f"{location} begins with Id., but note {footnote.number - 1} does not cite "
                              "exactly one source")
            elif sources != previous_sources:
                errors.append(f"{location} begins with Id. but does not carry the {{{{src:...}}}} of the "
                              f"source in note {footnote.number - 1} ({previous_sources[0]})")
        for target_label in SUPRA_NOTE_RE.findall(footnote.text):
            target = context.draft.footnotes.get(target_label)
            if target is None or not target.number:
                continue
            if target.number >= footnote.number:
                errors.append(f"{location} says supra note {target.number}, which does not come earlier")
            elif not set(sources) & set(lexed[target.label].sources):
                errors.append(f"{location} points to supra note {target.number}, which does not cite the "
                              "same source")
        citations.append({"footnote": footnote.number, "label": footnote.label, "kind": kind,
                          "sources": sources})
    return citations, errors


def _sentences(text: str) -> list[str]:
    protected = text
    for index, abbreviation in enumerate(ABBREVIATIONS):
        protected = protected.replace(abbreviation, abbreviation.replace(".", f"\x00{index}\x00"))
    parts = re.split(r"(?<=[.!?])[\"'" + RIGHT_QUOTE + chr(0x201D) + r")]*\s+(?=[A-Z\"(" + chr(0x201C) + r"])",
                     protected)
    restored: list[str] = []
    for part in parts:
        for index, abbreviation in enumerate(ABBREVIATIONS):
            part = part.replace(abbreviation.replace(".", f"\x00{index}\x00"), abbreviation)
        if part.strip():
            restored.append(part.strip())
    return restored


def style_warnings(paragraphs: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    """Return warnings for (location, visible text, text with value tokens removed) triples."""

    warnings: list[dict[str, str]] = []
    acronyms_seen: set[str] = set()
    for location, visible, untokened in paragraphs:
        words = WORD_RE.findall(visible)
        if len(words) > LONG_PARAGRAPH_WORDS:
            warnings.append({"kind": "long_paragraph", "location": location,
                             "detail": f"{len(words)} words"})
        for sentence in _sentences(visible):
            count = len(WORD_RE.findall(sentence))
            if count > LONG_SENTENCE_WORDS:
                warnings.append({"kind": "long_sentence", "location": location,
                                 "detail": f"{count} words: {sentence[:80]}..."})
            marks = sentence.count(EM_DASH) + sentence.count(" -- ") + sentence.count(":") + sentence.count(";")
            marks += len(re.findall(r"\s" + EN_DASH + r"\s", sentence))
            if marks > 1:
                warnings.append({"kind": "punctuation", "location": location,
                                 "detail": f"more than one dash, colon, or semicolon: {sentence[:80]}..."})
        for match in HYPE_RE.finditer(visible):
            warnings.append({"kind": "overstatement_or_filler", "location": location,
                             "detail": match.group(0)})
        for match in ACRONYM_RE.finditer(visible):
            acronym = match.group(1)
            if acronym in acronyms_seen or ROMAN_RE.fullmatch(acronym):
                continue
            acronyms_seen.add(acronym)
            if not match.group(0).startswith("("):
                warnings.append({"kind": "undefined_acronym", "location": location,
                                 "detail": f"{acronym} is used before it is spelled out as Long Form ({acronym})"})
        for match in NUMBER_RE.finditer(untokened):
            raw = match.group(0).rstrip(",")
            digits = raw.replace(",", "").rstrip("%")
            if re.fullmatch(r"1[6-9]\d\d|20\d\d", digits) and not raw.endswith("%"):
                continue
            if NUMBER_PREFIX_RE.search(untokened[: match.start()]):
                continue
            warnings.append({"kind": "number_not_from_values_table", "location": location,
                             "detail": raw})
    return warnings


def validate(draft: Draft, project_root: Path) -> tuple[Context, dict[str, object]]:
    repository_root = _repository_root(project_root)
    metadata = draft.metadata
    errors: list[str] = []
    for item in [part.strip() for part in metadata["source_versions"].split(";") if part.strip()]:
        try:
            if not _resolve_project_path(repository_root, item).exists():
                errors.append(f"source_versions entry does not exist: {item}")
        except ValueError as exc:
            errors.append(str(exc))
    limit_text = metadata.get("abstract_word_limit", "") or str(DEFAULT_ABSTRACT_WORD_LIMIT)
    if not limit_text.isdigit() or int(limit_text) < 50:
        errors.append("abstract_word_limit must be a whole number of at least 50")
        limit_text = str(DEFAULT_ABSTRACT_WORD_LIMIT)
    sources = load_sources(_resolve_project_path(repository_root, metadata["sources"]))
    values = load_values(_resolve_project_path(repository_root, metadata["values"]), repository_root)

    errors.extend(check_structure(draft))
    number_headings(draft.headings)
    errors.extend(number_footnotes(draft))
    context = Context(draft, sources, values)
    number_displays(context)

    lexed_blocks: dict[int, Lexed] = {}
    for position, block in enumerate(draft.blocks):
        location = _location(block)
        if block.kind in ("paragraph", "quote"):
            in_abstract = block.heading.role == "abstract"
            lexed_blocks[position] = context.lex(
                block.text, location, allow_footnotes=not in_abstract, allow_notes=True
            )
        elif block.kind == "display":
            lexed_blocks[position] = context.lex(block.display.caption, f"{location}, caption")
            try:
                path = _resolve_project_path(repository_root, block.display.path)
                if not path.is_file():
                    errors.append(f"line {block.line}: display file does not exist: {block.display.path}")
                elif block.display.kind == "table":
                    if any(CONTROL_RE.search(cell) for row in _read_table(path) for cell in row):
                        errors.append(f"line {block.line}: table has a control character: {block.display.path}")
                elif block.display.kind == "equation":
                    if CONTROL_RE.search(_read_equation(path)):
                        errors.append(f"line {block.line}: equation has a control character: {block.display.path}")
            except ValueError as exc:
                errors.append(f"line {block.line}: {exc}")
        else:
            kind, identifier, caption = block.pending
            lexed_blocks[position] = context.lex(caption, f"{location}, caption")
            context.placeholders.append({"kind": "pending_display", "location": location,
                                         "text": f"{kind} {identifier}: {caption}"})
    lexed_footnotes = {
        label: context.lex(footnote.text, f"note {footnote.number or '?'}", allow_sources=True)
        for label, footnote in draft.footnotes.items()
    }
    lexed_headings = {
        heading.order: context.lex(heading.visible or heading.title, heading.ref or heading.title)
        for heading in draft.headings
    }
    title_lexed = context.lex(metadata["title"], "title")
    author_note = context.lex(metadata.get("author_note", "") or "[Author information and acknowledgments.]",
                              "author note")
    citations, footnote_errors = analyze_footnotes(context, lexed_footnotes)
    errors.extend(footnote_errors)
    errors.extend(check_cited_sources(sources, set(context.sources_used), repository_root))

    abstract_words = sum(
        len(WORD_RE.findall(lexed_blocks[position].plain))
        for position, block in enumerate(draft.blocks)
        if block.heading.role == "abstract"
    )
    if abstract_words == 0:
        errors.append("the Abstract is empty")
    if abstract_words > int(limit_text):
        errors.append(f"the Abstract has {abstract_words} words; the limit is {limit_text}")

    visible_parts = [lexed.plain for lexed in lexed_blocks.values()]
    visible_parts += [lexed.plain for lexed in lexed_footnotes.values()]
    visible_parts += [title_lexed.plain, author_note.plain, metadata.get("authors", "")]
    visible_parts += [heading.visible for heading in draft.headings]
    for value in visible_parts:
        if re.search(r"(?<![\w/])project/", value):
            errors.append(f"a project path would be visible in the draft: {value[:80]}")
            break
    errors.extend(context.errors)
    if errors:
        unique = list(dict.fromkeys(errors))
        raise ValueError("draft problems:\n- " + "\n- ".join(unique))

    body_paragraphs = []
    for position, block in enumerate(draft.blocks):
        if block.kind == "paragraph":
            untokened = re.sub(r"\{\{[^{}]*\}\}|\[\[[^\]]*\]\]|\[\^[^\]]*\]", " ", block.text)
            body_paragraphs.append((_location(block), lexed_blocks[position].plain, untokened))
    analysis = {
        "lexed_blocks": lexed_blocks,
        "lexed_footnotes": lexed_footnotes,
        "lexed_headings": lexed_headings,
        "title": title_lexed,
        "author_note": author_note,
        "citations": citations,
        "abstract_words": abstract_words,
        "warnings": style_warnings(body_paragraphs),
        "sources": sources,
        "values": values,
    }
    return context, analysis


# --------------------------------------------------------------------------------------------
# Word rendering


def _run(text: str, *, italic=False, bold=False, smallcaps=False, highlight=False, style=None):
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    if style:
        style_element = OxmlElement("w:rStyle")
        style_element.set(qn("w:val"), style)
        properties.append(style_element)
    if bold:
        properties.append(OxmlElement("w:b"))
    if italic:
        properties.append(OxmlElement("w:i"))
    if smallcaps:
        properties.append(OxmlElement("w:smallCaps"))
    if highlight:
        mark = OxmlElement("w:highlight")
        mark.set(qn("w:val"), "yellow")
        properties.append(mark)
    if len(properties):
        run.append(properties)
    text_element = OxmlElement("w:t")
    text_element.set(qn("xml:space"), "preserve")
    text_element.text = text
    run.append(text_element)
    return run


def _footnote_reference(footnote_id: int):
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    style = OxmlElement("w:rStyle")
    style.set(qn("w:val"), "FootnoteReference")
    properties.append(style)
    run.append(properties)
    reference = OxmlElement("w:footnoteReference")
    reference.set(qn("w:id"), str(footnote_id))
    run.append(reference)
    return run


def _append_pieces(paragraph_element, pieces: list[Piece], footnote_ids: dict[str, int], *, upper=False) -> None:
    for piece in pieces:
        if piece.kind == "fnref":
            paragraph_element.append(_footnote_reference(footnote_ids[piece.label]))
        elif piece.text:
            text = piece.text.upper() if upper and not piece.highlight else piece.text
            paragraph_element.append(
                _run(text, italic=piece.italic, bold=piece.bold, smallcaps=piece.smallcaps,
                     highlight=piece.highlight)
            )


def _clear_runs(paragraph) -> None:
    for child in list(paragraph._p):
        if child.tag != qn("w:pPr"):
            paragraph._p.remove(child)


def _add_note_comments(doc, paragraph, notes: list[str]) -> None:
    if not notes:
        return
    if not paragraph.runs:
        paragraph.add_run(" ")
    doc.add_comment(runs=paragraph.runs, text=" ".join(notes), author="Drafting notes", initials="DN")


def _word_profile(metadata: dict[str, str]) -> dict[str, object]:
    template_id = metadata.get("word_template", "").strip() or "law_review_v1"
    if template_id not in SUPPORTED_WORD_TEMPLATES:
        raise ValueError(f"word_template must be one of: {', '.join(SUPPORTED_WORD_TEMPLATES)}")
    profiles = _load_word_profiles()
    profile = dict(profiles[template_id])
    path = Path(__file__).resolve().parents[1] / str(profile["template_path"])
    if not path.is_file():
        raise ValueError(f"Word template does not exist: {profile['template_path']}")
    if _sha256(path) != str(profile.get("sha256", "")).casefold():
        raise ValueError(f"Word template hash mismatch for {template_id}")
    profile["template_id"] = template_id
    profile["resolved_path"] = path
    return profile


def _render_docx_display(doc, block: Block, lexed: Lexed, context: Context, repository_root: Path,
                         total_width: int) -> None:
    if block.kind == "pending":
        kind, identifier, _caption = block.pending
        _, number = context.displays[identifier]
    else:
        kind, number = block.display.kind, context.displays[block.display.artifact_id][1]
    label = f"({number})" if kind == "equation" else f"{kind.capitalize()} {number}. "

    def caption_paragraph():
        paragraph = doc.add_paragraph(style="Caption")
        if kind != "equation":
            paragraph._p.append(_run(label))
        _append_pieces(paragraph._p, lexed.pieces, {})
        return paragraph

    if block.kind == "pending":
        if kind == "equation":
            placeholder = doc.add_paragraph(style="Caption")
            placeholder._p.append(_run(f"[[pending: equation]]    ({number})", highlight=True))
            caption_paragraph()
        else:
            caption_paragraph()
            placeholder = doc.add_paragraph(style="Caption")
            placeholder._p.append(_run(f"[[pending: {kind} to come]]", highlight=True))
        return
    path = _resolve_project_path(repository_root, block.display.path)
    if kind == "table":
        caption_paragraph().paragraph_format.keep_with_next = True
        rows = _read_table(path)
        table = doc.add_table(rows=len(rows), cols=len(rows[0]))
        table.style = "Table Grid"
        _repeat_header(table.rows[0])
        _set_article_table_geometry(table, _content_sensitive_widths(rows, total_width))
        for row_index, (word_row, values) in enumerate(zip(table.rows, rows)):
            for cell, value in zip(word_row.cells, values):
                cell.text = value
                _set_cell_shading(cell, "D9D9D9" if row_index == 0 else WHITE)
                if row_index == 0:
                    for run in cell.paragraphs[0].runs:
                        run.bold = True
    elif kind == "figure":
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Inches(0)
        paragraph.paragraph_format.keep_with_next = True
        natural = Image.from_file(str(path)).width.inches
        shape = paragraph.add_run().add_picture(str(path), width=Inches(min(natural, total_width / 1440)))
        _embed_alt_text(shape, block.display.alt_text or lexed.plain)
        caption_paragraph()
    else:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Inches(0)
        paragraph.paragraph_format.keep_with_next = True
        paragraph.add_run(_read_equation(path)).font.name = "Cambria Math"
        paragraph.add_run(f"    ({number})")
        caption = doc.add_paragraph()
        caption.paragraph_format.first_line_indent = Inches(0)
        _append_pieces(caption._p, lexed.pieces, {})


def build_docx(draft: Draft, context: Context, analysis: dict[str, object], output: Path,
               repository_root: Path) -> dict[str, object]:
    metadata = draft.metadata
    profile = _word_profile(metadata)
    doc = _load_template_without_prototype_comments(Path(profile["resolved_path"]))
    lexed_blocks: dict[int, Lexed] = analysis["lexed_blocks"]
    lexed_footnotes: dict[str, Lexed] = analysis["lexed_footnotes"]
    authors = metadata.get("authors", "").strip() or "[Author Name]"
    running_title = metadata.get("running_title", "").strip() or analysis["title"].plain

    _replace_visible_text(doc.paragraphs[0], analysis["title"].plain.upper())
    _replace_visible_text(doc.paragraphs[1], authors)
    author_reference = next(iter(doc.paragraphs[1]._p.iter(qn("w:footnoteReference"))), None)
    if author_reference is None:
        raise ValueError("the law-review template has no author footnote")
    author_id = author_reference.get(qn("w:id"))
    author_reference.set(qn("w:customMarkFollows"), "1")
    star = OxmlElement("w:t")
    star.text = "*"
    author_reference.addnext(star)

    abstract_positions = [
        position for position, block in enumerate(draft.blocks) if block.heading.role == "abstract"
    ]
    abstract_paragraph = doc.paragraphs[2]
    _clear_body_after(doc, 3)
    template_abstract = copy.deepcopy(abstract_paragraph._p)
    previous = abstract_paragraph._p
    abstract_objects = []
    for index, position in enumerate(abstract_positions):
        if index == 0:
            _clear_runs(abstract_paragraph)
            element = abstract_paragraph._p
        else:
            element = copy.deepcopy(template_abstract)
            for child in list(element):
                if child.tag != qn("w:pPr"):
                    element.remove(child)
            previous.addnext(element)
        _append_pieces(element, lexed_blocks[position].pieces, {})
        previous = element
        abstract_objects.append((element, lexed_blocks[position].notes))
    _replace_header_placeholder(doc, running_title)
    doc.add_page_break()
    _add_toc_field(doc)
    doc.add_page_break()

    ordered = sorted((item for item in draft.footnotes.values()), key=lambda item: item.number)
    used_ids = {author_id}
    footnote_ids: dict[str, int] = {}
    next_id = 1
    for footnote in ordered:
        while str(next_id) in used_ids:
            next_id += 1
        footnote_ids[footnote.label] = next_id
        used_ids.add(str(next_id))

    total_width = _content_width_dxa(doc)
    last_heading = None
    for position, block in enumerate(draft.blocks):
        if block.heading.role == "abstract":
            continue
        if block.heading is not last_heading:
            _render_headings_through(doc, draft, block.heading, last_heading, analysis)
            last_heading = block.heading
        lexed = lexed_blocks[position]
        if block.kind in ("paragraph", "quote"):
            paragraph = doc.add_paragraph()
            if block.kind == "quote":
                paragraph.paragraph_format.left_indent = Inches(0.5)
                paragraph.paragraph_format.right_indent = Inches(0.5)
                paragraph.paragraph_format.first_line_indent = Inches(0)
            _append_pieces(paragraph._p, lexed.pieces, footnote_ids)
            _add_note_comments(doc, paragraph, lexed.notes)
        else:
            _render_docx_display(doc, block, lexed, context, repository_root, total_width)
    _render_headings_through(doc, draft, None, last_heading, analysis)

    for element, notes in abstract_objects:
        _add_note_comments(doc, Paragraph(element, doc._body), notes)

    footnotes_part = doc.part.part_related_by(RT.FOOTNOTES)
    root = parse_xml(footnotes_part.blob)
    author_note = next(
        (node for node in root.iter(qn("w:footnote")) if node.get(qn("w:id")) == author_id), None
    )
    if author_note is None:
        raise ValueError("the law-review template's author footnote is missing")
    for node in list(root.iter(qn("w:footnote"))):
        if node.get(qn("w:type")) is None and node.get(qn("w:id")) != author_id:
            root.remove(node)
    note_paragraph = author_note.find(qn("w:p"))
    for child in list(note_paragraph):
        if child.tag != qn("w:pPr"):
            note_paragraph.remove(child)
    note_paragraph.append(_run("*", style="FootnoteReference"))
    note_paragraph.append(_run(" "))
    _append_pieces(note_paragraph, analysis["author_note"].pieces, {})
    label = metadata.get("draft_label", "").strip() or DEFAULT_DRAFT_LABEL
    note_paragraph.append(_run(" " + label))
    for footnote in ordered:
        element = OxmlElement("w:footnote")
        element.set(qn("w:id"), str(footnote_ids[footnote.label]))
        paragraph = OxmlElement("w:p")
        properties = OxmlElement("w:pPr")
        style = OxmlElement("w:pStyle")
        style.set(qn("w:val"), "FootnoteText")
        properties.append(style)
        paragraph.append(properties)
        reference_run = OxmlElement("w:r")
        reference_properties = OxmlElement("w:rPr")
        reference_style = OxmlElement("w:rStyle")
        reference_style.set(qn("w:val"), "FootnoteReference")
        reference_properties.append(reference_style)
        reference_run.append(reference_properties)
        reference_run.append(OxmlElement("w:footnoteRef"))
        paragraph.append(reference_run)
        paragraph.append(_run(" "))
        _append_pieces(paragraph, lexed_footnotes[footnote.label].pieces, {})
        element.append(paragraph)
        root.append(element)
    referenced = {node.get(qn("w:id")) for node in doc.element.body.iter(qn("w:footnoteReference"))}
    for node in list(root.iter(qn("w:footnote"))):
        if node.get(qn("w:type")) is None and node.get(qn("w:id")) not in referenced:
            root.remove(node)
    footnotes_part._blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    _request_field_updates(doc)
    doc.core_properties.title = analysis["title"].plain
    doc.core_properties.subject = "Illustrative law review article draft for the author to rewrite"
    doc.core_properties.author = "" if authors.startswith("[") else authors
    fixed_time = datetime(2000, 1, 1, tzinfo=timezone.utc)
    doc.core_properties.created = fixed_time
    doc.core_properties.modified = fixed_time
    doc.save(output)
    return {
        "template_id": profile["template_id"],
        "template_path": str(profile["template_path"]),
        "template_sha256": str(profile["sha256"]),
        "requirements_authority": profile.get("requirements_authority"),
        "requirements_checked": profile.get("requirements_checked"),
    }


def _render_headings_through(doc, draft: Draft, target: Heading | None, last: Heading | None,
                             analysis: dict[str, object]) -> None:
    """Render every heading after ``last`` up to and including ``target`` (or all remaining)."""

    start = last.order if last is not None else 0
    stop = target.order if target is not None else len(draft.headings)
    for heading in draft.headings[start:stop]:
        if heading.role == "abstract" and heading.level == 1:
            continue
        paragraph = doc.add_paragraph(style=f"Heading {heading.level}")
        lexed = analysis["lexed_headings"][heading.order]
        _append_pieces(paragraph._p, lexed.pieces, {}, upper=heading.level == 1)


# --------------------------------------------------------------------------------------------
# Markdown rendering


def _markdown(pieces: list[Piece], footnote_numbers: dict[str, int] | None = None, *, upper=False) -> str:
    """Render pieces as Markdown, merging neighbors that share emphasis so markers stay balanced."""

    output: list[str] = []
    group: list[str] = []
    style: tuple[bool, bool] | None = None

    def flush() -> None:
        if not group:
            return
        text = "".join(group)
        group.clear()
        core = text.strip()
        if style and any(style) and core:
            lead = text[: len(text) - len(text.lstrip())]
            trail = text[len(text.rstrip()) :]
            if style[1]:
                core = f"**{core}**"
            if style[0]:
                core = f"*{core}*"
            output.append(lead + core + trail)
        else:
            output.append(text)

    for piece in pieces:
        if piece.kind == "fnref":
            flush()
            style = None
            output.append(f"[^{footnote_numbers[piece.label]}]")
            continue
        text = piece.text.upper() if upper and not piece.highlight else piece.text
        text = text.replace("\\", "\\\\").replace("*", "\\*")
        if (piece.italic, piece.bold) != style:
            flush()
            style = (piece.italic, piece.bold)
        group.append(text)
    flush()
    return "".join(output)


def build_markdown(draft: Draft, context: Context, analysis: dict[str, object], output: Path,
                   repository_root: Path) -> None:
    metadata = draft.metadata
    lexed_blocks: dict[int, Lexed] = analysis["lexed_blocks"]
    lexed_footnotes: dict[str, Lexed] = analysis["lexed_footnotes"]
    numbers = {label: footnote.number for label, footnote in draft.footnotes.items()}
    label = metadata.get("draft_label", "").strip() or DEFAULT_DRAFT_LABEL
    lines = [
        f"# {analysis['title'].plain.upper()}",
        "",
        f"**{metadata.get('authors', '').strip() or '[Author Name]'}**",
        "",
        f"Author note: {_markdown(analysis['author_note'].pieces)} {label}",
        "",
        "## Abstract",
        "",
    ]
    last_heading = None
    for position, block in enumerate(draft.blocks):
        lexed = lexed_blocks[position]
        if block.heading.role != "abstract" and block.heading is not last_heading:
            start = last_heading.order if last_heading is not None else 0
            for heading in draft.headings[start : block.heading.order]:
                if heading.role == "abstract":
                    continue
                visible = _markdown(analysis["lexed_headings"][heading.order].pieces,
                                    upper=heading.level == 1)
                lines.extend([f"{'#' * (heading.level + 1)} {visible}", ""])
            last_heading = block.heading
        if block.kind == "paragraph":
            lines.extend([_markdown(lexed.pieces, numbers), ""])
        elif block.kind == "quote":
            lines.extend(["> " + _markdown(lexed.pieces, numbers), ""])
        elif block.kind == "pending":
            kind, identifier, _caption = block.pending
            number = context.displays[identifier][1]
            name = f"Equation ({number})" if kind == "equation" else f"{kind.capitalize()} {number}"
            lines.extend([f"**{name}.** {_markdown(lexed.pieces)}", "", f"[[pending: {kind} to come]]", ""])
        else:
            display = block.display
            number = context.displays[display.artifact_id][1]
            path = _resolve_project_path(repository_root, display.path)
            caption = _markdown(lexed.pieces)
            if display.kind == "table":
                rows = _read_table(path)
                lines.extend([f"**Table {number}.** {caption}", ""])
                lines.append("| " + " | ".join(rows[0]) + " |")
                lines.append("|" + "|".join("---" for _ in rows[0]) + "|")
                lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
                lines.append("")
            elif display.kind == "figure":
                relative = Path(os.path.relpath(path, output.parent)).as_posix()
                lines.extend([f"![{display.alt_text or lexed.plain}]({relative})", "",
                              f"**Figure {number}.** {caption}", ""])
            else:
                lines.extend(["$$", _read_equation(path), f"\\tag{{{number}}}", "$$", "", caption, ""])
    if last_heading is not None:
        for heading in draft.headings[last_heading.order :]:
            visible = _markdown(analysis["lexed_headings"][heading.order].pieces, upper=heading.level == 1)
            lines.extend([f"{'#' * (heading.level + 1)} {visible}", ""])
    for footnote in sorted(draft.footnotes.values(), key=lambda item: item.number):
        lines.append(f"[^{footnote.number}]: {_markdown(lexed_footnotes[footnote.label].pieces)}")
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------
# Output checks, manifest, and command line


def _validate_output(path: Path, draft: Draft, analysis: dict[str, object]) -> None:
    expected_notes = len(draft.footnotes)
    if path.suffix == ".docx":
        import zipfile

        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml").decode("utf-8")
            footnotes_xml = archive.read("word/footnotes.xml").decode("utf-8")
        references = re.findall(r"<w:footnoteReference\b[^>]*>", document_xml)
        numbered = [item for item in references if "customMarkFollows" not in item]
        if len(numbered) != expected_notes:
            raise ValueError(f"Word output has {len(numbered)} numbered footnotes; expected {expected_notes}")
        visible = re.sub(r"<[^>]+>", "", document_xml) + re.sub(r"<[^>]+>", "", footnotes_xml)
        tables = len(re.findall(r"<w:tbl[ >]", document_xml))
        expected_tables = sum(1 for block in draft.blocks if block.kind == "display" and block.display.kind == "table")
        if tables != expected_tables:
            raise ValueError(f"Word output has {tables} tables; expected {expected_tables}")
        reopened = Document(path)
        expected_comments = sum(1 for lexed in analysis["lexed_blocks"].values() if lexed.notes)
        if len(reopened.comments) != expected_comments:
            raise ValueError("Word output comments do not match the [[note: ...]] paragraphs")
    else:
        visible = path.read_text(encoding="utf-8")
        if len(re.findall(r"(?m)^\[\^\d+\]:", visible)) != expected_notes:
            raise ValueError("Markdown output footnote count does not match the source")
    for leftover in ("{{", "!display", "!pending", "[^"):
        if leftover in visible and not (leftover == "[^" and path.suffix == ".md"):
            raise ValueError(f"output still contains unrendered markup: {leftover}")


def summarize(draft: Draft, context: Context, analysis: dict[str, object]) -> dict[str, object]:
    lexed_blocks: dict[int, Lexed] = analysis["lexed_blocks"]
    body_words = sum(
        len(WORD_RE.findall(lexed_blocks[position].plain))
        for position, block in enumerate(draft.blocks)
        if block.heading.role != "abstract" and block.kind in ("paragraph", "quote")
    )
    footnote_words = sum(len(WORD_RE.findall(lexed.plain)) for lexed in analysis["lexed_footnotes"].values())
    placeholder_counts: dict[str, int] = {}
    for item in context.placeholders:
        placeholder_counts[item["kind"]] = placeholder_counts.get(item["kind"], 0) + 1
    warning_counts: dict[str, int] = {}
    for item in analysis["warnings"]:
        warning_counts[item["kind"]] = warning_counts.get(item["kind"], 0) + 1
    sources: dict[str, dict[str, str]] = analysis["sources"]
    values: dict[str, dict[str, str]] = analysis["values"]
    return {
        "structure": [
            {"level": heading.level, "role": heading.role, "heading": heading.visible or heading.title,
             "reference": heading.ref, "anchor": heading.anchor}
            for heading in draft.headings
        ],
        "counts": {
            "abstract_words": analysis["abstract_words"],
            "body_words": body_words,
            "footnote_words": footnote_words,
            "total_words": analysis["abstract_words"] + body_words + footnote_words,
            "footnotes": len(draft.footnotes),
            "parts": sum(1 for heading in draft.headings if heading.level == 1 and heading.role == "part"),
            "appendices": sum(1 for heading in draft.headings if heading.level == 1 and heading.role == "appendix"),
            "displays": len(context.displays),
            "placeholders": placeholder_counts,
            "warnings": warning_counts,
        },
        "citations": analysis["citations"],
        "sources_cited": {key: value for key, value in sorted(context.sources_used.items())},
        "sources_unused": sorted(set(sources) - set(context.sources_used)),
        "values_used": {
            key: {"value": values[key]["value"], "status": values[key]["status"],
                  "source": values[key]["source"], "locations": locations}
            for key, locations in sorted(context.values_used.items())
        },
        "values_unused": sorted(set(values) - set(context.values_used)),
        "placeholders": context.placeholders,
        "notes_to_researcher": context.notes,
        "warnings": analysis["warnings"],
    }


def load_and_validate(source: Path, project_root: Path) -> tuple[Draft, Context, dict[str, object]]:
    if source.suffix.lower() != ".md":
        raise ValueError("source must be a .md file")
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    draft = parse_source(source.read_text(encoding="utf-8"))
    context, analysis = validate(draft, project_root)
    return draft, context, analysis


def check(source: Path, project_root: Path) -> dict[str, object]:
    draft, context, analysis = load_and_validate(source, project_root)
    return summarize(draft, context, analysis)


def build(source: Path, output: Path, manifest: Path, project_root: Path) -> dict[str, object]:
    if output.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError("output must be a .docx or .md file")
    if manifest.suffix.lower() != ".json":
        raise ValueError("manifest must be a .json file")
    for path in (output, manifest):
        if path.exists():
            raise ValueError(f"refusing to overwrite existing file: {path}")
    draft, context, analysis = load_and_validate(source, project_root)
    repository_root = _repository_root(project_root)
    metadata = draft.metadata
    for path in (output, manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        word_template = None
        if output.suffix.lower() == ".docx":
            word_template = build_docx(draft, context, analysis, output, repository_root)
        else:
            build_markdown(draft, context, analysis, output, repository_root)
        created.append(output)
        _validate_output(output, draft, analysis)
        sources_path = _resolve_project_path(repository_root, metadata["sources"])
        values_path = _resolve_project_path(repository_root, metadata["values"])
        payload = {
            "schema_version": "1.0",
            "utility_id": "draft-article",
            "draft_status": "illustrative",
            "source": {"path": source.as_posix(), "sha256": _sha256(source)},
            "output": {"path": output.as_posix(), "format": output.suffix.lstrip(".").lower(),
                       "sha256": _sha256(output)},
            "source_register": {"path": metadata["sources"], "sha256": _sha256(sources_path)},
            "values_table": {"path": metadata["values"], "sha256": _sha256(values_path)},
            "source_versions": [part.strip() for part in metadata["source_versions"].split(";") if part.strip()],
            "target_venue": metadata["target_venue"],
            "word_template": word_template,
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        payload.update(summarize(draft, context, analysis))
        manifest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8",
                            newline="\n")
        created.append(manifest)
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="run-scoped Markdown source")
    parser.add_argument("output", type=Path, nargs="?", help="new .docx or .md file")
    parser.add_argument("--manifest", type=Path, help="new run manifest JSON (required with output)")
    parser.add_argument("--check", action="store_true",
                        help="validate only and print the inventory and warnings; write nothing")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(),
                        help="repository root containing project/")
    args = parser.parse_args()
    try:
        if args.check:
            if args.output or args.manifest:
                raise ValueError("--check writes nothing; omit the output and --manifest")
            summary = check(args.source.resolve(), args.project_root.resolve())
            print(json.dumps({key: summary[key] for key in ("counts", "placeholders", "warnings",
                                                             "sources_unused", "values_unused")},
                             indent=2))
            return 0
        if not args.output or not args.manifest:
            raise ValueError("give an output path and --manifest, or use --check")
        payload = build(args.source.resolve(), args.output.resolve(), args.manifest.resolve(),
                        args.project_root.resolve())
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    counts = payload["counts"]
    print(
        f"Created {args.output} and {args.manifest}: {counts['total_words']} words, "
        f"{counts['footnotes']} footnotes, placeholders {counts['placeholders'] or 'none'}, "
        f"warnings {counts['warnings'] or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
