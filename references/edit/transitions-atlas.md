# Transitions atlas

A transition is a join with a length. A hard cut is a transition of 0 frames. Every entry below gives when to use it, its length in frames at 60 fps (seconds × 60), a recipe built from the existing kit, and how it fails. Recipes assume `MotionMath` (`motion-math.js`) and `PostFX` (`postfx-glsl.js`) are loaded, and that `plan.hits` is the shared beat list (see [plan-schema.md](../produce/plan-schema.md)).

Shared helper for every timed join:

```js
// Progress 0 → 1 of a join that starts at t0 and lasts `frames` frames at 60 fps.
const progress = (t, t0, frames, spec = 'power2.inOut') =>
  MotionMath.tween(t, t0, t0 + frames / 60, 0, 1, spec);
```

Every transition is a pure function of `t`. Nothing is kept between frames, so any frame can be rendered alone.

## 1. Cut-based (0–7 frames)

| Transition | Use when | Frames @ 60 | Recipe | Fails when |
|---|---|---|---|---|
| Hard cut | The eye has read the outgoing shot | 0 | `t < t0 ? A(t) : B(t - t0)` | The outgoing shot is not read yet |
| Smash cut | Calm to loud, or one emotion to the next | 0, plus a hit | `MotionMath.impulse(t, plan.hits)` on B's first 4–6 frames | The calm side lasts under about 30 frames |
| Graphic match | One shape, colour or position carries across | 0 | Same parameters on both sides at `t0` (see [cutting.md](cutting.md)) | Off by more than about 10 px at 1080 wide |
| Action match | A movement continues | 0 | Shared velocity at `t0` through `MotionMath.tween` on both sides | The speed changes on one side |
| J or L cut | The sound carries the scene change | 0 picture; 6–30 sound | Sound offset in the mix, picture unchanged | Used on a hit: reads as desync |
| Jump cut | Same subject, time skipped | 0 | Move at least 10 % of the frame width, or scale by 1.25× | A small move reads as a glitch |
| Flash cut | Strong emphasis on one beat | 2–3 | `fx.finish(scene, null, {exposure: 1 + 3 * MotionMath.impulse(t, plan.hits, 20)})` | More than three flashes in a second |

## 2. Camera (6–120 frames)

| Transition | Use when | Frames @ 60 | Recipe | Fails when |
|---|---|---|---|---|
| Push-in | A lead into a detail | 30–90 | `s = MotionMath.tween(t, t0, t1, 1, 1.25, 'power2.inOut')` on the group | Scales the type with no parallax; reads as zoom |
| Dolly zoom | Unease, a shift of perspective | 60–120 | Eye distance and `focal` move in opposite directions in `MotionMath.project` | No matching focal change: reads as a plain zoom |
| Whip pan | A fast change of place | 6–12 at the peak | `PostFX` `directionalBlur` (recipe A) | Longer than about 12 frames smears the frame |
| Zoom whip | Energy on a hit | 8–16 | `PostFX` `radialBlur`, `spin: {int: 0}` (recipe B) | The centre is off the subject |
| Spin whip | A change of mode | 10–18 | `radialBlur` with `spin: {int: 1}`, amount 0.1–0.3 rad | Large amounts tear the frame edge |
| 3D rotation | A reveal of a surface | 30–60 | Eye moved along `MotionMath.arcPoint`, `MotionMath.lookAt` each frame | Crosses the 180° line (see [cutting.md](cutting.md)) |
| Impact shake | A hit | 6–12 | `MotionMath.shake(t, plan.hits, {px: 8})` | Shakes small type; keep text under about 1 % |
| Handheld drift | Life, documentary feel | Continuous | `MotionMath.wiggle(t, {freq: 0.5, amp: 4})` | Too much reads as a failing render |

## 3. Mask and shape (8–36 frames)

