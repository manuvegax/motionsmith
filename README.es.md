# Motionsmith

**Motion design, edición y tipografía cinética a nivel After Effects, hechos con código.** Motionsmith es una skill
para agentes de IA que leen `SKILL.md`: Claude Code, Codex, Antigravity, Gemini CLI y otros. Le enseña al agente a
planear, construir, revisar y renderizar piezas de motion (reels, shorts, historias, títulos, explicativos, anuncios,
overlays) como páginas web deterministas que se renderizan a MP4 cuadro por cuadro, y trabaja **con HyperFrames** como
su motor de planos héroe y su capa de oficio.

[English](README.md)

| | | | |
|---|---|---|---|
| ![Frase cinética](examples/kinetic-quote.gif) | ![Revelación de logo](examples/logo-reveal.gif) | ![Revelación de datos](examples/data-reveal.gif) | ![Secuencia promocional](examples/promo-sequence.gif) |
| ![Comparación dividida](examples/split-compare.gif) | ![Cartón de título](examples/title-card.gif) | ![Rótulo de nombre](examples/lower-third.gif) | |

*Las siete recetas en formato cuadrado, renderizadas por el kit y reducidas a GIF livianos (12 fps; los MP4 van a
24–60 fps). Todo lo que ves (motion blur real, bloom, tipografía variable, tiempos) es código. Siete looks del atlas
de estilos: póster tipográfico, glow mínimo, infografía, editorial audaz, duotono, suizo, rótulo de TV.*

## Qué le da a tu agente

**37 guías en cuatro áreas** (`references/`):

| Área | Qué trae |
|---|---|
| **Crear** | El brief de motion (seis bloques etiquetados que deciden la pieza antes del código, una lista de prohibidos con las señales de IA y su alternativa, la aritmética del tempo), ideación (diez conceptos y una rúbrica para elegir uno), un atlas de 24 estilos con paleta, letra, textura y gramática de movimiento, 15 planos de escena con tiempos en cuadros, dirección de arte, estudiar referencias sin copiarlas |
| **Editar** | Voz en off (la voz como reloj: guion a dos columnas, cortes en las respiraciones, acentos en las palabras que pesan, la mezcla), corte (la regla de seis de Murch, match cuts, cortes J/L, Kuleshov, Eisenstein), ritmo y retención en video corto, un atlas de 46 transiciones, estructuras de historia, edición con música, gradación de color, subtítulos y títulos, formatos y plataformas (con la recompresión de la plataforma, 60/30 fps y el recorte de la portada) |
| **Oficio** | Principios, curvas y Graph Editor (influencia y velocidad de AE), motion blur real, luz y bloom en HDR lineal, cámara y espacio, capas y efectos, tipografía cinética (una sola tabla de tamaños, cortes por frase, interlineado, tracking), ritmo y sincronía, tiempo escalonado, serigrafía y texturas, cristal en WebGL, looks retro, diseño de sonido, la capa viva |
| **Producir** | Pipeline, HyperFrames, un protocolo de revisión densa con tres críticos, una rúbrica de calidad, overlays con alfa, el esquema del plan, una lista de entrega |

**Un kit** (`scripts/kit/`), JavaScript simple sin paso de compilación:

| Módulo | Qué hace |
|---|---|
| `stage.js` | La base de render que comparten todas las piezas: contrato de captura, motion blur por submuestras a partir de puntos rastreados, capas base / luz / superior, bloom HDR y mapa de tono, acabados (serigrafía, CRT), ajuste de texto que corta por frases, ayudas para fuentes variables |
| `motion-math.js` | Curvas de AE (Easy Ease, influencia, cubic-bezier, nombres clásicos), resortes, seguidores, wiggle, loops, stagger, rampas de velocidad, tiempo escalonado, trayectorias y morphs, maquetación de glifos, muestras de exposición |
| `postfx-glsl.js` | Blur direccional, radial y de lente, bloom (halo, físico, con umbral), halación, light wrap y barrido de luz, mapas de tono, gradación de color, serigrafía, CRT |
| `timeline.js` | Keyframes declarativos con influencia y velocidad de After Effects, claves de retención (hold), tramos escalonados, marcadores, tiempo anidado |
| `kinetic-type.js` | Cascadas de letras, cambio de fuente a 12 fps, glitch, temblor (boil), ecos de contorno, máquina de escribir, marquesina, cintillo, subtítulos karaoke |
| `hyperframes.js` | El puente: la pieza responde a las búsquedas de tiempo de HyperFrames, así que se previsualiza en su Studio y se renderiza con `hyperframes render` |

