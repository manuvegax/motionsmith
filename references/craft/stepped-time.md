# Stepped time: on twos, 12 fps, speed ramps and echo

Read when motion should feel more crafted or hand-made, for a "frame-rate lag" look, stop-motion, or slow motion
with character. Functions in `motion-math.js` (`posterize`, `stepped`, `speedRamp`, `echo`). Demonstration: block K
of the [technique lab](../../templates/technique-lab/).

## 1. What it is

In traditional animation, drawings are made **on twos**: each held for two frames of 24 (12 poses per second).
Motion graphics imitate it with **Posterize Time** (After Effects effect) or the `posterizeTime(fps)` expression:
the animation is computed at 60 fps, but each pose is held and then jumps. It is not slow motion (speed does not
change); the cadence changes, and it feels tactile and intentional.

| Variant | Cadence | Feels | Code |
|---|---|---|---|
| K1 · Fluid | 60 poses/s | Clean, digital | Normal time + motion blur |
| K2 · Twos at 60 | 30 poses/s | Nearly fluid, a little firmer | `posterize(t, 30)` |
| K3 · 12 fps | 12 poses/s | Hand-made, soft stop-motion: classic "twos" at 24 fps | `posterize(t, 12)` |
| K4 · Hybrid | Object at 12, camera and background at 60 | The most "pro": character without nausea | Object with `posterize`, camera with `t` |
| K5 · Speed ramp | 60, speed varying | Fast → slow → fast: slow motion that hits | `speedRamp(speedFn)` |
| K6 · Echo | 60, with earlier copies | A graphic trail of the motion | `echo(t, {count, lag, decay})` |

## 2. Doing it well

- **The master stays at 60 fps.** Only what should step is stepped; the file never drops its frame rate.
- **Hybrid by default**: elements (type, objects) at 12 or on twos; camera and continuous backgrounds fluid. A
  stepped camera jerks and nauseates (*Spider-Verse* mixes ones and twos per character).
- **Motion blur**: at 12 fps, either none (crisp stop-motion) or an exposure relative to the step (low-frame-rate
  film). Never 60 fps blur on poses that jump: both show at once. With posterized time inside the exposure window,
  the samples collapse to one pose, so stepped type stays crisp automatically.
- **Fast moves at 12 fps**: an object crossing a lot of space jumps too far between poses. Split the gesture, or
  use a *smear*: stretch the object along the motion on the fast pose.
- **Synchronised boil**: textures (print, grain, line) change at the same cadence as the poses.
- **Hits on steps**: at 12 fps, `hits` should fall on a pose change (multiples of 1/12 s) so the sound meets
  something that moves.
- **Per-element offsets**: posterize each element's *local* time (`posterize(t − start, 12)`), so a cascade of
  letters does not step in lockstep.
- **Determinism**: `posterize` adds an epsilon so frame centres never fall on the wrong side of a step
  (`floor(t·fps + 1e-6)`); a bare `Math.floor` skips poses.

## 3. Speed ramps

`speedRamp(t => speed, {from, to})` integrates a speed curve (1 = normal, 0.2 = very slow, 2 = double) and returns
the content time; After Effects time remapping does the same.
- The classic ramp: in fast, brake on the instant that matters (an impact, a reveal), out fast.
- The slow stretch needs less motion blur (real sub-samples give it automatically) and something to look at.
- For real footage a ramp needs a higher capture frame rate or interpolation; in code-made motion it is free.

## 4. Echo

After Effects' Echo composites earlier copies of the layer. `echo(t, {count: 5, lag: .06, decay: .55})` returns
instants and opacities; draw from oldest to newest. Good for graphic whips and the trail of a hero object; 3–6
copies are enough. For type, outline echoes are usually better ([kinetic type](kinetic-typography.md)).

## 5. Check

- Consecutive frames (`sample_frames --frames a:b`): at 12 fps a pose repeats for 5 frames and jumps; on twos, 2.
- In the hybrid, background and camera move on every frame.
- In a ramp, `motion_curves.py` on the dumped trajectory: speed drops where planned.
- At real speed on the target device, it must not nauseate: that test belongs to the viewer.

## Sources

Adobe, "Using time effects in After Effects" (Posterize Time, Echo), "Expression language reference"
(`posterizeTime`), "Time-stretching and time-remapping".
