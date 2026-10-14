"""P1 商品匯入匯出的整合測試：在已安裝的正式版 ERPNext 容器內執行，結束時全部復原（不留下測試資料）。

    docker compose cp live_import.py backend:/tmp/live_import.py
    docker compose cp ../../nila-erpnext/seed/sample-skus.csv backend:/tmp/sample-skus.csv
    docker compose exec backend bash -c "cd sites && ../env/bin/python /tmp/live_import.py nila /tmp/sample-skus.csv"

加上第三個參數（款式數）會改做大量測試：產生「款式數 × 全部甲型 × 全部尺寸」個規格並計時。
"""

import csv
import io
import sys
import time
from unittest import mock

import frappe

failures = []
files = []


def check(label, ok, detail=""):
    print(f"{'✓' if ok else '✗'} {label}{'：' + str(detail) if detail not in ('', None) else ''}", flush=True)
    if not ok:
        failures.append(label)


def upload(name, table):
    buf = io.StringIO()
    csv.writer(buf).writerows(table)
    f = frappe.get_doc({"doctype": "File", "file_name": name, "is_private": 1, "content": buf.getvalue().encode("utf-8-sig")}).insert()
    files.append(f.get_full_path())
    return f.file_url


def run_job(url):
    """執行背景匯入工作本身（不經過佇列），並攔下它最後的 commit，測試結束才能全部復原。"""
    from nila_app import importer

    with mock.patch.object(frappe.db, "commit"):
        importer.run_import(url, "Administrator")
    return importer.import_status()


def qty(item, wh):
    return frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh}, "actual_qty") or 0


