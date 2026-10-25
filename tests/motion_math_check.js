/* Property checks for scripts/kit/motion-math.js. Run: node tests/motion_math_check.js (prints "ok N"). */
'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const M = require(path.join(__dirname, '..', 'scripts', 'kit', 'motion-math.js'));

let checks = 0;
const near = (a, b, tol, msg) => { checks++; assert.ok(Math.abs(a - b) <= tol, `${msg}: ${a} vs ${b} (tol ${tol})`); };
const ok = (cond, msg) => { checks++; assert.ok(cond, msg); };

// Every named easing starts at 0 and ends at 1.
for (const [name, f] of Object.entries(M.EASINGS)) {
  near(f(0), 0, 1e-9, `${name}(0)`);
  near(f(1), 1, 1e-9, `${name}(1)`);
}
// Curves without overshoot never go backwards.
for (const name of ['linear', 'power1.out', 'power2.in', 'power3.out', 'power4.inOut', 'expo.out', 'expo.inOut', 'sine.inOut',
  'circ.out', 'easyEase', 'easyEase.in', 'easyEase.out', 'css.ease']) {
  const f = M.EASINGS[name];
  let prev = -1e-12, monotone = true;
  for (let i = 0; i <= 1000; i++) { const v = f(i / 1000); if (v < prev - 1e-9) monotone = false; prev = v; }
  ok(monotone, `${name} is monotone`);
}
ok(Math.max(...Array.from({length: 1001}, (_, i) => M.EASINGS['back.out'](i / 1000))) > 1.05, 'back.out overshoots');
ok(Math.max(...Array.from({length: 1001}, (_, i) => M.EASINGS['elastic.out'](i / 1000))) > 1.1, 'elastic.out overshoots');

// cubicBezier against an independent dense parametric sampling of CSS "ease".
{
  const f = M.cubicBezier(.25, .1, .25, 1);
  const x1 = .25, y1 = .1, x2 = .25, y2 = 1;
  const bx = t => 3 * (1 - t) * (1 - t) * t * x1 + 3 * (1 - t) * t * t * x2 + t * t * t;
  const by = t => 3 * (1 - t) * (1 - t) * t * y1 + 3 * (1 - t) * t * t * y2 + t * t * t;
  for (const x of [.1, .25, .5, .75, .9]) {
    let best = 0, err = 1;
    for (let i = 0; i <= 200000; i++) { const t = i / 200000, e = Math.abs(bx(t) - x); if (e < err) { err = e; best = t; } }
    near(f(x), by(best), 2e-4, `css ease at ${x}`);
  }
  near(f(.5), .8024, 2e-3, 'css ease at 0.5 ≈ 0.8024');
  assert.throws(() => M.cubicBezier(1.2, 0, .5, 1), RangeError);
}
// AE Easy Ease (33.33 % influence, zero speed) is cubic-bezier(1/3, 0, 2/3, 1).
{
  const a = M.aeEase(), b = M.cubicBezier(.3333, 0, .6667, 1);
  for (const x of [.1, .3, .5, .7, .9]) near(a(x), b(x), 1e-6, `easy ease at ${x}`);
  const snappy = M.aeEase({outInfluence: 80, inInfluence: 80});
  ok(snappy(.15) < a(.15) && snappy(.85) > a(.85), 'higher influence starts slower and lands longer');
  near(M.aeSpeedMultiple(500, 1000, 2), 1, 1e-12, 'speed equal to average is multiple 1');
}
// AE remaps.
near(M.linear(5, 0, 10, 0, 100), 50, 1e-9, 'linear 5-arg');
near(M.linear(.25, 0, 100), 25, 1e-9, 'linear 3-arg');
near(M.ease(0, 0, 1, 10, 20), 10, 1e-9, 'ease start');
near(M.ease(1, 0, 1, 10, 20), 20, 1e-9, 'ease end');
assert.deepEqual(M.linear(.5, [0, 0], [10, 20]), [5, 10]); checks++;
near(M.tween(1.5, 1, 2, 0, 100, 'linear'), 50, 1e-9, 'tween');

