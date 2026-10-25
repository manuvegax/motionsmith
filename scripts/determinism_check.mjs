/* Determinism and readiness proof for a seekable composition.
   Seeks in a scrambled order (A -> late -> early -> A), compares the two captures of A, repeats A on a
   fresh page, and checks the fonts that must be loaded. Exit 1 on any mismatch, page error or missing font.

   node determinism_check.mjs --root <piece> [--times 2.4,11.7,0.35,2.4] [--font "430px <family>"]... [--report preview/determinism.json] */
import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {openComposition, newReadyPage, seek, clampTime, parseArgs} from './kit/runtime.mjs';

const usage = 'Usage: node determinism_check.mjs --root <piece> [--times a,b,c,a] [--font "430px <family>"]... [--noblur] [--report file] [--page sub/index.html] [--node-modules dir] [--chrome exe]';
let args;
try { args = parseArgs(process.argv.slice(2), {flags: ['noblur', 'help'], repeat: ['font']}); }
catch (error) { console.error(error.message + '\n' + usage); process.exit(2); }
if (args.help || !args.root) { console.log(usage); process.exit(args.help ? 0 : 2); }

const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const session = await openComposition({root: args.root, page: args.page, nodeModules: args['node-modules'], chrome: args.chrome});
let report;
try {
  const {page, config, errors, browser, pageUrl} = session;
  const d = config.duration;
  const times = (args.times ? args.times.split(',').map(Number) : [0.2 * d, 0.97 * d, 0.03 * d, 0.2 * d])
    .map(t => Number(clampTime(t, config).toFixed(3)));
  if (times.length < 3 || times[0] !== times[times.length - 1]) throw new Error('--times must start and end with the same instant');
  const blur = !args.noblur, captures = [];
  for (const t of times) { await seek(page, t, blur); captures.push({t, sha256: hash(await page.screenshot({timeout: 120000}))}); }
  const fresh = await newReadyPage(browser, pageUrl, errors, {width: config.width, height: config.height});
  await seek(fresh, times[0], blur);
  const freshHash = hash(await fresh.screenshot({timeout: 120000}));
  const fonts = {};
  // document.fonts.check() is true for families that were never declared: look for a FontFace that actually loaded.
  for (const spec of args.font || []) fonts[spec] = await page.evaluate(s => {
    const family = s.replace(/^.*?\d+(\.\d+)?(px|pt|em|rem)\s+/, '').replace(/["']/g, '').trim();
    const faces = [...document.fonts].filter(f => f.family.replace(/["']/g, '') === family);
    if (faces.length) return faces.some(f => f.status === 'loaded') ? 'loaded' : `declared but ${faces[0].status}`;
    return document.fonts.check(s) ? 'system or undeclared' : 'missing';
  }, spec);
  report = {root: path.resolve(args.root), config, blur, captures,
    same_page_match: captures[0].sha256 === captures[captures.length - 1].sha256,
    fresh_page_match: freshHash === captures[0].sha256, fonts,
    errors: [...new Set(errors)].slice(0, 12), gpu: session.gpu,
    limits: 'Proves repeatable pixels for these instants only; not smoothness, timing or artistic quality.'};
  report.deterministic = report.same_page_match && report.fresh_page_match;
} finally {
  await session.close();
}
if (args.report) {
  await fs.mkdir(path.dirname(path.resolve(args.report)), {recursive: true});
  await fs.writeFile(path.resolve(args.report), JSON.stringify(report, null, 2));
}
console.log(JSON.stringify(report, null, 2));
const badFont = Object.values(report.fonts).some(v => v !== 'loaded' && v !== 'system or undeclared');
if (!report.deterministic || report.errors.some(e => e.startsWith('pageerror') || e.startsWith('webgl') || e.startsWith('network blocked')) || badFont) process.exitCode = 1;
