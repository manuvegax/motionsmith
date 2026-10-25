"""Audio to per-frame envelopes for audio-reactive motion (the code version of AE "Convert Audio to Keyframes").

Writes JSON (and optionally a JS file setting window.AUDIO_ENV) with one value per video frame, 0..1:
overall RMS and three bands (low 20-150 Hz, mid 150-2000 Hz, high 2-12 kHz), smoothed with attack/release
like a meter, plus suggested `hits` from attack detection to paste into plan.json after reviewing them.

Levels are RMS in dB relative to full scale. --norm shared (default) maps every curve against the loudest
value of the clip, so a quiet band stays quiet instead of swinging 0..1 on its own hiss; --norm band gives
each curve its own top (the old behaviour); --norm absolute uses fixed dB (--floor-db to --ceiling-db).

  python scripts/audio_envelope.py assets/soundtrack.wav --fps 60 --out preview/audio-env.json --js assets/audio-env.js
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works under python -I too
from audio_check import SR, decode, onsets, utf8_console  # noqa: E402

BANDS = {"low": (20, 150), "mid": (150, 2000), "high": (2000, 12000)}


def smooth(values: np.ndarray, fps: float, attack: float, release: float) -> np.ndarray:
    """One-pole follower: rises with the attack time constant, falls with the release one."""
    up = 1 - math.exp(-1 / max(attack * fps, 1e-6))
    down = 1 - math.exp(-1 / max(release * fps, 1e-6))
    out = np.zeros_like(values)
    level = 0.0
    for i, v in enumerate(values):
        level += (v - level) * (up if v > level else down)
        out[i] = level
    return out


def envelopes(mono: np.ndarray, fps: float, attack: float, release: float, floor_db: float,
              norm: str = "shared", ceiling_db: float = -12.0) -> tuple[dict[str, list[float]], dict[str, float]]:
    hop = SR / fps
    frames = int(round(len(mono) / hop))
    win = 2048
    window = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    raw = {name: np.zeros(frames) for name in ("rms", *BANDS)}
    # Parseval with the window's power: a band's RMS in the same full-scale units as the total RMS.
    calibration = 2 / (win * win * float(np.mean(window ** 2)))
    padded = np.concatenate([np.zeros(win // 2), mono, np.zeros(win)])
    for i in range(frames):
        start = int(round(i * hop))
        chunk = padded[start:start + win]
        raw["rms"][i] = math.sqrt(float(np.mean(chunk ** 2)))
        spectrum = np.abs(np.fft.rfft(chunk * window))
        for name, (lo, hi) in BANDS.items():
            band = spectrum[(freqs >= lo) & (freqs < hi)]
            raw[name][i] = math.sqrt(float(np.sum(band ** 2)) * calibration) if band.size else 0.0
    decibels = {name: 20 * np.log10(np.maximum(values, 1e-12)) for name, values in raw.items()}
    quiet = -70.0   # a silent or near-silent file must read as silence, not be stretched to full scale
    shared_top = max(max(float(d.max()) for d in decibels.values()), quiet)
    result, peaks = {}, {}
    for name, d in decibels.items():
        top = {"shared": shared_top, "band": max(float(d.max()), quiet), "absolute": ceiling_db}[norm]
        bottom = floor_db if norm == "absolute" else top + floor_db
        normalized = np.clip((d - bottom) / max(top - bottom, 1e-6), 0, 1)
        result[name] = [round(float(v), 4) for v in smooth(normalized, fps, attack, release)]
        peaks[name] = round(float(d.max()), 1)
    return result, peaks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("--fps", type=float, default=60)
    parser.add_argument("--attack", type=float, default=.01, help="seconds to rise")
    parser.add_argument("--release", type=float, default=.15, help="seconds to fall")
    parser.add_argument("--norm", choices=("shared", "band", "absolute"), default="shared")
    parser.add_argument("--floor-db", type=float, default=-48,
                        help="level that maps to 0: below the top (shared, band) or in dBFS (absolute)")
    parser.add_argument("--ceiling-db", type=float, default=-12, help="dBFS that maps to 1 with --norm absolute")
    parser.add_argument("--hits", type=int, default=12, help="how many attack candidates to suggest")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--js", type=Path, help="also write `window.AUDIO_ENV = {...}` for a composition")
    args = parser.parse_args()
    utf8_console()
    report = {"source": str(args.source.resolve()), "errors": []}
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        report["errors"].append("ffmpeg must be on PATH")
    elif not args.source.is_file():
        report["errors"].append("source file is missing")
    elif args.floor_db >= 0 and args.norm != "absolute":
        report["errors"].append("--floor-db must be negative")
    elif args.norm == "absolute" and args.floor_db >= args.ceiling_db:
        report["errors"].append("--floor-db must be below --ceiling-db")
    if not report["errors"]:
        try:
            mono = decode(args.source, ffmpeg).mean(axis=1)
            env, peaks = envelopes(mono, args.fps, args.attack, args.release, args.floor_db, args.norm, args.ceiling_db)
            frames = len(env["rms"])
            found = onsets(mono, args.hits)
            hits = [{"time": t, "amplitude": round(max(.3, env["rms"][min(frames - 1, int(t * args.fps))] * 1.4), 2),
                     "role": "onset (revisar)"} for t in found]
            report.update({"fps": args.fps, "frames": frames, "duration_s": round(len(mono) / SR, 3),
                           "attack_s": args.attack, "release_s": args.release, "norm": args.norm, "floor_db": args.floor_db,
                           "peak_dbfs": peaks,
                           "envelopes": env, "suggested_hits": hits,
                           "usage": "const env = window.AUDIO_ENV, f = Math.min(env.frames - 1, Math.floor(t * env.fps)); env.envelopes.low[f]; keep text and logo reactions <= 5 % scale"})
        except (RuntimeError, ValueError, OSError) as error:
            report["errors"].append(str(error))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    if args.js and not report["errors"]:
        args.js.parent.mkdir(parents=True, exist_ok=True)
        compact = {k: report[k] for k in ("fps", "frames", "envelopes", "suggested_hits")}
        args.js.write_text("window.AUDIO_ENV = " + json.dumps(compact) + ";\n", encoding="utf-8")
    summary = {k: report.get(k) for k in ("errors", "fps", "frames", "duration_s")}
    summary["suggested_hits"] = report.get("suggested_hits", [])[:6]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    sys.exit(main())
