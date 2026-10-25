"""Install Motionsmith as a skill for Claude Code, Codex, Antigravity, Gemini CLI or any agent that reads SKILL.md.

    python install.py --all                     # every agent below that is installed on this machine
    python install.py --claude --codex          # ~/.claude/skills/motionsmith and ~/.codex/skills/motionsmith
    python install.py --antigravity             # ~/.gemini/config/skills/motionsmith (Antigravity app, IDE)
    python install.py --gemini                  # ~/.gemini/skills/motionsmith (Gemini CLI)
    python install.py --workspace path/to/project   # <project>/.agents/skills/motionsmith (Antigravity and others, per project)
    python install.py --dest D:/skills/motionsmith
    python install.py --claude --check          # list the files that would change, change nothing

The destination mirrors this folder (git metadata, caches and render output are skipped). Your personal taste
profiles in `<install>/profiles/personal/` belong to you, not to the repo: install never deletes or overwrites them.
A profile in this folder's `profiles/personal/` is copied only when the destination has no file of that name (a seed);
if both exist and differ, the installed one is kept and reported under "personal_kept". The previous install is backed
up first to ~/.motionsmith-backups/ (the last five per destination are kept). A destination that is not empty and is
not a Motionsmith install (for example ~/.claude/skills itself) is refused, because mirroring removes extra files.
"""
from __future__ import annotations

import argparse
import filecmp
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP_DIRS = {".git", ".github", "ci", "__pycache__", "node_modules", "preview", "final", "work"}
SKIP_SUFFIXES = {".pyc"}
PERSONAL = Path("profiles") / "personal"
KEEP_BACKUPS = 5


def files(base: Path) -> set[Path]:
    out = set()
    for path in base.rglob("*"):
        rel = path.relative_to(base)
        if any(part in SKIP_DIRS for part in rel.parts) or path.suffix in SKIP_SUFFIXES or not path.is_file():
            continue
        out.add(rel)
    return out


def personal(rel: Path) -> bool:
    return PERSONAL in rel.parents


def plan(dest: Path) -> dict[str, list[Path]]:
    src = files(ROOT)
    old = files(dest) if dest.exists() else set()
    differs = {p for p in src & old if not filecmp.cmp(ROOT / p, dest / p, shallow=False)}
    return {
        "add": sorted(p for p in src - old),                                   # personal seeds included: nothing to overwrite
        "change": sorted(p for p in differs if not personal(p)),
        "remove": sorted(p for p in old - src if not personal(p)),
        "personal_kept": sorted(p for p in differs if personal(p)),           # yours: never overwritten
    }


def backup_folder(dest: Path) -> Path:
    # e.g. claude-motionsmith-1a2b3c: the agent's folder, the skill, and a short hash of the path (two projects never mix)
    tag = f"{dest.parent.parent.name.lstrip('.') or 'skills'}-{dest.name}-{hashlib.sha1(str(dest).encode()).hexdigest()[:6]}"
    return Path.home() / ".motionsmith-backups" / f"{tag}-{time.strftime('%Y%m%d-%H%M%S')}"


def prune_backups(latest: Path) -> None:
    tag = latest.name.rsplit("-", 2)[0]
    siblings = sorted(p for p in latest.parent.glob(f"{tag}-*") if p.is_dir() and p.name.rsplit("-", 2)[0] == tag)
    for old in siblings[:-KEEP_BACKUPS]:
        shutil.rmtree(old, ignore_errors=True)


def refusal(dest: Path) -> str | None:
    """Why dest is not a safe place to mirror into, or None. Mirroring removes every file the repo does not have,
    so dest must be new, empty, or an earlier Motionsmith install: never a parent folder such as ~/.claude/skills."""
    if dest == ROOT or ROOT in dest.parents or dest in ROOT.parents:
        return "the destination and this folder contain each other"
    if not dest.exists():
        return None
    if not dest.is_dir():
        return "the destination exists and is not a folder"
    if not any(dest.iterdir()):
        return None
    skill = dest / "SKILL.md"
    if skill.is_file() and any(line.strip() == "name: motionsmith" for line in skill.read_text(encoding="utf-8", errors="replace").splitlines()[:10]):
        return None
    return "the destination is not empty and is not a Motionsmith install (use the skill folder itself, e.g. ~/.claude/skills/motionsmith)"


def install(dest: Path, check: bool) -> dict:
    why = refusal(dest)
    if why:
        return {"dest": str(dest), "installed": False, "error": why}
    steps = plan(dest)
    report = {"dest": str(dest), **{k: [p.as_posix() for p in v] for k, v in steps.items()}}
    pending = steps["add"] or steps["change"] or steps["remove"]
    if check or not pending:
        report["installed"] = False
        report["would_change"] = bool(pending)
        return report
    if dest.exists():
        backup = backup_folder(dest)
        shutil.copytree(dest, backup, ignore=shutil.ignore_patterns("__pycache__"))
        prune_backups(backup)
        report["backup"] = str(backup)
    for rel in steps["add"] + steps["change"]:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, target)
    for rel in steps["remove"]:
        (dest / rel).unlink()
    report["installed"] = True
    return report


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claude", action="store_true", help="install to ~/.claude/skills/motionsmith")
    parser.add_argument("--codex", action="store_true", help="install to ~/.codex/skills/motionsmith")
    parser.add_argument("--antigravity", action="store_true", help="install to ~/.gemini/config/skills/motionsmith")
    parser.add_argument("--gemini", action="store_true", help="install to ~/.gemini/skills/motionsmith (Gemini CLI)")
    parser.add_argument("--workspace", type=Path, action="append", default=[], help="a project: install to <project>/.agents/skills/motionsmith")
    parser.add_argument("--all", action="store_true", help="every agent whose home folder exists (~/.claude, ~/.codex, ~/.gemini)")
    parser.add_argument("--dest", type=Path, action="append", default=[], help="another destination folder")
    parser.add_argument("--check", action="store_true", help="only list what would change")
    args = parser.parse_args()
    dests = list(args.dest)
    home = Path.home()
    targets = {"claude": home / ".claude" / "skills" / "motionsmith", "codex": home / ".codex" / "skills" / "motionsmith",
               "antigravity": home / ".gemini" / "config" / "skills" / "motionsmith", "gemini": home / ".gemini" / "skills" / "motionsmith"}
    for name, target in targets.items():
        agent_home = target.parents[1] if name != "antigravity" else target.parents[2]
        if getattr(args, name) or (args.all and agent_home.is_dir()):
            dests.append(target)
    for project in args.workspace:
        if not project.is_dir():
            parser.error(f"--workspace must be an existing project folder: {project}")
        dests.append(project / ".agents" / "skills" / "motionsmith")
    if not dests:
        parser.error("choose --claude, --codex, --antigravity, --gemini, --workspace, --dest or --all")
    failed = False
    for dest in dests:
        report = install(dest.resolve(), args.check)
        failed = failed or "error" in report
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
