"""Verify stream expectations, frame cadence and full decoding of an export; do not infer visual quality."""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))  # works under python -I too
from video_timing import video_timing


def cadence(source: Path, ffprobe: str, fps: float) -> dict:
    """Frame-by-frame timestamp cadence of the first video stream (CFR check)."""
    raw = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "frame=best_effort_timestamp_time", "-of", "csv=p=0", str(source)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    if raw.returncode:
        return {"checked": False, "error": raw.stderr[-1000:]}
    stamps = [float(line.split(",")[0]) for line in raw.stdout.split() if line and line.split(",")[0] not in ("", "N/A")]
    deltas = [b - a for a, b in zip(stamps, stamps[1:])]
    if not deltas or fps <= 0:
        return {"checked": False, "error": "not enough timestamps", "timestamps": len(stamps)}
    worst = max(abs(d - 1 / fps) for d in deltas)
    # A millisecond-rounded container (e.g. 1/1000 timebase) can deviate by up to half a tick.
    return {"checked": True, "timestamps": len(stamps), "max_delta_error_s": worst,
            "constant": worst <= 0.0006, "non_increasing": sum(1 for d in deltas if d <= 0)}


def verify(source: Path, width: int | None = None, height: int | None = None,
           fps: float | None = None, duration: float | None = None, audio: str = "optional",
           require_cfr: bool = False, require_bt709: bool = False, pix_fmt: str | None = None) -> dict:
    report = {"path": str(source.resolve()), "errors": [], "warnings": [], "decoded": False,
              "visual_review": "not_performed_by_this_script", "listening": "not_performed_by_this_script"}
    ffprobe, ffmpeg = shutil.which("ffprobe"), shutil.which("ffmpeg")
    if not ffprobe or not ffmpeg:
        report["errors"].append("ffprobe and ffmpeg must be on PATH")
        return report
    if not source.is_file():
        report["errors"].append("source file is missing")
        return report
    raw = subprocess.run([ffprobe, "-v", "error", "-count_frames", "-show_streams", "-show_format",
                          "-of", "json", str(source)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if raw.returncode:
        report["errors"].append("ffprobe failed: " + raw.stderr[-2000:])
        return report
    try:
        metadata = json.loads(raw.stdout)
        video = next((s for s in metadata["streams"] if s["codec_type"] == "video"), None)
        if video is None:
            raise ValueError("no video stream")
        rate = video.get("avg_frame_rate", "0/0")
        actual_fps = float(Fraction(rate)) if rate != "0/0" else 0.0
        frame_count = int(video.get("nb_read_frames", 0))
        timing = video_timing(source, ffprobe, video, actual_fps)
        actual_duration = timing["duration_s"]
        audios = [s for s in metadata["streams"] if s["codec_type"] == "audio"]
        report.update({"width": video["width"], "height": video["height"], "fps": actual_fps,
                       "frames": frame_count, "duration_s": actual_duration,
                       "timing": timing,
                       "container_duration_s": float(metadata["format"].get("duration", 0)),
                       "codec": video.get("codec_name"), "pixel_format": video.get("pix_fmt"),
                       "audio_streams": len(audios)})
        # Colour: untagged or BT.601 video is shown with HD (BT.709) assumptions by most players, which shifts reds.
        color = {k: video.get(k, "unknown") for k in ("color_space", "color_primaries", "color_transfer", "color_range")}
        report["color"] = color
        untagged = [k for k, v in color.items() if v in ("unknown", "", None)]
        if untagged or color["color_space"] != "bt709":
            message = (f"colour not tagged as BT.709 ({', '.join(f'{k}={v}' for k, v in color.items())}): "
                       "players may assume BT.709 and shift the brand red; render with the kit or add the BT.709 flags")
            (report["errors"] if require_bt709 else report["warnings"]).append(message)
        if pix_fmt and video.get("pix_fmt") != pix_fmt:
            report["errors"].append(f"pix_fmt: expected {pix_fmt}, got {video.get('pix_fmt')}")
        for key, expected in (("width", width), ("height", height)):
            if expected is not None and video[key] != expected:
                report["errors"].append(f"{key}: expected {expected}, got {video[key]}")
        if fps is not None and abs(actual_fps - fps) > 0.001:
            report["errors"].append(f"fps: expected {fps}, got {actual_fps}")
        if actual_fps <= 0 or frame_count <= 0 or actual_duration <= 0:
            report["errors"].append("video must have positive fps, frame count and duration")
        if duration is not None:
            tolerance = max(1 / max(1.0, actual_fps), 0.005)
            if abs(actual_duration - duration) > tolerance + 1e-6:
                report["errors"].append(f"duration: expected {duration}, got {actual_duration}")
            expected_frames = round(duration * (fps if fps is not None else actual_fps))
            if frame_count != expected_frames:
                report["errors"].append(f"frames: expected {expected_frames}, got {frame_count}")
        if audio == "required" and not audios:
            report["errors"].append("audio stream required but absent")
        if audio == "forbidden" and audios:
            report["errors"].append("audio stream present but forbidden")
        for index, track in enumerate(audios):
            track_duration = float(track.get("duration") or 0)
            if track_duration <= 0:
                report["warnings"].append(f"audio[{index}] duration unavailable; temporal alignment needs review")
            if track_duration and abs(track_duration - actual_duration) > max(0.1, 2 / max(1, actual_fps)):
                report["warnings"].append(f"audio[{index}] duration differs: {track_duration}")
        container_end = float(metadata["format"].get("duration", 0)) + float(metadata["format"].get("start_time", 0))
        if audios and container_end - (timing["start_s"] + actual_duration) > max(0.1, 2 / max(1, actual_fps)):
            report["warnings"].append("container extends beyond video; review the audio tail")
    except (KeyError, ValueError, TypeError, ZeroDivisionError) as error:
        report["errors"].append("invalid stream metadata: " + str(error))
        return report
    report["cadence"] = cadence(source, ffprobe, actual_fps)
    if report["cadence"].get("checked"):
        if report["cadence"]["non_increasing"]:
            report["errors"].append("video timestamps are not strictly increasing")
        elif not report["cadence"]["constant"]:
            (report["errors"] if require_cfr else report["warnings"]).append(
                f"variable frame cadence: max deviation {report['cadence']['max_delta_error_s']:.6f} s")
    elif require_cfr:
        report["errors"].append("constant cadence could not be checked")
    decode = subprocess.run([ffmpeg, "-v", "error", "-xerror", "-err_detect", "explode", "-i", str(source),
                             "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    report["decoded"] = decode.returncode == 0
    if decode.returncode:
        report["errors"].append("full decode failed: " + decode.stderr[-3000:])
    return report


def positive_float(value: str) -> float:
    try:
        number = float(Fraction(value))
    except (ValueError, ZeroDivisionError):
        raise argparse.ArgumentTypeError("expected a positive number or rational")
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("expected a finite positive number")
    return number


def main() -> int:
    for stream in (sys.stdout, sys.stderr):   # cp1252 consoles under python -I
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--fps", type=positive_float)
    parser.add_argument("--duration", type=positive_float)
    parser.add_argument("--audio", choices=("required", "optional", "forbidden"), default="optional")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--require-cfr", action="store_true",
                        help="fail if frame timestamps are not evenly spaced at the stream fps")
    parser.add_argument("--require-bt709", action="store_true",
                        help="fail if the video stream is not tagged BT.709 (matrix, primaries, transfer, range)")
    parser.add_argument("--pix-fmt", help="expected pixel format, e.g. yuv420p")
    args = parser.parse_args()
    if args.report:
        same_path = args.source.resolve() == args.report.resolve()
        same_file = args.source.exists() and args.report.exists() and args.source.samefile(args.report)
        if same_path or same_file:
            print(json.dumps({"errors": ["report path must not overwrite the source video"], "decoded": False}))
            return 1
    report = verify(args.source, args.width, args.height, args.fps, args.duration, args.audio, args.require_cfr,
                    args.require_bt709, args.pix_fmt)
    result = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        try:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(result, encoding="utf-8")
        except OSError as error:
            report["errors"].append("cannot write report: " + str(error))
            result = json.dumps(report, ensure_ascii=False, indent=2)
    print(result)
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
