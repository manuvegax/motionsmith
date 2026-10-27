# Niches: what each kind of content needs, and the recipe that starts it

Read when the request names a field (psychology, finance, cooking, fitness, podcasts, history, tech) or a kind of
content (a list, a tutorial, a data point, a story). The craft does not change between niches; what changes is what
the viewer came for, what counts as proof, and which defaults make it look like everyone else's. Each row is a
starting point, not a rule: the profile (`MOTIONSMITH.md`) and the brief win.

## 1. The map

| Niche | The viewer came for | Hook that fits | Structure ([story structures](../edit/story-structures.md)) | Start from |
|---|---|---|---|---|
| Psychology, self-knowledge, therapy | Recognising themselves | A scene they have lived, said in the second person; a question they have not dared to ask | Problem → reframe; question → answer | `voice-captions`, `step-diagram` (a mechanism), `kinetic-quote` |
| Education, science, explainers | Understanding a mechanism | The surprising result first, then how | Explainer: definition → mechanism → example → takeaway | `step-diagram`, brief `explainer` |
| Data, finance, economy | One comparison that changes their mind | The number, with its unit and its source, on frame one | Three-beat reveal: context → the number → what it means | `chart-bars`, `data-reveal` |
| Lists, rankings, tips | Many small payoffs and the best one last | "Number one surprised me", the count shown | Escalating list, countdown | `ranking` |
| Podcasts, interviews, yapping | A voice and an idea worth the time | The strongest sentence of the clip, first | One moment that stands alone (a claim, a turn, a confession) | `audiogram`, `voice-captions` |
| Documentary, history, stories | Being taken somewhere | The end of the story, then "how did we get here" | Hook → turn → payoff; before/after | `broll-story`, brief `voiceover` |
| Product, launch, service | Seeing it work | The result in use, not the logo | Launch: promise → 3–5 moments → ending | `promo-sequence`, brief `launch` |
| Tutorials, software, how-to | Doing it themselves | The finished result, then the steps | Numbered steps, each one visible | `step-diagram` (chain), `broll-story` with screen recordings |
| Fitness, cooking, crafts | Following along | The final plate or move, then the first step | Steps on a timer; before/after | `ranking` (steps), `broll-story` |
| Quotes, poetry, songs (own words) | A line that stays | The line itself, typeset as the hero | One line, then its turn | `kinetic-quote`, `voice-captions` |
| Brand titles, intros, channels | Recognition | The mark in motion | Logo reveal, title card, lower third | `logo-reveal`, `title-card`, `lower-third` |

## 2. What changes per niche

**Psychology and personal content.** Specific scenes beat general claims: "you check your phone before you are
awake" lands, "phones affect attention" does not. One idea per piece; tenderness over alarm; no diagnosis in a
caption. Code-drawn shapes and type carry it better than stock faces. Data with an author's name tends to perform
worse than a lived scene with the same idea (a pattern in one account's numbers, not a law).

**Education.** A sequence with a start and an end, never a topic tour. The diagram builds and never resets; the
accent marks only the step being explained; every label has its reading time. Facts are researched first and listed
with their sources; a fact that cannot be checked is left out.

**Data and finance.** One comparison per chart. Bars and areas start at zero; scales are not stretched; counts never
overshoot the true value; the source is on screen, not in the caption. Red means the accent, not a loss, unless the
whole piece says so. Units always next to the number.

**Lists.** The count is an open loop: show how many are left. Strongest item last, a surprising one first. Each item
gets the same time, number one a little more. Seven is a lot for a reel; three to five usually lands.

**Podcasts and yapping.** Cut to one moment that stands alone, 30–60 s. Captions are the picture: big, karaoke-style,
the stressed words marked. The frame moves with the voice and rests in its pauses. The speaker's name once, on top.

**Documentary and B-roll.** The picture adds what the voice does not say; every shot has its licence; one grade for
every source; wide, medium and detail alternate ([B-roll](../edit/broll.md)).

**Tutorials.** Show the finished result first. One step per scene, numbered, with the action visible (a zoom on the
click, not the whole screen). The viewer must be able to pause on any step and follow.

## 3. Banned per niche (add to the brief's list)

| Niche | Avoid → instead |
|---|---|
| Psychology | Brain icons and glowing neurons → a concrete scene; "you are not broken" slogans → a specific observation |
| Education | A wall of text → one label at a time; a topic tour → one mechanism |
| Data | Truncated axes, 3D bars, pie charts with ten slices → bars from zero, one highlight |
| Lists | Equal weight on every item → number one gets the accent and more time |
| Podcasts | A static photo with a waveform → captions that follow the voice, the frame breathing with it |
| Documentary | Stock clips that illustrate every noun → pictures that add; mixed grades → one grade |
| Product | The logo first → the product working |
| Tutorials | The whole screen at once → a zoom on the step |

## 4. Sound per niche

Psychology and stories: sound design without music, or a low bed under the voice; data and lists: ticks on the
counts, a hit on the payoff; podcasts: the voice alone, no bed; product: a track on the beat
([sound design](../craft/sound-design.md), [voice-over §5](../edit/voiceover.md#5-the-mix)).

## 5. Recipes added for niches

| Recipe | Niche | Data |
|---|---|---|
| `chart-bars` | Data, finance | `data.json`: title, unit, decimals, source, highlight, bars |
| `ranking` | Lists, tips, steps | `data.json`: title, items (rank, label, note) |
| `step-diagram` | Education, psychology, processes | `data.json`: title, loop, takeaway, steps (label, note) |
| `audiogram` | Podcasts, yapping, voice notes | `voice.json` from `voice_plan.py` (words, phrases, levels) |
| `voice-captions`, `broll-story` | Any narrated piece | `voice.json`, `assets/broll/timeline.json` |

`new_piece.py --recipe <name>` copies the recipe's sample `data.json` and points `plan.data` to it: edit the data, not
the code.
