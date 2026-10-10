# 庫存管理系統：主機設定（在「已安裝 InvenTree 的電腦」執行一次）
# 讓這台電腦成為主機，其他電腦可透過區網連入；並建立桌面 App 捷徑、內建中文操作助手、
# 預設語言設為繁體中文。執行前會列出所有變更並請你確認。
#
# 用法（建議以系統管理員身分開啟 PowerShell，才能設定防火牆）：
#   powershell -ExecutionPolicy Bypass -File .\setup-server.ps1
#   powershell -ExecutionPolicy Bypass -File .\setup-server.ps1 -InstallDir D:\inventree -ServerIP 192.168.1.20
param(
    [string]$InstallDir = (Join-Path $HOME "inventree"),
    [string]$ServerIP = ""
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$helperSrc = Join-Path $here "..\inventree-ui-helper\inventree-ui-helper.user.js"
$utf8 = New-Object System.Text.UTF8Encoding $false

Write-Host "== 庫存管理系統：主機設定 ==" -ForegroundColor Cyan

# ---------- 檢查 ----------
foreach ($f in @("docker-compose.yml", ".env")) {
    if (-not (Test-Path (Join-Path $InstallDir $f))) { throw "在 $InstallDir 找不到 $f。請確認 InvenTree 已用 install.ps1 安裝，或用 -InstallDir 指定位置。" }
}
foreach ($f in @("Caddyfile.app", "docker-compose.override.yml", "start-inventree.ps1", "backup.ps1", "restore.ps1", "app\index.html", "app\icon.ico", "app\icon.png", "app\client-shortcut.ps1", "lib\EnvFile.ps1", "lib\NotifierConfig.ps1", "lib\DashboardPlugin.ps1", "notifier\notifier.py", "notifier\config.example.json", "plugins\mgmt_dashboard\__init__.py", "plugins\mgmt_dashboard\static\mgmt_dashboard.js")) {
    if (-not (Test-Path (Join-Path $here $f))) { throw "安裝套件缺少 $f，請重新下載完整的 inventree-app 資料夾。" }
}
if (-not (Test-Path $helperSrc)) { throw "找不到中文操作助手 $helperSrc，請下載完整的 repo（需要 inventree-ui-helper 資料夾）。" }
# 通知服務的公司設定以匯入腳本的設定為準（config.json 優先，沒有就用範例）
$seedDir = Join-Path $here "..\inventree-seed"
$seedConfig = @("config.json", "config.example.json") | ForEach-Object { Join-Path $seedDir $_ } | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $seedConfig) { throw "找不到公司設定 $seedDir\config.json（需要下載完整的 repo，包含 inventree-seed 資料夾）。" }
. (Join-Path $here "lib\EnvFile.ps1")
. (Join-Path $here "lib\NotifierConfig.ps1")
. (Join-Path $here "lib\DashboardPlugin.ps1")

$ovr = Join-Path $InstallDir "docker-compose.override.yml"
if ((Test-Path $ovr) -and -not (Select-String -Path $ovr -Pattern '\[inventree-app\]' -Quiet)) {
    throw "$ovr 已存在且不是本工具建立的，為避免覆蓋你的設定已停止。"
}

# ---------- 偵測區網 IP ----------
if (-not $ServerIP) {
    $cands = @(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" } |
        ForEach-Object { $_.IPv4Address.IPAddress })
    $guess = if ($cands.Count) { $cands[0] } else { "" }
    $ans = Read-Host "本機區網 IP 偵測為「$guess」。直接按 Enter 使用，或輸入正確的 IP"
    $ServerIP = if ($ans.Trim()) { $ans.Trim() } else { $guess }
}
if ($ServerIP -notmatch '^\d{1,3}(\.\d{1,3}){3}$') { throw "IP 格式不正確：「$ServerIP」" }

