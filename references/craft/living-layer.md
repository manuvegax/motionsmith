# The living layer: synced accents and "more dopamine"

Read when someone asks for more motion, "more dopamine", a background that is not static, or when a piece feels
still even though its main action works. In short-form, stillness is where viewers leave
([pacing & retention](../edit/pacing-retention.md)).

## 1. The rule

- **The first frame moves.**
- **No stretch longer than ~0.5 s where the frame barely changes.** A reading hold keeps the text still enough to
  read and moves everything around it.
- A production case (one piece, not a study, but it matches what retention graphs of short video show: viewers
  decide in the first seconds, and a frame that does not change reads as a still image): a piece approved for its
  craft lost almost every viewer in the first seconds because it had 1–1.5 s holds; rebuilt with inner accents (type that glitches, echoes, an inversion flash, moving type layers,
  a printed texture that boils), the same story stopped looking "the same".

In sober pieces (diagrams, data) and overlays that sit on footage, ask before applying this layer and give them an
ambient budget instead (drift and breath, no accents); in short-form social video it is the default. Measure it:
the mean frame difference of a hold, after downsampling away the grain, should not sit near zero for more than
~0.5 s.

## 2. Three levels of motion

| Level | What moves | Amplitude | Rule |
|---|---|---|---|
| **Ambient** | Background, camera drift, text float, dust, moving outline type | Small and slow: text float ±4 px at 1080 wide; camera breath and background drift 1–3 % of the frame; ≤ 0.5 Hz for drift, ≤ 2 Hz for float | Nothing is fully still; nothing competes with the action. The single source for idle amplitudes |
| **Accents** | Zoom, shake, RGB split, flash, background breath, inversion, misregistration kick | Fast and short: decay in 0.1–0.3 s | On the sound's `hits`, plus a few sub-beats inside long holds |
| **Reading** | The text or object that must be understood | Coherent float ≤ 4 px per word; stepped boil ≤ 5 px | Sharp and settled; the ambient keeps living behind it |

Contrast is what makes it work: a legible anchor over a living background, and hits that land with the sound.
"Everything vibrates" is not this layer.

## 3. Proven recipes

| Layer | Build |
|---|---|
| Parallax grids | Two repeatable textures (a fine 32 px grid and a 128 px grid with crosses) sliding at different speeds; their opacity breathes with `impulse(t, hits)`. No depth writes |
| Paper grain | The texture offset **jumps** every 1/24 s; a continuous offset is seen sliding |
| Dark background | Vignette + a faint grid rising + a radial mask + ~70 seeded particles (18 % in the accent), gentle twinkle |
| Handheld camera | Slow sines of ±4 px in x/y; on hits, a 3.5 % zoom and a shake decaying with `exp(−14·Δt)` |
| Image on hits | RGB split ~0.011 decaying with `exp(−8·Δt)`; a 0.1–0.3 flash on the key reveals |
| Light sweeps | A diagonal additive band crossing in 0.4–0.5 s on cuts; above 1 it feeds the bloom |
| Moving type layers | Giant outline words (6–12 % opacity) marching behind each scene at constant speed; a coloured ticker band with running copy |
| Type inside holds | Font glitch (one letter, one 12 fps step), boil, outline echoes, a one-step inversion flash twice ([kinetic type](kinetic-typography.md)) |
| Printed texture | Screen print with ink that boils at 12 fps and misregistration that kicks on hits ([print & textures](print-textures.md)) |
| Final grain | Different noise every frame (~0.02); it also dithers |

A common base in JavaScript, the same hit list the soundtrack uses:

```javascript
const hits = plan.hits;   // [{time, amplitude, role}] from plan.json
const punch = 1 + .035 * MotionMath.impulse(t, hits, 9);            // camera zoom
const [sx, sy] = MotionMath.shake(t, hits, {px: 7});                 // impact shake, starts at rest
const aberration = .011 * MotionMath.impulse(t, hits, 8);           // RGB split for finish()
```

Everything depends only on `t`: the same instant gives the same frame when seeking backwards.

## 3b. Moving holds: the motion that never stops

The best motion graphics never reach speed zero. When a card lands or the last line settles, something keeps moving
so slowly that nobody sees it move, only that the picture is alive: a push of a few percent over the shot, a drift of
a few pixels, a sway of tenths of a degree. A frame that repeats exactly reads as frozen, and the ending of a piece is
where it shows most.

| Device | Amount (1080 px frame) | In `kit/comp.js` |
|---|---|---|
| Residual drift of a layer after its last key | 2–7 px of wander, 0.1–0.5°, growth 0.3–1.1 % per second, eased in over 0.6 s | `layer({drift})`: on by default, from the style; `drift: false` for a layer that must not move |
| Scene breathing (the slow push on every shot) | 2.5–8 % of scale over the scene at a constant speed after an ease-in (never an ease-out), a sway of 4–14 px and 0.1–0.6° | `sequence(…, {breathe})` or per scene `{breathe}`; on by default |
| Light that wanders | A sweep every 3–6 s, a glow that pulses 5–10 % | `effects: [{type: 'lightSweep', period}]`, a glow strength on keys |
| Matter | Grain that changes every frame, paper drifting slower than the subject | The stage's finish; a paper layer with its own slow keys |

- **Under the threshold of notice**: if a viewer can say "it is moving", it is too much for a hold. Measured on the
  edges of a 1080 px frame, 0.15–0.3 px per frame reads as alive and still; under 0.05 reads as frozen.
- **Overscan the sway**: a scene that sways or tilts must start slightly larger than the frame (103-104 %), or a
  strip of background shows at an edge. `comp.js` computes it from the sway; `tests/test_holds.py` checks every corner.
- **No ease-out on the push**: the slow push keeps its speed to the last frame; easing it out freezes the end of every
  shot.
- **Never the same speed twice**: the drift is noise (two octaves, 0.1–0.25 Hz), not a constant slide, which reads
  as a mistake.
- **The end too**: the last 1–2 s of a piece keep breathing to the last frame; the hit lands, the motion goes on.
- **Measure it**: `python -I <skill>/scripts/hold_check.py final/piece.mp4 --curve preview/motion.png` reports every
  stretch whose edges move slower than 0.06 px per frame (grain does not move edges). On the editorial collage the
  card hold and the last two seconds read 0.00 (frozen); with moving holds the quietest stretch reads 0.18 and the
  ending 0.29, alive and still unnoticed.

## 4. Costs and limits

- **Bitrate**: grain, moving grids and halftones raise file size a lot (14 → 39 MB for grids and grain; ~3× more with a
  full-frame halftone). Check the weight and the compressed frame.
- **Determinism**: fixed seeds and frame numbers; never `Math.random()` or the clock.
- **Dose**: zoom 0.035, aberration 0.011, grain 0.022, boil 4–5 px are starting levels. When the viewer says "too
  much" or "too little", change those numbers before the choreography.
- **Occlusion**: new background layers never write depth ([glass & WebGL §2](glass-webgl.md#2-depth-the-rule-that-prevented-most-bugs)).
