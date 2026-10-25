# The 12 principles, applied to motion graphics

Read when designing any movement, or when something looks robotic, floaty or dead. The principles come from
classical animation (Thomas & Johnston, *The Illusion of Life*, 1981); here they are applied to video, not to an
interface: a short video can exaggerate more and hold longer, but it must leave reading time.
Functions: `scripts/kit/motion-math.js` (`MotionMath`). Curves in depth: [curves & Graph Editor](curves-graph-editor.md).

## 1. Starting durations at 60 fps

Craft ranges to start from, not perceptual laws. Scale with distance and size, then check at real speed.

| Feel | Frames at 60 fps | Seconds | Typical use |
|---|---|---|---|
| Snap | 6–10 | 0.10–0.17 | Impact, a word stamped on a beat |
| Quick | 12–20 | 0.20–0.33 | A word entering, a pop, a small object |
| Normal | 24–36 | 0.40–0.60 | A medium object crossing part of the frame |
| Heavy | 40–72 | 0.67–1.20 | A large object, the camera, a reveal |
| Dramatic | 90+ | 1.5+ | A long retreat, an orbit, an ending |

- **Distance** (adapted from LottieFiles): 100 px = 1×, 200 px ≈ 1.3×, 400 px ≈ 1.6×, crossing the frame ≈ 1.8–2×.
- **Exits** at 65–75 % of the entrance: what has been understood leaves sooner.
- **Offsets**: secondary parts 4–10 frames behind the leader; cascade offsets and totals in
  [rhythm §5](rhythm-sync.md#5-cascades-stagger).

## 2. The twelve, one by one

| Principle | In motion graphics | Starting numbers | In code | Symptom when missing |
|---|---|---|---|---|
| **1. Squash and stretch** | Stretch along the velocity, squash on impact, keep the area | Paper and glass ≤ 5–14 %; elastic 15–25 % | `squashStretch(speed)` → `{along, across}` | Hard rubber with no weight, or jelly where glass was meant |
| **2. Anticipation** | A short pull the other way before the action | 10–20 % of the travel, 6–12 frames | Piecewise target in `followerTable` | The action arrives unannounced and reads as a jump |
| **3. Staging** | One thing leads each moment; the rest calms, darkens or blurs | One focus per instant | Motion contrast, depth of field, vignette, opacity | The eye does not know where to go |
| **4. Straight ahead / pose to pose** | Pose to pose: key states and curves between them. Straight ahead: simulation (springs, particles) | — | Keys with `tween()` or `kit/timeline.js`; simulation with `followerTable` | Structureless motion, or lifeless poses |
| **5. Follow-through and overlap** | Secondary parts follow the leader late and settle after it | 4–10 frames of lag | `delay(fn, s)` or one follower per part | Everything starts and stops on the same frame: a rigid block |
| **6. Slow in, slow out** | Nothing starts or stops at full speed | Easy Ease peaks at 1.5× the mean speed | `easing('easyEase')`, `aeEase()`, `power3.out` | Robotic (linear) or floaty (slow ease-in-out on an entrance) |
| **7. Arcs** | Organic paths curve | Deviation 15–30 % of the distance | `arcPoint(u, p0, p1, bend)`, `pathSampler` | Mechanical diagonals on something organic |
| **8. Secondary action** | A smaller gesture that reinforces: shadow, glint, caustic, dust | Smaller and a little later | Layers derived from the leader's state | No detail, or detail competing with the action |
| **9. Timing** | The frame count gives weight and mood | Table in §1 | Durations in frames, never by eye | Everything lasts the same: no rhythm |
| **10. Exaggeration** | Push the key pose beyond the literal so it reads | Overshoot: paper 3–5 %, glass 0–16 %, rubber 15–25 % | `spring` with a chosen damping ([curves §3](curves-graph-editor.md#3-springs-damping-and-overshoot)) | Correct but lukewarm |
| **11. Solid drawing** | Coherent perspective, light and shadow across layers | One light direction per scene | 3D or well-scaled 2.5D camera; shadows share the light | Cut-outs glued on, no volume |
| **12. Appeal** | Clear silhouettes, readable paths, a pleasing rhythm | Silhouette test, greyscale test | [Dense review](../produce/review-protocol.md) | Correct but interchangeable with a template |

## 3. One worked example

A glass lens that hunts for an eye and docks into a letter:
- **anticipation, arc and overshoot**: it pulls 24 px the other way for 0.18 s, flies in an arc on a 1.7 Hz spring
  with damping 0.5 (≈16 % overshoot) and lands exactly on its cue;
- **squash and stretch**: it stretches up to 14 % with its speed and tilts with it;
- **secondary action**: its shadow and red caustic grow with its height;
- **follow-through**: after docking, a decaying scale wobble and a pulse of light;
- **staging**: in the macro shot its reflections dim so the eye leads.

## 4. Pose-to-pose workflow (as in After Effects)

1. **Stepped blocking**: key poses only, with holds, to check timing and staging at real speed. If the blocking
   does not tell the story, curves will not save it.
2. **Spline**: curves between poses (`tween`, `aeEase`, `kit/timeline.js`), arcs and overlap.
3. **Polish**: anticipation, overshoot, secondary action, blur, living layer; then the
   [review protocol](../produce/review-protocol.md) and `motion_curves.py`.

**Living holds**: a "still" state keeps camera breath and background drift of 1–3 % of the frame and a text float of
a few px ([living layer §2](living-layer.md#2-three-levels-of-motion)) so it never looks frozen. In
short-form, a hold also needs inner accents ([living layer](living-layer.md)).

## 5. Spacing charts

Plot the position on every frame: an ease-out bunches frames at the end, an ease-in at the start, an Easy Ease at
both ends. `node <skill>/scripts/dump_state.mjs … --step 0.0166667` and
`python -I <skill>/scripts/motion_curves.py --json …` draw that chart with the speed on top. A corner in the speed
graph is a kink: two segments meeting at different speeds.

## Sources

Thomas, F. & Johnston, O. (1981). *The Illusion of Life: Disney Animation*. Timing and material tables from the
`motion-design` skill (LottieFiles, MIT) and the `after-effects` skill (dylantarre, MIT), adapted to 60 fps
vertical video ([third-party credits](../../THIRD_PARTY.md)).
