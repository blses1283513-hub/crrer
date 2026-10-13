# 妮菈穿戴甲正式版：還原（⚠️ 會用備份的內容取代目前系統的全部資料）
# 用法：
#   powershell -ExecutionPolicy Bypass -File .\restore-nila.ps1 -BackupDir "C:\Users\你\Documents\妮菈備份\20261013_233000"
# 換電腦時：先在新電腦執行 install-nila.ps1 完成安裝，再執行本腳本還原舊電腦的備份。
# 還原後請用「備份當時」的帳號密碼登入（帳號與密碼存在資料庫中，會一起還原）。
param(
    [Parameter(Mandatory = $true)][string]$BackupDir,
    [string]$InstallDir = (Split-Path $PSScriptRoot -Parent),
    [switch]$SkipSafetyBackup
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/NilaCommon.ps1")
$prodDir = Join-Path $InstallDir "production"
if (-not (Test-Path (Join-Path $prodDir "docker-compose.yml"))) { throw "在 $prodDir 找不到正式版，請先執行 install-nila.ps1，或用 -InstallDir 指定安裝位置。" }
if (-not (Test-Path $BackupDir)) { throw "找不到備份資料夾：$BackupDir" }

$files = @(Get-ChildItem $BackupDir -File | Where-Object { $_.Name -match '-(database\.sql\.gz|files\.tar|private-files\.tar|site_config_backup\.json)$' })
$db = @($files | Where-Object { $_.Name -like '*-database.sql.gz' })
if ($db.Count -ne 1) { throw "備份資料夾中必須剛好有一個 *-database.sql.gz（目前 $($db.Count) 個）。請指定單一一份備份的資料夾。" }
$stamps = @($files | ForEach-Object { ($_.Name -split '-')[0] } | Sort-Object -Unique)
if ($stamps.Count -ne 1) { throw "備份資料夾中混有不同時間的檔案：$($stamps -join '、')" }

Assert-Docker
$envValues = Get-NilaEnv -Path (Join-Path $prodDir ".env")
$port = [int]$envValues["HTTP_PORT"]

Write-Host ""
Write-Host "將用以下備份取代目前系統的全部資料：" -ForegroundColor Yellow
$files | ForEach-Object { Write-Host ("  {0}（{1:N1} MB）" -f $_.Name, ($_.Length / 1MB)) }
if (-not $SkipSafetyBackup) { Write-Host "  還原前會先自動備份目前的資料（萬一要反悔可以還原回來）" }
Write-Host "  還原後請用「備份當時」的帳號密碼登入。"
Write-Host ""
$ok = Read-Host "確定要還原？目前的資料會被取代 (輸入 YES 繼續)"
if ($ok -cne "YES") { Write-Host "已取消，未做任何變更。"; exit 0 }

if (-not $SkipSafetyBackup) {
    Write-Host "先備份目前的資料…"
    & (Join-Path $prodDir "backup-nila.ps1") -InstallDir $InstallDir
}

Push-Location $prodDir
try {
    docker compose up -d | Out-Null
    if (-not (Wait-NilaReady -Port $port)) { throw "系統沒有回應，無法還原。請執行 docker compose ps 查看。" }
    Write-Host "1/3 複製備份到系統…"
    docker compose exec -T backend bash -c "rm -rf sites/restore && mkdir -p sites/restore"
    if ($LASTEXITCODE -ne 0) { throw "無法準備還原資料夾。" }
    foreach ($f in $files) {
        docker compose cp $f.FullName "backend:/home/frappe/frappe-bench/sites/restore/$($f.Name)" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "複製 $($f.Name) 失敗。" }
    }
    Write-Host "2/3 還原中（數分鐘）…"
    $out = (docker compose run --rm restore) | Out-String
    Write-Host $out
    docker compose exec -T backend bash -c "rm -rf sites/restore" | Out-Null
    if ($out -notmatch 'NILA_RESTORE_OK') { throw "還原失敗（見上方訊息）。目前的資料已在還原前備份，可再用本腳本還原回去。" }
    Write-Host "3/3 重新啟動…"
    Restart-NilaAll
    if (-not (Wait-NilaReady -Port $port)) { throw "還原後系統沒有回應。請執行 docker compose ps 與 docker compose logs --tail 50 backend 查看。" }
} finally { Pop-Location }

Write-Host ""
Write-Host "✓ 還原完成。請用備份當時的帳號密碼登入：http://localhost:$port" -ForegroundColor Green
