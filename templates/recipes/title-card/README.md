# title-card

Swiss title card: a grid draws, a rule and a typed eyebrow, the title rises line by line from masks, a marker hops while it holds.

**Look:** Swiss / International: paper, black ink, one orange accent, a visible six-column grid, flush left (style atlas #1).
**Intent:** Open a chapter or a video with a calm, confident title.
**Action:** The grid is drawing on frame 0; the rule draws across, the eyebrow types, the title's lines rise from their masks in a cascade and the subtitle settles; an accent marker hops along the rule and the cursor blinks while it holds; it all reverses faster to exit.

```bash
python -I <skill>/scripts/new_piece.py work/my-piece --recipe title-card --title "Slow is smooth, smooth is fast"
```

Default 4 s (at least 3 s), any format (`--format reel|story|portrait|square|landscape`).

## Make it yours

Set `EYEBROW` and `SUBTITLE` (or `''`), the palette and `COLUMNS`. There is no light layer and the tone map is `clip`, so ink and accent keep their colours.

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
| `rule` | 0 s | 0.3 |
| `eyebrow` | 0.12 s | 0.3 |
| `title` | 0.35 s | 0.8 |
| `exit` | 0.7 s before the end | 0.4 |

## Craft note

Every curve is a Timeline track with After Effects influence. Low `outInfluence` leaves sharp, high `inInfluence` lands soft: tune them like the Graph Editor. Swiss means flush left and a grid you can see.

## Check before showing

```bash
python -I <skill>/scripts/validate_plan.py plan.json
node <skill>/scripts/determinism_check.mjs --root .
node <skill>/scripts/sample_frames.mjs --root . --out preview/walk --every 0.25
python -I <skill>/scripts/build_soundtrack.py --plan plan.json --out assets/soundtrack.wav
```

Then the dense review in `references/produce/review-protocol.md`. Everything lives in `piece.js`; the render
plumbing (motion blur, bloom, tone map, capture contract) is in `kit/stage.js`.
