// 庫存表：每款一個區塊，列＝各公司＋全公司合計＋建議補貨，欄＝甲型 × 尺寸＋小計。點數字看該格的異動明細。
frappe.pages["nila-stock-matrix"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("庫存表"), single_column: true });
	wrapper.nila = new NilaStockMatrix(page);
};

frappe.pages["nila-stock-matrix"].on_page_show = function (wrapper) {
	if (wrapper.nila && wrapper.nila.loaded) wrapper.nila.load(true);
};

class NilaStockMatrix {
	constructor(page) {
		this.page = page;
		this.page_length = 20;
		frappe.xcall("nila_app.matrix.get_options").then((o) => this.make(o));
	}

	make(o) {
		const p = this.page;
		const refresh = () => this.load(true);
		const blank = [{ value: "", label: "" }];
		this.fields = [
			p.add_field({ fieldtype: "Data", fieldname: "q", label: __("款式編號或名稱"), change: refresh }),
			p.add_field({ fieldtype: "Select", fieldname: "shape", label: __("甲型"), options: ["", ...o.shapes], change: refresh }),
			p.add_field({ fieldtype: "Select", fieldname: "size", label: __("尺寸"), options: ["", ...o.sizes], change: refresh }),
			p.add_field({ fieldtype: "Select", fieldname: "warehouse", label: __("公司"), options: [...blank, ...o.warehouses], change: refresh }),
			p.add_field({ fieldtype: "Select", fieldname: "status", label: __("商品狀態"), options: ["", "上架", "停售", "停產"], change: refresh }),
			p.add_field({ fieldtype: "Select", fieldname: "state", label: __("庫存狀態"), options: ["", "負庫存", "缺貨", "低庫存"], change: refresh }),
			p.add_field({ fieldtype: "Check", fieldname: "only_need", label: __("只看需補貨"), change: refresh }),
			p.add_field({ fieldtype: "Select", fieldname: "mode", label: __("顯示"), default: "actual", change: refresh,
				options: [{ value: "actual", label: __("實際庫存") }, { value: "projected", label: __("預計庫存（扣訂單、加已叫貨）") }] }),
		];
		p.add_inner_button(__("匯出 Excel"), () => {
			window.open(`/api/method/nila_app.matrix.export_matrix?filters=${encodeURIComponent(JSON.stringify(this.values()))}`);
		});
		p.add_inner_button(__("補貨建議"), () => frappe.set_route("nila-replenish"));
		this.$summary = $(`<div class="mb-2"></div>`).appendTo(p.body);
		$(nila.legend()).appendTo(p.body);
		this.$list = $(`<div class="nila-matrix"></div>`).appendTo(p.body);
		this.$more = $(`<button class="btn btn-default btn-sm mb-4">${__("顯示更多款式")}</button>`)
			.appendTo(p.body).hide().on("click", () => this.load(false));
		this.$list.on("click", "td[data-item]", (ev) => this.drill($(ev.currentTarget).data()));
		this.loaded = true;
		this.load(true);
	}

	values() {
		const v = {};
		this.fields.forEach((f) => (v[f.df.fieldname] = f.get_value()));
		return v;
	}

	async load(reset) {
		if (reset) this.start = 0;
		const r = await frappe.xcall("nila_app.matrix.get_matrix", {
			filters: this.values(), start: this.start, page_length: this.page_length,
		});
		if (reset) this.$list.empty();
		this.$list.append(r.styles.map((s) => nila.style_block(s)).join("") ||
			(reset ? `<p class="text-muted">${__("沒有符合條件的款式")}</p>` : ""));
		this.start += r.styles.length;
		this.$more.toggle(this.start < r.total).text(__("顯示更多款式（已顯示 {0}／{1}）", [this.start, r.total]));
		const s = r.summary;
		this.$summary.html(`<span class="text-muted">${__("符合 {0} 款", [r.total])}</span>
			${s.need_styles ? `・<a class="nila-need">${__("{0} 款需補貨，共 {1} 件", [s.need_styles, s.need_qty])}</a>` : ""}
			${s.negative ? `・<span class="nila-neg" style="padding:0 6px">${__("{0} 款有負庫存", [s.negative])}</span>` : ""}`);
		this.$summary.find(".nila-need").on("click", () => frappe.set_route("nila-replenish"));
	}

	drill({ item, wh }) {
		if (this.values().mode === "projected") {
			frappe.set_route("query-report", "Stock Projected Qty", { item_code: item, warehouse: wh || undefined });
			return;
		}
		frappe.set_route("query-report", "Stock Ledger", {
			company: frappe.defaults.get_user_default("Company"), from_date: "2000-01-01",
			to_date: frappe.datetime.get_today(), item_code: item, warehouse: wh || undefined,
		});
	}
}
