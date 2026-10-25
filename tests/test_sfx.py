"""Tests for the sfx package and scripts/build_soundtrack.py.

Render-level checks run anywhere with NumPy. The build checks need FFmpeg (loudness is measured with it) and are
skipped without it: same seed gives the same WAV bytes, loudness lands within 1 LU of the target, and every hit has an
attack within the BT.1359 window (45 ms before to 125 ms after), checked with scripts/audio_check.py.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audio_check  # noqa: E402
from sfx import SR, VOICES, Score, duck_envelope, ffmpeg_measure, normalize_hits, render  # noqa: E402

PLAN = {
    "duration": 4.0,
    "hits": [
        {"time": 0.5, "amplitude": 1.0, "role": "hit"},
        {"time": 1.6, "amplitude": 1.0, "role": "boom"},
        {"time": 2.4, "amplitude": 0.8, "role": "glass"},
        {"time": 3.1, "amplitude": 0.9, "role": "slap"},
    ],
}
CUES = {
    "cues": [
        {"voice": "bed", "levels": [[0, 0.10], [2.0, 0.25], [4.0, 0.05]]},
        # Ends 0.3 s before the first hit: a riser peak inside audio_check's 120 ms onset gap would hide the hit.
        {"time": 0.0, "voice": "riser", "end": 0.2, "gain": 0.2},
        {"time": 1.0, "voice": "whoosh", "duration": 0.5, "pan_from": -0.6, "pan_to": 0.6},
        {"time": 2.0, "voice": "ticks", "count": 4, "spacing": 0.02},
        {"time": 2.0, "voice": "reverse_swell", "duration": 0.2},
        {"time": 3.6, "voice": "shimmer", "duration": 0.3, "gain": 0.1},
        {"time": 3.4, "voice": "duck", "fall": 0.05, "hold": 0.1, "rise": 0.03, "depth": 0.5},
    ]
}


def _build(out: Path, *extra: str, plan: Path, cues: Path | None = None, seed: int = 7):
    command = [sys.executable, str(SCRIPTS / "build_soundtrack.py"), "--plan", str(plan), "--out", str(out),
               "--seed", str(seed), *extra]
    if cues is not None:
        command += ["--cues", str(cues)]
    out.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", cwd=out.parent)


def _read_mono(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as handle:
        assert handle.getnchannels() == 2 and handle.getsampwidth() == 2 and handle.getframerate() == SR
        frames = handle.readframes(handle.getnframes())
    stereo = np.frombuffer(frames, dtype="<i2").reshape(-1, 2).astype(np.float64) / 32768
    return stereo.mean(axis=1)


class RenderTests(unittest.TestCase):
    """Synthesis and scheduling; no FFmpeg needed."""

    def test_same_seed_same_samples(self):
        first, report_a = render(PLAN, CUES, 3)
        second, report_b = render(PLAN, CUES, 3)
        self.assertTrue(np.array_equal(first, second))
        self.assertEqual(report_a, report_b)
        other, _ = render(PLAN, CUES, 4)
        self.assertFalse(np.array_equal(first, other))

    def test_every_voice_is_finite_and_audible(self):
        for name, fn in VOICES.items():
            score = Score(1.0, 5)
            kwargs = {}
            for parameter in list(inspect.signature(fn).parameters.values())[2:]:
                if parameter.default is inspect.Parameter.empty:
                    kwargs[parameter.name] = 3 if parameter.name == "count" else 0.3
            fn(score, 0.1, **kwargs)
            self.assertTrue(np.isfinite(score.dry).all(), name)
            self.assertGreater(float(np.max(np.abs(score.dry))), 1e-4, name)

    def test_hits_land_on_their_exact_times(self):
        master, report = render({"duration": 2.0, "hits": [{"time": 1.0, "amplitude": 1.0, "role": "boom"}]}, {"cues": []}, 2)
        energy = np.abs(master).sum(axis=1)
        start = round(1.0 * SR)
        silence = energy[: start - 2 * SR // 100].max(initial=0.0)
        self.assertLess(silence + 1e-9, energy[start:start + SR // 100].max())
        self.assertEqual(report["hits"][0]["voice"], "boom")

    def test_a_new_piece_plan_gives_its_duration_in_frames(self):
        from sfx.schedule import plan_duration
        self.assertAlmostEqual(plan_duration({"duration_frames": 240, "fps": 60}), 4.0)
        self.assertAlmostEqual(plan_duration({"duration_frames": 300, "fps": "30000/1001"}), 300 * 1001 / 30000)
        self.assertEqual(plan_duration({"duration": 2.5, "duration_frames": 99, "fps": 60}), 2.5)
        with self.assertRaisesRegex(ValueError, "duration"):
            plan_duration({"hits": []})
        master, _ = render({"duration_frames": 180, "fps": 60, "hits": [{"time": 1.0, "amplitude": 1, "role": "hit"}]}, None, 1)
        self.assertEqual(master.shape[0], 3 * SR)

    def test_unknown_parameter_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "unknown parameter"):
            render(PLAN, {"cues": [{"time": 1.0, "voice": "hit", "bogus": 1}]}, 1)

    def test_unknown_voice_and_bad_hit_are_errors(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            render(PLAN, {"cues": [{"time": 1.0, "voice": "trumpet"}]}, 1)
        with self.assertRaisesRegex(ValueError, "time"):
            normalize_hits([{"amplitude": 1.0}])
        with self.assertRaisesRegex(ValueError, "amplitude"):
            normalize_hits([[1.0, 5.0]])

    def test_role_mapped_to_a_voice_with_required_parameters_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "needs parameters"):
            render({"duration": 2.0, "hits": [{"time": 1.0, "role": "sweep"}]}, {"role_voices": {"sweep": "riser"}}, 1)

    def test_duck_envelope_dips_and_returns(self):
        gain = duck_envelope(SR * 2, SR, [{"at": 1.0, "fall": 0.05, "hold": 0.1, "rise": 0.05, "depth": 0.9}])
        self.assertAlmostEqual(float(gain[0]), 1.0)
        self.assertAlmostEqual(float(gain[int(1.1 * SR)]), 0.1, places=3)
        self.assertAlmostEqual(float(gain[int(1.9 * SR)]), 1.0, places=6)

    def test_cue_outside_the_piece_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "outside the piece"):
            render(PLAN, {"cues": [{"time": 9.0, "voice": "hit"}]}, 1)


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required for the mastering measurements")
class BuildTests(unittest.TestCase):
    """The command-line build, measured with FFmpeg and with the audio checks."""

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.work = Path(cls.directory.name)
        cls.plan = cls.work / "plan.json"
        cls.cues = cls.work / "cues.json"
        cls.plan.write_text(json.dumps(PLAN), encoding="utf-8")
        cls.cues.write_text(json.dumps(CUES), encoding="utf-8")
        cls.first = cls.work / "a" / "soundtrack.wav"
        cls.result = _build(cls.first, "--report", str(cls.work / "a" / "report.json"), plan=cls.plan, cues=cls.cues)
        cls.report = json.loads((cls.work / "a" / "report.json").read_text(encoding="utf-8")) if cls.result.returncode == 0 else {}

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_a_silent_plan_fails_with_a_message(self):
        silent = self.work / "silent.json"
        silent.write_text(json.dumps({"duration": 3, "hits": []}), encoding="utf-8")
        result = _build(self.work / "silent" / "s.wav", plan=silent, cues=None)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("silent", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_build_succeeds(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout + self.result.stderr)
        self.assertTrue(self.first.is_file())

    def test_same_seed_gives_identical_wav(self):
        second = self.work / "b" / "soundtrack.wav"
        result = _build(second, plan=self.plan, cues=self.cues)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(digest(self.first), digest(second))
        self.assertEqual(self.report["sha256"], digest(self.first))

    def test_loudness_within_one_lu_and_peak_under_ceiling(self):
        measured = audio_check.ebur128(self.first, shutil.which("ffmpeg"))
        self.assertLessEqual(abs(measured["integrated_lufs"] - (-16.0)), 1.0, measured)
        self.assertLessEqual(measured["true_peak_dbtp"], -1.4, measured)

    def test_every_hit_has_an_attack_inside_the_bt1359_window(self):
        mono = _read_mono(self.first)
        events = [{"time": h["time"], "role": h["role"], "source": "hits"} for h in normalize_hits(PLAN["hits"])]
        found = audio_check.onsets(mono, 24)
        sync = audio_check.match_events(found, events, audio_check.EARLY_S, audio_check.LATE_S)
        self.assertEqual(sync["unmatched_events"], [], sync)
        for row in sync["events"]:
            self.assertLessEqual(-45, row["offset_ms"], row)
            self.assertLessEqual(row["offset_ms"], 125, row)

    def test_refuses_to_overwrite_without_replace(self):
        before = hashlib.sha256(self.first.read_bytes()).hexdigest()
        result = _build(self.first, plan=self.plan, cues=self.cues)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--replace", result.stderr)
        self.assertEqual(hashlib.sha256(self.first.read_bytes()).hexdigest(), before)
        replaced = _build(self.first, "--replace", plan=self.plan, cues=self.cues)
        self.assertEqual(replaced.returncode, 0, replaced.stdout + replaced.stderr)
        self.assertEqual(hashlib.sha256(self.first.read_bytes()).hexdigest(), before)

    def test_bad_cue_is_a_usage_error_and_writes_nothing(self):
        bad = self.work / "bad-cues.json"
        bad.write_text(json.dumps({"cues": [{"time": 1.0, "voice": "hit", "bogus": 2}]}), encoding="utf-8")
        out = self.work / "c" / "soundtrack.wav"
        result = _build(out, plan=self.plan, cues=bad)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("unknown parameter", result.stderr)
        self.assertFalse(out.exists())

    def test_ffmpeg_measures_the_written_file(self):
        measured = ffmpeg_measure(shutil.which("ffmpeg"), path=self.first)
        self.assertLessEqual(abs(measured["integrated_lufs"] + 16.0), 1.0)


if __name__ == "__main__":
    unittest.main()
