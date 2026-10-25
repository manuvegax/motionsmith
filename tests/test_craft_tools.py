"""Checks for the craft tools: motion_curves (Graph Editor), audio_envelope, dump_state + --page, and PostFX in a browser."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave

import numpy as np

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
KEEP = os.environ.get("MOTION_KEEP_TEST_EVIDENCE") == "1"


def run_py(script, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8")


class Workspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(tempfile.mkdtemp(prefix="motion-craft-tools-"))

    @classmethod
    def tearDownClass(cls):
        if not KEEP:
            shutil.rmtree(cls.workspace, ignore_errors=True)


@unittest.skipUnless(shutil.which("node"), "node evaluates the easings")
class MotionCurves(Workspace):
    def test_known_shapes(self):
        out = self.workspace / "curves.png"
        result = run_py("motion_curves.py", "--ease", "linear", "--ease", "easyEase", "--ease", "back.out",
                        "--distance", "900", "--duration", ".8", "--out", out)
        report = json.loads(result.stdout)
        self.assertEqual(report["errors"], [], result.stderr)
        curves = report["curves"]
        self.assertAlmostEqual(curves["linear"]["peak_to_average"], 1.0, delta=.02)
        self.assertAlmostEqual(curves["easyEase"]["peak_to_average"], 1.5, delta=.05)   # Easy Ease peaks at 1.5× the average
        self.assertAlmostEqual(curves["back.out"]["overshoot_pct"], 10.0, delta=.5)
        self.assertEqual(curves["easyEase"]["speed_kinks_at_s"], [])
        self.assertTrue(out.is_file())

    def test_corner_is_detected_in_a_dump(self):
        samples = [{"t": i / 120, "value": [800 * (i / 120) if i <= 60 else 400 + 200 * (i / 120 - .5), 0]} for i in range(121)]
        path = self.workspace / "corner.json"
        path.write_text(json.dumps({"samples": samples}), encoding="utf-8")
        report = json.loads(run_py("motion_curves.py", "--json", path, "--shutter", "180", "--fps", "60").stdout)
        corner = report["curves"]["corner"]
        self.assertEqual(corner["speed_kinks_at_s"], [.5])
        self.assertAlmostEqual(corner["px_per_exposure_at_peak"], 800 * .5 / 60, delta=.2)

    def test_nothing_to_analyse_is_an_error(self):
        self.assertEqual(run_py("motion_curves.py").returncode, 1)


class AudioEnvelope(Workspace):
    def test_bands_follow_their_bursts(self):
        sr, seconds = 48000, 2.0
        t = np.arange(int(sr * seconds)) / sr
        signal = np.zeros_like(t)
        low = (t > .3) & (t < .6)
        high = (t > 1.2) & (t < 1.5)
        signal[low] += .5 * np.sin(2 * np.pi * 70 * t[low])
        signal[high] += .3 * np.sin(2 * np.pi * 5000 * t[high])
        pcm = np.round(np.column_stack([signal, signal]) * 32767).astype("<i2")
        source = self.workspace / "bursts.wav"
        with wave.open(str(source), "wb") as handle:
            handle.setnchannels(2), handle.setsampwidth(2), handle.setframerate(sr)
            handle.writeframes(pcm.tobytes())
        out, js = self.workspace / "env.json", self.workspace / "env.js"
        result = run_py("audio_envelope.py", source, "--fps", "30", "--out", out, "--js", js)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(report["frames"], 60)
        env = report["envelopes"]
        at = lambda name, sec: env[name][int(sec * 30)]
        self.assertGreater(at("low", .5), .7)
        self.assertLess(at("high", .5), .3)
        self.assertGreater(at("high", 1.4), .7)
        self.assertLess(at("low", 1.4), .3)
        self.assertTrue(all(0 <= v <= 1 for v in env["rms"]))
        self.assertTrue(js.read_text(encoding="utf-8").startswith("window.AUDIO_ENV = "))
        self.assertTrue(any(abs(h["time"] - .3) < .05 for h in report["suggested_hits"]))

    def test_a_silent_file_reads_as_silence(self):
        source = self.workspace / "silent.wav"
        with wave.open(str(source), "wb") as handle:
            handle.setnchannels(2), handle.setsampwidth(2), handle.setframerate(48000)
            handle.writeframes(np.zeros((48000, 2), "<i2").tobytes())
        out = self.workspace / "env-silent.json"
        result = run_py("audio_envelope.py", source, "--fps", "30", "--out", out)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        env = json.loads(out.read_text(encoding="utf-8"))["envelopes"]
        self.assertLess(max(max(v) for v in env.values()), .01, {k: max(v) for k, v in env.items()})

    def test_a_quiet_band_stays_quiet_with_shared_normalisation(self):
        sr = 48000
        t = np.arange(sr * 2) / sr
        signal = .5 * np.sin(2 * np.pi * 70 * t) + .01 * np.sin(2 * np.pi * 5000 * t)   # hiss-level highs, -34 dB
        pcm = np.round(np.column_stack([signal, signal]) * 32767).astype("<i2")
        source = self.workspace / "quiet-high.wav"
        with wave.open(str(source), "wb") as handle:
            handle.setnchannels(2), handle.setsampwidth(2), handle.setframerate(sr)
            handle.writeframes(pcm.tobytes())
        levels = {}
        for norm in ("shared", "band"):
            out = self.workspace / f"env-{norm}.json"
            result = run_py("audio_envelope.py", source, "--fps", "30", "--norm", norm, "--out", out)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(out.read_text(encoding="utf-8"))
            levels[norm] = report["envelopes"]["high"][30]
        self.assertLess(levels["shared"], .4, levels)    # stays where it is relative to the mix
        self.assertGreater(levels["band"], .9, levels)   # the old per-band top inflated it to full scale
        self.assertAlmostEqual(report["peak_dbfs"]["low"], -9.0, delta=1.0)   # 0.5 sine = -9 dB RMS re full scale


POSTFX_PAGE = """<!doctype html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#000">
<canvas id="c" width="256" height="256"></canvas>
<script src="../kit/motion-math.js"></script><script src="../kit/postfx-glsl.js"></script>
<script>
const gl = document.getElementById('c').getContext('webgl', {preserveDrawingBuffer: true, antialias: false});
const fx = PostFX.runner(gl, {width: 256, height: 256});
const scene = fx.target(), mid = fx.target();
const DOT = 'precision highp float;varying vec2 uv;uniform vec2 c;uniform float r,v;void main(){gl_FragColor=vec4(vec3(length((uv-c)*256.)<r?v:0.),1.);}';
function read(x, y) { const p = new Uint8Array(4); gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, p); return p[0]; }
function rgb(x, y) { const p = new Uint8Array(4); gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, p); return [p[0], p[1], p[2]]; }
function patch(x, y, n) { const p = new Uint8Array(n * n * 4); gl.readPixels(x, y, n, n, gl.RGBA, gl.UNSIGNED_BYTE, p); return Array.from({length: n * n}, (_, i) => p[i * 4]); }
const MASK = 'precision highp float;varying vec2 uv;uniform float r;void main(){gl_FragColor=vec4(0.,0.,0.,length((uv-.5)*256.)<r?1.:0.);}';
const COMP = 'precision highp float;varying vec2 uv;uniform float r;void main(){gl_FragColor=vec4(vec3(length((uv-.5)*256.)<r?.05:1.),1.);}';
function corr(a, b) { const n = a.length, ma = a.reduce((s, v) => s + v, 0) / n, mb = b.reduce((s, v) => s + v, 0) / n;
  let ab = 0, aa = 0, bb = 0; for (let i = 0; i < n; i++) { ab += (a[i] - ma) * (b[i] - mb); aa += (a[i] - ma) ** 2; bb += (b[i] - mb) ** 2; }
  return ab / Math.sqrt(aa * bb + 1e-9); }
