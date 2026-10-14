"""網站基本設定：安裝、升級（migrate）時自動執行；也可手動執行：

    bench --site <網站> execute nila_app.setup.install.setup_site

全部可重複執行：已存在的資料不會重複建立，也不會刪除或改動已在使用的資料。
需要 sites/nila-config.json（由安裝腳本產生）才會建立公司與倉庫；沒有設定檔時只建立與公司無關的部分。
"""

import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from nila_app.catalog import STATUSES
from nila_app.stockrules import DISPATCH_STATUSES
from nila_app.setup.config import TRANSIT, ConfigError, check_shape_changes, load_config, read_terms

ITEM_GROUP = "穿戴甲"
UOM = "件"
PRICE_LISTS = ["官網售價", "實體售價"]
SHAPE_ATTR = "甲型"
SIZE_ATTR = "尺寸"

COST_PERMLEVEL = 5  # 成本欄位的權限層級（ERPNext 原本沒用到 5，不會和既有設定衝突）
_ON_STYLE = "eval:doc.variant_of"  # 規格（變體）上唯讀，只能在款式修改
CUSTOM_FIELDS = {
    "Item": [
        {"fieldname": "nila_status", "label": "商品狀態", "fieldtype": "Select", "options": "\n".join(STATUSES),
         "default": "上架", "insert_after": "item_name", "in_list_view": 1, "in_standard_filter": 1,
         "read_only_depends_on": _ON_STYLE,
         "description": "停售、停產：不能接新訂單，門市仍可賣；停產：不再補貨。在款式修改，所有規格一起變更"},
        {"fieldname": "nila_shape", "label": "甲型", "fieldtype": "Data", "insert_after": "nila_status",
         "read_only": 1, "depends_on": "eval:doc.variant_of", "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "nila_size", "label": "尺寸", "fieldtype": "Data", "insert_after": "nila_shape",
         "read_only": 1, "depends_on": "eval:doc.variant_of", "in_list_view": 1, "in_standard_filter": 1},
        {"fieldname": "nila_reorder_target", "label": "補貨目標", "fieldtype": "Int", "insert_after": "nila_size",
         "depends_on": "eval:!doc.has_variants", "non_negative": 1,
         "description": "全公司合計的補貨目標；依款式與甲型設定"},
        {"fieldname": "nila_cost", "label": "成本", "fieldtype": "Currency", "insert_after": "nila_reorder_target",
         "read_only_depends_on": _ON_STYLE, "non_negative": 1, "permlevel": COST_PERMLEVEL},
        {"fieldname": "nila_web_price", "label": "官網售價", "fieldtype": "Currency", "insert_after": "nila_cost",
         "read_only_depends_on": _ON_STYLE, "non_negative": 1},
        {"fieldname": "nila_store_price", "label": "實體售價", "fieldtype": "Currency", "insert_after": "nila_web_price",
         "read_only_depends_on": _ON_STYLE, "non_negative": 1, "in_list_view": 1,
         "description": "在款式修改成本與售價，所有規格會自動套用"},
    ],
    "Sales Order": [
        {"fieldname": "nila_dispatch_status", "label": "出貨狀態", "fieldtype": "Select",
         "options": "\n" + "\n".join(DISPATCH_STATUSES), "insert_after": "status", "read_only": 1,
         "allow_on_submit": 1, "no_copy": 1, "in_list_view": 1, "in_standard_filter": 1,
         "description": "依先後分配庫存後自動計算；入庫、調撥、出貨、取消後會自動更新"},
        {"fieldname": "nila_channel", "label": "銷售管道", "fieldtype": "Select", "options": "\n門市\n官網",
         "insert_after": "nila_dispatch_status", "read_only": 1, "in_standard_filter": 1, "no_copy": 1,
         "description": "「官網」是從 SHOPLINE 自動匯入的訂單"},
        {"fieldname": "nila_shopline_number", "label": "官網訂單編號", "fieldtype": "Data", "insert_after": "nila_channel",
         "read_only": 1, "no_copy": 1, "in_standard_filter": 1, "in_global_search": 1,
         "depends_on": "eval:doc.nila_shopline_number"},
        {"fieldname": "nila_shopline_id", "label": "SHOPLINE 訂單 ID", "fieldtype": "Data", "insert_after": "nila_shopline_number",
         "read_only": 1, "no_copy": 1, "hidden": 1, "unique": 1, "description": "同一筆官網訂單不會重複建立"},
    ],
    "Stock Entry": [
        {"fieldname": "nila_destination", "label": "調入倉庫", "fieldtype": "Link", "options": "Warehouse",
         "insert_after": "add_to_transit", "read_only": 1, "no_copy": 1, "depends_on": "eval:doc.nila_destination",
         "in_standard_filter": 1, "description": "在途調撥單的最終目的地，「到貨入庫」時轉入這個倉庫"},
        {"fieldname": "nila_sales_order", "label": "相關訂單", "fieldtype": "Link", "options": "Sales Order",
         "insert_after": "nila_destination", "read_only": 1, "no_copy": 1, "depends_on": "eval:doc.nila_sales_order"},
    ],
    "Customer": [
        {"fieldname": "nila_phone", "label": "手機", "fieldtype": "Data", "insert_after": "customer_name", "unique": 1,
         "in_list_view": 1, "in_standard_filter": 1, "in_global_search": 1, "bold": 1,
         "description": "會員以手機號碼識別，不能重複（自動統一成 09xxxxxxxx）"},
    ],
    "Sales Invoice": [
        {"fieldname": "nila_channel", "label": "銷售管道", "fieldtype": "Select", "options": "\n門市\n官網",
         "insert_after": "customer", "read_only": 1, "in_standard_filter": 1, "in_list_view": 1,
         "description": "只有「門市」計入會員消費與抽獎（官網訂單不算）"},
        {"fieldname": "nila_client_id", "label": "結帳代碼", "fieldtype": "Data", "insert_after": "nila_channel",
         "unique": 1, "hidden": 1, "read_only": 1, "no_copy": 1, "description": "同一筆結帳重送時不會重複建立"},
        {"fieldname": "nila_cashier", "label": "收銀人員", "fieldtype": "Link", "options": "User",
         "insert_after": "nila_client_id", "read_only": 1, "no_copy": 1, "in_standard_filter": 1},
    ],
    "Material Request Item": [
        {"fieldname": "nila_suggested_qty", "label": "建議補貨數", "fieldtype": "Float", "insert_after": "qty",
         "read_only": 1, "no_copy": 1, "in_list_view": 1, "columns": 1},
    ],
}
# 原因選項的預設值（可在「原因選項」自行新增或停用）
DEFAULT_REASONS = {
    "補貨調整": ["預計熱賣", "銷售趨緩", "廠商最低叫貨量", "季節或活動", "其他"],
    "負庫存": ["訂單超賣", "門市先賣未入帳", "盤點差異", "其他"],
    "調撥調整": ["門市保留展示", "門市自己的客人要用", "其他"],
}
DEFAULT_SUPPLIER = "預設廠商"
MEMBER_GROUP = "會員"
DEFAULT_CUSTOMERS = ["門市散客", "官網散客"]  # 不是會員的門市客人；SHOPLINE 官網訂單（P7）
# 預設會把款式的這些欄位複製到所有規格；補貨設定每個規格不同，不能複製
NOT_COPIED_TO_VARIANTS = ["reorder_levels"]
# 安裝精靈建立的英文預設倉庫：沒有庫存異動就停用，避免選錯
DEFAULT_WAREHOUSES = ["Stores", "Finished Goods", "Work In Progress", "Goods In Transit"]