$settings = [ordered]@{
    "INVENTREE_SITE_URL"        = "`"http://$ServerIP`""
    "INVENTREE_ALLOWED_HOSTS"   = "`"$ServerIP,localhost,127.0.0.1`""
    "INVENTREE_TRUSTED_ORIGINS" = "`"http://$ServerIP,http://localhost,http://127.0.0.1`""
    "INVENTREE_LANGUAGE"        = "zh-hant"
}
# 管理看板外掛（儀表板小工具）：啟用外掛並設為每次啟動自動啟用
$envPath = Join-Path $InstallDir ".env"
(Get-DashboardEnvSettings -Current (Get-EnvValues -Path $envPath)).GetEnumerator() | ForEach-Object { $settings[$_.Key] = $_.Value }
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$ts = Get-Date -Format "yyyyMMdd-HHmmss"

# ---------- 列出變更，等待確認 ----------
Write-Host ""
Write-Host "將進行以下變更（安裝位置：$InstallDir）：" -ForegroundColor Yellow
Write-Host "  1. 備份 .env 為 .env.bak-$ts"
Write-Host "  2. .env 設定（讓其他電腦可連入、預設繁體中文）："
$settings.GetEnumerator() | ForEach-Object { Write-Host "       $($_.Key)=$($_.Value)" }
Write-Host "  3. 新增／更新檔案（官方檔案不修改）："
Write-Host "       Caddyfile.app、docker-compose.override.yml、start-inventree.ps1、backup.ps1、restore.ps1"
Write-Host "       app\（App 外框、中文操作助手、圖示、用戶端捷徑腳本）"
Write-Host "       notifier\（通知服務；新增一個容器 inventree-notifier，首次會下載約 50MB 的 python:3.12-alpine 映像）"
Write-Host "       通知服務的公司設定取自 $seedConfig ："
foreach ($c in @((Get-Content -Raw -Encoding UTF8 -Path $seedConfig | ConvertFrom-Json).companies)) { Write-Host "         $($c.name)　群組 $($c.owner_group)　料號前綴 $($c.code)-" }
Write-Host "       （若與你實際的公司名稱不同，請先按 N 取消，把你的 config.json 放到 inventree-seed 資料夾後再執行）"
Write-Host "       管理看板外掛（儀表板小工具）：放到 inventree-data\plugins\$DashboardDirName，並在 InvenTree 開啟「介面整合」"
if ($isAdmin) { Write-Host "  4. Windows 防火牆：允許 TCP 80 埠連入（私人／網域網路）" }
else { Write-Host "  4. 防火牆：略過（目前不是系統管理員，完成後會告訴你怎麼補設）" }
Write-Host "  5. 重新啟動系統容器（約 1–3 分鐘，期間無法使用；資料不受影響）"
Write-Host "  6. 桌面建立捷徑「庫存管理系統」"
Write-Host ""
$ok = Read-Host "確定執行？(Y/N)"
if ($ok -notmatch '^[Yy]') { Write-Host "已取消，未做任何變更。"; exit 0 }

# ---------- 1–2. .env ----------
Copy-Item $envPath "$envPath.bak-$ts"
Set-EnvFile -Path $envPath -Settings $settings
Write-Host "✓ .env 已更新（原檔備份為 .env.bak-$ts）"

# ---------- 3. 檔案 ----------
$appDir = Join-Path $InstallDir "app"
New-Item -ItemType Directory -Force -Path $appDir | Out-Null
foreach ($f in @("Caddyfile.app", "docker-compose.override.yml", "start-inventree.ps1", "backup.ps1", "restore.ps1")) {
    Copy-Item (Join-Path $here $f) $InstallDir -Force
}
Copy-Item (Join-Path $here "app\*") $appDir -Recurse -Force
Copy-Item $helperSrc $appDir -Force
Write-Host "✓ App 檔案已放置"

