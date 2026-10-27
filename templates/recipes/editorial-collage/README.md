# Editorial collage

The documentary motion-graphics language of After Effects, in one 12 s piece. Paper with matter and a monumental
figure out of focus behind a phrase of mixed weights (the keyword in red); a zoom through the red keyword into a macro
shot of a printed page, depth of field, a marker sweeping the one line that matters, the camera pulling back to the
headline; a whip pan with real motion blur to a ribbon drawing on and a pinned card dropping with its list; a cut to
black where a phone rises, notifications stack and switch off, and the closing line glows red.

## Make it yours

```bash
python -I <skill>/scripts/new_piece.py work/collage --recipe editorial-collage --format reel --fps 30
# edit work/collage/data.json: numeral, phrase, document {kicker, headline, highlight}, card, notifications, ending
```

Phrase markup: `|` breaks a line, `*word*` or `*several words*` is the keyword, `~word` is small.

## Hits

`phrase`, `zoom`, `marker`, `whip`, `card`, `black`, `end`. A `cues.json` with `role_voices` gives each its sound
(slap, boom, tap, hit, glass) plus a riser into the zoom and a whoosh on the whip.

## Craft note

Matter, depth and carriers ([editorial collage](../../../references/create/editorial-collage.md)): the figure is out
of focus so the phrase reads first; the keyword's red becomes the red that opens the page; the whip carries the
energy; the hit cuts to black. One hero per moment.

## Check before showing

A frame per scene, a full-size crop of the macro page (smooth depth of field, the marker on its line), and a dense
window on the zoom and the whip.
