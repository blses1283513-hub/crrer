// 門市銷售：掃碼（掃碼槍）或輸入料號 → 數量 → 選會員（可不選）→ 結帳，扣該門市庫存並記一筆消費。
// 店長以上可改價、可退貨。每一筆結帳有固定的結帳代碼，網路斷掉重送也不會重複扣庫存。
frappe.pages["nila-store-sale"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("門市銷售"), single_column: true });
	wrapper.nila = new NilaStoreSale(page);
};

frappe.pages["nila-store-sale"].on_page_show = function (wrapper) {
	if (wrapper.nila && wrapper.nila.$scan) setTimeout(() => wrapper.nila.$scan.trigger("focus"), 300);
};

class NilaStoreSale {
	constructor(page) {
		this.page = page;
		this.cart = [];
		this.member = null;
		this.new_client_id();
		frappe.xcall("nila_app.retail.sale_context").then((ctx) => this.make(ctx));
	}

	new_client_id() {
		this.client_id = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : frappe.utils.get_random(32);
	}

	make(ctx) {
		this.ctx = ctx;
		const p = this.page;
		if (!ctx.stores.length) {
			$(p.body).html(`<p class="text-muted">${__("你的帳號還沒有設定門市，請管理員在「帳號管理」設定。")}</p>`);
			return;
		}
		this.store = p.add_field({ fieldtype: "Select", fieldname: "store", label: __("門市"), options: ctx.stores,
			default: ctx.stores[0].value, change: () => this.$scan.trigger("focus") });
		if (ctx.stores.length === 1) this.store.$wrapper.find("select").prop("disabled", true);
		if (ctx.can_return) p.add_inner_button(__("退貨／退款"), () => this.return_dialog());
		p.add_inner_button(__("今日銷售"), () => frappe.set_route("List", "Sales Invoice", { nila_channel: "門市", posting_date: frappe.datetime.get_today() }));
		// 不能用 p.body.html()：會把上方的門市選單一起清掉
		$(`<div class="nila-sale"></div>`).appendTo(p.body).html(`
			<div class="row">
			<div class="col-md-8">
				<input class="form-control input-lg nila-scan mb-2" placeholder="${__("掃碼或輸入料號後按 Enter")}" autocomplete="off">
				<table class="table table-bordered nila-cart"><thead><tr>
					<th>${__("規格")}</th><th style="width:110px">${__("數量")}</th><th style="width:130px">${__("單價")}</th>
					<th style="width:110px">${__("小計")}</th><th style="width:40px"></th></tr></thead><tbody></tbody></table>
			</div>
			<div class="col-md-4">
				<div class="frappe-card p-3 mb-3">
					<div class="mb-2"><b>${__("會員")}</b></div>
					<div class="nila-member mb-2"></div>
					<div class="input-group mb-2"><input class="form-control nila-member-q" placeholder="${__("手機或姓名")}">
						<button class="btn btn-default nila-member-find">${__("找")}</button></div>
					<button class="btn btn-default btn-sm nila-member-new">${__("新增會員")}</button>
				</div>
				<div class="frappe-card p-3">
					<div class="text-muted">${__("合計")}</div><div class="nila-total" style="font-size:2rem;font-weight:700">0</div>
					<button class="btn btn-primary btn-lg btn-block mt-2 nila-pay">${__("結帳")}</button>
					<button class="btn btn-default btn-sm btn-block mt-2 nila-clear">${__("清空")}</button>
					<div class="nila-last small text-muted mt-2"></div>
				</div>
			</div></div>`);
		this.$scan = $(p.body).find(".nila-scan");
		this.$scan.on("keydown", (ev) => {
			if (ev.key === "Enter") {
				ev.preventDefault();
				const code = this.$scan.val().trim();
				this.$scan.val("");
				if (code) this.add_code(code);
			}
		});
		$(p.body).find(".nila-member-find").on("click", () => this.find_member());
		$(p.body).find(".nila-member-q").on("keydown", (ev) => ev.key === "Enter" && this.find_member());
		$(p.body).find(".nila-member-new").on("click", () => this.new_member());
		$(p.body).find(".nila-pay").on("click", () => this.pay());
		$(p.body).find(".nila-clear").on("click", () => frappe.confirm(__("清空這筆結帳？"), () => this.reset()));
		$(p.body).find(".nila-cart").on("change", "input", (ev) => {
			const $i = $(ev.target), i = Number($i.closest("tr").data("i"));
			const v = Number($i.val());
			if ($i.hasClass("nila-qty")) this.cart[i].qty = Math.max(1, Math.round(v) || 1);
			if ($i.hasClass("nila-rate")) this.cart[i].rate = v >= 0 ? v : this.cart[i].list_rate;
			this.render();
		}).on("click", ".nila-del", (ev) => {
			this.cart.splice(Number($(ev.target).closest("tr").data("i")), 1);
			this.render();
		});
		this.render();
		this.$scan.trigger("focus");
	}

