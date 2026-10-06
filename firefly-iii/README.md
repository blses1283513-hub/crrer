---
tags: [finance, firefly-iii, hub]
created: 2026-10-06
purpose: Firefly III 個人記帳系統的入口：安裝、匯入、每月流程、備份升級
---

# Firefly III 個人記帳系統

[Firefly III](https://github.com/firefly-iii/firefly-iii) 是開源、自架的記帳軟體，資料只存在你自己的電腦或 NAS 上。

| 檔案 | 用途 |
|---|---|
| [[設計]] | 帳戶、分類、預算、存錢筒、帳單的結構設計（**先讀**） |
| [[規則]] | 台灣常見商家的自動分類規則 |
| `docker-compose.yml` | Firefly III + MariaDB + Data Importer + 排程 |
| `.env.example` / `.db.env.example` / `.importer.env.example` | 設定範本（複製後填密碼） |
| `importer/玉山-存款.json`、`importer/玉山-信用卡.json` | 玉山銀行 CSV 匯入設定 |
| `scripts/check.ps1` | Windows 安裝檢查（唯讀） |
| `scripts/backup.sh` | 備份資料庫與附件（Windows 用 Git Bash 或 WSL 執行） |

> 🔒 `.gitignore` 已排除 `.env`、`.db.env`、`.importer.env`、`*.csv`、`*.xls(x)` 與 `backups/`。**真正的密碼與銀行對帳單永遠不要提交到 Git。**

---

## 1. 安裝（約 15 分鐘）

需求：已安裝 Docker 與 Docker Compose 的電腦或 NAS（Synology 用 Container Manager、QNAP 用 Container Station），至少 1 GB 記憶體。

**Windows PC：** 安裝 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)（需開啟 WSL 2，安裝程式會引導），安裝後**重新開機並啟動 Docker Desktop**。以下指令在 PowerShell 執行，並先 `cd` 到本資料夾。電腦要保持開機，手機才連得到；睡眠時服務會中斷。

```sh
cd firefly-iii
cp .env.example .env
cp .db.env.example .db.env
cp .importer.env.example .importer.env

# 產生兩組不同的 32 字元隨機字串，分別填入 .env 的 APP_KEY 與 STATIC_CRON_TOKEN
head -c 200 /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9' | head -c 32; echo
head -c 200 /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9' | head -c 32; echo
```

Windows PowerShell 版本（`cp` 同樣可用；上面兩行產生字串的指令改用這個，執行兩次）：
```powershell
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

編輯設定檔：
1. `.env`：填入 `APP_KEY`、`STATIC_CRON_TOKEN`、`DB_PASSWORD`、`SITE_OWNER`，並把 `APP_URL` 改成主機 IP，例如 `http://192.168.1.100:8080`。
2. `.db.env`：`MYSQL_PASSWORD` 要與 `.env` 的 `DB_PASSWORD` **相同**。
3. `.importer.env`：`VANITY_URL` 與 `APP_URL` 相同。`FIREFLY_III_ACCESS_TOKEN` 先留空，第 2 步再填。

```sh
docker compose up -d
docker compose logs -f app   # 看到 "Firefly III is ready" 類訊息後按 Ctrl+C
```

開啟 `http://<主機IP>:8080`，註冊第一個帳號（第一個註冊的就是管理員），主要幣別選 **TWD**。

> 若 8080 / 8081 埠已被 NAS 其他服務占用，修改 `docker-compose.yml` 中 `ports` 冒號**左邊**的數字，並同步更新 `APP_URL` 與 `VANITY_URL`。

## 2. 首次設定（約 30 分鐘，照 [[設計]] 建立）

