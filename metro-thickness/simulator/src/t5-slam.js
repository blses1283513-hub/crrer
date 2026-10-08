/* DRAM Thickness Metro — T5 SLAM: scribe line area marks. Clickable scribe-line layout; every mark
   explains what is measured there and checks the measurement spot against the pad size. */
(function (root) {
  'use strict';
  const D = root.DMS;
  // spot footprints (µm): [along x, along y]; SE elongates by 1/cos(AOI) in the plane of incidence
  const MARKS = {
    film: { zh: '膜厚量測墊 film pad', go: '#t1', tech: '橢偏 SE（65°）／反射光譜', spot: () => [25, 25 / Math.cos((65 * Math.PI) / 180)], what: '平坦的整面膜（blanket），量 t、n、k。DRAM 的 ZrO₂ 也常在這裡或監控片上量。',
      pit: ['斜入射使光斑在入射面方向拉長 1/cos θ（65° 時約 2.4 倍）：25 µm 光斑變成約 59 µm，比 50 µm 量測墊還長，邊緣圖形會混進訊號。', '量測墊是大面積平坦區：CMP 碟陷、沉積負載效應都和陣列區不同，墊上的厚度不等於陣列裡的厚度。'] },
    ocd: { zh: 'OCD 光柵 grating', go: '#t8', tech: '散射量測 OCD（光譜橢偏或正入射偏振反射）', spot: () => [30, 30], what: '週期性的線／間距（line/space）或孔陣列，量 CD、深度、側壁角（SWA）。比 CD-SEM 快、便宜、非破壞，且能看到深度。',
      pit: ['光柵必須比光斑大且週期完整：光斑落到光柵外會改變光譜。', '模型要描述真實剖面（SWA、底部圓角、硬罩殘留），否則參數會互相補償。'] },
    sem: { zh: 'CD-SEM 標靶 line/space · contact hole', go: '#t6', tech: 'CD-SEM（低能量一次電子、二次電子成像）', spot: () => [1, 1], what: '線、間距與接觸孔的頂部 CD；靠圖形辨識（PR）找到同一個位置。',
      pit: ['電子束會縮減光阻（shrinkage）並造成充電：同一點不要重複量。', '圖形辨識若找錯特徵，量到的是別的東西——看 PR 分數。'] },
    ov: { zh: '疊對標記 overlay box-in-box', go: '#t7', tech: '影像式疊對（IBO，box-in-box）／繞射式（DBO）', spot: () => [40, 40], what: '外框為前層、內框為當層；兩框中心的差就是疊對誤差。每個曝光場四角各一組，用來分出晶圓項（平移、旋轉、放大）與場內項。',
      pit: ['機台誘發偏移 TIS：晶圓轉 0°／180° 各量一次取平均去除。', '標記本身被製程破壞（CMP、沉積不對稱）會造成假的疊對。'] },
    align: { zh: '對準標記 alignment mark', go: '#t7', tech: '曝光機對準感測器', spot: () => [60, 30], what: '曝光機用來定位晶圓；它的誤差直接出現在疊對的平移、旋轉、放大項。', pit: ['對準標記與疊對標記受到相同製程影響時，誤差可能互相抵消而看不見。'] },
    stress: { zh: '整片晶圓（應力）', go: '#t9', tech: '雷射掃描晶圓曲率', spot: () => [0, 0], what: '應力不量在量測墊上，而是量整片晶圓的曲率：沉積前、後各量一次，取曲率差，用 Stoney 方程換算。', pit: ['只量沉積後一次：晶圓原本的翹曲會被當成膜的應力。'] },
  };
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui;
    const padSl = V.knob({ key: 'pad', zh: '量測墊尺寸', en: 'pad size', unit: 'µm', min: 30, max: 100, step: 1, tier: 'red', src: '示意；常見 40–60 µm' }, 50, (v) => S.setExt({ slam: { pad: Math.round(v) } }));
    const scribeSl = V.knob({ key: 'scribe', zh: '切割道寬度', en: 'scribe width', unit: 'µm', min: 40, max: 120, step: 1, tier: 'red', src: '示意；先進製程約 60–80 µm' }, 80, (v) => S.setExt({ slam: { scribe: Math.round(v) } }));
    const svgBox = u.el('div', { class: 'svgscroll' }), info = u.el('div', { class: 'card' }), fitTable = u.el('div');
    host.append(
      u.el('h2', { id: 'h-t5' }, 'T5 SLAM 切割道量測標記 ', u.el('span', { class: 'en' }, 'scribe line area marks')),
      u.el('p', { class: 'sub' }, '產品晶粒裡的結構太小、太密，量測機台多半量的是切割道（scribe line）上專門放的標記：膜厚墊、OCD 光柵、CD-SEM 標靶、疊對框、對準標記。點一個標記看它量什麼、用什麼機台、有什麼陷阱，並檢查光斑放不放得進去。'),
      u.el('div', { class: 'grid2' }, u.el('div', {}, svgBox, padSl, scribeSl), u.el('div', {}, info, fitTable)));

    function draw(s) {
      const e = s.ext.slam, pad = e.pad, W = e.scribe, sel2 = e.focus;
      const sc = 2.2, X0 = 20, Y0 = 70; // px per µm
      const g = u.svg('svg', { viewBox: '0 0 640 300', role: 'img', 'aria-label': '切割道上的量測標記配置' });
      // dies above and below the scribe
      g.append(u.svg('rect', { x: 0, y: 0, width: 640, height: Y0, fill: 'var(--m-si)', opacity: 0.55 }), u.svg('rect', { x: 0, y: Y0 + W * sc, width: 640, height: 300, fill: 'var(--m-si)', opacity: 0.55 }));
      for (let i = 0; i < 40; i++) g.append(u.svg('line', { x1: i * 16, x2: i * 16 + 8, y1: Y0 - 14, y2: Y0 - 14, stroke: 'var(--m-si-ln)', 'stroke-width': 3 }));
      g.append(u.svg('text', { x: 8, y: 18, 'font-size': 11, fill: 'var(--text)' }, '晶粒（陣列區）'), u.svg('text', { x: 8, y: Y0 + 14, 'font-size': 11, fill: 'var(--text-dim)' }, `切割道 ${W} µm`));
      const cy = Y0 + (W * sc) / 2;
      const items = [];
      let x = X0 + 40;
      const box = (id, w, h, draw2) => {
        const gx = u.svg('g', { class: 'slam-mark' + (sel2 === id ? ' on' : ''), role: 'button', tabindex: 0, 'aria-label': MARKS[id].zh });
        const px = x, py = cy - (h * sc) / 2;
        gx.append(u.svg('rect', { x: px - 4, y: py - 4, width: w * sc + 8, height: h * sc + 8, fill: 'transparent', stroke: sel2 === id ? 'var(--sig)' : 'transparent', 'stroke-width': 2 }));
        draw2(gx, px, py, w * sc, h * sc);
        gx.addEventListener('click', () => S.setExt({ slam: { focus: id } }));
        gx.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); S.setExt({ slam: { focus: id } }); } });
        g.append(gx); items.push(id);
        x += w * sc + 22;
        return [px, py];
      };
      const p = Math.min(pad, W - 6);
      box('film', p, p, (gx, px, py, w, h) => gx.append(u.svg('rect', { x: px, y: py, width: w, height: h, fill: 'var(--m-hik)', stroke: 'var(--m-hik-ln)' })));
      box('ocd', p, p, (gx, px, py, w, h) => { gx.append(u.svg('rect', { x: px, y: py, width: w, height: h, fill: 'var(--surface)', stroke: 'var(--m-ox-ln)' })); for (let k = 0; k < w; k += 4) gx.append(u.svg('line', { x1: px + k, x2: px + k, y1: py, y2: py + h, stroke: 'var(--m-ox-ln)', 'stroke-width': 1.6 })); });
      box('sem', 20, 20, (gx, px, py, w, h) => { gx.append(u.svg('rect', { x: px, y: py, width: w, height: h / 2 - 2, fill: 'var(--surface)', stroke: 'var(--m-poly-ln)' })); for (let k = 2; k < w; k += 5) gx.append(u.svg('line', { x1: px + k, x2: px + k, y1: py, y2: py + h / 2 - 2, stroke: 'var(--m-poly-ln)', 'stroke-width': 2 })); for (let a = 0; a < 4; a++) for (let b = 0; b < 2; b++) gx.append(u.svg('circle', { cx: px + 5 + a * 10, cy: py + h / 2 + 6 + b * 10, r: 3, fill: 'var(--m-poly)', stroke: 'var(--m-poly-ln)' })); });
      box('ov', 28, 28, (gx, px, py, w, h) => { gx.append(u.svg('rect', { x: px, y: py, width: w, height: h, fill: 'none', stroke: 'var(--m-met-ln)', 'stroke-width': 5 }), u.svg('rect', { x: px + w * 0.3 + 2, y: py + h * 0.3 - 1, width: w * 0.4, height: h * 0.4, fill: 'var(--m-cu)', stroke: 'var(--m-cu-ln)' })); });
      box('align', 40, 20, (gx, px, py, w, h) => { for (let k = 0; k < 6; k++) gx.append(u.svg('rect', { x: px + k * (w / 6), y: py, width: w / 12, height: h, fill: 'var(--m-met)', stroke: 'var(--m-met-ln)' })); });
      // spot footprint of the selected mark
      const m = MARKS[sel2];
      if (m && sel2 !== 'stress') {
        const [sx, sy] = m.spot();
        const idx = items.indexOf(sel2);
        g.append(u.svg('text', { x: 20, y: 290, 'font-size': 11, fill: 'var(--text-dim)' }, `虛線＝${m.tech.split('（')[0]} 光斑 ${sx.toFixed(0)}×${sy.toFixed(0)} µm（${sel2 === 'film' ? '橢偏 65° 斜入射拉長' : '示意'}）`));
        const ref = g.querySelectorAll('.slam-mark')[idx].querySelector('rect');
        const rx = +ref.getAttribute('x') + 4 + (+ref.getAttribute('width') - 8) / 2, ry = cy;
        g.append(u.svg('ellipse', { cx: rx, cy: ry, rx: (sx * sc) / 2, ry: (sy * sc) / 2, fill: 'none', stroke: 'var(--sig)', 'stroke-width': 1.6, 'stroke-dasharray': '4 3' }));
      }
      const wf = u.svg('g', { class: 'slam-mark' + (sel2 === 'stress' ? ' on' : ''), role: 'button', tabindex: 0, 'aria-label': MARKS.stress.zh });
      wf.append(u.svg('rect', { x: 520, y: 248, width: 110, height: 40, rx: 4, fill: 'var(--surface-3)', stroke: sel2 === 'stress' ? 'var(--sig)' : 'var(--border)' }), u.svg('text', { x: 575, y: 272, 'text-anchor': 'middle', 'font-size': 11, fill: 'var(--text)' }, '整片晶圓：應力'));
      wf.addEventListener('click', () => S.setExt({ slam: { focus: 'stress' } }));
      g.append(wf);
      svgBox.replaceChildren(g);

      info.replaceChildren(u.el('h3', {}, m.zh), V.kvGrid([['量測方法', m.tech], ['量什麼', m.what]]), u.el('ul', { class: 'pit' }, ...m.pit.map((t) => u.el('li', {}, t))), u.el('p', {}, u.el('a', { href: m.go }, '到對應模組 →')));
      const rows = Object.entries(MARKS).filter(([k]) => k !== 'stress' && k !== 'align').map(([k, mm]) => {
        const [sx, sy] = mm.spot(); const size = k === 'sem' ? 20 : k === 'ov' ? 28 : pad;
        const okFit = Math.max(sx, sy) + 10 <= size;
        return u.el('tr', {}, u.el('td', {}, mm.zh.split(' ')[0]), u.el('td', { class: 'm' }, `${sx.toFixed(0)}×${sy.toFixed(0)}`), u.el('td', { class: 'm' }, `${size}`), u.el('td', {}, V.chip(okFit ? '放得下' : '光斑溢出', okFit ? 'good' : 'reject')));
      });
      fitTable.replaceChildren(u.el('h4', { class: 'grp' }, '光斑 vs 量測墊（含 ±5 µm 定位誤差）'), u.el('table', { class: 'f' }, u.el('thead', {}, u.el('tr', {}, u.el('th', {}, '標記'), u.el('th', {}, '光斑 µm'), u.el('th', {}, '墊 µm'), u.el('th', {}, ''))), u.el('tbody', {}, ...rows)));
      if (D.terms) D.terms.wrap(info);
    }
    S.subscribe((s) => { if (!padSl.contains(document.activeElement)) padSl.sync(s.ext.slam.pad); if (!scribeSl.contains(document.activeElement)) scribeSl.sync(s.ext.slam.scribe); draw(s); });
  }
  root.DMS.t5 = { mount, MARKS };
})(typeof globalThis !== 'undefined' ? globalThis : this);
