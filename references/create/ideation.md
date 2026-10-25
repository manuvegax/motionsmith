# Ideation: ten visual concepts from any brief

Use this before any scene is built. It turns one brief into ten distinct visual concepts, scores them
against six criteria, and turns the winner into a storyboard with states and a `hits` list. Its output feeds
[art direction](art-direction.md) (style frames), [scene recipes](scene-recipes.md) (blueprints) and the
[plan schema](../produce/plan-schema.md). All times are at 60 fps.

## 1. Write the brief as one sentence

Fill this sentence before generating anything:

> The viewer must discover **X**. At the end, **Y** must be true.

If you cannot fill **X** and **Y**, the brief is not ready. Ask for them. Do not invent a message.

Then fix the constraints that every concept must respect:

| Field | Example | Why it matters |
|---|---|---|
| Duration | 8 s | Sets how many states fit (section 5) |
| Format | `reel`, `story`, `insert`, `overlay` | Safe area and transparency needs |
| Mode | `editorial`, `kinetic`, `diagram`, `glow`, `retro` | Filters the [style atlas](style-atlas.md) |
| Audio | `required`, `optional`, `forbidden` | With `forbidden`, hits still drive the image (shakes, flashes), with no sound |
| Exact copy | "NOTHING MOVES" | Copy that must survive word for word |
| Exclusions | "no glow on titles" | Vetoes that apply to every concept |

## 2. Generate: eight moves

Run every move. Each one should give 2–4 candidates. Aim for 20–25 raw candidates, then keep ten. Write
each candidate as one line: *what the viewer sees → what moves → what it means*.

### 2.1 Metaphor mapping

Find a system elsewhere that has the same relation as the message. Map the relation, not the look.

| Source system | Relation it has | Motion it implies |
|---|---|---|
| A lens bringing a scene into focus | unclear → clear | focus pull on the key word; reading time starts at the first sharp frame |
| A scale that tips | weight builds until it flips | a counter that flips the claim when the last weight lands |
| Tide over sand | a layer erases what it covers | a wipe that reveals the next state; the erased thing keeps its identity |
| A relay race | one carrier passes the baton | one shape becomes the next scene's frame |

### 2.2 Visual verbs

Pick the verb the brief implies. A verb is a motion you can program.

| Verb | Motion | Built with |
|---|---|---|
| separate | parts leave a shared point | `arcPoint`, `tween` with `cubic.out` |
| stack | items arrive and build a column | `stagger(i, n, {from: 'end'})` |
| substitute | one thing takes the place of another, same anchor | two `tween` curves on one baseline |
| reveal | a mask uncovers the next state | a mask edge driven by `easing` |
| compress | scale down and blur with energy | `tween` plus `directionalBlur` |
| pass through | the camera enters an object | scale ramp plus `radialBlur` |
| orbit | the subject turns around an axis | `arcPoint`, or a depth scale in 2.5D |
| anchor | one element stays fixed while the rest move | a constant position in `state(t)` |

### 2.3 Transform the key noun

Take the noun that carries the message. Make one transform per axis. The noun must stay recognizable in at
least one of them.

| Axis | Question | Example for "time" |
|---|---|---|
| Opposite | What is its negation? | a clock that runs backwards |
| Tool | What does it act on? | time as a ruler, measured in frames |
| Material | What is it made of? | a stack of paper sheets |
| Scale | What if it is huge or tiny? | one second filling the frame |
| Sound | What would it sound like? | a tick that becomes a hit |

### 2.4 Constraint cards

Constraints create concepts. Draw three cards per session. A concept must obey all three, or break one with
a written reason.

| # | Card |
|---|---|
| 1 | One shape only: a circle or a ring |
| 2 | Text is the only image |
| 3 | One camera move for the whole piece |
| 4 | Linear motion and one spring only |
| 5 | Every cut is a match cut |
| 6 | The object steps at 12 fps; the camera runs at 60 |
| 7 | Two inks and paper |
| 8 | One light source |
| 9 | Nothing moves more than 20 px per exposure |
| 10 | Enter from the edge of the frame only |
| 11 | Play the timeline backwards: the last state comes first |
| 12 | Sound first: motion exists only between hits |

Draw with a seed, so the same session gives the same cards:

