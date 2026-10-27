# Keyframes and cuts: making it move like After Effects

Read when a piece "works but does not feel like After Effects": robotic moves, everything arriving at once, scenes
that cut or dissolve instead of handing over. What makes AE work feel designed is not effects: it is the speed graph of
every key, the offsets between layers, layers that inherit motion from their parents, precomps that overlap at a cut,
and transitions whose swap happens under a hit. `scripts/kit/comp.js` puts that model in code; the recipe
`editorial-collage` is built entirely with it.

## 1. The composition model

| After Effects | comp.js | Notes |
|---|---|---|
| Layer: anchor point, position, scale, rotation, opacity | `Comp.layer({anchor, position, scale, rotation, opacity, draw})` | Each property a value, a function of time, or keyframes |
| Keyframes and the graph editor (influence, speed) | `Comp.k([t, v, ease], …)` | The ease named on a key shapes the segment that leaves it |
| Parenting (a child follows its parent's transform, not its opacity) | `parent: 'name'` | Title, rule and items of a card are its children: the card's drop carries them |
| Null object | A layer with no `draw` | A control for a group |
| Precomp with time remapping | `layer({comp, timeRemap or speed})` | A scene is a precomp; time remap ramps or freezes it |
| Masks and track mattes | `mask(ctx, t)`, `matte: {layer, invert}` | Iris and slice transitions are masks |
| 3D layer, camera, depth of field (focus distance, aperture) | `threeD: true`, `comp({camera: {position, zoom, focusDistance, aperture}})` | 2.5D: perspective by depth, blur by distance from the focus plane; key the focus for a rack focus |
| Motion blur | The stage's sub-frame motion blur, fed by `comp.track(t)` | Every layer reports two points; no hand-written track |
| Sequence layers with overlap, transitions | `Comp.sequence(scenes, transitions)` | The incoming precomp sits on top during the overlap |

## 2. Keys: the speed graph decides the feel

AE's Easy Ease is 33 % influence on both handles with zero speed: symmetric, polite, recognisable as "default". Pros
drag the handles. Named eases in `comp.js` (out influence / in influence, both at speed 0):

| Ease | Handles | Speed graph | Use |
|---|---|---|---|
| `easy` | 33 / 33 | A symmetric bump | Camera drifts, things that should not draw attention |
| `snap` | 12 / 88 | Peak in the first fifth, long settle | The default for anything arriving: words, cards, objects |
| `punch` | 5 / 95 | A spike, then a very long settle | Slams, logo hits, the keyword |
| `swift` | 40 / 85 | Quick but not abrupt, long settle | Moves inside a scene, camera pull backs |
| `glide` | 55 / 60 | Soft both ends | Background drift, slow dollies |
| `accel` | 85 / 12 | Leaves slowly, arrives fast | Exits, the start of a whip or a zoom through |
| `whip` | 72 / 72 | Slow, violent middle, slow | Whip pans (the middle is where the blur lives) |
| `hold` | — | A step | A value that jumps on the key (AE hold keyframe) |

Measured with `comp.js`: a 1000 px `snap` move peaks in its first fifth and moves under a tenth of that speed in its
last tenth: that long tail is what reads as "expensive". A linear or a symmetric ease on an arrival reads as default.

- **Overshoot is a key, not an elastic.** `Comp.overshoot(t0, from, t1, to, {amount: .04–.10, settle: .2–.3})` adds
  the key a designer drags past the target and back. Use it on the hero, small on secondary layers, never on text
  that must be read while it settles (keep `amount` under .08 for type).
- **Scale and rotation get their own curves.** A keyword lands from 135 % with `punch`-like settle while its position
  uses `snap`; a card rotates from 14° to −3° while it drops. Properties settling at slightly different times is what
  makes a move feel physical.
- **Opacity is fast.** Fade in over 3–5 frames (`snap`), never over the whole move; the move carries the entrance.
- **Blur in, not fade in, for type**: 10–14 px of blur clearing in 6–8 frames reads as focus, not as a dissolve.

## 3. Offsets: nothing starts together

| What | Offset |
|---|---|
| Words of a line | 3 frames each |
| The keyword after the line | 6 more frames |
| Children of a card (title, rule, items) | The title 12 frames after the card starts to fall; items 5 frames apart |
| Secondary elements after the hero lands | 4–10 frames |
| Leaving in turn (notifications switching off) | Reverse order, 4 frames apart, `accel` |

Offsets are counted in frames (at 30 fps a frame is 33 ms), as in AE's timeline. A cascade with equal offsets reads
as mechanical past five items: shorten later offsets slightly, or group them.

## 4. Cuts: scenes hand over

- **Precomps overlap.** A transition is an overlap of two precomps, 8–16 frames, where both are driven by the
  transition's keys. A hard cut is an overlap of zero.
- **Swap under the hit, never through a dissolve.** In a zoom or a spin the outgoing scene accelerates until it fills
  the frame; on the half, under a two-frame flash or the keyword's colour, the incoming scene takes over already
  moving and settles. Two half-transparent scenes on screen at once is a crossfade (`tests/test_comp.py` refuses
  one in any transition).
- **Keep the direction of motion.** A whip carries both scenes the same way; a push lands with a small overshoot; a
  zoom's incoming scene starts larger (≈160 %) and settles to 100 % with the blur clearing, so no edge shows.
- **Cut on the beat, or a frame before it.** The hit and the swap share a frame; the sound's attack can lead by 1–2
  frames. Cut on the action: the outgoing scene is still moving when the cut comes.
- **Durations**: whip 9–11 frames, push 12–16, zoom through 14–16, iris 12–14, slices 14–18, spin 14–16; a hard cut
  for a change of world (paper → black), with the hit.
- **Match the carrier.** The keyword's red becomes the flash; the ribbon passes through both scenes; a print lands
  on the last one. Without a carrier, a hard cut on the beat is better than a decorative transition.

| Transition | Outgoing | Incoming | Swap |
|---|---|---|---|
| `whip` | Travels a full frame, `whip` ease | Travels with it | Continuous |
| `push` | Pushed out, shrinks 6 % | Lands with an overshoot (`back.out`) | Continuous |
| `zoom` | Scales ×27 into a point, `expo.in` | From 160 % to 100 %, blur 28 → 0, `snap` | Half, under the flash |
| `iris` | Steps back 5 % | Opens in a circle from a point, `snap` | Mask |
| `slice` | Drifts up | Bars sweep it in, staggered | Mask |
| `spin` | Spins away accelerating | Spins in from the other side | Half |
| `cut` | — | — | On the frame |

## 4b. Layer effects

`layer({effects: [...]})`, applied in order on the layer's own pixels (or on its time):

| Effect | After Effects | Options | Use |
|---|---|---|---|
| `glow` | Glow | `radius`, `strength` (0–2), `color`, `mode` (`lighter`, `screen`) | A keyword on black, a light that emits |
| `shadow` | Drop Shadow | `x`, `y`, `blur`, `color` | Type or cut-outs over a busy ground |
| `echo` | Echo | `count`, `step` (s), `decay` | Trails on a fast move, a stutter on a hit |
| `rgbSplit` | Channel offset / chromatic aberration | `px` (or a function of time), `angle` | Accelerating into a zoom, a glitch on a cut; 0 at rest |
| `tint`, `fill` | Tint, Fill | `color`, `amount` | Recolour a layer to the accent |
| `lightSweep` | CC Light Sweep | `at`, `dur` or `period`, `angle`, `width`, `intensity` | A gloss across a title or a logo once it has landed |
| `posterize` | Posterize Time | `fps` | One layer on twos (12 fps) while the rest stays fluid |

An effect earns its place with a reason in the scene ([motion brief §3](../create/motion-brief.md#3-the-banned-list)):
the glow because the word emits, the split because the camera accelerates, the sweep because the title has just landed.

## 4c. Motion styles

`Comp.style('editorial' | 'punchy' | 'calm' | 'sober')` sets, for the whole piece, the arrival and exit eases, the
offset between layers, the overshoot amount, the residual drift, the scene breathing and the transition durations.

| Style | Arrival | Offset | Overshoot | Drift | Breathing | Use |
|---|---|---|---|---|---|---|
| `editorial` | `snap` | 3 frames | 6 % | 5 px, 0.35° | 6 %, sway 10 px | Essays, explainers, the default |
| `punchy` | `punch` | 2 frames | 10 % | 7 px, 0.5° | 8 %, sway 14 px | Promos, hooks, music-led reels |
| `calm` | `swift` | 5 frames | 3 % | 3.5 px, 0.25° | 4 %, sway 7 px | Reflective pieces, slow voice-overs |
| `sober` | `swift` | 4 frames | 0 | 2 px, 0.1° | 2.5 %, sway 4 px | Data, overlays, institutional work |

Drift and breathing look large on paper; on screen they are 0.15–0.3 px per frame (5–9 px a second), under the
threshold of notice. The breathing push eases in over the first fifth of a scene and then keeps a constant speed to
its last frame: an ease-out would bring it to rest exactly where the shot ends. Each scene is overscanned just enough
(about 3 % in `editorial`) that its sway and tilt never uncover the edge of the frame; `breathe: {overscan: false}`
turns that off for a scene whose edges must stay exact.

Set it before building the layers (`Comp.style('punchy')` at the top of `setup`), or pass a partial object to change
one value (`Comp.style({overshoot: .04})`).

## 5. Camera

- One family of moves per scene: a slow dolly (`glide`, 5–10 % closer over the scene), a rack focus (`hold`, then
  `swift` over 0.5–0.8 s), a pull back to give context (`swift`).
- Depth of field is what makes a 2.5D scene read as depth: aperture 10–20 px at twice the focus distance; the
  phrase on the focus plane, the figure behind it out of focus, then the focus moves to the phrase as it lands.
- Never move the camera and the hero with the same curve at the same time: one leads, the other follows 3–6 frames.

## 6. Checks

- **Speed graphs**: dump a layer's position over time (`dump_state.mjs`) and look at `motion_curves.py`: arrivals peak
  early and settle long; no constant-speed segments except loops.
- **Dense windows on every cut** (`sample_frames.mjs --frames a:b`): no frame shows two half-transparent scenes; the
  swap frame is covered by the flash or the carrier; no empty frame after a transition.
- **Offsets**: a sheet at 3-frame steps through a cascade shows each layer one step behind the previous.
- `tests/test_comp.py` covers the model: snap's speed profile, overshoot keys, parenting, sequence overlaps and that
  no transition crossfades.

## Sources

Adobe After Effects documentation: keyframe interpolation, the graph editor (influence and speed), parenting, null
objects, precomposing and time remapping, track mattes, 3D layers and the camera's depth of field. The named eases,
offsets and durations are Motionsmith's defaults from frame-by-frame study of editorial reels; measure your own
references the same way and record your choices in the profile.
