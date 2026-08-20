from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_skeleton_draft import (  # noqa: E402
    CROSSWALK_COLUMNS,
    build,
    make_crosswalk_rows,
    parse_source,
    validate_crosswalk,
)


def sample_source(output_format: str = "docx") -> str:
    return f'''---
title: "Court access and claim outcomes"
subtitle: "Article skeleton"
output_format: "{output_format}"
target_venue: "Journal of Law and Empirical Analysis"
target_length: "10,000 words"
source_versions: "project/artifacts/preemption_review_v001.docx; project/artifacts/analysis_report_v001.md; project/artifacts/analysis_results_v001/results.csv; project/artifacts/robustness_report_v001.md; project/DEVIATIONS.md"
---

## [S01] Introduction
**Purpose:** Define the problem and state the verified contribution.
**Claims:** Corrected filing rate is 12% in the study population, project/artifacts/analysis_results_v001/results.csv#R-H01.
**Evidence:** project/artifacts/preemption_review_v001.docx#CE-01
**Results:** project/artifacts/analysis_results_v001/results.csv#R-H01
**Tables and figures:** project/artifacts/analysis_results_v001/results.csv#F-01
**Counterarguments:** Selection into observed dockets may narrow external validity.
**Limitations:** Scope is limited to the sampled courts and years.
**Open questions:** citation-needed:AUTH-01 for the doctrinal framing.
**Approximate length:** 900 words

### [S01.01] Contribution and literature position
**Purpose:** Distinguish the study from the closest empirical work.
**Claims:** Contribution language approved in the preemption review, project/artifacts/preemption_review_v001.docx#CONTRIBUTION-01.
**Evidence:** project/artifacts/preemption_review_v001.docx#CE-02
**Results:** none
**Tables and figures:** none
**Counterarguments:** The closest work may cover a related procedural setting.
**Limitations:** The source map may require a later literature recheck.
**Open questions:** Whether to move the full lineage discussion to a later section.
**Approximate length:** 500 words

## [S02] Design and validation
**Purpose:** Explain identification, measurement, and validation before presenting findings.
**Claims:** Validation supports the primary measure within the prespecified threshold, project/artifacts/analysis_report_v001.md#VAL-01.
**Evidence:** project/artifacts/analysis_report_v001.md#VAL-01
**Results:** project/artifacts/analysis_report_v001.md#VAL-01
**Tables and figures:** project/artifacts/analysis_results_v001/results.csv#T-01
**Counterarguments:** Validation error may differ outside the held-out sample.
**Limitations:** Sparse subgroups produce imprecise class-specific estimates.
**Open questions:** Whether the validation table belongs here or in an appendix.
**Approximate length:** 2,500 words

## [S03] Findings and robustness
**Purpose:** Present primary, null, and fragile findings with the robustness boundary.
**Claims:** The primary estimate is stable, while the secondary estimate is null and one subgroup result is fragile, project/artifacts/robustness_report_v001.md#ROB-01.
**Evidence:** project/artifacts/robustness_report_v001.md#ROB-01
**Results:** project/artifacts/analysis_results_v001/results.csv#R-H01; project/artifacts/analysis_results_v001/results.csv#R-H02; project/artifacts/robustness_report_v001.md#ROB-FRAGILE-01
**Tables and figures:** project/artifacts/analysis_results_v001/results.csv#T-02; project/artifacts/analysis_results_v001/results.csv#F-02
**Counterarguments:** Model choice may explain the fragile subgroup comparison.
**Limitations:** The null estimate remains compatible with effects inside its interval.
**Open questions:** Whether to emphasize the null finding in the introduction.
**Approximate length:** 3,000 words

## [S04] Limitations and implications
**Purpose:** Collect design limits, deviations, and bounded implications.
**Claims:** None beyond the claims already mapped above.
**Evidence:** project/DEVIATIONS.md#DEV-01
**Results:** project/artifacts/analysis_results_v001/results.csv#R-H02; omit:R-H02
**Tables and figures:** none
**Counterarguments:** A broader sample could change the practical implications.
**Limitations:** Coverage, measurement, and model sensitivity remain explicit.
**Open questions:** The researcher must approve whether R-H02 is omitted from the main text.
**Approximate length:** 1,300 words
'''


