# Talking-head edits: a person to camera, with inserts, right in version one

Read when someone hands over a recording of themselves (or a client) talking to camera and wants a short-form edit:
cuts, captions, inserts, B-roll, sound. This guide is the order of work and the checks that matter. It is general:
the person's taste (palette, caption style, B-roll look) lives in their profiles and wins over every default here.

Why it exists: an 85-second reel edited without this order took ten versions. Every rejection was predictable: a
look discovered by trial and error, a frame of the speaker looking down, the last word cut, a stale render delivered,
a voice decorrelated by the speed change, an opening with nothing moving. Each section below closes one of them.

## 1. Load the whole toolchain at once

When HyperFrames hosts the film, load its skills together in the first message, not one at a time as problems show
up: the entry skill (render contract), core (composition), CLI (lint, snapshot, render), animation, keyframes (camera
punches, masks, drawn strokes), audio, registry (ready-made blocks before hand-building), `media-use` (footage
treatments, cut-outs, transcripts) and any talking-head or recut skill installed. Add the speech-to-text and voice
isolation tools the person uses (say the credit cost first when they are paid). Motionsmith brings the craft, the
taste profiles and the review.

## 2. Ask once, then build

One message, at most three groups of questions: the version's job (main post or a trial/test variant), the footage
or images the person supplies for B-roll, and anything that must not change. Then write a one-page edit brief in the
piece folder: the opening (§4), one line per spoken sentence (face, type insert, B-roll, lower third), palette, speed.
Show only finished work.

## 3. The pipeline

| Step | Do | Check |
|---|---|---|
| 1 Cut | Transcribe; take the best take of each sentence; remove fillers and repeats. Leave breath: about 0.18 s before each sentence and 0.26–0.42 s after, by punctuation. Never trim pauses inside a sentence: it reads as words glued together | Listen to every seam |
| 2 Grade | One grade for the whole recording; from HDR phones, a soft tone map before any look | One frame per take side by side |
| 3 Voice | Isolate if the room is noisy; gentle EQ; keep the voice **mono** and identical in both channels; never lay a room-tone or noise bed under an isolated voice | Silence floor, spectrum, no added hiss |
| 4 Words | Word timings from speech-to-text; **measure the last word in the waveform**, not in the transcript (transcripts misplace word ends) | The tail of the final word is above the noise floor |
| 5 Gaze | Score every frame of the face: eyes down, blink, eyes to the side (`scripts/gaze_check.py`); calibrate to the person (heavy lids are not "looking down") | A strip of faces around each flagged run |
| 6 Plan | Cover every run of eyes-down with an insert; no stretch of face shorter than 0.4 s between inserts (it flickers); eyes open on the first 3 frames of face after an insert and the last 2 before one | The generator refuses to write if a visible face frame fails |
| 7 B-roll | Treat every picture with one finish so footage, photos and generated clips belong together (§5) | One frame per shot on one sheet |
| 8 Compose | Inserts start on a frame boundary with their first line already on screen (never an empty first frame); an insert that spans a cut-out silence lasts to its end in output time | Lint clean |
| 9 Review | Snapshot six frames around every seam (−2…+3) plus one per second; mark the platform's unsafe zones; read every sheet **before** rendering | `contact_sheet.py` or the HyperFrames snapshot |
| 10 Render | One render per version; never two at once; delete the previous output and log first so a wait cannot read a stale "complete" | A frame of a known insert pulled from the final file |
| 11 Mix | From lossless stems: voice mono with a time-domain stretch (`atempo`) if the edit is sped up, music separately, effects at their new times, loudness in two passes, **one** encode | `audio_check.py`; left/right correlation > 0.95; zero clipped samples |
| 12 Verify | Loudness and true peak, a full transcription diffed against the script, the last word plus ≥ 0.8 s of face after it, the first frame (not black, a word within 0.5 s), gaze and blinks on the final file | `verify_export.py` + the gaze check on the MP4 |

