# 妮菈穿戴甲：ERPNext 16

- **正式版** → [`production/`](production/README.md)：給客戶使用，含妮菈客製功能（`apps/nila_app/`）、安裝、更新、備份、還原。
- **試用版** → 本頁以下：只供評估，不能裝客製功能。

## 試用版

方案見 [`../nila-erpnext-plan.md`](../nila-erpnext-plan.md)。這個資料夾是「步驟 3：試用」用的檔案，**只供試用，不是正式環境**。

| 檔案 | 用途 |
|---|---|
| `install-erpnext-trial.ps1` | 一鍵安裝：ERPNext 16、初次設定（公司、台灣、新台幣、繁體中文）、範例資料、−2 → 補 12 的情境。可重複執行 |
| `verify-erpnext-trial.ps1` | 自動驗證 13 項功能（在途調撥、叫貨不重複、出貨、實際庫存不變負、條碼、修改紀錄、權限、會員合併、用語修正） |
| `trial-checklist.md` | 安裝步驟與手動操作清單（請填寫結果回報） |
| `docker-compose.yml` | 以官方 frappe_docker 的 `pwd.yml`（MIT）為基礎，固定版本、密碼由 `.env` 提供、預設埠 8080（安裝時可用 `-Port` 改） |
| `seed/sample-skus.csv` | 範例 SKU 試算表（3 種甲型、10 款、72 個規格、5 個公司的期初庫存）；也是正式匯入格式的雛形 |
| `seed/shapes.csv` | 甲型與縮寫（料號的一部分，上線後不能改） |
| `seed/terms.csv` | 用語修正（例：Item → 商品、Projected Qty → 預計庫存） |
| `seed/seed_trial.py`、`seed/verify_trial.py` | 在 ERPNext 容器內執行的設定與驗證程式（不需要電腦上安裝 Python） |

自動測試：`tests/erpnext/`（試算表讀取）與 `.github/workflows/nila-erpnext-trial.yml`（在 GitHub 上用同一支安裝腳本裝真正的 ERPNext，跑 13 項驗證與續裝）。
