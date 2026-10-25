# Formats and platforms

Sizes, durations, safe zones, loudness, codec, colour tags and frame rate for the places a piece is shipped. Read it before a piece is composed (the frame size and safe zones change the layout), and again before export.

**Source note.** The platform values here come from third-party 2025–2026 spec guides, not from the platforms' own documentation. Where the guides disagree, the value is marked **(verify)**. Check each platform's help centre before a release, and update this file when a value changes.

## 1. Master rule: compose once, export many

- Compose at the largest format you ship, and keep the safe zones of every other format in the same frame. A 9:16 piece with 1:1 deliverables needs its key text inside the 1:1 frame too.
- Render at the highest quality the piece needs (1080 on the short side is the working standard), then export each format from that master.
- The frame size is part of the plan: write `width`, `height`, `fps` and the safe band into the plan, not into the scene code.

## 2. Vertical short-form: Reels, TikTok, Shorts

| Platform | Frame | Length | Frame rate | Codec and audio | Safe band (1080 × 1920) |
|---|---|---|---|---|---|
| Instagram Reels | 1080 × 1920 (9:16) | Sources disagree: 90 s in-app; longer uploads (verify) | 30 minimum; 60 supported (verify) | H.264 High, AAC-LC, MP4 or MOV | Keep text in the band below (verify per platform) |
| TikTok | 1080 × 1920 (9:16) | Up to 10 min by API; longer in the app (verify) | 30 common; 60 for high-motion source (verify) | H.264, AAC-LC, MP4 | Bottom 400–480 px and right 120–150 px covered by UI (verify) |
| YouTube Shorts | 1080 × 1920 (9:16) | Up to 3 min (since October 2024) (verify) | 30 or 60 (verify) | H.264, AAC-LC, MP4 | Keep text clear of the title and button overlay (verify) |

- **Two zones for vertical formats** (1080 × 1920):
  - **Working safe area** (what `new_piece.py --format reel` writes into `plan.json`): x 80–930, y 220–1440, that
    is 80 px left, 150 px right for the button column, 220 px top and 480 px bottom for the caption and the account
    name. Titles and captions live here. `--format story` uses x 60–1020, y 250–1580 (fewer overlays).
  - **Conservative band** for the one line that must survive every interface: y 300–1240 px with 120 px side
    margins, the widest margin among the sources (verify). Use it for the hook line and the payoff when a piece
    ships to several platforms.
  A project profile (`MOTIONSMITH.md`) can set its own measured values; they win over these.
- Edge entries and full-bleed backgrounds may run through the margins; only text, faces and what must be read stay in the band.
- A vertical piece that opens with a caption at the bottom edge is covered on most platforms. Put the first caption in the band.

## 3. Horizontal and square: YouTube, LinkedIn, X

| Platform | Frame | Length | Frame rate | Notes |
|---|---|---|---|---|
| YouTube 16:9 | 1920 × 1080 (or 3840 × 2160) | No short limit for long-form (verify) | 24–60 | Keep titles inside the central 80 % (practice) |
| LinkedIn feed | 1:1 1080 × 1080; 4:5 1080 × 1350; 16:9 1920 × 1080; 9:16 (verify) | 3 s to 10 min; some guides say 15 (verify) | 30 | Under 2 min performs better in the sources, not a platform rule (verify) |
| LinkedIn ads | 1:1, 4:5, 9:16, 16:9 | 3 s to 30 min (verify); 15–30 s suggested | 30 | File limit 200 MB or 500 MB by source (verify) |
| X (Twitter) | 16:9 1280 × 720 recommended (1920 × 1080 accepted); 1:1 720 × 720 recommended; 9:16 720 × 1280 recommended (verify) | About 2 min 20 s for standard accounts (verify) | 60 or less | MP4 or MOV, H.264 High; file 512 MB by source (verify) |

## 4. Ads by ratio

