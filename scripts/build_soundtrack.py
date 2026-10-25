"""Build a soundtrack whose impacts sit on a piece's hits: NumPy synthesis (plus an optional recorded music bed, see sfx/music.py), FFmpeg-measured loudness.

  python scripts/build_soundtrack.py --plan plan.json [--cues cues.json] --out assets/soundtrack.wav [--seed 1]
      [--lufs -16] [--tp -1.5] [--tolerance-lu 1.0] [--report preview/soundtrack-report.json] [--replace]

plan.json and cues.json are described in sfx/schedule.py. The WAV is 16-bit stereo at 48 kHz and identical for the same
plan, cues and seed. It is written only when its integrated loudness lands within the tolerance of the target and its
true peak stays under the ceiling. The report also checks every hit against the audio with scripts/audio_check.py:
the attack must fall from 45 ms before to 125 ms after the hit (ITU-R BT.1359). Unmatched hits are warnings.
Refuses to overwrite an existing output or report unless --replace is given.
Exit codes: 0 built, 1 the mix missed the loudness or peak target, 2 usage or input error.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))  # works under python -I too
from audio_check import EARLY_S, LATE_S, onsets, match_events, utf8_console  # noqa: E402
from sfx import SR, ffmpeg_measure, independent_ebur128, master_to_target, normalize_hits, render, write_wav  # noqa: E402

DEFAULT_SEED = 1


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {path}: {error}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def read_wav_mono(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as handle:
        frames = handle.readframes(handle.getnframes())
        channels = handle.getnchannels()
    stereo = np.frombuffer(frames, dtype="<i2").reshape(-1, channels).astype(np.float64) / 32768
    return stereo.mean(axis=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan", type=Path, required=True, help="plan.json: duration and hits")
    parser.add_argument("--cues", type=Path, help="cues.json: voices placed on times, layers and room (optional)")
    parser.add_argument("--out", type=Path, required=True, help="WAV to write, e.g. assets/soundtrack.wav")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="same seed, same samples (default 1)")
    parser.add_argument("--lufs", type=float, default=-16.0, help="integrated loudness target in LUFS")
    parser.add_argument("--tp", type=float, default=-1.5, help="true peak ceiling in dBTP")
    parser.add_argument("--tolerance-lu", type=float, default=1.0, help="accepted distance from the loudness target")
    parser.add_argument("--report", type=Path, help="JSON with the placed events, mastering and measurements")
    parser.add_argument("--replace", action="store_true", help="overwrite the WAV (and the report) if they exist")
    args = parser.parse_args()
    utf8_console()

    for path in (args.plan, args.cues):
        if path is not None and not path.is_file():
            parser.error(f"file not found: {path}")
    for path in (args.out, args.report):
        if path is not None and path.exists() and not args.replace:
            parser.error(f"{path} exists; choose another name or pass --replace")
    if args.out.suffix.lower() != ".wav":
        parser.error("--out must be a .wav file")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        parser.error("FFmpeg must be on PATH: the loudness target is measured with it")

    try:
        plan = read_json(args.plan)
        cues = read_json(args.cues) if args.cues else {}
        base = (args.cues or args.plan).resolve().parent   # music files in cues.json are relative to it
        master, placed = render(plan, cues, args.seed, SR, base=base)
    except (ValueError, TypeError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if not np.isfinite(master).all() or float(np.max(np.abs(master), initial=0.0)) < 1e-6:
        print("error: the mix is silent: the plan has no hits and the cues place no voices", file=sys.stderr)
        return 1
    try:
        samples, mastering = master_to_target(master, ffmpeg, args.lufs, args.tp, SR)
    except RuntimeError as error:
        print(f"error: the mix cannot be measured: {error}", file=sys.stderr)
        return 1
    if not np.isfinite(samples).all() or np.max(np.abs(samples)) >= 1:
        print("error: the mix is not finite or reaches full scale", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.out.with_name(f"{args.out.stem}.{os.getpid()}.tmp.wav")
    try:
        data = write_wav(temporary, samples, SR)
        measured = ffmpeg_measure(ffmpeg, path=temporary, target_lufs=args.lufs, target_tp=args.tp, sr=SR)
        independent = independent_ebur128(ffmpeg, temporary)
        lufs_ok = abs(measured["integrated_lufs"] - args.lufs) <= args.tolerance_lu
        peak_ok = measured["true_peak_dbtp"] <= args.tp + .1
        if not (lufs_ok and peak_ok):
            print(f"error: the mix measures {measured['integrated_lufs']} LUFS and {measured['true_peak_dbtp']} dBTP; "
                  f"target {args.lufs} LUFS ±{args.tolerance_lu} and at most {args.tp} dBTP. Nothing was written.",
                  file=sys.stderr)
            return 1
        mono = read_wav_mono(temporary)
        hits = normalize_hits(plan.get("hits"))
        events = [{"time": h["time"], "role": h["role"], "source": "hits"} for h in hits]
        found = onsets(mono, max(24, 2 * len(events)))
        sync = match_events(found, events, EARLY_S, LATE_S) if events else {"events": [], "unmatched_events": [],
                                                                            "onsets_without_event": found}
        warnings = [f"no attack from {EARLY_S} s before to {LATE_S} s after {row['role']} at {row['time']} s"
                    for row in sync["unmatched_events"]]
        os.replace(temporary, args.out)
    finally:
        if temporary.exists():
            temporary.unlink()

    summary = {
        "soundtrack": str(args.out.resolve()), "seed": args.seed, "duration_s": round(len(samples) / SR, 3),
        "sample_rate": SR, "channels": 2, "pcm_bits": 16, "sha256": hashlib.sha256(data).hexdigest(),
        "integrated_lufs": measured["integrated_lufs"], "true_peak_dbtp": measured["true_peak_dbtp"],
        "lra_lu": measured["lra_lu"], "target_lufs": args.lufs, "target_true_peak_dbtp": args.tp,
        "independent_ebur128": independent, "mastering": mastering, "hits": placed["hits"],
        "cues": placed["cues"], "layers": placed["layers"], "highpass_hz": placed["highpass_hz"],
        "sync": sync, "warnings": warnings,
        "measurement_method": "FFmpeg loudnorm input measurement and ebur128 true peak on the written WAV",
        "listening": "not performed: the metrics do not judge the mix or how it feels with the picture",
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("soundtrack", "seed", "duration_s", "integrated_lufs", "true_peak_dbtp",
                                              "sha256", "warnings")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
