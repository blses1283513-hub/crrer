// 補貨建議：建議補貨數＝補貨目標 − 全公司預計庫存；建議調撥＝出貨倉不夠出訂單、其他公司有剩。
// 勾選後建立補貨單（待叫貨）或在途調撥單；數量和建議不同要選原因；負庫存可以標註原因。
frappe.pages["nila-replenish"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("補貨建議"), single_column: true });
	wrapper.nila = new NilaReplenish(page);
};

frappe.pages["nila-replenish"].on_page_show = function (wrapper) {
	if (wrapper.nila && wrapper.nila.ready) wrapper.nila.load();
};

class NilaReplenish {
	constructor(page) {
		this.page = page;
		const refresh = () => this.load();
		frappe.xcall("nila_app.matrix.get_options").then((o) => {
			this.q = page.add_field({ fieldtype: "Data", fieldname: "q", label: __("款式編號或名稱"), change: refresh });
			this.shape = page.add_field({ fieldtype: "Select", fieldname: "shape", label: __("甲型"), options: ["", ...o.shapes], change: refresh });
			page.add_inner_button(__("庫存表"), () => frappe.set_route("nila-stock-matrix"));
			page.add_inner_button(__("補貨單（待叫貨）"), () => frappe.set_route("List", "Material Request", { status: "Pending" }));
			page.add_inner_button(__("在途調撥單"), () =>
				frappe.set_route("List", "Stock Entry", { add_to_transit: 1, docstatus: 1, per_transferred: ["<", 100] }));
			page.add_inner_button(__("調整紀錄"), () => frappe.set_route("List", "Nila Reason Log"));
			this.$summary = $(`<div class="mb-3"></div>`).appendTo(page.body);
			this.$buy = $(`<div class="mb-4"></div>`).appendTo(page.body);
			this.$move = $(`<div class="mb-4"></div>`).appendTo(page.body);
			this.ready = true;
			this.load();
		});
	}

	async load() {
		const r = await frappe.xcall("nila_app.replenish.get_suggestions", {
			filters: { q: this.q.get_value(), shape: this.shape.get_value() },
		});
		this.data = r;
		const s = r.summary;
		this.$summary.html(`<b>${__("{0} 個規格建議補貨，共 {1} 件", [s.items, s.qty])}</b>
			・${__("{0} 筆建議調撥", [s.transfers])}
			${s.negative ? `・<span class="nila-neg" style="padding:0 6px">${__("{0} 個規格負庫存", [s.negative])}</span>` : ""}
			<div class="text-muted small">${__("建議補貨＝補貨目標 − 全公司預計庫存（總公司＋各分公司＋在途，已扣訂單、已加補貨單與已叫貨）。建立補貨單後建議數會自動變 0，不會重複叫貨。停產不補。")}</div>`);
		this.render_buy(r);
		this.render_move(r);
	}

