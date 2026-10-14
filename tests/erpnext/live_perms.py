"""P6（帳號、5 個層級的權限、成本欄位、抽獎）的整合測試：在已安裝的正式版 ERPNext 容器內執行，結束時全部復原。

    docker compose cp live_perms.py backend:/tmp/live_perms.py
    docker compose exec backend bash -c "cd sites && ../env/bin/python /tmp/live_perms.py nila"
"""

import sys

import frappe

failures = []
PW = "Nila-Test-2026!qz"  # 測試用，夠強的密碼


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


def as_user(user, fn, *args, **kwargs):
    frappe.set_user(user)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user("Administrator")


def denied(user, fn, *args, **kwargs):
    err = raises(as_user, user, fn, *args, **kwargs)
    return bool(err) and ("沒有權限" in err or "不能" in err or "Not permitted" in err or "permission" in err.lower())


def run():
    from nila_app import accounts, dispatch, importer, lottery, matrix, products, replenish, retail, salesreport, stock
    from nila_app import levels as L

    whs = stock.warehouses(include_transit=False)
    hq = stock.hq_warehouse()
    a, b = [w["name"] for w in whs if not w["hq"]][:2]

    # ---------- 基本設定 ----------
    check("可以用帳號（不需信箱）登入", frappe.db.get_single_value("System Settings", "allow_login_using_user_name") == 1)
    ws = frappe.get_doc("Workspace", "妮菈")
    check("「妮菈」首頁有門市銷售、庫存表、抽獎、帳號管理",
          {"nila-store-sale", "nila-stock-matrix", "Nila Lottery", "nila-accounts"} <= {l.link_to for l in ws.links if l.type == "Link"})
    check("盤點：總公司作業、店長可以建立送出",
          all(frappe.db.get_value("Custom DocPerm", {"parent": "Stock Reconciliation", "role": r, "permlevel": 0}, "submit")
              for r in (L.HQ_STAFF, L.STORE_LEAD)))
    pl = frappe.get_meta("Item").get_field("valuation_rate").permlevel
    check("成本欄位放在權限層級 5", pl == 5 and frappe.get_meta("Item").get_field("nila_cost").permlevel == 5
          and frappe.get_meta("Stock Entry Detail").get_field("basic_rate").permlevel == 5, pl)

    # ---------- 帳號管理 ----------
    def make(username, level, stores=(), name="測試"):
        return accounts.save_account({"full_name": f"{name}{username}", "username": username, "level": level,
                                      "stores": list(stores), "password": PW})
    u_admin = make("t.admin", L.ADMIN)["name"]
    u_mgr = make("t.mgr", L.MANAGER)["name"]
    u_hq = make("t.hq", L.HQ_STAFF, [a])["name"]
    u_lead = make("t.lead", L.STORE_LEAD, [a])["name"]
    u_staff = make("t.staff", L.STORE_STAFF, [a])["name"]
    rows = {r["name"]: r for r in accounts.list_accounts()["accounts"]}
    check("新增 5 個層級的帳號", all(rows[u]["level"] == lv for u, lv in
                              [(u_admin, L.ADMIN), (u_mgr, L.MANAGER), (u_hq, L.HQ_STAFF), (u_lead, L.STORE_LEAD), (u_staff, L.STORE_STAFF)]))
    check("帳號＝登入名稱、信箱用內部位址", frappe.db.get_value("User", u_staff, ["username", "email"]) == ("t.staff", "t.staff@nila.local"))
    check("總公司層級不綁門市（選了也不存）", rows[u_hq]["stores"] == [] and rows[u_lead]["stores"] == [a])
    check("店員沒有 ERPNext 標準角色", set(frappe.get_roles(u_staff)) & set(L.STANDARD_ROLES) == set())
    check("總公司作業帶 Stock User、Sales User，沒有可看成本的角色",
          {"Stock User", "Sales User"} <= set(frappe.get_roles(u_hq)) and not set(frappe.get_roles(u_hq)) & set(L.COST_ROLES))
    from frappe.utils.password import check_password
    check("初始密碼可以登入", check_password(u_staff, PW) == u_staff)
    err = raises(make, "t.weak", L.STORE_STAFF, [a])
    check("新帳號沒有密碼：拒絕", raises(accounts.save_account, {"full_name": "x", "username": "t.nopw", "level": L.HQ_STAFF})
          and "初始密碼" in raises(accounts.save_account, {"full_name": "x", "username": "t.nopw", "level": L.HQ_STAFF}))
    err = raises(accounts.save_account, {"full_name": "弱", "username": "t.weak", "level": L.HQ_STAFF, "password": "123"})
    check("太弱的密碼：拒絕", bool(err), err)
    err = raises(accounts.save_account, {"full_name": "重", "username": "t.staff", "level": L.HQ_STAFF, "password": PW})
    check("帳號重複：拒絕", err and "已經有人使用" in err, err)
    err = raises(accounts.save_account, {"full_name": "店", "username": "t.nostore", "level": L.STORE_STAFF, "password": PW})
    check("店員沒選門市：拒絕", err and "至少要選一間門市" in err, err)
    accounts.save_account({"name": u_staff, "full_name": "測試店員", "username": "t.staff", "level": L.STORE_LEAD, "stores": [a, b]})
    check("改成店長、兩間門市：角色與門市一起更新", L.level_of(frappe.get_roles(u_staff)) == L.STORE_LEAD and "Stock User" in frappe.get_roles(u_staff)
          and L.STORE_STAFF not in frappe.get_roles(u_staff) and accounts._user_rows([u_staff])[0]["stores"] == [a, b])
    accounts.save_account({"name": u_staff, "full_name": "測試店員", "username": "t.staff", "level": L.STORE_STAFF, "stores": [a]})
    check("改回店員：移除 Stock User 與多的門市", "Stock User" not in frappe.get_roles(u_staff) and accounts._user_rows([u_staff])[0]["stores"] == [a])
    accounts.reset_password(u_staff, PW + "2")
    check("重設密碼", check_password(u_staff, PW + "2") == u_staff)
    accounts.set_enabled(u_staff, 0)
    check("停用帳號", frappe.db.get_value("User", u_staff, "enabled") == 0)
    accounts.set_enabled(u_staff, 1)
    err = raises(as_user, u_admin, accounts.set_enabled, u_admin, 0)
    check("管理員不能停用自己", err and "不能停用自己" in err, err)
    err = raises(as_user, u_admin, accounts.save_account, {"name": u_admin, "full_name": "x", "username": "t.admin", "level": L.MANAGER})
    check("管理員不能把自己降級", err and "不能把自己改成" in err, err)
    check("營運主管不能管理帳號", denied(u_mgr, accounts.list_accounts))
    err = raises(accounts.save_account, {"name": "Administrator", "full_name": "x", "username": "admin", "level": L.ADMIN})
    check("不能修改內建 Administrator", err and "Administrator" in err, err)

    # ---------- 各層級能做與不能做 ----------
    check("店員：門市銷售只有自己的門市", [s["value"] for s in as_user(u_staff, retail.sale_context)["stores"]] == [a])
    m = as_user(u_staff, matrix.build, {})[0]
    labels = {r["label"] for blk in m for r in blk["rows"]}
    check("店員：庫存表只看到自己門市，沒有全公司合計與建議補貨", labels <= {"分公司A"}, labels)
    m = as_user(u_hq, matrix.build, {})[0]
    check("總公司作業：庫存表有全公司合計", any(r["label"] == "全公司合計" for blk in m for r in blk["rows"]))
    check("店員、店長不能看補貨建議", denied(u_staff, replenish.get_suggestions) and denied(u_lead, replenish.get_suggestions))
    check("總公司作業可以看補貨建議，但不能建立補貨單",
          as_user(u_hq, replenish.get_suggestions)["can_order"] is False
          and denied(u_hq, replenish.create_material_request, [{"item": "x", "qty": 1, "suggest": 1}]))
    check("店長不能建立調撥單、不能看訂單調度面板",
          denied(u_lead, replenish.create_transfers, [{"item": "x", "from": hq, "to": a, "qty": 1, "suggest": 1}])
          and denied(u_lead, dispatch.order_panel, {"docstatus": 0, "items": []}))
    check("總公司作業不能新增款式、不能匯入匯出商品",
          denied(u_hq, products.get_style_options) and denied(u_hq, importer.download_template))
    check("營運主管可以新增款式", as_user(u_mgr, products.get_style_options)["sizes"])
    check("總公司作業、店長不能開抽獎", denied(u_hq, lottery.preview, "x") and denied(u_lead, lottery.preview, "x"))
    check("店員不能看消費報表、店長可以（自己的門市）", denied(u_staff, salesreport.get_report, {})
          and as_user(u_lead, salesreport.get_options)["stores"] == [{"value": a, "label": "分公司A"}])

    # ERPNext 原本的畫面
    def perm(user, doctype, ptype="read"):
        return as_user(user, frappe.has_permission, doctype, ptype)
    check("店員看不到 ERPNext 的訂單、商品、盤點", not perm(u_staff, "Sales Order") and not perm(u_staff, "Item")
          and not perm(u_staff, "Stock Reconciliation"))
    check("總公司作業可以建立訂單、調撥、盤點", perm(u_hq, "Sales Order", "create") and perm(u_hq, "Stock Entry", "create")
          and perm(u_hq, "Stock Reconciliation", "submit"))
    check("店長可以盤點、不能建立訂單", perm(u_lead, "Stock Reconciliation", "create") and not perm(u_lead, "Sales Order", "create"))
    check("只有能看成本的層級可以開含金額的庫存報表",
          not as_user(u_hq, frappe.get_doc("Report", "Stock Ledger").is_permitted)
          and not as_user(u_lead, frappe.get_doc("Report", "Stock Balance").is_permitted)
          and as_user(u_mgr, frappe.get_doc("Report", "Stock Ledger").is_permitted)
          and as_user(u_hq, frappe.get_doc("Report", "Stock Projected Qty").is_permitted))

    # 成本欄位
    opts = products.get_style_options()
    style = products.create_style({"name": "權限測試款", "cost": 123, "web_price": 390, "store_price": 350,
                                   "cells": [{"shape": opts["shapes"][0], "size": opts["sizes"][0]}], "targets": {}})
    item = style["variants"][0]
    from frappe.client import get as client_get
    seen = as_user(u_hq, client_get, "Item", item)
    check("總公司作業讀商品：看不到成本", not seen.get("nila_cost") and not seen.get("valuation_rate"), (seen.get("nila_cost"), seen.get("valuation_rate")))
    seen = as_user(u_mgr, client_get, "Item", item)
    check("營運主管讀商品：看得到成本", seen.get("nila_cost") == 123, seen.get("nila_cost"))
    retail_opening = frappe.get_doc({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "purpose": "Material Receipt",
                                     "items": [{"item_code": item, "qty": 5, "t_warehouse": hq, "basic_rate": 123}]}).insert()
    retail_opening.submit()
    se = stock.create_transfer(hq, a, [(item, 2)])
    seen = as_user(u_hq, client_get, "Stock Entry", se)
    check("總公司作業讀調撥單：看不到金額", not seen["items"][0].get("basic_rate") and not seen.get("total_outgoing_value"),
          (seen["items"][0].get("basic_rate"), seen.get("total_outgoing_value")))
    check("店員看異動明細：只看到自己門市", all(r["warehouse"] == "分公司A" for r in as_user(u_staff, stock.history, item))
          and denied(u_staff, stock.history, item, hq))
    err = raises(as_user, u_staff, stock.receive_transfer, se)
    check("店員不能到貨入庫", err and "沒有權限" in err, err)
    se_b = stock.create_transfer(hq, b, [(item, 1)])
    check("店長不能收別家門市的貨", denied(u_lead, stock.receive_transfer, se_b))
    as_user(u_lead, stock.receive_transfer, se)
    check("店長收自己門市的貨", stock.num(frappe.db.get_value("Bin", {"item_code": item, "warehouse": a}, "actual_qty")) == 2)
    return {"item": item, "a": a, "b": b, "hq": hq, "u_hq": u_hq, "u_mgr": u_mgr}


