"""install.py: mirrors the skill, lists what would change, and never deletes or overwrites a personal profile."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]


def load_installer():
    spec = importlib.util.spec_from_file_location("motionsmith_install", SKILL / "install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Install(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="motion-install-"))
        self.src = self.tmp / "clone"
        for rel, text in {"SKILL.md": "---\nname: motionsmith\n---\nv1", "scripts/tool.py": "print(1)", "profiles/personal/me.md": "seed",
                          "profiles/personal/.gitkeep": "", "__pycache__/x.pyc": "skip", "work/piece/plan.json": "{}"}.items():
            path = self.src / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home), "USERPROFILE": str(self.home)})
        self.env.start()
        self.installer = load_installer()
        self.installer.ROOT = self.src
        self.dest = self.home / ".claude" / "skills" / "motionsmith"

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_first_install_seeds_the_profile_and_skips_caches_and_work(self):
        report = self.installer.install(self.dest, check=False)
        self.assertTrue(report["installed"])
        self.assertEqual((self.dest / "profiles/personal/me.md").read_text(encoding="utf-8"), "seed")
        self.assertFalse((self.dest / "__pycache__").exists())
        self.assertFalse((self.dest / "work").exists())

    def test_reinstall_never_overwrites_or_deletes_personal_files(self):
        self.installer.install(self.dest, check=False)
        (self.dest / "profiles/personal/me.md").write_text("approvals recorded after install", encoding="utf-8")
        (self.dest / "profiles/personal/only-here.md").write_text("mine", encoding="utf-8")
        (self.src / "SKILL.md").write_text("---\nname: motionsmith\n---\nv2", encoding="utf-8")
        (self.dest / "scripts/stale.py").write_text("old", encoding="utf-8")
        check = self.installer.install(self.dest, check=True)
        self.assertEqual((check["change"], check["remove"], check["personal_kept"]),
                         (["SKILL.md"], ["scripts/stale.py"], ["profiles/personal/me.md"]))
        self.assertTrue(check["would_change"])
        self.assertEqual((self.dest / "SKILL.md").read_text(encoding="utf-8"), "---\nname: motionsmith\n---\nv1")   # --check touches nothing
        report = self.installer.install(self.dest, check=False)
        self.assertTrue(report["installed"])
        self.assertTrue((self.dest / "SKILL.md").read_text(encoding="utf-8").endswith("v2"))
        self.assertFalse((self.dest / "scripts/stale.py").exists())
        self.assertEqual((self.dest / "profiles/personal/me.md").read_text(encoding="utf-8"), "approvals recorded after install")
        self.assertEqual((self.dest / "profiles/personal/only-here.md").read_text(encoding="utf-8"), "mine")
        backup = Path(report["backup"])
        self.assertTrue(backup.name.startswith("claude-motionsmith-"), backup.name)
        self.assertEqual((backup / "profiles/personal/only-here.md").read_text(encoding="utf-8"), "mine")

    def test_refuses_a_folder_that_is_not_a_motionsmith_install(self):
        skills = self.home / ".claude" / "skills"
        (skills / "other-skill").mkdir(parents=True)
        (skills / "other-skill" / "SKILL.md").write_text("---\nname: other\n---\n", encoding="utf-8")
        report = self.installer.install(skills, check=False)                    # the parent folder, by mistake
        self.assertIn("error", report)
        self.assertTrue((skills / "other-skill" / "SKILL.md").exists())
        self.assertIn("error", self.installer.install(self.src / "nested", check=True))   # inside the repo
        self.assertNotIn("error", self.installer.install(self.dest, check=False))          # a new folder is fine
        (self.src / "SKILL.md").write_text("---\nname: motionsmith\n---\nv1", encoding="utf-8")
        self.installer.install(self.dest, check=False)
        self.assertNotIn("error", self.installer.install(self.dest, check=True))           # and an earlier install

    def test_every_agent_target_and_all(self):
        import subprocess, sys as _sys
        (self.home / ".claude").mkdir()
        (self.home / ".gemini").mkdir()
        project = self.tmp / "project"
        project.mkdir()
        env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home)}
        run = lambda *a: subprocess.run([_sys.executable, str(SKILL / "install.py"), *a, "--check"], capture_output=True, text=True, encoding="utf-8", env=env)
        out = run("--all").stdout
        for part in (".claude/skills/motionsmith", ".gemini/config/skills/motionsmith", ".gemini/skills/motionsmith"):
            self.assertIn(part, out.replace("\\\\", "/").replace("\\", "/"))
        self.assertNotIn(".codex", out)                                         # no ~/.codex here: --all skips it
        out = run("--codex", "--workspace", str(project)).stdout.replace("\\\\", "/").replace("\\", "/")
        self.assertIn(".codex/skills/motionsmith", out)
        self.assertIn("project/.agents/skills/motionsmith", out)
        self.assertNotEqual(run("--workspace", str(self.tmp / "missing")).returncode, 0)

    def test_backups_are_pruned_to_the_last_five(self):
        root = self.home / ".motionsmith-backups"
        for i in range(7):
            (root / f"claude-motionsmith-2026010{i}-000000").mkdir(parents=True)
        (root / "codex-motionsmith-20260101-000000").mkdir()
        self.installer.prune_backups(root / "claude-motionsmith-20260106-000000")
        left = sorted(p.name for p in root.iterdir())
        self.assertEqual(len([n for n in left if n.startswith("claude-")]), 5)
        self.assertIn("codex-motionsmith-20260101-000000", left)              # another destination's backups stay


if __name__ == "__main__":
    unittest.main()