def log(msg):
    print(msg, flush=True)


def _config():
    return load_config(frappe.local.sites_path)


def after_install():
    # 初次設定精靈完成前（例如剛建立網站），公司、時區、根類別都還不存在，什麼都不做；
    # 由 setup_site 完成初次設定後再建立。之後每次升級都會重新確認。
    if not frappe.is_setup_complete():
        return
    ensure_basics()
    cfg = _config()
    if cfg:
        ensure_company_data(cfg)


def after_migrate():
    after_install()


def setup_site():
    """安裝腳本呼叫：完成初次設定精靈（若尚未完成）並建立全部基本資料。"""
    cfg = _config()
    if not cfg:
        raise ConfigError(f"找不到 {os.path.join(frappe.local.sites_path, 'nila-config.json')}")
    if not frappe.is_setup_complete():
        from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

        setup_complete({
            "language": "zh-TW", "country": "Taiwan", "timezone": "Asia/Taipei", "currency": "TWD",
            "company_name": cfg["company_name"], "company_abbr": cfg["company_abbr"],
            "chart_of_accounts": "Standard",
            "fy_start_date": f"{frappe.utils.nowdate()[:4]}-01-01", "fy_end_date": f"{frappe.utils.nowdate()[:4]}-12-31",
            "setup_demo": 0,
        })
        if not frappe.is_setup_complete():
            raise RuntimeError("初次設定精靈沒有完成")
        log(f"✓ 初次設定完成：{cfg['company_name']}（台灣、新台幣、台北時區）")
    ensure_basics()
    ensure_company_data(cfg)
    frappe.db.commit()
    log("✓ 基本設定完成")


