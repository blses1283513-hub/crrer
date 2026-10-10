# 庫存管理系統 App（多台電腦共用）

> 完整的從零安裝流程（含換主機）請看 repo 根目錄的 [`inventree-install-guide.md`](../inventree-install-guide.md)。

把已安裝好的 InvenTree 變成一個「App」：

- **主機電腦**：桌面出現「庫存管理系統」圖示。點兩下會自動啟動 Docker 與系統，並開啟獨立視窗（沒有網址列，看起來像一般軟體）。
- **其他電腦**：不用安裝 Docker，建立一個桌面捷徑就能連到主機，所有人看到**同一份**庫存。
- **中文操作助手內建**：滑鼠停留說明、調貨提醒、📋 異動紀錄都直接內建，**不必再裝 Tampermonkey**。
- **預設語言改為繁體中文**：任何電腦第一次開啟就是中文。
- **設定全部保留**：帳號、群組、權限、系統設定、庫存與異動紀錄都存在主機的資料庫中，換哪台電腦登入都一樣。另附一鍵備份。

## 通知（🔔）

App 內建通知小視窗：低庫存、別家公司或管理員把庫存調進／調出你的公司庫位、大量或歸零的異常操作，**只通知與你所屬公司有關的事**，已讀紀錄存在伺服器。由 `setup-server.ps1` 新增的 `inventree-notifier` 容器提供，規則、限制與疑難排解見 [`notifier/README.md`](notifier/README.md)。

## 架構

```
          ┌──────────── 主機電腦（Docker） ────────────┐
其他電腦 ─┤  http://主機IP  →  代理伺服器（Caddy）        │
  瀏覽器  │                    ├─ /app/  App 外框＋中文操作助手 │
本機 ─────┤  http://localhost  └─ 其餘  InvenTree（資料庫）    │
          └────────────────────────────────────────────┘
```

## 一、主機電腦設定（只做一次）

前提：已用 `inventree-install` 安裝好 InvenTree，且目前可以正常登入。

1. 下載本 repo 最新的分支內容（要包含 `inventree-app` 和 `inventree-ui-helper` 兩個資料夾）。
2. 在「開始」選單對 PowerShell 按右鍵 →「以系統管理員身分執行」。用系統管理員是為了設定防火牆；不是的話也能執行，只是防火牆要事後補設。
3. 切到 `inventree-app` 資料夾，執行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup-server.ps1
   ```

4. 腳本會偵測本機 IP，**列出所有變更並請你確認**，輸入 `Y` 才會執行：
   - 備份 `.env`（原檔另存為 `.env.bak-時間`）
   - `.env` 加上：允許其他電腦連入的設定、預設語言繁體中文
   - 新增 App 檔案（官方檔案**不修改**）
   - 防火牆開放 80 埠
   - 重新啟動系統（約 1–3 分鐘，**資料不受影響**）
   - 桌面建立「庫存管理系統」捷徑
5. 完成後畫面會顯示其他電腦要用的網址，例如 `http://192.168.1.20`，以及建立捷徑的指令。

> **主機要保持開機**，其他電腦才能使用。建議在 Docker Desktop 設定中勾選「Start Docker Desktop when you sign in」，開機後系統會自動啟動。

## 二、其他電腦（每台做一次，不需要 Docker）

**方法 A：一行指令建立桌面捷徑**（建議）

在那台電腦開 PowerShell（不需系統管理員），貼上主機設定完成時顯示的指令，例如：

```powershell
iwr http://192.168.1.20/app/client-shortcut.ps1 -OutFile $env:TEMP\cs.ps1; powershell -ExecutionPolicy Bypass -File $env:TEMP\cs.ps1 -Server 192.168.1.20
```

**方法 B：用 Edge 安裝成 App**

用 Edge 開 `http://主機IP`，點右上角「⋯」，選「應用程式」裡的「將此網站安裝為應用程式」。

兩種方法完成後，用**自己的帳號**登入即可。各公司帳號只能修改自家庫存。

## 三、備份

在主機的安裝資料夾（預設 `C:\Users\你的帳號\inventree`）執行：

```powershell
powershell -ExecutionPolicy Bypass -File .\backup.ps1
```

備份檔會存到「文件\InvenTree備份\inventree-backup-時間.zip」，內容包括：
- 資料庫：帳號、權限、設定、庫存、異動紀錄
- 上傳的檔案
- 所有設定檔

系統不必停止。建議每天或每週備份一次，並另存一份到隨身碟或雲端。

> 備份內含密碼，請妥善保管。

**還原到新主機**（換電腦時用，會覆蓋新主機資料庫）：

```powershell
powershell -ExecutionPolicy Bypass -File .\restore.ps1 -BackupZip "D:\inventree-backup-時間.zip"
```

完整換主機流程見 [`inventree-install-guide.md`](../inventree-install-guide.md) 第七章。還原腳本尚未實測，放入重要資料前請先演練一次。

## 常見問題

| 狀況 | 處理 |
|---|---|
| 最後出現「Unable to save shortcut …??????.lnk」 | 系統語言非中文，捷徑元件不支援中文檔名；已修正，重新下載後再跑一次 `setup-server.ps1`（不重跑也可，系統已啟動） |
| 其他電腦連不到 | ① 主機已開機且系統在執行 ② 兩台在同一個網路 ③ 主機網路設定為「私人網路」 ④ 防火牆已開放 80 埠 |
| 主機 IP 變了 | 在路由器把 IP 固定給主機；IP 改變時，在主機重新執行 `setup-server.ps1`，其他電腦重建捷徑 |
| 出現 INVE-E7 錯誤 | 你用的網址不在允許清單中。請用 `http://localhost`（主機上）或 `http://主機IP`，然後重新執行 `setup-server.ps1` |
| 想還原成官方原始設定 | 安裝資料夾中把 `.env.bak-時間` 改名回 `.env`，刪除 `docker-compose.override.yml`，執行 `docker compose up -d` |
| 曾裝過 Tampermonkey 版助手 | 可以移除；App 已內建，兩者同時存在也不會重複顯示 |

## 驗證狀況

- ✅ **代理設定**：用真正的 Caddy 2.10 驗證設定有效。InvenTree 預設會禁止被內嵌，已確認設定能正確覆蓋。
- ✅ **App 外框**：在 Chromium 用模擬的 InvenTree 測試，用 localhost 與 IP 兩種網址開啟都能載入，中文操作助手也能內建運作；重新整理後會停在原頁面。
- ✅ **主機設定（.env 部分）**：用安裝產生的 1.5.6 `.env` 測過，可重複執行，不會重複寫入或改到其他設定。
- ✅ **允許連入的設定**：依 InvenTree 1.5.6 原始碼核對（主機清單、信任來源、`zh-hant` 語言代碼）。
- 🧪 **尚未實測**：Windows 上實際執行各腳本，以及連接真的 InvenTree。這裡只能檢查 PowerShell 語法，第一次執行如有錯誤，請把畫面訊息貼給我。
