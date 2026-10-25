/* Motionsmith starter piece.
   A minimal piece made by code that already does what is non-negotiable (SKILL.md → Essential craft). The render
   plumbing lives in kit/stage.js: the capture contract (motionConfig, motionReady, seek), real motion blur by
   sub-samples (samples ≥ px/3 from the fastest tracked point), light in linear HDR with a 'halo' bloom, and a `top`
   layer composited after the tone map so the brand colour comes back exact. This file only says what is on screen:
   - everything is a function of t: state(t) keeps nothing between calls, the same t gives the same frame;
   - beats come from the `hits` of plan.json, the same list the soundtrack uses (references/craft/rhythm-sync.md §3);
   - positions are fractions of the frame (U = the short side), so any format from new_piece.py works.
   Change the scene in state() and draw(); keep `track` honest so the blur follows what moves. Guides: references/00-index.md. */
(() => {
  'use strict';
  const M = window.MotionMath;
  const ACCENT = '#ff422e', PAPER = '#efeee8', BG = '#121214';
  const FONT_FAMILY = window.Stage.FONTS.SANS;              // system stack; replace with the piece's real font (@font-face)
  const FONT_WEIGHT = 800;
  const TITLE = 'TITLE';
  let GLYPHS = [], TITLE_WIDTH = 0, FONT = '';

  window.Stage.run({
    fonts: [`${FONT_WEIGHT} 200px ${FONT_FAMILY}`],
    background: BG,
    shutter: 270,                                          // 180–300° by default, 360–400° on whips
    lightGain: 3,                                          // the light layer is worth more than 1: that is what makes it bloom
    finish: {bloomMode: 'halo', strength: .45, halation: 1.2, toneMap: 'shoulder', vignette: .2, grain: .02},

    setup({W, U, safe, fit, base}) {
      // Centred on the frame (like the ring) and inside the safe area: usable width is twice the shorter side.
      const fitWidth = .97 * 2 * Math.min(W / 2 - safe.x, safe.x + safe.width - W / 2);   // 3 % margin for ink overhang
      ({font: FONT, width: TITLE_WIDTH} = fit(TITLE, {weight: FONT_WEIGHT, family: FONT_FAMILY, max: Math.round(.185 * U), width: fitWidth}));
      base.font = FONT;
      GLYPHS = M.layoutGlyphs(TITLE, text => base.measureText(text).width);
    },

    /* The scene at instant t. It depends only on t and the plan's hits. */
    state(t, {W, H, U, DURATION, HITS}) {
      const ringIn = M.clamp((t - .3) / .55);
      const ringPos = M.arcPoint(M.easing('cubic.out')(ringIn), [-.15 * W, .78 * H], [W / 2, .4271 * H], .12);   // lands on an arc
      const ringScale = M.easing('back.out')(M.clamp((t - .3) / .6)) * (1 + .08 * M.impulse(t, HITS, 9));        // overshoot and hit
      const exitAt = DURATION - .7, rise = .065 * U;
      const letters = GLYPHS.map((_, i, all) => {
        const start = 1 + M.stagger(i, all.length, {each: .04, from: 'center'});                // cascade from the centre
        const enter = M.easing('cubic.out')(M.clamp((t - start) / .45));
        const leave = M.easing('cubic.in')(M.clamp((t - exitAt - M.stagger(i, all.length, {each: .015})) / .32));   // exit ≈ 0.7 × entrance
        return {enter, leave, y: (1 - enter) * rise - leave * rise * .7};
      });
      const bar = M.easing('cubic.out')(M.clamp((t - 1.45) / .5)) * (1 - M.easing('cubic.in')(M.clamp((t - exitAt) / .3)));
      const drift = M.wiggle(t, {freq: .18, amp: .13 * U, octaves: 2, dims: 2, seed: 7});      // living layer: the background never stops
      const radius = .213 * U * ringScale;
      const track = [ringPos, [ringPos[0] + radius, ringPos[1]],                              // the ring moves and scales
        ...letters.map((l, i) => [GLYPHS[i] ? GLYPHS[i].x : 0, l.y]), [.389 * U * bar / 2, 0]];
      return {ringPos, ringScale, letters, bar, drift, track};
    },

    draw(s, {base: b, light: l, top}, {W, H, U}) {
      const gx = W / 2 + s.drift[0], gy = .573 * H + s.drift[1], glow = l.createRadialGradient(gx, gy, 0, gx, gy, .65 * U);
      glow.addColorStop(0, 'rgba(255,66,46,.10)'); glow.addColorStop(1, 'rgba(255,66,46,0)');
      l.fillStyle = glow; l.fillRect(0, 0, W, H);
      if (s.ringScale > 0) {   // the ring is light (× lightGain and the tone map): it comes out lighter than the accent, on purpose
        l.save(); l.translate(s.ringPos[0], s.ringPos[1]); l.scale(s.ringScale, s.ringScale);
        l.strokeStyle = ACCENT; l.lineWidth = .024 * U; l.beginPath(); l.arc(0, 0, .213 * U, 0, Math.PI * 2); l.stroke(); l.restore();
      }
      b.save(); b.font = FONT; b.fillStyle = PAPER;
      const x0 = (W - TITLE_WIDTH) / 2, y0 = .651 * H;
      GLYPHS.forEach((g, i) => {                                 // each grapheme at its measured x (keeps kerning)
        const {enter, leave, y} = s.letters[i], alpha = enter * (1 - leave);
        if (alpha <= 0) return;                                  // the letter does not exist before its start
        b.globalAlpha = alpha;
        b.fillText(g.ch, x0 + g.x, y0 + y);
      });
      b.restore();
      // After the tone map: the exact accent, because it never goes through the curve.
      if (s.bar > 0) { const w = .389 * U * s.bar; top.fillStyle = ACCENT; top.fillRect((W - w) / 2, .6823 * H, w, .013 * U); }
    },
  });
})();
