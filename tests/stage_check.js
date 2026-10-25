/* Checks for the pure parts of scripts/kit/stage.js (wrap, breakLines, fitLines, trackSpeed) and its refusals.
   The render plumbing itself needs a browser: tests/test_recipes.py and tests/test_new_piece.py cover it.
   Run: node tests/stage_check.js (prints "ok N"). */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const kit = path.join(__dirname, '..', 'scripts', 'kit');
globalThis.MotionMath = require(path.join(kit, 'motion-math.js'));
globalThis.PostFX = require(path.join(kit, 'postfx-glsl.js'));
require(path.join(kit, 'stage.js'));
const S = globalThis.Stage;

let checks = 0;
const ok = (cond, msg) => { checks++; assert.ok(cond, msg); };
const same = (a, b, msg) => { checks++; assert.deepEqual(a, b, msg); };
const throws = (fn, type, msg) => { checks++; assert.throws(fn, type, msg); };

// A monospace measure: every character is half the size wide.
const mono = size => s => s.length * size * .5;
const measureAt = (s, size) => mono(size)(s);

// wrap: greedy, '|' forces a break, never splits a word, keeps every word in order.
{
  const text = 'the eye only sees what the mind is ready for';
  for (const width of [40, 120, 200, 400, 1e6]) {
    const lines = S.wrap(text, mono(20), width);
    same(lines.join(' '), text, `wrap keeps the words in order at ${width}`);
    ok(lines.every(l => mono(20)(l) <= width || !l.includes(' ')), `only a single long word may exceed ${width}`);
  }
  same(S.wrap('one two|three', mono(20), 1e6), ['one two', 'three'], 'pipe forces a break');
  same(S.wrap('  spaced   out  ', mono(20), 1e6), ['spaced out'], 'extra spaces collapse');
  same(S.wrap('', mono(20), 100), [], 'empty text, no lines');
}

// fitLines: fits the box, respects maxLines, balances the lines.
{
  const text = 'the eye only sees what the mind is ready for';
  for (const [width, height, maxLines] of [[600, 400, 4], [900, 300, 3], [300, 900, 5], [1200, 200, 2]]) {
    const r = S.fitLines(text, measureAt, {max: 200, min: 8, width, height, lineHeight: 1.1, maxLines});
    ok(r.lines.length <= maxLines, `at most ${maxLines} lines`);
    ok(r.widths.every(w => w <= width + 1e-9), 'every line inside the width');
    ok(r.lines.length * r.size * 1.1 <= height + 1e-9, 'the block inside the height');
    same(r.lines.join(' '), text, 'no word lost');
    ok(r.size <= 200 && r.size >= 8, 'size within the limits');
    // The largest size that fits at all (greedy gives the fewest lines); fitLines may go up to 20 % under it, and
    // only to find breaks with no penalty.
    let largest = 0;
    for (let size = 200; size >= 8 && !largest; size--) {
      const lines = S.wrap(text, s => measureAt(s, size), width);
      if (lines.length <= maxLines && lines.length * size * 1.1 <= height && lines.every(l => measureAt(l, size) <= width)) largest = size;
    }
    ok(r.size === largest || (r.bad === 0 && r.size >= Math.floor(.8 * largest)), `size ${r.size} vs largest ${largest}`);
  }
  // Greedy at 200 px would give 'aaaa bbbb cccc dddd' + 'eeee f'; balanced gives two lines of similar width.
  const balanced = S.fitLines('aaaa bbbb cccc dddd eeee f', measureAt, {max: 20, min: 20, width: 200, maxLines: 2});
  same(balanced.lines.length, 2, 'two lines');
  ok(Math.abs(balanced.widths[0] - balanced.widths[1]) <= 50, `balanced lines, no lonely last word: ${balanced.lines.join(' / ')}`);
  // Phrases: no line ends on a short word, no stub line, '|' still breaks.
  const endsShort = lines => lines.slice(0, -1).some(l => /^[\p{L}']{1,3}$/u.test(l.split(' ').pop()));
  for (const t of ['what the mind is ready for', 'la mente ve lo que está lista para ver', 'two decisions, one road']) {
    const r = S.fitLines(t, measureAt, {max: 150, min: 20, width: 900, height: 1100, maxLines: 4});
    ok(!endsShort(r.lines) && r.bad === 0, `phrase breaks: ${r.lines.join(' / ')}`);
    ok(r.widths.every(w => w >= .35 * 900), `no stub line: ${r.lines.join(' / ')}`);
  }
  same(S.fitLines('one|two three', measureAt, {max: 150, min: 20, width: 900}).lines, ['one', 'two three'], 'a forced break wins');
  same(S.breakLines('aaa bbb', mono(20), 10), null, 'no layout when a word is wider than the line');
  const tiny = S.fitLines('supercalifragilistic', measureAt, {max: 50, min: 10, width: 50});
  ok(tiny.size === 10, 'a word that never fits falls back to the minimum size');
}

// trackSpeed: the largest displacement of any tracked point; ignores missing points.
{
  same(S.trackSpeed({track: [[0, 0], [10, 10]]}, {track: [[3, 4], [10, 10]]}), 5, 'largest displacement');
  same(S.trackSpeed({track: [[0, 0]]}, {track: [[0, 0], [100, 100]]}), 0, 'only points present in both states');
  same(S.trackSpeed({}, {}), 0, 'no track, no speed');
  same(S.trackSpeed({track: [null, [0, 0]]}, {track: [[5, 5], [0, 6]]}), 6, 'null points are skipped');
}

// run() refuses a config without state() and draw().
throws(() => S.run({}), TypeError, 'state and draw are required');
throws(() => S.run({state: () => ({})}), TypeError, 'draw is required');
ok(S.FINISH.bloomMode === 'halo', 'halo bloom by default');

console.log(`ok ${checks}`);