1. **選項 → 貨幣**：確認 TWD 為預設；有外幣帳戶或海外刷卡就啟用 USD / JPY。
2. **帳戶 → 資產帳戶**：依 [[設計]] 第 1 節建立，填入今天的實際餘額作為開戶餘額。
3. **分類**：依 [[設計]] 第 3 節建立。
4. **預算**：依 [[設計]] 第 4 節建立 3 個預算，並啟用每月自動預算。
5. **存錢筒**、**帳單/訂閱**：依 [[設計]] 第 5、6 節建立。
6. **規則**：依 [[規則]] 建立 4 個規則群組。
7. **建立匯入工具權杖**：選項 → 個人資料 → OAuth → 個人存取權杖 → 建立。把權杖貼到 `.importer.env` 的 `FIREFLY_III_ACCESS_TOKEN`，然後執行：
   ```sh
   docker compose up -d importer
   ```

## 2.5 安裝檢查清單（Windows 電腦 + Android 手機）

先在電腦跑自動檢查（唯讀，不會改任何東西）：
```powershell
powershell -ExecutionPolicy Bypass -File scripts\check.ps1
```
它會檢查 Docker、三個設定檔、金鑰長度、四個容器與兩個網頁，並列出手機可用的網址。全部 `[OK]` 才算電腦端完成。手機端無法自動檢查，請逐項打勾：

| # | 裝置 | 檢查項目 | 應該看到 | ✓ |
|---|---|---|---|---|
| 1 | 電腦 | `check.ps1` 沒有 `[FAIL]` | 最後一行綠字「全部檢查通過」 | ☐ |
| 2 | 電腦 | 開 `http://localhost:8080` | Firefly III 登入或註冊頁 | ☐ |
| 3 | 電腦 | 已註冊管理員，主要幣別 TWD | 儀表板顯示 NT$ | ☐ |
| 4 | 電腦 | 開 `http://localhost:8081` | 匯入工具頁面（權杖已填） | ☐ |
| 5 | 手機 | 連同一個 Wi-Fi，Chrome 開 `http://<電腦區網IP>:8080` | 登入頁 | ☐ |
| 6 | 手機 | 登入成功 | 看得到儀表板 | ☐ |
| 7 | 手機 | Chrome ⋮ → 新增至主畫面 | 主畫面出現圖示 | ☐ |
| 8 | 手機 | 關掉 Wi-Fi 用行動網路，已連 Tailscale，開 Tailscale 位址 | 同樣的登入頁 | ☐ |

**手機連不上時（第 5 或第 8 項失敗），最常見原因是 Windows 防火牆。** 以系統管理員開 PowerShell（開始選單搜尋 PowerShell → 右鍵 → 以系統管理員身分執行），只放行這兩個埠，且只限家裡區網與 Tailscale：
```powershell
New-NetFirewallRule -DisplayName "Firefly III" -Direction Inbound -Protocol TCP -LocalPort 8080,8081 -Action Allow -Profile Any -RemoteAddress LocalSubnet,100.64.0.0/10
```
`100.64.0.0/10` 是 Tailscale 使用的位址範圍。這條規則不會讓網際網路上的其他人連入。
> 舊版本的這份文件用的是 `-Profile Private -RemoteAddress LocalSubnet`，Tailscale 的連線可能被擋，請改用上面這條。已建立過舊規則的話，先執行 `Remove-NetFirewallRule -DisplayName "Firefly III"` 再建立新的。

## 2.6 外出連線：Tailscale（Windows 電腦 + Android 手機）

目的：不開放路由器埠、不暴露到網際網路，只有你自己的裝置能連回家裡的電腦。Tailscale 個人使用免費。

