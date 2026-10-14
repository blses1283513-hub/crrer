# 妮菈穿戴甲：ERPNext 16 正式版安裝（Windows PowerShell）
# 建立正式版：官方 ERPNext 16 ＋ 妮菈客製功能（nila_app）；公司、總公司與分公司倉庫、甲型、尺寸依 nila-config.json 建立。
# 只供區網內使用（http://電腦IP:埠號），不對外開放。資料與試用版、InvenTree 完全分開。
#
# 用法（在下載的 nila-erpnext\production 資料夾中）：
#   powershell -ExecutionPolicy Bypass -File .\install-nila.ps1
#   powershell -ExecutionPolicy Bypass -File .\install-nila.ps1 -InstallDir D:\nila-erpnext -Port 8091
# 第一次執行時，若安裝資料夾還沒有 nila-config.json，會先放一份範本並停下來，請確認公司、分公司、甲型後再執行一次。
# 中途失敗時直接再執行一次即可（沿用已設定的密碼，已建立的資料不會重複）。
param(
    [string]$InstallDir = (Join-Path $HOME "nila-erpnext"),
    [int]$Port = 8090
)

$ErrorActionPreference = "Stop"
$src = Split-Path $PSScriptRoot -Parent          # 下載的 nila-erpnext 資料夾
. (Join-Path $PSScriptRoot "lib/NilaCommon.ps1")

Write-Host "== 妮菈穿戴甲：ERPNext 16 正式版安裝 ==" -ForegroundColor Cyan

# ---------- 檢查 ----------
foreach ($f in @("production/docker-compose.yml", "production/Dockerfile", "production/nila-config.example.json", "apps/nila_app/nila_app/hooks.py")) {
    if (-not (Test-Path (Join-Path $src $f))) { throw "缺少 $f，請下載完整的 nila-erpnext 資料夾。" }
}
Assert-Docker
$prodDir = Join-Path $InstallDir "production"
$envPath = Join-Path $prodDir ".env"
$cfgPath = Join-Path $prodDir "nila-config.json"
$resume = Test-Path $envPath
$version = Get-NilaAppVersion -AppsDir (Join-Path $src "apps")

# 設定檔：第一次先放範本並停下，讓使用者確認公司、分公司、甲型（甲型縮寫是料號的一部分，上線後不能改）
New-Item -ItemType Directory -Force -Path $prodDir | Out-Null
if (-not (Test-Path $cfgPath)) {
    Copy-Item (Join-Path $src "production/nila-config.example.json") $cfgPath
    Write-Host ""
    Write-Host "已放置設定檔：$cfgPath" -ForegroundColor Yellow
    Write-Host "請用記事本打開，確認公司名稱、總公司與分公司名稱、甲型與縮寫（2–3 個大寫英文字母），存檔後再執行一次本腳本。"
    Write-Host "⚠ 甲型縮寫會成為料號的一部分（例：0001-LT-XS），開始使用後就不能修改。" -ForegroundColor Yellow
    exit 0
}
try { $cfg = [IO.File]::ReadAllText($cfgPath) | ConvertFrom-Json } catch { throw "$cfgPath 格式錯誤（必須是 JSON）：$($_.Exception.Message)" }
if (-not $cfg.company_name -or -not $cfg.shapes) { throw "$cfgPath 缺少 company_name 或 shapes。" }

if (-not $resume) {
    $busy = $false
    try { $busy = [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) } catch { }
    if ($busy) { throw "埠 $Port 已被其他程式使用。請改用其他埠重新執行，例如：-Port 8091" }
}
$sysDrive = if ($env:SystemDrive) { $env:SystemDrive.TrimEnd(":") } else { (Get-Location).Drive.Name }
$drive = Get-PSDrive $sysDrive
if ($drive.Free -lt 15GB) { Write-Host ("⚠ {0} 槽只剩 {1:N1} GB，ERPNext 映像約 7 GB，建議至少 15 GB。" -f $drive.Name, ($drive.Free / 1GB)) -ForegroundColor Yellow }

# ---------- 密碼 ----------
if (-not $resume) {
    Write-Host ""
    Write-Host "請設定最高管理員（Administrator）的密碼：至少 10 個字元，不可包含單引號 '。這是正式版，請使用不易猜到的密碼並妥善保存。"
    $p1 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host "管理員密碼" -AsSecureString)))
    $p2 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host "再輸入一次" -AsSecureString)))
    if ($p1 -ne $p2) { throw "兩次輸入的密碼不同，請重新執行。" }
    if ($p1.Length -lt 10 -or $p1.Contains("'")) { throw "密碼至少 10 個字元，且不可包含單引號 '。請重新執行。" }
}

# ---------- 列出變更，等待確認 ----------
Write-Host ""
Write-Host "將進行以下動作（安裝位置：$InstallDir）：" -ForegroundColor Yellow
if ($resume) { Write-Host "  · 偵測到先前的安裝設定，沿用原本的密碼與埠號，從中斷處繼續" }
else { Write-Host "  1. 寫入 .env（隨機產生的資料庫密碼、管理員密碼、埠號 $Port）" }
Write-Host "  2. 複製正式版檔案與妮菈客製功能（nila_app $version）"
Write-Host "  3. 建置映像檔（第一次需下載約 1.4 GB 的 ERPNext，約 5–20 分鐘）並啟動；建立網站約 3–5 分鐘"
Write-Host "  4. 依設定檔建立："
Write-Host "       公司：$($cfg.company_name)（縮寫 $($cfg.company_abbr)）"
Write-Host "       倉庫：$($cfg.hq)、$((@($cfg.branches)) -join '、')、在途"
Write-Host "       甲型：$((@($cfg.shapes) | ForEach-Object { "$($_.name)($($_.abbr))" }) -join '、')"
Write-Host "       台灣、新台幣、台北時區、繁體中文"
Write-Host "  5. 完成後從 .env 移除管理員密碼（網站已保存，不需要留在檔案中）"
Write-Host ""
$ok = Read-Host "確定執行？(Y/N)"
if ($ok -notmatch '^[Yy]') { Write-Host "已取消，未做任何變更。"; exit 0 }

