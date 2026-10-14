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
