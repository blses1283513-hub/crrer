# 庫存管理系統：完整安裝流程

從一台全新的 Windows 電腦開始，到擁有全部功能，並可日後**把主機換成另一台電腦**。

> 版本：InvenTree **1.5.6**（Docker 安裝）。
> 本文的每一步都有「驗收」，做完一步、驗收通過再進下一步。
> 標示 🧪 的是尚未在真機實測、依文件推定的做法，遇到差異請以畫面為準。

## 一、先看懂：誰是誰

| 角色 | 說明 | 要做什麼 |
|---|---|---|
| **主機** | 跑系統與資料庫的那一台電腦，**要保持開機** | 做第二、三章的全部步驟 |
| **用戶端** | 公司其他人的電腦，用瀏覽器連到主機 | 只做第四章，不需要 Docker |

資料全部在主機。換電腦使用，就是換「用戶端」或換「主機」（見第七章）。

## 二、你會得到什麼功能

| 功能 | 說明 | 來源 |
|---|---|---|
| 庫存管理 | 零件／SKU、庫位、庫存、採購單（進貨）、銷售單（出貨）、盤點、低庫存通知 | InvenTree 內建 |
| 三間公司、450 個 SKU | 3 公司 × 10 產品 × 5 樣式 × 3 尺寸，料號如 `A-P03-S2-XL` | `inventree-seed/` 匯入腳本 |
| 只有自家使用者能修改 | 各公司庫位由該公司群組擁有；看得到、改不到別家庫存（**管理員例外**） | 擁有權控制 |
| 繁體中文 | 預設語言為繁體中文 | `INVENTREE_LANGUAGE=zh-hant` |
| 💡 滑鼠停留說明 | 停在按鈕上跳出中文操作說明 | App 內建操作助手 |
| 📦 調貨提醒 | 打開「轉移庫存」跳出提醒視窗，即時顯示來源與目的公司，跨公司會警告 | App 內建操作助手 |
| 📋 異動紀錄 | 所有庫存異動的時間、操作人，可篩選、匯出 CSV | App 內建操作助手 |
| 桌面 App | 桌面圖示一鍵啟動，獨立視窗（無網址列） | `inventree-app/` |
| 多台電腦共用 | 區網內其他電腦連到主機，看到同一份資料 | `inventree-app/` |
| 備份與還原 | 一鍵備份成 zip；可還原到新主機 | `backup.ps1`、`restore.ps1` |

## 三、主機安裝（依序做）

### 步驟 1：安裝 Docker Desktop

1. 到 <https://www.docker.com/products/docker-desktop/> 下載並安裝，依提示啟用 WSL 2，必要時重新開機。
2. 開啟 Docker Desktop，等左下角顯示 **Engine running**。
3. 在 Docker Desktop 設定的 General 中，勾選 **Start Docker Desktop when you sign in**（開機後系統能自動啟動）。

**驗收**：開 PowerShell，輸入 `docker version`，看得到 Client 與 Server 兩段版本資訊。

### 步驟 2：下載本專案

1. 下載 <https://github.com/blses1283513-hub/crrer/archive/refs/heads/claude/sharp-brahmagupta-tnbukb.zip>（私人 repo 需先登入 GitHub）。
2. 解壓縮到固定位置，例如 `C:\inventree-setup\`。
3. 裡面與本流程有關的是這四個資料夾，**請保持在同一個資料夾內**（腳本會用相對位置找彼此）：

   | 資料夾 | 用途 |
   |---|---|
   | `inventree-install` | 安裝 InvenTree |
   | `inventree-seed` | 匯入公司、產品、450 個 SKU |
   | `inventree-app` | App、區網共用、備份、還原 |
   | `inventree-ui-helper` | 中文操作助手（會被複製進 App） |

   repo 裡的其他檔案與本系統無關，可忽略。

**驗收**：解壓縮後看得到上述四個資料夾。

### 步驟 3：安裝 InvenTree

1. 開 PowerShell，切到 `inventree-install`：

   ```powershell
   cd C:\inventree-setup\...\inventree-install
   powershell -ExecutionPolicy Bypass -File .\install.ps1
   ```

2. 依提示輸入管理員帳號、Email、密碼。
   - 密碼**不可含單引號 `'`**。請記下這組帳密，之後登入用。
3. 等待。第一次要下載映像並初始化資料庫，**約 3–5 分鐘**，期間畫面可能一段時間沒動作。
4. 預設安裝到 `C:\Users\你的帳號\inventree`（可用 `-InstallDir` 改位置，之後所有「安裝資料夾」都指這裡）。

**驗收**：在安裝資料夾執行 `docker compose ps`，五個容器（db、cache、server、worker、proxy）都是 `Up … (healthy)`。瀏覽器開 <http://localhost> 看得到登入頁。