	async add_code(code) {
		const r = await frappe.xcall("nila_app.retail.lookup_item", { code });
		if (r.exact) return this.add_item(r.items[0]);
		if (!r.items.length) {
			frappe.show_alert({ message: __("找不到：{0}", [code]), indicator: "red" });
			frappe.utils.play_sound("error");
			return;
		}
		const d = new frappe.ui.Dialog({ title: __("選擇規格"), fields: [{ fieldtype: "HTML", fieldname: "list" }] });
		const e = frappe.utils.escape_html;
		d.fields_dict.list.$wrapper.html(r.items.map((it, i) =>
			`<button class="btn btn-default btn-block text-left nila-pick" data-i="${i}">${e(it.item)} ${e(it.item_name)}　${it.rate ?? ""}</button>`).join(""));
		d.fields_dict.list.$wrapper.on("click", ".nila-pick", (ev) => { d.hide(); this.add_item(r.items[Number($(ev.currentTarget).data("i"))]); });
		d.show();
	}

	add_item(it) {
		const line = this.cart.find((l) => l.item === it.item && l.rate === (it.rate || 0));
		if (line) line.qty += 1;
		else this.cart.push({ item: it.item, item_name: it.item_name, status: it.status, qty: 1, rate: it.rate || 0, list_rate: it.rate || 0 });
		this.render();
		this.$scan.trigger("focus");
	}

	render() {
		const e = frappe.utils.escape_html;
		const can_price = this.ctx.can_price;
		$(this.page.body).find(".nila-cart tbody").html(this.cart.map((l, i) => `<tr data-i="${i}">
			<td>${e(l.item)}<div class="small text-muted">${e(l.item_name || "")}${l.status && l.status !== "上架" ? `・<span class="text-danger">${e(l.status)}</span>` : ""}</div></td>
			<td><input type="number" min="1" step="1" class="form-control nila-qty" value="${l.qty}"></td>
			<td>${can_price ? `<input type="number" min="0" class="form-control nila-rate" value="${l.rate}">` : format_currency(l.rate)}
				${l.rate !== l.list_rate ? `<div class="small text-muted">${__("原價 {0}", [l.list_rate])}</div>` : ""}</td>
			<td>${format_currency(l.qty * l.rate)}</td>
			<td><button class="btn btn-xs btn-default nila-del">✕</button></td></tr>`).join("") ||
			`<tr><td colspan="5" class="text-muted">${__("尚未加入商品")}</td></tr>`);
		const total = this.cart.reduce((a, l) => a + l.qty * l.rate, 0);
		$(this.page.body).find(".nila-total").text(format_currency(total));
		const m = this.member;
		$(this.page.body).find(".nila-member").html(m
			? `<span class="indicator-pill blue">${e(m.customer_name)} ${e(m.phone || "")}</span> <a class="nila-member-clear small">${__("取消")}</a>`
			: `<span class="text-muted">${__("未選（門市散客）")}</span>`);
		$(this.page.body).find(".nila-member-clear").on("click", () => { this.member = null; this.render(); });
	}

	async find_member() {
		const q = $(this.page.body).find(".nila-member-q").val().trim();
		if (!q) return;
		const rows = await frappe.xcall("nila_app.retail.find_member", { q });
		if (rows.length === 1) { this.member = rows[0]; this.render(); return; }
		if (!rows.length) {
			frappe.confirm(__("找不到會員「{0}」，要新增嗎？", [q]), () => this.new_member(q));
			return;
		}
		const e = frappe.utils.escape_html;
		const d = new frappe.ui.Dialog({ title: __("選擇會員"), fields: [{ fieldtype: "HTML", fieldname: "list" }] });
		d.fields_dict.list.$wrapper.html(rows.map((m, i) =>
			`<button class="btn btn-default btn-block text-left nila-pick" data-i="${i}">${e(m.customer_name)}　${e(m.phone || "")}</button>`).join(""));
		d.fields_dict.list.$wrapper.on("click", ".nila-pick", (ev) => { d.hide(); this.member = rows[Number($(ev.currentTarget).data("i"))]; this.render(); });
		d.show();
	}

	new_member(q) {
		const is_phone = q && /^[\d+\-\s()]+$/.test(q);
		frappe.prompt([
			{ fieldtype: "Data", fieldname: "customer_name", label: __("姓名"), reqd: 1, default: is_phone ? "" : (q || "") },
			{ fieldtype: "Data", fieldname: "phone", label: __("手機"), reqd: 1, default: is_phone ? q : "" },
		], async (v) => {
			this.member = await frappe.xcall("nila_app.retail.create_member", v);
			frappe.show_alert({ message: __("已新增會員"), indicator: "green" });
			this.render();
		}, __("新增會員"), __("新增"));
	}