| Ratio | Typical placements | Size | Length guidance | Notes |
|---|---|---|---|---|
| 9:16 | Stories, Reels, vertical feeds | 1080 × 1920 | 6 s bumper to 30 s | Safe band as in section 2 |
| 4:5 | Feeds (Meta, LinkedIn) | 1080 × 1350 | 15–30 s | Often the best feed ratio (practice) |
| 1:1 | Feeds, carousels, X | 1080 × 1080 | 15–30 s | Keep the subject centred |
| 16:9 | Video feeds, YouTube ads, X | 1920 × 1080 | 6, 15 or 30 s (verify per placement) | Skip buttons may appear after about 5 s (verify) |

- Meta sources recommend exporting three files (9:16, 4:5, 1:1) to cover most feed and story placements (verify). Meta's limits in the sources: MP4 or MOV, H.264, a 4 GB ceiling; Stories up to 60 s per card and Reels up to 90 s (verify).
- The hook of a paid placement should land in the first 1.5 s (practice; see [pacing-retention.md](pacing-retention.md)).
- Ad rules (ratios, text amount, claims) are set by each platform and change; check the current ad policy before a campaign (verify).

## 5. Safe zones at a glance

| Format | Frame | Text band (y) | Side margin | Source |
|---|---|---|---|---|
| 9:16 vertical | 1080 × 1920 | Working 220–1440 px; conservative 300–1240 px | 80 px left, 150 px right; conservative 120 px | `new_piece.py` defaults; conservative band is the widest of the sources (verify) |
| 4:5 feed | 1080 × 1350 | Top 10 %, bottom 15 % free: 135–1147 px (practice) | 60 px | Practice; verify. `--format portrait` |
| 1:1 feed | 1080 × 1080 | Top and bottom 8 % free: 86–994 px (practice) | 60 px | Practice; verify. `--format square` |
| 16:9 | 1920 × 1080 | Central 80 % for titles: 108–972 px (practice) | 10 % (192 px) | Practice. `--format landscape` |

## 6. Loudness

| Target | Value | Basis |
|---|---|---|
| Motionsmith default | Integrated −16 LUFS; true peak ≤ −1.5 dBTP in the WAV, ≤ −1 dBTP in the MP4 | The default of `build_soundtrack.py`, the sound template and the delivery checklist: AAC raises peaks, so the WAV keeps 0.5 dB more room ([sound design](../craft/sound-design.md)) |
| Social short-form, louder | Integrated about −14 LUFS; true peak −1 dBTP | Common target in the guides and in streaming normalisation (verify per platform). Platforms normalise anyway; −16 to −14 is the safe range. Set it in a profile (`build_soundtrack.py --lufs -14`) |
| Broadcast reference | Integrated −23 LUFS; true peak −1 dBTP | EBU R 128 |

Measure and normalise with FFmpeg:

```
ffmpeg -i export.mp4 -af ebur128=peak=true -f null -
ffmpeg -i mix.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 48000 mix-norm.wav
```

- Measure the final MP4, not only the WAV: AAC changes the peaks and the loudness. `scripts/audio_check.py` reports loudness and sections for the WAV and for the muxed video (see [music-editing.md](music-editing.md)).
- Keep the true peak at or below −1 dBTP. A true peak above 0 dBTP clips after the platform re-encodes.

## 7. Codec, colour tags and frame rate

| Setting | Value | Why |
|---|---|---|
| Container | MP4 with `+faststart` | Plays before the whole file downloads |
| Video | H.264 High profile, 8-bit 4:2:0 (`yuv420p`) | Accepted everywhere listed above |
| Audio | AAC-LC, stereo, 48 kHz | The sources list AAC-LC for every platform (verify) |
| Colour primaries, transfer, matrix | BT.709 | The picture is SDR, graded for BT.709 |
| Range | Limited (`tv`) | Standard for delivery |
| Frame rate | Constant (CFR); 30 or 60 | Pick per platform; 60 keeps fast motion cleaner where it is accepted (verify) |

The colour tags must be written into the file, not only assumed:

```
ffmpeg -framerate 60 -i frames/%06d.png -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:v libx264 -profile:v high -crf 14 -preset medium -movflags +faststart out.mp4
```

