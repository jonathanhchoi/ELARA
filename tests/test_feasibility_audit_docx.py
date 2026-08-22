from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from docx import Document

from kit_context import resolve_test_root


ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from build_feasibility_audit import (  # noqa: E402
    GATES,
    LEGACY_HEADINGS,
    build,
    parse_blocks,
    parse_source,
    validate_sections,
)
from workflow_lib import load_stages  # noqa: E402


def _gate_section(index: int, question: str) -> str:
    extra = ""
    if index == 6:
        extra = (
            "\n**Sub-agent timing:** Low, central, and high scenarios are 18, 24, and "
            "36 hours based on 2,400 assignments, bounded concurrency, observed "
            "duration, retries, serial validation, and aggregation.\n\n"
            "**API-price comparison:** The optional API route is estimated at $48 to "
            "$92 from current prices, projected tokens, retries, model tiers, and "
            "available batch discounts.\n\n"
            "**Human and other resources:** Validation requires 80 research-assistant "
            "hours. No fixed charge is known.\n"
        )
    if index == 8:
        extra = (
            "\n**Researcher decision needed:** Approve the proposed $75 maximum API "
            "probe only if the default sub-agent route cannot complete the pilot.\n"
        )
    return (
        f"\n## {question}\n\n"
        "**Decision:** Pass with conditions.\n\n"
        f"**Evidence:** Probe P-{index:02d} and model row M-{index:02d}.\n"
        f"{extra}\n"
        "**What this means:** The project can proceed if the stated condition is met.\n\n"
        "**Conditions or next step:** Preserve the cited evidence and obtain any "
        "required approval.\n"
    )


SAMPLE_SOURCE = (
    "---\n"
    'title: "Feasibility Audit: Judicial Treatment of Synthetic Evidence"\n'
    'subtitle: "Can federal opinions support a reliable post-2024 comparison?"\n'
    'recommendation: "go with modifications"\n'
    'audit_date: "2026-08-21"\n'
    'report_version: "v001"\n'
    "---\n\n"
    "## Decision summary\n\n"
    "> **Bottom line:** The project is feasible if the corpus and validation plan "
    "are narrowed as specified below.\n"
    + "".join(
        _gate_section(index, gate.question) for index, gate in enumerate(GATES, start=1)
    )
    + "\n## Controlling limitation\n\n"
    "The controlling limitation is the number of readable opinions in the central estimate after screening.\n\n"
    "## Recommendation and what would change it\n\n"
    "Proceed with modifications. A failed corpus probe or an infeasible minimum "
    "detectable effect would change the recommendation.\n\n"
    "## Evidence gaps and limitations\n\n"
    "The authorization lead time remains unverified and is disclosed as a limitation.\n"
)


