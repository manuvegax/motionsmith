"""The voice is the clock: turn a voice over and its word timings into the piece's plan.

  python -I <skill>/scripts/voice_plan.py --plan work/piece/plan.json --voice work/piece/assets/voice.wav \\
      [--words voice-words.json] [--script script.md] [--brief brief.md] [--voice-start 0.1] [--tail 0.8]
      [--preset reel] [--max-scene 3.5] [--min-scene 0.8] [--lead-frames 2] [--dry-run]

Word timings (--words) come from any speech-to-text that gives them: ElevenLabs speech-to-text JSON ("words" with
start/end), Whisper JSON ("segments" with "words"), a plain list of {text, start, end}, WebVTT with inline word times,
or SRT (word times then estimated inside each cue). Without --words, --script is aligned to the voice by its pauses
(marked "estimated": good for a draft, not for karaoke).

It writes, next to the plan:
  plan.json     duration from the voice; one scene per phrase (cut on the pause before it, the picture leading the
                sound by --lead-frames); cuts; emphasis hits on the stressed words; captions; audio required
  voice.json    every word, phrase and pause with its time in the piece, for piece.js to read
  captions.json lines for kinetic captions (scripts/captions.py rules: line length and reading speed)
  cues.json     the "voiceover" cue for build_soundtrack.py (the voice on top, the rest ducked under it)

Emphasis: one accent per phrase, at least 1 s apart. It starts on the last content word (where a neutral sentence
puts its main stress); a word louder or longer than the phrase, or before a pause, can take it over; a word marked
in the script with *asterisks* or CAPITALS always wins. Function words never take it unless marked. With --brief, each scene takes its screen action from the brief's two-column table (voice | screen).
It measures timing and level; it does not hear meaning: read the emphasis list and move what is wrong.
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python -I drops the script's folder
import captions as caps  # noqa: E402
from validate_plan import validate  # noqa: E402

SR = 16000
STOPWORDS = set("""
a al algo ante como con contra cual cuando de del desde donde e el ella ellas ellos en entre era es esa ese eso esta
este esto fue ha hay la las le les lo los me mi mis muy nos o os para pero por que quien se sea si sin sobre su sus
te ti tu tus un una uno unos unas y ya yo él tú ni pues tan
the a an and or but if of to in on at by for with from as is are was were be been it its this that these those
i you he she we they me him her us them my your his our their not no so do does did have has had will would can
""".split())
SENTENCE_END = re.compile(r"[.!?…:;]+[\"»”')\]]*$")
SOFT_END = re.compile(r"[,—–]+[\"»”')\]]*$")


def norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if c.isalnum() and unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------------------------------------------
# Inputs

def load_words(path: Path) -> list[caps.Word]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        raw = None
        if isinstance(data, dict) and isinstance(data.get("words"), list):
            raw = data["words"]                                   # ElevenLabs speech-to-text
        elif isinstance(data, dict) and isinstance(data.get("segments"), list) and any(
                isinstance(s, dict) and s.get("words") for s in data["segments"]):
            raw = [w for s in data["segments"] for w in s.get("words") or []]   # Whisper
        elif isinstance(data, list) and data and isinstance(data[0], dict) and "start" in data[0] and not data[0].get("words"):
            raw = data
        if raw is not None:
            items = []
            for w in raw:
                if not isinstance(w, dict) or w.get("type", "word") != "word":
                    continue
                text = caps.clean(str(w.get("text", w.get("word", ""))))
                if text and w.get("start") is not None:
                    items.append((text, float(w["start"]), None if w.get("end") is None else float(w["end"])))
            items.sort(key=lambda item: item[1])
            # Engines that only give word onsets (Windows SAPI, some aligners): a word ends where the next begins.
            words = [caps.Word(text, start, end if end is not None else
                               (items[k + 1][1] - .02 if k + 1 < len(items) else start + .09 * len(text) + .15), source=True)
                     for k, (text, start, end) in enumerate(items)]
            if words:
                return words
    fmt = caps.detect_format(path, "auto")
    return [w for cue in caps.load(path, fmt) for w in caps.cue_words(cue)]


def decode(path: Path) -> np.ndarray:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("FFmpeg must be on PATH to read the voice")
    out = subprocess.run([ffmpeg, "-v", "error", "-nostdin", "-i", str(path), "-map", "0:a:0", "-ac", "1", "-ar", str(SR),
                          "-f", "f32le", "-"], capture_output=True)
    if out.returncode or not out.stdout:
        raise ValueError(f"cannot decode {path}: {out.stderr.decode('utf-8', 'replace')[-300:]}")
    return np.frombuffer(out.stdout, np.float32).astype(np.float64)


def level_db(audio: np.ndarray, window: float = .02) -> np.ndarray:
    hop = int(SR * window)
    frames = len(audio) // hop
    if frames == 0:
        return np.array([-90.0])
    rms = np.sqrt(np.mean(audio[: frames * hop].reshape(frames, hop) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms)


def audible_threshold(db: np.ndarray) -> float:
    return max(float(np.percentile(db, 95)) - 32, float(np.percentile(db, 10)) + 8)


def tighten(words: list[caps.Word], db: np.ndarray, window: float = .02) -> list[caps.Word]:
    """End each word where it stops being audible (plus 30 ms), never before 50 ms after its start. Word ends taken
    from the next onset (or padded by a speech-to-text) hide the pauses; this brings them back."""
    threshold = audible_threshold(db)
    out = []
    for w in words:
        a, b = int(w.start / window), int(math.ceil(w.end / window))
        seg = db[a:b]
        loud = np.nonzero(seg > threshold)[0]
        end = (a + loud[-1] + 1) * window + .03 if len(loud) else w.end
        out.append(caps.Word(w.text, w.start, max(w.start + .05, min(w.end, end)), w.source))
    return out


def speech_regions(db: np.ndarray, window: float = .02, min_gap: float = .18) -> list[tuple[float, float]]:
    on = db > audible_threshold(db)
    regions, start = [], None
    for i, flag in enumerate(on):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            regions.append([start * window, i * window])
            start = None
    if start is not None:
        regions.append([start * window, len(on) * window])
    merged = []
    for r in regions:
        if merged and r[0] - merged[-1][1] < min_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(a, b) for a, b in merged if b - a > .06]


def script_tokens(text: str) -> list[dict]:
    """Words of a script with their marks: *word* or CAPITALS = forced emphasis. Markdown tables keep only the
    first column (the voice); headings, list bullets and tags are dropped."""
    voice_lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("<") or re.match(r"^\|?\s*:?-{3,}", s):
            continue
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and norm(cells[0]) in {"voz", "voice", "vo", "loquese oye", "loqueseoye", "audio"}:
                continue
            s = cells[0] if cells else ""
        s = re.sub(r"^[-*•]\s+", "", s)
        voice_lines.append(s)
    tokens = []
    for raw in " ".join(voice_lines).split():
        bare = raw.strip("*_")
        forced = (raw.startswith("*") and raw.rstrip(".,;:!?…»”\"'").endswith("*")) or (
            len(norm(bare)) > 1 and bare.isupper())
        text = bare.replace("*", "")
        if norm(text):
            tokens.append({"text": text, "norm": norm(text), "forced": forced})
    return tokens


def _spread(tokens: list[dict], regions: list[tuple[float, float]]) -> list[caps.Word]:
    """Spread tokens over the speech inside regions by character weight (pauses removed)."""
    speech = sum(b - a for a, b in regions)
    weights = [len(t["text"]) + 1.5 for t in tokens]
    total = sum(weights) or 1

    def at(fraction: float) -> float:
        target, acc = fraction * speech, 0.0
        for a, b in regions:
            if acc + (b - a) >= target - 1e-9:
                return a + (target - acc)
            acc += b - a
        return regions[-1][1]

    words, cursor = [], 0.0
    for token, weight in zip(tokens, weights):
        start, end = at(cursor / total), at((cursor + weight) / total)
        cursor += weight
        words.append(caps.Word(token["text"], start, max(end, start + .05), source=False))
    return words


def align_script(tokens: list[dict], regions: list[tuple[float, float]], min_pause: float = .3) -> list[caps.Word]:
    """Estimated word times from the script and the voice's pauses: each sentence end snaps to the nearest long pause
    (at most 1.5 s from where the characters put it), then words spread by character weight inside each sentence."""
    if not tokens or not regions:
        return []
    ends = [k for k, t in enumerate(tokens) if SENTENCE_END.search(t["text"])]
    if not ends or ends[-1] != len(tokens) - 1:
        ends.append(len(tokens) - 1)
    rough = _spread(tokens, regions)
    gaps = [(regions[i][1], regions[i + 1][0]) for i in range(len(regions) - 1) if regions[i + 1][0] - regions[i][1] >= min_pause]
    bounds, used, last = [], set(), regions[0][0]
    for k in ends[:-1]:
        guess = rough[k].end
        options = [(abs(g[0] - guess), i) for i, g in enumerate(gaps) if i not in used and g[0] > last and abs(g[0] - guess) <= 1.5]
        if options:
            _, i = min(options)
            used.add(i)
            bounds.append(gaps[i])
            last = gaps[i][1]
        else:
            bounds.append((guess, guess))
            last = guess
    words, first, start = [], 0, regions[0][0]
    for n, k in enumerate(ends):
        stop = bounds[n][0] if n < len(bounds) else regions[-1][1]
        inside = [(max(a, start), min(b, stop)) for a, b in regions if b > start and a < stop]
        words += _spread(tokens[first:k + 1], inside or [(start, max(stop, start + .1))])
        first = k + 1
        start = bounds[n][1] if n < len(bounds) else stop
    return words


def match_script(words: list[caps.Word], tokens: list[dict]) -> tuple[list[caps.Word], list[bool]]:
    """Match the timed words to the script by sequence: forced-emphasis flags, and the script's punctuation and
    spelling where the speech-to-text dropped them (phrases end on the script's full stops)."""
    flags = [False] * len(words)
    if not tokens:
        return words, flags
    out = list(words)
    a = [norm(w.text) for w in words]
    b = [t["norm"] for t in tokens]
    for block in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            token, i = tokens[block.b + k], block.a + k
            flags[i] = token["forced"]
            out[i] = caps.Word(token["text"], words[i].start, words[i].end, words[i].source)
    return out, flags


def brief_rows(text: str) -> list[dict]:
    """Rows of the two-column table (voice | screen) in a brief or script."""
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or re.match(r"^\|?\s*:?-{3,}", s):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 2 or norm(cells[0]) in {"voz", "voice", "vo", "audio", "loqueseoye"}:
            continue
        if norm(cells[0]):
            rows.append({"voice": cells[0], "screen": cells[1], "norms": [norm(w) for w in cells[0].split() if norm(w)]})
    return rows


# ---------------------------------------------------------------------------------------------------------------
# Analysis

def phrases_of(words: list[caps.Word], long_pause: float, max_scene: float, min_scene: float) -> list[list[int]]:
    groups, current = [], []
    for i, w in enumerate(words):
        current.append(i)
        gap = words[i + 1].start - w.end if i + 1 < len(words) else 0
        if SENTENCE_END.search(w.text) or gap >= long_pause or i + 1 == len(words):
            groups.append(current)
            current = []
    # Split long phrases at the comma or the widest pause nearest the middle.
    out = []
    stack = list(groups)
    while stack:
        g = stack.pop(0)
        span = words[g[-1]].end - words[g[0]].start
        if span <= max_scene or len(g) < 4:
            out.append(g)
            continue
        mid = words[g[0]].start + span / 2
        # Only split where speech allows it: a comma or dash, or a real pause. Never in the middle of a clause.
        places = [k for k in range(1, len(g) - 2)
                  if SOFT_END.search(words[g[k]].text) or words[g[k + 1]].start - words[g[k]].end >= .18]
        if not places:
            out.append(g)
            continue

        def cost(k: int) -> float:
            gap = words[g[k + 1]].start - words[g[k]].end
            soft = 1.0 if SOFT_END.search(words[g[k]].text) else 0.0
            return abs(words[g[k]].end - mid) / span - 2 * gap - .3 * soft

        k = min(places, key=cost)
        stack[:0] = [g[: k + 1], g[k + 1:]]
    # Merge phrases that are too short to read as a scene.
    merged = []
    for g in out:
        if merged and words[merged[-1][-1]].end - words[merged[-1][0]].start < min_scene:
            merged[-1] = merged[-1] + g
        else:
            merged.append(g)
    if len(merged) > 1 and words[merged[-1][-1]].end - words[merged[-1][0]].start < min_scene:
        merged[-2] = merged[-2] + merged.pop()
    return merged


def emphasis(words: list[caps.Word], phrases: list[list[int]], db: np.ndarray, forced: list[bool],
             spacing: float = 1.0) -> list[dict]:
    """One accent per phrase. In a neutral Spanish or English sentence the main stress falls on the last content
    word (the nuclear accent), so that word starts ahead; a word louder or longer than its phrase, or followed by a
    pause, can overtake it; a word marked in the script always wins. Function words never take it unless marked."""
    window = .02

    def loud(w: caps.Word) -> float:
        a = int(w.start / window)
        seg = db[a:max(a + 1, int(math.ceil(w.end / window)))]
        return float(seg.max()) if len(seg) else -90.0

    picks = []
    for g in phrases:
        content = [i for i in g if norm(words[i].text) and (norm(words[i].text) not in STOPWORDS or forced[i])]
        if not content:
            continue
        levels = {i: loud(words[i]) for i in content}
        median = float(np.median(list(levels.values())))
        best, best_score = None, -math.inf
        for i in content:
            w, n = words[i], norm(words[i].text)
            stretch = (w.end - w.start) / (.075 * len(n) + .1) - 1
            gap = words[i + 1].start - w.end if i + 1 < len(words) else .5
            score = (1.0 * (i == content[-1]) + (levels[i] - median) / 4 + .8 * max(-.5, min(stretch, 1.5))
                     + (.5 if gap >= .25 else 0) + (.2 if len(n) >= 6 else 0) + (10 if forced[i] else 0))
            if score > best_score:
                best, best_score = i, score
        picks.append({"index": best, "score": round(float(best_score), 2), "forced": bool(forced[best])})
    picks.sort(key=lambda p: (-p["forced"], -p["score"]))
    chosen = []
    for p in picks:
        if all(abs(words[p["index"]].start - words[c["index"]].start) >= spacing for c in chosen):
            chosen.append(p)
    return sorted(chosen, key=lambda p: p["index"])


# ---------------------------------------------------------------------------------------------------------------

def build(args) -> dict:
    voice_path = args.voice.resolve()
    audio = decode(voice_path)
    db = level_db(audio)
    regions = speech_regions(db)
    tokens = script_tokens(args.script.read_text(encoding="utf-8-sig")) if args.script else []
    notes, warnings = [], []
    if args.words:
        words = load_words(args.words)
        timing = "measured" if all(w.source for w in words) else "estimated"
    elif tokens:
        words = align_script(tokens, regions)
        timing = "estimated"
        warnings.append("word times estimated from the script and the pauses: fine for cuts, too loose for karaoke; "
                        "get word timings from speech-to-text for the final")
    else:
        raise ValueError("need --words (word timings) or --script (the text that was read)")
    if not words:
        raise ValueError("no words found in the timings")
    voice_seconds = len(audio) / SR
    if words[-1].start > voice_seconds + .25:
        raise ValueError(f"the word timings run to {words[-1].start:.2f} s but the voice lasts {voice_seconds:.2f} s: "
                         "a different time base (sample rate, an offset, another take?). Re-export the timings from "
                         "this exact file")
    inside = sum(any(a - .12 <= w.start <= b for a, b in regions) for w in words) / len(words)
    if inside < .8:
        warnings.append(f"only {inside:.0%} of the word onsets fall where the voice is audible: the timings may "
                        "belong to another take or be offset")
    words, forced = match_script(words, tokens)
    words = tighten(words, db)
    phrases = phrases_of(words, args.long_pause, args.max_scene, args.min_scene)
    accents = emphasis(words, phrases, db, forced)

    plan_path = args.plan
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    fps_raw = plan.get("fps", 60)
    num, _, den = str(fps_raw).partition("/")
    fps = float(num) / float(den or 1)
    off = args.voice_start
    last = max(words[-1].end, voice_seconds if args.keep_voice_tail else words[-1].end)
    duration_frames = int(math.ceil((off + last + args.tail) * fps))
    plan["duration_frames"] = duration_frames
    plan["audio"] = "required"

    # Cuts: the picture changes just before the first word of each phrase (the eye leads the ear).
    starts = [0]
    for g in phrases[1:]:
        t = off + words[g[0]].start - args.lead_frames / fps
        frame = max(starts[-1] + 1, int(round(t * fps)))
        starts.append(frame)
    rows = brief_rows(args.brief.read_text(encoding="utf-8-sig")) if args.brief else []
    row_of = {}
    if rows:
        flat = [(r, n) for r, row in enumerate(rows) for n in row["norms"]]
        a = [norm(w.text) for w in words]
        b = [n for _, n in flat]
        for block in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
            for k in range(block.size):
                row_of[block.a + k] = flat[block.b + k][0]
    scenes = []
    for s, g in enumerate(phrases):
        text = " ".join(words[i].text for i in g)
        votes = [row_of[i] for i in g if i in row_of]
        screen = rows[max(set(votes), key=votes.count)]["screen"] if votes else ""
        end = starts[s + 1] if s + 1 < len(phrases) else duration_frames
        scenes.append({"id": f"s{s + 1:02d}", "start_frame": starts[s], "end_frame": end,
                       "intent": f"Say: {text}",
                       "action": screen or "Decide what the screen does while this is said (brief: voice | screen)",
                       "text": text, "transition": {"kind": "end" if s + 1 == len(phrases) else "cut"},
                       "voice": {"start": round(off + words[g[0]].start, 3), "end": round(off + words[g[-1]].end, 3)}})
    if not rows:
        notes.append("no brief table: every scene's action is a placeholder; write what the screen does")
    plan["scenes"] = scenes
    plan["cuts"] = [round(f / fps, 4) for f in starts[1:]]
    kept = [h for h in plan.get("hits") or [] if isinstance(h, dict) and not str(h.get("role", "")).startswith(("emphasis", "bar "))
            and isinstance(h.get("time"), (int, float)) and h["time"] < duration_frames / fps]
    dropped = len(plan.get("hits") or []) - len(kept)
    if dropped:
        notes.append(f"replaced {dropped} earlier emphasis/grid hits or hits past the end")
    if kept:
        notes.append("kept named hits: " + ", ".join(f"{h['role']} @ {h['time']:g}" for h in kept[:6])
                     + "; check they still fall where the voice wants them")
    added = [{"time": round(off + words[p["index"]].start, 3),
              "amplitude": 1.0 if p["forced"] else round(float(.6 + .1 * min(max(p["score"] - 1, 0), 4)), 2),
              "role": f"emphasis: {words[p['index']].text.strip('.,;:!?¿¡…»«“”')}"} for p in accents]
    plan["hits"] = sorted(kept + added, key=lambda h: h["time"])
    plan.pop("bpm", None), plan.pop("meter", None), plan.pop("lead", None)

    folder = plan_path.parent
    shifted = [caps.Word(w.text, w.start + off, w.end + off, w.source) for w in words]
    cues = [caps.Cue(shifted[g[0]].start, shifted[g[-1]].end, " ".join(shifted[i].text for i in g), [shifted[i] for i in g])
            for g in phrases]
    preset = caps.PRESETS[args.preset]
    lines, cap_warnings = caps.build(cues, preset["max_chars"], preset["cps"], .6, balanced=True)
    warnings += cap_warnings
    plan["captions"] = "captions.json"

    pauses = [{"start": round(off + words[i].end, 3), "end": round(off + words[i + 1].start, 3)}
              for i in range(len(words) - 1) if words[i + 1].start - words[i].end >= .25]
    speech_time = sum(w.end - w.start for w in words)
    span = words[-1].end - words[0].start
    wps = len(words) / span if span > 0 else 0
    if wps > 3.3:
        warnings.append(f"{wps:.1f} words per second: fast for on-screen text; captions will flash, cut fewer words")
    long_scenes = [s["id"] for s in scenes if (s["end_frame"] - s["start_frame"]) / fps > args.max_scene + 1]
    if long_scenes:
        warnings.append("scenes longer than --max-scene with no place to split (no pause or comma): " + ", ".join(long_scenes))
    try:
        rel_voice = voice_path.relative_to(folder.resolve()).as_posix()
    except ValueError:
        rel_voice = str(voice_path)
        warnings.append("the voice is outside the piece folder: copy it into assets/ so the piece travels")
    plan["voice"] = {"file": rel_voice, "start": off, "timing": timing, "words": "voice.json"}

    voice_json = {"file": rel_voice, "start": off, "timing": timing, "words_per_second": round(wps, 2),
                  "words": [{"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3),
                             "emphasis": any(p["index"] == i for p in accents)} for i, w in enumerate(shifted)],
                  "phrases": [{"scene": scenes[s]["id"], "text": scenes[s]["text"], "start": scenes[s]["voice"]["start"],
                               "end": scenes[s]["voice"]["end"]} for s in range(len(scenes))],
                  "pauses": pauses}
    report = {"plan": str(plan_path), "timing": timing, "words": len(words), "scenes": len(scenes),
              "duration_s": round(duration_frames / fps, 3), "words_per_second": round(wps, 2),
              "speech_share": round(speech_time / span, 2) if span else None,
              "emphasis": [{"word": words[p["index"]].text, "time": round(off + words[p["index"]].start, 3),
                            "score": p["score"], "forced": p["forced"]} for p in accents],
              "notes": notes, "warnings": warnings}
    errors = validate(plan)
    report["errors"] = errors
    if args.dry_run or errors:
        report["written"] = []
        return report

    def write(path: Path, data) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    write(plan_path, plan)
    write(folder / "voice.json", voice_json)
    write(folder / "captions.json", {"preset": args.preset, "max_chars": preset["max_chars"], "cps": preset["cps"],
                                     "lines": lines, "warnings": cap_warnings})
    cues_path = folder / "cues.json"
    cue_data = json.loads(cues_path.read_text(encoding="utf-8-sig")) if cues_path.exists() else {"cues": []}
    cue_data["cues"] = [c for c in cue_data.get("cues") or [] if c.get("voice") != "voiceover"]
    cue_data["cues"].append({"voice": "voiceover", "file": rel_voice, "time": off, "gain_db": 0, "duck_db": -15})
    write(cues_path, cue_data)
    report["written"] = [str(plan_path), str(folder / "voice.json"), str(folder / "captions.json"), str(cues_path)]
    return report


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plan", type=Path, required=True, help="the piece's plan.json (new_piece.py makes one)")
    parser.add_argument("--voice", type=Path, required=True, help="the voice: WAV, MP3, M4A…")
    parser.add_argument("--words", type=Path, help="word timings: ElevenLabs/Whisper JSON, VTT, SRT or [{text,start,end}]")
    parser.add_argument("--script", type=Path, help="the text that was read; *word* or CAPITALS force an emphasis")
    parser.add_argument("--brief", type=Path, help="a brief or script with a voice | screen table: scene actions")
    parser.add_argument("--voice-start", type=float, default=0.1, help="when the voice starts in the piece (s)")
    parser.add_argument("--tail", type=float, default=0.8, help="seconds after the last word")
    parser.add_argument("--keep-voice-tail", action="store_true", help="let the whole audio file play, not only to the last word")
    parser.add_argument("--preset", choices=sorted(caps.PRESETS), default="voice",
                        help="caption line length and speed (voice: captions that follow a voice the viewer hears)")
    parser.add_argument("--max-scene", type=float, default=3.5, help="split phrases longer than this (s)")
    parser.add_argument("--min-scene", type=float, default=0.8, help="merge phrases shorter than this (s)")
    parser.add_argument("--long-pause", type=float, default=0.45, help="a pause this long ends a phrase (s)")
    parser.add_argument("--lead-frames", type=int, default=2, help="frames the picture cut leads the phrase's first word")
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = parser.parse_args()
    try:
        report = build(args)
    except (OSError, ValueError, KeyError) as error:
        print(json.dumps({"errors": [str(error)]}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
