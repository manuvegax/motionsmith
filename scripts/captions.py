"""Captions for kinetic type: SRT, WebVTT or JSON in, a timed line list out (for karaoke in kit/kinetic-type.js).

  python scripts/captions.py talk.srt --out captions.json [--preset reel] [--max-chars 22] [--cps 15]
      [--min-seconds 0.6] [--format auto|srt|vtt|json] [--replace]

Presets are formats with their own line length and reading speed:
  reel      22 characters per line, 15 characters per second (vertical video, large type)
  story     20 characters per line, 14 cps (text laid over an image)
  subtitle  42 characters per line, 17 cps (the conventional subtitle limits)
  voice     24 characters per line, 22 cps (captions that follow a voice the viewer hears: the ear carries the pace)
Lines are wrapped on word boundaries and never inside a word; a word longer than the limit keeps a line of its own and
is reported. Word timings come from the source when it has them (WebVTT <00:01.200> tags, or "words" in JSON such as
Whisper writes them); otherwise they are estimated from character counts across the cue and marked "estimated".
With source timings a line also closes before the word that would make its reading speed exceed --cps (after at least
two words). Every line stays on screen for its reading time (characters / cps) and at least --min-seconds, never past
the start of the next line. Lines that still read faster than cps are listed under warnings.
Refuses to overwrite the output unless --replace is given.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

PRESETS = {
    "reel": {"max_chars": 22, "cps": 15.0},
    "story": {"max_chars": 20, "cps": 14.0},
    "subtitle": {"max_chars": 42, "cps": 17.0},
    "voice": {"max_chars": 24, "cps": 22.0},
}
MIN_WORDS_BEFORE_SPEED_SPLIT = 2
TIMESTAMP = re.compile(r"^\s*(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:[,.](\d{1,3}))?\s*$")
INLINE_TIME = re.compile(r"<(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3})>")
TAG = re.compile(r"</?[A-Za-z][^>]*>")


@dataclass(frozen=True)
class Word:
    text: str
    start: float
    end: float
    source: bool   # True when the timing came from the input, False when it was estimated


@dataclass
class Cue:
    start: float
    end: float
    text: str
    words: list[Word] | None = None


@dataclass
class Line:
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


def parse_time(value) -> float:
    """Seconds from a number, '1.5', 'mm:ss.mmm', 'hh:mm:ss,mmm' (SRT) or 'hh:mm:ss.mmm' (VTT)."""
    if isinstance(value, bool):
        raise ValueError(f"not a time: {value!r}")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    match = TIMESTAMP.match(text)
    if match:
        hours, minutes, seconds, fraction = match.groups()
        return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + (float("0." + fraction) if fraction else 0.0)
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"not a time: {value!r}") from None


def clean(text: str) -> str:
    """Plain text: markup and inline timestamps removed, whitespace collapsed, Unicode normalised to NFC."""
    text = INLINE_TIME.sub("", unicodedata.normalize("NFC", text))
    return " ".join(TAG.sub("", text).split())


def estimate_words(words: list[str], start: float, end: float) -> list[Word]:
    """Spread a cue's time over its words in proportion to their length (plus one space each)."""
    total = sum(len(w) + 1 for w in words)
    span = max(end - start, 0.0)
    out, cursor = [], 0
    for word in words:
        begin = start + span * cursor / total
        cursor += len(word) + 1
        out.append(Word(word, begin, start + span * cursor / total, source=False))
    return out


def parse_srt(text: str) -> list[Cue]:
    cues = []
    for block in re.split(r"\r?\n\s*\r?\n", text.replace("﻿", "").strip()):
        lines = [line for line in block.splitlines() if line.strip()]
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            continue
        start, end = (part.strip() for part in lines[timing].split("-->", 1))
        if not start or not end.split():
            raise ValueError(f"SRT cue {len(cues) + 1} needs both a start and an end time: {lines[timing]!r}")
        cues.append(Cue(parse_time(start), parse_time(end.split()[0]), clean(" ".join(lines[timing + 1:]))))
    if not cues:
        raise ValueError("no SRT cues found: each cue needs a line with 'start --> end'")
    return cues


