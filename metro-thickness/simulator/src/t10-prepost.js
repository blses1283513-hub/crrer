/* DRAM Thickness Metro — T10 pre/post measurement for dry etch, CMP and wet process:
   rate and rate uniformity from site-matched maps, selectivity from the stop film, CMP erosion,
   wet other-film loss, matched vs unmatched sampling, and the Δ-uncertainty formula. */
(function (root) {
  'use strict';
  const D = root.DMS;
  const MODES = {
    etch: { zh: '乾蝕刻 Dry etch', target: '被蝕刻膜（如 SiO₂ mold）', stop: '停止層（如 SiN）', rateZh: '蝕刻速率 ER', dram: 'DRAM 例：電容孔 mold 氧化層蝕刻停在 SiN 支撐層／蝕刻停止層。' },
    cmp: { zh: 'CMP 研磨', target: '被研磨膜（如 oxide overburden）', stop: '停止層（如 SiN）', rateZh: '研磨速率 RR', dram: 'DRAM 例：STI 或電容 mold 平坦化，SiN 為停止層；密集陣列區的停止層被多磨＝侵蝕（erosion）。' },
    wet: { zh: '濕製程 Wet', target: '被移除膜（如犧牲氧化層）', stop: '—', rateZh: '濕蝕刻速率 ER', dram: 'DRAM 例：電容 mold 濕式移除（HF）時，SiN 支撐層與 TiN 電極要「幾乎不被吃」——另一層膜的損失也要量。' },
  };
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui, P = D.proc, T = D.thick;
    const modeSeg = V.seg(Object.entries(MODES).map(([k, m]) => [k, m.zh]), 'etch', (k) => S.setExt({ pp: { mode: k } }), '製程');
    const K = [
      ['t0', '目標膜厚（前）', 'pre thickness', 'nm', 30, 300, 1], ['rr', '平均速率', 'mean rate', 'nm/s', 0.2, 5, 0.05], ['timeF', '製程時間（相對清除時間）', 'time / clear time', '×', 0.4, 1.6, 0.01],
      ['sel', '選擇比 目標:停止', 'selectivity', ':1', 2, 50, 1], ['dome', '速率中心快（+）／邊緣快（−）', 'rate dome', '%', -8, 8, 0.1], ['edge', '邊緣速率', 'rate edge', '%', -10, 10, 0.1],
      ['inDome', '來料膜形狀（中心厚 +）', 'incoming shape', '%', -4, 4, 0.1], ['density', '圖形密度（CMP 侵蝕）', 'pattern density', '', 0, 1, 0.05], ['other', '另一層膜的濕蝕刻速率', 'other-film ER', 'nm/s', 0, 0.2, 0.002],
      ['sPre', '前量測 σ', 'σ pre', 'nm', 0.05, 1, 0.01], ['sPost', '後量測 σ', 'σ post', 'nm', 0.05, 1, 0.01],
    ];
    const sl = {};
    K.forEach(([k, zh, en, unit, mn, mx, st]) => { sl[k] = V.knob({ key: k, zh, en, unit, min: mn, max: mx, step: st, tier: 'red', src: '示意' }, 0, (v) => S.setExt({ pp: { [k]: v } })); });
    const mSeg = V.seg([[true, '前後同點（site-matched）'], [false, '前後不同點']], true, (k) => S.setExt({ pp: { matched: k === 'true' } }), '取樣');
    const ctx = u.el('div', { class: 'info' }), mapBox = u.el('div'), kv = u.el('div'), prof = u.el('div'), dCard = u.el('div');
    host.append(
      u.el('h2', { id: 'h-t10' }, 'T10 前後量測：速率・均勻性・選擇比 ', u.el('span', { class: 'en' }, 'pre/post · rate · uniformity · selectivity')),
      u.el('p', { class: 'sub' }, '乾蝕刻、CMP、濕製程都靠「前量一次、後量一次」：同一片、同一批點，膜厚差除以時間就是速率；各點速率的分散就是速率均勻性；目標膜與停止層的速率比就是選擇比。CMP 還要量停止層被多磨了多少（侵蝕），濕製程要量其他膜被吃了多少。'),
      u.el('div', { class: 'row' }, modeSeg), ctx,
      u.el('div', { class: 'grid2' }, u.el('div', {}, ...K.map(([k]) => sl[k]), u.el('div', { class: 'row' }, mSeg)), u.el('div', {}, kv, mapBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' }, u.el('div', {}, u.el('h4', { class: 'grp' }, '沿直徑：前、後與停止層'), prof), dCard));

    function draw(s) {
      const e = s.ext.pp, M = MODES[e.mode];
      modeSeg.sync(e.mode); mSeg.sync(e.matched);
      K.forEach(([k]) => { if (!sl[k].contains(document.activeElement)) sl[k].sync(e[k]); });
      ['sel', 'density'].forEach((k) => { sl[k].hidden = e.mode === 'wet' || (k === 'density' && e.mode !== 'cmp'); });
      sl.other.hidden = e.mode !== 'wet';
      ctx.textContent = `${M.dram} 目標膜：${M.target}；停止層：${M.stop}。`;
      const tClear = e.t0 / e.rr;
      const p = { mode: e.mode, t0: e.t0, rr: e.rr, time: e.timeF * tClear, sel: e.sel, stop0: 50, dome: e.dome, edge: e.edge, inDome: e.inDome, density: e.density, sPre: e.sPre, sPost: e.sPost, other: e.other };
      const sites = T.polarSites([1, 8, 16, 24]), other = T.PLANS.p5.sites; // unmatched: pre on a sparse 5-point plan, post on 49 points
      const rows = P.removalMap(p, sites, 7);
      // rate monitor: a timed partial process (60% of the clear time) on a blanket wafer, sites matched or not
      const pm = { ...p, time: 0.6 * tClear }, mon = P.removalMap(pm, sites, 9);
      const st = P.rateStats(mon, pm, e.matched ? null : P.removalMap(pm, other, 11));
      const rateUsed = e.matched ? st.rate : st.unmatched;
      const prod = P.rateStats(rows, p, null);
      const cleared = rows.filter((r) => r.post === 0).length;
      const stopLoss = rows.map((r) => r.stopLoss), otherLoss = rows.map((r) => r.otherLoss);
      const mx = (a) => Math.max(...a), mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;
      const selMeas = e.mode === 'wet' ? NaN : rateUsed / prod.stopRate;
      const pairs = [[`${M.rateZh}（監控片部分製程）`, `${rateUsed.toFixed(3)} nm/s`], ['真實平均速率', `${e.rr.toFixed(3)} nm/s`], ['速率均勻性 1σ/平均', `${st.unif.toFixed(2)} %`, st.unif > 3 ? 'badtxt' : '']];
      if (e.mode === 'wet') pairs.push(['另一層膜損失（平均／最大）', `${mean(otherLoss).toFixed(2)}／${mx(otherLoss).toFixed(2)} nm`, mx(otherLoss) > 2 ? 'badtxt' : 'goodtxt']);
      else pairs.push(['產品片已清除的點', `${cleared}／${rows.length}`, cleared < rows.length ? 'badtxt' : 'goodtxt'], ['選擇比（量測）', Number.isFinite(selMeas) ? `${selMeas.toFixed(1)} : 1` : '—（未過蝕刻）'], [e.mode === 'cmp' ? '停止層侵蝕（平均／最大）' : '停止層損失（平均／最大）', `${mean(stopLoss).toFixed(2)}／${mx(stopLoss).toFixed(2)} nm`, mx(stopLoss) > 5 ? 'badtxt' : '']);
      kv.replaceChildren(V.kvGrid(pairs),
        u.el('p', { class: 'note' }, (e.mode !== 'wet' && cleared < rows.length ? `製程時間不足：${rows.length - cleared} 個點還有殘膜（under-etch／under-polish）——速率最慢或來料最厚的地方先出問題。` : '') +
          (e.matched ? '' : ` 前後不同點（前量 5 點、後量 49 點）：來料膜的形狀被混進速率（${(st.unmatched - st.rate >= 0 ? '+' : '')}${(((st.unmatched - st.rate) / st.rate) * 100).toFixed(2)} %），而且無法算出每點速率圖。`) +
          ' 速率從「部分製程」的監控片量：膜清除後，後量測只剩 0，就不含速率資訊了。'));
      // rate map (from the monitor)
      const W = 260, c = W / 2, R = W / 2 - 8, g = u.svg('svg', { viewBox: `0 0 ${W} ${W}`, class: 'svg-small', role: 'img', 'aria-label': '速率晶圓圖' });
      g.append(u.svg('circle', { cx: c, cy: c, r: R, fill: 'var(--surface-3)', stroke: 'var(--text-dim)' }));
      const rates = mon.map((r) => (r.mPre - r.mPost) / pm.time), lo = Math.min(...rates), hi = Math.max(...rates);
      mon.forEach((r, i) => { const t = hi > lo ? (rates[i] - lo) / (hi - lo) : 0.5; g.append(u.svg('circle', { cx: c + (r.x / 150) * R, cy: c - (r.y / 150) * R, r: 7, fill: `rgb(${Math.round(205 - 170 * t)},${Math.round(226 - 160 * t)},${Math.round(251 - 140 * t)})`, stroke: 'var(--surface)' })); });
      mapBox.replaceChildren(u.el('h4', { class: 'grp' }, `速率圖（監控片，49 點）${lo.toFixed(3)} → ${hi.toFixed(3)} nm/s`), e.matched ? g : u.el('p', { class: 'note' }, '前後不同點時，無法算出每一點的速率——只剩一個平均值。'));
      // profile along x
      const xs = []; for (let x = -147; x <= 147; x += 3) xs.push(x);
      const line = xs.map((x) => P.siteRemoval(p, x, 0));
      const ser = [{ pts: xs.map((x, i) => [x, line[i].pre]), color: 'var(--text-dim)', label: '前（目標膜）' }, { pts: xs.map((x, i) => [x, line[i].post]), color: 'var(--accent)', label: '後（目標膜）' }];
      const loss = xs.map((x, i) => [x, e.mode === 'wet' ? line[i].otherLoss : line[i].stopLoss]);
      prof.replaceChildren(V.chart(ser, { h: 200, xLabel: '位置 x (mm)', yLabel: '目標膜 (nm)', yMin: 0, xFmt: (v) => v.toFixed(0), yFmt: (v) => v.toFixed(0), aria: '前後厚度剖面' }),
        V.chart([{ pts: loss, color: 'var(--leak)', area: true, label: e.mode === 'wet' ? '另一層膜損失' : e.mode === 'cmp' ? '停止層侵蝕' : '停止層損失' }], { h: 170, xLabel: '位置 x (mm)', yLabel: '損失 (nm)', yMin: 0, xFmt: (v) => v.toFixed(0), yFmt: (v) => v.toFixed(1), aria: '停止層或其他膜的損失' }),
        u.el('p', { class: 'note' }, e.mode === 'wet' ? '另一層膜的損失也要量：濕製程要「只拿掉一層」。' : '最先清除的地方（速率最快或來料最薄）停止層被蝕刻最久，損失最大——選擇比與均勻性一起決定停止層要留多厚。'));
      const sd = T.deltaSigma(e.sPre, e.sPost, e.matched ? 0.8 : 0), sdi = T.deltaSigma(e.sPre, e.sPost, 0);
      dCard.replaceChildren(u.el('div', { class: 'card' }, u.el('h3', {}, '差值的不確定度'),
        V.kvGrid([['σ_Δ（同機同點，ρ≈0.8）', `${T.deltaSigma(e.sPre, e.sPost, 0.8).toFixed(3)} nm`, 'goodtxt'], ['σ_Δ（不同機台或點，ρ=0）', `${sdi.toFixed(3)} nm`, 'badtxt'], ['速率 σ（目前取樣）', `${(sd / pm.time).toFixed(4)} nm/s`]]),
        u.el('p', { class: 'note' }, 'σ_Δ² = σ_pre² + σ_post² − 2ρσ_preσ_post。前後用同一台、同一點、同一配方，系統誤差互相抵消（ρ 大）。選擇比 = 目標膜速率 ÷ 停止層速率，兩個速率的誤差會相乘放大，停止層損失很小時尤其不準——要用足夠的過蝕刻時間或專用停止層監控片。'),
        u.el('p', { class: 'note' }, '舊版 T3 的「蝕刻／CMP 前後差值」卡片已併入這裡。')));
    }
    S.subscribe(draw);
  }
  root.DMS.t10 = { mount, MODES };
})(typeof globalThis !== 'undefined' ? globalThis : this);
