/* Shared runtime for the capture kit: find Playwright and a Chromium without hard-coding a user profile,
   serve the composition, wait for its readiness contract and expose seek/screenshot helpers.

   Composition contract (own-HTML route):
     window.motionConfig = {width, height, fps, frames, duration, ...}
     window.motionReady  (or window.ready): a promise resolved with a plain value, never a GSAP timeline
     window.seek(t, blur = true): draws the exact state at absolute time t (seconds)
     window.motionInitialized (optional): set to true when everything above exists

   Run `node runtime.mjs --probe` to print what was resolved (exit 3 if Playwright is missing, 4 if no browser launches). */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {serveLocal} from './local-server.mjs';

const home = os.homedir();
const localAppData = process.env.LOCALAPPDATA || path.join(home, 'AppData', 'Local');

function hasPlaywright(dir) {
  return dir && fs.existsSync(path.join(dir, 'playwright', 'package.json'));
}

export function resolveNodeModules(explicit, startDir = process.cwd()) {
  const candidates = [explicit, process.env.MOTION_NODE_MODULES];
  for (let dir = path.resolve(startDir); ; dir = path.dirname(dir)) {
    candidates.push(path.join(dir, 'node_modules'));
    if (path.dirname(dir) === dir) break;
  }
  candidates.push(
    path.join(home, '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', 'node', 'node_modules'),
    process.env.APPDATA && path.join(process.env.APPDATA, 'npm', 'node_modules'),
    '/usr/local/lib/node_modules', '/usr/lib/node_modules');
  return candidates.find(hasPlaywright) || null;
}

export function resolveChrome(explicit) {
  for (const value of [explicit, process.env.MOTION_CHROME]) if (value && fs.existsSync(value)) return value;
  const roots = [path.join(localAppData, 'ms-playwright'), path.join(home, '.cache', 'ms-playwright'),
    path.join(home, 'Library', 'Caches', 'ms-playwright')];
  for (const root of roots) {
    if (!fs.existsSync(root)) continue;
    const builds = fs.readdirSync(root).filter(name => /^chromium-\d+$/.test(name))
      .sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]));
    for (const build of builds) {
      for (const rel of ['chrome-win64/chrome.exe', 'chrome-win/chrome.exe', 'chrome-linux/chrome',
        'chrome-mac/Chromium.app/Contents/MacOS/Chromium']) {
        const file = path.join(root, build, rel);
        if (fs.existsSync(file)) return file;
      }
    }
  }
  return null;   // let Playwright use its own default
}

export function loadChromium(nodeModules) {
  const dir = resolveNodeModules(nodeModules);
  if (!dir) throw new Error('Playwright not found. Pass --node-modules <dir> or set MOTION_NODE_MODULES.');
  const require = createRequire(path.join(dir, '__motion_kit__.cjs'));
  return {chromium: require('playwright').chromium, nodeModules: dir};
}

export const CHROME_ARGS = ['--disable-gpu-shader-disk-cache', '--disk-cache-size=1', '--disable-application-cache'];

/* Open the composition and wait for its contract. Returns {browser, page, server, config, errors, close}. */
export async function openComposition({root, page = 'index.html', nodeModules, chrome, timeoutMs = 60000, width = 1080, height = 1920}) {
  root = path.resolve(root);
  const pageFile = path.resolve(root, page);
  if (!pageFile.startsWith(root + path.sep) || !fs.existsSync(pageFile)) throw new Error(`Page not found inside ${root}: ${page}`);
  const {chromium} = loadChromium(nodeModules);
  const executablePath = resolveChrome(chrome) || undefined;
  const browser = await chromium.launch({headless: true, executablePath, args: CHROME_ARGS});
  const server = await serveLocal(root);
  const errors = [];
  const close = async () => { await browser.close().catch(() => {}); await server.close().catch(() => {}); };
  try {
    const pageUrl = server.url + path.relative(root, pageFile).split(path.sep).map(encodeURIComponent).join('/');
    const tab = await newReadyPage(browser, pageUrl, errors, {timeoutMs, width, height});
    const config = await tab.evaluate(() => window.motionConfig);
    const gpu = await gpuInfo(tab);
    return {browser, page: tab, server, pageUrl, config, errors, close, gpu, executablePath: executablePath || 'playwright default'};
  } catch (error) {
    await close();
    throw new Error(`${error.message}${errors.length ? '\nPage errors:\n' + errors.slice(0, 6).join('\n') : ''}`);
  }
}

/* Environment switches read by every capture script:
   MOTION_ALLOW_NETWORK=1  let the page load from the internet (blocked by default: a render must not depend on it);
   MOTION_MAX_SAMPLES=N    cap motion-blur samples per frame for fast drafts (kit/stage.js reads it). */
