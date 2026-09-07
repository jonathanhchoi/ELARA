"""Execute the actual saved Claude workflows with deterministic asynchronous host fixtures."""
from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path

from kit_context import resolve_test_root

ROOT = resolve_test_root(Path(__file__).resolve().parents[1])


class SavedWorkflowSchedulerTests(unittest.TestCase):
    def test_actual_saved_workflow_bodies(self) -> None:
        node = shutil.which("node")
        if node is None:
            self.assertFalse(os.environ.get("CI"), "CI requires Node.js for saved-workflow execution checks")
            self.skipTest("Node.js is required for saved-workflow execution checks")
        version = subprocess.check_output([node, "--version"], text=True, timeout=10).strip()
        print(f"Saved-workflow JavaScript runtime: Node.js {version}")
        result = subprocess.run(
            [node, str(ROOT / "tests/workflow_scheduler.mjs"), str(ROOT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("saved-workflow execution checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