def parse_vtt(text: str) -> list[Cue]:
    body = text.replace("﻿", "").strip()
    if not body.startswith("WEBVTT"):
        raise ValueError("not a WebVTT file: the first line must be WEBVTT")
    cues = []
    for block in re.split(r"\r?\n\s*\r?\n", body):   # the header block has no '-->'; a cue glued to it still counts
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing is None:
            continue
        start, end = (part.strip() for part in lines[timing].split("-->", 1))
        if not start or not end.split():
            raise ValueError(f"WebVTT cue {len(cues) + 1} needs both a start and an end time: {lines[timing]!r}")
        start_s, end_s = parse_time(start), parse_time(end.split()[0])
        payload = "\n".join(lines[timing + 1:]).strip()
        words = timed_words(payload, start_s, end_s)
        plain = clean(payload)
        cues.append(Cue(start_s, end_s, plain, words))
    if not cues:
        raise ValueError("no WebVTT cues found")
    return cues


def timed_words(payload: str, start: float, end: float) -> list[Word] | None:
    """Words from inline <00:01.200> tags. Returns None when the cue carries no word timings."""
    pieces = INLINE_TIME.split(payload)
    if len(pieces) == 1:
        return None
    segments = [(start, clean(pieces[0]))]
    for index in range(1, len(pieces), 2):
        segments.append((parse_time(pieces[index]), clean(pieces[index + 1]) if index + 1 < len(pieces) else ""))
    words = []
    for index, (seg_start, seg_text) in enumerate(segments):
        seg_end = segments[index + 1][0] if index + 1 < len(segments) else end
        seg_words = seg_text.split()
        if not seg_words:
            continue
        if len(seg_words) == 1:
            words.append(Word(seg_words[0], seg_start, seg_end, source=True))
        else:
            words += [Word(w.text, w.start, w.end, source=False) for w in estimate_words(seg_words, seg_start, seg_end)]
    return words or None


def parse_json(data) -> list[Cue]:
    items = data
    if isinstance(data, dict):
        items = data.get("cues", data.get("segments"))
    if not isinstance(items, list) or not items:
        raise ValueError('JSON needs a list of cues, or an object with "cues" or "segments"')
    cues = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or "start" not in item or "end" not in item:
            raise ValueError(f"cue {index} needs start and end (seconds)")
        start, end = parse_time(item["start"]), parse_time(item["end"])
        raw_words = item.get("words")
        words = None
        if isinstance(raw_words, list) and raw_words:
            words = []
            for w in raw_words:
                text = clean(str(w.get("text", w.get("word", ""))))
                if text:
                    words.append(Word(text, parse_time(w["start"]), parse_time(w["end"]), source=True))
        text = clean(str(item.get("text", " ".join(w.text for w in words or []))))
        cues.append(Cue(start, end, text, words))
    return cues


def cue_words(cue: Cue) -> list[Word]:
    if cue.words:
        return cue.words
    return estimate_words(cue.text.split(), cue.start, cue.end) if cue.text else []


def wrap(words: list[Word], max_chars: int, cps: float, min_seconds: float, warnings: list[str]) -> list[Line]:
    """Greedy lines: as many words as max_chars allows; with source timings also as many as reads at cps."""
    lines: list[Line] = []
    current: Line | None = None
    for word in words:
        if len(word.text) > max_chars:
            warnings.append(f'"{word.text}" is {len(word.text)} characters, over the limit of {max_chars}: it keeps its own line')
        if current is None:
            current = Line([word])
            continue
        candidate = current.words + [word]
        chars = len(" ".join(w.text for w in candidate))
        span = max(word.end - current.words[0].start, min_seconds)
        too_long = chars > max_chars
        too_fast = word.source and len(current.words) >= MIN_WORDS_BEFORE_SPEED_SPLIT and chars / span > cps
        if too_long or too_fast:
            lines.append(current)
            current = Line([word])
        else:
            current.words.append(word)
    if current is not None:
        lines.append(current)
    return lines


# Words a caption line should not end on (articles, prepositions, conjunctions): the line would hang.
WEAK_ENDINGS = set("""a al ante con de del el en entre la las le lo los mi mis o para pero por que se sin sobre su sus
te tu tus un una unos unas y e ni the a an and or but of to in on at by for with from as my your his her our their""".split())