### 步驟 4：登入並建立三個公司群組

1. 用步驟 3 的管理員帳密登入 <http://localhost>。
2. 建立三個使用者群組，名稱要**完全一致**：`company-A`、`company-B`、`company-C`。
   - 位置：🧪 管理中心（Admin Center）→ 使用者（Users）→ 群組（Groups）。
   - 若管理中心打不開（出現 INVE-E17），改用 <http://localhost/admin/> 的「Groups」。
3. 設定各群組的權限（roles）。建議起點（可日後調整）：

   | 項目 | 檢視 | 新增 | 修改 | 刪除 |
   |---|---|---|---|---|
   | 零件、零件分類 | ✔ | | | |
   | 庫存、庫位 | ✔ | ✔ | ✔ | |
   | 採購單、銷售單 | ✔ | ✔ | ✔ | |

   「刪除」一律不開，庫存數量錯誤請用「盤點」修正。
4. 建立各公司的使用者帳號，加入對應群組。一般人員**不要**給管理員權限。

**驗收**：三個群組存在；各自有至少一個使用者。

### 步驟 5：建立管理員 API token

1. 登入後進入你的使用者設定（右上角使用者選單 → 帳號設定），🧪 找「存取權杖（Access Tokens）」，建立一個，**立刻複製**。
2. token 等同密碼，不要分享、不要貼到聊天或文件。

**驗收**：手上有一串 token。

### 步驟 6：匯入公司與 450 個 SKU

1. 安裝 Python 3（<https://www.python.org/downloads/>，安裝時勾選 **Add python.exe to PATH**）。驗證：`python --version`。
2. 切到 `inventree-seed`，複製設定檔：

   ```powershell
   cd C:\inventree-setup\...\inventree-seed
   copy config.example.json config.json
   ```

3. 用記事本開 `config.json`，把公司名稱、群組名稱、樣式、尺寸改成你要的。預設是「A 公司／B 公司／C 公司」、群組 `company-A` 等。
   - ⚠️ **公司名稱要與中文操作助手一致**：如果改了公司名稱，也要改 `inventree-ui-helper\inventree-ui-helper.user.js` 開頭 `CONFIG.companies`，並且**在步驟 7 之前**改好（步驟 7 會把它複製進 App）。
4. 先試跑（不連線，只產生清單）：

   ```powershell
   python seed_skus.py --config config.json --dry-run
   ```

   應顯示「3 公司，30 產品模板，450 個 SKU」。
5. 正式匯入：

   ```powershell
   $env:INVENTREE_URL = "http://localhost"
   $env:INVENTREE_TOKEN = "貼上步驟 5 的 token"
   python seed_skus.py --config config.json
   ```

   腳本可重複執行，已存在的資料不會重複建立。
6. 🧪 第一次執行如果出現 API 錯誤（尤其是參數相關），請把完整錯誤訊息（不含 token）交給協助的人處理。

**驗收**：「零件」頁看到 30 個產品、450 個 SKU；「庫存」頁看到三間公司的庫位。

### 步驟 7：設定成 App 並開放區網（setup-server）

1. 以**系統管理員身分**開 PowerShell（在開始選單對 PowerShell 按右鍵）。
2. 切到 `inventree-app` 執行：

   ```powershell
   cd C:\inventree-setup\...\inventree-app
   powershell -ExecutionPolicy Bypass -File .\setup-server.ps1
   ```

3. 它會偵測主機的區網 IP，請依下列確認後按 Enter：
   - 在 PowerShell 輸入 `ipconfig`，確認 IPv4 位址是你**實際上網那張網卡**（Wi-Fi 或乙太網路），不是 VPN、WSL、Hyper-V 的虛擬網卡。不對就手動輸入正確 IP。
4. 腳本會**列出所有變更並等你輸入 `Y`**。內容包括：備份並修改 `.env`、放置 App 檔案、開防火牆 80 埠、重啟系統、建立桌面捷徑。原本的 `.env` 會備份為 `.env.bak-時間`。
5. 重啟約 1–5 分鐘，資料不受影響。
6. 結束時會顯示：其他電腦要用的網址，以及建立捷徑的指令。**把那一行指令存起來**，第四章要用。

**如果出現黃色警告「公用網路」**：到「設定 → 網路和網際網路 → 內容」，把目前網路改成**私人網路**，否則其他電腦會被防火牆擋住。

**驗收**：桌面出現「庫存管理系統」圖示，點兩下會開出獨立視窗，介面為繁體中文，右下角有「💡 操作說明」與「📋 異動紀錄」兩個按鈕。

> 若捷徑建立失敗：不影響系統，改用 <http://localhost> 或照畫面上的提示手動建立捷徑（原因與修正見第八章）。

