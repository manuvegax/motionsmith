/* Recipe · B-roll story: footage and photos under a voice. The background is the B-roll timeline that
   scripts/broll.py assemble writes (clips trimmed to their scenes, stills moving in code with Ken Burns and parallax,
   one grade for every source, see kit/footage.js). Over it, the spoken phrase sits in the lower third: each word lands
   as it is said, the stressed word gets an accent box, and a soft shadow and a bottom gradient keep the type legible
   on any picture. A slow push on the whole frame keeps even a held shot alive.
   Data: plan.broll (timeline.json) and plan.voice (voice.json, scripts/voice_plan.py). Without a timeline the
   background is a moving code-drawn field; without a voice, TITLE is spread as a demo voice (*word* = stressed).
   Guides: references/edit/broll.md, references/edit/voiceover.md, references/edit/captions-titles.md. */
(() => {
  'use strict';
  const M = window.MotionMath, S = window.Stage, F = window.Footage, {SANS} = S.FONTS;
  const INK = '#101110', PAPER = '#f4f2ec', ACCENT = '#ff422e';
  const TITLE = 'TITLE';
  const MAX_WORDS = 24, LEAD_FRAMES = 2, RISE = .12;
  let footage = null, phrases = [], size = 80;

  function demo(title, duration) {
    const tokens = String(title).split(/\s+/).filter(Boolean);
    const step = Math.min(.42, Math.max(.5, duration - .9) / Math.max(1, tokens.length));
    let t = .15, current = null;
    const out = [];
    tokens.forEach((raw, i) => {
      const w = {text: raw.replace(/\*/g, ''), start: t, end: t + step * .85, emphasis: /^\*.+\*[.,;:!?…]*$/u.test(raw)};
      if (!current) { current = {start: t, end: t, words: []}; out.push(current); }
      current.words.push(w); current.end = w.end;
      t += step + (/[.!?…]$/u.test(raw) ? step * .8 : 0);
      if (/[.!?…]$/u.test(raw) || i === tokens.length - 1) current = null;
    });
    for (const p of out) if (!p.words.some(w => w.emphasis)) p.words[p.words.length - 1].emphasis = true;
    return out;
  }

  async function json(src) {
    if (!src || typeof fetch !== 'function') return null;
    try { const r = await fetch(src, {cache: 'no-store'}); return r.ok ? r.json() : null; } catch (e) { return null; }
  }

  window.Stage.run({
    fonts: [`800 100px ${SANS}`],
    background: '#1a1a1c',
    layers: [],
    finish: {toneMap: 'clip', vignette: .16, grain: .035},

    async setup({W, H, U, FPS, DURATION, safe, base, plan, ...env}) {
      footage = F.create({W, H, U, FPS, DURATION, ...env}, await json(plan.broll));
      const voice = await json(plan.voice && plan.voice.words);
      const raw = voice ? (voice.phrases || []).map(p => ({start: +p.start, end: +p.end,
        words: (voice.words || []).filter(w => w.start >= p.start - .01 && w.start <= p.end + .01)
          .map(w => ({text: String(w.text), start: +w.start, end: +w.end, emphasis: !!w.emphasis}))})).filter(p => p.words.length) : [];
      const source = raw.length ? raw : demo(TITLE, DURATION);
      size = Math.round(.068 * U);
      const width = safe.width * .92, measure = text => { base.font = S.font({weight: 800, size, family: SANS}); return base.measureText(text).width; };
      const space = measure(' '), lineHeight = size * 1.18, bottom = safe.y + safe.height * .9;
      phrases = source.map((p, k) => {
        // Lines that fill the width greedily, at most two; the block sits on the lower third's baseline.
        const lines = [[]];
        let x = 0;
        for (const w of p.words) {
          const ww = measure(w.text);
          if (lines[lines.length - 1].length && x + ww > width) { lines.push([]); x = 0; }
          lines[lines.length - 1].push({...w, width: ww}); x += ww + space;
        }
        const placed = [];
        lines.forEach((line, li) => {
          const total = line.reduce((a, w) => a + w.width, 0) + space * (line.length - 1);
          let left = W / 2 - total / 2;
          const baseline = bottom - (lines.length - 1 - li) * lineHeight;
          for (const w of line) { placed.push({...w, x: left, baseline}); left += w.width + space; }
        });
        return {from: k === 0 ? 0 : Math.max(0, p.start - LEAD_FRAMES / FPS), words: placed.slice(0, MAX_WORDS), top: bottom - lines.length * lineHeight};
      });
      phrases.forEach((p, k) => { p.to = k + 1 < phrases.length ? phrases[k + 1].from : DURATION + 1; });
    },

    prepare: t => footage && footage.prepare(t),

    state(t, {W, H, FPS, DURATION}) {
      // The scene comes from the frame, not the sub-sample: every motion-blur sample of a cut frame shows the new
      // phrase (no ghost of the old one). Still a pure function of t.
      const tf = (Math.floor(t * FPS + 1e-6) + .5) / FPS;
      let k = 0;
      while (k + 1 < phrases.length && tf >= phrases[k + 1].from) k++;
      const phrase = phrases[k] || {words: [], top: H};
      const push = 1 + .03 * M.clamp(t / Math.max(DURATION, 1e-6));
      const words = phrase.words.map(w => ({w, rise: M.easing('expo.out')(M.clamp((t - w.start + .03) / RISE)),
        box: w.emphasis ? M.easing('cubic.out')(M.clamp((t - w.start) / .18)) : 0}));
      const track = [...(footage ? footage.track(t) : [[0, 0], [W, H]])];
      for (let i = 0; i < MAX_WORDS; i++) { const v = words[i]; track.push(v ? [v.w.x, v.w.baseline + (1 - v.rise) * size * .4] : [0, 0]); }
      track.push([push * W / 2, push * H / 2]);
      return {t, k, push, words, top: phrase.top, track,
        debug: {phrases: phrases.length, segment: footage && footage.segmentAt(t) ? footage.segmentAt(t).id : null}};
    },

    draw(s, {base}, {W, H, U}) {
      base.save(); base.translate(W / 2, H / 2); base.scale(s.push, s.push); base.translate(-W / 2, -H / 2);
      const shown = footage && footage.draw(base, s.t).drawn;
      if (!shown) {   // no B-roll yet: a moving field, so the piece is never a flat colour
        const g = base.createLinearGradient(0, 0, W, H);
        g.addColorStop(0, '#2a2622'); g.addColorStop(.5 + .3 * Math.sin(s.t * .6), '#4a4038'); g.addColorStop(1, '#15151a');
        base.fillStyle = g; base.fillRect(0, 0, W, H);
      }
      base.restore();
      // A gradient under the lower third: the type reads on a sky or on snow.
      const shade = base.createLinearGradient(0, s.top - size * 2, 0, H);
      shade.addColorStop(0, 'rgba(0,0,0,0)'); shade.addColorStop(1, 'rgba(0,0,0,.62)');
      base.fillStyle = shade; base.fillRect(0, s.top - size * 2, W, H);
      for (const v of s.words) {
        if (v.rise <= 0) continue;
        const {w} = v, y = w.baseline + (1 - v.rise) * size * .4;
        base.save();
        base.globalAlpha = Math.min(1, v.rise * 1.5);
        if (v.box > 0) {   // the stressed word's accent box grows from its left edge
          base.fillStyle = ACCENT;
          base.fillRect(w.x - size * .12, y - size * .86, (w.width + size * .24) * v.box, size * 1.08);
        }
        base.font = S.font({weight: 800, size, family: SANS}); base.textAlign = 'left';
        base.shadowColor = 'rgba(0,0,0,.55)'; base.shadowBlur = v.box > 0 ? 0 : size * .25; base.shadowOffsetY = size * .04;
        base.fillStyle = v.box > .5 ? INK : PAPER;
        base.fillText(w.text, w.x, y);
        base.restore();
      }
    },
  });
})();
