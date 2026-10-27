"""kit/collage.js: mixed-weight phrases (keyword spans), and the recipes built on it run headless."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = r"""
const vm = require('node:vm'), fs = require('node:fs'), path = require('node:path');
const kit = process.argv[1];
const box = {Math, JSON, Number, String, Array, Object, Intl, console};
box.window = box; box.globalThis = box;
vm.createContext(box);
for (const f of ['motion-math.js', 'collage.js']) vm.runInContext(fs.readFileSync(path.join(kit, f), 'utf8'), box);
const ctx = {font: '', measureText(t) { const s = Number((/(\d+(?:\.\d+)?)px/.exec(this.font) || [0, 10])[1]); return {width: [...t].length * s * .56}; }};
const C = box.Collage.create({W: 1080, H: 1920, U: 1080, base: ctx});
const out = C.layoutPhrase(process.argv[2], {width: 900, size: 100, measure: ctx});
console.log(JSON.stringify(out.map(w => [w.text, w.kind, w.line])));
"""


def layout(text: str) -> list:
    r = subprocess.run(["node", "-e", SCRIPT, str(SKILL / "scripts" / "kit"), text], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "node runs the kit")
class CollageTests(unittest.TestCase):
    def test_keyword_spans_and_small_words(self):
        words = layout("~Of ~what ~you ~see, | *70 %* | ~you ~did ~not ~choose.")
        self.assertEqual([w[1] for w in words if w[0] in ("70", "%")], ["key", "key"])
        self.assertEqual({w[1] for w in words if w[0] in ("Of", "choose.")}, {"small"})
        self.assertEqual(max(w[2] for w in words), 2)
        spans = layout("This is *take it back* now")
        self.assertEqual([w[1] for w in spans], ["body", "body", "key", "key", "key", "body"])

    def test_recipes_run_headless(self):
        workspace = Path(tempfile.mkdtemp(prefix="motion-collage-"))
        try:
            for recipe in ("editorial-collage", "broll-story"):
                piece = workspace / recipe
                subprocess.run([sys.executable, "-I", str(SKILL / "scripts" / "new_piece.py"), str(piece), "--recipe", recipe,
                                "--fps", "30"], check=True, capture_output=True)
                check = subprocess.run(["node", str(SKILL / "tests" / "recipes_check.js"), str(piece)], capture_output=True, text=True)
                result = json.loads(check.stdout.strip().splitlines()[-1])
                self.assertEqual(result["errors"], [], recipe)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
