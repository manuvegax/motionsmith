/* footage.js · B-roll inside a piece: video clips and stills on a timeline, drawn deterministically.
   scripts/broll.py assemble writes assets/broll/timeline.json and the frames it points to:
     {"fps": 30, "width": 1080, "height": 1920, "grade": {...}, "segments": [
       {"id": "s01", "start": 0, "end": 2.9, "kind": "video", "dir": "assets/broll/frames/s01", "count": 87},
       {"id": "s02", "start": 2.9, "end": 6.1, "kind": "still", "image": "assets/broll/stills/s02.jpg",
        "move": "push-in", "focus": [0.5, 0.4], "fg": "assets/broll/stills/s02-fg.png"},
       {"id": "s03", "start": 6.1, "end": 8, "kind": "gap"}]}
   A video segment has one JPEG per frame of the piece, already trimmed and covering the frame: the footage carries its
   own blur, so every sub-sample of a frame draws that frame. A still moves in code (Ken Burns with an eased curve,
   so it is sub-pixel smooth and gets real motion blur); with an `fg` cut-out (a PNG with alpha) the foreground moves
   faster than the background: parallax. One grade for everything (contrast, saturation, warmth, lift), so clips and
   photos from different sources read as one film.

     const F = Footage.create(env, await (await fetch('assets/broll/timeline.json')).json());
     Stage.run({..., prepare: t => F.prepare(t), draw(s, {base}) { F.draw(base, s.t); ... }});

   Uses env.loadImage. In the headless checks (no Image) it draws nothing and never throws. */
