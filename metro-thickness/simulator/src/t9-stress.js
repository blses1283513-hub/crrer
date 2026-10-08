/* DRAM Thickness Metro — T9 thin-film stress: before/after wafer-curvature scans, Stoney equation,
   sign convention (tensile +, compressive −), thermal vs intrinsic, bow, and the overlay link. */
(function (root) {
  'use strict';
  const D = root.DMS;
  // film presets: intrinsic stress (MPa), biaxial modulus (GPa), CTE (ppm/K), deposition T (°C). Ranges are typical; values illustrative.
  const FILMS = {
    pesin: { zh: 'PECVD SiN（電容支撐層）', s: -300, M: 200, a: 2.3, T: 400, src: 'PECVD SiN 可由製程調成壓應力或拉應力（Nistala 2017；Picciotto 2009）' },
    lpsin: { zh: 'LPCVD Si₃N₄', s: 1000, M: 290, a: 3.2, T: 780, src: 'LPCVD 氮化矽多為高拉應力（Laconte 2004 等）' },
    teos: { zh: 'PECVD SiO₂（TEOS）', s: -150, M: 85, a: 0.5, T: 400, src: '示意：PECVD 氧化層多為壓應力' },
    tin: { zh: 'TiN 電極', s: -1500, M: 400, a: 9.4, T: 450, src: '示意：濺鍍 TiN 常為高壓應力，依離子轟擊而定' },
    zro2: { zh: 'ZrO₂（晶化後）', s: 400, M: 230, a: 10, T: 300, src: '示意：晶化體積收縮使應力往拉應力移動' },
  };
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui, X = D.ext;
    const filmSeg = V.seg(Object.entries(FILMS).map(([k, f]) => [k, f.zh]), 'pesin', (k) => S.setExt({ stress: { film: k, s: FILMS[k].s } }), '膜');
    const K = [
      ['s', '本質應力（拉 +／壓 −）', 'intrinsic stress', 'MPa', -2000, 2000, 10],
      ['tf', '膜厚', 'film thickness', 'nm', 20, 2000, 5],
      ['ts', '基板厚度', 'substrate thickness', 'µm', 700, 800, 1],
      ['pre', '來料晶圓翹曲（沉積前）', 'incoming bow', 'µm', -60, 60, 1],
    ];
    const sl = {};
    K.forEach(([k, zh, en, unit, mn, mx, st]) => { sl[k] = V.knob({ key: k, zh, en, unit, min: mn, max: mx, step: st, tier: k === 'ts' ? 'green' : 'red', src: k === 'ts' ? 'SEMI 300 mm 晶圓 775 µm' : '示意' }, 0, (v) => S.setExt({ stress: { [k]: v } })); });
    const preSeg = V.seg([[true, '沉積前後各量一次'], [false, '只量沉積後']], true, (k) => S.setExt({ stress: { usePre: k === 'true' } }), '量測方式');
    const scanBox = u.el('div'), kv = u.el('div'), cartoon = u.el('div'), thBox = u.el('div'), link = u.el('div', { class: 'info' });
    host.append(
      u.el('h2', { id: 'h-t9' }, 'T9 薄膜應力 ', u.el('span', { class: 'en' }, 'thin-film stress · wafer curvature · Stoney')),
      u.el('p', { class: 'sub' }, '應力不是在量測墊上量，而是量整片晶圓的曲率。沉積前掃一次、沉積後再掃一次，兩次曲率相減再代入 Stoney 方程。慣例：拉應力（tensile）為正，晶圓往膜面凹（碗形）；壓應力（compressive）為負，晶圓往膜面凸（拱形）。'),
      u.el('div', { class: 'row' }, filmSeg),
      u.el('div', { class: 'grid2' }, u.el('div', {}, ...K.map(([k]) => sl[k]), u.el('div', { class: 'row' }, preSeg)), u.el('div', {}, cartoon, kv)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' }, u.el('div', {}, u.el('h4', { class: 'grp' }, '雷射掃描高度（沿直徑）'), scanBox), u.el('div', {}, u.el('h4', { class: 'grp' }, '熱應力 vs 本質應力'), thBox, link)));

    function draw(s) {
      const e = s.ext.stress, f = FILMS[e.film];
      filmSeg.sync(e.film); preSeg.sync(e.usePre);
      K.forEach(([k]) => { if (!sl[k].contains(document.activeElement)) sl[k].sync(e[k]); });
      const sTh = X.thermalStress(f.M, f.a, f.T);
      const sTot = e.s + sTh;
      const kFilm = X.kappaFromStress(sTot, e.ts, e.tf);
      const k0 = (8 * e.pre * 1e-6) / 0.09; // incoming bow -> curvature
      const pre = X.scan(0, { k0, tilt: 2e-5 }, 11, 0.05), post = X.scan(kFilm, { k0, tilt: 2e-5 }, 12, 0.05);
      const kPre = X.fitCurvature(pre), kPost = X.fitCurvature(post);
      const dk = e.usePre ? kPost - kPre : kPost;
      const sMeas = X.stoneyStress(dk, e.ts, e.tf);
      const err = sMeas - sTot;
      scanBox.replaceChildren(V.chart([{ pts: pre, color: 'var(--text-dim)', label: '沉積前', dots: true, width: 1, r: 2 }, { pts: post, color: 'var(--accent)', label: '沉積後', dots: true, width: 1, r: 2 }],
        { h: 220, xLabel: '位置 x (mm)', yLabel: '高度 (µm)', yFmt: (v) => v.toFixed(0), aria: '沉積前後的晶圓高度掃描' }),
        u.el('p', { class: 'note' }, `擬合 z = a + bx + cx²，曲率 κ = 2c。沉積前 κ = ${(kPre * 1000).toFixed(3)}，沉積後 κ = ${(kPost * 1000).toFixed(3)} (1/km)。`));
      const kind = sMeas >= 0 ? '拉應力 tensile（+）' : '壓應力 compressive（−）';
      const bow = X.bowUm(kFilm + k0);
      kv.replaceChildren(V.kvGrid([['量測應力 σ', `${sMeas.toFixed(0)} MPa`, Math.abs(err) > 0.1 * Math.max(Math.abs(sTot), 50) ? 'badtxt' : ''], ['真實總應力', `${sTot.toFixed(0)} MPa`], ['類型', kind], ['曲率半徑 R', `${Math.abs(1 / kFilm) > 1e5 ? '∞' : (1 / kFilm).toFixed(0)} m`], ['沉積後晶圓翹曲（300 mm）', `${bow.toFixed(1)} µm`, Math.abs(bow) > 50 ? 'badtxt' : ''], ['只量一次的誤差', `${(X.stoneyStress(kPost, e.ts, e.tf) - sTot).toFixed(0)} MPa`]]),
        u.el('p', { class: 'note' }, `σ = [E/(1−ν)]_Si · t_s² / (6 t_f) · Δ(1/R)，Si(001) 雙軸模數 180.5 GPa（Janssen 2009）。σ ∝ 1/t_f：膜厚量錯 5%，應力就錯 5%——膜厚與應力要一起量。${e.usePre ? '' : ' 目前只量沉積後：來料翹曲被當成膜應力。'}`));
      // cartoon of wafer shape
      const c = u.svg('svg', { viewBox: '0 0 320 110', class: 'svg-small', role: 'img', 'aria-label': `晶圓形狀：${kind}` });
      const amp = Math.max(-28, Math.min(28, -bow / 3));
      c.append(u.svg('path', { d: `M20,${60 + amp} Q160,${60 - amp} 300,${60 + amp} L300,${74 + amp} Q160,${74 - amp} 20,${74 + amp} Z`, fill: 'var(--m-si)', stroke: 'var(--m-si-ln)' }));
      c.append(u.svg('path', { d: `M20,${60 + amp} Q160,${60 - amp} 300,${60 + amp}`, fill: 'none', stroke: sMeas >= 0 ? 'var(--leak)' : 'var(--accent)', 'stroke-width': 5 }));
      c.append(u.svg('text', { x: 160, y: 104, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--text-dim)' }, sMeas >= 0 ? '拉應力：膜想收縮 → 晶圓往膜面凹（誇大顯示）' : '壓應力：膜想伸長 → 晶圓往膜面凸（誇大顯示）'));
      cartoon.replaceChildren(c);
      // thermal vs intrinsic
      const temps = []; for (let T0 = 100; T0 <= 900; T0 += 20) temps.push([T0, X.thermalStress(f.M, f.a, T0)]);
      thBox.replaceChildren(V.chart([{ pts: temps, color: 'var(--leak)', label: '熱應力 σ_th（降溫到 25 °C）' }, { pts: [[f.T, sTh]], color: 'var(--sig)', dotsOnly: true, r: 5, label: '此膜的沉積溫度' }],
        { h: 200, xLabel: '沉積溫度 (°C)', yLabel: 'σ_th (MPa)', hlines: [{ y: 0, color: 'var(--text-faint)' }], yFmt: (v) => v.toFixed(0), aria: '熱應力對沉積溫度' }),
        u.el('p', { class: 'note' }, `σ_th = M_f (α_f − α_Si) ΔT（膜熱膨脹係數大於 Si → 降溫後拉應力）。${f.zh}：α_f ${f.a} ppm/K，M_f ${f.M} GPa → σ_th ${sTh.toFixed(0)} MPa。總應力 = 本質（成長時的微結構、離子轟擊、H 含量）＋ 熱應力。來源：${f.src}。`));
      const mag = X.bowMagPpm(kFilm + k0, e.ts);
      link.textContent = `連到疊對（T7）：翹曲的晶圓被吸盤吸平時，表面產生 ≈ (t_s/2)·κ 的應變 → 晶圓放大量約 ${mag.toFixed(2)} ppm（150 mm 半徑處 ${(mag * 150).toFixed(0)} nm）。T7 的「納入應力」開啟時會加進晶圓放大項。`;
    }
    S.subscribe(draw);
  }
  root.DMS.t9 = { mount, FILMS };
})(typeof globalThis !== 'undefined' ? globalThis : this);
