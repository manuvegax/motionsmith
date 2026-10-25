/* Render chosen instants of a seekable composition to JPEGs (t<seconds>.jpg), with or without exposure blur.
   This is the inspection workhorse: a grid over the whole piece, dense windows around transitions,
   and the same instant without blur to tell blur from geometry.

   node sample_frames.mjs --root <piece> --out <new-folder> [--every 0.5] [--window 7.0:7.6:0.1]... [--times 1.75,3.62] [--noblur]
   --frames 420:432[:1] picks exact frame centres (n + 0.5) / fps, the instants render_stream captures; --png is lossless;
   --png --alpha leaves the page background transparent (straight alpha), for overlays.
   Then: python contact_sheet.py <new-folder> --out <sheet.jpg>; look at it; delete the folder. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {openComposition, seek, clampTime, parseArgs} from './kit/runtime.mjs';

const usage = 'Usage: node sample_frames.mjs --root <piece> --out <folder> [--every s] [--window a:b:step]... [--times t1,t2] [--frames a:b[:step]] [--png [--alpha]] [--noblur] [--quality 88] [--page sub/index.html] [--node-modules dir] [--chrome exe]';
let args;
try { args = parseArgs(process.argv.slice(2), {flags: ['noblur', 'help', 'png', 'alpha'], repeat: ['window', 'frames']}); }
catch (error) { console.error(error.message + '\n' + usage); process.exit(2); }
if (args.help || !args.root || !args.out) { console.log(usage); process.exit(args.help ? 0 : 2); }
if (args.alpha && !args.png) { console.error('--alpha needs --png (JPEG has no alpha channel)'); process.exit(2); }

const out = path.resolve(args.out);
try {
  const existing = await fs.readdir(out);
  if (existing.length) { console.error(`Output folder is not empty: ${out}`); process.exit(2); }
} catch (error) { if (error.code !== 'ENOENT') throw error; }

const session = await openComposition({root: args.root, page: args.page, nodeModules: args['node-modules'], chrome: args.chrome});
try {
  const {page, config, errors} = session;
  const times = new Set();
  const add = t => { if (Number.isFinite(t)) times.add(Number(clampTime(t, config).toFixed(3))); };
  if (args.every) { const s = Number(args.every); for (let t = s / 2; t < config.duration; t += s) add(t); }
  for (const w of args.window || []) {
    const [a, b, step] = w.split(':').map(Number);
    if (!(step > 0) || !(b >= a)) throw new Error(`Bad --window ${w}; use start:end:step`);
    for (let t = a; t <= b + 1e-9; t += step) add(t);
  }
  for (const t of (args.times || '').split(',').filter(Boolean)) add(Number(t));
  const exact = new Map();   // frame centres are kept unrounded so stepped poses land on the same frame as in the render
  for (const f of args.frames || []) {
    const [a, b = a, step = 1] = f.split(':').map(Number);
    if (!Number.isInteger(a) || !Number.isInteger(b) || !(step >= 1) || b < a) throw new Error(`Bad --frames ${f}; use first:last[:step]`);
    for (let n = a; n <= b && n < config.frames; n += step) exact.set(n, (n + 0.5) / config.fps);
  }
  if (!times.size && !exact.size) throw new Error('No instants requested: use --every, --window, --times or --frames');
  await fs.mkdir(out, {recursive: true});
  const blur = !args.noblur, quality = Number(args.quality || 88), started = Date.now();
  const type = args.png ? 'png' : 'jpeg', ext = args.png ? 'png' : 'jpg';
  const shot = (file, t) => page.screenshot({path: path.join(out, file), type, timeout: 120000, ...(args.png ? {omitBackground: Boolean(args.alpha)} : {quality})});
  const list = [...times].sort((a, b) => a - b);
  for (const t of list) { await seek(page, t, blur); await shot(`t${t.toFixed(3)}.${ext}`, t); }
  for (const [n, t] of [...exact].sort((a, b) => a[0] - b[0])) { await seek(page, t, blur); await shot(`t${t.toFixed(4)}_f${n}.${ext}`, t); }
  const report = {root: path.resolve(args.root), out, blur, times: list, frames: [...exact.keys()], gpu: session.gpu, seconds: Number(((Date.now() - started) / 1000).toFixed(1)),
    config, chrome: session.executablePath, errors: [...new Set(errors)].slice(0, 12),
    note: 'Inspection frames: build a contact sheet, look at it, then delete this folder.'};
  await fs.writeFile(path.join(out, 'sample-report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({frames: list.length + exact.size, out, blur, seconds: report.seconds, errors: report.errors}));
  if (report.errors.some(e => e.startsWith('pageerror') || e.startsWith('webgl') || e.startsWith('network blocked'))) process.exitCode = 1;
} finally {
  await session.close();
}
