"""The motion brief: six tagged blocks that decide a piece before any code is written.

A brief is a Markdown file with the blocks <inputs>, <direction>, <structure>, <build>, <gotchas> and <start>
(the structure of the strongest prompts in the Prompt Motion gallery; references/create/motion-brief.md). It is the
plan written in words, and it doubles as a portable prompt for any agent.

  python -I <skill>/scripts/brief.py list                                   # the brief templates
  python -I <skill>/scripts/brief.py new work/piece/brief.md --template reel-hook [--set duration=12 --set bpm=100]
  python -I <skill>/scripts/brief.py check work/piece/brief.md              # decisions present, tempo arithmetic
  python -I <skill>/scripts/brief.py grid --bpm 120 --duration 15 [--meter 4] [--lead 0] [--fps 60]
  python -I <skill>/scripts/brief.py plan work/piece/brief.md --plan work/piece/plan.json [--hits bar|beat|none] [--replace-hits]

`check` reads lines such as `concept: ...`, `banned:` with `- avoid -> instead` items, `tempo: 120 BPM`,
`meter: 4/4`, `duration: 15 s`, `bars: 7.5`, `loop: yes` (Spanish keys work too: concepto, prohibido, compás,
duración, compases, bucle, público). It checks that the decisions exist and that the numbers agree; it never judges
whether the idea is good.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import sys

SKILL = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL / "templates" / "briefs"
BLOCKS = ("inputs", "direction", "structure", "build", "gotchas", "start")
REQUIRED = ("direction", "structure", "build", "start")
# Key aliases (English and Spanish) -> canonical key. Matched at the start of a line, before a colon.
ALIASES = {
    "concept": "concept", "concepto": "concept", "idea": "concept",
    "recurring element": "recurring", "recurring": "recurring", "elemento recurrente": "recurring", "hilo": "recurring",
    "banned": "banned", "ban": "banned", "avoid": "banned", "prohibido": "banned", "prohibidos": "banned",
    "evitar": "banned",
    "tempo": "tempo", "bpm": "tempo",
    "meter": "meter", "compás": "meter", "compas": "meter", "metric": "meter", "métrica": "meter",
    "duration": "duration", "duración": "duration", "duracion": "duration", "length": "duration",
    "bars": "bars", "compases": "bars",
    "lead": "lead", "downbeat": "lead", "primer tiempo": "lead",
    "loop": "loop", "bucle": "loop",
    "audience": "audience", "público": "audience", "publico": "audience", "audiencia": "audience",
    "facts": "facts", "hechos": "facts", "datos": "facts",
    "kind": "kind", "tipo": "kind",
    "format": "format", "formato": "format",
    "ending": "ending", "final": "ending", "cierre": "ending",
}
ARROWS = re.compile(r"\s*(?:->|→|=>|—>|\binstead\s*:|\ben su lugar\s*:)\s*", re.IGNORECASE)
PLACEHOLDER = re.compile(r"\{\{\s*([a-zA-Z_][\w-]*)\s*(?:\|([^}]*))?\}\}")
YES = {"yes", "y", "true", "sí", "si", "seamless", "on"}
NO = {"no", "n", "false", "off", "none", "ninguno"}
FREE_TEMPO = {"free", "voice", "voz", "libre", "none", "ninguno"}


def _stdout_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):   # cp1252 consoles under python -I
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------------------------------------------
# Parsing

def blocks(text: str) -> dict[str, str]:
    """Return the body of each tagged block. A block is <name> ... </name>; unknown tags are ignored."""
    found = {}
    for name in BLOCKS:
        match = re.search(rf"<{name}>(.*?)</{name}>", text, re.IGNORECASE | re.DOTALL)
        if match:
            found[name] = match.group(1).strip("\n")
    return found


def fields(text: str) -> dict:
    """Read `key: value` lines (any block) and the banned list. Later lines do not override earlier ones."""
    out: dict = {"banned": []}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip().lstrip("-*• ").strip()
        match = re.match(r"^\**([A-Za-zÁÉÍÓÚáéíóúñÑ ]{2,24}?)\**\s*:\s*(.*)$", line)
        key = ALIASES.get(match.group(1).strip().lower()) if match else None
        if key == "banned":
            inline = match.group(2).strip()
            items = [s for s in re.split(r"\s*;\s*", inline) if s] if inline else []
            j = i + 1
            # The list continues on indented or bulleted lines until a blank line or another key.
            while j < len(lines) and re.match(r"^\s*[-*•]\s+", lines[j]):
                items.append(re.sub(r"^\s*[-*•]\s+", "", lines[j]).strip())
                j += 1
            for item in items:
                if item:
                    out["banned"].append(_ban(item))
            i = j
            continue
        if key and key not in out and match.group(2).strip():
            out[key] = match.group(2).strip()
        i += 1
    return out


def _ban(item: str) -> dict:
    parts = ARROWS.split(item, maxsplit=1)
    avoid = parts[0].strip(" .;,")
    instead = parts[1].strip(" .;,") if len(parts) > 1 else ""
    return {"avoid": avoid, "instead": instead}


def _number(value: str | None) -> Fraction | None:
    if not value:
        return None
    match = re.search(r"(\d+(?:[.,]\d+)?)(?:\s*/\s*(\d+))?", value)
    if not match:
        return None
    number = Fraction(match.group(1).replace(",", "."))
    return number / int(match.group(2)) if match.group(2) else number


def _meter(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(\d+)\s*/\s*\d+", value) or re.search(r"(\d+)", value)
    return int(match.group(1)) if match else None


def _seconds(value: str | None) -> Fraction | None:
    """'15 s', '15', '0:15', '1:30', '90 frames @ 60' are all accepted."""
    if not value:
        return None
    clock = re.search(r"(\d+):(\d{2})", value)
    if clock:
        return Fraction(int(clock.group(1)) * 60 + int(clock.group(2)))
    frames = re.search(r"(\d+)\s*(?:frames|fotogramas)\s*(?:@|at|a)\s*(\d+)", value, re.IGNORECASE)
    if frames:
        return Fraction(int(frames.group(1)), int(frames.group(2)))
    return _number(value)


WORDS_PER_SECOND = 2.5   # a natural Spanish or English voice-over (about 150 words a minute)


def script_rows(text: str) -> list[dict]:
    """The two-column script table (| voice | screen |) of a voice-over brief; the header row is skipped."""
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or re.match(r"^\|?\s*:?-{3,}", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or cells[0].lower() in {"voice", "voz", "vo", "audio", "lo que se oye"}:
            continue
        rows.append({"voice": cells[0].replace("*", ""), "screen": cells[1]})
    return rows


# ---------------------------------------------------------------------------------------------------------------
# Grid

def grid(bpm: Fraction, duration: Fraction, meter: int = 4, lead: Fraction = Fraction(0), fps: int = 60) -> dict:
    beat = Fraction(60) / bpm
    beats = []
    k = 0
    while lead + k * beat < duration:
        t = lead + k * beat
        beats.append({"index": k, "bar": k // meter + 1, "beat": k % meter + 1, "time": float(round(t, 4)),
                      "frame": int(t * fps), "downbeat": k % meter == 0})
        k += 1
    bars = (duration - lead) / (beat * meter)
    return {"bpm": float(bpm), "meter": meter, "lead": float(lead), "fps": fps, "duration": float(duration),
            "beat_seconds": float(round(beat, 6)), "bar_seconds": float(round(beat * meter, 6)),
            "beat_frames": float(round(beat * fps, 3)), "bars": float(round(bars, 4)), "beats": beats,
            "whole_bars": bars.denominator == 1}


def _grid_table(g: dict) -> str:
    rows = [f"{g['bpm']:g} BPM, {g['meter']}/4: a beat is {g['beat_seconds']:g} s ({g['beat_frames']:g} frames at "
            f"{g['fps']}), a bar {g['bar_seconds']:g} s; {g['duration']:g} s hold {g['bars']:g} bars"
            + ("" if g["whole_bars"] else " (not a whole number: say which bar is short or where the piece ends)"),
            "", "| bar | beat | time (s) | frame |", "|---|---|---|---|"]
    for b in g["beats"]:
        rows.append(f"| {b['bar']} | {b['beat']}{' ●' if b['downbeat'] else ''} | {b['time']:g} | {b['frame']} |")
    return "\n".join(rows)


# ---------------------------------------------------------------------------------------------------------------
# Check

def check(text: str) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    found = blocks(text)
    for name in REQUIRED:
        if name not in found:
            errors.append(f"missing <{name}> block")
    for name in ("inputs", "gotchas"):
        if name not in found:
            warnings.append(f"no <{name}> block: " + ("say what to ask before building" if name == "inputs"
                                                     else "list the known failure points (text blur, overlap, loop seam)"))
    unfilled = sorted({m.group(1) for m in PLACEHOLDER.finditer(text) if m.group(2) is None})
    if unfilled:
        errors.append("unfilled placeholders: " + ", ".join(unfilled) + " (brief.py new --set name=value)")
    data = fields(text)

    if not data.get("concept"):
        errors.append("no `concept:` line: name the one idea in one line (one concept, not a tour of effects)")
    elif len(data["concept"].split()) > 40:
        warnings.append("the concept runs past 40 words: it should fit one line")
    if not data.get("recurring"):
        warnings.append("no `recurring element:`: the one thing that carries every transition (a shape, a word, a line)")

    banned = data["banned"]
    if len(banned) < 3:
        errors.append(f"banned list has {len(banned)} items: name 5–9 defaults to rule out, each with what to do instead")
    else:
        if len(banned) < 5 or len(banned) > 9:
            warnings.append(f"banned list has {len(banned)} items; 5–9 keeps it a decision, not a manifesto")
        missing = [b["avoid"] for b in banned
                   if not b["instead"] and not re.search(r"templat|plantilla", b["avoid"], re.IGNORECASE)]
        if missing:
            warnings.append("banned items without an alternative (write `avoid -> instead`): " + "; ".join(missing[:4]))
        if not any(re.search(r"templat|plantilla", b["avoid"], re.IGNORECASE) for b in banned):
            warnings.append("end the banned list with `anything that looks like a template` so unnamed defaults are judged too")

    duration = _seconds(data.get("duration"))
    if duration is None or duration <= 0:
        errors.append("no `duration:` (seconds): it sets how many states and beats fit")
    tempo_text = (data.get("tempo") or "").strip().lower()
    free = tempo_text.split()[0] in FREE_TEMPO if tempo_text else False
    bpm = None if free else _number(data.get("tempo"))
    derived = None
    if not tempo_text:
        errors.append("no `tempo:`: give BPM (cuts land on a grid) or `tempo: voice` / `free` and say what drives the timing")
    elif not free and (bpm is None or not 0 < bpm <= 400):
        errors.append(f"tempo `{data.get('tempo')}` is not a BPM in (0, 400]")
    meter = _meter(data.get("meter")) or 4
    lead = _seconds(data.get("lead")) or Fraction(0)
    if bpm and duration:
        derived = grid(bpm, duration, meter, lead)
        stated = _number(data.get("bars"))
        if stated is not None and abs(Fraction(stated) - Fraction(str(derived["bars"]))) > Fraction(1, 100):
            errors.append(f"bars say {float(stated):g} but {float(duration):g} s at {float(bpm):g} BPM in {meter}/4 "
                          f"hold {derived['bars']:g}: fix the duration, the tempo or the bar count")
        if not derived["whole_bars"] and stated is None:
            warnings.append(f"{derived['bars']:g} bars is not a whole number: say what the last partial bar holds "
                            "(an end title on half a bar, a tail) or change the duration")
        if derived["beat_seconds"] < 0.2:
            warnings.append("a beat under 0.2 s: an event on every beat will strobe; act on every second beat")

    loop = (data.get("loop") or "").strip().lower()
    if not loop:
        warnings.append("say `loop: yes` (last frame matches the first) or `loop: no`")
    elif loop.split()[0].strip(".,;") not in YES | NO:
        warnings.append(f"loop `{data.get('loop')}`: use yes or no")
    if not data.get("ending"):
        warnings.append("no `ending:`: name what the last frame holds (the reveal, a line, a logo, the loop seam)")

    kind = (data.get("kind") or "").lower()
    script = script_rows(text)
    spoken = None
    if script or "voice" in kind or "voz" in kind:
        if not script:
            errors.append("a voice-over brief needs its script as a two-column table: | voice | screen |")
        else:
            words = sum(len(r["voice"].split()) for r in script)
            spoken = round(words / WORDS_PER_SECOND, 1)
            empty = [r["voice"][:30] for r in script if not r["screen"].strip()]
            if empty:
                warnings.append("rows with no screen column (what is seen while it is said): " + "; ".join(empty[:3]))
            if duration and not .75 <= float(duration) / max(spoken, .1) <= 1.6:
                warnings.append(f"the script has {words} words, about {spoken:g} s spoken at {WORDS_PER_SECOND} words per "
                                f"second, but duration says {float(duration):g} s: cut words or change the duration")
    if "explain" in kind or "explica" in kind:
        if not data.get("audience"):
            errors.append("explainer without `audience:`: one line on who watches sets vocabulary and pace")
        if not data.get("facts"):
            errors.append("explainer without `facts:`: research first, never invent numbers, names, dates or quotes")
    if "start" in found and not re.search(r"grid|rejilla|storyboard|beat|concept|concepto|period|periodo|step list|steps|pasos|script|guion", found["start"], re.IGNORECASE):
        warnings.append("<start> should ask for the concept line and the beat grid or storyboard before any code")
    if "build" in found and not re.search(r"review|revis|per beat|por beat|frame per|fotograma", found["build"], re.IGNORECASE):
        warnings.append("<build> has no review step: one frame per beat before the full render")

    summary = {k: data.get(k) for k in ("kind", "concept", "recurring", "duration", "tempo", "meter", "bars", "lead",
                                         "loop", "ending", "audience", "format") if data.get(k)}
    summary["banned"] = banned
    if spoken is not None:
        summary["script"] = {"rows": len(script), "words": sum(len(r["voice"].split()) for r in script),
                             "estimated_seconds": spoken}
    if derived:
        summary["grid"] = {k: derived[k] for k in ("bpm", "meter", "lead", "beat_seconds", "bar_seconds", "bars", "whole_bars")}
    return {"errors": errors, "warnings": warnings, "blocks": [b for b in BLOCKS if b in found], "brief": summary,
            "idea_quality_checked": False}


# ---------------------------------------------------------------------------------------------------------------
# Templates

def templates() -> dict[str, Path]:
    return {p.stem: p for p in sorted(TEMPLATES.glob("*.md")) if p.stem.lower() != "readme"} if TEMPLATES.exists() else {}


def fill(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        name, default = match.group(1), match.group(2)
        if name in values:
            return values[name]
        return default.strip() if default is not None else match.group(0)
    return PLACEHOLDER.sub(replace, text)


def template_variables(text: str) -> list[tuple[str, str | None]]:
    seen, out = set(), []
    for m in PLACEHOLDER.finditer(text):
        if m.group(1) not in seen:
            seen.add(m.group(1))
            out.append((m.group(1), m.group(2).strip() if m.group(2) is not None else None))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Plan

def to_plan(text: str, plan: dict, *, hits: str = "bar", replace_hits: bool = False) -> tuple[dict, list[str]]:
    """Copy the brief's decisions into plan.json fields; add grid hits when the plan has none (or when asked)."""
    notes = []
    data = fields(text)
    if data.get("concept"):
        plan["concept"] = data["concept"]
    if data.get("recurring"):
        plan["recurring_element"] = data["recurring"]
    if data["banned"]:
        plan["banned"] = data["banned"]
    if data.get("audience"):
        plan["audience"] = data["audience"]
    loop = (data.get("loop") or "").strip().lower()
    if loop:
        plan["loop"] = loop.split()[0].strip(".,;") in YES
    tempo_text = (data.get("tempo") or "").strip().lower()
    bpm = None if (tempo_text and tempo_text.split()[0] in FREE_TEMPO) else _number(data.get("tempo"))
    meter = _meter(data.get("meter")) or 4
    lead = _seconds(data.get("lead")) or Fraction(0)
    if bpm:
        plan["bpm"] = float(bpm) if bpm.denominator != 1 else int(bpm)
        plan["meter"] = meter
        if lead:
            plan["lead"] = float(lead)
    duration_b = _seconds(data.get("duration"))
    fps = Fraction(str(plan.get("fps", 60)))
    duration_p = Fraction(plan["duration_frames"]) / fps if isinstance(plan.get("duration_frames"), int) else None
    if duration_b and duration_p and abs(duration_b - duration_p) > Fraction(1, 2) / fps:
        notes.append(f"the brief says {float(duration_b):g} s but plan.json lasts {float(duration_p):g} s: "
                     f"recreate the piece with --duration {float(duration_b):g} or fix the brief")
    if bpm and duration_p:
        g = grid(bpm, duration_p, meter, lead, int(fps) if fps.denominator == 1 else 60)
        beat_s = g["beat_seconds"]
        existing = [] if replace_hits else [h for h in plan.get("hits") or [] if isinstance(h, dict)]
        # Named hits (a recipe reads them by role) are kept; grid hits fill the beats nobody claimed yet.
        off = [h for h in existing if isinstance(h.get("time"), (int, float))
               and min(abs(h["time"] - b["time"]) for b in g["beats"]) > 1.5 / float(fps)]
        if off:
            notes.append("hits off the grid (more than 1.5 frames from a beat): "
                         + ", ".join(f"{h.get('role', '?')} @ {h['time']:g} s" for h in off[:6])
                         + "; move them onto a beat or say why they are off it")
        if hits != "none":
            taken = [h["time"] for h in existing if isinstance(h.get("time"), (int, float))]
            chosen = [b for b in g["beats"] if (hits == "beat" or b["downbeat"])
                      and all(abs(b["time"] - t) > beat_s * 0.25 for t in taken)]
            added = [{"time": b["time"], "amplitude": 0.8 if b["downbeat"] else 0.4,
                      "role": f"bar {b['bar']}" + ("" if b["downbeat"] else f" beat {b['beat']}")} for b in chosen]
            plan["hits"] = sorted(existing + added, key=lambda h: h.get("time", 0))
            notes.append(f"added {len(added)} grid hits ({hits}) beside {len(existing)} existing; rename each "
                         "'bar N' role to what happens on screen")
    return plan, notes


