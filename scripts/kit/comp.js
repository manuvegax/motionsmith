/* comp.js · the After Effects composition model in code: layers with anchor, position, scale, rotation and opacity on
   keyframes (the graph editor's influence and speed), parenting, precomps with time remapping, masks and track mattes,
   a 2.5D camera with depth of field, and a sequence builder whose transitions overlap two precomps the way an editor
   does it in AE. Everything is a function of time, and every layer reports where it moves, so the stage's motion blur
   follows it without a hand-written track.

     const A = window.Comp, k = A.k;
     const card = A.layer({name: 'card', position: k([0, [540, 2400]], [.6, [540, 960], 'snap']), draw: (g, t) => {...}});
     const title = A.layer({name: 'title', parent: 'card', position: [0, -120], scale: A.overshoot(.4, 60, .9, 100), draw: ...});
     const scene1 = A.comp({width: W, height: H, duration: 3, background: '#ece8de', layers: [title, card]});   // top first
     const film = A.sequence([{comp: scene1}, {comp: scene2}], [{type: 'whip', dur: .32}]);
     Stage.run({state: t => ({t, track: film.track(t)}), draw: (s, {base}) => film.render(base, s.t)});

   Keyframes: k([t, value, ease?], ...) where ease names the curve that LEAVES that key: 'easy' (AE Easy Ease, 33 %),
   'snap' (fast out, long settle: 12 % / 88 %), 'punch' (5 / 95), 'swift' (40 / 85), 'glide' (55 / 60), 'accel' (leaves
   slowly, arrives fast: 85 / 12), 'linear', 'hold', or {out, in} influences in percent. Values are numbers or arrays.
   overshoot(t0, from, t1, to, {amount, settle}) adds the overshoot key a motion designer would add by hand.
   Transitions: cut, whip, push, zoom, iris, slice, spin, flash (a flash also works on a cut). */
