"""Voices: one function per sound, each placed on a Score at a time in seconds.

Every voice takes (score, at, ...) and returns nothing. `at` is the moment the sound starts, except for the two that
lead into an impact (reverse_swell and lid), which say so in their docstrings. The defaults are a starting point.
VOICES maps the names used in cues.json to the functions; the gain default of each voice is its own default argument.
"""
from __future__ import annotations

import math

import numpy as np

from .core import edge_fade, noise, rms_normal, saturate, smoothstep, swept, timeline


def hit(score, at, gain=.55, pan=0.0, reverb=.22):
    """Short tight impact for a cut or a stamp: a falling body, saturated, with a crack on the attack."""
    sr = score.sr
    x = timeline(.6, sr)
    frequency = 52 + 90 * np.exp(-x / .045)
    phase = 2 * np.pi * np.cumsum(frequency) / sr
    body = saturate((.6 * np.sin(phase) + .5 * np.sin(2 * phase + .4)) * np.exp(-x / .16), 2.6)
    crack = noise(score, .6, 1800, 11000) * np.exp(-x / .012) * .55
    score.place(at, edge_fade(body + crack, .0006, .04, sr), gain, pan, reverb)


def boom(score, at, gain=.9, start_hz=92, end_hz=31, decay=1.5, punch=1.0, reverb=.35):
    """Cinematic impact: a falling sine, saturated so that its harmonics (60-300 Hz) survive small speakers."""
    sr = score.sr
    duration = decay * 2.4
    x = timeline(duration, sr)
    frequency = end_hz + (start_hz - end_hz) * np.exp(-x / .11)
    phase = 2 * np.pi * np.cumsum(frequency) / sr
    tone = (.55 * np.sin(phase) + .50 * np.sin(2 * phase + .3) * np.exp(-x / (decay * .6))
            + .30 * np.sin(3 * phase + .9) * np.exp(-x / (decay * .35)))
    body = saturate(tone * np.exp(-x / decay), 3.2)
    click = noise(score, duration, 1500, 9000) * np.exp(-x / .006) * .30 * punch
    thump = noise(score, duration, 60, 420) * np.exp(-x / .07) * .45 * punch
    score.place(at, edge_fade(body + click + thump, .0008, .06, sr), gain, 0, reverb)


def glass(score, at, base=1760.0, gain=.24, pan=0.0, decay=1.3, reverb=.5, bright=1.0):
    """Struck glass: inharmonic partials, detuned between the ears so that the ring beats and widens."""
    sr = score.sr
    duration = decay * 2.6
    x = timeline(duration, sr)
    left = np.zeros_like(x)
    right = np.zeros_like(x)
    for ratio, amplitude, decay_scale in ((1, 1, 1), (2.32, .55, .62), (4.25, .32, .40), (6.63, .17, .27), (9.38, .09, .18)):
        envelope = np.exp(-x / (decay * decay_scale))
        left += amplitude * np.sin(2 * np.pi * base * ratio * x) * envelope
        right += amplitude * np.sin(2 * np.pi * base * ratio * 1.0028 * x + .6) * envelope
    strike = noise(score, duration, 3000, 15000) * np.exp(-x / .004) * .35 * bright
    stereo = np.column_stack((left + strike, right + strike)) * .42
    balance = np.array([math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)]) * math.sqrt(2)
    score.place(at, edge_fade(stereo * balance, .0005, .08, sr), gain, 0, reverb)


def whoosh(score, at, duration=.4, pan_from=-.2, pan_to=.1, centre_from=1100, centre_to=520, gain=.3,
           octaves=1.6, reverb=.15):
    """Air band-passed with a centre that falls as it passes (a Doppler feel); the pan travels with equal power."""
    sr = score.sr
    x = timeline(duration, sr)
    u = x / duration
    centre = lambda t: centre_from * (centre_to / centre_from) ** (t / duration)
    air = rms_normal(swept(noise(score, duration, 80, 14000), centre, sr, octaves))
    envelope = np.sin(np.pi * u) ** 2 * (.35 + .65 * u)
    score.place(at, edge_fade(air * envelope, .01, .02, sr), gain, pan_from + (pan_to - pan_from) * smoothstep(u), reverb)


