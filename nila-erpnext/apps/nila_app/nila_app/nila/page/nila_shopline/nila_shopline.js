// SHOPLINE 官網訂單：連線設定（只有管理員；金鑰只顯示最後 4 碼）、同步狀態、官網訂單紀錄與待處理清單。
frappe.pages["nila-shopline"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("SHOPLINE 官網訂單"), single_column: true });
	wrapper.nila = new NilaShopline(page);
};

frappe.pages["nila-shopline"].on_page_show = function (wrapper) {
	wrapper.nila && wrapper.nila.load();
};

class NilaShopline {
	constructor(page) {
		this.page = page;
		this.state = "待處理";
		this.$status = $(`<div class="mb-3"></div>`).appendTo(page.body);
		this.$settings = $(`<div class="mb-4"></div>`).appendTo(page.body);
		this.$filters = $(`<div class="d-flex flex-wrap align-items-center mb-2" style="gap:6px"></div>`).appendTo(page.body);
		this.$orders = $(`<div></div>`).appendTo(page.body);
		page.set_secondary_action(__("重新整理"), () => this.load(), "refresh");
		this.load();
	}

	async load() {
		this.s = await frappe.xcall("nila_app.shopline.get_settings");
		this.render_status();
		if (this.s.can_edit && !this.settings_drawn) this.render_settings();
		this.load_orders();
	}

	render_status() {
		const s = this.s, e = frappe.utils.escape_html;
		const on = s.enabled ? `<span class="indicator-pill green">${__("自動同步：開啟")}</span>`
			: `<span class="indicator-pill gray">${__("自動同步：關閉")}</span>`;
		const warn = s.enabled && !s.scheduler ? `<div class="text-danger">${__("系統排程目前停用，自動同步不會執行")}</div>` : "";
		this.$status.html(`<div class="d-flex flex-wrap align-items-center" style="gap:12px">${on}
			${s.merchant_name ? `<span>${__("商店")}：<b>${e(s.merchant_name)}</b></span>` : ""}
			<span class="text-muted">${__("上次同步")}：${e(s.last_run || __("尚未同步"))}</span>
			${s.last_ok ? `<span class="text-muted">${__("上次成功")}：${e(s.last_ok)}</span>` : ""}</div>
			${s.last_result ? `<div class="mt-1 ${s.last_result.startsWith("失敗") ? "text-danger" : "text-muted"} nila-sl-result">${e(s.last_result)}</div>` : ""}${warn}`);
	}

	render_settings() {
		this.settings_drawn = true;
		const s = this.s, e = frappe.utils.escape_html;
		const since = (s.import_since || "").replace(" ", "T").slice(0, 16);
		this.$settings.html(`<div class="border rounded p-3">
			<h5 class="mb-3">${__("連線設定")}</h5>
			<div class="row">
				<div class="col-md-6 form-group"><label class="control-label">${__("API 金鑰（Access Token）")}</label>
					<input type="password" class="form-control nila-sl-token" autocomplete="new-password"
						placeholder="${s.token_set ? e(__("已設定（{0}），留空表示不變", [s.token_hint])) : e(__("貼上 SHOPLINE 後台產生的金鑰"))}">
					<div class="text-muted small mt-1">${__("在 SHOPLINE 後台「設定 → 管理員設定 → API 權限」產生。金鑰只存在這台電腦的系統裡，畫面不會再顯示完整內容；請不要貼到聊天或信件。")}</div></div>
				<div class="col-md-6 form-group"><label class="control-label">${__("商店代號（handle，測試連線成功後會自動帶入）")}</label>
					<input type="text" class="form-control nila-sl-handle" value="${e(s.handle)}"></div>
				<div class="col-md-3 form-group"><label class="control-label">${__("每幾分鐘同步一次")}</label>
					<input type="number" min="2" class="form-control nila-sl-interval" value="${e(String(s.interval))}"></div>
				<div class="col-md-5 form-group"><label class="control-label">${__("從這個時間之後的官網訂單開始匯入")}</label>
					<input type="datetime-local" class="form-control nila-sl-since" value="${e(since)}">
					<div class="text-muted small mt-1">${__("空白：從啟用的那一刻開始（不匯入以前的訂單）")}</div></div>
				<div class="col-md-4 form-group pt-4">
					<label class="mb-1 d-block"><input type="checkbox" class="nila-sl-pos" ${s.exclude_pos ? "checked" : ""}> ${__("不匯入 SHOPLINE 門市 POS 訂單")}</label>
					<label class="mb-0 d-block"><input type="checkbox" class="nila-sl-enabled" ${s.enabled ? "checked" : ""}> <b>${__("啟用自動同步")}</b></label></div>
			</div>
			<div class="d-flex flex-wrap" style="gap:8px">
				<button class="btn btn-primary btn-sm nila-sl-save">${__("儲存設定")}</button>
				<button class="btn btn-default btn-sm nila-sl-test">${__("測試連線")}</button>
				<button class="btn btn-default btn-sm nila-sl-sync">${__("立即同步")}</button>
				<span class="nila-sl-msg align-self-center"></span>
			</div></div>`);
		const $ = (c) => this.$settings.find(c);
		const msg = (text, ok) => $(".nila-sl-msg").attr("class", `nila-sl-msg align-self-center ${ok ? "text-success" : "text-danger"}`).text(text);
		$(".nila-sl-save").on("click", async () => {
			const since = $(".nila-sl-since").val();
			this.s = await frappe.xcall("nila_app.shopline.save_settings", { data: {
				token: $(".nila-sl-token").val(), handle: $(".nila-sl-handle").val(), interval: $(".nila-sl-interval").val(),
				import_since: since ? since.replace("T", " ") + ":00" : "", exclude_pos: $(".nila-sl-pos").is(":checked") ? 1 : 0,
				enabled: $(".nila-sl-enabled").is(":checked") ? 1 : 0 } });
			$(".nila-sl-token").val("").attr("placeholder", this.s.token_set ? __("已設定（{0}），留空表示不變", [this.s.token_hint]) : "");
			$(".nila-sl-since").val((this.s.import_since || "").replace(" ", "T").slice(0, 16));
			this.render_status();
			msg(__("已儲存"), true);
		});
		$(".nila-sl-test").on("click", async () => {
			msg(__("連線中…"), true);
			const r = await frappe.xcall("nila_app.shopline.test_connection", { token: $(".nila-sl-token").val(), handle: $(".nila-sl-handle").val() });
			msg(r.message, r.ok);
			if (r.ok && r.handle && !$(".nila-sl-handle").val()) $(".nila-sl-handle").val(r.handle);
		});
		$(".nila-sl-sync").on("click", async () => {
			msg(__("同步中…"), true);
			const r = await frappe.xcall("nila_app.shopline.sync_now");
			msg(r.message, r.ok);
			this.load();
		});
	}

