/* collage.js · the editorial-collage toolbox: the After Effects devices of documentary and editorial motion graphics,
   drawn in Canvas 2D, deterministic (seeded), cached where they are expensive. See references/create/editorial-collage.md.

     const C = Collage.create(env);                       // in setup()
     const paper = C.paper({tone: '#efeee8'});            // a sheet with matter: blotches, grain, fibres, edges
     const page = C.document({headline: '…', body: [...], highlight: '…'});   // a printed page with real text
     draw: C.drawPaper(base, paper); C.drawDocument(base, page, {cx, cy, scale, focus, highlight});
           C.numeral(base, '70', {…}); C.phrase(base, laid, t, {…}); C.ribbon(…); C.card(…); C.phone(…); C.object(…)

   Devices and the After Effects tool each one stands for:
     paper / drawPaper     a scanned paper plate (texture layer, multiply)
     document/drawDocument a macro shot of print with depth of field (camera lens blur, focus distance) and a
                           highlighter (shape layer, trim paths, multiply)
     numeral               a monumental out-of-focus figure behind the phrase (a 3D layer far from the focus plane)
     layoutPhrase/phrase   mixed weights and sizes in one phrase, the keyword in the accent (text animators per word)
     textOnPath            type on a curve (path text)
     ribbon                a thick curved stroke drawing on (shape layer stroke, trim paths, drop shadow)
     card                  a paper card with a soft shadow and a pin
     phone                 a device with stacked notifications (pre-comp with a UI)
     object                a cut-out (PNG with alpha) with a contact shadow and a soft drop shadow, in depth
     trim                  any path drawn on from `from` to `to`
   Depth: every device takes `blur` (px) so a layer far from the focus plane is soft; `depthBlur(z, focus)` gives it. */
