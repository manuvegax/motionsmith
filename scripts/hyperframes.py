"""Make a Motionsmith piece a HyperFrames project, or hand its render to a HyperFrames film as a clip.

  python -I <skill>/scripts/hyperframes.py sync <piece> [--check] [--version 0.8.192]
      Copy width, height, duration and fps from plan.json into index.html's root (the HyperFrames contract reads them
      before any script runs), and write hyperframes.json and package.json when missing. Then, inside the piece:
      npx hyperframes@<version> lint · check · preview · render. --check only reports a mismatch (exit 1).

  python -I <skill>/scripts/hyperframes.py clip <piece> --project <hyperframes project> --start 2.0
      [--video final/piece.mp4] [--audio assets/soundtrack.wav] [--track 1] [--name quote]
      Copy a rendered MP4 (and its WAV) into <project>/assets/motionsmith/ and print the <video>/<audio> elements to
      paste into the film's index.html. Refuses to overwrite a file that is already there.

The piece keeps working with Motionsmith's own tools: kit/hyperframes.js only answers HyperFrames' hf-seek events.
Guide: references/produce/hyperframes.md.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import shutil
import sys

DEFAULT_VERSION = "0.8.192"   # pin, as `hyperframes init` does: renders stay reproducible
GSAP = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"   # the version `hyperframes init` loads
ROOT_TAG = re.compile(r"<div\b[^>]*\bdata-motionsmith-root\b[^>]*>")
BLOCK = re.compile(r"\n?<!-- hyperframes:(head|timeline) -->.*?<!-- /hyperframes:\1 -->", re.S)


def hyperframes_blocks(duration: str) -> tuple[str, str]:
    head = (f'<!-- hyperframes:head -->\n<script src="{GSAP}"></script>\n<!-- /hyperframes:head -->')
    timeline = ('<!-- hyperframes:timeline -->\n<script>\n'
                '  /* HyperFrames only: the paused timeline it binds, as long as the piece; kit/hyperframes.js draws every\n'
                '     instant it seeks. Motionsmith\'s own tools never load GSAP, so this does nothing there. */\n'
                f'  if (window.gsap && window.__timelines) window.__timelines["motionsmith"] = MotionsmithHyperFrames.timeline(gsap, {duration});\n'
                '</script>\n<!-- /hyperframes:timeline -->')
    return head, timeline


def plan_numbers(piece: Path) -> dict:
    plan = json.loads((piece / "plan.json").read_text(encoding="utf-8"))
    fps = Fraction(plan["fps"]) if isinstance(plan["fps"], str) else Fraction(str(plan["fps"]))
    duration = Fraction(plan["duration_frames"]) / fps
    fps_text = plan["fps"] if isinstance(plan["fps"], str) else f'{plan["fps"]:g}'
    return {"width": int(plan["width"]), "height": int(plan["height"]), "duration": float(round(duration, 3)),
            "fps": float(fps), "fps_text": fps_text}


def root_attributes(tag: str) -> dict:
    found = dict(re.findall(r'\b(data-[a-z-]+)="([^"]*)"', tag))
    return {"width": found.get("data-width"), "height": found.get("data-height"), "duration": found.get("data-duration"),
            "fps": found.get("data-fps")}


def set_attribute(tag: str, name: str, value: str) -> str:
    if re.search(rf'\b{name}="[^"]*"', tag):
        return re.sub(rf'\b{name}="[^"]*"', f'{name}="{value}"', tag)
    return tag[:-1] + f' {name}="{value}">'


def sync(piece: Path, check: bool, version: str, project: bool = True) -> dict:
    index = piece / "index.html"
    html = index.read_text(encoding="utf-8")
    match = ROOT_TAG.search(html)
    if not match:
        return {"piece": str(piece), "ok": False, "error": "index.html has no <div data-motionsmith-root …>: copy it from templates/starter/index.html"}
    numbers = plan_numbers(piece)
    want = {"width": str(numbers["width"]), "height": str(numbers["height"]), "duration": f'{numbers["duration"]:g}',
            "fps": numbers["fps_text"]}   # HyperFrames renders at the root's data-fps: the shutter math assumes the plan's fps
    have = root_attributes(match.group(0))
    mismatch = {k: {"index.html": have[k], "plan.json": want[k]} for k in want if have[k] != want[k]}
    registered = re.search(r'MotionsmithHyperFrames\.timeline\(gsap, ([0-9.]+)\)', html)
    if registered and registered.group(1) != want["duration"]:
        mismatch["timeline"] = {"index.html": registered.group(1), "plan.json": want["duration"]}
    report = {"piece": str(piece), "size": [numbers["width"], numbers["height"]], "duration_s": numbers["duration"],
              "mismatch": mismatch, "written": []}
    if check:
        report["ok"] = not mismatch
        return report
    tag = match.group(0)
    for key, value in want.items():
        tag = set_attribute(tag, f"data-{key}", value)
    html = html[:match.start()] + tag + html[match.end():]
    html = BLOCK.sub("", html)
    if project:   # GSAP and the timeline registration only where HyperFrames will open the piece
        head, timeline = hyperframes_blocks(want["duration"])
        html = html.replace("</head>", head + "\n</head>", 1)
        html = html.replace('<script src="kit/hyperframes.js"></script>', '<script src="kit/hyperframes.js"></script>\n' + timeline, 1)
    viewport = f'<meta name="viewport" content="width={numbers["width"]}, height={numbers["height"]}">'
    html = re.sub(r'<meta name="viewport"[^>]*>', viewport, html) if 'name="viewport"' in html else html.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + viewport, 1)
    index.write_text(html, encoding="utf-8")
    report["written"].append("index.html")
    if not project:
        report["ok"] = True
        return report
    manifest = piece / "hyperframes.json"
    if not manifest.exists():
        manifest.write_text(json.dumps({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                                       "paths": {"assets": "assets"}, "media": {"autoProxy": True}}, indent=2) + "\n", encoding="utf-8")
        report["written"].append("hyperframes.json")
    package = piece / "package.json"
    if not package.exists():
        scripts = {name: f"npx --yes hyperframes@{version} {name}" for name in ("lint", "check", "preview", "render")}
        package.write_text(json.dumps({"name": re.sub(r"[^a-z0-9-]+", "-", piece.name.lower()).strip("-") or "motionsmith-piece",
                                       "private": True, "type": "module", "scripts": scripts}, indent=2) + "\n", encoding="utf-8")
        report["written"].append("package.json")
    report["ok"] = True
    report["next"] = [f"cd {piece}", f"npx --yes hyperframes@{version} lint", f"npx --yes hyperframes@{version} preview",
                      f"npx --yes hyperframes@{version} render --quality looks --output final/hyperframes.mp4"]
    return report


def clip(piece: Path, project: Path, start: float, video: Path | None, audio: Path | None, track: int, name: str | None) -> dict:
    numbers = plan_numbers(piece)
    name = re.sub(r"[^a-z0-9-]+", "-", (name or piece.name).lower()).strip("-") or "piece"
    video = (piece / video) if video and not video.is_absolute() else video
    if video is None:
        finals = sorted((piece / "final").glob("*.mp4")) if (piece / "final").is_dir() else []
        video = finals[0] if len(finals) == 1 else None
    if video is None or not video.is_file():
        return {"ok": False, "error": "pass --video: the rendered MP4 of the piece (render_stream.mjs)"}
    if not (project / "index.html").is_file():
        return {"ok": False, "error": f"{project} is not a HyperFrames project (no index.html)"}
    assets = project / "assets" / "motionsmith"
    assets.mkdir(parents=True, exist_ok=True)
    copies = [(video, assets / f"{name}{video.suffix.lower()}")]
    if audio:
        audio = (piece / audio) if not audio.is_absolute() else audio
        if not audio.is_file():
            return {"ok": False, "error": f"audio not found: {audio}"}
        copies.append((audio, assets / f"{name}{audio.suffix.lower()}"))
    taken = [str(dst) for _, dst in copies if dst.exists()]
    if taken:
        return {"ok": False, "error": "already in the project, rename with --name: " + ", ".join(taken)}
    for src, dst in copies:
        shutil.copy2(src, dst)
    rel = lambda p: p.relative_to(project).as_posix()
    d = f'{numbers["duration"]:g}'
    snippet = [f'<video id="ms-{name}" class="clip" src="{rel(copies[0][1])}" muted playsinline '
               f'data-start="{start:g}" data-duration="{d}" data-track-index="{track}"></video>']
    if audio:
        snippet.append(f'<audio id="ms-{name}-sound" src="{rel(copies[1][1])}" data-start="{start:g}" data-duration="{d}" '
                       f'data-track-index="{track + 10}" data-volume="1"></audio>')
    return {"ok": True, "copied": [rel(dst) for _, dst in copies], "paste_into_index_html": snippet,
            "note": "the clip's frames come from the MP4 (HyperFrames decodes it with FFmpeg); retime by moving data-start"}


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sync", help="make the piece a HyperFrames project (or --check it)")
    s.add_argument("piece", type=Path)
    s.add_argument("--check", action="store_true")
    s.add_argument("--version", default=DEFAULT_VERSION, help=f"HyperFrames CLI version to pin (default {DEFAULT_VERSION})")
    c = sub.add_parser("clip", help="copy a rendered piece into a HyperFrames film and print its <video> element")
    c.add_argument("piece", type=Path)
    c.add_argument("--project", type=Path, required=True)
    c.add_argument("--start", type=float, required=True, help="seconds on the film's timeline")
    c.add_argument("--video", type=Path)
    c.add_argument("--audio", type=Path)
    c.add_argument("--track", type=int, default=1)
    c.add_argument("--name")
    args = parser.parse_args()
    piece = args.piece.resolve()
    if not (piece / "plan.json").is_file():
        parser.error(f"not a Motionsmith piece (no plan.json): {piece}")
    if args.command == "sync":
        report = sync(piece, args.check, args.version)
    else:
        if args.start < 0:
            parser.error("--start must be zero or positive")
        report = clip(piece, args.project.resolve(), args.start, args.video, args.audio, args.track, args.name)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else (1 if args.command == "sync" and args.check else 2)


if __name__ == "__main__":
    sys.exit(main())
