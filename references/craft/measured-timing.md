# Measured timing: what professional motion actually does

Read when choosing a duration, a curve, a stagger or a hold and there is no profile or reference that decides it. These
are medians from a study that sampled professional motion frame by frame; use them as the default and break them on
purpose. The taste profiles win over them, and so does the person on their phone.

**Where the numbers come from.** The motionmaxxing skill (Tejash Makwana, Apache-2.0) measured about 4,300 distinct
moves in 50 short moments recreated frame-accurately from professional launch and product films (hooks, turns, proofs
and calls to action), at 30 fps on a 16:9 stage. Its tables are summarised here in this skill's words. Two cautions:
they are launch films, not talking-head reels, and short moments, not whole films; a reel cuts faster and a whole film
is calmer than any 3–7 s moment.

## 1. Durations

| What | Median (frames at 30 fps) | Usual range (p25–p75) | Note |
|---|---|---|---|
| Any move, pooled | **10 f (0.33 s)** | 6–24 f | 13 % are 2–3 f snaps; 12 % run longer than 1 s |
| Position (x or y) | 12 f | 6–24 f | median travel ~5 % of the width / ~8 % of the height |
| Scale | 10 f | 5–22 f | median change 0.25 |
| Rotation | 11 f | 6–21 f | median 25° |
| Opacity | **6 f** | 4–12 f | a helper, not the move |
| Blur | 7 f | 4–10 f | median 5 px |
| Calls to action | **6 f** for supporting pieces | — | the most staccato part of a film; the hero mark still takes 18–30 f |

Exits are about as long as entrances for position (14 vs 12 f) and a little shorter for scale. Motionsmith's rule
"exits 65–75 % of the entrance" is the shorter end of the same picture.

## 2. Landing decelerates, leaving accelerates

- 58 % of landings ease out; 37 % of departures (42 % of scale exits, 63 % of blur-outs) accelerate. Peak speed of an
  accelerating exit sits near the end (t ≈ 0.9): the thing is thrown away and the cut takes it.
- Elements arrive and leave by **moving**: 3,392 transform entrances against 584 opacity fades. When something simply
  appears, 57 % of the time it is a one-frame cut. A pure fade-in is the generator's default.
- An entrance spends two or more channels at once (offset + blur clearing, scale + opacity helper), never opacity alone.

## 3. The twelve measured eases

Use them by name in keys (`Comp.k([0, a, 'm.softLand'], [.4, b])`), in `Comp.curve('m.accelExit')`, or anywhere a
MotionMath easing is accepted (`M.easing('m.glide')`). `Comp.style('measured')` sets arrive `m.softLand`, slam
`m.snapSettle`, exit `m.accelExit`, no overshoot and siblings 2 frames apart.

| Name | % done at 10 / 25 / 50 / 75 % of the time | Typical length | What it is for |
|---|---|---|---|
| `m.cruise` | 10 / 25 / 50 / 75 (linear) | 9 f, drifts 26 f+ | Drift, camera creep, counters, fades; every drift is linear |
| `m.glide` | 16 / 39 / 69 / 91 | 10 f | All-purpose medium lands, entries and exits alike |
| `m.softInOut` | 4 / 17 / 50 / 83 | 9 f | Opacity, blur, ground and colour ramps |
| `m.softLand` | 30 / 59 / 85 / 95 | 12 f | Text rising, panels, scale-ins; the entrance workhorse |
| `m.gentleIn` | 1 / 6 / 24 / 55 | 9 f | The start of an exit, a blur-out, a push into a cut |
| `m.snapSettle` | 54 / 84 / 96 / 98 | 11 f | Hero and call-to-action entrances: most of the travel in 4 frames, then a long tail |
| `m.whip` | 23 / 52 / 83 / 97 | 7–8 f | Big fast moves, the entry half of a whip |
| `m.accelExit` | 0 / 3 / 16 / 47 | 13 f | Leaving the frame or shrinking into a cut |
| `m.crashOut` | 0 / 0 / 6 / 32 | 17 f | Pull-offs that end at full speed on a hard cut |
| `m.popOver` | 10 / 46 / 96 / 108, peak 1.08 at 0.72 | 15 f | The late lean past the mark: 88 % of real overshoots |
| `m.crashIn` | 91 / 118 / 110 / 103, peak 1.18 at 0.27 | 10 f | A slam that passes the mark and relaxes |
| `m.bounceHard` | 13 / 62 / 138 / 139, peak 1.48 at 0.62 | 22 f | The big overshoot: under 2 % of moves; once, if ever |

