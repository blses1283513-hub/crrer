// Particle orb: a breathing sphere that re-forms into a moving animal per thinking stage.
// Animals are real rigged glTF models; each frame the particles are re-sampled from the
// animated surface (morph targets or skinning), lit by the surface normal and shaded by
// the model's own vertex colors or texture.
const Orb = (() => {
  const ANIMALS = {
    horse: { file: "animals/horse.txt", clip: 0, yaw: Math.PI / 2, emoji: "🐎", speed: 1 },
    flamingo: { file: "animals/flamingo.txt", clip: 0, yaw: 0, emoji: "🦩", speed: 0.9 },
    parrot: { file: "animals/parrot.txt", clip: 0, yaw: 0, emoji: "🦜", speed: 1 },
    stork: { file: "animals/stork.txt", clip: 0, yaw: Math.PI / 2, emoji: "🐦", speed: 0.85 },
    foxSurvey: { file: "animals/fox.txt", clip: "Survey", yaw: 0, emoji: "🦊", speed: 1 },
    foxWalk: { file: "animals/fox.txt", clip: "Walk", yaw: 0, emoji: "🦊", speed: 1 },
    foxRun: { file: "animals/fox.txt", clip: "Run", yaw: 0, emoji: "🦊", speed: 0.8 },
  };
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const models = new Map(), rigs = new Map(), silhouettes = new Map();
  let N, renderer, scene, camera, group, geo, mat, rings = [], glow;
  let cur, curN, curS, tgt, tgtN, tgtS, delay, switchAt = 0, shape = "sphere", live = null, busy = 0, busyTarget = 0;
  let yaw = 0, pitch = 0, dragYaw = 0, dragPitch = 0, velYaw = 0, dragging = false, lastX = 0, lastY = 0;
  let mouse = { x: 9, y: 9, on: 0 }, host, clock = 0, last = 0, running = false, token = 0;

  function shuffleIdx(n) {
    const a = new Uint32Array(n); for (let i = 0; i < n; i++) a[i] = i;
    for (let i = n - 1; i > 0; i--) { const j = (Math.random() * (i + 1)) | 0; const t = a[i]; a[i] = a[j]; a[j] = t; }
    return a;
  }

  function sphere() {
    const p = new Float32Array(N * 3), nrm = new Float32Array(N * 3), s = new Float32Array(N).fill(1);
    const g = Math.PI * (3 - Math.sqrt(5)), order = shuffleIdx(N);
    for (let k = 0; k < N; k++) {
      const i = order[k], y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), t = g * i, sh = 1 + (Math.random() - 0.5) * 0.035;
      nrm[k * 3] = Math.cos(t) * r; nrm[k * 3 + 1] = y; nrm[k * 3 + 2] = Math.sin(t) * r;
      p[k * 3] = nrm[k * 3] * sh; p[k * 3 + 1] = y * sh; p[k * 3 + 2] = nrm[k * 3 + 2] * sh;
    }
    return { p, n: nrm, s };
  }

  // ---------- rigged models ----------
  function loadModel(file) {
    if (models.has(file)) return models.get(file);
    // Models ship as base64 text: artifacts serve .txt but not .glb.
    const pr = fetch(file).then((r) => { if (!r.ok) throw new Error(r.status); return r.text(); })
      .then((b64) => { const bin = atob(b64.trim()), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i); return u8.buffer; })
      .then((buf) => new Promise((ok, bad) => new THREE.GLTFLoader().parse(buf, "", ok, bad)));
    models.set(file, pr);
    return pr;
  }

  function textureLum(tex) {
    const img = tex?.image;
    if (!img || !img.width) return null;
    const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
    const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height).data;
    return (u, v) => {
      u = ((u % 1) + 1) % 1; v = ((v % 1) + 1) % 1;
      const i = ((Math.min(c.height - 1, (v * c.height) | 0)) * c.width + Math.min(c.width - 1, (u * c.width) | 0)) * 4;
      return (d[i] * 0.3 + d[i + 1] * 0.59 + d[i + 2] * 0.11) / 255;
    };
  }

  async function rig(name) {
    if (rigs.has(name)) return rigs.get(name);
    const spec = ANIMALS[name];
    const gltf = await loadModel(spec.file);
    const root = THREE.SkeletonUtils ? THREE.SkeletonUtils.clone(gltf.scene) : gltf.scene;
    let mesh = null;
    root.traverse((o) => { if (!mesh && (o.isSkinnedMesh || o.isMesh)) mesh = o; });
    const g = mesh.geometry, pos = g.attributes.position, idx = g.index;
    const tris = idx ? idx.array : Uint32Array.from({ length: pos.count }, (_, i) => i);
    const morphs = g.morphAttributes.position || [], relative = g.morphTargetsRelative;
    const clip = typeof spec.clip === "number" ? gltf.animations[spec.clip] : gltf.animations.find((a) => a.name === spec.clip) || gltf.animations[0];
    const mixer = new THREE.AnimationMixer(root);
    mixer.clipAction(clip).play();

    // Area-weighted surface samples in the bind pose.
    const nt = tris.length / 3, cum = new Float32Array(nt), A = new THREE.Vector3(), B = new THREE.Vector3(), C = new THREE.Vector3();
    let total = 0;
    for (let t = 0; t < nt; t++) {
      A.fromBufferAttribute(pos, tris[t * 3]); B.fromBufferAttribute(pos, tris[t * 3 + 1]); C.fromBufferAttribute(pos, tris[t * 3 + 2]);
      total += B.sub(A).cross(C.sub(A)).length() / 2; cum[t] = total;
    }
    const sTri = new Uint32Array(N), sU = new Float32Array(N), sV = new Float32Array(N), shade = new Float32Array(N);
    const color = g.attributes.color, uv = g.attributes.uv, lum = textureLum(mesh.material?.map);
    for (let k = 0; k < N; k++) {
      const r = Math.random() * total;
      let lo = 0, hi = nt - 1;
      while (lo < hi) { const m = (lo + hi) >> 1; if (cum[m] < r) lo = m + 1; else hi = m; }
      let u = Math.random(), v = Math.random();
      if (u + v > 1) { u = 1 - u; v = 1 - v; }
      sTri[k] = lo; sU[k] = u; sV[k] = v;
      const [a, b, c] = [tris[lo * 3], tris[lo * 3 + 1], tris[lo * 3 + 2]], w = 1 - u - v;
      let L = 0.8;
      if (lum && uv) L = lum(w * uv.getX(a) + u * uv.getX(b) + v * uv.getX(c), w * uv.getY(a) + u * uv.getY(b) + v * uv.getY(c));
      else if (color) {
        const l = (i) => color.getX(i) * 0.3 + color.getY(i) * 0.59 + color.getZ(i) * 0.11;
        L = w * l(a) + u * l(b) + v * l(c);
      }
      shade[k] = 0.35 + 0.65 * Math.min(1, L * 1.25);
    }

    const verts = new Float32Array(pos.count * 3), tmp = new THREE.Vector3();
    function pose(t) {
      mixer.setTime(t);
      root.updateMatrixWorld(true);
      const inf = mesh.morphTargetInfluences, mw = mesh.matrixWorld;
      for (let i = 0; i < pos.count; i++) {
        if (mesh.isSkinnedMesh) mesh.boneTransform(i, tmp);
        else {
          tmp.fromBufferAttribute(pos, i);
          if (inf) for (let j = 0; j < morphs.length; j++) {
            const f = inf[j]; if (!f) continue;
            const m = morphs[j];
            if (relative) { tmp.x += f * m.getX(i); tmp.y += f * m.getY(i); tmp.z += f * m.getZ(i); }
            else { tmp.x += f * (m.getX(i) - pos.getX(i)); tmp.y += f * (m.getY(i) - pos.getY(i)); tmp.z += f * (m.getZ(i) - pos.getZ(i)); }
          }
        }
        tmp.applyMatrix4(mw);
        verts[i * 3] = tmp.x; verts[i * 3 + 1] = tmp.y; verts[i * 3 + 2] = tmp.z;
      }
    }

    // Frame the whole motion: bounding box over the loop, then center and scale.
    const lo3 = [Infinity, Infinity, Infinity], hi3 = [-Infinity, -Infinity, -Infinity];
    for (let s = 0; s < 8; s++) {
      pose((clip.duration * s) / 8);
      for (let i = 0; i < pos.count; i++) for (let a = 0; a < 3; a++) {
        const x = verts[i * 3 + a]; if (x < lo3[a]) lo3[a] = x; if (x > hi3[a]) hi3[a] = x;
      }
    }
    const ctr = lo3.map((l, a) => (l + hi3[a]) / 2), scale = 2.35 / Math.max(hi3[0] - lo3[0], hi3[1] - lo3[1], hi3[2] - lo3[2]);
    const cy = Math.cos(spec.yaw), sy = Math.sin(spec.yaw);

    function fill(t, P, Nn) {
      pose(t);
      for (let k = 0; k < N; k++) {
        const tr = sTri[k], a = tris[tr * 3] * 3, b = tris[tr * 3 + 1] * 3, c = tris[tr * 3 + 2] * 3, u = sU[k], v = sV[k], w = 1 - u - v;
        let x = w * verts[a] + u * verts[b] + v * verts[c] - ctr[0];
        const y = w * verts[a + 1] + u * verts[b + 1] + v * verts[c + 1] - ctr[1];
        let z = w * verts[a + 2] + u * verts[b + 2] + v * verts[c + 2] - ctr[2];
        const rx = x * cy + z * sy, rz = -x * sy + z * cy;
        P[k * 3] = rx * scale; P[k * 3 + 1] = y * scale; P[k * 3 + 2] = rz * scale;
        const e1x = verts[b] - verts[a], e1y = verts[b + 1] - verts[a + 1], e1z = verts[b + 2] - verts[a + 2];
        const e2x = verts[c] - verts[a], e2y = verts[c + 1] - verts[a + 1], e2z = verts[c + 2] - verts[a + 2];
        let nx = e1y * e2z - e1z * e2y, ny = e1z * e2x - e1x * e2z, nz = e1x * e2y - e1y * e2x;
        const l = Math.hypot(nx, ny, nz) || 1; nx /= l; ny /= l; nz /= l;
        Nn[k * 3] = nx * cy + nz * sy; Nn[k * 3 + 1] = ny; Nn[k * 3 + 2] = -nx * sy + nz * cy;
      }
    }
    const r = { fill, shade, duration: clip.duration, speed: spec.speed };
    rigs.set(name, r);
    return r;
  }

  // ---------- emoji silhouette fallback ----------
  function silhouette(name) {
    if (silhouettes.has(name)) return silhouettes.get(name);
    const S = 200, cv = document.createElement("canvas"); cv.width = cv.height = S;
    const cx = cv.getContext("2d", { willReadFrequently: true });
    cx.textAlign = "center"; cx.textBaseline = "middle";
    cx.font = `${S * 0.78}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif`;
    cx.fillText(ANIMALS[name]?.emoji || "🐋", S / 2, S / 2 + S * 0.04);
    const img = cx.getImageData(0, 0, S, S).data, fill = [];
    let x0 = S, y0 = S, x1 = 0, y1 = 0;
    for (let i = 0; i < S * S; i++) if (img[i * 4 + 3] > 60) {
      fill.push(i); const x = i % S, y = (i / S) | 0;
      x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
    }
    const out = sphere();
    if (fill.length > 500 && fill.length / ((x1 - x0 + 1) * (y1 - y0 + 1)) < 0.93) {
      const sc = 2.2 / Math.max(x1 - x0, y1 - y0), mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
      for (let k = 0; k < N; k++) {
        const i = fill[(Math.random() * fill.length) | 0];
        out.p[k * 3] = ((i % S) - mx) * sc; out.p[k * 3 + 1] = -(((i / S) | 0) - my) * sc; out.p[k * 3 + 2] = (Math.random() - 0.5) * 0.3;
        out.n[k * 3] = 0; out.n[k * 3 + 1] = 0; out.n[k * 3 + 2] = 1; out.s[k] = 0.85;
      }
    }
    silhouettes.set(name, out);
    return out;
  }

  // ---------- rendering ----------
  const VERT = `
    attribute float aSeed, aShade;
    attribute vec3 aNormal;
    uniform float uTime, uSize, uRatio, uBusy, uMouseOn;
    uniform vec2 uMouse;
    varying float vDepth, vSeed, vLight;
    void main() {
      vec3 p = position;
      p += aNormal * sin(uTime * 1.4 + aSeed * 6.283 + p.y * 3.0) * (0.006 + 0.01 * uBusy);
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      vec4 clip = projectionMatrix * mv;
      vec2 dv = clip.xy / clip.w - uMouse;
      mv.xy += normalize(dv + 1e-5) * uMouseOn * smoothstep(0.32, 0.0, length(dv)) * 0.22;
      gl_Position = projectionMatrix * mv;
      gl_PointSize = uSize * (0.55 + aSeed * 0.8) * uRatio * (3.4 / -mv.z);
      vec3 n = normalize(normalMatrix * aNormal);
      float key = abs(dot(n, normalize(vec3(-0.45, 0.7, 0.55))));
      float rim = pow(1.0 - abs(n.z), 2.0);
      vLight = aShade * (0.28 + 0.72 * key) + rim * 0.35;
      vDepth = clamp((mv.z + 4.3) / 2.4, 0.0, 1.0);
      vSeed = aSeed;
    }`;
  const FRAG = `
    uniform vec3 uDeep, uMid, uLight;
    uniform float uTime;
    varying float vDepth, vSeed, vLight;
    void main() {
      float d = length(gl_PointCoord - 0.5);
      if (d > 0.5) discard;
      float a = smoothstep(0.5, 0.0, d); a *= a;
      float b = clamp(vLight * (0.55 + 0.45 * vDepth), 0.0, 1.2);
      vec3 col = mix(uDeep, uMid, smoothstep(0.1, 0.6, b));
      col = mix(col, uLight, smoothstep(0.6, 1.05, b) + step(0.95, vSeed) * 0.5);
      float tw = 0.82 + 0.18 * sin(uTime * 2.1 + vSeed * 40.0);
      gl_FragColor = vec4(col, a * tw * (0.25 + 0.75 * b));
    }`;

  function ring(radius, tiltX, tiltZ) {
    const pts = [];
    for (let i = 0; i <= 128; i++) { const t = (i / 128) * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(t) * radius, 0, Math.sin(t) * radius)); }
    const line = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({ color: 0x4f8dff, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false }));
    line.rotation.set(tiltX, 0, tiltZ);
    return line;
  }

  function glowTexture() {
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const g = c.getContext("2d"), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    r.addColorStop(0, "rgba(90,160,255,0.5)"); r.addColorStop(0.45, "rgba(30,90,220,0.16)"); r.addColorStop(1, "rgba(0,20,80,0)");
    g.fillStyle = r; g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  }

  function init(el) {
    host = el;
    if (!window.THREE) return false;
    try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" }); } catch { return false; }
    N = matchMedia("(max-width: 640px)").matches ? 4500 : 7000;
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
    camera.position.set(0, 0, 3.4);
    group = new THREE.Group(); scene.add(group);

    const s0 = sphere();
    cur = s0.p; curN = s0.n; curS = s0.s;
    tgt = new Float32Array(cur); tgtN = new Float32Array(curN); tgtS = new Float32Array(curS);
    delay = new Float32Array(N);
    const seeds = new Float32Array(N);
    for (let i = 0; i < N; i++) { seeds[i] = Math.random(); delay[i] = Math.random() * 0.45; }
    geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(cur, 3));
    geo.setAttribute("aNormal", new THREE.BufferAttribute(curN, 3));
    geo.setAttribute("aShade", new THREE.BufferAttribute(curS, 1));
    geo.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    mat = new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 }, uSize: { value: 4.6 }, uRatio: { value: renderer.getPixelRatio() }, uBusy: { value: 0 },
        uMouse: { value: new THREE.Vector2(9, 9) }, uMouseOn: { value: 0 },
        uDeep: { value: new THREE.Color("#0b3d91") }, uMid: { value: new THREE.Color("#2f7bff") }, uLight: { value: new THREE.Color("#cfeeff") },
      },
    });
    group.add(new THREE.Points(geo, mat));
    rings = [ring(1.32, 1.2, 0.3), ring(1.46, 1.75, -0.5), ring(1.22, 0.4, 1.1)];
    rings.forEach((r) => scene.add(r));
    glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    glow.scale.set(4.2, 4.2, 1); glow.position.z = -1; scene.add(glow);

    new ResizeObserver(resize).observe(el); resize();
    bindPointer(el);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) start(); });
    start();
    // Warm the model cache so the first stage transforms without a pause.
    if (THREE.GLTFLoader) setTimeout(() => ["foxSurvey", "stork", "horse"].forEach((n) => rig(n).catch(() => {})), 800);
    return true;
  }

  function resize() {
    const w = host.clientWidth || 1, h = host.clientHeight || 1;
    renderer.setSize(w, h, false);
    camera.aspect = w / h; camera.updateProjectionMatrix();
  }

  function bindPointer(el) {
    el.addEventListener("pointerdown", (e) => { dragging = true; lastX = e.clientX; lastY = e.clientY; el.setPointerCapture(e.pointerId); });
    el.addEventListener("pointermove", (e) => {
      const r = el.getBoundingClientRect();
      mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1; mouse.y = -(((e.clientY - r.top) / r.height) * 2 - 1); mouse.on = 1;
      if (!dragging) return;
      const dx = e.clientX - lastX, dy = e.clientY - lastY; lastX = e.clientX; lastY = e.clientY;
      dragYaw += dx * 0.008; velYaw = dx * 0.008; dragPitch = Math.max(-0.8, Math.min(0.8, dragPitch + dy * 0.006));
    });
    const up = () => { dragging = false; };
    el.addEventListener("pointerup", up); el.addEventListener("pointercancel", up);
    el.addEventListener("pointerleave", () => { mouse.on = 0; });
  }

  function start() { if (!running && renderer) { running = true; last = performance.now(); requestAnimationFrame(frame); } }

  function frame(now) {
    if (document.hidden) { running = false; return; }
    const dt = Math.min(0.05, (now - last) / 1000); last = now; clock += dt;
    busy += (busyTarget - busy) * Math.min(1, dt * 3);
    if (live) live.fill(((clock - switchAt) * live.speed) % live.duration, tgt, tgtN);
    const since = clock - switchAt;
    // Ease in while re-forming, then track the animation exactly.
    const k = reduced || since > 1.6 ? 1 : Math.min(1, dt * 4.5);
    for (let i = 0; i < N; i++) {
      if (!reduced && since < delay[i]) continue;
      const j = i * 3;
      cur[j] += (tgt[j] - cur[j]) * k; cur[j + 1] += (tgt[j + 1] - cur[j + 1]) * k; cur[j + 2] += (tgt[j + 2] - cur[j + 2]) * k;
      curN[j] += (tgtN[j] - curN[j]) * k; curN[j + 1] += (tgtN[j + 1] - curN[j + 1]) * k; curN[j + 2] += (tgtN[j + 2] - curN[j + 2]) * k;
      curS[i] += (tgtS[i] - curS[i]) * k;
    }
    geo.attributes.position.needsUpdate = true; geo.attributes.aNormal.needsUpdate = true; geo.attributes.aShade.needsUpdate = true;

    if (!dragging) { dragYaw += velYaw; velYaw *= 0.93; dragPitch *= 0.96; }
    if (!reduced) {
      if (shape === "sphere") yaw += dt * (0.14 + busy * 0.5);
      else {
        const want = -0.35 + Math.sin(clock * 0.4) * 0.35;
        const diff = ((want - yaw) % (Math.PI * 2) + Math.PI * 3) % (Math.PI * 2) - Math.PI;
        yaw += diff * Math.min(1, dt * 2.2);
      }
    }
    pitch += ((shape === "sphere" ? 0.18 : 0.08) - pitch) * Math.min(1, dt * 2);
    group.rotation.set(pitch + dragPitch, yaw + dragYaw, 0);
    const ringAlpha = shape === "sphere" ? 0.16 + busy * 0.12 : 0.04;
    rings.forEach((r, i) => {
      if (!reduced) r.rotation.y += dt * (0.06 + i * 0.03) * (1 + busy * 3);
      r.material.opacity += (ringAlpha - r.material.opacity) * Math.min(1, dt * 3);
    });
    glow.material.opacity = 0.7 + busy * 0.25 + Math.sin(clock * 1.6) * 0.06 * (1 + busy);
    const u = mat.uniforms;
    u.uTime.value = clock; u.uBusy.value = busy;
    u.uMouse.value.set(mouse.x, mouse.y);
    u.uMouseOn.value += ((reduced ? 0 : mouse.on) - u.uMouseOn.value) * Math.min(1, dt * 5);
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  function apply(target) {
    tgt = target.p; tgtN = target.n; tgtS = target.s;
    switchAt = clock;
    start();
  }

  async function setShape(name) {
    if (!renderer || name === shape) return;
    const my = ++token;
    shape = name in ANIMALS ? name : "sphere";
    if (shape === "sphere") { live = null; apply(sphere()); return; }
    try {
      if (!THREE.GLTFLoader) throw new Error("no loader");
      const r = await rig(shape);
      if (my !== token) return;
      live = r;
      apply({ p: new Float32Array(N * 3), n: new Float32Array(N * 3), s: r.shade });
      r.fill(0, tgt, tgtN);
    } catch {
      if (my !== token) return;
      live = null; apply(silhouette(shape));
    }
  }

  function setBusy(on) { busyTarget = on ? 1 : 0; if (!on) setShape("sphere"); start(); }

  return { init, setShape, setBusy, ANIMALS };
})();
