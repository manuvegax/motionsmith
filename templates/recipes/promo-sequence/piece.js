/* Recipe · promo sequence, three scenes and two transitions: editing, not only animation.
   1. HOOK on paper: one huge condensed word slams in on a spring (shake on the hit, letters boil on 12 fps).
   2. A WHIP PAN carries the cut: the camera crosses a whole frame in about 0.25 s with real motion blur (a 360°
      shutter integrated by kit/stage.js), and the statement scene arrives already moving.
   3. STATEMENT on ink: its lines rise from their masks, an accent rule sweeps under them, the camera pushes in.
   4. An IRIS grows from the end of the rule and opens the END CARD on the accent: the closing word gains weight as it
      lands (variable Archivo), a mark pops, a link types in.
   A scene counter (01 / 03) steps with every cut and a progress bar fills along the top: nothing is ever frozen.
   TITLE: "hook | statement" (the part before '|' is the hook; without '|', the first word). Set END, LINK and the
   palette. Times: hits 'hook slam', 'whip', 'statement', 'iris', 'end card'. Guides: references/edit/cutting.md,
   references/edit/transitions-atlas.md (whip pan, iris), references/craft/blur.md, references/edit/story-structures.md. */
(() => {
  'use strict';
  const M = window.MotionMath, T = window.Timeline, S = window.Stage, {SANS, MONO} = S.FONTS;
  const PAPER = '#f1efe9', INK = '#0e0e0f', ACCENT = '#ffe14d', MUTED = 'rgba(241,239,233,.62)';
  const TITLE = 'TITLE';
  const END = 'Make it move';                  // the end card's word(s)
  const LINK = 'your.link/here';               // typed under it; '' for none
  let hook = '', statement = [], hookFont = '', hookSize = 200, hookGlyphs = [], hookWidth = 0;
  let lineFont = '', lineSize = 100, endSize = 140, monoSize = 48, X0 = 80, LINES_Y = [], RULE_Y = 0, RULE_W = 600;
  let HOOK = .15, WHIP = 2.25, STATE = 2.55, IRIS = 5.45, ENDT = 5.85, tl;

  window.Stage.run({
    fonts: [`900 200px ${SANS}`, `800 100px ${SANS}`, `500 48px ${MONO}`],
    background: PAPER,
    shutter: 300,
    maxSamples: 48,
    finish: {bloomMode: 'halo', strength: .3, halation: .6, toneMap: 'shoulder', vignette: .14, grain: .03},

    setup({W, H, U, DURATION, HITS, safe, fit, fitLines, base, hit}) {
      HOOK = hit('hook slam', .15); WHIP = Math.max(hit('whip', 2.25), HOOK + .6);
      STATE = Math.max(hit('statement', 2.3), WHIP - .05); IRIS = Math.max(hit('iris', DURATION - 2.55), STATE + 1.2);
      ENDT = Math.max(hit('end card', IRIS + .4), IRIS + .2);
      const parts = TITLE.split('|').map(p => p.trim()).filter(Boolean);
      const words = TITLE.replace(/\|/g, ' ').split(/\s+/).filter(Boolean);
      hook = parts.length > 1 ? parts[0] : (words[0] || TITLE);
      const rest = parts.length > 1 ? parts.slice(1).join(' ') : words.slice(1).join(' ');
      X0 = safe.x;
      const maxHook = Math.round(.42 * U), condensed = size => S.font({weight: 900, stretch: 'condensed', size, family: SANS});
      base.font = condensed(maxHook);
      hookSize = Math.max(12, Math.floor(Math.min(maxHook, maxHook * safe.width * .96 / (base.measureText(hook).width || 1))));
      hookFont = condensed(hookSize); base.font = hookFont; hookWidth = base.measureText(hook).width;
      hookGlyphs = M.layoutGlyphs(hook, t => base.measureText(t).width);
      const fitted = fitLines(rest || hook, {weight: 800, family: SANS, max: Math.round(.16 * U), min: Math.round(.08 * U),
        width: safe.width * .94, height: safe.height * .5, lineHeight: 1.02, maxLines: 4});
      statement = fitted.lines; lineSize = fitted.size; lineFont = fitted.font;
      const blockH = statement.length * lineSize * 1.02;
      const top = safe.y + (safe.height - blockH) * .55;
      LINES_Y = statement.map((_, i) => top + (i + .8) * lineSize * 1.02);
      RULE_Y = LINES_Y[LINES_Y.length - 1] + lineSize * .45;
      base.font = lineFont; RULE_W = Math.min(safe.width * .94, Math.max(...statement.map(l => base.measureText(l).width)));
      endSize = fit(END, {weight: 900, family: SANS, max: Math.round(.16 * U), width: safe.width * .9}).size;
      monoSize = Math.round(.045 * U);
      tl = T.scene({
        tracks: {
          cam: [{t: WHIP - .14, v: 0, ease: 'expo.inOut'}, {t: WHIP + .14, v: -1}],                 // frames of travel, ×W
          rise: [{t: STATE, v: 1, ae: {outInfluence: 16}}, {t: STATE + .65, v: 0, ae: {inInfluence: 90}}],
          rule: [{t: STATE + .45, v: 0, ae: {outInfluence: 20}}, {t: STATE + 1.05, v: 1, ae: {inInfluence: 85}}],
          iris: [{t: IRIS - .05, v: 0, ease: 'power3.in'}, {t: IRIS + .38, v: 1}],
          endIn: [{t: ENDT, v: 0, ae: {outInfluence: 14}}, {t: ENDT + .6, v: 1, ae: {inInfluence: 90}}],
          push: [{t: STATE, v: 1}, {t: IRIS + .4, v: 1.05}],
          hookPush: [{t: HOOK + .3, v: 1}, {t: WHIP, v: 1.07, ease: 'sine.in'}],
          echo: [{t: HOOK + .85, v: 0, ae: {outInfluence: 18}}, {t: HOOK + 1.3, v: 1, ae: {inInfluence: 85}}],
        },
        hits: HITS,
      });
    },

    state(t, {W, H, U, DURATION, safe}) {
      const slamHit = [{time: HOOK, amplitude: 1}];
      const slam = M.spring(Math.max(0, t - HOOK + .1), {freq: 2.2, damping: .42});   // already in flight on frame 0
      const hookScale = (1.55 - .55 * slam) * tl.value('hookPush', t), shake = M.shake(t, slamHit, {px: .014 * U});
      const echo = tl.value('echo', t);
      const cam = tl.value('cam', t) * W;
      const rises = statement.map((_, i) => tl.value('rise', t - i * .07));
      const rule = tl.value('rule', t), push = tl.value('push', t), iris = tl.value('iris', t);
      const endIn = tl.value('endIn', t), pop = M.easing('back.out')(M.clamp((t - ENDT - .15) / .45));
      const typed = LINK ? M.clamp(M.posterize(t - ENDT - .5, 12) / .6) : 0;
      const scene = t < WHIP ? 0 : t < IRIS + .2 ? 1 : 2;
      const irisCenter = [X0 + RULE_W * rule, RULE_Y], irisMax = Math.hypot(Math.max(irisCenter[0], W - irisCenter[0]), Math.max(irisCenter[1], H - irisCenter[1]));
      const track = [[cam, 0], [hookWidth / 2 * hookScale, hookSize / 2 * hookScale], [shake[0], shake[1]], [echo * .05 * U, echo * .04 * U],
        ...rises.map(r => [0, r * lineSize * 1.15]), [RULE_W * rule, 0], [iris * irisMax, 0], [0, (1 - endIn) * endSize * .4],
        [pop * .06 * U, 0], [push * W / 2, push * H / 2]];
      return {t, hookScale, shake, echo, cam, rises, rule, push, iris, irisCenter, irisMax, endIn, pop, typed, scene,
        progress: M.clamp(t / DURATION), step: Math.floor(t * 12), track};
    },

    draw(s, {base, light, top}, {W, H, U, safe}) {
      // 1. HOOK on paper (until the whip has carried it out of frame)
      if (s.cam > -W) {
        base.save(); base.translate(s.cam + s.shake[0], s.shake[1]);
        base.fillStyle = PAPER; base.fillRect(0, 0, W, H);
        base.font = hookFont; base.fillStyle = INK; base.textBaseline = 'alphabetic';
        const cx = W / 2, cy = safe.y + safe.height * .5;
        base.translate(cx, cy); base.scale(s.hookScale, s.hookScale);
        if (s.echo > 0) {   // an outline echo slides out from behind the word halfway through the hold
          base.strokeStyle = INK; base.lineWidth = Math.max(2, .003 * U);
          for (let k = 3; k >= 1; k--) {
            const wob = .004 * U * Math.sin(M.posterize(s.t, 12) * 9 + k);
            base.globalAlpha = .35 * (1 - (k - 1) / 4) * s.echo;
            base.strokeText(hook, -hookWidth / 2 - k * .018 * U * s.echo + wob, hookSize * .36 - k * .014 * U * s.echo);
          }
          base.globalAlpha = 1;
        }
        hookGlyphs.forEach((g, i) => {   // letters boil a little on 12 fps: alive while the word is read
          const j = .0025 * U, dx = (window.KineticType.hash2(i, s.step) - .5) * j, dy = (window.KineticType.hash2(i + 50, s.step) - .5) * j;
          base.fillText(g.ch, -hookWidth / 2 + g.x + dx, hookSize * .36 + dy);
        });
        base.restore();
      }
      // 2. STATEMENT on ink (arrives inside the whip, from one frame to the right)
      const drawStatement = ctx => {
        ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
        ctx.save(); ctx.translate(W / 2, H / 2); ctx.scale(s.push, s.push); ctx.translate(-W / 2, -H / 2);
        ctx.font = lineFont; ctx.fillStyle = PAPER;
        statement.forEach((line, i) => {
          const r = s.rises[i];
          if (r >= 1) return;
          ctx.save(); ctx.beginPath(); ctx.rect(0, LINES_Y[i] - lineSize * .98, W, lineSize * 1.24); ctx.clip();
          ctx.fillText(line, X0, LINES_Y[i] + r * lineSize * 1.15); ctx.restore();
        });
        if (s.rule > 0) { ctx.fillStyle = ACCENT; ctx.fillRect(X0, RULE_Y, RULE_W * s.rule, Math.max(4, .012 * U)); }
        ctx.restore();
      };
      if (s.cam < 0) { base.save(); base.translate(s.cam + W, 0); drawStatement(base); base.restore(); }
      // 3. IRIS into the END CARD on the accent
      if (s.iris > 0) {
        base.save(); base.beginPath(); base.arc(s.irisCenter[0], s.irisCenter[1], s.iris * s.irisMax, 0, M.TAU); base.clip();
        base.fillStyle = ACCENT; base.fillRect(0, 0, W, H);
        const cy = safe.y + safe.height * .5;
        if (s.pop > 0) {   // the mark: a ring and a dot, popping in
          base.save(); base.translate(W / 2, cy - endSize * 1.25); base.scale(s.pop, s.pop);
          base.strokeStyle = INK; base.lineWidth = .02 * U; base.beginPath(); base.arc(0, 0, .07 * U, 0, M.TAU); base.stroke();
          base.fillStyle = INK; base.beginPath(); base.arc(0, 0, .022 * U, 0, M.TAU); base.fill(); base.restore();
        }
        if (s.endIn > 0) {   // the closing word gains weight as it lands
          base.font = S.font({weight: M.mix(300, 900, s.endIn), size: endSize, family: SANS}); base.textAlign = 'center';
          base.fillStyle = INK; base.globalAlpha = M.clamp(s.endIn * 3);
          base.fillText(END, W / 2, cy + endSize * .35 + (1 - s.endIn) * endSize * .4); base.globalAlpha = 1;
        }
        if (LINK && s.typed > 0) {
          base.font = `500 ${monoSize}px ${MONO}`; base.textAlign = 'center'; base.fillStyle = INK;
          const shown = LINK.slice(0, Math.ceil(LINK.length * s.typed));
          base.fillText(shown + (s.typed < 1 && s.step % 2 ? '_' : ''), W / 2, cy + endSize * .35 + monoSize * 2.2);
        }
        base.restore();
      }
      // On top: the scene counter steps with every cut, a progress bar fills along the top edge.
      const dark = s.scene === 1;
      top.font = `500 ${monoSize}px ${MONO}`; top.textAlign = 'left'; top.fillStyle = dark ? MUTED : 'rgba(14,14,15,.7)';
      top.fillText(`0${s.scene + 1} / 03`, safe.x, safe.y + monoSize);
      top.fillStyle = dark ? ACCENT : INK; top.fillRect(0, 0, W * s.progress, Math.max(4, .008 * U));
    },
  });
})();