(function (root) {
  'use strict';
  const M = root.MotionMath;

  function create(env) {
    const {W, H, U} = env;
    const canvas = (w, h) => {   // an offscreen canvas in the browser; a stand-in in the headless checks
      if (typeof root.document === 'undefined' || !root.document.createElement) return null;
      const c = root.document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h));
      return c;
    };

    /* ---------- paper ---------- */
    function paper({tone = '#efeee8', grain = .055, blotch = .05, fibres = 140, edge = .22, seed = 7, width = W, height = H} = {}) {
      const c = canvas(width, height);
      if (!c) return {stub: true, tone};
      const g = c.getContext('2d', {willReadFrequently: true}), r = M.rng(seed);
      g.fillStyle = tone; g.fillRect(0, 0, width, height);
      for (let i = 0; i < 26; i++) {   // low-frequency blotches: the sheet is never one flat colour
        const x = r() * width, y = r() * height, rad = (.15 + r() * .45) * Math.max(width, height);
        const grad = g.createRadialGradient(x, y, 0, x, y, rad), dark = r() < .55;
        grad.addColorStop(0, dark ? `rgba(80,70,55,${blotch * r()})` : `rgba(255,255,250,${blotch * r() * 1.4})`);
        grad.addColorStop(1, 'rgba(0,0,0,0)');
        g.fillStyle = grad; g.fillRect(0, 0, width, height);
      }
      g.lineCap = 'round';
      for (let i = 0; i < fibres; i++) {   // fibres: short faint curves
        const x = r() * width, y = r() * height, len = (.01 + r() * .03) * U, a = r() * Math.PI * 2;
        g.strokeStyle = `rgba(${r() < .5 ? '70,60,50' : '255,255,255'},${.06 + r() * .08})`; g.lineWidth = .6 + r();
        g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + Math.cos(a + .6) * len, y + Math.sin(a + .6) * len, x + Math.cos(a) * len * 1.6, y + Math.sin(a) * len * 1.6); g.stroke();
      }
      const img = g.getImageData(0, 0, width, height), d = img.data;   // fine grain, seeded
      for (let i = 0, n = 0; i < d.length; i += 4, n++) {
        const v = (M.hash(n, seed) - .5) * 255 * grain;
        d[i] = Math.max(0, Math.min(255, d[i] + v)); d[i + 1] = Math.max(0, Math.min(255, d[i + 1] + v)); d[i + 2] = Math.max(0, Math.min(255, d[i + 2] + v * .9));
      }
      g.putImageData(img, 0, 0);
      const v = g.createRadialGradient(width / 2, height / 2, Math.min(width, height) * .35, width / 2, height / 2, Math.max(width, height) * .75);
      v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, `rgba(40,30,20,${edge})`);
      g.fillStyle = v; g.fillRect(0, 0, width, height);
      return {canvas: c, tone, width, height};
    }
    function drawPaper(ctx, sheet, {x = 0, y = 0, scale = 1, alpha = 1} = {}) {
      if (!sheet || sheet.stub) { ctx.fillStyle = sheet ? sheet.tone : '#efeee8'; ctx.fillRect(0, 0, W, H); return; }
      ctx.save(); ctx.globalAlpha = alpha;
      ctx.translate(W / 2 + x, H / 2 + y); ctx.scale(scale, scale);
      ctx.drawImage(sheet.canvas, -sheet.width / 2, -sheet.height / 2);
      ctx.restore();
    }

    /* ---------- a printed page ---------- */
    const LOREM = 'The attention economy pays for every second a screen keeps. Feeds are designed to be endless, so the decision to stop never arrives on its own. Notifications borrow the urgency of an alarm and spend it on trivia. Each refresh is a small bet; the reward is uncertain, which is exactly why it works. What the eye sees first, it keeps.';
    function document({headline = 'Positioning', kicker = 'THE MIND', body = [LOREM], highlight = '', width = 2200, serif, sans,
      tone = '#f1ece1', ink = '#1d1a16', seed = 11, columns = 2} = {}) {
      serif = serif || (root.Stage && root.Stage.FONTS.SERIF) || 'Georgia, serif';
      sans = sans || (root.Stage && root.Stage.FONTS.SANS) || 'sans-serif';
      const height = Math.round(width * 1.38), margin = width * .07, gutter = width * .04;
      const c = canvas(width, height);
      const lines = [];   // every set line: {text, x, y, w, size} in page pixels (for highlights and focus)
      if (!c) return {stub: true, width, height, lines, highlightLine: -1};
      const g = c.getContext('2d', {willReadFrequently: true});
      const sheet = paper({tone, width, height, grain: .045, blotch: .06, fibres: 220, edge: .18, seed});
      g.drawImage(sheet.canvas, 0, 0);
      g.fillStyle = ink; g.textBaseline = 'alphabetic';
      g.font = `600 ${Math.round(width * .018)}px ${sans}`; g.letterSpacing = `${Math.round(width * .004)}px`;
      g.fillText(kicker.toUpperCase(), margin, margin + width * .02);
      g.letterSpacing = '0px';
      g.fillRect(margin, margin + width * .035, width - margin * 2, Math.max(2, width * .0015));
      const headSize = Math.round(width * .085);
      g.font = `800 ${headSize}px ${serif}`;
      g.fillText(headline, margin, margin + width * .035 + headSize * 1.05, width - margin * 2);
      const top = margin + width * .035 + headSize * 1.45, size = Math.round(width * .026), lead = size * 1.42;
      const colW = (width - margin * 2 - gutter * (columns - 1)) / columns;
      g.font = `400 ${size}px ${serif}`;
      let text = '';
      for (let i = 0; text.length < 2600; i++) text += (i ? ' ' : '') + body[i % body.length];
      const MARK = '';   // the highlighted sentence goes in whole, on a line of its own, a third of the way down
      if (highlight) { const cut = text.indexOf(' ', 520); text = text.slice(0, cut) + ' ' + MARK + ' ' + text.slice(cut + 1); }
      const words = text.split(/\s+/);
      let col = 0, y = top, line = [];
      const flush = (last = false) => {
        if (!line.length) return;
        const x0 = margin + col * (colW + gutter), plain = line.join(' ');
        const natural = g.measureText(plain).width, gaps = line.length - 1;
        if (!last && gaps > 0 && natural > colW * .8) {   // justified, like print
          const extra = (colW - natural) / gaps;
          let x = x0;
          for (const w of line) { g.fillText(w, x, y); x += g.measureText(w).width + g.measureText(' ').width + extra; }
        } else g.fillText(plain, x0, y);
        lines.push({text: plain, x: x0, y, w: last ? natural : colW, size});
        line = []; y += lead;
        if (y > height - margin) { col++; y = top; }
      };
      let highlightLine = -1;
      for (const w of words) {
        if (col >= columns) break;
        if (w === MARK) {   // close the paragraph, set the sentence alone (shrunk to fit the column if needed)
          flush(true);
          if (col >= columns) break;
          const x0 = margin + col * (colW + gutter), natural = g.measureText(highlight).width;
          const k = Math.min(1, colW / natural);
          g.save(); g.font = `400 ${Math.round(size * k)}px ${serif}`; g.fillText(highlight, x0, y); g.restore();
          lines.push({text: highlight, x: x0, y, w: natural * k, size: size * k, highlight: true});
          highlightLine = lines.length - 1; y += lead;
          continue;
        }
        if (g.measureText([...line, w].join(' ')).width > colW) flush();
        if (col >= columns) break;
        line.push(w);
      }
      flush(true);
      const hx = highlightLine >= 0 ? lines[highlightLine].x : 0, hw = highlightLine >= 0 ? lines[highlightLine].w : 0;
      // Depth of field is pre-computed: the page at a few blur levels, cross-faded by distance from the focus line.
      const levels = [];
      for (const b of [3, 7, 13, 22]) {
        const lc = canvas(width, height), lg = lc.getContext('2d');
        lg.filter = `blur(${b}px)`; lg.drawImage(c, 0, 0); levels.push({blur: b, canvas: lc});
      }
      const headY = margin + width * .035 + headSize * .7;   // the headline's middle, for a focus pull
      return {canvas: c, width, height, lines, highlightLine, hx, hw, size, levels, headY};
    }
    /* Draw a page: cx, cy = where the page's focus point lands on screen; scale = page px → screen px; focus = page y in
       focus (defaults to the highlighted line); dof = blur in screen px one page height away from focus; highlight =
       0..1 progress of the marker sweep; rot = a small rotation. Depth of field grows smoothly with distance from the
       focus line, the way a macro lens renders a page. */
    function drawDocument(ctx, doc, {cx = W / 2, cy = H / 2, scale = .5, focus, dof = 18, highlight = 0,
      marker = 'rgba(255,214,0,.82)', rot = 0, alpha = 1, focusX} = {}) {
      if (!doc || doc.stub) return;
      const hl = doc.highlightLine >= 0 ? doc.lines[doc.highlightLine] : null;
      const fy = focus ?? (hl ? hl.y - hl.size * .35 : doc.height / 2), fx = focusX ?? (hl ? doc.hx + doc.hw / 2 : doc.width / 2);
      ctx.save(); ctx.globalAlpha = alpha;
      ctx.translate(cx, cy); ctx.rotate(rot); ctx.scale(scale, scale); ctx.translate(-fx, -fy);
      ctx.shadowColor = 'rgba(0,0,0,.35)'; ctx.shadowBlur = 60; ctx.shadowOffsetY = 30;
      ctx.fillStyle = '#000'; ctx.fillRect(0, 0, doc.width, doc.height);   // the sheet's shadow on what lies under it
      ctx.shadowColor = 'transparent';
      ctx.drawImage(doc.canvas, 0, 0);
      // Depth of field: each pre-blurred level fades in where the page lies far enough from the focus line for that
      // much blur. `dof` = screen px of blur one page height away from focus. Each level is masked by a vertical ramp
      // (transparent around the focus line, opaque beyond it), so blur grows smoothly, with no bands.
      const perPage = Math.max(1e-3, dof);
      const blurAt = y => Math.abs(y - fy) / doc.height * perPage;   // screen px of blur at page row y
      doc.scratch = doc.scratch || canvas(doc.width, doc.height);
      const og = doc.scratch && doc.scratch.getContext('2d');
      for (const level of og ? doc.levels || [] : []) {
        const screenBlur = level.blur * scale;
        const near = screenBlur * .55 / perPage * doc.height, far = screenBlur * 1.1 / perPage * doc.height;   // page px
        if (near > doc.height * 1.1) continue;
        og.globalCompositeOperation = 'copy'; og.drawImage(level.canvas, 0, 0);
        const y0 = fy - far, y1 = fy + far, span = Math.max(1, y1 - y0);
        const grad = og.createLinearGradient(0, y0, 0, y1);
        const inner = (far - near) / span;   // ramp width as a fraction of the gradient
        grad.addColorStop(0, 'rgba(0,0,0,1)');
        grad.addColorStop(Math.min(.5, inner), 'rgba(0,0,0,0)');
        grad.addColorStop(Math.max(.5, 1 - inner), 'rgba(0,0,0,0)');
        grad.addColorStop(1, 'rgba(0,0,0,1)');
        og.globalCompositeOperation = 'destination-in'; og.fillStyle = grad; og.fillRect(0, 0, doc.width, doc.height);
        og.globalCompositeOperation = 'source-over';
        ctx.drawImage(doc.scratch, 0, 0);
      }
      if (hl && highlight > 0) {   // the marker sweeps under the words, multiplied into the ink, as soft as its row
        const r = M.rng(5), h = hl.size * 1.05, top = hl.y - hl.size * .82, soft = blurAt(hl.y - hl.size * .35) / scale;
        const end = doc.hx - hl.size * .2 + (doc.hw + hl.size * .4) * M.easing('cubic.out')(M.clamp(highlight));
        ctx.save(); ctx.globalCompositeOperation = 'multiply'; ctx.fillStyle = marker;
        if (soft > .5) ctx.filter = `blur(${Math.min(40, soft).toFixed(1)}px)`;
        ctx.beginPath(); ctx.moveTo(doc.hx - hl.size * .2, top + r() * h * .08);
        ctx.lineTo(end, top + r() * h * .1); ctx.lineTo(end + h * .1, top + h * .97); ctx.lineTo(doc.hx - hl.size * .25, top + h + r() * h * .06);
        ctx.closePath(); ctx.fill(); ctx.restore();
      }
      ctx.restore();
    }

    /* ---------- type ---------- */
    /* A phrase with mixed weights: '|' breaks a line, *word* is the keyword (accent, bigger, heaviest), ~word is small
       and light. Returns laid-out words: {text, kind, x, y, size, font, width, index}. */
    function layoutPhrase(text, {width = W * .8, size = U * .1, align = 'center', x = W / 2, y = H / 2, family, keyScale = 1.65,
      smallScale = .62, lead = .98, measure} = {}) {
      family = family || (root.Stage && root.Stage.FONTS.SANS) || 'sans-serif';
      const fontOf = (kind, s) => `${kind === 'key' ? 900 : kind === 'small' ? 500 : 750} ${Math.round(s)}px ${family}`;
      let inKey = false;   // *several words* make one keyword span
      const lines = String(text).split('|').map(l => l.trim().split(/\s+/).filter(Boolean).map(raw => {
        const opens = raw.startsWith('*') || raw.startsWith('~*'), closes = /\*[.,;:!?…%]*$/u.test(raw);
        const key = inKey || opens;
        if (opens && !closes) inKey = true;
        if (closes) inKey = false;
        const kind = key ? 'key' : raw.startsWith('~') ? 'small' : 'body';
        const t = raw.replace(/^~/, '').replace(/\*/g, '');
        const s = size * (kind === 'key' ? keyScale : kind === 'small' ? smallScale : 1);
        return {text: t, kind, size: s, font: fontOf(kind, s)};
      }));
      const ctx = measure || env.base;
      let fit = 1;
      for (const line of lines) {   // shrink the whole phrase if one line is too wide
        let w = 0; line.forEach((wd, i) => { ctx.font = wd.font; wd.width = ctx.measureText(wd.text).width; w += wd.width + (i ? size * .22 : 0); });
        fit = Math.min(fit, width / Math.max(w, 1));
      }
      const out = [];
      let cursor = y, index = 0;
      const heights = lines.map(l => Math.max(...l.map(w => w.size)) * fit);
      const total = heights.reduce((a, h) => a + h * lead, 0);
      cursor = y - total / 2;
      lines.forEach((line, li) => {
        const h = heights[li]; cursor += h * lead;
        let w = 0; line.forEach((wd, i) => { wd.size *= fit; wd.font = fontOf(wd.kind, wd.size); ctx.font = wd.font; wd.width = ctx.measureText(wd.text).width; w += wd.width + (i ? size * fit * .22 : 0); });
        let left = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
        for (const wd of line) { out.push({...wd, x: left, y: cursor - (h - wd.size) * .08, line: li, index: index++}); left += wd.width + size * fit * .22; }
      });
      return out;
    }
    /* Draw a laid-out phrase at time t: each word rises in from below with a blur (`at[i]` = its start), the keyword
       settles from 112 % and can glow (on dark grounds). */
    function phrase(ctx, words, t, {at = [], ink = '#121212', accent = '#ff422e', glow = 0, rise = .5, dur = .5, alpha = 1, blur = 0} = {}) {
      for (const w of words) {
        const start = at[w.index] ?? 0, u = M.clamp((t - start) / dur);
        if (u <= 0) continue;
        const e = M.easing('expo.out')(u), s = w.kind === 'key' ? M.mix(1.12, 1, M.easing('back.out')(u)) : 1;
        ctx.save();
        ctx.globalAlpha = alpha * Math.min(1, u * 2.5);
        const b = blur + (1 - e) * 10;
        if (b > .3) ctx.filter = `blur(${b.toFixed(2)}px)`;
        ctx.translate(w.x + w.width / 2, w.y + (1 - e) * w.size * rise); ctx.scale(s, s);
        ctx.font = w.font; ctx.textAlign = 'center'; ctx.letterSpacing = w.kind === 'key' ? `${(-w.size * .02).toFixed(1)}px` : '0px';
        if (glow && w.kind === 'key') { ctx.shadowColor = accent; ctx.shadowBlur = w.size * .45 * glow; }
        ctx.fillStyle = w.kind === 'key' ? accent : ink;
        ctx.globalAlpha *= w.kind === 'small' ? .82 : 1;
        ctx.fillText(w.text, 0, 0);
        ctx.restore();
      }
    }
    /* Type on a curve: pts = a polyline; offset = start along it (px); the glyphs follow its tangent. */
    function textOnPath(ctx, text, pts, {font, color = '#121212', offset = 0, spacing = 0, alpha = 1} = {}) {
      const seg = [], acc = [0];
      for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(l); acc.push(acc[i - 1] + l); }
      const at = d => {
        let i = 1; while (i < acc.length - 1 && acc[i] < d) i++;
        const u = M.clamp((d - acc[i - 1]) / (seg[i - 1] || 1)), a = pts[i - 1], b = pts[i];
        return {x: M.mix(a[0], b[0], u), y: M.mix(a[1], b[1], u), r: Math.atan2(b[1] - a[1], b[0] - a[0])};
      };
      ctx.save(); ctx.font = font; ctx.fillStyle = color; ctx.globalAlpha = alpha; ctx.textAlign = 'center';
      let d = offset;
      for (const ch of [...text]) {
        const w = ctx.measureText(ch).width, p = at(d + w / 2);
        ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.fillText(ch, 0, 0); ctx.restore();
        d += w + spacing;
      }
      ctx.restore();
    }
    function numeral(ctx, text, {x = W / 2, y = H / 2, size = U * .9, family, color = '#1a1a1a', alpha = .9, blur = 0, weight = 300, italic = true} = {}) {
      family = family || (root.Stage && root.Stage.FONTS.SERIF) || 'serif';
      ctx.save(); ctx.globalAlpha = alpha; if (blur > .3) ctx.filter = `blur(${blur.toFixed(1)}px)`;
      ctx.font = `${italic ? 'italic ' : ''}${weight} ${Math.round(size)}px ${family}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.letterSpacing = `${(-size * .04).toFixed(1)}px`; ctx.fillStyle = color; ctx.fillText(text, x, y);
      ctx.restore();
    }

    /* ---------- shapes ---------- */
    const smooth = pts => {   // Chaikin, twice: a polyline into a soft curve
      let p = pts;
      for (let k = 0; k < 3; k++) {
        const q = [p[0]];
        for (let i = 0; i < p.length - 1; i++) { const a = p[i], b = p[i + 1]; q.push([a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25], [a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75]); }
        q.push(p[p.length - 1]); p = q;
      }
      return p;
    };
    function trim(ctx, pts, {from = 0, to = 1, width = 4, color = '#121212', cap = 'round', shadow = 0, alpha = 1, dash} = {}) {
      if (to <= from) return;
      const acc = [0];
      for (let i = 1; i < pts.length; i++) acc.push(acc[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
      const total = acc[acc.length - 1], a = from * total, b = to * total;
      ctx.save(); ctx.globalAlpha = alpha; ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = cap; ctx.lineJoin = 'round';
      if (dash) ctx.setLineDash(dash);
      if (shadow) { ctx.shadowColor = 'rgba(0,0,0,.28)'; ctx.shadowBlur = width * shadow; ctx.shadowOffsetY = width * .25 * shadow; }
      ctx.beginPath();
      let started = false;
      for (let i = 1; i < pts.length; i++) {
        if (acc[i] < a) continue;
        const p0 = pts[i - 1], p1 = pts[i], s0 = Math.max(a, acc[i - 1]), s1 = Math.min(b, acc[i]), l = acc[i] - acc[i - 1] || 1;
        const q0 = [M.mix(p0[0], p1[0], (s0 - acc[i - 1]) / l), M.mix(p0[1], p1[1], (s0 - acc[i - 1]) / l)];
        const q1 = [M.mix(p0[0], p1[0], (s1 - acc[i - 1]) / l), M.mix(p0[1], p1[1], (s1 - acc[i - 1]) / l)];
        if (!started) { ctx.moveTo(q0[0], q0[1]); started = true; }
        ctx.lineTo(q1[0], q1[1]);
        if (acc[i] >= b) break;
      }
      ctx.stroke(); ctx.restore();
    }
    function ribbon(ctx, controls, {width = U * .09, color = '#bdbab2', from = 0, to = 1, shadow = .6, alpha = 1} = {}) {
      trim(ctx, smooth(controls), {from, to, width, color, cap: 'butt', shadow, alpha});
    }
    function circle(cx, cy, r, n = 96, start = -Math.PI / 2) {
      return Array.from({length: n + 1}, (_, i) => [cx + r * Math.cos(start + i / n * Math.PI * 2), cy + r * Math.sin(start + i / n * Math.PI * 2)]);
    }
    function roundRect(ctx, x, y, w, h, r) {
      ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath();
    }
    function pin(ctx, x, y, r = U * .022, color = '#e3261a') {
      ctx.save();
      ctx.fillStyle = 'rgba(0,0,0,.28)'; ctx.filter = `blur(${(r * .35).toFixed(1)}px)`;
      ctx.beginPath(); ctx.ellipse(x + r * .5, y + r * .9, r * .9, r * .45, 0, 0, Math.PI * 2); ctx.fill();
      ctx.filter = 'none';
      const g = ctx.createRadialGradient(x - r * .35, y - r * .4, r * .08, x, y, r * 1.05);
      g.addColorStop(0, '#ff9a8a'); g.addColorStop(.35, color); g.addColorStop(1, '#6e0c06');
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }
    /* A card: paper or a flat colour, a soft shadow that grows with lift, a pin at the top. content(ctx, w, h) draws
       inside, in card coordinates. */
    function card(ctx, {x = W / 2, y = H / 2, w = U * .55, h = U * .7, rot = 0, lift = 1, fill = '#9b9a97', radius = U * .012,
      pinned = true, content, alpha = 1, texture} = {}) {
      ctx.save(); ctx.globalAlpha = alpha; ctx.translate(x, y); ctx.rotate(rot);
      ctx.shadowColor = `rgba(0,0,0,${.22 + .12 * lift})`; ctx.shadowBlur = U * (.03 + .05 * lift); ctx.shadowOffsetY = U * (.012 + .03 * lift); ctx.shadowOffsetX = U * .008 * lift;
      ctx.fillStyle = fill; roundRect(ctx, -w / 2, -h / 2, w, h, radius); ctx.fill();
      ctx.shadowColor = 'transparent';
      if (texture && !texture.stub) { ctx.save(); roundRect(ctx, -w / 2, -h / 2, w, h, radius); ctx.clip(); ctx.globalAlpha = alpha * .35; ctx.globalCompositeOperation = 'multiply'; ctx.drawImage(texture.canvas, -w / 2, -h / 2, w, h); ctx.restore(); }
      if (content) { ctx.save(); ctx.translate(-w / 2, -h / 2); content(ctx, w, h); ctx.restore(); }
      if (pinned) pin(ctx, 0, -h / 2 + U * .035);
      ctx.restore();
    }
    /* A phone: body, bezel, a screen drawn by screen(ctx, w, h, t); tilt is a small rotation. */
    function phone(ctx, {x = W / 2, y = H / 2, h = U * 1.1, rot = 0, lift = 1, screen, alpha = 1, glow = 0} = {}) {
      const w = h * .49, r = w * .14;
      ctx.save(); ctx.globalAlpha = alpha; ctx.translate(x, y); ctx.rotate(rot);
      ctx.shadowColor = `rgba(0,0,0,${.35 + .15 * lift})`; ctx.shadowBlur = U * (.05 + .06 * lift); ctx.shadowOffsetY = U * (.02 + .03 * lift);
      ctx.fillStyle = '#121214'; roundRect(ctx, -w / 2, -h / 2, w, h, r); ctx.fill();
      ctx.shadowColor = 'transparent';
      const edge = ctx.createLinearGradient(-w / 2, 0, w / 2, 0);
      edge.addColorStop(0, 'rgba(255,255,255,.18)'); edge.addColorStop(.08, 'rgba(255,255,255,0)'); edge.addColorStop(.92, 'rgba(255,255,255,0)'); edge.addColorStop(1, 'rgba(255,255,255,.12)');
      ctx.strokeStyle = edge; ctx.lineWidth = w * .02; roundRect(ctx, -w / 2, -h / 2, w, h, r); ctx.stroke();
      const sw = w * .9, sh = h * .955;
      ctx.save(); roundRect(ctx, -sw / 2, -sh / 2, sw, sh, r * .85); ctx.clip();
      ctx.fillStyle = '#0b0b0d'; ctx.fillRect(-sw / 2, -sh / 2, sw, sh);
      if (glow) { ctx.shadowColor = 'transparent'; }
      if (screen) { ctx.translate(-sw / 2, -sh / 2); screen(ctx, sw, sh); }
      ctx.restore();
      ctx.fillStyle = '#000'; roundRect(ctx, -w * .14, -sh / 2 + w * .035, w * .28, w * .075, w * .04); ctx.fill();   // the island
      const sheen = ctx.createLinearGradient(-w / 2, -h / 2, w / 2, h / 2);
      sheen.addColorStop(0, 'rgba(255,255,255,.10)'); sheen.addColorStop(.4, 'rgba(255,255,255,0)');
      ctx.fillStyle = sheen; roundRect(ctx, -sw / 2, -sh / 2, sw, sh, r * .85); ctx.fill();
      ctx.restore();
    }
    /* A notification on a phone screen, iOS-like: app tile, title, line, time. */
    function notification(ctx, x, y, w, {title = 'App', body = '', time = 'now', tint = '#ff3b30', alpha = 1} = {}) {
      const h = w * .2, r = h * .28, sans = (root.Stage && root.Stage.FONTS.SANS) || 'sans-serif';
      ctx.save(); ctx.globalAlpha = alpha;
      ctx.fillStyle = 'rgba(58,58,62,.92)'; roundRect(ctx, x, y, w, h, r); ctx.fill();
      ctx.fillStyle = tint; roundRect(ctx, x + h * .18, y + h * .2, h * .6, h * .6, h * .14); ctx.fill();
      ctx.fillStyle = '#f2f2f2'; ctx.font = `700 ${Math.round(h * .24)}px ${sans}`; ctx.textAlign = 'left';
      ctx.fillText(title, x + h * .95, y + h * .42);
      ctx.fillStyle = 'rgba(242,242,242,.75)'; ctx.font = `400 ${Math.round(h * .21)}px ${sans}`;
      ctx.fillText(body, x + h * .95, y + h * .74, w - h * 1.2);
      ctx.fillStyle = 'rgba(242,242,242,.5)'; ctx.font = `400 ${Math.round(h * .18)}px ${sans}`; ctx.textAlign = 'right';
      ctx.fillText(time, x + w - h * .2, y + h * .42);
      ctx.restore();
      return h;
    }
    /* A cut-out (an image with alpha): a contact shadow under it, a soft drop shadow, depth blur. */
    function object(ctx, img, {x = W / 2, y = H / 2, h = U * .5, rot = 0, blur = 0, lift = .5, alpha = 1, shadow = true} = {}) {
      if (!img || img.stub) return;
      const w = h * (img.naturalWidth || img.width) / (img.naturalHeight || img.height);
      ctx.save(); ctx.globalAlpha = alpha; ctx.translate(x, y);
      if (shadow) {
        ctx.save(); ctx.filter = `blur(${(U * .012 * (1 + lift)).toFixed(1)}px)`; ctx.fillStyle = `rgba(0,0,0,${.35 - .15 * lift})`;
        ctx.beginPath(); ctx.ellipse(0, h * .48 + U * .01 * lift, w * .38, h * .045, 0, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      }
      ctx.rotate(rot);
      if (blur > .3) ctx.filter = `blur(${blur.toFixed(1)}px)`;
      if (shadow) { ctx.shadowColor = 'rgba(0,0,0,.3)'; ctx.shadowBlur = U * .04 * (1 + lift); ctx.shadowOffsetY = U * .025 * (1 + lift); }
      ctx.drawImage(img, -w / 2, -h / 2, w, h);
      ctx.restore();
    }
    const depthBlur = (z, focus = 0, k = 9) => Math.min(30, Math.abs(z - focus) * k);

    return {paper, drawPaper, document, drawDocument, layoutPhrase, phrase, textOnPath, numeral, trim, ribbon, smooth,
      circle, roundRect, pin, card, phone, notification, object, depthBlur};
  }

  root.Collage = {create};
})(typeof globalThis !== 'undefined' ? globalThis : this);
