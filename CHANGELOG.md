# Changelog

## 1.0.0 · 2026-10-24

First public release.

- **Guides**: 34 guides in four areas. Create (ideation, style atlas of 24 looks, 15 scene blueprints, art
  direction, reference study), Edit (cutting, pacing and retention, transitions atlas, story structures, music
  editing, colour grade, captions and titles, formats and platforms), Craft (15 guides from principles to sound
  design) and Produce (pipeline, review protocol with three critics, rubric, overlays, plan schema, delivery).
- **Kit**: `motion-math.js`, `postfx-glsl.js`, and new `timeline.js` (keyframes with After Effects influence),
  `kinetic-type.js` (cascades, face cycling, glitch, echoes, typewriter, marquee, karaoke) and `stage.js` (shared
  render plumbing: capture contract, motion blur from tracked points, HDR bloom, tone map, text fitting that breaks
  on phrases, portable font stacks, and a GPU-free environment for tests).
- **Recipes**: logo reveal (minimal glow), kinetic quote (typographic poster), title card (Swiss), data reveal
  (infographic), lower third (broadcast) and split compare (duotone), runnable in five formats, with readable sizes
  (48 px floor at 1080) and holds that stay alive. `new_piece.py --recipe` and `--format reel|story|portrait|square|landscape`.
- **Sound**: `scripts/sfx/` synthesis library and `build_soundtrack.py` from the plan's hits.
- **Tools**: `captions.py`, `make_gif.py`, plus the existing capture, render, verification and audio tools.
- **Taste profiles**: project (`MOTIONSMITH.md`) and personal (`profiles/personal/`, never committed).
- **Install**: `install.py --claude --codex`; never overwrites or deletes personal profiles, refuses a folder that
  is not a Motionsmith install, `--check` lists every file it would touch.
- **Review before release**: three critics (engineer, art director and editor, first-time user) checked the code, the
  guides and the recipes; every confirmed finding was fixed and is covered by a test. A second, adversarial audit
  followed (attack surface, failure scenarios, other agents).
- **HyperFrames**: `new_piece.py --hyperframes` and `scripts/hyperframes.py sync` make a piece a HyperFrames project
  (passes `hyperframes lint` and `check`, renders with `hyperframes render`, same frames as `render_stream`);
  `hyperframes.py clip` hands a rendered piece to a HyperFrames film; guide `references/produce/hyperframes.md`.
- **Type**: a font kit (Archivo with variable weight and width, Fraunces, JetBrains Mono; SIL OFL) in every piece;
  weight landings and width slams in the recipes; `Stage.font()`; balanced line breaks that follow phrases.
- **Finish**: `Stage.looks.print` (screen print with a misregistration kick on the hits) and `Stage.looks.crt`.
- **Seventh recipe**: promo sequence (hook slam, whip pan with real motion blur, iris, end card).
- **Hardening**: captures cannot reach the internet; the local server refuses symlinks out of the piece and foreign
  Host headers; drafts with `MOTION_MAX_SAMPLES`; an opt-in 8-bit fallback; pieces are never created inside the skill;
  `install.py` refuses folders that are not a Motionsmith install.
- **Agents**: `install.py --antigravity`, `--gemini`, `--workspace` and `--all`, besides `--claude` and `--codex`.
