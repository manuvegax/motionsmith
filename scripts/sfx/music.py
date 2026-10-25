"""A recorded music bed under the synthesized score: decoded by FFmpeg, aligned to the bar, looped to cover the piece,
faded in and out, and ducked on every hit of the plan so the impacts stay on top.

Cue (in cues.json, paths relative to the cues file, or to the plan when there is no cues file):
  {"voice": "music", "file": "assets/bed.wav", "gain_db": -6, "time": 0, "start": 0, "start_bar": 0, "bpm": 90,
   "beats_per_bar": 4, "loop": true, "fade_in": 0.4, "fade_out": 1.2, "duck_db": -8, "duck_attack": 0.012,
   "duck_release": 0.35}
time = when the bed enters the piece (s); start = where to start reading the file (s); start_bar + bpm = the same, in
bars (it wins over start). duck_db = how far it dips at each hit (0 = no ducking). The bed goes in after the room, so
it keeps its own space. The same file and settings give the same samples.
"""
from __future__ import annotations

import hashlib
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np

ALLOWED = {"file", "gain_db", "time", "start", "start_bar", "bpm", "beats_per_bar", "loop", "fade_in", "fade_out",
           "duck_db", "duck_attack", "duck_release"}


def decode(path: Path, sr: int) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("music: FFmpeg must be on PATH to read the file")
    result = subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0", "-ac", "2", "-ar", str(sr),
                             "-f", "f32le", "-"], capture_output=True, check=False)
    if result.returncode or not result.stdout:
        raise ValueError(f"music: cannot decode {path}: {result.stderr.decode('utf-8', 'replace')[-300:]}")
    return np.frombuffer(result.stdout, np.float32).reshape(-1, 2).astype(np.float64)


def _num(params: dict, key: str, default: float) -> float:
    value = params.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"music: {key} must be a finite number, got {value!r}")
    return float(value)


def bed_from_file(params: dict, duration: float, sr: int, hits: list[dict], base: Path | None) -> tuple[np.ndarray, dict]:
    unknown = set(params) - ALLOWED - {"voice"}
    if unknown:
        raise ValueError(f"music: unknown parameter(s) {sorted(unknown)}; allowed: {sorted(ALLOWED)}")
    if not isinstance(params.get("file"), str) or not params["file"].strip():
        raise ValueError("music: needs a file (a WAV, MP3, M4A… on this machine)")
    path = Path(params["file"])
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    if not path.is_file():
        raise ValueError(f"music: file not found: {path}")
    gain_db, enter = _num(params, "gain_db", -6), _num(params, "time", 0)
    if not 0 <= enter < duration:
        raise ValueError(f"music: time {enter} is outside the piece (0 to {duration} s)")
    start = _num(params, "start", 0)
    if "start_bar" in params:
        bpm = _num(params, "bpm", 0)
        if not bpm > 0:
            raise ValueError("music: start_bar needs bpm (the track's tempo)")
        start = _num(params, "start_bar", 0) * _num(params, "beats_per_bar", 4) * 60 / bpm
    if start < 0:
        raise ValueError("music: start must not be negative")
    fade_in, fade_out = max(0.0, _num(params, "fade_in", .4)), max(0.0, _num(params, "fade_out", 1.2))
    duck_db = _num(params, "duck_db", -8)
    attack, release = max(1e-3, _num(params, "duck_attack", .012)), max(1e-3, _num(params, "duck_release", .35))
    loop = params.get("loop", True)
    if not isinstance(loop, bool):
        raise ValueError("music: loop must be true or false")

    audio = decode(path, sr)
    first = int(round(start * sr))
    if first >= len(audio):
        raise ValueError(f"music: start {start:.3f} s is past the end of the file ({len(audio) / sr:.3f} s)")
    need = int(round(duration * sr)) - int(round(enter * sr))
    body = audio[first:]
    if loop and len(body) < need:
        body = np.concatenate([body] + [audio] * math.ceil((need - len(body)) / len(audio)))
    body = body[:need]
    out = np.zeros((int(round(duration * sr)), 2))
    at = int(round(enter * sr))
    out[at:at + len(body)] = body

    t = np.arange(len(out)) / sr
    env = np.ones(len(out))
    if fade_in > 0:
        env *= np.clip((t - enter) / fade_in, 0, 1) ** 2
    if fade_out > 0:
        env *= np.sin(np.pi / 2 * np.clip((duration - t) / fade_out, 0, 1)) ** 2
    if duck_db < 0:   # dips on every hit: fast attack, slow release, so the impact reads first
        depth = 1 - 10 ** (duck_db / 20)
        dip = np.zeros(len(out))
        for hit in hits:
            k = float(hit["time"])
            rise = np.clip((t - (k - attack)) / attack, 0, 1)
            fall = np.exp(-np.clip(t - k, 0, None) / release)
            dip = np.maximum(dip, np.where(t < k, rise, fall) * min(1.0, float(hit.get("amplitude", 1))))
        env *= 1 - depth * dip
    out *= env[:, None] * 10 ** (gain_db / 20)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return out, {"file": str(path), "sha256_16": digest, "gain_db": gain_db, "time": enter, "start_s": round(start, 4),
                 "loop": loop, "fade_in": fade_in, "fade_out": fade_out, "duck_db": duck_db, "file_seconds": round(len(audio) / sr, 3)}
