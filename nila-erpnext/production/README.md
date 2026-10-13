# 妮菈穿戴甲：ERPNext 16 正式版

官方 ERPNext 16 ＋ 妮菈客製功能（`nila_app`），裝在客戶的電腦上，客戶是最高權限的使用者（`Administrator`）。
只供**同一個區網**使用（`http://電腦IP:8090`），不對外開放；之後若要讓門市或手機從外面連進來，再加對外通道即可，不需要重裝。

> 開發進度：**P0（正式版骨架）已完成**——安裝、更新、備份、還原，以及公司、倉庫、甲型、尺寸、自訂欄位、繁中用語等基本設定。
> 客製功能（庫存表、全公司補貨、訂單調度、門市消費與會員、抽獎、SHOPLINE）會在 P1–P7 陸續加入，用 `update-nila.ps1` 更新即可，資料不受影響。

## 需要什麼

- Windows 10／11，已安裝並啟動 **Docker Desktop**。
- C 槽至少 **15 GB** 可用空間（ERPNext 映像約 7 GB）、Docker 可用記憶體 4 GB 以上。
- 可以上網（第一次安裝要下載約 1.4 GB）。
- 不需要系統管理員權限；只有「開放區網其他電腦連入」與「每天自動備份」的登記可能需要。

## 安裝（第一次）

1. 下載並解壓縮專案，開一般的 PowerShell，切到 `nila-erpnext\production`：

   ```powershell
   cd "解壓縮的位置\nila-erpnext\production"
   powershell -ExecutionPolicy Bypass -File .\install-nila.ps1
   ```

2. 第一次執行會在 `C:\Users\你的帳號\nila-erpnext\production\nila-config.json` 放一份設定範本後停下。用記事本打開確認：

   | 欄位 | 說明 |
   |---|---|
   | `company_name`、`company_abbr` | 公司名稱與縮寫（縮寫 2–5 個大寫英文字母，會出現在倉庫名稱後面） |
   | `hq`、`branches` | 總公司與各分公司（門市）名稱。之後可再新增分公司 |
   | `shapes` | 甲型名稱與縮寫（2–3 個大寫英文字母）。**縮寫是料號的一部分（例：`0001-LT-XS`），開始使用後不能改**；之後可再新增甲型 |
   | `sizes` | 尺寸，預設 XS、S、M、L |

3. 存檔後**再執行一次同樣的指令**。設定最高管理員密碼（至少 10 個字元，輸入兩次），確認變更後輸入 `Y`。
4. 第一次約 10–30 分鐘。完成後瀏覽器會開啟 <http://localhost:8090>，用 `Administrator` 與剛才的密碼登入。

- 埠 8090 被占用時：加上 `-Port 8091`。
- 中途失敗：直接再執行一次（沿用密碼，資料不會重複建立）。
- 安裝完成後，`.env` 只留資料庫密碼；管理員密碼已從檔案中移除。**`.env` 請勿分享。**

## 讓同一個區網的其他電腦使用

以**系統管理員身分**開 PowerShell，開放 8090 埠（只限私人與網域網路）：

```powershell
New-NetFirewallRule -DisplayName "妮菈 ERPNext (TCP 8090)" -Direction Inbound -Protocol TCP -LocalPort 8090 -Action Allow -Profile Private,Domain
```

其他電腦用瀏覽器開 `http://主機IP:8090`（主機 IP 用 `ipconfig` 查）。主機的網路要設為「私人網路」，IP 建議在路由器固定。

## 備份（非常重要：主機沒有 UPS）

```powershell
cd C:\Users\你的帳號\nila-erpnext\production
powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "D:\妮菈備份"
```

- 每份備份放在 `文件\妮菈備份\日期時間\`（資料庫、上傳檔案、網站設定），保留最近 30 份。
- `-CopyTo` 指定**第二個地方**（隨身碟、NAS、或 Google Drive／OneDrive 的同步資料夾）。電腦壞掉時，只有放在別處的備份救得回來。
- **每天自動備份**（每天 23:30，電腦與 Docker 要開著）：

  ```powershell
  powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "D:\妮菈備份" -RegisterDaily
  ```

## 還原

⚠️ 會用備份的內容**取代目前的全部資料**。還原前會自動先備份目前的資料。

```powershell
powershell -ExecutionPolicy Bypass -File .\restore-nila.ps1 -BackupDir "C:\Users\你的帳號\Documents\妮菈備份\20261013_233000"
```

輸入 `YES` 確認。完成後請用**備份當時**的帳號密碼登入（帳號密碼存在資料庫中，會一起還原）。

**換電腦**：在新電腦依「安裝」完成安裝（`nila-config.json` 用舊電腦備份資料夾中的那份），再用上面的指令還原舊電腦的備份。

## 更新到新版本

下載新版並解壓縮後，在**新下載的** `nila-erpnext\production` 資料夾執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\update-nila.ps1
```

會先自動備份，再替換程式、重新建置、升級資料庫結構並重新啟動（約 3–10 分鐘）。`.env` 與 `nila-config.json` 不會被改動。完成後各電腦按一次 Ctrl+F5。

## 日常操作

| 要做的事 | 指令（在 `C:\Users\你的帳號\nila-erpnext\production`） |
|---|---|
| 查看狀態 | `docker compose ps` |
| 暫停／再開 | `docker compose stop`／`docker compose start` |
| 電腦重開機後 | Docker Desktop 啟動後系統會自動啟動（建議在 Docker Desktop 設定「登入時自動啟動」） |
| 看錯誤紀錄 | `docker compose logs --tail 50 backend` |
| 出現 502 錯誤 | `docker compose restart`（前端與後端一起重新啟動） |

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `install-nila.ps1`、`update-nila.ps1`、`backup-nila.ps1`、`restore-nila.ps1` | 安裝、更新、備份、還原 |
| `docker-compose.yml` | 以官方 frappe_docker 正式版設定（`compose.yaml`＋mariadb、redis、noproxy override，MIT）為基礎 |
| `Dockerfile` | 官方 `frappe/erpnext:v16.50.0`＋`nila_app`（在你的電腦上建置，不需要映像檔倉庫） |
| `nila-config.example.json` | 公司、分公司、甲型、尺寸的設定範本 |
| `lib/NilaCommon.ps1` | 腳本共用的函式 |
| `../apps/nila_app/` | 妮菈客製功能（ERPNext app，GPLv3） |

## 驗證狀況

| 項目 | 狀況 |
|---|---|
| 安裝（兩次執行、密碼含 `$ " 空白`、安裝後移除 .env 中的管理員密碼） | ✅ 在真正的 ERPNext 16 上自動測試，GitHub Actions 每次都重跑 |
| 備份（含第二個地方）、還原（備份後的變動被取代、還原前自動備份）、換電腦還原（新電腦、不同密碼） | ✅ 同上 |
| 更新（版本升級、資料保留） | ✅ 同上 |
| 在 Windows 的 Docker Desktop 上執行 | 🧪 尚未在 Windows 實測（腳本相容 Windows PowerShell 5.1，但自動測試是在 Linux 的 PowerShell 7 上跑） |
| 每天自動備份的排程登記（`-RegisterDaily`） | 🧪 尚未在 Windows 實測 |
