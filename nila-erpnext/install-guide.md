# 妮菈穿戴甲系統 完整安裝流程（客戶可自行安裝）

照順序做，每一步做完再做下一步。全部做完約 1.5–2 小時（大部分是等待下載與建置）。
**整個過程不需要把任何密碼或金鑰告訴別人。**

---

## 第 0 步：確認電腦

| 項目 | 需求 |
|---|---|
| 系統 | Windows 10（22H2）或 Windows 11（專業版、家用版都可以） |
| 記憶體 | 8 GB 以上（建議 16 GB） |
| 硬碟 | C 槽至少 **30 GB** 可用空間 |
| 網路 | 安裝時要能上網（會下載約 1.4 GB）；日常使用只需要區網 |
| 放置 | 這台電腦要**一直開機**（門市會連到它），放在只有員工能接觸的地方 |

---

## 第 1 步：安裝 Docker Desktop

1. 用瀏覽器開 <https://www.docker.com/products/docker-desktop/>，下載 Windows 版並安裝。
2. 安裝時**保持勾選「Use WSL 2」**。
3. 安裝完成後依指示**重新開機**。
4. 開機後從開始功能表打開 **Docker Desktop**，接受條款（可以略過登入）。
5. 等左下角出現綠色的 **Engine running**（鯨魚圖示不再轉動）。
6. Docker Desktop → 右上角齒輪 Settings → General → 勾選 **Start Docker Desktop when you sign in to your computer** → Apply。

> 如果出現「Virtualization」或「WSL」相關錯誤：要進電腦的 BIOS 開啟虛擬化（Intel VT-x／AMD SVM）。不熟的話請電腦行協助，開好之後回到這一步。

---

## 第 2 步：取得安裝檔

1. 向維護人員取得安裝檔 ZIP（內含 `nila-erpnext` 資料夾）。
2. 放到 `C:\nila-download`，**按右鍵 → 全部解壓縮**，解壓縮後路徑應該像這樣：

   ```
   C:\nila-download\nila-erpnext\production\install-nila.ps1
   ```

   （資料夾名稱如果多了一層，例如 `crrer-claude-xxx\nila-erpnext`，照實際的路徑調整下面的指令即可。）

---

## 第 3 步：打開 PowerShell 並進入資料夾

1. 開始功能表搜尋 **PowerShell**，點選「Windows PowerShell」（一般身分就可以）。
2. 輸入（路徑依第 2 步實際位置調整）：

   ```powershell
   cd C:\nila-download\nila-erpnext\production
   ```

---

## 第 4 步：第一次執行安裝（只放設定檔）

```powershell
powershell -ExecutionPolicy Bypass -File .\install-nila.ps1
```

看到「已放置設定檔」就會停下來，這是正常的。

---

## 第 5 步：確認公司設定（非常重要）

用記事本打開：

```
C:\Users\你的使用者名稱\nila-erpnext\production\nila-config.json
```

| 欄位 | 要填什麼 |
|---|---|
| `company_name` | 公司名稱，例：`妮菈穿戴甲` |
| `company_abbr` | 公司縮寫，2–5 個大寫英文字母，例：`NL`（會出現在倉庫名稱後面） |
| `hq` | 總公司的名稱 |
| `branches` | 各分公司（門市）的名稱，用逗號分開；之後還可以再新增 |
| `shapes` | 甲型的名稱與縮寫（2–3 個大寫英文字母），例：`{"name": "長梯", "abbr": "LT"}`；之後還可以再新增甲型 |
| `sizes` | 尺寸，預設 `XS、S、M、L` |

> ⚠️ **甲型的縮寫會成為料號的一部分**（例：`0001-LT-XS`），料號也是條碼與 SHOPLINE 的 SKU。**開始使用後就不能修改**，請先確認清楚。
> 其他欄位（公司、分公司名稱）也請先確認；修改格式時注意逗號與引號不要刪掉。

存檔。

---

## 第 6 步：第二次執行安裝（正式安裝）

回到 PowerShell，**再執行一次同樣的指令**：

```powershell
powershell -ExecutionPolicy Bypass -File .\install-nila.ps1
```

1. 出現「管理員密碼」：輸入你要的**最高管理員（Administrator）密碼**，輸入時畫面不會顯示文字，這是正常的。
   - 至少 10 個字元，不能包含單引號 `'`，請設不容易猜到的密碼，**寫下來放在安全的地方**。
2. 再輸入一次相同的密碼。
3. 看到確認訊息時輸入 `Y` 按 Enter。
4. 等待約 **10–30 分鐘**（會下載、建置、建立網站，過程中畫面會一直跑字，請不要關閉視窗）。
5. 出現「完成！」後，瀏覽器會自動打開 <http://localhost:8090>。

**如果中途失敗或視窗被關掉**：直接再執行一次同樣的指令，會自動接續，已建立的資料不會重複。
**如果提示「埠 8090 已被其他程式使用」**：改用 `.\install-nila.ps1 -Port 8091`，之後網址的 8090 也改成 8091。

