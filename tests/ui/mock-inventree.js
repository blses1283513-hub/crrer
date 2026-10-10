// 模擬 InvenTree 1.5.6 的頁面與 API，供自動測試使用（不需要真的 InvenTree）。
// - /web/*        模擬前端頁面：選單按鈕、轉移／移除／盤點視窗（送出時呼叫 API，與真實行為相同）
// - /api/*        模擬庫存、零件、庫位、異動紀錄、轉移與移除 API；POST 需帶 X-CSRFToken
// - /__posts      測試用：讀取收到的 POST；/__reset 重設狀態
// 回應都帶 X-Frame-Options: DENY（與 InvenTree 預設相同），用來驗證 App 的代理設定會正確覆蓋。
'use strict';

const http = require('http');

const CSRF = 'test-csrf-token';

function initialState() {
  return {
    locations: [
      { pk: 1, name: 'A 公司', pathstring: 'A 公司', structural: true },
      { pk: 2, name: '主倉', pathstring: 'A 公司/主倉', structural: false },
      { pk: 3, name: 'B 公司', pathstring: 'B 公司', structural: true },
      { pk: 4, name: '主倉', pathstring: 'B 公司/主倉', structural: false },
      { pk: 5, name: '主倉', pathstring: 'C 公司/主倉', structural: false },
    ],
    parts: [
      { pk: 8, IPN: 'A-P01', name: 'A 產品P01', full_name: 'A 產品P01', is_template: true },
      { pk: 9, IPN: 'A-P01-S1-XL', name: 'A 產品P01 / 樣式1 / XL', full_name: 'A 產品P01 / 樣式1 / XL', is_template: false },
    ],
    stock: [
      { pk: 1, part: 9, location: 2, quantity: 120 },
      { pk: 2, part: 9, location: 4, quantity: 30 },
    ],
    tracking: [],
    posts: [],
  };
}

let state = initialState();

const PAGE = `<!doctype html><html><head><meta charset="utf-8"><title>InvenTree</title></head><body>
<nav><a href="#" id="nav-stock">Stock</a> <button aria-label="action-menu-stock-operations">⋮</button>
<button id="open-transfer">Transfer</button> <button id="open-remove">Remove</button> <button id="open-count">Count</button> <button>Random</button></nav>
<div id="root"></div>
<script>
  function dialog(title, kind, value) {
    var root = document.getElementById('root');
    root.innerHTML = '<div role="dialog"><div class="mantine-Modal-content"><h2 class="mantine-Modal-title">' + title + '</h2>' +
      '<table><tbody><tr><td><a href="/web/stock/item/1/">A-P01-S1-XL</a></td><td>A 公司/主倉</td><td>120</td>' +
      '<td><input id="qty" type="number" value="' + value + '"></td></tr></tbody></table>' +
      '<input id="dest" value=""><button id="cancel">Cancel</button><button id="submit" type="submit">Submit</button></div></div>';
    document.getElementById('submit').addEventListener('click', function () {
      var csrf = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
      fetch('/api/stock/' + kind + '/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ items: [{ pk: 1, quantity: Number(document.getElementById('qty').value) }], location: 4 }) })
        .then(function () { root.innerHTML = '<div id="done">done</div>'; });
    });
  }
  document.getElementById('open-transfer').onclick = function () { dialog('Transfer Stock', 'transfer', 1); };
  document.getElementById('open-remove').onclick = function () { dialog('Remove Stock', 'remove', 1); };
  document.getElementById('open-count').onclick = function () { dialog('Count Stock', 'count', 1); };
</script></body></html>`;

function page(rows, url) {
  const limit = Number(url.searchParams.get('limit') || 0);
  const offset = Number(url.searchParams.get('offset') || 0);
  if (!limit) return rows;
  const slice = rows.slice(offset, offset + limit);
  return { count: rows.length, next: offset + limit < rows.length ? 'next' : null, previous: null, results: slice };
}

function locPath(pk) {
  const l = state.locations.find((x) => x.pk === pk);
  return l ? l.pathstring : '';
}