### 步驟 8：啟用擁有權控制（最後才做）

1. 🧪 以管理員登入，進入系統設定（System Settings）→ 庫存（Stock），開啟**庫存擁有權控制（Stock Ownership Control）**。
2. ⚠️ 一定要在步驟 6（匯入，會設定庫位擁有者）**之後**才開。開啟後，沒有擁有者的庫位與庫存，除管理員外沒人能修改。

**驗收**（用各公司的一般帳號測）：
- A 公司帳號：能修改 A 公司庫存。
- A 公司帳號：看得到 B、C 公司庫存，但**不能修改**（按鈕被隱藏）。
- 🧪 實測：用 A 帳號走一次採購收貨，確認新入庫的庫存仍屬於 A 公司（能由 A 修改）。

### 步驟 9：整體驗收清單

- [ ] 桌面圖示可一鍵開啟，介面為繁體中文
- [ ] 滑鼠停在「庫存」「轉移」等按鈕上 0.5 秒會出現中文說明
- [ ] 打開「轉移庫存」，右上角跳出調貨提醒；選到別家公司庫位會變橘色警告
- [ ] 做一次進貨、轉移、出貨後，「📋 異動紀錄」能看到時間與操作人
- [ ] 各公司帳號權限符合步驟 8 的驗收
- [ ] 已執行一次 `backup.ps1` 並確認產生 zip（第六章）

## 四、其他電腦（用戶端）

**不需要 Docker，不需要系統管理員。** 前提：與主機在**同一個區網**，且主機已開機、系統在執行。

在那台電腦開 PowerShell，貼上步驟 7 結束時顯示的那一行，格式如下：

```powershell
iwr http://主機IP/app/client-shortcut.ps1 -OutFile $env:TEMP\cs.ps1; powershell -ExecutionPolicy Bypass -File $env:TEMP\cs.ps1 -Server 主機IP
```

桌面會出現「庫存管理系統」圖示。用**自己的帳號**登入。

替代方法：用 Edge 開 `http://主機IP`，右上角「⋯」→「應用程式」→「將此網站安裝為應用程式」。

**驗收**：點圖示能開啟，且看到與主機相同的庫存資料。

## 五、日常使用

- **主機**：保持開機。開機後 Docker 會自動啟動系統；也可點桌面圖示，會自動確認並啟動。
- **用戶端**：點桌面圖示即可。
- **停止系統**（極少需要）：在安裝資料夾執行 `docker compose down`，資料不會遺失。再次啟動：`docker compose up -d` 或點桌面圖示。
- **主機 IP 變了**：其他電腦會連不到。到路由器把 IP **固定給主機**（DHCP 保留）。若 IP 已變，在主機重新執行 `setup-server.ps1`，其他電腦重做第四章。

## 六、備份

**手動備份**（系統不必停止）：

```powershell
cd C:\Users\你的帳號\inventree
powershell -ExecutionPolicy Bypass -File .\backup.ps1
```

產生 `文件\InvenTree備份\inventree-backup-時間.zip`，內含資料庫（帳號、權限、設定、庫存、異動紀錄）、上傳檔案、設定檔。

**自動備份**（每天凌晨 2 點；🧪 以系統管理員身分執行一次；備份時 Docker 須在執行中）：

```powershell
schtasks /Create /SC DAILY /ST 02:00 /TN "InvenTreeBackup" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\你的帳號\inventree\backup.ps1"
```

⚠️ 備份內含密碼（`.env`），請妥善保管。**請定期另存一份到隨身碟或雲端**，不要只放在主機本身。

## 七、把主機換成另一台電腦

情境：換新電腦、或要讓別台電腦當主機。**新主機的 IP 會不同，其他電腦要重做第四章。**

在**舊主機**：

1. 執行 `backup.ps1`，取得最新備份 zip。
2. 記下版本：打開安裝資料夾的 `.env`，看 `INVENTREE_TAG=`（目前是 `1.5.6`）。
3. 把 zip 複製到新主機（隨身碟或網路）。

在**新主機**：

