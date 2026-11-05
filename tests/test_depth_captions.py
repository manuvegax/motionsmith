"""depth_captions.py: onset snap, caption groups, word choice and placement, model refusal, and a full render."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
import depth_captions as dc  # noqa: E402

FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def W(text, s, e):
    return {"text": text, "start": s, "end": e}


class LogicTests(unittest.TestCase):
    def test_snap_moves_an_early_start_to_the_voice(self):
        audio = np.zeros(dc.SR * 2, np.float32)
        t = np.arange(int(dc.SR * .6)) / dc.SR
        audio[int(.5 * dc.SR): int(1.1 * dc.SR)] = .3 * np.sin(2 * np.pi * 220 * t)
        audio += np.random.default_rng(0).normal(0, 1e-4, audio.size).astype(np.float32)
        out = dc.snap_onsets([W("hola", .4, 1.0)], dc.level_db(audio))
        self.assertAlmostEqual(out[0]["start"], .5, delta=.02)
        self.assertEqual(out[0]["raw_start"], .4)

    def test_snap_keeps_a_word_inside_speech_and_the_order(self):
        audio = .3 * np.sin(2 * np.pi * 220 * np.arange(dc.SR * 2) / dc.SR).astype(np.float32)
        out = dc.snap_onsets([W("a", .5, .7), W("b", .69, .9)], dc.level_db(audio))
        self.assertEqual([w["start"] for w in out], [.5, .69])

    def test_groups_split_and_skip_the_big_word(self):
        words = [W("si", 0, .2), W("me", .2, .3), W("llego", .3, .5), W("a", .5, .6), W("morir,", .6, .9),
                 W("pizza", 1.0, 1.4), W("y", 1.45, 1.5), W("full", 1.5, 1.7)]
        g = dc.caption_groups(words, 5, 3.0)
        self.assertEqual([[w["text"] for w in x["words"]] for x in g], [["si", "me", "llego"], ["a", "morir,"], ["y", "full"]])
        self.assertEqual(g[0]["end"], .5)                       # until the next group starts
        self.assertAlmostEqual(g[-1]["end"], 2.9, delta=1e-6)   # its last word + 1.2 s, inside the clip

    def test_pick_word(self):
        words = [W("el", 0, .1), W("cerebro", .1, .5), W("tiene", .5, .7), W("100", .7, 1), W("trucos", 1, 1.4)]
        self.assertEqual(dc.pick_word(words, None, None), 3)            # a number first
        self.assertEqual(dc.pick_word(words, "CEREBRO", None), 1)       # case and accents ignored
        with self.assertRaises(SystemExit):
            dc.pick_word(words, "nada", None)

    def head(self, H=400, Wd=240, top=120, r=50):
        yy, xx = np.mgrid[0:H, 0:Wd]
        m = ((xx - Wd / 2) ** 2 + (yy - top - r) ** 2 <= r * r) | ((yy > top + 2 * r - 10) & (abs(xx - Wd / 2) < 80))
        return (m * 255).astype(np.uint8)

    def test_head_top_ignores_a_raised_hand_at_the_side(self):
        m = self.head()
        m[20:60, 5:30] = 255
        self.assertAlmostEqual(dc.head_top(m), 120, delta=2)   # the first row a few px wide

    def test_place_word_overlaps_sixty_percent_and_covers_enough(self):
        m = self.head()
        ink = np.ones((40, 200), np.float32)
        y, cover = dc.place_word(m, ink)
        self.assertAlmostEqual(y, 120 - .4 * 40, delta=2)
        self.assertGreaterEqual(cover, .15)

    def test_place_word_lowers_for_a_pointy_head(self):
        m = np.zeros((400, 240), np.uint8)
        yy, xx = np.mgrid[0:400, 0:240]
        m[(yy >= 100) & (abs(xx - 120) <= (yy - 100) * .15)] = 255       # a narrow cone: a hood
        ink = np.ones((40, 200), np.float32)
        y, cover = dc.place_word(m, ink)
        self.assertGreater(y, 100 - 16)
        self.assertGreaterEqual(cover, .15)

    def test_pop_reaches_105_then_settles(self):
        vals = [dc.pop(i / 6) for i in range(8)]
        self.assertAlmostEqual(vals[0], .8)
        self.assertAlmostEqual(max(vals), 1.05, delta=.005)
        self.assertEqual(vals[6], 1.0)

    def test_missing_model_refuses_without_downloading(self):
        tmp = tempfile.mkdtemp()
        old = os.environ.get("U2NET_HOME")
        os.environ["U2NET_HOME"] = tmp
        try:
            with self.assertRaises(SystemExit) as cm:
                dc.model_path("birefnet-portrait")
            self.assertIn("nothing was downloaded", str(cm.exception))
        finally:
            if old is None:
                os.environ.pop("U2NET_HOME")
            else:
                os.environ["U2NET_HOME"] = old
            shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(FFMPEG, "ffmpeg makes the fixture")
class RenderTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="motion-depth-"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_render_storyboard_and_events(self):
        w, h, fps, n = 270, 480, 30, 30
        frames = np.full((n, h, w, 3), 200, np.uint8)
        yy, xx = np.mgrid[0:h, 0:w]
        disc = (xx - w / 2) ** 2 + (yy - 200) ** 2 <= 60 ** 2
        frames[:, disc] = (40, 30, 30)
        clip = self.dir / "clip.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                        "-f", "lavfi", "-i", "sine=frequency=220:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-shortest", str(clip)],
                       input=frames.tobytes(), check=True, capture_output=True)
        words = self.dir / "words.json"
        words.write_text(json.dumps({"words": [W("una", .05, .2), W("palabra", .2, .4), W("PIZZA", .4, .7), W("fin", .7, .9)]}))
        matte = self.dir / "matte"
        matte.mkdir()
        from PIL import Image
        for i in range(12, n):
            Image.fromarray((disc * 255).astype(np.uint8)).save(matte / f"{i:06d}.png")
        script = SKILL / "scripts" / "depth_captions.py"
        out = self.dir / "final" / "clip.mp4"
        r = subprocess.run([sys.executable, "-I", str(script), "render", str(clip), "--words", str(words), "--word", "pizza",
                            "--matte", str(matte), "--out", str(out), "--color", "#111111"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        rep = json.loads(r.stdout)
        self.assertEqual(rep["frames"], n)
        self.assertEqual(rep["frames_without_matte"], 0)
        self.assertGreaterEqual(rep["head_covers"], .15)
        self.assertTrue(out.with_suffix(".png").exists())
        events = json.loads(Path(str(out) + ".events.json").read_text(encoding="utf-8"))
        self.assertEqual(events[0]["role"], "big word PIZZA")
        tags = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                               "stream=color_space,color_primaries,color_transfer", "-of", "json", str(out)],
                              capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(tags)["streams"][0]["color_primaries"], "bt709")
        again = subprocess.run([sys.executable, "-I", str(script), "render", str(clip), "--words", str(words), "--word", "pizza",
                                "--matte", str(matte), "--out", str(out)], capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)                       # never overwrites a render
        board = subprocess.run([sys.executable, "-I", str(script), "storyboard", str(clip), "--words", str(words), "--word",
                                "pizza", "--matte", str(matte), "--out", str(self.dir / "board")], capture_output=True, text=True)
        self.assertEqual(board.returncode, 0, board.stderr)
        self.assertGreaterEqual(len(list((self.dir / "board").glob("*.png"))), 3)


if __name__ == "__main__":
    unittest.main()
