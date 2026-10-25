/* motion-math.js · After Effects craft as pure functions of time.
   Every function is deterministic: same arguments, same result, so window.seek(t) can jump anywhere.
   Browser: <script src="motion-math.js"></script> → window.MotionMath.   Node: require('./motion-math.js').
   Guides: references/craft/curves-graph-editor.md, principles.md, blur.md, rhythm-sync.md. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.MotionMath = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const TAU = Math.PI * 2;

  /* ---------- basics ---------- */
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const mix = (a, b, u) => Array.isArray(a) ? a.map((v, i) => v + (b[i] - v) * u) : a + (b - a) * u;
  const smoothstep = u => { u = clamp(u); return u * u * (3 - 2 * u); };
  const smootherstep = u => { u = clamp(u); return u * u * u * (u * (u * 6 - 15) + 10); };

  /* AE expression remaps: linear(t, tMin, tMax, v1, v2) or linear(t, v1, v2) with t in 0..1.
     ease(): zero speed at both ends (cubic Hermite, an approximation of AE's curve); easeIn/easeOut: one end. */
  function remapWith(shape) {
    return function (t, a, b, c, d) {
      const [u, v1, v2] = arguments.length >= 5 ? [b === a ? (t >= b ? 1 : 0) : (t - a) / (b - a), c, d] : [t, a, b];
      return mix(v1, v2, shape(clamp(u)));
    };
  }
  const linear = remapWith(u => u);
  const ease = remapWith(smoothstep);
  const easeIn = remapWith(u => u * u * (2 - u));
  const easeOut = remapWith(u => 1 - (1 - u) * (1 - u) * (1 + u));

  /* ---------- easing curves (u in 0..1 → progress, 0 → 0 and 1 → 1) ---------- */
  const inOut = f => u => u < .5 ? f(2 * u) / 2 : 1 - f(2 - 2 * u) / 2;
  const out = f => u => 1 - f(1 - u);
  const powerIn = n => u => Math.pow(u, n);
  const expoIn = u => u <= 0 ? 0 : Math.pow(2, 10 * (u - 1)) - Math.pow(2, -10) * (1 - u);   // exact 0 at u=0
  const sineIn = u => 1 - Math.cos(u * Math.PI / 2);
  const circIn = u => 1 - Math.sqrt(1 - u * u);
  const backIn = (s = 1.70158) => u => u * u * ((s + 1) * u - s);
  const elasticOut = (amplitude = 1, period = .3) => {
    const a = Math.max(1, amplitude), s = period / TAU * Math.asin(1 / a);
    return u => u <= 0 ? 0 : u >= 1 ? 1 : a * Math.pow(2, -10 * u) * Math.sin((u - s) * TAU / period) + 1;
  };

  /* Penner's bounce: a ball that lands and bounces three times (playful, not for paper or glass). */
  function bounceOut(u) {
    const n = 7.5625, d = 2.75;
    if (u < 1 / d) return n * u * u;
    if (u < 2 / d) return n * (u -= 1.5 / d) * u + .75;
    if (u < 2.5 / d) return n * (u -= 2.25 / d) * u + .9375;
    return n * (u -= 2.625 / d) * u + .984375;
  }
  /* Hold-and-jump progress in n equal steps (a stepped tween; for stepped *time* use posterize). */
  const steps = n => u => u >= 1 ? 1 : Math.floor(clamp(u) * n) / n;

  /* Cubic bezier timing function (as CSS and as an AE value graph), solved for x with Newton + bisection. */
  function cubicBezier(x1, y1, x2, y2) {
    if (!(x1 >= 0 && x1 <= 1 && x2 >= 0 && x2 <= 1)) throw new RangeError('cubicBezier: x1 and x2 must be within [0, 1]');
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = t => ((ax * t + bx) * t + cx) * t, sy = t => ((ay * t + by) * t + cy) * t;
    const dx = t => (3 * ax * t + 2 * bx) * t + cx;
    function solve(x) {
      let t = x;
      for (let i = 0; i < 8; i++) {
        const e = sx(t) - x;
        if (Math.abs(e) < 1e-7) return t;
        const d = dx(t);
        if (Math.abs(d) < 1e-6) break;
        t -= e / d;
      }
      let lo = 0, hi = 1;
      t = x;
      for (let i = 0; i < 60; i++) {
        const v = sx(t);
        if (Math.abs(v - x) < 1e-7) break;
        if (x > v) lo = t; else hi = t;
        t = (lo + hi) / 2;
      }
      return t;
    }
    return x => x <= 0 ? 0 : x >= 1 ? 1 : sy(solve(x));
  }

  /* AE temporal ease between two keyframes on a normalized value graph.
     influence: % of the segment the handle reaches (Easy Ease = 33.33).
     speed: keyframe speed as a multiple of the segment's average speed (0 = eased to a stop, 1 = linear). */
  function aeEase({outInfluence = 33.33, inInfluence = 33.33, outSpeed = 0, inSpeed = 0} = {}) {
    const io = clamp(outInfluence / 100, .001, 1), ii = clamp(inInfluence / 100, .001, 1);
    return cubicBezier(io, io * outSpeed, 1 - ii, 1 - ii * inSpeed);
  }
  /* Convert an AE speed in units/s to the multiple aeEase expects. */
  const aeSpeedMultiple = (speed, distance, duration) => distance === 0 ? 0 : speed * duration / distance;

  const EASINGS = {
    linear: u => u,
    'sine.in': sineIn, 'sine.out': out(sineIn), 'sine.inOut': inOut(sineIn),
    'circ.in': circIn, 'circ.out': out(circIn), 'circ.inOut': inOut(circIn),
    'expo.in': expoIn, 'expo.out': out(expoIn), 'expo.inOut': inOut(expoIn),
    'back.in': backIn(), 'back.out': out(backIn()), 'back.inOut': inOut(backIn(1.70158 * 1.525)),
    'elastic.out': elasticOut(), 'elastic.in': out(elasticOut()),
    // AE naming: "Easy Ease In" eases the ARRIVAL into a keyframe (a CSS ease-out shape); "Easy Ease Out" eases the departure.
    easyEase: aeEase(), 'easyEase.in': aeEase({outInfluence: .1, outSpeed: 1}), 'easyEase.out': aeEase({inInfluence: .1, inSpeed: 1}),
    'css.ease': cubicBezier(.25, .1, .25, 1),
  };
  for (let n = 1; n <= 4; n++) {
    EASINGS[`power${n}.in`] = powerIn(n + 1);
    EASINGS[`power${n}.out`] = out(powerIn(n + 1));
    EASINGS[`power${n}.inOut`] = inOut(powerIn(n + 1));
  }
  EASINGS['bounce.out'] = bounceOut;
  EASINGS['bounce.in'] = out(bounceOut);
  EASINGS['bounce.inOut'] = inOut(out(bounceOut));
  // Classic names (GSAP convention): power1 = quad (u²), power2 = cubic (u³), power3 = quart (u⁴), power4 = quint (u⁵).
  ['quad', 'cubic', 'quart', 'quint'].forEach((name, k) => {
    for (const kind of ['in', 'out', 'inOut']) EASINGS[`${name}.${kind}`] = EASINGS[`power${k + 1}.${kind}`];
  });
  /* easing('power3.out') | easing([x1, y1, x2, y2]) | easing('steps(6)') | easing(fn) -> u => progress */
  function easing(spec) {
    if (typeof spec === 'function') return spec;
    if (Array.isArray(spec)) return cubicBezier(...spec);
    const st = /^steps\((\d+)\)$/.exec(spec);
    if (st) return steps(Number(st[1]));
    const f = EASINGS[spec];
    if (!f) throw new Error(`Unknown easing: ${spec}`);
    return f;
  }
  /* Tween a value between two keyframe times with a named easing. */
  const tween = (t, t0, t1, v0, v1, spec = 'power2.out') =>
    mix(v0, v1, easing(spec)(t1 === t0 ? (t >= t1 ? 1 : 0) : clamp((t - t0) / (t1 - t0))));

  /* ---------- physics ---------- */
  /* Damped spring step response 0 → 1. freq: natural frequency in Hz; damping ζ (<1 overshoots, 1 critical). */
  function spring(t, {freq = 2, damping = .5} = {}) {
    if (t <= 0) return 0;
    const w = TAU * freq, z = damping;
    if (z < 1) {
      const wd = w * Math.sqrt(1 - z * z);
      return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + z * w / wd * Math.sin(wd * t));
    }
    if (z === 1) return 1 - Math.exp(-w * t) * (1 + w * t);
    const r = Math.sqrt(z * z - 1), r1 = -w * (z - r), r2 = -w * (z + r);
    return 1 + (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r1 - r2);
  }
  /* Physical parameters (stiffness, damping, mass) → {freq, damping ζ}. */
  function springFromPhysics({stiffness = 170, damping = 26, mass = 1} = {}) {
    const w = Math.sqrt(stiffness / mass);
    return {freq: w / TAU, damping: damping / (2 * Math.sqrt(stiffness * mass))};
  }
  const springOvershoot = damping => damping >= 1 ? 0 : Math.exp(-Math.PI * damping / Math.sqrt(1 - damping * damping));
  /* Time after which the step response stays within `tolerance` of 1. Searched numerically over a window set by the
     slow pole, so it is right for under-, critically and over-damped springs. */
  function springSettle({freq = 2, damping = .5} = {}, tolerance = .02) {
    const w = TAU * freq, z = Math.max(damping, 1e-6);
    const slow = z < 1 ? z * w : w * (z - Math.sqrt(z * z - 1));
    const horizon = 12 / Math.max(slow, 1e-6), n = 6000;
    for (let i = n; i >= 0; i--) {
      const t = horizon * i / n;
      if (Math.abs(spring(t, {freq, damping}) - 1) > tolerance) return horizon * Math.min(n, i + 1) / n;
    }
    return 0;
  }

  /* AE inertial bounce after a keyframe: velocity at the key × amp × decaying sine. */
  const inertialBounce = (t, velocity, {amp = .05, freq = 3, decay = 8} = {}) =>
    t <= 0 ? 0 : velocity * amp * Math.sin(freq * t * TAU) / Math.exp(decay * t);

  /* Spring-damper follower integrated once at load (fixed small step) and then only sampled:
     physical lag and overshoot that stay seekable. target(t) returns a number or an array;
     omega (rad/s) and zeta may be numbers or functions of t (piecewise behaviour, anticipation). */
  function followerTable({from, to, dt = 1 / 960, target, omega = TAU * 2, zeta = .7, initial, initialVelocity}) {
    if (!(to > from)) throw new RangeError('followerTable: to must be greater than from');
    const first = target(from), dims = Array.isArray(first) ? first.length : 1;
    const asArray = v => Array.isArray(v) ? v : [v];
    const n = Math.round((to - from) / dt) + 1;
    const pos = new Float64Array(n * dims), vel = new Float64Array(n * dims);
    const p = asArray(initial ?? first).slice(), v = asArray(initialVelocity ?? new Array(dims).fill(0)).slice();
    const W = typeof omega === 'function' ? omega : () => omega, Z = typeof zeta === 'function' ? zeta : () => zeta;
    for (let i = 0; i < n; i++) {
      const t = from + i * dt, goal = asArray(target(t)), w = W(t), z = Z(t);
      for (let k = 0; k < dims; k++) {
        const a = w * w * (goal[k] - p[k]) - 2 * z * w * v[k];
        v[k] += a * dt; p[k] += v[k] * dt;            // semi-implicit Euler: stable at this step
        pos[i * dims + k] = p[k]; vel[i * dims + k] = v[k];
      }
    }
    function sample(t) {
      const f = clamp((t - from) / dt, 0, n - 1.000001), i = Math.floor(f), u = f - i;
      const value = [], velocity = [];
      for (let k = 0; k < dims; k++) {
        value.push(pos[i * dims + k] + (pos[(i + 1) * dims + k] - pos[i * dims + k]) * u);
        velocity.push(vel[i * dims + k] + (vel[(i + 1) * dims + k] - vel[i * dims + k]) * u);
      }
      return dims === 1 ? {value: value[0], velocity: velocity[0]} : {value, velocity};
    }
    return {sample, from, to, dt, samples: n};
  }

  /* Squash and stretch from speed, preserving area: along the motion × (1+s), across ÷ (1+s). */
  function squashStretch(speed, {k = .00007, max = .14} = {}) {
    const s = 1 + Math.min(max, Math.abs(speed) * k);
    return {along: s, across: 1 / s};
  }
  /* Point on a curved path from p0 to p1 (arc principle). bend: the curve's peak deviation from the straight line,
     as a fraction of the distance (0.15–0.3 for organic arcs). The quadratic's control point sits at twice that. */
  function arcPoint(u, p0, p1, bend = .2) {
    const mx = (p0[0] + p1[0]) / 2, my = (p0[1] + p1[1]) / 2, dx = p1[0] - p0[0], dy = p1[1] - p0[1];
    const c = [mx - dy * 2 * bend, my + dx * 2 * bend], a = 1 - u;
    return [a * a * p0[0] + 2 * a * u * c[0] + u * u * p1[0], a * a * p0[1] + 2 * a * u * c[1] + u * u * p1[1]];
  }

  /* Spatial path separated from timing (AE spatial vs temporal interpolation): u → point at constant speed
     along a polyline (roving keyframes). Pair it with an easing: path(easing('power2.inOut')(u)).
     Also returns the tangent angle for auto-orient. Dense points (sampled curves) give smooth paths. */
  function pathSampler(points) {
    if (points.length < 2) throw new RangeError('pathSampler needs at least two points');
    const lengths = [0];
    for (let i = 1; i < points.length; i++) lengths.push(lengths[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
    const total = lengths[lengths.length - 1];
    function at(u) {
      const d = clamp(u) * total;
      let lo = 0, hi = lengths.length - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; if (lengths[m] <= d) lo = m; else hi = m; }
      const seg = lengths[hi] - lengths[lo] || 1, k = (d - lengths[lo]) / seg, a = points[lo], b = points[hi];
      return {point: [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k], angle: Math.atan2(b[1] - a[1], b[0] - a[0])};
    }
    return {at, length: total};
  }

  /* ---------- deterministic randomness, noise, loops ---------- */
  function hash(n, seed = 0) {
    let h = Math.imul((n | 0) ^ Math.imul(seed | 0, 0x9E3779B1), 0x85EBCA6B);
    h ^= h >>> 13; h = Math.imul(h, 0xC2B2AE35); h ^= h >>> 16;
    return (h >>> 0) / 4294967296;
  }
  function rng(seed = 1) {   // mulberry32
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function valueNoise(x, seed = 0) {
    const i = Math.floor(x), f = x - i, u = f * f * f * (f * (f * 6 - 15) + 10);
    return mix(hash(i, seed) * 2 - 1, hash(i + 1, seed) * 2 - 1, u);
  }
  /* AE wiggle(freq, amp, octaves, amp_mult): smooth deterministic noise added to a value.
     Returns the offset (number, or array when dims > 1, each axis with its own seed). */
  function wiggle(t, {freq = 2, amp = 10, octaves = 1, ampMult = .5, seed = 0, dims = 1} = {}) {
    const axis = d => {
      let sum = 0, a = amp, f = freq;
      for (let o = 0; o < octaves; o++) { sum += a * valueNoise(t * f, seed * 131 + d * 7919 + o * 104729); a *= ampMult; f *= 2; }
      return sum;
    };
    return dims === 1 ? axis(0) : Array.from({length: dims}, (_, d) => axis(d));
  }
  /* AE loopOut types on a local time: 'cycle' | 'pingpong'. */
  function loop(t, period, mode = 'cycle') {
    const m = ((t % (2 * period)) + 2 * period) % (2 * period);
    if (mode === 'pingpong') return m < period ? m : 2 * period - m;
    return ((t % period) + period) % period;
  }

  /* AE loopOut on a value: fn(t) animated over [0, period]. 'cycle' and 'pingpong' repeat; 'offset' repeats adding
     the change of each cycle (a background that keeps scrolling); 'continue' keeps the final velocity. */
  function loopValue(fn, t, period, mode = 'cycle') {
    if (t <= period || mode === 'cycle' || mode === 'pingpong') return fn(t <= period && t >= 0 ? t : loop(t, period, mode === 'pingpong' ? 'pingpong' : 'cycle'));
    const a = fn(0), b = fn(period);
    if (mode === 'offset') {
      const k = Math.floor(t / period), r = t - k * period;
      return Array.isArray(b) ? fn(r).map((v, i) => v + k * (b[i] - a[i])) : fn(r) + k * (b - a);
    }
    if (mode === 'continue') {
      const h = Math.min(1e-3, period / 10), b0 = fn(period - h);
      return Array.isArray(b) ? b.map((v, i) => v + (v - b0[i]) / h * (t - period)) : b + (b - b0) / h * (t - period);
    }
    throw new Error(`loopValue: unknown mode '${mode}'`);
  }

  /* ---------- time ---------- */
  /* Stagger delay for element `index` of `count`. from: 'start' | 'end' | 'center' | 'edges' | 'random' | index.
     grid: [cols, rows] measures distance in the grid. curve: optional easing to distribute delays. */
  function stagger(index, count, {each = .05, from = 'start', seed = 0, grid = null, curve = null} = {}) {
    if (count <= 1) return 0;
    let dist, maxDist;
    if (from === 'random') {
      const order = Array.from({length: count}, (_, i) => i), next = rng(seed + 1);
      for (let i = count - 1; i > 0; i--) { const j = Math.floor(next() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
      dist = order.indexOf(index); maxDist = count - 1;
    } else if (grid) {
      const [cols, rows] = grid, col = index % cols, row = Math.floor(index / cols);
      const cx = (cols - 1) / 2, cy = (rows - 1) / 2;
      const corners = [[0, 0], [cols - 1, 0], [0, rows - 1], [cols - 1, rows - 1]];
      if (from === 'edges') {
        dist = Math.min(col, row, cols - 1 - col, rows - 1 - row);
        maxDist = Math.min(cx, cy);
      } else {
        let ox, oy;
        if (from === 'center') [ox, oy] = [cx, cy];
        else if (from === 'end') [ox, oy] = [cols - 1, rows - 1];
        else if (from === 'start') [ox, oy] = [0, 0];
        else if (typeof from === 'number') [ox, oy] = [from % cols, Math.floor(from / cols)];
        else throw new Error(`stagger: unknown from '${from}'`);
        dist = Math.hypot(col - ox, row - oy);
        maxDist = Math.max(...corners.map(([x, y]) => Math.hypot(x - ox, y - oy)));
      }
    } else {
      if (!['start', 'end', 'center', 'edges'].includes(from) && typeof from !== 'number') throw new Error(`stagger: unknown from '${from}'`);
      const c = (count - 1) / 2;
      if (from === 'start') dist = index;
      else if (from === 'end') dist = count - 1 - index;
      else if (from === 'center') dist = Math.abs(index - c);
      else if (from === 'edges') dist = c - Math.abs(index - c);
      else dist = Math.abs(index - Number(from));
      maxDist = from === 'center' || from === 'edges' ? c : typeof from === 'number' ? Math.max(from, count - 1 - from) : count - 1;
    }
    if (!curve || maxDist === 0) return dist * each;
    return easing(curve)(dist / maxDist) * maxDist * each;
  }
  /* AE valueAtTime(time - lag): the same animation, later. */
  const delay = (fn, seconds) => t => fn(t - seconds);
  /* Time remap from a speed curve (1 = normal, .25 = slow motion, 3 = fast): returns t → content time. */
  function speedRamp(speed, {from = 0, to, dt = 1 / 600} = {}) {
    if (!(to > from)) throw new RangeError('speedRamp: to must be greater than from');
    const n = Math.round((to - from) / dt) + 1, table = new Float64Array(n);
    for (let i = 1; i < n; i++) table[i] = table[i - 1] + (speed(from + (i - 1) * dt) + speed(from + i * dt)) / 2 * dt;
    // Content time equals clock time at `from`, then advances at the given speed.
    return t => {
      if (t <= from) return from + (t - from) * speed(from);
      if (t >= to) return from + table[n - 1] + (t - to) * speed(to);
      const f = (t - from) / dt, i = Math.floor(f);
      return from + table[i] + (table[Math.min(i + 1, n - 1)] - table[i]) * (f - i);
    };
  }

  /* Stepped time (AE Posterize Time / posterizeTime(fps), animating "on twos"): the pose holds and jumps at
     `fps`. A tiny epsilon keeps frame-centre times from falling on the wrong side of a step boundary. */
  const posterize = (t, fps = 12, offset = 0) => Math.floor((t - offset) * fps + 1e-6) / fps + offset;
  const stepped = (fn, fps = 12, offset = 0) => t => fn(posterize(t, fps, offset));
  /* AE Echo: earlier copies of the same animation. Returns [{t, weight}] newest first; draw each copy with its weight. */
  function echo(t, {count = 5, lag = .05, decay = .6} = {}) {
    return Array.from({length: count + 1}, (_, k) => ({t: t - k * lag, weight: Math.pow(decay, k)}));
  }

  /* ---------- exposure (motion blur) ---------- */
  function halton(i, base) { let f = 1, r = 0; while (i > 0) { f /= base; r += f * (i % base); i = Math.floor(i / base); } return r; }
  /* Sample times for one frame, AE semantics: the shutter opens at t + phase and stays open `shutter` degrees.
     phase = -shutter/2 (default) centres the blur on t. Each sample also gets a Halton sub-pixel jitter. */
  function exposureTimes(t, {fps = 60, shutter = 180, phase, samples = 16} = {}) {
    const ph = phase ?? -shutter / 2, open = t + ph / 360 / fps, length = shutter / 360 / fps;
    return Array.from({length: samples}, (_, j) => ({
      t: open + (j + .5) / samples * length,
      jitter: samples > 1 ? [halton(j + 1, 2) - .5, halton(j + 1, 3) - .5] : [0, 0],
      weight: 1 / samples,
    }));
  }
  const pxPerExposure = (speedPxPerSecond, shutter = 180, fps = 60) => Math.abs(speedPxPerSecond) * shutter / 360 / fps;
  function blurAdvice(px) {
    if (px < 1) return 'none: below a pixel per exposure, blur only softens';
    if (px < 20) return 'natural: real motion blur reads as weight';
    if (px < 80) return 'strong: check the landing frame is sharp and the edges do not ghost';
    return 'stylized: a smear; keep it to snaps and whips, not to anything that must be read';
  }

  /* ---------- hits shared with the sound (plan.json "hits") ---------- */
  const normalizeHits = hits => hits.map(h => Array.isArray(h) ? {time: h[0], amplitude: h[1]} : h);
  function impulse(t, hits, rate = 9) {
    return normalizeHits(hits).reduce((s, h) => s + (t >= h.time ? h.amplitude * Math.exp(-(t - h.time) * rate) : 0), 0);
  }
  /* Impact shake: starts at rest on the hit, peaks within about a frame and decays. Returns [x, y] in px
     (`px` = peak size for amplitude 1; 6–12 px reads as a hit at 1080 wide). */
  function shake(t, hits, {rate = 14, minAmplitude = .8, fx = 71, fy = 83, px = 1} = {}) {
    return normalizeHits(hits).reduce((s, h) => {
      if (t < h.time || h.amplitude < minAmplitude) return s;
      const k = t - h.time, e = px * h.amplitude * Math.exp(-k * rate);
      return [s[0] + e * Math.sin(k * fx), s[1] + e * Math.sin(k * fy) * .8];
    }, [0, 0]);
  }

  /* ---------- particles ---------- */
  /* Particle i of an endless emitter, in closed form (no state): each one is reborn every `life` seconds with a
     fresh seeded random set. Returns {u: 0..1 age, cycle, rand(k): stable random in this cycle}. */
  function particle(i, t, {life = 3, seed = 0} = {}) {
    const start = hash(i, seed * 7 + 1) * life, local = t + start, cycle = Math.floor(local / life);
    return {u: (local - cycle * life) / life, cycle, rand: k => hash(i * 9973 + cycle * 131 + k, seed)};
  }

  /* ---------- path morph ---------- */
  /* Resample a polyline to n points evenly spaced along its length (closed: the last point joins the first). */
  function resamplePath(points, n, {closed = false} = {}) {
    const pts = closed ? [...points, points[0]] : points, path = pathSampler(pts);
    return Array.from({length: n}, (_, k) => path.at(closed ? k / n : k / (n - 1)).point);
  }
  const signedArea = pts => pts.reduce((s, p, i) => { const q = pts[(i + 1) % pts.length]; return s + p[0] * q[1] - q[0] * p[1]; }, 0) / 2;
  /* Make b correspond to a for morphing: same winding, and (closed) the rotation of start point with the least travel. */
  function alignPaths(a, b, {closed = true} = {}) {
    if (a.length !== b.length) throw new RangeError('alignPaths: resample both paths to the same number of points first');
    let best = b;
    if (closed) {
      const wound = Math.sign(signedArea(a)) !== Math.sign(signedArea(b)) ? [...b].reverse() : b;
      let bestCost = Infinity;
      for (let s = 0; s < wound.length; s++) {
        let cost = 0;
        for (let i = 0; i < a.length; i++) { const q = wound[(i + s) % wound.length]; cost += (a[i][0] - q[0]) ** 2 + (a[i][1] - q[1]) ** 2; }
        if (cost < bestCost) { bestCost = cost; best = wound.map((_, i) => wound[(i + s) % wound.length]); }
      }
    }
    return best;
  }
  const morphPath = (a, b, u) => a.map((p, i) => [p[0] + (b[i][0] - p[0]) * u, p[1] + (b[i][1] - p[1]) * u]);

  /* ---------- 3D camera ---------- */
  const sub3 = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const cross3 = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const norm3 = v => { const l = Math.hypot(...v) || 1; return v.map(x => x / l); };
  /* Camera basis looking from eye to target (screen y grows downwards, as on a canvas). */
  function lookAt(eye, target, up = [0, 1, 0]) {   // same screen convention: x to the right, y down
    const back = norm3(sub3(eye, target)), right = norm3(cross3(up, back)), down = cross3(back, right);
    return {pos: eye, right, down, back};
  }
  /* Project a world point: x/y in px around `center`, scale = focal / depth (size multiplier), depth > 0 in front. */
  function project(p, cam, {focal = 1700, center = [540, 960]} = {}) {
    const d = sub3(p, cam.pos), x = d[0] * cam.right[0] + d[1] * cam.right[1] + d[2] * cam.right[2];
    const y = d[0] * cam.down[0] + d[1] * cam.down[1] + d[2] * cam.down[2], z = -(d[0] * cam.back[0] + d[1] * cam.back[1] + d[2] * cam.back[2]);
    const scale = focal / Math.max(z, 1e-6);
    return {x: center[0] + x * scale, y: center[1] + y * scale, scale, depth: z, visible: z > 0};
  }

  /* ---------- typography ---------- */
  /* Per-letter layout that keeps kerning and never splits a letter with an accent: graphemes (Intl.Segmenter, NFC)
     placed at measure(prefix). measure(str) returns a width, e.g. s => ctx.measureText(s).width. */
  function layoutGlyphs(text, measure) {
    const clean = text.normalize('NFC');
    const parts = typeof Intl !== 'undefined' && Intl.Segmenter
      ? [...new Intl.Segmenter(undefined, {granularity: 'grapheme'}).segment(clean)].map(x => x.segment) : Array.from(clean);
    let prefix = '';
    return parts.map((ch, index) => { const x = measure(prefix); prefix += ch; return {ch, index, x, w: measure(prefix) - x}; });
  }
  /* Reading time by characters (subtitle practice: about 15–17 characters per second); entrance and exit come on top. */
  const readingTimeChars = (text, {charsPerSecond = 15, floor = .8, extra = 0} = {}) =>
    Math.max(floor, text.normalize('NFC').replace(/\s+/g, ' ').trim().length / charsPerSecond) + extra;
  /* Seconds a line must stay readable (entrance and exit come on top). */
  const readingTime = (words, {wordsPerSecond = 3.5, floor = .8, extra = 0} = {}) => Math.max(floor, words / wordsPerSecond) + extra;

  return {
    TAU, clamp, mix, smoothstep, smootherstep, linear, ease, easeIn, easeOut,
    EASINGS, easing, tween, cubicBezier, aeEase, aeSpeedMultiple, powerIn, expoIn, sineIn, circIn, backIn, elasticOut, inOut, out,
    spring, springFromPhysics, springOvershoot, springSettle, inertialBounce, followerTable, squashStretch, arcPoint, pathSampler,
    hash, rng, valueNoise, wiggle, loop, loopValue, stagger, delay, speedRamp, bounceOut, steps,
    particle, resamplePath, alignPaths, morphPath, lookAt, project, layoutGlyphs, readingTimeChars, posterize, stepped, echo,
    halton, exposureTimes, pxPerExposure, blurAdvice, impulse, shake, normalizeHits, readingTime,
  };
});
