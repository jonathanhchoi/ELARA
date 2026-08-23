"""Validate and render an ELARA skeleton draft from one canonical Markdown source.

The source is an immutable, run-scoped planning artifact. The builder validates
its article structure, restrained prose, and provenance references, then creates
a new Word, LaTeX, or Markdown researcher-facing artifact and a run manifest.
Existing files are never overwritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


CONTENT_WIDTH_DXA = 9360
NAVY = "17365D"
BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
MUTED = "667085"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F4F6F9"
BORDER = "CBD5E1"
WHITE = "FFFFFF"

REQUIRED_METADATA = (
    "title",
    "subtitle",
    "output_format",
    "target_venue",
    "source_versions",
)
LEGACY_IGNORED_METADATA = {"target_length"}
SUPPORTED_FORMATS = {"docx", "tex", "md"}
REQUIRED_FIELDS = (
    "Section role",
    "Bare-bones content",
    "Source support",
    "Results presented",
    "Displays",
    "Author work",
    "Open questions",
)
LEGACY_IGNORED_FIELDS = {"Approximate length"}
TRACE_FIELDS = {"Bare-bones content", "Source support", "Results presented", "Displays"}
ALWAYS_TRACED_FIELDS = {"Source support", "Results presented", "Displays"}
ALLOWED_ROLES = {
    "abstract",
    "introduction",
    "background",
    "methods",
    "results",
    "robustness",
    "discussion",
    "limitations",
    "conclusion",
    "appendix",
    "other",
}
REQUIRED_TOP_LEVEL_ROLES = {
    "introduction",
    "methods",
    "results",
    "limitations",
    "conclusion",
}
EMPIRICAL_ROLES = {"methods", "results", "robustness"}
AUTHOR_TO_WRITE = "Author to write."
MAX_CONTENT_WORDS = 120
MAX_NONEMPIRICAL_CONTENT_WORDS = 35
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO-SKELETON|TODO|TBD|PLACEHOLDER|INSERT|XXX)\b|<[^>]+>",
    re.IGNORECASE,
)
SECTION_HEADING_RE = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
FIELD_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.*?)\s*$")
PROJECT_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<path>project/[A-Za-z0-9_./-]+)#(?P<id>[A-Za-z0-9_.:-]+)"
)
BARE_PROJECT_REF_RE = re.compile(r"(?<![A-Za-z0-9_])project/[A-Za-z0-9_./-]+(?!#)")
NUMBER_RE = re.compile(r"(?<![A-Za-z])\b\d+(?:\.\d+)?%?\b")
DISPLAY_KINDS = {"table", "figure", "equation"}
DISPLAY_SUFFIXES = {
    "table": {".csv", ".tsv"},
    "figure": {".png", ".jpg", ".jpeg"},
    "equation": {".tex", ".txt"},
}
UNSAFE_TEX_RE = re.compile(
    r"\\(?:input|include|write|openout|read|usepackage|documentclass|begin\s*\{document\}|end\s*\{document\})\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Section:
    title: str
    level: int
    order: int
    fields: dict[str, str]

    @property
    def depth(self) -> int:
        return self.level - 2


@dataclass(frozen=True)
class Display:
    kind: str
    reference: str
    path: str
    artifact_id: str
    caption: str


def parse_displays(value: str) -> list[Display]:
    if value.strip().lower() == "none":
        return []
    displays: list[Display] = []
    for raw_spec in value.split(" || "):
        parts = [part.strip() for part in raw_spec.split("|", 2)]
        if len(parts) != 3 or not all(parts):
            raise ValueError(
                "Displays entries must use kind|project/path#artifact-id|caption, separated by ' || '"
            )
        kind, reference, caption = parts
        kind = kind.lower()
        if kind not in DISPLAY_KINDS:
            raise ValueError(f"unsupported display kind: {kind}")
        match = PROJECT_REF_RE.fullmatch(reference)
        if not match:
            raise ValueError(f"display reference must use project/path#artifact-id: {reference}")
        suffix = Path(match.group("path")).suffix.lower()
        if suffix not in DISPLAY_SUFFIXES[kind]:
            raise ValueError(f"{kind} display has unsupported file extension: {suffix or '(none)'}")
        if PLACEHOLDER_RE.search(caption):
            raise ValueError("display caption contains an unresolved placeholder")
        displays.append(Display(kind, reference, match.group("path"), match.group("id"), caption))
    return displays


def _decode_value(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid quoted metadata value: {value}") from exc
        if not isinstance(parsed, str):
            raise ValueError("metadata values must be strings")
        return parsed.strip()
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            raise ValueError(f"invalid quoted metadata value: {value}")
        return value[1:-1].replace("''", "'").strip()
    return value


def _source_version_paths(value: str) -> list[str]:
    paths = [item.strip() for item in value.split(";") if item.strip()]
    if not paths:
        raise ValueError("source_versions must name at least one verified project artifact")
    for item in paths:
        if not item.startswith("project/") or "#" in item or PLACEHOLDER_RE.search(item):
            raise ValueError(f"invalid source_versions entry: {item}")
    if len(paths) != len(set(paths)):
        raise ValueError("source_versions contains duplicate paths")
    return paths


def parse_source(text: str) -> tuple[dict[str, str], list[Section]]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("source must begin with a metadata block")
    try:
        metadata_end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise ValueError("metadata block has no closing --- line") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:metadata_end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, raw = line.partition(":")
        key = key.strip().lower()
        if not separator or not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ValueError(f"invalid metadata line: {line}")
        if key in metadata:
            raise ValueError(f"duplicate metadata key: {key}")
        metadata[key] = _decode_value(raw)

    missing = [key for key in REQUIRED_METADATA if not metadata.get(key)]
    if missing:
        raise ValueError("missing required metadata: " + ", ".join(missing))
    output_format = metadata["output_format"].lower().lstrip(".")
    if output_format not in SUPPORTED_FORMATS:
        raise ValueError("output_format must be docx, tex, or md")
    metadata["output_format"] = output_format
    _source_version_paths(metadata["source_versions"])
    if PLACEHOLDER_RE.search(normalized):
        raise ValueError("source contains an unresolved placeholder")
    for key in LEGACY_IGNORED_METADATA:
        metadata.pop(key, None)

    sections: list[Section] = []
    current_title = ""
    current_level = 0
    current_fields: dict[str, str] = {}

    def finish_section() -> None:
        nonlocal current_title, current_level, current_fields
        if not current_title:
            return
        missing_fields = [field for field in REQUIRED_FIELDS if not current_fields.get(field)]
        if missing_fields:
            raise ValueError(
                f"section {current_title} is missing required fields: {', '.join(missing_fields)}"
            )
        unknown_fields = sorted(
            set(current_fields) - set(REQUIRED_FIELDS) - LEGACY_IGNORED_FIELDS
        )
        if unknown_fields:
            raise ValueError(
                f"section {current_title} contains unknown fields: {', '.join(unknown_fields)}"
            )
        sections.append(
            Section(
                current_title,
                current_level,
                len(sections) + 1,
                {key: current_fields[key] for key in REQUIRED_FIELDS},
            )
        )
        current_title = ""
        current_level = 0
        current_fields = {}

    for line_number, line in enumerate(lines[metadata_end + 1 :], metadata_end + 2):
        if not line.strip():
            continue
        heading = SECTION_HEADING_RE.fullmatch(line.strip())
        if heading:
            finish_section()
            current_level = len(heading.group(1))
            current_title = heading.group(2).strip()
            continue
        if not current_title:
            raise ValueError(
                f"line {line_number} is outside a section; only structured section records are allowed"
            )
        field = FIELD_RE.fullmatch(line.strip())
        if not field:
            raise ValueError(
                f"line {line_number} is not a structured field; use the Bare-bones content field"
            )
        name, value = field.group(1).strip(), field.group(2).strip()
        if name in current_fields:
            raise ValueError(f"section {current_title} repeats field {name}")
        current_fields[name] = value
    finish_section()

    validate_sections(sections)
    return metadata, sections


def validate_sections(sections: list[Section]) -> None:
    top_level = [section for section in sections if section.depth == 0]
    if len(top_level) < 5:
        raise ValueError("skeleton draft must contain at least five top-level sections")
    titles = [section.title.casefold() for section in sections]
    if len(titles) != len(set(titles)):
        raise ValueError("section headings must be unique")

    previous_level = 1
    empirical_content_roles: set[str] = set()
    for section in sections:
        if section.level == 2:
            previous_level = 2
        elif section.level > previous_level + 1:
            raise ValueError(
                f"section {section.title} skips a Markdown heading level"
            )
        previous_level = section.level

        role = section.fields["Section role"].strip().lower()
        if role not in ALLOWED_ROLES:
            raise ValueError(
                f"section {section.title} has unsupported Section role {section.fields['Section role']}"
            )

        content = section.fields["Bare-bones content"].strip()
        word_count = len(re.findall(r"\b[\w'-]+\b", content))
        if word_count > MAX_CONTENT_WORDS:
            raise ValueError(
                f"section {section.title} Bare-bones content exceeds {MAX_CONTENT_WORDS} words"
            )
        if role not in EMPIRICAL_ROLES and content.casefold() != AUTHOR_TO_WRITE.casefold():
            if word_count > MAX_NONEMPIRICAL_CONTENT_WORDS:
                raise ValueError(
                    f"section {section.title} leaves too much non-empirical prose for the agent"
                )
            if len(re.findall(r"[.!?](?:\s|$)", content)) > 1:
                raise ValueError(
                    f"section {section.title} non-empirical content must be one sentence or less"
                )
        if role in EMPIRICAL_ROLES and content.casefold() != AUTHOR_TO_WRITE.casefold():
            empirical_content_roles.add(role)

        displays = parse_displays(section.fields["Displays"])
        results_value = section.fields["Results presented"].strip()
        if role in {"results", "robustness"}:
            if results_value.lower() == "none":
                raise ValueError(
                    f"section {section.title} must identify the results it presents"
                )
            if not displays:
                raise ValueError(
                    f"section {section.title} must present results through at least one table, figure, or equation"
                )

        section_refs = [
            match
            for field_name in TRACE_FIELDS
            for match in PROJECT_REF_RE.finditer(section.fields[field_name])
        ]
        for field_name in TRACE_FIELDS:
            value = section.fields[field_name]
            refs = list(PROJECT_REF_RE.finditer(value))
            value_without_refs = PROJECT_REF_RE.sub("", value)
            if BARE_PROJECT_REF_RE.search(value_without_refs):
                raise ValueError(
                    f"section {section.title} {field_name} artifact references require #ID"
                )
            if field_name in ALWAYS_TRACED_FIELDS and value.lower() != "none" and not refs:
                raise ValueError(
                    f"section {section.title} {field_name} must be 'none' or cite project/...#ID"
                )
            if NUMBER_RE.search(value) and not section_refs:
                raise ValueError(
                    f"section {section.title} {field_name} contains an untraced number"
                )

    top_roles = {section.fields["Section role"].strip().lower() for section in top_level}
    missing_roles = sorted(REQUIRED_TOP_LEVEL_ROLES - top_roles)
    if missing_roles:
        raise ValueError(
            "skeleton draft is not organizationally complete; missing top-level roles: "
            + ", ".join(missing_roles)
        )
    for required_role in ("methods", "results"):
        if required_role not in empirical_content_roles:
            raise ValueError(
                f"skeleton draft must include bare-bones {required_role} content"
            )


def validate_artifact_references(
    metadata: dict[str, str], sections: list[Section], project_root: Path
) -> None:
    repository_root = _repository_root(project_root)
    referenced = _source_version_paths(metadata["source_versions"])
    referenced.extend(
        match.group("path")
        for section in sections
        for value in section.fields.values()
        for match in PROJECT_REF_RE.finditer(value)
    )
    resolved = {
        item: _resolve_project_path(repository_root, item) for item in set(referenced)
    }
    missing = sorted(item for item, path in resolved.items() if not path.exists())
    if missing:
        raise ValueError("referenced project artifacts do not exist: " + ", ".join(missing))

    for section in sections:
        for display in parse_displays(section.fields["Displays"]):
            path = _resolve_project_path(repository_root, display.path)
            if display.kind == "table":
                _read_table(path)
            elif display.kind == "equation":
                _read_equation(path)


def _repository_root(project_root: Path) -> Path:
    return project_root.parent if project_root.name == "project" else project_root


def _resolve_project_path(repository_root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or not relative.parts or relative.parts[0] != "project":
        raise ValueError(f"artifact reference must remain under project/: {value}")
    project_directory = (repository_root / "project").resolve()
    resolved = (repository_root / relative).resolve()
    try:
        resolved.relative_to(project_directory)
    except ValueError as exc:
        raise ValueError(f"artifact reference escapes project/: {value}") from exc
    return resolved


def _read_table(path: Path) -> list[list[str]]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [[cell.strip() for cell in row] for row in csv.reader(handle, delimiter=delimiter)]
    if not rows or not rows[0]:
        raise ValueError(f"display table is empty: {path}")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError(f"display table has inconsistent row widths: {path}")
    if len(rows) > 200 or width > 25:
        raise ValueError(f"display table is too large for a skeleton draft: {path}")
    return rows


def _read_equation(path: Path) -> str:
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"display equation is empty: {path}")
    if len(value) > 4000:
        raise ValueError(f"display equation is too long: {path}")
    if UNSAFE_TEX_RE.search(value):
        raise ValueError(f"display equation contains an unsafe LaTeX command: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _set_style_font(style, size: float, color: str, *, bold: bool = False) -> None:
    style.font.name = "Calibri"
    style.font.size = Pt(size)
    style.font.color.rgb = RGBColor.from_string(color)
    style.font.bold = bold
    r_pr = style.element.get_or_add_rPr()
    fonts = r_pr.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, fonts)
    for key in ("ascii", "hAnsi", "eastAsia"):
        fonts.set(qn(f"w:{key}"), "Calibri")


def _configure_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.85)
    section.bottom_margin = Inches(0.8)
    section.left_margin = Inches(0.95)
    section.right_margin = Inches(0.95)
    section.header_distance = Inches(0.35)
    section.footer_distance = Inches(0.35)
    section.different_first_page_header_footer = False
    doc.settings.odd_and_even_pages_header_footer = False

    normal = doc.styles["Normal"]
    _set_style_font(normal, 10.5, "222222")
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.08
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for name, size, before, after in (
        ("Title", 24, 0, 4),
        ("Subtitle", 11.5, 0, 14),
        ("Heading 1", 15, 14, 6),
        ("Heading 2", 12.5, 10, 4),
        ("Heading 3", 11.5, 8, 3),
        ("Heading 4", 10.5, 7, 3),
    ):
        style = doc.styles[name]
        _set_style_font(style, size, BLUE if name != "Title" else NAVY, bold=True)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.keep_together = True


def _set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def _set_table_geometry(table, widths: list[int]) -> None:
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    tbl_pr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    table_width = OxmlElement("w:tblW")
    table_width.set(qn("w:w"), str(sum(widths)))
    table_width.set(qn("w:type"), "dxa")
    tbl_pr.insert(0, table_width)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{edge}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:color"), BORDER)
        borders.append(border)
    tbl_pr.append(borders)
    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        column = OxmlElement("w:gridCol")
        column.set(qn("w:w"), str(width))
        grid.append(column)
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_width = OxmlElement("w:tcW")
            tc_width.set(qn("w:w"), str(width))
            tc_width.set(qn("w:type"), "dxa")
            tc_pr.append(tc_width)
            margins = OxmlElement("w:tcMar")
            for side, value in (("top", 70), ("left", 100), ("bottom", 70), ("right", 100)):
                node = OxmlElement(f"w:{side}")
                node.set(qn("w:w"), str(value))
                node.set(qn("w:type"), "dxa")
                margins.append(node)
            tc_pr.append(margins)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def _repeat_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def _add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, end])


def _add_docx_displays(doc: Document, section: Section, repository_root: Path) -> None:
    for display in parse_displays(section.fields["Displays"]):
        path = _resolve_project_path(repository_root, display.path)
        label = display.kind.capitalize()
        caption = doc.add_paragraph()
        caption.paragraph_format.keep_with_next = True
        caption.add_run(f"{label}. ").bold = True
        caption.add_run(display.caption)
        source = doc.add_paragraph()
        source.paragraph_format.keep_with_next = True
        source_run = source.add_run(display.reference)
        source_run.italic = True
        source_run.font.size = Pt(8.5)
        source_run.font.color.rgb = RGBColor.from_string(MUTED)
        if display.kind == "table":
            rows = _read_table(path)
            table = doc.add_table(rows=len(rows), cols=len(rows[0]))
            table.style = "Table Grid"
            if rows:
                _repeat_header(table.rows[0])
            widths = [CONTENT_WIDTH_DXA // len(rows[0])] * len(rows[0])
            _set_table_geometry(table, widths)
            for row_index, (word_row, values) in enumerate(zip(table.rows, rows)):
                for cell, value in zip(word_row.cells, values):
                    cell.text = value
                    _set_cell_shading(cell, LIGHT_BLUE if row_index == 0 else WHITE)
                    if row_index == 0:
                        for run in cell.paragraphs[0].runs:
                            run.bold = True
        elif display.kind == "figure":
            paragraph = doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run()
            run.add_picture(str(path), width=Inches(6.2))
        else:
            paragraph = doc.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = paragraph.add_run(_read_equation(path))
            run.font.name = "Cambria Math"
            run.font.size = Pt(11)


def build_docx(
    metadata: dict[str, str], sections: list[Section], output: Path, repository_root: Path
) -> None:
    doc = Document()
    _configure_document(doc)
    doc.core_properties.title = metadata["title"]
    doc.core_properties.subject = "ELARA Stage 17 article skeleton"
    doc.core_properties.author = "ELARA"
    fixed_time = datetime(2000, 1, 1, tzinfo=timezone.utc)
    doc.core_properties.created = fixed_time
    doc.core_properties.modified = fixed_time

    header = doc.sections[0].header.paragraphs[0]
    header.text = "ELARA  |  SKELETON DRAFT"
    for run in header.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(8.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor.from_string(MUTED)
    footer = doc.sections[0].footer.paragraphs[0]
    _add_page_number(footer)

    kicker = doc.add_paragraph()
    kicker.paragraph_format.space_after = Pt(3)
    run = kicker.add_run("ELARA SKELETON DRAFT")
    run.bold = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor.from_string(BLUE)
    doc.add_paragraph(metadata["title"], style="Title")
    doc.add_paragraph(metadata["subtitle"], style="Subtitle")

    callout = doc.add_table(rows=1, cols=1)
    _set_table_geometry(callout, [CONTENT_WIDTH_DXA])
    _set_cell_shading(callout.cell(0, 0), LIGHT_GRAY)
    paragraph = callout.cell(0, 0).paragraphs[0]
    paragraph.add_run("Authoring boundary. ").bold = True
    paragraph.add_run(
        "This draft supplies the complete article structure and only minimal methods and "
        "results language. The researcher writes the substantive prose."
    )

    for label, value in (
        ("Target venue", metadata["target_venue"]),
        ("Verified source set", metadata["source_versions"]),
    ):
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.add_run(f"{label}: ").bold = True
        paragraph.add_run(value)

    doc.add_paragraph("Article structure", style="Heading 1")
    overview = doc.add_table(rows=1 + len(sections), cols=2)
    _repeat_header(overview.rows[0])
    for cell, value in zip(overview.rows[0].cells, ("Section", "Role")):
        _set_cell_shading(cell, LIGHT_BLUE)
        paragraph = cell.paragraphs[0]
        paragraph.add_run(value).bold = True
    for row, section in zip(overview.rows[1:], sections):
        cells = row.cells
        values = (
            f"{'  ' * section.depth}{section.title}",
            section.fields["Section role"],
        )
        for cell, value in zip(cells, values):
            cell.text = value
            _set_cell_shading(cell, WHITE)
    _set_table_geometry(overview, [7000, 2360])

    doc.add_page_break()
    doc.add_paragraph("Skeleton draft", style="Heading 1")
    for section in sections:
        heading_level = min(section.depth + 1, 4)
        doc.add_paragraph(section.title, style=f"Heading {heading_level}")
        content = doc.add_paragraph()
        content.paragraph_format.space_after = Pt(6)
        content_run = content.add_run(section.fields["Bare-bones content"])
        if section.fields["Bare-bones content"].casefold() == AUTHOR_TO_WRITE.casefold():
            content_run.italic = True
            content_run.font.color.rgb = RGBColor.from_string(MUTED)
        for field_name in (
            "Source support",
            "Results presented",
            "Author work",
            "Open questions",
        ):
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.15)
            paragraph.paragraph_format.first_line_indent = Inches(-0.15)
            paragraph.add_run(f"{field_name}: ").bold = True
            paragraph.add_run(section.fields[field_name])
        _add_docx_displays(doc, section, repository_root)
    doc.save(output)


def _latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def _latex_text_with_refs(value: str) -> str:
    pieces: list[str] = []
    cursor = 0
    for match in PROJECT_REF_RE.finditer(value):
        pieces.append(_latex_escape(value[cursor : match.start()]))
        pieces.append(r"\path{" + match.group(0) + "}")
        cursor = match.end()
    pieces.append(_latex_escape(value[cursor:]))
    return "".join(pieces)


def _latex_displays(display_value: str, repository_root: Path, output: Path) -> list[str]:
    lines: list[str] = []
    for display in parse_displays(display_value):
        path = _resolve_project_path(repository_root, display.path)
        lines.append(
            rf"\textbf{{{display.kind.capitalize()}.}} {_latex_escape(display.caption)}"
        )
        lines.append(rf"\textit{{Source:}} \path{{{display.reference}}}")
        if display.kind == "table":
            rows = _read_table(path)
            columns = "l" * len(rows[0])
            lines.extend([r"\begin{center}", r"\resizebox{\linewidth}{!}{%", rf"\begin{{tabular}}{{{columns}}}", r"\hline"])
            for index, row in enumerate(rows):
                content = " & ".join(_latex_escape(cell) for cell in row) + r" \\"
                if index == 0:
                    content = r"\textbf{" + (r"} & \textbf{".join(_latex_escape(cell) for cell in row)) + r"} \\ \hline"
                lines.append(content)
            lines.extend([r"\hline", r"\end{tabular}%", r"}", r"\end{center}"])
        elif display.kind == "figure":
            relative = Path(os.path.relpath(path, output.parent)).as_posix()
            lines.extend(
                [
                    r"\begin{center}",
                    rf"\includegraphics[width=0.92\linewidth]{{\detokenize{{{relative}}}}}",
                    r"\end{center}",
                ]
            )
        else:
            lines.extend([r"\[", _read_equation(path), r"\]"])
    return lines


def build_tex(
    metadata: dict[str, str], sections: list[Section], output: Path, repository_root: Path
) -> None:
    heading_commands = ("section", "subsection", "subsubsection", "paragraph")
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[letterpaper,margin=1in]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{lmodern}",
        r"\usepackage{xcolor}",
        r"\usepackage{tabularx}",
        r"\usepackage{graphicx}",
        r"\usepackage{fancyhdr}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\definecolor{ELARABlue}{HTML}{2E74B5}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\lhead{\small\color{gray} ELARA | SKELETON DRAFT}",
        r"\rfoot{\thepage}",
        r"\fancypagestyle{plain}{\fancyhf{}\lhead{\small\color{gray} ELARA | SKELETON DRAFT}\rfoot{\thepage}}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{5pt}",
        r"\setlength{\emergencystretch}{3em}",
        r"\raggedright",
        r"\sloppy",
        rf"\title{{{_latex_escape(metadata['title'])}}}",
        rf"\author{{{_latex_escape(metadata['subtitle'])}}}",
        r"\date{}",
        r"\begin{document}",
        r"\maketitle",
        r"\begin{center}\fcolorbox{ELARABlue}{gray!8}{\parbox{0.88\linewidth}{\textbf{Authoring boundary.} This draft supplies the complete article structure and only minimal methods and results language. The researcher writes the substantive prose.}}\end{center}",
        r"\begin{itemize}",
        rf"\item \textbf{{Target venue:}} {_latex_escape(metadata['target_venue'])}",
        r"\item \textbf{Verified source set:}",
        r"\begin{itemize}",
        *(
            rf"\item \path{{{path}}}"
            for path in _source_version_paths(metadata["source_versions"])
        ),
        r"\end{itemize}",
        r"\end{itemize}",
        r"\section*{Article structure}",
        r"\begin{tabularx}{\linewidth}{@{}X p{0.22\linewidth}@{}}",
        r"\textbf{Section} & \textbf{Role} \\\hline",
    ]
    for section in sections:
        lines.append(
            f"{_latex_escape('  ' * section.depth + section.title)} & "
            f"{_latex_escape(section.fields['Section role'])} \\\\"
        )
    lines.extend([r"\end{tabularx}", r"\clearpage", r"\section*{Skeleton draft}"])
    for section in sections:
        command = heading_commands[min(section.depth, len(heading_commands) - 1)]
        lines.append(rf"\{command}*{{{_latex_escape(section.title)}}}")
        content = _latex_text_with_refs(section.fields["Bare-bones content"])
        if section.fields["Bare-bones content"].casefold() == AUTHOR_TO_WRITE.casefold():
            lines.append(rf"\textcolor{{gray}}{{\emph{{{content}}}}}")
        else:
            lines.append(content)
        lines.append(r"\begin{description}")
        for field_name in (
            "Source support",
            "Results presented",
            "Author work",
            "Open questions",
        ):
            lines.append(
                rf"\item[{_latex_escape(field_name)}] {_latex_text_with_refs(section.fields[field_name])}"
            )
        lines.append(r"\end{description}")
        lines.extend(_latex_displays(section.fields["Displays"], repository_root, output))
    lines.extend([r"\end{document}", ""])
    output.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def _markdown_displays(display_value: str, repository_root: Path, output: Path) -> list[str]:
    lines: list[str] = []
    for display in parse_displays(display_value):
        path = _resolve_project_path(repository_root, display.path)
        lines.extend(
            [
                f"**{display.kind.capitalize()}.** {display.caption}",
                "",
                f"*Source: `{display.reference}`*",
                "",
            ]
        )
        if display.kind == "table":
            rows = _read_table(path)
            lines.append("| " + " | ".join(rows[0]) + " |")
            lines.append("|" + "|".join("---" for _ in rows[0]) + "|")
            lines.extend("| " + " | ".join(row) + " |" for row in rows[1:])
        elif display.kind == "figure":
            relative = Path(os.path.relpath(path, output.parent)).as_posix()
            lines.append(f"![{display.caption}]({relative})")
        else:
            lines.extend(["$$", _read_equation(path), "$$"])
        lines.append("")
    return lines


def build_markdown(
    metadata: dict[str, str], sections: list[Section], output: Path, repository_root: Path
) -> None:
    lines = [
        f"# {metadata['title']}",
        "",
        f"*{metadata['subtitle']}*",
        "",
        "> **Authoring boundary.** This draft supplies the complete article structure and only minimal methods and results language. The researcher writes the substantive prose.",
        "",
        f"- **Target venue:** {metadata['target_venue']}",
        f"- **Verified source set:** {metadata['source_versions']}",
        "",
        "## Article structure",
        "",
        "| Section | Role |",
        "|---|---|",
    ]
    for section in sections:
        lines.append(
            f"| {'&nbsp;' * (section.depth * 4)}{section.title} | "
            f"{section.fields['Section role']} |"
        )
    lines.extend(["", "## Skeleton draft", ""])
    for section in sections:
        level = min(3 + section.depth, 6)
        lines.append(f"{'#' * level} {section.title}")
        lines.append("")
        content = section.fields["Bare-bones content"]
        if content.casefold() == AUTHOR_TO_WRITE.casefold():
            lines.append(f"*{content}*")
        else:
            lines.append(content)
        lines.append("")
        for field_name in (
            "Source support",
            "Results presented",
            "Author work",
            "Open questions",
        ):
            lines.append(f"**{field_name}:** {section.fields[field_name]}")
            lines.append("")
        lines.extend(_markdown_displays(section.fields["Displays"], repository_root, output))
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def _validate_output(path: Path, output_format: str, sections: list[Section]) -> None:
    if output_format == "docx":
        reopened = Document(path)
        headings = {
            paragraph.text.strip()
            for paragraph in reopened.paragraphs
            if paragraph.style is not None and paragraph.style.name.startswith("Heading")
        }
        missing = [section.title for section in sections if section.title not in headings]
        if missing:
            raise ValueError("generated Word artifact is missing sections: " + ", ".join(missing))
        if not reopened.tables:
            raise ValueError("generated Word artifact is missing table geometry")
    else:
        text = path.read_text(encoding="utf-8")
        missing = [section.title for section in sections if section.title not in text]
        if missing:
            raise ValueError("generated artifact is missing sections: " + ", ".join(missing))
        if PLACEHOLDER_RE.search(text):
            raise ValueError("generated artifact contains an unresolved placeholder")


def build(
    source: Path,
    output: Path,
    manifest: Path,
    project_root: Path,
) -> None:
    if source.suffix.lower() != ".md":
        raise ValueError("source must be a .md file")
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    for path in (output, manifest):
        if path.exists():
            raise ValueError(f"refusing to overwrite existing artifact: {path}")
    if manifest.suffix.lower() != ".json":
        raise ValueError("manifest must be a .json file")

    metadata, sections = parse_source(source.read_text(encoding="utf-8"))
    output_format = metadata["output_format"]
    if output.suffix.lower() != f".{output_format}":
        raise ValueError(
            f"output extension {output.suffix or '(none)'} does not match output_format {output_format}"
        )
    validate_artifact_references(metadata, sections, project_root)
    repository_root = _repository_root(project_root)

    for path in (output, manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        if output_format == "docx":
            build_docx(metadata, sections, output, repository_root)
        elif output_format == "tex":
            build_tex(metadata, sections, output, repository_root)
        else:
            build_markdown(metadata, sections, output, repository_root)
        created.append(output)
        _validate_output(output, output_format, sections)

        manifest_payload = {
            "schema_version": "1.1",
            "stage_id": "17-skeleton-draft",
            "source": {"path": source.as_posix(), "sha256": _sha256(source)},
            "output": {
                "path": output.as_posix(),
                "format": output_format,
                "sha256": _sha256(output),
            },
            "sections": [
                {
                    "title": section.title,
                    "level": section.level,
                    "order": section.order,
                    "role": section.fields["Section role"],
                }
                for section in sections
            ],
            "displays": [
                {
                    "section": section.title,
                    "kind": display.kind,
                    "reference": display.reference,
                    "caption": display.caption,
                }
                for section in sections
                for display in parse_displays(section.fields["Displays"])
            ],
            "verified_source_versions": _source_version_paths(metadata["source_versions"]),
        }
        manifest.write_text(
            json.dumps(manifest_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        created.append(manifest)
    except Exception:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="immutable run-scoped Markdown source")
    parser.add_argument("output", type=Path, help="new .docx, .tex, or .md artifact")
    parser.add_argument("--manifest", type=Path, required=True, help="new run manifest JSON")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="repository root containing project/",
    )
    args = parser.parse_args()
    try:
        build(
            args.source.resolve(),
            args.output.resolve(),
            args.manifest.resolve(),
            args.project_root.resolve(),
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Created {args.output} and {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
