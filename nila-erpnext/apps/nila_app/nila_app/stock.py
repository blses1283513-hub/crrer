"""共用的庫存查詢與動作：庫存表（P2）、補貨（P3）、訂單調度（P4）都用這裡。

- 查詢：甲型、尺寸、倉庫順序；每個規格在每個倉庫的庫存（一次查完）；在途數量；未出貨的訂單明細。
- 分配：把庫存依先後分配給訂單（規則在 stockrules.py）。
- 動作：建立在途調撥單（調出倉 → 在途 → 調入倉）、到貨入庫、記錄調整原因。
"""

import frappe
from frappe import _

from nila_app import products as p
from nila_app.setup.config import TRANSIT, load_config
from nila_app.stockrules import allocate, num

VIEW_ROLES = {"System Manager", "Stock Manager", "Stock User", "Item Manager", "Sales Manager", "Sales User",
              "Purchase Manager", "Purchase User"}
MANAGE_ROLES = {"System Manager", "Stock Manager", "Purchase Manager"}
REASON_KINDS = ["補貨調整", "負庫存", "調撥調整"]


def check_roles(roles):
    if frappe.session.user != "Administrator" and not roles & set(frappe.get_roles()):
        frappe.throw(_("沒有權限"), frappe.PermissionError)


# ---------- 基本資料 ----------

def shapes():
    """{甲型名稱: 縮寫}，依設定的順序。"""
    return {v.attribute_value: v.abbr for v in frappe.get_all(
        "Item Attribute Value", filters={"parent": p.SHAPE_ATTR}, fields=["attribute_value", "abbr"], order_by="idx")}


def sizes():
    return p._attribute_values(p.SIZE_ATTR)


def warehouses(include_transit=True):
    """使用中的倉庫，依「總公司、分公司（設定檔順序）、其他、在途」排列。
    每個 {"name": 倉庫代碼, "label": 名稱, "transit": 是否在途倉, "hq": 是否總公司}。"""
    rows = frappe.get_all("Warehouse", filters={"is_group": 0, "disabled": 0},
                          fields=["name", "warehouse_name", "warehouse_type"], order_by="creation")
    cfg = load_config(frappe.local.sites_path) or {}
    rank = {n: i for i, n in enumerate([cfg.get("hq"), *cfg.get("branches", [])]) if n}
    hq = cfg.get("hq")
    out = []
    for w in rows:
        transit = w.warehouse_type == "Transit"
        if transit and (w.warehouse_name != TRANSIT or not include_transit):
            continue
        out.append({"name": w.name, "label": w.warehouse_name, "transit": transit, "hq": w.warehouse_name == hq})
    out.sort(key=lambda w: (w["transit"], rank.get(w["label"], len(rank))))
    return out


def transit_warehouse():
    return next((w["name"] for w in warehouses() if w["transit"]), None)


def hq_warehouse():
    whs = warehouses(include_transit=False)
    return next((w["name"] for w in whs if w["hq"]), whs[0]["name"] if whs else None)


# ---------- 庫存查詢 ----------

BIN_FIELDS = ["actual_qty", "projected_qty", "reserved_qty", "ordered_qty", "indented_qty"]


def bins(items=None, whs=None):
    """{料號: {倉庫: {實際、預計、預留、已叫貨、補貨單}}}。items 為 None 表示全部。"""
    filters = {"warehouse": ["in", whs or [w["name"] for w in warehouses()]]}
    if items is not None:
        if not items:
            return {}
        filters["item_code"] = ["in", list(items)]
    out = {}
    for b in frappe.get_all("Bin", filters=filters, fields=["item_code", "warehouse", *BIN_FIELDS]):
        out.setdefault(b.item_code, {})[b.warehouse] = {f: num(b.get(f)) for f in BIN_FIELDS}
    return out


def transit_inbound(items=None):
    """{(料號, 目的倉庫): 在途、還沒入庫的數量}（由本系統建立、有記錄目的倉庫的調撥單）。"""
    cond, args = "", {}
    if items is not None:
        if not items:
            return {}
        cond, args = "and d.item_code in %(items)s", {"items": tuple(items)}
    rows = frappe.db.sql(f"""
        select d.item_code, se.nila_destination, sum(d.transfer_qty - ifnull(d.transferred_qty, 0)) qty
        from `tabStock Entry Detail` d join `tabStock Entry` se on se.name = d.parent
        where se.docstatus = 1 and se.add_to_transit = 1 and ifnull(se.nila_destination, '') != ''
          and ifnull(se.per_transferred, 0) < 100 {cond}
        group by d.item_code, se.nila_destination""", args, as_dict=True)
    return {(r.item_code, r.nila_destination): num(r.qty) for r in rows if r.qty > 0}


def open_order_lines(items=None, orders=None):
    """未出貨的訂單明細，依先後（訂單日期、建立時間、行號）排序。qty＝還沒出貨的數量（庫存單位）。"""
    cond, args = [], {}
    if items is not None:
        cond.append("i.item_code in %(items)s")
        args["items"] = tuple(items) or ("",)
    if orders is not None:
        cond.append("o.name in %(orders)s")
        args["orders"] = tuple(orders) or ("",)
    where = (" and " + " and ".join(cond)) if cond else ""
    rows = frappe.db.sql(f"""
        select i.name `key`, o.name `order`, i.item_code item, i.warehouse,
               (i.qty - ifnull(i.delivered_qty, 0)) * ifnull(nullif(i.conversion_factor, 0), 1) qty
        from `tabSales Order Item` i join `tabSales Order` o on o.name = i.parent
        where o.docstatus = 1 and o.status not in ('Closed', 'Completed', 'On Hold')
          and i.qty > ifnull(i.delivered_qty, 0) and ifnull(i.warehouse, '') != '' {where}
        order by o.transaction_date, o.creation, i.idx""", args, as_dict=True)
    return [dict(r, qty=num(r.qty)) for r in rows]


