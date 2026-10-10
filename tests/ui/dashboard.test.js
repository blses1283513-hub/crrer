// 管理看板（InvenTree 儀表板外掛）小工具的自動測試：在 Chromium 載入外掛的 JS，
// 以模擬的 InvenTree API 與通知服務驗證計算與畫面。
'use strict';

const { test, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const http = require('http');
const path = require('path');
const { chromium } = require('playwright');

const JS = path.join(__dirname, '..', '..', 'inventree-app', 'plugins', 'mgmt_dashboard', 'static', 'mgmt_dashboard.js');
const MODULE_URL = '/static/plugins/mgmt-dashboard/mgmt_dashboard.js';
const COMPANIES = [{ name: 'A 公司', code: 'A' }, { name: 'B 公司', code: 'B' }, { name: 'C 公司', code: 'C' }];

const iso = (msAgo) => new Date(Date.now() - msAgo).toISOString();
const DAY = 86400000;

let state;
function reset() {
  const locations = [
    { pk: 1, name: 'A 公司', pathstring: 'A 公司' }, { pk: 2, name: '主倉', pathstring: 'A 公司/主倉' },
    { pk: 3, name: 'B 公司', pathstring: 'B 公司' }, { pk: 4, name: '主倉', pathstring: 'B 公司/主倉' },
    { pk: 5, name: '主倉', pathstring: 'C 公司/主倉' }, { pk: 6, name: '待處理', pathstring: '待處理' },
  ];
  const stock = [];
  // 600 筆 A 公司庫存（測試分頁：每頁 500）
  for (let i = 0; i < 600; i += 1) stock.push({ pk: 1000 + i, part: 100 + (i % 3), location: 2, quantity: 1, updated: iso(1 * DAY) });
  stock.push({ pk: 1, part: 200, location: 4, quantity: 50, updated: iso(90 * DAY) });
  stock.push({ pk: 2, part: 300, location: 5, quantity: 7.5, updated: iso(200 * DAY) });
  stock.push({ pk: 3, part: 300, location: 6, quantity: 4, updated: iso(5 * DAY) });
  const parts = [
    { pk: 100, IPN: 'A-P01-S1-XL', name: 'A1', active: true, is_template: false, total_in_stock: 200, minimum_stock: 10 },
    { pk: 101, IPN: 'A-P01-S1-L', name: 'A2', active: true, is_template: false, total_in_stock: 5, minimum_stock: 10 },   // 低庫存
    { pk: 102, IPN: 'A-P01-S1-M', name: 'A3', active: true, is_template: false, total_in_stock: 0, minimum_stock: 10 },   // 缺貨
    { pk: 200, IPN: 'B-P01-S1-XL', name: '<img src=x onerror="window.__xss=1">B1', active: true, is_template: false, total_in_stock: 50, minimum_stock: 0 },
    { pk: 300, IPN: 'C-P01-S1-XL', name: 'C1', active: true, is_template: false, in_stock: 0, minimum_stock: 0 },        // 只有 in_stock 欄位
    { pk: 301, IPN: 'C-P01', name: 'C 範本', active: true, is_template: true, total_in_stock: 0 },
    { pk: 302, IPN: 'C-P02-S1-XL', name: 'C 停用', active: false, is_template: false, total_in_stock: 0 },
  ];
  const midnight = new Date(); midnight.setHours(0, 0, 0, 0);
  const today = (minutes) => new Date(midnight.getTime() + minutes * 60000).toISOString();
  const tracking = [
    { date: today(1), tracking_type: 11, deltas: { added: 30, quantity: 80 }, item_detail: { location: 2 }, user_detail: { username: 'amy' } },
    { date: today(2), tracking_type: 12, deltas: { removed: 5, quantity: 75 }, item_detail: { location: 2 }, user_detail: { username: 'amy' } },
    { date: today(3), tracking_type: 20, deltas: { location: 4, quantity: 10 }, item_detail: { location: 5 }, user_detail: { username: 'bob' } },
    { date: today(4), tracking_type: 40, deltas: { stockitem: 1, quantity: 3 }, item_detail: { location: 5 }, user_detail: { username: 'bob' } },
    { date: today(5), tracking_type: 10, deltas: { quantity: 9 }, item_detail: { location: 5 }, user_detail: { username: 'carol' } },
    { date: today(6), tracking_type: 70, deltas: { quantity: 100 }, item_detail: { location: 6 }, user: 9 },
    { date: today(7), tracking_type: 5, deltas: {}, item_detail: { location: 2 }, user_detail: { username: 'amy' } },        // 編輯：不計
    { date: new Date(midnight.getTime() - 3600000).toISOString(), tracking_type: 11, deltas: { added: 999 }, item_detail: { location: 2 } }, // 昨天：不計
  ];
  const feed = {
    ok: true, user: { name: 'amy', sees: ['A 公司'] }, unread: 3, warnings: [],
    items: [
      { id: 'low:1', kind: 'low_stock', severity: 'warn', time: null, title: '📉 低庫存' },
      { id: 'low:2', kind: 'low_stock', severity: 'warn', time: iso(60000), title: '📉 低庫存（有時間）' },
      { id: '9', kind: 'transfer_out', severity: 'warn', time: iso(3600000), title: '📤 bob 把 10 件 A-P01-S1-XL 從 A 公司 調出', detail: 'A 公司/主倉 → B 公司/主倉' },
      { id: '8', kind: 'zero', severity: 'danger', time: iso(2 * 3600000), title: '⚠️ 庫存歸零：<b>X</b>', detail: '' },
      { id: '7', kind: 'transfer_in', severity: 'warn', time: iso(30 * 3600000), title: '太舊，不顯示' },
    ],
  };
  state = { locations, stock, parts, tracking, feed, feedStatus: 200, apiStatus: 200, queries: [] };
}

function page(rows, url) {
  const limit = Number(url.searchParams.get('limit') || 0);
  const offset = Number(url.searchParams.get('offset') || 0);
  if (!limit) return rows;
  return { count: rows.length, next: null, previous: null, results: rows.slice(offset, offset + limit) };
}

function api(url) {
  const p = url.pathname;
  state.queries.push(p + url.search);
  if (state.apiStatus !== 200) return [state.apiStatus, { detail: 'no' }];
  const locPath = (pk) => (state.locations.find((l) => l.pk === pk) || {}).pathstring;
  const partOf = (pk) => state.parts.find((x) => x.pk === pk) || {};
  if (p === '/api/stock/location/') return [200, page(state.locations, url)];
  if (p === '/api/part/') {
    const rows = state.parts.filter((x) => url.searchParams.get('active') !== 'true' || x.active)
      .filter((x) => url.searchParams.get('is_template') !== 'false' || !x.is_template);
    return [200, page(rows, url)];
  }
  if (p === '/api/stock/') {
    const before = url.searchParams.get('updated_before');
    let rows = state.stock.filter((s) => !before || s.updated < before);
    if (url.searchParams.get('ordering') === 'updated') rows = [...rows].sort((a, b) => a.updated.localeCompare(b.updated));
    return [200, page(rows.map((s) => ({
      ...s, location_detail: { pk: s.location, pathstring: locPath(s.location) },
      part_detail: { IPN: partOf(s.part).IPN, full_name: partOf(s.part).name },
    })), url)];
  }
  if (p === '/api/stock/track/') {
    const min = url.searchParams.get('min_date');
    return [200, page(state.tracking.filter((t) => !min || t.date.slice(0, 10) >= min), url)];
  }
  return [404, { detail: 'not mocked' }];
}

let server; let base; let browser; let pg; let errors;

before(async () => {
  server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const send = (code, type, body) => { res.writeHead(code, { 'Content-Type': type }); res.end(body); };
    if (url.pathname === MODULE_URL) return send(200, 'text/javascript; charset=utf-8', fs.readFileSync(JS));
    if (url.pathname === '/notify/api/feed') {
      return state.feedStatus === 200 ? send(200, 'application/json', JSON.stringify(state.feed)) : send(state.feedStatus, 'text/plain', 'down');
    }
    if (url.pathname.startsWith('/api/')) { const [code, data] = api(url); return send(code, 'application/json', JSON.stringify(data)); }
    return send(200, 'text/html; charset=utf-8', '<!doctype html><meta charset="utf-8"><body><div id="w" style="width:600px"></div></body>');
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  base = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch();
});

after(async () => {
  await browser.close();
  await new Promise((r) => server.close(r));
});

beforeEach(async () => {
  reset();
  pg = await browser.newPage();
  errors = [];
  pg.on('pageerror', (e) => errors.push(e.message));
  await pg.goto(base + '/web/');
});

// 與 InvenTree 傳入的 ctx 相同形狀：api 為類 axios（錯誤帶 response.status）、context 為外掛提供的設定
async function render(fn, context = {}) {
  await pg.evaluate(async ({ url, fn, context }) => {
    const m = await import(url);
    window.__m = m;
    const api = {
      get: async (u, opts) => {
        const qs = new URLSearchParams(Object.entries((opts && opts.params) || {}).map(([k, v]) => [k, String(v)]));
        const r = await fetch(u + '?' + qs);
        if (!r.ok) { const e = new Error('Request failed'); e.response = { status: r.status }; throw e; }
        return { data: await r.json() };
      },
    };
    window.__nav = [];
    m[fn](document.getElementById('w'), { api, navigate: (p) => window.__nav.push(p), context });
  }, { url: MODULE_URL, fn, context: { companies: [{ name: 'A 公司', code: 'A' }, { name: 'B 公司', code: 'B' }, { name: 'C 公司', code: 'C' }], ...context } });
  await pg.waitForFunction(() => /更新於|失敗|權限/.test(document.getElementById('w').textContent));
}

const cells = () => pg.$$eval('#w tbody tr', (rows) => rows.map((r) => [...r.cells].map((c) => c.textContent.trim())));
const text = () => pg.$eval('#w', (n) => n.textContent);
const noErrors = () => assert.deepEqual(errors, [], '頁面不應有 JavaScript 錯誤');

test('入口函式符合 InvenTree 的格式：(容器, ctx) 兩個參數', async () => {
  const r = await pg.evaluate(async (url) => {
    const m = await import(url);
    return ['renderCompanyOverview', 'renderCrossCompany', 'renderTodayActivity', 'renderStagnantStock'].map((k) => [k, typeof m[k], m[k].length]);
  }, MODULE_URL);
  r.forEach(([k, type, len]) => { assert.equal(type, 'function', k); assert.equal(len, 2, `${k} 必須接受 2 個參數（舊式入口），InvenTree 才會傳入容器`); });
});

test('公司判斷：依庫位路徑與料號前綴，名稱相近不誤判', async () => {
  const r = await pg.evaluate(async ({ url, cs }) => {
    const m = await import(url);
    return [m.companyOfPath('A 公司/主倉', cs), m.companyOfPath('A 公司', cs), m.companyOfPath('A 公司二廠/主倉', cs),
      m.companyOfPath(undefined, cs), m.companyOfIpn('B-P01-S1-XL', cs), m.companyOfIpn('BX-P01', cs), m.companyOfIpn('', cs)];
  }, { url: MODULE_URL, cs: COMPANIES });
  assert.deepEqual(r, ['A 公司', 'A 公司', null, null, 'B 公司', null, null]);
});

test('① 各公司庫存總覽：分頁讀完、依庫位加總、低庫存與缺貨依料號公司', async () => {
  await render('renderCompanyOverview');
  assert.deepEqual(await cells(), [
    ['A 公司', '600', '3', '1', '1'],
    ['B 公司', '50', '1', '0', '0'],
    ['C 公司', '7.5', '1', '0', '1'],
    ['其他庫位', '4', '1', '—', '—'],
  ]);
  const stockPages = state.queries.filter((q) => q.startsWith('/api/stock/?'));
  assert.equal(stockPages.length, 2, '603 筆應分兩頁讀取');
  assert.ok(stockPages.every((q) => q.includes('in_stock=true')), '只算在庫的庫存');
  assert.ok(state.queries.some((q) => q.startsWith('/api/part/?') && q.includes('active=true') && q.includes('is_template=false')));
  noErrors();
});

test('③ 跨公司調動與異常：只顯示近 24 小時的調動與異常，不含低庫存；內容不當 HTML', async () => {
  await render('renderCrossCompany');
  const t = await text();
  assert.match(t, /調入 0/); assert.match(t, /調出 1/); assert.match(t, /歸零 1/); assert.match(t, /大量 0/);
  assert.match(t, /bob 把 10 件/);
  assert.ok(!t.includes('太舊'), '超過 24 小時不顯示');
  assert.ok(!t.includes('📉'), '低庫存不在此小工具');
  assert.match(t, /⚠️ 庫存歸零：<b>X<\/b>/, '標題以純文字顯示');
  assert.match(t, /範圍：A 公司/);
  noErrors();
});

test('③ 異常時間範圍依外掛設定（alert_hours）', async () => {
  await render('renderCrossCompany', { alert_hours: 48 });
  assert.match(await text(), /太舊，不顯示/);
});

test('③ 通知服務沒回應時顯示中文說明，不影響頁面', async () => {
  state.feedStatus = 502;
  await render('renderCrossCompany');
  assert.match(await text(), /通知服務沒有回應/);
  noErrors();
});

test('④ 今日異動摘要：依類型與公司分類、只算今天、列出操作人', async () => {
  await render('renderTodayActivity');
  assert.deepEqual(await cells(), [
    ['A 公司', '1 筆／30', '1 筆／5', '0', '0'],
    ['B 公司', '0', '0', '1 筆／10', '0'],
    ['C 公司', '0', '0', '1 筆／3', '1'],
    ['其他／已刪除', '1 筆／100', '0', '0', '0'],
  ]);
  const t = await text();
  assert.match(t, /今日共 6 筆/);
  assert.match(t, /amy 2/); assert.match(t, /bob 2/); assert.match(t, /carol 1/); assert.match(t, /使用者 #9 1/);
  const q = state.queries.find((x) => x.startsWith('/api/stock/track/?'));
  assert.ok(q.includes('item_detail=true') && q.includes('user_detail=true') && q.includes('min_date='));
  noErrors();
});

test('⑤ 呆滯庫存：依天數篩選、最久的排前面、可點進庫存、名稱不當 HTML', async () => {
  await render('renderStagnantStock');
  const rows = await cells();
  assert.equal(rows.length, 2);
  assert.equal(rows[0][0], 'C-P01-S1-XL');
  assert.match(rows[0][4], /^(199|200) 天$/);
  assert.equal(rows[1][0], 'B-P01-S1-XL');
  assert.equal(rows[1][1], '<img src=x onerror="window.__xss=1">B1');
  assert.equal(await pg.evaluate(() => window.__xss), undefined);
  const t = await text();
  assert.match(t, /A 公司 0 筆／0 件/); assert.match(t, /B 公司 1 筆／50 件/); assert.match(t, /C 公司 1 筆／7.5 件/);
  const q = state.queries.find((x) => x.startsWith('/api/stock/?'));
  const expected = await pg.evaluate(() => new Date(Date.now() - 60 * 86400000).toLocaleDateString('sv-SE'));
  assert.ok(q.includes(`updated_before=${expected}`), q);
  await pg.click('#w tbody tr:first-child a');
  assert.deepEqual(await pg.evaluate(() => window.__nav), ['/stock/item/2/']);
  noErrors();
});

test('⑤ 呆滯天數依外掛設定', async () => {
  await render('renderStagnantStock', { stagnant_days: 300 });
  assert.match(await text(), /沒有超過 300 天未異動的庫存/);
});

test('沒有權限時顯示中文訊息', async () => {
  state.apiStatus = 403;
  await render('renderCompanyOverview');
  assert.match(await text(), /沒有讀取這些資料的權限/);
  noErrors();
});

test('重新整理會重新讀取資料', async () => {
  await render('renderTodayActivity');
  state.tracking = [];
  await pg.click('#w button[aria-label="重新整理"]');
  await pg.waitForFunction(() => /今日共 0 筆/.test(document.getElementById('w').textContent));
  noErrors();
});
