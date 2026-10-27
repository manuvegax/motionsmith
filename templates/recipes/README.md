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
| [data-reveal](data-reveal/README.md) | Data reveal: a number rolls up on odometer wheels while a teal gauge fills; it lands on its hit and the hold breathes | Infographic | 5 s | `count starts`, `value lands`, `exit` |
| [kinetic-quote](kinetic-quote/README.md) | Kinetic quote: words cascade in while cycling type faces; the keyword lands last, twice the size, on its own hit | Typographic poster | 6 s | `first word`, `keyword lands`, `exit` |
| [logo-reveal](logo-reveal/README.md) | Logo reveal: pieces of a mark fly in on arcs, lock on one hit and settle; a glint crosses it and returns; the wordmark tracks in | Minimal glow | 4 s | `mark locks`, `glint`, `wordmark` |
| [lower-third](lower-third/README.md) | Lower third: an accent bar grows, name and role panels wipe out from behind it, a progress line fills while it holds, then it wipes back | Clean broadcast | 5 s | `bar in`, `name in`, `out` |
| [promo-sequence](promo-sequence/README.md) | Promo sequence: a hook word slams in, a whip pan with real motion blur cuts to a statement, an iris opens the end card | Bold editorial | 8 s | `hook slam`, `whip`, `statement`, `iris`, `end card` |
| [split-compare](split-compare/README.md) | Split compare: a divider whips from BEFORE to AFTER under a headline band, springs to the middle, holds alive and ends on AFTER | Duotone | 6 s | `whip`, `settle`, `labels`, `exit` |
| [broll-story](broll-story/README.md) | B-roll story: clips and photos under a voice, one grade, Ken Burns and parallax in code; the phrase in the lower third, the stressed word in an accent box | Documentary | 8 s (the voice sets it) | `emphasis: <word>` |
| [voice-captions](voice-captions/README.md) | Voice captions: each spoken phrase is a scene; words land as they are said, the stressed word in the accent; every cut swaps paper and ink | Bold editorial | 8 s (the voice sets it) | `emphasis: <word>` (written by voice_plan.py; a demo one before) |
| [title-card](title-card/README.md) | Swiss title card: a grid draws, a rule and a typed eyebrow, the title rises line by line from masks, a marker hops while it holds | Swiss / International | 4 s | `rule`, `eyebrow`, `title`, `exit` |

Write a new recipe by copying one: `piece.js` (with the `const TITLE = 'TITLE';` line), `recipe.json` and
`README.md`. A recipe hit has `time` (seconds from the start) or `from_end` (seconds before the end).
`tests/test_recipes.py` picks it up on its own.