- `scripts/render_stream.mjs` pipes frames into FFmpeg and writes these BT.709 tags itself (with `--crf` and `--preset` for the encode). Prove it on the file: `scripts/verify_export.py --require-bt709 --require-cfr`.
- An untagged export is read with a different colour matrix, and saturated colours shift. In one test, a saturated red (#ff422e) came back as about (255, 81, 40) until the tags were written. See [color-grade.md](color-grade.md), section 3.

## 7b. Survive the platform

- **The re-encode.** Every platform re-encodes the upload at a far lower bitrate than a CRF 14 master. Grain that
  changes every frame, halftone dots and fine grids eat that bitrate first and come back as blocks or mush. Before
  sign-off, simulate it and look at the darkest gradient, the finest text and the textures at 100 %:

  ```
  ffmpeg -i final/piece.mp4 -c:v libx264 -b:v 4M -maxrate 4M -bufsize 8M -preset medium -c:a copy preview/platform-sim.mp4
  ```

  4 Mbps is a working guess for 1080 × 1920 short-form (verify). If the texture dies: make the grain coarser (a 2–3 px
  structure), step it at 12 fps instead of every frame, or lower it where there is text.
- **60 fps master, 30 fps playback.** When the platform or the device plays 30 fps, every other frame of a 60 fps
  master is dropped and a 180° shutter becomes an effective 90°: fast moves strobe. For 30 fps delivery render at 30
  with 180–270°, or keep 60 with 270–360° so each kept frame carries enough smear.
- **Cover and grid.** The profile grid shows a crop of the cover (3:4 on Instagram since 2025; verify). Keep the
  cover's title inside the central 1080 × 1440 of a 1080 × 1920 frame, and choose a cover frame where it is settled
  and sharp.

## 8. Delivery matrix

| Format | Size | Length target | Rate | Loudness | Tags |
|---|---|---|---|---|---|
| Vertical short-form | 1080 × 1920 | 15–30 s (practice) | 30 or 60 | −16 (to −14) LUFS, ≤ −1 dBTP | BT.709, tv |
| Feed square | 1080 × 1080 | 15–30 s | 30 | −16 (to −14) LUFS | BT.709, tv |
| Feed portrait | 1080 × 1350 | 15–30 s | 30 | −16 (to −14) LUFS | BT.709, tv |
| Landscape | 1920 × 1080 | As the piece needs | 30 or 60 | −16 (to −14) LUFS | BT.709, tv |
| Ad bumper | 1080 × 1920 | 6 s | 30 | −16 (to −14) LUFS | BT.709, tv |

## 9. Checklist

- [ ] The master is composed with every target's safe band in frame.
- [ ] Text sits inside the band of every format it ships in.
- [ ] Length is inside the platform's limit for the format (verify on the day of upload).
- [ ] Loudness measured on the MP4: integrated at the profile's target (−16 LUFS by default, −14 if chosen), true peak at or below −1 dBTP.
- [ ] Codec H.264 High, yuv420p, AAC-LC 48 kHz.
- [ ] Colour tags written: bt709 primaries, transfer and matrix; range tv.
- [ ] Frame rate constant, and the same as the plan's `fps`.
- [ ] The export decodes fully and its frame cadence is right.
- [ ] Textures and small text survive a simulated platform re-encode (section 7b).

## 10. How to check

- Verify the stream and the cadence with `scripts/verify_export.py` (run it with `--help` for its arguments). It checks the stream expectations, the frame cadence and that the whole file decodes. It does not judge quality.
- Confirm the tags with `ffprobe -v error -select_streams v:0 -show_entries stream=color_space,color_primaries,color_transfer,color_range,width,height,r_frame_rate -of default=nw=1 export.mp4`.
- Measure the loudness with the `ebur128` command in section 6.
- Check the safe band on a frame: sample the first caption and the last title with `scripts/sample_frames.mjs`, and look at the contact sheet with the band drawn over it.
- Before a release, check each platform's own specification page, and update the table above with the date you checked.

Related: [delivery-checklist.md](../produce/delivery-checklist.md) for the full release list; [overlays-alpha.md](../produce/overlays-alpha.md) for exports with transparency; [captions-titles.md](captions-titles.md) for placement inside the band; [color-grade.md](color-grade.md) for the colour pipeline; [music-editing.md](music-editing.md) for the audio check; [pipeline.md](../produce/pipeline.md) for where the export sits in the flow.