4. 做**步驟 1、2**（Docker、下載專案）。
5. 做**步驟 3**。⚠️ 版本必須與舊主機相同：舊主機不是 1.5.6 時，加上 `-Version`，例如：

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Version 1.5.6
   ```

   管理員帳密隨便設即可，還原後會被舊主機的帳號取代。
6. 做**步驟 7**（`setup-server.ps1`）。這一步會設定新主機的 IP、App 與防火牆。
7. **跳過**步驟 4、5、6、8（群組、匯入、擁有權設定都已在備份裡）。
8. 到新主機的安裝資料夾執行還原（🧪 還原腳本尚未實測）：

   ```powershell
   cd C:\Users\你的帳號\inventree
   powershell -ExecutionPolicy Bypass -File .\restore.ps1 -BackupZip "D:\inventree-backup-時間.zip"
   ```

   腳本會列出變更並等你輸入 `Y`。**它會覆蓋新主機資料庫的全部內容。**
9. 用**舊主機的帳號密碼**登入，檢查庫存數量、異動紀錄、群組與權限是否與舊主機一致。

最後：

10. 確認新主機運作正常後，**關閉舊主機的系統**（`docker compose down`），避免兩台同時有人輸入資料造成資料分岔。
11. 通知所有人：重做第四章（用新主機的 IP）。舊的桌面圖示可刪除。

## 八、疑難排解

| 狀況 | 原因與處理 |
|---|---|
| 步驟 7 最後出現 `Unable to save shortcut …??????.lnk` | 你的 Windows 系統語言不是中文，建立捷徑的元件無法處理中文檔名。**已修正**：請重新下載最新的專案，重新執行 `setup-server.ps1`（會備份 `.env`，可安全重跑）。**不重跑也沒關係**，系統已經啟動，直接用 <http://localhost> 即可 |
| 其他電腦連不到 | ① 主機已開機且系統在執行（`docker compose ps`）② 兩台在同一個網路 ③ 主機網路設定為「私人網路」④ 防火牆有開 TCP 80 ⑤ 用的是 `http://主機IP`，不是 `https` |
| 用手機熱點時其他電腦連不到 | 熱點常會禁止裝置互相連線，IP 也容易變動。**正式使用請改用路由器或有線／Wi-Fi 區網**，並固定主機 IP |
| 打開網址出現 INVE-E7 | 你用的網址不在允許清單。主機用 `http://localhost`，其他電腦用 `http://主機IP`；IP 變了就重跑 `setup-server.ps1` |
| 管理中心出現 INVE-E17 | 前端畫面載入錯誤。Ctrl+F5、換無痕視窗或換瀏覽器；仍不行就用 <http://localhost/admin/> |
| 啟動時說 80 埠已被佔用 | 已有程式（如 IIS）佔用 80 埠。先關掉該程式；不行的話見 `inventree-install/README.md` 的 8080 埠改法 |
| 啟動很久沒反應 | 第一次可能 3–5 分鐘。`docker compose ps` 看狀態，`docker compose logs --tail 50 inventree-server` 看原因 |
| PowerShell 說「禁止執行指令碼」 | 照本文用 `powershell -ExecutionPolicy Bypass -File …` 執行 |
| 密碼含單引號被拒 | 安裝腳本不允許帳號、Email、密碼含 `'`，換一組即可 |
| 登入頁沒有登入框 | 容器可能尚未就緒或瀏覽器快取：`docker compose ps` 確認全部 healthy，再用無痕視窗開 `http://localhost/web/login` |
| 想回到官方原始設定 | 安裝資料夾中，把 `.env.bak-時間` 改名回 `.env`，刪除 `docker-compose.override.yml`，執行 `docker compose up -d` |

## 九、附錄

### 檔案與資料夾位置（主機）

| 位置 | 內容 |
|---|---|
| `C:\Users\你的帳號\inventree\` | 安裝資料夾：`.env`、`docker-compose.yml`、`docker-compose.override.yml`、`Caddyfile.app`、`start-inventree.ps1`、`backup.ps1`、`restore.ps1`、`app\` |
| `…\inventree\inventree-data\` | **所有資料**（資料庫、上傳檔案）。請勿手動修改或刪除 |
| `文件\InvenTree備份\` | 備份 zip |

### 完全移除（⚠️ 資料會永久消失，請先備份）

```powershell
cd C:\Users\你的帳號\inventree
docker compose down
```

再刪除安裝資料夾，即移除全部資料。

### 驗證狀況

| 項目 | 狀況 |
|---|---|
| InvenTree 1.5.6 安裝與啟動（`install.ps1`） | ✅ 在你的主機實測成功 |
| `setup-server.ps1`：`.env` 修改、App 檔案、防火牆、重啟 | ✅ 在你的主機實測成功 |
| 桌面捷徑 | 已修正中文檔名問題；🧪 修正後尚未重新實測 |
| 代理設定、App 外框、中文操作助手 | ✅ 以真正的 Caddy 與模擬頁面在瀏覽器測試通過；🧪 尚未在真的 InvenTree 畫面實測 |
| 匯入腳本 `seed_skus.py` | 🧪 尚未對真的 InvenTree 1.5.6 實測 |
| 其他電腦連入（區網） | 🧪 尚未實測（你目前接的是手機熱點，見第八章） |
| `backup.ps1`、`restore.ps1`、自動備份排程 | 🧪 尚未實測，**請在放入重要資料前先完整演練一次：備份 → 在另一台還原 → 核對資料** |
