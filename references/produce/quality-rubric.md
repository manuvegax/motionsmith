# Quality rubric, blockers and evidence

Read when deciding whether a piece can be delivered and what evidence must back that decision. The order of
review steps is in the [review protocol](review-protocol.md).

## 1. What is reviewed and with what evidence

| Layer | Test | Evidence that must remain |
|---|---|---|
| Composition | Frames of maximum occupation, complete text, silhouette | Images and the concrete defects/fixes |
| Requested language | The walk of compositions against the reference moments | Observed operation, own application, comparable samples |
| Optics | Peak with/without blur and the landing; material at closest zoom | Trail and focus told apart, reading recovered, defects fixed |
| Time | Proxy at real speed, transition strips, intermediate states | Which stretches were seen and the real reach of playback |
| Energy | Walk every 0.5 s | No dead stretch; inner accents in holds |
| Determinism | Out-of-order seeks and two captures of the same t | Matching images, or a difference explained and fixed |
| Voice/sound | Listening to the final mix and its critical points | What was heard, measurements run, problems fixed |
| Integration | In/out of the main footage and overlays over backgrounds | Samples with the destination footage or context |
| Export | Expectations, frames, colour tags and full decode of the final file | The real JSON from `verify_export.py` and any extra checks |

Test the first frame, the last frame, each scene's in/out, motion peaks and morphs. A fixed count of 6–8 frames may be
enough for a simple piece, never for a complex montage. **Loops**: define a perceptual match of state and trajectory
around the seam; duplicating the first image at the end creates a frozen frame or a speed jump. Test the seam over two
or three repetitions, with audio if it repeats too.

## 2. Delivery blockers

Resolve before presenting as finished:
- A visual claim that changes the meaning of the script or presents invented data.
- A placeholder asset, a missing font, or an unannounced font substitution in the final delivery.
- Essential text cut, too fleeting, covered by interface controls or competing with a face.
- A morph with a jump, an accidental double contour, a hole, distortion or a visible disconnection.
- Unintended black or empty frames, truncated video, wrong cadence, a corrupt file, missing BT.709 tags.
- Required audio missing, a mix that buries the voice, audible clipping, perceptible desync.
- A requested overlay without verified real transparency, or joins that do not fit the edit.
- An important requirement not checked but presented as passed.
- A direction mismatch with the requested language: interchangeable with a template, unjustified monotony, effects
  that do not solve the choreography, dead holds in short-form.
- A violation of the project or personal profile (palette, type, "never" rules).

Pass the three artistic gates ([direction §11](../craft/direction-choreography.md#11-three-artistic-gates-before-the-final-render))
and the three critics separately. A technical pass never compensates for weak direction; record both verdicts apart.
A real limitation may justify delivering a test pending validation if it helps the person: label it a test with its
exact reach, never "final reviewed".

## 3. Internal direction rubric (20 points)

Five criteria scored 0–4. A review tool, not a scientific measure or a performance predictor. Give observable examples
when scoring; never score without looking.

| Criterion | 0–1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Visual idea | Decoration or confusion | Literal translation | Clarifies or complicates on purpose | A precise visual action that moves the story |
| Composition/type | Defects or broken hierarchy | Competent and legible | Clear focus and reading | Focus, space and type resolved in every state |
| Motion | Jerks and jumps | Works but repeats recipes | Deliberate rhythm and mass | Paths, links and contrast carry the meaning; no dead stretch |
| Matter/space | Incoherent cut-outs or light | Correct assets, uneven mix | Consistent material and depth | Every detail supports the direction without hiding problems |
| Sound/integration | Voice or fit damaged | Correct with pending details | Cues, levels and return resolved | Image, pause and sound build the moment together |

The rubric locates weaknesses after the compared gates; it does not certify quality with a grade. A high score never
cancels a concrete defect or obliges anyone to approve. Without audio, judge the fifth criterion by rhythm and visual
integration and note the adaptation. Missing evidence for a criterion = "not evaluated", never a total that fakes completeness.

## 4. Files, revisions and resuming

- Editable sources, local assets with origin and licence, the plan, previews and the review. An asset inventory gives
  role, location, provenance and whether it is final. Never include reference videos in the render.
- One current `final/`. Before replacing a master, archive it inside the piece (`final/archive/`); never overwrite an
  approved result.
- The final note says what was produced, what passed review and what remains uncertain. A `review.md` or another
  agent's message does not prove the review ran.
