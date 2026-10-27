"""hook_variants.py: titles swapped safely, variants from the brief, the seam check and the joined renders."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import brief  # noqa: E402
import hook_variants as hv  # noqa: E402


def run_py(script: str, *args: object) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def browser_available() -> bool:
    if not (shutil.which("node") and shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return False
    return subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True).returncode == 0


BRIEF = """<direction>
concept: one body, three ways in
hooks:
- PARA -> an order
- ¿CANSADO? -> a question
seam: 2.6 s
</direction>
"""


class TitleAndInitTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="motion-hooks-"))

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def test_title_round_trip_with_quotes_and_accents(self):
        script = 'const A = 1;\n  const TITLE = "Hola | mundo";\nconst TITLE = "second";\n'
        self.assertEqual(hv.read_title(script), "Hola | mundo")
        changed = hv.set_title(script, 'Él dijo "no" | y \'ya\'')
        self.assertEqual(hv.read_title(changed), 'Él dijo "no" | y \'ya\'')
        self.assertIn('const TITLE = "second";', changed)   # only the first line changes

    def test_brief_reads_hooks_and_seam(self):
        report = brief.check(BRIEF)
        self.assertEqual(report["brief"]["hooks"], ["PARA -> an order", "¿CANSADO? -> a question"])
        self.assertFalse(any("hook" in e for e in report["errors"]))
        same = brief.check(BRIEF.replace("¿CANSADO? -> a question", "PARA -> an order"))
        self.assertTrue(any("same" in e for e in same["errors"]))
        no_seam = brief.check(BRIEF.replace("seam: 2.6 s\n", ""))
        self.assertTrue(any("seam" in w for w in no_seam["warnings"]))

    def test_init_keeps_the_body_of_the_title(self):
        piece = self.workspace / "piece"
        self.assertEqual(run_py("new_piece.py", piece, "--recipe", "promo-sequence", "--title", "FRÉNALE | el feed gasta").returncode, 0)
        (piece / "brief.md").write_text(BRIEF, encoding="utf-8")
        self.assertEqual(run_py("hook_variants.py", "init", "--piece", piece, "--brief", piece / "brief.md").returncode, 0)
        spec = json.loads((piece / "variants.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["seam"], 2.6)
        self.assertEqual([v["title"] for v in spec["variants"]],
                         ["FRÉNALE | el feed gasta", "PARA | el feed gasta", "¿CANSADO? | el feed gasta"])
        self.assertEqual(run_py("hook_variants.py", "init", "--piece", piece, "--brief", piece / "brief.md").returncode, 2)

    def test_render_refuses_a_bad_spec(self):
        piece = self.workspace / "piece"
        self.assertEqual(run_py("new_piece.py", piece, "--recipe", "promo-sequence").returncode, 0)
        (piece / "variants.json").write_text(json.dumps({"seam": 99, "variants": [{"id": "a", "title": "x"}]}), encoding="utf-8")
        result = run_py("hook_variants.py", "render", "--piece", piece)
        self.assertEqual(result.returncode, 2)
        self.assertIn("seam", result.stdout)
        self.assertIn("two or more", result.stdout)


@unittest.skipUnless(browser_available(), "node + Playwright + ffmpeg render the variants")
class RenderTests(unittest.TestCase):
    def test_variants_join_and_a_late_hook_is_refused(self):
        workspace = Path(tempfile.mkdtemp(prefix="motion-hooks-render-"))
        try:
            piece = workspace / "promo"
            self.assertEqual(run_py("new_piece.py", piece, "--recipe", "promo-sequence", "--format", "square", "--fps", "12",
                                    "--duration", "6", "--title", "MOVE | every frame counts").returncode, 0)
            spec = {"seam": 2.6, "variants": [{"id": "a", "title": "MOVE | every frame counts"},
                                              {"id": "b", "title": "STOP | every frame counts"}]}
            (piece / "variants.json").write_text(json.dumps(spec), encoding="utf-8")
            result = run_py("hook_variants.py", "render", "--piece", piece, "--audio", "none", "--preset", "ultrafast")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertLess(max(report["seam_difference"].values()), .5)
            self.assertEqual(report["rendered_frames"], 31 * 2 + 72 - 31)
            for v in report["variants"]:
                frames = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames",
                                         "-of", "csv=p=0", v["file"]], capture_output=True, text=True).stdout.strip()
                self.assertEqual(int(frames), 72)
            self.assertTrue((piece / "final" / "hooks" / "hooks.md").exists())
            # A statement that differs too is still on screen after the seam: refused, nothing rendered.
            spec["variants"][1]["title"] = "STOP | a different body"
            (piece / "variants.json").write_text(json.dumps(spec), encoding="utf-8")
            shutil.rmtree(piece / "final" / "hooks")
            bad = run_py("hook_variants.py", "render", "--piece", piece, "--audio", "none", "--preset", "ultrafast")
            self.assertEqual(bad.returncode, 1)
            self.assertIn("differs from the piece at the seam", bad.stdout)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
