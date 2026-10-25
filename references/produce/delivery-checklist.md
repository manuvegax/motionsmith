# Delivery checklist

Run before telling anyone a piece is ready. Platform specifics (sizes, safe zones, durations, loudness) live in
[formats & platforms](../edit/formats-platforms.md); the review steps in the [review protocol](review-protocol.md).

## 1. The file

| Check | Expected | How |
|---|---|---|
| Size and aspect | The plan's `width` × `height` | `verify_export.py --width … --height …` |
| Cadence | The plan's fps, constant | `verify_export.py --fps … --require-cfr` |
| Duration and frames | `duration_frames / fps`, exact frame count | `verify_export.py --duration …` |
| Codec | H.264 yuv420p (or ProRes 4444 / WebM alpha for overlays) | Render report |
| Colour | BT.709, limited range, tagged | `verify_export.py --require-bt709` |
| Quality | CRF 14 (18–20 for heavy texture); no banding or blocks in the darkest gradient and finest text | One or two full MP4 frames at 100 % |
| Fine textures | No moiré when scaled to 720 wide | `ffmpeg -vf scale=720:-2` on a frame |
| Platform re-encode | Grain, halftone and small text survive about 4 Mbps | [formats §7b](../edit/formats-platforms.md#7b-survive-the-platform) |
| Fast start | Index at the front | Set by `render_stream.mjs` |
| Weight | Reasonable for the destination (phone transfer, upload limits) | File size in the report |

## 2. Sound

| Check | Expected | How |
|---|---|---|
| Loudness | The profile's target (default −16 LUFS integrated) | `audio_check.py` on the MP4 |
| Peak | ≤ −2 dBTP in the WAV; ≤ −1.0 dBTP in the AAC file | `audio_check.py --max-true-peak -2` on the WAV, default on the MP4 |
| Sync | An attack within −45/+125 ms of each hit | `audio_check.py --plan plan.json` |
| Phone | Energy above 120 Hz carries the piece; mono fold loss ≤ 4.5 dB | `audio_check.py` warnings and notes |
| Edges | Fade-in, last sample at zero | `audio_check.py` |

## 3. Reading and safe areas

- Every line of text at phone size, with its last character, inside the platform's safe area.
- Reading budget from the first sharp frame ([kinetic type](../craft/kinetic-typography.md)).
- Faces, logos and essential text not covered by the platform interface.

## 4. Direction

- The dense review done, every sheet looked at; the three critics passed with evidence.
- The project and personal profiles respected (palette, type, curves, "never" rules).
- The first frame moves; no dead stretch; the ending keeps the new relation; a loop seam checked if it loops.

## 5. The message

Say, in the person's language:
- the file path, resolution, fps, duration, audio, size;
- what was checked and how (determinism, dense review, export, audio);
- the limits: what only the person can judge (real-speed playback, listening, taste on the target device);
- what was archived or moved, and where.

Never promise reach, virality or automatic publishing; publishing is the person's decision.
