# B-roll: footage and photos with their licence, under one grade

Read when a piece uses real pictures: clips, photos, archive, the person's own footage. Motionsmith does not edit long
footage (that is HyperFrames or an editor); it builds short pieces where real pictures carry what the voice does not
say, and puts its type, light and sound over them in one deterministic render.

Tools: `scripts/broll.py` (`ingest`, `shotlist`, `assemble`, `credits`), `scripts/kit/footage.js` (the timeline drawn
inside a piece), `templates/recipes/broll-story` (a runnable piece).

## 1. Provenance before anything

Every file enters through `broll.py ingest`, which copies it into `assets/broll/src/` and records it in
`assets/broll/provenance.json`: source, licence, author, title, sha256, size, duration, whether it is AI-generated.

| Licence | What it asks | Notes |
|---|---|---|
| `own` | Nothing | The person's material; never use theirs unless they handed it over for this piece |
| `cc0`, `pd` | Nothing | Public domain; keep the source anyway |
| `cc-by`, `cc-by-sa` | The credit (`--author`) in the caption or description; SA: share-alike | `broll.py credits` writes the lines |
| `pexels`, `pixabay`, `unsplash` | Their own licences: free use, no resale of the raw file, no implied endorsement | Check the current terms on the site |
| `licensed` | What the contract says | Put it in `--notes` |

- **Ask before downloading.** A licence on a page is a claim: keep the page's URL as the source, and prefer
  collections that state the licence per file (Wikimedia Commons, NASA, Internet Archive's public domain, Pexels,
  Pixabay). Never pull from a search engine's image results.
- No file without a licence goes in; CC BY without an author is refused.
- `--ai` records AI-generated material, so a project that forbids it can check before publishing.

## 2. The shot list comes from the plan

`broll.py shotlist` writes one shot per scene (`assets/broll/shots.json` and a readable `shots.md`). With a voice plan
that is one shot per phrase: the picture changes when the voice turns.

- **The picture adds, it does not repeat.** For «every notification is a small alarm», a phone screen is the literal
  picture; a smoke detector's red light, a hand flinching, or a dog's ear turning is the added one.
- **Mix the scales**: wide (where we are), medium (who or what), detail (what matters). Two wides in a row read as one.
- **Alternate the moves** of stills (the shot list does it: push-in, pan-left, pull-out, pan-right, tilt): two pushes
  in a row feel like a zoom that stalls.
- A scene without a file keeps the piece's own background (a `gap`): fine for a title or a breath.

## 3. Assembling the timeline

`broll.py assemble` conforms every shot to the piece:

| Shot | What happens |
|---|---|
| Clip | Trimmed from its `in` point to the scene's length, at the piece's fps, cropped to cover the frame around `focus` ([x, y] from 0 to 1), one JPEG per frame. Shorter than the scene: the last frame holds, and it says so |
| Still | Resized (up to twice the frame), moved in code by `kit/footage.js` with an eased Ken Burns: sub-pixel smooth, real motion blur on fast pans |
| Still + `fg` | A cut-out PNG with alpha (the foreground, made by hand) travels further than the background: parallax |
| Nothing | A gap |

It writes `assets/broll/timeline.json` and links it as `plan.broll`. In the piece, `Stage.run({prepare})` loads only
the frame each seek needs, so the render stays deterministic and memory stays flat. Frames weigh about 250 KB each at
1080×1920: delete `assets/broll/frames/` after the final render. Render these pieces with `render_stream.mjs` or
`render_parallel.mjs`; inside a HyperFrames film, let HyperFrames carry the footage and give it Motionsmith's type as a
clip ([HyperFrames](../produce/hyperframes.md)).

## 4. One grade for every source

Clips from three cameras and two photo archives look like five films. `timeline.json → grade` applies one look to all
of them, in the piece: `contrast`, `saturate`, `brightness`, `warmth` (a warm or cool cast, soft-light) and `lift`
(lifted blacks). Then the stage's grain and vignette sit over everything, footage and type alike.

- Grade toward the brand's palette, not toward "cinematic": a desaturated base lets the accent colour own the frame.
- Check the darkest and the brightest shot together on one sheet: the grade must hold both.
- Burned-in captions need the lower-third gradient and a soft shadow on bright footage; `broll-story` does both.

## 5. Cuts on footage

- Cut on movement inside the shot, or on the voice's breath ([cutting](cutting.md), [voice-over](voiceover.md)).
- At a cut, every motion-blur sample of the frame belongs to the new scene: choose the scene from the frame
  (`Math.floor(t * FPS)`), never from the sub-sample time, or a ghost of the old picture shows on the cut frame.
- Footage carries its own motion blur: the kit draws the same footage frame for every sub-sample of a frame and blurs
  only what moves in code (the still's Ken Burns, the type).

## 6. Review

`sample_frames.mjs --cuts` (both sides of every cut: no ghost, no wrong shot), a full-size crop of the brightest shot
under the captions, a sheet with one frame per shot (one grade?), and `broll.py credits` before publishing.

## Sources

Licence terms: Creative Commons licence deeds (creativecommons.org/licenses), the Pexels, Pixabay and Unsplash
licence pages. Shot scales and cutting on movement follow standard documentary practice; Walter Murch, *In the Blink of
an Eye*, for cutting on the breath.
