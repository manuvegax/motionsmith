"""Resolve video timing without treating the container/audio duration as video duration."""
from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess


def number(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (ValueError, TypeError):
        return default


def video_timing(source: Path, ffprobe: str, stream: dict, fps: float) -> dict:
    duration = number(stream.get("duration"))
    start = number(stream.get("start_time"))
    if duration > 0:
        return {"duration_s": duration, "start_s": start, "method": "video_stream_duration"}
    result = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_frames",
                             "-show_entries", "frame=best_effort_timestamp_time,duration_time,pkt_duration_time",
                             "-of", "json", str(source)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise ValueError("Cannot resolve video timestamps: " + result.stderr[-2000:])
    frames = json.loads(result.stdout).get("frames", [])
    samples = []
    for frame in frames:
        if "best_effort_timestamp_time" not in frame:
            continue
        pts = number(frame["best_effort_timestamp_time"], float("nan"))
        if not math.isfinite(pts):
            continue
        frame_duration = number(frame.get("duration_time") or frame.get("pkt_duration_time"))
        if frame_duration <= 0:
            frame_duration = 1 / fps if fps > 0 else 0
        samples.append((pts, frame_duration))
    if not samples:
        raise ValueError("Video has neither a stream duration nor usable frame timestamps")
    start = min(pts for pts, _ in samples)
    end = max(pts + frame_duration for pts, frame_duration in samples)
    if end <= start:
        raise ValueError("Video timestamp interval is empty")
    return {"duration_s": end - start, "start_s": start, "method": "video_frame_timestamps"}