(function (root) {
  'use strict';
  const M = root.MotionMath, TL = root.Timeline;
  const EASES = {easy: [33.33, 33.33], snap: [12, 88], punch: [5, 95], swift: [40, 85], glide: [55, 60], accel: [85, 12], whip: [72, 72]};
  const curve = name => { const e = EASES[name] || name; return M.aeEase({outInfluence: e[0], inInfluence: e[1]}); };

  /* Motion styles: one switch for the feel of a whole piece. drift = the residual life of a layer once its last key has
     landed (px of wander, degrees of sway, % of growth per second); breathe = the slow push every scene gets (% of
     scale over the scene, degrees, px of travel); offset = frames between layers; transitions = seconds. */
  const STYLES = {
    editorial: {arrive: 'snap', slam: 'punch', exit: 'accel', offset: 3, overshoot: .06,
      drift: {px: 5, deg: .35, grow: .8}, breathe: {scale: 6, deg: .4, px: 10},
      transitions: {whip: .32, push: .45, zoom: .5, iris: .42, slice: .5, spin: .5}},
    punchy: {arrive: 'punch', slam: 'punch', exit: 'accel', offset: 2, overshoot: .1,
      drift: {px: 7, deg: .5, grow: 1.1}, breathe: {scale: 8, deg: .6, px: 14},
      transitions: {whip: .26, push: .36, zoom: .4, iris: .34, slice: .4, spin: .4}},
    calm: {arrive: 'swift', slam: 'snap', exit: 'glide', offset: 5, overshoot: .03,
      drift: {px: 3.5, deg: .25, grow: .55}, breathe: {scale: 4, deg: .25, px: 7},
      transitions: {whip: .4, push: .6, zoom: .65, iris: .55, slice: .65, spin: .65}},
    sober: {arrive: 'swift', slam: 'snap', exit: 'glide', offset: 4, overshoot: 0,
      drift: {px: 2, deg: .1, grow: .3}, breathe: {scale: 2.5, deg: .1, px: 4},
      transitions: {whip: .4, push: .6, zoom: .6, iris: .5, slice: .6, spin: .6}},
  };
  let STYLE = STYLES.editorial;
  function style(which) {
    if (which !== undefined) STYLE = typeof which === 'string' ? (STYLES[which] || STYLE) : {...STYLES.editorial, ...which};
    return STYLE;
  }
  const hashName = name => { let h = 2166136261; for (const ch of String(name)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return (h >>> 0) % 100000; };
  /* Seconds after which a layer's keys are done (its last key on position, scale or rotation), in layer time. */
  const settleTime = L => Math.max(0, ...['position', 'scale', 'rotation'].map(p => L[p] && L[p].anim ? L[p].anim.keys[L[p].anim.keys.length - 1].t : 0));

  /* ---------- keyframes ---------- */
  function k(...keys) {
    const ks = keys.map(([t, v]) => ({t, v}));
    keys.forEach(([, , ease], i) => {
      if (i === keys.length - 1 || ease === undefined) return;
      if (ease === 'hold') { ks[i].hold = true; return; }
      if (ease === 'linear') { ks[i].ease = 'linear'; return; }
      const e = typeof ease === 'string' ? EASES[ease] : [ease.out, ease.in];
      if (!e) throw new RangeError(`unknown ease ${ease}`);
      ks[i].ae = {...(ks[i].ae || {}), outInfluence: e[0]};
      ks[i + 1].ae = {...(ks[i + 1].ae || {}), inInfluence: e[1]};
    });
    return {anim: TL.track(ks)};
  }
  /* The overshoot a designer keys by hand: arrive past the target, settle back. */
  function overshoot(t0, from, t1, to, {amount = STYLE.overshoot, settle = .22, ease = 'swift'} = {}) {
    const over = Array.isArray(to) ? to.map((v, i) => v + (v - from[i]) * amount) : to + (to - from) * amount;
    return k([t0, from, ease], [t1, over, 'easy'], [t1 + settle, to]);
  }
  const val = (p, t, fallback) => p === undefined ? fallback : p && p.anim ? TL.value(p.anim, t) : typeof p === 'function' ? p(t) : p;

  /* ---------- 2D affine matrices [a, b, c, d, e, f] (the canvas order) ---------- */
  const mul = (m, n) => [m[0] * n[0] + m[2] * n[1], m[1] * n[0] + m[3] * n[1], m[0] * n[2] + m[2] * n[3], m[1] * n[2] + m[3] * n[3],
    m[0] * n[4] + m[2] * n[5] + m[4], m[1] * n[4] + m[3] * n[5] + m[5]];
  const T = (x, y) => [1, 0, 0, 1, x, y], S = (x, y) => [x, 0, 0, y, 0, 0];
  const R = deg => { const r = deg * Math.PI / 180, c = Math.cos(r), s = Math.sin(r); return [c, s, -s, c, 0, 0]; };
  const apply = (m, [x, y]) => [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]];
  const ID = [1, 0, 0, 1, 0, 0];

  /* Drawing state that save/restore does not reliably cover in every browser (letterSpacing, kerning) is reset too,
     so the same t gives the same pixels whatever was drawn before it. */
  function clean(ctx) {
    if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';
    if ('wordSpacing' in ctx) ctx.wordSpacing = '0px';
    if ('fontKerning' in ctx) ctx.fontKerning = 'auto';
    ctx.filter = 'none'; ctx.shadowColor = 'rgba(0,0,0,0)'; ctx.shadowBlur = 0; ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0;
    ctx.textAlign = 'start'; ctx.textBaseline = 'alphabetic'; ctx.globalCompositeOperation = 'source-over';
    if (ctx.setLineDash) ctx.setLineDash([]);
  }

  /* ---------- offscreen canvases, pooled ---------- */
  const pool = new Map();
  function scratch(key, w, h) {
    if (typeof root.document === 'undefined' || !root.document.createElement) return null;
    let c = pool.get(key);
    if (!c || c.width !== w || c.height !== h) {
      // CPU-rastered, like the stage's layers: a GPU canvas can give different pixels for the same t after other seeks
      c = root.document.createElement('canvas'); c.width = w; c.height = h; c.getContext('2d', {willReadFrequently: true}); pool.set(key, c);
    }
    return c;
  }

  /* ---------- layers ---------- */
  let unnamed = 0;
  function layer(o) {
    return {name: o.name || `layer${++unnamed}`, in: o.in ?? 0, out: o.out ?? Infinity, start: o.start ?? (o.in ?? 0),
      parent: o.parent, anchor: o.anchor, position: o.position, scale: o.scale, rotation: o.rotation, opacity: o.opacity,
      blur: o.blur, threeD: !!o.threeD, blend: o.blend, mask: o.mask, matte: o.matte, isMatte: !!o.isMatte,
      draw: o.draw, comp: o.comp, timeRemap: o.timeRemap, speed: o.speed ?? 1, visible: o.visible ?? true, size: o.size,
      drift: o.drift ?? true, effects: o.effects || []};
  }
  const localTime = (L, t) => L.timeRemap !== undefined ? val(L.timeRemap, t - L.start) : (t - L.start) * L.speed;

  /* ---------- compositions ---------- */
  function comp({name = 'comp', width, height, duration, background, layers = [], camera} = {}) {
    const byName = new Map(layers.map(L => [L.name, L]));
    const self = {name, width, height, duration, background, layers, camera, byName};

    /* The layer's transform at comp time t, with its parents, and (for 3D layers) the camera's projection. */
    function matrix(L, t, depth = 0) {
      if (depth > 16) throw new RangeError('comp: parenting loop');
      const lt = localTime(L, t);
      const anchor = val(L.anchor, lt, [0, 0]);
      let pos = val(L.position, lt, [width / 2, height / 2]);
      let sc = val(L.scale, lt, 100);
      sc = Array.isArray(sc) ? sc : [sc, sc];
      let rot = val(L.rotation, lt, 0), blur = val(L.blur, lt, 0);
      if (L.drift) {   // a moving hold: once the keys have landed the layer keeps breathing, never at speed zero
        const d = L.drift === true ? STYLE.drift : {...STYLE.drift, ...L.drift};
        L._settle ??= settleTime(L);
        const since = lt - L._settle, r = M.smoothstep(M.clamp(since / .6)), seed = L._seed ??= hashName(L.name);
        if (r > 0 && (d.px || d.deg || d.grow)) {
          const w = M.wiggle(lt, {freq: .22, amp: d.px, octaves: 2, seed, dims: 2});
          pos = [pos[0] + w[0] * r, pos[1] + w[1] * r, ...(pos.length > 2 ? [pos[2]] : [])];
          rot += M.wiggle(lt, {freq: .17, amp: d.deg, seed: seed + 7}) * r;
          const g = 1 + d.grow / 100 * Math.max(0, since) * r;
          sc = [sc[0] * g, sc[1] * g];
        }
      }
      if (L.threeD && camera) {   // 2.5D: perspective by depth, depth of field by distance from the focus plane
        const cam = val(camera.position, t, [width / 2, height / 2, -(camera.zoom || width * 1.4)]);
        const zoom = val(camera.zoom, t, width * 1.4), d = Math.max(1, (pos[2] || 0) - cam[2]);
        const persp = zoom / d;
        pos = [width / 2 + (pos[0] - cam[0]) * persp, height / 2 + (pos[1] - cam[1]) * persp];
        sc = [sc[0] * persp, sc[1] * persp];
        const focus = val(camera.focusDistance, t, zoom), aperture = val(camera.aperture, t, 0);
        blur += aperture * Math.abs(d - focus) / focus;
      }
      let m = mul(mul(mul(T(pos[0], pos[1]), R(rot)), S(sc[0] / 100, sc[1] / 100)), T(-anchor[0], -anchor[1]));
      if (L.parent) {
        const P = byName.get(L.parent);
        if (!P) throw new RangeError(`comp ${name}: unknown parent ${L.parent}`);
        m = mul(matrix(P, t, depth + 1).m, m);
      }
      return {m, lt, blur};
    }

    /* The layer's own pixels: transform, opacity, blur, blend, mask, then its content (a precomp or its draw). */
    function paintLayer(ctx, L, t, base, key, alpha = 1) {
      const {m, lt, blur} = matrix(L, t);
      const opacity = val(L.opacity, lt, 100) / 100 * alpha;
      if (opacity <= 0) return;
      ctx.save();
      clean(ctx);   // every layer draws from a clean state: nothing a previous frame set can leak into this one
      ctx.setTransform(...mul(base, m));
      ctx.globalAlpha *= opacity;
      if (blur > .3) ctx.filter = `blur(${blur.toFixed(2)}px)`;
      if (L.blend && !L.effects.length) ctx.globalCompositeOperation = L.blend;
      if (L.mask) { ctx.beginPath(); L.mask(ctx, lt, L); ctx.clip(); }   // an AE layer mask, in layer coordinates
      if (L.comp) {   // a precomp: render it at its own time into a canvas, then draw it as this layer's content
        const c = scratch(`${key}/${L.name}`, L.comp.width, L.comp.height);
        if (c) {
          const g = c.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, c.width, c.height);
          L.comp.render(g, lt, `${key}/${L.name}`);
          ctx.drawImage(c, 0, 0);
        }
      } else if (L.draw) L.draw(ctx, lt, L);
      ctx.restore();
    }

    /* A layer with its effects. Time effects change when it is drawn: posterize (stepped time) and echo (copies at
       earlier times, fading, behind it). Pixel effects work on the layer's own pixels in a canvas: glow, shadow,
       rgbSplit, tint, fill, lightSweep. */
    function drawLayer(ctx, L, t, base, key) {
      const fx = L.effects;
      const post = fx.find(e => e.type === 'posterize');
      if (post) { const lt = (t - L.start) * L.speed, q = Math.floor(lt * post.fps + 1e-6) / post.fps; t = L.start + q / L.speed; }
      const echo = fx.find(e => e.type === 'echo');
      const pixel = fx.filter(e => !['posterize', 'echo'].includes(e.type));
      const draw = (g, tt, b, a) => paintLayer(g, L, tt, b, key, a);
      const render = (g, b) => {
        if (echo) for (let i = echo.count || 4; i >= 1; i--) draw(g, t - i * (echo.step ?? 2 / 30), b, Math.pow(echo.decay ?? .55, i));
        draw(g, t, b, 1);
      };
      if (!pixel.length) { render(ctx, base); return; }
      const E = scratch(`${key}/${L.name}#fx`, width, height);
      if (!E) { render(ctx, base); return; }
      const ge = E.getContext('2d'); ge.setTransform(1, 0, 0, 1, 0, 0); ge.clearRect(0, 0, width, height);
      render(ge, ID);
      const lt = localTime(L, t);
      for (const e of pixel) applyEffect(E, e, lt, key, L.name);
      ctx.save(); clean(ctx); ctx.setTransform(...base);
      if (L.blend) ctx.globalCompositeOperation = L.blend;
      const shadow = pixel.find(e => e.type === 'shadow');
      if (shadow) {   // a drop shadow from the layer's alpha
        ctx.shadowColor = shadow.color || 'rgba(0,0,0,.35)'; ctx.shadowBlur = shadow.blur ?? width * .03;
        ctx.shadowOffsetX = shadow.x ?? 0; ctx.shadowOffsetY = shadow.y ?? width * .015;
      }
      const glow = pixel.find(e => e.type === 'glow');
      if (glow) {   // the glow sits under the layer's pixels, added or screened
        const G = scratch(`${key}/${L.name}#glow`, width, height), gg = G.getContext('2d');
        gg.setTransform(1, 0, 0, 1, 0, 0); gg.clearRect(0, 0, width, height);
        gg.filter = `blur(${(glow.radius ?? width * .025).toFixed(1)}px)`; gg.drawImage(E, 0, 0); gg.filter = 'none';
        if (glow.color) { gg.globalCompositeOperation = 'source-in'; gg.fillStyle = glow.color; gg.fillRect(0, 0, width, height); gg.globalCompositeOperation = 'source-over'; }
        ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0)'; ctx.globalCompositeOperation = glow.mode || 'lighter';
        const strength = glow.strength ?? .8;
        ctx.globalAlpha = Math.min(1, strength); ctx.drawImage(G, 0, 0);
        if (strength > 1) { ctx.globalAlpha = strength - 1; ctx.drawImage(G, 0, 0); }
        ctx.restore();
      }
      ctx.drawImage(E, 0, 0);
      ctx.restore();
    }

    function applyEffect(E, e, lt, key, name) {
      const g = E.getContext('2d');
      g.save(); g.setTransform(1, 0, 0, 1, 0, 0);
      if (e.type === 'fill') { g.globalCompositeOperation = 'source-in'; g.fillStyle = e.color || '#fff'; g.fillRect(0, 0, width, height); }
      if (e.type === 'tint') { g.globalCompositeOperation = 'source-atop'; g.globalAlpha = e.amount ?? .5; g.fillStyle = e.color || '#ff3b23'; g.fillRect(0, 0, width, height); }
      if (e.type === 'lightSweep') {   // a band of light crossing the layer, only where the layer is
        const at = e.at ?? 0, dur = e.dur ?? .8, u = e.period ? (lt % e.period) / Math.min(dur, e.period) : (lt - at) / dur;
        if (u > 0 && u < 1) {
          const a = (e.angle ?? -20) * Math.PI / 180, w = (e.width ?? .18) * width, x = M.mix(-.3, 1.3, curve('swift')(u)) * width;
          const dx = Math.cos(a) * w, dy = Math.sin(a) * w, grad = g.createLinearGradient(x - dx, height / 2 - dy, x + dx, height / 2 + dy);
          grad.addColorStop(0, 'rgba(255,255,255,0)'); grad.addColorStop(.5, `rgba(255,255,255,${e.intensity ?? .55})`); grad.addColorStop(1, 'rgba(255,255,255,0)');
          g.globalCompositeOperation = 'source-atop'; g.fillStyle = grad; g.fillRect(0, 0, width, height);
        }
      }
      if (e.type === 'rgbSplit') {   // chromatic aberration: each channel offset along an angle, added back together
        const px = typeof e.px === 'function' ? e.px(lt) : (e.px ?? 4), a = (e.angle ?? 0) * Math.PI / 180;
        if (px > .2) {
          const X = scratch(`${key}/${name}#rgb`, width, height), C = scratch(`${key}/${name}#ch`, width, height);
          const gx = X.getContext('2d'), gc = C.getContext('2d');
          gx.setTransform(1, 0, 0, 1, 0, 0); gx.clearRect(0, 0, width, height); gx.globalCompositeOperation = 'lighter';
          [['#ff0000', -1], ['#00ff00', 0], ['#0000ff', 1]].forEach(([colour, k]) => {
            gc.setTransform(1, 0, 0, 1, 0, 0); gc.globalCompositeOperation = 'copy'; gc.drawImage(E, 0, 0);
            gc.globalCompositeOperation = 'multiply'; gc.fillStyle = colour; gc.fillRect(0, 0, width, height);
            gc.globalCompositeOperation = 'destination-in'; gc.drawImage(E, 0, 0); gc.globalCompositeOperation = 'source-over';
            gx.drawImage(C, Math.cos(a) * px * k, Math.sin(a) * px * k);
          });
          gx.globalCompositeOperation = 'source-over';
          g.globalCompositeOperation = 'copy'; g.drawImage(X, 0, 0);
        }
      }
      g.restore();
    }

    /* Draw the comp at time t onto ctx (its current transform is the comp's origin). */
    function render(ctx, t, key = name) {
      const base = ctx.getTransform ? (m => [m.a, m.b, m.c, m.d, m.e, m.f])(ctx.getTransform()) : ID;
      if (background) {
        ctx.save();
        if (typeof background === 'function') background(ctx, t); else { ctx.fillStyle = background; ctx.fillRect(0, 0, width, height); }
        ctx.restore();
      }
      for (let i = layers.length - 1; i >= 0; i--) {   // AE order: the first layer is on top
        const L = layers[i];
        if (!L.visible || L.isMatte || t < L.in || t >= L.out) continue;
        if (L.matte) {   // track matte: the layer through the alpha of another layer
          const A = scratch(`${key}/${L.name}#a`, width, height), B = scratch(`${key}/${L.name}#b`, width, height);
          const src = byName.get(L.matte.layer);
          if (!A || !src) { drawLayer(ctx, L, t, base, key); continue; }
          const ga = A.getContext('2d'), gb = B.getContext('2d');
          for (const g of [ga, gb]) { g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, width, height); }
          drawLayer(ga, L, t, ID, key); drawLayer(gb, src, t, ID, key);
          ga.setTransform(1, 0, 0, 1, 0, 0);
          ga.globalCompositeOperation = L.matte.invert ? 'destination-out' : 'destination-in';
          ga.drawImage(B, 0, 0); ga.globalCompositeOperation = 'source-over';
          ctx.save(); ctx.setTransform(...base); ctx.drawImage(A, 0, 0); ctx.restore();
        } else drawLayer(ctx, L, t, base, key);
      }
    }

    /* Where things move: two points per layer (its anchor and a point 100 px along its x axis), every layer, visible
       or not, so the list keeps one length at every t (the stage's motion blur measures the fastest point). Precomps
       add their own layers' points, mapped through the precomp layer. */
    function track(t, outer = ID) {
      const pts = [];
      for (const L of layers) {
        const live = L.visible && !L.isMatte && t >= L.in && t < L.out;
        const {m} = live ? matrix(L, t) : {m: ID};
        const w = mul(outer, m), anchor = val(L.anchor, live ? localTime(L, t) : 0, [0, 0]);
        pts.push(live ? apply(w, anchor) : [0, 0], live ? apply(w, [anchor[0] + 100, anchor[1]]) : [0, 0]);
        if (L.comp) pts.push(...L.comp.track(live ? localTime(L, t) : 0, live ? w : ID).map(p => live ? p : [0, 0]));
      }
      return pts;
    }
    return Object.assign(self, {render, track, matrix: (n, t) => matrix(byName.get(n), t).m});
  }

  /* ---------- transitions: how two overlapping precomps hand over ---------- */
  /* Each returns {out(u) → props of the outgoing layer, in(u) → props of the incoming one, mask?, flash?} for u in 0..1
     across the overlap. Props: dx, dy (px), scale (multiplier), rot (deg), opacity (0..1), blur (px), anchor point. */
  const TRANSITIONS = {
    cut: () => ({out: () => ({}), in: () => ({})}),
    whip: ({dir = 'left', W, H}) => {   // a camera pan across a whole frame: both scenes travel together, eased hard
      const e = curve('whip'), sx = dir === 'left' ? -1 : dir === 'right' ? 1 : 0, sy = dir === 'up' ? -1 : dir === 'down' ? 1 : 0;
      return {out: u => ({dx: sx * W * e(u), dy: sy * H * e(u)}), in: u => ({dx: -sx * W * (1 - e(u)), dy: -sy * H * (1 - e(u))})};
    },
    push: ({dir = 'left', W, H}) => {   // the new scene pushes the old one out and lands with a small overshoot
      const e = curve('swift'), o = M.easing('back.out'), sx = dir === 'left' ? -1 : dir === 'right' ? 1 : 0, sy = dir === 'up' ? -1 : dir === 'down' ? 1 : 0;
      return {out: u => ({dx: sx * W * e(u) * .55, dy: sy * H * e(u) * .55, scale: 1 - .06 * e(u)}),
        in: u => ({dx: -sx * W * (1 - o(u)), dy: -sy * H * (1 - o(u))})};
    },
    zoom: ({at, W, H}) => {   // through a point: the old scene accelerates into it until it fills the frame; on the
      // swap (half way, under the flash) the new scene takes over already moving forward and settles. No crossfade.
      const p = at || [W / 2, H / 2], land = curve('snap'), into = M.easing('expo.in');
      return {out: u => ({scale: 1 + 26 * into(M.clamp(u / .5)), anchor: p, opacity: u < .5 ? 1 : 0}),
        in: u => { const v = land(M.clamp((u - .5) / .5)); return {scale: M.mix(1.6, 1, v), anchor: [W / 2, H / 2], blur: 28 * (1 - v), opacity: u >= .5 ? 1 : 0}; }};   // from 160 %: no edge shows
    },
    iris: ({at, W, H}) => {   // the new scene opens from a point in a circle; the old one steps back
      const p = at || [W / 2, H / 2], e = curve('snap'), R = Math.hypot(W, H);
      return {out: u => ({scale: 1 - .05 * curve('swift')(u), anchor: p}),
        in: () => ({}), mask: (g, u) => { g.arc(p[0], p[1], Math.max(.5, R * e(u)), 0, Math.PI * 2); }};
    },
    slice: ({n = 5, dir = 'up', W, H}) => {   // bars sweep the new scene in, one after another
      const e = curve('snap');
      return {out: u => ({dy: -H * .08 * curve('accel')(u)}), in: () => ({}), mask: (g, u) => {
        for (let i = 0; i < n; i++) {
          const v = e(M.clamp((u - i * .08) / (1 - (n - 1) * .08)));
          if (dir === 'up') g.rect(i * W / n, H * (1 - v), W / n + 1, H * v + 1); else g.rect(0, i * H / n, W * v, H / n + 1);
        }
      }};
    },
    spin: ({W, H}) => {   // the old scene spins away accelerating; the new one spins in from the other side, swap on the half
      const out = M.easing('expo.in'), land = curve('snap');
      return {out: u => ({rot: -35 * out(M.clamp(u / .5)), scale: 1 + .8 * out(M.clamp(u / .5)), anchor: [W / 2, H / 2], opacity: u < .5 ? 1 : 0}),
        in: u => { const v = land(M.clamp((u - .5) / .5)); return {rot: 35 * (1 - v), scale: M.mix(1.8, 1, v), anchor: [W / 2, H / 2], opacity: u >= .5 ? 1 : 0}; }};
    },
  };

  /* A film from scenes: [{comp, duration?}], transitions between them [{type, dur, flash, ...}]. Each scene becomes a
     precomp layer; a transition overlaps the end of one with the start of the next by `dur` seconds and drives both
     layers' transforms (and the incoming layer's mask). flash: a colour that blinks for two frames on the cut. */
  function sequence(scenes, transitions = [], {width, height, fps = 30, background = '#000', breathe} = {}) {
    const W = width || scenes[0].comp.width, H = height || scenes[0].comp.height;
    const starts = [0];
    scenes.forEach((s, i) => { if (i) starts.push(starts[i - 1] + (scenes[i - 1].duration ?? scenes[i - 1].comp.duration) - ((transitions[i - 1] || {}).dur || 0)); });
    const duration = starts[starts.length - 1] + (scenes[scenes.length - 1].duration ?? scenes[scenes.length - 1].comp.duration);
    const fx = transitions.map(tr => (TRANSITIONS[tr.type] || TRANSITIONS.cut)({...tr, W, H}));
    const layersList = scenes.map((s, i) => {
      const len = s.duration ?? s.comp.duration, inT = starts[i];
      const tin = i > 0 ? {fx: fx[i - 1], t0: starts[i], dur: transitions[i - 1].dur || 0} : null;
      const tout = i < scenes.length - 1 ? {fx: fx[i], t0: starts[i + 1], dur: transitions[i].dur || 0} : null;
      const br = s.breathe === false ? null : {...STYLE.breathe, ...(breathe || {}), ...(s.breathe || {})}, seed = 31 + i * 17;
      const props = t => {   // this scene's transform at comp time t, from the transitions around it
        let p = {};
        if (tin && tin.dur > 0 && t < tin.t0 + tin.dur) p = tin.fx.in(M.clamp((t - tin.t0) / tin.dur));
        if (tout && tout.dur > 0 && t >= tout.t0) p = {...p, ...tout.fx.out(M.clamp((t - tout.t0) / tout.dur))};
        return p;
      };
      // breathe: every scene pushes in slowly for its whole life and sways a little, so no shot is ever frozen,
      // including the last one (the slow push editors put on every shot). The push eases in over the first fifth and
      // then keeps a constant speed to the last frame: an ease-out would bring it to rest exactly where the shot ends.
      // Overscan: the sway and the tilt would show the comp's edge, so the scene starts just large enough to cover them
      // (what an editor does with 103-104 % under a handheld move). `breathe: {overscan: false}` turns it off.
      const over = !br || br.overscan === false ? 1 : 1 + .002 +
        2 * (br.px * 1.05 + Math.max(W, H) / 2 * Math.sin(br.deg * Math.PI / 180)) / Math.min(W, H);
      const push = t => {
        if (!br) return 1;
        const u = Math.max(0, t / len), a = .2;
        const f = u < a ? u * u / (2 * a) : u - a / 2;
        return over * (1 + br.scale / 100 * f / (1 - a / 2));
      };
      const sway = t => br ? M.wiggle(t, {freq: .12, amp: br.px, seed, dims: 2}) : [0, 0];
      return layer({name: `scene${i}`, in: inT, out: inT + len, start: inT, comp: s.comp, drift: false,
        anchor: t => (props(t + inT).anchor || [W / 2, H / 2]),
        position: t => { const p = props(t + inT), a = p.anchor || [W / 2, H / 2], w = sway(t); return [a[0] + (p.dx || 0) + w[0], a[1] + (p.dy || 0) + w[1]]; },
        scale: t => 100 * (props(t + inT).scale ?? 1) * push(t),
        rotation: t => (props(t + inT).rot || 0) + (br ? M.wiggle(t, {freq: .1, amp: br.deg, seed: seed + 3}) : 0),
        opacity: t => 100 * (props(t + inT).opacity ?? 1), blur: t => props(t + inT).blur || 0,
        mask: tin && tin.fx.mask ? (g, t) => {
          const u = M.clamp((t + inT - tin.t0) / Math.max(tin.dur, 1e-6));
          if (u >= 1) g.rect(-W, -H, W * 3, H * 3); else tin.fx.mask(g, u);
        } : undefined});
    });
    // The later scene sits on top during an overlap (AE: the incoming clip on the layer above).
    const ordered = layersList.slice().reverse();
    transitions.forEach((tr, i) => {
      if (!tr.flash) return;
      const at = starts[i + 1] + (tr.dur || 0) / 2;
      ordered.unshift(layer({name: `flash${i}`, in: at - .5 / fps, out: at + 2 / fps, drift: false, draw: g => { g.fillStyle = tr.flash; g.fillRect(0, 0, W, H); },
        position: [0, 0], opacity: t => 100 * (1 - M.clamp((t - .5 / fps) / (1.5 / fps)))}));
    });
    const film = comp({name: 'film', width: W, height: H, duration, background, layers: ordered});
    film.starts = starts;
    film.cuts = transitions.map((tr, i) => ({at: starts[i + 1], end: starts[i + 1] + (tr.dur || 0), type: tr.type || 'cut'}));
    return film;
  }

  root.Comp = {k, overshoot, value: val, layer, comp, sequence, style, STYLES, EASES, TRANSITIONS, curve, matrix: {mul, T, S, R, apply}};
})(typeof globalThis !== 'undefined' ? globalThis : this);
