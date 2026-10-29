# Index: what to read when

Find the row that describes the request or the symptom. The guide says what to do; the tool says how to check it.
Profiles (project and personal) override every default here: read them first ([SKILL §0](../SKILL.md#0-load-the-taste-first)).

## 1. By request or symptom

| Request or symptom | Read | Check with |
|---|---|---|
| "Make me a piece about X" (from zero) | [Motion brief](create/motion-brief.md) → [ideation](create/ideation.md) → [art direction](create/art-direction.md) → [story structures](edit/story-structures.md) | `brief.py check`, then the three critics ([review protocol §3](produce/review-protocol.md#3-the-three-critics)) |
| A one-line prompt ("make a dynamic 15-second motion video"), or a prompt written for another tool | [Motion brief §2 and §7](create/motion-brief.md#2-the-six-blocks): rewrite it into six blocks, show the missing decisions | `brief.py check` |
| A showreel, a launch film, an explainer, a loop | [Motion brief §6](create/motion-brief.md#6-by-kind-of-piece), `templates/briefs/` | `brief.py new --template …` then `check` |
| "Looks AI-made": glows, bursts, crossfades, bouncy, corner text | [Motion brief §3](create/motion-brief.md#3-the-banned-list): the banned list with its alternatives | The art director's critic against the list |
| Cuts off the music, tempo arithmetic, "how many bars fit" | [Motion brief §4](create/motion-brief.md#4-tempo-bars-and-the-arithmetic) | `brief.py grid`, then `sample_frames.mjs --beats` |
| The loop jumps or stutters at the seam | [Story structures §6](edit/story-structures.md#6-loop), [motion brief §5](create/motion-brief.md#5-review-per-beat-and-the-loop) | `loop_check.py` |
| "It looks the same / static / needs more dopamine" | [Pacing & retention](edit/pacing-retention.md), [living layer](craft/living-layer.md) | Walk every 0.5 s: no two samples alike |
| "Looks generic, not like After Effects", flat, ugly | [Editorial collage](create/editorial-collage.md): matter, depth, mixed type, carriers; `--recipe editorial-collage` | A frame per scene next to the references: matter, depth, one hero |
| Study a reference video properly (frames at each cut) | [companions/README.md](../companions/README.md): Motion Architect's vision engine | Its report's frame paths, read one by one |
| A palette or a type pairing for a mood | Motion Architect's design engine (`search.py ... --domain color/typography/style`) | Contrast and the brand profile |
| "Looks like a template", generic | [Direction §12](craft/direction-choreography.md#12-frequent-errors-and-the-first-fix), [style atlas](create/style-atlas.md) | Compared direction gate |
| "It goes flat for a few seconds", frozen ending, dead hold | [Living layer §3b](craft/living-layer.md#3b-moving-holds-the-motion-that-never-stops): residual drift, scene breathing | `hold_check.py final/x.mp4 --curve` |
| An effect: glow, echo, RGB split, light sweep, tint | [Keyframes & cuts §4b](craft/keyframes-and-cuts.md#4b-layer-effects) | A frame where the effect has its reason |
| The whole feel: snappier, calmer, more sober | [Keyframes & cuts §4c](craft/keyframes-and-cuts.md#4c-motion-styles): `Comp.style()` | One style per piece |
| "Does not feel like After Effects": keys, offsets, cuts | [Keyframes & cuts](craft/keyframes-and-cuts.md): `kit/comp.js` (named eases, overshoot keys, parenting, precomps, transitions with a swap under the hit) | Speed graphs peak early; no frame with two half-transparent scenes |
| A transition looks like a dissolve | [Keyframes & cuts §4](craft/keyframes-and-cuts.md#4-cuts-scenes-hand-over): swap on the half under a flash | `sample_frames.mjs --frames` across the cut |
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
| "Which hook works?", trial reels, A/B of the opening | [Motion brief §8](create/motion-brief.md#8-hook-variants-for-trial-reels): `hooks:` + `seam:`, `hook_variants.py` | Seam difference < 0.5; `final/hooks/hooks.md` after 24–48 h |
| A talking-head recording to edit (a person to camera + inserts), "people leave in the first 3 seconds" | [Talking-head edits](edit/talking-head.md): load the toolchain at once, ask once, the pipeline, the opening | `gaze_check.py` on the take and the final file; `verify_export.py`; `audio_check.py` (mono, phase) |
| The speaker looks down, blinks on a seam, or the last word is cut | [Talking-head edits §3](edit/talking-head.md#3-the-pipeline) | `gaze_check.py`; the last word measured in the waveform |
| B-roll from different sources looks pasted on; "needs the same finish", frame-rate lag on footage | [Talking-head edits §5](edit/talking-head.md#5-b-roll-that-belongs-one-finish-many-methods) | `print_footage.py` |
| A dense edit feels robotic | [Talking-head edits §6](edit/talking-head.md#6-pace-without-sounding-robotic) | Cuts listed with their reason |
| Clips or photos under a voice, B-roll, archive, Ken Burns, parallax | [B-roll](edit/broll.md): `broll.py`, `--recipe broll-story` | `sample_frames.mjs --cuts`; `broll.py credits` |
| Is this image allowed? Licence, credit, provenance | [B-roll §1](edit/broll.md#1-provenance-before-anything) | `assets/broll/provenance.json` |
| Clips from different sources do not match | [B-roll §4](edit/broll.md#4-one-grade-for-every-source): one grade in `timeline.json` | A sheet with one frame per shot |
| A ghost of the previous shot on a cut frame | [B-roll §5](edit/broll.md#5-cuts-on-footage): choose the scene from the frame, not the sub-sample | `sample_frames.mjs --cuts --png` |
| A niche: psychology, education, data, lists, podcasts, documentary, tutorials, fitness | [Niches](create/niches.md): hook, structure, banned list and the recipe to start from | The brief's banned list includes the niche row |
| A chart from numbers, a top N, a process diagram, a podcast clip | `--recipe chart-bars`, `ranking`, `step-diagram`, `audiogram` ([niches §5](create/niches.md#5-recipes-added-for-niches)) | Edit `data.json`, not the code |
| Cut to music | [Music editing](edit/music-editing.md) | Beat grid in the plan |
| A piece told by a voice, narration, "voz en off" | [Voice-over](edit/voiceover.md): two-column script, `voice_plan.py`, `--recipe voice-captions` | `sample_frames.mjs --cuts --hits`, `voice_over_bed_db` ≥ 10 |
| The voice is buried, music over the words | [Voice-over §5](edit/voiceover.md#5-the-mix): the `voiceover` cue ducks the rest | `build_soundtrack.py` report |
| Captions for a voice: fast, bad breaks, ending on «de» | [Voice-over §3](edit/voiceover.md#3-what-voice_plan-decides-and-why), `captions.py --preset voice` | captions.json warnings |
| Sound without music | [Sound design](craft/sound-design.md) | `build_soundtrack.py`, `audio_check.py` |
| A specific scene (logo reveal, lower third, data reveal…) | [Scene recipes](create/scene-recipes.md), `templates/recipes/` | `determinism_check` on the recipe |
| A style ("brutalist", "Swiss", "Y2K"…) | [Style atlas](create/style-atlas.md) | Style frames sequence |
| A HyperFrames project, film or workflow; "put this in my HyperFrames video" | [HyperFrames](produce/hyperframes.md) (HyperFrames owns the film) | `hyperframes.py sync --check`, `npx hyperframes check` |
| Several scenes with motivated transitions (a promo, an intro) | `templates/recipes/promo-sequence`, [cutting](edit/cutting.md), [transitions atlas](edit/transitions-atlas.md) | Dense window on each cut |
| Render takes too long, a long piece (20–90 s) | [Pipeline §3b](produce/pipeline.md#3b-long-pieces-parallel-chunks-that-resume): `render_parallel.mjs --workers 3`; `MOTION_MAX_SAMPLES=8` for drafts | The report's `speedup_vs_one_worker` |
| A render died halfway | `render_parallel.mjs`: run the same command again, finished chunks are reused | `reused_chunks` in the report |
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
