# Changelog

## 1.4.0 · 2026-10-26

Hook variants for trial reels.

- **`scripts/hook_variants.py`**: `init` writes `variants.json` from the brief's `hooks:` and `seam:` (the piece itself
  is the control); `render` makes one folder per variant (its TITLE and hit times), proves to the pixel that every
  variant matches the piece at the seam (refuses one that does not), renders each opening alone and the body once,
  builds one soundtrack per variant, joins them without re-encoding and leaves `final/hooks/hooks.md`, a results
  table for the 3-second skip rate and the average watch time.
- `brief.py` reads `hooks:` (two to four, all different) and `seam:`.
- Motion brief §8 and pacing §2 on testing the hook instead of guessing.

## 1.3.0 · 2026-10-26

Long pieces render in parallel chunks that resume.

- **`scripts/render_parallel.mjs`**: chunks of about three per worker render at once, each in its own browser; a
  failed chunk is retried twice; an interrupted render resumes from its finished chunks (fingerprinted on every file of
  the piece and the encoder settings, so a changed piece never reuses them); chunks join without re-encoding, audio
  over the whole, frame count checked. Measured: a 18.7 s voice-over at 1080×1920 / 30 fps went from 13.0 to 6.0
  minutes with three workers.
- `render_stream.mjs --frames a:b` (an exact frame range) and `--report <file>`.
- Pipeline guide §3b.

## 1.2.0 · 2026-10-26

The voice is the clock: pieces told by a voice.

- **`scripts/voice_plan.py`**: a voice and its word timings (ElevenLabs speech-to-text, Whisper, a list of onsets,
  WebVTT, SRT, or the script alone aligned to the voice's pauses) become the plan: one scene per phrase (split only at
  a comma or a real pause), cuts two frames before each phrase, one accent per phrase (the last content word unless the
  voice or a `*mark*` in the script says otherwise), balanced captions, `voice.json` for the piece and the
  `voiceover` cue. Stops when the timings belong to another take; tightens word ends so pauses come back; restores the
  script's punctuation; takes each scene's action from the brief's voice | screen table.
- **Mix**: a `voiceover` cue puts the voice on top, dry, and ducks everything else under its own envelope; the report
  gives `voice_over_bed_db` and warns under 10 dB. A soft `tap` voice for accents under speech (`emphasis` hits).
  The master now lowers the gain of dense material that is too loud even unsaturated, instead of failing.
- **Captions**: `captions.py --preset voice` (22 characters per second, the ear carries the pace) and balanced lines
  that never end on a weak word or leave one short word alone.
- **Recipe `voice-captions`**: each phrase a scene, words land as they are said, the stressed word in the accent with
  an underline sweep, paper and ink swap on every cut; reads `voice.json`, or spreads its title as a demo voice.
- **Brief `voiceover`**: a two-column script (voice | screen); `brief.py check` estimates the spoken length at 2.5
  words per second and flags rows with no picture.
- **Review per phrase**: `sample_frames.mjs --cuts` (both sides of every cut) and `--scenes` (one frame per phrase).
- **Delivery weight**: `render_stream.mjs` reports `size_mb` and `video_mbps` and warns above 40 Mbit/s (grain at CRF 14
  ran to 73 Mbit/s in a test; CRF 20 gave 1.8). `audio_check.py` no longer asks for an impact on voice accents.
- Guide `references/edit/voiceover.md`.

## 1.1.0 · 2026-10-26

The motion brief: decide the piece before the code.

- **Brief in six blocks** (`references/create/motion-brief.md`): `<inputs>`, `<direction>`, `<structure>`,
  `<build>`, `<gotchas>`, `<start>`, the structure of the strongest prompts in the Prompt Motion gallery, mapped to
  Motionsmith. One concept, a recurring element, a banned list written as `avoid -> instead`, a tempo and a bar count
  that add up, the ending, the loop decision. SKILL step 1 now writes it; a one-line request gets rewritten into it.
- **Five brief templates** (`templates/briefs/`): vertical reel with a hook, showreel (15 s, 120 BPM, 7.5 bars),
  launch, explainer (audience and a facts line: research, never invent) and seamless loop. Each is also a portable
  prompt.
- **`scripts/brief.py`**: `list`, `new` (from a template with `--set`), `check` (missing blocks and decisions,
  unfilled placeholders, bans without alternatives, bar arithmetic, explainer facts), `grid` (every beat's time and
  frame) and `plan` (concept, bans, tempo, meter, loop into plan.json; bar or beat hits added beside the recipe's
  named hits, and off-grid hits listed). English and Spanish keys.
- **AI tells**: the banned list doubles as the art director's checklist (glows without a source, bursts from nowhere,
  crossfades, bounce on everything, corner text, generic gradients, stock UI, `Math.random`).
- **Review per beat**: `sample_frames.mjs --beats`, `--bars`, `--hits` and `--beat-offset` read the plan's grid; the
  review protocol looks at the grid first.
- **`scripts/loop_check.py`**: a loop's seam measured on the MP4: pose (seam step against ordinary steps) and speed
  (pace at both ends), and the repeated-first-frame stutter.
- **Plan**: optional `concept`, `recurring_element`, `banned`, `meter`, `loop`, `audience`; `validate_plan.py
  --require-brief`.
- Explainers gain the sequence, audience and facts rules; loops the seam rules.

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
