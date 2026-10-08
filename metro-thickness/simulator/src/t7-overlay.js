/* DRAM Thickness Metro — T7 overlay: box-in-box registration marks, field-corner sampling, vector map,
   8-term linear model (XY shift, wafer rotation/magnification, field rotation/magnification), residuals, TIS. */
(function (root) {
  'use strict';
  const D = root.DMS;
  const TERMS = [
    ['Tx', 'X 平移 X shift', 'nm', -10, 10, 0.1], ['Ty', 'Y 平移 Y shift', 'nm', -10, 10, 0.1],
    ['Mwx', '晶圓放大 X wafer mag', 'ppm', -2, 2, 0.01], ['Mwy', '晶圓放大 Y wafer mag', 'ppm', -2, 2, 0.01], ['Rw', '晶圓旋轉 wafer rot', 'µrad', -1, 1, 0.01],
    ['Mfx', '場內放大 X field mag', 'ppm', -5, 5, 0.05], ['Mfy', '場內放大 Y field mag', 'ppm', -5, 5, 0.05], ['Rf', '場內旋轉 field rot', 'µrad', -5, 5, 0.05],
    ['noise', '隨機殘差 σ', 'nm', 0, 3, 0.05], ['tis', 'TIS 機台誘發偏移', 'nm', -3, 3, 0.05],
  ];
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui, X = D.ext;
    const sl = {};
    TERMS.forEach(([k, zh, unit, mn, mx, st]) => { sl[k] = V.knob({ key: k, zh, en: '', unit, min: mn, max: mx, step: st, tier: 'red', src: '示意：注入的真實誤差' }, 0, (v) => S.setExt({ ov: { [k]: v } })); });
    const stressSeg = V.seg([[true, '納入 T9 新膜應力（兩層曝光之間）'], [false, '不納入']], true, (k) => S.setExt({ ov: { useStress: k === 'true' } }), '應力');
    const tisSeg = V.seg([[false, '只量 0°'], [true, '0° 與 180° 平均（去 TIS）']], false, (k) => S.setExt({ ov: { tis180: k === 'true' } }), 'TIS');
    const mapBox = u.el('div', { class: 'svgscroll' }), boxBox = u.el('div'), fitBox = u.el('div'), resBox = u.el('div');
    host.append(
      u.el('h2', { id: 'h-t7' }, 'T7 疊對量測 ', u.el('span', { class: 'en' }, 'overlay · registration boxes · linear model')),
      u.el('p', { class: 'sub' }, '疊對（overlay）＝當層圖形相對前層的位移。切割道上的 box-in-box：外框是前層、內框是當層，量兩框中心差。每個曝光場四角各量一點，就能把誤差拆成晶圓項（XY 平移、晶圓旋轉、晶圓放大）與場內項（場內旋轉、場內放大），回饋給曝光機修正；修不掉的叫殘差（residual）。DRAM 的儲存節點接觸（SNC）對位就靠它。'),
      u.el('div', { class: 'grid-t7' }, u.el('div', {}, u.el('h4', { class: 'grp' }, '注入的真實誤差'), ...TERMS.map(([k]) => sl[k]), u.el('div', { class: 'row' }, stressSeg), u.el('div', { class: 'row' }, tisSeg)),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '向量圖（箭頭放大顯示）'), mapBox),
        u.el('div', {}, u.el('h4', { class: 'grp' }, 'box-in-box 怎麼量'), boxBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' }, u.el('div', {}, u.el('h4', { class: 'grp' }, '線性模型擬合 vs 注入值'), fitBox), u.el('div', {}, u.el('h4', { class: 'grp' }, '殘差與規格'), resBox)));

    function draw(s) {
      const e = s.ext.ov;
      TERMS.forEach(([k]) => { if (!sl[k].contains(document.activeElement)) sl[k].sync(e[k]); });
      stressSeg.sync(e.useStress); tisSeg.sync(e.tis180);
      // stress-induced wafer magnification from T9
      let magStress = 0;
      if (e.useStress && D.t9) {
        const st = s.ext.stress, f = D.t9.FILMS[st.film];
        const k = X.kappaFromStress(st.s + X.thermalStress(f.M, f.a, f.T), st.ts, st.tf); // only the film added between the two exposures; incoming bow is common to both layers
        magStress = X.bowMagPpm(k, st.ts);
      }
      const p = { ...e, Mwx: e.Mwx + magStress, Mwy: e.Mwy + magStress, tis: e.tis180 ? 0 : e.tis };
      const v = X.overlayVectors(p, 21), fit = X.overlayFit(v);
      // vector map
      const vmax = Math.max(...v.map((m) => Math.hypot(m.dx, m.dy)), 1);
      const W = 340, c = W / 2, sc = (W / 2 - 12) / 150, arrow = Math.min(3.2, 16 / vmax); // px per nm, auto-scaled so the longest arrow is ≤ 16 px
      const g = u.svg('svg', { viewBox: `0 0 ${W} ${W}`, role: 'img', 'aria-label': '疊對向量圖' });
      g.append(u.svg('circle', { cx: c, cy: c, r: 150 * sc, fill: 'var(--surface-3)', stroke: 'var(--text-dim)' }));
      const seen = new Set();
      for (const m of v) { const key = m.X + ',' + m.Y; if (seen.has(key)) continue; seen.add(key); g.append(u.svg('rect', { x: c + (m.X - 13) * sc, y: c - (m.Y + 16.5) * sc, width: 26 * sc, height: 33 * sc, fill: 'none', stroke: 'var(--border)', 'stroke-width': 0.6 })); }
      for (const m of v) {
        const x0 = c + (m.X + m.x) * sc, y0 = c - (m.Y + m.y) * sc, x1 = x0 + m.dx * arrow, y1 = y0 - m.dy * arrow;
        g.append(u.svg('line', { x1: x0, y1: y0, x2: x1, y2: y1, stroke: 'var(--accent)', 'stroke-width': 1.1 }));
        g.append(u.svg('circle', { cx: x1, cy: y1, r: 1.3, fill: 'var(--accent)' }));
      }
      const ref = vmax > 20 ? Math.pow(10, Math.floor(Math.log10(vmax))) : 5;
      g.append(u.svg('line', { x1: 14, x2: 14 + ref * arrow, y1: W - 14, y2: W - 14, stroke: 'var(--accent)', 'stroke-width': 1.6 }), u.svg('text', { x: 18 + ref * arrow, y: W - 10, 'font-size': 10, fill: 'var(--text-dim)' }, `${ref} nm`));
      mapBox.replaceChildren(g, u.el('p', { class: 'note' }, `${v.length} 個標記（${seen.size} 個場 × 4 角）。放大＝箭頭向外放射；旋轉＝繞中心打轉；平移＝全部同向。場內項會讓每個場四角的箭頭形成自己的小圖樣。`));
      // box-in-box schematic with a measured offset at one mark
      const m0 = v[0];
      const b = u.svg('svg', { viewBox: '0 0 260 200', class: 'svg-small', role: 'img', 'aria-label': 'box-in-box 標記與訊號' });
      const ox = Math.max(-12, Math.min(12, m0.dx)), oy = Math.max(-12, Math.min(12, m0.dy));
      b.append(u.svg('rect', { x: 50, y: 20, width: 120, height: 120, fill: 'none', stroke: 'var(--m-met-ln)', 'stroke-width': 10 }));
      b.append(u.svg('rect', { x: 85 + ox * 1.5, y: 55 - oy * 1.5, width: 50, height: 50, fill: 'var(--m-cu)', stroke: 'var(--m-cu-ln)' }));
      b.append(u.svg('text', { x: 110, y: 160, 'text-anchor': 'middle', 'font-size': 10.5, fill: 'var(--text-dim)' }, '外框：前層　內框：當層（偏移誇大 1.5×）'));
      b.append(u.svg('text', { x: 110, y: 178, 'text-anchor': 'middle', 'font-size': 9.5, fill: 'var(--text)', 'font-family': 'var(--fm)' }, `OV_x = 中心(內) − 中心(外) = ${m0.dx.toFixed(2)} nm`));
      b.append(u.svg('text', { x: 110, y: 194, 'text-anchor': 'middle', 'font-size': 9.5, fill: 'var(--text)', 'font-family': 'var(--fm)' }, `OV_y = ${m0.dy.toFixed(2)} nm`));
      boxBox.replaceChildren(b, u.el('p', { class: 'note' }, 'TIS（tool-induced shift）：光學不對稱讓機台本身產生偏移。把晶圓轉 180° 再量，真實疊對變號、TIS 不變：TIS = (OV₀ + OV₁₈₀)/2，真實值 = (OV₀ − OV₁₈₀)/2。'));
      // fit table
      const inj = { Tx: p.Tx + p.tis, Ty: p.Ty, Mwx: p.Mwx, Mwy: p.Mwy, Rw: p.Rw, Mfx: p.Mfx, Mfy: p.Mfy, Rf: p.Rf };
      const lab = { Tx: 'X 平移 (nm)', Ty: 'Y 平移 (nm)', Mwx: '晶圓放大 X (ppm)', Mwy: '晶圓放大 Y (ppm)', Rw: '晶圓旋轉 (µrad)', Mfx: '場內放大 X (ppm)', Mfy: '場內放大 Y (ppm)', Rf: '場內旋轉 (µrad)' };
      fitBox.replaceChildren(u.el('table', { class: 'f' }, u.el('thead', {}, u.el('tr', {}, u.el('th', {}, '項目'), u.el('th', {}, '注入（含應力、TIS）'), u.el('th', {}, '擬合'))),
        u.el('tbody', {}, ...Object.keys(lab).map((k) => u.el('tr', {}, u.el('td', {}, lab[k]), u.el('td', { class: 'm' }, inj[k].toFixed(3)), u.el('td', { class: 'm' }, fit.c[k].toFixed(3)))))),
        u.el('p', { class: 'note' }, `ppm × 位置(mm) = nm：1 ppm 的晶圓放大在 150 mm 處就是 150 nm。${magStress ? `目前 T9 應力貢獻 ${magStress.toFixed(2)} ppm。` : ''}${!e.tis180 && Math.abs(e.tis) > 0.05 ? ' TIS 沒去除：它會被擬合成 X 平移，曝光機會「修正」一個不存在的誤差。' : ''}`));
      const spec = 3; // nm, illustrative DRAM critical layer
      const ok = (q) => (q <= spec ? 'good' : q <= 1.5 * spec ? 'marginal' : 'reject');
      resBox.replaceChildren(V.kvGrid([['原始 |m|+3σ X', `${fit.raw.x.m3s.toFixed(2)} nm`], ['原始 |m|+3σ Y', `${fit.raw.y.m3s.toFixed(2)} nm`], ['殘差 |m|+3σ X', `${fit.resid.x.m3s.toFixed(2)} nm`], ['殘差 |m|+3σ Y', `${fit.resid.y.m3s.toFixed(2)} nm`]]),
        u.el('div', { class: 'row' }, V.chip(`修正前 ${Math.max(fit.raw.x.m3s, fit.raw.y.m3s) <= spec ? '合格' : '不合格'}`, ok(Math.max(fit.raw.x.m3s, fit.raw.y.m3s))), V.chip(`修正後（殘差）${Math.max(fit.resid.x.m3s, fit.resid.y.m3s) <= spec ? '合格' : '不合格'}`, ok(Math.max(fit.resid.x.m3s, fit.resid.y.m3s))),
          u.el('button', { type: 'button', onclick: () => S.setMeas('overlay', 'sObs', Math.max(fit.resid.x.sd, fit.resid.y.sd)) }, '把殘差 σ 送到 M6 的 SNC 對位')),
        u.el('p', { class: 'note' }, `規格示意 ${spec} nm（|m|+3σ）。線性項可由曝光機修正（回饋 APC）；殘差是隨機誤差與高階項，只能從製程或標記品質改善。M6 的「儲存節點接觸對位」項目使用這個 σ。`));
    }
    S.subscribe(draw);
  }
  root.DMS.t7 = { mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