function report() {
  const out = {hdr: fx.hdr};
  // 1) bloom: a small HDR dot gets a halo 24 px away only when bloom is on.
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 4, v: 12}});
  fx.finish(scene, null, {toneMap: 'aces'}); out.noBloom = read(128 + 24, 128);
  const b = fx.bloom(scene, {levels: 5, radius: .006});
  fx.finish(scene, b, {toneMap: 'aces', strength: .15}); out.withBloom = read(128 + 24, 128); out.centre = read(128, 128);
  // 2) directional blur spreads along its axis only.
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 6, v: 1}});
  fx.pass('directionalBlur', {to: mid, textures: {image: scene}, uniforms: {dir: [.25, 0], samples: {int: 48}}});
  fx.pass('copy', {textures: {image: mid}});
  out.alongAxis = read(128 + 20, 128); out.acrossAxis = read(128, 128 + 20);
  // 3) tone maps: clip saturates a bright value, ACES compresses it below white.
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 30, v: 1.6}});
  fx.finish(scene, null, {toneMap: 'clip'}); out.clip = read(128, 128);
  fx.finish(scene, null, {toneMap: 'aces'}); out.aces = read(128, 128);
  // 4) lens blur turns a bright point into a disc.
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 1.5, v: 40}});
  fx.pass('lensBlur', {to: mid, textures: {image: scene}, uniforms: {radius: [.06, .06], gain: 0, threshold: 1, blades: 6, rotation: 0, samples: {int: 96}}});
  fx.finish(mid, null, {toneMap: 'clip'});
  out.discInside = read(128 + 8, 128); out.discOutside = read(128 + 30, 128);
  // 5) screen print: a flat mid-grey field turns into paper and ink dots, not grey.
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 90, v: .2}});
  fx.finish(scene, null, {to: mid, toneMap: 'clip'});
  fx.pass('screenPrint', {textures: {image: mid}, uniforms: {res: [256, 256], paper: [.95, .94, .91], inkA: [1, .27, .18], inkB: [.08, .08, .09],
    inks: 1, cell: 10, angleA: 0, angleB: .785, offA: [0, 0], offB: [0, 0], texture: 0, seed: 0, strength: 1}});
  out.printLight = 0; out.printDark = 0;
  for (let x = 100; x < 156; x++) { const v = read(x, 128); if (v > 200) out.printLight++; if (v < 70) out.printDark++; }
  // 6) bloom energy: a flat field keeps its value in every mode that claims it (normalised pyramid, renormalised Karis).
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 1000, v: .5}});
  fx.finish(scene, null, {toneMap: 'clip'}); out.flatBase = read(128, 128);
  const flat = fx.bloom(scene, {levels: 5, radius: .006});
  fx.finish(scene, flat, {toneMap: 'clip', bloomMode: 'physical', strength: 1}); out.flatPhysical = read(128, 128);
  fx.finish(scene, flat, {toneMap: 'clip', bloomMode: 'halo', strength: 1}); out.flatHalo = read(128, 128);
  // 7) halation: a red fringe around a bright dot, never a tint on a flat field.
  fx.finish(scene, flat, {toneMap: 'clip', halation: 2}); out.flatHalation = rgb(128, 128);
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 4, v: 12}});
  const hot = fx.bloom(scene, {levels: 5, radius: .006});
  fx.finish(scene, hot, {toneMap: 'clip', halation: 2}); out.fringe = rgb(128 + 14, 128); out.dotCore = rgb(128, 128);
  // 8) grain: deterministic per frame, a new pattern every frame (not the previous one slid by a pixel).
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 1000, v: .2}});
  fx.finish(scene, null, {toneMap: 'clip', grain: .2, frame: 0}); const g0 = patch(100, 100, 24);
  fx.finish(scene, null, {toneMap: 'clip', grain: .2, frame: 1}); const g1 = patch(100, 100, 24);
  fx.finish(scene, null, {toneMap: 'clip', grain: .2, frame: 0}); const g0again = patch(100, 100, 24);
  out.grainRepeat = g0.every((v, i) => v === g0again[i]);
  out.grainSpread = Math.max(...g0) - Math.min(...g0);
  out.grainSlide = 0;
  for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) {
    const a = [], b = [];
    for (let y = 2; y < 22; y++) for (let x = 2; x < 22; x++) { a.push(g0[y * 24 + x]); b.push(g1[(y + dy) * 24 + x + dx]); }
    out.grainSlide = Math.max(out.grainSlide, Math.abs(corr(a, b)));
  }
  // 9) light sweep: a band at pos 0 lights the centre and fades away from it; sweepExtent matches the geometry.
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 0, v: 0}});
  fx.pass('lightSweep', {to: mid, textures: {image: scene}, uniforms: {pos: 0, width: .08, strength: 1, angle: 0, aspect: 1, tint: [1, 1, 1]}});
  fx.pass('copy', {textures: {image: mid}}); out.sweepCentre = read(128, 128); out.sweepFar = read(128 + 80, 128);
  out.sweepExtent = PostFX.sweepExtent(9 / 16, 0);
  // 10) radial blur: zoom smears along the radius, spin across it.
  fx.pass(DOT, {to: scene, uniforms: {c: [.75, .5], r: 4, v: 1}});
  fx.pass('radialBlur', {to: mid, textures: {image: scene}, uniforms: {center: [.5, .5], amount: .4, aspect: 1, samples: {int: 64}, spin: {int: 0}}});
  fx.pass('copy', {textures: {image: mid}}); out.zoomRadial = read(192 + 9, 128); out.zoomTangent = read(192, 128 + 9);
  fx.pass('radialBlur', {to: mid, textures: {image: scene}, uniforms: {center: [.5, .5], amount: .4, aspect: 1, samples: {int: 64}, spin: {int: 1}}});
  fx.pass('copy', {textures: {image: mid}}); out.spinRadial = read(192 + 9, 128); out.spinTangent = read(192, 128 + 9);
  // 11) CRT: scanlines alternate rows; the barrel pushes the corners off the tube.
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 1000, v: .8}});
  fx.pass('crt', {textures: {image: scene}, uniforms: {curvature: .3, scanline: .5, grille: 0, vignette: 0}});
  const column = [0, 1, 2, 3, 4, 5].map(i => read(128, 120 + i));
  out.scanlineSwing = Math.max(...column) - Math.min(...column); out.crtCorner = read(1, 1);
  // 14) pure black stays black under bloom and halation (the pyramid had a 1e-4 floor that lifted it).
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 0, v: 0}});
  const dark = fx.bloom(scene, {levels: 5, radius: .006});
  fx.finish(scene, dark, {toneMap: 'clip', bloomMode: 'add', strength: 4, halation: 2}); out.blackUnderBloom = rgb(128, 128);
  // 13) accumulation: clear: true on the first blended sample starts from black (it used to be ignored).
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 1000, v: .25}});
  for (let k = 0; k < 2; k++) fx.pass('copy', {to: mid, textures: {image: scene}, blend: 'add', clear: true});
  fx.pass('copy', {textures: {image: mid}}); out.accumOnce = read(128, 128);
  fx.pass('copy', {to: mid, textures: {image: scene}, blend: 'add', clear: false});
  fx.pass('copy', {textures: {image: mid}}); out.accumTwice = read(128, 128);
  // 12) light wrap: the bright background bleeds into the subject's edge only; its middle stays dark.
  const alpha = fx.target(), alphaBlur = fx.target(), comp = fx.target();
  fx.pass(MASK, {to: alpha, uniforms: {r: 60}});
  fx.pass('directionalBlur', {to: mid, textures: {image: alpha}, uniforms: {dir: [.06, 0], samples: {int: 48}}});
  fx.pass('directionalBlur', {to: alphaBlur, textures: {image: mid}, uniforms: {dir: [0, .06], samples: {int: 48}}});
  fx.pass(COMP, {to: comp, uniforms: {r: 60}});
  fx.pass(DOT, {to: scene, uniforms: {c: [.5, .5], r: 1000, v: 1}});
  for (const amount of [0, 1]) {
    fx.pass('lightWrap', {to: mid, textures: {comp, bgBlur: scene, fgAlpha: alpha, fgAlphaBlur: alphaBlur}, uniforms: {amount}});
    fx.pass('copy', {textures: {image: mid}});
    out['wrapEdge' + amount] = read(128 + 57, 128); out['wrapMiddle' + amount] = read(128, 128);
  }
  return out;
}
window.motionConfig = {width: 256, height: 256, fps: 30, frames: 30, duration: 1};
window.fxReport = report();
window.seek = () => {};
window.motionReady = Promise.resolve();
</script></body></html>"""


class BrowserTools(Workspace):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        probe = subprocess.run(["node", str(SCRIPTS / "kit" / "runtime.mjs"), "--probe"], capture_output=True, text=True)
        if probe.returncode != 0:
            raise unittest.SkipTest("Playwright not available")
        # Same layout as the skill: root/kit/*.js and root/page/index.html, opened with --page.
        (cls.workspace / "kit").mkdir()
        for name in ("motion-math.js", "postfx-glsl.js"):
            shutil.copy(SCRIPTS / "kit" / name, cls.workspace / "kit" / name)
        (cls.workspace / "page").mkdir()
        (cls.workspace / "page" / "index.html").write_text(POSTFX_PAGE, encoding="utf-8")

    def dump(self, expr, *extra):
        out = self.workspace / f"dump-{abs(hash(expr))}.json"
        result = subprocess.run(["node", str(SCRIPTS / "dump_state.mjs"), "--root", str(self.workspace), "--page", "page/index.html",
                                 "--expr", expr, "--times", "0", "--out", str(out), *extra],
                                capture_output=True, text=True, encoding="utf-8", timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(data["errors"], [])
        return data["samples"][0]["value"]

    def test_postfx_passes_do_what_they_claim(self):
        r = self.dump("window.fxReport")
        self.assertTrue(r["hdr"], "half-float targets expected on this GPU")
        self.assertGreater(r["withBloom"], r["noBloom"] + 8, r)
        self.assertGreater(r["alongAxis"], r["acrossAxis"] + 30, r)
        self.assertEqual(r["clip"], 255)
        self.assertLess(r["aces"], 252)
        self.assertGreater(r["discInside"], r["discOutside"] + 30, r)
        self.assertGreaterEqual(r["printLight"], 8, r)   # halftone: paper between the dots…
        self.assertGreaterEqual(r["printDark"], 8, r)    # …and ink dots, instead of a flat grey
        self.assertLessEqual(abs(r["flatPhysical"] - r["flatBase"]), 3, r)   # bloom keeps a flat field's energy
        self.assertLessEqual(abs(r["flatHalo"] - r["flatBase"]), 2, r)
        red, green, _ = r["flatHalation"]
        self.assertLessEqual(abs(red - green), 2, r)                     # no tint on a flat field
        self.assertGreater(r["fringe"][0], r["fringe"][1] + 15, r)       # red fringe next to the bright dot
        self.assertTrue(r["grainRepeat"], r)
        self.assertGreater(r["grainSpread"], 25, r)
        self.assertLess(r["grainSlide"], .35, r)                         # frame 1 is not frame 0 shifted
        self.assertGreater(r["sweepCentre"], 200, r)
        self.assertLess(r["sweepFar"], 10, r)
        self.assertAlmostEqual(r["sweepExtent"], .28125, places=5)
        self.assertGreater(r["zoomRadial"], r["zoomTangent"] + 30, r)
        self.assertGreater(r["spinTangent"], r["spinRadial"] + 30, r)
        self.assertGreater(r["scanlineSwing"], 40, r)
        self.assertEqual(r["crtCorner"], 0, r)
        self.assertGreater(r["wrapEdge1"], r["wrapEdge0"] + 20, r)
        self.assertLessEqual(abs(r["wrapMiddle1"] - r["wrapMiddle0"]), 2, r)
        self.assertEqual(r["blackUnderBloom"], [0, 0, 0], r)
        self.assertAlmostEqual(r["accumOnce"], 64, delta=2, msg=r)        # cleared, then one 0.25
        self.assertAlmostEqual(r["accumTwice"], 128, delta=2, msg=r)      # clear: false keeps adding

    def test_dump_state_evaluates_motion_math_in_the_page(self):
        value = self.dump("MotionMath.spring(t + 10, {freq: 2, damping: .5})")
        self.assertAlmostEqual(value, 1.0, places=4)

    def test_alpha_capture_keeps_the_background_transparent(self):
        page = self.workspace / "alpha"
        page.mkdir(exist_ok=True)
        (page / "index.html").write_text("""<!doctype html><html><head><meta charset="utf-8"></head>
