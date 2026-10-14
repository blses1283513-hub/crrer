// 會員匯入：下載範本 → 上傳名單（姓名、手機）→ 預覽（不寫入）→ 匯入（背景執行，全部成功才寫入）。
frappe.pages["nila-member-import"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("會員匯入"), single_column: true });
	wrapper.nila = new NilaMemberImport(page);
};

class NilaMemberImport {
	constructor(page) {
		this.page = page;
		page.add_inner_button(__("下載空白範本"), () => window.open("/api/method/nila_app.memberimport.download_template"));
		this.form = new frappe.ui.FieldGroup({
			parent: page.body,
			fields: [
				{ fieldtype: "HTML", options: `<p class="text-muted">${__(
					"名單兩欄：姓名、手機（例：0912345678，有沒有橫線、+886 都可以）。手機已經是會員的會略過，不會改原本的資料。有任何錯誤時不會匯入，請修正後重新上傳。"
				)}</p>` },
				{ fieldtype: "Attach", fieldname: "file", label: __("會員名單（Excel 或 CSV）"), change: () => this.preview() },
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
		const r = await frappe.xcall("nila_app.memberimport.preview", { file_url });
		const e = frappe.utils.escape_html;
		const list = (items) => `<ul class="mb-0">${items.map((x) => `<li>${e(x)}</li>`).join("")}</ul>`;
		let html = "";
		if (r.errors.length) {
			html += `<div class="alert alert-danger"><b>${__("有 {0} 個錯誤，請修正後重新上傳（不會匯入任何資料）", [r.errors.length])}</b>${list(r.errors)}</div>`;
		}
		if (r.warnings.length) html += `<div class="alert alert-warning">${list(r.warnings)}</div>`;
		if (!r.errors.length) {
			html += `<p><b>${__("新增 {0} 位會員", [r.new])}</b>　${__("略過 {0} 位（已經是會員）", [r.skipped])}</p>`;
			if (r.sample.length) {
				html += `<table class="table table-sm table-bordered" style="width:auto"><thead><tr><th>${__("列")}</th><th>${__("姓名")}</th><th>${__("手機")}</th></tr></thead><tbody>
					${r.sample.map((m) => `<tr><td>${m.row}</td><td>${e(m.name)}</td><td>${e(m.phone)}</td></tr>`).join("")}</tbody></table>`;
				if (r.new > r.sample.length) html += `<p class="text-muted">${__("只列出前 {0} 位", [r.sample.length])}</p>`;
				this.page.set_primary_action(__("開始匯入"), () => this.start(file_url), "upload");
			} else {
				html += `<p>${__("沒有需要新增的會員。")}</p>`;
			}
		}
		this.$result.html(html);
	}

	start(file_url) {
		frappe.confirm(__("確定要匯入嗎？會在背景執行，全部成功才寫入。"), async () => {
			this.page.clear_primary_action();
			this.show(await frappe.xcall("nila_app.memberimport.start_import", { file_url }));
			this.poll();
		});
	}

	async poll() {
		clearTimeout(this.timer);
		const s = await frappe.xcall("nila_app.memberimport.import_status");
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
		$s.html(html + "</div>");
	}
}