def riser(score, at, duration, gain=.32, noise_from=260, noise_to=7500, tone_from=98, tone_to=784, pan=0.0,
          reverb=.28):
    """Tension into an impact: rising filtered noise, a rising detuned tone and a tremolo that speeds up.
    It is cut dead at its end, where the impact should be."""
    sr = score.sr
    x = timeline(duration, sr)
    u = x / duration
    rise = lambda t: noise_from * (noise_to / noise_from) ** ((t / duration) ** 1.3)
    air = rms_normal(swept(noise(score, duration), rise, sr, 1.4))
    frequency = tone_from * (tone_to / tone_from) ** (u ** 1.6)
    phase = 2 * np.pi * np.cumsum(frequency) / sr
    tone = sum(np.sin(k * phase + .3 * k) / k for k in range(1, 6)) + sum(np.sin(k * phase * 1.007) / k for k in range(1, 6))
    tremolo = .55 + .45 * np.sin(2 * np.pi * np.cumsum(4 + 16 * u ** 2) / sr) ** 2
    envelope = u ** 2.3
    score.place(at, edge_fade((air * .85 + tone * .16 * tremolo) * envelope, .05, .006, sr), gain, pan, reverb)


def reverse_swell(score, at, duration, gain=.32, reverb=.2):
    """A reversed cymbal-like decay that ends on `at`, the impact it leads into (it starts at at - duration)."""
    sr = score.sr
    x = timeline(duration, sr)
    tail = noise(score, duration, 1800, 15000) * np.exp(-x / (duration * .32))
    low = noise(score, duration, 90, 900) * np.exp(-x / (duration * .45)) * .55
    score.place(at - duration, edge_fade((tail + low)[::-1], .02, .004, sr), gain, 0, reverb)


def slap(score, at, gain=.30, pan=0.0):
    """Something light landing on something hard: noise with a short low thump."""
    sr = score.sr
    x = timeline(.2, sr)
    signal = noise(score, .2, 700, 9500) * np.exp(-x / .016) + .55 * np.sin(2 * np.pi * 150 * x) * np.exp(-x / .028)
    score.place(at, edge_fade(signal, .0006, .02, sr), gain, pan, .08)


def heartbeat(score, at, gain=.42):
    """Two muffled beats (lub-dub), lightly saturated so that they read on small speakers."""
    sr = score.sr
    for offset, hz, level in ((0, 54, 1.0), (.26, 66, .72)):
        x = timeline(.32, sr)
        beat = saturate((np.sin(2 * np.pi * hz * x) + .6 * np.sin(4 * np.pi * hz * x + .5))
                        * np.exp(-x / .07) * (1 - np.exp(-x / .004)), 2.6)
        beat += noise(score, .32, 60, 300) * np.exp(-x / .03) * .25
        score.place(at + offset, edge_fade(beat, .001, .03, sr), gain * level, 0, .05)


def ticks(score, at, count, spacing=.022, gain=.05, pan=0.0, pitch=3200):
    """A burst of tiny clicks, for letters that land one after another."""
    sr = score.sr
    for index in range(count):
        x = timeline(.03, sr)
        frequency = pitch * (1 + .06 * score.rng.standard_normal())
        click = np.sin(2 * np.pi * frequency * x) * np.exp(-x / .004) + noise(score, .03, 2500, 12000) * np.exp(-x / .002) * .4
        score.place(at + index * spacing, edge_fade(click, .0003, .008, sr), gain * (.75 + .25 * score.rng.random()), pan, .1)


