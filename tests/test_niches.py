"""Recipes for niches: their sample data travels with the piece and the GPU-free check runs them."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
DATA_RECIPES = {"chart-bars": "bars", "ranking": "items", "step-diagram": "steps"}


class NicheRecipeTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="motion-niches-"))

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_data_is_copied_and_linked(self):
        for recipe, key in DATA_RECIPES.items():
            with self.subTest(recipe=recipe):
                piece = self.workspace / recipe
                made = subprocess.run([sys.executable, "-I", str(SCRIPTS / "new_piece.py"), str(piece), "--recipe", recipe,
                                       "--format", "reel", "--fps", "30"], capture_output=True, text=True)
                self.assertEqual(made.returncode, 0, made.stdout)
                plan = json.loads((piece / "plan.json").read_text(encoding="utf-8"))
                self.assertEqual(plan["data"], "data.json")
                data = json.loads((piece / "data.json").read_text(encoding="utf-8"))
                self.assertTrue(data[key])

    @unittest.skipUnless(shutil.which("node"), "node runs the GPU-free check")
    def test_recipes_run_with_edited_data_shapes(self):
        piece = self.workspace / "diagram"
        subprocess.run([sys.executable, "-I", str(SCRIPTS / "new_piece.py"), str(piece), "--recipe", "step-diagram"], check=True,
                       capture_output=True)
        check = subprocess.run(["node", str(SKILL / "tests" / "recipes_check.js"), str(piece)], capture_output=True, text=True)
        result = json.loads(check.stdout.strip().splitlines()[-1])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["debug"]["steps"], 4)
        audiogram = self.workspace / "pod"
        subprocess.run([sys.executable, "-I", str(SCRIPTS / "new_piece.py"), str(audiogram), "--recipe", "audiogram",
                        "--title", "Ana | Show"], check=True, capture_output=True)
        check = subprocess.run(["node", str(SKILL / "tests" / "recipes_check.js"), str(audiogram)], capture_output=True, text=True)
        result = json.loads(check.stdout.strip().splitlines()[-1])
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["debug"]["voice"])   # the demo voice without voice.json


if __name__ == "__main__":
    unittest.main()
