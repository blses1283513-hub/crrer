"""會員名單匯入（P8：上線時把客戶原有的會員名單匯入）。規則在 retailrules.plan_members。

- 試算表（Excel 或 CSV）兩欄：姓名、手機。先預覽（不寫入），沒有錯誤才能匯入。
- 手機已經是會員的略過（不改原本的資料）；全部成功才寫入；在背景執行。
- 只有營運主管以上（可以合併會員的層級）可以使用。
"""

import frappe
from frappe import _

from nila_app import perms
from nila_app import retailrules as R
from nila_app.importer import _read_table

STATE_KEY = "nila_member_import_state"
MEMBER_GROUP = "會員"


def _check():
    perms.require("member_merge")


def _existing():
    return {c.nila_phone: c.customer_name for c in frappe.get_all("Customer", filters={"nila_phone": ["is", "set"]},
                                                                  fields=["nila_phone", "customer_name"])}


def _plan(file_url):
    return R.plan_members(_read_table(file_url), _existing())


@frappe.whitelist()
def download_template():
    _check()
    from frappe.utils.xlsxutils import build_xlsx_response

    build_xlsx_response([R.MEMBER_COLUMNS], "nila-members-template")


@frappe.whitelist()
def preview(file_url):
    _check()
    p = _plan(file_url)
    return {"errors": p["errors"], "warnings": p["warnings"][:200], "new": len(p["new"]), "skipped": len(p["skipped"]),
            "sample": p["new"][:50]}


@frappe.whitelist()
def start_import(file_url):
    _check()
    state = frappe.cache.get_value(STATE_KEY) or {}
    if state.get("state") in ("queued", "running") and frappe.utils.time_diff_in_hours(frappe.utils.now(), state.get("time")) < 2:
        frappe.throw(_("{0} 的會員匯入還在進行中，請等它完成").format(state.get("user")))
    _set_state("queued", _("排隊中…"))
    frappe.enqueue("nila_app.memberimport.run_import", queue="long", timeout=2 * 3600, file_url=file_url,
                   user=frappe.session.user, enqueue_after_commit=True)
    return import_status()


@frappe.whitelist()
def import_status():
    _check()
    return frappe.cache.get_value(STATE_KEY) or {}


def _set_state(state, message, **extra):
    frappe.cache.set_value(STATE_KEY, {"state": state, "message": message, "user": frappe.session.user,
                                       "time": frappe.utils.now(), **extra}, expires_in_sec=7 * 24 * 3600)


def run_import(file_url, user):
    """背景工作：全部成功才寫入。"""
    frappe.set_user(user)
    frappe.db.savepoint("nila_member_import")
    try:
        _set_state("running", _("檢查資料…"), progress=0)
        p = _plan(file_url)
        if p["errors"]:
            raise frappe.ValidationError(_("資料有誤，沒有匯入任何資料：") + "；".join(p["errors"][:20]))
        total = len(p["new"])
        for i, m in enumerate(p["new"], start=1):
            frappe.get_doc({"doctype": "Customer", "customer_name": m["name"], "customer_type": "Individual",
                            "customer_group": MEMBER_GROUP, "nila_phone": m["phone"]}).insert(ignore_permissions=True)
            if i % 200 == 0:
                _set_state("running", _("已建立 {0}/{1} 位會員").format(i, total), progress=round(i / total * 100))
        frappe.db.commit()
        _set_state("done", _("匯入完成：新增 {0} 位會員，略過 {1} 位已經是會員的").format(total, len(p["skipped"])),
                   new=total, skipped=len(p["skipped"]))
    except Exception as e:
        frappe.db.rollback(save_point="nila_member_import")
        frappe.log_error(title="妮菈會員匯入失敗")
        _set_state("failed", _("匯入失敗，沒有寫入任何資料：{0}").format(frappe.utils.strip_html(str(e))[:2000]))
