"""妮菈穿戴甲：ERPNext 16 試用版的初始設定與範例資料。

在 ERPNext 的 backend 容器內執行（使用 ERPNext 本身的程式，不需要管理員密碼，也不需要在電腦上安裝 Python）：

    cd /home/frappe/frappe-bench/sites
    ../env/bin/python /tmp/nila-seed/seed_trial.py --site frontend \
        --csv /tmp/nila-seed/sample-skus.csv --shapes /tmp/nila-seed/shapes.csv

做的事（可重複執行，已存在的資料不會重複建立）：
  1. 完成初次設定（公司、台灣、新台幣、台北時區），介面語言改為繁體中文，開啟排程器
  2. 建立倉庫：總公司、各分公司（依試算表欄位）、在途
  3. 建立單位「件」、商品群組「穿戴甲」、價格表「官網售價」「實體售價」、自訂欄位「商品狀態」「補貨目標」
  4. 建立甲型、尺寸兩個屬性；依試算表建立款式（範本）與規格（變體），料號由 ERPNext 依屬性縮寫自動產生
  5. 匯入期初庫存（各公司）
  6. 建立客戶需求的情境：官網訂單 5 件 0001-LT-M（總公司 2、分公司A 1）
  7. 套用用語修正（例：Item → 商品、Projected Qty → 預計庫存）
  8. 列出該規格的「全公司預計庫存」與建議補貨量（客戶的例子：−2、補 12）

試算表格式（第一列為標題）：
  SKU 編碼, 款式編號, 款式名稱, 甲型, 尺寸, 商品狀態, 成本, 官網售價, 實體售價, 補貨目標, 總公司, 分公司A, …
  「補貨目標」之後的每一欄都是一個公司（倉庫）的期初庫存，第一個公司欄必須是「總公司」。
"""

import argparse
import csv
import datetime
import sys
from collections import OrderedDict

SIZES = ["XS", "S", "M", "L"]
STATUSES = ["上架", "停售", "停產"]
FIXED_COLUMNS = ["SKU 編碼", "款式編號", "款式名稱", "甲型", "尺寸", "商品狀態", "成本", "官網售價", "實體售價", "補貨目標"]
HQ = "總公司"
TRANSIT = "在途"
ITEM_GROUP = "穿戴甲"
UOM = "件"
PRICE_LISTS = {"官網售價": "官網售價", "實體售價": "實體售價"}
SCENARIO_CUSTOMER = "官網散客"
SCENARIO_MARK = "NILA-TRIAL-SCENARIO"
OPENING_MARK = "NILA-TRIAL-OPENING"
SCENARIO_SKU = "0001-LT-M"
SCENARIO_QTY = 5

SETUP_ARGS = {
    "language": "zh-TW",
    "country": "Taiwan",
    "timezone": "Asia/Taipei",
    "currency": "TWD",
    "company_name": "妮菈穿戴甲（試用）",
    "company_abbr": "NL",
    "chart_of_accounts": "Standard",
    "fy_start_date": "2026-01-01",
    "fy_end_date": "2026-12-31",
    "setup_demo": 0,
}


class SheetError(ValueError):
    pass


# ---------------- 試算表（純邏輯，不需要 ERPNext，可單獨測試） ----------------

def read_shapes(path):
    """甲型 → 縮寫。縮寫 2–3 個大寫英文字母，不可重複。"""
    shapes = OrderedDict()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            name, abbr = (row.get("甲型") or "").strip(), (row.get("縮寫") or "").strip()
            if not name or not abbr:
                raise SheetError(f"甲型檔第 {i} 列：甲型與縮寫都要填")
            if not (abbr.isascii() and abbr.isalpha() and abbr.isupper() and 2 <= len(abbr) <= 3):
                raise SheetError(f"甲型檔第 {i} 列：縮寫「{abbr}」必須是 2–3 個大寫英文字母")
            if name in shapes or abbr in shapes.values():
                raise SheetError(f"甲型檔第 {i} 列：甲型或縮寫重複（{name} / {abbr}）")
            shapes[name] = abbr
    if not shapes:
        raise SheetError("甲型檔沒有任何甲型")
    return shapes


