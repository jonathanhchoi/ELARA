from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_skeleton_draft import build, parse_displays, parse_source  # noqa: E402


def sample_figure_png(width: int = 640, height: int = 360) -> bytes:
    """Return a dependency-free PNG with axes, intervals, and point estimates."""

    pixels = bytearray()
    estimates = [(150, 120), (270, 185), (390, 240), (510, 155)]
    for y in range(height):
        pixels.append(0)
        for x in range(width):
            color = (255, 255, 255)
            if (70 <= x <= 570 and y == 300) or (x == 70 and 45 <= y <= 300):
                color = (74, 85, 104)
            for point_x, point_y in estimates:
                if abs(x - point_x) <= 45 and abs(y - point_y) <= 2:
                    color = (75, 117, 181)
                if (x - point_x) ** 2 + (y - point_y) ** 2 <= 36:
                    color = (31, 78, 121)
            pixels.extend(color)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(
        b"IDAT", zlib.compress(bytes(pixels), 9)
    ) + chunk(b"IEND", b"")


def sample_source(output_format: str = "docx") -> str:
    return f'''---
title: "Court access and claim outcomes"
subtitle: "Skeleton draft"
output_format: "{output_format}"
target_venue: "Journal of Law and Empirical Analysis"
target_length: "10,000 words"
source_versions: "project/artifacts/preemption_review_v001.md; project/artifacts/methods_plan_v001.md; project/artifacts/results_v001.csv; project/artifacts/results_figure_v001.png; project/artifacts/estimating_equation_v001.tex; project/artifacts/robustness_v001.csv; project/DEVIATIONS.md"
---

## Introduction
**Section role:** introduction
**Bare-bones content:** Author to write.
**Source support:** project/artifacts/preemption_review_v001.md#CONTRIBUTION-01
**Results presented:** none
**Displays:** none
**Author work:** State the research question, contribution, and thesis in the author's own prose.
**Open questions:** Whether to lead with court access or claim outcomes.
**Approximate length:** 900 words

## Background and contribution
**Section role:** background
**Bare-bones content:** Author to write.
**Source support:** project/artifacts/preemption_review_v001.md#LITERATURE-01
**Results presented:** none
**Displays:** none
**Author work:** Develop the literature position and legal context in the author's own prose.
**Open questions:** Whether the doctrinal discussion belongs here or after the results.
**Approximate length:** 1,200 words

## Data and methods
**Section role:** methods
**Bare-bones content:** The study estimates filing outcomes in the approved court sample using the preregistered specification in project/artifacts/methods_plan_v001.md#METHOD-01.
**Source support:** project/artifacts/methods_plan_v001.md#METHOD-01; project/artifacts/methods_plan_v001.md#ESTIMAND-01
**Results presented:** none
**Displays:** equation|project/artifacts/estimating_equation_v001.tex#EQ-01|Estimating equation with outcome, treatment, covariates, and court fixed effects defined in the text below
**Author work:** Explain the design choices and identifying assumptions in the author's own prose.
**Open questions:** Whether to move implementation details to an appendix.
**Approximate length:** 2,000 words

### Validation
**Section role:** methods
**Bare-bones content:** The held-out comparison met the approved validation threshold in project/artifacts/methods_plan_v001.md#VALIDATION-01.
**Source support:** project/artifacts/methods_plan_v001.md#VALIDATION-01
**Results presented:** project/artifacts/methods_plan_v001.md#VALIDATION-01
**Displays:** none
**Author work:** Explain the remaining measurement concern.
**Open questions:** Whether validation details belong in the main text.
**Approximate length:** 500 words

## Results
**Section role:** results
**Bare-bones content:** The primary estimate is positive, the secondary estimate is null, and uncertainty is reported in project/artifacts/results_v001.csv#RESULTS-ALL.
**Source support:** project/artifacts/results_v001.csv#RESULTS-ALL
**Results presented:** project/artifacts/results_v001.csv#R-H01; project/artifacts/results_v001.csv#R-H02; project/artifacts/results_v001.csv#R-SUBGROUP-01
**Displays:** table|project/artifacts/results_v001.csv#TABLE-PRIMARY|Complete estimates for the primary, secondary, and subgroup analyses with standard errors and sample sizes || figure|project/artifacts/results_figure_v001.png#FIGURE-PRIMARY|Point estimates and 95 percent confidence intervals for every preregistered analysis
**Author work:** Interpret the complete findings and connect them to the argument in the author's own prose.
**Open questions:** Which result should receive the most attention in the introduction.
**Approximate length:** 2,500 words

### Robustness and deviations
**Section role:** robustness
**Bare-bones content:** The complete specification checks and the fragile subgroup result appear in project/artifacts/robustness_v001.csv#ROBUSTNESS-ALL.
**Source support:** project/artifacts/robustness_v001.csv#ROBUSTNESS-ALL; project/DEVIATIONS.md#DEV-01
**Results presented:** project/artifacts/robustness_v001.csv#ROB-01; project/artifacts/robustness_v001.csv#ROB-02; project/artifacts/robustness_v001.csv#ROB-FRAGILE-01
**Displays:** table|project/artifacts/robustness_v001.csv#TABLE-ROBUSTNESS|All robustness specifications, including null and fragile findings, with standard errors and sample sizes
**Author work:** Explain how the checks and deviation affect the conclusions.
**Open questions:** Whether the full table belongs in the main text or appendix.
**Approximate length:** 900 words

## Limitations
**Section role:** limitations
**Bare-bones content:** Author to write.
**Source support:** project/DEVIATIONS.md#LIMITATION-01
**Results presented:** none
**Displays:** none
**Author work:** Develop the limits on inference and generalization in the author's own prose.
**Open questions:** How much space to give measurement and coverage limits.
**Approximate length:** 800 words

## Conclusion
**Section role:** conclusion
**Bare-bones content:** Author to write.
**Source support:** project/artifacts/preemption_review_v001.md#CONTRIBUTION-01
**Results presented:** none
**Displays:** none
**Author work:** State the implications and conclusion in the author's own prose.
**Open questions:** Which implication should close the article.
**Approximate length:** 500 words
'''


