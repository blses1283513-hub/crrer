// 管理看板：InvenTree 1.5.6 儀表板小工具（由 mgmt_dashboard 外掛提供）
//
// 每個 render 函式接收 (target, ctx)：target 是小工具的容器，ctx 是 InvenTree 傳入的外掛環境，
// ctx.api 為已登入的 axios（以使用者自己的權限讀取資料），ctx.context 為外掛在伺服器端提供的設定。
// 只讀取資料，不修改任何東西；所有資料庫內容都以 textContent 顯示，不會被當成 HTML 執行。

const REFRESH_MS = 5 * 60 * 1000;
const PAGE_SIZE = 500;
const MAX_ROWS = 10000;

// 異動類型（StockHistoryCode，依 InvenTree 1.5.6 原始碼）
const IN_TYPES = [1, 11, 15, 70, 80, 105];   // 建立、手動新增、退回庫存、採購收貨、退貨單、客戶退回
const OUT_TYPES = [12, 60, 100];             // 手動移除、銷售出貨、交給客戶
const MOVE_TYPES = [20, 40];                 // 轉移、分批轉移（從原庫存拆出）
const COUNT_TYPES = [10];                    // 盤點

// ---------------- 純邏輯（可單獨測試） ----------------

export const num = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

export function fmt(v) {
  const n = num(v);
  return Number.isInteger(n) ? n.toLocaleString('zh-TW') : n.toLocaleString('zh-TW', { maximumFractionDigits: 2 });
}

export function companyOfPath(path, companies) {
  const p = String(path || '');
  const c = (companies || []).find((x) => p === x.name || p.startsWith(x.name + '/'));
  return c ? c.name : null;
}

export function companyOfIpn(ipn, companies) {
  const s = String(ipn || '');
  const c = (companies || []).find((x) => x.code && s.startsWith(x.code + '-'));
  return c ? c.name : null;
}

const rowsOf = (data) => (Array.isArray(data) ? data : (data && data.results) || []);

// 依 limit/offset 讀完整清單；超過 maxRows 時停止並標示 truncated
export async function fetchAll(api, url, params, maxRows = MAX_ROWS) {
  const rows = [];
  let offset = 0;
  for (;;) {
    const res = await api.get(url, { params: { ...params, limit: PAGE_SIZE, offset } });
    const data = res.data;
    const batch = rowsOf(data);
    rows.push(...batch);
    const total = Array.isArray(data) ? batch.length : num(data && data.count);
    offset += batch.length;
    if (!batch.length || offset >= total || Array.isArray(data)) return { rows, truncated: false };
    if (rows.length >= maxRows) return { rows, truncated: true };
  }
}

const partTotal = (p) => num(p.total_in_stock !== undefined && p.total_in_stock !== null ? p.total_in_stock : p.in_stock);

// ① 各公司庫存總覽
export function summarizeOverview(stockRows, partRows, companies) {
  const base = () => ({ qty: 0, skus: new Set(), items: 0, low: 0, out: 0 });
  const by = new Map(companies.map((c) => [c.name, base()]));
  const other = base();
  for (const s of stockRows) {
    const name = companyOfPath(s.location_detail && s.location_detail.pathstring, companies);
    const b = name ? by.get(name) : other;
    b.qty += num(s.quantity);
    b.items += 1;
    if (s.part !== undefined && s.part !== null) b.skus.add(s.part);
  }
  for (const p of partRows) {
    if (p.is_template || p.active === false) continue;
    const name = companyOfIpn(p.IPN, companies);
    if (!name) continue;
    const total = partTotal(p);
    const min = num(p.minimum_stock);
    if (total <= 0) by.get(name).out += 1;
    else if (min > 0 && total < min) by.get(name).low += 1;
  }
  const out = companies.map((c) => {
    const b = by.get(c.name);
    return { name: c.name, qty: b.qty, skus: b.skus.size, items: b.items, low: b.low, out: b.out };
  });
  if (other.items) out.push({ name: '其他庫位', qty: other.qty, skus: other.skus.size, items: other.items, low: null, out: null });
  return out;
}

