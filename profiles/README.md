# Taste profiles

Motionsmith ships generic defaults. Profiles make it yours: they record what you like, what you rejected and how
you work, and they override the guides every time the skill runs.

## Two kinds

| Profile | Where | What goes in it | Shared? |
|---|---|---|---|
| **Personal** | `profiles/personal/*.md` inside the installed skill: `~/.claude/skills/motionsmith/profiles/personal/` (Claude Code) or `~/.codex/skills/motionsmith/profiles/personal/` (Codex) | Your taste across every project: curves, looks, cadence, sound, working rules, things never to do | Never. The folder is in `.gitignore`; `install.py` never deletes or overwrites it |
| **Project** | `MOTIONSMITH.md` at the project root (or a path named in the project's `CLAUDE.md` / `AGENTS.md`) | That project's brand (palette, type, logo rules), approved and rejected pieces, platforms, delivery folders, data | Lives with the project |

Order of precedence: **project > personal > guide defaults**.

## Writing a profile

Start from [example.md](example.md): copy it into the installed skill's `profiles/personal/<your-name>.md`, or into a
clone's `profiles/personal/` and run `install.py`, which copies a personal profile only where the destination has
none (it never replaces yours). With both Claude Code and Codex installed, each install has its own copy: keep one as
the source and copy it over by hand when it changes. Keep it short and concrete:

- Prefer decisions over adjectives: "entrances use `back.out` or a spring with damping 0.5" beats "bouncy".
- Quote the person when a rule comes from them, with the date: rules with a reason survive.
- Record rejections as carefully as approvals: they are the strongest signal.
- Use the technique-lab codes (A1, F2…) when the choice was made by watching the lab: how to render it is in
  [references/00-index.md](../references/00-index.md) ("Choosing with the technique lab").

## Keeping it alive

When the user approves, rejects or corrects something, the skill offers to add it to the right profile, as a row of
the "Approved and rejected" table (date, piece, verdict, their words, what it teaches). A rule
that stops being true is edited or removed, not left to contradict a newer one.

## Privacy

A personal profile can contain names, brands, metrics and opinions about real work. It must never be committed to
a public repository, pasted into a shared document or sent to a third-party service. If you keep a backup, keep it
private.
