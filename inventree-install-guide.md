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
| ⚠️ 異常數量警告 | 移除、轉移、盤點、新增時，數量 ≥100、超過現有庫存、或歸零，送出前跳出確認 | App 內建操作助手 |
| 🔀 快速調貨 | 搜尋料號、依公司分色看各庫位庫存、點選來源與目的即可調貨（可跨公司，會提醒） | App 內建操作助手 |
| 🧹 零件整理 | 停用／還原／永久刪除不需要的零件，附多層安全檢查，刪除前自動匯出異動紀錄，且不會被匯入腳本建回來 | `inventree-seed/manage_parts.py`（見「整理不需要的零件」） |
| 🎛️ 浮動面板 | 右下角平常只有一個小圓點（顯示未讀通知數），滑鼠移上去才展開四個功能按鈕，不會擋住操作 | App 內建操作助手 |
| 🔔 通知小視窗 | 低庫存、別家公司或管理員把庫存調進／調出你的公司庫位、大量或歸零的異常操作；**只通知與你所屬公司有關的事**；已讀紀錄存在伺服器，換電腦也一致 | 通知服務 `inventree-app/notifier/`（詳見該資料夾的 README） |
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

### 步驟 4：建立 API token（先做，下一步的腳本要用）

1. 用步驟 3 的管理員帳密登入 <http://localhost>。
2. 進入你的使用者設定（右上角使用者選單 → 帳號設定），🧪 找「存取權杖（Access Tokens）」，建立一個，**立刻複製**。
3. token 等同密碼，不要分享、不要貼到聊天或文件。

**驗收**：手上有一串 token。

### 步驟 5：建立職務分級（群組與權限）

權限分兩個維度，使用者要**同時**屬於兩邊才能修改自家公司庫存：

| 維度 | 群組 | 決定什麼 |
|---|---|---|
| 公司 | `company-A`、`company-B`、`company-C` | 能修改**哪家公司**的庫存（庫位擁有權）；本身只給檢視 |
| 職務 | `role-manager` 公司主管、`role-warehouse` 倉管、`role-sales` 業務、`role-viewer` 唯讀 | 能做**什麼動作**（見下表） |

| 職務 | 庫存 | 採購單（進貨） | 銷售單（出貨） | 其他 |
|---|---|---|---|---|
| 公司主管 | 檢視、新增、修改 | 檢視、新增、修改 | 檢視、新增、修改 | 零件、庫位唯讀 |
| 倉管 | 檢視、新增、修改 | 檢視、新增、修改 | 檢視 | 零件、庫位唯讀 |
| 業務 | 檢視 | 檢視 | 檢視、新增、修改 | 零件、庫位唯讀 |
| 唯讀 | 檢視 | 檢視 | 檢視 | 全部唯讀 |

**所有職務都沒有刪除權限**（庫存錯誤請用「盤點」修正），也都沒有「管理」角色（帳號與權限由 superuser 統一管理）。完整矩陣見 `inventree-seed/roles.json`，可自行調整。

執行（先用 `show` 預覽，不連線）：

```powershell
cd C:\inventree-setup\...\inventree-seed
copy config.example.json config.json
python setup_roles.py show
```

確認後正式建立（會先列出變更並等你輸入 `Y`）：

```powershell
$env:INVENTREE_URL = "http://localhost"
$env:INVENTREE_TOKEN = "貼上步驟 4 的 token"
python setup_roles.py apply
```

建立使用者並加入群組（**不需要郵件伺服器**，密碼由你設定，輸入時不顯示）：

```powershell
python setup_roles.py add-user a-wh --groups company-A,role-warehouse --email a-wh@example.com
python setup_roles.py add-user b-sales --groups company-B,role-sales
```

一個人要有一個公司群組＋一個職務群組。只有公司群組、沒有職務群組的人只能檢視。

稽核（唯讀，建議每月做一次）：

```powershell
python setup_roles.py audit
```

會列出：superuser 是否超過 2 人、沒有任何群組的帳號、只有公司群組沒有職務群組的帳號、每個人的群組。

> 🧪 `add-user` 依 InvenTree 原始碼設計，尚未在真機實測：建立使用者時系統會嘗試寄信（尚未設定郵件伺服器，可能只在記錄中出現錯誤，不影響帳號建立）。若 `add-user` 失敗，改用管理中心或 <http://localhost/admin/> 手動建立，並把錯誤訊息交給協助的人。

