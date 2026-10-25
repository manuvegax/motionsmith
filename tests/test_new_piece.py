"""new_piece.py and templates/starter: a scaffold that validates, is deterministic and keeps the brand red exact."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
KEEP = os.environ.get("MOTION_KEEP_TEST_EVIDENCE") == "1"


def run_py(script, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


class NewPiece(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-new-piece-"))
        cls.piece = cls.workspace / "pieza"
        result = run_py("new_piece.py", cls.piece, "--title", "El silencio de las cosas")   # wider than the frame at 200 px
        assert result.returncode == 0, result.stdout + result.stderr

    @classmethod
    def tearDownClass(cls):
        if not KEEP:
            shutil.rmtree(cls.workspace, ignore_errors=True)

    def test_scaffold_has_its_own_kit_and_a_valid_plan(self):
        for rel in ("index.html", "piece.js", "plan.json", "README.md", "kit/motion-math.js", "kit/postfx-glsl.js", "assets", "preview"):
            self.assertTrue((self.piece / rel).exists(), rel)
        self.assertEqual((self.piece / "kit" / "postfx-glsl.js").read_bytes(), (SCRIPTS / "kit" / "postfx-glsl.js").read_bytes())
        self.assertIn('const TITLE = "El silencio de las cosas";', (self.piece / "piece.js").read_text(encoding="utf-8"))
        report = json.loads(run_py("validate_plan.py", self.piece / "plan.json").stdout)
        self.assertEqual(report["errors"], [])

    def test_story_format_and_refusals(self):
        story = self.workspace / "historia"
        result = run_py("new_piece.py", story, "--format", "story")
        self.assertEqual(result.returncode, 0, result.stdout)
        plan = json.loads((story / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual((plan["format"], plan["duration_frames"], plan["safe_area"]["y"]), ("story", 360, 250))
        again = run_py("new_piece.py", self.piece)                       # not empty: never overwrite a piece
        self.assertEqual(again.returncode, 2)
        self.assertIn("not an empty folder", again.stdout)
        self.assertEqual(run_py("new_piece.py", self.workspace / "x", "--duration", "1").returncode, 2)   # template needs >= 3 s
        self.assertFalse((self.workspace / "x").exists())

    def test_every_format_scaffolds_a_valid_plan_inside_its_frame(self):
        sizes = {"reel": (1080, 1920), "story": (1080, 1920), "portrait": (1080, 1350), "square": (1080, 1080),
                 "landscape": (1920, 1080)}
        for fmt, (width, height) in sizes.items():
            with self.subTest(fmt=fmt):
                folder = self.workspace / f"format-{fmt}"
                result = run_py("new_piece.py", folder, "--format", fmt, "--fps", "30")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
                self.assertEqual((plan["width"], plan["height"]), (width, height))
                safe = plan["safe_area"]
                self.assertLessEqual(safe["x"] + safe["width"], width)
                self.assertLessEqual(safe["y"] + safe["height"], height)
                self.assertEqual(plan.get("format"), fmt if fmt in ("reel", "story") else None)
                report = json.loads(run_py("validate_plan.py", folder / "plan.json").stdout)
                self.assertEqual(report["errors"], [], fmt)

    @unittest.skipUnless(shutil.which("node"), "node drives the browser")
    def test_template_is_deterministic_and_keeps_the_brand_red_exact(self):
        probe = subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True, text=True)
        if probe.returncode != 0:
            self.skipTest("Playwright not available")
        det = subprocess.run(["node", str(SCRIPTS / "determinism_check.mjs"), "--root", str(self.piece), "--times", "2.4,0.6,1.1,2.4"],
                             capture_output=True, text=True, encoding="utf-8", timeout=240)
        self.assertEqual(det.returncode, 0, det.stdout[-1500:] + det.stderr)
        out = self.workspace / "frames"
        shot = subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(self.piece), "--out", str(out),
                               "--times", "0.62,2.03", "--png"], capture_output=True, text=True, encoding="utf-8", timeout=240)
        self.assertEqual(shot.returncode, 0, shot.stdout + shot.stderr)
        from PIL import Image
        with Image.open(out / "t2.030.png") as image:
            frame = image.convert("RGB")
            bar = frame.getpixel((540, 1317))
            self.assertTrue(all(abs(a - b) <= 2 for a, b in zip(bar, (255, 66, 46))), bar)   # composed after the tone map
            ring = frame.getpixel((540, 820 - 230))                                            # top of the ring: light
            self.assertGreater(ring[0], 200)
            self.assertLess(ring[1], 160)
            import numpy as np
            title = np.asarray(frame, float)[1100:1260]                                        # the long title fits the safe area
            ink = np.nonzero((title.min(axis=2) > 200).any(axis=0))[0]
            self.assertGreater(len(ink), 0)
            self.assertGreaterEqual(ink.min(), 80)
            self.assertLessEqual(ink.max(), 1080 - 140)
        sharp = self.workspace / "frames-noblur"   # mid-flight the ring moves fast: blur must change the frame
        shot = subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(self.piece), "--out", str(sharp),
                               "--times", "0.62", "--png", "--noblur"], capture_output=True, text=True, encoding="utf-8", timeout=240)
        self.assertEqual(shot.returncode, 0, shot.stdout + shot.stderr)
        import numpy as np
        with Image.open(out / "t0.620.png") as blurred, Image.open(sharp / "t0.620.png") as still:
            difference = np.abs(np.asarray(blurred.convert("L"), float) - np.asarray(still.convert("L"), float))
        self.assertGreater(float((difference > 5).mean()), .003)   # ~13 px of smear on the stroke (0.6 % of the frame measured)


if __name__ == "__main__":
    unittest.main()
