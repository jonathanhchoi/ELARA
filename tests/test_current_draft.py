from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
for folder in (ROOT / "scripts", Path(__file__).resolve().parent):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import current_draft  # noqa: E402
import storage  # noqa: E402
from build_article_draft import build  # noqa: E402
import test_article_draft  # noqa: E402  (module import, so its tests are not collected twice)


STATE = """---
schema_version: "1.5"
workflow_version: "2.21.0"
project_slug: "fixture"
current_draft_placeholder: null
current_stage: "04-methods-design"
status: "ready"
active_artifacts: {active}
approvals: {{}}
outstanding_user_inputs: []
last_run_id: null
updated_at: "2026-11-09T00:00:00Z"
---

# Project state
"""

DECISIONS = """# Decision log

## DEC-20261109T000000Z-001

- decision: selected
- decision_text: Sample every published opinion from 2000 to 2020.

## DEC-20261109T000100Z-002

- decision: selected
- decision_text: Exclude unpublished opinions (from the draft, P0002).
"""


def methods_draft(path: Path, sample_sentence: str, *, tracked: bool = False) -> None:
    document = Document()
    document.add_heading("Study Design", level=1)
    document.add_paragraph(sample_sentence)
    paragraph = document.add_paragraph("We exclude unpublished opinions.")
    if tracked:
        paragraph._p.append(parse_xml(
            f'<w:ins {nsdecls("w")} w:id="1" w:author="Jane" w:date="2026-11-09T00:00:00Z">'
            '<w:r><w:t xml:space="preserve"> We also exclude per curiam orders.</w:t></w:r></w:ins>'))
        paragraph._p.append(parse_xml(
            f'<w:del {nsdecls("w")} w:id="2" w:author="Jane" w:date="2026-11-09T00:00:00Z">'
            '<w:r><w:delText xml:space="preserve"> And dissents.</w:delText></w:r></w:del>'))
    document.add_paragraph("A sentence of framing that states no method.")
    document.save(str(path))


class CurrentDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "project").mkdir()
        self.write_state({})
        (self.root / "project" / "DECISIONS.md").write_text(DECISIONS, encoding="utf-8")
        self.draft = self.root / "current_draft.docx"

    def write_state(self, active: dict) -> None:
        (self.root / "project" / "PROJECT_STATE.md").write_text(
            STATE.format(active=json.dumps(active)).replace("current_draft_placeholder: null\n", ""),
            encoding="utf-8",
        )

    def reconcile(self, result: dict) -> None:
        self.write_state({
            "current_draft": {"path": result["snapshot"], "sha256": result["sha256"]},
            "current_draft_text": result["text"],
        })

    def test_status_reports_presence_and_change(self) -> None:
        self.assertEqual(storage.current_draft(self.root)["present"], False)
        (self.root / "~$current_draft.docx").write_bytes(b"lock file")
        self.assertEqual(storage.current_draft(self.root)["present"], False)
        methods_draft(self.root / "Current_Draft.docx", "We sample every opinion.")
        report = storage.current_draft(self.root)
        self.assertTrue(report["present"])
        self.assertTrue(report["changed"])
        self.assertIsNone(report["reconciled_sha256"])
        sha = hashlib.sha256((self.root / "Current_Draft.docx").read_bytes()).hexdigest()
        self.write_state({"current_draft": {"path": "project/inputs/current_draft_v001.docx", "sha256": sha}})
        self.assertFalse(storage.current_draft(self.root)["changed"])
        (self.root / "Current_Draft.docx").unlink()
        self.assertTrue(storage.current_draft(self.root)["removed"])

    def test_snapshot_extracts_diffs_and_resumes(self) -> None:
        self.assertEqual(current_draft.snapshot(self.root)["status"], "absent")
        methods_draft(self.draft, "We sample every published opinion from 2000 to 2020.")
        first = current_draft.snapshot(self.root)
        self.assertEqual(first["status"], "snapshot")
        self.assertEqual(first["snapshot"], "project/inputs/current_draft_v001.docx")
        self.assertIsNone(first["changes"])
        text = (self.root / first["text"]).read_text(encoding="utf-8")
        self.assertIn("[P0001|H1] Study Design", text)
        self.assertIn("[P0002] We sample every published opinion from 2000 to 2020.", text)
        self.reconcile(first)
        self.assertEqual(current_draft.snapshot(self.root)["status"], "unchanged")

        methods_draft(self.draft, "We sample every published opinion from 1990 to 2020.")
        second = current_draft.snapshot(self.root)
        self.assertEqual(second["version"], 2)
        self.assertEqual([item["now"] for item in second["changes"]["changed"]], ["P0002"])
        self.assertEqual(second["changes"]["added"], [])
        again = current_draft.snapshot(self.root)
        self.assertEqual(again["snapshot"], second["snapshot"], "an interrupted reconciliation reuses its copy")
        self.assertFalse((self.root / "project/inputs/current_draft_v003.docx").exists())

    def test_tracked_changes_read_as_accepted_and_listed(self) -> None:
        methods_draft(self.draft, "We sample every opinion.", tracked=True)
        content = current_draft.extract(self.draft)
        texts = [paragraph["text"] for paragraph in content["paragraphs"]]
        self.assertIn("We exclude unpublished opinions. We also exclude per curiam orders.", texts)
        self.assertFalse(any("dissents" in text for text in texts))
        kinds = sorted((change["kind"], change["paragraph"]) for change in content["changes"])
        self.assertEqual(kinds, [("deleted", "P0003"), ("inserted", "P0003")])

    def test_footnotes_and_comments_from_a_word_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = test_article_draft.ArticleDraftTests("test_refuses_to_overwrite")._project(root)
            output = root / "draft.docx"
            build(source, output, root / "manifest.json", root)
            content = current_draft.extract(output)
        footnotes = {note["id"]: note["text"] for note in content["footnotes"]}
        self.assertIn("F*", footnotes)
        self.assertIn("Bostock", footnotes["F1"])
        self.assertIn("supra note 4", footnotes["F5"])
        self.assertEqual(len(content["comments"]), 1)
        self.assertEqual(content["comments"][0]["text"], "Name the agreement rate here?")
        body = " ".join(paragraph["text"] for paragraph in content["paragraphs"])
        self.assertIn("with a dictionary.[^1]", body)

    def _table(self, rows: list[str]) -> Path:
        path = self.root / "project" / "artifacts" / "draft_reconciliation_v002.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(",".join(current_draft.COLUMNS) + "\n" + "\n".join(rows) + "\n", encoding="utf-8")
        return path

    def test_check_validates_quotes_records_decisions_and_coverage(self) -> None:
        methods_draft(self.draft, "We sample every published opinion from 2000 to 2020.")
        first = current_draft.snapshot(self.root)
        self.reconcile(first)
        methods_draft(self.draft, "We sample every published opinion from 1990 to 2020.")
        second = current_draft.snapshot(self.root)
        text = self.root / second["text"]
        previous = self.root / first["text"]
        good = self._table([
            'R001,P0002,"from 1990 to 2020",sampling,conflicts_unfrozen,DEC-20261109T000000Z-001,'
            'Asked the researcher; the sample period is not yet frozen,pending',
        ])
        summary = current_draft.check(good, text, previous, self.root)
        self.assertEqual(summary["categories"], {"conflicts_unfrozen": 1})
        self.assertEqual(summary["pending"], ["R001"])

        bad_quote = self._table(['R001,P0002,"from 1985 to 2020",sampling,matches,DEC-20261109T000000Z-001,,'])
        with self.assertRaisesRegex(ValueError, "word for word"):
            current_draft.check(bad_quote, text, previous, self.root)
        uncovered = self._table(['R001,P0003,"exclude unpublished",sampling,matches,DEC-20261109T000100Z-002,,'])
        with self.assertRaisesRegex(ValueError, "changed passage P0002 has no row"):
            current_draft.check(uncovered, text, previous, self.root)
        unknown = self._table(['R001,P0002,"1990",sampling,settles_open,none,Recorded as the researcher\'s choice,'
                               'DEC-20991231T000000Z-009'])
        with self.assertRaisesRegex(ValueError, "decision_id must name a record"):
            current_draft.check(unknown, text, previous, self.root)
        missing_record = self._table(['R001,P0002,"1990",sampling,matches,none,,'])
        with self.assertRaisesRegex(ValueError, "needs the record"):
            current_draft.check(missing_record, text, previous, self.root)


if __name__ == "__main__":
    unittest.main()
