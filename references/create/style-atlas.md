# Style atlas: 24 looks built with the kit

Each entry gives a palette rule, a type rule, a texture, the motion grammar (curves, cadence, transitions), the
kit calls that build the look, when to use it and when to avoid it, and the cliché to dodge. Numbers are
starting points for a 1080×1920 frame at 60 fps; test them on a phone-sized preview.

Conventions: `M` is `window.MotionMath` and `P` is `window.PostFX` ([motion-math.js](../../scripts/kit/motion-math.js),
[postfx-glsl.js](../../scripts/kit/postfx-glsl.js)). Shaders are keys of `PostFX.SHADERS`, run with
`fx.pass('name', {...})`. Bloom modes are `halo`, `physical` and `add`. Tone maps are `clip`, `shoulder`,
`reinhard` and `aces`. The plan's `mode` field takes `editorial`, `kinetic`, `diagram`, `glow` or `retro`.
For the rendering pipeline behind the calls, see [pipeline](../produce/pipeline.md).

## Index

| # | Style | Mode | Main calls |
|---|---|---|---|
| 1 | Swiss / International | diagram | `tween`, `stagger`, `layoutGlyphs` |
| 2 | Brutalist | kinetic | `steps(n)`, `posterize`, `toneMap: 'clip'` |
| 3 | Editorial collage | editorial | `followerTable`, `delay`, `lightWrap` |
| 4 | Risograph / screen print | editorial | `screenPrint`, `posterize`, `wiggle` |
| 5 | Y2K chrome | glow | `lightSweep`, `bloom` add, `spring` |
| 6 | Frosted glass | glow | `lensBlur`, `bloom` halo, `followerTable` |
| 7 | CRT / VHS | retro | `crt`, `posterize`, `shake` |
| 8 | Minimal glow | glow | `bloom` halo, `spring`, `loopValue` |
| 9 | Kinetic type poster | kinetic | `layoutGlyphs`, `stagger`, `impulse` |
| 10 | Bauhaus geometric | diagram | `arcPoint`, `loopValue`, `stagger` grid |
| 11 | Memphis | kinetic | `elastic.out`, `wiggle`, `loopValue` |
| 12 | Paper cut-out / stop-motion | editorial | `posterize(t, 12)`, `followerTable`, `squashStretch` |
| 13 | Hand-drawn scribble | kinetic | `pathSampler`, `morphPath`, `wiggle` |
| 14 | Ink and bleed | editorial | `valueNoise`, `hash`, custom pass |
| 15 | Infographic / data | diagram | `tween`, `arcPoint`, `resamplePath` |
| 16 | Isometric | diagram | `lookAt`, `project`, `stagger` |
| 17 | Cinematic noir | editorial | `toneMap: 'aces'`, `lensBlur`, `cocPx` |
| 18 | Neon | glow | `bloom` add, `halation`, `posterize` |
| 19 | Duotone photo | editorial | custom luma pass, `followerTable` |
| 20 | Analog film | retro | `grain`, `halation`, `echo` |
| 21 | Generative / particles | glow | `particle`, `rng`, `valueNoise` |
| 22 | Typographic maximalism | kinetic | `layoutGlyphs`, `echo`, `speedRamp` |
| 23 | Monochrome + one accent | any | `saturation: 0`, accent over the result |
| 24 | Terminal monospace | retro | `loop`, `hash`, `posterize` |

## The looks

### 1. Swiss / International
- **Palette:** paper or white, black ink, one accent with one meaning. No gradients.
- **Type:** one grotesk, flush left, on a visible 12-column grid. Numbers and hairline rules are graphic elements.
- **Texture:** none. Flat fills and rules of 2–4 px.
- **Motion:** entries with `cubic.out` in 12–20 f; exits at 65–75 % of the entry. One element moves per beat. Hard cuts between grid states.
- **Use / avoid:** explanations, lists of facts, numbers. Avoid when the piece must feel mysterious or handmade.
- **Cliché:** every element slides in from the left on the same ease.

### 2. Brutalist
- **Palette:** black, white and one loud colour at full saturation. No tints.
- **Type:** heavy grotesk or condensed sans at poster size. The text fills the frame. No tracking.
- **Texture:** none, or a photocopy grain no stronger than `finish({grain: .01})`.
- **Motion:** hard cuts. Stepped objects with `M.easing('steps(6)')`; type enters over 2–3 f with no easing. Hits become shakes.
- **Build:** `M.posterize`, `M.stepped`, `M.impulse`, `finish({toneMap: 'clip'})`.
- **Use / avoid:** a manifesto, a stance, one hard claim. Avoid gentle or explanatory content.
- **Cliché:** a black box with white text on a stock layout, called "bold".

