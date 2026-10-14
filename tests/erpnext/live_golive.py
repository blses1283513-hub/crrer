"""P8（上線）的整合測試：會員名單匯入、還原演練的資料摘要、首頁連結。在正式版容器內執行，結束時全部復原。

    docker compose cp live_golive.py backend:/tmp/live_golive.py
    docker compose exec backend bash -c "cd sites && ../env/bin/python /tmp/live_golive.py nila [會員人數]"

加上會員人數（例如 5000）時另外測大量匯入的速度。
"""

import os
import sys
import time

import frappe

failures = []
PW = "Nila-Test-2026!qz"


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


files = []


def upload(name, text, encoding="utf-8-sig"):
    f = frappe.get_doc({"doctype": "File", "file_name": name, "content": text.encode(encoding), "is_private": 1}).insert(
        ignore_permissions=True)
    files.append(f.get_full_path())
    return f.file_url


def run(scale):
    from nila_app import accounts, memberimport
    from nila_app import levels as L
    from nila_app.setup import drill

    # ---------- 首頁 ----------
    ws = frappe.get_doc("Workspace", "妮菈")
    check("「妮菈」首頁有會員匯入", "nila-member-import" in {l.link_to for l in ws.links if l.type == "Link"})

    # ---------- 會員匯入 ----------
    real_commit = frappe.db.commit
    frappe.db.commit = lambda *a, **k: None  # 匯入工作會 commit；測試中改成不寫入，結束時全部復原
    try:
        frappe.get_doc({"doctype": "Customer", "customer_name": "原本的會員", "customer_type": "Individual",
                        "customer_group": "會員", "nila_phone": "0977000001"}).insert()
        bad = upload("members-bad.csv", "姓名,手機\n甲,0977000101\n,0977000102\n乙,12345\n丙,0977-000-101\n")
        r = memberimport.preview(bad)
        check("會員匯入預覽：列出每一個錯誤與列號", len(r["errors"]) == 3 and "第 3 列" in r["errors"][0], r["errors"])
        memberimport.run_import(bad, "Administrator")
        st = memberimport.import_status()
        check("有錯誤時不匯入任何資料", st["state"] == "failed" and not frappe.db.exists("Customer", {"nila_phone": "0977000101"}), st)

        big5 = upload("members.csv", "姓名,手機\n王小美,0977-000-201\n李大華,977000202\n陳一,+886 977 000 203\n"
                                      "原本的會員,0977000001\n改名的人,0977000001\n", "cp950")
        r = memberimport.preview(big5)
        check("繁體中文 Windows 存的 CSV（Big5）、Excel 去掉開頭 0 的手機都能讀；檔案內手機重複會指出列號",
          r["new"] == 3 and r["sample"][1]["name"] == "李大華" and r["sample"][1]["phone"] == "0977000202"
          and r["errors"] == ["第 6 列（改名的人）：手機 0977000001 和第 5 列重複"], r)
        good = upload("members-ok.csv", "姓名,手機\n王小美,0977-000-201\n李大華,977000202\n陳一,+886 977 000 203\n原本的會員,0977000001\n")
        r = memberimport.preview(good)
        check("預覽：新增 3 位、略過 1 位已經是會員的", (r["new"], r["skipped"], r["errors"]) == (3, 1, []), r)
        memberimport.run_import(good, "Administrator")
        st = memberimport.import_status()
        rows = frappe.get_all("Customer", filters={"nila_phone": ["in", ["0977000201", "0977000202", "0977000203"]]},
                              fields=["customer_name", "nila_phone", "customer_group"], order_by="nila_phone")
        check("匯入完成：會員群組、手機統一格式", st["state"] == "done" and [(x.customer_name, x.nila_phone, x.customer_group) for x in rows]
              == [("王小美", "0977000201", "會員"), ("李大華", "0977000202", "會員"), ("陳一", "0977000203", "會員")], (st, rows))
        check("已經是會員的不改原本資料", frappe.db.count("Customer", {"nila_phone": "0977000001"}) == 1)
        r = memberimport.preview(good)
        check("同一份名單再匯入：全部略過", (r["new"], r["skipped"]) == (0, 4), r)

        # 權限：只有營運主管以上
        for u in ("gl_hq", "gl_mgr"):
            if frappe.db.exists("User", f"{u}@nila.local"):
                frappe.delete_doc("User", f"{u}@nila.local", ignore_permissions=True, force=True)
        u_hq = accounts.save_account({"full_name": "總公司", "username": "gl_hq", "level": L.HQ_STAFF, "password": PW})["name"]
        u_mgr = accounts.save_account({"full_name": "主管", "username": "gl_mgr", "level": L.MANAGER, "password": PW})["name"]
        err = raises(as_user, u_hq, memberimport.preview, good)
        check("總公司作業不能匯入會員", err and "沒有權限" in err, err)
        check("營運主管可以匯入會員", as_user(u_mgr, memberimport.preview, good)["skipped"] == 4)

        if scale:
            lines = ["姓名,手機"] + [f"會員{i:05d},09{88000000 + i:08d}" for i in range(scale)]
            url = upload("members-scale.csv", "\n".join(lines) + "\n")
            t = time.time()
            r = memberimport.preview(url)
            t_preview = time.time() - t
            t = time.time()
            memberimport.run_import(url, "Administrator")
            t_import = time.time() - t
            st = memberimport.import_status()
            check(f"大量匯入 {scale} 位會員：預覽 {t_preview:.1f} 秒、匯入 {t_import:.0f} 秒",
                  r["new"] == scale and st["state"] == "done", st.get("message"))
    finally:
        frappe.db.commit = real_commit

    # ---------- 還原演練的資料摘要 ----------
    rep = drill.report()
    check("資料摘要：版本、款式、規格、會員、銷售、庫存", rep["version"] == frappe.get_attr("nila_app.__version__")
          and rep["members"] >= 4 and rep["company"] and isinstance(rep["stock_qty"], float), rep)
    check("資料摘要：已儲存的金鑰解得開", rep["secrets_ok"])


def main():
    site = sys.argv[1] if len(sys.argv) > 1 else "nila"
    scale = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    frappe.init(site=site, sites_path=".")
    frappe.connect()
    frappe.set_user("Administrator")
    try:
        run(scale)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        check("執行過程沒有錯誤", False, e)
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for p in files:
            try:
                os.remove(p)
            except OSError:
                pass
        frappe.destroy()
    print(f"\n{'全部通過' if not failures else '未通過：' + '、'.join(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
