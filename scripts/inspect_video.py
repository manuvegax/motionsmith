"""Inspect local reference footage without changing it; export timed contact sheets."""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont, ImageOps
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))  # works under python -I too
from video_timing import number, video_timing


def run(args: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(args, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-4000:])
    return result


def font(size: int):
    for candidate in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def inspect(source: Path, out: Path, samples: int = 16, times: list[float] | None = None,
            scene_threshold: float | None = None) -> dict:
    source = source.resolve(strict=True)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise ValueError("Choose a new or empty --out directory; existing outputs are preserved.")
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("ffmpeg and ffprobe must be available on PATH.")
    raw = json.loads(run([ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(source)]).stdout)
    video = next((s for s in raw["streams"] if s["codec_type"] == "video"), None)
    if video is None:
        raise ValueError("Input has no video stream.")
    rate = video.get("avg_frame_rate", "0/0")
    fps = float(Fraction(rate)) if rate != "0/0" else 30.0
    timing = video_timing(source, ffprobe, video, fps)
    duration = timing["duration_s"]
    seek_offset = timing["start_s"] - number(raw["format"].get("start_time"))
    last = max(0.0, duration - 1 / max(1.0, fps))
    if duration <= 0:
        raise ValueError("Input has no positive duration.")
    if times is None:
        times = [last * n / (samples - 1) for n in range(samples)]
    if not times or any(not math.isfinite(t) or t < 0 or t > last + 1e-6 for t in times):
        raise ValueError(f"Times must fall within [0, {last:.4f}] seconds.")
    cuts = []
    if scene_threshold is not None:
        result = run([ffmpeg, "-hide_banner", "-i", str(source), "-an", "-vf",
                      f"select=gt(scene\\,{scene_threshold}),showinfo", "-f", "null", "-"])
        cuts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", result.stderr.decode("utf-8", "replace"))]
    out.mkdir(parents=True, exist_ok=True)
    columns, thumb_w, thumb_h, label_h, header_h = 4, 252, 448, 30, 64
    rows = math.ceil(len(times) / columns)
    sheet = Image.new("RGB", (columns * thumb_w, header_h + rows * (thumb_h + label_h)), "#161619")
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 8), source.stem[:95], font=font(14), fill="white")
    draw.text((12, 32), f'{video["width"]}x{video["height"]} | {fps:.3f} fps | {duration:.3f}s | sampled frames',
              font=font(15), fill="#bbbbc2")
    frames = []
    for index, t in enumerate(times):
        data = run([ffmpeg, "-v", "error", "-ss", f"{max(0, t + seek_offset):.8f}", "-i", str(source),
                    "-map", "0:v:0", "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"]).stdout
        frame = Image.open(BytesIO(data)).convert("RGB")
        name = f"frame-{index:03d}-{t:07.3f}s.png"
        with (out / name).open("xb") as handle:
            frame.save(handle, format="PNG")
        thumb = ImageOps.contain(frame, (thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = index % columns * thumb_w
        y = header_h + index // columns * (thumb_h + label_h)
        sheet.paste(thumb, (x + (thumb_w - thumb.width) // 2, y + (thumb_h - thumb.height) // 2))
        draw.text((x + 8, y + thumb_h + 3), f"{t:.3f} s", font=font(17), fill="white")
        frames.append({"requested_time_s": t, "source_seek_s": max(0, t + seek_offset), "path": name})
    with (out / "contact-sheet.jpg").open("xb") as handle:
        sheet.save(handle, format="JPEG", quality=95, subsampling=0)
    digest = hashlib.sha256()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    report = {
        "source": str(source), "sha256": digest.hexdigest(), "duration_s": duration, "timing": timing,
        "video": video, "audio_streams": [s for s in raw["streams"] if s["codec_type"] == "audio"],
        "inspection_level": "sampled_frames_not_continuous_playback_or_listening",
        "scene_threshold": scene_threshold, "scene_change_candidates_s": cuts,
        "scene_detection_note": "Image differences suggest transitions; they do not prove editorial cuts.",
        "frames": frames, "contact_sheet": "contact-sheet.jpg",
    }
    with (out / "inspection.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> int:
    for stream in (sys.stdout, sys.stderr):   # cp1252 consoles under python -I
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--times", help="Comma-separated timestamps, in seconds")
    parser.add_argument("--scene-threshold", type=float)
    args = parser.parse_args()
    if not 2 <= args.samples <= 200:
        parser.error("--samples must be between 2 and 200")
    if args.scene_threshold is not None and not 0 < args.scene_threshold < 1:
        parser.error("--scene-threshold must fall between 0 and 1")
    try:
        times = [float(t) for t in args.times.split(",")] if args.times else None
        report = inspect(args.source, args.out, args.samples, times, args.scene_threshold)
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Inspection failed: {error}\n")
    print(json.dumps({"source": str(args.source), "duration_s": report["duration_s"],
                      "sheet": str(args.out / "contact-sheet.jpg"),
                      "scene_candidates_s": report["scene_change_candidates_s"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