	async load_orders() {
		const data = await frappe.xcall("nila_app.shopline.list_orders", { state: this.state, q: this.q || "" });
		const e = frappe.utils.escape_html;
		const states = [["", __("全部")], ...this.s.states.map((s) => [s, s])];
		this.$filters.html(states.map(([v, l]) => `<button class="btn btn-xs ${this.state === v ? "btn-primary" : "btn-default"}" data-state="${e(v)}">
			${e(l)}${v && data.counts[v] ? ` (${data.counts[v]})` : ""}</button>`).join("")
			+ `<input type="search" class="form-control form-control-sm ml-2" style="max-width:220px" placeholder="${__("搜尋單號、顧客、說明")}" value="${e(this.q || "")}">`);
		this.$filters.find("button").on("click", (ev) => { this.state = $(ev.currentTarget).data("state"); this.load_orders(); });
		this.$filters.find("input").on("change", (ev) => { this.q = ev.target.value; this.load_orders(); });
		const pill = { "已建立訂單": "green", "已取消訂單": "gray", "待處理": "orange", "略過": "gray", "已人工處理": "blue" };
		this.rows = data.rows;
		this.$orders.html(`<table class="table table-bordered table-sm"><thead><tr><th>${__("官網單號")}</th><th>${__("下單時間")}</th>
			<th>${__("顧客")}</th><th class="text-right">${__("金額")}</th><th>${__("官網狀態")}</th><th>${__("處理結果")}</th>
			<th>${__("銷售訂單")}</th><th>${__("商品")}</th><th>${__("說明")}</th><th></th></tr></thead><tbody>
			${data.rows.map((r, i) => `<tr data-i="${i}"><td>${e(r.order_number || r.name)}</td><td>${e(r.shopline_created || "")}</td>
				<td>${e(r.customer_name || "")}</td><td class="text-right">${r.total == null ? "" : format_currency(r.total)}</td>
				<td>${e(r.status || "")}${r.payment_status ? `<br><span class="text-muted small">${e(r.payment_status)}</span>` : ""}</td>
				<td style="white-space:nowrap"><span class="indicator-pill ${pill[r.state] || "gray"}">${e(r.state)}</span></td>
				<td>${r.sales_order ? `<a href="/app/sales-order/${encodeURIComponent(r.sales_order)}">${e(r.sales_order)}</a>` : ""}</td>
				<td class="small">${r.items.map((x) => `${e(x.sku)} × ${e(String(x.qty))}`).join("<br>")}</td>
				<td class="small">${e(r.message || "")}</td>
				<td>${r.state === "待處理" ? `<button class="btn btn-xs btn-default nila-sl-retry">${__("重新處理")}</button>
					<button class="btn btn-xs btn-default nila-sl-done mt-1">${__("標記已人工處理")}</button>` : ""}</td></tr>`).join("")
			|| `<tr><td colspan="10" class="text-muted">${__("沒有資料")}</td></tr>`}</tbody></table>
			<div class="text-muted small">${__("官網訂單會建立成「銷售訂單」（客戶：官網散客，從總公司出貨），不計入會員消費與抽獎。SHOPLINE 的 SKU 要和系統的料號相同（例如 0001-LT-XS）。")}</div>`);
		const row = (ev) => this.rows[Number($(ev.target).closest("tr").data("i"))];
		this.$orders.find(".nila-sl-retry").on("click", async (ev) => {
			const r = await frappe.xcall("nila_app.shopline.retry", { name: row(ev).name });
			frappe.show_alert({ message: `${r.state}${r.message ? "：" + r.message : ""}`, indicator: r.state === "待處理" ? "orange" : "green" }, 7);
			this.load();
		});
		this.$orders.find(".nila-sl-done").on("click", (ev) => {
			const r = row(ev);
			frappe.prompt([{ fieldtype: "Small Text", fieldname: "note", label: __("怎麼處理的（例如：已手動建立訂單、已退貨）") }], async (v) => {
				await frappe.xcall("nila_app.shopline.mark_handled", { name: r.name, note: v.note });
				this.load();
			}, __("標記已人工處理：{0}", [r.order_number || r.name]), __("標記"));
		});
	}
}
