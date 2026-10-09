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
foreach ($f in @("Caddyfile.app", "docker-compose.override.yml", "start-inventree.ps1", "backup.ps1", "app\index.html", "app\icon.ico", "app\icon.png", "app\client-shortcut.ps1")) {
    if (-not (Test-Path (Join-Path $here $f))) { throw "安裝套件缺少 $f，請重新下載完整的 inventree-app 資料夾。" }
}
if (-not (Test-Path $helperSrc)) { throw "找不到中文操作助手 $helperSrc，請下載完整的 repo（需要 inventree-ui-helper 資料夾）。" }

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
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$ts = Get-Date -Format "yyyyMMdd-HHmmss"

# ---------- 列出變更，等待確認 ----------
Write-Host ""
Write-Host "將進行以下變更（安裝位置：$InstallDir）：" -ForegroundColor Yellow
Write-Host "  1. 備份 .env 為 .env.bak-$ts"
Write-Host "  2. .env 設定（讓其他電腦可連入、預設繁體中文）："
$settings.GetEnumerator() | ForEach-Object { Write-Host "       $($_.Key)=$($_.Value)" }
Write-Host "  3. 新增／更新檔案（官方檔案不修改）："
Write-Host "       Caddyfile.app、docker-compose.override.yml、start-inventree.ps1、backup.ps1"
Write-Host "       app\（App 外框、中文操作助手、圖示、用戶端捷徑腳本）"
if ($isAdmin) { Write-Host "  4. Windows 防火牆：允許 TCP 80 埠連入（私人／網域網路）" }
else { Write-Host "  4. 防火牆：略過（目前不是系統管理員，完成後會告訴你怎麼補設）" }
Write-Host "  5. 重新啟動系統容器（約 1–3 分鐘，期間無法使用；資料不受影響）"
Write-Host "  6. 桌面建立捷徑「庫存管理系統」"
Write-Host ""
$ok = Read-Host "確定執行？(Y/N)"
if ($ok -notmatch '^[Yy]') { Write-Host "已取消，未做任何變更。"; exit 0 }

# ---------- 1–2. .env ----------
$envPath = Join-Path $InstallDir ".env"
Copy-Item $envPath "$envPath.bak-$ts"
$text = [IO.File]::ReadAllText($envPath)
foreach ($kv in $settings.GetEnumerator()) {
    $line = "$($kv.Key)=$($kv.Value)"
    $re = [regex]("(?m)^" + [regex]::Escape($kv.Key) + "=.*$")
    if ($re.IsMatch($text)) {
        $evaluator = [System.Text.RegularExpressions.MatchEvaluator] { param($m) $line }.GetNewClosure()
        $text = $re.Replace($text, $evaluator, 1)
    } else {
        $text = $text.TrimEnd() + "`n$line`n"
    }
}
[IO.File]::WriteAllText($envPath, $text, $utf8)
Write-Host "✓ .env 已更新（原檔備份為 .env.bak-$ts）"

# ---------- 3. 檔案 ----------
$appDir = Join-Path $InstallDir "app"
New-Item -ItemType Directory -Force -Path $appDir | Out-Null
foreach ($f in @("Caddyfile.app", "docker-compose.override.yml", "start-inventree.ps1", "backup.ps1")) {
    Copy-Item (Join-Path $here $f) $InstallDir -Force
}
Copy-Item (Join-Path $here "app\*") $appDir -Recurse -Force
Copy-Item $helperSrc $appDir -Force
Write-Host "✓ App 檔案已放置"

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
} finally { Pop-Location }

$deadline = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 3
    try { Invoke-WebRequest "http://localhost/app/" -UseBasicParsing -TimeoutSec 5 | Out-Null; $up = $true } catch { $up = $false }
} until ($up -or (Get-Date) -gt $deadline)
if (-not $up) { throw "系統 5 分鐘內未就緒。請執行 docker compose ps 與 docker compose logs --tail 50 inventree-server 查看原因。" }
Write-Host "✓ 系統已就緒"

# ---------- 6. 桌面捷徑 ----------
$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "庫存管理系統.lnk"
$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
$s.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$(Join-Path $InstallDir 'start-inventree.ps1')`""
$s.WorkingDirectory = $InstallDir
$s.IconLocation = Join-Path $appDir "icon.ico"
$s.Description = "庫存管理系統（主機）"
$s.Save()
Write-Host "✓ 桌面捷徑已建立"

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
