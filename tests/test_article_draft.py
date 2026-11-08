from __future__ import annotations

import hashlib
import re
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

from build_article_draft import build, check, parse_source  # noqa: E402


def tiny_png(width: int = 40, height: int = 20) -> bytes:
    rows = b"".join(b"\x00" + bytes([200, 210, 230] * width) for _ in range(height))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


SOURCE = """---
title: "Do Judges Read Dictionaries?"
authors: "Jane Q. Researcher"
author_note: "Assistant Professor of Law, Example Law School."
running_title: "Judges and Dictionaries"
target_venue: "student-edited law review"
word_template: "law_review_v1"
sources: "project/runs/r1/article_sources.csv"
values: "project/runs/r1/article_values.csv"
source_versions: "project/artifacts/results/estimates.csv"
---

<!-- Guidance comments are ignored. -->

# Abstract

Judges say they read statutes the way ordinary people do. We checked {{value:n_opinions}} opinions and found that {{value:h1_share}} cite a dictionary. [[pending: one sentence on the second hypothesis]]

# Introduction {#intro}

Picture a judge with a dictionary.[^i1] She wants the ordinary meaning, and she wants it fast.[^i2]

We read {{value:n_opinions}} opinions using large language models (LLMs) and checked the coding against people.[^i3] [[note: Name the agreement rate here?]]

{{part:debate}} explains the debate, {{part:results}} reports the findings, and {{display:T1}} has the headline number.

[^i1]: *See* *Bostock v. Clayton County*, 590 U.S. 644, 654 (2020) {{src:S01}}.

[^i2]: *Id.* at 655 {{src:S01}}.

[^i3]: For the details, see *infra* {{part:app}}.

# The Dictionary Debate {#debate}

## What Textualists Say {#debate-text}

Textualists ask what a word meant to ordinary readers.[^d1] Critics say dictionaries are a poor guide.[^d2]

[^d1]: Jane Doe, *Dictionaries in Court*, 100 [Harv. L. Rev.]{.sc} 1, 5 (2020) {{src:S02}}.

[^d2]: Doe, *supra* note {{fn:d1}}, at 9 {{src:S02}}; [[citation needed: critics who argue that dictionaries mislead]].

## Why It Matters

> If the dictionary decides the case, its editors become lawmakers.[^d3]

[^d3]: An illustrative quotation.

# Results {#results}

About {{value:h1_share}} of opinions cite a dictionary. The change after 2010 is {{value:h2_effect}}.

!display table|project/artifacts/results/table1.csv#T1|Share of opinions citing a dictionary.
!display figure|project/artifacts/results/fig1.png#F1|Dictionary citations over time.|A line rising over time.
!pending table|T2|Dictionary citations by circuit.

# Conclusion

Judges read dictionaries, at least {{value:h1_share}} of the time. See {{display:T2}}.

# Appendix A. Coding and Validation {#app}

## Prompt

The coding prompt appears in {{part:app-prompt}}.

## The Full Prompt {#app-prompt}

!display equation|project/artifacts/results/eq1.tex#EQ1|Where Y is one when an opinion cites a dictionary.
"""


