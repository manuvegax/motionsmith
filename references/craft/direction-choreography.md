# Direction and choreography

Read when choosing a visual language, building a shot, fixing a generic finish, or when someone asks for work
"like After Effects", "more motion" or "more editorial". The goal is a designed montage: spatial relations,
materials, speeds and transitions that hold together. Choose the operations the idea needs; never pile up effects.
Style frames and art direction: [art direction](../create/art-direction.md).

## 1. One visual action, one consequence

- Write the action as a verb: separate, accumulate, substitute, reveal, compress, compare, erase, pass through.
  "Elegant", "cinematic" and "very pro" are not programmable actions.
- Find the instant where the new thing is understood. That instant gets the best hierarchy.
- In a narrative insert, say what makes it necessary: it clarifies a relation, turns a metaphor into action, shows
  evidence, contradicts what is heard, or prepares the return to the person. If removing it changes nothing,
  rethink it or cut it. A visual pause can have a function too.

## 2. Style state before animating

Resolve one frame of maximum information at final size and at ~360 px wide:
- **Hierarchy**: one dominant focus, one support, one background. Scale contrast creates priority.
- **Grid**: alignments tied to object and text, breathing room, the safe area.
- **Type**: one leading family and, when it helps, a secondary one per role. Check files, accents, figures and
  punctuation before rendering. Never substitute the brand face silently.
- **Palette**: roles for background, ink and accent. Three colours plus neutrals is a good test limit, not a law.
- **Matter**: sharp images, clean mask edges, texture at scale. Grain can unify mixed photos; it must not hide low
  resolution or compete with text.
- **Space**: background, subject and foreground with ordered depth; the same light, shadow and perspective across
  cut-outs that must live together.

Do not carry a reference's micro-labels, stamps, codes, crosses and numbers into the master as decoration.

## 3. Choreography: preparation, action, consequence

Each scene records `motion` with four concrete texts (see [plan schema](../produce/plan-schema.md)):
- `preparation`: who prepares attention, when, by how much.
- `action`: the dominant element, path, distance, scale and window of peak speed.
- `follow_through`: which layer answers afterwards or carries into the next scene.
- `reading`: when it is understood and reading recovers; with no text, what is recognised.

A justified absence is allowed (`none, fixed camera to hold the read`). Use offsets and speeds by function, not
one uniform stagger. Design distances as well as durations: a 1100 px swipe in 0.18 s needs another exposure and
landing than a 25 px drift over 0.6 s. Overshoot goes on the hero, not on everything: never make paper, photo and
camera all wobble alike.

**Motion grammar**: mass (big things need more time and settling), relation (cause enters before effect; the delay
means something), arcs, continuity (keep position and, where it applies, speed across links), contrast (a fast move
stands out only against stillness; moving everything dilutes attention).

### The action score (frame by frame)

For a hero action, write a table of windows covering every frame: dominant action and anticipation → path/anchor →
**contact frame** → secondary response and reading. Contact frames are design events, not clock callbacks: the
response starts only after them, computed from absolute frame numbers:

```text
p = clamp((frame - start) / (end - start), 0, 1)
position = path(p, fixed_anchor)
response = before_state                                 if frame < contact + lag
response = absolute_function(frame - contact - lag)     otherwise
```

The response is indispensable: if removing it changes nothing, the hero is decorative even if it blinks. The
action must read with a fixed camera and without blur.

## 4. A physical follower, precomputed

When something chases with weight (a lens following a gaze, a camera following its subject), integrate a
spring-damper **once at load** with a small fixed step (1/960 s) and store position and velocity in a table; each
`seek(t)` interpolates it. Physics, and the same `t` still gives the same frame. A `mix()` between two poses has no
inertia; a spring integrated during capture cannot seek backwards.
- Piecewise target: follow another variable with a delay, then a short pull the other way (anticipation), then the
  destination.
- Tune ω and ζ so it lands when it should; **dump the trajectory** (`dump_state.mjs`) instead of trusting the last frame.
- Derive tilt (clamped ±0.35 rad) and stretch (≤ 14 %) from velocity; on docking, a light pulse and a fast-decaying
  scale wobble. The pivot returns exactly to rest on the cue. `MotionMath.followerTable` implements it.

## 5. Continuity that produces a reveal

Repeating the same eye, object or word does not link actions by itself. Check the chain:
**previous state → action that changes it → relation discovered → result kept**. If continuity is promised, show
which detail the viewer can follow through the link: a reflection, an edge, a counter, a baseline, a contact point.
- Design the camera's destination before its path. A macro earns its zoom if it discovers something the wide shot
  did not show; a pull-out can reveal that what we saw was a fragment of a larger composition (an eye living inside
  the counter of an O becomes a word when the camera retreats).
- The ending keeps the new relation; going back to "photo on top, headline below" loses the transformation.
- Local links and editorial cuts coexist. A cut can have a job: call a cut a cut, a wipe a wipe.