---

## 第 7 步：登入並確認

1. 帳號 `Administrator`，密碼是第 6 步設定的。
2. 登入後點首頁的「**妮菈**」，應該會看到：門市銷售、庫存表、補貨建議、新增款式、帳號管理等功能。
3. 在 PowerShell 執行健康檢查：

   ```powershell
   powershell -ExecutionPolicy Bypass -File "$HOME\nila-erpnext\production\check-nila.ps1"
   ```

   此時 Docker、網頁、9 個服務應該都是 ✓；「還沒有備份」是正常的，下一步處理。

---

## 第 8 步：讓同一個區網的其他電腦使用

1. 開始功能表搜尋 PowerShell，**按右鍵 → 以系統管理員身分執行**。
2. 開放連線（只限私人／網域網路）：

   ```powershell
   New-NetFirewallRule -DisplayName "妮菈 ERPNext (TCP 8090)" -Direction Inbound -Protocol TCP -LocalPort 8090 -Action Allow -Profile Private,Domain
   ```

3. 查這台電腦的區網 IP：

   ```powershell
   ipconfig
   ```

   找「IPv4 位址」，例如 `192.168.1.20`。
4. 其他電腦用瀏覽器開 `http://192.168.1.20:8090`，加入書籤。
5. **建議**：到路由器把這台電腦的 IP 設成固定（不然重開機後 IP 可能變）；這台電腦的網路類型要是「私人網路」（設定 → 網路和網際網路 → 內容 → 網路設定檔類型）。

---

## 第 9 步：上線設定（備份、斷電保護）

這台電腦沒有 UPS，所以要做到：**停電恢復後自己開機、系統自己恢復、資料每天自動備份到雲端**。

### 9-1 雲端備份資料夾

1. 在這台電腦安裝客戶的雲端硬碟電腦版（例如 Google Drive 電腦版）並登入。
2. 在雲端硬碟裡建立資料夾 `妮菈備份`，並設定為「**一律保留在這部裝置上**」（讓它同步到雲端）。
3. 記下路徑，例如 `G:\我的雲端硬碟\妮菈備份`（OneDrive 則類似 `C:\Users\你的使用者名稱\OneDrive\妮菈備份`）。
4. 雲端帳號**請開啟兩步驟驗證**；備份檔等同全部資料，不要分享這個資料夾。

### 9-2 每天自動備份＋登入後自動啟動

以**系統管理員身分**開 PowerShell（同第 8 步），執行（雲端路徑換成你的）：

```powershell
cd $HOME\nila-erpnext\production
powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "G:\我的雲端硬碟\妮菈備份" -RegisterDaily
powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "G:\我的雲端硬碟\妮菈備份"
powershell -ExecutionPolicy Bypass -File .\check-nila.ps1 -RegisterStartup
```

- 第 1 行：登記每天 **23:30** 自動備份（那個時間電腦要開著）。
- 第 2 行：**立刻先備份一次**，確認雲端資料夾裡出現一個「日期時間」資料夾。
- 第 3 行：登記「登入 Windows 後自動檢查並啟動系統」。

### 9-3 停電後自動開機、自動登入

1. **BIOS 設定**：開機時按 Del 或 F2（各廠牌不同）進入 BIOS，找到「**AC Power Recovery**」或「**Restore on AC Power Loss**」，設為 **Power On**，儲存離開。（名稱因廠牌而異，不確定請電腦行協助。）
2. **自動登入 Windows**：按 `Win + R` 輸入 `netplwiz` → 取消勾選「必須輸入使用者名稱和密碼，才能使用這台電腦」→ 輸入這個帳號的密碼。
   - 看不到這個選項時：設定 → 帳戶 → 登入選項 → 關閉「為了提高安全性，僅允許 Microsoft 帳戶使用 Windows Hello 登入」，再試一次。
3. **關閉睡眠**：設定 → 系統 → 電源 → 「接上電源時，讓電腦進入睡眠狀態」選 **永不**。

### 9-4 驗證

```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\nila-erpnext\production\check-nila.ps1"
```

這次應該幾乎都是 ✓（只剩「建議做還原演練」）。接著做第一次**還原演練**（約 2–10 分鐘，不影響正常使用）：

```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\nila-erpnext\production\drill-nila.ps1"
```

看到「**還原演練成功**」就表示備份是可以還原的。

最後**重新開機一次**：登入後等 5 分鐘，打開 <http://localhost:8090> 應該自己就能用。

---

## 第 10 步：建立同事的帳號

1. 用 Administrator 登入 → 首頁「妮菈」→「**帳號管理**」→ 新增帳號。
2. 填：姓名、帳號（英文小寫或數字，登入用，不需要信箱）、層級、門市（店長、店員要選門市）、初始密碼。
3. 5 個層級：1 管理員、2 營運主管、3 總公司作業、4 門市店長、5 門市店員。能做的事見《使用手冊》。
4. **建議**：幫自己也建一個「1 管理員」帳號平常使用，Administrator 留作備用。
5. 請每位同事第一次登入後，自己到右上角頭像 → My Settings → 變更密碼。

