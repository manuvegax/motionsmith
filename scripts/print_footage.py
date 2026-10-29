"""Screen print with frame-rate lag for footage and photos: one finish so every B-roll insert belongs together.

Two inks with a halftone fixed to the screen (9 px cells; the base ink at 45°, the accent at 15°), misregistration
that boils on twos and jumps on the keywords you pass, a paper texture, and the footage stepped to 15 fps (each
picture held for two output frames at 30 fps) while the composition's camera above stays fluid. Saturated warm reds
of the source go to the accent ink; everything else goes to the base ink by its light.

  --inks paper   dark ink + accent on paper (default)
  --inks night   light ink + accent on black stock
  --no-accent    everything in the base ink (use on skin: warm skin would land in the accent ink)

Guides: references/edit/talking-head.md §5, references/craft/print-textures.md, references/craft/stepped-time.md.

Usage:
  python -I print_footage.py clip.mp4 out.mp4 --dur 2.0 [--start 0.5] [--hits 0.4,1.2] [--inks paper|night]
  python -I print_footage.py photo.jpg out.mp4 --dur 1.5 --push 0.06          (a photo: slow push, also on twos)
  options: --size 1080x1920 --accent "#e8331f" --ink "#151412" --paper "#efeee8" --texture paper.jpg --no-accent
Output: H.264, 30 fps, CRF 12, a keyframe every 6 frames (fast seeking in HyperFrames), BT.709 tags.
Needs ffmpeg and numpy only.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np

FPS = 30
PHOTO = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def box(a: np.ndarray, r: int, axis: int) -> np.ndarray:
    if r < 1:
        return a
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r + 1, r)
    c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis, dtype=np.float64)
    n = a.shape[axis]
    hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / (2 * r + 1)).astype(np.float32)


def blur(a: np.ndarray, sigma: float) -> np.ndarray:
    """three box passes ≈ a gaussian of that sigma (no OpenCV/SciPy needed)."""
    r = max(1, int(round(np.sqrt(12 * sigma * sigma / 3 + 1) / 2)))
    for _ in range(3):
        a = box(box(a, r, 0), r, 1)
    return a


def smooth(x: np.ndarray, a: float, b: float) -> np.ndarray:
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


class Printer:
    def __init__(self, w: int, h: int, inks: str, ink: str, paper: str, accent: str, texture: str | None, use_accent: bool):
        self.w, self.h, self.inks, self.use_accent = w, h, inks, use_accent
        self.ink, self.paper, self.accent = hex_rgb(ink), hex_rgb(paper), hex_rgb(accent)
        self.grids = {}
        if texture and Path(texture).exists():
            t = read_frames(texture, w, h, gray=True)[0].astype(np.float32) / 255
        else:                                              # paper made of soft noise
            t = blur(np.random.default_rng(77).standard_normal((h, w)).astype(np.float32), 6)
        self.tex = (t - t.mean()) / (t.std() + 1e-6)

    def grid(self, cell: int, ang: float) -> np.ndarray:
        if (cell, ang) not in self.grids:
            yy, xx = np.mgrid[0:self.h, 0:self.w].astype(np.float32)
            a = np.deg2rad(ang)
            u = (xx * np.cos(a) + yy * np.sin(a)) / cell
            v = (-xx * np.sin(a) + yy * np.cos(a)) / cell
            self.grids[(cell, ang)] = np.sqrt((u - np.round(u)) ** 2 + (v - np.round(v)) ** 2) / 0.7071
        return self.grids[(cell, ang)]

    def dots(self, cover: np.ndarray, cell: int, ang: float) -> np.ndarray:
        return smooth(np.sqrt(np.clip(cover, 0, 1)) - self.grid(cell, ang), -0.07, 0.07)

    def __call__(self, img: np.ndarray, k: int, hits: tuple = ()) -> np.ndarray:
        """img: RGB float 0..1 (h, w, 3); k: output frame at 30 fps."""
        step = k // 2                                      # the print changes on twos (15 fps)
        t = step * 2 / FPS                                 # so both frames of a step are identical
        rng = np.random.default_rng(9000 + step)
        hit = sum(np.exp(-max(t - g, 0) / 0.09) * (t >= g - 1e-6) for g in hits)
        dxa, dya = 4 + rng.uniform(-1.5, 1.5) + 9 * hit, -3 + rng.uniform(-1.5, 1.5) - 4 * hit
        dxb, dyb = -1 + rng.uniform(-1, 1) - 3 * hit, 1 + rng.uniform(-1, 1) + 2 * hit
        r, g, b = img[..., 0], img[..., 1], img[..., 2]
        mx, mn = img.max(-1), img.min(-1)
        sat = np.where(mx > 1e-6, (mx - mn) / (mx + 1e-6), 0)
        hue = np.zeros_like(mx)
        d = mx - mn + 1e-6
        hue = np.where(mx == r, (60 * (g - b) / d) % 360, hue)
        hue = np.where(mx == g, 60 * (b - r) / d + 120, hue)
        hue = np.where(mx == b, 60 * (r - g) / d + 240, hue)
        red = (((hue <= 26) | (hue >= 335)) & (sat > 0.35) & (mx > 0.16)).astype(np.float32)
        red = blur(red, 1.5) * np.clip((sat - 0.35) / 0.3, 0, 1) * (0.5 + 0.5 * sat)
        if not self.use_accent:
            red = np.zeros_like(red)
        lum = img @ np.array([0.30, 0.59, 0.11], np.float32)
        low = np.random.default_rng(11000 + step).standard_normal((self.h // 8 + 1, self.w // 8 + 1)).astype(np.float32)
        boil = blur(np.repeat(np.repeat(blur(low, 1.2), 8, 0), 8, 1)[:self.h, :self.w], 4) * 0.10
        m_acc = np.roll(self.dots(red * 0.95, 9, 15) * np.clip(1 + boil, 0, 1.2), (int(round(dya)), int(round(dxa))), (0, 1))
        tex = self.tex[..., None]
        if self.inks == "night":
            cover = np.clip((lum - 0.15) / 0.80, 0, 1) * (1 - red)
            m = np.roll(self.dots(cover, 9, 45) * np.clip(1 + boil + 0.05 * self.tex, 0, 1.2), (int(round(dyb)), int(round(dxb))), (0, 1))
            stock = self.ink * (1 + 0.0875 * tex)
            out = stock * (1 - m[..., None]) + self.paper * (0.94 + 0.06 * tex) * m[..., None]
            out = out * (1 - 0.92 * m_acc[..., None]) + self.accent * 0.92 * m_acc[..., None]
        else:
            cover = np.clip((0.96 - lum) / 0.9, 0, 1) * (1 - red)
            m = np.roll(self.dots(cover, 9, 45) * np.clip(1 + boil + 0.05 * self.tex, 0, 1.2), (int(round(dyb)), int(round(dxb))), (0, 1))
            out = self.paper * (1 + 0.06 * tex)
            out = out * (1 - m_acc[..., None] * (1 - self.accent))
            out = out * (1 - m[..., None] * (1 - self.ink) * 0.95)
        grain = np.random.default_rng(12000 + step).standard_normal((self.h, self.w)).astype(np.float32) * 0.012
        return np.clip(out + grain[..., None], 0, 1)


def read_frames(src: str, w: int, h: int, start: float = 0.0, dur: float | None = None, gray: bool = False) -> np.ndarray:
    photo = Path(src).suffix.lower() in PHOTO
    cmd = ["ffmpeg", "-v", "error"] + ([] if photo else ["-ss", f"{start:.3f}"]) + ["-i", str(src)]
    if dur and not photo:
        cmd += ["-t", f"{dur + 0.2:.3f}"]
    cmd += ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}", "-frames:v", "1"] if photo else \
           ["-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"]
    cmd += ["-f", "rawvideo", "-pix_fmt", "gray" if gray else "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w) if gray else np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def source_fps(src: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", str(src)], capture_output=True, text=True).stdout.strip() or "30/1"
    a, _, b = r.partition("/")
    return float(a) / float(b or 1)


def frames_on_twos(src: str, w: int, h: int, dur: float, start: float = 0.0, push: float = 0.0, dy: int = 0):
    photo = Path(src).suffix.lower() in PHOTO
    a = read_frames(src, w, h, start, dur)
    f_src = 1.0 if photo else source_fps(src)
    n = int(round(dur * FPS))
    for k in range(n):
        i = 0 if photo else min(int(round((k // 2) * 2 / FPS * f_src)), len(a) - 1)
        f = a[i].astype(np.float32) / 255
        if push:                                           # nearest-neighbour push from the centre, also on twos
            s = 1 + push * ((k // 2) * 2) / max(n - 1, 1)
            ys = np.clip(((np.arange(h) - h / 2) / s + h / 2).astype(int), 0, h - 1)
            xs = np.clip(((np.arange(w) - w / 2) / s + w / 2).astype(int), 0, w - 1)
            f = f[ys][:, xs]
        if dy:
            f = np.concatenate([np.repeat(f[:1], dy, 0), f[:-dy]], 0)
        yield f


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--dur", type=float, required=True, help="output seconds")
    ap.add_argument("--start", type=float, default=0.0, help="second of the clip to start from")
    ap.add_argument("--hits", default="", help="output seconds where the misregistration jumps (the keywords)")
    ap.add_argument("--inks", choices=["paper", "night"], default="paper")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--ink", default="#151412"); ap.add_argument("--paper", default="#efeee8"); ap.add_argument("--accent", default="#e8331f")
    ap.add_argument("--texture", help="a paper scan; without it the paper is made of soft noise")
    ap.add_argument("--no-accent", action="store_true", help="everything in the base ink (footage with skin)")
    ap.add_argument("--push", type=float, default=0.0, help="photos: slow push (0.06 = 6 %%)")
    ap.add_argument("--dy", type=int, default=0, help="move the picture down N px (room for type above)")
    a = ap.parse_args(argv)
    w, h = (int(x) for x in a.size.lower().split("x"))
    ink, paper = (a.ink, a.paper) if a.inks == "paper" else ("#0e0e0f", "#efeee8")
    pr = Printer(w, h, a.inks, ink, paper, a.accent, a.texture, not a.no_accent)
    hits = tuple(float(x) for x in a.hits.split(",") if x.strip())
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-g", "6", "-pix_fmt", "yuv420p",
                          "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(a.out)], stdin=subprocess.PIPE)
    last = None
    for k, f in enumerate(frames_on_twos(a.src, w, h, a.dur, a.start, a.push, a.dy)):
        if k % 2 == 0 or last is None:                     # one print per step, written twice
            last = (pr(f, k, hits) * 255 + 0.5).astype(np.uint8).tobytes()
        p.stdin.write(last)
    p.stdin.close()
    return p.wait()


if __name__ == "__main__":
    raise SystemExit(main())