# ---------------------------------------------------------------------------------------------------------------

def main() -> int:
    _stdout_utf8()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list the brief templates and their variables")
    p_new = sub.add_parser("new", help="write a brief from a template")
    p_new.add_argument("destination", type=Path)
    p_new.add_argument("--template", required=True)
    p_new.add_argument("--set", action="append", default=[], metavar="NAME=VALUE")
    p_check = sub.add_parser("check", help="check a brief's decisions and tempo arithmetic")
    p_check.add_argument("brief", type=Path)
    p_grid = sub.add_parser("grid", help="print the beat grid")
    p_grid.add_argument("--bpm", type=str, required=True)
    p_grid.add_argument("--duration", type=str, required=True, help="seconds")
    p_grid.add_argument("--meter", type=int, default=4)
    p_grid.add_argument("--lead", type=str, default="0", help="time of beat 0 in seconds")
    p_grid.add_argument("--fps", type=int, default=60)
    p_grid.add_argument("--json", action="store_true")
    p_plan = sub.add_parser("plan", help="copy the brief's decisions (and grid hits) into plan.json")
    p_plan.add_argument("brief", type=Path)
    p_plan.add_argument("--plan", type=Path, required=True)
    p_plan.add_argument("--hits", choices=("bar", "beat", "none"), default="bar")
    p_plan.add_argument("--replace-hits", action="store_true", help="drop the existing hits first (a recipe then falls back to its own times)")
    args = parser.parse_args()

    if args.command == "list":
        found = templates()
        for name, path in found.items():
            text = path.read_text(encoding="utf-8")
            first = next((l.strip("# ").strip() for l in text.splitlines() if l.startswith("# ")), name)
            variables = ", ".join(f"{n}={d}" if d is not None else n for n, d in template_variables(text))
            print(f"{name:12} {first}\n{'':12} variables: {variables}")
        return 0 if found else 1

    if args.command == "new":
        found = templates()
        if args.template not in found:
            print(f"Unknown template {args.template!r}; available: {', '.join(found)}", file=sys.stderr)
            return 2
        values = {}
        for item in args.set:
            if "=" not in item:
                print(f"--set needs NAME=VALUE, got {item!r}", file=sys.stderr)
                return 2
            name, value = item.split("=", 1)
            values[name.strip()] = value
        dest = args.destination
        if dest.exists():
            print(f"Refusing to overwrite {dest}", file=sys.stderr)
            return 2
        try:
            dest.resolve().relative_to(SKILL)
            print("Write briefs in the project, not inside the skill (the next install replaces it)", file=sys.stderr)
            return 2
        except ValueError:
            pass
        text = fill(found[args.template].read_text(encoding="utf-8"), values)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        report = check(text)
        print(json.dumps({"written": str(dest), "template": args.template, "errors": report["errors"],
                          "warnings": report["warnings"]}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "check":
        try:
            text = args.brief.read_text(encoding="utf-8-sig")
        except OSError as error:
            print(json.dumps({"errors": [str(error)]}), file=sys.stderr)
            return 2
        report = check(text)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(bool(report["errors"]))

    if args.command == "grid":
        bpm, duration, lead = _number(args.bpm), _seconds(args.duration), _seconds(args.lead) or Fraction(0)
        if not bpm or not 0 < bpm <= 400 or not duration or duration <= 0 or not 1 <= args.meter <= 16:
            print("Need --bpm in (0, 400], --duration > 0 and --meter in 1..16", file=sys.stderr)
            return 2
        g = grid(bpm, duration, args.meter, lead, args.fps)
        print(json.dumps(g, indent=2) if args.json else _grid_table(g))
        return 0

    if args.command == "plan":
        try:
            text = args.brief.read_text(encoding="utf-8-sig")
            plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            print(json.dumps({"errors": [str(error)]}), file=sys.stderr)
            return 2
        if not isinstance(plan, dict):
            print(json.dumps({"errors": ["plan must be an object"]}), file=sys.stderr)
            return 2
        plan, notes = to_plan(text, plan, hits=args.hits, replace_hits=args.replace_hits)
        args.plan.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from validate_plan import validate   # noqa: E402  (same folder; python -I drops it from sys.path)
        errors = validate(plan)
        print(json.dumps({"plan": str(args.plan), "notes": notes, "errors": errors}, ensure_ascii=False, indent=2))
        return int(bool(errors))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