### 3. Editorial collage
- **Palette:** paper, muted photo tones, one accent taken from the paper or the object. Shadows take the colour of the light.
- **Type:** a serif or grotesk headline over the cut-outs. Captions at 42 px or more on a 1080 frame.
- **Texture:** real paper scans as assets. Grain at 0.015 at most.
- **Motion:** layered entries 4–10 f apart (`M.delay`). Parallax between planes: the back plane moves at 0.2–0.4 × the front. An object follows its target with `M.followerTable` (lag 0.1–0.3 s).
- **Build:** `M.followerTable`, `M.delay`, `M.arcPoint`, `P.SHADERS.lightWrap` (amount 0.2–0.6), `M.squashStretch`.
- **Use / avoid:** archives, documentary, objects that tell a story. Avoid abstract data: collage then reads as random.
- **Cliché:** the same drop shadow under every cut-out.

### 4. Risograph / screen print
- **Palette:** two spot inks on warm paper, for example a bright red and a near-black.
- **Type:** any face. Small text is never screened: draw it in solid ink above the pass.
- **Texture:** `screenPrint` with `inks: 2`, a `cell` of at least 6 px at 1080 wide, and misregistration of 3–5 px.
- **Motion:** the ink boils at 12 fps, because the seed steps at 12 fps. The object may run at 12 fps too (hybrid).
- **Build:** `fx.pass('screenPrint', …)` after `finish`; `M.posterize(t, 12)` for the seed; `M.wiggle` for drift.
- **Use / avoid:** zines, gigs, anything that should feel printed. Avoid small text, and textures at 60 fps: they read as video noise.
- **Cliché:** halftone dots on everything.

### 5. Y2K chrome
- **Palette:** silver and grey, with a saturated reflection band (cyan to magenta, or blue to lilac). Black background.
- **Type:** a wide or rounded sans. The highlight comes from light, not from a bevel filter.
- **Texture:** specular bands, one `lightSweep` per beat.
- **Motion:** springs with ζ 0.3–0.5; squash and stretch up to 14 %; sparkles from `M.particle`.
- **Build:** `P.SHADERS.lightSweep` before the bloom; `bloom(…, {threshold: 1.0})` and `finish({bloomMode: 'add'})`; `M.spring`; `M.squashStretch`.
- **Use / avoid:** playful products, nostalgia. Avoid calm explanations.
- **Cliché:** a glossy sphere with a fake reflection.

