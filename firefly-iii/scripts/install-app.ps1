# Create a desktop shortcut that opens Firefly III as a standalone app window (no address bar),
# using the custom firefly icon. This script is ASCII-only on purpose so it works on any Windows locale.
# It only (1) copies the icon to %LOCALAPPDATA%\FireflyIII and (2) creates one .lnk on the Desktop.
# Usage (in the firefly-iii folder):
#   powershell -ExecutionPolicy Bypass -File scripts\install-app.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\install-app.ps1 -Url http://100.x.y.z:8080
param(
  [string]$Url = ''
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

# 1. URL (default: APP_URL from .env)
if (-not $Url) {
  $envFile = Join-Path $root '.env'
  if (Test-Path $envFile) {
    $line = Get-Content $envFile | Where-Object { $_ -match '^APP_URL=' } | Select-Object -First 1
    if ($line) { $Url = ($line -replace '^APP_URL=', '').Trim().Trim('"') }
  }
}
if (-not $Url) { $Url = 'http://localhost:8080' }
Write-Host "URL     : $Url"

# 2. Browser (Edge first, then Chrome)
$candidates = @(
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$browser = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) { throw 'Neither Edge nor Chrome was found. Please install one of them.' }
Write-Host "Browser : $browser"

# 3. Copy icon to a stable location
$icoSrc = Join-Path $root 'icon\firefly-app.ico'
if (-not (Test-Path $icoSrc)) { throw "Icon not found: $icoSrc" }
$iconDir = Join-Path $env:LOCALAPPDATA 'FireflyIII'
New-Item -ItemType Directory -Force -Path $iconDir | Out-Null
$icoDst = Join-Path $iconDir 'firefly-app.ico'
Copy-Item $icoSrc $icoDst -Force
Write-Host "Icon    : $icoDst"

# 4. Desktop folder (must exist)
$desktop = [Environment]::GetFolderPath('Desktop')
Write-Host "Desktop : $desktop  (exists: $(Test-Path $desktop))"
if (-not (Test-Path $desktop)) {
  $alt = Join-Path $env:USERPROFILE 'Desktop'
  if (Test-Path $alt) { $desktop = $alt } else { throw "Desktop folder not found: $desktop" }
}

# 5. Create the shortcut with an ASCII name first (avoids Unicode problems in the COM call)
$lnkAscii = Join-Path $desktop 'Firefly.lnk'
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkAscii)
$lnk.TargetPath = $browser
$lnk.Arguments = "--app=$Url"
$lnk.IconLocation = "$icoDst,0"
$lnk.Description = 'Firefly III'
$lnk.WorkingDirectory = Split-Path -Parent $browser
$lnk.Save()
if (-not (Test-Path $lnkAscii)) { throw "Shortcut was not created: $lnkAscii" }

# 6. Try to rename it to the Chinese name (written as Unicode code points so the file encoding does not matter)
$zhName = -join ([char]0x8A18, [char]0x5E33)
$final = $lnkAscii
try {
  $zhPath = Join-Path $desktop ($zhName + '.lnk')
  Move-Item -LiteralPath $lnkAscii -Destination $zhPath -Force
  $final = $zhPath
} catch {
  Write-Host 'Could not rename to the Chinese name; keeping Firefly.lnk' -ForegroundColor Yellow
}

Write-Host ''
Write-Host "Done. Shortcut created: $final" -ForegroundColor Green
Write-Host 'Double-click it to open. Right-click -> Pin to taskbar / Start if you like.'
Write-Host 'Docker Desktop must be running, otherwise the page will not open.'
