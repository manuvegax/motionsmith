"""Tests for scripts/captions.py: SRT, WebVTT and JSON input, line wrapping, reading speed, and the command line."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import captions as C  # noqa: E402

SRT = """1
00:00:01,000 --> 00:00:03,500
<i>Hello</i> everyone,
today we talk about rhythm

2
00:00:04,000 --> 00:00:05,000
Thanks.
"""

VTT = """WEBVTT

NOTE a comment that is not a cue

1
00:00:00.000 --> 00:00:02.000 line:0 position:50%
<00:00.000><c>one</c> <00:00.400><c>two</c> <00:01.200><c>three</c>
"""


class ParseTests(unittest.TestCase):
    def test_time_forms(self):
        self.assertEqual(C.parse_time("1.5"), 1.5)
        self.assertEqual(C.parse_time("01:02.5"), 62.5)
        self.assertEqual(C.parse_time("01:00:00,250"), 3600.25)
        with self.assertRaisesRegex(ValueError, "not a time"):
            C.parse_time("soon")

    def test_srt_times_text_and_markup(self):
        cues = C.parse_srt(SRT)
        self.assertEqual(len(cues), 2)
        self.assertEqual((cues[0].start, cues[0].end), (1.0, 3.5))
        self.assertEqual(cues[0].text, "Hello everyone, today we talk about rhythm")
        self.assertIsNone(cues[0].words)

    def test_vtt_needs_its_header(self):
        with self.assertRaisesRegex(ValueError, "WEBVTT"):
            C.parse_vtt(SRT)

    def test_a_cue_without_an_end_time_is_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, "start and an end"):
            C.parse_srt("1\n00:00:01,000 --> \nhello\n")
        with self.assertRaisesRegex(ValueError, "start and an end"):
            C.parse_vtt("WEBVTT\n\n00:00:01.000 -->\nhello\n")

    def test_a_vtt_cue_right_after_the_header_line_is_kept(self):
        cues = C.parse_vtt("WEBVTT\n00:00:00.500 --> 00:00:02.000\nfirst line\n\n00:00:02.000 --> 00:00:03.000\nsecond\n")
        self.assertEqual([c.text for c in cues], ["first line", "second"])

    def test_vtt_word_timings_come_from_inline_tags(self):
        cue = C.parse_vtt(VTT)[0]
        self.assertEqual([w.text for w in cue.words], ["one", "two", "three"])
        self.assertEqual([(w.start, w.end) for w in cue.words], [(0.0, 0.4), (0.4, 1.2), (1.2, 2.0)])
        self.assertTrue(all(w.source for w in cue.words))
        self.assertEqual(cue.text, "one two three")

    def test_json_accepts_cues_segments_and_whisper_words(self):
        data = {"segments": [{"start": 0.0, "end": 2.0, "words": [
            {"word": " hello", "start": 0.0, "end": 0.8}, {"word": " world", "start": 0.9, "end": 2.0}]}]}
        cue = C.parse_json(data)[0]
        self.assertEqual([w.text for w in cue.words], ["hello", "world"])
        self.assertEqual(cue.text, "hello world")
        plain = C.parse_json([{"start": "00:00:01,500", "end": "00:00:02.250", "text": "x"}])[0]
        self.assertEqual((plain.start, plain.end), (1.5, 2.25))
        with self.assertRaisesRegex(ValueError, "start and end"):
            C.parse_json([{"text": "x"}])


class LineTests(unittest.TestCase):
    def test_lines_respect_max_chars_and_keep_every_word_in_order(self):
        text = "one two three four five six seven eight nine ten"
        lines, warnings = C.build([C.Cue(0.0, 10.0, text)], 14, 15.0, 0.6)
        self.assertTrue(all(line["chars"] <= 14 for line in lines), lines)
        self.assertEqual(" ".join(line["text"] for line in lines), text)
        self.assertEqual(warnings, [])

    def test_a_word_over_the_limit_keeps_its_own_line_and_is_reported(self):
        lines, warnings = C.build([C.Cue(0.0, 4.0, "short extraordinarily long")], 10, 15.0, 0.6)
        self.assertIn("extraordinarily", [line["text"] for line in lines])
        self.assertTrue(any("over the limit" in w for w in warnings), warnings)

    def test_estimated_word_times_cover_the_cue_in_proportion_to_length(self):
        words = C.cue_words(C.Cue(1.0, 3.0, "one two three"))
        self.assertAlmostEqual(words[0].start, 1.0)
        self.assertAlmostEqual(words[-1].end, 3.0)
        # "one", "two" and "three" weigh 4, 4 and 6 (length plus the space): 14 units share the 2 s.
        self.assertAlmostEqual(words[0].end - words[0].start, 2 * 4 / 14, places=9)
        self.assertFalse(any(w.source for w in words))

    def test_source_timings_close_a_line_that_reads_too_fast(self):
        words = [C.Word("one", 0.0, 0.2, True), C.Word("two", 0.2, 0.4, True),
                 C.Word("three", 0.4, 0.5, True), C.Word("four", 0.5, 0.6, True)]
        lines, _ = C.build([C.Cue(0.0, 0.6, "one two three four", words)], 40, 15.0, 0.6)
        self.assertEqual([line["text"] for line in lines], ["one two", "three four"])
        self.assertEqual({line["timing"] for line in lines}, {"source"})

    def test_estimated_timings_never_split_by_speed(self):
        lines, _ = C.build([C.Cue(0.0, 1.0, "one two three four")], 40, 15.0, 0.6)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["timing"], "estimated")

    def test_a_short_line_stays_on_screen_until_its_reading_time_without_overlap(self):
        cues = [C.Cue(0.0, 0.2, "hello"), C.Cue(0.3, 2.0, "goodbye")]
        lines, _ = C.build(cues, 22, 15.0, 0.6)
        self.assertEqual(lines[0]["end"], 0.3)
        self.assertEqual(lines[1]["start"], 0.3)

    def test_lines_are_ordered_and_never_overlap(self):
        lines, _ = C.build(C.parse_srt(SRT), 22, 15.0, 0.6)
        for before, after in zip(lines, lines[1:]):
            self.assertLessEqual(before["start"], after["start"])
            self.assertLessEqual(before["end"], after["start"] + 1e-9)

    def test_presets_set_line_length_and_speed(self):
        self.assertEqual(C.PRESETS["reel"], {"max_chars": 22, "cps": 15.0})
        self.assertEqual(C.PRESETS["subtitle"]["max_chars"], 42)


class CommandLineTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(ROOT / "scripts" / "captions.py"), *args],
                              capture_output=True, text=True, encoding="utf-8")

    def test_writes_json_and_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "talk.srt"
            source.write_text(SRT, encoding="utf-8")
            out = Path(folder) / "captions.json"
            result = self.run_cli(str(source), "--out", str(out), "--preset", "subtitle")
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(document["version"], 1)
            self.assertEqual(document["format"]["max_chars"], 42)
            self.assertTrue(all(line["words"] for line in document["lines"]))
            again = self.run_cli(str(source), "--out", str(out))
            self.assertEqual(again.returncode, 2)
            self.assertIn("--replace", again.stderr)
            self.assertEqual(self.run_cli(str(source), "--out", str(out), "--replace").returncode, 0)

    def test_unknown_extension_needs_an_explicit_format(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "talk.txt"
            source.write_text(SRT, encoding="utf-8")
            result = self.run_cli(str(source), "--out", str(Path(folder) / "c.json"))
            self.assertEqual(result.returncode, 2)
            self.assertIn("--format", result.stderr)


if __name__ == "__main__":
    unittest.main()
