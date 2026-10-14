"""P7（SHOPLINE 官網訂單同步）的整合測試：在已安裝的正式版 ERPNext 容器內執行，結束時全部復原。

測試時在容器內啟動一個「模擬的 SHOPLINE」（依官方文件的 GET /v1/orders、GET /v1/token/info 格式），
不會連到真正的 SHOPLINE，也不需要真的金鑰。

    docker compose cp live_shopline.py backend:/tmp/live_shopline.py
    docker compose exec backend bash -c "cd sites && ../env/bin/python /tmp/live_shopline.py nila"
"""

import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import frappe

failures = []
TOKEN = "test-token-for-mock-only-9f3a"
PW = "Nila-Test-2026!qz"


def check(label, ok, detail=""):
    print(f"{'✓' if ok else '✗'} {label}{'：' + str(detail) if detail not in ('', None) else ''}", flush=True)
    if not ok:
        failures.append(label)


def raises(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        frappe.clear_messages()
        return str(e)
    return None


def as_user(user, fn, *args, **kwargs):
    frappe.set_user(user)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user("Administrator")


def denied(user, fn, *args, **kwargs):
    err = raises(as_user, user, fn, *args, **kwargs)
    return bool(err) and ("沒有權限" in err or "Not permitted" in err or "permission" in err.lower())


# ---------- 模擬的 SHOPLINE ----------

class Mock:
    orders = {}
    requests = []
    throttle = 0
    merchant = {"_id": "m1", "handle": "nilatest", "name": "妮菈測試商店", "email": "shop@example.com"}


def utc_iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000+00:00")


def _key(iso):  # ISO → "YYYY-MM-DD HH:MM:SS"（UTC）
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, body, headers=None):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        Mock.requests.append({"path": u.path, "q": q, "ua": self.headers.get("User-Agent"),
                              "auth": self.headers.get("Authorization")})
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            return self.send(401, {"error": "Unauthorized", "code": "Unauthorized"})
        if Mock.throttle > 0:
            Mock.throttle -= 1
            return self.send(429, {"error": "Rate limit exceeded", "code": "RateLimitExceeded"}, {"Retry-After": "0.2"})
        if u.path == "/v1/token/info":
            return self.send(200, {"staff": {}, "merchant": Mock.merchant, "user": {}})
        if u.path != "/v1/orders":
            return self.send(404, {"error": "not found"})
        items = sorted(Mock.orders.values(), key=lambda o: o["created_at"])
        if q.get("order_ids[]"):
            ids = q["order_ids[]"]
            found = [o for o in items if o["id"] in ids]
            return self.send(200, {"items": found, "pagination": {"current_page": 1, "per_page": 50, "total_pages": 1,
                                                                    "total_count": len(found)},
                                   "error": {"notfound": [i for i in ids if i not in Mock.orders], "gone": []}})
        after, before = q.get("updated_after", [None])[0], q.get("updated_before", [None])[0]
        items = [o for o in items if (not after or _key(o["updated_at"]) >= after) and (not before or _key(o["updated_at"]) <= before)]
        per, page = int(q.get("per_page", ["24"])[0]), int(q.get("page", ["1"])[0])
        pages = max(1, -(-len(items) // per))
        return self.send(200, {"items": items[(page - 1) * per: page * per],
                               "pagination": {"current_page": page, "per_page": per, "total_pages": pages, "total_count": len(items)}})


def start_mock():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def money(v):
    return {"cents": v, "dollars": float(v), "currency_iso": "TWD", "currency_symbol": "NT$", "label": f"NT${v}"}


def line(sku, qty, price, discounted=None, kind="Product"):
    it = {"id": f"li-{sku}-{qty}", "item_type": kind, "sku": sku, "quantity": qty, "item_price": money(price),
          "price": money(price), "total": money(price * qty), "title_translations": {"zh-hant": f"測試 {sku}"}}
    if discounted is not None:
        it["discounted_total"] = money(discounted)
    return it


def add_order(oid, lines, status="confirmed", pay="completed", minutes_ago=10, **kw):
    now = datetime.now(timezone.utc)
    o = Mock.orders.get(oid) or {"id": oid, "order_number": f"SL{oid}", "created_at": utc_iso(now - timedelta(minutes=minutes_ago)),
                                 "customer_name": f"顧客{oid}", "customer_phone": "0912000000", "created_by": "shop", "type": "general"}
    o.update({"status": status, "order_payment": {"status": pay}, "subtotal_items": lines,
              "total": money(sum(i["total"]["dollars"] for i in lines) + 60), "updated_at": utc_iso(now - timedelta(seconds=30))})
    o.update(kw)
    Mock.orders[oid] = o
    return o


def update_order(oid, **kw):
    o = Mock.orders[oid]
    if "lines" in kw:
        o["subtotal_items"] = kw.pop("lines")
    if "pay" in kw:
        o["order_payment"] = {"status": kw.pop("pay")}
    o.update(kw)
    o["updated_at"] = utc_iso(datetime.now(timezone.utc))


# ---------- 測試 ----------

def run():
    from nila_app import accounts, products, shopline, stock
    from nila_app import levels as L
    from nila_app import shoplinerules as S

    srv = start_mock()
    frappe.local.conf["nila_shopline_base_url"] = f"http://127.0.0.1:{srv.server_address[1]}/v1"
    hq = stock.hq_warehouse()
    base = shopline._counts()  # 網站上原本就有的紀錄（只比較這次測試新增的）

    # ---------- 安裝結果 ----------
    check("資料表：SHOPLINE 設定、官網訂單紀錄", frappe.db.exists("DocType", "Nila SHOPLINE Settings")
          and frappe.db.exists("DocType", "Nila SHOPLINE Order"))
    check("銷售訂單自訂欄位：銷售管道、官網訂單編號、SHOPLINE 訂單 ID（不能重複）",
          all(frappe.get_meta("Sales Order").get_field(f) for f in ["nila_channel", "nila_shopline_number", "nila_shopline_id"])
          and frappe.get_meta("Sales Order").get_field("nila_shopline_id").unique)
    jobs = frappe.get_all("Scheduled Job Type", filters={"method": "nila_app.shopline.scheduled"}, fields=["frequency", "stopped"])
    check("排程：每分鐘檢查一次", jobs and jobs[0].frequency == "Cron" and not jobs[0].stopped, jobs)
    ws = frappe.get_doc("Workspace", "妮菈")
    check("「妮菈」首頁有 SHOPLINE 官網訂單", "nila-shopline" in {l.link_to for l in ws.links if l.type == "Link"})
    s0 = frappe.get_single("Nila SHOPLINE Settings")
    check("預設關閉自動同步", not s0.enabled, s0.enabled)

    # 帳號：營運主管可以看官網訂單、不能改設定；總公司作業看不到
    for u in ("sl_manager", "sl_hq"):
        if frappe.db.exists("User", f"{u}@nila.local"):
            frappe.delete_doc("User", f"{u}@nila.local", ignore_permissions=True, force=True)
    u_mgr = accounts.save_account({"full_name": "主管", "username": "sl_manager", "level": L.MANAGER, "password": PW})["name"]
    u_hq = accounts.save_account({"full_name": "總公司", "username": "sl_hq", "level": L.HQ_STAFF, "password": PW})["name"]

    # ---------- 設定與金鑰 ----------
    frappe.db.set_single_value("Nila SHOPLINE Settings", {"enabled": 0, "synced_until": "", "last_run": None, "last_ok": None,
                                                          "handle": "", "merchant_name": ""})
    since = (frappe.utils.now_datetime() - timedelta(hours=1)).replace(microsecond=0)
    res = shopline.save_settings({"token": TOKEN, "handle": "", "interval": 5, "exclude_pos": 1, "enabled": 0,
                                  "import_since": str(since)})
    check("儲存設定：金鑰只回傳最後 4 碼", res["token_set"] and res["token_hint"].endswith("9f3a") and TOKEN not in json.dumps(res),
          res["token_hint"])
    stored = frappe.db.sql("select value from `tabSingles` where doctype=%s and field='token'", "Nila SHOPLINE Settings")
    check("資料庫裡的設定不是明碼（另外加密保存）", TOKEN not in str(stored), stored)
    auth = frappe.db.sql("select password from `__Auth` where doctype=%s and fieldname='token'", "Nila SHOPLINE Settings")
    check("加密保存的金鑰不是明碼", auth and TOKEN not in auth[0][0])
    res = shopline.save_settings({"token": "", "handle": "", "interval": 5, "exclude_pos": 1, "enabled": 0,
                                  "import_since": str(since)})
    check("金鑰欄位空白儲存：原本的金鑰不變", res["token_set"] and shopline._token() == TOKEN)
    err = raises(shopline.save_settings, {"interval": 1, "import_since": str(since)})
    check("同步間隔至少 2 分鐘", err and "至少 2 分鐘" in err, err)
    m = as_user(u_mgr, shopline.get_settings)
    check("營運主管：可以看狀態，看不到金鑰、不能修改", not m["can_edit"] and m["token_hint"] == "")
    check("營運主管：不能修改設定、測試連線、立即同步",
          denied(u_mgr, shopline.save_settings, {"enabled": 0}) and denied(u_mgr, shopline.test_connection)
          and denied(u_mgr, shopline.sync_now))
    check("總公司作業：不能開官網訂單", denied(u_hq, shopline.get_settings) and denied(u_hq, shopline.list_orders))

    # ---------- 測試連線 ----------
    r = shopline.test_connection(token="wrong-token")
    check("測試連線：金鑰錯誤", not r["ok"] and "金鑰無效" in r["message"], r)
    Mock.requests.clear()
    r = shopline.test_connection()
    check("測試連線：成功，顯示商店名稱", r["ok"] and "妮菈測試商店" in r["message"], r)
    check("沒填商店代號：自動帶入", frappe.db.get_single_value("Nila SHOPLINE Settings", "handle") == "nilatest")
    check("送出的標頭：Bearer 金鑰", Mock.requests and Mock.requests[-1]["auth"] == f"Bearer {TOKEN}")
    Mock.requests.clear()
    shopline.test_connection()
    check("送出的標頭：User-Agent 是商店代號", Mock.requests[-1]["ua"] == "nilatest", Mock.requests[-1]["ua"])

    # ---------- 準備商品與官網訂單 ----------
    opts = products.get_style_options()
    style = products.create_style({"name": "官網測試款", "cost": 100, "web_price": 390, "store_price": 350, "status": "停售",
                                   "cells": [{"shape": opts["shapes"][0], "size": s} for s in opts["sizes"][:3]], "targets": {}})
    x, y, z = style["variants"]
    Mock.orders.clear()
    add_order("A", [line(x, 2, 390, discounted=700), line(y.lower(), 1, 390), line(x, 1, 0, kind="Gift")], status="confirmed")
    add_order("B", [line(x, 1, 390), line("9999-NO-SUCH", 1, 390)])
    add_order("C", [line(x, 1, 390)], created_by="pos")
    add_order("D", [line(x, 1, 390)], status="cancelled", pay="refunded")
    add_order("G", [line(z, 1, 390)], status="completed")
    add_order("R", [line(x, 1, 390)], type="return")
    add_order("H", [line(y, 1, 390)], minutes_ago=9)
    for i in range(55):  # 讓結果超過一頁（每頁 50 筆）
        add_order(f"T{i:02d}", [line(x, 1, 390)], status="temp", minutes_ago=30)
    add_order("OLD", [line(x, 1, 390)], minutes_ago=600)
    Mock.orders["OLD"]["updated_at"] = utc_iso(datetime.now(timezone.utc) - timedelta(hours=5))  # 開始時間以前的訂單

    # ---------- 關閉時不會同步 ----------
    Mock.requests.clear()
    shopline.scheduled()
    check("關閉時排程不會連到 SHOPLINE", not Mock.requests)

    # ---------- 第一次同步 ----------
    real_create = shopline._create_sales_order

    def broken(order, lines, skus):
        if order["id"] == "H":
            raise RuntimeError("模擬的錯誤")
        return real_create(order, lines, skus)

    shopline._create_sales_order = broken
    Mock.throttle = 1  # 第一次請求回 429，要自動等一下再試
    Mock.requests.clear()
    res = shopline.sync(commit=False)
    shopline._create_sales_order = real_create
    check("同步成功", res["ok"], res)
    pages = [rq for rq in Mock.requests if rq["path"] == "/v1/orders"]
    check("超過每秒限制（429）時自動等一下再試", len(pages) >= 3 and Mock.throttle == 0, len(pages))
    q = pages[-1]["q"]
    check("查詢參數：updated_after／updated_before（UTC）、每頁 50 筆、分頁",
          q.get("per_page") == ["50"] and q.get("page") == ["2"] and len(q["updated_after"][0]) == 19, q)
    expect_after = (since - timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    check("第一次從設定的開始時間（換算成 UTC）查起", q["updated_after"][0] == expect_after, (q["updated_after"][0], expect_after))
    log = lambda oid: frappe.db.get_value("Nila SHOPLINE Order", oid, ["state", "sales_order", "message", "items_json"], as_dict=True)
    a = log("A")
    check("正常訂單：建立銷售訂單", a and a.state == S.CREATED and a.sales_order, a)
    so = frappe.get_doc("Sales Order", a.sales_order)
    check("銷售訂單：官網散客、銷售管道官網、總公司出貨、已送出",
          (so.customer, so.nila_channel, so.set_warehouse, so.docstatus) == ("官網散客", "官網", hq, 1),
          (so.customer, so.nila_channel, so.set_warehouse, so.docstatus))
    rows = {(d.item_code, d.qty, d.rate) for d in so.items}
    check("明細：同 SKU 合併、小寫 SKU 也對得到、單價用折扣後金額、贈品 0 元",
          rows == {(x, 3, round(700 / 3, 2)), (y, 1, 390)}, rows)
    check("官網訂單編號記在訂單上", so.nila_shopline_number == "SLA" and so.po_no == "SLA" and so.nila_shopline_id == "A")
    check("總公司缺貨也照樣建立，出貨狀態由調度計算", bool(so.nila_dispatch_status), so.nila_dispatch_status)
    check("停售的商品：官網已賣出，照樣建立", frappe.db.get_value("Item", x, "nila_status") == "停售")
    b = log("B")
    check("對不到料號：待處理，不建立訂單", b.state == S.PENDING and not b.sales_order and "9999-NO-SUCH" in b.message, b)
    check("待處理紀錄保留官網的商品", "9999-NO-SUCH" in (b.items_json or ""))
    check("SHOPLINE 門市 POS 訂單：略過", log("C").state == S.SKIPPED)
    check("建立前就取消／退款：略過", log("D").state == S.SKIPPED and not log("D").sales_order)
    check("退貨單：待處理", log("R").state == S.PENDING)
    check("暫存（temp）：略過", log("T00").state == S.SKIPPED and log("T54").state == S.SKIPPED)
    check("開始時間以前的訂單：不匯入", not log("OLD"))
    h = log("H")
    check("某一筆出錯：放進待處理，其他訂單照樣處理", h.state == S.PENDING and "系統處理時發生錯誤" in h.message
          and log("G").state == S.CREATED, h)
    st = frappe.get_single("Nila SHOPLINE Settings")
    check("記錄同步狀態", st.last_ok and st.synced_until and "查到" in st.last_result, st.last_result)
    check("有待處理時通知管理者", frappe.db.exists("Notification Log", {"for_user": "Administrator", "subject": ["like", "%待處理%"],
                                                                 "link": "/app/nila-shopline"}))

    # ---------- 重複查到不會重複建立 ----------
    until1 = frappe.db.get_single_value("Nila SHOPLINE Settings", "synced_until")
    Mock.requests.clear()
    shopline.sync(commit=False)
    after2 = [rq for rq in Mock.requests if rq["path"] == "/v1/orders"][0]["q"]["updated_after"][0]
    check("之後從上次同步到的時間往前 2 分鐘查起", after2 == (datetime.strptime(until1, "%Y-%m-%d %H:%M:%S")
                                                 - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S"), (after2, until1))
    frappe.db.set_single_value("Nila SHOPLINE Settings", "synced_until", "")
    shopline.sync(commit=False)
    n = frappe.db.count("Sales Order", {"nila_shopline_id": "A"})
    check("同一段時間再同步一次：不會重複建立訂單", n == 1, n)

    # ---------- 取消、退款 ----------
    update_order("A", status="cancelled")
    shopline.sync(commit=False)
    check("官網取消：還沒出貨的銷售訂單自動取消", frappe.db.get_value("Sales Order", a.sales_order, "docstatus") == 2
          and log("A").state == S.CANCELLED, log("A"))
    shopline.sync(commit=False)
    check("取消後再同步：不會再動", log("A").state == S.CANCELLED)

    g = log("G")
    from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note

    dn = make_delivery_note(g.sales_order)
    dn.insert()
    dn.submit()
    update_order("G", pay="refunded")
    shopline.sync(commit=False)
    g2 = log("G")
    check("已出貨後才退款：待處理，訂單不自動取消", g2.state == S.PENDING and "已經出貨" in g2.message
          and frappe.db.get_value("Sales Order", g.sales_order, "docstatus") == 1, g2)
    check("營運主管：可以看官網訂單、標記已人工處理", any(r["name"] == "G" for r in as_user(u_mgr, shopline.list_orders, S.PENDING)["rows"]))
    as_user(u_mgr, shopline.mark_handled, "G", "已辦理退貨")
    g3 = frappe.get_doc("Nila SHOPLINE Order", "G")
    check("標記已人工處理：記錄處理人員與備註", g3.state == S.HANDLED and g3.handled_by == u_mgr and "已辦理退貨" in g3.message)
    update_order("G", pay="refunded")
    shopline.sync(commit=False)
    check("人工處理後再同步：不再提醒", log("G").state == S.HANDLED)
    err = raises(shopline.mark_handled, "A")
    check("只有待處理的可以標記", err and "只有待處理" in err, err)

    # ---------- 修正後重新處理 ----------
    update_order("B", lines=[line(x, 1, 390), line(z, 1, 390)])
    r = as_user(u_mgr, shopline.retry, "B")
    check("在 SHOPLINE 改好 SKU 後按「重新處理」：建立訂單", r["state"] == S.CREATED and r["sales_order"], r)
    shopline.retry("H")
    check("出錯的訂單重新處理：建立訂單", log("H").state == S.CREATED, log("H"))
    err = raises(shopline.retry, "NOPE")
    check("重新處理不存在的紀錄：提示", bool(err), err)

    # ---------- 建立後官網修改內容 ----------
    update_order("H", lines=[line(y, 3, 390)])
    shopline.sync(commit=False)
    hh = log("H")
    check("建立後官網改了數量：待處理，不自動改訂單", hh.state == S.PENDING and "修改" in hh.message
          and frappe.db.get_value("Sales Order Item", {"parent": hh.sales_order}, "qty") == 1, hh)

    # ---------- 排程間隔 ----------
    shopline.save_settings({"token": "", "handle": "nilatest", "interval": 5, "exclude_pos": 1, "enabled": 1,
                            "import_since": str(since)})
    frappe.db.set_single_value("Nila SHOPLINE Settings", "synced_until", "")
    frappe.db.set_single_value("Nila SHOPLINE Settings", "last_run", frappe.utils.now_datetime())
    Mock.requests.clear()
    shopline.scheduled()
    check("啟用後：還沒到間隔不會同步", not Mock.requests)
    frappe.db.set_single_value("Nila SHOPLINE Settings", "last_run", frappe.utils.now_datetime() - timedelta(minutes=6))
    shopline.sync = (lambda real: (lambda commit=True, manual=False, until=None: real(commit=False)))(shopline.sync)
    shopline.scheduled()
    check("啟用後：到了間隔就同步", any(rq["path"] == "/v1/orders" for rq in Mock.requests))

    # ---------- 金鑰失效 ----------
    shopline.save_settings({"token": "expired-token-xxxx", "handle": "nilatest", "interval": 5, "exclude_pos": 1, "enabled": 1,
                            "import_since": str(since)})
    before = frappe.db.get_single_value("Nila SHOPLINE Settings", "synced_until")
    res = shopline.sync(commit=False)
    st = frappe.get_single("Nila SHOPLINE Settings")
    check("金鑰失效：同步失敗並記錄原因，下次從同一個時間再查", not res["ok"] and st.last_result.startswith("失敗")
          and "金鑰無效" in st.last_result and st.synced_until == before, st.last_result)
    check("同步失敗時通知管理者", frappe.db.exists("Notification Log", {"for_user": "Administrator", "subject": ["like", "%失敗%金鑰%"]}))
    lst = shopline.list_orders()
    check("官網訂單清單：各狀態筆數", {k: lst["counts"].get(k, 0) - base.get(k, 0) for k in (S.CREATED, S.PENDING, S.HANDLED, S.CANCELLED)}
          == {S.CREATED: 1, S.PENDING: 2, S.HANDLED: 1, S.CANCELLED: 1}, lst["counts"])
    check("網站訂單不計入會員消費（建立的是銷售訂單，不是門市銷售）",
          not frappe.db.exists("Sales Invoice", {"nila_channel": "門市", "customer": "官網散客"}))
    srv.shutdown()


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "nila"
    frappe.init(site=site, sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        run()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        check("執行過程沒有錯誤", False, e)
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.destroy()
    print(f"\n{'全部通過' if not failures else '未通過：' + '、'.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