class SkeletonDraftBuilderTests(unittest.TestCase):
    def _project(self, root: Path) -> None:
        text_files = {
            "project/artifacts/preemption_review_v001.md": "verified contribution and literature\n",
            "project/artifacts/methods_plan_v001.md": "verified methods and validation\n",
            "project/artifacts/estimating_equation_v001.tex": r"Y_{ic} = \alpha + \beta T_{ic} + X_{ic}'\gamma + \delta_c + \varepsilon_{ic}",
            "project/DEVIATIONS.md": "verified deviations and limitations\n",
        }
        for relative, value in text_files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8")
        for relative, value in {
            "project/artifacts/results_v001.csv": "analysis,estimate,se,n\nprimary,0.12,0.03,400\nsecondary,0.01,0.04,400\nsubgroup,0.08,0.06,90\n",
            "project/artifacts/robustness_v001.csv": "specification,estimate,se,n\nbaseline,0.12,0.03,400\nalternate,0.11,0.04,400\nsubgroup,0.08,0.06,90\n",
        }.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8")
        figure = root / "project/artifacts/results_figure_v001.png"
        figure.parent.mkdir(parents=True, exist_ok=True)
        figure.write_bytes(sample_figure_png())

    def _build(self, root: Path, output_format: str) -> tuple[Path, Path, Path]:
        self._project(root)
        source = root / f"source_{output_format}.md"
        output = root / f"skeleton_draft_v001.{output_format}"
        manifest = root / f"manifest_{output_format}.json"
        source.write_text(sample_source(output_format), encoding="utf-8")
        build(source, output, manifest, root)
        return source, output, manifest

    def test_builds_all_supported_formats_with_complete_displays(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for output_format in ("docx", "tex", "md"):
                source, output, manifest = self._build(root / output_format, output_format)
                self.assertTrue(source.is_file())
                self.assertTrue(output.is_file())
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema_version"], "1.1")
                self.assertEqual(payload["output"]["format"], output_format)
                self.assertEqual(payload["sections"][0]["title"], "Introduction")
                self.assertEqual(payload["sections"][3]["level"], 3)
                self.assertEqual(len(payload["displays"]), 4)
                self.assertNotIn("crosswalk", payload)

    def test_word_uses_descriptive_headings_and_renders_all_display_types(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, output, _ = self._build(Path(directory), "docx")
            document = Document(output)
            headings = [
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.style and paragraph.style.name.startswith("Heading")
            ]
            self.assertIn("Introduction", headings)
            self.assertIn("Validation", headings)
            self.assertFalse(any("[S0" in heading for heading in headings))
            self.assertGreaterEqual(len(document.tables), 3)
            self.assertTrue(any("Y_{ic}" in paragraph.text for paragraph in document.paragraphs))
            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
                footer_xml = "".join(
                    archive.read(name).decode("utf-8")
                    for name in archive.namelist()
                    if name.startswith("word/footer") and name.endswith(".xml")
                )
                media = [name for name in archive.namelist() if name.startswith("word/media/")]
            self.assertIn('w:type="fixed"', document_xml)
            self.assertIn(" PAGE ", footer_xml)
            self.assertTrue(media)

    def test_latex_and_markdown_include_tables_figures_equations_and_captions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, tex_output, _ = self._build(root / "tex", "tex")
            tex = tex_output.read_text(encoding="utf-8")
            self.assertIn(r"\section*{Introduction}", tex)
            self.assertIn(r"\subsection*{Validation}", tex)
            self.assertIn(r"\includegraphics", tex)
            self.assertIn(r"Y_{ic}", tex)
            self.assertIn("Complete estimates for the primary", tex)
            _, md_output, _ = self._build(root / "md", "md")
            md = md_output.read_text(encoding="utf-8")
            self.assertIn("| analysis | estimate | se | n |", md)
            self.assertIn("![Point estimates", md)
            self.assertIn("$$", md)

    def test_rejects_unsupported_format_and_extension_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            source = root / "source.md"
            source.write_text(sample_source("pdf"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "output_format"):
                build(source, root / "out.pdf", root / "manifest.json", root)
            source.write_text(sample_source("tex"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                build(source, root / "out.md", root / "manifest.json", root)

    def test_rejects_missing_field_placeholder_and_heading_jump(self) -> None:
        missing = sample_source().replace("**Open questions:** Whether to lead with court access or claim outcomes.\n", "", 1)
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            parse_source(missing)
        with self.assertRaisesRegex(ValueError, "unresolved placeholder"):
            parse_source(sample_source().replace("Skeleton draft", "TODO-SKELETON", 1))
        with self.assertRaisesRegex(ValueError, "skips a Markdown heading level"):
            parse_source(sample_source().replace("### Validation", "#### Validation", 1))

    def test_requires_complete_structure_and_minimal_methods_and_results_prose(self) -> None:
        missing_conclusion = sample_source().split("\n## Conclusion\n", 1)[0] + "\n"
        with self.assertRaisesRegex(ValueError, "missing top-level roles: conclusion"):
            parse_source(missing_conclusion)
        no_results_content = sample_source().replace(
            "The primary estimate is positive, the secondary estimate is null, and uncertainty is reported in project/artifacts/results_v001.csv#RESULTS-ALL.",
            "Author to write.",
        )
        with self.assertRaisesRegex(ValueError, "bare-bones results content"):
            parse_source(no_results_content)
        excess = sample_source().replace(
            "**Bare-bones content:** Author to write.",
            "**Bare-bones content:** " + " ".join(["word"] * 36) + ".",
            1,
        )
        with self.assertRaisesRegex(ValueError, "too much non-empirical prose"):
            parse_source(excess)

    def test_requires_traced_results_and_displayed_result_sections(self) -> None:
        untraced = sample_source().replace(
            "**Results presented:** project/artifacts/results_v001.csv#R-H01; project/artifacts/results_v001.csv#R-H02; project/artifacts/results_v001.csv#R-SUBGROUP-01",
            "**Results presented:** primary, secondary, and subgroup results",
        )
        with self.assertRaisesRegex(ValueError, "must be 'none' or cite"):
            parse_source(untraced)
        no_display = sample_source().replace(
            "**Displays:** table|project/artifacts/results_v001.csv#TABLE-PRIMARY|Complete estimates for the primary, secondary, and subgroup analyses with standard errors and sample sizes || figure|project/artifacts/results_figure_v001.png#FIGURE-PRIMARY|Point estimates and 95 percent confidence intervals for every preregistered analysis",
            "**Displays:** none",
        )
        with self.assertRaisesRegex(ValueError, "at least one table, figure, or equation"):
            parse_source(no_display)
        partly_bare = sample_source().replace(
            "**Source support:** project/artifacts/results_v001.csv#RESULTS-ALL",
            "**Source support:** project/artifacts/results_v001.csv#RESULTS-ALL; project/DEVIATIONS.md",
        )
        with self.assertRaisesRegex(ValueError, "artifact references require #ID"):
            parse_source(partly_bare)

    def test_rejects_bad_display_specs_and_missing_artifacts(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported display kind"):
            parse_displays("chart|project/artifacts/results_v001.csv#T-1|Caption")
        with self.assertRaisesRegex(ValueError, "unsupported file extension"):
            parse_displays("figure|project/artifacts/results_v001.csv#F-1|Caption")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.md"
            source.write_text(sample_source(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "do not exist"):
                build(source, root / "out.docx", root / "manifest.json", root)

    def test_rejects_artifact_paths_that_escape_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            outside = root / "outside.csv"
            outside.write_text("analysis,estimate\nprimary,0.12\n", encoding="utf-8")
            source = root / "source.md"
            source.write_text(
                sample_source("md").replace(
                    "project/artifacts/results_v001.csv#TABLE-PRIMARY",
                    "project/artifacts/../../outside.csv#TABLE-PRIMARY",
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "escapes project"):
                build(
                    source,
                    root / "skeleton_draft_v001.md",
                    root / "manifest.json",
                    root,
                )

    def test_refuses_to_overwrite_any_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, manifest = self._build(root, "md")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                build(source, output, manifest, root)

    def test_rejects_unsafe_equation_and_malformed_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            equation = root / "project/artifacts/estimating_equation_v001.tex"
            equation.write_text(r"\input{secret.tex}", encoding="utf-8")
            source = root / "source.md"
            source.write_text(sample_source(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsafe LaTeX command"):
                build(source, root / "out.docx", root / "manifest.json", root)
            equation.write_text(r"Y = X\beta", encoding="utf-8")
            table = root / "project/artifacts/results_v001.csv"
            table.write_text("a,b\n1\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inconsistent row widths"):
                build(source, root / "out.docx", root / "manifest.json", root)


if __name__ == "__main__":
    unittest.main()