def allocation(items=None, extra_lines=()):
    """把這些規格的庫存依先後分配給全部未出貨的訂單明細（extra_lines：還沒送出的訂單，排在最後）。
    items 為 None：全部有未出貨訂單的規格。"""
    if items is None:
        lines = open_order_lines() + list(extra_lines)
        items = list({ln["item"] for ln in lines})
    else:
        items = list(set(items))
        lines = open_order_lines(items=items) + list(extra_lines)
    stock = bins(items)
    sources = [w["name"] for w in warehouses(include_transit=False)]
    actual = {(i, w): v["actual_qty"] for i, by in stock.items() for w, v in by.items() if w in sources}
    incoming = {(i, w): v["ordered_qty"] for i, by in stock.items() for w, v in by.items() if v["ordered_qty"]}
    results, transfers = allocate(lines, actual, transit_inbound(items), incoming, sources)
    return lines, results, transfers


# ---------- 調撥 ----------

def _check_transfer_warehouses(from_wh, to_wh):
    usable = {w["name"] for w in warehouses(include_transit=False)}
    if from_wh not in usable or to_wh not in usable:
        frappe.throw(_("調出、調入倉庫必須是使用中的總公司或分公司"))
    if from_wh == to_wh:
        frappe.throw(_("調出與調入倉庫不能相同"))


def create_transfer(from_wh, to_wh, items, sales_order=None, remarks=None):
    """建立並送出在途調撥單：調出倉的庫存立即轉到在途倉，調入倉「到貨入庫」後才增加。
    items：[(料號, 數量)]。回傳調撥單號。"""
    _check_transfer_warehouses(from_wh, to_wh)
    transit = transit_warehouse()
    if not transit:
        frappe.throw(_("找不到在途倉"))
    rows = [(code, num(qty)) for code, qty in items if num(qty) > 0]
    if not rows:
        frappe.throw(_("沒有要調撥的數量"))
    se = frappe.get_doc({
        "doctype": "Stock Entry", "stock_entry_type": "Material Transfer", "purpose": "Material Transfer",
        "company": frappe.db.get_value("Warehouse", from_wh, "company"), "add_to_transit": 1,
        "from_warehouse": from_wh, "to_warehouse": transit, "nila_destination": to_wh,
        "nila_sales_order": sales_order, "remarks": remarks,
        "items": [{"item_code": code, "qty": qty, "s_warehouse": from_wh, "t_warehouse": transit,
                   "allow_zero_valuation_rate": 1} for code, qty in rows],
    })
    se.insert()
    se.submit()
    return se.name


@frappe.whitelist()
def receive_transfer(name):
    """在途調撥單到貨：建立並送出入庫單，把在途數量全部轉入調入倉。回傳入庫單號。"""
    check_roles(VIEW_ROLES)
    from erpnext.stock.doctype.stock_entry.stock_entry import make_stock_in_entry

    out = frappe.get_doc("Stock Entry", name)
    if out.docstatus != 1 or not out.add_to_transit or not out.nila_destination:
        frappe.throw(_("{0} 不是在途中的調撥單").format(name))
    if (out.per_transferred or 0) >= 100:
        frappe.throw(_("{0} 已經全部入庫").format(name))
    doc = make_stock_in_entry(name)
    for d in doc.items:
        d.t_warehouse = out.nila_destination
    doc.to_warehouse = out.nila_destination
    doc.nila_sales_order = out.nila_sales_order
    doc.insert()
    doc.submit()
    return doc.name


# ---------- 調整原因 ----------

@frappe.whitelist()
def reasons(kind):
    """某一類可選的原因（「原因選項」可自行新增、停用）。"""
    check_roles(VIEW_ROLES)
    return frappe.get_all("Nila Reason", filters={"kind": kind, "disabled": 0}, pluck="reason", order_by="idx, creation")


def log_reason(kind, item_code, before, after, reason, note=None, warehouse=None, ref=None):
    """記錄一次調整：誰、何時、哪個規格、原本建議多少、改成多少、原因。"""
    if not reason:
        frappe.throw(_("{0}：數量和建議不同，請選擇原因").format(item_code))
    frappe.get_doc({
        "doctype": "Nila Reason Log", "kind": kind, "item_code": item_code, "warehouse": warehouse,
        "before_qty": before, "after_qty": after, "reason": reason, "note": note,
        "reference_doctype": ref[0] if ref else None, "reference_name": ref[1] if ref else None,
    }).insert(ignore_permissions=True)


def latest_reasons(kind, items):
    """{料號: 最新一筆原因}（例如負庫存原因）。"""
    out = {}
    if not items:
        return out
    for r in frappe.get_all("Nila Reason Log", filters={"kind": kind, "item_code": ["in", list(items)]},
                            fields=["item_code", "reason", "note", "owner", "creation"], order_by="creation desc"):
        out.setdefault(r.item_code, r)
    return out
