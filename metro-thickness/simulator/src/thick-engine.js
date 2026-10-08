/* DRAM Thickness Metro — thickness engine (pure functions, no DOM).
   Optics (Airy/TMM, Psi/Delta), XRR (Parratt), XRF, Levenberg–Marquardt fit,
   ALD wafer map, step coverage in the capacitor hole, dielectric leakage,
   and the thickness pipeline that feeds the DRAM engine.
   Every number marked 🔴 is illustrative; see THICK_DEFS sources. */
(function (root) {
  'use strict';

  // ---------- seeded RNG ----------
  function rng(seed) {
    let a = seed >>> 0;
    const u = () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const n = () => { let x = 0, y = 0; while (x === 0) x = u(); while (y === 0) y = u(); return Math.sqrt(-2 * Math.log(x)) * Math.cos(2 * Math.PI * y); };
    return { u, n };
  }

  // ---------- complex arithmetic: [re, im] ----------
  const C = (re, im = 0) => [re, im];
  const add = (a, b) => [a[0] + b[0], a[1] + b[1]];
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1]];
  const mul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
  const div = (a, b) => { const d = b[0] * b[0] + b[1] * b[1]; return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d]; };
  const csqrt = (a) => { const r = Math.hypot(a[0], a[1]); let re = Math.sqrt((r + a[0]) / 2), im = Math.sqrt(Math.max(0, (r - a[0]) / 2)); if (a[1] < 0) im = -im; return [re, im]; };
  const cexp = (a) => { const e = Math.exp(a[0]); return [e * Math.cos(a[1]), e * Math.sin(a[1])]; };
  const abs2 = (a) => a[0] * a[0] + a[1] * a[1];

  // ---------- optical constants (n + ik), wavelength in nm ----------
  const cauchy = (l, A, B) => A + B / ((l / 1000) ** 2);
  const MAT = {
    // ZrO2: n 2.08–2.14 near 550 nm (Yusoh 2012); crystallised (tetragonal) films index higher (Yoon 2011). 🟠 shape, 🔴 exact values
    ZrO2: (l, fT) => C(cauchy(l, 2.04 + 0.04 * fT, 0.0185), 0),
    Al2O3: (l) => C(cauchy(l, 1.63, 0.006), 0),
    TiOx: (l) => C(cauchy(l, 2.25, 0.045), 0.01),
    // TiN: Drude, eps_inf 4.0, hbar*wp 5.6 eV, gamma 0.35 eV 🔴 illustrative
    TiN: (l) => {
      const E = 1239.84 / l, einf = 4.0, wp = 5.6, g = 0.35;
      const den = E * E + g * g;
      const e1 = einf - (wp * wp) / den, e2 = (wp * wp * g) / (E * den);
      return csqrt([e1, e2]);
    },
    Si: (l) => {
      const tab = [[300, 5.0, 4.2], [350, 5.48, 2.94], [400, 5.57, 0.387], [450, 4.67, 0.145], [500, 4.30, 0.073], [550, 4.08, 0.041], [600, 3.95, 0.025], [650, 3.85, 0.017], [700, 3.78, 0.012], [800, 3.69, 0.006], [900, 3.63, 0.003]];
      for (let i = 0; i < tab.length - 1; i++) {
        const a = tab[i], b = tab[i + 1];
        if (l <= b[0]) { const t = (l - a[0]) / (b[0] - a[0]); return C(a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])); }
      }
      return C(3.63, 0.003);
    },
    SiO2: (l) => C(cauchy(l, 1.448, 0.00356), 0),
  };

  // ---------- thin-film optics ----------
  function cosIn(n0, sin0, nj) { const s = div(C(n0 * sin0), nj); return csqrt(sub(C(1), mul(s, s))); }
  function fres(ni, nj, ci, cj) {
    const a = mul(ni, ci), b = mul(nj, cj), c = mul(nj, ci), d = mul(ni, cj);
    return [div(sub(a, b), add(a, b)), div(sub(c, d), add(c, d))];
  }
  // layers: [{n: complex, d: nm}] from top; ambient n=1; substrate complex n
  function stackR(l, layers, nSub, thetaDeg) {
    const th = (thetaDeg * Math.PI) / 180, s0 = Math.sin(th);
    const ns = [C(1), ...layers.map((x) => x.n), nSub];
    const cs = ns.map((n) => cosIn(1, s0, n));
    let [rs, rp] = fres(ns[ns.length - 2], ns[ns.length - 1], cs[ns.length - 2], cs[ns.length - 1]);
    for (let j = ns.length - 2; j >= 1; j--) {
      const beta = mul(C((2 * Math.PI * layers[j - 1].d) / l), mul(ns[j], cs[j]));
      const e = cexp(mul(C(0, 2), beta));
      const [r01s, r01p] = fres(ns[j - 1], ns[j], cs[j - 1], cs[j]);
      const rse = mul(rs, e), rpe = mul(rp, e);
      rs = div(add(r01s, rse), add(C(1), mul(r01s, rse)));
      rp = div(add(r01p, rpe), add(C(1), mul(r01p, rpe)));
    }
    return [rs, rp];
  }
  function reflectance(l, layers, nSub, thetaDeg = 0) { const [rs, rp] = stackR(l, layers, nSub, thetaDeg); return 0.5 * (abs2(rs) + abs2(rp)); }
  function psiDelta(l, layers, nSub, thetaDeg = 65) {
    const [rs, rp] = stackR(l, layers, nSub, thetaDeg);
    const rho = div(rp, rs);
    const psi = (Math.atan(Math.sqrt(abs2(rho))) * 180) / Math.PI;
    let del = (Math.atan2(rho[1], rho[0]) * 180) / Math.PI; if (del < 0) del += 360;
    return [psi, del];
  }

  // ---------- the ZAZ monitor stack (true film) and the recipe model ----------
  // truth: air / ZrO2(top, tZ/2) / Al2O3(tA) / ZrO2(bottom, tZ/2) / TiOx IL / TiN
  function zazLayers(l, f) {
    const z = MAT.ZrO2(l, f.fT);
    const L = [{ n: z, d: f.tZ / 2 }, { n: MAT.Al2O3(l), d: f.tA }, { n: z, d: f.tZ / 2 }];
    if (f.tIL > 0) L.push({ n: MAT.TiOx(l), d: f.tIL });
    if (f.amc > 0) L.unshift({ n: C(1.45), d: f.amc }); // adsorbed hydrocarbon/water layer on monitor
    return L;
  }
  const WL = []; for (let l = 300; l <= 900; l += 10) WL.push(l);
  function spectrum(f, theta = 65) { return WL.map((l) => psiDelta(l, zazLayers(l, f), MAT.TiN(l), theta)); }

  // model film from parameter vector according to recipe config
  // cfg: { floatTA, floatN, includeIL, ilFixed, libFT, fitAMC }
  function modelFilm(cfg, x) {
    let i = 0;
    const tZ = x[i++];
    const tA = cfg.floatTA ? x[i++] : cfg.tAfixed;
    const dn = cfg.floatN ? x[i++] : 0;
    return { tZ, tA, tIL: cfg.includeIL ? cfg.ilFixed : 0, fT: cfg.libFT + dn / 0.04, amc: 0 };
  }
  function paramNames(cfg) { return ['tZ', ...(cfg.floatTA ? ['tA'] : []), ...(cfg.floatN ? ['Δn'] : [])]; }

  function residuals(cfg, x, data, sig) {
    const f = modelFilm(cfg, x), m = spectrum(f), r = [];
    for (let i = 0; i < WL.length; i++) { r.push((data[i][0] - m[i][0]) / sig[0]); let d = data[i][1] - m[i][1]; if (d > 180) d -= 360; if (d < -180) d += 360; r.push(d / sig[1]); }
    return r;
  }
  // Levenberg–Marquardt with numeric Jacobian. Returns fit, covariance, correlations, chi2nu, residual spectra.
  function lmFit(cfg, data, sig, x0) {
    let x = x0.slice(), lam = 1e-3;
    let r = residuals(cfg, x, data, sig), chi = r.reduce((s, v) => s + v * v, 0);
    const P = x.length, h = [1e-4, 1e-4, 1e-5];
    let J = null;
    for (let it = 0; it < 60; it++) {
      J = x.map((_, j) => { const xp = x.slice(), xm = x.slice(); xp[j] += h[j]; xm[j] -= h[j]; const rp = residuals(cfg, xp, data, sig), rm = residuals(cfg, xm, data, sig); return rp.map((v, k) => (v - rm[k]) / (2 * h[j])); });
      const A = Array.from({ length: P }, (_, a) => Array.from({ length: P }, (_, b) => J[a].reduce((s, v, k) => s + v * J[b][k], 0)));
      const g = Array.from({ length: P }, (_, a) => J[a].reduce((s, v, k) => s + v * r[k], 0));
      let improved = false;
      for (let tries = 0; tries < 8; tries++) {
        const M = A.map((row, a) => row.map((v, b) => (a === b ? v * (1 + lam) : v)));
        const dx = solve(M, g.map((v) => -v));
        const xn = x.map((v, j) => v + dx[j]);
        const rn = residuals(cfg, xn, data, sig), cn = rn.reduce((s, v) => s + v * v, 0);
        if (cn < chi) { x = xn; r = rn; const dc = chi - cn; chi = cn; lam = Math.max(lam / 5, 1e-9); improved = true; if (dc < 1e-9 * (1 + chi)) it = 99; break; }
        lam *= 8;
      }
      if (!improved) break;
    }
    const A = Array.from({ length: P }, (_, a) => Array.from({ length: P }, (_, b) => J[a].reduce((s, v, k) => s + v * J[b][k], 0)));
    const N = r.length, chi2nu = chi / Math.max(N - P, 1);
    const cov = inv(A).map((row) => row.map((v) => v * Math.max(chi2nu, 1)));
    const corr = cov.map((row, a) => row.map((v, b) => v / Math.sqrt(cov[a][a] * cov[b][b])));
    return { x, cov, corr, chi2nu, sd: cov.map((row, a) => Math.sqrt(row[a])), resid: r, names: paramNames(cfg) };
  }
  function solve(M, b) { const A = M.map((r, i) => [...r, b[i]]), n = b.length; for (let i = 0; i < n; i++) { let p = i; for (let k = i + 1; k < n; k++) if (Math.abs(A[k][i]) > Math.abs(A[p][i])) p = k; [A[i], A[p]] = [A[p], A[i]]; for (let k = i + 1; k < n; k++) { const f = A[k][i] / A[i][i]; for (let j = i; j <= n; j++) A[k][j] -= f * A[i][j]; } } const x = new Array(n).fill(0); for (let i = n - 1; i >= 0; i--) { let s = A[i][n]; for (let j = i + 1; j < n; j++) s -= A[i][j] * x[j]; x[i] = s / A[i][i]; } return x; }
  function inv(M) { const n = M.length; return Array.from({ length: n }, (_, j) => solve(M, Array.from({ length: n }, (_, i) => (i === j ? 1 : 0)))).reduce((acc, col, j) => { col.forEach((v, i) => { acc[i][j] = v; }); return acc; }, Array.from({ length: n }, () => new Array(n).fill(0))); }

  // Measure the true film with the recipe: noise-free fit gives systematic bias; noisy repeats give precision.
  function measure(truth, cfg, noise, seed, repeats) {
    const sig = [noise.psi, noise.delta];
    const clean = spectrum(truth);
    const x0 = [truth.tZ + 0.3, ...(cfg.floatTA ? [cfg.tAfixed] : []), ...(cfg.floatN ? [0] : [])];
    const sys = lmFit(cfg, clean, sig, x0);
    const R = rng(seed), reps = [];
    let one = null;
    for (let k = 0; k < repeats; k++) {
      const data = clean.map(([p, d]) => [p + R.n() * sig[0], d + R.n() * sig[1]]);
      const f = lmFit(cfg, data, sig, sys.x);
      reps.push(f.x);
      if (k === 0) one = { ...f, data };
    }
    const mean = sys.x.map((_, j) => reps.reduce((s, v) => s + v[j], 0) / reps.length);
    const sd = sys.x.map((_, j) => Math.sqrt(reps.reduce((s, v) => s + (v[j] - mean[j]) ** 2, 0) / Math.max(reps.length - 1, 1)));
    return { sys, reps, mean, sd, one, clean, model: spectrum(modelFilm(cfg, sys.x)) };
  }

  // ---------- XRR (Parratt) ----------
  const RE = 2.8179403262e-15, NA = 6.02214076e23, LAM_X = 1.5406e-10;
  const XMAT = { ZrO2: { rho: 5.68, Z: 56, M: 123.22, bd: 0.03 }, Al2O3: { rho: 3.0, Z: 50, M: 101.96, bd: 0.01 }, TiOx: { rho: 3.9, Z: 38, M: 79.87, bd: 0.03 }, TiN: { rho: 5.4, Z: 29, M: 61.87, bd: 0.05 }, CHx: { rho: 1.0, Z: 8, M: 14, bd: 0.001 } };
  function xdelta(m, rhoScale = 1) { const ne = ((m.rho * rhoScale * 1e6) / m.M) * NA * m.Z; const d = (RE * LAM_X * LAM_X * ne) / (2 * Math.PI); return [d, d * m.bd]; }
  // layers top->bottom {mat, d(nm), sig(nm), rhoScale}; substrate mat name
  function xrr(layers, subMat, thetasDeg) {
    const k0 = (2 * Math.PI) / (LAM_X * 1e9); // nm^-1
    const L = [{ db: [0, 0], d: 0, sigTop: 0 }, ...layers.map((x) => ({ db: xdelta(XMAT[x.mat], x.rhoScale || 1), d: x.d, sigTop: x.sigTop || 0 })), { db: xdelta(XMAT[subMat]), d: 0, sigTop: 0.3 }];
    return thetasDeg.map((t) => {
      const c = Math.cos((t * Math.PI) / 180);
      const kz = L.map((x) => { const n = [1 - x.db[0], x.db[1]]; return mul(C(k0), csqrt(sub(mul(n, n), C(c * c)))); });
      let X = C(0);
      for (let j = L.length - 2; j >= 0; j--) {
        const s = L[j + 1].sigTop; // roughness of the interface above layer j+1 (Nevot–Croce)
        let r = div(sub(kz[j], kz[j + 1]), add(kz[j], kz[j + 1]));
        r = mul(r, cexp(mul(C(-2 * s * s), mul(kz[j], kz[j + 1]))));
        const e = j + 1 < L.length - 1 ? cexp(mul(C(0, 2 * L[j + 1].d), kz[j + 1])) : C(1);
        const Xe = mul(X, e);
        X = div(add(r, Xe), add(C(1), mul(r, Xe)));
      }
      return abs2(X);
    });
  }
  function zazXrrLayers(f, opts) {
    const rough = 0.25 + 0.35 * f.fT; // crystallised ZrO2 roughens (Park 2025) 🔴 magnitude
    const L = [];
    if (f.amc > 0) L.push({ mat: 'CHx', d: f.amc, sigTop: 0.2 });
    L.push({ mat: 'ZrO2', d: f.tZ / 2, sigTop: rough, rhoScale: f.rhoZ || 1 });
    if (!opts || !opts.noAl) L.push({ mat: 'Al2O3', d: f.tA, sigTop: 0.25 });
    L.push({ mat: 'ZrO2', d: opts && opts.noAl ? f.tZ / 2 + f.tA : f.tZ / 2, sigTop: 0.25, rhoScale: f.rhoZ || 1 });
    if (f.tIL > 0) L.push({ mat: 'TiOx', d: f.tIL, sigTop: 0.25 });
    return L;
  }
  function xrrCurve(f, opts) {
    const th = []; for (let t = 0.1; t <= 4.0001; t += 0.01) th.push(+t.toFixed(3));
    return { th, R: xrr(zazXrrLayers(f, opts), 'TiN', th) };
  }

  // ---------- XRF (TiN bottom electrode) ----------
  // I/I_inf = 1 - exp(-mu* rho t); recipe converts mass thickness with a fixed calibration density.
  function xrf(tTiN_nm, rho, rhoCal = 5.4) {
    const mu = 0.012; // per (g/cm3 * nm), 🔴 illustrative so that 10 nm is well inside the linear range
    const I = 1 - Math.exp(-mu * rho * tTiN_nm);
    const mass = -Math.log(1 - I) / mu; // rho*t recovered
    return { I, reported: mass / rhoCal, mass };
  }

  // ---------- ALD process ----------
  function gpcFactor(T) { // ALD window 250–300 °C 🟠 shape
    if (T < 250) return 1 - 0.006 * (250 - T);
    if (T > 300) return 1 + 0.012 * (T - 300);
    return 1;
  }
  // relative mean thickness vs. the recipe nominal (cycles N0 = tZ/gpc0)
  function aldMean(tZnom, ald, gpc0) {
    const N0 = tZnom / gpc0, N = N0 + ald.dN;
    const dep = N * ald.gpc * gpcFactor(ald.T);
    const cvd = Math.max(0, 1 - ald.purge) * 0.12 * tZnom; // parasitic CVD from short purge 🔴
    return { mean: dep + cvd, cvd, N };
  }
  // site thickness on a 300 mm wafer (x,y in mm)
  function aldSite(mean, cvd, ald, x, y) {
    const R = 150, rho2 = (x * x + y * y) / (R * R), rho = Math.sqrt(rho2);
    const dome = (ald.dome / 100) * (0.5 - rho2);           // + dome: centre thick
    const tilt = (ald.tilt / 100) * (x / R);
    const edge = (ald.edge / 100) * Math.exp(-(1 - rho) / 0.035);
    const cvdShape = cvd * (1.5 * (0.5 - rho2));             // parasitic CVD is centre-heavy (showerhead)
    return mean * (1 + dome + tilt + edge) + cvdShape;
  }
  function polarSites(rings) { // e.g. [1,8,16,24] on radius 147 mm
    const out = [], nR = rings.length - 1;
    rings.forEach((n, i) => { if (i === 0) { out.push([0, 0]); return; } const r = (147 * i) / nR; for (let k = 0; k < n; k++) { const a = (2 * Math.PI * k) / n + (i % 2 ? 0 : Math.PI / n); out.push([r * Math.cos(a), r * Math.sin(a)]); } });
    return out;
  }
  const PLANS = {
    p5: { zh: '5 點', sites: [[0, 0], [98, 0], [-98, 0], [0, 98], [0, -98]] },
    p9: { zh: '9 點', sites: [[0, 0], ...polarSites([1, 8]).slice(1).map(([x, y]) => [x * 0.66, y * 0.66])] },
    p13: { zh: '13 點', sites: polarSites([1, 4, 8]) },
    p49: { zh: '49 點', sites: polarSites([1, 8, 16, 24]) },
  };

  // ---------- step coverage inside the capacitor hole ----------
  // penetration depth (in aspect-ratio units) ∝ sqrt(exposure / GPC)  (Gonsalves et al. 2026, Knudsen regime)
  function coverageProfile(AR, ald, gpc0, xpd0, nSlices = 40) {
    const xpd = xpd0 * Math.sqrt(ald.exposure / (ald.gpc / gpc0));
    const w = 0.15 * xpd, prof = [];
    for (let i = 0; i < nSlices; i++) {
      const z = ((i + 0.5) / nSlices) * AR; // depth from top in AR units
      const th = z <= xpd - w ? 1 : z >= xpd + w ? 0 : (xpd + w - z) / (2 * w);
      prof.push({ z, th: Math.max(th, 0.05) });
    }
    return { xpd, prof, bottom: prof[prof.length - 1].th };
  }

  // ---------- dielectric leakage (cell bias) ----------
  // J = J0 * 10^(-(tLeak - t0)/dec), tLeak = tZ + wA*tA  (Al2O3 suppresses leakage per nm more strongly). 🔴 values; spec scale 🟠
  const J_SHORT = 1e-3; // A/cm2: treat as a hard short when the film is nearly absent
  function jLeak(tZ, tA, L) { return Math.min(J_SHORT, L.J0 * Math.pow(10, -((tZ + L.wA * tA) - L.t0) / L.dec)); }

  // ---------- the pipeline: settings -> effective DRAM parameters ----------
  const THICK_DEFAULTS = {
    gpc0: 0.09,
    ald: { dN: 0, gpc: 0.09, T: 275, purge: 1.0, dome: 0, tilt: 0, edge: 0, exposure: 1.0 },
    film: { tIL: 0.5, amc: 0, rhoZ: 1 },
    metro: { modelBias: 0, toolBias: 0, apcOn: false },
    leak: { J0: 3e-10, t0: 7.0, dec: 0.25, wA: 2 },
    xpd0: 70,
  };
  const clone = (o) => JSON.parse(JSON.stringify(o));
  function pipeline(p, th) {
    const a = aldMean(p.tZ_nm, th.ald, th.gpc0);
    const procMult = a.mean / p.tZ_nm;
    const metroBias = th.metro.modelBias + th.metro.toolBias; // AMC on the monitor enters through T1 (it is part of the measured film)
    // APC removes process drift but inherits Metro bias; siteT pins a wafer-map site thickness (T2)
    const tTrue = th.siteT != null ? th.siteT : th.metro.apcOn ? p.tZ_nm - metroBias : a.mean;
    const reported = tTrue + metroBias;
    const AR = p.H_nm / p.D_nm;
    const cov = coverageProfile(AR, th.ald, th.gpc0, th.xpd0);
    const kZ = p.fT * p.kT + (1 - p.fT) * p.kM;
    let invEOT = 0, I = 0;
    for (const s of cov.prof) {
      const t = tTrue * s.th, eot = 3.9 * (t / kZ + p.tA_nm / p.kA);
      invEOT += 1 / eot; I += jLeak(t, p.tA_nm, th.leak);
    }
    const n = cov.prof.length;
    const eotEff = n / invEOT;
    const tZeff = kZ * (eotEff / 3.9 - p.tA_nm / p.kA);
    const Jcell = I / n;
    return {
      params: { ...p, tZ_nm: tZeff, Jcell_Acm2: Jcell },
      info: { tTrue, reported, metroBias, procMult, cvd: a.cvd, N: a.N, AR, xpd: cov.xpd, prof: cov.prof, bottom: cov.bottom, tBottom: tTrue * cov.bottom, tZeff, Jcell, Jtop: jLeak(tTrue, p.tA_nm, th.leak) },
    };
  }
  const round = (k, v) => (typeof v === 'number' ? Math.round(v * 1e4) / 1e4 : v);
  function isNominal(th) { return JSON.stringify(th, round) === JSON.stringify(THICK_DEFAULTS, round); }

  // ---------- statistics for T3 ----------
  function runRules(x, c, s) {
    const z = x.map((v) => (v - c) / s), hits = { R1: [], R2: [], R3: [], R4: [], R5: [] };
    for (let i = 0; i < z.length; i++) {
      if (Math.abs(z[i]) > 3) hits.R1.push(i);
      if (i >= 2) { const w = z.slice(i - 2, i + 1); if (w.filter((v) => v > 2).length >= 2 || w.filter((v) => v < -2).length >= 2) hits.R2.push(i); }
      if (i >= 4) { const w = z.slice(i - 4, i + 1); if (w.filter((v) => v > 1).length >= 4 || w.filter((v) => v < -1).length >= 4) hits.R3.push(i); }
      if (i >= 7) { const w = z.slice(i - 7, i + 1); if (w.every((v) => v > 0) || w.every((v) => v < 0)) hits.R4.push(i); }
      if (i >= 5) { const w = z.slice(i - 5, i + 1); let up = true, dn = true; for (let k = 1; k < w.length; k++) { if (!(w[k] > w[k - 1])) up = false; if (!(w[k] < w[k - 1])) dn = false; } if (up || dn) hits.R5.push(i); }
    }
    return hits;
  }
  function ewma(x, c, s, lam = 0.2, L = 3) {
    let z = c; const out = [];
    x.forEach((v, i) => { z = lam * v + (1 - lam) * z; const w = L * s * Math.sqrt((lam / (2 - lam)) * (1 - (1 - lam) ** (2 * (i + 1)))); out.push({ z, lo: c - w, hi: c + w, alarm: z > c + w || z < c - w }); });
    return out;
  }
  function meanSd(x) { const m = x.reduce((a, b) => a + b, 0) / x.length; const s = Math.sqrt(x.reduce((a, b) => a + (b - m) ** 2, 0) / Math.max(x.length - 1, 1)); return { m, s }; }
  function cpk(x, lsl, usl) { const { m, s } = meanSd(x); const v = Math.min(usl - m, m - lsl) / (3 * s); const n = x.length; const se = Math.sqrt(1 / (9 * n) + (v * v) / (2 * (n - 1))); return { cpk: v, lo: v - 1.96 * se, hi: v + 1.96 * se, m, s }; }
  // crossed ANOVA gauge R&R, y[p][o][r]
  function grr(y, lsl, usl) {
    const p = y.length, o = y[0].length, r = y[0][0].length;
    let gm = 0; y.forEach((a) => a.forEach((b) => b.forEach((v) => { gm += v; }))); gm /= p * o * r;
    const mp = y.map((a) => a.flat().reduce((s, v) => s + v, 0) / (o * r));
    const mo = Array.from({ length: o }, (_, j) => y.reduce((s, a) => s + a[j].reduce((q, v) => q + v, 0), 0) / (p * r));
    const mpo = y.map((a) => a.map((b) => b.reduce((s, v) => s + v, 0) / r));
    let ssp = 0, sso = 0, sspo = 0, sse = 0;
    mp.forEach((v) => { ssp += o * r * (v - gm) ** 2; }); mo.forEach((v) => { sso += p * r * (v - gm) ** 2; });
    for (let i = 0; i < p; i++) for (let j = 0; j < o; j++) { sspo += r * (mpo[i][j] - mp[i] - mo[j] + gm) ** 2; for (let k = 0; k < r; k++) sse += (y[i][j][k] - mpo[i][j]) ** 2; }
    const msp = ssp / (p - 1), mso = sso / (o - 1), mspo = sspo / ((p - 1) * (o - 1)), mse = sse / (p * o * (r - 1));
    const vE = mse, vPO = Math.max((mspo - mse) / r, 0), vO = Math.max((mso - mspo) / (p * r), 0), vP = Math.max((msp - mspo) / (o * r), 0);
    const vG = vE + vO + vPO;
    return { rep: Math.sqrt(vE), repro: Math.sqrt(vO + vPO), grr: Math.sqrt(vG), part: Math.sqrt(vP), pt: (6 * Math.sqrt(vG)) / (usl - lsl), pctTotal: Math.sqrt(vG / (vG + vP)), ndc: (1.41 * Math.sqrt(vP)) / Math.sqrt(vG) };
  }
  function deming(x, y) {
    const n = x.length, mx = x.reduce((a, b) => a + b, 0) / n, my = y.reduce((a, b) => a + b, 0) / n;
    let sxx = 0, syy = 0, sxy = 0; for (let i = 0; i < n; i++) { sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; sxy += (x[i] - mx) * (y[i] - my); }
    sxx /= n; syy /= n; sxy /= n;
    const b1 = (syy - sxx + Math.sqrt((syy - sxx) ** 2 + 4 * sxy * sxy)) / (2 * sxy);
    return { b0: my - b1 * mx, b1 };
  }
  function deltaSigma(s0, s1, rho) { return Math.sqrt(Math.max(s0 * s0 + s1 * s1 - 2 * rho * s0 * s1, 0)); }

  const api = { rng, C, add, sub, mul, div, csqrt, cexp, abs2, MAT, stackR, reflectance, psiDelta, zazLayers, WL, spectrum, modelFilm, paramNames, lmFit, measure, xrr, xrrCurve, zazXrrLayers, xdelta, XMAT, xrf, gpcFactor, aldMean, aldSite, polarSites, PLANS, coverageProfile, jLeak, J_SHORT, THICK_DEFAULTS, clone, pipeline, isNominal, runRules, ewma, meanSd, cpk, grr, deming, deltaSigma };
  root.DMS = root.DMS || {};
  root.DMS.thick = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
