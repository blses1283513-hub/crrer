// 會員：同一個人有兩筆會員資料時，營運主管以上可以把這一筆合併到另一筆（消費紀錄移過去，這一筆刪除）。
frappe.ui.form.on("Customer", {
	refresh(frm) {
		const d = frm.doc;
		if (frm.is_new() || d.customer_group !== "會員") return;
		if (!frappe.user.has_role(["System Manager", "妮菈管理員", "妮菈營運主管"])) return;  // 伺服器也會再檢查
		frm.add_custom_button(__("合併到另一位會員"), () => {
			const dlg = new frappe.ui.Dialog({
				title: __("把「{0}」合併到…", [d.customer_name]),
				fields: [
					{ fieldtype: "Link", fieldname: "target", label: __("保留的會員"), options: "Customer", reqd: 1,
						get_query: () => ({ filters: { customer_group: "會員", name: ["!=", d.name] } }) },
					{ fieldtype: "HTML", options: `<p class="text-muted">${__("這一筆的消費紀錄會全部移到保留的會員，然後刪除這一筆，不能復原。")}</p>` },
				],
				primary_action_label: __("合併"),
				primary_action: async (v) => {
					const target = await frappe.xcall("nila_app.retail.merge_members", { source: d.name, target: v.target });
					dlg.hide();
					frappe.show_alert({ message: __("已合併到 {0}", [target]), indicator: "green" });
					frappe.set_route("Form", "Customer", target);
				},
			});
			dlg.show();
		});
	},
});
