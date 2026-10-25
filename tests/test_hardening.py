"""Hardening found in the pre-release audit: the capture server, the network fence, draft samples, the 8-bit
fallback and where pieces may live."""
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
TESTS = Path(__file__).resolve().parent


def run_py(script, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def browser_available() -> bool:
    if not shutil.which("node"):
        return False
    return subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True, text=True).returncode == 0


class Server(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "node runs the server check")
    def test_the_capture_server_stays_inside_its_folder(self):
        result = subprocess.run(["node", str(TESTS / "server_check.mjs")], capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(result.stdout.startswith("ok "), result.stdout)


class Placement(unittest.TestCase):
    def test_a_piece_is_never_created_inside_the_skill(self):
        inside = SKILL / "work" / "should-not-exist"
        result = run_py("new_piece.py", inside)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("inside the skill", result.stdout)
        self.assertFalse(inside.exists())


@unittest.skipUnless(browser_available(), "node + Playwright drive the browser")
class Capture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-hardening-"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.workspace, ignore_errors=True)

    def scaffold(self, name, *extra):
        folder = self.workspace / name
        self.assertEqual(run_py("new_piece.py", folder, "--fps", "30", *extra).returncode, 0)
        return folder

    def sample(self, folder, env=None):
        return subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(folder), "--out", str(folder / "preview" / "s"),
                               "--times", "1.2"], capture_output=True, text=True, encoding="utf-8", timeout=300,
                              env={**os.environ, **(env or {})})

    def test_the_page_cannot_reach_the_internet_during_a_capture(self):
        folder = self.scaffold("network")
        script = folder / "piece.js"
        script.write_text("fetch('https://example.com/x.json').catch(() => {});\n" + script.read_text(encoding="utf-8"), encoding="utf-8")
        result = self.sample(folder)
        self.assertNotEqual(result.returncode, 0, "a blocked request must fail the capture")
        self.assertIn("network blocked: https://example.com/x.json", result.stdout + result.stderr)

    def test_without_half_float_the_piece_says_how_to_render_in_8_bits(self):
        folder = self.scaffold("no-hdr")
        index = folder / "index.html"
        patch = ("<script>const g = WebGLRenderingContext.prototype.getExtension;"
                 "WebGLRenderingContext.prototype.getExtension = function (n) { return /half_float/i.test(n) ? null : g.call(this, n); };</script>\n")
        html = index.read_text(encoding="utf-8")
        index.write_text(html.replace('<script src="kit/motion-math.js"></script>', patch + '<script src="kit/motion-math.js"></script>', 1), encoding="utf-8")
        refused = self.sample(folder)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("allow_ldr", refused.stdout + refused.stderr)
        plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
        plan["render"] = {"allow_ldr": True}
        (folder / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        result = subprocess.run(["node", str(SCRIPTS / "dump_state.mjs"), "--root", str(folder), "--expr", "window.motionConfig",
                                 "--times", "1", "--seek", "--out", str(folder / "preview" / "ldr.json")], capture_output=True,
                                text=True, encoding="utf-8", timeout=300)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        value = json.loads((folder / "preview" / "ldr.json").read_text(encoding="utf-8"))["samples"][0]["value"]
        self.assertFalse(value["hdr"])
        self.assertIn("8-bit", value["samples"])

    def test_a_draft_caps_the_samples_and_says_so(self):
        folder = self.scaffold("draft")
        result = subprocess.run(["node", str(SCRIPTS / "dump_state.mjs"), "--root", str(folder), "--expr", "window.motionConfig",
                                 "--times", "1", "--out", str(folder / "preview" / "config.json")], capture_output=True, text=True,
                                encoding="utf-8", timeout=300, env={**os.environ, "MOTION_MAX_SAMPLES": "4"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        config = json.loads((folder / "preview" / "config.json").read_text(encoding="utf-8"))
        value = config["samples"][0]["value"]
        self.assertTrue(value["draft"])
        self.assertTrue(value["samples"].endswith("1–4"), value["samples"])
