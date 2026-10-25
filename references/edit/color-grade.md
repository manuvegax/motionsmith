# Color grade

How colour is decided and kept consistent: the linear-light workflow, a set of looks the kit can produce, legibility, shot-to-shot consistency, and the rule for exact brand colours. Read it before the first frame is graded, and again before the final export.

Grading is the last decision about what a picture says. It changes mood more than any other single setting, so it is decided once for the piece and then held.

## 1. Workflow in linear light

Light adds in linear values, not in the sRGB values that the screen shows. Mixing, blurring, bloom and light sweeps are only correct in linear.

| Step | What happens | Where in the kit |
|---|---|---|
| 1. Author | Colours are written as sRGB hex, then converted to linear before any mix | Your piece; see the helper below |
| 2. Render | The scene is drawn into a half-float target | `PostFX.runner` and `fx.target()` |
| 3. Light | Blur, bloom and light sweeps work on the linear scene | `fx.bloom`, `lightSweep`, blur passes |
| 4. Tone map | Highlights are compressed | `fx.finish` with `toneMap` |
| 5. Grade | Exposure, lift, gamma, gain, saturation | `fx.finish` options |
| 6. Encode | Encoded for the screen, then tagged BT.709 on export | `fx.finish` and FFmpeg (see [formats-platforms.md](formats-platforms.md)) |

```js
// Exact sRGB to linear, for colours authored as hex.
const srgbToLinear = c => c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
```

What `fx.finish` does, in order (`postfx-glsl.js`): exposure, tone map, lift and gain, gamma, saturation, vignette, the encode (`pow(c, 1/2.2)`), then grain. Its options are scalars: `lift`, `gamma`, `gain` and `saturation` are single numbers, not per-channel values.

Tone maps by name: `clip` (hard clamp), `shoulder` (default, a soft top), `reinhard` (`x / (1 + x)`), `aces` (a filmic curve). Start with `shoulder`; use `aces` for high-contrast pieces, and `clip` only to see what the scene holds before the curve.

## 2. Looks the kit can produce

| Look | Recipe with `fx.finish` | When | Risk |
|---|---|---|---|
| Monochrome plus one accent | `{saturation: 0}`, then the accent as a separate brand layer (section 3) | Editorial, statements, one thing that matters | The accent is the only colour: keep it to one object |
| Film emulation | `{lift: 0.03, gamma: 1.05, saturation: 0.9, halation: 1.2, grain: 0.02}` with a warm `halationTint`; halation needs a bloom target | Memory, documentary, soft drama | Grain on small type reads as noise |
| Bleach bypass | `{saturation: 0.45, gain: 1.12, gamma: 0.95}`, `toneMap: 'aces'` | Gritty, high contrast, a harsh moment | Crushes the shadows; check the text in them |
| High-key clean | `{exposure: 1.1, lift: 0, gain: 1.05}`, `toneMap: 'shoulder'` | Clean product, bright statements | Whites lose separation from a white page |
| Low-key night | `{exposure: 0.8, gamma: 0.9, vignette: 0.3}` | Quiet, intimate, a question | Type disappears; give it a plate |
| Duotone | Gradient map from luma to two colours | Graphic, poster-like | Not in the kit: needs a custom 1-D lookup pass |
| Teal and orange, with restraint | Split toning: shadows cool, highlights warm, 5–10 % | A cinematic cliché if pushed | Not in the kit: needs a custom pass; keep it weak |

- Duotone and split toning need per-channel or per-region controls, and the kit's `finish` takes scalars. Build them as a custom pass when a piece needs them, and say so in the plan.
- "Restraint" in teal and orange means the colours are almost present. When a viewer names the look, it is too strong.
- Saturation mixes each pixel between its luma (`0`, grey) and its own colour (`1`, unchanged). Above `1` it pushes past the authored colour. Do not go above `1.1` for skin or text.

## 3. Exact brand colours: composite after tone mapping

The tone map and the encode bend colour. A saturated brand red that goes through the shoulder curve and the encode does not come out the same value. So brand colours are not graded: they are composited on top of the graded picture.

```js
fx.finish(scene, bloom, {toneMap: 'aces', saturation: 0.9});     // the picture, graded, to the canvas
fx.pass('copy', {textures: {image: brandLayer}, blend: 'alpha', clear: false});  // exact colour on top
```