<body style="margin:0;background:transparent"><div style="position:absolute;left:40px;top:40px;width:60px;height:60px;
background:rgba(255,66,46,.5)"></div><script>window.motionConfig = {width: 200, height: 200, fps: 30, frames: 1, duration: 1 / 30};
window.seek = () => {}; window.motionReady = Promise.resolve();</script></body></html>""", encoding="utf-8")
        out = self.workspace / "alpha-frames"
        result = subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(self.workspace), "--page", "alpha/index.html",
                                 "--out", str(out), "--frames", "0:0", "--png", "--alpha", "--noblur"],
                                capture_output=True, text=True, encoding="utf-8", timeout=180)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        from PIL import Image
        with Image.open(next(out.glob("*.png"))) as image:
            rgba = image.convert("RGBA")
            self.assertEqual(rgba.getpixel((5, 5))[3], 0)                     # background stays transparent
            self.assertAlmostEqual(rgba.getpixel((70, 70))[3], 128, delta=2)  # half-transparent square keeps its alpha
            self.assertGreater(rgba.getpixel((70, 70))[0], 240)               # straight alpha: colour not darkened
        refused = subprocess.run(["node", str(SCRIPTS / "sample_frames.mjs"), "--root", str(self.workspace), "--page", "alpha/index.html",
                                  "--out", str(self.workspace / "alpha-jpeg"), "--frames", "0:0", "--alpha"],
                                 capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(refused.returncode, 2)

    def test_page_outside_root_is_refused(self):
        result = subprocess.run(["node", str(SCRIPTS / "dump_state.mjs"), "--root", str(self.workspace / "page"), "--page", "../kit/x.html",
                                 "--expr", "1", "--times", "0", "--out", str(self.workspace / "no.json")],
                                capture_output=True, text=True, encoding="utf-8", timeout=120)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
