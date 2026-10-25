# Cutting

How to join one shot to the next so the viewer keeps the thread. Read this before deciding where a cut goes, and before writing any `plan.json` cut list. Timing numbers are at 60 fps unless stated.

A cut poses a question to the viewer: where am I, what changed, what matters now. A good cut answers that question before the viewer has to ask it. A bad cut makes the viewer stop and re-read.

## 1. Murch's rule of six

Walter Murch, *In the Blink of an Eye* (1995; 2nd ed. 2001), ranks what a cut must serve:

| Rank | Criterion | Weight | Question to ask at the cut |
|---|---|---|---|
| 1 | Emotion | 51 % | Does the cut keep, or deliberately move, the feeling the viewer has? |
| 2 | Story | 23 % | Does it advance what happens or what is known? |
| 3 | Rhythm | 10 % | Does it land in the pattern of the piece? |
| 4 | Eye-trace | 7 % | Is the eye ready, and does it know where to go? |
| 5 | Plane of the screen | 5 % | Does the 2D composition still work across the join? |
| 6 | Three-dimensional space | 4 % | Does the cut respect the space the viewer has built? |

- The weights are Murch's own estimate, not a measurement. Use them as an order: when two cuts both work, take the one that wins on the higher criterion.
- In motion graphics the last two criteria are the easiest to argue about and the least likely to decide a piece. Do not spend an hour on a 2D alignment that the emotion does not need.

## 2. Cut on action

Cut in the middle of a movement. The eye carries the movement across the join, and the join disappears.

- Direction and speed must match across the cut. Keep the speed within about 10 % (practice).
- A movement that changes speed at the cut is read as a second movement, not a continuation.

```js
// Shot A: a bar sweeps right. Shot B takes over while the bar is still moving.
const cutAt = 1.2;                                          // 72 frames at 60 fps
const sweep = MotionMath.tween(t, 0.8, 1.6, 0, 1, 'sine.inOut');   // one move that spans the cut: peak speed at 1.2
const frame = t < cutAt ? drawA({sweep}) : drawB({sweep, t: t - cutAt});  // B reads the same curve, so the speed carries over
```

`drawA` and `drawB` are the piece's own functions. The sweep value is a pure function of `t`, so both shots read the same number at the cut.

## 3. Match cuts

A match cut joins two shots through something they share. Three kinds:

| Kind | What must match | Check |
|---|---|---|
| Graphic | Shape, colour, position, size of one element | Same pixel position within a few px at 1080 wide |
| Action | Motion vector and speed through the join | Frame samples either side show the same path |
| Sound | A sound from one shot runs into the next, or both start on one beat | Listen with the picture; see [music-editing.md](music-editing.md) |

Thematic matches (a shape in one shot answered by another shape with a different meaning) are the classic form, as in the bone-to-spacecraft cut in Kubrick's *2001: A Space Odyssey* (1968). They work when the shape is the only thing that matters.

```js
// The circle in shot A and the circle in shot B share one set of numbers.
const disc = {x: 540, y: 960, r: 220};                      // px, 1080 × 1920 frame
const outgoing = t => drawA({disc});                       // A shrinks the disc to disc.r at cutAt
const incoming = t => drawB({disc});                       // B starts from the same disc
```

- A graphic match fails when the match is off by more than the eye ignores. A misalignment of 10 px at 1080 wide reads as an error, not a match.
- A match fails when the matched element changes size or speed on one side only.

## 4. J and L cuts

Sound and picture need not change on the same frame.

- **J-cut**: the sound of the next shot starts before its picture. The sound leads.
- **L-cut**: the picture changes and the sound of the previous shot carries on. The sound trails.

The names come from the shape the cut makes on a timeline.

| Offset between sound and picture | Effect | Use |
|---|---|---|
| 0 frames | Hard sync | Hits, impacts, anything that must read as one event |
| 6–12 frames (0.1–0.2 s) | The join feels soft | Narration, ambience, music under a change of image |
| 15–30 frames (0.25–0.5 s) | Clearly a J or L | Sound carries the scene change across the join |
| 30–120 frames (0.5–2 s) | A voice-over bridge | The narrator's line starts over the old image, or finishes over the new one |

