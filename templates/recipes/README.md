# Scene recipes

Runnable starting points built on `kit/stage.js`, `kit/timeline.js` and `kit/kinetic-type.js`. Each one
renders in every format (`--format reel|story|portrait|square|landscape`), is deterministic, and reads its key
times from the `hits` of `plan.json`, so the soundtrack and the picture stay together when you retime.

```bash
python -I <skill>/scripts/new_piece.py work/my-piece --recipe kinetic-quote --title "the mind is *ready* for"
python -I <skill>/scripts/new_piece.py --list-recipes
```

| Recipe | What it does | Look | Default length | Hits |
|---|---|---|---|---|
| [audiogram](audiogram/README.md) | Audiogram: a waveform that scrolls with the voice's level, speaker and show on a card, the phrase karaoke-style | Podcast card | 10 s (the voice sets it) | `emphasis: <word>` |
| [chart-bars](chart-bars/README.md) | Chart bars: horizontal bars grow from zero, values counting; the highlight lands last in the accent; the source stays on screen | Editorial data | 6 s | `first bar`, `highlight`, `exit` |
| [data-reveal](data-reveal/README.md) | Data reveal: a number rolls up on odometer wheels while a teal gauge fills; it lands on its hit and the hold breathes | Infographic | 5 s | `count starts`, `value lands`, `exit` |
| [editorial-collage](editorial-collage/README.md) | Editorial collage: a monumental figure behind a mixed-weight phrase, a zoom through the red keyword into a macro page with a marker, a whip to a ribbon and a pinned card, a cut to black with a phone | Editorial collage | 12 s | `phrase`, `zoom`, `marker`, `whip`, `card`, `black`, `end` |
| [kinetic-quote](kinetic-quote/README.md) | Kinetic quote: words cascade in while cycling type faces; the keyword lands last, twice the size, on its own hit | Typographic poster | 6 s | `first word`, `keyword lands`, `exit` |
| [logo-reveal](logo-reveal/README.md) | Logo reveal: pieces of a mark fly in on arcs, lock on one hit and settle; a glint crosses it and returns; the wordmark tracks in | Minimal glow | 4 s | `mark locks`, `glint`, `wordmark` |
| [lower-third](lower-third/README.md) | Lower third: an accent bar grows, name and role panels wipe out from behind it, a progress line fills while it holds, then it wipes back | Clean broadcast | 5 s | `bar in`, `name in`, `out` |
| [promo-sequence](promo-sequence/README.md) | Promo sequence: a hook word slams in, a whip pan with real motion blur cuts to a statement, an iris opens the end card | Bold editorial | 8 s | `hook slam`, `whip`, `statement`, `iris`, `end card` |
| [ranking](ranking/README.md) | Ranking: a top N counting down, numbers slam in as outlines that fill, a vertical whip with real blur between places, number one in the accent | Bold editorial | 10 s | `first place`, `number one`, `exit` |
| [split-compare](split-compare/README.md) | Split compare: a divider whips from BEFORE to AFTER under a headline band, springs to the middle, holds alive and ends on AFTER | Duotone | 6 s | `whip`, `settle`, `labels`, `exit` |
| [broll-story](broll-story/README.md) | B-roll story: clips and photos as prints that stack on paper under a voice, one grade; the phrase in mixed weights, the stressed word in red with a stroke | Editorial collage | 8 s (the voice sets it) | `emphasis: <word>` |
| [voice-captions](voice-captions/README.md) | Voice captions: each spoken phrase is a scene; words land as they are said, the stressed word in the accent; every cut swaps paper and ink | Bold editorial | 8 s (the voice sets it) | `emphasis: <word>` (written by voice_plan.py; a demo one before) |
| [step-diagram](step-diagram/README.md) | Step diagram: a process builds step by step and never resets; a loop closes into a circle; ends on the takeaway | Diagram on paper | 9 s | `first step`, `takeaway`, `exit` |
| [title-card](title-card/README.md) | Swiss title card: a grid draws, a rule and a typed eyebrow, the title rises line by line from masks, a marker hops while it holds | Swiss / International | 4 s | `rule`, `eyebrow`, `title`, `exit` |

Write a new recipe by copying one: `piece.js` (with the `const TITLE = 'TITLE';` line), `recipe.json` and
`README.md`; a data-driven recipe adds `"data": "data.json"` to recipe.json and ships a sample `data.json`, which
`new_piece.py` copies and links as `plan.data`. A recipe hit has `time` (seconds from the start) or `from_end` (seconds before the end).
`tests/test_recipes.py` picks it up on its own.
