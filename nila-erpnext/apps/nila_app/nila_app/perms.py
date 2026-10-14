"""5 個層級的權限檢查（妮菈的頁面與功能共用）。能力表在 levels.py。"""

import frappe
from frappe import _

from nila_app import levels as L


def can(cap, user=None):
    user = user or frappe.session.user
    return L.has_cap(cap, frappe.get_roles(user), user)


def require(*caps):
    """有其中一項能力就可以。"""
    if not any(can(c) for c in caps):
        frappe.throw(_("沒有權限執行這個動作"), frappe.PermissionError)


def caps(*names):
    """給畫面用：{能力: 是否可以}。"""
    return {n: can(n) for n in names}


def scoped(user=None):
    user = user or frappe.session.user
    return L.store_scoped(frappe.get_roles(user), user)


def allowed_stores(user=None):
    """可以操作的門市倉庫 [{"name", "label", ...}]：門市層級只有自己的門市，其他層級是全部（不含在途倉）。"""
    from nila_app import stock

    user = user or frappe.session.user
    whs = stock.warehouses(include_transit=False)
    if not scoped(user):
        return whs
    mine = set(frappe.get_all("User Permission", filters={"user": user, "allow": "Warehouse"}, pluck="for_value"))
    return [w for w in whs if w["name"] in mine]


def check_store(store):
    if store not in {w["name"] for w in allowed_stores()}:
        frappe.throw(_("不能操作這個門市：{0}").format(store), frappe.PermissionError)
    return store


class elevated:
    """權限已由能力表檢查過，建立單據時改用系統權限（門市人員沒有會計科目、價格表等權限），
    呼叫的地方另外記錄實際操作的人。"""

    def __enter__(self):
        self.user = frappe.session.user
        if self.user != "Administrator":
            frappe.set_user("Administrator")
        return self.user

    def __exit__(self, *exc):
        if frappe.session.user != self.user:
            frappe.set_user(self.user)


def has_app_permission():
    """首頁的「妮菈」：有任何一個妮菈層級（或系統管理員）就顯示。"""
    roles = set(frappe.get_roles())
    return frappe.session.user == "Administrator" or "System Manager" in roles or bool(roles & set(L.LEVELS))
