# Blur: kinds, settings and how to check them

Read for "more blur", blur that leaves ghosts, a blurred transition or depth of field. Shaders in
`scripts/kit/postfx-glsl.js`; exposure samples in `scripts/kit/motion-math.js`.

## 1. Which blur is which

| Kind | What it simulates | In After Effects | In code |
|---|---|---|---|
| **Real motion blur** | The shutter trail while something moves | Per-layer motion blur switch + composition advanced settings | Sub-frame samples accumulated in float (`exposureTimes`) |
| **Synthesised motion blur** | The same, estimated from footage | Pixel Motion Blur, RSMB (plugin) | Only for video clips; not needed for code-made layers |
| **CC Force Motion Blur** | Sub-samples over an animated layer | Time effect (Shutter Phase since v24) | Same as real motion blur |
| **Directional** | A trail in a fixed direction | Directional Blur | `directionalBlur` |
| **Radial** | Zoom (towards the centre) or spin | Radial Blur / CC Radial Fast Blur | `radialBlur` (`spin` 0 or 1) |
| **Lens and bokeh** | Optical defocus shaped by the iris | Camera Lens Blur | `lensBlur` (polygonal iris, highlight boost, rim, cat-eye, chroma) |
| **Depth of field** | Only one plane in focus | 3D camera: Focus Distance, Aperture, Blur Level | `cocPx()` per plane + `lensBlur` |
| **Gaussian / box** | Uniform softening | Gaussian Blur, Fast Box Blur | Separable pass |
| **Transition blur** | A change of attention | Animated blur on an entrance or exit | Radius animated with the same curve as the move |
| **Feather** | A soft mask edge | Mask Feather | `smoothstep` over the distance to the edge |

## 2. Real motion blur

This section is the single source for shutter angle and samples; other guides link here.

**After Effects settings** (Composition → Settings → Advanced; Adobe, "Composition basics"):
- **Shutter Angle**: simulated exposure in degrees, 1° (almost no trail) to 720° (a lot). At 24 fps, 90° is 1/96 s.
- **Shutter Phase**: when the shutter opens relative to the frame. Adobe recommends −½ of the angle (−90° at
  180°) so the trail is centred on the object.
- **Samples Per Frame**: the minimum; used by 3D and shape layers.
- **Adaptive Sample Limit**: the maximum, for 2D layers whose motion After Effects can measure.