- A J or L cut is a deliberate offset of a sound from its own picture. For a sync event (a hit paired with a visual), stay inside the detectability window of ITU-R BT.1359-1 (1998): sound about 45 ms early or 125 ms late starts to be noticed. Aim for zero.
- Keep the sound event and the picture event in the same `plan.json` `hits` entry when they are one event. Split them only for a J or L.

## 5. Jump cut

The same subject appears in a different position, scale or moment, with no transition. Jean-Luc Godard used it in *À bout de souffle* (*Breathless*, 1960) to make time feel compressed.

- A small change reads as a glitch. A large change reads as intent. Rule of thumb (practice): move at least about 10 % of the frame width, or change scale by at least 1.25×.
- Put a hit on a jump cut when the change must read as a decision.

## 6. Smash cut

An abrupt join from a quiet shot to a loud one, or from a calm image to a disturbing one. No transition; the impact is the transition.

```js
const hit = MotionMath.impulse(t, plan.hits);              // 1 on the hit, decays at 9 per second
const kick = 1 + 0.04 * hit;                                // a 4 % punch on the incoming frame
```

- The calm shot must last long enough to register: under about 0.5 s (30 frames) it is not felt as calm.
- Do not use it on every cut. Contrast is what makes the smash work.

## 7. Cross-cutting

Alternate between two or more threads that will converge. D. W. Griffith made the form standard in *Intolerance* (1916).

- Shorten the interval as the threads approach each other: for example 2.0 s, 2.0 s, 1.0 s, 0.5 s, 0.25 s.
- Write the cut times into `plan.json` as an explicit list. An integrated formula is harder to review than a list.
- It fails when the threads do not share a question, or when every interval is the same length (no escalation).

```js
// plan.json: "cuts": [0, 2.0, 4.0, 5.0, 5.5, 5.75, 6.0], threads alternate A, B, A, B...
const idx = plan.cuts.findIndex((c, i) => t >= c && t < (plan.cuts[i + 1] ?? Infinity));
const thread = idx % 2 === 0 ? 'A' : 'B';
```

## 8. Cutaway and insert

- **Insert**: a close view of a detail inside the same action (a hand, a number, the point of impact). Hold 6–30 frames (0.1–0.5 s) and return to the wide view.
- **Cutaway**: a jump to a different subject, then back to the action.
- Return to the main action within about 1 s unless the cutaway is the payoff.
- An insert with no link to the main action reads as a random cut.

## 9. The Kuleshov effect

The same neutral image, placed after three different shots, was read as three different emotions. Lev Kuleshov's experiments are reported in V. I. Pudovkin, *Film Technique* (1929).

- The meaning of a shot depends on the shot before it and the shot after it.
- Check it: place one neutral element (a plain shape, a face, a dot) after a warm image and after a cold image. Sample three frames of each join. If the neutral element reads differently, the piece is using the effect; if it reads the same, the cut is not carrying meaning.

## 10. Eisenstein's five methods of montage

Sergei Eisenstein described five methods in his essay "Methods of Montage" (1929), collected in *Film Form* (1949).

| Method | What sets the cut | Motion-graphics use |
|---|---|---|
| Metric | A fixed count (a metronome) | Beat-locked cuts, grid edits |
| Rhythmic | The movement inside the frames | Cuts timed to the speed of the motion |
| Tonal | The emotional tone of each shot | Mood change between sections |
| Overtonal | Metric, rhythmic and tonal together | The feeling that rises from the whole sequence |
| Intellectual | The collision of two shots makes a third idea | Juxtaposition of two images that mean something together |

The intellectual method is the classic one, as in the slaughter-house sequence intercut with the strike in *Strike* (1925). In short-form, use it sparingly: an idea that needs two shots to form is worth one collision per piece.

## 11. Continuity, the 180° rule, and screen direction

