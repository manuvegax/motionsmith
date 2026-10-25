# Captions and titles

Text on screen in motion pieces: burned-in captions, lower thirds, title cards and end cards. Read it when a piece has speech, a title, a name or a call to action. Text is part of the picture here, so it follows the same rules as cuts, holds and the grade.

Most short-form is watched muted at first. A caption is therefore not decoration: it is the piece's speech for the viewer who has no sound.

## 1. Burned-in or sidecar

| Choice | Use when | Trade-off |
|---|---|---|
| Burned-in (drawn in the picture) | The caption style is part of the look; the platform will not show a sidecar file | Fixed style; cannot be turned off or changed by the viewer |
| Sidecar file (SRT or VTT) | Accessibility on a player that supports it; translation | The viewer or the player controls the style |
| Both | A long piece with a strong style, and a need for accessible text | Two sources to keep in sync |

- Accessibility guidance (WCAG 2.2, success criterion 1.2.2, captions for prerecorded media) asks for captions on speech. Burned-in captions meet the need for sound-off viewing; the sidecar meets the need for a text alternative in players.
- Keep the caption text in one place: `plan.captions`, either the `captions.json` written by `scripts/captions.py` or inline lines `{text, start, end}` ([plan schema §1b](../produce/plan-schema.md#1b-edit-fields-optional-checked-when-present)). Render the burned-in version and the sidecar from it.

## 2. Reading speed

| Measure | Value | Basis |
|---|---|---|
| Characters per second | 15 | `MotionMath.readingTimeChars` default; subtitle practice is about 15–17 cps for adults (verify against your own style guide) |
| Words per second | 3.5 | `MotionMath.readingTime` default (practice). It gives less time than characters for long words: use `readingTimeChars` by default, and the larger of the two when you have both |
| Shortest time on screen | 0.8 s | `floor` in the kit (practice) |
| Lines per caption | 2 at most | Subtitle convention (practice) |
| Entrance and exit | 0.1–0.2 s each | Practice for captions; a longer fade reads as a delay. Display type: [kinetic typography §1](../craft/kinetic-typography.md#1-the-reading-budget-rules) |

```js
const text = 'Read it at the pace of speech';
const shown = MotionMath.readingTimeChars(text, {charsPerSecond: 15, floor: 0.8, extra: 0.3}); // + entrance and exit
```

- A caption must stay on screen at least as long as its reading time. Check the whole plan at once:

```js
const tooShort = plan.captions.filter(c => (c.end - c.start) < MotionMath.readingTimeChars(c.text));
```

- A caption that is read faster than it is spoken is a caption the viewer cannot follow. Split it, or shorten it.

## 3. Caption styles

| Style | What moves | Timing | Good for | Fails when |
|---|---|---|---|---|
| Karaoke (word by word) | The active word changes colour or weight | Each word's `start` and `end` from the transcript | Speech with a rhythm, music-led pieces | Word timing drifts by more than a frame |
| Keyword highlight | One or two words change colour, weight or size | Each keyword on its own beat | Argument, instruction, the point of a line | More than two highlights in one line |
| Pop-on | The whole phrase appears at once, holds, leaves | On a hit, held for the reading time | Short lines, punchy statements | A phrase longer than its reading time |

Karaoke, in code:

```js
// plan.words: [{text, start, end}] from the transcript, in seconds.
const ink = [240, 236, 226], accent = [255, 92, 60];           // sRGB; the active word takes the accent
const colourOf = w => (t >= w.start && t < w.end ? accent : ink);
const entrance = i => MotionMath.stagger(i, plan.words.length, {each: 0.06, from: 'start'});
```

- The karaoke highlight is part of the graded picture. Check its contrast on each frame it changes (see [color-grade.md](color-grade.md), section 4).
- Keyword highlights work best when the highlight arrives on a hit (see [music-editing.md](music-editing.md)), not on a silence.

## 4. Placement per format

| Format | Where captions sit | Notes |
|---|---|---|
| 9:16 vertical (Reels, TikTok, Shorts) | Middle third, above the bottom band where platform UI sits | The bottom band is covered by captions, buttons and the caption of the post (see [formats-platforms.md](formats-platforms.md) for the margins) |
| 4:5 feed | Lower third of the frame, with a margin | Platform UI is lighter than in vertical formats (verify) |
| 1:1 feed | Lower third, centred | Keep clear of the edge |
| 16:9 | Lower third, centred or lower-left for names | Standard subtitle position |

- Keep the caption block inside the safe margins for the format, not the raw frame. For 9:16, keep the block above about y = 1440 px at 1080 × 1920 (practice; see the margins in [formats-platforms.md](formats-platforms.md)).
- Do not cover a face, a hand or the payoff with the caption. Move the caption up when the subject is in the lower half.

## 5. Lower thirds

A name, a role or a term, shown for a moment, usually near the start of a person's first appearance.

| Part | Timing | Note |
|---|---|---|
| Enter | 0.5 s after the cut, over 0.2–0.3 s | Not on the cut itself: the eye must have the shot first |
| Hold | 3–4 s (practice) | Long enough to read two lines |
| Leave | 0.3 s | Leave on the beat of the next change if one is planned |

- In 9:16, move the lower third up to the middle third; the bottom band is covered by platform UI.
- Lower thirds on bright areas fail. Put a dark plate behind them.

## 6. Title cards

- A title card holds 2–3 s, and carries one idea. More than about six words needs two cards (practice).
- Give the title motion within the first frame (see [pacing-retention.md](pacing-retention.md), section 1). A still title card is a swipe.
- Size: one table for every guide, in [kinetic typography §5](../craft/kinetic-typography.md#5-legibility-on-a-phone): at 1080 wide, titles 100–150 px, captions 70–90 px, nothing that must be read under 48 px.

```js
const titleWords = titleText.trim().split(/\s+/).length;
const titleHold = Math.max(MotionMath.readingTime(titleWords, {wordsPerSecond: 3.5, floor: 1.5}), 2);
```

## 7. End cards

- The end card holds the last 3–5 s (practice). It carries the title, the handle or the call to action, as text.
- The payoff must finish before the end card starts. An end card on top of the payoff is a missed answer.
- End-screen rules differ per platform, and they sometimes take over part of the frame (verify per platform).

## 8. Legibility of the type itself

- Use a legible face with a weight of 600 or heavier for captions (practice). Thin weights break up in motion and on compressed video.
- Line height 1.2–1.3 and small or zero letter-spacing for captions (practice).
- Keep kerning when you split text into letters: `MotionMath.layoutGlyphs(text, measure)` places graphemes at the measured prefix, so accents and kerning survive.
- Add a plate, an outline or a shadow when the text crosses a bright area. Test it against the contrast rule in [color-grade.md](color-grade.md).

## 9. Checks

- [ ] Every line of speech has a caption, with the reading time met (`tooShort` above is empty).
- [ ] Karaoke timings are within one frame of the audio.
- [ ] No more than two keyword highlights per line.
- [ ] Captions sit inside the safe margins of their format.
- [ ] Lower thirds leave after 3–4 s and are not over a face.
- [ ] Title cards hold 2–3 s and carry one idea; the first frame moves.
- [ ] End card starts after the payoff.
- [ ] Contrast passes at its minimum in every frame the text is on screen.

## 10. How to check

- Sample frames at the first, middle and last frame of each caption with `node scripts/sample_frames.mjs --root <piece> --out <folder> --times <list>`, then a contact sheet: `python scripts/contact_sheet.py <folder> --out <sheet.jpg>`.
- Enlarge the caption block on the sheet with the crop option: `python scripts/contact_sheet.py <folder> --out <sheet.jpg> --crop x,y,w,h --tile 520`, to read the letters as a viewer would.
- Check the audio and the caption together by watching the export, not only the sheet. A sheet cannot show timing.

Related: [cutting.md](cutting.md) for where text joins a shot; [transitions-atlas.md](transitions-atlas.md) for text joins (letter stagger, word swap, mask reveal); [kinetic-typography.md](../craft/kinetic-typography.md) for type in motion; [formats-platforms.md](formats-platforms.md) for the safe margins; [story-structures.md](story-structures.md) for the end card's place in a structure; [color-grade.md](color-grade.md) for contrast.
