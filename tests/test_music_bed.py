"""The music bed (scripts/sfx/music.py): a recorded file under the score, aligned, looped, faded and ducked on hits."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from sfx import SR, render  # noqa: E402
from sfx.music import bed_from_file  # noqa: E402


def write_wav(path: Path, seconds: float, sr: int = 44100, freq: float = 220.0) -> None:
    t = np.arange(int(seconds * sr)) / sr
    tone = .3 * np.sin(2 * np.pi * freq * t)
    marker = np.where(t < .05, .9, 0)                          # a click at the very start: tells where reading began
    data = np.stack([tone + marker, tone + marker], 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(data, -1, 1) * 32767).astype("<i2").tobytes())


def rms(x: np.ndarray) -> float:
    return float(np.sqrt((x ** 2).mean()))


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg decodes the music file")
class MusicBed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="motion-music-"))
        write_wav(cls.tmp / "bed.wav", 2.0)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_bed_plays_between_hits_and_dips_on_them(self):
        hits = [{"time": 2.5, "amplitude": 1.0, "role": "hit"}]   # away from the loop point (2 s)
        layer, info = bed_from_file({"file": "bed.wav", "gain_db": 0, "fade_in": 0, "fade_out": 0, "duck_db": -12},
                                    4.0, SR, hits, self.tmp)
        self.assertEqual(layer.shape, (4 * SR, 2))
        before, on_hit = rms(layer[int(1.5 * SR):int(1.8 * SR)]), rms(layer[int(2.5 * SR):int(2.55 * SR)])
        self.assertGreater(before, .15)
        self.assertLess(on_hit, before * .4)                     # about −12 dB on the hit
        self.assertTrue(info["loop"])
        self.assertGreater(rms(layer[int(3.5 * SR):]), .1)       # the 2 s file looped to cover 4 s

    def test_start_bar_reads_from_the_bar_and_loop_false_stops(self):
        layer, info = bed_from_file({"file": "bed.wav", "gain_db": 0, "fade_in": 0, "fade_out": 0, "duck_db": 0,
                                     "start_bar": 1, "bpm": 240, "loop": False}, 3.0, SR, [], self.tmp)
        self.assertAlmostEqual(info["start_s"], 1.0)              # one bar of 4 beats at 240 BPM = 1 s
        self.assertLess(np.abs(layer[:int(.04 * SR)]).max(), .5)  # the start click is not there: reading began at 1 s
        self.assertLess(rms(layer[int(1.2 * SR):]), 1e-6)         # 1 s of file left, no loop: silence after it

    def test_mistakes_are_clear(self):
        for params, needle in (({"file": "missing.wav"}, "not found"), ({"file": "bed.wav", "volume": 1}, "unknown"),
                               ({"file": "bed.wav", "start_bar": 1}, "needs bpm"), ({"file": "bed.wav", "time": 9}, "outside")):
            with self.subTest(params=params), self.assertRaisesRegex(ValueError, needle):
                bed_from_file(params, 4.0, SR, [], self.tmp)

    def test_render_mixes_it_after_the_room_and_reports_it(self):
        plan = {"duration": 3.0, "hits": [{"time": 1.0, "amplitude": 1.0, "role": "hit"}]}
        master, report = render(plan, {"cues": [{"voice": "music", "file": "bed.wav", "gain_db": -6}]}, 1, base=self.tmp)
        again, _ = render(plan, {"cues": [{"voice": "music", "file": "bed.wav", "gain_db": -6}]}, 1, base=self.tmp)
        self.assertTrue(np.array_equal(master, again))           # same file, same settings, same samples
        self.assertEqual(len(report["layers"]["music"]), 1)
        self.assertEqual(report["layers"]["music"][0]["gain_db"], -6)
        self.assertGreater(rms(master[int(2.0 * SR):int(2.4 * SR)]), .05)

    def test_build_soundtrack_reads_the_file_next_to_the_cues(self):
        work = self.tmp / "piece"
        (work / "assets").mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.tmp / "bed.wav", work / "assets" / "bed.wav")
        (work / "plan.json").write_text(json.dumps({"duration_frames": 180, "fps": 60,
                                                    "hits": [{"time": 1.0, "amplitude": 1, "role": "hit"}]}), encoding="utf-8")
        (work / "cues.json").write_text(json.dumps({"cues": [{"voice": "music", "file": "assets/bed.wav", "gain_db": -8}]}), encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "build_soundtrack.py"), "--plan", str(work / "plan.json"),
                                 "--cues", str(work / "cues.json"), "--out", str(work / "assets" / "soundtrack.wav"),
                                 "--report", str(work / "report.json")], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((work / "report.json").read_text(encoding="utf-8"))
        self.assertIn("music", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
