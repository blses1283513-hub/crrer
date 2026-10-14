// 商品清單：加上「新增款式」「匯入／匯出」按鈕（保留 ERPNext 原本的清單設定）。
(() => {
	const settings = (frappe.listview_settings["Item"] = frappe.listview_settings["Item"] || {});
	const onload = settings.onload;
	settings.onload = function (listview) {
		if (onload) onload.call(this, listview);
		if (frappe.model.can_create("Item")) {
			listview.page.add_inner_button(__("新增款式"), () => frappe.set_route("nila-new-style"));
			listview.page.add_inner_button(__("匯入／匯出"), () => frappe.set_route("nila-item-import"));
		}
	};
})();