**驗收**：`python setup_roles.py audit` 沒有警告；各公司至少有一個倉管帳號。

### 步驟 6：匯入公司與 450 個 SKU

1. 安裝 Python 3（<https://www.python.org/downloads/>，安裝時勾選 **Add python.exe to PATH**）。驗證：`python --version`。
2. 切到 `inventree-seed`，複製設定檔（步驟 5 已複製過的話，這一步略過，直接進入下一項）：

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
   $env:INVENTREE_TOKEN = "貼上步驟 4 的 token"
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

**驗收**：桌面出現「庫存管理系統」圖示，點兩下會開出獨立視窗，介面為繁體中文，右下角有一個小圓點，滑鼠移上去會展開「🔔 通知」「🔀 快速調貨」「📋 異動紀錄」「💡 操作說明」四個按鈕。

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
- [ ] 完成 [`inventree-acceptance-checklist.md`](inventree-acceptance-checklist.md) 真實環境驗收清單

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

### 整理不需要的零件（停用與刪除）

InvenTree 本身有刪除零件的功能，但有兩個陷阱（依 1.5.6 原始碼）：

1. **啟用中的零件不能刪**，必須先「停用」。
2. **刪除零件會連帶永久刪除它所有的庫存項目與全部異動紀錄（時間、操作人）**，無法復原；刪除範本時，底下的變體不會被刪，而是變成沒有範本的獨立零件。

所以建議**先停用、確定不需要再刪除**：

| | 停用（retire） | 永久刪除（delete） |
|---|---|---|
| 零件、庫存、異動紀錄 | 全部保留 | **全部消失** |
| 之後能還原嗎 | 可以（restore），隨時 | 不行，只能從備份還原 |
| 快速調貨、低庫存通知 | 不再出現 | 不再出現 |
| 誰能做 | superuser | superuser（職務群組刻意沒有刪除權限） |

**單一零件（網頁）**：零件頁面 → 編輯 → 取消勾選「啟用」→ 儲存。確定要刪除時，用 superuser 帳號在零件頁面的「⋮」選單選刪除（只有已停用的零件會出現）。

**一次處理多個（建議）**：用 `inventree-seed\manage_parts.py`。需要 superuser 的 API token；一定要用 `--ipn`、`--glob` 或 `--file` 指定範圍，工具**不提供「全部」**。

```powershell
$env:INVENTREE_URL = "http://localhost"
$env:INVENTREE_TOKEN = "貼上 superuser 的 token"

python manage_parts.py list    --glob "A-P03-S5-*"      # 先看會選到哪些（唯讀）
python manage_parts.py retire  --glob "A-P03-S5-*"      # 停用（可還原）
python manage_parts.py restore --glob "A-P03-S5-*"      # 後悔了：還原
python manage_parts.py delete  --glob "A-P03-S5-*"      # 永久刪除（見下方保護）
```

`delete` 的保護（任何一項不符合就**不會刪**，並列出原因）：

- 零件必須已停用（工具自己檢查，不只靠伺服器）
- 庫存必須是 0
- 不能有銷售單或採購單明細，也不能有「採購中、生產中、已分配」的數量
- 範本底下還有不在這次範圍的變體時，不會刪
- 無法確認訂單狀況時（讀不到），預設停下，必須你確認後加 `--ignore-warnings`
- 刪除前**自動匯出**零件資料與異動紀錄（CSV）到 `deleted-parts-時間\` 資料夾
- 要求你輸入要刪除的數量，並再確認「已備份」
- 刪除成功後記錄到 `removed_parts.json`，**之後執行 `seed_skus.py` 不會把這些料號建回來**

> 刪除前請先執行 `backup.ps1`。可以加 `--dry-run` 只看檢查結果、不刪除。

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
| 🔔 鈴鐺是灰色（通知服務尚未啟用） | 在安裝資料夾執行 `docker compose ps`，確認 `inventree-notifier` 在執行；沒有的話重新執行 `setup-server.ps1`。紀錄：`docker compose logs --tail 50 inventree-notifier` |
| 🔔 一直沒有通知 | 自己的操作不會通知自己，請用**另一個帳號**測試；帳號要加入 `company-X` 群組；通知最多約 30 秒才會出現 |
| 想回到官方原始設定 | 安裝資料夾中，把 `.env.bak-時間` 改名回 `.env`，刪除 `docker-compose.override.yml`，執行 `docker compose up -d` |

## 九、更新已安裝的系統

已經依本文安裝好，之後下載了新版專案（例如新增了功能）時，照下面做。**資料庫與庫存資料不會被動到**；`setup-server.ps1` 只會更新 App 檔案、`.env` 的設定與新增的容器，執行前會列出變更並等你輸入 `Y`，`.env` 會先自動備份。

**1. 用瀏覽器下載最新版**（私人 repo 需先登入 GitHub），存到「下載」資料夾：

```
https://github.com/blses1283513-hub/crrer/archive/refs/heads/claude/sharp-brahmagupta-tnbukb.zip
```

**2. 以系統管理員身分開 PowerShell**，依序貼上（路徑請依你的實際位置調整）：

```powershell
# 備份（建議；失敗不影響更新，但請把錯誤訊息留著）
cd C:\Users\Ande\inventree
powershell -ExecutionPolicy Bypass -File .\backup.ps1

