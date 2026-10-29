"""Talking-head tools: print_footage.py (screen print on twos) and gaze_check.py (labels, blink runs)."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import gaze_check  # noqa: E402
import print_footage  # noqa: E402

FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def decode(path: Path, w: int, h: int) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


@unittest.skipUnless(FFMPEG, "ffmpeg makes the fixture")
class PrintFootageTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="motion-print-"))
        self.src = self.dir / "src.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=24", "-t", "1",
                        "-pix_fmt", "yuv420p", str(self.src)], check=True)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def render(self, name: str, *extra: str) -> np.ndarray:
        out = self.dir / name
        code = print_footage.main([str(self.src), str(out), "--dur", "0.4", "--size", "108x192", "--hits", "0.1", *extra])
        self.assertEqual(code, 0)
        return decode(out, 108, 192)

    def test_frames_on_twos_and_deterministic(self):
        a = self.render("a.mp4")
        self.assertEqual(len(a), 12)                       # 0.4 s at 30 fps
        for k in range(0, 12, 2):                          # each print is held for two frames
            self.assertLess(np.abs(a[k].astype(int) - a[k + 1].astype(int)).mean(), 1.0)
        self.assertGreater(np.abs(a[0].astype(int) - a[2].astype(int)).mean(), 1.0)   # and then it moves
        b = self.render("b.mp4")
        self.assertLess(np.abs(a.astype(int) - b.astype(int)).mean(), 0.5)            # same input, same output

    def test_red_goes_to_the_accent_ink_unless_switched_off(self):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xd02818:size=320x240:rate=24", "-t", "1",
                        "-pix_fmt", "yuv420p", str(self.src)], check=True)
        for inks in ("paper", "night"):
            red = self.render(f"r-{inks}.mp4", "--inks", inks)[:, 40:150, 20:90].astype(float).mean((0, 1, 2))
            self.assertGreater(red[0], red[1] + 60, inks)               # reads as the accent
            flat = self.render(f"f-{inks}.mp4", "--inks", inks, "--no-accent")[:, 40:150, 20:90].astype(float).mean((0, 1, 2))
            self.assertLess(abs(flat[0] - flat[1]), 25, inks)            # base ink only: neutral


class GazeLabelTests(unittest.TestCase):
    @staticmethod
    def row(t, down=0.1, closed=0.1, side=0.1, dpitch=0.0, face=True):
        return {"t": t, "face": face, "down": down, "closed": closed, "side": side, "dpitch": dpitch}

    def test_short_closed_run_is_a_blink_long_down_run_stays_down(self):
        rows = [self.row(k / 30) for k in range(30)]
        for k in range(5, 9):
            rows[k]["closed"] = 0.6                       # a 4-frame blink
        for k in range(15, 25):
            rows[k]["down"] = 0.6                         # 10 frames reading the notes
        gaze_check.runs(rows, 0.42, 10)
        self.assertEqual({rows[k]["label"] for k in range(5, 9)}, {"blink"})
        self.assertEqual({rows[k]["label"] for k in range(15, 25)}, {"down"})
        s = gaze_check.summary(rows, 30)
        self.assertEqual(len(s["down_runs"]), 1)
        self.assertEqual(len(s["blink_first_second"]), 4)

    def test_head_drop_with_low_eyes_counts_and_heavy_lids_do_not(self):
        rows = [self.row(0, down=0.3, dpitch=12), self.row(0.033, down=0.3, dpitch=2), self.row(0.067, face=False)]
        gaze_check.runs(rows, 0.42, 10)
        self.assertEqual([r["label"] for r in rows], ["down", "ok", "no_face"])

    def test_relabel_cli(self):
        d = Path(tempfile.mkdtemp(prefix="motion-gaze-"))
        try:
            p = d / "g.json"
            p.write_text(json.dumps([self.row(k / 30, down=0.5) for k in range(10)]), encoding="utf-8")
            self.assertEqual(gaze_check.main(["--relabel", str(p), "--down", "0.6"]), 0)
            self.assertEqual({r["label"] for r in json.loads(p.read_text(encoding="utf-8"))}, {"ok"})
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
