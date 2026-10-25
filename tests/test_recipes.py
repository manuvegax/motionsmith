"""templates/recipes: every recipe scaffolds in every format, validates, renders without page errors and is deterministic."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
RECIPES = sorted(p.name for p in (SKILL / "templates" / "recipes").iterdir() if (p / "recipe.json").exists())
KEEP = os.environ.get("MOTION_KEEP_TEST_EVIDENCE") == "1"


def run_py(script, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def browser_available() -> bool:
    if not shutil.which("node"):
        return False
    probe = subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True, text=True)
    return probe.returncode == 0


class Recipes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-recipes-"))

    @classmethod
    def tearDownClass(cls):
        if not KEEP:
            shutil.rmtree(cls.workspace, ignore_errors=True)

    def test_there_are_six_recipes_with_complete_metadata(self):
        self.assertGreaterEqual(len(RECIPES), 6, RECIPES)
        listed = json.loads(run_py("new_piece.py", "--list-recipes").stdout)
        self.assertEqual(sorted(listed), RECIPES)
        for name in RECIPES:
            folder = SKILL / "templates" / "recipes" / name
            meta = json.loads((folder / "recipe.json").read_text(encoding="utf-8"))
            for key in ("what", "title", "mode", "default_seconds", "intent", "action", "hits"):
                self.assertIn(key, meta, f"{name}: {key}")
            self.assertIn("const TITLE = 'TITLE';", (folder / "piece.js").read_text(encoding="utf-8"), name)
            self.assertTrue((folder / "README.md").exists(), name)
            for hit in meta["hits"]:
                self.assertTrue(("time" in hit) != ("from_end" in hit), f"{name}: a hit has time or from_end")

    def test_every_recipe_validates_in_every_format_and_keeps_hits_inside(self):
        for name in RECIPES:
            for fmt in ("reel", "story", "portrait", "square", "landscape"):
                with self.subTest(recipe=name, fmt=fmt):
                    folder = self.workspace / f"{name}-{fmt}"
                    result = run_py("new_piece.py", folder, "--recipe", name, "--format", fmt, "--fps", "30")
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
                    duration = plan["duration_frames"] / plan["fps"]
                    self.assertTrue(all(0 <= h["time"] <= duration for h in plan["hits"]), plan["hits"])
                    self.assertTrue((folder / "kit" / "stage.js").exists())
                    report = json.loads(run_py("validate_plan.py", folder / "plan.json").stdout)
                    self.assertEqual(report["errors"], [])

    @unittest.skipUnless(shutil.which("node"), "node runs the headless check")
    def test_every_recipe_runs_headless_in_every_format_with_odd_titles(self):
        """No browser needed (so CI runs it): setup() and state(t) over the whole piece, a stable and finite track."""
        titles = ["x", "A title long enough to need three lines in a reel frame", "Café ñandú", "ab 🙂 cd", "one|two three", "e\u0301 *ok* now"]
        folders = []
        for name in RECIPES:
            for fmt in ("reel", "story", "portrait", "square", "landscape"):
                folder = self.workspace / f"headless-{name}-{fmt}"
                self.assertEqual(run_py("new_piece.py", folder, "--recipe", name, "--format", fmt, "--fps", "30").returncode, 0)
                folders.append(folder)
            for i, title in enumerate(titles):
                folder = self.workspace / f"headless-{name}-title{i}"
                self.assertEqual(run_py("new_piece.py", folder, "--recipe", name, "--format", "landscape", "--fps", "24", "--title", title).returncode, 0, title)
                folders.append(folder)
        starter = self.workspace / "headless-starter"
        self.assertEqual(run_py("new_piece.py", starter, "--format", "square").returncode, 0)
        folders.append(starter)
        result = subprocess.run(["node", str(SKILL / "tests" / "recipes_check.js"), *map(str, folders)],
                                capture_output=True, text=True, encoding="utf-8", timeout=600)
        reports = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(reports), len(folders), result.stderr[-1500:])
        failed = [(Path(r["piece"]).name, r["errors"][:2]) for r in reports if not r["ok"]]
        self.assertEqual(failed, [])

    @unittest.skipUnless(shutil.which("node"), "node runs the headless check")
    def test_the_quote_keyword_survives_markers_and_graphemes(self):
        cases = {"the mind | is *ready* for": "ready", "the mind|is *ready* for": "ready", "ab 🙂 *cd*": "cd",
                 "Cafe\u0301 *ok* now": "ok", "x 👍🏽 yz *w*": "w", "no markers here": "here"}
        folders = {}
        for i, (title, keyword) in enumerate(cases.items()):
            folder = self.workspace / f"quote-key-{i}"
            self.assertEqual(run_py("new_piece.py", folder, "--recipe", "kinetic-quote", "--format", "landscape", "--title", title).returncode, 0)
            folders[folder.name] = (title, keyword)
        result = subprocess.run(["node", str(SKILL / "tests" / "recipes_check.js"), *[str(self.workspace / f) for f in folders]],
                                capture_output=True, text=True, encoding="utf-8", timeout=300)
        for line in result.stdout.splitlines():
            report = json.loads(line)
            title, keyword = folders[Path(report["piece"]).name]
            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(report["debug"]["keyword"], keyword, title)
            drawn = "".join(report["debug"]["lines"]).replace(" ", "")
            expected = title.replace("*", "").replace("|", "").replace(" ", "")
            self.assertEqual(unicodedata.normalize("NFC", drawn), unicodedata.normalize("NFC", expected), title)   # no letter lost

    def test_exit_hits_move_with_the_duration(self):
        folder = self.workspace / "long-quote"
        self.assertEqual(run_py("new_piece.py", folder, "--recipe", "kinetic-quote", "--duration", "9").returncode, 0)
        hits = {h["role"]: h["time"] for h in json.loads((folder / "plan.json").read_text(encoding="utf-8"))["hits"]}
        self.assertAlmostEqual(hits["exit"], 9 - .62, places=3)
        self.assertAlmostEqual(hits["keyword lands"], 2.6, places=3)
        self.assertEqual(run_py("new_piece.py", self.workspace / "short", "--recipe", "kinetic-quote", "--duration", "3").returncode, 2)

    @unittest.skipUnless(browser_available(), "node + Playwright drive the browser")
    def test_every_recipe_is_deterministic_and_renders_wide(self):
        for name in RECIPES:
            with self.subTest(recipe=name):
                folder = self.workspace / f"det-{name}"
                self.assertEqual(run_py("new_piece.py", folder, "--recipe", name, "--fps", "30").returncode, 0)
                det = subprocess.run(["node", str(SCRIPTS / "determinism_check.mjs"), "--root", str(folder), "--times", "1.95,0.4,1.95"],
                                     capture_output=True, text=True, encoding="utf-8", timeout=300)
                self.assertEqual(det.returncode, 0, det.stdout[-1500:] + det.stderr[-800:])
                wide = self.workspace / f"wide-{name}"
                self.assertEqual(run_py("new_piece.py", wide, "--recipe", name, "--format", "landscape", "--fps", "30").returncode, 0)
                # 3.0 s comes after every main hit: the quote's echoes start at ~2.7 s.
                shot = subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(wide), "--out", str(wide / "preview"),
                                       "--times", "3.0", "--noblur"], capture_output=True, text=True, encoding="utf-8", timeout=300)
                self.assertEqual(shot.returncode, 0, shot.stdout[-1500:] + shot.stderr[-800:])
                self.assertEqual(json.loads(shot.stdout.strip().splitlines()[-1])["errors"], [])


if __name__ == "__main__":
    unittest.main()
