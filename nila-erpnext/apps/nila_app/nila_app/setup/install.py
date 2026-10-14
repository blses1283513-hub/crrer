"""網站基本設定：安裝、升級（migrate）時自動執行；也可手動執行：

    bench --site <網站> execute nila_app.setup.install.setup_site

全部可重複執行：已存在的資料不會重複建立，也不會刪除或改動已在使用的資料。
需要 sites/nila-config.json（由安裝腳本產生）才會建立公司與倉庫；沒有設定檔時只建立與公司無關的部分。
"""

import os

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from nila_app.catalog import STATUSES
from nila_app.setup.config import TRANSIT, ConfigError, check_shape_changes, load_config, read_terms

ITEM_GROUP = "穿戴甲"
UOM = "件"
PRICE_LISTS = ["官網售價", "實體售價"]
SHAPE_ATTR = "甲型"
SIZE_ATTR = "尺寸"

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
         "read_only_depends_on": _ON_STYLE, "non_negative": 1},
        {"fieldname": "nila_web_price", "label": "官網售價", "fieldtype": "Currency", "insert_after": "nila_cost",
         "read_only_depends_on": _ON_STYLE, "non_negative": 1},
        {"fieldname": "nila_store_price", "label": "實體售價", "fieldtype": "Currency", "insert_after": "nila_web_price",
         "read_only_depends_on": _ON_STYLE, "non_negative": 1, "in_list_view": 1,
         "description": "在款式修改成本與售價，所有規格會自動套用"},
    ]
}
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


def _ensure_item_settings():
    """商品清單顯示「款式」欄；款式的補貨設定不複製到規格；不自動從交易新增售價（售價只由款式同步）。"""
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter

    if frappe.db.get_value("Property Setter", {"doc_type": "Item", "field_name": "variant_of",
                                                   "property": "in_list_view"}, "value") != "1":
        make_property_setter("Item", "variant_of", "in_list_view", 1, "Check", validate_fields_for_doctype=False)
    frappe.db.delete("Variant Field", {"parent": "Item Variant Settings", "field_name": ["in", NOT_COPIED_TO_VARIANTS]})
    if frappe.db.get_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing"):
        frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 0)


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
