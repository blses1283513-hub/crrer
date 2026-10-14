"""商品（款式與規格）：欄位同步、售價同步、狀態檢查、新增款式。

- 成本、官網售價、實體售價、商品狀態在「款式」（商品範本）上修改，自動套用到所有規格（變體）。
- 規格的這些欄位唯讀；售價（Item Price）只能由款式同步，不能在規格上單獨修改。
- 停售、停產的規格不能建立銷售訂單；門市（POS、銷售發票）仍可賣，用來出清庫存。
"""

import frappe
from frappe import _

from nila_app import perms
from nila_app.catalog import (
    NO_ORDER_STATUSES,
    NO_REPLENISH_STATUSES,
    CatalogError,
    clean_style,
    next_style_code,
    variant_name,
)

ITEM_GROUP = "穿戴甲"
UOM = "件"
SHAPE_ATTR = "甲型"
SIZE_ATTR = "尺寸"
WEB_PRICE_LIST = "官網售價"
STORE_PRICE_LIST = "實體售價"
STYLE_FIELDS = ["nila_status", "nila_cost", "nila_web_price", "nila_store_price"]


# ---------- 欄位同步 ----------

def item_validate(doc, method=None):
    if doc.variant_of:
        style = frappe.db.get_value("Item", doc.variant_of, ["item_name", *STYLE_FIELDS], as_dict=True)
        if style:
            for f in STYLE_FIELDS:
                doc.set(f, style.get(f))
            attrs = {a.attribute: a.attribute_value for a in doc.attributes}
            doc.nila_shape = attrs.get(SHAPE_ATTR)
            doc.nila_size = attrs.get(SIZE_ATTR)
            if doc.nila_shape and doc.nila_size:
                doc.item_name = variant_name(style.item_name, doc.nila_shape, doc.nila_size)
            if style.nila_cost:
                doc.valuation_rate = style.nila_cost
        if (doc.nila_reorder_target or 0) < 0:
            frappe.throw(_("補貨目標不可小於 0"))
    elif doc.has_variants:
        for f, label in [("nila_cost", "成本"), ("nila_web_price", "官網售價"), ("nila_store_price", "實體售價")]:
            if (doc.get(f) or 0) < 0:
                frappe.throw(_("{0}不可小於 0").format(label))


def item_on_update(doc, method=None):
    if doc.has_variants:
        sync_style(doc.name)
    elif doc.variant_of:
        _sync_prices(doc.name, doc.nila_web_price, doc.nila_store_price)


def sync_style(style):
    """把款式的狀態、成本、售價、名稱套用到全部規格（直接寫入，不逐一重存，數量多也很快）。"""
    s = frappe.db.get_value("Item", style, ["item_name", *STYLE_FIELDS], as_dict=True)
    for v in frappe.get_all("Item", filters={"variant_of": style},
                            fields=["name", "item_name", "nila_shape", "nila_size", "valuation_rate", *STYLE_FIELDS]):
        changes = {f: s.get(f) for f in STYLE_FIELDS if v.get(f) != s.get(f)}
        if v.nila_shape and v.nila_size:
            name = variant_name(s.item_name, v.nila_shape, v.nila_size)
            if v.item_name != name:
                changes["item_name"] = name
        if s.nila_cost and v.valuation_rate != s.nila_cost:
            changes["valuation_rate"] = s.nila_cost
        if changes:
            frappe.db.set_value("Item", v.name, changes)
        _sync_prices(v.name, s.nila_web_price, s.nila_store_price)


def _sync_prices(item_code, web, store):
    for price_list, rate in [(WEB_PRICE_LIST, web), (STORE_PRICE_LIST, store)]:
        if rate in (None, ""):
            continue
        name = frappe.db.get_value("Item Price", {"item_code": item_code, "price_list": price_list}, "name")
        if name:
            if frappe.db.get_value("Item Price", name, "price_list_rate") == rate:
                continue
            doc = frappe.get_doc("Item Price", name)
            doc.price_list_rate = rate
        else:
            doc = frappe.get_doc({"doctype": "Item Price", "item_code": item_code, "price_list": price_list,
                                  "price_list_rate": rate})
        doc.flags.nila_sync = True
        doc.save(ignore_permissions=True)


def item_price_validate(doc, method=None):
    if doc.flags.nila_sync or doc.price_list not in (WEB_PRICE_LIST, STORE_PRICE_LIST):
        return
    style = frappe.db.get_value("Item", doc.item_code, "variant_of")
    if style:
        frappe.throw(_("{0}請在款式 {1} 修改，會自動套用到所有規格").format(doc.price_list, style),
                     title=_("售價由款式統一設定"))


# ---------- 狀態 ----------

