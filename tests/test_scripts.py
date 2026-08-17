from __future__ import annotations

import codecs
import csv
import hashlib
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
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
        self.assertIn("offline one-unit fan-out smoke passed", result.stdout)


def run_installer(target: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the downloaded copy's installer from the researcher's folder, as the quick start does."""
    return subprocess.run(
        [sys.executable, str(target / ".elara-src" / "scripts" / "install.py"), *arguments],
        cwd=target,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )


def stage_download(target: Path) -> None:
    copy_kit(ROOT, target / ".elara-src")
    (target / ".elara-src" / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (target / ".elara-src" / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")


class InstallerTests(unittest.TestCase):
    def test_quick_start_install_into_folder_with_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "My Paper"
            (target / "data").mkdir(parents=True)
            (target / "draft.docx").write_bytes(b"draft bytes")
            (target / "data" / "cases.csv").write_text("id\n1\n", encoding="utf-8")
            (target / "notes.md").write_text("[a broken link](nowhere.md)\n```\n", encoding="utf-8")
            stage_download(target)
            result = run_installer(target, "--skip-install")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for relative in (
                "AGENTS.md",
                "CLAUDE.md",
                "START_HERE.md",
                "workflow/stages/00-initialize.md",
                "workflow/shared/tool-menu.md",
                ".claude/skills/elr/SKILL.md",
                ".agents/skills/elr/SKILL.md",
                "project/PROJECT_STATE.md",
                "scripts/doctor.py",
            ):
                self.assertTrue((target / relative).is_file(), relative)
            self.assertFalse((target / ".elara-src").exists(), "temporary download should be removed")
            self.assertFalse((target / ".github").exists(), "CI configuration is not part of a workspace")
            self.assertEqual((target / "draft.docx").read_bytes(), b"draft bytes")
            self.assertEqual((target / "data" / "cases.csv").read_text(encoding="utf-8"), "id\n1\n")
            self.assertIn("EXISTING", result.stdout)
            self.assertIn("draft.docx", result.stdout)
            self.assertIn("DOCTOR: PASS", result.stdout)
            self.assertIn("NEXT: read START_HERE.md", result.stdout)
            # The researcher's own notes.md is not a kit surface and cannot fail validation.
            self.assertEqual(validate_repository(target), [])
            self.assertEqual(validate_docs(target), [])

    def test_installer_reports_conflicts_then_overwrites_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            target.mkdir()
            (target / "AGENTS.md").write_text("# my agents\n", encoding="utf-8")
            (target / "README.md").write_text("# my readme\n", encoding="utf-8")
            stage_download(target)
            result = run_installer(target, "--skip-install", "--skip-doctor", "--keep-source")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("CONFLICT", result.stdout)
            self.assertIn("AGENTS.md  (needed by ELARA)", result.stdout)
            self.assertIn("README.md", result.stdout)
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "# my agents\n")
            self.assertTrue((target / "workflow" / "stages" / "00-initialize.md").is_file())
            self.assertTrue((target / ".elara-src").is_dir())

            result = run_installer(target, "--skip-install", "--skip-doctor", "--overwrite")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("REPLACED", result.stdout)
            self.assertEqual(
                (target / "AGENTS.md").read_text(encoding="utf-8"),
                (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            )
            backups = list((target / ".elara-backup").rglob("AGENTS.md"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), "# my agents\n")
            self.assertFalse((target / ".elara-src").exists())
            self.assertEqual(validate_repository(target), [])

    def test_installer_never_replaces_an_initialized_project_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            copy_kit(ROOT, target)
            state = target / "project" / "PROJECT_STATE.md"
            initialized = state.read_text(encoding="utf-8").replace(
                "project_slug: null", 'project_slug: "live-project"'
            ).replace('current_stage: "00-initialize"', 'current_stage: "05-codebook-and-schema"')
            state.write_text(initialized, encoding="utf-8")
            (target / "project" / "DECISIONS.md").write_text("# decisions\n\n- kept\n", encoding="utf-8")
            (target / "workflow" / "shared" / "guardrails.md").write_text("tampered\n", encoding="utf-8")
            stage_download(target)
            result = run_installer(target, "--skip-install", "--skip-doctor", "--overwrite")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("KEPT", result.stdout)
            self.assertEqual(state.read_text(encoding="utf-8"), initialized)
            self.assertEqual(
                (target / "project" / "DECISIONS.md").read_text(encoding="utf-8"), "# decisions\n\n- kept\n"
            )
            self.assertEqual(
                (target / "workflow" / "shared" / "guardrails.md").read_text(encoding="utf-8"),
                (ROOT / "workflow" / "shared" / "guardrails.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(validate_state(target), [])

            stage_download(target)
            result = run_installer(target, "--skip-install", "--skip-doctor")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("copied 0 file(s)", result.stdout)
            self.assertNotIn("CONFLICT", result.stdout.replace("CONFLICT, PIP, or DOCTOR", ""))

    def test_installer_refuses_a_target_inside_the_download(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper"
            target.mkdir()
            stage_download(target)
            result = run_installer(target, "--target", str(target / ".elara-src" / "inside"))
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("must not be inside", result.stdout)


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
