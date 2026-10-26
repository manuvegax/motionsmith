# Vertical reel with a hook (kinetic type, 9:16)

A short-form piece for Reels, TikTok or Shorts: one phrase or idea, the first frame already moving, a payoff that
earns a rewatch. Fill it with `python -I <skill>/scripts/brief.py new <piece>/brief.md --template reel-hook --set
name=value`, then `brief.py check`. Every placeholder with a default is a decision; change the defaults that do not fit.

<inputs>
Before building, ask in one message (at most three groups) only for what is missing:
- The exact on-screen copy, word for word: {{copy|the phrase the piece is built on}}.
- Brand palette and type, or permission to use the profile's (MOTIONSMITH.md).
- Sound: sound design only, a music bed (file and licence), or silent.
Keep earlier answers; never ask twice.
</inputs>

<direction>
kind: reel
format: reel 1080x1920, 60 fps, safe area from new_piece.py
concept: {{concept|one line: what the viewer discovers and what is true at the end}}
recurring element: {{recurring|one shape, word or line that carries every transition}}
audience: {{audience|who scrolls past this and why they would stop}}
Type: {{type|one display face with a variable axis (Archivo from the font kit) plus one italic serif for the second voice}}.
Palette: {{palette|paper, ink and one accent; the accent marks only the payoff}}.
Motion: entrances ease out, exits ease in and shorter, the hero on a spring with a small overshoot; real motion blur
on fast moves, sharp on every reading frame.
Camera: one family for the whole piece ({{camera|push-ins and whip pans}}), always motivated.
Matter: grain and print texture over the type; nothing reads as flat vector.
banned:
- holds over 0.5 s where nothing changes -> a reading hold keeps the text still and moves what surrounds it
- crossfades -> every scene grows out of the previous one through the recurring element
- glows with no source -> light only where something on screen emits it
- particle bursts -> motion starts from or ends in an element already on screen
- bouncy easing on everything -> overshoot only on the hero landing
- corner labels and HUD text -> text only when it says something
- anything that looks like a template -> if a default appears, replace it with a decision
ending: {{ending|the payoff line held sharp, the accent on its key word}}
</direction>

<structure>
duration: {{duration|12}} s
tempo: {{bpm|100}} BPM
meter: 4/4
loop: {{loop|no}}
- Bar 1 is the hook: the first frame already moves and the key word lands on beat 1.
- Each following bar does one thing that flows from the last; something changes on every beat (an accent inside the
  reading holds: a weight jump, an echo, an inversion, a sweep).
- The payoff lands on the downbeat of the last full bar and is the strongest moment.
- The tail holds the payoff long enough to read it twice.
</structure>

<build>
- `new_piece.py <piece> --format reel --duration {{duration|12}}` (or `--recipe kinetic-quote`), then `brief.py plan`
  to copy these decisions and the bar hits into plan.json; rename each hit's role to what it does on screen.
- piece.js writes `setup`, `state(t)` and `draw`; everything is a function of t, seeded, no clocks or Math.random.
- Text fits the safe area with `Stage.fitLines`; reading budgets from `MotionMath.readingTime`.
- Sound from the same hits (`build_soundtrack.py`); every visual event has its sound.
- Review before the full render: one frame per beat (`sample_frames.mjs --beats`), a walk every 0.5 s for stillness,
  dense windows on every cut, then the three critics. Fix what is off-grid, cramped or hard to read.
- Render with `render_stream.mjs`, verify with `verify_export.py --require-cfr --require-bt709` and `audio_check.py`.
</build>

<gotchas>
- Text scaled by the camera blurs if it is drawn small and enlarged: draw it at its largest size and scale down.
- Two lines swapping in one place overlap: give the outgoing line its exit before the next one enters.
- The interface covers the right column and the bottom: keep everything that must be read inside the safe area.
- If loop is yes, the last frame leads into the first in pose and speed (`loop_check.py`).
</gotchas>

<start>
Name the concept in one line, show the beat grid (`brief.py grid`) and the storyboard as states, one line per bar.
Then build without further questions, run the review and deliver the MP4, the sources and what only the person can
judge on their phone.
</start>
