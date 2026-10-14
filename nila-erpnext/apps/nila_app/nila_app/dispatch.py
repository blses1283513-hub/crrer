"""訂單調度（P4）。

- 出貨倉：預設總公司，可改成任何一家分公司（整張訂單或每一行），不能選在途倉。
- 出貨狀態：依先後把各倉庫存分配給未出貨的訂單（規則在 stockrules.allocate）：
  可出貨（出貨倉現貨足夠）、待調撥（要從其他公司調或已在途）、已叫貨（等採購到貨）、待叫貨（全公司都不夠）、已出貨。
- 入庫、調撥、出貨、門市銷售、盤點、採購單、訂單送出／修改／取消後，相關訂單的狀態自動重算；每天早上再全部重算一次。
- 訂單畫面顯示每一行在各倉庫的庫存與分配結果；缺貨時可一鍵建立在途調撥單。
"""

import frappe
from frappe import _

from nila_app import stock
from nila_app.stockrules import DELIVERED, num, order_status


# ---------- 出貨狀態 ----------

def refresh_orders(orders):
    """重算這些訂單的出貨狀態（同時重算同規格的其他訂單，因為先後順序會互相影響）。"""
    orders = list(set(orders))
    if not orders:
        return
    items = {ln["item"] for ln in stock.open_order_lines(orders=orders)}
    if items:
        _refresh(orders, items)
    else:
        _write(orders, [], {})  # 已全部出貨、關閉或取消


def refresh_items(items):
    """庫存變動後：重算所有含這些規格的未出貨訂單。"""
    items = list(set(i for i in items if i))
    if not items:
        return
    orders = {ln["order"] for ln in stock.open_order_lines(items=items)}
    if orders:
        _refresh(orders, items)


def refresh_all():
    orders = frappe.get_all("Sales Order", filters={"docstatus": 1, "status": ["not in", ["Closed", "Completed"]]}, pluck="name")
    lines, res, _tr = stock.allocation()
    _write(orders, lines, res)


def _refresh(orders, items):
    lines, res, _tr = stock.allocation(items)
    # 這些訂單其他規格的分配也要算進來，訂單狀態才完整
    other = {ln["item"] for ln in stock.open_order_lines(orders=list(orders))} - set(items)
    if other:
        more_lines, more_res, _ = stock.allocation(other)
        lines += more_lines
        res.update(more_res)
    _write(orders, lines, res)


def _write(orders, lines, res):
    by_order = {}
    for ln in lines:
        by_order.setdefault(ln["order"], []).append(res[ln["key"]])
    info = {o.name: o for o in frappe.get_all("Sales Order", filters={"name": ["in", list(orders) or [""]]},
                                               fields=["name", "docstatus", "status", "per_delivered", "nila_dispatch_status"])}
    for name in orders:
        o = info.get(name)
        if not o:
            continue
        if o.docstatus != 1 or o.status == "Closed":
            new = ""
        elif (o.per_delivered or 0) >= 100 or o.status == "Completed":
            new = DELIVERED
        elif name in by_order:
            new = order_status(by_order[name])
        else:
            new = ""  # 沒有需要出庫存的明細
        if (o.nila_dispatch_status or "") != new:
            frappe.db.set_value("Sales Order", name, "nila_dispatch_status", new, update_modified=False)


# ---------- 單據事件 ----------

def sales_order_validate(doc, method=None):
    """出貨倉可以是總公司或任何分公司，但不能是在途倉或停用的倉庫。"""
    usable = {w["name"] for w in stock.warehouses(include_transit=False)}
    bad = sorted({d.warehouse for d in doc.items if d.warehouse and d.warehouse not in usable})
    if doc.set_warehouse and doc.set_warehouse not in usable:
        bad = sorted(set(bad) | {doc.set_warehouse})
    if bad:
        frappe.throw(_("出貨倉必須是總公司或分公司：{0}").format("、".join(bad)), title=_("出貨倉不正確"))


def sales_order_changed(doc, method=None):
    refresh_items([d.item_code for d in doc.items])
    refresh_orders([doc.name])


