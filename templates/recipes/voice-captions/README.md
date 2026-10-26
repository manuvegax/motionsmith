# Voice captions

The voice is the clock. Each spoken phrase becomes a scene: its words land the moment they are said, rising from a
thin to a black weight; the stressed word lands in the accent with a pop and an underline sweep; on every cut paper
and ink swap and the camera punches in. A giant outline of the stressed word slides behind, so nothing is frozen
while someone speaks.

## Make it yours

```bash
python -I <skill>/scripts/new_piece.py work/vo --recipe voice-captions --format reel --duration 20
# put the voice in work/vo/assets/voice.wav and its word timings next to it (speech-to-text JSON, VTT or SRT)
python -I <skill>/scripts/voice_plan.py --plan work/vo/plan.json --voice work/vo/assets/voice.wav \
    --words work/vo/assets/voice-words.json --script work/vo/script.md --brief work/vo/brief.md
python -I <skill>/scripts/build_soundtrack.py --plan work/vo/plan.json --cues work/vo/cues.json --out work/vo/assets/soundtrack.wav
node <skill>/scripts/render_stream.mjs --root work/vo --out final/vo.mp4 --audio assets/soundtrack.wav
```

`voice_plan.py` sets the duration from the voice and writes `voice.json` (words, phrases, emphasis), `captions.json`,
the cuts and the emphasis hits in `plan.json`, and the `voiceover` cue in `cues.json`. Mark stressed words in the
script with `*asterisks*`. Colours: `PAPER`, `INK`, `ACCENT` at the top of `piece.js`.

## Hits

`emphasis: <word>`, one per phrase, written by `voice_plan.py`. Their sound is a soft `tap` that never covers the word.

## Craft note

Cuts sit two frames before each phrase (the eye leads the ear). One accent per phrase, at least a second apart. Long
phrases are split by `voice_plan.py` only at a comma or a real pause.

## Check before showing

`sample_frames.mjs --cuts` (both sides of every cut) and `--hits` (every stressed word), then listen: the voice must
sit 10 dB or more over the rest (`build_soundtrack.py` warns otherwise).