### 6. Frosted glass
- **Palette:** a deep neutral (around #121214 to #1a1a1d), white or grey frost, one emissive accent on the part that carries the meaning.
- **Type:** a light sans, sitting on the glass or behind it.
- **Texture:** refraction of a blurred background (`lensBlur`), and light wrap at the edges.
- **Motion:** slow. A lens follower with `M.followerTable` (for example ω = 2π·1.7 rad/s, ζ = 0.5). Text does not overshoot. Traversals use `power2.inOut`.
- **Build:** `P.SHADERS.lensBlur` (radius, rim, chroma), `bloom` in `halo` mode, `lightWrap`, `followerTable`, `project` for depth.
- **Use / avoid:** products, interfaces, lens metaphors. Avoid a busy photo behind text.
- **Cliché:** a blurred rectangle with a white border. Glass must refract something.

### 7. CRT / VHS
- **Palette:** phosphor-tinted colours with chromatic misregistration, one warm white, black tube edges.
- **Type:** a mono or pixel face, drawn on a small canvas and enlarged with nearest-neighbour filtering. On-screen display in boxes.
- **Texture:** scanlines (a period of 3 px at 1080 wide; test at 720), an RGB mask, vignette and barrel distortion.
- **Motion:** the subject steps at 12 fps, with hard jumps, a tracking band and shakes on hits. No motion blur on glitch frames.
- **Build:** `P.SHADERS.crt`; `M.posterize`; `M.shake` and `M.impulse`; `M.hash` for glitch rows. Full two-pass recipe: [retro looks](../craft/retro-looks.md).
- **Use / avoid:** retro narrative, a found tape, tech nostalgia. Avoid when the content must be read at speed.
- **Cliché:** rolling bars and random glitches everywhere. Glitch is punctuation, not texture.

### 8. Minimal glow
- **Palette:** a charcoal background, white and grey shapes built from layers, one accent on the part that carries the meaning.
- **Type:** small, lowercase sans. Few words.
- **Texture:** none. The light is the texture (halo bloom).
- **Motion:** `back.out` entries for shapes, or `spring` for small objects. One pulse at the end. Ambient drift within ±4 px.
- **Build:** `finish({bloomMode: 'halo', strength: 0.25–0.45})` on `bloom(…, {levels: 6})`; `M.spring`; `M.loopValue` for the drift.
- **Use / avoid:** concept pieces, explainers around one object. Avoid text-heavy scenes: glow on type lowers contrast.
- **Cliché:** glow on every element. Glow belongs to emitters.

### 9. Kinetic type poster
- **Palette:** two or three colours. Ink on paper, or paper on ink. The accent colours one word.
- **Type:** display at 280–490 px for one word, 100–150 px for a multi-line title, 48–64 px for support ([size table](../craft/kinetic-typography.md#5-legibility-on-a-phone)).
- **Texture:** none, or light grain.
- **Motion:** cascades of 1–2 f per letter (at most 0.3 s in total). Masks. Hits drive shakes. The exit waits for `readingTime`.
- **Build:** `M.layoutGlyphs`, `M.stagger`, `M.impulse`, `M.shake`, `M.readingTimeChars`, `M.easing('expo.out')`.
- **Use / avoid:** one phrase that must land. Avoid paragraphs.
- **Cliché:** letters bouncing in one by one, with the same stagger for every word.

### 10. Bauhaus geometric
- **Palette:** a red, blue and yellow trio with black and white. One colour per shape.
- **Type:** a geometric sans, minimal, set on the grid.
- **Texture:** flat. No grain.
- **Motion:** mechanical arcs, rotations in `loop` cycles, a grid cascade, `expo.inOut` for turns. No bounce.
- **Build:** `M.arcPoint`, `M.loopValue` in `'cycle'` mode, `M.pathSampler`, `M.stagger` with `grid`, `M.easing('expo.inOut')`.
- **Use / avoid:** systems, structures, education. Avoid emotional content.
- **Cliché:** a circle, a square and a triangle turning in a loop with no information.

### 11. Memphis
- **Palette:** pastels with black and one hot colour. Patterns: dots, squiggles, triangles.
- **Type:** a heavy geometric sans with mixed weights.
- **Texture:** patterns as flat shapes, not as noise.
- **Motion:** springy entries with `elastic.out` or `back.out`. Squiggles traced with `M.wiggle`. Patterns scroll with `loopValue` in `'offset'` mode.
- **Build:** `M.easing('elastic.out')`, `M.wiggle`, `M.loopValue`, `M.stagger` with `grid`.
- **Use / avoid:** playful, young, fashion. Avoid solemn subjects.
- **Cliché:** squiggles stuck on everything.

### 12. Paper cut-out / stop-motion
- **Palette:** paper tones. Shadows are a darker paper, not black.
- **Type:** hand-cut letters or a serif. Cut edges are shapes, not filters.
- **Texture:** paper grain that steps at 12 fps.
- **Motion:** stepped at 12 fps. Squash and stretch of at most 5 %. Followers for drag. Hard cuts. One frame of anticipation before each move.
- **Build:** `M.posterize(t, 12)`, `M.stepped`, `M.followerTable`, `M.squashStretch`, `M.delay`.
- **Use / avoid:** handmade, nostalgic, gentle. Avoid crisp tech.
- **Cliché:** random jitter on everything, which reads as a filter.

### 13. Hand-drawn scribble
- **Palette:** ink on paper, with one coloured highlight.
- **Type:** a marker or handwritten face. Underlines as strokes.
- **Texture:** line wobble. The paper stays still.
- **Motion:** strokes drawn along a path (a partial length of `pathSampler`). Wobble with `M.wiggle`, stepped at 12 fps. Shape changes with `alignPaths` and `morphPath`.
- **Build:** `M.pathSampler`, `M.resamplePath`, `M.alignPaths`, `M.morphPath`, `M.wiggle`, `M.posterize`.
- **Use / avoid:** explainers with a friendly tone. Avoid data.
- **Cliché:** a fake marker with random noise on the line.

### 14. Ink and bleed
- **Palette:** black ink on warm paper, with a lighter second ink for the bleed.
- **Type:** a serif or a display face with ink-like terminals.
- **Texture:** bleeding edges, and paper.
- **Motion:** reveals by a rising noise threshold (the spread), timed with `sine.inOut`. Little or no overshoot.
- **Build:** `M.valueNoise` and `M.hash` for the threshold, `M.easing('sine.inOut')`, and a custom shader pass (the kit does not bundle one).
- **Use / avoid:** literary, mysterious pieces. Avoid fast content.
- **Cliché:** blotchy noise edges on every cut.

### 15. Infographic / data
- **Palette:** neutrals with one accent per series. Axes and labels at 4.5:1 contrast or better. Never use a red and green pair as the only signal.
- **Type:** a sans with tabular figures. Labels at 42 px or more.
- **Texture:** none.
- **Motion:** linear connectors. `power2.inOut` for bars and counts. One series at a time. No overshoot on data.
- **Build:** `M.tween`, `M.stagger`, `M.layoutGlyphs`, `M.arcPoint` for connectors, `M.resamplePath` for a stroke drawn in order.
- **Use / avoid:** a relation between numbers. Avoid decoration that only looks like a chart, and numbers without a source.
- **Cliché:** count-ups that land on a round figure with no source.

### 16. Isometric
- **Palette:** three tones per object (lit, side, shadow) and a background. One accent on the active part.
- **Type:** a sans on the iso plane, or flat over it.
- **Texture:** flat shading.
- **Motion:** slides along the three axes with ease-in-out. Stacks build with `stagger` from `'start'`. A 90° turn in 1–1.5 s.
- **Build:** `M.lookAt` and `M.project`. Place the camera far away, so depth changes the scale very little. `M.stagger`, `M.easing('power2.inOut')`.
- **Use / avoid:** systems, products, processes. Avoid organic content.
- **Cliché:** the isometric cube grid.

### 17. Cinematic noir
- **Palette:** near-monochrome: black and warm white, with at most one cool or warm accent. High contrast.
- **Type:** a condensed serif or a typewriter face, with shadows over the text.
- **Texture:** grain at 0.02–0.03 per frame. A faint light leak from `lightSweep` at low strength.
- **Motion:** push-ins of 0.8–2 s with ease-in-out. Rack focus of 0.5–1.2 s. Long holds. Few hits.
- **Build:** `finish({toneMap: 'aces', vignette: 0.3, grain: 0.025})`; `P.cocPx` with `P.SHADERS.lensBlur` for depth of field; `M.easing('power2.inOut')`.
- **Use / avoid:** drama, mystery, documentary. Avoid bright explainers.
- **Cliché:** a teal and orange grade on everything.

### 18. Neon
- **Palette:** black, with one or two saturated neons (pink, cyan).
- **Type:** a thin geometric sans. Glow on the outline, not the fill.
- **Texture:** none. The glow is the texture; halation adds warmth.
- **Motion:** a buzzing flicker from `posterize` at 10–14 fps, otherwise steady. Hits as power-ups.
- **Build:** `bloom(…, {threshold: 1.2, knee: 0.5})`; `finish({bloomMode: 'add', strength: 1–4, halation: 1–2.5})`; `M.posterize`; `M.hash`.
- **Use / avoid:** nightlife, tech, playful openers. Avoid pieces that need long reading.
- **Cliché:** a wobbling neon outline around everything.

### 19. Duotone photo
- **Palette:** two inks mapped by luminance: a dark ink for shadows, a light ink for highlights.
- **Type:** one ink, sans or serif, over the photo.
- **Texture:** the photo's own grain. No added texture.
- **Motion:** a slow pan or zoom across the photo (at most 5 % scale over 3–4 s). Text enters over 12–18 f. Push-ins with ease-in-out.
- **Build:** a luminance-to-ink fragment shader passed to `fx.pass` as raw GLSL (about four lines), and `M.followerTable` for a parallax crop.
- **Use / avoid:** archive photos, portraits. Avoid products, where colour is the message.
- **Cliché:** a flat duotone with a gradient overlay on every photo.

### 20. Analog film
- **Palette:** warm highlights and cool shadows (split tone), halation at bright edges.
- **Type:** a film-era serif or grotesk, with a slight bloom.
- **Texture:** grain at 0.02–0.03 per frame, with light leaks used sparingly.
- **Motion:** gate weave as a 1–2 px wobble. Ghosting with echoes. Optionally, a 24 fps cadence for the camera only.
- **Build:** `finish({halation: 1.2, grain: 0.025, aberration: 0.004, lift, gamma, gain})`; `M.wiggle` for the weave; `M.echo`; `M.posterize(t, 24)`.
- **Use / avoid:** documentary, nostalgia. Avoid crisp tech.
- **Cliché:** dust and scratches as random overlays.

### 21. Generative / particles
- **Palette:** one or two hues on a dark or light field, with colour mapped by noise.
- **Type:** sparse, or none. If used, mono.
- **Texture:** the particles are the texture. Grain low.
- **Motion:** continuous flows (a `valueNoise` field gives the direction). Particles with lifetimes. Bursts on hits with `M.impulse`.
- **Build:** `M.particle(i, t, {life, seed})`, `M.rng`, `M.hash`, `M.valueNoise`, `M.halton`, and `M.exposureTimes` for particle blur.
- **Use / avoid:** abstract transitions, music-led pieces. Avoid when a message must be read.
- **Cliché:** thousands of particles on a gradient, with no structure.

### 22. Typographic maximalism
- **Palette:** three or four colours with strong contrast. One dominant.
- **Type:** two or three roles, a scale contrast of 4:1 or more, overlapping layers.
- **Texture:** none, or print.
- **Motion:** layered cascades on a grid, echoes of 3–5 copies, `speedRamp` for rhythm. Density must fit the reading budget.
- **Build:** `M.layoutGlyphs`, `M.stagger` with `grid`, `M.echo`, `M.speedRamp`, `M.readingTime`.
- **Use / avoid:** energetic posters, fast messages. Avoid pieces that explain something.
- **Cliché:** every word at the same size, shouting at once.

### 23. Monochrome + one accent
- **Palette:** greys plus one accent that carries meaning. The accent is composed after the tone map, so it keeps its exact colour.
- **Type:** one family in two weights.
- **Texture:** none, or one.
- **Motion:** one easing family for the whole piece. The accent moves only when it speaks.
- **Build:** `finish({saturation: 0})` for the grey layer, then the accent over the result with a plain alpha pass (the top-layer pattern in [the starter](../../templates/starter/piece.js)).
- **Use / avoid:** any brief that needs focus, and the default when unsure. Avoid briefs that ask for variety.
- **Cliché:** the accent on three elements at once, so nothing is accented.

### 24. Terminal monospace
- **Palette:** a dark grey background, one phosphor-like text colour, one alert colour.
- **Type:** a monospace on a fixed cell grid, with a block cursor.
- **Texture:** light scanlines, or none.
- **Motion:** typing at 12–30 characters per second. Scrambled glyphs from `M.hash` until their cue. Cursor blink at 2–5 Hz.
- **Build:** `M.loop` for the blink, `M.hash` for the scramble, `M.posterize` for the cadence, `M.layoutGlyphs` for the cell grid.
- **Use / avoid:** code, systems, notes. Avoid emotional content.
- **Cliché:** green text with random characters and a blinking underscore.

## Mixing rules

- Two styles at most. One owns type, one owns texture, and motion comes from one of them.
- A style must do a job in the piece, not only sit in the palette.
- One primary texture per piece. A second texture is a subtle layer at most.

## Two passes, as code

The print pass runs after `finish`, because the tone-mapped image is already in sRGB:

```js
fx.finish(scene, bloom, {to: tmp, toneMap: 'shoulder'});
fx.pass('screenPrint', {textures: {image: tmp}, uniforms: {
  res: [W, H], paper: [.95, .94, .91], inkA: [1, .27, .18], inkB: [.08, .08, .09],
  inks: 2, cell: 10, angleA: .26, angleB: .785,     // 10 px dots; ink A at 15°, ink B at 45°
  offA: [4, -3], offB: [-1, 1],                     // misregistration in px
  texture: .6, seed: Math.round(M.posterize(t, 12) * 12),   // the ink boils at 12 fps
  strength: 1}});                                   // 0.25–0.4 is a subtle print layer
```

The CRT pass takes the same shape. The values are starting points:

```js
fx.pass('crt', {textures: {image: tmp}, uniforms: {curvature: .12, scanline: .35, grille: .25, vignette: .35}});
```
