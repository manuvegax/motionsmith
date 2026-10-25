/* Recipe · data reveal, infographic look. A number rolls up on real odometer wheels (each column carries when the one
   below passes 9, so the units blur while the tens click over), a gauge arc fills in the light layer and lights the
   ticks it passes, and the value lands exactly on its hit with a punch and a flash ring. The hold stays alive with
   an ambient budget: a glint with a tail travels round the arc, a scan ring breathes out of the gauge every 1.2 s,
   the lit ticks shimmer and the camera breathes. The label sits under the number and the source at the bottom of
   the safe area, readable: a number on screen always says where it comes from.
   Data honesty: the count never overshoots the true value; only the scale punch moves on the hit. The accent is a
   calm teal, not an alarm red. Set VALUE, SUFFIX, MAX (the gauge's full circle), the label (TITLE) and SOURCE.
   Times: hits 'count starts' and 'value lands'.
   Guides: references/create/scene-recipes.md, references/craft/blur.md (the units wheel is the fastest edge). */
(() => {
  'use strict';
  const M = window.MotionMath, {SANS} = window.Stage.FONTS;
  const INK = '#eef3f8', MUTED = '#9db0c6', ACCENT = '#2ee6c5', BG = '#0c1424';
  const TITLE = 'TITLE';                       // the label under the number
  const VALUE = 73, MAX = 100, SUFFIX = '%';   // whole numbers; the gauge fills VALUE / MAX of the circle
  const SOURCE = 'Source: your data, month year';
  const TICKS = 60;
  let digits = 1, cell = 100, digitFont = '', suffixFont = '', label = [], labelFont = '', labelSize = 70, sourceFont = '', sourceSize = 50;
  let CX = 540, CY = 800, R = 300, numberWidth = 0, suffixWidth = 0, cellH = 200, START = .3, LAND = 1.9;

  window.Stage.run({
    fonts: [`800 100px ${SANS}`, `700 60px ${SANS}`, `600 50px ${SANS}`],
    background: BG,
    finish: {bloomMode: 'halo', strength: .5, halation: .9, toneMap: 'shoulder', vignette: .22, grain: .025},

    setup({W, U, safe, fitLines, base, hit}) {
      START = hit('count starts', .3); LAND = hit('value lands', 1.9);
      digits = String(Math.round(VALUE)).length;
      R = Math.min(.34 * U, safe.height * .25); CX = W / 2; CY = safe.y + safe.height * .36;
      const numberSize = Math.round(R * 1.1 / Math.max(1, (digits + .55 * SUFFIX.length) * .58));   // fills ~60 % of the ring
      cellH = numberSize;
      digitFont = `800 ${numberSize}px ${SANS}`; suffixFont = `800 ${Math.round(numberSize * .42)}px ${SANS}`;
      base.font = digitFont; cell = Math.max(...'0123456789'.split('').map(d => base.measureText(d).width));   // tabular cells
      base.font = suffixFont; suffixWidth = SUFFIX ? base.measureText(SUFFIX).width : 0;
      numberWidth = digits * cell + suffixWidth;
      const fit = fitLines(TITLE, {weight: 700, family: SANS, max: Math.round(.075 * U), min: Math.round(.05 * U),
        width: safe.width * .9, maxLines: 2, lineHeight: 1.12});
      label = fit.lines; labelSize = fit.size; labelFont = fit.font;
      sourceSize = Math.round(.045 * U); sourceFont = `600 ${sourceSize}px ${SANS}`;
    },

    state(t, {W, H, U, DURATION}) {
      const u = M.clamp((t - START) / (LAND - START));
      const count = VALUE * M.easing('power3.out')(u);
      // Odometer: the units wheel turns with the count; a higher wheel only moves while the one below goes 9 → 0.
      const wheels = Array.from({length: digits}, (_, k) => k === 0 ? count
        : Math.floor(count / 10 ** k) + M.clamp((count % 10 ** k) - (10 ** k - 1), 0, 1));
      const punch = M.impulse(t, [{time: LAND, amplitude: 1}], 8);
      const fill = count / MAX, flash = M.clamp((t - LAND) / .7);
      const glint = t > LAND ? ((t - LAND) / 1.4) % 1 : -1;                  // travels round the filled arc, on a loop
      const scan = t > LAND + .3 ? ((t - LAND - .3) / 1.2) % 1 : -1;          // a ring breathing out of the gauge
      const intro = M.easing('cubic.out')(M.clamp((t + .12) / .45));          // the gauge track is drawing on frame 0
      const exit = M.easing('cubic.in')(M.clamp((t - (DURATION - .45)) / .45));
      const push = 1 + .035 * M.clamp(t / DURATION), drift = M.wiggle(t, {freq: .15, amp: .012 * U, dims: 2, seed: 2});
      const glintAt = glint >= 0 ? -Math.PI / 2 + M.TAU * fill * glint : -Math.PI / 2;
      const track = [...wheels.map(p => [0, p * cellH]), [R * Math.cos(fill * M.TAU), R * Math.sin(fill * M.TAU)],
        [R * punch * .06, 0], [R * Math.cos(glintAt), R * Math.sin(glintAt)], [R * (1 + .5 * M.easing('expo.out')(flash)), 0],
        [R * (1.05 + .5 * Math.max(0, scan)), 0], [drift[0] + push * W / 2, drift[1] + push * H / 2]];
      return {count, wheels, punch, fill, flash, glint, glintAt, scan, intro, exit, push, drift, t,
        labelIn: M.easing('cubic.out')(M.clamp((t - LAND + .2) / .45)), track};
    },

    draw(s, {base, light, top}, {W, H, U, safe}) {
      const a0 = -Math.PI / 2, scale = 1 + .06 * s.punch, alpha = 1 - s.exit;
      for (const ctx of [base, light, top]) {   // camera breath: a slow push and a drift
        ctx.save(); ctx.globalAlpha = alpha;
        ctx.translate(W / 2 + s.drift[0], H / 2 + s.drift[1]); ctx.scale(s.push, s.push); ctx.translate(-W / 2, -H / 2);
      }
      base.lineCap = light.lineCap = 'round';
      base.strokeStyle = 'rgba(238,243,248,.1)'; base.lineWidth = .028 * U;   // the empty gauge
      base.beginPath(); base.arc(CX, CY, R, a0, a0 + M.TAU * s.intro); base.stroke();
      for (let i = 0; i < TICKS; i++) {   // ticks: faint on base, lit on the light layer once the arc has passed them
        const f = i / TICKS, ang = a0 + f * M.TAU, r0 = R * 1.12, r1 = R * (i % 5 ? 1.16 : 1.2);
        if (f > s.intro) break;
        const lit = f <= s.fill, ctx = lit ? light : base;
        const shimmer = lit ? .5 + .5 * Math.sin(s.t * 5 - i * .45) : 0;
        ctx.strokeStyle = lit ? ACCENT : 'rgba(238,243,248,.22)'; ctx.lineWidth = .004 * U;
        ctx.globalAlpha = alpha * (lit ? .45 + .4 * shimmer * (1 - s.flash * .5) + .5 * s.punch : 1);
        ctx.beginPath(); ctx.moveTo(CX + r0 * Math.cos(ang), CY + r0 * Math.sin(ang)); ctx.lineTo(CX + r1 * Math.cos(ang), CY + r1 * Math.sin(ang)); ctx.stroke();
      }
      light.globalAlpha = alpha;
      if (s.fill > 0) {
        light.strokeStyle = ACCENT; light.lineWidth = .028 * U;
        light.beginPath(); light.arc(CX, CY, R, a0, a0 + M.TAU * s.fill); light.stroke();
      }
      if (s.glint >= 0) {   // a head and a short tail, drawn as a few fading dots behind it
        for (let k = 0; k < 6; k++) {
          const g = s.glintAt - k * .035;
          if (g < a0) break;
          light.globalAlpha = alpha * (1 - k / 6);
          light.fillStyle = 'rgba(230,255,250,.95)'; light.beginPath(); light.arc(CX + R * Math.cos(g), CY + R * Math.sin(g), .016 * U * (1 - k * .1), 0, M.TAU); light.fill();
        }
      }
      if (s.scan >= 0) {
        light.globalAlpha = alpha * .35 * (1 - s.scan) ** 2; light.strokeStyle = ACCENT; light.lineWidth = .004 * U;
        light.beginPath(); light.arc(CX, CY, R * (1.05 + .5 * s.scan), 0, M.TAU); light.stroke();
      }
      if (s.flash > 0 && s.flash < 1) {
        light.globalAlpha = alpha; light.strokeStyle = `rgba(238,243,248,${.5 * (1 - s.flash) ** 2})`; light.lineWidth = .006 * U;
        light.beginPath(); light.arc(CX, CY, R * (1 + .5 * M.easing('expo.out')(s.flash)), 0, M.TAU); light.stroke();
      }
      base.save(); base.translate(CX, CY); base.scale(scale, scale); base.translate(-CX, -CY);
      base.font = digitFont; base.textAlign = 'center'; base.fillStyle = INK;
      const left = CX - numberWidth / 2, baseline = CY + cellH * .35;
      for (let k = 0; k < digits; k++) {   // column k from the right; leading zeros fade in only once reached
        const p = s.wheels[k], x = left + (digits - 1 - k) * cell + cell / 2, d = Math.floor(p), f = p - d;
        const shown = k === 0 ? 1 : M.clamp(p);
        if (shown <= 0) continue;
        base.save(); base.beginPath(); base.rect(x - cell / 2, baseline - cellH * .82, cell, cellH * .9); base.clip();
        base.globalAlpha = alpha * shown;
        base.fillText(String(((d % 10) + 10) % 10), x, baseline - f * cellH);
        base.fillText(String((((d + 1) % 10) + 10) % 10), x, baseline + (1 - f) * cellH);
        base.restore();
      }
      if (SUFFIX) { base.font = suffixFont; base.textAlign = 'left'; base.fillText(SUFFIX, left + digits * cell + .01 * U, baseline - cellH * .32); }
      base.restore();
      base.font = labelFont; base.textAlign = 'center'; base.fillStyle = INK;
      label.forEach((line, i) => {
        base.globalAlpha = alpha * s.labelIn;
        base.fillText(line, CX, CY + R * 1.32 + (i + .8) * labelSize * 1.12 + (1 - s.labelIn) * .02 * U);
      });
      base.font = sourceFont; base.fillStyle = MUTED; base.globalAlpha = alpha * s.labelIn;
      base.fillText(SOURCE, CX, safe.y + safe.height - .25 * sourceSize);
      for (const ctx of [base, light, top]) ctx.restore();
    },
  });
})();
