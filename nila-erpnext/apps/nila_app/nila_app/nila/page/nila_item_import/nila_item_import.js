// 商品匯入匯出：下載範本、匯出全部商品；上傳試算表 → 預覽（不寫入）→ 匯入（背景執行，全部成功才寫入）。
frappe.pages["nila-item-import"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("商品匯入匯出"), single_column: true });
	wrapper.nila = new NilaItemImport(page);
};

class NilaItemImport {
	constructor(page) {
		this.page = page;
		const download = (method) => window.open(`/api/method/nila_app.importer.${method}`);
		page.add_inner_button(__("下載空白範本"), () => download("download_template"));
		page.add_inner_button(__("匯出全部商品"), () => download("export_items"));
		this.form = new frappe.ui.FieldGroup({
			parent: page.body,
			fields: [
				{ fieldtype: "HTML", options: `<p class="text-muted">${__(
					"一列＝一個規格。款式編號留空會自動編號；各公司欄位是新規格的期初庫存，已存在的規格不會改庫存（請用盤點）。大量匯入（例如第一次匯入全部商品）約需 30 分鐘，請在沒有人操作庫存時進行。"
				)}</p>` },
				{ fieldtype: "Attach", fieldname: "file", label: __("試算表（Excel 或 CSV）"), change: () => this.preview() },
				{ fieldtype: "HTML", fieldname: "result" },
			],
		});
		this.form.make();
		this.$result = $(this.form.get_field("result").wrapper);
		this.poll();
	}

	async preview() {
		const file_url = this.form.get_value("file");
		this.page.clear_primary_action();
		this.$result.empty();
		if (!file_url) return;
		this.$result.html(`<p class="text-muted">${__("檢查中…")}</p>`);
		const r = await frappe.xcall("nila_app.importer.preview", { file_url });
		const e = frappe.utils.escape_html;
		const c = r.counts || {};
		const list = (items, cls) => `<ul class="${cls}">${items.map((x) => `<li>${e(x)}</li>`).join("")}</ul>`;
		let html = "";
		if (r.errors.length) {
			html += `<div class="alert alert-danger"><b>${__("有 {0} 個錯誤，請修正試算表後重新上傳（不會匯入任何資料）", [r.errors.length])}</b>${list(r.errors, "mb-0")}</div>`;
		}
		if (r.warnings.length) html += `<div class="alert alert-warning">${list(r.warnings, "mb-0")}</div>`;
		if (!r.errors.length) {
			html += `<table class="table table-bordered" style="width:auto"><tbody>
				<tr><th>${__("新增款式")}</th><td>${c.new_styles}</td><th>${__("更新款式")}</th><td>${c.updated_styles}</td></tr>
				<tr><th>${__("新增規格")}</th><td>${c.new_variants}</td><th>${__("更新規格（補貨目標）")}</th><td>${c.updated_variants}</td></tr>
				<tr><th>${__("不變的規格")}</th><td>${c.unchanged_variants}</td><th>${__("期初庫存（件）")}</th><td>${c.stock_qty}</td></tr>
			</tbody></table>`;
			if (r.changes.length) {
				html += `<table class="table table-sm table-bordered"><thead><tr><th>${__("款式編號")}</th><th>${__("款式名稱")}</th>
					<th>${__("動作")}</th><th>${__("新增規格")}</th><th>${__("更新規格")}</th><th>${__("期初庫存")}</th></tr></thead><tbody>
					${r.changes.map((x) => `<tr><td>${e(x.code)}</td><td>${e(x.name)}</td><td>${e(x.action)}</td>
						<td>${x.new_variants}</td><td>${x.updated_variants}</td><td>${x.stock}</td></tr>`).join("")}
					</tbody></table>`;
				if (r.more) html += `<p class="text-muted">${__("還有 {0} 個款式未列出", [r.more])}</p>`;
			}
			const todo = c.new_styles + c.updated_styles + c.new_variants + c.updated_variants;
			if (todo) {
				this.page.set_primary_action(__("開始匯入"), () => this.start(file_url), "upload");
			} else {
				html += `<p>${__("沒有需要變更的資料。")}</p>`;
			}
		}
		this.$result.html(html);
	}

	start(file_url) {
		frappe.confirm(__("確定要匯入嗎？會在背景執行，全部成功才寫入。"), async () => {
			this.page.clear_primary_action();
			this.show(await frappe.xcall("nila_app.importer.start_import", { file_url }));
			this.poll();
		});
	}

	async poll() {
		clearTimeout(this.timer);
		const s = await frappe.xcall("nila_app.importer.import_status");
		this.show(s);
		if (s && ["queued", "running"].includes(s.state)) this.timer = setTimeout(() => this.poll(), 3000);
	}

	show(s) {
		if (!s || !s.state) return;
		const e = frappe.utils.escape_html;
		const $s = this.page.main.find(".nila-import-state").length
			? this.page.main.find(".nila-import-state")
			: $(`<div class="nila-import-state mb-4"></div>`).prependTo(this.page.body);
		const cls = { queued: "info", running: "info", done: "success", failed: "danger" }[s.state];
		let html = `<div class="alert alert-${cls}"><b>${e(s.message)}</b> <span class="text-muted small">${e(s.user || "")} ${e(s.time || "")}</span>`;
		if (s.state === "running" || s.state === "queued") {
			html += `<div class="progress mt-2"><div class="progress-bar" style="width:${s.progress || 0}%"></div></div>`;
		}
		if (s.state === "done" && s.counts) {
			html += `<div>${__("新增款式 {0}、更新款式 {1}、新增規格 {2}、更新規格 {3}、期初庫存 {4} 件", [
				s.counts.new_styles, s.counts.updated_styles, s.counts.new_variants, s.counts.updated_variants, s.counts.stock_qty])}</div>`;
		}
		$s.html(html + "</div>");
	}
}
