"""B-roll: provenance, the shot list from the plan, the assembled timeline, credits and the recipe drawing it."""
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
FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def run_py(script: str, *args: object) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


def out(result: subprocess.CompletedProcess) -> dict:
    return json.loads(result.stdout)


def browser_available() -> bool:
    if not (shutil.which("node") and FFMPEG):
        return False
    return subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True).returncode == 0


@unittest.skipUnless(FFMPEG, "ffmpeg makes and conforms the clips")
class BrollTests(unittest.TestCase):
    def setUp(self):
        from PIL import Image
        self.workspace = Path(tempfile.mkdtemp(prefix="motion-broll-"))
        self.piece = self.workspace / "piece"
        self.assertEqual(run_py("new_piece.py", self.piece, "--recipe", "broll-story", "--format", "square", "--fps", "24",
                                "--duration", "4").returncode, 0)
        plan = json.loads((self.piece / "plan.json").read_text(encoding="utf-8"))
        # Three scenes: a clip, a still with a cut-out, nothing.
        plan["scenes"] = [
            {"id": "s01", "start_frame": 0, "end_frame": 36, "intent": "i", "action": "a clip", "text": "one", "transition": {"kind": "cut"}},
            {"id": "s02", "start_frame": 36, "end_frame": 72, "intent": "i", "action": "a photo", "text": "two", "transition": {"kind": "cut"}},
            {"id": "s03", "start_frame": 72, "end_frame": 96, "intent": "i", "action": "nothing", "text": "three", "transition": {"kind": "end"}}]
        (self.piece / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
        self.media = self.workspace / "media"
        self.media.mkdir()
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30", "-t", "1",
                        "-pix_fmt", "yuv420p", str(self.media / "short clip.mp4")], check=True)
        Image.new("RGB", (1600, 1200), (200, 120, 60)).save(self.media / "photo.jpg")
        Image.new("RGBA", (1600, 1200), (0, 0, 0, 0)).save(self.media / "photo-fg.png")

    def tearDown(self):
        shutil.rmtree(self.workspace, ignore_errors=True)

    def ingest(self, *extra):
        return run_py("broll.py", "ingest", *extra, "--piece", self.piece)

    def test_licence_rules(self):
        self.assertEqual(self.ingest(self.media / "photo.jpg").returncode, 2)
        self.assertEqual(self.ingest(self.media / "photo.jpg", "--license", "cc-by", "--source", "https://x").returncode, 2)
        self.assertEqual(self.ingest(self.media / "photo.jpg", "--license", "cc0").returncode, 2)   # no source
        ok = self.ingest(self.media / "photo.jpg", "--license", "cc-by", "--author", "Ana", "--source", "https://x")
        self.assertEqual(ok.returncode, 0, ok.stdout)
        again = out(self.ingest(self.media / "photo.jpg", "--license", "cc0", "--source", "https://y"))
        self.assertTrue(any("already" in w for w in again["warnings"]))
        record = json.loads((self.piece / "assets" / "broll" / "provenance.json").read_text(encoding="utf-8"))[0]
        self.assertEqual((record["license"], record["author"], record["kind"]), ("cc-by", "Ana", "image"))
        self.assertEqual(len(record["sha256"]), 64)

    def test_shotlist_assemble_credits(self):
        self.assertEqual(self.ingest(self.media / "short clip.mp4", "--license", "cc0", "--source", "https://clip").returncode, 0)
        self.assertEqual(self.ingest(self.media / "photo.jpg", self.media / "photo-fg.png", "--license", "cc-by",
                                     "--author", "Ana", "--source", "https://photo").returncode, 0)
        shots_report = out(run_py("broll.py", "shotlist", "--piece", self.piece))
        self.assertEqual(shots_report["shots"], 3)
        path = self.piece / "assets" / "broll" / "shots.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual([s["move"] for s in spec["shots"]], ["push-in", "pan-left", "pull-out"])
        spec["shots"][0]["file"] = "short-clip.mp4"
        spec["shots"][1].update(file="photo.jpg", fg="photo-fg.png")
        path.write_text(json.dumps(spec), encoding="utf-8")
        result = run_py("broll.py", "assemble", "--piece", self.piece)
        report = out(result)
        self.assertEqual(result.returncode, 0, report)
        self.assertEqual((report["video"], report["stills"], report["gaps"]), (1, 1, 1))
        self.assertTrue(any("holds" in w for w in report["warnings"]))   # a 1 s clip for a 1.5 s scene
        timeline = json.loads((self.piece / "assets" / "broll" / "timeline.json").read_text(encoding="utf-8"))
        video = timeline["segments"][0]
        self.assertEqual(video["count"], 36)
        self.assertEqual(len(list((self.piece / video["dir"]).glob("f*.jpg"))), 36)
        self.assertTrue((self.piece / video["dir"] / "f000000.jpg").exists())
        from PIL import Image
        with Image.open(self.piece / video["dir"] / "f000035.jpg") as im:
            self.assertEqual(im.size, (1080, 1080))
        self.assertIn("fg", timeline["segments"][1])
        plan = json.loads((self.piece / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["broll"], "assets/broll/timeline.json")
        credits = out(run_py("broll.py", "credits", "--piece", self.piece))
        self.assertTrue(credits["attribution_required"])
        self.assertEqual(len(credits["credits"]), 2)
        self.assertTrue(any("Ana" in c and "CC-BY" in c for c in credits["credits"]))
        # The GPU-free check runs the recipe with the timeline in place.
        check = subprocess.run(["node", str(SKILL / "tests" / "recipes_check.js"), str(self.piece)], capture_output=True, text=True)
        self.assertEqual(json.loads(check.stdout.strip().splitlines()[-1])["errors"], [])

    def test_unknown_file_is_refused(self):
        self.assertEqual(run_py("broll.py", "shotlist", "--piece", self.piece).returncode, 0)
        path = self.piece / "assets" / "broll" / "shots.json"
        spec = json.loads(path.read_text(encoding="utf-8"))
        spec["shots"][0]["file"] = "never-ingested.mp4"
        path.write_text(json.dumps(spec), encoding="utf-8")
        result = run_py("broll.py", "assemble", "--piece", self.piece)
        self.assertEqual(result.returncode, 1)
        self.assertIn("ingest it first", result.stdout)


@unittest.skipUnless(browser_available(), "node + Playwright render the timeline")
class BrollRenderTests(unittest.TestCase):
    def test_cut_frame_has_no_ghost_and_footage_is_drawn(self):
        from PIL import Image
        import numpy as np
        workspace = Path(tempfile.mkdtemp(prefix="motion-broll-render-"))
        try:
            piece = workspace / "p"
            self.assertEqual(run_py("new_piece.py", piece, "--recipe", "broll-story", "--format", "square", "--fps", "24",
                                    "--duration", "4").returncode, 0)
            plan = json.loads((piece / "plan.json").read_text(encoding="utf-8"))
            plan["scenes"] = [
                {"id": "s01", "start_frame": 0, "end_frame": 48, "intent": "i", "action": "red", "text": "", "transition": {"kind": "cut"}},
                {"id": "s02", "start_frame": 48, "end_frame": 96, "intent": "i", "action": "blue", "text": "", "transition": {"kind": "end"}}]
            (piece / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
            Image.new("RGB", (1400, 1400), (220, 30, 30)).save(workspace / "red.jpg")
            Image.new("RGB", (1400, 1400), (30, 30, 220)).save(workspace / "blue.jpg")
            self.assertEqual(run_py("broll.py", "ingest", workspace / "red.jpg", workspace / "blue.jpg", "--piece", piece, "--own").returncode, 0)
            run_py("broll.py", "shotlist", "--piece", piece)
            path = piece / "assets" / "broll" / "shots.json"
            spec = json.loads(path.read_text(encoding="utf-8"))
            spec["shots"][0]["file"], spec["shots"][1]["file"] = "red.jpg", "blue.jpg"
            path.write_text(json.dumps(spec), encoding="utf-8")
            self.assertEqual(run_py("broll.py", "assemble", "--piece", piece).returncode, 0)
            shots = workspace / "shots"
            r = subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(piece), "--out", str(shots),
                                "--frames", "47:48", "--png"], capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr)
            before, after = (np.asarray(Image.open(f).convert("RGB"), dtype=float) for f in sorted(shots.glob("*.png")))
            corner = (slice(20, 120), slice(20, 120))   # away from the captions
            self.assertGreater(before[corner][..., 0].mean(), before[corner][..., 2].mean() + 60)   # red, not grey
            self.assertGreater(after[corner][..., 2].mean(), after[corner][..., 0].mean() + 60)     # blue, no red ghost
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
