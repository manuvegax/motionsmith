# Light: glow, bloom, flares, tone mapping and grade

Read when a piece needs glow, light, a film look or a colour finish, or when something looks washed out or burnt.
Passes in `scripts/kit/postfx-glsl.js` (`PostFX.runner`). Glass materials and engine rules:
[glass & WebGL](glass-webgl.md).

## 1. Three rules before turning anything on

1. **Light is added in linear and mapped last.** HDR scene (values > 1), bloom on those values, tone mapping and
   gamma in the last pass. Clipping earlier destroys bloom and bokeh.
2. **Glow is earned.** It goes on things that emit or reflect (a lens, a neon, a letter made of glass), not on every
   headline: glow on every title = dull text and a template look.
3. **Exact brand colours go after the tone map.** ACES pulls saturated reds towards orange and white; a soft
   shoulder lowers 255 to 248. What must come out exact (a brand red in a bar, a logo, flat text) is composited on
   top of the result of `finish` (§5). Scene colours that do go through the curve are compared before and after.

## 2. The After Effects Glow effect and its equivalent

| AE parameter | What it does | In `PostFX` |
|---|---|---|
| Glow Based On | Colour or alpha | Prefilter on colour |
| Glow Threshold | Brightness below which there is no glow | `bloom(src, {threshold, knee})` (linear; ~1.0 = "brighter than white") |
| Glow Radius | How far the halo reaches | `levels` (more levels = wider) and `radius` |
| Glow Intensity | Halo brightness | `finish({bloomMode: 'add', strength})` |
| Composite Original | Glow in front, behind or alone | Composition order |
| Glow Colors / A & B | Own colour or a two-colour gradient | Bloom tint (`halationTint` or a custom pass) |

After Effects' Glow behaves differently at 32 bpc than at 8 or 16; the kit always works as at 32 bpc (half-float).
Deep Glow (a paid plugin) is the idea of a physically falling glow from many radii; the threshold-free pyramid
approximates it.

## 3. Threshold-free bloom vs thresholded bloom

**The pyramid** (Jimenez, SIGGRAPH 2014; LearnOpenGL, "Physically Based Bloom") blurs the whole HDR image over
several levels, without a threshold: bright things dominate only because they are brighter.
- 13-tap downsample per level with weights 0.125 (centre and inner cross), 0.0625 (sides) and 0.03125 (corners),
  summing to 1. On the first level, a **renormalised Karis average**: each 2×2 group weighs 1/(1 + luma) and the
  result is divided by the sum of weights, so a hot pixel does not flicker and a flat area keeps its exact value.
- Upsample with a 3×3 tent (4/16 centre, 2/16 sides, 1/16 corners), added at each level.
- `finish` divides the sum by the number of levels: a flat area is the same with or without bloom (tested).

`finish` has three blend modes:

| Mode | What it does | `strength` | When |
|---|---|---|---|
| `halo` (default) | Adds only the light that spills around bright things (`max(bloom − scene, 0)`). Flat areas do not change and a white letter stays white | 0.25–0.5 | The bloom for almost everything |
| `physical` | `mix(scene, bloom, strength)`: energy-conserving, but also softens detail | 0.1–0.3 | Diffuse atmosphere, dream, fog |
| `add` | Adds the whole bloom, like AE Glow | 1–4 with a threshold | Neon, sparks, glass edges; washed-out glow as a deliberate accent |

```javascript
const bloom = fx.bloom(lightOnly, {levels: 6, radius: .005});   // feed the bloom only what emits
fx.finish(scene, bloom, {bloomMode: 'halo', strength: .45, toneMap: 'shoulder'});
```

**Thresholded** (AE Glow look): only what passes the threshold glows, with a soft knee. `fx.bloom(scene,
{threshold: 1.2, knee: .5})` and `finish({bloomMode: 'add', strength: 4})`.

**Isolate what glows**: render emissive things into their own accumulation and bloom only that; text and paper
stay crisp (the [starter](../../templates/starter/piece.js) does this). Without normalisation, weights summing to
2.25 turned everything bright white; on light backgrounds, dim the objects' own light.

## 4. Halation, light wrap, flares and leaks