---

## 第 11 步：匯入正式資料

建議在**打烊後**做。每一種匯入都是「先預覽、沒有錯誤才能匯入、全部成功才寫入」，所以不怕匯到一半壞掉。

1. **商品與期初庫存**：首頁「妮菈」→「商品匯入匯出」→「下載空白範本」→ 填好（一列一個規格；各公司欄位填上線當天盤點的庫存）→ 上傳 → 看預覽 → 沒有錯誤就「開始匯入」。5,000 個規格約 30 分鐘，請在沒人操作庫存時進行。
2. **會員名單**：「妮菈」→「會員匯入」→ 下載範本 → 填「姓名、手機」→ 上傳預覽 → 匯入。手機已經是會員的會略過。
3. 舊的消費紀錄**不匯入**，會員消費與抽獎從上線那天開始累積。
4. 匯入完成後立刻備份一次：

   ```powershell
   powershell -ExecutionPolicy Bypass -File "$HOME\nila-erpnext\production\backup-nila.ps1" -CopyTo "G:\我的雲端硬碟\妮菈備份"
   ```

   記下這份備份資料夾的名稱，稱為「**驗收前**」。

---

## 第 12 步：驗收

照 `nila-erpnext\acceptance-checklist.md` 逐項勾選（第一章、第七章一定要做，其他章節抽查）。
驗收會產生測試用的銷售與訂單；做完後**還原到「驗收前」那份備份**，把測試資料清掉：

```powershell
powershell -ExecutionPolicy Bypass -File "$HOME\nila-erpnext\production\restore-nila.ps1" -BackupDir "$HOME\Documents\妮菈備份\驗收前的資料夾名稱"
```

輸入 `YES` 確認。完成後請用**備份當時**的帳號密碼登入。

---

## 第 13 步：SHOPLINE 官網訂單（取得 API 權限之後再做）

預設是關閉的，不影響其他功能。取得權限後：

1. SHOPLINE 後台 →「設定 → 管理員設定 → API 權限（API Auth）」產生 API 金鑰（這個功能要先向 SHOPLINE 窗口申請開通）。
2. 系統首頁「妮菈」→「SHOPLINE 官網訂單」→ 貼上金鑰 → 按「**測試連線**」，成功會顯示商店名稱。
3. 設定「從這個時間之後的官網訂單開始匯入」→ 勾「啟用自動同步」→「儲存設定」。
4. SHOPLINE 商品的 **SKU 必須等於系統的料號**（例如 `0001-LT-XS`），對不到的訂單會放進「待處理」。

> **金鑰等同商店的密碼**：只貼在這個設定欄，不要貼到聊天、信件或文件，也不需要給維護人員。

---

## 之後的日常維護（都在 PowerShell 執行）

先進入資料夾：`cd $HOME\nila-erpnext\production`

| 要做的事 | 指令 | 多久一次 |
|---|---|---|
| 檢查系統是否正常 | `powershell -ExecutionPolicy Bypass -File .\check-nila.ps1` | 每週 |
| 打不開或出現 502 | `powershell -ExecutionPolicy Bypass -File .\check-nila.ps1 -Fix` | 需要時 |
| 還原演練 | `powershell -ExecutionPolicy Bypass -File .\drill-nila.ps1` | 每月 |
| Administrator 忘記密碼 | `powershell -ExecutionPolicy Bypass -File .\reset-admin-password.ps1` | 需要時 |
| 更新到新版本 | 解壓縮新版 ZIP，在**新資料夾**的 `nila-erpnext\production` 執行 `powershell -ExecutionPolicy Bypass -File .\update-nila.ps1`（會先自動備份），完成後各電腦按 Ctrl+F5 | 有新版時 |

其他同事忘記密碼：由管理員到「妮菈 → 帳號管理 → 重設密碼」。
更完整的說明見 `nila-erpnext\production\README.md`；每天的操作見 `nila-erpnext\user-manual.md`。

---

## 常見問題

| 狀況 | 怎麼辦 |
|---|---|
| 「找不到執行中的 Docker」 | 打開 Docker Desktop，等 Engine running 後再執行 |
| 安裝很久沒有動靜 | 第一次建置需要 10–30 分鐘，只要視窗沒有出現紅色錯誤就繼續等 |
| 紅色錯誤、安裝中斷 | 直接再執行一次同樣的指令（會接續）；仍失敗，截圖紅字給維護人員（不要截到密碼） |
| 網址打不開 | 執行 `check-nila.ps1 -Fix` |
| 其他電腦連不到 | 確認第 8 步的防火牆指令、IP 沒變、網路類型是「私人網路」 |
| 備份失敗或雲端資料夾沒有檔案 | 確認雲端硬碟電腦版有登入、路徑正確，再手動備份一次 |
| 電腦停電後系統沒起來 | 等 5 分鐘；仍不行執行 `check-nila.ps1 -Fix` |
