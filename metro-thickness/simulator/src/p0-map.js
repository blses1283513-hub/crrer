/* DRAM Thickness Metro — P0 process → measurement map: the seven fab areas, what each measures and why,
   where it lives in this simulator, a DRAM example, plus mini calculators (PVD reflectivity, wet contact angle,
   BPSG dopant, poly dopant). */
(function (root) {
  'use strict';
  const D = root.DMS;
  const AREAS = {
    photo: { zh: '微影 Photo', what: '量光阻做出來的圖形', items: [['光阻厚度', '確認圖形會正確成形，且留下足夠光阻撐過乾蝕刻', '#t11'], ['CD', '顯影後確認印出的尺寸符合設計', '#t6'], ['疊對（registration）', '確認和前層對準', '#t7']], dram: 'BL、SNC、電容孔圖形；SNC 對位決定接觸面積。' },
    etch: { zh: '乾蝕刻 Dry etch', what: '量光阻下面被蝕刻出來的最終特徵', items: [['膜厚（前、後）', '算蝕刻速率、蝕刻均勻性、選擇比', '#t10'], ['CD（頂部／底部）', '蝕刻後確認尺寸', '#t6'], ['剖面（深度與形狀）', '例如斜側壁讓下一步填洞順利', '#t8']], dram: '48:1 電容孔：深度、底部 CD、彎曲（bowing）。' },
    diff: { zh: '擴散 Diffusion', what: '長或沉積非常薄的膜', items: [['膜厚（多在平坦監控片 TW）', 'TW 厚度和產品不同，但可以相關；膜很薄，量測要非常精密', '#t1b'], ['膜成分', '例如多晶矽的摻雜濃度，影響元件操作', '#p0'], ['質量', '有些膜難量厚度，改量質量（mass）', '#t1']], dram: '閘極氧化層、ZrO₂ ALD（爐管或單片）；TW 與電容孔內厚度的相關見 T2。' },
    cvd: { zh: 'CVD', what: '通常比擴散膜厚，量測項目類似', items: [['膜厚（多在切割道測試結構）', '', '#t5'], ['光學性質 n、k', '有些膜在曝光時必須透明', '#t1b'], ['膜成分', '例如 BPSG 的摻雜量，決定蝕刻速率', '#p0'], ['應力', '高應力會損壞元件，要密切監控', '#t9'], ['密度', '確認沉積製程沒有偏離開發時的狀態', '#t1']], dram: 'SiN 電容支撐層（應力、翹曲）、mold 氧化層（厚度、密度、濕蝕刻速率）。' },
    pvd: { zh: 'PVD 濺鍍', what: '金屬膜；廠內量測項目相對少', items: [['膜厚（切割道或測試片；多層膜要分別在測試片上量）', '', '#t1'], ['反射率', '用表面反射光的程度評估金屬表面粗糙度', '#p0'], ['密度', '確認沉積製程沒有偏離', '#t1']], dram: 'TiN 電極、W 位元線；金屬不透光，厚度靠 XRF、片電阻、聲學。' },
    cmp: { zh: 'CMP', what: '主要關心移除速率與均勻性', items: [['膜厚（前、後）', '算研磨速率、均勻性、選擇比；也量停止層的厚度以判斷侵蝕', '#t10'], ['剖面', '圖形密度造成的不平（例如碟陷），確認不影響元件', '#t10']], dram: '電容 mold 與 STI 平坦化；密集陣列的侵蝕。' },
    wet: { zh: '濕製程 Wet', what: '移除粒子、殘留物或整層膜，同時盡量不傷下層', items: [['膜厚（前、後）', '算濕蝕刻速率、均勻性、選擇比；也量其他膜，確認損失很小', '#t10'], ['接觸角', '濕製程後水在表面的附著程度', '#p0']], dram: '電容 mold 的 HF 移除：TiN 與 SiN 支撐不能被吃。' },
  };
  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state, V = D.tui, P = D.proc;
    const grid = u.el('div', { class: 'p0-grid' });
    const detail = u.el('div', { class: 'card' });
    const calc = u.el('div', { class: 'p0-calc' });
    host.append(
      u.el('h2', { id: 'h-p0' }, 'P0 製程 → 量測地圖 ', u.el('span', { class: 'en' }, 'what each fab area measures')),
      u.el('p', { class: 'sub' }, '七個製程區各自量什麼、為什麼量、在這個模擬器的哪裡。點一個製程區看細節；下方的小計算器補上前面模組沒有的項目：PVD 反射率與粗糙度、濕製程接觸角、BPSG 摻雜、多晶矽摻雜。'),
      grid, detail, u.el('h4', { class: 'grp', style: 'margin-top:14px' }, '製程專屬量測計算器'), calc);
    // calculators
    const c = {};
    const card = (title, en, kids) => u.el('div', { class: 'card' }, u.el('h3', {}, title, ' ', u.el('span', { class: 'en' }, en)), ...kids);
    const knob = (k, zh, en, unit, mn, mx, st, tier, src, log) => (c[k] = V.knob({ key: k, zh, en, unit, min: mn, max: mx, step: st, tier, src, log }, 0, (v) => S.setExt({ proc: { [k]: v } })));
    const roughOut = u.el('div'), caOut = u.el('div'), bpsgOut = u.el('div'), polyOut = u.el('div');
    const surfSeg = V.seg(Object.entries(P.SURF).map(([k, sv]) => [k, sv.zh]), 'hf', (k) => S.setExt({ proc: { surf: k } }), '表面');
    calc.append(
      card('PVD：反射率 → 表面粗糙度', 'reflectivity', [knob('rough', 'Al 表面粗糙度 σ', 'rms roughness', 'nm', 0, 30, 0.5, 'red', '示意'), roughOut]),
      card('濕製程：接觸角', 'contact angle', [u.el('div', { class: 'row' }, surfSeg), knob('hours', '清洗後放置時間', 'queue time', 'h', 0, 72, 1, 'red', '示意：有機物吸附使接觸角上升'), caOut]),
      card('CVD：BPSG 摻雜', 'BPSG dopant', [knob('B', '硼 B', 'boron', 'wt%', 0, 6, 0.1, 'orange', '常見 B、P 各約 3–5 wt%（通用文獻）'), knob('P', '磷 P', 'phosphorus', 'wt%', 0, 8, 0.1, 'orange', '同上'), bpsgOut]),
      card('擴散：多晶矽摻雜', 'poly dopant', [knob('N', '摻雜濃度', 'doping', 'cm⁻³', 1e18, 1e21, 1e18, 'red', '示意', true), knob('tp', '多晶矽厚度', 'poly thickness', 'nm', 30, 300, 1, 'red', '示意'), polyOut]));

    function draw(s) {
      const e = s.ext.proc;
      grid.replaceChildren(...Object.entries(AREAS).map(([k, a]) => u.el('button', { type: 'button', class: 'p0-area' + (e.area === k ? ' on' : ''), onclick: () => S.setExt({ proc: { area: k } }) }, u.el('b', {}, a.zh), u.el('span', {}, a.what), u.el('span', { class: 'n' }, `${a.items.length} 項量測`))));
      const a = AREAS[e.area];
      detail.replaceChildren(u.el('h3', {}, a.zh, '：', a.what), u.el('table', { class: 'f' }, u.el('thead', {}, u.el('tr', {}, u.el('th', {}, '量測'), u.el('th', {}, '為什麼'), u.el('th', {}, '在模擬器'))),
        u.el('tbody', {}, ...a.items.map(([m, why, go]) => u.el('tr', {}, u.el('td', {}, m), u.el('td', {}, why || '—'), u.el('td', {}, u.el('a', { href: go }, go === '#p0' ? '下方計算器' : go.replace('#', '').toUpperCase() + ' →')))))),
        u.el('p', { class: 'note' }, 'DRAM：', a.dram));
      if (D.terms) D.terms.wrap(detail);
      ['rough', 'hours', 'B', 'P', 'N', 'tp'].forEach((k) => { if (!c[k].contains(document.activeElement)) c[k].sync(e[k]); });
      surfSeg.sync(e.surf);
      const R0 = 0.92, R = P.roughR(R0, e.rough, 480);
      roughOut.replaceChildren(V.kvGrid([['鏡面反射率 @480 nm', `${(R * 100).toFixed(1)} %`], ['相對光滑表面', `${((R / R0) * 100).toFixed(1)} %`, R / R0 < 0.9 ? 'badtxt' : '']]),
        u.el('p', { class: 'note' }, 'R = R₀·exp[−(4πσ/λ)²]：粗糙表面把光散射掉，鏡面反射下降。PVD 金屬的晶粒變大、溫度過高或靶材異常時表面變粗——反射率是快速、非破壞的代理指標（R₀ 為示意值）。'));
      const ang = P.contactAngle(e.surf, e.hours);
      caOut.replaceChildren(V.kvGrid([['接觸角', `${ang.toFixed(0)}°`], ['表面', ang < 20 ? '親水（hydrophilic）' : ang > 60 ? '疏水（hydrophobic）' : '中間']]),
        u.el('p', { class: 'note' }, 'Young：cos θ = (γ_sv − γ_sl)/γ_lv。HF 清洗後的 Si 為 H 終端、疏水；SC1 後有化學氧化層、親水。清洗後放太久，有機物吸附讓接觸角上升——接觸角是清洗成效與等待時間（queue time）的指標。'));
      const b = P.bpsg(e.B, e.P);
      bpsgOut.replaceChildren(V.kvGrid([['相對濕蝕刻速率', `${b.erRel.toFixed(2)}×`], ['回流溫度（示意）', `${b.flowT.toFixed(0)} °C`], ['B+P 判讀', b.risk, e.B + e.P > 10 || e.B + e.P < 5 ? 'badtxt' : 'goodtxt']]),
        u.el('p', { class: 'note' }, `摻雜量用 FTIR 量：B–O 吸收約 ${b.ftirBO} cm⁻¹、P=O 約 ${b.ftirPO} cm⁻¹ 的峰面積換算 wt%（或 XRF）。P 越多，HF 濕蝕刻越快；B+P 越多，回流溫度越低。速率與溫度關係為示意。`));
      const rs = P.polyRs(e.N, e.tp);
      polyOut.replaceChildren(V.kvGrid([['片電阻 R_s', `${rs >= 1000 ? (rs / 1000).toFixed(1) + ' kΩ' : rs.toFixed(0) + ' Ω'}/□`], ['電阻率', `${(rs * e.tp * 1e-7 * 1000).toFixed(2)} mΩ·cm`]]),
        u.el('p', { class: 'note' }, 'R_s = 1/(q μ N t)，多晶矽遷移率受晶界限制（此處取 30 cm²/V·s，示意）。摻雜濃度用四點探針（片電阻）或 SIMS 確認；DRAM 的多晶矽接觸插塞（plug）電阻直接影響 tWR 與讀取。'));
    }
    S.subscribe(draw);
  }
  root.DMS.p0 = { mount, AREAS };
})(typeof globalThis !== 'undefined' ? globalThis : this);
