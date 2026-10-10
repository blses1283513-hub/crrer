// 中文操作助手的自動測試：在 Chromium 中對模擬 InvenTree 執行。
// 執行：node --test tests/ui/   （需先 npm ci 安裝 playwright，或設定 NODE_PATH 指向已安裝的 playwright）
'use strict';

const { test, before, after, beforeEach } = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const { chromium } = require('playwright');
const mock = require('./mock-inventree');

const HELPER = path.join(__dirname, '..', '..', 'inventree-ui-helper', 'inventree-ui-helper.user.js');

let server;
let browser;
let page;
let errors;

before(async () => {
  server = await mock.start();
  browser = await chromium.launch();
});

after(async () => {
  await browser.close();
  await server.close();
});

beforeEach(async () => {
  await fetch(server.url + '/__reset');
  page = await browser.newPage();
  errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(server.url + '/web/');
  await page.addScriptTag({ path: HELPER });
});

const posts = async () => (await fetch(server.url + '/__posts')).json();
const noErrors = () => assert.deepEqual(errors, [], '頁面不應有 JavaScript 錯誤');

test('異常判斷邏輯：大量、超量、歸零', async () => {
  const r = await page.evaluate(() => {
    const f = (...a) => window.__ith.evaluateAdjust(...a).map((w) => w.type).join(',');
    return {
      normal: f('transfer', 5, 120, 100),
      large: f('transfer', 100, 500, 100),
      over: f('remove', 150, 120, 100),
      overSmall: f('transfer', 20, 10, 100),
      zeroRemove: f('remove', 120, 120, 100),
      zeroTransfer: f('transfer', 30, 30, 100),
      countZero: f('count', 0, 50, 100),
      addLarge: f('add', 200, null, 100),
      addSmall: f('add', 5, null, 100),
      unknownExisting: f('remove', 5, null, 100),
      boundary99: f('transfer', 99, 500, 100),
    };
  });
  assert.equal(r.normal, '');
  assert.equal(r.large, 'large');
  assert.equal(r.over, 'large,over');
  assert.equal(r.overSmall, 'over');
  assert.equal(r.zeroRemove, 'large,zero');
  assert.equal(r.zeroTransfer, 'zero');
  assert.equal(r.countZero, 'zero');
  assert.equal(r.addLarge, 'large');
  assert.equal(r.addSmall, '');
  assert.equal(r.unknownExisting, '');
  assert.equal(r.boundary99, '', '99 件不算大量（門檻 100）');
  noErrors();
});

test('滑鼠停留說明：顯示、不誤判、可關閉', async () => {
  await page.hover('#nav-stock');
  await page.waitForSelector('.ith-tip', { timeout: 2000 });
  assert.match(await page.textContent('.ith-tip'), /庫存/);
  await page.hover('text=Random');
  await page.waitForTimeout(700);
  assert.equal(await page.$('.ith-tip'), null, '沒有對應說明的按鈕不應顯示');
  await page.click('text=💡 操作說明：開');
  await page.hover('#nav-stock');
  await page.waitForTimeout(700);
  assert.equal(await page.$('.ith-tip'), null, '關閉後不應顯示');
  noErrors();
});

test('調貨提醒：跨公司警告，視窗關閉時收起', async () => {
  await page.click('#open-transfer');
  const box = '[aria-label="調貨提醒"]';
  await page.waitForSelector(box);
  await page.fill('#dest', 'B 公司/主倉');
  await page.waitForFunction((b) => /跨公司/.test(document.querySelector(b).textContent), box, { timeout: 3000 });
  await page.evaluate(() => { document.getElementById('root').innerHTML = ''; });
  await page.waitForSelector(box, { state: 'detached', timeout: 3000 });
  noErrors();
});

test('異常警告：超量＋大量時跳出確認，取消則不送出', async () => {
  await page.click('#open-remove');
  await page.fill('#qty', '150');
  await page.click('#submit');
  const dlg = '[aria-label="異常操作確認"]';
  await page.waitForSelector(dlg);
  const text = await page.textContent(dlg);
  assert.match(text, /大量異動/);
  assert.match(text, /超量.*現有只有 120/);
  await page.click('text=取消，回去修改');
  await page.waitForTimeout(300);
  assert.equal((await posts()).length, 0, '取消後不應送出');
  assert.ok(await page.$('#submit'), '原視窗仍在，可修改');
  noErrors();
});

test('異常警告：確認繼續後才送出', async () => {
  await page.click('#open-remove');
  await page.fill('#qty', '120');
  await page.click('#submit');
  await page.waitForSelector('[aria-label="異常操作確認"]');
  assert.match(await page.textContent('[aria-label="異常操作確認"]'), /歸零/);
  await page.click('text=確認繼續');
  await page.waitForSelector('#done');
  const p = await posts();
  assert.equal(p.length, 1);
  assert.equal(p[0].path, '/api/stock/remove/');
  assert.equal(p[0].body.items[0].quantity, 120);
  noErrors();
});

test('異常警告：正常數量直接送出、不打擾', async () => {
  await page.click('#open-remove');
  await page.fill('#qty', '5');
  await page.click('#submit');
  await page.waitForSelector('#done');
  assert.equal(await page.$('[aria-label="異常操作確認"]'), null);
  assert.equal((await posts()).length, 1);
  noErrors();
});

test('異常警告：在數量欄按 Enter 也會檢查', async () => {
  await page.click('#open-count');
  await page.fill('#qty', '0');
  await page.press('#qty', 'Enter');
  await page.waitForSelector('[aria-label="異常操作確認"]');
  assert.match(await page.textContent('[aria-label="異常操作確認"]'), /盤點數量為 0/);
  await page.click('text=取消，回去修改');
  assert.equal((await posts()).length, 0);
  noErrors();
});