def sales_order_cancelled(doc, method=None):
    # 調撥單上的「相關訂單」只是參考，不擋取消（取消後提醒調撥單仍在途）
    doc.ignore_linked_doctypes = (*(doc.get("ignore_linked_doctypes") or ()), "Stock Entry")
    frappe.db.set_value("Sales Order", doc.name, "nila_dispatch_status", "", update_modified=False)
    refresh_items([d.item_code for d in doc.items])
    moving = frappe.get_all("Stock Entry", filters={"nila_sales_order": doc.name, "docstatus": 1, "add_to_transit": 1,
                                                    "per_transferred": ["<", 100]}, fields=["name", "nila_destination"])
    if moving:
        frappe.msgprint(_("這張訂單有還在途中的調撥單：{0}。到貨後貨會留在調入倉庫，可以用在其他訂單；不需要的話可以取消調撥單。").format(
            "、".join(f"{m.name}（→ {m.nila_destination}）" for m in moving)), title=_("提醒：調撥單仍在途"), indicator="orange")


def stock_changed(doc, method=None):
    """入庫、出貨、調撥、門市銷售、盤點、採購單送出或取消後，重算相關訂單。"""
    rows = doc.get("items") or []
    refresh_items([d.item_code for d in rows])
    # 出貨（出貨單、含出貨的銷售發票）：全部出完的訂單已不在未出貨清單，要另外更新成「已出貨」
    refresh_orders({d.get("against_sales_order") or d.get("sales_order") for d in rows} - {None, ""})


# ---------- 訂單畫面 ----------

@frappe.whitelist()
def order_panel(doc):
    """訂單畫面：每一行在各倉庫的庫存、分配結果（現貨、在途、調撥、已叫貨、還缺），以及調撥建議。
    尚未送出的訂單排在所有已送出訂單之後計算。"""
    stock.check_roles(stock.VIEW_ROLES)
    doc = frappe._dict(frappe.parse_json(doc))
    items = [frappe._dict(d) for d in (doc.get("items") or []) if d.get("item_code")]
    submitted = doc.get("docstatus") == 1 and doc.get("name") and not doc.get("__islocal")
    extra = []
    if not submitted and doc.get("docstatus", 0) == 0:
        for d in items:
            qty = (num(d.qty) - num(d.get("delivered_qty"))) * (num(d.get("conversion_factor")) or 1)
            if d.get("warehouse") and qty > 0:
                extra.append({"key": f"new-{d.idx}", "order": None, "item": d.item_code, "warehouse": d.warehouse, "qty": num(qty)})
    codes = list({d.item_code for d in items})
    lines, res, transfers = stock.allocation(codes, extra_lines=extra) if codes else ([], {}, [])
    whs = stock.warehouses()
    bins = stock.bins(codes) if codes else {}
    names = dict(frappe.get_all("Item", filters={"name": ["in", codes or [""]]}, fields=["name", "item_name"], as_list=True))
    out = []
    for d in items:
        key = d.get("name") if submitted else f"new-{d.idx}"
        r = res.get(key)
        out.append({"idx": d.idx, "item": d.item_code, "item_name": names.get(d.item_code), "warehouse": d.get("warehouse"),
                    "qty": num(d.qty), "delivered": num(d.get("delivered_qty")),
                    "stock": {w["name"]: bins.get(d.item_code, {}).get(w["name"], {}).get("actual_qty", 0) for w in whs},
                    "result": r})
    mine = [t for t in transfers if (t["order"] == doc.get("name") if submitted else t["order"] is None)]
    from nila_app.stockrules import group_transfers

    labels = {w["name"]: w["label"] for w in whs}
    moves = [dict(t, suggest=t["qty"], from_label=labels.get(t["from"]), to_label=labels.get(t["to"]), item_name=names.get(t["item"]),
                  orders=[doc.get("name")] if submitted else []) for t in group_transfers(mine)]
    results = [r["result"] for r in out if r["result"]]
    moving = frappe.get_all("Stock Entry", filters={"nila_sales_order": doc.get("name") or "", "docstatus": 1,
                                                    "add_to_transit": 1, "per_transferred": ["<", 100]},
                            fields=["name", "nila_destination"]) if submitted else []
    return {"warehouses": [{"name": w["name"], "label": w["label"], "transit": w["transit"]} for w in whs],
            "lines": out, "status": order_status(results) if results else "", "transfers": moves, "moving": moving,
            "reasons": stock.reasons("調撥調整"),
            "can_manage": frappe.session.user == "Administrator" or bool(stock.MANAGE_ROLES & set(frappe.get_roles()))}
