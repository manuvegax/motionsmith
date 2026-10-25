"""Master bus: stereo room, duck envelopes, high-pass, FFmpeg loudness measurement and the search for a LUFS target.

FFmpeg measures (loudnorm for the search, ebur128 for the final file); it never processes the delivered audio. The
mastering only applies a soft saturation drive and a gain, chosen by measurement, so that the integrated loudness
lands on the target while the true peak stays under the ceiling.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import wave
from pathlib import Path

import numpy as np

from .core import SR, Score, noise, saturate, smoothstep

TOLERANCE_LU = .15   # how close the search must land before it stops (the final check allows a full LU)


def room(score: Score, seconds: float = 2.3, decay: float = .48, wet: float = .55):
    """Convolve the send bus with a finite noise impulse response (darker tail, 18 ms pre-delay) and return the wet
    signal scaled by `wet`. The impulse response draws from the score's generator, so call it after the voices."""
    sr = score.sr
    length = round(seconds * sr)
    x = np.arange(length) / sr
    ir = np.column_stack([noise(score, seconds, 120, 9000), noise(score, seconds, 120, 9000)]) * np.exp(-x / decay)[:, None]
    ir[:round(.018 * sr)] = 0
    ir /= np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))
    size = 1 << int(math.ceil(math.log2(score.samples + length)))
    wet_signal = np.column_stack([np.fft.irfft(np.fft.rfft(score.send[:, c], size) * np.fft.rfft(ir[:, c], size), size)[:score.samples]
                                  for c in (0, 1)])
    return wet_signal * wet


def duck_envelope(samples: int, sr: int, events) -> np.ndarray:
    """Gain curve that dips for each event. An event is {at, fall, hold, rise, depth}: it falls over `fall` seconds
    from `at`, holds for `hold` seconds, and rises back over `rise` seconds. depth 0.94 leaves about -24 dB."""
    t = np.arange(samples) / sr
    gain = np.ones(samples)
    for event in events:
        start, fall, hold, rise, depth = (float(event[k]) for k in ("at", "fall", "hold", "rise", "depth"))
        down = smoothstep((t - start) / max(fall, 1e-9))
        up = 1 - smoothstep((t - (start + fall + hold)) / max(rise, 1e-9))
        gain *= 1 - depth * down * up
    return gain


def high_pass(signal: np.ndarray, sr: int, hz: float = 35.0) -> np.ndarray:
    """An eighth-order magnitude high-pass in the frequency domain. Deep sub-bass only eats headroom on phones."""
    if hz <= 0:
        return signal
    count = len(signal)
    spectrum = np.fft.rfft(signal, axis=0)
    frequencies = np.maximum(np.fft.rfftfreq(count, 1 / sr), 1e-6)
    spectrum *= (1 / np.sqrt(1 + (hz / frequencies) ** 8))[:, None]
    return np.fft.irfft(spectrum, n=count, axis=0)


