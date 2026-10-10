# InvenTree 主資料生成腳本

對應設計文件 `../inventree-dynamic-stock-design.md` 的**步驟 4**。

## 事前準備

1. 建立一個**管理員帳號的 API token**，供腳本使用。
2. 用 `setup_roles.py` 建立公司群組與職務群組、設定權限（**必須在匯入前做**，匯入腳本會把公司頂層庫位的擁有者設為 `company-A/B/C`）：

   ```powershell
   python setup_roles.py show      # 先預覽權限矩陣（不連線）
   python setup_roles.py apply     # 建立群組並設定權限（會列出變更並等你確認）
   ```

   - 權限矩陣在 `roles.json`，可自行調整。所有職務預設**沒有刪除權限**、也沒有「管理」角色。
   - `python setup_roles.py add-user 帳號 --groups company-A,role-warehouse` 可建立使用者並加入群組（不需要郵件伺服器）。
   - `python setup_roles.py audit` 唯讀稽核：superuser 人數、沒有群組的帳號、缺少職務群組的帳號。
3. **先不要**開啟擁有權控制（`STOCK_OWNERSHIP_CONTROL`），等腳本設好擁有者後再開，見下方「執行後」。

## 執行

```bash
cp config.example.json config.json   # 依實際公司、產品名稱修改

# 1) 先試跑：只產出 sku_plan.csv，不連線
python3 seed_skus.py --config config.json --dry-run

# 2) 確認 CSV 無誤後，寫入「測試站」
INVENTREE_URL=http://測試站:8000 INVENTREE_TOKEN=你的token \
python3 seed_skus.py --config config.json
```

腳本可重複執行：已存在的庫位、分類、零件、參數會沿用，不會重複建立。

## 會建立什麼

| 項目 | 數量（預設設定） |
|---|---|
| 頂層庫位（每公司一個，擁有者＝該公司群組） | 3 |
| 主倉庫位 | 3 |
| 零件分類 | 3 |
| 參數模板 Style、Size（含選項） | 2 |
| 產品模板 | 30 |
| 變體（SKU） | 450 |
| 參數值（每個 SKU 兩個） | 900 |

料號規則：產品模板 `A-P03`，變體 `A-P03-S2-XL`。

## 執行後

1. 到「設定 → 庫存」開啟**擁有權控制**。
2. 用各公司帳號登入，確認：可修改自己公司的庫存；別家公司的庫存**看得到但改不了**。
3. 注意：**管理員（superuser）可以修改所有公司的庫存**，這是 InvenTree 的設計。日常操作請用一般帳號，管理員帳號只給系統管理者。

## 待在測試站確認的地方（🧪）

這些項目無法從文件完全查證，第一次執行時請留意錯誤訊息：

- 參數端點 `/api/parameter/...` 與欄位 `model_type`、`model_id`：InvenTree 1.2 起改為通用參數模型；若你的版本不同，修改 `seed_skus.py` 開頭的 `ENDPOINTS`。可在站台的 `/api/` 頁面或用 OPTIONS 請求確認。
- 擁有者查詢 `/api/user/owner/` 回傳的欄位名稱（腳本以 `name` 比對群組名）。
- 新收貨的庫存項目是否自動繼承庫位擁有者：請在步驟 5 實測一次。
