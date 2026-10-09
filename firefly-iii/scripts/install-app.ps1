# 把 Firefly III 變成電腦上的 App：在桌面建立「記帳」捷徑（獨立視窗、無網址列、自訂螢火蟲圖示）。
# 只會做兩件事：複製圖示到 %LOCALAPPDATA%\FireflyIII，並在桌面建立一個 .lnk 捷徑。不會改動其他設定。
# 用法（在 firefly-iii 資料夾的 PowerShell）：
#   powershell -ExecutionPolicy Bypass -File scripts\install-app.ps1
# 指定網址（預設讀取 .env 的 APP_URL）：
#   powershell -ExecutionPolicy Bypass -File scripts\install-app.ps1 -Url http://100.x.y.z:8080
param(
  [string]$Url = '',
  [string]$Name = '記帳'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# 1. 網址
if (-not $Url) {
  $envFile = Join-Path $root '.env'
  if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match '^APP_URL=' } | Select-Object -First 1
    if ($line) { $Url = ($line -replace '^APP_URL=', '').Trim().Trim('"') }
  }
}
if (-not $Url) { $Url = 'http://localhost:8080' }
Write-Host "網址：$Url"

# 2. 找瀏覽器（優先 Edge，其次 Chrome）
$candidates = @(
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$browser = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) { throw '找不到 Edge 或 Chrome，請先安裝其中一個。' }
Write-Host "瀏覽器：$browser"

# 3. 複製圖示到固定位置（之後搬動 firefly-iii 資料夾，圖示也不會消失）
$icoSrc = Join-Path $root 'icon\firefly-app.ico'
if (-not (Test-Path $icoSrc)) { throw "找不到圖示：$icoSrc" }
$iconDir = Join-Path $env:LOCALAPPDATA 'FireflyIII'
New-Item -ItemType Directory -Force -Path $iconDir | Out-Null
$icoDst = Join-Path $iconDir 'firefly-app.ico'
Copy-Item $icoSrc $icoDst -Force

# 4. 建立桌面捷徑（--app 模式：獨立視窗、無網址列）
$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop "$Name.lnk"
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)
$lnk.TargetPath = $browser
$lnk.Arguments = "--app=$Url"
$lnk.IconLocation = "$icoDst,0"
$lnk.Description = 'Firefly III 記帳'
$lnk.WorkingDirectory = Split-Path -Parent $browser
$lnk.Save()

Write-Host ''
Write-Host "完成：桌面已建立捷徑「$Name」。雙擊即可開啟。" -ForegroundColor Green
Write-Host '可以對捷徑按右鍵 → 釘選到工作列 / 開始。'
Write-Host '提醒：Docker Desktop 需要在執行中，記帳頁面才打得開。'
