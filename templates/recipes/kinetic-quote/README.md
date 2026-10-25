# kinetic-quote

Kinetic quote: words cascade in while cycling type faces; the keyword lands last, twice the size, on its own hit.

**Look:** Typographic poster: warm paper, black ink, one ultramarine word (style atlas #9).
**Intent:** Make one sentence land, with the keyword as the payoff.
**Action:** Words cascade in letter by letter, cycling faces at 12 fps before they settle; a short vacuum; the keyword lands on its own line, about twice the size, in the accent, with a print kick and outline echoes; a giant outline marquee slides behind; lines leave one by one.

```bash
python -I <skill>/scripts/new_piece.py work/my-piece --recipe kinetic-quote --title "The eye only sees what the mind is *ready* for"
```

Default 6 s (at least 4 s), any format (`--format reel|story|portrait|square|landscape`).

## Make it yours

Mark the keyword with asterisks in the title: `--title "the mind is *ready* for"`. `|` forces a line break. Change `FACES` to the faces you have (the last one is where words settle) and `KEY_SCALE` for the keyword's size.

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
| `first word` | 0.06 s | 0.5 |
| `keyword lands` | 2.6 s | 1 |
| `exit` | 0.62 s before the end | 0.4 |

## Craft note

The keyword is the hero: its own line, about twice the size, its own hit. The words before it are spread so it lands after a short vacuum (`VACUUM`). Long sentences get a longer `--duration` or a later `keyword lands` hit.

## Check before showing

```bash
python -I <skill>/scripts/validate_plan.py plan.json
node <skill>/scripts/determinism_check.mjs --root .
node <skill>/scripts/sample_frames.mjs --root . --out preview/walk --every 0.25
python -I <skill>/scripts/build_soundtrack.py --plan plan.json --out assets/soundtrack.wav
```

Then the dense review in `references/produce/review-protocol.md`. Everything lives in `piece.js`; the render
plumbing (motion blur, bloom, tone map, capture contract) is in `kit/stage.js`.
