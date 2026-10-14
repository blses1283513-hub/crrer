"""帳號管理（P6）：只有管理員可以使用。

- 新增帳號：姓名、帳號（登入用，英數字）、層級、門市、初始密碼。不寄信（區網內沒有郵件主機）。
- 層級決定能做什麼（levels.CAPS）與 ERPNext 原本畫面的權限（levels.BUNDLES）。
- 門市店長、店員要選門市：只能看、只能操作這些門市（使用者權限：倉庫）。
- 停用／啟用、重設密碼。不能停用或降級自己，也不能修改內建的 Administrator（避免把自己鎖在外面）。
"""

import frappe
from frappe import _

from nila_app import levels as L
from nila_app import perms

EMAIL_DOMAIN = "nila.local"  # 帳號不需要真實信箱；登入時直接輸入帳號
WORKSPACE = "妮菈"


def _stores():
    from nila_app import stock

    return {w["name"]: w["label"] for w in stock.warehouses(include_transit=False)}


def _user_rows(names=None):
    filters = {"user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]}
    if names:
        filters["name"] = ["in", names]
    users = frappe.get_all("User", filters=filters, fields=["name", "full_name", "username", "enabled", "last_login"],
                           order_by="enabled desc, full_name")
    roles, stores = {}, {}
    for r in frappe.get_all("Has Role", filters={"parenttype": "User", "parent": ["in", [u.name for u in users] or [""]]},
                            fields=["parent", "role"]):
        roles.setdefault(r.parent, set()).add(r.role)
    for p in frappe.get_all("User Permission", filters={"allow": "Warehouse", "user": ["in", [u.name for u in users] or [""]]},
                            fields=["user", "for_value"], order_by="is_default desc, creation"):
        stores.setdefault(p.user, []).append(p.for_value)
    labels = _stores()
    out = []
    for u in users:
        level = L.level_of(roles.get(u.name))
        out.append({"name": u.name, "full_name": u.full_name, "username": u.username, "enabled": u.enabled,
                    "last_login": str(u.last_login or "")[:16], "level": level, "level_label": L.LEVEL_LABELS.get(level, _("（未設定）")),
                    "stores": stores.get(u.name, []), "store_labels": [labels.get(s, s) for s in stores.get(u.name, [])]})
    return out


@frappe.whitelist()
def list_accounts():
    perms.require("accounts")
    return {"accounts": _user_rows(),
            "levels": [{"value": lv, "label": L.LEVEL_LABELS[lv]} for lv in L.LEVELS],
            "stores": [{"value": k, "label": v} for k, v in _stores().items()],
            "store_levels": sorted(L.STORE_LEVELS), "me": frappe.session.user}


def _sync_stores(user, chosen):
    """門市（使用者權限：倉庫）：只保留選的門市；第一間是預設門市。"""
    have = {p.for_value: p.name for p in frappe.get_all("User Permission", filters={"user": user, "allow": "Warehouse"},
                                                         fields=["name", "for_value"])}
    for store, name in have.items():
        if store not in chosen:
            frappe.delete_doc("User Permission", name, ignore_permissions=True)
    for i, store in enumerate(chosen):
        if store in have:
            frappe.db.set_value("User Permission", have[store], "is_default", 1 if i == 0 else 0)
        else:
            frappe.get_doc({"doctype": "User Permission", "user": user, "allow": "Warehouse", "for_value": store,
                            "apply_to_all_doctypes": 1, "is_default": 1 if i == 0 else 0}).insert(ignore_permissions=True)


@frappe.whitelist()
def save_account(data):
    """新增或修改帳號：data = {name（修改時）, full_name, username, level, stores, password（新增必填）}。"""
    perms.require("accounts")
    data = frappe._dict(frappe.parse_json(data))
    name = data.get("name")
    if name == "Administrator":
        frappe.throw(_("不能修改內建的 Administrator 帳號"))
    data.username = str(data.get("username") or "").strip().lower()
    stores = list(dict.fromkeys(data.get("stores") or []))
    taken = set(frappe.get_all("User", filters={"username": ["is", "set"], "name": ["!=", name or ""]}, pluck="username"))
    errors = L.check_account({**data, "stores": stores}, _stores(), taken)
    if not name and not data.get("password"):
        errors.append("新帳號要設定初始密碼")
    if name and name == frappe.session.user and data.level != L.ADMIN:
        errors.append("不能把自己改成管理員以外的層級（避免沒有人能管理帳號）")
    if errors:
        frappe.throw("；".join(errors), title=_("資料有誤"))
    if data.level not in L.STORE_LEVELS:
        stores = []  # 總公司層級不限門市

    if name:
        user = frappe.get_doc("User", name)
        user.first_name, user.last_name = data.full_name.strip(), ""
        user.username = data.username
    else:
        user = frappe.get_doc({"doctype": "User", "email": f"{data.username}@{EMAIL_DOMAIN}", "first_name": data.full_name.strip(),
                               "username": data.username, "send_welcome_email": 0, "user_type": "System User",
                               "language": "zh-TW", "time_zone": "Asia/Taipei"})
    if data.get("password"):
        user.new_password = data.password  # ERPNext 會檢查密碼強度
    add, remove = L.plan_roles(data.level, [r.role for r in user.get("roles", [])])
    user.set("roles", [r for r in user.get("roles", []) if r.role not in remove])
    for role in add:
        user.append("roles", {"role": role})
    if frappe.db.exists("Workspace", WORKSPACE):
        user.default_workspace = WORKSPACE
    user.flags.ignore_permissions = True
    user.save() if name else user.insert()
    _sync_stores(user.name, stores)
    return _user_rows([user.name])[0]


@frappe.whitelist()
def set_enabled(name, enabled):
    perms.require("accounts")
    if name in ("Administrator", frappe.session.user):
        frappe.throw(_("不能停用自己或內建的 Administrator"))
    user = frappe.get_doc("User", name)
    user.enabled = 1 if frappe.utils.cint(enabled) else 0
    user.flags.ignore_permissions = True
    user.save()
    return _user_rows([name])[0]


@frappe.whitelist()
def reset_password(name, password):
    perms.require("accounts")
    if name == "Administrator":
        frappe.throw(_("內建 Administrator 的密碼請用安裝說明裡的方式修改"))
    if not password:
        frappe.throw(_("請輸入新密碼"))
    user = frappe.get_doc("User", name)
    user.new_password = password
    user.flags.ignore_permissions = True
    user.save()
    return True
