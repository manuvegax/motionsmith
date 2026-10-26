# Brief templates

Motion briefs in six tagged blocks (`<inputs>`, `<direction>`, `<structure>`, `<build>`, `<gotchas>`, `<start>`), one
per kind of piece. Each is also a prompt that runs as is in any agent with Motionsmith installed. How and why:
[the motion brief](../../references/create/motion-brief.md).

| Template | For | Default length and grid |
|---|---|---|
| `reel-hook` | Vertical reel, TikTok or Short built on one phrase: hook on frame one, an inner change every beat, a payoff | 12 s, 100 BPM, 5 bars |
| `showreel` | A motion showreel that proves range: one concept, five techniques, every shot transforms out of the last, loops | 15 s, 120 BPM, 7.5 bars |
| `launch` | A product, app, service or event: the promise, three to five moments, brand hex, the ending | 16 s, 120 BPM, 8 bars |
| `explainer` | A mechanism or process: a sequence with a start and an end, audience, checked facts | 40 s, timed by the voice or the build |
| `loop` | A seamless loop: background, cover, mood piece | 8 s, 120 BPM, 4 bars |

```bash
python -I <skill>/scripts/brief.py list
python -I <skill>/scripts/brief.py new work/my-reel/brief.md --template reel-hook --set duration=10 --set bpm=96 \
    --set "concept=the phone screen is a window that closes on the viewer"
python -I <skill>/scripts/brief.py check work/my-reel/brief.md
```

Every `{{name|default}}` is a decision with a default; `--set name=value` replaces it, and `brief.py list` shows the
names. Write briefs in the project, never inside the skill (the next install replaces it).