	pay() {
		if (!this.cart.length) return frappe.msgprint(__("尚未加入商品"));
		const total = this.cart.reduce((a, l) => a + l.qty * l.rate, 0);
		frappe.confirm(__("結帳 {0}，會員：{1}？", [format_currency(total), this.member ? this.member.customer_name : __("門市散客")]), async () => {
			const btn = $(this.page.body).find(".nila-pay").prop("disabled", true);
			try {
				const r = await frappe.xcall("nila_app.retail.checkout", { data: {
					client_id: this.client_id, store: this.store.get_value(), member: this.member && this.member.name,
					lines: this.cart.map((l) => ({ item: l.item, qty: l.qty, rate: l.rate === l.list_rate ? null : l.rate })),
				} });
				$(this.page.body).find(".nila-last").html(__("已結帳 {0}：{1}", [frappe.utils.get_form_link("Sales Invoice", r.name, true), format_currency(r.total)]));
				frappe.show_alert({ message: __("結帳完成 {0}", [format_currency(r.total)]), indicator: "green" });
				this.reset();
			} catch (err) {
				// 沒有成功（例如網路斷了）：保留購物車與結帳代碼，再按一次結帳不會重複扣庫存
			} finally {
				btn.prop("disabled", false);
			}
		});
	}

	reset() {
		this.cart = [];
		this.member = null;
		this.new_client_id();
		$(this.page.body).find(".nila-member-q").val("");
		this.render();
		this.$scan.trigger("focus");
	}

	return_dialog() {
		const d = new frappe.ui.Dialog({
			title: __("退貨／退款"), size: "extra-large",
			fields: [
				{ fieldtype: "Data", fieldname: "q", label: __("銷售單號或會員手機") },
				{ fieldtype: "Button", fieldname: "find", label: __("查詢") },
				{ fieldtype: "HTML", fieldname: "result" },
			],
		});
		const e = frappe.utils.escape_html;
		let sales = [];
		d.fields_dict.find.$input.on("click", async () => {
			sales = await frappe.xcall("nila_app.retail.find_sales", { q: d.get_value("q") });
			const uuid = () => ((window.crypto && crypto.randomUUID) ? crypto.randomUUID() : frappe.utils.get_random(32));
			// 每一筆銷售一個固定的退貨代碼：網路斷掉後再按一次「確認」不會重複退款
			d.fields_dict.result.$wrapper.html(sales.map((s, i) => `<div class="frappe-card p-2 mb-2" data-i="${i}" data-cid="${uuid()}">
				<b>${e(s.name)}</b> ${e(s.posting_date)} ${e(s.customer_name || "")} ${format_currency(s.total)}
				<table class="table table-sm mt-1"><thead><tr><th>${__("規格")}</th><th>${__("售出")}</th><th>${__("可退")}</th><th>${__("單價")}</th>
				<th>${__("退幾件")}</th><th>${__("退款金額（空白＝全額）")}</th></tr></thead><tbody>
				${s.lines.map((l) => `<tr data-row="${e(l.row)}"><td>${e(l.item)}</td><td>${l.qty}</td><td>${l.qty - l.returned}</td><td>${l.rate}</td>
					<td><input type="number" min="0" max="${l.qty - l.returned}" class="form-control input-xs nila-rqty" value="0" ${l.qty - l.returned ? "" : "disabled"}></td>
					<td><input type="number" min="0" class="form-control input-xs nila-ramt" ${l.qty - l.returned ? "" : "disabled"}></td></tr>`).join("")}
				</tbody></table>
				<div class="d-flex" style="gap:8px">
					<select class="form-control input-xs nila-mode" style="width:auto">
						<option value="goods">${__("退貨（商品退回門市庫存）")}</option><option value="refund">${__("只退款（商品不退回，處理 1 件）")}</option></select>
					<input class="form-control input-xs nila-reason" placeholder="${__("原因")}">
					<button class="btn btn-primary btn-xs nila-do">${__("確認")}</button></div></div>`).join("")
				|| `<p class="text-muted">${__("找不到門市銷售")}</p>`);
		});
		d.fields_dict.result.$wrapper.on("click", ".nila-do", (ev) => {
			const $c = $(ev.target).closest("[data-i]"), s = sales[Number($c.data("i"))];
			const mode = $c.find(".nila-mode").val();
			const lines = [];
			$c.find("tbody tr").each((_, tr) => {
				const qty = Number($(tr).find(".nila-rqty").val() || 0), amt = $(tr).find(".nila-ramt").val();
				if (qty > 0 || (mode === "refund" && amt)) lines.push({ row: $(tr).data("row"), qty: qty || 1, amount: amt === "" ? null : Number(amt) });
			});
			if (!lines.length) return frappe.msgprint(__("請填要退的件數或金額"));
			const client_id = $c.data("cid");
			frappe.confirm(__("確定{0}？", [mode === "goods" ? __("退貨") : __("只退款")]), async () => {
				const r = await frappe.xcall("nila_app.retail.make_return", { data: {
					client_id, invoice: s.name, mode, lines, reason: $c.find(".nila-reason").val() } });
				d.hide();
				frappe.msgprint(__("已建立 {0}，退款 {1}", [frappe.utils.get_form_link("Sales Invoice", r.name, true), format_currency(-r.total)]));
			});
		});
		d.show();
	}
}
