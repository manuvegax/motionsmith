"""Local OpenCV fallback: stream video measurements and an optional bounded JPEG strip.

This is measurement of decoded images, not playback, listening, semantic review or
identification of animation software/easing. No individual frame files are exported.
"""
from __future__ import annotations

import sys
import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np


MAX_STRIP_FRAMES = 64
FLOW_THRESHOLD_PX = 0.5
FLOW_PARAMETERS = dict(pyr_scale=0.5, levels=3, winsize=15, iterations=3,
                       poly_n=5, poly_sigma=1.2, flags=0)


def parse_strip(value: str) -> list[float]:
    """Inclusive sampling grid, without silently adding an off-grid end time."""
    try:
        start, end, step = map(float, value.split(":"))
    except (ValueError, TypeError):
        raise ValueError("strip must be START:END:STEP in seconds") from None
    if not all(math.isfinite(v) for v in (start, end, step)) or start < 0 or end < start or step <= 0:
        raise ValueError("strip needs finite times, 0 <= START <= END and STEP > 0")
    count_ratio = (end - start) / step
    if not math.isfinite(count_ratio) or count_ratio >= MAX_STRIP_FRAMES:
        raise ValueError(f"strip is limited to {MAX_STRIP_FRAMES} frames; increase STEP")
    return [start + index * step for index in range(math.floor(count_ratio + 1e-9) + 1)]


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected a positive integer") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def rounded(value) -> float:
    return round(float(value), 6)


def letterbox(frame: np.ndarray, width: int, height: int) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    source_h, source_w = frame.shape[:2]
    scale = min(width / source_w, height / source_h)
    scaled_w, scaled_h = max(1, round(source_w * scale)), max(1, round(source_h * scale))
    resized = cv2.resize(frame, (scaled_w, scaled_h), interpolation=cv2.INTER_AREA)
    x, y = (width - scaled_w) // 2, (height - scaled_h) // 2
    canvas = np.zeros((height, width, 3), dtype=np.uint8)
    canvas[y:y + scaled_h, x:x + scaled_w] = resized
    return canvas, (x, y, scaled_w, scaled_h)


