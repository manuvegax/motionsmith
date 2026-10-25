# Scene recipes: fifteen blueprints

Each recipe gives its purpose, a timing row in frames at 60 fps (1 f = 16.7 ms), the curves, a short skeleton
and the checks that prove it. A skeleton is the body of a helper called from `state(t)`, following the
starter ([piece.js](../../templates/starter/piece.js)): a pure function of `t` and of the plan's `hits`, with
no state kept between calls, so `window.seek(t)` gives the same frame in any order. Capitalized names
(`GLYPHS`, `HITS`, `DURATION`, `ROUTE`, `GROUPS`…) are constants that the piece sets from `plan.json` or from its own copy.

The kit is `M` (`window.MotionMath`) and `P` (`window.PostFX`); see [curves](../craft/curves-graph-editor.md)
for the names and [style atlas](style-atlas.md) for looks. The skeletons below use `layoutGlyphs`, `stagger` and
absolute frame windows so they read on their own. For production, `window.KineticType` (font cycling, echoes,
glitch, typewriter, marquee, karaoke) and `window.Timeline` (keyframes with After Effects influence, markers, hits)
do the same with less code, and `kit/stage.js` does the render plumbing.

**Six of these blueprints exist as runnable recipes** in [templates/recipes](../../templates/recipes/README.md):
logo reveal (1), title card (2), kinetic quote (3), lower third (4), data reveal (6) and split compare (8). Start
from one with `new_piece.py --recipe <name> --format <format>`; it validates, is deterministic and reads its times
from the plan's `hits`.

## Timing table

| # | Recipe | Length | Anticipation | Action | Settle | Read |
|---|---|---|---|---|---|---|
| 1 | Logo reveal | 150 f (2.5 s) | 0–12 | 12–48 | 48–66 | 66–150 |
| 2 | Title card | 180 f (3 s) | 0–9 | 9–40 | 40–54 | 54–180 |
| 3 | Kinetic quote | sum of groups | 0–18 per group | 18–30 | 30–40 | `readingTime` per group |
| 4 | Lower third | 240 f (4 s) | 0–6 | 6–24 | 24–30 | 30–204; exit 204–222 |
| 5 | Product hero | 300 f (5 s) | 0–6 | 6–60 | 60–72 | 72–300 (turn 60–252) |
| 6 | Stat reveal | 180 f (3 s) | 0–12 | 12–84 | 84–96 | 96–180 |
| 7 | Map route | 300 f (5 s) | 0–30 | 30–240 | 240–270 | 270–300 |
| 8 | Split compare | 180 f (3 s) | 0–12 | 12–63 | 63–78 | 78–180 |
| 9 | Countdown | 30 f per number | 0–6 | 6–12 | 12–18 | 18–30 (leaves 18–24) |
| 10 | Text behind subject | 240 f (4 s) | 0–12 | 12–36 | 36–48 | 48–240 |
| 11 | Word swap | 90 f per word | 0–6 | 6–30 | 30–40 | 40–90 |
| 12 | Ticker | text width ÷ speed | — | continuous | — | continuous |
| 13 | Collage build | 240 f (4 s) | 0–12 | 12–72 | 72–84 | 84–240 |
| 14 | Zoom through a lens | 48 f (0.8 s) | 0–8 | 8–36 (cut at 24) | 36–48 | the next scene |
| 15 | Loop end card | 180 f (3 s) | — | continuous | last 48 f: return | seamless |

## 1. Logo reveal

- **Purpose:** the mark arrives, is read, and leaves a trace.
- **Curves:** `back.out` for the scale (a small overshoot); `cubic.out` along an `arcPoint` for the path.
- **Skeleton:**

```js
const k = M.easing('back.out')(M.clamp((t - .2) / .6));                       // scale, 12–48 f
const pos = M.arcPoint(M.easing('cubic.out')(M.clamp((t - .2) / .6)), [-300, 800], [540, 960], .15);
const scale = k * (1 + .06 * M.impulse(t, HITS, 9));                          // settle hit at 48 f
```

- **Checks:** the mark is complete by 66 f and readable for at least 1 s; the hit lands on the frame where the mark stops.

## 2. Title card

- **Purpose:** name the piece in one phrase.
- **Curves:** `expo.out` per letter, with a stagger from the start.
- **Skeleton:**

```js
const letters = GLYPHS.map((g, i) => {
  const start = .15 + M.stagger(i, GLYPHS.length, {each: .02, from: 'start'});   // 1.2 f apart
  return M.easing('expo.out')(M.clamp((t - start) / .3));                       // 18 f per letter
});
```

- **Checks:** no letter is visible one frame before its start; the whole title is set by 40 f; the read lasts at least `readingTime` for its words.

## 3. Kinetic quote

- **Purpose:** a line that builds group by group, paced by reading time rather than by the beat.
- **Curves:** `expo.out` in, `cubic.in` out. The exit is shorter than the entry.
- **Skeleton:**