// ③ 跨公司調動與異常：取通知服務的清單，只留近 hours 小時的調動與異常（低庫存另有小工具）
export function alertItems(feed, nowMs, hours) {
  const since = nowMs - hours * 3600 * 1000;
  return ((feed && feed.items) || []).filter((i) => {
    if (i.kind === 'low_stock' || !i.time) return false;
    const t = Date.parse(i.time);
    return Number.isFinite(t) && t >= since;
  });
}

export function alertCounts(items) {
  const c = { transfer_in: 0, transfer_out: 0, large: 0, zero: 0 };
  items.forEach((i) => { if (i.kind in c) c[i.kind] += 1; });
  return c;
}

// ④ 今日異動摘要
export function classifyTracking(entries, locPathOf, companies, sinceMs) {
  const blank = () => ({ in: { n: 0, qty: 0 }, out: { n: 0, qty: 0 }, move: { n: 0, qty: 0 }, count: { n: 0 } });
  const by = new Map(companies.map((c) => [c.name, blank()]));
  const other = blank();
  const users = new Map();
  let total = 0;
  for (const e of entries) {
    const t = Date.parse(e.date);
    if (!Number.isFinite(t) || t < sinceMs) continue;
    const type = num(e.tracking_type);
    const d = e.deltas || {};
    const itemLoc = e.item_detail ? e.item_detail.location : null;
    let cat; let qty = null; let loc;
    if (IN_TYPES.includes(type)) { cat = 'in'; qty = d.added !== undefined ? d.added : d.quantity; loc = itemLoc; }
    else if (OUT_TYPES.includes(type)) { cat = 'out'; qty = d.removed !== undefined ? d.removed : d.quantity; loc = itemLoc; }
    else if (MOVE_TYPES.includes(type)) { cat = 'move'; qty = d.quantity; loc = d.location !== undefined && d.location !== null ? d.location : itemLoc; }
    else if (COUNT_TYPES.includes(type)) { cat = 'count'; loc = itemLoc !== null && itemLoc !== undefined ? itemLoc : d.location; }
    else continue;
    if (loc === undefined && d.location !== undefined) loc = d.location;
    const name = companyOfPath(locPathOf(loc), companies);
    const b = name ? by.get(name) : other;
    b[cat].n += 1;
    if (cat !== 'count') b[cat].qty += num(qty);
    total += 1;
    const u = (e.user_detail && (e.user_detail.username || e.user_detail.first_name)) || (e.user ? `使用者 #${e.user}` : '系統');
    users.set(u, (users.get(u) || 0) + 1);
  }
  const rows = companies.map((c) => ({ name: c.name, ...by.get(c.name) }));
  const otherN = other.in.n + other.out.n + other.move.n + other.count.n;
  if (otherN) rows.push({ name: '其他／已刪除', ...other });
  const userList = [...users.entries()].map(([name, n]) => ({ name, n })).sort((a, b) => b.n - a.n || a.name.localeCompare(b.name));
  return { rows, users: userList, total };
}

// ⑤ 呆滯庫存
export function stagnantSummary(rows, companies, nowMs) {
  const counts = new Map(companies.map((c) => [c.name, { n: 0, qty: 0 }]));
  const list = rows.map((s) => {
    const company = companyOfPath(s.location_detail && s.location_detail.pathstring, companies);
    const updated = Date.parse(s.updated);
    const days = Number.isFinite(updated) ? Math.floor((nowMs - updated) / 86400000) : null;
    if (company) { counts.get(company).n += 1; counts.get(company).qty += num(s.quantity); }
    return {
      pk: s.pk, part: s.part, company, days, qty: num(s.quantity),
      ipn: (s.part_detail && s.part_detail.IPN) || '',
      name: (s.part_detail && (s.part_detail.full_name || s.part_detail.name)) || '',
      location: (s.location_detail && s.location_detail.pathstring) || '',
    };
  });
  list.sort((a, b) => (b.days === null ? -1 : b.days) - (a.days === null ? -1 : a.days));
  return { counts: companies.map((c) => ({ name: c.name, ...counts.get(c.name) })), list };
}

