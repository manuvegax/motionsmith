# Camera and space

Read when deciding how the camera moves, building depth, or when a shot feels static or nauseating. Editing-level
choices (shot order, cuts) live in [cutting](../edit/cutting.md); here, technique and numbers.

## 1. Shot sizes

| Shot | What is seen | Use |
|---|---|---|
| Wide | The whole composition | Reading several things together, showing the relation |
| Medium | The main element with some context (⅓–½ of the frame) | Explaining |
| Close-up | One element fills the frame | Emphasis, a detail that must be read |
| Macro | A detail of the element | Discovering what the wide shot did not show |

Vary the size between consecutive shots; two equal sizes in a row feel flat. A shot can be born close and pull
out; an ending that holds keeps a slow push so it never freezes.

## 2. Moves

| Move | What it does | Starting numbers | When |
|---|---|---|---|
| **Push-in / dolly in** | Approach the subject | 0.8–2 s, ease-in-out; ×1.1–2 | Emphasis, entering something |
| **Pull-out / reveal** | Move away and discover the context | 1–2 s, ease-out | "What you saw was part of something bigger" |
| **Truck** | Lateral move | With 3-plane parallax | Connecting two elements |
| **Pedestal / crane** | Up or down | Slow | Vertical reveals |
| **Pan / tilt** | Rotate the camera | In 2.5D: translation + slight perspective | Following an action |
| **Orbit** | Circle the subject | 10–30° arc, ease-in-out | Volume, presenting an object |
| **Whip pan** | A very fast swipe that hides a cut | Swipe 6–12 frames (0.1–0.2 s), 0.3 s with its ease tails; a whole frame width; 360–400° shutter | Energetic scene change |
| **Dolly zoom** | Background changes size, subject does not | Focal ∝ distance | Vertigo, inner revelation |
| **Rack focus** | Change the plane in focus | 0.5–1.2 s | Moving attention without moving the camera |
| **Handheld** | Continuous organic drift | Noise 0.5–1.5 Hz, 2–6 px | A living base ([living layer](living-layer.md)) |
| **Camera punch** | Zoom or shake on an impact | Zoom 2–5 %, 6–12 px shake that decays | On the `hits` |

## 3. Focal length, perspective and parallax

- **Focal**: in After Effects, 50 mm is "normal"; a wide angle exaggerates depth (short focal, camera close), a
  telephoto flattens it. In a WebGL engine, a focal of 1700 px with the camera at 1700 shows z = 0 at real size.
- **Projected scale** = focal / distance to camera. A plane at half the distance looks twice as big.
- **Parallax**: apparent speed of a plane ∝ focal / distance. Background at 0.2–0.4× the foreground's speed. Moving
  every layer equally gives no parallax.
- **Dolly zoom**: keep `focal / distance` constant for the subject while the distance changes.
- `MotionMath.lookAt(eye, target)` and `MotionMath.project(p, cam, {focal, center})` cover a simple 3D camera.

## 4. Rigs

- **Target camera** (*point of interest*): position and look-at; the right/down/back basis is rebuilt with cross
  products (`lookAt`).
- **Camera on a null**: an orbit is rotating the null; in code, position = target + spherical coordinates.
- **Inertia**: the camera follows its target through a follower (`followerTable`) 0.1–0.3 s behind. Camera and
  subject never accelerate identically, or the sense of motion is lost.
- **Screen layers and world layers**: interface text, captions and on-screen displays live outside the camera
  (they neither grow nor get cut); story objects live inside it.

## 5. Shakes

| Kind | Build | Numbers |
|---|---|---|
| Handheld | `wiggle(t, {freq: .8, amp: 4, octaves: 2, dims: 2})` | 0.5–1.5 Hz, 2–6 px |
| Impact | `shake(t, hits, {px})` (decays with `exp(−14·Δt)`, starts at rest) | 6–12 px, hits ≥ 0.8 only |
| Vibration | Sine at 20–40 Hz | 1–2 px; engines, tension |
| Zoom punch | `focal × (1 + 0.035·impulse(t, hits))` | 2–5 % |

## 6. Rules

- One camera family per scene (frontal, editorial 2.5D or 3D); change family with a motive and a prepared transition.
- Do not rotate, zoom and translate at once without a focus that organises them.
- Text appears when the camera arrives, not mid-move.
- The world is bigger than the frame (overscan): no edge visible at the peak of a move.
- Do not alternate near and far faster than the eye can look: it nauseates.

## 7. Check

- Dump the camera position with `dump_state.mjs` and pass it through `motion_curves.py`: the camera has curves and kinks too.
- A frame at the peak of each move: world edges, cut text, resolution of scaled assets.
- A dense window on each whip: the cut must hide in the blurriest frame.

## Sources

Adobe, "Cameras, lights, and points of interest". `bang-motion` skill (MIT): shot sizes and screen layers.
