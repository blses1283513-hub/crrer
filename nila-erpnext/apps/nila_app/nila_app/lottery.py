"""抽獎（P6）：依活動的條件算出符合資格的會員與名額；預覽、產生名單快照、匯出 Excel。系統只判斷資格，不抽籤（Q10）。

消費的計算和消費報表相同（salesreport.consumption）：門市銷售扣退貨、退款，官網訂單不算。
"""

import frappe
from frappe import _

from nila_app import lotteryrules as T
from nila_app import perms, retail, salesreport
from nila_app.stockrules import num


def _stats(doc, rules):
    """期間內每位會員的消費統計；條件用到時才查單筆最高金額、買過的款式與甲型。"""
    stores = [s.warehouse for s in doc.stores] or [w["name"] for w in perms.allowed_stores()]
    members = {c.name: c for c in frappe.get_all("Customer", filters={"customer_group": retail.MEMBER_GROUP, "disabled": 0},
                                                  fields=["name", "customer_name", "nila_phone"])}
    data = salesreport.consumption(str(doc.from_date), str(doc.to_date), stores, list(members), by="customer")
    stats = {c: dict(v, styles=set(), shapes=set(), max_single=0) for c, v in data.items()}
    keys = {k for k, _v in rules}
    args = {"from": str(doc.from_date), "to": str(doc.to_date), "stores": tuple(stores) or ("",),
            "customers": tuple(stats) or ("",), "channel": retail.STORE_CHANNEL}
    base = """from `tabSales Invoice` s where s.docstatus = 1 and s.is_return = 0 and s.nila_channel = %(channel)s
              and s.posting_date between %(from)s and %(to)s and s.set_warehouse in %(stores)s and s.customer in %(customers)s"""
    # 單筆最高金額：扣掉該筆後來的退貨、退款
    for r in frappe.db.sql(f"""select s.customer, max(s.grand_total + coalesce((select sum(x.grand_total) from `tabSales Invoice` x
                                   where x.docstatus = 1 and x.is_return = 1 and x.return_against = s.name), 0)) m
                               {base} group by s.customer""", args, as_dict=True):
        stats[r.customer]["max_single"] = num(r.m)
    if keys & {"styles", "shapes"}:
        for r in frappe.db.sql(f"""select distinct s.customer, it.variant_of, it.nila_shape
                from `tabSales Invoice Item` i join `tabSales Invoice` s on s.name = i.parent
                join `tabItem` it on it.name = i.item_code
                where s.docstatus = 1 and s.is_return = 0 and s.nila_channel = %(channel)s
                  and s.posting_date between %(from)s and %(to)s and s.set_warehouse in %(stores)s and s.customer in %(customers)s""",
                               args, as_dict=True):
            if r.variant_of:
                stats[r.customer]["styles"].add(r.variant_of)
            if r.nila_shape:
                stats[r.customer]["shapes"].add(r.nila_shape)
    return stats, members


def evaluate(name):
    perms.require("lottery")
    doc = frappe.get_doc("Nila Lottery", name)
    try:
        rules, mode, unit, cap = T.clean_rules([r.as_dict() for r in doc.rules], doc.entry_mode, doc.entry_unit, doc.entry_cap)
    except T.LotteryError as e:
        frappe.throw(str(e), title=_("條件有誤"))
    stats, members = _stats(doc, rules)
    rows = T.evaluate(stats, rules, mode, unit, cap)
    for r in rows:
        m = members.get(r["customer"])
        r["customer_name"], r["phone"] = (m.customer_name, m.nila_phone) if m else ("", "")
    stores = [frappe.db.get_value("Warehouse", s.warehouse, "warehouse_name") for s in doc.stores]
    text = (f"期間：{doc.from_date} 至 {doc.to_date}。門市：{'、'.join(stores) or '全部'}。"
            + T.describe(rules, mode, unit, cap) + "（只計門市銷售、已扣退貨退款，官網訂單不算）")
    return doc, rows, text


@frappe.whitelist()
def preview(name):
    _doc, rows, text = evaluate(name)
    return {"count": len(rows), "entries": sum(r["entries"] for r in rows), "rows": rows[:200], "more": max(0, len(rows) - 200),
            "description": text}


@frappe.whitelist()
def generate(name):
    """產生名單快照（之後不會因退貨或改條件而變動）。回傳快照代碼。"""
    doc, rows, text = evaluate(name)
    snap = frappe.get_doc({
        "doctype": "Nila Lottery Snapshot", "lottery": doc.name, "generated_on": frappe.utils.now(),
        "member_count": len(rows), "entry_total": sum(r["entries"] for r in rows), "rules_text": text,
        "entries": [{"customer": r["customer"], "customer_name": r["customer_name"], "phone": r["phone"], "orders": r["orders"],
                     "net": r["net"], "max_single": r["max_single"], "entries": r["entries"]} for r in rows],
    })
    snap.insert(ignore_permissions=True)
    return snap.name


@frappe.whitelist()
def export_snapshot(name):
    perms.require("lottery")
    snap = frappe.get_doc("Nila Lottery Snapshot", name)
    title = frappe.db.get_value("Nila Lottery", snap.lottery, "title")
    rows = [[_("活動"), title], [_("產生時間"), str(snap.generated_on)], [_("條件"), snap.rules_text], [],
            [_("會員"), _("姓名"), _("手機"), _("消費次數"), _("消費淨額"), _("單筆最高"), _("名額")]]
    rows += [[e.customer, e.customer_name, e.phone, e.orders, e.net, e.max_single, e.entries] for e in snap.entries]
    from frappe.utils.xlsxutils import build_xlsx_response

    build_xlsx_response(rows, f"nila-lottery-{snap.name}")