1. **電腦：** 到 [tailscale.com/download](https://tailscale.com/download) 安裝 Windows 版，用 Google 或 Microsoft 帳號登入。
2. **手機：** Google Play 安裝 Tailscale，用**同一個帳號**登入，開啟 VPN 開關。
3. 在電腦 Tailscale 圖示上看電腦的 Tailscale IP（`100.x.y.z`）。`check.ps1` 也會列出。
4. 手機（關閉 Wi-Fi 測試）開 `http://100.x.y.z:8080`，應看到登入頁。
5. 編輯 `.env` 的 `APP_URL` 與 `.importer.env` 的 `VANITY_URL`，都改成 `http://100.x.y.z:8080`（電腦的 Tailscale 位址）。**建議在家和外出都統一用這個網址**：它不會因為換 Wi-Fi 而改變。`APP_URL` 若還是 `localhost`，手機登入後可能被導回 `localhost` 而打不開。改完後執行：
   ```powershell
   docker compose up -d --force-recreate
   ```
6. 讓電腦保持可連線：電腦要開機且不能睡眠；Docker Desktop 設定 → General → 勾選「Start Docker Desktop when you sign in」。
7. 在 Tailscale 管理頁（login.tailscale.com）對電腦選「Disable key expiry」，避免金鑰到期後突然連不上。

> ⚠️ 不要使用 Tailscale Funnel，也不要在路由器做埠轉發：那會把你的財務資料公開到網際網路上。
> `APP_URL` 只能設一個。用另一個網址開啟時，登入通常仍可用，但部分連結會導回 `APP_URL`；若發生，統一改用一種網址即可。
> 手機要記帳時需先開啟 Tailscale。

## 3. 匯入玉山銀行 CSV

### 3.1 先確認欄位（第一次必做）

⚠️ 兩份 JSON 的欄位順序是**依常見格式假設的，尚未用你的實際檔案驗證**。銀行改版也可能改變格式。第一次匯入前，請用文字編輯器打開 CSV，逐欄對照下表；不符時，到 Data Importer 的「角色設定」頁面調整，再按「下載設定檔」覆蓋這份 JSON。

**`玉山-存款.json`（假設 8 欄）**

| 欄 | 假設內容 | 角色 (role) |
|---|---|---|
| 0 | 交易日期 | `date_transaction` |
| 1 | 交易時間 | `_ignore` |
| 2 | 摘要 | `description` |
| 3 | 支出金額 | `amount_debit`（自動轉為負數） |
| 4 | 存入金額 | `amount_credit` |
| 5 | 餘額 | `_ignore` |
| 6 | 備註 | `note` |
| 7 | 轉出入帳號 | `opposing-number` |

**`玉山-信用卡.json`（假設 6 欄）**

| 欄 | 假設內容 | 角色 (role) |
|---|---|---|
| 0 | 消費日 | `date_transaction` |
| 1 | 入帳日 | `date_book` |
| 2 | 消費明細 | `description` |
| 3 | 新臺幣金額（消費為正、退款為負） | `amount_negated`（反轉正負號：消費變支出，退款變收入） |
| 4 | 外幣幣別 | `foreign-currency-code` |
| 5 | 外幣金額 | `amount_foreign` |

### 3.2 匯入前的檔案處理

- **編碼**：台灣銀行的匯出檔常是 **Big5**，匯入工具只吃 **UTF-8**。轉換方式（Mac / Linux / NAS）：
  ```sh
  iconv -f BIG5 -t UTF-8 原檔.csv > 原檔-utf8.csv
  ```
  Windows 可用記事本「另存新檔」，編碼選 UTF-8。
- **只有 Excel 檔**：用 Excel 開啟後「另存為 CSV UTF-8（逗號分隔）」。
- **民國年日期**（例如 `115/10/01`）：匯入工具無法直接解析。請先在 Excel 把日期欄轉成西元年 `2026/10/01`，或改用銀行提供的西元年格式匯出。
- **日期格式不同**：若是 `2026-10-01`，把 JSON 的 `"date"` 改成 `"Y-m-d"`。
- **檔頭與檔尾**：銀行檔案前幾行若是帳號資訊、最後幾行若是合計，請先刪掉，只保留「標題列＋交易列」。

### 3.3 匯入步驟

1. 開 `http://<主機IP>:8081`，選「上傳檔案 (file)」。
2. 上傳 CSV ＋ 對應的 JSON 設定檔。
3. 確認「預設帳戶」：存款選「玉山存款」，信用卡選「玉山信用卡」。JSON 裡的 `default_account` 是帳戶 ID，數字依你的系統而定；在 Firefly III 開啟該帳戶時，網址最後的數字就是 ID。改對後重新下載 JSON，下次就不用再選。
4. 勾選「套用規則」→ 開始匯入。
5. 重複匯入同一期間不會產生重複交易：`duplicate_detection_method: classic` 會比對日期、金額、描述，跳過已存在的交易。

## 4. 每月例行（約 30 分鐘，建議每月 5 日）

1. **匯入**：下載玉山存款與信用卡上個月的 CSV → 匯入（第 3 節）。
2. **清理無分類**：報表 → 選上個月 →「無分類」交易逐筆分類。同一商家出現 2 次以上就補進 [[規則]]。
3. **對帳 (Reconcile)**：在每個資產帳戶頁按「對帳」，Firefly III 的餘額應等於銀行 App 上的實際餘額。對不上，通常是漏了現金交易或匯入重複。
4. **看預算**：預算頁看哪一層超支，只問一個問題：**是意外，還是預算本來就不誠實？** 後者就調整預算金額。
5. **存錢**：發薪後轉帳到「緊急預備金」，分配到各存錢筒。
6. **看帳單**：帳單頁確認本月該付的都已付款，並留意是否有不認得的訂閱。
7. **備份**：`sh scripts/backup.sh`（第 5 節）。

**每年 1 月加做**：檢查訂閱清單（三個月沒用就退訂）、依去年實際支出重設預算比例、更新緊急預備金目標（6 × 每月必要支出）。

## 5. 備份與還原

**Windows PowerShell 版**（在 `firefly-iii` 資料夾執行）：
```powershell
mkdir backup
docker compose exec -T db sh -c 'exec mariadb-dump --single-transaction -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" > /tmp/firefly.sql'
docker cp firefly_iii_db:/tmp/firefly.sql .\backup\firefly.sql
docker cp firefly_iii_core:/var/www/html/storage/upload .\backup\upload
copy .env, .db.env, .importer.env .\backup\
dir backup
```
確認 `backup\firefly.sql` 不是 0 KB。這裡刻意不用 PowerShell 的 `>` 轉向輸出，因為 Windows PowerShell 會把檔案轉成 UTF-16，之後無法匯入。

**macOS / Linux / NAS / Git Bash / WSL 版：**
```sh
sh scripts/backup.sh          # 產生 backups/YYYY-MM-DD/
```

備份資料夾含資料庫、附件與設定檔（**含密碼**）。請另外複製一份到外接硬碟或加密的雲端空間；只放在同一台 NAS 上不算備份。

還原：
```sh
gunzip -c backups/2026-10-06/firefly-db.sql.gz | \
  docker compose exec -T db sh -c 'exec mariadb -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"'
docker compose exec -T app tar -xzf - -C /var/www/html/storage < backups/2026-10-06/firefly-upload.tar.gz
```

> ⚠️ 還原時 `.env` 的 `APP_KEY` 必須與備份當時**相同**，否則加密欄位無法讀取。

## 5.5 換電腦

你的記帳資料存在舊電腦 Docker 的資料庫磁碟區，**不在 GitHub，也不在資料夾裡**。只複製資料夾到新電腦，得到的會是空的 Firefly III。

| 項目 | 搬移方式 | 沒搬的後果 |
|---|---|---|
| 記帳資料（資料庫） | 匯出再匯入（見下） | 全部記錄消失 |
| `.env`、`.db.env`、`.importer.env` | 手動複製，用隨身碟，不要用雲端或寄信；它們被 `.gitignore` 排除，GitHub 上沒有 | 密碼與金鑰遺失 |
| `APP_KEY`（在 `.env` 裡） | 新電腦用**完全相同**的值 | **加密欄位無法讀取，最大的坑** |
| 附件（收據照片） | 匯出再匯入 | 附件消失 |
| Tailscale、防火牆規則、Docker 開機自啟、電源設定 | 在新電腦重做（第 2.6 節） | 手機連不上 |

**步驟：**

1. **舊電腦備份**：照第 5 節的 PowerShell 版備份，確認 `backup\firefly.sql` 有內容。`backup` 資料夾含密碼與全部財務資料，只放在隨身碟，用完刪除或加密保存。
2. **新電腦準備**：安裝 Docker Desktop，下載 `firefly-iii` 資料夾，把備份裡的三個設定檔放進去，**內容不要改**。
3. **先只啟動資料庫並匯入：**
   ```powershell
   docker compose up -d db
   # 等約 1 分鐘
   docker cp .\backup\firefly.sql firefly_iii_db:/tmp/firefly.sql
   docker compose exec -T db sh -c 'exec mariadb -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < /tmp/firefly.sql'
   ```
4. **啟動全部並還原附件：**
   ```powershell
   docker compose up -d
   docker cp .\backup\upload firefly_iii_core:/var/www/html/storage/
   docker compose exec -u root app chown -R www-data:www-data /var/www/html/storage/upload
   ```
5. 開 `http://localhost:8080`，用**原本的帳號密碼**登入，確認帳戶餘額與交易都在。
6. **重設手機連線**：新電腦安裝 Tailscale（同一個帳號），會得到新的 `100.x.y.z`。更新新電腦 `.env` 的 `APP_URL` 與 `.importer.env` 的 `VANITY_URL`，執行 `docker compose up -d --force-recreate`；重做第 2.5 節的防火牆規則；手機刪掉舊主畫面圖示，用新網址重新加入；到 Tailscale 管理頁移除舊電腦。

**注意：**
- 舊電腦先不要關、不要刪 Docker 資料，新電腦用一週確認無誤再清理。
- 匯入工具若提示權杖無效，到 Firefly III 重建個人存取權杖，更新 `.importer.env`，再 `docker compose up -d --force-recreate importer`。
- 把 `APP_KEY` 與資料庫密碼另外存在密碼管理員：這兩樣遺失，備份也無法還原。
- 這份流程尚未在實際換機時驗證，請先在新電腦確認資料正確再處理舊電腦。

## 6. 升級

```sh
sh scripts/backup.sh          # 升級前一定先備份
docker compose pull
docker compose up -d
docker image prune -f
```

升級前先看 [Firefly III 的 Releases](https://github.com/firefly-iii/firefly-iii/releases) 有沒有「breaking change」說明。想更穩定，可以把 `docker-compose.yml` 的 `:latest` 改成固定版本號。

## 7. 常見問題

| 狀況 | 原因／解法 |
|---|---|
| 支出被算兩次 | 繳卡費被記成支出 → 檢查 [[規則]] 群組 1 |
| 匯入後中文亂碼 | CSV 是 Big5 → 見 3.2 節轉成 UTF-8 |
| 匯入失敗 "date" 錯誤 | 民國年或日期格式不符 → 見 3.2 節 |
| 定期交易沒自動產生 | `STATIC_CRON_TOKEN` 不是剛好 32 字元 → `docker compose logs cron` |
| 網頁 HTTP 500，日誌出現 `Unsupported cipher or incorrect key length` | `.env` 的 `APP_KEY` 不是剛好 32 字元（常見：占位字串沒換、多了引號或空格）。檢查長度：`((Select-String -Path .env -Pattern '^APP_KEY=').Line -replace '^APP_KEY=','').Length` 應為 32，修正後 `docker compose up -d --force-recreate app` |
| 手機登入後被導到 localhost | `APP_URL` 仍是 `localhost` → 改成 Tailscale 位址並 `docker compose up -d --force-recreate` |
| 手機連不上，電腦正常 | 防火牆 → 見 2.5 節；確認 Tailscale 已開啟 |
| 匯入工具連不上 | `FIREFLY_III_ACCESS_TOKEN` 空白或過期 → 重建權杖後執行 `docker compose up -d importer` |
