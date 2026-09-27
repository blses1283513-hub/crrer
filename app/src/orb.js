// Particle orb: a breathing sphere that re-forms into an animal per thinking stage.
const Orb = (() => {
  const ANIMALS = {
    elephant: "🐘", owl: "🦉", eagle: "🦅", octopus: "🐙", beaver: "🦫",
    fox: "🦊", dolphin: "🐬", whale: "🐋", squirrel: "🐿️", turtle: "🐢",
  };
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const cache = new Map();
  let N, renderer, scene, camera, group, points, geo, mat, rings = [], glow;
  let cur, target, delay, switchAt = 0, shape = "sphere", busy = 0, busyTarget = 0;
  let yaw = 0, pitch = 0, dragYaw = 0, dragPitch = 0, velYaw = 0, dragging = false, lastX = 0, lastY = 0;
  let mouse = { x: 9, y: 9, on: 0 }, host, clock = 0, last = 0, running = false;

  function sphere(n) {
    const out = new Float32Array(n * 3), g = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < n; i++) {
      const y = 1 - (i / (n - 1)) * 2, r = Math.sqrt(1 - y * y), t = g * i;
      const shell = 1 + (Math.random() - 0.5) * 0.035;
      out[i * 3] = Math.cos(t) * r * shell; out[i * 3 + 1] = y * shell; out[i * 3 + 2] = Math.sin(t) * r * shell;
    }
    return shuffle(out, n);
  }

  function shuffle(arr, n) {
    for (let i = n - 1; i > 0; i--) {
      const j = (Math.random() * (i + 1)) | 0;
      for (let k = 0; k < 3; k++) { const t = arr[i * 3 + k]; arr[i * 3 + k] = arr[j * 3 + k]; arr[j * 3 + k] = t; }
    }
    return arr;
  }

  // Fallback when the device draws no color emoji: a torus knot per animal.
  function knot(n, seed) {
    const out = new Float32Array(n * 3), p = 2 + (seed % 3), q = 3 + (seed % 4);
    for (let i = 0; i < n; i++) {
      const t = (i / n) * Math.PI * 2 * p, r = 0.62 + 0.28 * Math.cos((q / p) * t);
      const j = (Math.random() - 0.5) * 0.16;
      out[i * 3] = (r + j) * Math.cos(t); out[i * 3 + 1] = (r + j) * Math.sin(t);
      out[i * 3 + 2] = 0.28 * Math.sin((q / p) * t) + j;
    }
    return shuffle(out, n);
  }

  function animal(name) {
    if (cache.has(name)) return cache.get(name);
    const S = 200, cv = document.createElement("canvas");
    cv.width = cv.height = S;
    const cx = cv.getContext("2d", { willReadFrequently: true });
    cx.textAlign = "center"; cx.textBaseline = "middle";
    cx.font = `${S * 0.78}px "Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji","Twemoji Mozilla",sans-serif`;
    cx.fillText(ANIMALS[name], S / 2, S / 2 + S * 0.04);
    const img = cx.getImageData(0, 0, S, S).data;
    const inside = new Uint8Array(S * S), lum = new Float32Array(S * S);
    let count = 0, x0 = S, y0 = S, x1 = 0, y1 = 0;
    for (let i = 0; i < S * S; i++) {
      if (img[i * 4 + 3] > 60) {
        inside[i] = 1; count++;
        const x = i % S, y = (i / S) | 0;
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
      }
      lum[i] = (img[i * 4] * 0.3 + img[i * 4 + 1] * 0.59 + img[i * 4 + 2] * 0.11) * (img[i * 4 + 3] / 255);
    }
    const box = (x1 - x0 + 1) * (y1 - y0 + 1);
    let out;
    if (count < 500 || count / box > 0.93) {
      out = knot(N, Object.keys(ANIMALS).indexOf(name));
    } else {
      // Chamfer distance to the outline gives each silhouette a rounded depth.
      const d = new Float32Array(S * S);
      for (let i = 0; i < S * S; i++) d[i] = inside[i] ? 1e4 : 0;
      for (let y = 1; y < S - 1; y++) for (let x = 1; x < S - 1; x++) {
        const i = y * S + x; if (!d[i]) continue;
        d[i] = Math.min(d[i], d[i - 1] + 1, d[i - S] + 1, d[i - S - 1] + 1.4, d[i - S + 1] + 1.4);
      }
      for (let y = S - 2; y > 0; y--) for (let x = S - 2; x > 0; x--) {
        const i = y * S + x; if (!d[i]) continue;
        d[i] = Math.min(d[i], d[i + 1] + 1, d[i + S] + 1, d[i + S + 1] + 1.4, d[i + S - 1] + 1.4);
      }
      let dmax = 1; const fill = [], edge = [];
      for (let y = 1; y < S - 1; y++) for (let x = 1; x < S - 1; x++) {
        const i = y * S + x; if (!inside[i]) continue;
        dmax = Math.max(dmax, d[i]); fill.push(i);
        const gx = lum[i + 1] - lum[i - 1], gy = lum[i + S] - lum[i - S];
        if (d[i] <= 1.5 || gx * gx + gy * gy > 1600) edge.push(i);
      }
      const scale = 2.25 / Math.max(x1 - x0, y1 - y0), mx = (x0 + x1) / 2, my = (y0 + y1) / 2;
      out = new Float32Array(N * 3);
      for (let k = 0; k < N; k++) {
        const fromEdge = Math.random() < 0.3 && edge.length;
        const i = fromEdge ? edge[(Math.random() * edge.length) | 0] : fill[(Math.random() * fill.length) | 0];
        const x = (i % S) + Math.random() - 0.5, y = ((i / S) | 0) + Math.random() - 0.5;
        const depth = Math.sqrt(d[i] / dmax) * 0.42 * (fromEdge ? 1 : Math.random() * 0.35 + 0.65);
        out[k * 3] = (x - mx) * scale;
        out[k * 3 + 1] = -(y - my) * scale;
        out[k * 3 + 2] = (Math.random() < 0.5 ? -1 : 1) * depth;
      }
    }
    cache.set(name, out);
    return out;
  }

  const VERT = `
    attribute float aSeed;
    uniform float uTime, uSize, uRatio, uBusy, uMouseOn;
    uniform vec2 uMouse;
    varying float vDepth, vSeed;
    void main() {
      vec3 p = position;
      float n = sin(uTime * 1.4 + aSeed * 6.283 + p.y * 3.0) * (0.010 + 0.018 * uBusy);
      p += normalize(p + 1e-5) * n;
      vec4 mv = modelViewMatrix * vec4(p, 1.0);
      vec4 clip = projectionMatrix * mv;
      vec2 dv = clip.xy / clip.w - uMouse;
      float push = uMouseOn * smoothstep(0.32, 0.0, length(dv)) * 0.22;
      mv.xy += normalize(dv + 1e-5) * push;
      gl_Position = projectionMatrix * mv;
      gl_PointSize = uSize * (0.55 + aSeed * 0.9) * uRatio * (3.4 / -mv.z);
      vDepth = clamp((mv.z + 4.3) / 2.4, 0.0, 1.0);
      vSeed = aSeed;
    }`;
  const FRAG = `
    uniform vec3 uDeep, uMid, uLight;
    uniform float uTime;
    varying float vDepth, vSeed;
    void main() {
      float d = length(gl_PointCoord - 0.5);
      if (d > 0.5) discard;
      float a = smoothstep(0.5, 0.0, d); a *= a;
      vec3 col = mix(uDeep, uMid, vDepth);
      col = mix(col, uLight, smoothstep(0.7, 1.0, vDepth) * 0.85 + step(0.94, vSeed) * 0.6);
      float tw = 0.78 + 0.22 * sin(uTime * 2.1 + vSeed * 40.0);
      gl_FragColor = vec4(col, a * tw * (0.3 + 0.7 * vDepth));
    }`;

  function ring(radius, tiltX, tiltZ) {
    const pts = [];
    for (let i = 0; i <= 128; i++) {
      const t = (i / 128) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(t) * radius, 0, Math.sin(t) * radius));
    }
    const line = new THREE.LineLoop(
      new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({ color: 0x4f8dff, transparent: true, opacity: 0.16, blending: THREE.AdditiveBlending, depthWrite: false }),
    );
    line.rotation.set(tiltX, 0, tiltZ);
    return line;
  }

  function glowTexture() {
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const g = c.getContext("2d"), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
    r.addColorStop(0, "rgba(90,160,255,0.55)"); r.addColorStop(0.45, "rgba(30,90,220,0.18)"); r.addColorStop(1, "rgba(0,20,80,0)");
    g.fillStyle = r; g.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(c);
  }

  function init(el) {
    host = el;
    if (!window.THREE) return false;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    } catch { return false; }
    N = matchMedia("(max-width: 640px)").matches ? 4200 : 7000;
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
    camera.position.set(0, 0, 3.4);
    group = new THREE.Group(); scene.add(group);

    cur = sphere(N); target = new Float32Array(cur); delay = new Float32Array(N);
    const seeds = new Float32Array(N);
    for (let i = 0; i < N; i++) { seeds[i] = Math.random(); delay[i] = Math.random() * 0.45; }
    geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(cur, 3));
    geo.setAttribute("aSeed", new THREE.BufferAttribute(seeds, 1));
    mat = new THREE.ShaderMaterial({
      vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      uniforms: {
        uTime: { value: 0 }, uSize: { value: 5.2 }, uRatio: { value: renderer.getPixelRatio() }, uBusy: { value: 0 },
        uMouse: { value: new THREE.Vector2(9, 9) }, uMouseOn: { value: 0 },
        uDeep: { value: new THREE.Color("#0b3d91") }, uMid: { value: new THREE.Color("#2f7bff") }, uLight: { value: new THREE.Color("#bfe6ff") },
      },
    });
    points = new THREE.Points(geo, mat); group.add(points);
    rings = [ring(1.32, 1.2, 0.3), ring(1.46, 1.75, -0.5), ring(1.22, 0.4, 1.1)];
    rings.forEach((r) => scene.add(r));
    glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    glow.scale.set(4.2, 4.2, 1); glow.position.z = -1; scene.add(glow);

    new ResizeObserver(resize).observe(el); resize();
    bindPointer(el);
    document.addEventListener("visibilitychange", () => { if (!document.hidden) start(); });
    start();
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
    const since = clock - switchAt, k = reduced ? 1 : Math.min(1, dt * 4.2);
    let moving = false;
    for (let i = 0; i < N; i++) {
      if (since < delay[i] && !reduced) { moving = true; continue; }
      const j = i * 3;
      for (let a = 0; a < 3; a++) {
        const diff = target[j + a] - cur[j + a];
        if (diff > 1e-4 || diff < -1e-4) { cur[j + a] += diff * k; moving = true; }
      }
    }
    if (moving) geo.attributes.position.needsUpdate = true;

    if (!dragging) { dragYaw += velYaw; velYaw *= 0.93; dragPitch *= 0.96; }
    if (!reduced) {
      if (shape === "sphere") yaw += dt * (0.14 + busy * 0.5);
      else {
        const want = Math.sin(clock * 0.55) * 0.5;
        let diff = ((want - yaw) % (Math.PI * 2) + Math.PI * 3) % (Math.PI * 2) - Math.PI;
        yaw += diff * Math.min(1, dt * 2.2);
      }
    }
    pitch += ((shape === "sphere" ? 0.18 : 0.05) - pitch) * Math.min(1, dt * 2);
    group.rotation.set(pitch + dragPitch, yaw + dragYaw, 0);
    const ringAlpha = shape === "sphere" ? 0.16 + busy * 0.12 : 0.05;
    rings.forEach((r, i) => {
      if (!reduced) r.rotation.y += dt * (0.06 + i * 0.03) * (1 + busy * 3);
      r.material.opacity += (ringAlpha - r.material.opacity) * Math.min(1, dt * 3);
    });
    glow.material.opacity = 0.75 + busy * 0.25 + Math.sin(clock * 1.6) * 0.06 * (1 + busy);
    const u = mat.uniforms;
    u.uTime.value = clock; u.uBusy.value = busy;
    u.uMouse.value.set(mouse.x, mouse.y);
    u.uMouseOn.value += ((reduced ? 0 : mouse.on) - u.uMouseOn.value) * Math.min(1, dt * 5);
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  function setShape(name) {
    if (!renderer || name === shape) return;
    shape = name in ANIMALS ? name : "sphere";
    target = shape === "sphere" ? sphere(N) : animal(shape);
    switchAt = clock;
    start();
  }

  function setBusy(on) { busyTarget = on ? 1 : 0; if (!on) setShape("sphere"); start(); }

  return { init, setShape, setBusy, ANIMALS };
})();