export const localDate = (d) => d.toLocaleDateString('sv-SE'); // YYYY-MM-DD（本機時間）

// ---------------- 畫面 ----------------

function h(tag, props, children) {
  const node = document.createElement(tag);
  Object.entries(props || {}).forEach(([k, v]) => {
    if (v === null || v === undefined || v === false) return;
    if (k === 'style') Object.assign(node.style, v);
    else if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  });
  (children || []).forEach((c) => c !== null && c !== undefined && c !== false &&
    node.appendChild(typeof c === 'string' || typeof c === 'number' ? document.createTextNode(String(c)) : c));
  return node;
}

const S = {
  root: { font: '13px/1.5 system-ui,"Microsoft JhengHei",sans-serif', display: 'flex', flexDirection: 'column', gap: '6px' },
  head: { display: 'flex', alignItems: 'center', gap: '8px' },
  title: { fontWeight: '600', fontSize: '15px', flex: '1' },
  meta: { opacity: '.65', fontSize: '12px' },
  btn: { border: '1px solid rgba(128,128,128,.4)', background: 'transparent', color: 'inherit', borderRadius: '4px', cursor: 'pointer', padding: '0 6px', font: 'inherit' },
  scroll: { maxHeight: '240px', overflowY: 'auto' },
  table: { borderCollapse: 'collapse', width: '100%' },
  th: { textAlign: 'left', padding: '3px 6px', borderBottom: '1px solid rgba(128,128,128,.4)', whiteSpace: 'nowrap', fontWeight: '600' },
  td: { padding: '3px 6px', borderBottom: '1px solid rgba(128,128,128,.18)', verticalAlign: 'top' },
  num: { textAlign: 'right', fontVariantNumeric: 'tabular-nums' },
  note: { opacity: '.65', fontSize: '12px' },
  warn: { padding: '4px 8px', borderLeft: '4px solid #fd7e14', background: 'rgba(253,126,20,.12)' },
  err: { padding: '4px 8px', borderLeft: '4px solid #fa5252', background: 'rgba(250,82,82,.12)' },
  chip: { display: 'inline-block', padding: '0 8px', borderRadius: '10px', marginRight: '4px', fontSize: '12px', background: 'rgba(128,128,128,.18)' },
  danger: { color: '#fa5252', fontWeight: '600' },
};

function table(headers, rows, numericCols) {
  const isNum = (i) => (numericCols || []).includes(i);
  return h('table', { style: S.table }, [
    h('thead', {}, [h('tr', {}, headers.map((x, i) => h('th', { style: { ...S.th, ...(isNum(i) ? S.num : {}) }, text: x })))]),
    h('tbody', {}, rows.map((r) => h('tr', {}, r.map((cell, i) => {
      const td = h('td', { style: { ...S.td, ...(isNum(i) ? S.num : {}) } });
      if (cell instanceof Node) td.appendChild(cell); else td.textContent = cell === null || cell === undefined ? '—' : String(cell);
      return td;
    })))),
  ]);
}

function link(ctx, text, path) {
  return h('a', {
    href: path,
    style: { color: 'inherit' },
    onclick: (ev) => {
      if (ctx && typeof ctx.navigate === 'function') {
        ev.preventDefault();
        ctx.navigate(path.replace(/^\/web/, ''));
      }
    },
  }, [text]);
}

function errorText(err) {
  const status = err && err.response && err.response.status;
  if (status === 401 || status === 403) return '你的帳號沒有讀取這些資料的權限，請洽管理員。';
  if (status) return `讀取資料失敗（HTTP ${status}），請稍後按「重新整理」。`;
  return `讀取資料失敗：${(err && err.message) || err}`;
}

