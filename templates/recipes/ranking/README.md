# Ranking (top N, lists)

A top N that counts down. Each number slams in huge, first as an outline that fills as it lands; the label rises
under it and a short note follows; a vertical whip with real motion blur carries the eye to the next place. Number
one lands in the accent and holds longer. Dots on the side show how many places are left.

## Make it yours

```bash
python -I <skill>/scripts/new_piece.py work/top --recipe ranking --format reel --duration 10
# edit work/top/data.json: title and items from the last place to number one
```

## Hits

`first place`, `number one`, `exit`; the places in between spread evenly.

## Craft note

The countdown is an open loop ([pacing §8](../../../references/edit/pacing-retention.md)): show what is left, put
the strongest item last and a surprising one first. About 1.5–2 s per place; number one gets 2.5 s.

## Check before showing

`sample_frames.mjs --hits` and a dense window on one whip: the number is sharp when it lands, blurred only in the whip.
