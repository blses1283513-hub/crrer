// ==UserScript==
// @name         InvenTree 中文操作助手
// @namespace    crrer.inventree
// @version      0.1.0
// @description  滑鼠停留顯示中文操作說明、轉移庫存時跳出調貨提醒、查詢全部異動紀錄（時間與操作人）
// @match        http://localhost/*
// @match        http://127.0.0.1/*
// @grant        none
// @run-at       document-idle
// ==/UserScript==

(function () {
  'use strict';

  // 避免重複載入（例如同時透過 App 內建與 Tampermonkey 載入）
  if (window.__ithLoaded) return;
  window.__ithLoaded = true;

  // ===================== 設定 =====================
  const CONFIG = {
    // 與 inventree-seed/config.json 的公司名稱一致（頂層庫位名稱）
    companies: ['A 公司', 'B 公司', 'C 公司'],
    hoverDelayMs: 500,
    auditMaxRows: 2000,
    // 單筆數量達到此值即視為「大量」，送出前要求確認
    largeQty: 100,
    // 通知輪詢間隔（毫秒）
    notifyPollMs: 30000,
  };

  // ===================== 操作說明字典 =====================
  // match：比對按鈕／分頁／欄位的文字或 aria-label（中英文都列，因翻譯版本可能不同）
  const HELP = [
    // --- 主選單 ---
    { match: /^(dashboard|儀表板|首頁)$/i, text: '首頁儀表板：顯示低庫存、待處理訂單等摘要。' },
    { match: /^(parts?|零件)$/i, text: '零件：瀏覽所有產品與 SKU。可依分類（公司）篩選，點進去可看庫存與異動。' },
    { match: /^(stock|庫存)$/i, text: '庫存：依庫位（公司 → 倉庫）查看每個 SKU 的現有數量，也可在此轉移、盤點。' },
    { match: /^(purchasing|採購)$/i, text: '採購（進貨）：建立採購單，到貨後按「收貨」即自動入庫。' },
    { match: /^(sales|銷售)$/i, text: '銷售（出貨）：建立銷售單 → 建立出貨單 → 分配庫存 → 完成出貨。' },
    { match: /^(manufacturing|製造|生產)$/i, text: '製造：本案通常不使用。' },
    { match: /^(notifications?|通知)$/i, text: '通知：低庫存等系統通知會出現在這裡。' },
    { match: /^(search|搜尋|搜索)$/i, text: '搜尋：可輸入料號（例 A-P03-S2-XL）或品名快速找到 SKU。' },
    { match: /scan|barcode|條碼|掃描/i, text: '條碼掃描：用相機或掃描器讀取條碼，直接開啟該庫存或零件。' },

    // --- 庫存操作 ---
    { match: /^(stock actions?|stock operations?|庫存操作)$|action-menu-stock/i, text: '庫存操作選單：入庫、出庫、轉移、盤點都在這裡。每次操作都會記錄時間與操作人。' },
    { match: /^(add stock|新增庫存|增加庫存|添加庫存)$/i, text: '增加庫存：數量直接加上去（例如補登、退貨入庫）。請在備註寫明原因。' },
    { match: /^(remove stock|移除庫存|減少庫存)$/i, text: '減少庫存：數量直接扣除（例如報廢、樣品）。正常出貨請改用銷售單。' },
    { match: /^(transfer( stock)?|轉移(庫存)?|移動(庫存)?|調撥)$/i, text: '轉移庫存（調貨）：把庫存移到另一個庫位。同公司內可直接轉；跨公司請改用銷售單＋採購單。' },
    { match: /^(count( stock)?|盤點(庫存)?|清點)$/i, text: '盤點：輸入實際點到的數量，系統會自動計算差異並記錄。' },
    { match: /^(merge( stock)?|合併(庫存)?)$/i, text: '合併：把同一 SKU 在同庫位的多筆庫存合成一筆。' },
    { match: /^(change status|變更狀態|更改狀態)$/i, text: '變更狀態：標記為正常、損壞、隔離等。' },
    { match: /^(new stock item|add stock item|新增庫存項目|建立庫存項目)$/i, text: '新增庫存項目：手動建立一筆庫存（期初庫存用）。一般進貨請走採購單收貨。' },

    // --- 採購 / 銷售 ---
    { match: /^(new purchase order|add purchase order|新增採購單|建立採購單)$/i, text: '新增採購單：選擇供應商、填入要進貨的 SKU 與數量，並設定「目的地庫位」。' },
    { match: /^(receive( items| line items)?|收貨|接收)$/i, text: '收貨：勾選到貨的明細與數量，確認庫位後送出，庫存即自動增加。' },
    { match: /^(new sales order|add sales order|新增銷售單|建立銷售單)$/i, text: '新增銷售單：選擇客戶、加入要出貨的 SKU 與數量。' },
    { match: /^(new shipment|add shipment|新增出貨|建立出貨單|新增貨運)$/i, text: '新增出貨單：分配庫存前必須先建立出貨單。' },
    { match: /^(allocate( stock)?|分配(庫存)?)$/i, text: '分配庫存：從指定庫位保留要出貨的庫存，避免被別人用掉。' },
    { match: /^(complete shipment|完成出貨|完成貨運)$/i, text: '完成出貨：確認後庫存才會真正扣除，並記錄出貨時間與操作人。' },

    // --- 表格與通用 ---
    { match: /^(filters?|篩選|過濾)$/i, text: '篩選：可依庫位、狀態、參數（Style、Size）等條件縮小清單。' },
    { match: /^(download|export|下載|匯出|導出)/i, text: '匯出：把目前清單下載成 CSV／Excel。' },
    { match: /^(refresh|重新整理|刷新)$/i, text: '重新整理清單資料。' },
    { match: /^(edit|編輯)$/i, text: '編輯：修改目前資料。只有該公司的使用者能修改自家庫存。' },
    { match: /^(delete|刪除)$/i, text: '刪除：無法復原，請確認後再操作。庫存數量錯誤建議用「盤點」修正，不要刪除。' },
    { match: /^(submit|送出|提交|確定)$/i, text: '送出：確認無誤後送出，系統會記錄這次操作的時間與操作人。' },
    { match: /^(cancel|取消)$/i, text: '取消：不儲存任何變更。' },
    { match: /^(stock tracking|tracking|history|庫存追蹤|追蹤|歷史記錄|歷史)$/i, text: '異動紀錄：此項目所有入庫、出庫、轉移、盤點的時間與操作人。' },
    { match: /^(variants?|變體)$/i, text: '變體：此產品底下的所有樣式／尺寸 SKU。' },
    { match: /^(parameters?|參數)$/i, text: '參數：此 SKU 的樣式（Style）與尺寸（Size）。' },
    { match: /^(location|庫位|位置|儲存位置)$/i, text: '庫位：公司 → 倉庫。庫存歸屬以庫位判斷屬於哪間公司。' },
    { match: /^(quantity|數量)$/i, text: '數量：輸入本次要處理的數量，不可超過現有庫存。' },
    { match: /^(notes?|備註|說明)$/i, text: '備註：請寫明原因（例如：調貨給 B 公司、盤點差異），方便日後追查。' },
  ];

  // ===================== 共用工具 =====================
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* 忽略 */ } },
  };

  // 建立元素；只用 textContent，避免把資料庫內容當 HTML 執行
  function el(tag, props, children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([k, v]) => {
      if (v === null || v === undefined || v === false) return;   // 不要把 null 寫成字串 "null"
      if (k === 'style') Object.assign(node.style, v);
      else if (k === 'text') node.textContent = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    });
    (children || []).forEach((c) => c && node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c));
    return node;
  }

  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const localDay = (d) => d.toLocaleDateString('sv-SE'); // 本機日期 YYYY-MM-DD
  const today = () => localDay(new Date());

  const css = `
  .ith-tip{position:fixed;z-index:100002;max-width:300px;padding:8px 10px;border-radius:6px;
    background:#1f2937;color:#fff;font:13px/1.5 system-ui,"Microsoft JhengHei",sans-serif;
    box-shadow:0 4px 14px rgba(0,0,0,.25);pointer-events:none}
  #ith-dock{position:fixed;right:16px;bottom:16px;z-index:100001;display:flex;flex-direction:column;align-items:flex-end;gap:6px}
  #ith-dock-stack{display:none;flex-direction:column-reverse;align-items:flex-end;gap:6px}
  #ith-signal{width:40px;height:40px;border-radius:50%;border:none;cursor:pointer;color:#fff;background:#868e96;opacity:.55;
    font:600 14px system-ui,"Microsoft JhengHei",sans-serif;box-shadow:0 2px 8px rgba(0,0,0,.25);transition:opacity .15s;padding:0}
  #ith-signal.has-unread{background:#c92a2a;opacity:1}
  #ith-dock:hover #ith-signal,#ith-signal:focus-visible{opacity:1}
  .ith-fab{position:static;border:none;border-radius:20px;padding:8px 14px;white-space:nowrap;
    font:13px system-ui,"Microsoft JhengHei",sans-serif;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.2)}
  .ith-card{position:fixed;z-index:100003;background:#fff;color:#111;border-radius:10px;
    box-shadow:0 8px 30px rgba(0,0,0,.3);font:14px/1.6 system-ui,"Microsoft JhengHei",sans-serif}
  .ith-card h3{margin:0 0 8px;font-size:16px}
  .ith-card button{border:none;border-radius:6px;padding:6px 12px;cursor:pointer;font:inherit}
  .ith-primary{background:#228be6;color:#fff}
  .ith-plain{background:#e9ecef;color:#111}
  .ith-warn{background:#fff4e6;border-left:4px solid #fd7e14;padding:6px 8px;margin:8px 0}
  .ith-ok{background:#ebfbee;border-left:4px solid #40c057;padding:6px 8px;margin:8px 0}
  .ith-table{border-collapse:collapse;width:100%;font-size:13px}
  .ith-table th,.ith-table td{border-bottom:1px solid #e9ecef;padding:4px 6px;text-align:left;vertical-align:top}
  .ith-table th{position:sticky;top:0;background:#f8f9fa}
  .ith-card input,.ith-card select{font:inherit;padding:3px 6px;border:1px solid #ced4da;border-radius:4px}
  @media (prefers-color-scheme: dark){
    .ith-card{background:#25262b;color:#e9ecef}
    .ith-plain{background:#373a40;color:#e9ecef}
    .ith-warn{background:#3b2a16}.ith-ok{background:#1d3324}
    .ith-table th{background:#2c2e33}.ith-table th,.ith-table td{border-color:#373a40}
    .ith-card input,.ith-card select{background:#1a1b1e;color:#e9ecef;border-color:#495057}
  }`;
  document.head.appendChild(el('style', { text: css }));

  // ===================== 浮動面板：平常只顯示一個小圓點（未讀通知數），滑鼠移上去才展開功能按鈕 =====================
  const dock = el('div', { id: 'ith-dock' });
  const dockStack = el('div', { id: 'ith-dock-stack' });
  const signal = el('button', { id: 'ith-signal', 'aria-label': '庫存助手', 'aria-expanded': 'false', title: '庫存助手：滑鼠移到這裡顯示功能', text: '🔔' });
  dock.appendChild(dockStack);
  dock.appendChild(signal);
  document.body.appendChild(dock);

  let dockTimer = null;
  let dockPinned = false;   // 觸控裝置沒有「滑鼠移上去」，改為點一下展開
  const hoverless = () => !!(window.matchMedia && window.matchMedia('(hover: none)').matches);
  function setDock(open) {
    dockStack.style.display = open ? 'flex' : 'none';
    signal.setAttribute('aria-expanded', String(open));
  }
  const collapseSoon = () => { clearTimeout(dockTimer); dockTimer = setTimeout(() => setDock(false), 350); };
  dock.addEventListener('mouseenter', () => { clearTimeout(dockTimer); setDock(true); });
  dock.addEventListener('mouseleave', () => { if (!dockPinned) collapseSoon(); });
  dock.addEventListener('focusin', () => { clearTimeout(dockTimer); setDock(true); });
  dock.addEventListener('focusout', (e) => { if (!dockPinned && !dock.contains(e.relatedTarget)) collapseSoon(); });
  signal.addEventListener('click', () => {
    if (hoverless()) { dockPinned = !dockPinned; setDock(dockPinned); } else { togglePanel(); }   // 滑鼠：點圓點直接看通知
  });
  document.addEventListener('pointerdown', (e) => { if (dockPinned && !dock.contains(e.target)) { dockPinned = false; setDock(false); } }, true);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { dockPinned = false; setDock(false); } });

  // ===================== 1. 滑鼠停留說明 =====================
  let hintsOn = store.get('ith-hints-on', true);
  let tip = null;
  let tipTimer = null;
  const TARGETS = 'button, a, [role="tab"], [role="menuitem"], [role="button"], [role="option"], label, th';

  function labelOf(node) {
    const aria = node.getAttribute('aria-label') || node.getAttribute('title') || '';
    const text = norm(node.textContent);
    return [norm(aria), text.length <= 40 ? text : ''].filter(Boolean);
  }

  function findHelp(node) {
    for (const label of labelOf(node)) {
      const rule = HELP.find((r) => r.match.test(label));
      if (rule) return rule.text;
    }
    return null;
  }

  function hideTip() {
    clearTimeout(tipTimer);
    if (tip) { tip.remove(); tip = null; }
  }

  document.addEventListener('mouseover', (e) => {
    if (!hintsOn) return;
    const target = e.target.closest && e.target.closest(TARGETS);
    if (!target || target.closest('.ith-card')) return;
    const text = findHelp(target);
    if (!text) return;
    hideTip();
    tipTimer = setTimeout(() => {
      const r = target.getBoundingClientRect();
      tip = el('div', { class: 'ith-tip', role: 'tooltip', text: '💡 ' + text });
      document.body.appendChild(tip);
      const top = r.bottom + 8 + tip.offsetHeight > window.innerHeight ? r.top - tip.offsetHeight - 8 : r.bottom + 8;
      const left = Math.min(Math.max(8, r.left), window.innerWidth - tip.offsetWidth - 8);
      tip.style.top = top + 'px';
      tip.style.left = left + 'px';
    }, CONFIG.hoverDelayMs);
  }, true);

  document.addEventListener('mouseout', (e) => {
    const target = e.target.closest && e.target.closest(TARGETS);
    if (target && !target.contains(e.relatedTarget)) hideTip();
  }, true);
  document.addEventListener('mousedown', hideTip, true);

  const hintBtn = el('button', {
    class: 'ith-fab',
    title: '開關滑鼠停留時的中文操作說明',
    onclick: () => { hintsOn = !hintsOn; store.set('ith-hints-on', hintsOn); paintHintBtn(); hideTip(); },
  });
  function paintHintBtn() {
    hintBtn.textContent = hintsOn ? '💡 操作說明：開' : '💡 操作說明：關';
    hintBtn.style.background = hintsOn ? '#228be6' : '#868e96';
    hintBtn.style.color = '#fff';
  }
  paintHintBtn();
  dockStack.appendChild(hintBtn);

  // ===================== 2. 調貨（轉移庫存）提醒 =====================
  const TRANSFER_TITLE = /transfer|轉移|移動庫存|調撥|調貨/i;
  const watched = new WeakSet();

  function dialogTitle(dialog) {
    const t = dialog.querySelector('.mantine-Modal-title, [class*="Modal-title"], h2, h3, header');
    return norm(t ? t.textContent : '');
  }

  function companiesIn(text) {
    return CONFIG.companies.filter((c) => text.includes(c));
  }

  // 從視窗內容推斷「來源公司」與「目的公司」
  function analyse(dialog) {
    const rows = dialog.querySelectorAll('tbody tr');
    const sourceText = Array.from(rows).map((r) => r.textContent).join(' ');
    const destText = Array.from(dialog.querySelectorAll('input'))
      .map((i) => i.value || '').join(' ') +
      ' ' + Array.from(dialog.querySelectorAll('[class*="Select"] [class*="value"], [class*="Pill"]'))
        .map((n) => n.textContent).join(' ');
    return {
      itemCount: rows.length,
      sources: companiesIn(sourceText),
      dests: companiesIn(destText),
    };
  }

  function showTransferReminder(dialog) {
    if (store.get('ith-transfer-mute', '') === today()) return;

    const status = el('div', { class: 'ith-ok', text: '請選擇目的庫位。' });
    const mute = el('input', { type: 'checkbox', id: 'ith-mute' });
    const card = el('div', {
      class: 'ith-card', role: 'alertdialog', 'aria-label': '調貨提醒',
      style: { top: '16px', right: '16px', width: '320px', padding: '14px 16px' },
    }, [
      el('h3', { text: '📦 調貨提醒' }),
      el('div', { text: '送出前請確認：' }),
      el('ol', { style: { margin: '4px 0', paddingLeft: '20px' } }, [
        el('li', { text: '目的庫位正確（公司 → 倉庫）。' }),
        el('li', { text: '每筆數量不超過現有庫存。' }),
        el('li', { text: '備註寫明原因，例如「補貨給 B 公司門市」。' }),
        el('li', { text: '跨公司調貨請改用「銷售單＋採購單」，進出貨數字才會正確。' }),
      ]),
      status,
      el('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '8px' } }, [
        el('label', { for: 'ith-mute', style: { fontSize: '12px' } }, [mute, ' 今天不再提醒']),
        el('button', {
          class: 'ith-primary', text: '我知道了',
          onclick: () => { if (mute.checked) store.set('ith-transfer-mute', today()); close(); },
        }),
      ]),
    ]);
    document.body.appendChild(card);

    // 動態更新：每 0.7 秒依視窗內容更新狀態，視窗關閉時自動收起
    const timer = setInterval(() => {
      if (!document.body.contains(dialog)) { close(); return; }
      const a = analyse(dialog);
      const parts = [`本次轉移 ${a.itemCount} 筆庫存`];
      if (a.sources.length) parts.push(`來源：${a.sources.join('、')}`);
      if (a.dests.length) parts.push(`目的：${a.dests.join('、')}`);
      const cross = a.dests.length && a.sources.some((s) => !a.dests.includes(s));
      status.className = cross ? 'ith-warn' : 'ith-ok';
      status.textContent = parts.join('｜') +
        (cross ? '。⚠️ 這是跨公司調貨！請改用銷售單＋採購單。' : a.dests.length ? '。✅ 同公司內調貨。' : '。請選擇目的庫位。');
    }, 700);

    function close() { clearInterval(timer); card.remove(); }
  }

  new MutationObserver(() => {
    document.querySelectorAll('[role="dialog"], .mantine-Modal-content').forEach((d) => {
      const dialog = d.closest('[role="dialog"]') || d;
      if (watched.has(dialog) || dialog.closest('.ith-card')) return;
      if (!TRANSFER_TITLE.test(dialogTitle(dialog))) return;
      watched.add(dialog);
      showTransferReminder(dialog);
    });
  }).observe(document.body, { childList: true, subtree: true });

  // ===================== 3. 全部異動紀錄 =====================
  const TRACK_FIELDS = {
    quantity: '數量', added: '增加', removed: '減少', location: '庫位',
    status: '狀態', stockitem: '庫存項目', purchaseorder: '採購單', salesorder: '銷售單',
    customer: '客戶', buildorder: '生產單',
  };

  // 伺服器回傳的異動類型（英文）轉成中文；沒列到的保留原文
  const ACTION_ZH = [
    // 較具體的放前面，避免被通用字詞先比對到
    [/removed from assembly|uninstalled/i, '拆卸'], [/installed/i, '安裝'],
    [/received.*purchase/i, '採購收貨'], [/shipped.*sales|sales order/i, '銷售出貨'],
    [/assigned to customer/i, '指派給客戶'], [/returned/i, '退回入庫'],
    [/created/i, '建立庫存'], [/counted/i, '盤點'], [/added/i, '增加庫存'], [/removed/i, '減少庫存'],
    [/location changed|moved/i, '轉移庫位'], [/split/i, '拆分'], [/merged/i, '合併'],
    [/status/i, '變更狀態'], [/updated|edited/i, '更新資料'],
  ];
  const actionZh = (s) => { const m = ACTION_ZH.find(([re]) => re.test(s)); return m ? `${m[1]}（${s}）` : s; };

  async function api(path) {
    const res = await fetch(path, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
    if (res.status === 401 || res.status === 403) throw new Error('沒有權限或尚未登入，請重新登入 InvenTree。');
    if (!res.ok) throw new Error(`讀取失敗（${res.status}）：${path}`);
    return res.json();
  }

  // 讀取分頁 API；onPage 回傳 false 時停止
  async function fetchAll(base, onPage) {
    let offset = 0;
    const sep = base.includes('?') ? '&' : '?';
    for (;;) {
      const data = await api(`${base}${sep}limit=200&offset=${offset}`);
      const rows = Array.isArray(data) ? data : data.results || [];
      if (onPage(rows) === false || Array.isArray(data) || !data.next || !rows.length) return;
      offset += rows.length;
    }
  }

  async function loadAudit(f, setMsg) {
    const locations = {};
    await fetchAll('/api/stock/location/', (rows) => rows.forEach((l) => { locations[l.pk] = l.pathstring || l.name; }));
    const parts = {};
    await fetchAll('/api/part/', (rows) => rows.forEach((p) => { parts[p.pk] = p; }));

    const out = [];
    await fetchAll('/api/stock/track/?ordering=-date&item_detail=true&user_detail=true', (rows) => {
      for (const t of rows) {
        // 轉成本機時間（伺服器回傳的是含時區的時間戳），格式 YYYY-MM-DD HH:mm:ss
        const d = new Date(t.date);
        const local = isNaN(d) ? String(t.date || '') : d.toLocaleString('sv-SE', { hour12: false });
        const day = local.slice(0, 10);
        if (f.to && day > f.to) continue;
        if (f.from && day < f.from) return false; // 依日期新到舊排序，已超出範圍
        const item = t.item_detail || {};
        const deltas = t.deltas || {};
        const locId = deltas.location || item.location;
        const loc = locations[locId] || '';
        const part = parts[item.part] || {};
        const user = (t.user_detail && (t.user_detail.username || t.user_detail.first_name)) || t.user || '系統';
        const row = {
          time: local,
          user: String(user),
          action: actionZh(t.label || t.tracking_type_text || String(t.tracking_type || '')),
          ipn: part.IPN || '',
          name: part.full_name || part.name || (item.part ? `#${item.part}` : ''),
          location: loc,
          detail: Object.entries(deltas)
            .map(([k, v]) => `${TRACK_FIELDS[k] || k}：${k === 'location' ? locations[v] || v : v}`).join('；'),
          notes: t.notes || '',
        };
        if (f.company && !loc.startsWith(f.company)) continue;
        if (f.user && !row.user.toLowerCase().includes(f.user.toLowerCase())) continue;
        if (f.keyword && !(row.ipn + row.name).toLowerCase().includes(f.keyword.toLowerCase())) continue;
        out.push(row);
        if (out.length >= CONFIG.auditMaxRows) return false;
      }
      setMsg(`讀取中…已找到 ${out.length} 筆`);
      return true;
    });
    return out;
  }

  const COLS = [['time', '時間'], ['user', '操作人'], ['action', '動作'], ['ipn', '料號'],
    ['name', '品名'], ['location', '庫位'], ['detail', '異動內容'], ['notes', '備註']];

  function exportCsv(rows) {
    const q = (v) => `"${String(v).replace(/"/g, '""')}"`;
    const csv = '﻿' + [COLS.map((c) => q(c[1])).join(',')]
      .concat(rows.map((r) => COLS.map((c) => q(r[c[0]])).join(','))).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `stock-history_${today()}.csv`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { a.remove(); URL.revokeObjectURL(url); }, 1000);
  }

  function openAudit() {
    if (document.querySelector('.ith-audit')) return;
    const from = el('input', { type: 'date', value: localDay(new Date(Date.now() - 7 * 864e5)) });
    const to = el('input', { type: 'date', value: today() });
    const company = el('select', {}, [el('option', { value: '', text: '全部公司' })]
      .concat(CONFIG.companies.map((c) => el('option', { value: c, text: c }))));
    const user = el('input', { placeholder: '操作人', style: { width: '90px' } });
    const keyword = el('input', { placeholder: '料號或品名', style: { width: '120px' } });
    const msg = el('div', { style: { margin: '6px 0', fontSize: '13px' } });
    const tableBox = el('div', { style: { flex: '1', overflow: 'auto' } });
    let last = [];
    const csvBtn = el('button', { class: 'ith-plain', text: '匯出 CSV', disabled: 'disabled', onclick: () => exportCsv(last) });

    async function run() {
      msg.textContent = '讀取中…';
      tableBox.textContent = '';
      csvBtn.setAttribute('disabled', 'disabled');
      try {
        last = await loadAudit({ from: from.value, to: to.value, company: company.value, user: user.value, keyword: keyword.value },
          (t) => { msg.textContent = t; });
        msg.textContent = `共 ${last.length} 筆` + (last.length >= CONFIG.auditMaxRows ? `（已達上限 ${CONFIG.auditMaxRows} 筆，請縮小日期範圍）` : '');
        const table = el('table', { class: 'ith-table' }, [
          el('thead', {}, [el('tr', {}, COLS.map((c) => el('th', { text: c[1] })))]),
          el('tbody', {}, last.map((r) => el('tr', {}, COLS.map((c) => el('td', { text: r[c[0]] }))))),
        ]);
        tableBox.appendChild(table);
        if (last.length) csvBtn.removeAttribute('disabled');
      } catch (e) {
        msg.textContent = '⚠️ ' + e.message;
      }
    }

    const card = el('div', {
      class: 'ith-card ith-audit', role: 'dialog', 'aria-label': '全部異動紀錄',
      style: { inset: '5vh 5vw', padding: '16px', display: 'flex', flexDirection: 'column' },
    }, [
      el('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' } }, [
        el('h3', { text: '📋 全部異動紀錄（時間・操作人）' }),
        el('button', { class: 'ith-plain', text: '關閉', onclick: () => card.remove() }),
      ]),
      el('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' } }, [
        '從', from, '到', to, company, user, keyword,
        el('button', { class: 'ith-primary', text: '查詢', onclick: run }), csvBtn,
      ]),
      msg, tableBox,
    ]);
    document.body.appendChild(card);
    run();
  }

  dockStack.appendChild(el('button', {
    class: 'ith-fab', style: { background: '#495057', color: '#fff' },
    title: '查詢所有庫存異動：時間、操作人、數量、庫位', text: '📋 異動紀錄', onclick: openAudit,
  }));

  // ===================== 4. 異常數量警告 =====================
  // InvenTree 1.5.6 伺服器端不會擋「超過現有庫存」：移除會默默扣到 0、轉移會整批搬走。
  // 因此在送出前檢查：大量（≥ CONFIG.largeQty）、超量、歸零，跳出確認視窗。

  const ADJUST_KINDS = [
    { kind: 'transfer', re: /transfer|轉移|移動|調撥|調貨/i },
    { kind: 'remove', re: /remove|移除|減少|扣除/i },
    { kind: 'count', re: /count|盤點|清點|計數/i },
    { kind: 'add', re: /\badd\b|新增庫存|增加|添加/i },
  ];
  const SUBMIT_RE = /^(submit|送出|提交|確定|確認|儲存|保存|save)$/i;

  // 純邏輯：依操作種類、輸入數量、現有數量回傳警告清單（供測試直接呼叫）
  function evaluateAdjust(kind, value, existing, largeQty) {
    const warnings = [];
    const v = Number(value);
    const has = existing !== null && existing !== undefined && !isNaN(Number(existing));
    const ex = has ? Number(existing) : null;
    if (isNaN(v)) return warnings;
    if (v >= largeQty) warnings.push({ type: 'large', text: `大量異動：${v} 件（≥ ${largeQty}）` });
    if (kind === 'transfer' || kind === 'remove') {
      if (has && v > ex) {
        warnings.push({ type: 'over', text: `超量：輸入 ${v}，現有只有 ${ex}。系統不會報錯，會${kind === 'remove' ? '直接扣到 0' : '把整批 ' + ex + ' 件全部轉走'}` });
      } else if (has && v === ex && v > 0) {
        warnings.push({ type: 'zero', text: `歸零：${kind === 'remove' ? '移除後' : '轉出後'}原庫位此批庫存將變成 0` });
      }
    }
    if (kind === 'count' && v === 0) warnings.push({ type: 'zero', text: '歸零：盤點數量為 0，庫存將被清空' });
    return warnings;
  }

  // 共用確認視窗：回傳 Promise<boolean>
  function askConfirm(title, lines) {
    return new Promise((resolve) => {
      const finish = (ok) => { mask.remove(); resolve(ok); };
      const mask = el('div', {
        class: 'ith-mask', style: { position: 'fixed', inset: '0', background: 'rgba(0,0,0,.45)', zIndex: '100004' },
      });
      const card = el('div', {
        class: 'ith-card', role: 'alertdialog', 'aria-label': '異常操作確認',
        style: { top: '50%', left: '50%', transform: 'translate(-50%,-50%)', width: 'min(420px, calc(100vw - 32px))', padding: '16px 18px' },
      }, [
        el('h3', { text: '⚠️ ' + title }),
        el('div', {}, lines.map((t) => el('div', { class: 'ith-warn', text: t }))),
        el('div', { text: '確定要繼續這個操作嗎？', style: { margin: '8px 0' } }),
        el('div', { style: { display: 'flex', justifyContent: 'flex-end', gap: '8px' } }, [
          el('button', { class: 'ith-plain', text: '取消，回去修改', onclick: () => finish(false) }),
          el('button', { class: 'ith-primary', style: { background: '#e8590c' }, text: '確認繼續', onclick: () => finish(true) }),
        ]),
      ]);
      mask.appendChild(card);
      document.body.appendChild(mask);
      card.querySelector('.ith-plain').focus();
    });
  }

  function adjustKindOf(dialog) {
    const title = dialogTitle(dialog);
    const hit = ADJUST_KINDS.find((k) => k.re.test(title));
    return hit ? hit.kind : null;
  }

  // 從列中找現有數量：優先讀庫存項目連結（/stock/item/<pk>）向 API 查；否則取列中唯一的純數字欄位
  async function existingQtyOf(row) {
    const link = row.querySelector('a[href*="/stock/item/"]');
    const m = link && link.getAttribute('href').match(/\/stock\/item\/(\d+)/);
    if (m) {
      try { const item = await api(`/api/stock/${m[1]}/`); if (item && item.quantity !== undefined) return Number(item.quantity); } catch (e) { /* 改用畫面判斷 */ }
    }
    const nums = Array.from(row.querySelectorAll('td'))
      .filter((td) => !td.querySelector('input, select, textarea'))
      .map((td) => norm(td.textContent).replace(/,/g, ''))
      .filter((t) => /^\d+(\.\d+)?$/.test(t));
    return nums.length === 1 ? Number(nums[0]) : null;
  }

  async function collectWarnings(dialog, kind) {
    const lines = [];
    const rows = Array.from(dialog.querySelectorAll('tbody tr')).filter((r) => r.querySelector('input'));
    const targets = rows.length ? rows : [dialog];
    for (const row of targets) {
      const input = row.querySelector('input[type="number"], input[inputmode="decimal"], input[inputmode="numeric"]') ||
        Array.from(row.querySelectorAll('input')).find((i) => /^\s*\d+(\.\d+)?\s*$/.test(i.value));
      if (!input || input.value === '') continue;
      const existing = row === dialog ? null : await existingQtyOf(row);
      const label = row === dialog ? '' : (norm(row.querySelector('td') && row.querySelector('td').textContent) || '').slice(0, 30);
      evaluateAdjust(kind, input.value, existing, CONFIG.largeQty)
        .forEach((w) => lines.push((label ? `【${label}】` : '') + w.text));
    }
    return lines;
  }

  // 攔截 InvenTree 庫存操作視窗的「送出」：有異常先確認，確認後再放行
  document.addEventListener('click', async (e) => {
    const btn = e.target.closest && e.target.closest('button');
    if (!btn || btn.closest('.ith-card')) return;
    const dialog = btn.closest('[role="dialog"], .mantine-Modal-content');
    if (!dialog) return;
    const isSubmit = btn.type === 'submit' || SUBMIT_RE.test(norm(btn.textContent));
    if (!isSubmit) return;
    if (btn.__ithApproved) { btn.__ithApproved = false; return; }
    const kind = adjustKindOf(dialog.closest('[role="dialog"]') || dialog);
    if (!kind) return;

    e.preventDefault();
    e.stopImmediatePropagation();
    const lines = await collectWarnings(dialog, kind);
    if (lines.length && !(await askConfirm('偵測到異常數量', lines))) return;
    btn.__ithApproved = true;
    btn.click();
  }, true);

  // 在數量欄位按 Enter 也會送出：改為觸發「送出」按鈕，讓它同樣經過上面的檢查
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' || e.isComposing || !e.target.closest || e.target.tagName !== 'INPUT') return;
    const dialog = e.target.closest('[role="dialog"], .mantine-Modal-content');
    if (!dialog || dialog.closest('.ith-card') || !adjustKindOf(dialog.closest('[role="dialog"]') || dialog)) return;
    const btn = Array.from(dialog.querySelectorAll('button'))
      .find((b) => b.type === 'submit' || SUBMIT_RE.test(norm(b.textContent)));
    if (!btn) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    btn.click();
  }, true);

  // ===================== 5. 快速調貨 =====================
  const COMPANY_COLORS = ['#228be6', '#40c057', '#fab005', '#be4bdb', '#fd7e14'];
  const companyOf = (path) => CONFIG.companies.find((c) => (path || '').startsWith(c)) || '其他';
  const colorOf = (company) => {
    const i = CONFIG.companies.indexOf(company);
    return i >= 0 ? COMPANY_COLORS[i % COMPANY_COLORS.length] : '#868e96';
  };

  function csrfToken() {
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  async function apiPost(path, body) {
    const res = await fetch(path, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-CSRFToken': csrfToken() },
      body: JSON.stringify(body),
    });
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = text; }
    if (!res.ok) {
      const detail = data && typeof data === 'object' ? JSON.stringify(data) : String(data || '');
      throw new Error(res.status === 403 ? '沒有權限執行此操作（只有該公司的使用者能修改自家庫存）。' : `操作失敗（${res.status}）：${detail.slice(0, 300)}`);
    }
    return data;
  }

  function openQuickTransfer() {
    if (document.querySelector('.ith-qt')) return;
    const state = { part: null, items: [], source: null, locations: [] };

    const search = el('input', { placeholder: '輸入料號或品名，例如 A-P03-S2', style: { width: '100%' }, 'aria-label': '搜尋料號或品名' });
    const results = el('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px', margin: '6px 0' } });
    const stockBox = el('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '10px', margin: '8px 0' } });
    const dest = el('select', { 'aria-label': '目的庫位', style: { minWidth: '220px' } });
    const qty = el('input', { type: 'number', min: '1', step: '1', 'aria-label': '數量', style: { width: '100px' } });
    const allBtn = el('button', { class: 'ith-plain', text: '全部', title: '填入來源庫存的全部數量' });
    const notes = el('input', { placeholder: '備註／原因（例：補貨給 B 公司門市）', 'aria-label': '備註', style: { flex: '1', minWidth: '200px' } });
    const summary = el('div', { class: 'ith-ok', text: '① 搜尋並選擇產品。' });
    const sendBtn = el('button', { class: 'ith-primary', text: '確認調貨', disabled: 'disabled' });
    const msg = el('div', { style: { fontSize: '13px', minHeight: '18px' } });

    let timer = null;
    search.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(doSearch, 300);
    });

    async function doSearch() {
      const q = search.value.trim();
      results.textContent = '';
      if (q.length < 2) return;
      try {
        const data = await api(`/api/part/?search=${encodeURIComponent(q)}&active=true&limit=30`);
        // 只列出能存放庫存、且仍在使用的 SKU（已停用的零件不出現）
        const parts = (Array.isArray(data) ? data : data.results || []).filter((p) => !p.is_template && p.active !== false);
        if (!parts.length) { results.appendChild(el('span', { text: '找不到符合的產品（只列出可存放庫存的 SKU）。' })); return; }
        parts.slice(0, 20).forEach((p) => results.appendChild(el('button', {
          class: 'ith-plain', text: `${p.IPN || ''} ${p.full_name || p.name}`.trim(), onclick: () => selectPart(p),
        })));
      } catch (e) { msg.textContent = '⚠️ ' + e.message; }
    }

    async function loadLocations() {
      const out = [];
      await fetchAll('/api/stock/location/', (rows) => { rows.forEach((l) => out.push(l)); });
      state.locations = out.filter((l) => !l.structural)
        .map((l) => ({ pk: l.pk, path: l.pathstring || l.name }))
        .sort((a, b) => a.path.localeCompare(b.path, 'zh-Hant'));
      dest.textContent = '';
      dest.appendChild(el('option', { value: '', text: '② 選擇目的庫位' }));
      const groups = {};
      state.locations.forEach((l) => {
        const c = companyOf(l.path);
        if (!groups[c]) { groups[c] = el('optgroup', { label: c }); dest.appendChild(groups[c]); }
        groups[c].appendChild(el('option', { value: String(l.pk), text: l.path }));
      });
    }

    async function selectPart(p) {
      state.part = p;
      state.source = null;
      results.textContent = '';
      search.value = `${p.IPN || ''} ${p.full_name || p.name}`.trim();
      await loadStock();
    }

    async function loadStock() {
      stockBox.textContent = '讀取庫存中…';
      try {
        const data = await api(`/api/stock/?part=${state.part.pk}&in_stock=true&location_detail=true&limit=200`);
        state.items = (Array.isArray(data) ? data : data.results || [])
          .map((s) => ({ pk: s.pk, qty: Number(s.quantity), path: (s.location_detail && s.location_detail.pathstring) || '（未指定庫位）', location: s.location }))
          .filter((s) => s.qty > 0);
      } catch (e) { stockBox.textContent = '⚠️ ' + e.message; return; }
      renderStock();
      update();
    }

    function renderStock() {
      stockBox.textContent = '';
      const byCompany = {};
      CONFIG.companies.forEach((c) => { byCompany[c] = []; });
      state.items.forEach((s) => { const c = companyOf(s.path); (byCompany[c] = byCompany[c] || []).push(s); });
      Object.keys(byCompany).forEach((c) => {
        const items = byCompany[c];
        const total = items.reduce((n, s) => n + s.qty, 0);
        const card = el('div', {
          class: 'ith-qt-company',
          style: { border: `2px solid ${colorOf(c)}`, borderRadius: '8px', padding: '8px 10px', minWidth: '180px', flex: '1' },
        }, [
          el('div', { style: { fontWeight: '600', color: colorOf(c) }, text: `${c}　共 ${total} 件` }),
        ]);
        if (!items.length) card.appendChild(el('div', { style: { fontSize: '12px', opacity: '.7' }, text: '無庫存' }));
        items.forEach((s) => {
          const id = `ith-src-${s.pk}`;
          const radio = el('input', { type: 'radio', name: 'ith-src', id, value: String(s.pk) });
          if (state.source && state.source.pk === s.pk) radio.checked = true;
          radio.addEventListener('change', () => { state.source = s; update(); });
          card.appendChild(el('label', { for: id, style: { display: 'block', cursor: 'pointer', fontSize: '13px' } },
            [radio, ` ${s.path}：${s.qty} 件`]));
        });
        stockBox.appendChild(card);
      });
    }

    function currentWarnings() {
      const s = state.source;
      const v = Number(qty.value);
      const d = state.locations.find((l) => String(l.pk) === dest.value);
      const lines = evaluateAdjust('transfer', v, s ? s.qty : null, CONFIG.largeQty).map((w) => w.text);
      if (s && d && companyOf(s.path) !== companyOf(d.path)) {
        lines.unshift(`跨公司調貨：${companyOf(s.path)} → ${companyOf(d.path)}（進出貨統計不會計入，若需計入請改用銷售單＋採購單）`);
      }
      return { s, d, v, lines };
    }

    function update() {
      const { s, d, v, lines } = currentWarnings();
      let problem = '';
      if (!state.part) problem = '① 搜尋並選擇產品。';
      else if (!state.items.length) problem = '此產品目前沒有庫存可調。';
      else if (!s) problem = '② 點選要調出的來源庫位。';
      else if (!d) problem = '③ 選擇目的庫位。';
      else if (d.pk === s.location) problem = '來源與目的庫位相同。';
      else if (!(v > 0)) problem = '④ 輸入大於 0 的數量。';

      if (problem) {
        summary.className = 'ith-ok';
        summary.textContent = problem;
        sendBtn.setAttribute('disabled', 'disabled');
        return;
      }
      summary.className = lines.length ? 'ith-warn' : 'ith-ok';
      summary.textContent = `${s.path} → ${d.path}，${v} 件` + (lines.length ? '｜' + lines.join('｜') : '｜✅ 無異常');
      sendBtn.removeAttribute('disabled');
    }

    [dest, qty, notes].forEach((n) => n.addEventListener('input', update));
    dest.addEventListener('change', update);
    allBtn.addEventListener('click', () => { if (state.source) { qty.value = String(state.source.qty); update(); } });

    sendBtn.addEventListener('click', async () => {
      const { s, d, v, lines } = currentWarnings();
      if (!s || !d || !(v > 0)) return;
      if (lines.length && !(await askConfirm('調貨前請確認', lines))) return;
      // 超量時以現有數量送出（與 InvenTree 實際行為一致，且紀錄正確）
      const sendQty = Math.min(v, s.qty);
      sendBtn.setAttribute('disabled', 'disabled');
      msg.textContent = '調貨中…';
      try {
        await apiPost('/api/stock/transfer/', {
          items: [{ pk: s.pk, quantity: sendQty }],
          location: d.pk,
          notes: notes.value.trim() || `快速調貨：${s.path} → ${d.path}`,
        });
        msg.textContent = `✅ 已調貨 ${sendQty} 件：${s.path} → ${d.path}（已記錄時間與操作人）`;
        state.source = null;
        qty.value = '';
        await loadStock();
      } catch (e) {
        msg.textContent = '⚠️ ' + e.message;
        update();
      }
    });

    const card = el('div', {
      class: 'ith-card ith-qt', role: 'dialog', 'aria-label': '快速調貨',
      style: { top: '6vh', left: '50%', transform: 'translateX(-50%)', width: 'min(760px, calc(100vw - 32px))', maxHeight: '88vh', overflow: 'auto', padding: '16px' },
    }, [
      el('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' } }, [
        el('h3', { text: '🔀 快速調貨' }),
        el('button', { class: 'ith-plain', text: '關閉', onclick: () => card.remove() }),
      ]),
      search, results,
      el('div', { style: { fontSize: '13px', opacity: '.8' }, text: '目前庫存（點選來源庫位）：' }),
      stockBox,
      el('div', { style: { display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' } }, [
        '目的', dest, '數量', qty, allBtn,
      ]),
      el('div', { style: { display: 'flex', gap: '6px', margin: '6px 0' } }, [notes]),
      summary,
      el('div', { style: { display: 'flex', justifyContent: 'flex-end', gap: '8px', alignItems: 'center' } }, [msg, sendBtn]),
    ]);
    document.body.appendChild(card);
    search.focus();
    loadLocations().catch((e) => { msg.textContent = '⚠️ ' + e.message; });
  }

  dockStack.appendChild(el('button', {
    class: 'ith-fab', style: { background: '#e8590c', color: '#fff' },
    title: '快速把庫存從一個庫位調到另一個庫位（可跨公司）', text: '🔀 快速調貨', onclick: openQuickTransfer,
  }));

  // ===================== 6. 通知（小視窗與通知清單） =====================
  // 事件由伺服器端的「通知服務」（/notify/）依使用者所屬公司挑選；已讀紀錄存在伺服器，換電腦也一致。
  const NOTIFY_API = '/notify/api';
  const SEV_COLOR = { danger: '#e03131', warn: '#f08c00', info: '#228be6' };
  const notify = { items: [], unread: 0, user: null, warnings: [], state: 'loading', toasted: new Set(), first: true, open: false, panel: null };

  const badge = el('span', { style: { display: 'none', marginLeft: '6px', background: '#e03131', color: '#fff', borderRadius: '10px', padding: '0 7px', fontSize: '12px' } });
  const bell = el('button', {
    class: 'ith-fab', 'aria-label': '通知', style: { background: '#495057', color: '#fff' },
    title: '查看與你的公司有關的通知', onclick: () => togglePanel(),
  }, [el('span', { text: '🔔 通知' }), badge]);
  dockStack.appendChild(bell);
  const toastBox = el('div', { style: { position: 'fixed', top: '16px', right: '16px', zIndex: '100005', display: 'flex', flexDirection: 'column', gap: '8px', width: 'min(340px, calc(100vw - 32px))' } });
  document.body.appendChild(toastBox);

  function paintBell() {
    dock.style.display = notify.state === 'anon' ? 'none' : '';   // 還沒登入（登入頁）時整個面板不顯示
    signal.textContent = notify.unread > 0 ? (notify.unread > 99 ? '99+' : String(notify.unread)) : '🔔';
    signal.classList.toggle('has-unread', notify.unread > 0);
    signal.style.fontSize = notify.unread > 99 ? '12px' : '';
    badge.style.display = notify.unread > 0 ? '' : 'none';
    badge.textContent = notify.unread > 99 ? '99+' : (notify.unread > 0 ? String(notify.unread) : '');
    bell.style.background = notify.state === 'ok' ? (notify.unread > 0 ? '#c92a2a' : '#495057') : '#868e96';
    bell.title = {
      ok: notify.unread > 0 ? `有 ${notify.unread} 則未讀通知` : '沒有未讀通知',
      unavailable: '通知服務尚未啟用（請讓管理員重新執行 setup-server.ps1）',
      error: '暫時無法取得通知，稍後會自動重試',
      loading: '讀取通知中…',
    }[notify.state] || '通知';
    signal.title = `${bell.title}（滑鼠移到這裡顯示功能，點一下查看通知）`;
  }

  const localTime = (iso) => { const d = new Date(iso); return isNaN(d) ? '' : d.toLocaleString('sv-SE', { hour12: false }).slice(5, 16); };

  function showToast(item, onOpen) {
    const color = SEV_COLOR[item.severity] || SEV_COLOR.info;
    const toast = el('div', {
      class: 'ith-card ith-toast', role: 'status',
      style: { position: 'static', borderLeft: `5px solid ${color}`, padding: '10px 12px', cursor: 'pointer' },
      onclick: () => { toast.remove(); (onOpen || openPanel)(); },
    }, [
      el('div', { style: { display: 'flex', justifyContent: 'space-between', gap: '8px' } }, [
        el('div', { style: { fontWeight: '600' }, text: item.title }),
        el('button', { class: 'ith-plain', 'aria-label': '關閉', text: '✕', style: { padding: '0 6px' }, onclick: (e) => { e.stopPropagation(); toast.remove(); } }),
      ]),
      item.detail ? el('div', { style: { fontSize: '12px', opacity: '.8', marginTop: '2px' }, text: item.detail }) : null,
    ]);
    toastBox.appendChild(toast);
    while (toastBox.children.length > 4) toastBox.firstChild.remove();
    if (item.severity !== 'danger') setTimeout(() => toast.remove(), 12000);   // 異常（大量／歸零）要自己關閉
  }

  function toastNew() {
    const unread = notify.items.filter((i) => !i.read);
    if (notify.first) {
      notify.first = false;
      unread.forEach((i) => notify.toasted.add(i.id));
      if (unread.length) showToast({ title: `🔔 您有 ${unread.length} 則未讀通知`, detail: '點這裡查看', severity: unread.some((i) => i.severity === 'danger') ? 'danger' : 'info' });
      return;
    }
    const fresh = unread.filter((i) => !notify.toasted.has(i.id));
    fresh.forEach((i) => notify.toasted.add(i.id));
    fresh.slice(0, 3).forEach((i) => showToast(i));
    if (fresh.length > 3) showToast({ title: `🔔 另有 ${fresh.length - 3} 則新通知`, detail: '點這裡查看全部', severity: 'info' });
  }

  async function notifyPoll() {
    try {
      const res = await fetch(`${NOTIFY_API}/feed`, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
      if (res.status === 401) { notify.state = 'anon'; notify.items = []; notify.unread = 0; }
      else if (res.status === 404) { notify.state = 'unavailable'; }
      else if (!res.ok) { notify.state = 'error'; }
      else {
        const data = await res.json();
        notify.state = 'ok';
        notify.items = data.items || [];
        notify.unread = data.unread || 0;
        notify.user = data.user || null;
        notify.warnings = data.warnings || [];
        toastNew();
      }
    } catch (e) {
      notify.state = 'error';
    }
    paintBell();
    if (notify.open) renderPanel();
  }

  async function markRead(body) {
    try {
      await fetch(`${NOTIFY_API}/read`, {
        method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'inventory-helper' },
        body: JSON.stringify(body),
      });
    } catch (e) { /* 下一次輪詢會同步最新狀態 */ }
    await notifyPoll();
  }

  function renderPanel() {
    if (!notify.panel) return;
    const p = notify.panel;
    p.textContent = '';
    const maxId = Math.max(0, ...notify.items.filter((i) => /^\d+$/.test(i.id)).map((i) => Number(i.id)));
    p.appendChild(el('div', { style: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' } }, [
      el('h3', { style: { margin: '0' }, text: `🔔 通知${notify.unread ? `（未讀 ${notify.unread}）` : ''}` }),
      el('div', { style: { display: 'flex', gap: '6px' } }, [
        el('button', { class: 'ith-plain', text: '全部已讀', disabled: notify.unread ? null : 'disabled',
          onclick: () => { notify.items.forEach((i) => { i.read = true; }); notify.unread = 0; paintBell(); renderPanel(); markRead({ all: true, up_to: maxId }); } }),
        el('button', { class: 'ith-plain', text: '關閉', onclick: () => closePanel() }),
      ]),
    ]));
    if (notify.user) {
      const who = notify.user.sees && notify.user.sees.length ? notify.user.sees.join('、') : '（尚未加入任何公司群組）';
      p.appendChild(el('div', { style: { fontSize: '12px', opacity: '.75', margin: '4px 0 8px' }, text: `${notify.user.name}　接收範圍：${who}` }));
    }
    notify.warnings.forEach((w) => p.appendChild(el('div', { class: 'ith-warn', text: w })));
    if (notify.state !== 'ok') {
      p.appendChild(el('div', { class: 'ith-warn', text: bell.title }));
    } else if (!notify.items.length) {
      p.appendChild(el('div', { style: { padding: '16px 4px', opacity: '.7' }, text: '目前沒有通知。只有與你所屬公司有關的事件才會出現在這裡。' }));
    }
    const list = el('div', { style: { overflow: 'auto', flex: '1' } });
    notify.items.forEach((i) => {
      const color = SEV_COLOR[i.severity] || SEV_COLOR.info;
      list.appendChild(el('div', {
        class: 'ith-notice', 'data-id': i.id,
        style: { borderLeft: `4px solid ${color}`, padding: '6px 8px', margin: '6px 0', opacity: i.read ? '.6' : '1', background: i.read ? 'transparent' : 'rgba(255,200,0,.10)' },
      }, [
        el('div', { style: { fontWeight: i.read ? '400' : '600' }, text: i.title }),
        i.detail ? el('div', { style: { fontSize: '12px', opacity: '.8' }, text: i.detail }) : null,
        el('div', { style: { display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px', fontSize: '12px' } }, [
          ...(i.tags || []).map((t) => el('span', { style: { background: color, color: '#fff', borderRadius: '8px', padding: '0 6px' }, text: t })),
          el('span', { style: { opacity: '.7' }, text: i.time ? localTime(i.time) : '目前狀態' }),
          i.read ? null : el('button', { class: 'ith-plain', text: '已讀', style: { marginLeft: 'auto', padding: '0 8px' },
            onclick: () => { i.read = true; notify.unread = Math.max(0, notify.unread - 1); paintBell(); renderPanel(); markRead({ ids: [i.id] }); } }),
        ]),
      ]));
    });
    p.appendChild(list);
  }

  function openPanel() {
    if (notify.open) return;
    notify.open = true;
    notify.panel = el('div', {
      class: 'ith-card ith-notify-panel', role: 'dialog', 'aria-label': '通知',
      style: { right: '16px', bottom: '64px', width: 'min(400px, calc(100vw - 32px))', maxHeight: '60vh', padding: '12px 14px', display: 'flex', flexDirection: 'column' },
    });
    document.body.appendChild(notify.panel);
    renderPanel();
    notifyPoll();
  }
  function closePanel() { notify.open = false; if (notify.panel) { notify.panel.remove(); notify.panel = null; } }
  function togglePanel() { notify.open ? closePanel() : openPanel(); }

  // ===================== 7. 介面翻譯修正 =====================
  // InvenTree 1.5.6 的繁體中文翻譯在儀表板有缺漏或錯譯（已逐條對照官方 zh_Hant 翻譯檔）。
  // 只替換「整段文字完全相同」的地方，不會改到資料內容。
  // scope: 'dashboard' 表示只在儀表板與「新增小工具」抽屜內替換（同一段中文在別處有其他意思）。
  const TEXT_FIXES = [
    { from: 'Add Dashboard Widgets', to: '新增儀表板小工具' },              // 原始碼寫死英文，無法翻譯
    { from: 'High Stock', to: '庫存過量' },                                  // 缺翻譯
    { from: 'Show the number of parts which have excess stock', to: '顯示庫存超過上限的零件數量' },
    { from: 'Latest parts', to: '最新零件' },
    { from: 'Toggle dashboard edit mode', to: '切換儀表板編輯模式' },
    { from: '已訂購零件', to: '已訂閱零件' },                                  // 錯譯（Subscribed Parts）
    { from: '已訂閲類別', to: '已訂閱類別' },                                  // 異體字
    { from: '陳舊庫存項目', to: '久未異動庫存' },
    { from: '顯示陳舊的庫存項目數量', to: '顯示久未異動的庫存項目數量' },
    { from: '儀表盤', to: '儀表板' },                                          // 用語統一
    { from: '編輯佈局', to: '編輯版面' },
    { from: '生產訂單所需的', to: '生產訂單所需零件', scope: 'dashboard' },   // 句子被截斷；別處另有意思
  ];
  const DASHBOARD_SCOPE = '.mantine-Drawer-content, .react-grid-layout';

  function fixText(text, inDashboard) {
    const key = norm(text);
    const f = TEXT_FIXES.find((x) => x.from === key && (!x.scope || inDashboard));
    return f ? text.replace(key, f.to) : null;
  }

  function fixNode(node) {
    if (node.nodeType !== 3) return;
    const parent = node.parentElement;
    if (!parent || parent.closest('.ith-card, #ith-dock, script, style, input, textarea')) return;
    const fixed = fixText(node.nodeValue, !!parent.closest(DASHBOARD_SCOPE));
    if (fixed !== null && fixed !== node.nodeValue) node.nodeValue = fixed;
  }

  function fixTree(root) {
    if (root.nodeType === 3) return fixNode(root);
    if (root.nodeType !== 1) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) fixNode(n);
  }

  fixTree(document.body);
  new MutationObserver((muts) => {
    muts.forEach((m) => {
      if (m.type === 'characterData') fixNode(m.target);
      else m.addedNodes.forEach(fixTree);
    });
  }).observe(document.body, { childList: true, subtree: true, characterData: true });

  notifyPoll();
  setInterval(() => { if (document.visibilityState !== 'hidden') notifyPoll(); }, CONFIG.notifyPollMs);
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') notifyPoll(); });

  // 供自動測試使用的純邏輯函式（不影響一般使用）
  window.__ith = { evaluateAdjust, companyOf, CONFIG, notifyPoll, fixText, TEXT_FIXES };
})();
