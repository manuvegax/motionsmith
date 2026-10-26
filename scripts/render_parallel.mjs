/* Render a long piece in parallel chunks that resume: the same frames as render_stream.mjs, in a fraction of the time.

   node render_parallel.mjs --root <piece> --out final/piece.mp4 [--workers 3] [--chunk-seconds auto]
        [--audio assets/soundtrack.wav | --no-audio] [--crf 14] [--preset medium] [--keep-chunks] [--min-free-gb 2]

   The frames are split into chunks (by default about three per worker, at least 2 s); --workers chunks render at once, each in its own
   browser (render_stream.mjs --frames a:b). A chunk that fails is retried twice (a browser can die in a long capture).
   Finished chunks are kept in preview/chunks/<name>-<fingerprint>/ until the end, so an interrupted render resumes
   where it stopped; the fingerprint covers every file of the piece and the encoder settings, so a changed piece never
   reuses old chunks. The chunks are joined without re-encoding (they share the encoder settings and each starts on a
   keyframe), the audio is muxed over the whole, and the frame count of the result is checked against the plan.
   Every frame is a function of t, so a chunk boundary changes nothing in the picture.
   More workers is not always faster: they share one GPU. 2–4 is the useful range on a laptop; measure with --workers. */
import fs from 'node:fs/promises';
import {existsSync, readFileSync} from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn, spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {parseArgs} from './kit/runtime.mjs';

const usage = 'Usage: node render_parallel.mjs --root <piece> --out <file.mp4> [--workers 3] [--chunk-seconds s] [--audio file | --no-audio] [--crf 14] [--preset medium] [--keep-chunks] [--min-free-gb 2] [--node-modules dir] [--chrome exe]';
let args;
try { args = parseArgs(process.argv.slice(2), {flags: ['no-audio', 'keep-chunks', 'help']}); }
catch (error) { console.error(error.message + '\n' + usage); process.exit(2); }
if (args.help || !args.root || !args.out) { console.log(usage); process.exit(args.help ? 0 : 2); }

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(args.root);
const output = path.resolve(root, args.out);
if (existsSync(output)) { console.error(`Output already exists, choose a new name or archive it first: ${output}`); process.exit(2); }
for (const tool of ['ffmpeg', 'ffprobe']) {
  if (spawnSync(tool, ['-version'], {windowsHide: true}).error) { console.error(`${tool} is not on PATH`); process.exit(2); }
}
const workers = Math.max(1, Math.min(8, Number(args.workers ?? 3) | 0));
const crf = String(args.crf ?? 14), preset = args.preset || 'medium';
const plan = JSON.parse(readFileSync(path.join(root, 'plan.json'), 'utf8').replace(/^\uFEFF/, ''));
const fps = typeof plan.fps === 'string' && plan.fps.includes('/') ? plan.fps.split('/').map(Number).reduce((a, b) => a / b) : Number(plan.fps);
const frames = plan.duration_frames;
if (!(fps > 0) || !Number.isInteger(frames) || frames <= 0) { console.error('plan.json needs fps and duration_frames'); process.exit(2); }
let audio = null;
if (!args['no-audio']) {
  audio = path.resolve(root, args.audio || 'assets/soundtrack.wav');
  if (!existsSync(audio)) {
    if (args.audio) { console.error(`Audio not found: ${audio}`); process.exit(2); }
    audio = null;
  }
}

/* Fingerprint: every file of the piece (not renders or previews) plus the encoder settings. */
async function fingerprint() {
  const hash = crypto.createHash('sha256');
  const skip = new Set(['preview', 'final', 'node_modules', '.git']);
  async function walk(dir) {
    const entries = (await fs.readdir(dir, {withFileTypes: true})).sort((a, b) => a.name.localeCompare(b.name));
    for (const e of entries) {
      const full = path.join(dir, e.name);
      if (e.isDirectory()) { if (!skip.has(e.name)) await walk(full); continue; }
      if (/\.(mp4|mov)$/i.test(e.name)) continue;
      hash.update(path.relative(root, full)); hash.update(await fs.readFile(full));
    }
  }
  await walk(root);
  hash.update(JSON.stringify({crf, preset, renderer: readFileSync(path.join(here, 'render_stream.mjs'))}));
  return hash.digest('hex').slice(0, 12);
}

function probeFrames(file) {
  const r = spawnSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=nb_frames', '-of', 'csv=p=0', file],
    {encoding: 'utf8', windowsHide: true});
  return Number((r.stdout || '').trim());
}

function run(cmd, argv) {
  return new Promise(resolve => {
    const child = spawn(cmd, argv, {stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true});
    let log = '';
    child.stdout.on('data', d => { log = (log + d).slice(-4000); });
    child.stderr.on('data', d => { log = (log + d).slice(-4000); });
    child.on('close', code => resolve({code, log}));
    child.on('error', error => resolve({code: -1, log: String(error)}));
  });
}

const began = Date.now();
const key = await fingerprint();
const name = path.basename(output, path.extname(output));
const work = path.join(root, 'preview', 'chunks', `${name}-${key}`);
await fs.mkdir(work, {recursive: true});
const disk = await fs.statfs(work).catch(() => null);
const minFree = Number(args['min-free-gb'] ?? 2) * 2 ** 30;
if (disk && disk.bavail * disk.bsize < minFree) { console.error(`Less than ${args['min-free-gb'] ?? 2} GB free for the chunks`); process.exit(2); }

