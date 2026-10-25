# Overlays and alpha: capture, keep and test transparency

Read when a graphic goes over footage, for a lower third, a title or a transparent insert. The delivery must fit
the destination editor: agree on container, fps, visible duration, time origin and audio. Over an edited voice, an
overlay usually does not duplicate that track.

## 1. Design over the footage

Read the approved script and real cues; prepare the animation next to the gesture, object or area that motivates it.
Watch the take including its motion: a safe box on one frame does not guarantee a hand will not cross it two seconds
later. Reserve reading space, faces and the platform's interface. Keep a preview over the take and a view of the layer
alone; test backgrounds must never be burnt into the overlay.

## 2. Capturing with alpha

- With an engine, check its alpha support in the installed version and test one frame before rendering the sequence.
  A renderer that produces MP4 does not keep transparency.
- In your own page: transparent `html`, `body`, root and scene layers; no opaque background rectangle or filled
  canvas. With the kit: `node <skill>/scripts/sample_frames.mjs --root <piece> --out <dir> --frames a:b --png --alpha`
  (Playwright `omitBackground: true`, straight alpha; tested).
- Verify the PNGs are RGBA with transparent **and** opaque values where expected. A drawn checkerboard is an image,
  not transparency.

## 3. RGBA sequence to ProRes 4444 MOV

```bash
ffmpeg -n -framerate 30 -i "frames/%03d.png" -vf "scale=out_color_matrix=bt709:out_range=tv,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv" -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le -alpha_bits 16 "overlay.mov"
```

- BT.709 flags keep brand colours from shifting in the editor. Tested with 64×64 PNGs: the MOV is tagged BT.709, the
  extracted alpha is 0 on the background and 65535 on the mark, and `#ff422e` comes back as (255, 66, 46).
- Use the plan's fps (e.g. `30000/1001`), the exact frame count and a new path. Profile 4 is ProRes 4444 in this
  encoder. Never convert to yuv420p afterwards: alpha is lost. For WebM, test VP9 alpha in the destination editor.

## 4. Check the channel and the fit

```bash
ffmpeg -n -v error -i "overlay.mov" -vf alphaextract -frames:v 1 "alpha.png"
```

Black = transparent, white = opaque, grey = partial. Sample background, object centre, soft edge and halo; check
several times, not only the first (it may be fully transparent by design). Composite over light, over dark and over
real footage:

```bash
ffmpeg -n -f lavfi -i "color=c=white:s=1080x1920:r=30:d=1" -i "overlay.mov" -filter_complex "[0:v][1:v]overlay=alpha=straight:shortest=1:format=auto,scale=out_color_matrix=bt709:out_range=tv,setparams=colorspace=bt709:color_primaries=bt709:color_trc=bt709:range=tv[v]" -map "[v]" -an -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv -c:v libx264 -pix_fmt yuv420p "preview-light.mp4"
```

`alpha=straight` assumes unpremultiplied alpha; if the route delivers premultiplied, configure the compositor to
match. Dark halos over light usually mean premultiplication, hidden edge colour or resampling: never "fix" it with a
black key. `verify_export.py` does not inspect alpha: keep the extractions and composites as evidence.

## 5. With the WebGL kit

- `PostFX.finish` writes alpha 1: it is the full-frame finish. For an overlay, draw the layer with its alpha and apply
  only alpha-preserving passes (`copy`, directional or radial blur); bloom and tone mapping happen before, on the
  layer, and the alpha is computed separately (e.g. blurred like the colour).
- A WebGL canvas is premultiplied by default: write `vec4(color * a, a)` or create it with `premultipliedAlpha: false`
  ([glass & WebGL §6](../craft/glass-webgl.md#6-code-bugs-already-met)).
- Accumulating a layer with alpha over several samples: clear with `clearColor: [0, 0, 0, 0]`, accumulate
  premultiplied (`vec4(rgb * a, a) * weight`) and un-premultiply when compositing (the
  [starter](../../templates/starter/piece.js) does this for its brand layer).

## 6. Delivery package

- The transparent overlay with codec, container and alpha verified.
- A preview over the take if it exists; light/dark backgrounds as extra technical evidence.
- Time origin, visible duration, handles, fps, and whether it carries audio.
- Editable sources and assets with local paths; brief placement notes when they help.

A layer that needs a new voice, an unverified figure or a change of meaning goes back to the script; being able to
render it does not authorise inventing it.
