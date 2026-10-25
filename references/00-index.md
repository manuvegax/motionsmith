# Index: what to read when

Find the row that describes the request or the symptom. The guide says what to do; the tool says how to check it.
Profiles (project and personal) override every default here: read them first ([SKILL §0](../SKILL.md#0-load-the-taste-first)).

## 1. By request or symptom

| Request or symptom | Read | Check with |
|---|---|---|
| "Make me a piece about X" (from zero) | [Ideation](create/ideation.md) → [art direction](create/art-direction.md) → [story structures](edit/story-structures.md) | Three critics ([review protocol §3](produce/review-protocol.md#3-the-three-critics)) |
| "It looks the same / static / needs more dopamine" | [Pacing & retention](edit/pacing-retention.md), [living layer](craft/living-layer.md) | Walk every 0.5 s: no two samples alike |
| "Looks like a template", generic | [Direction §12](craft/direction-choreography.md#12-frequent-errors-and-the-first-fix), [style atlas](create/style-atlas.md) | Compared direction gate |
| Robotic, constant speed | [Curves §2](craft/curves-graph-editor.md#2-influence-and-speed-easy-ease-and-snappy-curves) | `motion_curves.py` (peak/mean ≈ 1 gives linear away) |
| Floaty, slow, indecisive | [Principles §1](craft/principles.md#1-starting-durations-at-60-fps), ease-out on entrances | Duration in frames vs the table |
| Dead: correct but lifeless | [Principles §2](craft/principles.md#2-the-twelve-one-by-one): anticipation, follow-through, overshoot | Dense window on arrivals |
| Flat, cut-outs glued on | Light wrap ([light §4](craft/light-bloom.md#4-halation-light-wrap-flares-and-leaks)), parallax ([camera §3](craft/camera-space.md#3-focal-length-perspective-and-parallax)), shadows | Dense window over light and dark |
| Static or nauseating camera | [Camera & space](craft/camera-space.md) | Dumped camera curves |
| Unreadable or fleeting text | [Kinetic type](craft/kinetic-typography.md), [captions & titles](edit/captions-titles.md) | First sharp frame + `readingTime` |
| Play with typography | [Kinetic type §3](craft/kinetic-typography.md#3-the-operations-menu) (font cycling, glitch, echoes, stacks), [variable type](craft/kinetic-typography.md#3b-variable-fonts-weight-and-width-in-motion) | Every face loaded (`determinism_check --font`) |
| Weight or width animation, "the letters breathe" | [Kinetic type §3b](craft/kinetic-typography.md#3b-variable-fonts-weight-and-width-in-motion): Archivo in the font kit | A sheet of the landing at 12 fps |
| Cuts feel random | [Cutting](edit/cutting.md) | Each cut has a written job |
| A transition | [Transitions atlas](edit/transitions-atlas.md), [direction §5](craft/direction-choreography.md#5-continuity-that-produces-a-reveal) | Dense window on the cut |
| Video inside letters, reveal by shape | [Layers §2](craft/layers-effects.md#2-mattes-and-masks) | Matte edges at full size |
| "How do I do After Effects effect X?" | [Layers §5](craft/layers-effects.md#5-after-effects-effects-and-their-equivalent) | — |
| More blur, ghosts, depth of field | [Blur](craft/blur.md) | Same peak with/without blur |
| Glow, washed out or burnt | [Light §1 and §3](craft/light-bloom.md#3-threshold-free-bloom-vs-thresholded-bloom) | Pixels at 255 in the MP4; greyscale |
| "Film look" | Light §5 (ACES), 180° blur, grain, halation, [color grade](edit/color-grade.md) | Technique lab F and G |
| Screen print, riso, halftone texture | [Print & textures](craft/print-textures.md) | Full-size MP4 frame and a 720 downscale |
| Frame-rate lag, on twos, 12 fps, stop-motion | [Stepped time](craft/stepped-time.md) | Consecutive frames: the pose repeats and jumps |
| Slow motion with character, ramps, echo | [Stepped time §3–4](craft/stepped-time.md#3-speed-ramps) | `motion_curves.py` on the trajectory |
| Retro, glitch, VHS, CRT | [Retro looks](craft/retro-looks.md) | Sheet of the glitch stretch |
| Glass, lenses, 3D layers in WebGL | [Glass & WebGL](craft/glass-webgl.md) | Full-size crops of the material |
| React to audio | [Rhythm §4](craft/rhythm-sync.md#4-audio-reactive-motion) | `audio_envelope.py` |
| Out-of-sync hits | [Rhythm §3](craft/rhythm-sync.md#3-one-list-of-hits), [sound design §5](craft/sound-design.md#5-sync) | `audio_check.py --plan` |
| Cut to music | [Music editing](edit/music-editing.md) | Beat grid in the plan |
| Sound without music | [Sound design](craft/sound-design.md) | `build_soundtrack.py`, `audio_check.py` |
| A specific scene (logo reveal, lower third, data reveal…) | [Scene recipes](create/scene-recipes.md), `templates/recipes/` | `determinism_check` on the recipe |
| A style ("brutalist", "Swiss", "Y2K"…) | [Style atlas](create/style-atlas.md) | Style frames sequence |
| A HyperFrames project, film or workflow; "put this in my HyperFrames video" | [HyperFrames](produce/hyperframes.md) (HyperFrames owns the film) | `hyperframes.py sync --check`, `npx hyperframes check` |
| Several scenes with motivated transitions (a promo, an intro) | `templates/recipes/promo-sequence`, [cutting](edit/cutting.md), [transitions atlas](edit/transitions-atlas.md) | Dense window on each cut |
| Render takes too long | [Pipeline §3](produce/pipeline.md#3-time-and-sub-sampling): `MOTION_MAX_SAMPLES=8` drafts, or HyperFrames' parallel render | The draft flag in `motionConfig` |
| "Network blocked" in a capture | The piece must load only its own files ([pipeline](produce/pipeline.md)) | `sample_frames` errors list |
| Study a reference | [Reference study](create/reference-study.md) | `inspect_video.py`, `watch_reference.py` |
| Another platform or aspect ratio | [Formats & platforms](edit/formats-platforms.md) | `new_piece.py --format …`, `verify_export.py` |
| Transparent overlay | [Overlays & alpha](produce/overlays-alpha.md) | `alphaextract` and composites |
| Render, export, colour | [Pipeline](produce/pipeline.md) | `verify_export.py --require-cfr --require-bt709` |
| Is it ready? | [Review protocol](produce/review-protocol.md), [quality rubric](produce/quality-rubric.md), [delivery checklist](produce/delivery-checklist.md) | All of the above |

## 2. Choosing with the technique lab

The technique lab (`templates/technique-lab/`) shows each technique with a code (A1, D3, F2, J2, K4…). Render it with
`node <skill>/scripts/render_stream.mjs --root <skill> --page templates/technique-lab/index.html --out <absolute path
outside the skill>/technique-lab.mp4 --no-audio` (a relative `--out` would land inside the installed skill, which the
next install replaces), let the person watch it on the target device, and record the codes they choose in their profile. Those choices then override the defaults of the guides.

## 3. After Effects or code?

Motionsmith does everything in code: deterministic, reviewable, versionable, no subscriptions or paid plugins, and
the essentials of After Effects (sub-frame motion blur, HDR glow, glass, 3D camera, mattes, expressions, time effects)
are covered. Reopen the question for real footage that needs tracking or rotoscoping, character rigs, heavy 3D with
plugins, hand retouching by a person, or a client who requires a `.aep`.
