// 補貨單：送出＝待叫貨；按「已叫貨」建立採購單＝已叫貨；採購單「到貨入庫」＝已到貨。
frappe.ui.form.on("Material Request", {
	refresh(frm) {
		const d = frm.doc;
		if (d.docstatus !== 1 || d.material_request_type !== "Purchase") return;
		if ((d.per_ordered || 0) < 100 && d.status !== "Stopped") {
			frm.set_intro(__("待叫貨：向廠商叫貨後，按「已叫貨」建立採購單。"), "orange");
			frm.add_custom_button(__("已叫貨（建立採購單）"), () => {
				frappe.prompt([{ fieldtype: "Link", fieldname: "supplier", label: __("廠商"), options: "Supplier", default: "預設廠商", reqd: 1 }],
					async (v) => {
						const po = await frappe.xcall("nila_app.replenish.mark_ordered", { material_request: d.name, supplier: v.supplier });
						frappe.msgprint(__("已建立採購單 {0}。貨到時在採購單按「到貨入庫」。", [frappe.utils.get_form_link("Purchase Order", po, true)]));
						frm.reload_doc();
					}, __("已叫貨"), __("建立採購單"));
			}).addClass("btn-primary");
		} else if ((d.per_received || 0) < 100) {
			frm.set_intro(__("已叫貨：貨到時在採購單按「到貨入庫」。"), "blue");
		}
	},
});