# 解壓縮到新資料夾（不覆蓋舊檔）
$zip  = (Get-ChildItem "C:\Users\Ande\Downloads\crrer-claude-sharp-brahmagupta-tnbukb*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
"使用的壓縮檔：$zip"
$dest = "C:\Users\Ande\Downloads\DEMOO\update-$(Get-Date -Format yyyyMMdd)"
Expand-Archive -Path $zip -DestinationPath $dest -Force

# 找到新版的 inventree-app，並沿用你原本的公司設定（inventree-seed\config.json，如果有）
$app  = (Get-ChildItem $dest -Recurse -Filter setup-server.ps1 | Select-Object -First 1).DirectoryName
$seed = Join-Path (Split-Path $app -Parent) "inventree-seed"
$old  = Get-ChildItem "C:\Users\Ande\Downloads\DEMOO" -Recurse -Filter config.json -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryName -like "*\inventree-seed" -and $_.FullName -notlike "$dest*" } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($old) { Copy-Item $old.FullName $seed -Force; "已沿用公司設定：$($old.FullName)" } else { "找不到舊的 config.json，將使用預設的 A/B/C 公司設定" }

# 執行更新
cd $app
powershell -ExecutionPolicy Bypass -File .\setup-server.ps1 -InstallDir C:\Users\Ande\inventree
```

畫面會列出變更與「通知服務的公司設定」，**確認公司名稱與你實際的一致**再輸入 `Y`。若不一致，輸入 `N` 取消，把正確的 `config.json` 放進新資料夾的 `inventree-seed` 再重新執行。

**3. 確認成功**：

```powershell
cd C:\Users\Ande\inventree
docker compose ps                                  # 應該有 inventree-notifier，狀態 Up (healthy)
docker compose logs --tail 20 inventree-notifier   # 應該看到「通知服務啟動」「初始化完成」
(Invoke-WebRequest http://localhost/notify/api/health -UseBasicParsing).Content   # 應該顯示 {"ok": true}
```

接著點桌面「庫存管理系統」，按 **Ctrl+F5**，右下角應該出現一個小圓點（有未讀通知時顯示數字），滑鼠移上去會展開 🔔 通知、🔀、📋、💡 四個按鈕。再用 [`inventree-acceptance-checklist.md`](inventree-acceptance-checklist.md) 的 F 區驗收通知。

**其他電腦不需要重新安裝。** 它們開啟 App 時會自動載入新版（按一次 Ctrl+F5 最保險）。

### 只更新有改變的檔案（不用重新下載整個專案）

如果這次更新**只動到幾個檔案**，不必下載整個 zip、也不必跑 `setup-server.ps1`：直接從 GitHub 下載那幾個檔案，換到對應的位置即可。**資料不會被動到。** 每次更新我都會告訴你是哪幾個檔案、要不要重啟通知服務。

| 檔案 | 放在哪裡 | 更新後要做什麼 |
|---|---|---|
| `inventree-ui-helper.user.js`（操作助手、浮動面板） | `C:\Users\Ande\inventree\app\` | 每台電腦按一次 Ctrl+F5（只在主機換一次，全部電腦都會更新） |
| `notifier.py`（通知服務） | `C:\Users\Ande\inventree\notifier\` | `docker compose restart inventree-notifier`（約 5 秒，已讀紀錄保留） |
| `manage_parts.py`、`seed_skus.py`（零件整理、匯入） | `C:\Users\Ande\inventree\tools\`（新建） | 不用重啟，在這個資料夾執行 |
| `backup.ps1`（備份腳本） | `C:\Users\Ande\inventree\` | 不用重啟 |

> 什麼時候不能只換檔案？更新內容碰到 Docker 設定（`docker-compose.override.yml`）、`Caddyfile.app`、`.env`、`setup-server.ps1`，就要用上面的「完整更新」。

**一般 PowerShell 即可（不需要系統管理員）**，整段貼上。它會先把所有檔案下載並檢查內容，**全部正確才開始替換**，替換前會備份舊檔：

```powershell
$base  = "https://raw.githubusercontent.com/blses1283513-hub/crrer/claude/sharp-brahmagupta-tnbukb"
$root  = "C:\Users\Ande\inventree"
$tools = Join-Path $root "tools"
New-Item -ItemType Directory -Force -Path $tools | Out-Null

# 要更新的檔案：來源路徑、安裝位置、用來確認內容正確的關鍵字
$files = @(
  @{ src = "inventree-ui-helper/inventree-ui-helper.user.js"; dst = "$root\app\inventree-ui-helper.user.js"; marker = "active=true" },
  @{ src = "inventree-app/notifier/notifier.py";              dst = "$root\notifier\notifier.py";             marker = "零件被刪除或資料庫還原" },
  @{ src = "inventree-seed/manage_parts.py";                  dst = "$tools\manage_parts.py";                  marker = "零件整理" },
  @{ src = "inventree-seed/seed_skus.py";                     dst = "$tools\seed_skus.py";                     marker = "load_removed" },
  @{ src = "inventree-app/backup.ps1";                        dst = "$root\backup.ps1";                        marker = "零件整理工具資料夾" }
)
$stamp  = Get-Date -Format yyyyMMdd-HHmmss
$staged = @()

# 1. 全部先下載並檢查（任何一個不對就整個停止，不會替換任何檔案）
foreach ($f in $files) {
  $tmp = Join-Path $env:TEMP ("upd-" + [IO.Path]::GetFileName($f.src))
  Invoke-WebRequest "$base/$($f.src)" -OutFile $tmp -UseBasicParsing
  $text = [IO.File]::ReadAllText($tmp, [Text.Encoding]::UTF8)
  if ($text.Length -lt 1000 -or $text -notmatch [regex]::Escape($f.marker)) { throw "下載的 $($f.src) 內容不正確，已停止，沒有替換任何檔案。" }
  $staged += @{ tmp = $tmp; dst = $f.dst }
}

# 2. 備份舊檔後替換
foreach ($s in $staged) {
  if (Test-Path $s.dst) { Copy-Item $s.dst "$($s.dst).bak-$stamp" }
  Copy-Item $s.tmp $s.dst -Force
}

# 3. 通知服務套用新程式（已讀紀錄保留）
Set-Location $root
docker compose restart inventree-notifier
"完成。各台電腦的 App 請按一次 Ctrl+F5。"
```

**如果下載被拒絕**（repo 是私人的）：改用上面「完整更新」，或用瀏覽器登入 GitHub 後逐一下載那幾個檔案，放到上表的位置。

**要還原某個檔案**：把同資料夾的 `檔名.bak-時間` 複製回原檔名即可（通知服務要再 `docker compose restart inventree-notifier`）。

**使用零件整理工具**需要 Python：`python --version` 能顯示版本即可。之後都在 `tools` 資料夾執行：

```powershell
cd C:\Users\Ande\inventree\tools
$env:INVENTREE_URL = "http://localhost"
$env:INVENTREE_TOKEN = "貼上 superuser 的 token"
python manage_parts.py list --glob "A-P03-S5-*"
```

`removed_parts.json` 會建立在這個資料夾。要重新匯入 SKU 時，請用這個資料夾的 `seed_skus.py`（把你的 `config.json` 複製進來，或加 `--config 路徑`），它會自動略過已刪除的料號；如果從別的資料夾執行，請加 `--removed C:\Users\Ande\inventree\tools\removed_parts.json`。

## 十、附錄

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

### 自動測試

每次推送到 GitHub，`.github/workflows/inventree-tests.yml` 會自動執行 `tests/` 內的測試。測試涵蓋：匯入腳本、安裝腳本、PowerShell 語法與 `.env` 編輯、中文操作助手、App 端對端。本機可用 `bash tests/run-all.sh` 執行。

真實 InvenTree 畫面上的行為，請用 [`inventree-acceptance-checklist.md`](inventree-acceptance-checklist.md) 逐項驗收。

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
