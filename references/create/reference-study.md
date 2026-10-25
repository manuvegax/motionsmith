# Reference study: operations, not images

A reference shows how someone achieved an effect. This file is the method for measuring what can be measured,
writing down what cannot, and building your own version. The output feeds [ideation](ideation.md), the
[style atlas](style-atlas.md) and [scene recipes](scene-recipes.md). The tools are in `scripts/`.

## 1. The rule

- **Take an operation:** what moves, what it reveals, how long it takes, how the camera relates to the object,
  where the eye is led.
- **Never take material:** frames, footage, music, logos, copy, a person's likeness or voice, or a layout that
  identifies a brand or a creator.
- **Your output** applies the operation to your own content and material, and proves it with your own timings.

## 2. Evidence levels

Say what you proved, and at which level. Never carry a conclusion above the level you reached.

| Level | What you can state | What is still missing |
|---|---|---|
| Technical | codec, size, fps, frame count, duration | direction, reading, sound |
| Measured images | differences, flow, candidate cuts, with units and times | that a candidate is a real cut; what the action is |
| Reviewed frames | composition, crops, text and states in named frames | continuity and rhythm between the samples |
| Watched in time | actions and links seen at real speed, in the intervals you played | sound; segments you did not play |
| Heard | intelligibility, contact, silence, mix | the visuals you did not review |
| Judgement | the operation shown, with the intent it serves | the owner's approval; any performance you did not measure |

Write the scope with the conclusion: "720 frames decoded", or "watched 4.1–4.7 s at real speed". Avoid words
such as "photographic", "After Effects", "smooth" or "perfect" unless visual evidence backs them.

## 3. Observed, inferred, own application

For each study, fill one row per operation:

| Source and time | Observed | Own application | Proof times | Not proven |
|---|---|---|---|---|
| Reference A, 1.10–1.90 s | a blurred foreground element partly hides the subject | an occluder hands the object over to the next state | 1.15, 1.36, 1.62 s | the easing, the lens, the audio |

Put the same row in the plan as `reference_evidence` ([plan schema](../produce/plan-schema.md)):

```json
{
  "reference_evidence": [{
    "source": "reference A, 1.10–1.90 s",
    "observed_operation": "a blurred foreground element partly hides the subject",
    "own_application": "an occluder hands the object over to the next state",
    "proof_times": [1.15, 1.36, 1.62]
  }]
}
```

Keep "Observed" as a description of what is on screen, and "Inferred" as a separate, labelled claim.

## 4. Dense sampling

Sample in this order. Each step decides where the next one looks.

1. **Overview.** 16–24 evenly spaced samples. The sheet shows the structure, not the motion.
2. **Cut candidates.** A scene threshold finds likely cuts. Confirm each one by eye.
3. **Transitions and links.** Samples every 0.05–0.1 s over ±0.3 s around each cut, morph, hit or link.
4. **Peaks.** The frame of highest motion. If you have your own version, compare it with and without blur.
5. **Real-size crops.** The smallest edge or glyph at 100 % zoom.
6. **Watch at real speed.** The tools do not play or hear the reference. You have to watch it, and say so.

```bash
python -I scripts/inspect_video.py "ref.mp4" --out "study/ref-overview" --samples 24 --scene-threshold 0.3
python -I scripts/inspect_video.py "ref.mp4" --out "study/ref-window" --times 1.10,1.15,1.20,1.25,1.30
python -I scripts/watch_reference.py "ref.mp4" --out "study/ref-measure" --analysis-size 180x320 --strip "1.0:2.0:0.1"
```

Use `-I` with Python whenever the file came from outside your machine. Run `--help` on each script for the
current flags. The `--out` folders must be new or empty: the tools never overwrite a study.

Frame folders take space. Delete them once you have looked at them, and keep only the frames you cite, in the
piece's `preview/` folder.

## 5. Keep observation, inference and limits apart

For each study, write three lists:

- **Observed:** a time and what is visible. "2.4 s: the ring leaves the frame on the left."
- **Inferred:** a claim you could not measure, marked as such. "Probably a fast ease-out, consistent with the
  overshoot at 2.6 s."
- **Not known:** what the samples cannot show. Easing, software, plugin, sound, the frames between samples.

Measured values can be stated as measured: frame counts, durations, cut times after you verify them, and
pixels per exposure for a motion you know the speed of. The watch tools do not identify the software or the
easing, so do not claim either from a video.

## 6. Turning a study into a brief

- Keep at most three operations per study.
- Each operation becomes a scene recipe ([scene recipes](scene-recipes.md)) or a style decision
  ([style atlas](style-atlas.md)).
- The proof times become the checks for your own version: if the reference's operation is visible at 1.36 s,
  your version must show its equivalent at a time you chose and can test.
- Do not transfer the reference's text, promotion, or closing card, even when its structure is good.

## 7. The tools

| Tool | What it does | Key flags | What it does not do |
|---|---|---|---|
| `scripts/inspect_video.py` | timed sheet and a JSON report for a local video, with candidate cuts | `--out` (new or empty), `--samples 2–200` (default 16), `--times a,b,c`, `--scene-threshold 0–1` | play, listen, or identify software; needs `ffmpeg` and `ffprobe` on the PATH |
| `scripts/watch_reference.py` | streams the whole file; measures differences, histograms and flow; writes metrics and a strip | `--out` (new or empty), `--analysis-size 180x320` or `270x480`, `--strip START:END:STEP` (at most 64 thumbnails), `--max-frames` (marks the pass as limited) | show physical speed or depth; see or hear; export frames |
| `scripts/sample_frames.mjs` | samples **your composition** at chosen instants | `--root`, `--out`, `--every`, `--window a:b:step`, `--times`, `--frames`, `--noblur`, `--png` | sample a reference video |
| `scripts/contact_sheet.py` | tiles a folder of frames into one sheet | `--out`, `--cols` (default 6), `--tile` (default 225), `--crop x,y,w,h`, `--title` | judge rhythm or smoothness |

Limits to keep in mind:

- `watch_reference.py` measures how the image changes. Flow gives appearance correspondences in analysis
  pixels, not velocity. A flash can trigger the cut detector.
- `watch_reference.py` needs OpenCV (`cv2`) and NumPy. `inspect_video.py` needs `ffmpeg` and `ffprobe` on the PATH.
- A decode that finishes does not certify the file. Run `verify_export.py` on it separately.
- A contact sheet finds defects. It does not show smoothness, rhythm or sound. Those need real-speed viewing.

## 8. Licensing and ethics checklist

- [ ] **Ask before downloading.** State the file, its source and its size, and wait for the owner's yes.
- [ ] **Record provenance** for every reference and asset: source URL, date, licence, and local path.
- [ ] **Check each asset's licence** on its own. A clip found online is not automatically free to reuse.
- [ ] **Keep reference material out of the final render**: frames, music, logos, copy, voice, likeness.
- [ ] **Do not infer authorship** from a file name, and do not identify a font or a plugin from its appearance.
- [ ] **Adapt the operation and change the content.** Say which operation you took, and where it came from.
- [ ] **Do not redistribute** the reference file, and do not publish its frames as evidence beyond the study.
- [ ] **Delete the frame folders** after review. Keep only what you cite.
