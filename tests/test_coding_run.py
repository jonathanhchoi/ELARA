"""The settings-driven runner for Stages 08, 11, 12, and 15 (scripts/coding_run.py).

Workers are simulated by submitting envelopes through ``unit_fanout.submit``, exactly
the call a real worker makes, using the public-domain Constitution fixture.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "scripts"))

import coding_run  # noqa: E402
from coding_run import RunnerError  # noqa: E402
from unit_fanout import submit  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "public_domain_e2e" / "inputs"
AUDIT_SCHEMA = ROOT / "workflow" / "templates" / "interpretive_audit_result.schema.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class Project:
    """A throwaway project folder holding the fixture corpus and frozen inputs."""

    def __init__(self, root: Path):
        self.root = root
        self.project = root / "project"
        self.artifacts = self.project / "artifacts"
        self.runs = self.project / "runs"
        shutil.copytree(FIXTURE / "corpus", self.project / "corpus" / "corpus_v001")
        self.artifacts.mkdir(parents=True)
        self.runs.mkdir()
        shutil.copy(FIXTURE / "schema.json", self.artifacts / "coding_schema_v001.json")
        shutil.copy(FIXTURE / "human_codes.csv", self.artifacts / "human_codes_v001.csv")
        (self.artifacts / "codebook_v001.md").write_text("Codebook: federal assignment.\n", encoding="utf-8")
        (self.artifacts / "coding_prompt_v001.md").write_text("Code the clause.\n", encoding="utf-8")
        (self.artifacts / "coding_prompt_paraphrase_v001.md").write_text(
            "Classify the clause.\n", encoding="utf-8"
        )
        with (FIXTURE / "corpus_manifest.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        with (self.artifacts / "unit_space_v001.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["unit_id", "file", "period", "pilot"])
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "unit_id": row["unit_id"],
                        "file": Path(row["file"]).name,
                        "period": row["period"],
                        "pilot": row["pilot"],
                    }
                )
        self.units = self.artifacts / "unit_space_v001.csv"
        self.model = {
            json.loads(line)["unit_id"]: json.loads(line)
            for line in (FIXTURE / "model_a.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        }

    def settings(self, name: str = "run_settings_v001.json", **overrides) -> Path:
        settings = {
            "settings_version": "1.0",
            "stage": "08-pilot",
            "inputs": [
                {"role": "instructions", "path": "coding_prompt_v001.md"},
                {"role": "codebook", "path": "codebook_v001.md"},
                {"role": "result_schema", "path": "coding_schema_v001.json"},
            ],
            "units": {
                "id_column": "unit_id",
                "fields": ["period"],
                "sources": [{"source_id": "text", "path_column": "file", "root": "../corpus/corpus_v001"}],
            },
            "quotes": {"anchors": [{"path": "exact_quote"}], "normalize": "whitespace"},
            "retry": {"on": ["quote_failed", "schema_failed", "worker_error"], "max_attempts": 2},
            "review": {"blind_seed": 7},
            "compare": {
                "fields": ["federal_assignment"],
                "human_codes": "human_codes_v001.csv",
                "bootstrap": {"resamples": 200, "seed": 11},
            },
        }
        settings.update(overrides)
        path = self.artifacts / name
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
        return path

    def envelope(self, assignment: dict, *, result=None, status="succeeded", error=None) -> dict:
        return {
            "contract_version": assignment["contract_version"],
            "assignment_id": assignment["assignment_id"],
            "unit_id": assignment["unit_id"],
            "attempt": assignment["attempt"],
            "status": status,
            "result": result,
            "error": error,
            "provenance": {"route": "fixture"},
        }

    def pending(self, run_dir: Path, block: int | None = None) -> list[dict]:
        listed = coding_run.fanout.status(run_dir, include_pending=True, block=block)
        return [
            json.loads(Path(item["assignment_path"]).read_text(encoding="utf-8"))
            for item in listed["pending_assignments"]
        ]

    def code_all(self, run_dir: Path, *, block: int | None = None, alter=None) -> None:
        """Submit the fixture's model row for every pending assignment."""
        for assignment in self.pending(run_dir, block):
            unit = assignment["payload"]["unit"]["unit_id"]
            result = dict(self.model[unit])
            if alter:
                result = alter(assignment, result)
            if result is None:
                envelope = self.envelope(assignment, status="refused", error="fixture refusal")
            else:
                envelope = self.envelope(assignment, result=result)
            submit(run_dir, assignment["assignment_id"], envelope)


class CodingRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.p = Project(Path(self._temp.name))

    def tearDown(self) -> None:
        self._temp.cleanup()

    # ------------------------------------------------------------------ settings and sample

    def test_invalid_settings_report_every_problem_at_once(self) -> None:
        path = self.p.settings(batch_size=0, quotes={"anchors": [{"path": "a[b]"}]})
        with self.assertRaises(RunnerError) as caught:
            coding_run.load_settings(path)
        message = str(caught.exception)
        self.assertIn("batch_size", message)
        self.assertIn("quotes/anchors", message)

    def test_sample_is_reproducible_stratified_and_honors_exclusions(self) -> None:
        exclusion = self.p.artifacts / "held_out_sample_v001.csv"
        exclusion.write_text("unit_id\nu01\n", encoding="utf-8")
        settings = self.p.settings(
            sample={"salt": "pilot-v001", "size": 4, "strata": ["period"], "exclude": ["held_out_sample_v001.csv"]}
        )
        first = coding_run.sample(settings, self.p.units, self.p.artifacts / "pilot_sample_v001.csv")
        second = coding_run.sample(settings, self.p.units, self.p.artifacts / "pilot_sample_v002.csv")
        self.assertEqual(first["out_sha256"], second["out_sha256"])
        self.assertEqual(first["selected"], 4)
        self.assertEqual(first["per_stratum"], {"early": 2, "later": 2})
        rows = read_csv(self.p.artifacts / "pilot_sample_v001.csv")
        self.assertNotIn("u01", {row["unit_id"] for row in rows})
        self.assertEqual(first["not_eligible"], {"excluded_by_earlier_list": 1})
        with self.assertRaises(RunnerError):
            coding_run.sample(settings, self.p.units, self.p.artifacts / "pilot_sample_v001.csv")

    # ------------------------------------------------------------------ prepare

    def test_dry_run_checks_everything_and_writes_nothing(self) -> None:
        settings = self.p.settings(
            batch_size=3,
            conditions=[
                {"id": "base", "model": "model-a"},
                {"id": "para", "replicates": 2, "replace": {"instructions": "paraphrase"}},
            ],
            inputs=[
                {"role": "instructions", "path": "coding_prompt_v001.md"},
                {"role": "paraphrase", "path": "coding_prompt_paraphrase_v001.md"},
                {"role": "codebook", "path": "codebook_v001.md"},
                {"role": "result_schema", "path": "coding_schema_v001.json"},
            ],
        )
        run_dir = self.p.runs / "20261104T120000Z_08-pilot_r001"
        summary = coding_run.prepare(settings, self.p.units, run_dir, dry_run=True)
        self.assertFalse(run_dir.exists())
        self.assertEqual(summary["assignments"], 8 + 16)
        self.assertEqual([block["condition"] for block in summary["blocks"]], ["base"] * 3 + ["para"] * 3)

    def test_paraphrase_condition_reads_its_own_prompt_in_place_of_the_base_prompt(self) -> None:
        settings = self.p.settings(
            conditions=[{"id": "base"}, {"id": "para", "replace": {"instructions": "paraphrase"}}],
            inputs=[
                {"role": "instructions", "path": "coding_prompt_v001.md"},
                {"role": "paraphrase", "path": "coding_prompt_paraphrase_v001.md"},
                {"role": "codebook", "path": "codebook_v001.md"},
                {"role": "result_schema", "path": "coding_schema_v001.json"},
            ],
        )
        run_dir = self.p.runs / "20261104T120000Z_15-robustness_r001"
        coding_run.prepare(settings, self.p.units, run_dir)
        roles = {}
        for assignment in self.p.pending(run_dir):
            payload = assignment["payload"]
            roles[payload["condition"]] = [item["role"] for item in payload["read_in_order"]]
        self.assertEqual(roles["base"], ["instructions", "codebook", "result_schema"])
        self.assertEqual(roles["para"], ["paraphrase", "codebook", "result_schema"])

    def test_missing_source_becomes_a_recorded_gap_and_a_changed_source_fails_closed(self) -> None:
        (self.p.project / "corpus" / "corpus_v001" / "u02_article_i_section_2.txt").unlink()
        settings = self.p.settings()
        run_dir = self.p.runs / "20261104T120000Z_08-pilot_r001"
        summary = coding_run.prepare(settings, self.p.units, run_dir)
        self.assertEqual((summary["units_assigned"], summary["gaps"]), (7, 1))

        with self.p.units.open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        hashed = self.p.artifacts / "unit_space_hashed_v001.csv"
        with hashed.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[*rows[0].keys(), "sha256"])
            writer.writeheader()
            for row in rows:
                writer.writerow({**row, "sha256": "0" * 64})
        sources = [{"source_id": "text", "path_column": "file", "root": "../corpus/corpus_v001", "sha256_column": "sha256"}]
        settings = self.p.settings(units={"id_column": "unit_id", "sources": sources})
        with self.assertRaisesRegex(RunnerError, "does not match its recorded sha256"):
            coding_run.prepare(settings, hashed, self.p.runs / "20261104T120000Z_08-pilot_r002")

    def test_command_line_prints_json_and_reports_errors_without_a_traceback(self) -> None:
        import subprocess

        settings = self.p.settings()
        run_dir = self.p.runs / "20261104T120000Z_08-pilot_r001"
        script = str(ROOT / "scripts" / "coding_run.py")
        done = subprocess.run(
            [sys.executable, script, "prepare", "--settings", str(settings), "--units", str(self.p.units),
             "--run-dir", str(run_dir), "--dry-run"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["assignments"], 8)
        failed = subprocess.run(
            [sys.executable, script, "check", "--run-dir", str(run_dir)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(failed.returncode, 1)
        self.assertTrue(failed.stderr.startswith("ERROR: "), failed.stderr)
        self.assertNotIn("Traceback", failed.stderr)

    def test_a_run_id_is_never_reused(self) -> None:
        settings = self.p.settings()
        run_dir = self.p.runs / "20261104T120000Z_08-pilot_r001"
        coding_run.prepare(settings, self.p.units, run_dir)
        with self.assertRaisesRegex(RunnerError, "new run ID"):
            coding_run.prepare(settings, self.p.units, run_dir)

    # ------------------------------------------------------------------ the pilot route end to end

    def test_pilot_route_checks_quotes_retries_logs_decisions_and_closes(self) -> None:
        settings = self.p.settings()
        run_dir = self.p.runs / "20261104T120000Z_08-pilot_r001"
        prepared = coding_run.prepare(settings, self.p.units, run_dir)
        self.assertEqual(prepared["next"]["action"], "launch")
        self.assertEqual(prepared["next"]["claude_code"]["workflow"], "elr-observation-fanout")
        self.assertEqual(prepared["next"]["claude_code"]["args"]["block"], 1)

        def bad_quote(assignment, result):
            if result["unit_id"] == "u03":
                result = dict(result, exact_quote="The Senate shall meet on Tuesdays")
            return result

        self.p.code_all(run_dir, alter=bad_quote)
        status = coding_run.check(run_dir)
        self.assertEqual(status["pending"], 0)
        self.assertEqual(status["awaiting_retry"], ["u03--base--r1-attempt001"])
        self.assertEqual(status["next"]["action"], "check_apply")
        self.assertNotIn("Senate shall meet", json.dumps(status))
        with self.assertRaisesRegex(RunnerError, "check --apply"):
            coding_run.close(run_dir)

        applied = coding_run.check(run_dir, apply=True)
        self.assertEqual(applied["retried"], [{"from": "u03--base--r1-attempt001", "to": "u03--base--r1-attempt002"}])
        self.assertEqual(applied["decisions_logged"], 1)
        self.assertEqual(applied["next"]["action"], "launch")
        self.assertTrue(Path(applied["checkpoint"]).is_file())
        decisions = [
            json.loads(line)
            for line in (run_dir / "failure_decisions.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(decisions[0]["disposition"], "retried as u03--base--r1-attempt002")
        self.assertEqual(decisions[0]["decided_by"], "assistant")

        self.p.code_all(run_dir)
        self.assertEqual(coding_run.check(run_dir)["next"]["action"], "close")
        with self.assertRaisesRegex(RunnerError, "close the run first"):
            coding_run.review(run_dir)
        closed = coding_run.close(run_dir)
        self.assertEqual(closed["final_status_counts"], {"succeeded": 8})
        dataset = [json.loads(line) for line in (run_dir / "normalized_outputs.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(dataset), 8)
        u03 = next(row for row in dataset if row["unit_id"] == "u03")
        self.assertEqual((u03["attempt"], u03["superseded"]), (2, ["u03--base--r1-attempt001"]))
        self.assertTrue((run_dir / u03["return_path"]).is_file())
        ledger = {row["unit_id"]: row for row in read_csv(run_dir / "pilot_ledger.csv")}
        self.assertEqual(len(ledger), 8)
        self.assertEqual(ledger["u03"]["attempt_outcomes"], "1:quote_failed; 2:succeeded")
        self.assertEqual(len(read_csv(run_dir / "schema_quote_compliance.csv")), 9)
        quotes = read_csv(run_dir / "quote_checks.csv")
        self.assertEqual(sum(row["status"] == "not_found" for row in quotes), 1)
        with self.assertRaisesRegex(RunnerError, "already closed"):
            coding_run.close(run_dir)

        sheet = coding_run.review(run_dir, version="001", human_codes=self.p.artifacts / "human_codes_v001.csv")
        rows = read_csv(Path(sheet["review_sheet"]))
        self.assertEqual(len(rows), 8)
        self.assertIn("researcher_valid (yes/no)", rows[0])
        u08 = next(row for row in rows if row["unit_id"] == "u08")
        self.assertEqual((u08["result.federal_assignment"], u08["human.federal_assignment"]), ("false", "true"))

        compared = coding_run.compare(run_dir, version="001")
        disagreements = read_csv(Path(compared["disagreements"]))
        self.assertEqual([(row["unit_id"], row["coder_b"]) for row in disagreements], [("u08", "human")])
        metrics = json.loads(Path(compared["metrics"]).read_text(encoding="utf-8"))
        pair = metrics["fields"]["federal_assignment"]["pairs"][0]
        self.assertEqual((pair["n"], pair["agree"]), (4, 3))

    def test_blind_review_hides_conditions_behind_letters_with_a_separate_key(self) -> None:
        settings = self.p.settings(conditions=[{"id": "base"}, {"id": "repeat"}])
        run_dir = self.p.runs / "20261104T120000Z_08-pilot_r001"
        coding_run.prepare(settings, self.p.units, run_dir)
        self.p.code_all(run_dir)
        coding_run.check(run_dir, apply=True)
        coding_run.close(run_dir)
        sheet = coding_run.review(run_dir, version="001", blind=True)
        rows = read_csv(Path(sheet["review_sheet"]))
        key = read_csv(Path(sheet["key"]))
        self.assertEqual(len(rows), 16)
        self.assertEqual({row["coder"] for row in rows}, {"A", "B"})
        self.assertEqual({row["coder"] for row in key}, {"base", "repeat"})
        self.assertNotIn("base", (Path(sheet["review_sheet"])).read_text(encoding="utf-8-sig"))

    # ------------------------------------------------------------------ batches, models, stopping rule

    def test_blocks_carry_the_condition_model_and_need_a_checkpoint_before_the_next(self) -> None:
        settings = self.p.settings(
            batch_size=4,
            conditions=[{"id": "base", "model": "model-a", "effort": "high"}, {"id": "second", "model": "model-b"}],
        )
        run_dir = self.p.runs / "20261104T120000Z_15-robustness_r001"
        prepared = coding_run.prepare(settings, self.p.units, run_dir)
        self.assertEqual(prepared["next"]["claude_code"]["args"], {
            "run_dir": str(run_dir.resolve()), "block": 1, "model": "model-a", "effort": "high"})
        self.p.code_all(run_dir, block=1)
        self.assertEqual(coding_run.check(run_dir)["next"]["action"], "check_apply")
        after = coding_run.check(run_dir, apply=True)
        self.assertEqual((after["next"]["action"], after["next"]["block"]), ("launch", 2))
        for block in (2, 3):
            self.p.code_all(run_dir, block=block)
            coding_run.check(run_dir, apply=True)
        last = coding_run.check(run_dir)["next"]
        self.assertEqual(last["claude_code"]["args"]["model"], "model-b")
        self.assertEqual(last["codex"]["agent"], "elr_worker")

    def test_stopping_rule_stops_launching_on_widespread_failure(self) -> None:
        settings = self.p.settings(batch_size=4, retry={"on": ["quote_failed"]}, stop={"batch_failure_rate": 0.25})
        run_dir = self.p.runs / "20261104T120000Z_11-scale-up_r001"
        coding_run.prepare(settings, self.p.units, run_dir)

        def refuse_two(assignment, result):
            return None if result["unit_id"] in {"u01", "u02"} else result

        self.p.code_all(run_dir, block=1, alter=refuse_two)
        result = coding_run.check(run_dir, apply=True)
        self.assertEqual(result["next"]["action"], "stop")
        self.assertIn("2 of 4 units failed", result["next"]["reasons"][0])

    def test_skip_retry_records_the_researchers_decision(self) -> None:
        settings = self.p.settings()
        run_dir = self.p.runs / "20261104T120000Z_08-pilot_r001"
        coding_run.prepare(settings, self.p.units, run_dir)
        self.p.code_all(run_dir, alter=lambda a, r: dict(r, exact_quote="nowhere") if r["unit_id"] == "u05" else r)
        with self.assertRaisesRegex(RunnerError, "no failed attempt awaiting a decision"):
            coding_run.check(run_dir, apply=True, skip_retry=["u04--base--r1-attempt001"])
        coding_run.check(
            run_dir, apply=True, skip_retry=["u05--base--r1-attempt001"], decided_by="researcher"
        )
        decision = json.loads((run_dir / "failure_decisions.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(decision["decided_by"], "researcher")
        self.assertIn("retry declined", decision["disposition"])
        closed = coding_run.close(run_dir)
        self.assertEqual(closed["final_status_counts"], {"quote_failed": 1, "succeeded": 7})

    # ------------------------------------------------------------------ source views and quote rules

    def test_line_view_locators_tolerance_and_alphanumeric_matching(self) -> None:
        original = "First line here.\nThe court held that the stat-\nute applies.\nLast line.\n"
        source = self.p.project / "corpus" / "opinion.lines.txt"
        source.write_text(coding_run._line_view(original), encoding="utf-8")
        self.assertTrue(source.read_text(encoding="utf-8").startswith("L1: First line here.\nL2: The court"))
        entry = {
            "source_id": "opinion",
            "path": str(source),
            "sha256": coding_run.fanout.sha256_file(source),
            "view": "lines",
        }
        rules = {
            "anchors": [{"path": "anchors[]", "source_field": "source_id", "locator_field": "locator"}],
            "normalize": "alphanumeric",
            "locator": "line",
            "line_tolerance": 1,
        }
        result = {
            "anchors": [
                {"source_id": "opinion", "locator": "L2", "quote": "the statute applies"},
                {"source_id": "opinion", "locator": "L4", "quote": "First line here"},
                {"source_id": "opinion", "locator": "L1-L9", "quote": "First line"},
                {"source_id": "web", "locator": "L1", "quote": "anything"},
                {"source_id": "opinion", "locator": "L1", "quote": "never said"},
            ]
        }
        rows = coding_run.check_quotes(result, {"sources": [entry]}, rules, {})
        self.assertEqual(
            [row["status"] for row in rows],
            ["ok", "wrong_location", "bad_locator", "unknown_source", "not_found"],
        )
        rules["wrong_location"] = "pass"
        rules["unchecked_sources"] = ["web"]
        rows = coding_run.check_quotes(result, {"sources": [entry]}, rules, {})
        self.assertEqual([row["status"] for row in rows][1:4], ["ok_elsewhere", "bad_locator", "unchecked"])

    def test_window_view_marks_the_target_and_quotes_match_without_markers(self) -> None:
        settings = self.p.settings(
            view={"mode": "window", "words_before": 2, "words_after": 2, "target_pattern": "Congress"},
            quotes={"anchors": [{"path": "exact_quote"}], "normalize": "whitespace", "max_words": 30},
        )
        run_dir = self.p.runs / "20261104T120000Z_08-pilot_r001"
        summary = coding_run.prepare(settings, self.p.units, run_dir)
        self.assertEqual(summary["units_assigned"], 2)
        self.assertEqual(summary["gap_reasons"], {"window target not found in source text": 6})
        pending = {item["payload"]["unit"]["unit_id"]: item for item in self.p.pending(run_dir)}
        shown = Path(pending["u01"]["payload"]["sources"][0]["path"]).read_text(encoding="utf-8")
        self.assertEqual(shown, "in a >>> Congress <<< of the")
        self.assertNotIn("u01_article_i_section_1.txt", json.dumps(pending["u01"]))
        quotes = {"u01": "in a >>> Congress <<< of", "u05": "Congress may from time to time ordain"}
        for unit, assignment in pending.items():
            result = dict(self.p.model[unit], exact_quote=quotes[unit])
            submit(run_dir, assignment["assignment_id"], self.p.envelope(assignment, result=result))
        self.assertEqual(coding_run.check(run_dir)["awaiting_retry"], ["u05--base--r1-attempt001"])
        coding_run.check(run_dir, apply=True)
        self.p.code_all(run_dir, alter=lambda a, r: dict(r, exact_quote="as the Congress may"))
        coding_run.check(run_dir, apply=True)
        closed = coding_run.close(run_dir)
        self.assertEqual(closed["final_status_counts"], {"succeeded": 2, "unreadable": 6})

    # ------------------------------------------------------------------ Stage 11 then Stage 12 audit

    def test_audit_run_covers_every_coded_observation_and_queues_unsupported_ones(self) -> None:
        coding = self.p.settings(stage="11-scale-up")
        coding_dir = self.p.runs / "20261104T120000Z_11-scale-up_r001"
        coding_run.prepare(coding, self.p.units, coding_dir)
        self.p.code_all(coding_dir)
        coding_run.check(coding_dir, apply=True)
        coding_run.close(coding_dir, version="001")
        dataset = self.p.artifacts / "coding_dataset_v001.jsonl"
        self.assertTrue((self.p.artifacts / "quote_verification_v001.csv").is_file())
        from validate_run import validate_coding

        errors, _summary = validate_coding(self.p.units, self.p.artifacts / "coding_ledger_v001.csv")
        self.assertEqual(errors, [])

        shutil.copy(AUDIT_SCHEMA, self.p.artifacts / "interpretive_audit_result_v001.json")
        (self.p.artifacts / "audit_prompt_v001.md").write_text("Audit the observation.\n", encoding="utf-8")
        audit = self.p.settings(
            "audit_settings_v001.json",
            stage="12-interpretive-verification",
            inputs=[
                {"role": "instructions", "path": "audit_prompt_v001.md"},
                {"role": "codebook", "path": "codebook_v001.md"},
                {"role": "result_schema", "path": "interpretive_audit_result_v001.json"},
            ],
            audit={"hide_fields": ["status"]},
            quotes=None,
        )
        settings = json.loads(audit.read_text(encoding="utf-8"))
        settings.pop("quotes")
        settings.pop("units")
        audit.write_text(json.dumps(settings), encoding="utf-8")
        audit_dir = self.p.runs / "20261104T130000Z_12-interpretive-verification_r001"
        coding_run.prepare(audit, dataset, audit_dir)
        for assignment in self.p.pending(audit_dir):
            observation = assignment["payload"]["observation"]
            self.assertNotIn("status", observation)
            self.assertTrue(Path(assignment["payload"]["sources"][0]["path"]).is_file())
            disposition = "unsupported" if observation["unit_id"] == "u08" else "supported"
            result = {"disposition": disposition, "reasoning": "fixture", "locations_inspected": ["whole clause"]}
            submit(audit_dir, assignment["assignment_id"], self.p.envelope(assignment, result=result))
        coding_run.check(audit_dir, apply=True)
        coding_run.close(audit_dir, version="001")
        coverage = read_csv(self.p.artifacts / "interpretive_audit_coverage_v001.csv")
        queue = read_csv(self.p.artifacts / "interpretive_recoding_queue_v001.csv")
        self.assertEqual(len(coverage), 8)
        self.assertEqual([(row["unit_id"], row["finding"], row["route"]) for row in queue], [("u08", "unsupported", "11-scale-up")])

    # ------------------------------------------------------------------ robustness comparison

    def test_paired_differences_against_the_human_benchmark_are_reproducible(self) -> None:
        settings = self.p.settings(stage="15-robustness", conditions=[{"id": "base"}, {"id": "para"}])
        run_dir = self.p.runs / "20261104T120000Z_15-robustness_r001"
        coding_run.prepare(settings, self.p.units, run_dir)

        def flip(assignment, result):
            if assignment["payload"]["condition"] == "para" and result["unit_id"] == "u08":
                result = dict(result, federal_assignment=True)
            return result

        self.p.code_all(run_dir, alter=flip)
        coding_run.check(run_dir, apply=True)
        coding_run.close(run_dir, version="001")
        with self.assertRaises(RunnerError):
            coding_run.compare(run_dir)
        compared = coding_run.compare(run_dir, version="001")
        metrics = json.loads(Path(compared["metrics"]).read_text(encoding="utf-8"))
        difference = metrics["fields"]["federal_assignment"]["paired_differences"][0]
        self.assertEqual((difference["coder"], difference["versus"], difference["n"]), ("para", "base", 4))
        self.assertAlmostEqual(difference["difference"], 0.25)
        self.assertEqual(len(difference["ci95"]), 2)
        self.assertEqual(
            [row["unit_id"] for row in read_csv(Path(compared["disagreeing_units"]))], ["u08"]
        )


class RunnerContractTests(unittest.TestCase):
    def test_settings_guide_documents_every_settings_field(self) -> None:
        guide = (ROOT / "workflow" / "templates" / "coding_run_settings.md").read_text(encoding="utf-8")
        for key in coding_run.SETTINGS_SCHEMA["properties"]:
            self.assertIn(f"`{key}`", guide, key)
        for command in ("sample", "prepare", "check", "close", "review", "compare"):
            self.assertIn(f"coding_run.py {command}", guide, command)

    def test_the_four_run_stages_use_the_runner_and_build_no_driver(self) -> None:
        for name in ("08-pilot", "11-scale-up", "12-interpretive-verification", "15-robustness"):
            body = (ROOT / "workflow" / "stages" / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("coding_run.py", body, name)
            self.assertNotIn("deterministic driver", body, name)
            self.assertNotIn("raw_model_outputs/", body, name)
        pilot = (ROOT / "workflow" / "stages" / "08-pilot.md").read_text(encoding="utf-8")
        self.assertIn("is not reviewed per project", pilot)
        scale_up = (ROOT / "workflow" / "stages" / "11-scale-up.md").read_text(encoding="utf-8")
        self.assertIn("byte for byte", scale_up)
        self.assertIn("project/artifacts/coding_run_settings_vNNN.json", scale_up)


if __name__ == "__main__":
    unittest.main()
