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
  .ith-fab{position:fixed;right:16px;z-index:100001;border:none;border-radius:20px;padding:8px 14px;
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
    class: 'ith-fab', style: { bottom: '16px' },
    title: '開關滑鼠停留時的中文操作說明',
    onclick: () => { hintsOn = !hintsOn; store.set('ith-hints-on', hintsOn); paintHintBtn(); hideTip(); },
  });
  function paintHintBtn() {
    hintBtn.textContent = hintsOn ? '💡 操作說明：開' : '💡 操作說明：關';
    hintBtn.style.background = hintsOn ? '#228be6' : '#868e96';
    hintBtn.style.color = '#fff';
  }
  paintHintBtn();
  document.body.appendChild(hintBtn);

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

  document.body.appendChild(el('button', {
    class: 'ith-fab', style: { bottom: '60px', background: '#495057', color: '#fff' },
    title: '查詢所有庫存異動：時間、操作人、數量、庫位', text: '📋 異動紀錄', onclick: openAudit,
  }));
})();
