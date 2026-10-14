"""還原演練與健康檢查用的資料摘要（只讀取，不改資料）。

    bench --site <網站> execute nila_app.setup.drill.report

drill-nila.ps1 會對「正式網站」與「從備份還原的臨時網站」各執行一次並比較。
"""

import json

import frappe


def _count(doctype, filters=None):
    try:
        return frappe.db.count(doctype, filters or {})
    except Exception:
        return None


def _latest(sql):
    try:
        v = frappe.db.sql(sql)[0][0]
        return str(v) if v else ""
    except Exception:
        return ""


def report():
    from frappe.utils.password import get_decrypted_password

    out = {
        "version": frappe.get_attr("nila_app.__version__"),
        "company": frappe.db.get_value("Company", {}, "name") or "",
        "styles": _count("Item", {"has_variants": 1}),
        "variants": _count("Item", {"variant_of": ["is", "set"]}),
        "members": _count("Customer", {"customer_group": "會員"}),
        "users": _count("User", {"user_type": "System User", "enabled": 1}),
        "store_sales": _count("Sales Invoice", {"docstatus": 1, "nila_channel": "門市"}),
        "sales_orders": _count("Sales Order", {"docstatus": 1}),
        "stock_entries": _count("Stock Ledger Entry", {"is_cancelled": 0}),
        "last_sale": _latest("select max(posting_date) from `tabSales Invoice` where docstatus = 1"),
        "last_stock": _latest("select left(max(posting_datetime), 16) from `tabStock Ledger Entry` where is_cancelled = 0"),
        "stock_qty": float(frappe.db.sql("select coalesce(sum(actual_qty), 0) from `tabBin`")[0][0] or 0),
    }
    # 已儲存的金鑰（SHOPLINE）解得開，表示加密金鑰也一起還原了
    out["secrets_ok"] = True
    if frappe.db.sql("select 1 from `__Auth` where doctype = 'Nila SHOPLINE Settings' and fieldname = 'token'"):
        try:
            out["secrets_ok"] = bool(get_decrypted_password("Nila SHOPLINE Settings", "Nila SHOPLINE Settings", "token",
                                                            raise_exception=False))
        except Exception:
            out["secrets_ok"] = False
    print("NILA_DRILL_REPORT " + json.dumps(out, ensure_ascii=False, default=str))
    return out
