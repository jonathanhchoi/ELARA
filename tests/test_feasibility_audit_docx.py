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
    CONSULTATION,
    GATES,
    LEGACY_HEADINGS,
    build,
    parse_blocks,
    parse_source,
    validate_sections,
)
from workflow_lib import load_stages  # noqa: E402


RUN_ID = "20260821T120000Z_03-feasibility-audit_r001"


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
        "**Analysis:** The probe, alternatives, assumptions, and tradeoffs support "
        "the conditional disposition and are stated in full.\n\n"
        "**What this means:** The project can proceed if the stated condition is met.\n\n"
        f"**Researcher input:** Decision D-{index:02d} accepted the displayed "
        "recommendation after reviewing the alternatives.\n\n"
        "**Conditions or next step:** Preserve the cited evidence and obtain any "
        "required approval.\n"
    )


SAMPLE_SOURCE = (
    "---\n"
    'title: "Feasibility Audit: Judicial Treatment of Synthetic Evidence"\n'
    'subtitle: "Can federal opinions support a reliable post-2024 comparison?"\n'
    'recommendation: "go with modifications"\n'
    'audit_date: "2026-08-21"\n'
    'consultation_date: "2026-08-22"\n'
    f'consultation_record: "project/runs/{RUN_ID}/feasibility_consultation.md"\n'
    'report_version: "v001"\n'
    "---\n\n"
    "## Decision summary\n\n"
    "> **Bottom line:** The project is feasible if the corpus and validation plan "
    "are narrowed as specified below.\n"
    + "".join(
        _gate_section(index, gate.question) for index, gate in enumerate(GATES, start=1)
    )
    + "\n## Researcher consultation and decisions\n\n"
    "**Consultation status:** Complete.\n\n"
    "**Decisions incorporated:** Decisions D-01 through D-08 record the questions "
    "presented in chat, the recommendations and alternatives, the researcher's "
    "answers, and their effects on the analysis.\n\n"
    "No material researcher-owned choice remains unresolved.\n\n"
    + "\n## Controlling limitation\n\n"
    "The controlling limitation is the number of readable opinions in the central estimate after screening.\n\n"
    "## Recommendation and what would change it\n\n"
    "Proceed with modifications. A failed corpus probe or an infeasible minimum "
    "detectable effect would change the recommendation.\n\n"
    "## Evidence gaps and limitations\n\n"
    "The authorization lead time remains unverified and is disclosed as a limitation.\n"
)


CONSULTATION_RECORD = (
    "# Feasibility-report consultation\n\n"
    "**Consultation status:** Complete.\n\n"
    + "".join(
        f"## D-{index:02d}\n\n"
        f"**Question:** Decide material feasibility choice {index}.\n\n"
        f"**Evidence:** Probe P-{index:02d}.\n\n"
        "**Recommendation:** Accept the displayed conditional design.\n\n"
        "**Alternatives and consequences:** Narrow the design or stop the project.\n\n"
        "**Researcher response:** Accept the recommendation.\n\n"
        "**Effect on analysis:** Carry the accepted condition into the report.\n\n"
        for index in range(1, 9)
    )
)


def _write_run_source(root: Path, *, include_consultation: bool = True) -> Path:
    run_dir = root / "project" / "runs" / RUN_ID
    run_dir.mkdir(parents=True)
    source = run_dir / "feasibility_audit_source.md"
    source.write_text(SAMPLE_SOURCE, encoding="utf-8")
    if include_consultation:
        (run_dir / "feasibility_consultation.md").write_text(
            CONSULTATION_RECORD,
            encoding="utf-8",
        )
    return source


class FeasibilityAuditBuilderTests(unittest.TestCase):
    def test_builds_question_led_latex_report_without_tables(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _write_run_source(root)
            output = root / "feasibility_audit_v001.tex"

            build(source, output)

            self.assertTrue(output.is_file())
            latex = output.read_text(encoding="utf-8")
            self.assertTrue(latex.startswith(r"\documentclass"))
            self.assertIn(r"\end{document}", latex)
            self.assertNotIn(r"\begin{tabular", latex)
            self.assertIn("Researcher consultation", latex)
            self.assertIn(r"feasibility\_consultation.md", latex)
            for gate in GATES:
                self.assertIn(gate.question, latex)
                self.assertNotIn(gate.internal_id, latex)

            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                build(source, output)

    def test_word_remains_an_explicit_optional_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _write_run_source(root)
            output = root / "feasibility_audit_v001.docx"
            build(source, output)
            document = Document(output)
            self.assertEqual(document.tables, [])
            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
            self.assertNotIn("<w:tbl>", document_xml)

    def test_refuses_to_build_before_the_consultation_record_exists(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = _write_run_source(root, include_consultation=False)
            output = root / "feasibility_audit_v001.tex"
            with self.assertRaisesRegex(ValueError, "consultation record does not exist"):
                build(source, output)
            self.assertFalse(output.exists())

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

        incomplete_analysis = SAMPLE_SOURCE.replace("**Analysis:** The probe", "The probe", 1)
        _metadata, incomplete_analysis_body = parse_source(incomplete_analysis)
        with self.assertRaisesRegex(ValueError, "missing labeled content: Analysis"):
            validate_sections(parse_blocks(incomplete_analysis_body))

        incomplete_consultation = SAMPLE_SOURCE.replace(
            "**Consultation status:** Complete.",
            "**Consultation status:** Pending.",
            1,
        )
        _metadata, incomplete_consultation_body = parse_source(incomplete_consultation)
        with self.assertRaisesRegex(ValueError, "consultation status must be complete"):
            validate_sections(parse_blocks(incomplete_consultation_body))

    def test_template_is_unresolved_and_contains_exact_question_sections(self) -> None:
        template = (ROOT / "workflow" / "templates" / "feasibility_audit_template.md").read_text(
            encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "unresolved placeholder"):
            parse_source(template)
        for gate in GATES:
            self.assertEqual(template.count("## " + gate.question), 1)
        self.assertEqual(template.count("## " + CONSULTATION), 1)
        self.assertNotIn("| Gate |", template)
        consultation_template = (
            ROOT / "workflow" / "templates" / "feasibility_consultation_template.md"
        ).read_text(encoding="utf-8")
        self.assertIn("TODO-CONSULTATION", consultation_template)
        for label in (
            "Question",
            "Evidence",
            "Recommendation",
            "Alternatives and consequences",
            "Researcher response",
            "Effect on analysis",
        ):
            self.assertIn(f"**{label}:**", consultation_template)


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
            "project/runs/<run_id>/feasibility_consultation.md",
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
        self.assertIn("ask all still-needed questions in one chat message", body)
        self.assertIn("Do not draft or build the final report yet", body)
        self.assertIn("This is the full feasibility analysis", body)
        self.assertIn("Researcher consultation and decisions", body)
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
        self.assertIn("workflow/templates/feasibility_consultation_template.md", doctor)
        self.assertIn("scripts/build_feasibility_audit.py", doctor)
        self.assertIn("scripts/latex_report.py", doctor)


if __name__ == "__main__":
    unittest.main()
