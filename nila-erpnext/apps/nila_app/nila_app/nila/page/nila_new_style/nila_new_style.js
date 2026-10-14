// 新增款式：輸入名稱、成本、售價，勾選甲型 × 尺寸，一次建立款式與全部規格。
// 選了「既有款式」時改為「加入規格」：已有的組合顯示為已勾選且不能取消。
frappe.pages["nila-new-style"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("新增款式"), single_column: true });
	wrapper.nila = new NilaNewStyle(page);
};

frappe.pages["nila-new-style"].on_page_show = function (wrapper) {
	const style = frappe.route_options && frappe.route_options.style;
	frappe.route_options = null;
	if (style && wrapper.nila) wrapper.nila.ready.then(() => wrapper.nila.form.set_value("style", style));
};

class NilaNewStyle {
	constructor(page) {
		this.page = page;
		this.existing = {};
		this.page.set_primary_action(__("建立"), () => this.submit(), "add");
		this.ready = frappe
			.xcall("nila_app.products.get_style_options")
			.then((opts) => {
				this.opts = opts;
				this.make_form();
			});
	}

	make_form() {
		const add_mode = "eval:doc.style";
		const new_mode = "eval:!doc.style";
		this.form = new frappe.ui.FieldGroup({
			parent: this.page.body,
			fields: [
				{ fieldtype: "Link", fieldname: "style", label: __("加入規格到既有款式（新增款式請留空）"), options: "Item",
					get_query: () => ({ filters: { has_variants: 1 } }), change: () => this.load_existing() },
				{ fieldtype: "Section Break", depends_on: new_mode },
				{ fieldtype: "Data", fieldname: "style_name", label: __("款式名稱"), depends_on: new_mode, mandatory_depends_on: new_mode },
				{ fieldtype: "Data", fieldname: "code", label: __("款式編號"), depends_on: new_mode,
					description: __("留空自動編號（建議：{0}）。之後不能改", [this.opts.next_code]) },
				{ fieldtype: "Select", fieldname: "status", label: __("商品狀態"), options: "上架\n停售\n停產", default: "上架", depends_on: new_mode },
				{ fieldtype: "Column Break" },
				{ fieldtype: "Currency", fieldname: "cost", label: __("成本"), depends_on: new_mode, mandatory_depends_on: new_mode, non_negative: 1 },
				{ fieldtype: "Currency", fieldname: "web_price", label: __("官網售價"), depends_on: new_mode, mandatory_depends_on: new_mode, non_negative: 1 },
				{ fieldtype: "Currency", fieldname: "store_price", label: __("實體售價"), depends_on: new_mode, mandatory_depends_on: new_mode, non_negative: 1 },
				{ fieldtype: "Section Break", label: __("甲型 × 尺寸") },
				{ fieldtype: "HTML", fieldname: "matrix" },
				{ fieldtype: "HTML", fieldname: "hint", depends_on: add_mode,
					options: `<p class="text-muted small">${__("成本、售價與狀態請在款式頁面修改，會自動套用到所有規格。")}</p>` },
			],
		});
		this.form.make();
		this.render_matrix();
	}

	render_matrix() {
		const { shapes, sizes } = this.opts;
		const e = frappe.utils.escape_html;
		const head = sizes.map((s) => `<th class="text-center">${e(s)}</th>`).join("");
		const rows = shapes
			.map((shape) => {
				const cells = sizes
					.map((size) => {
						const have = this.existing[`${shape}|${size}`];
						return `<td class="text-center"><input type="checkbox" class="nila-cell" data-shape="${e(shape)}" data-size="${e(size)}"
							${have ? "checked disabled" : ""}></td>`;
					})
					.join("");
				const target = this.existing_target(shape);
				return `<tr><th><label class="mb-0"><input type="checkbox" class="nila-row" data-shape="${e(shape)}"> ${e(shape)}</label></th>${cells}
					<td><input type="number" min="0" step="1" class="form-control input-xs nila-target" data-shape="${e(shape)}"
						value="${target === null ? "" : target}" placeholder="0" style="max-width:7em"></td></tr>`;
			})
			.join("");
		const $m = $(this.form.get_field("matrix").wrapper).empty();
		$m.append(`<table class="table table-bordered nila-matrix" style="width:auto">
			<thead><tr><th>${__("甲型")}</th>${head}<th>${__("補貨目標（每個尺寸）")}</th></tr></thead><tbody>${rows}</tbody></table>
			<p class="text-muted small">${__("勾選要建立的規格；料號為「款式編號-甲型縮寫-尺寸」，例如 0001-LT-XS。")}</p>`);
		$m.find(".nila-row").on("change", function () {
			$m.find(`.nila-cell[data-shape="${$(this).data("shape")}"]:not(:disabled)`).prop("checked", this.checked);
		});
	}

	existing_target(shape) {
		const t = Object.entries(this.existing).find(([k]) => k.startsWith(`${shape}|`));
		return t ? t[1] : null;
	}

	async load_existing() {
		const style = this.form.get_value("style");
		this.existing = {};
		if (style) {
			const rows = await frappe.db.get_list("Item", {
				filters: { variant_of: style },
				fields: ["nila_shape", "nila_size", "nila_reorder_target"],
				limit: 500,
			});
			rows.forEach((r) => (this.existing[`${r.nila_shape}|${r.nila_size}`] = r.nila_reorder_target || 0));
		}
		this.page.set_primary_action(style ? __("加入規格") : __("建立"), () => this.submit(), "add");
		this.render_matrix();
	}

	collect() {
		const $m = $(this.form.get_field("matrix").wrapper);
		const cells = $m.find(".nila-cell:checked:not(:disabled)").map((_, el) => ({ shape: $(el).data("shape"), size: $(el).data("size") })).get();
		const targets = {};
		$m.find(".nila-target").each((_, el) => {
			if (el.value !== "") targets[$(el).data("shape")] = el.value;
		});
		return { cells, targets };
	}

	async submit() {
		const v = this.form.get_values();
		if (!v) return;
		const { cells, targets } = this.collect();
		if (!cells.length) {
			frappe.msgprint(__("請至少勾選一個新的甲型 × 尺寸"));
			return;
		}
		let made, code;
		if (v.style) {
			made = await frappe.xcall("nila_app.products.add_variants", { style: v.style, cells, targets });
			code = v.style;
		} else {
			const r = await frappe.xcall("nila_app.products.create_style", {
				data: { code: v.code, name: v.style_name, status: v.status, cost: v.cost, web_price: v.web_price,
					store_price: v.store_price, cells, targets },
			});
			made = r.variants;
			code = r.code;
		}
		frappe.msgprint({
			title: __("完成"),
			indicator: "green",
			message: __("款式 {0}：已建立 {1} 個規格<br>{2}", [
				frappe.utils.get_form_link("Item", code, true),
				made.length,
				made.map(frappe.utils.escape_html).join("、"),
			]),
		});
		this.form.clear();
		this.opts = await frappe.xcall("nila_app.products.get_style_options");
		this.existing = {};
		this.render_matrix();
	}
}
