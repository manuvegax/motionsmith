/* Runs scaffolded pieces without a browser: loads each piece's own kit in Node, builds the environment from its
   plan.json (Stage.createEnv with a fake text measure), calls setup() once and state(t) on a dense grid of times.
   Checks that state never throws, that `track` (what drives the motion blur) has the same length at every t and only
   finite numbers, and reports the piece's optional `debug` field (e.g. the kinetic quote's keyword) so tests can
   assert on it. tests/test_recipes.py scaffolds the pieces (every recipe, every format, odd titles) and calls this.

   node tests/recipes_check.js <piece folder> [...] → one JSON line per piece: {piece, ok, errors, samples, track, debug} */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const segmenter = new Intl.Segmenter(undefined, {granularity: 'grapheme'});
const graphemes = text => [...segmenter.segment(String(text))].length;

/* A Canvas 2D stand-in for measuring: every grapheme is 0.56 em wide, plus letterSpacing. */
function fakeContext() {
  return {
    font: '10px sans-serif', letterSpacing: '0px', textAlign: 'start', textBaseline: 'alphabetic',
    measureText(text) {
      const size = Number((/(\d+(?:\.\d+)?)px/.exec(this.font) || [0, 10])[1]);
      const spacing = parseFloat(this.letterSpacing) || 0, n = graphemes(text);
      return {width: n * size * .56 + spacing * n, actualBoundingBoxAscent: size * .72, actualBoundingBoxDescent: size * .2};
    },
  };
}

class Path2D { constructor(d) { this.d = d; } addPath() {} }

async function check(folder) {
  const out = {piece: folder, ok: false, errors: [], samples: 0, track: null, debug: null};
  try {
    const plan = JSON.parse(fs.readFileSync(path.join(folder, 'plan.json'), 'utf8'));
    const kit = path.join(folder, 'kit');
    const sandbox = {console, Intl, Path2D, Math, JSON, Number, String, Array, Object, Error, TypeError, RangeError};
    sandbox.window = sandbox; sandbox.globalThis = sandbox;
    const context = vm.createContext(sandbox);
    for (const file of ['motion-math.js', 'postfx-glsl.js', 'timeline.js', 'kinetic-type.js', 'stage.js', 'footage.js', 'collage.js', 'comp.js']) {
      const source = fs.readFileSync(path.join(kit, file), 'utf8');
      vm.runInContext(source, context, {filename: file});   // UMD modules see no `module` here: they set globals
    }
    let cfg = null;
    sandbox.Stage.run = c => { cfg = c; return Promise.resolve(true); };
    vm.runInContext(fs.readFileSync(path.join(folder, 'piece.js'), 'utf8'), context, {filename: 'piece.js'});
    if (!cfg) throw new Error('piece.js did not call Stage.run');
    const ctx = fakeContext();
    const env = sandbox.Stage.createEnv(plan, () => ctx);
    if (cfg.setup) await cfg.setup(env);
    const step = 1 / Math.min(60, env.FPS);
    let length = null;
    for (let t = -.1; t <= env.DURATION + .1; t += step) {
      const s = cfg.state(t, env);
      out.samples++;
      const track = s && s.track;
      if (!Array.isArray(track)) { out.errors.push(`t=${t.toFixed(3)}: state has no track array`); break; }
      if (length === null) length = track.length;
      if (track.length !== length) out.errors.push(`t=${t.toFixed(3)}: track length ${track.length}, was ${length}`);
      const bad = track.findIndex(p => !Array.isArray(p) || p.length < 2 || !Number.isFinite(p[0]) || !Number.isFinite(p[1]));
      if (bad >= 0) out.errors.push(`t=${t.toFixed(3)}: track[${bad}] = ${JSON.stringify(track[bad])}`);
      if (s.debug !== undefined) out.debug = s.debug;
      if (out.errors.length > 5) break;
    }
    out.track = length;
  } catch (error) {
    out.errors.push(String(error && error.stack || error).split('\n').slice(0, 3).join(' | '));
  }
  out.ok = out.errors.length === 0;
  return out;
}

(async () => {
  const folders = process.argv.slice(2);
  if (!folders.length) { console.error('usage: node tests/recipes_check.js <piece folder> [...]'); process.exit(2); }
  let failed = 0;
  for (const folder of folders) {
    const result = await check(path.resolve(folder));
    if (!result.ok) failed++;
    console.log(JSON.stringify(result));
  }
  process.exit(failed ? 1 : 0);
})();