// 共用外框：標題、更新時間、重新整理；每 5 分鐘自動更新，小工具被移除後停止
function mount(target, title, load) {
  target.innerHTML = '';
  const meta = h('span', { style: S.meta, text: '讀取中…' });
  const body = h('div', { 'data-mgmt-body': '1' });
  let busy = false;
  const run = async () => {
    if (busy) return;
    busy = true;
    meta.textContent = '讀取中…';
    try {
      const content = await load();
      body.replaceChildren(content);
      meta.textContent = `更新於 ${new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })}`;
    } catch (err) {
      body.replaceChildren(h('div', { style: S.err, text: errorText(err) }));
      meta.textContent = '';
    } finally {
      busy = false;
    }
  };
  const refresh = h('button', { type: 'button', style: S.btn, title: '重新整理', 'aria-label': '重新整理', onclick: run }, ['↻']);
  target.appendChild(h('div', { style: S.root, 'data-mgmt-widget': title }, [
    h('div', { style: S.head }, [h('span', { style: S.title, text: title }), meta, refresh]), body,
  ]));
  run();
  const timer = setInterval(() => {
    if (!target.isConnected) return clearInterval(timer);
    if (document.visibilityState !== 'hidden') run();
  }, REFRESH_MS);
  return run;
}

const cfg = (ctx) => {
  const c = (ctx && ctx.context) || {};
  return {
    companies: Array.isArray(c.companies) && c.companies.length ? c.companies : [
      { name: 'A 公司', code: 'A' }, { name: 'B 公司', code: 'B' }, { name: 'C 公司', code: 'C' }],
    stagnantDays: num(c.stagnant_days) > 0 ? num(c.stagnant_days) : 60,
    alertHours: num(c.alert_hours) > 0 ? num(c.alert_hours) : 24,
    notifyUrl: c.notify_url || '/notify/api/feed',
  };
};

const truncNote = (flag) => (flag ? h('div', { style: S.warn, text: '資料量超過上限，只統計了前 10,000 筆。' }) : null);

// ① 各公司庫存總覽
export function renderCompanyOverview(target, ctx) {
  const { companies } = cfg(ctx);
  return mount(target, '各公司庫存總覽', async () => {
    const [stock, parts] = await Promise.all([
      fetchAll(ctx.api, '/api/stock/', { in_stock: true, location_detail: true, part_detail: false }),
      fetchAll(ctx.api, '/api/part/', { active: true, is_template: false }),
    ]);
    const rows = summarizeOverview(stock.rows, parts.rows, companies);
    return h('div', {}, [
      truncNote(stock.truncated || parts.truncated),
      table(['公司', '庫存總量', '品項數', '低庫存', '缺貨'], rows.map((r) => [
        r.name, fmt(r.qty), fmt(r.skus),
        r.low === null ? '—' : h('span', { style: r.low ? S.danger : {}, text: fmt(r.low) }),
        r.out === null ? '—' : h('span', { style: r.out ? S.danger : {}, text: fmt(r.out) }),
      ]), [1, 2, 3, 4]),
      h('div', { style: S.note, text: '庫存總量與品項數依「庫存所在庫位」；低庫存（未達最低庫存、尚未缺貨）與缺貨依料號所屬公司。' }),
    ]);
  });
}

// ③ 跨公司調動與異常
export function renderCrossCompany(target, ctx) {
  const { notifyUrl, alertHours } = cfg(ctx);
  return mount(target, '跨公司調動與異常', async () => {
    let feed;
    try {
      const res = await fetch(notifyUrl, { credentials: 'same-origin', headers: { Accept: 'application/json' } });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      feed = await res.json();
    } catch (err) {
      return h('div', { style: S.warn, text: `通知服務沒有回應（${err.message}）。請確認主機的 inventree-notifier 容器在執行。` });
    }
    const items = alertItems(feed, Date.now(), alertHours);
    const c = alertCounts(items);
    const chips = h('div', {}, [
      h('span', { style: S.chip, text: `📥 調入 ${c.transfer_in}` }),
      h('span', { style: S.chip, text: `📤 調出 ${c.transfer_out}` }),
      h('span', { style: { ...S.chip, ...(c.large ? S.danger : {}) }, text: `大量 ${c.large}` }),
      h('span', { style: { ...S.chip, ...(c.zero ? S.danger : {}) }, text: `歸零 ${c.zero}` }),
    ]);
    const list = items.length
      ? h('div', { style: S.scroll }, [table(['時間', '內容'], items.map((i) => [
        new Date(i.time).toLocaleString('zh-TW', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }),
        h('div', {}, [
          h('div', { style: i.severity === 'danger' ? S.danger : {}, text: i.title || '' }),
          i.detail ? h('div', { style: S.note, text: i.detail }) : null,
        ]),
      ]))])
      : h('div', { style: S.note, text: `最近 ${alertHours} 小時沒有跨公司調動或異常操作。` });
    const sees = feed && feed.user && Array.isArray(feed.user.sees) ? feed.user.sees.join('、') : '';
    return h('div', {}, [chips, list,
      h('div', { style: S.note, text: `範圍：${sees || '你所屬公司'}；不含你自己的操作。` })]);
  });
}

