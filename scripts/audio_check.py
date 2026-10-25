"""Measure a soundtrack or a muxed video: loudness, band balance, section levels, onsets vs events.

Measurement only. It does not listen, judge a mix or certify that sound and image feel in sync.
Typical use, on the WAV and again on the final MP4 (AAC changes peaks and loudness):

  python scripts/audio_check.py piece/assets/soundtrack.wav --plan piece/plan.json \
      --segment vacio=8.02:8.22 --spectrogram piece/preview/espectrograma.png --report piece/preview/audio-check.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np

SR = 48000
BANDS = ((20, 60), (60, 120), (120, 300), (300, 2000), (2000, 8000), (8000, 20000))
# ITU-R BT.1359-1: sound is detectably out of sync when it leads the image by 45 ms or lags it by 125 ms.
EARLY_S, LATE_S = 0.045, 0.125


def utf8_console() -> None:
    """Windows consoles default to cp1252 under python -I: print accents and symbols without crashing."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def decode(source: Path, ffmpeg: str) -> np.ndarray:
    """Decode the first audio stream to float32 stereo at 48 kHz."""
    result = subprocess.run([ffmpeg, "-v", "error", "-i", str(source), "-map", "0:a:0", "-ac", "2", "-ar", str(SR),
                             "-f", "f32le", "-"], capture_output=True, check=False)
    if result.returncode or not result.stdout:
        raise RuntimeError("cannot decode audio: " + result.stderr.decode("utf-8", "replace")[-1500:])
    return np.frombuffer(result.stdout, dtype="<f4").reshape(-1, 2).astype(np.float64)


def ebur128(source: Path, ffmpeg: str) -> dict:
    result = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(source), "-map", "0:a:0",
                             "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, check=False)
    text = result.stderr.decode("utf-8", "replace")
    summary = text[text.rfind("Summary:"):]
    found = {key: re.search(pattern, summary) for key, pattern in (
        ("integrated_lufs", r"I:\s*([-0-9.]+) LUFS"), ("lra_lu", r"LRA:\s*([-0-9.]+) LU"),
        ("true_peak_dbtp", r"Peak:\s*([-0-9.]+) dBFS"))}
    if result.returncode or not all(found.values()):
        raise RuntimeError("ebur128 measurement failed: " + text[-1500:])
    return {key: float(match[1]) for key, match in found.items()} | {"precision_db": 0.1, "method": "ffmpeg ebur128=peak=true"}


def db(x: float) -> float:
    return round(20 * math.log10(max(x, 1e-12)), 2)


def band_balance(mono: np.ndarray) -> dict:
    power = np.abs(np.fft.rfft(mono)) ** 2
    freqs = np.fft.rfftfreq(len(mono), 1 / SR)
    total = power[(freqs >= 20) & (freqs < 20000)].sum() or 1.0
    return {f"{lo}-{hi}_hz_pct": round(100 * power[(freqs >= lo) & (freqs < hi)].sum() / total, 1) for lo, hi in BANDS}


def segment_levels(mono: np.ndarray, segments: list[tuple[str, float, float]]) -> list[dict]:
    rows = []
    for name, a, b in segments:
        part = mono[int(a * SR):int(b * SR)]
        rows.append({"name": name, "start_s": a, "end_s": b,
                     "rms_dbfs": db(float(np.sqrt(np.mean(part ** 2)))) if len(part) else None,
                     "peak_dbfs": db(float(np.max(np.abs(part)))) if len(part) else None})
    return rows


