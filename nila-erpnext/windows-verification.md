# Windows 實機驗證與正式上線步驟（1.0.0）

分兩個階段：

- **階段 A：在你自己的 Windows 電腦**用範例資料完整驗證（可以放心測試、壞了重裝）。
- **階段 B：在客戶的電腦**正式安裝、匯入正式資料、驗收、上線。

每一步的結果請照最後的「回報表」回覆給我。**不需要、也不要傳給我**：任何密碼、`.env` 檔、SHOPLINE 金鑰、客戶的商品或會員資料、備份檔。畫面有錯誤時，截圖錯誤訊息即可。

---

## 0. 準備（兩台電腦都要）

1. Windows 10（22H2）或 Windows 11，記憶體 8 GB 以上（建議 16 GB），C 槽至少 30 GB 可用空間。
2. 安裝 **Docker Desktop**（<https://www.docker.com/products/docker-desktop/>），安裝時選「Use WSL 2」。裝好後重新開機，打開 Docker Desktop，等左下角顯示 Engine running。
   - 如果出現「Virtualization」相關錯誤：要在 BIOS 開啟虛擬化（Intel VT-x／AMD SVM）。
3. Docker Desktop → Settings → General：勾選「Start Docker Desktop when you sign in」。
4. 下載程式：GitHub 專案頁 → 切到分支 `claude/sharp-brahmagupta-tnbukb` → Code → Download ZIP，解壓縮到例如 `C:\nila-download`。

以下「開 PowerShell」是指：開始功能表搜尋 PowerShell。需要「以系統管理員身分執行」的步驟會特別註明。

---

## 階段 A：你自己的電腦（範例資料）

### A1. 安裝

```powershell
cd C:\nila-download\nila-erpnext\production
powershell -ExecutionPolicy Bypass -File .\install-nila.ps1
```

1. 第一次會停下來，打開 `C:\Users\你的帳號\nila-erpnext\production\nila-config.json` 看一下（範例可以不改），存檔。
2. 再執行一次同一個指令，設定 Administrator 密碼（至少 10 個字），輸入 `Y`。約 10–30 分鐘。
3. 完成後瀏覽器開 <http://localhost:8090>，用 Administrator 登入。

### A2. 上線設定

以**系統管理員身分**開 PowerShell：

```powershell
cd C:\Users\你的帳號\nila-erpnext\production
mkdir C:\nila-cloud-test   # 階段 A 用一個普通資料夾假裝是雲端資料夾
powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "C:\nila-cloud-test" -RegisterDaily
powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "C:\nila-cloud-test"
powershell -ExecutionPolicy Bypass -File .\check-nila.ps1 -RegisterStartup
powershell -ExecutionPolicy Bypass -File .\check-nila.ps1
```

最後一個指令應該全部 ✓（還原演練會顯示「建議」，下一步就做）。

### A3. 還原演練、忘記密碼

```powershell
powershell -ExecutionPolicy Bypass -File .\drill-nila.ps1
powershell -ExecutionPolicy Bypass -File .\reset-admin-password.ps1
```

演練應顯示「還原演練成功」；改密碼後用新密碼登入。

### A4. 範例資料與驗收清單

1. 用 Administrator 登入 →「妮菈」→「商品匯入匯出」→ 匯入 `C:\nila-download\nila-erpnext\seed\sample-skus.csv`（先預覽再匯入）。
2. 照 [`acceptance-checklist.md`](acceptance-checklist.md) 第一到六章逐項做。

### A5. 重開機與斷電

1. 重新開機（Windows 要自動登入才會自動啟動；階段 A 可以手動登入），登入後等 5 分鐘，打開 <http://localhost:8090>。
2. 執行 `check-nila.ps1`，看 `C:\Users\你的帳號\nila-erpnext\check-nila.log` 有沒有開機時的檢查紀錄。
3. （可以的話）在系統開著時直接拔電源，再開機登入，確認 5 分鐘內網頁可以開，資料都在。

### A6. 更新

下載新的 ZIP（或同一份），在新下載的資料夾執行：

```powershell
cd C:\nila-download\nila-erpnext\production
powershell -ExecutionPolicy Bypass -File .\update-nila.ps1
```

