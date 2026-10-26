# Third-party credits

Motionsmith is original work released under the MIT license. Part of its craft knowledge was learned from these
open skills and public references; no code or text is copied verbatim unless stated.

## Skills (MIT)

| Source | Commit | What informed Motionsmith |
|---|---|---|
| [RFTaurus/motion-skill](https://github.com/RFTaurus/motion-skill) (`bang-motion`, by Bang Tutorial) | `c1aa65e` | Text, blur and camera techniques; shot sizes; glow restraint on headlines; contrast under text |
| [SkillMedev/skills · kinetic-typography](https://github.com/SkillMedev/skills/tree/97a13607d669157a4a16d5ba79b77f208319f7b9/skills/kinetic-typography) | `97a1360` | Reading budget, entrances/exits, frame-based specs |
| [SkillMedev/skills · motion-design-principles](https://github.com/SkillMedev/skills/tree/97a13607d669157a4a16d5ba79b77f208319f7b9/skills/motion-design-principles) | `97a1360` | Diagnosis → curve → timing/spacing → arc |
| [LottieFiles/motion-design-skill](https://github.com/LottieFiles/motion-design-skill) | `f9a8a04` | Choreography (hero/response), stagger patterns, distance-based durations |
| [dylantarre/animation-principles · after-effects](https://github.com/dylantarre/animation-principles) | `8359713` | Key poses and breakdowns, staging, delays and arcs |

Each of these is distributed under the MIT license; see their repositories for the full text.

## Algorithms and public references

- Bloom pyramid and Karis average: J. Jimenez, *Next Generation Post Processing in Call of Duty: Advanced Warfare*
  (SIGGRAPH 2014); LearnOpenGL, "Physically Based Bloom".
- ACES filmic fit: K. Narkowicz, "ACES Filmic Tone Mapping Curve" (2016).
- Hash without sine: D. Hoskins, "Hash without Sine" (Shadertoy).
- Audio/video sync thresholds: ITU-R BT.1359-1.
- After Effects concepts (Graph Editor, motion blur settings, Glow, blending modes, track mattes) are described from
  Adobe's public documentation; Motionsmith does not use or require After Effects.

## Fonts (SIL Open Font License 1.1)

Copied unmodified from the [Google Fonts repository](https://github.com/google/fonts) into `templates/fonts/` (files
renamed only), each with its licence next to it. The OFL allows bundling and redistribution with software; the fonts
may not be sold on their own.

| Family | Files | Licence | Upstream |
|---|---|---|---|
| Archivo (variable weight and width) | `Archivo-VF.ttf`, `Archivo-Italic-VF.ttf` | `OFL-Archivo.txt` | [Omnibus-Type/Archivo](https://github.com/Omnibus-Type/Archivo) |
| Fraunces (variable) | `Fraunces-VF.ttf`, `Fraunces-Italic-VF.ttf` | `OFL-Fraunces.txt` | [undercasetype/Fraunces](https://github.com/undercasetype/Fraunces) |
| JetBrains Mono (variable) | `JetBrainsMono-VF.ttf` | `OFL-JetBrainsMono.txt` | [JetBrains/JetBrainsMono](https://github.com/JetBrains/JetBrainsMono) |

## Prompt Motion

The six-block brief (`<inputs>`, `<direction>`, `<structure>`, `<build>`, `<gotchas>`, `<start>`), the common AI
tells and the figures quoted in `references/create/motion-brief.md` come from the analyses and templates published at
[prompt-motion.com](https://prompt-motion.com/) (curated by @p4nthera_), read on 2026-10-26. The templates in
`templates/briefs/` are written for Motionsmith and paraphrase that structure; no text or video from the site is
included.

## HyperFrames

`scripts/kit/hyperframes.js` and `scripts/hyperframes.py` follow the public composition contract of
[HyperFrames](https://hyperframes.heygen.com) (root `data-*` attributes, `window.__timelines`, the `hf-seek` event,
`window.__hf.buildReady`). No HyperFrames code is included; projects load its CLI with `npx` and GSAP from its CDN.

No footage, photographs or music from third parties are included.
