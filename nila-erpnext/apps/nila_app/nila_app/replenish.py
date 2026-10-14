"""全公司補貨（P3）。

- 建議補貨數＝補貨目標 − 全公司預計庫存（總公司＋各分公司＋在途，已扣訂單、已加補貨單與已叫貨）。
  建立補貨單後，補貨單的數量會算進預計庫存，建議數自動變 0，不會重複叫貨。
- 建議調撥：出貨倉的庫存不夠出訂單、而其他公司有剩時，先建議調撥（例如門市調回總公司），不夠再叫貨。
- 數量改得和建議不同時要選原因，留下調整紀錄；負庫存可以標註原因。
- 補貨單：送出＝待叫貨；「已叫貨」建立採購單＝已叫貨；採購單「到貨入庫」＝已到貨。
- 每天早上自動重算，有需要補貨或調撥時通知管理者。
"""

import frappe
from frappe import _

from nila_app import stock
from nila_app.catalog import NO_REPLENISH_STATUSES
from nila_app.stockrules import group_transfers, num, replenish_qty

LEAD_DAYS = 7  # 補貨單的預計到貨日：今天＋7 天（可在補貨單上修改）


def _variants(q=None, shape=None):
    filters = {"variant_of": ["is", "set"], "disabled": 0}
    if shape:
        filters["nila_shape"] = shape
    rows = frappe.get_all("Item", filters=filters, fields=["name", "item_name", "variant_of", "nila_shape", "nila_size",
                                                          "nila_status", "nila_reorder_target"], order_by="name")
    if q:
        q = q.strip().lower()
        names = {s.name: (s.item_name or "").lower() for s in frappe.get_all("Item", filters={"has_variants": 1},
                                                                            fields=["name", "item_name"])}
        rows = [r for r in rows if q in r.variant_of.lower() or q in names.get(r.variant_of, "")]
    return rows


def suggestions(q=None, shape=None):
    """需要補貨或有負庫存的規格（依款式排序），以及建議調撥。"""
    variants = _variants(q, shape)
    bins = stock.bins([v.name for v in variants]) if variants else {}
    styles = {s.name: s.item_name for s in frappe.get_all("Item", filters={"has_variants": 1}, fields=["name", "item_name"])}
    rows = []
    for v in variants:
        by = bins.get(v.name, {})
        actual = sum(b["actual_qty"] for b in by.values())
        projected = sum(b["projected_qty"] for b in by.values())
        need = replenish_qty(v.nila_reorder_target, projected, v.nila_status)
        if not need and actual >= 0 and projected >= 0:
            continue
        rows.append({"item": v.name, "style": v.variant_of, "style_name": styles.get(v.variant_of), "shape": v.nila_shape,
                     "size": v.nila_size, "status": v.nila_status, "target": num(v.nila_reorder_target),
                     "actual": actual, "projected": projected,
                     "requested": sum(b["indented_qty"] for b in by.values()),
                     "ordered": sum(b["ordered_qty"] for b in by.values()),
                     "suggest": need, "can_order": v.nila_status not in NO_REPLENISH_STATUSES})
    reasons = stock.latest_reasons("負庫存", [r["item"] for r in rows if r["actual"] < 0 or r["projected"] < 0])
    for r in rows:
        n = reasons.get(r["item"])
        r["negative_reason"] = f"{n.reason}{'：' + n.note if n.note else ''}" if n else ""

    keep = {v.name for v in variants}
    _lines, _res, transfers = stock.allocation()
    labels = {w["name"]: w["label"] for w in stock.warehouses()}
    names = {v.name: v.item_name for v in variants}
    moves = [dict(t, suggest=t["qty"], from_label=labels.get(t["from"]), to_label=labels.get(t["to"]), item_name=names.get(t["item"]))
             for t in group_transfers(transfers) if t["item"] in keep]
    return rows, moves


@frappe.whitelist()
def get_suggestions(filters=None):
    stock.check_roles(stock.VIEW_ROLES)
    f = frappe.parse_json(filters or {}) or {}
    rows, moves = suggestions(f.get("q"), f.get("shape"))
    return {"rows": rows, "transfers": moves,
            "summary": {"items": sum(1 for r in rows if r["suggest"]), "qty": sum(r["suggest"] for r in rows),
                        "negative": sum(1 for r in rows if r["actual"] < 0 or r["projected"] < 0),
                        "transfers": len(moves)},
            "reasons": {k: stock.reasons(k) for k in stock.REASON_KINDS},
            "can_manage": frappe.session.user == "Administrator" or bool(stock.MANAGE_ROLES & set(frappe.get_roles()))}


@frappe.whitelist()
def create_material_request(rows):
    """依勾選的列建立並送出補貨單（待叫貨）。rows：[{item, qty, suggest, reason, note}]。回傳補貨單號。"""
    stock.check_roles(stock.MANAGE_ROLES)
    rows = [r for r in frappe.parse_json(rows) if num(r.get("qty")) > 0]
    if not rows:
        frappe.throw(_("沒有要叫貨的數量"))
    hq = stock.hq_warehouse()
    date = frappe.utils.add_days(frappe.utils.nowdate(), LEAD_DAYS)
    for r in rows:
        if num(r["qty"]) != num(r.get("suggest")) and not r.get("reason"):
            frappe.throw(_("{0}：叫貨數和建議不同，請選擇原因").format(r["item"]))
    mr = frappe.get_doc({
        "doctype": "Material Request", "material_request_type": "Purchase", "company": frappe.db.get_value("Warehouse", hq, "company"),
        "transaction_date": frappe.utils.nowdate(), "schedule_date": date, "set_warehouse": hq,
        "items": [{"item_code": r["item"], "qty": num(r["qty"]), "warehouse": hq, "schedule_date": date,
                   "nila_suggested_qty": num(r.get("suggest"))} for r in rows],
    })
    mr.insert()
    mr.submit()
    for r in rows:
        if num(r["qty"]) != num(r.get("suggest")):
            stock.log_reason("補貨調整", r["item"], num(r.get("suggest")), num(r["qty"]), r["reason"], r.get("note"),
                             warehouse=hq, ref=("Material Request", mr.name))
    return mr.name


