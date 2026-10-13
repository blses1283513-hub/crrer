# 妮菈穿戴甲正式版：安裝、更新、備份、還原共用的函式（Windows PowerShell 5.1 與 PowerShell 7 皆可）
# 注意：呼叫 docker 時不使用 2>&1，避免 Windows PowerShell 5.1 在 ErrorActionPreference=Stop 時
#       把 docker 寫到 stderr 的一般訊息（進度、警告）當成錯誤而中止。

$script:Utf8NoBom = New-Object System.Text.UTF8Encoding $false

function Get-NilaEnv {
    param([Parameter(Mandatory = $true)][string]$Path)
    $values = @{}
    if (Test-Path $Path) {
        foreach ($line in [IO.File]::ReadAllLines($Path)) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') {
                $v = $Matches[2]
                if ($v.Length -ge 2 -and (($v[0] -eq "'" -and $v[-1] -eq "'") -or ($v[0] -eq '"' -and $v[-1] -eq '"'))) { $v = $v.Substring(1, $v.Length - 2) }
                $values[$Matches[1]] = $v
            }
        }
    }
    return $values
}

# 寫入 .env：值一律以單引號包住（Docker Compose 照字面讀取，$ " 空白 都不會被解析），所以值不可含單引號
function Set-NilaEnv {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Values)
    $lines = foreach ($k in $Values.Keys) {
        $v = [string]$Values[$k]
        if ($v.Contains("'")) { throw "$k 的值不可包含單引號 '" }
        "$k='$v'"
    }
    [IO.File]::WriteAllText($Path, (($lines -join "`n") + "`n"), $script:Utf8NoBom)
}

function Get-NilaAppVersion {
    param([Parameter(Mandatory = $true)][string]$AppsDir)
    $init = Join-Path $AppsDir "nila_app/nila_app/__init__.py"
    $m = [regex]::Match([IO.File]::ReadAllText($init), '__version__\s*=\s*"([^"]+)"')
    if (-not $m.Success) { throw "讀不到 nila_app 的版本：$init" }
    return $m.Groups[1].Value
}

function Assert-Docker {
    try { docker version --format '{{.Server.Version}}' | Out-Null } catch { throw "找不到執行中的 Docker。請先啟動 Docker Desktop（右下角鯨魚圖示不再轉動）再執行。" }
    if ($LASTEXITCODE -ne 0) { throw "找不到執行中的 Docker。請先啟動 Docker Desktop 再執行。" }
}

function Wait-NilaReady {
    param([Parameter(Mandatory = $true)][int]$Port, [int]$Minutes = 5)
    $deadline = (Get-Date).AddMinutes($Minutes)
    do {
        Start-Sleep -Seconds 3
        try { $ok = (Invoke-WebRequest "http://localhost:$Port/api/method/ping" -UseBasicParsing -TimeoutSec 5).Content -match 'pong' } catch { $ok = $false }
    } until ($ok -or (Get-Date) -gt $deadline)
    return $ok
}

# 等一次性服務（create-site）結束；回傳 "exited 0" 之類的狀態
function Wait-NilaOneShot {
    param([Parameter(Mandatory = $true)][string]$Service, [int]$Minutes = 25)
    $deadline = (Get-Date).AddMinutes($Minutes)
    do {
        Start-Sleep -Seconds 10
        $state = (docker compose ps -a $Service --format '{{.State}} {{.ExitCode}}') | Select-Object -First 1
        Write-Host ("  {0}… {1}" -f $Service, $state)
    } until (($state -match '^exited') -or (Get-Date) -gt $deadline)
    return $state
}

# 前端（nginx）啟動時會記住後端的位址；後端重新建立後要一起重新啟動，否則會出現 502
function Restart-NilaAll {
    docker compose restart
    if ($LASTEXITCODE -ne 0) { throw "重新啟動失敗，請執行 docker compose ps 查看。" }
}

function Get-NilaLanIp {
    try {
        $ip = Get-NetIPConfiguration -ErrorAction Stop | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq "Up" } |
            ForEach-Object { $_.IPv4Address.IPAddress } | Select-Object -First 1
        if ($ip) { return $ip }
    } catch { }
    return "電腦IP"
}
