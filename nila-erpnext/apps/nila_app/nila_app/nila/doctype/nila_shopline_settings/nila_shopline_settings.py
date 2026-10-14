import frappe
from frappe import _
from frappe.model.document import Document


class NilaSHOPLINESettings(Document):
    def validate(self):
        if self.interval and self.interval < 2:
            frappe.throw(_("同步間隔至少 2 分鐘"))