# 通知服務：程式、設定（公司清單依匯入設定產生；保留你自行調整過的其他欄位）、已讀紀錄資料夾
$notifierDir = Join-Path $InstallDir "notifier"
New-Item -ItemType Directory -Force -Path $notifierDir | Out-Null
Copy-Item (Join-Path $here "notifier\notifier.py") $notifierDir -Force
Copy-Item (Join-Path $here "notifier\config.example.json") $notifierDir -Force
$notifierConfig = Join-Path $notifierDir "config.json"
$configJson = New-NotifierConfigJson -SeedConfigPath $seedConfig -TemplatePath (Join-Path $notifierDir "config.example.json") -ExistingPath $notifierConfig
Write-Utf8NoBom -Path $notifierConfig -Text $configJson
$ext = (Get-EnvValues -Path $envPath)["INVENTREE_EXT_VOLUME"]
if (-not $ext) { $ext = "./inventree-data" }
$dataDir = if ([IO.Path]::IsPathRooted($ext)) { $ext } else { Join-Path $InstallDir ($ext -replace '^\./', '') }
New-Item -ItemType Directory -Force -Path (Join-Path $dataDir "notifier") | Out-Null
Write-Host "✓ 通知服務檔案已放置"

# 管理看板外掛：程式與公司清單（與通知服務相同的公司設定）
$null = Install-DashboardPluginFiles -SourceDir (Join-Path $here "plugins\mgmt_dashboard") -DataDir $dataDir -CompaniesJson (New-DashboardCompaniesJson -ConfigPath $seedConfig)
Write-Host "✓ 管理看板外掛已放置"

# ---------- 4. 防火牆 ----------
if ($isAdmin) {
    $ruleName = "InvenTree 庫存管理系統 (TCP 80)"
    if (-not (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -Profile Private, Domain | Out-Null
    }
    Write-Host "✓ 防火牆已允許 TCP 80"
}
$public = @(Get-NetConnectionProfile | Where-Object { $_.NetworkCategory -eq "Public" })
if ($public.Count) {
    Write-Host "⚠ 目前網路「$($public[0].Name)」設定為「公用網路」，其他電腦會被防火牆擋住。" -ForegroundColor Yellow
    Write-Host "  請到「設定 → 網路和網際網路 → 內容」改為「私人網路」。" -ForegroundColor Yellow
}

# ---------- 5. 重新啟動 ----------
Write-Host "重新啟動系統容器…"
Push-Location $InstallDir
try {
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw "容器啟動失敗。可還原：把 .env.bak-$ts 改回 .env、刪除 docker-compose.override.yml，再執行 docker compose up -d。" }
    # Caddyfile.app 與外掛程式是掛載的檔案，內容改變時 up -d 不會重啟，需明確重新啟動
    docker compose restart inventree-server inventree-worker inventree-proxy
    if ($LASTEXITCODE -ne 0) { throw "容器重新啟動失敗，請執行 docker compose ps 查看。" }
} finally { Pop-Location }

$deadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 3
    try { Invoke-WebRequest "http://localhost/app/" -UseBasicParsing -TimeoutSec 5 | Out-Null; $up = $true } catch { $up = $false }
} until ($up -or (Get-Date) -gt $deadline)
if (-not $up) { throw "系統 5 分鐘內未就緒。請執行 docker compose ps 與 docker compose logs --tail 50 inventree-server 查看原因。" }
Write-Host "✓ 系統已就緒"

# 通知服務是新增的容器，啟動需要多一點時間；失敗不影響其他功能，只提示
$deadline = (Get-Date).AddMinutes(3)
do {
    try { $h = Invoke-WebRequest "http://localhost/notify/api/health" -UseBasicParsing -TimeoutSec 5; $notifyUp = ($h.StatusCode -eq 200) } catch { $notifyUp = $false }
    if (-not $notifyUp) { Start-Sleep -Seconds 3 }
} until ($notifyUp -or (Get-Date) -gt $deadline)
if ($notifyUp) { Write-Host "✓ 通知服務已就緒" }
else {
    Write-Host "⚠ 通知服務尚未就緒（不影響其他功能）。請在 $InstallDir 執行：docker compose logs --tail 50 inventree-notifier" -ForegroundColor Yellow
}

