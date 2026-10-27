/* Recipe · audiogram, for podcasts, yapping and voice notes. A waveform scrolls with the real level of the voice, the
   speaker and the show sit on top, and the phrase being said fills the middle karaoke-style: the words already said in
   full colour, the ones coming at a third, the stressed word in the accent. A progress line runs along the bottom.
   Everything that moves comes from the voice, so the frame breathes when the person speaks and rests when they pause.
   Data: voice.json from scripts/voice_plan.py (words, phrases, emphasis and the per-frame "levels" of the voice).
   Without it, TITLE ("Speaker | Show") names the card and a demo voice is spread over the piece.
   Guides: references/create/niches.md (podcast), references/edit/voiceover.md, references/edit/captions-titles.md. */
(() => {
  'use strict';
  const M = window.MotionMath, S = window.Stage, {SANS, MONO} = S.FONTS;
  const BG = '#121214', CARD = '#1d1d21', INK = '#f2efe8', DIM = 'rgba(242,239,232,.33)', ACCENT = '#ff422e';
  const TITLE = 'TITLE';   // "Speaker | Show"
  const BARS = 40;         // waveform bars; each is one frame of history further back
  const DEMO = 'The thing nobody tells you is that *attention* is a muscle. And the feed is a gym that only trains the wrong one.';
  let speaker = '', show = '', phrases = [], levels = null, levelFps = 30, size = 70, nameSize = 60, showSize = 40;
  let waveY = 0, waveH = 200, textTop = 0, cardTop = 0;

  async function voice(plan) {
    const src = plan.voice && plan.voice.words;
    if (!src || typeof fetch !== 'function') return null;
    try { const r = await fetch(src, {cache: 'no-store'}); return r.ok ? r.json() : null; } catch (e) { return null; }
  }
  function demo(duration) {
    const tokens = DEMO.split(/\s+/), step = Math.min(.36, Math.max(.5, duration - 1) / tokens.length);
    let t = .2, current = null;
    const out = [];
    tokens.forEach((raw, i) => {
      const w = {text: raw.replace(/\*/g, ''), start: t, end: t + step * .8, emphasis: /^\*.+\*[.,;:!?…]*$/u.test(raw)};
      if (!current) { current = {start: t, words: []}; out.push(current); }
      current.words.push(w); current.end = w.end;
      t += step + (/[.!?…]$/u.test(raw) ? step : 0);
      if (/[.!?…]$/u.test(raw) || i === tokens.length - 1) current = null;
    });
    return out;
  }
  // A demo level: speech-like bursts that follow the demo words, so the waveform still means something.
  const demoLevel = t => phrases.some(p => p.words.some(w => t >= w.start && t <= w.end + .05))
    ? .45 + .4 * Math.abs(Math.sin(t * 23.0) * Math.sin(t * 7.3)) : .04;

  window.Stage.run({
    fonts: [`800 100px ${SANS}`, `500 50px ${MONO}`],
    background: BG,
    layers: [],
    finish: {toneMap: 'clip', vignette: .2, grain: .03},

    async setup({W, H, U, DURATION, safe, base, plan}) {
      const parts = String(TITLE).split('|').map(p => p.trim());
      speaker = parts[0] || ''; show = parts[1] || '';
      const v = await voice(plan);
      if (v) {
        const words = (v.words || []).map(w => ({text: String(w.text), start: +w.start, end: +w.end, emphasis: !!w.emphasis}));
        phrases = (v.phrases || []).map(p => ({start: +p.start, end: +p.end, words: words.filter(w => w.start >= p.start - .01 && w.start <= p.end + .01)})).filter(p => p.words.length);
        if (v.levels) { levels = v.levels.values; levelFps = v.levels.fps; }
      }
      if (!phrases.length) phrases = demo(DURATION);
      nameSize = Math.round(.06 * U); showSize = Math.round(.034 * U); size = Math.round(.066 * U);
      waveH = Math.round(.18 * U);
      // The block (card + up to four caption lines) sits a little above the middle of the safe area.
      const block = nameSize * 2.6 + showSize * 1.6 + waveH * 1.7 + size * 4.8;
      cardTop = safe.y + Math.max(0, (safe.height - block) * .42);
      waveY = cardTop + nameSize * 2.6 + showSize * 1.6 + waveH * .8;
      textTop = waveY + waveH * .9 + size;
      const width = safe.width * .9, measure = text => { base.font = S.font({weight: 800, size, family: SANS}); return base.measureText(text).width; };
      const space = measure(' ');
      for (const p of phrases) {   // lay each phrase out once: greedy lines, left-aligned like a transcript
        let x = 0, line = 0;
        for (const w of p.words) {
          w.width = measure(w.text);
          if (x > 0 && x + w.width > width) { x = 0; line++; }
          w.x = safe.x + safe.width * .05 + x; w.line = line; x += w.width + space;
        }
      }
    },

    state(t, {W, FPS, DURATION}) {
      const tf = (Math.floor(t * FPS + 1e-6) + .5) / FPS;   // the phrase from the frame: no ghost on a change
      let k = 0;
      while (k + 1 < phrases.length && tf >= phrases[k + 1].start - .05) k++;
      const level = time => {
        if (!levels) return demoLevel(time);
        const i = Math.floor(time * levelFps);
        return i >= 0 && i < levels.length ? levels[i] : 0;
      };
      const wave = Array.from({length: BARS}, (_, i) => level(t - (BARS - 1 - i) / FPS * 1.5));
      const words = (phrases[k] ? phrases[k].words : []).map(w => ({w, said: M.easing('cubic.out')(M.clamp((t - w.start + .02) / .12)),
        pop: w.emphasis ? M.impulse(t, [{time: w.start, amplitude: 1}], 10) : 0}));
      const track = wave.map((v, i) => [i, v * waveH]);
      track.push([0, M.clamp(t / DURATION) * W]);
      return {t, k, wave, words, progress: M.clamp(t / DURATION), now: level(t), track,
        debug: {phrases: phrases.length, voice: !!levels}};
    },

    draw(s, {base}, {W, H, U, safe}) {
      // The card: speaker, show, a live dot that pulses with the voice.
      base.fillStyle = CARD; base.fillRect(safe.x - U * .02, cardTop - U * .02, safe.width + U * .04, waveY + waveH - cardTop + U * .06);
      base.fillStyle = ACCENT; base.globalAlpha = .55 + .45 * s.now;
      base.beginPath(); base.arc(safe.x + nameSize * .3, cardTop + nameSize * .62, nameSize * (.16 + .06 * s.now), 0, Math.PI * 2); base.fill();
      base.globalAlpha = 1; base.textAlign = 'left';
      base.fillStyle = INK; base.font = S.font({weight: 800, size: nameSize, family: SANS});
      base.fillText(speaker, safe.x + nameSize * .75, cardTop + nameSize * 1.0);
      base.fillStyle = DIM; base.font = `500 ${showSize}px ${MONO}`;
      base.fillText(show.toUpperCase(), safe.x + nameSize * .75, cardTop + nameSize * 1.0 + showSize * 1.6);
      // The waveform: mirrored bars, the newest on the right, the loudest in the accent.
      const gap = safe.width / BARS, bw = gap * .55;
      s.wave.forEach((v, i) => {
        const h = Math.max(U * .006, v * waveH);
        base.fillStyle = v > .7 ? ACCENT : INK; base.globalAlpha = .35 + .65 * (i / BARS);
        base.fillRect(safe.x + i * gap + (gap - bw) / 2, waveY - h / 2, bw, h);
      });
      base.globalAlpha = 1;
      // The phrase, karaoke-style.
      for (const v of s.words) {
        const {w} = v, y = textTop + w.line * size * 1.2, scale = 1 + .08 * v.pop;
        base.save(); base.translate(w.x + w.width / 2, y); base.scale(scale, scale);
        base.font = S.font({weight: 800, size, family: SANS}); base.textAlign = 'center';
        base.fillStyle = v.said > .5 ? (w.emphasis ? ACCENT : INK) : DIM;
        base.globalAlpha = .33 + .67 * v.said;
        base.fillText(w.text, 0, 0);
        base.restore();
      }
      // Progress along the bottom of the safe area.
      base.fillStyle = 'rgba(242,239,232,.15)'; base.fillRect(safe.x, safe.y + safe.height - U * .01, safe.width, U * .006);
      base.fillStyle = ACCENT; base.fillRect(safe.x, safe.y + safe.height - U * .01, safe.width * s.progress, U * .006);
    },
  });
})();