class ArticleDraftTests(unittest.TestCase):
    def _project(self, root: Path, source: str = SOURCE) -> Path:
        project = root / "project"
        retrieved = project / "sources" / "p1" / "retrieved"
        results = project / "artifacts" / "results"
        run = project / "runs" / "r1"
        for directory in (retrieved, results, run):
            directory.mkdir(parents=True, exist_ok=True)
        case = retrieved / "case.txt"
        case.write_text("Opinion text.\n", encoding="utf-8")
        article = retrieved / "article.txt"
        article.write_text("Article text.\n", encoding="utf-8")
        digest = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (case, article)}
        (run / "article_sources.csv").write_text(
            "source_id,citation,url,access_date,local_path,sha256,origin\n"
            f'S01,"Bostock v. Clayton County, 590 U.S. 644 (2020)",https://example.gov/b,2026-11-08,'
            f"project/sources/p1/retrieved/case.txt,{digest[case]},stage 02\n"
            f'S02,"Jane Doe, Dictionaries in Court, 100 Harv. L. Rev. 1 (2020)",https://example.org/d,2026-11-08,'
            f"project/sources/p1/retrieved/article.txt,{digest[article]},stage 02\n"
            "S03,Unused source,https://example.org/u,2026-11-08,,,stage 02\n",
            encoding="utf-8",
        )
        (results / "estimates.csv").write_text("estimand,estimate\nH1,0.42\n", encoding="utf-8")
        (results / "table1.csv").write_text("Specification,Estimate\nMain,0.42\nAlternative,0.40\n",
                                            encoding="utf-8")
        (results / "fig1.png").write_bytes(tiny_png())
        (results / "eq1.tex").write_text("Y_i = \\alpha + \\beta D_i\n", encoding="utf-8")
        (run / "article_values.csv").write_text(
            "key,value,status,source,description\n"
            "h1_share,42 percent,verified,project/artifacts/results/estimates.csv#H1,\n"
            'n_opinions,"12,400",verified,project/artifacts/results/estimates.csv#N,\n'
            "h2_effect,,pending,,the change after 2010\n",
            encoding="utf-8",
        )
        path = run / "article_draft_source.md"
        path.write_text(source, encoding="utf-8")
        return path

    def _build(self, root: Path, source: str = SOURCE, suffix: str = "docx") -> tuple[Path, dict]:
        path = self._project(root, source)
        output = root / "project" / "artifacts" / f"article_draft_v001.{suffix}"
        manifest = root / "project" / "runs" / "r1" / f"manifest_{suffix}.json"
        payload = build(path, output, manifest, root)
        return output, payload

    def _error(self, source: str) -> str:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError) as caught:
                check(self._project(root, source), root)
            return str(caught.exception)

    def test_word_output_has_real_footnotes_star_note_numbering_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output, payload = self._build(Path(directory))
            document = Document(output)
            headings = [p.text for p in document.paragraphs if p.style.name.startswith("Heading")]
            self.assertEqual(
                headings,
                [
                    "INTRODUCTION",
                    "I. THE DICTIONARY DEBATE",
                    "A. What Textualists Say",
                    "B. Why It Matters",
                    "II. RESULTS",
                    "CONCLUSION",
                    "APPENDIX A. CODING AND VALIDATION",
                    "A.1. Prompt",
                    "A.2. The Full Prompt",
                ],
            )
            self.assertEqual(document.paragraphs[0].text, "DO JUDGES READ DICTIONARIES?")
            self.assertEqual(len(document.comments), 1)
            self.assertEqual(len(document.tables), 1)
            body = "\n".join(p.text for p in document.paragraphs)
            self.assertIn("Part I explains the debate, Part II reports the findings, and Table 1", body)
            self.assertIn("12,400 opinions", body)
            self.assertIn("[[pending: the change after 2010]]", body)
            self.assertIn("See Table 2.", body)
            self.assertIn("appears in Appendix A.2.", body)
            self.assertNotIn("{{", body)
            with zipfile.ZipFile(output) as archive:
                document_xml = archive.read("word/document.xml").decode("utf-8")
                footnotes_xml = archive.read("word/footnotes.xml").decode("utf-8")
                header_xml = "".join(
                    archive.read(name).decode("utf-8") for name in archive.namelist()
                    if name.startswith("word/header")
                )
            self.assertIn('w:customMarkFollows="1"', document_xml)
            self.assertEqual(document_xml.count("<w:footnoteReference"), 7)
            self.assertIn("illustrative draft", footnotes_xml)
            self.assertIn("Example Law School", footnotes_xml)
            self.assertNotIn("[Footnote Contents]", footnotes_xml)
            self.assertIn("supra note 4, at 9", re.sub(r"<[^>]+>", "", footnotes_xml))
            self.assertNotIn("{{src", footnotes_xml)
            self.assertIn("<w:smallCaps/>", footnotes_xml)
            self.assertIn('w:highlight w:val="yellow"', footnotes_xml)
            self.assertIn("Judges and Dictionaries", header_xml)
            self.assertEqual(payload["draft_status"], "illustrative")
            self.assertEqual(payload["counts"]["footnotes"], 6)
            self.assertEqual(payload["counts"]["parts"], 2)
            self.assertEqual(payload["counts"]["appendices"], 1)
            kinds = {item["footnote"]: item["kind"] for item in payload["citations"]}
            self.assertEqual(kinds, {1: "cited", 2: "cited", 3: "internal", 4: "cited", 5: "cited",
                                     6: "explanatory"})
            self.assertEqual(payload["sources_unused"], ["S03"])
            self.assertEqual(
                sorted(item["kind"] for item in payload["placeholders"]),
                ["citation_needed", "pending_display", "pending_text", "pending_value"],
            )
            self.assertEqual(payload["notes_to_researcher"][0]["text"], "Name the agreement rate here?")
            self.assertEqual(payload["values_used"]["h2_effect"]["status"], "pending")
            self.assertEqual(payload["word_template"]["template_id"], "law_review_v1")

    def test_markdown_review_copy_resolves_tokens_and_numbers_footnotes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output, payload = self._build(Path(directory), suffix="md")
            text = output.read_text(encoding="utf-8")
            self.assertIn("## I. THE DICTIONARY DEBATE", text)
            self.assertIn("[^5]: Doe, *supra* note 4, at 9; [[citation needed:", text)
            self.assertIn("[^2]: *Id.* at 655.", text)
            self.assertNotIn("Name the agreement rate", text)
            self.assertNotIn("{{", text)
            self.assertEqual(payload["output"]["format"], "md")

    def test_check_writes_nothing_and_reports_style_warnings(self) -> None:
        source = SOURCE.replace(
            "She wants the ordinary meaning, and she wants it fast.",
            "This groundbreaking study of 87 cases shows the API matters.",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._project(root, source)
            before = sorted(p for p in root.rglob("*"))
            summary = check(path, root)
            self.assertEqual(before, sorted(p for p in root.rglob("*")))
        kinds = {(item["kind"], item["detail"].split(" ")[0]) for item in summary["warnings"]}
        self.assertIn(("overstatement_or_filler", "groundbreaking"), kinds)
        self.assertIn(("undefined_acronym", "API"), kinds)
        self.assertIn(("number_not_from_values_table", "87"), kinds)
        self.assertNotIn(("undefined_acronym", "LLM"), kinds)

    def test_refuses_to_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output, _payload = self._build(root)
            with self.assertRaises(ValueError):
                build(root / "project/runs/r1/article_draft_source.md", output,
                      root / "project/runs/r1/other.json", root)

    def test_id_must_repeat_the_single_preceding_source(self) -> None:
        message = self._error(SOURCE.replace("*Id.* at 655 {{src:S01}}.", "*Id.* at 655 {{src:S02}}."))
        self.assertIn("begins with Id.", message)

    def test_supra_must_point_to_a_note_citing_the_same_source(self) -> None:
        message = self._error(SOURCE.replace("note {{fn:d1}}, at 9 {{src:S02}}", "note {{fn:i1}}, at 9 {{src:S02}}"))
        self.assertIn("supra note 1", message)

    def test_citation_without_source_is_rejected(self) -> None:
        message = self._error(SOURCE.replace(" {{src:S01}}.\n\n[^i2]", ".\n\n[^i2]"))
        self.assertIn("note 1 looks like a citation", message)

    def test_unknown_source_and_changed_archive_are_rejected(self) -> None:
        self.assertIn("not in the source register", self._error(SOURCE.replace("{{src:S02}}.", "{{src:S09}}.")))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._project(root)
            (root / "project/sources/p1/retrieved/case.txt").write_text("changed\n", encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                check(path, root)
            self.assertIn("does not match its sha256", str(caught.exception))

    def test_structure_requirements(self) -> None:
        no_appendix = SOURCE.split("# Appendix A.")[0].replace(" {{part:app}}", " the appendix")
        no_appendix = no_appendix.replace("For the details, see *infra* the appendix.", "Details follow.")
        self.assertIn("at least one Appendix", self._error(no_appendix))
        self.assertIn("TODO-DRAFT", self._error(SOURCE.replace("Picture a judge", "TODO-DRAFT: hook")))
        long_abstract = SOURCE.replace("Judges say they read", "word " * 260 + "Judges say they read")
        self.assertIn("the limit is 250", self._error(long_abstract))
        self.assertIn("first heading must be # Abstract", self._error(SOURCE.replace("# Abstract", "# Summary")))

    def test_footnote_and_token_errors(self) -> None:
        self.assertIn("never referenced", self._error(SOURCE + "\n[^orphan]: Extra note.\n"))
        self.assertIn("has no definition", self._error(SOURCE.replace("fast.[^i2]", "fast.[^i9]")))
        self.assertIn("no heading has anchor", self._error(SOURCE.replace("{{part:debate}}", "{{part:nowhere}}")))
        self.assertIn("not in the values table", self._error(SOURCE.replace("{{value:h1_share}} cite", "{{value:missing}} cite")))
        self.assertIn("project path would be visible",
                      self._error(SOURCE.replace("Critics say", "See project/artifacts/x.csv. Critics say")))
        self.assertIn("footnote [^i1] is not allowed here",
                      self._error(SOURCE.replace("We checked {{value:n_opinions}}", "We checked[^i1] {{value:n_opinions}}")))
        self.assertIn("unknown bracket note", self._error(SOURCE.replace("[[note:", "[[todo:")))

    def test_verified_value_needs_its_result_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self._project(root)
            values = root / "project/runs/r1/article_values.csv"
            values.write_text(values.read_text(encoding="utf-8").replace("estimates.csv#H1", "missing.csv#H1"),
                              encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                check(path, root)
            self.assertIn("source file does not exist", str(caught.exception))

    def test_template_is_rejected_until_its_markers_are_replaced(self) -> None:
        template = (ROOT / "workflow/templates/article_draft_template.md").read_text(encoding="utf-8")
        with self.assertRaises(ValueError) as caught:
            parse_source(template)
        self.assertIn("TODO-DRAFT", str(caught.exception))
        for heading in ("# Abstract", "# Introduction", "# Conclusion", "# Appendix A."):
            self.assertIn(heading, template)
        for convention in ("{{src:", "{{value:", "{{part:", "[[citation needed:", "[[pending:", "!pending"):
            self.assertIn(convention, template)


if __name__ == "__main__":
    unittest.main()
