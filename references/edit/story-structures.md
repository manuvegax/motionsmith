# Story structures

A structure is an order of beats with a share of the runtime for each. This guide maps the common ones to scenes, durations and the shared `hits` list. Read it before you draw a storyboard, and before you write the scene list in the plan.

Every beat becomes three things in the plan: a scene (what is on screen), a duration (how long it holds), and zero or more hits (the moments that sound and picture share). If a beat has no hit, it still needs a scene; if a hit has no beat, remove it.

## 1. From beat to plan

```json
{
  "schema_version": 1, "width": 1080, "height": 1920, "fps": 60, "duration_frames": 900, "mode": "editorial", "format": "reel", "audio": "optional",
  "safe_area": {"x": 80, "y": 220, "width": 850, "height": 1220},
  "hits": [
    {"time": 0.0, "amplitude": 0.8, "role": "entry"},
    {"time": 1.2, "amplitude": 1.0, "role": "cut into the turn"},
    {"time": 9.75, "amplitude": 1.3, "role": "reveal"}
  ],
  "scenes": [
    {"id": "hook", "start_frame": 0, "end_frame": 72, "intent": "Beat: question", "action": "Open on the question, already moving", "text": "", "transition": {"kind": "cut", "carrier": ""}},
    {"id": "turn", "start_frame": 72, "end_frame": 360, "intent": "Beat: turn", "action": "The expectation flips", "text": "", "transition": {"kind": "cut", "carrier": ""}},
    {"id": "build", "start_frame": 360, "end_frame": 585, "intent": "Beat: evidence", "action": "One proof that the turn is true", "text": "", "transition": {"kind": "cut", "carrier": ""}},
    {"id": "payoff", "start_frame": 585, "end_frame": 765, "intent": "Beat: answer", "action": "The answer lands after a breath", "text": "", "transition": {"kind": "cut", "carrier": ""}},
    {"id": "loop", "start_frame": 765, "end_frame": 900, "intent": "Beat: return", "action": "The last image becomes the first", "text": "", "transition": {"kind": "end", "carrier": ""}}
  ]
}
```

A 15 s plan at 60 fps (900 frames) that passes `scripts/validate_plan.py`: the payoff starts at 65 % (9.75 s,
frame 585), inside the window of section 2. Field names and units: [plan-schema.md](../produce/plan-schema.md);
the validator checks the structure and never the taste.

```js
// The scene for time t, and the hits that drive the picture at t.
const frame = Math.floor(t * plan.fps + 1e-6);
const scene = plan.scenes.find(s => frame >= s.start_frame && frame < s.end_frame);
const hit = MotionMath.impulse(t, plan.hits);                 // the same list the sound reads
```

- Keep beat names short and the same across the plan and the sound file.
- Scene bounds are whole frames (`start_frame`, `end_frame`). Round once, in the plan, never again in the scene code.

## 2. Hook, turn, payoff

The basic short-form structure. The hook asks, the turn complicates, the payoff answers.

| Beat | Share | 15 s | 30 s | Hit at the start of the beat |
|---|---|---|---|---|
| Hook | 0–10 % | 0–1.5 s | 0–3 s | Entry hit, 0.8 |
| Turn | 10–50 % | 1.5–7.5 s | 3–15 s | Cut into the turn, 1.0 |
| Evidence | 50–65 % | 7.5–9.75 s | 15–19.5 s | Optional, 0.5 |
| Payoff | 65–85 % | 9.75–12.75 s | 19.5–25.5 s | Reveal, 1.3 |
| Return | 85–100 % | 12.75–15 s | 25.5–30 s | Soft, 0.3, or none (loop) |

- The turn must change what the viewer believes or expects. A turn that only repeats the hook is a long hook.
- The payoff must be the answer to the hook's question, not a new question.

## 3. Three-beat reveal

Show a thing, name it, show what it does. Good for objects, diagrams and small mechanisms.

| Beat | Share | What is on screen | Hit |
|---|---|---|---|
| Tease | 0–35 % | The object in part or in silhouette; no label | Soft entry hit |
| Reveal | 35–60 % | The whole object, labelled; the camera or the light moves once | Strong hit, 1.2 |
| Explain | 60–100 % | One mechanism at a time, each step built with a stagger | Small hit on each step |

