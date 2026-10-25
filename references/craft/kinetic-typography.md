# Kinetic typography

Read whenever text moves: headlines, phrases entering letter by letter, typed captions, words hitting on a beat,
type as the main character. Captions and title cards for editing: [captions & titles](../edit/captions-titles.md).
Module: `scripts/kit/kinetic-type.js` (`KineticType`), built on `MotionMath.layoutGlyphs` and `stagger`.

## 1. The reading budget rules

- `MotionMath.readingTime(words)`: ~3.5 words/s, at least 0.8 s per line, +0.3 s for names, figures or rare words.
- `MotionMath.readingTimeChars(text, {charsPerSecond: 15, floor: .8})`: the same budget in characters, better for
  long words and short phrases (subtitle norms sit around 15–17 characters/s). When they disagree, use the larger.
- Entrance and exit are **separate**: while text moves or is blurred, it is not being read yet.
- With recorded voice, the text follows the voice; measure the speaker's own rate (fast speakers reach 2.7+ words/s).

| Segment | At 60 fps | Note |
|---|---|---|
| Entrance | Captions and supers 6–12 frames (0.1–0.2 s); words and lines of a kinetic piece 12–24 (0.2–0.4 s); a headline that *is* the event up to 30 (0.5 s) | The single source for text entrances; in the hook, text is readable within 12 frames |
| Reading | `readingTimeChars()` (characters, the default); `readingTime()` only when you count words; with both, the larger | From the first sharp frame |
| Exit | 10–24 frames, ≤ entrance | On a hard cut, leave with the cut |
| Offset per letter | 1–2 frames | Cascade totals: [rhythm §5](rhythm-sync.md#5-cascades-stagger) |
| Offset per word | 3–6 frames | Same |

## 2. Animators (After Effects range selectors)

In After Effects an animator moves properties per character, word or line through a selector that sweeps the text,
with shape, ease high/low and random order. In code:

```javascript
// progress of letter i: stagger delay and its own curve
const start = t0 + MotionMath.stagger(i, n, {each: .022, from: 'center'});   // 'start', 'end', 'edges', 'random' (seeded)
const u = MotionMath.clamp((t - start) / dur);
const p = MotionMath.easing('back.out')(u);
// position, rotation, scale and blur of the letter come from p; the letter does not exist before its start
```

- **Per character, word or line**: group indices before computing the stagger.
- **Selector shape** (square, ramp, triangle, round) = the curve that distributes the delay (`stagger(..., {curve})`).
- **Random order** with a fixed seed: `from: 'random', seed`.
- **Switch each letter off before its cue**: progress clamped at 0 can still draw it displaced.
- **Letter positions**: `MotionMath.layoutGlyphs(text, s => ctx.measureText(s).width)` returns `{ch, index, x, w}` per
  grapheme (Intl.Segmenter, NFC). Measuring the prefix instead of summing widths keeps kerning, and accented letters
  or composed emoji never split in two.

## 3. The operations menu

| Operation | Build | Careful |
|---|---|---|
| Fade | Opacity 0 → 1 | The safest for captions |
| Rise | 20–60 px + fade | Big distances make the eye follow the trip instead of reading |
| Scale pop | `1 + 0.14·sin(πu)` or a spring 0.85 → 1 | Never scale a whole sentence |
| Mask reveal | Clip by the line box | Do not cut accents or descenders |
| Tracking | Move letter positions | Do not animate `letter-spacing` with reflow: it trembles |
| Weight change | Variable font axis 400 → 700 over ~16 frames | Never fake bold by scaling |
| Per-letter 3D turn | `rotateX/Y` with perspective | Blur consistent with the turn |
| Per-letter blur | Radius reaching 0 with the entrance | Letters land sharp |
| **Font cycling** | Each letter steps through 2–3 faces at 12 fps for 0.2–0.3 s, then locks on the main face | Same cap height (scale each face to the main glyph box); locks before reading |
| **Glitch while read** | Each 12 fps step, a letter has a ~8–10 % chance to show another face for one step | Seeded hash per step; the word must stay readable |
| **Boil** | 4–5 px of stepped jitter per letter at 12 fps while read | Stepped, never a slide; keep it under 6 px |
| **Outline echoes** | 2–4 outline copies offset behind the word, sliding out and wobbling at 12 fps | Thick enough stroke (≈ 2.8 % of the size) to survive textures |
| **Shock ring** | Outline copies scaled up 4–16 % and fading on a hit | On the beat; ≤ 0.6 s |
| **Same-word stack** | The word repeated behind itself, offset (an extrusion of copies) | When the line *means* repetition |
| **Inversion flash** | Background and letters swap colours for one 12 fps step, twice | An accent inside a hold, never during the first read |
| Typewriter with cursor | Character count from t, stepped at 12 fps; cursor blinking 2–5 Hz | Crop the line texture, do not re-layout |
| Scramble / decode | Glyphs replaced by a seeded hash until their cue | Deterministic per frame |
| Text on a path | `pathSampler` + rotation from the tangent angle | Optical spacing on curves |
| Marquee / ticker | A long line of type tiling the frame and sliding at constant speed | Linear speed; outline at 6–12 % opacity behind content |
| Beat stamp | Enters on a `hit` with a pop and a short shake | One phrase per hit |

The rows in bold come from production: they kept long reading holds alive without hurting legibility.

## 3b. Variable fonts: weight and width in motion

The font kit (`templates/fonts/`, copied into every piece) gives Canvas 2D two animatable axes on **Archivo**:

| Axis | Range | How to animate it | Reads as |
|---|---|---|---|
| Weight | 100–900, continuous | a number in the font string: `Stage.font({weight: M.mix(260, 900, u), size, family: SANS})` | a letter that lands from thin to black, a word that breathes |
| Width | 62–125 % in Canvas's nine keywords | `Stage.font({stretch: 'extra-condensed'})` or `ctx.fontStretch`, stepped | a slam: condensed → normal on a 12 fps step |

- **Weight landing**: each letter enters at 250–300 and settles at its final weight with the same curve and stagger as
  its position, so the type gains mass as it stops (the kinetic quote recipe).
- **Width slam**: the hero word goes `extra-condensed → condensed → semi-condensed → normal` over its landing on the
  12 fps grid; the steps read as a stamp, not a stretch (the kinetic quote's keyword).
- **Weight that tracks**: a wordmark closes its letter spacing while its weight rises from 300 to 800 (the logo
  reveal).
- Lay out the line at the **final** weight and width: lighter and narrower stages are smaller, so nothing collides.
- Fraunces (serif, variable weight) and JetBrains Mono (variable weight) animate weight the same way; Canvas cannot
  reach Fraunces' other axes (optical size, softness), so use it for weight only.
- A face you add yourself animates only the axes its `@font-face` declares (`font-weight: 100 900`,
  `font-stretch: 62% 125%`).

## 4. Hierarchy in motion

- Entrance order is reading order.
- One accent per line: one word in the accent colour or a heavier weight.
- Size contrast between headline and support; support enters 4–8 frames after the headline settles.
- Text appears when the camera arrives; interface text lives outside the camera.
- Type that acts: give weight with scale around a stable anchor; reveal by semantic group; show a substitution by
  keeping the baseline while one word takes another's place; turn a letter's counter into a window to the next scene.

## 5. Legibility on a phone

- The one size table (every guide links here). Sizes at 1080 px on the short side; scale with it.

  | Role | Size | Share of the short side |
  |---|---|---|
  | One word or a short phrase that fills the screen | 280–490 px | 26–45 % |
  | Serif italic second voice | 150–180 px | 14–17 % |
  | Headline, title, multi-line statement | 100–150 px | 9–14 % |
  | Burned-in captions | 70–90 px | 6.5–8 % |
  | Support read once: labels, roles, eyebrows, sources | 48–64 px | 4.5–6 % |
  | Floor for anything that must be read | 48 px | 4.5 % |

  On a phone 48 px of a 1080 frame is about 9 pt, and the platform's re-encode softens it further. Test at phone
  size; a profile can set the project's own sizes.
- Contrast (WCAG relative luminance, measured on the real pixels): under white text the background is ≤ 18 % for
  captions and body (4.5 : 1) and ≤ 30 % for display type (3 : 1); under black text, ≥ 18 % and ≥ 10 %. Over noisy
  backgrounds, a box or a wide soft shadow. Thresholds: [color grade](../edit/color-grade.md).
- **Break on phrases, not on widths.** Never end a line on an article, preposition or conjunction ("the", "of", "a",
  "de", "la", "y"); keep a number with its unit and a name with its surname; no stub line under about a third of the
  width; then balance the lengths. `env.fitLines` (kit/stage.js) does this: "what the mind / is ready for", never
  "what the / mind is / ready for". A `|` in the text forces a break where meaning needs one.
- **Leading**: 0.9–1.0 × size for capitals and tight display sans; 1.05–1.15 for lower case with descenders; 1.15–1.25
  for captions.
- **Tracking**: display type over ~200 px tightens by 1–3 % of the size; capitals and small labels open by 5–12 %;
  never open lower-case text.
- **The hero is bigger, not only redder**: the word that carries the idea is 1.5–3× its neighbours or set on its own
  line ([art direction](../create/art-direction.md)). Colour alone is a weak hierarchy.
- **Scripts that join or run right to left** (Arabic, Hebrew, Devanagari, Thai): per-letter animators draw each
  grapheme on its own, which breaks joining and reverses the reading order. Animate whole words or whole lines there.
- Fit long titles to the safe area: shrink the font from the measured width, centred on the frame
  (`fitWidth = 2 · min(W/2 − safe.x, safe.x + safe.width − W/2)`), as the [starter](../../templates/starter/piece.js) does.
- Measure with the font loaded: in Canvas, `measureText` gives the advance, not the ink; a per-letter entrance can
  collide even when the whole word fits.

## 6. Check

- The first sharp frame of each line (dense window) and the frame where the exit starts: the gap ≥ `readingTime()`.
- The full line at phone size, including its last character.
- No letter visible before its cue (frames before the entrance).
- Font cycling and glitch: every face loaded (`determinism_check --font …`); the locked face is the main one.

## Sources

`kinetic-typography` skill (SkillMedev, MIT): reading budget, entrance/exit timing. Adobe, "Animating text"
(animators and selectors). `bang-motion` skill (MIT): contrast under text.