- `brandLayer` is drawn in sRGB values, with straight (not premultiplied) alpha, and it is not run through `finish`.
- The blend is `SRC_ALPHA, ONE_MINUS_SRC_ALPHA`, so the layer's alpha decides its coverage.
- Anything that must match a brand value exactly goes on this layer: logos, the accent colour, a text colour that carries a brand meaning.
- In one test, a saturated red (#ff422e) exported as about (255, 81, 40) until the output carried BT.709 tags. Tag the output, then check the pixel (section 7).

## 4. Legibility

Text must stay readable in every frame it is on screen, not only in the frame where it is designed.

| Text | Minimum contrast | Basis |
|---|---|---|
| Body-size text | 4.5 : 1 | WCAG 2.2, success criterion 1.4.3 (Contrast, minimum) |
| Large text (WCAG: 18 pt regular or 14 pt bold, about 24 CSS px or 18.7 CSS px; check the size on the export) | 3 : 1 | Same criterion |
| Graphic elements and icons | 3 : 1 | WCAG 2.2, success criterion 1.4.11 |

- Motion does not change the rule. A text that passes over a bright highlight for 6 frames fails for those 6 frames.
- Put a dark plate, a vignette or a blur behind text that crosses bright areas. Do not rely on the text's shadow alone.
- Test on a phone-brightness screen as well as on the reviewer's monitor (practice).

```js
// Relative luminance and contrast ratio, WCAG 2.2 definition. Rgb values are 0–255.
const lum = ([r, g, b]) => {
  const f = c => (c = c / 255) <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const contrast = (a, b) => (Math.max(lum(a), lum(b)) + 0.05) / (Math.min(lum(a), lum(b)) + 0.05);
```

## 5. Shot-to-shot consistency

One piece, one grade. Shots differ in content, not in the look.

- Use the same `finish` options in every shot. Exposure may vary per shot, within about ±10 % (practice), when the content demands it.
- Write the grade for each scene in the plan, so every shot's options are visible in one place:

```json
{"scenes": [
  {"id": "hook",   "from": 0.0, "to": 1.2, "grade": {"exposure": 1.0, "saturation": 0.9}},
  {"id": "turn",   "from": 1.2, "to": 6.0, "grade": {"exposure": 0.95, "saturation": 0.9}}
]}
```

- A change of look inside a piece must be a decision the structure needs (see [story-structures.md](story-structures.md)), and it must happen on a beat, not drift.
- Compare the scenes side by side on one contact sheet. A scene that looks like another piece is a grading error.

## 6. Colour in motion

- Interpolate colours in linear light, not in sRGB. The midpoint of a sRGB mix between two saturated colours goes muddy; the linear midpoint does not.
- Avoid a saturated colour that flickers near 3 Hz or faster for long. It is uncomfortable to watch and fails the flash guidance in [pacing-retention.md](pacing-retention.md).
- A colour change on a hit reads as a decision; a colour change on every cut reads as noise.

## 7. How to check

- Sample a frame at the brand layer and at a neutral area, export it, and read the pixels. Compare with the hex value within ±2 per channel at 8 bits.
- Confirm the tags on the export: `ffprobe -v error -select_streams v:0 -show_entries stream=color_space,color_primaries,color_transfer,color_range -of default=nw=1 <export.mp4>` should show `bt709` for space, primaries and transfer, and `tv` for range (see [formats-platforms.md](formats-platforms.md)).
- Look at a contact sheet of every scene: `python scripts/contact_sheet.py <folder> --out <sheet.jpg>`. A sheet shows the look; it does not prove the colour value. Use the pixel check for that.
- For the grade's effect on text, render one frame with the text and the grade, then compute the contrast of the text colour against the pixel behind it with the helper in section 4.

## 8. Checklist

- [ ] Colours authored as sRGB, converted to linear before mixing.
- [ ] Blur, bloom and light run in linear; the tone map comes after them.
- [ ] One set of `finish` options for the piece; per-scene differences written in the plan.
- [ ] Brand colours composited after `finish`, on a straight-alpha layer.
- [ ] Text passes contrast at its minimum, in every frame it is on screen.
- [ ] Saturation is not above 1.1 on skin or type.
- [ ] Colour changes are on beats, and no saturated flicker runs faster than about 3 Hz.
- [ ] Export tagged BT.709; brand pixels checked within ±2.

Related: [captions-titles.md](captions-titles.md) for text on graded frames; [light-bloom.md](../craft/light-bloom.md) for the light that the grade shapes; [retro-looks.md](../craft/retro-looks.md) for grain, halation and print; [print-textures.md](../craft/print-textures.md) for the screen print pass; [formats-platforms.md](formats-platforms.md) for the export tags; [art-direction.md](../create/art-direction.md) for choosing the look before grading it.
