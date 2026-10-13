# 妮菈穿戴甲正式版：更新到新版本（在「新下載」的 nila-erpnext\production 資料夾中執行）
# 先自動備份，再替換程式（nila_app 與正式版設定），重新建置、升級資料庫結構（migrate）並重新啟動。
# 安裝資料夾中的 .env（密碼）與 nila-config.json（公司、分公司、甲型）不會被改動。資料不會被刪除。
#
# 用法：powershell -ExecutionPolicy Bypass -File .\update-nila.ps1 [-InstallDir C:\Users\你\nila-erpnext]
param(
    [string]$InstallDir = (Join-Path $HOME "nila-erpnext"),
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"
$src = Split-Path $PSScriptRoot -Parent
. (Join-Path $PSScriptRoot "lib/NilaCommon.ps1")
$prodDir = Join-Path $InstallDir "production"
$envPath = Join-Path $prodDir ".env"
if (-not (Test-Path $envPath)) { throw "在 $prodDir 找不到已安裝的正式版。第一次請用 install-nila.ps1 安裝。" }
if ((Resolve-Path $src).Path.TrimEnd('\', '/') -eq (Resolve-Path $InstallDir).Path.TrimEnd('\', '/')) {
    throw "請在「新下載」的 nila-erpnext\production 資料夾中執行，而不是安裝資料夾。"
}
Assert-Docker

$envValues = Get-NilaEnv -Path $envPath
$old = $envValues["NILA_VERSION"]
$new = Get-NilaAppVersion -AppsDir (Join-Path $src "apps")
$port = [int]$envValues["HTTP_PORT"]

Write-Host "== 妮菈穿戴甲正式版更新：$old → $new ==" -ForegroundColor Cyan
Write-Host "將進行：先備份 → 替換 nila_app 與正式版設定檔 → 重新建置 → 升級資料庫結構 → 重新啟動（約 3–10 分鐘，期間無法使用）"
Write-Host ".env 與 nila-config.json 不會被改動。"
$ok = Read-Host "確定執行？(Y/N)"
if ($ok -notmatch '^[Yy]') { Write-Host "已取消，未做任何變更。"; exit 0 }

if (-not $SkipBackup) {
    Write-Host "1/5 先備份…"
    & (Join-Path $prodDir "backup-nila.ps1") -InstallDir $InstallDir
}

Write-Host "2/5 替換程式…"
$appsDest = Join-Path $InstallDir "apps"
if (Test-Path (Join-Path $appsDest "nila_app")) { Remove-Item (Join-Path $appsDest "nila_app") -Recurse -Force }
New-Item -ItemType Directory -Force -Path $appsDest | Out-Null
Copy-Item (Join-Path $src "apps/nila_app") $appsDest -Recurse -Force
foreach ($f in @("docker-compose.yml", "Dockerfile", "nila-config.example.json", "install-nila.ps1", "update-nila.ps1", "backup-nila.ps1", "restore-nila.ps1")) {
    Copy-Item (Join-Path $src "production/$f") $prodDir -Force
}
Copy-Item (Join-Path $src "production/lib/*") (Join-Path $prodDir "lib") -Force
$envValues["NILA_VERSION"] = $new
$ordered = [ordered]@{}
foreach ($k in @("NILA_VERSION", "SITE_NAME", "HTTP_PORT", "DB_PASSWORD", "ADMIN_PASSWORD")) { $ordered[$k] = $envValues[$k] }
Set-NilaEnv -Path $envPath -Values $ordered

Push-Location $prodDir
try {
    Write-Host "3/5 重新建置並啟動…"
    docker compose build
    if ($LASTEXITCODE -ne 0) { throw "建置失敗（資料未受影響）。" }
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw "啟動失敗（資料未受影響）。" }
    $state = Wait-NilaOneShot -Service "create-site"
    if ($state -notmatch '^exited 0') { docker compose logs --tail 40 create-site; throw "啟動後的設定失敗（$state）。" }

    Write-Host "4/5 升級資料庫結構…"
    $site = $envValues["SITE_NAME"]
    docker compose exec -T backend bench --site $site migrate | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "升級資料庫結構失敗。資料在更新前已備份，可用 restore-nila.ps1 還原。" }

    Write-Host "5/5 重新啟動…"
    Restart-NilaAll
    if (-not (Wait-NilaReady -Port $port)) { throw "更新後系統沒有回應。請執行 docker compose ps 與 docker compose logs --tail 50 backend 查看。" }
} finally { Pop-Location }

Write-Host "✓ 已更新到 $new。各電腦開啟後按一次 Ctrl+F5。" -ForegroundColor Green
