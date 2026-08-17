"""Tests for scripts/bootstrap.py: installing the kit into a researcher's folder."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_workflow import validate_repository  # noqa: E402


def run_bootstrap(*arguments: str, cwd: Path, script: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script or (SCRIPTS / "bootstrap.py")), *arguments],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )


def install(target: Path, *extra: str, script: Path | None = None, cwd: Path | None = None) -> dict:
    if cwd is None:
        cwd = target if target.is_dir() else target.parent
        cwd.mkdir(parents=True, exist_ok=True)
    completed = run_bootstrap(
        "--into", str(target), "--source", str(ROOT), "--no-install", "--json", *extra,
        cwd=cwd,
        script=script,
    )
    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - diagnostic aid
        raise AssertionError(
            "bootstrap did not print JSON\nstdout:\n" + completed.stdout + "\nstderr:\n" + completed.stderr
        ) from exc
    summary["_returncode"] = completed.returncode
    summary["_stderr"] = completed.stderr
    return summary


class FreshInstallTests(unittest.TestCase):
    def test_installs_into_empty_folder_and_passes_the_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            target.mkdir()
            summary = install(target)
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["_returncode"], 0, summary["_stderr"])
            self.assertEqual(summary["existing_materials"], [])
            self.assertEqual(summary["kept"], [])
            self.assertEqual(summary["merged"], [])
            self.assertGreater(summary["files"]["installed"], 100)
            for relative in (
                "AGENTS.md",
                "CLAUDE.md",
                "PIPELINE.md",
                "ELARA_README.md",
                "LICENSE.ELARA",
                "requirements.txt",
                ".gitignore",
                "scripts/bootstrap.py",
                "scripts/doctor.py",
                "workflow/stages/00-initialize.md",
                ".agents/skills/elr/SKILL.md",
                ".claude/skills/elr/SKILL.md",
                "project/PROJECT_STATE.md",
                "project/BOOTSTRAP.md",
                "project/ELARA_MANIFEST.json",
                "tests/fixtures/one_unit_fanout/spec.json",
            ):
                self.assertTrue((target / relative).is_file(), relative)
            # README.md and LICENSE in a project folder are the researcher's to use.
            self.assertFalse((target / "README.md").exists())
            self.assertFalse((target / "LICENSE").exists())
            manifest = json.loads((target / "project" / "ELARA_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertIn("ELARA_README.md", manifest["kit_paths"])
            self.assertIn("scripts/doctor.py", manifest["kit_paths"])
            self.assertIn("project/PROJECT_STATE.md", manifest["project_paths"])
            self.assertEqual(manifest["researcher_paths"], [])
            self.assertEqual(manifest["researcher_files_in_kit_folders"], {})
            self.assertEqual(summary["shared_folders"], [])
            self.assertEqual(summary["essential_conflicts"], [])
            # Maintainer-only surfaces never travel into a project folder.
            self.assertFalse((target / ".github").exists())
            self.assertTrue(summary["doctor"]["ok"], summary["doctor"])
            self.assertEqual(validate_repository(target), [])
            report = (target / "project" / "BOOTSTRAP.md").read_text(encoding="utf-8")
            self.assertIn("## Bootstrap run ", report)
            self.assertIn("Next steps for the assistant", report)
            self.assertIn("00-initialize.md", report)
            self.assertIn("whole pipeline or use specific tools", report)
            self.assertIn("```json", report)

    def test_second_run_changes_nothing_and_appends_a_report_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            target.mkdir()
            install(target)
            summary = install(target)
            self.assertTrue(summary["ok"], summary)
            self.assertTrue(summary["already_installed"])
            self.assertEqual(summary["files"]["installed"], 0)
            self.assertEqual(summary["files"]["updated"], 0)
            self.assertEqual(summary["merged"], [])
            report = (target / "project" / "BOOTSTRAP.md").read_text(encoding="utf-8")
            self.assertEqual(report.count("## Bootstrap run "), 2)
            self.assertEqual(report.count("# ELARA bootstrap report"), 1)

    def test_installs_from_a_github_style_zip_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "ELARA-main.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for path in ROOT.rglob("*"):
                    if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts:
                        bundle.write(path, Path("ELARA-main") / path.relative_to(ROOT))
            target = Path(tmp) / "nested" / "paper"
            completed = run_bootstrap(
                "--into", str(target), "--source", str(archive), "--no-install", "--json", cwd=Path(tmp)
            )
            summary = json.loads(completed.stdout)
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["source"]["kind"], "archive")
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertEqual(validate_repository(target), [])

    def test_running_inside_a_kit_copy_only_checks_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kit = Path(tmp) / "kit"
            install(kit)
            (kit / "project" / "BOOTSTRAP.md").unlink()
            completed = run_bootstrap("--no-install", "--json", cwd=kit, script=kit / "scripts" / "bootstrap.py")
            summary = json.loads(completed.stdout)
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["source"]["kind"], "local copy")
            self.assertEqual(summary["files"]["installed"], 0)
            self.assertGreater(summary["files"]["unchanged"], 100)
            self.assertTrue((kit / "project" / "BOOTSTRAP.md").is_file())


class ExistingFolderTests(unittest.TestCase):
    def _populate(self, target: Path) -> None:
        target.mkdir(parents=True)
        (target / "README.md").write_text("# My paper\n\n[broken](nope.md)\n```\nunbalanced\n", encoding="utf-8")
        (target / ".gitignore").write_text("*.aux\n*.log\n", encoding="utf-8")
        (target / "requirements.txt").write_text("pandas>=2\n", encoding="utf-8")
        (target / "CLAUDE.md").write_text("# Paper notes\nAlways cite Bluebook.\n", encoding="utf-8")
        (target / "AGENTS.md").write_text("Use British spelling.\n", encoding="utf-8")
        (target / "notes.md").write_text("```\nunbalanced fence in my own notes\n", encoding="utf-8")
        (target / "draft.docx").write_bytes(b"not really a docx")
        (target / "data").mkdir()
        (target / "data" / "cases.csv").write_text("id,outcome\n1,affirmed\n", encoding="utf-8")
        (target / ".claude" / "skills" / "my-own-skill").mkdir(parents=True)
        (target / ".claude" / "skills" / "my-own-skill" / "SKILL.md").write_text(
            "---\nname: something-else\n---\nmine\n", encoding="utf-8"
        )

    def test_never_overwrites_and_reports_what_was_there(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            self._populate(target)
            before = {
                relative: (target / relative).read_bytes()
                for relative in ("README.md", "notes.md", "draft.docx", "data/cases.csv")
            }
            summary = install(target)
            self.assertTrue(summary["ok"], summary)
            for relative, content in before.items():
                self.assertEqual((target / relative).read_bytes(), content, relative)
            names = {record["name"] for record in summary["existing_materials"]}
            self.assertEqual(
                names,
                {"README.md", ".gitignore", "requirements.txt", "CLAUDE.md", "AGENTS.md", "notes.md", "draft.docx", "data", ".claude"},
            )
            data_record = next(record for record in summary["existing_materials"] if record["name"] == "data")
            self.assertEqual(data_record["kind"], "folder")
            self.assertEqual(data_record["files"], 1)
            # The kit README and LICENSE live under their kit names; the researcher's README stays put.
            self.assertTrue((target / "ELARA_README.md").is_file())
            self.assertTrue(any(item.startswith("README.md -> ELARA_README.md") for item in summary["kept"]))
            self.assertTrue((target / "LICENSE.ELARA").is_file())
            self.assertFalse((target / "LICENSE").exists())
            # .gitignore and requirements.txt gained the kit's lines in one marked block.
            gitignore = (target / ".gitignore").read_text(encoding="utf-8")
            self.assertTrue(gitignore.startswith("*.aux\n*.log\n"))
            self.assertIn("# >>> ELARA", gitignore)
            self.assertIn("project/runs/", gitignore)
            requirements = (target / "requirements.txt").read_text(encoding="utf-8")
            self.assertTrue(requirements.startswith("pandas>=2\n"))
            self.assertIn("jsonschema", requirements)
            # AGENTS.md and CLAUDE.md: kit block first, researcher's text after it.
            agents = (target / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(agents.startswith("<!-- elara:begin"))
            self.assertIn("# ELARA: Empirical Legal Analysis with Research Agents", agents)
            self.assertTrue(agents.rstrip().endswith("Use British spelling."))
            claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertTrue(claude.startswith("@AGENTS.md\n<!-- elara:begin"))
            self.assertIn("Claude Code adapter", claude)
            self.assertTrue(claude.rstrip().endswith("Always cite Bluebook."))
            # The researcher's own notes, README, and skills do not fail the kit's checks.
            self.assertTrue(summary["doctor"]["ok"], summary["doctor"])
            self.assertEqual(validate_repository(target), [])
            report = (target / "project" / "BOOTSTRAP.md").read_text(encoding="utf-8")
            self.assertIn("`draft.docx`", report)
            self.assertIn("`data/`", report)
            self.assertIn("adoption path", report)

    def test_rerun_is_idempotent_and_update_refreshes_only_kit_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            self._populate(target)
            install(target)
            first = {
                relative: (target / relative).read_bytes()
                for relative in ("AGENTS.md", "CLAUDE.md", ".gitignore", "requirements.txt", "README.md", "ELARA_README.md")
            }
            summary = install(target)
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["files"]["installed"], 0)
            self.assertEqual(summary["merged"], [])
            for relative, content in first.items():
                self.assertEqual((target / relative).read_bytes(), content, relative)
            # Simulate an older kit file and a locally edited stage; --update refreshes both,
            # never the project state, the researcher's files, or their text in merged files.
            (target / "PIPELINE.md").write_text("old kit map\n", encoding="utf-8")
            (target / "workflow" / "stages" / "18-cite-check.md").write_text("old\n", encoding="utf-8")
            state = target / "project" / "PROJECT_STATE.md"
            state_text = state.read_text(encoding="utf-8").replace("project_slug: null", 'project_slug: "mine"')
            state.write_text(state_text, encoding="utf-8")
            summary = install(target)  # without --update: kept, reported
            self.assertEqual(summary["files"]["updated"], 0)
            self.assertTrue(any(item.startswith("PIPELINE.md") for item in summary["kept"]))
            summary = install(target, "--update")
            self.assertGreaterEqual(summary["files"]["updated"], 2)
            self.assertEqual(
                (target / "PIPELINE.md").read_bytes(), (ROOT / "PIPELINE.md").read_bytes()
            )
            self.assertEqual(state.read_text(encoding="utf-8"), state_text)
            self.assertEqual((target / "README.md").read_bytes(), first["README.md"])
            claude = (target / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertEqual(claude.count("<!-- elara:begin"), 1)
            self.assertTrue(claude.rstrip().endswith("Always cite Bluebook."))

    def test_loose_downloaded_script_removes_itself_and_temporary_kit_is_not_material(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            target.mkdir()
            (target / "draft.docx").write_bytes(b"draft")
            loose = target / "bootstrap.py"
            shutil.copy2(SCRIPTS / "bootstrap.py", loose)
            kit_copy = target / ".elara-kit"
            shutil.copytree(ROOT, kit_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
            completed = run_bootstrap(
                "--into", str(target), "--source", str(kit_copy), "--no-install", "--json",
                cwd=target, script=loose,
            )
            summary = json.loads(completed.stdout)
            self.assertTrue(summary["ok"], summary)
            self.assertFalse(loose.exists())
            self.assertEqual(summary["removed_loose_script"], "bootstrap.py")
            self.assertEqual([record["name"] for record in summary["existing_materials"]], ["draft.docx"])
            report = (target / "project" / "BOOTSTRAP.md").read_text(encoding="utf-8")
            self.assertIn(".elara-kit", report)
            # The temporary .elara-kit copy is removed for the researcher; nothing else is.
            self.assertIn("has been removed", report)
            self.assertTrue(summary["temporary_source_removed"])
            self.assertFalse(kit_copy.exists())
            self.assertTrue((target / "draft.docx").exists())
            self.assertTrue((target / "AGENTS.md").exists())

    def test_temporary_kit_under_another_name_is_kept_and_keep_flag_preserves_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            target.mkdir()
            kit_copy = target / "ELARA"
            shutil.copytree(ROOT, kit_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
            summary = install(target, "--source", str(kit_copy))
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["temporary_source"], "ELARA")
            self.assertIsNone(summary["temporary_source_removed"])
            self.assertTrue(kit_copy.exists(), "a clone under a name of the researcher's choosing is left alone")
            report = (target / "project" / "BOOTSTRAP.md").read_text(encoding="utf-8")
            self.assertIn("delete that folder", report)

            other = Path(tmp) / "paper2"
            other.mkdir()
            kit_copy = other / ".elara-kit"
            shutil.copytree(ROOT, kit_copy, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
            summary = install(other, "--source", str(kit_copy), "--keep")
            self.assertTrue(summary["ok"], summary)
            self.assertIsNone(summary["temporary_source_removed"])
            self.assertTrue(kit_copy.exists())

    def test_manifest_names_kit_shared_and_researcher_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            (target / "scripts").mkdir(parents=True)
            (target / "scripts" / "analyze.py").write_text("print('mine')\n", encoding="utf-8")
            # The researcher's own file sits exactly where the kit keeps its doctor.
            (target / "scripts" / "doctor.py").write_text("# my own doctor\n", encoding="utf-8")
            (target / ".claude" / "skills" / "my-own-skill").mkdir(parents=True)
            (target / ".claude" / "skills" / "my-own-skill" / "SKILL.md").write_text(
                "---\nname: something-else\n---\nmine\n", encoding="utf-8"
            )
            (target / ".gitignore").write_text("*.aux\n", encoding="utf-8")
            summary = install(target)
            manifest_path = target / "project" / "ELARA_MANIFEST.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertIn("scripts/bootstrap.py", manifest["kit_paths"])
            self.assertIn("workflow/stages/00-initialize.md", manifest["kit_paths"])
            self.assertNotIn("scripts/doctor.py", manifest["kit_paths"])
            self.assertIn(".gitignore", manifest["shared_paths"])
            self.assertIn("project/PROJECT_STATE.md", manifest["project_paths"])
            self.assertEqual(manifest["researcher_paths"], ["scripts/doctor.py"])
            self.assertEqual(
                manifest["researcher_files_in_kit_folders"],
                {
                    ".claude": [".claude/skills/my-own-skill/SKILL.md"],
                    "scripts": ["scripts/analyze.py", "scripts/doctor.py"],
                },
            )
            # The researcher's file at a kit path is untouched and reported as theirs.
            self.assertEqual((target / "scripts" / "doctor.py").read_text(encoding="utf-8"), "# my own doctor\n")
            self.assertTrue(any(item.startswith("scripts/doctor.py (yours") for item in summary["kept"]))
            self.assertEqual(summary["researcher_paths"], ["scripts/doctor.py"])
            shared = {record["folder"]: record for record in summary["shared_folders"]}
            self.assertEqual(shared["scripts"]["yours"], ["scripts/analyze.py", "scripts/doctor.py"])
            self.assertEqual(shared[".claude"]["yours"], [".claude/skills/my-own-skill/SKILL.md"])
            self.assertGreater(shared["scripts"]["kit_files"], 5)
            # A researcher file where ELARA needs its own is a plainly reported conflict, and
            # the researcher's script is never run as if it were the kit's doctor.
            self.assertEqual(summary["essential_conflicts"], ["scripts/doctor.py"])
            self.assertFalse(summary["ok"])
            self.assertFalse(summary["doctor"]["ok"])
            self.assertTrue(any("your own file" in failure for failure in summary["doctor"]["failures"]))
            self.assertTrue(any("incomplete in this folder" in warning for warning in summary["warnings"]))
            report = (target / "project" / "BOOTSTRAP.md").read_text(encoding="utf-8")
            self.assertIn("### Folders you already had that the kit also uses", report)
            self.assertIn("`scripts/analyze.py`", report)
            self.assertIn("ELARA_MANIFEST.json", report)
            self.assertIn("ELARA is incomplete in this folder", report)
            # --update refreshes kit files but never the researcher's file at a kit path.
            (target / "PIPELINE.md").write_text("old\n", encoding="utf-8")
            summary = install(target, "--update")
            self.assertEqual((target / "scripts" / "doctor.py").read_text(encoding="utf-8"), "# my own doctor\n")
            self.assertEqual((target / "PIPELINE.md").read_bytes(), (ROOT / "PIPELINE.md").read_bytes())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["researcher_paths"], ["scripts/doctor.py"])
            self.assertEqual(summary["essential_conflicts"], ["scripts/doctor.py"])

    def test_kit_readme_installed_by_an_earlier_version_is_refreshed_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            target.mkdir()
            # An earlier kit version put its README at the plain name; simulate an older text.
            legacy = (ROOT / "README.md").read_text(encoding="utf-8").replace("## Start here", "## Getting started")
            (target / "README.md").write_text(legacy, encoding="utf-8")
            summary = install(target)
            self.assertTrue(summary["ok"], summary)
            self.assertFalse((target / "ELARA_README.md").exists(), "no second copy of the kit README")
            self.assertTrue(any(item.startswith("README.md (an earlier kit version") for item in summary["kept"]))
            self.assertEqual((target / "README.md").read_text(encoding="utf-8"), legacy)
            summary = install(target, "--update")
            self.assertEqual((target / "README.md").read_bytes(), (ROOT / "README.md").read_bytes())
            self.assertFalse((target / "ELARA_README.md").exists())
            manifest = json.loads((target / "project" / "ELARA_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertIn("README.md", manifest["kit_paths"])
            self.assertEqual(validate_repository(target), [])

    def test_dry_run_writes_nothing_and_shows_the_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            self._populate(target)
            before = sorted(str(path.relative_to(target)) for path in target.rglob("*"))
            summary = install(target, "--dry-run")
            self.assertTrue(summary["dry_run"])
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["_returncode"], 0, summary["_stderr"])
            self.assertGreater(summary["files"]["installed"], 100)
            self.assertTrue(summary["doctor"]["skipped"])
            self.assertIsNone(summary["report_path"])
            self.assertIsNone(summary["manifest_path"])
            # The plan names what a real run would keep, merge, and prepend ...
            self.assertTrue(any(item.startswith("README.md -> ELARA_README.md") for item in summary["kept"]))
            self.assertTrue(any(item.startswith(".gitignore") for item in summary["merged"]))
            self.assertTrue(any(item.startswith("AGENTS.md") for item in summary["merged"]))
            names = {record["name"] for record in summary["existing_materials"]}
            self.assertIn("draft.docx", names)
            # ... but nothing at all changed on disk.
            after = sorted(str(path.relative_to(target)) for path in target.rglob("*"))
            self.assertEqual(before, after)
            self.assertFalse((target / "project").exists())
            self.assertFalse((target / "ELARA_README.md").exists())
            self.assertEqual((target / ".gitignore").read_text(encoding="utf-8"), "*.aux\n*.log\n")
            # The human report says so and shows a folder-level plan.
            completed = run_bootstrap(
                "--into", str(target), "--source", str(ROOT), "--no-install", "--dry-run", cwd=target
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("DRY RUN", completed.stdout)
            self.assertIn("would install:", completed.stdout)
            self.assertIn("workflow/", completed.stdout)
            self.assertIn("run the same command again without --dry-run", completed.stdout)
            self.assertEqual(sorted(str(path.relative_to(target)) for path in target.rglob("*")), before)

    def test_doctor_runs_for_the_detected_host_or_none(self) -> None:
        import bootstrap

        claude = {"running_inside": ["Claude Code"], "on_path": {"Claude Code": "/usr/bin/claude", "Codex": None}}
        self.assertEqual(bootstrap.doctor_platform(claude), "claude")
        codex = {"running_inside": ["Codex"], "on_path": {"Claude Code": None, "Codex": "/usr/bin/codex"}}
        self.assertEqual(bootstrap.doctor_platform(codex), "codex")
        # Inside a host whose command is not on PATH, or outside any host: a maintenance check.
        self.assertEqual(bootstrap.doctor_platform({"running_inside": ["Claude Code"], "on_path": {}}), "none")
        self.assertEqual(bootstrap.doctor_platform({"running_inside": [], "on_path": {"Codex": "/usr/bin/codex"}}), "none")
        self.assertEqual(bootstrap.doctor_platform(claude, requested="none"), "none")
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            target.mkdir()
            summary = install(target, "--platform", "none")
            self.assertTrue(summary["ok"], summary)
            self.assertEqual(summary["doctor"]["platform"], "none")
            report = (target / "project" / "BOOTSTRAP.md").read_text(encoding="utf-8")
            self.assertIn("Agent host checked: none", report)

    def test_cloud_sync_detection_uses_path_components_and_the_onedrive_variables(self) -> None:
        import os
        from unittest import mock

        import bootstrap

        cleared = {name: "" for name in bootstrap.ONEDRIVE_VARIABLES}
        with mock.patch.dict(os.environ, cleared):
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                cases = {
                    base / "OneDrive - University" / "paper": "OneDrive",
                    base / "My Drive" / "Colab Notebooks" / "paper": "Google Drive",
                    base / "GoogleDrive-me@example.org" / "paper": "Google Drive",
                    base / "Dropbox (Personal)" / "paper": "Dropbox",
                    base / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "paper": "iCloud",
                    base / "Library" / "CloudStorage" / "Box-Box" / "paper": "a cloud storage service",
                    base / "projects" / "paper": None,
                    # A folder whose name merely contains the word is not a synced location.
                    base / "notes-about-onedrive-migration" / "paper": None,
                    base / "C--Users-me-OneDrive-Desktop-projects" / "paper": None,
                }
                for path, expected in cases.items():
                    self.assertEqual(bootstrap.cloud_sync_service(path), expected, str(path))
                    warning = bootstrap.cloud_sync_warning(path)
                    if expected is None:
                        self.assertIsNone(warning)
                    else:
                        self.assertIn(expected, warning)
                        self.assertIn("Stage 00 offers", warning)
                # Windows records where OneDrive lives; anything under it is synced whatever its name.
                onedrive = base / "cloud"
                onedrive.mkdir()
                with mock.patch.dict(os.environ, {"OneDrive": str(onedrive)}):
                    self.assertEqual(bootstrap.cloud_sync_service(onedrive / "paper"), "OneDrive")
                    self.assertIsNone(bootstrap.cloud_sync_service(base / "elsewhere" / "paper"))

    def test_folder_counts_past_the_cap_are_reported_as_more_than(self) -> None:
        import bootstrap

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / "data").mkdir()
            for index in range(5):
                (target / "data" / f"{index}.txt").write_text("x", encoding="utf-8")
            (target / "small").mkdir()
            (target / "small" / "one.txt").write_text("x", encoding="utf-8")
            original = bootstrap.FOLDER_COUNT_CAP
            bootstrap.FOLDER_COUNT_CAP = 3
            try:
                records = {record["name"]: record for record in bootstrap.snapshot_existing(target, set())}
            finally:
                bootstrap.FOLDER_COUNT_CAP = original
            self.assertEqual(records["data"]["files"], 3)
            self.assertTrue(records["data"]["files_truncated"])
            self.assertEqual(records["small"]["files"], 1)
            self.assertFalse(records["small"]["files_truncated"])

    def test_refuses_an_initialized_kit_copy_as_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "used"
            install(source)
            state = source / "project" / "PROJECT_STATE.md"
            state.write_text(
                state.read_text(encoding="utf-8").replace("project_slug: null", 'project_slug: "used"'),
                encoding="utf-8",
            )
            target = Path(tmp) / "fresh"
            completed = run_bootstrap(
                "--into", str(target), "--source", str(source), "--no-install", "--json", cwd=Path(tmp)
            )
            self.assertEqual(completed.returncode, 2, completed.stdout)
            self.assertIn("initialized project", json.loads(completed.stdout)["error"])
            self.assertFalse((target / "AGENTS.md").exists())


if __name__ == "__main__":
    unittest.main()
