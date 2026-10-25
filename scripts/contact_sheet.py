"""Build a labelled contact sheet from a folder of frames, or a sheet of enlarged crops.

Pairs with sample_frames.mjs (files named t<seconds>.jpg) but accepts any JPG/PNG folder.
A sheet helps an agent look; it never proves smoothness, timing or sound.

  python scripts/contact_sheet.py preview/tmp-7.0-7.6 --out preview/acople.jpg --cols 7
  python scripts/contact_sheet.py preview/tmp-glass --out preview/cristal.jpg --crop 140,800,800,800 --tile 520
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from PIL import Image, ImageDraw, ImageFont

TIME_NAME = re.compile(r"^t(-?\d+(?:\.\d+)?)(?:[-_].*)?$")


def font(size: int):
    for candidate in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def frames(folder: Path) -> list[tuple[str, Path]]:
    files = [p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    def key(path: Path):
        match = TIME_NAME.match(path.stem)
        return (0, float(match[1]), path.name) if match else (1, 0.0, path.name)
    labelled = []
    for path in sorted(files, key=key):
        match = TIME_NAME.match(path.stem)
        labelled.append((f"{float(match[1]):.3f} s" if match else path.stem, path))
    return labelled


def parse_crop(text: str) -> tuple[int, int, int, int]:
    try:
        x, y, w, h = (int(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("crop is x,y,width,height in source pixels")
    if w <= 0 or h <= 0 or x < 0 or y < 0:
        raise argparse.ArgumentTypeError("crop needs x,y >= 0 and positive size")
    return x, y, w, h


def main() -> int:
    for stream in (sys.stdout, sys.stderr):   # cp1252 consoles under python -I
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cols", type=int, default=6)
    parser.add_argument("--tile", type=int, default=225, help="tile width in pixels")
    parser.add_argument("--crop", type=parse_crop, help="x,y,w,h: show this region of every frame enlarged")
    parser.add_argument("--title", default="")
    args = parser.parse_args()
    if not args.folder.is_dir():
        print(f"not a folder: {args.folder}", file=sys.stderr)
        return 1
    if args.out.resolve().parent == args.folder.resolve():
        print("write the sheet outside the frames folder, so the folder can be deleted after looking", file=sys.stderr)
        return 1
    items = frames(args.folder)
    if not items:
        print("no JPG/PNG frames found", file=sys.stderr)
        return 1
    first = Image.open(items[0][1])
    region = args.crop or (0, 0, first.width, first.height)
    if region[0] + region[2] > first.width or region[1] + region[3] > first.height:
        print(f"crop {region} exceeds frame {first.width}x{first.height}", file=sys.stderr)
        return 1
    tile_w = args.tile
    tile_h = round(tile_w * region[3] / region[2])
    cols = max(1, min(args.cols, len(items)))
    rows = (len(items) + cols - 1) // cols
    head = 26 if args.title else 0
    label_h = 20
    sheet = Image.new("RGB", (tile_w * cols, head + (tile_h + label_h) * rows), (20, 21, 20))
    draw = ImageDraw.Draw(sheet)
    small = font(14)
    if args.title:
        draw.text((6, 4), args.title, font=font(16), fill="white")
    for index, (label, path) in enumerate(items):
        image = Image.open(path).convert("RGB").crop((region[0], region[1], region[0] + region[2], region[1] + region[3]))
        image = image.resize((tile_w, tile_h), Image.LANCZOS)
        x, y = (index % cols) * tile_w, head + (index // cols) * (tile_h + label_h)
        sheet.paste(image, (x, y))
        draw.text((x + 5, y + tile_h + 2), label, font=small, fill="white")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out, quality=90)
    scale = tile_w / region[2]
    print(f"{args.out} · {len(items)} frames · region {region} · scale {scale:.2f}x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
