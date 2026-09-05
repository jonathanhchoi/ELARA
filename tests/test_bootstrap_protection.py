import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import bootstrap


class UpdateProtectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.target = self.root / "source", self.root / "target"
        for root in (self.source, self.target):
            (root / "scripts").mkdir(parents=True)
            (root / "scripts/example.py").write_text("old")
        (self.target / "project").mkdir()
        self.path = self.target / "scripts/example.py"
        self.base = hashlib.sha256(b"old").hexdigest()
        self.manifest = {"kit_paths": ["scripts/example.py"], "baseline_hashes": {"scripts/example.py": self.base}}
        self.save()
        (self.source / "scripts/example.py").write_text("new")

    def save(self):
        (self.target / bootstrap.MANIFEST_RELATIVE).write_text(json.dumps(self.manifest))

    def update(self, dry=False):
        return bootstrap.install(self.source, self.target, True, already_installed=True, dry_run=dry)

    def test_clean_update_and_dry_run(self):
        self.assertEqual(self.update(True)["updated"], ["scripts/example.py"])
        self.assertEqual(self.path.read_text(), "old")
        self.update()
        self.assertEqual(self.path.read_text(), "new")

    def test_modified_file_is_preserved_and_baseline_not_relearned(self):
        self.path.write_text("researcher correction")
        result = self.update()
        self.assertEqual(result["update_conflicts"][0]["reason"], "locally_modified")
        self.assertEqual(result["baseline_hashes"]["scripts/example.py"], self.base)
        self.assertEqual(result["updated"], [])
        self.assertEqual(self.path.read_text(), "researcher correction")

    def test_active_run_binding_blocks_even_clean_upgrade(self):
        (self.target / "project/ELARA_PROTECTED_PATHS.json").write_text(json.dumps({"schema_version": "1.0", "bindings": {"scripts/example.py": self.base}}))
        self.assertEqual(self.update()["update_conflicts"][0]["reason"], "protected_active_run")
        self.assertEqual(self.path.read_text(), "old")

    def test_shared_file_local_edits_are_preserved_too(self):
        source = self.source / "requirements.txt"
        target = self.target / "requirements.txt"
        source.write_text("jsonschema\nnew-package\n")
        target.write_text("jsonschema\nresearcher-package\n")
        self.manifest["baseline_hashes"]["requirements.txt"] = hashlib.sha256(b"jsonschema\n").hexdigest()
        self.save()
        result = self.update()
        self.assertEqual(target.read_text(), "jsonschema\nresearcher-package\n")
        self.assertIn("requirements.txt", {r["path"] for r in result["update_conflicts"]})
        self.assertNotIn("requirements.txt (+1 line(s))", result["merged"])

    def test_missing_or_changed_protected_file_is_drift(self):
        self.manifest["protected_bindings"] = {"scripts/example.py": self.base}
        self.save()
        self.path.unlink()
        self.assertEqual(self.update()["update_conflicts"][0]["reason"], "protected_file_drift")
        self.assertFalse(self.path.exists())

    def test_legacy_unknown_baseline_is_not_overwritten(self):
        self.manifest.pop("baseline_hashes")
        self.save()
        self.assertEqual(self.update()["update_conflicts"][0]["reason"], "unknown_installation_baseline")

    def test_malformed_protection_and_path_escape_fail_closed(self):
        for bindings in ({"../outside": self.base}, {"scripts/example.py": "bad"}):
            (self.target / "project/ELARA_PROTECTED_PATHS.json").write_text(json.dumps({"schema_version": "1.0", "bindings": bindings}))
            with self.assertRaises(bootstrap.BootstrapError):
                self.update()
        self.assertEqual(self.path.read_text(), "old")

    def test_no_update_pass_does_not_launder_legacy_local_bytes(self):
        self.manifest.pop("baseline_hashes")
        self.save()
        self.path.write_text("local correction")
        result = bootstrap.install(self.source, self.target, False, already_installed=True)
        self.assertNotIn("scripts/example.py", result["baseline_hashes"])
        self.manifest["baseline_hashes"] = result["baseline_hashes"]
        self.save()
        self.assertEqual(self.update()["update_conflicts"][0]["reason"], "unknown_installation_baseline")
        self.assertEqual(self.path.read_text(), "local correction")

    def test_protected_drift_detected_even_when_identical_to_incoming(self):
        self.manifest["protected_bindings"] = {"scripts/example.py": self.base}
        self.save()
        self.path.write_text("new")
        self.assertEqual(self.update()["update_conflicts"][0]["reason"], "protected_file_drift")

    def test_removed_upstream_protected_path_is_still_checked(self):
        self.manifest["protected_bindings"] = {"scripts/absent.py": self.base}
        self.save()
        self.assertEqual(self.update()["update_conflicts"][0]["reason"], "protected_file_drift")


if __name__ == "__main__":
    unittest.main()