**In code**: `MotionMath.exposureTimes(t, {fps, shutter, phase, samples})` returns the instants with the same
meaning (default phase = −shutter/2) plus a Halton jitter per sample that also antialiases. The jitter pattern is
the same every frame (stable: it does not shimmer); with one sample there is no jitter and no antialias, so a
frame without blur needs its own antialias. Accumulate in float with weight `1/M` and convert to 8 bits once
([pipeline §3](../produce/pipeline.md#3-time-and-sub-sampling)). The [starter](../../templates/starter/piece.js)
picks the sample count from the fastest edge of the frame.

| Angle | Look | When |
|---|---|---|
| 90° | Choppy and crisp | Tense action, strobe effect |
| 180° | Natural film | The base for almost everything |
| 270–360° | Fluid | Fast moves that must read smooth |
| 400–720° | Stylised smear | Whips, hits, swipes; never while reading |

**Default**: 180–300° for normal moves and 360–400° for whips. On a phone at real speed the angle is felt as
smoothness rather than seen; 720° rarely pays for its render. A profile may set its own range.

**Phase**: −shutter/2 centres the trail; −shutter leaves it behind the object (comet); 0 throws it forward.

**How much trail**: px per exposure = speed (px/s) × angle / 360 / fps. `pxPerExposure()` computes it and
`motion_curves.py` reports it at the peak:

| px per exposure | Reads as |
|---|---|
| < 1 | No useful trail: blur only softens; skip it |
| 1–20 | Natural: weight is felt |
| 20–80 | Strong: check the landing frame is sharp and no copies show |
| > 80 | Stylised smear: hits and whips only |

**How many samples**: gap between copies = px per exposure / samples. Above ~3 px, steps show; start with
`samples ≥ px/3` (a 60 px trail → ≥ 20 samples; a whip at 200 px → 64–72).

**Do not apply it** to moves shorter than the element's width per frame, to fades or colour changes, to text
being read, to slow drifts, or to whole containers that do not move.

## 3. Directional and radial

- **Directional**: when sub-sampling is impossible (a pre-rendered layer, a video). `dir` = velocity × px per
  exposure, in uv (`[px_x / W, px_y / H]`). Draw the layer with margin, or the trail is cut by a straight edge.
- **Zoom**: for a push-through or an impact. Centre on the focus, `amount` 0.05–0.3 at the peak, decaying.
- **Spin**: for fast rotations; `amount` in radians ≈ angular speed × exposure. Many samples (96–128) or the spin
  draws rings on fine detail.
- As a **transition**, these blurs peak on the cut and fade within ~8–15 frames each side
  ([transitions atlas](../edit/transitions-atlas.md)).
- **Order with a print look**: blur first, then the screen print, so halftone dots stay crisp
  ([print & textures](print-textures.md)).

## 4. Lens, bokeh and depth of field

**Camera Lens Blur** (Adobe, "Blur and Sharpen effects"): radius, iris (shape, roundness, aspect, rotation,
diffraction fringe), specular highlights (gain, threshold, saturation) and a blur map. `lensBlur` reproduces the
essentials: disc or polygonal kernel (`blades`, `rotation`) and highlight boost (`gain`, `threshold`).

- **Bokeh needs HDR**: a point at 8–40 in linear light becomes a bright disc; the same point already clipped to 1
  becomes mush. Defocus before tone mapping.
- **What makes it read as a lens** (a first attempt that blurred the whole frame was judged "not really a lens"):
  1. **A sharp subject and only the background defocused.** A whole blurred frame reads as a filter.
  2. **Discs with a slightly brighter rim** (`rim` 0.8–1.2), round or many-bladed.
  3. **Cat-eye** towards the frame edges (`catEye` 0.4–0.6 with `opticalCenter`).
  4. **A subtle colour fringe** on the disc edge (`chroma` 0.02–0.03).
  5. **Lights of different colours** in the background: bokeh shows in lights, not in surfaces.
- **Dotted discs**: lights smaller than the gap between samples (≈ radius·√(π/samples)) come out as dot patterns.
  Pre-blur the plane by that gap and use 160–256 samples.
- **Gaussian vs lens**: Gaussian melts; a disc draws the iris.

**Depth of field** (After Effects camera: Focus Distance, Aperture, Blur Level, near/far). In code, per plane:
`PostFX.cocPx(distance, focus, aperture, max)` gives the radius and `lensBlur` applies it.
- **Rack focus**: animate the focus distance ease-in-out over 0.5–1.2 s; one sharp plane at a time. The text plane
  stays in focus while it is read.
- In 2.5D, defocus layer by layer; per-pixel blur from a depth buffer is not in the kit yet.

## 5. Blur as a transition

- Enter with high blur that reaches 0 with the entrance curve (e.g. 30 → 0 with `power4.out`); exit 0 → 45 with
  `power2.in`. Text lands sharp and stays sharp while read.
- A transition blur is measured too: if it hides a geometric jump, fix the jump first.

## 6. In linear light

Averaging in sRGB darkens bright edges. The kit accumulates in linear (gamma 2.2) and shaders receive HDR
textures. CSS `filter: blur()` works in sRGB: fine for a detail, not for a trail.

## 7. Check

| Test | Command or look |
|---|---|
| The same peak with and without blur | `sample_frames.mjs --times … --noblur` vs normal |
| Sharp landing | First settled frame after the peak |
| Steps or copies | Enlarged crop of the peak; if visible, raise samples |
| Cut trail | A straight edge in the trail: give the layer margin |
| Banding in the trail | 8-bit accumulation: move to float |
| Right amount | `motion_curves.py`: px per exposure at the peak |

## Sources

Adobe, "After Effects composition basics" (advanced motion blur settings), "Apply Blur and Sharpen effects"
(Camera Lens Blur), "Cameras, lights, and points of interest" (depth of field), "Apply motion blur for smoother
playback" (Pixel Motion Blur), v24 release notes (Shutter Phase in CC Force Motion Blur).
