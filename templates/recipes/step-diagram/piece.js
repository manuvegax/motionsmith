/* Recipe · step diagram, for education, psychology and any process. The diagram builds one step at a time and never
   resets: an arrow draws from the previous node, the new node lands in the accent with its label, and the step's
   explanation sits in the lower band for its reading time; then the node settles into ink and the next arrow starts.
   A process that repeats ("loop": true) is laid out as a circle and its last arrow closes back to the first node.
   The diagram ends complete, under the takeaway. The active node breathes while its explanation is read.
   Data: data.json (copied by new_piece.py): {"title": "…", "loop": true, "takeaway": "…",
     "steps": [{"label": "Trigger", "note": "…"}, …]} (two to seven steps).
   Times: hits 'first step', 'takeaway', 'exit'; the steps in between spread evenly, each at least its reading time.
   Guides: references/create/niches.md (education), references/edit/story-structures.md §9 (explainers). */
(() => {
  'use strict';
  const M = window.MotionMath, S = window.Stage, {SANS, SERIF} = S.FONTS;
  const PAPER = '#efeee8', INK = '#101110', MUTED = '#7a7872', ACCENT = '#ff422e';
  const TITLE = 'TITLE';
  const SAMPLE = {title: '', loop: true, takeaway: 'Break one link and the loop loosens.', steps: [
    {label: 'Trigger', note: 'a notification, a pause, a moment of boredom'},
    {label: 'Craving', note: 'the urge to check, before you have thought'},
    {label: 'Scroll', note: 'the thumb moves; something new appears'},
    {label: 'Reward', note: 'a small hit of novelty, never quite enough'}]};
  let data = SAMPLE, title = [], nodes = [], R = 60, labelSize = 50, noteSize = 44, titleSize = 60, bandY = 0, FIRST = .4, TAKE = 6, EXIT = 7.5;

  async function load(plan) {
    if (!plan.data || typeof fetch !== 'function') return null;
    try { const r = await fetch(plan.data, {cache: 'no-store'}); return r.ok ? r.json() : null; } catch (e) { return null; }
  }

  window.Stage.run({
    fonts: [`800 100px ${SANS}`, `italic 400 100px ${SERIF}`],
    background: PAPER,
    layers: [],
    finish: {toneMap: 'clip', vignette: .1, grain: .03},

    async setup({W, H, U, DURATION, safe, hit, fitLines, plan}) {
      data = {...SAMPLE, ...((await load(plan)) || {})};
      if (!data.title) data.title = TITLE;
      const steps = (data.steps || []).slice(0, 7);
      FIRST = hit('first step', .4); EXIT = hit('exit', DURATION - .5); TAKE = hit('takeaway', Math.max(FIRST + 1, EXIT - 1.8));
      const fit = fitLines(data.title, {weight: 800, family: SANS, max: Math.round(.07 * U), min: Math.round(.045 * U), width: safe.width, maxLines: 2});
      title = fit.lines; titleSize = fit.size; labelSize = Math.round(.05 * U); noteSize = Math.round(.048 * U);
      const areaTop = safe.y + title.length * titleSize * 1.1 + titleSize * 1.6, areaBottom = safe.y + safe.height * .64;
      const cx = W / 2, cy = (areaTop + areaBottom) / 2, n = steps.length;
      R = Math.round(Math.min(.09 * U, (areaBottom - areaTop) / (n * 2.6)));
      const each = n > 1 ? (TAKE - .4 - FIRST) / n : 1;
      nodes = steps.map((s, i) => {
        let x, y, a = Math.PI / 2;   // a: the direction the label sits in, away from the arrows
        if (data.loop && n > 2) {   // a circle, starting at the top, clockwise
          const ring = Math.min(safe.width * .36, (areaBottom - areaTop) * .44);
          a = -Math.PI / 2 + i * 2 * Math.PI / n;
          x = cx + ring * Math.cos(a); y = cy + ring * Math.sin(a);
        } else { x = cx; y = areaTop + R + i * (areaBottom - areaTop - 2 * R) / Math.max(1, n - 1); a = 0; }
        const note = fitLines(s.note || '', {weight: 400, style: 'italic', family: SERIF, max: noteSize, min: Math.round(noteSize * .75), width: safe.width * .9, maxLines: 2});
        return {...s, i, x, y, a, at: FIRST + i * each, note};
      });
      bandY = safe.y + safe.height * .86;
    },

    state(t, {W, H}) {
      const arrows = nodes.map((nd, i) => {
        const from = i > 0 ? nodes[i - 1] : (data.loop && nodes.length > 2 && t > TAKE - .5 ? nodes[nodes.length - 1] : null);
        const at = i > 0 ? nd.at - .3 : TAKE - .45;
        return from ? {from, to: nd, u: M.easing('cubic.inOut')(M.clamp((t - at) / .3))} : null;
      }).filter(Boolean);
      const active = nodes.reduce((k, nd, i) => (t >= nd.at ? i : k), -1);
      const shown = nodes.map(nd => ({nd, land: M.easing('back.out')(M.clamp((t - nd.at) / .35)),
        hot: t < TAKE ? M.clamp((t - nd.at) / .2) * (1 - M.clamp((t - (nodes[nd.i + 1] ? nodes[nd.i + 1].at - .3 : TAKE)) / .25)) : 0}));
      const breathe = 1 + .04 * Math.sin(t * 4);
      const take = M.easing('cubic.out')(M.clamp((t - TAKE) / .4)), exit = M.clamp((t - EXIT) / .4);
      return {t, arrows, shown, active, breathe, take, exit, track: shown.map(s => [s.nd.x, s.nd.y - (1 - s.land) * R]),
        debug: {steps: nodes.length, loop: !!data.loop, active}};
    },

    draw(s, {base}, {W, H, U, safe}) {
      base.globalAlpha = 1 - s.exit;
      base.fillStyle = INK; base.textAlign = 'center'; base.font = S.font({weight: 800, size: titleSize, family: SANS});
      title.forEach((line, i) => base.fillText(line, W / 2, safe.y + (i + 1) * titleSize * 1.1));
      // Arrows: drawn from node to node, stopping at the rims, with a head when they arrive.
      for (const a of s.arrows) {
        const dx = a.to.x - a.from.x, dy = a.to.y - a.from.y, d = Math.hypot(dx, dy) || 1, ux = dx / d, uy = dy / d;
        const x0 = a.from.x + ux * R * 1.15, y0 = a.from.y + uy * R * 1.15;
        const x1 = x0 + (d - R * 2.3) * a.u * ux, y1 = y0 + (d - R * 2.3) * a.u * uy;
        base.strokeStyle = INK; base.lineWidth = U * .005; base.lineCap = 'round';
        base.beginPath(); base.moveTo(x0, y0); base.lineTo(x1, y1); base.stroke();
        if (a.u > .9) {
          base.fillStyle = INK; base.beginPath();
          base.moveTo(x1 + ux * U * .012, y1 + uy * U * .012);
          base.lineTo(x1 - uy * U * .012 - ux * U * .01, y1 + ux * U * .012 - uy * U * .01);
          base.lineTo(x1 + uy * U * .012 - ux * U * .01, y1 - ux * U * .012 - uy * U * .01);
          base.fill();
        }
      }
      // Nodes: the active one in the accent, breathing; the rest settled in ink.
      for (const {nd, land, hot} of s.shown) {
        if (land <= 0) continue;
        const r = R * land * (hot > .5 ? s.breathe : 1);
        base.fillStyle = hot > .5 ? ACCENT : INK;
        base.beginPath(); base.arc(nd.x, nd.y, r, 0, Math.PI * 2); base.fill();
        base.fillStyle = PAPER; base.font = S.font({weight: 800, size: Math.round(R * .8), family: SANS});
        base.fillText(String(nd.i + 1), nd.x, nd.y + R * .28);
        base.fillStyle = INK; base.font = S.font({weight: 800, size: labelSize, family: SANS});
        const dx = Math.cos(nd.a), dy = Math.sin(nd.a);   // outward from the ring (a chain puts labels to the right)
        if (Math.abs(dx) > .5) {
          base.textAlign = dx > 0 ? 'left' : 'right';
          base.fillText(nd.label, nd.x + dx * R * 1.35, nd.y + labelSize * .35);
        } else base.fillText(nd.label, nd.x, nd.y + (dy > 0 ? R + labelSize * 1.1 : -R - labelSize * .45));
        base.textAlign = 'center';
      }
      // The explanation of the active step, in the lower band; the takeaway replaces it at the end.
      const nd = s.active >= 0 ? nodes[s.active] : null;
      base.textAlign = 'center';
      if (nd && s.take < 1) {
        base.globalAlpha = (1 - s.exit) * (1 - s.take) * M.clamp((s.t - nd.at - .15) / .25);
        base.fillStyle = MUTED; base.font = nd.note.font;
        nd.note.lines.forEach((line, i) => base.fillText(line, W / 2, bandY + i * nd.note.size * 1.2));
      }
      if (s.take > 0) {
        base.globalAlpha = (1 - s.exit) * s.take; base.fillStyle = ACCENT;
        base.font = S.font({weight: 800, size: Math.round(.055 * U), family: SANS});
        base.fillText(data.takeaway || '', W / 2, bandY + (1 - s.take) * U * .03);
      }
      base.globalAlpha = 1;
    },
  });
})();