def ensure_basics():
    """與公司無關的設定：語言、排程器、單位、商品類別、價格表、自訂欄位、尺寸屬性、用語。"""
    if frappe.db.get_single_value("System Settings", "language") != "zh-TW":
        frappe.db.set_single_value("System Settings", "language", "zh-TW")
    frappe.db.set_value("User", "Administrator", "language", "zh-TW")

    from frappe.utils.scheduler import enable_scheduler, is_scheduler_disabled

    if is_scheduler_disabled():
        enable_scheduler()

    if not frappe.db.exists("UOM", UOM):
        frappe.get_doc({"doctype": "UOM", "uom_name": UOM, "must_be_whole_number": 1}).insert()
    if not frappe.db.exists("Item Group", ITEM_GROUP):
        frappe.get_doc({"doctype": "Item Group", "item_group_name": ITEM_GROUP,
                        "parent_item_group": "All Item Groups"}).insert()
    currency = frappe.db.get_single_value("System Settings", "currency") or "TWD"
    if not frappe.db.exists("Currency", currency):
        currency = "TWD"
    for pl in PRICE_LISTS:
        if not frappe.db.exists("Price List", pl):
            frappe.get_doc({"doctype": "Price List", "price_list_name": pl, "currency": currency,
                            "selling": 1, "enabled": 1}).insert()
    create_custom_fields(CUSTOM_FIELDS, update=True)
    _ensure_item_settings()
    _ensure_stock_settings()
    _ensure_reasons()
    _ensure_roles()
    _ensure_level_permissions()
    _ensure_workspace()
    if not frappe.db.get_single_value("System Settings", "allow_login_using_user_name"):
        frappe.db.set_single_value("System Settings", "allow_login_using_user_name", 1)  # 用帳號登入，不需要信箱
    if not frappe.db.exists("Supplier", DEFAULT_SUPPLIER):
        frappe.get_doc({"doctype": "Supplier", "supplier_name": DEFAULT_SUPPLIER,
                        "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 1}, "name")}).insert()
    _ensure_attribute(SIZE_ATTR, [(s, s) for s in (_config() or {}).get("sizes", ["XS", "S", "M", "L"])])
    _ensure_terms()


def ensure_company_data(cfg):
    """依設定檔建立：甲型、總公司與分公司倉庫、在途倉。只新增，不刪除也不改名。"""
    existing = {}
    if frappe.db.exists("Item Attribute", SHAPE_ATTR):
        for v in frappe.get_doc("Item Attribute", SHAPE_ATTR).item_attribute_values:
            existing[v.attribute_value] = v.abbr
    new = check_shape_changes(existing, cfg["shapes"])
    _ensure_attribute(SHAPE_ATTR, [(s["name"], s["abbr"]) for s in new])

    company = frappe.db.get_value("Company", {"abbr": cfg["company_abbr"]}, "name") or frappe.db.get_value("Company", {}, "name")
    if not company:
        raise RuntimeError("找不到公司，請先完成初次設定")
    abbr = frappe.db.get_value("Company", company, "abbr")
    parent = frappe.db.get_value("Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ["in", ["", None]]}, "name")
    for name in [cfg["hq"], *cfg["branches"]]:
        if not frappe.db.exists("Warehouse", f"{name} - {abbr}"):
            frappe.get_doc({"doctype": "Warehouse", "warehouse_name": name, "company": company,
                            "parent_warehouse": parent}).insert()
    transit = f"{TRANSIT} - {abbr}"
    if not frappe.db.exists("Warehouse", transit):
        frappe.get_doc({"doctype": "Warehouse", "warehouse_name": TRANSIT, "company": company,
                        "parent_warehouse": parent, "warehouse_type": "Transit"}).insert()
    if frappe.db.get_value("Company", company, "default_in_transit_warehouse") != transit:
        frappe.db.set_value("Company", company, "default_in_transit_warehouse", transit)
    _ensure_default_warehouse(company, f"{cfg['hq']} - {abbr}", abbr)
    _ensure_retail(company, [f"{n} - {abbr}" for n in [cfg["hq"], *cfg["branches"]]])


def _ensure_item_settings():
    """商品清單顯示「款式」欄；款式的補貨設定不複製到規格；不自動從交易新增售價（售價只由款式同步）。"""
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    if frappe.db.get_value("Property Setter", {"doc_type": "Item", "field_name": "variant_of",
                                                   "property": "in_list_view"}, "value") != "1":
        make_property_setter("Item", "variant_of", "in_list_view", 1, "Check", validate_fields_for_doctype=False)
    frappe.db.delete("Variant Field", {"parent": "Item Variant Settings", "field_name": ["in", NOT_COPIED_TO_VARIANTS]})
    if frappe.db.get_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing"):
        frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 0)


def _ensure_stock_settings():
    """庫存可以變成負數（需求 Q1：先出貨、門市先賣，之後再入庫）。"""
    if not frappe.db.get_single_value("Stock Settings", "allow_negative_stock"):
        frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
        log("✓ 允許負庫存")


def _ensure_reasons():
    """原因選項的預設值：某一類完全沒有選項時才建立（之後使用者刪改不會被加回來）。
    更新時 update-nila.ps1 會先執行基本設定、再 migrate 建立新的資料表；這時還沒有這個 DocType 就先略過，
    migrate 結束後的 after_migrate 會再執行一次。"""
    if not frappe.db.exists("DocType", "Nila Reason"):
        return
    for kind, reasons in DEFAULT_REASONS.items():
        if not frappe.db.exists("Nila Reason", {"kind": kind}):
            for r in reasons:
                frappe.get_doc({"doctype": "Nila Reason", "kind": kind, "reason": r}).insert()


def _ensure_roles():
    """5 個層級的角色（權限內容見 retailrules.CAPS；帳號與門市在「帳號管理」設定）。"""
    from nila_app.retailrules import LEVELS

    for role in LEVELS:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def _ensure_perm(doctype, role, permlevel, ptypes):
    """確保某角色在某單據有這些權限（可重複執行）。第一次會先把 ERPNext 原本的權限複製成自訂權限，原本的權限不變。"""
    from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

    setup_custom_perms(doctype)
    if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": permlevel, "if_owner": 0}):
        add_permission(doctype, role, permlevel)
    for ptype in ptypes:
        update_permission_property(doctype, role, permlevel, ptype, 1, validate=False)


def _ensure_level_permissions():
    """5 個層級在 ERPNext 原本畫面的權限：額外的單據權限、成本欄位只有可看成本的角色看得到、含金額的庫存報表限制角色。"""
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    from nila_app import levels as L

    for doctype, role, ptypes in L.EXTRA_PERMS:
        _ensure_perm(doctype, role, 0, ptypes)
    for parent, fields in L.COST_FIELDS.items():
        for doctype, field in fields:
            if field.startswith("nila_"):
                continue  # 自訂欄位直接在 CUSTOM_FIELDS 設定
            if frappe.get_meta(doctype).get_field(field) and str(frappe.db.get_value(
                    "Property Setter", {"doc_type": doctype, "field_name": field, "property": "permlevel"}, "value")) != str(COST_PERMLEVEL):
                make_property_setter(doctype, field, "permlevel", COST_PERMLEVEL, "Int", validate_fields_for_doctype=False)
        for role in L.COST_ROLES:
            _ensure_perm(parent, role, COST_PERMLEVEL, ["read"])
    # 庫存報表大多顯示金額：只有可看成本的角色能開（數量請用「庫存表」）。已經自訂過的報表不動
    allowed = {"Stock Manager", "System Manager", "Accounts Manager", L.ADMIN, L.MANAGER}
    for report in frappe.get_all("Report", filters={"module": "Stock", "disabled": 0}, pluck="name"):
        if report in L.OPEN_STOCK_REPORTS or frappe.db.exists("Custom Role", {"report": report}):
            continue
        roles = {r.role for r in frappe.get_all("Has Role", filters={"parent": report, "parenttype": "Report"}, fields=["role"])}
        keep = sorted((roles - {"Stock User", "Sales User", "Purchase User", "Accounts User"}) | allowed)
        frappe.get_doc({"doctype": "Custom Role", "report": report, "ref_doctype": frappe.db.get_value("Report", report, "ref_doctype"),
                        "roles": [{"role": r} for r in keep]}).insert(ignore_permissions=True)
    frappe.clear_cache()


WORKSPACE = "妮菈"
WORKSPACE_CARDS = [  # (卡片, [(類型, 目標, 名稱)])
    ("門市", [("Page", "nila-store-sale", "門市銷售"), ("Page", "nila-sales-report", "消費報表"), ("Page", "nila-barcode", "條碼")]),
    ("庫存與訂單", [("Page", "nila-stock-matrix", "庫存表"), ("Page", "nila-replenish", "補貨建議"),
                 ("DocType", "Sales Order", "銷售訂單"), ("DocType", "Stock Reconciliation", "盤點")]),
    ("商品與會員", [("Page", "nila-new-style", "新增款式"), ("Page", "nila-item-import", "商品匯入匯出"),
                 ("DocType", "Customer", "會員與客戶"), ("Page", "nila-member-import", "會員匯入")]),
    ("管理", [("DocType", "Nila Lottery", "抽獎活動"), ("Page", "nila-shopline", "SHOPLINE 官網訂單"),
            ("Page", "nila-accounts", "帳號管理")]),
]


def _ensure_workspace():
    """「妮菈」首頁：各層級只會看到自己有權限的功能。每次升級依最新清單更新。"""
    import json

    links, content = [], []
    for card, items in WORKSPACE_CARDS:
        items = [(kind, target, label) for kind, target, label in items if frappe.db.exists(kind, target)]  # 更新前還沒建立的先略過
        if not items:
            continue
        links.append({"type": "Card Break", "label": card, "link_count": len(items)})
        links += [{"type": "Link", "label": label, "link_type": kind, "link_to": target} for kind, target, label in items]
        content.append({"id": frappe.generate_hash(length=10), "type": "card", "data": {"card_name": card, "col": 4}})
    doc = frappe.get_doc("Workspace", WORKSPACE) if frappe.db.exists("Workspace", WORKSPACE) else frappe.new_doc("Workspace")
    doc.update({"label": WORKSPACE, "title": WORKSPACE, "module": "Nila", "public": 1, "icon": "sell", "sequence_id": 0.5,
                "content": json.dumps(content, ensure_ascii=False)})
    doc.set("links", links)
    doc.flags.ignore_permissions = True
    doc.save() if not doc.is_new() else doc.insert()


def _ensure_retail(company, stores):
    """會員客戶群組、門市散客與官網散客、每個門市的收銀設定（付款方式：現金）。"""
    if not frappe.db.exists("Customer Group", MEMBER_GROUP):
        frappe.get_doc({"doctype": "Customer Group", "customer_group_name": MEMBER_GROUP,
                        "parent_customer_group": "All Customer Groups"}).insert(ignore_permissions=True)
    for name in DEFAULT_CUSTOMERS:
        if not frappe.db.exists("Customer", name):
            frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Individual",
                            "customer_group": "Individual" if frappe.db.exists("Customer Group", "Individual")
                            else "All Customer Groups"}).insert(ignore_permissions=True)
    from nila_app.retail import pos_profile

    for store in stores:
        if frappe.db.exists("Warehouse", store):
            pos_profile(store)


