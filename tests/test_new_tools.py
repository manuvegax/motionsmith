"""Checks for the tools added on 22-10-2026: audio_check, contact_sheet, cadence, plan timing and the capture kit."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

import numpy as np
from PIL import Image

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
KEEP = os.environ.get("MOTION_KEEP_TEST_EVIDENCE") == "1"


def run_py(script, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


class Workspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-new-tools-"))

    @classmethod
    def tearDownClass(cls):
        if not KEEP:
            shutil.rmtree(cls.workspace, ignore_errors=True)


class IsolatedImports(unittest.TestCase):
    def test_every_python_cli_starts_under_python_isolated_mode(self):
        for script in ("inspect_video.py", "verify_export.py", "validate_plan.py", "watch_reference.py",
                       "audio_check.py", "contact_sheet.py", "audio_envelope.py", "motion_curves.py"):
            with self.subTest(script=script):
                if script == "watch_reference.py" and importlib.util.find_spec("cv2") is None:
                    continue                                     # OpenCV is optional
                result = run_py(script, "--help")
                self.assertEqual(result.returncode, 0, result.stderr)


class PlanTiming(Workspace):
    def setUp(self):
        self.plan = {
            "schema_version": 1, "width": 1080, "height": 1920, "fps": 60, "duration_frames": 420,
            "mode": "retro", "format": "story", "audio": "required",
            "safe_area": {"x": 80, "y": 270, "width": 920, "height": 1310},
            "hits": [{"time": 1.0, "amplitude": 1, "role": "señal"}, {"time": 6.25, "amplitude": 1.4, "role": "apagado"}],
            "sound_cues": [{"time": 0.1, "role": "encendido"}],
            "scenes": [{"id": "a", "start_frame": 0, "end_frame": 420, "intent": "x", "action": "y", "text": "",
                        "transition": {"kind": "end", "carrier": ""}}],
        }

    def check(self, plan):
        path = self.workspace / "plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        result = run_py("validate_plan.py", path)
        return json.loads(result.stdout)["errors"]

    def test_retro_story_with_hits_is_valid(self):
        self.assertEqual(self.check(self.plan), [])

    def test_bad_hits_and_cues_are_reported(self):
        cases = {
            "out of order": lambda p: p["hits"].reverse(),
            "beyond duration": lambda p: p["hits"][1].update(time=7.5),
            "amplitude": lambda p: p["hits"][0].update(amplitude=0),
            "role": lambda p: p["hits"][0].pop("role"),
            "cue time": lambda p: p["sound_cues"][0].update(time=9),
            "format": lambda p: p.update(format="post"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                plan = copy.deepcopy(self.plan)
                mutate(plan)
                self.assertTrue(self.check(plan), name)


class AudioCheck(Workspace):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sr, seconds = 48000, 3.0
        t = np.arange(int(sr * seconds)) / sr
        signal = 0.35 * np.sin(2 * np.pi * 40 * t)                       # mostly sub-bass: phones lose it
        for at in (0.5, 1.5, 2.5):                                       # three clicks: the onsets to find
            i = int(at * sr)
            k = np.arange(2400)
            signal[i:i + 2400] += 0.5 * np.sin(2 * np.pi * 2000 * k / sr) * np.exp(-k / 300)
        signal[int(1.9 * sr):int(2.1 * sr)] = 0                          # a silent gap to measure
        fade = np.minimum(1, np.minimum(t, seconds - t) / 0.01)
        pcm = np.round(np.column_stack([signal * fade] * 2) * 32767).astype("<i2")
        cls.wav = cls.workspace / "clicks.wav"
        with wave.open(str(cls.wav), "wb") as handle:
            handle.setnchannels(2), handle.setsampwidth(2), handle.setframerate(sr)
            handle.writeframes(pcm.tobytes())

    def test_onsets_events_segments_and_phone_warning(self):
        spectrogram = self.workspace / "spec.png"
        result = run_py("audio_check.py", self.wav, "--events", "0.5,1.5,2.5,2.9", "--onsets", "4",
                        "--segment", "gap=1.95:2.05", "--spectrogram", spectrogram)
        report = json.loads(result.stdout)
        self.assertEqual(report["errors"], [], result.stderr)
        matched = {e["time"]: e["onset_s"] for e in report["sync"]["events"]}
        for at in (0.5, 1.5, 2.5):
            self.assertIsNotNone(matched[at], report["sync"])
            self.assertLess(abs(matched[at] - at), 0.03)
        self.assertIsNone(matched[2.9])
        self.assertTrue(any("below 60 Hz" in w for w in report["warnings"]))
        self.assertLess(report["segments"][0]["rms_dbfs"], -90)
        self.assertTrue(spectrogram.is_file())

    def test_missing_file_is_an_error(self):
        result = run_py("audio_check.py", self.workspace / "nope.wav")
        self.assertEqual(result.returncode, 1)

    def test_symbols_in_paths_print_as_utf8(self):
        result = run_py("audio_check.py", self.workspace / "señal→gris·.wav")   # → is not in cp1252
        self.assertEqual(json.loads(result.stdout)["errors"], ["source file is missing"], result.stderr)

    @staticmethod
    def write(path, left, right, sr=48000):
        pcm = np.round(np.column_stack([left, right]) * 32767).astype("<i2")
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(2), handle.setsampwidth(2), handle.setframerate(sr)
            handle.writeframes(pcm.tobytes())

    def test_sound_may_lag_more_than_lead_and_array_hits_work(self):
        sr = 48000
        signal = np.zeros(sr * 3)
        for at in (0.6, 1.6):
            i, k = int(at * sr), np.arange(2400)
            signal[i:i + 2400] += 0.5 * np.sin(2 * np.pi * 2000 * k / sr) * np.exp(-k / 300)
        wav, plan = self.workspace / "lag.wav", self.workspace / "lag-plan.json"
        self.write(wav, signal, signal)
        # 0.6 s is 100 ms after its event (accepted, noted); 1.6 s is 60 ms before its event (rejected: > 45 ms).
        plan.write_text(json.dumps({"hits": [[0.5, 1.0], [1.66, 1.0]]}), encoding="utf-8")
        report = json.loads(run_py("audio_check.py", wav, "--plan", plan, "--onsets", "2").stdout)
        self.assertEqual(report["errors"], [])
        events = {round(e["time"], 2): e for e in report["sync"]["events"]}
        self.assertIsNotNone(events[0.5]["onset_s"], report["sync"])
        self.assertIsNone(events[1.66]["onset_s"], report["sync"])
        self.assertTrue(any("after the image" in n for n in report["notes"]), report["notes"])
        symmetric = json.loads(run_py("audio_check.py", wav, "--plan", plan, "--onsets", "2", "--tolerance", "0.07").stdout)
        self.assertIsNotNone({round(e["time"], 2): e for e in symmetric["sync"]["events"]}[1.66]["onset_s"])

    def test_silence_never_matches_an_event(self):
        sr = 48000
        signal = np.zeros(sr * 4)
        i, k = sr, np.arange(2400)                                   # one real hit at 1.0 s, silence elsewhere
        signal[i:i + 2400] += 0.5 * np.sin(2 * np.pi * 2000 * k / sr) * np.exp(-k / 300)
        wav = self.workspace / "one-hit.wav"
        self.write(wav, signal, signal)
        report = json.loads(run_py("audio_check.py", wav, "--events", "1.0,2.0,3.0").stdout)
        matched = {e["time"]: e["onset_s"] for e in report["sync"]["events"]}
        self.assertIsNotNone(matched[1.0], report["sync"])
        self.assertIsNone(matched[2.0], report["sync"])
        self.assertIsNone(matched[3.0], report["sync"])

    def test_matching_takes_the_closest_pair_first(self):
        sys.path.insert(0, str(SCRIPTS))
        from audio_check import match_events
        result = match_events([1.09], [{"time": 1.0, "role": "a"}, {"time": 1.1, "role": "b"}], .045, .125)
        rows = {r["role"]: r["onset_s"] for r in result["events"]}
        self.assertEqual(rows, {"a": None, "b": 1.09})   # 1.09 belongs to b (10 ms), not to a (90 ms)

    def test_out_of_phase_stereo_is_flagged(self):
        sr = 48000
        t = np.arange(sr * 2) / sr
        tone = 0.3 * np.sin(2 * np.pi * 440 * t) * np.minimum(1, np.minimum(t, 2 - t) / 0.01)
        wav = self.workspace / "phase.wav"
        self.write(wav, tone, -0.9 * tone)
        report = json.loads(run_py("audio_check.py", wav).stdout)
        self.assertLess(report["stereo_correlation"], 0)
        self.assertGreater(report["mono_fold_loss_db"], 10)
        self.assertTrue(any("correlation" in w for w in report["warnings"]), report["warnings"])
        self.assertTrue(any("mono loses" in w for w in report["warnings"]), report["warnings"])


class ContactSheet(Workspace):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.frames = cls.workspace / "frames"
        cls.frames.mkdir()
        for t in (0.25, 1.0, 10.5):
            Image.new("RGB", (108, 192), (int(t * 20), 40, 90)).save(cls.frames / f"t{t:.3f}.jpg")

    def test_sheet_and_crop(self):
        out = self.workspace / "sheet.jpg"
        result = run_py("contact_sheet.py", self.frames, "--out", out, "--cols", "2", "--tile", "54")
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(out) as sheet:
            self.assertEqual(sheet.size, (108, 2 * (96 + 20)))
        crop = self.workspace / "crop.jpg"
        result = run_py("contact_sheet.py", self.frames, "--out", crop, "--crop", "10,10,40,40", "--tile", "80", "--cols", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        with Image.open(crop) as cut:
            self.assertEqual(cut.size, (240, 100))

    def test_refusals(self):
        self.assertEqual(run_py("contact_sheet.py", self.frames, "--out", self.frames / "x.jpg").returncode, 1)
        self.assertEqual(run_py("contact_sheet.py", self.frames, "--out", self.workspace / "y.jpg",
                                "--crop", "100,100,50,50").returncode, 1)


class Cadence(Workspace):
    def test_constant_cadence_is_reported(self):
        video = self.workspace / "cfr.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=30:duration=1",
                        "-pix_fmt", "yuv420p", str(video)], check=True, capture_output=True)
        result = run_py("verify_export.py", video, "--fps", "30", "--duration", "1", "--audio", "forbidden", "--require-cfr")
        report = json.loads(result.stdout)
        self.assertEqual(report["errors"], [], report)
        self.assertTrue(report["cadence"]["constant"])
        self.assertEqual(report["cadence"]["timestamps"], 30)


FIXTURE = """<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;background:#000}</style></head>
<body><canvas id="c" width="128" height="228"></canvas><script>
const c=document.getElementById('c').getContext('2d');
window.motionConfig={width:128,height:228,fps:12,frames:12,duration:1};
window.seek=(t)=>{c.fillStyle='#111';c.fillRect(0,0,128,228);c.fillStyle='#ff422e';
  const jitter=%s;c.fillRect(10+100*t+jitter,100,18,18)};