def _num(value, label, line, integer=False):
    text = (value or "").strip().replace(",", "")
    if text == "":
        return 0
    try:
        n = float(text)
    except ValueError:
        raise SheetError(f"第 {line} 列：「{label}」不是數字：{value}")
    if n < 0:
        raise SheetError(f"第 {line} 列：「{label}」不能是負數")
    if integer and n != int(n):
        raise SheetError(f"第 {line} 列：「{label}」必須是整數")
    return int(n) if integer else n


def sku_code(style_code, shape_abbr, size):
    """與 ERPNext make_variant_item_code 相同的規則：範本編號-屬性縮寫（依屬性順序：甲型、尺寸）。"""
    return f"{style_code}-{shape_abbr}-{size}"


def read_sheet(path, shapes):
    """讀 SKU 試算表，回傳 (公司清單, 款式 dict, 規格 list)。發現任何錯誤就整份停止。"""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = [h.strip() for h in next(reader)]
        except StopIteration:
            raise SheetError("試算表是空的")
        if header[: len(FIXED_COLUMNS)] != FIXED_COLUMNS:
            raise SheetError("試算表前幾欄必須依序是：" + "、".join(FIXED_COLUMNS))
        companies = header[len(FIXED_COLUMNS):]
        if not companies or companies[0] != HQ:
            raise SheetError(f"「補貨目標」之後第一欄必須是「{HQ}」，之後是各分公司")
        if len(set(companies)) != len(companies) or any(not c for c in companies):
            raise SheetError("公司欄名稱不可空白或重複")
        styles, skus, seen = OrderedDict(), [], set()
        for line, row in enumerate(reader, start=2):
            if not any(c.strip() for c in row):
                continue
            row = row + [""] * (len(header) - len(row))
            r = dict(zip(header, (c.strip() for c in row)))
            code, name, shape, size, status = r["款式編號"], r["款式名稱"], r["甲型"], r["尺寸"], r["商品狀態"] or "上架"
            if not code or not name:
                raise SheetError(f"第 {line} 列：款式編號與款式名稱必填")
            if not code.isascii() or not code.isalnum():
                raise SheetError(f"第 {line} 列：款式編號「{code}」只能是英文字母或數字")
            if shape not in shapes:
                raise SheetError(f"第 {line} 列：甲型「{shape}」不在甲型清單中")
            if size not in SIZES:
                raise SheetError(f"第 {line} 列：尺寸「{size}」必須是 {'/'.join(SIZES)}")
            if status not in STATUSES:
                raise SheetError(f"第 {line} 列：商品狀態「{status}」必須是 {'/'.join(STATUSES)}")
            style = {
                "code": code, "name": name, "status": status,
                "cost": _num(r["成本"], "成本", line),
                "web_price": _num(r["官網售價"], "官網售價", line),
                "store_price": _num(r["實體售價"], "實體售價", line),
            }
            if code in styles:
                prev = styles[code]
                for k in ("name", "status", "cost", "web_price", "store_price"):
                    if prev[k] != style[k]:
                        raise SheetError(f"第 {line} 列：同一款式 {code} 的「{k}」與前面的列不一致（款式、狀態、成本與售價設在款式層級）")
            else:
                styles[code] = style
            sku = sku_code(code, shapes[shape], size)
            given = r["SKU 編碼"]
            if given and given != sku:
                raise SheetError(f"第 {line} 列：SKU 編碼「{given}」與規則產生的「{sku}」不同（SKU 編碼可留空，由系統產生）")
            if sku in seen:
                raise SheetError(f"第 {line} 列：規格 {sku} 重複")
            seen.add(sku)
            skus.append({
                "sku": sku, "style": code, "shape": shape, "size": size,
                "target": _num(r["補貨目標"], "補貨目標", line, integer=True),
                "stock": OrderedDict((c, _num(r[c], c, line, integer=True)) for c in companies),
            })
    if not skus:
        raise SheetError("試算表沒有任何規格")
    return companies, styles, skus


def reorder_suggestion(target, projected_by_warehouse):
    """全公司合計（客戶 Q1、Q2）：建議補貨 = max(0, 補貨目標 − Σ 各倉預計庫存)。在途倉也計入（貨仍屬公司）。"""
    total = sum(projected_by_warehouse.values())
    return total, max(0, target - total)


# ---------------- 寫入 ERPNext（需在 backend 容器內執行） ----------------

def log(msg):
    print(msg, flush=True)


