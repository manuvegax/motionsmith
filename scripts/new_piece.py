"""Create a new piece from the starter or a scene recipe: the scene, a plan.json and its own copy of the kit.

The piece works on its own: the kit libraries are copied into it, because the capture server never serves files
outside the piece folder. Refuses a destination that exists and is not empty.

  python -I <skill>/scripts/new_piece.py work/2026-10-23-my-piece \\
      [--format reel|story|portrait|square|landscape] [--recipe NAME] [--fps 60] [--duration 4]
      [--title "TITLE"] [--mode kinetic] [--audio optional]
  python -I <skill>/scripts/new_piece.py --list-recipes

Every template positions things as fractions of the frame, so any format works; the title shrinks to fit the safe
area. The timings suit 3-8 s pieces (retime piece.js for longer ones).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

SKILL = Path(__file__).resolve().parents[1]
STARTER = SKILL / "templates" / "starter"
RECIPES = SKILL / "templates" / "recipes"
KIT = SKILL / "scripts" / "kit"
FONT_KIT = SKILL / "templates" / "fonts"    # Archivo, Fraunces, JetBrains Mono (SIL OFL), copied into assets/fonts
KIT_FILES = ("motion-math.js", "postfx-glsl.js", "timeline.js", "kinetic-type.js", "stage.js", "footage.js", "hyperframes.js")
# Frame size and working safe area per format (references/edit/formats-platforms.md; verify with real screenshots).
# "reel" is the union of the vertical short-form interfaces (Reels, TikTok, Shorts): right column and bottom captions.
FORMATS = {
    "reel": (1080, 1920, {"x": 80, "y": 220, "width": 850, "height": 1220}),
    "story": (1080, 1920, {"x": 60, "y": 250, "width": 960, "height": 1330}),
    "portrait": (1080, 1350, {"x": 60, "y": 135, "width": 960, "height": 1012}),
    "square": (1080, 1080, {"x": 60, "y": 86, "width": 960, "height": 908}),
    "landscape": (1920, 1080, {"x": 192, "y": 108, "width": 1536, "height": 864}),
}
PLAN_FORMAT = {"reel": "reel", "story": "story"}   # plan.json `format` values; other ratios are plain inserts
DEFAULT_SECONDS = {"story": 6.0}
PLACEHOLDER = "const TITLE = 'TITLE';"


def recipes() -> dict[str, dict]:
    out = {}
    for folder in sorted(RECIPES.glob("*/")) if RECIPES.exists() else []:
        meta = folder / "recipe.json"
        if (folder / "piece.js").exists() and meta.exists():
            out[folder.name] = json.loads(meta.read_text(encoding="utf-8")) | {"folder": folder}
    return out


def build_plan(fmt: str, fps: int, seconds: float, title: str, mode: str, audio: str, recipe: dict | None) -> dict:
    width, height, safe = FORMATS[fmt]
    frames = round(fps * seconds)
    hits = [{"time": round(min(2.0, seconds / 2), 3), "amplitude": 1, "role": "ring lands"}]
    intent = "Starting point: replace with the real intent of the scene"
    action = "The ring lands on an arc with overshoot; the title cascades in from the centre"
    if recipe:
        # A recipe hit is either absolute ("time") or anchored to the end ("from_end"): entrances keep their pace
        # and exits move with the duration. piece.js reads them back by role, so image and sound stay together.
        hits = [{"time": round(min(max(seconds - h["from_end"] if "from_end" in h else h["time"], 0), seconds), 3),
                 "amplitude": h.get("amplitude", 1), "role": h["role"]} for h in recipe["hits"]]
        intent, action = recipe["intent"], recipe["action"]
    plan = {
        "schema_version": 1, "width": width, "height": height, "fps": fps, "duration_frames": frames,
        "mode": mode, "audio": audio, "safe_area": dict(safe), "hits": hits,
        "scenes": [{"id": "piece", "start_frame": 0, "end_frame": frames, "intent": intent, "action": action,
                    "text": title, "transition": {"kind": "end", "carrier": ""}}],
    }
    if fmt in PLAN_FORMAT:
        plan["format"] = PLAN_FORMAT[fmt]
    return plan


def main() -> int:
    for stream in (sys.stdout, sys.stderr):   # cp1252 consoles under python -I
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    available = recipes()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("destination", type=Path, nargs="?")
    parser.add_argument("--format", choices=sorted(FORMATS), default="reel")
    parser.add_argument("--recipe", choices=sorted(available) or None, help="start from a scene recipe instead of the starter")
    parser.add_argument("--list-recipes", action="store_true")
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--duration", type=float, help="seconds (default: the recipe's, or 4; story 6)")
    parser.add_argument("--title", default=None, help="the main text drawn by the template")
    parser.add_argument("--mode", choices=("editorial", "kinetic", "diagram", "glow", "retro"), default=None)
    parser.add_argument("--audio", choices=("required", "optional", "forbidden"), default="optional")
    parser.add_argument("--hyperframes", action="store_true",
                        help="also make the piece a HyperFrames project (hyperframes.json, package.json): Studio preview and render")
    args = parser.parse_args()

    if args.list_recipes:
        print(json.dumps({name: {"what": r["what"], "seconds": r["default_seconds"]} for name, r in available.items()},
                         ensure_ascii=False, indent=2))
        return 0
    if args.destination is None:
        parser.error("a destination folder is required")

    recipe = available.get(args.recipe) if args.recipe else None
    template = recipe["folder"] if recipe else STARTER
    title = args.title if args.title is not None else (recipe["title"] if recipe else "TITLE")
    mode = args.mode or (recipe["mode"] if recipe else "kinetic")
    seconds = args.duration if args.duration is not None else (
        recipe["default_seconds"] if recipe else DEFAULT_SECONDS.get(args.format, 4.0))
    dest = args.destination.resolve()
    problems = []
    if dest == SKILL or SKILL in dest.parents:
        problems.append(f"the piece would live inside the skill ({SKILL}); the next install replaces that folder: "
                        "create it in your project instead")
    if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
        problems.append(f"destination exists and is not an empty folder: {dest}")
    if not 1 <= args.fps <= 120:
        problems.append("--fps must be between 1 and 120")
    shortest = recipe.get("min_seconds", 3) if recipe else 3
    if not shortest <= seconds <= 60:
        problems.append(f"--duration must be between {shortest:g} and 60 seconds for this template (its timings are absolute: retime piece.js for other lengths)")
    if not title.replace("|", " ").replace("*", " ").strip() or len(title) > 80:
        problems.append("--title must be 1-80 characters with at least one word ('|' and '*' are markers)")

    script = (template / "piece.js").read_text(encoding="utf-8")   # check the template before writing anything
    if PLACEHOLDER not in script:
        problems.append(f"{template.name}/piece.js has no {PLACEHOLDER!r} line: update the template or new_piece.py")
    if problems:
        print(json.dumps({"created": False, "errors": problems}, ensure_ascii=False, indent=2))
        return 2
    script = script.replace(PLACEHOLDER, f"const TITLE = {json.dumps(title, ensure_ascii=False)};", 1)

    (dest / "kit").mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "README.md"):
        shutil.copy2((template / name) if (template / name).exists() else (STARTER / name), dest / name)
    (dest / "piece.js").write_text(script, encoding="utf-8")
    for name in KIT_FILES:
        if (KIT / name).exists():
            shutil.copy2(KIT / name, dest / "kit" / name)
    for folder in ("assets", "preview"):
        (dest / folder).mkdir(exist_ok=True)
    if FONT_KIT.is_dir():
        shutil.copytree(FONT_KIT, dest / "assets" / "fonts", dirs_exist_ok=True)
    plan = build_plan(args.format, args.fps, seconds, title, mode, args.audio, recipe)
    if recipe and recipe.get("data"):   # the recipe's sample data (data.json): edit it, the piece reads it at setup
        shutil.copy2(recipe["folder"] / recipe["data"], dest / recipe["data"])
        plan["data"] = recipe["data"]
    (dest / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hyperframes   # index.html's root carries the plan's size and duration (the HyperFrames contract)
    hyperframes.sync(dest, check=False, version=hyperframes.DEFAULT_VERSION, project=args.hyperframes)

    skill = str(Path(__file__).resolve().parent).replace("\\", "/")
    print(json.dumps({
        "created": True, "piece": str(dest), "format": args.format, "recipe": args.recipe, "size": [plan["width"], plan["height"]],
        "fps": args.fps, "duration_s": seconds,
        "next": [f'python -I {skill}/validate_plan.py "{dest / "plan.json"}"',
                 f'node {skill}/determinism_check.mjs --root "{dest}"',
                 f'node {skill}/sample_frames.mjs --root "{dest}" --out "{dest / "preview" / "walk"}" --every 0.5'],
        "errors": [],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
