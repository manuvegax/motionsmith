"""The technique lab renders, stays deterministic and its curves measure what the guides say."""
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
PAGE = "templates/technique-lab/index.html"
KEEP = os.environ.get("MOTION_KEEP_TEST_EVIDENCE") == "1"


class Laboratorio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe = subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True, text=True)
        if probe.returncode != 0:
            raise unittest.SkipTest("Playwright not available")
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-lab-tests-"))

    @classmethod
    def tearDownClass(cls):
        if not KEEP:
            shutil.rmtree(cls.workspace, ignore_errors=True)

    def node(self, script, *args):
        return subprocess.run(["node", str(SCRIPTS / script), "--root", str(SKILL), "--page", PAGE, *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", timeout=300)

    def test_every_block_renders_without_page_errors(self):
        out = self.workspace / "frames"
        result = self.node("sample_frames.mjs", "--out", out, "--times", "1,4.3,9,14.4,17.2,23.2,29.6,34.6,38.6,43.6,46.4")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((out / "sample-report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["errors"], [])
        self.assertEqual(len(list(out.glob("t*.jpg"))), 11)

    def test_deterministic_after_visiting_other_blocks(self):
        result = self.node("determinism_check.mjs", "--times", "17.175,40,5,29.6,17.175")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["deterministic"])

    def test_block_a_curves_match_the_guide(self):
        dump = self.workspace / "lanes.json"
        result = self.node("dump_state.mjs", "--expr", "window.labState(t)", "--from", "2.5", "--to", "3.6", "--step", "0.005", "--out", dump)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        expected = {0: (1.0, 0.0), 2: (1.5, 0.0), 3: (5.0, 0.0), 4: (None, 10.0)}
        for lane, (ratio, overshoot) in expected.items():
            curves = subprocess.run([sys.executable, "-I", str(SCRIPTS / "motion_curves.py"), "--json", str(dump), "--key", f"lanes.{lane}.x"],
                                    capture_output=True, text=True, encoding="utf-8")
            curve = list(json.loads(curves.stdout)["curves"].values())[0]
            if ratio is not None:
                self.assertAlmostEqual(curve["peak_to_average"], ratio, delta=.08, msg=f"lane {lane}")
            self.assertAlmostEqual(curve["overshoot_pct"], overshoot, delta=.6, msg=f"lane {lane}")
            self.assertEqual(curve["speed_kinks_at_s"], [], f"lane {lane}")


if __name__ == "__main__":
    unittest.main()
