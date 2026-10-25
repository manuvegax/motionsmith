# Layers, effects and compositing: what After Effects does with layers, done in code

Read when combining images, cut-outs and light, when a mask or matte is needed, or when looking for the
equivalent of an After Effects effect.

## 1. Blend modes

Most modes change colour, not alpha (Adobe, "Blending modes"). In code, apply them in linear light when the layer
is light.

| Mode | Formula (a = layer, b = background) | Use | In WebGL |
|---|---|---|---|
| Normal | a·α + b·(1 − α) | Default | `blendFunc(SRC_ALPHA, ONE_MINUS_SRC_ALPHA)` |
| Add (Linear Dodge) | a + b | Light, glints, sweeps | `blendFunc(ONE, ONE)` |
| Screen | 1 − (1 − a)(1 − b) | Light that burns less, light leaks | `blendFunc(ONE, ONE_MINUS_SRC_COLOR)` |
| Multiply | a·b | Shadows, ink, paper texture | `blendFunc(DST_COLOR, ZERO)` |
| Overlay | b < 0.5 ? 2ab : 1 − 2(1 − a)(1 − b) | Grain, contrasty texture | In a shader |
| Soft Light | Softened overlay | Subtle grain, tint | In a shader |
| Difference | \|a − b\| | Graphic effects, glitch | In a shader |
| Alpha Add | Sum of alphas | Joining two semi-transparent edges without a seam | In a shader |

**Stencil and Silhouette** affect every layer below (Stencil shows only inside; Silhouette punches through).

## 2. Mattes and masks

- **Track matte** (Adobe, "Track Mattes"): any layer can matte another. **Alpha** uses transparency; **Luma**, brightness;
  inverted versions show where the matte is 0. For clean edges, raise the matte's contrast.
- **In code**: multiply the layer's alpha by the matte channel in the shader, or use the stencil buffer for hard
  shapes. Typical cases: video inside letters, a photo revealed by a brand shape, text behind a subject
  ([scene recipes](../create/scene-recipes.md)).
- **Feathered masks**: describe the shape as a signed distance to the edge and use `smoothstep(−f, f, d)`. Expand or
  choke = add to `d`. Animating a mask shape is a morph ([transitions atlas](../edit/transitions-atlas.md)).

## 3. Adjustment layers, precomps and hierarchy

| In After Effects | In code |
|---|---|
| Adjustment layer | Draw the layers below into a target and process it with `fx.pass(...)` before compositing |
| Precomposition | A `scene(tLocal)` function drawing into its own target; local time = `t − start`, its own transform |
| Collapse Transformations | Draw the content with the parent's transform instead of rasterising it |
| Parenting and nulls | Multiply parent × child matrices; a null is a parent without an image |
| Anchor point | The pivot: scale from the base if the object grows from there, not from the centre |

## 4. Shape layers

| Operator | Equivalent |
|---|---|
| Trim Paths (drawing a stroke) | Walk the path to a fraction of its length: `pathSampler` + dash, or an SDF with a threshold |
| Repeater | Instances with incremental transform and opacity |
| Offset Paths | Add to the signed distance |
| Wiggle Paths | Deterministic noise on the vertices (`wiggle` with one seed per vertex) |
| Round Corners | `smoothstep` over a rounded-box distance |
| Merge / morph paths | `resamplePath`, `alignPaths`, `morphPath` (same point count, aligned start) |

## 5. After Effects effects and their equivalent

| Effect | Code equivalent | Where |
|---|---|---|
| Glow | Thresholded bloom | [Light §2](light-bloom.md#2-the-after-effects-glow-effect-and-its-equivalent) |
| Directional / Radial / Camera Lens Blur | `directionalBlur`, `radialBlur`, `lensBlur` | [Blur](blur.md) |
| Motion blur switch / CC Force Motion Blur | `exposureTimes` sub-samples | [Blur §2](blur.md#2-real-motion-blur) |
| Fractal Noise | Seeded fbm noise by octaves | `wiggle` as a base |
| Turbulent Displace / Displacement Map | Offset uv by noise or a texture | Custom shader |
| Echo | Draw the layer at t − k·Δt with decreasing opacity | `MotionMath.echo`, several passes or the accumulator |
| Posterize Time | `MotionMath.posterize(t, fps)` | [Stepped time](stepped-time.md) |
| Linear / Radial / Gradient Wipe | Mask by uv projection, angle or luminance | Custom shader |
| Venetian Blinds | Stripe mask | Custom shader |
| Shift Channels / RGB split | Chromatic aberration | `finish({aberration})` |
| CC Lens / Optics Compensation | Barrel distortion | `barrel()` in the `crt` pass |
| Wave Warp | Sine displacement | Custom shader |
| CC Light Rays | Radial blur of the thresholded prefilter, added | `bloomPrefilter` + `radialBlur` |
| Drop Shadow | Offset, blurred alpha under the layer | A soft shadow texture |
| Bevel / Emboss | Normals from a height map | Blurred glyph alpha as height ([glass & WebGL](glass-webgl.md)) |
| Levels / Curves | Lift, gamma and gain | `finish({lift, gamma, gain})` |
| Noise | Per-frame grain | `finish({grain})` |
| Halftone / risograph | Two-ink halftone with misregistration | `screenPrint` ([print & textures](print-textures.md)) |
| CRT / scanlines | Barrel, scanlines, aperture grille | `crt` ([retro looks](retro-looks.md)) |
| Time Displacement | Each pixel shows another instant from a map | Expensive: precompute instants; rarely worth it |

## 6. Check

- Each layer over light, dark and real imagery; matte edges at full size.
- Added light (add or screen) must not burn text: greyscale check.
- Background layers do not write depth ([glass & WebGL §2](glass-webgl.md#2-depth-the-rule-that-prevented-most-bugs)).

## Sources

Adobe, "Use blending modes and layer styles", "Track Mattes and Traveling Mattes", "Use alpha channels, masks, and mattes".
