"""kit/comp.js: the After Effects model (keyframes with influence, overshoot keys, parenting, sequences, transitions)."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import unittest

KIT = Path(__file__).resolve().parents[1] / "scripts" / "kit"
PRELUDE = r"""
const vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
const box = {Math, JSON, Number, String, Array, Object, console};
box.window = box; box.globalThis = box; vm.createContext(box);
for (const f of ['motion-math.js', 'timeline.js', 'comp.js']) vm.runInContext(fs.readFileSync(path.join(process.argv[1], f), 'utf8'), box);
const A = box.Comp, k = A.k, out = {};
"""


def run(body: str) -> dict:
    r = subprocess.run(["node", "-e", PRELUDE + body + "\nconsole.log(JSON.stringify(out));", str(KIT)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "node runs the kit")
class CompTests(unittest.TestCase):
    def test_snap_peaks_early_and_settles_long(self):
        o = run("""
          const tr = k([0, 0, 'snap'], [1, 1000]);
          const v = t => A.value(tr, t);
          out.speeds = Array.from({length: 10}, (_, i) => v((i + 1) / 10) - v(i / 10));
          const easy = k([0, 0, 'easy'], [1, 1000]);
          out.easyMid = A.value(easy, .5);""")
        speeds = o["speeds"]
        self.assertLessEqual(speeds.index(max(speeds)), 1)        # fastest within the first fifth (it leaves from speed 0)
        self.assertLess(speeds[-1], speeds[0] * .1)              # a long, slow settle
        self.assertAlmostEqual(o["easyMid"], 500, delta=1)       # Easy Ease is symmetric

    def test_overshoot_goes_past_and_comes_back(self):
        o = run("""
          const tr = A.overshoot(0, 0, .5, 100, {amount: .1, settle: .2});
          out.peak = A.value(tr, .5); out.end = A.value(tr, .7); out.later = A.value(tr, 2);""")
        self.assertAlmostEqual(o["peak"], 110, delta=.01)
        self.assertAlmostEqual(o["end"], 100, delta=.01)
        self.assertAlmostEqual(o["later"], 100, delta=.01)

    def test_parenting_and_anchor(self):
        o = run("""
          const parent = A.layer({name: 'p', position: [500, 500], rotation: 90, scale: 200});
          const child = A.layer({name: 'c', parent: 'p', position: [10, 0], anchor: [5, 0]});
          const c = A.comp({width: 1000, height: 1000, duration: 1, layers: [child, parent]});
          out.child = A.matrix.apply(c.matrix('c', 0), [5, 0]);""")
        self.assertAlmostEqual(o["child"][0], 500, delta=1e-6)   # the child's anchor sits 10 px along the parent's
        self.assertAlmostEqual(o["child"][1], 520, delta=1e-6)   # rotated (90°) and scaled (×2) x axis

    def test_sequence_overlaps_and_keeps_one_track_length(self):
        o = run("""
          const one = () => A.comp({width: 100, height: 100, duration: 3, layers: [A.layer({name: 'x', position: [50, 50]})]});
          const film = A.sequence([{comp: one()}, {comp: one()}, {comp: one()}], [{type: 'whip', dur: .3}, {type: 'zoom', dur: .5, flash: '#f00'}]);
          out.duration = film.duration; out.starts = film.starts;
          out.lengths = [0, 2.8, 5.4, 8].map(t => film.track(t).length);""")
        self.assertAlmostEqual(o["duration"], 9 - .3 - .5, places=6)
        self.assertEqual([round(s, 3) for s in o["starts"]], [0, 2.7, 5.2])
        self.assertEqual(len(set(o["lengths"])), 1)

    def test_breathing_never_comes_to_rest(self):
        # The slow push keeps its speed to the last frame of a scene: an ease-out would freeze the end of every shot.
        o = run("""
          const one = () => A.comp({width: 100, height: 100, duration: 4, layers: [A.layer({name: 'x', position: [50, 50]})]});
          const film = A.sequence([{comp: one()}, {comp: one()}], [{type: 'cut'}]);
          const L = film.byName.get('scene1'), s = t => A.value(L.scale, t);
          out.mid = s(2.0 + 1 / 30) - s(2.0); out.end = s(4 - 1 / 30) - s(4 - 2 / 30);
          out.first = s(0); out.last = s(4);""")
        self.assertGreater(o["mid"], 0)
        self.assertGreater(o["end"], o["mid"] * .9)               # still pushing at the last frame
        self.assertGreater(o["last"] - o["first"], 3)              # a few percent over the scene

    def test_no_transition_crossfades(self):
        o = run("""
          out.bad = [];
          for (const [name, fn] of Object.entries(A.TRANSITIONS)) {
            const tr = fn({W: 1000, H: 1000, at: [500, 500]});
            for (let u = 0; u <= 1; u += .01) {
              const a = tr.out(u).opacity ?? 1, b = tr.in(u).opacity ?? 1;
              if (a > .02 && a < .98 && b > .02 && b < .98) { out.bad.push(name); break; }
            }
          }""")
        self.assertEqual(o["bad"], [])


if __name__ == "__main__":
    unittest.main()
