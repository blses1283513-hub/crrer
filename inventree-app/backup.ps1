# 庫存管理系統：備份（主機電腦用）
# 備份資料庫（帳號、權限、語言與系統設定、庫存、異動紀錄）、上傳的檔案、以及所有設定檔，
# 打包成一個 zip。系統不需要停止。
# 用法：powershell -ExecutionPolicy Bypass -File backup.ps1
param(
    [string]$InstallDir = $PSScriptRoot,
    [string]$OutDir = (Join-Path ([Environment]::GetFolderPath("MyDocuments")) "InvenTree備份")
)

$ErrorActionPreference = "Stop"
Set-Location $InstallDir

# 從 .env 讀取資料庫名稱、帳號與資料夾
$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.*)$') { $envVars[$Matches[1]] = $Matches[2].Trim().Trim('"', "'") }
}
$dbUser = $envVars["INVENTREE_DB_USER"]
$dbName = $envVars["INVENTREE_DB_NAME"]
$ext = $envVars["INVENTREE_EXT_VOLUME"]
$dataDir = if ([IO.Path]::IsPathRooted($ext)) { $ext } else { Join-Path $InstallDir ($ext -replace '^\./', '') }
if (-not $dbUser -or -not $dbName) { throw ".env 中找不到資料庫設定（INVENTREE_DB_USER / INVENTREE_DB_NAME）。" }

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$dumpName = "db-$ts.dump"

Write-Host "1/3 匯出資料庫…"
docker compose exec -T inventree-db sh -c "mkdir -p /var/lib/postgresql/data/backups && pg_dump -U '$dbUser' -d '$dbName' -Fc -f /var/lib/postgresql/data/backups/$dumpName"
if ($LASTEXITCODE -ne 0) { throw "資料庫匯出失敗，請確認系統正在執行（docker compose ps）。" }
$dump = Join-Path $dataDir "backups\$dumpName"

Write-Host "2/3 收集設定檔與上傳檔案…"
$stage = Join-Path $env:TEMP "inventree-backup-$ts"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Move-Item $dump (Join-Path $stage $dumpName)
foreach ($f in @(".env", "docker-compose.yml", "docker-compose.override.yml", "Caddyfile", "Caddyfile.app", "start-inventree.ps1", "backup.ps1")) {
    if (Test-Path $f) { Copy-Item $f $stage }
}
if (Test-Path "app") { Copy-Item "app" $stage -Recurse }
$media = Join-Path $dataDir "media"
if (Test-Path $media) { Copy-Item $media (Join-Path $stage "media") -Recurse }
# 通知服務：已讀紀錄與設定
$notifyState = Join-Path $dataDir "notifier\state.json"
if (Test-Path $notifyState) {
    New-Item -ItemType Directory -Force -Path (Join-Path $stage "notifier-state") | Out-Null
    Copy-Item $notifyState (Join-Path $stage "notifier-state\state.json")
}
if (Test-Path "notifier") { Copy-Item "notifier" (Join-Path $stage "notifier") -Recurse }

Write-Host "3/3 壓縮…"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$zip = Join-Path $OutDir "inventree-backup-$ts.zip"
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip
Remove-Item $stage -Recurse -Force

Write-Host ""
Write-Host "備份完成：$zip" -ForegroundColor Green
Write-Host "注意：備份內含 .env（資料庫與管理員密碼），請妥善保管，不要分享。" -ForegroundColor Yellow
