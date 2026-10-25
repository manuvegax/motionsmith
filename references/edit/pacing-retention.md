# Pacing and retention

How a piece keeps a viewer past the first second, then past the middle, then to the end. Read this when you shape a hook, a hold, a density curve or an ending. Numbers are at 60 fps unless stated; "practice" marks a working value to test on your own pieces, not a measured rule.

## 1. The first frame must move

Short-form is decided by a swipe. A still first frame gives the viewer a reason to leave before the piece has begun.

- Frame 0 is not blank and not a title card at rest. Something is already changing.
- Motion starts within 3 frames (0.05 s) of t = 0.
- A fade from black lasts at most 3 frames. A longer fade is a swipe.
- Text in the hook is readable within 0.2 s of its entrance (practice). Entrance lengths by role: [kinetic typography §1](../craft/kinetic-typography.md#1-the-reading-budget-rules).

```js
// Start big and settle: the first frame already has motion, no rest state at t = 0.
const scale = MotionMath.tween(t, 0, 0.3, 1.12, 1, 'power3.out');   // 1.12 at t = 0, 1.0 at 0.3 s
```

## 2. The hook: 0–1 s, then the 3-second gate

| Time | What must be true |
|---|---|
| 0.0 s | Something is moving; the frame carries a question, a claim, an anomaly or a number |
| 0.5 s | The viewer knows what kind of piece this is |
| 1.0 s | The viewer knows what they are waiting for |
| 2.0 s | First re-hook (see section 3) |
| 3.0 s | The gate: the viewer has decided to stay or leave |

- The 3-second gate is a craft heuristic, not a platform rule. Platforms publish their own retention curves; compare the drop-off at 0–3 s with them where the platform exposes it (verify per platform).
- Before 3 s the piece should have changed state at least three times: a cut, a hit, a text change, a layout change or a camera move (practice).

## 3. Re-hooks every 2–4 s

A re-hook is anything that makes the viewer's attention jump again. Plan them on the same timeline as the cuts and hits.

| Interval | Re-hook type | Example |
|---|---|---|
| 2–4 s | Cut to a new framing | Wide to close |
| 2–4 s | Audio hit | Impulse on the cut frame |
| 2–4 s | New question | A line of text asks what comes next |
| 3–4 s | Layout change | Text moves from left to right |
| 3–4 s | Colour or light change | A single-accent flip (within flash limits, section 9) |

- Two re-hooks of the same type in a row stop working. Vary the type.
- A re-hook at a silent moment is worth more than one on a loud moment: silence is the contrast.

## 4. Density curve over the piece

Density is the amount of change per second: cuts, hits, text changes and layout changes. Plot it for the whole piece before you animate it.

```js
// Changes per 1-second window: cuts plus hits. Text changes are counted the same way.
const density = s =>
  plan.cuts.filter(c => c >= s && c < s + 1).length +
  MotionMath.normalizeHits(plan.hits).filter(h => h.time >= s && h.time < s + 1).length;
```

Shape of a good curve for a 15–30 s piece (practice):

| Section | Share of runtime | Density | Job |
|---|---|---|---|
| Hook | 0–10 % | High | Stop the swipe |
| Setup | 10–35 % | Medium | Give the viewer the frame to read the question |
| Build | 35–60 % | Rising | Add evidence, tighten the gap |
| Payoff | 60–80 % | Peak, then one breath of 0.5–1 s | Answer the question |
| Tail or loop | Last 15 % (2–4.5 s) | Falling or looping | Hold the answer and loop |

- A flat curve (same density from start to end) loses viewers in the middle.
- A curve that peaks in the hook and then falls is a common failure. The hook is the start of the build, not the peak.

## 5. Where the payoff goes

- The payoff lands at 65–85 % of the runtime for most short pieces (practice), the same window as the structures in [story structures](story-structures.md). For a 15 s piece that is about 10–13 s; for a 30 s piece, 19.5–25.5 s.
- Give the viewer one breath before the payoff: 0.5–1 s with no hit and no cut, so the answer lands.
- Do not place the payoff in the last second. The viewer must have time to take it in, and the loop must start from it.
- A payoff before 50 % makes the rest of the piece an aftermath. Use that only on purpose, as a reversal (see [story-structures.md](story-structures.md)).

## 6. Loopable endings

A loop plays again without the viewer noticing the seam. Replays count as views on most platforms (verify per platform), so a clean loop is worth the work.

| Loop mode | Behaviour | Use |
|---|---|---|
| `cycle` | Repeats from the start | Object returns to rest |
| `pingpong` | Goes forward, then back | Swings, breathing, pulses |
| `offset` | Repeats and adds the change of each cycle | A background that keeps drifting |
| `continue` | Keeps the final velocity after the period | A movement that carries past the end |

```js
const period = 6;                                               // seconds: 360 frames at 60 fps
const sweep = p => MotionMath.tween(p, 0, period, 0, 1, 'sine.inOut');
const u = MotionMath.loopValue(sweep, t, period, 'cycle');       // the seam is where u goes 1 → 0
```

- The seam must match in position and in velocity. A position match with a velocity break reads as a hitch.
- To loop a piece that changes state, end on the state of the first frame, or cut to a match of it (see [cutting.md](cutting.md), match cuts).
- Check: for a 6 s loop at 60 fps, frame 360 should match frame 0, and frame 359 should be the state just before rest, not a jump. The check is in [How to check](#11-how-to-check).

## 7. Catalogue of pattern interrupts

A pattern interrupt breaks a predictable rhythm for a few frames. Use it on a planned beat, not at random.

| Interrupt | Length (frames @ 60) | Kit or recipe | Fails when |
|---|---|---|---|
| Scale punch | 4–8 | `1 + 0.04 * MotionMath.impulse(t, plan.hits)` | Applied to text that must be read |
| Hit and shake | 6–12 | `MotionMath.shake(t, plan.hits, {px: 8})` | Shakes the whole frame including small type |
| Direction reversal | 1 cut | Element sign flips on a hit | No hit; the reversal is random |
| Speed change | 6–12 | `MotionMath.stepped(fn, 12)` for the stretch | Used for the whole piece |
| Typographic glitch | 2–3 | Horizontal slice offset from `MotionMath.hash(frame, seed)` | Lasts more than 6 frames; reads as broken |
| Inversion flash | 1–2 | Swap ink and paper for 1–2 frames | Over the flash limit (section 9) |
| Question on screen | 18 to type in | Text enters after 0.5 s | Too many questions in one 3 s window |
| Number count-up | 30–48 as an accent; 72–84 when the number is the hero ([scene recipes](../create/scene-recipes.md)) | `MotionMath.tween(t, t0, t1, 0, value, 'expo.out')` | The count ends before the reader can follow it |
| Focus pull | 18–30 | `PostFX` `lensBlur`, radius from 0 to about 0.01 | Blur reaches the subject |
| Echo | 3–6 copies | `MotionMath.echo(t, {count: 4, lag: 0.03, decay: 0.6})` | Copies overlap the text |
| Edge entry | 6–10 | Element enters from the frame edge | Edge overlaps the platform UI (see [formats-platforms.md](formats-platforms.md)) |

## 8. Open loops and the curiosity gap

The gap between what the viewer knows and what they want to know keeps them watching.

- State the question early: within 2 s of the start.
- Delay the answer, and show evidence that the answer exists.
- Close the loop at the payoff. An answer that is smaller than the question loses the viewer.
- For a short piece, keep one open loop at a time. Two loops compete.

| Loop type | Opened by | Closed by |
|---|---|---|
| Question | A line of text | The answer on screen |
| Object | A box, a door, a covered shape | Its contents are revealed |
| Number | A count that has not reached its target | The count finishes at the payoff |
| Process | A process that stops halfway | It resumes and completes |

- A loop that is never closed is a bait. Use it only if the piece is deliberately part of a series, and say so in the plan.

## 9. The holds rule (short-form)

In short-form, a stretch of more than about 0.5 s (30 frames) in which the frame barely changes loses viewers. The viewer reads "nothing happens" and leaves.

When a hold is needed (a read, a quote, a reveal that must breathe), give it inner accents:

| Accent | Frequency | Recipe | Note |
|---|---|---|---|
| Type glitch | 1–2 per second | Slice offset for 2–3 frames | Keep it under 6 frames |
| Echo | On a text change | `MotionMath.echo` | Lag 2–3 frames |
| Inversion flash | At most 3 per second | Ink and paper swapped for 1–2 frames | Check the flash limit below |
| Living background | Continuous | Slow `MotionMath.wiggle` or noise, 1–3 % of the frame | Amplitudes: [living layer §2](../craft/living-layer.md#2-three-levels-of-motion) |

```js
// A hold with inner accents: the background breathes and a glitch fires for 3 frames each second.
const breath = MotionMath.wiggle(t, {freq: 0.4, amp: 6, seed: 3});   // px, slow drift
const glitch = (t % 1) < 3 / 60 ? 1 : 0;                              // 3 frames at the start of each second
```

Flash limit: WCAG 2.3.1 (2.0, 2008; current 2.2) allows no more than three flashes in any one second, and ITU-R BT.1702 gives guidance for flashing and patterned images in broadcast. Keep every flash, including the inversion, under three per second and avoid large saturated red flicker.

## 10. Checklist

- [ ] Frame 0 is moving; no fade from black longer than 3 frames.
- [ ] Three or more state changes in the first 3 s.
- [ ] A re-hook every 2–4 s, and no two of the same type in a row.
- [ ] Density curve plotted; the peak sits after the hook and before the payoff.
- [ ] Payoff at 60–80 % of runtime, with a 0.5–1 s breath before it.
- [ ] Loop seam matches in position and velocity.
- [ ] Every hold longer than 0.5 s has an inner accent.
- [ ] Flashes under three per second.
- [ ] One open loop at a time, closed at the payoff.

## 11. How to check

- **Mean difference per sample**: sample the piece every 3 frames (for example with `node scripts/sample_frames.mjs --root <piece> --out <folder> --frames 0:600:3`) and compute the mean absolute difference between neighbouring frames. Flag any run longer than 30 frames below the threshold you set for the piece. There is no kit script for this yet; it is a planned check for [quality-rubric.md](../produce/quality-rubric.md).
- **Density**: print the density curve from section 4 for the piece and compare its shape with the table in section 4.
- **Seam**: for a 6 s loop, sample frames 359, 360 and 0 with `node scripts/sample_frames.mjs --root <piece> --out <folder> --frames 0:360` (or the list form), then look at the contact sheet. Frame 360 should match frame 0.
- **Platform data**: compare the piece's first-3-second drop-off with the platform's own retention data where it is shown (verify per platform).

Related: [cutting.md](cutting.md) for shot lengths; [transitions-atlas.md](transitions-atlas.md) for the joins; [story-structures.md](story-structures.md) for where the payoff goes in each structure; [captions-titles.md](captions-titles.md) for text that holds a hold; [living-layer.md](../craft/living-layer.md) for the background that breathes; [rhythm-sync.md](../craft/rhythm-sync.md) for placing re-hooks on a beat; [stepped-time.md](../craft/stepped-time.md) for speed changes.