- **180° rule**: keep the camera on one side of the line of action. Crossing it reverses screen direction and confuses the space.
- **Screen direction**: an element moving right in shot A moves right in shot B, unless the cut is a deliberate reversal with a hit.
- **Persistent elements**: positions, colours and type sizes that carry across a cut must match within a few px and the same hue.

```js
// One camera side for the whole sequence: the eye stays on the same side of the subject.
const cam = MotionMath.lookAt([0, 0, 2400], [0, 0, 0]);    // same eye for every shot in the sequence
```

`MotionMath.lookAt` and `MotionMath.project` share one camera convention (screen y grows downwards). Keep the eye's side fixed when you build a sequence.

## 12. Eye-trace

The eye goes to motion first, then faces, the brightest area, text, and the largest element. At a cut the eye must find the new focal point.

- Put the new focal point where the eye was at the cut. The eye then does not search.
- Check it: mark the focal point on the last frame before the cut and on the first frame after. The distance should be short, about a quarter of the frame width or less (practice).

## 13. When to cut

Cut when the eye has read the shot, not before and not long after.

| Element | First read | Each extra element |
|---|---|---|
| Single image or shape | 0.3–0.5 s (practice) | +0.2 s |
| Short text | `MotionMath.readingTimeChars` (15 characters per second, floor 0.8 s) | Included in the count |
| Number or label | 0.5 s | +0.3 s |

```js
const caption = 'Cut when the eye is done';
const hold = Math.max(MotionMath.readingTimeChars(caption), 1.2);   // seconds to keep the shot
const cutFrame = Math.round((start + hold) * 60);                    // whole frames at 60 fps
```

- Round cut frames to whole frames. A cut on 2.4001 s is still one frame early or late in the export.
- After the read, do not keep the frame still. A hold longer than about 0.5 s needs a visible change; see [pacing-retention.md](pacing-retention.md).

## 14. Shot-length guidance for short-form

| Use | Shot length | Frames at 60 fps |
|---|---|---|
| Hook shot (first read of the piece) | 0.5–1.0 s | 30–60 |
| One idea, one image | 1.0–2.0 s | 60–120 |
| Text-led shot | Reading time plus 0.3 s | Variable |
| Beat-locked fast montage | 0.25–0.5 s | 15–30 |
| Hold without a visible change | 0.5 s at most | 30 at most |

These are working ranges (practice), not rules. Track the average shot length of each piece and compare it with the pacing guide.

## 15. Checklist

- [ ] Each cut passes the top criteria of Murch's ordering: emotion, then story.
- [ ] Direction and speed match across every cut that moves.
- [ ] One focal point at each cut, in the same place on both sides.
- [ ] Hits and their pictures share a frame, unless the cut is a J or L on purpose.
- [ ] The eye has read the outgoing shot before the cut.
- [ ] Screen direction is consistent and the 180° rule holds in 3D shots.
- [ ] Frame samples either side of every cut have been looked at.

## 16. How to check

- A dense window around a cut, with and without blur, to tell blur from geometry:

  ```
  node scripts/sample_frames.mjs --root <piece> --out <new-folder> --window 7.0:7.6:0.1
  node scripts/sample_frames.mjs --root <piece> --out <new-folder> --frames 420:432 --noblur
  ```

  `--frames` picks exact frame centres, the same instants `render_stream.mjs` captures.
- A labelled sheet for a reviewer: `python scripts/contact_sheet.py <new-folder> --out <sheet.jpg>`. A sheet helps the eye; it does not prove timing or sync. Delete the sample folder after review.
- For hits and J/L offsets, check the audio with `scripts/audio_check.py --plan plan.json` and see [music-editing.md](music-editing.md).

Related: [pacing-retention.md](pacing-retention.md) for hold lengths and pattern interrupts; [transitions-atlas.md](transitions-atlas.md) for the joins that are not plain cuts; [rhythm-sync.md](../craft/rhythm-sync.md) for placing cuts on a beat; [principles.md](../craft/principles.md) for the craft basics; [review-protocol.md](../produce/review-protocol.md) for how a reviewer looks at a sample.
