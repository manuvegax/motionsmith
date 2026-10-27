/* Recipe · B-roll story, in the editorial-collage language: footage and photos as prints on paper under a voice.
   Each shot of the B-roll timeline (scripts/broll.py assemble) lands as a print (a white border, a soft shadow, tape
   on two corners, a slight turn) on a sheet of paper with matter; the previous print stays underneath, so the story
   accumulates instead of cutting away. Above the prints, the phrase being said sets itself in mixed weights: function
   words small, the stressed word large in the accent with a red stroke drawing under it, every word landing the moment
   it is said. Clips play inside their print (kit/footage.js: trimmed to the scene, one grade for every source);
   stills move inside theirs (Ken Burns, parallax with a cut-out).
   Data: plan.broll (timeline.json) and plan.voice (voice.json, scripts/voice_plan.py). Without a timeline the prints
   are blank paper; without a voice, TITLE is spread as a demo voice (*word* = stressed).
   Guides: references/create/editorial-collage.md, references/edit/broll.md, references/edit/voiceover.md. */
(() => {
  'use strict';
  const M = window.MotionMath, S = window.Stage, F = window.Footage, Cg = window.Collage, {SANS} = S.FONTS;
  const PAPER = '#ece8de', INK = '#151412', RED = '#ff3b23', TAPE = 'rgba(232,222,196,.78)';
  const TITLE = 'TITLE';
  const SMALL = new Set('a al de del el en la las lo los y o que se un una the a an of to in on and or is it you your i we my'.split(' '));
  const LEAD_FRAMES = 2;
  let C = null, sheet = null, footage = null, shots = [], phrases = [], film = null, filmCtx = null;
  let PRINT = {x: 540, y: 1150, w: 760, h: 950};

  async function json(src) {
    if (!src || typeof fetch !== 'function') return null;
    try { const r = await fetch(src, {cache: 'no-store'}); return r.ok ? r.json() : null; } catch (e) { return null; }
  }
  function demo(title, duration) {
    const tokens = String(title).split(/\s+/).filter(Boolean), step = Math.min(.42, Math.max(.5, duration - .9) / Math.max(1, tokens.length));
    let t = .2, current = null;
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

  window.Stage.run({
    fonts: [`900 100px ${SANS}`, `750 100px ${SANS}`, `500 100px ${SANS}`],
    background: PAPER,
    layers: [],
    shutter: 270,
    finish: {toneMap: 'clip', vignette: .2, grain: .03},

    async setup(env) {
      const {W, H, U, FPS, DURATION, safe, plan} = env;
      C = Cg.create(env);
      sheet = C.paper({tone: PAPER, seed: 5});
      footage = F.create(env, await json(plan.broll));
      if (typeof document !== 'undefined' && document.createElement) {   // the footage is drawn full-frame here, then cropped into a print
        film = document.createElement('canvas'); film.width = W; film.height = H; filmCtx = film.getContext('2d');
      }
      PRINT = {x: W / 2, y: safe.y + safe.height * .64, w: safe.width * .9, h: safe.height * .58};
      const segs = footage.segments.length ? footage.segments : [{id: 's01', start: 0, end: DURATION, kind: 'gap'}];
      shots = segs.map((s, i) => ({...s, i, rot: [-.045, .03, -.02, .05, -.035][i % 5], dx: [0, -.03, .025, -.015, .02][i % 5] * W}));
      const voice = await json(plan.voice && plan.voice.words);
      const raw = voice ? (voice.phrases || []).map(p => ({start: +p.start, end: +p.end,
        words: (voice.words || []).filter(w => w.start >= p.start - .01 && w.start <= p.end + .01)
          .map(w => ({text: String(w.text), start: +w.start, end: +w.end, emphasis: !!w.emphasis}))})).filter(p => p.words.length) : [];
      const source = raw.length ? raw : demo(TITLE, DURATION);
      // Each phrase as mixed type: function words small, the stressed word as the keyword, the rest in the body weight.
      phrases = source.map((p, k) => {
        const markup = p.words.map(w => {
          const bare = w.text.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
          return w.emphasis ? `*${w.text}*` : SMALL.has(bare) ? `~${w.text}` : w.text;
        });
        const lines = [];   // two or three lines, broken at even word counts
        const per = Math.ceil(markup.length / Math.min(3, Math.max(1, Math.ceil(markup.length / 4))));
        for (let i = 0; i < markup.length; i += per) lines.push(markup.slice(i, i + per).join(' '));
        const laid = C.layoutPhrase(lines.join(' | '), {width: safe.width * .96, size: U * .125, y: safe.y + safe.height * .17});
        laid.forEach((w, i) => { w.at = p.words[i] ? p.words[i].start - .03 : p.start; });
        return {from: k === 0 ? 0 : Math.max(0, p.start - LEAD_FRAMES / FPS), words: laid};
      });
    },

    prepare: t => footage && footage.prepare(t),

    state(t, {W, H, FPS}) {
      const tf = (Math.floor(t * FPS + 1e-6) + .5) / FPS;   // scene and phrase from the frame: no ghost on a cut
      let k = 0; while (k + 1 < phrases.length && tf >= phrases[k + 1].from) k++;
      let j = 0; while (j + 1 < shots.length && tf >= shots[j + 1].start) j++;
      const land = M.easing('back.out')(M.clamp((t - shots[j].start) / .45));
      const drift = M.wiggle(t, {freq: .25, amp: W * .006, seed: 3, dims: 2});
      const key = phrases[k] ? phrases[k].words.find(w => w.kind === 'key') : null;
      const track = [[PRINT.x + drift[0], PRINT.y - (1 - land) * H * .5], [PRINT.x + PRINT.w / 2, PRINT.y + PRINT.h / 2 - (1 - land) * H * .5]];
      return {t, k, j, land, drift, key, track, debug: {shot: shots[j] && shots[j].id, phrase: k}};
    },

    draw(s, {base: ctx}, {W, H, U}) {
      const t = s.t;
      C.drawPaper(ctx, sheet, {x: s.drift[0] * .5, y: s.drift[1] * .5});
      // The print underneath (the previous shot) stays, a little darker; the new one lands on top.
      const print = (shot, landing, under) => {
        const {w, h} = PRINT, b = U * .022;
        ctx.save();
        ctx.translate(PRINT.x + shot.dx + s.drift[0], PRINT.y - (1 - landing) * H * .55 + s.drift[1]);
        ctx.rotate(shot.rot + (1 - landing) * .25);
        ctx.shadowColor = `rgba(0,0,0,${under ? .2 : .32})`; ctx.shadowBlur = U * (.03 + .05 * (1 - landing)); ctx.shadowOffsetY = U * (.015 + .04 * (1 - landing));
        ctx.fillStyle = '#f8f6f1'; ctx.fillRect(-w / 2, -h / 2, w, h);
        ctx.shadowColor = 'transparent';
        const iw = w - b * 2, ih = h - b * 2;
        if (!under && film && footage.draw(filmCtx, t).drawn) {   // the shot, cropped to the print's window
          const k = Math.max(iw / W, ih / H), sw = iw / k, sh = ih / k;
          ctx.drawImage(film, (W - sw) / 2, (H - sh) / 2, sw, sh, -w / 2 + b, -h / 2 + b, iw, ih);
        } else {
          ctx.fillStyle = under ? '#cfcac0' : '#d9d4ca'; ctx.fillRect(-w / 2 + b, -h / 2 + b, iw, ih);
        }
        if (under) { ctx.fillStyle = 'rgba(30,25,20,.18)'; ctx.fillRect(-w / 2, -h / 2, w, h); }
        ctx.fillStyle = TAPE;   // tape across two corners
        for (const [x, y, r] of [[-w / 2 + b * .5, -h / 2 + b * .5, -.7], [w / 2 - b * .5, -h / 2 + b * .5, .7]]) {
          ctx.save(); ctx.translate(x, y); ctx.rotate(r); ctx.fillRect(-U * .07, -U * .022, U * .14, U * .044); ctx.restore();
        }
        ctx.restore();
      };
      if (s.j > 0) print(shots[s.j - 1], 1, true);
      print(shots[s.j], s.land, false);
      // The phrase, mixed weights; a red stroke draws under the keyword once it is said.
      const p = phrases[s.k];
      if (p) {
        C.phrase(ctx, p.words, t, {at: p.words.map(w => w.at), ink: INK, accent: RED, dur: .4});
        if (s.key) {
          const u = M.clamp((t - s.key.at - .15) / .35);
          C.trim(ctx, [[s.key.x, s.key.y + s.key.size * .14], [s.key.x + s.key.width * .5, s.key.y + s.key.size * .2], [s.key.x + s.key.width, s.key.y + s.key.size * .12]],
            {to: M.easing('cubic.out')(u), width: s.key.size * .07, color: RED});
        }
      }
    },
  });
})();
