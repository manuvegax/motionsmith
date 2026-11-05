# Depth captions: a word behind the head, captions in front

Read when a talking-head clip needs captions that live in the room instead of on the glass: one big word sits
**behind** the speaker's head, the rest of what they say pops up **in front** of them, and a slow camera moves through
both. Tool: `scripts/depth_captions.py` (`words`, `matte`, `storyboard`, `render`). For a full edit with inserts, cut
the reel first ([talking head](talking-head.md)); this is a finish on a clip of 5–40 s.

## 1. The stack

Every frame is four layers, back to front:

| Layer | What it is | Why |
|---|---|---|
| 1 Plate | The original frame | The room and the person, untouched colour |
| 2 Big word | One word in heavy condensed capitals, ~85 % of the width | The word that carries the line, spent once |
| 3 Person | The same frame cut out with a soft alpha | Their head covers the word: that is what sells "behind" |
| 4 Captions | Up to three words at a time, ~7 % of the width, soft shadow | Everything else they say, in front |

A virtual camera pushes through the stack at three depths: the plate grows 3.5 % over the clip, the word behind
2.6 %, the captions 5 %. The difference is small and constant (ease-in over 0.6 s, then constant speed to the last
frame, so nothing freezes), and it is what makes the type read as placed in depth rather than pasted on top
([living layer](../craft/living-layer.md), [camera & space](../craft/camera-space.md)).

## 2. Numbers

| Decision | Value | Reason |
|---|---|---|
| Big word width | 85 % of the frame (`--width`); never wider than the frame at the pop's peak | Big enough to be the picture, room for the overshoot |
| Big word face | Archivo, weight ~860, width 66 % (a condensed heavy, like Anton), white | Reads at thumbnail size; one family with the captions |
| Vertical place | The head overlaps ~60 % of the letter height: the top of the head just over halfway up the letters | Less and it floats above; more and it stops reading |
| Head top | Highest row of the cut-out inside the **middle 40 %** of the width, on the frame where the word is said | A raised hand at the side does not count |
| Minimum cover | The head covers ≥ 15 % of the word's ink; if not (a hood, a hat, a low head), the word is lowered until it does | Under ~15 % the eye does not see it as behind |
| Entrance | 80 % → 105 % → 100 % over 6 frames, on the frame the word starts; then it stays where it landed | A pop on the voice; the camera keeps it alive |
| Captions | Up to 3 words, split at punctuation, at pauses over 0.3 s and at the big word; each word appears on its start (4 frames: a 1.2 % H rise, 90 → 100 %); the group stays until the next one starts (at most 1.2 s after its last word) | Words already on screen never re-centre: the group is laid out once |
| Caption size | ~7 % of the width, weight 700, soft dark shadow | Legible on a phone over any background |
| Caption place | Above the big word, never on it, between 15 % and 65 % of the height; when the head sits so high that there is no room above, just under the word (the report says `below the word`) | Instagram's buttons and caption cover the bottom third; the top bar covers the first ~15 % |
| Ink | White by default; when the wall behind the word is within 0.35 of the ink's lightness the report warns (`warning_contrast`): use a dark ink or the brand accent (`--color`) | White on a cream wall disappears; on the first test a near-black word read at once |
| The big word | Not captioned twice | It is already the biggest thing on screen |

## 3. Timing to the frame

A caption three frames late is felt even when nobody can say why. Speech-to-text gives word starts that are usually
early: on the first test (Spanish, faster-whisper small) seven of sixteen starts moved, by a median of 0.12 s.

1. **Transcribe** with faster-whisper: word timestamps, **no initial prompt** (a prompt can make it drop words), the
   audio decoded to a 16 kHz mono array first (newer versions fail on some file paths). The tool reads a model already
   in the Hugging Face cache and never downloads one without `--allow-download`.
2. **Show the line** to the person with doubtful words marked `[?]`, names spelled as they say them. Fix the JSON: a
   corrected word keeps the time of the word it replaces.
3. **Snap** every start to the voice: the first rising 10 ms step above the word's local floor + 9 dB, searched from
   0.08 s before to 0.25 s after the transcript time. Run `words --words corrected.json` after every edit.