def wrap_balanced(words: list[Word], max_chars: int, warnings: list[str]) -> list[Line]:
    """Lines of even length inside one cue: the fewest lines that fit, then breaks that keep lines alike, never end a
    line on a weak word (de, que, y, the…) and never leave one short word alone. Dynamic programming over breaks."""
    n = len(words)
    for word in words:
        if len(word.text) > max_chars:
            warnings.append(f'"{word.text}" is {len(word.text)} characters, over the limit of {max_chars}: it keeps its own line')

    def length(i: int, j: int) -> int:
        return len(" ".join(w.text for w in words[i:j]))

    def bare(text: str) -> str:
        return re.sub(r"[^\w]", "", text.lower())

    total = length(0, n)
    lines_needed = max(1, -(-total // max_chars))
    target = total / lines_needed
    best = [0.0] + [float("inf")] * n
    back = [0] * (n + 1)
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            size = length(i, j)
            if size > max_chars and j - i > 1:
                break
            cost = (size - target) ** 2 + 400   # 400 per line: fewer lines first
            if j < n and bare(words[j - 1].text) in WEAK_ENDINGS:
                cost += 900
            if j - i == 1 and n > 1 and len(words[i].text) < 9:
                cost += 700                      # a lone short word
            if best[i] + cost < best[j]:
                best[j], back[j] = best[i] + cost, i
    cuts, j = [], n
    while j > 0:
        cuts.append((back[j], j))
        j = back[j]
    return [Line(list(words[i:j])) for i, j in reversed(cuts)]


def build(cues: list[Cue], max_chars: int, cps: float, min_seconds: float,
          balanced: bool = False) -> tuple[list[dict], list[str]]:
    """balanced: break each cue into even lines (wrap_balanced) instead of filling lines greedily; for captions
    that follow a voice, where each cue is one spoken phrase."""
    warnings: list[str] = []
    lines: list[Line] = []
    for cue in sorted(cues, key=lambda c: c.start):
        words = cue_words(cue)
        lines += wrap_balanced(words, max_chars, warnings) if balanced and words else wrap(words, max_chars, cps, min_seconds, warnings)
    result = []
    for index, line in enumerate(lines):
        start = line.words[0].start
        end = line.words[-1].end
        chars = len(line.text)
        need = max(chars / cps, min_seconds)
        limit = lines[index + 1].words[0].start if index + 1 < len(lines) else float("inf")
        if end - start < need:
            end = max(end, min(start + need, limit))
        reading = chars / (end - start) if end > start else float("inf")
        if reading > cps + .5:
            warnings.append(f"line {index} reads at {reading:.1f} cps (limit {cps:g}): {line.text!r}")
        source = all(w.source for w in line.words)
        result.append({
            "index": index, "text": line.text, "start": round(start, 3), "end": round(end, 3), "chars": chars,
            "reading_cps": round(reading, 2) if reading != float("inf") else None,
            "timing": "source" if source else "estimated",
            "words": [{"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3)} for w in line.words],
        })
    return result, warnings


def detect_format(path: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    return {".srt": "srt", ".vtt": "vtt", ".json": "json"}.get(path.suffix.lower(), "")


def load(path: Path, fmt: str) -> list[Cue]:
    text = path.read_text(encoding="utf-8-sig")
    if fmt == "srt":
        return parse_srt(text)
    if fmt == "vtt":
        return parse_vtt(text)
    if fmt == "json":
        try:
            return parse_json(json.loads(text))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSON: {error}") from None
    raise ValueError("cannot tell the format from the extension: pass --format srt, vtt or json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="SRT, WebVTT or JSON file")
    parser.add_argument("--out", type=Path, required=True, help="captions JSON to write")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="reel", help="line length and reading speed (default reel)")
    parser.add_argument("--max-chars", type=int, help="override the preset's characters per line")
    parser.add_argument("--cps", type=float, help="override the preset's reading speed (characters per second)")
    parser.add_argument("--min-seconds", type=float, default=0.6, help="shortest time a line stays on screen")
    parser.add_argument("--format", choices=["auto", "srt", "vtt", "json"], default="auto")
    parser.add_argument("--replace", action="store_true", help="overwrite the output if it exists")
    args = parser.parse_args()

    if not args.source.is_file():
        parser.error(f"file not found: {args.source}")
    if args.out.exists() and not args.replace:
        parser.error(f"{args.out} exists; choose another name or pass --replace")
    preset = PRESETS[args.preset]
    max_chars = preset["max_chars"] if args.max_chars is None else args.max_chars
    cps = preset["cps"] if args.cps is None else args.cps
    if max_chars < 4 or not 1 <= cps <= 40 or args.min_seconds < 0:
        parser.error("max-chars must be at least 4, cps between 1 and 40, min-seconds not negative")
    try:
        cues = load(args.source, detect_format(args.source, args.format))
        lines, warnings = build(cues, max_chars, cps, args.min_seconds)
    except (ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    timings = {line["timing"] for line in lines}
    document = {
        "version": 1, "source": args.source.name,
        "format": {"preset": args.preset, "max_chars": max_chars, "cps": cps, "min_seconds": args.min_seconds},
        "timing": "mixed" if len(timings) > 1 else (timings.pop() if timings else "none"),
        "lines": lines, "warnings": warnings,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out.resolve()), "lines": len(lines), "timing": document["timing"],
                      "warnings": len(warnings)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
