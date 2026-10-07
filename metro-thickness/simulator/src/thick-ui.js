/* DRAM Thickness Metro — shared UI for the thickness modules: SVG charts, sliders, CSV copy, chain cells. */
(function (root) {
  'use strict';
  const D = root.DMS;

  // ---------- generic line/scatter chart ----------
  // series: [{ pts: [[x,y],...], color, width, dash, label, dots, area }]
  // opts: { w, h, xLabel, yLabel, xTicks, yTicks, xFmt, yFmt, logY, hlines:[{y,label,color,dash}], vlines:[{x,label,color}], band:{y0,y1,color}, xMin,xMax,yMin,yMax, aria }
  function chart(series, o) {
    const u = D.ui;
    const hasLeg = series.some((q) => q.label);
    const W = o.w || 640, H = o.h || 240, L = o.left || 56, R = o.right || 16, T = o.top || (hasLeg ? 32 : 18), B = o.bottom || 38;
    const all = series.flatMap((s) => s.pts);
    const fy = o.logY ? (v) => Math.log10(Math.max(v, 1e-300)) : (v) => v;
    let xMin = o.xMin ?? Math.min(...all.map((p) => p[0])), xMax = o.xMax ?? Math.max(...all.map((p) => p[0]));
    let yMin = o.yMin ?? Math.min(...all.map((p) => fy(p[1]))), yMax = o.yMax ?? Math.max(...all.map((p) => fy(p[1])));
    for (const h of o.hlines || []) { yMin = Math.min(yMin, fy(h.y)); yMax = Math.max(yMax, fy(h.y)); }
    if (yMax === yMin) { yMax += 1; yMin -= 1; }
    const pad = (yMax - yMin) * 0.08; if (o.yMin == null) yMin -= pad; if (o.yMax == null) yMax += pad;
    if (xMax === xMin) xMax += 1;
    const X = (x) => L + ((x - xMin) / (xMax - xMin)) * (W - L - R);
    const Y = (y) => H - B - ((fy(y) - yMin) / (yMax - yMin)) * (H - T - B);
    const g = u.svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': o.aria || '' });
    const nice = (lo, hi, n) => { const step = Math.pow(10, Math.floor(Math.log10((hi - lo) / n))); const m = [1, 2, 2.5, 5, 10].find((k) => (hi - lo) / (k * step) <= n) * step; const out = []; for (let v = Math.ceil(lo / m) * m; v <= hi + 1e-12; v += m) out.push(+v.toPrecision(12)); return out; };
    const yt = o.yTicks || (o.logY ? nice(Math.ceil(yMin), Math.floor(yMax), 5).filter((v) => Number.isInteger(v)) : nice(yMin, yMax, 5));
    const xt = o.xTicks || nice(xMin, xMax, 6);
    if (o.band) g.append(u.svg('rect', { x: L, width: W - L - R, y: Y(o.band.y1), height: Math.max(Y(o.band.y0) - Y(o.band.y1), 0), fill: o.band.color || 'var(--accent-soft)' }));
    for (const v of yt) {
      const yy = o.logY ? H - B - ((v - yMin) / (yMax - yMin)) * (H - T - B) : Y(v);
      g.append(u.svg('line', { x1: L, x2: W - R, y1: yy, y2: yy, stroke: 'var(--border-soft)' }));
      g.append(u.svg('text', { x: L - 6, y: yy + 4, 'text-anchor': 'end', 'font-size': 10.5, 'font-family': 'var(--fm)', fill: 'var(--text-faint)' }, o.logY ? `1e${v}` : (o.yFmt ? o.yFmt(v) : String(v))));
    }
    for (const v of xt) {
      g.append(u.svg('line', { x1: X(v), x2: X(v), y1: H - B, y2: H - B + 4, stroke: 'var(--text-faint)' }));
      g.append(u.svg('text', { x: X(v), y: H - B + 16, 'text-anchor': 'middle', 'font-size': 10.5, 'font-family': 'var(--fm)', fill: 'var(--text-faint)' }, o.xFmt ? o.xFmt(v) : String(v)));
    }
    g.append(u.svg('line', { x1: L, x2: W - R, y1: H - B, y2: H - B, stroke: 'var(--text-dim)' }));
    if (o.xLabel) g.append(u.svg('text', { x: (L + W - R) / 2, y: H - 4, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--text-dim)' }, o.xLabel));
    if (o.yLabel) g.append(u.svg('text', { x: 12, y: (T + H - B) / 2, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--text-dim)', transform: `rotate(-90 12 ${(T + H - B) / 2})` }, o.yLabel));
    for (const h of o.hlines || []) {
      g.append(u.svg('line', { x1: L, x2: W - R, y1: Y(h.y), y2: Y(h.y), stroke: h.color || 'var(--text-dim)', 'stroke-dasharray': h.dash || '5 4', 'stroke-width': 1.2 }));
      if (h.label) g.append(u.svg('text', { x: W - R - 4, y: Y(h.y) - 4, 'text-anchor': 'end', 'font-size': 10.5, fill: 'var(--text-dim)' }, h.label));
    }
    for (const v of o.vlines || []) {
      g.append(u.svg('line', { x1: X(v.x), x2: X(v.x), y1: T, y2: H - B, stroke: v.color || 'var(--text-faint)', 'stroke-dasharray': v.dash || '3 3' }));
      if (v.label) g.append(u.svg('text', { x: X(v.x) + 4, y: T + 12, 'font-size': 10.5, fill: 'var(--text-dim)' }, v.label));
    }
    for (const s of series) {
      if (s.pts.length < 1) continue;
      if (s.area) {
        const d = `M${X(s.pts[0][0])},${H - B} L` + s.pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(' L') + ` L${X(s.pts.at(-1)[0])},${H - B} Z`;
        g.append(u.svg('path', { d, fill: s.color, opacity: 0.14 }));
      }
      if (!s.dotsOnly) g.append(u.svg('path', { d: 'M' + s.pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(' L'), fill: 'none', stroke: s.color, 'stroke-width': s.width || 2, 'stroke-dasharray': s.dash || null, 'stroke-linejoin': 'round' }));
      if (s.dots || s.dotsOnly) for (const p of s.pts) g.append(u.svg('circle', { cx: X(p[0]).toFixed(1), cy: Y(p[1]).toFixed(1), r: s.r || 3, fill: p[2] || s.color, stroke: 'var(--surface)', 'stroke-width': 1 }));
    }
    if (series.some((s) => s.label)) {
      let lx = L + 6;
      const leg = u.svg('g');
      for (const s of series.filter((q) => q.label)) {
        leg.append(u.svg('line', { x1: lx, x2: lx + 16, y1: T - 18, y2: T - 18, stroke: s.color, 'stroke-width': 2.4, 'stroke-dasharray': s.dash || null }));
        leg.append(u.svg('text', { x: lx + 20, y: T - 14, 'font-size': 10.5, fill: 'var(--text-dim)' }, s.label));
        lx += 30 + s.label.length * 6.2;
      }
      g.append(leg);
    }
    g.X = X; g.Y = Y;
    return g;
  }

  function num(v, d = 3) { return Number.isFinite(v) ? v.toFixed(d) : '—'; }
  function kvGrid(pairs) {
    const u = D.ui;
    return u.el('div', { class: 'kv' }, ...pairs.map(([k, v, cls]) => u.el('div', {}, u.el('span', { class: 'k' }, k), u.el('span', { class: 'v' + (cls ? ' ' + cls : '') }, v))));
  }
  // compact slider: {key, zh, en, unit, min, max, step, tier, src}
  function knob(def, value, onInput) { return D.ui.slider({ ...def, tier: def.tier || 'red', src: def.src || '示意' }, value, onInput); }
  function seg(options, current, onPick, label) {
    const u = D.ui;
    const btns = {};
    const s = u.el('div', { class: 'seg', role: 'group', 'aria-label': label || '' }, ...options.map(([k, lab]) => (btns[k] = u.el('button', { type: 'button', onclick: () => onPick(k) }, lab))));
    s.sync = (cur) => { for (const [k, b] of Object.entries(btns)) b.classList.toggle('on', String(k) === String(cur)); };
    s.sync(current);
    return s;
  }
  function copyBtn(label, getText) {
    const u = D.ui;
    const note = u.el('span', { class: 'note', role: 'status' });
    const b = u.el('button', { type: 'button', onclick: async () => {
      const t = getText();
      try { await navigator.clipboard.writeText(t); note.textContent = `已複製 ${t.split('\n').length - 1} 列（CSV）`; }
      catch (e) { const ta = u.el('textarea', { class: 'csvfallback', rows: 6 }); ta.value = t; note.replaceChildren('無法自動複製，請全選下方文字：', ta); ta.select(); }
    } }, label);
    return u.el('span', { class: 'copy' }, b, note);
  }
  function chip(text, kind) { return D.ui.el('span', { class: `band ${kind}` }, text); }

  // ---------- chain bar: ZrO2 true vs reported ----------
  const thickChain = {
    mount(sel) {
      const u = D.ui, host = document.querySelector(sel).querySelector('.chain');
      const v = u.el('span', { class: 'v' }), unit = u.el('span', { class: 'u' }, 'nm'), d = u.el('span', { class: 'd' });
      const cell = u.el('div', { class: 'cc', role: 'listitem', title: 'ZrO₂ 真實膜厚與量測讀值' }, u.el('span', { class: 'k' }, 'ZrO₂ 真實｜讀值'), u.el('div', {}, v, unit), d);
      host.insertBefore(cell, host.children[1]);
      D.state.subscribe((s) => {
        const i = s.thickInfo;
        v.textContent = `${i.tTrue.toFixed(2)}｜${i.reported.toFixed(2)}`;
        const parts = [];
        if (Math.abs(i.metroBias) > 0.005) parts.push(`量測偏差 ${i.metroBias > 0 ? '+' : ''}${i.metroBias.toFixed(2)}`);
        if (i.bottom < 0.995) parts.push(`孔底 ${Math.round(i.bottom * 100)}%`);
        if (s.thick.metro.apcOn) parts.push('APC');
        d.textContent = parts.join('，');
        d.className = 'd' + (Math.abs(i.metroBias) > 0.05 || i.bottom < 0.9 ? ' bad' : '');
      });
    },
  };

  const api = { chart, num, kvGrid, knob, seg, copyBtn, chip };
  D.tui = api;
  D.thickChain = thickChain;
})(typeof globalThis !== 'undefined' ? globalThis : this);
