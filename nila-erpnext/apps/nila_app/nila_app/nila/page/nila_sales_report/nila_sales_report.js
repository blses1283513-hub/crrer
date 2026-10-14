// 消費報表：門市銷售扣掉退貨、退款後的淨額（官網訂單不算）。可依會員、門市或明細查看，匯出 Excel。
frappe.pages["nila-sales-report"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("消費報表"), single_column: true });
	wrapper.nila = new NilaSalesReport(page);
};

class NilaSalesReport {
	constructor(page) {
		this.page = page;
		frappe.xcall("nila_app.salesreport.get_options").then((o) => this.make(o));
	}

	make(o) {
		const p = this.page, refresh = () => this.load();
		const today = frappe.datetime.get_today();
		this.fields = [
			p.add_field({ fieldtype: "Date", fieldname: "from_date", label: __("開始"), default: frappe.datetime.month_start(), change: refresh }),
			p.add_field({ fieldtype: "Date", fieldname: "to_date", label: __("結束"), default: today, change: refresh }),
			p.add_field({ fieldtype: "Select", fieldname: "store", label: __("門市"), options: [{ value: "", label: "" }, ...o.stores], change: refresh }),
			p.add_field({ fieldtype: "Data", fieldname: "member", label: __("會員手機或姓名"), change: refresh }),
			p.add_field({ fieldtype: "Select", fieldname: "group", label: __("檢視"), default: "member", change: refresh,
				options: [{ value: "member", label: __("依會員") }, { value: "store", label: __("依門市") }, { value: "detail", label: __("明細") }] }),
		];
		p.add_inner_button(__("匯出 Excel"), () =>
			window.open(`/api/method/nila_app.salesreport.export_report?filters=${encodeURIComponent(JSON.stringify(this.values()))}`));
		this.$out = $(`<div></div>`).appendTo(p.body);
		this.load();
	}

	values() {
		const v = {};
		this.fields.forEach((f) => (v[f.df.fieldname] = f.get_value()));
		return v;
	}

	async load() {
		const r = await frappe.xcall("nila_app.salesreport.get_report", { filters: this.values() });
		const e = frappe.utils.escape_html, c = (v) => format_currency(v);
		const t = r.total;
		let head, body;
		if (r.group === "detail") {
			head = [__("單號"), __("日期"), __("門市"), __("客人"), __("類別"), __("金額"), __("收銀人員")];
			body = r.rows.map((x) => `<tr><td>${frappe.utils.get_form_link("Sales Invoice", x.key, true)}</td><td>${e(x.date)}</td>
				<td>${e(x.store)}</td><td>${e(x.customer || "")}</td><td>${e(x.kind)}</td><td class="text-right">${c(x.net)}</td><td>${e(x.cashier || "")}</td></tr>`);
		} else {
			const member = r.group === "member";
			head = [member ? __("會員") : __("門市"), ...(member ? [__("手機")] : []), __("消費次數"), __("銷售金額"), __("退款金額"), __("淨額"), __("最後消費日")];
			body = r.rows.map((x) => `<tr><td>${member ? frappe.utils.get_form_link("Customer", x.key, true, x.label) : e(x.label)}</td>
				${member ? `<td>${e(x.phone || "")}</td>` : ""}<td class="text-right">${x.orders}</td><td class="text-right">${c(x.gross)}</td>
				<td class="text-right">${c(x.refund)}</td><td class="text-right"><b>${c(x.net)}</b></td><td>${e(x.last_date)}</td></tr>`);
		}
		this.$out.html(`<p>${__("{0} 至 {1}", [r.from_date, r.to_date])}・${__("消費次數 {0}", [t.orders])}・${__("銷售 {0}", [c(t.gross)])}
			・${__("退款 {0}", [c(t.refund)])}・<b>${__("淨額 {0}", [c(t.net)])}</b>
			<span class="text-muted small">（${__("只計門市銷售；官網訂單不算；部分退款只扣退款金額")}）</span></p>
			<table class="table table-bordered table-sm"><thead><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr></thead>
			<tbody>${body.join("") || `<tr><td colspan="${head.length}" class="text-muted">${__("沒有資料")}</td></tr>`}</tbody></table>`);
	}
}
