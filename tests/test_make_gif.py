"""Tests for scripts/make_gif.py: the FFmpeg palette pipeline on a synthetic MP4 (skipped without FFmpeg), the size warning,
overwrite protection, and argument checks that need no FFmpeg."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import make_gif  # noqa: E402

SCRIPT = ROOT / "scripts" / "make_gif.py"


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")


class CommandTests(unittest.TestCase):
    def test_the_filter_is_one_palette_per_clip(self):
        graph = make_gif.gif_filter(10, 160, 64, "bayer")
        for part in ("fps=10", "scale=160:-1:flags=lanczos", "palettegen=max_colors=64:stats_mode=diff", "paletteuse=dither=bayer"):
            self.assertIn(part, graph)

    def test_the_command_seeks_then_trims_and_loops_forever(self):
        command = make_gif.build_command("ffmpeg", Path("in.mp4"), Path("out.gif"), start=1.5, duration=2.0, fps=12, width=480)
        self.assertEqual(command[command.index("-ss") + 1], "1.500")
        self.assertEqual(command[command.index("-t") + 1], "2.000")
        self.assertEqual(command[command.index("-loop") + 1], "0")
        self.assertIn("-n", command)
        self.assertIn("-y", make_gif.build_command("ffmpeg", Path("a"), Path("b"), overwrite=True))

    def test_no_dither_is_a_valid_choice(self):
        self.assertIn("dither=none", make_gif.gif_filter(12, 480, 128, "none"))

    def test_bad_arguments_are_usage_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            video = Path(folder) / "clip.mp4"
            video.write_bytes(b"not really a video")
            self.assertEqual(run_cli("--video", str(video), "--start", "2", "--end", "1", "--out", str(Path(folder) / "a.gif")).returncode, 2)
            self.assertEqual(run_cli("--video", str(video), "--out", str(Path(folder) / "a.png")).returncode, 2)
            self.assertEqual(run_cli("--video", str(Path(folder) / "missing.mp4"), "--out", str(Path(folder) / "a.gif")).returncode, 2)
            self.assertEqual(run_cli("--root", folder, "--start", "0", "--out", str(Path(folder) / "a.gif")).returncode, 2)


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for the GIF tests")
class GifTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.directory.name)
        cls.video = cls.folder / "synthetic.mp4"
        # Two seconds of test pattern at 24 fps; mpeg4 is always available, so no encoder choice is needed.
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=24",
                        "-t", "2", "-c:v", "mpeg4", "-pix_fmt", "yuv420p", str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_a_time_range_becomes_a_looping_gif_of_the_right_size(self):
        out = self.folder / "range.gif"
        result = run_cli("--video", str(self.video), "--start", "0.5", "--end", "1.5", "--fps", "10", "--width", "80",
                         "--out", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report["width"], report["height"]), (80, 60))
        self.assertIn(report["frames"], range(9, 12), report)
        self.assertEqual(out.read_bytes()[:4], b"GIF8")
        self.assertEqual(report["warnings"], [])

    def test_a_large_gif_is_reported_and_strict_fails(self):
        out = self.folder / "big.gif"
        result = run_cli("--video", str(self.video), "--start", "0", "--duration", "1", "--fps", "12", "--width", "160",
                         "--max-mb", "0.0001", "--out", str(out))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any("larger than" in w for w in json.loads(result.stdout)["warnings"]))
        strict = run_cli("--video", str(self.video), "--duration", "1", "--width", "160", "--max-mb", "0.0001",
                         "--strict", "--out", str(self.folder / "strict.gif"))
        self.assertEqual(strict.returncode, 1)

    def test_an_existing_gif_is_kept_unless_replaced(self):
        out = self.folder / "kept.gif"
        self.assertEqual(run_cli("--video", str(self.video), "--duration", "0.5", "--width", "64", "--out", str(out)).returncode, 0)
        before = out.read_bytes()
        again = run_cli("--video", str(self.video), "--duration", "0.5", "--width", "64", "--out", str(out))
        self.assertEqual(again.returncode, 2)
        self.assertEqual(out.read_bytes(), before)
        self.assertEqual(run_cli("--video", str(self.video), "--duration", "0.5", "--width", "32", "--replace", "--out", str(out)).returncode, 0)

    def test_a_broken_video_is_an_ffmpeg_error(self):
        broken = self.folder / "broken.mp4"
        broken.write_bytes(b"\x00" * 64)
        result = run_cli("--video", str(broken), "--out", str(self.folder / "broken.gif"))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertFalse((self.folder / "broken.gif").exists())


if __name__ == "__main__":
    unittest.main()
