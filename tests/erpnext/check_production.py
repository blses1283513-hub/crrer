"""妮菈 ERPNext 正式版的端對端檢查（GitHub Actions 使用；也可在本機對已安裝的系統執行）。

  --phase install   檢查安裝結果，並建立「備份前標記」
  --phase mutate    刪除「備份前標記」、建立「備份後標記」（模擬備份後的資料變動）
  --phase restored  檢查還原結果：「備份前標記」回來、「備份後標記」消失；並重新檢查安裝結果
"""

import argparse
import http.cookiejar
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BEFORE, AFTER = "備份前標記", "備份後標記"
failures = []


def check(label, ok, detail=""):
    print(f"{'✓' if ok else '✗'} {label}{'：' + str(detail) if detail else ''}", flush=True)
    if not ok:
        failures.append(label)


class Client:
    def __init__(self, base):
        self.base = base
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, path, data=None, method=None):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(self.base + path, data=body, method=method, headers={"Content-Type": "application/json"})
        try:
            with self.op.open(req, timeout=120) as r:
                return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            return e.code, {}

    def get_list(self, doctype, fields='["name"]', filters="[]"):
        q = urllib.parse.quote
        return self.call(f"/api/resource/{q(doctype, safe='')}?limit_page_length=500&fields={q(fields)}&filters={q(filters)}")[1].get("data", [])

    def get_doc(self, doctype, name):
        q = lambda s: urllib.parse.quote(s, safe="")
        return self.call(f"/api/resource/{q(doctype)}/{q(name)}")[1].get("data", {})

    def exists(self, doctype, name):
        q = lambda s: urllib.parse.quote(s, safe="")
        return self.call(f"/api/resource/{q(doctype)}/{q(name)}")[0] == 200


