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
    "Sales Order": {
        "validate": ["nila_app.products.sales_order_validate", "nila_app.dispatch.sales_order_validate"],
        "on_submit": "nila_app.dispatch.sales_order_changed",
        "on_update_after_submit": "nila_app.dispatch.sales_order_changed",
        "on_cancel": "nila_app.dispatch.sales_order_cancelled",
    },
    # 會員：手機統一格式、不能重複
    "Customer": {"validate": "nila_app.retail.customer_validate"},
    # 停產的商品不能補貨
    "Material Request": {"validate": "nila_app.replenish.material_request_validate"},
}
# 庫存或已叫貨數量改變的單據：送出、取消後重算相關訂單的出貨狀態
for _dt in ["Delivery Note", "Stock Entry", "Purchase Receipt", "Stock Reconciliation", "Sales Invoice", "POS Invoice",
            "Purchase Order"]:
    doc_events[_dt] = {"on_submit": "nila_app.dispatch.stock_changed", "on_cancel": "nila_app.dispatch.stock_changed"}

# 每天早上：重算訂單出貨狀態、補貨與調撥建議，有需要時通知管理者
scheduler_events = {"daily": ["nila_app.replenish.daily"]}

# 商品頁面與清單的按鈕（新增款式、加入甲型／尺寸）
doctype_js = {
    "Item": "public/js/item.js",
    "Sales Order": "public/js/sales_order.js",
    "Material Request": "public/js/material_request.js",
    "Stock Entry": "public/js/stock_entry.js",
    "Purchase Order": "public/js/purchase_order.js",
}
doctype_list_js = {"Item": "public/js/item_list.js", "Material Request": "public/js/material_request_list.js"}

# 共用的庫存狀態顏色與表格（庫存表、補貨、訂單面板）；加上版本號，更新後瀏覽器會重新下載
from nila_app import __version__ as _v  # noqa: E402

app_include_js = [f"/assets/nila_app/js/nila.js?v={_v}"]
app_include_css = [f"/assets/nila_app/css/nila.css?v={_v}"]