test('快速調貨：跨公司、需確認、送出正確內容與 CSRF', async () => {
  await page.click('text=🔀 快速調貨');
  await page.fill('[aria-label="搜尋料號或品名"]', 'A-P01-S1');
  await page.click('.ith-qt button:has-text("A-P01-S1-XL")');
  await page.waitForSelector('.ith-qt-company');
  const cards = await page.$$eval('.ith-qt-company', (c) => c.map((x) => x.textContent));
  assert.ok(cards.some((t) => /A 公司\s*共 120 件/.test(t)), 'A 公司應有 120 件');
  assert.ok(cards.some((t) => /B 公司\s*共 30 件/.test(t)), 'B 公司應有 30 件');
  assert.equal(await page.$('.ith-qt button:has-text("A-P01 A 產品P01")'), null, '範本零件不應出現在可調清單');

  await page.check('#ith-src-1');
  await page.selectOption('[aria-label="目的庫位"]', '4');
  await page.fill('[aria-label="數量"]', '5');
  await page.fill('[aria-label="備註"]', '補貨給 B 公司門市');
  assert.match(await page.textContent('.ith-qt .ith-warn'), /跨公司調貨：A 公司 → B 公司/);
  const structural = await page.$$eval('[aria-label="目的庫位"] option', (o) => o.map((x) => x.textContent));
  assert.ok(!structural.includes('A 公司'), '結構性庫位（不能放庫存）不應出現在目的清單');

  await page.click('text=確認調貨');
  await page.waitForSelector('[aria-label="異常操作確認"]');
  await page.click('text=確認繼續');
  await page.waitForFunction(() => /已調貨 5 件/.test(document.querySelector('.ith-qt').textContent));
  const p = await posts();
  assert.equal(p.length, 1);
  assert.equal(p[0].path, '/api/stock/transfer/');
  assert.deepEqual(p[0].body.items, [{ pk: 1, quantity: 5 }]);
  assert.equal(p[0].body.location, 4);
  assert.equal(p[0].body.notes, '補貨給 B 公司門市');
  assert.equal(p[0].csrf, mock.CSRF);
  await page.waitForFunction(() => /A 公司\s*共 115 件/.test(document.querySelector('.ith-qt').textContent));
  noErrors();
});

test('快速調貨：超量時以現有數量送出；同庫位不可送出', async () => {
  await page.click('text=🔀 快速調貨');
  await page.fill('[aria-label="搜尋料號或品名"]', 'A-P01-S1');
  await page.click('.ith-qt button:has-text("A-P01-S1-XL")');
  await page.waitForSelector('#ith-src-2');
  await page.check('#ith-src-2');
  await page.selectOption('[aria-label="目的庫位"]', '4');
  await page.fill('[aria-label="數量"]', '10');
  assert.match(await page.textContent('.ith-qt .ith-ok'), /來源與目的庫位相同/);
  assert.equal(await page.getAttribute('text=確認調貨', 'disabled'), 'disabled');

  await page.selectOption('[aria-label="目的庫位"]', '5');
  await page.fill('[aria-label="數量"]', '50');
  await page.click('text=確認調貨');
  await page.waitForSelector('[aria-label="異常操作確認"]');
  assert.match(await page.textContent('[aria-label="異常操作確認"]'), /超量/);
  await page.click('text=確認繼續');
  await page.waitForFunction(() => /已調貨 30 件/.test(document.querySelector('.ith-qt').textContent));
  assert.equal((await posts())[0].body.items[0].quantity, 30);
  noErrors();
});

test('快速調貨：沒有權限時顯示清楚的中文訊息', async () => {
  await page.context().clearCookies();
  await page.click('text=🔀 快速調貨');
  await page.fill('[aria-label="搜尋料號或品名"]', 'A-P01-S1');
  await page.click('.ith-qt button:has-text("A-P01-S1-XL")');
  await page.waitForSelector('#ith-src-1');
  await page.check('#ith-src-1');
  await page.selectOption('[aria-label="目的庫位"]', '2');
  await page.selectOption('[aria-label="目的庫位"]', '5');
  await page.fill('[aria-label="數量"]', '1');
  await page.click('text=確認調貨');
  await page.click('text=確認繼續');
  await page.waitForFunction(() => /沒有權限/.test(document.querySelector('.ith-qt').textContent));
  noErrors();
});

test('異動紀錄：顯示調貨紀錄、資料庫內容不被當成 HTML 執行', async () => {
  await page.evaluate(async () => {
    const csrf = document.cookie.match(/csrftoken=([^;]+)/)[1];
    await fetch('/api/stock/transfer/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify({ items: [{ pk: 1, quantity: 2 }], location: 4, notes: '<img src=x onerror="window.__xss=1">' }) });
  });
  await page.click('text=📋 異動紀錄');
  await page.waitForFunction(() => /共 \d+ 筆/.test(document.querySelector('.ith-audit').textContent));
  const rows = await page.$$eval('.ith-audit tbody tr', (t) => t.map((r) => r.textContent));
  assert.ok(rows.some((r) => /tester/.test(r) && /轉移庫位/.test(r)), '應顯示操作人與中文動作');
  assert.equal(await page.$('.ith-audit img'), null, '備註中的 HTML 不應被執行');
  assert.equal(await page.evaluate(() => window.__xss), undefined);
  noErrors();
});

test('重複載入不會產生兩組按鈕', async () => {
  await page.addScriptTag({ path: HELPER });
  assert.equal((await page.$$('text=🔀 快速調貨')).length, 1);
  noErrors();
});
