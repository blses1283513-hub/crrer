"""妮菈穿戴甲：ERPNext 16 試用版的功能實測（在 backend 容器內執行，須先跑過 seed_trial.py）。

逐項操作並判定「通過／未通過」，驗證方案中尚未查證（❓）的功能：
  A. 客戶例子：全公司預計庫存 −2、建議補貨 12
  B. 調撥在途（Q12）：分公司A → 在途 → 總公司收貨；在途期間全公司數字不變
  C. 叫貨後不重複建議（需求 03-5）：採購單 12 件 → 建議補貨變 0 → 收貨後實際入庫
  D. 出貨：依銷售訂單出貨 5 件，預留歸零
  E. 實際庫存不會變負：出貨超過實際數量會被擋下
  F. 條碼搜尋：以料號條碼找到規格
  G. 修改紀錄：誰、何時、改了什麼
  H. 依倉庫限制權限：分公司A 的帳號只看得到分公司A
  I. 會員合併：重複的會員合併成一個
  J. 用語修正：「Projected Qty」改譯為「預計庫存」

會建立名稱含「NILA-TRIAL-VERIFY」的單據，方便在畫面上查看；只能執行一次（重跑會提示並停止）。
用法：
  cd /home/frappe/frappe-bench/sites
  /home/frappe/frappe-bench/env/bin/python /tmp/nila-seed/verify_trial.py --site frontend
"""

import argparse
import datetime
import sys

MARK = "NILA-TRIAL-VERIFY"
SKU = "0001-LT-M"
results = []


