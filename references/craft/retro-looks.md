# Retro looks: CRT, VHS, glitch (and stories)

Read for a vintage screen, glitch, VHS or TV look, or for a short vertical story. Pass: `crt` in
`scripts/kit/postfx-glsl.js` (compact); the full two-pass recipe is below.

## 1. Short stories as a format

- 1080×1920, 5–8 s. One idea and one or two lines; seen once, then gone.
- Working safe area: x 80–1000, y 270–1580 (progress bar and name on top, reply bar at the bottom) — verify with a
  real screenshot ([formats & platforms](../edit/formats-platforms.md)).
- A story derived from a reel reuses the actor or asset and changes the language: it is not a crop of the reel.
- In `plan.json`: `"format": "story"` and, for this look, `"mode": "retro"`.
- **Weight**: with snow, grain or glitch, CRF 14 gave 86 MB for 7 s; CRF 20 gave 34 MB with no visible loss in the
  checked frames. Archive the heavy version, do not delete it.

## 2. The CRT / VHS recipe in two passes

1. **Content at half resolution** (540×960): the image with horizontal glitch slices and RGB separation, hash snow,
   and the text layer on top. Half resolution already gives the tube's softness.
2. **Tube at full resolution** (1080×1920): barrel curvature, rounded corners, power-on and power-off squash
   (vertical scale down to 0.4 %, then horizontal), a tracking band moving down, row jitter during glitches, RGB
   misconvergence, phosphor glow (8 taps around), scanlines every 3 px (`cos(y·2π/3)`), an RGB aperture grille per
   column, vignette, fine noise and a faint glass reflection.
   If the platform scales video to 720 wide (verify), a 3 px pattern becomes 2 px and can moiré: check an MP4
   scaled with `-vf scale=720:-2`; if it appears, raise the period to 4–6 px or drop the grille and keep the lines.
3. **VHS text**: a 270×480 canvas redrawn every frame and uploaded with NEAREST filtering (fat pixels). A
   semi-transparent caption box behind, a blinking cursor, a 1 px dark outline. Corrupt the text with glyphs
   `#%&@$/\|<>01?*` chosen by hash. OSD: "▶ PLAY" (drawn triangle, not a glyph), "SP", a counter; "CH 03" and
   "NO SIGNAL" before locking on.

Timings that worked (7 s): power-on 0.10–0.42 s, snow until 1.00 s, signal locks with a glitch jump, first line
typed 1.15–1.85 s, glitch 2.70–3.15 s, second line 3.30–4.40 s, degradation from 5.60 s, power-off to a line and a
dot 6.25–6.95 s.

## 3. Learned the hard way

- **Legibility on a small canvas**: 11 px on a 270-wide canvas is 44 px final, unreadable. OSD at 13 px (52 final)
  and captions at 20 px (80 final) with a box behind worked.
- Measure positions with every line visible: a counter collided with the second line.
- **Deterministic glitch**: an integer hash of (frame, index); never `Math.random()`. During a glitch, update the
  actor at 12 fps so it stutters.
- **No motion blur**: one sample per frame; the glitch must read crisp.
- One word in the accent colour: the retro look already brings plenty of texture.

## 4. Sound

TV and tape vocabulary (power-on thump, hum, tape hiss, tracking warble, degauss) in [sound design](sound-design.md).
Measure with `audio_check.py` like any piece.

## 5. Other retro looks, not yet battle-tested

16 mm film (grain, gate weave, light burns), green or amber phosphor monitors, simulated datamosh, risograph
(see [print & textures](print-textures.md)). Mark them as first attempts and run the full
[review protocol](../produce/review-protocol.md).
