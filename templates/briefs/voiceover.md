# Voice-over piece (the voice is the clock)

A reel, explainer or story told by a voice: recorded, or synthesized. The script is written in two columns, what is
heard and what is seen, so every phrase arrives with its picture. The voice sets every time: scenes, cuts, accents
and captions come from it (`voice_plan.py`), not from a beat grid.

<inputs>
Ask in one message for what is missing:
- The script, or the idea to write it from; who records it (their own voice, a synthesized voice and which one).
- The visual world: code-drawn type and shapes, photos or footage they hand over (with licence), or both.
- Music bed (file and licence) or sound design only.
</inputs>

<direction>
kind: voiceover
format: {{format|reel 1080x1920}}, 30 fps (a voice-led piece does not need 60)
concept: {{concept|one line: what the viewer understands at the end that they did not at the start}}
recurring element: {{recurring|the stressed word of each phrase, always in the accent, always underlined as it is said}}
audience: {{audience|who listens and what they already know}}
Picture: every phrase changes the picture (a cut, a swap of ground, a camera move); the stressed word lands on screen
the moment it is said; captions follow the voice word by word.
Sound: the voice on top, dry; the bed and effects duck under it (10 dB or more under the voice); accents are soft taps
that never cover a word.
banned:
- a picture that illustrates the word literally on every line -> a picture that adds what the voice does not say
- text that arrives before it is said -> words land on their own onset
- impacts on stressed syllables -> a soft tap, or silence, so the word stays clear
- music over the voice -> the bed ducks under every phrase
- one picture held under a long phrase -> split the phrase at its comma, or move the camera
- anything that looks like a template
ending: {{ending|the last phrase alone on a clean frame, held for two beats of silence}}
</direction>

<structure>
duration: {{duration|10}} s
tempo: voice
loop: no

| voice | screen |
|---|---|
| {{line1|First phrase: the hook, said in the first second.}} | {{screen1|What the viewer sees while it is said}} |
| {{line2|Second phrase: the turn, with its *stressed* word marked.}} | {{screen2|The picture that changes with it}} |
| {{line3|Third phrase: the payoff.}} | {{screen3|The last image, held}} |

About 2.5 words per second in Spanish or English; a pause is a breath for the picture.
</structure>

<build>
- `new_piece.py <piece> --recipe voice-captions --format reel --fps 30` (or the starter for your own picture).
- Voice in `assets/`; word timings from speech-to-text (ElevenLabs speech-to-text, Whisper) into `assets/voice-words.json`.
- `voice_plan.py --plan plan.json --voice assets/voice.wav --words assets/voice-words.json --script brief.md --brief brief.md`:
  scenes per phrase, cuts in the pauses, one accent per phrase, captions, the voiceover cue.
- Read its emphasis list against the script; mark the words it missed with *asterisks* and run it again.
- `build_soundtrack.py --plan plan.json --cues cues.json` (voice on top, everything else ducked).
- Review per phrase: `sample_frames.mjs --cuts` (both sides of every cut) and `--hits` (every stressed word); then the
  three critics. Render at 30 fps, `verify_export.py`, `audio_check.py`.
</build>

<gotchas>
- Word timings from another take or another sample rate drift: export them from the exact file (voice_plan stops when
  they run past the audio).
- A synthesized voice is flat: the accent falls on the last content word of each phrase unless the script marks it.
- Captions that follow a voice can read faster than subtitles (the ear carries the pace), but not faster than 22
  characters per second.
</gotchas>

<start>
Show the two-column script with its stressed words and the estimated length (`brief.py check`), then record or
synthesize, run voice_plan and build without further questions.
</start>
