# 妮菈穿戴甲正式版：還原演練（建議每個月一次；正式資料完全不受影響，系統可以照常使用）
# 把一份備份還原到「臨時網站」，確認備份檔完整、能還原、資料數量合理，再刪除臨時網站。
# 這樣在真的需要還原之前，就知道備份是好的。
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File .\drill-nila.ps1                        演練最近一次的備份
#   powershell -ExecutionPolicy Bypass -File .\drill-nila.ps1 -BackupDir "G:\我的雲端硬碟\妮菈備份\20261013_233000"
#   （演練雲端資料夾裡的那一份，可以同時確認雲端的備份也是好的）
param(
    [string]$BackupDir = "",
    [string]$InstallDir = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/NilaCommon.ps1")
$prodDir = Join-Path $InstallDir "production"
if (-not (Test-Path (Join-Path $prodDir "docker-compose.yml"))) { throw "在 $prodDir 找不到正式版，請用 -InstallDir 指定安裝位置。" }

if (-not $BackupDir) {
    $state = Join-Path $InstallDir "last-backup.json"
    if (Test-Path $state) { $b = Get-Content $state -Raw -Encoding UTF8 | ConvertFrom-Json; if ($b.ok) { $BackupDir = $b.dir } }
    if (-not $BackupDir) { throw "找不到最近的備份，請用 -BackupDir 指定一份備份的資料夾。" }
}
if (-not (Test-Path $BackupDir)) { throw "找不到備份資料夾：$BackupDir" }
$files = @(Get-ChildItem $BackupDir -File | Where-Object { $_.Name -match '-(database\.sql\.gz|files\.tar|private-files\.tar|site_config_backup\.json)$' })
if (@($files | Where-Object { $_.Name -like '*-database.sql.gz' }).Count -ne 1) { throw "備份資料夾中必須剛好有一個 *-database.sql.gz：$BackupDir" }

Assert-Docker
$site = (Get-NilaEnv -Path (Join-Path $prodDir ".env"))["SITE_NAME"]
if (-not $site) { $site = "nila" }

function Get-Report([string]$text) {
    $line = ($text -split "`n" | Where-Object { $_ -like 'NILA_DRILL_REPORT *' } | Select-Object -Last 1)
    if (-not $line) { return $null }
    return ($line.Substring(18) | ConvertFrom-Json)
}

Write-Host "== 還原演練：$BackupDir ==" -ForegroundColor Cyan
Write-Host "（正式資料不受影響；約需 3–10 分鐘）"
$started = Get-Date
Push-Location $prodDir
try {
    docker compose exec -T backend bash -c "rm -rf sites/drill-restore && mkdir -p sites/drill-restore"
    if ($LASTEXITCODE -ne 0) { throw "系統沒有在執行。請先執行 check-nila.ps1 -Fix。" }
    foreach ($f in $files) {
        docker compose cp $f.FullName "backend:/home/frappe/frappe-bench/sites/drill-restore/$($f.Name)" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "複製 $($f.Name) 失敗。" }
    }
    $out = (docker compose run --rm drill) | Out-String
    $live = (docker compose exec -T backend bench --site $site execute nila_app.setup.drill.report) | Out-String
} finally { Pop-Location }

$ok = $out -match 'NILA_DRILL_OK'
$r = Get-Report $out
$now = Get-Report $live
if ($ok -and $r) {
    $rows = @(
        @("系統版本", "version"), @("款式", "styles"), @("規格", "variants"), @("會員", "members"), @("帳號", "users"),
        @("門市銷售", "store_sales"), @("銷售訂單", "sales_orders"), @("庫存異動", "stock_entries"), @("全公司庫存（件）", "stock_qty"),
        @("最後一筆銷售日期", "last_sale"), @("最後一筆庫存異動", "last_stock"))
    Write-Host ""
    Write-Host ("{0,-18}{1,-22}{2}" -f "", "備份還原後", "目前系統")
    foreach ($x in $rows) { Write-Host ("{0,-18}{1,-22}{2}" -f $x[0], $r.($x[1]), $(if ($now) { $now.($x[1]) } else { "" })) }
    Write-Host "（備份之後才新增的資料，目前系統會比較多，這是正常的）"
    if (-not $r.secrets_ok) { Write-Host "! 已儲存的 SHOPLINE 金鑰在還原後解不開：備份缺少網站設定檔（*-site_config_backup.json），還原後要重新輸入金鑰" -ForegroundColor Yellow }
}

$minutes = [math]::Round(((Get-Date) - $started).TotalMinutes, 1)
$result = [ordered]@{ ok = [bool]($ok -and $r); time = (Get-Date -Format "yyyy-MM-dd HH:mm:ss"); backup = $BackupDir; minutes = $minutes }
if (-not $result.ok) { $result.error = (($out -split "`n" | Where-Object { $_ -match 'NILA_DRILL_ERROR|Error|錯誤' } | Select-Object -Last 3) -join " ") }
Save-NilaJson -Path (Join-Path $InstallDir "last-drill.json") -Value $result
if ($result.ok) {
    Write-Host ""
    Write-Host "✓ 還原演練成功（$minutes 分鐘）：這份備份可以正常還原，臨時網站已刪除。" -ForegroundColor Green
} else {
    Write-Host $out
    throw "還原演練失敗：這份備份可能有問題。請換一份較新的備份再演練，並立即執行 backup-nila.ps1 重新備份。"
}
