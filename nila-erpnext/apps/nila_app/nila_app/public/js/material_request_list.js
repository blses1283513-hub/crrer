// 補貨單清單：狀態顯示為 待叫貨／已叫貨／已到貨（其他類型的單據維持 ERPNext 原本的顯示）。
(() => {
	const settings = (frappe.listview_settings["Material Request"] = frappe.listview_settings["Material Request"] || {});
	const original = settings.get_indicator;
	settings.add_fields = [...(settings.add_fields || []), "material_request_type", "per_ordered", "per_received"];
	settings.get_indicator = function (doc) {
		if (doc.docstatus === 1 && doc.material_request_type === "Purchase") {
			if (doc.status === "Pending") return [__("待叫貨"), "orange", "status,=,Pending"];
			if (["Ordered", "Partially Ordered"].includes(doc.status)) return [__("已叫貨"), "blue", "status,=," + doc.status];
			if (["Received", "Partially Received"].includes(doc.status)) return [__("已到貨"), "green", "status,=," + doc.status];
		}
		return original ? original.call(this, doc) : undefined;
	};
})();