class Seeder:
    def __init__(self, frappe, companies, styles, skus, shapes):
        self.frappe = frappe
        self.companies, self.styles, self.skus, self.shapes = companies, styles, skus, shapes
        self.created = 0

    def exists(self, doctype, name_or_filters):
        return self.frappe.db.exists(doctype, name_or_filters)

    def insert(self, doc, submit=False):
        d = self.frappe.get_doc(doc)
        d.insert()
        if submit:
            d.submit()
        self.created += 1
        return d

    # 1. 初次設定與語言
    def setup(self):
        frappe = self.frappe
        if not frappe.is_setup_complete():
            from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
            result = setup_complete(dict(SETUP_ARGS))
            if not frappe.is_setup_complete():
                raise RuntimeError(f"初次設定未完成：{result}")
            log("✓ 初次設定完成（公司、台灣、新台幣、台北時區）")
        ss = frappe.get_single("System Settings")
        if ss.language != "zh-TW":
            ss.language = "zh-TW"
            ss.save()
        frappe.db.set_value("User", "Administrator", "language", "zh-TW")
        from frappe.utils.scheduler import enable_scheduler, is_scheduler_disabled
        if is_scheduler_disabled():
            enable_scheduler()
            log("✓ 已開啟排程器（自動補貨需要）")
        companies = frappe.get_all("Company", fields=["name", "abbr"])
        if len(companies) != 1:
            raise RuntimeError(f"預期只有一個公司，實際 {len(companies)} 個")
        self.company, self.abbr = companies[0]["name"], companies[0]["abbr"]
        log(f"✓ 公司：{self.company}（{self.abbr}）、介面語言：繁體中文")

    def wh(self, name):
        return f"{name} - {self.abbr}"

    # 2–3. 主檔
    def masters(self):
        frappe = self.frappe
        parent = frappe.db.get_value("Warehouse", {"company": self.company, "is_group": 1, "parent_warehouse": ["in", ["", None]]}, "name")
        for name in self.companies:
            if not self.exists("Warehouse", self.wh(name)):
                self.insert({"doctype": "Warehouse", "warehouse_name": name, "company": self.company, "parent_warehouse": parent})
        if not self.exists("Warehouse", self.wh(TRANSIT)):
            self.insert({"doctype": "Warehouse", "warehouse_name": TRANSIT, "company": self.company,
                         "parent_warehouse": parent, "warehouse_type": "Transit"})
        frappe.db.set_value("Company", self.company, "default_in_transit_warehouse", self.wh(TRANSIT))
        if not self.exists("UOM", UOM):
            self.insert({"doctype": "UOM", "uom_name": UOM, "must_be_whole_number": 1})
        if not self.exists("Item Group", ITEM_GROUP):
            self.insert({"doctype": "Item Group", "item_group_name": ITEM_GROUP, "parent_item_group": "All Item Groups"})
        currency = frappe.db.get_value("Company", self.company, "default_currency")
        for pl in PRICE_LISTS:
            if not self.exists("Price List", pl):
                self.insert({"doctype": "Price List", "price_list_name": pl, "currency": currency, "selling": 1, "enabled": 1})
        for fieldname, df in (
            ("nila_status", {"label": "商品狀態", "fieldtype": "Select", "options": "\n".join(STATUSES), "default": "上架", "insert_after": "item_name", "in_list_view": 1, "in_standard_filter": 1}),
            ("nila_reorder_target", {"label": "補貨目標", "fieldtype": "Int", "insert_after": "nila_status", "description": "全公司合計的補貨目標；依款式與甲型設定"}),
        ):
            if not self.exists("Custom Field", f"Item-{fieldname}"):
                self.insert({"doctype": "Custom Field", "dt": "Item", "fieldname": fieldname, **df})
        for attr, values in (("甲型", list(self.shapes.items())), ("尺寸", [(s, s) for s in SIZES])):
            if self.exists("Item Attribute", attr):
                doc = frappe.get_doc("Item Attribute", attr)
                have = {v.attribute_value for v in doc.item_attribute_values}
                missing = [(v, a) for v, a in values if v not in have]
                if missing:
                    for v, a in missing:
                        doc.append("item_attribute_values", {"attribute_value": v, "abbr": a})
                    doc.save()
            else:
                self.insert({"doctype": "Item Attribute", "attribute_name": attr,
                             "item_attribute_values": [{"attribute_value": v, "abbr": a} for v, a in values]})
        if not self.exists("Customer", SCENARIO_CUSTOMER):
            self.insert({"doctype": "Customer", "customer_name": SCENARIO_CUSTOMER, "customer_type": "Individual",
                         "customer_group": "Individual" if self.exists("Customer Group", "Individual") else "All Customer Groups",
                         "territory": "Taiwan" if self.exists("Territory", "Taiwan") else "All Territories"})
        log("✓ 倉庫、單位、商品群組、價格表、自訂欄位、屬性、客戶")

    # 4. 款式與規格
    def items(self):
        frappe = self.frappe
        from erpnext.controllers.item_variant import create_variant
        for style in self.styles.values():
            if not self.exists("Item", style["code"]):
                self.insert({
                    "doctype": "Item", "item_code": style["code"], "item_name": style["name"],
                    "item_group": ITEM_GROUP, "stock_uom": UOM, "is_stock_item": 1, "has_variants": 1,
                    "valuation_rate": style["cost"], "nila_status": style["status"],
                    "attributes": [{"attribute": "甲型"}, {"attribute": "尺寸"}],
                })
        made = 0
        for s in self.skus:
            style = self.styles[s["style"]]
            self.prices(s["sku"], style)
            if self.exists("Item", s["sku"]):
                continue
            v = create_variant(s["style"], {"甲型": s["shape"], "尺寸": s["size"]})
            if v.item_code != s["sku"]:
                raise RuntimeError(f"ERPNext 產生的料號 {v.item_code} 與規則 {s['sku']} 不同")
            v.item_name = f"{style['name']} {s['shape']} {s['size']}"
            v.nila_status = style["status"]
            v.nila_reorder_target = s["target"]
            v.valuation_rate = style["cost"]
            v.append("barcodes", {"barcode": s["sku"]})
            v.insert()
            self.created += 1
            made += 1
            self.prices(s["sku"], style)
        log(f"✓ 款式 {len(self.styles)} 個、規格 {len(self.skus)} 個（本次新建 {made} 個；料號皆由 ERPNext 依屬性縮寫產生，與規則一致）")

    def prices(self, sku, style):
        """ERPNext 不允許在款式（範本）上設價格（實測：Item Price cannot be created for the template item），
        所以把款式的兩種售價複製到每個規格。正式版需要「改款式價格時同步到所有規格」的客製功能。"""
        if not self.exists("Item", sku):
            return
        for pl, key in (("官網售價", "web_price"), ("實體售價", "store_price")):
            if style[key] and not self.exists("Item Price", {"item_code": sku, "price_list": pl}):
                self.insert({"doctype": "Item Price", "item_code": sku, "price_list": pl, "price_list_rate": style[key]})

    # 5. 期初庫存
    def opening_stock(self):
        if self.exists("Stock Entry", {"remarks": OPENING_MARK, "docstatus": 1}):
            log("· 期初庫存已匯入過，略過")
            return
        rows = []
        for s in self.skus:
            cost = self.styles[s["style"]]["cost"]
            for company, qty in s["stock"].items():
                if qty > 0:
                    rows.append({"item_code": s["sku"], "qty": qty, "t_warehouse": self.wh(company),
                                 "uom": UOM, "conversion_factor": 1, "basic_rate": cost})
        if rows:
            self.insert({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "purpose": "Material Receipt",
                         "company": self.company, "remarks": OPENING_MARK, "items": rows}, submit=True)
        log(f"✓ 期初庫存 {len(rows)} 筆")

    # 6. 客戶例子：官網訂單 5 件
    def scenario(self):
        frappe = self.frappe
        if not any(s["sku"] == SCENARIO_SKU for s in self.skus):
            log(f"· 試算表沒有 {SCENARIO_SKU}，略過情境訂單")
            return
        if self.exists("Sales Order", {"po_no": SCENARIO_MARK, "docstatus": 1}):
            log("· 情境訂單已建立過，略過")
            return
        today = datetime.date.today()
        style = self.styles[SCENARIO_SKU.split("-")[0]]
        self.insert({
            "doctype": "Sales Order", "customer": SCENARIO_CUSTOMER, "company": self.company, "order_type": "Sales",
            "transaction_date": str(today), "delivery_date": str(today + datetime.timedelta(days=7)),
            "selling_price_list": "官網售價", "set_warehouse": self.wh(HQ), "po_no": SCENARIO_MARK,
            "items": [{"item_code": SCENARIO_SKU, "qty": SCENARIO_QTY, "rate": style["web_price"], "uom": UOM,
                       "conversion_factor": 1, "warehouse": self.wh(HQ),
                       "delivery_date": str(today + datetime.timedelta(days=7))}],
        }, submit=True)
        log(f"✓ 情境訂單：{SCENARIO_CUSTOMER} 訂 {SCENARIO_QTY} 件 {SCENARIO_SKU}（總公司出貨）")

    # 用語修正（ERPNext 繁中翻譯中仍是英文或用詞不同的地方）
    def terms(self, path):
        if not path:
            return
        made = 0
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                src, dst = (row.get("英文原文") or "").strip(), (row.get("繁體中文") or "").strip()
                if not src or not dst:
                    continue
                name = self.frappe.db.get_value("Translation", {"language": "zh-TW", "source_text": src}, "name")
                if name:
                    if self.frappe.db.get_value("Translation", name, "translated_text") != dst:
                        self.frappe.db.set_value("Translation", name, "translated_text", dst)
                else:
                    self.insert({"doctype": "Translation", "language": "zh-TW", "source_text": src, "translated_text": dst})
                    made += 1
        self.frappe.clear_cache()
        log(f"✓ 用語修正（新增 {made} 條）")

    # 7. 報告
    def report(self, sku=SCENARIO_SKU):
        frappe = self.frappe
        target = frappe.db.get_value("Item", sku, "nila_reorder_target") or 0
        bins = frappe.get_all("Bin", filters={"item_code": sku}, fields=["warehouse", "actual_qty", "reserved_qty", "ordered_qty", "projected_qty"])
        log(f"\n=== {sku} 各倉庫存 ===")
        log(f"{'倉庫':<16}{'實際':>6}{'訂單預留':>8}{'已叫貨':>6}{'預計':>6}")
        for b in sorted(bins, key=lambda b: b["warehouse"]):
            log(f"{b['warehouse']:<16}{b['actual_qty']:>6g}{b['reserved_qty']:>8g}{b['ordered_qty']:>6g}{b['projected_qty']:>6g}")
        total, need = reorder_suggestion(target, {b["warehouse"]: b["projected_qty"] for b in bins})
        log(f"全公司預計庫存 {total:g}；補貨目標 {target}；建議補貨 {need:g}")
        return total, need


