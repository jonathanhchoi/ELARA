"""The mechanical stage-completion check (scripts/stage_check.py)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import coding_run  # noqa: E402
from stage_check import check_stage  # noqa: E402
from test_coding_run import Project  # noqa: E402
from workflow_lib import parse_frontmatter  # noqa: E402


def stage_meta(stage_id: str) -> dict:
    meta, _body = parse_frontmatter(ROOT / "workflow" / "stages" / f"{stage_id}.md")
    return meta


class StageCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        (self.root / "project" / "runs").mkdir(parents=True)
        (self.root / "project" / "artifacts").mkdir()
        for name in ("DECISIONS.md", "RUN_LEDGER.md", "DEVIATIONS.md"):
            (self.root / "project" / name).write_text(f"# {name}\n", encoding="utf-8")
        self.active: dict = {}
        self.approvals: dict = {}

    def tearDown(self) -> None:
        self._temp.cleanup()

    def state(self, current: str, status: str, last_run_id: str | None = None, **extra) -> None:
        fields = {
            "schema_version": "1.5",
            "workflow_version": "2.18.0",
            "project_slug": "fixture",
            "current_stage": current,
            "status": status,
            "active_artifacts": self.active,
            "approvals": self.approvals,
            "outstanding_user_inputs": extra.get("outstanding", []),
            "last_run_id": last_run_id,
            "updated_at": "2026-11-04T00:00:00Z",
        }
        lines = ["---"] + [f"{key}: {json.dumps(value)}" for key, value in fields.items()] + ["---", "", "# Project state", ""]
        (self.root / "project" / "PROJECT_STATE.md").write_text("\n".join(lines), encoding="utf-8")

    def make_outputs(self, stage_id: str, run_id: str, *, skip: tuple[str, ...] = ()) -> None:
        """Create every required output of a stage (version 001) and record artifacts as active."""
        run_dir = self.root / "project" / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        with (self.root / "project" / "RUN_LEDGER.md").open("a", encoding="utf-8") as handle:
            handle.write(f"- {run_id} started\n")
        for item in stage_meta(stage_id)["declared_outputs"]:
            if " (" in item or item in skip:
                continue
            path = item.replace("<run_id>", run_id).replace("vNNN", "v001")
            target = self.root / path
            if item.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            elif not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("fixture\n", encoding="utf-8")
            if "vNNN" in item:
                self.active[Path(item).name.replace("_vNNN", "").split(".")[0]] = path

    def check(self, stage: str) -> dict:
        return check_stage(self.root, stage, kit_root=ROOT)

    # ------------------------------------------------------------------ results

    def test_complete_when_outputs_are_active_and_state_has_moved_on(self) -> None:
        run_id = "20261104T120000Z_14-analysis-and-correction_r001"
        self.make_outputs("14-analysis-and-correction", run_id)
        self.state("15-robustness", "ready", run_id)
        report = self.check("14")
        self.assertEqual((report["result"], report["done"]), ("complete", True), report)
        self.assertEqual(report["run_id"], run_id)
        self.assertEqual((report["missing"], report["not_active"], report["problems"]), ([], [], []))

    def test_missing_inactive_and_changed_outputs_are_listed_exactly(self) -> None:
        run_id = "20261104T120000Z_14-analysis-and-correction_r001"
        self.make_outputs("14-analysis-and-correction", run_id)
        (self.root / "project" / "artifacts" / "analysis_report_v001.md").unlink()
        del self.active["analysis_execution_plan"]
        self.active["analysis_dataset"] = {
            "path": "project/artifacts/analysis_dataset_v001.csv",
            "sha256": "0" * 64,
        }
        self.state("15-robustness", "ready", run_id)
        report = self.check("14-analysis-and-correction")
        self.assertFalse(report["done"])
        self.assertIn("project/artifacts/analysis_report_v001.md is recorded as active but does not exist", report["problems"])
        self.assertEqual(report["not_active"], ["project/artifacts/analysis_execution_plan_v001.md"])
        self.assertIn(
            "project/artifacts/analysis_dataset_v001.csv does not match the sha256 recorded in active_artifacts",
            report["problems"],
        )

    def test_the_highest_active_version_is_the_one_checked(self) -> None:
        run_id = "20261104T120000Z_14-analysis-and-correction_r001"
        self.make_outputs("14-analysis-and-correction", run_id)
        self.active["analysis_report_old"] = "project/artifacts/analysis_report_v001.md"
        self.active["analysis_report"] = "project/artifacts/analysis_report_v002.md"
        self.state("15-robustness", "ready", run_id)
        self.assertIn(
            "project/artifacts/analysis_report_v002.md is recorded as active but does not exist",
            self.check("14")["problems"],
        )

    def test_a_gated_stage_awaiting_approval_is_done_without_its_gate_memo(self) -> None:
        run_id = "20261104T120000Z_08-pilot_r001"
        self.make_outputs("08-pilot", run_id)
        self.state("08-pilot", "awaiting_approval", run_id, outstanding=["pilot-acceptance"])
        report = self.check("08")
        self.assertEqual((report["result"], report["done"]), ("awaiting_approval", True), report)
        memo = next(item for item in report["conditional"] if "pilot_acceptance" in item["output"])
        self.assertFalse(memo["present"])

        self.approvals["pilot-acceptance"] = {"decision": "approved"}
        self.state("09-freeze-and-preregister", "ready", run_id)
        report = self.check("08")
        self.assertFalse(report["done"])
        self.assertEqual(report["missing"], ["project/artifacts/pilot_acceptance_vNNN.md"])

    def test_moving_past_a_gate_that_was_never_approved_is_a_problem(self) -> None:
        run_id = "20261104T120000Z_07-adversarial-review_r001"
        self.make_outputs("07-adversarial-review", run_id)
        self.state("08-pilot", "ready", run_id)
        report = self.check("07")
        self.assertFalse(report["done"])
        self.assertIn("state has moved past 07-adversarial-review but the design-freeze gate is not approved", report["problems"])

    def test_failure_route_and_researcher_stop_end_the_stage_paused_does_not(self) -> None:
        self.state("12-interpretive-verification", "failed")
        self.assertEqual((self.check("12")["result"], self.check("12")["done"]), ("failure_route", True))
        self.state("12-interpretive-verification", "waiting_for_user", outstanding=["budget decision"])
        self.assertEqual((self.check("12")["result"], self.check("12")["done"]), ("stopped", True))
        self.state("12-interpretive-verification", "paused")
        self.assertEqual((self.check("12")["result"], self.check("12")["done"]), ("in_progress", False))
        self.state("10-corpus-acquisition", "running")
        self.assertEqual(self.check("12")["result"], "not_started")

    def test_a_run_missing_from_the_run_ledger_is_a_problem(self) -> None:
        run_id = "20261104T120000Z_14-analysis-and-correction_r001"
        self.make_outputs("14-analysis-and-correction", run_id)
        (self.root / "project" / "RUN_LEDGER.md").write_text("# Run ledger\n", encoding="utf-8")
        self.state("15-robustness", "ready", run_id)
        self.assertIn(f"run {run_id} has no entry in project/RUN_LEDGER.md", self.check("14")["problems"])

    # ------------------------------------------------------------------ with the coding runner

    def test_a_closed_coding_run_passes_and_a_later_edit_to_its_dataset_fails(self) -> None:
        project = Project(self.root / "kitless")
        run_id = "20261104T120000Z_11-scale-up_r001"
        settings = project.settings(stage="11-scale-up")
        run_dir = project.runs / run_id
        coding_run.prepare(settings, project.units, run_dir)
        project.code_all(run_dir)
        coding_run.close(run_dir, version="001")
        self.root = project.root
        for name in ("DECISIONS.md", "DEVIATIONS.md"):
            (project.project / name).write_text("#\n", encoding="utf-8")
        (project.project / "RUN_LEDGER.md").write_text(f"- {run_id} started and closed\n", encoding="utf-8")
        for name in ("coding_revision_queue_v001.csv", "scale_up_report_v001.md"):
            (project.artifacts / name).write_text("fixture\n", encoding="utf-8")
        for name in (
            "coding_dataset_v001.jsonl", "coding_ledger_v001.csv", "schema_validation_v001.csv",
            "quote_verification_v001.csv", "coding_revision_queue_v001.csv", "scale_up_report_v001.md",
        ):
            self.active[name.split("_v001")[0]] = f"project/artifacts/{name}"
        self.state("12-interpretive-verification", "ready", run_id)
        report = self.check("11")
        self.assertEqual((report["result"], report["done"]), ("complete", True), report)

        with (project.artifacts / "coding_dataset_v001.jsonl").open("a", encoding="utf-8") as handle:
            handle.write("{}\n")
        report = self.check("11")
        self.assertFalse(report["done"])
        self.assertTrue(any("dataset output changed" in item for item in report["problems"]), report["problems"])

    def test_an_unclosed_coding_run_is_not_done(self) -> None:
        project = Project(self.root / "kitless")
        run_id = "20261104T120000Z_08-pilot_r001"
        coding_run.prepare(project.settings(), project.units, project.runs / run_id)
        self.root = project.root
        (project.project / "RUN_LEDGER.md").write_text(f"- {run_id}\n", encoding="utf-8")
        self.state("08-pilot", "awaiting_approval", run_id)
        self.assertIn(f"run {run_id} is not closed (run scripts/coding_run.py close)", self.check("08")["problems"])

    # ------------------------------------------------------------------ command line

    def test_command_line_exit_status_follows_done(self) -> None:
        script = str(ROOT / "scripts" / "stage_check.py")
        self.state("12-interpretive-verification", "failed")
        done = subprocess.run(
            [sys.executable, script, "--stage", "12", "--root", str(self.root), "--kit-root", str(ROOT)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(json.loads(done.stdout)["done"])
        self.state("12-interpretive-verification", "running")
        running = subprocess.run(
            [sys.executable, script, "--stage", "12-interpretive-verification", "--root", str(self.root), "--kit-root", str(ROOT)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(running.returncode, 1)
        bad = subprocess.run(
            [sys.executable, script, "--stage", "pilot", "--root", str(self.root), "--kit-root", str(ROOT)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(bad.returncode, 2)
        self.assertTrue(bad.stderr.startswith("ERROR: unknown stage"))


class GoalConditionContractTests(unittest.TestCase):
    def test_every_long_running_stage_completes_on_stage_check(self) -> None:
        for path in sorted((ROOT / "workflow" / "stages").glob("*.md")):
            meta, _body = parse_frontmatter(path)
            if not meta["long_running"]:
                continue
            condition = meta["goal_condition"]
            self.assertIn(f"`python scripts/stage_check.py --stage {meta['stage_id']}` reports `done: true`", condition, path.name)
            self.assertLess(len(condition), 400, path.name)


if __name__ == "__main__":
    unittest.main()
