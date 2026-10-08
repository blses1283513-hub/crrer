/* DRAM Thickness Metro — T6 CD-SEM: secondary-electron linescan, edge-detection threshold,
   line/space vs contact hole, pattern recognition score, resist shrinkage from repeated scans. */
(function (root) {
  'use strict';
  const D = root.DMS;
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui, X = D.ext;
    const K = [
      ['topCD', '真實頂部 CD', 'top CD', 'nm', 15, 60, 0.5], ['h', '高度／深度', 'height', 'nm', 20, 150, 1], ['swa', '側壁角 SWA', 'sidewall angle', '°', 78, 90, 0.5],
      ['beam', '電子束尺寸 σ', 'beam size', 'nm', 0.5, 6, 0.1], ['frames', '平均影格數', 'frames', '', 1, 64, 1], ['thr', '邊緣閾值', 'edge threshold', '%', 10, 90, 1], ['scans', '同一點重複量測次數', 'repeat scans', '次', 1, 20, 1],
    ];
    const sl = {};
    K.forEach(([k, zh, en, unit, mn, mx, st]) => { sl[k] = V.knob({ key: k, zh, en, unit, min: mn, max: mx, step: st, tier: 'red', src: '示意' }, 0, (v) => S.setExt({ sem: { [k]: st >= 1 ? Math.round(v) : v } })); });
    const typeSeg = V.seg([[false, '線／間距 line/space'], [true, '接觸孔 contact hole']], false, (k) => S.setExt({ sem: { hole: k === 'true' } }), '圖形');
    const matSeg = V.seg([['resist', '光阻（會縮）'], ['hard', '硬罩／蝕刻後']], 'resist', (k) => S.setExt({ sem: { mat: k } }), '材料');
    const lsBox = u.el('div'), thrBox = u.el('div'), kv = u.el('div'), physBox = u.el('div');
    host.append(
      u.el('h2', { id: 'h-t6' }, 'T6 CD-SEM ', u.el('span', { class: 'en' }, 'secondary electrons · edge detection · pattern recognition')),
      u.el('p', { class: 'sub' }, 'CD-SEM 用低能量一次電子（約 300–800 eV）掃過圖形，收集樣品表面逸出的二次電子（SE，<50 eV）。側壁傾斜處二次電子逸出較多（正割定律），邊緣特別亮（edge bloom），所以影像亮度輪廓不是幾何輪廓——CD 是「演算法在某個閾值找到的邊」。'),
      u.el('div', { class: 'grid2' }, u.el('div', {}, u.el('div', { class: 'row' }, typeSeg, matSeg), ...K.map(([k]) => sl[k])), u.el('div', {}, physBox, kv)),
      u.el('div', { class: 'grid2', style: 'margin-top:10px' }, u.el('div', {}, u.el('h4', { class: 'grp' }, '二次電子線掃描 linescan'), lsBox), u.el('div', {}, u.el('h4', { class: 'grp' }, '量到的 CD 對閾值'), thrBox)));
    // detector schematic (static)
    const d = u.svg('svg', { viewBox: '0 0 300 170', class: 'svg-small', role: 'img', 'aria-label': 'CD-SEM 偵測：一次電子束、樣品、二次電子、收集器' });
    d.append(u.svg('line', { x1: 150, y1: 6, x2: 150, y2: 100, stroke: 'var(--accent)', 'stroke-width': 3 }), u.svg('text', { x: 156, y: 22, 'font-size': 10.5, fill: 'var(--text-dim)' }, '一次電子 PE（低 kV）'));
    d.append(u.svg('path', { d: 'M90,100 L130,100 L138,70 L162,70 L170,100 L210,100 L210,130 L90,130 Z', fill: 'var(--m-poly)', stroke: 'var(--m-poly-ln)' }));
    for (const [x2, y2] of [[60, 55], [70, 40], [240, 50], [228, 36]]) d.append(u.svg('path', { d: `M150,98 Q${(150 + x2) / 2},${y2 + 30} ${x2},${y2}`, fill: 'none', stroke: 'var(--leak)', 'stroke-width': 1.3, 'stroke-dasharray': '3 2' }));
    d.append(u.svg('rect', { x: 22, y: 30, width: 40, height: 20, rx: 3, fill: 'var(--surface-3)', stroke: 'var(--text-dim)' }), u.svg('text', { x: 42, y: 44, 'text-anchor': 'middle', 'font-size': 9.5, fill: 'var(--text)' }, '偵測器'));
    d.append(u.svg('text', { x: 20, y: 70, 'font-size': 9.5, fill: 'var(--text-dim)' }, '收集柵 +偏壓'), u.svg('text', { x: 196, y: 30, 'font-size': 9.5, fill: 'var(--leak)' }, '二次電子 SE'));
    d.append(u.svg('text', { x: 150, y: 150, 'text-anchor': 'middle', 'font-size': 10, fill: 'var(--text-dim)' }, '收集柵加正偏壓把低能 SE 拉進偵測器（Everhart–Thornley／in-lens）'));
    physBox.replaceChildren(d);
    let template = null;

    function draw(s) {
      const e = s.ext.sem;
      K.forEach(([k]) => { if (!sl[k].contains(document.activeElement)) sl[k].sync(e[k]); });
      typeSeg.sync(e.hole); matSeg.sync(e.mat);
      // resist shrinkage: CD shrinks with accumulated dose (repeat scans); saturating exponential
      const shrink = e.mat === 'resist' ? 0.06 * e.topCD * (1 - Math.exp(-(e.scans - 1) / 6)) : 0;
      const g = { topCD: e.topCD - shrink, h: e.h, swa: e.swa, beam: e.beam, frames: e.frames, hole: e.hole };
      const ls = X.linescan(g, 31 + e.scans);
      const foot = e.h / Math.tan((e.swa * Math.PI) / 180);
      const trueTop = e.topCD, trueBot = e.hole ? Math.max(e.topCD - 2 * foot, 0) : e.topCD + 2 * foot;
      const cd = X.cdThreshold(ls, e.thr / 100);
      if (!template || template.hole !== e.hole) template = { hole: e.hole, y: X.linescan({ topCD: 30, h: 60, swa: 87, beam: 2, frames: 64, hole: e.hole }, 1).y };
      const pr = X.prScore(template.y, ls.y);
      lsBox.replaceChildren(V.chart([{ pts: ls.x.map((x, i) => [x, ls.y[i]]), color: 'var(--accent)', width: 1.3, label: 'SE 訊號' }],
        { h: 220, xLabel: '位置 (nm)', yLabel: 'SE 強度（相對）', vlines: [{ x: -cd / 2, label: `${e.thr}%`, color: 'var(--sig)' }, { x: cd / 2, color: 'var(--sig)' }, { x: -trueTop / 2, color: 'var(--text-faint)', dash: '2 2' }, { x: trueTop / 2, color: 'var(--text-faint)', dash: '2 2' }], xFmt: (v) => v.toFixed(0), yFmt: (v) => v.toFixed(1), aria: '二次電子線掃描' }),
        u.el('p', { class: 'note' }, `紅線：${e.thr}% 閾值找到的邊；灰虛線：真實頂部邊緣。${e.hole ? '接觸孔：底部的二次電子逃不出來而偏暗，孔越深越暗——深孔的底部 CD 很難用 SEM 量。' : '邊緣亮峰（edge bloom）是二次電子從頂角兩面逸出。'}`));
      const ths = []; for (let t = 10; t <= 90; t += 5) ths.push([t, X.cdThreshold(ls, t / 100)]);
      thrBox.replaceChildren(V.chart([{ pts: ths, color: 'var(--accent)', dots: true, width: 1.5, label: '量到的 CD' }], { h: 220, xLabel: '閾值 (%)', yLabel: 'CD (nm)', hlines: [{ y: trueTop, label: '真實頂部', color: 'var(--ok)' }, { y: trueBot, label: '真實底部', color: 'var(--leak)' }], yFmt: (v) => v.toFixed(0), aria: 'CD 對閾值' }),
        u.el('p', { class: 'note' }, '同一個影像，閾值不同 CD 就不同：閾值越低，找到的邊越往外（電子束模糊把基線端拉寬）；閾值越高越靠近亮峰（側壁上緣）。哪個閾值對應真實頂部或底部 CD，必須用參考量測（TEM、AFM）校正——T-sigma 法就是在找這個對應。閾值與演算法是配方的一部分，跨機台、跨世代必須固定；文獻指出閾值法可造成約 10% 的線寬非線性（Hershey 1993）。'));
      const err = cd - trueTop;
      kv.replaceChildren(V.kvGrid([['量到的 CD', `${cd.toFixed(1)} nm`], ['真實頂部／底部', `${trueTop.toFixed(1)}／${trueBot.toFixed(1)} nm`], ['相對頂部偏差', `${err >= 0 ? '+' : ''}${err.toFixed(1)} nm`], ['光阻縮減（重複 ' + e.scans + ' 次）', `${shrink.toFixed(2)} nm`, shrink > 0.5 ? 'badtxt' : ''], ['圖形辨識 PR 分數', pr.toFixed(3), pr < 0.7 ? 'badtxt' : 'goodtxt']]),
        u.el('div', { class: 'row' }, V.chip(pr >= 0.7 ? 'PR 通過' : 'PR 失敗：跳點或量錯位置', pr >= 0.7 ? 'good' : 'reject'),
          u.el('button', { type: 'button', onclick: () => S.setDrift({ key: 'capD', meanShift: +((err / trueTop) * 100).toFixed(2), shiftUnit: '%', sigmaScale: 1 }) }, '把 CD 偏差（%）送到 M6 電容外徑')),
        u.el('p', { class: 'note' }, '圖形辨識（PR）：機台先用低倍影像和配方裡存的樣板做相關比對，找到量測點再放大。製程讓影像外觀改變（側壁角、對比、充電）時分數下降；低於門檻就跳點，或更糟——對到相鄰的特徵。光阻在電子束下會收縮，同一點重複量 CD 會一直變小：量具研究（GR&R）要用不同點，或改用硬罩後量測。'));
    }
    S.subscribe(draw);
  }
  root.DMS.t6 = { mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