def onsets(mono: np.ndarray, count: int, min_gap: float = 0.12, min_strength: float = 0.15) -> list[float]:
    """Spectral-flux attack candidates (60 Hz-12 kHz), strongest first, then sorted in time. Only frames whose flux
    reaches `min_strength` x the strongest one count: silence or a steady bed never becomes a hit.
    Times run ~10 ms early on average (measured bias -9 ms; noise bursts 7-17 ms)."""
    hop, win = SR // 100, 2048
    if len(mono) < win + hop:
        return []
    frames = np.lib.stride_tricks.sliding_window_view(mono, win)[::hop] * np.hanning(win)
    spectrum = np.abs(np.fft.rfft(frames, axis=1))
    freqs = np.fft.rfftfreq(win, 1 / SR)
    band = np.log1p(spectrum[:, (freqs >= 60) & (freqs < 12000)] * 50)
    flux = np.maximum(0, np.diff(band, axis=0)).sum(axis=1)
    times = (np.arange(len(flux)) + 1) * hop / SR + win / 2 / SR
    floor = max(min_strength * float(flux.max(initial=0.0)), 1e-6)
    picked: list[float] = []
    for index in np.argsort(flux)[::-1]:
        if flux[index] < floor:
            break
        t = float(times[index])
        if all(abs(t - other) > min_gap for other in picked):
            picked.append(t)
        if len(picked) >= count:
            break
    return sorted(round(t, 3) for t in picked)


def match_events(found: list[float], events: list[dict], early: float, late: float) -> dict:
    """Pair events and onsets inside [time - early, time + late] (sound may lag more than lead). Pairs are taken
    closest first over the whole list, so an earlier event cannot steal the onset that sits on a later one."""
    pairs = sorted((abs(t - event["time"]), e, i) for e, event in enumerate(events) for i, t in enumerate(found)
                   if -early <= t - event["time"] <= late)
    chosen, used = {}, set()
    for _, e, i in pairs:
        if e not in chosen and i not in used:
            chosen[e] = i
            used.add(i)
    rows = []
    for e, event in enumerate(events):
        if e in chosen:
            onset = found[chosen[e]]
            rows.append({**event, "onset_s": onset, "offset_ms": round((onset - event["time"]) * 1000)})
        else:
            rows.append({**event, "onset_s": None, "offset_ms": None})
    return {"tolerance_s": {"early": early, "late": late, "source": "ITU-R BT.1359-1 detectability"}, "events": rows,
            "unmatched_events": [r for r in rows if r["onset_s"] is None],
            "onsets_without_event": [t for i, t in enumerate(found) if i not in used]}


def plan_events(path: Path) -> list[dict]:
    plan = json.loads(path.read_text(encoding="utf-8-sig"))
    events = []
    for hit in plan.get("hits") or []:
        # {time, amplitude, role} as plan.json asks, or [time, amplitude] as MotionMath.impulse also accepts.
        try:
            if isinstance(hit, dict):
                time, role = float(hit["time"]), hit.get("role", "hit")
            elif isinstance(hit, (list, tuple)):
                time, role = float(hit[0]), "hit"
            else:
                time, role = float(hit), "hit"
        except (TypeError, ValueError, KeyError, IndexError):
            raise ValueError(f"plan.json hits: no time in {hit!r}; use {{time, amplitude, role}} or [time, amplitude]")
        events.append({"time": time, "role": role, "source": "hits"})
    known = {round(e["time"], 3) for e in events}
    for cue in plan.get("sound_cues", []):
        if isinstance(cue, dict) and isinstance(cue.get("time"), (int, float)) and round(cue["time"], 3) not in known:
            events.append({"time": float(cue["time"]), "role": cue.get("role", "cue"), "source": "sound_cues"})
    return sorted(events, key=lambda e: e["time"])


