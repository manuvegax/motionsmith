"""Behavioral checks for the local OpenCV observation fallback, using tiny real clips."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import importlib.util
import unittest

import numpy as np

if importlib.util.find_spec("cv2") is None:
    raise unittest.SkipTest("OpenCV (cv2) is optional: only watch_reference.py needs it")
import cv2  # noqa: E402


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "watch_reference.py"


class WatchReferenceTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="motion-watch-tests-")
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)

    def make_clip(self, kind="static", count=12):
        path = self.root / f"{kind}.avi"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 10, (90, 160))
        self.assertTrue(writer.isOpened(), "The test environment needs an MJPG encoder")
        for index in range(count):
            frame = np.zeros((160, 90, 3), dtype=np.uint8)
            if kind == "moving":
                x = 5 + index * 3
                frame[45:95, x:x + 26] = (220, 160, 80)
                for row in range(45, 95, 8):
                    cv2.line(frame, (x, row), (x + 25, row), (255, 255, 255), 2)
            elif kind == "cut":
                frame[:] = 255 if index >= count // 2 else 0
            else:
                cv2.rectangle(frame, (20, 40), (65, 115), (140, 200, 80), -1)
            writer.write(frame)
        writer.release()
        self.assertLess(path.stat().st_size, 100_000)
        return path

    def cli(self, source, out, *args):
        self.assertTrue(SCRIPT.is_file(), "watch_reference.py is not implemented")
        return subprocess.run([sys.executable, "-B", str(SCRIPT), str(source), "--out", str(out),
                               *map(str, args)], capture_output=True, text=True, encoding="utf-8")

    def read_success(self, result, out):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads((out / "watch-report.json").read_text(encoding="utf-8"))
        records = [json.loads(line) for line in (out / "watch-metrics.jsonl").read_text().splitlines()]
        self.assertEqual(report["errors"], [])
        return report, records

    def test_static_clip_has_negligible_measured_motion(self):
        source, out = self.make_clip(), self.root / "out"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        report, records = self.read_success(self.cli(source, out), out)
        self.assertEqual(report["tool"], "local_opencv_fallback")
        self.assertEqual(report["decoded_frames"], 12)
        self.assertEqual([row["frame_index"] for row in records], list(range(12)))
        self.assertTrue(all(row["timestamp_observed_s"] is not None for row in records))
        self.assertTrue(all(a["timestamp_s"] < b["timestamp_s"] for a, b in zip(records, records[1:])))
        self.assertTrue(all(row["difference"]["mean_absolute_normalized"] < 0.002 for row in records[1:]))
        self.assertTrue(all(row["flow"]["moving_fraction"] < 0.01 for row in records[1:]))
        self.assertEqual(report["cut_candidate_count"], 0)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
        self.assertEqual(sorted(path.suffix for path in out.iterdir()), [".json", ".jsonl"])

    def test_crossing_object_has_positive_horizontal_flow(self):
        source, out = self.make_clip("moving"), self.root / "out"
        report, records = self.read_success(self.cli(source, out), out)
        motions = [row["flow"] for row in records[1:]]
        self.assertGreater(float(np.median([row["median_dx_px"] for row in motions])), 1)
        self.assertGreater(float(np.median([row["moving_fraction"] for row in motions])), 0.05)
        self.assertGreater(max(row["p90_magnitude_px"] for row in motions), 1)
        self.assertLess(float(np.median([abs(row["median_dy_px"]) for row in motions])), 1)
        self.assertEqual(report["analysis"]["width"], 180)
        self.assertEqual(report["analysis"]["height"], 320)

    def test_black_white_cut_is_a_candidate_at_the_actual_frame(self):
        source, out = self.make_clip("cut"), self.root / "out"
        report, records = self.read_success(self.cli(source, out), out)
        candidates = [row for row in records if row["cut_candidate"]]
        self.assertEqual([row["frame_index"] for row in candidates], [6])
        self.assertGreater(candidates[0]["histogram_distance"], 0.9)
        self.assertGreater(candidates[0]["difference"]["mean_absolute_normalized"], 0.9)
        self.assertEqual(report["cut_candidate_count"], 1)
        self.assertFalse(report["semantic_or_plugin_analysis_performed"])

    def test_dense_strip_uses_decoded_indices_and_observed_times(self):
        source, out = self.make_clip("moving"), self.root / "out"
        report, records = self.read_success(self.cli(source, out, "--strip", "0.15:0.75:0.3"), out)
        entries = report["strip"]["frames"]
        self.assertEqual([entry["frame_index"] for entry in entries], [2, 5, 8])
        for entry in entries:
            self.assertGreaterEqual(entry["timestamp_observed_s"] + 1e-8, entry["requested_time_s"])
            self.assertLess(entry["timestamp_observed_s"] - entry["requested_time_s"], 0.101)
            self.assertEqual(entry["timestamp_s"], records[entry["frame_index"]]["timestamp_s"])
        sheet = out / report["strip"]["path"]
        self.assertIsNotNone(cv2.imread(str(sheet)))
        self.assertLess(sheet.stat().st_size, 250_000)
        self.assertEqual(len(list(out.glob("*.jpg"))), 1)
        self.assertEqual(len(list(out.glob("*.png"))), 0)

    def test_existing_output_is_preserved(self):
        source, out = self.make_clip(), self.root / "out"
        out.mkdir()
        original = out / "watch-metrics.jsonl"
        original.write_bytes(b"keep the prior output")
        result = self.cli(source, out)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("empty", result.stdout + result.stderr)
        self.assertEqual(original.read_bytes(), b"keep the prior output")

    def test_maximum_strip_stays_one_compact_file_with_64_entries(self):
        source, out = self.make_clip("moving"), self.root / "out"
        report, _ = self.read_success(self.cli(source, out, "--strip", "0:0.63:0.01"), out)
        self.assertEqual(len(report["strip"]["frames"]), 64)
        self.assertEqual(len(list(out.iterdir())), 3)
        self.assertLess(sum(path.stat().st_size for path in out.iterdir()), 1_000_000)

    def test_invalid_strip_intervals_are_rejected_without_writing(self):
        source = self.make_clip()
        for index, interval in enumerate(("1:0:0.1", "-1:0:0.1", "0:1:0", "nan:1:0.1", "0:inf:1", "0:1:0.001")):
            with self.subTest(interval=interval):
                out = self.root / f"invalid-{index}"
                result = self.cli(source, out, "--strip", interval)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("strip", (result.stdout + result.stderr).lower())
                self.assertFalse(out.exists())

    def test_strip_outside_decoded_interval_does_not_report_success(self):
        source, out = self.make_clip(), self.root / "out"
        result = self.cli(source, out, "--strip", "0:2:0.5")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("strip", (result.stdout + result.stderr).lower())
        self.assertNotIn("Traceback", result.stderr)

    def test_frame_limit_is_explicit_and_does_not_claim_full_decode(self):
        source, out = self.make_clip("moving"), self.root / "out"
        report, records = self.read_success(self.cli(source, out, "--max-frames", 3, "--analysis-size", "270x480"), out)
        self.assertEqual(len(records), 3)
        self.assertEqual(report["decode_stop_reason"], "max_frames")
        self.assertFalse(report["reached_end_of_stream"])
        self.assertEqual(report["analysis"]["width"], 270)
        self.assertEqual(report["analysis"]["height"], 480)

    def test_invalid_dimensions_and_frame_limits_fail_before_output(self):
        source = self.make_clip()
        for index, arguments in enumerate((("--analysis-size", "0x320"), ("--max-frames", "0"), ("--max-frames", "-1"))):
            with self.subTest(arguments=arguments):
                out = self.root / f"invalid-option-{index}"
                result = self.cli(source, out, *arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
