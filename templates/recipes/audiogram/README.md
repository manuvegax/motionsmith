# Audiogram (podcast, yapping, voice notes)

A waveform scrolls with the real level of the voice; the speaker and the show sit on a card with a live dot that
pulses with it; the phrase being said fills the middle karaoke-style (said words in full colour, coming words at a
third, the stressed word in red); a progress line runs along the bottom.

## Make it yours

```bash
python -I <skill>/scripts/new_piece.py work/pod --recipe audiogram --format reel --fps 30 --title "Manu Vega | Capítulo cero"
python -I <skill>/scripts/voice_plan.py --plan work/pod/plan.json --voice work/pod/assets/clip.wav --words words.json --script script.md
python -I <skill>/scripts/build_soundtrack.py --plan work/pod/plan.json --cues work/pod/cues.json --out work/pod/assets/soundtrack.wav
node <skill>/scripts/render_parallel.mjs --root work/pod --out final/pod.mp4 --workers 3 --crf 20
```

## Hits

`emphasis: <word>` from `voice_plan.py`.

## Craft note

Everything that moves comes from the voice, so the frame rests when the person pauses. Cut the clip to its best
30–60 s: a podcast moment that stands alone (a claim, a story turn, a confession) beats a summary.

## Check before showing

`sample_frames.mjs --scenes` (one frame per phrase): the phrase fits, the stressed word is the right one.
