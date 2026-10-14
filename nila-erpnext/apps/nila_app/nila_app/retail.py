"""門市銷售與會員（P5）。

- 5 個層級的權限檢查（能力表在 retailrules.CAPS）；門市層級只能操作自己的門市（使用者權限：倉庫）。
- 會員＝客戶（客戶群組「會員」），只有姓名與手機；手機統一格式、不能重複；可合併。
- 門市銷售：掃碼或輸入料號 → 數量 → 選會員（可不選）→ 結帳，建立已收款的銷售發票，扣該門市庫存。
  價格預設「實體售價」，店長以上可改價；同一筆結帳重送不會重複建立（結帳代碼）。
- 退貨（商品退回門市庫存，可只退部分金額）與只退款（商品不退回）；部分退款只扣退款金額（Q9）。
"""

import frappe
from frappe import _

from nila_app import retailrules as R
from nila_app import stock
from nila_app.stockrules import num

MEMBER_GROUP = "會員"
WALK_IN = "門市散客"
WEB_CUSTOMER = "官網散客"
STORE_CHANNEL, WEB_CHANNEL = "門市", "官網"
STORE_PRICE_LIST = "實體售價"
PAYMENT = "Cash"


# ---------- 權限 ----------

def can(cap, user=None):
    user = user or frappe.session.user
    return R.can(cap, frappe.get_roles(user), user)


def require(cap):
    if not can(cap):
        frappe.throw(_("沒有權限執行這個動作"), frappe.PermissionError)


class elevated:
    """權限已由本模組的能力表檢查過，建立單據時改用系統權限（門市人員沒有會計科目、價格表等權限），
    並在單據的「收銀人員」記錄實際操作的人。"""

    def __enter__(self):
        self.user = frappe.session.user
        if self.user != "Administrator":
            frappe.set_user("Administrator")
        return self.user

    def __exit__(self, *exc):
        if frappe.session.user != self.user:
            frappe.set_user(self.user)


def allowed_stores(user=None):
    """可以操作的門市倉庫 [{"name", "label"}]：門市層級只有自己的門市，其他層級是全部（不含在途倉）。"""
    user = user or frappe.session.user
    whs = stock.warehouses(include_transit=False)
    if not R.store_scoped(frappe.get_roles(user), user):
        return whs
    mine = set(frappe.get_all("User Permission", filters={"user": user, "allow": "Warehouse"}, pluck="for_value"))
    return [w for w in whs if w["name"] in mine]


def check_store(store):
    if store not in {w["name"] for w in allowed_stores()}:
        frappe.throw(_("不能操作這個門市：{0}").format(store), frappe.PermissionError)
    return store


def pos_profile(store):
    """每個門市一個收銀設定（付款方式：現金），沒有就建立。"""
    label = frappe.db.get_value("Warehouse", store, "warehouse_name")
    name = f"門市-{label}"
    if not frappe.db.exists("POS Profile", name):
        company = frappe.db.get_value("Warehouse", store, "company")
        c = frappe.db.get_value("Company", company, ["write_off_account", "cost_center", "default_currency"], as_dict=True)
        frappe.get_doc({
            "doctype": "POS Profile", "__newname": name, "company": company, "warehouse": store,
            "selling_price_list": STORE_PRICE_LIST, "currency": c.default_currency, "update_stock": 1,
            "write_off_account": c.write_off_account, "write_off_cost_center": c.cost_center,
            "payments": [{"mode_of_payment": PAYMENT, "default": 1}],
        }).insert(ignore_permissions=True)
    return name


# ---------- 會員 ----------

def customer_validate(doc, method=None):
    """會員一定要有手機；手機統一格式且不能和其他客戶重複。"""
    if doc.customer_group != MEMBER_GROUP and not doc.get("nila_phone"):
        return
    if not doc.get("nila_phone"):
        frappe.throw(_("會員一定要填手機號碼"))
    try:
        doc.nila_phone = R.normalize_phone(doc.nila_phone)
    except R.RetailError as e:
        frappe.throw(str(e))
    dup = frappe.db.get_value("Customer", {"nila_phone": doc.nila_phone, "name": ["!=", doc.name]},
                              ["name", "customer_name"], as_dict=True)
    if dup:
        frappe.throw(_("手機 {0} 已經是會員「{1}」（{2}）").format(doc.nila_phone, dup.customer_name, dup.name),
                     title=_("會員重複"))


def _member_row(c):
    return {"name": c.name, "customer_name": c.customer_name, "phone": c.nila_phone}


@frappe.whitelist()
def find_member(q):
    """用手機（完整號碼）或姓名找會員，最多 10 筆。"""
    require("member")
    q = (q or "").strip()
    if not q:
        return []
    fields = ["name", "customer_name", "nila_phone"]
    try:
        phone = R.normalize_phone(q)
    except R.RetailError:
        phone = None
    if phone:
        return [_member_row(c) for c in frappe.get_all("Customer", filters={"nila_phone": phone}, fields=fields)]
    return [_member_row(c) for c in frappe.get_all("Customer", filters={"customer_group": MEMBER_GROUP, "disabled": 0},
                                                  or_filters={"customer_name": ["like", f"%{q}%"], "nila_phone": ["like", f"%{q}%"]},
                                                  fields=fields, limit=10, order_by="customer_name")]


