/* Recipe · chart bars, for data and finance. Horizontal bars (labels read in a vertical frame) grow from a zero
   baseline one after another while their values count up; the highlighted bar lands last, in the accent, on its own
   hit, and the others step back. The source sits at the bottom, always readable: a number on screen says where it
   comes from. The hold breathes: a sheen crosses the highlighted bar and the grid drifts.
   Data honesty: bars start at zero and their length is proportional to the value; counts never overshoot; no 3D.
   Data: data.json (copied by new_piece.py; plan.data points to it):
     {"title": "…", "unit": "%", "decimals": 0, "source": "Source: …", "highlight": "2026",
      "bars": [{"label": "2022", "value": 31}, …]}
   Times: hits 'first bar', 'highlight', 'exit'. Guides: references/create/niches.md (data), scene-recipes.md. */
(() => {
  'use strict';
  const M = window.MotionMath, S = window.Stage, {SANS} = S.FONTS;
  const BG = '#0f1115', INK = '#f2efe8', MUTED = '#8d929c', ACCENT = '#ff422e', GRID = 'rgba(242,239,232,.08)';
  const TITLE = 'TITLE';   // used when data.json has no title
  const SAMPLE = {title: '', unit: '%', decimals: 0, source: 'Source: sample data, replace data.json', highlight: '2026',
    bars: [{label: '2022', value: 31}, {label: '2023', value: 38}, {label: '2024', value: 44}, {label: '2025', value: 52}, {label: '2026', value: 67}]};
  const GROW = .55;        // seconds one bar takes to grow
  let data = SAMPLE, rows = [], title = [], titleSize = 80, rowH = 100, barX = 0, barMax = 600, labelSize = 50, valueSize = 50;
  let FIRST = .35, HIGH = 2.6, EXIT = 5.4, maxValue = 1, sourceSize = 40;

  async function load(plan) {
    if (!plan.data || typeof fetch !== 'function') return null;
    try { const r = await fetch(plan.data, {cache: 'no-store'}); return r.ok ? r.json() : null; } catch (e) { return null; }
  }
  const format = v => `${v.toFixed(data.decimals || 0)}${data.unit || ''}`;

  window.Stage.run({
    fonts: [`800 100px ${SANS}`, `600 60px ${SANS}`],
    background: BG,
    layers: [],
    finish: {toneMap: 'clip', vignette: .18, grain: .025},

    async setup({W, U, DURATION, safe, base, hit, fitLines, plan}) {
      data = {...SAMPLE, ...((await load(plan)) || {})};
      if (!data.title) data.title = TITLE;
      const bars = (data.bars || []).slice(0, 8);
      FIRST = hit('first bar', .35); HIGH = hit('highlight', Math.min(DURATION - 2, FIRST + bars.length * .45 + .2));
      EXIT = hit('exit', DURATION - .5);
      maxValue = Math.max(1e-9, ...bars.map(b => Math.abs(b.value)));
      const fit = fitLines(data.title, {weight: 800, family: SANS, max: Math.round(.085 * U), min: Math.round(.05 * U),
        width: safe.width, maxLines: 3, lineHeight: 1.05});
      title = fit.lines; titleSize = fit.size;
      const top = safe.y + title.length * titleSize * 1.05 + titleSize * 1.4;
      sourceSize = Math.round(.032 * U);
      const bottom = safe.y + safe.height - sourceSize * 2.2;
      rowH = Math.min(.21 * U, (bottom - top) / Math.max(1, bars.length));
      labelSize = Math.round(rowH * .32); valueSize = Math.round(rowH * .36);
      base.font = S.font({weight: 600, size: labelSize, family: SANS});
      const labelW = Math.max(...bars.map(b => base.measureText(b.label).width));
      base.font = S.font({weight: 800, size: valueSize, family: SANS});
      const valueW = base.measureText(format(maxValue)).width;
      barX = safe.x + labelW + labelSize * .6;
      barMax = safe.x + safe.width - barX - valueW - valueSize * .5;
      const others = bars.filter(b => b.label !== String(data.highlight));
      const step = others.length > 1 ? Math.max(.12, (HIGH - .35 - FIRST) / (others.length - 1)) : 0;
      let k = 0;
      rows = bars.map((b, i) => {
        const key = b.label === String(data.highlight);
        return {...b, key, y: top + i * rowH, at: key ? HIGH - GROW * .7 : FIRST + (k++) * step};
      });
    },

    state(t, {W, H, FPS}) {
      // The bars grow with sub-frame motion blur; the numbers are read from the frame, so they stay sharp.
      const tf = (Math.floor(t * FPS + 1e-6) + .5) / FPS;
      const exit = M.easing('cubic.in')(M.clamp((t - EXIT) / .45));
      const keyLanded = M.clamp((t - HIGH) / .3);
      const bars = rows.map(r => {
        const u = M.easing('expo.out')(M.clamp((t - r.at) / GROW));
        const punch = r.key ? M.impulse(t, [{time: HIGH, amplitude: 1}], 10) : 0;
        return {r, u, punch, dim: r.key ? 0 : .55 * keyLanded, value: r.value * M.easing('expo.out')(M.clamp((tf - r.at) / GROW))};
      });
      const track = bars.map(b => [barX + barMax * Math.abs(b.r.value) / maxValue * b.u, b.r.y]);
      track.push([0, exit * H * .05]);
      return {t, bars, exit, sheen: M.clamp((t - HIGH - .4) / 1.1) % 1, track,
        debug: {bars: rows.length, highlight: rows.filter(r => r.key).map(r => r.label)}};
    },

    draw(s, {base}, {W, H, U, safe}) {
      const t = s.t, alpha = 1 - s.exit, drift = (t * .015 * U) % (.08 * U);
      base.save(); base.globalAlpha = alpha;
      base.strokeStyle = GRID; base.lineWidth = Math.max(1, .0015 * U);   // the grid drifts: a hold never freezes
      for (let x = barX - drift; x < W; x += .08 * U) { if (x < barX) continue; base.beginPath(); base.moveTo(x, rows[0] ? rows[0].y - rowH * .6 : 0); base.lineTo(x, rows.length ? rows[rows.length - 1].y + rowH * .4 : H); base.stroke(); }
      base.fillStyle = INK; base.font = S.font({weight: 800, size: titleSize, family: SANS}); base.textAlign = 'left';
      title.forEach((line, i) => base.fillText(line, safe.x, safe.y + (i + 1) * titleSize * 1.05));
      base.fillStyle = MUTED; base.font = S.font({weight: 600, size: sourceSize, family: SANS});
      base.fillText(data.source || '', safe.x, safe.y + safe.height - sourceSize * .6);
      for (const b of s.bars) {
        const {r} = b, len = barMax * Math.abs(r.value) / maxValue * b.u, h = rowH * .56, y = r.y - h / 2;
        base.globalAlpha = alpha * (1 - b.dim);
        base.fillStyle = r.key ? INK : MUTED; base.textAlign = 'right';
        base.font = S.font({weight: r.key ? 800 : 600, size: labelSize, family: SANS});
        base.fillText(r.label, barX - labelSize * .4, r.y + labelSize * .35);
        base.fillStyle = r.key ? ACCENT : INK;
        base.fillRect(barX, y - b.punch * h * .08, len, h * (1 + b.punch * .16));
        if (b.u > .02) {
          base.textAlign = 'left'; base.fillStyle = r.key ? ACCENT : INK;
          base.font = S.font({weight: 800, size: Math.round(valueSize * (r.key ? 1.15 : 1)), family: SANS});
          base.fillText(format(b.value), barX + len + valueSize * .3, r.y + valueSize * .36);
        }
        if (r.key && s.sheen > 0) {   // a light sheen crosses the highlighted bar while it holds
          const x = barX + len * s.sheen, g = base.createLinearGradient(x - .06 * U, 0, x + .06 * U, 0);
          g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(.5, 'rgba(255,255,255,.35)'); g.addColorStop(1, 'rgba(255,255,255,0)');
          base.fillStyle = g; base.fillRect(barX, y, len, h);
        }
      }
      base.restore();
    },
  });
})();
