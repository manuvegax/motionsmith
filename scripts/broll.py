"""B-roll: footage and photos with their provenance, a shot list from the plan, and a timeline the piece draws.

  python -I <skill>/scripts/broll.py ingest clip.mp4 photo.jpg --piece work/vo --source https://... --license cc0 [--author "Name"]
  python -I <skill>/scripts/broll.py shotlist --piece work/vo            # assets/broll/shots.json + shots.md, one shot per scene
  python -I <skill>/scripts/broll.py assemble --piece work/vo            # frames, stills and assets/broll/timeline.json
  python -I <skill>/scripts/broll.py credits --piece work/vo             # attribution lines for the caption

ingest copies each file into assets/broll/src/ and records it in assets/broll/provenance.json: source, licence,
author, sha256, size and duration. A file without a licence is refused; CC BY needs an author. --own marks the
person's own material; --ai marks AI-generated material (recorded, so a project that forbids it can check).
shotlist writes one shot per scene of plan.json (a voice plan gives one per phrase), alternating camera moves for
stills; fill each shot's "file" (a name from provenance), "in" (seconds into a clip), "move" and "focus".
assemble conforms every clip to the piece: trimmed to its scene, at the piece's fps, cropped to cover the frame around
its focus point, one JPEG per frame (a clip shorter than its scene holds its last frame, and says so); stills are
resized and moved in code by kit/footage.js (Ken Burns, parallax with an "fg" cut-out). It writes timeline.json and
links it from plan.json ("broll"). One grade for all sources lives in timeline.json ("grade") and is applied in the
piece. Frame folders are large (about 250 KB per frame at 1080x1920): delete assets/broll/frames after the final render.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

LICENSES = {"own", "cc0", "pd", "cc-by", "cc-by-sa", "pexels", "pixabay", "unsplash", "licensed"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}
MOVES = ["push-in", "pan-left", "pull-out", "pan-right", "tilt-up", "tilt-down"]


def utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def say(data, code: int = 0) -> int:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return code


def broll_dir(piece: Path) -> Path:
    return piece / "assets" / "broll"


def load_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base[:40] or "file"


def probe(path: Path) -> dict:
    if path.suffix.lower() in IMAGE_EXT:
        from PIL import Image
        with Image.open(path) as im:
            return {"kind": "image", "width": im.width, "height": im.height}
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,avg_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True)
    data = json.loads(out.stdout or "{}")
    if not data.get("streams"):
        raise ValueError(f"{path.name}: no video stream")
    s = data["streams"][0]
    num, _, den = s.get("avg_frame_rate", "0/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 0
    return {"kind": "video", "width": s["width"], "height": s["height"], "fps": round(fps, 3),
            "duration": round(float(data.get("format", {}).get("duration", 0)), 3)}


def plan_of(piece: Path) -> tuple[dict, float]:
    plan = json.loads((piece / "plan.json").read_text(encoding="utf-8-sig"))
    num, _, den = str(plan.get("fps", 60)).partition("/")
    return plan, float(num) / float(den or 1)


# ---------------------------------------------------------------------------------------------------------------

def cmd_ingest(args) -> int:
    piece = args.piece.resolve()
    license_ = "own" if args.own else (args.license or "").lower()
    if license_ not in LICENSES:
        return say({"errors": [f"--license must be one of {sorted(LICENSES)} (or --own): material without a known "
                               "licence does not go into a piece"]}, 2)
    if license_ in {"cc-by", "cc-by-sa"} and not args.author:
        return say({"errors": ["CC BY needs --author: the credit is part of the licence"]}, 2)
    if license_ != "own" and not args.source:
        return say({"errors": ["--source (where it came from: a URL or a description) is required"]}, 2)
    record_path = broll_dir(piece) / "provenance.json"
    records = load_json(record_path, [])
    added, warnings = [], []
    for file in args.files:
        src = file.resolve()
        if not src.is_file():
            return say({"errors": [f"not a file: {src}"]}, 2)
        info = probe(src)
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        if any(r["sha256"] == digest for r in records):
            warnings.append(f"{src.name} is already ingested")
            continue
        name = f"{slug(src.stem)}{src.suffix.lower()}"
        n = 2
        while any(r["file"] == name for r in records):
            name = f"{slug(src.stem)}-{n}{src.suffix.lower()}"
            n += 1
        dest = broll_dir(piece) / "src" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        record = {"file": name, "path": dest.relative_to(piece).as_posix(), "original_name": src.name, **info,
                  "source": args.source or "own material", "license": license_, "author": args.author or "",
                  "title": args.title or src.stem, "ai_generated": bool(args.ai), "sha256": digest,
                  "ingested": dt.date.today().isoformat(), "notes": args.notes or ""}
        if args.ai:
            warnings.append(f"{name} is marked AI-generated: check the project allows it")
        records.append(record)
        added.append(record)
    write_json(record_path, records)
    return say({"added": [{k: r[k] for k in ("file", "kind", "license", "source")} for r in added],
                "provenance": str(record_path), "warnings": warnings})


def cmd_shotlist(args) -> int:
    piece = args.piece.resolve()
    plan, fps = plan_of(piece)
    out = broll_dir(piece) / "shots.json"
    if out.exists() and not args.replace:
        return say({"errors": [f"{out} exists (use --replace); edit it instead"]}, 2)
    records = load_json(broll_dir(piece) / "provenance.json", [])
    shots = []
    for k, scene in enumerate(plan.get("scenes") or []):
        start, end = scene["start_frame"] / fps, scene["end_frame"] / fps
        shots.append({"id": scene["id"], "start": round(start, 4), "end": round(end, 4), "duration": round(end - start, 3),
                      "say": scene.get("text", ""), "screen": scene.get("action", ""),
                      "file": "", "in": 0, "move": MOVES[k % len(MOVES)], "focus": [.5, .5], "fg": ""})
    write_json(out, {"fps": fps, "available": [r["file"] for r in records], "shots": shots})
    rows = "\n".join(f"| {s['id']} | {s['duration']:.1f} s | {s['say'][:48]} | {s['screen'][:48]} | | {s['move']} |" for s in shots)
    (broll_dir(piece) / "shots.md").write_text(
        "# Shot list\n\nOne shot per scene. Fill `file` in shots.json with a name from provenance.json; the picture "
        "should add what the voice does not say.\n\n| scene | length | said | screen | file | move |\n|---|---|---|---|---|---|\n"
        + rows + "\n", encoding="utf-8", newline="\n")
    return say({"shots": len(shots), "written": [str(out), str(broll_dir(piece) / "shots.md")],
                "available": [r["file"] for r in records]})


def cmd_assemble(args) -> int:
    piece = args.piece.resolve()
    plan, fps = plan_of(piece)
    W, H = plan["width"], plan["height"]
    spec = load_json(broll_dir(piece) / "shots.json", None)
    if not spec:
        return say({"errors": ["no assets/broll/shots.json: run shotlist first"]}, 2)
    records = {r["file"]: r for r in load_json(broll_dir(piece) / "provenance.json", [])}
    errors, warnings, segments = [], [], []
    frames_root = broll_dir(piece) / "frames"
    stills_root = broll_dir(piece) / "stills"
    if frames_root.exists():
        shutil.rmtree(frames_root)
    for shot in spec["shots"]:
        sid, start, end = shot["id"], float(shot["start"]), float(shot["end"])
        file = (shot.get("file") or "").strip()
        if not file:
            warnings.append(f"{sid}: no file, the scene keeps the piece's own background")
            segments.append({"id": sid, "start": start, "end": end, "kind": "gap"})
            continue
        record = records.get(file)
        if not record:
            errors.append(f"{sid}: {file} is not in provenance.json (ingest it first: no material without its licence)")
            continue
        src = piece / record["path"]
        focus = [float(v) for v in (shot.get("focus") or [.5, .5])]
        if record["kind"] == "video":
            need = end - start
            count = max(1, round(end * fps) - round(start * fps))
            begin = float(shot.get("in") or 0)
            available = record["duration"] - begin
            if available <= 0:
                errors.append(f"{sid}: in = {begin} s is past the end of {file} ({record['duration']} s)")
                continue
            if available + 1 / fps < need:
                warnings.append(f"{sid}: {file} has {available:.2f} s from its in-point, the scene needs {need:.2f}: "
                                "its last frame holds (choose an earlier in-point or a longer clip)")
            folder = frames_root / sid
            folder.mkdir(parents=True)
            fx, fy = (min(max(v, 0), 1) for v in focus)
            vf = (f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,"
                  f"crop={W}:{H}:(iw-{W})*{fx}:(ih-{H})*{fy},tpad=stop_mode=clone:stop_duration={need + 1}")
            r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(begin), "-i", str(src), "-an", "-vf", vf,
                                "-frames:v", str(count), "-q:v", str(args.quality), "-start_number", "0",
                                str(folder / "f%06d.jpg")], capture_output=True, text=True)
            written = len(list(folder.glob("f*.jpg")))
            if r.returncode or written != count:
                errors.append(f"{sid}: ffmpeg wrote {written} of {count} frames: {r.stderr[-300:]}")
                continue
            segments.append({"id": sid, "start": start, "end": end, "kind": "video", "file": file,
                             "dir": folder.relative_to(piece).as_posix(), "count": count, "focus": focus})
        else:
            from PIL import Image
            stills_root.mkdir(parents=True, exist_ok=True)
            dest = stills_root / f"{sid}.jpg"
            with Image.open(src) as im:
                im = im.convert("RGB")
                limit = 2 * max(W, H)
                if max(im.size) > limit:
                    im.thumbnail((limit, limit), Image.LANCZOS)
                if min(im.width / W, im.height / H) < 1:
                    warnings.append(f"{sid}: {file} is {im.width}x{im.height}, smaller than the frame: it will look soft")
                im.save(dest, quality=92)
            segment = {"id": sid, "start": start, "end": end, "kind": "still", "file": file,
                       "image": dest.relative_to(piece).as_posix(), "move": shot.get("move") or "push-in", "focus": focus}
            fg = (shot.get("fg") or "").strip()
            if fg:
                fg_record = records.get(fg)
                if not fg_record:
                    errors.append(f"{sid}: fg {fg} is not in provenance.json")
                    continue
                fg_dest = stills_root / f"{sid}-fg.png"
                shutil.copy2(piece / fg_record["path"], fg_dest)
                segment["fg"] = fg_dest.relative_to(piece).as_posix()
            segments.append(segment)
    if errors:
        return say({"errors": errors, "warnings": warnings}, 1)
    old = load_json(broll_dir(piece) / "timeline.json", {})
    timeline = {"fps": fps, "width": W, "height": H,
                "grade": old.get("grade") or {"contrast": 1.08, "saturate": .9, "brightness": 1, "warmth": .06, "lift": .02},
                "segments": segments}
    write_json(broll_dir(piece) / "timeline.json", timeline)
    plan["broll"] = "assets/broll/timeline.json"
    write_json(piece / "plan.json", plan)
    size = sum(f.stat().st_size for f in broll_dir(piece).rglob("*") if f.is_file() and ("frames" in f.parts or "stills" in f.parts))
    return say({"timeline": str(broll_dir(piece) / "timeline.json"), "segments": len(segments),
                "video": sum(s["kind"] == "video" for s in segments), "stills": sum(s["kind"] == "still" for s in segments),
                "gaps": sum(s["kind"] == "gap" for s in segments), "disk_mb": round(size / 1e6, 1), "warnings": warnings})


def cmd_credits(args) -> int:
    piece = args.piece.resolve()
    records = {r["file"]: r for r in load_json(broll_dir(piece) / "provenance.json", [])}
    timeline = load_json(broll_dir(piece) / "timeline.json", {"segments": []})
    used = []
    for s in timeline["segments"]:
        for key in ("file",):
            if s.get(key) and s[key] not in used:
                used.append(s[key])
    lines, missing = [], []
    for name in used:
        r = records.get(name)
        if not r:
            missing.append(name)
            continue
        if r["license"] == "own":
            continue
        who = f" — {r['author']}" if r["author"] else ""
        lines.append(f"{r['title']}{who} ({r['license'].upper()}) {r['source']}")
    text = "\n".join(lines)
    (broll_dir(piece) / "credits.txt").write_text(text + ("\n" if text else ""), encoding="utf-8")
    needs = any(records[n]["license"] in {"cc-by", "cc-by-sa"} for n in used if n in records)
    return say({"credits": lines, "attribution_required": needs, "missing": missing,
                "written": str(broll_dir(piece) / "credits.txt")})


def main() -> int:
    utf8()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("ingest", help="copy footage or photos into the piece with their provenance")
    p.add_argument("files", type=Path, nargs="+")
    p.add_argument("--piece", type=Path, required=True)
    p.add_argument("--source", help="URL or description of where it came from")
    p.add_argument("--license", help=", ".join(sorted(LICENSES)))
    p.add_argument("--author", default="")
    p.add_argument("--title", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--own", action="store_true", help="the person's own material")
    p.add_argument("--ai", action="store_true", help="AI-generated material (recorded)")
    p = sub.add_parser("shotlist", help="one shot per scene of plan.json")
    p.add_argument("--piece", type=Path, required=True)
    p.add_argument("--replace", action="store_true")
    p = sub.add_parser("assemble", help="conform the shots into frames, stills and timeline.json")
    p.add_argument("--piece", type=Path, required=True)
    p.add_argument("--quality", type=int, default=3, help="JPEG quality for ffmpeg (2 best .. 31 worst)")
    p = sub.add_parser("credits", help="attribution lines for what the timeline uses")
    p.add_argument("--piece", type=Path, required=True)
    args = parser.parse_args()
    return {"ingest": cmd_ingest, "shotlist": cmd_shotlist, "assemble": cmd_assemble, "credits": cmd_credits}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
