# Companions

Other open-source skills that ship inside Motionsmith because they help it. Each keeps its own licence, notice and
credit; Motionsmith does not modify them (to update one, copy a newer upstream over its folder).

## motion-architect

By Enrique Rocha ([@soyenriquerocha](https://github.com/Hainrixz), tododeia.com), MIT, upstream
[github.com/Hainrixz/motion-architect](https://github.com/Hainrixz/motion-architect) (commit in `UPSTREAM_COMMIT`).
A Remotion-based motion-graphics agent: intake, references, brand, an approved storyboard, React compositions,
stills, render. Its own notice and third-party list: `motion-architect/NOTICE`, `motion-architect/third_party/NOTICES.md`.

What Motionsmith uses it for:

| Need | Use | Command |
|---|---|---|
| Study a reference video (a URL or a file): frames at the cuts, scene changes, captions | Its vision engine, always `--engine local` | `python <skill>/companions/motion-architect/skills/motion-architect/engine/vision/analyze.py "<url-or-file>" --engine local --no-whisper` |
| Palettes, type pairings, styles from a mood ("editorial magazine", "raw collage") | Its design engine (a searchable catalogue) | `python <skill>/companions/motion-architect/skills/motion-architect/engine/design/scripts/search.py "editorial collage" --domain style` (also `--domain color`, `typography`) |
| UI click, key and impact sounds (CC0, Kenney and opengameart) | Its SFX library | `<skill>/companions/motion-architect/studio/public/sfx/` (index: `skills/motion-architect/references/sfx-library.md`) |
| A piece the person wants built in React and previewed in Remotion Studio | The whole agent: `/motion` in Claude Code | Studio at `~/motion-architect/studio` (`npm run studio`) |

Run its Python scripts with plain `python` (not `-I`): they import their neighbour modules. The vision engine only
reaches the internet to download a URL you give it (yt-dlp), or if you configure a key (Gemini, Groq, OpenAI) for its
optional cloud modes; Motionsmith never sets one.

When to stay in Motionsmith instead: real sub-frame motion blur, HDR light and bloom, screen print, variable-font type,
the editorial-collage kit, sound by synthesis, voice-led and B-roll pieces, hook variants, parallel resumable renders.
Remotion's licence is free for individuals and small teams; check it before commercial use by a company.

### Installing it as its own agent

```bash
# the studio where it builds and renders (it looks in ./studio, $MOTION_ARCHITECT_HOME or ~/motion-architect)
cp -r <skill>/companions/motion-architect ~/motion-architect
cd ~/motion-architect/studio && npm install
# Claude Code: its /motion command and reference-analyst agent
claude plugin marketplace add ~/motion-architect
claude plugin install motion-architect@motion-architect
# Codex, Antigravity, Gemini CLI: the skill folder
cp -r ~/motion-architect/skills/motion-architect ~/.codex/skills/
```
