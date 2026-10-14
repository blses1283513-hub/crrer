// 抽獎名單快照：不能修改，可匯出 Excel。
frappe.ui.form.on("Nila Lottery Snapshot", {
	refresh(frm) {
		frm.disable_save();
		frm.add_custom_button(__("匯出 Excel"), () =>
			window.open(`/api/method/nila_app.lottery.export_snapshot?name=${encodeURIComponent(frm.doc.name)}`)).addClass("btn-primary");
	},
});