def check_install(c, expect_version, p0_only=False):
    versions = c.call("/api/method/frappe.utils.change_log.get_versions")[1].get("message", {})
    check("已安裝 frappe、erpnext、nila_app", {"frappe", "erpnext", "nila_app"} <= set(versions), list(versions))
    if expect_version:
        got = versions.get("nila_app", {}).get("version")
        check(f"nila_app 版本 {expect_version}", got == expect_version, got)
    companies = c.get_list("Company", '["name","abbr","default_currency","country","default_in_transit_warehouse"]')
    check("公司：妮菈穿戴甲（NL、新台幣、台灣）", len(companies) == 1 and companies[0]["name"] == "妮菈穿戴甲"
          and companies[0]["abbr"] == "NL" and companies[0]["default_currency"] == "TWD" and companies[0]["country"] == "Taiwan", companies)
    whs = {w["name"]: w["warehouse_type"] for w in c.get_list("Warehouse", '["name","warehouse_type"]', '[["is_group","=",0]]')}
    wanted = ["總公司 - NL", "分公司A - NL", "分公司B - NL", "分公司C - NL", "分公司D - NL"]
    check("倉庫：總公司與 4 間分公司", all(w in whs for w in wanted), sorted(whs))
    check("在途倉，並設為公司預設在途倉", whs.get("在途 - NL") == "Transit" and companies and companies[0]["default_in_transit_warehouse"] == "在途 - NL")
    shapes = [(v["attribute_value"], v["abbr"]) for v in c.get_doc("Item Attribute", "甲型").get("item_attribute_values", [])]
    check("甲型：長梯 LT、短梯 ST、長橢圓 LO", shapes == [("長梯", "LT"), ("短梯", "ST"), ("長橢圓", "LO")], shapes)
    sizes = [v["attribute_value"] for v in c.get_doc("Item Attribute", "尺寸").get("item_attribute_values", [])]
    check("尺寸：XS、S、M、L", sizes == ["XS", "S", "M", "L"], sizes)
    fields = {f["name"] for f in c.get_list("Custom Field", '["name"]', '[["dt","=","Item"]]')}
    check("自訂欄位：商品狀態、補貨目標", {"Item-nila_status", "Item-nila_reorder_target"} <= fields)
    pls = {p["name"] for p in c.get_list("Price List", '["name"]')}
    check("價格表：官網售價、實體售價", {"官網售價", "實體售價"} <= pls)
    ss = c.get_doc("System Settings", "System Settings")
    check("繁體中文、台北時區", ss.get("language") == "zh-TW" and ss.get("time_zone") == "Asia/Taipei", (ss.get("language"), ss.get("time_zone")))
    terms = c.get_list("Translation", '["source_text","translated_text"]', '[["language","=","zh-TW"]]')
    check("用語修正（Projected Qty → 預計庫存）", any(t["source_text"] == "Projected Qty" and t["translated_text"] == "預計庫存" for t in terms))
    if p0_only:
        return
    # P1 商品
    check("自訂欄位：甲型、尺寸、成本、官網售價、實體售價",
          {f"Item-nila_{f}" for f in ["shape", "size", "cost", "web_price", "store_price"]} <= fields)
    st = c.get_doc("Stock Settings", "Stock Settings")
    check("預設倉庫是總公司", st.get("default_warehouse") == "總公司 - NL", st.get("default_warehouse"))
    off = {w["name"] for w in c.get_list("Warehouse", '["name"]', '[["disabled","=",1]]')}
    check("英文預設倉庫已停用", {"Stores - NL", "Finished Goods - NL", "Work In Progress - NL", "Goods In Transit - NL"} <= off, sorted(off))
    pages = {pg["name"] for pg in c.get_list("Page", '["name"]', '[["module","=","Nila"]]')}
    check("頁面：新增款式、商品匯入匯出", {"nila-new-style", "nila-item-import"} <= pages, sorted(pages))
    status, body = c.call("/api/method/nila_app.products.get_style_options")
    check("新增款式 API 可用", status == 200 and body.get("message", {}).get("sizes") == ["XS", "S", "M", "L"], status)
    # P2 庫存表、P3 全公司補貨、P4 訂單調度
    check("允許負庫存", st.get("allow_negative_stock") == 1)
    check("頁面：庫存表、補貨建議", {"nila-stock-matrix", "nila-replenish"} <= pages, sorted(pages))
    cf = {f["name"] for f in c.get_list("Custom Field", '["name"]', '[["fieldname","like","nila_%"]]')}
    check("自訂欄位：訂單出貨狀態、調撥單調入倉、補貨單建議數",
          {"Sales Order-nila_dispatch_status", "Stock Entry-nila_destination", "Stock Entry-nila_sales_order",
           "Material Request Item-nila_suggested_qty"} <= cf, sorted(cf))
    kinds = {r["kind"] for r in c.get_list("Nila Reason", '["kind"]')}
    check("原因選項：補貨調整、負庫存、調撥調整", kinds == {"補貨調整", "負庫存", "調撥調整"}, kinds)
    check("預設廠商", c.exists("Supplier", "預設廠商"))
    try:
        with c.op.open(c.base + "/assets/nila_app/js/nila.js", timeout=60) as r:
            asset = r.status == 200 and b"nila.style_block" in r.read()
    except urllib.error.HTTPError:
        asset = False
    check("共用畫面檔（/assets/nila_app）可以下載", asset)
    # P5 門市銷售與會員
    check("頁面：門市銷售、消費報表、條碼", {"nila-store-sale", "nila-sales-report", "nila-barcode"} <= pages, sorted(pages))
    roles = {r["name"] for r in c.get_list("Role", '["name"]', '[["name","like","妮菈%"]]')}
    check("5 個層級的角色", roles == {"妮菈管理員", "妮菈營運主管", "妮菈總公司作業", "妮菈門市店長", "妮菈門市店員"}, roles)
    check("自訂欄位：會員手機、銷售管道、結帳代碼、收銀人員",
          {"Customer-nila_phone", "Sales Invoice-nila_channel", "Sales Invoice-nila_client_id", "Sales Invoice-nila_cashier"} <= cf)
    check("會員群組、門市散客、官網散客", c.exists("Customer Group", "會員") and c.exists("Customer", "門市散客") and c.exists("Customer", "官網散客"))
    profiles = {x["name"] for x in c.get_list("POS Profile", '["name"]')}
    check("每個門市的收銀設定", {"門市-總公司", "門市-分公司A", "門市-分公司B", "門市-分公司C", "門市-分公司D"} <= profiles, sorted(profiles))
    # P6 帳號、權限、抽獎
    check("頁面：帳號管理", "nila-accounts" in pages)
    check("可以用帳號登入（不需信箱）", c.get_doc("System Settings", "System Settings").get("allow_login_using_user_name") == 1)
    check("「妮菈」首頁", c.exists("Workspace", "妮菈"))
    check("抽獎活動資料表", c.call("/api/resource/Nila%20Lottery?limit_page_length=1")[0] == 200)
    cost = c.call("/api/method/frappe.client.get_value?doctype=Property%20Setter&fieldname=value&filters="
                  + urllib.parse.quote('{"doc_type":"Item","field_name":"valuation_rate","property":"permlevel"}'))[1]
    check("成本欄位只有可看成本的層級看得到", (cost.get("message") or {}).get("value") == "5", cost)
    # P7 SHOPLINE
    check("頁面：SHOPLINE 官網訂單", "nila-shopline" in pages)
    check("自訂欄位：銷售訂單的銷售管道、官網訂單編號",
          {"Sales Order-nila_channel", "Sales Order-nila_shopline_number", "Sales Order-nila_shopline_id"} <= cf)
    status, body = c.call("/api/method/nila_app.shopline.get_settings")
    check("SHOPLINE 同步預設關閉（更新不會自動開啟）", status == 200 and not body.get("message", {}).get("enabled"), status)
    for method in ["nila_app.matrix.get_matrix", "nila_app.replenish.get_suggestions", "nila_app.retail.sale_context",
                   "nila_app.salesreport.get_options", "nila_app.accounts.list_accounts", "nila_app.shopline.list_orders"]:
        status, _body = c.call(f"/api/method/{method}")
        check(f"API 可用：{method}", status == 200, status)


