/* DRAM Thickness Metro — process-area physics (pure functions): pre/post rate maps and selectivity,
   resist swing curve and etch budget, PVD reflectivity vs roughness, wet contact angle,
   BPSG dopant → wet etch rate, poly dopant → sheet resistance. Values marked illustrative in the UI. */
(function (root) {
  'use strict';
  const T = root.DMS.thick;
  const { C } = T;

  // ---------- pre/post removal (dry etch, CMP, wet) ----------
  // p: { mode, t0 (target film pre, nm), rr (nm/s), time (s), over (overetch fraction), sel (target:stop),
  //      stop0 (stop film pre, nm), dome, edge (% of rr), density (CMP pattern density 0..1), matched, sPre, sPost, other (wet: ER of other film nm/s) }
  function siteRemoval(p, x, y) {
    const R = 150, rho2 = (x * x + y * y) / (R * R), rho = Math.sqrt(rho2);
    const shape = 1 + (p.dome / 100) * (0.5 - rho2) + (p.edge / 100) * Math.exp(-(1 - rho) / 0.06);
    const pre = p.t0 * (1 + ((p.inDome ?? 0.4) / 100) * (0.5 - rho2)); // incoming film shape (centre-thick if > 0)
    const rate = p.rr * shape;
    const tClear = pre / rate;              // time this site needs to clear the target film
    const tTot = p.time;                    // process time actually run
    let post, stopLoss = 0, otherLoss = 0;
    if (p.mode === 'wet') { post = Math.max(pre - rate * tTot, 0); otherLoss = p.other * tTot * shape; }
    else if (tTot <= tClear) post = pre - rate * tTot;
    else { post = 0; stopLoss = (rate / p.sel) * (tTot - tClear); }
    if (p.mode === 'cmp') stopLoss *= 1 + 2.5 * p.density; // dense arrays erode faster (erosion)
    return { pre, post, rate, stopLoss, otherLoss, tClear };
  }
  function removalMap(p, sites, seed) {
    const R = T.rng(seed);
    return sites.map(([x, y]) => {
      const s = siteRemoval(p, x, y);
      const mPre = s.pre + R.n() * p.sPre, mPost = s.post + R.n() * p.sPost;
      const mStopPre = p.stop0 + R.n() * p.sPre, mStopPost = p.stop0 - s.stopLoss + R.n() * p.sPost;
      return { x, y, ...s, mPre, mPost, mStopPre, mStopPost };
    });
  }
  // rate from measurements: matched = same sites pre and post; unmatched = pre map mean vs post on other sites
  function rateStats(rows, p, unmatchedRows) {
    const tUse = p.mode === 'wet' ? p.time : Math.min(p.time, ...rows.map((r) => r.tClear)); // only sites still in the target film give a rate
    const rates = rows.filter((r) => r.post > 0).map((r) => (r.mPre - r.mPost) / p.time);
    const ms = (a) => { const m = a.reduce((s, v) => s + v, 0) / a.length; const sd = Math.sqrt(a.reduce((s, v) => s + (v - m) ** 2, 0) / Math.max(a.length - 1, 1)); return { m, sd }; };
    const r = rates.length >= 3 ? ms(rates) : { m: NaN, sd: NaN };
    let un = NaN;
    if (unmatchedRows) { const a = ms(unmatchedRows.map((q) => q.mPre)).m, b = ms(rows.filter((q) => q.post > 0).map((q) => q.mPost)).m; un = (a - b) / p.time; }
    const stopRates = rows.filter((q) => q.post === 0 && q.tClear < p.time).map((q) => (q.mStopPre - q.mStopPost) / (p.time - q.tClear));
    const stop = stopRates.length ? ms(stopRates).m : NaN;
    return { rate: r.m, rateSd: r.sd, unif: (r.sd / r.m) * 100, unmatched: un, stopRate: stop, selectivity: r.m / stop, tUse };
  }

  // ---------- resist: swing curve and etch budget ----------
  // ArF (193 nm): resist n 1.70+0.02i, organic BARC 1.82+0.34i, Si 0.88+2.78i (illustrative values)
  const LAM_PHOTO = 193;
  const N_RES = C(1.70, 0.02), N_BARC = C(1.82, 0.34), N_SI193 = C(0.88, 2.78);
  function resistR(tRes, tBarc) {
    const L = [{ n: N_RES, d: tRes }]; if (tBarc > 0) L.push({ n: N_BARC, d: tBarc });
    return T.reflectance(LAM_PHOTO, L, N_SI193, 0);
  }
  // energy coupled into the resist ∝ (1 − R); dose-to-size scales as 1/(1 − R); CD responds with a dose latitude slope
  // CD relative to the swing-averaged coupling (150–300 nm), slope: nm CD per % coupled-energy change (illustrative)
  function swingCD(tRes, tBarc, cd0, _unused, slope = 0.25) {
    let e0 = 0, n = 0; for (let t = 150; t <= 300; t += 2) { e0 += 1 - resistR(t, tBarc); n++; } e0 /= n;
    const e = 1 - resistR(tRes, tBarc);
    return cd0 + slope * ((e - e0) / e0) * 100;
  }
  const swingPeriod = () => LAM_PHOTO / (2 * N_RES[0]);
  function resistBudget(r) { // r: { t, film, erFilm (nm/s), selR (film:resist), over }
    const tEtch = (r.film / r.erFilm) * (1 + r.over);
    const used = (r.erFilm / r.selR) * tEtch;
    return { tEtch, used, remain: r.t - used };
  }

  // ---------- PVD reflectivity vs roughness ----------
  // specular reflectance of a rough metal: R = R0 · exp(−(4π σ cos θ / λ)²)  (Davies / Bennett–Porteus)
  function roughR(R0, sigmaNm, lamNm, thetaDeg = 0) { const g = (4 * Math.PI * sigmaNm * Math.cos((thetaDeg * Math.PI) / 180)) / lamNm; return R0 * Math.exp(-(g * g)); }

  // ---------- wet: contact angle ----------
  // Young: cos θ = (γ_sv − γ_sl) / γ_lv ; surface presets and organic pickup after clean (illustrative time constant)
  const SURF = { hf: { zh: 'HF-last Si（H 終端，疏水）', th0: 72 }, ox: { zh: '化學氧化層（SC1 後，親水）', th0: 5 }, sin: { zh: 'SiN 表面', th0: 25 }, tin: { zh: 'TiN（自然氧化）', th0: 35 } };
  function contactAngle(surf, hours) { const th0 = SURF[surf].th0, thMax = 60; return th0 >= thMax ? th0 : th0 + (thMax - th0) * (1 - Math.exp(-hours / 24)); }
  const young = (gsv, gsl, glv = 72.8) => (Math.acos(Math.max(-1, Math.min(1, (gsv - gsl) / glv))) * 180) / Math.PI;

  // ---------- CVD: BPSG dopant ----------
  // wet etch rate in dilute HF rises with P (and B) content; reflow (flow) temperature falls with B+P. Illustrative linear forms.
  function bpsg(Bwt, Pwt) {
    return { erRel: 1 + 0.18 * Pwt + 0.06 * Bwt, flowT: 1000 - 22 * (Bwt + Pwt), ftirBO: 1380, ftirPO: 1330, risk: Bwt + Pwt > 10 ? '過高：吸濕、硼酸鹽結晶析出' : Bwt + Pwt < 5 ? '偏低：回流不足、填洞差' : '正常範圍' };
  }

  // ---------- diffusion: poly dopant → sheet resistance ----------
  // Rs = 1/(q μ N t); μ for heavily doped poly-Si ≈ 30 cm²/V·s (illustrative, grain-boundary limited)
  function polyRs(Ncm3, tNm, mu = 30) { const q = 1.602e-19; const rho = 1 / (q * mu * Ncm3); return rho / (tNm * 1e-7); } // ohm/sq

  const api = { siteRemoval, removalMap, rateStats, LAM_PHOTO, resistR, swingCD, swingPeriod, resistBudget, roughR, SURF, contactAngle, young, bpsg, polyRs };
  root.DMS.proc = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
