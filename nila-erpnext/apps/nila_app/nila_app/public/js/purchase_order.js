// 採購單（已叫貨）：貨到時按「到貨入庫」建立入庫單，可修改實收數量後送出。
frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		const d = frm.doc;
		if (d.docstatus !== 1 || (d.per_received || 0) >= 100 || ["Closed", "On Hold"].includes(d.status)) return;
		frm.add_custom_button(__("到貨入庫"), () =>
			frappe.model.open_mapped_doc({ method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt", frm })
		).addClass("btn-primary");
	},
});