- The explanation is one line of text per step at most. Reading time is in [captions-titles.md](captions-titles.md).
- A reveal that comes before 25 % of the runtime leaves the rest with nothing to do.

## 4. Before and after

Two states of one thing. The flip is the story.

| Beat | Share | Content | Hit |
|---|---|---|---|
| Before | 0–40 % | State A, shown long enough to be felt | Entry, 0.6 |
| Flip | 40–60 % | Transition from A to B (see [transitions-atlas.md](transitions-atlas.md)) | Strong, 1.2, at the flip frame |
| After | 60–100 % | State B, with one detail that A did not have | Soft, 0.4, at the detail |

- Keep the layout of A and B the same, so the eye can compare. Change one thing, or the comparison is not visible.
- For a loop: the after-state can return to the before-state, which needs a plan for the seam (see [pacing-retention.md](pacing-retention.md), section 6).

## 5. Escalating list

Several items, each one bigger than the last. The viewer counts, and the count is the tension.

| Beat | Share | Content | Hit |
|---|---|---|---|
| Item 1 | 0–20 % | The smallest case | Entry, 0.6 |
| Items 2 to N−1 | 20–80 % | Each one larger, 1.5–2.5 s each | Hit on each item change, 0.8 to 1.0 |
| Item N | 80–95 % | The largest case; the piece's payoff | Reveal, 1.3 |
| Close | 95–100 % | Title or one word | Soft or none |

- Keep each item between 1.5 s and 2.5 s; shorter than 1.5 s and the item is not read, longer than 2.5 s and the count stalls.
- Vary the scale of each item by a fixed step, so the escalation is felt and not only counted.

## 6. Loop

The last frame matches the first. The viewer watches again without noticing the seam.

- Choose the loop period first: 6 s, 9 s or 12 s, for example. Every beat is then a fraction of that period.
- `MotionMath.loop` and `MotionMath.loopValue` give the seam-safe time. See [pacing-retention.md](pacing-retention.md), section 6, for modes.
- A loop without a payoff is a mood piece. Name the intent in the plan before you draw it.
- The seam needs pose **and** speed to match, and the first frame must not appear twice: sample t in `[0, period)`.
  Mark `"loop": true` in the plan and check the MP4 with `loop_check.py` (seam ratio and speed ratio near 1).
  Brief: `templates/briefs/loop.md`.

## 7. Question, then answer

The question is on screen in the first second. The answer comes at the payoff.

| Beat | Share | Content | Hit |
|---|---|---|---|
| Question | 0–10 % | The question as text, or as a visual that poses it | Entry, 0.8 |
| Hold | 10–70 % | Evidence, one step at a time, that the answer exists | Hits on each step, 0.5 |
| Answer | 70–90 % | The answer, shown in the same place as the question | Reveal, 1.3 |
| Tail | 90–100 % | Answer held, then loop or end card | Soft, 0.3 |

- The answer must be the same size as the question or larger, or the viewer feels cheated.
- Place the answer where the question was. The eye returns to the same spot.

## 8. Problem, then reframe

The same situation seen from a new frame. The reframe changes one variable: the camera angle, the scale, the colour or the order of events.

| Beat | Share | Content | Hit |
|---|---|---|---|
| Problem | 0–45 % | The situation, shown as it is felt | Entry, 0.6 |
| Pressure | 45–60 % | The situation worsens (scale, speed or repetition) | Rising hits, 0.5 each |
| Reframe | 60–75 % | The same objects, one variable changed | Strong, 1.2 |
| Consequence | 75–100 % | What the new frame makes possible | Soft, 0.4 |

- Do not explain the reframe in words. Let the change do it, and let one line of text name it.
- A reframe that changes everything reads as a new piece. Change one variable.

## 9. Explainers

For concepts that need a mechanism. Typical length 30–60 s.

| Part | Share | Content |
|---|---|---|
| Definition | 0–15 % | The concept in one sentence, as text on a clean frame |
| Mechanism | 15–50 % | The diagram builds in steps, one step per beat |
| Example | 50–80 % | One concrete case, shown on the same diagram |
| Takeaway | 80–100 % | One sentence; the diagram holds |