def check(label, ok, detail=""):
    results.append((label, bool(ok)))
    print(f"{'✓' if ok else '✗'} {label}{'：' + detail if detail else ''}", flush=True)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--site", default="frontend")
    a = p.parse_args(argv)

    import frappe
    from frappe.utils import flt

    frappe.init(site=a.site, sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        if frappe.db.exists("Supplier", f"試用供應商 {MARK}"):
            print("已經驗證過（資料已存在）。要重做請重新安裝試用版。")
            return 0
        company, abbr = frappe.db.get_value("Company", {}, ["name", "abbr"])
        wh = lambda n: f"{n} - {abbr}"
        HQ, BA, TR = wh("總公司"), wh("分公司A"), wh("在途")
        today = datetime.date.today()

        def bins():
            rows = frappe.get_all("Bin", filters={"item_code": SKU}, fields=["warehouse", "actual_qty", "reserved_qty", "ordered_qty", "projected_qty"])
            return {r.warehouse: r for r in rows}

        def total_projected():
            return sum(flt(r.projected_qty) for r in bins().values())

        target = frappe.db.get_value("Item", SKU, "nila_reorder_target") or 0
        suggestion = lambda: max(0, target - total_projected())

        # A
        b = bins()
        check("A. 客戶例子：總公司預計 −3、分公司A +1、全公司 −2、建議補 12",
              flt(b[HQ].projected_qty) == -3 and flt(b[BA].projected_qty) == 1 and total_projected() == -2 and suggestion() == 12,
              f"總公司 {b[HQ].projected_qty:g}、分公司A {b[BA].projected_qty:g}、全公司 {total_projected():g}、建議 {suggestion():g}")

        # B 在途調撥
        out = frappe.get_doc({
            "doctype": "Stock Entry", "stock_entry_type": "Material Transfer", "purpose": "Material Transfer",
            "company": company, "add_to_transit": 1, "remarks": f"{MARK} 分公司A 寄回總公司",
            "items": [{"item_code": SKU, "qty": 1, "s_warehouse": BA, "t_warehouse": TR, "uom": "件", "conversion_factor": 1}],
        })
        out.insert(); out.submit()
        b = bins()
        check("B1. 寄出後：分公司A 0、在途 1，全公司預計仍是 −2（在途也算公司的貨）",
              flt(b[BA].actual_qty) == 0 and flt(b[TR].actual_qty) == 1 and total_projected() == -2,
              f"分公司A {b[BA].actual_qty:g}、在途 {b[TR].actual_qty:g}、全公司 {total_projected():g}")
        from erpnext.stock.doctype.stock_entry.stock_entry import make_stock_in_entry
        rec = make_stock_in_entry(out.name)
        for it in rec.items:
            it.t_warehouse = HQ
        rec.remarks = f"{MARK} 總公司收貨"
        rec.insert(); rec.submit()
        b = bins()
        check("B2. 收貨後：在途 0、總公司實際 3、全公司 −2；收貨單連回寄出單",
              flt(b[TR].actual_qty) == 0 and flt(b[HQ].actual_qty) == 3 and total_projected() == -2 and rec.outgoing_stock_entry == out.name,
              f"總公司實際 {b[HQ].actual_qty:g}、在途 {b[TR].actual_qty:g}")
        check("B3. 寄出單標示已全部收貨", flt(frappe.db.get_value("Stock Entry", out.name, "per_transferred")) == 100)

        # C 叫貨與入庫
        sup = frappe.get_doc({"doctype": "Supplier", "supplier_name": f"試用供應商 {MARK}",
                              "supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}, "name") or "All Supplier Groups"})
        sup.insert()
        po = frappe.get_doc({
            "doctype": "Purchase Order", "supplier": sup.name, "company": company,
            "transaction_date": str(today), "schedule_date": str(today + datetime.timedelta(days=7)),
            "set_warehouse": HQ, "remarks": MARK,
            "items": [{"item_code": SKU, "qty": 12, "rate": 180, "uom": "件", "conversion_factor": 1,
                       "warehouse": HQ, "schedule_date": str(today + datetime.timedelta(days=7))}],
        })
        po.insert(); po.submit()
        b = bins()
        check("C1. 叫貨 12 件後：已叫貨 12、全公司預計 10、建議補貨變 0（不會重複叫貨）",
              flt(b[HQ].ordered_qty) == 12 and total_projected() == 10 and suggestion() == 0,
              f"已叫貨 {b[HQ].ordered_qty:g}、全公司 {total_projected():g}、建議 {suggestion():g}")
        from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
        pr = make_purchase_receipt(po.name)
        pr.insert(); pr.submit()
        b = bins()
        check("C2. 入庫後：總公司實際 15、已叫貨 0、全公司預計仍是 10",
              flt(b[HQ].actual_qty) == 15 and flt(b[HQ].ordered_qty) == 0 and total_projected() == 10,
              f"實際 {b[HQ].actual_qty:g}、已叫貨 {b[HQ].ordered_qty:g}")

        # D 出貨
        so_name = frappe.db.get_value("Sales Order", {"po_no": "NILA-TRIAL-SCENARIO", "docstatus": 1}, "name")
        from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
        dn = make_delivery_note(so_name)
        dn.insert(); dn.submit()
        b = bins()
        so = frappe.get_doc("Sales Order", so_name)
        check("D. 出貨 5 件後：總公司實際 10、預留 0、訂單已出貨 100%",
              flt(b[HQ].actual_qty) == 10 and flt(b[HQ].reserved_qty) == 0 and flt(so.per_delivered) == 100,
              f"實際 {b[HQ].actual_qty:g}、預留 {b[HQ].reserved_qty:g}、訂單狀態 {so.status}")

        frappe.db.commit()  # E 會故意觸發錯誤並復原，先保存前面的結果

        # E 實際庫存不能變負
        blocked, reason = False, ""
        try:
            se = frappe.get_doc({
                "doctype": "Stock Entry", "stock_entry_type": "Material Issue", "purpose": "Material Issue",
                "company": company, "remarks": MARK,
                "items": [{"item_code": SKU, "qty": 999, "s_warehouse": HQ, "uom": "件", "conversion_factor": 1}],
            })
            se.insert(); se.submit()
        except Exception as e:  # ERPNext 會丟出 NegativeStockError
            blocked = True
            frappe.db.rollback()
            frappe.clear_messages()
            reason = type(e).__name__
        check("E. 實際庫存不足時出庫被擋下（實際數量不會變負；負數只出現在預計庫存）", blocked, reason if blocked else "沒有被擋下")

        # F 條碼
        from erpnext.selling.page.point_of_sale.point_of_sale import search_for_serial_or_batch_or_barcode_number
        found = search_for_serial_or_batch_or_barcode_number(SKU)
        check("F. 以條碼（內容＝料號）找到規格", (found or {}).get("item_code") == SKU, str(found))

        # G 修改紀錄
        track = frappe.get_meta("Item").track_changes
        item = frappe.get_doc("Item", SKU)
        item.nila_reorder_target = int(item.nila_reorder_target or 0) + 1
        item.save()
        versions = frappe.get_all("Version", filters={"ref_doctype": "Item", "docname": SKU}, fields=["owner", "creation", "data"], order_by="creation desc", limit=1)
        check("G. 修改紀錄：改規格的補貨目標後，留下誰、何時、改前改後",
              bool(versions) and "nila_reorder_target" in (versions[0].data or ""),
              f"追蹤變更={'開' if track else '關'}；最新紀錄 {versions[0].owner if versions else '無'}")
        item.nila_reorder_target -= 1
        item.save()

        # H 權限：分公司A 帳號只看到分公司A
        email = "branch-a.trial@example.com"
        if not frappe.db.exists("User", email):
            u = frappe.get_doc({"doctype": "User", "email": email, "first_name": "分公司A 門市", "send_welcome_email": 0,
                                "roles": [{"role": "Stock User"}, {"role": "Sales User"}]})
            u.insert()
        frappe.get_doc({"doctype": "User Permission", "user": email, "allow": "Warehouse", "for_value": BA, "apply_to_all_doctypes": 1}).insert()
        frappe.set_user(email)
        visible = {r.warehouse for r in frappe.get_list("Bin", fields=["warehouse"], limit_page_length=0)}
        frappe.set_user("Administrator")
        check("H. 分公司A 的門市帳號只看得到分公司A 的庫存", visible == {BA}, f"看得到：{'、'.join(sorted(visible)) or '無'}")

        # I 會員合併
        def member(name):
            d = frappe.get_doc({"doctype": "Customer", "customer_name": name, "customer_type": "Individual",
                                "customer_group": "Individual" if frappe.db.exists("Customer Group", "Individual") else "All Customer Groups"})
            d.insert()
            return d.name
        keep, dup = member(f"王小美 {MARK}"), member(f"王小美（重複）{MARK}")
        frappe.rename_doc("Customer", dup, keep, merge=True)
        check("I. 重複會員合併成一個", not frappe.db.exists("Customer", dup) and frappe.db.exists("Customer", keep))

        # J 用語修正
        before = frappe.get_all("Translation", filters={"language": "zh-TW", "source_text": "Projected Qty"}, pluck="name")
        if not before:
            frappe.get_doc({"doctype": "Translation", "language": "zh-TW", "source_text": "Projected Qty", "translated_text": "預計庫存"}).insert()
        frappe.clear_cache()
        frappe.local.lang = "zh-TW"
        got = frappe._("Projected Qty", lang="zh-TW")
        check("J. 用語可在系統內修正：「Projected Qty」顯示為「預計庫存」（原翻譯為「可用數量」）", got == "預計庫存", got)

        frappe.db.commit()
    finally:
        frappe.destroy()

    passed = sum(1 for _, ok in results if ok)
    print(f"\n結果：{passed}/{len(results)} 項通過")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
