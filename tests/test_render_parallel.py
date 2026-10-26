"""render_parallel.mjs: chunks render at once, join exactly, match render_stream.mjs and resume."""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def browser_available() -> bool:
    if not (shutil.which("node") and shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return False
    return subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True).returncode == 0


def frames_of(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries",
                          "stream=nb_read_frames", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return int(out.stdout.strip())


def psnr(a: Path, b: Path) -> float:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(a), "-i", str(b), "-lavfi", "psnr", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    match = re.search(r"average:([\d.]+|inf)", out)
    return float("inf") if match.group(1) == "inf" else float(match.group(1))


@unittest.skipUnless(browser_available(), "node + Playwright + ffmpeg render the chunks")
class RenderParallelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-parallel-"))
        cls.piece = cls.workspace / "piece"
        made = subprocess.run([sys.executable, "-I", str(SCRIPTS / "new_piece.py"), str(cls.piece), "--recipe", "kinetic-quote",
                               "--format", "square", "--fps", "24", "--duration", "4"], capture_output=True, text=True)
        assert made.returncode == 0, made.stdout + made.stderr

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.workspace, ignore_errors=True)

    def render(self, out: str, *extra: str) -> dict:
        result = subprocess.run(["node", str(SCRIPTS / "render_parallel.mjs"), "--root", str(self.piece), "--out", out,
                                 "--no-audio", "--chunk-seconds", "1", "--workers", "2", "--preset", "ultrafast", *extra],
                                capture_output=True, text=True, timeout=900)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def test_chunks_join_exactly_and_match_one_pass(self):
        report = self.render("final/par.mp4")
        self.assertEqual(report["chunks"], 4)
        self.assertEqual(frames_of(self.piece / "final" / "par.mp4"), 96)
        one = subprocess.run(["node", str(SCRIPTS / "render_stream.mjs"), "--root", str(self.piece), "--out", "final/one.mp4",
                              "--no-audio", "--preset", "ultrafast"], capture_output=True, text=True, timeout=900)
        self.assertEqual(one.returncode, 0, one.stderr)
        # Same frames, different keyframe placement: the encodes differ only by compression noise.
        self.assertGreater(psnr(self.piece / "final" / "par.mp4", self.piece / "final" / "one.mp4"), 40)
        self.assertEqual(list((self.piece / "preview" / "chunks").glob("par-*")), [])   # cleaned up

    def test_resume_reuses_chunks_and_a_changed_piece_does_not(self):
        first = self.render("final/a.mp4", "--keep-chunks")
        self.assertEqual(first["reused_chunks"], 0)
        (self.piece / "final" / "a.mp4").unlink()
        again = self.render("final/a.mp4", "--keep-chunks")
        self.assertEqual(again["reused_chunks"], 4)
        script = self.piece / "piece.js"
        script.write_text(script.read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8")
        (self.piece / "final" / "a.mp4").unlink()
        changed = self.render("final/a.mp4")
        self.assertEqual(changed["reused_chunks"], 0)

    def test_refuses_to_overwrite(self):
        (self.piece / "final").mkdir(exist_ok=True)
        (self.piece / "final" / "taken.mp4").write_bytes(b"x")
        result = subprocess.run(["node", str(SCRIPTS / "render_parallel.mjs"), "--root", str(self.piece), "--out", "final/taken.mp4",
                                 "--no-audio"], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
