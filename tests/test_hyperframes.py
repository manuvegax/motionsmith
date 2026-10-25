"""scripts/hyperframes.py and kit/hyperframes.js: a piece becomes a HyperFrames project, stays in sync with its plan,
and hands its render to a HyperFrames film as a clip. The HyperFrames CLI itself runs only with
MOTION_TEST_HYPERFRAMES=1 (it is downloaded by npx)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def run_py(script, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def root_tag(piece: Path) -> str:
    return re.search(r'<div id="root"[^>]*>', (piece / "index.html").read_text(encoding="utf-8")).group(0)


class HyperFramesBridge(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="motion-hf-"))

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def test_every_piece_carries_the_plan_on_its_root_but_only_a_project_loads_gsap(self):
        plain, project = self.work / "plain", self.work / "project"
        self.assertEqual(run_py("new_piece.py", plain, "--recipe", "data-reveal", "--format", "square", "--fps", "30").returncode, 0)
        self.assertEqual(run_py("new_piece.py", project, "--recipe", "data-reveal", "--hyperframes", "--fps", "24").returncode, 0)
        self.assertIn('data-width="1080" data-height="1080" data-duration="5" data-fps="30"', root_tag(plain))
        self.assertNotIn("gsap", (plain / "index.html").read_text(encoding="utf-8"))
        self.assertFalse((plain / "hyperframes.json").exists())
        html = (project / "index.html").read_text(encoding="utf-8")
        self.assertIn("gsap@3.14.2/dist/gsap.min.js", html)
        self.assertIn('window.__timelines["motionsmith"] = MotionsmithHyperFrames.timeline(gsap, 5)', html)
        self.assertTrue(html.index("kit/hyperframes.js") < html.index("window.__timelines"))
        self.assertIn('data-fps="24"', root_tag(project))
        package = json.loads((project / "package.json").read_text(encoding="utf-8"))
        self.assertIn("hyperframes@", package["scripts"]["render"])
        self.assertTrue((project / "hyperframes.json").exists())
        self.assertTrue((project / "kit" / "hyperframes.js").exists())

    def test_sync_is_idempotent_and_check_catches_a_retimed_plan(self):
        piece = self.work / "p"
        self.assertEqual(run_py("new_piece.py", piece, "--hyperframes").returncode, 0)
        before = (piece / "index.html").read_text(encoding="utf-8")
        self.assertEqual(run_py("hyperframes.py", "sync", piece).returncode, 0)
        self.assertEqual((piece / "index.html").read_text(encoding="utf-8"), before)          # same plan, same file
        plan = json.loads((piece / "plan.json").read_text(encoding="utf-8"))
        plan["duration_frames"] = 300
        (piece / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        check = run_py("hyperframes.py", "sync", piece, "--check")
        self.assertEqual(check.returncode, 1)
        report = json.loads(check.stdout)
        self.assertEqual(set(report["mismatch"]), {"duration", "timeline"})
        self.assertEqual(run_py("hyperframes.py", "sync", piece).returncode, 0)
        html = (piece / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-duration="5"', root_tag(piece))
        self.assertEqual(html.count("hyperframes:timeline -->"), 2)                           # one block, not two
        self.assertEqual(run_py("hyperframes.py", "sync", piece, "--check").returncode, 0)

    def test_clip_copies_the_render_into_a_film_and_prints_its_elements(self):
        piece, film = self.work / "shot", self.work / "film"
        self.assertEqual(run_py("new_piece.py", piece, "--recipe", "lower-third").returncode, 0)
        (piece / "final").mkdir()
        (piece / "final" / "shot.mp4").write_bytes(b"not really a video")
        (piece / "assets" / "soundtrack.wav").write_bytes(b"RIFF")
        film.mkdir()
        (film / "index.html").write_text("<!doctype html>", encoding="utf-8")
        result = run_py("hyperframes.py", "clip", piece, "--project", film, "--start", "4.5", "--audio", "assets/soundtrack.wav", "--name", "Name Tag")
        self.assertEqual(result.returncode, 0, result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue((film / "assets" / "motionsmith" / "name-tag.mp4").exists())
        video, audio = report["paste_into_index_html"]
        self.assertIn('data-start="4.5" data-duration="5"', video)
        self.assertIn("muted", video)
        self.assertIn('<audio id="ms-name-tag-sound"', audio)
        again = run_py("hyperframes.py", "clip", piece, "--project", film, "--start", "1", "--name", "Name Tag")
        self.assertEqual(again.returncode, 2)                                                  # never overwrites
        self.assertIn("already in the project", again.stdout)


@unittest.skipUnless(os.environ.get("MOTION_TEST_HYPERFRAMES") == "1" and shutil.which("npx"),
                     "set MOTION_TEST_HYPERFRAMES=1 to run the HyperFrames CLI (downloaded by npx)")
class HyperFramesCli(unittest.TestCase):
    def test_hyperframes_lint_accepts_a_motionsmith_piece(self):
        work = Path(tempfile.mkdtemp(prefix="motion-hf-cli-"))
        try:
            piece = work / "quote"
            self.assertEqual(run_py("new_piece.py", piece, "--recipe", "kinetic-quote", "--hyperframes").returncode, 0)
            version = re.search(r"hyperframes@([\d.]+)", (piece / "package.json").read_text(encoding="utf-8")).group(1)
            npx = shutil.which("npx")
            lint = subprocess.run([npx, "--yes", f"hyperframes@{version}", "lint", "--json"], cwd=piece, capture_output=True,
                                  text=True, encoding="utf-8", timeout=600, env={**os.environ, "HYPERFRAMES_SKIP_SKILLS": "1"})
            report = json.loads(lint.stdout[lint.stdout.index("{"):])
            self.assertTrue(report["ok"], report["findings"])
            self.assertEqual(report["errorCount"], 0)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
