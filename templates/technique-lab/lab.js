/* Motionsmith technique lab.
   Each technique has a code (A1, D3…) so a viewer can answer with the ones they like (and record them in a taste profile).
   Pipeline per frame: each tile is drawn in Canvas 2D (base layer + an emissive layer that becomes HDR light),
   accumulated in float with its own motion-blur samples (MotionMath.exposureTimes), then post-processed with
   PostFX restricted to the tile (scissor). Labels are drawn last, crisp, on top. Everything depends only on t. */
(() => {
  'use strict';
  const W = 1080, H = 1920, FPS = 60;
  const M = window.MotionMath, P = window.PostFX;
  const INK = '#101110', PAPER = '#efeee8', RED = '#ff422e', BG = '#121214', MUTED = '#9a9aa2';
  const FONT = '"Segoe UI", "Helvetica Neue", Arial, sans-serif';
  const gl = document.getElementById('art').getContext('webgl', {alpha: false, antialias: false, preserveDrawingBuffer: true});
  if (!gl) throw new Error('WebGL required');
  const fx = P.runner(gl, {width: W, height: H});
  if (!fx.hdr) throw new Error('Half-float render targets required for the HDR demos');
  const accum = fx.target(), tmp = fx.target(), tmp2 = fx.target(), bgOnly = fx.target(), alphaT = fx.target(), alphaB = fx.target(), alphaB2 = fx.target();

  /* ---------- textures fed from Canvas 2D ---------- */
  function texture() {
    const t = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, W, H, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
    for (const k of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, k, gl.LINEAR);
    for (const k of [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T]) gl.texParameteri(gl.TEXTURE_2D, k, gl.CLAMP_TO_EDGE);
    return t;
  }
  const baseTex = texture(), glowTex = texture(), fgTex = texture(), overlayTex = texture();
  function upload(tex, canvas, rect) {
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    if (rect) gl.texSubImage2D(gl.TEXTURE_2D, 0, rect.x, H - rect.y - rect.h, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
    else gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
  }
  const scissorOf = r => [r.x, H - r.y - r.h, r.w, r.h];
  function clearRegion(target, rect, color) {
    gl.bindFramebuffer(gl.FRAMEBUFFER, target.fb);
    gl.viewport(0, 0, W, H);
    if (rect) { gl.enable(gl.SCISSOR_TEST); gl.scissor(...scissorOf(rect)); }
    gl.clearColor(...color, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.disable(gl.SCISSOR_TEST);
  }
  /* base (sRGB) + emissive (sRGB × gain) in linear light; optional foreground composited over with its alpha. */
  const COMPOSE = `precision highp float;varying vec2 uv;uniform sampler2D base,glow,fg;uniform float gain,weight,useFg;
    void main(){vec3 c=pow(texture2D(base,uv).rgb,vec3(2.2))+pow(texture2D(glow,uv).rgb,vec3(2.2))*gain;
      if(useFg>.5){vec4 f=texture2D(fg,uv);c=mix(c,pow(f.rgb,vec3(2.2)),f.a);}
      gl_FragColor=vec4(c*weight,1.);}`;
  const OVER = 'precision highp float;varying vec2 uv;uniform sampler2D image,fg;void main(){vec4 f=texture2D(fg,uv);gl_FragColor=vec4(mix(texture2D(image,uv).rgb,pow(f.rgb,vec3(2.2)),f.a),1.);}';
  const ALPHA = 'precision highp float;varying vec2 uv;uniform sampler2D fg;void main(){float a=texture2D(fg,uv).a;gl_FragColor=vec4(a,a,a,a);}';

  /* ---------- per-size 2D canvases ---------- */
  const pool = new Map();
  function canvases(w, h) {
    const key = `${w}x${h}`;
    if (!pool.has(key)) {
      const make = () => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
      const base = make(), glow = make(), fg = make();
      // CPU raster (willReadFrequently): GPU canvases cache glyphs and can change text by 1–2 levels depending on history.
      const ctx = c => c.getContext('2d', {willReadFrequently: true});
      pool.set(key, {base, glow, fg, bc: ctx(base), gc: ctx(glow), fc: ctx(fg)});
    }
    return pool.get(key);
  }
  const overlay = document.createElement('canvas');
  overlay.width = W; overlay.height = H;
  const oc = overlay.getContext('2d', {willReadFrequently: true});

  /* ---------- small drawing helpers (tile-local coordinates) ---------- */
  function reset(c) { c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1; c.filter = 'none'; c.globalCompositeOperation = 'source-over'; }
  function text(c, str, x, y, size, color, {weight = 600, align = 'left', baseline = 'alphabetic', alpha = 1} = {}) {
    c.save(); c.globalAlpha = alpha; c.font = `${weight} ${size}px ${FONT}`; c.fillStyle = color; c.textAlign = align; c.textBaseline = baseline;
    c.fillText(str, x, y); c.restore();
  }
  function disc(c, x, y, r, color) { c.beginPath(); c.arc(x, y, r, 0, M.TAU); c.fillStyle = color; c.fill(); }
  function rrect(c, x, y, w, h, r, color) { c.beginPath(); c.roundRect(x, y, w, h, r); c.fillStyle = color; c.fill(); }
  function gridLines(c, w, h, step, color, offsetX = 0, offsetY = 0) {
    c.save(); c.strokeStyle = color; c.lineWidth = 1; c.beginPath();
    for (let x = ((offsetX % step) + step) % step; x <= w; x += step) { c.moveTo(x + .5, 0); c.lineTo(x + .5, h); }
    for (let y = ((offsetY % step) + step) % step; y <= h; y += step) { c.moveTo(0, y + .5); c.lineTo(w, y + .5); }
    c.stroke(); c.restore();
  }
  const fmt = n => n.toFixed(1).replace('.', ',');

  /* ---------- layout ---------- */
  function cells(cols, rows, {x = 60, y = 380, w = 960, h = 1380, gap = 36} = {}) {
    const cw = Math.floor((w - gap * (cols - 1)) / cols), ch = Math.floor((h - gap * (rows - 1)) / rows), out = [];
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) out.push({x: x + c * (cw + gap), y: y + r * (ch + gap), w: cw, h: ch});
    return out;
  }
  const pingpong = (local, go, hold) => {          // forward, hold, backward, hold → {dir, u}
    const period = 2 * (go + hold), p = M.loop(local, period);
    if (p < go) return {dir: 1, u: p / go};
    if (p < go + hold) return {dir: 1, u: 1};
    if (p < 2 * go + hold) return {dir: -1, u: (p - go - hold) / go};
    return {dir: -1, u: 1};
  };

  /* ================= cards ================= */
  const CARDS = [];
  let cursor = 2.5;
  function card(spec) { spec.start = cursor; spec.end = cursor + spec.duration; cursor = spec.end; CARDS.push(spec); return spec; }

  /* ---- A · curves ---- */
  const A_EASES = [
    ['A1', 'Linear', M.easing('linear')],
    ['A2', 'Quartic ease-out (power3)', M.easing('power3.out')],
    ['A3', 'Easy Ease (33 %)', M.easing('easyEase')],
    ['A4', 'Influence 80/80 (snappy)', M.aeEase({outInfluence: 80, inInfluence: 80})],
    ['A5', 'Back · overshoot', M.easing('back.out')],
    ['A6', 'Spring ζ 0.5', u => M.spring(u * 1.1, {freq: 1.6, damping: .5})],
    ['A7', 'Cubic ease-out (cubic.out)', M.easing('cubic.out')],
  ];
  const A_GO = 1.1, A_HOLD = .5;
  function aProgress(e, local) {
    const {dir, u} = pingpong(local, A_GO, A_HOLD), end = e(1);
    return dir > 0 ? e(u) : end * (1 - e(u));
  }
  const A_STATS = A_EASES.map(([, , e]) => {
    const n = 400, sp = [];
    for (let i = 0; i < n; i++) sp.push((e((i + 1) / n) - e(i / n)) * n);
    return {speeds: sp, peak: Math.max(...sp.map(Math.abs))};
  });
  card({id: 'A', title: 'Curves', subtitle: 'The same path with seven curves. Below, their speed graphs.', duration: 5,
    shutter: 180, samples: 16,
    tiles: cells(1, 7, {gap: 14}).map((rect, i) => ({rect, code: A_EASES[i][0], name: A_EASES[i][1],
      detail: `peak ${fmt(A_STATS[i].peak)}× the mean speed`,
      draw(c, g, local) {
        const w = rect.w, x0 = 70, x1 = w - 70, p = aProgress(A_EASES[i][2], local);
        c.strokeStyle = '#2a2a30'; c.lineWidth = 2; c.beginPath(); c.moveTo(x0, 122); c.lineTo(x1, 122); c.stroke();
        const sp = A_STATS[i].speeds, gy0 = rect.h - 8, gh = Math.min(38, rect.h - 158);
        c.strokeStyle = '#55555c'; c.lineWidth = 2; c.beginPath();
        sp.forEach((v, k) => { const x = x0 + (x1 - x0) * k / (sp.length - 1), y = gy0 - Math.max(-.3, v) / A_STATS[i].peak * gh; k ? c.lineTo(x, y) : c.moveTo(x, y); });
        c.stroke();
        const {u} = pingpong(local, A_GO, A_HOLD), px = x0 + (x1 - x0) * u;
        c.strokeStyle = RED; c.globalAlpha = .7; c.beginPath(); c.moveTo(px, gy0 - gh - 6); c.lineTo(px, gy0 + 4); c.stroke(); c.globalAlpha = 1;
        const x = x0 + (x1 - x0) * p;
        disc(c, x, 122, 20, PAPER); disc(c, x, 122, 8, RED);
      }})),
  });

  /* ---- B · principles ---- */
  const B_GO = 1.2, B_HOLD = .4;
  function bPlain(local) { const {dir, u} = pingpong(local, B_GO, B_HOLD), e = M.easing('sine.inOut')(u); return dir > 0 ? e : 1 - e; }
  function bAlive(local) {
    const {dir, u} = pingpong(local, B_GO, B_HOLD), tau = u * B_GO, A = .18;
    const go = tau < A ? -.08 * Math.sin(Math.PI / 2 * tau / A) : -.08 + 1.08 * M.spring(tau - A, {freq: 1.5, damping: .42});
    return dir > 0 ? go : 1 - go;
  }
  const B_P0 = [70, 560], B_P1 = [392, 150];
  card({id: 'B', title: 'Principles', subtitle: 'Anticipation, overshoot, follow-through and arcs vs the flat version.', duration: 5,
    shutter: 180, samples: 12,
    tiles: [
      {code: 'B1', name: 'No anticipation', detail: 'ease-in-out, dead stop'},
      {code: 'B2', name: 'Anticipate · overshoot · follow', detail: 'pull back, spring, squash, trailing antenna'},
      {code: 'B3', name: 'Straight line', detail: 'mechanical path'},
      {code: 'B4', name: 'Arc', detail: 'organic path, auto-orient'},
    ].map((d, i, all) => {
      const rect = cells(2, 2)[i];
      return {...d, rect, draw(c, g, local) {
        const w = rect.w, h = rect.h;
        if (i < 2) {
          const f = i === 0 ? bPlain : bAlive, span = w - 140 - 100, p = f(local);
          const x = 70 + span * p, y = h * .55;
          const v = (f(local + .004) - f(local - .004)) / .008 * span;
          const sq = i === 1 ? M.squashStretch(v, {k: .00011, max: .3}) : {along: 1, across: 1};
          c.fillStyle = 'rgba(0,0,0,.45)'; c.beginPath(); c.ellipse(x + 50, y + 62, 58 * sq.along, 10, 0, 0, M.TAU); c.fill();
          c.save(); c.translate(x + 50, y + 50); c.scale(sq.along, sq.across);
          rrect(c, -50, -50, 100, 100, 18, RED); c.restore();
          if (i === 1) {
            const lag = f(local - .09), ax = 70 + span * lag + 50;
            c.strokeStyle = PAPER; c.lineWidth = 4; c.beginPath(); c.moveTo(x + 50, y - 50 * sq.across); c.lineTo(ax, y - 120); c.stroke();
            disc(c, ax, y - 120, 14, PAPER);
          }
          c.strokeStyle = '#2a2a30'; c.lineWidth = 2; c.beginPath(); c.moveTo(40, y + 72); c.lineTo(w - 40, y + 72); c.stroke();
        } else {
          const {dir, u} = pingpong(local, 1.0, .3), e = M.easing('power2.inOut')(u), q = dir > 0 ? e : 1 - e;
          const path = i === 2 ? s => [M.mix(B_P0[0], B_P1[0], s), M.mix(B_P0[1], B_P1[1], s)] : s => M.arcPoint(s, B_P0, B_P1, -.175);
          c.strokeStyle = '#3a3a42'; c.setLineDash([6, 10]); c.lineWidth = 2; c.beginPath();
          for (let k = 0; k <= 40; k++) { const [px, py] = path(k / 40); k ? c.lineTo(px, py) : c.moveTo(px, py); }
          c.stroke(); c.setLineDash([]);
          const [x, y] = path(q), [nx, ny] = path(Math.min(1, q + .01)), [bx, by] = path(Math.max(0, q - .01));
          const angle = Math.atan2(ny - by, nx - bx) + (dir < 0 ? Math.PI : 0);
          c.save(); c.translate(x, y); if (i === 3) c.rotate(angle);
          c.beginPath(); c.moveTo(34, 0); c.lineTo(-24, -22); c.lineTo(-12, 0); c.lineTo(-24, 22); c.closePath(); c.fillStyle = PAPER; c.fill();
          c.restore();
        }
      }};
    }),
  });

  /* ---- C · stagger ---- */
  const C_MODES = [
    {code: 'C1', name: 'From the start', detail: 'reading order', opts: {from: 'start'}, each: .55 / 35},
    {code: 'C2', name: 'From the centre', detail: 'grid distance', opts: {from: 'center', grid: [6, 6]}, each: .55 / Math.hypot(2.5, 2.5)},
    {code: 'C3', name: 'Seeded random', detail: 'same order every render', opts: {from: 'random', seed: 7}, each: .55 / 35},
    {code: 'C4', name: 'Wave from a corner', detail: 'grid + power2.out curve', opts: {from: 'start', grid: [6, 6], curve: 'power2.out'}, each: .55 / Math.hypot(5, 5)},
  ];
  card({id: 'C', title: 'Cascades', subtitle: 'The same pop in four orders. Total cascade ≤ 0.55 s.', duration: 4.5,
    shutter: 180, samples: 8,
    tiles: C_MODES.map((d, i) => {
      const rect = cells(2, 2)[i];
      return {...d, rect, draw(c, g, local) {
        const cycle = M.loop(local, 2.25), step = Math.min(rect.w, rect.h - 120) / 7;
        const ox = (rect.w - step * 5) / 2, oy = 120 + (rect.h - 120 - step * 5) / 2;
        for (let k = 0; k < 36; k++) {
          const delay = M.stagger(k, 36, {...d.opts, each: d.each});
          const inU = M.clamp((cycle - delay) / .32), outU = M.clamp((cycle - 1.25 - delay) / .28);
          const s = M.easing('back.out')(inU) * (1 - M.easing('power2.in')(outU));
          if (s <= 0) continue;
          disc(c, ox + (k % 6) * step, oy + Math.floor(k / 6) * step, step * .3 * s, delay === 0 ? RED : PAPER);
        }
      }};
    }),
  });

  /* ---- D · motion blur ---- */
  const D_GO = .35, D_HOLD = .65, D_TRAVEL = 530;
  const dPeak = (() => { const e = M.easing('expo.inOut'); let m = 0; for (let i = 0; i < 1000; i++) m = Math.max(m, (e((i + 1) / 1000) - e(i / 1000)) * 1000); return m * D_TRAVEL / D_GO; })();
  const D_SHUTTERS = [[0, 1], [180, 30], [360, 60], [720, 120]];   // gap between copies ≤ 3 px
  card({id: 'D', title: 'Motion blur', subtitle: 'The same whip with four shutters (real sub-samples).', duration: 5,
    tiles: cells(1, 4, {gap: 24}).map((rect, i) => ({rect, code: `D${i + 1}`, name: `Shutter ${D_SHUTTERS[i][0]}°`,
      detail: i ? `≈ ${Math.round(M.pxPerExposure(dPeak, D_SHUTTERS[i][0]))} px per exposure at the peak · ${D_SHUTTERS[i][1]} samples` : 'no blur: there is no trail',
      shutter: D_SHUTTERS[i][0], samples: D_SHUTTERS[i][1],
      draw(c, g, local) {
        gridLines(c, rect.w, rect.h, 60, '#1d1d22');
        const {dir, u} = pingpong(local, D_GO, D_HOLD), e = M.easing('expo.inOut')(u), q = dir > 0 ? e : 1 - e;
        const x = 50 + D_TRAVEL * q, y = rect.h - 190 - 24;
        rrect(c, x, y, 330, 190, 16, PAPER); c.fillStyle = RED; c.fillRect(x, y, 16, 190);
        text(c, 'FOCUS', x + 175, y + 132, 104, INK, {weight: 800, align: 'center'});
      }})),
  });

  /* ---- E · blur types ---- */
  const E_DOTS = Array.from({length: 14}, (_, k) => [M.hash(k, 11), M.hash(k, 12), .6 + .4 * M.hash(k, 13)]);
  function eContent(c, g, rect) {
    gridLines(c, rect.w, rect.h, 46, '#24242a');
    text(c, 'FOCUS', rect.w / 2, rect.h * .62, 120, PAPER, {weight: 800, align: 'center'});
    disc(c, rect.w * .74, rect.h * .3, 34, RED);
    for (const [hx, hy, k] of E_DOTS) disc(g, 40 + hx * (rect.w - 80), 130 + hy * (rect.h - 200), 5 * k, '#ffffff');
  }
  /* E5: city lights at night behind a sharp subject. Light colours and sizes are seeded (same every render). */
  const E_LIGHTS = Array.from({length: 46}, (_, k) => ({x: M.hash(k, 31), y: M.hash(k, 32), s: M.hash(k, 33), warm: M.hash(k, 34) < .62}));
  function eNight(c, g, rect) {
    const sky = c.createLinearGradient(0, 0, 0, rect.h);
    sky.addColorStop(0, '#0b0d16'); sky.addColorStop(1, '#1a1214'); c.fillStyle = sky; c.fillRect(0, 0, rect.w, rect.h);
    c.fillStyle = '#20202a';
    for (let k = 0; k < 7; k++) c.fillRect(k * rect.w / 7 + 6, rect.h * (.45 + .25 * M.hash(k, 35)), rect.w / 7 - 12, rect.h);
    for (const L of E_LIGHTS) disc(g, L.x * rect.w, 110 + L.y * (rect.h - 150), 2.5 + 3.5 * L.s, L.warm ? '#ffb070' : '#9fc4ff');
  }
  function eSubject(f, rect) {
    f.fillStyle = '#efeee8'; f.beginPath(); f.roundRect(rect.w * .2, rect.h * .5, rect.w * .6, 150, 18); f.fill();
    f.fillStyle = '#ff422e'; f.fillRect(rect.w * .2, rect.h * .5, 14, 150);
    f.font = `800 96px ${FONT}`; f.fillStyle = '#101110'; f.textAlign = 'center'; f.fillText('FOCUS', rect.w / 2 + 8, rect.h * .5 + 110);
  }
  const eAmount = local => .5 - .5 * Math.cos(M.TAU * local / 2.5);
  const centerUv = rect => [(rect.x + rect.w / 2) / W, 1 - (rect.y + rect.h / 2) / H];
  const E_TILES = [
    {code: 'E1', name: 'Directional', detail: 'a trail on one axis (Directional Blur)', post: (r, a) => { fx.pass('directionalBlur', {to: tmp, scissor: scissorOf(r), textures: {image: accum}, uniforms: {dir: [a * .05, 0], samples: {int: 48}}}); return tmp; }},
    {code: 'E2', name: 'Radial zoom', detail: 'push-through, impact', post: (r, a) => { fx.pass('radialBlur', {to: tmp, scissor: scissorOf(r), textures: {image: accum}, uniforms: {center: centerUv(r), amount: a * .35, aspect: W / H, samples: {int: 48}, spin: {int: 0}}}); return tmp; }},
    {code: 'E3', name: 'Spin', detail: 'fast rotations', post: (r, a) => { fx.pass('radialBlur', {to: tmp, scissor: scissorOf(r), textures: {image: accum}, uniforms: {center: centerUv(r), amount: a * .6, aspect: W / H, samples: {int: 48}, spin: {int: 1}}}); return tmp; }},
    {code: 'E4', name: 'Box (Fast Box Blur)', detail: 'points turn square: no lens shape', post: (r, a) => {
      fx.pass('directionalBlur', {to: tmp, scissor: scissorOf(r), textures: {image: accum}, uniforms: {dir: [a * .03, 0], samples: {int: 32}}});
      fx.pass('directionalBlur', {to: tmp2, scissor: scissorOf(r), textures: {image: tmp}, uniforms: {dir: [0, a * .03 * W / H], samples: {int: 32}}}); return tmp2; }},
    {code: 'E5', name: 'Real lens · bokeh', detail: 'sharp subject, bright-rimmed discs, cat-eye', lens: true},
    {code: 'E6', name: 'Rack focus', detail: 'focus moves from back to front', draw(c, g, local, rect) {
      const f = eAmount(local);
      c.save(); c.filter = `blur(${(14 * (1 - f)).toFixed(2)}px)`;
      gridLines(c, rect.w, rect.h * .55, 40, '#3a3a44');
      for (let k = 0; k < 9; k++) disc(c, 50 + k * (rect.w - 100) / 8, rect.h * .3, 12, '#7a7a86');
      c.restore();
      c.save(); c.filter = `blur(${(14 * f).toFixed(2)}px)`;
      text(c, 'HERE', 40, rect.h - 60, 140, RED, {weight: 800}); c.restore();
    }},
  ];
  card({id: 'E', title: 'Kinds of blur', subtitle: 'Each one simulates something else. The amount rises and falls.', duration: 5,
    tiles: E_TILES.map((d, i) => {
      const rect = cells(2, 3)[i];
      if (d.lens) return {...d, rect, gain: 14, draw: (c, g) => eNight(c, g, rect), drawFg: f => eSubject(f, rect),
        post: local => {
          const a = .25 + .75 * eAmount(local), gap = a * .03 * Math.sqrt(Math.PI / 200);   // pre-blur ≈ gap between samples
          fx.pass('directionalBlur', {to: tmp2, scissor: scissorOf(rect), textures: {image: bgOnly}, uniforms: {dir: [gap * 1.6, 0], samples: {int: 12}}});
          fx.pass('directionalBlur', {to: tmp, scissor: scissorOf(rect), textures: {image: tmp2}, uniforms: {dir: [0, gap * 1.6 * W / H], samples: {int: 12}}});
          fx.pass('copy', {to: tmp2, scissor: scissorOf(rect), textures: {image: tmp}});
          fx.pass('lensBlur', {to: tmp, scissor: scissorOf(rect), textures: {image: tmp2}, uniforms: {
            radius: [a * .03, a * .03 * W / H], gain: 0, threshold: 1, blades: 0, rotation: 0, rim: 1.1, chroma: .025, catEye: .55,
            opticalCenter: centerUv(rect), samples: {int: 200}}});
          fx.pass(OVER, {to: tmp2, scissor: scissorOf(rect), textures: {image: tmp, fg: fgTex}});
          return tmp2;
        }};
      return {...d, rect, gain: 9,
        draw: d.draw ? (c, g, local) => d.draw(c, g, local, rect) : (c, g) => eContent(c, g, rect),
        post: d.post ? local => d.post(rect, eAmount(local)) : null};
    }),
  });

  /* ---- F · light ---- */
  const F_POINTS = Array.from({length: 9}, (_, k) => [M.hash(k, 21), M.hash(k, 22)]);
  function fContent(c, g, rect, local) {
    const w = rect.w, h = rect.h, cx = w / 2, cy = h * .56;
    c.fillStyle = '#0e0e10'; c.fillRect(0, 0, w, h);
    c.strokeStyle = '#7a1c12'; c.lineWidth = 12; c.beginPath(); c.arc(cx, cy, 120, 0, M.TAU); c.stroke();
    g.strokeStyle = RED; g.lineWidth = 9; g.beginPath(); g.arc(cx, cy, 120, 0, M.TAU); g.stroke();
    text(c, 'LIGHT', cx, cy + 38, 104, '#f4f4f0', {weight: 800, align: 'center'});
    const spin = local * .4;
    F_POINTS.forEach(([a, b], k) => {
      const ang = a * M.TAU + spin, r = 175 + b * 40;
      disc(g, cx + Math.cos(ang) * r, cy + Math.sin(ang) * r * .8, 3 + 3 * b, '#ffffff');
    });
  }
  /* Bloom of one tile only: copy its region into an empty buffer so light from a neighbour cannot leak in. */
  function isolated(rect) {
    clearRegion(tmp2, null, [0, 0, 0]);
    fx.pass('copy', {to: tmp2, scissor: scissorOf(rect), textures: {image: accum}});
    return tmp2;
  }
  const F_TILES = [
    {code: 'F1', name: 'No bloom', detail: 'reference', post: null},
    {code: 'F2', name: 'Threshold-free bloom', detail: 'halo around bright things, no wash', post: r => { const b = fx.bloom(isolated(r), {levels: 6, radius: .005}); fx.finish(accum, b, {scissor: scissorOf(r), bloomMode: 'halo', strength: .5}); return 'done'; }},
    {code: 'F3', name: 'Thresholded glow', detail: 'like AE Glow: only what passes 1.2', post: r => { const b = fx.bloom(isolated(r), {levels: 6, radius: .006, threshold: 1.2, knee: .5}); fx.finish(accum, b, {scissor: scissorOf(r), bloomMode: 'add', strength: 4}); return 'done'; }},
    {code: 'F4', name: 'Low threshold (common mistake)', detail: 'everything glows: washed out', post: r => { const b = fx.bloom(isolated(r), {levels: 6, radius: .006, threshold: .12, knee: .1}); fx.finish(accum, b, {scissor: scissorOf(r), bloomMode: 'add', strength: 6.5}); return 'done'; }},
    {code: 'F5', name: 'Halation', detail: 'reddish film halo', post: r => { const b = fx.bloom(isolated(r), {levels: 6, radius: .006}); fx.finish(accum, b, {scissor: scissorOf(r), bloomMode: 'halo', strength: .3, halation: 2.1}); return 'done'; }},
    {code: 'F6', name: 'Light wrap', detail: 'left without, right with', wrap: true},
  ];
  function fWrapBg(c, g, rect) {
    const grad = c.createLinearGradient(0, 0, rect.w, rect.h);
    grad.addColorStop(0, '#f2c27a'); grad.addColorStop(.55, '#ff8a4a'); grad.addColorStop(1, '#5a2a6a');
    c.fillStyle = grad; c.fillRect(0, 0, rect.w, rect.h);
    const sun = g.createRadialGradient(rect.w * .5, rect.h * .3, 0, rect.w * .5, rect.h * .3, rect.w * .55);
    sun.addColorStop(0, '#ffffff'); sun.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = sun; g.fillRect(0, 0, rect.w, rect.h);
  }
  function fWrapFg(f, rect) {
    f.fillStyle = '#16161a';
    f.beginPath(); f.arc(rect.w / 2, rect.h * .42, 70, 0, M.TAU); f.fill();
    f.beginPath(); f.roundRect(rect.w / 2 - 120, rect.h * .42 + 80, 240, 300, 60); f.fill();
  }
  card({id: 'F', title: 'Light', subtitle: 'Bloom, glow, halation and light wrap on the same HDR scene.', duration: 5,
    tiles: F_TILES.map((d, i) => {
      const rect = cells(2, 3)[i];
      return {...d, rect, gain: 6,
        draw: d.wrap ? (c, g) => fWrapBg(c, g, rect) : (c, g, local) => fContent(c, g, rect, local),
        drawFg: d.wrap ? f => fWrapFg(f, rect) : null,
        post: d.wrap ? () => {
          fx.pass(ALPHA, {to: alphaT, scissor: scissorOf(rect), textures: {fg: fgTex}});
          fx.pass('directionalBlur', {to: alphaB2, scissor: scissorOf(rect), textures: {image: alphaT}, uniforms: {dir: [.016, 0], samples: {int: 24}}});
          fx.pass('directionalBlur', {to: alphaB, scissor: scissorOf(rect), textures: {image: alphaB2}, uniforms: {dir: [0, .016 * W / H], samples: {int: 24}}});
          fx.pass('directionalBlur', {to: tmp2, scissor: scissorOf(rect), textures: {image: bgOnly}, uniforms: {dir: [.04, 0], samples: {int: 32}}});
          fx.pass('directionalBlur', {to: tmp, scissor: scissorOf(rect), textures: {image: tmp2}, uniforms: {dir: [0, .04 * W / H], samples: {int: 32}}});
          const right = {x: rect.x + rect.w / 2, y: rect.y, w: rect.w / 2, h: rect.h};
          fx.pass('lightWrap', {to: tmp2, scissor: scissorOf(right), textures: {comp: accum, bgBlur: tmp, fgAlpha: alphaT, fgAlphaBlur: alphaB}, uniforms: {amount: .5}});
          fx.finish(tmp2, null, {scissor: scissorOf(right)});
          return 'done';
        } : d.post ? () => d.post(rect) : null};
    }),
  });

  /* ---- G · tone mapping ---- */
  const G_MAPS = [['G1', 'Clip', 'clip'], ['G2', 'Soft shoulder', 'shoulder'], ['G3', 'Reinhard', 'reinhard'], ['G4', 'Fitted ACES', 'aces']];
  card({id: 'G', title: 'Tone mapping', subtitle: 'The same HDR light through four curves. On the right, the brand red unprocessed.', duration: 4,
    tiles: cells(1, 4, {gap: 24}).map((rect, i) => ({rect, code: G_MAPS[i][0], name: G_MAPS[i][1], gain: 8, toneMap: G_MAPS[i][2],
      draw(c, g) {
        const w = rect.w - 200, h = rect.h;
        const ramp = g.createLinearGradient(40, 0, w, 0);
        ramp.addColorStop(0, '#000000'); ramp.addColorStop(1, '#ffffff');
        g.fillStyle = ramp; g.fillRect(40, 90, w - 40, 70);
        const red = g.createRadialGradient(170, h * .72, 0, 170, h * .72, 110);
        red.addColorStop(0, '#ff6a50'); red.addColorStop(.6, '#8a1e10'); red.addColorStop(1, 'rgba(0,0,0,0)');
        g.fillStyle = red; g.fillRect(40, h * .72 - 120, 260, 240);
        disc(c, 170, h * .72, 60, RED);
        text(c, 'FOCUS', 470, h * .72 + 40, 110, '#f6f6f2', {weight: 800, align: 'center'});
      },
      post: () => { fx.finish(accum, null, {scissor: scissorOf(rect), toneMap: G_MAPS[i][2]}); return 'done'; }})),
  });

  /* ---- H · camera ---- */
  function world(c, rect, cam, local, {scenes = false} = {}) {
    const w = rect.w, h = rect.h;
    c.save(); c.translate(w / 2 + cam.x * .0 , h / 2); c.scale(cam.s, cam.s); c.translate(-w / 2, -h / 2);
    const layer = (factor, fn) => { c.save(); c.translate(-cam.x * factor + cam.sx, -cam.y * factor + cam.sy); fn(); c.restore(); };
    layer(.3, () => { gridLines(c, w * 3, h, 48, '#222228', 0, 0); for (let k = -6; k < 18; k++) disc(c, k * 70 + 20, h * .22, 6, '#4a4a54'); });
    layer(.65, () => { for (let k = -4; k < 12; k++) rrect(c, k * 150 + 40, h * .42, 70, 70, 10, '#5d5d68'); });
    if (scenes) {
      layer(1, () => { text(c, 'A', w * .5, h * .78, 230, PAPER, {weight: 800, align: 'center'}); text(c, 'B', w * 1.5, h * .78, 230, RED, {weight: 800, align: 'center'}); });
    } else layer(1.2, () => { for (let k = -3; k < 8; k++) rrect(c, k * 220 + 60, h * .64, 26, 220, 8, RED); });
    c.restore();
  }
  const H_HITS = [[.5, 1.2], [2.1, 1.2], [3.7, 1.2]];
  card({id: 'H', title: 'Camera', subtitle: 'Push-in, whip, parallax and shakes.', duration: 5,
    shutter: 180, samples: 8,
    tiles: [
      {code: 'H1', name: 'Push-in', detail: '×1.6 with ease-in-out'},
      {code: 'H2', name: 'Whip with blur', detail: 'scene change hidden in the trail', shutter: 360, samples: 32},
      {code: 'H3', name: 'Parallax', detail: 'back ×0.3 · middle ×0.65 · front ×1.2'},
      {code: 'H4', name: 'Handheld + impact', detail: 'continuous drift and zoom hits'},
    ].map((d, i) => {
      const rect = cells(2, 2)[i];
      return {...d, rect, draw(c, g, local) {
        let cam = {x: 0, y: 0, s: 1, sx: 0, sy: 0};
        if (i === 0) { const {dir, u} = pingpong(local, 1.4, .4), e = M.easing('power2.inOut')(u); cam.s = 1 + .6 * (dir > 0 ? e : 1 - e); }
        if (i === 1) { const {dir, u} = pingpong(local, .3, 1.0), e = M.easing('expo.inOut')(u); cam.x = rect.w * (dir > 0 ? e : 1 - e); }
        if (i === 2) cam.x = 110 * Math.sin(M.TAU * local / 3);
        if (i === 3) {
          const [hx, hy] = M.wiggle(local, {freq: .8, amp: 5, octaves: 2, dims: 2, seed: 4}), [kx, ky] = M.shake(local, H_HITS);
          cam.sx = hx + 9 * kx; cam.sy = hy + 9 * ky; cam.s = 1 + .035 * M.impulse(local, H_HITS, 10);
        }
        world(c, rect, cam, local, {scenes: i === 1});
        if (i === 3 && M.impulse(local, H_HITS, 10) > .5) rrect(c, rect.w - 70, 30, 40, 40, 20, RED);
      }};
    }),
  });

  /* ---- I · noise and loops ---- */
  card({id: 'I', title: 'Noise and loops', subtitle: 'After Effects wiggle() and loopOut(), deterministic.', duration: 4,
    shutter: 180, samples: 8,
    tiles: [
      {code: 'I1', name: 'Wiggle · 1 octave', detail: 'freq 1.2 · amp 120 px', octaves: 1},
      {code: 'I2', name: 'Wiggle · 3 octaves', detail: 'more fine detail', octaves: 3},
      {code: 'I3', name: 'Cycle loop', detail: 'back to the start'},
      {code: 'I4', name: 'Ping-pong loop', detail: 'there and back'},
    ].map((d, i) => {
      const rect = cells(2, 2)[i];
      return {...d, rect, draw(c, g, local) {
        const cx = rect.w / 2, cy = rect.h * .56;
        if (i < 2) {
          const at = s => M.wiggle(s, {freq: 1.2, amp: 120, octaves: d.octaves, dims: 2, seed: 9});
          c.strokeStyle = 'rgba(239,238,232,.35)'; c.lineWidth = 3; c.beginPath();
          for (let k = 0; k <= 50; k++) { const [x, y] = at(local - k * .03); k ? c.lineTo(cx + x, cy + y) : c.moveTo(cx + x, cy + y); }
          c.stroke();
          const [x, y] = at(local); disc(c, cx + x, cy + y, 22, RED);
        } else {
          const span = rect.w - 160, u = M.loop(local, 1.5, i === 2 ? 'cycle' : 'pingpong') / 1.5;
          c.strokeStyle = '#2a2a30'; c.lineWidth = 2; c.beginPath(); c.moveTo(80, cy); c.lineTo(80 + span, cy); c.stroke();
          disc(c, 80 + span * u, cy, 26, i === 2 ? PAPER : RED);
        }
      }};
    }),
  });
  /* ---- J · screen print ---- */
  function jContent(c, rect, local) {
    const w = rect.w, h = rect.h;
    const bg = c.createLinearGradient(0, 0, 0, h); bg.addColorStop(0, '#f4f3ee'); bg.addColorStop(1, '#c9c7bf');
    c.fillStyle = bg; c.fillRect(0, 0, w, h);
    const sphere = c.createRadialGradient(w * .38, h * .4, 10, w * .5, h * .52, w * .42);
    sphere.addColorStop(0, '#f6f6f2'); sphere.addColorStop(.6, '#77767a'); sphere.addColorStop(1, '#1c1c1f');
    c.fillStyle = sphere; c.beginPath(); c.arc(w * .5, h * .52, w * .36, 0, M.TAU); c.fill();
    text(c, 'FOCUS', w / 2, h * .9, 120, INK, {weight: 800, align: 'center'});
    const [x, y] = M.arcPoint(M.clamp(bAlive(local), -.1, 1.1), [w * .18, h * .72], [w * .82, h * .3], -.15);
    disc(c, x, y, 54, RED); disc(c, x, y, 26, '#f4f3ee');
  }
  const PRINT = {res: [W, H], paper: [.95, .94, .91], inkA: [1, .27, .18], inkB: [.08, .08, .09], angleA: .26, angleB: .785, offA: [0, 0], offB: [0, 0]};
  const J_TILES = [
    {code: 'J1', name: 'Halftone', detail: 'one ink, dots at 45°', u: () => ({inks: 1, cell: 9, texture: 0, strength: 1, seed: 0})},
    {code: 'J2', name: 'Two inks · misregistration', detail: 'red and black off-register, overprint', u: () => ({inks: 2, cell: 10, texture: .3, strength: 1, seed: 0, offA: [4, -3], offB: [-1, 1]})},
    {code: 'J3', name: 'Boiling texture', detail: 'uneven ink and register trembling at 12 fps', u: local => {
      const k = Math.floor(local * 12 + 1e-6);
      return {inks: 2, cell: 10, texture: 1, strength: 1, seed: k % 97, offA: [4 + 3 * (M.hash(k, 41) - .5), -3 + 3 * (M.hash(k, 42) - .5)], offB: [-1, 1]};
    }},
    {code: 'J4', name: 'Subtle layer over the piece', detail: 'the same print mixed at 35 %', u: local => ({inks: 2, cell: 7, texture: .6, strength: .35, seed: Math.floor(local * 12 + 1e-6) % 97, offA: [3, -2], offB: [-1, 1]})},
  ];
  card({id: 'J', title: 'Screen print', subtitle: 'Halftone, two inks off-register, boiling texture and a subtle layer.', duration: 5,
    shutter: 180, samples: 8,
    tiles: J_TILES.map((d, i) => {
      const rect = cells(2, 2)[i];
      return {...d, rect, draw: (c, g, local) => jContent(c, rect, local),
        post: local => {
          fx.finish(accum, null, {to: tmp, scissor: scissorOf(rect)});
          fx.pass('screenPrint', {scissor: scissorOf(rect), textures: {image: tmp}, uniforms: {...PRINT, ...d.u(local)}});
          return 'done';
        }};
    }),
  });

  /* ---- K · stepped time ---- */
  const K_RAMP = M.speedRamp(tau => { const m = M.loop(tau, 2.4); return m > .15 && m < .95 ? .22 : 1.7; }, {to: 8});
  function kObject(c, rect, T, alpha = 1) {
    const [x, y] = M.arcPoint(M.clamp(bAlive(T), -.1, 1.1), [rect.w * .2, rect.h * .74], [rect.w * .8, rect.h * .36], -.15);
    c.save(); c.globalAlpha = alpha; c.translate(x, y); c.rotate(.25 * Math.sin(T * 2));
    rrect(c, -62, -40, 124, 80, 12, PAPER); c.fillStyle = RED; c.fillRect(-62, -40, 12, 80);
    c.restore();
  }
  const K_TILES = [
    {code: 'K1', name: 'Fluid 60 fps', detail: 'reference, with motion blur', shutter: 180, samples: 12, time: l => l},
    {code: 'K2', name: 'On twos · 30 fps', detail: 'each pose lasts 2 frames', time: l => M.posterize(l, 30)},
    {code: 'K3', name: '12 fps · Posterize Time', detail: 'each pose lasts 5 frames: hand-made', time: l => M.posterize(l, 12)},
    {code: 'K4', name: 'Hybrid', detail: 'object at 12 fps, background and camera fluid', time: l => M.posterize(l, 12), smoothBg: true},
    {code: 'K5', name: 'Speed ramp', detail: 'fast → slow → fast', shutter: 180, samples: 12, time: l => K_RAMP(l)},
    {code: 'K6', name: 'Echo', detail: 'earlier copies fading out', echo: true, time: l => l},
  ];
  card({id: 'K', title: 'Stepped time', subtitle: 'The same gesture at 60 fps, on twos, at 12 fps, hybrid, ramped and echoed.', duration: 5,
    tiles: K_TILES.map((d, i) => {
      const rect = cells(2, 3)[i];
      return {...d, rect, draw(c, g, local) {
        gridLines(c, rect.w, rect.h, 44, '#222228', d.smoothBg ? -local * 70 : 0, 0);
        if (d.echo) for (const e of M.echo(local, {count: 5, lag: .06, decay: .55}).reverse()) kObject(c, rect, e.t, e.weight);
        else kObject(c, rect, d.time(local));
      }};
    }),
  });
  const TOTAL = cursor + 2.5;

  /* ================= frame ================= */
  const BG_LIN = [0x12, 0x12, 0x14].map(v => Math.pow(v / 255, 2.2));
  function drawTile(tile, card, t, local, blur) {
    const rect = tile.rect, shutter = blur ? (tile.shutter ?? card.shutter ?? 0) : 0;
    const samples = blur && shutter > 0 ? (tile.samples ?? card.samples ?? 1) : 1;
    const times = M.exposureTimes(t, {fps: FPS, shutter, samples});
    const cv = canvases(rect.w, rect.h);
    clearRegion(accum, rect, [0, 0, 0]);
    if (tile.drawFg) clearRegion(bgOnly, rect, [0, 0, 0]);
    for (const s of times) {
      const ls = Math.max(0, s.t - card.start);
      for (const c of [cv.bc, cv.gc, cv.fc]) reset(c);
      cv.bc.fillStyle = BG; cv.bc.fillRect(0, 0, rect.w, rect.h);
      cv.gc.fillStyle = '#000'; cv.gc.fillRect(0, 0, rect.w, rect.h);
      tile.draw(cv.bc, cv.gc, ls);
      upload(baseTex, cv.base, rect); upload(glowTex, cv.glow, rect);
      if (tile.drawFg) {
        cv.fc.clearRect(0, 0, rect.w, rect.h); tile.drawFg(cv.fc, ls); upload(fgTex, cv.fg, rect);
        fx.pass(COMPOSE, {to: bgOnly, scissor: scissorOf(rect), blend: 'add', clear: false, textures: {base: baseTex, glow: glowTex, fg: fgTex}, uniforms: {gain: tile.gain ?? 6, weight: s.weight, useFg: 0}});
      }
      fx.pass(COMPOSE, {to: accum, scissor: scissorOf(rect), blend: 'add', clear: false,
        textures: {base: baseTex, glow: glowTex, fg: fgTex}, uniforms: {gain: tile.gain ?? 6, weight: s.weight, useFg: tile.drawFg ? 1 : 0}});
    }
  }
  function label(x, y, code, name, detail) {
    oc.save();
    oc.font = `700 30px ${FONT}`; const wCode = oc.measureText(code).width;
    oc.font = `600 30px ${FONT}`; const wName = oc.measureText(name).width;
    oc.fillStyle = 'rgba(10,10,12,.72)'; oc.beginPath(); oc.roundRect(x, y, wCode + wName + 52, 48, 10); oc.fill();
    text(oc, code, x + 14, y + 35, 30, RED, {weight: 700});
    text(oc, name, x + 28 + wCode, y + 35, 30, PAPER, {weight: 600});
    if (detail) {
      oc.font = `500 22px ${FONT}`; const wd = oc.measureText(detail).width;
      oc.fillStyle = 'rgba(10,10,12,.6)'; oc.beginPath(); oc.roundRect(x, y + 54, wd + 28, 34, 8); oc.fill();
      text(oc, detail, x + 14, y + 78, 22, MUTED, {weight: 500});
    }
    oc.restore();
  }
  function drawOverlay(t, card) {
    reset(oc); oc.clearRect(0, 0, W, H);
    if (!card) {
      const intro = t < 2.5, a = M.clamp(intro ? t / .4 : (t - (TOTAL - 2.5)) / .4);
      oc.globalAlpha = a;
      if (intro) {
        text(oc, 'Technique', 70, 760, 128, PAPER, {weight: 800});
        text(oc, 'lab', 70, 890, 128, RED, {weight: 800});
        text(oc, 'Motionsmith', 74, 980, 36, MUTED, {weight: 600});
        text(oc, 'Every demo has a code: A1, D3, F2…', 74, 1120, 38, PAPER, {weight: 500});
        text(oc, 'Answer with the ones you like.', 74, 1172, 38, PAPER, {weight: 500});
      } else {
        text(oc, 'Which ones?', 70, 820, 104, PAPER, {weight: 800});
        text(oc, 'For example: A5 · B2 · J4 · K3', 74, 930, 44, RED, {weight: 600});
        text(oc, 'They become your taste profile.', 74, 1000, 38, MUTED, {weight: 500});
      }
      oc.globalAlpha = 1;
      return;
    }
    text(oc, card.id, 60, 300, 180, RED, {weight: 800});
    text(oc, card.title, 210, 236, 72, PAPER, {weight: 700});
    oc.save(); oc.font = `500 30px ${FONT}`;
    const words = card.subtitle.split(' '); let line = '', y = 292;
    for (const word of words) { const test = line ? `${line} ${word}` : word; if (oc.measureText(test).width > 800 && line) { text(oc, line, 212, y, 30, MUTED, {weight: 500}); line = word; y += 38; } else line = test; }
    text(oc, line, 212, y, 30, MUTED, {weight: 500}); oc.restore();
    for (const tile of card.tiles) label(tile.rect.x + 14, tile.rect.y + 14, tile.code, tile.name, tile.detail);
    if (card.id === 'G') card.tiles.forEach(tile => { rrect(oc, tile.rect.x + tile.rect.w - 170, tile.rect.y + tile.rect.h / 2 - 50, 140, 100, 14, RED); text(oc, 'brand', tile.rect.x + tile.rect.w - 100, tile.rect.y + tile.rect.h / 2 + 80, 22, MUTED, {weight: 600, align: 'center'}); });
    if (card.id === 'F') { const r = card.tiles[5].rect; oc.strokeStyle = 'rgba(255,255,255,.5)'; oc.setLineDash([8, 8]); oc.beginPath(); oc.moveTo(r.x + r.w / 2, r.y + 110); oc.lineTo(r.x + r.w / 2, r.y + r.h - 20); oc.stroke(); oc.setLineDash([]); }
    const n = CARDS.indexOf(card);
    CARDS.forEach((cd, k) => disc(oc, 70 + k * 34, 1850, k === n ? 9 : 5, k === n ? RED : '#55555c'));
    text(oc, `technique lab · ${t.toFixed(2)} s`, W - 60, 1858, 22, '#6a6a72', {weight: 500, align: 'right'});
  }
  function paint(t, blur = true) {
    t = M.clamp(t, 0, TOTAL - 1e-6);
    const card = CARDS.find(c => t >= c.start && t < c.end) || null;
    clearRegion(accum, null, BG_LIN);
    // Passes may read a few pixels outside their tile (misregistration, blur): no buffer may carry another frame's pixels.
    for (const target of [tmp, tmp2, bgOnly, alphaT, alphaB, alphaB2]) clearRegion(target, null, [0, 0, 0]);
    if (card) for (const tile of card.tiles) drawTile(tile, card, t, t - card.start, blur);
    fx.finish(accum, null, {toneMap: 'shoulder'});
    if (card) for (const tile of card.tiles) {
      if (!tile.post) continue;
      const out = tile.post(t - card.start);
      if (out && out !== 'done') fx.finish(out, null, {scissor: scissorOf(tile.rect), toneMap: tile.toneMap || 'shoulder'});
    }
    drawOverlay(t, card);
    upload(overlayTex, overlay, null);
    fx.pass('copy', {textures: {image: overlayTex}, blend: 'alpha', clear: false});
  }

  window.motionConfig = {width: W, height: H, fps: FPS, frames: Math.round(TOTAL * FPS), duration: TOTAL,
    samples: 'per tile, 1–72 (MotionMath.exposureTimes)', shutter_degrees: 'per tile, 0–720', kind: 'Technique lab: curves, principles, stagger, motion blur, blur types, light, tone mapping, camera, noise'};
  window.labCards = CARDS.map(c => ({id: c.id, title: c.title, start: c.start, end: c.end, tiles: c.tiles.map(t => ({code: t.code, name: t.name, detail: t.detail || ''}))}));
  /* Data for dump_state.mjs: positions of the card A dots (px along their track) at absolute time t. */
  window.labState = t => {
    const a = CARDS[0], local = t - a.start, span = 960 - 140;
    return {lanes: A_EASES.map(([code, , e]) => ({code, x: 70 + span * aProgress(e, local)}))};
  };
  window.__lab = {gl, fx, targets: {accum, tmp, tmp2, bgOnly, alphaT, alphaB, alphaB2}, textures: {baseTex, glowTex, fgTex}};   // inspection only
  window.motionReady = document.fonts.load(`600 30px ${FONT}`).then(() => { window.seek = (t, blur = true) => paint(t, blur); paint(0); window.motionInitialized = true; });
})();
