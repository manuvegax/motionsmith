# Review protocol: dense review and the three critics

Read before calling a stretch or a piece finished. Contact sheets every 1–2 s missed every serious defect in
production; the steps below found them. The goal is **right first time**: the person never sees a version that
had not passed this.

## 1. What each step found

| Step | Defect found |
|---|---|
| A dense 0.1 s window around a docking | A glass ring almost vanished: shadows wrote depth and hid it |
| The same instant without blur | A white ring during a push was not blur: it was HDR plus bloom on light paper |
| A full-size crop | The rectangle of a photo showed through the glass; colour fringes in the macro |
| A dumped trajectory | A spring arrived 0.5 s before its cue |
| A frame without blur | A tilted print was clipped by the background grid |
| A full MP4 frame in the darkest gradient | Ruled out 8-bit banding in a vignette |
| Audio band balance | 71 % of the energy sat below 60 Hz, inaudible on a phone |
| RMS per segment | The "vacuum" before the reveal was −18 dB, not silence |
| A sheet of 18 instants | Text drawn at 11 px on a small canvas was unreadable |
| An enlarged crop | "Smudges" were eyelashes in the photo: a false alarm, nothing touched |
| `determinism_check` on a new template | An accumulator never cleared: the frame changed when seeking back |
| A walk every 0.5 s of an approved piece | 1–1.5 s holds where the frame barely changed: why viewers left |

The false alarm matters as much as the rest: **zoom in before fixing**.

## 2. The dense review, in order

Needs a composition with the capture contract ([pipeline](pipeline.md)). `<piece>` is the folder with `index.html`;
`<tmp>` a new folder.

0. **Determinism**. Without it nothing else is comparable.
   `node <skill>/scripts/determinism_check.mjs --root <piece> --font "400px MyFont" --report <piece>/preview/determinism.json`
1. **Full walk** every 0.5 s: composition, complete text, safe area, material jumps between scenes, **and stillness**
   (two consecutive samples that look the same = a hold to animate).
   `node <skill>/scripts/sample_frames.mjs --root <piece> --out <tmp>/walk --every 0.5`
   `python -I <skill>/scripts/contact_sheet.py <tmp>/walk --out <tmp>/walk.jpg --cols 8 --tile 168`
1b. **One frame per beat** when the plan has a tempo (`bpm`), or one per hit: the grid is where the piece is
   supposed to change, so look there first. Fix anything off-grid, cluttered, overlapping or hard to read.
   `node <skill>/scripts/sample_frames.mjs --root <piece> --out <tmp>/beats --beats --beat-offset 0.05` (or `--bars`, `--hits`)
   `python -I <skill>/scripts/contact_sheet.py <tmp>/beats --out <tmp>/beats.jpg --cols 8 --tile 168`
2. **Dense windows** around every cut, transition, hit and docking (±0.3 s, step 0.05–0.1 s, or exact frames with
   `--frames`): elements vanishing, occlusions, half-arrived layers, text before its cue.
3. **Without blur**, the same peaks with `--noblur`. If the defect stays, it is geometry, material or depth, not
   exposure. If it goes, check shutter, weights or samples.
4. **Full-size crops** of material at its closest zoom: glass, cut-out edges, glyphs, halftone dots.
   `python -I <skill>/scripts/contact_sheet.py <tmp>/peaks --out <tmp>/glass.jpg --crop 140,800,800,800 --tile 520 --cols 2`
5. **Data**: expose the state function (trajectory, spring, cue) on `window` temporarily and dump it with
   `dump_state.mjs`; check things arrive when they should; remove the hook before rendering.
6. **A proxy of the hardest stretch**, with its audio, before the full render:
   `node <skill>/scripts/render_stream.mjs --root <piece> --out preview/proxy.mp4 --start 6.4 --end 8.8`
7. **The exact file**: `verify_export.py --require-cfr --require-bt709` (and `loop_check.py` when the plan says
   `"loop": true`), then open one or two full MP4 frames: the
   darkest gradient (banding) and the finest text (compression blocks); for fine textures, a 720-wide downscale (moiré).
8. **Audio**, on the WAV and again on the MP4 (AAC moves the peak):
   `python -I <skill>/scripts/audio_check.py <piece>/final/x.mp4 --plan <piece>/plan.json --spectrogram <piece>/preview/spectrogram.png --report <piece>/preview/audio-check.json`
   Read the spectrogram: sync warnings are candidates, not verdicts.

Rules: **look at every sheet** (open it; generating it is not reviewing). After a fix, repeat only the affected steps
and neighbouring links. Delete frame folders after looking (they fill disks); keep cited evidence in `preview/`. A
sheet finds defects; it does not prove smoothness, rhythm or sound.

## 3. The three critics

After the dense review and before showing anything, run three independent critiques, each as if it were a different
person who did not build the piece. Write each verdict with evidence (frame times, crops), not adjectives.

| Critic | Asks | Blocks the delivery when |
|---|---|---|
| **Art director** | Is there one idea, the brief's `concept`? Does every state serve it? Is it distinctive or interchangeable with a template? Does anything on the banned list or the [AI tells](../create/motion-brief.md#3-the-banned-list) appear (glow without a source, a burst from nowhere, a crossfade, bounce on everything, corner text, a generic gradient)? Hierarchy, palette, type, matter, the ending's new relation | It is generic, a banned item appears, the hierarchy is broken, the brand/profile is violated, the ending loses the transformation |
| **Editor** | Does the first frame move? Any hold > ~0.5 s without an inner change? Does every cut have a job and land on the grid? Reading budgets? Payoff placement (the strongest moment where the brief put it), loop seam, density curve? | Dead stretches, text too fast, cuts without motive or off the grid, a late or missing payoff, a loop that jumps |
| **Technician** | Determinism, cadence, BT.709, loudness and sync, blur sampling, no ghosts or clipped glass, safe areas, file weight | Any failed check, any unverified requirement presented as passed |

Fix what they find, re-run the affected steps, then show. If a critic's finding is wrong, say why in the review notes.
When the person rejects something anyway, their verdict wins and goes into the profile.

## 4. What to look for in each kind of moment

| Moment | Look at |
|---|---|
| A cut | The last frame of A and the first of B: nothing vanishes halfway, no layers in different states |
| An object arriving | Dumped trajectory, overshoot and the exact arrival frame; shadow and contact |
| A macro or a camera entering | A full-size crop: asset resolution, reflections, fringes, edges |
| Text landing | First sharp frame, accents and descenders, ink box vs advance width |
| A hit | Frames −1/0/+3: the accent happens on the hit and decays |
| A reading hold | At least one inner change per ~0.5 s that does not hurt reading |
| A dark background or gradient | A full MP4 frame at 100 %: banding and blocks |
| A low-resolution canvas (retro) | Final text size in pixels and reading at phone size |

## 5. What this protocol cannot cover

Real-speed playback, listening and taste on the target device. Say so in every delivery and ask the person to judge
those; record their words in the profile. Log each defect as error → cause → fix → evidence in the piece's learning log.
