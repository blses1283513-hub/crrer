/* DRAM Thickness Metro — T4 excursion triage: seven DRAM thickness cases, the five checks,
   a verdict, and the filled communication template. Each case reconfigures the whole simulator. */
(function (root) {
  'use strict';
  const D = root.DMS;
  const BUCKET = { metro: '量測系統 Metro', process: '製程 Process', equipment: '設備 Equipment', material: '材料／模型 Material·model' };
  const CHECKS = [
    ['ref', '1 參考片', 'Reference：控制片／參考片也異常嗎？'],
    ['second', '2 第二台機', 'Replication：另一台合格機台看到一樣的結果嗎？'],
    ['map', '3 空間特徵', 'Spatial：中心、邊緣、傾斜、局部？'],
    ['time', '4 時間特徵', 'Time：隨機、漸變、階躍？'],
    ['link', '5 製程關聯', 'Process link：同一時間什麼改變了？'],
  ];
  const CASES = [
    { id: 'c1', name: 'M3 換燈後 ZrO₂ +0.12 nm', go: '#t3',
      symptom: 'SPC 在週二 14:00 後跳高 0.12 nm，所有腔體都一樣。M3 當天早上換了氘燈。',
      t3: { tool: 2, tools: [{ off: 0, slope: 1 }, { off: 0.02, slope: 1 }, { off: 0.12, slope: 1 }] }, thick: { metro: { toolBias: 0.12 } },
      ev: { ref: 'M3 上的參考片讀 6.12 nm（認證值 6.00）→ 異常。', second: '同一片產品送 M1：5.99 nm，與歷史一致。', map: '整片均勻上移，形狀沒變。', time: '單一階躍，時間點＝換燈。', link: '腔體 FDC 無異常。' },
      answer: 'metro', why: '參考片在 M3 也異常、第二台機正常、整片平移、時間對齊換燈 → 量測系統。先停 M3 出貨判定，做波長／強度校正與匹配，再放行。',
      comm: ['ZrO₂ 讀值自週二 14:00 起 +0.12 nm，只出現在 M3 量的批次。', 'M3 參考片 +0.12 nm；同批產品在 M1 為 5.99 nm；晶圓形狀不變。', '時間與 M3 換燈一致，屬量測偏差，非製程。', 'M1/M2 參考片在基線內；腔體 FDC 正常。', 'M3 暫停判定，重做校正與 tool-to-tool matching；受影響批次以 M1 重量。', 'M3 放行後連續 3 天參考片＋與 M1 配對量測。'] },
    { id: 'c2', name: 'B 腔 PM 後中心變厚', go: '#t2',
      symptom: 'B 腔 PM 後，ZrO₂ 均勻度從 0.6% 變 1.8%，平均值只動 0.02 nm。',
      thick: { ald: { dome: 3.5 } },
      ev: { ref: '參考片正常。', second: '兩台量測機一致。', map: '中心厚、邊緣薄（圓頂），徑向係數 a₁ 由 0 變負。', time: 'PM 後第一批開始的階躍。', link: 'PM 更換了噴頭；FDC 顯示中心區加熱功率略高。' },
      answer: 'equipment', why: '量測正常、空間特徵是圓頂、時間對齊 PM、硬體有更換 → 設備。平均值幾乎沒動，所以只看平均的 SPC 抓不到；要看徑向係數與晶片風險圖。',
      comm: ['B 腔 PM 後 ZrO₂ 均勻度 0.6% → 1.8%，中心厚。', '徑向係數 a₁ 自 PM 後第一批轉負；A/C 腔不變。', '圓頂形狀較符合噴頭／加熱分區問題，非量測。', '兩台量測機與參考片一致。', '設備檢查噴頭安裝與中心加熱區校正；B 腔先降載。', '徑向係數納入 SPC；恢復後連續 3 批 49 點圖。'] },
    { id: 'c3', name: '退火條件變更後 SE 讀值 −0.1 nm', go: '#t1',
      symptom: '後段退火溫度下調後，ZrO₂ SE 讀值 −0.1 nm，但 XRR 總厚沒變，C_s 卻下降了。',
      drift: { key: 'phase', meanShift: -0.4, shiftUnit: 'abs', sigmaScale: 1 }, select: 'phase',
      ev: { ref: '參考片正常（參考片沒有經過新的退火）。', second: '所有 SE 機台一起偏 −0.1 nm（共用同一個 n/k 資料庫）。', map: '整片均勻。', time: '階躍，對齊退火配方變更。', link: 'XRD 四方相比例 0.90 → 0.50；XRR 總厚不變。' },
      answer: 'material', why: '膜的晶相變了：n 下降但資料庫仍用晶化膜的 n，擬合把 n 的錯誤推到厚度上；XRR 證明厚度沒變。真正的電性問題是 κ 下降讓 C_s 變小——厚度讀值反而在誤導。',
      comm: ['退火變更後 SE 讀值 −0.1 nm，XRR 總厚不變。', '所有 SE 機台同向偏移；XRD 四方相 0.90 → 0.50。', '屬材料（晶相）改變造成的模型偏差，厚度未變；κ 下降使 C_s 下降（見 M4）。', 'XRR 與參考片確認厚度不變。', '整合與製程評估退火條件；量測端更新 n/k 資料庫或加入相比例模型。', '追蹤 XRD 相比例與 C_s（M4）。'] },
    { id: 'c4', name: '所有機台的監控片慢慢變厚', go: '#t3',
      symptom: '三台量測機的 ZrO₂ 監控片在兩週內都上升約 0.05 nm，產品讀值不變。',
      thick: { film: { amc: 0.15 } }, t3: { amcRate: 0.015 },
      ev: { ref: '參考片本身在漂：三台一起、鋸齒狀。', second: '第二台機看到同樣的上升。', map: '均勻。', time: '漸變，清潔後回到基線（鋸齒）。', link: '無製程變更；監控片存放於開放式片匣。' },
      answer: 'metro', why: '三台一起漂、清潔後歸零、產品不變 → 監控片表面吸附（AMC），是量測參考出了問題，不是機台也不是製程。不要因此調製程。',
      comm: ['ZrO₂ 監控片三台同步上升約 0.05 nm／兩週，產品不變。', '鋸齒狀，清潔後回到基線。', '監控片表面吸附，非機台漂移、非製程。', '新清潔的參考片在三台都在基線內。', '監控片改密封存放、固定清潔週期；模型加入表面層或改用較厚監控膜。', '追蹤清潔前後讀值差。'] },
    { id: 'c5', name: '監控片全合格，retention fail 卻上升', go: '#t2',
      symptom: '前驅物鋼瓶更換後，ZrO₂ 監控片平均與均勻度都正常，但 wafer test 的 retention fail 上升。',
      thick: { ald: { exposure: 0.55 } },
      ev: { ref: '參考片正常。', second: '兩台量測機一致，讀值在規格中心。', map: '平面晶圓圖正常。', time: '階躍，對齊鋼瓶更換。', link: '鋼瓶溫度設定偏低 → 前驅物曝氣量下降；平面晶圓上不缺料，深孔底部缺料。' },
      answer: 'process', why: '平面監控片看不到孔內：曝氣量不足時穿透深度變短，48:1 的電容孔底膜變薄、漏電集中在孔底。這是 DRAM 膜厚量測最大的盲點，需要 TEM 剖面或孔內量測（或電性）來看。',
      comm: ['鋼瓶更換後 retention fail 上升，ZrO₂ 監控片正常。', '平面量測與參考片皆正常；時間對齊鋼瓶更換。', '曝氣量不足導致電容孔底覆蓋不足（step coverage），平面量測看不到。', '安排 TEM 剖面量孔底厚度；比對鋼瓶溫度紀錄。', '製程恢復鋼瓶溫度／延長脈衝；量測端新增孔內覆蓋監控（剖面抽檢）。', '追蹤 retention fail 與 TEM 孔底厚度。'] },
    { id: 'c6', name: 'XRF 說 TiN 下電極薄了 5%', go: '#t1',
      symptom: '換了 TiN 靶材後，XRF 讀值 −5%，但片電阻幾乎不變。',
      t1: { xrfRho: 5.13 },
      ev: { ref: 'XRF 參考片正常。', second: '另一台 XRF 一致。', map: '均勻。', time: '階躍，對齊換靶。', link: 'XRR 顯示 TiN 密度 5.40 → 5.13 g/cm³，厚度不變。' },
      answer: 'material', why: 'XRF 量的是單位面積原子數（ρ·t），配方用固定密度換算；密度下降被讀成變薄。XRR 分得出密度與厚度。這是材料改變，不是厚度改變。',
      comm: ['換靶後 TiN XRF 讀值 −5%，片電阻不變。', 'XRF 兩台一致；XRR 顯示密度 −5%、厚度不變。', '屬材料密度改變，XRF 換算偏差。', 'XRR 與片電阻交叉確認。', '評估新靶材密度對電性的影響；XRF 校正密度更新或改用 XRR 混合量測。', '追蹤 XRR 密度與 XRF 讀值。'] },
    { id: 'c7', name: '清機後第一批偏厚、中心更厚', go: '#t2',
      symptom: 'A 腔清機後，ZrO₂ 平均 +0.4 nm，而且中心特別厚。',
      thick: { ald: { purge: 0.6 } },
      ev: { ref: '參考片正常。', second: '兩台量測機一致。', map: '中心厚（噴頭下方），整體也偏厚。', time: '清機後開始。', link: '清機後吹淨時間設定被縮短；n 也略變。' },
      answer: 'process', why: '吹淨不足，兩種前驅物在氣相相遇，產生寄生 CVD：多出來的膜集中在噴頭下方。ALD 的自限性被破壞，厚度與均勻度一起變差。',
      comm: ['A 腔清機後 ZrO₂ +0.4 nm，中心厚。', '量測一致；形狀為中心厚，伴隨平均偏厚。', '吹淨不足造成寄生 CVD。', '比對清機前後配方：吹淨時間被縮短。', '恢復吹淨時間；檢查閥門時序。', '恢復後 3 批 49 點圖與粒子檢查。'] },
    { id: 'c8', name: '曝光機換鏡組後邊緣場疊對變大', go: '#t7',
      symptom: 'SNC 層疊對 |m|+3σ 從 2.5 nm 升到 5 nm，晶圓邊緣最差，中心正常。',
      ext: { ov: { Mwx: 0.35, Mwy: 0.33 } },
      ev: { ref: '疊對參考片在量測機上正常；TIS 0°/180° 檢查正常。', second: '另一台疊對量測機看到相同向量圖。', map: '向量從中心往外放射，邊緣最大——典型的晶圓放大（wafer magnification）。', time: '曝光機投影鏡組更換後開始。', link: '線性模型擬合出晶圓放大 +0.35 ppm；殘差正常。' },
      answer: 'equipment', why: '向量放射狀、擬合項集中在晶圓放大、殘差正常、時間對齊鏡組更換 → 曝光機（設備）。線性項可由曝光機修正：更新放大補償後應回到規格內。',
      comm: ['SNC 層疊對 |m|+3σ 2.5 → 5 nm，邊緣最差。', '線性模型：晶圓放大 X/Y +0.35/+0.33 ppm；殘差未變；兩台量測機一致。', '屬曝光機放大校正偏移（鏡組更換後）。', 'TIS 與參考片正常，排除量測。', '曝光機更新放大補償，回饋 APC；確認對準標記品質。', '連續 3 批向量圖與殘差追蹤。'] },
    { id: 'c9', name: '支撐層 SiN 換配方後晶圓翹曲、疊對放大', go: '#t9',
      symptom: '電容支撐層 PECVD SiN 換成高沉積速率配方後，下一層曝光的疊對出現晶圓放大，晶圓翹曲也變大。',
      ext: { stress: { film: 'pesin', s: -600, tf: 150 }, ov: { useStress: true } },
      ev: { ref: '應力量測：沉積前後各掃一次，參考片正常。', second: '另一台曲率量測一致：約 −0.6 GPa（壓應力），翹曲約 50 µm。', map: '晶圓呈拱形（往膜面凸），疊對向量放射狀。', time: '階躍，對齊 SiN 配方變更。', link: '新配方的離子轟擊較強，膜更緻密、壓應力更大；曲率 → 吸平時表面應變 → 晶圓放大。' },
      answer: 'process', why: '應力是膜的性質：新 SiN 配方壓應力變大，晶圓翹曲；吸盤吸平時表面應變變成疊對的晶圓放大項。量測都正常，根因在沉積製程。',
      comm: ['支撐層 SiN 換配方後，翹曲增加、下一層疊對出現晶圓放大。', '前後曲率：σ ≈ −0.6 GPa（壓）、翹曲約 50 µm；疊對擬合的晶圓放大與應力推算（約 −2 ppm）一致。', '新 SiN 配方應力過大。', '兩台曲率量測一致；疊對殘差正常。', '調整 SiN 配方（RF 功率、氣體比）把應力拉回規格；短期由曝光機補償放大。', '每批量應力（前後兩次）與疊對放大項。'] },
    { id: 'c10', name: '同一點重複量測，光阻 CD 一直變小', go: '#t6',
      symptom: 'GR&R 研究中，同一個點量 15 次，CD 從 30.0 nm 一路降到約 28.5 nm，重複性看起來很差。',
      ext: { sem: { scans: 15, mat: 'resist' } },
      ev: { ref: '硬罩參考片重複量測很穩定。', second: '另一台 CD-SEM 量新的點：30.0 nm。', map: '只有被重複量的那幾個點變小。', time: '隨量測次數單調下降、逐漸飽和。', link: '電子束劑量讓光阻收縮（shrinkage）。' },
      answer: 'metro', why: '是量測本身改變了樣品：電子束讓光阻收縮。GR&R 要換點或用硬罩樣品；配方可降低劑量（低 kV、少影格）。',
      comm: ['光阻 CD 同點重複量測單調下降約 1.5 nm。', '硬罩參考片穩定；新點量測正常；只有被重複照射的點變小。', '電子束造成光阻收縮，屬量測誘發。', '換點重量與硬罩樣品確認。', 'GR&R 改用不同點／硬罩樣品；配方降低劑量。', '追蹤每點照射次數。'] },
    { id: 'c11', name: 'OCD 說 CD +2.5 nm，XSEM 卻沒變', go: '#t8',
      symptom: '蝕刻偏壓功率調整後，OCD 回報頂部 CD +2.5 nm（+8%），但 XSEM 剖面的頂部 CD 不變，只有側壁角變小。',
      ext: { ocd: { bias: 0.55, floatSWA: false } },
      ev: { ref: 'OCD 參考片正常。', second: '另一台 OCD 用同一個模型，結果一樣。', map: '整片均勻。', time: '階躍，對齊偏壓功率變更。', link: 'XSEM：頂部 CD 與深度不變，側壁角 87° → 85.7°；OCD 模型把 SWA 固定在 87°。' },
      answer: 'material', why: '模型錯：SWA 被固定，真實剖面變寬的底部被擬合推到頂部 CD 上（CD 與 SWA 相關）。放開 SWA 或用 XSEM／CD-SEM 參考值重建模型。',
      comm: ['偏壓變更後 OCD 頂部 CD +2.5 nm，XSEM 頂部 CD 不變。', 'XSEM 顯示 SWA 87° → 85.7°；OCD 模型 SWA 固定。', '模型假設失效（SWA 固定），屬模型問題。', '放開 SWA 重擬合：CD 回到正常、SWA 讀到 85.7°。', '更新 OCD 模型（SWA 浮動）並以 XSEM 驗證；檢查 CD 與 SWA 相關性。', '分批追蹤 OCD vs XSEM。'] },
  ];

  function mount(sel) {
    const host = document.querySelector(sel);
    const u = D.ui, S = D.state;
    D.cases = CASES;
    let cur = null, shown = new Set(), verdict = null;
    const list = u.el('div', { class: 'cases', role: 'group', 'aria-label': '案例' }, ...CASES.map((c) => u.el('button', { type: 'button', 'data-c': c.id, onclick: () => pick(c.id) }, c.name)));
    const body = u.el('div', { class: 'case-body' });
    host.append(
      u.el('h2', { id: 'h-t4' }, 'T4 異常判讀練習 ', u.el('span', { class: 'en' }, 'excursion triage · five checks')),
      u.el('p', { class: 'sub' }, '選一個案例：整個模擬器（鏈條、T1–T3、M4–M6）會切換到那個情境。依序做五項檢查，看證據，再判斷問題屬於量測、製程、設備還是材料。判斷完成後會產生可直接貼到報告的溝通範本。'),
      list, body,
      u.el('div', { class: 'row' }, u.el('button', { type: 'button', onclick: () => { S.reset(); cur = null; draw(); } }, '回到預設（離開案例）')));

    function pick(id) { cur = CASES.find((c) => c.id === id); shown = new Set(); verdict = null; S.applyCase(id); draw(); }
    function draw() {
      list.querySelectorAll('button').forEach((b) => b.classList.toggle('on', cur && b.dataset.c === cur.id));
      if (!cur) { body.replaceChildren(u.el('p', { class: 'note' }, '尚未選擇案例。目前是預設參數（Micron 1β 級，公開資料推算）。')); return; }
      const checks = u.el('div', { class: 'checks' }, ...CHECKS.map(([k, lab, q]) => {
        const open = shown.has(k);
        return u.el('div', { class: 'check' + (open ? ' open' : '') },
          u.el('button', { type: 'button', onclick: () => { shown.add(k); draw(); } }, lab),
          u.el('span', { class: 'q' }, q), open ? u.el('p', { class: 'ev' }, cur.ev[k]) : null);
      }));
      const ready = shown.size >= 3;
      const vRow = u.el('div', { class: 'row' }, u.el('span', { class: 'note' }, ready ? '你的判斷：' : `至少做 3 項檢查再判斷（已做 ${shown.size}）`),
        ...Object.entries(BUCKET).map(([k, lab]) => u.el('button', { type: 'button', disabled: !ready, class: verdict === k ? 'on' : '', onclick: () => { verdict = k; draw(); } }, lab)));
      const out = [];
      if (verdict) {
        const right = verdict === cur.answer;
        out.push(u.el('div', { class: right ? 'info' : 'warn' }, right ? `正確：${BUCKET[cur.answer]}。` : `再想一下：答案是 ${BUCKET[cur.answer]}。`, ' ', cur.why));
        const L = ['觀察 Observation', '證據 Evidence', '假設 Hypothesis', '驗證 Verification', '行動 Action', '追蹤 Monitoring'];
        const txt = cur.comm.map((c, i) => `${L[i]}：${c}`).join('\n');
        out.push(u.el('div', { class: 'card' }, u.el('h3', {}, '溝通範本 communication template'), u.el('ol', { class: 'comm' }, ...cur.comm.map((c, i) => u.el('li', {}, u.el('b', {}, L[i] + '：'), c))),
          D.tui.copyBtn('複製範本', () => txt + '\n')));
      }
      body.replaceChildren(u.el('div', { class: 'card' }, u.el('h3', {}, cur.name), u.el('p', {}, cur.symptom),
        u.el('p', { class: 'note' }, '模擬器已切換到這個情境。', u.el('a', { href: cur.go }, '到相關模組看證據 →'))), checks, vRow, ...out);
      if (D.terms) D.terms.wrap(body);
    }
    draw();
  }
  root.DMS.t4 = { mount, CASES };
})(typeof globalThis !== 'undefined' ? globalThis : this);
