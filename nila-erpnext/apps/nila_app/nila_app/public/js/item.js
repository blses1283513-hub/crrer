// 商品頁面：款式（範本）加上「加入規格」按鈕；規格提示成本、售價、狀態要在款式修改。
frappe.ui.form.on("Item", {
	refresh(frm) {
		if (frm.doc.has_variants && !frm.is_new()) {
			frm.add_custom_button(__("加入甲型／尺寸"), () =>
				frappe.set_route("nila-new-style", { style: frm.doc.name })
			);
		}
		if (frm.doc.variant_of) {
			frm.set_intro(__("成本、售價與商品狀態由款式 {0} 統一設定。", [frappe.utils.get_form_link("Item", frm.doc.variant_of, true)]), "blue");
		}
	},
});
