/* Recipe · editorial collage, built the After Effects way: four precomps on a film, layers keyed in the graph editor
   (fast out, long settle; overshoot keys; offsets of a few frames between layers), parenting, a 2.5D camera with a rack
   focus, and transitions that overlap two precomps.
     1. FIGURE   3D camera: the phrase on the focus plane, a monumental figure 600 px behind it; the camera dollies in
                 and racks focus from the figure to the phrase as its words land one by one, the keyword last.
     2. PAGE     a printed page in macro: the camera tracks along the line, a marker sweeps it, then pulls back to the
                 headline (depth of field follows the focus line).
     3. CARD     a ribbon draws on; a pinned card drops with an overshoot; its title, rule and items are its children
                 (parenting), each keyed with its own offset.
     4. PHONE    a cut to black on the hit: the phone rises, its notifications (children of the phone) slide in and
                 switch off in turn, and the closing line lands with a red glow.
   Transitions: zoom through the keyword with a two-frame red flash, a whip pan, a hard cut on the beat.
   Data: data.json (numeral, phrase, document {kicker, headline, highlight}, card {title, items}, notifications,
   ending). Phrase markup: '|' breaks a line, *word* or *several words* is the keyword, ~word is small.
   Kit: kit/comp.js (the AE model), kit/collage.js (the devices). Guide: references/craft/keyframes-and-cuts.md. */