@frappe.whitelist()
def create_member(customer_name, phone):
    require("member")
    name = (customer_name or "").strip()
    if not name:
        frappe.throw(_("會員姓名必填"))
    with elevated():
        doc = frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Individual",
                              "customer_group": MEMBER_GROUP, "nila_phone": phone})
        doc.insert()
    return _member_row(doc)


@frappe.whitelist()
def merge_members(source, target):
    """把會員 source 併入 target（消費紀錄全部移到 target，source 刪除）。"""
    require("member_merge")
    if source == target:
        frappe.throw(_("不能合併同一個會員"))
    for n in (source, target):
        if frappe.db.get_value("Customer", n, "customer_group") != MEMBER_GROUP:
            frappe.throw(_("{0} 不是會員").format(n))
    from frappe.model.rename_doc import rename_doc

    with elevated():
        rename_doc("Customer", source, target, merge=True)
    return target


# ---------- 門市銷售 ----------

@frappe.whitelist()
def sale_context():
    require("store_sale")
    return {"stores": [{"value": w["name"], "label": w["label"]} for w in allowed_stores()],
            "can_price": can("price_override"), "can_return": can("store_return"), "walk_in": WALK_IN}


def _store_prices(items):
    return dict(frappe.get_all("Item Price", filters={"price_list": STORE_PRICE_LIST, "item_code": ["in", list(items) or [""]]},
                               fields=["item_code", "price_list_rate"], as_list=True))


@frappe.whitelist()
def lookup_item(code):
    """掃碼或輸入料號：完全符合就回傳該規格；否則回傳最多 10 個候選（料號或名稱包含輸入的文字）。"""
    require("store_sale")
    code = (code or "").strip()
    fields = ["name", "item_name", "nila_status"]
    hit = frappe.get_all("Item", filters={"name": code.upper(), "variant_of": ["is", "set"], "disabled": 0}, fields=fields)
    if not hit:
        hit = frappe.get_all("Item", filters={"variant_of": ["is", "set"], "disabled": 0},
                             or_filters={"name": ["like", f"%{code}%"], "item_name": ["like", f"%{code}%"]},
                             fields=fields, limit=10, order_by="name")
    prices = _store_prices([h.name for h in hit])
    return {"exact": len(hit) == 1 and hit[0].name == code.upper(),
            "items": [{"item": h.name, "item_name": h.item_name, "status": h.nila_status, "rate": prices.get(h.name)} for h in hit]}


def _existing(client_id):
    return frappe.db.get_value("Sales Invoice", {"nila_client_id": client_id, "docstatus": 1},
                               ["name", "grand_total", "rounded_total"], as_dict=True)


def _pay_in_full(doc):
    total = doc.rounded_total or doc.grand_total
    for p in doc.payments:
        p.amount = total if p.default else 0
    if not any(p.default for p in doc.payments) and doc.payments:
        doc.payments[0].amount = total


def _client_id(data):
    cid = str(data.get("client_id") or "").strip()
    if not cid or len(cid) > 64:
        frappe.throw(_("缺少結帳代碼，請重新整理頁面"))
    return cid


@frappe.whitelist()
def checkout(data):
    """門市結帳：data = {client_id, store, member, lines: [{item, qty, rate}]}。
    同一個 client_id 重送時回傳原本的銷售發票（不會重複扣庫存）。"""
    require("store_sale")
    data = frappe.parse_json(data)
    cid = _client_id(data)
    done = _existing(cid)
    if done:
        return {"name": done.name, "total": done.rounded_total or done.grand_total, "duplicate": True}
    store = check_store(data.get("store"))
    try:
        lines = R.merge_cart(data.get("lines"))
    except R.RetailError as e:
        frappe.throw(str(e))
    items = {ln["item"] for ln in lines}
    valid = set(frappe.get_all("Item", filters={"name": ["in", list(items)], "variant_of": ["is", "set"], "disabled": 0}, pluck="name"))
    missing = sorted(items - valid)
    if missing:
        frappe.throw(_("找不到這些商品：{0}").format("、".join(missing)))
    prices = _store_prices(items)
    for ln in lines:
        if ln["rate"] is not None and ln["rate"] != num(prices.get(ln["item"])) and not can("price_override"):
            frappe.throw(_("沒有改價的權限：{0}").format(ln["item"]), frappe.PermissionError)
    member = data.get("member") or None
    if member and frappe.db.get_value("Customer", member, "customer_group") != MEMBER_GROUP:
        frappe.throw(_("{0} 不是會員").format(member))
    try:
        with elevated() as cashier:
            doc = frappe.get_doc({
                "doctype": "Sales Invoice", "customer": member or WALK_IN,
                "company": frappe.db.get_value("Warehouse", store, "company"),
                "is_pos": 1, "pos_profile": pos_profile(store), "update_stock": 1, "set_warehouse": store,
                "selling_price_list": STORE_PRICE_LIST, "nila_channel": STORE_CHANNEL, "nila_client_id": cid,
                "nila_cashier": cashier,
                "items": [{"item_code": ln["item"], "qty": ln["qty"], "warehouse": store} for ln in lines],
            })
            doc.set_missing_values()
            for d, ln in zip(doc.items, lines):
                if ln["rate"] is not None:
                    d.rate = ln["rate"]
            doc.calculate_taxes_and_totals()
            _pay_in_full(doc)
            doc.insert()
            doc.submit()
    except frappe.UniqueValidationError:
        frappe.db.rollback()
        done = _existing(cid)
        if done:  # 同一筆結帳同時送了兩次，另一次已經成功
            return {"name": done.name, "total": done.rounded_total or done.grand_total, "duplicate": True}
        raise
    return {"name": doc.name, "total": doc.rounded_total or doc.grand_total, "duplicate": False}