def test_lottery(ctx):
    from nila_app import lottery, retail

    item, a, b, hq = ctx["item"], ctx["a"], ctx["b"], ctx["hq"]
    today = frappe.utils.nowdate()
    members = [retail.create_member(f"抽獎會員{i}", f"09770000{i:02d}")["name"] for i in range(4)]
    # 會員0：2 次 700（共 1400，A）；會員1：1 次 1750（A）；會員2：1 次 350（B）；會員3：1 次 1050（A），之後退 1050
    sales = {}
    for n, (m, store, qty) in enumerate([(0, a, 1), (0, a, 1), (1, a, 5), (2, b, 1), (3, a, 3)]):
        sales[n] = retail.checkout({"client_id": f"lot-{n}", "store": store, "member": members[m], "lines": [{"item": item, "qty": qty}]})
    row = retail.find_sales(sales[4]["name"])[0]["lines"][0]
    retail.make_return({"client_id": "lot-r", "invoice": sales[4]["name"], "mode": "goods", "lines": [{"row": row["row"], "qty": 3}]})
    web = frappe.get_doc({"doctype": "Sales Invoice", "customer": members[2], "nila_channel": "官網", "company": frappe.db.get_value("Company", {}, "name"),
                          "set_warehouse": hq, "items": [{"item_code": item, "qty": 10}]})
    web.set_missing_values()
    web.insert()
    web.submit()

    lot = frappe.get_doc({"doctype": "Nila Lottery", "title": "週年慶抽獎", "from_date": today, "to_date": today,
                          "rules": [{"rule_type": "累計消費金額", "value": "700"}], "entry_mode": "每滿 X 元 1 個名額",
                          "entry_unit": 700, "entry_cap": 2}).insert()
    r = lottery.preview(lot.name)
    got = {x["customer"]: x["entries"] for x in r["rows"]}
    check("抽獎：累計滿 700，每 700 元 1 名額、上限 2（會員0 700＝1、會員1 1750＝2；退貨歸零者、官網訂單不算）",
          got == {members[0]: 1, members[1]: 2}, (got, r["description"]))
    lot.stores = []
    lot.append("stores", {"warehouse": b})
    lot.set("rules", [])
    lot.entry_mode = "每人 1 個名額"
    lot.save()
    got = {x["customer"] for x in lottery.preview(lot.name)["rows"]}
    check("抽獎：只限分公司B、沒有條件＝有消費就有 1 個名額（官網的大筆消費不算）", got == {members[2]}, got)
    lot.set("stores", [])
    lot.set("rules", [{"rule_type": "消費次數", "value": "2"}, {"rule_type": "買過指定甲型", "value": "不存在的甲型,"
                       + frappe.db.get_value("Item", item, "nila_shape")}])
    lot.save()
    got = {x["customer"] for x in lottery.preview(lot.name)["rows"]}
    check("抽獎：條件全部符合（2 次以上＋買過指定甲型）", got == {members[0]}, got)
    snap = frappe.get_doc("Nila Lottery Snapshot", lottery.generate(lot.name))
    check("產生名單快照：人數、名額、條件文字", snap.member_count == 1 and snap.entry_total == 1 and "消費次數至少 2 次" in snap.rules_text
          and snap.entries[0].phone == "0977000000", snap.rules_text)
    row = retail.find_sales(sales[0]["name"])[0]["lines"][0]
    retail.make_return({"client_id": "lot-r2", "invoice": sales[0]["name"], "mode": "goods", "lines": [{"row": row["row"], "qty": 1}]})
    snap.reload()
    check("之後整筆退貨（消費次數變 1）：快照不變，重新預覽才會變", snap.member_count == 1 and lottery.preview(lot.name)["count"] == 0)
    snap.member_count = 99
    err = raises(snap.save)
    check("名單快照不能修改", err and "不能修改" in err, err)
    lottery.export_snapshot(snap.name)
    from io import BytesIO
    import openpyxl
    vals = list(openpyxl.load_workbook(BytesIO(frappe.response["filecontent"])).active.values)
    check("匯出名單 Excel", vals[0][1] == "週年慶抽獎" and any(v[2] == "0977000000" for v in vals[4:]), vals[:5])
    frappe.response.pop("filecontent", None)
    bad = frappe.get_doc({"doctype": "Nila Lottery", "title": "錯", "from_date": today, "to_date": today,
                          "rules": [{"rule_type": "消費次數", "value": "abc"}], "entry_mode": "每 N 次消費 1 個名額"})
    err = raises(bad.insert)
    check("條件有誤時不能儲存", err and "要填數字" in err and "大於 0" in err, err)
    check("總公司作業不能產生名單", denied(ctx["u_hq"], lottery.generate, lot.name))


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "nila"
    frappe.init(site=site, sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        ctx = run()
        test_lottery(ctx)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        check("執行過程沒有錯誤", False, e)
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
        frappe.destroy()
    print(f"\n{'全部通過' if not failures else '未通過：' + '、'.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
