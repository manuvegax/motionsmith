/* hyperframes.js · the bridge that lets a Motionsmith piece run inside HyperFrames (Studio preview, `hyperframes
   render`, and as part of a bigger HyperFrames film), without changing the piece.
   Two signals drive the same pure function, window.seek(t), so both renderers produce the same frame:
   - the paused GSAP timeline that HyperFrames requires (`window.__timelines["motionsmith"]`): one tween on a clock
     whose setter draws the instant HyperFrames seeks to (MotionsmithHyperFrames.timeline, wired by
     scripts/hyperframes.py sync);
   - `hf-seek` {time, waitUntil}, which HyperFrames dispatches on every seek (its Three.js / TypeGPU contract).
   The same instant is never drawn twice in a row. Readiness goes to window.__hf.buildReady, so HyperFrames waits for
   fonts, plan and shaders before its first frame. Outside HyperFrames (determinism_check, render_stream…) there is no
   runtime, no GSAP and no hf-seek: nothing here fires.
   Load it AFTER piece.js. Guide: references/produce/hyperframes.md. */
(function (root) {
  'use strict';
  const KEY = 'motionsmith';
  let last = null;

  /* Time inside this piece: the time of the composition that owns it, minus the data-start of any ancestor
     composition when the piece is mounted at an offset. */
  function localTime(time) {
    const host = root.document && root.document.querySelector('[data-motionsmith-root]');
    let offset = 0;
    for (let node = host && host.parentElement; node; node = node.parentElement) {
      if (node.hasAttribute && node.hasAttribute('data-composition-id') && node.hasAttribute('data-start')) offset += Number(node.getAttribute('data-start')) || 0;
    }
    return Math.max(0, (Number(time) || 0) - offset);
  }

  function draw(time) {
    if (!root.motionInitialized || typeof root.seek !== 'function') return false;
    const t = localTime(time);
    if (last !== null && Math.abs(t - last) < 1e-9) return true;   // the timeline and hf-seek both asked for it
    root.seek(t, true);
    last = t;
    return true;
  }

  root.addEventListener('hf-seek', event => {
    const detail = event.detail || {};
    if (draw(detail.time)) return;
    if (root.motionReady && typeof detail.waitUntil === 'function') detail.waitUntil(root.motionReady.then(() => draw(detail.time)));
  });

  /* The paused timeline HyperFrames binds: one linear tween of a clock from 0 to `duration` seconds. */
  function timeline(gsap, duration) {
    let now = 0;
    const clock = {get t() { return now; }, set t(v) { now = v; draw(v); }};
    const tl = gsap.timeline({paused: true});
    tl.to(clock, {t: duration, duration, ease: 'none'}, 0);
    return tl;
  }

  // Declared-compute hold (HyperFrames waits for it before rendering): registered synchronously, right after piece.js.
  if (root.motionReady) {
    root.__hf = root.__hf || {};
    root.__hf.buildReady = root.__hf.buildReady || {};
    root.__hf.buildReady[KEY] = root.motionReady;
  }
  root.MotionsmithHyperFrames = {localTime, draw, timeline, key: KEY};
})(typeof globalThis !== 'undefined' ? globalThis : this);