```js
const hold = GROUPS.map(g => M.readingTime(g.words, {extra: g.names ? .3 : 0}));   // seconds to read each group
let at = .2;
const windows = hold.map(h => { const w = {enter: at, exit: at + .3 + h}; at = w.exit + .3; return w; });
```

- **Checks:** each group stays unchanged while it is read; the read is at least `readingTime` after the first sharp frame; no group starts before the previous one has left.

## 4. Lower third

- **Purpose:** a name and a role, in the lower part of the frame, out of the way of the face.
- **Curves:** the bar `cubic.out`, the text `expo.out`, the exit `cubic.in`.
- **Skeleton:**

```js
const bar = M.easing('cubic.out')(M.clamp(t / .3));                       // 0–18 f
const text = M.easing('expo.out')(M.clamp((t - .1) / .3));                // 6–24 f
const exit = M.easing('cubic.in')(M.clamp((t - 3.4) / .3));               // 204–222 f
```

- **Checks:** the text sits inside the safe area ([formats and platforms](../edit/formats-platforms.md)); the exit starts after the read, which is `readingTime` for the words plus 0.3 s for a name.

## 5. Product hero

- **Purpose:** show an object as an object. It arrives, turns a little, and stays readable.
- **Curves:** `back.out` on entry, for a small overshoot; `power2.inOut` on a 30° turn.
- **Skeleton:**

```js
const enter = M.easing('back.out')(M.clamp((t - .1) / .6));                 // 6–42 f
const turn = M.easing('power2.inOut')(M.clamp((t - 1) / 3.2)) * Math.PI / 6;   // 60–252 f, 30°
const width = Math.cos(turn) * enter;                                       // a card turning on its vertical axis
```

- **Checks:** the frame never crops the object at 30°; the shadow falls on the side away from the light, at every point of the turn.

## 6. Stat reveal

- **Purpose:** a number counts up to its source value, then a label explains it.
- **Curves:** `expo.out` for the count-up; `cubic.out` for the label, after the number stops.
- **Skeleton:**

```js
const value = M.tween(t, .2, 1.4, 0, TARGET, 'expo.out');                  // count-up, 12–84 f
const label = M.easing('cubic.out')(M.clamp((t - 1.4) / .4));              // after the number settles
const shown = String(Math.round(value));                                   // no locale formatting: same output everywhere
```

- **Checks:** the last frame shows the source value exactly; the label appears after the number stops; the source is written in the piece's notes. Do not invent a figure.

## 7. Map route

- **Purpose:** a path between places, drawn at constant speed, with a marker that knows its heading.
- **Curves:** `power2.inOut` along a `pathSampler`, which measures by distance, so the speed is constant along the polyline.
- **Skeleton:**

```js
const route = M.pathSampler(ROUTE);                                        // ROUTE: dense points, in px
const u = M.easing('power2.inOut')(M.clamp((t - .5) / 3.5));               // 30–240 f
const {point, angle} = route.at(u);                                        // marker position and heading
```

- **Checks:** no kink in the marker's speed at a corner (run `motion_curves.py` on the dumped path); enough points in `ROUTE` that the curve does not facet.

## 8. Split-screen compare

- **Purpose:** two states side by side, with the divider as the gesture.
- **Curves:** the divider `power2.inOut`; each side `expo.out`, the second one 9 f later.
- **Skeleton:**

```js
const split = M.easing('power2.inOut')(M.clamp((t - .2) / .4));            // divider, 12–36 f
const left = M.easing('expo.out')(M.clamp((t - .6) / .3));                 // 36–54 f
const right = M.easing('expo.out')(M.clamp((t - .75) / .3));               // 45–63 f
```

- **Checks:** each side is readable after its reveal; the divider never crosses a line of text.

## 9. Countdown

- **Purpose:** three numbers and a go, one per beat.
- **Curves:** `back.out` for the pop (12 f), `cubic.in` for the leave (18–24 f). A hit on each beat.
- **Skeleton:**

```js
const beat = Math.min(NUMBERS.length - 1, Math.floor(t / .5));             // 0.5 s = 30 f per number
const local = t - beat * .5;
const pop = M.easing('back.out')(M.clamp(local / .2));                     // 0–12 f
const leave = M.easing('cubic.in')(M.clamp((local - .3) / .1));            // 18–24 f
```

- **Checks:** `hits` has one entry per beat; the GO holds to the last frame; each number leaves before the next beat.

## 10. Text behind subject (matte)

- **Purpose:** the subject covers the text, so the type sits in depth.
- **Curves:** the text `expo.out` before the subject appears; the subject has a small wobble from `M.wiggle`.
- **Skeleton:**

```js
const text = M.easing('expo.out')(M.clamp((t - .2) / .4));                 // text first, 12–36 f
const drift = M.wiggle(t, {freq: .4, amp: 4, dims: 2, seed: 3});           // ±4 px on the subject only
// draw order: background → text → subject cut-out (alpha PNG, offset by drift) → light wrap
```

