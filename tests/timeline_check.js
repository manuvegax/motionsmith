/* Property checks for scripts/kit/timeline.js. Run: node tests/timeline_check.js (prints "ok N"). */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const MM = require(path.join(__dirname, '..', 'scripts', 'kit', 'motion-math.js'));
const T = require(path.join(__dirname, '..', 'scripts', 'kit', 'timeline.js'));

let checks = 0;
const near = (a, b, tol, msg) => { checks++; assert.ok(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b} (tol ${tol})`); };
const ok = (cond, msg) => { checks++; assert.ok(cond, msg); };
const same = (a, b, msg) => { checks++; assert.deepEqual(a, b, msg); };
const throws = (fn, type, msg) => { checks++; assert.throws(fn, type, msg); };

// Linear default and value at the ends.
{
  const tr = T.track([{t: 0, v: 0}, {t: 1, v: 10}]);
  near(T.value(tr, .5), 5, 1e-12, 'linear midpoint');
  near(T.value(tr, 0), 0, 0, 'first key');
  near(T.value(tr, 1), 10, 0, 'last key');
  near(T.value(tr, -5), 0, 0, 'before the first key holds the first value');
  near(T.value(tr, 9), 10, 0, 'after the last key holds the last value');
  throws(() => T.value(tr, NaN), RangeError, 'NaN time is rejected');
}
// Named easings, bezier arrays and functions drive the same segment.
{
  const named = T.track([{t: 0, v: 0, ease: 'power2.out'}, {t: 2, v: 100}]);
  near(T.value(named, 1), MM.tween(1, 0, 2, 0, 100, 'power2.out'), 1e-9, 'named ease equals MotionMath.tween');
  const bez = T.track([{t: 0, v: 0, ease: [.25, .1, .25, 1]}, {t: 1, v: 1}]);
  near(T.value(bez, .25), MM.cubicBezier(.25, .1, .25, 1)(.25), 1e-9, 'cubic bezier array');
  const fn = T.track([{t: 0, v: 0, ease: u => u * u}, {t: 1, v: 10}]);
  near(T.value(fn, .5), 2.5, 1e-12, 'function ease');
  const stepped = T.track([{t: 0, v: 0, ease: 'steps(4)'}, {t: 1, v: 10}]);
  near(T.value(stepped, .6), 5, 1e-12, 'steps(4) holds in quarters');
  near(T.value(stepped, .24), 0, 1e-12, 'steps(4) holds the first quarter');
  throws(() => T.track([{t: 0, v: 0, ease: 'no.such'}, {t: 1, v: 1}]), Error, 'unknown ease name');
}
// Curves without overshoot never go backwards.
{
  const tr = T.track([{t: 0, v: 0, ease: 'power3.inOut'}, {t: 1, v: 1}]);
  let prev = -1, monotone = true;
  for (let i = 0; i <= 500; i++) { const v = T.value(tr, i / 500); if (v < prev - 1e-12) monotone = false; prev = v; }
  ok(monotone, 'power3.inOut is monotone');
}
// AE influence and speed.
{
  const easy = T.track([{t: 0, v: 0, ae: {}}, {t: 1, v: 1}]);
  for (const x of [.1, .3, .5, .7, .9]) near(T.value(easy, x), MM.EASINGS.easyEase(x), 1e-9, `easy ease at ${x}`);
  const fast = T.track([{t: 0, v: 0, ae: {outSpeed: 100}}, {t: 1, v: 100}]);
  const slope = (T.value(fast, .0005) - T.value(fast, 0)) / .0005;
  near(slope, 100, 2, 'outSpeed in units per second sets the starting speed');
  // A segment reads the out side of its first key and the in side of its second key (as After Effects does).
  const slow = T.track([{t: 0, v: 0, ae: {outInfluence: 80}}, {t: 1, v: 1, ae: {inInfluence: 80}}]);
  ok(T.value(slow, .15) < T.value(easy, .15) && T.value(slow, .85) > T.value(easy, .85), 'higher influence starts slower and lands longer');
  throws(() => T.track([{t: 0, v: 0, ae: {outInfluence: 0}}, {t: 1, v: 1}]), RangeError, 'influence 0 is rejected');
  throws(() => T.track([{t: 0, v: 0, ae: {inInfluence: 120}}, {t: 1, v: 1}]), RangeError, 'influence above 100 is rejected');
}
// Hold keys keep the value until the next key, then jump.
{
  const tr = T.track([{t: 0, v: 0, hold: true}, {t: 1, v: 10}]);
  near(T.value(tr, .5), 0, 0, 'hold keeps the value inside the segment');
  near(T.value(tr, .999), 0, 0, 'hold keeps the value until the next key');
  near(T.value(tr, 1), 10, 0, 'the next key arrives on its time');
  const three = T.track([{t: 0, v: 1}, {t: 1, v: 2, hold: true}, {t: 2, v: 5}]);
  near(T.value(three, 1.5), 2, 0, 'a later hold in a longer track');
  near(T.value(three, 2), 5, 0, 'the key after a hold');
}
// Stepped segments: time posterized at N fps inside the segment.
{
  const tr = T.track([{t: 0, v: 0, fps: 4}, {t: 1, v: 1}]);
  near(T.value(tr, .26), .25, 1e-12, 'fps 4 holds the pose of the quarter');
  near(T.value(tr, .499), .25, 1e-12, 'just before the second quarter');
  near(T.value(tr, .5), .5, 1e-12, 'the boundary belongs to the new pose');
  near(T.value(tr, .2499), 0, 1e-12, 'the first quarter starts at 0');
  let changes = 0, prev = T.value(tr, 0);
  for (let n = 1; n < 60; n++) { const v = T.value(tr, (n + .5) / 60); if (v !== prev) changes++; prev = v; }
  near(changes, 3, 0, 'four poses at 4 fps change three times in one second');
}
// Vectors: componentwise, copies returned, same shape required.
{
  const tr = T.track([{t: 0, v: [0, 0]}, {t: 1, v: [10, -20]}]);
  same(T.value(tr, .5), [5, -10], 'vector midpoint');
  const got = T.value(tr, .5);
  got[0] = 999;
  same(T.value(tr, .5), [5, -10], 'returned vectors are copies');
  throws(() => T.track([{t: 0, v: [0, 0]}, {t: 1, v: [1]}]), RangeError, 'vector lengths must match');
  throws(() => T.track([{t: 0, v: 0}, {t: 1, v: [1, 2]}]), RangeError, 'number and vector cannot mix');
}
// Validation of keys.
{
  throws(() => T.track([]), RangeError, 'empty track');
  throws(() => T.track([{t: 0, v: 0}, {t: 0, v: 1}]), RangeError, 'duplicate key times');
  throws(() => T.track([{t: 0, v: NaN}]), RangeError, 'NaN value');
  throws(() => T.track([{v: 1}]), RangeError, 'missing time');
  throws(() => T.track([{t: 0, v: 0, fps: 0}, {t: 1, v: 1}]), RangeError, 'fps must be positive');
}
// Keys may come unsorted; the result is the same.
{
  const sorted = T.track([{t: 0, v: 0}, {t: 1, v: 10}, {t: 2, v: 0}]);
  const shuffled = T.track([{t: 2, v: 0}, {t: 0, v: 0}, {t: 1, v: 10}]);
  for (const t of [.25, .75, 1.5, 1.9]) near(T.value(shuffled, t), T.value(sorted, t), 0, `unsorted keys at ${t}`);
}
// Scenes: values, markers and hits in one clock.
{
  const sc = T.scene({
    tracks: {x: [{t: 0, v: 0}, {t: 1, v: 100}], s: [{t: 0, v: 1, ease: 'power2.out'}, {t: 2, v: 2}]},
    markers: {intro: 0, cut: 1.5},
    hits: [{time: 1.5, amplitude: 1, role: 'boom'}, [.4, .5]],
  });
  near(sc.value('x', .5), 50, 1e-12, 'scene track value');
  same(Object.keys(sc.values(1)).sort(), ['s', 'x'], 'values lists every track');
  near(sc.marker('cut'), 1.5, 0, 'marker time');
  same(sc.hits.map(h => h.time), [.4, 1.5], 'hits sorted by time');
  same(sc.hits.map(h => h.role), ['hit', 'boom'], 'roles default to hit');
  near(sc.impulse(1.5, 9), MM.impulse(1.5, [{time: 1.5, amplitude: 1}, {time: .4, amplitude: .5}], 9), 1e-12, 'scene impulse uses all hits');
  near(sc.impulse(1.5, 9), 1, 1e-4, 'the impulse peaks at the hit');
  near(sc.duration, 2, 0, 'duration is the latest key, marker or hit');
  throws(() => sc.marker('nope'), RangeError, 'unknown marker');
  throws(() => sc.value('nope', 0), RangeError, 'unknown track');
  const times = [.1, .9, .4, 1.7];
  const forward = times.map(t => sc.value('s', t));
  const backward = times.slice().reverse().map(t => sc.value('s', t)).reverse();
  same(backward, forward, 'values do not depend on call order');
}
// Nested time: a track and a whole scene run at an offset and a speed.
{
  const base = T.track([{t: 0, v: 0}, {t: 4, v: 40}]);
  const child = T.nest(base, {offset: 2, speed: 2});
  near(T.value(child, 3), T.value(base, 2), 1e-12, 'nested track maps time: offset 2, speed 2');
  near(T.value(child, 1), 0, 0, 'nested track holds before its offset');
  near(T.value(child, 4), T.value(base, 4), 1e-12, 'nested track reaches the child end at parent time 4');
  throws(() => T.nest(base, {speed: 0}), RangeError, 'speed must be positive');
  throws(() => T.nest(base, {speed: -1}), RangeError, 'reversed speed is rejected');
  const sc = T.scene({tracks: {x: [{t: 0, v: 0}, {t: 2, v: 20}]}, markers: {cut: 3}, hits: [{time: 4, amplitude: 1}]});
  const parent = T.nest(sc, {offset: 1, speed: 2});
  near(parent.value('x', 2), sc.value('x', 2), 1e-12, 'nested scene value');
  near(parent.marker('cut'), 2.5, 1e-12, 'nested marker moves to parent time');
  near(parent.hits[0].time, 3, 1e-12, 'nested hit moves to parent time');
  near(parent.impulse(3, 9), 1, 1e-12, 'nested impulse peaks at the moved hit');
  near(parent.duration, 3, 1e-12, 'nested duration in parent time');
}
// Grouped helpers: hitList keeps plan.json fields and sorts; empty hits are fine.
{
  same(T.hitList([]), [], 'no hits');
  same(T.hitList([{time: 2, amplitude: .5, role: 'glass'}, [1, 1]]), [{time: 1, amplitude: 1, role: 'hit'}, {time: 2, amplitude: .5, role: 'glass'}], 'hit shapes');
  throws(() => T.hitList([{amplitude: 1}]), RangeError, 'a hit needs a time');
}
// Purity: the same t gives the same value on every call, with no state between calls.
{
  const tr = T.track([{t: 0, v: [0, 1], ease: 'power2.inOut'}, {t: 1, v: [3, -1], ae: {outSpeed: 2}}, {t: 2, v: [0, 0], fps: 12}]);
  const grid = Array.from({length: 61}, (_, i) => i / 30);
  const first = grid.map(t => T.value(tr, t));
  const again = grid.slice().reverse().map(t => T.value(tr, t)).reverse();
  same(again, first, 'pure in t');
  checks += grid.length;
}

console.log(`ok ${checks}`);
