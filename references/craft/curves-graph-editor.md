# Curves and the Graph Editor, in code

Read when choosing a curve, translating an After Effects setting, or when something looks linear, floaty or
jerky. Functions in `scripts/kit/motion-math.js` (and keyframes in `scripts/kit/timeline.js`); measurement with
`scripts/motion_curves.py`.

## 1. Value graph and speed graph

- **Value graph**: the property (position, scale, opacity) against time. It shows *where*.
- **Speed graph**: how much it changes per second. It shows *how*: height is speed, a flat stretch is constant
  speed, the area under the curve is the distance travelled.
- After Effects opens spatial properties (position, anchor point) in the speed graph and temporal ones (opacity)
  in the value graph by default (Adobe, "Speed").

`motion_curves.py` draws both and measures what the Graph Editor only lets you eyeball:

```bash
python -I <skill>/scripts/motion_curves.py --ease linear --ease easyEase --ae 80,80 --ease power3.out --distance 900 --duration .8 --out preview/curves.png
python -I <skill>/scripts/motion_curves.py --json preview/lens.json --key value --out preview/lens-curve.png
```

## 2. Influence and speed: Easy Ease and snappy curves

- **Easy Ease** (F9) sets speed 0 and 33.33 % influence on both sides of the key (Adobe, "Speed"). It equals
  `cubic-bezier(1/3, 0, 2/3, 1)`. Measured: its peak is **1.5×** the mean speed.
- **More influence** (70–90 %) lengthens acceleration and braking and concentrates speed in the middle. That is
  the snappy motion-graphics look: at 80/80 the peak reaches **~5×** the mean. It needs more blur at the peak.
- **Asymmetric**: fast departure and long arrival (`aeEase({outInfluence: 10, outSpeed: 2, inInfluence: 85})`), or
  the reverse for an exit that accelerates.
- **Naming trap**: in After Effects, *Easy Ease In* smooths the **arrival** at the key, which CSS calls ease-out.
  In the library, `'easyEase.in'` follows the After Effects convention.
- An After Effects speed in px/s converts to the `aeEase` scale with `aeSpeedMultiple(speed, distance, duration)`.

| In After Effects | In `motion-math.js` | For |
|---|---|---|
| Linear | `'linear'` | Loops, continuous rotation, scrolling backgrounds |
| Hold (stepped key) | `t < t1 ? a : b` (or a hold key in `timeline.js`) | Hard changes, blocking |
| Easy Ease | `'easyEase'` or `aeEase()` | On-screen move from A to B |
| Easy Ease In / Out | `'easyEase.in'` / `'easyEase.out'` | Only the arrival or only the departure |
| High influence | `aeEase({outInfluence: 80, inInfluence: 80})` | Energetic move with a fast middle |
| Exponential (Flow-style plugins) | `'expo.out'`, `'expo.inOut'` | Punchy entrance, long landing |
| Overshoot or bounce | `'back.out'`, `spring()`, `inertialBounce()` | Weight and life |

**Classic names and powers** (GSAP convention, used by the library): `power1` = quadratic (u²), `power2` = cubic
(u³), `power3` = quartic (u⁴), `power4` = quintic (u⁵). Aliases: `quad.out`, `cubic.out`, `quart.out`, `quint.out`.
Measured on the way out: cubic peaks at 3× the mean, quartic at 4×.

Directional rule to start from: **entrances ease-out, exits ease-in, on-screen moves ease-in-out, living things on
springs**. An ease-in on an entrance feels slow; an ease-in-out on an entrance feels floaty. A user's preferred
curves (for example "hero entrances with `back.out`, support with `cubic.out`") belong in their
[profile](../../profiles/README.md) and override this rule.

## 3. Springs: damping and overshoot

`spring(t, {freq, damping})` is the analytic response. Overshoot depends only on the damping ratio ζ:

| ζ | Overshoot | Character |
|---|---|---|
| 0.3 | 37 % | Playful, elastic |
| 0.4 | 25 % | Lively |
| 0.5 | 16 % | A glass lens that docks with life |
| 0.6 | 9.5 % | Firm with life |
| 0.7 | 4.6 % | Sober |
| 0.8 | 1.5 % | Almost no overshoot |
| 1.0 | 0 % | Critical: fastest without overshoot |

`springOvershoot(ζ)` gives the exact figure, `springSettle()` when it settles, and
`springFromPhysics({stiffness, damping, mass})` translates stiffness and mass. To make a spring land on a cue,
tune `freq` and dump the trajectory.

## 4. Spatial vs temporal interpolation

In After Effects the position path (spatial) and the speed along it (temporal) are separate. Keep them separate
in code too:

```javascript
const path = MotionMath.pathSampler(points);                        // the shape of the path, at constant speed
const u = MotionMath.easing('power2.inOut')((t - t0) / (t1 - t0));   // how it is travelled
const {point, angle} = path.at(u);                                  // angle gives auto-orient
```

- **Roving keyframes** (constant speed through several points) = `pathSampler`, which reparametrises by length.
- **A simple arc** between two points: `arcPoint(u, p0, p1, bend)`.
- **Speed continuity**: when one move hands over to another (A → B → C), the speed at B must match (*continuous
  bezier* in After Effects). Otherwise there is a kink: `motion_curves.py` lists it in `speed_kinks_at_s`. One
  curve over the whole path, or a physical follower, avoids it.

## 5. After Effects expressions and their equivalent

| Expression | Equivalent | Note |
|---|---|---|
| `linear(t, tMin, tMax, v1, v2)` | `MotionMath.linear(...)` | Also the three-argument form and vectors |
| `ease(...)`, `easeIn(...)`, `easeOut(...)` | `MotionMath.ease/easeIn/easeOut` | Hermite curve: an approximation of After Effects' |
| `valueAtTime(time - lag)` | `delay(fn, lag)` | Trails and overlap |
| `wiggle(freq, amp, octaves, amp_mult)` | `wiggle(t, {freq, amp, octaves, ampMult, seed})` | Deterministic: same seed, same noise |
| `loopOut("cycle")` / `("pingpong")` | `loop(t, period, 'cycle' \| 'pingpong')`, `loopValue(fn, t, period, mode)` | Also `offset` and `continue` |
| Inertial bounce | `inertialBounce(t, velocity, {amp, freq, decay})` | After a key, with the arrival speed |
| Time remap | `speedRamp(speedFn, {from, to})` | Slow motion or a sped-up range ([stepped time](stepped-time.md)) |
| `posterizeTime(12)` | `MotionMath.posterize(t, 12)` | Stutter. A bare `Math.floor(t*12)/12` skips poses at frame edges through float rounding |

Signatures checked against Adobe's expression reference and docsforadobe.

## 6. Checking a curve

1. Dump the real trajectory of the composition with `dump_state.mjs`.
2. `motion_curves.py`: peak speed and when, peak/mean ratio, overshoot, settle time and kinks.
3. With the peak in px/s, read the px per exposure (in the report) and choose the blur ([blur §2](blur.md#2-real-motion-blur)).
4. Look at the landing frame and its neighbours: the numbers do not say whether it feels right; the frame and the
   target device do.

## Sources

Adobe, "Apply and control speed changes" (Graph Editor, influence, Easy Ease), "Expression language reference";
docsforadobe, *After Effects Expression Reference*.
