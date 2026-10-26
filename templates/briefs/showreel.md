# Motion showreel (15 s, 120 BPM)

The most-copied prompt in the Prompt Motion gallery asks for a "dynamic 15-second showreel" in one line and leaves
every decision open; its results scatter. This version decides the concept, the range, the grid and the bans, and
runs on Motionsmith's engine. Needs no input: change the defaults that do not fit.

<inputs>
None required. Optional: a palette or typeface to use, a format other than {{format|landscape 1920x1080}}.
</inputs>

<direction>
kind: showreel
format: {{format|landscape 1920x1080}}, 60 fps
concept: {{concept|pick one concept and name it in one line before starting; every shot serves it}}
recurring element: {{recurring|one shape that every shot transforms out of the previous one}}
Every shot transforms out of the previous one: no cuts, no fades.
Type: {{type|one typeface: Archivo from the font kit, its weight and width animated}}.
Palette: at most three colours plus black and white.
Camera: one camera language for the whole piece.
Range, each with an equal share of the time: kinetic type, shape morphing, a 2D-to-3D moment (parallax or a
perspective turn), a data or interface moment, and an end title.
banned:
- particle bursts -> motion that starts from an element on screen
- glows and lens flares -> light only where something emits it
- camera shake -> a motivated push or whip
- RGB split -> misregistered print (Stage.looks.print) if a glitch is needed
- crossfades -> morphs through the recurring element
- generic gradients -> flat fields with grain
- bouncy easing -> springs with a tiny overshoot on the hero only
- holds longer than 0.5 s -> an inner change at least every beat
- anything that looks like a template
ending: the end title on the last half bar; its last frame matches the first so the reel loops
</direction>

<structure>
duration: 15 s
tempo: 120 BPM
meter: 4/4
bars: 7.5
loop: yes
- An action on every beat (0.5 s).
- Bar 1 is the hook. Bars 2–6 each carry one technique of the range, flowing out of the last.
- Bar 7 is the strongest moment.
- The last half bar is the end title; its final frame leads into the first.
</structure>

<build>
- `new_piece.py <piece> --format landscape --duration 15`, `brief.py plan --hits beat` for a hit on every beat.
- Springs and exponential eases as functions of t (`MotionMath`); real sub-frame motion blur from tracked points
  (`stage.js`), sharp on reading frames.
- Sound from the hits (`build_soundtrack.py`): a kick on every beat, a riser into bar 7, a hit on each scene change.
- Review: one frame per beat (`sample_frames.mjs --beats`) before the full render; fix anything cluttered, off-beat,
  overlapping or hard to read. Then the three critics.
- Render with `render_stream.mjs`, `verify_export.py`, `audio_check.py --plan`, and `loop_check.py` on the MP4.
</build>

<gotchas>
- Equal time per technique and one technique per bar collide at 7.5 bars: five techniques take bars 2–6, the hook and
  the strongest moment take bars 1 and 7, the title takes the half bar. Say so in the plan.
- Morphs jump when point correspondence is missing; never hide a jump with a flash.
- The loop needs pose and speed to match at the seam.
</gotchas>

<start>
Name the concept in one line, show the beat-by-beat storyboard (`brief.py grid --bpm 120 --duration 15`), then build
without asking further questions and deliver the MP4.
</start>