def run(sample):
    from nila_app import importer

    abbr = frappe.db.get_value("Company", {}, "abbr")
    with open(sample, encoding="utf-8-sig") as f:
        table = list(csv.reader(f))
    shapes = {v.attribute_value: v.abbr for v in frappe.get_all("Item Attribute Value", filters={"parent": "甲型"}, fields=["attribute_value", "abbr"])}
    # 範例試算表的料號是固定的 0001…；本機已有款式時改用不會撞號的編號
    offset = 0
    while any(frappe.db.exists("Item", f"{int(r[1]) + offset:04d}") for r in table[1:]):
        offset += 1000
    for r in table[1:]:
        r[1] = f"{int(r[1]) + offset:04d}"
        r[0] = f"{r[1]}-{shapes[r[3]]}-{r[4]}"
    first = table[1]

    url = upload("p1-sample.csv", table)
    pv = importer.preview(url)
    check("預覽：範例試算表沒有錯誤", pv["errors"] == [], pv["errors"][:3])
    check("預覽：10 款、72 個規格", (pv["counts"]["new_styles"], pv["counts"]["new_variants"]) == (10, 72), pv["counts"])
    check("預覽不寫入資料", not frappe.db.exists("Item", first[1]))

    t = time.time()
    st = run_job(url)
    check("匯入完成", st.get("state") == "done", st.get("message"))
    print(f"  （72 個規格含期初庫存，用時 {time.time() - t:.1f} 秒）")
    sku = first[0]
    check("規格建立、料號一致", frappe.db.exists("Item", sku) and frappe.db.get_value("Item", sku, "variant_of") == first[1])
    item = frappe.db.get_value("Item", sku, ["nila_status", "nila_cost", "nila_reorder_target", "nila_shape", "nila_size"], as_dict=True)
    check("規格帶入狀態、成本、補貨目標、甲型、尺寸",
          (item.nila_status, item.nila_cost, item.nila_reorder_target, item.nila_shape, item.nila_size)
          == (first[5], float(first[6]), int(first[9]), first[3], first[4]), item)
    price = frappe.db.get_value("Item Price", {"item_code": sku, "price_list": "實體售價"}, "price_list_rate")
    check("售價建立", price == float(first[8]), price)
    head = table[0]
    expect = {w: int(first[head.index(w)]) for w in ["總公司", "分公司A", "分公司B", "分公司C", "分公司D"]}
    got = {w: qty(sku, f"{w} - {abbr}") for w in expect}
    check("各公司期初庫存", got == expect, got)
    total_expected = sum(int(x) for r in table[1:] for x in r[10:15])
    total = frappe.db.sql("select sum(actual_qty) from tabBin where item_code like %s", (f"{first[1][:2]}%",))[0][0] or 0
    check("期初庫存總數", int(total) >= total_expected, (total, total_expected))
    sr = frappe.get_all("Stock Reconciliation", filters={"purpose": "Opening Stock", "docstatus": 1}, pluck="name")
    check("期初庫存用「期初庫存」盤點單（已過帳）", len(sr) >= 5, len(sr))

    # 再匯入一次同樣的檔案：不變；有庫存的已存在規格會提醒
    pv = importer.preview(url)
    check("重複匯入：全部不變", (pv["counts"]["new_variants"], pv["counts"]["updated_variants"], pv["counts"]["unchanged_variants"]) == (0, 0, 72), pv["counts"])
    check("重複匯入：提醒已存在的規格不匯入庫存", any("不會匯入庫存" in w for w in pv["warnings"]), pv["warnings"])

    # 修改：改售價、補貨目標，並在缺少組合的款式加一個新規格
    t2 = [list(r) for r in table]
    style_rows = [r for r in t2[1:] if r[1] == first[1]]
    for r in style_rows:
        r[8] = "999"
    style_rows[0][9] = "33"
    have = {}
    for r in t2[1:]:
        have.setdefault(r[1], set()).add((r[3], r[4]))
    cand, cell = next((c, (s, z)) for c, cells in have.items() for s in shapes for z in ["XS", "S", "M", "L"] if (s, z) not in cells)
    src = next(r for r in t2[1:] if r[1] == cand)
    t2.append(["", cand, src[2], cell[0], cell[1], src[5], src[6], src[7], src[8], "4", "7", "", "", "", ""])
    url2 = upload("p1-change.csv", t2)
    pv = importer.preview(url2)
    check("修改預覽：1 款更新、1 規格更新、1 規格新增", (pv["counts"]["updated_styles"], pv["counts"]["updated_variants"], pv["counts"]["new_variants"]) == (1, 1, 1), pv["counts"])
    st = run_job(url2)
    check("修改匯入完成", st.get("state") == "done", st.get("message"))
    check("款式售價更新並同步到規格", frappe.db.get_value("Item Price", {"item_code": sku, "price_list": "實體售價"}, "price_list_rate") == 999)
    check("補貨目標更新", frappe.db.get_value("Item", sku, "nila_reorder_target") == 33)
    new_sku = f"{cand}-{shapes[cell[0]]}-{cell[1]}"
    check("既有款式加入新規格並有期初庫存", frappe.db.exists("Item", new_sku) and qty(new_sku, f"總公司 - {abbr}") == 7, new_sku)
    check("已存在規格的庫存沒有被改", qty(sku, f"總公司 - {abbr}") == expect["總公司"])

    # 錯誤的檔案：不匯入
    bad = [list(r) for r in table[:3]]
    bad[1][1], bad[2][1] = "", ""
    bad[1][3] = "方形"
    url3 = upload("p1-bad.csv", bad)
    pv = importer.preview(url3)
    check("錯誤會列出列號", any(e.startswith("第 2 列：沒有這個甲型") for e in pv["errors"]), pv["errors"])
    st = run_job(url3)
    check("有錯誤時背景匯入也不寫入", st.get("state") == "failed", st.get("message"))

    # 中途失敗：全部取消
    t4 = [table[0], ["", "", "回滾測試款", first[3], "XS", "上架", "1", "1", "1", "1", "1", "", "", "", ""],
          ["", "", "回滾測試款", first[3], "S", "上架", "1", "1", "1", "1", "1", "", "", "", ""]]
    url4 = upload("p1-rollback.csv", t4)
    with mock.patch("nila_app.importer._opening_stock", side_effect=RuntimeError("模擬期初庫存失敗")):
        st = run_job(url4)
    check("中途失敗：狀態為失敗並說明沒有寫入", st.get("state") == "failed" and "沒有寫入" in st.get("message", ""), st.get("message"))
    check("中途失敗：款式與規格都沒有留下", not frappe.db.exists("Item", {"item_name": "回滾測試款"}))

    # 匯出與範本
    frappe.local.response = frappe._dict()
    importer.export_items()
    from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

    rows = read_xlsx_file_from_attached_file(fcontent=frappe.local.response.filecontent)
    check("匯出：標題列與匯入格式相同", rows[0][:10] == table[0][:10] and rows[0][10:] == table[0][10:], rows[0])
    exported = {r[0]: r for r in rows[1:]}
    e = exported.get(sku)
    check("匯出：含目前庫存", e is not None and int(e[10]) == expect["總公司"], e)
    url5 = upload("p1-export.csv", [[("" if c is None else c) for c in r] for r in rows])
    pv = importer.preview(url5)
    check("匯出的檔案可以直接匯入（沒有變更）", pv["errors"] == [] and pv["counts"]["new_variants"] == 0
          and pv["counts"]["updated_variants"] == 0 and pv["counts"]["updated_styles"] == 0, (pv["errors"][:3], pv["counts"]))
    frappe.local.response = frappe._dict()
    importer.download_template()
    tpl = read_xlsx_file_from_attached_file(fcontent=frappe.local.response.filecontent)
    check("空白範本只有標題列", len(tpl) == 1 and tpl[0] == rows[0])