Compared with Motionsmith's AE eases: `snap` (12/88) and `m.snapSettle` are the same family (`snap` starts from speed
zero, as an After Effects key does; `snapSettle` already moves on frame 1); `accel` is close to `m.accelExit`; `glide`
(AE 55/60) is softer than `m.glide`. Pick the AE names when the piece must match an After Effects project; pick the
measured ones when it must match what professionals ship.

## 4. Overshoot is rare, late and small

- 8.8 % of moves overshoot by more than 3 %. 88 % of those peak **after** a third of the move (median t 0.65–0.70): a
  slow lean past the mark and back over 15–24 f, not a fast spring.
- Sizes in single films are small: +4 to +6 %. One visible spring per film, at the payoff.
- So: overshoot only the hero, use `m.popOver` or `Comp.overshoot` with `amount` ≤ 0.06, and keep everything else
  landing clean.

## 5. Stagger and overlap

| Gap between sibling onsets | 1 f | 2 f | 3 f | 4–5 f | 6 f + |
|---|---|---|---|---|---|
| Share of all gaps | **56 %** | 13 % | 8 % | 13 % | 10 % |

- Letters, tiles and rows run 1–3 f apart with uneven gaps (3, 2, 2, 2, 2…), each move about twice as long as the gap,
  so the tails overlap and the wave reads as one gesture. A uniform timer reads as a loading list.
- Whole **words** run slower: 2–4 f in a fast hook, 4–6 f in a headline, 8–12 f when a voice leads, and a longer gap
  before the word that lands the line. With a voice, on-screen words land 0–2 frames **before** they are heard.
- Calls to action are the only place gaps widen (~8 f).

## 6. Holds and drift

- In 3–7 s moments, something moves on ~99 % of frames; drifts are linear, median 26 f at ~2.5 px/f, slow background
  creeps 1.1–1.5 px/f.
- Whole human-made films are calmer: a bright launch film can be still for half its length, and a calm, legible film
  beat a frantic one in a direct comparison. The rule is not "always move": it is **no dead frame** (a hold keeps one
  living thing) and **a designed breath** (0.6–1.5 s, with a reason, before a payoff) is welcome.
- Legitimate still holds are payoffs: a readable list 0.8 s, a lockup 0.67 s, a single number ~0.5 s. A resolved end
  card holds 0.6–1.4 s; longer reads as "the film gave up".

## 7. Camera

- Pushes are 48 % ease-out and median 1.46× over ~18 f; slow creeps are linear.
- A reveal is a one-frame snap of the scale (ratio 0.56–0.77) followed by a 9–18 f tail.
- One camera group: type and interface are never zoomed on their own track.

## 8. How to use this

1. Start from the style (`Comp.style('measured')` or the profile's choice) and the durations in §1.
2. Give each role its own curve: lands, slams, exits, drifts, counters. One global ease on everything is the loudest
   machine tell.
3. Check the result with `motion_curves.py` (speed graphs) and `hold_check.py` (dead holds), then on the phone.

## Sources

Tejash Makwana, motionmaxxing (github.com/Tejashmakwana/motionmaxxing, Apache-2.0), `references/motion.md`,
`references/slop.md` and `taste/`, read 2026-11-05. The measurements are theirs; the summary, the mapping to Comp and
the curve implementation (power fits and monotone cubics through the published points) are this skill's
([third-party credits](../../THIRD_PARTY.md)).
