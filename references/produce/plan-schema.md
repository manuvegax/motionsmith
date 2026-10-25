# The plan (`plan.json`)

Read when turning a storyboard into production. Validate with `python -I <skill>/scripts/validate_plan.py plan.json`
(add `--require-craft` when a specific language or level was requested). `new_piece.py` writes a valid one.

## 1. Minimal schema

Frames belong to half-open intervals `[start_frame, end_frame)`. Scenes cover the master with no gaps or overlaps; a
two-layer transition uses both layers inside the interval, it does not duplicate scene time.

```json
{
  "schema_version": 1,
  "width": 1080, "height": 1920, "fps": 60, "duration_frames": 480,
  "mode": "editorial", "format": "reel", "audio": "optional",
  "safe_area": {"x": 80, "y": 220, "width": 850, "height": 1220},
  "hits": [{"time": 2.0, "amplitude": 1, "role": "ring lands"}],
  "scenes": [
    {"id": "object", "start_frame": 0, "end_frame": 180,
     "intent": "Present a relation between object and space",
     "action": "A circle opens until it frames an image",
     "text": "", "transition": {"kind": "morph", "carrier": "white contour and a stable centre"}},
    {"id": "window", "start_frame": 180, "end_frame": 480,
     "intent": "Reveal the new framing and resolve the action",
     "action": "The frame reveals an editorial composition and settles",
     "text": "", "transition": {"kind": "end", "carrier": ""}}
  ]
}
```

| Field | Values |
|---|---|
| `mode` | `editorial`, `kinetic`, `diagram`, `glow`, `retro` |
| `format` (optional) | `reel`, `story`, `insert`, `overlay` (aspect comes from `width`/`height`) |
| `audio` | `required`, `optional`, `forbidden` |
| `fps` | A number or a rational string such as `"30000/1001"` |
| `duration_frames`, `width`, `height` | Positive integers; even dimensions for yuv420p |
| `safe_area` | Integer `x`, `y`, `width`, `height` inside the frame ([formats & platforms](../edit/formats-platforms.md)) |
| `hits` (optional) | Chronological `{time, amplitude (0, 2], role}`: the beats shared by image and sound |
| `sound_cues` (optional) | `{time, role, source}` validated inside the duration |
| `transition.kind` | `cut`, `match-cut`, `morph`, `mask`, `wipe`, `camera`, `fade`, `end`; visual links need a `carrier` (what stays) |

Each scene has a unique id, `intent`, `action` and `text` (may be empty). The last `end` can mark a close; it does not
imply a hold.

### 1b. Edit fields (optional, checked when present)

| Field | Values | Used by |
|---|---|---|
| `bpm`, `lead` | Tempo in (0, 400]; `lead` = time of beat 0 in seconds (needs `bpm`) | [music editing §1](../edit/music-editing.md#1-beat-grid) |
| `cuts` | Strictly increasing times in seconds inside the duration | [cutting](../edit/cutting.md) |
| `captions` | A path to the `captions.json` that `scripts/captions.py` writes, or inline lines `{text, start, end}` (seconds, chronological, no overlap; optional `words: [{text, start, end}]`) | [captions & titles](../edit/captions-titles.md), `KineticType.karaoke` |

Keep one source per quantity: cut times and caption times live here, and the code reads them; nothing is
retyped in `piece.js`.

## 2. Craft fields (with `--require-craft`)

When a specific language or level is requested, add:

```json
{
  "reference_evidence": [{
    "source": "local reference and the stretch observed",
    "observed_operation": "the document fills the frame and focus discovers a word",
    "own_application": "a photo sheet becomes the frame of the headline",
    "proof_times": [1.15, 1.36, 1.62]
  }],
  "style_sequence": [
    {"time": 0.3, "composition": "photographic macro, a word cut by the frame"},
    {"time": 1.6, "composition": "open field, three sheets on different planes"},
    {"time": 3.1, "composition": "monumental negative type organising the cut-out"}
  ]
}
```

and per scene `motion` (`preparation`, `action`, `follow_through`, `reading`; see
[direction §3](../craft/direction-choreography.md#3-choreography-preparation-action-consequence)) and `blur_plan`
(`motion`, `focus`, `text_resolution`). The validator checks presence, shape and times, not quality. Other useful
fields: `assets`, `voice_cues`, `camera`, `palette`, `font_roles`, `loop`, `handles`, `concept`.

## 3. A coherent music grid

With music, define BPM, metre and which beat holds each change. At 120 BPM a beat is 0.5 s and a 4/4 bar is 2 s; 15 s
hold 7.5 bars. If a brief asks for equal time per technique *and* one technique per bar, resolve the contradiction in
the plan and say which one wins. With recorded voice, derive rhythm from its cues before imposing a grid.
[Music editing](../edit/music-editing.md).

## 4. The plan is not the storyboard

The minimal schema does not replace a storyboard. Compare the visual evidence, never approve a plan for having its
fields filled. For cues, keep source, real time, scene and associated action; a sound does not need an impact on
every beat.
