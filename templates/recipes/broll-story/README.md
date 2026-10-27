# B-roll story

Footage and photos under a voice. The background is the B-roll timeline from `broll.py assemble`: clips trimmed to
their scenes, stills that push, pan or tilt in code (Ken Burns, sub-pixel smooth, real motion blur) with parallax when
a cut-out is given, and one grade for every source. The phrase being said sits in the lower third: words land as they
are spoken, the stressed one gets a red box, and a gradient and a soft shadow keep it legible on any picture.

## Make it yours

```bash
python -I <skill>/scripts/new_piece.py work/doc --recipe broll-story --format reel --fps 30
python -I <skill>/scripts/broll.py ingest clip.mp4 photo.jpg --piece work/doc --source "https://…" --license cc0
python -I <skill>/scripts/voice_plan.py --plan work/doc/plan.json --voice work/doc/assets/voice.wav --words words.json --script script.md
python -I <skill>/scripts/broll.py shotlist --piece work/doc      # then set "file" for each shot in assets/broll/shots.json
python -I <skill>/scripts/broll.py assemble --piece work/doc
python -I <skill>/scripts/build_soundtrack.py --plan work/doc/plan.json --cues work/doc/cues.json --out work/doc/assets/soundtrack.wav
node <skill>/scripts/render_parallel.mjs --root work/doc --out final/doc.mp4 --workers 3 --crf 20
python -I <skill>/scripts/broll.py credits --piece work/doc       # attribution for the caption
```

## Hits

`emphasis: <word>` from `voice_plan.py`.

## Craft note

Video carries its own blur, so every sub-sample of a frame draws the same footage frame; stills move in code. Grade
everything the same (assets/broll/timeline.json → grade) and let the picture add what the voice does not say.

## Check before showing

`sample_frames.mjs --cuts` on both sides of every cut, a full-size crop of the brightest shot under the captions,
and `broll.py credits`: CC BY material needs its credit in the caption.
