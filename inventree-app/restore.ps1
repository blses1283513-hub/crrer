# 庫存管理系統：還原備份（新主機電腦用）
# 把 backup.ps1 產生的 zip 還原到「已安裝並完成 setup-server.ps1 的新主機」：
# 資料庫（帳號、權限、設定、庫存、異動紀錄）與上傳的檔案。
# 不會還原 .env：新主機的網址、IP、資料庫密碼以新主機自己的設定為準。
#
# 注意：還原會【覆蓋】新主機資料庫中的所有資料。執行前會列出變更並要求確認。
# 用法：powershell -ExecutionPolicy Bypass -File .\restore.ps1 -BackupZip "D:\inventree-backup-20261010-020001.zip"
param(
    [Parameter(Mandatory = $true)][string]$BackupZip,
    [string]$InstallDir = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $BackupZip)) { throw "找不到備份檔：$BackupZip" }
Set-Location $InstallDir

# ---------- 讀取新主機的 .env ----------
$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.*)$') { $envVars[$Matches[1]] = $Matches[2].Trim().Trim('"', "'") }
}
$dbUser = $envVars["INVENTREE_DB_USER"]; $dbName = $envVars["INVENTREE_DB_NAME"]
$ext = $envVars["INVENTREE_EXT_VOLUME"]
$dataDir = if ([IO.Path]::IsPathRooted($ext)) { $ext } else { Join-Path $InstallDir ($ext -replace '^\./', '') }
$newTag = $envVars["INVENTREE_TAG"]
if (-not $dbUser -or -not $dbName) { throw ".env 中找不到資料庫設定。請確認這裡是已安裝的 InvenTree 資料夾。" }

# ---------- 解開備份並檢查 ----------
$stage = Join-Path $env:TEMP ("inventree-restore-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
Expand-Archive -Path $BackupZip -DestinationPath $stage -Force
$dump = Get-ChildItem $stage -Filter "db-*.dump" | Select-Object -First 1
if (-not $dump) { Remove-Item $stage -Recurse -Force; throw "備份檔中找不到資料庫檔（db-*.dump）。這不是 backup.ps1 產生的備份。" }

$oldTag = $null
$oldEnv = Join-Path $stage ".env"
if (Test-Path $oldEnv) {
    $m = Select-String -Path $oldEnv -Pattern '^INVENTREE_TAG=(.*)$' | Select-Object -First 1
    if ($m) { $oldTag = $m.Matches[0].Groups[1].Value.Trim('"', "'") }
}
Write-Host "備份檔：$BackupZip"
Write-Host "  備份時的版本：$oldTag　　新主機版本：$newTag"
if ($oldTag -and $newTag -and $oldTag -ne $newTag) {
    Write-Host "⚠ 版本不同！請先把新主機 .env 的 INVENTREE_TAG 改成 $oldTag（並執行 docker compose up -d）再還原；資料庫不能從新版還原回舊版。" -ForegroundColor Yellow
    $force = Read-Host "仍要繼續？(Y/N)"
    if ($force -notmatch '^[Yy]') { Remove-Item $stage -Recurse -Force; Write-Host "已取消，未做任何變更。"; exit 0 }
}

Write-Host ""
Write-Host "將進行以下變更：" -ForegroundColor Yellow
Write-Host "  1. 暫停 inventree-server / worker / proxy（還原期間無法使用）"
Write-Host "  2. 以備份覆蓋【新主機資料庫的全部資料】（含目前的帳號、權限、庫存）"
Write-Host "  3. 還原上傳的檔案（media）與通知的已讀紀錄（備份中沒有的話，舊的通知紀錄會改名保留，服務重新開始記錄）"
Write-Host "  4. 重新啟動系統"
Write-Host "  不會變更：.env、IP 與網址設定、App 檔案。"
$ok = Read-Host "確定覆蓋新主機的資料？(Y/N)"
if ($ok -notmatch '^[Yy]') { Remove-Item $stage -Recurse -Force; Write-Host "已取消，未做任何變更。"; exit 0 }

# ---------- 還原 ----------
Write-Host "1/4 暫停服務…"
docker compose stop inventree-server inventree-worker inventree-proxy
if ($LASTEXITCODE -ne 0) { throw "無法暫停服務。" }
cmd /c "docker compose stop inventree-notifier >nul 2>&1"   # 舊版安裝沒有這個服務，找不到時略過
docker compose up -d inventree-db inventree-cache | Out-Null

Write-Host "2/4 還原資料庫…"
$backupsDir = Join-Path $dataDir "backups"
New-Item -ItemType Directory -Force -Path $backupsDir | Out-Null
Copy-Item $dump.FullName (Join-Path $backupsDir $dump.Name) -Force
docker compose exec -T inventree-db sh -c "pg_restore -U '$dbUser' -d '$dbName' --clean --if-exists --no-owner --no-privileges /var/lib/postgresql/data/backups/$($dump.Name)"
# pg_restore 遇到可忽略的警告（例如物件不存在）也會回傳非 0，所以只提示不中止
if ($LASTEXITCODE -ne 0) { Write-Host "⚠ pg_restore 回報了警告或錯誤（代碼 $LASTEXITCODE）。若啟動後資料正常可忽略；否則請把上方訊息貼給協助的人。" -ForegroundColor Yellow }

Write-Host "3/4 還原上傳的檔案…"
$media = Join-Path $stage "media"
if (Test-Path $media) {
    New-Item -ItemType Directory -Force -Path (Join-Path $dataDir "media") | Out-Null
    Copy-Item (Join-Path $media "*") (Join-Path $dataDir "media") -Recurse -Force
}

Write-Host "通知的已讀紀錄…"
$notifyDir = Join-Path $dataDir "notifier"
New-Item -ItemType Directory -Force -Path $notifyDir | Out-Null
$notifyTarget = Join-Path $notifyDir "state.json"
$notifyBackup = Join-Path $stage "notifier-state\state.json"
if (Test-Path $notifyBackup) {
    Copy-Item $notifyBackup $notifyTarget -Force
} elseif (Test-Path $notifyTarget) {
    # 備份沒有通知紀錄：現有的紀錄與還原後的資料庫不一致，改名保留，讓通知服務重新開始（不會產生歷史通知）
    Move-Item $notifyTarget "$notifyTarget.old-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
}

Write-Host "4/4 重新啟動系統…"
docker compose up -d
if ($LASTEXITCODE -ne 0) { throw "啟動失敗，請執行 docker compose logs --tail 50 inventree-server 查看原因。" }
Remove-Item $stage -Recurse -Force

Write-Host ""
Write-Host "還原完成。請用【舊主機的帳號與密碼】登入（新主機安裝時建立的管理員帳號已被備份內容取代）。" -ForegroundColor Green
Write-Host "登入後請檢查：庫存數量、異動紀錄、群組與權限是否與舊主機一致。"
