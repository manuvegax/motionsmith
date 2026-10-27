"""Moving holds: hold_check.py finds frozen stretches; comp.js keeps layers and scenes alive after their keys land."""
from __future__ import annotations

import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

SKILL = Path(__file__).resolve().parents[1]
KIT = SKILL / "scripts" / "kit"
FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def encode(path: Path, frames: list[np.ndarray], fps: int = 30) -> None:
    h, w = frames[0].shape
    subprocess.run(["ffmpeg", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                    "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(path)],
                   input=b"".join(f.astype(np.uint8).tobytes() for f in frames), check=True, capture_output=True)


@unittest.skipUnless(FFMPEG, "ffmpeg encodes the fixtures")
class HoldCheckTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="motion-holds-"))
        self.rng = np.random.default_rng(1)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def clip(self, still_from: int | None, speed: float = 1.6) -> Path:
        """A disc that travels, with grain on every frame; from frame `still_from` it stops (grain only)."""
        yy, xx = np.mgrid[0:240, 0:136]
        out = []
        for i in range(90):
            j = i if still_from is None or i < still_from else still_from
            x = 30 + j * speed
            r = np.sqrt((xx - x) ** 2 + (yy - 120) ** 2)
            disc = np.clip(25.5 - r, 0, 1)                                      # antialiased edge, as the stage draws
            img = 200 - 120 * disc + self.rng.normal(0, 1.2, (240, 136))     # grain, as the finish adds
            out.append(np.clip(img, 0, 255))
        path = self.dir / f"clip-{still_from}-{speed}.mp4"
        encode(path, out)
        return path

    def run_check(self, path: Path) -> dict:
        r = subprocess.run([sys.executable, "-I", str(SKILL / "scripts" / "hold_check.py"), str(path), "--min", ".5"],
                           capture_output=True, text=True)
        return json.loads(r.stdout)

    def test_a_frozen_end_is_found(self):
        report = self.run_check(self.clip(still_from=50))
        self.assertEqual(len(report["holds"]), 1, report)
        self.assertAlmostEqual(report["holds"][0]["start"], 50 / 30, delta=.1)

    def test_constant_motion_is_alive(self):
        report = self.run_check(self.clip(still_from=None))
        self.assertEqual(report["holds"], [], report)

    def test_a_moving_hold_under_notice_is_alive(self):
        # 0.2 px per frame (6 px a second): what a slow push and drift give; grain alone must not pass for it
        report = self.run_check(self.clip(still_from=None, speed=.2))
        self.assertEqual(report["holds"], [], report)
        self.assertGreater(report["median_edge_speed"], .1)


@unittest.skipUnless(shutil.which("node"), "node runs the kit")
class DriftTests(unittest.TestCase):
    def test_drift_starts_after_the_last_key_and_stays_tiny(self):
        script = r"""
          const vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
          const box = {Math, JSON, Number, String, Array, Object, console}; box.window = box; box.globalThis = box; vm.createContext(box);
          for (const f of ['motion-math.js', 'timeline.js', 'comp.js']) vm.runInContext(fs.readFileSync(path.join(process.argv[1], f), 'utf8'), box);
          const A = box.Comp, k = A.k;
          const L = A.layer({name: 'card', position: k([0, [0, 0], 'snap'], [1, [500, 500]])});
          const still = A.layer({name: 'still', position: [500, 500], drift: false});
          const c = A.comp({width: 1000, height: 1000, duration: 6, layers: [L, still]});
          const at = (n, t) => A.matrix.apply(c.matrix(n, t), [0, 0]);
          const out = {atLanding: at('card', 1), later: [2, 3, 4, 5].map(t => at('card', t)), still: [2, 5].map(t => at('still', t))};
          console.log(JSON.stringify(out));"""
        r = subprocess.run(["node", "-e", script, str(KIT)], capture_output=True, text=True, check=True)
        o = json.loads(r.stdout)
        self.assertAlmostEqual(o["atLanding"][0], 500, delta=.01)         # exactly on the key when it lands
        moves = [math.hypot(p[0] - 500, p[1] - 500) for p in o["later"]]
        self.assertTrue(all(.05 < m < 30 for m in moves), moves)        # then alive, but only a few px (and the slow growth)
        self.assertEqual(o["still"][0], o["still"][1])                    # drift: false stays put

    def test_scenes_breathe_to_the_last_frame(self):
        script = r"""
          const vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
          const box = {Math, JSON, Number, String, Array, Object, console}; box.window = box; box.globalThis = box; vm.createContext(box);
          for (const f of ['motion-math.js', 'timeline.js', 'comp.js']) vm.runInContext(fs.readFileSync(path.join(process.argv[1], f), 'utf8'), box);
          const A = box.Comp;
          const s = A.comp({width: 1000, height: 1000, duration: 3, layers: [A.layer({name: 'x', position: [500, 500], drift: false})]});
          const film = A.sequence([{comp: s}], []);
          const corner = t => A.matrix.apply(film.matrix('scene0', t), [0, 0]);
          console.log(JSON.stringify([2.5, 2.8, 2.98].map(corner)));"""
        r = subprocess.run(["node", "-e", script, str(KIT)], capture_output=True, text=True, check=True)
        pts = json.loads(r.stdout)
        self.assertNotEqual(pts[1], pts[2])                               # still moving in the last frames
        self.assertLess(math.hypot(pts[2][0] - pts[1][0], pts[2][1] - pts[1][1]), 10)   # gently

    def test_sway_never_shows_the_edge(self):
        # The scene's sway and tilt never uncover the comp's background: every frame corner stays inside the scene.
        script = r"""
          const vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
          const box = {Math, JSON, Number, String, Array, Object, console}; box.window = box; box.globalThis = box; vm.createContext(box);
          for (const f of ['motion-math.js', 'timeline.js', 'comp.js']) vm.runInContext(fs.readFileSync(path.join(process.argv[1], f), 'utf8'), box);
          const A = box.Comp, W = 1080, H = 1920, out = [];
          for (const style of ['editorial', 'punchy', 'calm', 'sober']) {
            A.style(style);
            const s = () => A.comp({width: W, height: H, duration: 4, layers: [A.layer({name: 'x', position: [0, 0], drift: false})]});
            const film = A.sequence([{comp: s()}, {comp: s()}], [{type: 'cut'}]);
            for (let t = 0; t < film.duration; t += 1 / 30) {
              const name = t < film.starts[1] ? 'scene0' : 'scene1', m = film.matrix(name, t);
              // invert the scene's 2D matrix and map each frame corner into scene space
              const [a, b, c, d, e, f] = m, det = a * d - b * c;
              for (const [x, y] of [[0, 0], [W, 0], [0, H], [W, H]]) {
                const u = (d * (x - e) - c * (y - f)) / det, v = (-b * (x - e) + a * (y - f)) / det;
                if (u < -.5 || v < -.5 || u > W + .5 || v > H + .5) { out.push([style, +t.toFixed(2), x, y]); break; }
              }
            }
          }
          A.style('editorial');
          console.log(JSON.stringify(out.slice(0, 5)));"""
        r = subprocess.run(["node", "-e", script, str(KIT)], capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(r.stdout), [])


if __name__ == "__main__":
    unittest.main()