def ffmpeg_measure(ffmpeg: str, samples=None, path=None, target_lufs: float = -16.0, target_tp: float = -1.5,
                   sr: int = SR) -> dict:
    """Integrated loudness, true peak and loudness range from FFmpeg's loudnorm analysis (input measurement).
    Pass float32 interleaved stereo samples (piped) or a file path."""
    args = [ffmpeg, "-hide_banner", "-nostats", "-v", "info"]
    if samples is not None:
        args += ["-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "pipe:0"]
        data = np.asarray(samples, dtype="<f4").tobytes()
    else:
        args += ["-i", str(path)]
        data = None
    args += ["-af", f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:print_format=json", "-f", "null", "-"]
    result = subprocess.run(args, input=data, capture_output=True, check=False)
    stderr = result.stderr.decode("utf-8", "replace")
    if result.returncode:
        raise RuntimeError("FFmpeg measurement failed: " + stderr[-3000:])
    matches = re.findall(r'\{\s*"input_i".*?\}', stderr, re.S)
    if not matches:
        raise RuntimeError("FFmpeg did not return EBU R128 measurements")
    raw = json.loads(matches[-1])
    values = {"integrated_lufs": float(raw["input_i"]), "true_peak_dbtp": float(raw["input_tp"]),
              "lra_lu": float(raw["input_lra"]), "threshold_lufs": float(raw["input_thresh"])}
    if not all(math.isfinite(v) for v in values.values()):
        raise RuntimeError("non-finite loudness result")
    return values


def independent_ebur128(ffmpeg: str, path) -> dict:
    """A second opinion on the written file: FFmpeg's ebur128 filter with true peak, over a full decode."""
    result = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-v", "info", "-xerror", "-i", str(path),
                             "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, check=False)
    stderr = result.stderr.decode("utf-8", "replace")
    if result.returncode:
        raise RuntimeError("independent EBU R128 failed: " + stderr[-2000:])
    summary = stderr[stderr.rfind("Summary:"):]
    integrated = re.search(r"Integrated loudness:\s*I:\s*([-0-9.]+) LUFS", summary)
    peak = re.search(r"True peak:\s*Peak:\s*([-0-9.]+) dBFS", summary)
    if not integrated or not peak:
        raise RuntimeError("cannot parse the ebur128 summary")
    return {"integrated_lufs": float(integrated[1]), "true_peak_dbtp": float(peak[1]), "method": "ffmpeg ebur128=peak=true"}


def master_to_target(samples: np.ndarray, ffmpeg: str, target_lufs: float = -16.0, target_tp: float = -1.5,
                     sr: int = SR):
    """Find the saturation drive whose output, gained so that its true peak sits just under the ceiling, has the
    integrated loudness closest to the target. Returns (samples, report). The search is bounded: a poor fit is
    reported, never hidden, and the caller decides whether it is acceptable."""
    ceiling = target_tp - .05
    normalized = samples / max(1e-12, float(np.max(np.abs(samples))))
    attempts = []
    best = None

    def trial(drive):
        candidate = saturate(normalized, drive)
        info = ffmpeg_measure(ffmpeg, candidate * .7, target_lufs=target_lufs, target_tp=target_tp, sr=sr)
        gain_db = ceiling - info["true_peak_dbtp"]
        predicted = info["integrated_lufs"] + gain_db
        attempts.append({"drive": round(drive, 4), "integrated_after_peak_alignment_lufs": round(predicted, 3)})
        return candidate * .7 * 10 ** (gain_db / 20), predicted, gain_db

    low, high = .2, 12.0
    for drive in (1.0, 3.0, .5, 6.0, 2.0, 4.5, 9.0):
        candidate, predicted, gain_db = trial(drive)
        if best is None or abs(predicted - target_lufs) < abs(best[2] - target_lufs):
            best = (candidate, drive, predicted, gain_db)
        if abs(predicted - target_lufs) <= TOLERANCE_LU:
            break
        if predicted < target_lufs:
            low = max(low, drive)
        else:
            high = min(high, drive)
    if abs(best[2] - target_lufs) > TOLERANCE_LU and low < high:
        for _ in range(7):
            drive = (low + high) / 2
            candidate, predicted, gain_db = trial(drive)
            if abs(predicted - target_lufs) < abs(best[2] - target_lufs):
                best = (candidate, drive, predicted, gain_db)
            if predicted < target_lufs:
                low = drive
            else:
                high = drive
            if abs(predicted - target_lufs) <= TOLERANCE_LU:
                break
    report = {"target_integrated_lufs": target_lufs, "target_true_peak_dbtp": target_tp, "ceiling_dbtp": ceiling,
              "soft_saturation_drive": round(best[1], 4), "predicted_integrated_lufs": round(best[2], 3),
              "measurement_attempts": attempts}
    return best[0], report


def write_wav(path, samples: np.ndarray, sr: int = SR) -> bytes:
    """16-bit PCM stereo. Returns the bytes written, so that callers can hash them. No timestamps are stored."""
    if not np.isfinite(samples).all() or np.max(np.abs(samples)) >= 1:
        raise ValueError("samples must be finite and below full scale")
    pcm = np.round(samples * 32767).astype("<i2")
    data = pcm.tobytes()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sr)
        handle.writeframes(data)
    return path.read_bytes()