Ends come from the transcript; they only decide when a group may linger. For the last word of a reel, measure its
tail in the waveform ([talking head](talking-head.md) step 4).

## 4. Steps

```bash
python -I <skill>/scripts/depth_captions.py words clip.mp4 --out work/words.json --language es
# show the line, fix names and [?] words in work/words.json, then re-snap:
python -I <skill>/scripts/depth_captions.py words clip.mp4 --words work/words.json --out work/words.json
python -I <skill>/scripts/depth_captions.py matte clip.mp4 --words work/words.json --word PIZZA --out work/matte
python -I <skill>/scripts/depth_captions.py storyboard clip.mp4 --words work/words.json --word PIZZA --matte work/matte --out work/preview/board
python -I <skill>/scripts/depth_captions.py render clip.mp4 --words work/words.json --word PIZZA --matte work/matte --out work/final/clip-v1.mp4
```

- **Pick the word** that carries the line: the number, the object, the thing the clip is about. Without `--word` the
  tool picks the longest content word (a number first; words in the last 30 % of the clip count less) and says which; `--display`
  shows other text for it (a number written out, an accent the transcript lost).
- **Cut-out**: from the frame of the big word to the end (`--lead N` adds frames before). Models are the ONNX files
  rembg keeps in `~/.u2net`: `birefnet-portrait` (best on hair, ~1 GB), `isnet-general-use` (~180 MB, good on a clear
  edge), `u2net_human_seg`. The tool runs them with onnxruntime and never downloads: a missing model stops with its
  size. A few seconds per frame on a CPU: say how long before starting, run it in the background.
- **Storyboard** before the render: one still per caption group plus the word landing. Check the placement there
  (`head_covers` in the report), not in the MP4.
- **Render**: H.264 at the clip's size and frame rate, converted with the clip's own colour matrix and tagged with it,
  so the colours do not shift; an iPhone HDR (HLG) clip is tone-mapped to BT.709 and the report says so. The original
  audio is kept. It writes a still of the word (`<out>.png`) and `<out>.events.json` (the word and each caption group)
  for the sound.

## 5. Sound

One sound per visible event, placed on its frame, mixed under the voice: a soft low thump or a paper tap under the big
word, nothing or a tick under caption groups (a sound on every group turns into a metronome). Take the times from
`events.json` into the plan's `hits` and build it with `build_soundtrack.py`, or place recorded effects by hand; keep the
voice on top ([sound design](../craft/sound-design.md)).

## 6. Filming for it

- Leave space above the head: the big word needs somewhere to sit.
- Light on the face and hair, and a background that separates from them: a clear edge round the head is what sells it.
- 5–10 s per depth word. Spend it once per clip: if every line gets a word behind the head, none of them matters.

## 7. Checks

| Check | Pass |
|---|---|
| `head_covers` in the storyboard or render report | ≥ 0.15 (a warning prints below that) |
| `frames_without_matte` | 0 (the render exits 1 otherwise) |
| The still | The word reads, the head clearly in front, no halo round the hair, captions clear of the word |
| `verify_export.py --require-cfr` | The frame rate and size of the clip, BT.709 tags, audio present |
| `hold_check.py` | No dead hold: the camera push keeps every frame moving |
| On the phone | Captions on the syllable, the edge round the head at real speed: only the person can judge it |

## 8. Notes like an editor

The breakdown this comes from worked in rounds: a storyboard first (one still per line), a first full cut rendered
while the creator slept, then notes written on frames, the way one would note an editor; five rounds made the reel.
Ask for notes the same way (time + what to change), change only what was asked, render again, keep each version.

## 9. What it does not do

It does not relight the person to a new room (the breakdown used Beeble, a paid relighting service, for that), does not
rebuild the background behind the person (so the plate and the person move together; only the type has parallax), and
does not animate per letter. It is a finish for one clip, not an editor.

## Sources

Shaan Johari (@viashaan), "How I edited my captions reel with AI" (Notion breakdown of an Instagram reel, read
2026-11-05): the stack, the placement numbers, the pop, the caption band, the timing method and the rounds of notes are
from it; the tool, the onset snap, the model runner, the depth push and the checks are this skill's.
