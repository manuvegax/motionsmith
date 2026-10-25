# Screen print, riso and print textures

Read for a screen-print, risograph, printed or halftone look, a "motion-graphics texture layer", or a layer that
gives matter to a piece that is too clean. Pass: `screenPrint` in `scripts/kit/postfx-glsl.js`. Demonstration:
block J of the [technique lab](../../templates/technique-lab/).

## 1. What it is

Screen printing and risography print **flat inks** one by one on paper. What gives them away:

| Trait | What shows |
|---|---|
| Flat inks | Two or three colours; mixes come from overlap |
| Halftone | Mid-tones are dots of varying size on a rotated grid (one angle per ink) |
| Misregistration | Each ink sits a few pixels off the others: coloured edges appear |
| Overprint | Where two inks cross, they multiply and darken |
| Uneven ink | Coverage varies; paper shows through |
| Paper | Grain and a warm tone, not pure white |
| Boil | In animation, the texture changes every few frames (12 fps): it is alive |

A brand built on paper, ink and one accent is already a two-ink palette: screen print suits it naturally.

## 1b. Real textures: paper, fabric, glass

A scanned or photographed texture gives matter that code noise does not: fibres, creases, uneven ink. Keep the file in
the piece's `assets/` (captures load nothing from outside the folder) at the frame size or a little larger.

```js
// setup()
paper = await env.loadImage('assets/paper-crumpled.jpg');
// draw(), after the picture on base: the texture multiplies, so white stays white and the ink darkens a little
base.save(); base.globalCompositeOperation = 'multiply'; base.globalAlpha = .3;
base.drawImage(paper, drift[0], drift[1], W * 1.04, H * 1.04);   // a little larger, so a slow drift never shows an edge
base.restore();
```

| Texture | Blend | Opacity | Notes |
|---|---|---|---|
| Light paper over a flat colour | `multiply` | 0.2–0.4 | The default layer of matter; keep it off small text if it drops contrast |
| Dark paper or fabric as the ground | normal (draw first) | 1 | Text in a light ink; check contrast on the real pixels |
| Glass, light streaks | `screen` on base, or draw on the `light` layer | 0.3–0.8 | On `light` it feeds the bloom: it glows |
| Any texture that should feel printed | `multiply`, then `Stage.looks.print` | 0.2–0.3 | The halftone of the print pass sits on top of the scan |

- **Move it a little.** A texture that stays perfectly still while everything moves reads as a sticker. Drift it 1–2 %
  of the frame over the piece, or jump its offset on a 12 fps grid (a "boil" of the paper, see [stepped
  time](stepped-time.md)). Same offset for the same `t`: compute it from `t`, never from a counter.
- **Resolution.** Draw at 1:1 or downscale. An image upscaled more than about 1.5× looks soft: use it only blurred or as
  light.
- **Tiling.** Only textures with matching edges tile; test by drawing two copies side by side at full size.
- **The platform's re-encode** eats fine paper grain first: check it ([formats §7b](../edit/formats-platforms.md#7b-survive-the-platform)).
- **Provenance.** Record where each file came from and its licence next to it; generated or AI-enhanced textures say
  so in their metadata (`xmp:CreatorTool`). A public repository or a client job needs a licence you can show.

## 2. The `screenPrint` pass

It runs on the tone-mapped (sRGB) image, so after `finish`:

```javascript
fx.finish(scene, bloom, {to: tmp, toneMap: 'shoulder'});
fx.pass('screenPrint', {textures: {image: tmp}, uniforms: {
  res: [1080, 1920], paper: [.95, .94, .91], inkA: [1, .27, .18], inkB: [.08, .08, .09],
  inks: 2, cell: 10, angleA: .26, angleB: .785,          // 10 px halftone; red at 15°, black at 45°
  offA: [4, -3], offB: [-1, 1],                         // misregistration in px
  texture: .6, seed: Math.round(MotionMath.posterize(t, 12) * 12),   // uneven ink that boils at 12 fps
  strength: 1}});                                       // 0.25–0.4 = a subtle layer over the piece
```

- `inkB` (black) comes from the image's darkness; `inkA` (accent) from its redness. `inks: 1` = one ink.
- `strength` mixes with the original: 1 is a full screen print; 0.25–0.4 is a **layer** that adds matter without
  changing the piece.

| Variant | Settings | When |
|---|---|---|
| J1 · One-ink halftone | `inks 1` (or 2 on a greyscale image), `cell 8–9`, no texture | Graphic portraits, black-and-white scenes |
| J2 · Two inks with misregistration | `inks 2`, 3–5 px offsets | Riso look; scenes with the accent colour |
| J3 · Boiling texture | J2 + `texture 1` + `seed` and misregistration changing at 12 fps | With stepped time (pairs with K3) |
| J4 · Subtle layer | `strength .3–.4`, `cell 6–8` | Over any piece, to take the digital edge off |

## 3. Rules

- **The halftone lives on the screen**, not on objects: it neither moves nor scales with them (as in real print,
  and it prevents moiré).
- **Dots of 6 px or more** at 1080 wide: finer ones turn to mush in H.264. Encode at CRF ≤ 18 and check an MP4
  frame at full size; check a 720-wide downscale for moiré.
- **Small text is not screened**: draw it after the pass or in solid ink. A large headline survives the halftone.
- **Boil at 12 fps**, not 60: at 60 the texture reads as video noise, not paper.
- **Blur before print**: transition blurs go before the pass, so a printed frame of a moving image keeps crisp dots
  (blurring the dots draws spokes and moiré).
- **Misregistration on the hits**: kick the ink offsets with `impulse(t, hits)` (8–10 px) and let them settle.
- **A narrative use**: print the flat world and lift the print when the story moves to depth (glass, light, focus):
  the texture itself becomes the turn.
- The accent is one ink: it is not screened in accent and black at once (the pass subtracts black where the accent is).
- Expect heavy files: a full-frame halftone at CRF 14 can weigh ~3× a clean piece.

## 4. In After Effects

Built with adjustment layers and third-party plugins (halftone, channel shift, fractal noise stepped with Posterize
Time) or scanned textures in Multiply. Here it is one deterministic pass, no plugins.

## 5. Check

- An MP4 frame at full size: moiré, dots merging, banding; and the same frame scaled to 720 wide.
- The accent colour is still recognisable.
- The headline reads at phone size.
- In J3, consecutive frames: the texture changes every 5 frames (12 fps), not every frame.