# ---------- 退貨、退款 ----------

def _sold(invoice):
    rows = frappe.get_all("Sales Invoice Item", filters={"parent": invoice}, fields=["name", "item_code", "item_name", "qty", "rate"],
                          order_by="idx")
    returned = {}
    for r in frappe.db.sql("""
            select i.sales_invoice_item row, sum(-i.qty) qty from `tabSales Invoice Item` i
            join `tabSales Invoice` s on s.name = i.parent
            where s.docstatus = 1 and s.is_return = 1 and s.return_against = %s group by i.sales_invoice_item""",
            invoice, as_dict=True):
        returned[r.row] = num(r.qty)
    return {r.name: {"item": r.item_code, "item_name": r.item_name, "qty": num(r.qty), "rate": num(r.rate),
                     "returned": returned.get(r.name, 0)} for r in rows}


def _store_invoice(name):
    inv = frappe.db.get_value("Sales Invoice", name, ["name", "docstatus", "is_return", "nila_channel", "set_warehouse",
                                                      "customer", "posting_date", "grand_total", "rounded_total"], as_dict=True)
    if not inv or inv.docstatus != 1 or inv.is_return or inv.nila_channel != STORE_CHANNEL:
        frappe.throw(_("找不到門市銷售：{0}").format(name))
    check_store(inv.set_warehouse)
    return inv


@frappe.whitelist()
def find_sales(q):
    """用銷售單號或會員手機找門市銷售（最近 20 筆），列出每一行還可以退幾件。"""
    require("store_return")
    q = (q or "").strip()
    stores = [w["name"] for w in allowed_stores()]
    filters = {"docstatus": 1, "is_return": 0, "nila_channel": STORE_CHANNEL, "set_warehouse": ["in", stores or [""]]}
    try:
        filters["customer"] = ["in", frappe.get_all("Customer", filters={"nila_phone": R.normalize_phone(q)}, pluck="name") or [""]]
    except R.RetailError:
        filters["name"] = ["like", f"%{q}%"]
    names = frappe.get_all("Sales Invoice", filters=filters, pluck="name", order_by="posting_date desc, creation desc", limit=20)
    out = []
    for n in names:
        inv = _store_invoice(n)
        out.append({"name": n, "posting_date": str(inv.posting_date), "customer": inv.customer,
                    "customer_name": frappe.db.get_value("Customer", inv.customer, "customer_name"),
                    "store": inv.set_warehouse, "total": inv.rounded_total or inv.grand_total,
                    "lines": [dict(v, row=k) for k, v in _sold(n).items()]})
    return out


@frappe.whitelist()
def make_return(data):
    """退貨或只退款：data = {client_id, invoice, mode: goods|refund, lines: [{row, qty, amount}], reason}。"""
    require("store_return")
    data = frappe.parse_json(data)
    cid = _client_id(data)
    done = _existing(cid)
    if done:
        return {"name": done.name, "total": done.rounded_total or done.grand_total, "duplicate": True}
    inv = _store_invoice(data.get("invoice"))
    try:
        plan = R.plan_return(_sold(inv.name), data.get("mode"), data.get("lines"))
    except R.RetailError as e:
        frappe.throw(str(e))
    from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

    by_row = {p["row"]: p for p in plan}
    with elevated() as cashier:
        ret = make_sales_return(inv.name)
        ret.items = [d for d in ret.items if d.sales_invoice_item in by_row]
        for d in ret.items:
            p = by_row[d.sales_invoice_item]
            d.qty, d.rate = -p["qty"], p["rate"]
        ret.set_missing_values()
        ret.update_stock = 1 if data.get("mode") == R.GOODS else 0  # 收銀設定會把它改回 1，要在之後設定
        ret.nila_client_id = cid
        ret.nila_channel = STORE_CHANNEL
        ret.set_warehouse = inv.set_warehouse  # 退貨單不會自動帶門市；報表依門市統計要靠它
        ret.nila_cashier = cashier
        ret.remarks = (data.get("reason") or "").strip()[:500] or None
        ret.calculate_taxes_and_totals()
        _pay_in_full(ret)
        ret.insert()
        ret.submit()
    return {"name": ret.name, "total": ret.rounded_total or ret.grand_total, "duplicate": False}
