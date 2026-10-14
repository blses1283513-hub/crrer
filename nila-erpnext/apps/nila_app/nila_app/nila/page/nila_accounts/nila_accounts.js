// 帳號管理（只有管理員）：新增帳號、設定層級與門市、停用、重設密碼。帳號用來登入，不需要信箱。
frappe.pages["nila-accounts"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("帳號管理"), single_column: true });
	wrapper.nila = new NilaAccounts(page);
};

class NilaAccounts {
	constructor(page) {
		this.page = page;
		page.set_primary_action(__("新增帳號"), () => this.edit(), "add");
		this.$out = $(`<div></div>`).appendTo(page.body);
		$(`<div class="text-muted small mt-3">${__("1 管理員：全部（含帳號管理、成本）。2 營運主管：商品、售價、成本、補貨叫貨、調度、會員合併、抽獎、全部報表。3 總公司作業：訂單、出貨、調撥、盤點、看庫存表與補貨建議（看不到成本）。4 門市店長：自己門市的銷售、退貨、改價、盤點、到貨入庫、消費報表。5 門市店員：自己門市的銷售、會員、看庫存。")}</div>`).appendTo(page.body);
		this.load();
	}

	async load() {
		this.data = await frappe.xcall("nila_app.accounts.list_accounts");
		const e = frappe.utils.escape_html;
		this.$out.html(`<table class="table table-bordered"><thead><tr><th>${__("姓名")}</th><th>${__("帳號")}</th><th>${__("層級")}</th>
			<th>${__("門市")}</th><th>${__("最後登入")}</th><th>${__("狀態")}</th><th></th></tr></thead><tbody>
			${this.data.accounts.map((a, i) => `<tr class="${a.enabled ? "" : "text-muted"}" data-i="${i}"><td>${e(a.full_name || "")}</td>
				<td>${e(a.username || a.name)}</td><td>${e(a.level_label)}</td><td>${e(a.store_labels.join("、") || (a.level ? __("全部") : ""))}</td>
				<td>${e(a.last_login || "")}</td><td>${a.enabled ? __("使用中") : __("已停用")}</td>
				<td><button class="btn btn-xs btn-default nila-edit">${__("修改")}</button>
					<button class="btn btn-xs btn-default nila-pw">${__("重設密碼")}</button>
					${a.name === this.data.me ? "" : `<button class="btn btn-xs btn-default nila-toggle">${a.enabled ? __("停用") : __("啟用")}</button>`}</td></tr>`).join("")
			|| `<tr><td colspan="7" class="text-muted">${__("還沒有帳號")}</td></tr>`}</tbody></table>`);
		const row = (ev) => this.data.accounts[Number($(ev.target).closest("tr").data("i"))];
		this.$out.find(".nila-edit").on("click", (ev) => this.edit(row(ev)));
		this.$out.find(".nila-pw").on("click", (ev) => this.password(row(ev)));
		this.$out.find(".nila-toggle").on("click", (ev) => {
			const a = row(ev);
			frappe.confirm(a.enabled ? __("停用 {0}？停用後不能登入，資料保留。", [a.full_name]) : __("啟用 {0}？", [a.full_name]), async () => {
				await frappe.xcall("nila_app.accounts.set_enabled", { name: a.name, enabled: a.enabled ? 0 : 1 });
				this.load();
			});
		});
	}

	edit(a) {
		const store_levels = this.data.store_levels;
		const d = new frappe.ui.Dialog({
			title: a ? __("修改帳號") : __("新增帳號"),
			fields: [
				{ fieldtype: "Data", fieldname: "full_name", label: __("姓名"), reqd: 1 },
				{ fieldtype: "Data", fieldname: "username", label: __("帳號（登入用，英文小寫或數字）"), reqd: 1 },
				{ fieldtype: "Select", fieldname: "level", label: __("層級"), reqd: 1, options: [{ value: "", label: "" }, ...this.data.levels],
					change: () => toggle() },
				// 門市用自己畫的勾選框：frappe 的多選欄位在這個對話框裡會讓剛輸入的欄位被清掉
				{ fieldtype: "HTML", fieldname: "stores_html" },
				...(a ? [] : [{ fieldtype: "Password", fieldname: "password", label: __("初始密碼"), reqd: 1,
					description: __("請告訴對方，並請他登入後自行修改") }]),
			],
			primary_action_label: __("儲存"),
			primary_action: async (v) => {
				v.stores = d.fields_dict.stores_html.$wrapper.find("input:checked").map((_, el) => el.value).get();
				delete v.stores_html;
				await frappe.xcall("nila_app.accounts.save_account", { data: Object.assign({ name: a && a.name }, v) });
				d.hide();
				frappe.show_alert({ message: __("已儲存"), indicator: "green" });
				this.load();
			},
		});
		const e = frappe.utils.escape_html;
		d.fields_dict.stores_html.$wrapper.html(`<label class="control-label">${__("門市（門市店長、店員必選）")}</label>
			<div class="d-flex flex-wrap" style="gap:4px 16px">${this.data.stores.map((st) => `<label class="mb-0">
				<input type="checkbox" value="${e(st.value)}" ${a && a.stores.includes(st.value) ? "checked" : ""}> ${e(st.label)}</label>`).join("")}</div>`);
		const toggle = () => d.fields_dict.stores_html.$wrapper.toggle(store_levels.includes(d.get_value("level")));
		d.show();
		// 先給每個欄位一個初始值（空白也要設），否則在這個對話框裡，第一次輸入的欄位會在移到下一欄時被清掉
		d.set_values({ full_name: a ? a.full_name : "", username: a ? a.username : "", level: a ? a.level : "" });
		toggle();
	}

	password(a) {
		frappe.prompt([{ fieldtype: "Password", fieldname: "password", label: __("新密碼"), reqd: 1 }], async (v) => {
			await frappe.xcall("nila_app.accounts.reset_password", { name: a.name, password: v.password });
			frappe.show_alert({ message: __("已重設 {0} 的密碼", [a.full_name]), indicator: "green" });
		}, __("重設密碼：{0}", [a.full_name]), __("重設"));
	}
}
