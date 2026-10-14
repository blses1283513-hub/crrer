import frappe
from frappe import _
from frappe.model.document import Document


class NilaLotterySnapshot(Document):
    def validate(self):
        if not self.is_new() and not self.flags.nila_internal:
            frappe.throw(_("名單快照不能修改；要改條件請回到抽獎活動重新產生"))
