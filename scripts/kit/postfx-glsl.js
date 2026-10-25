/* postfx-glsl.js · light and blur passes for WebGL 1 compositions (After Effects effects, rebuilt as shaders).
   Browser: <script src="postfx-glsl.js"></script> → window.PostFX.   Node: require() exposes the sources for tests.
   Guides: references/craft/blur.md and references/craft/light-bloom.md.

   const fx = PostFX.runner(gl, {width: 1080, height: 1920});
   const scene = fx.target();                         // HDR (half-float) when the GPU allows it
   ...draw the scene into scene.fb...
   const bloom = fx.bloom(scene, {levels: 6, radius: .005});
   fx.finish(scene, bloom, {bloomMode: 'halo', strength: .45, toneMap: 'aces', vignette: .25, grain: .02, frame: n});
*/
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.PostFX = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const VERTEX = 'attribute vec2 point;varying vec2 uv;void main(){uv=point*.5+.5;gl_Position=vec4(point,0.,1.);}';
  const HEAD = 'precision highp float;varying vec2 uv;\n';
  const LUMA = 'float luma(vec3 c){return dot(c,vec3(.2126,.7152,.0722));}\n';
  // Hash without sine (Dave Hoskins, "Hash without Sine"): stable under float rounding on every GPU.
  const HASH = 'float hash(vec2 p){vec3 p3=fract(vec3(p.xyx)*.1031);p3+=dot(p3,p3.yzx+33.33);return fract((p3.x+p3.y)*p3.z);}\n';

  const SHADERS = {
    copy: HEAD + 'uniform sampler2D image;void main(){gl_FragColor=texture2D(image,uv);}',

    /* AE Directional Blur: box average along a direction. dir = blur length in uv: [px_x / W, px_y / H]
       (uv is not isotropic in a vertical frame). Up to 128 samples. */
    directionalBlur: HEAD + `uniform sampler2D image;uniform vec2 dir;uniform int samples;
      void main(){vec4 s=vec4(0.);float n=0.;
        for(int i=0;i<128;i++){if(i>=samples)break;float k=(float(i)+.5)/float(samples)-.5;s+=texture2D(image,uv+dir*k);n+=1.;}
        gl_FragColor=s/n;}`,

    /* AE Radial Blur: zoom (towards/away from centre) or spin (around it). amount: zoom fraction or spin radians. */
    radialBlur: HEAD + `uniform sampler2D image;uniform vec2 center;uniform float amount,aspect;uniform int samples,spin;
      void main(){vec4 s=vec4(0.);float n=0.;vec2 d=uv-center;d.x*=aspect;
        for(int i=0;i<128;i++){if(i>=samples)break;float k=(float(i)+.5)/float(samples)-.5;vec2 p;
          if(spin==1){float a=amount*k;p=vec2(d.x*cos(a)-d.y*sin(a),d.x*sin(a)+d.y*cos(a));}else p=d*(1.+amount*k);
          p.x/=aspect;s+=texture2D(image,center+p);n+=1.;}
        gl_FragColor=s/n;}`,

    /* AE Camera Lens Blur: disc (or polygonal iris) kernel on a golden-angle spiral; HDR highlights become bokeh.
       radius in uv (x of the short side); gain/threshold boost highlights like the effect's Highlight controls.
       What makes it read as a real lens (all optional, 0 = off):
         rim     brighter disc edge (spherical aberration, "soap-bubble" bokeh), 0.5–1.5
         chroma  colour fringe at the disc edge (longitudinal CA), 0.01–0.04
         catEye  discs clipped into a lemon shape towards the frame edge (optical vignetting), 0.3–0.8;
                 opticalCenter is the uv of the lens axis (set it when catEye > 0)
       Small lights come out dotted when they are smaller than the gap between samples (≈ radius·√(π/samples)):
       pre-blur the plane by about that gap (two directionalBlur passes) and use 160–256 samples.
       And above all: blur only the out-of-focus plane and keep the subject sharp (see blur-completo.md §4). */
    lensBlur: HEAD + LUMA + `uniform sampler2D image;uniform vec2 radius,opticalCenter;uniform float gain,threshold,blades,rotation,rim,chroma,catEye;uniform int samples;
      void main(){vec3 s=vec3(0.);float n=0.;vec2 axis=(uv-opticalCenter)*2.;
        for(int i=0;i<256;i++){if(i>=samples)break;float fi=float(i);float r=sqrt((fi+.5)/float(samples));float a=fi*2.39996323+rotation;
          if(blades>2.5){float seg=6.2831853/blades;float m=mod(a,seg)-seg*.5;r*=cos(seg*.5)/cos(m);}
          vec2 o=vec2(cos(a),sin(a))*r;
          if(catEye>0.&&length(o+axis*catEye)>1.)continue;
          vec2 off=o*radius;vec3 c;
          if(chroma>0.)c=vec3(texture2D(image,uv+off*(1.+chroma)).r,texture2D(image,uv+off).g,texture2D(image,uv+off*(1.-chroma)).b);
          else c=texture2D(image,uv+off).rgb;
          c*=1.+gain*smoothstep(threshold,threshold+.25,luma(c));
          float w=1.+rim*r*r*r;s+=c*w;n+=w;}
        gl_FragColor=vec4(s/max(n,1e-4),1.);}`,

    /* Threshold prefilter with a soft knee (AE Glow Threshold, without the hard edge). */
    bloomPrefilter: HEAD + `uniform sampler2D image;uniform float threshold,knee;
      void main(){vec3 c=texture2D(image,uv).rgb;float br=max(c.r,max(c.g,c.b));
        float soft=clamp(br-threshold+knee,0.,2.*knee);soft=soft*soft/(4.*knee+1e-5);
        gl_FragColor=vec4(c*max(soft,br-threshold)/max(br,1e-5),1.);}`,

    /* 13-tap downsample (Jimenez 2014, weights from LearnOpenGL "Physically Based Bloom"). karis=1 on the first level:
       each 2x2 group is weighted by 1/(1+luma) and the result is renormalised, so one hot pixel cannot flicker
       ("fireflies") while a flat area keeps its exact value (LearnOpenGL's shortcut darkened bright areas). */
    bloomDown: HEAD + LUMA + `uniform sampler2D image;uniform vec2 texel;uniform float karis;
      vec3 t(float x,float y){return texture2D(image,uv+texel*vec2(x,y)).rgb;}
      vec4 kw(vec3 a,vec3 b,vec3 c,vec3 d,float s){vec3 m=(a+b+c+d)*.25;float w=s/(1.+luma(m));return vec4(m*w,w);}
      void main(){vec3 a=t(-2.,2.),b=t(0.,2.),c=t(2.,2.),d=t(-2.,0.),e=t(0.,0.),f=t(2.,0.),g=t(-2.,-2.),h=t(0.,-2.),i=t(2.,-2.);
        vec3 j=t(-1.,1.),k=t(1.,1.),l=t(-1.,-1.),m=t(1.,-1.);vec3 o;
        if(karis>.5){vec4 s=kw(j,k,l,m,.5)+kw(a,b,d,e,.125)+kw(b,c,e,f,.125)+kw(d,e,g,h,.125)+kw(e,f,h,i,.125);o=s.rgb/s.a;}
        else{o=e*.125+(a+c+g+i)*.03125+(b+d+f+h)*.0625+(j+k+l+m)*.125;}
        gl_FragColor=vec4(max(o,vec3(0.)),1.);}`,   // no floor: pure black must stay black under bloom

    /* 3x3 tent upsample; drawn with additive blending into the next larger level. radius in uv. */
    bloomUp: HEAD + `uniform sampler2D image;uniform vec2 radius;
      vec3 t(float x,float y){return texture2D(image,uv+radius*vec2(x,y)).rgb;}
      void main(){vec3 o=t(0.,0.)*4.+(t(0.,1.)+t(-1.,0.)+t(1.,0.)+t(0.,-1.))*2.+t(-1.,1.)+t(1.,1.)+t(-1.,-1.)+t(1.,-1.);
        gl_FragColor=vec4(o/16.,1.);}`,

    /* Light wrap: the blurred background bleeds into the edges of the foreground. */
    lightWrap: HEAD + `uniform sampler2D comp,bgBlur,fgAlpha,fgAlphaBlur;uniform float amount;
      void main(){vec3 c=texture2D(comp,uv).rgb;float a=texture2D(fgAlpha,uv).a,ab=texture2D(fgAlphaBlur,uv).a;
        gl_FragColor=vec4(c+texture2D(bgBlur,uv).rgb*a*(1.-ab)*amount,1.);}`,

    /* A diagonal band of light added in linear HDR (run before bloom so it glints). pos and width are in frame
       heights from the centre; PostFX.sweepExtent(aspect, angle) gives the pos where the band leaves the frame. */
    lightSweep: HEAD + `uniform sampler2D image;uniform float pos,width,strength,angle,aspect;uniform vec3 tint;
      void main(){vec3 c=texture2D(image,uv).rgb;vec2 p=(uv-.5)*vec2(aspect,1.);vec2 n=vec2(cos(angle),sin(angle));
        float d=dot(p,n)-pos;gl_FragColor=vec4(c+tint*strength*exp(-d*d/(width*width)),1.);}`,

    /* Finish: bloom mix, halation, exposure, tone map, lift/gamma/gain, chromatic aberration, vignette, grain, gamma. */
    finish: HEAD + LUMA + HASH + `uniform sampler2D scene,bloom;uniform float useBloom,bloomMode,bloomNorm,strength,halation,halationThreshold,exposure,toneMap,
        aberration,vignette,grain,frame,lift,gamma,gain,saturation;uniform vec3 halationTint;uniform vec2 res;
      vec3 tm(vec3 x){
        if(toneMap<.5)return clamp(x,0.,1.);
        if(toneMap<1.5){vec3 o=max(x-.85,0.);return min(x,vec3(.85))+.15*(1.-exp(-o/.15));}
        if(toneMap<2.5)return x/(1.+x);
        return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0.,1.);}
      void main(){vec2 d=(uv-.5)*aberration;
        vec3 c=vec3(texture2D(scene,uv+d).r,texture2D(scene,uv).g,texture2D(scene,uv-d).b);
        if(useBloom>.5){vec3 b=texture2D(bloom,uv).rgb*bloomNorm;   // the pyramid sums its levels: normalise
          // physical: energy-conserving mix (dims sharp detail); add: AE-Glow-like; halo: adds only the spread
          // around bright things (b > c), so flat areas do not brighten and white text stays white.
          vec3 spread=max(b-max(c,vec3(halationThreshold)),0.);   // light that leaked past bright edges
          c=bloomMode<.5?mix(c,b,strength):bloomMode<1.5?c+b*strength:c+max(b-c,0.)*strength;
          c+=spread*halationTint*halation;}   // halation: a red fringe around highlights; flat areas stay untinted
        c*=exposure;c=tm(c);
        c=gain*(c+lift*(1.-c));c=pow(max(c,0.),vec3(1./max(gamma,1e-3)));
        c=mix(vec3(luma(c)),c,saturation);
        float r=length((uv-.5)*vec2(1.,1.));c*=1.-vignette*smoothstep(.25,.75,r);
        c=pow(max(c,0.),vec3(1./2.2));
        vec2 jump=vec2(hash(vec2(frame,1.)),hash(vec2(frame,7.)))*4096.;   // a new pattern every frame, never a slide
        c+=(hash(floor(uv*res)+jump)-.5)*grain;
        gl_FragColor=vec4(c,1.);}`,

    /* Screen print / risograph layer, run on the tone-mapped (sRGB) image. Two spot inks over paper:
       inkB from darkness (key), inkA from redness (accent), each as a rotated halftone (dot = cell in px),
       with misregistration (offA/offB in px), overprint by multiplication, uneven ink (texture 0–1) and paper
       grain. seed changes the ink texture: step it (12 fps) for a "boiling" print. inks = 1 → single ink
       (luminance only). strength mixes with the original: 0.25–0.4 = a subtle print layer over the piece. */
    screenPrint: HEAD + LUMA + HASH + `uniform sampler2D image;uniform vec2 res,offA,offB;uniform vec3 paper,inkA,inkB;
        uniform float cell,angleA,angleB,texture,seed,strength,inks;
      float vnoise(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
        return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x),mix(hash(i+vec2(0.,1.)),hash(i+1.),f.x),f.y);}
      float dots(vec2 px,float cov,float ang){float c=cos(ang),s=sin(ang);vec2 p=mat2(c,-s,s,c)*px/cell;
        float d=length(fract(p)-.5),r=sqrt(clamp(cov,0.,1.))*.66;return 1.-smoothstep(r-.07,r+.07,d);}
      void main(){vec2 px=uv*res;vec3 cA=texture2D(image,uv+offA/res).rgb,cB=texture2D(image,uv+offB/res).rgb;
        float kA=inks>1.5?clamp((cA.r-max(cA.g,cA.b))*1.9,0.,1.):0.;
        float kB=clamp((1.-luma(cB))*1.12-.04,0.,1.)*(1.-.75*kA);
        float ink=1.+texture*(vnoise(px*.08+seed*17.)-.5)*.9;
        float hA=dots(px,kA,angleA)*ink,hB=dots(px,kB,angleB)*ink;
        vec3 col=paper*mix(vec3(1.),inkA,clamp(hA,0.,1.))*mix(vec3(1.),inkB,clamp(hB,0.,1.));
        col*=1.-texture*.08*(hash(floor(px*.5)+seed)-.5);
        gl_FragColor=vec4(mix(texture2D(image,uv).rgb,col,strength),1.);}`,

    /* Compact CRT tube (see references/craft/retro-looks.md for the full two-pass recipe). */
    crt: HEAD + `uniform sampler2D image;uniform float curvature,scanline,grille,vignette;
      vec2 barrel(vec2 u){vec2 c=u-.5;float r=dot(c,c);return .5+c*(1.+curvature*r);}
      void main(){vec2 u=barrel(uv);if(u.x<0.||u.x>1.||u.y<0.||u.y>1.){gl_FragColor=vec4(0.,0.,0.,1.);return;}
        vec3 c=texture2D(image,u).rgb;float sl=1.-scanline+scanline*(.5+.5*cos(gl_FragCoord.y*2.0943951));
        float m=mod(gl_FragCoord.x,3.);vec3 g=vec3(m<1.?1.:1.-grille,(m>=1.&&m<2.)?1.:1.-grille,m>=2.?1.:1.-grille);
        c*=sl*g*(1.-vignette*dot(uv-.5,uv-.5)*2.);gl_FragColor=vec4(c,1.);}`,
  };

  const TONE_MAPS = {clip: 0, shoulder: 1, reinhard: 2, aces: 3};

  /* Circle of confusion radius in px for a plane at `distance` when the camera focuses at `focus`. */
  const cocPx = (distance, focus, aperture = 30, maxPx = 40) => Math.min(maxPx, aperture * Math.abs(distance - focus) / Math.max(distance, 1e-6));

  /* pos at which a lightSweep band of `angle` leaves a frame of this aspect (W/H), in frame heights. */
  const sweepExtent = (aspect, angle = -.5) => .5 * (Math.abs(Math.cos(angle)) * aspect + Math.abs(Math.sin(angle)));

  /* requireHdr (default true): fail clearly instead of silently rendering bloom and bokeh in 8 bits. */
  function runner(gl, {width, height, requireHdr = true} = {}) {
    const W = width || gl.drawingBufferWidth, H = height || gl.drawingBufferHeight;
    const half = gl.getExtension('OES_texture_half_float');
    const halfLinear = gl.getExtension('OES_texture_half_float_linear');
    const halfColor = gl.getExtension('EXT_color_buffer_half_float');
    const hdrType = half && halfLinear && halfColor ? half.HALF_FLOAT_OES : gl.UNSIGNED_BYTE;
    if (requireHdr && hdrType === gl.UNSIGNED_BYTE) throw new Error('PostFX: half-float render targets are not available (OES_texture_half_float, _linear, EXT_color_buffer_half_float); pass requireHdr: false to accept 8-bit');
    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
    const info = {renderer: debugInfo ? gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER), hdr: hdrType !== gl.UNSIGNED_BYTE};
    const quad = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, quad);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, 1, 1, -1, -1, 1, 1, -1, 1]), gl.STATIC_DRAW);
    const programs = new Map(), owned = [];

    function compile(type, source) {
      const s = gl.createShader(type);
      gl.shaderSource(s, source); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('PostFX shader: ' + gl.getShaderInfoLog(s));
      return s;
    }
    function program(source) {
      if (programs.has(source)) return programs.get(source);
      const p = gl.createProgram();
      gl.attachShader(p, compile(gl.VERTEX_SHADER, VERTEX)); gl.attachShader(p, compile(gl.FRAGMENT_SHADER, source));
      gl.linkProgram(p);
      if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('PostFX link: ' + gl.getProgramInfoLog(p));
      const entry = {p, point: gl.getAttribLocation(p, 'point'), uniforms: new Map()};
      programs.set(source, entry);
      return entry;
    }
    function target(w = W, h = H, {hdr = true} = {}) {
      const tex = gl.createTexture();
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, hdr ? hdrType : gl.UNSIGNED_BYTE, null);
      for (const k of [gl.TEXTURE_MIN_FILTER, gl.TEXTURE_MAG_FILTER]) gl.texParameteri(gl.TEXTURE_2D, k, gl.LINEAR);
      for (const k of [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T]) gl.texParameteri(gl.TEXTURE_2D, k, gl.CLAMP_TO_EDGE);
      const fb = gl.createFramebuffer();
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      if (gl.checkFramebufferStatus(gl.FRAMEBUFFER) !== gl.FRAMEBUFFER_COMPLETE) throw new Error(`PostFX framebuffer ${w}x${h} incomplete`);
      gl.bindFramebuffer(gl.FRAMEBUFFER, null);
      const t = {tex, fb, w, h, hdr: hdr && hdrType !== gl.UNSIGNED_BYTE};
      owned.push(t);
      return t;
    }
    /* Run one full-screen pass. uniforms: number → float, [n,n] → vec2…, {int: n} → int; textures: {name: target|WebGLTexture}.
       blend: null | 'add' | 'alpha'. scissor: [x, y, w, h] in target pixels from the bottom-left (limits drawing and clearing).
       clear: by default the target is cleared only when not blending; clear: true clears it before a blended draw too
       (the first sample of an accumulation), clear: false never clears. clearColor: [0, 0, 0, 0] for a layer with alpha. */
    function pass(source, {to = null, uniforms = {}, textures = {}, blend = null, clear = null, clearColor = [0, 0, 0, 1], scissor = null} = {}) {
      const prog = program(SHADERS[source] || source);
      gl.bindFramebuffer(gl.FRAMEBUFFER, to ? to.fb : null);
      gl.viewport(0, 0, to ? to.w : W, to ? to.h : H);
      gl.useProgram(prog.p);
      gl.disable(gl.DEPTH_TEST); gl.disable(gl.SCISSOR_TEST);
      if (scissor) { gl.enable(gl.SCISSOR_TEST); gl.scissor(...scissor); }
      if (blend === 'add') { gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE); }
      else if (blend === 'alpha') { gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA); }
      else gl.disable(gl.BLEND);
      if (clear === null ? !blend : clear) { gl.clearColor(...clearColor); gl.clear(gl.COLOR_BUFFER_BIT); }
      const loc = name => { if (!prog.uniforms.has(name)) prog.uniforms.set(name, gl.getUniformLocation(prog.p, name)); return prog.uniforms.get(name); };
      let unit = 0;
      for (const [name, value] of Object.entries(textures)) {
        gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, value && value.tex ? value.tex : value); gl.uniform1i(loc(name), unit++);
      }
      for (const [name, value] of Object.entries(uniforms)) {
        const l = loc(name);
        if (l === null) continue;
        if (value && typeof value === 'object' && 'int' in value) gl.uniform1i(l, value.int);
        else if (Array.isArray(value)) gl[`uniform${value.length}fv`](l, value);
        else gl.uniform1f(l, value);
      }
      gl.bindBuffer(gl.ARRAY_BUFFER, quad);
      gl.enableVertexAttribArray(prog.point);
      gl.vertexAttribPointer(prog.point, 2, gl.FLOAT, false, 8, 0);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      gl.disable(gl.BLEND);
      gl.disable(gl.SCISSOR_TEST);
    }
    const mips = [];
    let prefiltered = null, lastLevels = 1;
    /* Bloom pyramid. threshold: null = physical (whole HDR image, mix with small strength in finish);
       a number = AE-Glow-like look (soft-knee prefilter, add in finish). Returns the half-resolution bloom target. */
    function bloom(src, {levels = 6, radius = .005, threshold = null, knee = .5, karis = true} = {}) {
      while (mips.length < levels) { const d = 2 ** (mips.length + 1); mips.push(target(Math.max(1, Math.ceil(W / d)), Math.max(1, Math.ceil(H / d)))); }
      let input = src;
      if (threshold !== null) {
        prefiltered ||= target();
        pass('bloomPrefilter', {to: prefiltered, textures: {image: src}, uniforms: {threshold, knee}});
        input = prefiltered;
      }
      for (let i = 0; i < levels; i++) {
        pass('bloomDown', {to: mips[i], textures: {image: input}, uniforms: {texel: [1 / input.w, 1 / input.h], karis: i === 0 && karis ? 1 : 0}});
        input = mips[i];
      }
      lastLevels = levels;
      for (let i = levels - 1; i > 0; i--) {
        pass('bloomUp', {to: mips[i - 1], textures: {image: mips[i]}, uniforms: {radius: [radius * H / W, radius]}, blend: 'add', clear: false});
      }
      return mips[0];
    }
    /* bloomMode: 'halo' (default; light spreads around highlights without washing the frame),
       'physical' (energy-conserving mix: also dims sharp detail) or 'add' (AE Glow, use with a threshold).
       strength: halo 0.25–0.45; physical 0.1–0.3; add 1–4.
       halation: red fringe from the light that spreads past bright edges (film halation), 1–2.5. It never tints a
       flat area or the inside of a white letter; halationThreshold > 0 keeps it to brighter sources only. */
    function finish(scene, bloomTarget, {to = null, scissor = null, bloomMode = 'halo', strength = .35, halation = 0, halationTint = [1, .32, .12], halationThreshold = 0,
      exposure = 1, toneMap = 'shoulder', aberration = 0, vignette = 0, grain = 0, frame = 0, lift = 0, gamma = 1, gain = 1, saturation = 1} = {}) {
      pass('finish', {to, scissor, textures: {scene, bloom: bloomTarget || scene}, uniforms: {
        useBloom: bloomTarget ? 1 : 0, bloomMode: {physical: 0, add: 1, halo: 2}[bloomMode] ?? 2, bloomNorm: 1 / lastLevels, strength, halation, halationTint, halationThreshold, res: [W, H], exposure,
        toneMap: TONE_MAPS[toneMap] ?? toneMap, aberration, vignette, grain, frame: frame % 997, lift, gamma, gain, saturation}});
    }
    function dispose() {
      for (const t of owned) { gl.deleteTexture(t.tex); gl.deleteFramebuffer(t.fb); }
      for (const {p} of programs.values()) gl.deleteProgram(p);
      gl.deleteBuffer(quad);
    }
    return {W, H, hdr: hdrType !== gl.UNSIGNED_BYTE, info, target, pass, bloom, finish, dispose};
  }

  return {VERTEX, SHADERS, TONE_MAPS, cocPx, sweepExtent, runner};
});
