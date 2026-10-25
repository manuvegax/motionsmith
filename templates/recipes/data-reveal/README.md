# data-reveal

Data reveal: a number rolls up on odometer wheels while a teal gauge fills; it lands on its hit and the hold breathes.

**Look:** Infographic: night navy, one calm teal accent, muted source line (style atlas #15).
**Intent:** Make one number land and be believed, with its source on screen.
**Action:** The gauge is drawing on frame 0; the number rolls up on odometer wheels while the arc fills and lights its ticks; it lands on its hit with a punch and a flash ring; a glint, a scan ring, shimmering ticks and a camera breath keep the hold alive; label and source sit below.

```bash
python -I <skill>/scripts/new_piece.py work/my-piece --recipe data-reveal --title "of the goal reached this week"
```

Default 5 s (at least 3 s), any format (`--format reel|story|portrait|square|landscape`).

## Make it yours

Set `VALUE`, `MAX`, `SUFFIX`, the label (`--title`) and `SOURCE`. Whole numbers only. Change `ACCENT` to the colour that means "good" in your piece; keep red for warnings.

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
| `count starts` | 0.3 s | 0.4 |
| `value lands` | 1.9 s | 1 |
| `exit` | 0.45 s before the end | 0.3 |

## Craft note

The count never overshoots the true value; only the scale punch moves on the hit. Keep the source on screen and readable (48 px or more at 1080). The hold is an ambient budget (glint, scan ring, shimmer, camera breath), not accents: data wants calm.

## Check before showing

```bash
python -I <skill>/scripts/validate_plan.py plan.json
node <skill>/scripts/determinism_check.mjs --root .
node <skill>/scripts/sample_frames.mjs --root . --out preview/walk --every 0.25
python -I <skill>/scripts/build_soundtrack.py --plan plan.json --out assets/soundtrack.wav
```

Then the dense review in `references/produce/review-protocol.md`. Everything lives in `piece.js`; the render
plumbing (motion blur, bloom, tone map, capture contract) is in `kit/stage.js`.