def spectrogram(mono: np.ndarray, out: Path, events: list[dict]) -> None:
    from PIL import Image, ImageDraw
    hop, win, width, height = 240, 4096, 1500, 520
    frames = np.lib.stride_tricks.sliding_window_view(mono, win)[::hop] * np.hanning(win)
    spec = 20 * np.log10(np.abs(np.fft.rfft(frames, axis=1)) + 1e-9)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    rows = np.geomspace(25, 16000, height)
    image = spec[:, np.searchsorted(freqs, rows).clip(0, len(freqs) - 1)].T[::-1]
    image = np.clip((image - (image.max() - 80)) / 80, 0, 1)[:, np.linspace(0, image.shape[1] - 1, width).astype(int)]
    rgb = np.stack([image ** .7 * 255, image ** 1.6 * 200, image ** 3 * 255], -1).astype(np.uint8)
    picture = Image.fromarray(rgb)
    draw = ImageDraw.Draw(picture)
    duration = len(mono) / SR
    for hz in (50, 100, 300, 1000, 3000, 10000):
        y = height - 1 - int(np.searchsorted(rows, hz))
        draw.line([(0, y), (18, y)], fill=(120, 120, 120))
        draw.text((20, y - 6), f"{hz} Hz", fill=(150, 150, 150))
    for event in events:
        x = int(event["time"] / duration * width)
        draw.line([(x, 0), (x, height)], fill=(80, 200, 255))
        draw.text((x + 3, 4), str(event.get("role", ""))[:14], fill=(80, 200, 255))
    strip = Image.new("RGB", (width, 120), (15, 15, 18))
    sd = ImageDraw.Draw(strip)
    step = SR // 20
    levels = [20 * math.log10(max(float(np.sqrt(np.mean(mono[i:i + step] ** 2))), 1e-9)) for i in range(0, len(mono) - step, step)]
    if len(levels) > 1:
        sd.line([(int(i / len(levels) * width), int(110 - (max(v, -60) + 60) / 60 * 100)) for i, v in enumerate(levels)],
                fill=(255, 120, 90), width=2)
    sd.text((4, 4), "RMS cada 50 ms (-60..0 dBFS)", fill=(200, 200, 200))
    sheet = Image.new("RGB", (width, height + 120))
    sheet.paste(picture, (0, 0))
    sheet.paste(strip, (0, height))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def parse_segment(text: str) -> tuple[str, float, float]:
    try:
        name, span = text.split("=", 1)
        a, b = (float(v) for v in span.split(":"))
    except ValueError:
        raise argparse.ArgumentTypeError("use name=start:end in seconds")
    if not name or b <= a or a < 0:
        raise argparse.ArgumentTypeError("segment needs a name and 0 <= start < end")
    return name, a, b


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="WAV, MP4 or any file with an audio stream")
    parser.add_argument("--plan", type=Path, help="plan.json: its hits and sound_cues become the events to match")
    parser.add_argument("--events", help="extra event times in seconds, comma separated")
    parser.add_argument("--early", type=float, default=EARLY_S, help="max seconds a sound may lead its event (BT.1359: 0.045)")
    parser.add_argument("--late", type=float, default=LATE_S, help="max seconds a sound may lag its event (BT.1359: 0.125)")
    parser.add_argument("--tolerance", type=float, help="symmetric window in seconds, overrides --early and --late")
    parser.add_argument("--onsets", type=int, default=24, help="how many attack candidates to keep")
    parser.add_argument("--segment", type=parse_segment, action="append", default=[], help="name=start:end (repeatable)")
    parser.add_argument("--target-lufs", type=float, default=-16.0)
    parser.add_argument("--lufs-tolerance", type=float, default=1.0)
    parser.add_argument("--max-true-peak", type=float, default=-1.0, help="ceiling in dBTP for the measured file")
    parser.add_argument("--max-sub-pct", type=float, default=50.0,
                        help="warn when this share of energy is below 60 Hz (phones do not reproduce it)")
    parser.add_argument("--max-low-pct", type=float, default=75.0,
                        help="note when this share is below 120 Hz: a phone speaker plays little of the mix")
    parser.add_argument("--min-correlation", type=float, default=0.3, help="warn below this L/R correlation")
    parser.add_argument("--max-mono-loss", type=float, default=4.5,
                        help="warn when folding to mono loses more dB (uncorrelated stereo already loses 3 dB; 4.5 means real cancellation)")
    parser.add_argument("--onset-strength", type=float, default=0.15,
                        help="share of the strongest attack an onset needs to count (silence never matches an event)")
    parser.add_argument("--spectrogram", type=Path, help="write a PNG with event markers and an RMS strip")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    args = parser.parse_args()
    utf8_console()
    early, late = (args.tolerance, args.tolerance) if args.tolerance is not None else (args.early, args.late)

    ffmpeg = shutil.which("ffmpeg")
    report: dict = {"source": str(args.source.resolve()), "errors": [], "warnings": [], "notes": [],
                    "listening": "not_performed_by_this_script"}
    if not ffmpeg:
        report["errors"].append("ffmpeg must be on PATH")
    elif not args.source.is_file():
        report["errors"].append("source file is missing")
    if args.spectrogram and args.report and args.spectrogram.resolve() == args.report.resolve():
        report["errors"].append("spectrogram and report must be different files")
    if not report["errors"]:
        try:
            stereo = decode(args.source, ffmpeg)
            mono = stereo.mean(axis=1)
            events = plan_events(args.plan) if args.plan else []
            if args.events:
                known = {round(e["time"], 3) for e in events}
                events += [{"time": float(v), "role": f"event {float(v):g}s", "source": "--events"}
                           for v in args.events.split(",") if v.strip() and round(float(v), 3) not in known]
            events.sort(key=lambda e: e["time"])
            loud = ebur128(args.source, ffmpeg)
            bands = band_balance(mono)
            corr = float(np.corrcoef(stereo.T)[0, 1]) if stereo[:, 0].std() > 0 and stereo[:, 1].std() > 0 else None
            # Many phones play one speaker or sum to mono: (L+R)/2 against the mean channel level.
            side_rms = float(np.mean([np.sqrt(np.mean(stereo[:, c] ** 2)) for c in (0, 1)]))
            mono_loss = round(db(side_rms) - db(float(np.sqrt(np.mean(mono ** 2)))), 2) if side_rms > 1e-9 else 0.0
            report.update({"duration_s": round(len(mono) / SR, 3), "loudness": loud, "band_balance": bands,
                           "stereo_correlation": None if corr is None else round(corr, 3), "mono_fold_loss_db": mono_loss,
                           "first_sample_abs": round(float(np.abs(stereo[0]).max()), 6),
                           "last_sample_abs": round(float(np.abs(stereo[-1]).max()), 6),
                           "segments": segment_levels(mono, args.segment)})
            found = onsets(mono, args.onsets, min_strength=args.onset_strength)
            report["onsets_s"] = found
            if events:
                report["sync"] = match_events(found, events, early, late)
                for row in report["sync"]["unmatched_events"]:
                    report["warnings"].append(f"no attack from {early}s before to {late}s after {row['role']} at {row['time']}s")
                for row in report["sync"]["events"]:
                    if row["offset_ms"] is not None and row["offset_ms"] > 60:
                        report["notes"].append(f"{row['role']} at {row['time']}s: sound {row['offset_ms']} ms after the image;"
                                               " accepted, but impacts land better on the same frame")
            if abs(loud["integrated_lufs"] - args.target_lufs) > args.lufs_tolerance:
                report["warnings"].append(f"integrated {loud['integrated_lufs']} LUFS, target {args.target_lufs}±{args.lufs_tolerance}")
            if loud["true_peak_dbtp"] > args.max_true_peak:
                report["warnings"].append(f"true peak {loud['true_peak_dbtp']} dBTP above {args.max_true_peak}")
            if bands["20-60_hz_pct"] > args.max_sub_pct:
                report["warnings"].append(f"{bands['20-60_hz_pct']}% of energy below 60 Hz: a phone speaker will lose most of it;"
                                          " add 60-300 Hz harmonics (saturation, octave layers) and high-pass ~35 Hz")
            low_pct = round(bands["20-60_hz_pct"] + bands["60-120_hz_pct"], 1)
            if low_pct > args.max_low_pct:
                report["notes"].append(f"{low_pct}% of energy below 120 Hz: on a phone speaker most of the mix disappears;"
                                       " check that clicks, risers and voice carry the piece on their own")
            if corr is not None and corr < args.min_correlation:
                report["warnings"].append(f"L/R correlation {corr:.2f}: wide or out-of-phase stereo can sound hollow when a phone sums to mono")
            if mono_loss > args.max_mono_loss:
                report["warnings"].append(f"folding to mono loses {mono_loss} dB: some layers cancel between channels")
            if report["first_sample_abs"] > 0.01 or report["last_sample_abs"] > 0.01:
                report["warnings"].append("audio does not start/end near silence: check for clicks at the edges")
            if args.spectrogram:
                spectrogram(mono, args.spectrogram, events)
                report["spectrogram"] = str(args.spectrogram.resolve())
        except (RuntimeError, ValueError, KeyError, OSError) as error:
            report["errors"].append(str(error))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return int(bool(report["errors"]) or (args.strict and bool(report["warnings"])))


if __name__ == "__main__":
    sys.exit(main())