(function (root) {
  'use strict';
  const M = root.MotionMath;
  const MOVES = {   // scale and pan (fractions of the free margin) at the start and the end of a still
    'push-in': {from: {s: 1.0, x: 0, y: 0}, to: {s: 1.14, x: 0, y: 0}},
    'pull-out': {from: {s: 1.14, x: 0, y: 0}, to: {s: 1.0, x: 0, y: 0}},
    'pan-left': {from: {s: 1.1, x: .8, y: 0}, to: {s: 1.1, x: -.8, y: 0}},
    'pan-right': {from: {s: 1.1, x: -.8, y: 0}, to: {s: 1.1, x: .8, y: 0}},
    'tilt-up': {from: {s: 1.1, x: 0, y: .8}, to: {s: 1.1, x: 0, y: -.8}},
    'tilt-down': {from: {s: 1.1, x: 0, y: -.8}, to: {s: 1.1, x: 0, y: .8}},
    'hold': {from: {s: 1.03, x: 0, y: 0}, to: {s: 1.05, x: 0, y: 0}},   // never fully still: a slow breath
  };
  const GRADE = {contrast: 1.08, saturate: .9, brightness: 1, warmth: .06, lift: .02};

  function create(env, timeline) {
    const segments = (timeline && timeline.segments || []).slice().sort((a, b) => a.start - b.start);
    const grade = {...GRADE, ...(timeline && timeline.grade || {})};
    const fps = (timeline && timeline.fps) || env.FPS;
    const cache = new Map();   // src → image, the last few only
    let current = {segment: null, image: null, fg: null};

    const segmentAt = t => {
      let found = null;
      for (const s of segments) if (t >= s.start - 1e-9 && t < s.end - 1e-9) found = s;
      return found || segments[segments.length - 1] || null;
    };
    async function load(src) {
      if (!src) return null;
      if (cache.has(src)) return cache.get(src);
      const image = await env.loadImage(src);
      cache.set(src, image);
      while (cache.size > 6) cache.delete(cache.keys().next().value);
      return image;
    }
    const pad = n => String(n).padStart(6, '0');

    /* Load what frame t shows: the segment's video frame, or its still (and cut-out). */
    async function prepare(t) {
      const segment = segmentAt(t);
      if (!segment || segment.kind === 'gap') { current = {segment, image: null, fg: null}; return; }
      if (segment.kind === 'video') {
        const n = M.clamp(Math.floor((t - segment.start) * fps + 1e-6), 0, Math.max(0, (segment.count || 1) - 1));
        current = {segment, image: await load(`${segment.dir}/f${pad(n)}.jpg`), fg: null};
      } else {
        current = {segment, image: await load(segment.image), fg: await load(segment.fg)};
      }
    }

    /* Where a still sits at time t: its move, eased in and out over the segment. */
    function still(segment, t) {
      const move = MOVES[segment.move] || MOVES['push-in'];
      const u = M.easing('sine.inOut')(M.clamp((t - segment.start) / Math.max(1e-6, segment.end - segment.start)));
      return {s: M.mix(move.from.s, move.to.s, u), x: M.mix(move.from.x, move.to.x, u), y: M.mix(move.from.y, move.to.y, u)};
    }

    function cover(ctx, image, {s = 1, x = 0, y = 0, focus = [.5, .5]} = {}) {
      const iw = image.naturalWidth || image.width, ih = image.naturalHeight || image.height;
      const k = Math.max(env.W / iw, env.H / ih) * s, w = iw * k, h = ih * k;
      const freeX = w - env.W, freeY = h - env.H;
      const left = -freeX * focus[0] + x * freeX / 2, top = -freeY * focus[1] + y * freeY / 2;
      ctx.drawImage(image, M.clamp(left, -freeX, 0), M.clamp(top, -freeY, 0), w, h);
    }

    /* Draw the footage of time t (a sub-sample of the prepared frame) with the common grade. */
    function draw(ctx, t, {darken = 0} = {}) {
      const {segment, image, fg} = current;
      if (!segment || !image || image.stub) return {segment, drawn: false};
      ctx.save();
      ctx.filter = `contrast(${grade.contrast}) saturate(${grade.saturate}) brightness(${grade.brightness})`;
      if (segment.kind === 'video') cover(ctx, image, {focus: segment.focus || [.5, .5]});
      else {
        const p = still(segment, t);
        cover(ctx, image, {...p, focus: segment.focus || [.5, .5]});
        if (fg && !fg.stub) cover(ctx, fg, {s: p.s * 1.04, x: p.x * 1.8, y: p.y * 1.8, focus: segment.focus || [.5, .5]});   // the cut-out travels further
      }
      ctx.filter = 'none';
      if (grade.warmth) {   // warm or cool cast, the same on every source
        ctx.globalCompositeOperation = 'soft-light'; ctx.globalAlpha = Math.abs(grade.warmth) * 2;
        ctx.fillStyle = grade.warmth > 0 ? '#ff9a3c' : '#3c8bff'; ctx.fillRect(0, 0, env.W, env.H);
      }
      if (grade.lift) {     // lifted blacks: a film-like floor
        ctx.globalCompositeOperation = 'lighten'; ctx.globalAlpha = 1;
        const v = Math.round(255 * grade.lift); ctx.fillStyle = `rgb(${v},${v},${v})`; ctx.fillRect(0, 0, env.W, env.H);
      }
      if (darken) { ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = darken; ctx.fillStyle = '#000'; ctx.fillRect(0, 0, env.W, env.H); }
      ctx.restore();
      return {segment, drawn: true};
    }

    /* Points for the motion-blur track: the corners of a moving still (constant length whatever the segment). */
    function track(t) {
      const segment = segmentAt(t);
      if (!segment || segment.kind !== 'still') return [[0, 0], [env.W, env.H]];
      const p = still(segment, t), w = env.W * p.s, h = env.H * p.s;
      const left = (env.W - w) / 2 + p.x * (w - env.W) / 2, top = (env.H - h) / 2 + p.y * (h - env.H) / 2;
      return [[left, top], [left + w, top + h]];
    }

    return {prepare, draw, track, segmentAt, segments, MOVES};
  }

  root.Footage = {create, MOVES, GRADE};
})(typeof globalThis !== 'undefined' ? globalThis : this);
