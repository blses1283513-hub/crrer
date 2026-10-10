// App 端對端測試：真正的 Caddy + 正式的 Caddyfile.app + 模擬 InvenTree，於 Chromium 驗證。
// 需要環境變數 CADDY_BIN 指向 caddy 執行檔；未設定時略過（CI 會自動下載）。
'use strict';

const { test, before, after } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const net = require('net');
const { spawn, execFileSync } = require('child_process');
const mock = require('../ui/mock-inventree');

const ROOT = path.join(__dirname, '..', '..');
const CADDY = process.env.CADDY_BIN;
const skip = !CADDY && 'CADDY_BIN 未設定，略過 App 端對端測試';

let server; let caddy; let browser; let base; let tmp;

function freePort() {
  return new Promise((resolve) => {
    const s = net.createServer().listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => resolve(p)); });
  });
}

async function waitFor(url, ms = 15000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    try { const r = await fetch(url, { redirect: 'manual' }); if (r.status < 500) return; } catch (e) { /* 尚未就緒 */ }
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error('Caddy 未啟動：' + url);
}

before(async () => {
  if (skip) return;
  const { chromium } = require('playwright');
  server = await mock.start();
  tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'inventree-app-test-'));
  const appDir = path.join(tmp, 'app');
  fs.cpSync(path.join(ROOT, 'inventree-app', 'app'), appDir, { recursive: true });
  fs.copyFileSync(path.join(ROOT, 'inventree-ui-helper', 'inventree-ui-helper.user.js'), path.join(appDir, 'inventree-ui-helper.user.js'));
  fs.mkdirSync(path.join(tmp, 'log'));

  const port = await freePort();
  const health = await freePort();
  base = `http://localhost:${port}`;
  // 只改「環境相關」的部分（路徑與埠號），其餘與正式設定完全相同
  const conf = fs.readFileSync(path.join(ROOT, 'inventree-app', 'Caddyfile.app'), 'utf8')
    .replace('root * /var/www/app', `root * ${appDir}`)
    .replace(/^http:\/\/ \{/m, `http://:${port} {`)
    .replace('/var/log/caddy', path.join(tmp, 'log'))
    .replace(/^:9090 \{/m, `:${health} {`);
  assert.notEqual(conf, fs.readFileSync(path.join(ROOT, 'inventree-app', 'Caddyfile.app'), 'utf8'));
  const confPath = path.join(tmp, 'Caddyfile');
  fs.writeFileSync(confPath, conf);
  execFileSync(CADDY, ['validate', '--config', confPath, '--adapter', 'caddyfile'], { env: { ...process.env, INVENTREE_SERVER: server.url }, stdio: 'pipe' });
  caddy = spawn(CADDY, ['run', '--config', confPath, '--adapter', 'caddyfile'], { env: { ...process.env, INVENTREE_SERVER: server.url }, stdio: 'ignore' });
  await waitFor(base + '/app/');
  browser = await chromium.launch();
});

after(async () => {
  if (skip) return;
  if (browser) await browser.close();
  if (caddy) caddy.kill();
  if (server) await server.close();
  fs.rmSync(tmp, { recursive: true, force: true });
});

test('根路徑導向 App、覆蓋 X-Frame-Options、提供 App 檔案', { skip }, async () => {
  const r = await fetch(base + '/', { redirect: 'manual' });
  assert.equal(r.status, 302);
  assert.match(r.headers.get('location'), /\/app\/$/);
  const web = await fetch(base + '/web/');
  assert.equal(web.headers.get('x-frame-options'), 'SAMEORIGIN', 'InvenTree 的 DENY 應被改為 SAMEORIGIN');
  for (const f of ['/app/', '/app/inventree-ui-helper.user.js', '/app/icon.png', '/app/icon.ico', '/app/client-shortcut.ps1']) {
    assert.equal((await fetch(base + f)).status, 200, f);
  }
});

for (const host of ['localhost', '127.0.0.1']) {
  test(`以 ${host} 開啟 App：載入 InvenTree 並內建操作助手`, { skip }, async () => {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await page.goto(base.replace('localhost', host) + '/');
    await page.waitForFunction(() => {
      const f = document.getElementById('f');
      return f && f.contentWindow && f.contentWindow.__ithLoaded;
    }, null, { timeout: 10000 });
    const frame = page.frames().find((f) => f !== page.mainFrame());
    const buttons = await frame.$$eval('.ith-fab', (b) => b.map((x) => x.textContent));
    assert.deepEqual(buttons.sort(), ['💡 操作說明：開', '📋 異動紀錄', '🔀 快速調貨'].sort());
    assert.match(await page.title(), /庫存管理系統/);
    assert.deepEqual(errors, []);
    await page.close();
  });
}

test('深層連結與重新整理會回到原頁面；誤嵌套時自動解除', { skip }, async () => {
  const page = await browser.newPage();
  await page.goto(base + '/app/#/web/part/5/');
  await page.waitForFunction(() => document.getElementById('f').contentWindow.location.pathname === '/web/part/5/');
  const inner = page.frames().find((f) => f !== page.mainFrame());
  await inner.evaluate(() => { location.href = '/'; });
  await page.waitForFunction(() => document.getElementById('f').contentWindow.location.pathname === '/web/', null, { timeout: 10000 });
  assert.equal(page.frames().length, 2, '不應出現 App 中再套一層 App');
  await page.close();
});