Transitions in depth: [transitions atlas](../edit/transitions-atlas.md).

## 6. Morphs

- Two images cross-faded are a dissolve, not a morph.
- Normalise origin, winding and topology; resample by segment length so point density matches
  (`MotionMath.resamplePath`, `alignPaths`, `morphPath`); keep semantic anchors.
- Check 0, 25, 50, 75 and 100 % plus a strip around the point of greatest deformation: no spikes, holes,
  self-intersections, winding flips, double edges or jumping pivots. A still at 50 % can pass and hide a jump at 49 %.
- If the assets cannot support the transition, redesign the link or declare the simplification.

## 7. Camera, 2.5D and 3D

- One camera family per scene: stable frontal, an editorial camera travelling a plane, or a 3D space with consistent
  depth. Changing family needs a motive and a prepared transition ([camera & space](camera-space.md)).
- 2.5D uses flat cut-outs; it does not rebuild a hidden face. Limit the turn so that limit never shows. Real volume or
  an orbit needs geometry, lights and a 3D camera. A photo that only scales is not "real 3D".
- A transition by camera needs a shared space or an occlusion that justifies it; otherwise say "cut".

## 8. Modes

| Mode | What it is | Keys |
|---|---|---|
| **Editorial narrative** | Cut-outs, archive, scenes, return to the person | Matter with meaning, collage planes with roles (context, lead object, type that orders, detail that confirms) |
| **Kinetic continuous** | One carrier links scenes | A persistent object or edge that is followed |
| **Diagram / interface** | A relation that is understood | Axes, units, honest proportions; cursor approach, contact and response |
| **Glow minimal** | Silhouette, layered materials, one accent | Charcoal background, frosted materials, one accented part that carries meaning ([glass & WebGL](glass-webgl.md)) |
| **Retro** | Tube, tape, glitch | [Retro looks](retro-looks.md) |

Glow, textures, capitals and cuts depend on the mode; do not mix prohibitions from different modes.

## 9. Diagrams, data and interfaces

Say what changes and why. Give axes, units and proportional mapping whenever a magnitude is claimed; never
"improve" a curve so it looks like a finding. A conceptual diagram is labelled as illustrative. A cursor has
approach, contact and response times; no clicks into the void, invented values or unreadable filler text.

## 10. An actor that acts

If the protagonist must act, separate movement from the inner gesture frame: animate gaze, eyelid, pose or joints
and test them with a fixed camera. A photo that moves is not an articulated actor; prepare clean plates and masks so
no second pupil or holes appear.

## 11. Three artistic gates before the final render

1. **Compared direction**: your sequence of states next to the observed reference moments; what was reinterpreted,
   and which material or composition proves it. Reject a result interchangeable with a template.
2. **Choreography**: the hardest stretch and the whole piece in consecutive frames: who prepares, who leads, what
   follows, when it reads. Reject zooms and entrances with no relation, monotony or noise that kills hierarchy.
3. **Matter and optics**: blur on/off at the peak and the landing; detail at the closest zoom and in the compressed
   MP4. Reject ghosts, halos, unmotivated focus, text that never resolves, placeholder material.

These are direction judgments with evidence, separate from export and determinism checks. A numeric check does not
replace them, and 60 fps plus a correct codec never proved craft.

## 12. Frequent errors and the first fix

| Symptom | First fix |
|---|---|
| Looks like a template | Change the relation between image and phrase, the link or the composition; do not add effects |
| Looks AI-made (glows, bursts, crossfades, bounce, corner text) | Write the banned list with its alternatives ([motion brief §3](../create/motion-brief.md#3-the-banned-list)); give every effect a reason in the scene |
| A tour of effects, no idea | One `concept:` line and one recurring element that carries every transition ([motion brief](../create/motion-brief.md)) |
| Pretty but not understood | Choose the instant of meaning; reduce competition; give reading time |
| Everything floats | Anchor pivots, give contact and mass, decide what is still relative to what |
| Text trembles | Check scaling, hinting, fractional positions and reflow; compare frames without blur |
| The morph jumps | Fix correspondence and continuity; never hide it with a flash |
| Washed-out finish | Check contrast and the sum of halos; do not raise white indiscriminately |
| Blurry when zoomed | Replace the asset or reduce the zoom; a higher export resolution does not recover detail |
| The face disappears behind text | Redesign the layout for the real footage and the interface mask |
| It feels static | [Living layer](living-layer.md) and [pacing](../edit/pacing-retention.md): accents inside holds |

## Sources

Adobe documentation ("Speed", "Animating text", "Blur and sharpen effects", "Cameras, lights and points of
interest") supports the operations; the direction decisions and gates belong to Motionsmith. Recipes per problem
informed by `bang-motion`, `motion-design-principles`, `motion-design` and `kinetic-typography`
([third-party credits](../../THIRD_PARTY.md)).