- Each diagram step lasts at least its reading time: `MotionMath.readingTime(words, {wordsPerSecond: 3.5, floor: 0.8})`. A step with ten words needs about 3 s.
- Build the diagram with `MotionMath.stagger` over its parts, so the build order is one line of code and the timing is in one place.
- Give a **sequence with a start and an end**, not a topic ("a recipe from start to finish", "a request moving through
  a system"); topic-only briefs are where explainers turn generic. About five seconds per idea is a starting length.
- Name the **audience** in one line: it sets vocabulary and pace.
- **Facts**: research first; check every number, name, date and quote against a source and list them in the plan;
  never invent one. Brief: `templates/briefs/explainer.md` ([motion brief §6](../create/motion-brief.md#6-by-kind-of-piece)).

## 10. Ads, neutral frameworks

Use these to structure an ad for any product or idea. No brand is assumed.

| Framework | Beats | 15 s split | Notes |
|---|---|---|---|
| PAS (Problem, Agitate, Solve) | Problem, then deepen the problem, then the solution | 0–3 s, 3–7 s, 7–15 s | Direct-response copywriting tradition; the agitation is one visual escalation, not a list of fears |
| AIDA (Attention, Interest, Desire, Action) | Attention, interest, desire, one action | 0–2 s, 2–6 s, 6–12 s, 12–15 s | Attributed to E. St. Elmo Lewis, about 1898 (verify the year before citing) |

- Put the call to action in the last 2–3 s, as one line and one shape. Two calls to action compete for the same second; keep one.
- Captions are required for sound-off viewing; see [captions-titles.md](captions-titles.md).
- Platform sizes and safe zones for ads are in [formats-platforms.md](formats-platforms.md).

## 11. Title sequences

A title sequence states the idea of the piece before the piece starts. Saul Bass's sequences for *Vertigo* (1958) and *North by Northwest* (1959) are the classic reference: the title is the thesis, and the shapes carry the theme.

| Part | Share (30 s) | Content | Hit |
|---|---|---|---|
| Title card | 0–6 s | The shape moves from frame 0 and the title is readable by 3 s, held 2–3 s; the shape will return | Entry, 0.8 |
| Motif | 6–15 s | The shape transforms; each transformation is one idea | Hit per transformation, 0.6 |
| Handover | 15–18 s | The shape becomes the first image of the piece | Strong, 1.2, at the handover |

- A title card holds 2–3 s and carries one idea. A title of more than about six words needs two cards.
- The handover is a match cut (see [cutting.md](cutting.md)): the motif becomes the first image.

## 12. Structure at a glance

| Structure | Beats | Typical runtime | Hits | Loop |
|---|---|---|---|---|
| Hook, turn, payoff | 4–5 | 15–30 s | Entry, cut, reveal | Optional |
| Three-beat reveal | 3 | 15–45 s | Reveal, one per step | No |
| Before and after | 3 | 10–20 s | Flip, detail | Often |
| Escalating list | 3 + N items | 15–30 s | One per item change | Optional |
| Question, then answer | 4 | 10–20 s | Question, reveal | Often |
| Problem, then reframe | 4 | 15–30 s | Pressure, reframe | No |
| Explainer | 4 | 30–60 s | One per step | No |
| PAS / AIDA ad | 3–4 | 15–30 s | Problem, solve, CTA | No |
| Title sequence | 3 | 10–30 s | Title, motif, handover | No |

## 13. Checks

- [ ] Each beat has a scene, a duration and at least one reason to exist.
- [ ] The piece can be said in one sentence that contains the question and the answer.
- [ ] The payoff sits in its share of the runtime (see [pacing-retention.md](pacing-retention.md), section 5).
- [ ] Every hit maps to a beat, and every beat with a turn has a hit.
- [ ] `scripts/validate_plan.py` passes.
- [ ] A reviewer who has not seen the plan can say what the piece is about after one viewing of the contact sheet.

Related: [pacing-retention.md](pacing-retention.md) for the density curve and holds; [transitions-atlas.md](transitions-atlas.md) for the joins between beats; [music-editing.md](music-editing.md) for where the hits land in music; [ideation.md](../create/ideation.md) for choosing the structure; [scene-recipes.md](../create/scene-recipes.md) for what each scene looks like; [plan-schema.md](../produce/plan-schema.md) for the fields.
