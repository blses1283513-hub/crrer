"""P1 商品功能的整合測試：在已安裝的正式版 ERPNext 容器內執行，結束時全部復原（不留下測試資料）。

    docker compose cp live_products.py backend:/tmp/live_products.py
    docker compose exec backend bash -c "cd sites && ../env/bin/python /tmp/live_products.py nila"
"""

import sys
from unittest import mock

import frappe

failures = []


def check(label, ok, detail=""):
    print(f"{'✓' if ok else '✗'} {label}{'：' + str(detail) if detail not in ('', None) else ''}", flush=True)
    if not ok:
        failures.append(label)


def raises(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception as e:  # noqa: BLE001
        frappe.clear_messages()
        return str(e)
    return None


def price(item, pl):
    return frappe.db.get_value("Item Price", {"item_code": item, "price_list": pl}, "price_list_rate")


def run():
    from nila_app import products as p

    abbr = frappe.db.get_value("Company", {}, "abbr")
    company = frappe.db.get_value("Company", {}, "name")
    hq = f"總公司 - {abbr}"

    # P1-1 預設倉庫
    check("預設倉庫是總公司", frappe.db.get_single_value("Stock Settings", "default_warehouse") == hq)
    disabled = frappe.get_all("Warehouse", filters={"disabled": 1}, pluck="name")
    check("英文預設倉庫已停用", all(f"{w} - {abbr}" in disabled for w in ["Stores", "Finished Goods", "Work In Progress", "Goods In Transit"]), disabled)
    check("總公司、分公司、在途未停用", not any(w in disabled for w in [hq, f"在途 - {abbr}"]))
    check("不從交易自動新增售價", not frappe.db.get_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing"))
    check("補貨設定不從款式複製到規格", not frappe.db.exists("Variant Field", {"field_name": "reorder_levels"}))

    opts = p.get_style_options()
    shapes, sizes = opts["shapes"], opts["sizes"]
    check("新增款式選項：甲型與尺寸", len(shapes) >= 2 and sizes == ["XS", "S", "M", "L"], opts)

    # P1-3 新增款式（自動編號）
    cells = [{"shape": shapes[0], "size": s} for s in sizes] + [{"shape": shapes[1], "size": s} for s in sizes[:2]]
    res = p.create_style({"name": "測試櫻花", "cost": 80, "web_price": 390, "store_price": 350,
                          "cells": cells, "targets": {shapes[0]: 12, shapes[1]: 6}})
    code = res["code"]
    check("自動款式編號為 4 位數字", len(code) == 4 and code.isdigit(), code)
    check("建立 6 個規格", len(res["variants"]) == 6, res["variants"])
    first = res["variants"][0]
    sa = frappe.db.get_value("Item Attribute Value", {"parent": "甲型", "attribute_value": shapes[0]}, "abbr")
    check("規格料號：款式-甲型縮寫-尺寸", first == f"{code}-{sa}-XS", first)
    v = frappe.get_doc("Item", first)
    check("規格名稱、甲型、尺寸", (v.item_name, v.nila_shape, v.nila_size) == (f"測試櫻花-{shapes[0]}-XS", shapes[0], "XS"),
          (v.item_name, v.nila_shape, v.nila_size))
    check("規格帶入成本、狀態、估價", (v.nila_cost, v.nila_status, v.valuation_rate) == (80, "上架", 80))
    check("補貨目標依甲型", v.nila_reorder_target == 12 and
          frappe.db.get_value("Item", res["variants"][-1], "nila_reorder_target") == 6)
    check("兩個價格表都有售價", (price(first, "官網售價"), price(first, "實體售價")) == (390, 350))

    # 款式名稱可重複，編號自動往後
    res2 = p.create_style({"name": "測試櫻花", "cost": 1, "web_price": 1, "store_price": 1,
                           "cells": [{"shape": shapes[0], "size": "M"}]})
    check("款式名稱可重複、編號不重複", res2["code"] == str(int(code) + 1).zfill(4), res2["code"])

    # 指定編號
    err = raises(p.create_style, {"code": code, "name": "x", "cost": 1, "web_price": 1, "store_price": 1,
                                  "cells": [{"shape": shapes[0], "size": "M"}]})
    check("指定已存在的編號會被拒絕", err and "已經存在" in err, err)
    err = raises(p.create_style, {"name": "", "cost": -1, "web_price": "abc", "store_price": 1, "cells": []})
    check("輸入錯誤一次列出", err and all(k in err for k in ["款式名稱必填", "成本不可小於 0", "官網售價必須是數字", "至少要勾選"]), err)

    # 全部成功才寫入
    from erpnext.controllers import item_variant
    real = item_variant.create_variant
    calls = {"n": 0}

    def flaky(*a, **k):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("模擬第 2 個規格失敗")
        return real(*a, **k)

    with mock.patch.object(item_variant, "create_variant", flaky):
        err = raises(p.create_style, {"code": "T9999", "name": "失敗款", "cost": 1, "web_price": 1, "store_price": 1,
                                      "cells": [{"shape": shapes[0], "size": "XS"}, {"shape": shapes[0], "size": "S"}]})
    check("中途失敗時整個款式都不建立", err and not frappe.db.exists("Item", "T9999")
          and not frappe.db.exists("Item", {"variant_of": "T9999"}), err)

    # P1-2/P1-4 在款式修改，同步到全部規格
    tpl = frappe.get_doc("Item", code)
    tpl.nila_cost, tpl.nila_web_price, tpl.nila_store_price, tpl.nila_status = 90, 420, 380, "停售"
    tpl.item_name = "測試櫻花新"
    tpl.save()
    rows = frappe.get_all("Item", filters={"variant_of": code}, fields=["name", "item_name", "nila_cost", "nila_status", "valuation_rate"])
    check("成本、狀態、名稱同步到全部規格", all(r.nila_cost == 90 and r.nila_status == "停售" and r.valuation_rate == 90
                                     and r.item_name.startswith("測試櫻花新-") for r in rows), rows[:2])
    check("售價同步到全部規格", all(price(r.name, "官網售價") == 420 and price(r.name, "實體售價") == 380 for r in rows))
    check("修改紀錄有留下", frappe.db.exists("Version", {"ref_doctype": "Item", "docname": code}))

    # 規格不能單獨改
    vd = frappe.get_doc("Item", first)
    vd.nila_cost = 1
    vd.nila_status = "上架"
    vd.save()
    check("規格上改成本、狀態會被款式的值蓋回", (vd.nila_cost, vd.nila_status) == (90, "停售"))
    ip = frappe.get_doc("Item Price", {"item_code": first, "price_list": "實體售價"})
    ip.price_list_rate = 1
    err = raises(ip.save)
    check("規格上不能單獨改售價", err and "款式" in err, err)

    # 加入新的甲型 × 尺寸
    added = p.add_variants(code, [{"shape": shapes[1], "size": "S"}, {"shape": shapes[1], "size": "M"}], {shapes[1]: 6})
    check("既有款式加入新規格（已有的略過）", len(added) == 1 and added[0].endswith("-M"), added)
    nv = frappe.get_doc("Item", added[0])
    check("新規格帶入款式目前的設定與售價", nv.nila_cost == 90 and nv.nila_status == "停售" and price(nv.name, "實體售價") == 380)
    err = raises(p.add_variants, code, [{"shape": shapes[1], "size": "M"}])
    check("全部都已存在時提示", err and "已經存在" in err, err)

    # P1-5 停售／停產不能建立銷售訂單；門市仍可賣
    cust = frappe.get_doc({"doctype": "Customer", "customer_name": "測試客戶P1", "customer_type": "Individual"}).insert()
    so = {"doctype": "Sales Order", "customer": cust.name, "company": company, "transaction_date": frappe.utils.nowdate(),
          "delivery_date": frappe.utils.nowdate(), "set_warehouse": hq,
          "items": [{"item_code": first, "qty": 1, "rate": 420}]}
    err = raises(frappe.get_doc(dict(so)).insert)
    check("停售商品不能建立銷售訂單", err and "停售" in err, err)
    ok_item = res2["variants"][0]
    err = raises(frappe.get_doc({**so, "items": [{"item_code": ok_item, "qty": 1, "rate": 1}]}).insert)
    check("上架商品可以建立銷售訂單", err is None, err)
    tpl2 = frappe.get_doc("Item", res2["code"])
    tpl2.nila_status = "停產"
    tpl2.save()
    err = raises(frappe.get_doc({**so, "items": [{"item_code": ok_item, "qty": 1, "rate": 1}]}).insert)
    check("停產商品不能建立銷售訂單", err and "停產" in err, err)
    err = raises(frappe.get_doc({"doctype": "Sales Invoice", "customer": cust.name, "company": company,
                                 "update_stock": 0, "items": [{"item_code": ok_item, "qty": 1, "rate": 1}]}).insert)
    check("停產商品在門市（銷售發票）仍可賣", err is None, err)
    rep = frappe.get_all("Item", filters=p.replenishable_filters(), pluck="name")
    check("停產商品不在補貨範圍、停售仍會補貨", ok_item not in rep and first in rep)


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "nila"
    frappe.init(site=site, sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        run()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        check("執行過程沒有錯誤", False, e)
    finally:
        frappe.db.rollback()
        frappe.destroy()
    print(f"\n{'全部通過' if not failures else '未通過：' + '、'.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