def lid(score, at, gain=.06):
    """A blink: a soft low flutter, felt more than heard. `at` is the frame it leads into; it starts .05 s before."""
    sr = score.sr
    x = timeline(.12, sr)
    signal = noise(score, .12, 120, 1400) * np.exp(-x / .03) * np.sin(np.pi * x / .12)
    score.place(at - .05, edge_fade(signal, .002, .02, sr), gain, 0, .05)


def shimmer(score, at, duration, gain=.16):
    """A light sweep across a title: high glints that travel left to right over a rising air band."""
    sr = score.sr
    for _ in range(70):
        t = at + duration * score.rng.random() ** .9
        x = timeline(.07, sr)
        frequency = 3000 + 6500 * score.rng.random()
        grain = np.sin(2 * np.pi * frequency * x) * np.exp(-x / (.012 + .03 * score.rng.random()))
        score.place(t, edge_fade(grain, .001, .01, sr), gain * (.25 + .75 * score.rng.random()) * .5,
                    -.85 + 1.7 * (t - at) / duration, .55)
    x = timeline(duration, sr)
    rise = lambda s: 4200 * (10500 / 4200) ** (s / duration)
    air = rms_normal(swept(noise(score, duration, 2000, 16000), rise, sr, 1.0))
    score.place(at, edge_fade(air * np.sin(np.pi * x / duration) ** 2, .02, .05, sr), gain * .45,
                np.linspace(-.8, .8, len(x)), .3)


def tension(score, at, duration, root_hz=880.0, ratio=1.25, detune=1.0047, gain=.022, reverb=.45):
    """A faint high pair, slightly beating, that rises over `duration` (suspense, not melody). Fades in and out."""
    sr = score.sr
    x = timeline(duration, sr)
    u = x / duration
    frequency = root_hz * ratio ** u
    phase = 2 * np.pi * np.cumsum(frequency) / sr
    pair = (np.sin(phase) + np.sin(phase * detune)) * .5 * smoothstep(u * 3) * (1 - smoothstep((x - (duration - .6)) / .6))
    score.place(at, pair * gain * (.6 + .4 * u), 1.0, 0, reverb)


def bed(score, levels, root_hz=36.7, rise=.06, rise_from=3.6, rise_length=3.65, gain=1.0, reverb=.12):
    """A low drone for the whole score. levels: [[t, level], ...] interpolated over time (0 is silence).
    The pitch rises by `rise` (fraction) between rise_from and rise_from + rise_length, then holds."""
    sr = score.sr
    t = np.arange(score.samples) / sr
    times, values = zip(*sorted((float(a), float(b)) for a, b in levels))
    level = np.interp(t, times, values)
    pitch = 1 + rise * smoothstep((t - rise_from) / max(rise_length, 1e-9))
    base = 2 * np.pi * np.cumsum(pitch) / sr
    partials = ((1.0, .30, 1.0, 0.0), (1.5, .45, 1.003, .4), (2.0, .60, 1.002, 0.0), (3.0, .40, 1.0, 1.1), (4.0, .22, .998, .7))
    drone = sum(amp * np.sin(root_hz * ratio * detune * base + phase) for ratio, amp, detune, phase in partials)
    drone = saturate(drone * .55, 1.6) * (.85 + .15 * np.sin(2 * np.pi * .23 * t))
    rumble = noise(score, score.duration, 60, 520) * .30
    stereo = np.column_stack((drone + rumble, drone + np.roll(rumble, 911)))
    score.place(0, stereo * level[:, None], gain, 0, reverb)


VOICES = {
    "hit": hit, "boom": boom, "glass": glass, "whoosh": whoosh, "riser": riser, "reverse_swell": reverse_swell,
    "slap": slap, "heartbeat": heartbeat, "ticks": ticks, "lid": lid, "shimmer": shimmer, "tension": tension,
}
# Whole-score layers: they do not take a time. The scheduler handles them (see schedule.py).
LAYERS = ("bed", "room", "duck")
