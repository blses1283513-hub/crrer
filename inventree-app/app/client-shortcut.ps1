# 庫存管理系統：在「其他電腦」建立桌面捷徑
# 不需要安裝 Docker，也不需要系統管理員權限。
# 用法：powershell -ExecutionPolicy Bypass -File client-shortcut.ps1 -Server 192.168.1.20
param(
    [Parameter(Mandatory = $true)][string]$Server
)

$ErrorActionPreference = "Stop"
$Server = $Server.Trim() -replace '^https?://', '' -replace '/.*$', ''
$url = "http://$Server/app/"

Write-Host "檢查能否連到主機 $Server …"
try { Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 10 | Out-Null }
catch { throw "連不到 $url 。請確認：主機電腦已開機並啟動系統、兩台在同一個網路、主機防火牆已開放。" }

$dir = Join-Path $env:LOCALAPPDATA "InventoryApp"
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$icon = Join-Path $dir "icon.ico"
Invoke-WebRequest "http://$Server/app/icon.ico" -UseBasicParsing -OutFile $icon

$browser = $null
foreach ($exe in @("msedge.exe", "chrome.exe")) {
    foreach ($root in @("HKLM:", "HKCU:")) {
        $key = "$root\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\$exe"
        if (-not $browser -and (Test-Path $key)) {
            $p = (Get-ItemProperty $key).'(default)'
            if ($p -and (Test-Path $p)) { $browser = $p }
        }
    }
}
if (-not $browser) { throw "找不到 Microsoft Edge 或 Google Chrome，請先安裝其中一個。" }

# WScript.Shell 內部以系統「非 Unicode 字碼頁」處理路徑，非中文系統會把中文檔名變成 ?????? 而存檔失敗。
# 因此先以純英文檔名存到暫存資料夾，再用 PowerShell 搬到桌面並改成中文名稱。
try {
    $tmpLnk = Join-Path $env:TEMP ("inventree-app-" + [guid]::NewGuid().ToString("N") + ".lnk")
    $shell = New-Object -ComObject WScript.Shell
    $s = $shell.CreateShortcut($tmpLnk)
    $s.TargetPath = $browser
    $s.Arguments = "--app=$url"
    $s.IconLocation = $icon
    $s.Save()

    $desktops = @([Environment]::GetFolderPath("DesktopDirectory"), (Join-Path $env:USERPROFILE "Desktop"))
    if ($env:OneDrive) { $desktops += (Join-Path $env:OneDrive "Desktop") }
    $desktop = $desktops | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if (-not $desktop) { throw "找不到桌面資料夾。" }
    $final = Join-Path $desktop "庫存管理系統.lnk"
    Move-Item $tmpLnk $final -Force

    Write-Host ""
    Write-Host "完成！桌面已建立「庫存管理系統」捷徑，點兩下即可開啟。" -ForegroundColor Green
} catch {
    Write-Host "⚠ 桌面捷徑建立失敗：$($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "  請手動建立：在桌面按右鍵 → 新增 → 捷徑，位置貼上下面這一行：" -ForegroundColor Yellow
    Write-Host "    `"$browser`" --app=$url" -ForegroundColor Cyan
}
