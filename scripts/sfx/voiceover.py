"""A recorded voice over the score: placed on its time, kept dry and on top, and everything else ducked while it speaks.

Cue (in cues.json; the path is relative to the cues file):
  {"voice": "voiceover", "file": "assets/voice.wav", "time": 0.0, "gain_db": 0, "duck_db": -15,
   "duck_attack": 0.04, "duck_release": 0.35, "highpass_hz": 70}
time = when the voice starts in the piece (s). duck_db = how far the music, the bed and the effects dip under speech
(0 switches it off). The duck follows the voice's own envelope (a sidechain), so pauses breathe and words stay clear.
The report gives voice_over_bed_db: how far the voice sits above the rest while it speaks (aim for 10 dB or more).
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np

from .music import decode

ALLOWED = {"file", "time", "gain_db", "duck_db", "duck_attack", "duck_release", "highpass_hz"}


def _num(params: dict, key: str, default: float) -> float:
    value = params.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"voiceover: {key} must be a finite number, got {value!r}")
    return float(value)


def _highpass(mono: np.ndarray, sr: int, hz: float) -> np.ndarray:
    if hz <= 0:
        return mono
    spectrum = np.fft.rfft(mono)
    f = np.maximum(np.fft.rfftfreq(len(mono), 1 / sr), 1e-6)
    return np.fft.irfft(spectrum / np.sqrt(1 + (hz / f) ** 8), n=len(mono))


def envelope(mono: np.ndarray, sr: int, attack: float, release: float, window: float = .01) -> np.ndarray:
    """Per-sample speech envelope in 0..1: windowed RMS, gated 35 dB under the voice's loud level, smoothed with a
    fast attack and a slower release."""
    hop = max(1, int(sr * window))
    frames = len(mono) // hop + 1
    padded = np.zeros(frames * hop)
    padded[:len(mono)] = mono
    rms = np.sqrt(np.mean(padded.reshape(frames, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    loud = np.percentile(db, 95) if len(db) else -90
    level = np.clip((db - (loud - 35)) / 25, 0, 1)
    a, r = math.exp(-window / max(attack, 1e-3)), math.exp(-window / max(release, 1e-3))
    smooth = np.empty_like(level)
    state = 0.0
    for i, value in enumerate(level):
        coeff = a if value > state else r
        state = coeff * state + (1 - coeff) * value
        smooth[i] = state
    return np.repeat(smooth, hop)[:len(mono)]


def voice_layer(params: dict, duration: float, sr: int, base: Path | None) -> tuple[np.ndarray, np.ndarray, dict]:
    """Returns (stereo voice, 0..1 speech envelope, info), both as long as the piece."""
    unknown = set(params) - ALLOWED - {"voice"}
    if unknown:
        raise ValueError(f"voiceover: unknown parameter(s) {sorted(unknown)}; allowed: {sorted(ALLOWED)}")
    if not isinstance(params.get("file"), str) or not params["file"].strip():
        raise ValueError("voiceover: needs a file (the recorded or synthesized voice)")
    path = Path(params["file"])
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    if not path.is_file():
        raise ValueError(f"voiceover: file not found: {path}")
    at = _num(params, "time", 0)
    if not 0 <= at < duration:
        raise ValueError(f"voiceover: time {at} is outside the piece (0 to {duration} s)")
    gain_db = _num(params, "gain_db", 0)
    attack, release = _num(params, "duck_attack", .04), _num(params, "duck_release", .35)
    audio = decode(path, sr)
    mono = _highpass(audio.mean(axis=1), sr, _num(params, "highpass_hz", 70))
    total = int(round(duration * sr))
    start = int(round(at * sr))
    body = mono[: max(0, total - start)]
    voice = np.zeros(total)
    voice[start:start + len(body)] = body * 10 ** (gain_db / 20)
    env = envelope(voice, sr, attack, release)
    info = {"file": str(path), "sha256_16": hashlib.sha256(path.read_bytes()).hexdigest()[:16], "time": at,
            "gain_db": gain_db, "duck_db": _num(params, "duck_db", -15), "file_seconds": round(len(mono) / sr, 3),
            "cut_at_end": len(mono) > len(body)}
    return np.column_stack([voice, voice]), env, info


def duck_under(master: np.ndarray, env: np.ndarray, duck_db: float) -> np.ndarray:
    if duck_db >= 0:
        return master
    depth = 1 - 10 ** (duck_db / 20)
    return master * (1 - depth * env[: len(master)])[:, None]


def voice_over_bed(voice: np.ndarray, rest: np.ndarray, env: np.ndarray) -> float | None:
    """dB between the voice and everything else, measured only where the voice speaks."""
    speaking = env[: len(voice)] > .5
    if speaking.sum() < 100:
        return None
    v = np.sqrt(np.mean(voice[speaking] ** 2) + 1e-12)
    r = np.sqrt(np.mean(rest[speaking] ** 2) + 1e-12)
    return round(float(20 * np.log10(v / r)), 1)
