/* Recipe · ranking, a top N that counts down. Each place gets the same share of time: its number slams in huge, first
   as an outline that fills as it lands, its label rises under it and a short note follows; a vertical whip with real
   motion blur carries the eye to the next place. Number one lands in the accent and holds longer. Dots along the side
   say how far the countdown is, so the viewer waits for number one instead of leaving.
   Data: data.json (copied by new_piece.py): {"title": "…", "items": [{"rank": 5, "label": "…", "note": "…"}, …]}
   sorted from the last place to number one (the order they appear).
   Times: hits 'first place', 'number one', 'exit'; the places in between spread evenly.
   Guides: references/create/niches.md (lists), references/edit/pacing-retention.md (open loops). */
(() => {
  'use strict';
  const M = window.MotionMath, S = window.Stage, {SANS} = S.FONTS;
  const PAPER = '#efeee8', INK = '#101110', MUTED = '#6d6b66', ACCENT = '#ff422e';
  const TITLE = 'TITLE';
  const SAMPLE = {title: '', items: [
    {rank: 5, label: 'Autoplay', note: 'the next video starts before you decide'},
    {rank: 4, label: 'Red badges', note: 'a number that asks to be zero'},
    {rank: 3, label: 'Pull to refresh', note: 'a slot machine in your thumb'},
    {rank: 2, label: 'Streaks', note: 'losing feels worse than winning feels good'},
    {rank: 1, label: 'Infinite scroll', note: 'no bottom, no moment to stop'}]};
  let data = SAMPLE, places = [], numberSize = 400, labelSize = 90, noteSize = 44, titleSize = 50;
  let FIRST = .2, ONE = 5, EXIT = 7.5, slot = 1;

  async function load(plan) {
    if (!plan.data || typeof fetch !== 'function') return null;
    try { const r = await fetch(plan.data, {cache: 'no-store'}); return r.ok ? r.json() : null; } catch (e) { return null; }
  }

  window.Stage.run({
    fonts: [`900 200px ${SANS}`, `800 100px ${SANS}`, `500 50px ${SANS}`],
    background: PAPER,
    layers: [],
    shutter: 300,
    finish: {toneMap: 'clip', vignette: .12, grain: .03},

    async setup({W, H, U, DURATION, safe, hit, fitLines, plan}) {
      data = {...SAMPLE, ...((await load(plan)) || {})};
      if (!data.title) data.title = TITLE;
      const items = (data.items || []).slice(0, 10);
      FIRST = hit('first place', .2); EXIT = hit('exit', DURATION - .5);
      ONE = hit('number one', Math.max(FIRST + .8, EXIT - 2.4));
      slot = items.length > 1 ? (ONE - FIRST) / (items.length - 1) : 1;
      numberSize = Math.round(Math.min(.5 * U, safe.height * .3)); titleSize = Math.round(.04 * U);
      places = items.map((it, i) => {
        const label = fitLines(it.label, {weight: 800, family: SANS, max: Math.round(.11 * U), min: Math.round(.06 * U), width: safe.width * .9, maxLines: 2});
        const note = fitLines(it.note || '', {weight: 500, family: SANS, max: Math.round(.045 * U), min: Math.round(.035 * U), width: safe.width * .85, maxLines: 3});
        return {...it, at: FIRST + i * slot, one: i === items.length - 1, label, note};
      });
      places.forEach((p, i) => { p.leave = i + 1 < places.length ? places[i + 1].at - .12 : EXIT; });
    },

    state(t, {W, H, U, FPS}) {
      const tf = (Math.floor(t * FPS + 1e-6) + .5) / FPS;
      let k = 0;
      while (k + 1 < places.length && tf >= places[k + 1].at - .12) k++;
      const p = places[k] || {at: 0, leave: 1, one: false};
      const land = M.easing('expo.out')(M.clamp((t - p.at) / .32));
      const fill = M.clamp((t - p.at - .1) / .18);
      const out = M.easing('expo.in')(M.clamp((t - (p.leave - .14)) / .14));          // the whip up, into the next place
      const inn = 1 - M.easing('expo.out')(M.clamp((t - p.at + .02) / .2));            // the next place arrives from below
      const dy = (-out + inn) * H * .55;
      const punch = M.impulse(t, [{time: p.at + .12, amplitude: p.one ? 1.4 : 1}], 10);
      const labelIn = M.easing('cubic.out')(M.clamp((t - p.at - .18) / .3));
      const noteIn = M.easing('cubic.out')(M.clamp((t - p.at - .4) / .3));
      const exit = M.clamp((t - EXIT) / .4);
      return {t, k, p, land, fill, dy, punch, labelIn, noteIn, exit, track: [[W / 2, H * .4 + dy], [W / 2 + U * .3, H * .4 + dy]],
        debug: {places: places.length, showing: p.rank}};
    },

    draw(s, {base}, {W, H, U, safe}) {
      const {p} = s;
      if (!p || p.rank === undefined) return;
      base.globalAlpha = 1 - s.exit;
      base.fillStyle = MUTED; base.font = S.font({weight: 500, size: titleSize, family: SANS}); base.textAlign = 'left';
      base.fillText(String(data.title).toUpperCase(), safe.x, safe.y + titleSize, safe.width);
      // Countdown dots: how many places are left before number one.
      places.forEach((q, i) => {
        base.fillStyle = i < s.k ? MUTED : i === s.k ? (q.one ? ACCENT : INK) : 'rgba(16,17,16,.18)';
        base.beginPath(); base.arc(safe.x + safe.width - U * .015, safe.y + titleSize * 2.6 + i * U * .045, U * (i === s.k ? .012 : .008), 0, Math.PI * 2); base.fill();
      });
      base.save(); base.translate(0, s.dy);
      const cy = safe.y + safe.height * .42, scale = (1.6 - .6 * s.land) * (1 + .06 * s.punch);
      base.save(); base.translate(W / 2, cy); base.scale(scale, scale);
      base.font = S.font({weight: 900, size: numberSize, family: SANS}); base.textAlign = 'center';
      const color = p.one ? ACCENT : INK, text = String(p.rank);
      base.lineWidth = U * .006; base.strokeStyle = color; base.strokeText(text, 0, numberSize * .35);   // outline first,
      base.globalAlpha = (1 - s.exit) * s.fill; base.fillStyle = color; base.fillText(text, 0, numberSize * .35);   // then it fills as it lands
      base.restore();
      base.globalAlpha = (1 - s.exit) * s.labelIn; base.fillStyle = INK; base.textAlign = 'center';
      base.font = p.label.font;
      p.label.lines.forEach((line, i) => base.fillText(line, W / 2, cy + numberSize * .55 + (i + .8) * p.label.size * 1.05 + (1 - s.labelIn) * U * .04));
      const noteY = cy + numberSize * .55 + (p.label.lines.length + .6) * p.label.size * 1.05;
      base.globalAlpha = (1 - s.exit) * s.noteIn; base.fillStyle = MUTED; base.font = p.note.font;
      p.note.lines.forEach((line, i) => base.fillText(line, W / 2, noteY + (i + .8) * p.note.size * 1.2));
      base.restore();
      base.globalAlpha = 1;
    },
  });
})();
