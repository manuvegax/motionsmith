# Chart bars (data, finance)

Horizontal bars grow from a zero baseline one after another while their values count up; the highlighted bar lands
last, in the accent, on its own hit, and the others step back. The source stays on screen. While it holds, a sheen
crosses the highlighted bar and the grid drifts.

## Make it yours

```bash
python -I <skill>/scripts/new_piece.py work/chart --recipe chart-bars --format reel
# edit work/chart/data.json: title, unit, decimals, source, highlight, bars (up to eight)
```

## Hits

`first bar`, `highlight`, `exit`. The other bars spread between the first and the highlight.

## Craft note

One comparison per chart; the highlight is the payoff. Bars start at zero and stay proportional; counts never
overshoot; no 3D. A number without its source is an opinion: the source line is part of the design.

## Check before showing

The highlighted bar's value at full size, the source at 720 px wide, and that the longest label fits.