| Transition | Use when | Frames @ 60 | Recipe | Fails when |
|---|---|---|---|---|
| Linear wipe | A clear change of content | 12–24 | Edge at `x = W * progress(t, t0, 18, 'expo.inOut')` | Hard edge with nothing moving; add a bright edge line |
| Ragged wipe | A hand-made edge | 14–24 | Edge per column plus 1-D noise (recipe E) | Noise too fine; reads as dither |
| Iris | Focus on a centred subject | 18–30 | Circle radius `MotionMath.tween(t, t0, t1, 0, R, 'circ.out')` | The subject is off-centre |
| Clock wipe | Time passing | 24–36 | Angle `2π * progress` around the centre | Reads as a loading icon |
| Diagonal wipe | Energy, a sporting change | 10–16 | Line `x·cos θ + y·sin θ = offset`, offset tweened | Angle against the direction of motion |
| Split slide | Two halves reveal a third | 12–18 | Each half offset by `MotionMath.tween(..., 'power3.out')` | Splits a word in half |
| Frame grow | A container opens to full frame | 12–24 | Scale 0.6 → 1 with `MotionMath.ease` | Corner radius pops |
| Polygon reveal | Geometric, brand-like | 18–30 | `MotionMath.resamplePath` of an N-gon, scale tweened | Too few sides; reads as a circle |

## 4. Optical: blur and light (4–24 frames)

| Transition | Use when | Frames @ 60 | Recipe | Fails when |
|---|---|---|---|---|
| Blur dissolve | A soft change of image | 12–20 | Outgoing blur rises 0 → 20 px while incoming falls | Both sides heavy: mud at the midpoint |
| Blur bridge | The same subject moves to a new scene | 8–12 | `directionalBlur` peaks at the midpoint | Longer than about 12 frames |
| Light sweep | A glint, a premium feel | 16–24 | `lightSweep` with `PostFX.sweepExtent` (recipe D) | `strength` above about 1.5 clips the bright areas |
| Light leak | A warm, film-like join | 12–20 | `lightSweep` with a warm `tint` and low strength | Overused; reads as a filter |
| Flash to white | A rebirth, a reveal | 4–8 | Exposure ramps to 4, then back to 1 | Strobing over three per second (see [pacing-retention.md](pacing-retention.md)) |
| Exposure dip | A fade through light | 10–18 | `exposure` 1 → 0.2 → 1 | Blacks go grey; highlights clip |
| Focus pull | A shift of attention | 18–30 | `PostFX.cocPx` into `lensBlur` (recipe C) | Blur reaches the subject |
| Bloom bridge | A light tie between scenes | 8–12 | `fx.finish(scene, bloom, {strength})` ramped | Fog over the whole frame |

## 5. Typographic (6–36 frames)