def main(argv=None):
    p = argparse.ArgumentParser(description="妮菈穿戴甲 ERPNext 試用版：初始設定與範例資料")
    p.add_argument("--site", default="frontend")
    p.add_argument("--csv", required=True, help="SKU 試算表（UTF-8 CSV）")
    p.add_argument("--shapes", required=True, help="甲型與縮寫（UTF-8 CSV）")
    p.add_argument("--terms", help="用語修正（UTF-8 CSV：英文原文,繁體中文）")
    p.add_argument("--check", action="store_true", help="只檢查試算表，不寫入")
    a = p.parse_args(argv)
    try:
        shapes = read_shapes(a.shapes)
        companies, styles, skus = read_sheet(a.csv, shapes)
    except SheetError as e:
        print(f"✗ 試算表有問題，沒有寫入任何資料：{e}", file=sys.stderr)
        return 2
    log(f"試算表：{len(styles)} 款、{len(skus)} 個規格、公司 {'、'.join(companies)}")
    if a.check:
        return 0
    import frappe
    frappe.init(site=a.site, sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    seeder = Seeder(frappe, companies, styles, skus, shapes)
    try:
        seeder.setup()
        frappe.db.commit()
        seeder.masters()
        seeder.items()
        seeder.opening_stock()
        seeder.scenario()
        seeder.terms(a.terms)
        frappe.db.commit()
        seeder.report()
        log(f"\n完成（本次新增 {seeder.created} 筆資料）")
        return 0
    except Exception as e:
        frappe.db.rollback()
        print(f"✗ 失敗，本階段的變更已復原：{e}", file=sys.stderr)
        raise
    finally:
        frappe.destroy()


if __name__ == "__main__":
    sys.exit(main())
