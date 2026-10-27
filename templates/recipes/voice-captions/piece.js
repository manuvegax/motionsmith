/* Recipe · voice captions, the voice is the clock. Each spoken phrase is a scene: its words land the moment they are
   said (rising, from a thin to a black weight), the stressed word lands in the accent with a pop and an underline
   sweep, and every cut swaps paper and ink with a small camera punch, so the picture changes when the voice turns.
   Behind the words a giant outline of the scene's stressed word slides, and the camera keeps a slow push: no frame is
   frozen while someone is speaking.
   Data: voice.json, written by scripts/voice_plan.py (words, phrases and emphasis measured on the real voice). Without
   it, TITLE is spread over the piece as a demo voice: *word* marks the stressed word, a full stop ends a phrase.
   Times live in voice.json and plan.json (the emphasis hits); nothing is retyped here.
   Guides: references/edit/voiceover.md, references/craft/kinetic-typography.md, references/edit/captions-titles.md. */
(() => {
  'use strict';
  const M = window.MotionMath, S = window.Stage, {SANS} = S.FONTS;
  const PAPER = '#efeee8', INK = '#101110', ACCENT = '#ff422e';
  const TITLE = 'TITLE';
  const THIN = 250, BLACK = 900;     // a word enters thin and settles black (Archivo's weight axis)
  const RISE = .14, SETTLE = .24;    // seconds a word takes to rise in, and to reach its full weight
  const LEAD_FRAMES = 2;             // the picture cuts this many frames before the phrase's first word (as voice_plan)
  const MAX_WORDS = 24;              // the most words one scene can show (the motion-blur track has a fixed length)
  let scenes = [], marqueeFont = '';

  /* TITLE → a demo voice: even speech at ~2.6 words per second, phrases on full stops, *word* stressed. */
  function demo(title, duration) {
    const tokens = String(title).split(/\s+/).filter(Boolean);
    const span = Math.max(.5, duration - .9), step = Math.min(.42, span / Math.max(1, tokens.length));
    let t = .15;
    const words = [], phrases = [];
    let current = null;
    tokens.forEach((raw, i) => {
      const text = raw.replace(/\*/g, '');
      const word = {text, start: t, end: t + step * .85, emphasis: /^\*.+\*[.,;:!?…]*$/u.test(raw)};
      words.push(word);
      if (!current) { current = {start: t, end: t, words: []}; phrases.push(current); }
      current.words.push(word); current.end = word.end;
      t += step + (/[.!?…]$/u.test(raw) ? step * .8 : 0);
      if (/[.!?…]$/u.test(raw) || i === tokens.length - 1) current = null;
    });
    for (const p of phrases) if (!p.words.some(w => w.emphasis)) p.words[p.words.length - 1].emphasis = true;
    return phrases;
  }

  function fromVoice(data) {
    const words = (data.words || []).map(w => ({text: String(w.text), start: Number(w.start), end: Number(w.end), emphasis: Boolean(w.emphasis)}));
    return (data.phrases || []).map(p => ({start: Number(p.start), end: Number(p.end),
      words: words.filter(w => w.start >= Number(p.start) - .01 && w.start <= Number(p.end) + .01)})).filter(p => p.words.length);
  }

  /* Even lines that never end on a weak word (de, que, y, the…) and never leave one short word alone: the fewest lines
     that fit, then dynamic programming over the breaks. widths are at size 1. */
  const WEAK = new Set('a al ante con de del el en entre la las le lo los mi mis o para pero por que se sin sobre su sus te tu tus un una unos unas y e ni the an and or but of to in on at by for with from as my your'.split(' '));
  function balance(texts, widths, space, maxWidth) {
    const n = texts.length, lineWidth = (i, j) => widths.slice(i, j).reduce((a, b) => a + b, 0) + space * (j - i - 1);
    const total = lineWidth(0, n), target = total / Math.max(1, Math.ceil(total / maxWidth));
    const best = [0], back = [0];
    for (let j = 1; j <= n; j++) {
      best[j] = Infinity;
      for (let i = j - 1; i >= 0; i--) {
        const w = lineWidth(i, j);
        if (w > maxWidth && j - i > 1) break;
        let cost = ((w - target) / maxWidth) ** 2 * 100 + 40 + (w > maxWidth ? 1e4 : 0);
        if (j < n && WEAK.has(texts[j - 1].toLowerCase().replace(/[^\p{L}]/gu, ''))) cost += 90;
        if (j - i === 1 && n > 1 && texts[i].length < 8) cost += 70;
        if (best[i] + cost < best[j]) { best[j] = best[i] + cost; back[j] = i; }
      }
    }
    const lines = [];
    for (let j = n; j > 0; j = back[j]) lines.unshift([back[j], j]);
    return {lines, width: Math.max(...lines.map(([i, j]) => lineWidth(i, j)))};
  }

  window.Stage.run({
    fonts: [`${BLACK} 100px ${SANS}`, `${THIN} 100px ${SANS}`],
    background: PAPER,
    layers: [],                                   // paper and ink do not glow: a clip tone map keeps the exact colours
    finish: {toneMap: 'clip', vignette: .1, grain: .03},

    async setup({W, H, U, FPS, DURATION, safe, base, plan}) {
      let phrases = null;
      const file = plan.voice && plan.voice.words;   // voice_plan.py writes plan.voice: only then is there a voice.json
      if (file && typeof fetch === 'function') {
        try { const r = await fetch(file, {cache: 'no-store'}); if (r.ok) phrases = fromVoice(await r.json()); } catch (e) { phrases = null; }
      }
      if (!phrases || !phrases.length) phrases = demo(TITLE, DURATION);
      const maxWidth = safe.width * .9, maxHeight = safe.height * .6;
      const measure = (text, size) => { base.font = S.font({weight: BLACK, size, family: SANS}); return base.measureText(text).width; };
      const layouts = phrases.map(p => {
        const texts = p.words.map(w => w.text), widths = texts.map(t => measure(t, 100) / 100), space = measure(' ', 100) / 100;
        // The largest size, up to .15 U, at which the balanced lines fit the width and four lines' height.
        let size = Math.round(.15 * U);
        for (; size > Math.round(.05 * U); size--) {
          const b = balance(texts, widths, space, maxWidth / size);
          if (b.width * size <= maxWidth && b.lines.length <= 4 && b.lines.length * size * 1.04 <= maxHeight) break;
        }
        return {texts, widths, space, fitted: size};
      });
      // One size for the whole piece reads as one voice: the smallest fitted size, but never under .1 U; a phrase
      // that cannot fit at it takes its own smaller size.
      const common = Math.max(Math.round(.1 * U), Math.min(...layouts.map(l => l.fitted)));
      scenes = phrases.map((p, k) => {
        const l = layouts[k], size = Math.min(common, l.fitted), lineHeight = size * 1.04;
        const {lines} = balance(l.texts, l.widths, l.space, maxWidth / size);
        let y = safe.y + safe.height * .42 - lines.length * lineHeight / 2;
        const placed = [];
        lines.forEach(([i, j], li) => {
          const lineWidth = (l.widths.slice(i, j).reduce((a, b) => a + b, 0) + l.space * (j - i - 1)) * size;
          let x = W / 2 - lineWidth / 2;
          y += lineHeight;
          for (let n = i; n < j; n++) {
            const w = p.words[n], wordWidth = l.widths[n] * size;
            placed.push({...w, x, width: wordWidth, baseline: y - size * .2, line: li});
            x += wordWidth + l.space * size;
          }
        });
        const stressed = placed.find(w => w.emphasis) || placed[placed.length - 1];
        const from = k === 0 ? 0 : Math.max(0, p.start - LEAD_FRAMES / FPS);
        return {k, from, size, words: placed.slice(0, MAX_WORDS), stressed: stressed ? stressed.text.replace(/[^\p{L}\p{N}]/gu, '').toUpperCase() : ''};
      });
      scenes.forEach((s, k) => { s.to = k + 1 < scenes.length ? scenes[k + 1].from : DURATION + 1; });
      marqueeFont = `${BLACK} ${Math.round(.34 * U)}px ${SANS}`;
    },

    state(t, {W, H, U, FPS, DURATION}) {
      // The scene comes from the frame, not the sub-sample: every motion-blur sample of a cut frame shows the new
      // phrase and ground (no ghost of the old one). Still a pure function of t.
      const tf = (Math.floor(t * FPS + 1e-6) + .5) / FPS;
      let k = 0;
      while (k + 1 < scenes.length && tf >= scenes[k + 1].from) k++;
      const scene = scenes[k] || {words: [], from: 0, size: 100, stressed: ''};
      const since = t - scene.from;
      const punch = k > 0 ? .045 * (1 - M.easing('expo.out')(M.clamp(since / .35))) : 0;
      const push = 1 + .025 * M.clamp(t / Math.max(DURATION, 1e-6)) + punch;
      const marqueeX = -.09 * U * t;
      const words = scene.words.map(w => {
        const rise = M.easing('expo.out')(M.clamp((t - w.start + .04) / RISE));
        const weight = M.mix(THIN, BLACK, M.easing('cubic.out')(M.clamp((t - w.start + .04) / SETTLE)));
        const pop = w.emphasis ? M.impulse(t, [{time: w.start, amplitude: 1}], 9) : 0;
        const sweep = w.emphasis ? M.easing('cubic.out')(M.clamp((t - w.start - .05) / .28)) : 0;
        return {w, rise, weight, pop, sweep, dy: (1 - rise) * .32 * scene.size};
      });
      const track = [];
      for (let i = 0; i < MAX_WORDS; i++) {
        const v = words[i];
        track.push(v ? [v.w.x + v.w.width / 2, v.w.baseline + v.dy] : [0, 0]);
      }
      track.push([marqueeX, 0], [push * W / 2, push * H / 2]);
      return {t, k, push, words, marqueeX, dark: k % 2 === 1, track,
        debug: {scenes: scenes.length, scene: k, said: words.filter(v => v.rise > 0).map(v => v.w.text).join(' ')}};
    },

    draw(s, {base}, {W, H, U}) {
      const scene = scenes[s.k];
      const bg = s.dark ? INK : PAPER, fg = s.dark ? PAPER : INK;
      base.fillStyle = bg; base.fillRect(0, 0, W, H);
      if (!scene) return;
      // The living layer: a giant outline of the scene's stressed word sliding behind the words.
      if (scene.stressed) {
        base.save(); base.font = marqueeFont; base.textBaseline = 'middle'; base.globalAlpha = .09;
        base.strokeStyle = fg; base.lineWidth = .0035 * U;
        const unit = base.measureText(`${scene.stressed} · `).width || 1;
        let x = ((s.marqueeX % unit) + unit) % unit - unit;
        for (; x < W; x += unit) base.strokeText(`${scene.stressed} · `, x, H * .8);
        base.restore();
      }
      base.save(); base.translate(W / 2, H / 2); base.scale(s.push, s.push); base.translate(-W / 2, -H / 2);
      for (const v of s.words) {
        if (v.rise <= 0) continue;
        const {w} = v, cx = w.x + w.width / 2, scale = 1 + .1 * v.pop;
        base.save();
        base.translate(cx, w.baseline + v.dy); base.scale(scale, scale);
        base.globalAlpha = Math.min(1, v.rise * 1.6);
        base.font = S.font({weight: v.weight, size: scene.size, family: SANS});
        base.textAlign = 'center'; base.fillStyle = w.emphasis ? ACCENT : fg;
        base.fillText(w.text, 0, 0);
        if (v.sweep > 0) {   // the underline sweeps under the stressed word as it is said
          base.fillStyle = ACCENT;
          base.fillRect(-w.width / 2, scene.size * .12, w.width * v.sweep, Math.max(3, scene.size * .07));
        }
        base.restore();
      }
      base.restore();
    },
  });
})();
