from __future__ import annotations

import codecs
import csv
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from check_docs import validate_docs  # noqa: E402
from test_acceptance import copy_kit  # noqa: E402
from validate_workflow import validate_repository, validate_state  # noqa: E402
from workflow_lib import parse_frontmatter  # noqa: E402


def run_script(script: str, *arguments: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *arguments],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def write_manifest(manifest: Path, root: Path, relatives: list[str]) -> None:
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["artifact_path", "sha256", "bytes"])
        for relative in relatives:
            data = (root / relative).read_bytes()
            writer.writerow([relative, hashlib.sha256(data).hexdigest(), len(data)])


class EncodingAndScopeTests(unittest.TestCase):
    def test_bom_prefixed_state_file_parses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp) / "kit"
            copy_kit(ROOT, kit)
            state = kit / "project" / "PROJECT_STATE.md"
            text = state.read_text(encoding="utf-8")
            state.write_bytes(codecs.BOM_UTF8 + text.encode("utf-8"))
            meta, _body = parse_frontmatter(state)
            self.assertEqual(meta["status"], "ready")
            self.assertEqual(validate_state(kit), [])

    def test_researcher_content_is_never_scanned_but_kit_surfaces_are(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp) / "kit"
            copy_kit(ROOT, kit)
            inputs = kit / "project" / "inputs"
            (inputs / "notes.md").write_bytes("a “smart-quoted” note".encode("cp1252"))
            (inputs / "draft.md").write_text(
                "```\nunbalanced fence\n\n[broken](./no-such-file.md)\n", encoding="utf-8"
            )
            self.assertEqual(validate_docs(kit), [])
            self.assertEqual(validate_repository(kit), [])
            (kit / "workflow" / "junk.md").write_text("```\nunbalanced fence\n", encoding="utf-8")
            errors = validate_docs(kit)
            self.assertTrue(any("junk.md" in error and "unbalanced" in error for error in errors))


class RepositoryValidationTests(unittest.TestCase):
    def test_misspelled_required_input_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp) / "kit"
            copy_kit(ROOT, kit)
            stage = kit / "workflow" / "stages" / "11-scale-up.md"
            text = stage.read_text(encoding="utf-8")
            self.assertIn("project/artifacts/pilot_acceptance_vNNN.md", text)
            stage.write_text(
                text.replace(
                    "project/artifacts/pilot_acceptance_vNNN.md",
                    "project/artifacts/pilot_aceptance_vNNN.md",
                    1,
                ),
                encoding="utf-8",
            )
            errors = validate_repository(kit)
            self.assertTrue(
                any("pilot_aceptance" in error and "not a declared output" in error for error in errors),
                errors,
            )

    def test_orphan_wrapper_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp) / "kit"
            copy_kit(ROOT, kit)
            orphan = kit / ".claude" / "skills" / "elr-99-bogus"
            orphan.mkdir()
            (orphan / "SKILL.md").write_text(
                '---\nname: "elr-99-bogus"\ndescription: "Leftover wrapper."\n---\n\n# Bogus\n',
                encoding="utf-8",
            )
            errors = validate_repository(kit)
            self.assertTrue(
                any("orphan wrapper" in error and "elr-99-bogus" in error for error in errors),
                errors,
            )

    def test_malformed_stage_id_is_an_error_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp) / "kit"
            copy_kit(ROOT, kit)
            stage = kit / "workflow" / "stages" / "11-scale-up.md"
            text = stage.read_text(encoding="utf-8")
            stage.write_text(
                text.replace('stage_id: "11-scale-up"', 'stage_id: "xx-scale-up"', 1),
                encoding="utf-8",
            )
            errors = validate_repository(kit)
            self.assertTrue(any("stage_id must be" in error for error in errors), errors)


class FreezeVerifierTests(unittest.TestCase):
    def test_verify_freeze_passes_then_fails_on_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frozen").mkdir()
            (root / "frozen" / "analysis.py").write_text("print('frozen')\n", encoding="utf-8")
            (root / "codebook.md").write_text("# Codebook v1\n", encoding="utf-8")
            manifest = root / "frozen_artifact_manifest_v001.csv"
            write_manifest(manifest, root, ["frozen/analysis.py", "codebook.md"])
            passing = run_script("verify_freeze.py", "--manifest", str(manifest), "--root", str(root))
            self.assertEqual(passing.returncode, 0, passing.stderr)
            self.assertIn("PASS", passing.stdout)
            (root / "codebook.md").write_text("# Codebook v1, quietly edited\n", encoding="utf-8")
            failing = run_script("verify_freeze.py", "--manifest", str(manifest), "--root", str(root))
            self.assertNotEqual(failing.returncode, 0)
            self.assertIn("codebook.md", failing.stderr)


