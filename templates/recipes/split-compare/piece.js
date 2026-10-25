/* Recipe · split compare (before / after), duotone. A headline band sits on top; under it the frame opens on BEFORE:
   strokes on slate that never sit still (they boil on a 12 fps grid). A divider whips across with a 360° shutter and
   reveals AFTER: the same marks resolved into a calm grid of ink dots on paper, with one accent point. The divider
   springs back to the middle and settles on its hit, the labels pop in at the bottom; while it holds, BEFORE keeps
   boiling, a wave crosses the AFTER grid, a light runs down the divider and the accent point pulses. To end, AFTER
   takes the whole frame: the piece finishes on the answer.
   Replace drawBefore() and drawAfter() with your two states (two designs, two numbers, two frames of a product).
   Set TITLE (the headline) and LABELS. Times: hits 'whip', 'settle', 'labels', 'exit'.
   Guides: references/edit/transitions-atlas.md (wipes), references/craft/blur.md (whips want a 360–400° shutter). */
(() => {
  'use strict';
  const M = window.MotionMath, T = window.Timeline, K = window.KineticType, {SANS, MONO} = window.Stage.FONTS;
  const PAPER = '#ece8de', INK = '#121316', SLATE = '#262a31', STROKE = 'rgba(176,184,196,.75)', ACCENT = '#12b886';
  const TITLE = 'TITLE';
  const LABELS = ['BEFORE', 'AFTER'];
  let strokes = [], dots = [], accentDot = null, title = {lines: [], size: 100, font: ''}, labelFont = '', labelSize = 50;
  let bandBottom = 400, labelY = 1400, WHIP = .6, SETTLE = 1.5, LABEL = 1.75, EXIT = 5.4, tl;

  window.Stage.run({
    fonts: [`800 100px ${SANS}`, `700 50px ${MONO}`],
    background: SLATE,
    shutter: 360,                                   // the whip is the shot's big gesture: a fuller smear
    finish: {bloomMode: 'halo', strength: .4, halation: .8, toneMap: 'shoulder', vignette: .16, grain: .03},

    setup({W, H, U, DURATION, HITS, safe, fitLines, hit}) {
      WHIP = Math.max(.25, hit('whip', .6)); SETTLE = Math.max(hit('settle', 1.5), WHIP + .45);   // keys stay in order if retimed
      LABEL = Math.max(hit('labels', SETTLE + .25), SETTLE); EXIT = Math.min(Math.max(hit('exit', DURATION - .6), SETTLE + .3), DURATION - .3);
      title = fitLines(TITLE, {weight: 800, family: SANS, max: Math.round(.1 * U), min: Math.round(.06 * U),
        width: safe.width, height: .3 * safe.height, lineHeight: 1.04, maxLines: 2});
      bandBottom = safe.y + title.lines.length * title.size * 1.04 + .05 * U;
      labelSize = Math.round(.046 * U); labelFont = `700 ${labelSize}px ${MONO}`;
      labelY = safe.y + safe.height - labelSize;
      const gy0 = bandBottom + .1 * U, gy1 = labelY - labelSize * 1.7 - .07 * U, gx0 = safe.x + .06 * U, gx1 = safe.x + safe.width - .06 * U;
      const spacing = .12 * U, cols = Math.max(3, Math.round((gx1 - gx0) / spacing) + 1), rows = Math.max(3, Math.round((gy1 - gy0) / spacing) + 1);
      const rng = M.rng(9);
      dots = []; strokes = [];
      for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
        const i = dots.length, x = M.mix(gx0, gx1, c / (cols - 1)), y = M.mix(gy0, gy1, r / (rows - 1));
        dots.push({x, y, c, r, i});
        strokes.push({x: gx0 + rng() * (gx1 - gx0), y: gy0 + rng() * (gy1 - gy0), a: rng() * Math.PI, len: (.03 + .06 * rng()) * U, spin: (rng() - .5) * 1.2, i});
      }
      accentDot = dots[Math.floor(rows * .45) * cols + Math.floor(cols * .7)];
      tl = T.scene({
        tracks: {
          divider: [{t: 0, v: 1.04, hold: true}, {t: WHIP - .2, v: 1.04, ease: 'expo.inOut'}, {t: WHIP + .18, v: -.04, ease: 'back.out'},
            {t: SETTLE, v: .5, hold: true}, {t: EXIT, v: .5, ease: 'expo.in'}, {t: EXIT + .45, v: -.04}],
          title: [{t: -.2, v: 0, ae: {outInfluence: 20}}, {t: .4, v: 1, ae: {inInfluence: 85}}],   // rising on frame 0
        },
        hits: HITS,
      });
    },

    state(t, {W, U}) {
      const held = t > SETTLE && t < EXIT ? M.clamp((t - SETTLE) / .6) * M.clamp((EXIT - t) / .3) : 0;
      const x = (tl.value('divider', t) + held * M.wiggle(t, {freq: .3, amp: .012, seed: 4})) * W;
      const settle = M.impulse(t, [{time: SETTLE, amplitude: 1}], 9);
      const labels = LABELS.map((_, i) => M.easing('back.out')(M.clamp((t - LABEL - i * .1) / .4)) * (1 - M.easing('cubic.in')(M.clamp((t - EXIT) / .3))));
      const rise = tl.value('title', t), wave = (t * .7) % 1, beam = t > SETTLE ? ((t - SETTLE) / 1.2) % 1 : -1;
      const track = [[x, 0], [0, (1 - rise) * title.size * 1.2], ...labels.map(k => [k * labelSize * 4, 0]), [0, beam * U]];
      return {t, x, settle, labels, rise, wave, beam, pulse: .5 + .5 * Math.sin(t * 4.2), track};
    },

    draw(s, {base, light, top}, {W, H, U, safe}) {
      const step = K.stepOf(s.t);                       // BEFORE boils on the 12 fps grid
      const drawBefore = () => {
        base.fillStyle = SLATE; base.fillRect(0, bandBottom, W, H - bandBottom);
        base.strokeStyle = STROKE; base.lineWidth = .007 * U; base.lineCap = 'round';
        for (const k of strokes) {
          const j = .014 * U, jx = (K.hash2(k.i, step) - .5) * j, jy = (K.hash2(k.i + 99, step) - .5) * j;
          const a = k.a + k.spin * s.t + (K.hash2(k.i + 7, step) - .5) * .35;
          base.beginPath(); base.moveTo(k.x + jx - Math.cos(a) * k.len / 2, k.y + jy - Math.sin(a) * k.len / 2);
          base.lineTo(k.x + jx + Math.cos(a) * k.len / 2, k.y + jy + Math.sin(a) * k.len / 2); base.stroke();
        }
      };
      const drawAfter = () => {
        base.fillStyle = PAPER; base.fillRect(0, bandBottom, W, H - bandBottom);
        base.fillStyle = INK;
        for (const d of dots) {   // a calm wave crosses the grid on the diagonal
          if (d === accentDot) continue;
          const phase = (d.c + d.r) / 12 - s.wave, swell = Math.exp(-((((phase % 1 + 1) % 1 - .5) / .08) ** 2));
          base.beginPath(); base.arc(d.x, d.y, .008 * U * (1 + .6 * swell), 0, M.TAU); base.fill();
        }
        top.fillStyle = ACCENT;
        top.beginPath(); top.arc(accentDot.x, accentDot.y, .02 * U * (1 + .18 * s.pulse), 0, M.TAU); top.fill();
      };
      const x = M.clamp(s.x, 0, W);
      for (const [side, paint] of [[[0, x], drawBefore], [[x, W], drawAfter]]) {
        if (side[1] - side[0] <= 0) continue;
        for (const ctx of [base, top]) { ctx.save(); ctx.beginPath(); ctx.rect(side[0], bandBottom, side[1] - side[0], H - bandBottom); ctx.clip(); }
        paint();
        for (const ctx of [base, top]) ctx.restore();
      }
      if (s.x > -.02 * W && s.x < 1.02 * W) {   // the divider: a glow that smears on the whip, a beam on a loop, a handle
        light.fillStyle = PAPER; light.globalAlpha = .85; light.fillRect(s.x - .003 * U, bandBottom, .006 * U, H - bandBottom);
        if (s.beam >= 0) {
          const by = bandBottom + s.beam * (H - bandBottom), g = light.createLinearGradient(0, by - .08 * U, 0, by + .08 * U);
          g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(.5, 'rgba(255,255,255,1)'); g.addColorStop(1, 'rgba(255,255,255,0)');
          light.globalAlpha = 1; light.fillStyle = g; light.fillRect(s.x - .006 * U, by - .08 * U, .012 * U, .16 * U);
        }
        light.globalAlpha = 1;
        const hy = (bandBottom + labelY) / 2, r = .045 * U * (1 + .12 * s.settle);
        top.save(); top.fillStyle = INK; top.beginPath(); top.arc(s.x, hy, r, 0, M.TAU); top.fill();
        top.strokeStyle = PAPER; top.lineWidth = .006 * U; top.lineJoin = 'round';
        for (const d of [-1, 1]) { top.beginPath(); top.moveTo(s.x + d * r * .18, hy - r * .35); top.lineTo(s.x + d * r * .5, hy); top.lineTo(s.x + d * r * .18, hy + r * .35); top.stroke(); }
        top.restore();
      }
      // The headline band: one colour under the whole title, so it reads over both halves.
      top.fillStyle = INK; top.fillRect(0, 0, W, bandBottom);
      top.save(); top.beginPath(); top.rect(0, safe.y - .02 * U, W, bandBottom - safe.y); top.clip();
      top.font = title.font; top.textAlign = 'center'; top.fillStyle = PAPER;
      title.lines.forEach((line, i) => top.fillText(line, W / 2, safe.y + (i + .82) * title.size * 1.04 + (1 - s.rise) * title.size * 1.3));
      top.restore();
      top.font = labelFont; top.letterSpacing = `${Math.round(labelSize * .14)}px`; top.textAlign = 'center';
      LABELS.forEach((label, i) => {   // pills that pop in at the bottom, each on its side of the divider
        const k = s.labels[i];
        if (k <= 0) return;
        const w = top.measureText(label).width + labelSize * 1.2, h = labelSize * 1.7;
        const cx = i === 0 ? Math.min(s.x - .04 * U - w / 2, W - w / 2) : Math.max(s.x + .04 * U + w / 2, w / 2);
        top.save(); top.translate(cx, labelY - h / 2); top.scale(k, k);
        top.fillStyle = i === 1 ? ACCENT : INK; top.fillRect(-w / 2, -h / 2, w, h);
        top.fillStyle = i === 1 ? INK : PAPER; top.fillText(label, labelSize * .07, labelSize * .36);
        top.restore();
      });
      top.letterSpacing = '0px';
    },
  });
})();
