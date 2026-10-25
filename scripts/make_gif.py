"""A light GIF from a time range of a video, or of a composition.

  python scripts/make_gif.py --video final/piece.mp4 --start 1.0 --end 3.5 --out preview/clip.gif
  python scripts/make_gif.py --root pieces/piece --start 1.0 --end 3.5 --out preview/clip.gif [--page sub/index.html]

--video: any file FFmpeg can read. --root: a composition folder; the range is first rendered to a temporary MP4 with
render_stream.mjs (the same capture as a normal render: Node, Playwright and Chrome), then converted.
One palette per clip (palettegen with stats_mode=diff, paletteuse with bayer dithering by default) keeps the colours
and the size small. --fps and --width set the cost; --colors caps the palette. A GIF over --max-mb is reported as a
warning (--strict makes warnings fail). Refuses to overwrite an existing GIF unless --replace is given.
Exit codes: 0 written, 1 FFmpeg or the render failed, 2 usage or input error.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
DITHERS = {
    "bayer": "paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
    "sierra2_4a": "paletteuse=dither=sierra2_4a:diff_mode=rectangle",
    "none": "paletteuse=dither=none:diff_mode=rectangle",
}


def gif_filter(fps: int, width: int, colors: int, dither: str) -> str:
    """One filter graph: resample and scale, split, build one palette for the clip, then map the frames onto it."""
    return (f"fps={fps},scale={width}:-1:flags=lanczos,split[a][b];"
            f"[a]palettegen=max_colors={colors}:stats_mode=diff[palette];[b][palette]{DITHERS[dither]}")


def build_command(ffmpeg: str, video: Path, out: Path, *, start: float = 0.0, duration: float | None = None,
                  fps: int = 12, width: int = 480, colors: int = 128, dither: str = "bayer",
                  overwrite: bool = False) -> list[str]:
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y" if overwrite else "-n"]
    if start > 0:
        command += ["-ss", f"{start:.3f}"]
    command += ["-i", str(video)]
    if duration is not None:
        command += ["-t", f"{duration:.3f}"]
    command += ["-vf", gif_filter(fps, width, colors, dither), "-loop", "0", str(Path(out).resolve())]
    return command


def describe(out: Path) -> dict:
    from PIL import Image

    with Image.open(out) as image:
        return {"frames": getattr(image, "n_frames", 1), "width": image.size[0], "height": image.size[1]}


def render_composition(root: Path, start: float, end: float, folder: Path, args) -> Path:
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node is required to render a composition")
    clip = folder / "clip.mp4"
    command = [node, str(SCRIPTS / "render_stream.mjs"), "--root", str(root), "--out", str(clip),
               "--start", f"{start:.3f}", "--end", f"{end:.3f}", "--no-audio"]
    for flag, value in (("--page", args.page), ("--node-modules", args.node_modules), ("--chrome", args.chrome)):
        if value:
            command += [flag, value]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
    if result.returncode:
        raise RuntimeError("the composition did not render:\n" + (result.stderr or result.stdout)[-2000:])
    return clip


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--video", type=Path, help="a video file FFmpeg can read")
    source.add_argument("--root", type=Path, help="a composition folder rendered with render_stream.mjs")
    parser.add_argument("--start", type=float, default=0.0, help="first second of the clip (default 0)")
    parser.add_argument("--end", type=float, help="last second of the clip")
    parser.add_argument("--duration", type=float, help="length of the clip in seconds (instead of --end)")
    parser.add_argument("--fps", type=int, default=12, help="frames per second (default 12)")
    parser.add_argument("--width", type=int, default=480, help="width in pixels, height follows the aspect (default 480)")
    parser.add_argument("--colors", type=int, default=128, help="palette size, 2 to 256 (default 128)")
    parser.add_argument("--dither", choices=sorted(DITHERS), default="bayer")
    parser.add_argument("--max-mb", type=float, default=8.0, help="warn above this size in megabytes (default 8)")
    parser.add_argument("--out", type=Path, required=True, help="the .gif to write")
    parser.add_argument("--replace", action="store_true", help="overwrite the GIF if it exists")
    parser.add_argument("--strict", action="store_true", help="exit 1 when there are warnings")
    parser.add_argument("--page", help="for --root: the page to render, relative to the folder")
    parser.add_argument("--node-modules", help="for --root: the node_modules folder to use")
    parser.add_argument("--chrome", help="for --root: the Chrome executable to use")
    args = parser.parse_args()

    if args.start < 0 or (args.end is not None and args.end <= args.start) or (args.duration is not None and args.duration <= 0):
        parser.error("start must be at least 0, end after start, duration positive")
    if args.end is not None and args.duration is not None:
        parser.error("pass --end or --duration, not both")
    if args.root is not None and args.end is None and args.duration is None:
        parser.error("a composition needs --end or --duration")
    if not 1 <= args.fps <= 30 or not 32 <= args.width <= 1080 or not 2 <= args.colors <= 256 or args.max_mb <= 0:
        parser.error("fps 1-30, width 32-1080, colors 2-256, max-mb positive")
    if args.out.suffix.lower() != ".gif":
        parser.error("--out must be a .gif file")
    if args.out.exists() and not args.replace:
        parser.error(f"{args.out} exists; choose another name or pass --replace")
    if args.video is not None and not args.video.is_file():
        parser.error(f"file not found: {args.video}")
    if args.root is not None and not args.root.is_dir():
        parser.error(f"folder not found: {args.root}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.error("FFmpeg must be on PATH")

    duration = args.duration if args.duration is not None else (args.end - args.start if args.end is not None else None)
    with tempfile.TemporaryDirectory() as folder:
        try:
            if args.root is not None:
                video = render_composition(args.root.resolve(), args.start, args.start + duration, Path(folder), args)
                start, length = 0.0, None
            else:
                video, start, length = args.video, args.start, duration
            args.out.parent.mkdir(parents=True, exist_ok=True)
            command = build_command(ffmpeg, video, args.out, start=start, duration=length, fps=args.fps, width=args.width,
                                    colors=args.colors, dither=args.dither, overwrite=args.replace)
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
            if result.returncode:
                raise RuntimeError("FFmpeg failed:\n" + result.stderr[-2000:])
        except RuntimeError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1

    size = args.out.stat().st_size
    warnings = []
    if size > args.max_mb * 1_000_000:
        warnings.append(f"the GIF is {size / 1e6:.1f} MB, larger than {args.max_mb:g} MB: lower --fps, --width or --colors")
    info = describe(args.out)   # the clip's real length: a range past the end of the piece is clamped by the render
    report = {"out": str(args.out.resolve()), "bytes": size, **info, "fps": args.fps,
              "duration_s": round(info["frames"] / args.fps, 3), "warnings": warnings}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if (warnings and args.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
