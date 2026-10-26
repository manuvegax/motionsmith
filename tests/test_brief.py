"""The motion brief (brief.py), the brief fields of the plan, per-beat sampling and the loop check."""
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

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import brief  # noqa: E402
import loop_check  # noqa: E402
from validate_plan import validate  # noqa: E402

KEEP = os.environ.get("MOTION_KEEP_TEST_EVIDENCE") == "1"

GOOD = """
<inputs>Ask for the copy.</inputs>
<direction>
concept: the phone screen becomes a window that closes
recurring element: the rounded rectangle
banned:
- glows -> light only where something emits it
- crossfades -> every scene grows out of the last
- particle bursts -> motion from an element on screen
- bouncy easing -> overshoot only on the hero
- anything that looks like a template
ending: the window shut, one line under it
</direction>
<structure>
duration: 15 s
tempo: 120 BPM
meter: 4/4
bars: 7.5
loop: yes
</structure>
<build>Review one frame per beat before the full render.</build>
<gotchas>Text scaled up blurs.</gotchas>
<start>Show the concept and the beat grid first.</start>
"""


def run_py(script: str, *args: object) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def browser_available() -> bool:
    if not shutil.which("node"):
        return False
    return subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True).returncode == 0


class BriefCheckTests(unittest.TestCase):
    def test_good_brief_passes_with_its_decisions(self):
        report = brief.check(GOOD)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["brief"]["concept"], "the phone screen becomes a window that closes")
        self.assertEqual(len(report["brief"]["banned"]), 5)
        self.assertEqual(report["brief"]["banned"][0], {"avoid": "glows", "instead": "light only where something emits it"})
        self.assertEqual(report["brief"]["grid"]["bars"], 7.5)

    def test_one_line_prompt_fails_on_every_missing_decision(self):
        report = brief.check("Make a dynamic 15-second motion graphics video. Go all out.")
        text = " ".join(report["errors"])
        for needle in ("<direction>", "<structure>", "concept", "banned", "duration", "tempo"):
            self.assertIn(needle, text)

    def test_bar_arithmetic_disagreement_is_an_error(self):
        report = brief.check(GOOD.replace("bars: 7.5", "bars: 8"))
        self.assertTrue(any("hold 7.5" in e for e in report["errors"]), report["errors"])

    def test_partial_bar_without_a_statement_warns(self):
        report = brief.check(GOOD.replace("bars: 7.5\n", ""))
        self.assertEqual(report["errors"], [])
        self.assertTrue(any("7.5 bars is not a whole number" in w for w in report["warnings"]))

    def test_bans_without_alternative_and_without_template_catch_all_warn(self):
        text = GOOD.replace("- glows -> light only where something emits it", "- glows").replace(
            "- anything that looks like a template\n", "")
        warnings = " ".join(brief.check(text)["warnings"])
        self.assertIn("without an alternative", warnings)
        self.assertIn("looks like a template", warnings)

    def test_explainer_needs_audience_and_facts(self):
        report = brief.check(GOOD.replace("concept:", "kind: explainer\nconcept:"))
        text = " ".join(report["errors"])
        self.assertIn("audience", text)
        self.assertIn("facts", text)

    def test_spanish_keys_and_free_tempo(self):
        text = (GOOD.replace("concept:", "concepto:").replace("banned:", "prohibido:").replace("duration: 15 s", "duración: 0:20")
                .replace("tempo: 120 BPM", "tempo: voz").replace("bars: 7.5\n", "").replace("loop: yes", "bucle: no"))
        report = brief.check(text)
        self.assertEqual(report["errors"], [])
        self.assertNotIn("grid", report["brief"])

    def test_unfilled_placeholder_is_an_error(self):
        report = brief.check(GOOD.replace("the phone screen becomes a window that closes", "{{concept}}"))
        self.assertTrue(any("placeholders: concept" in e for e in report["errors"]))

    def test_grid_frames_and_downbeats(self):
        g = brief.grid(brief.Fraction(120), brief.Fraction(15), 4, brief.Fraction(0), 60)
        self.assertEqual(len(g["beats"]), 30)
        self.assertEqual(g["beats"][3]["frame"], 90)
        self.assertEqual(sum(b["downbeat"] for b in g["beats"]), 8)
        self.assertFalse(g["whole_bars"])
        g = brief.grid(brief.Fraction(128), brief.Fraction(15), 4, brief.Fraction(0), 60)
        self.assertTrue(g["whole_bars"])


class BriefCliTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="motion-brief-tests-"))

    def tearDown(self):
        if not KEEP:
            shutil.rmtree(self.workspace, ignore_errors=True)

    def test_every_template_writes_a_brief_that_passes_clean(self):
        names = list(brief.templates())
        self.assertEqual(set(names), {"reel-hook", "showreel", "launch", "explainer", "loop"})
        for name in names:
            with self.subTest(name=name):
                dest = self.workspace / f"{name}.md"
                self.assertEqual(run_py("brief.py", "new", dest, "--template", name).returncode, 0)
                result = run_py("brief.py", "check", dest)
                report = json.loads(result.stdout)
                self.assertEqual(result.returncode, 0, report)
                self.assertEqual(report["errors"], [])
                self.assertEqual(report["warnings"], [], report["warnings"])

    def test_new_sets_values_and_refuses_to_overwrite(self):
        dest = self.workspace / "reel.md"
        result = run_py("brief.py", "new", dest, "--template", "reel-hook", "--set", "duration=9.6", "--set", "bpm=100",
                        "--set", "concept=the word FOCUS burns down to its O")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = dest.read_text(encoding="utf-8")
        self.assertIn("concept: the word FOCUS burns down to its O", text)
        self.assertIn("duration: 9.6 s", text)
        self.assertEqual(brief.check(text)["brief"]["grid"]["bars"], 4.0)
        self.assertEqual(run_py("brief.py", "new", dest, "--template", "reel-hook").returncode, 2)

    def test_new_refuses_to_write_inside_the_skill(self):
        result = run_py("brief.py", "new", SKILL / "work-should-not-exist" / "b.md", "--template", "loop")
        self.assertEqual(result.returncode, 2)
        self.assertFalse((SKILL / "work-should-not-exist").exists())

    def test_plan_copies_decisions_and_writes_bar_hits(self):
        (self.workspace / "brief.md").write_text(GOOD, encoding="utf-8")
        piece = self.workspace / "piece"
        self.assertEqual(run_py("new_piece.py", piece, "--format", "square", "--duration", "15", "--fps", "30").returncode, 0)
        plan_path = piece / "plan.json"
        result = run_py("brief.py", "plan", self.workspace / "brief.md", "--plan", plan_path, "--replace-hits")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(plan["bpm"], 120)
        self.assertEqual(plan["meter"], 4)
        self.assertIs(plan["loop"], True)
        self.assertEqual(len(plan["banned"]), 5)
        self.assertEqual([h["time"] for h in plan["hits"]], [0, 2, 4, 6, 8, 10, 12, 14])
        self.assertEqual(validate(plan, require_brief=True), [])

    def test_plan_warns_when_durations_disagree(self):
        (self.workspace / "brief.md").write_text(GOOD, encoding="utf-8")
        piece = self.workspace / "piece"
        self.assertEqual(run_py("new_piece.py", piece, "--format", "square", "--duration", "4").returncode, 0)
        out = json.loads(run_py("brief.py", "plan", self.workspace / "brief.md", "--plan", piece / "plan.json").stdout)
        self.assertTrue(any("--duration 15" in n for n in out["notes"]), out)

    def test_grid_cli(self):
        result = run_py("brief.py", "grid", "--bpm", "90", "--duration", "8", "--json")
        g = json.loads(result.stdout)
        self.assertEqual(g["beat_frames"], 40.0)
        self.assertEqual(run_py("brief.py", "grid", "--bpm", "0", "--duration", "8").returncode, 2)

    def test_plan_keeps_recipe_hits_and_flags_off_grid_ones(self):
        (self.workspace / "brief.md").write_text(GOOD.replace("duration: 15 s", "duration: 4 s").replace("bars: 7.5\n", ""), encoding="utf-8")
        piece = self.workspace / "quote"
        self.assertEqual(run_py("new_piece.py", piece, "--recipe", "kinetic-quote", "--duration", "4", "--fps", "30").returncode, 0)
        before = [h["role"] for h in json.loads((piece / "plan.json").read_text(encoding="utf-8"))["hits"]]
        out = json.loads(run_py("brief.py", "plan", self.workspace / "brief.md", "--plan", piece / "plan.json").stdout)
        plan = json.loads((piece / "plan.json").read_text(encoding="utf-8"))
        roles = [h["role"] for h in plan["hits"]]
        for role in before:
            self.assertIn(role, roles)
        self.assertEqual([h["time"] for h in plan["hits"]], sorted(h["time"] for h in plan["hits"]))
        self.assertEqual(out["errors"], [])
        self.assertTrue(any("added" in n for n in out["notes"]))


