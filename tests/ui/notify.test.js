// 通知小視窗的自動測試：真正的通知服務＋模擬 InvenTree，在 Chromium 驗證畫面。
// 需要 python3（用來啟動 tests/notifier/serve_sim.py）。
'use strict';

const { test, before, after, beforeEach, afterEach } = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const readline = require('readline');
const { spawn } = require('child_process');
const { chromium } = require('playwright');
const mock = require('./mock-inventree');

const HELPER = path.join(__dirname, '..', '..', 'inventree-ui-helper', 'inventree-ui-helper.user.js');
const SIM = path.join(__dirname, '..', 'notifier', 'serve_sim.py');

let sim; let info; let web; let browser;

async function startSim() {
  const proc = spawn(process.env.PYTHON || 'python3', ['-I', SIM], { stdio: ['ignore', 'pipe', 'ignore'] });
  const line = await new Promise((resolve, reject) => {
    const rl = readline.createInterface({ input: proc.stdout });
    rl.once('line', resolve);
    proc.once('exit', () => reject(new Error('模擬服務未能啟動')));
  });
  return { proc, info: JSON.parse(line) };
}

const ctl = (op, ...args) => fetch(`http://127.0.0.1:${info.ctl_port}/ctl`, { method: 'POST', body: JSON.stringify({ op, args }) }).then((r) => r.json());

before(async () => {
  browser = await chromium.launch();
});

after(async () => {
  await browser.close();
});

let ctx; let page; let errors;

// 以某位使用者（對應模擬 InvenTree 的 session）開啟頁面
async function open(user) {
  ctx = await browser.newContext();
  if (user) await ctx.addCookies([{ name: 'sessionid', value: `sess-${user}`, url: web.url }]);
  page = await ctx.newPage();
  errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(web.url + '/web/');
  await page.addScriptTag({ path: HELPER });
  await page.waitForFunction(() => window.__ith && window.__ith.notifyPoll);
  return page;
}

const showDock = () => page.hover('#ith-signal');
const poll = () => page.evaluate(() => window.__ith.notifyPoll());
const badge = async () => (await page.textContent('[aria-label="通知"]')).replace('🔔 通知', '').trim();
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// 每個測試都用全新的模擬 InvenTree、通知服務與已讀狀態，彼此不互相影響
beforeEach(async () => {
  ({ proc: sim, info } = await startSim());
  web = await mock.start(0, { notifierUrl: `http://127.0.0.1:${info.notifier_port}` });
});

afterEach(async () => {
  if (ctx) await ctx.close();
  ctx = null;
  await web.close();
  sim.kill();
});

test('收到與自己公司有關的事件：鈴鐺紅色數字、小視窗跳出、清單內容正確', async () => {
  await open('b-wh');
  await poll();                                  // 初始化（第一次輪詢之前的事件不通知）
  await ctl('move', 'a-wh', 'itemA', 'locB');    // A 公司的人把庫存調進 B 公司（80 件，非大量）
  await poll();
  await page.waitForSelector('.ith-toast');
  assert.match(await page.textContent('.ith-toast'), /調進 B 公司/);
  assert.equal(await badge(), '1');

  await showDock();
  await page.click('[aria-label="通知"]');
  await page.waitForSelector('.ith-notify-panel');
  const panel = await page.textContent('.ith-notify-panel');
  assert.match(panel, /A 公司 的 a-wh 把 80 件 A-P01-S1-XL 調進 B 公司/);
  assert.match(panel, /A 公司\/主倉 → B 公司\/主倉/);
  assert.match(panel, /接收範圍：B 公司/);
  assert.deepEqual(errors, []);
});

test('只收到與自己公司有關的通知（C 公司什麼都不會看到）', async () => {
  await open('c-wh');
  await poll();
  await ctl('move', 'a-wh', 'itemA', 'locB');
  await ctl('remove', 'a-wh', 'bigA', 150);
  await poll();
  assert.equal(await badge(), '');
  await showDock();
  await page.click('[aria-label="通知"]');
  assert.match(await page.textContent('.ith-notify-panel'), /目前沒有通知/);
  assert.equal(await page.$('.ith-toast'), null);
});

test('大量操作的小視窗不會自動消失，其他通知會', async () => {
  await open('a-wh2');
  await poll();
  await ctl('remove', 'a-wh', 'bigA', 150);
  await poll();
  await page.waitForSelector('.ith-toast');
  assert.match(await page.textContent('.ith-toast'), /大量移除/);
  await wait(500);
  assert.ok(await page.$('.ith-toast'), '異常（大量／歸零）要等人關閉');
  await page.click('.ith-toast button[aria-label="關閉"]');
  assert.equal(await page.$('.ith-toast'), null);
});

test('標示已讀：單筆與全部；重新整理與換電腦（另一個瀏覽器）都一致', async () => {
  await open('a-wh2');
  await poll();
  await ctl('remove', 'a-wh', 'bigA', 150);
  await ctl('add', 'a-wh', 'bigA', 300);
  await poll();
  assert.equal(await badge(), '2');
  await showDock();
  await page.click('[aria-label="通知"]');
  await page.waitForSelector('.ith-notice');
  await page.click('.ith-notice button:has-text("已讀")');
  await page.waitForFunction(() => document.querySelector('[aria-label="通知"]').textContent.includes('1'));
  assert.equal(await badge(), '1');

  // 「換一台電腦」：全新的瀏覽器環境，同一個帳號
  const other = await browser.newContext();
  await other.addCookies([{ name: 'sessionid', value: 'sess-a-wh2', url: web.url }]);
  const p2 = await other.newPage();
  await p2.goto(web.url + '/web/');
  await p2.addScriptTag({ path: HELPER });
  await p2.waitForFunction(() => document.querySelector('[aria-label="通知"]').textContent.includes('1'));
  await p2.close();
  await other.close();

  await page.click('.ith-notify-panel button:has-text("全部已讀")');
  await page.waitForFunction(() => !/\d/.test(document.querySelector('[aria-label="通知"]').textContent));
  await page.reload();
  await page.addScriptTag({ path: HELPER });
  await page.waitForFunction(() => window.__ith && window.__ith.notifyPoll);
  await poll();
  assert.equal(await badge(), '');
  assert.deepEqual(errors, []);
});