@frappe.whitelist()
def create_transfers(rows):
    """依勾選的調撥建議建立在途調撥單（同一組調出、調入倉合併成一張）。全部成功才寫入。
    rows：[{item, from, to, qty, suggest, reason, note, orders}]。回傳調撥單號清單。"""
    stock.check_roles(stock.MANAGE_ROLES)
    rows = [r for r in frappe.parse_json(rows) if num(r.get("qty")) > 0]
    if not rows:
        frappe.throw(_("沒有要調撥的數量"))
    for r in rows:
        if num(r["qty"]) != num(r.get("suggest")) and not r.get("reason"):
            frappe.throw(_("{0}：調撥數和建議不同，請選擇原因").format(r["item"]))
    groups = {}
    for r in rows:
        groups.setdefault((r["from"], r["to"]), []).append(r)
    names = []
    frappe.db.savepoint("nila_transfers")
    try:
        for (src, dst), rs in groups.items():
            orders = {o for r in rs for o in (r.get("orders") or [])}
            name = stock.create_transfer(src, dst, [(r["item"], r["qty"]) for r in rs],
                                         sales_order=orders.pop() if len(orders) == 1 else None,
                                         remarks=_("調撥給訂單：{0}").format("、".join(sorted({o for r in rs for o in (r.get("orders") or [])}))))
            for r in rs:
                if num(r["qty"]) != num(r.get("suggest")):
                    stock.log_reason("調撥調整", r["item"], num(r.get("suggest")), num(r["qty"]), r["reason"], r.get("note"),
                                     warehouse=src, ref=("Stock Entry", name))
            names.append(name)
    except Exception:
        frappe.db.rollback(save_point="nila_transfers")
        raise
    return names


@frappe.whitelist()
def set_negative_reason(item, reason, note=None):
    stock.check_roles(stock.VIEW_ROLES)
    stock.log_reason("負庫存", item, None, None, reason, note)


@frappe.whitelist()
def mark_ordered(material_request, supplier=None):
    """補貨單「已叫貨」：建立並送出採購單（廠商預設為「預設廠商」，單價＝成本）。回傳採購單號。"""
    stock.check_roles(stock.MANAGE_ROLES)
    from erpnext.stock.doctype.material_request.material_request import make_purchase_order

    from nila_app.setup.install import DEFAULT_SUPPLIER

    mr = frappe.get_doc("Material Request", material_request)
    if mr.docstatus != 1 or mr.material_request_type != "Purchase" or (mr.per_ordered or 0) >= 100:
        frappe.throw(_("{0} 不是待叫貨的補貨單").format(material_request))
    po = make_purchase_order(material_request)
    po.supplier = supplier or DEFAULT_SUPPLIER
    po.schedule_date = mr.schedule_date
    costs = dict(frappe.get_all("Item", filters={"name": ["in", [d.item_code for d in po.items]]},
                                fields=["name", "nila_cost"], as_list=True))
    for d in po.items:
        d.rate = costs.get(d.item_code) or 0
        d.schedule_date = d.schedule_date or mr.schedule_date
    po.insert()
    po.submit()
    return po.name


def material_request_validate(doc, method=None):
    """停產的商品不能補貨。"""
    if doc.material_request_type != "Purchase":
        return
    codes = list({d.item_code for d in doc.items if d.item_code})
    blocked = frappe.get_all("Item", filters={"name": ["in", codes or [""]], "nila_status": ["in", list(NO_REPLENISH_STATUSES)]},
                             pluck="name")
    if blocked:
        frappe.throw(_("以下商品已停產，不能補貨：{0}").format("、".join(sorted(blocked))), title=_("商品不能補貨"))


def daily():
    """每天自動：重算訂單出貨狀態；有需要補貨或調撥時，通知庫存管理者。"""
    from nila_app import dispatch

    dispatch.refresh_all()
    rows, moves = suggestions()
    need = [r for r in rows if r["suggest"]]
    if not need and not moves:
        return
    subject = _("今天有 {0} 個規格建議補貨（共 {1} 件），{2} 筆建議調撥").format(len(need), sum(r["suggest"] for r in need), len(moves))
    # Administrator 不會有角色紀錄，但它是（可能唯一的）最高權限使用者，一定要通知
    users = {"Administrator"} | set(frappe.get_all("Has Role", filters={
        "role": ["in", ["System Manager", "Stock Manager", "Purchase Manager"]], "parenttype": "User"}, pluck="parent"))
    enabled = set(frappe.get_all("User", filters={"name": ["in", list(users) or [""]], "enabled": 1}, pluck="name"))
    for u in sorted(enabled):
        frappe.get_doc({"doctype": "Notification Log", "subject": subject, "for_user": u, "type": "Alert",
                        "link": "/app/nila-replenish"}).insert(ignore_permissions=True)
