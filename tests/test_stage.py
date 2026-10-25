"""Runs the Node checks of the pure parts of scripts/kit/stage.js inside the Python suite."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest

TESTS = Path(__file__).resolve().parent


@unittest.skipUnless(shutil.which("node"), "node is required for stage checks")
class Stage(unittest.TestCase):
    def test_checks_pass(self):
        result = subprocess.run(["node", str(TESTS / "stage_check.js")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"^ok \d+")
        self.assertGreater(int(result.stdout.split()[1]), 30)


if __name__ == "__main__":
    unittest.main()
