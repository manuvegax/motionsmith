# Seamless loop

A piece the viewer watches again without seeing the seam: a background, a mood piece, an animated cover, a title
that breathes. The period comes first; every beat is a fraction of it.

<inputs>
None required. Optional: the palette, the text if any, and where the loop will play.
</inputs>

<direction>
kind: loop
format: {{format|square 1080x1080}}, 60 fps
concept: {{concept|one transformation that returns to its start: what changes and how it comes back}}
recurring element: {{recurring|the shape that transforms and returns}}
Palette: {{palette|two inks and one accent}}.
Motion: periodic functions of t (MotionMath.loop, loopValue); every moving part has a period that divides the loop.
banned:
- a seam where pose matches but speed breaks -> match pose and velocity at t = 0 and t = period
- the first frame repeated as the last -> sample t in [0, period), never period itself
- random flicker -> seeded noise looped over the period
- glows with no source -> light only where something emits it
- crossfading the end into the start -> the motion itself returns
- anything that looks like a template
ending: the last frame leads into the first
</direction>

<structure>
duration: {{duration|8}} s
tempo: {{bpm|120}} BPM
meter: 4/4
loop: yes
- The period is the duration: {{duration|8}} s, a whole number of bars at the tempo.
- One accent per bar; the strongest on the last downbeat before the seam.
</structure>

<build>
- `new_piece.py <piece> --format square --duration {{duration|8}}`; `brief.py plan`.
- Every value from `MotionMath.loopValue` or a sine of `2πt / period`; noise seeded and looped.
- Review: one frame per bar (`sample_frames.mjs --bars`) and the frames just before and after the seam.
- Render, `verify_export.py`, then `loop_check.py final/<piece>.mp4`: seam ratio near 1, speed ratio near 1.
</build>

<gotchas>
- A period that does not divide the duration leaves a jump at the seam.
- Motion blur at the seam needs the sub-frames of the last frame to wrap into the first period.
</gotchas>

<start>
Name the transformation in one line, show the period and its bars, then build and deliver the MP4 with the
loop_check report.
</start>