(() => {
  'use strict';
  const S = window.Stage, A = window.Comp, Cg = window.Collage, {SANS, SERIF, MONO} = S.FONTS;
  const k = A.k, V = A.value;
  const PAPER = '#ece8de', INK = '#151412', RED = '#ff3b23', GREY = '#a9a59d', NIGHT = '#0b0b0c', DESK = '#2b2824';
  const TITLE = 'TITLE';
  const SAMPLE = {
    numeral: '70',
    phrase: '~Of ~what ~you ~see, | *70 %* | ~you ~did ~not ~choose.',
    document: {kicker: 'The attention economy', headline: 'Who decides what you see', highlight: 'What the eye sees first, it keeps.'},
    card: {title: 'Attention', items: ['No pause', 'No bottom', 'No real choice']},
    notifications: [{title: 'Feed', body: '24 new posts for you'}, {title: 'Messages', body: 'You have 3 unread'},
      {title: 'Streak', body: 'Do not lose your 41 days'}, {title: 'Live', body: 'Someone you follow is live'}],
    ending: '~Take ~it | *back.*'};
  const F = 1 / 30;   // a frame at 30 fps: offsets between layers are counted in frames, as in AE
  let film = null, hits = {};

  async function load(plan) {
    if (!plan.data || typeof fetch !== 'function') return null;
    try { const r = await fetch(plan.data, {cache: 'no-store'}); return r.ok ? r.json() : null; } catch (e) { return null; }
  }

  /* Each word of a phrase becomes a layer: it rises in with an overshoot key and fades up fast; the keyword lands
     last, from 135 % with a small counter-rotation. Offsets: 3 frames between words, 6 more before the keyword. */
  function wordLayers(words, t0, {ink = INK, accent = RED, glow = 0, threeD = false, z = 0, tag = 'w'} = {}) {
    let t = t0;
    return words.map((w, i) => {
      if (w.kind === 'key') t += 6 * F;
      const at = t; t += 3 * F;
      const x = w.x + w.width / 2, y = w.y, rise = w.size * .55;
      const pos = threeD ? A.overshoot(at, [x, y + rise, z], at + .34, [x, y, z], {amount: .07}) : A.overshoot(at, [x, y + rise], at + .34, [x, y], {amount: .07});
      return A.layer({name: `${tag}${i}`, threeD, position: pos,
        opacity: k([at, 0, 'snap'], [at + .12, 100]),
        scale: w.kind === 'key' ? A.overshoot(at, 135, at + .4, 100, {amount: .05}) : 100,
        rotation: w.kind === 'key' ? k([at, -5, 'snap'], [at + .45, 0]) : 0,
        blur: k([at, 12, 'snap'], [at + .22, 0]),
        draw: g => {
          g.font = w.font; g.textAlign = 'center'; g.fillStyle = w.kind === 'key' ? accent : ink;
          g.letterSpacing = w.kind === 'key' ? `${(-w.size * .02).toFixed(1)}px` : '0px';
          if (glow && w.kind === 'key') { g.shadowColor = accent; g.shadowBlur = w.size * .45; }
          g.globalAlpha *= w.kind === 'small' ? .82 : 1;
          g.fillText(w.text, 0, 0);
        }});
    });
  }

  window.Stage.run({
    fonts: [`900 100px ${SANS}`, `750 100px ${SANS}`, `500 100px ${SANS}`, `italic 300 100px ${SERIF}`, `800 100px ${SERIF}`, `400 100px ${SERIF}`, `500 40px ${MONO}`],
    background: '#000',
    layers: [],
    shutter: 180,
    maxSamples: 32,
    finish: {toneMap: 'clip', vignette: .2, grain: .028},

    async setup(env) {
      const {W, H, U, DURATION, safe, plan} = env;
      const data = {...SAMPLE, ...((await load(plan)) || {})};
      const C = Cg.create(env);
      const sheet = C.paper({tone: PAPER, seed: 3}), night = C.paper({tone: NIGHT, grain: .04, blotch: .03, fibres: 0, edge: .4, seed: 9});
      const cardSheet = C.paper({tone: '#f4f1ea', width: 800, height: 1000, seed: 4, edge: .1});
      const page = C.document({kicker: data.document.kicker, headline: data.document.headline, highlight: data.document.highlight, width: 2400});
      const paperLayer = (name, sheetOf, drift) => A.layer({name, position: k([0, [W / 2, H / 2], 'glide'], [4, [W / 2 + drift[0], H / 2 + drift[1]]]),
        draw: g => C.drawPaper(g, sheetOf, {x: -W / 2, y: -H / 2})});
      const dA = 3.1, dB = 3.6, dC = 3.2, tz = .5, tw = .32;
      const dD = Math.max(2.4, DURATION - (dA + dB + dC - tz - tw));

      // 1. FIGURE: a 2.5D camera, the phrase on the focus plane, the figure behind it.
      const phrase = C.layoutPhrase(data.phrase, {width: safe.width * .96, size: U * .15, y: safe.y + safe.height * .5});
      const key = phrase.find(w => w.kind === 'key') || phrase[0];
      const camZ = -1500;
      const sceneA = A.comp({name: 'figure', width: W, height: H, duration: dA, background: PAPER,
        camera: {zoom: 1500, aperture: 16,
          position: k([0, [W / 2 - 20, H / 2, camZ], 'glide'], [dA, [W / 2 + 25, H / 2 - 10, camZ + 150]]),
          focusDistance: k([0, 2100, 'hold'], [.9, 2100, 'swift'], [1.6, 1440])},   // rack focus: figure → phrase
        layers: [...wordLayers(phrase, .25, {threeD: true}),
          A.layer({name: 'figure', threeD: true, position: k([0, [W * .58, H * .47, 600], 'glide'], [dA, [W * .55, H * .46, 600]]),
            scale: 210, draw: g => C.numeral(g, data.numeral, {x: 0, y: 0, size: U * .62, alpha: .55, color: '#2a2724'})}),
          A.layer({name: 'grid', opacity: 70, position: [0, 0], draw: g => {
            g.strokeStyle = 'rgba(20,20,18,.06)'; g.lineWidth = 1;
            for (let x = safe.x; x <= safe.x + safe.width + 1; x += safe.width / 6) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
          }}),
          paperLayer('paper', sheet, [-30, 12])]});

      // 2. PAGE: the camera's moves are keys on the page and its focus, as on an AE camera.
      const hl = page.highlightLine >= 0 ? page.lines[page.highlightLine] : null;
      const lineY = hl ? hl.y - hl.size * .35 : 900;
      const P = {
        scale: k([0, 1.02, 'glide'], [1.9, .97, 'swift'], [3.1, .37]),
        focusX: k([0, hl ? page.hx + page.hw * .1 : 1200, 'glide'], [1.9, hl ? page.hx + page.hw * .78 : 1200, 'swift'], [3.1, page.width / 2]),
        focusY: k([0, lineY, 'hold'], [1.9, lineY, 'swift'], [3.1, page.headY || 400]),
        dof: k([0, 85, 'hold'], [1.9, 85, 'swift'], [3.1, 10]),
        cy: k([0, H * .5, 'hold'], [1.9, H * .5, 'swift'], [3.1, H * .42]),
        rot: k([0, -.075, 'glide'], [3.1, -.02]),
        marker: k([.75, 0, 'snap'], [1.45, 1]),
      };
      const sceneB = A.comp({name: 'page', width: W, height: H, duration: dB, background: DESK, layers: [
        A.layer({name: 'page', position: [0, 0], draw: (g, t) => C.drawDocument(g, page, {cx: W / 2, cy: V(P.cy, t), scale: V(P.scale, t),
          rot: V(P.rot, t), dof: V(P.dof, t), focus: V(P.focusY, t), focusX: V(P.focusX, t), highlight: V(P.marker, t), marker: 'rgba(255,59,35,.62)'})})]});

      // 3. CARD: a ribbon draws on; the card drops with an overshoot; its title, rule and items are its children.
      const cw = U * .74, ch = U * .94, items = data.card.items || [];
      const RIBBON = [[W * .95, -H * .02], [W * .62, H * .16], [W * .22, H * .42], [W * .72, H * .62], [W * .38, H * .86], [-W * .1, H * 1.04]];
      const ribbonOn = k([0, 0, 'swift'], [.95, 1]), lift = k([.15, 1.5, 'snap'], [.6, .45]);
      const sceneC = A.comp({name: 'card', width: W, height: H, duration: dC, background: PAPER, layers: [
        ...items.map((item, i) => {
          const at = 1.0 + i * 5 * F, y = -ch * .5 + ch * (.53 + i * .13);
          return A.layer({name: `item${i}`, parent: 'card', position: A.overshoot(at, [-cw * .3 + 40, y], at + .35, [-cw * .3, y], {amount: .1}),
            opacity: k([at, 0, 'snap'], [at + .15, 100]), draw: g => {
              g.strokeStyle = '#fbfaf6'; g.lineWidth = cw * .012;
              g.beginPath(); g.arc(0, -cw * .03, cw * .035, 0, Math.PI * 2); g.stroke();
              g.beginPath(); g.moveTo(-cw * .025, -cw * .055); g.lineTo(cw * .025, -cw * .005); g.stroke();
              g.fillStyle = '#fbfaf6'; g.font = `600 ${Math.round(cw * .075)}px ${SANS}`; g.textAlign = 'left';
              g.fillText(item, cw * .09, 0);
            }});
        }),
        A.layer({name: 'rule', parent: 'card', anchor: [0, 0], position: [-cw * .36, -ch * .12], scale: k([.75, [0, 100], 'snap'], [1.15, [100, 100]]),
          draw: g => { g.fillStyle = '#fbfaf6'; g.fillRect(0, 0, cw * .72, Math.max(2, cw * .012)); }}),
        A.layer({name: 'title', parent: 'card', position: [0, -ch * .18], scale: A.overshoot(.55, 70, .9, 100, {amount: .06}),
          opacity: k([.55, 0, 'snap'], [.7, 100]),
          draw: g => { g.fillStyle = '#fbfaf6'; g.font = `800 ${Math.round(cw * .17)}px ${SANS}`; g.textAlign = 'center'; g.fillText(data.card.title, 0, 0, cw * .86); }}),
        A.layer({name: 'card', position: A.overshoot(.15, [W * .52, -H * .35], .62, [W * .52, H * .47], {amount: .05, settle: .25}),
          rotation: k([.15, 14, 'snap'], [.8, -3]), draw: (g, t) => C.card(g, {x: 0, y: 0, w: cw, h: ch, rot: 0, lift: V(lift, t), fill: '#8f8d89', texture: cardSheet})}),
        A.layer({name: 'ribbon', position: [0, 0], draw: (g, t) => C.ribbon(g, RIBBON, {width: U * .14, color: GREY, to: V(ribbonOn, t), shadow: .5})}),
        paperLayer('paper', sheet, [-24, 0])]});

      // 4. PHONE: black, the phone rises, its notifications are its children and leave in turn; the ending lands.
      const ph = U * 1.25, pw = ph * .49, sw = pw * .9, sh = ph * .955, list = data.notifications || [];
      const ending = C.layoutPhrase(data.ending, {width: safe.width * .9, size: U * .13, y: safe.y + safe.height * .1});
      const notes = list.map((n, i) => {
        const at = .45 + i * 6 * F, off = 1.55 + (list.length - 1 - i) * 4 * F;
        const y = -sh / 2 + sh * .3 + i * sw * .22, x = -sw / 2 + sw * .05;
        return A.layer({name: `note${i}`, parent: 'phone', position: A.overshoot(at, [x + sw * .5, y], at + .4, [x, y], {amount: .06}),
          opacity: k([at, 0, 'snap'], [at + .1, 100, 'hold'], [off, 100, 'accel'], [off + .2, 0]),
          draw: g => C.notification(g, 0, 0, sw * .9, {title: n.title, body: n.body, time: 'now', tint: i % 2 ? '#3a8bff' : RED})});
      });
      const sceneD = A.comp({name: 'phone', width: W, height: H, duration: dD, background: NIGHT, layers: [
        ...wordLayers(ending, 1.25, {ink: '#f2efe8', glow: 1, tag: 'e'}),
        ...notes,
        A.layer({name: 'phone', position: A.overshoot(.05, [W / 2, H * 1.5], .6, [W / 2, H * .72], {amount: .04, settle: .3}),
          rotation: k([.05, 7, 'snap'], [.75, -4]),
          draw: g => C.phone(g, {x: 0, y: 0, h: ph, rot: 0, lift: 1, screen: (s, w, h) => {
            s.fillStyle = '#f2f2f2'; s.font = `200 ${Math.round(w * .2)}px ${SANS}`; s.textAlign = 'center'; s.fillText('21:47', w / 2, h * .2);
          }})}),
        A.layer({name: 'glow', position: [W / 2, H * .62], opacity: k([0, 0, 'swift'], [.7, 100]), draw: g => {
          const r = g.createRadialGradient(0, 0, 0, 0, 0, U * .8); r.addColorStop(0, 'rgba(255,59,35,.2)'); r.addColorStop(1, 'rgba(255,59,35,0)');
          g.fillStyle = r; g.fillRect(-U, -U, U * 2, U * 2);
        }}),
        A.layer({name: 'night', position: [W / 2, H / 2], draw: g => C.drawPaper(g, night, {x: -W / 2, y: -H / 2})})]});

      // The zoom goes through the keyword: its centre on screen at the end of scene 1.
      const keyAt = [key.x + key.width / 2, key.y - key.size * .35];
      film = A.sequence([{comp: sceneA}, {comp: sceneB}, {comp: sceneC}, {comp: sceneD}],
        [{type: 'zoom', dur: tz, at: keyAt, flash: RED}, {type: 'whip', dur: tw, dir: 'left'}, {type: 'cut', dur: 0}], {background: '#000'});
      const [, sb, sc, sd] = film.starts;
      hits = {phrase: .25, zoom: sb, marker: sb + .75, whip: sc, card: sc + .62, black: sd, end: sd + 1.25};
    },

    state(t) { return {t, track: film.track(t), debug: {hits, starts: film.starts, duration: film.duration}}; },

    draw(s, {base}) { film.render(base, s.t); },
  });
})();
