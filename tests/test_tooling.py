"""Real CLI checks: plan boundaries, media expectations and complete decoding."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
KEEP = os.environ.get("MOTION_KEEP_TEST_EVIDENCE") == "1"   # default: clean temp folders (the disk runs near full)


class ToolingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-pro-tests-"))
        cls.video = cls.workspace / "fixture.mp4"
        cls.plan = {
            "schema_version": 1, "width": 320, "height": 568, "fps": 30,
            "duration_frames": 30, "mode": "editorial", "audio": "required",
            "safe_area": {"x": 20, "y": 60, "width": 280, "height": 420},
            "scenes": [
                {"id": "a", "start_frame": 0, "end_frame": 15, "intent": "show relation",
                 "action": "circle extends", "text": "A", "transition": {"kind": "morph", "carrier": "contour"}},
                {"id": "b", "start_frame": 15, "end_frame": 30, "intent": "resolve relation",
                 "action": "line settles", "text": "B", "transition": {"kind": "end", "carrier": ""}},
            ],
        }
        if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
            raise unittest.SkipTest("ffmpeg and ffprobe unavailable")
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-f", "lavfi", "-i",
                        "testsrc2=size=320x568:rate=30:duration=1", "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=48000:duration=1", "-c:v", "libx264",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
                        "-shortest", str(cls.video)], check=True, capture_output=True)
        cls.long_audio = cls.workspace / "long-audio.mkv"
        subprocess.run(["ffmpeg", "-v", "error", "-n", "-i", str(cls.video), "-f", "lavfi", "-i",
                        "sine=frequency=440:sample_rate=48000:duration=2", "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy", "-c:a", "aac", str(cls.long_audio)], check=True, capture_output=True)
        if KEEP:
            print(f"\nEvidence directory preserved: {cls.workspace}")

    @classmethod
    def tearDownClass(cls):
        if not KEEP:
            shutil.rmtree(cls.workspace, ignore_errors=True)

    def cli(self, script, *args):
        path = SKILL / "scripts" / script
        self.assertTrue(path.is_file(), f"Required CLI not implemented: {script}")
        return subprocess.run([sys.executable, str(path), *map(str, args)], capture_output=True, text=True, encoding="utf-8")

    def write_plan(self, value):
        path = self.workspace / f"{self.id().split('.')[-1]}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_accepts_contiguous_plan(self):
        result = self.cli("validate_plan.py", self.write_plan(self.plan))
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_rejects_gap(self):
        plan = copy.deepcopy(self.plan)
        plan["scenes"][1]["start_frame"] = 16
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("gap", result.stdout.lower())

    def test_rejects_morph_without_carrier(self):
        plan = copy.deepcopy(self.plan)
        plan["scenes"][0]["transition"]["carrier"] = ""
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("carrier", result.stdout.lower())

    def test_rejects_safe_area_outside_frame(self):
        plan = copy.deepcopy(self.plan)
        plan["safe_area"]["width"] = 400
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("safe_area", result.stdout)

    def test_rejects_end_before_duration(self):
        plan = copy.deepcopy(self.plan)
        plan["scenes"][-1]["end_frame"] = 29
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duration", result.stdout.lower())

    def test_edit_fields_are_checked_when_present(self):
        duration = self.plan["duration_frames"] / self.plan["fps"]
        good = copy.deepcopy(self.plan)
        good.update({"bpm": 120, "lead": 0, "cuts": [0, duration / 2], "captions": "captions.json"})
        self.assertEqual(self.cli("validate_plan.py", self.write_plan(good)).returncode, 0)
        inline = copy.deepcopy(self.plan)
        inline["captions"] = [{"text": "one", "start": 0, "end": duration / 3}, {"text": "two", "start": duration / 3, "end": duration / 2}]
        self.assertEqual(self.cli("validate_plan.py", self.write_plan(inline)).returncode, 0)
        bad = copy.deepcopy(self.plan)
        bad.update({"bpm": -1, "lead": 0.1, "cuts": [0.2, 0.1], "captions": [{"text": "x", "start": 0.2, "end": 0.1}]})
        errors = json.loads(self.cli("validate_plan.py", self.write_plan(bad)).stdout)["errors"]
        for needle in ("bpm", "cuts must be strictly increasing", "ends before it starts"):
            self.assertTrue(any(needle in e for e in errors), (needle, errors))

    def test_invalid_mode_type_returns_structured_error(self):
        plan = copy.deepcopy(self.plan)
        plan["mode"] = []
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["errors"])
        self.assertNotIn("Traceback", result.stderr)

    def test_invalid_audio_type_returns_structured_error(self):
        plan = copy.deepcopy(self.plan)
        plan["audio"] = {}
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["errors"])

    def test_invalid_transition_type_returns_structured_error(self):
        plan = copy.deepcopy(self.plan)
        plan["scenes"][0]["transition"]["kind"] = []
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["errors"])

    def test_boolean_schema_version_is_not_version_one(self):
        plan = copy.deepcopy(self.plan)
        plan["schema_version"] = True
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("schema_version", result.stdout)

    def test_float_schema_version_is_not_version_one(self):
        plan = copy.deepcopy(self.plan)
        plan["schema_version"] = 1.0
        result = self.cli("validate_plan.py", self.write_plan(plan))
        self.assertNotEqual(result.returncode, 0)

    def test_verifies_real_file_and_decodes(self):
        result = self.cli("verify_export.py", self.video, "--width", 320, "--height", 568,
                          "--fps", 30, "--duration", 1, "--audio", "required")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertTrue(report["decoded"])
        self.assertEqual(report["frames"], 30)
        self.assertEqual(report["errors"], [])

    def test_rejects_incorrect_resolution(self):
        result = self.cli("verify_export.py", self.video, "--width", 1080, "--height", 1920)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("width", result.stdout.lower())

    def test_rejects_incorrect_fps(self):
        result = self.cli("verify_export.py", self.video, "--fps", 60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("fps", result.stdout.lower())

    def test_rejects_incorrect_duration(self):
        result = self.cli("verify_export.py", self.video, "--duration", 2)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duration", result.stdout.lower())

    def test_rejects_corrupt_file(self):
        corrupt = self.workspace / "broken.mp4"
        corrupt.write_bytes(b"this is not an mp4")
        result = self.cli("verify_export.py", corrupt)
        self.assertNotEqual(result.returncode, 0)

    def test_report_cannot_overwrite_input_video(self):
        target = self.workspace / "preserve-this-video.mp4"
        target.write_bytes(self.video.read_bytes())
        before = target.read_bytes()
        result = self.cli("verify_export.py", target, "--report", target)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_bytes(), before)

    def test_duration_uses_video_not_longer_audio_container(self):
        result = self.cli("verify_export.py", self.long_audio, "--duration", 1, "--fps", 30)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertAlmostEqual(report["duration_s"], 1, places=2)
        self.assertGreater(report["container_duration_s"], 2)
        self.assertTrue(report["warnings"])

    def test_inspects_video_with_longer_audio(self):
        out = self.workspace / "long-audio-inspection"
        result = self.cli("inspect_video.py", self.long_audio, "--out", out, "--samples", 4)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads((out / "inspection.json").read_text(encoding="utf-8"))
        self.assertAlmostEqual(report["duration_s"], 1, places=2)

    def test_inspection_preserves_existing_outputs(self):
        out = self.workspace / "existing-inspection"
        out.mkdir()
        original = out / "frame-000-000.000s.png"
        original.write_bytes(b"preserve this existing output")
        before = original.read_bytes()
        result = self.cli("inspect_video.py", self.video, "--out", out, "--samples", 2)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(original.read_bytes(), before)

    def test_reference_sampling_saves_real_frames(self):
        out = self.workspace / "inspection"
        result = self.cli("inspect_video.py", self.video, "--out", out, "--samples", 2)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads((out / "inspection.json").read_text(encoding="utf-8"))
        self.assertEqual(len(report["frames"]), 2)
        self.assertTrue((out / report["contact_sheet"]).is_file())
        self.assertIn("not_continuous", report["inspection_level"])


class CraftPlanTests(unittest.TestCase):
    """Craft evidence is a structural contract, independent of media tooling."""

    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-craft-tests-"))
        if KEEP:
            print(f"\nCraft evidence directory preserved: {cls.workspace}")

    @classmethod
    def tearDownClass(cls):
        if not KEEP:
            shutil.rmtree(cls.workspace, ignore_errors=True)

    def setUp(self):
        self.plan = {
            "schema_version": 1, "width": 320, "height": 568, "fps": 30,
            "duration_frames": 30, "mode": "kinetic", "audio": "forbidden",
            "safe_area": {"x": 20, "y": 60, "width": 280, "height": 420},
            "scenes": [
                {"id": "a", "start_frame": 0, "end_frame": 30,
                 "intent": "change the meaning of the contour", "action": "contour opens",
                 "text": "", "transition": {"kind": "end", "carrier": ""}},
            ],
        }
        self.craft = copy.deepcopy(self.plan)
        self.craft["reference_evidence"] = [{
            "source": "local-reference.mp4 at 0.2-0.8 s",
            "observed_operation": "Object crosses the type and changes its framing",
            "own_application": "The contour becomes the boundary of the next composition",
            "proof_times": [0, 0.5, 1],
        }]
        self.craft["style_sequence"] = [
            {"time": 0, "composition": "A tight contour dominates the upper area"},
            {"time": 1, "composition": "The open contour frames the lower statement"},
        ]
        self.craft["scenes"][0]["motion"] = {
            "preparation": "Contour compresses before opening",
            "action": "Its edge crosses the statement",
            "follow_through": "none, the edge stops at a deliberate hard boundary",
            "reading": "The statement holds after the edge clears it",
        }
        self.craft["scenes"][0]["blur_plan"] = {
            "motion": "Exposure follows the moving edge and resolves at rest",
            "focus": "none, this is a single graphic plane",
            "text_resolution": "The moving type resolves before its reading interval",
        }

    def cli(self, plan, require_craft=True):
        path = self.workspace / f"{self.id().split('.')[-1]}.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        args = [sys.executable, str(SKILL / "scripts" / "validate_plan.py"), str(path)]
        if require_craft:
            args.append("--require-craft")
        return subprocess.run(args, capture_output=True, text=True, encoding="utf-8")

    def assert_structural_error(self, plan, expected):
        result = self.cli(plan)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        report = json.loads(result.stdout)
        self.assertFalse(report["artistic_quality_checked"])
        self.assertTrue(any(expected in message for message in report["errors"]), report)
        self.assertNotIn("Traceback", result.stderr)

    def test_accepts_craft_evidence_without_certifying_art(self):
        result = self.cli(self.craft)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(json.loads(result.stdout), {"errors": [], "artistic_quality_checked": False})

    def test_legacy_plan_remains_valid_without_flag(self):
        result = self.cli(self.plan, require_craft=False)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertFalse(json.loads(result.stdout)["artistic_quality_checked"])

    def test_requires_reference_evidence_with_flag(self):
        for value in (None, [], {}, "reference"):
            with self.subTest(value=value):
                plan = copy.deepcopy(self.craft)
                plan["reference_evidence"] = value
                self.assert_structural_error(plan, "reference_evidence")

    def test_requires_each_reference_description(self):
        for key in ("source", "observed_operation", "own_application"):
            for value in (None, "", "  ", []):
                with self.subTest(key=key, value=value):
                    plan = copy.deepcopy(self.craft)
                    plan["reference_evidence"][0][key] = value
                    self.assert_structural_error(plan, key)

    def test_requires_nonempty_proof_times(self):
        for value in (None, [], {}, "0.5"):
            with self.subTest(value=value):
                plan = copy.deepcopy(self.craft)
                plan["reference_evidence"][0]["proof_times"] = value
                self.assert_structural_error(plan, "proof_times")

    def test_rejects_malformed_reference_entries(self):
        plan = copy.deepcopy(self.craft)
        plan["reference_evidence"] = [None]
        self.assert_structural_error(plan, "reference_evidence[0]")

    def test_requires_style_sequence(self):
        for value in (None, [], {}, "opening"):
            with self.subTest(value=value):
                plan = copy.deepcopy(self.craft)
                plan["style_sequence"] = value
                self.assert_structural_error(plan, "style_sequence")

    def test_requires_each_style_composition_and_time(self):
        for entry, expected in ((None, "style_sequence[0]"),
                                ({"time": 0}, "composition"),
                                ({"time": 0, "composition": " "}, "composition"),
                                ({"composition": "A close frame"}, "time")):
            with self.subTest(entry=entry):
                plan = copy.deepcopy(self.craft)
                plan["style_sequence"] = [entry]
                self.assert_structural_error(plan, expected)

    def test_rejects_non_numeric_non_finite_and_outside_times(self):
        for value in (True, False, "0.5", None, float("nan"), float("inf"),
                      float("-inf"), -0.01, 1.01):
            for location in ("proof_times", "style_sequence"):
                with self.subTest(value=value, location=location):
                    plan = copy.deepcopy(self.craft)
                    if location == "proof_times":
                        plan["reference_evidence"][0]["proof_times"] = [value]
                    else:
                        plan["style_sequence"][0]["time"] = value
                    self.assert_structural_error(plan, location)

    def test_time_range_uses_rational_fps(self):
        plan = copy.deepcopy(self.craft)
        plan["fps"] = "30000/1001"
        plan["reference_evidence"][0]["proof_times"] = [0, 1.001]
        plan["style_sequence"][-1]["time"] = 1.001
        result = self.cli(plan)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        plan["reference_evidence"][0]["proof_times"] = [1.002]
        self.assert_structural_error(plan, "proof_times")

    def test_requires_all_motion_and_blur_fields_in_every_scene(self):
        for section, keys in (("motion", ("preparation", "action", "follow_through", "reading")),
                              ("blur_plan", ("motion", "focus", "text_resolution"))):
            for missing in (None, *keys):
                with self.subTest(section=section, missing=missing):
                    plan = copy.deepcopy(self.craft)
                    if missing is None:
                        del plan["scenes"][0][section]
                    else:
                        del plan["scenes"][0][section][missing]
                    self.assert_structural_error(plan, section if missing is None else missing)

    def test_rejects_empty_or_malformed_motion_and_blur_descriptions(self):
        for section, key in (("motion", "reading"), ("blur_plan", "focus")):
            for value in (None, "", "   ", [], "none", "none,", "NONE:   "):
                with self.subTest(section=section, value=value):
                    plan = copy.deepcopy(self.craft)
                    plan["scenes"][0][section][key] = value
                    self.assert_structural_error(plan, f"{section}.{key}")

    def test_justified_none_does_not_require_effects_or_camera(self):
        plan = copy.deepcopy(self.craft)
        for section in ("motion", "blur_plan"):
            for key in plan["scenes"][0][section]:
                plan["scenes"][0][section][key] = "none, the deliberately static visual carries this moment"
        result = self.cli(plan)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_invalid_duration_or_fps_still_returns_structured_errors(self):
        for field, value in (("fps", 0), ("fps", "nan"), ("duration_frames", None)):
            with self.subTest(field=field, value=value):
                plan = copy.deepcopy(self.craft)
                plan[field] = value
                self.assert_structural_error(plan, field)


if __name__ == "__main__":
    unittest.main(verbosity=2)
