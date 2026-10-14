// 妮菈共用：庫存狀態顏色、圖例、款式區塊表格（庫存表、補貨、訂單面板共用）。
frappe.provide("nila");

nila.STATE_CLASS = { 負庫存: "nila-neg", 缺貨: "nila-out", 低庫存: "nila-low", 正常: "nila-ok" };

nila.legend = function () {
	return `<div class="nila-legend small mb-2">${["負庫存", "缺貨", "低庫存", "正常"]
		.map((s) => `<span class="${nila.STATE_CLASS[s]}">${__(s)}</span>`)
		.join("")}<span class="text-muted" style="border:0">${__("缺貨、低庫存看「全公司合計」列（低庫存＝低於補貨目標）；各公司只標負庫存")}</span></div>`;
};

nila.qty = function (v) {
	return v === null || v === undefined || v === "" ? "" : String(v);
};

// 款式區塊：欄＝甲型（上層）× 尺寸（下層）＋小計；列＝各公司、全公司合計、建議補貨。
// style = {code, name, status, columns: [{shape, sizes: [{size, item}]}], rows: [{label, warehouse, kind, cells: {料號: {q, s}}, sum, sum_state}]}
nila.style_block = function (style) {
	const e = frappe.utils.escape_html;
	const cols = style.columns.flatMap((c) => c.sizes);
	const top = style.columns.map((c) => `<th colspan="${c.sizes.length}">${e(c.shape)}</th>`).join("");
	const sub = cols.map((c) => `<th>${e(c.size)}</th>`).join("");
	const body = style.rows
		.map((r) => {
			const cells = cols
				.map((c) => {
					if (!c.item) return `<td class="nila-blank"></td>`;
					const v = r.cells[c.item];
					if (!v) return `<td></td>`;
					const data = r.kind === "suggest" ? "" : `data-item="${e(c.item)}" data-wh="${e(r.warehouse || "")}"`;
					const cls = nila.STATE_CLASS[v.s] || (v.q === 0 ? "text-muted" : "");
					return `<td class="${cls}" ${data} title="${e(c.item)}">${nila.qty(v.q)}</td>`;
				})
				.join("");
			return `<tr class="nila-${r.kind}"><td class="nila-label">${e(r.label)}</td>${cells}
				<td class="${nila.STATE_CLASS[r.sum_state] || ""}">${nila.qty(r.sum)}</td></tr>`;
		})
		.join("");
	const link = frappe.utils.get_form_link("Item", style.code, true, `${style.code} ${style.name}`);
	return `<div class="nila-style"><h5>${link} <span class="text-muted small">${e(style.status || "")}</span></h5>
		<table class="nila-grid table-sm"><thead><tr><th rowspan="2"></th>${top}<th rowspan="2">${__("小計")}</th></tr>
		<tr>${sub}</tr></thead><tbody>${body}</tbody></table></div>`;
};

// 可修改數量的建議表（補貨建議頁的叫貨、調撥，訂單畫面的調撥共用）：數量改得和建議不同時要選原因。
// cols: [{label, html(row)}]；rows 每列需有 suggest；回傳 HTML，用 nila.collect($table, rows) 取回勾選的列。
nila.edit_table = function (rows, cols, reasons, opts = {}) {
	const e = frappe.utils.escape_html;
	const reason_opts = `<option value=""></option>${reasons.map((r) => `<option>${e(r)}</option>`).join("")}`;
	const head = cols.map((c) => `<th>${c.label}</th>`).join("");
	const body = rows
		.map((r, i) => `<tr data-i="${i}">
			<td><input type="checkbox" class="nila-pick" ${opts.checked === false ? "" : "checked"} ${opts.disabled ? "disabled" : ""}></td>
			${cols.map((c) => `<td>${c.html(r)}</td>`).join("")}
			<td>${r.suggest}</td>
			<td><input type="number" min="0" step="1" class="form-control input-xs nila-qty" style="width:80px" value="${r.suggest}" ${opts.disabled ? "disabled" : ""}></td>
			<td><select class="form-control input-xs nila-reason" style="min-width:120px" ${opts.disabled ? "disabled" : ""}>${reason_opts}</select></td>
			<td><input type="text" class="form-control input-xs nila-note" placeholder="${__("備註")}" ${opts.disabled ? "disabled" : ""}></td>
		</tr>`)
		.join("");
	return `<table class="table table-sm table-bordered nila-edit" style="width:auto">
		<thead><tr><th><input type="checkbox" class="nila-pick-all" ${opts.checked === false ? "" : "checked"}></th>${head}
		<th>${__("建議")}</th><th>${opts.qty_label || __("數量")}</th><th>${__("原因（數量和建議不同時必填）")}</th><th>${__("備註")}</th></tr></thead>
		<tbody>${body}</tbody></table>`;
};

nila.bind_edit_table = function ($table) {
	$table.find(".nila-pick-all").on("change", (ev) => $table.find(".nila-pick:enabled").prop("checked", ev.target.checked));
	$table.find(".nila-qty").on("input", (ev) => {
		const $tr = $(ev.target).closest("tr");
		const changed = String(ev.target.value) !== String($tr.find("td").eq(-4).text());
		$tr.find(".nila-reason").toggleClass("border-danger", changed && !$tr.find(".nila-reason").val());
	});
};

// 取回勾選的列：[{...原本的列, qty, reason, note}]；數量和建議不同卻沒選原因時提示並回傳 null。
nila.collect = function ($table, rows) {
	const out = [];
	let missing = [];
	$table.find("tbody tr").each((_, tr) => {
		const $tr = $(tr);
		if (!$tr.find(".nila-pick").prop("checked")) return;
		const r = rows[Number($tr.data("i"))];
		const qty = Number($tr.find(".nila-qty").val() || 0);
		const reason = $tr.find(".nila-reason").val();
		if (qty !== Number(r.suggest) && !reason) missing.push(r.item);
		if (qty > 0) out.push(Object.assign({}, r, { qty, reason, note: $tr.find(".nila-note").val() }));
	});
	if (missing.length) {
		frappe.msgprint(__("數量和建議不同，請選擇原因：{0}", [missing.join("、")]));
		return null;
	}
	if (!out.length) {
		frappe.msgprint(__("請勾選至少一列，數量要大於 0"));
		return null;
	}
	return out;
};

// 調撥建議的欄位（補貨建議頁與訂單畫面共用）
nila.transfer_cols = function () {
	const e = frappe.utils.escape_html;
	return [
		{ label: __("規格"), html: (r) => `${frappe.utils.get_form_link("Item", r.item, true)}<div class="small text-muted">${e(r.item_name || "")}</div>` },
		{ label: __("調出"), html: (r) => e(r.from_label) },
		{ label: __("調入"), html: (r) => e(r.to_label) },
		{ label: __("訂單"), html: (r) => (r.orders || []).map((o) => frappe.utils.get_form_link("Sales Order", o, true)).join("<br>") },
	];
};