class FeasibilityAuditBuilderTests(unittest.TestCase):
    def test_builds_question_led_latex_report_without_tables(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "feasibility_audit_source.md"
            output = root / "feasibility_audit_v001.tex"
            source.write_text(SAMPLE_SOURCE, encoding="utf-8")

            build(source, output)

            self.assertTrue(output.is_file())
            latex = output.read_text(encoding="utf-8")
            self.assertTrue(latex.startswith(r"\documentclass"))
            self.assertIn(r"\end{document}", latex)
            self.assertNotIn(r"\begin{tabular", latex)
            for gate in GATES:
                self.assertIn(gate.question, latex)
                self.assertNotIn(gate.internal_id, latex)

            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                build(source, output)

    def test_word_remains_an_explicit_optional_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "feasibility_audit_source.md"
            output = root / "feasibility_audit_v001.docx"
            source.write_text(SAMPLE_SOURCE, encoding="utf-8")
            build(source, output)
            document = Document(output)
            self.assertEqual(document.tables, [])
            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertNotIn("<w:tbl>", document_xml)

    def test_rejects_tables_legacy_headings_and_incomplete_gates(self) -> None:
        metadata, body = parse_source(SAMPLE_SOURCE)
        self.assertEqual(metadata["recommendation"], "go with modifications")
        validate_sections(parse_blocks(body))

        table_source = SAMPLE_SOURCE.replace(
            "The controlling limitation is",
            "| Item | Finding |\n| --- | --- |\n| Constraint | Readable opinions |\n\n"
            "The controlling limitation is",
            1,
        )
        _metadata, table_body = parse_source(table_source)
        with self.assertRaisesRegex(ValueError, "not a table"):
            validate_sections(parse_blocks(table_body))

        for legacy_heading in LEGACY_HEADINGS:
            with self.subTest(legacy_heading=legacy_heading):
                legacy_source = SAMPLE_SOURCE.replace(GATES[0].question, legacy_heading, 1)
                _metadata, legacy_body = parse_source(legacy_source)
                with self.assertRaisesRegex(
                    ValueError, "invalid feasibility-report section headings"
                ):
                    validate_sections(parse_blocks(legacy_body))

        incomplete = SAMPLE_SOURCE.replace("**Evidence:** Probe P-02", "Probe P-02", 1)
        _metadata, incomplete_body = parse_source(incomplete)
        with self.assertRaisesRegex(ValueError, "missing labeled content: Evidence"):
            validate_sections(parse_blocks(incomplete_body))

    def test_template_is_unresolved_and_contains_exact_question_sections(self) -> None:
        template = (ROOT / "workflow" / "templates" / "feasibility_audit_template.md").read_text(
            encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "unresolved placeholder"):
            parse_source(template)
        for gate in GATES:
            self.assertEqual(template.count("## " + gate.question), 1)
        self.assertNotIn("| Gate |", template)


class FeasibilityAuditStageContractTests(unittest.TestCase):
    def test_pdf_report_and_question_labels_are_stage_03_contract(self) -> None:
        stages = {meta["stage_id"]: (meta, body) for _, meta, body in load_stages(ROOT)}
        stage_three, body = stages["03-feasibility-audit"]
        self.assertIn(
            "project/artifacts/feasibility_audit_vNNN.pdf",
            stage_three["declared_outputs"],
        )
        self.assertIn(
            "project/artifacts/feasibility_audit_vNNN.tex",
            stage_three["declared_outputs"],
        )
        self.assertTrue(
            any("feasibility_audit_vNNN.docx" in item for item in stage_three["declared_outputs"])
        )
        self.assertIn(
            "project/runs/<run_id>/feasibility_audit_source.md",
            stage_three["declared_outputs"],
        )
        self.assertIn(
            "project/runs/<run_id>/rendered_feasibility_audit/",
            stage_three["declared_outputs"],
        )
        self.assertIn("scripts/build_feasibility_audit.py", body)
        self.assertIn("workflow/templates/feasibility_audit_template.md", body)
        self.assertIn("Do not use a gate table", body)
        self.assertIn("one prose section for each gate", body)
        self.assertIn("contains no tables", body)
        for number, gate in enumerate(GATES, start=1):
            self.assertIn(f"**Gate {number}: {gate.question}**", body)
            self.assertIn(f"stable internal ID is `{gate.internal_id}`", body)

        stage_four, _stage_four_body = stages["04-methods-design"]
        self.assertIn(
            "project/artifacts/feasibility_audit_vNNN.pdf (or the explicit researcher-selected alternative)",
            stage_four["required_inputs"],
        )
        self.assertNotIn(
            "project/artifacts/feasibility_audit_vNNN.md",
            stage_four["required_inputs"],
        )

        doctor = (ROOT / "scripts" / "doctor.py").read_text(encoding="utf-8")
        self.assertIn("workflow/templates/feasibility_audit_template.md", doctor)
        self.assertIn("scripts/build_feasibility_audit.py", doctor)
        self.assertIn("scripts/latex_report.py", doctor)


if __name__ == "__main__":
    unittest.main()