// About three chunks per worker keeps every browser busy to the end (a lone last chunk leaves the others idle);
// never under 2 s, where the browser start-up starts to weigh.
const chunkSeconds = args['chunk-seconds'] ? Number(args['chunk-seconds']) : Math.max(2, frames / fps / (workers * 3));
const size = Math.max(1, Math.round(chunkSeconds * fps));
const chunks = [];
for (let a = 0, i = 0; a < frames; a += size, i++) {
  chunks.push({i, a, b: Math.min(frames, a + size), file: path.join(work, `chunk-${String(i).padStart(4, '0')}.mp4`)});
}
const reused = [];
for (const c of chunks) {
  if (existsSync(c.file) && existsSync(c.file + '.done') && probeFrames(c.file) === c.b - c.a) { c.done = true; reused.push(c.i); }
  else { await fs.rm(c.file, {force: true}); await fs.rm(c.file + '.done', {force: true}); }
}
console.log(JSON.stringify({chunks: chunks.length, frames, workers, reused: reused.length, work}));

const failures = [];
let rendered = 0, chunkMinutes = 0;
const queue = chunks.filter(c => !c.done);
async function worker() {
  for (let c = queue.shift(); c; c = queue.shift()) {
    let ok = false, last = '';
    for (let attempt = 1; attempt <= 3 && !ok; attempt++) {
      await fs.rm(c.file, {force: true});
      const t0 = Date.now();
      const argv = [path.join(here, 'render_stream.mjs'), '--root', root, '--out', c.file, '--frames', `${c.a}:${c.b}`, '--no-audio',
        '--crf', crf, '--preset', preset, '--report', c.file + '.report.json', '--min-free-gb', '0.2'];
      if (args['node-modules']) argv.push('--node-modules', args['node-modules']);
      if (args.chrome) argv.push('--chrome', args.chrome);
      const r = await run(process.execPath, argv);
      ok = r.code === 0 && probeFrames(c.file) === c.b - c.a;
      last = r.log.split(/\r?\n/).filter(Boolean).slice(-2).join(' | ');
      if (ok) {
        chunkMinutes += (Date.now() - t0) / 60000;
        await fs.writeFile(c.file + '.done', JSON.stringify({frames: [c.a, c.b], attempt}));
      } else if (attempt < 3) console.error(`chunk ${c.i} (frames ${c.a}-${c.b - 1}) failed, retrying: ${last}`);
    }
    if (!ok) { failures.push({chunk: c.i, frames: [c.a, c.b], log: last}); continue; }
    rendered++;
    console.log(`chunk ${c.i + 1}/${chunks.length} done (${rendered + reused.length}/${chunks.length})`);
  }
}
await Promise.all(Array.from({length: Math.min(workers, queue.length)}, worker));
if (failures.length) {
  console.error(JSON.stringify({completed: false, failures, resume: 'run the same command again: finished chunks are kept'}, null, 2));
  process.exit(1);
}

// Join without re-encoding; the audio goes over the whole piece.
const list = path.join(work, 'list.txt');
await fs.writeFile(list, chunks.map(c => `file '${c.file.replace(/\\/g, '/').replace(/'/g, "'\\''")}'`).join('\n') + '\n');
await fs.mkdir(path.dirname(output), {recursive: true});
const seconds = frames / fps;
const join = ['-hide_banner', '-loglevel', 'error', '-n', '-f', 'concat', '-safe', '0', '-i', list];
if (audio) join.push('-i', audio);
join.push('-map', '0:v:0');
if (audio) join.push('-map', '1:a:0', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000');
join.push('-c:v', 'copy', '-t', String(seconds), '-movflags', '+faststart', output);
const joined = await run('ffmpeg', join);
const total = existsSync(output) ? probeFrames(output) : 0;
if (joined.code !== 0 || total !== frames) {
  await fs.rm(output, {force: true});
  console.error(`Join failed (${total} of ${frames} frames): ${joined.log}`);
  process.exit(1);
}
const bytes = (await fs.stat(output)).size;
const wall = (Date.now() - began) / 60000;
const report = {output, frames, fps, workers, chunks: chunks.length, chunk_frames: size, reused_chunks: reused.length,
  minutes: Number(wall.toFixed(1)), chunk_minutes: Number(chunkMinutes.toFixed(1)),
  speedup_vs_one_worker: rendered ? Number((chunkMinutes / Math.max(wall, 1e-6)).toFixed(2)) : null,
  crf: Number(crf), preset, audio: audio || 'none', size_mb: Number((bytes / 1e6).toFixed(1)),
  video_mbps: Number((bytes * 8 / 1e6 / seconds).toFixed(1)), fingerprint: key,
  note: 'speedup_vs_one_worker = summed chunk render time / wall time (an estimate: one browser alone runs a little faster)'};
if (report.video_mbps > 40) report.warnings = [`${report.video_mbps} Mbit/s: for upload render with --crf 18-20`];
const reportPath = path.join(root, 'preview', `${name}.render-report.json`);
await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
if (!args['keep-chunks']) await fs.rm(work, {recursive: true, force: true});
console.log(JSON.stringify({completed: true, ...report, report: reportPath}));
