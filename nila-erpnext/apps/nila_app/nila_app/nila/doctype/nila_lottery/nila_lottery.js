// 抽獎活動：設定條件後「預覽」看符合的人數與名單；確認後「產生名單」存成快照，可匯出 Excel。系統只判斷資格，不抽籤。
frappe.ui.form.on("Nila Lottery", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("預覽"), async () => {
			if (frm.is_dirty()) await frm.save();
			const r = await frappe.xcall("nila_app.lottery.preview", { name: frm.doc.name });
			const e = frappe.utils.escape_html;
			const d = new frappe.ui.Dialog({ title: __("預覽：{0} 人符合，名額合計 {1}", [r.count, r.entries]), size: "large",
				fields: [{ fieldtype: "HTML", fieldname: "t" }], primary_action_label: __("產生名單"),
				primary_action: () => { d.hide(); frm.trigger("nila_generate"); } });
			d.fields_dict.t.$wrapper.html(`<p class="text-muted small">${e(r.description)}</p>
				<table class="table table-sm table-bordered"><thead><tr><th>${__("姓名")}</th><th>${__("手機")}</th><th>${__("消費次數")}</th>
				<th>${__("消費淨額")}</th><th>${__("名額")}</th></tr></thead><tbody>
				${r.rows.map((x) => `<tr><td>${e(x.customer_name)}</td><td>${e(x.phone || "")}</td><td>${x.orders}</td>
					<td>${format_currency(x.net)}</td><td>${x.entries}</td></tr>`).join("") || `<tr><td colspan="5" class="text-muted">${__("沒有人符合")}</td></tr>`}
				</tbody></table>${r.more ? `<p class="text-muted">${__("還有 {0} 人未列出（產生名單後可匯出全部）", [r.more])}</p>` : ""}`);
			d.show();
		});
		frm.add_custom_button(__("產生名單"), () => frm.trigger("nila_generate")).addClass("btn-primary");
		frm.add_custom_button(__("已產生的名單"), () => frappe.set_route("List", "Nila Lottery Snapshot", { lottery: frm.doc.name }));
	},
	nila_generate(frm) {
		frappe.confirm(__("依目前的條件產生名單？名單會存成快照，之後不會變動（可以再產生新的）。"), async () => {
			if (frm.is_dirty()) await frm.save();
			const name = await frappe.xcall("nila_app.lottery.generate", { name: frm.doc.name });
			frappe.set_route("Form", "Nila Lottery Snapshot", name);
		});
	},
});
