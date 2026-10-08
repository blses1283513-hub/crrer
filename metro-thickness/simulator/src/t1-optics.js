/* DRAM Thickness Metro — T1 optical measurement lab: SE spectra, recipe model, fit, residuals,
   parameter correlation, split tracking, XRR cross-check, XRF TiN card. */
(function (root) {
  'use strict';
  const D = root.DMS;

  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, T = D.thick, V = D.tui;
    const G = 'green', Y = 'yellow', O = 'orange', R = 'red';

    // ---- controls: true film ----
    const sl = {};
    const film = [
      { key: 'tZ_nm', zh: 'ZrO₂ 總厚（設計）', en: 'ZrO₂ total', unit: 'nm', min: 4, max: 8, step: 0.05, tier: O, src: 'TechInsights（通用）high-k 6–7 nm', set: (v) => S.setParam('tZ_nm', v), get: (s) => s.params.tZ_nm },
      { key: 'tA_nm', zh: 'Al₂O₃ 夾層', en: 'Al₂O₃ insert', unit: 'nm', min: 0, max: 1.5, step: 0.05, tier: R, src: '示意；ZAZ 結構', set: (v) => S.setParam('tA_nm', v), get: (s) => s.params.tA_nm },
      { key: 'fT', zh: '四方相比例（真實膜）', en: 'tetragonal fraction', unit: '', min: 0, max: 1, step: 0.01, tier: O, src: '晶化後 n 上升（Yoon 2011）；n 的變化幅度為示意', set: (v) => S.setParam('fT', v), get: (s) => s.params.fT },
      { key: 'tIL', zh: 'TiOx 介面層（真實）', en: 'TiOx interfacial layer', unit: 'nm', min: 0, max: 1.5, step: 0.05, tier: O, src: 'O₃ 製程在 TiN 上形成較厚 TiOx（Jang 2024）；數值示意', set: (v) => S.setThick({ film: { tIL: v } }), get: (s) => s.thick.film.tIL },
      { key: 'amc', zh: '監控片表面吸附層', en: 'AMC on monitor', unit: 'nm', min: 0, max: 0.6, step: 0.01, tier: R, src: '示意；有機物／水氣吸附，見書 §17', set: (v) => S.setThick({ film: { amc: v } }), get: (s) => s.thick.film.amc },
    ];
    const filmBox = u.el('div', {}, u.el('h4', { class: 'grp' }, '真實的膜 true film（監控片）'), ...film.map((f) => (sl[f.key] = V.knob(f, f.get(S.snapshot()), (v) => f.set(v)))));

    // ---- controls: recipe model ----
    const cfgBox = u.el('div', {}, u.el('h4', { class: 'grp' }, '配方模型 recipe model'));
    const ilSeg = V.seg([[true, '含 TiOx 介面層（固定 0.5 nm）'], [false, '省略介面層']], true, (k) => S.setT1({ includeIL: k === 'true' }), '介面層');
    const taSeg = V.seg([[false, 'Al₂O₃ 固定'], [true, 'Al₂O₃ 也擬合']], false, (k) => S.setT1({ floatTA: k === 'true' }), 'Al₂O₃');
    const nSeg = V.seg([[false, 'n 固定（資料庫）'], [true, 'n 也擬合']], false, (k) => S.setT1({ floatN: k === 'true' }), 'n');
    const libSl = V.knob({ key: 'libFT', zh: '資料庫 n 對應的四方相比例', en: 'library assumes fT', unit: '', min: 0, max: 1, step: 0.01, tier: R, src: '示意：n/k 資料庫在某一退火條件下校準' }, 0.9, (v) => S.setT1({ libFT: v }));
    const noiseSl = V.knob({ key: 'noise', zh: '光譜雜訊倍率', en: 'spectral noise ×', unit: '×', min: 0.2, max: 10, step: 0.1, tier: R, src: '基準 σΨ 0.01°、σΔ 0.02°（示意）' }, 1, (v) => S.setT1({ noise: v }));
    cfgBox.append(u.el('div', { class: 'row' }, ilSeg), u.el('div', { class: 'row' }, taSeg, nSeg), libSl, noiseSl);

    // ---- outputs ----
    const psiBox = u.el('div'), delBox = u.el('div'), resBox = u.el('div'), corrBox = u.el('div'), splitBox = u.el('div'), xrrBox = u.el('div');
    const res = u.el('div'), xrrKv = u.el('div'), flag = u.el('div', { class: 'warn', hidden: true });
    let xrrNoAl = false;
    const xrrSeg = V.seg([[false, 'ZAZ（有 Al₂O₃）'], [true, 'ZrO₂ 直接在 TiN 上']], false, (k) => { xrrNoAl = k === 'true'; drawXrr(last); }, 'XRR 堆疊');

    // XRF card
    const xrfOut = u.el('div');
    let xrfTSl = null, xrfRSl = null;
    const xrfBox = u.el('div', { class: 'card' }, u.el('h3', {}, 'XRF：TiN 下電極 ', u.el('span', { class: 'en' }, 'mass thickness, not thickness')),
      (xrfTSl = V.knob({ key: 'xt', zh: 'TiN 真實厚度', en: 'TiN thickness', unit: 'nm', min: 5, max: 20, step: 0.1, tier: R, src: '示意' }, 10, (v) => S.setT1({ xrfT: v }))),
      (xrfRSl = V.knob({ key: 'xr', zh: 'TiN 真實密度', en: 'TiN density', unit: 'g/cm³', min: 4.4, max: 5.6, step: 0.02, tier: O, src: '塊材 5.4；PVD/ALD 薄膜常較低（示意範圍）' }, 5.4, (v) => S.setT1({ xrfRho: v }))),
      xrfOut,
      u.el('p', { class: 'note' }, 'XRF 量到的是單位面積的 Ti 原子數（ρ·t）。配方用固定校正密度 5.4 g/cm³ 換算厚度，所以密度變低會被讀成「變薄」。要分開密度與厚度，需要 XRR。'));
    function drawXrf(s) {
      const xrfT = s.t1.xrfT, xrfRho = s.t1.xrfRho;
      if (!xrfTSl.contains(document.activeElement)) xrfTSl.sync(xrfT);
      if (!xrfRSl.contains(document.activeElement)) xrfRSl.sync(xrfRho);
      const r = T.xrf(xrfT, xrfRho);
      xrfOut.replaceChildren(V.kvGrid([['XRF 讀值 reported', `${r.reported.toFixed(2)} nm`], ['真實 true', `${xrfT.toFixed(2)} nm`], ['偏差 bias', `${(r.reported - xrfT >= 0 ? '+' : '')}${(r.reported - xrfT).toFixed(2)} nm`, Math.abs(r.reported - xrfT) > 0.3 ? 'badtxt' : '']]));
    }

    host.append(
      u.el('h2', { id: 'h-t1' }, 'T1 光學量測實驗室 ', u.el('span', { class: 'en' }, 'optical measurement lab · SE + XRR + XRF')),
      u.el('p', { class: 'sub' }, '在 TiN 監控片上量 ZAZ（ZrO₂/Al₂O₃/ZrO₂）介電層。機台量到的是 Ψ、Δ 光譜，不是厚度；厚度是配方模型擬合出來的。改變真實的膜或配方的假設，看擬合結果、殘差與參數相關性怎麼變。這裡算出的量測偏差會送進上方鏈條，若開啟 T3 的 APC，偏差會變成真實膜厚的誤差。'),
      u.el('div', { class: 'grid2' }, filmBox, cfgBox),
      flag,
      u.el('h4', { class: 'grp', style: 'margin-top:14px' }, '擬合結果 fit result'), res,
      u.el('div', { class: 'grid2', style: 'margin-top:10px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, 'Ψ 光譜（65°）'), psiBox),
        u.el('div', {}, u.el('h4', { class: 'grp' }, 'Δ 光譜（65°）'), delBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, '殘差 residual（量測 − 模型，以 σ 為單位）'), resBox),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '重複量測散佈 repeat fits'), corrBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, '分批追蹤 split tracking（A5）'), splitBox,
          u.el('p', { class: 'note' }, '製程刻意改變 ZrO₂ 厚度 ±0.4 nm，配方回報的變化量應等於真實變化量（斜率 1）。模型錯誤常常在單點看不出來，在分批斜率上才露出來。')),
        u.el('div', {}, u.el('div', { class: 'row' }, u.el('h4', { class: 'grp', style: 'margin:0' }, 'XRR 參考量測 cross-check'), xrrSeg), xrrBox, xrrKv)),
      u.el('div', { class: 'grid2', style: 'margin-top:12px' }, xrfBox,
        u.el('div', { class: 'card' }, u.el('h3', {}, '為什麼要 XRR 交叉驗證'),
          u.el('p', { class: 'note' }, 'XRR 的 Kiessig 條紋週期 Δθ ≈ λ/(2d) 幾乎不依賴光學常數，所以適合當參考量測。但 ZrO₂ 與 TiN 的電子密度幾乎相同（臨界角都約 0.33°），ZrO₂ 直接長在 TiN 上時，底部介面幾乎沒有對比，條紋很弱；ZAZ 中的 Al₂O₃（臨界角約 0.25°）反而提供了對比。切換上方按鈕比較。'),
          u.el('p', { class: 'note' }, 'SE 與 XRR 的總厚度差距超過 0.15 nm 時，先懷疑模型（介面層、n/k），不是機台。'))));

    // ---- compute ----
    let last = null, lastKey = '', timer = 0, result = null;
    const NOISE = { psi: 0.01, delta: 0.02 };
    function truthOf(s) { const d = s.designParams; return { tZ: d.tZ_nm, tA: d.tA_nm, tIL: s.thick.film.tIL, fT: d.fT, amc: s.thick.film.amc }; }
    function cfgOf(s) { return { includeIL: s.t1.includeIL, ilFixed: 0.5, floatTA: s.t1.floatTA, floatN: s.t1.floatN, libFT: s.t1.libFT, tAfixed: s.params.tA_nm }; }
    function compute(s) {
      const truth = truthOf(s), cfg = cfgOf(s), nz = { psi: NOISE.psi * s.t1.noise, delta: NOISE.delta * s.t1.noise };
      const m = T.measure(truth, cfg, nz, 11, 24);
      const split = [-0.4, -0.2, 0, 0.2, 0.4].map((dt) => {
        const tr = { ...truth, tZ: truth.tZ + dt };
        const f = T.lmFit(cfg, T.spectrum(tr), [nz.psi, nz.delta], [tr.tZ + 0.2, ...(cfg.floatTA ? [cfg.tAfixed] : []), ...(cfg.floatN ? [0] : [])]);
        return [dt, f.x[0] - m.sys.x[0]];
      });
      const n = split.length, mx = split.reduce((a, p) => a + p[0], 0) / n, my = split.reduce((a, p) => a + p[1], 0) / n;
      const slope = split.reduce((a, p) => a + (p[0] - mx) * (p[1] - my), 0) / split.reduce((a, p) => a + (p[0] - mx) ** 2, 0);
      return { truth, cfg, nz, m, split, slope };
    }
    function render(s) {
      last = s;
      for (const f of film) if (!sl[f.key].contains(document.activeElement)) sl[f.key].sync(f.get(s));
      ilSeg.sync(s.t1.includeIL); taSeg.sync(s.t1.floatTA); nSeg.sync(s.t1.floatN);
      if (!libSl.contains(document.activeElement)) libSl.sync(s.t1.libFT);
      if (!noiseSl.contains(document.activeElement)) noiseSl.sync(s.t1.noise);
      drawXrf(s);
      const key = JSON.stringify([truthOf(s), cfgOf(s), s.t1.noise]);
      if (key !== lastKey) {
        lastKey = key; clearTimeout(timer);
        timer = setTimeout(() => { result = compute(last); draw(result, last); S.setModelBias(result.m.sys.x[0] - result.truth.tZ); }, result ? 60 : 0);
      }
    }
    function draw(r, s) {
      const { m, truth, cfg } = r;
      const names = m.sys.names;
      const bias = m.sys.x[0] - truth.tZ;
      const chi = m.sys.chi2nu;
      const chiKind = chi < 2 ? 'good' : chi < 20 ? 'marginal' : 'reject';
      const pairs = [['ZrO₂ 擬合值 fitted', `${m.mean[0].toFixed(3)} ± ${m.sd[0].toFixed(3)} nm`], ['真實值 true', `${truth.tZ.toFixed(3)} nm`],
        ['系統偏差 bias', `${bias >= 0 ? '+' : ''}${bias.toFixed(3)} nm`, Math.abs(bias) > 0.05 ? 'badtxt' : 'goodtxt'], ['重複性 1σ', `${(m.sd[0] * 1000).toFixed(1)} pm`]];
      if (cfg.floatTA) pairs.push(['Al₂O₃ 擬合', `${m.mean[1].toFixed(3)} ± ${m.sd[1].toFixed(3)} nm`], ['corr(t_Z, t_A)', m.sys.corr[0][1].toFixed(3), Math.abs(m.sys.corr[0][1]) > 0.9 ? 'badtxt' : '']);
      if (cfg.floatN) { const j = names.indexOf('Δn'); pairs.push(['Δn 擬合', m.mean[j].toFixed(4)], ['corr(t_Z, n)', m.sys.corr[0][j].toFixed(3), Math.abs(m.sys.corr[0][j]) > 0.9 ? 'badtxt' : '']); }
      const gofV = D.ext.gof(m.one.data, m.model), gofK = D.ext.gofBand(gofV);
      r.gof = gofV;
      res.replaceChildren(V.kvGrid(pairs), u.el('div', { class: 'row' }, u.el('span', { class: 'note' }, 'GOF（≈1 完美、≥0.95 可接受、<0.8 不吻合）'), V.chip(gofV.toFixed(4), gofK),
        u.el('span', { class: 'note' }, 'χ²ν（理想 ≈ 1）'), V.chip(chi.toFixed(chi < 10 ? 2 : 0), chiKind),
        u.el('span', { class: 'note' }, gofV >= 0.95 && chi > 20 ? `GOF ${gofV.toFixed(4)} 看起來「合格」，但 χ²ν = ${chi.toFixed(0)}：GOF 是對光譜總變化的比例，光譜本身變化很大時，系統性殘差也只佔一點點。GOF 合格不代表模型對——要一起看 χ²ν、殘差結構與 XRR。` : chi > 20 ? '模型無法解釋資料：殘差有結構，先查堆疊與 n/k。' : chi > 2 ? '殘差略有結構。' : '殘差接近純雜訊；但好的擬合不代表模型正確，看 XRR 與分批斜率。')));
      const msgs = [];
      if (!cfg.includeIL && truth.tIL > 0.05) msgs.push(`模型省略了 ${truth.tIL.toFixed(2)} nm TiOx 介面層：擬合把它吸收進 ZrO₂，讀值偏厚 ${bias.toFixed(2)} nm。`);
      if (Math.abs(truth.fT - cfg.libFT) > 0.05) msgs.push(`真實膜的晶相（f_t ${truth.fT.toFixed(2)}）與 n/k 資料庫（${cfg.libFT.toFixed(2)}）不一致：n 錯，厚度跟著錯。`);
      if (truth.amc > 0.02) msgs.push(`監控片上有 ${truth.amc.toFixed(2)} nm 吸附層：所有機台一起偏厚，看起來像製程漂移。`);
      flag.hidden = !msgs.length; flag.replaceChildren(...msgs.map((t) => u.el('div', {}, t)));

      const wl = T.WL;
      const data = m.one.data;
      V.chart && psiBox.replaceChildren(V.chart([{ pts: wl.map((l, i) => [l, data[i][0]]), color: 'var(--text-dim)', dotsOnly: true, r: 2, label: '量測' }, { pts: wl.map((l, i) => [l, m.model[i][0]]), color: 'var(--accent)', label: '模型' }], { h: 210, xLabel: '波長 nm', yLabel: 'Ψ (°)', yFmt: (v) => v.toFixed(1), aria: 'Psi 光譜：量測點與模型曲線' }));
      delBox.replaceChildren(V.chart([{ pts: wl.map((l, i) => [l, data[i][1]]), color: 'var(--text-dim)', dotsOnly: true, r: 2, label: '量測' }, { pts: wl.map((l, i) => [l, m.model[i][1]]), color: 'var(--accent)', label: '模型' }], { h: 210, xLabel: '波長 nm', yLabel: 'Δ (°)', yFmt: (v) => v.toFixed(0), aria: 'Delta 光譜：量測點與模型曲線' }));
      const rr = m.one.resid;
      resBox.replaceChildren(V.chart([{ pts: wl.map((l, i) => [l, rr[2 * i]]), color: 'var(--accent)', label: 'Ψ' }, { pts: wl.map((l, i) => [l, rr[2 * i + 1]]), color: 'var(--leak)', label: 'Δ' }],
        { h: 190, xLabel: '波長 nm', yLabel: '殘差 / σ', hlines: [{ y: 3, color: 'var(--text-faint)' }, { y: -3, color: 'var(--text-faint)' }], yFmt: (v) => v.toFixed(0), aria: '殘差光譜' }));
      if (cfg.floatTA || cfg.floatN) {
        const j = cfg.floatTA ? 1 : names.indexOf('Δn');
        const tv = cfg.floatTA ? truth.tA : 0;
        corrBox.replaceChildren(V.chart([{ pts: m.reps.map((x) => [x[0], x[j]]), color: 'var(--accent)', dotsOnly: true, r: 3, label: '每次重複量測' }, { pts: [[truth.tZ, tv]], color: 'var(--sig)', dotsOnly: true, r: 5, label: '真實' }],
          { h: 190, xLabel: 't_Z (nm)', yLabel: cfg.floatTA ? 't_A (nm)' : 'Δn', xFmt: (v) => v.toFixed(3), yFmt: (v) => v.toFixed(3), aria: '重複擬合的參數散佈' }),
          u.el('p', { class: 'note' }, `點沿斜線排列＝兩個參數互相補償（相關係數 ${m.sys.corr[0][j].toFixed(2)}）。單看 t_Z 的 σ 會低估真正的不確定度。`));
      } else {
        const rng0 = Math.max(...m.reps.map((x) => x[0])) - Math.min(...m.reps.map((x) => x[0]));
        const dig = Math.min(6, Math.max(3, Math.ceil(-Math.log10(rng0 || 1e-3)) + 1));
        corrBox.replaceChildren(V.chart([{ pts: m.reps.map((x, i) => [i + 1, x[0]]), color: 'var(--accent)', dots: true, width: 1, label: '重複量測 t_Z' }],
          { h: 190, left: 74, xLabel: '重複次數', yLabel: 't_Z (nm)', hlines: [{ y: truth.tZ, color: 'var(--sig)' }], yFmt: (v) => v.toFixed(dig), aria: '重複量測序列' }),
          u.el('p', { class: 'note' }, '只擬合 t_Z：重複性很好。在右上切換「也擬合 Al₂O₃／n」看相關性。'));
      }
      const sp = r.split;
      splitBox.replaceChildren(V.chart([{ pts: sp.map((p) => [p[0], p[0]]), color: 'var(--text-faint)', dash: '4 4', label: '理想 slope 1' }, { pts: sp, color: 'var(--accent)', dots: true, label: '配方回報' }],
        { h: 190, xLabel: '真實變化 Δt_Z (nm)', yLabel: '回報變化 (nm)', xFmt: (v) => v.toFixed(1), yFmt: (v) => v.toFixed(1), aria: '分批追蹤' }),
        V.kvGrid([['斜率 slope', r.slope.toFixed(3), Math.abs(r.slope - 1) > 0.03 ? 'badtxt' : 'goodtxt']]));
      drawXrr(s);
    }
    function drawXrr(s) {
      if (!result) return;
      const truth = result.truth;
      const c = T.xrrCurve(truth, { noAl: xrrNoAl });
      xrrBox.replaceChildren(V.chart([{ pts: c.th.map((t, i) => [t, c.R[i]]), color: 'var(--accent)', width: 1.6, label: xrrNoAl ? 'ZrO₂/TiN' : 'ZAZ/TiOx/TiN' }],
        { h: 200, logY: true, xLabel: '2θ/2 = θ (°)', yLabel: '反射率 R', vlines: [{ x: 0.33, label: 'θc' }], xFmt: (v) => v.toFixed(1), aria: 'XRR 反射率曲線' }));
      const R = T.rng(5);
      const xrrTot = truth.tZ + truth.tA + truth.tIL + truth.amc + R.n() * 0.03;
      const seTot = result.m.sys.x[0] + (result.cfg.floatTA ? result.m.sys.x[1] : result.cfg.tAfixed) + (result.cfg.includeIL ? 0.5 : 0);
      const diff = seTot - xrrTot;
      D.t1Last = { bias: result.m.sys.x[0] - truth.tZ, sd: result.m.sd[0], chi: result.m.sys.chi2nu, slope: result.slope, seXrr: diff, gof: result.gof };
      document.dispatchEvent(new CustomEvent('dms:results'));
      xrrKv.replaceChildren(V.kvGrid([['XRR 總厚 total', `${xrrTot.toFixed(2)} nm`], ['SE 模型總厚', `${seTot.toFixed(2)} nm`], ['差距 SE − XRR', `${diff >= 0 ? '+' : ''}${diff.toFixed(2)} nm`, Math.abs(diff) > 0.15 ? 'badtxt' : 'goodtxt']]),
        u.el('p', { class: 'note' }, 'XRR 讀值以「真實總厚 + 0.03 nm 雜訊」模擬（條紋週期近乎與模型無關）；曲線本身由 Parratt 遞迴計算。'));
    }
    S.subscribe(render);
  }
  root.DMS.t1 = { mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
