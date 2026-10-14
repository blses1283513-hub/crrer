// 訂單：顯示每一行在各倉庫的庫存與調度（現貨、在途、調撥、已叫貨、還缺）；缺貨時一鍵建立在途調撥單。
// 出貨倉預設總公司，可改成分公司（整張訂單的「出貨倉」或每一行的倉庫）。
frappe.ui.form.on("Sales Order", {
	refresh(frm) {
		nila_so.render(frm);
	},
	set_warehouse(frm) {
		nila_so.later(frm);
	},
});

frappe.ui.form.on("Sales Order Item", {
	item_code: (frm) => nila_so.later(frm),
	qty: (frm) => nila_so.later(frm),
	warehouse: (frm) => nila_so.later(frm),
	items_remove: (frm) => nila_so.later(frm),
});

const nila_so = {
	later(frm) {
		clearTimeout(frm._nila_timer);
		frm._nila_timer = setTimeout(() => nila_so.render(frm), 800);
	},

	panel(frm) {
		const $grid = $(frm.fields_dict.items.wrapper);
		let $p = $grid.prev(".nila-so-panel");
		if (!$p.length) $p = $(`<div class="nila-so-panel mb-3"></div>`).insertBefore($grid);
		return $p;
	},

	async render(frm) {
		const $p = nila_so.panel(frm);
		if (frm.doc.docstatus === 2 || !(frm.doc.items || []).some((d) => d.item_code)) {
			$p.empty();
			return;
		}
		const r = await frappe.xcall("nila_app.dispatch.order_panel", { doc: frm.doc });
		const e = frappe.utils.escape_html;
		const label = Object.fromEntries(r.warehouses.map((w) => [w.name, w.label]));
		const whs = r.warehouses.filter((w) => !w.transit);
		const plan = (x) => {
			if (!x) return "";
			const parts = [];
			if (x.stock) parts.push(__("現貨 {0}", [x.stock]));
			if (x.transit) parts.push(__("在途 {0}", [x.transit]));
			if (x.transfer) parts.push(__("調撥 {0}（{1}）", [x.transfer, x.sources.map((s) => `${label[s[0]]} ${s[1]}`).join("、")]));
			if (x.ordered) parts.push(__("已叫貨 {0}", [x.ordered]));
			if (x.short) parts.push(`<span class="nila-neg" style="padding:0 4px">${__("還缺 {0}", [x.short])}</span>`);
			return parts.join("・");
		};
		const rows = r.lines.map((d) => `<tr><td>${d.idx}</td><td>${e(d.item)}<div class="small text-muted">${e(d.item_name || "")}</div></td>
			<td>${e(label[d.warehouse] || d.warehouse || "")}</td><td>${d.qty}${d.delivered ? `<div class="small text-muted">${__("已出 {0}", [d.delivered])}</div>` : ""}</td>
			${whs.map((w) => `<td class="${d.stock[w.name] < 0 ? "nila-neg" : w.name === d.warehouse ? "font-weight-bold" : "text-muted"}">${d.stock[w.name]}</td>`).join("")}
			<td>${plan(d.result)}</td></tr>`).join("");
		const status = frm.doc.docstatus === 1 ? frm.doc.nila_dispatch_status : r.status;
		const color = { 可出貨: "green", 待調撥: "orange", 已叫貨: "blue", 待叫貨: "red", 已出貨: "gray" }[status] || "gray";
		$p.html(`<div class="mb-1"><b>${__("各倉庫存與調度")}</b>
			${status ? `<span class="indicator-pill ${color} ml-2">${__(status)}</span>` : ""}
			<span class="text-muted small ml-2">${frm.doc.docstatus === 0 ? __("（未送出：排在所有已送出訂單之後計算）") : ""}</span></div>
			<div style="overflow-x:auto"><table class="nila-grid table-sm"><thead><tr><th>#</th><th>${__("規格")}</th><th>${__("出貨倉")}</th><th>${__("數量")}</th>
			${whs.map((w) => `<th>${e(w.label)}</th>`).join("")}<th>${__("分配")}</th></tr></thead><tbody>${rows}</tbody></table></div>
			${r.moving.length ? `<div class="small mt-1">${__("在途調撥單：")}${r.moving.map((m) => frappe.utils.get_form_link("Stock Entry", m.name, true)).join("、")}</div>` : ""}`);
		if (frm.doc.docstatus === 1 && r.transfers.length && r.can_transfer) {
			frm.remove_custom_button(__("建立調撥單"), __("調度"));
			frm.add_custom_button(__("建立調撥單"), () => nila_so.transfer_dialog(frm, r), __("調度"));
		}
	},

	transfer_dialog(frm, r) {
		const d = new frappe.ui.Dialog({
			title: __("建立調撥單"), size: "extra-large",
			fields: [{ fieldtype: "HTML", fieldname: "table" }],
			primary_action_label: __("建立調撥單"),
			primary_action: async () => {
				const picked = nila.collect($t, r.transfers);
				if (!picked) return;
				const names = await frappe.xcall("nila_app.replenish.create_transfers", { rows: picked });
				d.hide();
				frappe.msgprint(__("已建立調撥單：{0}。調入倉到貨後在調撥單按「到貨入庫」。",
					[names.map((n) => frappe.utils.get_form_link("Stock Entry", n, true)).join("、")]));
				frm.reload_doc();
			},
		});
		d.fields_dict.table.$wrapper.html(`<p class="text-muted small">${__("建立後調出倉的貨立即轉到在途；調入倉「到貨入庫」後才增加。")}</p>
			${nila.edit_table(r.transfers, nila.transfer_cols(), r.reasons, { qty_label: __("調撥數") })}`);
		const $t = d.fields_dict.table.$wrapper.find("table.nila-edit");
		nila.bind_edit_table($t);
		d.show();
	},
};
