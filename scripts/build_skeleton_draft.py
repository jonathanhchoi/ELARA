"""Validate and render an ELARA article skeleton from one canonical Markdown source.

The source is an immutable, run-scoped planning artifact. The builder validates
its section hierarchy and provenance references, then creates a new Word,
LaTeX, or Markdown researcher-facing artifact, a machine-readable crosswalk,
and a run manifest. Existing files are never overwritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
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
    "target_length",
    "source_versions",
)
SUPPORTED_FORMATS = {"docx", "tex", "md"}
REQUIRED_FIELDS = (
    "Purpose",
    "Claims",
    "Evidence",
    "Results",
    "Tables and figures",
    "Counterarguments",
    "Limitations",
    "Open questions",
    "Approximate length",
)
TRACE_FIELDS = {"Claims", "Evidence", "Results", "Tables and figures"}
ALWAYS_TRACED_FIELDS = {"Evidence", "Results", "Tables and figures"}
PLACEHOLDER_RE = re.compile(
    r"\b(?:TODO-SKELETON|TODO|TBD|PLACEHOLDER|INSERT|XXX)\b|<[^>]+>",
    re.IGNORECASE,
)
SECTION_HEADING_RE = re.compile(
    r"^(#{2,6})\s+\[(S\d{2}(?:\.\d{2})*)\]\s+(.+?)\s*$"
)
FIELD_RE = re.compile(r"^\*\*([^*]+):\*\*\s*(.*?)\s*$")
PROJECT_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<path>project/[A-Za-z0-9_./-]+)#(?P<id>[A-Za-z0-9_.:-]+)"
)
BARE_PROJECT_REF_RE = re.compile(r"(?<![A-Za-z0-9_])project/[A-Za-z0-9_./-]+(?!#)")
OMISSION_RE = re.compile(r"(?<![A-Za-z0-9_])omit:(?P<id>[A-Za-z0-9_.:-]+)")
NUMBER_RE = re.compile(r"(?<![A-Za-z])\b\d+(?:\.\d+)?%?\b")
LENGTH_RE = re.compile(r"\b\d[\d,]*(?:\s*[–-]\s*\d[\d,]*)?\s+(?:words?|pages?)\b", re.I)
CROSSWALK_COLUMNS = (
    "section_id",
    "parent_id",
    "section_order",
    "section_title",
    "field",
    "artifact_path",
    "artifact_id",
    "disposition",
    "note",
)


@dataclass(frozen=True)
class Section:
    section_id: str
    title: str
    level: int
    order: int
    fields: dict[str, str]

    @property
    def depth(self) -> int:
        return self.section_id.count(".")

    @property
    def parent_id(self) -> str:
        return self.section_id.rpartition(".")[0]


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

    sections: list[Section] = []
    current_id = ""
    current_title = ""
    current_level = 0
    current_fields: dict[str, str] = {}

    def finish_section() -> None:
        nonlocal current_id, current_title, current_level, current_fields
        if not current_id:
            return
        missing_fields = [field for field in REQUIRED_FIELDS if not current_fields.get(field)]
        if missing_fields:
            raise ValueError(
                f"section {current_id} is missing required fields: {', '.join(missing_fields)}"
            )
        unknown_fields = sorted(set(current_fields) - set(REQUIRED_FIELDS))
        if unknown_fields:
            raise ValueError(
                f"section {current_id} contains unknown fields: {', '.join(unknown_fields)}"
            )
        sections.append(
            Section(current_id, current_title, current_level, len(sections) + 1, dict(current_fields))
        )
        current_id = ""
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
            current_id = heading.group(2)
            current_title = heading.group(3).strip()
            continue
        if not current_id:
            raise ValueError(
                f"line {line_number} is outside a section; only structured section records are allowed"
            )
        field = FIELD_RE.fullmatch(line.strip())
        if not field:
            raise ValueError(
                f"line {line_number} is not a structured field; article paragraphs are not allowed"
            )
        name, value = field.group(1).strip(), field.group(2).strip()
        if name in current_fields:
            raise ValueError(f"section {current_id} repeats field {name}")
        current_fields[name] = value
    finish_section()

    validate_sections(sections)
    return metadata, sections


def validate_sections(sections: list[Section]) -> None:
    if len([section for section in sections if section.depth == 0]) < 2:
        raise ValueError("skeleton must contain at least two top-level sections")
    ids = [section.section_id for section in sections]
    if len(ids) != len(set(ids)):
        raise ValueError("section IDs must be unique")

    expected_by_parent: dict[str, int] = {}
    seen: set[str] = set()
    for section in sections:
        expected_level = 2 + section.depth
        if section.level != expected_level:
            raise ValueError(
                f"section {section.section_id} must use Markdown heading level {expected_level}"
            )
        if section.parent_id and section.parent_id not in seen:
            raise ValueError(
                f"section {section.section_id} appears before or without parent {section.parent_id}"
            )
        parent = section.parent_id
        expected_number = expected_by_parent.get(parent, 1)
        actual_number = int(section.section_id.rsplit(".", 1)[-1].removeprefix("S"))
        if actual_number != expected_number:
            expected_id = (
                f"{parent}.{expected_number:02d}" if parent else f"S{expected_number:02d}"
            )
            raise ValueError(
                f"section order is not sequential: expected {expected_id}, found {section.section_id}"
            )
        expected_by_parent[parent] = expected_number + 1
        seen.add(section.section_id)

        if not LENGTH_RE.search(section.fields["Approximate length"]):
            raise ValueError(
                f"section {section.section_id} Approximate length must state words or pages"
            )
        for field_name in TRACE_FIELDS:
            value = section.fields[field_name]
            refs = list(PROJECT_REF_RE.finditer(value))
            if BARE_PROJECT_REF_RE.search(value) and not refs:
                raise ValueError(
                    f"section {section.section_id} {field_name} artifact references require #ID"
                )
            if field_name in ALWAYS_TRACED_FIELDS and value.lower() != "none" and not refs:
                raise ValueError(
                    f"section {section.section_id} {field_name} must be 'none' or cite project/...#ID"
                )
            if NUMBER_RE.search(value) and not refs:
                raise ValueError(
                    f"section {section.section_id} {field_name} contains an untraced number"
                )
            ref_ids = {match.group("id") for match in refs}
            for omission in OMISSION_RE.finditer(value):
                if omission.group("id") not in ref_ids:
                    raise ValueError(
                        f"section {section.section_id} omission {omission.group('id')} lacks its source reference"
                    )


def validate_artifact_references(
    metadata: dict[str, str], sections: list[Section], project_root: Path
) -> None:
    if project_root.name == "project":
        repository_root = project_root.parent
    else:
        repository_root = project_root
    referenced = _source_version_paths(metadata["source_versions"])
    referenced.extend(
        match.group("path")
        for section in sections
        for value in section.fields.values()
        for match in PROJECT_REF_RE.finditer(value)
    )
    missing = sorted(
        item for item in set(referenced) if not (repository_root / Path(item)).exists()
    )
    if missing:
        raise ValueError("referenced project artifacts do not exist: " + ", ".join(missing))


def make_crosswalk_rows(sections: list[Section]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for section in sections:
        for field_name in REQUIRED_FIELDS:
            value = section.fields[field_name]
            refs = list(PROJECT_REF_RE.finditer(value))
            omissions = {match.group("id") for match in OMISSION_RE.finditer(value)}
            for match in refs:
                artifact_id = match.group("id")
                rows.append(
                    {
                        "section_id": section.section_id,
                        "parent_id": section.parent_id,
                        "section_order": str(section.order),
                        "section_title": section.title,
                        "field": field_name,
                        "artifact_path": match.group("path"),
                        "artifact_id": artifact_id,
                        "disposition": "omitted" if artifact_id in omissions else "placed",
                        "note": value,
                    }
                )
    validate_crosswalk(rows, sections)
    return rows


def validate_crosswalk(rows: list[dict[str, str]], sections: list[Section]) -> None:
    section_map = {section.section_id: section for section in sections}
    seen: set[tuple[str, str, str, str]] = set()
    for index, row in enumerate(rows, 2):
        if set(row) != set(CROSSWALK_COLUMNS):
            raise ValueError(f"crosswalk row {index} has malformed columns")
        section = section_map.get(row["section_id"])
        if section is None or row["section_title"] != section.title:
            raise ValueError(f"crosswalk row {index} has an unknown or mismatched section")
        if row["parent_id"] != section.parent_id or row["section_order"] != str(section.order):
            raise ValueError(f"crosswalk row {index} has inconsistent hierarchy or order")
        if row["field"] not in REQUIRED_FIELDS:
            raise ValueError(f"crosswalk row {index} has an unknown field")
        if row["disposition"] not in {"placed", "omitted"}:
            raise ValueError(f"crosswalk row {index} has an invalid disposition")
        if not row["artifact_path"].startswith("project/") or not row["artifact_id"]:
            raise ValueError(f"crosswalk row {index} lacks artifact provenance")
        key = (row["section_id"], row["field"], row["artifact_path"], row["artifact_id"])
        if key in seen:
            raise ValueError(f"crosswalk row {index} duplicates an earlier mapping")
        seen.add(key)
    if not rows:
        raise ValueError("crosswalk must contain at least one traceability row")


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


def build_docx(metadata: dict[str, str], sections: list[Section], output: Path) -> None:
    doc = Document()
    _configure_document(doc)
    doc.core_properties.title = metadata["title"]
    doc.core_properties.subject = "ELARA Stage 17 article skeleton"
    doc.core_properties.author = "ELARA"
    fixed_time = datetime(2000, 1, 1, tzinfo=timezone.utc)
    doc.core_properties.created = fixed_time
    doc.core_properties.modified = fixed_time

    header = doc.sections[0].header.paragraphs[0]
    header.text = "ELARA  |  ARTICLE SKELETON"
    for run in header.runs:
        run.font.name = "Calibri"
        run.font.size = Pt(8.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor.from_string(MUTED)
    footer = doc.sections[0].footer.paragraphs[0]
    _add_page_number(footer)

    kicker = doc.add_paragraph()
    kicker.paragraph_format.space_after = Pt(3)
    run = kicker.add_run("ELARA PLANNING ARTIFACT")
    run.bold = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor.from_string(BLUE)
    doc.add_paragraph(metadata["title"], style="Title")
    doc.add_paragraph(metadata["subtitle"], style="Subtitle")

    callout = doc.add_table(rows=1, cols=1)
    _set_table_geometry(callout, [CONTENT_WIDTH_DXA])
    _set_cell_shading(callout.cell(0, 0), LIGHT_GRAY)
    paragraph = callout.cell(0, 0).paragraphs[0]
    paragraph.add_run("Planning boundary. ").bold = True
    paragraph.add_run(
        "This document arranges verified claims and evidence. It is not article prose."
    )

    for label, value in (
        ("Target venue", metadata["target_venue"]),
        ("Target length", metadata["target_length"]),
        ("Verified source set", metadata["source_versions"]),
    ):
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.add_run(f"{label}: ").bold = True
        paragraph.add_run(value)

    doc.add_paragraph("Proposed order", style="Heading 1")
    overview = doc.add_table(rows=1 + len(sections), cols=3)
    _repeat_header(overview.rows[0])
    for cell, value in zip(overview.rows[0].cells, ("ID", "Section and purpose", "Approx. length")):
        _set_cell_shading(cell, LIGHT_BLUE)
        paragraph = cell.paragraphs[0]
        paragraph.add_run(value).bold = True
    for row, section in zip(overview.rows[1:], sections):
        cells = row.cells
        values = (
            section.section_id,
            f"{section.title}. {section.fields['Purpose']}",
            section.fields["Approximate length"],
        )
        for cell, value in zip(cells, values):
            cell.text = value
            _set_cell_shading(cell, WHITE)
    _set_table_geometry(overview, [1150, 6010, 2200])

    doc.add_page_break()
    doc.add_paragraph("Section-by-section map", style="Heading 1")
    for section in sections:
        heading_level = min(section.depth + 1, 4)
        doc.add_paragraph(
            f"[{section.section_id}] {section.title}", style=f"Heading {heading_level}"
        )
        for field_name in REQUIRED_FIELDS:
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.left_indent = Inches(0.15)
            paragraph.paragraph_format.first_line_indent = Inches(-0.15)
            paragraph.add_run(f"{field_name}: ").bold = True
            paragraph.add_run(section.fields[field_name])
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


def build_tex(metadata: dict[str, str], sections: list[Section], output: Path) -> None:
    heading_commands = ("section", "subsection", "subsubsection", "paragraph")
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[letterpaper,margin=1in]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{lmodern}",
        r"\usepackage{xcolor}",
        r"\usepackage{tabularx}",
        r"\usepackage{fancyhdr}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\definecolor{ELARABlue}{HTML}{2E74B5}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\lhead{\small\color{gray} ELARA | ARTICLE SKELETON}",
        r"\rfoot{\thepage}",
        r"\fancypagestyle{plain}{\fancyhf{}\lhead{\small\color{gray} ELARA | ARTICLE SKELETON}\rfoot{\thepage}}",
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
        r"\begin{center}\fcolorbox{ELARABlue}{gray!8}{\parbox{0.88\linewidth}{\textbf{Planning boundary.} This document arranges verified claims and evidence. It is not article prose.}}\end{center}",
        r"\begin{itemize}",
        rf"\item \textbf{{Target venue:}} {_latex_escape(metadata['target_venue'])}",
        rf"\item \textbf{{Target length:}} {_latex_escape(metadata['target_length'])}",
        r"\item \textbf{Verified source set:}",
        r"\begin{itemize}",
        *(
            rf"\item \path{{{path}}}"
            for path in _source_version_paths(metadata["source_versions"])
        ),
        r"\end{itemize}",
        r"\end{itemize}",
        r"\section*{Proposed order}",
        r"\begin{tabularx}{\linewidth}{@{}p{0.11\linewidth}X p{0.19\linewidth}@{}}",
        r"\textbf{ID} & \textbf{Section and purpose} & \textbf{Approx. length} \\\hline",
    ]
    for section in sections:
        lines.append(
            f"{_latex_escape(section.section_id)} & "
            f"{_latex_escape(section.title + '. ' + section.fields['Purpose'])} & "
            f"{_latex_escape(section.fields['Approximate length'])} \\\\"
        )
    lines.extend([r"\end{tabularx}", r"\clearpage", r"\section*{Section-by-section map}"])
    for section in sections:
        command = heading_commands[min(section.depth, len(heading_commands) - 1)]
        lines.append(
            rf"\{command}*{{[{_latex_escape(section.section_id)}] {_latex_escape(section.title)}}}"
        )
        lines.append(r"\begin{description}")
        for field_name in REQUIRED_FIELDS:
            lines.append(
                rf"\item[{_latex_escape(field_name)}] {_latex_text_with_refs(section.fields[field_name])}"
            )
        lines.append(r"\end{description}")
    lines.extend([r"\end{document}", ""])
    output.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build_markdown(metadata: dict[str, str], sections: list[Section], output: Path) -> None:
    lines = [
        f"# {metadata['title']}",
        "",
        f"*{metadata['subtitle']}*",
        "",
        "> **Planning boundary.** This document arranges verified claims and evidence. It is not article prose.",
        "",
        f"- **Target venue:** {metadata['target_venue']}",
        f"- **Target length:** {metadata['target_length']}",
        f"- **Verified source set:** {metadata['source_versions']}",
        "",
        "## Proposed order",
        "",
        "| ID | Section and purpose | Approximate length |",
        "|---|---|---|",
    ]
    for section in sections:
        lines.append(
            f"| {section.section_id} | {section.title}. {section.fields['Purpose']} | "
            f"{section.fields['Approximate length']} |"
        )
    lines.extend(["", "## Section-by-section map", ""])
    for section in sections:
        level = min(3 + section.depth, 6)
        lines.append(f"{'#' * level} [{section.section_id}] {section.title}")
        lines.append("")
        for field_name in REQUIRED_FIELDS:
            lines.append(f"**{field_name}:** {section.fields[field_name]}")
            lines.append("")
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8", newline="\n")


def _write_crosswalk(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CROSSWALK_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _validate_written_crosswalk(path: Path, sections: list[Section]) -> None:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CROSSWALK_COLUMNS:
            raise ValueError("written crosswalk has malformed columns")
        validate_crosswalk(list(reader), sections)


def _validate_output(path: Path, output_format: str, sections: list[Section]) -> None:
    if output_format == "docx":
        reopened = Document(path)
        headings = {
            paragraph.text.strip()
            for paragraph in reopened.paragraphs
            if paragraph.style is not None and paragraph.style.name.startswith("Heading")
        }
        missing = [
            section.section_id
            for section in sections
            if f"[{section.section_id}] {section.title}" not in headings
        ]
        if missing:
            raise ValueError("generated Word artifact is missing sections: " + ", ".join(missing))
        if not reopened.tables:
            raise ValueError("generated Word artifact is missing table geometry")
    else:
        text = path.read_text(encoding="utf-8")
        missing = [section.section_id for section in sections if section.section_id not in text]
        if missing:
            raise ValueError("generated artifact is missing sections: " + ", ".join(missing))
        if PLACEHOLDER_RE.search(text):
            raise ValueError("generated artifact contains an unresolved placeholder")


def build(
    source: Path,
    output: Path,
    crosswalk: Path,
    manifest: Path,
    project_root: Path,
) -> None:
    if source.suffix.lower() != ".md":
        raise ValueError("source must be a .md file")
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    for path in (output, crosswalk, manifest):
        if path.exists():
            raise ValueError(f"refusing to overwrite existing artifact: {path}")
    if crosswalk.suffix.lower() != ".csv":
        raise ValueError("crosswalk must be a .csv file")
    if manifest.suffix.lower() != ".json":
        raise ValueError("manifest must be a .json file")

    metadata, sections = parse_source(source.read_text(encoding="utf-8"))
    output_format = metadata["output_format"]
    if output.suffix.lower() != f".{output_format}":
        raise ValueError(
            f"output extension {output.suffix or '(none)'} does not match output_format {output_format}"
        )
    validate_artifact_references(metadata, sections, project_root)
    rows = make_crosswalk_rows(sections)

    for path in (output, crosswalk, manifest):
        path.parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    try:
        if output_format == "docx":
            build_docx(metadata, sections, output)
        elif output_format == "tex":
            build_tex(metadata, sections, output)
        else:
            build_markdown(metadata, sections, output)
        created.append(output)
        _validate_output(output, output_format, sections)

        _write_crosswalk(crosswalk, rows)
        created.append(crosswalk)
        _validate_written_crosswalk(crosswalk, sections)

        manifest_payload = {
            "schema_version": "1.0",
            "stage_id": "17-skeleton-draft",
            "source": {"path": source.as_posix(), "sha256": _sha256(source)},
            "output": {
                "path": output.as_posix(),
                "format": output_format,
                "sha256": _sha256(output),
            },
            "crosswalk": {
                "path": crosswalk.as_posix(),
                "sha256": _sha256(crosswalk),
                "rows": len(rows),
            },
            "sections": [section.section_id for section in sections],
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
    parser.add_argument("--crosswalk", type=Path, required=True, help="new crosswalk CSV")
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
            args.crosswalk.resolve(),
            args.manifest.resolve(),
            args.project_root.resolve(),
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Created {args.output}, {args.crosswalk}, and {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
