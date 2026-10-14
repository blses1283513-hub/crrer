// 條碼：選款式（或輸入料號），產生每個規格的條碼（內容＝料號，Code 128），可直接列印或另存圖檔。
frappe.pages["nila-barcode"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("條碼"), single_column: true });
	wrapper.nila = new NilaBarcode(page);
};

class NilaBarcode {
	constructor(page) {
		this.page = page;
		this.style = page.add_field({ fieldtype: "Link", fieldname: "style", label: __("款式"), options: "Item",
			get_query: () => ({ filters: { has_variants: 1 } }), change: () => this.load() });
		this.codes = page.add_field({ fieldtype: "Data", fieldname: "codes", label: __("或輸入料號（以逗號分隔）"), change: () => this.load() });
		page.set_primary_action(__("列印"), () => window.print(), "printer");
		// 用 frappe 內建的條碼欄位產生 SVG（JsBarcode）
		const $hidden = $(`<div style="display:none"></div>`).appendTo(page.body);
		this.ctl = frappe.ui.form.make_control({ parent: $hidden,
			df: { fieldtype: "Barcode", fieldname: "bc", options: JSON.stringify({ format: "CODE128", width: 2, height: 50, fontSize: 14 }) },
			render_input: true });
		this.$out = $(`<div class="nila-barcodes d-flex flex-wrap" style="gap:16px"></div>`).appendTo(page.body);
		$(`<style>@media print { .page-head, .page-form, .navbar, .layout-side-section { display:none !important } .nila-barcodes > div { break-inside: avoid } }</style>`).appendTo(page.body);
	}

	async load() {
		const style = this.style.get_value(), codes = (this.codes.get_value() || "").split(/[,，\s]+/).filter(Boolean);
		const filters = style ? { variant_of: style } : codes.length ? { name: ["in", codes.map((c) => c.toUpperCase())] } : null;
		if (!filters) return this.$out.empty();
		const items = await frappe.db.get_list("Item", { filters, fields: ["name", "item_name", "nila_store_price"], limit: 500, order_by: "name asc" });
		const e = frappe.utils.escape_html;
		this.$out.html(items.map((it) => {
			const svg = this.ctl.get_barcode_html(it.name) || "";
			return `<div class="text-center p-2" style="border:1px dashed var(--border-color);width:260px">
				<div class="small">${e(it.item_name)}</div>${svg}
				${it.nila_store_price ? `<div class="small">${format_currency(it.nila_store_price)}</div>` : ""}
				<a class="small nila-save" data-code="${e(it.name)}">${__("另存圖檔")}</a></div>`;
		}).join("") || `<p class="text-muted">${__("沒有規格")}</p>`);
		this.$out.find(".nila-save").on("click", (ev) => {
			const $svg = $(ev.target).closest("div").find("svg");
			const blob = new Blob([$svg.prop("outerHTML")], { type: "image/svg+xml" });
			const a = document.createElement("a");
			a.href = URL.createObjectURL(blob);
			a.download = `${$(ev.target).data("code")}.svg`;
			a.click();
		});
	}
}
