# logo-reveal

Logo reveal: pieces of a mark fly in on arcs, lock on one hit and settle; a glint crosses it and returns; the wordmark tracks in.

**Look:** Minimal glow: charcoal, warm white, one red accent, bloom in halo mode (style atlas #8).
**Intent:** Introduce the brand with one strong lock and a clean end card.
**Action:** Pieces of the mark accelerate into place and lock (punch, flash, shock ring), recoil and settle; a glint crosses the mark and returns every 1.6 s; the wordmark tracks in from wide spacing; a tagline settles; dust drifts and the accent breathes while it holds.

```bash
python -I <skill>/scripts/new_piece.py work/my-piece --recipe logo-reveal --title "BRAND"
```

Default 4 s (at least 3 s), any format (`--format reel|story|portrait|square|landscape`).

## Make it yours

Paste your logo's SVG path data into `MARK` (viewBox 0 0 100 100), one entry per piece that should fly. Give each piece its `pivot` (its own centre) so it spins on itself. Put the piece that must keep an exact brand colour on `layer: 'top'`.

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
| `mark locks` | 0.85 s | 1 |
| `glint` | 1.2 s | 0.35 |
| `wordmark` | 1.45 s | 0.5 |

## Craft note

Pieces accelerate into the lock (`power2.in`) so the energy lands on the hit, then recoil and settle: nothing stops dead. If it reads too aggressive, shorten the arcs (`from`) before softening the curve.

## Check before showing

```bash
python -I <skill>/scripts/validate_plan.py plan.json
node <skill>/scripts/determinism_check.mjs --root .
node <skill>/scripts/sample_frames.mjs --root . --out preview/walk --every 0.25
python -I <skill>/scripts/build_soundtrack.py --plan plan.json --out assets/soundtrack.wav
```

Then the dense review in `references/produce/review-protocol.md`. Everything lives in `piece.js`; the render
plumbing (motion blur, bloom, tone map, capture contract) is in `kit/stage.js`.