class PlanBriefFieldTests(unittest.TestCase):
    def plan(self, **extra):
        base = {"schema_version": 1, "width": 1080, "height": 1080, "fps": 30, "duration_frames": 60, "mode": "kinetic",
                "audio": "optional", "safe_area": {"x": 0, "y": 0, "width": 1080, "height": 1080},
                "scenes": [{"id": "a", "start_frame": 0, "end_frame": 60, "intent": "i", "action": "a", "text": "",
                            "transition": {"kind": "end"}}]}
        base.update(extra)
        return base

    def test_fields_are_checked_when_present(self):
        self.assertEqual(validate(self.plan()), [])
        errors = " ".join(validate(self.plan(banned=[{"instead": "x"}], meter=0, loop="yes", concept="")))
        for needle in ("banned[0]", "meter", "loop", "concept"):
            self.assertIn(needle, errors)
        self.assertIn("meter needs bpm", " ".join(validate(self.plan(meter=4))))

    def test_require_brief(self):
        errors = " ".join(validate(self.plan(), require_brief=True))
        for needle in ("concept", "banned", "loop"):
            self.assertIn(needle, errors)
        ok = self.plan(concept="c", loop=False, banned=[{"avoid": a, "instead": "b"} for a in "xyz"])
        self.assertEqual(validate(ok, require_brief=True), [])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg and ffprobe encode the fixtures")
class LoopCheckTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="motion-loop-tests-"))

    def tearDown(self):
        if not KEEP:
            shutil.rmtree(self.workspace, ignore_errors=True)

    def encode(self, name: str, position) -> Path:
        """A white disc on black moved by position(i) -> (x, y), 2 s at 30 fps, encoded losslessly enough."""
        import numpy as np
        w, h, n = 160, 160, 60
        yy, xx = np.mgrid[0:h, 0:w]
        frames = []
        for i in range(n):
            x, y = position(i, n)
            frames.append(((xx - x) ** 2 + (yy - y) ** 2 < 18 ** 2).astype(np.uint8) * 255)
        out = self.workspace / name
        subprocess.run(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", "30",
                        "-i", "-", "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(out)],
                       input=b"".join(f.tobytes() for f in frames), check=True, capture_output=True)
        return out

    def test_circular_loop_passes_and_linear_travel_fails(self):
        loop = self.encode("loop.mp4", lambda i, n: (80 + 40 * math.cos(2 * math.pi * i / n), 80 + 40 * math.sin(2 * math.pi * i / n)))
        travel = self.encode("travel.mp4", lambda i, n: (30 + 100 * i / (n - 1), 80))
        good = run_py("loop_check.py", loop)
        self.assertEqual(good.returncode, 0, good.stdout)
        self.assertLess(json.loads(good.stdout)["seam_ratio"], 2.0)
        bad = run_py("loop_check.py", travel)
        self.assertEqual(bad.returncode, 1, bad.stdout)
        self.assertTrue(json.loads(bad.stdout)["errors"])

    def test_repeated_first_frame_is_flagged(self):
        stutter = self.encode("stutter.mp4", lambda i, n: (80 + 40 * math.cos(2 * math.pi * i / (n - 1)), 80 + 40 * math.sin(2 * math.pi * i / (n - 1))))
        report = json.loads(run_py("loop_check.py", stutter).stdout)
        self.assertTrue(any("first frame twice" in w or "same frame twice" in w for w in report["warnings"]), report)

    def test_measure_on_still_frames(self):
        import numpy as np
        still = np.zeros((10, 8, 8), dtype=np.float32)
        self.assertTrue(loop_check.measure(still, 30)["pass"])
        still[-1] += 20
        self.assertFalse(loop_check.measure(still, 30)["pass"])


@unittest.skipUnless(browser_available(), "node + Playwright drive the browser")
class BeatSamplingTests(unittest.TestCase):
    def test_beats_bars_and_hits_come_from_the_plan(self):
        workspace = Path(tempfile.mkdtemp(prefix="motion-beats-tests-"))
        try:
            piece = workspace / "piece"
            self.assertEqual(run_py("new_piece.py", piece, "--format", "square", "--duration", "4", "--fps", "30").returncode, 0)
            plan = json.loads((piece / "plan.json").read_text(encoding="utf-8"))
            plan.update(bpm=120, meter=4)
            (piece / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            for flag, expected in (("--beats", 8), ("--bars", 2)):
                out = workspace / flag.strip("-")
                result = subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(piece), "--out", str(out),
                                         flag, "--noblur"], capture_output=True, text=True, timeout=300)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(len(list(out.glob("t*.jpg"))), expected)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
