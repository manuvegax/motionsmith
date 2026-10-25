/* Recipe · kinetic quote, typographic poster on paper. A sentence arrives word by word; each word's letters cascade in
   while they cycle type faces on a 12 fps grid and settle into the heavy face. The keyword is the hero: it lands last,
   on its own hit and its own line, about twice the size, in the accent, with a print kick (an ink copy jumps out of
   register for a moment) and outline echoes behind it. Behind everything a giant outline marquee of the keyword
   slides; the settled letters boil a little and the keyword glitches now and then, and the camera keeps a slow push,
   so the hold is never frozen. The block leaves line by line.
   Variable type (Archivo, from the font kit): every letter lands from a thin weight to black as it settles, and the
   keyword slams from extra-condensed to its full width on a 12 fps step while it lands.
   Mark the keyword with asterisks in TITLE ("the mind is *ready* for"); without them the last word is the keyword.
   '|' forces a line break. Times: hits 'first word' and 'keyword lands'; the words in between are spread so the
   keyword arrives on its hit after a short vacuum. Uses kit/kinetic-type.js and kit/stage.js.
   Guides: references/craft/kinetic-typography.md, references/create/scene-recipes.md, style atlas #9. */
(() => {
  'use strict';
  const M = window.MotionMath, K = window.KineticType, S = window.Stage, {SANS, SERIF, MONO} = S.FONTS;
  const PAPER = '#ebe7dd', INK = '#121212', ACCENT = '#2f3dff';
  const TITLE = 'TITLE';
  // Faces the letters cycle through; the LAST one is where every word settles.
  const FACES = [{style: '', weight: 700, family: MONO}, {style: 'italic', weight: 400, family: SERIF}, {style: '', weight: 900, family: SANS}];
  const KEY_SCALE = 1.9;                // the keyword's size against the other words (art direction: hero 1.5–3×)
  const WORD_SPAN = .42, VACUUM = .3;   // seconds one word takes to land; the pause before the keyword
  const LEAD = .12;                     // the first word is already mid-flight on frame 0
  const EACH = .024, DY = .5, ANGLE = -.12;
  const THIN = 260, BLACK = 900;        // the weight a letter enters with and the one it settles into
  const SLAM = ['extra-condensed', 'condensed', 'semi-condensed', 'normal'];   // the keyword's width steps, 12 fps
  let lines = [], words = [], keyword = '', keyChars = '', marqueeWidth = 0, marqueeFont = '';

  const fontOf = (f, px) => `${f.style ? f.style + ' ' : ''}${f.weight} ${px}px ${f.family}`;
  const graphemes = text => M.layoutGlyphs(String(text), () => 0).length;   // the same segmentation as layoutLine

  /* TITLE → the words before the keyword (with their '|' breaks), the keyword, the words after. */
  function parse(title) {
    const tokens = [];
    String(title).split('|').forEach((part, p) => part.trim().split(/\s+/).filter(Boolean).forEach((w, k) => tokens.push({w, brk: p > 0 && k === 0})));
    let key = tokens.findIndex(t => /^\*.+\*[.,;:!?…]*$/u.test(t.w));
    if (key < 0) key = tokens.length - 1;
    const clean = tokens.map(t => ({...t, w: t.w.replace(/\*/g, '')}));
    const join = list => list.map((t, i) => (i > 0 && t.brk ? '|' : '') + t.w).join(' ').replace(/ \|/g, '|');
    return {pre: join(clean.slice(0, key)), key: clean[key] ? clean[key].w : '', post: join(clean.slice(key + 1))};
  }

  window.Stage.run({
    fonts: FACES.map(f => fontOf(f, 100)),
    background: PAPER,
    layers: [],                          // paper does not glow: no light layer, a 'clip' tone map keeps ink and accent
    finish: {toneMap: 'clip', vignette: .12, grain: .02},
    post: S.looks.print({inks: 1, strength: .3, kick: 4, paper: [.922, .906, .867], inkB: [.07, .07, .07]}),   // a riso layer: halftone on the ink, a kick on every hit

    setup({W, U, DURATION, safe, base, hit}) {
      const lock = FACES[FACES.length - 1], parts = parse(TITLE), width = safe.width * .96;
      const at = size => text => { base.font = fontOf(lock, size); return base.measureText(text).width; };
      // Largest size at which the words before and after set into ≤ 3 + 2 lines and the keyword fits its own line.
      let layout = null;
      for (let size = Math.round(.15 * U); size >= Math.round(.06 * U) && !layout; size--) {
        const pre = parts.pre ? S.breakLines(parts.pre, at(size), width, 3) : {lines: []};
        const post = parts.post ? S.breakLines(parts.post, at(size), width, 2) : {lines: []};
        if (!pre || !post) continue;
        const keySize = Math.floor(Math.min(size * KEY_SCALE, size * KEY_SCALE * width / Math.max(1, at(size * KEY_SCALE)(parts.key))));
        const height = (pre.lines.length + post.lines.length) * size * 1.04 + keySize * 1.02;
        if (height <= safe.height * .78) layout = {size, keySize, pre: pre.lines, post: post.lines};
      }
      layout = layout || {size: Math.round(.06 * U), keySize: Math.round(.1 * U), pre: parts.pre ? [parts.pre.replace(/\|/g, ' ')] : [], post: parts.post ? [parts.post.replace(/\|/g, ' ')] : []};
      const rows = [...layout.pre.map(text => ({text, size: layout.size, key: false})), {text: parts.key, size: layout.keySize, key: true},
        ...layout.post.map(text => ({text, size: layout.size, key: false}))];
      const total = rows.reduce((h, r) => h + r.size * (r.key ? 1.02 : 1.04), 0);
      const first = hit('first word', .06), land = hit('keyword lands', Math.min(2.6, DURATION * .5));
      const before = layout.pre.join(' ').split(/\s+/).filter(Boolean).length;
      const step = Math.max(.1, (land - VACUUM - first) / Math.max(1, before));
      let y = safe.y + (safe.height - total) * .45, index = 0;
      lines = rows.map((row, li) => {
        const fonts = FACES.map(f => fontOf(f, row.size));
        const measure = (text, face) => { base.font = fonts[face]; return {width: base.measureText(text).width, ascent: .76 * row.size, descent: .24 * row.size}; };
        const layoutLine = K.layoutLine(row.text, {measure, faces: FACES.length});
        y += row.size * (row.key ? 1.02 : 1.04);
        const baseline = y - row.size * .24, left = W / 2 - layoutLine.width / 2;
        let g = 0;   // glyphs skip spaces, so each word owns the next graphemes(word) glyphs
        const lineWords = row.text.split(' ').filter(Boolean).map(text => {
          const own = layoutLine.glyphs.slice(g, g += graphemes(text));
          const i = index++, isKey = row.key;
          const start = isKey ? land - .06 : (i < before ? first - LEAD + i * step : land + .35 + (i - before - 1) * .2);
          return {index: i, isKey, at: start, glyphs: own, size: row.size};
        });
        words.push(...lineWords);
        return {li, left, baseline, size: row.size, fonts, words: lineWords, key: row.key};
      });
      keyword = parts.key.replace(/[.,;:!?…]+$/u, '').toUpperCase();
      keyChars = words.filter(w => w.isKey).flatMap(w => w.glyphs.map(g => g.ch)).join('');
      marqueeFont = `900 ${Math.round(.3 * U)}px ${lock.family}`;
      base.font = marqueeFont; marqueeWidth = base.measureText(`${keyword} · `).width || 1;
    },

    state(t, {W, H, U, DURATION}) {
      const exitAt = DURATION - .62, push = 1 + .03 * M.clamp(t / DURATION);
      const exits = lines.map(l => M.easing('cubic.in')(M.clamp((t - exitAt - l.li * .07) / .4)));
      const ease = M.easing('expo.out'), land = words.find(w => w.isKey), kick = land ? M.impulse(t, [{time: land.at + .06, amplitude: 1}], 11) : 0;
      // One point per letter: the newest letter of a word moves fastest, and it is the one the blur must follow.
      const letters = words.flatMap(w => w.glyphs.map((g, i) => {
        const v = 1 - ease(M.clamp((t - w.at - i * EACH) / WORD_SPAN));
        return [v * ANGLE * g.height * .5, v * DY * w.size];
      }));
      const marqueeX = -.08 * U * t;
      const track = [...letters, ...exits.map(e => [0, -e * .07 * U]), [marqueeX, 0], [kick * .014 * U, kick * .01 * U], [push * W / 2, push * H / 2]];
      return {t, push, exits, kick, track, debug: {keyword: keyChars, words: words.length, lines: lines.map(l => l.words.map(w => w.glyphs.map(g => g.ch).join('')).join(' '))}};
    },

    draw(s, {base}, {W, H, U, DURATION}) {
      const t = s.t;
      K.marquee(t, {text: `${keyword} · `, lineWidth: marqueeWidth, y: H * .5, speed: .08 * U, frameWidth: W, color: INK, opacity: .1},
        c => {   // the living layer: a giant outline of the keyword sliding behind everything
          base.save(); base.font = marqueeFont; base.textAlign = 'center'; base.textBaseline = 'middle';
          base.globalAlpha = c.opacity; base.strokeStyle = c.color; base.lineWidth = .0035 * U;
          base.strokeText(c.text, c.x, c.y); base.restore();
        });
      base.save(); base.translate(W / 2, H / 2); base.scale(s.push, s.push); base.translate(-W / 2, -H / 2);
      for (const line of lines) {
        const e = s.exits[line.li];
        if (e >= 1) continue;
        for (const w of line.words) {
          const opts = {at: w.at, span: WORD_SPAN, dx: 0, dy: DY * w.size, angle: ANGLE, each: EACH, ease: 'expo.out', pop: .1,
            float: 0, cycle: w.isKey ? .5 : .2, boil: .003 * U, hashSeed: w.index, glitch: w.isKey ? .06 : 0, blur: 0};
          const lockFace = FACES.length - 1;
          const fontFor = c => {   // the settled face is variable: weight from THIN to BLACK, the keyword's width on steps
            if (c.face !== lockFace) return line.fonts[c.face];
            const settle = M.easing('cubic.out')(M.clamp((t - w.at - c.i * EACH) / (WORD_SPAN * 1.15)));
            const step = w.isKey ? Math.min(SLAM.length - 1, Math.floor(M.posterize(Math.max(0, t - w.at), 12) / (WORD_SPAN / SLAM.length))) : SLAM.length - 1;
            return S.font({weight: M.mix(THIN, BLACK, settle), stretch: SLAM[step] === 'normal' ? '' : SLAM[step], size: w.size, family: FACES[lockFace].family});
          };
          const glyph = (c, g, color, dx = 0, dy = 0) => {
            base.save();
            base.translate(line.left + c.x + dx, line.baseline + c.y - e * .07 * U + dy);
            base.rotate(c.angle); base.scale(c.height / g.height, c.height / g.height);
            base.font = fontFor(c); base.textAlign = 'center'; base.globalAlpha = c.opacity * (1 - e);
            base.fillStyle = color; base.fillText(c.ch, 0, -g.y);
            base.restore();
          };
          if (w.isKey) {   // outline echoes behind the keyword
            K.echo(w.glyphs, t, {from: w.at + .12, until: DURATION - .5, count: 3, dx: -.012 * U, dy: -.012 * U, color: ACCENT, opacity: .55}, c => {
              const g = w.glyphs.find(x => x.i === c.i);   // echo keeps the glyph's line index (run gives the list index)
              if (!g) return;
              base.save();
              base.translate(line.left + c.x, line.baseline + c.y - e * .07 * U);
              base.font = line.fonts[c.face]; base.textAlign = 'center'; base.globalAlpha = c.opacity * (1 - e);
              base.strokeStyle = c.color; base.lineWidth = .003 * U; base.strokeText(c.ch, 0, -g.y);
              base.restore();
            });
          }
          K.run(w.glyphs, t, opts, c => {
            const g = w.glyphs[c.i];
            if (w.isKey && s.kick > .02) glyph(c, g, INK, s.kick * .014 * U, s.kick * .01 * U);   // the print kick: ink out of register
            glyph(c, g, w.isKey ? ACCENT : INK);
          });
        }
      }
      base.restore();
    },
  });
})();
