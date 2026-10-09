# InvenTree 一鍵安裝（Windows PowerShell）
# 下載官方 Docker 安裝檔、設定版本與帳號密碼、初始化資料庫並啟動。
#
# 用法（在 PowerShell 中）：
#   powershell -ExecutionPolicy Bypass -File .\install.ps1
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Version 1.5.6 -InstallDir C:\inventree

param(
    [string]$Version = "1.5.6",
    [string]$InstallDir = "$HOME\inventree",
    [string]$SiteUrl = "http://localhost"
)

$ErrorActionPreference = "Stop"
$base = "https://raw.githubusercontent.com/inventree/InvenTree/$Version/contrib/container"

Write-Host "== InvenTree $Version 安裝 ==" -ForegroundColor Cyan

# 1. 檢查 Docker
try { docker version --format '{{.Server.Version}}' | Out-Null }
catch { throw "找不到執行中的 Docker。請先安裝並啟動 Docker Desktop：https://www.docker.com/products/docker-desktop/" }

# 2. 建立安裝資料夾（已存在且有設定檔時不覆蓋）
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Set-Location $InstallDir
if (Test-Path ".env") {
    throw "$InstallDir 已有 .env，為避免覆蓋既有設定，已停止。若要重裝請換資料夾或手動備份後刪除。"
}

# 3. 下載官方檔案
foreach ($f in @("docker-compose.yml", ".env", "Caddyfile")) {
    Write-Host "下載 $f"
    Invoke-WebRequest -UseBasicParsing -Uri "$base/$f" -OutFile $f
}

# 4. 設定 .env
$adminUser = Read-Host "管理員帳號（例 admin）"
$adminEmail = Read-Host "管理員 Email"
$sec = Read-Host "管理員密碼" -AsSecureString
$adminPass = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
$dbPass = ([guid]::NewGuid().ToString("N"))

# 值會以單引號寫入 .env（Docker Compose 照字面讀取，不展開 $），所以不能含單引號
foreach ($v in @($adminUser, $adminEmail, $adminPass)) {
    if ([string]::IsNullOrEmpty($v) -or $v.Contains("'")) {
        Remove-Item -Force "docker-compose.yml", ".env", "Caddyfile"
        throw "帳號、Email、密碼不可為空，也不可包含單引號 '。請重新執行。"
    }
}

$envText = Get-Content ".env" -Raw
$envText = $envText -replace '(?m)^INVENTREE_TAG=.*$', "INVENTREE_TAG=$Version"
$envText = $envText -replace '(?m)^INVENTREE_SITE_URL=.*$', "INVENTREE_SITE_URL=`"$SiteUrl`""
$envText = $envText -replace '(?m)^INVENTREE_DB_PASSWORD=.*$', "INVENTREE_DB_PASSWORD=$dbPass"
# 用 scriptblock 取代，避免 -replace 把密碼中的 $1、$& 等當成反向參照
$envText = [regex]::Replace($envText, '(?m)^#INVENTREE_ADMIN_USER=.*$', { "INVENTREE_ADMIN_USER='$adminUser'" })
$envText = [regex]::Replace($envText, '(?m)^#INVENTREE_ADMIN_PASSWORD=.*$', { "INVENTREE_ADMIN_PASSWORD='$adminPass'" })
$envText = [regex]::Replace($envText, '(?m)^#INVENTREE_ADMIN_EMAIL=.*$', { "INVENTREE_ADMIN_EMAIL='$adminEmail'" })
[IO.File]::WriteAllText("$InstallDir\.env", $envText)

# 5. 初始化（下載映像、建立資料庫、建立管理員）並啟動
Write-Host "初始化資料庫（第一次需下載映像，約數分鐘）..."
docker compose run --rm inventree-server invoke update
if ($LASTEXITCODE -ne 0) { throw "初始化失敗，請查看上方錯誤訊息。" }
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw "啟動失敗，請查看上方錯誤訊息。" }

Write-Host ""
Write-Host "完成！請用瀏覽器開啟 $SiteUrl ，以剛才的管理員帳號登入。" -ForegroundColor Green
Write-Host "資料存放於：$InstallDir\inventree-data"
Write-Host "停止：在 $InstallDir 執行 docker compose down"
