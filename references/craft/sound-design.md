# Sound design for motion

Read when a piece carries its own sound, with or without voice or music. Library: `scripts/sfx/` with
`scripts/build_soundtrack.py`; template: [`templates/sound_design_suspense.py`](../../templates/sound_design_suspense.py).
Measurement: `scripts/audio_check.py`. Editing to music: [music editing](../edit/music-editing.md).

## 1. Function before effects

- Decide first: music, sound design only, voice, or a mix. Sound design without music is a strong, ownable choice
  for suspense and reveals (a profile may make it the default).
- Every moment the sound marks is a cue. Impacts also go into `hits` in `plan.json`; the image uses them for zoom,
  shake, aberration and flash. **One list** prevents drift.
- Density follows the temperature of the story: not every cut gets a hit; silence is a cue too.
- Every new visual event gets its sound: ticks when letters cycle faces, a slap on an inversion flash, a glass ping
  on a ripple. Visual accents without sound feel weightless.

## 2. Vocabulary that works for suspense

| Element | When | Build | Careful |
|---|---|---|---|
| Bed / drone | The whole clip, tightening towards the turn | 36.7 Hz weak + 55/73/110/147 Hz, soft saturation; pitch +6 % and level 0.08→0.32 up to the turn | The fundamental alone is inaudible on phones |
| Beating high pair | While something searches | 880 Hz and 880×1.0047 Hz, low, rising with tension | Tension, not melody |
| Riser | Into each turn | Rising filtered noise + detuned tone + accelerating tremolo; envelope u^2.3 | **Dies dry on the hit** (~6 ms release); a 15–20 ms gap before the impact makes the transient define sync |
| Boom | Landing, reveal | Sine 110→30 Hz + octave + twelfth, saturated (drive ~3), click and noise thump | Without 60–300 Hz harmonics it vanishes on phones |
| Short hit | A cut, a word stamp | Sine 140→52 Hz with octave + high noise crack | |
| Whoosh | An object crossing | Band noise whose centre **falls** (Doppler), late peak, panning with the object | Pan in the direction of on-screen travel |
| Reverse swell | Suction into a hit | A reversed noise tail | Ends before the vacuum, if any |
| Heartbeat | While the hero searches | Lub-dub 0.26 s apart, shortening intervals, saturated | |
| Glass | A glass object appears | Inharmonic partials 1 / 2.32 / 4.25 / 6.63 / 9.38, L/R detuned 0.28 % | |
| Ticks | Letters landing in a cascade or cycling faces | 3 ms clicks at 2–3 kHz, one per letter or per 12 fps step | Very quiet |
| **Vacuum** | Just before the reveal | Duck everything to ~−24 dB for ~0.2 s; the big hit comes right after | Measure it: aim for near silence |
| Glints | A light sweep | 3–9.5 kHz grains panned with the light over high air | |

**Retro vocabulary** (CRT/VHS): power-on thump with degauss hum, tube whine (~8–10 kHz, very low), static until
the signal locks, 60 Hz hum with harmonics and tape hiss, a beep per typed letter (higher on the accent word),
glitches as noise and hum chopped by an irregular gate plus bit-crush, tape slowing down (hum drops ~35 %), and a
power-off zap.

## 3. Phone physics

A phone speaker barely reproduces below ~100–150 Hz: a 30–40 Hz fundamental is lost. With 60–300 Hz harmonics
(saturation, octave layers) and a 35 Hz high-pass, a mix that had 71 % of its energy below 60 Hz dropped to 39.5 %
and the impacts became audible. `audio_check.py` warns above 50 % below 60 Hz and notes above 75 % below 120 Hz:
working thresholds, not a norm.

Many phones sum both channels or play through one speaker. `audio_check.py` measures L/R correlation (warning
below 0.3) and the mono-fold loss (`mono_fold_loss_db`, warning above 4.5 dB; uncorrelated wide stereo already loses
3 dB and is normal): an out-of-phase layer disappears on a phone. The final listen is on the target device.

## 4. Loudness and master

- A sensible delivery target for social video: **−16 LUFS integrated and ≤ −2 dBTP in the WAV** (a delivery
  decision, not a platform mandate; see [formats & platforms](../edit/formats-platforms.md)).
- Master with bus saturation at a drive found by measuring the result, then gain up to the peak ceiling. With little
  peak and lots of noise, gain = min(peak ceiling, LUFS target).
- **AAC moves the peak**: −1.55 dBTP in a WAV became −1.2 dBTP in one MP4 and −0.8 dBTP in another (with a dense
  music bed). The WAV keeps −2 dBTP so the MP4 stays under −1. Measure the final file again (`audio_check.py` on the MP4).
- Edges: a 10 ms fade-in and a last sample at zero; `audio_check.py` warns about clicks at the edges.

## 4b. A music bed under the hits

Sound design without music is the default; when a piece wants a recorded bed (an intro, a loop the person chose),
`build_soundtrack.py` mixes it under the synthesized hits with a `music` cue:

```json
{"cues": [{"voice": "music", "file": "assets/bed.wav", "gain_db": -6, "start_bar": 4, "bpm": 90,
           "fade_in": 0.4, "fade_out": 1.2, "duck_db": -8}]}
```

- **Align it to the bar**: `start_bar` + `bpm` (and `beats_per_bar`, 4 by default) start reading the file on a
  downbeat; put the piece's first hit on a downbeat of the bed too (`60 / bpm × 4` s per bar).
- **Duck it on the hits**: `duck_db` dips the bed on every hit of the plan (12 ms attack, 350 ms release by default),
  so the impact reads first. −6 to −10 dB is a clear dip without pumping.
- **Level**: the whole mix is mastered to the loudness target, so `gain_db` sets the bed against the effects, not the
  final level; −6 to −12 dB under the hits is a starting point.
- It loops to cover the piece (`"loop": false` to stop at the end of the file), fades in and out, and goes in after the
  room, so it keeps its own space. Same file and settings, same samples; the report records the file's hash.
- A file the person downloaded carries a licence: check it before publishing (attribution, commercial use).

## 5. Sync

- `audio_check.py --plan plan.json` looks for an attack between 45 ms before and 125 ms after each `hit` and
  `sound_cue` (ITU-R BT.1359-1 detectability; `--tolerance` sets a symmetric window). Only attacks with ≥ 15 % of the
  strongest one count (`--onset-strength`): silence or a steady bed never "matches" a hit. Resolution ~10 ms, with a
  typical −9 ms bias (sound reads slightly early).
- A riser dying into a hit, or a whoosh at its crest, can mask the attack or make it read 50–80 ms early. Before
  moving a sound, look at the spectrogram: the hit may be there even if the detector hesitates. In new pieces, put
  the attack on the contact frame or slightly after, never before.
- Image hits read the same `hits` list; if a time changes, it changes on both sides.

## 6. Determinism and provenance

Seeded NumPy synthesis, no samples or external material; FFmpeg only measures. Regenerating requires an explicit
`--replace`. When using library sounds, record provenance and licence, and ask before downloading anything.
