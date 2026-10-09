# 庫存管理系統：一鍵啟動（主機電腦用）
# 由桌面捷徑「庫存管理系統」呼叫：確認 Docker 已啟動 → 啟動 InvenTree → 以 App 視窗開啟。
param(
    [string]$InstallDir = $PSScriptRoot,
    [string]$Url = "http://localhost/app/"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName PresentationFramework
$Host.UI.RawUI.WindowTitle = "庫存管理系統 - 啟動中"

function Fail([string]$msg) {
    [System.Windows.MessageBox]::Show($msg, "庫存管理系統", "OK", "Error") | Out-Null
    exit 1
}

function Test-Docker {
    try { docker info *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

function Find-AppBrowser {
    foreach ($exe in @("msedge.exe", "chrome.exe")) {
        foreach ($root in @("HKLM:", "HKCU:")) {
            $key = "$root\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\$exe"
            if (Test-Path $key) {
                $path = (Get-ItemProperty $key).'(default)'
                if ($path -and (Test-Path $path)) { return $path }
            }
        }
    }
    return $null
}

function Test-Site([string]$u) {
    try { Invoke-WebRequest $u -UseBasicParsing -TimeoutSec 5 | Out-Null; return $true } catch { return $false }
}

# 已在執行就直接開視窗
if (-not (Test-Site $Url)) {
    # 1. Docker
    if (-not (Test-Docker)) {
        Write-Host "正在啟動 Docker Desktop…"
        $dd = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
        if (-not (Test-Path $dd)) { Fail "找不到 Docker Desktop，請確認已安裝。" }
        Start-Process $dd
        $deadline = (Get-Date).AddMinutes(3)
        while (-not (Test-Docker)) {
            if ((Get-Date) -gt $deadline) { Fail "Docker Desktop 啟動逾時（3 分鐘）。請手動開啟 Docker Desktop 後再試一次。" }
            Start-Sleep -Seconds 3
        }
    }

    # 2. InvenTree
    Write-Host "正在啟動庫存管理系統…（第一次可能需要 1–3 分鐘）"
    Push-Location $InstallDir
    try {
        docker compose up -d
        if ($LASTEXITCODE -ne 0) { Fail "啟動失敗。請在 $InstallDir 執行 docker compose logs 查看原因。" }
    } finally { Pop-Location }

    $deadline = (Get-Date).AddMinutes(5)
    while (-not (Test-Site $Url)) {
        if ((Get-Date) -gt $deadline) { Fail "系統啟動逾時（5 分鐘）。請在 $InstallDir 執行 docker compose ps 查看狀態。" }
        Start-Sleep -Seconds 3
    }
}

# 3. 以 App 視窗開啟（沒有網址列）；找不到 Edge／Chrome 時用預設瀏覽器
$browser = Find-AppBrowser
if ($browser) { Start-Process $browser "--app=$Url" } else { Start-Process $Url }
