# Step diagram (education, psychology, processes)

A process builds one step at a time and never resets: an arrow draws from the previous node, the new node lands in
the accent with its number and label, and its explanation sits in the lower band for its reading time; then it
settles into ink. With `"loop": true` the steps sit on a circle and the last arrow closes back to the first. The
diagram ends complete, under the takeaway.

## Make it yours

```bash
python -I <skill>/scripts/new_piece.py work/loop --recipe step-diagram --format reel --duration 10
# edit work/loop/data.json: title, loop, takeaway, steps (label + note)
```

## Hits

`first step`, `takeaway`, `exit`; the steps in between spread evenly.

## Craft note

A sequence, not a topic ([story structures §9](../../../references/edit/story-structures.md)): each step is caused by
the one before, the accent marks only the step being explained, and the facts in the notes are checked.

## Check before showing

One frame per step (`sample_frames.mjs --times`), the longest note at full size, and that labels do not touch arrows.