class RunReconciliationTests(unittest.TestCase):
    def write_corpus_fixture(self, root: Path, space_rows: str, manifest_rows: str) -> tuple[Path, Path]:
        unit_space = root / "unit_space_v001.csv"
        manifest = root / "corpus_manifest_v001.csv"
        unit_space.write_text("unit_id,note\n" + space_rows, encoding="utf-8")
        manifest.write_text("unit_id,status\n" + manifest_rows, encoding="utf-8")
        return unit_space, manifest

    def test_corpus_passes_on_consistent_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unit_space, manifest = self.write_corpus_fixture(
                Path(tmp), "u1,a\nu2,b\nu3,c\n", "u1,retrieved\nu2,retrieved\nu3,unavailable\n"
            )
            result = run_script(
                "validate_run.py", "corpus", "--unit-space", str(unit_space), "--manifest", str(manifest)
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_corpus_fails_on_duplicate_unit_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unit_space, manifest = self.write_corpus_fixture(
                Path(tmp), "u1,a\nu1,b\nu3,c\n", "u1,retrieved\nu3,retrieved\n"
            )
            result = run_script(
                "validate_run.py", "corpus", "--unit-space", str(unit_space), "--manifest", str(manifest)
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate unit ID", result.stderr)

    def test_corpus_fails_on_status_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            unit_space, manifest = self.write_corpus_fixture(
                Path(tmp), "u1,a\nu2,b\nu3,c\n", "u1,retrieved\nu2,retrieved\nu3,\n"
            )
            result = run_script(
                "validate_run.py", "corpus", "--unit-space", str(unit_space), "--manifest", str(manifest)
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("status counts sum to 2", result.stderr)


class DoctorTests(unittest.TestCase):
    def test_doctor_passes_on_the_real_kit(self) -> None:
        result = run_script("doctor.py", "--platform", "none")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)
        self.assertIn("python-docx", result.stdout)
        self.assertIn("offline one-unit fan-out smoke passed", result.stdout)
        self.assertIn("offline research fan-out smoke passed", result.stdout)
        self.assertIn("restricted worker definitions and saved workflows present", result.stdout)

    def test_doctor_fails_when_a_worker_definition_loses_its_tool_restriction(self) -> None:
        # A worker that inherits the host's interactive tools can crash the host (2026-08-17
        # incident); the doctor must fail closed on a missing or unrestricted definition.
        from doctor import _worker_agent_failures  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "kit"
            copy_kit(ROOT, root)
            self.assertEqual(_worker_agent_failures(root), [])
            research = root / ".claude" / "agents" / "elr-research-worker.md"
            text = research.read_text(encoding="utf-8")
            research.write_text(text.replace("disallowedTools: mcp__*,", "disallowedTools:"), encoding="utf-8")
            failures = _worker_agent_failures(root)
            self.assertTrue(any("mcp__*" in failure for failure in failures), failures)
            coding = root / ".claude" / "agents" / "elr-worker.md"
            text = coding.read_text(encoding="utf-8")
            coding.write_text(text.replace("tools: Read, Bash, Glob, Grep", "tools: Read, Bash, WebFetch"), encoding="utf-8")
            failures = _worker_agent_failures(root)
            self.assertTrue(any("grants web tools" in failure for failure in failures), failures)
            coding.unlink()
            result = subprocess.run(
                [sys.executable, str(root / "scripts" / "doctor.py"), "--platform", "none", "--skip-smoke", "--root", str(root)],
                text=True, capture_output=True, timeout=120, check=False,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("missing .claude/agents/elr-worker.md", result.stdout + result.stderr)

    def test_doctor_checks_the_codex_worker_agents_and_the_saved_workflows(self) -> None:
        # The same roles on Codex are custom sub-agents in .codex/agents/; the doctor must fail
        # closed when one is renamed, loses its instructions or sandbox, gains an MCP server, or
        # when a saved workflow stops launching the restricted agent type.
        from doctor import _worker_agent_failures  # noqa: PLC0415

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "kit"
            copy_kit(ROOT, root)
            self.assertEqual(_worker_agent_failures(root), [])
            codex_worker = root / ".codex" / "agents" / "elr-worker.toml"
            original = codex_worker.read_text(encoding="utf-8")
            codex_worker.write_text(original.replace('name = "elr_worker"', 'name = "worker"'), encoding="utf-8")
            failures = _worker_agent_failures(root)
            self.assertTrue(any('name = "elr_worker"' in failure for failure in failures), failures)
            codex_worker.write_text(original + '\n[mcp_servers.docs]\nurl = "https://example.invalid/mcp"\n', encoding="utf-8")
            failures = _worker_agent_failures(root)
            self.assertTrue(any("declares an MCP server" in failure for failure in failures), failures)
            codex_worker.write_text(original.replace('sandbox_mode = "workspace-write"', ""), encoding="utf-8")
            failures = _worker_agent_failures(root)
            self.assertTrue(any("no sandbox_mode" in failure for failure in failures), failures)
            codex_worker.write_text(original, encoding="utf-8")
            self.assertEqual(_worker_agent_failures(root), [])
            workflow = root / ".claude" / "workflows" / "elr-research-fanout.js"
            text = workflow.read_text(encoding="utf-8")
            workflow.write_text(text.replace("agentType: 'elr-research-worker'", "agentType: 'general-purpose'"), encoding="utf-8")
            failures = _worker_agent_failures(root)
            self.assertTrue(any("general-purpose" in failure for failure in failures), failures)
            self.assertTrue(any("agentType elr-research-worker" in failure for failure in failures), failures)
            codex_research = root / ".codex" / "agents" / "elr-research-worker.toml"
            codex_research.unlink()
            result = subprocess.run(
                [sys.executable, str(root / "scripts" / "doctor.py"), "--platform", "none", "--skip-smoke", "--root", str(root)],
                text=True, capture_output=True, timeout=120, check=False,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("missing .codex/agents/elr-research-worker.toml", result.stdout + result.stderr)


class HostProbeTests(unittest.TestCase):
    """The doctor's agent-host checks, with the CLI probe and the session
    environment controlled. Codex Desktop on Windows installs a packaged
    codex.exe that other programs are not allowed to start (WinError 5), while
    the CODEX_* variables of the session running the check prove the host
    works; the doctor accepts that evidence without weakening any check
    outside an active session (issue observed 2026-08-24)."""

    WINDOWSAPPS_CODEX = (
        "C:\\Program Files\\WindowsApps\\OpenAI.Codex_26.818.5229.0_x64__8wekyb3d8bbwe"
        "\\app\\resources\\codex.EXE"
    )

    @staticmethod
    def _environ_without_sessions(**extra: str) -> dict[str, str]:
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("CODEX_")
            and key not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")
        }
        environment.update(extra)
        return environment

    def _host_reports(self, platform, environment, which, run):
        import doctor  # noqa: PLC0415

        with mock.patch.dict(os.environ, environment, clear=True), \
                mock.patch.object(doctor.shutil, "which", side_effect=which), \
                mock.patch.object(doctor.subprocess, "run", side_effect=run):
            return doctor._host_reports(platform)

    def _which_codex_only(self, name):
        return self.WINDOWSAPPS_CODEX if name == "codex" else None

    def test_an_active_codex_session_accepts_an_unlaunchable_codex_cli(self) -> None:
        denied = PermissionError(13, "Access is denied")
        for platform in ("codex", "auto"):
            with self.subTest(platform=platform):
                reports, failures, warnings = self._host_reports(
                    platform,
                    self._environ_without_sessions(CODEX_HOME="1"),
                    self._which_codex_only,
                    denied,
                )
                self.assertEqual(failures, [])
                codex = reports["codex"]
                self.assertTrue(codex["required"])
                self.assertTrue(codex["ready"])
                self.assertEqual(codex["verified_by"], "active_session")
                self.assertIsNone(codex["version"])
                self.assertIn("Access is denied", codex["version_output"])
                self.assertTrue(
                    any(
                        "not blocking" in warning and "Access is denied" in warning
                        for warning in warnings
                    ),
                    warnings,
                )

    def test_an_active_codex_session_accepts_a_codex_cli_missing_from_path(self) -> None:
        def nothing_on_path(name):
            return None

        def no_probe(*arguments, **keywords):
            raise AssertionError("no command should be launched when nothing is on PATH")

        for platform in ("codex", "auto"):
            with self.subTest(platform=platform):
                reports, failures, warnings = self._host_reports(
                    platform,
                    self._environ_without_sessions(CODEX_HOME="1"),
                    nothing_on_path,
                    no_probe,
                )
                self.assertEqual(failures, [])
                codex = reports["codex"]
                self.assertTrue(codex["required"])
                self.assertFalse(codex["installed"])
                self.assertTrue(codex["ready"])
                self.assertEqual(codex["verified_by"], "active_session")
                self.assertTrue(
                    any("not on PATH" in warning for warning in warnings), warnings
                )

    def test_an_unlaunchable_codex_cli_still_fails_outside_a_session(self) -> None:
        reports, failures, warnings = self._host_reports(
            "codex",
            self._environ_without_sessions(),
            self._which_codex_only,
            PermissionError(13, "Access is denied"),
        )
        self.assertFalse(reports["codex"]["ready"])
        self.assertIsNone(reports["codex"]["verified_by"])
        self.assertEqual(warnings, [])
        self.assertTrue(
            any(
                "could not verify a usable Codex version with --version" in failure
                and "Access is denied" in failure
                for failure in failures
            ),
            failures,
        )

    def test_a_launchable_codex_cli_is_still_verified_by_its_version(self) -> None:
        def version_probe(*arguments, **keywords):
            return subprocess.CompletedProcess(arguments, 0, stdout="codex-cli 1.2.3\n", stderr="")

        reports, failures, warnings = self._host_reports(
            "codex",
            self._environ_without_sessions(CODEX_HOME="1"),
            self._which_codex_only,
            version_probe,
        )
        self.assertEqual(failures, [])
        self.assertEqual(warnings, [])
        codex = reports["codex"]
        self.assertTrue(codex["ready"])
        self.assertEqual(codex["version"], "1.2.3")
        self.assertEqual(codex["verified_by"], "cli_version")

    def test_the_claude_minimum_version_is_never_waived_by_a_session(self) -> None:
        def which_claude_only(name):
            return "/usr/local/bin/claude" if name == "claude" else None

        def old_version_probe(*arguments, **keywords):
            return subprocess.CompletedProcess(arguments, 0, stdout="2.0.0 (Claude Code)\n", stderr="")

        reports, failures, warnings = self._host_reports(
            "claude",
            self._environ_without_sessions(CLAUDECODE="1"),
            which_claude_only,
            old_version_probe,
        )
        self.assertFalse(reports["claude"]["ready"])
        self.assertEqual(warnings, [])
        self.assertTrue(
            any(
                "older than ELARA's dynamic-workflow minimum 2.1.154" in failure
                for failure in failures
            ),
            failures,
        )

    def test_a_current_claude_cli_still_passes(self) -> None:
        def which_claude_only(name):
            return "/usr/local/bin/claude" if name == "claude" else None

        def current_version_probe(*arguments, **keywords):
            return subprocess.CompletedProcess(arguments, 0, stdout="2.1.154 (Claude Code)\n", stderr="")

        reports, failures, warnings = self._host_reports(
            "claude",
            self._environ_without_sessions(CLAUDECODE="1"),
            which_claude_only,
            current_version_probe,
        )
        self.assertEqual(failures, [])
        self.assertTrue(reports["claude"]["ready"])
        self.assertEqual(reports["claude"]["verified_by"], "cli_version")

    def test_the_full_report_passes_and_keeps_the_probe_diagnostic(self) -> None:
        import doctor  # noqa: PLC0415

        with mock.patch.dict(
            os.environ, self._environ_without_sessions(CODEX_HOME="1"), clear=True
        ), mock.patch.object(
            doctor.shutil, "which", side_effect=self._which_codex_only
        ), mock.patch.object(
            doctor.subprocess, "run", side_effect=PermissionError(13, "Access is denied")
        ):
            report = doctor.build_report(ROOT, platform="codex", smoke=False)
        self.assertTrue(report["ok"], report["failures"])
        self.assertTrue(report["warnings"], report)
        self.assertEqual(report["hosts"]["codex"]["verified_by"], "active_session")
        self.assertIn("Access is denied", report["hosts"]["codex"]["version_output"])


class PreregistrationTemplateTests(unittest.TestCase):
    def test_template_sections_carry_markers_and_stage_09_vocabulary(self) -> None:
        template = ROOT / "workflow" / "templates" / "preregistration_template.md"
        self.assertTrue(template.is_file())
        text = template.read_text(encoding="utf-8")
        sections = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
        self.assertGreaterEqual(len(sections), 15)
        for section in sections:
            title, _newline, body = section.partition("\n")
            self.assertIn("TODO-PREREG", body, f"section {title!r} has no TODO-PREREG marker")
        for term in ("seed", "minimum detectable", "multiplicity", "frozen_analysis"):
            self.assertIn(term, text)


if __name__ == "__main__":
    unittest.main()
