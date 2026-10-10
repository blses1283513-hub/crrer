# 庫存管理系統：加入「管理看板」儀表板小工具＋介面翻譯修正（給已經安裝好的主機用，不需重新下載整個專案）
#
# 會做的事（執行前會列出並等你確認）：
#   1. 備份 .env、Caddyfile.app、中文操作助手
#   2. .env：INVENTREE_PLUGINS_ENABLED=True、INVENTREE_PLUGINS_MANDATORY 加入 mgmt-dashboard（每次啟動自動啟用外掛）
#   3. 放置管理看板外掛到 inventree-data\plugins\mgmt_dashboard（含公司清單 companies.json）
#   4. 更新 Caddyfile.app（外掛 JS 不快取）與中文操作助手（儀表板翻譯修正）
#   5. 重新啟動系統容器，並在 InvenTree 內開啟「介面整合」、複製外掛 JS
# 資料庫與庫存資料不會被動到。可以重複執行。
#
# 用法：powershell -ExecutionPolicy Bypass -File .\enable-dashboard.ps1 [-InstallDir C:\Users\你\inventree]
param(
    [string]$InstallDir = (Join-Path $HOME "inventree"),
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
. (Join-Path $here "lib\EnvFile.ps1")
. (Join-Path $here "lib\DashboardPlugin.ps1")

Write-Host "== 管理看板與介面翻譯修正 ==" -ForegroundColor Cyan

# ---------- 檢查 ----------
foreach ($f in @("docker-compose.yml", ".env", "docker-compose.override.yml")) {
    if (-not (Test-Path (Join-Path $InstallDir $f))) { throw "在 $InstallDir 找不到 $f。請先完成 setup-server.ps1（完整安裝），或用 -InstallDir 指定位置。" }
}
if (-not (Select-String -Path (Join-Path $InstallDir "docker-compose.override.yml") -Pattern '\[inventree-app\]' -Quiet)) {
    throw "docker-compose.override.yml 不是本工具建立的，請先執行 setup-server.ps1。"
}
$pluginSrc = Join-Path $here "plugins\mgmt_dashboard"
$caddySrc = Join-Path $here "Caddyfile.app"
foreach ($p in @((Join-Path $pluginSrc "__init__.py"), (Join-Path $pluginSrc "static\mgmt_dashboard.js"), $caddySrc)) {
    if (-not (Test-Path $p)) { throw "缺少 $p，請確認下載的檔案完整。" }
}
$helperSrc = @((Join-Path $here "inventree-ui-helper.user.js"), (Join-Path $here "..\inventree-ui-helper\inventree-ui-helper.user.js")) |
    Where-Object { Test-Path $_ } | Select-Object -First 1

# 公司清單：通知服務設定（已依匯入設定產生）優先，其次匯入設定
$companySrc = @((Join-Path $InstallDir "notifier\config.json"), (Join-Path $here "..\inventree-seed\config.json"), (Join-Path $here "..\inventree-seed\config.example.json")) |
    Where-Object { Test-Path $_ } | Select-Object -First 1
$companiesJson = if ($companySrc) { New-DashboardCompaniesJson -ConfigPath $companySrc } else { $null }

$envPath = Join-Path $InstallDir ".env"
$envValues = Get-EnvValues -Path $envPath
$settings = Get-DashboardEnvSettings -Current $envValues
$ext = $envValues["INVENTREE_EXT_VOLUME"]
if (-not $ext) { $ext = "./inventree-data" }
$dataDir = if ([IO.Path]::IsPathRooted($ext)) { $ext } else { Join-Path $InstallDir ($ext -replace '^\./', '') }
$ts = Get-Date -Format "yyyyMMdd-HHmmss"

# ---------- 列出變更，等待確認 ----------
Write-Host ""
Write-Host "將進行以下變更（安裝位置：$InstallDir）：" -ForegroundColor Yellow
Write-Host "  1. 備份 .env、Caddyfile.app、app\inventree-ui-helper.user.js（檔名加上 .bak-$ts）"
Write-Host "  2. .env 設定："
$settings.GetEnumerator() | ForEach-Object { Write-Host "       $($_.Key)=$($_.Value)" }
Write-Host "  3. 放置管理看板外掛：$dataDir\plugins\$DashboardDirName"
if ($companySrc) {
    Write-Host "       公司清單取自 $companySrc ："
    foreach ($c in @(($companiesJson | ConvertFrom-Json).companies)) { Write-Host "         $($c.name)　料號前綴 $($c.code)-" }
} else { Write-Host "       找不到公司設定，使用預設的 A/B/C 公司" }
Write-Host "  4. 更新 Caddyfile.app$(if ($helperSrc) { '、中文操作助手（儀表板翻譯修正）' } else { '（找不到中文操作助手檔案，略過）' })"
Write-Host "  5. 重新啟動系統容器（約 1–3 分鐘，期間無法使用；資料不受影響），並在 InvenTree 開啟「介面整合」"
Write-Host ""
if (-not $Yes) {
    $ok = Read-Host "確定執行？(Y/N)"
    if ($ok -notmatch '^[Yy]') { Write-Host "已取消，未做任何變更。"; exit 0 }
}

# ---------- 1. 備份 ----------
$appHelper = Join-Path $InstallDir "app\inventree-ui-helper.user.js"
foreach ($f in @($envPath, (Join-Path $InstallDir "Caddyfile.app"), $appHelper)) {
    if (Test-Path $f) { Copy-Item $f "$f.bak-$ts" }
}
Write-Host "✓ 已備份（.bak-$ts）"

# ---------- 2–4. 設定與檔案 ----------
Set-EnvFile -Path $envPath -Settings $settings
$dest = Install-DashboardPluginFiles -SourceDir $pluginSrc -DataDir $dataDir -CompaniesJson $companiesJson
Copy-Item $caddySrc (Join-Path $InstallDir "Caddyfile.app") -Force
if ($helperSrc) { Copy-Item $helperSrc $appHelper -Force }
Write-Host "✓ 設定與檔案已更新（外掛：$dest）"

# ---------- 5. 重新啟動與啟用 ----------
Write-Host "重新啟動系統容器…"
Push-Location $InstallDir
try {
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw "容器啟動失敗。可還原：把 .env.bak-$ts 改回 .env，再執行 docker compose up -d。" }
    docker compose restart inventree-server inventree-worker inventree-proxy
    if ($LASTEXITCODE -ne 0) { throw "容器重新啟動失敗，請執行 docker compose ps 查看。" }
} finally { Pop-Location }

$deadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 3
    try { Invoke-WebRequest "http://localhost/api/" -UseBasicParsing -TimeoutSec 5 | Out-Null; $up = $true } catch { $up = $false }
} until ($up -or (Get-Date) -gt $deadline)
if (-not $up) { throw "系統 5 分鐘內未就緒。請執行 docker compose ps 與 docker compose logs --tail 50 inventree-server 查看原因。" }
Write-Host "✓ 系統已就緒，正在啟用管理看板…"

$problem = Invoke-DashboardActivate -InstallDir $InstallDir
if ($problem) {
    Write-Host "⚠ 管理看板尚未啟用：$problem" -ForegroundColor Yellow
    Write-Host "  系統其他功能不受影響。稍後可再執行一次本腳本；仍失敗請把上方訊息交給協助的人。" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "完成！" -ForegroundColor Green
Write-Host "  1. 開啟 App 後按一次 Ctrl+F5（每台電腦各按一次）。"
Write-Host "  2. 到「儀表板」→ 右上角選單 →「新增小工具」，可以看到：各公司庫存總覽、跨公司調動與異常、今日異動摘要、呆滯庫存。"
Write-Host "  3. 呆滯天數與異常顯示時間：管理中心 → 外掛（Plugins）→ 管理看板 的設定。"
