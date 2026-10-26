"""Plan and cues in, stereo buffer out: hits become impacts on their exact times, cues place any voice, layers and the room.

plan.json   {"duration": 12.0, "hits": [{"time": 1.7, "amplitude": 1.0, "role": "boom"}, [2.4, 0.8]]}
            hits may also be bare numbers or [time, amplitude] pairs (the shape MotionMath.impulse accepts).
cues.json   {"role_voices": {"impact": "hit"},          optional: role → voice for hits
             "highpass_hz": 35,                          optional: 0 switches the high-pass off
             "cues": [
               {"time": 0.62, "voice": "riser", "end": 1.70, "gain": 0.2},
               {"time": 1.28, "voice": "whoosh", "duration": 0.44, "pan_from": 0.75, "pan_to": -0.85},
               {"voice": "bed", "levels": [[0, 0.08], [7, 0.3], [12, 0]]},
               {"voice": "duck", "time": 7.97, "fall": 0.07, "hold": 0.165, "rise": 0.04, "depth": 0.94},
               {"voice": "room", "seconds": 2.3, "decay": 0.48, "wet": 0.55},
               {"voice": "music", "file": "assets/bed.wav", "gain_db": -6, "start_bar": 0, "bpm": 90, "duck_db": -8}
             ]}
"music" puts a recorded bed under the score (sfx/music.py): aligned to the bar, looped, faded, ducked on each hit.
"voiceover" puts a recorded voice on top (sfx/voiceover.py): dry, and everything else ducked under its envelope.
{"voice": "voiceover", "file": "assets/voice.wav", "time": 0, "gain_db": 0, "duck_db": -12}
Hits whose role starts with "emphasis" (scripts/voice_plan.py writes them) use the soft "tap", not an impact.
Every voice parameter is checked against the voice's signature: an unknown name is an error, never silently ignored.
"""
from __future__ import annotations

import inspect
import math
from pathlib import Path

import numpy as np

from .core import SR, Score
from .master import duck_envelope, high_pass, room
from .music import bed_from_file
from .voiceover import duck_under, voice_layer, voice_over_bed
from .voices import LAYERS, VOICES, bed

DEFAULT_ROLE_VOICES = {"hit": "hit", "impact": "hit", "stamp": "hit", "boom": "boom", "glass": "glass", "slap": "slap",
                       "paper": "slap", "heartbeat": "heartbeat", "emphasis": "tap", "tap": "tap"}
DUCK_DEFAULTS = {"fall": .07, "hold": .165, "rise": .04, "depth": .94}
FADE_IN_S, FADE_OUT_S = .012, .5


def normalize_hits(hits) -> list[dict]:
    """Hits as {time, amplitude, role}, sorted by time. Accepts dicts, [time, amplitude] pairs and bare times."""
    out = []
    for index, hit in enumerate(hits or []):
        if isinstance(hit, dict):
            time, amplitude, role = hit.get("time"), hit.get("amplitude", 1.0), hit.get("role", "hit")
        elif isinstance(hit, (list, tuple)) and hit:
            time, amplitude, role = hit[0], (hit[1] if len(hit) > 1 else 1.0), "hit"
        else:
            time, amplitude, role = hit, 1.0, "hit"
        if isinstance(time, bool) or not isinstance(time, (int, float)) or not math.isfinite(time) or time < 0:
            raise ValueError(f"plan.json hits[{index}]: needs a time in seconds, got {hit!r}")
        if isinstance(amplitude, bool) or not isinstance(amplitude, (int, float)) or not 0 < amplitude <= 2:
            raise ValueError(f"plan.json hits[{index}]: amplitude must be in (0, 2], got {amplitude!r}")
        out.append({"time": float(time), "amplitude": float(amplitude), "role": str(role)})
    return sorted(out, key=lambda h: h["time"])


def _parameters(fn, skip: int = 2) -> dict:
    """Parameter name → inspect.Parameter after the first `skip` ones: (score, at) for voices, (score) for layers."""
    return dict(list(inspect.signature(fn).parameters.items())[skip:])


def _check_params(name: str, fn, params: dict, skip: int = 2) -> None:
    allowed = _parameters(fn, skip)
    unknown = sorted(set(params) - set(allowed))
    if unknown:
        raise ValueError(f"voice {name}: unknown parameter(s) {unknown}; allowed: {sorted(allowed)}")
    missing = sorted(k for k, p in allowed.items() if p.default is inspect.Parameter.empty and k not in params)
    if missing:
        raise ValueError(f"voice {name}: missing required parameter(s) {missing}")