test('第一次載入有未讀時，只彈一個彙總小視窗；之後的新事件各自彈出', async () => {
  await ctl('remove', 'b-wh', 'bigB', 150);
  await open('b-wh');                                   // 先讓服務初始化
  await poll();
  await ctl('remove', 'a-wh', 'bigB', 150);             // 初始化之後才發生
  await page.close();
  await open('b-wh');                                   // 重新載入：有未讀
  await page.waitForSelector('.ith-toast');
  assert.equal(await page.locator('.ith-toast').count(), 1);
  assert.match(await page.textContent('.ith-toast'), /您有 \d+ 則未讀通知/);
  await ctl('remove', 'a-wh', 'bigB', 120);
  await poll();
  await page.waitForFunction(() => document.querySelectorAll('.ith-toast').length === 2);
  assert.match(await page.locator('.ith-toast').nth(1).textContent(), /大量移除/);
});

test('低庫存：只有該公司看到；已讀後消失，變得更低會再通知', async () => {
  await open('a-wh2');
  await poll();
  await ctl('remove', 'a-wh', 'itemA', 40);            // 80 → 40（< 最低 50）
  await poll();
  await showDock();
  await page.click('[aria-label="通知"]');
  await page.waitForSelector('.ith-notice');
  const text = await page.textContent('.ith-notify-panel');
  assert.match(text, /低庫存：A-P01-S1-XL 現有 40，最低標準 50/);
  await page.click('.ith-notice button:has-text("已讀")');
  await page.waitForFunction(() => !/\d/.test(document.querySelector('[aria-label="通知"]').textContent));
  await ctl('remove', 'a-wh', 'itemA', 10);            // 更低
  await poll();
  assert.equal(await badge(), '1');
});

test('通知服務沒有啟用（404）時只顯示灰色鈴鐺，不影響其他功能', async () => {
  const bare = await mock.start(0);                    // 沒有轉送 /notify
  const c = await browser.newContext();
  const p = await c.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  await p.goto(bare.url + '/web/');
  await p.addScriptTag({ path: HELPER });
  await p.waitForFunction(() => /尚未啟用/.test(document.querySelector('[aria-label="通知"]').title));
  assert.equal(await p.locator('.ith-toast').count(), 0);
  assert.ok(await p.$('text=🔀 快速調貨'));
  assert.deepEqual(errs, []);
  await c.close();
  await bare.close();
});

test('資料庫內容不會被當成 HTML 執行', async () => {
  await open('a-wh2');
  await poll();
  await ctl('remove', 'a-wh', 'bigA', 150, '<img src=x onerror="window.__xss=1">');
  await poll();
  await showDock();
  await page.click('[aria-label="通知"]');
  await page.waitForSelector('.ith-notice');
  assert.equal(await page.$('.ith-notify-panel img'), null);
  assert.equal(await page.evaluate(() => window.__xss), undefined);
  assert.match(await page.textContent('.ith-notify-panel'), /<img src=x/);
});

test('小圓點只顯示未讀數；沒有未讀時安靜；點圓點直接開啟通知清單', async () => {
  await open('a-wh2');
  await poll();
  assert.equal((await page.textContent('#ith-signal')).trim(), '🔔');
  assert.equal(await page.evaluate(() => document.getElementById('ith-signal').classList.contains('has-unread')), false);

  await ctl('remove', 'a-wh', 'bigA', 150);
  await ctl('add', 'a-wh', 'bigA', 300);
  await poll();
  assert.equal((await page.textContent('#ith-signal')).trim(), '2', '圓點上顯示未讀通知數');
  assert.equal(await page.evaluate(() => document.getElementById('ith-signal').classList.contains('has-unread')), true);
  assert.equal(await page.isVisible('#ith-dock-stack'), false, '收起時不顯示按鈕，只顯示數字');

  await page.click('#ith-signal');                     // 滑鼠點圓點：直接看通知
  await page.waitForSelector('.ith-notify-panel');
  assert.match(await page.textContent('.ith-notify-panel'), /大量移除/);
  await page.click('.ith-notify-panel button:has-text("全部已讀")');
  await page.waitForFunction(() => document.getElementById('ith-signal').textContent.trim() === '🔔');
  assert.deepEqual(errors, []);
});

test('登入頁（沒登入）時整個浮動面板都不顯示', async () => {
  await open(null);
  await page.waitForFunction(() => document.getElementById('ith-dock').style.display === 'none');
  assert.deepEqual(errors, []);
});

test('超過 99 則顯示 99+', async () => {
  await open('a-wh2');
  await poll();
  for (let i = 0; i < 101; i++) await ctl('add', 'a-wh', 'bigA', 120);
  await poll();
  assert.equal((await page.textContent('#ith-signal')).trim(), '99+');
});
