/* timeline.js · declarative keyframes for motion graphics, as pure functions of time.
   A track is a list of keyframes {t, v, ease | ae, hold, fps}. value(track, t) depends only on t, so window.seek(t)
   can jump anywhere and every frame of a piece is reproducible. scene({tracks, markers, hits}) groups tracks with
   named markers and the hits that the sound also uses (plan.json "hits").
   Browser: load motion-math.js first, then this file → window.Timeline. Node: require('./timeline.js').
   Eases apply to the segment that leaves a key: a MotionMath name ('power3.out'), [x1, y1, x2, y2] (cubic bezier),
   'steps(n)', or a function u → progress. ae: {outInfluence, inInfluence, outSpeed, inSpeed}, read from both keys of a
   segment as After Effects does: influence in percent, speed in units per second (a vector uses its length).
   hold: true keeps the value until the next key (AE hold keyframe). fps: n posterizes the time inside a segment
   (stepped segment, "on twos" at 12). Vectors interpolate componentwise with the same progress. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./motion-math.js'));
  else root.Timeline = factory(root.MotionMath);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (MM) {
  'use strict';
  const DEFAULT_INFLUENCE = 33.33;   // After Effects' default: each handle reaches a third of the segment (Easy Ease)

  const copy = v => Array.isArray(v) ? v.slice() : v;
  const isVector = v => Array.isArray(v);
  const isFiniteValue = v => isVector(v) ? v.length > 0 && v.every(Number.isFinite) : Number.isFinite(v);
  const distance = (a, b) => isVector(a) ? Math.hypot(...a.map((x, i) => b[i] - x)) : Math.abs(b - a);

  /* Progress curve of the segment a → b. An explicit ease on a wins; otherwise AE influence and speed decide. */
  function segmentEase(a, b) {
    if (a.ease !== undefined) return MM.easing(a.ease);
    if (!a.ae && !b.ae) return MM.easing('linear');
    const out = a.ae || {}, into = b.ae || {}, span = b.t - a.t, change = distance(a.v, b.v);
    return MM.aeEase({
      outInfluence: out.outInfluence ?? DEFAULT_INFLUENCE,
      inInfluence: into.inInfluence ?? DEFAULT_INFLUENCE,
      outSpeed: MM.aeSpeedMultiple(out.outSpeed ?? 0, change, span),
      inSpeed: MM.aeSpeedMultiple(into.inSpeed ?? 0, change, span),
    });
  }

  /* Validates the keys and precomputes one segment per pair of neighbouring keys. Keys may come unsorted. */
  function track(keys, {name = 'track'} = {}) {
    if (!Array.isArray(keys) || keys.length === 0) throw new RangeError(`${name}: a track needs at least one keyframe`);
    const ks = keys.map((k, i) => {
      if (!k || !Number.isFinite(k.t)) throw new RangeError(`${name}: keyframe ${i} needs a finite time t`);
      if (!isFiniteValue(k.v)) throw new RangeError(`${name}: keyframe ${i} needs a finite number or array of numbers v`);
      if (k.fps !== undefined && !(k.fps > 0)) throw new RangeError(`${name}: keyframe ${i} fps must be positive`);
      for (const side of ['outInfluence', 'inInfluence']) {
        if (k.ae && k.ae[side] !== undefined && !(k.ae[side] > 0 && k.ae[side] <= 100)) {
          throw new RangeError(`${name}: keyframe ${i} ae.${side} must be a percentage in (0, 100]`);
        }
      }
      return k;
    }).sort((a, b) => a.t - b.t);
    for (let i = 1; i < ks.length; i++) {
      if (ks[i].t === ks[i - 1].t) throw new RangeError(`${name}: two keyframes share the time ${ks[i].t}`);
      if (isVector(ks[i].v) !== isVector(ks[0].v) || (isVector(ks[0].v) && ks[i].v.length !== ks[0].v.length)) {
        throw new RangeError(`${name}: every keyframe must have the same shape (number or vector of the same length)`);
      }
    }
    const frozen = ks.map(k => Object.freeze({t: k.t, v: copy(k.v), ease: k.ease, ae: k.ae ? {...k.ae} : undefined,
      hold: !!k.hold, fps: k.fps || 0}));
    const segments = frozen.slice(0, -1).map((a, i) => a.hold
      ? Object.freeze({hold: true, fps: 0, ease: null})
      : Object.freeze({hold: false, fps: a.fps, ease: segmentEase(a, frozen[i + 1])}));
    return Object.freeze({name, keys: Object.freeze(frozen), segments: Object.freeze(segments)});
  }

  /* The value of a track at time t (seconds). Before the first key and after the last one the end values hold. */
  function value(tr, t) {
    if (!Number.isFinite(t)) throw new RangeError('value: time must be a finite number of seconds');
    if (tr.nested) return value(tr.nested.track, (t - tr.nested.offset) * tr.nested.speed);
    const ks = tr.keys, last = ks.length - 1;
    if (t <= ks[0].t) return copy(ks[0].v);
    if (t >= ks[last].t) return copy(ks[last].v);
    let lo = 0, hi = last;   // invariant: ks[lo].t <= t < ks[hi].t
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (ks[mid].t <= t) lo = mid; else hi = mid;
    }
    const a = ks[lo], b = ks[lo + 1], seg = tr.segments[lo];
    if (seg.hold) return copy(a.v);
    const local = seg.fps ? MM.posterize(t - a.t, seg.fps) : t - a.t;
    return MM.mix(a.v, b.v, seg.ease(MM.clamp(local / (b.t - a.t))));
  }

  /* Hits in the plan.json shape {time, amplitude, role}; [time, amplitude] pairs are accepted too (MotionMath.impulse). */
  function hitList(hits = []) {
    return MM.normalizeHits(hits).map(h => {
      const time = Number(h.time);
      if (!Number.isFinite(time)) throw new RangeError('hits: each hit needs a finite time');
      return {time, amplitude: h.amplitude ?? 1, role: h.role ?? 'hit'};
    }).sort((a, b) => a.time - b.time);
  }

  /* A named group of tracks with markers and hits, all in the same clock. markers: {name: t} or [{name, t}]. */
  function scene({tracks = {}, markers = {}, hits = []} = {}) {
    const compiled = {};
    for (const [name, keys] of Object.entries(tracks)) compiled[name] = track(keys, {name});
    const names = Object.keys(compiled);
    const entries = Array.isArray(markers) ? markers.map(m => [m.name, m.t]) : Object.entries(markers);
    const marks = {};
    for (const [name, t] of entries) {
      if (!Number.isFinite(t)) throw new RangeError(`marker ${name} needs a finite time`);
      marks[name] = t;
    }
    const list = hitList(hits);
    const trackOf = name => {
      if (!compiled[name]) throw new RangeError(`unknown track: ${name}`);
      return compiled[name];
    };
    const duration = Math.max(0, ...names.map(n => compiled[n].keys[compiled[n].keys.length - 1].t),
      ...Object.values(marks), ...list.map(h => h.time));
    return Object.freeze({
      tracks: Object.freeze(compiled), markers: Object.freeze({...marks}), hits: Object.freeze(list), duration,
      value: (name, t) => value(trackOf(name), t),
      values: t => Object.fromEntries(names.map(n => [n, value(compiled[n], t)])),
      marker: name => {
        if (!(name in marks)) throw new RangeError(`unknown marker: ${name}`);
        return marks[name];
      },
      impulse: (t, rate) => MM.impulse(t, list, rate),
      shake: (t, opts) => MM.shake(t, list, opts),
    });
  }

  /* Nested time: the child starts at parent time `offset` and runs at `speed` (2 = twice as fast). Works on a track
     (value maps the time) and on a scene (every track, marker and hit moves to parent time). */
  function nest(source, {offset = 0, speed = 1} = {}) {
    if (!Number.isFinite(offset)) throw new RangeError('nest: offset must be a finite number of seconds');
    if (!(Number.isFinite(speed) && speed > 0)) throw new RangeError('nest: speed must be positive (time runs forwards)');
    const toParent = t => offset + t / speed, toChild = t => (t - offset) * speed;
    if (source.keys) {
      return Object.freeze({name: `${source.name} (nested)`, keys: source.keys, segments: source.segments,
        nested: Object.freeze({track: source, offset, speed})});
    }
    if (!source.tracks) throw new TypeError('nest: pass a track or a scene');
    const hits = Object.freeze(source.hits.map(h => Object.freeze({...h, time: toParent(h.time)})));
    const markers = Object.freeze(Object.fromEntries(Object.entries(source.markers).map(([k, t]) => [k, toParent(t)])));
    return Object.freeze({
      tracks: source.tracks, markers, hits, duration: toParent(source.duration),
      value: (name, t) => source.value(name, toChild(t)),
      values: t => source.values(toChild(t)),
      marker: name => toParent(source.marker(name)),
      impulse: (t, rate) => MM.impulse(t, hits, rate),
      shake: (t, opts) => MM.shake(t, hits, opts),
    });
  }

  return {track, value, scene, nest, hitList, DEFAULT_INFLUENCE};
});
