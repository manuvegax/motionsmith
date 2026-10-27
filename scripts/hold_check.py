"""Find the dead holds of a video: stretches where the picture stops moving.

The best motion graphics never stop: when everything has landed, something still breathes (a slow push, a drift of a
few pixels, a tenth of a degree). A frame that repeats exactly reads as frozen even when the eye cannot say why. This
measures how fast the edges of the picture move between consecutive frames and reports every stretch longer than
--min seconds whose edges move slower than --floor pixels per frame (in the video's own pixels).

  python -I <skill>/scripts/hold_check.py final/piece.mp4 [--min 0.4] [--floor 0.06] [--report preview/holds.json]
  python -I <skill>/scripts/hold_check.py final/piece.mp4 --curve preview/motion-curve.png   # edge speed over time

Edge speed: on the strongest edges of a slightly blurred greyscale copy, the change between two frames divided by the
edge's gradient is how far that edge moved. The median over the edges ignores film grain (which changes every frame
but does not move edges) and does not need a grain floor. Measured on 1080 px pieces: a frozen hold reads 0.00, a
moving hold (a slow push and drift) 0.15-0.3 px per frame, under the threshold of notice; above ~1 something is
plainly moving. A frame with no edges (black, a flat colour) counts as still. It measures pixels; it does not watch
the piece.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np


def frames(path: Path, width: int) -> tuple[np.ndarray, float, float]:
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,avg_frame_rate",
                            "-of", "json", str(path)], capture_output=True, text=True, check=True)
    s = json.loads(probe.stdout)["streams"][0]
    num, _, den = s["avg_frame_rate"].partition("/")
    fps = float(num) / float(den or 1)
    width = min(width, int(s["width"]))
    h = max(2, round(int(s["height"]) * width / int(s["width"]) / 2) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf",
                          f"scale={width}:{h}:flags=area,format=gray,gblur=sigma=1.5", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    data = np.frombuffer(raw, np.uint8)
    n = data.size // (width * h)
    return data[: n * width * h].reshape(n, h, width).astype(np.float32), fps, int(s["width"]) / width


def edge_speed(stack: np.ndarray, scale: float) -> np.ndarray:
    """Median edge displacement between consecutive frames, in source pixels per frame."""
    out = np.zeros(max(0, len(stack) - 1), np.float32)
    for i in range(len(out)):
        a, b = stack[i], stack[i + 1]
        gy, gx = np.gradient((a + b) / 2)
        g = np.hypot(gx, gy)
        mask = g > max(float(np.percentile(g, 97)), 4.0)
        if mask.sum() >= 50:
            out[i] = float(np.median(np.abs(b - a)[mask] / g[mask])) * scale
    return out


def holds(motion: np.ndarray, fps: float, floor: float, minimum: float) -> list[dict]:
    still = motion < floor
    out, start = [], None
    for i, s in enumerate(list(still) + [False]):
        if s and start is None:
            start = i
        elif not s and start is not None:
            length = (i - start) / fps
            if length >= minimum:
                seg = motion[start:i]
                out.append({"start": round(start / fps, 3), "end": round(i / fps, 3), "seconds": round(length, 2),
                            "edge_speed": round(float(seg.mean()), 3), "frozen": bool(seg.mean() < floor * .4)})
            start = None
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("--min", type=float, default=.4, help="report holds at least this long (s)")
    parser.add_argument("--floor", type=float, default=.06, help="edges moving slower than this (px/frame) are a hold")
    parser.add_argument("--width", type=int, default=540, help="analysis width (px); results are in the video's pixels")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--curve", type=Path, help="a PNG of the edge speed over time")
    args = parser.parse_args()
    if not shutil.which("ffmpeg"):
        print(json.dumps({"errors": ["ffmpeg is needed"]}))
        return 2
    stack, fps, scale = frames(args.video, args.width)
    motion = edge_speed(stack, scale)
    found = holds(motion, fps, args.floor, args.min)
    total = sum(h["seconds"] for h in found)
    report = {"video": str(args.video), "fps": round(fps, 3), "frames": int(len(stack)), "holds": found,
              "held_seconds": round(total, 2), "held_share": round(total / max(len(stack) / fps, 1e-6), 3),
              "median_edge_speed": round(float(np.median(motion)), 3) if len(motion) else 0.0,
              "p10_edge_speed": round(float(np.percentile(motion, 10)), 3) if len(motion) else 0.0,
              "floor": args.floor,
              "verdict": "alive" if not found else f"{len(found)} dead hold(s): add a moving hold (slow push, drift, breathing)",
              "note": "Edge speed in px/frame; watch it at real speed on the phone."}
    if args.curve:
        from PIL import Image, ImageDraw
        w, h = 1200, 300
        img = Image.new("RGB", (w, h), (18, 18, 20)); d = ImageDraw.Draw(img)
        dur = max(len(motion), 1) / fps
        top = max(1.0, float(np.percentile(motion, 98))) if len(motion) else 1.0
        for hseg in found:
            d.rectangle([hseg["start"] / dur * w, 0, hseg["end"] / dur * w, h], fill=(70, 20, 20))
        y = lambda v: h - 10 - min(1.0, v / top) * (h - 20)
        pts = [(i / max(1, len(motion) - 1) * w, y(v)) for i, v in enumerate(motion)]
        if len(pts) > 1:
            d.line(pts, fill=(255, 66, 46), width=2)
        d.line([(0, y(args.floor)), (w, y(args.floor))], fill=(120, 120, 120), width=1)
        args.curve.parent.mkdir(parents=True, exist_ok=True); img.save(args.curve)
        report["curve"] = str(args.curve)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if not found else 1


if __name__ == "__main__":
    raise SystemExit(main())
