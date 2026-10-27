/* Recipe · editorial collage, the documentary motion-graphics language of After Effects: paper with matter, a
   monumental figure out of focus behind a phrase of mixed weights, a zoom through the red keyword into a macro shot of
   a printed page (depth of field, a marker sweeping one line, the camera pulling back to the headline), a whip pan to a
   ribbon that draws on and a pinned card that drops with its list, and a cut to black where a phone stacks
   notifications that switch off one by one under the closing line. Every transition has a carrier: the keyword's red
   becomes the page, the whip carries the energy, the hit cuts to black.
   Data: data.json (copied by new_piece.py): numeral, phrase, document {kicker, headline, highlight}, card {title,
   items}, notifications [{title, body}], ending. Markup in phrases: '|' breaks a line, *word* is the keyword, ~word is
   small. Times: hits 'phrase', 'zoom', 'marker', 'whip', 'card', 'black', 'end'.
   Kit: kit/collage.js (references/create/editorial-collage.md). */
(() => {
  'use strict';
  const M = window.MotionMath, S = window.Stage, Cg = window.Collage, {SANS, SERIF, MONO} = S.FONTS;
  const PAPER = '#ece8de', INK = '#151412', RED = '#ff3b23', GREY = '#a9a59d', NIGHT = '#0b0b0c';
  const TITLE = 'TITLE';
  const RIBBON = (W, H) => [[W * .95, -H * .02], [W * .62, H * .16], [W * .22, H * .42], [W * .72, H * .62], [W * .38, H * .86], [-W * .1, H * 1.04]];
  const SAMPLE = {
    numeral: '70',
    phrase: '~Of ~what ~you ~see, | *70 %* | ~you ~did ~not ~choose.',
    document: {kicker: 'The attention economy', headline: 'Who decides what you see',
      highlight: 'What the eye sees first, it keeps.'},
    card: {title: 'Attention', items: ['No pause', 'No bottom', 'No real choice']},
    notifications: [{title: 'Feed', body: '24 new posts for you'}, {title: 'Messages', body: 'You have 3 unread'},
      {title: 'Streak', body: 'Do not lose your 41 days'}, {title: 'Live', body: 'Someone you follow is live'}],
    ending: '~Take ~it | *back.*'};
  let C = null, data = SAMPLE, sheet = null, nightSheet = null, cardSheet = null, page = null, phrase1 = [], ending = [];
  let T = {phrase: .25, zoom: 2.35, marker: 3.5, whip: 6.1, card: 6.15, black: 9.1, end: 10.4};

  async function load(plan) {
    if (!plan.data || typeof fetch !== 'function') return null;
    try { const r = await fetch(plan.data, {cache: 'no-store'}); return r.ok ? r.json() : null; } catch (e) { return null; }
  }

  window.Stage.run({
    fonts: [`900 100px ${SANS}`, `500 100px ${SANS}`, `italic 300 100px ${SERIF}`, `800 100px ${SERIF}`, `400 100px ${SERIF}`, `500 40px ${MONO}`],
    background: PAPER,
    layers: [],
    shutter: 270,
    maxSamples: 40,
    finish: {toneMap: 'clip', vignette: .2, grain: .028},

    async setup(env) {
      const {W, H, U, DURATION, safe, hit, plan} = env;
      data = {...SAMPLE, ...((await load(plan)) || {})};
      for (const k of Object.keys(T)) T[k] = hit(k, T[k]);
      C = Cg.create(env);
      sheet = C.paper({tone: PAPER, seed: 3});
      nightSheet = C.paper({tone: NIGHT, grain: .04, blotch: .03, fibres: 0, edge: .4, seed: 9});
      cardSheet = C.paper({tone: '#f4f1ea', width: 800, height: 1000, seed: 4, edge: .1});
      page = C.document({kicker: data.document.kicker, headline: data.document.headline, highlight: data.document.highlight, width: 2400});
      phrase1 = C.layoutPhrase(data.phrase, {width: safe.width * .96, size: U * .15, y: safe.y + safe.height * .5});
      ending = C.layoutPhrase(data.ending, {width: safe.width * .9, size: U * .13, y: safe.y + safe.height * .2});
    },

    state(t, {W, H, U, FPS, DURATION}) {
      const tf = (Math.floor(t * FPS + 1e-6) + .5) / FPS;   // the scene from the frame: no ghost across a cut
      const scene = tf < T.zoom + .4 ? 0 : tf < T.whip + .12 ? 1 : tf < T.black ? 2 : 3;
      const key = phrase1.find(w => w.kind === 'key') || {x: W / 2, y: H / 2, width: 0, size: 0};
      const keyC = [key.x + key.width / 2, key.y - key.size * .35];
      // 1. zoom through the keyword: expo-in scale around it until red fills the frame
      const zoomU = M.clamp((t - T.zoom) / .4), zoom = 1 + 22 * M.easing('expo.in')(zoomU);
      const push1 = 1 + .05 * M.clamp(t / T.zoom);
      // 2. the page: macro (scale .95) tracking along the line, then a pull back to .36 that shows the headline
      const s2 = t - (T.zoom + .4);
      const pull = M.easing('cubic.inOut')(M.clamp((s2 - 1.9) / 1.4));
      const pageScale = M.mix(.95, .36, pull) * (1 + .03 * M.clamp(s2 / 3));
      const travel = M.easing('sine.inOut')(M.clamp(s2 / 2.2));
      const flash = 1 - M.clamp(s2 / .22);
      // the whip: camera crosses a frame to the left in .3 s
      const whipU = M.clamp((t - (T.whip - .15)) / .3), whip = M.easing('expo.inOut')(whipU);
      // 3. card scene
      const s3 = t - T.card;
      const ribbon = M.easing('cubic.inOut')(M.clamp((t - (T.whip - .3)) / .9));
      const drop = M.easing('back.out')(M.clamp(s3 / .55));
      // 4. black: the phone rises, notifications stack then switch off, the ending glows
      const s4 = t - T.black;
      const rise = M.easing('expo.out')(M.clamp(s4 / .7));
      const track = [[keyC[0] + (keyC[0] - W / 2) * (zoom - 1) * .02, keyC[1]], [W * zoom * .01, 0], [W * whip, 0], [0, H * (1 - drop) * .3], [0, H * (1 - rise) * .5]];
      return {t, scene, keyC, zoom, zoomU, push1, pageScale, travel, pull, flash, whip, ribbon, drop, s2, s3, s4, rise, track,
        debug: {scene, highlightLine: page ? page.highlightLine : -1}};
    },

    draw(s, {base: ctx}, {W, H, U, safe}) {
      const t = s.t;
      if (s.scene === 0) {   // paper, the monumental figure, the phrase
        ctx.save();
        ctx.translate(s.keyC[0], s.keyC[1]); ctx.scale(s.zoom * s.push1, s.zoom * s.push1); ctx.translate(-s.keyC[0], -s.keyC[1]);
        C.drawPaper(ctx, sheet, {x: M.wiggle(t, {freq: .3, amp: U * .01, seed: 2})});
        ctx.strokeStyle = 'rgba(20,20,18,.06)'; ctx.lineWidth = 1;   // a faint layout grid: the page is designed
        for (let x = safe.x; x <= safe.x + safe.width + 1; x += safe.width / 6) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
        const focus = M.clamp((t - T.phrase - .9) / 1.2);
        C.numeral(ctx, data.numeral, {x: W * .56 + M.wiggle(t, {freq: .2, amp: U * .02, seed: 5}), y: H * .47, size: U * 1.25,
          blur: M.mix(22, 7, M.easing('cubic.inOut')(focus)), alpha: .55, color: '#2a2724'});
        C.phrase(ctx, phrase1, t, {at: phrase1.map((w, i) => T.phrase + i * .11 + (w.kind === 'key' ? .25 : 0)), ink: INK, accent: RED});
        ctx.restore();
        if (s.zoomU > .55) { ctx.fillStyle = RED; ctx.globalAlpha = M.clamp((s.zoomU - .55) / .45); ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
        return;
      }
      if (s.scene === 1) {   // the macro shot of the page, the marker, the pull back; it whips out to the left
        ctx.save(); ctx.translate(-W * s.whip, 0);
        ctx.fillStyle = '#2b2824'; ctx.fillRect(0, 0, W, H);
        const hl = page.lines && page.highlightLine >= 0 ? page.lines[page.highlightLine] : null;
        const fx = hl ? M.mix(page.hx + page.hw * M.mix(.1, .75, s.travel), page.width / 2, s.pull) : undefined;
        C.drawDocument(ctx, page, {cx: W * .5, cy: H * M.mix(.5, .4, s.pull), scale: s.pageScale, rot: M.mix(-.07, -.02, s.pull),
          dof: M.mix(80, 10, s.pull), highlight: M.clamp((t - T.marker) / .8), marker: 'rgba(255,59,35,.62)', focusX: fx,
          focus: hl ? M.mix(hl.y - hl.size * .35, page.headY, s.pull) : undefined});
        ctx.restore();
        if (s.flash > 0) { ctx.fillStyle = RED; ctx.globalAlpha = s.flash; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1; }
        if (s.whip > 0) {   // the next scene enters from the right during the whip, its ribbon already drawing
          ctx.save(); ctx.translate(W * (1 - s.whip), 0); C.drawPaper(ctx, sheet, {});
          C.ribbon(ctx, RIBBON(W, H), {width: U * .14, color: GREY, to: s.ribbon, shadow: .5}); ctx.restore();
        }
        return;
      }
      if (s.scene === 2) {   // the ribbon and the pinned card
        C.drawPaper(ctx, sheet, {x: -U * .02 * s.s3});
        C.ribbon(ctx, RIBBON(W, H), {width: U * .14, color: GREY, to: s.ribbon, shadow: .5});
        const items = data.card.items || [];
        C.card(ctx, {x: W * .52, y: H * .47 - (1 - s.drop) * H * .35, w: U * .74, h: U * .94, rot: -.03 + (1 - s.drop) * .12, lift: M.mix(1.4, .45, s.drop),
          fill: '#8f8d89', texture: cardSheet, content: (g, w, h) => {
            g.fillStyle = '#fbfaf6'; g.font = `800 ${Math.round(w * .17)}px ${SANS}`; g.textAlign = 'center';
            g.fillText(data.card.title, w / 2, h * .32, w * .86);
            g.fillRect(w * .14, h * .38, w * .72 * M.easing('cubic.out')(M.clamp((s.s3 - .35) / .4)), Math.max(2, w * .012));
            items.forEach((item, i) => {
              const u = M.easing('expo.out')(M.clamp((s.s3 - .6 - i * .28) / .4));
              if (u <= 0) return;
              const y = h * (.53 + i * .13);
              g.save(); g.globalAlpha = u; g.translate((1 - u) * w * .06, 0);
              g.strokeStyle = '#fbfaf6'; g.lineWidth = w * .012;
              g.beginPath(); g.arc(w * .2, y - w * .03, w * .035, 0, Math.PI * 2); g.stroke();   // an icon: a crossed circle
              g.beginPath(); g.moveTo(w * .175, y - w * .055); g.lineTo(w * .225, y - w * .005); g.stroke();
              g.fillStyle = '#fbfaf6'; g.font = `600 ${Math.round(w * .075)}px ${SANS}`; g.textAlign = 'left';
              g.fillText(item, w * .29, y);
              g.restore();
            });
          }});
        return;
      }
      // 4. the black scene
      C.drawPaper(ctx, nightSheet, {});
      const glow = ctx.createRadialGradient(W / 2, H * .62, 0, W / 2, H * .62, U * .8);
      glow.addColorStop(0, `rgba(255,59,35,${.18 * s.rise})`); glow.addColorStop(1, 'rgba(255,59,35,0)');
      ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
      const list = data.notifications || [];
      C.phone(ctx, {x: W / 2, y: H * .66 + (1 - s.rise) * H * .6, h: U * 1.25, rot: -.04, lift: 1, screen: (g, w, h) => {
        g.fillStyle = '#f2f2f2'; g.font = `200 ${Math.round(w * .2)}px ${SANS}`; g.textAlign = 'center';
        g.fillText('21:47', w / 2, h * .2);
        list.forEach((n, i) => {
          const inn = M.easing('back.out')(M.clamp((s.s4 - .35 - i * .22) / .4));
          const off = M.clamp((s.s4 - 2.0 - (list.length - 1 - i) * .18) / .25);   // they switch off, last first
          if (inn <= 0 || off >= 1) return;
          C.notification(g, w * .05 + (1 - inn) * w * .4, h * .3 + i * w * .22, w * .9, {title: n.title, body: n.body, time: 'now', alpha: inn * (1 - off), tint: i % 2 ? '#3a8bff' : RED});
        });
      }});
      C.phrase(ctx, ending, t, {at: ending.map((w, i) => T.end + i * .12), ink: '#f2efe8', accent: RED, glow: 1});
    },
  });
})();
