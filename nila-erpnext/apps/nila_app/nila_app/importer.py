"""商品試算表的匯入、匯出與範本下載。

匯入分兩步：
1. 預覽（preview）：讀取上傳的 Excel／CSV，列出會新增、更新的數量與每一列的錯誤，不寫入任何資料。
2. 匯入（start_import）：在背景執行；全部成功才寫入，任何一筆失敗就全部取消。
"""

import os

import frappe
from frappe import _

from nila_app import products as p
from nila_app import stock
from nila_app.catalog import next_style_code
from nila_app.sheet import export_rows, headers, parse_csv, plan_import

STATE_KEY = "nila_import_state"
STOCK_ROWS_PER_ENTRY = 100  # ERPNext 超過 100 列會改在背景另外過帳，就無法「全部成功才寫入」
# 全部成功才寫入＝整個匯入是一筆交易。ERPNext 預設一筆交易最多 20 萬次寫入，
# 第一次匯入全部商品（約 5,000 個規格＋各公司期初庫存）會超過，所以匯入工作中放寬
MAX_WRITES = 5_000_000
ALLOWED_ROLES = {"System Manager", "Item Manager", "Stock Manager"}


def _check_role():
    if frappe.session.user != "Administrator" and not ALLOWED_ROLES & set(frappe.get_roles()):
        frappe.throw(_("沒有權限匯入或匯出商品"), frappe.PermissionError)


def _context():
    """甲型 {名稱: 縮寫}、尺寸、各公司倉庫 {欄名: 倉庫}（依設定檔的順序）。"""
    return stock.shapes(), stock.sizes(), {w["label"]: w["name"] for w in stock.warehouses(include_transit=False)}


def _existing():
    styles = {}
    for t in frappe.get_all("Item", filters={"has_variants": 1},
                            fields=["name", "item_name", *p.STYLE_FIELDS]):
        styles[t.name] = {"name": t.item_name, "status": t.nila_status, "cost": t.nila_cost,
                          "web_price": t.nila_web_price, "store_price": t.nila_store_price, "variants": {}}
    for v in frappe.get_all("Item", filters={"variant_of": ["is", "set"]},
                            fields=["name", "variant_of", "nila_shape", "nila_size", "nila_reorder_target"]):
        if v.variant_of in styles:
            styles[v.variant_of]["variants"][(v.nila_shape, v.nila_size)] = {"code": v.name, "target": v.nila_reorder_target}
    codes = frappe.get_all("Item", filters={"has_variants": 0}, pluck="name")
    return {"styles": styles, "codes": codes}


def _read_table(file_url):
    f = frappe.get_doc("File", {"file_url": file_url})
    ext = os.path.splitext(f.file_name or file_url)[1].lower()
    if ext == ".xlsx":
        from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

        return read_xlsx_file_from_attached_file(file_url=file_url)
    if ext == ".csv":
        try:
            # 讀原始位元組：ERPNext 的 get_content() 會先用西歐編碼解碼，Big5 的中文會變成亂碼
            with open(f.get_full_path(), "rb") as fh:
                return parse_csv(fh.read())
        except ValueError as e:
            frappe.throw(str(e))
    frappe.throw(_("只能匯入 Excel（.xlsx）或 CSV 檔"))


def _plan(file_url):
    shapes, sizes, whs = _context()
    return plan_import(_read_table(file_url), shapes, sizes, list(whs), _existing()), whs


@frappe.whitelist()
def preview(file_url):
    _check_role()
    plan, _whs = _plan(file_url)
    changes = []
    for s in plan["styles"]:
        news = [f"{v['shape']} {v['size']}" for v in s["variants"] if v["is_new"]]
        upd = [v["code"] for v in s["variants"] if not v["is_new"] and v["changed"]]
        if s["is_new"] or s["changed"] or news or upd:
            changes.append({"code": s["code"] or _("（自動編號）"), "name": s["name"],
                            "action": _("新增款式") if s["is_new"] else (_("更新款式") if s["changed"] else _("不變")),
                            "new_variants": len(news), "updated_variants": len(upd),
                            "stock": sum(sum(v["stock"].values()) for v in s["variants"])})
    return {"errors": plan["errors"], "warnings": plan["warnings"], "counts": plan["counts"],
            "changes": changes[:300], "more": max(0, len(changes) - 300)}


@frappe.whitelist()
def start_import(file_url):
    _check_role()
    state = frappe.cache.get_value(STATE_KEY) or {}
    busy = state.get("state") in ("queued", "running")
    if busy and frappe.utils.time_diff_in_hours(frappe.utils.now(), state.get("time")) < 4:
        frappe.throw(_("{0} 的匯入還在進行中，請等它完成").format(state.get("user")))
    _set_state("queued", _("排隊中…"))
    frappe.enqueue("nila_app.importer.run_import", queue="long", timeout=4 * 3600, file_url=file_url,
                   user=frappe.session.user, enqueue_after_commit=True)
    return import_status()


@frappe.whitelist()
def import_status():
    _check_role()
    return frappe.cache.get_value(STATE_KEY) or {}


def _set_state(state, message, **extra):
    frappe.cache.set_value(STATE_KEY, {"state": state, "message": message, "user": frappe.session.user,
                                       "time": frappe.utils.now(), **extra}, expires_in_sec=7 * 24 * 3600)


