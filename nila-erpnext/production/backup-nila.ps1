# 妮菈穿戴甲正式版：備份（系統不必停止）
# 產生一組完整備份（資料庫、上傳檔案、網站設定），放到「文件\妮菈備份\日期時間」；
# 可同時複製到第二個地方（隨身碟、NAS、雲端硬碟的同步資料夾）——電腦壞了資料才不會一起消失。
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1
#   powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "D:\妮菈備份"
#   每天自動備份（登記 Windows 工作排程器，每天 23:30）：
#   powershell -ExecutionPolicy Bypass -File .\backup-nila.ps1 -CopyTo "D:\妮菈備份" -RegisterDaily
param(
    [string]$InstallDir = (Split-Path $PSScriptRoot -Parent),
    [string]$OutDir = "",
    [string]$CopyTo = "",
    [int]$Keep = 30,
    [switch]$RegisterDaily,
    [string]$At = "23:30"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/NilaCommon.ps1")
if (-not $OutDir) {
    $docs = [Environment]::GetFolderPath("MyDocuments")
    if (-not $docs) { $docs = Join-Path $HOME "Documents" }
    $OutDir = Join-Path $docs "妮菈備份"
}
$prodDir = Join-Path $InstallDir "production"
if (-not (Test-Path (Join-Path $prodDir "docker-compose.yml"))) { throw "在 $prodDir 找不到正式版，請用 -InstallDir 指定安裝位置。" }

if ($RegisterDaily) {
    $self = Join-Path $prodDir "backup-nila.ps1"
    $tr = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$self`" -InstallDir `"$InstallDir`" -OutDir `"$OutDir`""
    if ($CopyTo) { $tr += " -CopyTo `"$CopyTo`"" }
    schtasks /Create /F /SC DAILY /ST $At /TN "NilaBackup" /TR $tr | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "登記排程失敗（可能需要以系統管理員身分執行）。" }
    Write-Host "✓ 已登記每天 $At 自動備份（工作排程器：NilaBackup）。電腦與 Docker 須在該時間開著。" -ForegroundColor Green
    exit 0
}

Assert-Docker
$site = (Get-NilaEnv -Path (Join-Path $prodDir ".env"))["SITE_NAME"]
if (-not $site) { $site = "nila" }
$bdir = "sites/$site/private/backups"

Push-Location $prodDir
try {
    Write-Host "1/3 產生備份…"
    docker compose exec -T backend bench --site $site backup --with-files | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "備份失敗。請確認系統正在執行（docker compose ps）。" }

    # 最新一組：同一個時間戳記開頭的檔案
    $names = @(docker compose exec -T backend ls -1t $bdir)
    $latest = $names | Where-Object { $_ -match '^(\d{8}_\d{6})-' } | Select-Object -First 1
    if (-not $latest) { throw "找不到剛產生的備份檔。" }
    $stamp = ([regex]::Match($latest, '^(\d{8}_\d{6})-')).Groups[1].Value
    $set = @($names | Where-Object { $_.StartsWith("$stamp-") })
    if (-not ($set | Where-Object { $_ -like '*-database.sql.gz' })) { throw "備份不完整：找不到資料庫檔。" }

    Write-Host "2/3 複製到 $OutDir …"
    $dest = Join-Path $OutDir $stamp
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    foreach ($n in $set) {
        docker compose cp "backend:/home/frappe/frappe-bench/$bdir/$n" (Join-Path $dest $n) | Out-Null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $dest $n))) { throw "複製 $n 失敗。" }
    }
    Copy-Item (Join-Path $prodDir "nila-config.json") $dest -ErrorAction SilentlyContinue

    # 容器內只保留最近 3 天的備份，避免佔滿空間（完整的歷史在電腦的備份資料夾）
    docker compose exec -T backend find $bdir -type f -mtime +3 -delete | Out-Null
} finally { Pop-Location }

function Remove-OldSets([string]$root) {
    $sets = @(Get-ChildItem $root -Directory | Where-Object { $_.Name -match '^\d{8}_\d{6}$' } | Sort-Object Name -Descending)
    if ($sets.Count -gt $Keep) { $sets[$Keep..($sets.Count - 1)] | ForEach-Object { Remove-Item $_.FullName -Recurse -Force } }
}
Remove-OldSets $OutDir

if ($CopyTo) {
    Write-Host "3/3 複製到第二個地方：$CopyTo …"
    New-Item -ItemType Directory -Force -Path $CopyTo | Out-Null
    Copy-Item $dest $CopyTo -Recurse -Force
    Remove-OldSets $CopyTo
} else {
    Write-Host "3/3 未指定第二個地方（-CopyTo）。建議同時備份到隨身碟、NAS 或雲端硬碟的同步資料夾。" -ForegroundColor Yellow
}

$size = (Get-ChildItem $dest | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("✓ 備份完成：{0}（{1:N1} MB，保留最近 {2} 份）" -f $dest, $size, $Keep) -ForegroundColor Green
