/* DRAM Thickness Metro — T8 dry-etch profile + OCD scatterometry: etch knobs make a trench grating,
   TE/TM spectra (zeroth-order EMA), model fit of depth / top CD / SWA, correlation, CD-SEM cross-check. */
(function (root) {
  'use strict';
  const D = root.DMS;
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui, X = D.ext;
    const K = [
      ['time', '蝕刻時間（相對）', 'etch time', '×', 0.8, 1.2, 0.01, '深度 ∝ 時間（示意）'],
      ['bias', '偏壓功率（相對）', 'bias power', '×', 0.6, 1.4, 0.01, '離子方向性 → 側壁角（示意）'],
      ['poly', '側壁聚合物（CD 偏移）', 'polymer CD bias', 'nm', -4, 4, 0.1, '鈍化層 → 頂部 CD（示意）'],
      ['hm', '殘留硬罩 SiO₂', 'hard-mask remain', 'nm', 0, 12, 0.5, '示意'],
    ];
    const sl = {};
    K.forEach(([k, zh, en, unit, mn, mx, st, src]) => { sl[k] = V.knob({ key: k, zh, en, unit, min: mn, max: mx, step: st, tier: 'red', src }, 0, (v) => S.setExt({ ocd: { [k]: v } })); });
    const swaSeg = V.seg([[true, 'SWA 也擬合'], [false, 'SWA 固定 87°']], true, (k) => S.setExt({ ocd: { floatSWA: k === 'true' } }), 'SWA');
    const hmSeg = V.seg([[true, '模型含硬罩'], [false, '模型忽略硬罩']], true, (k) => S.setExt({ ocd: { modelHM: k === 'true' } }), '硬罩');
    const profBox = u.el('div'), specBox = u.el('div'), kv = u.el('div'), cmp = u.el('div');
    host.append(
      u.el('h2', { id: 'h-t8' }, 'T8 乾蝕刻剖面與 OCD ', u.el('span', { class: 'en' }, 'dry-etch profile · scatterometry')),
      u.el('p', { class: 'sub' }, '乾蝕刻決定剖面：深度、頂部 CD、側壁角（SWA）。OCD 對週期性光柵（線與間距）打寬頻光，量反射光譜，再用電磁模型反推剖面。偏振方向與光柵線平行（TE）或垂直（TM）時，光「看到」的有效折射率差很多，兩組光譜一起擬合才分得出 CD 與深度。這裡用零階等效介質（EMA，週期 ≪ 波長時成立）示範；量產用 RCWA。'),
      u.el('div', { class: 'grid2' }, u.el('div', {}, u.el('h4', { class: 'grp' }, '蝕刻製程旋鈕'), ...K.map(([k]) => sl[k]), u.el('div', { class: 'row' }, swaSeg), u.el('div', { class: 'row' }, hmSeg)), u.el('div', {}, u.el('h4', { class: 'grp' }, '剖面：真實（填色）vs OCD 擬合（虛線）'), profBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' }, u.el('div', {}, u.el('h4', { class: 'grp' }, 'TE／TM 反射光譜（量測點 vs 模型）'), specBox), u.el('div', {}, u.el('h4', { class: 'grp' }, '擬合結果與參數相關性'), kv)),
      cmp);
    let lastKey = '';
    function draw(s) {
      const e = s.ext.ocd;
      K.forEach(([k]) => { if (!sl[k].contains(document.activeElement)) sl[k].sync(e[k]); });
      swaSeg.sync(e.floatSWA); hmSeg.sync(e.modelHM);
      const key = JSON.stringify(e); if (key === lastKey) return; lastKey = key;
      const tru = { pitch: 80, depth: 120 * e.time, topCD: 30 + e.poly, swa: Math.min(89.5, 84 + 3 * e.bias + (e.trueSWAoff || 0)), hm: e.hm };
      const meas0 = X.ocdSpectra(tru), R = D.thick.rng(41), nz = 0.002;
      const meas = { TE: meas0.TE.map((v) => v + R.n() * nz), TM: meas0.TM.map((v) => v + R.n() * nz) };
      const g0 = { pitch: 80, depth: 120, topCD: 30, swa: 87, hm: e.modelHM ? tru.hm : 0 };
      const free = e.floatSWA ? ['depth', 'topCD', 'swa'] : ['depth', 'topCD'];
      const f = X.ocdFit(meas, g0, nz, free);
      const fit = { ...g0, ...f.fit };
      // profile drawing
      const W = 300, H = 220, sx = 1.6, sz = 1.2, x0 = 30, z0 = 30;
      const prof = (g, attrs) => { const foot = g.depth / Math.tan((g.swa * Math.PI) / 180); const p = []; for (let k = 0; k < 2; k++) { const cx = x0 + 40 * sx + k * g.pitch * sx; p.push(`M${cx - (g.topCD / 2) * sx},${z0} L${cx + (g.topCD / 2) * sx},${z0} L${cx + (g.topCD / 2 + foot) * sx},${z0 + g.depth * sz} L${cx - (g.topCD / 2 + foot) * sx},${z0 + g.depth * sz} Z`); } return u.svg('path', { d: p.join(' '), ...attrs }); };
      const sv = u.svg('svg', { viewBox: `0 0 ${W} ${H}`, class: 'svg-small', role: 'img', 'aria-label': '蝕刻溝槽剖面' });
      sv.append(u.svg('rect', { x: 0, y: z0 + tru.depth * sz, width: W, height: H, fill: 'var(--m-si)' }));
      sv.append(prof(tru, { fill: 'var(--m-si)', stroke: 'var(--m-si-ln)' }));
      if (tru.hm > 0) for (let k = 0; k < 2; k++) { const cx = x0 + 40 * sx + k * 80 * sx; sv.append(u.svg('rect', { x: cx - (tru.topCD / 2) * sx, y: z0 - tru.hm * sz, width: tru.topCD * sx, height: tru.hm * sz, fill: 'var(--m-ox)', stroke: 'var(--m-ox-ln)' })); }
      sv.append(prof(fit, { fill: 'none', stroke: 'var(--sig)', 'stroke-width': 1.6, 'stroke-dasharray': '4 3' }));
      sv.append(u.svg('text', { x: W - 6, y: 16, 'text-anchor': 'end', 'font-size': 10.5, fill: 'var(--text-dim)' }, `週期 ${tru.pitch} nm，兩條線`));
      profBox.replaceChildren(sv);
      const wl = X.WLO;
      const mm = f.model, half = wl.length;
      specBox.replaceChildren(V.chart([
        { pts: wl.map((l, i) => [l, meas.TE[i] * 100]), color: 'var(--accent)', dotsOnly: true, r: 2 }, { pts: wl.map((l, i) => [l, mm[i] * 100]), color: 'var(--accent)', label: 'TE（E ∥ 線）' },
        { pts: wl.map((l, i) => [l, meas.TM[i] * 100]), color: 'var(--leak)', dotsOnly: true, r: 2 }, { pts: wl.map((l, i) => [l, mm[half + i] * 100]), color: 'var(--leak)', label: 'TM（E ⟂ 線）' }],
      { h: 230, xLabel: '波長 nm', yLabel: 'R (%)', yFmt: (v) => v.toFixed(0), aria: 'TE 與 TM 反射光譜' }),
      u.el('p', { class: 'note' }, `等效介質：TE 看到 n² 的面積平均（線越寬 n 越接近 Si），TM 看到 1/n² 的平均（被空氣主導）。週期 80 nm 小於最短波長 250 nm，只有零階繞射。`));
      const nm = { depth: '深度 depth', topCD: '頂部 CD', swa: '側壁角 SWA' };
      const rows = ['depth', 'topCD', 'swa'].map((k) => [nm[k], tru[k], fit[k], free.includes(k)]);
      kv.replaceChildren(u.el('table', { class: 'f' }, u.el('thead', {}, u.el('tr', {}, u.el('th', {}, '參數'), u.el('th', {}, '真實'), u.el('th', {}, 'OCD'), u.el('th', {}, '誤差'))),
        u.el('tbody', {}, ...rows.map(([n2, t, v, fr]) => u.el('tr', {}, u.el('td', {}, n2 + (fr ? '' : '（固定）')), u.el('td', { class: 'm' }, t.toFixed(2)), u.el('td', { class: 'm' }, v.toFixed(2)), u.el('td', { class: 'm ' + (Math.abs(v - t) > (n2.includes('SWA') ? 0.5 : 0.8) ? 'badtxt' : 'goodtxt') }, (v - t >= 0 ? '+' : '') + (v - t).toFixed(2)))))),
        V.kvGrid([['χ²ν', f.chi2nu.toFixed(f.chi2nu < 10 ? 2 : 0), f.chi2nu > 3 ? 'badtxt' : 'goodtxt'], ...(free.length > 2 ? [['corr(CD, SWA)', f.corr[1][2].toFixed(2), Math.abs(f.corr[1][2]) > 0.9 ? 'badtxt' : ''], ['corr(depth, SWA)', f.corr[0][2].toFixed(2)]] : [['corr(depth, CD)', f.corr[0][1].toFixed(2)]])]),
        u.el('div', { class: 'row' }, u.el('button', { type: 'button', onclick: () => S.setDrift({ key: 'capH', meanShift: +(((fit.depth - 120) / 120) * 100).toFixed(2), shiftUnit: '%', sigmaScale: 1 }) }, '把 OCD 深度變化（%）送到 M6 電容高度')),
        u.el('p', { class: 'note' }, !e.floatSWA && Math.abs(tru.swa - 87) > 0.5 ? `SWA 固定在 87°，但真實是 ${tru.swa.toFixed(1)}°：擬合把側壁的差異推到深度與 CD 上——數字看起來穩定，其實是錯的。` : !e.modelHM && tru.hm > 1 ? '模型忽略了殘留硬罩：多出來的氧化層被吸收成深度與 CD 的誤差。' : '模型與真實結構一致時，三個參數都能分開；相關係數接近 ±1 的組合需要固定其一或用 CD-SEM／TEM 參考值（混合量測）。'));
      // CD-SEM vs OCD comparison
      const ls = X.linescan({ topCD: tru.topCD, h: tru.depth, swa: tru.swa, beam: 2, frames: 16, hole: false }, 7);
      const semCD = X.cdThreshold(ls, 0.5);
      cmp.replaceChildren(u.el('h4', { class: 'grp', style: 'margin-top:12px' }, 'OCD vs CD-SEM'),
        u.el('table', { class: 'f' }, u.el('thead', {}, u.el('tr', {}, u.el('th', {}, ''), u.el('th', {}, 'OCD'), u.el('th', {}, 'CD-SEM'))), u.el('tbody', {},
          u.el('tr', {}, u.el('td', {}, '這個結構的 CD'), u.el('td', { class: 'm' }, `${fit.topCD.toFixed(1)} nm（頂部，模型定義）`), u.el('td', { class: 'm' }, `${semCD.toFixed(1)} nm（50% 閾值）`)),
          u.el('tr', {}, u.el('td', {}, '深度／SWA'), u.el('td', {}, '有'), u.el('td', {}, '無（俯視影像）')),
          u.el('tr', {}, u.el('td', {}, '速度'), u.el('td', {}, '快（每點約 1–3 s）'), u.el('td', {}, '較慢（對焦、PR、多影格）')),
          u.el('tr', {}, u.el('td', {}, '成本／損傷'), u.el('td', {}, '光學、非破壞'), u.el('td', {}, '電子束：光阻收縮、充電')),
          u.el('tr', {}, u.el('td', {}, '代價'), u.el('td', {}, '需要模型與週期性光柵；參數相關'), u.el('td', {}, '直接影像；閾值定義影響 CD')))),
        u.el('p', { class: 'note' }, 'OCD 與 CD-SEM 的「CD」定義不同（模型的頂部寬 vs 閾值邊），兩者有固定偏差是正常的；重要的是偏差穩定。常把 CD-SEM 當 OCD 的參考或餵進 OCD 模型（混合量測）。'));
    }
    S.subscribe(draw);
  }
  root.DMS.t8 = { mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