function stockOut(s) {
  return { pk: s.pk, part: s.part, location: s.location, quantity: s.quantity, location_detail: { pk: s.location, pathstring: locPath(s.location) } };
}

function handleApi(req, res, url, body) {
  const json = (code, data) => {
    res.writeHead(code, { 'Content-Type': 'application/json', 'X-Frame-Options': 'DENY' });
    res.end(JSON.stringify(data));
  };
  const p = url.pathname;

  if (req.method === 'POST') {
    if (req.headers['x-csrftoken'] !== CSRF) return json(403, { detail: 'CSRF Failed' });
    let data;
    try { data = JSON.parse(body || '{}'); } catch (e) { return json(400, { detail: 'bad json' }); }
    state.posts.push({ path: p, body: data, csrf: req.headers['x-csrftoken'] });
    if (p === '/api/stock/transfer/') {
      for (const it of data.items || []) {
        const s = state.stock.find((x) => x.pk === it.pk);
        if (!s) return json(400, { items: ['not found'] });
        if (!(Number(it.quantity) > 0)) return json(400, { quantity: ['Quantity must be greater than zero'] });
        // 與 InvenTree 1.5.6 相同：數量 >= 現有時整批搬走，不報錯
        const q = Math.min(Number(it.quantity), s.quantity);
        if (q >= s.quantity) { s.location = data.location; } else {
          s.quantity -= q;
          state.stock.push({ pk: state.stock.length + 1, part: s.part, location: data.location, quantity: q });
        }
        state.tracking.unshift({ date: new Date().toISOString(), user_detail: { username: 'tester' }, label: 'Location changed', deltas: { location: data.location, quantity: q }, item_detail: { part: s.part, location: data.location }, notes: data.notes || '' });
      }
      return json(201, []);
    }
    if (p === '/api/stock/remove/' || p === '/api/stock/count/') return json(201, []);
    return json(404, {});
  }

  if (p === '/api/stock/location/') return json(200, page(state.locations, url));
  if (p === '/api/part/') {
    const q = (url.searchParams.get('search') || '').toLowerCase();
    const rows = state.parts.filter((x) => !q || (x.IPN + ' ' + x.name).toLowerCase().includes(q));
    return json(200, page(rows, url));
  }
  if (p === '/api/stock/') {
    const part = Number(url.searchParams.get('part'));
    return json(200, page(state.stock.filter((s) => !part || s.part === part).map(stockOut), url));
  }
  const item = p.match(/^\/api\/stock\/(\d+)\/$/);
  if (item) {
    const s = state.stock.find((x) => x.pk === Number(item[1]));
    return s ? json(200, stockOut(s)) : json(404, {});
  }
  if (p === '/api/stock/track/') return json(200, page(state.tracking, url));
  return json(404, { detail: 'not mocked' });
}

function start(port = 0) {
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => { body += c; });
    req.on('end', () => {
      const url = new URL(req.url, 'http://localhost');
      if (url.pathname === '/__posts') { res.writeHead(200, { 'Content-Type': 'application/json' }); return res.end(JSON.stringify(state.posts)); }
      if (url.pathname === '/__reset') { state = initialState(); res.writeHead(204); return res.end(); }
      if (url.pathname.startsWith('/api/')) return handleApi(req, res, url, body);
      if (url.pathname.startsWith('/web')) {
        res.writeHead(200, {
          'Content-Type': 'text/html; charset=utf-8', 'X-Frame-Options': 'DENY',
          'Set-Cookie': `csrftoken=${CSRF}; Path=/; SameSite=Lax`,
        });
        return res.end(PAGE);
      }
      res.writeHead(404); res.end('not found');
    });
  });
  return new Promise((resolve) => server.listen(port, '127.0.0.1', () => {
    resolve({ url: `http://127.0.0.1:${server.address().port}`, port: server.address().port, close: () => new Promise((r) => server.close(r)) });
  }));
}

module.exports = { start, CSRF };

if (require.main === module) {
  start(Number(process.argv[2] || 8000)).then((s) => console.log('mock InvenTree on', s.url));
}