class SkeletonDraftBuilderTests(unittest.TestCase):
    def _project(self, root: Path) -> None:
        files = (
            "project/artifacts/preemption_review_v001.docx",
            "project/artifacts/analysis_report_v001.md",
            "project/artifacts/analysis_results_v001/results.csv",
            "project/artifacts/robustness_report_v001.md",
            "project/DEVIATIONS.md",
        )
        for relative in files:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("verified\n", encoding="utf-8")

    def _build(self, root: Path, output_format: str) -> tuple[Path, Path, Path, Path]:
        self._project(root)
        source = root / f"source_{output_format}.md"
        output = root / f"skeleton_draft_v001.{output_format}"
        crosswalk = root / f"crosswalk_{output_format}.csv"
        manifest = root / f"manifest_{output_format}.json"
        source.write_text(sample_source(output_format), encoding="utf-8")
        build(source, output, crosswalk, manifest, root)
        return source, output, crosswalk, manifest

    def test_builds_all_supported_formats_from_same_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for output_format in ("docx", "tex", "md"):
                source, output, crosswalk, manifest = self._build(root / output_format, output_format)
                self.assertTrue(source.is_file())
                self.assertTrue(output.is_file())
                self.assertTrue(crosswalk.is_file())
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertEqual(payload["output"]["format"], output_format)
                self.assertEqual(payload["sections"], ["S01", "S01.01", "S02", "S03", "S04"])
                with crosswalk.open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertTrue(any(row["artifact_id"] == "R-H02" for row in rows))
                self.assertTrue(
                    any(
                        row["artifact_id"] == "R-H02" and row["disposition"] == "omitted"
                        for row in rows
                    )
                )

    def test_word_uses_headings_lists_fixed_table_and_page_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, output, _, _ = self._build(Path(directory), "docx")
            document = Document(output)
            headings = [
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.style and paragraph.style.name.startswith("Heading")
            ]
            self.assertIn("[S01] Introduction", headings)
            self.assertIn("[S01.01] Contribution and literature position", headings)
            self.assertGreaterEqual(len(document.tables), 2)
            self.assertTrue(any(p.style and p.style.name == "List Bullet" for p in document.paragraphs))
            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
                footer_xml = "".join(
                    archive.read(name).decode("utf-8")
                    for name in archive.namelist()
                    if name.startswith("word/footer") and name.endswith(".xml")
                )
            self.assertIn('w:type="fixed"', document_xml)
            self.assertIn(" PAGE ", footer_xml)

    def test_latex_escapes_project_paths_and_contains_nested_sections(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, output, _, _ = self._build(Path(directory), "tex")
            text = output.read_text(encoding="utf-8")
            self.assertIn(r"\section*{[S01] Introduction}", text)
            self.assertIn(r"\subsection*{[S01.01] Contribution and literature position}", text)
            self.assertIn(r"\path{project/artifacts/analysis_results_v001", text)

    def test_rejects_unsupported_format_and_extension_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._project(root)
            source = root / "source.md"
            source.write_text(sample_source("pdf"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "output_format"):
                build(source, root / "out.pdf", root / "crosswalk.csv", root / "manifest.json", root)
            source.write_text(sample_source("tex"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match"):
                build(source, root / "out.md", root / "crosswalk.csv", root / "manifest.json", root)

    def test_rejects_missing_field_placeholder_and_bad_hierarchy(self) -> None:
        missing = sample_source().replace("**Open questions:** citation-needed:AUTH-01 for the doctrinal framing.\n", "", 1)
        with self.assertRaisesRegex(ValueError, "missing required fields"):
            parse_source(missing)
        with self.assertRaisesRegex(ValueError, "unresolved placeholder"):
            parse_source(sample_source().replace("Article skeleton", "TODO-SKELETON", 1))
        bad_hierarchy = sample_source().replace("### [S01.01]", "### [S01.02]", 1)
        with self.assertRaisesRegex(ValueError, "not sequential"):
            parse_source(bad_hierarchy)

    def test_rejects_untraced_results_and_missing_artifacts(self) -> None:
        untraced = sample_source().replace(
            "**Results:** project/artifacts/analysis_results_v001/results.csv#R-H01",
            "**Results:** corrected estimate 12%",
            1,
        )
        with self.assertRaisesRegex(ValueError, "must be 'none' or cite"):
            parse_source(untraced)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.md"
            source.write_text(sample_source(), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "do not exist"):
                build(source, root / "out.docx", root / "crosswalk.csv", root / "manifest.json", root)

    def test_refuses_to_overwrite_any_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output, crosswalk, manifest = self._build(root, "md")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                build(source, output, crosswalk, manifest, root)

    def test_rejects_malformed_crosswalk(self) -> None:
        _metadata, sections = parse_source(sample_source())
        rows = make_crosswalk_rows(sections)
        malformed = [dict(rows[0])]
        malformed[0].pop("artifact_id")
        with self.assertRaisesRegex(ValueError, "malformed columns"):
            validate_crosswalk(malformed, sections)
        self.assertEqual(tuple(rows[0]), CROSSWALK_COLUMNS)


if __name__ == "__main__":
    unittest.main()
