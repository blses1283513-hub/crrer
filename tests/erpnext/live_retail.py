"""P5（門市銷售與會員）的整合測試：在已安裝的正式版 ERPNext 容器內執行，結束時全部復原。

    docker compose cp live_retail.py backend:/tmp/live_retail.py
    docker compose exec backend bash -c "cd sites && ../env/bin/python /tmp/live_retail.py nila"
    （大量測試：再加上筆數，例如 nila 20000）
"""

import sys

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


def make_user(email, role, store=None):
    u = frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0,
                        "roles": [{"role": role}]}).insert(ignore_permissions=True)
    if store:
        frappe.get_doc({"doctype": "User Permission", "user": u.name, "allow": "Warehouse", "for_value": store,
                        "apply_to_all_doctypes": 1}).insert(ignore_permissions=True)
    return u.name


def as_user(user, fn, *args, **kwargs):
    frappe.set_user(user)
    try:
        return fn(*args, **kwargs)
    finally:
        frappe.set_user("Administrator")


def run():
    from nila_app import products as p
    from nila_app import retail, stock
    from nila_app import retailrules as R

    def bin_qty(item, wh):
        return stock.num(frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty"))

    whs = stock.warehouses(include_transit=False)
    hq = stock.hq_warehouse()
    a, b = [w["name"] for w in whs if not w["hq"]][:2]

    # 基本設定
    check("5 個層級的角色", all(frappe.db.exists("Role", r) for r in R.LEVELS))
    check("會員群組、門市散客、官網散客", frappe.db.exists("Customer Group", "會員") and frappe.db.exists("Customer", "門市散客")
          and frappe.db.exists("Customer", "官網散客"))
    check("每個門市都有收銀設定（現金）", all(frappe.db.exists("POS Profile", f"門市-{w['label']}") for w in whs))

    opts = p.get_style_options()
    res = p.create_style({"name": "測試門市款", "cost": 100, "web_price": 390, "store_price": 350, "status": "停售",
                          "cells": [{"shape": opts["shapes"][0], "size": s} for s in opts["sizes"][:2]],
                          "targets": {opts["shapes"][0]: 5}})
    x, y = res["variants"]

    # 會員
    m1 = retail.create_member("王小美", "0912-345-678")
    check("新增會員：手機統一格式", m1["phone"] == "0912345678", m1)
    err = raises(retail.create_member, "王小美二", "+886 912 345 678")
    check("同一支手機不能重複", err and "已經是會員" in err, err)
    err = raises(retail.create_member, "李", "12345")
    check("手機格式錯誤：拒絕", err and "格式不正確" in err, err)
    err = raises(retail.create_member, "", "0911111111")
    check("姓名必填", err and "姓名必填" in err, err)
    check("用手機找會員（不同寫法）", [m["name"] for m in retail.find_member("+886912345678")] == [m1["name"]])
    check("用姓名找會員", m1["name"] in [m["name"] for m in retail.find_member("小美")])
    c = frappe.get_doc({"doctype": "Customer", "customer_name": "一般客戶", "customer_type": "Company"}).insert()
    check("一般客戶不用填手機", c.name and not c.get("nila_phone"))
    frappe.get_doc({"doctype": "Customer", "customer_name": "一般客戶二", "customer_type": "Company"}).insert()
    check("多個沒有手機的客戶不會互相衝突", True)

    # 權限與門市範圍
    staff = make_user("staff-a@example.com", R.STORE_STAFF, a)
    lead = make_user("lead-a@example.com", R.STORE_LEAD, a)
    hq_user = make_user("hq@example.com", R.HQ_STAFF)
    plain = make_user("plain@example.com", "Stock User")
    ctx = as_user(staff, retail.sale_context)
    check("店員只看到自己的門市、不能改價、不能退貨",
          [s["value"] for s in ctx["stores"]] == [a] and not ctx["can_price"] and not ctx["can_return"], ctx)
    ctx = as_user(lead, retail.sale_context)
    check("店長：自己的門市、可改價、可退貨", [s["value"] for s in ctx["stores"]] == [a] and ctx["can_price"] and ctx["can_return"])
    check("總公司作業：全部門市", len(as_user(hq_user, retail.sale_context)["stores"]) == len(whs))
    err = raises(as_user, plain, retail.sale_context)
    check("沒有妮菈層級的帳號不能用門市銷售", err and "沒有權限" in err, err)

    # 結帳
    item = retail.lookup_item(x.lower())
    check("掃碼（大小寫不同）找到規格與實體售價", item["exact"] and item["items"][0]["rate"] == 350, item)
    check("輸入部分名稱列出候選", len(retail.lookup_item("測試門市款")["items"]) == 2)
    before = bin_qty(x, a)
    r1 = as_user(staff, retail.checkout, {"client_id": "t-1", "store": a, "member": m1["name"],
                                          "lines": [{"item": x, "qty": 1}, {"item": x, "qty": 1}, {"item": y, "qty": 1}]})
    si = frappe.get_doc("Sales Invoice", r1["name"])
    check("店員結帳：停售商品門市仍可賣、已收款、扣分公司A 庫存",
          si.docstatus == 1 and si.status == "Paid" and si.nila_channel == "門市" and bin_qty(x, a) == before - 2,
          (si.status, si.grand_total, bin_qty(x, a)))
    check("收銀人員記錄實際操作的店員", si.nila_cashier == staff, si.nila_cashier)
    check("結帳金額＝實體售價 × 數量（同料號合併）", r1["total"] == 1050 and [d.qty for d in si.items] == [2, 1], r1)
    again = as_user(staff, retail.checkout, {"client_id": "t-1", "store": a, "lines": [{"item": x, "qty": 1}]})
    check("同一筆結帳重送：回傳原單、不重複扣庫存", again["name"] == r1["name"] and again["duplicate"] and bin_qty(x, a) == before - 2)
    err = raises(as_user, staff, retail.checkout, {"client_id": "t-2", "store": b, "lines": [{"item": x, "qty": 1}]})
    check("店員不能在別的門市結帳", err and "不能操作這個門市" in err, err)
    err = raises(as_user, staff, retail.checkout, {"client_id": "t-3", "store": a, "lines": [{"item": x, "qty": 1, "rate": 300}]})
    check("店員不能改價", err and "沒有改價的權限" in err, err)
    r2 = as_user(lead, retail.checkout, {"client_id": "t-4", "store": a, "lines": [{"item": x, "qty": 1, "rate": 300}]})
    check("店長可以改價；沒選會員＝門市散客", r2["total"] == 300 and frappe.db.get_value("Sales Invoice", r2["name"], "customer") == "門市散客")
    err = raises(retail.checkout, {"client_id": "t-5", "store": a, "lines": [{"item": "NOPE-1", "qty": 1}]})
    check("不存在的料號：拒絕", err and "找不到這些商品" in err, err)
    err = raises(retail.checkout, {"store": a, "lines": [{"item": x, "qty": 1}]})
    check("缺少結帳代碼：拒絕", err and "結帳代碼" in err, err)
    r3 = retail.checkout({"client_id": "t-6", "store": hq, "lines": [{"item": y, "qty": 3}]})
    check("庫存不足也能賣（負庫存）", bin_qty(y, hq) < 0 and r3["name"], bin_qty(y, hq))

    # 退貨、退款
    err = raises(as_user, staff, retail.find_sales, m1["phone"])
    check("店員不能退貨", err and "沒有權限" in err, err)
    found = as_user(lead, retail.find_sales, "0912345678")
    check("用會員手機找到銷售", [f["name"] for f in found] == [r1["name"]], [f["name"] for f in found])
    lines = {ln["item"]: ln for ln in found[0]["lines"]}
    before = bin_qty(x, a)
    ret = as_user(lead, retail.make_return, {"client_id": "t-r1", "invoice": r1["name"], "mode": "goods",
                                             "lines": [{"row": lines[x]["row"], "qty": 1, "amount": 100}], "reason": "瑕疵"})
    rdoc = frappe.get_doc("Sales Invoice", ret["name"])
    check("退貨 1 件只退 100：庫存回到分公司A、金額 −100",
          rdoc.is_return and rdoc.grand_total == -100 and bin_qty(x, a) == before + 1 and rdoc.remarks == "瑕疵",
          (rdoc.grand_total, bin_qty(x, a)))
    ref = as_user(lead, retail.make_return, {"client_id": "t-r2", "invoice": r1["name"], "mode": "refund",
                                             "lines": [{"row": lines[y]["row"], "amount": 50}]})
    check("只退款 50：庫存不變", frappe.db.get_value("Sales Invoice", ref["name"], "grand_total") == -50 and bin_qty(x, a) == before + 1)
    again = as_user(lead, retail.make_return, {"client_id": "t-r2", "invoice": r1["name"], "mode": "refund",
                                               "lines": [{"row": lines[y]["row"], "amount": 50}]})
    check("退款重送不會重複", again["duplicate"] and again["name"] == ref["name"])
    left = {ln["item"]: ln["qty"] - ln["returned"] for ln in retail.find_sales(r1["name"])[0]["lines"]}
    check("可退數量扣掉已退的", left == {x: 1, y: 0}, left)
    err = raises(as_user, lead, retail.make_return, {"client_id": "t-r3", "invoice": r1["name"], "mode": "goods",
                                                     "lines": [{"row": lines[x]["row"], "qty": 2}]})
    check("超過可退數量：拒絕", err and "最多只能再退 1 件" in err, err)
    err = raises(as_user, lead, retail.make_return, {"client_id": "t-r4", "invoice": r3["name"], "mode": "goods",
                                                     "lines": [{"row": "x", "qty": 1}]})
    check("店長不能退別的門市的銷售", err and "不能操作這個門市" in err, err)

    # 合併會員
    m2 = retail.create_member("王小美（舊）", "0922333444")
    retail.checkout({"client_id": "t-7", "store": hq, "member": m2["name"], "lines": [{"item": x, "qty": 1}]})
    err = raises(as_user, lead, retail.merge_members, m2["name"], m1["name"])
    check("店長不能合併會員", err and "沒有權限" in err, err)
    retail.merge_members(m2["name"], m1["name"])
    check("合併會員：消費紀錄移到保留的會員", not frappe.db.exists("Customer", m2["name"])
          and frappe.db.count("Sales Invoice", {"customer": m1["name"], "docstatus": 1, "is_return": 0}) == 2)
    return {"member": m1["name"], "x": x, "y": y, "a": a, "lead": lead, "staff": staff, "hq_user": hq_user}


def test_report(ctx):
    from nila_app import retail, salesreport, stock

    today = frappe.utils.nowdate()
    m, a = ctx["member"], ctx["a"]
    # 官網訂單（管道＝官網）不算會員消費
    web = frappe.get_doc({"doctype": "Sales Invoice", "customer": m, "nila_channel": "官網", "selling_price_list": "官網售價",
                          "company": frappe.db.get_value("Company", {}, "name"), "set_warehouse": stock.hq_warehouse(),
                          "items": [{"item_code": ctx["x"], "qty": 1}]})
    web.set_missing_values()
    web.insert()
    web.submit()
    data = salesreport.consumption(today, today, customers=[m])
    check("會員消費：2 次、銷售 1400、退款 150、淨額 1250（官網訂單不算）",
          data.get(m) == {"orders": 2, "gross": 1400, "refund": 150, "net": 1250, "last_date": today}, data.get(m))
    r = salesreport.build({"group": "store", "from_date": today, "to_date": today})
    by = {x["key"]: x for x in r["rows"]}
    check("依門市：分公司A 銷售 1350、退款 150、淨額 1200", (by[a]["gross"], by[a]["refund"], by[a]["net"]) == (1350, 150, 1200), by.get(a))
    r = salesreport.build({"group": "member", "from_date": today, "to_date": today, "member": "0912345678"})
    check("依會員：用手機篩選", [x["key"] for x in r["rows"]] == [m] and r["rows"][0]["phone"] == "0912345678", r["rows"])
    r = salesreport.build({"group": "detail", "from_date": today, "to_date": today, "store": a})
    check("明細：分公司A 的銷售與退貨單（含收銀人員）", len(r["rows"]) == 4 and {x["kind"] for x in r["rows"]} == {"銷售", "退貨／退款"}
          and any(x["cashier"] == ctx["staff"] for x in r["rows"]), [(x["label"], x["kind"], x["net"]) for x in r["rows"]])
    frappe.set_user(ctx["lead"])
    try:
        r = salesreport.build({"group": "store", "from_date": today, "to_date": today})
        check("店長只看到自己的門市", [x["key"] for x in r["rows"]] == [a], [x["key"] for x in r["rows"]])
        err = raises(salesreport.build, {"group": "store", "store": stock.hq_warehouse()})
        check("店長不能指定別的門市", err and "不能查看" in err, err)
    finally:
        frappe.set_user("Administrator")
    frappe.set_user(ctx["hq_user"])
    try:
        err = raises(salesreport.build, {})
        check("總公司作業不能看消費報表", err and "沒有權限" in err, err)
    finally:
        frappe.set_user("Administrator")
    salesreport.export_report({"group": "member", "from_date": today, "to_date": today})
    from io import BytesIO
    import openpyxl
    vals = list(openpyxl.load_workbook(BytesIO(frappe.response["filecontent"])).active.values)
    check("匯出 Excel", vals[0][:2] == ("會員", "手機") and any(v[1] == "0912345678" for v in vals[1:]), vals[:2])
    frappe.response.pop("filecontent", None)


def run_scale(n_invoices, n_members=5000):
    """大量測試：n_members 位會員、n_invoices 筆門市銷售（約 1 成是退貨），分散在一年內與各門市。
    資料直接寫進資料表（只為測速度，結束時復原），量測消費統計與報表的時間。"""
    import random
    import time
    from datetime import date, timedelta

    from nila_app import salesreport, stock

    now = frappe.utils.now()
    base = {"creation": now, "modified": now, "owner": "Administrator", "modified_by": "Administrator"}
    members = [dict(base, name=f"SPEED-M{i:05d}", customer_name=f"速度會員{i}", customer_type="Individual",
                    customer_group="會員", nila_phone=f"09{i:08d}", docstatus=0) for i in range(n_members)]
    keys = list(members[0])
    frappe.db.bulk_insert("Customer", keys, [[m[k] for k in keys] for m in members], chunk_size=2000)
    stores = [w["name"] for w in stock.warehouses(include_transit=False)]
    company = frappe.db.get_value("Company", {}, "name")
    start = date.today() - timedelta(days=364)
    invs = []
    for n in range(n_invoices):
        ret = random.random() < 0.1
        amt = random.choice([350, 700, 1050]) * (-1 if ret else 1)
        invs.append(dict(base, name=f"SPEED-SI-{n:06d}", docstatus=1, is_return=int(ret), nila_channel="門市",
                         posting_date=(start + timedelta(days=random.randint(0, 364))).isoformat(),
                         customer=random.choice(members)["name"], customer_name="", company=company, currency="TWD",
                         set_warehouse=random.choice(stores), grand_total=amt, rounded_total=amt, base_grand_total=amt,
                         conversion_rate=1, debit_to="Debtors - NL", status="Paid"))
    keys = list(invs[0])
    frappe.db.bulk_insert("Sales Invoice", keys, [[i[k] for k in keys] for i in invs], chunk_size=5000)
    print(f"  （資料：{n_members} 位會員、{n_invoices} 筆門市銷售／退貨）")
    year_from, today = start.isoformat(), date.today().isoformat()

    def timed(label, fn, limit):
        t = time.time()
        out = fn()
        used = time.time() - t
        check(f"大量：{label}（{used:.2f} 秒，目標 {limit} 秒內）", used < limit)
        return out

    data = timed("一年全部會員的消費統計", lambda: salesreport.consumption(year_from, today), 3)
    mine = {k: v for k, v in data.items() if k.startswith("SPEED-M")}  # 網站上可能還有其他銷售
    check("大量：統計筆數與總額正確", sum(v["orders"] for v in mine.values()) == sum(1 for i in invs if not i["is_return"])
          and round(sum(v["net"] for v in mine.values())) == sum(i["grand_total"] for i in invs))
    timed("報表：依會員（一年）", lambda: salesreport.get_report({"group": "member", "from_date": year_from, "to_date": today}), 5)
    timed("報表：依門市（一年）", lambda: salesreport.get_report({"group": "store", "from_date": year_from, "to_date": today}), 3)
    timed("報表：明細（一個月）", lambda: salesreport.get_report({"group": "detail", "from_date": frappe.utils.add_days(today, -30),
                                                            "to_date": today}), 3)
    timed("報表：用手機找一位會員（一年）", lambda: salesreport.get_report({"member": "0900001234", "from_date": year_from,
                                                                  "to_date": today}), 2)


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "nila"
    frappe.init(site=site, sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        if len(sys.argv) > 2:
            run_scale(int(sys.argv[2]))
        else:
            ctx = run()
            if ctx:
                test_report(ctx)
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
