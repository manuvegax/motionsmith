# Product or launch film

For a product, an app, a service or an event. The strongest launch prompts in the Prompt Motion gallery say what to
show and how: the promise, three to five concrete moments, the look in hex, a tempo, an avoid list and the ending.

<inputs>
Ask in one message for what is missing:
- Product name and what it does for the user, in one line.
- Three to five real moments to show, in order (screens, actions, objects), and the assets for them.
- Brand colours as hex, one font, light or dark; a royalty-free track near the tempo below, or sound design only.
</inputs>

<direction>
kind: launch
format: {{format|reel 1080x1920}}, 60 fps
concept: {{concept|the product as the subject, not the backdrop: one line on what changes for the user}}
recurring element: {{recurring|the product's own shape or interface element that carries every transition}}
Promise: {{promise|Product: what it does for the user}}.
Moments, in order: {{moments|1. the problem in one frame; 2. the first action; 3. the result; 4. the proof}}.
Look: {{palette|brand hex colours}}, one font ({{type|Archivo}}), {{mode|light}} mode.
Camera: zoom so each moment fills the frame; one camera language.
banned:
- glows -> light only where the interface emits it
- particle bursts -> motion that starts from the product
- crossfades -> each moment grows out of the last one through the recurring element
- stock-looking icons and UI kits -> the product's real screens or code-drawn shapes in its style
- corner labels -> text only when it says something
- dead time -> something happens on every beat
- anything that looks like a template
ending: {{ending|the logo and one line of copy, sharp, on the last downbeat}}
</direction>

<structure>
duration: {{duration|16}} s
tempo: {{bpm|120}} BPM
meter: 4/4
loop: {{loop|no}}
- Bar 1: the hook, the promise or the problem, already moving on frame one.
- One moment per bar or two, in the order above; something happens on every beat.
- The strongest moment on the last full bar; the ending holds long enough to read the line twice.
</structure>

<build>
- `new_piece.py <piece> --format reel --duration {{duration|16}}` or `--recipe promo-sequence`; `brief.py plan`.
- Real assets only (screenshots, logos, the product's palette); text swapping inside a container gets its own exit
  before the next enters.
- Sound effects on the measured peaks of the track (`audio_envelope.py` suggests them); the beat grid starts on the
  track's downbeat (`lead` in the plan).
- Review: one frame per beat (`sample_frames.mjs --beats`), dense windows on every morph, the three critics.
- Render, `verify_export.py`, `audio_check.py --plan`.
</build>

<gotchas>
- `will-change`-style caching or drawing text small and scaling it up blurs the type: draw at the largest size.
- A screen that fills the frame needs a source big enough for the zoom: check the asset at full size.
- Without the track's downbeat, the cuts drift off the music: measure it before writing the hits.
</gotchas>

<start>
Ask for the inputs above, then name the concept, show the moment list on the beat grid, build without further
questions and deliver the MP4 and the sources.
</start>