def histogram(content: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(content, cv2.COLOR_BGR2HSV)
    result = cv2.calcHist([hsv], [0, 1, 2], None, [16, 4, 8], [0, 180, 0, 256, 0, 256])
    return cv2.normalize(result, result, alpha=1, norm_type=cv2.NORM_L1)


def measure(previous: np.ndarray, current: np.ndarray, roi: tuple[int, int, int, int]) -> tuple[dict, dict]:
    x, y, width, height = roi
    region = np.s_[y:y + height, x:x + width]
    difference = cv2.absdiff(previous, current)[region]
    flow = cv2.calcOpticalFlowFarneback(previous, current, None, **FLOW_PARAMETERS)[region]
    if not np.isfinite(flow).all():
        raise ValueError("Farneback produced non-finite flow; measurements are incomplete")
    magnitude = np.hypot(flow[..., 0], flow[..., 1])
    moving = magnitude >= FLOW_THRESHOLD_PX
    selected = flow[moving]
    result = {
        "median_dx_px": rounded(np.median(selected[:, 0])) if selected.size else 0.0,
        "median_dy_px": rounded(np.median(selected[:, 1])) if selected.size else 0.0,
        "median_all_dx_px": rounded(np.median(flow[..., 0])),
        "median_all_dy_px": rounded(np.median(flow[..., 1])),
        "p90_magnitude_px": rounded(np.percentile(magnitude, 90)),
        "moving_fraction": rounded(np.mean(moving)),
    }
    return {"mean_absolute_normalized": rounded(np.mean(difference) / 255),
            "changed_fraction": rounded(np.mean(difference >= 10))}, result


def save_strip(out: Path, thumbnails: list[np.ndarray], entries: list[dict]) -> dict:
    columns, thumb_w, thumb_h, label_h = 4, 135, 240, 40
    rows = math.ceil(len(thumbnails) / columns)
    sheet = np.full((rows * (thumb_h + label_h), columns * thumb_w, 3), 22, dtype=np.uint8)
    for index, (thumbnail, entry) in enumerate(zip(thumbnails, entries)):
        x, y = index % columns * thumb_w, index // columns * (thumb_h + label_h)
        sheet[y:y + thumb_h, x:x + thumb_w] = thumbnail
        lines = (f'#{entry["frame_index"]} obs {entry["timestamp_s"]:.3f}s',
                 f'req {entry["requested_time_s"]:.3f}s')
        for line_index, line in enumerate(lines):
            cv2.putText(sheet, line, (x + 3, y + thumb_h + 14 + line_index * 17),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.32, (235, 235, 235), 1, cv2.LINE_AA)
    encoded_ok, encoded = cv2.imencode(".jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not encoded_ok:
        raise ValueError("Cannot encode the JPEG strip")
    with (out / "watch-strip.jpg").open("xb") as handle:
        handle.write(encoded.tobytes())
    return {"path": "watch-strip.jpg", "frames": entries, "max_frames": MAX_STRIP_FRAMES,
            "selection_method": "sequential_decode_first_frame_at_or_after_requested_relative_timestamp",
            "thumbnail_dimensions": [thumb_w, thumb_h]}


def watch(source: Path, out: Path, analysis_size: str = "180x320", strip: list[float] | None = None,
          max_frames: int | None = None) -> dict:
    if analysis_size not in {"180x320", "270x480"}:
        raise ValueError("analysis-size must be 180x320 or 270x480")
    if max_frames is not None and (type(max_frames) is not int or max_frames <= 0):
        raise ValueError("max-frames must be a positive integer")
    if strip is not None and (not strip or len(strip) > MAX_STRIP_FRAMES
                              or any(not math.isfinite(t) or t < 0 for t in strip)
                              or any(a > b for a, b in zip(strip, strip[1:]))):
        raise ValueError("strip must contain ordered finite nonnegative times, at most 64")
    source = source.resolve(strict=True)
    if not source.is_file():
        raise ValueError("source must be a local video file")
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError("out must be a new or empty directory; existing outputs are preserved")
    capture = cv2.VideoCapture(str(source))
    try:
        if not capture.isOpened():
            raise ValueError("OpenCV could not open the source video")
        fps = capture.get(cv2.CAP_PROP_FPS)
        source_w, source_h = capture.get(cv2.CAP_PROP_FRAME_WIDTH), capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if not all(math.isfinite(v) and v > 0 for v in (fps, source_w, source_h)):
            raise ValueError("video must report finite positive fps and dimensions")
        if source_w > 16384 or source_h > 16384:
            raise ValueError("video dimensions exceed the supported 16384-pixel side")
        reported_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        width, height = map(int, analysis_size.split("x"))
        report = {
            "schema_version": 1, "tool": "local_opencv_fallback", "errors": [],
            "source": {"path": str(source), "bytes": source.stat().st_size,
                       "width_reported": int(source_w), "height_reported": int(source_h),
                       "fps_reported": fps, "frame_count_reported": reported_count if math.isfinite(reported_count) else None,
                       "duration_estimate_from_reported_frames_s": (reported_count / fps
                           if math.isfinite(reported_count) and reported_count > 0 else None),
                       "backend": capture.getBackendName(), "opencv_version": cv2.__version__},
            "analysis": {"width": width, "height": height, "resize": "aspect_preserving_letterbox",
                         "flow_method": "Farneback", "flow_parameters": FLOW_PARAMETERS,
                         "flow_units": "analysis_pixels_per_decoded_frame_pair",
                         "flow_median_scope": "pixels_in_content_roi_with_magnitude_at_least_threshold",
                         "moving_threshold_px": FLOW_THRESHOLD_PX,
                         "cut_heuristic": "(histogram_distance >= 0.6 and mean_absolute_difference >= 0.12) or difference >= 0.45",
                         "histogram": "HSV 16x4x8, L1 normalized, Bhattacharyya distance",
                         "difference": "grayscale absolute difference; normalized mean and fraction >= 10/255"},
            "timebase": "timestamp_s and strip requests are seconds relative to the first decoded frame; timestamp_observed_s is raw OpenCV POS_MSEC/1000",
            "semantic_or_plugin_analysis_performed": False,
            "limitations": [
                "No continuous playback, listening, semantic interpretation or definitive software/easing identification.",
                "Flow is an appearance-based estimate, unreliable across cuts, occlusion, blur, low texture or flashing.",
                "Candidate cuts are image changes, including flashes; they do not prove editorial cuts.",
                "Timestamps and reported frame indices depend on the OpenCV backend; estimates are labeled explicitly.",
                "OpenCV read returning false does not certify complete decoding or file integrity; use verify_export.py separately.",
                "The JPEG strip selects decoded frames at or after requested times; it does not interpolate frames.",
                "Frame-count/fps duration estimates assume constant frame rate; the observed timestamp span excludes the last frame exposure.",
            ],
        }
        out.mkdir(parents=True, exist_ok=True)
        previous, previous_hist, previous_raw_time = None, None, None
        timestamp_origin = None
        timestamps_estimated, index, cut_count = 0, 0, 0
        candidates, thumbnails, strip_entries = [], [], []
        pending = list(strip or [])
        roi, decoded_shape = None, None
        last_time = None
        with (out / "watch-metrics.jsonl").open("x", encoding="utf-8") as metrics:
            while True:
                if max_frames is not None and index >= max_frames:
                    report.update(decode_stop_reason="max_frames", reached_end_of_stream=False)
                    break
                decoded, frame = capture.read()
                if not decoded:
                    report.update(decode_stop_reason="opencv_read_returned_false", reached_end_of_stream=True)
                    break
                if frame is None or not frame.size:
                    raise ValueError(f"empty decoded image at frame {index}")
                if decoded_shape is None:
                    decoded_shape = frame.shape[:2]
                    report["source"]["decoded_dimensions"] = [frame.shape[1], frame.shape[0]]
                elif frame.shape[:2] != decoded_shape:
                    raise ValueError("changing decoded dimensions are not supported in one measurement stream")
                raw_time = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
                observed = (raw_time if math.isfinite(raw_time) and raw_time >= 0
                            and (previous_raw_time is None or raw_time > previous_raw_time) else None)
                if index == 0:
                    timestamp_origin = observed if observed is not None else 0.0
                relative_time = observed - timestamp_origin if observed is not None else index / fps
                timestamp_source = "opencv_pos_msec" if observed is not None else "estimated_frame_index_over_reported_fps"
                if observed is None:
                    timestamps_estimated += 1
                    if strip is not None:
                        raise ValueError("strip requires usable observed OpenCV timestamps; this backend only permits frame-index estimates")
                previous_raw_time = raw_time
                current, roi = letterbox(frame, width, height)
                x, y, content_w, content_h = roi
                gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
                current_hist = histogram(current[y:y + content_h, x:x + content_w])
                difference, flow, distance, cut_candidate = None, None, None, False
                if previous is not None:
                    difference, flow = measure(previous, gray, roi)
                    distance = rounded(cv2.compareHist(previous_hist, current_hist, cv2.HISTCMP_BHATTACHARYYA))
                    diff_mean = difference["mean_absolute_normalized"]
                    cut_candidate = (distance >= 0.6 and diff_mean >= 0.12) or diff_mean >= 0.45
                backend_position = capture.get(cv2.CAP_PROP_POS_FRAMES)
                record = {"frame_index": index,
                          "decoder_reported_next_frame_index": backend_position if math.isfinite(backend_position) else None,
                          "timestamp_s": rounded(relative_time),
                          "timestamp_backend_raw_s": rounded(raw_time) if math.isfinite(raw_time) else None,
                          "timestamp_observed_s": rounded(observed) if observed is not None else None,
                          "timestamp_source": timestamp_source, "difference": difference, "flow": flow,
                          "histogram_distance": distance, "cut_candidate": bool(cut_candidate)}
                metrics.write(json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")
                if cut_candidate:
                    cut_count += 1
                    if len(candidates) < 128:
                        candidates.append({"frame_index": index, "timestamp_s": rounded(relative_time)})
                while pending and relative_time + 1e-8 >= pending[0]:
                    requested = pending.pop(0)
                    thumbnail, _ = letterbox(frame, 135, 240)
                    thumbnails.append(thumbnail)
                    strip_entries.append({"requested_time_s": rounded(requested), "frame_index": index,
                                          "timestamp_s": rounded(relative_time),
                                          "timestamp_observed_s": rounded(observed),
                                          "timestamp_source": timestamp_source})
                last_time = relative_time
                previous, previous_hist = gray, current_hist
                index += 1
        if not index:
            raise ValueError("no video frames were decoded")
        if pending:
            raise ValueError(f"strip request {pending[0]:.6f}s is outside the decoded interval ending at {last_time:.6f}s; no successful report produced")
        report.update(decoded_frames=index, last_decoded_timestamp_s=rounded(last_time),
                      timestamp_origin_observed_s=timestamp_origin, estimated_timestamp_count=timestamps_estimated,
                      observed_timestamp_count=index - timestamps_estimated,
                      decoded_duration_estimate_frames_over_reported_fps_s=rounded(index / fps),
                      cut_candidate_count=cut_count, cut_candidates=candidates,
                      cut_candidates_omitted=max(0, cut_count - len(candidates)),
                      metrics_path="watch-metrics.jsonl", strip=None)
        report["analysis"]["content_roi"] = dict(zip(("x", "y", "width", "height"), roi))
        if strip is not None:
            report["strip"] = save_strip(out, thumbnails, strip_entries)
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        report["source"]["sha256"] = digest.hexdigest()
        with (out / "watch-report.json").open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, allow_nan=False, indent=2)
        return report
    finally:
        capture.release()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):   # cp1252 consoles under python -I
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="New or empty output directory; never overwrites files")
    parser.add_argument("--analysis-size", choices=("180x320", "270x480"), default="180x320")
    parser.add_argument("--strip", help="START:END:STEP seconds relative to first decoded frame, max 64 thumbnails")
    parser.add_argument("--max-frames", type=positive_int, help="Stop after this many sequentially decoded frames, explicitly marked as limited")
    args = parser.parse_args()
    try:
        strip = parse_strip(args.strip) if args.strip is not None else None
        report = watch(args.source, args.out, args.analysis_size, strip, args.max_frames)
    except (OSError, ValueError, cv2.error) as error:
        print(json.dumps({"errors": [str(error)], "report_complete": False,
                          "note": "A failed run may leave partial measurements; existing files and source are preserved."}, ensure_ascii=False))
        return 1
    print(json.dumps({"errors": [], "tool": report["tool"], "report": str(args.out / "watch-report.json"),
                      "decoded_frames": report["decoded_frames"], "decode_stop_reason": report["decode_stop_reason"],
                      "strip": str(args.out / report["strip"]["path"]) if report["strip"] else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
