"""Hook variants for trial reels: several openings, one body, rendered once and joined.

  python -I <skill>/scripts/hook_variants.py init --piece work/reel --brief work/reel/brief.md   # variants.json from hooks:
  python -I <skill>/scripts/hook_variants.py render --piece work/reel [--variants variants.json] [--workers 3]
      [--audio auto|none|file.wav] [--crf 20] [--preset medium]

variants.json:
  {"seam": 2.5,                                   # seconds: from here every variant must look exactly the same
   "variants": [
     {"id": "a", "title": "Everything | moves for a reason"},              # the piece as it is (the control)
     {"id": "b", "title": "Nothing | moves for a reason", "hits": {"hook slam": 0.1}},
     {"id": "c", "title": "Stop | moves for a reason", "note": "a command instead of a claim"}]}

A variant changes the piece's TITLE (the const TITLE line that new_piece.py wrote) and, optionally, the time of named
hits. Each variant renders only frames [0, seam); the body [seam, end) renders once, from the piece itself. The seam
is checked, not assumed: the first body frame of every variant must match the piece's to the pixel (mean difference
under 0.5 of 255), or that variant is refused, because a jump at the seam would show in the video. Pick a seam after
the last moment that depends on the hook (after the transition that carries it away).
Sound: auto builds one soundtrack per variant from its own plan (and the piece's cues.json), so each hook's hits keep
their sound; none renders silent; a file uses that audio for all.
Out: final/hooks/<piece>-<id>.mp4, a report, and final/hooks/hooks.md: a table to fill with each trial reel's results.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import brief as briefs  # noqa: E402
from validate_plan import validate  # noqa: E402

TITLE_LINE = re.compile(r"^(\s*)const TITLE = .*?;[ \t]*$", re.MULTILINE)
SKIP = {"preview", "final", "node_modules", ".git"}


def read_title(script: str) -> str | None:
    match = TITLE_LINE.search(script)
    if not match:
        return None
    literal = match.group(0).split("=", 1)[1].strip().rstrip(";").strip()
    try:
        return json.loads(literal)
    except ValueError:
        return literal.strip("'\"")


def set_title(script: str, title: str) -> str:
    return TITLE_LINE.sub(lambda m: f"{m.group(1)}const TITLE = {json.dumps(title, ensure_ascii=False)};", script, count=1)


def fps_of(plan: dict) -> float:
    num, _, den = str(plan.get("fps", 60)).partition("/")
    return float(num) / float(den or 1)


def run(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")


def node(script: str, *args: object) -> subprocess.CompletedProcess:
    return run(["node", str(SCRIPTS / script), *map(str, args)])


def copy_piece(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for item in src.iterdir():
        if item.name in SKIP:
            continue
        if item.is_dir():
            shutil.copytree(item, dest / item.name)
        else:
            shutil.copy2(item, dest / item.name)


def frame_png(piece: Path, frame: int, out: Path) -> np.ndarray:
    from PIL import Image
    if out.exists():
        shutil.rmtree(out)
    r = node("sample_frames.mjs", "--root", piece, "--out", out, "--frames", f"{frame}:{frame}", "--png")
    if r.returncode != 0:
        raise RuntimeError(f"cannot sample frame {frame} of {piece}: {r.stderr[-400:]}")
    file = next(out.glob("*.png"))
    return np.asarray(Image.open(file).convert("RGB"), dtype=np.float32)


def frames_of(path: Path) -> int:
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(path)])
    return int((r.stdout or "0").strip() or 0)


# ---------------------------------------------------------------------------------------------------------------

def cmd_init(args) -> int:
    piece = args.piece.resolve()
    script = (piece / "piece.js").read_text(encoding="utf-8")
    base = read_title(script)
    if base is None:
        print(json.dumps({"errors": ["piece.js has no `const TITLE = ...;` line"]}))
        return 2
    data = briefs.fields(args.brief.read_text(encoding="utf-8-sig"))
    hooks = data.get("hooks") or []
    if len(hooks) < 2:
        print(json.dumps({"errors": ["the brief needs a `hooks:` list with two to four openings"]}))
        return 2
    rest = base.split("|", 1)[1].strip() if "|" in base else ""
    variants = [{"id": "a", "title": base, "note": "the piece as it is (control)"}]
    for k, hook in enumerate(hooks[:4], start=1):
        text = hook.split("->")[0].strip()
        title = f"{text} | {rest}" if rest else text
        variants.append({"id": chr(ord("a") + k), "title": title[:80], "note": hook})
    seam = briefs._seconds(data.get("seam")) if data.get("seam") else None
    out = piece / "variants.json"
    if out.exists() and not args.replace:
        print(json.dumps({"errors": [f"{out} exists (use --replace)"]}))
        return 2
    payload = {"seam": float(seam) if seam else None, "variants": variants}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    notes = [] if seam else ["no `seam:` in the brief: set \"seam\" in variants.json (seconds after the hook is gone)"]
    print(json.dumps({"written": str(out), "variants": len(variants), "notes": notes}, ensure_ascii=False, indent=2))
    return 0


def cmd_render(args) -> int:
    piece = args.piece.resolve()
    spec_path = (args.variants or piece / "variants.json").resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    plan = json.loads((piece / "plan.json").read_text(encoding="utf-8-sig"))
    script = (piece / "piece.js").read_text(encoding="utf-8")
    fps = fps_of(plan)
    total = plan["duration_frames"]
    errors = []
    seam = spec.get("seam")
    if not isinstance(seam, (int, float)) or not 0 < seam * fps < total - 1:
        errors.append("variants.json needs a seam (seconds) inside the piece")
    variants = spec.get("variants") or []
    ids = [v.get("id") for v in variants]
    if len(variants) < 2 or len(set(ids)) != len(ids) or not all(isinstance(i, str) and re.fullmatch(r"[\w-]{1,20}", i) for i in ids):
        errors.append("variants needs two or more entries with unique short ids")
    if read_title(script) is None:
        errors.append("piece.js has no `const TITLE = ...;` line to vary")
    if errors:
        print(json.dumps({"errors": errors}, indent=2))
        return 2
    seam_frame = round(seam * fps)
    name = piece.name
    work = piece / "preview" / "hooks"
    out_dir = piece / "final" / "hooks"
    out_dir.mkdir(parents=True, exist_ok=True)
    taken = [out_dir / f"{name}-{v['id']}.mp4" for v in variants if (out_dir / f"{name}-{v['id']}.mp4").exists()]
    if taken:
        print(json.dumps({"errors": [f"already rendered: {t}; archive it first" for t in taken]}, indent=2))
        return 2
    work.mkdir(parents=True, exist_ok=True)

    # 1. One folder per variant: the piece with its title and hits.
    folders = {}
    for v in variants:
        folder = work / v["id"]
        copy_piece(piece, folder)
        (folder / "piece.js").write_text(set_title(script, str(v.get("title", ""))), encoding="utf-8")
        vplan = json.loads(json.dumps(plan))
        for role, time in (v.get("hits") or {}).items():
            for h in vplan.get("hits") or []:
                if h.get("role") == role:
                    h["time"] = float(time)
        vplan["hits"] = sorted(vplan.get("hits") or [], key=lambda h: h["time"]) or vplan.get("hits")
        problems = validate(vplan)
        if problems:
            errors.append(f"variant {v['id']}: {problems}")
        (folder / "plan.json").write_text(json.dumps(vplan, ensure_ascii=False, indent=2), encoding="utf-8")
        folders[v["id"]] = folder
    if errors:
        print(json.dumps({"errors": errors}, indent=2))
        return 2

    # 2. The seam must match to the pixel, or the variant would jump into the body.
    reference = frame_png(piece, seam_frame, work / "seam-piece")
    seam_report = {}
    for vid, folder in folders.items():
        diff = float(np.abs(frame_png(folder, seam_frame, work / f"seam-{vid}") - reference).mean())
        seam_report[vid] = round(diff, 3)
        if diff > .5:
            errors.append(f"variant {vid} differs from the piece at the seam (frame {seam_frame}, mean {diff:.2f}/255): "
                          "move the seam later, after everything the hook touches has left the frame")
    if errors:
        print(json.dumps({"errors": errors, "seam_difference": seam_report}, indent=2))
        return 1

    # 3. Render: every hook [0, seam) and the body [seam, end) once, several at a time.
    jobs = [("body", piece, f"{seam_frame}:{total}", work / "body.mp4")]
    jobs += [(vid, folder, f"0:{seam_frame}", work / f"hook-{vid}.mp4") for vid, folder in folders.items()]

    def render(job):
        label, root, frames, out = job
        out.unlink(missing_ok=True)
        r = node("render_stream.mjs", "--root", root, "--out", out, "--frames", frames, "--no-audio", "--crf", args.crf,
                 "--preset", args.preset, "--report", str(out) + ".report.json", "--min-free-gb", "0.2")
        if r.returncode != 0 and frames_of(out) == 0:   # one retry: a browser can die in a long capture
            out.unlink(missing_ok=True)
            r = node("render_stream.mjs", "--root", root, "--out", out, "--frames", frames, "--no-audio", "--crf", args.crf,
                     "--preset", args.preset, "--report", str(out) + ".report.json", "--min-free-gb", "0.2")
        a, b = map(int, frames.split(":"))
        return label, r.returncode == 0 and frames_of(out) == b - a, r.stderr[-300:]

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(render, jobs))
    failed = [f"{label}: {log}" for label, ok, log in results if not ok]
    if failed:
        print(json.dumps({"errors": failed}, indent=2))
        return 1

    # 4. Sound per variant, then join hook + body.
    outputs = []
    for v in variants:
        vid, folder = v["id"], folders[v["id"]]
        audio = None
        if args.audio == "auto":
            cues = piece / "cues.json"
            sound = folder / "assets" / "soundtrack-variant.wav"
            argv = [sys.executable, "-I", str(SCRIPTS / "build_soundtrack.py"), "--plan", str(folder / "plan.json"),
                    "--out", str(sound), "--replace"]
            if cues.exists():
                argv += ["--cues", str(folder / "cues.json")]
            r = run(argv)
            if r.returncode != 0:
                print(json.dumps({"errors": [f"soundtrack for {vid}: {r.stderr[-400:]}"]}, indent=2))
                return 1
            audio = sound
        elif args.audio != "none":
            audio = Path(args.audio).resolve()
        listing = work / f"list-{vid}.txt"
        listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in (work / f"hook-{vid}.mp4", work / "body.mp4")), encoding="utf-8")
        out = out_dir / f"{name}-{vid}.mp4"
        argv = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-n", "-f", "concat", "-safe", "0", "-i", str(listing)]
        if audio:
            argv += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
        argv += ["-c:v", "copy", "-t", str(total / fps), "-movflags", "+faststart", str(out)]
        r = run(argv)
        if r.returncode != 0 or frames_of(out) != total:
            out.unlink(missing_ok=True)
            print(json.dumps({"errors": [f"join {vid}: {r.stderr[-400:]}"]}, indent=2))
            return 1
        outputs.append({"id": vid, "title": v.get("title"), "note": v.get("note", ""), "file": str(out),
                        "size_mb": round(out.stat().st_size / 1e6, 1)})

    log = out_dir / "hooks.md"
    if not log.exists():
        rows = "\n".join(f"| {o['id']} | {o['title']} | | | | | |" for o in outputs)
        log.write_text(f"""# Hook variants · {name}

