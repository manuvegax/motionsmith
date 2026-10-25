# lower-third

Lower third: an accent bar grows, name and role panels wipe out from behind it, a progress line fills while it holds, then it wipes back.

**Look:** Clean broadcast: white and ink panels, one signal-yellow accent, over a footage placeholder.
**Intent:** Say who is speaking without covering them or stealing the shot.
**Action:** The accent bar is already growing on frame 0; the name panel wipes out from behind it with the name rising in its mask, the role panel follows a beat later; while it holds a light runs down the bar and a progress line fills; everything wipes back into the bar.

```bash
python -I <skill>/scripts/new_piece.py work/my-piece --recipe lower-third --title "Name Surname"
```

Default 5 s (at least 3 s), any format (`--format reel|story|portrait|square|landscape`).

## Make it yours

Set the name (`--title`) and `ROLE`. `BACKDROP = false` gives a flat background; for real footage see `references/produce/overlays-alpha.md`.

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
| `bar in` | 0.12 s | 0.4 |
| `name in` | 0.4 s | 0.6 |
| `out` | 0.9 s before the end | 0.4 |

## Craft note

Lower thirds live on the bottom of the safe area and get an ambient budget while they hold (a light on the bar, a progress line), never accents that pull the eye from the speaker. Check them against the platform's interface (`references/edit/formats-platforms.md`).

## Check before showing

```bash
python -I <skill>/scripts/validate_plan.py plan.json
node <skill>/scripts/determinism_check.mjs --root .
node <skill>/scripts/sample_frames.mjs --root . --out preview/walk --every 0.25
python -I <skill>/scripts/build_soundtrack.py --plan plan.json --out assets/soundtrack.wav
```

Then the dense review in `references/produce/review-protocol.md`. Everything lives in `piece.js`; the render
plumbing (motion blur, bloom, tone map, capture contract) is in `kit/stage.js`.
