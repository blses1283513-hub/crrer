import frappe
from frappe import _
from frappe.model.document import Document


class NilaLottery(Document):
    def validate(self):
        from nila_app.lotteryrules import LotteryError, clean_rules

        if self.from_date and self.to_date and str(self.from_date) > str(self.to_date):
            frappe.throw(_("消費期間的開始日期不能晚於結束日期"))
        try:
            clean_rules([r.as_dict() for r in self.rules], self.entry_mode, self.entry_unit, self.entry_cap)
        except LotteryError as e:
            frappe.throw(str(e), title=_("條件有誤"))
