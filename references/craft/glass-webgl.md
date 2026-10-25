# Glass, materials and optics in custom WebGL

Read when building pieces with glass, glow, lenses or 3D layers in your own WebGL. Values come from a production
engine (a glass lens that docks into a letter): starting points, not presets.

## 1. Architecture that worked

- **HDR scene** in half-float: values may exceed 1. Exposure accumulation in float, once per sample, weight `1/M`;
  resolve to 8 bits once at the end ([pipeline §3](../produce/pipeline.md#3-time-and-sub-sampling)).
- **Two passes per sample**: A with the opaque world; B starts as a copy of A and glass is drawn reading A as the
  backdrop to refract it. Never read the texture attached to the target of the same draw.
- **Halton (2,3) jitter** per exposure sample: blur and antialias in one step.
- **Bloom** from what emits (or what passes a threshold); composite through a soft shoulder (never a hard clip)
  and gamma 2.2. In the kit: `PostFX.runner(gl)` → `bloom` + `finish`.
- Text as canvas textures; glass letters with a bevel map (blurred alpha as height) to derive normals.
- A post chain on the tone-mapped frame (screen print, transition blur) can reuse the kit's shader sources
  directly: `PostFX.SHADERS.screenPrint`, `.radialBlur`, `.directionalBlur` compile with any full-screen vertex
  shader that passes `uv`.

## 2. Depth: the rule that prevented most bugs

- Backgrounds, grids, shadows, caustics and moving type layers draw with `depthMask(false)`. If they write depth,
  they clip any object tilted in 3D that crosses their plane (a ring hidden by its own shadow; a print clipped by
  a grid).
- Order: background → opaque → depth-less shadows → glass.

## 3. Glass

- Layers: refraction of the blurred backdrop, stronger tint at the edges (Fresnel), a milky fill, specular and inner
  light. On letters, a base fill of ~0.75; with Fresnel alone they look like hollow tubes.
- **Over light backgrounds, inner light is too much**: scale it by the backdrop luminance (`1 − 0.6·lum`). Without
  it, a red reached 5–7 in linear and the bloom burnt it white.
- **A lens draws what is seen inside itself**: magnified (×1.13) and clipped to an ellipse. A rectangle behind a
  translucent ring shows its edge.
- **Chromatic aberration only near the edge** (radial mask). Over the whole disc, magnified by a macro, it makes
  colour fringes.
- Reflections that can be dimmed per shot: in a macro, turn 80–90 % of the specular and sweep off so they do not
  compete with the photo's own highlights.
- Material families that worked: frosted (`tint ≈ [.93,.96,1]`, body .30, glow .78, rim .95, frost 13 px), tight
  frosted for small letters (crisper rim, frost 5 px), accent glass with its own light for the one meaningful object.

## 4. Bloom on a budget

- Level weights must sum to 1 (normalise by the level count). At 2.25, everything bright went white. A composite
  gain around 0.75 for hand-rolled pyramids.
- "Hot cores to white" only above ~2.5–9 in linear and with ≤ 35 % mix.
- Check in greyscale: if edge and interior melt, lower the fill or the exposure. More: [light](light-bloom.md).

## 5. Eight bits at the end

- Dark gradients (vignettes) in yuv420p: open a full MP4 frame. Fine grain that changes every frame (~0.02) dithers.
- Grain and moving grids cost bitrate: the same 12 s piece went from 14 MB to 39 MB at CRF 14 when they were added.

## 6. Code bugs already met

- **Name collisions**: a texture uniform called `height` overwrote the quad height and broke a title. Use explicit
  names (`bevelTex`).
- Debug hooks on `window` (`lensAt`, `eyeDebug`) removed before the render.
- Check half-float/float extensions and `FRAMEBUFFER_COMPLETE`, and fail with a clear message when missing.
- Restore `blendFunc` and `depthMask` after every additive layer (light sweeps, particles).
- `preserveDrawingBuffer: true` so captures read the last draw.
- **Premultiplied alpha**: a WebGL canvas is premultiplied by default. A shader writing colour without multiplying by
  alpha gives semi-transparent edges a light halo. Write `vec4(color * a, a)` or create the context with
  `premultipliedAlpha: false`, and blend with `ONE, ONE_MINUS_SRC_ALPHA`.
- **Non-power-of-two textures** (1080×1920 never is one): in WebGL 1 no mipmaps and no `REPEAT`. Use `CLAMP_TO_EDGE`
  and `LINEAR`; a texture that must repeat measures 256, 512 or 1024.
- **Canvas 2D text that changes with history**: a GPU-accelerated 2D canvas caches glyphs, and the same letter can
  differ by 1–2 levels depending on what was drawn before (a title letter changed in 19 pixels and
  `determinism_check` failed). Create 2D canvases that become textures with
  `getContext('2d', {willReadFrequently: true})` (CPU raster).
- **An accumulator that was never cleared**: a pass with blending that ignored `clear: true` added the first
  motion-blur sample to the previous frame (the whole frame changed when seeking back to the same t). In the kit,
  `clear: true` always clears; by default it clears only when not blending; `clearColor: [0,0,0,0]` for alpha layers.
- **Intermediate buffers holding another frame's pixels**: a scissored pass that reads a few pixels outside its
  region (blur, print misregistration) finds what another block left in an earlier frame. Clear every intermediate
  target at the start of each frame.
