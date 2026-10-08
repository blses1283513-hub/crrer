/* DRAM Thickness Metro — extension engine (pure functions): GOF, thickness-range sensitivity,
   n–t correlation vs thickness, FFT thickness, wafer-curvature stress (Stoney), overlay linear model,
   CD-SEM linescan + edge detection, grating OCD (zeroth-order EMA, TE/TM) with LM fit. */
(function (root) {
  'use strict';
  const T = root.DMS.thick;
  const { C, add, sub, mul, div, csqrt, abs2 } = T;

  // ---------- GOF (vendor-style, 0..1) ----------
  // GOF = 1 - Σ(meas-model)² / Σ(meas-mean)², computed over Ψ and Δ separately and averaged.
  function gof(data, model) {
    let g = 0;
    for (const k of [0, 1]) {
      const y = data.map((d) => d[k]), m = model.map((d) => d[k]);
      const my = y.reduce((a, b) => a + b, 0) / y.length;
      const ssr = y.reduce((a, v, i) => a + (v - m[i]) ** 2, 0), sst = y.reduce((a, v) => a + (v - my) ** 2, 0);
      g += 1 - ssr / sst;
    }
    return g / 2;
  }
  const gofBand = (g) => (g >= 0.95 ? 'good' : g >= 0.8 ? 'marginal' : 'reject');

  // ---------- thickness range: SiO2 on Si ----------
  const WLR = []; for (let l = 400; l <= 900; l += 5) WLR.push(l);
  const rSpec = (d) => WLR.map((l) => T.reflectance(l, [{ n: T.MAT.SiO2(l), d }], T.MAT.Si(l), 0));
  const dSpec = (d) => WLR.map((l) => T.psiDelta(l, [{ n: T.MAT.SiO2(l), d }], T.MAT.Si(l), 70));
  // RMS signal change per 1 Å of thickness, relative to noise (R: 0.1 % abs; Δ: 0.02 °)
  function sensitivity(dnm) {
    const h = 0.1; // 1 Å
    const r0 = rSpec(dnm), r1 = rSpec(dnm + h), p0 = dSpec(dnm), p1 = dSpec(dnm + h);
    const rmsR = Math.sqrt(r0.reduce((a, v, i) => a + (r1[i] - v) ** 2, 0) / r0.length) / 0.001;
    const rmsD = Math.sqrt(p0.reduce((a, v, i) => { let dd = p1[i][1] - v[1]; if (dd > 180) dd -= 360; if (dd < -180) dd += 360; return a + dd * dd + ((p1[i][0] - v[0]) / 0.01 * 0.02) ** 2; }, 0) / p0.length) / 0.02;
    const fringes = 2 * 1.46 * dnm * (1 / 400 - 1 / 900);
    return { rmsR, rmsD, fringes };
  }
  // corr(d, n) of a single SiO2 film fitted with SE when both float (normal equations, unit noise)
  function corrDN(dnm) {
    const sig = [0.01, 0.02], h = [0.05, 5e-4];
    const f = (d, dn) => WLR.map((l) => T.psiDelta(l, [{ n: C(T.MAT.SiO2(l)[0] + dn), d }], T.MAT.Si(l), 70));
    const base = f(dnm, 0), jd = f(dnm + h[0], 0), jn = f(dnm, h[1]);
    const col = (m, hh) => m.flatMap((v, i) => { let dd = v[1] - base[i][1]; if (dd > 180) dd -= 360; if (dd < -180) dd += 360; return [(v[0] - base[i][0]) / hh / sig[0], dd / hh / sig[1]]; });
    const a = col(jd, h[0]), b = col(jn, h[1]);
    const aa = a.reduce((s, v) => s + v * v, 0), bb = b.reduce((s, v) => s + v * v, 0), ab = a.reduce((s, v, i) => s + v * b[i], 0);
    const det = aa * bb - ab * ab;
    const cov = [[bb / det, -ab / det], [-ab / det, aa / det]];
    return { corr: cov[0][1] / Math.sqrt(cov[0][0] * cov[1][1]), sdD: Math.sqrt(cov[0][0]), sdN: Math.sqrt(cov[1][1]) };
  }
  // same, for reflectometry only (normal incidence R, noise 0.1 %): needs >= ~1 fringe to separate n and d
  function corrDNrefl(dnm) {
    const h = [0.01, 1e-4];
    const f = (d, dn) => WLR.map((l) => T.reflectance(l, [{ n: C(T.MAT.SiO2(l)[0] + dn), d }], T.MAT.Si(l), 0));
    const b0 = f(dnm, 0), a = f(dnm + h[0], 0).map((v, i) => (v - b0[i]) / h[0] / 0.001), b = f(dnm, h[1]).map((v, i) => (v - b0[i]) / h[1] / 0.001);
    const aa = a.reduce((s, v) => s + v * v, 0), bb = b.reduce((s, v) => s + v * v, 0), ab = a.reduce((s, v, i) => s + v * b[i], 0);
    const det = aa * bb - ab * ab;
    return { corr: -ab / Math.sqrt(aa * bb), sdD: Math.sqrt(bb / det), sdDfixed: 1 / Math.sqrt(aa) };
  }
  // thickness from the fringe period: FFT of R(k), k = 1/λ (same math an FTIR / Michelson system uses for thick epi)
  function fftThickness(dnm, nAvg = 1.46) {
    const kmin = 1 / 900, kmax = 1 / 400, N = 512, ks = [], R = [];
    for (let i = 0; i < N; i++) { const k = kmin + ((kmax - kmin) * i) / (N - 1); ks.push(k); R.push(T.reflectance(1 / k, [{ n: T.MAT.SiO2(1 / k), d: dnm }], T.MAT.Si(1 / k), 0)); }
    const m = R.reduce((a, b) => a + b, 0) / N; const y = R.map((v, i) => (v - m) * (0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (N - 1))));
    const dk = (kmax - kmin) / (N - 1);
    let best = 0, bestD = 0; const spec = [];
    for (let D = 50; D <= 12000; D += 10) { // candidate optical path 2nD (nm)
      let re = 0, im = 0; for (let i = 0; i < N; i++) { const ph = 2 * Math.PI * D * ks[i]; re += y[i] * Math.cos(ph); im += y[i] * Math.sin(ph); }
      const p = re * re + im * im; spec.push([D / (2 * nAvg), p]); if (p > best) { best = p; bestD = D; }
    }
    return { d: bestD / (2 * nAvg), spec, resolution: 1 / (2 * nAvg * (kmax - kmin)) };
  }

  // ---------- stress (Stoney) ----------
  // σ = M_s t_s² /(6 t_f) · Δκ, M_s = E/(1-ν) biaxial (Si(001): 180.5 GPa). κ>0 when the film side is concave (tensile).
  const MS_SI = 180.5e9;
  function stoneyStress(dKappa, ts_um, tf_nm, Ms = MS_SI) { return (Ms * (ts_um * 1e-6) ** 2 / (6 * tf_nm * 1e-9)) * dKappa / 1e6; } // MPa
  function kappaFromStress(sMPa, ts_um, tf_nm, Ms = MS_SI) { return (sMPa * 1e6 * 6 * tf_nm * 1e-9) / (Ms * (ts_um * 1e-6) ** 2); } // 1/m
  // height scan across a 300 mm diameter: z(x) = κ x²/2 + incoming bow shape + tilt + noise (µm)
  function scan(kappa, extra, seed, noiseUm) {
    const R = T.rng(seed), pts = [];
    for (let x = -145; x <= 145.01; x += 5) { const xm = x / 1000; pts.push([x, (kappa * xm * xm / 2 + extra.k0 * xm * xm / 2 + extra.tilt * xm) * 1e6 + R.n() * noiseUm]); }
    return pts;
  }
  function fitCurvature(pts) { // z = a + b x + c x², κ = 2c (x in m, z in µm)
    let S = [0, 0, 0, 0, 0], Sy = [0, 0, 0];
    for (const [xmm, z] of pts) { const x = xmm / 1000, zz = z * 1e-6; let p = 1; for (let i = 0; i < 5; i++) { S[i] += p; if (i < 3) Sy[i] += p * zz; p *= x; } }
    const A = [[S[0], S[1], S[2]], [S[1], S[2], S[3]], [S[2], S[3], S[4]]];
    const sol = solve3(A, Sy); return 2 * sol[2];
  }
  function solve3(A, b) { const M = A.map((r, i) => [...r, b[i]]); for (let i = 0; i < 3; i++) { let p = i; for (let k = i + 1; k < 3; k++) if (Math.abs(M[k][i]) > Math.abs(M[p][i])) p = k; [M[i], M[p]] = [M[p], M[i]]; for (let k = i + 1; k < 3; k++) { const f = M[k][i] / M[i][i]; for (let j = i; j < 4; j++) M[k][j] -= f * M[i][j]; } } const x = [0, 0, 0]; for (let i = 2; i >= 0; i--) { let s = M[i][3]; for (let j = i + 1; j < 3; j++) s -= M[i][j] * x[j]; x[i] = s / M[i][i]; } return x; }
  const bowUm = (kappa, Dmm = 300) => (kappa * (Dmm / 1000) ** 2 / 8) * 1e6;
  // thermal mismatch stress after cooling from T_dep to 25 °C: σ_th = M_f (α_f − α_s) ΔT  (film expands more than Si → tensile +)
  function thermalStress(Mf_GPa, alphaF_ppm, Tdep, alphaS_ppm = 2.6) { return Mf_GPa * 1e3 * (alphaF_ppm - alphaS_ppm) * 1e-6 * (Tdep - 25); } // MPa
  // in-plane surface strain of a bowed wafer when chucked flat ≈ (t_s/2)·κ → wafer magnification in ppm
  const bowMagPpm = (kappa, ts_um = 775) => (ts_um * 1e-6 / 2) * kappa * 1e6;

  // ---------- overlay ----------
  // fields on a 300 mm wafer, 26 x 33 mm, 4 corner marks per field (±11, ±14.5 mm)
  function fieldGrid() {
    const F = [];
    for (let i = -5; i <= 5; i++) for (let j = -4; j <= 4; j++) {
      const X = i * 26, Y = j * 33; if (Math.hypot(Math.abs(X) + 13, Math.abs(Y) + 16.5) > 150) continue;
      for (const [x, y] of [[-11, -14.5], [11, -14.5], [-11, 14.5], [11, 14.5]]) F.push({ X, Y, x, y });
    }
    return F;
  }
  // p: { Tx, Ty (nm), Mwx, Mwy, Rw, Mfx, Mfy, Rf (ppm), noise (nm), tis (nm) }; positions in mm -> ppm*mm = nm
  function overlayVectors(p, seed) {
    const R = T.rng(seed);
    return fieldGrid().map((m) => {
      const dx = p.Tx + p.Mwx * m.X - p.Rw * m.Y + p.Mfx * m.x - p.Rf * m.y + R.n() * p.noise + p.tis;
      const dy = p.Ty + p.Mwy * m.Y + p.Rw * m.X + p.Mfy * m.y + p.Rf * m.x + R.n() * p.noise;
      return { ...m, dx, dy };
    });
  }
  // least-squares fit of the 8-term linear model (x and y fitted jointly for shared rotations)
  function overlayFit(v) {
    // unknowns: Tx, Ty, Mwx, Mwy, Rw, Mfx, Mfy, Rf
    const rows = [], ys = [];
    for (const m of v) { rows.push([1, 0, m.X, 0, -m.Y, m.x, 0, -m.y]); ys.push(m.dx); rows.push([0, 1, 0, m.Y, m.X, 0, m.y, m.x]); ys.push(m.dy); }
    const n = 8, A = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => rows.reduce((s, r) => s + r[i] * r[j], 0)));
    const b = Array.from({ length: n }, (_, i) => rows.reduce((s, r, k) => s + r[i] * ys[k], 0));
    const c = gaussN(A, b);
    const res = v.map((m, i) => ({ ...m, rx: m.dx - rows[2 * i].reduce((s, r, j) => s + r * c[j], 0), ry: m.dy - rows[2 * i + 1].reduce((s, r, j) => s + r * c[j], 0) }));
    const stat = (arr) => { const mu = arr.reduce((a, b2) => a + b2, 0) / arr.length; const sd = Math.sqrt(arr.reduce((a, b2) => a + (b2 - mu) ** 2, 0) / (arr.length - 1)); return { mu, sd, m3s: Math.abs(mu) + 3 * sd }; };
    return { c: { Tx: c[0], Ty: c[1], Mwx: c[2], Mwy: c[3], Rw: c[4], Mfx: c[5], Mfy: c[6], Rf: c[7] }, res, raw: { x: stat(v.map((m) => m.dx)), y: stat(v.map((m) => m.dy)) }, resid: { x: stat(res.map((m) => m.rx)), y: stat(res.map((m) => m.ry)) } };
  }
  function gaussN(A, b) { const n = b.length, M = A.map((r, i) => [...r, b[i]]); for (let i = 0; i < n; i++) { let p = i; for (let k = i + 1; k < n; k++) if (Math.abs(M[k][i]) > Math.abs(M[p][i])) p = k; [M[i], M[p]] = [M[p], M[i]]; for (let k = i + 1; k < n; k++) { const f = M[k][i] / M[i][i]; for (let j = i; j <= n; j++) M[k][j] -= f * M[i][j]; } } const x = new Array(n).fill(0); for (let i = n - 1; i >= 0; i--) { let s = M[i][n]; for (let j = i + 1; j < n; j++) s -= M[i][j] * x[j]; x[i] = s / M[i][i]; } return x; }

  // ---------- CD-SEM linescan ----------
  // trapezoid line (or hole) of topCD, height h, sidewall angle swa (deg). SE yield: flat δ0, slopes δ0/cos(θ) (secant law)
  // plus an edge "bloom" where SE escape through the sidewall; Gaussian beam blur; shot noise from frames.
  function linescan(g, seed) {
    const xs = [], sig = [];
    const half = g.topCD / 2, foot = g.h / Math.tan((g.swa * Math.PI) / 180), botHalf = half + foot;
    // line: top plateau |x|<half, sloped walls to botHalf, substrate beyond.
    // hole: opening of width topCD at the surface, walls narrowing to the bottom (half - foot), dark bottom.
    const wallY = Math.min(3.2, 1 / Math.cos((g.swa * Math.PI) / 180)) * 0.35 + 0.9; // secant law, clamped
    const raw = (x) => {
      const ax = Math.abs(x);
      if (!g.hole) {
        let y = ax <= half ? 1.1 : ax <= botHalf ? wallY : 1.0;
        y += 1.2 * Math.exp(-(((ax - half) / 2.5) ** 2)); // edge bloom: SE escape through the top corner
        return y;
      }
      const bHalf = Math.max(half - foot, 1);
      let y = ax >= half ? 1.0 : ax >= bHalf ? wallY : 0.3; // hole bottom: SE are trapped
      y += 1.0 * Math.exp(-(((ax - half) / 2.5) ** 2));
      return y;
    };
    const R = T.rng(seed), dx = 0.5, span = Math.max(80, botHalf * 2.6);
    const xr = []; for (let x = -span; x <= span; x += dx) xr.push(x);
    const r = xr.map(raw);
    const s = g.beam; const kw = Math.ceil((3 * s) / dx); const ker = []; let ks = 0;
    for (let i = -kw; i <= kw; i++) { const w = Math.exp(-0.5 * ((i * dx) / s) ** 2); ker.push(w); ks += w; }
    for (let i = 0; i < xr.length; i++) { let v = 0; for (let k = -kw; k <= kw; k++) { const j = Math.min(xr.length - 1, Math.max(0, i + k)); v += r[j] * ker[k + kw]; } xs.push(xr[i]); sig.push(v / ks + (R.n() * 0.25) / Math.sqrt(g.frames)); }
    return { x: xs, y: sig, half, botHalf, hole: !!g.hole };
  }
  // threshold edge detection on each side: level = min + t·(max-min), searching outward from the peak
  function cdThreshold(ls, t) {
    const n = ls.x.length, mid = Math.floor(n / 2);
    if (ls.hole) { // dark bottom in the middle: walk outward from the centre minimum to the wall peak
      const edgeH = (dir) => {
        const end = dir > 0 ? n - 1 : 0; let pk = mid;
        for (let i = mid; i !== end; i += dir) if (ls.y[i] > ls.y[pk]) pk = i;
        let mn = mid; for (let i = mid; i !== pk; i += dir) if (ls.y[i] < ls.y[mn]) mn = i;
        const lvl = ls.y[mn] + t * (ls.y[pk] - ls.y[mn]);
        for (let i = mn; i !== pk; i += dir) if (ls.y[i] >= lvl) { const f = (lvl - ls.y[i - dir]) / (ls.y[i] - ls.y[i - dir]); return ls.x[i - dir] + f * (ls.x[i] - ls.x[i - dir]); }
        return ls.x[pk];
      };
      return edgeH(1) - edgeH(-1);
    }
    const edge = (dir) => {
      let pk = mid; const end = dir > 0 ? n - 1 : 0;
      for (let i = mid; i !== end; i += dir) if (ls.y[i] > ls.y[pk]) pk = i;
      let mn = pk; for (let i = pk; i !== end; i += dir) if (ls.y[i] < ls.y[mn]) mn = i;
      const lvl = ls.y[mn] + t * (ls.y[pk] - ls.y[mn]);
      for (let i = pk; i !== mn; i += dir) if (ls.y[i] <= lvl) { const f = (ls.y[i - dir] - lvl) / (ls.y[i - dir] - ls.y[i]); return ls.x[i - dir] + f * (ls.x[i] - ls.x[i - dir]); }
      return ls.x[mn];
    };
    return edge(1) - edge(-1);
  }
  // pattern recognition score: normalized cross-correlation with the stored template
  function prScore(a, b) {
    const n = Math.min(a.length, b.length), ma = a.slice(0, n).reduce((s, v) => s + v, 0) / n, mb = b.slice(0, n).reduce((s, v) => s + v, 0) / n;
    let sab = 0, saa = 0, sbb = 0; for (let i = 0; i < n; i++) { sab += (a[i] - ma) * (b[i] - mb); saa += (a[i] - ma) ** 2; sbb += (b[i] - mb) ** 2; }
    return sab / Math.sqrt(saa * sbb);
  }

  // ---------- grating OCD (zeroth-order EMA, valid for pitch << λ) ----------
  // trench etched into Si (or a film on Si): lines of material, spaces of air. topCD = line top width, swa, depth.
  function emaTE(f, n1, n2) { return csqrt(add(mul(C(f), mul(n1, n1)), mul(C(1 - f), mul(n2, n2)))); }
  function emaTM(f, n1, n2) { const inv = add(div(C(f), mul(n1, n1)), div(C(1 - f), mul(n2, n2))); return csqrt(div(C(1), inv)); }
  function gratingLayers(l, g, pol, slices = 12) {
    const nSi = T.MAT.Si(l), nAir = C(1), L = [];
    for (let i = 0; i < slices; i++) {
      const z = (i + 0.5) / slices; // 0 top .. 1 bottom
      const w = g.topCD + 2 * z * g.depth / Math.tan((g.swa * Math.PI) / 180);
      const f = Math.min(Math.max(w / g.pitch, 0.02), 0.98);
      L.push({ n: pol === 'TE' ? emaTE(f, nSi, nAir) : emaTM(f, nSi, nAir), d: g.depth / slices });
    }
    if (g.hm > 0) L.unshift({ n: T.MAT.SiO2(l), d: g.hm }); // oxide hard mask left on top of the lines (approximated as a uniform layer)
    return L;
  }
  const WLO = []; for (let l = 250; l <= 800; l += 10) WLO.push(l);
  function ocdSpectra(g) { return { TE: WLO.map((l) => T.reflectance(l, gratingLayers(l, g, 'TE'), T.MAT.Si(l), 0)), TM: WLO.map((l) => T.reflectance(l, gratingLayers(l, g, 'TM'), T.MAT.Si(l), 0)) }; }
  // fit depth, topCD, swa to measured TE+TM spectra
  function ocdFit(meas, g0, noise, free = ['depth', 'topCD', 'swa']) {
    let x = free.map((k) => g0[k]);
    const model = (xx) => { const g = { ...g0 }; free.forEach((k, i) => { g[k] = xx[i]; }); const s = ocdSpectra(g); return [...s.TE, ...s.TM]; };
    const y = [...meas.TE, ...meas.TM];
    const resid = (xx) => model(xx).map((v, i) => (y[i] - v) / noise);
    let r = resid(x), chi = r.reduce((s, v) => s + v * v, 0), lam = 1e-2, J = null;
    const h = free.map((k) => (k === 'swa' ? 0.05 : 0.05));
    for (let it = 0; it < 40; it++) {
      J = x.map((_, j) => { const xp = x.slice(), xm = x.slice(); xp[j] += h[j]; xm[j] -= h[j]; const a = resid(xp), b = resid(xm); return a.map((v, k) => (v - b[k]) / (2 * h[j])); });
      const P = x.length, A = Array.from({ length: P }, (_, a) => Array.from({ length: P }, (_, b) => J[a].reduce((s, v, k) => s + v * J[b][k], 0)));
      const g = Array.from({ length: P }, (_, a) => J[a].reduce((s, v, k) => s + v * r[k], 0));
      let ok = false;
      for (let t = 0; t < 8; t++) {
        const M = A.map((row, a) => row.map((v, b) => (a === b ? v * (1 + lam) : v)));
        const dx = gaussN(M, g.map((v) => -v)); const xn = x.map((v, j) => v + dx[j]);
        if (free.includes('swa')) { const k = free.indexOf('swa'); xn[k] = Math.min(Math.max(xn[k], 70), 90); }
        const rn = resid(xn), cn = rn.reduce((s, v) => s + v * v, 0);
        if (cn < chi) { const dc = chi - cn; x = xn; r = rn; chi = cn; lam = Math.max(lam / 5, 1e-9); ok = true; if (dc < 1e-8 * (1 + chi)) it = 99; break; }
        lam *= 8;
      }
      if (!ok) break;
    }
    const P = x.length, A = Array.from({ length: P }, (_, a) => Array.from({ length: P }, (_, b) => J[a].reduce((s, v, k) => s + v * J[b][k], 0)));
    const cov = Array.from({ length: P }, (_, j) => gaussN(A, Array.from({ length: P }, (_, i) => (i === j ? 1 : 0)))); // columns
    const corr = cov.map((row, a) => row.map((v, b) => v / Math.sqrt(cov[a][a] * cov[b][b])));
    const out = {}; free.forEach((k, i) => { out[k] = x[i]; });
    return { fit: out, sd: free.map((_, i) => Math.sqrt(cov[i][i] * Math.max(chi / (y.length - P), 1))), corr, chi2nu: chi / (y.length - P), names: free, model: model(x) };
  }

  const api = { gof, gofBand, WLR, rSpec, dSpec, sensitivity, corrDN, corrDNrefl, fftThickness, MS_SI, stoneyStress, kappaFromStress, scan, fitCurvature, bowUm, thermalStress, bowMagPpm, fieldGrid, overlayVectors, overlayFit, linescan, cdThreshold, prScore, emaTE, emaTM, gratingLayers, WLO, ocdSpectra, ocdFit };
  root.DMS.ext = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