	render_buy(r) {
		const e = frappe.utils.escape_html;
		const rows = r.rows;
		this.buy_rows = rows;
		if (!rows.length) {
			this.$buy.html(`<h5>${__("建議叫貨")}</h5><p class="text-muted">${__("目前沒有需要補貨的規格")}</p>`);
			return;
		}
		const neg = (x) => x.actual < 0 || x.projected < 0;
		const cols = [
			{ label: __("規格"), html: (x) => `${frappe.utils.get_form_link("Item", x.item, true)}
				<div class="small text-muted">${e(x.style_name || "")} ${e(x.shape || "")} ${e(x.size || "")}${x.status !== "上架" ? `・${e(x.status)}` : ""}</div>` },
			{ label: __("補貨目標"), html: (x) => x.target },
			{ label: __("全公司實際"), html: (x) => `<span class="${x.actual < 0 ? "nila-neg" : ""}" style="padding:0 4px">${x.actual}</span>` },
			{ label: __("全公司預計"), html: (x) => `<span class="${x.projected < 0 ? "nila-neg" : ""}" style="padding:0 4px">${x.projected}</span>` },
			{ label: __("補貨單未叫貨"), html: (x) => x.requested || "" },
			{ label: __("已叫貨未到"), html: (x) => x.ordered || "" },
			{ label: __("負庫存原因"), html: (x) => neg(x)
				? `${e(x.negative_reason || "")} <a class="nila-neg-reason small" data-item="${e(x.item)}">${x.negative_reason ? __("修改") : __("標註")}</a>` : "" },
		];
		const pick = rows.filter((x) => x.suggest > 0 && x.can_order);
		this.$buy.html(`<h5>${__("建議叫貨")}</h5>${nila.edit_table(pick, cols, r.reasons["補貨調整"], { qty_label: __("叫貨數"), disabled: !r.can_manage })}
			${r.can_manage ? `<button class="btn btn-primary btn-sm nila-make-mr">${__("建立補貨單（待叫貨）")}</button>` : ""}
			${rows.length > pick.length ? `<h6 class="mt-3">${__("負庫存（不需叫貨）")}</h6>
				<table class="table table-sm table-bordered" style="width:auto"><tbody>${rows.filter((x) => !pick.includes(x))
					.map((x) => `<tr>${cols.map((c) => `<td>${c.html(x)}</td>`).join("")}</tr>`).join("")}</tbody></table>` : ""}`);
		const $t = this.$buy.find("table.nila-edit");
		nila.bind_edit_table($t);
		this.$buy.find(".nila-make-mr").on("click", () => {
			const picked = nila.collect($t, pick);
			if (!picked) return;
			frappe.confirm(__("建立補貨單：{0} 個規格，共 {1} 件？", [picked.length, picked.reduce((a, x) => a + x.qty, 0)]), async () => {
				const name = await frappe.xcall("nila_app.replenish.create_material_request", { rows: picked });
				frappe.msgprint(__("已建立補貨單 {0}（待叫貨）。叫貨後在補貨單按「已叫貨」。", [frappe.utils.get_form_link("Material Request", name, true)]));
				this.load();
			});
		});
		this.$buy.find(".nila-neg-reason").on("click", (ev) => this.negative_reason($(ev.currentTarget).data("item")));
	}

	render_move(r) {
		this.move_rows = r.transfers;
		if (!r.transfers.length) {
			this.$move.html(`<h5>${__("建議調撥")}</h5><p class="text-muted">${__("目前沒有需要調撥的訂單")}</p>`);
			return;
		}
		this.$move.html(`<h5>${__("建議調撥")}</h5>
			<p class="text-muted small">${__("出貨倉的庫存不夠出訂單、其他公司有剩時，先調撥（例如門市調回總公司），不夠的部分才算進叫貨。建立後調出倉的貨立即轉到在途，調入倉「到貨入庫」後才增加。")}</p>
			${nila.edit_table(r.transfers, nila.transfer_cols(), r.reasons["調撥調整"], { qty_label: __("調撥數"), disabled: !r.can_manage })}
			${r.can_manage ? `<button class="btn btn-primary btn-sm nila-make-move">${__("建立調撥單")}</button>` : ""}`);
		const $t = this.$move.find("table.nila-edit");
		nila.bind_edit_table($t);
		this.$move.find(".nila-make-move").on("click", () => {
			const picked = nila.collect($t, r.transfers);
			if (!picked) return;
			frappe.confirm(__("建立 {0} 筆調撥？調出倉的貨會立即轉到在途。", [picked.length]), async () => {
				const names = await frappe.xcall("nila_app.replenish.create_transfers", { rows: picked });
				frappe.msgprint(__("已建立調撥單：{0}", [names.map((n) => frappe.utils.get_form_link("Stock Entry", n, true)).join("、")]));
				this.load();
			});
		});
	}

	negative_reason(item) {
		frappe.prompt([
			{ fieldtype: "Select", fieldname: "reason", label: __("負庫存原因"), options: ["", ...this.data.reasons["負庫存"]], reqd: 1 },
			{ fieldtype: "Small Text", fieldname: "note", label: __("備註") },
		], async (v) => {
			await frappe.xcall("nila_app.replenish.set_negative_reason", { item, reason: v.reason, note: v.note });
			this.load();
		}, __("{0} 負庫存原因", [item]), __("儲存"));
	}
}
