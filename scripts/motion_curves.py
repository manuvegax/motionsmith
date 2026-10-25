"""Graph Editor for code: value and speed graphs, with the numbers After Effects shows only by eye.

Sources: a trajectory dumped with dump_state.mjs (--json), or easings evaluated by kit/motion-math.js itself
(--ease / --bezier / --ae), so the curve you plot is the curve the composition uses.

  python scripts/motion_curves.py --json preview/lens.json --key value --out preview/curvas-lente.png
  python scripts/motion_curves.py --ease linear --ease power3.out --ease easyEase --ae 80,80 --distance 900 --duration .6 --out curvas.png

Reports per curve: peak speed (units/s) and when, overshoot %, settle time, speed kinks and px per exposure at
the chosen shutter, with a motion-blur recommendation. It measures motion; it does not judge taste.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

KIT = Path(__file__).resolve().parent / "kit" / "motion-math.js"
COLORS = [(255, 90, 70), (90, 190, 255), (250, 210, 80), (120, 220, 140), (200, 140, 255), (255, 150, 200), (230, 230, 230)]


def eval_easings(specs: list[tuple[str, str]], samples: int) -> dict[str, list[float]]:
    """Ask motion-math.js for the progress of each easing at `samples` points (single source of truth)."""
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node is required to evaluate easings from motion-math.js")
    program = (
        "const M=require(process.argv[1]);const specs=JSON.parse(process.argv[2]);const n=+process.argv[3];const out={};"
        "for(const [label,kind,arg] of specs){let f;"
        "if(kind==='ease')f=M.easing(arg);else if(kind==='bezier')f=M.cubicBezier(...arg);"
        "else if(kind==='ae')f=M.aeEase({outInfluence:arg[0],inInfluence:arg[1],outSpeed:arg[2]||0,inSpeed:arg[3]||0});"
        "else if(kind==='spring')f=u=>M.spring(u*arg[2],{freq:arg[0],damping:arg[1]});"
        "out[label]=Array.from({length:n},(_,i)=>f(i/(n-1)));}"
        "process.stdout.write(JSON.stringify(out));"
    )
    payload = []
    for label, spec in specs:
        kind, _, arg = spec.partition(":")
        if kind in ("bezier", "ae", "spring") and arg:
            payload.append([label, kind, [float(v) for v in arg.split(",")]])
        else:
            payload.append([label, "ease", spec])
    result = subprocess.run([node, "-e", program, str(KIT), json.dumps(payload), str(samples)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[-800:])
    return json.loads(result.stdout)


def pick(value, key: str | None):
    """Extract a number or a vector from one sample value. key: 'value', 'value.0', 'x', 'pos.1'…"""
    if key:
        for part in key.split("."):
            value = value[int(part)] if isinstance(value, list) else value[part]
    if isinstance(value, dict):
        for name in ("value", "x", "pos", "position"):
            if name in value:
                return pick(value[name], None)
        raise ValueError("cannot pick a number from a dict sample; use --key")
    return value


def analyse(times: list[float], values: list, *, shutter: float, fps: float, settle_tol: float) -> dict:
    vectors = [v if isinstance(v, list) else [v] for v in values]
    dims = len(vectors[0])
    start, end = vectors[0], vectors[-1]
    travel = math.dist(start, end) if dims > 1 else abs(end[0] - start[0])
    speeds, mids = [], []
    for i in range(1, len(times)):
        dt = times[i] - times[i - 1]
        if dt <= 0:
            raise ValueError("times must increase")
        speeds.append(math.dist(vectors[i], vectors[i - 1]) / dt)
        mids.append((times[i] + times[i - 1]) / 2)
    peak_index = max(range(len(speeds)), key=speeds.__getitem__)
    peak = speeds[peak_index]
    # Overshoot: furthest progress past the end along the start→end direction.
    overshoot = 0.0
    if travel > 0:
        direction = [(e - s) / travel for s, e in zip(start, end)]
        progress = [sum((v[k] - start[k]) * direction[k] for k in range(dims)) / travel for v in vectors]
        overshoot = max(0.0, max(progress) - 1.0) * 100
    settle = times[0]
    tolerance = settle_tol * (travel if travel > 0 else 1.0)
    for t, v in zip(times, vectors):
        if math.dist(v, end) > tolerance:
            settle = t
    # Kinks: an isolated jump of the signed velocity (along the main direction) between two samples — a corner
    # where two keys meet with different speeds. Smooth peaks and direction reversals are not kinks.
    axis = [(e - s) / travel for s, e in zip(start, end)] if travel > 0 else [1.0] + [0.0] * (dims - 1)
    signed = [sum((vectors[i][k] - vectors[i - 1][k]) * axis[k] for k in range(dims)) / (times[i] - times[i - 1])
              for i in range(1, len(times))]
    dv = [signed[i] - signed[i - 1] for i in range(1, len(signed))]
    kinks = []
    for i in range(len(dv)):
        neighbours = max(abs(dv[i - 1]) if i > 0 else 0.0, abs(dv[i + 1]) if i + 1 < len(dv) else 0.0)
        if abs(dv[i]) > 6 * neighbours and abs(dv[i]) > .05 * peak:
            kinks.append(round(times[i + 1], 4))
    px = peak * shutter / 360 / fps
    if px < 1:
        advice = "none: below a pixel per exposure"
    elif px < 20:
        advice = "natural motion blur"
    elif px < 80:
        advice = "strong: check landing sharpness and ghosting"
    else:
        advice = "stylized smear: snaps and whips only"
    return {"duration_s": round(times[-1] - times[0], 4), "travel": round(travel, 3), "peak_speed": round(peak, 2),
            "peak_at_s": round(mids[peak_index], 4), "average_speed": round(travel / (times[-1] - times[0]), 2) if times[-1] > times[0] else 0,
            "peak_to_average": round(peak / (travel / (times[-1] - times[0])), 2) if travel > 0 else None,
            "overshoot_pct": round(overshoot, 2), "settled_at_s": round(settle, 4), "speed_kinks_at_s": kinks[:12],
            "px_per_exposure_at_peak": round(px, 2), "shutter_degrees": shutter, "fps": fps, "blur_advice": advice,
            "_speeds": speeds, "_mids": mids, "_vectors": vectors}


def font(size: int):
    from PIL import ImageFont
    for candidate in ("C:/Windows/Fonts/segoeui.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def plot(curves: dict[str, dict], times_by: dict[str, list[float]], out: Path, title: str) -> None:
    from PIL import Image, ImageDraw
    small, big = font(14), font(18)
    width, panel, pad = 1200, 380, 60
    image = Image.new("RGB", (width, panel * 2 + 90), (16, 16, 18))
    draw = ImageDraw.Draw(image)
    draw.text((pad, 12), title or "motion curves", font=big, fill=(235, 235, 235))
    tmin = min(t[0] for t in times_by.values())
    tmax = max(t[-1] for t in times_by.values())
    all_values = [v for c in curves.values() for vec in c["_vectors"] for v in vec]
    vmin, vmax = min(all_values), max(all_values)
    smax = max(max(c["_speeds"]) for c in curves.values()) or 1
    if vmax == vmin:
        vmax = vmin + 1
    def frame(top, label):
        draw.rectangle([pad, top, width - pad, top + panel - 40], outline=(70, 70, 76))
        draw.text((pad, top - 20), label, font=small, fill=(170, 170, 176))
    frame(60, "VALUE GRAPH · valor por eje")
    frame(60 + panel, "SPEED GRAPH · velocidad (unidades/s)")
    sx = lambda t: pad + (t - tmin) / ((tmax - tmin) or 1) * (width - 2 * pad)
    for index, (label, c) in enumerate(curves.items()):
        color = COLORS[index % len(COLORS)]
        times = times_by[label]
        for k in range(len(c["_vectors"][0])):
            pts = [(sx(t), 60 + panel - 40 - (v[k] - vmin) / (vmax - vmin) * (panel - 60) - 10) for t, v in zip(times, c["_vectors"])]
            draw.line(pts, fill=color if k == 0 else tuple(int(ch * .6) for ch in color), width=2)
        pts = [(sx(t), 60 + panel * 2 - 50 - s / smax * (panel - 70)) for t, s in zip(c["_mids"], c["_speeds"])]
        draw.line(pts, fill=color, width=2)
        px, py = sx(c["peak_at_s"]), 60 + panel * 2 - 50 - c["peak_speed"] / smax * (panel - 70)
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], outline=color)
        draw.text((pad + (index % 3) * 370, panel * 2 + 52 + (index // 3) * 16),
                  f"■ {label}: peak {c['peak_speed']:.0f}/s @ {c['peak_at_s']:.2f}s · overshoot {c['overshoot_pct']:.1f}%",
                  font=small, fill=color)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):   # cp1252 consoles under python -I
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", type=Path, action="append", default=[], help="dump_state.mjs output (repeatable)")
    parser.add_argument("--key", help="path inside each sample value: value, value.0, x…")
    parser.add_argument("--ease", action="append", default=[], help="easing name from motion-math.js (repeatable)")
    parser.add_argument("--bezier", action="append", default=[], help="x1,y1,x2,y2 (repeatable)")
    parser.add_argument("--ae", action="append", default=[], help="AE ease: outInfluence,inInfluence[,outSpeed,inSpeed] (repeatable)")
    parser.add_argument("--spring", action="append", default=[], help="freqHz,damping (uses --duration as time span)")
    parser.add_argument("--distance", type=float, default=1000, help="travel in px for synthetic curves")
    parser.add_argument("--duration", type=float, default=.6, help="seconds for synthetic curves")
    parser.add_argument("--samples", type=int, default=241)
    parser.add_argument("--shutter", type=float, default=180)
    parser.add_argument("--fps", type=float, default=60)
    parser.add_argument("--settle", type=float, default=.01, help="settled when within this fraction of the travel")
    parser.add_argument("--out", type=Path, help="PNG with value and speed graphs")
    parser.add_argument("--title", default="")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    curves, times_by, errors = {}, {}, []
    try:
        for path in args.json:
            data = json.loads(path.read_text(encoding="utf-8"))
            samples = data["samples"] if isinstance(data, dict) else data
            times = [float(s["t"]) for s in samples]
            values = [pick(s["value"], args.key) for s in samples]
            label = f"{path.stem}{'.' + args.key if args.key else ''}"
            curves[label] = analyse(times, values, shutter=args.shutter, fps=args.fps, settle_tol=args.settle)
            times_by[label] = times
        specs = [(name, name) for name in args.ease] + [(f"bezier({b})", f"bezier:{b}") for b in args.bezier]
        specs += [(f"ae({a})", f"ae:{a}") for a in args.ae] + [(f"spring({s})", f"spring:{s},{args.duration}") for s in args.spring]
        if specs:
            n = max(3, args.samples)
            progress = eval_easings(specs, n)
            times = [i / (n - 1) * args.duration for i in range(n)]
            for label, values in progress.items():
                curves[label] = analyse(times, [v * args.distance for v in values], shutter=args.shutter, fps=args.fps, settle_tol=args.settle)
                times_by[label] = times
        if not curves:
            errors.append("nothing to analyse: use --json and/or --ease/--bezier/--ae/--spring")
        elif args.out:
            plot(curves, times_by, args.out, args.title)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        errors.append(str(error))
    report = {"errors": errors, "curves": {k: {m: v for m, v in c.items() if not m.startswith("_")} for k, c in curves.items()},
              "plot": str(args.out.resolve()) if args.out and not errors else None,
              "limits": "Measures speed and shape; it does not judge taste or replace watching the motion."}
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text, encoding="utf-8")
    print(text)
    return int(bool(errors))


if __name__ == "__main__":
    sys.exit(main())
