const T = require('../src/thick-engine.js');
const ok = (c, m) => { console.log((c ? 'PASS ' : 'FAIL ') + m); if (!c) process.exitCode = 1; };
// 1. reflectance 100 nm SiO2/Si @550 normal vs Wolfram 0.10239 (same n: Si 4.08+0.041i)
const R = T.reflectance(550, [{ n: T.MAT.SiO2(550), d: 100 }], T.C(4.08, 0.041), 0);
ok(Math.abs(R - 0.102393) < 2e-4, `R(100nm SiO2/Si,550) = ${R.toFixed(5)} (Wolfram 0.10239)`);
// 2. Delta sensitivity near 1 nm oxide @633/70deg with n_Si 3.785+0.0187i, Wolfram 0.2998 deg/A
const dl = (d) => T.psiDelta(633, [{ n: T.MAT.SiO2(633), d }], T.C(3.785, 0.0187), 70)[1];
const sens = Math.abs(dl(1.05) - dl(0.95)) / 1.0;
ok(Math.abs(sens - 0.2998) < 0.003, `dDelta/dd = ${sens.toFixed(4)} deg/A (Wolfram 0.2998)`);
// 3. XRR critical angle ZrO2 (Wolfram 0.3296 deg)
const [d] = T.xdelta(T.XMAT.ZrO2); const thc = Math.sqrt(2 * d) * 180 / Math.PI;
ok(Math.abs(thc - 0.3296) < 0.001, `theta_c ZrO2 = ${thc.toFixed(4)} deg`);
// 4. Cpk CI on booklet data (python/wolfram 4.848, CI 1.83–7.86)
const c = T.cpk([20.01, 19.98, 20.04, 20.02, 20.07, 19.99], 19.5, 20.5);
ok(Math.abs(c.cpk - 4.848) < 0.002 && Math.abs(c.lo - 1.831) < 0.01, `Cpk ${c.cpk.toFixed(3)} CI ${c.lo.toFixed(2)}–${c.hi.toFixed(2)}`);
// 5. Deming on exact line
const x = [10, 20, 30, 40, 50], y = x.map((v) => 1.02 * v + 0.1); const dm = T.deming(x, y);
ok(Math.abs(dm.b1 - 1.02) < 1e-9 && Math.abs(dm.b0 - 0.1) < 1e-9, `Deming b1 ${dm.b1} b0 ${dm.b0.toFixed(3)}`);
// 6. GR&R matches python metro_tools on a fixed small dataset
const yy = [[[20.00, 20.01], [20.02, 20.03]], [[20.50, 20.52], [20.53, 20.51]], [[19.80, 19.79], [19.82, 19.83]]];
const g = T.grr(yy, 19, 21); console.log('   GRR', JSON.stringify(g));
// 7. fit recovers truth with correct model (no bias), IL omitted -> bias
const truth = { tZ: 6.0, tA: 0.5, tIL: 0.5, fT: 0.9, amc: 0 };
const good = { floatTA: false, floatN: false, includeIL: true, ilFixed: 0.5, libFT: 0.9, tAfixed: 0.5 };
let t0 = Date.now(); const mg = T.measure(truth, good, { psi: 0.01, delta: 0.02 }, 7, 20);
ok(Math.abs(mg.sys.x[0] - 6.0) < 1e-3, `good model sys tZ ${mg.sys.x[0].toFixed(4)} sd ${mg.sd[0].toFixed(4)} nm (${Date.now() - t0} ms)`);
const bad = { ...good, includeIL: false }; const mb = T.measure(truth, bad, { psi: 0.01, delta: 0.02 }, 7, 5);
console.log(`   IL omitted: tZ ${mb.sys.x[0].toFixed(3)} bias ${(mb.sys.x[0] - 6).toFixed(3)} chi2nu ${mb.sys.chi2nu.toFixed(1)}`);
const wrongN = { ...good, libFT: 0.9 }; const mn = T.measure({ ...truth, fT: 0.5 }, wrongN, { psi: 0.01, delta: 0.02 }, 7, 5);
console.log(`   film fT 0.5 but library 0.9: tZ ${mn.sys.x[0].toFixed(3)} (true 6.000)`);
const flo = { ...good, floatTA: true }; const mf = T.measure(truth, flo, { psi: 0.01, delta: 0.02 }, 7, 30);
console.log(`   float tA: corr(tZ,tA) ${mf.sys.corr[0][1].toFixed(3)} sd tZ ${mf.sd[0].toFixed(4)} sd tA ${mf.sd[1].toFixed(4)}`);
// 8. pipeline nominal: tZeff == tZ, J nominal
const p = { tZ_nm: 6, tA_nm: 0.5, fT: 0.9, kT: 38, kM: 20, kA: 9, H_nm: 1200, D_nm: 25 };
const pl = T.pipeline(p, T.THICK_DEFAULTS);
ok(Math.abs(pl.info.tZeff - 6) < 1e-9, `pipeline nominal tZeff ${pl.info.tZeff} J ${pl.info.Jcell.toExponential(2)} AR ${pl.info.AR} xpd ${pl.info.xpd}`);
const th2 = T.clone(T.THICK_DEFAULTS); th2.ald.exposure = 0.35; const pl2 = T.pipeline(p, th2);
console.log(`   under-dose exposure 0.35: xpd ${pl2.info.xpd.toFixed(1)} bottom ${pl2.info.bottom.toFixed(2)} tZeff ${pl2.info.tZeff.toFixed(3)} J ${pl2.info.Jcell.toExponential(2)}`);
// 9. xrr curve sanity
t0 = Date.now(); const xc = T.xrrCurve(truth); console.log(`   XRR ${xc.R.length} pts in ${Date.now() - t0} ms; R(0.1)=${xc.R[0].toFixed(3)} R(2.0)=${xc.R[190].toExponential(2)}`);
const xf = T.xrf(10, 5.0); console.log(`   XRF TiN 10 nm rho 5.0 -> reported ${xf.reported.toFixed(3)} nm`);
