# Motionsmith with HyperFrames

[HyperFrames](https://hyperframes.heygen.com) renders video from HTML: a composition declares its timing with
`data-*` attributes, a paused GSAP timeline (or another seekable runtime) gives the motion, and the framework owns
media, audio, preview (Studio) and render. Motionsmith renders video from pure functions of time with its own
capture tools. They meet in one place: **both seek a page to an exact instant and capture it**, so a Motionsmith piece
can run inside HyperFrames, and a HyperFrames film can carry Motionsmith shots.

Tested with HyperFrames CLI 0.8.192: a piece made with `new_piece.py --hyperframes` passes `hyperframes lint` and
`hyperframes check` with no findings and renders with `hyperframes render` (4 capture workers, BT.709 MP4); a frame
of that render and the same instant captured by `sample_frames.mjs` differ by 2/255 on average (the encoders).

## 1. Who does what

| Job | Use | Why |
|---|---|---|
| A whole film with footage, voice-over, talking heads, captions on footage, a music track, a slideshow, a website capture | **HyperFrames** (its entry skill routes to `embedded-captions`, `talking-head-recut`, `music-to-video`, `general-video`, `slideshow`…) | It owns media decoding, audio mixing, sub-compositions, Studio, cloud and batch renders |
| DOM layout, GSAP choreography of HTML elements, registry blocks | **HyperFrames** | Its runtime and lint are built for it |
| A hero shot that needs **real motion blur** (sub-frame shutter samples), **HDR light and bloom**, halation, screen print, CRT, glass | **Motionsmith** | HyperFrames' own rule says real motion blur is not available to a seeked renderer and fakes it (`motion-blur-streak`); `kit/stage.js` integrates the shutter for real |
| Kinetic type with per-letter physics, variable-font weight and width animation, face cycling on a 12 fps grid | **Motionsmith** (`kit/kinetic-type.js`, the font kit) | Canvas 2D per glyph, deterministic |
| Sound design without music, built from the beats | **Motionsmith** (`build_soundtrack.py`) | Synthesised from the plan's `hits`, measured to a loudness target |
| Measuring: determinism, curves, sync, export | **Both**: `hyperframes check` for the film; `determinism_check`, `motion_curves`, `audio_check`, `verify_export` for the shot | Different questions |
| Taste, review, right first time | **Motionsmith** profiles and review protocol, applied to either | The rules do not depend on the renderer |

When a HyperFrames project or workflow is in play (there is a `hyperframes.json`, a HyperFrames skill is active, or
the person asks for HyperFrames), **HyperFrames owns the film**: follow its entry skill for intake, structure and
render. Motionsmith brings the craft guides, the shots that need its engine, the sound and the review.

## 2. Three ways to combine them

### A. The piece is a HyperFrames project (live, scrubbable)

```bash
python -I <skill>/scripts/new_piece.py work/quote --recipe kinetic-quote --hyperframes
# or, for an existing piece:
python -I <skill>/scripts/hyperframes.py sync work/quote
cd work/quote
npx --yes hyperframes@0.8.192 lint
npx --yes hyperframes@0.8.192 check
npx --yes hyperframes@0.8.192 preview      # Studio: scrub the Motionsmith piece on a timeline
npx --yes hyperframes@0.8.192 render --quality looks --output final/hyperframes.mp4
```

What `sync` does: copies width, height, duration and fps from `plan.json` into the root element of `index.html`
(HyperFrames reads them before any script runs, and renders at the root's `data-fps`, so the motion blur keeps the
shutter it was designed for), adds GSAP and the registration of a paused timeline
(`window.__timelines["motionsmith"]`), and writes `hyperframes.json` and a `package.json` that pins the CLI version.
`kit/hyperframes.js` turns every HyperFrames seek (the timeline and its `hf-seek` event) into `window.seek(t)`, the
same pure function `render_stream.mjs` calls, and holds HyperFrames on `window.__hf.buildReady` until fonts, plan and
shaders are ready. Motionsmith's tools still work on the same folder: they never load GSAP, so the bridge stays quiet.

**After you retime `plan.json`, run `sync` again** (or `sync --check` in a script: it exits 1 on a mismatch). A root
`data-duration` that disagrees with the plan cuts or freezes the end of the render.

### B. A rendered shot inside a HyperFrames film (the safe default)

Render the shot with Motionsmith, then place it in the film as a clip. HyperFrames decodes video with FFmpeg frame by
frame, so the clip is exact.

```bash
node <skill>/scripts/render_stream.mjs --root work/quote --out final/quote.mp4 --audio assets/soundtrack.wav
python -I <skill>/scripts/hyperframes.py clip work/quote --project my-film --start 4.5 --video final/quote.mp4 --audio assets/soundtrack.wav
```

`clip` copies the files into `my-film/assets/motionsmith/` and prints the elements to paste into the film's
`index.html`:

```html
<video id="ms-quote" class="clip" src="assets/motionsmith/quote.mp4" muted playsinline data-start="4.5" data-duration="6" data-track-index="1"></video>
<audio id="ms-quote-sound" src="assets/motionsmith/quote.wav" data-start="4.5" data-duration="6" data-track-index="11" data-volume="1"></audio>
```

- The video is `muted` and its sound is a separate `<audio>` with an `id` (HyperFrames mixes `audio[id][src]` only).
- Never put `data-start` on a wrapper around the `<video>` as well (HyperFrames lint: `video_nested_in_timed_element`).
- For a shot over footage, render it with alpha ([overlays & alpha](overlays-alpha.md)) as WebM or MOV:
  HyperFrames extracts alpha-capable sources as PNG frames. Check a rendered frame of the film over the footage.
  HyperFrames itself also renders `--format mov` (ProRes 4444) or `webm` with transparency, and `png-sequence`.
- Match the frame rate: render the shot at the film's fps, or the film resamples it.

### C. Motionsmith craft in a GSAP composition

The guides are renderer-independent. When you write GSAP inside HyperFrames:

| Motionsmith | GSAP in HyperFrames |
|---|---|
| `MotionMath.easing('power3.out')`, `expo.out`, `back.out` | The same names: `ease: 'power3.out'` |
| After Effects influence and speed ([curves](../craft/curves-graph-editor.md)) | A cubic-bezier through GSAP's CustomEase, or the nearest named ease; check the speed graph |
| Cascades ≤ 0.3 s for letters ([rhythm §5](../craft/rhythm-sync.md#5-cascades-stagger)) | `stagger: {each: 0.022}` |
| Reading budget, sizes ([kinetic typography](../craft/kinetic-typography.md)) | The same numbers; HyperFrames' `fitTextFontSize` fits a width |
| Living layer ([living layer](../craft/living-layer.md)) | A slow ambient tween on a wrapper, never on a `class="clip"` element |
| Real motion blur on a whip or a slam | Render that shot with Motionsmith (B), or accept the faked streak |
| `hits` shared by image and sound | The same times as GSAP labels and as `<audio>` starts |

## 3. Things that break a render

| Symptom | Cause | Fix |
|---|---|---|
| `missing_timeline_registry` in `hyperframes lint` | No `window.__timelines[...]` in `index.html` | `hyperframes.py sync` |
| The render ends early or holds the last frame | Root `data-duration` ≠ the plan's duration | `hyperframes.py sync` after every retime |
| Blank or black canvas in the render | The piece failed before ready (missing font, WebGL without half-float) | Run `node <skill>/scripts/determinism_check.mjs --root .` first: it reports page errors and the GPU |
| Very slow preview or render | Full motion blur (up to 64 samples a frame) on a software GPU | Draft with `MOTION_MAX_SAMPLES=8` in Motionsmith's tools; check the render summary for `software gpu` |
| `network blocked` in Motionsmith's tools | The piece loads something from the internet | Put the file in `assets/`; GSAP from the CDN is the one exception, skipped on purpose |
| Two different frames for the same time | State kept between seeks | Everything in `state(t)` must come from `t` (SKILL.md §3, rule 13) |

## 4. Check both ways

1. Motionsmith: `determinism_check`, `sample_frames` at the times that matter, `verify_export`.
2. HyperFrames: `lint`, `check`, then a render.
3. Compare one frame from each render at the same time (`sample_frames` and a frame of HyperFrames' MP4): they come
   from the same `window.seek(t)`; small differences come only from the encoders.

Related: [pipeline](pipeline.md), [overlays & alpha](overlays-alpha.md), [delivery checklist](delivery-checklist.md),
[formats & platforms](../edit/formats-platforms.md).
