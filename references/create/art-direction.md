# Art direction: from brief to style frames

Decide the look before the motion. A style frame is one state of the piece at its final size, not a mood
board, and a sequence of style frames is judged as a set. This file covers the path from brief to approved
frames. The gates after motion are in the [review protocol](../produce/review-protocol.md).

## 1. The order of decisions

| Step | Decide | Output | Done when |
|---|---|---|---|
| 1 | The consequence sentence and the mode | one sentence; `mode` | it passes the two-sentence test in [ideation](ideation.md) |
| 2 | The style: one, two at most | a name from the [style atlas](style-atlas.md) | each layer has one owner |
| 3 | Palette roles | background, ink, support, accent | contrast checks pass on real pixels |
| 4 | Type roles | display, text, caption | fonts load and are measured |
| 5 | The texture budget | one primary texture | the texture has a stated function |
| 6 | Style frames | 3–5 frames at final size | each frame passes section 8 |
| 7 | Sequence compare | 5–7 frames across the piece | the set reads as one piece, with progression |

## 2. Hierarchy and one hero

- **One hero per moment.** Everything else supports it or waits.
- **Scale creates priority.** As a starting point, the hero is 2–4 times the size of the support text.
  Check this at 360 px wide, because that is roughly what a phone shows of the frame.
- **Squint test.** Blur the frame until the words stop being readable, and ask what is still visible. That
  should be the hero. If something else survives, the hierarchy is wrong.

## 3. Focal point and eye-trace

- Draw the path the eye takes: entry (an edge, or a hit) → hero → support → exit.
- The first thing the eye reaches must be the first word of the sentence. A path that circles back loses the
  reading order.
- Draw the eye-trace on three frames: the entry, the hero and the last state. Each one needs a single path.

## 4. Palette rules

- **Default:** neutrals plus one accent. Background and ink come from the neutral range. The accent appears
  only where it carries meaning, and covers about 10 % of the frame at most.
- **Roles, not swatches.** Record background, ink, support and accent in the plan's `palette` field, with
  their values. A role keeps its meaning when the swatch changes.
- **Legibility.** Behind white text the background is at most 18 % relative luminance for body and captions
  (4.5 : 1) and 30 % for display type (3 : 1) ([color grade](../edit/color-grade.md)). Measure the real pixels
  behind the text, after motion and grain.
- **Greyscale test.** Convert the frame to greyscale. The hierarchy must survive. An accent that differs only
  in hue disappears in greyscale.
- **Exact colours come last.** The tone curve moves saturated reds towards orange and white. A brand colour that
  must stay exact is composed after the tone map ([light and bloom](../craft/light-bloom.md)).

## 5. Typographic system

- **Two roles:** display and text. Add a caption role only when the content needs one.
- **Sizes**: one table for every guide, in [kinetic typography §5](../craft/kinetic-typography.md#5-legibility-on-a-phone)
  (hero 280–490 px, titles 100–150 px, captions 70–90 px, support 48–64 px, nothing read under 48 px, at 1080 on the
  short side). Story captions sit on a solid box.

- **Check the font file itself.** Accents, numerals and punctuation must exist in the font you ship. Measure
  with the loaded font. A Canvas `measureText` returns the advance width, not the ink, so inspect the last glyph.
- **Record the roles** in the plan's `font_roles` field ([plan schema](../produce/plan-schema.md)).

## 6. Texture budget

- **One primary texture per piece:** paper grain, print, scanlines, glass, or photo grain.
- **A second texture only as a subtle layer.** For a print pass, strength 0.3 or less. See [print textures](../craft/print-textures.md).
- **Every texture needs a function.** It must say where the piece comes from, or what material it is. If you
  cannot say it, remove it.
- **Never on small text.** Check the piece at 1080 and at 720 wide (scaled), where fine patterns can turn into moiré.
- **Grain** at 0.015–0.03 per frame also dithers gradients, which stops 8-bit banding.

## 7. Motion vocabulary per mode

Each mode has its own grammar. A piece mixes modes only on purpose, and the mode is written in the plan.

| Mode | Carrier and rhythm | Curves | Cadence | Transitions | Avoid |
|---|---|---|---|---|---|
| Editorial | cuts with matched anchors; long holds | `cubic.out` entries; `cubic.in` exits at 65–75 % of the entry | 60 fps | match cut, mask, camera | one ease on every element |
| Kinetic | one carrier links the scenes; cascades | `back.out` or a spring (ζ 0.4–0.6) for pops; `expo.out` for type | 60 fps | morph, wipe, whip | everything moving at once |
| Diagram | the relation first; connectors and counts | `linear` connectors; `power2.inOut` for bars | 60 fps; reveals in steps | stroke draw; cut when the data changes | overshoot on data |
| Glow | slow and damped; the light is the carrier | `power2.inOut` traverses; followers for lenses | 60 fps | light leak, bloom swell, glass morph | glow on all the text |
| Retro | a stepped subject, hard cuts, tracking | steps and `posterize` at 12 fps | subject 12 fps; camera 60 fps (hybrid) | glitch cut, tracking jump | smooth easing, which looks digital |

Overshoot is allowed where a material can carry it: a card, a shape, a spring. Text that must be read, the
camera and data do not overshoot ([principles](../craft/principles.md)).

## 8. Style-frame checks

- [ ] **Hero.** One per frame. The squint test returns it.
- [ ] **Eye-trace.** Entry → hero → support → exit is one path.
- [ ] **Reading.** At 360 px wide the key text is legible, and it matches the approved copy exactly.
- [ ] **Palette.** Roles recorded. The accent covers about 10 % or less. The greyscale test passes. Exact colours
  are composed after the tone map.
- [ ] **Texture.** One primary texture, with its function written down. None on small text.
- [ ] **Material.** At 100 % zoom the edges, cut-outs and grain are clean.
- [ ] **Sequence.** Five to seven frames compared at once. Composition changes between frames, not only the copy.
- [ ] **Mode.** The motion vocabulary in section 7 matches the mode in the plan.

## 9. Compare a sequence, not a frame

- Lay out five to seven frames in the piece's real order. Use `contact_sheet.py` with 4 columns and 360 px tiles.
- Ask whether the frames share one system (type, palette, texture) while the composition changes.
- A single attractive frame can hide a piece that repeats one composition for eight seconds. The set exposes it.
- When you compare against a reference, put them on one sheet and compare the operation, not the look. See
  [reference study](reference-study.md).
- For detail, crop the same region from each frame (`--crop x,y,w,h`) and read the crops side by side.

## 10. Sign-off

- Record the decision in the piece's notes: style, mode, palette roles, type roles, texture, and the frames
  approved, with their times.
- Approval of the art direction is not approval of the motion. After motion, the three gates in the
  [review protocol](../produce/review-protocol.md) apply: direction, choreography, material and optics.
- A frame that passes section 8 can still be generic in motion. If the piece reads as a template once it moves,
  return to the design, even when the render is technically correct.
