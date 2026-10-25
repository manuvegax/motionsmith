# promo-sequence

Promo sequence: a hook word slams in, a whip pan with real motion blur cuts to a statement, an iris opens the end card.

**Look:** Bold editorial: paper, ink and an acid-yellow accent, a colour step per scene (style atlas #2 and #22).
**Intent:** Show editing, not only animation: three scenes joined by motivated transitions, ending on an action.
**Action:** A huge condensed word slams in on a spring and boils; the camera whips a whole frame with a 300° shutter and the statement arrives inside the blur; its lines rise from masks and an accent rule sweeps under them; an iris grows from the rule into the end card, where the closing word gains weight and a link types in; a scene counter and a progress bar keep counting.

```bash
python -I <skill>/scripts/new_piece.py work/my-piece --recipe promo-sequence --title "Everything | moves for a reason"
```

Default 8 s (at least 6 s), any format (`--format reel|story|portrait|square|landscape`).

## Make it yours

Write the hook and the statement in the title: `--title "Everything | moves for a reason"`. Set `END`, `LINK` and the palette. Move the hits in plan.json to retime the cuts.

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
| `hook slam` | 0.15 s | 1 |
| `whip` | 2.25 s | 0.9 |
| `statement` | 2.3 s | 0.5 |
| `iris` | 2.55 s before the end | 0.8 |
| `end card` | 2.15 s before the end | 0.6 |

## Craft note

Each transition has a motive: the whip carries the energy of the slam into the next scene, and the iris grows from the end of the rule, the last thing the eye was following. The cut hides inside the blur, so the whip needs its 300–360° shutter.

## Check before showing

```bash
python -I <skill>/scripts/validate_plan.py plan.json
node <skill>/scripts/determinism_check.mjs --root .
node <skill>/scripts/sample_frames.mjs --root . --out preview/walk --every 0.25
python -I <skill>/scripts/build_soundtrack.py --plan plan.json --out assets/soundtrack.wav
```

Then the dense review in `references/produce/review-protocol.md`. Everything lives in `piece.js`; the render
plumbing (motion blur, bloom, tone map, capture contract) is in `kit/stage.js`.