def run_scale(n_styles):
    """大量測試：n 款 × 全部甲型 × 全部尺寸，每個規格 5 個公司都有期初庫存。"""
    from nila_app import importer

    attr = frappe.get_doc("Item Attribute", "甲型")
    extra = [("測試甲型", "XA"), ("測試甲型二", "XB"), ("測試甲型三", "XC"), ("測試甲型四", "XD")]
    for name, ab in extra[: max(0, 7 - len(attr.item_attribute_values))]:  # 正式上線是 7 種甲型
        attr.append("item_attribute_values", {"attribute_value": name, "abbr": ab})
    attr.save()
    shapes, sizes, whs = importer._context()
    head = importer.headers(list(whs))
    table = [head]
    for i in range(n_styles):
        for s in shapes:
            for z in sizes:
                table.append(["", "", f"大量測試{i:03d}", s, z, "上架", "100", "390", "350", "10"] + ["2"] * len(whs))
    url = upload("p1-scale.csv", table)
    n = len(table) - 1
    t = time.time()
    pv = importer.preview(url)
    check(f"大量：預覽 {n} 個規格", pv["errors"] == [] and pv["counts"]["new_variants"] == n, (pv["errors"][:3], pv["counts"]))
    print(f"  （預覽用時 {time.time() - t:.1f} 秒）")
    t = time.time()
    st = run_job(url)
    used = time.time() - t
    # 測試攔下了匯入工作的 commit（結束時才能全部復原），之後的步驟仍在同一筆交易中，要沿用放寬的寫入上限
    frappe.db.MAX_WRITES_PER_TRANSACTION = importer.MAX_WRITES
    check(f"大量：匯入 {n} 個規格與期初庫存", st.get("state") == "done", st.get("message"))
    print(f"  （匯入用時 {used / 60:.1f} 分鐘）")
    check("大量：規格數正確", frappe.db.count("Item", {"item_name": ["like", "大量測試%"], "variant_of": ["is", "set"]}) == n)
    code = frappe.db.get_value("Item", {"item_name": "大量測試000", "has_variants": 1}, "name")
    t = time.time()
    doc = frappe.get_doc("Item", code)
    doc.nila_store_price = 360
    doc.save()
    check(f"大量：修改一個款式（{len(shapes) * len(sizes)} 個規格）售價", all(
        r == 360 for r in frappe.get_all("Item Price", filters={"item_code": ["like", f"{code}-%"], "price_list": "實體售價"}, pluck="price_list_rate")))
    print(f"  （修改款式用時 {time.time() - t:.1f} 秒）")
    t = time.time()
    frappe.local.response = frappe._dict()
    importer.export_items()
    print(f"  （匯出用時 {time.time() - t:.1f} 秒）")


def main():
    site, sample = sys.argv[1], sys.argv[2]
    frappe.init(site=site, sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        if len(sys.argv) > 3:
            run_scale(int(sys.argv[3]))
        else:
            run(sample)
    except Exception as e:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        check("執行過程沒有錯誤", False, e)
    finally:
        frappe.db.rollback()
        frappe.cache.delete_value("nila_import_state")
        import os

        for f in files:
            if os.path.exists(f):
                os.remove(f)
        frappe.destroy()
    print(f"\n{'全部通過' if not failures else '未通過：' + '、'.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
