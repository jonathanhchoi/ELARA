"""Public synthetic fixtures for the shared Windows process transport."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
try:
    import tomllib
except ImportError:
    import tomli as tomllib
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/host_transport.py"
SPEC = importlib.util.spec_from_file_location("elara_host_transport", SCRIPT)
transport = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transport)


class HostTransportTests(unittest.TestCase):
    def test_literal_toml_roundtrip(self):
        self.assertEqual(tomllib.loads(transport.literal_toml_setting("reasoning", "high")), {"reasoning": "high"})

    def test_literal_rejects_injection(self):
        for value in ("x'y", "x\ny", "x\ry", "x\x00y"):
            with self.assertRaises(ValueError):
                transport.literal_toml_setting("reasoning", value)

    def test_backend_contract_explicit(self):
        flags = transport.backend_overrides()
        self.assertEqual(flags[::2], ["-c"] * 4)
        merged = [tomllib.loads(value) for value in flags[1::2]]
        self.assertEqual([row["features"]["multi_agent_v2"] for row in merged], [
            {"enabled": True}, {"tool_namespace": "collaboration"},
            {"expose_spawn_agent_model_overrides": True}, {"wait_agent_enabled": True}])

    def test_hook_quote_free_atoms(self):
        for value in ("two words", 'a"b', "a'b", "a&b", "a%b", "a!b", "a(b)"):
            with self.assertRaises(ValueError):
                transport.quote_free_atom(value)

    def test_shell_metacharacters_rejected(self):
        for value in ("%PATH%", "!VAR!", "a&b", "a|b", "a>b", "a^b", "a(b)", 'a"b'):
            with self.assertRaises(ValueError):
                transport.cmd_wrapper(["program.cmd", value])

    @unittest.skipUnless(os.name == "nt", "real Windows command transport")
    def test_actual_cmd_and_batch_forwarding_preserve_settings(self):
        # Fixture lives in the OS temp directory, not a researcher workspace.
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            receiver = folder / "receiver.py"
            receiver.write_text("import json,sys\ntry:\n import tomllib\nexcept ImportError:\n import tomli as tomllib\nprint(json.dumps([tomllib.loads(v) for v in sys.argv[1:]]))\n", encoding="utf-8")
            batch = folder / "fixture.cmd"
            batch.write_text('@echo off\n"' + sys.executable + '" -B "' + str(receiver) + '" %*\n', encoding="utf-8")
            setting = transport.literal_toml_setting("reasoning", "high")
            result = subprocess.run(transport.cmd_wrapper([str(batch), setting]), capture_output=True, check=False)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, b"")
            self.assertEqual(json.loads(result.stdout), [{"reasoning": "high"}])

    @unittest.skipUnless(os.name == "nt", "real Windows command transport")
    def test_actual_spaced_batch_and_arguments_preserved(self):
        with tempfile.TemporaryDirectory(prefix="elara transport ") as temporary:
            folder = Path(temporary)
            receiver = folder / "spaced receiver.py"
            receiver.write_text("import json,sys\nprint(json.dumps(sys.argv[1:]))\n", encoding="utf-8")
            batch = folder / "spaced fixture.cmd"
            batch.write_text('@echo off\n"' + sys.executable + '" -B "' + str(receiver) + '" %*\n', encoding="utf-8")
            values = [transport.literal_toml_setting("key", "two words"), str(folder / "spaced argument.txt"), "plain", str(folder) + "\\"]
            for target in ([str(batch)], [sys.executable, "-B", str(receiver)]):
                with self.subTest(target=Path(target[0]).suffix):
                    command = transport.cmd_wrapper([*target, *values])
                    self.assertIsInstance(command, str)
                    result = subprocess.run(command, capture_output=True, check=False)
                    self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
                    self.assertEqual(result.stderr, b"")
                    self.assertEqual(json.loads(result.stdout), values)


if __name__ == "__main__":
    unittest.main()