def _ensure_default_warehouse(company, hq, abbr):
    """預設倉庫改為總公司；停用沒有庫存異動的英文預設倉庫。"""
    if frappe.db.get_single_value("Stock Settings", "default_warehouse") != hq:
        frappe.db.set_single_value("Stock Settings", "default_warehouse", hq)
    group = frappe.get_doc("Item Group", ITEM_GROUP)
    row = next((d for d in group.item_group_defaults if d.company == company), None)
    if not row or row.default_warehouse != hq:
        if not row:
            row = group.append("item_group_defaults", {"company": company})
        row.default_warehouse = hq
        group.save()
    for name in DEFAULT_WAREHOUSES:
        wh = f"{name} - {abbr}"
        if (frappe.db.get_value("Warehouse", wh, "disabled") == 0
                and not frappe.db.exists("Stock Ledger Entry", {"warehouse": wh})
                and not frappe.db.exists("Company", {"default_in_transit_warehouse": wh})):
            frappe.db.set_value("Warehouse", wh, "disabled", 1)
            log(f"✓ 停用預設倉庫：{wh}")


def _ensure_attribute(name, values):
    if frappe.db.exists("Item Attribute", name):
        doc = frappe.get_doc("Item Attribute", name)
        have = {v.attribute_value for v in doc.item_attribute_values}
        missing = [(v, a) for v, a in values if v not in have]
        if missing:
            for v, a in missing:
                doc.append("item_attribute_values", {"attribute_value": v, "abbr": a})
            doc.save()
    elif values:
        frappe.get_doc({"doctype": "Item Attribute", "attribute_name": name,
                        "item_attribute_values": [{"attribute_value": v, "abbr": a} for v, a in values]}).insert()


def _ensure_terms():
    path = os.path.join(os.path.dirname(__file__), "terms.csv")
    changed = False
    for src, dst in read_terms(path):
        name = frappe.db.get_value("Translation", {"language": "zh-TW", "source_text": src}, "name")
        if not name:
            frappe.get_doc({"doctype": "Translation", "language": "zh-TW", "source_text": src, "translated_text": dst}).insert()
            changed = True
    if changed:
        frappe.clear_cache()