# ---------- 1–2. 檔案 ----------
if (-not $resume) {
    Set-NilaEnv -Path $envPath -Values ([ordered]@{
        NILA_VERSION = $version; SITE_NAME = "nila"; HTTP_PORT = "$Port"
        DB_PASSWORD = [guid]::NewGuid().ToString("N"); ADMIN_PASSWORD = $p1
    })
    $p1 = $null; $p2 = $null
}
$envValues = Get-NilaEnv -Path $envPath
$Port = [int]$envValues["HTTP_PORT"]
$appsDest = Join-Path $InstallDir "apps"
$sameDir = (Resolve-Path $src).Path.TrimEnd('\', '/') -eq (Resolve-Path $InstallDir).Path.TrimEnd('\', '/')
if (-not $sameDir) {
    # 只替換程式（nila_app），安裝資料夾中的 .env 與 nila-config.json 不動
    if (Test-Path (Join-Path $appsDest "nila_app")) { Remove-Item (Join-Path $appsDest "nila_app") -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $appsDest | Out-Null
    Copy-Item (Join-Path $src "apps/nila_app") $appsDest -Recurse -Force
}
foreach ($f in $script:NilaProductionFiles) {
    $from = Join-Path $src "production/$f"
    if ((Test-Path $from) -and ((Resolve-Path $from).Path -ne (Join-Path (Resolve-Path $prodDir).Path $f))) { Copy-Item $from $prodDir -Force }
}
New-Item -ItemType Directory -Force -Path (Join-Path $prodDir "lib") | Out-Null
Copy-Item (Join-Path $src "production/lib/*") (Join-Path $prodDir "lib") -Force -ErrorAction SilentlyContinue
Write-Host "✓ 設定與檔案已放置"

# ---------- 3–4. 建置、啟動、建立網站 ----------
Push-Location $prodDir
try {
    Write-Host "建置映像檔（第一次會下載 ERPNext，請耐心等候）…"
    docker compose build
    if ($LASTEXITCODE -ne 0) { throw "建置失敗。若訊息含「429 Too Many Requests」，代表 Docker Hub 暫時限制下載次數，等 30 分鐘後再執行一次即可。" }
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw "啟動失敗，請把上方訊息交給協助的人。修正後可直接再執行本腳本。" }

    Write-Host "建立網站與基本設定…"
    $state = Wait-NilaOneShot -Service "create-site"
    $log = (docker compose logs --no-color create-site) | Out-String
    if ($state -notmatch '^exited 0' -or $log -notmatch 'NILA_SITE_READY') {
        docker compose logs --tail 40 create-site
        throw "建立網站失敗（$state）。請把上方訊息交給協助的人；修正後可直接再執行本腳本。"
    }
    if (-not (Wait-NilaReady -Port $Port)) { throw "系統沒有回應。請執行 docker compose ps 與 docker compose logs --tail 50 backend 查看。" }
    Write-Host "✓ 系統已啟動，基本設定完成"
} finally { Pop-Location }

# ---------- 5. 移除 .env 中的管理員密碼 ----------
$envValues = Get-NilaEnv -Path $envPath
if ($envValues["ADMIN_PASSWORD"]) {
    $envValues["ADMIN_PASSWORD"] = ""
    $ordered = [ordered]@{}
    foreach ($k in @("NILA_VERSION", "SITE_NAME", "HTTP_PORT", "DB_PASSWORD", "ADMIN_PASSWORD")) { $ordered[$k] = $envValues[$k] }
    Set-NilaEnv -Path $envPath -Values $ordered
    Write-Host "✓ 已從 .env 移除管理員密碼"
}

$ip = Get-NilaLanIp
Write-Host ""
Write-Host "完成！" -ForegroundColor Green
Write-Host "  本機：http://localhost:$Port"
Write-Host "  同一個區網的其他電腦：http://${ip}:$Port（需先開放防火牆，見 README）"
Write-Host "  帳號：Administrator　密碼：你剛才設定的密碼"
Write-Host ""
Write-Host "接下來（只要做一次，見 README「上線設定」）：" -ForegroundColor Cyan
Write-Host "  1. 每天自動備份（含雲端資料夾）：powershell -ExecutionPolicy Bypass -File `"$prodDir\backup-nila.ps1`" -CopyTo `"雲端資料夾\妮菈備份`" -RegisterDaily"
Write-Host "  2. 登入後自動啟動（以系統管理員身分執行）：powershell -ExecutionPolicy Bypass -File `"$prodDir\check-nila.ps1`" -RegisterStartup"
Write-Host "  3. 隨時檢查系統：powershell -ExecutionPolicy Bypass -File `"$prodDir\check-nila.ps1`"" 
Write-Host "  ⚠ .env 內有資料庫密碼，請勿分享；它不在備份中，但還原時不需要。"
try { Start-Process "http://localhost:$Port" } catch { }
