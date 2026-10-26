/* Render a seekable composition straight into FFmpeg (PNG over a pipe): no frame sequence on disk.
   Frame n is captured at its centre, t = (n + 0.5) / fps. Refuses to overwrite the output.

   node render_stream.mjs --root <piece> --out final/pieza.mp4 [--audio assets/soundtrack.wav | --no-audio]
        [--crf 14] [--preset medium] [--start 6.4 --end 8.8] [--min-free-gb 1]
   --start/--end render a proxy of the hardest stretch with its audio slice, before the full render. */
import fs from 'node:fs/promises';
import {existsSync} from 'node:fs';
import path from 'node:path';
import {spawn, spawnSync} from 'node:child_process';
import {once} from 'node:events';
import {openComposition, seek, parseArgs} from './kit/runtime.mjs';

const usage = 'Usage: node render_stream.mjs --root <piece> --out <file.mp4> [--audio file | --no-audio] [--crf 14] [--preset medium] [--start s] [--end s] [--min-free-gb 1] [--page sub/index.html] [--node-modules dir] [--chrome exe]';
let args;
try { args = parseArgs(process.argv.slice(2), {flags: ['no-audio', 'help']}); }
catch (error) { console.error(error.message + '\n' + usage); process.exit(2); }
if (args.help || !args.root || !args.out) { console.log(usage); process.exit(args.help ? 0 : 2); }

const root = path.resolve(args.root);
const output = path.resolve(root, args.out);
if (existsSync(output)) { console.error(`Output already exists, choose a new name or archive it first: ${output}`); process.exit(2); }
await fs.mkdir(path.dirname(output), {recursive: true});
const minFree = Number(args['min-free-gb'] ?? 1) * 2 ** 30;
const disk = await fs.statfs(path.dirname(output)).catch(() => null);
if (disk && disk.bavail * disk.bsize < minFree) {
  console.error(`Only ${(disk.bavail * disk.bsize / 2 ** 30).toFixed(2)} GB free next to the output; need ${args['min-free-gb'] ?? 1} GB`);
  process.exit(2);
}
let audio = null;
if (!args['no-audio']) {
  audio = path.resolve(root, args.audio || 'assets/soundtrack.wav');
  if (!existsSync(audio)) {
    if (args.audio) { console.error(`Audio not found: ${audio}`); process.exit(2); }
    audio = null;
  }
}

