// 在途調撥單：顯示調入倉；到貨後按「到貨入庫」，在途的貨全部轉入調入倉。
frappe.ui.form.on("Stock Entry", {
	refresh(frm) {
		const d = frm.doc;
		if (d.docstatus !== 1 || !d.add_to_transit || !d.nila_destination || (d.per_transferred || 0) >= 100) return;
		frm.remove_custom_button("End Transit");
		frm.remove_custom_button(__("End Transit"));
		frm.set_intro(__("在途中：調入倉 {0} 收到貨後，按「到貨入庫」。", [d.nila_destination]), "orange");
		frm.add_custom_button(__("到貨入庫"), () => {
			frappe.confirm(__("確認 {0} 已收到這張調撥單的全部貨品？", [d.nila_destination]), async () => {
				const name = await frappe.xcall("nila_app.stock.receive_transfer", { name: d.name });
				frappe.show_alert({ message: __("已入庫：{0}", [name]), indicator: "green" });
				frm.reload_doc();
			});
		}).addClass("btn-primary");
	},
});