def make_group(c, name):
    return c.call("/api/resource/Item%20Group", {"item_group_name": name, "parent_item_group": "All Item Groups"})[0] == 200


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8090")
    p.add_argument("--password", required=True)
    p.add_argument("--expect-version")
    p.add_argument("--phase", choices=["install", "mutate", "restored"], required=True)
    p.add_argument("--p0-only", action="store_true", help="只檢查 P0（0.1.x 版）的項目")
    a = p.parse_args()

    c = Client(a.url)
    status, body = c.call("/api/method/login", {"usr": "Administrator", "pwd": a.password})
    check("以設定的管理員密碼登入", status == 200 and body.get("message") == "Logged In", status)
    if status != 200:
        return 1

    if a.phase == "install":
        check_install(c, a.expect_version, a.p0_only)
        check(f"建立「{BEFORE}」", c.exists("Item Group", BEFORE) or make_group(c, BEFORE))
    elif a.phase == "mutate":
        q = urllib.parse.quote(BEFORE, safe="")
        check(f"刪除「{BEFORE}」", c.call(f"/api/resource/Item%20Group/{q}", method="DELETE")[0] in (200, 202))
        check(f"建立「{AFTER}」", make_group(c, AFTER))
    else:
        check(f"還原後「{BEFORE}」回來了", c.exists("Item Group", BEFORE))
        check(f"還原後「{AFTER}」消失了（備份之後的變動被取代）", not c.exists("Item Group", AFTER))
        check_install(c, a.expect_version, a.p0_only)

    print(f"\n{'全部通過' if not failures else '未通過：' + '、'.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
