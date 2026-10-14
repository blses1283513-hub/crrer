"""消費報表（P5）。會員消費＝門市銷售扣掉退貨、退款（部分退款只扣退款金額）；官網訂單不算（Q7）。

consumption() 也是 P6 抽獎資格的計算基礎，報表與抽獎的金額一定一致。
"""

import frappe
from frappe import _

from nila_app import retail
from nila_app.stockrules import num

GROUPS = ["member", "store", "detail"]


def _dates(f):
    to = f.get("to_date") or frappe.utils.nowdate()
    frm = f.get("from_date") or frappe.utils.get_first_day(to).isoformat()
    if str(frm) > str(to):
        frappe.throw(_("開始日期不能晚於結束日期"))
    return str(frm), str(to)


def consumption(from_date, to_date, stores=None, customers=None, by="customer"):
    """門市銷售的消費統計（含退貨、退款）。by：customer（會員）或 store（門市）。
    回傳 {鍵: {orders（消費次數）, gross（銷售金額）, refund（退款金額）, net（淨額）, last_date}}。
    消費次數：不含退貨單；整筆都退掉的銷售也不算一次（部分退款仍算）。"""
    key = {"customer": "s.customer", "store": "s.set_warehouse"}[by]
    cond, args = [], {"from": from_date, "to": to_date, "channel": retail.STORE_CHANNEL}
    if stores is not None:
        cond.append("s.set_warehouse in %(stores)s")
        args["stores"] = tuple(stores) or ("",)
    if customers is not None:
        cond.append("s.customer in %(customers)s")
        args["customers"] = tuple(customers) or ("",)
    where = (" and " + " and ".join(cond)) if cond else ""
    rows = frappe.db.sql(f"""
        select {key} k,
               sum(case when s.is_return = 0 and s.grand_total + coalesce(r.ret, 0) > 0 then 1 else 0 end) orders,
               sum(case when s.is_return = 0 then s.grand_total else 0 end) gross,
               sum(case when s.is_return = 1 then -s.grand_total else 0 end) refund,
               sum(s.grand_total) net, max(s.posting_date) last_date
        from `tabSales Invoice` s
        left join (select return_against, sum(grand_total) ret from `tabSales Invoice`
                   where docstatus = 1 and is_return = 1 and ifnull(return_against, '') != '' group by return_against) r
               on r.return_against = s.name and s.is_return = 0
        where s.docstatus = 1 and s.nila_channel = %(channel)s and s.posting_date between %(from)s and %(to)s {where}
        group by {key}""", args, as_dict=True)
    return {r.k: {"orders": int(r.orders or 0), "gross": num(r.gross), "refund": num(r.refund), "net": num(r.net),
                  "last_date": str(r.last_date) if r.last_date else ""} for r in rows}


def _scope(f):
    stores = [w["name"] for w in retail.allowed_stores()]
    if f.get("store"):
        if f["store"] not in stores:
            frappe.throw(_("不能查看這個門市：{0}").format(f["store"]), frappe.PermissionError)
        stores = [f["store"]]
    return stores


def build(filters):
    retail.require("sales_report")
    f = frappe.parse_json(filters or {}) or {}
    group = f.get("group") if f.get("group") in GROUPS else "member"
    frm, to = _dates(f)
    stores = _scope(f)
    customers = None
    if f.get("member"):
        customers = [m["name"] for m in retail.find_member(f["member"])]
    labels = {w["name"]: w["label"] for w in retail.allowed_stores()}
    if group == "store":
        data = consumption(frm, to, stores, customers, by="store")
        rows = [dict(v, key=k, label=labels.get(k, k)) for k, v in data.items()]
        rows.sort(key=lambda r: -r["net"])
    elif group == "member":
        members = {c.name: c for c in frappe.get_all("Customer", filters={"customer_group": retail.MEMBER_GROUP},
                                                      fields=["name", "customer_name", "nila_phone"])}
        data = consumption(frm, to, stores, customers if customers is not None else list(members), by="customer")
        rows = [dict(v, key=k, label=members[k].customer_name, phone=members[k].nila_phone) for k, v in data.items() if k in members]
        rows.sort(key=lambda r: -r["net"])
    else:
        filters_ = {"docstatus": 1, "nila_channel": retail.STORE_CHANNEL, "posting_date": ["between", [frm, to]],
                    "set_warehouse": ["in", stores or [""]]}
        if customers is not None:
            filters_["customer"] = ["in", customers or [""]]
        rows = [{"key": s.name, "label": s.name, "date": str(s.posting_date), "store": labels.get(s.set_warehouse, s.set_warehouse),
                 "customer": s.customer_name, "kind": _("退貨／退款") if s.is_return else _("銷售"), "net": num(s.grand_total),
                 "cashier": s.nila_cashier}
                for s in frappe.get_all("Sales Invoice", filters=filters_, order_by="posting_date desc, creation desc", limit=2000,
                                        fields=["name", "posting_date", "set_warehouse", "customer_name", "is_return", "grand_total",
                                                "nila_cashier"])]
    total = {"orders": sum(r.get("orders", 0) for r in rows), "gross": sum(r.get("gross", 0) for r in rows),
             "refund": sum(r.get("refund", 0) for r in rows), "net": sum(r.get("net", 0) for r in rows)}
    return {"group": group, "from_date": frm, "to_date": to, "rows": rows, "total": total}


@frappe.whitelist()
def get_report(filters=None):
    r = build(filters)
    r["rows"] = r["rows"][:1000]
    return r


@frappe.whitelist()
def get_options():
    retail.require("sales_report")
    return {"stores": [{"value": w["name"], "label": w["label"]} for w in retail.allowed_stores()]}


@frappe.whitelist()
def export_report(filters=None):
    r = build(filters)
    if r["group"] == "detail":
        head = [_("單號"), _("日期"), _("門市"), _("客人"), _("類別"), _("金額"), _("收銀人員")]
        rows = [[x["label"], x["date"], x["store"], x["customer"], x["kind"], x["net"], x["cashier"]] for x in r["rows"]]
    else:
        head = [_("會員") if r["group"] == "member" else _("門市")] + ([_("手機")] if r["group"] == "member" else []) + \
               [_("消費次數"), _("銷售金額"), _("退款金額"), _("淨額"), _("最後消費日")]
        rows = [[x["label"]] + ([x["phone"]] if r["group"] == "member" else []) +
                [x["orders"], x["gross"], x["refund"], x["net"], x["last_date"]] for x in r["rows"]]
    from frappe.utils.xlsxutils import build_xlsx_response

    build_xlsx_response([head, *rows], f"nila-sales-{r['from_date']}-{r['to_date']}")
