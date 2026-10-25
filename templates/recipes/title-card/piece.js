/* Recipe · title card, Swiss / International style. Flush left and weighted to the bottom of the frame, on a visible
   six-column grid. On frame 0 the grid lines are already drawing down; an accent rule draws across, an eyebrow types
   itself on the 12 fps grid, the title's lines rise from behind their own masks in a cascade and an italic subtitle
   settles. While it holds, an accent marker hops along the rule from column to column (stepped, like a page
   counter), the eyebrow's cursor keeps blinking and the camera pushes in slowly. The exit reverses the entrance
   faster (about 0.6×): lines drop back into their masks, the rule retracts to the right.
   Every curve is a Timeline track with After Effects influence (kit/timeline.js), so you can read and tune it like a
   Graph Editor: outInfluence low = it leaves sharp, inInfluence high = it lands soft. No light layer (paper does not
   glow) and a 'clip' tone map, so ink and accent keep their colours (vignette and grain still touch the paper).
   Times: hits 'rule', 'eyebrow', 'title', 'exit'. Guides: references/craft/curves-graph-editor.md,
   references/edit/captions-titles.md, references/create/style-atlas.md (Swiss). */
(() => {
  'use strict';
  const M = window.MotionMath, T = window.Timeline, K = window.KineticType, {SANS, SERIF} = window.Stage.FONTS;
  const PAPER = '#f2f0eb', INK = '#111111', ACCENT = '#ff5a1f', GRID = 'rgba(17,17,17,.08)';
  const TITLE = 'TITLE';
  const EYEBROW = 'CHAPTER 01';
  const SUBTITLE = 'a subtitle that adds one idea';   // '' for none
  const COLUMNS = 6;
  let lines = [], titleFont = '', size = 100, eyebrowFont = '', eyebrowSize = 50, subFont = '', subSize = 60;
  let X0 = 80, Y = {}, RULE = 600, eyebrowWidth = 0, colW = 100, HOLD = [1.2, 3.3], tl;

  window.Stage.run({
    fonts: [`800 100px ${SANS}`, `italic 400 60px ${SERIF}`, `700 50px ${SANS}`],
    background: PAPER,
    layers: ['top'],
    finish: {toneMap: 'clip', vignette: .1, grain: .03},

    setup({U, DURATION, HITS, safe, fitLines, base, hit}) {
      const ruleAt = hit('rule', 0), eyebrowAt = hit('eyebrow', .12), titleAt = hit('title', .35);
      const exitAt = Math.min(Math.max(hit('exit', DURATION - .7), titleAt + 1.1), DURATION - .5);   // keys stay in order if retimed
      X0 = safe.x; RULE = safe.width; colW = safe.width / COLUMNS;
      const fit = fitLines(TITLE, {weight: 800, family: SANS, max: Math.round(.15 * U), min: Math.round(.09 * U),
        width: safe.width * .96, height: safe.height * .42, lineHeight: 1, maxLines: 3});
      ({font: titleFont, size} = fit);
      eyebrowSize = Math.round(.045 * U); subSize = Math.round(.056 * U);
      eyebrowFont = `700 ${eyebrowSize}px ${SANS}`; subFont = `italic 400 ${subSize}px ${SERIF}`;
      base.font = eyebrowFont; base.letterSpacing = `${Math.round(eyebrowSize * .12)}px`; eyebrowWidth = base.measureText(EYEBROW).width; base.letterSpacing = '0px';
      const titleLines = fit.lines.length ? fit.lines : [TITLE];
      const blockBottom = safe.y + safe.height * .9;   // weighted to the bottom: the top of the frame is the grid's
      const subH = SUBTITLE ? subSize * 1.9 : 0;
      const lastBaseline = blockBottom - subH;
      lines = titleLines.map((text, i) => ({text, i, baseline: lastBaseline - (titleLines.length - 1 - i) * size}));
      Y.rule = lines[0].baseline - size * .98 - .04 * U;
      Y.eyebrow = Y.rule - .035 * U;
      Y.sub = lastBaseline + subSize * 1.6;
      HOLD = [titleAt + 1, exitAt];
      const back = .45;   // exits ≈ 0.6 × the entrance
      tl = T.scene({
        tracks: {
          grid: [{t: -.25, v: 0, ae: {outInfluence: 25}}, {t: .7, v: 1, ae: {inInfluence: 80}}],              // drawing on frame 0
          rise: [{t: titleAt, v: 1, ae: {outInfluence: 18}}, {t: titleAt + .75, v: 0, ae: {inInfluence: 92}},
            {t: exitAt, v: 0, ease: 'cubic.in'}, {t: exitAt + back, v: 1}],
          rule: [{t: ruleAt - .15, v: 0, ae: {outInfluence: 30}}, {t: ruleAt + .58, v: 1, ae: {inInfluence: 85}},
            {t: exitAt + .1, v: 1, ease: 'cubic.in'}, {t: exitAt + .1 + back, v: 2}],
          sub: [{t: titleAt + .5, v: 0, ease: 'cubic.out'}, {t: titleAt + 1, v: 1}, {t: exitAt, v: 1, ease: 'cubic.in'}, {t: exitAt + .3, v: 0}],
          eyebrowOut: [{t: exitAt, v: 1, ease: 'cubic.in'}, {t: exitAt + .25, v: 0}],
          push: [{t: 0, v: 1}, {t: DURATION, v: 1.04}],
        },
        markers: {eyebrow: eyebrowAt, title: titleAt, exit: exitAt},
        hits: HITS,
      });
    },

    state(t, {W, H, U}) {
      const rises = lines.map(l => tl.value('rise', t - l.i * .08));   // the cascade: each line on the same curve, later
      const rule = tl.value('rule', t), push = tl.value('push', t), grid = tl.value('grid', t);
      // The marker hops one column every 0.5 s while the card holds; each hop takes 0.18 s (stepped, not drifting).
      const hold = M.clamp((t - HOLD[0]) / .3) * M.clamp((HOLD[1] - t) / .25);
      const hops = Math.max(0, (t - HOLD[0]) / .5), hop = Math.floor(hops), into = M.easing('cubic.inOut')(M.clamp((hops - hop) / .36));
      const column = ((hop % COLUMNS) + into) % COLUMNS, markerX = X0 + column * colW;
      const blink = K.stepOf(t, 2) % 2 === 0;
      const track = [...rises.map(r => [0, r * size * 1.15]), [RULE * Math.min(1, rule), 0], [RULE * Math.max(0, rule - 1), 0],
        [0, grid * H], [markerX, hold * .02 * U], [push * W / 2, push * H / 2]];
      return {t, rises, rule, push, grid, hold, markerX, blink, sub: tl.value('sub', t), eyebrowOut: tl.value('eyebrowOut', t), track};
    },

    draw(s, {base, top}, {W, H, U}) {
      for (const ctx of [base, top]) { ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(s.push, s.push); ctx.translate(-W / 2, -H / 2); }
      base.fillStyle = GRID;
      for (let c = 0; c <= COLUMNS; c++) {   // the grid draws down from the top, column by column
        const k = M.clamp(s.grid * 1.3 - c * .05);
        if (k > 0) base.fillRect(X0 + c * colW - .001 * U, 0, Math.max(1, .002 * U), H * k);
      }
      const a = RULE * Math.max(0, s.rule - 1), b = RULE * Math.min(1, s.rule), ruleH = Math.max(2, .006 * U);
      if (b > a) { top.fillStyle = INK; top.fillRect(X0 + a, Y.rule, b - a, ruleH); }
      if (s.hold > 0) {   // the accent marker sits on the rule
        const m = .045 * U;
        top.fillStyle = ACCENT; top.globalAlpha = s.hold; top.fillRect(s.markerX, Y.rule - m * .5 * s.hold + ruleH / 2, colW, m * s.hold * .5); top.globalAlpha = 1;
      }
      const typed = K.typewriter(s.t, {at: tl.marker('eyebrow'), dur: .5, text: EYEBROW, x: X0 + eyebrowWidth / 2, y: Y.eyebrow, width: eyebrowWidth,
        height: eyebrowSize, color: ACCENT, opacity: s.eyebrowOut, cursorColor: INK, cursorWidth: Math.max(2, .005 * U)}, c => {
        if (c.kind === 'rect') { top.fillStyle = c.color; top.fillRect(c.x - c.width / 2, c.y - c.height * .75, c.width, c.height); return; }
        top.save(); top.beginPath(); top.rect(c.left, c.y - c.height * 1.2, c.fullWidth * c.reveal, c.height * 1.6); top.clip();
        top.font = eyebrowFont; top.letterSpacing = `${Math.round(eyebrowSize * .12)}px`; top.globalAlpha = c.opacity;
        top.fillStyle = c.color; top.fillText(c.text, c.left, c.y); top.restore();
      });
      const done = typed.length === 1 && typed[0].reveal >= 1;
      if (done && s.blink && s.eyebrowOut > .5) {   // the cursor keeps blinking after the eyebrow is typed
        top.fillStyle = INK; top.fillRect(X0 + eyebrowWidth + .012 * U, Y.eyebrow - eyebrowSize * .75, Math.max(2, .005 * U), eyebrowSize * .8);
      }
      top.letterSpacing = '0px';
      base.font = titleFont; base.fillStyle = INK;
      lines.forEach((l, i) => {   // each line slides inside its own mask: it appears from nothing, without a fade
        const r = s.rises[i];
        if (r >= 1) return;
        base.save(); base.beginPath(); base.rect(0, l.baseline - size * .98, W, size * 1.24); base.clip();
        base.fillText(l.text, X0, l.baseline + r * size * 1.15); base.restore();
      });
      if (SUBTITLE && s.sub > 0) {
        base.font = subFont; base.globalAlpha = s.sub; base.fillStyle = INK;
        base.fillText(SUBTITLE, X0, Y.sub + (1 - s.sub) * .02 * U); base.globalAlpha = 1;
      }
      for (const ctx of [base, top]) ctx.restore();
    },
  });
})();