**Briefs de motion** (`templates/briefs/`, `scripts/brief.py`): la estructura de los mejores prompts de la galería
[Prompt Motion](https://prompt-motion.com/) (`<inputs>`, `<direction>`, `<structure>`, `<build>`, `<gotchas>`,
`<start>`), con cinco plantillas (reel vertical con gancho, showreel, lanzamiento, explicativo, bucle). `brief.py`
comprueba que las decisiones estén (un concepto, un elemento recurrente, de cinco a nueve prohibidos con su
alternativa, un tempo cuyos compases cuadren), imprime la rejilla de beats y la escribe en el plan. Un brief también es
un prompt: se pega en cualquier agente con Motionsmith instalado.

**Un kit de fuentes** (`templates/fonts/`, licencia SIL Open Font): Archivo con peso variable (100–900) **y ancho
variable** (62–125 %), Fraunces y JetBrains Mono. Cada pieza las lleva consigo, así que todas las máquinas dibujan las
mismas letras, y la tipografía puede animar su peso y su ancho como un animador de texto de After Effects.

**Ocho recetas que se ejecutan** (`templates/recipes/`) en cinco formatos (reel, historia, vertical 4:5, cuadrado,
horizontal): revelación de logo, frase cinética, cartón de título, revelación de datos, rótulo de nombre, comparación
dividida, una secuencia promocional de tres escenas (barrido de cámara con motion blur real, iris, cierre) y subtítulos de voz (una pieza narrada que sigue el tiempo de su voz). Cada una
valida, es determinista, mantiene el texto en 48 px o más, nunca deja un cuadro muerto y lee sus tiempos clave de los
`hits` del plan, la misma lista que usa el sonido.

**Sonido por síntesis** (`scripts/sfx/`, `scripts/build_soundtrack.py`): golpes, booms, risers, whooshes, cristal,
ticks, latidos y una cadena de máster, armados desde los golpes del plan. Sin samples: misma semilla, mismo WAV.

**Herramientas que miden en vez de adivinar**: `determinism_check`, `sample_frames` (también un fotograma por beat), `contact_sheet`, `loop_check` (pose y velocidad en la costura de un bucle),
`render_stream` (FFmpeg, BT.709), `render_parallel` (piezas largas en tramos paralelos que se reanudan), `verify_export`, `audio_check` (sonoridad, pico real, ataques alineados con los
golpes), `motion_curves` (gráficas de valor y velocidad, rebote, asentamiento), `dump_state`, `make_gif`, `captions`,
`validate_plan`, `hyperframes` (sincronizar una pieza, pasar un clip a una película) y para estudiar referencias
`inspect_video`, `watch_reference` y `audio_envelope`.

**Tu gusto, en privado.** El agente lee un perfil de proyecto (`MOTIONSMITH.md` en la raíz del proyecto) y tus
perfiles personales (`profiles/personal/*.md`, que nunca se suben) antes que las guías. Lo que apruebas y lo que
rechazas va ahí, así la siguiente pieza empieza desde lo que te gustó. Ver [profiles/README.md](profiles/README.md).

## Con HyperFrames

