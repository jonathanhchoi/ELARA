"""Model advice is evidence-backed, platform-scoped, offline, and nonblocking."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "scripts"))

import model_readiness as readiness  # noqa: E402
import doctor  # noqa: E402


NOW = datetime(2035, 1, 2, 12, tzinfo=timezone.utc)


def evidence(platform="codex", now=NOW):
    record = readiness.evidence_template([platform], now)["platforms"][platform]
    model = "future-frontier-research-model"
    record.update({
        "recommended_model": model, "recommended_effort": "deep-research",
        "effort_policy": "resolved", "current_model": model,
        "current_effort": "deep-research", "host_surface": "Active desktop session",
        "selection_kind": "active_session",
        "sources": [{
            "url": "https://learn.chatgpt.com/docs/models" if platform == "codex" else "https://code.claude.com/docs/en/model-config",
            "retrieved_at": now.isoformat(),
            "finding": "Fixture: the strongest generally available model and its supported research effort.",
        }],
        "access": {
            "status": "available", "kind": "active_session", "model": model,
            "observed_at": now.isoformat(), "detail": "Fixture: native active-session metadata.",
        },
    })
    return record


def write_evidence(path, records):
    path.write_text(json.dumps({"schema_version": "1.0", "platforms": records}), encoding="utf-8")


class ModelReadinessTests(unittest.TestCase):
    def test_future_model_and_effort_names_work_for_either_provider(self):
        for platform in readiness.PLATFORMS:
            with self.subTest(platform=platform):
                result = readiness.assess(platform, evidence(platform), now=NOW)
                self.assertEqual(result["status"], "recommended")
                self.assertEqual(result["access_status"], "available")
                self.assertEqual(result["warnings"], [])
                self.assertEqual(result["basis"], "agent_collected_evidence")
                plans = " ".join(result["recommendations"])
                self.assertIn("Pro 20x" if platform == "codex" else "Max 20x", plans)
                self.assertNotIn("Max 20x" if platform == "codex" else "Pro 20x", plans)

    def test_available_but_not_selected_recommends_switch_not_purchase(self):
        record = evidence()
        record["current_model"] = "current-economy-model"
        record["access"]["kind"] = "account_model_catalog"
        result = readiness.assess("codex", record, now=NOW)
        self.assertEqual(result["status"], "selection_recommended")
        self.assertEqual(result["selection_status"], "different_model")
        self.assertNotIn("upgrading your plan", " ".join(result["warnings"]))

    def test_effort_mismatch_and_unknown_effort_are_separate(self):
        record = evidence()
        record["current_effort"] = "light"
        self.assertEqual(readiness.assess("codex", record, now=NOW)["selection_status"], "different_effort")
        record["current_effort"] = None
        result = readiness.assess("codex", record, now=NOW)
        self.assertEqual(result["selection_status"], "unknown")
        self.assertEqual(result["access_status"], "available")
        self.assertNotEqual(result["status"], "recommended")

    def test_configured_model_is_not_a_verified_active_selection(self):
        for kind in ("configuration", "user_report", "unknown"):
            record = evidence()
            record["selection_kind"] = kind
            record["access"]["kind"] = "account_model_catalog"
            result = readiness.assess("codex", record, now=NOW)
            self.assertEqual(result["access_status"], "available")
            self.assertEqual(result["selection_status"], "unknown")
            self.assertNotEqual(result["status"], "recommended")

    def test_model_without_effort_requires_explicit_not_supported(self):
        record = evidence()
        record.update(recommended_effort=None, current_effort=None, effort_policy="not_supported")
        self.assertEqual(readiness.assess("codex", record, now=NOW)["status"], "recommended")
        record["effort_policy"] = "unknown"
        self.assertNotEqual(readiness.assess("codex", record, now=NOW)["status"], "recommended")

    def test_positive_denial_recommends_access_upgrade(self):
        record = evidence("claude")
        record["current_model"] = "fallback-model"
        record["access"].update(status="unavailable", kind="host_access_status")
        result = readiness.assess("claude", record, now=NOW)
        self.assertEqual(result["status"], "upgrade_recommended")
        self.assertIn("strongly recommends upgrading", result["warnings"][0])

    def test_configuration_generic_catalog_and_user_report_never_confirm_access(self):
        for kind in ("configuration", "catalog_only", "user_report", "unknown"):
            for status in ("available", "unavailable"):
                with self.subTest(kind=kind, status=status):
                    record = evidence()
                    record["current_model"] = "another-model"
                    record["access"].update(kind=kind, status=status)
                    result = readiness.assess("codex", record, now=NOW)
                    self.assertEqual(result["access_status"], "unknown")
                    self.assertEqual(result["status"], "unverified")

    def test_access_to_fallback_is_not_access_to_strongest(self):
        record = evidence("claude")
        record["current_model"] = record["access"]["model"] = "fallback-model"
        self.assertEqual(readiness.assess("claude", record, now=NOW)["access_status"], "unknown")

    def test_missing_evidence_and_unresolved_recommendation_warn(self):
        for record in (None, readiness.evidence_template(["codex"], NOW)["platforms"]["codex"]):
            result = readiness.assess("codex", record, now=NOW)
            self.assertEqual(result["status"], "unverified")
            self.assertIn("not proof that access is missing", result["warnings"][0])

    def test_timestamps_are_fresh_timezone_aware_and_not_future_dated(self):
        for location in ("checked_at", "source", "access"):
            for stamp in ((NOW - timedelta(days=2)).isoformat(), (NOW + timedelta(hours=1)).isoformat(), "2035-01-02T12:00:00", "bad"):
                with self.subTest(location=location, stamp=stamp):
                    record = evidence()
                    if location == "source":
                        record["sources"][0]["retrieved_at"] = stamp
                    elif location == "access":
                        record["access"]["observed_at"] = stamp
                    else:
                        record[location] = stamp
                    self.assertEqual(readiness.assess("codex", record, now=NOW)["status"], "unverified")

    def test_sources_must_be_from_applicable_official_provider(self):
        for url in (
            "https://example.org/models", "https://learn.chatgpt.com.evil.example/models",
            "https://learn.chatgpt.com@evil.example/models", "http://learn.chatgpt.com/docs/models",
            "https://code.claude.com/docs/en/model-config", "https://learn.chatgpt.com/docs/models?token=private",
            "https://learn.chatgpt.com:bad/docs/models", "https://user:pass@learn.chatgpt.com/docs/models",
        ):
            with self.subTest(url=url):
                record = evidence()
                record["sources"][0]["url"] = url
                result = readiness.assess("codex", record, now=NOW)
                self.assertEqual(result["status"], "unverified")
                self.assertNotIn(url, json.dumps(result))
        record = evidence()
        record["sources"] = []
        self.assertEqual(readiness.assess("codex", record, now=NOW)["status"], "unverified")

    def test_malformed_and_contradictory_records_cannot_pass(self):
        records = [[], {}, "invalid", evidence(), evidence(), evidence(), evidence()]
        records[3]["access"]["status"] = "unavailable"
        records[4]["recommended_effort"] = None
        records[5]["access"]["model"] = "not-the-active-model"
        records[6]["unexpected"] = "not part of the contract"
        for record in records:
            with self.subTest(record=record):
                self.assertEqual(readiness.assess("codex", record, now=NOW)["status"], "unverified")

    def test_report_does_not_echo_private_input_or_raw_summaries(self):
        record = evidence()
        record["current_model"] = "sk-private-sentinel"
        result = readiness.assess("codex", record, now=NOW)
        self.assertNotIn("sk-private-sentinel", json.dumps(result))
        record = evidence()
        record["access"]["detail"] = "private-account-summary-sentinel"
        self.assertNotIn("private-account-summary-sentinel", json.dumps(readiness.assess("codex", record, now=NOW)))

    def test_file_assessment_is_scoped_and_records_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "evidence.json"
            records = {platform: evidence(platform) for platform in readiness.PLATFORMS}
            write_evidence(path, records)
            with patch("subprocess.run", side_effect=AssertionError("No subprocesses")), patch("urllib.request.urlopen", side_effect=AssertionError("No network")):
                report = readiness.build_advisory(["codex"], path, now=NOW)
            self.assertEqual(list(report["platforms"]), ["codex"])
            self.assertEqual(report["evidence_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(report["network_calls"], 0)
            self.assertEqual(report["model_calls"], 0)
            write_evidence(path, {"claude": evidence("claude")})
            self.assertEqual(readiness.build_advisory(["codex"], path, now=NOW)["platforms"]["codex"]["status"], "unverified")

    def test_invalid_missing_and_oversized_files_warn_without_exposing_contents(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "evidence.json"
            for contents in (None, b"private-json-sentinel", b"x" * (readiness.MAX_EVIDENCE_BYTES + 1), b'{"schema_version":"1.0","schema_version":"1.0","platforms":{}}', b'[]'):
                if contents is not None:
                    path.write_bytes(contents)
                report = readiness.build_advisory(["codex"], path, now=NOW)
                self.assertEqual(report["platforms"]["codex"]["status"], "unverified")
                self.assertNotIn("private-json-sentinel", json.dumps(report))

    def test_maintenance_does_not_even_read_evidence(self):
        with patch.object(readiness, "_load_evidence", side_effect=AssertionError("No file read")):
            report = readiness.build_advisory([], "unused.json", now=NOW)
        self.assertEqual(report["status"], "not_checked")
        self.assertEqual(report["warnings"], [])

    def test_cli_unknown_is_successful_advice_not_installation_failure(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts/model_readiness.py"), "--platform", "claude", "--json"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["platforms"]["claude"]["status"], "unverified")

    def test_doctor_retains_software_success_with_model_warning(self):
        hosts = {p: {"required": p == "codex"} for p in readiness.PLATFORMS}
        with patch.object(doctor, "_host_reports", return_value=(hosts, [], [])):
            report = doctor.build_report(ROOT, platform="codex", smoke=False)
        self.assertTrue(report["ok"], report["failures"])
        self.assertEqual(list(report["model_readiness"]["platforms"]), ["codex"])
        self.assertTrue(report["warnings"])

    def test_doctor_uses_explicit_fresh_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "evidence.json"
            write_evidence(path, {"claude": evidence("claude", datetime.now(timezone.utc))})
            hosts = {p: {"required": p == "claude"} for p in readiness.PLATFORMS}
            with patch.object(doctor, "_host_reports", return_value=(hosts, [], [])):
                report = doctor.build_report(ROOT, platform="claude", smoke=False, model_evidence=path)
            self.assertTrue(report["ok"], report["failures"])
            self.assertEqual(report["model_readiness"]["platforms"]["claude"]["status"], "recommended")

    def test_fresh_install_and_update_carry_evidence_and_preserve_project_files(self):
        from test_bootstrap import install

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "paper"
            path = root / "evidence.json"
            record = evidence("codex", datetime.now(timezone.utc))
            write_evidence(path, {"codex": record})
            environment = dict(os.environ, CODEX_MODEL_READINESS_TEST="1")
            summary = install(target, "--platform", "codex", "--model-evidence", str(path), env=environment)
            self.assertEqual(summary["_returncode"], 0, summary)
            self.assertEqual(summary["model_readiness"]["platforms"]["codex"]["status"], "recommended")
            report_path = target / "project/BOOTSTRAP.md"
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Model access and capacity", report)
            self.assertIn("ChatGPT Pro 20x", report)
            self.assertIn("model-readiness.md", report)
            self.assertIn("before substantive research", report)
            state = target / "project/PROJECT_STATE.md"
            state.write_text(state.read_text(encoding="utf-8") + "\nResearcher's existing note.\n", encoding="utf-8")
            snapshot = target / "project/ACCESS_MODEL_SNAPSHOT_v001.md"
            snapshot.write_text("Existing snapshot; do not replace.\n", encoding="utf-8")
            before = {p: p.read_bytes() for p in (state, snapshot)}
            # A new installation report cannot turn old evidence into a current pass.
            record["checked_at"] = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            write_evidence(path, {"codex": record})
            updated = install(target, "--update", "--platform", "codex", "--model-evidence", str(path), env=environment)
            self.assertEqual(updated["_returncode"], 0, updated)
            self.assertEqual(updated["model_readiness"]["platforms"]["codex"]["status"], "unverified")
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_manual_and_skipped_doctor_installations_warn_and_defer(self):
        from test_bootstrap import install

        with tempfile.TemporaryDirectory() as raw:
            for arguments in (("--platform", "none"), ("--skip-doctor",)):
                target = Path(raw) / ("manual" if len(arguments) == 2 else "skipped")
                summary = install(target, *arguments)
                self.assertEqual(summary["_returncode"], 0, summary)
                self.assertEqual(summary["model_readiness"]["status"], "not_checked")
                self.assertIn("not been verified", " ".join(summary["warnings"]))
                report = (target / "project/BOOTSTRAP.md").read_text(encoding="utf-8")
                self.assertIn("ChatGPT Pro 20x", report)
                self.assertIn("Claude Max 20x", report)

    def test_doctor_does_not_reclassify_software_failures_as_advice(self):
        hosts = {p: {"required": p == "codex"} for p in readiness.PLATFORMS}
        with patch.object(doctor, "_host_reports", return_value=(hosts, ["broken host fixture"], [])):
            report = doctor.build_report(ROOT, platform="codex", smoke=False)
        self.assertFalse(report["ok"])
        self.assertIn("broken host fixture", report["failures"])

    def test_installer_does_not_import_a_researcher_owned_advisory_helper(self):
        from test_bootstrap import install

        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "paper"
            (target / "scripts").mkdir(parents=True)
            helper = target / "scripts/model_readiness.py"
            text = "from pathlib import Path\nPath(__file__).with_name('executed.txt').touch()\n"
            helper.write_text(text, encoding="utf-8")
            for extra in ((), ("--update",)):
                summary = install(target, *extra)
                self.assertFalse(summary["ok"])
                self.assertIn("scripts/model_readiness.py", summary["essential_conflicts"])
                self.assertIn("your own file", " ".join(summary["doctor"]["failures"]))
                self.assertEqual(helper.read_text(encoding="utf-8"), text)
                self.assertFalse((target / "scripts/executed.txt").exists())

    def test_doctor_auto_checks_only_the_active_provider(self):
        hosts = {p: {"required": True, "active_session": p == "codex"} for p in readiness.PLATFORMS}
        with patch.object(doctor, "_host_reports", return_value=(hosts, [], [])):
            report = doctor.build_report(ROOT, platform="auto", smoke=False)
        self.assertEqual(list(report["model_readiness"]["platforms"]), ["codex"])
        hosts["codex"]["active_session"] = False
        with patch.object(doctor, "_host_reports", return_value=(hosts, [], [])):
            report = doctor.build_report(ROOT, platform="auto", smoke=False)
        self.assertEqual(report["model_readiness"]["status"], "not_checked")
        with patch.object(doctor, "_host_reports", return_value=(hosts, [], [])):
            report = doctor.build_report(ROOT, platform="all", smoke=False)
        self.assertEqual(set(report["model_readiness"]["platforms"]), set(readiness.PLATFORMS))

    def test_setup_contract_is_wired_and_has_no_fixed_model_names(self):
        shared = (ROOT / "workflow/shared/model-readiness.md").read_text(encoding="utf-8")
        for path in ("AGENTS.md", "README.md", "workflow/stages/00-initialize.md", "scripts/bootstrap.py"):
            self.assertIn("model-readiness.md", (ROOT / path).read_text(encoding="utf-8"))
        stage = (ROOT / "workflow/stages/00-initialize.md").read_text(encoding="utf-8")
        self.assertIn("project/model_readiness_evidence_vNNN.json", stage.split("---", 2)[1])
        self.assertIn("read-only", shared)
        self.assertIn("frozen/preregistered", shared)
        self.assertIn("24 hours", shared)
        implementation = (ROOT / "scripts/model_readiness.py").read_text(encoding="utf-8")
        for text in (implementation, shared):
            self.assertNotRegex(text.lower(), r"gpt-?\d|claude-(?:opus|sonnet|fable)-\d")


if __name__ == "__main__":
    unittest.main()
