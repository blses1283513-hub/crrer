/* DRAM Thickness Metro — T3 SPC, gauge R&R, tool matching, APC loop, monitor-wafer contamination,
   and the etch/CMP delta-uncertainty card. Shares σ_meas and the spec window with M6 (B3). */
(function (root) {
  'use strict';
  const D = root.DMS;
  const EVENTS = [['none', '無事件'], ['step', '階躍 +0.15 nm（第 30 批）'], ['drift', '漂移 +0.006 nm／批（第 25 批起）'], ['sigma', '變異 ×2（第 30 批起）']];

  function simulateLots(s) {
    const T = D.thick, design = s.designParams, th = s.thick;
    const target = design.tZ_nm, a = T.aldMean(target, th.ald, th.gpc0);
    const R = T.rng(21), tools = s.t3.tools, sMeas = s.params.meas.tZ.sMeas;
    const out = []; let c = 0;
    for (let i = 0; i < 60; i++) {
      const ev = s.t3.event;
      const sp = ev === 'sigma' && i >= 30 ? 0.06 : 0.03;
      const d = (a.mean - target) + (ev === 'step' && i >= 30 ? 0.15 : 0) + (ev === 'drift' && i >= 25 ? 0.006 * (i - 24) : 0) + R.n() * sp;
      const truth = target + d - c;
      const k = s.t3.tool === 3 ? i % 3 : s.t3.tool;
      const bias = tools[k].off + (tools[k].slope - 1) * truth + th.metro.modelBias;
      const rep = truth + bias + R.n() * sMeas;
      if (th.metro.apcOn) c += 0.5 * (rep - target);
      out.push({ lot: i + 1, tool: k, truth, rep });
    }
    return out;
  }

  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, T = D.thick, V = D.tui;
    const evSeg = V.seg(EVENTS, 'none', (k) => S.setT3({ event: k }), '製程事件');
    const toolSeg = V.seg([[0, 'M1'], [1, 'M2'], [2, 'M3'], [3, '輪流派工']], 0, (k) => { S.setT3({ tool: +k }); syncToolBias(); }, '量測機台');
    const apcSeg = V.seg([[false, 'APC 關'], [true, 'APC 開']], false, (k) => S.setThick({ metro: { apcOn: k === 'true' } }), 'APC');
    const amcSl = V.knob({ key: 'amc', zh: '監控片吸附速率', en: 'AMC growth', unit: 'nm/天', min: 0, max: 0.03, step: 0.001, tier: 'red', src: '示意；見書 §17' }, 0, (v) => S.setT3({ amcRate: v }));
    // tool table + shared gauge
    const offIn = [], slIn = [];
    const toolRows = [0, 1, 2].map((k) => {
      const o = u.el('input', { type: 'number', step: 0.01, 'aria-label': `M${k + 1} 偏移` }), sl2 = u.el('input', { type: 'number', step: 0.005, 'aria-label': `M${k + 1} 斜率` });
      o.addEventListener('change', () => { const t = S.get().t3.tools.map((x) => ({ ...x })); t[k].off = +o.value || 0; S.setT3({ tools: t }); syncToolBias(); });
      sl2.addEventListener('change', () => { const t = S.get().t3.tools.map((x) => ({ ...x })); t[k].slope = +sl2.value || 1; S.setT3({ tools: t }); syncToolBias(); });
      offIn.push(o); slIn.push(sl2);
      return u.el('tr', {}, u.el('td', {}, `M${k + 1}`), u.el('td', {}, o), u.el('td', {}, sl2));
    });
    const sMeasIn = u.el('input', { type: 'number', step: 0.001, min: 0, 'aria-label': 'σ_meas' });
    sMeasIn.addEventListener('change', () => { const v = +sMeasIn.value; if (v >= 0) S.setMeas('tZ', 'sMeas', v); });
    const specIn = u.el('input', { type: 'number', step: 0.01, min: 0.01, 'aria-label': '規格半寬' });
    specIn.addEventListener('change', () => { const v = +specIn.value; if (v > 0) S.setMeas('tZ', 'specHalf', v); });
    function syncToolBias() {
      const s = S.snapshot(), t = s.t3.tools, tz = s.designParams.tZ_nm;
      const b = (k) => t[k].off + (t[k].slope - 1) * tz;
      const v = s.t3.tool === 3 ? (b(0) + b(1) + b(2)) / 3 : b(s.t3.tool);
      S.setThick({ metro: { toolBias: v } });
    }

    const iBox = u.el('div'), eBox = u.el('div'), monBox = u.el('div'), grrBox = u.el('div'), matchBox = u.el('div'), cpkBox = u.el('div'), apcNote = u.el('div', { class: 'info' });
    let csv = [];
    // A7 delta card
    let dS0 = 0.3, dS1 = 0.3, dRho = 0.8, dT = 60, dDel = 38;
    const dOut = u.el('div'), dChart = u.el('div');
    function drawDelta() {
      const sd = T.deltaSigma(dS0, dS1, dRho), sdi = T.deltaSigma(dS0, dS1, 0);
      dOut.replaceChildren(V.kvGrid([['移除量 Δd', `${dDel.toFixed(1)} nm`], ['速率 ER／RR', `${(dDel / dT).toFixed(3)} nm/s`], ['σ_Δ（同機同點，ρ）', `${sd.toFixed(3)} nm`, 'goodtxt'], ['σ_Δ（不同機台，ρ=0）', `${sdi.toFixed(3)} nm`, 'badtxt'], ['σ_速率', `${(sd / dT).toFixed(4)} nm/s`]]));
      const pts = []; for (let r = 0; r <= 0.99; r += 0.03) pts.push([r, T.deltaSigma(dS0, dS1, r)]);
      dChart.replaceChildren(V.chart([{ pts, color: 'var(--accent)', label: 'σ_Δ' }, { pts: [[dRho, sd]], color: 'var(--sig)', dotsOnly: true, r: 5 }], { h: 170, xLabel: '前後量測誤差相關係數 ρ', yLabel: 'σ_Δ (nm)', xFmt: (v) => v.toFixed(1), yFmt: (v) => v.toFixed(2), aria: '差值不確定度對相關係數' }));
    }
    const deltaCard = u.el('div', { class: 'card' }, u.el('h3', {}, '蝕刻／CMP 前後差值（A7）', u.el('span', { class: 'en' }, ' pre/post Δ')),
      V.knob({ key: 'd0', zh: '前量測 σ', en: 'σ pre', unit: 'nm', min: 0.05, max: 1, step: 0.01 }, dS0, (v) => { dS0 = v; drawDelta(); }),
      V.knob({ key: 'd1', zh: '後量測 σ', en: 'σ post', unit: 'nm', min: 0.05, max: 1, step: 0.01 }, dS1, (v) => { dS1 = v; drawDelta(); }),
      V.knob({ key: 'dr', zh: '誤差相關 ρ（同機同點時高）', en: 'error correlation', unit: '', min: 0, max: 0.99, step: 0.01 }, dRho, (v) => { dRho = v; drawDelta(); }),
      dOut, dChart, u.el('p', { class: 'note' }, 'σ_Δ² = σ₀² + σ₁² − 2ρσ₀σ₁。DRAM 例子：電容孔 mold 氧化層 CMP 後殘厚、或蝕刻後停止層厚度。前後用同一台、同一點量，系統誤差互相抵消。'));

    host.append(
      u.el('h2', { id: 'h-t3' }, 'T3 SPC・量具・機台匹配 ', u.el('span', { class: 'en' }, 'SPC · gauge R&R · matching · APC')),
      u.el('p', { class: 'sub' }, '60 批 ZrO₂ 監控讀值。灰線是只有模擬器才知道的真實膜厚，藍點是量測讀值。打開 APC 後讀值會被控制在目標，但若機台有偏差，真實膜厚會被推離目標——量測偏差變成製程偏差。σ_meas 與規格半寬和 M6 共用。'),
      u.el('div', { class: 'grid2' },
        u.el('div', {}, u.el('div', { class: 'row' }, u.el('span', { class: 'note' }, '製程事件'), evSeg), u.el('div', { class: 'row' }, u.el('span', { class: 'note' }, '量測機台'), toolSeg),
          u.el('div', { class: 'row' }, apcSeg), amcSl,
          u.el('div', { class: 'row' }, u.el('label', {}, 'σ_meas（共用 M6）', sMeasIn), u.el('label', {}, '規格半寬', specIn), u.el('span', { class: 'note' }, 'nm'))),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '機台偏移與斜率 tool offset & slope'), u.el('table', { class: 'f' }, u.el('thead', {}, u.el('tr', {}, u.el('th', {}, '機台'), u.el('th', {}, '偏移 nm'), u.el('th', {}, '斜率'))), u.el('tbody', {}, ...toolRows)),
          u.el('p', { class: 'note' }, '讀值 = 真實 + 偏移 + (斜率 − 1)·真實 + T1 模型偏差 + 雜訊。'), apcNote)),
      u.el('div', { class: 'grid2', style: 'margin-top:12px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, 'I 管制圖 individuals chart'), iBox, u.el('div', { class: 'row' }, V.copyBtn('複製批次 CSV', () => csv.join('\n')))),
        u.el('div', {}, u.el('h4', { class: 'grp' }, 'EWMA（λ = 0.2）'), eBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:12px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, '製程能力 capability'), cpkBox),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '監控片每日讀值（AMC）'), monBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:12px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, 'Gauge R&R（10 片 × 3 機台 × 3 次）'), grrBox),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '機台匹配 matching（8 片參考片）'), matchBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:12px' }, deltaCard, u.el('div', {})));
    drawDelta();

    let lastKey = '';
    function render(s) {
      evSeg.sync(s.t3.event); toolSeg.sync(s.t3.tool); apcSeg.sync(s.thick.metro.apcOn);
      if (!amcSl.contains(document.activeElement)) amcSl.sync(s.t3.amcRate);
      s.t3.tools.forEach((t, k) => { if (document.activeElement !== offIn[k]) offIn[k].value = t.off; if (document.activeElement !== slIn[k]) slIn[k].value = t.slope; });
      if (document.activeElement !== sMeasIn) sMeasIn.value = s.params.meas.tZ.sMeas;
      if (document.activeElement !== specIn) specIn.value = s.params.meas.tZ.specHalf;
      const key = JSON.stringify([s.t3, s.thick, s.designParams.tZ_nm, s.params.meas.tZ]);
      if (key === lastKey) return; lastKey = key;
      const lots = simulateLots(s), target = s.designParams.tZ_nm, spec = s.params.meas.tZ.specHalf;
      const rep = lots.map((l) => l.rep);
      const base = rep.slice(0, 20), cl = base.reduce((a, b) => a + b, 0) / 20;
      const mr = base.slice(1).reduce((a, v, i) => a + Math.abs(v - base[i]), 0) / 19, sg = mr / 1.128;
      const hits = T.runRules(rep, cl, sg);
      const flagged = new Set(Object.values(hits).flat());
      const colors = ['var(--accent)', 'var(--ok)', 'var(--leak)'];
      iBox.replaceChildren(V.chart([
        { pts: lots.map((l) => [l.lot, l.truth]), color: 'var(--text-faint)', width: 1.4, label: '真實膜厚' },
        { pts: lots.map((l, i) => [l.lot, l.rep, flagged.has(i) ? 'var(--sig)' : colors[l.tool]]), color: 'var(--accent)', width: 1, dots: true, r: 3.2, label: '讀值（紅點＝判異）' }],
        { h: 230, xLabel: '批次', yLabel: 't_ZrO₂ (nm)', hlines: [{ y: cl + 3 * sg, label: 'UCL', color: 'var(--text-dim)' }, { y: cl - 3 * sg, label: 'LCL', color: 'var(--text-dim)' }, { y: target + spec, label: 'USL', color: 'var(--sig)', dash: '2 3' }, { y: target - spec, label: 'LSL', color: 'var(--sig)', dash: '2 3' }], yFmt: (v) => v.toFixed(2), aria: 'I 管制圖' }),
        u.el('p', { class: 'note' }, `管制界限由前 20 批計算（I-MR）：中心 ${cl.toFixed(3)}、σ ${sg.toFixed(3)} nm。判異：` + (Object.entries(hits).filter(([, v]) => v.length).map(([k, v]) => `${k} 第 ${v[0] + 1} 批起`).join('、') || '無') +
          (s.t3.tool === 3 ? '。輪流派工時點的顏色代表機台（藍 M1、綠 M2、橘 M3）。' : '。')));
      const ew = T.ewma(rep, cl, sg);
      const first = ew.findIndex((e) => e.alarm);
      eBox.replaceChildren(V.chart([{ pts: ew.map((e, i) => [i + 1, e.z]), color: 'var(--accent)', label: 'EWMA' }, { pts: ew.map((e, i) => [i + 1, e.hi]), color: 'var(--text-dim)', dash: '4 4' }, { pts: ew.map((e, i) => [i + 1, e.lo]), color: 'var(--text-dim)', dash: '4 4' }],
        { h: 230, xLabel: '批次', yLabel: 'EWMA (nm)', yFmt: (v) => v.toFixed(3), aria: 'EWMA 管制圖' }),
        u.el('p', { class: 'note' }, first >= 0 ? `EWMA 第 ${first + 1} 批警報。對小而持續的偏移比 I 圖敏感。` : 'EWMA 無警報。'));
      csv = ['lot,tool,true_nm,reported_nm', ...lots.map((l) => `${l.lot},M${l.tool + 1},${l.truth.toFixed(4)},${l.rep.toFixed(4)}`)];

      const last30 = rep.slice(30), tru30 = lots.slice(30).map((l) => l.truth);
      const cR = T.cpk(last30, target - spec, target + spec), cT = T.cpk(tru30, target - spec, target + spec);
      const kind = (v) => (v >= 1.33 ? 'good' : v >= 1 ? 'marginal' : 'reject');
      cpkBox.replaceChildren(V.kvGrid([['Cpk（讀值，後 30 批）', `${cR.cpk.toFixed(2)}（95% ${cR.lo.toFixed(2)}–${cR.hi.toFixed(2)}）`], ['Cpk（真實膜厚）', `${cT.cpk.toFixed(2)}（95% ${cT.lo.toFixed(2)}–${cT.hi.toFixed(2)}）`],
        ['讀值平均', `${cR.m.toFixed(3)} nm`], ['真實平均', `${cT.m.toFixed(3)} nm`]]),
        u.el('div', { class: 'row' }, V.chip(`讀值 ${kind(cR.cpk) === 'good' ? '合格' : kind(cR.cpk) === 'marginal' ? '勉強' : '不合格'}`, kind(cR.cpk)), V.chip(`真實 ${kind(cT.cpk) === 'good' ? '合格' : kind(cT.cpk) === 'marginal' ? '勉強' : '不合格'}`, kind(cT.cpk))),
        u.el('p', { class: 'note' }, Math.abs(cR.cpk - cT.cpk) > 0.3 ? '讀值的 Cpk 與真實膜厚的 Cpk 差很多：不是量測雜訊讓好製程看起來差，就是 APC＋機台偏差讓壞製程看起來好。' : '30 個點的 Cpk 信賴區間很寬，報告時一起附上。'));
      apcNote.textContent = s.thick.metro.apcOn ? `APC 開：控制器讓讀值回到目標。目前機台偏差 ${(s.thick.metro.toolBias + s.thick.metro.modelBias).toFixed(3)} nm，所以真實膜厚被推到約 ${(target - s.thick.metro.toolBias - s.thick.metro.modelBias).toFixed(3)} nm。上方鏈條的電性結果已反映這件事。` : 'APC 關：製程漂移直接出現在讀值上；機台偏差只影響讀值，不影響真實膜。';

      // monitor wafer: reference 6.00 nm, measured daily, cleaned every 10 days
      const Rm = T.rng(9), tool = s.t3.tool === 3 ? 0 : s.t3.tool, tl = s.t3.tools[tool];
      const days = Array.from({ length: 30 }, (_, d) => { const amc = s.t3.amcRate * (d % 10); return [d + 1, 6 + tl.off + (tl.slope - 1) * 6 + 0.28 * amc + Rm.n() * s.params.meas.tZ.sMeas]; });
      monBox.replaceChildren(V.chart([{ pts: days, color: 'var(--accent)', dots: true, width: 1.2, label: `參考片（M${tool + 1}）` }],
        { h: 200, xLabel: '天', yLabel: '讀值 (nm)', hlines: [{ y: 6, label: '認證值 6.00', color: 'var(--text-faint)' }], vlines: s.t3.amcRate > 0 ? [{ x: 10.5, label: '清潔' }, { x: 20.5, label: '清潔' }] : [], yFmt: (v) => v.toFixed(2), aria: '監控片每日讀值' }),
        u.el('p', { class: 'note' }, s.t3.amcRate > 0 ? '鋸齒狀上升、清潔後歸零：是監控片表面吸附，不是機台漂移，也不是製程。所有機台會一起看到。（0.28：吸附層（n≈1.45）被 ZrO₂ 模型吸收時的換算係數，由 T1 的擬合算出。）' : '把吸附速率調高，看監控片如何「假漂移」。'));

      // gauge R&R with the current tools and shared σ_meas
      const Rg = T.rng(13), parts = Array.from({ length: 10 }, (_, i) => target - 0.4 + (0.8 * i) / 9);
      const y = parts.map((pt) => s.t3.tools.map((tl2) => [0, 1, 2].map(() => pt + tl2.off + (tl2.slope - 1) * pt + Rg.n() * s.params.meas.tZ.sMeas)));
      const g = T.grr(y, target - spec, target + spec);
      const band = (v) => (v < 0.1 ? 'good' : v <= 0.3 ? 'marginal' : 'reject');
      const m6pt = (6 * s.params.meas.tZ.sMeas) / (2 * spec);
      grrBox.replaceChildren(V.kvGrid([['重複性 σ', `${g.rep.toFixed(4)} nm`], ['再現性 σ（機台）', `${g.repro.toFixed(4)} nm`], ['GR&R σ', `${g.grr.toFixed(4)} nm`], ['ndc', g.ndc.toFixed(1), g.ndc >= 5 ? 'goodtxt' : 'badtxt']]),
        u.el('div', { class: 'row' }, u.el('span', { class: 'note' }, 'P/T（含機台）'), V.chip(`${(g.pt * 100).toFixed(1)}%`, band(g.pt)), u.el('span', { class: 'note' }, 'M6 的 P/T（只含 σ_meas）'), V.chip(`${(m6pt * 100).toFixed(1)}%`, band(m6pt))),
        u.el('p', { class: 'note' }, g.repro > g.rep ? '再現性（機台間差異）大於重複性：改善方向是匹配，不是單機精度。' : '重複性主導：改善單機精度（平均次數、光斑、對焦）。'));

      D.t3Last = { pt: g.pt, ndc: g.ndc, toolBias: s.t3.tools.map((t2) => t2.off + (t2.slope - 1) * target), sMeas: s.params.meas.tZ.sMeas, spec };
      document.dispatchEvent(new CustomEvent('dms:results'));
      // matching: Bland–Altman of M2, M3 vs M1 on reference wafers
      const Rr = T.rng(17), refs = Array.from({ length: 8 }, (_, i) => 4.6 + i * 0.5);
      const meas = s.t3.tools.map((tl2) => refs.map((r) => r + tl2.off + (tl2.slope - 1) * r + Rr.n() * s.params.meas.tZ.sMeas));
      const ser = [1, 2].map((k) => ({ pts: refs.map((_, i) => [(meas[k][i] + meas[0][i]) / 2, meas[k][i] - meas[0][i]]), color: k === 1 ? 'var(--ok)' : 'var(--leak)', dots: true, width: 1.2, label: `M${k + 1} − M1` }));
      const dm2 = T.deming(meas[0], meas[1]), dm3 = T.deming(meas[0], meas[2]);
      matchBox.replaceChildren(V.chart(ser, { h: 200, xLabel: '兩機平均 (nm)', yLabel: '差值 (nm)', hlines: [{ y: 0, color: 'var(--text-faint)' }], xFmt: (v) => v.toFixed(1), yFmt: (v) => v.toFixed(2), aria: 'Bland–Altman 匹配圖' }),
        V.kvGrid([['M2 = b₀ + b₁·M1', `${dm2.b0.toFixed(3)} + ${dm2.b1.toFixed(4)}·M1`], ['M3 = b₀ + b₁·M1', `${dm3.b0.toFixed(3)} + ${dm3.b1.toFixed(4)}·M1`]]),
        u.el('p', { class: 'note' }, 'Bland–Altman：差值隨厚度傾斜＝斜率不匹配，單一 offset 修正不夠。戴明迴歸（兩軸都有誤差）估斜率。'));
    }
    S.subscribe(render);
    syncToolBias();
  }
  root.DMS.t3 = { mount, simulateLots };
})(typeof globalThis !== 'undefined' ? globalThis : this);
