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

from build_preemption_review import (  # noqa: E402
    REQUIRED_SECTIONS,
    build,
    parse_blocks,
    parse_source,
)
from workflow_lib import load_stages  # noqa: E402


SAMPLE_SOURCE = """---
title: "Preemption Review: Judicial Treatment of Synthetic Evidence"
subtitle: "How do federal courts evaluate authentication objections to synthetic evidence?"
verdict: "partially preempted"
recommended_disposition: "Reposition around authentication reasoning and the post-2024 period"
scoop_risk: "moderate"
review_date: "2026-08-19"
recheck_date: "2026-11-19"
---

## Annotated map of closest work

### Rivera, *Authenticating Synthetic Media* (2025)

**Publication status and venue:** Published law-review article.

**Question and thesis:** The article asks how existing authentication doctrine
applies to synthetic media and argues for a reliability-focused approach.

**Data and method:** Doctrinal analysis of reported cases.

**Relationship to this project:** It overlaps with the doctrinal question but
does not estimate court-level treatment using the proposed opinion corpus. See
[archived source](https://example.org/rivera).

## Verdict and flip conditions

> **Verdict:** Partially preempted. The doctrinal thesis is occupied, but the
proposed empirical comparison remains open.

- A working paper using the same opinion corpus would flip the verdict.
- A broader corpus can distinguish the project from the closest work.

## Positioning and lineage

**Honest contribution sentence:** The project measures how authentication
reasoning varies across courts after synthetic evidence became practically
available.

## Scoop risk

The risk is moderate because two active researchers have adjacent projects.

## Search methods and saturation evidence

1. Ran sixteen distinct queries across four routes.
2. Searched the closest authors and their coauthors.
3. Logged three saturation queries that produced no unseen close work.

| Route | Queries | Close works |
| --- | --- | --- |
| OpenAlex | 6 | 2 |
| Repositories | 5 | 1 |
| Open web | 5 | 0 |

## Access limitations and manual search packet

HeinOnline remained inaccessible. Run `"synthetic evidence" AND authentication`
and return any result published since 2024.

## Review date and recheck

Reviewed on 2026-08-19. Recheck by 2026-11-19 or sooner if a named researcher
posts a new working paper.
"""


class PreemptionReviewBuilderTests(unittest.TestCase):
    def test_wrapped_callouts_and_lists_remain_single_blocks(self) -> None:
        blocks = parse_blocks(
            "> **Verdict:** Partially preempted.\n"
            "The narrower empirical comparison remains open.\n\n"
            "- A working paper using the same corpus would\n"
            "  flip the verdict.\n\n"
            "1. Ran sixteen distinct queries across\n"
            "   four routes."
        )
        callout = next(block for block in blocks if block.kind == "callout")
        bullets = [block.text for block in blocks if block.kind == "bullet"]
        ordered = [block.text for block in blocks if block.kind == "ordered"]
        self.assertIn("comparison remains open", callout.text)
        self.assertIn("would flip the verdict", bullets[0])
        self.assertIn("four routes", ordered[0])

    def test_builds_structured_word_report_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "preemption_review_source.md"
            output = root / "preemption_review_v001.docx"
            source.write_text(SAMPLE_SOURCE, encoding="utf-8")

            build(source, output)

            self.assertTrue(output.is_file())
            self.assertGreater(output.stat().st_size, 10_000)
            document = Document(output)
            self.assertEqual(
                document.core_properties.title,
                "Preemption Review: Judicial Treatment of Synthetic Evidence",
            )
            self.assertGreaterEqual(len(document.tables), 2)
            self.assertEqual(document.tables[0].cell(0, 0).text, "Verdict")
            heading_text = {
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.style and paragraph.style.name == "Heading 1"
            }
            self.assertTrue(set(REQUIRED_SECTIONS) <= heading_text)

            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
                relationships = archive.read("word/_rels/document.xml.rels").decode("utf-8")
                header_parts = [name for name in archive.namelist() if name.startswith("word/header")]
                footer_parts = [name for name in archive.namelist() if name.startswith("word/footer")]
            self.assertIn("w:numPr", document_xml)
            self.assertIn('w:w="9360"', document_xml)
            self.assertIn("https://example.org/rivera", relationships)
            self.assertEqual(header_parts, [])
            self.assertEqual(footer_parts, [])

            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                build(source, output)

    def test_unresolved_template_marker_is_rejected(self) -> None:
        template = (ROOT / "workflow" / "templates" / "preemption_review_template.md").read_text(
            encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "unresolved placeholder"):
            parse_source(template)


class PreemptionReviewStageContractTests(unittest.TestCase):
    def test_word_report_is_the_active_stage_02_artifact(self) -> None:
        stages = {meta["stage_id"]: (meta, body) for _, meta, body in load_stages(ROOT)}
        stage_two, body = stages["02-preemption-review"]
        self.assertIn(
            "project/artifacts/preemption_review_vNNN.docx",
            stage_two["declared_outputs"],
        )
        self.assertNotIn(
            "project/artifacts/preemption_review_vNNN.md",
            stage_two["declared_outputs"],
        )
        self.assertIn("project/runs/<run_id>/preemption_review_source.md", stage_two["declared_outputs"])
        self.assertIn("project/runs/<run_id>/rendered_preemption_review/", stage_two["declared_outputs"])
        self.assertIn("scripts/build_preemption_review.py", body)
        self.assertIn("inspect every page at 100 percent zoom", body)
        for stage_id in ("03-feasibility-audit", "04-methods-design"):
            self.assertIn(
                "project/artifacts/preemption_review_vNNN.docx",
                stages[stage_id][0]["required_inputs"],
            )


if __name__ == "__main__":
    unittest.main()
