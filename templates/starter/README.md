# A Motionsmith piece

Created with `scripts/new_piece.py` from the Motionsmith skill. Change the scene in `piece.js` (`state()` and
`draw()`); the rest already follows the kit's contract and the essential craft rules. Draw the picture on `base`,
what should glow on `light` (it feeds the bloom) and exact brand colours on `top` (composited after the tone map). The
example timings (ring at 0.3 s, title at 1 s, exit 0.7 s before the end) suit 3–8 s pieces; the title shrinks to fit
the safe area. Every position is a fraction of the frame, so the same scene works in any format.

| File | What it is |
|---|---|
| `index.html` | The canvas, the libraries and a root element that also satisfies HyperFrames' contract |
| `piece.js` | The scene: `setup`, `state(t)` (with the `track` points that drive the blur) and `draw` on three layers |
| `plan.json` | Size, fps, duration, safe area, scenes and `hits` (the beats shared by image and sound) |
| `kit/` | A copy of the skill's kit (`motion-math.js`, `postfx-glsl.js`, `timeline.js`, `kinetic-type.js`, `stage.js`, `hyperframes.js`): the piece depends on no outside path. `stage.js` does the render plumbing: capture contract, motion blur, HDR light, bloom, tone map, finishing looks |
| `assets/fonts/` | The font kit: Archivo (variable weight and width), Fraunces, JetBrains Mono, under the SIL Open Font License. `Stage.FONTS` uses them first |
| `assets/` | Images and sound of this piece |
| `preview/` | Frames, sheets and review reports |
| `final/` | The current delivery only (created by `render_stream.mjs`) |

Next steps (`<skill>` = the skill's folder, `<piece>` = this folder):

```bash
python -I <skill>/scripts/validate_plan.py "<piece>/plan.json"
node <skill>/scripts/determinism_check.mjs --root "<piece>"
node <skill>/scripts/sample_frames.mjs --root "<piece>" --out "<piece>/preview/walk" --every 0.5
python -I <skill>/scripts/contact_sheet.py "<piece>/preview/walk" --out "<piece>/preview/walk.jpg"
MOTION_MAX_SAMPLES=8 node <skill>/scripts/render_stream.mjs --root "<piece>" --out final/draft.mp4 --no-audio
node <skill>/scripts/render_stream.mjs --root "<piece>" --out final/piece.mp4 --no-audio
```

To open it in HyperFrames (Studio preview, `hyperframes render`): `python -I <skill>/scripts/hyperframes.py sync
"<piece>"`, then `npx --yes hyperframes@0.8.192 preview` inside the folder. Run `sync` again after you retime
`plan.json`. Captures load only this folder's files: put everything the piece needs in `assets/`.

The full review protocol is in the skill's `references/produce/review-protocol.md`.
