# Rhythm and sync

Read when distributing motion over time: what hits, what breathes, how it syncs with voice, music or sound
design, and how it reacts to audio. Editing to music in depth: [music editing](../edit/music-editing.md).

## 1. Sources of rhythm, by authority

1. **The voice**, if there is one: real cues from the recorded take (and the script's cue table).
2. **The music**, if there is one: a beat grid ([plan schema](../produce/plan-schema.md)).
3. **Sound design without music**: the plan's `hits`, shared by image and sound ([sound design](sound-design.md)).

## 2. Beat grid

- A beat lasts 60 / BPM seconds; at 60 fps that is 3600 / BPM frames (120 BPM → 30 frames).
- Accent hierarchy: downbeat of a bar > beat > off-beat. Big changes on bars, small ones on beats.
- Do not put a hit on every beat: density follows the temperature of the story.

## 3. One list of hits

`hits` in `plan.json` (`{time, amplitude, role}`) is the single source. The image reads it with
`MotionMath.impulse(t, hits)` and `shake(t, hits)`; the soundtrack places its impacts there
(`scripts/build_soundtrack.py`); `audio_check.py --plan` checks there is an attack near each one. If a time changes,
it changes on both sides. `MotionMath` also accepts the short form `[time, amplitude]` in code; `plan.json` uses
objects with a `role`.

| Amplitude | Typical role | Image reaction |
|---|---|---|
| 0.3–0.5 | A landing, paper, a letter | Background breath |
| 0.8–1 | A cut, an appearance, a stamp | Camera zoom, brief aberration |
| 1.2–1.4 | The reveal | All of the above + a flash |

## 4. Audio-reactive motion

`audio_envelope.py` is the code version of "Convert Audio to Keyframes": one value per frame (0–1) for the total
level and three bands, with attack and release like a meter. Levels are RMS in dB re full scale. `--norm shared`
(default) measures every curve against the loudest value in the clip, so a nearly empty band stays low instead of
swinging 0–1 on its own hiss; `--norm band` gives each curve its own top; `--norm absolute` uses fixed dB between
`--floor-db` and `--ceiling-db`. The report lists `peak_dbfs` per band.

```bash
python -I <skill>/scripts/audio_envelope.py assets/soundtrack.wav --fps 60 --out preview/audio-env.json --js assets/audio-env.js
```

```javascript
const env = window.AUDIO_ENV, f = Math.min(env.frames - 1, Math.floor(t * env.fps));
const pulse = env.envelopes.low[f];          // lows → scale or breath of something big
const spark = env.envelopes.high[f];         // highs → glints, grain
```

- Big backgrounds react 10–30 %; text and logos ≤ 5 % (more reads as trembling).
- Attack ~10 ms, release ~150 ms; longer release = more breath, less tic.
- `suggested_hits` are candidates: listen and look before moving them into the plan.

## 5. Cascades (stagger)

The single source for cascade offsets and totals; principles and kinetic type link here.

| Pattern | Offset | At 60 fps | Cascade total | Use |
|---|---|---|---|---|
| Micro | 17–40 ms | 1–2 frames | ≤ 0.3 s (22 ms × 12 letters = 0.26 s) | Letters |
| Standard | 50–100 ms | 3–6 frames | ≤ 0.4 s | Words, cards |
| Dramatic | 100–200 ms | 6–12 frames | ≤ 0.6 s | A few big pieces |

If the total runs long, lower the offset or group (by words instead of letters); do not speed up each element.
Origins: start, end, centre, edges, seeded random, a grid cell (`MotionMath.stagger(i, n, {from, grid, each,
curve})`). Reverse it for exits.

## 6. Density curve

Plan intensity per scene: calm → build → peak at the reveal → resolution. After a peak, 0.3–0.8 s of less activity
so the next hit is felt. A vacuum (near silence, a held camera) just before the reveal makes the reveal land. In
short-form, "less activity" still means a living layer: never a frozen frame ([pacing](../edit/pacing-retention.md)).

## 7. Cuts and sync

- **Cut on action**: movement continues through the cut and hides it.
- **Match speeds** on both sides of a cut or a hand-off (no kink).
- **Hide the cut** behind an occlusion, a whip or a flash, in its blurriest frame.
- **Audio-visual sync**: sound that lags is tolerated more than sound that leads (ITU-R BT.1359-1: detectability
  at +45 ms lead and −125 ms lag). Impacts sit on the same frame as the visual contact. Risers that crest early make
  the attack read early: leave a 15–20 ms gap before the impact so its transient defines the sync.

## 8. Check

- `audio_check.py --plan plan.json`: an attack between 45 ms before and 125 ms after each hit. Above 60 ms of lag it
  leaves a note. Look at the spectrogram on any warning.
- A dense window on each hit: frames −1, 0 and +3. The accent happens on the hit and decays.
- The whole piece at real speed on the target device, judged by the person who will publish it.

## Sources

`hyperframes-animation` (audio reactivity, intensity limits); `motion-design` by LottieFiles (MIT, stagger
patterns); ITU-R BT.1359-1 on relative timing of sound and vision.
