import frappe
from frappe import _
from frappe.model.document import Document


class NilaReasonLog(Document):
    def on_trash(self):
        if frappe.session.user != "Administrator":
            frappe.throw(_("調整紀錄不能刪除"))
