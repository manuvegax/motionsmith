"""Depth captions for a talking head: one big word behind the head, the rest of the words as captions in front.

Every frame is a stack, back to front: the original frame, the big word, the person cut out of that same frame, the
captions. A slow virtual camera pushes through the stack at three depths (the plate, the word behind the head, the
captions in front), so the type sits in the room instead of on the glass. Each word lands on the frame where it is
heard: speech-to-text starts words early, so every start is moved to where the voice gets loud.

  python -I <skill>/scripts/depth_captions.py words <clip.mp4> --out <piece>/words.json [--language es]
  python -I <skill>/scripts/depth_captions.py words <clip.mp4> --words <piece>/words.json --out <piece>/words.json   # re-snap after edits
  python -I <skill>/scripts/depth_captions.py matte <clip.mp4> --words <piece>/words.json --word MIEDO --out <piece>/matte
  python -I <skill>/scripts/depth_captions.py storyboard <clip.mp4> --words <piece>/words.json --word MIEDO --matte <piece>/matte --out <piece>/preview/board
  python -I <skill>/scripts/depth_captions.py render <clip.mp4> --words <piece>/words.json --word MIEDO --matte <piece>/matte --out <piece>/final/clip.mp4

`words`: faster-whisper (word timestamps, no initial prompt, fed a 16 kHz array, never a path), then every start
snapped to the voice's onset; prints the line with doubtful words marked [?] for the person to check. With --words it
only re-snaps a list the person corrected (a fixed word keeps the time of the word it replaced).
`matte`: a soft alpha of the person on every frame from the big word to the end, with a local ONNX model
(birefnet-portrait, isnet, u2net: the files rembg keeps in ~/.u2net) run by onnxruntime. Nothing is downloaded: a
missing model stops with its size and where it goes.
`render`: the stack, H.264 with the source's own colour tags and its audio, a still of the big word, and
`<out>.events.json` (the times of the word and of each caption group, for sound design).

Numbers (from a published breakdown, see references/edit/depth-captions.md): big word ~85 % of the width, the head
overlapping ~60 % of its letter height and covering at least 15 % of its ink; it pops 80 -> 105 -> 100 % over 6
frames; captions up to 3 words, ~7 % of the width, between 15 % and 65 % of the height, above the big word, never on
it, and the big word is not captioned twice.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata

import numpy as np

SKILL = Path(__file__).resolve().parents[1]
FONT = SKILL / "templates" / "fonts" / "Archivo-VF.ttf"
SR = 16000
STOP = set("""a al algo como con de del el ella ellos en era es esa ese eso esta este esto fue ha hay la las le lo los
mas me mi muy no nos o para pero por que se si sin su sus te tu un una uno y ya yo the a an and are as at be but by for
from i in is it its me my of on or so that the this to was we with you your""".split())
MODELS = {  # file stem -> (input size, mean, std, sigmoid, approx MB)
    "birefnet": (1024, (.485, .456, .406), (.229, .224, .225), True, 973),
    "isnet": (1024, (.485, .456, .406), (1., 1., 1.), False, 179),
    "u2net": (320, (.485, .456, .406), (.229, .224, .225), False, 176),
}
PREFERRED = ["birefnet-portrait", "birefnet-general", "u2net_human_seg", "isnet-general-use", "u2net"]


def say(*a):
    print(*a, file=sys.stderr, flush=True)


def norm(w: str) -> str:
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^0-9a-zñ]", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


# ---------------------------------------------------------------- video in and out
def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(round(float(sd["rotation"])))
    rot = rot or int(v.get("tags", {}).get("rotate", 0) or 0)
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, _, den = v.get("r_frame_rate", "30/1").partition("/")
    fps = float(num) / float(den or 1)
    dur = float(v.get("duration") or data.get("format", {}).get("duration") or 0)
    trc = v.get("color_transfer") or ""
    matrix = v.get("color_space") or ""
    if matrix in ("", "unknown", "reserved"):
        matrix = "bt709" if h >= 720 or w >= 720 else "smpte170m"
    return {"w": w, "h": h, "fps": fps, "rate": v.get("r_frame_rate", "30/1"), "duration": dur,
            "frames": int(v.get("nb_frames") or round(dur * fps)), "matrix": matrix,
            "range": "pc" if v.get("color_range") == "pc" else "tv", "hdr": trc in ("arib-std-b67", "smpte2084"),
            "primaries": v.get("color_primaries") or "bt709", "trc": trc or "bt709",
            "audio": any(s["codec_type"] == "audio" for s in data["streams"])}


def swscale_matrix(m: str) -> str:
    return {"bt709": "bt709", "smpte170m": "bt601", "bt470bg": "bt601", "bt2020nc": "bt2020", "bt2020c": "bt2020",
            "fcc": "fcc", "smpte240m": "smpte240m"}.get(m, "bt709")


def decode(path: Path, info: dict):
    """Yield RGB frames as uint8 arrays, converted with the source's own matrix (HDR is tone-mapped to BT.709)."""
    if info["hdr"]:
        vf = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
              "zscale=t=bt709:m=bt709:r=tv,format=rgb24")
    else:
        vf = f"scale=in_color_matrix={swscale_matrix(info['matrix'])}:in_range={info['range']},format=rgb24"
    p = subprocess.Popen(["ffmpeg", "-v", "fatal", "-i", str(path), "-map", "0:v:0", "-vf", vf, "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE)   # fatal only: stopping early (a storyboard) closes the pipe on purpose
    size = info["w"] * info["h"] * 3
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield np.frombuffer(buf, np.uint8).reshape(info["h"], info["w"], 3)
    finally:
        p.stdout.close()
        if p.poll() is None:
            p.terminate()
        p.wait()


def encoder(path: Path, src: Path, info: dict):
    if info["hdr"]:
        matrix, prim, trc, rng = "bt709", "bt709", "bt709", "tv"
    else:
        matrix, prim, trc, rng = info["matrix"], info["primaries"], info["trc"], info["range"]
    cmd = ["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{info['w']}x{info['h']}",
           "-r", info["rate"], "-i", "-"]
    if info["audio"]:
        cmd += ["-i", str(src), "-map", "0:v", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
    # setparams writes the tags on the frames themselves (newer FFmpeg takes them from the frames, not the options);
    # no -shortest: it stops reading the picture when the audio ends and drops the last frames.
    rng_name = "pc" if rng == "pc" else "tv"
    cmd += ["-vf", f"scale=out_color_matrix={swscale_matrix(matrix)}:out_range={rng},format=yuv420p,"
                   f"setparams=color_primaries={prim}:color_trc={trc}:colorspace={matrix}:range={rng_name}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-colorspace", matrix, "-color_primaries", prim,
            "-color_trc", trc, "-color_range", rng, "-movflags", "+faststart"]
    if info["frames"]:
        cmd += ["-t", f"{info['frames'] / info['fps']:.4f}"]
    cmd.append(str(path))
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


# ---------------------------------------------------------------- words
def audio16k(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def level_db(audio: np.ndarray, hop: float = .01) -> np.ndarray:
    n = int(SR * hop)
    frames = len(audio) // n
    if frames == 0:
        return np.zeros(0, np.float32)
    rms = np.sqrt(np.mean(audio[: frames * n].reshape(frames, n) ** 2, axis=1) + 1e-12)
    return (20 * np.log10(rms)).astype(np.float32)


def snap_onsets(words: list[dict], db: np.ndarray, hop: float = .01, before: float = .08, after: float = .25,
                rise: float = 9.0) -> list[dict]:
    """Move each start to where the voice gets loud: the first rising 10 ms step above the word's local floor + rise dB,
    searched from `before` s ahead of the transcript time to `after` s past it. Starts stay in order and before ends."""
    if not len(db):
        return words
    top = float(np.percentile(db, 98))
    out, last = [], 0.0
    for w in words:
        w = dict(w)
        s = float(w["start"])
        a, b = max(0, int((s - before) / hop)), min(len(db) - 1, int((s + after) / hop))
        floor = float(np.percentile(db[max(0, int((s - .4) / hop)): max(1, int(s / hop))], 20)) if s > .05 else float(db[: max(1, a + 1)].min())
        thr = max(floor + rise, top - 40)
        hit = None
        for i in range(max(a, 1), b + 1):
            if db[i] >= thr and db[i] > db[i - 1] and db[i - 1] < thr:
                hit = i * hop
                break
        if hit is not None and hit < float(w["end"]) - .02:
            w.setdefault("raw_start", round(s, 3))
            s = hit
        s = max(s, last)
        w["start"] = round(s, 3)
        last = s + .01
        out.append(w)
    return out


def cached_whisper(model: str, model_dir: str | None) -> str | None:
    """A faster-whisper model already on disk: a folder, or a Hugging Face cache snapshot (read without the hub)."""
    if Path(model).is_dir():
        return model
    roots = [Path(model_dir)] if model_dir else []
    hf = os.environ.get("HF_HUB_CACHE") or (Path(os.environ["HF_HOME"]) / "hub" if os.environ.get("HF_HOME") else None)
    roots += [Path(hf)] if hf else []
    roots.append(Path.home() / ".cache" / "huggingface" / "hub")
    for root in roots:
        for snap in sorted(root.glob(f"models--Systran--faster-whisper-{model}/snapshots/*/model.bin")):
            return str(snap.parent)
    return None


def transcribe(path: Path, model: str, language: str | None, model_dir: str | None, allow_download: bool) -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit(f"faster-whisper is not installed for this Python ({exc}); ask before installing it, or pass "
                         f"--words with timings from another tool (ElevenLabs, Whisper, an SRT turned into JSON).")
    local = cached_whisper(model, model_dir)
    if local is None and not allow_download:
        raise SystemExit(f"The faster-whisper model '{model}' is not on this computer. It downloads once (small ~0.5 GB): "
                         f"ask the person, then run again with --allow-download.")
    try:
        wm = WhisperModel(local or model, device="cpu", compute_type="int8", download_root=model_dir)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"faster-whisper could not load '{local or model}': {exc}")
    segments, _ = wm.transcribe(audio16k(path), language=language, word_timestamps=True, initial_prompt=None,
                                condition_on_previous_text=False, vad_filter=False)
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append({"text": text, "start": round(float(w.start), 3), "end": round(float(w.end), 3),
                              "prob": round(float(w.probability), 3)})
    return words


def show_line(words: list[dict]) -> str:
    return " ".join(w["text"] + ("[?]" if w.get("prob", 1) < .5 else "") for w in words)


def pick_word(words: list[dict], wanted: str | None, index: int | None) -> int:
    if index is not None:
        if not 0 <= index < len(words):
            raise SystemExit(f"--word-index {index} is outside the {len(words)} words")
        return index
    if wanted:
        target = norm(wanted)
        for i, w in enumerate(words):
            if norm(w["text"]) == target:
                return i
        raise SystemExit(f"'{wanted}' is not in the words: {show_line(words)}")
    span = words[-1]["end"] if words else 1
    best, score = 0, -1.0
    for i, w in enumerate(words):
        n = norm(w["text"])
        if not n or n in STOP:
            continue
        s = (10 if any(c.isdigit() for c in n) else 0) + len(n) - (4 if w["start"] > .7 * span else 0)
        if s > score:
            best, score = i, s
    return best


def caption_groups(words: list[dict], big: int, end: float, max_words: int = 3, max_chars: int = 18,
                   gap: float = .3, linger: float = 1.2) -> list[dict]:
    """Up to `max_words` words per group, split at punctuation, pauses and the big word (never captioned)."""
    groups, cur = [], []

    def close():
        if cur:
            groups.append({"words": [dict(w) for w in cur], "start": cur[0]["start"]})
            cur.clear()
    for i, w in enumerate(words):
        if i == big:
            close()
            continue
        if cur and (len(cur) >= max_words or re.search(r"[.,;:?!…]$", cur[-1]["text"])
                    or w["start"] - cur[-1]["end"] > gap or len(" ".join(x["text"] for x in cur + [w])) > max_chars):
            close()
        cur.append(w)
    close()
    for g, nxt in zip(groups, groups[1:] + [None]):
        stop = g["words"][-1]["end"] + linger
        g["end"] = round(min(nxt["start"] if nxt else end, stop, end), 3)
    return groups


# ---------------------------------------------------------------- matte
def model_path(name: str | None) -> Path:
    home = Path(os.environ.get("U2NET_HOME") or Path.home() / ".u2net")
    if name and Path(name).suffix == ".onnx":
        p = Path(name)
        if p.exists():
            return p
        raise SystemExit(f"Model file not found: {p}")
    names = [name] if name else PREFERRED
    for n in names:
        p = home / f"{n}.onnx"
        if p.exists():
            return p
    want = name or "birefnet-portrait"
    kind = next((k for k in MODELS if want.startswith(k)), "birefnet")
    raise SystemExit(f"No cut-out model '{want}' in {home}. It is a one-time download of about {MODELS[kind][4]} MB "
                     f"(rembg keeps its models there as <name>.onnx). Ask the person before downloading; nothing was "
                     f"downloaded. Found there: {sorted(x.name for x in home.glob('*.onnx')) if home.exists() else 'nothing'}")


class Matter:
    def __init__(self, path: Path):
        import onnxruntime as ort
        stem = path.stem.lower()
        kind = next((k for k in MODELS if stem.startswith(k)), "u2net")
        self.size, self.mean, self.std, self.sigmoid, _ = MODELS[kind]
        self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        self.input = self.session.get_inputs()[0].name
        self.kind = kind

    def __call__(self, rgb: np.ndarray) -> np.ndarray:
        from PIL import Image
        img = Image.fromarray(rgb).resize((self.size, self.size), Image.LANCZOS)
        a = np.asarray(img, np.float32)
        a = a / max(float(a.max()), 1e-6)
        a = (a - np.array(self.mean, np.float32)) / np.array(self.std, np.float32)
        out = self.session.run(None, {self.input: a.transpose(2, 0, 1)[None].astype(np.float32)})[0][:, 0]
        if self.sigmoid:
            out = 1 / (1 + np.exp(-out))
        lo, hi = float(out.min()), float(out.max())
        pred = (out[0] - lo) / max(hi - lo, 1e-6)
        mask = Image.fromarray((pred * 255).astype(np.uint8)).resize((rgb.shape[1], rgb.shape[0]), Image.LANCZOS)
        return np.asarray(mask)


def load_matte(folder: Path, i: int) -> np.ndarray | None:
    p = folder / f"{i:06d}.png"
    if not p.exists():
        return None
    from PIL import Image
    return np.asarray(Image.open(p).convert("L"))


# ---------------------------------------------------------------- type
def font(size: int, weight: float, width: float):
    from PIL import ImageFont
    f = ImageFont.truetype(str(FONT), max(4, int(size)))
    try:
        axes = f.get_variation_axes()
        vals = []
        for ax in axes:
            tag = (ax.get("name") or b"")
            tag = tag.decode() if isinstance(tag, bytes) else str(tag)
            lo, hi = ax["minimum"], ax["maximum"]
            v = weight if "eight" in tag else width if "idth" in tag else ax.get("default", lo)
            vals.append(min(hi, max(lo, v)))
        f.set_variation_by_axes(vals)
    except (OSError, AttributeError):
        pass
    return f


def sprite(text: str, size: int, weight: float, width: float, color=(255, 255, 255), tracking: float = 0.0):
    """Ink-tight RGBA sprite of a line of text, plus its ink box height."""
    from PIL import Image, ImageDraw
    f = font(size, weight, width)
    x0, y0, x1, y1 = f.getbbox(text)
    pad = int(size * .1)
    img = Image.new("L", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), 0)
    ImageDraw.Draw(img).text((pad - x0, pad - y0), text, font=f, fill=255)
    a = np.asarray(img, np.float32) / 255
    rgba = np.zeros(a.shape + (4,), np.float32)
    rgba[..., :3] = np.array(color, np.float32) / 255
    rgba[..., 3] = a
    return rgba, pad


def line_sprite(text: str, size: int, weight: float, width: float, color=(255, 255, 255)):
    """RGBA sprite on the font's line box (ascent + descent, advance width), so words drawn one by one share a baseline
    and centre on their advance."""
    from PIL import Image, ImageDraw
    f = font(size, weight, width)
    asc, desc = f.getmetrics()
    pad = int(size * .25)
    adv = f.getlength(text)
    img = Image.new("L", (int(math.ceil(adv)) + 2 * pad, asc + desc + 2 * pad), 0)
    ImageDraw.Draw(img).text((pad, pad + asc), text, font=f, fill=255, anchor="ls")
    a = np.asarray(img, np.float32) / 255
    rgba = np.zeros(a.shape + (4,), np.float32)
    rgba[..., :3] = np.array(color, np.float32) / 255
    rgba[..., 3] = a
    return rgba


def fit_size(text: str, target_w: float, weight: float, width: float) -> int:
    size = 200
    for _ in range(3):
        f = font(size, weight, width)
        x0, _, x1, _ = f.getbbox(text)
        size = max(8, int(size * target_w / max(1, x1 - x0)))
    return size


def head_top(matte: np.ndarray, band: float = .4, thresh: int = 128) -> int | None:
    """Top of the head: the highest row where the person fills a few pixels of the middle `band` of the frame (a raised
    hand at the side does not count)."""
    h, w = matte.shape
    a, b = int(w * (.5 - band / 2)), int(w * (.5 + band / 2))
    rows = np.nonzero((matte[:, a:b] >= thresh).sum(axis=1) >= max(3, (b - a) // 60))[0]
    return int(rows[0]) if len(rows) else None


def place_word(matte: np.ndarray, ink: np.ndarray, overlap: float = .6, min_cover: float = .15,
               floor_frac: float = .06, step_frac: float = .01) -> tuple[int, float]:
    """Top y of the word's ink box so the head overlaps `overlap` of its height; lowered until the head covers at least
    `min_cover` of its ink. Returns (y, coverage). `ink` is the word's alpha (h x w) centred horizontally."""
    H, W = matte.shape
    hh, ww = ink.shape
    top = head_top(matte)
    if top is None:
        return int(H * .2), 0.0
    y = max(int(H * floor_frac), int(top - (1 - overlap) * hh))
    x = (W - ww) // 2

    def cover(yy):
        ys, ye = max(0, yy), min(H, yy + hh)
        xs, xe = max(0, x), min(W, x + ww)
        if ye <= ys or xe <= xs:
            return 0.0
        part = ink[ys - yy: ye - yy, xs - x: xe - x]
        m = matte[ys:ye, xs:xe] >= 128
        total = float(ink.sum())
        return float((part * m).sum()) / total if total else 0.0
    c = cover(y)
    step = max(1, int(H * step_frac))
    while c < min_cover and y + hh < H * .75:
        y += step
        c = cover(y)
    return y, c


def over(base: np.ndarray, rgba: np.ndarray, x: float, y: float, scale: float = 1.0, opacity: float = 1.0) -> None:
    """Composite an RGBA float sprite onto a float RGB frame, its centre at (x, y), scaled about its centre."""
    from PIL import Image
    if scale != 1.0:
        h, w = rgba.shape[:2]
        nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
        rgba = np.stack([np.asarray(Image.fromarray(rgba[..., c]).resize((nw, nh), Image.BICUBIC)) for c in range(4)], -1)
        rgba = np.clip(rgba, 0, 1)
    h, w = rgba.shape[:2]
    x0, y0 = int(round(x - w / 2)), int(round(y - h / 2))
    H, W = base.shape[:2]
    xs, ys, xe, ye = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xe <= xs or ye <= ys:
        return
    s = rgba[ys - y0: ye - y0, xs - x0: xe - x0]
    a = s[..., 3:4] * opacity
    base[ys:ye, xs:xe] = base[ys:ye, xs:xe] * (1 - a) + s[..., :3] * a


def shadowed(rgba: np.ndarray, radius: float, alpha: float = .45, dy: int = 0) -> np.ndarray:
    from PIL import Image, ImageFilter
    pad = int(radius * 2.5) + abs(dy)
    h, w = rgba.shape[:2]
    big = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    sh = Image.fromarray((rgba[..., 3] * 255).astype(np.uint8))
    canvas = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    canvas.paste(sh, (pad, pad + dy))
    soft = np.asarray(canvas.filter(ImageFilter.GaussianBlur(radius)), np.float32) / 255 * alpha
    big[..., 3] = soft
    a = np.zeros_like(big)
    a[pad:pad + h, pad:pad + w] = rgba
    out_a = a[..., 3:4] + big[..., 3:4] * (1 - a[..., 3:4])
    rgb = (a[..., :3] * a[..., 3:4]) / np.maximum(out_a, 1e-6)
    return np.concatenate([rgb, out_a], -1)


def pop(u: float) -> float:
    """80 % -> 105 % -> 100 % over 6 frames (u = frames since the word / 6)."""
    if u <= 0:
        return .8
    if u >= 1:
        return 1.0
    keys = [(0, .8), (.6, 1.05), (1, 1.0)]
    for (a, va), (b, vb) in zip(keys, keys[1:]):
        if u <= b:
            k = (u - a) / (b - a)
            k = 1 - (1 - k) ** 3
            return va + (vb - va) * k
    return 1.0


# ---------------------------------------------------------------- the stack
class Stack:
    def __init__(self, info: dict, words: list[dict], big: int, args):
        self.info, self.words, self.big = info, words, big
        W, H = info["w"], info["h"]
        self.W, self.H = W, H
        self.word_t = float(words[big]["start"])
        self.word_f = int(math.floor(self.word_t * info["fps"] + 1e-6))
        self.color = tuple(int(args.color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        text = (args.display or words[big]["text"]).strip(" .,;:!?¿¡\"'«»").upper()
        size = fit_size(text, W * args.width, 860, 66)
        self.word_sprite, _ = sprite(text, size, 860, 66, self.color)
        self.word_text = text
        self.camera = args.camera
        self.y_word = None
        self.coverage = None
        self.cap_size = int(W * .07)
        self.cap_font = font(self.cap_size, 700, 100)
        self.groups = caption_groups(words, big, info["duration"] or words[-1]["end"] + 1)
        self.cap_cache = {}
        self.plate0 = None
        self.cap_place = "above the word"
        self.wall_luma, self.low_contrast = None, False

    def set_matte(self, matte: np.ndarray):
        ink = self.word_sprite[..., 3]
        y, c = place_word(matte, ink)
        self.y_word, self.coverage = y, c
        hh = ink.shape[0]
        self.word_cy = y + hh / 2
        cap_h = self.cap_size * 1.25
        gap = .02 * self.H
        above = y - gap - cap_h / 2
        if above - cap_h / 2 >= .15 * self.H:          # room above the big word, under the app's top bar
            self.cap_cy, self.cap_place = float(above), "above the word"
        else:                                          # never on it: just under the word, inside the 65 % line
            self.cap_cy = float(min(y + hh + gap + cap_h / 2, .65 * self.H - cap_h / 2))
            self.cap_place = "below the word (no room above)"
        # Ink against the wall behind it (person excluded): a light ink on a light wall does not read.
        x0 = (self.W - ink.shape[1]) // 2
        box = (slice(max(0, y), min(self.H, y + hh)), slice(max(0, x0), min(self.W, x0 + ink.shape[1])))
        self.wall_luma = None
        if self.plate0 is not None:
            lum = self.plate0[box].astype(np.float32) @ np.array([.2126, .7152, .0722], np.float32) / 255
            keep = (ink[: lum.shape[0], : lum.shape[1]] > .5) & (matte[box] < 128)
            if keep.sum() > 50:
                self.wall_luma = float(np.median(lum[keep]))
        ink_l = (.2126 * self.color[0] + .7152 * self.color[1] + .0722 * self.color[2]) / 255
        self.low_contrast = self.wall_luma is not None and abs(ink_l - self.wall_luma) < .35

    def cam(self, t: float) -> float:
        """Push progress: eases in over 0.6 s, then constant speed to the last frame (a moving hold, never a stop)."""
        if self.camera == "still":
            return 0.0
        dur = max(self.info["duration"], 1e-3)
        ramp = .6
        v = 1 / (dur - ramp / 2)
        return (t * t / (2 * ramp) * v) if t < ramp else (ramp / 2 + (t - ramp)) * v

    def caption(self, text: str):
        if text not in self.cap_cache:
            rgba = line_sprite(text, self.cap_size, 700, 100, (255, 255, 255))
            self.cap_cache[text] = shadowed(rgba, self.cap_size * .12, .5, int(self.cap_size * .04))
        return self.cap_cache[text]

    def frame(self, i: int, rgb: np.ndarray, matte: np.ndarray | None) -> np.ndarray:
        from PIL import Image
        t = i / self.info["fps"]
        W, H = self.W, self.H
        p = self.cam(t)
        s_plate, s_word, s_cap = 1 + .035 * p, 1 + .026 * p, 1 + .05 * p
        plate = rgb
        if s_plate != 1:
            nw, nh = int(round(W * s_plate)), int(round(H * s_plate))
            x0, y0 = (nw - W) // 2, (nh - H) // 2
            plate = np.asarray(Image.fromarray(rgb).resize((nw, nh), Image.BICUBIC))[y0:y0 + H, x0:x0 + W]
            if matte is not None:
                matte = np.asarray(Image.fromarray(matte).resize((nw, nh), Image.BICUBIC))[y0:y0 + H, x0:x0 + W]
        out = plate.astype(np.float32) / 255
        cx, cy = W / 2, H / 2
        if i >= self.word_f and self.y_word is not None:
            u = (i - self.word_f) / 6
            wy = cy + (self.word_cy - cy) * s_word
            over(out, self.word_sprite, cx, wy, pop(u) * s_word)
            if matte is not None:
                a = (matte.astype(np.float32) / 255)[..., None]
                out = (plate.astype(np.float32) / 255) * a + out * (1 - a)
        for g in self.groups:
            if not g["start"] <= t < g["end"]:
                continue
            # The whole group is laid out once, centred; each word appears in its own slot when it is said, so the
            # words already on screen never re-centre.
            texts = [w["text"] for w in g["words"]]
            fnt = self.cap_font
            x_left = cx - fnt.getlength(" ".join(texts)) * s_cap / 2
            ccy = cy + (self.cap_cy - cy) * s_cap
            for j, w in enumerate(g["words"]):
                if t < w["start"]:
                    break
                off = fnt.getlength(" ".join(texts[:j]) + (" " if j else ""))
                k = min(1.0, (t - w["start"]) * self.info["fps"] / 4)   # 4 frames: rise 1.2 % H, 90 -> 100 %
                ease = 1 - (1 - k) ** 3
                wx = x_left + (off + fnt.getlength(w["text"]) / 2) * s_cap
                over(out, self.caption(w["text"]), wx, ccy + (1 - ease) * .012 * H, s_cap * (.9 + .1 * ease),
                     min(1.0, .25 + ease))
            break
        return (np.clip(out, 0, 1) * 255 + .5).astype(np.uint8)


# ---------------------------------------------------------------- commands
def read_words(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    words = data["words"] if isinstance(data, dict) else data
    return [{"text": str(w.get("text", w.get("word", ""))).strip(), "start": float(w["start"]), "end": float(w["end"]),
             **({"prob": w["prob"]} if "prob" in w else {})} for w in words if str(w.get("text", w.get("word", ""))).strip()]


def cmd_words(a) -> int:
    if a.words:
        words = read_words(a.words)
    else:
        words = transcribe(a.video, a.model, a.language, a.model_dir, a.allow_download)
    snapped = snap_onsets(words, level_db(audio16k(a.video)))
    moved = [w for w in snapped if "raw_start" in w and abs(w["start"] - w["raw_start"]) >= .02]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps({"words": snapped}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    shift = float(np.median([w["start"] - w["raw_start"] for w in moved])) if moved else 0.0
    print(json.dumps({"words": len(snapped), "line": show_line(snapped), "doubtful": [w["text"] for w in snapped if w.get("prob", 1) < .5],
                      "snapped_to_voice": len(moved), "median_shift_s": round(shift, 3), "out": str(a.out),
                      "next": "Show the line to the person; fix names and doubtful words in the JSON (keep their times), "
                              "then run words again with --words to re-snap."}, ensure_ascii=False, indent=2))
    return 0


def cmd_matte(a) -> int:
    info = probe(a.video)
    words = read_words(a.words)
    big = pick_word(words, a.word, a.word_index)
    start_f = max(0, int(math.floor(words[big]["start"] * info["fps"])) - a.lead)
    path = model_path(a.model)
    m = Matter(path)
    a.out.mkdir(parents=True, exist_ok=True)
    todo = max(1, info["frames"] - start_f)
    say(f"cut-out with {path.name} ({m.kind}) from frame {start_f}: {todo} frames, a few seconds each on a CPU")
    done = 0
    for i, rgb in enumerate(decode(a.video, info)):
        if i < start_f:
            continue
        target = a.out / f"{i:06d}.png"
        if target.exists():
            continue
        from PIL import Image
        Image.fromarray(m(rgb)).save(target, optimize=False, compress_level=3)
        done += 1
        if done % 10 == 0:
            say(f"  {done}/{todo}")
    print(json.dumps({"model": path.name, "from_frame": start_f, "written": done, "folder": str(a.out)}, indent=2))
    return 0


def setup(a):
    info = probe(a.video)
    words = read_words(a.words)
    big = pick_word(words, a.word, a.word_index)
    return info, words, big, Stack(info, words, big, a)


def cmd_render(a, board: bool = False) -> int:
    info, words, big, st = setup(a)
    if not board and a.out.exists():
        raise SystemExit(f"{a.out} exists; Motionsmith never overwrites a render: choose a new name")
    first = load_matte(a.matte, st.word_f)
    if first is None:
        raise SystemExit(f"No matte for frame {st.word_f} in {a.matte}: run the matte step first")
    for i, rgb in enumerate(decode(a.video, info)):
        if i == st.word_f:
            st.plate0 = rgb.copy()
            break
    st.set_matte(first)
    placement = {"word": st.word_text, "word_y": st.y_word, "head_covers": round(st.coverage, 3),
                 "captions": st.cap_place, "wall_luma": None if st.wall_luma is None else round(st.wall_luma, 2)}
    if st.low_contrast:
        placement["warning_contrast"] = ("the word's ink is close to the wall behind it: try a dark ink (--color #111111) "
                                          "or the brand accent")
    still_f = st.word_f + int(round(.5 * info["fps"]))
    if board:
        targets = sorted({st.word_f + 6, still_f} | {int((g["start"] + min(.6, (g["end"] - g["start"]) * .7)) * info["fps"]) for g in st.groups})
        a.out.mkdir(parents=True, exist_ok=True)
        from PIL import Image
        saved = []
        for i, rgb in enumerate(decode(a.video, info)):
            if i in targets:
                img = st.frame(i, rgb, load_matte(a.matte, i) if i >= st.word_f else None)
                p = a.out / f"board_{i:05d}_{i / info['fps']:06.2f}s.png"
                Image.fromarray(img).save(p)
                saved.append(str(p))
            if i > max(targets):
                break
        print(json.dumps({"stills": saved, **placement}, ensure_ascii=False, indent=2))
        return 0
    a.out.parent.mkdir(parents=True, exist_ok=True)
    enc = encoder(a.out, a.video, info)
    from PIL import Image
    missing, n = 0, 0
    still = a.out.with_suffix(".png")
    for i, rgb in enumerate(decode(a.video, info)):
        matte = load_matte(a.matte, i) if i >= st.word_f else None
        if i >= st.word_f and matte is None:
            missing += 1
        img = st.frame(i, rgb, matte)
        if i == still_f:
            Image.fromarray(img).save(still)
        enc.stdin.write(img.tobytes())
        n += 1
    enc.stdin.close()
    if enc.wait() != 0:
        raise SystemExit("ffmpeg failed while encoding")
    events = [{"t": round(st.word_t, 3), "role": f"big word {st.word_text}"}] + \
             [{"t": g["start"], "role": "caption " + " ".join(w["text"] for w in g["words"])} for g in st.groups]
    Path(str(a.out) + ".events.json").write_text(json.dumps(events, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    report = {"out": str(a.out), "still": str(still), "frames": n, "size": f"{info['w']}x{info['h']}",
              "fps": round(info["fps"], 3), "word_at": st.word_t, **placement,
              "caption_groups": len(st.groups), "frames_without_matte": missing, "hdr_tone_mapped": info["hdr"],
              "events": str(a.out) + ".events.json",
              "next": "Check the still, then watch it on the phone: timing and the edge round the head are judged there."}
    if st.coverage < .15:
        report["warning"] = "the head covers under 15 % of the word: the 'behind' does not read; lower the word or pick another"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("words", help="word timings, snapped to the voice")
    w.add_argument("video", type=Path)
    w.add_argument("--out", type=Path, required=True)
    w.add_argument("--words", type=Path, help="re-snap this corrected list instead of transcribing")
    w.add_argument("--model", default="small")
    w.add_argument("--language")
    w.add_argument("--model-dir")
    w.add_argument("--allow-download", action="store_true", help="only after the person agreed (~0.5 GB for small)")
    for name in ("matte", "storyboard", "render"):
        p = sub.add_parser(name)
        p.add_argument("video", type=Path)
        p.add_argument("--words", type=Path, required=True)
        p.add_argument("--word", help="the word behind the head (default: the strongest content word)")
        p.add_argument("--word-index", type=int)
        p.add_argument("--out", type=Path, required=True)
        if name == "matte":
            p.add_argument("--model", help="birefnet-portrait (default when present), isnet-general-use, u2net_human_seg or a .onnx path")
            p.add_argument("--lead", type=int, default=0, help="also cut out this many frames before the word")
        else:
            p.add_argument("--matte", type=Path, required=True)
            p.add_argument("--display", help="text to show for the big word (e.g. a number written out)")
            p.add_argument("--color", default="#ffffff")
            p.add_argument("--width", type=float, default=.85, help="big word width as a share of the frame")
            p.add_argument("--camera", choices=["push", "still"], default="push")
    a = ap.parse_args()
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print(json.dumps({"errors": ["ffmpeg and ffprobe are needed"]}))
        return 2
    if a.cmd == "words":
        return cmd_words(a)
    if a.cmd == "matte":
        return cmd_matte(a)
    return cmd_render(a, board=a.cmd == "storyboard")


if __name__ == "__main__":
    raise SystemExit(main())
