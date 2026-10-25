/* Recipe · logo reveal, minimal glow. The pieces of a mark drift in frame, accelerate on arcs into place and lock on
   one hit (scale punch, flash, shock ring, a small shake), then recoil and settle instead of stopping dead; a glint
   crosses the mark, the wordmark tracks in from wide letter spacing and a tagline settles. The end card holds alive:
   the glint comes back every 1.6 s, the accent piece breathes, dust drifts through the light and the camera keeps a
   slow push.
   Make it yours: paste your logo's SVG paths into MARK (viewBox 0 0 100 100, one entry per piece that should fly),
   set the palette and the font. Times come from the plan's hits ('mark locks', 'glint', 'wordmark'): retime
   plan.json and the soundtrack moves with the picture. Plumbing: kit/stage.js. Guide: references/create/scene-recipes.md. */
(() => {
  'use strict';
  const M = window.MotionMath, T = window.Timeline;
  const PAPER = '#efeee8', ACCENT = '#ff422e', BG = '#101112';
  const FAMILY = window.Stage.FONTS.SANS, WEIGHT = 800;
  const GLINT_EVERY = 1.6;                      // seconds between sheens while the end card holds
  const TITLE = 'TITLE';                        // the wordmark
  const TAGLINE = 'MADE BY CODE';               // '' for none
  // One entry per piece. layer: 'base' (picture), 'light' (glows and blooms) or 'top' (exact colour, after the tone
  // map). from: start offset in mark sizes. spin: start rotation (rad). pivot: the piece's own centre (mark units).
  const MARK = [
    {d: 'M50 4A40 40 0 1 1 49.99 4ZM50 17A27 27 0 1 0 50.01 17Z', fill: PAPER, layer: 'base', from: [-.78, .62], spin: -2.4, delay: 0, pivot: [50, 44]},
    {d: 'M43 37H57V51H43Z', fill: ACCENT, layer: 'top', from: [.72, -.86], spin: 3.1, delay: .08, pivot: [50, 44]},
    {d: 'M24 92H76V99H24Z', fill: PAPER, layer: 'base', from: [.8, .78], spin: .9, delay: .16, pivot: [50, 95.5]},
  ];
  let pieces = [], whole, glyphs = [], naturalWidth = 0, wordFont = '', wordSize = 100, tagFont = '', tagSize = 48, dust = [];
  let S = 400, CX = 540, CY = 800, WORD_Y = 1200, LOCK = .85, GLINT = 1.2, WORD = 1.45, tl;

  window.Stage.run({
    fonts: [`${WEIGHT} 100px ${FAMILY}`, `600 40px ${FAMILY}`],
    background: BG,
    finish: {bloomMode: 'halo', strength: .5, halation: 1.1, toneMap: 'shoulder', vignette: .25, grain: .025},

    setup({W, U, DURATION, HITS, safe, fit, base, hit}) {
      LOCK = hit('mark locks', .85); GLINT = hit('glint', LOCK + .35); WORD = hit('wordmark', LOCK + .6);
      pieces = MARK.map(p => ({...p, path: new Path2D(p.d)}));
      whole = new Path2D(); pieces.forEach(p => whole.addPath(p.path));
      S = Math.min(.42 * U, safe.height * .42);
      CX = W / 2; CY = safe.y + safe.height * .4;
      ({font: wordFont, size: wordSize, width: naturalWidth} = fit(TITLE, {weight: WEIGHT, family: FAMILY,
        max: Math.round(.13 * U), width: safe.width * .74}));
      base.font = wordFont;
      glyphs = M.layoutGlyphs(TITLE, s => base.measureText(s).width);
      WORD_Y = CY + S * .62 + wordSize * .9;
      tagSize = Math.round(.045 * U); tagFont = `600 ${tagSize}px ${FAMILY}`;
      const rng = M.rng(21);
      dust = Array.from({length: 26}, (_, i) => ({x: rng(), y: rng(), r: (.0015 + .003 * rng()) * U, speed: .01 + .02 * rng(), phase: rng() * 6.28, i}));
      tl = T.scene({
        tracks: {
          spacing: [{t: WORD, v: .55, ae: {outInfluence: 12}}, {t: WORD + .9, v: .06, ae: {inInfluence: 88}}],   // em: wide → tight
          tag: [{t: WORD + .45, v: 0, ease: 'cubic.out'}, {t: WORD + .95, v: 1}],
          push: [{t: 0, v: 1}, {t: DURATION, v: 1.035}],                                            // living layer: slow push
        },
        hits: HITS,
      });
    },

    state(t, {U}) {
      const push = tl.value('push', t), lockHit = [{time: LOCK, amplitude: 1}];
      const punch = M.impulse(t, lockHit, 9), markScale = push * (1 + .07 * punch);
      const shake = M.shake(t, lockHit, {px: .009 * U});
      const after = Math.max(0, t - LOCK), recoil = t > LOCK ? Math.exp(-after * 7) * Math.sin(after * 22) : 0;   // overshoot, back, settle
      const flights = pieces.map((p, i) => {
        const start = p.delay - .25, u = M.clamp((t - start) / (LOCK - start));
        const k = M.easing('power2.in')(u);                         // accelerates into the lock: the energy lands on the hit
        const drift = M.wiggle(t, {freq: .7, amp: .05 * S, dims: 2, seed: 11 + i}).map(v => v * (1 - k));
        const pos = M.arcPoint(k, [p.from[0] * S, p.from[1] * S], [0, 0], i % 2 ? -.18 : .18);
        const len = Math.hypot(p.from[0], p.from[1]) || 1, over = .045 * S * recoil;   // past the lock, along the arrival
        const breathe = p.layer === 'top' ? 1 + .05 * Math.sin(Math.max(0, t - LOCK - .4) * 3.6) * M.clamp((t - LOCK - .4) / .4) : 1;
        return {x: pos[0] + drift[0] - p.from[0] / len * over, y: pos[1] + drift[1] - p.from[1] / len * over,
          angle: p.spin * (1 - k) - .06 * Math.sign(p.spin) * recoil, scale: (.6 + .4 * k) * breathe};
      });
      // The glint: first on its hit, then every GLINT_EVERY seconds while the card holds.
      const since = t - GLINT, glint = since < 0 ? -1 : M.easing('sine.inOut')(M.clamp((since % GLINT_EVERY) / .75)) * 1.9 - .45;
      const glintX = CX + (glint * 140 - 70) * S / 100 * markScale;
      const ring = M.clamp((t - LOCK) / .6), shock = t >= LOCK ? {r: S * (.55 + 1.2 * M.easing('expo.out')(ring)), a: (1 - ring) ** 2} : null;
      const spacing = tl.value('spacing', t) * wordSize;
      const letters = glyphs.map((g, i) => M.easing('cubic.out')(M.clamp((t - WORD - M.stagger(i, glyphs.length, {each: .03, from: 'center'})) / .35)));
      const lineWidth = naturalWidth + spacing * (glyphs.length - 1);
      const track = [
        ...flights.flatMap((f, i) => {
          const c = [CX + f.x * markScale, CY + f.y * markScale], r = .45 * S * f.scale * markScale;
          return [c, [c[0] + r * Math.cos(f.angle + i), c[1] + r * Math.sin(f.angle + i)]];   // centre and a point on the rim
        }),
        [CX - lineWidth / 2, 0], [CX + lineWidth / 2, 0], [shock ? shock.r : 0, 0], [glint > -.45 && glint < 1.45 ? glintX : 0, 0],
        [push * CX, push * CY],
      ];
      const close = M.clamp((tl.value('spacing', t) - .06) / (.55 - .06));   // 1 = wide and thin, 0 = tight and heavy
      return {t, markScale, punch, shake, flights, shock, spacing, letters, lineWidth, weight: M.mix(WEIGHT, 300, close), tag: tl.value('tag', t), glint, track};
    },

    draw(s, {base, light, top}, {W, H, U}) {
      const layers = {base, light, top};
      const t0 = [CX + s.shake[0], CY + s.shake[1]];
      const glow = light.createRadialGradient(t0[0], t0[1], 0, t0[0], t0[1], .7 * U);
      glow.addColorStop(0, `rgba(255,66,46,${.07 + .1 * s.punch})`); glow.addColorStop(1, 'rgba(255,66,46,0)');
      light.fillStyle = glow; light.fillRect(0, 0, W, H);
      for (const d of dust) {   // ambient: motes rising slowly through the light, twinkling
        const y = ((d.y - d.speed * s.t) % 1 + 1) % 1, a = .25 + .25 * Math.sin(s.t * 2.2 + d.phase);
        light.globalAlpha = a; light.fillStyle = PAPER;
        light.beginPath(); light.arc(d.x * W + .01 * U * Math.sin(s.t * .8 + d.i), y * H, d.r, 0, Math.PI * 2); light.fill();
      }
      light.globalAlpha = 1;
      if (s.shock && s.shock.a > 0) {
        light.strokeStyle = `rgba(239,238,232,${.55 * s.shock.a})`; light.lineWidth = .006 * U;
        light.beginPath(); light.arc(t0[0], t0[1], s.shock.r, 0, Math.PI * 2); light.stroke();
      }
      const unit = S / 100;
      pieces.forEach((p, i) => {
        const f = s.flights[i];
        for (const ctx of [layers[p.layer], s.punch > .02 && p.layer !== 'light' ? light : null]) {
          if (!ctx) continue;
          ctx.save();
          ctx.translate(t0[0] + f.x * s.markScale, t0[1] + f.y * s.markScale);
          ctx.scale(unit * s.markScale, unit * s.markScale);
          ctx.translate(p.pivot[0] - 50, p.pivot[1] - 50);
          ctx.rotate(f.angle); ctx.scale(f.scale, f.scale);
          ctx.translate(-p.pivot[0], -p.pivot[1]);
          ctx.globalAlpha = ctx === light && p.layer !== 'light' ? .85 * Math.min(1, s.punch) : 1;   // the flash on the lock
          ctx.fillStyle = p.fill; ctx.fill(p.path);
          ctx.restore();
        }
      });
      if (s.glint > -.4 && s.glint < 1.4) {   // a sheen clipped to the mark, on the light layer so it blooms
        light.save();
        light.translate(t0[0] - 50 * unit * s.markScale, t0[1] - 50 * unit * s.markScale);
        light.scale(unit * s.markScale, unit * s.markScale);
        light.clip(whole);
        light.transform(1, 0, -.45, 1, 0, 0);
        const gx = s.glint * 140 - 20, band = light.createLinearGradient(gx - 16, 0, gx + 16, 0);
        band.addColorStop(0, 'rgba(255,255,255,0)'); band.addColorStop(.5, 'rgba(255,255,255,.9)'); band.addColorStop(1, 'rgba(255,255,255,0)');
        light.fillStyle = band; light.fillRect(-60, -10, 260, 130);
        light.restore();
      }
      base.save(); base.font = window.Stage.font({weight: s.weight, size: wordSize, family: FAMILY}); base.fillStyle = PAPER;   // variable weight
      const x0 = CX - s.lineWidth / 2 + s.shake[0];
      glyphs.forEach((g, i) => {
        if (s.letters[i] <= 0) return;
        base.globalAlpha = s.letters[i];
        base.fillText(g.ch, x0 + g.x + i * s.spacing, WORD_Y + (1 - s.letters[i]) * .04 * U + s.shake[1]);
      });
      if (TAGLINE && s.tag > 0) {
        base.font = tagFont; base.letterSpacing = `${Math.round(.012 * U)}px`; base.textAlign = 'center';
        base.globalAlpha = s.tag * .78;
        base.fillText(TAGLINE, CX + s.shake[0], WORD_Y + wordSize * .5 + tagSize * 1.4 + (1 - s.tag) * .02 * U);
      }
      base.restore();
    },
  });
})();
