/* DRAM Thickness Metro — NPI qualification scorecard (A6): auto-filled from T1, T2, T3. */
(function (root) {
  'use strict';
  const D = root.DMS;
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, T = D.thick, V = D.tui;
    let req = 20;
    const grid = u.el('div', { class: 'npi' });
    const reqSl = V.knob({ key: 'wph', zh: '需要的產能', en: 'required throughput', unit: '片/時', min: 10, max: 120, step: 1, tier: 'red', src: '示意：依取樣計畫與產線節拍' }, req, (v) => { req = Math.round(v); draw(); });
    host.append(
      u.el('h2', { id: 'h-npi' }, 'NPI 配方驗證計分卡 ', u.el('span', { class: 'en' }, 'qualification scorecard')),
      u.el('p', { class: 'sub' }, '書 §25 的六個問題，加上 DRAM 專屬的孔內覆蓋。每一列由上面模組的目前結果自動填入；改變 T1 的模型、T3 的機台或 T2 的取樣計畫，看哪一項先失敗。'),
      reqSl, grid);
    function row(name, q, value, pass, how) {
      const kind = pass === null ? 'na' : pass === 'warn' ? 'marginal' : pass ? 'good' : 'reject';
      const txt = pass === null ? '需參考量測' : pass === 'warn' ? '勉強' : pass ? '通過' : '未通過';
      return u.el('div', { class: 'npi-row' }, u.el('div', {}, u.el('b', {}, name), u.el('span', { class: 'note' }, q)), u.el('div', { class: 'mono' }, value), V.chip(txt, kind), u.el('div', { class: 'note' }, how));
    }
    function draw() {
      const s = S.snapshot(), a = D.t1Last, b = D.t3Last;
      if (!a || !b) { grid.replaceChildren(u.el('p', { class: 'note' }, '等待 T1 與 T3 計算…')); return; }
      const spec = b.spec, n = T.PLANS[s.t3.plan].sites.length, wph = 3600 / (20 + 2.5 * n);
      const maxBias = Math.max(...b.toolBias.map(Math.abs));
      const sens = 3 * b.sMeas;
      grid.replaceChildren(
        row('準確度 Accuracy', '與參考量測一致嗎？', `SE − XRR = ${a.seXrr >= 0 ? '+' : ''}${a.seXrr.toFixed(2)} nm`, Math.abs(a.seXrr) <= 0.1, 'XRR 總厚交叉驗證（T1）；目標 ≤ 0.10 nm'),
        row('精密度 Precision', '隨機變異夠小嗎？', `P/T ${(b.pt * 100).toFixed(1)} %`, b.pt < 0.1 ? true : b.pt <= 0.3 ? 'warn' : false, 'GR&R 含機台再現性（T3）；<10% 通過、10–30% 勉強'),
        row('靈敏度 Sensitivity', '能看到最小需要的偏移嗎？', `3σ_meas ${sens.toFixed(3)} nm`, sens <= spec / 2, `需偵測規格半寬的一半（${(spec / 2).toFixed(3)} nm）`),
        row('擬合品質 GOF', '模型和光譜吻合嗎？', `GOF ${(a.gof ?? NaN).toFixed(4)}`, a.gof >= 0.95 ? (a.chi < 2 ? true : 'warn') : a.gof >= 0.8 ? 'warn' : false, a.gof >= 0.95 && a.chi >= 2 ? 'GOF ≥ 0.95 但 χ²ν 偏高：GOF 對系統性誤差不敏感（T1）' : '≥ 0.95 可接受、< 0.8 不吻合（T1）'),
        row('穩健性 Robustness', '製程窗口內模型仍成立嗎？', `斜率 ${a.slope.toFixed(3)}，χ²ν ${a.chi.toFixed(a.chi < 10 ? 2 : 0)}`, Math.abs(a.slope - 1) <= 0.03 && a.chi < 2, '分批追蹤斜率 1 ± 0.03 且殘差為雜訊（T1）'),
        row('產能 Throughput', '跟得上產線嗎？', `${wph.toFixed(0)} 片/時（${n} 點）`, wph >= req, `每片 20 s＋每點 2.5 s（示意）；需求 ${req} 片/時`),
        row('匹配 Matching', '機台之間一致嗎？', `最大機台偏差 ${maxBias.toFixed(3)} nm`, maxBias <= 0.1 * 2 * spec, `≤ 規格窗口的 10%（${(0.2 * spec).toFixed(3)} nm）（T3）`),
        row('孔內覆蓋 Coverage（DRAM）', '平面讀值代表孔底嗎？', `孔底 ${Math.round(s.thickInfo.bottom * 100)} %`, s.thickInfo.bottom >= 0.95 ? null : false, s.thickInfo.bottom >= 0.95 ? '模型推算正常，但平面量測無法驗證：需 TEM 剖面抽檢（T2）' : '孔底覆蓋不足：平面配方無法代表產品（T2）'));
    }
    document.addEventListener('dms:results', draw);
    S.subscribe(() => draw());
  }
  root.DMS.npi = { mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
