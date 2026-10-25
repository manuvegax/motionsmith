# Music editing

How picture follows music: beat grids, phrasing, where cuts land, drops, silence, and motion that responds to the audio. Read it when a piece has a music track, and when the sound is only hits. The craft of rhythm in general is in [rhythm-sync.md](../craft/rhythm-sync.md); this guide is the editing side of it.

Order of authority for rhythm, the same rule as [rhythm-sync §1](../craft/rhythm-sync.md#1-sources-of-rhythm-by-authority): **the voice wins wherever words must be understood** (cut on the speech, then fit the music around it: slide the track, trim a bar, duck it); with no voice, the music; with neither, the plan's `hits`.

## 1. Beat grid

A beat lasts `60 / BPM` seconds. At 60 fps a beat is `3600 / BPM` frames.

| BPM | Beat (frames) | Bar of 4 beats (s / frames) | 8 bars (s) |
|---|---|---|---|
| 90 | 40 | 2.667 / 160 | 21.33 |
| 100 | 36 | 2.400 / 144 | 19.20 |
| 110 | 32.73 (not whole) | 2.182 / 130.9 | 17.45 |
| 120 | 30 | 2.000 / 120 | 16.00 |
| 128 | 28.125 (not whole) | 1.875 / 112.5 | 15.00 |
| 140 | 25.71 (not whole) | 1.714 / 102.9 | 13.71 |
| 160 | 22.5 (not whole) | 1.500 / 90 | 12.00 |

Many tempos do not give a whole number of frames per beat. Do not add a rounded beat length repeatedly: the error grows with every beat. Compute each beat from the start of the track and round once.

```js
const bpm = 110, fps = 60, lead = 0.12;                        // seconds of silence before beat 1
const beatTime = n => lead + n * 60 / bpm;                     // exact, from the start: no drift
const beatFrame = n => Math.round(beatTime(n) * fps);          // nearest whole frame, never accumulated
```

- Write `bpm` and `lead` into the plan, once. Every cut then refers to a beat number, not a frame number.
- Check the lead-in against the audio: the first beat must match the first transient of the track, not the file's first sample.

## 2. Bars and phrasing

Phrasing is the grouping of bars. Most pop, electronic and hip-hop tracks phrase in 4s, 8s and 16s; the big changes belong on the phrase boundaries.

| Boundary | Use it for |
|---|---|
| 16 bars | A section change: the whole look changes |
| 8 bars | A large visual change, a new scene |
| 4 bars | A new sub-scene, or a change of camera |
| 2 bars | A change of element within a scene |
| 1 bar | A cut between two shots of one idea |
| 1 beat | A movement accent, a small change of scale or colour |
| Off-beat | Texture, a flicker, a secondary element |

- Count from the start of the phrase, not from the start of the file. A section that begins on bar 5 is bar 1 of its own phrase.
- **Short-form scale.** At 90–130 BPM a bar lasts 1.8–2.7 s, so a 15–30 s reel holds about 6–16 bars and rarely reaches a 16-bar section change. Shift the table down: **4 bars** = section change (the look changes), **2 bars** = a new scene, **1 bar** = a new shot, **half a bar** = a change of element, **1 beat** = an accent.
- **Half-time or double-time?** A track at 140 BPM can feel like 70. Cut on the pulse a listener taps, not on the number in the file's metadata; when in doubt, mark both grids and pick by watching.
- **Music added inside the app** (Reels, TikTok) starts wherever the user drags it, so a beat grid built in the edit no longer lines up. If the piece must cut to music, put the music in the export.
- A cut on bar 3 of an 8-bar phrase, when every other cut is on bar 1, reads as an error unless the music does the same.

## 3. Downbeats and off-beats

- **Downbeat** (beat 1 of a bar): the strongest point. Use it for cuts that must read as decisions, and for the first frame of a section.
- **Beat 3**: a secondary point. Use it for a second cut in the same bar.
- **Off-beat** (the "and" between beats): a push. Use it for tension, for a cut that arrives early, or for a syncopated hit.

Practice: most cuts on the beat, with a small share off-beat. An off-beat cut needs an audible reference, or it reads as late.

```js
const and = n => beatTime(n) + 0.5 * 60 / bpm;               // the "and" of beat n, a syncopated push
```

## 4. Syncopation

A syncopated hit lands between the beats the ear expects. It creates a push that the beat then resolves.

- Use one syncopated hit per 2–4 bars at most (practice). More than that and the grid is lost.
- Pair it with a visual that anticipates: the element starts its move half a beat early and lands on the next downbeat.
- Check it with the sound: the hit's onset must sit on the "and", within the sync window in section 9.

## 5. Drops

A drop is the moment the music changes energy, usually after a gap.

| Part | Length | Picture |
|---|---|---|
| Build | 4–8 bars | Rising density, speed or light (see [pacing-retention.md](pacing-retention.md)) |
| Gap | 1 bar, or half a bar | Picture stops, freezes or goes dark |
| Drop | On the downbeat | The biggest change in the piece: a cut, a scale punch, a reveal |

```js
const drop = beatTime(32);                                     // the downbeat after eight bars of build
const punch = 1 + 0.06 * MotionMath.impulse(t, [[drop, 1.3]]); // impulse takes [time, amplitude] pairs too
```

- The gap is the contrast. A drop without a gap is a bigger section, not a drop.
- Put the drop on a downbeat. A drop on the off-beat reads as a mistake in most genres (practice).

## 6. Silence as a hit

A cut to silence is a hit when the picture was in motion right before it.

- Silence lasts 1/8 to 1/2 bar (practice): at 120 BPM, 0.25 s to 1 s.
- The picture holds motion until the silence starts, then freezes for the silence. The freeze is the hit.
- Make the silence in the audio edit, not with a volume automation in code. Check the silence is clean: no click at its edges.
- Measure it: `python scripts/audio_check.py <track.wav> --segment silence=8.02:8.22` reports the level of the named stretch (the segment syntax from its header).

## 7. Tempo and shot length

Tempo sets the ceiling of how fast cuts can come, not the floor. A slow track with fast cuts reads as frantic.

| Shot length | Beats at 120 BPM | Frames at 60 fps | Use |
|---|---|---|---|
| 1 beat | 1 | 30 | Fast montage, a beat-locked series |
| 2 beats | 2 | 60 | The usual short-form shot |
| 4 beats (1 bar) | 4 | 120 | One idea, one image |
| 8 beats (2 bars) | 8 | 240 | A hold with a visible change |
| 16 beats | 16 | 480 | Only with inner accents (see [pacing-retention.md](pacing-retention.md), section 9) |

- Pick the shot length from the piece's density curve, then round it to beats. A shot that ends mid-beat is a cut the music does not support.
- At 90 BPM, one beat is 40 frames; at 160 BPM, 22.5 frames, which is not a whole number. Round cut frames once, from the beat time.

## 8. Audio-reactive motion

Motion can follow the envelope of the track: the loudness of the low, mid and high bands, one value per frame.

- Build the envelope in advance with `scripts/audio_envelope.py --js <file>`. It writes `window.AUDIO_ENV` with one value per frame, 0 to 1, for overall level and three bands. Read from the precomputed file.
- Never read a live audio analyser in the render. A live analyser is not deterministic, so `seek(t)` would not reproduce a frame.
- Reaction sizes (practice): large backgrounds 10–30 %; type and logos at 5 % or less. More than that reads as a shake.

```js
const env = window.AUDIO_ENV, f = Math.min(env.frames - 1, Math.floor(t * env.fps));
const pulse = env.envelopes.low[f];                            // bass drives a large shape's scale
const sparkle = env.envelopes.high[f];                         // highs drive grain or small glints
```

- Attack about 10 ms and release about 150 ms give a meter-like response; a longer release gives breath, a shorter one gives tic.
- The suggested hits from `audio_envelope.py` are candidates. Listen to them and keep the ones that matter; then they become the piece's `hits`.

## 9. Checks

- `scripts/audio_check.py <track.wav> --plan plan.json` compares audio onsets with the plan's events. Read it as measurement: it does not judge the mix or prove that the piece feels in sync.
- Sync window (ITU-R BT.1359-1, 1998): sound about 45 ms early or 125 ms late starts to be noticed. Keep hit-to-onset offsets well inside that and aim for zero; when a frame must give, let the picture lead by 0–2 frames, because an early sound is noticed sooner (45 ms) than a late one (125 ms).
- Check the final MP4 as well as the WAV: AAC changes peaks and loudness, so a clean WAV can clip after encoding (see [formats-platforms.md](formats-platforms.md)).

## 10. Checklist

- [ ] `bpm` and `lead` are in the plan; every cut refers to a beat number.
- [ ] Beats are computed from the start of the track, never accumulated.
- [ ] Big changes sit on phrase boundaries (8–16 bars in long pieces, 2–4 bars in a reel); small ones on beats.
- [ ] Off-beat cuts have an audible reference.
- [ ] Each drop follows a gap, and lands on a downbeat.
- [ ] Silences are clean, and the picture freezes into them.
- [ ] Shot lengths are whole beat multiples, rounded once.
- [ ] Audio-reactive values come from the precomputed envelope file.
- [ ] Every hit's onset is inside the sync window.

Related: [rhythm-sync.md](../craft/rhythm-sync.md) for the craft of rhythm; [cutting.md](cutting.md) for cut placement in general; [pacing-retention.md](pacing-retention.md) for density and holds; [story-structures.md](story-structures.md) for where the drop sits in a structure; [sound-design.md](../craft/sound-design.md) for pieces with no music; [plan-schema.md](../produce/plan-schema.md) for the `hits` fields.
