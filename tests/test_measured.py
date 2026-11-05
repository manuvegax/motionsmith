"""Measured eases (motion-math 'm.*') and their use in comp.js keys and the 'measured' style."""
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
const M = box.MotionMath, A = box.Comp, out = {};
"""
# % of travel at 10 / 25 / 50 / 75 % of the time, as measured (motionmaxxing references/motion.md section 2).
TABLE = {
    "cruise": (10, 25, 50, 75), "glide": (16, 39, 69, 91), "softInOut": (4, 17, 50, 83), "softLand": (30, 59, 85, 95),
    "gentleIn": (1, 6, 24, 55), "snapSettle": (54, 84, 96, 98), "whip": (23, 52, 83, 97), "accelExit": (0, 3, 16, 47),
    "crashOut": (0, 0, 6, 32), "popOver": (10, 46, 96, 108), "crashIn": (91, 118, 110, 103), "bounceHard": (13, 62, 138, 139),
}
PEAKS = {"popOver": (.72, 1.08), "crashIn": (.27, 1.18), "bounceHard": (.62, 1.48)}


def run(body: str) -> dict:
    r = subprocess.run(["node", "-e", PRELUDE + body + "\nconsole.log(JSON.stringify(out));", str(KIT)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "node runs the kit")
class MeasuredEaseTests(unittest.TestCase):
    def test_every_ease_passes_its_measured_points(self):
        o = run("""
          for (const name of Object.keys(M.MEASURED)) {
            const f = M.easing('m.' + name);
            out[name] = {pts: [.1, .25, .5, .75].map(u => f(u) * 100), ends: [f(0), f(1)],
                         peak: Array.from({length: 1001}, (_, i) => [i / 1000, f(i / 1000)]).reduce((a, b) => b[1] > a[1] ? b : a)};
          }""")
        self.assertEqual(set(o), set(TABLE))
        for name, want in TABLE.items():
            got = o[name]["pts"]
            for g, w in zip(got, want):
                self.assertAlmostEqual(g, w, delta=3.5, msg=f"{name}: {got} vs measured {want}")
            self.assertAlmostEqual(o[name]["ends"][0], 0, delta=1e-9)
            self.assertAlmostEqual(o[name]["ends"][1], 1, delta=1e-9)
        for name, (t, v) in PEAKS.items():
            pt, pv = o[name]["peak"]
            self.assertAlmostEqual(pt, t, delta=.03, msg=name)
            self.assertAlmostEqual(pv, v, delta=.01, msg=name)

    def test_non_overshooting_eases_never_pass_the_mark(self):
        o = run("""
          for (const name of ['cruise', 'glide', 'softInOut', 'softLand', 'gentleIn', 'snapSettle', 'whip', 'accelExit', 'crashOut']) {
            const f = M.easing('m.' + name), v = Array.from({length: 401}, (_, i) => f(i / 400));
            out[name] = {max: Math.max(...v), monotone: v.every((x, i) => i === 0 || x >= v[i - 1] - 1e-9)};
          }""")
        for name, r in o.items():
            self.assertLessEqual(r["max"], 1 + 1e-9, name)
            self.assertTrue(r["monotone"], name)

    def test_comp_keys_and_the_measured_style_use_them(self):
        o = run("""
          const tr = A.k([0, 0, 'm.softLand'], [1, 100]);
          out.land = [.1, .25, .5].map(t => A.value(tr, t));
          const lv = A.k([0, 0, 'm.accelExit'], [1, 100]);
          out.leave = A.value(lv, .5);
          out.curve = A.curve('m.snapSettle')(.1);
          const s = A.style('measured'); out.style = {arrive: s.arrive, exit: s.exit, overshoot: s.overshoot, offset: s.offset};
          A.style('editorial');
          out.bad = (() => { try { A.k([0, 0, 'nope'], [1, 1]); return 'no error'; } catch (e) { return e.name; } })();""")
        self.assertAlmostEqual(o["land"][0], 27.1, delta=1)      # 1 - 0.9^3
        self.assertAlmostEqual(o["leave"], 16.5, delta=1)        # 0.5^2.6
        self.assertAlmostEqual(o["curve"], .54, delta=.01)
        self.assertEqual(o["style"], {"arrive": "m.softLand", "exit": "m.accelExit", "overshoot": 0, "offset": 2})
        self.assertEqual(o["bad"], "RangeError")


if __name__ == "__main__":
    unittest.main()
