/* stage.js · the render plumbing every piece shares, so a piece only writes setup(), state(t) and draw().
   What it does for you (SKILL.md → Essential craft):
   - the capture contract of scripts/kit/runtime.mjs: window.motionConfig, window.motionReady, window.seek(t, blur);
     plus window.motionState(t) for dump_state.mjs;
   - plan.json gives width, height, fps, duration, hits and safe area, so the same piece renders in any format;
   - three Canvas 2D layers per sample: base (the picture, sRGB), light (emissive: × lightGain, the only bloom source,
     so text on base stays crisp) and top (exact colours composited after the tone map, with alpha);
   - real motion blur: sub-samples across the shutter, samples ≥ px/3 of the fastest edge (references/craft/blur.md §2);
   - linear HDR accumulation, bloom pyramid in 'halo' mode, tone map and grain (PostFX.finish).
   Load motion-math.js and postfx-glsl.js first → window.Stage.

     Stage.run({
       fonts: ['800 200px "Segoe UI"'],              // loaded before setup (declare real fonts with @font-face)
       background: '#121214',                        // base is filled with it before every draw
       setup(env) { ... },                           // once, after plan.json and fonts; may be async; lay text out here
       state(t, env) { return {..., track: [[x, y], ...]}; },   // pure function of t; track = the points that move
       draw(s, layers, env) { layers.base.fillText(...); },     // layers: base, light, top (Canvas 2D contexts)
     });

   track drives the motion blur: list the points whose motion you want smeared (corners of a moving box, a letter's
   centre, a point on the rim of something that scales). The stage measures how far the fastest one travels in one
   frame and picks the number of samples. Give speed(a, b, env) → px per frame instead for anything track misses.
   env: {W, H, U (short side), FPS, DURATION, HITS, safe, plan, M (MotionMath), hit(role, fallback), fit(...),
   fitLines(...), base, light, top}. hit('keyword lands', 2.6) reads a time from the plan's hits, so the image and the
   soundtrack move together when someone retimes plan.json. Options: shutter (270), lightGain (3), layers (['light', 'top']), bloom ({levels, radius}), finish
   (PostFX.finish options), maxSamples (64), post (a last pass on the tone-mapped frame, before the top layer):
     post: Stage.looks.print({inks: 1, strength: .3})   // screen print / riso, misregistration kicks on the hits
     post: Stage.looks.crt()                             // CRT tube
     post: (fx, image, {t, frame, env}) => fx.pass(…)    // your own: read `image`, draw to the screen */
