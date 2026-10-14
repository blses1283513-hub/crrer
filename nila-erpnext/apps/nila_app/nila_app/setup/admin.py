"""主機上的維護指令（由 reset-admin-password.ps1 呼叫；只能在安裝系統的電腦上透過 Docker 執行）。

    bench --site <網站> execute nila_app.setup.admin.reset_password
密碼與帳號由環境變數 NILA_NEW_PASSWORD、NILA_RESET_USER 傳入，不出現在指令或紀錄中。
"""

import os
import time

import frappe


def reset_password():
    from frappe.utils.password import update_password

    user = os.environ.get("NILA_RESET_USER") or "Administrator"
    pw = os.environ.get("NILA_NEW_PASSWORD") or ""
    if len(pw) < 10:
        raise SystemExit("密碼太短")
    if not frappe.db.exists("User", user):
        raise SystemExit(f"找不到帳號：{user}")
    # 系統剛啟動或有人正在登入時，帳號資料可能同時被更新：重試幾次
    for attempt in range(5):
        try:
            update_password(user, pw)
            frappe.db.commit()
            if not frappe.db.get_value("User", user, "enabled"):
                frappe.db.set_value("User", user, "enabled", 1)
                frappe.db.commit()
            break
        except frappe.QueryDeadlockError:
            frappe.db.rollback()
            if attempt == 4:
                raise
            time.sleep(1 + attempt)
    # 輸錯太多次被暫時鎖住的話，一起解除（帳號、信箱、使用者名稱都可能是登入時用的名稱）
    for key in {user, frappe.db.get_value("User", user, "username"), frappe.db.get_value("User", user, "email")} - {None, ""}:
        frappe.cache.hdel("login_failed_count", key)
    print("NILA_PASSWORD_OK")