- **Note:** the matte is an asset you make; the kit does not segment. Composite the light wrap with `P.SHADERS.lightWrap`.
- **Checks:** the matte edge at 100 % zoom (hair, shoulders); the text is occluded exactly at the subject's edge; no halo; the wobble stays within 4 px.

## 11. Word swap

- **Purpose:** one word becomes another on the same baseline.
- **Curves:** the old word `cubic.in` out (0–13 f); the new word `cubic.out` in (9–29 f).
- **Skeleton:**

```js
const out = M.easing('cubic.in')(M.clamp((t - T) / .22));                  // old word leaves, 0–13 f
const inn = M.easing('cubic.out')(M.clamp((t - T - .15) / .33));          // new word arrives, 9–29 f
// one baseline: both words share y; only alpha and x offset change
```

- **Shape morph:** resample both outlines with `resamplePath(points, n, {closed: true})`, align them with `alignPaths`, then blend with `morphPath(a, b, u)`.
- **Checks:** no frame where both words are legible in the same spot; the baseline is constant; the new word is readable for at least `readingTime` before the next change.

## 12. Ticker / marquee

- **Purpose:** a line that runs without stopping, for an insert or a loop.
- **Curves:** linear. This is the one place where linear motion is right.
- **Skeleton:**

```js
const period = TEXT_W / SPEED;                                             // seconds for one full pass
const x = -M.loop(t, period) * SPEED;                                      // always within [-TEXT_W, 0]
// draw the line at x and at x + TEXT_W, so the seam never shows
```

- **Checks:** the loop closes at `period` (compare t = 0 with t = period). `M.pxPerExposure(SPEED, SHUTTER, FPS)` sets the blur: at 180 px/s and a 180° shutter it is 1.5 px, so only a light blur.

## 13. Collage build

- **Purpose:** pieces land one after another, each with its own contact shadow.
- **Curves:** `power3.out` per piece (a strong deceleration). A random order with a fixed seed, about 4 f apart.
- **Skeleton:**

```js
const k = M.stagger(i, PIECES.length, {each: .07, from: 'random', seed: 5});   // fixed order, ~4 f apart
const p = M.easing('power3.out')(M.clamp((t - .2 - k) / .5));               // 12–42 f per piece, plus stagger
```

- **Checks:** each piece's shadow matches the light direction; no piece enters from behind another's shadow; the last piece settles by 72 f.

## 14. Zoom through a lens

- **Purpose:** a cut hidden inside a zoom. The camera goes through the lens, and the next scene is already waiting.
- **Curves:** `power3.in` for the zoom. The blur peaks where the cut happens, at 36 f, where the scale is already
  about 4×.
- **Skeleton:**

```js
const p = M.clamp((t - T0) / .8);                                          // 48 f window
const CUT = .75;                                                           // 36 f into the window
const scale = 1 + 8 * M.easing('power3.in')(p);                            // 4.4× at the cut: the lens fills the frame
const blur = .25 * Math.exp(-(((p - CUT) / .12) ** 2));                     // a bump centred on the cut
// pass: P.SHADERS.radialBlur in zoom mode, amount = blur, centre on the lens
```

- **Checks:** the cut sits inside the blur peak, so the most-blurred frame is the cut; the incoming scene reads within 3 f of the cut; one hit at the cut.

## 15. Loop end card

- **Purpose:** a card that repeats without a visible seam.
- **Curves:** periodic functions of the loop phase. `M.wiggle` is not periodic, so it does not belong here.
- **Skeleton:**

```js
const period = DURATION;                                                   // one loop = the whole card
const phase = M.loop(t, period);                                           // 0 … period, then again
const up = M.easing('power2.inOut')(M.clamp(phase / .8));
const down = M.easing('power2.inOut')(M.clamp((phase - period + .8) / .8));
const k = up - down;                                                       // 0 at both ends, with zero speed: no seam
```

- **Checks:** the frame at `period − 1/60` and the frame at 0 match in position, colour and speed. Sample 2–3 repetitions (`t0 + k·period`) and confirm there is no jump.

## Checks for every recipe

- **Determinism:** draw f 120, then f 40, then f 120 again. The two f 120 frames must match (`determinism_check.mjs`).
- **Reading:** every text window lasts at least `readingTime` (or `readingTimeChars`) after its first sharp frame ([kinetic typography](../craft/kinetic-typography.md)).
- **Blur:** at each peak, `pxPerExposure` decides the blur; above 80 px is a snap, not something to read ([blur](../craft/blur.md)).
- **Hits:** each physical change is in `plan.json` `hits`. The image and the sound read the same list ([rhythm and sync](../craft/rhythm-sync.md)).
- **Safe area:** every text element sits inside `plan.json` `safe_area` ([formats and platforms](../edit/formats-platforms.md)).
