/* kinetic-type.js · kinetic typography as pure functions of time, for Canvas 2D or WebGL.
   Each animator returns draw commands (plain objects) and calls draw(command) for each one, so the same choreography
   can drive fillText/strokeText/clip on a 2D context or a textured quad in a WebGL scene. Letters pose, swap faces
   and boil on a 12 fps grid (hashes change once per step), so seek(t) reproduces any frame.
   Coordinates: frame pixels, origin top-left, y down. Every command's x and y are the centre of its box.
   Browser: load motion-math.js first, then this file → window.KineticType. Node: require('./kinetic-type.js').
   Commands:
     {kind: 'glyph' | 'outline', ch, i, face, x, y, z, angle, width, height, opacity, blur, color}
     {kind: 'text', text, x, y, z, width, height, color, opacity, angle, blur, [reveal, left, fullWidth]}
     {kind: 'rect', x, y, z, width, height, color, opacity}
   face is an index into the faces you asked layoutLine for; the last face (lock) is the one the word settles into.
   Use faceWidths[face] for the box of a glyph in another face. Outline commands mean: stroke the glyph's outline. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(require('./motion-math.js'));
  else root.KineticType = factory(root.MotionMath);
})(typeof globalThis !== 'undefined' ? globalThis : this, function (MM) {
  'use strict';
  const STEP_FPS = 12;   // the pace of the letters: poses, face swaps, boil and blink change on this grid

  /* Deterministic hash in [0, 1) for two integers (the boil and glitch draws). Same inputs, same output. */
  function hash2(a, b) {
    let h = Math.imul(a | 0, 374761393) + Math.imul(b | 0, 668265263);
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }
  /* Index of the step that contains t: 0 for [0, 1/fps), 1 for [1/fps, 2/fps), … */
  const stepOf = (t, fps = STEP_FPS) => Math.floor(t * fps + 1e-6);

  function emit(commands, draw) {
    if (typeof draw === 'function') for (const c of commands) draw(c);
    return commands;
  }

  /* One line of type. measure(text, face) → {width, ascent, descent} in the same units as the output (px).
     faces: how many faces the animators may cycle through (1 = no cycling); lock: the settled face (default the last).
     track: extra space after every character (px). maxWidth: scale the whole line down to fit.
     Spaces take their advance and draw nothing; characters are graphemes (an accent stays with its letter). */
  function layoutLine(text, opts = {}) {
    const {measure, faces = 1, track = 0, maxWidth = Infinity} = opts;
    if (typeof measure !== 'function') throw new TypeError('layoutLine: pass measure(text, face) → {width, ascent, descent}');
    if (!Number.isInteger(faces) || faces < 1) throw new RangeError('layoutLine: faces must be a positive integer');
    const lock = opts.lock ?? faces - 1;
    if (!Number.isInteger(lock) || lock < 0 || lock >= faces) throw new RangeError('layoutLine: lock must be the index of one face');
    if (!(maxWidth > 0)) throw new RangeError('layoutLine: maxWidth must be positive');
    const pieces = MM.layoutGlyphs(String(text), s => s ? measure(s, lock).width : 0);
    const raw = [];
    for (const p of pieces) {
      if (/^\s$/u.test(p.ch)) continue;
      const m = measure(p.ch, lock), box = m.ascent + m.descent || 1;
      // Other faces keep their own proportions but share the settled glyph's height.
      const faceWidths = Array.from({length: faces}, (_, f) => {
        const fm = f === lock ? m : measure(p.ch, f);
        return fm.width * box / ((fm.ascent + fm.descent) || 1);
      });
      raw.push({ch: p.ch, index: p.index, left: p.x + p.index * track, width: m.width, ascent: m.ascent,
        descent: m.descent, height: box, faceWidths});
    }
    if (raw.length === 0) return {text: String(text), width: 0, ascent: 0, descent: 0, height: 0, faces, lock, scale: 1, glyphs: []};
    const origin = raw[0].left;
    let right = 0, ascent = 0, descent = 0;
    for (const g of raw) {
      right = Math.max(right, g.left + g.width - origin);
      ascent = Math.max(ascent, g.ascent);
      descent = Math.max(descent, g.descent);
    }
    const factor = Math.min(1, maxWidth / right);
    const glyphs = raw.map((g, i) => ({
      ch: g.ch, index: g.index, i, lock, faces,
      x: (g.left - origin + g.width / 2) * factor,           // centre, relative to the line's left edge at the baseline
      y: (g.descent - g.ascent) / 2 * factor,                  // centre, relative to the baseline (y down)
      width: g.width * factor, height: g.height * factor,
      faceWidths: g.faceWidths.map(w => w * factor),
    }));
    return {text: String(text), width: right * factor, ascent: ascent * factor, descent: descent * factor,
      height: (ascent + descent) * factor, faces, lock, scale: factor, glyphs};
  }

  /* Words of a row laid out left to right. Returns {width, scale, words: [{text, x (left), centre, width}]}. */
  function layoutWords(words, {measure, face = 0, gap = 0, maxWidth = Infinity} = {}) {
    if (typeof measure !== 'function') throw new TypeError('layoutWords: pass measure(text, face)');
    const widths = words.map(w => measure(String(w), face).width);
    const natural = widths.reduce((s, w) => s + w, 0) + gap * Math.max(0, words.length - 1);
    const factor = Math.min(1, maxWidth / natural);
    let x = 0;
    const placed = words.map((w, i) => {
      const width = widths[i] * factor, item = {text: String(w), x, centre: x + width / 2, width};
      x += width + gap * factor;
      return item;
    });
    return {width: natural * factor, scale: factor, words: placed};
  }

  /* Per-letter entrance. Each glyph starts displaced (dx, dy, angle), eases to rest with a scale pop, and
     cycles faces for `cycle` seconds before it settles. Options (the defaults are a starting point):
       at, span: when the cascade starts and how long one letter takes (s)
       dx, dy, angle: start displacement (px, y down) and start rotation (rad, scaled by the eased progress)
       offset, exit: horizontal shift for a whole run, and a slide to the left (px)
       order: 'start' | 'end' | 'center' | 'edges' | 'random' | index; each: delay between letters (s); seed: for 'random'
       cycle, cycleFps: seconds of face cycling before a letter settles, and its pace (12 fps)
       glitch: chance per step that a settled, read letter jumps to another face for one step (0..1)
       step: pose the letters at this fps (stepped time); 0 keeps smooth time
       boil: px of stepped jitter on settled letters, changing every step; hashSeed: changes every hash
       pop: scale overshoot on landing; float, floatSpeed: slow vertical float (px, rad/s); blur: motion blur factor
       ease: the entrance curve (MotionMath name or bezier); color: fill colour */
  function run(glyphs, t, opts = {}, draw) {
    const o = {at: 0, span: .5, dx: 0, dy: 340, angle: -.14, color: '#ffffff', offset: 0, exit: 0, order: 'start',
      each: .022, seed: 7, cycle: 0, cycleFps: STEP_FPS, glitch: 0, step: 0, boil: 0, hashSeed: 0, pop: .14,
      float: 4, floatSpeed: 1.6, blur: .003, ease: 'quart.out', ...opts};
    const ease = MM.easing(o.ease), hs = o.hashSeed * 1009, k = stepOf(t), out = [];
    glyphs.forEach((g, i) => {
      const start = o.at + MM.stagger(i, glyphs.length, {each: o.each, from: o.order, seed: o.seed});
      if (t < start) return;
      const tl = o.step ? MM.posterize(t - start, o.step) : t - start;
      const u = ease(MM.clamp(tl / o.span)), v = 1 - u;
      const moving = o.boil && tl > o.span;
      const bx = moving ? o.boil * (hash2(i * 13 + 7 + hs, k) - .5) : 0;
      const by = moving ? o.boil * (hash2(i * 29 + 3 + hs, k + 7919) - .5) : 0;
      const float = o.float * Math.sin(t * o.floatSpeed + o.at * 3);
      const x = o.offset + v * o.dx - o.exit + bx, y = v * o.dy + float + by, z = 20 + v * 30;
      const opacity = MM.clamp(tl / .045), scale = 1 + o.pop * Math.sin(Math.PI * u);
      let face = g.lock;
      if (o.cycle && g.faces > 1 && tl < o.cycle) face = stepOf(tl, o.cycleFps) % g.faces;
      if (face === g.lock && o.glitch && g.faces > 1 && tl > o.span + .15 && hash2(i * 101 + 17 + hs, k) < o.glitch) {
        face = Math.floor(hash2(i * 7 + 5 + hs, k + 31) * (g.faces - 1));
      }
      out.push({kind: 'glyph', ch: g.ch, i, face, x: g.x + x, y: g.y + y, z, angle: v * o.angle,
        width: g.faceWidths[face] * scale, height: g.height * scale, opacity, blur: v * o.blur, color: o.color});
    });
    return emit(out, draw);
  }

  /* Outline echoes behind a line: copies slide out from behind the letters and wobble on the 12 fps grid.
     Options: from, until (s; the echo rises over .32 s and fades over the last .18 s), count, dx, dy (px per copy),
     grow (scale per copy), shift [x, y], z, opacity, color, wobbleFps. */
  function echo(glyphs, t, opts = {}, draw) {
    const o = {from: 0, until: Infinity, count: 3, dx: -16, dy: -16, color: '#ff0000', opacity: .5, z: 14, grow: 0,
      shift: [0, 0], wobbleFps: STEP_FPS, ...opts};
    if (t < o.from || t > o.until) return emit([], draw);
    const rise = MM.easing('quart.out')(MM.clamp((t - o.from) / .32));
    const fade = 1 - MM.clamp((t - (o.until - .18)) / .18), tt = MM.posterize(t, o.wobbleFps), out = [];
    for (let k = o.count; k >= 1; k--) {
      const wob = 2.5 * Math.sin(tt * 9 + k * 1.7), s = 1 + o.grow * k * rise;
      for (const g of glyphs) {
        out.push({kind: 'outline', ch: g.ch, i: g.i, face: g.lock,
          x: g.x + o.shift[0] + o.dx * k * rise + wob, y: g.y + o.shift[1] + o.dy * k * rise, z: o.z - k,
          width: g.width * s, height: g.height * s,
          opacity: o.opacity * (1 - (k - 1) / (o.count + 1)) * fade * rise, color: o.color});
      }
    }
    return emit(out, draw);
  }

  /* A line that never stops: copies tile the frame and slide left at `speed` px/s (y in px).
     Options: text, lineWidth (measured width of one copy, required), y, height, speed, frameWidth, color, opacity, z. */
  function marquee(t, opts = {}, draw) {
    const o = {text: '', lineWidth: 0, y: 0, height: 0, speed: 100, frameWidth: 1080, color: '#000000', opacity: .1, z: -100, ...opts};
    if (!(o.lineWidth > 0)) throw new RangeError('marquee: lineWidth must be the measured width of one copy of the text');
    const off = ((o.speed * t) % o.lineWidth + o.lineWidth) % o.lineWidth, last = Math.ceil(o.frameWidth / o.lineWidth) + 1;
    const out = [];
    for (let k = -1; k <= last; k++) {
      out.push({kind: 'text', text: o.text, x: k * o.lineWidth - off + o.lineWidth / 2, y: o.y, z: o.z,
        width: o.lineWidth, height: o.height, color: o.color, opacity: o.opacity});
    }
    return emit(out, draw);
  }

  /* A coloured band that slides in from the left (inDuration s), with a running text inside it.
     Options: at, speed, y, frameWidth, bandHeight, bandWidth (default 1.3 × frameWidth), bandColor, text, lineWidth
     (required), height, color, z, inDuration. */
  function ticker(t, opts = {}, draw) {
    const o = {at: 0, speed: 380, y: 0, frameWidth: 1080, bandHeight: 96, bandWidth: 0, bandColor: '#ff0000', text: '',
      lineWidth: 0, height: 0, color: '#ffffff', z: 60, inDuration: .3, ...opts};
    if (t < o.at) return emit([], draw);
    if (!(o.lineWidth > 0)) throw new RangeError('ticker: lineWidth must be the measured width of one copy of the text');
    const inn = MM.easing('quart.out')(MM.smoothstep(MM.clamp((t - o.at) / o.inDuration)));
    const slide = -o.frameWidth * (1 - inn), off = ((o.speed * t) % o.lineWidth + o.lineWidth) % o.lineWidth;
    const out = [{kind: 'rect', x: o.frameWidth / 2 + slide, y: o.y, z: o.z, width: o.bandWidth || o.frameWidth * 1.3,
      height: o.bandHeight, color: o.bandColor, opacity: 1}];
    const last = Math.ceil(o.frameWidth / o.lineWidth) + 1;
    for (let k = -1; k <= last; k++) {
      out.push({kind: 'text', text: o.text, x: k * o.lineWidth - off + slide + o.lineWidth / 2, y: o.y + 2, z: o.z + 1,
        width: o.lineWidth, height: o.height, color: o.color, opacity: 1});
    }
    return emit(out, draw);
  }

  /* Typewriter reveal on the 12 fps grid, with a blinking cursor while it types. x, y, width, height: the full line
     (x is its centre). The text command has reveal (0..1) and left: clip the full text to width × reveal from left. */
  function typewriter(t, opts = {}, draw) {
    const o = {at: 0, dur: 1, text: '', x: 0, y: 0, width: 0, height: 0, z: 20, color: '#000000', angle: 0, blur: 0,
      opacity: 1, fps: STEP_FPS, cursorColor: '#ff0000', cursorWidth: 8, cursorHeight: .8, cursorGap: 10, ...opts};
    if (t < o.at) return emit([], draw);
    const f = MM.clamp(MM.posterize(t - o.at, o.fps) / o.dur);
    if (f <= 0) return emit([], draw);
    const left = o.x - o.width / 2, visible = o.width * f, out = [];
    out.push({kind: 'text', text: o.text, x: left + visible / 2, y: o.y, z: o.z, width: visible, height: o.height,
      fullWidth: o.width, left, reveal: f, color: o.color, angle: o.angle, blur: o.blur, opacity: o.opacity});
    if (f < 1 && stepOf(t, o.fps) % 2 === 0) {
      out.push({kind: 'rect', x: left + visible + o.cursorGap, y: o.y, z: o.z, width: o.cursorWidth,
        height: o.height * o.cursorHeight, color: o.cursorColor, opacity: 1});
    }
    return emit(out, draw);
  }

  /* Karaoke state at t for the words of one caption line: [{text, start, end}] in seconds (captions.py output).
     Returns [{index, text, start, end, state: 'pending' | 'active' | 'done', fill}] where fill is 0..1 progress
     through the word (eased by opts.ease, stepped by opts.fps when given). Draw a highlight over the first `fill`. */
  function karaoke(words, t, opts = {}) {
    const ease = MM.easing(opts.ease ?? 'linear');
    return words.map((w, index) => {
      if (!Number.isFinite(w.start) || !Number.isFinite(w.end)) throw new RangeError(`karaoke: word ${index} needs start and end`);
      const span = Math.max(w.end - w.start, 1e-9);
      let local = t - w.start;
      if (opts.fps && local > 0) local = MM.posterize(local, opts.fps);
      const state = t < w.start ? 'pending' : t >= w.end ? 'done' : 'active';
      return {index, text: w.text, start: w.start, end: w.end, state, fill: ease(MM.clamp(local / span))};
    });
  }

  return {STEP_FPS, hash2, stepOf, layoutLine, layoutWords, run, echo, marquee, ticker, typewriter,
    reveal: typewriter,   // alias of typewriter
    karaoke};
});
