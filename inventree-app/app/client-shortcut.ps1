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

$lnk = Join-Path ([Environment]::GetFolderPath("Desktop")) "庫存管理系統.lnk"
$shell = New-Object -ComObject WScript.Shell
$s = $shell.CreateShortcut($lnk)
$s.TargetPath = $browser
$s.Arguments = "--app=$url"
$s.IconLocation = $icon
$s.Description = "庫存管理系統（主機 $Server）"
$s.Save()

Write-Host ""
Write-Host "完成！桌面已建立「庫存管理系統」捷徑，點兩下即可開啟。" -ForegroundColor Green