export async function newReadyPage(browser, url, errors, {timeoutMs = 60000, width = 1080, height = 1920} = {}) {
  const page = await browser.newPage({viewport: {width, height}, deviceScaleFactor: 1});
  const origin = new URL(url).origin;
  if (process.env.MOTION_ALLOW_NETWORK !== '1') {
    await page.route('**/*', route => {
      const target = route.request().url();
      if (target.startsWith(origin + '/') || target === origin) return route.continue();
      if (/^https:\/\/cdn\.jsdelivr\.net\/npm\/gsap@[\d.]+\/dist\/gsap\.min\.js$/.test(target)) return route.abort('blockedbyclient');   // HyperFrames-only
      errors.push(`network blocked: ${target.slice(0, 300)} (pieces load only their own files; MOTION_ALLOW_NETWORK=1 allows it)`);
      return route.abort('blockedbyclient');
    });
  }
  const cap = Number(process.env.MOTION_MAX_SAMPLES);
  if (Number.isInteger(cap) && cap >= 1) await page.addInitScript(n => { window.motionOverrides = {maxSamples: n}; }, cap);
  page.on('pageerror', e => errors.push('pageerror: ' + String(e).slice(0, 1500)));
  // A failed request is reported with its URL; the browser's own favicon probe is not an asset of the piece.
  page.on('console', m => {
    const text = m.text();
    if (m.type() === 'error' && !text.startsWith('Failed to load resource')) errors.push('console: ' + text.slice(0, 600));
    // Chrome reports broken GL state (feedback loops, invalid operations) as warnings: they are errors for a render.
    else if (m.type() === 'warning' && /^(\[\.WebGL|WebGL|GL_|GL ERROR)/.test(text)) errors.push('webgl: ' + text.slice(0, 600));
  });
  page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('/favicon.ico')) errors.push(`http ${r.status()}: ${r.url()}`); });
  // <audio>/<video> elements abort their own range requests while buffering: that is not a failure.
  page.on('requestfailed', r => {
    const media = /\.(wav|mp3|m4a|mp4|webm)(\?|$)/i.test(r.url()) && (r.failure()?.errorText || '').includes('ERR_ABORTED');
    const blocked = (r.failure()?.errorText || '').includes('BLOCKED_BY_CLIENT');   // already reported as network blocked
    if (!media && !blocked && !r.url().endsWith('/favicon.ico')) errors.push(`request failed: ${r.url()} ${r.failure()?.errorText || ''}`);
  });
  await page.goto(url);
  await page.waitForFunction(() => typeof window.seek === 'function', null, {timeout: timeoutMs});
  await page.evaluate(async ms => {
    const ready = window.motionReady || window.ready;
    if (ready && typeof ready.then === 'function') {
      await Promise.race([ready, new Promise((_, reject) => setTimeout(() => reject(new Error(
        'readiness promise did not settle (resolving it with a GSAP timeline makes it wait for the timeline)')), ms))]);
    }
  }, timeoutMs);
  await page.waitForFunction(() => !('motionInitialized' in window) || window.motionInitialized === true, null, {timeout: timeoutMs});
  const config = await page.evaluate(() => window.motionConfig);
  for (const key of ['width', 'height', 'fps', 'frames', 'duration']) {
    if (!config || !(Number(config[key]) > 0)) throw new Error(`window.motionConfig.${key} must be a positive number`);
  }
  if (config.width !== width || config.height !== height) await page.setViewportSize({width: config.width, height: config.height});
  return page;
}

/* Which GPU path rendered the frames (goes into the reports: half-float support changes bloom and bokeh). */
export async function gpuInfo(page) {
  return page.evaluate(() => {
    const gl = document.createElement('canvas').getContext('webgl');
    if (!gl) return {webgl: false};
    const debug = gl.getExtension('WEBGL_debug_renderer_info');
    return {webgl: true, renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
      halfFloatTargets: Boolean(gl.getExtension('OES_texture_half_float') && gl.getExtension('EXT_color_buffer_half_float'))};
  });
}

export function clampTime(t, config) { return Math.min(Math.max(t, 0), config.duration - 1e-6); }

export async function seek(page, t, blur = true) { await page.evaluate(([t, b]) => window.seek(t, b), [t, blur]); }

/* Tiny argv parser: --key value, --flag, repeatable keys collected as arrays. */
export function parseArgs(argv, {flags = [], repeat = []} = {}) {
  const out = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith('--')) throw new Error(`Unexpected argument: ${arg}`);
    const key = arg.slice(2);
    if (flags.includes(key)) { out[key] = true; continue; }
    const value = argv[++i];
    if (value === undefined) throw new Error(`Missing value for --${key}`);
    if (repeat.includes(key)) (out[key] ||= []).push(value); else out[key] = value;
  }
  return out;
}

if (process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url && process.argv.includes('--probe')) {
  // Exit 3: no Playwright. Exit 4: Playwright but no browser that launches (e.g. `npx playwright install chromium`
  // never ran). Browser tests skip on any non-zero exit.
  const nodeModules = resolveNodeModules(null, path.dirname(fileURLToPath(import.meta.url)));
  const report = {node: process.version, node_modules: nodeModules, chrome: resolveChrome(null), launch: false};
  if (!nodeModules) process.exitCode = 3;
  else {
    try {
      const {chromium} = loadChromium(nodeModules);
      const browser = await chromium.launch({headless: true, executablePath: resolveChrome(null) || undefined, args: CHROME_ARGS});
      await browser.close();
      report.launch = true;
    } catch (error) {
      report.error = String(error.message || error).split('\n')[0];
      process.exitCode = 4;
    }
  }
  console.log(JSON.stringify(report));
}
