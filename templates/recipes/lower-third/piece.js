/* Recipe · lower third (name and role), clean broadcast look. On frame 0 the accent bar is already growing; the name
   panel wipes out from behind it with the name rising inside its mask, the role panel follows a beat later. While it
   holds, an overlay keeps an ambient budget, not accents: a light pulse runs down the bar, a progress line under the
   role fills with the time on screen, and the "footage" drifts. The exit wipes everything back into the bar faster
   than it came (about 0.6× the entrance).
   The backdrop is a placeholder for footage (soft shapes and a slow push) so legibility can be judged: set
   BACKDROP = false for a flat background, and see references/produce/overlays-alpha.md to render with transparency.
   Set the name (TITLE), ROLE and the palette. Times: hits 'bar in', 'name in', 'out'.
   Guides: references/edit/captions-titles.md (lower thirds), references/edit/formats-platforms.md (safe areas). */
(() => {
  'use strict';
  const M = window.MotionMath, T = window.Timeline, {SANS, MONO} = window.Stage.FONTS;
  const PANEL = '#f6f5f1', INK = '#101114', ACCENT = '#ffcc1f', BG = '#1a2129';
  const TITLE = 'TITLE';                         // the name
  const ROLE = 'ROLE · ORGANISATION';
  const BACKDROP = true;
  let nameFont = '', roleFont = '', nameSize = 90, roleSize = 54, nameWidth = 0, roleWidth = 0;
  let X = 80, Y = 1300, PAD = 30, BAR = 22, nameH = 130, roleH = 100, blobs = [], HOLD = [1, 4], tl;

  window.Stage.run({
    fonts: [`800 100px ${SANS}`, `600 50px ${MONO}`],
    background: BG,
    finish: {bloomMode: 'halo', strength: .35, halation: .8, toneMap: 'shoulder', vignette: .18, grain: .03},

    setup({W, H, U, DURATION, HITS, safe, fit, base, hit}) {
      const barIn = hit('bar in', .12), nameIn = Math.max(hit('name in', .4), barIn + .1);   // keys stay in order if retimed
      const out = Math.min(Math.max(hit('out', DURATION - .9), nameIn + .9), DURATION - .5);
      PAD = .028 * U; BAR = .02 * U; X = safe.x + .01 * U;
      const room = safe.width * .9 - BAR - 2 * PAD;
      ({font: nameFont, size: nameSize, width: nameWidth} = fit(TITLE, {weight: 800, family: SANS, max: Math.round(.085 * U), width: room}));
      ({font: roleFont, size: roleSize} = fit(ROLE, {weight: 600, family: MONO, max: Math.round(.048 * U), width: room}));
      base.font = roleFont; base.letterSpacing = `${Math.round(roleSize * .08)}px`; roleWidth = base.measureText(ROLE).width; base.letterSpacing = '0px';
      nameH = nameSize * 1.42; roleH = roleSize * 1.8;
      Y = safe.y + safe.height - .02 * U - nameH - roleH;   // the block sits on the bottom of the safe area
      HOLD = [nameIn + .75, out];
      const rng = M.rng(5);
      blobs = Array.from({length: 7}, (_, i) => ({x: rng() * W, y: rng() * H, r: (.25 + .35 * rng()) * U, hue: i % 3, seed: i}));
      tl = T.scene({
        tracks: {
          bar: [{t: barIn - .2, v: 0, ae: {outInfluence: 20}}, {t: barIn + .28, v: 1, ae: {inInfluence: 85}},   // growing on frame 0
            {t: out + .22, v: 1, ease: 'cubic.in'}, {t: out + .45, v: 0}],
          name: [{t: nameIn, v: 0, ae: {outInfluence: 15}}, {t: nameIn + .5, v: 1, ae: {inInfluence: 90}},
            {t: out, v: 1, ease: 'cubic.in'}, {t: out + .3, v: 0}],
          role: [{t: nameIn + .14, v: 0, ae: {outInfluence: 15}}, {t: nameIn + .64, v: 1, ae: {inInfluence: 90}},
            {t: out - .05, v: 1, ease: 'cubic.in'}, {t: out + .25, v: 0}],
          push: [{t: 0, v: 1}, {t: DURATION, v: 1.05}],
        },
        hits: HITS,
      });
    },

    state(t, {U}) {
      const bar = tl.value('bar', t), name = tl.value('name', t), role = tl.value('role', t);
      const nameW = nameWidth + 2 * PAD, roleW = roleWidth + 2 * PAD;
      const drift = blobs.map(b => M.wiggle(t, {freq: .08, amp: .14 * U, dims: 2, seed: b.seed}));
      const progress = M.clamp((t - HOLD[0]) / Math.max(.1, HOLD[1] - HOLD[0])) * Math.min(1, role * 1.2);
      const pulse = t > HOLD[0] - .3 ? ((t - HOLD[0] + .3) / 1.1) % 1 : -1;   // a light running down the bar, on a loop
      const barH = (nameH + roleH) * bar, push = tl.value('push', t);
      const track = [[0, barH], [name * nameW, 0], [role * roleW, 0], [0, (1 - name) * nameSize * 1.2], [0, (1 - role) * roleSize * 1.6],
        [progress * roleW, 0], [0, pulse * (nameH + roleH)], ...drift.map(d => [d[0] * push, d[1] * push])];
      return {t, bar, name, role, nameW, roleW, barH, drift, progress, pulse, push, track};
    },

    draw(s, {base, light, top}, {W, H, U}) {
      if (BACKDROP) {
        base.save(); base.translate(W / 2, H / 2); base.scale(s.push, s.push); base.translate(-W / 2, -H / 2);
        blobs.forEach((b, i) => {
          const x = b.x + s.drift[i][0], y = b.y + s.drift[i][1], g = base.createRadialGradient(x, y, 0, x, y, b.r);
          const c = ['70,96,120', '128,96,80', '60,72,96'][b.hue];
          g.addColorStop(0, `rgba(${c},.6)`); g.addColorStop(1, `rgba(${c},0)`);
          base.fillStyle = g; base.fillRect(0, 0, W, H);
        });
        base.restore();
        const shade = base.createLinearGradient(0, H * .55, 0, H);   // footage usually needs this under a lower third
        shade.addColorStop(0, 'rgba(0,0,0,0)'); shade.addColorStop(1, 'rgba(0,0,0,.45)');
        base.fillStyle = shade; base.fillRect(0, 0, W, H);
      }
      const x0 = X + BAR, bottom = Y + nameH + roleH;
      if (s.bar > 0) {   // grows upward from the bottom; its exact colour sits on the top layer, its glow on the light layer
        top.fillStyle = ACCENT; top.fillRect(X, bottom - s.barH, BAR, s.barH);
        light.globalAlpha = .35 * s.bar; light.fillStyle = ACCENT; light.fillRect(X, bottom - s.barH, BAR, s.barH);
        if (s.pulse >= 0) {
          const py = Y + s.pulse * (nameH + roleH), g = light.createLinearGradient(0, py - .05 * U, 0, py + .05 * U);
          g.addColorStop(0, 'rgba(255,240,200,0)'); g.addColorStop(.5, 'rgba(255,240,200,.9)'); g.addColorStop(1, 'rgba(255,240,200,0)');
          const y0 = Math.max(bottom - s.barH, py - .05 * U), y1 = Math.min(bottom, py + .05 * U);
          light.globalAlpha = .8 * s.bar; light.fillStyle = g; if (y1 > y0) light.fillRect(X, y0, BAR, y1 - y0);
        }
        light.globalAlpha = 1;
      }
      if (s.name > 0) {   // the panel wipes out from behind the bar; the name rises inside the same mask
        base.save(); base.beginPath(); base.rect(x0, Y, s.nameW * s.name, nameH); base.clip();
        base.fillStyle = PANEL; base.fillRect(x0, Y, s.nameW, nameH);
        base.font = nameFont; base.fillStyle = INK;
        base.fillText(TITLE, x0 + PAD, Y + nameH * .71 + (1 - s.name) * nameSize * 1.2);
        base.restore();
      }
      if (s.role > 0) {
        base.save(); base.beginPath(); base.rect(x0, Y + nameH, s.roleW * s.role, roleH); base.clip();
        base.fillStyle = INK; base.fillRect(x0, Y + nameH, s.roleW, roleH);
        base.font = roleFont; base.letterSpacing = `${Math.round(roleSize * .08)}px`; base.fillStyle = PANEL;
        base.fillText(ROLE, x0 + PAD, Y + nameH + roleH * .66 + (1 - s.role) * roleSize * 1.6);
        base.restore();
        if (s.progress > 0) { top.fillStyle = ACCENT; top.fillRect(x0, bottom - .006 * U, s.roleW * s.progress, .006 * U); }
      }
    },
  });
})();
