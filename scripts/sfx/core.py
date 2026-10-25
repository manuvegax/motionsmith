"""Shared primitives for deterministic sound design: a seeded score buffer, envelopes, noise and swept filters.

Synthesis only (NumPy); no samples, no music. One generator per Score drives every voice, so the same plan, cues and
seed give the same samples. Times are seconds; buffers are float64 arrays of shape (samples, 2) at `sr` Hz.
"""
from __future__ import annotations

import math

import numpy as np

SR = 48000


class Score:
    """A stereo buffer of `duration` seconds, a send bus for the room, and the generator every voice draws from."""

    def __init__(self, duration: float, seed: int, sr: int = SR):
        if not duration > 0:
            raise ValueError("duration must be positive")
        self.sr = sr
        self.duration = float(duration)
        self.samples = round(self.duration * sr)
        self.rng = np.random.default_rng(seed)
        self.dry = np.zeros((self.samples, 2))
        self.send = np.zeros_like(self.dry)

    def place(self, at, signal, gain=1.0, pan=0.0, reverb=0.0):
        """Add a mono or stereo signal starting at `at` seconds. pan: -1 (left) to 1 (right), a scalar or a per-sample array."""
        start = round(at * self.sr)
        signal = np.asarray(signal, dtype=np.float64)
        if start < 0:
            signal = signal[-start:]
            start = 0
        count = min(len(signal), self.samples - start)
        if count <= 0:
            return
        signal = signal[:count]
        if signal.ndim == 1:
            if np.ndim(pan) == 0:
                position = np.full(count, float(pan))
            else:
                position = np.asarray(pan, dtype=np.float64)[:count]
            position = np.clip(position, -1, 1)
            angle = (position + 1) * np.pi / 4
            stereo = np.column_stack((np.cos(angle), np.sin(angle))) * signal[:, None]
        else:
            stereo = signal[:count]
        self.dry[start:start + count] += stereo * gain
        if reverb:
            self.send[start:start + count] += stereo * gain * reverb


def timeline(duration: float, sr: int = SR) -> np.ndarray:
    """Seconds from 0 for `duration` seconds of samples."""
    return np.arange(round(duration * sr), dtype=np.float64) / sr


def smoothstep(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def edge_fade(signal, attack: float = .003, release: float = .018, sr: int = SR):
    """Raised-cosine edges: the first and last samples are exactly zero, so a voice never clicks at its boundaries."""
    result = np.array(signal, dtype=np.float64, copy=True)
    for length, reverse in ((min(len(result), round(attack * sr)), False),
                            (min(len(result), round(release * sr)), True)):
        if length > 1:
            ramp = np.sin(np.linspace(0, np.pi / 2, length)) ** 2
            if result.ndim == 2:
                ramp = ramp[:, None]
            if reverse:
                result[-length:] *= ramp[::-1]
            else:
                result[:length] *= ramp
    return result


def rms_normal(x):
    """Scale to unit RMS so that noise layers can be mixed by their gains alone."""
    return x / max(1e-12, math.sqrt(float(np.mean(x * x))))


def noise(score: Score, duration: float, low: float = 20.0, high: float = 20000.0) -> np.ndarray:
    """Band-limited white noise from the score's generator, unit RMS."""
    count = round(duration * score.sr)
    spectrum = np.fft.rfft(score.rng.standard_normal(count))
    frequencies = np.maximum(np.fft.rfftfreq(count, 1 / score.sr), 1e-6)
    shape = 1 / np.sqrt(1 + (low / frequencies) ** 6) / np.sqrt(1 + (frequencies / high) ** 8)
    shape[0] = 0
    return rms_normal(np.fft.irfft(spectrum * shape, n=count))


def swept(signal, centre_of_time, sr: int = SR, octaves: float = 1.2, frame: int = 2048, hop: int = 512):
    """A time-varying band-pass: overlap-added STFT frames whose centre frequency is centre_of_time(seconds) in Hz."""
    window = np.hanning(frame)
    padded = np.concatenate([np.zeros(frame // 2), signal, np.zeros(frame)])
    out = np.zeros(len(padded))
    weight = np.zeros(len(padded))
    log_f = np.log2(np.maximum(np.fft.rfftfreq(frame, 1 / sr), 1.0))
    for start in range(0, len(signal) + frame // 2, hop):
        segment = padded[start:start + frame]
        if len(segment) < frame:
            break
        centre = math.log2(max(20.0, centre_of_time(start / sr)))
        gain = np.exp(-.5 * ((log_f - centre) / (octaves / 2)) ** 2)
        out[start:start + frame] += np.fft.irfft(np.fft.rfft(segment * window) * gain, n=frame) * window
        weight[start:start + frame] += window ** 2
    return (out / np.maximum(weight, 1e-6))[frame // 2:frame // 2 + len(signal)]


def saturate(x, drive: float):
    """Soft clipping that keeps full scale at 1 for small signals and adds harmonics as the drive rises."""
    return np.tanh(x * drive) / np.tanh(drive)