if (spawnSync('ffmpeg', ['-version'], {windowsHide: true}).error) { console.error('ffmpeg is not on PATH: install it or add it before rendering'); process.exit(2); }
const session = await openComposition({root, page: args.page, nodeModules: args['node-modules'], chrome: args.chrome});
let ffmpeg, current = null;
try {
  const {page, config, errors} = session;
  const start = Number(args.start ?? 0), end = Number(args.end ?? config.duration);
  const first = Math.round(start * config.fps), last = Math.min(config.frames, Math.round(end * config.fps));
  if (!(last > first)) throw new Error(`Empty frame range ${first}..${last}`);
  const count = last - first, seconds = count / config.fps;
  const ffArgs = ['-hide_banner', '-loglevel', 'warning', '-n', '-f', 'image2pipe', '-vcodec', 'png',
    '-framerate', String(config.fps), '-i', 'pipe:0'];
  if (audio) ffArgs.push('-ss', String(first / config.fps), '-t', String(seconds), '-i', audio);
  ffArgs.push('-map', '0:v:0');
  if (audio) ffArgs.push('-map', '1:a:0', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000');
  // BT.709 matrix *and* tags: untagged BT.601 (FFmpeg's default for RGB input) turns #ff422e into (255,81,40) in
  // players that assume HD colour. setparams writes primaries/transfer, which the -color_* flags alone did not.
  ffArgs.push('-vf', 'scale=out_color_matrix=bt709:out_range=tv,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv',
    '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv');
  ffArgs.push('-c:v', 'libx264', '-preset', args.preset || 'medium', '-crf', String(args.crf ?? 14), '-pix_fmt', 'yuv420p',
    '-frames:v', String(count), '-t', String(seconds), '-movflags', '+faststart', output);
  ffmpeg = spawn('ffmpeg', ffArgs, {stdio: ['pipe', 'ignore', 'pipe'], windowsHide: true});
  let log = '', pipeError = null;
  ffmpeg.stderr.on('data', d => { log = (log + d.toString()).slice(-12000); });
  ffmpeg.stdin.on('error', e => { pipeError = e; });
  const finished = new Promise((resolve, reject) => { ffmpeg.on('error', reject); ffmpeg.on('close', resolve); });
  finished.catch(() => {});   // awaited later; this only keeps an early spawn error from crashing as unhandled
  const began = Date.now();
  for (let n = first; n < last; n++) {
    if (pipeError) throw pipeError;
    current = n;
    let frame;
    for (let attempt = 1; ; attempt++) {          // one retry: a long capture can hit a transient browser hiccup
      try { await seek(page, (n + 0.5) / config.fps, true); frame = await page.screenshot({type: 'png', timeout: 120000}); break; }
      catch (error) { if (attempt >= 2) throw error; console.error(`Frame ${n}: ${error.message.split(/\r?\n/)[0]} — retrying once`); }
    }
    if (!ffmpeg.stdin.write(frame)) await once(ffmpeg.stdin, 'drain');
    if ((n - first) % 60 === 0) console.log(`Captured ${n - first + 1}/${count} frames`);
  }
  ffmpeg.stdin.end();
  const code = await finished;
  if (code !== 0) throw new Error(`ffmpeg exit ${code}: ${log}`);
  const report = {output, frames: count, first_frame: first, fps: config.fps, width: config.width, height: config.height,
    proxy: first !== 0 || last !== config.frames, audio: audio || 'none', crf: Number(args.crf ?? 14),
    capture: 'Playwright screenshots of window.seek((n+0.5)/fps) streamed to ffmpeg; no image sequence on disk',
    samples: config.samples, shutter_degrees: config.shutter_degrees, minutes: Number(((Date.now() - began) / 60000).toFixed(1)),
    color: 'BT.709 matrix and tags, limited range', chrome: session.executablePath, gpu: session.gpu,
    page_errors: [...new Set(errors)], ffmpeg_log: log};
  // Weight: grain and fine texture at a low CRF make huge files that every platform re-encodes anyway.
  const bytes = (await fs.stat(output)).size, clipSeconds = count / config.fps;
  report.size_mb = Number((bytes / 1e6).toFixed(1));
  report.video_mbps = Number((bytes * 8 / 1e6 / Math.max(clipSeconds, 1e-6)).toFixed(1));
  if (report.video_mbps > 40) report.warnings = [`${report.video_mbps} Mbit/s (${report.size_mb} MB): grain or texture at CRF ${report.crf}; the platform re-encodes to a few Mbit/s, so for upload render with --crf 18-20 (a fraction of the size, the same on the phone)`];
  // final/ keeps only the delivery: the report goes to the sibling preview/ (of the served piece, or of the
  // other piece the video is written into); a video written anywhere else gets the report next to it.
  const insideRoot = output.startsWith(root + path.sep), outDir = path.dirname(output);
  const reportDir = insideRoot ? path.join(root, 'preview') : path.basename(outDir) === 'final' ? path.join(path.dirname(outDir), 'preview') : outDir;
  const reportPath = path.join(reportDir, path.basename(output, path.extname(output)) + '.render-report.json');
  await fs.mkdir(path.dirname(reportPath), {recursive: true});
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({completed: true, output, frames: count, size_mb: report.size_mb, video_mbps: report.video_mbps,
    report: reportPath, page_errors: report.page_errors, warnings: report.warnings || []}));
  if (report.page_errors.some(e => e.startsWith('pageerror') || e.startsWith('webgl') || e.startsWith('network blocked'))) process.exitCode = 1;
} catch (error) {
  console.error(`Render failed${current === null ? '' : ` at frame ${current}`}: ${error.stack || error}`);
  if (ffmpeg && ffmpeg.exitCode === null) {
    ffmpeg.kill();
    await Promise.race([once(ffmpeg, 'close'), new Promise(resolve => setTimeout(resolve, 10000))]);   // let it release the file
  }
  // A partial file must not look like a delivery; a failed clean-up must not hide the real error.
  for (let attempt = 0; attempt < 5; attempt++) {
    try { await fs.rm(output, {force: true}); break; }
    catch (cleanup) { if (attempt === 4) console.error(`Could not delete the partial file, delete it by hand: ${output} (${cleanup.code})`); else await new Promise(r => setTimeout(r, 1000)); }
  }
  process.exitCode = 1;
} finally {
  await session.close();
}
