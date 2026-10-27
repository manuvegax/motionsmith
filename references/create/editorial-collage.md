# Editorial collage: the After Effects language of documentary motion graphics

Read when a piece should look made in After Effects by a motion designer, not generated: explainers, essays, narrated
reels, brand stories, B-roll under a voice. This is the look of most editorial reels that travel well: real objects
cut out on paper, a phrase set in mixed weights with one red word, a figure out of focus behind it, a printed page in
macro with one line highlighted, cards with pins, a ribbon sweeping across, a cut to black with a glow. The kit is
`scripts/kit/collage.js`; the runnable recipes are `editorial-collage` and `broll-story`.

## 1. Why pieces look generic, and what fixes it

Measured against five editorial reels the user handed over (studied frame by frame in October 2026; their alias and
the instant of each observation in brackets), generated pieces fail in the same six places:

| Generic | Editorial (where it shows in the references) | Device in the kit |
|---|---|---|
| Flat type on a flat colour | Paper with matter, newsprint, a faint grid; never one flat colour (01 at 3.5 s, 05 throughout) | `C.paper`, `C.drawPaper` |
| One font, one size | Mixed weights and sizes inside one phrase, the keyword larger and red ("You've got the / *ideas* and / *content*", 05 at 1.2 s) | `C.layoutPhrase` + `C.phrase` (`~small`, `*key*`) |
| Everything on one plane | A monumental figure out of focus behind the phrase (03, "70" at 4.7 s); a blurred foreground figure crossing (01 at 1.7 s) | `C.numeral` with `blur`, `C.depthBlur` |
| Text pasted on images | Print in macro with depth of field and a highlighter on one line (03 at 7–14 s) | `C.document` + `C.drawDocument` |
| Icons and stock shapes | Real objects cut out with contact shadows: bulb, keyboard, briefcase, coin, bottle (05, 01, 03) | `C.object` (a PNG with alpha) |
| Hard cuts and crossfades | Carriers: a coin substituted by a card, a frame shrinking to make room, black to cream keeping a contour, messages accumulating (01 at 16.2 s and 17.9 s, 02 at 10.9 s, 04 at 13.8 s) | zoom through a keyword, whip pans, prints that stack, cuts on a hit |

The kit gives the devices; the brief and the [art direction](art-direction.md) decide which ones a piece needs. A
piece uses three or four of them, never all.

## 2. The devices

| Device | After Effects equivalent | Use it for | Notes |
|---|---|---|---|
| Paper (`paper`) | A scanned paper plate on top, multiply | Every light ground | Blotches, grain, fibres and darker edges, seeded; drift it slowly so the hold is alive |
| Mixed phrase (`layoutPhrase`, `phrase`) | Text layers per word, animators on position, blur and scale | Any line of copy | `~word` small and light, `word` body, `*word*` or `*several words*` keyword (accent, ×1.65, heaviest, settles from 112 %); words rise in with a blur |
| Monumental figure (`numeral`) | A huge 3D text layer far behind the focus plane | A number, a year, a single letter | Italic serif, 40–60 % opacity, blur 7–25 px; rack focus it as the phrase lands |
| Printed page (`document`, `drawDocument`) | A page in 3D with the camera's lens blur and a focus distance, a shape layer highlighter with trim paths | Proof, a quote, a source, a definition | Real text set in justified columns; the highlighted sentence on a line of its own; depth of field grows smoothly from the focus line; pull back to the headline |
| Highlighter (`highlight` in `drawDocument`) | A rectangle with trim paths, multiply | The one line that matters | Sweeps left to right in 0.6–0.8 s, slightly irregular edges; red multiply for a red brand, yellow for news |
| Ribbon (`ribbon`) | A thick shape-layer stroke with trim paths and a drop shadow | A path through the frame that ties scenes | Grey or the brand's neutral, wide (12–15 % of the short side); draws on during a transition |
| Card (`card`) | A pre-comp on a solid with a drop shadow, a pin layer | A list, a definition, a takeaway | Drops with `back.out`, shadow shrinks as it lands (lift 1.4 → 0.45), pinned at the top |
| Phone (`phone`, `notification`) | A device mock-up pre-comp | Anything about screens, apps, feeds | Notifications stack with a spring and leave one by one; a red glow on black behind it |
| Cut-out object (`object`) | A PNG layer with a contact shadow and a drop shadow, depth blur | The physical thing the line is about | The person's photos or licensed images, cut out by hand or on a plain background; never AI-generated where the project forbids it ([B-roll §1](../edit/broll.md#1-provenance-before-anything)) |
| Trim paths (`trim`, `circle`) | Trim paths on any shape | Underlines, circles around a word, arrows, connectors | Draw on with an ease-out; end with a round cap |
| Type on a curve (`textOnPath`) | Path text | A phrase that follows a ribbon or an object's edge (05, "is just noise" at 5.9 s) | Keep it short; one curve per piece |