```js
const next = MotionMath.rng(42);                                  // same seed, same cards
const deck = CARDS.slice();                                       // CARDS: the twelve above
const draw = () => deck.splice(Math.floor(next() * deck.length), 1)[0];   // no card repeats
const hand = [draw(), draw(), draw()];
```

### 2.5 Style collisions

Pair two styles from the [style atlas](style-atlas.md). One owns **type**, one owns **motion**, one owns
**texture**; never give two styles the same layer. Example: terminal monospace (type), risograph (texture), stepped time (motion).

### 2.6 The camera is the idea

Test: remove the camera move. If the idea still reads, the camera is decoration.

- A pull-out that reveals the frame was part of a larger picture.
- A push through a window that shows the next state.
- A rack focus that picks one word out of a list.

### 2.7 Type as object

Test: remove any letter. If the sentence still reads and nothing about the letter matters, it is decoration.

- Letters as bricks that build a total.
- A word that lands on a surface and casts a shadow.
- A window that slides across a sentence, so the text is revealed in pieces.

### 2.8 What does the last movement reveal?

Design the last state first. Write: "The last movement produces the relation ___, which was not visible before."
Name the carrier that survives to the end. A last state that only changes the copy is a repetition, not a reveal.

## 3. Ten concepts

| # | Concept (one line) | Verb | Style | Hero moment | First-frame hook |
|---|---|---|---|---|---|
| C1 | <one line> | <verb> | <style> | 2.4 s | <hook> |

Ten rows, C1 to C10. Log each rejected candidate in one line, for example: "C7 needs footage tracking; no kit path".

## 4. Score

Score each concept 1–5 on six criteria. Use the anchors, not your taste.

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Clarity | The viewer cannot say what changed | The change reads after a second watch | The change and its meaning read in one pass, at the viewer's speed |
| Surprise | The expected template: slide in, fade out | Predictable, with one twist | Unexpected, yet explained by the mechanism |
| Feasibility in code | Needs footage tracking, a rig or a missing asset | Needs one custom shader or an asset you must make | Every part is a kit function or a short combination of them |
| Brand fit | Breaks the palette, type or voice of the brief | Neutral | Uses the palette roles, type roles and voice of the brief |
| Loopability | Start and end states do not match | Matches the state, not the motion | State and motion match across the splice, checked over 2–3 repeats |
| First-frame hook | Empty or dark first frame | Something moves in frame 0 | One readable, high-contrast element, legible at thumbnail size |

Rules:

- **Loopability** applies only when the brief asks for a loop. Otherwise drop it and compare on the same criteria.
- **Kill rules.** Clarity of 2 or less discards the concept. Feasibility of 1 means redesign or discard.
- Score the first and the last state separately. A strong start with a weak end is still a weak concept.

## 5. From the winner to a storyboard

1. **Name the states**, S0 to Sn. Use 3–6 states for 8–15 s. A state ends when the viewer can read it.
2. **Fill each state**: composition, verb, carrier (what persists), and reading time (`readingTime(words)`, or
   `readingTimeChars(text)` for copy). Add the four `motion` fields from the [plan schema](../produce/plan-schema.md).
3. **Place the hits.** A hit is a physical change: a state boundary, a reveal, an arrival. Keep one list,
   shared by image and sound.
4. **Run the two-sentence test.** Say what changes and why it matters, in two sentences. If you cannot, go
   back to step 1.
5. **Check the ends.** Compare S0 with the last state, and mark each motion's peak for the [blur plan](../craft/blur.md).

Example for a two-word claim that flips (frames at 60 fps):

```
S0   0–30 f     dark frame; a ring enters on an arc         carrier: ring   reading: —
S1   30–138 f   letters cascade from the centre             carrier: ring   reading: 1.1 s (4 words)
S2   138–216 f  the ring pushes outward; the claim flips    carrier: ring   reading: 0.8 s (2 words)
S3   216–300 f  hold; the last frame matches S0 for a loop  carrier: ring   reading: 1.1 s (4 words)

hits: [{"time": 0.50, "amplitude": 0.8, "role": "entry"},
       {"time": 2.30, "amplitude": 1.2, "role": "reveal"}]
```

## 6. Next steps

Look: [art direction](art-direction.md). Blueprints: [scene recipes](scene-recipes.md). Proof of an operation:
[reference study](reference-study.md). Timing and checks: [principles](../craft/principles.md) and the [quality rubric](../produce/quality-rubric.md).
