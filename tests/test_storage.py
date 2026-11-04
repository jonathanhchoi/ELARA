"""Exercise byte integrity and recovery, without requiring a sync service."""

from __future__ import annotations

import json
import argparse
import zipfile
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])
sys.path.insert(0, str(ROOT / "scripts"))
import storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "My Drive/study"
        self.local = self.base / "local/study"
        self.home.mkdir(parents=True)
        for path in ("AGENTS.md", "scripts/doctor.py", "project/PROJECT_STATE.md"):
            target = self.local / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture", encoding="utf-8")
        (self.local / "workflow/stages").mkdir(parents=True)
        self.binding = storage.bind(self.home, self.local)

    def make_snapshot(self):
        for name, data in (("result.csv", "value\n42\n"), ("audit.json", '{"verified":true}')):
            path = self.local / "project" / name
            path.write_bytes(data.encode("utf-8"))
        return storage.snapshot(self.home, {"deliverables": ["project/result.csv", "project/audit.json"],
                                          "omissions": ["No live database selected"]}, "stage complete")

    def test_same_workspace_from_either_root_and_read_only_status(self):
        before = sorted(str(p) for p in self.base.rglob("*"))
        self.assertEqual(storage.status(self.home), storage.status(self.local))
        self.assertEqual(before, sorted(str(p) for p in self.base.rglob("*")))
        self.assertEqual(storage.bind(self.home, self.local), self.binding)

    def test_missing_local_copy_never_reinitializes(self):
        shutil.rmtree(self.local)
        with self.assertRaisesRegex(ValueError, "without reinitializing"):
            storage.status(self.home)
        self.assertFalse(self.local.exists())

    def test_originals_and_existing_imports_are_preserved(self):
        source = self.home / "original.txt"
        source.write_bytes(b"original")
        imported = storage.stage(self.home, source, "project/inputs/source_v001.txt")
        self.assertEqual(Path(imported["destination"]).read_bytes(), b"original")
        source.write_bytes(b"changed original")
        with self.assertRaisesRegex(ValueError, "differs"):
            storage.stage(self.home, source, "project/inputs/source_v001.txt")
        self.assertEqual(Path(imported["destination"]).read_bytes(), b"original")
        self.assertEqual(source.read_bytes(), b"changed original")

    def test_completed_snapshot_reopens_with_verified_files_and_marker(self):
        snap = self.make_snapshot()
        receipt = storage.publish(self.home, snap["snapshot_id"])
        self.assertEqual(receipt["status"], "copied_to_sync_folder")
        self.assertFalse(receipt["upload_confirmed"])
        destination = Path(receipt["destination"])
        manifest = storage.read_json(destination / "manifest.json")
        self.assertEqual(manifest["omissions"], ["No live database selected"])
        for row in manifest["deliverables"]:
            self.assertEqual(storage.digest(destination / "deliverables" / row["path"]), row["sha256"])
        self.assertTrue((destination / "COMPLETE.json").is_file())
        self.assertEqual(storage.retry(self.home), [])
        self.assertEqual(storage.publish(self.home, snap["snapshot_id"])["status"], "copied_to_sync_folder")

    def test_partial_export_retries_without_rerunning_or_recapturing_research(self):
        snap = self.make_snapshot()
        copier = storage.copy_verified
        calls = 0

        def interrupt(source, destination, expected=None):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Drive temporarily unavailable")
            return copier(source, destination, expected)

        with mock.patch.object(storage, "copy_verified", side_effect=interrupt):
            receipt = storage.publish(self.home, snap["snapshot_id"])
        self.assertEqual(receipt["status"], "pending")
        destination = self.home / storage.EXPORTS / snap["snapshot_id"]
        self.assertFalse((destination / "COMPLETE.json").exists())
        (self.local / "project/result.csv").write_bytes(b"later work")
        self.assertEqual(storage.retry(self.local)[0]["status"], "copied_to_sync_folder")
        self.assertEqual((destination / "deliverables/project/result.csv").read_bytes(), b"value\n42\n")

    def test_offline_home_keeps_local_checkpoint_and_does_not_recreate_mount(self):
        snap = self.make_snapshot()
        held = self.base / "disconnected"
        self.home.rename(held)
        receipt = storage.publish(self.local, snap["snapshot_id"])
        self.assertEqual(receipt["status"], "pending")
        self.assertFalse(self.home.exists())
        held.rename(self.home)
        self.assertEqual(storage.retry(self.local)[0]["status"], "copied_to_sync_folder")

    def test_destination_conflict_is_preserved_and_agent_can_select_new_export_name(self):
        snap = self.make_snapshot()
        conflict = self.home / storage.EXPORTS / snap["snapshot_id"] / "deliverables/project/result.csv"
        conflict.parent.mkdir(parents=True)
        conflict.write_bytes(b"someone else's edit")
        self.assertEqual(storage.publish(self.home, snap["snapshot_id"])["status"], "pending")
        receipt = storage.publish(self.home, snap["snapshot_id"], snap["snapshot_id"] + "-retry")
        self.assertEqual(receipt["status"], "copied_to_sync_folder")
        self.assertEqual(conflict.read_bytes(), b"someone else's edit")

    def test_corrupt_local_snapshot_cannot_get_completion_marker(self):
        snap = self.make_snapshot()
        (Path(snap["snapshot"]) / "deliverables/project/result.csv").write_bytes(b"corrupt")
        self.assertEqual(storage.publish(self.home, snap["snapshot_id"])["status"], "pending")
        self.assertFalse((self.home / storage.EXPORTS / snap["snapshot_id"] / "COMPLETE.json").exists())

    def test_low_space_preserves_source_and_existing_project(self):
        source = self.home / "source.txt"
        source.write_bytes(b"original")
        with mock.patch.object(storage.shutil, "disk_usage", return_value=mock.Mock(free=0)):
            with self.assertRaisesRegex(OSError, "space"):
                storage.stage(self.home, source, "project/inputs/source.txt")
        self.assertEqual(source.read_bytes(), b"original")
        self.assertFalse((self.local / "project/inputs/source.txt").exists())

    def test_input_changed_during_copy_is_not_published(self):
        source = self.home / "source.txt"
        source.write_bytes(b"before")
        original_copy = storage.shutil.copyfileobj

        def change_source(incoming, outgoing, length):
            original_copy(incoming, outgoing, length)
            source.write_bytes(b"after!")

        with mock.patch.object(storage.shutil, "copyfileobj", side_effect=change_source):
            with self.assertRaisesRegex(ValueError, "Source changed"):
                storage.stage(self.home, source, "project/inputs/source.txt")
        self.assertFalse((self.local / "project/inputs/source.txt").exists())
        self.assertEqual(list((self.local / "project/inputs").iterdir()), [])

    def test_no_path_escape_or_recursive_storage_snapshot(self):
        for path in ("../escape", str(self.home / "absolute"), "project/ELARA_STORAGE.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                storage.snapshot(self.home, {"deliverables": [path]}, "bad")
        snap = self.make_snapshot()
        relative = (Path(snap["snapshot"]) / "manifest.json").relative_to(self.local).as_posix()
        with self.assertRaises(ValueError):
            storage.snapshot(self.local, {"deliverables": [relative]}, "recursive")
        with self.assertRaises(ValueError):
            storage.snapshot(self.local, {"archives": ["project/storage"]}, "recursive")
        with self.assertRaises(ValueError):
            storage.publish(self.local, "../escape")

    def test_link_to_outside_cannot_be_a_destination(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.local / "project/inputs"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Creating symlinks is unavailable")
        with self.assertRaises(ValueError):
            storage.stage(self.home, self.local / "AGENTS.md", "project/inputs/escape.txt")
        self.assertEqual(list(outside.iterdir()), [])

    def test_closed_runs_are_never_modified_by_export_receipts(self):
        closed = self.local / "project/runs/closed"
        closed.mkdir(parents=True)
        record = closed / "run_manifest.json"
        record.write_bytes(b'{"status":"complete"}')
        snap = storage.snapshot(self.local, {"archives": ["project/runs/closed"]}, "closed")
        before = {p.relative_to(closed): p.read_bytes() for p in closed.rglob("*") if p.is_file()}
        storage.publish(self.home, snap["snapshot_id"])
        self.assertEqual(before, {p.relative_to(closed): p.read_bytes() for p in closed.rglob("*") if p.is_file()})


class CloudInstallTests(unittest.TestCase):
    def test_download_provenance_reaches_local_installation(self):
        import bootstrap
        import check_update

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            home = base / "My Drive/Google Drive Study"
            commit = "a" * 40
            source_info = {"kind": "download", "location": "immutable-test-archive",
                           "commit": commit, "verified_commit": commit}
            args = argparse.Namespace(into=str(home), source=str(ROOT), update=False,
                                      dry_run=False, no_install=True, skip_doctor=True,
                                      keep=True, platform="none", model_evidence=None)
            with mock.patch.object(bootstrap, "resolve_source", return_value=(ROOT, source_info)), \
                 mock.patch.dict(os.environ, {"ELARA_WORKSPACE_HOME": str(base / "local")}):
                result = bootstrap.bootstrap(args)
            self.assertTrue(result["ok"], result)
            local = Path(result["storage"]["working_root"])
            manifest, problems = check_update.installation_evidence(local)
            self.assertEqual(problems, [])
            self.assertEqual(manifest["installed_commit"], commit)
            self.assertEqual(manifest["source"], source_info)
            with mock.patch.object(bootstrap, "github_commit", return_value={
                "commit": commit, "subject": "fixture", "url": "https://example.invalid/fixture"
            }):
                check = check_update.check(home, "00-initialize")
            self.assertTrue(check["ready"], check)
            self.assertEqual(check["working_root"], str(local))

    def test_installer_creates_companion_and_resume_uses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            home = base / "My Drive/study"
            home.mkdir(parents=True)
            original = home / "notes.txt"
            original.write_bytes(b"researcher original")
            env = {**os.environ, "ELARA_WORKSPACE_HOME": str(base / "workspaces")}
            command = [sys.executable, str(ROOT / "scripts/bootstrap.py"), "--into", str(home),
                       "--source", str(ROOT), "--no-install", "--skip-doctor", "--json"]
            preview = subprocess.run(command + ["--dry-run"], env=env, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(preview.stdout)["storage"]["status"], "planned")
            self.assertEqual(list(home.iterdir()), [original])
            self.assertFalse((base / "workspaces").exists())
            installed = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            record = json.loads(installed.stdout)
            self.assertEqual(record["storage"]["status"], "managed")
            working = Path(record["storage"]["working_root"])
            self.assertFalse((working / "notes.txt").exists())
            self.assertEqual(original.read_bytes(), b"researcher original")
            self.assertFalse(any("synchronization" in warning for warning in record["warnings"]))
            state = working / "project/PROJECT_STATE.md"
            state.write_text(state.read_text(encoding="utf-8").replace("project_slug: null", 'project_slug: "active-study"'), encoding="utf-8")
            again = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
            self.assertEqual(json.loads(again.stdout)["storage"]["working_root"], str(working))
            self.assertIn('project_slug: "active-study"', state.read_text(encoding="utf-8"))
            original_state = state.read_bytes()
            storage.stage(home, original, "project/inputs/notes_v001.txt")
            exported = storage.export(home, "00-initialize")
            self.assertEqual(exported["status"], "copied_to_sync_folder", exported)
            manifest = storage.read_json(Path(exported["destination"]) / "manifest.json")
            self.assertIn("project/PROJECT_STATE.md", [row["path"] for row in manifest["deliverables"]])
            self.assertNotIn("project/inputs/notes_v001.txt", [row["path"] for row in manifest["deliverables"]])
            self.assertEqual(state.read_bytes(), original_state)
            self.assertEqual(storage.status(home)["working_root"], str(working))

    def test_existing_history_is_not_replaced_by_fresh_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "My Drive/study"
            shutil.copytree(ROOT / "project", home / "project")
            ledger = home / "project/RUN_LEDGER.md"
            with ledger.open("a", encoding="utf-8") as handle:
                handle.write("\nExisting run\n")
            before = ledger.read_bytes()
            with mock.patch.dict(os.environ, {"ELARA_WORKSPACE_HOME": str(Path(tmp) / "local")}):
                self.assertEqual(storage.setup(home, ROOT)["status"], "needs_transition")
            self.assertEqual(before, ledger.read_bytes())
            self.assertFalse((Path(tmp) / "local").exists())


class StageEndExportTests(unittest.TestCase):
    """2.19.0: the deliverables as files and each finished run as one zip, at the end of a stage."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.home, self.local = base / "My Drive/study", base / "local/study"
        self.home.mkdir(parents=True)
        for path in ("AGENTS.md", "scripts/doctor.py", "project/DECISIONS.md", "project/RUN_LEDGER.md"):
            target = self.local / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("record\n", encoding="utf-8")
        (self.local / "workflow/stages").mkdir(parents=True)
        self.write_state("complete", None)
        storage.bind(self.home, self.local)
        self.write("project/artifacts/report_v001.md", "report")
        self.write("project/artifacts/figures_v001/a.png", "a")
        for index in range(storage.FOLDER_AS_FILES_LIMIT + 1):
            self.write(f"project/artifacts/tables_v001/t{index:03}.csv", str(index))
        self.write("project/inputs/source_v001.txt", "copy of an original")
        for index in range(300):
            self.write(f"project/runs/R1_11-scale-up_r001/worker_returns/u{index:03}.json", "{}")
        self.write("project/runs/R1_11-scale-up_r001/close_receipt.json", '{"reconciles": true}')
        self.write("project/runs/R1_11-scale-up_r001/__pycache__/x.pyc", "disposable")

    def write(self, relative, text):
        path = self.local / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_state(self, status, last_run_id):
        active = json.dumps({"report": "project/artifacts/report_v001.md",
                             "figures": {"path": "project/artifacts/figures_v001"},
                             "tables": "project/artifacts/tables_v001", "source": "project/inputs/source_v001.txt",
                             "gone": "project/artifacts/missing_v001.md"})
        run = "null" if last_run_id is None else '"' + last_run_id + '"'
        self.write("project/PROJECT_STATE.md", f"""---
schema_version: "1.5"
current_stage: "12-interpretive-audit"
status: "{status}"
active_artifacts: {active}
last_run_id: {run}
---

# Project state
""")

    def test_export_sends_deliverables_as_files_and_each_run_as_one_verified_zip(self):
        result = storage.export(self.home, "11-scale-up")
        self.assertEqual(result["status"], "copied_to_sync_folder", result)
        destination = Path(result["destination"])
        self.assertIn("11-scale-up", destination.name)
        manifest = storage.read_json(destination / "manifest.json")
        loose = [row["path"] for row in manifest["deliverables"]]
        self.assertEqual(loose[:3], ["project/PROJECT_STATE.md", "project/DECISIONS.md", "project/RUN_LEDGER.md"])
        self.assertIn("project/artifacts/report_v001.md", loose)
        self.assertIn("project/artifacts/figures_v001/a.png", loose)
        self.assertEqual([row["path"] for row in manifest["archives"]],
                         ["project/artifacts/tables_v001", "project/runs/R1_11-scale-up_r001"])
        reasons = {row["path"]: row["reason"] for row in manifest["omissions"]}
        self.assertIn("original stays", reasons["project/inputs/source_v001.txt"])
        self.assertEqual(reasons["project/artifacts/missing_v001.md"], "active output not found")
        sent = sorted(p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file())
        self.assertLess(len(sent), 20)
        run = manifest["archives"][1]
        self.assertEqual(run["file_count"], 301)
        with zipfile.ZipFile(destination / run["archive"]) as archive:
            names = archive.namelist()
            self.assertIn("R1_11-scale-up_r001/close_receipt.json", names)
            self.assertFalse(any("__pycache__" in name for name in names))
            for row in run["members"]:
                member = archive.read(row["path"].split("project/runs/", 1)[1])
                self.assertEqual(storage.hashlib.sha256(member).hexdigest(), row["sha256"])
        self.assertEqual(storage.digest(destination / run["archive"]), run["sha256"])

    def test_unchanged_runs_are_not_sent_again_and_a_changed_run_is(self):
        storage.export(self.home, "11-scale-up")
        again = storage.default_selection(self.home)
        self.assertEqual(again["archives"], ["project/artifacts/tables_v001"])
        self.write("project/runs/R1_11-scale-up_r001/late.json", "{}")
        self.write("project/runs/R2_12-interpretive-audit_r001/checks/check_001.json", "{}")
        self.assertEqual(storage.default_selection(self.home)["archives"],
                         ["project/artifacts/tables_v001", "project/runs/R1_11-scale-up_r001",
                          "project/runs/R2_12-interpretive-audit_r001"])

    def test_an_active_run_folder_is_archived_once(self):
        state = self.local / "project/PROJECT_STATE.md"
        text = state.read_text(encoding="utf-8")
        state.write_text(text.replace('{"report"', '{"run": "project/runs/R1_11-scale-up_r001", "report"'),
                         encoding="utf-8")
        selection = storage.default_selection(self.home)
        self.assertEqual(selection["archives"].count("project/runs/R1_11-scale-up_r001"), 1)
        self.assertEqual(storage.export(self.home, "11-scale-up")["status"], "copied_to_sync_folder")

    def test_a_run_still_in_progress_waits_for_its_own_end(self):
        self.write_state("running", "R1_11-scale-up_r001")
        selection = storage.default_selection(self.home)
        self.assertNotIn("project/runs/R1_11-scale-up_r001", selection["archives"])
        self.assertIn("run still in progress", selection["omissions"][-1]["reason"])

    def test_earlier_loose_exports_still_retry_and_count_as_sent(self):
        working = self.local
        identity = "20261020T120000.000000Z-old00000"
        directory = working / storage.OPERATIONS / "exports" / identity
        rows = []
        for path in sorted((working / "project/runs/R1_11-scale-up_r001").rglob("*")):
            relative = path.relative_to(working).as_posix()
            if path.is_file() and "__pycache__" not in relative:
                target = directory / "files" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
                rows.append({"path": relative, "size": path.stat().st_size, "sha256": storage.digest(path)})
        storage.write_new(directory / "manifest.json", {
            "schema_version": "1.0", "snapshot_id": identity, "project_id": storage.status(self.home)["project_id"],
            "working_root": str(working), "label": "old checkpoint", "files": rows, "omissions": []})
        # Not yet copied, so the run still counts as unsent.
        self.assertIn("project/runs/R1_11-scale-up_r001", storage.default_selection(self.home)["archives"])
        [receipt] = storage.retry(self.home)
        self.assertEqual(receipt["status"], "copied_to_sync_folder", receipt)
        self.assertTrue((self.home / storage.EXPORTS / identity / "files/project/runs/R1_11-scale-up_r001/close_receipt.json").is_file())
        self.assertEqual(storage.default_selection(self.home)["archives"], ["project/artifacts/tables_v001"])

    def test_selections_name_deliverables_and_archives_and_cap_loose_files(self):
        with self.assertRaisesRegex(ValueError, "deliverables"):
            storage.snapshot(self.home, {"files": ["project/PROJECT_STATE.md"]}, "old format")
        many = [f"project/runs/R1_11-scale-up_r001/worker_returns/u{index:03}.json" for index in range(300)]
        with self.assertRaisesRegex(ValueError, "archives"):
            storage.snapshot(self.home, {"deliverables": many}, "too many")

    def test_a_local_project_needs_no_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp)
            (plain / "project").mkdir()
            self.assertEqual(storage.export(plain, "11-scale-up")["status"], "not_needed")

    def test_export_command_reports_the_copy(self):
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/storage.py"), "export",
                                    "--root", str(self.home), "--label", "11-scale-up"],
                                   capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual((result["status"], result["archives"]), ("copied_to_sync_folder", 2))


if __name__ == "__main__":
    unittest.main()