window.motionReady=Promise.resolve();window.motionInitialized=true;window.seek(0);
</script></body></html>"""


class CaptureKit(Workspace):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        probe = subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True, text=True)
        if probe.returncode != 0:
            raise unittest.SkipTest("Playwright not available for the capture kit")
        cls.good = cls.workspace / "good"
        cls.bad = cls.workspace / "bad"
        for folder, jitter in ((cls.good, "0"), (cls.bad, "Math.random()*40")):
            folder.mkdir()
            (folder / "index.html").write_text(FIXTURE % jitter, encoding="utf-8")

    def node(self, script, *args):
        return subprocess.run(["node", str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True,
                              encoding="utf-8", timeout=180)

    def test_samples_determinism_and_render(self):
        out = self.workspace / "samples"
        result = self.node("sample_frames.mjs", "--root", self.good, "--out", out, "--every", "0.5", "--times", "0.9")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in out.glob("*.jpg")), ["t0.250.jpg", "t0.750.jpg", "t0.900.jpg"])
        again = self.node("sample_frames.mjs", "--root", self.good, "--out", out, "--times", "0.1")
        self.assertNotEqual(again.returncode, 0, "a non-empty output folder must be refused")

        good = self.node("determinism_check.mjs", "--root", self.good)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertTrue(json.loads(good.stdout)["deterministic"])
        bad = self.node("determinism_check.mjs", "--root", self.bad)
        self.assertEqual(bad.returncode, 1)
        self.assertFalse(json.loads(bad.stdout)["deterministic"])

        video = self.workspace / "render" / "clip.mp4"
        render = self.node("render_stream.mjs", "--root", self.good, "--out", video, "--no-audio", "--min-free-gb", "0")
        self.assertEqual(render.returncode, 0, render.stderr)
        check = json.loads(run_py("verify_export.py", video, "--width", "128", "--height", "228", "--fps", "12",
                                  "--duration", "1", "--audio", "forbidden", "--require-cfr").stdout)
        self.assertEqual(check["errors"], [], check)
        self.assertTrue((video.parent / "clip.render-report.json").is_file())
        refused = self.node("render_stream.mjs", "--root", self.good, "--out", video, "--no-audio")
        self.assertEqual(refused.returncode, 2, "an existing output must never be overwritten")


if __name__ == "__main__":
    unittest.main()
