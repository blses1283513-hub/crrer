const T = require('../src/thick-engine.js'); const X = require('../src/ext-engine.js');
const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) process.exitCode = 1; };
// Stoney vs Wolfram: 100 nm, -1 GPa -> R = 180.69 m
const k = X.kappaFromStress(-1000, 775, 100); ok(Math.abs(1 / Math.abs(k) - 180.688) < 0.01, `R = ${(1 / Math.abs(k)).toFixed(3)} m`);
ok(Math.abs(X.stoneyStress(1 / 50, 775, 100) - 3613.76) < 0.1, `sigma(R=50m) = ${X.stoneyStress(1 / 50, 775, 100).toFixed(2)} MPa`);
ok(Math.abs(X.bowUm(1 / 50) - 225) < 1e-6, `bow ${X.bowUm(1 / 50)} um`);
// curvature fit recovers kappa with incoming bow subtracted
const pre = X.scan(0, { k0: 2e-3, tilt: 1e-4 }, 1, 0.05), post = X.scan(k, { k0: 2e-3, tilt: 1e-4 }, 2, 0.05);
const dk = X.fitCurvature(post) - X.fitCurvature(pre); ok(Math.abs(X.stoneyStress(dk, 775, 100) + 1000) < 30, `before/after stress ${X.stoneyStress(dk, 775, 100).toFixed(1)} MPa (true -1000)`);
console.log('   post-only (no pre-scan) stress', X.stoneyStress(X.fitCurvature(post), 775, 100).toFixed(1));
// EMA vs Wolfram TE 2.8332, TM 1.3695 for f=0.5, n=3.88
const te = X.emaTE(0.5, T.C(3.88), T.C(1)), tm = X.emaTM(0.5, T.C(3.88), T.C(1));
ok(Math.abs(te[0] - 2.83323) < 1e-4 && Math.abs(tm[0] - 1.36946) < 1e-4, `EMA TE ${te[0].toFixed(4)} TM ${tm[0].toFixed(4)}`);
// overlay: fit recovers injected terms; Wolfram dx check 17 nm
const p = { Tx: 2, Ty: -1, Mwx: 0.2, Mwy: 0.15, Rw: 0.1, Mfx: 1.0, Mfy: -0.5, Rf: 0.3, noise: 0.5, tis: 0 };
const f = X.overlayFit(X.overlayVectors(p, 3)); console.log('   overlay fit', JSON.stringify(Object.fromEntries(Object.entries(f.c).map(([a, b]) => [a, +b.toFixed(3)]))), 'resid m3s', f.resid.x.m3s.toFixed(2), f.resid.y.m3s.toFixed(2));
ok(Math.abs(f.c.Mwx - 0.2) < 0.01 && Math.abs(f.c.Rf - 0.3) < 0.05, 'overlay terms recovered');
// GOF: correct vs missing-IL model
const truth = { tZ: 6, tA: 0.5, tIL: 0.5, fT: 0.9, amc: 0 }, good = { floatTA: false, floatN: false, includeIL: true, ilFixed: 0.5, libFT: 0.9, tAfixed: 0.5 };
const mg = T.measure(truth, good, { psi: 0.01, delta: 0.02 }, 7, 1), mb = T.measure(truth, { ...good, includeIL: false }, { psi: 0.01, delta: 0.02 }, 7, 1);
console.log('   GOF good', X.gof(mg.one.data, mg.model).toFixed(6), 'GOF IL-missing', X.gof(mb.one.data, mb.model).toFixed(6), 'chi2nu', mb.sys.chi2nu.toFixed(0));
// sensitivity / correlation across thickness
for (const d of [2, 10, 50, 100, 300, 1000, 3000]) { const s = X.sensitivity(d), c = X.corrDN(d); console.log(`   d ${d} nm: R-sens ${s.rmsR.toFixed(2)} SE-sens ${s.rmsD.toFixed(2)} fringes ${s.fringes.toFixed(2)} corr(d,n) ${c.corr.toFixed(3)}`); }
const ff = X.fftThickness(2500); ok(Math.abs(ff.d - 2500) < 60, `FFT thickness ${ff.d.toFixed(0)} nm (true 2500, resolution ${ff.resolution.toFixed(0)} nm)`);
// CD-SEM: threshold sweep
const g = { topCD: 30, h: 60, swa: 86, beam: 2, frames: 16, hole: false }; const ls = X.linescan(g, 4);
console.log('   CD vs threshold', [0.2, 0.5, 0.8].map((t) => X.cdThreshold(ls, t).toFixed(1)).join(' / '), 'true top 30 bottom', (30 + 2 * 60 / Math.tan(86 * Math.PI / 180)).toFixed(1));
// OCD fit
const g0 = { pitch: 80, topCD: 30, depth: 120, swa: 87, hm: 0 }; const meas = X.ocdSpectra({ ...g0, depth: 126, topCD: 31.5, swa: 86 });
const t0 = Date.now(); const of = X.ocdFit(meas, g0, 0.002); console.log('   OCD fit', JSON.stringify(Object.fromEntries(Object.entries(of.fit).map(([a, b]) => [a, +b.toFixed(2)]))), 'corr', of.corr.map((r) => r.map((v) => v.toFixed(2)).join(',')).join(' | '), `${Date.now() - t0} ms`);
ok(Math.abs(of.fit.depth - 126) < 0.5 && Math.abs(of.fit.topCD - 31.5) < 0.5, 'OCD recovers depth and CD');