| Transition | Use when | Frames @ 60 | Recipe | Fails when |
|---|---|---|---|---|
| Letter stagger | A title enters | 1–2 per letter; ≤ 18 total ([rhythm §5](../craft/rhythm-sync.md#5-cascades-stagger)) | `MotionMath.stagger(i, count, {each: 0.022, from: 'start'})` over `MotionMath.layoutGlyphs` | The cascade lasts past ~0.3 s and the title reads letter by letter |
| Kinetic slam | An emphasis word | 8–12 | `MotionMath.spring(t, {freq: 3, damping: 0.5})`, scale 1.4 → 1 | Overlaps its neighbours |
| Word swap | A word changes | 6–10 | Old word out upwards, new word in from below with `MotionMath.easeOut` | The width changes and the line jitters; reserve the width |
| Type mask reveal | A title unveils | 12–18 | A mask bar moves across the text | The mask cuts the ascenders |
| Stepped flip | A mechanical change | Steps at 12 fps | `MotionMath.stepped(fn, 12)` on the glyph index | Reads as a bug at 60 fps; use once |

## 6. Material: ink, paper, glitch, print (3–30 frames)

| Transition | Use when | Frames @ 60 | Recipe | Fails when |
|---|---|---|---|---|
| Ink bleed | An organic change | 16–24 | Noise threshold against progress (recipe E, 2-D in a shader) | Too smooth to read as ink |
| Page turn | A document, a reading | 18–30 | `MotionMath.arcPoint` for the curl, a soft shadow under it | No shadow: reads as a slide |
| Glitch slice | Distortion, data | 3–6 | Row offsets from `MotionMath.hash(row + frame, seed)` (recipe F) | Lasts more than 6 frames |
| Riso print swap | A print look | 12–24 | `PostFX` `screenPrint` with `strength` ramped 0 → 0.35 (recipe G) | Moiré on small type |
| Film burn | A retro edge | 12–20 | Warm `lightSweep` plus a faint `radialBlur` | Overused |
| Paper tear | A torn edge | 12–18 | Ragged noise edge with a bright rim | Reads as a render bug without the rim |

## 7. Morph (18–40 frames)

| Transition | Use when | Frames @ 60 | Recipe | Fails when |
|---|---|---|---|---|
| Shape morph | One icon becomes another | 18–36 | `resamplePath` both, `alignPaths`, `morphPath` (recipe H) | Point order twists; fix the start point |
| Colour morph | A hue change | 12–24 | Interpolate in linear light: `c ** 2.2`, mix, encode | sRGB midpoint goes muddy |
| Object morph | A logo to a logo | 24–40 | Shared pivot, same topology | Different topology folds the shape |
| Scale-through | A shape opens into the next scene | 24–40 | Shape A scales until it covers the frame; scene B starts inside | The edge pops if the shape is off-centre |

## 8. Recipes

Recipes A–C and G use the `PostFX` runner: `const fx = PostFX.runner(gl, {width: 1080, height: 1920})`, `scene = fx.target()` with the sharp scene drawn into it, `fx.W` and `fx.H` for the size. Each pass writes to a target, and `fx.finish(source, bloom, options)` writes the final frame.

**A. Whip pan (directional blur).** Blur length in px comes from speed, with a whip shutter of 360° at 60 fps ([blur](../craft/blur.md)).

```js
const speed = fx.W / (8 / 60);                                     // the frame crossed in 8 frames: 8100 px/s at 1080
const px = MotionMath.pxPerExposure(speed, 360, 60) * MotionMath.impulse(t, plan.hits, 14);   // about 135 px at the peak
const whipped = fx.target();
fx.pass('directionalBlur', {to: whipped, textures: {image: scene},
  uniforms: {dir: [px / fx.W, 0], samples: {int: 32}}});
fx.finish(whipped, null, {toneMap: 'aces'});
```

**B. Zoom whip (radial blur).** `amount` is the zoom fraction.

```js
const zoom = 0.35 * MotionMath.impulse(t, plan.hits, 12);
fx.pass('radialBlur', {to: whipped, textures: {image: scene},
  uniforms: {center: [0.5, 0.5], amount: zoom, aspect: fx.W / fx.H, samples: {int: 48}, spin: {int: 0}}});
```

**C. Focus pull (lens blur).** The circle of confusion comes from the depth of the plane and the focus distance. `distance(t)` is the piece's own function.

```js
const px = PostFX.cocPx(distance(t), focus, 30, 40);            // blur in px for this depth
fx.pass('lensBlur', {to: blurred, textures: {image: scene}, uniforms: {
  radius: [px / fx.W, px / fx.H], opticalCenter: [0.5, 0.5], gain: 0.8, threshold: 0.8,
  rim: 0.6, chroma: 0.02, catEye: 0, blades: 0, rotation: 0, samples: {int: 160}}});
```

**D. Light sweep.** Run it before bloom so the band glints. `pos` runs from one edge of the frame to the other.

```js
const ext = PostFX.sweepExtent(fx.W / fx.H, -0.5);              // the position where the band leaves the frame
const pos = MotionMath.tween(t, t0, t0 + 0.3, -ext, ext, 'power2.inOut');
fx.pass('lightSweep', {to: lit, textures: {image: scene},
  uniforms: {pos, width: 0.08, strength: 1.2, angle: -0.5, aspect: fx.W / fx.H, tint: [1, 0.9, 0.7]}});
```

**E. Ragged edge (1-D noise, per column).** The same noise, run in a shader for 2-D ink, gives the ink bleed.

```js
// Wipe edge in px for each column: progress sets the mean, noise makes the edge ragged.
const W = 1080, reach = progress(t, t0, 18, 'expo.inOut') * W;
const edgeAt = x => reach + 60 * (MotionMath.valueNoise(x * 0.01, 3) - 0.5);
const visible = x => x < edgeAt(x);                             // draw column x of B where true, A elsewhere
```

**F. Glitch slice.** `plan.glitches` is your own list of first frames (add it to the plan); each glitch lasts 3 frames.

```js
const frame = Math.floor(t * 60);
const glitching = plan.glitches.some(g => frame >= g && frame < g + 3);
const shiftFor = row => glitching ? 24 * (MotionMath.hash(row + frame, 11) - 0.5) : 0;   // px, per 24-px row
```

**G. Riso print swap.** `screenPrint` works on the tone-mapped image, so run it after `finish`. Stepping the seed at 12 fps makes the ink boil.

```js
const seed = Math.floor(t * 12);                                // the ink texture changes at 12 fps
fx.pass('screenPrint', {to: printed, textures: {image: tone}, uniforms: {
  res: [fx.W, fx.H], offA: [3, 0], offB: [-2, 1], paper: [0.96, 0.93, 0.86],
  inkA: [0.9, 0.2, 0.15], inkB: [0.1, 0.2, 0.45], cell: 9, angleA: 0.26, angleB: 1.31,
  texture: 0.6, seed, strength: 0.35 * progress(t, t0, 18), inks: 2}});
```

**H. Shape morph.** Both shapes need the same number of points, and `alignPaths` rotates and reverses `b` to match `a`.

```js
const n = 96;
const a = MotionMath.resamplePath(shapeA, n, {closed: true});
const b = MotionMath.alignPaths(a, MotionMath.resamplePath(shapeB, n, {closed: true}), {closed: true});
const current = MotionMath.morphPath(a, b, progress(t, t0, 30));
```

## 9. Checklist for any transition

- [ ] The join length is in whole frames at 60 fps, and `t0` is a frame centre.
- [ ] The outgoing and incoming states agree at the join, or the join is a deliberate contrast.
- [ ] Flashes stay under three per second (WCAG 2.3.1).
- [ ] Blur length matches the motion (`MotionMath.pxPerExposure`); `MotionMath.blurAdvice(px)` says what the blur reads as.
- [ ] Type stays readable through the join (see [captions-titles.md](captions-titles.md)).
- [ ] The transition appears on the story's beat list only where the story needs it (see [story-structures.md](story-structures.md)).

## 10. How to check

- Sample the join densely: `node scripts/sample_frames.mjs --root <piece> --out <folder> --window 7.0:7.6:0.1`, then `python scripts/contact_sheet.py <folder> --out <sheet.jpg>`.
- For blur, render the same instant with and without it: add `--noblur` to tell blur from geometry.
- Check determinism: `node scripts/determinism_check.mjs --root <piece> --times 2.4,2.6,2.4` (use the join's own times) must pass, so the join is the same on repeated seeks.
- For a flash, count flashes per second from the sampled frames before shipping.

Related: [cutting.md](cutting.md) for the joins that are plain cuts; [pacing-retention.md](pacing-retention.md) for the flash limit and holds; [kinetic-typography.md](../craft/kinetic-typography.md) for type joins; [blur.md](../craft/blur.md) for blur practice; [light-bloom.md](../craft/light-bloom.md) for light sweeps and bloom; [print-textures.md](../craft/print-textures.md) for riso and paper; [glass-webgl.md](../craft/glass-webgl.md) for shader-level work; [curves-graph-editor.md](../craft/curves-graph-editor.md) for easing choice; [stepped-time.md](../craft/stepped-time.md) for 12 fps steps.
