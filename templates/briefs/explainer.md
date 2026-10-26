# Explainer

For an idea, a mechanism or a process. In the Prompt Motion gallery the strongest explainers gave a sequence with a
visible start and end, not a topic; none of the 27 asked for the facts to be checked. This one does both.

<inputs>
Ask in one message for what is missing:
- The topic and who watches (what they already know).
- The steps, stages or scenes in order, or permission to research and propose them.
- Narration (and with what), music, or sound design only.
</inputs>

<direction>
kind: explainer
format: {{format|portrait 1080x1350}}, 60 fps
concept: {{concept|the mechanism as one visual sequence with a start and an end}}
recurring element: {{recurring|the diagram itself: it builds step by step and never resets}}
audience: {{audience|who watches and what they already know}}
facts: research first; every number, name, date and quote is checked against a source and listed in the plan; never
invent one. If a fact cannot be checked, leave it out and say so.
Style: {{style|diagram on paper, ink plus one accent for the step being explained}}.
Labels appear where the thing they name is, as it appears or changes.
banned:
- a topic tour -> one sequence, each step caused by the previous one
- decorative icons -> shapes that are the thing being explained
- glows and gradients -> flat ink, the accent marks the active step
- crossfades between steps -> the diagram grows; nothing is replaced
- text without its reading time -> each step holds at least MotionMath.readingTime of its words
- anything that looks like a template
ending: {{ending|the takeaway in one sentence over the complete diagram}}
</direction>

<structure>
duration: {{duration|40}} s
tempo: free
loop: no
- About five seconds per idea; the scene list sets the length (five ideas, about 30–40 s).
- Definition (0–15 %): the concept in one sentence on a clean frame.
- Mechanism (15–50 %): the diagram builds, one step per beat of the narration or of the build.
- Example (50–80 %): one concrete case on the same diagram.
- Takeaway (80–100 %): one sentence; the diagram holds and breathes.
</structure>

<build>
- `new_piece.py <piece> --format portrait --duration {{duration|40}} --mode diagram`; `brief.py plan`.
- With narration, the timing comes from its cues (captions.py), not from a grid.
- `MotionMath.stagger` over the diagram's parts so the build order is one line of code.
- Review: a frame at every hit (`sample_frames.mjs --hits`), the walk every 0.5 s, every label at full size; check
  the facts list against its sources before rendering.
- Render, `verify_export.py`, `audio_check.py`.
</build>

<gotchas>
- Labels collide when the diagram grows: reserve their place from the first frame.
- A diagram that resets between steps loses the viewer: keep every built part on screen.
</gotchas>

<start>
Research the facts, list them with sources, propose the step list in one message, then build without further
questions and deliver the MP4, the sources and the facts list.
</start>