def sales_order_validate(doc, method=None):
    if doc.flags.get("nila_shopline"):
        return  # SHOPLINE 官網已經賣出的訂單照樣建立（請在官網下架停售的商品）
    codes = list({d.item_code for d in doc.items if d.item_code})
    if not codes:
        return
    blocked = frappe.get_all("Item", filters={"name": ["in", codes], "nila_status": ["in", list(NO_ORDER_STATUSES)]},
                             fields=["name", "nila_status"])
    if blocked:
        lines = "<br>".join(f"{b.name}（{b.nila_status}）" for b in sorted(blocked, key=lambda b: b.name))
        frappe.throw(_("以下商品已停售或停產，不能建立訂單：<br>{0}").format(lines), title=_("商品不能接單"))


def replenishable_filters():
    """可補貨的規格（給補貨計算使用）：排除停產與停用的商品。"""
    return {"variant_of": ["is", "set"], "disabled": 0, "nila_status": ["not in", list(NO_REPLENISH_STATUSES)]}


# ---------- 新增款式 ----------

def _attribute_values(attr):
    return frappe.get_all("Item Attribute Value", filters={"parent": attr}, pluck="attribute_value", order_by="idx")


@frappe.whitelist()
def get_style_options():
    """新增款式頁面需要的選項：甲型、尺寸、建議的款式編號。"""
    perms.require("item_manage")
    return {"shapes": _attribute_values(SHAPE_ATTR), "sizes": _attribute_values(SIZE_ATTR),
            "next_code": suggest_code()}


def suggest_code():
    return next_style_code(frappe.get_all("Item", filters={"has_variants": 1}, pluck="name"))


@frappe.whitelist()
def create_style(data):
    """建立款式與勾選的規格。全部成功才寫入；任何一筆失敗就全部取消。回傳 {code, variants}。"""
    perms.require("item_manage")
    data = frappe.parse_json(data)
    try:
        style = clean_style(data, _attribute_values(SHAPE_ATTR), _attribute_values(SIZE_ATTR))
    except CatalogError as e:
        frappe.throw(str(e), title=_("資料有誤"))

    code = style["code"]
    if code:
        if frappe.db.exists("Item", code):
            frappe.throw(_("款式編號 {0} 已經存在").format(code), title=_("資料有誤"))
    else:
        code = suggest_code()
        while frappe.db.exists("Item", code):  # 編號被其他商品占用時往後找
            code = next_style_code([code])

    frappe.db.savepoint("nila_create_style")
    try:
        frappe.get_doc({
            "doctype": "Item", "item_code": code, "item_name": style["name"], "item_group": ITEM_GROUP,
            "stock_uom": UOM, "is_stock_item": 1, "include_item_in_manufacturing": 0,
            "has_variants": 1, "variant_based_on": "Item Attribute",
            "attributes": [{"attribute": SHAPE_ATTR}, {"attribute": SIZE_ATTR}],
            "nila_status": style["status"], "nila_cost": style["cost"],
            "nila_web_price": style["web_price"], "nila_store_price": style["store_price"],
        }).insert()
        variants = _make_variants(code, style["cells"], style["targets"])
    except Exception:
        frappe.db.rollback(save_point="nila_create_style")
        raise
    return {"code": code, "variants": variants}


@frappe.whitelist()
def add_variants(style, cells, targets=None):
    """在既有款式加入新的甲型 × 尺寸。已存在的組合會略過。回傳新增的規格料號。"""
    perms.require("item_manage")
    if not frappe.db.get_value("Item", style, "has_variants"):
        frappe.throw(_("{0} 不是款式").format(style))
    s = frappe.db.get_value("Item", style, ["item_name", *STYLE_FIELDS], as_dict=True)
    data = {"name": s.item_name, "cost": s.nila_cost, "web_price": s.nila_web_price,
            "store_price": s.nila_store_price, "status": s.nila_status,
            "cells": frappe.parse_json(cells), "targets": frappe.parse_json(targets or "{}")}
    try:
        clean = clean_style(data, _attribute_values(SHAPE_ATTR), _attribute_values(SIZE_ATTR))
    except CatalogError as e:
        frappe.throw(str(e), title=_("資料有誤"))
    have = {(v.nila_shape, v.nila_size) for v in
            frappe.get_all("Item", filters={"variant_of": style}, fields=["nila_shape", "nila_size"])}
    cells = [c for c in clean["cells"] if c not in have]
    if not cells:
        frappe.throw(_("勾選的甲型 × 尺寸都已經存在"))
    frappe.db.savepoint("nila_add_variants")
    try:
        return _make_variants(style, cells, clean["targets"])
    except Exception:
        frappe.db.rollback(save_point="nila_add_variants")
        raise


def _make_variants(style, cells, targets):
    from erpnext.controllers.item_variant import create_variant

    made = []
    for shape, size in cells:
        v = create_variant(style, {SHAPE_ATTR: shape, SIZE_ATTR: size})
        v.nila_reorder_target = targets.get(shape) or 0
        v.insert()
        made.append(v.name)
    return made