One body, {len(outputs)} openings (seam at {seam:g} s). Post each as a trial reel at the same hour on different days,
or on the same day to different audiences; fill the row when it has had 24-48 h.

With a small account every number is noise: compare the **3-second skip rate** and the **average watch time** between
variants, not views. A difference under about ten points of skip rate is not a difference.

| id | hook | views | skip rate 3 s | average watch (s) | shares | verdict |
|---|---|---|---|---|---|---|
{rows}
""", encoding="utf-8")
    report = {"piece": str(piece), "seam_s": seam, "seam_frame": seam_frame, "seam_difference": seam_report,
              "frames_per_hook": seam_frame, "body_frames": total - seam_frame,
              "rendered_frames": seam_frame * len(variants) + total - seam_frame,
              "frames_if_rendered_whole": total * len(variants), "variants": outputs, "results_log": str(log)}
    (out_dir / "hooks-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init", help="variants.json from the brief's hooks: list")
    p_init.add_argument("--piece", type=Path, required=True)
    p_init.add_argument("--brief", type=Path, required=True)
    p_init.add_argument("--replace", action="store_true")
    p_render = sub.add_parser("render", help="render every hook and the body once, check the seam, join")
    p_render.add_argument("--piece", type=Path, required=True)
    p_render.add_argument("--variants", type=Path)
    p_render.add_argument("--workers", type=int, default=3)
    p_render.add_argument("--audio", default="auto", help="auto (one soundtrack per variant), none, or a file")
    p_render.add_argument("--crf", default="20")
    p_render.add_argument("--preset", default="medium")
    p_render.add_argument("--keep-work", action="store_true")
    args = parser.parse_args()
    return cmd_init(args) if args.command == "init" else cmd_render(args)


if __name__ == "__main__":
    raise SystemExit(main())