(function (root) {
  'use strict';
  const M = root.MotionMath, P = root.PostFX;
  if (!M || !P) throw new Error('stage.js: load kit/motion-math.js and kit/postfx-glsl.js first');

  /* base (sRGB → linear) + light × gain, times the sample weight: samples add up in float. */
  const COMPOSE = `precision highp float;varying vec2 uv;uniform sampler2D base,light;uniform float gain,weight;
    void main(){vec3 c=pow(texture2D(base,uv).rgb,vec3(2.2))+pow(texture2D(light,uv).rgb,vec3(2.2))*gain;gl_FragColor=vec4(c*weight,1.);}`;
  const BASE_ONLY = `precision highp float;varying vec2 uv;uniform sampler2D base;uniform float weight;
    void main(){gl_FragColor=vec4(pow(texture2D(base,uv).rgb,vec3(2.2))*weight,1.);}`;
  const LIGHT_ONLY = `precision highp float;varying vec2 uv;uniform sampler2D light;uniform float gain,weight;
    void main(){gl_FragColor=vec4(pow(texture2D(light,uv).rgb,vec3(2.2))*gain*weight,1.);}`;
  /* The top layer accumulates premultiplied and is composited in sRGB after the tone map: where it fully covers, the
     colour comes back exact; its moving edges keep their trail. */
  const TOP_SAMPLE = `precision highp float;varying vec2 uv;uniform sampler2D image;uniform float weight;
    void main(){vec4 c=texture2D(image,uv);gl_FragColor=vec4(c.rgb*c.a,c.a)*weight;}`;
  const TOP_OVER = `precision highp float;varying vec2 uv;uniform sampler2D image;
    void main(){vec4 c=texture2D(image,uv);gl_FragColor=vec4(c.rgb/max(c.a,1e-5),min(c.a,1.));}`;

  const FINISH = {bloomMode: 'halo', strength: .45, halation: 1.2, toneMap: 'shoulder', vignette: .2, grain: .02};
  /* The font kit first (templates/fonts, copied by new_piece.py into assets/fonts and linked by index.html: the same
     letters on every machine), then system stacks that exist on Windows, macOS and Linux as a fallback.
     SANS = Archivo (weights 100–900, widths 62–125 %: animate weight in the font string and width with
     ctx.fontStretch or a stretch keyword, "condensed 900 120px Archivo"), SERIF = Fraunces, MONO = JetBrains Mono.
     For another face, add its @font-face to index.html and list it in fonts: [...]. */
  const SYSTEM = {
    SANS: '"Segoe UI", "Helvetica Neue", Helvetica, Roboto, "Noto Sans", "Liberation Sans", Arial, sans-serif',
    SERIF: 'Georgia, "Times New Roman", "Noto Serif", "Liberation Serif", serif',
    MONO: 'Consolas, Menlo, "DejaVu Sans Mono", "Liberation Mono", "Courier New", monospace',
  };
  const FONTS = Object.freeze({
    SANS: `"Archivo", ${SYSTEM.SANS}`, SERIF: `"Fraunces", ${SYSTEM.SERIF}`, MONO: `"JetBrains Mono", ${SYSTEM.MONO}`,
    SYSTEM: Object.freeze(SYSTEM),
  });
  /* Font string with an optional width: font({weight: 640, size: 120, stretch: 'condensed'}). */
  const font = ({style = '', weight = 400, stretch = '', size = 100, family = FONTS.SANS} = {}) =>
    [style, String(Math.round(weight)), stretch, `${size}px`, family].filter(Boolean).join(' ');
  const STRETCHES = ['ultra-condensed', 'extra-condensed', 'condensed', 'semi-condensed', 'normal', 'semi-expanded',
    'expanded', 'extra-expanded', 'ultra-expanded'];   // what Canvas 2D accepts: 50 % … 200 % in 9 steps

  /* Largest distance any tracked point travels between two states (px). */
  function trackSpeed(a, b) {
    const pa = (a && a.track) || [], pb = (b && b.track) || [];
    let most = 0;
    for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
      if (!pa[i] || !pb[i]) continue;
      const d = Math.hypot(pb[i][0] - pa[i][0], pb[i][1] - pa[i][1]);
      if (Number.isFinite(d)) most = Math.max(most, d);
    }
    return most;
  }

  /* A word that should not end a line: up to three letters and no punctuation after it ("the", "of", "a", "de", "la",
     "y", "to"). Phrases break after punctuation and before these words, not after them. */
  const SHORT = /^[\p{L}\p{M}'’]{1,3}$/u;
  const PHRASE_PENALTY = .35, ORPHAN_PENALTY = .35, SHORT_LINE = .35;   // a line under 35 % of the width is a stub

  function words(text) {
    const list = [], forced = new Set();
    String(text).split('|').forEach((part, k) => {
      if (k > 0 && list.length) forced.add(list.length);
      list.push(...part.trim().split(/\s+/).filter(Boolean));
    });
    return {list, forced};
  }

  /* Greedy word wrap; '|' forces a break. measure(text) → width in px. It gives the fewest lines, not the best ones:
     fitLines() chooses the breaks. */
  function wrap(text, measure, width) {
    const {list, forced} = words(text), lines = [];
    let line = [];
    list.forEach((word, i) => {
      if (line.length && (forced.has(i) || measure([...line, word].join(' ')) > width)) { lines.push(line.join(' ')); line = []; }
      line.push(word);
    });
    if (line.length) lines.push(line.join(' '));
    return lines;
  }

  /* The best breaks at one size, by dynamic programming over the words: every line inside width, at most maxLines,
     '|' always breaks. Cost = Σ (slack / width)² over the lines, which balances them, plus a penalty when a line ends
     on a short word, when the last line is a lone word, and for a stub line under 35 % of the width. Returns {lines, widths, bad (number of penalties)} or null
     when no layout fits. */
  function breakLines(text, measure, width, maxLines = Infinity) {
    const {list, forced} = words(text), n = list.length;
    if (!n) return {lines: [], widths: [], bad: 0};
    const limit = Math.min(maxLines, n), cache = new Map();
    const lineWidth = (i, j) => {
      const key = i * 4096 + j;
      if (!cache.has(key)) cache.set(key, measure(list.slice(i, j).join(' ')));
      return cache.get(key);
    };
    const cost = Array.from({length: limit + 1}, () => new Array(n + 1).fill(Infinity));
    const from = Array.from({length: limit + 1}, () => new Array(n + 1).fill(-1));
    cost[0][0] = 0;
    for (let L = 1; L <= limit; L++) {
      for (let j = 1; j <= n; j++) {
        for (let i = j - 1; i >= 0; i--) {
          if (i < j - 1 && forced.has(i + 1)) break;                 // a line never crosses a forced break
          const w = lineWidth(i, j);
          if (w > width) break;                                       // starting earlier only makes it wider
          if (cost[L - 1][i] === Infinity) continue;
          const slack = (width - w) / width;
          const penalty = (j < n && j - i > 1 && SHORT.test(list[j - 1]) ? PHRASE_PENALTY : 0)
            + (j === n && n > 1 && j - i === 1 ? ORPHAN_PENALTY : 0)
            + (n > 1 && w < SHORT_LINE * width && !forced.has(j) && !forced.has(i) ? ORPHAN_PENALTY : 0);
          const c = cost[L - 1][i] + slack * slack + penalty;
          if (c < cost[L][j]) { cost[L][j] = c; from[L][j] = i; }
        }
      }
    }
    let lines = 0;
    for (let L = 1; L <= limit; L++) if (cost[L][n] < (lines ? cost[lines][n] : Infinity) - 1e-12) lines = L;
    if (!lines) return null;
    const cuts = [];
    for (let L = lines, j = n; L > 0; j = from[L][j], L--) cuts.unshift([from[L][j], j]);
    let bad = 0;
    const out = cuts.map(([i, j]) => {
      if (j < n && j - i > 1 && SHORT.test(list[j - 1])) bad++;
      if (j === n && n > 1 && j - i === 1) bad++;
      if (n > 1 && lineWidth(i, j) < SHORT_LINE * width && !forced.has(j) && !forced.has(i)) bad++;
      return list.slice(i, j).join(' ');
    });
    return {lines: out, widths: cuts.map(([i, j]) => lineWidth(i, j)), bad};
  }

  /* Largest size at which the text sets into ≤ maxLines lines inside width × height, with the best breaks at that
     size. If those breaks still end a line on a short word, leave a lone last word or a stub line, it looks up to
     20 % smaller for a clean layout and takes the first it finds. measureAt(text, size) → width. Returns {size, lines, widths, bad}. */
  function fitLines(text, measureAt, {max = 200, min = 12, width = 1000, height = Infinity, lineHeight = 1.05, maxLines = 4} = {}) {
    let first = null;
    for (let size = Math.floor(max); size >= min; size--) {          // 1 px steps
      const room = Math.min(maxLines, Math.floor(height / (size * lineHeight)));
      if (!(room >= 1)) continue;
      const r = breakLines(text, s => measureAt(s, size), width, room);
      if (!r) continue;
      if (r.bad === 0) return {size, ...r};
      if (!first) first = {size, ...r};
      if (size <= first.size * .8) break;
    }
    if (first) return first;
    const lines = wrap(text, s => measureAt(s, min), width);       // a word wider than the box: the minimum, greedy
    return {size: min, lines, widths: lines.map(l => measureAt(l, min)), bad: 0};
  }

  /* Everything a piece's setup() and state() read, from plan.json and a Canvas 2D context used only to measure text
     (measure() returns it). No GPU: tests/recipes_check.js builds it in Node with a fake context. */
  function createEnv(plan, measure) {
    const env = {M, plan};
    env.W = plan.width || 1080; env.H = plan.height || 1920; env.U = Math.min(env.W, env.H);
    env.FPS = typeof plan.fps === 'string' ? plan.fps.split('/').map(Number).reduce((a, b) => a / b) : plan.fps;
    env.DURATION = plan.duration_frames / env.FPS;
    env.HITS = (plan.hits || []).slice().sort((a, b) => a.time - b.time);
    env.safe = plan.safe_area || {x: Math.round(.074 * env.W), y: Math.round(.1 * env.H), width: Math.round(.852 * env.W), height: Math.round(.8 * env.H)};
    env.hit = (role, fallback) => {
      const found = env.HITS.find(h => h.role === role);
      if (found) return Number(found.time);
      if (fallback === undefined) throw new RangeError(`plan.json has no hit with role "${role}"`);
      return fallback;
    };
    /* Largest font size ≤ max at which text fits width. Returns {size, font, width}. */
    env.fit = (text, {weight = 800, family = 'sans-serif', max = 200, width = env.W, style = ''} = {}) => {
      const ctx = measure(), make = s => `${style ? style + ' ' : ''}${weight} ${s}px ${family}`;
      ctx.font = make(max);
      const natural = ctx.measureText(text).width || 1;
      const size = Math.max(1, Math.floor(Math.min(max, max * width / natural)));
      ctx.font = make(size);
      return {size, font: make(size), width: ctx.measureText(text).width};
    };
    /* Wrap and size a block of text: {size, font, lines, widths, bad}. Options as fit() plus height, lineHeight,
       maxLines, min (fitLines above). */
    env.fitLines = (text, {weight = 800, family = 'sans-serif', style = '', ...opts} = {}) => {
      const ctx = measure(), make = s => `${style ? style + ' ' : ''}${weight} ${s}px ${family}`;
      const result = fitLines(text, (s, size) => { ctx.font = make(size); return ctx.measureText(s).width; }, {width: env.W, ...opts});
      return {...result, font: make(result.size)};
    };
    Object.defineProperty(env, 'base', {get: measure, enumerable: true});
    return env;
  }

  function run(cfg) {
    if (!cfg || typeof cfg.state !== 'function' || typeof cfg.draw !== 'function') {
      throw new TypeError('Stage.run: pass {state(t, env), draw(state, layers, env)}');
    }
    const overrides = root.motionOverrides || {};   // MOTION_MAX_SAMPLES=N on the capture scripts: fast drafts
    const shutter = cfg.shutter ?? 270, lightGain = cfg.lightGain ?? 3;
    const maxSamples = Math.max(1, Math.min(cfg.maxSamples ?? 64, overrides.maxSamples ?? Infinity));
    let ldr = false;                                   // 8-bit fallback: one sample, no bloom (plan.render.allow_ldr)
    const useLight = (cfg.layers ?? ['light', 'top']).includes('light');
    const useTop = (cfg.layers ?? ['light', 'top']).includes('top');
    let env = null;
    let gl, fx, accum, glowAccum, topAccum, layers, textures, finished = null;

    function layer() {   // CPU-rastered (willReadFrequently): the same t gives the same pixels whatever was drawn before
      const c = document.createElement('canvas'); c.width = env.W; c.height = env.H;
      return {c, ctx: c.getContext('2d', {willReadFrequently: true})};
    }
    function texture() {
      const t = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, env.W, env.H, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      for (const k of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, k, gl.LINEAR);
      for (const k of [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T]) gl.texParameteri(gl.TEXTURE_2D, k, gl.CLAMP_TO_EDGE);
      return t;
    }
    function upload(tex, canvas) {
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
      gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    }

    function exposures(t, blur) {
      if (!blur || ldr) return [{t, weight: 1}];
      const a = cfg.state(t - .5 / env.FPS, env), b = cfg.state(t + .5 / env.FPS, env);
      const perFrame = cfg.speed ? cfg.speed(a, b, env) : trackSpeed(a, b);
      const wanted = Math.ceil(M.pxPerExposure(perFrame * env.FPS, shutter, env.FPS) / 3);
      const samples = Number.isFinite(wanted) ? M.clamp(wanted, 1, maxSamples) : maxSamples;   // NaN speed: blur fully, never skip the frame
      return M.exposureTimes(t, {fps: env.FPS, shutter, samples});
    }

    function paint(t, blur = true) {
      t = M.clamp(t, 0, env.DURATION - 1e-6);
      const ctxs = {base: layers.base.ctx, light: layers.light.ctx, top: layers.top.ctx};
      exposures(t, blur).forEach((e, i) => {
        const s = cfg.state(e.t, env);
        ctxs.base.setTransform(1, 0, 0, 1, 0, 0); ctxs.base.globalAlpha = 1;
        ctxs.base.fillStyle = cfg.background ?? '#000'; ctxs.base.fillRect(0, 0, env.W, env.H);
        if (useLight) { ctxs.light.setTransform(1, 0, 0, 1, 0, 0); ctxs.light.globalAlpha = 1; ctxs.light.fillStyle = '#000'; ctxs.light.fillRect(0, 0, env.W, env.H); }
        if (useTop) { ctxs.top.setTransform(1, 0, 0, 1, 0, 0); ctxs.top.clearRect(0, 0, env.W, env.H); }
        cfg.draw(s, ctxs, env);
        const sample = {uniforms: {gain: lightGain, weight: e.weight}, blend: 'add', clear: i === 0};   // the first sample clears
        upload(textures.base, layers.base.c);
        if (useLight) {
          upload(textures.light, layers.light.c);
          fx.pass(COMPOSE, {...sample, to: accum, textures: {base: textures.base, light: textures.light}});
          fx.pass(LIGHT_ONLY, {...sample, to: glowAccum, textures: {light: textures.light}});
        } else {
          fx.pass(BASE_ONLY, {...sample, to: accum, textures: {base: textures.base}});
        }
        if (useTop) {
          upload(textures.top, layers.top.c);
          fx.pass(TOP_SAMPLE, {...sample, to: topAccum, textures: {image: textures.top}, clearColor: [0, 0, 0, 0]});
        }
      });
      const frame = Math.floor(t * env.FPS + 1e-6);
      const finish = {...FINISH, ...(cfg.finish || {}), frame};
      const bloom = useLight && !ldr ? fx.bloom(glowAccum, {levels: 6, radius: .005, ...(cfg.bloom || {})}) : null;
      if (cfg.post) {   // finish into a target, then the post pass draws the frame
        finished = finished || fx.target();
        fx.finish(accum, bloom, {...(bloom ? finish : {...finish, strength: 0, halation: 0}), to: finished});
        cfg.post(fx, finished, {t, frame, env});
      } else {
        fx.finish(accum, bloom, bloom ? finish : {...finish, strength: 0, halation: 0});
      }
      if (useTop) fx.pass(TOP_OVER, {textures: {image: topAccum}, blend: 'alpha', clear: false});
    }

    root.motionInitialized = false;
    root.motionReady = (async () => {
      const plan = await (await fetch('plan.json', {cache: 'no-store'})).json();
      env = createEnv(plan, () => layers.base.ctx);
      const canvas = document.getElementById(cfg.canvas || 'art');
      canvas.width = env.W; canvas.height = env.H; canvas.style.width = `${env.W}px`; canvas.style.height = `${env.H}px`;
      gl = canvas.getContext('webgl', {alpha: false, antialias: false, preserveDrawingBuffer: true});
      if (!gl) throw new Error('WebGL required');
      try {
        fx = P.runner(gl, {width: env.W, height: env.H});   // fails with a clear message without HDR (half-float)
      } catch (error) {
        if (!(plan.render && plan.render.allow_ldr)) {
          throw new Error(`${error.message}. Motion blur and bloom need it. To render anyway in 8 bits (no motion blur, no bloom), set "render": {"allow_ldr": true} in plan.json.`);
        }
        fx = P.runner(gl, {width: env.W, height: env.H, requireHdr: false});
        ldr = true;
        console.warn('Motionsmith: 8-bit fallback (render.allow_ldr): no motion blur, no bloom');
      }
      accum = fx.target(); glowAccum = useLight ? fx.target() : null; topAccum = useTop ? fx.target() : null;
      layers = {base: layer(), light: layer(), top: layer()};
      textures = {base: texture(), light: useLight ? texture() : null, top: useTop ? texture() : null};
      env.light = layers.light.ctx; env.top = layers.top.ctx;   // env.base is the base layer's context (createEnv)
      const fontReport = [];
      for (const f of cfg.fonts || []) {
        await document.fonts.load(f);
        fontReport.push({font: f, loaded: document.fonts.check(f) && [...document.fonts].some(face => face.status === 'loaded' && f.includes(face.family.replace(/"/g, '')))});
      }
      if (cfg.setup) await cfg.setup(env);
      root.motionConfig = {width: env.W, height: env.H, fps: env.FPS, frames: plan.duration_frames, duration: env.DURATION,
        shutter_degrees: shutter, samples: ldr ? '1 (8-bit fallback)' : `≥ px/3 per frame, 1–${maxSamples}`, hdr: !ldr,
        draft: maxSamples < (cfg.maxSamples ?? 64), fonts: fontReport};
      root.motionState = t => cfg.state(t, env);
      root.seek = (t, blur = true) => paint(t, blur);
      paint(0);
      root.motionInitialized = true;
      return true;
    })();
    return root.motionReady;
  }

  /* Finishing looks for the `post` option. print = the kit's screenPrint pass (references/craft/print-textures.md):
     inkB comes from the frame's darkness, inkA from its redness; `kick` multiplies the misregistration on every hit of
     the plan, `strength` 0.25–0.4 is a layer of matter over the piece, 1 a full print. crt = the compact CRT tube. */
  const looks = {
    print: (o = {}) => (fx, image, {t, env}) => {
      const kick = 1 + (o.kick ?? 3) * M.impulse(t, env.HITS, 12);
      const offA = (o.offA || [4, -3]).map(v => v * env.U / 1080 * kick), offB = (o.offB || [-1, 1]).map(v => v * env.U / 1080 * kick);
      fx.pass('screenPrint', {textures: {image}, uniforms: {res: [env.W, env.H], paper: o.paper || [.95, .94, .91],
        inkA: o.inkA || [1, .27, .18], inkB: o.inkB || [.08, .08, .09], inks: o.inks ?? 2, cell: o.cell ?? Math.max(4, env.U / 108),
        angleA: o.angleA ?? .26, angleB: o.angleB ?? .785, offA, offB, texture: o.texture ?? .6,
        seed: Math.round(M.posterize(t, o.fps ?? 12) * (o.fps ?? 12)), strength: o.strength ?? .35}});
    },
    crt: (o = {}) => (fx, image) => fx.pass('crt', {textures: {image}, uniforms: {curvature: o.curvature ?? .08,
      scanline: o.scanline ?? .25, grille: o.grille ?? .15, vignette: o.vignette ?? .3}}),
  };

  root.Stage = {run, createEnv, trackSpeed, wrap, breakLines, fitLines, FINISH, FONTS, font, STRETCHES, looks};
})(typeof globalThis !== 'undefined' ? globalThis : this);
