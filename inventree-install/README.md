# 在自己的電腦安裝 InvenTree 1.5.6

用官方的 Docker 安裝方式。腳本會自動下載 **InvenTree 1.5.6** 的官方安裝檔、設定版本與帳號，初始化資料庫並啟動。

## 1. 先安裝 Docker

- **Windows / macOS**：安裝並開啟 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。Windows 安裝時依提示啟用 WSL 2。
- **Linux**：安裝 [Docker Engine 與 Compose 外掛](https://docs.docker.com/engine/install/)。

確認 Docker 已啟動：開終端機輸入 `docker version`，有出現 Server 版本即可。

## 2. 下載這個資料夾

從 GitHub 下載本 repo（分支 `claude/sharp-brahmagupta-tnbukb`），或只下載 `inventree-install/` 內的腳本。

## 3. 執行安裝

**Windows**（在此資料夾開 PowerShell）：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

**macOS / Linux**：

```bash
bash install.sh
```

過程中會問你：管理員帳號、Email、密碼。資料庫密碼會自動隨機產生。

預設安裝到使用者目錄下的 `inventree` 資料夾。可改位置：

```powershell
.\install.ps1 -InstallDir D:\inventree
```

```bash
INSTALL_DIR=/opt/inventree bash install.sh
```

## 4. 開始使用

瀏覽器開啟 <http://localhost>，用剛設定的管理員帳號登入。

接著依 `../inventree-seed/README.md` 匯入 450 個 SKU。API token 可在登入後的使用者設定中建立。

## 常用指令（在安裝資料夾中執行）

| 動作 | 指令 |
|---|---|
| 停止 | `docker compose down` |
| 再次啟動 | `docker compose up -d` |
| 查看紀錄 | `docker compose logs -f inventree-server` |
| 備份資料 | 停止後複製整個 `inventree-data` 資料夾 |

## 常見問題

- **80 埠被占用**（例如已有 IIS 或其他網頁伺服器，啟動時出現 `port is already allocated`）：最簡單是先關掉占用的程式。若必須改用 8080：
  1. `.env`：把 `INVENTREE_SITE_URL` 改成 `"http://localhost:8080"`，並加一行 `INVENTREE_HTTP_PORT=8080`。
  2. `docker-compose.yml`：把 `- ${INVENTREE_HTTP_PORT:-80}:80` 改成 `- ${INVENTREE_HTTP_PORT:-80}:${INVENTREE_HTTP_PORT:-80}`（因為代理伺服器 Caddy 會依 SITE_URL 的埠號監聽，內外埠號要一致）。
  3. 執行 `docker compose up -d`，開 <http://localhost:8080>。
- **腳本說已有 .env 而停止**：表示該資料夾已安裝過。腳本不會覆蓋既有設定；要重裝請換資料夾。
- **安全提醒**：`.env` 內有管理員與資料庫密碼，請勿上傳或分享。此安裝是給本機或內網測試用，若要開放到網際網路，需另外設定網域與 HTTPS。

## 版本說明

- 設計文件原以 1.4.x 撰寫；依你的指示改用 **1.5.6**（2026-10 查得的最新正式版）。已核對 1.5.6 的官方安裝檔，設定項目與 1.4.3 相同。
- 要換版本：Windows 加 `-Version x.y.z`；macOS / Linux 前面加 `VERSION=x.y.z`。