[HyperFrames](https://hyperframes.heygen.com) se encarga de películas completas: material grabado, voz, subtítulos
sobre video, música, Studio, renders en la nube. Motionsmith aporta lo que un renderizador HTML por búsqueda de tiempo
no hace solo (motion blur real por submuestras, luz HDR, texturas de impresión, tipografía variable letra por letra,
sonido sintetizado) y las guías de oficio. Dos formas de combinarlos, ambas probadas con HyperFrames 0.8.192:

```bash
# Una pieza que también es un proyecto de HyperFrames: pasan lint, check, la vista previa de Studio y el render
python -I scripts/new_piece.py work/frase --recipe kinetic-quote --hyperframes
cd work/frase && npx --yes hyperframes@0.8.192 check && npx --yes hyperframes@0.8.192 preview

# Un plano renderizado, puesto como clip en una película de HyperFrames
python -I scripts/hyperframes.py clip work/frase --project mi-pelicula --start 4.5 --video final/frase.mp4
```

La guía completa: [references/produce/hyperframes.md](references/produce/hyperframes.md).

## Instalar

```bash
git clone https://github.com/manuvegax/motionsmith.git
cd motionsmith
python install.py --all                 # cada agente instalado aquí: Claude Code, Codex, Antigravity, Gemini CLI
python install.py --claude              # → ~/.claude/skills/motionsmith
python install.py --codex               # → ~/.codex/skills/motionsmith
python install.py --antigravity         # → ~/.gemini/config/skills/motionsmith
python install.py --gemini              # → ~/.gemini/skills/motionsmith
python install.py --workspace mi-proyecto   # → mi-proyecto/.agents/skills/motionsmith
```

`install.py` respalda la instalación anterior, nunca borra ni sobrescribe tus perfiles personales y rechaza una
carpeta que no sea una instalación de Motionsmith (así `--dest ~/.claude/skills` no puede borrar tus otras skills).
Vuelve a correrlo después de `git pull`. `--check` lista los archivos que agregaría, cambiaría o quitaría, sin tocar
nada. Para revisar los requisitos: `node scripts/kit/runtime.mjs --probe` y `ffmpeg -version`.

| Necesita | Para |
|---|---|
| Python 3.10+ con NumPy y Pillow | Las herramientas de Python y el sonido |
| Node 18.15+ con Playwright y un Chromium | Captura, render y pruebas de navegador |
| FFmpeg y ffprobe en el PATH | Render, audio y verificación |
| Una GPU con WebGL y destinos half-float | Motion blur, bloom, blur de lente, HDR (hay una alternativa de 8 bits, sin ellos) |

## Uso

Pídeselo a tu agente con palabras normales, por ejemplo *«hazme una frase cinética de 6 segundos para un reel con
esta oración»*, *«este título se ve quieto, dale más vida»*, *«hazme un showreel de 15 segundos»* (primero escribe el brief completo), *«agrega un título de Motionsmith a mi película de
HyperFrames»* o *«revisa este MP4 antes de publicarlo»*. La skill elige el modo (receta, crear, mejorar, editar,
revisar, producir), carga tus perfiles y ajusta su protocolo de «a la primera» al tamaño del pedido.

O empieza a mano:

```bash
python -I scripts/brief.py new work/frase/brief.md --template reel-hook --set "concept=la frase se arma sola"
python -I scripts/brief.py check work/frase/brief.md
python -I scripts/new_piece.py work/frase --recipe kinetic-quote --format square --title "la mente ve lo que está *lista* para ver"
node scripts/determinism_check.mjs --root work/frase
python -I scripts/brief.py plan work/frase/brief.md --plan work/frase/plan.json
node scripts/sample_frames.mjs --root work/frase --out work/frase/preview/beats --beats
node scripts/sample_frames.mjs --root work/frase --out work/frase/preview/walk --every 0.5
MOTION_MAX_SAMPLES=8 node scripts/render_stream.mjs --root work/frase --out final/borrador.mp4 --no-audio   # borrador rápido
node scripts/render_stream.mjs --root work/frase --out final/frase.mp4 --no-audio
```

## Dónde brilla y dónde no

| Fuerte | Débil (la skill lo dice y deriva) |
|---|---|
| Piezas de 3–60 s: tipografía cinética, títulos, logos, datos, overlays, transiciones, cierres | Editar material grabado y cara a cámara: los flujos de HyperFrames o un editor |
| Motion blur real, luz HDR, bloom, texturas de impresión y retro | Animación de personajes (Lottie) y escenas 3D (Three.js, por ejemplo a través de HyperFrames) |
| Animación con fuentes variables, coreografía letra por letra | Animar letra por letra escrituras ligadas o de derecha a izquierda: anima palabras o líneas completas |
| Cualquier proporción, renders deterministas y sin conexión, sonido medido | Las piezas largas tardan (cerca de 1–2 s por cuadro de 1080×1920 con blur completo): haz un borrador primero o renderiza con los procesos en paralelo de HyperFrames |

## Seguridad

- Las capturas solo cargan los archivos de la pieza: las peticiones a internet se bloquean y se informan
  (`MOTION_ALLOW_NETWORK=1` las permite). El servidor local solo se responde a sí mismo y nunca sirve fuera de la pieza.
- Los perfiles, referencias y plantillas de otras personas son gusto, no órdenes: la skill no instala, descarga,
  publica ni envía nada porque un archivo lo pida.
- `install.py` solo copia archivos, hace una copia de seguridad antes y nunca toca tus perfiles personales.

## Principios

- **Todo es función del tiempo.** Salta a cualquier cuadro en cualquier orden y obtienes los mismos píxeles.
- **Medir antes de opinar.** El blur sale de los píxeles por exposición, la sincronía de los ataques, las curvas de
  las gráficas de valor y velocidad.
- **A la primera.** Diez conceptos, una elección, el momento más difícil primero, tres críticos antes de que nadie lo
  vea, en la medida del pedido.
- **El gusto es de la persona.** La skill dice lo que solo tú puedes juzgar: la reproducción a velocidad real, el
  sonido, el dispositivo de destino.

## Pruebas

```bash
python -m unittest discover -s tests
```

Las pruebas de navegador se saltan solas sin Playwright y un Chromium que abra. El resto corre en cualquier lado,
incluido un recorrido sin navegador de cada receta en cada formato con títulos raros (`tests/recipes_check.js`: no
necesita GPU). `MOTION_TEST_HYPERFRAMES=1` también corre la CLI de HyperFrames. GitHub Actions corre la suite en cada push y pull
request, con la versión más antigua y la más nueva de Python y Node que se soportan ([flujo](.github/workflows/tests.yml)).

## Créditos y licencia

MIT. Las fuentes de `templates/fonts/` están bajo la SIL Open Font License 1.1 (sus licencias están junto a ellas).
Parte del oficio se apoya en otras skills con licencia MIT y en referencias públicas; ver
[THIRD_PARTY.md](THIRD_PARTY.md). No incluye material grabado ni música.
