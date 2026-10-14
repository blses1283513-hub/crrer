app_name = "nila_app"
app_title = "妮菈穿戴甲"
app_publisher = "crrer"
app_description = "妮菈穿戴甲庫存與營運管理的 ERPNext 客製功能"
app_email = "blses1283513@gmail.com"
app_license = "gpl-3.0"
required_apps = ["erpnext"]

# 安裝與每次升級（migrate）後，確保基本設定存在（可重複執行，不會重複建立）
after_install = "nila_app.setup.install.after_install"
after_migrate = "nila_app.setup.install.after_migrate"

# 商品：款式的成本、售價、狀態同步到規格；售價只能在款式修改；停售、停產不能接單
doc_events = {
    "Item": {
        "validate": "nila_app.products.item_validate",
        "on_update": "nila_app.products.item_on_update",
    },
    "Item Price": {"validate": "nila_app.products.item_price_validate"},
    "Sales Order": {"validate": "nila_app.products.sales_order_validate"},
}

# 商品頁面與清單的按鈕（新增款式、加入甲型／尺寸）
doctype_js = {"Item": "public/js/item.js"}
doctype_list_js = {"Item": "public/js/item_list.js"}