更新後資料都在、`check-nila.ps1` 全部 ✓。

---

## 階段 B：客戶的電腦（正式上線）

### B1. 準備正式資料（由客戶整理，資料留在客戶那裡）

| 資料 | 格式 | 注意 |
|---|---|---|
| 公司設定 | 公司名稱、縮寫、總公司與各分公司名稱、甲型名稱與縮寫、尺寸 | **甲型縮寫是料號的一部分，開始使用後不能改** |
| 商品清單 | 系統的「商品匯入匯出 → 下載空白範本」 | 一列一個規格；各公司欄位填**上線當天盤點**的庫存 |
| 會員名單 | 系統的「會員匯入 → 下載空白範本」（姓名、手機） | 同一支手機只能一筆 |
| 同事名單 | 姓名、帳號、層級、門市 | 在「帳號管理」逐一建立 |
| 舊的消費紀錄 | 不匯入 | 會員消費與抽獎從上線那天開始累積 |

> 範本要先安裝好才能下載：可以先在階段 A 的電腦下載範本給客戶填。

### B2. 安裝與上線設定

1. 照「0. 準備」與「A1. 安裝」，但 `nila-config.json` 填**正式的公司設定**。
2. 客戶的雲端硬碟電腦版：登入客戶的帳號，建立 `妮菈備份` 資料夾並設為「一律保留在這部裝置上」，記下路徑（例如 `G:\我的雲端硬碟\妮菈備份`）。
3. 照 [`production/README.md`](production/README.md)「上線設定（只做一次）」第 2–8 步：每天備份到雲端資料夾、登入後自動啟動、Docker 自動啟動、BIOS 停電後自動開機、自動登入、關閉睡眠。
4. 開放區網連入（以系統管理員身分）：

   ```powershell
   New-NetFirewallRule -DisplayName "妮菈 ERPNext (TCP 8090)" -Direction Inbound -Protocol TCP -LocalPort 8090 -Action Allow -Profile Private,Domain
   ```

   在路由器把主機的 IP 固定下來，各門市的電腦用 `http://主機IP:8090`。

### B3. 匯入正式資料（建議在打烊後做）

1. 商品匯入（含各公司期初庫存）：先預覽，沒有錯誤才匯入。5,000 個規格約 30 分鐘。
2. 會員匯入：先預覽，處理掉錯誤（重複手機、格式錯誤）再匯入。
3. 帳號管理：建立每位同事的帳號（客戶自己建議也建一個「1 管理員」帳號平常使用）。
4. 立刻備份，並把這份備份資料夾名稱記下來，稱為「**驗收前**」：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "G:\我的雲端硬碟\妮菈備份"
   ```

### B4. 驗收

1. 照 [`acceptance-checklist.md`](acceptance-checklist.md) 快速跑一遍（第一章與第七章一定要做；其他章節抽查）。
2. 驗收完成後，還原到「驗收前」，把測試的銷售、訂單清掉：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\restore-nila.ps1 -BackupDir "C:\Users\你的帳號\Documents\妮菈備份\驗收前的資料夾名稱"
   ```
3. `drill-nila.ps1` 演練一次雲端資料夾裡的備份，`check-nila.ps1` 全部 ✓。
4. 正式開始使用。

### B5. SHOPLINE（取得 API 權限後）

照 README「SHOPLINE 官網訂單」：客戶自己把金鑰貼到設定頁、測試連線、設定開始時間、啟用。前幾天每天看一次「待處理」，有問題時截圖說明給我（不要截到金鑰）。

---

## 回報表

請複製下面這張表，填好回覆給我：

| 步驟 | 結果（✅／❌） | 花了多久 | 問題或錯誤訊息 |
|---|---|---|---|
| 電腦（Windows 版本、記憶體） | | — | |
| A1 安裝 | | | |
| A2 上線設定、check 全部 ✓ | | | |
| A3 還原演練、忘記密碼 | | | |
| A4 範例資料匯入、驗收清單 | | | |
| A5 重開機、斷電 | | | |
| A6 更新 | | | |
| B2 客戶電腦安裝與上線設定 | | | |
| B3 正式資料匯入（規格數、會員數） | | | |
| B4 驗收、還原到驗收前 | | | |
