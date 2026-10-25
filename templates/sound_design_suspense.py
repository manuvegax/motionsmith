"""TEMPLATE · Suspense sound design without music, by deterministic synthesis.

Copy into the piece folder as `sound.py` and edit ONLY what is marked "EDIT": DURATION, SEED, TITLE, VACUUM, CUES
and compose(). The example compose() is a short demonstration; it
shows the grammar (a riser dying into the hit, an impact with phone-audible harmonics, a vacuum before the reveal),
not timings to copy. Impact times must match the `hits` of plan.json, which also drive the image. Then:
`python -B sound.py --replace` and `scripts/audio_check.py`. For cue-list driven soundtracks without editing code,
see `scripts/build_soundtrack.py` and the `scripts/sfx/` library.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import wave

import numpy as np


ROOT = Path(__file__).resolve().parent
SR, DURATION = 48000, 12.0          # EDIT: exact duration of the video
N = round(SR * DURATION)
SEED = 202610220601                  # EDIT: one seed per piece (determinism)
TITLE = "Reveal example"            # EDIT: name in audio-notes.md
VACUUM = (7.97, 8.205)               # EDIT: (start, end) of the silence before the reveal, or None
TARGET_LUFS, TARGET_TP = -16.0, -1.5
rng = np.random.default_rng(SEED)
dry = np.zeros((N, 2), dtype=np.float64)
send = np.zeros_like(dry)


def timeline(duration):
    return np.arange(round(duration * SR), dtype=np.float64) / SR


def smoothstep(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


def edge_fade(signal, attack=.003, release=.018):
    """Raised-cosine boundaries; exact zero at the first and last sample."""
    result = np.array(signal, dtype=np.float64, copy=True)
    for length, reverse in ((min(len(result), round(attack * SR)), False),
                            (min(len(result), round(release * SR)), True)):
        if length > 1:
            ramp = np.sin(np.linspace(0, np.pi / 2, length)) ** 2
            if result.ndim == 2:
                ramp = ramp[:, None]
            if reverse:
                result[-length:] *= ramp[::-1]
            else:
                result[:length] *= ramp
    return result


def rms_normal(x):
    return x / max(1e-12, np.sqrt(np.mean(x * x)))


def noise(duration, low=20, high=20000):
    count = round(duration * SR)
    spectrum = np.fft.rfft(rng.standard_normal(count))
    frequencies = np.maximum(np.fft.rfftfreq(count, 1 / SR), 1e-6)
    shape = 1 / np.sqrt(1 + (low / frequencies) ** 6) / np.sqrt(1 + (frequencies / high) ** 8)
    shape[0] = 0
    return rms_normal(np.fft.irfft(spectrum * shape, n=count))


def swept(signal, centre_of_time, octaves=1.2, frame=2048, hop=512):
    """Time-varying band-pass by overlap-added STFT frames; centre_of_time(t) gives Hz at t seconds."""
    window = np.hanning(frame)
    padded = np.concatenate([np.zeros(frame // 2), signal, np.zeros(frame)])
    out = np.zeros(len(padded))
    weight = np.zeros(len(padded))
    log_f = np.log2(np.maximum(np.fft.rfftfreq(frame, 1 / SR), 1.0))
    for start in range(0, len(signal) + frame // 2, hop):
        segment = padded[start:start + frame]
        if len(segment) < frame:
            break
        gain = np.exp(-.5 * ((log_f - math.log2(max(20.0, centre_of_time(start / SR)))) / (octaves / 2)) ** 2)
        out[start:start + frame] += np.fft.irfft(np.fft.rfft(segment * window) * gain, n=frame) * window
        weight[start:start + frame] += window ** 2
    return (out / np.maximum(weight, 1e-6))[frame // 2:frame // 2 + len(signal)]


def place(at, signal, gain=1.0, pan=0.0, reverb=0.0):
    start = round(at * SR)
    if start < 0:
        signal = signal[-start:]
        start = 0
    count = min(len(signal), N - start)
    if count <= 0:
        return
    signal = np.asarray(signal[:count])
    if signal.ndim == 1:
        position = np.clip(np.broadcast_to(np.asarray(pan, dtype=np.float64), (count,)) if np.ndim(pan) == 0
                           else np.asarray(pan)[:count], -1, 1)
        stereo = np.column_stack((np.cos((position + 1) * np.pi / 4), np.sin((position + 1) * np.pi / 4))) * signal[:, None]
    else:
        stereo = signal
    dry[start:start + count] += stereo * gain
    if reverb:
        send[start:start + count] += stereo * gain * reverb


def saturate(x, drive):
    return np.tanh(x * drive) / np.tanh(drive)


# ---------- vocabulary ----------

def boom(at, gain=.9, start_hz=92, end_hz=31, decay=1.5, punch=1.0, reverb=.35):
    """Cinematic impact: falling sine, saturated so its harmonics (60-300 Hz) reach phone speakers."""
    duration = decay * 2.4
    x = timeline(duration)
    frequency = end_hz + (start_hz - end_hz) * np.exp(-x / .11)
    phase = 2 * np.pi * np.cumsum(frequency) / SR
    tone = .55 * np.sin(phase) + .50 * np.sin(2 * phase + .3) * np.exp(-x / (decay * .6)) + .30 * np.sin(3 * phase + .9) * np.exp(-x / (decay * .35))
    body = saturate(tone * np.exp(-x / decay), 3.2)
    click = noise(duration, 1500, 9000) * np.exp(-x / .006) * .30 * punch
    thump = noise(duration, 60, 420) * np.exp(-x / .07) * .45 * punch
    place(at, edge_fade(body + click + thump, .0008, .06), gain, 0, reverb)


def hit(at, gain=.55, pan=0.0, reverb=.22):
    """Short tight impact for a cut or a stamp."""
    x = timeline(.6)
    frequency = 52 + 90 * np.exp(-x / .045)
    phase = 2 * np.pi * np.cumsum(frequency) / SR
    body = saturate((.6 * np.sin(phase) + .5 * np.sin(2 * phase + .4)) * np.exp(-x / .16), 2.6)
    crack = noise(.6, 1800, 11000) * np.exp(-x / .012) * .55
    place(at, edge_fade(body + crack, .0006, .04), gain, pan, reverb)


def glass(at, base=1760.0, gain=.24, pan=0.0, decay=1.3, reverb=.5, bright=1.0):
    """Struck glass: inharmonic partials, left/right detuned so the ring beats and widens."""
    duration = decay * 2.6
    x = timeline(duration)
    left = np.zeros_like(x)
    right = np.zeros_like(x)
    for ratio, amplitude, decay_scale in ((1, 1, 1), (2.32, .55, .62), (4.25, .32, .40), (6.63, .17, .27), (9.38, .09, .18)):
        envelope = np.exp(-x / (decay * decay_scale))
        left += amplitude * np.sin(2 * np.pi * base * ratio * x) * envelope
        right += amplitude * np.sin(2 * np.pi * base * ratio * 1.0028 * x + .6) * envelope
    strike = noise(duration, 3000, 15000) * np.exp(-x / .004) * .35 * bright
    stereo = np.column_stack((left + strike, right + strike)) * .42
    balance = np.array([math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)]) * math.sqrt(2)
    place(at, edge_fade(stereo * balance, .0005, .08), gain, 0, reverb)


def whoosh(at, duration, pan_from, pan_to, centre_from=1100, centre_to=520, gain=.30, octaves=1.6, reverb=.15):
    """Band-passed air whose centre falls as it passes (Doppler); peak late, equal-power pan travel."""
    x = timeline(duration)
    u = x / duration
    air = rms_normal(swept(noise(duration, 80, 14000), lambda t: centre_from * (centre_to / centre_from) ** (t / duration), octaves))
    envelope = np.sin(np.pi * u) ** 2 * (.35 + .65 * u)
    place(at, edge_fade(air * envelope, .01, .02), gain, pan_from + (pan_to - pan_from) * smoothstep(u), reverb)


def riser(start, end, gain=.32, noise_from=260, noise_to=7500, tone_from=98, tone_to=784, pan=0.0, reverb=.28):
    """Tension into a hit: rising filtered noise, rising detuned tone, tremolo that accelerates. Cut dead at the end."""
    duration = end - start
    x = timeline(duration)
    u = x / duration
    air = rms_normal(swept(noise(duration), lambda t: noise_from * (noise_to / noise_from) ** ((t / duration) ** 1.3), 1.4))
    frequency = tone_from * (tone_to / tone_from) ** (u ** 1.6)
    phase = 2 * np.pi * np.cumsum(frequency) / SR
    tone = sum(np.sin(k * phase + .3 * k) / k for k in range(1, 6)) + sum(np.sin(k * phase * 1.007) / k for k in range(1, 6))
    tremolo = .55 + .45 * np.sin(2 * np.pi * np.cumsum(4 + 16 * u ** 2) / SR) ** 2
    envelope = u ** 2.3
    place(start, edge_fade((air * .85 + tone * .16 * tremolo) * envelope, .05, .006), gain, pan, reverb)


def reverse_swell(end, duration, gain=.32, reverb=.2):
    """A reversed cymbal-like decay: air that sucks into the following impact."""
    x = timeline(duration)
    tail = noise(duration, 1800, 15000) * np.exp(-x / (duration * .32))
    low = noise(duration, 90, 900) * np.exp(-x / (duration * .45)) * .55
    place(end - duration, edge_fade((tail + low)[::-1], .02, .004), gain, 0, reverb)


def slap(at, gain=.30, pan=0.0):
    """Paper landing on paper."""
    x = timeline(.2)
    signal = noise(.2, 700, 9500) * np.exp(-x / .016) + .55 * np.sin(2 * np.pi * 150 * x) * np.exp(-x / .028)
    place(at, edge_fade(signal, .0006, .02), gain, pan, .08)


def heartbeat(at, gain=.42):
    """Two muffled beats (lub-dub), saturated lightly so they read on small speakers."""
    for offset, hz, level in ((0, 54, 1.0), (.26, 66, .72)):
        x = timeline(.32)
        beat = saturate((np.sin(2 * np.pi * hz * x) + .6 * np.sin(4 * np.pi * hz * x + .5)) * np.exp(-x / .07) * (1 - np.exp(-x / .004)), 2.6)
        beat += noise(.32, 60, 300) * np.exp(-x / .03) * .25
        place(at + offset, edge_fade(beat, .001, .03), gain * level, 0, .05)


def ticks(at, count, spacing=.022, gain=.05, pan=0.0, pitch=3200):
    """A burst of tiny clicks for letters that land in a stagger."""
    for index in range(count):
        x = timeline(.03)
        frequency = pitch * (1 + .06 * rng.standard_normal())
        click = np.sin(2 * np.pi * frequency * x) * np.exp(-x / .004) + noise(.03, 2500, 12000) * np.exp(-x / .002) * .4
        place(at + index * spacing, edge_fade(click, .0003, .008), gain * (.75 + .25 * rng.random()), pan, .1)


def lid(at, gain=.06):
    """A blink: a soft low flutter, felt more than heard."""
    x = timeline(.12)
    signal = noise(.12, 120, 1400) * np.exp(-x / .03) * np.sin(np.pi * x / .12)
    place(at - .05, edge_fade(signal, .002, .02), gain, 0, .05)


def shimmer(start, end, gain=.16):
    """The light sweep across the title: high glints travelling left to right over a rising air band."""
    duration = end - start
    for _ in range(70):
        t = start + duration * rng.random() ** .9
        x = timeline(.07)
        frequency = 3000 + 6500 * rng.random()
        grain = np.sin(2 * np.pi * frequency * x) * np.exp(-x / (.012 + .03 * rng.random()))
        place(t, edge_fade(grain, .001, .01), gain * (.25 + .75 * rng.random()) * .5, -.85 + 1.7 * (t - start) / duration, .55)
    x = timeline(duration)
    air = rms_normal(swept(noise(duration, 2000, 16000), lambda s: 4200 * (10500 / 4200) ** (s / duration), 1.0))
    place(start, edge_fade(air * np.sin(np.pi * x / duration) ** 2, .02, .05), gain * .45, np.linspace(-.8, .8, len(x)), .3)


def bed():
    """Low drone that tightens towards the lock, drops out (vacuum) before the reveal, then settles."""
    t = np.arange(N) / SR
    level = np.interp(t, [0, 1.7, 3.6, 5.0, 7.2, 7.85, 8.0, 8.24, 8.3, 10.3, 11.4, 12.0],
                         [.08, .10, .12, .15, .30, .32, .02, .0, .20, .15, .10, 0])
    pitch_rise = 1 + .06 * smoothstep((t - 3.6) / 3.65) * (t < 7.95)
    base = 2 * np.pi * np.cumsum(pitch_rise) / SR
    drone = .30 * np.sin(36.7 * base) + .45 * np.sin(55.0 * 1.003 * base + .4) + .60 * np.sin(73.4 * 1.002 * base)
    drone += .40 * np.sin(110.0 * base + 1.1) + .22 * np.sin(146.8 * .998 * base + .7)
    drone = saturate(drone * .55, 1.6) * (.85 + .15 * np.sin(2 * np.pi * .23 * t))
    rumble = noise(DURATION, 60, 520) * .30
    stereo = np.column_stack((drone + rumble, drone + np.roll(rumble, 911)))
    place(0, stereo * level[:, None], 1.0, 0, .12)
    # A faint high tension pair, beating, that rises while the lens hunts (4.0-7.25): suspense, not melody.
    hunt = (t > 3.9) & (t < 7.95)
    u = np.clip((t - 3.9) / 3.35, 0, 1)
    frequency = 880 * (1.25 ** u)
    phase = 2 * np.pi * np.cumsum(frequency) / SR
    pair = (np.sin(phase) + np.sin(phase * 1.0047)) * .5 * hunt * smoothstep(u * 3) * (1 - smoothstep((t - 7.25) / .6))
    place(0, pair * .022 * (.6 + .4 * u), 1.0, 0, .45)


# ---------- the score of events, timed to motion.js ----------

# EDIT: one row per visual moment the sound marks (copied into audio-notes.md).
CUES = [
    {"time_s": 0.00, "visual": "eye macro, the first word enters", "sound": "low drone and air; rising whoosh and a soft hit as the word lands (0.40)"},
    {"time_s": 0.62, "visual": "the gaze travels", "sound": "short riser pushing into the cut"},
    {"time_s": 1.30, "visual": "red swipe to the left", "sound": "right-to-left whoosh; blink at 1.46"},
    {"time_s": 1.70, "visual": "cut to paper; three prints arrive", "sound": "short impact + three paper slaps (1.86 / 1.93 / 2.00)"},
    {"time_s": 2.00, "visual": "red band and the second word", "sound": "left-to-right swipe and a low stamp as the word settles (2.40)"},
    {"time_s": 2.90, "visual": "reading the line", "sound": "riser towards the lens"},
    {"time_s": 3.25, "visual": "a print passes the camera", "sound": "heavy right-to-left whoosh"},
    {"time_s": 3.60, "visual": "the glass lens is born", "sound": "struck glass + low hit; prints settle at 4.18 / 4.25"},
    {"time_s": 4.40, "visual": "the lens chases the gaze", "sound": "accelerating heartbeat (4.40 / 5.15 / 5.82 / 6.40) and a beating high pair"},
    {"time_s": 5.00, "visual": "the turn of the sentence", "sound": "main riser up to the docking; exit (5.34) and entry (5.60) whooshes"},
    {"time_s": 6.40, "visual": "lens anticipation and arc", "sound": "short suction and a Doppler whoosh"},
    {"time_s": 7.25, "visual": "the lens docks into the O", "sound": "glass click + impact; the air of the push comes in"},
    {"time_s": 7.60, "visual": "the camera enters the lens", "sound": "reverse swell; near-total vacuum 8.00-8.24"},
    {"time_s": 8.25, "visual": "pull-out reveals the word", "sound": "big impact with a long tail; orbit air"},
    {"time_s": 9.62, "visual": "the red O arrives", "sound": "high glass"},
    {"time_s": 9.50, "visual": "the other words enter", "sound": "short whooshes and click bursts"},
    {"time_s": 10.30, "visual": "the title settles", "sound": "final low impact + glass"},
    {"time_s": 10.55, "visual": "light sweep over the title", "sound": "glints travelling left to right"},
    {"time_s": 11.50, "visual": "tail", "sound": "decay only; fade 11.5-12"},
]


def compose():
    # EDIT: example from a 12 s reveal piece. Replace with the events of your piece.
    bed()
    # Scene A: first word
    whoosh(.0, .42, -.2, .1, 500, 1400, .16, 1.8, .1)
    ticks(.30, 4, .022, .035, .1, 2600)
    hit(.40, .26, .0, .25)
    riser(.62, 1.70, .20, 300, 6500, 110, 660)
    whoosh(1.28, .44, .75, -.85, 1500, 600, .34, 1.5, .12)
    lid(1.46)
    # Scene B: paper, second line
    hit(1.70, .62, -.05, .2)
    for at, pan in ((1.86, -.55), (1.93, .6), (2.00, .1)):
        slap(at, .34, pan)
    ticks(1.80, 5, .022, .03, -.3, 2300)
    whoosh(2.00, .32, -.8, .7, 900, 2200, .20, 1.3, .08)
    ticks(2.32, 6, .022, .045, .3, 2100)
    hit(2.42, .52, .15, .18)
    slap(2.42, .22, .2)
    riser(2.90, 3.60, .26, 350, 8000, 147, 880)
    whoosh(3.20, .44, .85, -.9, 900, 380, .46, 1.6, .15)
    lid(3.40, .05)
    # Scene C: the lens is born
    glass(3.60, 1568, .30, .0, 1.6, .55)
    hit(3.60, .40, .0, .3)
    whoosh(3.60, .5, -.9, -.2, 700, 1400, .14)
    whoosh(3.60, .5, .9, .2, 700, 1400, .14)
    slap(4.18, .24, -.45)
    slap(4.25, .22, .45)
    ticks(3.95, 8, .022, .03, .0, 2400)
    for at, level in ((4.40, .30), (5.15, .34), (5.82, .38), (6.40, .44)):
        heartbeat(at, level)
    # Scene D: the hunt and the lock
    riser(5.00, 7.25, .40, 220, 9000, 82, 990)
    whoosh(5.34, .30, .1, -.9, 1300, 700, .22)
    whoosh(5.60, .40, -.85, .0, 800, 1500, .16)
    ticks(5.90, 9, .022, .04, .25, 3000)
    reverse_swell(6.58, .18, .16)
    whoosh(6.56, .62, .45, -.25, 1500, 420, .34, 1.5, .2)
    whoosh(7.10, .55, .0, -.95, 1000, 450, .22)
    glass(7.25, 2093, .30, -.1, 1.1, .45)
    boom(7.25, .55, 110, 40, .55, 1.0, .25)
    lid(7.67, .05)
    # Push through the lens, vacuum, reveal
    whoosh(7.25, .80, .0, .0, 260, 900, .24, 2.0, .1)
    reverse_swell(8.0, .55, .34, .25)
    boom(8.25, 1.0, 95, 29, 1.9, 1.2, .45)
    whoosh(8.30, 1.9, -.5, .6, 600, 260, .20, 2.2, .3)
    # Title assembles
    glass(9.62, 2637, .24, .55, 1.3, .55)
    whoosh(9.30, .45, .95, .3, 1300, 600, .18)
    whoosh(9.48, .45, -.8, -.2, 1200, 650, .18)
    ticks(9.62, 6, .030, .035, -.2, 2700)
    whoosh(10.03, .40, .7, .1, 1200, 700, .15)
    ticks(10.18, 2, .040, .035, .1, 2900)
    riser(9.40, 10.30, .16, 600, 9000, 196, 1175)
    boom(10.30, .62, 82, 33, 1.3, .7, .5)
    glass(10.30, 1318.5, .20, .0, 2.0, .65, .6)
    lid(10.53, .04)
    shimmer(10.55, 11.45, .18)

    # Stereo room: finite noise IR (pink-ish, darker tail), convolved with the send bus.
    length = round(2.3 * SR)
    x = np.arange(length) / SR
    ir = np.column_stack([noise(2.3, 120, 9000), noise(2.3, 120, 9000)]) * np.exp(-x / .48)[:, None]
    ir[:round(.018 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))
    size = 1 << int(math.ceil(math.log2(N + length)))
    room = np.column_stack([np.fft.irfft(np.fft.rfft(send[:, c], size) * np.fft.rfft(ir[:, c], size), size)[:N] for c in (0, 1)])
    master = dry + room * .55
    # Vacuum before the reveal: everything ducks to about -24 dB; the reveal boom comes right after it.
    if VACUUM:
        t = np.arange(N) / SR
        duck = 1 - .94 * smoothstep((t - VACUUM[0]) / .07) * (1 - smoothstep((t - VACUUM[1]) / .04))
        master *= duck[:, None]
    # High-pass 35 Hz: deeper sub only eats headroom; phones cannot play it.
    spectrum = np.fft.rfft(master, axis=0)
    frequencies = np.maximum(np.fft.rfftfreq(N, 1 / SR), 1e-6)
    spectrum *= (1 / np.sqrt(1 + (35 / frequencies) ** 8))[:, None]
    master = np.fft.irfft(spectrum, n=N, axis=0)
    master -= np.mean(master, axis=0)
    time = np.arange(N) / SR
    master *= np.minimum(1, time / .012)[:, None]
    end_fade = np.sin(np.pi / 2 * np.clip((DURATION - time) / .50, 0, 1)) ** 2
    end_fade[-1] = 0
    return master * end_fade[:, None]


# ---------- measurement and mastering (FFmpeg measures; it does not process the delivered audio) ----------

def measure(ffmpeg, samples=None, path=None):
    args = [ffmpeg, "-hide_banner", "-nostats", "-v", "info"]
    if samples is not None:
        args += ["-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "pipe:0"]
        data = np.asarray(samples, dtype="<f4").tobytes()
    else:
        args += ["-i", str(path)]
        data = None
    args += ["-af", f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TP}:LRA=11:print_format=json", "-f", "null", "-"]
    result = subprocess.run(args, input=data, capture_output=True, check=False)
    stderr = result.stderr.decode("utf-8", "replace")
    if result.returncode:
        raise RuntimeError("FFmpeg measurement failed: " + stderr[-3000:])
    matches = re.findall(r'\{\s*"input_i".*?\}', stderr, re.S)
    if not matches:
        raise RuntimeError("FFmpeg did not return EBU R128 measurements")
    raw = json.loads(matches[-1])
    values = {"integrated_lufs": float(raw["input_i"]), "true_peak_dbtp": float(raw["input_tp"]),
              "lra_lu": float(raw["input_lra"]), "threshold_lufs": float(raw["input_thresh"])}
    if not all(math.isfinite(v) for v in values.values()):
        raise RuntimeError("Non-finite loudness result")
    return values


def master_to_target(master, ffmpeg):
    """Smooth bus saturation (more drive = denser), then gain to the true-peak ceiling; search the drive for the LUFS target."""
    normalized = master / max(1e-12, np.max(np.abs(master)))
    attempts, best = [], None
    low, high = .2, 12.0
    for drive in (1.0, 3.0, .5, 6.0, 2.0, 4.5, 9.0):
        candidate = saturate(normalized, drive)
        info = measure(ffmpeg, candidate * .7)
        gain_db = TARGET_TP - .05 - info["true_peak_dbtp"]
        predicted = info["integrated_lufs"] + gain_db
        attempts.append({"drive": drive, "integrated_after_true_peak_alignment_lufs": round(predicted, 3)})
        candidate = candidate * .7 * 10 ** (gain_db / 20)
        if best is None or abs(predicted - TARGET_LUFS) < abs(best[2] - TARGET_LUFS):
            best = (candidate, drive, predicted, gain_db)
        if abs(predicted - TARGET_LUFS) <= .15:
            break
        if predicted < TARGET_LUFS:
            low = max(low, drive)
        else:
            high = min(high, drive)
    if abs(best[2] - TARGET_LUFS) > .15 and low < high:
        for _ in range(7):
            drive = (low + high) / 2
            candidate = saturate(normalized, drive)
            info = measure(ffmpeg, candidate * .7)
            gain_db = TARGET_TP - .05 - info["true_peak_dbtp"]
            predicted = info["integrated_lufs"] + gain_db
            attempts.append({"drive": drive, "integrated_after_true_peak_alignment_lufs": round(predicted, 3)})
            candidate = candidate * .7 * 10 ** (gain_db / 20)
            if abs(predicted - TARGET_LUFS) < abs(best[2] - TARGET_LUFS):
                best = (candidate, drive, predicted, gain_db)
            if predicted < TARGET_LUFS:
                low = drive
            else:
                high = drive
            if abs(predicted - TARGET_LUFS) <= .15:
                break
    return best[0], {"target_integrated_lufs": TARGET_LUFS, "target_true_peak_dbtp": TARGET_TP,
                     "soft_saturation_drive": best[1], "predicted_integrated_lufs": round(best[2], 3),
                     "measurement_attempts": attempts}


def independent_ebur128(ffmpeg, path):
    result = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-v", "info", "-xerror", "-i", str(path),
                             "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True)
    stderr = result.stderr.decode("utf-8", "replace")
    if result.returncode:
        raise RuntimeError("Independent full decode/EBU R128 failed: " + stderr[-2000:])
    summary = stderr[stderr.rfind("Summary:"):]
    integrated = re.search(r"Integrated loudness:\s*I:\s*([-0-9.]+) LUFS", summary)
    peak = re.search(r"True peak:\s*Peak:\s*([-0-9.]+) dBFS", summary)
    if not integrated or not peak:
        raise RuntimeError("Cannot parse independent EBU R128 summary")
    return {"integrated_lufs": float(integrated[1]), "true_peak_rounded_dbtp": float(peak[1]),
            "printed_precision_db": .1, "full_decode_exit_code": result.returncode,
            "method": "ffmpeg ebur128=peak=true on the final PCM WAV"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Regenerate this piece's three audio outputs explicitly")
    args = parser.parse_args()
    destination = ROOT / "assets/soundtrack.wav"
    report_path = ROOT / "preview/audio-check.json"
    notes_path = ROOT / "audio-notes.md"
    if not args.replace and any(path.exists() for path in (destination, report_path, notes_path)):
        raise SystemExit("Audio outputs already exist; use --replace only for an authorized regeneration")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("FFmpeg is required for measured loudness; no dependency was installed")
    samples, mastering = master_to_target(compose(), ffmpeg)
    if not np.isfinite(samples).all() or np.max(np.abs(samples)) >= 1:
        raise RuntimeError("Invalid or clipping samples")
    pcm = np.round(samples * 32767).astype("<i2")
    destination.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())
    actual = pcm.astype(np.float64) / 32768
    measurements = measure(ffmpeg, path=destination)
    ebu = independent_ebur128(ffmpeg, destination)
    report = {"duration_s": len(actual) / SR, "sample_rate": SR, "channels": 2, "pcm_bits": 16,
              "samples_per_channel": len(actual), "seed": SEED, "music": "none; sound design only",
              "sample_peak_dbfs": float(20 * np.log10(np.max(np.abs(actual)))),
              "rms_dbfs": float(20 * np.log10(np.sqrt(np.mean(actual * actual)))),
              "first_sample": actual[0].tolist(), "last_sample": actual[-1].tolist(),
              "clipped_samples": int(np.count_nonzero(np.abs(actual) >= 1)),
              "stereo_correlation": float(np.corrcoef(actual.T)[0, 1]),
              **measurements, "mastering": mastering,
              "measurement_method": "FFmpeg loudnorm input measurement, EBU R128 and oversampled true peak",
              "independent_ebur128": ebu,
              "loudness_target_met": abs(measurements["integrated_lufs"] - TARGET_LUFS) <= 1.0,
              "true_peak_target_met": measurements["true_peak_dbtp"] <= TARGET_TP + .1,
              "original_numpy_synthesis": True, "external_assets": [], "cues": CUES,
              "subjective_listening": "not_performed; metrics do not establish perceived quality or mix balance",
              "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    cue_lines = "\n".join(f'- {cue["time_s"]:.2f} s · {cue["visual"]}: {cue["sound"]}.' for cue in CUES)
    notes_path.write_text(f'''# Sound design · {TITLE}

Effects only, **no music**: suspense with a low drone, risers, impacts, whooshes, heartbeats, glass and a vacuum.
{DURATION:g} s, 48 kHz, stereo 16-bit PCM, NumPy synthesis with seed {SEED}; no samples or external material.
`python -B sound.py --replace` regenerates this piece's three audio files.

Impact lows are saturated so their harmonics (60-300 Hz) are heard on a phone speaker, which does not reproduce a
30-40 Hz fundamental.

{cue_lines}

Master: soft bus saturation calibrated by measuring the result, then true-peak alignment. FFmpeg only measures; its
output is never the delivered audio.

Measured on the final WAV: **{measurements['integrated_lufs']:.2f} LUFS integrated** (target {TARGET_LUFS:.0f}),
**{measurements['true_peak_dbtp']:.2f} dBTP**, LRA {measurements['lra_lu']:.2f} LU; independent `ebur128`:
{ebu['integrated_lufs']:.1f} LUFS and peak {ebu['true_peak_rounded_dbtp']:.1f} dBTP. No subjective listening is
claimed: listen with the video, on the target device.
''', encoding="utf-8")
    print(json.dumps({"soundtrack": str(destination), "integrated_lufs": measurements["integrated_lufs"],
                      "true_peak_dbtp": measurements["true_peak_dbtp"], "lra_lu": measurements["lra_lu"],
                      "loudness_target_met": report["loudness_target_met"],
                      "true_peak_target_met": report["true_peak_target_met"]}, indent=2))
    if not report["loudness_target_met"] or not report["true_peak_target_met"]:
        raise SystemExit("Measured audio does not meet the requested mastering bounds")


if __name__ == "__main__":
    main()
