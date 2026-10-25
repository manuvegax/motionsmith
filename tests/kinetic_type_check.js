/* Property checks for scripts/kit/kinetic-type.js with a fake measure (no browser, no fonts).
   Run: node tests/kinetic_type_check.js (prints "ok N"). */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const MM = require(path.join(__dirname, '..', 'scripts', 'kit', 'motion-math.js'));
const K = require(path.join(__dirname, '..', 'scripts', 'kit', 'kinetic-type.js'));

let checks = 0;
const near = (a, b, tol, msg) => { checks++; assert.ok(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b} (tol ${tol})`); };
const ok = (cond, msg) => { checks++; assert.ok(cond, msg); };
const same = (a, b, msg) => { checks++; assert.deepEqual(a, b, msg); };
const throws = (fn, type, msg) => { checks++; assert.throws(fn, type, msg); };

// Fake font: every character is 10 px wide in the locked face; other faces are wider or narrower; height is 8 + 2.
const FACE_WIDTH = [1.1, .95, 1];
const measure = (s, face = 0) => ({width: [...s].length * 10 * (FACE_WIDTH[face] ?? 1), ascent: 8, descent: 2});

// ---- layout ----
{
  const line = K.layoutLine('ABC.', {measure, faces: 3});
  same(line.glyphs.map(g => g.ch), ['A', 'B', 'C', '.'], 'one glyph per character');
  same(line.glyphs.map(g => g.x), [5, 15, 25, 35], 'centres follow the pen, relative to the first glyph');
  near(line.width, 40, 1e-12, 'line width');
  near(line.glyphs[0].y, -3, 1e-12, 'centre sits above the baseline by (descent - ascent) / 2');
  near(line.height, 10, 1e-12, 'line height is ascent + descent');
  ok(line.lock === 2 && line.glyphs[0].lock === 2 && line.glyphs[0].faces === 3, 'the last face is the locked one');
  near(line.glyphs[0].width, 10, 1e-12, 'locked width');
  near(line.glyphs[0].faceWidths[0], 11, 1e-9, 'face 0 keeps its proportion at the settled height');
  near(line.glyphs[0].faceWidths[1], 9.5, 1e-9, 'face 1 likewise');
  const tracked = K.layoutLine('ABC.', {measure, faces: 3, track: 2});
  near(tracked.glyphs[1].x, 17, 1e-12, 'track adds space after every character');
  const spaced = K.layoutLine('A B', {measure, faces: 3});
  same(spaced.glyphs.map(g => g.ch), ['A', 'B'], 'spaces draw nothing');
  near(spaced.glyphs[1].x, 25, 1e-12, 'a space moves the pen');
  const graphemes = K.layoutLine('éx', {measure});
  same(graphemes.glyphs.length, 2, 'an accent stays with its letter (grapheme, not code point)');
  const fitted = K.layoutLine('VERSION', {measure, faces: 3, maxWidth: 35});
  near(fitted.width, 35, 1e-9, 'maxWidth scales the whole line to fit');
  near(fitted.scale, .5, 1e-9, 'the scale is reported');
  const empty = K.layoutLine('   ', {measure});
  same([empty.glyphs.length, empty.width], [0, 0], 'only spaces lays out nothing');
  throws(() => K.layoutLine('x'), TypeError, 'measure is required');
  throws(() => K.layoutLine('x', {measure, faces: 0}), RangeError, 'faces must be positive');
  throws(() => K.layoutLine('x', {measure, faces: 3, lock: 5}), RangeError, 'lock must be a face');
  throws(() => K.layoutLine('x', {measure, maxWidth: 0}), RangeError, 'maxWidth must be positive');
  const words = K.layoutWords(['ab', 'c'], {measure, face: 2, gap: 4});
  near(words.words[1].x, 24, 1e-12, 'words: second word after the first and the gap');
  near(words.width, 34, 1e-12, 'words: total width');
}

const glyphs = K.layoutLine('ABC.', {measure, faces: 3}).glyphs;
const at = (t, opts, list = glyphs) => K.run(list, t, opts);

// ---- run: entrance, rest, cascade ----
{
  same(at(-.01, {}), [], 'nothing before the cascade starts');
  const start = at(0, {});
  near(start[0].opacity, 0, 0, 'a letter is invisible at its first frame');
  near(start[0].y - glyphs[0].y, 340, 1e-9, 'a letter starts displaced by dy (y down)');
  const rest = at(10, {boil: 0});
  same(rest.length, 4, 'every letter is drawn at rest');
  ok(rest.every((c, i) => Math.abs(c.x - glyphs[i].x) < 1e-9 && Math.abs(c.angle) < 1e-9), 'at rest: home x, no angle');
  ok(rest.every((c, i) => Math.abs(c.y - glyphs[i].y) <= 4 + 1e-9), 'at rest only the float moves');
  ok(rest.every((c, i) => Math.abs(c.width - glyphs[i].faceWidths[2]) < 1e-9), 'at rest the scale pop has finished');
  const centred = K.run(glyphs, .02, {order: 'center', each: .022});
  same(centred.map(c => c.i).sort(), [1, 2], 'centre cascade: the middle two letters start first');
  const random = K.run(glyphs, .1, {order: 'random', seed: 3});
  same(random, K.run(glyphs, .1, {order: 'random', seed: 3}), 'random cascade is deterministic');
  same(glyphs.map((g, i) => MM.stagger(i, 4, {from: 'random', seed: 3, each: .022})).sort(), [0, .022, .044, .066], 'random cascade is a permutation of the delays');
  same(at(0, {step: 12, float: 0}).map(c => c.i), [0], 'stepped time: only the first letter exists at t=0');
  // Stepped poses: the entrance of one letter changes only at 12 fps boundaries.
  const ys = Array.from({length: 30}, (_, n) => K.run([glyphs[0]], (n + .5) / 60, {step: 12, span: .5, float: 0})[0].y);
  near(new Set(ys.map(y => y.toFixed(9))).size, 6, 0, 'stepped entrance: six poses in half a second at 12 fps');
  const smooth = Array.from({length: 30}, (_, n) => K.run([glyphs[0]], (n + .5) / 60, {span: .5, float: 0})[0].y);
  ok(new Set(smooth.map(y => y.toFixed(9))).size > 20, 'smooth time changes every frame');
  // Pop: the letter overshoots its width in the middle of the entrance.
  const widths = Array.from({length: 60}, (_, n) => K.run([glyphs[0]], n / 120, {span: .5, pop: .14})[0].width);
  ok(Math.max(...widths) > glyphs[0].faceWidths[2] * 1.05, 'pop: the scale overshoots while landing');
  // Angle eases to zero.
  near(K.run([glyphs[0]], .0, {angle: -.2, span: .5})[0].angle ?? 0, -.2, 1e-9, 'angle starts at its full value');
  near(K.run([glyphs[0]], 2, {angle: -.2, span: .5})[0].angle, 0, 1e-12, 'angle lands at zero');
}

// ---- face cycling, glitch, boil ----
{
  const faces = [0, 1, 2, 3, 4, 5].map(k => K.run([glyphs[0]], (k + .5) / 12, {cycle: .5})[0].face);
  same(faces, [0, 1, 2, 0, 1, 2], 'font cycle at 12 fps: faces 0, 1, 2, then again');
  near(K.run([glyphs[0]], .6, {cycle: .5})[0].face, 2, 0, 'after the cycle the letter shows the locked face');
  same(K.run(glyphs, 1, {span: .2}).map(c => c.face), [2, 2, 2, 2], 'no glitch: every letter settles');
  const glitched = K.run(glyphs, 1, {span: .2, glitch: 1});
  ok(glitched.every(c => c.face !== 2), 'glitch 1: every read letter jumps away from the locked face');
  ok(glitched.every(c => c.face >= 0 && c.face < 2), 'a glitch uses the other faces');
  // The float is smooth time by design, so these comparisons switch it off and test the stepped boil alone.
  same(K.run(glyphs, 1, {span: .2, boil: 10, float: 0}), K.run(glyphs, 1.01, {span: .2, boil: 10, float: 0}), 'boil holds within one 12 fps step');
  ok(JSON.stringify(K.run(glyphs, 1, {span: .2, boil: 10, float: 0})) !== JSON.stringify(K.run(glyphs, 1.1, {span: .2, boil: 10, float: 0})), 'boil changes between steps');
  same(K.run(glyphs, 1, {span: .2, glitch: .6, boil: 5}), K.run(glyphs, 1, {span: .2, glitch: .6, boil: 5}), 'hashes are deterministic');
  ok(K.hash2(3, 4) === K.hash2(3, 4) && K.hash2(3, 4) >= 0 && K.hash2(3, 4) < 1, 'hash2 is deterministic and in [0, 1)');
  near(K.stepOf(1 / 12), 1, 0, 'a step boundary belongs to the new step');
  near(K.stepOf(.0799), 0, 0, 'just before a boundary, the previous step');
  near(K.stepOf(1, 24), 24, 0, 'stepOf takes an fps');
}

// ---- echo ----
{
  const copies = K.echo(glyphs, .5, {from: 0, count: 3});
  near(copies.length, 12, 0, 'three copies of four letters');
  ok(copies.every(c => c.kind === 'outline'), 'echo commands are outlines');
  const first = copies.filter(c => c.i === 0).map(c => c.opacity);
  ok(first[0] < first[1] && first[1] < first[2], 'the copy nearest the letter is the most opaque');
  same(K.echo(glyphs, -1, {from: 0}), [], 'no echo before it starts');
  same(K.echo(glyphs, 2, {from: 0, until: 1}), [], 'no echo after it ends');
  ok(K.echo(glyphs, .01, {from: 0, count: 2, grow: .1}).every(c => c.width > 0), 'grow keeps widths positive');
}

// ---- marquee and ticker ----
{
  const cmds = [];
  for (let n = 0; n <= 100; n++) cmds.push(K.marquee(n * .1, {text: 'x', lineWidth: 300, frameWidth: 1080, y: 10}));
  for (const frame of cmds) {
    const sorted = frame.map(c => [c.x - c.width / 2, c.x + c.width / 2]).sort((a, b) => a[0] - b[0]);
    ok(sorted[0][0] <= 0 && sorted[sorted.length - 1][1] >= 1080, 'marquee copies cover the frame');
    ok(sorted.every((s, i) => i === 0 || Math.abs(s[0] - sorted[i - 1][1]) < 1e-9), 'marquee copies are contiguous');
  }
  const a = K.marquee(0, {lineWidth: 300, speed: 100})[1].x, b = K.marquee(1, {lineWidth: 300, speed: 100})[1].x;
  near(((a - b) % 300 + 300) % 300, 100, 1e-9, 'marquee moves left at speed px/s');
  throws(() => K.marquee(0, {}), RangeError, 'marquee needs lineWidth');
  same(K.ticker(-1, {at: 0, lineWidth: 200}), [], 'ticker waits for its start');
  const start = K.ticker(0, {at: 0, lineWidth: 200, frameWidth: 1080});
  near(start[0].x, 540 - 1080, 1e-9, 'band starts off screen to the left');
  const done = K.ticker(2, {at: 0, lineWidth: 200, frameWidth: 1080});
  near(done[0].x, 540, 1e-9, 'band settles in the middle');
  near(done[0].width, 1404, 1e-9, 'band is 1.3 frames wide');
  ok(done.slice(1).every(c => c.kind === 'text' && c.z > done[0].z - 1), 'text copies sit on the band');
  throws(() => K.ticker(0, {at: 0}), RangeError, 'ticker needs lineWidth');
}

// ---- typewriter ----
{
  const half = K.typewriter(.5, {at: 0, dur: 1, text: 'abc', x: 300, width: 200, height: 20});
  const text = half.find(c => c.kind === 'text');
  near(text.reveal, .5, 1e-12, 'half typed after half the duration');
  near(text.left, 200, 1e-12, 'the text is anchored at its left edge');
  near(text.width, 100, 1e-12, 'the visible part is the revealed fraction');
  near(text.x, 250, 1e-12, 'the visible part is centred on its own box');
  ok(half.some(c => c.kind === 'rect'), 'the cursor shows while typing on an even step');
  ok(!K.typewriter(.5 + 1 / 12, {at: 0, dur: 1, width: 200, height: 20, x: 300}).some(c => c.kind === 'rect'), 'the cursor blinks off on odd steps');
  ok(!K.typewriter(1.2, {at: 0, dur: 1, width: 200, height: 20, x: 300}).some(c => c.kind === 'rect'), 'no cursor after typing');
  near(K.typewriter(1.2, {at: 0, dur: 1, width: 200, height: 20, x: 300})[0].width, 200, 1e-12, 'the full line after typing');
  same(K.typewriter(-1, {at: 0, dur: 1, width: 200, height: 20, x: 300}), [], 'nothing before it starts');
}

// ---- karaoke ----
{
  const words = [{text: 'a', start: 0, end: 1}, {text: 'b', start: 1, end: 2}];
  same(K.karaoke(words, .5).map(w => w.state), ['active', 'pending'], 'first word active, second pending');
  near(K.karaoke(words, .5)[0].fill, .5, 1e-12, 'fill is the progress through the word');
  same(K.karaoke(words, 1.5).map(w => w.state), ['done', 'active'], 'first word done, second active');
  near(K.karaoke(words, 3)[1].fill, 1, 1e-12, 'a finished word is full');
  near(K.karaoke(words, .52, {fps: 12})[0].fill, .5, 1e-12, 'fps steps the karaoke fill');
  near(K.karaoke(words, .5, {ease: 'quad.in'})[0].fill, .25, 1e-12, 'fill can be eased');
  throws(() => K.karaoke([{text: 'x'}], 0), RangeError, 'karaoke words need timings');
}

// ---- determinism and purity ----
{
  const grid = Array.from({length: 40}, (_, n) => n / 20);
  const first = grid.map(t => K.run(glyphs, t, {cycle: .4, glitch: .3, boil: 3, order: 'random', seed: 11}));
  const again = grid.slice().reverse().map(t => K.run(glyphs, t, {cycle: .4, glitch: .3, boil: 3, order: 'random', seed: 11})).reverse();
  same(again, first, 'run is a pure function of t');
  checks += grid.length;
}

console.log(`ok ${checks}`);
