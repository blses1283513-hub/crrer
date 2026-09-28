// Procedural zoo: each species is a set of anatomical parts (ellipsoids, tapered tubes, membranes)
// posed per frame by its own gait. Particles are sampled over the parts once and re-placed every frame,
// so the animal walks, hops, flies, swims or crawls while Lin Brain thinks.
const Zoo = (() => {
  const TAU = Math.PI * 2;
  const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
  const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
  const len = (a) => Math.hypot(a[0], a[1], a[2]);
  const norm = (a) => { const l = len(a) || 1; return [a[0] / l, a[1] / l, a[2] / l]; };
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const mix = (a, b, s) => [a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, a[2] + (b[2] - a[2]) * s];
  const lerp = (a, b, s) => a + (b - a) * s;
  const dn = (ang) => [Math.sin(ang), -Math.cos(ang), 0]; // 0 = straight down, + swings forward (+x)
  const fw = (ang) => [Math.cos(ang), Math.sin(ang), 0]; // 0 = forward, + tilts up
  const pos = (x) => Math.max(0, x);
  function basis(d) {
    const x = norm(d);
    let z = cross(x, [0, 1, 0]);
    if (len(z) < 1e-3) z = cross(x, [0, 0, 1]);
    z = norm(z);
    return [x, cross(z, x), z];
  }

  // Parts. o.w = sampling weight (eyes get more), o.pat = marking pattern on local coords.
  const E = (c, d, r, sh = 0.8, o = {}) => ({ k: 0, c, B: basis(d), r, sh, ...o });
  const T = (a, b, r0, r1, sh = 0.75, o = {}) => ({ k: 1, a, b, r0, r1, sh, ...o });
  const Q = (p0, p1, p2, p3, sh = 0.7, o = {}) => ({ k: 2, p: [p0, p1, p2, p3], sh, ...o });
  const eyes = (parts, c, d, side, r, spread) => {
    for (const s of [1, -1]) parts.push(E(add(c, [0, 0, s * spread]), d, [r, r, r * 0.8], 1.9, { w: 6 }));
  };

  // Marking patterns: u is the particle's local coordinate on its part.
  const STRIPES = (f) => (u) => (Math.sin(u[0] * f * Math.PI + Math.sin(u[1] * 4) * 0.9) > 0 ? 1 : 0.32);
  const SPOTS = (f, dark = 0.4) => (u) => (Math.sin(u[0] * f) * Math.sin(u[1] * f * 1.3 + 1) * Math.sin(u[2] * f * 0.9 + 2) > 0.07 ? dark : 1);
  const BELLY = (k = 1.45) => (u) => (u[1] < -0.15 ? k : 1);
  const BANDS = (f) => (u) => (Math.sin(u[0] * f * Math.PI) > 0 ? 1.1 : 0.3);
  const COAT = (u) => 0.82 + 0.18 * Math.sin(u[0] * 23 + u[1] * 17 + u[2] * 11);

  // Rotate every part about a pivot (used for rolls, pitches and head turns).
  function rotate(parts, axis, ang, pivot = [0, 0, 0]) {
    const c = Math.cos(ang), s = Math.sin(ang);
    const rv = (v) => axis === "x" ? [v[0], v[1] * c - v[2] * s, v[1] * s + v[2] * c]
      : axis === "y" ? [v[0] * c + v[2] * s, v[1], -v[0] * s + v[2] * c]
      : [v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2]];
    const rp = (p) => add(rv(sub(p, pivot)), pivot);
    for (const p of parts) {
      if (p.k === 0) { p.c = rp(p.c); p.B = p.B.map(rv); }
      else if (p.k === 1) { p.a = rp(p.a); p.b = rp(p.b); }
      else p.p = p.p.map(rp);
    }
    return parts;
  }

  // ---------------- quadrupeds ----------------
  // Footfall timing from gait studies (Muybridge's photographs, Hildebrand's gait diagrams).
  // Offsets are the phase at which each foot touches down, in order [LH, LF, RH, RF]; duty = stance fraction.
  const GAITS = {
    walk: { off: [0, 0.25, 0.5, 0.75], duty: 0.66, bob: 2 },    // four-beat lateral-sequence walk
    amble: { off: [0, 0.25, 0.5, 0.75], duty: 0.55, bob: 2 },   // elephant: fast walk, no suspension
    pace: { off: [0, 0.02, 0.5, 0.52], duty: 0.6, bob: 2 },     // giraffe, camel: same-side legs together
    trot: { off: [0, 0.5, 0.5, 0], duty: 0.46, bob: 2 },        // diagonal pairs
    gallop: { off: [0, 0.5, 0.12, 0.6], duty: 0.34, bob: 1 },   // transverse gallop
    rotary: { off: [0, 0.62, 0.1, 0.5], duty: 0.28, bob: 1 },   // cheetah: rotary gallop with spine flex
  };
  const LEGTYPE = { hoof: [0.36, 0.34, 0.3], paw: [0.4, 0.37, 0.23], plant: [0.47, 0.43, 0.1], column: [0.52, 0.44, 0.04] };

  // Two-bone IK in the leg's plane; bend > 0 puts the middle joint behind the line (elbow), < 0 in front (stifle).
  function ik(A, F, l1, l2, bend) {
    let d = sub(F, A), D = len(d);
    const max = (l1 + l2) * 0.999;
    if (D > max) { F = add(A, mul(d, max / D)); d = sub(F, A); D = max; }
    const u = mul(d, 1 / D), a = (l1 * l1 - l2 * l2 + D * D) / (2 * D), h = Math.sqrt(Math.max(0, l1 * l1 - a * a));
    const perp = norm(cross(u, [0, 0, 1]));
    return add(add(A, mul(u, a)), mul(perp, h * bend));
  }

  function quad(o) {
    const G = GAITS[o.gait || "walk"], seg = LEGTYPE[o.legs || "hoof"];
    const L = o.L, Hw = o.Hw, Hh = o.Hh ?? Hw * 0.97, stride = o.stride ?? L * 0.8, lift = o.lift ?? Hw * 0.12;
    const cR = o.chest, bR = o.barrel ?? cR, rR = o.rump ?? bR, sh = o.sh ?? 0.8;
    const base = o.pat || COAT, pat = (u) => base(u) * (u[1] < -0.35 ? 1.28 : 1); // countershading: paler belly
    return (t) => {
      const ph = (t / o.T) % 1, w = TAU * ph, parts = [];
      const galloping = G.bob === 1;
      const bob = galloping ? Hw * 0.045 * Math.sin(w + 0.8) : -Hw * (o.bobA ?? 0.012) * Math.cos(2 * w);
      const pitch = galloping ? 0.09 * Math.sin(w + 2.2) : 0.012 * Math.sin(w);
      const flex = (o.flex ?? (galloping ? 0.06 : 0)) * L * Math.cos(w);
      const roll = galloping ? 0 : 0.025 * Math.sin(w);
      const sx = L / 2 + flex * 0.5, hx = -L / 2 - flex * 0.5;
      const sy = Hw * 0.9 + bob + pitch * L * 0.5, hy = Hh * 0.9 + bob - pitch * L * 0.5;
      const S0 = [sx, sy, 0], H0 = [hx, hy, 0], spine = norm(sub(S0, H0));
      const up = norm(cross([0, 0, 1], spine));
      // Torso: chest, barrel and rump volumes along the spine; overlaps are culled into one surface.
      parts.push(E(add(S0, add(mul(spine, -cR[0] * 0.25), mul(up, cR[1] * 0.1))), spine, cR, sh, { pat }));
      // Barrel spans withers to hips with its top on the back line, so the belly tucks up and the back stays continuous.
      const bTop = Math.max(cR[1], rR[1]) * 0.96;
      parts.push(E(add(mix(S0, H0, 0.5), mul(up, bTop - bR[1] + (o.sag ?? 0))), spine, [Math.max(bR[0], L * 0.5), bR[1], bR[2]], sh, { pat }));
      parts.push(E(add(mix(S0, H0, 0.5), mul(up, bTop - Math.min(cR[1], rR[1]) * 0.55)), spine, [L * 0.55, Math.min(cR[1], rR[1]) * 0.55, Math.min(cR[2], rR[2]) * 0.9], sh, { pat }));
      parts.push(E(add(H0, add(mul(spine, rR[0] * 0.25), mul(up, rR[1] * 0.12))), spine, rR, sh, { pat }));
      // Legs: [LH, LF, RH, RF]
      [[false, 1], [true, 1], [false, -1], [true, -1]].forEach(([front, side], i) => {
        const J0 = add(front ? S0 : H0, [front ? -0.02 * L : 0.03 * L, -(front ? cR[1] : rR[1]) * 0.35, side * (front ? cR[2] : rR[2]) * 0.62]);
        const legLen = J0[1] * (o.reach ?? 1.02), l1 = legLen * seg[0], l2 = legLen * seg[1], l3 = legLen * seg[2];
        const p = (ph - G.off[i] + 2) % 1, stance = p < G.duty;
        const s = stance ? p / G.duty : (p - G.duty) / (1 - G.duty), e = s * s * (3 - 2 * s);
        const baseX = (front ? sx : hx) + (front ? 0.02 : 0.06) * L;
        const fx = stance ? baseX + stride * (0.5 - s) : baseX + stride * (-0.5 + e);
        const fy = stance ? 0 : lift * Math.sin(Math.PI * s) * (front ? 1 : 0.8);
        const F = [fx, fy + l3 * 0.08, side * (front ? cR[2] : rR[2]) * 0.55];
        const fold = stance ? 0 : Math.sin(Math.PI * Math.min(1, s * 1.2));
        const ca = front ? 0.06 + (o.flexF ?? 1.5) * fold : -(0.32 + 0.55 * fold);
        const C = add(F, [Math.sin(ca) * l3, Math.cos(ca) * l3, 0]);
        const K = ik(J0, C, l1, l2, front ? 1 : -1);
        const lr = o.legR, ls = o.legSh ?? sh * 0.9;
        parts.push(E(mix(J0, K, 0.42), sub(K, J0), [l1 * 0.55, lr * (front ? 1.9 : 2.4), lr * (front ? 1.5 : 1.8)], sh, { pat })); // shoulder / thigh muscle
        parts.push(T(J0, K, lr * 1.3, lr * 1.05, ls, { pat }), T(K, C, lr * 1.05, lr * 0.8, ls, { pat }), T(C, F, lr * 0.8, lr * 0.72, ls));
        const footLen = o.legs === "plant" ? lr * 2.6 : lr * 1.2;
        parts.push(E(add(F, [footLen * 0.35, -lr * 0.05, 0]), [1, 0, 0], [footLen, lr * 0.62, lr * 1.0], o.footSh ?? 0.5));
      });
      // Neck and head: the head is stabilized (held level) while the body bobs, and nods with the forelimbs.
      const nb = add(S0, add(mul(spine, cR[0] * 0.55), mul(up, cR[1] * 0.45)));
      const nod = galloping ? 0.05 * Math.sin(w + 1) : (o.nod ?? 0.025) * Math.cos(2 * w);
      const want = [nb[0] + Math.cos(o.neckA) * o.neck, Hw * 0.9 + Math.sin(o.neckA) * o.neck + nod * Hw + cR[1] * 0.45, 0];
      const ne = add(nb, mul(norm(sub(want, nb)), o.neck));
      const nr = o.neckR ?? cR[1] * 0.55;
      parts.push(T(nb, ne, nr, nr * 0.72, sh, { pat }));
      if (o.mane) parts.push(T(add(nb, mul(up, nr * 0.8)), add(ne, [-0.02, nr * 0.75, 0]), nr * 0.35, nr * 0.25, o.maneSh ?? sh * 0.6));
      const hd = fw(o.headA + nod * 0.6), hl = o.headL, hr = o.headR;
      const hc = add(ne, mul(hd, hl * 0.3));
      parts.push(E(hc, hd, [hl * 0.5, hr, hr * 0.85], o.headSh ?? sh * 1.02, { pat: base }));
      if (o.snout) parts.push(E(add(hc, mul(hd, hl * 0.45)), fw(o.headA - 0.12), [o.snout[0], o.snout[1], o.snout[1] * 0.85], o.headSh ?? sh * 1.02));
      if (o.jaw) parts.push(E(add(hc, add(mul(hd, hl * 0.2), [0, -hr * 0.55, 0])), hd, [hl * 0.38, hr * 0.35, hr * 0.7], sh));
      eyes(parts, add(hc, add(mul(hd, hl * 0.12), [0, hr * 0.4, 0])), hd, 1, hr * 0.14, hr * 0.78);
      if (o.ears) {
        const [el, ew, ea] = o.ears;
        for (const s of [1, -1]) {
          const eb = add(hc, add(mul(hd, -hl * 0.2), [0, hr * 0.72, s * hr * 0.48]));
          const twitch = 0.12 * Math.max(0, Math.sin(TAU * t / 2.7 + s * 2)) ** 8;
          parts.push(T(eb, add(eb, [-Math.sin(ea) * el * 0.4, Math.cos(ea + twitch) * el, s * el * (o.earOut ?? 0.3)]), ew, ew * 0.18, sh * 0.95));
        }
      }
      // Tail: a lagging chain (follow-through), swinging against the hips.
      if (o.tail) {
        const [tl, tr, tu] = o.tail;
        let p0 = add(H0, add(mul(spine, -rR[0] * 0.95), mul(up, rR[1] * 0.35))), ang = Math.PI + tu;
        for (let k = 0; k < 4; k++) {
          const a = ang + (o.tailSw ?? 0.18) * Math.sin(w * (galloping ? 1 : 1) - k * 0.7) + (o.tailDroop ?? 0.06) * k;
          const p1 = add(p0, mul([Math.cos(a), Math.sin(a), 0.1 * Math.sin(w - k * 0.9)], tl / 4));
          parts.push(T(p0, p1, tr * (1 - k * 0.2), tr * (0.8 - k * 0.2) + 0.004, sh * 0.9, { pat: o.tailPat }));
          p0 = p1; ang = a + (o.tailCurl ?? 0);
        }
        if (o.tuft) parts.push(E(p0, [1, 0, 0], [o.tuft * 1.5, o.tuft, o.tuft], sh * 0.6));
      }
      o.extra?.(parts, { S0, H0, spine, up, hc, hd, hl, hr, ph, w, t, ne, nb, L, Hw, cR, bR, sh });
      if (roll) rotate(parts, "x", roll, [0, Hw * 0.5, 0]);
      return parts;
    };
  }

  // ---------------- hoppers ----------------
  function hopper(o) {
    return (t) => {
      const ph = (TAU * t) / o.T, parts = [], sh = o.sh ?? 0.8;
      const cy = (t / o.T) % 1;
      let air = 0, e = 0, squat = 0;
      if (cy < 0.2) squat = Math.sin((Math.PI * cy) / 0.2) * 0.6;                                   // anticipation crouch
      else if (cy < 0.32) { e = (cy - 0.2) / 0.12; air = 0.1 * e; }                                  // push-off
      else if (cy < 0.72) { const f = (cy - 0.32) / 0.4; air = Math.sin(Math.PI * f); e = 1 - 0.5 * f; } // flight
      else { const f = (cy - 0.72) / 0.28; squat = Math.sin(Math.PI * f) * 0.8; e = 0.5 * (1 - f); }     // landing absorbs
      const c = [0, o.H * (1 - 0.35 * squat) + o.jump * air, 0];
      const tilt = o.tilt + (o.tiltAir ?? 0) * e;
      const d = fw(tilt), up = fw(tilt + Math.PI / 2);
      parts.push(E(c, d, o.body, sh, { pat: o.pat || COAT }));
      for (const s of [1, -1]) {
        const hip = add(add(c, mul(d, -o.body[0] * 0.45)), [0, -o.body[1] * 0.3, s * o.body[2] * 0.65]);
        parts.push(E(hip, fw(lerp(1.0, -0.6, e)), [o.thigh[0], o.thigh[1], o.thigh[1] * 0.8], sh));
        const knee = add(hip, mul(dn(lerp(1.1, -1.25, e)), o.leg[0]));
        const heel = add(knee, mul(dn(lerp(-1.0, -1.7, e)), o.leg[1]));
        const toe = add(heel, mul(dn(lerp(Math.PI / 2 + 0.05, -1.9, e)), o.leg[2]));
        parts.push(T(knee, heel, o.legR, o.legR * 0.8, sh * 0.9), T(heel, toe, o.legR * 0.8, o.legR * 0.5, sh * 0.85));
        const sh1 = add(add(c, mul(d, o.body[0] * 0.55)), [0, -o.body[1] * 0.4, s * o.body[2] * 0.5]);
        const paw = add(sh1, mul(dn(lerp(0.25, o.armAir ?? 1.1, e)), o.arm));
        parts.push(T(sh1, paw, o.legR * 0.75, o.legR * 0.5, sh * 0.9));
      }
      const hc = add(c, add(mul(d, o.body[0] * o.headAt[0]), mul(up, o.body[1] * o.headAt[1])));
      const hd = fw(o.headA ?? 0);
      parts.push(E(hc, hd, o.head, o.headSh ?? sh * 1.05));
      if (o.snout) parts.push(E(add(hc, mul(hd, o.head[0] * 0.75)), hd, o.snout, sh * 1.05));
      eyes(parts, add(hc, add(mul(hd, o.head[0] * 0.3), [0, o.head[1] * (o.eyeUp ?? 0.35), 0])), hd, 1, o.eyeR ?? o.head[1] * 0.18, o.head[2] * (o.eyeOut ?? 0.8));
      if (o.ears) for (const s of [1, -1]) {
        const eb = add(hc, [-o.head[0] * 0.3, o.head[1] * 0.8, s * o.head[2] * 0.4]);
        parts.push(E(add(eb, mul(fw(1.9 - 0.3 * e + 0.08 * Math.sin(ph * 2 + s)), o.ears[0] / 2)), fw(1.9 - 0.3 * e), [o.ears[0] / 2, o.ears[1], o.ears[1] * 0.4], sh * 0.95));
      }
      if (o.tail) {
        const tb = add(c, mul(d, -o.body[0] * 0.95));
        if (o.tail[0] < 0.1) parts.push(E(tb, [1, 0, 0], [o.tail[1], o.tail[1], o.tail[1]], 1.2));
        else {
          const ta = Math.PI + (o.tailA ?? 0.5) - 0.3 * e;
          const mid = add(tb, mul(fw(ta), o.tail[0] * 0.5)), end = add(mid, mul(fw(ta + 0.25), o.tail[0] * 0.5));
          parts.push(T(tb, mid, o.tail[1], o.tail[1] * 0.7, sh * 0.9), T(mid, end, o.tail[1] * 0.7, o.tail[1] * 0.25, sh * 0.9));
        }
      }
      return parts;
    };
  }

  // ---------------- birds ----------------
  function bird(o) {
    return (t) => {
      const ph = (TAU * t) / o.T, parts = [], sh = o.sh ?? 0.8, [bl, by, bz] = o.body;
      const bob = o.mode === "fly" ? -0.04 * Math.sin(ph) : 0;
      const c = [0, bob, 0], d = fw(o.bodyA ?? 0.05), up = fw((o.bodyA ?? 0.05) + Math.PI / 2);
      parts.push(E(c, d, o.body, sh, { pat: o.bodyPat || COAT }));
      let turn = 0;
      if (o.headTurn) {
        // Owls hold the head still, then snap it to a new bearing.
        const keys = [0, -1.15, -1.15, 0.25, 1.0, 1.0, 0.1], hold = 0.85, k = Math.floor(t / hold), f = (t / hold) % 1;
        const from = keys[k % keys.length], to = keys[(k + 1) % keys.length], m = f < 0.78 ? 0 : (f - 0.78) / 0.22;
        turn = from + (to - from) * m * m * (3 - 2 * m);
      }
      const blink = o.blink && t % 3.3 < 0.13 ? 0.05 : 1;
      const hc = add(c, add(mul(d, bl * (o.headAt ?? 0.95)), mul(up, by * (o.neckUp ?? 0.6))));
      const hd = norm([Math.cos(turn) * Math.cos(o.headA ?? 0), Math.sin(o.headA ?? 0), Math.sin(turn)]);
      parts.push(T(add(c, mul(d, bl * 0.55)), hc, by * 0.55, o.head * 0.8, sh));
      parts.push(E(hc, hd, [o.head * 1.1, o.head, o.head * 0.95], o.headSh ?? sh * 1.05));
      if (o.disc) parts.push(E(add(hc, mul(hd, o.head * 0.55)), hd, [o.head * 0.25, o.head * 0.95, o.head], 1.05));
      if (o.beak) parts.push(T(add(hc, mul(hd, o.head * 0.85)), add(add(hc, mul(hd, o.head * 0.85 + o.beak[0])), [0, -o.beak[2] || 0, 0]), o.beak[1], 0.003, o.beakSh ?? 1.1));
      const side = norm(cross(hd, [0, 1, 0]));
      for (const s of [1, -1]) {
        const ec = add(hc, add(mul(hd, o.head * (o.disc ? 0.75 : 0.45)), add([0, o.head * 0.25, 0], mul(side, s * o.head * (o.disc ? 0.42 : 0.78)))));
        parts.push(E(ec, hd, [o.head * 0.2, o.head * (o.disc ? 0.26 : 0.17), o.head * (o.disc ? 0.26 : 0.17)], 1.9, { w: 6, dim: blink }));
      }
      if (o.tufts) for (const s of [1, -1]) {
        const tb = add(hc, add([0, o.head * 0.8, 0], mul(side, s * o.head * 0.55)));
        parts.push(T(tb, add(tb, [-o.head * 0.2, o.head * 0.55, s * o.head * 0.2]), o.head * 0.14, 0.003, sh));
      }
      if (o.ears) for (const s of [1, -1]) {
        const tb = add(hc, add([0, o.head * 0.7, 0], mul(side, s * o.head * 0.55)));
        parts.push(T(tb, add(tb, [-o.head * 0.3, o.head * 1.3, s * o.head * 0.5]), o.head * 0.35, 0.004, sh));
      }
      const [span, chord] = o.wing;
      let beat = (t / o.T) % 1, gliding = false;
      if (o.glide) { const k = t % (o.T * (o.glide + 2)); gliding = k > o.T * 2; beat = (k / o.T) % 1; }
      const down = 0.58, ez = (x) => x * x * (3 - 2 * x); // the powered downstroke takes longer than the recovery
      const stroke = beat < down ? 1 - 2 * ez(beat / down) : -1 + 2 * ez((beat - down) / (1 - down));
      const wrist = gliding || beat < down ? 0 : Math.sin((Math.PI * (beat - down)) / (1 - down));
      const flap = o.fold ? 0.12 * Math.sin(ph) : gliding ? (o.bias ?? 0.1) + 0.06 : (o.amp ?? 0.6) * stroke + (o.bias ?? 0.1);
      for (const s of [1, -1]) {
        const sd = add(c, add(mul(d, bl * (o.wingAt ?? 0.15)), add(mul(up, by * 0.55), [0, 0, s * bz * 0.7])));
        if (o.fold) {
          const back = add(sd, add(mul(d, -span), [0, -by * 0.3 + flap * 0.1, s * bz * 0.35]));
          parts.push(Q(add(sd, mul(d, chord * 0.3)), back, add(back, [0, -chord * 0.8, 0]), add(sd, [0, -chord * 0.9, s * 0.01]), o.wingSh ?? sh * 0.9));
          continue;
        }
        const a2 = flap * (o.bend ?? 1.35) - wrist * 0.55, ed = span * 0.42, hand = (span - ed) * (1 - 0.45 * wrist);
        const el = add(sd, [0, Math.sin(flap) * ed, s * Math.cos(flap) * ed]);
        const fig = o.fig8 ? chord * 0.6 * Math.sin(TAU * beat * 2) : 0;
        const tip = add(el, [-chord * ((o.sweep ?? 0.35) + 0.8 * wrist) + fig, Math.sin(a2) * hand, s * Math.cos(a2) * hand]);
        const ws = o.wingSh ?? sh * 0.95;
        parts.push(Q(add(sd, [chord * 0.45, 0, 0]), add(el, [chord * 0.4, 0, 0]), add(el, [-chord * 0.6, 0, 0]), add(sd, [-chord * 0.55, 0, 0]), ws));
        parts.push(Q(add(el, [chord * 0.4, 0, 0]), add(tip, [chord * 0.12, 0, 0]), add(tip, [-chord * (o.tipChord ?? 0.2), 0, 0]), add(el, [-chord * 0.6, 0, 0]), ws, { pat: o.wingPat }));
        if (o.primaries) {
          // Slotted primary feathers ("fingers") fanning from the wingtip, as eagles and crows show in flight.
          const out = norm(sub(tip, el)), n = o.primaries;
          for (let k = 0; k < n; k++) {
            const root = add(tip, [chord * (0.1 - 0.32 * (k / (n - 1))), 0, 0]);
            const end = add(root, add(mul(out, chord * (0.5 - 0.06 * k) * (1 - 0.5 * wrist)), [-chord * 0.12 * k, -Math.abs(stroke) * 0.02 * k, 0]));
            const wd = chord * 0.055;
            parts.push(Q(root, end, add(end, [-wd, 0, 0]), add(root, [-wd * 1.6, 0, 0]), ws * 0.95));
          }
        }
      }
      if (o.tail) {
        const tb = add(c, mul(d, -bl * 0.85)), tw = o.tail[1], tlen = o.tail[0], ta = Math.PI + (o.tailA ?? 0.05) + 0.05 * Math.sin(ph);
        const te = add(tb, mul(fw(ta), tlen));
        parts.push(Q(add(tb, [0, 0, tw * 0.25]), add(te, [0, 0, tw * 0.5]), add(te, [0, 0, -tw * 0.5]), add(tb, [0, 0, -tw * 0.25]), sh * 0.9));
      }
      if (o.legs) for (const s of [1, -1]) {
        const hip = add(c, add(mul(d, -bl * 0.2), [0, -by * 0.6, s * bz * 0.4]));
        const step = o.mode === "waddle" ? 0.25 * Math.sin(ph + (s > 0 ? 0 : Math.PI)) : 0;
        const foot = o.mode === "fly" ? add(hip, [-o.legs * 0.9, -o.legs * 0.3, 0]) : add(hip, mul(dn(step), o.legs));
        parts.push(T(hip, foot, by * 0.12, by * 0.08, o.legSh ?? 0.65));
        parts.push(E(add(foot, [by * 0.18, 0, 0]), [1, 0, 0], [by * 0.25, by * 0.05, by * 0.15], o.legSh ?? 0.65));
      }
      if (o.mode === "waddle") rotate(parts, "x", 0.12 * Math.sin(ph), [0, -by, 0]);
      if (o.mode === "fly" && !gliding) rotate(parts, "z", -0.05 * stroke, c);
      if (o.mode === "hover") rotate(parts, "z", 0.05 * Math.sin(ph * 0.1), c);
      return parts;
    };
  }

  // ---------------- swimmers ----------------
  function swimmer(o) {
    return (t) => {
      const ph = (TAU * t) / o.T, parts = [], n = o.n ?? 12, L = o.L, sh = o.sh ?? 0.8, pts = [];
      for (let i = 0; i <= n; i++) {
        const s = i / n, off = o.amp * (0.08 + s * s) * Math.sin(ph - o.k * s * TAU);
        pts.push([L * (0.5 - s), o.vertical ? off : 0, o.vertical ? 0 : off]);
      }
      for (let i = 0; i < n; i++) {
        parts.push(T(pts[i], pts[i + 1], o.prof(i / n) * L, o.prof((i + 1) / n) * L, sh, { pat: o.pat || BELLY(1.35) }));
      }
      const r0 = o.prof(0) * L;
      parts.push(E(add(pts[0], [r0 * 0.4, 0, 0]), sub(pts[0], pts[1]), [r0 * 1.3, r0, r0], sh * 1.05));
      const head = pts[0], hr = o.prof(0.06) * L;
      if (o.beak) parts.push(T(head, add(head, [o.beak[0], -o.beak[0] * 0.1, 0]), o.beak[1], o.beak[1] * 0.6, sh * 1.05));
      eyes(parts, add(head, [-L * (o.eyeAt ?? 0.06), hr * 0.3, 0]), [1, 0, 0], 1, hr * 0.22, hr * (o.fz ?? 0.8) * 0.9);
      const tp = pts[n], tdir = norm(sub(pts[n - 1], pts[n])), tback = mul(tdir, -1);
      const [fl, fh] = o.tailFin;
      if (o.vertical) {
        for (const s of [1, -1]) parts.push(Q(tp, add(tp, add(mul(tback, fl * 0.35), [0, -fl * 0.15, s * fh * 0.3])), add(tp, add(mul(tback, fl), [0, 0, s * fh])), add(tp, mul(tback, fl * 0.2)), sh * 0.9));
      } else {
        parts.push(Q(tp, add(tp, add(mul(tback, fl), [0, fh, 0])), add(tp, add(mul(tback, fl * 0.55), [0, 0, 0])), add(tp, add(mul(tback, fl * (o.lower ?? 1)), [0, -fh * (o.lower ?? 1), 0])), sh * 0.9, { pat: o.finPat }));
      }
      if (o.dorsal) {
        const i = Math.round(n * o.dorsal[0]), base = pts[i], r = o.prof(o.dorsal[0]) * L * (o.fy ?? 1);
        parts.push(Q(add(base, [L * 0.06, r * 0.8, 0]), add(base, [-L * o.dorsal[2], r + o.dorsal[1], 0]), add(base, [-L * (o.dorsal[2] + 0.02), r * 0.8, 0]), add(base, [-L * 0.1, r * 0.8, 0]), sh * 0.9, { pat: o.finPat }));
      }
      if (o.pecs) {
        const i = Math.round(n * 0.22), base = pts[i], r = o.prof(0.22) * L, [pl, pw] = o.pecs, fl2 = 0.35 * Math.sin(ph * 1.3);
        for (const s of [1, -1]) {
          const root = add(base, [0, -r * 0.4, s * r * 0.7]);
          const tip = add(root, [-pl * 0.4, -pl * (0.45 + fl2 * 0.5), s * pl * 0.8]);
          parts.push(Q(add(root, [pw * 0.5, 0, 0]), tip, add(tip, [-pw * 0.4, 0, 0]), add(root, [-pw * 0.5, 0, 0]), sh * 0.85));
        }
      }
      if (o.whiskers) for (const s of [1, -1]) parts.push(T(add(head, [-L * 0.03, -hr * 0.3, s * hr * 0.5]), add(head, [L * 0.02, -hr * 1.2, s * hr * 1.4]), 0.006, 0.002, 1));
      if (o.roll) rotate(parts, "x", o.roll * Math.sin(ph * 0.5));
      return parts;
    };
  }

  // ---------------- bespoke bodies ----------------
  function snake(t) {
    const ph = TAU * t / 1.6, parts = [], n = 22, pts = [];
    for (let i = 0; i <= n; i++) {
      const s = i / n, x = 0.95 - s * 1.9;
      pts.push([x, 0.05 + (i < 3 ? (3 - i) * 0.035 : 0), (0.05 + 0.2 * s) * Math.sin(ph - s * 9)]);
    }
    for (let i = 0; i < n; i++) {
      const s = (i + 0.5) / n, r = 0.055 * Math.sin(Math.PI * Math.min(1, 0.25 + s * 0.85)) + 0.01;
      parts.push(T(pts[i], pts[i + 1], r, r * 0.95, 0.8, { pat: SPOTS(9, 0.45) }));
    }
    const hd = norm(sub(pts[0], pts[1]));
    parts.push(E(add(pts[0], mul(hd, 0.03)), hd, [0.07, 0.038, 0.05], 0.85));
    eyes(parts, add(pts[0], add(mul(hd, 0.05), [0, 0.022, 0])), hd, 1, 0.011, 0.034);
    const flick = pos(Math.sin(ph * 3)) * 0.09;
    const tb = add(pts[0], mul(hd, 0.1));
    for (const s of [1, -1]) parts.push(T(tb, add(tb, add(mul(hd, flick + 0.005), [0, -0.01, s * flick * 0.25])), 0.004, 0.002, 1.3));
    return parts;
  }

  function turtle(t) {
    const ph = TAU * t / 2.4, parts = [];
    parts.push(E([0, 0.2, 0], [1, 0, 0], [0.42, 0.19, 0.34], 0.75, { pat: SPOTS(7, 0.5) }));
    parts.push(E([0, 0.1, 0], [1, 0, 0], [0.4, 0.05, 0.31], 0.95));
    const reach = 0.04 * Math.sin(ph * 0.5);
    const nb = [0.36, 0.15, 0], hc = [0.56 + reach, 0.2 + reach * 0.5, 0];
    parts.push(T(nb, hc, 0.06, 0.05, 0.85), E(hc, [1, -0.2, 0], [0.09, 0.055, 0.06], 0.9));
    eyes(parts, add(hc, [0.04, 0.02, 0]), [1, 0, 0], 1, 0.011, 0.045);
    [[0.26, 1], [0.26, -1], [-0.26, 1], [-0.26, -1]].forEach(([x, s], i) => {
      const p = ph + (i === 0 || i === 3 ? 0 : Math.PI), hip = [x, 0.13, s * 0.27];
      const foot = add(hip, [0.12 * Math.sin(p), -0.12 + 0.03 * pos(Math.cos(p)), s * 0.1]);
      parts.push(T(hip, foot, 0.055, 0.045, 0.8), E(foot, [1, 0, 0], [0.06, 0.02, 0.05], 0.7));
    });
    parts.push(T([-0.4, 0.15, 0], [-0.52, 0.1, 0.02 * Math.sin(ph)], 0.03, 0.005, 0.8));
    return parts;
  }

  function crocodile(t) {
    const ph = TAU * t / 1.8, parts = [], n = 7;
    parts.push(E([0.05, 0.16, 0.02 * Math.sin(ph)], [1, 0, 0], [0.42, 0.1, 0.17], 0.72, { pat: SPOTS(14, 0.55) }));
    const jaw = 0.12 * pos(Math.sin(ph * 0.5 - 1));
    parts.push(E([0.52, 0.17, 0], [1, 0, 0], [0.14, 0.07, 0.1], 0.78));
    parts.push(E([0.78, 0.17, 0], fw(jaw * 0.5), [0.2, 0.035, 0.06], 0.8), E([0.76, 0.12, 0], fw(-jaw), [0.19, 0.025, 0.055], 0.9));
    eyes(parts, [0.56, 0.235, 0], [1, 0, 0], 1, 0.018, 0.05);
    [[0.3, 1], [0.3, -1], [-0.25, 1], [-0.25, -1]].forEach(([x, s], i) => {
      const p = ph + (i === 0 || i === 3 ? 0 : Math.PI), hip = [x, 0.14, s * 0.14];
      const knee = [x + 0.08 * Math.sin(p), 0.1 + 0.03 * pos(Math.cos(p)), s * 0.3], foot = [x + 0.1 * Math.sin(p) + 0.04, 0.005, s * 0.34];
      parts.push(T(hip, knee, 0.04, 0.032, 0.72), T(knee, foot, 0.032, 0.025, 0.72));
    });
    let p0 = [-0.35, 0.16, 0];
    for (let i = 0; i < n; i++) {
      const s = (i + 1) / n, p1 = [-0.35 - s * 0.85, 0.16 - s * 0.1, 0.16 * s * Math.sin(ph - s * 4)];
      parts.push(T(p0, p1, 0.09 * (1 - s * 0.8) + 0.01, 0.09 * (1 - (s + 1 / n) * 0.8) + 0.008, 0.72, { pat: BANDS(4) }));
      p0 = p1;
    }
    return parts;
  }

  function seahorse(t) {
    const ph = TAU * t / 2, parts = [], bob = 0.05 * Math.sin(ph);
    const curve = [];
    for (let i = 0; i <= 18; i++) {
      const s = i / 18;
      const x = s < 0.5 ? 0.12 * Math.sin(s * TAU) : 0.1 * Math.cos((s - 0.5) * 11) - 0.05;
      const y = s < 0.6 ? 0.55 - s * 1.2 : -0.17 + 0.12 * Math.sin((s - 0.6) * 11);
      curve.push([x, y + bob, 0]);
    }
    for (let i = 0; i < 18; i++) {
      const s = i / 18, r = s < 0.1 ? 0.07 : 0.1 * (1 - s) + 0.012;
      parts.push(T(curve[i], curve[i + 1], r, r * 0.92, 0.82, { pat: BANDS(12) }));
    }
    const h = add(curve[0], [0.02, 0.06, 0]);
    parts.push(E(h, [1, 0.3, 0], [0.09, 0.06, 0.05], 0.85), T(add(h, [0.06, -0.01, 0]), add(h, [0.24, -0.06, 0]), 0.022, 0.016, 0.9));
    parts.push(T(add(h, [-0.02, 0.05, 0]), add(h, [-0.05, 0.12, 0]), 0.025, 0.005, 0.9));
    eyes(parts, add(h, [0.03, 0.02, 0]), [1, 0, 0], 1, 0.013, 0.045);
    const fb = curve[5], fl = 0.03 * Math.sin(ph * 6);
    parts.push(Q(add(fb, [-0.08, 0.06, 0]), add(fb, [-0.2, 0.05, fl]), add(fb, [-0.19, -0.08, -fl]), add(fb, [-0.08, -0.08, 0]), 0.95));
    return parts;
  }

  function octopus(t) {
    // Jet stroke: the mantle contracts fast and the arms stream behind, then it refills while the arms open like an umbrella.
    const cy = (t / 2.4) % 1, parts = [];
    const jet = cy < 0.28 ? Math.sin((Math.PI * cy) / 0.28) : 0, open = cy < 0.28 ? 1 - cy / 0.28 : (cy - 0.28) / 0.72;
    const c = [0, 0.35 + 0.1 * Math.sin(TAU * cy - 0.6), 0], m = 1 - 0.22 * jet;
    parts.push(E(add(c, [-0.12, 0.2, 0]), fw(2.1), [0.28 * m, 0.2 * m, 0.19 * m], 0.8, { pat: SPOTS(16, 0.6) }));
    parts.push(E(c, [1, 0, 0], [0.16, 0.14, 0.17], 0.85));
    eyes(parts, add(c, [0.1, 0.06, 0]), [1, 0, 0], 1, 0.03, 0.12);
    for (let k = 0; k < 8; k++) {
      const th = (k / 8) * TAU + 0.2, rad = 0.35 + 0.65 * open, dir = [Math.cos(th) * rad, 0, Math.sin(th) * rad];
      let p0 = add(c, [Math.cos(th) * 0.1, -0.1, Math.sin(th) * 0.1]), ang = -0.35 - 0.95 * (1 - open);
      for (let j = 0; j < 6; j++) {
        const a = ang - j * (0.1 + 0.1 * Math.sin(TAU * cy + k * 0.8 + j * 0.5)) + (j > 3 ? 0.25 * open : 0);
        const p1 = add(p0, add(mul(dir, Math.cos(a) * 0.1), [0, Math.sin(a) * 0.1, 0]));
        const r0 = 0.045 * (1 - j / 6.5) + 0.006;
        parts.push(T(p0, p1, r0, r0 * 0.82, 0.82, { pat: j > 1 ? BANDS(2) : undefined }));
        p0 = p1;
      }
    }
    return parts;
  }

  function jellyfish(t) {
    const cy = (t / 2.2) % 1, ph = TAU * cy, parts = [];
    const pulse = cy < 0.3 ? Math.sin((Math.PI / 2) * (cy / 0.3)) : 1 - (cy - 0.3) / 0.7; // quick squeeze, slow refill
    const c = [0, 0.45 + 0.07 * Math.sin(ph - 1.2), 0];
    parts.push(E(c, [0, 1, 0], [0.17 - 0.03 * pulse, 0.34 - 0.06 * pulse, 0.34 - 0.06 * pulse], 1.05, { pat: STRIPES(3) }));
    parts.push(E(add(c, [0, -0.05, 0]), [0, 1, 0], [0.06, 0.2, 0.2], 1.3));
    for (let k = 0; k < 12; k++) {
      const th = (k / 12) * TAU, rim = add(c, [Math.cos(th) * 0.3, -0.08, Math.sin(th) * 0.3]);
      let p0 = rim;
      for (let j = 0; j < 5; j++) {
        const p1 = add(p0, [0.03 * Math.sin(ph + j * 0.9 + k), -0.14, 0.03 * Math.cos(ph + j * 0.7 + k)]);
        parts.push(T(p0, p1, 0.006, 0.004, 1.1)); p0 = p1;
      }
    }
    for (let k = 0; k < 4; k++) {
      const th = (k / 4) * TAU + 0.4;
      let p0 = add(c, [Math.cos(th) * 0.05, -0.1, Math.sin(th) * 0.05]);
      for (let j = 0; j < 4; j++) {
        const p1 = add(p0, [0.05 * Math.sin(ph * 0.8 + j + k), -0.12, 0.05 * Math.cos(ph * 0.8 + j + k)]);
        parts.push(T(p0, p1, 0.03 - j * 0.005, 0.025 - j * 0.005, 1.15)); p0 = p1;
      }
    }
    return parts;
  }

  function crab(t) {
    const ph = TAU * t / 0.9, parts = [], sway = 0.05 * Math.sin(ph), c = [0, 0.22, sway];
    parts.push(E(c, [1, 0, 0], [0.2, 0.08, 0.3], 0.8, { pat: SPOTS(20, 0.7) }));
    for (const s of [1, -1]) {
      const st = add(c, [0.16, 0.06, s * 0.07]);
      parts.push(T(st, add(st, [0.03, 0.09, s * 0.02]), 0.012, 0.01, 0.8), E(add(st, [0.03, 0.1, s * 0.02]), [1, 0, 0], [0.022, 0.022, 0.022], 1.9, { w: 6 }));
      for (let k = 0; k < 4; k++) {
        const p = ph + k * 1.6 + (s > 0 ? 0 : Math.PI), x = 0.1 - k * 0.08;
        const hip = add(c, [x, -0.02, s * 0.25]), knee = add(hip, [0.02 * Math.sin(p), 0.1 + 0.05 * pos(Math.sin(p)), s * 0.18]);
        const foot = [x - 0.04, 0, c[2] + s * (0.6 + 0.05 * Math.cos(p))];
        parts.push(T(hip, knee, 0.022, 0.018, 0.78), T(knee, foot, 0.018, 0.006, 0.78));
      }
      const sh = add(c, [0.16, -0.02, s * 0.2]), elbow = add(sh, [0.12, 0.05, s * 0.14]), claw = add(elbow, [0.14, 0.03, s * 0.02]);
      parts.push(T(sh, elbow, 0.03, 0.035, 0.8), E(claw, [1, 0.1, 0], [0.1, 0.055, 0.045], 0.85));
      const open = 0.25 + 0.2 * Math.sin(ph * 2 + s);
      parts.push(T(add(claw, [0.06, 0.02, 0]), add(claw, [0.06 + 0.1 * Math.cos(open), 0.02 + 0.1 * Math.sin(open), 0]), 0.022, 0.006, 0.85));
    }
    return parts;
  }

  function spider(t) {
    const ph = TAU * t / 0.8, parts = [], c = [0, 0.26 + 0.01 * Math.sin(2 * ph), 0];
    parts.push(E(add(c, [0.12, 0, 0]), [1, 0, 0], [0.12, 0.075, 0.1], 0.75));
    parts.push(E(add(c, [-0.14, 0.04, 0]), fw(0.3), [0.19, 0.15, 0.16], 0.72, { pat: SPOTS(18, 0.5) }));
    for (let k = 0; k < 4; k++) for (const s of [1, -1]) parts.push(E(add(c, [0.22, 0.03 + (k % 2) * 0.02, s * (0.015 + (k >> 1) * 0.025)]), [1, 0, 0], [0.012, 0.012, 0.012], 1.9, { w: 4 }));
    for (let k = 0; k < 4; k++) for (const s of [1, -1]) {
      const p = ph + (k % 2 ? Math.PI : 0) + (s > 0 ? 0 : Math.PI), fx = 0.2 - k * 0.1;
      const hip = add(c, [fx * 0.5, 0, s * 0.07]), knee = add(hip, [fx * 0.7 + 0.04 * Math.sin(p), 0.2 + 0.05 * pos(Math.cos(p)), s * 0.25]);
      const ank = add(knee, [fx * 0.4 + 0.05 * Math.sin(p), -0.25, s * 0.2]), foot = [ank[0] + fx * 0.3, 0, ank[2] + s * 0.06];
      parts.push(T(hip, knee, 0.02, 0.016, 0.72), T(knee, ank, 0.016, 0.01, 0.72), T(ank, foot, 0.01, 0.004, 0.72));
    }
    return parts;
  }

  function bee(t) {
    const ph = TAU * t / 0.09, parts = [], bob = 0.04 * Math.sin(TAU * t / 1.4), c = [0, bob, 0];
    parts.push(E(add(c, [0.14, 0.02, 0]), [1, 0, 0], [0.07, 0.07, 0.075], 0.8));
    parts.push(E(c, [1, 0, 0], [0.1, 0.09, 0.09], 0.85, { pat: COAT }));
    parts.push(E(add(c, [-0.2, -0.04, 0]), fw(-0.3), [0.17, 0.11, 0.11], 0.9, { pat: BANDS(5) }));
    parts.push(T(add(c, [-0.35, -0.1, 0]), add(c, [-0.41, -0.13, 0]), 0.012, 0.001, 1.2));
    eyes(parts, add(c, [0.17, 0.04, 0]), [1, 0, 0], 1, 0.028, 0.05);
    for (const s of [1, -1]) {
      parts.push(T(add(c, [0.19, 0.07, s * 0.03]), add(c, [0.28, 0.16, s * 0.07]), 0.006, 0.006, 0.9));
      const a = 0.55 * Math.sin(ph) + 0.35, root = add(c, [0.02, 0.08, s * 0.05]);
      parts.push(Q(add(root, [0.05, 0, 0]), add(root, [0.02, Math.sin(a) * 0.3, s * Math.cos(a) * 0.3]), add(root, [-0.12, Math.sin(a) * 0.26, s * Math.cos(a) * 0.26]), add(root, [-0.05, 0, 0]), 1.25));
      for (let k = 0; k < 3; k++) {
        const hip = add(c, [0.05 - k * 0.06, -0.07, s * 0.05]);
        parts.push(T(hip, add(hip, [-0.03 - k * 0.02, -0.12, s * 0.08]), 0.01, 0.005, 0.7));
      }
    }
    return parts;
  }

  function butterfly(t) {
    const ph = TAU * t / 0.75, parts = [], bob = 0.06 * Math.sin(ph + 1), c = [0, bob, 0];
    parts.push(T(add(c, [0.18, 0, 0]), add(c, [-0.22, -0.03, 0]), 0.025, 0.012, 0.85));
    parts.push(E(add(c, [0.2, 0.01, 0]), [1, 0, 0], [0.035, 0.03, 0.03], 0.9));
    const a = 0.65 * Math.sin(ph) + 0.55, pat = SPOTS(9, 0.35);
    for (const s of [1, -1]) {
      parts.push(T(add(c, [0.22, 0.02, s * 0.01]), add(c, [0.38, 0.14, s * 0.1]), 0.004, 0.004, 1), E(add(c, [0.38, 0.14, s * 0.1]), [1, 0, 0], [0.012, 0.012, 0.012], 1.4));
      const at = (x, r) => add(c, [x, Math.sin(a) * r, s * Math.cos(a) * r]);
      parts.push(Q(add(c, [0.12, 0.01, 0]), at(0.34, 0.55), at(0.0, 0.6), add(c, [-0.02, 0.01, 0]), 1.05, { pat }));
      parts.push(Q(add(c, [0.0, 0.0, 0]), at(-0.06, 0.45), at(-0.3, 0.3), add(c, [-0.14, -0.01, 0]), 1.0, { pat }));
    }
    return rotate(parts, "z", 0.25, c);
  }

  function dragonfly(t) {
    const ph = TAU * t / 0.14, parts = [], drift = 0.04 * Math.sin(TAU * t / 2), c = [0, drift, 0];
    parts.push(E(c, [1, 0, 0], [0.09, 0.06, 0.06], 0.85));
    parts.push(E(add(c, [0.12, 0.01, 0]), [1, 0, 0], [0.045, 0.05, 0.06], 0.9));
    eyes(parts, add(c, [0.14, 0.03, 0]), [1, 0, 0], 1, 0.035, 0.035);
    let p0 = add(c, [-0.08, 0, 0]);
    for (let j = 0; j < 7; j++) { const p1 = add(p0, [-0.1, -0.004 * j, 0.004 * Math.sin(TAU * t + j)]); parts.push(T(p0, p1, 0.02, 0.016, 0.85, { pat: BANDS(1) })); p0 = p1; }
    for (const s of [1, -1]) for (const [x, off] of [[0.03, 0], [-0.05, 1.3]]) {
      const a = 0.35 * Math.sin(ph + off) + 0.1, root = add(c, [x, 0.05, s * 0.04]), r = 0.6;
      parts.push(Q(add(root, [0.03, 0, 0]), add(root, [0.0, Math.sin(a) * r, s * Math.cos(a) * r]), add(root, [-0.06, Math.sin(a) * r * 0.95, s * Math.cos(a) * r * 0.95]), add(root, [-0.03, 0, 0]), 1.2));
    }
    return parts;
  }

  function snail(t) {
    const ph = TAU * t / 3, parts = [];
    parts.push(E([0.05, 0.06, 0], [1, 0, 0], [0.42, 0.06, 0.11], 0.85, { pat: (u) => 0.9 + 0.12 * Math.sin(u[0] * 12 - ph * 3) }));
    parts.push(E([0.4, 0.12, 0], fw(0.5), [0.1, 0.07, 0.08], 0.88));
    for (const s of [1, -1]) {
      const b = [0.44, 0.17, s * 0.03], tip = add(b, [0.1 + 0.02 * Math.sin(ph + s), 0.2, s * 0.06]);
      parts.push(T(b, tip, 0.014, 0.01, 0.9), E(tip, [1, 0, 0], [0.022, 0.022, 0.022], 1.9, { w: 6 }));
    }
    const sc = [-0.05, 0.3, 0];
    for (let j = 0; j < 16; j++) {
      const th = j * 0.62, r = 0.22 * Math.exp(-0.11 * j), rr = 0.12 * Math.exp(-0.1 * j);
      parts.push(E(add(sc, [Math.cos(th) * r, Math.sin(th) * r, 0.01 * j]), [-Math.sin(th), Math.cos(th), 0], [rr * 0.9, rr, rr * 1.15], 0.8, { pat: BANDS(3) }));
    }
    return parts;
  }

  // ---------------- the zoo ----------------
  const S = {
    wolf: ["狼", 0.62, quad({ L: 0.72, Hw: 0.78, chest: [0.26, 0.2, 0.14], barrel: [0.24, 0.16, 0.14], rump: [0.2, 0.15, 0.13], legR: 0.03, legs: "paw", gait: "trot", T: 0.62, stride: 0.5, neck: 0.26, neckA: 0.55, headA: -0.15, headL: 0.3, headR: 0.1, snout: [0.13, 0.05], jaw: true, ears: [0.12, 0.035, 0.12], tail: [0.5, 0.055, 0.9], tailSw: 0.12 })],
    cat: ["貓", 1.0, quad({ L: 0.5, Hw: 0.42, chest: [0.16, 0.11, 0.09], barrel: [0.18, 0.1, 0.1], rump: [0.15, 0.11, 0.1], legR: 0.022, legs: "paw", T: 1.0, stride: 0.3, lift: 0.06, neck: 0.12, neckA: 0.5, headA: -0.05, headL: 0.2, headR: 0.08, snout: [0.05, 0.04], ears: [0.08, 0.035, 0.05], tail: [0.55, 0.024, -0.9], tailCurl: 0.25, tailSw: 0.25, pat: STRIPES(7) })],
    deer: ["鹿", 1.1, quad({ L: 0.7, Hw: 1.0, chest: [0.24, 0.18, 0.13], barrel: [0.24, 0.15, 0.13], rump: [0.2, 0.16, 0.13], legR: 0.022, T: 1.1, stride: 0.55, neck: 0.45, neckA: 1.0, neckR: 0.06, headA: -0.5, headL: 0.28, headR: 0.075, snout: [0.1, 0.04], ears: [0.13, 0.04, 0.9], earOut: 0.6, tail: [0.1, 0.04, -0.5], extra: (P, g) => {
      for (const s of [1, -1]) {
        const b = add(g.hc, [-0.02, g.hr * 0.9, s * 0.04]), m = add(b, [-0.05, 0.2, s * 0.08]), tip = add(m, [0.02, 0.18, s * 0.06]);
        P.push(T(b, m, 0.014, 0.011, 0.95), T(m, tip, 0.011, 0.004, 0.95), T(m, add(m, [0.1, 0.1, s * 0.02]), 0.009, 0.003, 0.95), T(b, add(b, [0.09, 0.08, s * 0.03]), 0.009, 0.003, 0.95));
      }
    } })],
    elephant: ["大象", 1.7, quad({ L: 1.0, Hw: 1.55, chest: [0.42, 0.5, 0.42], barrel: [0.5, 0.52, 0.45], rump: [0.4, 0.48, 0.42], legR: 0.1, legs: "column", gait: "amble", T: 1.7, stride: 0.7, lift: 0.1, bobA: 0.006, neck: 0.15, neckA: 0.3, neckR: 0.3, headA: -0.35, headL: 0.5, headR: 0.33, nod: 0.01, tail: [0.5, 0.025, 1.2], tuft: 0.03, extra: (P, g) => {
      let p0 = add(g.hc, mul(g.hd, g.hl * 0.45)), ang = -1.25;
      for (let k = 0; k < 6; k++) { const a = ang - 0.1 * k + 0.22 * Math.sin(g.w + k * 0.55); const p1 = add(p0, mul([Math.cos(a), Math.sin(a), 0.1 * Math.sin(g.w * 0.5 + k)], 0.14)); P.push(T(p0, p1, 0.085 - k * 0.011, 0.075 - k * 0.011, 0.8, { pat: BANDS(3) })); p0 = p1; }
      for (const s of [1, -1]) {
        const eb = add(g.hc, [-0.14, 0.12, s * 0.26]), fl = 0.3 + 0.25 * Math.sin(g.t * 2.2 + s);
        P.push(Q(eb, add(eb, [-0.3, 0.14, s * 0.1 * fl]), add(eb, [-0.34, -0.36, s * 0.26 * fl]), add(eb, [0, -0.4, s * 0.15 * fl]), 0.76));
        const tb = add(g.hc, [0.16, -0.18, s * 0.13]);
        P.push(T(tb, add(tb, [0.3, -0.06, s * 0.04]), 0.035, 0.012, 1.4));
      }
    } })],
    giraffe: ["長頸鹿", 1.5, quad({ L: 0.8, Hw: 1.55, Hh: 1.3, chest: [0.3, 0.26, 0.18], barrel: [0.3, 0.22, 0.18], rump: [0.24, 0.21, 0.17], legR: 0.03, gait: "pace", T: 1.5, stride: 0.9, neck: 1.25, neckA: 1.15, neckR: 0.08, headA: -0.35, headL: 0.32, headR: 0.075, snout: [0.09, 0.045], ears: [0.08, 0.03, 1.3], earOut: 0.8, tail: [0.5, 0.018, 1.2], tuft: 0.04, mane: true, maneSh: 0.5, pat: SPOTS(13, 0.35), extra: (P, g) => {
      for (const s of [1, -1]) { const b = add(g.hc, [-0.05, g.hr * 0.9, s * 0.03]); P.push(T(b, add(b, [-0.01, 0.1, 0]), 0.012, 0.01, 0.9), E(add(b, [-0.01, 0.1, 0]), [1, 0, 0], [0.018, 0.018, 0.018], 0.7)); }
    } })],
    bear: ["熊", 1.4, quad({ L: 0.75, Hw: 0.95, Hh: 0.9, chest: [0.35, 0.36, 0.28], barrel: [0.36, 0.34, 0.3], rump: [0.3, 0.34, 0.29], legR: 0.075, legs: "plant", T: 1.4, stride: 0.5, neck: 0.18, neckA: 0.3, neckR: 0.18, headA: -0.2, headL: 0.34, headR: 0.16, snout: [0.11, 0.075], ears: [0.07, 0.055, 0.1], tail: [0.08, 0.04, 0.5], sh: 0.68, extra: (P, g) => {
      P.push(E(add(g.S0, mul(g.up, g.cR[1] * 0.75)), g.spine, [0.22, 0.14, 0.2], 0.68));
    } })],
    lion: ["獅子", 1.2, quad({ L: 0.85, Hw: 0.95, chest: [0.3, 0.25, 0.19], barrel: [0.3, 0.2, 0.18], rump: [0.25, 0.21, 0.18], legR: 0.045, legs: "paw", T: 1.2, stride: 0.6, neck: 0.22, neckA: 0.45, headA: -0.15, headL: 0.34, headR: 0.14, snout: [0.11, 0.08], jaw: true, ears: [0.06, 0.04, 0.2], tail: [0.8, 0.025, 0.9], tuft: 0.06, extra: (P, g) => {
      P.push(E(add(g.hc, [-0.12, 0.0, 0]), fw(-0.25), [0.18, 0.3, 0.3], 0.6, { pat: (u) => 0.75 + 0.25 * Math.sin(u[1] * 30 + u[2] * 25) }));
    } })],
    zebra: ["斑馬", 0.72, quad({ L: 0.9, Hw: 1.25, chest: [0.3, 0.27, 0.19], barrel: [0.33, 0.25, 0.2], rump: [0.28, 0.26, 0.2], legR: 0.03, gait: "trot", T: 0.72, stride: 0.9, neck: 0.5, neckA: 0.95, neckR: 0.1, headA: -1.0, headL: 0.5, headR: 0.09, snout: [0.13, 0.07], ears: [0.13, 0.035, 0.3], tail: [0.5, 0.025, 1.0], tuft: 0.05, mane: true, maneSh: 0.35, pat: STRIPES(9) })],
    pig: ["豬", 0.6, quad({ L: 0.55, Hw: 0.5, chest: [0.26, 0.24, 0.21], barrel: [0.28, 0.26, 0.23], rump: [0.24, 0.25, 0.22], legR: 0.035, gait: "trot", T: 0.6, stride: 0.3, neck: 0.08, neckA: 0.1, neckR: 0.15, headA: -0.15, headL: 0.3, headR: 0.15, snout: [0.09, 0.08], ears: [0.1, 0.06, -0.6], earOut: 0.5, tail: [0.16, 0.014, 0.3], tailCurl: 1.4, sh: 0.92 })],
    cow: ["牛", 1.5, quad({ L: 1.0, Hw: 1.35, chest: [0.34, 0.35, 0.26], barrel: [0.4, 0.36, 0.3], rump: [0.32, 0.33, 0.28], legR: 0.045, T: 1.5, stride: 0.7, neck: 0.3, neckA: 0.35, neckR: 0.17, headA: -0.9, headL: 0.44, headR: 0.13, snout: [0.11, 0.1], ears: [0.12, 0.04, 1.6], earOut: 0.9, tail: [0.8, 0.02, 1.4], tuft: 0.06, pat: SPOTS(7, 0.35), extra: (P, g) => {
      for (const s of [1, -1]) { const b = add(g.hc, [-0.08, g.hr * 0.8, s * 0.08]); P.push(T(b, add(b, [0.03, 0.12, s * 0.14]), 0.02, 0.004, 1.2)); }
    } })],
    sheep: ["綿羊", 1.1, quad({ L: 0.6, Hw: 0.7, chest: [0.28, 0.28, 0.24], barrel: [0.3, 0.3, 0.26], rump: [0.26, 0.28, 0.24], legR: 0.025, T: 1.1, stride: 0.4, neck: 0.14, neckA: 0.5, headA: -0.7, headL: 0.28, headR: 0.09, ears: [0.08, 0.03, 1.6], earOut: 1, tail: [0.1, 0.05, 0.8], legSh: 0.5, headSh: 0.55, sh: 1.05, extra: (P, g) => {
      const c = mix(g.S0, g.H0, 0.5);
      for (let k = 0; k < 16; k++) { const a = (k / 16) * TAU, b = k * 2.3; P.push(E(add(c, [Math.cos(a) * 0.36, Math.sin(b) * 0.14 + 0.06, Math.sin(a) * 0.2]), [1, 0, 0], [0.12, 0.1, 0.1], 1.05)); }
    } })],
    camel: ["駱駝", 1.5, quad({ L: 0.9, Hw: 1.8, Hh: 1.7, chest: [0.3, 0.28, 0.2], barrel: [0.34, 0.26, 0.22], rump: [0.28, 0.26, 0.2], legR: 0.035, gait: "pace", T: 1.5, stride: 1.1, neck: 0.75, neckA: 0.25, neckR: 0.09, headA: -0.1, headL: 0.38, headR: 0.1, snout: [0.1, 0.075], ears: [0.06, 0.03, 0.3], tail: [0.45, 0.02, 1.2], tuft: 0.03, extra: (P, g) => {
      P.push(E(add(mix(g.S0, g.H0, 0.45), mul(g.up, g.bR[1] * 1.0)), g.spine, [0.26, 0.24, 0.16], 0.82));
    } })],
    rhino: ["犀牛", 1.0, quad({ L: 0.95, Hw: 1.4, chest: [0.38, 0.42, 0.34], barrel: [0.44, 0.44, 0.38], rump: [0.36, 0.42, 0.36], legR: 0.08, legs: "column", gait: "trot", T: 1.0, stride: 0.6, neck: 0.18, neckA: 0.1, neckR: 0.25, headA: -0.55, headL: 0.55, headR: 0.2, ears: [0.12, 0.05, 0.2], tail: [0.3, 0.025, 1.2], sh: 0.7, extra: (P, g) => {
      const n = add(g.hc, mul(g.hd, g.hl * 0.42)), m = add(g.hc, mul(g.hd, g.hl * 0.12));
      P.push(T(add(n, [0, 0.1, 0]), add(n, [0.05, 0.38, 0]), 0.065, 0.004, 1.1), T(add(m, [0, 0.15, 0]), add(m, [0.01, 0.3, 0]), 0.045, 0.004, 1.1));
    } })],
    hippo: ["河馬", 1.5, quad({ L: 1.05, Hw: 0.95, chest: [0.45, 0.45, 0.4], barrel: [0.5, 0.47, 0.43], rump: [0.42, 0.45, 0.4], legR: 0.09, legs: "column", T: 1.5, stride: 0.45, lift: 0.07, neck: 0.12, neckA: 0, neckR: 0.3, headA: -0.1, headL: 0.6, headR: 0.24, snout: [0.22, 0.2], jaw: true, ears: [0.05, 0.04, 0.2], tail: [0.18, 0.03, 1], sh: 0.72 })],
    cheetah: ["獵豹", 0.42, quad({ L: 0.75, Hw: 0.82, chest: [0.24, 0.2, 0.13], barrel: [0.22, 0.14, 0.12], rump: [0.18, 0.15, 0.12], legR: 0.026, legs: "paw", gait: "rotary", T: 0.42, stride: 1.0, lift: 0.18, flex: 0.2, neck: 0.24, neckA: 0.35, headA: -0.1, headL: 0.22, headR: 0.085, snout: [0.06, 0.05], ears: [0.05, 0.035, 0.2], tail: [0.75, 0.03, 0.6], tailSw: 0.35, pat: SPOTS(22, 0.35) })],
    rabbit: ["兔子", 0.7, hopper({ T: 0.7, H: 0.2, jump: 0.2, tilt: 0.35, tiltAir: -0.35, body: [0.26, 0.19, 0.16], thigh: [0.12, 0.09], leg: [0.1, 0.1, 0.14], legR: 0.028, arm: 0.14, head: [0.1, 0.09, 0.085], headAt: [1.0, 0.6], headA: -0.3, ears: [0.28, 0.035], tail: [0, 0.055] })],
    kangaroo: ["袋鼠", 0.9, hopper({ T: 0.9, H: 0.45, jump: 0.28, tilt: 1.05, tiltAir: -0.55, body: [0.35, 0.2, 0.17], thigh: [0.18, 0.12], leg: [0.2, 0.2, 0.26], legR: 0.035, arm: 0.16, armAir: 0.5, head: [0.12, 0.08, 0.07], headAt: [1.05, 0.3], headA: -0.1, snout: [0.06, 0.04, 0.04], ears: [0.16, 0.035], tail: [0.8, 0.07], tailA: -0.5 })],
    frog: ["青蛙", 1, hopper({ T: 1, H: 0.12, jump: 0.24, tilt: 0.25, tiltAir: -0.2, body: [0.22, 0.12, 0.17], thigh: [0.12, 0.07], leg: [0.16, 0.16, 0.18], legR: 0.03, arm: 0.12, head: [0.12, 0.07, 0.15], headAt: [0.85, 0.2], eyeR: 0.04, eyeUp: 1.0, eyeOut: 0.6, pat: SPOTS(20, 0.55), sh: 0.85 })],
    turtle: ["烏龜", 2.4, turtle],
    crocodile: ["鱷魚", 1.8, crocodile],
    snake: ["蛇", 1.6, snake],
    eagle: ["老鷹", 1.4, bird({ T: 1.4, mode: "fly", body: [0.3, 0.1, 0.1], head: 0.075, headSh: 1.25, beak: [0.07, 0.022, 0.03], wing: [1.1, 0.3], amp: 0.42, bias: 0.12, glide: 3, primaries: 5, tail: [0.24, 0.2], legs: 0.1 })],
    crow: ["烏鴉", 0.6, bird({ T: 0.6, mode: "fly", body: [0.24, 0.085, 0.085], head: 0.06, beak: [0.07, 0.016], wing: [0.7, 0.2], amp: 0.7, primaries: 4, tail: [0.18, 0.12], legs: 0.08, sh: 0.62 })],
    owl: ["貓頭鷹", 3, bird({ T: 3, mode: "perch", bodyA: 1.35, body: [0.3, 0.2, 0.18], head: 0.15, headAt: 1.0, neckUp: 0.05, headA: -0.1, headTurn: true, blink: true, disc: true, tufts: true, beak: [0.04, 0.02, 0.02], wing: [0.42, 0.3], fold: true, legs: 0.08, headAtY: 0, bodyPat: SPOTS(22, 0.7) })],
    penguin: ["企鵝", 0.9, bird({ T: 0.9, mode: "waddle", bodyA: 1.45, body: [0.36, 0.18, 0.17], head: 0.1, headAt: 1.05, neckUp: 0, headA: 0.1, beak: [0.09, 0.022, 0.02], wing: [0.26, 0.09], amp: 0.5, bias: -0.9, bend: 1, sweep: 0.1, legs: 0.05, legSh: 0.8, bodyPat: (u) => (u[1] < -0.1 ? 1.5 : 0.62) })],
    hummingbird: ["蜂鳥", 0.1, bird({ T: 0.1, mode: "hover", bodyA: 0.7, body: [0.16, 0.06, 0.055], head: 0.05, beak: [0.2, 0.008], wing: [0.36, 0.08], amp: 1.0, bias: 0.3, bend: 1, sweep: 0.05, fig8: true, tail: [0.1, 0.06], sh: 0.9 })],
    bat: ["蝙蝠", 0.45, bird({ T: 0.45, mode: "fly", body: [0.14, 0.07, 0.07], head: 0.06, headSh: 0.7, ears: true, wing: [0.6, 0.34], amp: 0.9, bias: 0.05, sweep: 0.22, tipChord: 0.3, legs: 0.08, sh: 0.55, wingSh: 0.6 })],
    shark: ["鯊魚", 1.3, swimmer({ T: 1.3, L: 1.7, amp: 0.1, k: 0.9, n: 12, prof: (s) => 0.1 * Math.pow(Math.sin(Math.PI * Math.min(1, s * 1.1 + 0.02)), 0.8) + 0.004, fz: 0.85, tailFin: [0.3, 0.32], lower: 0.6, dorsal: [0.35, 0.22, 0.12], pecs: [0.3, 0.12], sh: 0.72 })],
    whale: ["鯨", 3, swimmer({ T: 3, L: 2.2, amp: 0.12, k: 0.8, vertical: true, prof: (s) => 0.1 * Math.pow(Math.sin(Math.PI * Math.min(1, s * 1.05 + 0.08)), 0.7) + 0.006, fz: 0.95, tailFin: [0.25, 0.4], pecs: [0.55, 0.14], dorsal: [0.62, 0.05, 0.05], pat: STRIPES(18), sh: 0.75 })],
    dolphin: ["海豚", 1.1, swimmer({ T: 1.1, L: 1.3, amp: 0.1, k: 0.85, vertical: true, prof: (s) => 0.095 * Math.pow(Math.sin(Math.PI * Math.min(1, s * 1.05 + 0.1)), 0.9) + 0.006, fz: 0.85, beak: [0.12, 0.025], tailFin: [0.18, 0.24], dorsal: [0.42, 0.14, 0.08], pecs: [0.18, 0.07] })],
    koi: ["錦鯉", 1.2, swimmer({ T: 1.2, L: 0.8, amp: 0.12, k: 0.75, prof: (s) => 0.11 * Math.sin(Math.PI * Math.min(1, s * 1.1 + 0.08)) + 0.01, fz: 0.6, tailFin: [0.28, 0.2], dorsal: [0.4, 0.1, 0.2], pecs: [0.14, 0.08], whiskers: true, pat: SPOTS(10, 0.4), finPat: STRIPES(6), sh: 0.95 })],
    seahorse: ["海馬", 2, seahorse],
    octopus: ["章魚", 2.2, octopus],
    jellyfish: ["水母", 1.8, jellyfish],
    crab: ["螃蟹", 0.9, crab],
    spider: ["蜘蛛", 0.8, spider],
    bee: ["蜜蜂", 1.4, bee],
    butterfly: ["蝴蝶", 0.75, butterfly],
    dragonfly: ["蜻蜓", 2, dragonfly],
    snail: ["蝸牛", 3, snail],
  };

  // Particle allocation over parts, then per-frame placement.
  function areaOf(p) {
    if (p.k === 0) { const [a, b, c] = p.r, q = 1.6; return 4 * Math.PI * Math.pow((Math.pow(a * b, q) + Math.pow(a * c, q) + Math.pow(b * c, q)) / 3, 1 / q); }
    if (p.k === 1) return Math.PI * (p.r0 + p.r1) * len(sub(p.b, p.a)) + 1e-4;
    const [p0, p1, p2, p3] = p.p;
    return 0.5 * (len(cross(sub(p1, p0), sub(p3, p0))) + len(cross(sub(p1, p2), sub(p3, p2))));
  }

  const VIEW = {
    eagle: [0.8, 0.55], crow: [0.8, 0.55], bat: [0.8, 0.6], hummingbird: [0.5, 0.3], butterfly: [0.4, 0.95], bee: [0.6, 0.45],
    dragonfly: [0.5, 0.85], crab: [0.2, 0.5], spider: [0.3, 0.45], snake: [0.2, 0.95], koi: [0.2, 0.9], turtle: [0.3, 0.3],
    crocodile: [0.3, 0.4], shark: [0.25, 0.25], octopus: [0.4, 0.1],
  };

  function make(key, N) {
    const [, period, base] = S[key], view = VIEW[key];
    const build = view ? (t) => rotate(rotate(base(t), "y", view[0]), "x", view[1]) : base;
    const parts0 = build(0), M = parts0.length;
    const wts = parts0.map((p) => areaOf(p) * (p.w || 1)), tot = wts.reduce((a, b) => a + b, 0);
    const counts = wts.map((w) => Math.max(8, Math.round((N * w) / tot)));
    let over = counts.reduce((a, b) => a + b, 0) - N;
    while (over !== 0) { const i = counts.indexOf(Math.max(...counts)); counts[i] -= Math.sign(over); over -= Math.sign(over); }
    const pi = new Uint16Array(N), u0 = new Float32Array(N), u1 = new Float32Array(N), u2 = new Float32Array(N), shade = new Float32Array(N);
    let k = 0;
    for (let i = 0; i < M; i++) for (let j = 0; j < counts[i]; j++, k++) {
      const p = parts0[i];
      pi[k] = i;
      let u;
      if (p.k === 0) { let x = 0, y = 0, z = 0, l = 0; while (l < 1e-6) { x = Math.random() * 2 - 1; y = Math.random() * 2 - 1; z = Math.random() * 2 - 1; l = x * x + y * y + z * z; if (l > 1) l = 0; } l = Math.sqrt(l); u = [x / l, y / l, z / l]; }
      else if (p.k === 1) { const s = Math.random(), th = Math.random() * TAU; u = [s * 2 - 1, Math.cos(th), Math.sin(th)]; }
      else u = [Math.random() * 2 - 1, Math.random() * 2 - 1, (Math.random() - 0.5) * 0.02];
      u0[k] = u[0]; u1[k] = u[1]; u2[k] = u[2];
      shade[k] = Math.min(1.9, p.sh * (p.pat ? p.pat(u) : 1));
    }
    // Shuffle so particles fly in from everywhere when the orb re-forms.
    for (let i = N - 1; i > 0; i--) {
      const j = (Math.random() * (i + 1)) | 0;
      for (const arr of [pi, u0, u1, u2, shade]) { const t = arr[i]; arr[i] = arr[j]; arr[j] = t; }
    }

    function raw(t, P, Nn, Sh) {
      const parts = build(t);
      for (const p of parts) if (p.k === 1) { const B = basis(sub(p.b, p.a)); p.e1 = B[1]; p.e2 = B[2]; }
      for (let i = 0; i < N; i++) {
        const p = parts[pi[i]], a = u0[i], b = u1[i], c = u2[i], j = i * 3;
        let x, y, z, nx, ny, nz;
        if (p.k === 0) {
          const [X, Y, Z] = p.B, [rx, ry, rz] = p.r;
          x = p.c[0] + X[0] * a * rx + Y[0] * b * ry + Z[0] * c * rz;
          y = p.c[1] + X[1] * a * rx + Y[1] * b * ry + Z[1] * c * rz;
          z = p.c[2] + X[2] * a * rx + Y[2] * b * ry + Z[2] * c * rz;
          nx = X[0] * a / rx + Y[0] * b / ry + Z[0] * c / rz; ny = X[1] * a / rx + Y[1] * b / ry + Z[1] * c / rz; nz = X[2] * a / rx + Y[2] * b / ry + Z[2] * c / rz;
        } else if (p.k === 1) {
          const s = (a + 1) / 2, r = p.r0 + (p.r1 - p.r0) * s;
          nx = p.e1[0] * b + p.e2[0] * c; ny = p.e1[1] * b + p.e2[1] * c; nz = p.e1[2] * b + p.e2[2] * c;
          x = p.a[0] + (p.b[0] - p.a[0]) * s + nx * r; y = p.a[1] + (p.b[1] - p.a[1]) * s + ny * r; z = p.a[2] + (p.b[2] - p.a[2]) * s + nz * r;
        } else {
          const s = (a + 1) / 2, v = (b + 1) / 2, [p0, p1, p2, p3] = p.p;
          const w00 = (1 - s) * (1 - v), w10 = s * (1 - v), w11 = s * v, w01 = (1 - s) * v;
          x = p0[0] * w00 + p1[0] * w10 + p2[0] * w11 + p3[0] * w01;
          y = p0[1] * w00 + p1[1] * w10 + p2[1] * w11 + p3[1] * w01;
          z = p0[2] * w00 + p1[2] * w10 + p2[2] * w11 + p3[2] * w01;
          const n = cross(sub(p1, p0), sub(p3, p0));
          nx = n[0]; ny = n[1]; nz = n[2];
          const l = Math.hypot(nx, ny, nz) || 1; x += (nx / l) * c; y += (ny / l) * c; z += (nz / l) * c;
        }
        const l = Math.hypot(nx, ny, nz) || 1;
        P[j] = x; P[j + 1] = y; P[j + 2] = z; Nn[j] = nx / l; Nn[j + 1] = ny / l; Nn[j + 2] = nz / l;
      }
      if (!Sh) return;
      // Hide particles buried inside another solid part, so overlapping parts read as one surface.
      const occ = [];
      parts.forEach((p, i) => {
        if (p.k === 0 && Math.min(...p.r) > 0.025) occ.push({ i, k: 0, c: p.c, B: p.B, r: p.r.map((v) => v * 0.97) });
        else if (p.k === 1 && Math.max(p.r0, p.r1) > 0.025) {
          const ab = sub(p.b, p.a), L2 = ab[0] * ab[0] + ab[1] * ab[1] + ab[2] * ab[2] || 1;
          occ.push({ i, k: 1, a: p.a, ab, L2, r0: p.r0 * 0.95, r1: p.r1 * 0.95 });
        }
      });
      for (let i = 0; i < N; i++) {
        const j = i * 3, x = P[j], y = P[j + 1], z = P[j + 2], own = pi[i];
        let hidden = false;
        for (const o of occ) {
          if (o.i === own) continue;
          if (o.k === 0) {
            const dx = x - o.c[0], dy = y - o.c[1], dz = z - o.c[2], [X, Y, Z] = o.B;
            const a = (dx * X[0] + dy * X[1] + dz * X[2]) / o.r[0], b = (dx * Y[0] + dy * Y[1] + dz * Y[2]) / o.r[1], c = (dx * Z[0] + dy * Z[1] + dz * Z[2]) / o.r[2];
            if (a * a + b * b + c * c < 1) { hidden = true; break; }
          } else {
            const dx = x - o.a[0], dy = y - o.a[1], dz = z - o.a[2];
            const s = (dx * o.ab[0] + dy * o.ab[1] + dz * o.ab[2]) / o.L2;
            if (s <= 0 || s >= 1) continue;
            const ex = dx - o.ab[0] * s, ey = dy - o.ab[1] * s, ez = dz - o.ab[2] * s, r = o.r0 + (o.r1 - o.r0) * s;
            if (ex * ex + ey * ey + ez * ez < r * r) { hidden = true; break; }
          }
        }
        Sh[i] = hidden ? 0 : shade[i] * (parts[own].dim ?? 1);
      }
    }

    // Frame the whole motion loop.
    const tmp = new Float32Array(N * 3), tn = new Float32Array(N * 3), lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    for (let s = 0; s < 6; s++) {
      raw((period * s) / 6, tmp, tn);
      for (let i = 0; i < N; i++) for (let a = 0; a < 3; a++) { const v = tmp[i * 3 + a]; if (v < lo[a]) lo[a] = v; if (v > hi[a]) hi[a] = v; }
    }
    const ctr = lo.map((l, a) => (l + hi[a]) / 2), scale = 2.3 / Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]);
    function fill(t, P, Nn, Sh) {
      raw(t, P, Nn, Sh);
      for (let i = 0; i < N * 3; i += 3) { P[i] = (P[i] - ctr[0]) * scale; P[i + 1] = (P[i + 1] - ctr[1]) * scale; P[i + 2] = (P[i + 2] - ctr[2]) * scale; }
    }
    return { fill, shade, duration: period, speed: 1 };
  }

  const names = Object.fromEntries(Object.entries(S).map(([k, v]) => [k, v[0]]));
  return { has: (k) => k in S, make, names };
})();
