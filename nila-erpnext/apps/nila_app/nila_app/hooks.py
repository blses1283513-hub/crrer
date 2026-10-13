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
