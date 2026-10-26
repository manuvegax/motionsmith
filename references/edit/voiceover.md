# Voice-over: the voice is the clock

Read for any piece told by a voice: a narrated reel, an explainer, a story with a voice, a video essay. A beat grid
times music pieces; here the voice does. Every scene, cut, accent and caption comes from when words are said, and the
picture's job is to add what the voice does not say.

Tools: `scripts/voice_plan.py` (voice → plan), the `voiceover` cue of `build_soundtrack.py` (the mix),
`templates/recipes/voice-captions` (a runnable piece), `templates/briefs/voiceover.md` (the two-column brief),
`sample_frames.mjs --cuts --scenes --hits` (the review).

## 1. The script in two columns

Write what is heard and what is seen side by side, one phrase per row. The screen column is a decision, not a
caption: it says what changes while the phrase is said.

| voice | screen |
|---|---|
| Your brain does not want you *happy*. | The word HAPPY crosses itself out |
| It wants you to survive, so it keeps you on *alert*. | An eye opens in the centre |

- **Length from words**: about 2.5 words per second (150 a minute) in Spanish or English; `brief.py check` estimates
  it from the table and warns when the duration disagrees.
- **Mark the stressed word** of each phrase with `*asterisks*` (or CAPITALS). A recorded human voice usually stresses
  it already; a synthesized one is flat, and the mark is what puts the accent where the meaning is.
- **The picture adds, it does not repeat.** Showing exactly the noun that is said, line after line, reads as a
  slideshow. Show the consequence, the contrast, the detail the voice skips.
- **The first phrase is the hook** and it starts in the first second; the first frame already moves.

## 2. Recording, synthesis and word timings

| Source | Notes |
|---|---|
| The person's own voice | The strongest for a personal account. A quiet room, the phone close, one take per phrase is fine: voice_plan reads the joined file |
| A synthesized voice (ElevenLabs text-to-speech, or a local voice for drafts) | Ask before spending credits. Flat stress: mark the stressed words |
| Word timings | Speech-to-text with word timestamps on the **exact file**: ElevenLabs speech-to-text JSON, Whisper (`word_timestamps`), WebVTT with inline times. SRT works but its word times are estimated |
| No timings at all | `--script` alone: the text is spread over the voice's pauses. Good for cuts, too loose for word-by-word captions |

`voice_plan.py` stops when the timings run past the end of the audio (another take, another sample rate) and warns
when the word onsets do not fall where the voice is audible. Word ends are tightened to where each word stops
sounding, so the pauses come back even when a speech-to-text pads them.

## 3. What voice_plan decides, and why

```bash
python -I <skill>/scripts/voice_plan.py --plan <piece>/plan.json --voice <piece>/assets/voice.wav \
    --words <piece>/assets/voice-words.json --script <piece>/brief.md --brief <piece>/brief.md
```

| Decision | Rule | Override |
|---|---|---|
| Scenes | One per phrase: a full stop (taken from the script when the speech-to-text drops it) or a pause of 0.45 s ends it | `--long-pause` |
| Long phrases | Split only at a comma, a dash or a real pause, near the middle, when longer than 3.5 s; never inside a clause | `--max-scene` |
| Short phrases | Under 0.8 s they join the next | `--min-scene` |
| Cuts | Two frames before the phrase's first word: the eye leads the ear, so the new picture is there when the word arrives | `--lead-frames` |
| Accent | One per phrase, at least 1 s apart. It starts on the last content word (where a neutral sentence puts its main stress); a louder or longer word, or one before a pause, can take it; a marked word always wins | `*asterisks*` in the script |
| Captions | One phrase at a time, even lines, never ending on a weak word (de, que, y, the…), no lone short word; up to 22 characters per second, because the ear carries the pace | `--preset` |
| Duration | From the first word to the last, plus a tail (0.8 s) | `--voice-start`, `--tail` |
| Scene actions | From the brief's screen column, matched to the words spoken | `--brief` |

It writes `plan.json` (scenes, cuts, emphasis hits, captions, `voice`), `voice.json` (every word, phrase and pause
with its time in the piece, for `piece.js`), `captions.json` and the `voiceover` cue in `cues.json`. Read its emphasis
list against the script before building: it measures level and timing, it does not hear meaning.

## 4. Cutting on a voice

- **Cut in the breath, lead with the picture.** A cut that lands inside a word feels like a stumble; one or two
  frames before the word, the picture seems to answer the voice.
- **One picture per phrase is the floor, not the ceiling.** Inside a long phrase, move the camera, reveal a second
  layer, or change the scale on the comma ([pacing](pacing-retention.md)).
- **J and L cuts**: let the next phrase start over the last image (J) when the thought continues; hold the image after
  the voice ends (L) when it needs to sink in ([cutting](cutting.md)).
- **Silence is a beat.** A pause before the payoff is the voice-over's vacuum: let the picture hold its breath too.
- **Talking heads are not this**: footage of a face with captions goes to HyperFrames or an editor; Motionsmith makes
  the titles and inserts that go over it ([HyperFrames](../produce/hyperframes.md)).

## 5. The mix

```json
{"voice": "voiceover", "file": "assets/voice.wav", "time": 0.1, "gain_db": 0, "duck_db": -15}
```

- The voice goes in dry, on top. Everything else (synthesized bed, effects, a music cue) ducks under its own envelope:
  the duck follows the words, so the pauses breathe.
- **10 dB or more** between the voice and the rest while it speaks: `build_soundtrack.py` reports
  `voice_over_bed_db` and warns below 10. Lower the bed, or deepen `duck_db`.
- The whole mix masters to −16 LUFS integrated and ≤ −2 dBTP on the WAV (the MP4's AAC stays under −1).
- Accents under a voice are a soft `tap` (hits whose role starts with `emphasis`): an impact on a stressed syllable
  covers the syllable. Keep impacts for the pauses and the cuts between phrases.
- Low drones and sub hits vanish on a phone and fight the voice's chest; high-pass the bed if the voice gets muddy.

## 6. Delivery weight

A voice-led piece runs 20–90 s, and grain at the default CRF 14 makes it huge: a 19 s test came out at 73 Mbit/s
(170 MB) and at 1.8 Mbit/s with `--crf 20`, which looks the same on a phone after the platform re-encodes it.
`render_stream.mjs` reports `video_mbps` and warns above 40. Keep CRF 14 for a master you will edit again; upload a
CRF 18–20 render. Render at 30 fps: a voice does not need 60, and it halves the render time.

## 7. Review per phrase

```bash
node <skill>/scripts/sample_frames.mjs --root <piece> --out <tmp>/cuts --cuts --noblur    # both sides of every cut
node <skill>/scripts/sample_frames.mjs --root <piece> --out <tmp>/hits --hits --beat-offset 0.1   # every stressed word
node <skill>/scripts/sample_frames.mjs --root <piece> --out <tmp>/scenes --scenes          # one frame per phrase
```

Look for: a word on screen before it is said, a cut in the middle of a word, a caption line ending on «de» or «the»,
a stressed word in the wrong place, a phrase that sits on one still picture. Then listen on a phone with the screen
off: the voice must be clear without the picture.

## Sources

Speech rate and caption speed: broadcast subtitle practice (about 17 characters per second for unheard subtitles) and
the 150-words-a-minute rule of thumb for narration; nuclear stress on the last content word of a neutral phrase is the
standard description of Spanish and English intonation. The rules for cutting on a voice follow Walter Murch, *In the
Blink of an Eye* (cut on the blink, emotion first), applied to narration.