// Springs: start at rest, settle, and overshoot as theory says (ζ = 0.5 → 16.3 %).
{
  const opts = {freq: 1.7, damping: .5};
  near(M.spring(0, opts), 0, 1e-12, 'spring starts at 0');
  near(M.spring(10, opts), 1, 1e-4, 'spring settles');
  let peak = 0;
  for (let i = 0; i < 4000; i++) peak = Math.max(peak, M.spring(i / 1000, opts));
  near(peak - 1, M.springOvershoot(.5), 2e-3, 'measured overshoot equals theory');
  near(M.springOvershoot(.5), .163, 2e-3, 'ζ = 0.5 overshoots ≈ 16.3 %');
  let crit = 0, over = 0, monotone = true, prev = 0;
  for (let i = 0; i < 4000; i++) {
    const t = i / 1000;
    crit = Math.max(crit, M.spring(t, {freq: 2, damping: 1}));
    const v = M.spring(t, {freq: 2, damping: 2}); over = Math.max(over, v);
    if (v < prev - 1e-12) monotone = false; prev = v;
  }
  ok(crit <= 1 + 1e-9, 'critical damping does not overshoot');
  ok(over <= 1 + 1e-9 && monotone, 'overdamped is monotone without overshoot');
  const physical = M.springFromPhysics({stiffness: 100, damping: 20, mass: 1});
  near(physical.freq, 10 / M.TAU, 1e-12, 'stiffness → freq');
  near(physical.damping, 1, 1e-12, 'critical physical damping');
  const settle = M.springSettle(opts);
  near(M.spring(settle * 1.6, opts), 1, .02, 'settle time puts the response within tolerance');
  near(M.inertialBounce(0, 500), 0, 1e-12, 'bounce starts at 0');
  ok(Math.abs(M.inertialBounce(2, 500)) < 1e-4, 'bounce decays');
}
// Follower table: deterministic, seekable, converges to a constant target, interpolates.
{
  const make = () => M.followerTable({from: 0, to: 3, target: () => [100, -50], omega: M.TAU * 2, zeta: .6, initial: [0, 0]});
  const a = make(), b = make();
  assert.deepEqual(a.sample(1.234), b.sample(1.234)); checks++;
  const end = a.sample(3).value;
  near(end[0], 100, .05, 'follower x converges'); near(end[1], -50, .05, 'follower y converges');
  const mid = a.sample(0.5).value, before = a.sample(0.5 - a.dt / 2).value;
  ok(Number.isFinite(mid[0]) && Math.abs(mid[0] - before[0]) < 2, 'follower interpolates smoothly');
  const scalar = M.followerTable({from: 0, to: 1, target: t => t < .2 ? 0 : 1, omega: 30, zeta: .5});
  ok(typeof scalar.sample(.5).value === 'number', 'scalar follower returns numbers');
}
// Deterministic noise and randomness.
{
  near(M.wiggle(1.37, {seed: 4}), M.wiggle(1.37, {seed: 4}), 0, 'wiggle is deterministic');
  ok(M.wiggle(1.37, {seed: 4}) !== M.wiggle(1.37, {seed: 5}), 'seeds differ');
  let max = 0, jump = 0, prev = M.wiggle(0, {freq: 3, amp: 10, octaves: 3});
  for (let i = 1; i < 6000; i++) {
    const v = M.wiggle(i / 1000, {freq: 3, amp: 10, octaves: 3});
    max = Math.max(max, Math.abs(v)); jump = Math.max(jump, Math.abs(v - prev)); prev = v;
  }
  ok(max <= 10 * (1 + .5 + .25) + 1e-9, 'wiggle bounded by its octave sum');
  ok(jump < 1, 'wiggle is continuous (no jumps between 1 ms steps)');
  const xy = M.wiggle(2, {dims: 2, amp: 5});
  ok(Array.isArray(xy) && xy[0] !== xy[1], 'axes are independent');
  const r1 = M.rng(7), r2 = M.rng(7);
  for (let i = 0; i < 20; i++) { const v = r1(); near(v, r2(), 0, 'rng reproducible'); ok(v >= 0 && v < 1, 'rng range'); }
  for (let i = -50; i < 50; i++) { const h = M.hash(i, 3); ok(h >= 0 && h < 1, 'hash range'); }
}
// Loops and stagger.
{
  near(M.loop(2.5, 1), .5, 1e-12, 'cycle');
  near(M.loop(1.25, 1, 'pingpong'), .75, 1e-12, 'pingpong going back');
  near(M.loop(-.25, 1), .75, 1e-12, 'negative time cycles');
  const n = 9;
  for (let i = 0; i < n; i++) near(M.stagger(i, n, {from: 'center'}), M.stagger(n - 1 - i, n, {from: 'center'}), 1e-12, 'center is symmetric');
  near(M.stagger(4, n, {from: 'center'}), 0, 1e-12, 'center starts at the middle');
  near(M.stagger(8, n, {each: .1}), .8, 1e-12, 'start: linear delays');
  const randomDelays = Array.from({length: n}, (_, i) => M.stagger(i, n, {from: 'random', seed: 3, each: 1})).sort((a, b) => a - b);
  assert.deepEqual(randomDelays, Array.from({length: n}, (_, i) => i)); checks++;
  near(M.stagger(4, 9, {grid: [3, 3], from: 'center'}), 0, 1e-12, 'grid centre');
  near(M.stagger(0, 9, {grid: [3, 3], from: 'center', each: 1}), Math.SQRT2, 1e-12, 'grid corner distance');
  near(M.stagger(8, n, {each: .1, curve: 'power2.out'}), .8, 1e-12, 'curved stagger keeps the total');
  near(M.delay(t => t * 2, .5)(1), 1, 1e-12, 'delay = valueAtTime(time - lag)');
}
// Speed ramp (time remap).
{
  const identity = M.speedRamp(() => 1, {to: 4});
  near(identity(2.5), 2.5, 1e-9, 'speed 1 is identity');
  const slow = M.speedRamp(() => .5, {to: 4});
  near(slow(2), 1, 1e-9, 'speed 0.5 halves');
  const ramp = M.speedRamp(t => t < 1 ? 1 : .25, {to: 3});
  ok(ramp(2) > 1 && ramp(2) < 1.3, 'slow motion after 1 s');
}
// Exposure sampling with AE shutter semantics.
{
  const s = M.exposureTimes(1, {fps: 60, shutter: 180, samples: 16});
  near(s.length, 16, 0, 'sample count');
  const mean = s.reduce((a, x) => a + x.t, 0) / s.length;
  near(mean, 1, 1e-12, 'phase −shutter/2 centres the blur');
  near(s[15].t - s[0].t, (15 / 16) * (180 / 360 / 60), 1e-12, 'span matches the shutter');
  ok(M.exposureTimes(1, {fps: 60, shutter: 180, phase: 0, samples: 8}).every(x => x.t >= 1), 'phase 0 trails after t');
  near(s.reduce((a, x) => a + x.weight, 0), 1, 1e-12, 'weights sum to 1');
  near(M.pxPerExposure(1200, 180, 60), 10, 1e-12, 'px per exposure');
  ok(M.blurAdvice(.5).startsWith('none') && M.blurAdvice(100).startsWith('stylized'), 'blur advice bands');
}
// Hits, squash, arcs, reading time.
{
  const hits = [[1, 1], {time: 2, amplitude: .5}];
  near(M.impulse(.5, hits), 0, 0, 'no impulse before the first hit');
  near(M.impulse(1, hits), 1, 1e-12, 'impulse peaks at the hit');
  ok(M.impulse(1.5, hits) < .05, 'impulse decays');
  assert.deepEqual(M.shake(.9, hits), [0, 0]); checks++;
  const sq = M.squashStretch(2000);
  near(sq.along * sq.across, 1, 1e-12, 'squash keeps the area');
  const mid = M.arcPoint(.5, [0, 0], [100, 0], .25);
  ok(Math.abs(mid[1]) > 10, 'arc bends away from the straight line');
  assert.deepEqual(M.arcPoint(1, [0, 0], [100, 0]), [100, 0]); checks++;
  near(M.readingTime(5), 5 / 3.5, 1e-12, 'reading time');
  near(M.readingTime(1), .8, 1e-12, 'reading floor');
}
// Path at constant speed (roving keyframes) with tangent for auto-orient.
{
  const path = M.pathSampler([[0, 0], [100, 0], [100, 300]]);
  near(path.length, 400, 1e-9, 'path length');
  assert.deepEqual(path.at(.25).point, [100, 0]); checks++;
  assert.deepEqual(path.at(.625).point, [100, 150]); checks++;
  near(path.at(.1).angle, 0, 1e-12, 'tangent along x');
  near(path.at(.9).angle, Math.PI / 2, 1e-12, 'tangent along y');
  assert.throws(() => M.pathSampler([[0, 0]]), RangeError);
}
// Classic easing names map to the GSAP powers: cubic is power2 (u³), quart is power3 (u⁴).
near(M.EASINGS['cubic.out'](.3), 1 - Math.pow(.7, 3), 1e-12, 'cubic.out is 1-(1-u)^3');
near(M.EASINGS['quart.out'](.3), M.EASINGS['power3.out'](.3), 1e-12, 'quart.out = power3.out');
near(M.EASINGS['quad.in'](.5), .25, 1e-12, 'quad.in is u^2');
// Stepped time and echo.
{
  near(M.posterize(.49, 12), 5 / 12, 1e-12, 'posterize holds the pose');
  near(M.posterize(5 / 12, 12), 5 / 12, 1e-12, 'a step boundary belongs to the new pose');
  near(M.posterize((25 + .5) / 60, 12), 5 / 12, 1e-12, 'frame 25 at 60 fps (0.425 s) holds the 12 fps pose 5');
  let changes = 0, prev = M.posterize(0, 12);
  for (let n = 1; n < 60; n++) { const v = M.posterize((n + .5) / 60, 12); if (v !== prev) changes++; prev = v; }
  near(changes, 11, 0, '12 pose changes per second at 60 fps (11 inside one second)');
  near(M.stepped(t => t * 10, 24)(.51), Math.floor(.51 * 24 + 1e-6) / 24 * 10, 1e-12, 'stepped wraps a function');
  const e = M.echo(2, {count: 3, lag: .1, decay: .5});
  near(e.length, 4, 0, 'echo copies'); near(e[3].t, 1.7, 1e-12, 'echo lag'); near(e[3].weight, .125, 1e-12, 'echo decay');
}
// ---- fixes from the 22-10-2026 review ----
{
  near(M.linear(5, 5, 5, 0, 1), 1, 0, 'zero-length segment gives the end value, not NaN');
  near(M.ease(4, 5, 5, 0, 1), 0, 0, 'zero-length segment before its time gives the start value');
  near(M.tween(1, 1, 1, 0, 10, 'linear'), 10, 0, 'zero-length tween');
  for (const z of [1, 1.5]) {
    const opts = {freq: 2, damping: z}, ts = M.springSettle(opts);
    let late = 0;
    for (let k = 0; k < 400; k++) late = Math.max(late, Math.abs(M.spring(ts + k * .01, opts) - 1));
    ok(late <= .02 + 1e-9 && Math.abs(M.spring(ts * .9, opts) - 1) > .02, `settle time is right for damping ${z}`);
  }
  const mid = M.arcPoint(.5, [0, 0], [100, 0], .25);
  near(Math.abs(mid[1]), 25, 1e-9, 'arcPoint bend is the real peak deviation');
  const ramp = M.speedRamp(() => 1, {from: 2, to: 6});
  near(ramp(2), 2, 1e-12, 'speedRamp content time starts at from'); near(ramp(3), 3, 1e-9, 'speed 1 keeps clock time');
  near(ramp(1), 1, 1e-12, 'before from it extrapolates');
  const hit = [{time: 1, amplitude: 1}];
  near(Math.hypot(...M.shake(1, hit, {px: 10})), 0, 1e-12, 'shake starts at rest on the hit');
  ok(Math.hypot(...M.shake(1 + 1 / 60, hit, {px: 10})) > 4, 'and kicks within the first frame');
  assert.throws(() => M.stagger(1, 9, {from: 'centre'})); checks++;
  assert.throws(() => M.stagger(1, 9, {from: 'middle', grid: [3, 3]})); checks++;
  near(M.stagger(4, 9, {grid: [3, 3], from: 'edges', each: 1}), 1, 1e-12, 'grid edges: the centre cell is last');
  near(M.stagger(0, 9, {grid: [3, 3], from: 'edges', each: 1}), 0, 1e-12, 'grid edges: a corner is first');
  near(M.stagger(8, 9, {grid: [3, 3], from: 4, each: 1}), Math.SQRT2, 1e-12, 'grid from an index');
}
// ---- new helpers ----
{
  const f = t => t * 10;
  near(M.loopValue(f, 2.5, 1, 'offset'), 25, 1e-9, 'offset loop keeps accumulating');
  near(M.loopValue(f, 2.5, 1, 'cycle'), 5, 1e-9, 'cycle loop');
  near(M.loopValue(f, 3, 1, 'continue'), 30, 1e-6, 'continue keeps the last velocity');
  near(M.loopValue(t => [t, -t], 1.5, 1, 'offset')[1], -1.5, 1e-9, 'offset works on vectors');
  near(M.easing('steps(4)')(.6), .5, 1e-12, 'steps(4) holds');
  ok(M.EASINGS['bounce.out'](.5) > .7 && M.EASINGS['bounce.out'](.5) < .8, 'bounce.out bounces');
  const a1 = M.particle(3, 1.234, {life: 2, seed: 5}), a2 = M.particle(3, 1.234, {life: 2, seed: 5});
  near(a1.u, a2.u, 0, 'particle is deterministic'); near(a1.rand(1), a2.rand(1), 0, 'particle random is stable in a cycle');
  ok(a1.u >= 0 && a1.u < 1, 'particle age in range');
  ok(M.particle(3, 1.234 + 2, {life: 2, seed: 5}).cycle === a1.cycle + 1, 'reborn every life');
  const square = [[0, 0], [100, 0], [100, 100], [0, 100]], circle = Array.from({length: 4}, (_, k) => [50 + 70 * Math.cos(-k * Math.PI / 2 + 2), 50 + 70 * Math.sin(-k * Math.PI / 2 + 2)]);
  const rs = M.resamplePath(square, 16, {closed: true});
  near(rs.length, 16, 0, 'resample count');
  near(Math.hypot(rs[1][0] - rs[0][0], rs[1][1] - rs[0][1]), 25, 1e-9, 'evenly spaced along the length');
  const rc = M.resamplePath(circle, 16, {closed: true}), al = M.alignPaths(rs, rc);
  ok(Math.sign(M.resamplePath(square, 16, {closed: true}).reduce((s, p, i, arr) => s + p[0] * arr[(i + 1) % 16][1] - arr[(i + 1) % 16][0] * p[1], 0))
     === Math.sign(al.reduce((s, p, i, arr) => s + p[0] * arr[(i + 1) % 16][1] - arr[(i + 1) % 16][0] * p[1], 0)), 'aligned path has the same winding');
  assert.deepEqual(M.morphPath(rs, al, 0), rs); checks++;
  assert.deepEqual(M.morphPath(rs, al, 1), al); checks++;
  const cam = M.lookAt([0, 0, 1700], [0, 0, 0]);
  const c0 = M.project([0, 0, 0], cam);
  near(c0.x, 540, 1e-9, 'centre projects to the centre'); near(c0.scale, 1, 1e-12, 'focal = distance gives scale 1');
  const r0 = M.project([100, 50, 0], cam);
  near(r0.x, 640, 1e-9, '+x world is to the right'); near(r0.y, 1010, 1e-9, '+y world is down (screen convention)');
  ok(M.project([0, 0, 850], cam).scale > 1.99, 'closer means bigger');
  ok(!M.project([0, 0, 1800], cam).visible, 'behind the camera is not visible');
  // A kerning pair: the measured prefix is narrower than the sum of letters.
  const widths = {A: 10, V: 10, AV: 17, 'AVA': 27};
  const measure = str => widths[str] ?? [...str].length * 10;
  const g = M.layoutGlyphs('AVA', measure);
  near(g[1].x, 10, 0, 'second glyph at measure("A")'); near(g[2].x, 17, 0, 'third glyph keeps the AV kerning');
  const accent = M.layoutGlyphs('e\u0301xito', s => s.length);
  near(accent.length, 5, 0, 'a decomposed é is one glyph, not two');
  near(M.readingTimeChars('one plain line of text'), 22 / 15, 1e-12, 'reading time by characters');
}
console.log(`ok ${checks}`);
