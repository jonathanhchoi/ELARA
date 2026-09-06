"""Currency, provenance, and safe installation regressions; no live network."""

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bootstrap
import check_update


OLD = "a" * 40
NEW = "b" * 40
STAGE = "00-initialize"


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.target = self.root / "research"
        files = {
            "AGENTS.md": bootstrap.KIT_TITLE + "\nInstructions\n",
            "README.md": bootstrap.KIT_TITLE + "\nReadme\n",
            "workflow/stages/00-initialize.md": "# Initialize\n",
            "scripts/example.py": "original\n",
            "scripts/doctor.py": "# Synthetic doctor\n",
            "project/PROJECT_STATE.md": 'workflow_version: "2.7.0"\nproject_slug: null\n',
            "project/DECISIONS.md": "# Decisions\n",
        }
        for relative, contents in files.items():
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")

    def install(self, commit=OLD, update=False, strict=False, dry=False):
        args = argparse.Namespace(into=str(self.target), update=update, require_clean=strict,
                                  dry_run=dry, no_install=True, skip_doctor=True, keep=True,
                                  platform="none", model_evidence=None)
        info = {"kind": "download", "commit": commit, "verified_commit": commit,
                "location": "https://github.com/" + bootstrap.REPOSITORY, "ref": "main"}
        with patch.object(bootstrap, "resolve_source", return_value=(self.source, info)), \
                patch.object(bootstrap, "ensure_dependency", return_value={"status": "present"}):
            return bootstrap.bootstrap(args)

    def check(self, latest=OLD):
        with patch.object(bootstrap, "github_commit", return_value={
                "commit": latest, "subject": "Update", "url": "https://github.com/example"}):
            return check_update.check(self.target, STAGE)

    def test_current_is_read_only_and_research_state_is_not_installation_version(self):
        report = self.install()
        self.assertEqual(report["installed_commit"], OLD)
        state = self.target / "project/PROJECT_STATE.md"
        state.write_text('workflow_version: "old-research-version"\nproject_slug: project\n')
        before = snapshot(self.target)
        self.assertTrue(self.check()["ready"])
        self.assertEqual(snapshot(self.target), before)

    def test_new_commit_with_same_version_pauses_without_installing_or_recording_consent(self):
        self.install()
        before = snapshot(self.target)
        result = self.check(NEW)
        self.assertEqual(result["status"], "update_available")
        self.assertFalse(result["ready"])
        self.assertEqual(snapshot(self.target), before)
        self.assertEqual(self.check(NEW)["status"], "update_available")

    def test_network_failure_cannot_reuse_a_previous_success(self):
        self.install()
        self.assertTrue(self.check()["ready"])
        before = snapshot(self.target)
        with patch.object(bootstrap, "github_commit", side_effect=bootstrap.BootstrapError("GitHub unavailable")):
            result = check_update.check(self.target, STAGE)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(result["ready"])
        self.assertEqual(snapshot(self.target), before)

    def test_modified_missing_and_incomplete_inventory_never_pass(self):
        self.install()
        path = self.target / "scripts/example.py"
        original = path.read_bytes()
        path.write_text("local correction")
        self.assertEqual(self.check()["status"], "conflict")
        path.unlink()
        self.assertEqual(self.check()["status"], "conflict")
        path.write_bytes(original)
        manifest_path = self.target / bootstrap.MANIFEST_RELATIVE
        manifest = json.loads(manifest_path.read_text())
        manifest["installed_hashes"].pop("scripts/example.py")
        manifest_path.write_text(json.dumps(manifest))
        self.assertFalse(self.check()["ready"])

    def test_approved_exact_update_and_second_live_check(self):
        self.install()
        (self.source / "scripts/example.py").write_text("updated")
        before_state = (self.target / "project/PROJECT_STATE.md").read_bytes()
        self.assertTrue(self.install(NEW, update=True, strict=True)["ok"])
        self.assertTrue(self.check(NEW)["ready"])
        self.assertFalse((self.target / bootstrap.UPDATE_PENDING_RELATIVE).exists())
        self.assertEqual((self.target / "project/PROJECT_STATE.md").read_bytes(), before_state)
        self.assertEqual(self.check("c" * 40)["status"], "update_available")

    def test_strict_preflight_preserves_entire_tree_on_local_or_protected_conflict(self):
        self.install()
        (self.source / "AGENTS.md").write_text(bootstrap.KIT_TITLE + "\nNew instructions")
        (self.source / "scripts/example.py").write_text("new")
        original = (self.target / "scripts/example.py").read_bytes()
        for protected in (False, True):
            with self.subTest(protected=protected):
                (self.target / "scripts/example.py").write_bytes(original if protected else b"local")
                if protected:
                    (self.target / "project/ELARA_PROTECTED_PATHS.json").write_text(json.dumps({
                        "schema_version": "1.0", "bindings": {"scripts/example.py": hashlib.sha256(original).hexdigest()}}))
                before = snapshot(self.target)
                with self.assertRaises(bootstrap.BootstrapError):
                    self.install(NEW, update=True, strict=True)
                self.assertEqual(snapshot(self.target), before)

    def test_partial_legacy_update_does_not_claim_latest(self):
        self.install()
        (self.target / "scripts/example.py").write_text("local")
        (self.source / "scripts/example.py").write_text("new")
        result = self.install(NEW, update=True)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["installed_commit"])
        self.assertFalse(result["installation_complete"])
        self.assertTrue((self.target / bootstrap.UPDATE_PENDING_RELATIVE).exists())
        self.assertFalse(self.check(NEW)["ready"])

    def test_interrupted_update_leaves_marker_and_can_be_completed(self):
        self.install()
        (self.source / "scripts/example.py").write_text("new")
        real_install = bootstrap.install

        def interrupted(source, target, update, **kwargs):
            if not kwargs.get("dry_run"):
                (Path(target) / "scripts/example.py").write_text("new")
                raise OSError("simulated interrupted write")
            return real_install(source, target, update, **kwargs)

        with patch.object(bootstrap, "install", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.install(NEW, update=True, strict=True)
        self.assertTrue((self.target / bootstrap.UPDATE_PENDING_RELATIVE).exists())
        self.assertFalse(self.check(NEW)["ready"])
        self.assertTrue(self.install(NEW, update=True, strict=True)["ok"])
        self.assertTrue(self.check(NEW)["ready"])

    def test_removed_upstream_file_requires_review(self):
        self.install()
        (self.source / "scripts/example.py").unlink()
        before = snapshot(self.target)
        with self.assertRaises(bootstrap.BootstrapError):
            self.install(NEW, update=True, strict=True)
        self.assertEqual(snapshot(self.target), before)

    def test_repeated_partial_update_cannot_forget_a_removed_upstream_file(self):
        self.install()
        (self.source / "scripts/example.py").unlink()
        for _ in range(2):
            report = self.install(NEW, update=True)
            self.assertFalse(report["installation_complete"])
            self.assertIn("scripts/example.py", report["files"]["kit_paths"])
            self.assertFalse(self.check(NEW)["ready"])

    def test_zip_without_git_can_be_verified_without_writes(self):
        shutil.copytree(self.source, self.target)
        before = snapshot(self.target)
        with patch.object(bootstrap, "local_source_info", return_value={}), \
                patch.object(bootstrap, "download_kit", return_value=(self.source, {"verified_commit": OLD})):
            result = self.check()
        self.assertTrue(result["ready"], result)
        self.assertEqual(result["identity_basis"], "live content comparison")
        self.assertEqual(snapshot(self.target), before)

    def test_legacy_manifest_can_compare_to_latest_without_rewriting_identity(self):
        self.install()
        path = self.target / bootstrap.MANIFEST_RELATIVE
        manifest = json.loads(path.read_text())
        for field in ("installed_commit", "installation_complete", "installed_hashes"):
            manifest.pop(field)
        path.write_text(json.dumps(manifest))
        before = snapshot(self.target)
        with patch.object(bootstrap, "download_kit", return_value=(self.source, {"verified_commit": OLD})):
            self.assertTrue(self.check()["ready"])
        self.assertEqual(snapshot(self.target), before)
        (self.source / "scripts/example.py").write_text("new")
        with patch.object(bootstrap, "download_kit", return_value=(self.source, {"verified_commit": NEW})):
            self.assertEqual(self.check(NEW)["status"], "update_available")

    def test_malformed_or_escaping_manifest_fails_closed(self):
        self.install()
        path = self.target / bootstrap.MANIFEST_RELATIVE
        for record in ([], {"kit_paths": ["../outside"]}, {"kit_paths": [1]}, {"kit_paths": "bad"}):
            path.write_text(json.dumps(record))
            self.assertFalse(self.check()["ready"])

    def test_failed_setup_keeps_update_pending(self):
        self.install()
        (self.source / "scripts/example.py").write_text("new")
        with patch.object(bootstrap, "ensure_dependency", return_value={"status": "missing"}):
            # install() normally mocks a present dependency, so call with that
            # helper's source mock but explicit arguments instead.
            args = argparse.Namespace(into=str(self.target), update=True, require_clean=True,
                                      dry_run=False, no_install=True, skip_doctor=True, keep=True,
                                      platform="none", model_evidence=None)
            with patch.object(bootstrap, "resolve_source", return_value=(self.source, {
                    "kind": "download", "location": "test", "verified_commit": NEW})):
                report = bootstrap.bootstrap(args)
        self.assertFalse(report["ok"])
        self.assertTrue((self.target / bootstrap.UPDATE_PENDING_RELATIVE).exists())
        self.assertFalse(self.check(NEW)["ready"])


class SourceIdentityTests(unittest.TestCase):
    def test_resolve_and_download_use_the_same_full_commit(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("ELARA-main/AGENTS.md", bootstrap.KIT_TITLE)
            bundle.writestr("ELARA-main/workflow/stages/00-initialize.md", "# Init")
            bundle.writestr("ELARA-main/scripts/doctor.py", "# Doctor")
            bundle.writestr("ELARA-main/project/PROJECT_STATE.md", "project_slug: null")
        metadata = json.dumps({"sha": OLD, "commit": {"message": "First line\nDetails"}}).encode()
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(bootstrap, "urlopen", side_effect=[io.BytesIO(metadata), io.BytesIO(archive.getvalue())]) as fetch:
            root, info = bootstrap.download_kit("main", temp)
            self.assertTrue(root.is_dir())
            self.assertEqual(info["verified_commit"], OLD)
            self.assertIn("/archive/" + OLD + ".zip", fetch.call_args.args[0].full_url)

    def test_invalid_or_changed_exact_commit_response_fails(self):
        for record in ({"sha": "short"}, {"sha": NEW, "commit": {"message": "wrong"}}):
            with patch.object(bootstrap, "urlopen", return_value=io.BytesIO(json.dumps(record).encode())):
                with self.assertRaises(bootstrap.BootstrapError):
                    bootstrap.github_commit(OLD)

    @unittest.skipUnless(shutil.which("git"), "Git not installed")
    def test_only_clean_official_clone_supplies_local_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.run(["git", "-C", temp, *args], check=True, capture_output=True, text=True)
            git("init", "-q")
            git("remote", "add", "origin", "https://github.com/" + bootstrap.REPOSITORY + ".git")
            (root / "README.md").write_text("original")
            git("add", "README.md")
            git("-c", "user.name=ELARA Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture")
            identity = bootstrap.local_source_info(root)
            self.assertEqual(len(identity["verified_commit"]), 40)
            (root / "README.md").write_text("local edit")
            self.assertNotIn("verified_commit", bootstrap.local_source_info(root))
            (root / "README.md").write_text("original")
            git("remote", "set-url", "origin", "https://github.com/example/research.git")
            self.assertNotIn("verified_commit", bootstrap.local_source_info(root))


class RoutingTests(unittest.TestCase):
    def test_all_parent_entry_routes_include_the_update_contract(self):
        import sync_skill_wrappers as wrappers
        for claude in (False, True):
            texts = [wrappers.router_text(claude=claude),
                     wrappers.observation_skill_text(claude=claude),
                     wrappers.wrapper_text("elr-test", "test", "workflow/stages/test.md", claude=claude)]
            texts.extend(wrappers.utility_wrapper_text(name, spec, claude=claude)
                         for name, spec in wrappers.UTILITY_SKILLS.items())
            for text in texts:
                self.assertIn("workflow/shared/kit-updates.md", text)
                self.assertIn("scripts/check_update.py", text)
                self.assertIn("ready: true", text)
                self.assertIn("declined", text)


if __name__ == "__main__":
    unittest.main()
