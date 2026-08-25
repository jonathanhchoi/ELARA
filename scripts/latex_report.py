"""Shared LaTeX renderer for ELARA's formatted researcher-facing reports."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import Path


INLINE_RE = re.compile(
    r"(\[[^\]]+\]\(https?://[^)]+\)|\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)"
)
LATEX_ESCAPES = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "%": r"\%",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    return "".join(LATEX_ESCAPES.get(char, char) for char in text)


def inline_code_latex(text: str) -> str:
    """Render escaped inline code with break opportunities at common separators."""
    escaped = escape_latex(text)
    for separator in ("/", r"\_", "-", "."):
        escaped = escaped.replace(separator, separator + r"\allowbreak{}")
    return r"\texttt{" + escaped + "}"


def inline_latex(text: str) -> str:
    parts: list[str] = []
    cursor = 0
    for match in INLINE_RE.finditer(text):
        parts.append(escape_latex(text[cursor : match.start()]))
        token = match.group(0)
        link = re.fullmatch(r"\[([^\]]+)\]\((https?://[^)]+)\)", token)
        if link:
            label, url = link.groups()
            parts.append(r"\href{" + escape_latex(url) + "}{" + escape_latex(label) + "}")
        elif token.startswith("**"):
            parts.append(r"\textbf{" + inline_latex(token[2:-2]) + "}")
        elif token.startswith("`"):
            parts.append(inline_code_latex(token[1:-1]))
        elif token.startswith("*"):
            parts.append(r"\emph{" + inline_latex(token[1:-1]) + "}")
        cursor = match.end()
    parts.append(escape_latex(text[cursor:]))
    return "".join(parts)


def _table_columns(column_count: int) -> str:
    if column_count < 1:
        raise ValueError("LaTeX table must have at least one column")
    return " ".join([r">{\raggedright\arraybackslash}X"] * column_count)


def _render_table(rows: Sequence[Sequence[str]]) -> list[str]:
    if not rows or not rows[0]:
        raise ValueError("LaTeX table cannot be empty")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("LaTeX table rows must have the same column count")
    lines = [
        r"\begin{center}",
        r"\small",
        r"\begin{tabularx}{\textwidth}{" + _table_columns(width) + "}",
        r"\toprule",
        " & ".join(r"\textbf{" + inline_latex(cell) + "}" for cell in rows[0]) + r" \\",
        r"\midrule",
    ]
    for row in rows[1:]:
        lines.append(" & ".join(inline_latex(cell) for cell in row) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{center}"])
    return lines


def _render_blocks(blocks, page_break_before: set[str]) -> list[str]:
    lines: list[str] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        if block.kind == "heading":
            if block.text in page_break_before:
                lines.append(r"\clearpage")
            command = {1: "section", 2: "section", 3: "subsection", 4: "subsubsection"}.get(
                block.level, "paragraph"
            )
            lines.append(f"\\{command}{{{inline_latex(block.text)}}}")
        elif block.kind == "paragraph":
            lines.extend([inline_latex(block.text), ""])
        elif block.kind == "callout":
            lines.extend(
                [
                    r"\begin{quote}",
                    inline_latex(block.text),
                    r"\end{quote}",
                ]
            )
        elif block.kind == "code":
            lines.extend([r"\begin{verbatim}", block.text, r"\end{verbatim}"])
        elif block.kind in {"ordered", "bullet"}:
            kind = block.kind
            environment = "enumerate" if kind == "ordered" else "itemize"
            lines.append(f"\\begin{{{environment}}}")
            while index < len(blocks) and blocks[index].kind == kind:
                lines.append(r"\item " + inline_latex(blocks[index].text))
                index += 1
            lines.append(f"\\end{{{environment}}}")
            index -= 1
        elif block.kind == "table":
            lines.extend(_render_table(block.rows))
        elif block.kind == "rule":
            lines.append(r"\medskip\hrule\medskip")
        index += 1
    return lines


def render_latex_report(
    *,
    title: str,
    subtitle: str,
    kicker: str,
    metadata_rows: Iterable[tuple[str, str]],
    blocks,
    page_break_before: Iterable[str] = (),
) -> str:
    metadata = []
    for label, value in metadata_rows:
        metadata.append(
            r"\noindent\textcolor{ELARAMuted}{\textbf{" + escape_latex(label) + r":}} "
            + inline_latex(value)
            + r"\\"
        )
    body = _render_blocks(blocks, set(page_break_before))
    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage[letterpaper,margin=1in]{geometry}",
        r"\usepackage{iftex}",
        r"\ifPDFTeX",
        r"  \usepackage[T1]{fontenc}",
        r"  \usepackage[utf8]{inputenc}",
        r"  \usepackage{lmodern}",
        r"\else",
        r"  \usepackage{fontspec}",
        r"  \setmainfont{Latin Modern Roman}",
        r"  \setsansfont{Latin Modern Sans}",
        r"  \setmonofont{Latin Modern Mono}",
        r"\fi",
        r"\usepackage{microtype}",
        r"\usepackage{xcolor}",
        r"\usepackage{hyperref}",
        r"\usepackage{xurl}",
        r"\usepackage{enumitem}",
        r"\usepackage{booktabs}",
        r"\usepackage{tabularx}",
        r"\usepackage{array}",
        r"\usepackage{fancyhdr}",
        r"\usepackage{titlesec}",
        r"\usepackage{parskip}",
        r"\definecolor{ELARANavy}{HTML}{17365D}",
        r"\definecolor{ELARABlue}{HTML}{2E74B5}",
        r"\definecolor{ELARAMuted}{HTML}{667085}",
        r"\hypersetup{colorlinks=true,linkcolor=ELARANavy,urlcolor=ELARABlue}",
        r"\setlist{leftmargin=1.6em,itemsep=0.25em,topsep=0.4em}",
        r"\titleformat{\section}[block]{\Large\bfseries\color{ELARABlue}}{}{0pt}{}",
        r"\titleformat{\subsection}[block]{\large\bfseries\color{ELARANavy}}{}{0pt}{}",
        r"\titleformat{\subsubsection}[block]{\normalsize\bfseries\color{ELARANavy}}{}{0pt}{}",
        r"\titlespacing*{\section}{0pt}{1.05em}{0.5em}",
        r"\titlespacing*{\subsection}{0pt}{0.95em}{0.35em}",
        r"\pagestyle{fancy}",
        r"\fancyhf{}",
        r"\renewcommand{\headrulewidth}{0pt}",
        r"\fancyfoot[C]{\textcolor{ELARAMuted}{\thepage}}",
        r"\setlength{\emergencystretch}{2em}",
        r"\begin{document}",
        r"\thispagestyle{fancy}",
        r"{\small\bfseries\color{ELARABlue} " + escape_latex(kicker.upper()) + r"}\par",
        r"\vspace{0.45em}",
        r"{\LARGE\bfseries\color{ELARANavy} " + inline_latex(title) + r"}\par",
        r"\vspace{0.45em}",
        r"{\large\itshape\color{ELARAMuted} " + inline_latex(subtitle) + r"}\par",
        r"\vspace{1em}",
        *metadata,
        r"\vspace{0.45em}\hrule\vspace{0.7em}",
        *body,
        r"\end{document}",
        "",
    ]
    return "\n".join(lines)


def validate_latex_output(path: Path, required_headings: Sequence[str], placeholder_re) -> None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith(r"\documentclass") or not text.rstrip().endswith(r"\end{document}"):
        raise ValueError("generated LaTeX report is incomplete")
    cursor = 0
    for heading in required_headings:
        rendered = r"\section{" + inline_latex(heading) + "}"
        position = text.find(rendered, cursor)
        if position < 0:
            raise ValueError(f"generated LaTeX report is missing section: {heading}")
        cursor = position + len(rendered)
    if placeholder_re.search(text):
        raise ValueError("generated LaTeX report contains an unresolved placeholder")
