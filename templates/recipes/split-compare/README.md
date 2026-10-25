# split-compare

Split compare: a divider whips from BEFORE to AFTER under a headline band, springs to the middle, holds alive and ends on AFTER.

**Look:** Duotone: slate and paper, ink, one emerald accent (style atlas #19 and #23).
**Intent:** Show a change by letting the viewer see both states at once.
**Action:** BEFORE strokes boil on slate; a divider whips across with heavy blur to reveal AFTER (a calm grid with one accent point), springs back to the middle and settles; labels pop in; a wave, a light beam and a pulse keep the hold alive; AFTER takes the frame to end.

```bash
python -I <skill>/scripts/new_piece.py work/my-piece --recipe split-compare --title "Same frame, two decisions"
```

Default 6 s (at least 3 s), any format (`--format reel|story|portrait|square|landscape`).

## Make it yours

Replace `drawBefore()` and `drawAfter()` with your two states. Set the headline (`--title`) and `LABELS`.

Fonts: the font kit travels with the piece in `assets/fonts/` (Archivo with variable weight and width, Fraunces,
JetBrains Mono; SIL OFL), so every machine draws the same letters. For another face, add its `@font-face` to
`index.html`, put it in `fonts: [...]` and check it with `determinism_check --font`.

HyperFrames: add `--hyperframes` to `new_piece.py` (or run `scripts/hyperframes.py sync` on the piece) to preview it in
HyperFrames Studio and render it with `npx hyperframes render`; see `references/produce/hyperframes.md`.

## Hits

The piece reads these times from `plan.json` by role (`env.hit(role)`). Move a hit there and the picture moves
with it; give the same plan to `scripts/build_soundtrack.py` and the sound lands on it too.

| Role | Default time | Amplitude |
|---|---|---|
| `whip` | 0.6 s | 1 |
| `settle` | 1.5 s | 0.8 |
| `labels` | 1.75 s | 0.4 |
| `exit` | 0.6 s before the end | 0.6 |

## Craft note

The headline sits on its own band, so it reads over both halves and the divider never crosses it. The whip uses a 360° shutter for a fuller smear. The piece ends on AFTER: finish on the answer.

## Check before showing

```bash
python -I <skill>/scripts/validate_plan.py plan.json
node <skill>/scripts/determinism_check.mjs --root .
node <skill>/scripts/sample_frames.mjs --root . --out preview/walk --every 0.25
python -I <skill>/scripts/build_soundtrack.py --plan plan.json --out assets/soundtrack.wav
```

Then the dense review in `references/produce/review-protocol.md`. Everything lives in `piece.js`; the render
plumbing (motion blur, bloom, tone map, capture contract) is in `kit/stage.js`.
