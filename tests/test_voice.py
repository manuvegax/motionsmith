"""The voice as the clock: voice_plan.py, the voiceover cue, balanced captions, the voice-over brief and the per-phrase
review. The "voice" is synthetic (tone bursts for words, silences for pauses), so the tests run anywhere."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

import numpy as np

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import brief  # noqa: E402
import captions  # noqa: E402
import voice_plan  # noqa: E402
from validate_plan import validate  # noqa: E402

KEEP = os.environ.get("MOTION_KEEP_TEST_EVIDENCE") == "1"
FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))

# Three phrases. The last word of the first phrase is louder and longer; "alerta" is marked in the script.
SCRIPT = """| voz | pantalla |
|---|---|
| Tu cerebro no quiere que seas feliz. | La palabra se tacha |
| Quiere que sobrevivas, y para eso te mantiene *alerta*. | Un ojo se abre |
| Hoy apaga una sola. | Una luz se apaga |
"""
PHRASES = [
    ["Tu", "cerebro", "no", "quiere", "que", "seas", "feliz"],
    ["Quiere", "que", "sobrevivas", "y", "para", "eso", "te", "mantiene", "alerta"],
    ["Hoy", "apaga", "una", "sola"],
]


def run_py(script: str, *args: object) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def browser_available() -> bool:
    if not shutil.which("node"):
        return False
    return subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True).returncode == 0


def synth_voice(path: Path, *, pause: float = .6, gap: float = .05, sr: int = 16000) -> list[dict]:
    """Write a mono WAV of tone bursts (one per word) and return the word timings."""
    t, words, chunks = .2, [], [np.zeros(int(.2 * sr))]
    for p, phrase in enumerate(PHRASES):
        for k, text in enumerate(phrase):
            length = .05 * len(text) + .08   # about 2.6 words per second with the gaps
            amp = .25
            if p == 0 and k == len(phrase) - 1:
                length, amp = length * 1.5, .5      # the stressed last word: longer and louder
            x = np.arange(int(length * sr)) / sr
            burst = amp * np.sin(2 * np.pi * (180 + 20 * k) * x) * np.sin(np.pi * x / length)
            chunks += [burst, np.zeros(int(gap * sr))]
            words.append({"text": text, "start": round(t, 3), "end": round(t + length, 3)})
            t += length + gap
        chunks.append(np.zeros(int(pause * sr)))
        t += pause
    audio = np.concatenate(chunks)
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sr)
        out.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    return words


class CaptionBalanceTests(unittest.TestCase):
    def words(self, text: str) -> list:
        return [captions.Word(w, i * .3, i * .3 + .25, True) for i, w in enumerate(text.split())]

    def test_lines_never_end_on_a_weak_word_and_no_lone_short_word(self):
        warnings = []
        lines = captions.wrap_balanced(self.words("Por eso el teléfono te atrapa cada notificación es una pequeña alarma"), 24, warnings)
        texts = [l.text for l in lines]
        for line in texts[:-1]:
            self.assertNotIn(line.split()[-1].lower(), captions.WEAK_ENDINGS, texts)
        self.assertTrue(all(len(l) <= 24 for l in texts), texts)
        self.assertFalse(any(len(l.split()) == 1 and len(l) < 9 for l in texts), texts)

    def test_build_balanced_keeps_word_times(self):
        cue = captions.Cue(0, 3, "Lo digo casi con ternura", self.words("Lo digo casi con ternura"))
        lines, _ = captions.build([cue], 14, 22, .6, balanced=True)
        self.assertEqual(" ".join(l["text"] for l in lines), "Lo digo casi con ternura")
        self.assertNotEqual(lines[0]["text"].split()[-1], "con")
        self.assertEqual(lines[0]["words"][0]["start"], 0)


class LoadWordsTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="motion-voice-load-"))

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def write(self, name: str, data) -> Path:
        path = self.workspace / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_elevenlabs_whisper_and_onset_only_lists(self):
        eleven = self.write("e.json", {"text": "hola mundo", "words": [
            {"text": "hola", "start": .1, "end": .4, "type": "word"}, {"text": " ", "start": .4, "end": .5, "type": "spacing"},
            {"text": "mundo", "start": .5, "end": .9, "type": "word"}]})
        whisper = self.write("w.json", {"segments": [{"start": 0, "end": 1, "text": "hola mundo",
                                                      "words": [{"word": " hola", "start": .1, "end": .4}, {"word": " mundo", "start": .5, "end": .9}]}]})
        onsets = self.write("o.json", [{"text": "hola", "start": .1}, {"text": "mundo", "start": .5}])
        for path in (eleven, whisper, onsets):
            with self.subTest(path=path.name):
                words = voice_plan.load_words(path)
                self.assertEqual([w.text for w in words], ["hola", "mundo"])
                self.assertAlmostEqual(words[0].start, .1)
                self.assertLess(words[0].end, words[1].start + 1e-9)

    def test_script_tokens_take_the_voice_column_and_marks(self):
        tokens = voice_plan.script_tokens(SCRIPT)
        self.assertEqual(tokens[0]["text"], "Tu")
        self.assertNotIn("pantalla", [t["norm"] for t in tokens])
        self.assertNotIn("tacha", [t["norm"] for t in tokens])
        self.assertTrue(next(t for t in tokens if t["norm"] == "alerta")["forced"])


@unittest.skipUnless(FFMPEG, "ffmpeg decodes the voice")
class VoicePlanTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="motion-voice-"))
        self.piece = self.workspace / "piece"
        result = run_py("new_piece.py", self.piece, "--recipe", "voice-captions", "--format", "reel", "--fps", "30")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (self.piece / "assets").mkdir(exist_ok=True)
        self.voice = self.piece / "assets" / "voice.wav"
        self.words = synth_voice(self.voice)
        (self.workspace / "words.json").write_text(json.dumps({"words": self.words}), encoding="utf-8")
        (self.workspace / "script.md").write_text(SCRIPT, encoding="utf-8")

    def tearDown(self):
        if not KEEP:
            shutil.rmtree(self.workspace, ignore_errors=True)

    def plan(self, *extra):
        return run_py("voice_plan.py", "--plan", self.piece / "plan.json", "--voice", self.voice,
                      "--words", self.workspace / "words.json", "--script", self.workspace / "script.md",
                      "--brief", self.workspace / "script.md", *extra)

    def test_voice_becomes_the_plan(self):
        result = self.plan()
        report = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, report)
        plan = json.loads((self.piece / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(validate(plan), [])
        self.assertEqual(len(plan["scenes"]), 3)
        self.assertEqual([s["action"] for s in plan["scenes"]], ["La palabra se tacha", "Un ojo se abre", "Una luz se apaga"])
        self.assertTrue(plan["scenes"][0]["text"].endswith("feliz."))   # punctuation restored from the script
        # Cuts lead the phrase's first word by two frames.
        second = self.words[len(PHRASES[0])]["start"] + .1
        self.assertAlmostEqual(plan["cuts"][0], round(round((second - 2 / 30) * 30) / 30, 4), places=3)
        emphasis = [h["role"] for h in plan["hits"] if h["role"].startswith("emphasis")]
        self.assertEqual(emphasis, ["emphasis: feliz", "emphasis: alerta", "emphasis: sola"])
        self.assertEqual(plan["audio"], "required")
        self.assertEqual(plan["voice"]["file"], "assets/voice.wav")
        duration = plan["duration_frames"] / 30
        self.assertAlmostEqual(duration, self.words[-1]["end"] + .1 + .8, delta=.05)
        voice = json.loads((self.piece / "voice.json").read_text(encoding="utf-8"))
        self.assertEqual(len(voice["words"]), sum(map(len, PHRASES)))
        self.assertEqual(len(voice["phrases"]), 3)
        self.assertGreaterEqual(len(voice["pauses"]), 2)
        levels = voice["levels"]["values"]
        self.assertEqual(len(levels), plan["duration_frames"])                       # one level per frame of the piece
        self.assertTrue(0 <= min(levels) and max(levels) <= 1 and max(levels) > .5)
        self.assertLess(levels[0], .2)   # silence before the voice
        caps = json.loads((self.piece / "captions.json").read_text(encoding="utf-8"))
        for line in caps["lines"][:-1]:
            self.assertNotIn(line["text"].split()[-1].lower().strip(".,"), captions.WEAK_ENDINGS, line["text"])
        cues = json.loads((self.piece / "cues.json").read_text(encoding="utf-8"))
        self.assertEqual([c["voice"] for c in cues["cues"]], ["voiceover"])

    def test_timings_from_another_take_stop_it(self):
        late = [{**w, "start": w["start"] + 30, "end": w["end"] + 30} for w in self.words]
        (self.workspace / "words.json").write_text(json.dumps({"words": late}), encoding="utf-8")
        result = self.plan()
        self.assertEqual(result.returncode, 2)
        self.assertIn("time base", result.stdout)
        self.assertFalse((self.piece / "voice.json").exists())

    def test_script_alone_gives_estimated_timing(self):
        result = run_py("voice_plan.py", "--plan", self.piece / "plan.json", "--voice", self.voice,
                        "--script", self.workspace / "script.md", "--dry-run")
        report = json.loads(result.stdout)
        self.assertEqual(report["timing"], "estimated")
        self.assertEqual(report["scenes"], 3)
        self.assertTrue(any("estimated" in w for w in report["warnings"]))
        self.assertEqual(report["written"], [])

    def test_long_phrase_splits_only_at_the_comma(self):
        result = self.plan("--max-scene", "1.5", "--dry-run")
        report = json.loads(result.stdout)
        self.assertEqual(report["errors"], [])
        # Phrase two splits at "sobrevivas," (its only comma); phrase one has no comma or pause and stays whole.
        self.assertEqual(report["scenes"], 4)

    def test_soundtrack_puts_the_voice_on_top(self):
        self.assertEqual(self.plan().returncode, 0)
        cues = json.loads((self.piece / "cues.json").read_text(encoding="utf-8"))
        cues["cues"].insert(0, {"voice": "bed", "levels": [[0, .1], [4, .1]]})
        (self.piece / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
        result = run_py("build_soundtrack.py", "--plan", self.piece / "plan.json", "--cues", self.piece / "cues.json",
                        "--out", self.piece / "assets" / "soundtrack.wav", "--report", self.piece / "sound.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads((self.piece / "sound.json").read_text(encoding="utf-8"))
        layer = report["layers"]["voiceover"][0]
        self.assertGreater(layer["voice_over_bed_db"], 10)
        self.assertTrue(all(h["voice"] == "tap" for h in report["hits"] if h["role"].startswith("emphasis")))
        self.assertFalse(any("emphasis" in w for w in report["warnings"]))

    def test_loud_bed_is_reported(self):
        self.assertEqual(self.plan().returncode, 0)
        cues = json.loads((self.piece / "cues.json").read_text(encoding="utf-8"))
        cues["cues"][0]["duck_db"] = 0
        cues["cues"][0]["gain_db"] = -18
        cues["cues"].insert(0, {"voice": "bed", "levels": [[0, .9], [4, .9]]})
        (self.piece / "cues.json").write_text(json.dumps(cues), encoding="utf-8")
        run_py("build_soundtrack.py", "--plan", self.piece / "plan.json", "--cues", self.piece / "cues.json",
               "--out", self.piece / "assets" / "soundtrack.wav", "--report", self.piece / "sound.json")
        report = json.loads((self.piece / "sound.json").read_text(encoding="utf-8"))
        self.assertTrue(any("dB over the rest" in w for w in report["warnings"]), report["warnings"])


class VoiceoverBriefTests(unittest.TestCase):
    def test_table_and_length(self):
        text = (SKILL / "templates" / "briefs" / "voiceover.md").read_text(encoding="utf-8")
        filled = brief.fill(text, {})
        report = brief.check(filled)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["brief"]["script"]["rows"], 3)
        long = brief.check(filled.replace("duration: 10 s", "duration: 40 s"))
        self.assertTrue(any("words" in w and "40 s" in w for w in long["warnings"]))
        no_table = "\n".join(l for l in filled.splitlines() if not l.startswith("|"))
        self.assertTrue(any("two-column" in e for e in brief.check(no_table)["errors"]))


@unittest.skipUnless(FFMPEG and browser_available(), "node + Playwright drive the browser")
class PhraseReviewTests(unittest.TestCase):
    def test_cuts_and_scenes_sampling(self):
        workspace = Path(tempfile.mkdtemp(prefix="motion-voice-review-"))
        try:
            piece = workspace / "piece"
            self.assertEqual(run_py("new_piece.py", piece, "--recipe", "voice-captions", "--format", "square", "--fps", "30").returncode, 0)
            (piece / "assets").mkdir(exist_ok=True)
            words = synth_voice(piece / "assets" / "voice.wav")
            (workspace / "w.json").write_text(json.dumps(words), encoding="utf-8")
            (workspace / "s.md").write_text(SCRIPT, encoding="utf-8")
            self.assertEqual(run_py("voice_plan.py", "--plan", piece / "plan.json", "--voice", piece / "assets" / "voice.wav",
                                    "--words", workspace / "w.json", "--script", workspace / "s.md").returncode, 0)
            for flag, expected in (("--cuts", 4), ("--scenes", 3)):   # two cuts, a frame on each side
                out = workspace / flag.strip("-")
                result = subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(piece), "--out", str(out),
                                         flag, "--noblur"], capture_output=True, text=True, timeout=300)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(list(out.glob("t*.jpg"))), expected)
            # The recipe read voice.json: the debug line says which words are on screen.
            dump = subprocess.run(["node", str(SCRIPTS / "dump_state.mjs"), "--root", str(piece), "--times", "1.2",
                                   "--expr", "s => s.debug"], capture_output=True, text=True, timeout=300)
            if dump.returncode == 0 and dump.stdout.strip():
                self.assertIn("Tu", dump.stdout)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