Two speed-change traps: stretching an already mixed stereo file with a per-channel pitch-preserving stretcher can
leave left and right nearly opposite (the voice half-cancels on a phone speaker), and down-mixing a stereo WAV with
`-ac 1` sums the channels (+3 dB) and clips. Read one channel (`pan=mono|c0=c0`) and stretch the mono voice.

## 4. The first three seconds

Viewers decide in about three seconds; a black screen with a small line of type at the top loses most of them.

- Frame 0 says who and what happened: a face with a short lower third, or the strongest image, never a slow fade.
- A different image about every 0.8 s across the first five seconds (face → quote over a reacting crowd/chat → a
  full-bleed colour card → a crossed-out word → the first B-roll), each change with its sound.
- A camera hit on frame 0 (stepped scale, a brief flash) and a hit plus a sub layer in the sound.
- No blink in the first second: if the take has one, hold an eyes-open frame inside the opening camera hit.
- A trial variant gets a different opening, order and palette, not the same edit with a new title.

## 5. B-roll that belongs: one finish, many methods

Pick a finish once per person or series and apply it to every insert; vary the method, not the finish.

**Finish example: screen print with frame-rate lag** (`scripts/print_footage.py`): two inks with a halftone fixed to
the screen, misregistration that boils on twos and jumps on keywords, a paper texture, footage stepped to 15 fps while
the camera above stays fluid ([print & textures](../craft/print-textures.md), [stepped time](../craft/stepped-time.md)).
Other finishes that work the same way: photocopy, risograph, cyanotype, VHS ([retro looks](../craft/retro-looks.md)).

| Method | When | How |
|---|---|---|
| A supplied or licensed clip | A visual metaphor of the sentence | Chosen per sentence, not all of them; treated with the finish |
| A crop of the speaker's own eyes | Lines aimed at the viewer | A band of the face, enlarged, photocopy, a scanner bar |
| The speaker's silhouette | The person under something happening (a crowd laughing, a door of light) | Background removal, filled, rim light |
| A negative of the take | A dark turn | Inverted greyscale |
| A held frame | Hide a blink or freeze a moment under a hit | A still inside a stepped camera move |
| A cold type insert | The line that must be read | Two faces (serif italic + heavy caps), one coloured keyword |
| A full-bleed colour card | A one-second hit in the opening | Accent colour to the edges, ink type |
| A crossed-out word | Negating something | Big word, a marker stroke drawn in steps, a strike sound |
| A live chat | Mockery, a crowd, "on stream" | Generic usernames in colours, messages pushing up |
| A typed card | Quoting what someone wrote | Monospace, cursor, one coloured phrase, a signature |
| A kinetic lower third | Long face stretches without covering the face | Gradient, stepped landing, an underline stroke |
| A stepped reframe | Punctuate an idea | Scale on `steps(3)`, the take at 15 fps for 0.45 s, a felt sub |

Over every picture: registration marks, a colour bar and marker strokes (circle, arrow, underline, corners, box,
strike) drawn when the word is said ([editorial collage](../create/editorial-collage.md)).

## 6. Pace without sounding robotic

Dense edits can tip into mechanical. Things that made a dense talking-head edit feel robotic:
- reframes on a clock (every N seconds) instead of on meaning (a new idea, a feeling, a gesture); vary the lengths;
- a global speed-up that also shortens the breaths; prefer removing silence and keeping 1.05–1.08×;
- text on screen almost all the time; leave stretches of plain face looking at camera;
- heavy processing on an isolated voice; less EQ often sounds more human.

## 7. Process that saves tokens and renders

- A new video starts in a new session that loads this guide and the profiles; knowledge lives in files, not in the
  conversation history.
- Decide in the brief, review on the composition, render once, verify the file, then show it.
- Do not change what the person approved because a review suggested it; ask.
- Close each piece by writing its approvals and rejections, with the person's words and the date, into the profile.
