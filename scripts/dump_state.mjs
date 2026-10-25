/* Evaluate a JavaScript expression of `t` inside a composition at many instants and save the values as JSON.
   It is how a trajectory, a spring or a camera is checked with data instead of with a single frame.

   node dump_state.mjs --root <piece> --expr "window.lensAt(t)" --from 6.4 --to 7.6 --step 0.01 --out preview/lens.json
   node dump_state.mjs --root <piece> --expr "window.labState(t).dot" --times 1,1.5,2 --seek --out ...
   --seek calls window.seek(t) first (for state that only exists after drawing). Then: python motion_curves.py --json <out>. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {openComposition, seek, parseArgs} from './kit/runtime.mjs';

const usage = 'Usage: node dump_state.mjs --root <piece> --expr "<js using t>" (--from a --to b --step s | --times t1,t2) --out <file.json> [--seek] [--page sub/index.html] [--node-modules dir] [--chrome exe]';
let args;
try { args = parseArgs(process.argv.slice(2), {flags: ['seek', 'help']}); }
catch (error) { console.error(error.message + '\n' + usage); process.exit(2); }
if (args.help || !args.root || !args.expr || !args.out) { console.log(usage); process.exit(args.help ? 0 : 2); }

let times;
if (args.times) times = args.times.split(',').filter(Boolean).map(Number);
else {
  const from = Number(args.from), to = Number(args.to), step = Number(args.step || 1 / 60);
  if (!(to >= from) || !(step > 0)) { console.error('Use --from a --to b --step s with b >= a and s > 0\n' + usage); process.exit(2); }
  times = [];
  for (let i = 0; from + i * step <= to + 1e-9; i++) times.push(Number((from + i * step).toFixed(6)));
}
if (!times.length || times.some(t => !Number.isFinite(t))) { console.error('No valid instants'); process.exit(2); }

const session = await openComposition({root: args.root, page: args.page, nodeModules: args['node-modules'], chrome: args.chrome});
let samples;
try {
  const {page, errors} = session;
  samples = [];
  for (const t of times) {
    if (args.seek) await seek(page, t, false);
    const value = await page.evaluate(([expr, t]) => {
      const v = new Function('t', `return (${expr});`)(t);
      return JSON.parse(JSON.stringify(v, (k, x) => x instanceof Float32Array || x instanceof Float64Array ? Array.from(x) : x));
    }, [args.expr, t]);
    samples.push({t, value});
  }
  const report = {root: path.resolve(args.root), page: args.page || 'index.html', expr: args.expr, seek: Boolean(args.seek),
    fps: session.config.fps, samples, errors: [...new Set(errors)].slice(0, 12)};
  await fs.mkdir(path.dirname(path.resolve(args.out)), {recursive: true});
  await fs.writeFile(path.resolve(args.out), JSON.stringify(report));
  console.log(JSON.stringify({samples: samples.length, out: path.resolve(args.out), first: samples[0], errors: report.errors}));
} finally {
  await session.close();
}