## 3. Composition rules that make it read as designed

- **One hero per frame.** The phrase or the object or the page, never all three at full strength. The others are out
  of focus, smaller or darker.
- **Depth in three planes.** Background matter (paper, page, black with a glow), the subject (phrase, object, card),
  and something closer or further away out of focus (the figure, a foreground shape). Blur sells depth more than scale.
- **Type touches things.** A phrase sits behind an object, wraps around it or overlaps it; words do not float in a
  safe empty box. Tight leading (0.95–1.0) and words of different sizes locked to one optical baseline.
- **One accent colour, used for meaning.** The keyword, the marker, the glow, the pin: the same red. Everything else
  is paper, ink and a neutral grey.
- **Shadows decide realism.** Every object, card and print has a soft drop shadow and, when it rests on the paper, a
  contact shadow; shadows grow and soften while the thing is lifted, and tighten when it lands.
- **Matter on top of everything.** Grain and a vignette over the whole frame (the stage's finish), so type, paper and
  footage share one surface.

## 4. Motion rules

- **Words land when they are said** (with a voice) or on the beat (without one), rising 30–50 % of their size with a
  blur that clears as they settle; the keyword lands last in its line, from 112 %.
- **Camera with a reason.** A slow push on holds (3–5 % over the scene), a rack focus to reveal what was behind, a
  zoom through the keyword to enter the next scene, a whip pan with real motion blur to change subject, a pull back
  to give context (the headline above the highlighted line).
- **Carriers between scenes**, as in [direction §5](../craft/direction-choreography.md#5-continuity-that-produces-a-reveal):
  the keyword's red becomes the next scene's colour, a print lands on the previous one, a ribbon passes through both
  scenes, the hit cuts to black.
- **The scene is chosen from the frame**, never from the motion-blur sub-sample, so nothing ghosts on a cut frame.
- **No dead frame.** If a transition ends on an empty frame (a whip landing on bare paper), start the next scene's
  first element during the transition.

## 5. Recipes

| Recipe | What it shows | Data |
|---|---|---|
| `editorial-collage` | Figure behind a mixed phrase → zoom through the keyword → macro page with a marker and a pull back → whip → ribbon and pinned card → cut to black, phone with notifications, glowing ending | `data.json` |
| `broll-story` | Clips and photos as prints that stack on paper, the voice's phrase in mixed weights with a red keyword stroke | `voice.json`, `assets/broll/timeline.json` |

## 6. Checks

- A sheet of one frame per scene next to the references: does each frame have matter, depth and one hero?
- A full-size crop of the macro page: the focus line is sharp, the blur grows smoothly (no bands).
- A dense window on every transition: the carrier is visible on both sides; no empty frame.
- `determinism_check.mjs`: the paper, the page and the blur levels are seeded and cached, so the same t gives the
  same pixels.

## Sources

The five reference reels the user provided (720×1280, 17–38 s), studied in `referentes/motion-graphics-2026-10-21/`
of the user's project; After Effects concepts (lens blur and focus distance on 3D layers, trim paths, track mattes,
drop shadows, path text) from Adobe's documentation. The kit is Motionsmith's own code.