| Effect | What it is | Recipe |
|---|---|---|
| **Halation** | Film's red-orange halo around highlights | `finish({halation: 1–2.5, halationTint: [1, .32, .12]})` on the bloom. Tints only the light spilling past bright edges, never a flat area or the inside of a letter; `halationThreshold` > 0 limits it to brighter sources |
| **Light wrap** | Background light bleeds into a cut-out's edge: integrates collages | `lightWrap` pass with the blurred background and the cut-out's blurred alpha; `amount` 0.2–0.6 |
| **Anamorphic streak** | A horizontal line on very bright points | Thresholded prefilter + `directionalBlur` in x only, cool tint, added |
| **Light leak** | A soft ball of light entering from an edge at a cut | Huge radial gradient with screen blend over 40–60 % of the frame, in the accent colour |
| **Lens ghosts** | Internal reflections opposite the light | Sample the prefilter at `1 − uv`, scaled, tinted and added |
| **Light sweep** | A diagonal glint across a title | `lightSweep` pass **before** the bloom, so it glints; `PostFX.sweepExtent(aspect, angle)` gives where it leaves the frame |

## 5. Tone mapping

| Curve | Character | When |
|---|---|---|
| Clip (`clip`) | Hard saturation | Never with HDR and bloom |
| Soft shoulder (`shoulder`) | Keeps colour up to 0.85 and compresses the rest | Graphics with flat brand colours (keeps a red red) |
| Reinhard (`reinhard`) | Flat, low contrast | Rarely |
| Fitted ACES (`aces`) | Film contrast; highlights go white | Photographic and cinematic scenes without a critical brand colour |

What each curve does to white: with `shoulder` (knee at 0.85), linear 1.0 comes out at **248/255**, 1.25 at 254, and
~1.5 is needed for 255. With ACES, 1.0 comes out at ~0.8 before gamma. Hence: **exact brand colours are
composited after the tone map**, in sRGB, on top of `finish`.

`finish` always encodes to sRGB (gamma 2.2) at the end; its `gamma` option is a different thing: a mid-tone
grade (1 = no change, §7). `finish` writes alpha 1: it is for the final frame, not a transparent overlay
([overlays & alpha](../produce/overlays-alpha.md)).

Narkowicz's fitted ACES (2016): `x(2.51x + 0.03) / (x(2.43x + 0.59) + 0.14)`, clamped to [0, 1]. It is pre-exposed
(1 → ~0.8); multiply the input by 0.6 for the original ACES. Linear in and out; gamma comes after.

## 6. Linear flow and exposure

In After Effects: 32 bpc and a linearised working space (blend at gamma 1.0; Adobe, "Managing color"). In code:
half-float scene, linear accumulation, `exposure` in `finish`, gamma only at the end.

## 7. Grade

- `finish({lift, gamma, gain, saturation})`: lift raises shadows, gain highlights, gamma mid-tones.
- Split-toning: slightly cool shadows and warm highlights, in small doses.
- Protect the accent: check its hue in a final frame before and after the grade. Looks: [color grade](../edit/color-grade.md).

## 8. Vignette, aberration and grain

- Vignette 0.15–0.35: guides the eye without being noticed.
- Chromatic aberration 0.002–0.011, stronger only on hits.
- Grain 0.015–0.03 per frame (a new pattern every frame, never a slide): dithers banding and costs bitrate.

## 9. Check

- **Greyscale**: if the halo melts edge and interior, there is too much light.
- **Clipped highlights**: count pixels at 255 in an MP4 frame; many outside the light source = lower exposure.
- **Accent**: the same brand colour before and after (measure the pixel).
- **MP4**: banding in the vignette and blocks in the halos after compression.

## Sources

Adobe, "Stylize effects" (Glow), "Managing color" (32 bpc, linearisation). J. Jimenez, *Next Generation Post
Processing in Call of Duty: Advanced Warfare* (SIGGRAPH 2014); LearnOpenGL, "Physically Based Bloom" (2022).
K. Narkowicz, "ACES Filmic Tone Mapping Curve" (2016). `bang-motion` skill (MIT) on headline glow and light leaks.