# 管理看板：在 InvenTree 內開啟介面整合並複製外掛 JS；失敗不影響其他功能，只提示
$deadline = (Get-Date).AddMinutes(3)
do {
    try { Invoke-WebRequest "http://localhost/api/" -UseBasicParsing -TimeoutSec 5 | Out-Null; $apiUp = $true } catch { $apiUp = $false; Start-Sleep -Seconds 3 }
} until ($apiUp -or (Get-Date) -gt $deadline)
$dashProblem = Invoke-DashboardActivate -InstallDir $InstallDir
if ($dashProblem) {
    Write-Host "⚠ 管理看板尚未啟用（不影響其他功能）：$dashProblem" -ForegroundColor Yellow
    Write-Host "  稍後可在 inventree-app 資料夾執行：powershell -ExecutionPolicy Bypass -File .\enable-dashboard.ps1 -InstallDir $InstallDir" -ForegroundColor Yellow
} else { Write-Host "✓ 管理看板已啟用（儀表板 → 新增小工具）" }

# ---------- 6. 桌面捷徑 ----------
# WScript.Shell 內部以系統「非 Unicode 字碼頁」處理路徑，非中文系統會把中文檔名變成 ?????? 而存檔失敗。
# 因此先以純英文檔名存到暫存資料夾，再用 PowerShell 搬到桌面並改成中文名稱。
# 捷徑失敗不影響系統本身（此時系統已啟動完成），所以只提示、不中止。
$psExe = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
$startScript = Join-Path $InstallDir 'start-inventree.ps1'
$shortcutArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$startScript`""
try {
    $tmpLnk = Join-Path $env:TEMP ("inventree-app-" + [guid]::NewGuid().ToString("N") + ".lnk")
    $shell = New-Object -ComObject WScript.Shell
    $s = $shell.CreateShortcut($tmpLnk)
    $s.TargetPath = $psExe
    $s.Arguments = $shortcutArgs
    $s.WorkingDirectory = $InstallDir
    $s.IconLocation = Join-Path $appDir "icon.ico"
    $s.Save()

    $desktops = @([Environment]::GetFolderPath("DesktopDirectory"), (Join-Path $env:USERPROFILE "Desktop"))
    if ($env:OneDrive) { $desktops += (Join-Path $env:OneDrive "Desktop") }
    $desktop = $desktops | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $desktop) { throw "找不到桌面資料夾。" }
    $final = Join-Path $desktop "庫存管理系統.lnk"
    Move-Item $tmpLnk $final -Force
    Write-Host "✓ 桌面捷徑已建立：$final"
} catch {
    Write-Host "⚠ 桌面捷徑建立失敗：$($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  不影響系統使用。請手動建立：在桌面按右鍵 → 新增 → 捷徑，位置貼上下面這一行：" -ForegroundColor Yellow
    Write-Host "    `"$psExe`" $shortcutArgs" -ForegroundColor Cyan
}

# ---------- 完成 ----------
Write-Host ""
Write-Host "完成！" -ForegroundColor Green
Write-Host "  本機：點桌面「庫存管理系統」，或瀏覽器開 http://localhost"
Write-Host "  其他電腦：瀏覽器開 http://$ServerIP"
Write-Host "  其他電腦建立桌面捷徑（在那台電腦的 PowerShell 貼上）："
Write-Host "    iwr http://$ServerIP/app/client-shortcut.ps1 -OutFile `$env:TEMP\cs.ps1; powershell -ExecutionPolicy Bypass -File `$env:TEMP\cs.ps1 -Server $ServerIP" -ForegroundColor Cyan
if (-not $isAdmin) {
    Write-Host ""
    Write-Host "⚠ 防火牆尚未設定。請以系統管理員身分開啟 PowerShell，執行：" -ForegroundColor Yellow
    Write-Host "    New-NetFirewallRule -DisplayName 'InvenTree 庫存管理系統 (TCP 80)' -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -Profile Private,Domain" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "提醒：主機 IP 若改變（例如路由器重新分配），其他電腦會連不到。建議在路由器把 $ServerIP 固定給這台電腦，IP 改變時重新執行本腳本即可。"