// ④ 今日異動摘要
export function renderTodayActivity(target, ctx) {
  const { companies } = cfg(ctx);
  return mount(target, '今日異動摘要', async () => {
    const now = new Date();
    const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const yesterday = localDate(new Date(midnight - 86400000));
    const [track, locs] = await Promise.all([
      // min_date 為「晚於該日」；往前多抓一天避免時區差，再以本機午夜過濾
      fetchAll(ctx.api, '/api/stock/track/', { min_date: yesterday, item_detail: true, user_detail: true }),
      fetchAll(ctx.api, '/api/stock/location/', {}),
    ]);
    const paths = new Map(locs.rows.map((l) => [l.pk, l.pathstring || l.name]));
    const r = classifyTracking(track.rows, (pk) => paths.get(pk), companies, midnight);
    const pair = (x) => (x.n ? `${x.n} 筆／${fmt(x.qty)}` : '0');
    return h('div', {}, [
      truncNote(track.truncated),
      table(['公司', '入庫', '出庫', '調入', '盤點'], r.rows.map((x) => [x.name, pair(x.in), pair(x.out), pair(x.move), String(x.count.n)]), [1, 2, 3, 4]),
      h('div', { style: { marginTop: '4px' } }, [
        h('span', { style: S.note, text: `今日共 ${r.total} 筆。操作人：` }),
        r.users.length ? r.users.slice(0, 8).map((u) => h('span', { style: S.chip, text: `${u.name} ${u.n}` })) : h('span', { style: S.note, text: '無' }),
      ].flat()),
      h('div', { style: S.note, text: '「筆／數量」；調入依目的庫位的公司計算，其他依庫存目前所在庫位。' }),
    ]);
  });
}

// ⑤ 呆滯庫存
export function renderStagnantStock(target, ctx) {
  const { companies, stagnantDays } = cfg(ctx);
  return mount(target, '呆滯庫存', async () => {
    const now = Date.now();
    const cutoff = localDate(new Date(now - stagnantDays * 86400000));
    const res = await fetchAll(ctx.api, '/api/stock/', {
      in_stock: true, updated_before: cutoff, ordering: 'updated', location_detail: true, part_detail: true,
    });
    const s = stagnantSummary(res.rows, companies, now);
    const top = s.list.slice(0, 30);
    return h('div', {}, [
      truncNote(res.truncated),
      h('div', {}, s.counts.map((c) => h('span', { style: S.chip, text: `${c.name} ${c.n} 筆／${fmt(c.qty)} 件` }))),
      top.length
        ? h('div', { style: S.scroll }, [table(['料號', '品名', '庫位', '數量', '未異動'], top.map((x) => [
          link(ctx, x.ipn || `#${x.pk}`, `/web/stock/item/${x.pk}/`), x.name, x.location, fmt(x.qty),
          x.days === null ? '—' : `${x.days} 天`,
        ]), [3, 4])])
        : h('div', { style: S.note, text: `沒有超過 ${stagnantDays} 天未異動的庫存。` }),
      h('div', { style: S.note, text: `超過 ${stagnantDays} 天沒有任何異動（入出庫、轉移、盤點）的庫存，最久的排最前面；天數可在外掛設定調整。` }),
    ]);
  });
}
