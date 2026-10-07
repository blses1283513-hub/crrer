/* DRAM Thickness Metro — T2 ALD wafer map: process knobs, true map vs sampled sites, uniformity,
   step coverage in the capacitor hole (2D + 3D), leakage/fail-bit vs thickness, chip-level risk map. */
(function (root) {
  'use strict';
  const D = root.DMS;

  // diverging blue <-> red around zero, neutral grey midpoint (dataviz reference poles)
  function divColor(t) { // t in [-1,1]
    const neg = [42, 120, 214], pos = [227, 73, 72], mid = [150, 150, 150];
    const a = Math.min(Math.abs(t), 1), c = t < 0 ? neg : pos;
    return `rgb(${Math.round(mid[0] + (c[0] - mid[0]) * a)},${Math.round(mid[1] + (c[1] - mid[1]) * a)},${Math.round(mid[2] + (c[2] - mid[2]) * a)})`;
  }
  // sequential: light -> dark blue (fails), log scale
  const SEQ = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b'];
  const seqColor = (t) => SEQ[Math.max(0, Math.min(SEQ.length - 1, Math.round(t * (SEQ.length - 1))))];

  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, T = D.thick, V = D.tui, E = D.engine, P = D.params;
    const REF = E.referenceQV(P.DEFAULTS);
    const O = 'orange', R = 'red';
    const knobs = {};
    const KN = [
      { key: 'dN', zh: '循環數變化', en: 'Δ cycles', unit: 'cyc', min: -15, max: 15, step: 1, tier: R, src: '示意；ALD 厚度 ≈ N·GPC', path: ['ald', 'dN'] },
      { key: 'gpc', zh: 'GPC 每循環成長', en: 'growth per cycle', unit: 'nm', min: 0.05, max: 0.15, step: 0.005, tier: O, src: 'ALD 典型 0.05–0.15 nm／循環（Kessels 2025 綜述，經 Gonsalves 2026 引用）', path: ['ald', 'gpc'] },
      { key: 'T', zh: '晶圓溫度', en: 'wafer temperature', unit: '°C', min: 200, max: 350, step: 1, tier: R, src: 'ALD 窗口 250–300 °C 為示意', path: ['ald', 'T'] },
      { key: 'purge', zh: '吹淨時間（相對）', en: 'purge (relative)', unit: '×', min: 0.3, max: 1, step: 0.05, tier: R, src: '<1 時前驅物混合 → 寄生 CVD（示意）', path: ['ald', 'purge'] },
      { key: 'exposure', zh: '前驅物曝氣量（相對）', en: 'precursor exposure', unit: '×', min: 0.3, max: 1.5, step: 0.05, tier: O, src: '穿透深度 ∝ √(曝氣量/GPC)（Gonsalves 2026）；比例常數示意', path: ['ald', 'exposure'] },
      { key: 'dome', zh: '中心厚／邊緣厚', en: 'dome (+) / bowl (−)', unit: '%', min: -6, max: 6, step: 0.1, tier: R, src: '示意：噴頭、加熱分區', path: ['ald', 'dome'] },
      { key: 'tilt', zh: '左右傾斜', en: 'tilt', unit: '%', min: -4, max: 4, step: 0.1, tier: R, src: '示意：進氣側、晶圓偏心', path: ['ald', 'tilt'] },
      { key: 'edge', zh: '邊緣環', en: 'edge ring', unit: '%', min: -6, max: 6, step: 0.1, tier: R, src: '示意：edge ring、抽氣', path: ['ald', 'edge'] },
    ];
    const setPath = (path, v) => S.setThick({ [path[0]]: { [path[1]]: v } });
    const getPath = (s, path) => s.thick[path[0]][path[1]];
    const knobBox = u.el('div', {}, u.el('h4', { class: 'grp' }, 'ALD 製程旋鈕 process knobs'), ...KN.map((k) => (knobs[k.key] = V.knob(k, getPath(S.snapshot(), k.path), (v) => setPath(k.path, k.step >= 1 ? Math.round(v) : v)))));
    const planSeg = V.seg(Object.entries(T.PLANS).map(([k, p]) => [k, p.zh]), 'p49', (k) => S.setT3({ plan: k }), '取樣計畫');
    const mapCanvas = u.el('canvas', { class: 'wafer', width: 360, height: 360, role: 'img', 'aria-label': 'ZrO₂ 真實膜厚晶圓圖與取樣點' });
    const mapStats = u.el('div'), mapLegend = u.el('div', { class: 'legend' });
    const riskCanvas = u.el('canvas', { class: 'wafer', width: 360, height: 360, role: 'img', 'aria-label': '晶片 fail bit 風險圖' });
    const riskStats = u.el('div'), riskLegend = u.el('div', { class: 'legend' });
    const covBox = u.el('div'), covKv = u.el('div'), three = u.el('div', { class: 'three' }), threeNote = u.el('p', { class: 'note' });
    const failBox = u.el('div'), leakBox = u.el('div');
    let csvRows = [];

    host.append(
      u.el('h2', { id: 'h-t2' }, 'T2 ALD 晶圓圖與孔內覆蓋 ', u.el('span', { class: 'en' }, 'ALD wafer map · step coverage · fail-bit map')),
      u.el('p', { class: 'sub' }, '左邊轉製程旋鈕，看真實的晶圓圖（色塊）與取樣點（圓點）各看到什麼。下面看同一層膜進到 48:1 的電容孔裡之後，孔底還剩多少——監控片量的是平面，孔底的膜沒有人量得到。'),
      u.el('div', { class: 'grid-t2' }, knobBox,
        u.el('div', {}, u.el('div', { class: 'row' }, u.el('h4', { class: 'grp', style: 'margin:0' }, '真實晶圓圖＋取樣點'), planSeg), mapCanvas, mapLegend),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '取樣看到的 vs 真實'), mapStats, V.copyBtn('複製量測點 CSV', () => csvRows.join('\n')))),
      u.el('div', { class: 'grid2', style: 'margin-top:16px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, '孔內膜厚分布 step coverage（B1）'), covBox, covKv),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '3D 電容剖面（可拖曳旋轉）'), three, threeNote)),
      u.el('div', { class: 'grid2', style: 'margin-top:16px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, 'fail bit 對 ZrO₂ 厚度（B2：規格為何有上下限）'), failBox),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '介電層漏電對厚度'), leakBox)),
      u.el('div', { class: 'grid2', style: 'margin-top:16px' },
        u.el('div', {}, u.el('h4', { class: 'grp' }, '晶片 fail bit 風險圖（同一片晶圓）'), riskCanvas, riskLegend),
        u.el('div', {}, u.el('h4', { class: 'grp' }, '讀圖'), riskStats)));

    // ---------- drawing helpers ----------
    function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || '#888'; }
    function drawWafer(cv, valueAt, colorOf, sites) {
      const ctx = cv.getContext('2d'), W = cv.width, H = cv.height, R = W / 2 - 6, cx = W / 2, cy = H / 2;
      ctx.clearRect(0, 0, W, H);
      const n = 72, cell = (2 * R) / n;
      for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
        const px = -R + (i + 0.5) * cell, py = -R + (j + 0.5) * cell;
        if (px * px + py * py > R * R) continue;
        const x = (px / R) * 150, y = (-py / R) * 150;
        ctx.fillStyle = colorOf(valueAt(x, y));
        ctx.fillRect(cx + px - cell / 2, cy + py - cell / 2, cell + 0.6, cell + 0.6);
      }
      ctx.strokeStyle = css('--text-dim'); ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.stroke();
      ctx.fillStyle = css('--surface'); ctx.beginPath(); ctx.arc(cx, cy + R, 5, 0, 2 * Math.PI); ctx.fill(); // notch
      for (const [x, y] of sites || []) {
        ctx.beginPath(); ctx.arc(cx + (x / 150) * R, cy - (y / 150) * R, 4.2, 0, 2 * Math.PI);
        ctx.fillStyle = css('--surface'); ctx.fill(); ctx.lineWidth = 1.6; ctx.strokeStyle = css('--text'); ctx.stroke();
      }
    }
    function legend(box, stops, labels) {
      box.replaceChildren(u.el('span', { class: 'ramp', style: `background:linear-gradient(90deg,${stops.join(',')})` }), u.el('span', { class: 'note' }, labels));
    }

    // ---------- 3D capacitor (three.js r128 if available) ----------
    let three3 = null;
    function initThree() {
      if (three3 || !root.THREE) return !!three3;
      const TH = root.THREE;
      const w = Math.min(three.clientWidth || 420, 520), h = 300;
      const renderer = new TH.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setPixelRatio(Math.min(root.devicePixelRatio || 1, 2)); renderer.setSize(w, h);
      const scene = new TH.Scene(), cam = new TH.PerspectiveCamera(35, w / h, 0.1, 100);
      cam.position.set(0, 0.8, 12); cam.lookAt(0, 0, 0);
      scene.add(new TH.AmbientLight(0xffffff, 0.75)); const dl = new TH.DirectionalLight(0xffffff, 0.6); dl.position.set(3, 5, 6); scene.add(dl);
      const grp = new TH.Group(); scene.add(grp);
      three.replaceChildren(renderer.domElement);
      let drag = null;
      renderer.domElement.addEventListener('pointerdown', (e) => { drag = [e.clientX, e.clientY, grp.rotation.y, grp.rotation.x]; renderer.domElement.setPointerCapture(e.pointerId); });
      renderer.domElement.addEventListener('pointermove', (e) => { if (!drag) return; grp.rotation.y = drag[2] + (e.clientX - drag[0]) * 0.01; grp.rotation.x = Math.max(-0.8, Math.min(0.8, drag[3] + (e.clientY - drag[1]) * 0.01)); renderer.render(scene, cam); });
      renderer.domElement.addEventListener('pointerup', () => { drag = null; });
      renderer.domElement.setAttribute('aria-label', '3D 電容剖面，顏色為孔內各深度的 ZrO₂ 厚度');
      three3 = { TH, renderer, scene, cam, grp };
      return true;
    }
    function draw3D(info) {
      if (!initThree()) { three.replaceChildren(u.el('div', { class: 'three-off' }, '3D 檢視需要載入 three.js；目前無法載入，請看左側 2D 剖面。')); return; }
      const { TH, renderer, scene, cam, grp } = three3;
      while (grp.children.length) { const c = grp.children.pop(); c.geometry.dispose(); c.material.dispose(); }
      const Hh = 5.2, prof = info.prof, segs = prof.length;
      const half = Math.PI * 1.25;
      const mk = (r, color, opacity) => new TH.Mesh(new TH.CylinderGeometry(r, r, Hh, 48, 1, true, 0, half), new TH.MeshStandardMaterial({ color, side: TH.DoubleSide, transparent: opacity < 1, opacity, metalness: 0.3, roughness: 0.6 }));
      grp.add(mk(1.0, 0x9aa1ab, 0.55));          // outer TiN (storage node)
      const g = new TH.CylinderGeometry(0.86, 0.86, Hh, 48, segs, true, 0, half);
      const col = [], pos = g.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        const y = pos.getY(i), depth = (Hh / 2 - y) / Hh; // 0 top .. 1 bottom
        const th = prof[Math.min(segs - 1, Math.floor(depth * segs))].th;
        const c = new TH.Color(divColor(-(1 - th) * 5));
        col.push(c.r, c.g, c.b);
      }
      g.setAttribute('color', new TH.Float32BufferAttribute(col, 3));
      grp.add(new TH.Mesh(g, new TH.MeshStandardMaterial({ vertexColors: true, side: TH.DoubleSide, roughness: 0.8 })));
      grp.add(mk(0.72, 0x6b727e, 1));            // inner TiN (plate)
      grp.rotation.set(0.25, -0.6, 0);
      renderer.render(scene, cam);
    }

    // ---------- render ----------
    let lastKey = '';
    function render(s) {
      for (const k of KN) if (!knobs[k.key].contains(document.activeElement)) knobs[k.key].sync(getPath(s, k.path));
      planSeg.sync(s.t3.plan);
      const key = JSON.stringify([s.thick, s.designParams, s.t3.plan]);
      if (key === lastKey) return; lastKey = key;
      const info = s.thickInfo, th = s.thick, design = s.designParams;
      const a = T.aldMean(design.tZ_nm, th.ald, th.gpc0);
      const meanTrue = info.tTrue, cvd = a.cvd * (meanTrue / a.mean);
      const siteT = (x, y) => T.aldSite(meanTrue - cvd, cvd, th.ald, x, y);
      const sites = T.PLANS[s.t3.plan].sites;
      // measurement noise on sampled sites, from the shared gauge (B3)
      const rngM = T.rng(3), sMeas = s.params.meas.tZ.sMeas;
      const sampled = sites.map(([x, y]) => [x, y, siteT(x, y) + info.metroBias + rngM.n() * sMeas]);
      const target = design.tZ_nm, spec = s.params.meas.tZ.specHalf;
      const span = Math.max(spec, 0.05);
      drawWafer(mapCanvas, siteT, (v) => divColor((v - target) / span), sites);
      legend(mapLegend, [divColor(-1), divColor(0), divColor(1)], `${(target - span).toFixed(2)} ← 目標 ${target.toFixed(2)} → ${(target + span).toFixed(2)} nm（色階 = 規格半寬）`);
      // statistics
      const vals = sampled.map((q) => q[2]); const ms = T.meanSd(vals);
      const dense = []; for (let x = -147; x <= 147; x += 7) for (let y = -147; y <= 147; y += 7) if (x * x + y * y <= 147 * 147) dense.push(siteT(x, y));
      const dm = T.meanSd(dense), dMin = Math.min(...dense), dMax = Math.max(...dense);
      const sMin = Math.min(...vals), sMax = Math.max(...vals);
      const outTrue = dense.filter((v) => Math.abs(v - target) > spec).length / dense.length;
      // radial + tilt fit on the sampled sites
      const fitLin = (rows, ys) => { const n = rows[0].length; const A = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => rows.reduce((s2, r) => s2 + r[i] * r[j], 0))); const b = Array.from({ length: n }, (_, i) => rows.reduce((s2, r, k) => s2 + r[i] * ys[k], 0)); try { return gauss(A, b); } catch (e) { return new Array(n).fill(NaN); } };
      const rowsR = sampled.map(([x, y]) => [1, (x * x + y * y) / (150 * 150), x / 150, y / 150]);
      const cf = sampled.length >= 5 ? fitLin(rowsR, vals) : [NaN, NaN, NaN, NaN];
      mapStats.replaceChildren(
        V.kvGrid([
          ['取樣平均 sampled mean', `${ms.m.toFixed(3)} nm`], ['真實平均 true mean', `${dm.m.toFixed(3)} nm`],
          ['取樣半全距均勻度', `${(((sMax - sMin) / (2 * ms.m)) * 100).toFixed(2)} %`], ['真實半全距均勻度', `${(((dMax - dMin) / (2 * dm.m)) * 100).toFixed(2)} %`],
          ['取樣 1σ／平均', `${((ms.s / ms.m) * 100).toFixed(2)} %`], ['超出規格的晶圓面積', `${(outTrue * 100).toFixed(1)} %`, outTrue > 0.01 ? 'badtxt' : 'goodtxt'],
          ['徑向係數 a₁（−＝中心厚）', Number.isFinite(cf[1]) ? `${cf[1].toFixed(3)} nm` : '點數不足'], ['傾斜 c_x', Number.isFinite(cf[2]) ? `${cf[2].toFixed(3)} nm` : '—'],
        ]),
        u.el('p', { class: 'note' }, `${T.PLANS[s.t3.plan].zh}取樣：讀值含量測雜訊 σ_meas ${sMeas.toFixed(3)} nm（與 M6、T3 共用）${Math.abs(info.metroBias) > 0.005 ? `與量測偏差 ${info.metroBias.toFixed(3)} nm` : ''}。` +
          (s.t3.plan === 'p5' && Math.abs(s.thick.ald.edge) > 2 ? ' 5 點計畫沒有邊緣點，邊緣環幾乎看不到。' : '') +
          ((dMax - dMin) < 0.2 * (sMax - sMin) ? ' 真實膜幾乎完全均勻：取樣算出的均勻度幾乎全部來自量測雜訊——均勻度規格必須大於量具能力。' : '') + ' 徑向與傾斜係數可以直接放進 SPC。'));
      csvRows = ['site_id,x_mm,y_mm,thickness_nm,true_nm', ...sampled.map(([x, y, v], i) => `${i + 1},${x.toFixed(1)},${y.toFixed(1)},${v.toFixed(4)},${siteT(x, y).toFixed(4)}`)];

      // step coverage profile
      const prof = info.prof;
      covBox.replaceChildren(V.chart([{ pts: prof.map((q) => [q.z, meanTrue * q.th]), color: 'var(--accent)', area: true, label: '孔內 ZrO₂ 厚度' }],
        { h: 210, xLabel: '深度（深寬比單位，0 = 孔口）', yLabel: 't_ZrO₂ (nm)', yMin: 0, hlines: [{ y: meanTrue, label: '監控片讀到的平面厚度', color: 'var(--text-faint)' }], vlines: [{ x: info.AR, label: `孔底 AR ${info.AR.toFixed(0)}`, color: 'var(--sig)' }], xFmt: (v) => v.toFixed(0), yFmt: (v) => v.toFixed(1), aria: '孔內膜厚對深度' }));
      const r = s.drifted;
      covKv.replaceChildren(V.kvGrid([['穿透深度 x_PD', `${info.xpd.toFixed(0)}（AR 單位）`], ['孔底覆蓋 bottom', `${Math.round(info.bottom * 100)} %`, info.bottom < 0.9 ? 'badtxt' : 'goodtxt'],
        ['孔底厚度', `${info.tBottom.toFixed(2)} nm`], ['等效 t_Z（電容）', `${info.tZeff.toFixed(2)} nm`], ['平均漏電 J', `${info.Jcell.toExponential(1)} A/cm²`, info.Jcell > 1e-8 ? 'badtxt' : ''],
        ['介電放電時間 t_diel', Number.isFinite(r.tDiel_s) ? `${u.sci(r.tDiel_s)} s` : '∞']]),
        u.el('p', { class: 'note' }, info.bottom < 0.9 ? '監控片上的厚度完全在規格內，但孔底的膜太薄：漏電集中在孔底，retention fail 上升。平面量測看不到這件事——需要 TEM 剖面或孔內量測。' : '前驅物曝氣量足以穿透到孔底。把曝氣量調低或把電容做高（M4 的 H），看覆蓋何時開始掉。'));
      draw3D(info);
      threeNote.textContent = `顏色：灰＝與孔口相同厚度，藍＝變薄。高度壓縮顯示（實際 AR ${info.AR.toFixed(0)}:1）。外層半透明為儲存節點 TiN，內芯為上電極 TiN。`;

      // fail bits vs thickness (U-shape) and leakage vs thickness
      const sweep = [];
      for (let t = 4.6; t <= 10.0001; t += 0.1) {
        const thS = { ...th, siteT: t, metro: { ...th.metro, modelBias: 0, toolBias: 0 } };
        const pl = T.pipeline({ ...design, tZ_nm: t }, thS);
        const c = E.compute(pl.params, REF);
        sweep.push([+t.toFixed(2), Math.max(c.failRet + c.failSense, 1e-3), pl.info.Jcell, Math.max(c.failSense, 1e-3)]);
      }
      const nowF = Math.max(r.failRet + r.failSense, 1e-3);
      failBox.replaceChildren(V.chart([{ pts: sweep.map((q) => [q[0], q[1]]), color: 'var(--accent)', label: '總 fail bit' }, { pts: sweep.map((q) => [q[0], q[3]]), color: 'var(--leak)', dash: '5 4', label: '其中感測失效' }, { pts: [[meanTrue, nowF]], color: 'var(--sig)', dotsOnly: true, r: 5, label: '目前' }],
        { h: 220, logY: true, xLabel: 'ZrO₂ 真實厚度 (nm)', yLabel: 'fail bit／晶片', band: null, vlines: [{ x: target - spec, label: 'LSL' }, { x: target + spec, label: 'USL' }], xFmt: (v) => v.toFixed(1), aria: 'fail bit 對厚度的 U 形曲線' }),
        u.el('p', { class: 'note' }, '不對稱的 U 形：薄的一側是懸崖（漏電每 0.25 nm 增一個數量級，retention fail 暴增）；厚的一側是緩坡（EOT 上升、C_s 下降、ΔV 變小，感測失效慢慢增加）。所以規格中心若放在最低點，下限離懸崖太近——這是厚度規格常常偏向厚側的原因。孔底覆蓋不足時懸崖往右移。'));
      leakBox.replaceChildren(V.chart([{ pts: sweep.map((q) => [q[0], q[2]]), color: 'var(--leak)', label: 'J（含孔內分布）' }],
        { h: 220, logY: true, xLabel: 'ZrO₂ 真實厚度 (nm)', yLabel: 'J (A/cm²)', hlines: [{ y: 1e-8, label: '示意上限（cell 偏壓）' }], xFmt: (v) => v.toFixed(1), aria: '漏電對厚度' }),
        u.el('p', { class: 'note' }, '文獻的 DRAM 電容漏電規格是 0.8 V 下 <1×10⁻⁷ A/cm²（Lee 2024、Li 2024）。cell 實際偏壓約 V_ARY/2，這裡用 1×10⁻⁸ 當示意上限；每薄 0.25 nm 漏電約增一個數量級（示意斜率）。'));

      // chip-level risk map (13 x 13 grid)
      const risk = [];
      for (let x = -140; x <= 140; x += 23.3) for (let y = -140; y <= 140; y += 23.3) {
        if (x * x + y * y > 147 * 147) continue;
        const t = siteT(x, y);
        const pl = T.pipeline({ ...design, tZ_nm: t }, { ...th, siteT: t });
        const c = E.compute(pl.params, REF);
        risk.push([x, y, Math.max(c.failRet + c.failSense, 1e-3)]);
      }
      const lmin = Math.log10(Math.min(...risk.map((q) => q[2]))), lmax = Math.max(Math.log10(Math.max(...risk.map((q) => q[2]))), lmin + 1);
      const nearest = (x, y) => { let b = risk[0], bd = Infinity; for (const q of risk) { const d = (q[0] - x) ** 2 + (q[1] - y) ** 2; if (d < bd) { bd = d; b = q; } } return b[2]; };
      drawWafer(riskCanvas, nearest, (v) => seqColor((Math.log10(v) - lmin) / (lmax - lmin)), []);
      legend(riskLegend, SEQ, `fail bit／晶片：1e${lmin.toFixed(1)} → 1e${lmax.toFixed(1)}（對數）`);
      const worst = risk.reduce((a2, q) => (q[2] > a2[2] ? q : a2)), best = risk.reduce((a2, q) => (q[2] < a2[2] ? q : a2));
      const uniform = worst[2] / best[2] < 1.5;
      riskStats.replaceChildren(u.el('p', { class: 'note' }, uniform ? `整片風險均勻（約 ${u.sci(worst[2])} fail bit／晶片，修補前）：問題不在空間分布，而在整片的平均或孔內覆蓋。` : `最差晶片在 (${worst[0].toFixed(0)}, ${worst[1].toFixed(0)}) mm，約 ${u.sci(worst[2])} fail bit（修補前），最好的約 ${u.sci(best[2])}。風險圖跟著厚度圖走：薄的區域漏電、厚的區域 C_s 不足。`),
        u.el('p', { class: 'note' }, '這是量測工程師最該帶到會議上的圖：不是「均勻度 1.2%」，而是「哪些晶粒因為這個厚度分布而 fail」。'));
    }
    function gauss(A, b) { const n = b.length, M = A.map((r, i) => [...r, b[i]]); for (let i = 0; i < n; i++) { let p = i; for (let k = i + 1; k < n; k++) if (Math.abs(M[k][i]) > Math.abs(M[p][i])) p = k; [M[i], M[p]] = [M[p], M[i]]; if (Math.abs(M[i][i]) < 1e-12) throw new Error('singular'); for (let k = i + 1; k < n; k++) { const f = M[k][i] / M[i][i]; for (let j = i; j <= n; j++) M[k][j] -= f * M[i][j]; } } const x = new Array(n).fill(0); for (let i = n - 1; i >= 0; i--) { let s2 = M[i][n]; for (let j = i + 1; j < n; j++) s2 -= M[i][j] * x[j]; x[i] = s2 / M[i][i]; } return x; }
    S.subscribe(render);
    // redraw canvases when the theme flips
    if (root.matchMedia) root.matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', () => { lastKey = ''; render(S.snapshot()); });
  }
  root.DMS.t2 = { mount };
})(typeof globalThis !== 'undefined' ? globalThis : this);
