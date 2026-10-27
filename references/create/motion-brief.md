# The motion brief: six blocks that decide the piece before the code

Read before building anything from a brief, a script or an idea, and whenever a request arrives as one vague line
("make a dynamic 15-second motion video"). The brief is the plan written in words: it decides what a model or a
person would otherwise fill with defaults. It also travels: the same file is a prompt that any agent can run.

Tool: `python -I <skill>/scripts/brief.py` (`list`, `new`, `check`, `grid`, `plan`). Templates:
[`templates/briefs/`](../../templates/briefs/README.md).

## 1. Why a structure

The [Prompt Motion](https://prompt-motion.com/) gallery collects about 230 motion films made with Claude, each with
the prompt that made it. Its own analyses (October 2026; likes reflect each poster's audience, so read them as a
rough signal, not proof) found:

| Finding | What it says for a brief |
|---|---|
| The median prompt is 26 words; 78 open with the same "make a dynamic N-second motion graphics video" line, and the most-copied one ran from 0 to 17,023 likes, median 5 | A one-line request leaves every decision open, so the results scatter |
| The 19 prompts over 100 words had a median of 56 likes against 5 for prompts of 26 words or fewer | Length is not the point: each line should take a decision away from the defaults |
| Only 16 prompts had a banned list, yet four of the 20 most-liked did | Naming what not to do is the cheapest quality gain |
| Launch prompts that named a beat or BPM (11 of 92) cut like films; the rest cut like slideshows | A tempo and a bar count give the cuts a grid |
| No explainer (0 of 27) asked for the facts to be checked; only 2 named the audience | An explainer needs a fact line and an audience line |
| Creators at maximum effort settings still ranged from 1 to 17,023 likes | Settings outside the brief do not replace decisions inside it |

The strongest long prompts share one shape: tagged blocks. Motionsmith adopts it, with its own engine in the build.

## 2. The six blocks

```
<inputs>     what to ask before building (only what is missing)
<direction>  one concept, the recurring element, type, palette, motion, camera, the banned list, the ending
<structure>  duration, tempo, meter, bars, loop; what happens bar by bar
<build>      how it is made and reviewed (Motionsmith's tools; short, because the kit already decides most of it)
<gotchas>    the known failure points of this kind of piece
<start>      what to show before any code (concept line, beat grid, storyboard), then build without more questions
```

`brief.py check` reads `key: value` lines anywhere in the blocks (English or Spanish keys) and fails on what is
missing; it never judges whether the idea is good.

| Block | Must decide | Key lines read by `check` |
|---|---|---|
| `<inputs>` | The variables only the person can give: exact copy, assets, brand, music and its licence. At most three groups, asked once | — |
| `<direction>` | **One concept** in one line (a piece without one becomes a tour of effects). **A recurring element** that carries every transition. Type, palette, motion rules, camera language. **The banned list.** The ending | `concept:`, `recurring element:`, `banned:`, `ending:`, `kind:`, `audience:`, `facts:` |
| `<structure>` | Duration from the voice or the format; tempo and meter; the bar count and what each bar does; where the strongest moment lands; loop or not | `duration:`, `tempo:` (BPM, or `voice` / `free`), `meter:`, `bars:`, `lead:`, `loop:` |
| `<build>` | The Motionsmith path: `new_piece.py`, `brief.py plan`, state as a function of t, sound from the hits, the per-beat review, render and verification | (warns when no review step is written) |
| `<gotchas>` | What breaks this kind of piece: scaled text blurring, two lines overlapping in a swap, the loop seam, the safe area, morph correspondence | — |
| `<start>` | Show the concept line and the beat grid or storyboard first; then build without further questions; deliver the file and what only the person can judge | (warns when it does not ask for them) |

## 3. The banned list

Write five to nine items, one per line, each as `avoid -> instead`, and end with "anything that looks like a template"
so the defaults you did not name are judged too. A ban without an alternative only removes; the `instead` says what
to build. Start from the common tells below, then add what went wrong in the last test.

| Tell | Why it reads as machine-made | Write instead |
|---|---|---|
| Glows and neon with no source | Decoration that makes a frame look rich without a reason | Light only where something on screen emits it ([light](../craft/light-bloom.md)) |
| Particle bursts | Motion that comes from nothing and leads nowhere | Motion that starts from or ends in an element on screen |
| Crossfades | Nobody designed the transition | Every scene grows out of the previous one through the recurring element ([transitions](../edit/transitions-atlas.md)) |
| Bouncy easing on everything | Cartoon springiness | Springs with a tiny overshoot on the hero only ([curves](../craft/curves-graph-editor.md)) |
| Corner labels, frame counters, HUD readouts | Suggests detail without carrying information | Text only when it tells the viewer something |
| Long holds, dead time | A still frame works only while it is being read | An inner change at least every beat or ~0.5 s ([living layer](../craft/living-layer.md)) |
| Generic gradients | The default background of every generator | A flat field with grain, print or paper ([print & textures](../craft/print-textures.md)) |
| Stock footage, stock icons and UI kits | Interchangeable with every other piece | Real assets or shapes drawn in code in the piece's style |
| A slowly spinning object as the whole idea | A demo, not a piece | One action with a consequence ([direction](../craft/direction-choreography.md)) |
| Camera shake, RGB split, lens flares | Energy pasted on top | A motivated camera move; misregistered print if a glitch is needed |
| `Math.random()` and clocks | A frame you approved changes on the next render | Seeded values and frame numbers: everything is a function of t |

The banned list is taste, not law: a profile that approves glows (a neon mode, a light that does emit) overrides it.
The rule is that every effect has a reason in the scene.

## 4. Tempo, bars and the arithmetic

Give a tempo and let it set the grid: at `bpm`, a beat is `60 / bpm` seconds and a 4/4 bar is four beats. Then check
that the numbers agree before any code: `brief.py grid --bpm 120 --duration 15` prints every beat with its time and
frame.

| Tempo | Beat | 4/4 bar | 15 s hold | Use |
|---|---|---|---|---|
| 90 BPM | 0.667 s | 2.667 s | 5.625 bars | Suspense, reading-heavy pieces |
| 100 BPM | 0.6 s | 2.4 s | 6.25 bars | Kinetic type with reading holds |
| 120 BPM | 0.5 s | 2 s | 7.5 bars | Showreels, launches; an action on every beat |
| 128 BPM | 0.469 s | 1.875 s | 8 bars | Dense promos |

- A duration that is not a whole number of bars is a decision, not an accident: say what the partial bar holds (the
  end title on half a bar) or change the duration (`check` warns unless `bars:` states it).
- Contradictions are resolved in the brief, not in the code: "equal time per technique" and "one technique per bar"
  cannot both hold in 7.5 bars. Write which one wins.
- A beat under 0.2 s strobes when something happens on every beat; act on every second beat.
- With a recorded track, beat 0 is its first downbeat (`lead:`), measured, not guessed
  ([music editing](../edit/music-editing.md)). With a voice, write `tempo: voice` and take the timing from its cues.
- `brief.py plan` writes `bpm`, `meter`, `lead` and adds bar (or beat) hits beside the hits the plan already has
  (a recipe reads its own by role, so they are kept), and lists the existing hits that sit off the grid. Rename each
  `bar N` role to what happens on screen, so image and sound read the same list ([rhythm](../craft/rhythm-sync.md)).

## 5. Review per beat, and the loop

Before the full render, look at one frame per beat: `sample_frames.mjs --root <piece> --out <tmp> --beats` (or
`--bars`, `--hits`; `--beat-offset 0.05` to see the accent after it lands), then a contact sheet. Fix anything
off-grid, cluttered, overlapping or hard to read. This is step 2 of the [review protocol](../produce/review-protocol.md),
aimed at the grid.

A loop needs the last frame to lead into the first in pose **and** speed, and never the first frame twice. Check the
MP4 with `loop_check.py`: the seam step should look like any other step (seam ratio near 1) and the speed should not
break (speed ratio near 1).

## 6. By kind of piece

| Kind | What the strongest briefs add | Template |
|---|---|---|
| Vertical reel, hook | The first frame moves; the key word lands on beat 1; an inner change every beat; the payoff on the last full bar | `reel-hook` |
| Showreel | A concept named first; a required range of techniques; every shot transforms out of the last; the loop | `showreel` |
| Launch, product | The promise in one line; three to five concrete moments in order; hex colours; a tempo; the product as the subject, not the backdrop; the ending | `launch` |
| Explainer | A sequence with a start and an end, not a topic; the audience; about five seconds per idea; labels where the thing is; a facts line (research, never invent numbers, names, dates or quotes) | `explainer` |
| Loop | The period first, every motion a divisor of it; pose and speed matched at the seam | `loop` |

## 7. From the brief to the piece

1. `brief.py new <piece>/brief.md --template <kind>` (or write one by hand with the six blocks), fill it with the
   person's answers, run `brief.py check`.
2. Run [ideation](ideation.md) when the concept line is still open: ten concepts, one winner, written into `concept:`.
3. `new_piece.py <piece> --format … --duration …` (the folder may already hold the brief), then
   `brief.py plan <piece>/brief.md --plan <piece>/plan.json`. `validate_plan.py --require-brief` confirms the concept,
   the banned list and the loop decision reached the plan.
4. Storyboard as states, style frames, the hardest moment first, the per-beat review, the three critics, render
   (SKILL §2).

When the person hands over a prompt written for another tool, rewrite it into the six blocks and show the decisions
it was missing before building; keep their words where they decided something.

## 8. Hook variants for trial reels

The first three seconds decide whether anyone sees the rest, and they are the part a creator is least sure of. Instead
of guessing, write two to four openings for one body and let trial reels compare them.

```text
hooks:
- PARA -> an order
- ¿CANSADO? -> a question
- 3 SEGUNDOS -> a number
seam: 2.6 s
```

- **Vary one thing.** An order, a question, a number, a confession: the same idea entering three ways. Three different
  ideas teach nothing about hooks.
- **The seam** is the second from which every variant looks the same: after the transition that carries the hook
  away. `hook_variants.py` proves it to the pixel and refuses a variant that still differs there.
- **One body, rendered once.** Each variant renders only its opening; the body renders once and is joined behind each
  (with four variants of a 15 s reel and a 2.6 s seam: 25 s of rendering instead of 60).
- **Each hook keeps its sound**: one soundtrack per variant from its own plan.
- **Read the results honestly.** Post at the same hour, fill `final/hooks/hooks.md` after 24–48 h, compare the
  3-second skip rate and the average watch time. With a small account a difference under about ten points is noise;
  repeat the winner against a new challenger before calling it.

```bash
python -I <skill>/scripts/hook_variants.py init --piece <piece> --brief <piece>/brief.md   # variants.json
python -I <skill>/scripts/hook_variants.py render --piece <piece> --workers 3              # final/hooks/*.mp4
```

## Sources

Prompt Motion (prompt-motion.com, curated by @p4nthera_): the analyses "AI motion graphics prompts: what 230 real
examples show", "How to prompt an AI launch video", "AI explainer video prompts", "Why AI motion graphics look
AI-made" and "Remotion vs HyperFrames vs plain HTML", and its showreel and 3D templates, read on 2026-10-26. The block
names and the findings are theirs; the mapping to Motionsmith, the arithmetic checks and the templates are this
skill's ([third-party credits](../../THIRD_PARTY.md)).
