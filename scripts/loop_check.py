"""Check that a looping video loops: the jump from the last frame back to the first must look like any other step.

A seamless loop has two conditions: the last frame leads into the first (position) and motion keeps its pace across
the seam (speed). This decodes a small greyscale copy of the video and compares the seam step (last -> first) with the
ordinary steps around it.

  python -I <skill>/scripts/loop_check.py final/piece.mp4 [--tolerance 2.0] [--width 160] [--report preview/loop.json]

seam_ratio = seam step / median step near the ends. Around 1 is invisible; above the tolerance the loop jumps.
speed_ratio = mean step in the first 0.25 s / mean step in the last 0.25 s; far from 1 means the speed breaks at the
seam even when the frames match. A still piece (no motion near the ends) passes when the seam is under 1 grey level.
It measures pixels; it does not watch the loop at real speed on a phone.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np


def _probe(path: Path) -> tuple[int, int, float]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,avg_frame_rate", "-of", "json", str(path)],
                         check=True, capture_output=True, text=True).stdout
    stream = json.loads(out)["streams"][0]
    num, _, den = stream["avg_frame_rate"].partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    return int(stream["width"]), int(stream["height"]), fps


def frames(path: Path, width: int) -> tuple[np.ndarray, float]:
    src_w, src_h, fps = _probe(path)
    height = max(2, round(src_h * width / src_w / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf",
                          f"scale={width}:{height}:flags=area,format=gray", "-f", "rawvideo", "-"],
                         check=True, capture_output=True).stdout
    data = np.frombuffer(raw, dtype=np.uint8)
    count = data.size // (width * height)
    return data[: count * width * height].reshape(count, height, width).astype(np.float32), fps


def measure(stack: np.ndarray, fps: float, tolerance: float = 2.0) -> dict:
    if len(stack) < 4:
        return {"pass": False, "errors": ["need at least 4 frames"]}
    steps = np.abs(np.diff(stack, axis=0)).mean(axis=(1, 2))
    seam = float(np.abs(stack[0] - stack[-1]).mean())
    window = max(2, int(round(fps * 0.25))) if fps > 0 else 8
    head, tail = steps[:window], steps[-window:]
    near = np.concatenate([head, tail])
    typical = float(np.median(near))
    still = typical < 0.25
    seam_ratio = seam / typical if typical > 1e-6 else (0.0 if seam < 1e-6 else float("inf"))
    speed_ratio = float(head.mean() / tail.mean()) if tail.mean() > 1e-6 else (1.0 if head.mean() < 1e-6 else float("inf"))
    errors, warnings = [], []
    if still:
        if seam > 1.0:
            errors.append(f"the ends are still but differ by {seam:.2f} grey levels: the loop jumps")
    else:
        if seam_ratio > tolerance:
            errors.append(f"the seam step is {seam_ratio:.1f}x a normal step (tolerance {tolerance}): the last frame "
                          "does not lead into the first")
        if not 1 / 3 <= speed_ratio <= 3:
            warnings.append(f"motion is {speed_ratio:.2f}x faster at the start than at the end: the speed breaks at "
                            "the seam (match the velocity too, not only the pose)")
    if not still and seam < max(0.15, 0.05 * typical):   # encoding noise only: the same pose twice
        warnings.append("the last frame equals the first: the seam shows the same frame twice (a stutter); end one "
                        "step before the first pose, e.g. sample t in [0, period) not [0, period]")
    return {"pass": not errors, "frames": int(len(stack)), "fps": round(fps, 3), "seam_step": round(seam, 3),
            "typical_step": round(typical, 3), "seam_ratio": round(seam_ratio, 3) if np.isfinite(seam_ratio) else None,
            "speed_ratio": round(speed_ratio, 3) if np.isfinite(speed_ratio) else None, "still_ends": still,
            "tolerance": tolerance, "errors": errors, "warnings": warnings,
            "note": "Pixel measure of the seam; watch the loop at real speed on the target device."}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("--tolerance", type=float, default=2.0)
    parser.add_argument("--width", type=int, default=160, help="analysis width in pixels (small is enough)")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print(json.dumps({"pass": False, "errors": ["ffmpeg and ffprobe are needed on PATH"]}))
        return 2
    try:
        stack, fps = frames(args.video, max(16, args.width // 2 * 2))
        report = measure(stack, fps, args.tolerance)
    except (subprocess.CalledProcessError, OSError, KeyError, IndexError, ValueError) as error:
        report = {"pass": False, "errors": [f"could not read {args.video}: {error}"]}
    report["video"] = str(args.video)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
