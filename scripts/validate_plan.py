"""Validate the frame-based edit plan. This checks structure, never artistic quality."""
from __future__ import annotations

import sys
import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import re


def _description(container: dict, key: str, prefix: str, errors: list[str]) -> None:
    """Require an explanation, allowing an explicit omission with its reason."""
    value = container.get(key)
    location = f"{prefix}.{key}"
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{location} must be a nonempty description")
    elif re.match(r"^none\b", value.strip(), re.IGNORECASE):
        if not re.match(r"^none\s*[,;:\u2013\u2014-]\s*\S", value.strip(), re.IGNORECASE):
            errors.append(f"{location} needs a reason after 'none, '")


def _time(value: object, prefix: str, duration: Fraction | None, errors: list[str]) -> None:
    # JSON booleans are not numeric times. Decimal text avoids float boundary drift
    # when comparing a value such as 0.3 with an exact rational frame duration.
    if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
        errors.append(f"{prefix} must be a finite numeric time in seconds")
    elif value < 0 or (duration is not None and Fraction(str(value)) > duration):
        errors.append(f"{prefix} must be within the plan duration in seconds (0 <= time <= duration)")


def _craft(plan: dict, duration: Fraction | None, errors: list[str]) -> None:
    """Check declared craft evidence only; this cannot judge its artistic merit."""
    references = plan.get("reference_evidence")
    if not isinstance(references, list) or not references:
        errors.append("reference_evidence must be a nonempty list when --require-craft is used")
    else:
        for index, reference in enumerate(references):
            prefix = f"reference_evidence[{index}]"
            if not isinstance(reference, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for key in ("source", "observed_operation", "own_application"):
                _description(reference, key, prefix, errors)
            times = reference.get("proof_times")
            if not isinstance(times, list) or not times:
                errors.append(f"{prefix}.proof_times must be a nonempty list of times in plan seconds")
            else:
                for time_index, value in enumerate(times):
                    _time(value, f"{prefix}.proof_times[{time_index}]", duration, errors)

    styles = plan.get("style_sequence")
    if not isinstance(styles, list) or not styles:
        errors.append("style_sequence must be a nonempty list when --require-craft is used")
    else:
        for index, style in enumerate(styles):
            prefix = f"style_sequence[{index}]"
            if not isinstance(style, dict):
                errors.append(f"{prefix} must be an object")
                continue
            _time(style.get("time"), f"{prefix}.time", duration, errors)
            _description(style, "composition", prefix, errors)

    scenes = plan.get("scenes")
    if not isinstance(scenes, list):
        return  # The base schema reports invalid or missing scenes.
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        for section, keys in (
            ("motion", ("preparation", "action", "follow_through", "reading")),
            ("blur_plan", ("motion", "focus", "text_resolution")),
        ):
            prefix = f"scene[{index}].{section}"
            value = scene.get(section)
            if not isinstance(value, dict):
                errors.append(f"{prefix} must be an object when --require-craft is used")
                continue
            for key in keys:
                _description(value, key, prefix, errors)


def _timed_lists(plan: dict, duration: Fraction | None, errors: list[str]) -> None:
    """Optional shared timing: hits drive both the image (punch, shake, flash) and the sound."""
    hits = plan.get("hits")
    if hits is not None:
        if not isinstance(hits, list) or not hits:
            errors.append("hits must be a nonempty list when present")
        else:
            previous = None
            for index, hit in enumerate(hits):
                prefix = f"hits[{index}]"
                if not isinstance(hit, dict):
                    errors.append(f"{prefix} must be an object with time, amplitude and role")
                    continue
                _time(hit.get("time"), f"{prefix}.time", duration, errors)
                amplitude = hit.get("amplitude")
                if type(amplitude) not in (int, float) or not 0 < amplitude <= 2:
                    errors.append(f"{prefix}.amplitude must be a number in (0, 2]")
                if not isinstance(hit.get("role"), str) or not hit["role"].strip():
                    errors.append(f"{prefix}.role must say what the hit marks")
                time = hit.get("time")
                if type(time) in (int, float) and previous is not None and time < previous:
                    errors.append(f"{prefix} is out of chronological order")
                if type(time) in (int, float):
                    previous = time
    cues = plan.get("sound_cues")
    if cues is not None:
        if not isinstance(cues, list):
            errors.append("sound_cues must be a list when present")
        else:
            for index, cue in enumerate(cues):
                if not isinstance(cue, dict):
                    errors.append(f"sound_cues[{index}] must be an object")
                    continue
                _time(cue.get("time"), f"sound_cues[{index}].time", duration, errors)
    # Edit fields the guides use (references/produce/plan-schema.md §1b): a music grid, cut points and captions.
    bpm = plan.get("bpm")
    if bpm is not None and (type(bpm) not in (int, float) or not 0 < bpm <= 400):
        errors.append("bpm must be a number in (0, 400] when present")
    if plan.get("lead") is not None:
        _time(plan.get("lead"), "lead", duration, errors)
        if bpm is None:
            errors.append("lead needs bpm: it is the time of beat 0")
    cuts = plan.get("cuts")
    if cuts is not None:
        if not isinstance(cuts, list) or not cuts:
            errors.append("cuts must be a nonempty list of times in seconds when present")
        else:
            for index, cut in enumerate(cuts):
                _time(cut, f"cuts[{index}]", duration, errors)
            if all(type(c) in (int, float) for c in cuts) and any(b <= a for a, b in zip(cuts, cuts[1:])):
                errors.append("cuts must be strictly increasing")
    captions = plan.get("captions")
    if captions is not None and not (isinstance(captions, str) and captions.strip()):
        if not isinstance(captions, list) or not captions:
            errors.append("captions must be a path to captions.json (scripts/captions.py) or a nonempty list of lines")
        else:
            previous = None
            for index, line in enumerate(captions):
                prefix = f"captions[{index}]"
                if not isinstance(line, dict) or not isinstance(line.get("text"), str) or not line["text"].strip():
                    errors.append(f"{prefix} needs nonempty text, start and end")
                    continue
                _time(line.get("start"), f"{prefix}.start", duration, errors)
                _time(line.get("end"), f"{prefix}.end", duration, errors)
                start, end = line.get("start"), line.get("end")
                if type(start) in (int, float) and type(end) in (int, float):
                    if end <= start:
                        errors.append(f"{prefix} ends before it starts")
                    if previous is not None and start < previous:
                        errors.append(f"{prefix} overlaps the previous line")
                    previous = end


def _brief_fields(plan: dict, errors: list[str], *, require: bool) -> None:
    """Decisions copied from the motion brief (scripts/brief.py plan; references/create/motion-brief.md)."""
    for key in ("concept", "recurring_element", "audience"):
        value = plan.get(key)
        if value is not None and (not isinstance(value, str) or not value.strip()):
            errors.append(f"{key} must be a nonempty string when present")
    banned = plan.get("banned")
    if banned is not None:
        if not isinstance(banned, list):
            errors.append("banned must be a list of {avoid, instead}")
        else:
            for index, item in enumerate(banned):
                if not isinstance(item, dict) or not isinstance(item.get("avoid"), str) or not item["avoid"].strip():
                    errors.append(f"banned[{index}] needs a nonempty avoid (and an instead)")
                elif not isinstance(item.get("instead", ""), str):
                    errors.append(f"banned[{index}].instead must be a string")
    meter = plan.get("meter")
    if meter is not None and (type(meter) is not int or not 1 <= meter <= 16):
        errors.append("meter must be an integer number of beats per bar in 1..16")
    if meter is not None and plan.get("bpm") is None:
        errors.append("meter needs bpm")
    if plan.get("loop") is not None and type(plan.get("loop")) is not bool:
        errors.append("loop must be true or false (true: the last frame matches the first; check with loop_check.py)")
    if require:
        if not isinstance(plan.get("concept"), str) or not plan["concept"].strip():
            errors.append("concept is required with --require-brief: the one idea in one line")
        if not isinstance(banned, list) or len(banned) < 3:
            errors.append("banned needs at least 3 {avoid, instead} items with --require-brief")
        if type(plan.get("loop")) is not bool:
            errors.append("loop (true or false) is required with --require-brief")


def validate(plan: object, *, require_craft: bool = False, require_brief: bool = False) -> list[str]:
    errors = []
    if not isinstance(plan, dict):
        return ["plan must be an object"]
    if type(plan.get("schema_version")) is not int or plan["schema_version"] != 1:
        errors.append("schema_version must be 1")
    for key in ("width", "height", "duration_frames"):
        value = plan.get(key)
        if type(value) is not int or value <= 0:
            errors.append(f"{key} must be a positive integer")
    for key in ("width", "height"):
        value = plan.get(key)
        if type(value) is int and value % 2:
            errors.append(f"{key} must be even for the default yuv420p delivery")
    fps = None
    try:
        candidate = Fraction(str(plan.get("fps", 0)))
        if isinstance(plan.get("fps"), bool) or candidate <= 0:
            raise ValueError()
        fps = candidate
    except (ValueError, ZeroDivisionError):
        errors.append("fps must be a positive number or rational string")
    if not isinstance(plan.get("mode"), str) or plan["mode"] not in {"editorial", "kinetic", "diagram", "glow", "retro"}:
        errors.append("mode must be editorial, kinetic, diagram, glow or retro")
    if "format" in plan and plan["format"] not in {"reel", "story", "insert", "overlay"}:
        errors.append("format must be reel, story, insert or overlay when present")
    if not isinstance(plan.get("audio"), str) or plan["audio"] not in {"required", "optional", "forbidden"}:
        errors.append("audio must be required, optional or forbidden")
    safe = plan.get("safe_area")
    if not isinstance(safe, dict):
        errors.append("safe_area must be an object")
    elif any(type(safe.get(key)) is not int for key in ("x", "y", "width", "height")):
        errors.append("safe_area needs integer x, y, width and height")
    elif safe["x"] < 0 or safe["y"] < 0 or safe["width"] <= 0 or safe["height"] <= 0:
        errors.append("safe_area has invalid coordinates or dimensions")
    elif (type(plan.get("width")) is int and type(plan.get("height")) is int
          and (safe["x"] + safe["width"] > plan["width"] or safe["y"] + safe["height"] > plan["height"])):
        errors.append("safe_area extends outside the frame")
    frames = plan.get("duration_frames")
    duration = Fraction(frames, 1) / fps if type(frames) is int and frames > 0 and fps is not None else None
    _timed_lists(plan, duration, errors)
    _brief_fields(plan, errors, require=require_brief)
    if require_craft:
        _craft(plan, duration, errors)
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return errors + ["scenes must be a nonempty list"]
    cursor, ids = 0, set()
    allowed_transitions = {"cut", "match-cut", "morph", "mask", "wipe", "camera", "fade", "end"}
    for index, scene in enumerate(scenes):
        prefix = f"scene[{index}]"
        if not isinstance(scene, dict):
            errors.append(f"{prefix} must be an object")
            continue
        ident = scene.get("id")
        if not isinstance(ident, str) or not ident.strip():
            errors.append(f"{prefix} needs a nonempty id")
        elif ident in ids:
            errors.append(f"{prefix} duplicate id: {ident}")
        else:
            ids.add(ident)
        start, end = scene.get("start_frame"), scene.get("end_frame")
        if type(start) is not int or type(end) is not int or start < 0 or end <= start:
            errors.append(f"{prefix} has invalid frame interval")
        else:
            if start != cursor:
                errors.append(f"{prefix} {'gap' if start > cursor else 'overlap'} at frame {cursor}")
            cursor = end
        for key in ("intent", "action"):
            if not isinstance(scene.get(key), str) or not scene[key].strip():
                errors.append(f"{prefix} needs nonempty {key}")
        if not isinstance(scene.get("text"), str):
            errors.append(f"{prefix}.text must be a string (empty is allowed)")
        transition = scene.get("transition")
        if (not isinstance(transition, dict) or not isinstance(transition.get("kind"), str)
                or transition["kind"] not in allowed_transitions):
            errors.append(f"{prefix} needs a valid transition.kind")
        else:
            kind = transition["kind"]
            if kind in {"morph", "mask", "match-cut", "camera", "wipe"}:
                carrier = transition.get("carrier")
                if not isinstance(carrier, str) or not carrier.strip():
                    errors.append(f"{prefix} transition needs a carrier")
            if kind == "end" and index != len(scenes) - 1:
                errors.append(f"{prefix} uses end before last scene")
    if cursor != plan.get("duration_frames"):
        errors.append(f"scene coverage ends at {cursor}, not duration_frames={plan.get('duration_frames')}")
    return errors


def main() -> int:
    for stream in (sys.stdout, sys.stderr):   # cp1252 consoles under python -I
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--require-craft", action="store_true",
                        help="require reference, composition, motion and blur evidence structure; never certify artistic quality")
    parser.add_argument("--require-brief", action="store_true",
                        help="require the brief's decisions in the plan: concept, a banned list and loop (scripts/brief.py plan)")
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
        errors = validate(plan, require_craft=args.require_craft, require_brief=args.require_brief)
    except (OSError, ValueError) as error:
        errors = [str(error)]
    print(json.dumps({"errors": errors, "artistic_quality_checked": False}, ensure_ascii=False, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