def _number(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number, got {value!r}")
    return float(value)


def plan_duration(plan: dict, cues: dict | None = None) -> float:
    """Seconds: plan["duration"], else duration_frames / fps (fps may be a rational string such as "30000/1001"),
    else cues["duration"]."""
    if plan.get("duration") is not None:
        return _number(plan["duration"], "plan.json duration")
    frames, fps = plan.get("duration_frames"), plan.get("fps")
    if frames is not None and fps is not None:
        if isinstance(fps, str) and "/" in fps:
            num, den = fps.split("/", 1)
            fps = float(num) / float(den)
        return _number(frames, "plan.json duration_frames") / _number(fps, "plan.json fps")
    return _number((cues or {}).get("duration"), "plan.json duration (or duration_frames and fps)")


def render(plan: dict, cues: dict | None, seed: int, sr: int = SR, base: Path | None = None):
    """Render the score. Returns (master, report): master is float64 (samples, 2) before the loudness search, with
    fades applied; report lists every hit and cue as it was placed (for the audit). base: the folder that relative
    music files are read from (build_soundtrack.py passes the cues file's folder)."""
    cues = cues or {}
    duration = plan_duration(plan, cues)
    if not duration > 0:
        raise ValueError("plan.json duration must be positive")
    score = Score(duration, seed, sr)
    role_voices = {**DEFAULT_ROLE_VOICES, **(cues.get("role_voices") or {})}
    for role, name in role_voices.items():
        if name not in VOICES:
            raise ValueError(f"role_voices[{role!r}]: unknown voice {name!r}; known: {sorted(VOICES)}")
    report = {"duration_s": duration, "seed": seed, "hits": [], "cues": [], "layers": {}}

    # Layers that cover the whole score go first: the bed draws its rumble from the generator.
    entries = list(cues.get("cues") or [])
    for entry in entries:
        if entry.get("voice") == "bed":
            params = {k: v for k, v in entry.items() if k not in ("voice", "time")}
            _check_params("bed", bed, params, skip=1)
            bed(score, **params)
            report["layers"].setdefault("bed", []).append(params)

    # Hits: each one is an impact on its exact time, scaled by its amplitude.
    for hit in normalize_hits(plan.get("hits")):
        # "emphasis: word" uses the "emphasis" voice: the part before a colon names the family.
        name = role_voices.get(hit["role"]) or role_voices.get(hit["role"].split(":")[0].strip(), "hit")
        fn = VOICES[name]
        if any(p.default is inspect.Parameter.empty for p in _parameters(fn).values()):
            raise ValueError(f"role {hit['role']!r} maps to {name}, which needs parameters: use a cue for it")
        gain = inspect.signature(fn).parameters["gain"].default * hit["amplitude"]
        fn(score, hit["time"], gain=gain)
        report["hits"].append({"time": hit["time"], "role": hit["role"], "voice": name, "gain": round(gain, 4)})

    # Cues in list order: any voice, with its parameters checked against its signature.
    duck_events = []
    room_settings = {"seconds": 2.3, "decay": .48, "wet": .55}
    music = []
    voiceovers = []
    for entry in entries:
        name = entry.get("voice")
        if name == "bed":
            continue
        if name == "voiceover":
            voiceovers.append({k: v for k, v in entry.items() if k != "voice"})
            continue
        if name == "music":
            music.append({k: v for k, v in entry.items() if k != "voice"})
            continue
        if name == "room":
            params = {k: v for k, v in entry.items() if k not in ("voice", "time")}
            allowed = {"seconds", "decay", "wet"}
            if set(params) - allowed:
                raise ValueError(f"room: unknown parameter(s) {sorted(set(params) - allowed)}; allowed: {sorted(allowed)}")
            room_settings.update(params)
            continue
        if name == "duck":
            event = {"at": _number(entry.get("time"), "duck time"), **DUCK_DEFAULTS}
            for key in DUCK_DEFAULTS:
                if key in entry:
                    event[key] = _number(entry[key], f"duck {key}")
            if set(entry) - {"voice", "time", *DUCK_DEFAULTS}:
                raise ValueError(f"duck: unknown parameter(s) {sorted(set(entry) - {'voice', 'time', *DUCK_DEFAULTS})}")
            duck_events.append(event)
            report["layers"].setdefault("duck", []).append(event)
            continue
        if name not in VOICES:
            raise ValueError(f"cue voice {name!r} is unknown; known: {sorted(VOICES) + list(LAYERS)}")
        at = _number(entry.get("time"), f"cue {name} time")
        if not 0 <= at < duration:
            raise ValueError(f"cue {name} at {at} s is outside the piece (0 to {duration} s)")
        params = {k: v for k, v in entry.items() if k not in ("voice", "time")}
        fn = VOICES[name]
        if "end" in params:
            end = _number(params.pop("end"), f"cue {name} end")
            if "duration" in _parameters(fn) and "duration" not in params:
                params["duration"] = end - at
        _check_params(name, fn, params)
        fn(score, at, **params)
        report["cues"].append({"time": at, "voice": name, "params": params})

    master = score.dry + room(score, **room_settings)
    report["layers"]["room"] = room_settings
    for params in music:   # after the room: a recorded bed keeps its own space
        layer, info = bed_from_file(params, duration, sr, normalize_hits(plan.get("hits")), base)
        master = master + layer[: len(master)]
        report["layers"].setdefault("music", []).append(info)
    if duck_events:
        master = master * duck_envelope(score.samples, sr, duck_events)[:, None]
    for params in voiceovers:   # last: the voice stays dry and on top; everything under it dips while it speaks
        voice, env, info = voice_layer(params, duration, sr, base)
        master = duck_under(master, env, info["duck_db"])
        info["voice_over_bed_db"] = voice_over_bed(voice, master, env)
        master = master + voice[: len(master)]
        report["layers"].setdefault("voiceover", []).append(info)
    highpass = _number(cues.get("highpass_hz", 35), "highpass_hz")
    master = high_pass(master, sr, highpass)
    report["highpass_hz"] = highpass
    master = master - np.mean(master, axis=0)
    time = np.arange(score.samples) / sr
    master = master * np.minimum(1, time / FADE_IN_S)[:, None]
    end_fade = np.sin(np.pi / 2 * np.clip((duration - time) / FADE_OUT_S, 0, 1)) ** 2
    end_fade[-1] = 0
    return master * end_fade[:, None], report