def run_import(file_url, user):
    """背景工作：全部成功才寫入。"""
    frappe.set_user(user)
    limit = frappe.db.MAX_WRITES_PER_TRANSACTION
    frappe.db.MAX_WRITES_PER_TRANSACTION = max(limit, MAX_WRITES)
    frappe.db.savepoint("nila_import")
    try:
        _set_state("running", _("檢查資料…"))
        plan, whs = _plan(file_url)
        if plan["errors"]:
            raise frappe.ValidationError(_("資料有誤，沒有匯入任何資料：") + "；".join(plan["errors"][:20]))
        summary = _apply(plan, whs)
        frappe.db.commit()
        _set_state("done", _("匯入完成"), counts=plan["counts"], summary=summary, warnings=plan["warnings"])
    except Exception as e:
        frappe.db.rollback(save_point="nila_import")
        frappe.log_error(title="妮菈商品匯入失敗")
        _set_state("failed", _("匯入失敗，沒有寫入任何資料：{0}").format(frappe.utils.strip_html(str(e))[:2000]))
    finally:
        frappe.db.MAX_WRITES_PER_TRANSACTION = limit


def _apply(plan, whs):
    from erpnext.controllers.item_variant import create_variant

    total = sum(len(s["variants"]) for s in plan["styles"]) or 1
    done, created_codes = 0, []
    used = set(_existing()["styles"]) | set(frappe.get_all("Item", pluck="name"))
    stock = {}  # 倉庫 -> [(料號, 數量, 成本)]
    for s in plan["styles"]:
        code = s["code"]
        if s["is_new"]:
            if not code:
                code = p.suggest_code()
                while code in used:
                    code = next_style_code([code])
            used.add(code)
            frappe.get_doc({
                "doctype": "Item", "item_code": code, "item_name": s["name"], "item_group": p.ITEM_GROUP,
                "stock_uom": p.UOM, "is_stock_item": 1, "include_item_in_manufacturing": 0,
                "has_variants": 1, "variant_based_on": "Item Attribute",
                "attributes": [{"attribute": p.SHAPE_ATTR}, {"attribute": p.SIZE_ATTR}],
                "nila_status": s["status"], "nila_cost": s["cost"],
                "nila_web_price": s["web_price"], "nila_store_price": s["store_price"],
            }).insert()
            created_codes.append(code)
        elif s["changed"]:
            t = frappe.get_doc("Item", code)
            t.update({"item_name": s["name"], "nila_status": s["status"], "nila_cost": s["cost"],
                      "nila_web_price": s["web_price"], "nila_store_price": s["store_price"]})
            t.save()
        for v in s["variants"]:
            if v["is_new"]:
                doc = create_variant(code, {p.SHAPE_ATTR: v["shape"], p.SIZE_ATTR: v["size"]})
                doc.nila_reorder_target = v["target"]
                doc.insert()
                for col, qty in v["stock"].items():
                    stock.setdefault(whs[col], []).append((doc.name, qty, s["cost"] or 0))
            elif v["changed"]:
                d = frappe.get_doc("Item", v["code"])
                d.nila_reorder_target = v["target"]
                d.save()
            done += 1
            if done % 50 == 0:
                _set_state("running", _("商品 {0}/{1}").format(done, total), progress=round(done / total * 80))
    entries = _opening_stock(stock)
    return {"styles": created_codes[:50], "stock_entries": entries}


def _opening_stock(stock):
    """新規格的期初庫存：每個倉庫一張或多張「期初庫存」盤點單（每張最多 100 列）。"""
    if not stock:
        return []
    from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_difference_account

    company = frappe.db.get_value("Warehouse", next(iter(stock)), "company")
    account = get_difference_account("Opening Stock", company)
    chunks = [(wh, rows[i:i + STOCK_ROWS_PER_ENTRY]) for wh, rows in stock.items()
              for i in range(0, len(rows), STOCK_ROWS_PER_ENTRY)]
    names = []
    for n, (wh, rows) in enumerate(chunks, start=1):
        sr = frappe.get_doc({
            "doctype": "Stock Reconciliation", "purpose": "Opening Stock", "company": company,
            "expense_account": account, "set_warehouse": wh,
            "items": [{"item_code": code, "warehouse": wh, "qty": qty, "valuation_rate": rate,
                       "allow_zero_valuation_rate": 0 if rate else 1} for code, qty, rate in rows],
        })
        sr.insert()
        sr.submit()
        names.append(sr.name)
        _set_state("running", _("期初庫存 {0}/{1}").format(n, len(chunks)), progress=80 + round(n / len(chunks) * 20))
    return names


@frappe.whitelist()
def download_template():
    _check_role()
    _shapes, _sizes, whs = _context()
    from frappe.utils.xlsxutils import build_xlsx_response

    build_xlsx_response([headers(list(whs))], "nila-import-template")  # 英文檔名：中文檔名在部分瀏覽器會變成「download」


@frappe.whitelist()
def export_items():
    """匯出全部規格（與匯入同格式），含目前各公司的實際庫存。"""
    _check_role()
    shapes, sizes, whs = _context()
    ex = _existing()["styles"]
    col_of = {wh: col for col, wh in whs.items()}
    stock = {}
    for b in frappe.get_all("Bin", filters={"warehouse": ["in", list(whs.values())]},
                            fields=["item_code", "warehouse", "actual_qty"]):
        if b.actual_qty:
            stock.setdefault(b.item_code, {})[col_of[b.warehouse]] = b.actual_qty
    from frappe.utils.xlsxutils import build_xlsx_response

    build_xlsx_response(export_rows(ex, list(shapes), sizes, list(whs), stock),
                        f"nila-items-{frappe.utils.nowdate()}")
