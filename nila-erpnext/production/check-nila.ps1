# 妮菈穿戴甲正式版：健康檢查（隨時可以執行，不會改動資料）
# 檢查：Docker、每個服務、網頁能不能開、上次備份（含第二個地方）、磁碟空間、自動排程。
#
# 用法：
#   powershell -ExecutionPolicy Bypass -File .\check-nila.ps1            只檢查
#   powershell -ExecutionPolicy Bypass -File .\check-nila.ps1 -Fix       系統沒有回應時自動啟動或重新啟動
#   開機（登入）後自動檢查並啟動（登記 Windows 工作排程器；請用「以系統管理員身分執行」的 PowerShell）：
#   powershell -ExecutionPolicy Bypass -File .\check-nila.ps1 -RegisterStartup
param(
    [string]$InstallDir = (Split-Path $PSScriptRoot -Parent),
    [switch]$Fix,
    [switch]$RegisterStartup,
    [int]$WaitDockerMinutes = 0,
    [int]$MaxBackupHours = 36,
    [double]$MinFreeGB = 10,
    [int]$MaxDrillDays = 40
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/NilaCommon.ps1")
$prodDir = Join-Path $InstallDir "production"
if (-not (Test-Path (Join-Path $prodDir "docker-compose.yml"))) { throw "在 $prodDir 找不到正式版，請用 -InstallDir 指定安裝位置。" }
$logPath = Join-Path $InstallDir "check-nila.log"

if ($RegisterStartup) {
    $self = Join-Path $prodDir "check-nila.ps1"
    $tr = "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$self`" -InstallDir `"$InstallDir`" -Fix -WaitDockerMinutes 15"
    schtasks /Create /F /SC ONLOGON /DELAY 0001:00 /RL HIGHEST /TN "NilaStart" /TR $tr | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "登記排程失敗：請在開始功能表的 PowerShell 按右鍵「以系統管理員身分執行」後再執行。" }
    Write-Host "✓ 已登記：每次登入 Windows 後 1 分鐘自動檢查並啟動系統（工作排程器：NilaStart，紀錄在 $logPath）。" -ForegroundColor Green
    Write-Host "  另外請確認：Docker Desktop 設定「登入時自動啟動」；停電後自動開機與自動登入請見 README「開機自動啟動與停電」。"
    exit 0
}

$failures = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]
$log = New-Object System.Collections.Generic.List[string]
function Say([string]$mark, [string]$text, [string]$color = "Gray") {
    Write-Host "$mark $text" -ForegroundColor $color
    $log.Add("$mark $text")
}
function Ok([string]$t) { Say "✓" $t "Green" }
function Bad([string]$t) { Say "✗" $t "Red"; $failures.Add($t) }
function Warn([string]$t) { Say "!" $t "Yellow"; $warnings.Add($t) }

# 執行外部指令、不顯示輸出，回傳結束代碼。Windows PowerShell 5.1 在 Stop 模式下把 stderr 轉向會變成錯誤，所以暫時改成 Continue
function Invoke-Quiet([scriptblock]$Block) {
    $old = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Block *> $null } catch { return 1 } finally { $ErrorActionPreference = $old }
    return $LASTEXITCODE
}
function Test-Docker { return ((Invoke-Quiet { docker version --format '{{.Server.Version}}' }) -eq 0) }
function Test-Ping([int]$port) {
    try { return ((Invoke-WebRequest "http://localhost:$port/api/method/ping" -UseBasicParsing -TimeoutSec 10).Content -match 'pong') } catch { return $false }
}
function Get-Services {
    # docker compose ps 的 JSON：新版每行一個物件，舊版是一個陣列
    $raw = @(docker compose ps -a --format json) -join "`n"
    if (-not $raw.Trim()) { return @() }
    if ($raw.TrimStart().StartsWith("[")) { return @($raw | ConvertFrom-Json) }
    return @($raw -split "`n" | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json })
}

Say "==" ("妮菈系統檢查 {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) "Cyan"
$envValues = Get-NilaEnv -Path (Join-Path $prodDir ".env")
$port = [int]$envValues["HTTP_PORT"]
if (-not $port) { $port = 8090 }

# 1. Docker（開機後 Docker Desktop 需要一點時間啟動）
$deadline = (Get-Date).AddMinutes($WaitDockerMinutes)
while (-not (Test-Docker) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 10 }
if (Test-Docker) { Ok "Docker 執行中" } else { Bad "Docker 沒有執行：請啟動 Docker Desktop（並在設定中勾選「登入時自動啟動」）" }

if (-not $failures.Count) {
    Push-Location $prodDir
    try {
        # 2. 網頁（開機後服務自己會啟動，最多等 3 分鐘）
        $ready = Test-Ping $port
        if (-not $ready -and $Fix) {
            Say "…" "網頁還沒有回應，等服務自動啟動（最多 3 分鐘）"
            $ready = Wait-NilaReady -Port $port -Minutes 3
            if (-not $ready) {
                Say "…" "啟動所有服務（docker compose up -d）"
                Invoke-Quiet { docker compose up -d } | Out-Null
                # up -d 會重新執行啟動設定（create-site）；等它做完，避免剛恢復時登入出錯
                Wait-NilaOneShot -Service "create-site" -Minutes 15 | Out-Null
                $ready = Wait-NilaReady -Port $port -Minutes 8
            }
            if (-not $ready) {
                Say "…" "重新啟動所有服務（docker compose restart）"
                Invoke-Quiet { docker compose restart } | Out-Null
                $ready = Wait-NilaReady -Port $port -Minutes 5
            }
            if ($ready) { Say "…" "已自動恢復" }
        }
        if ($ready) { Ok "網頁正常：http://localhost:$port" } else { Bad "網頁沒有回應（http://localhost:$port）。請執行 check-nila.ps1 -Fix；仍不行請看 docker compose logs --tail 50 backend" }

        # 3. 每個服務
        $long = "backend", "frontend", "websocket", "queue-short", "queue-long", "scheduler", "db", "redis-cache", "redis-queue"
        $svc = @{}
        foreach ($s in Get-Services) { $svc[$s.Service] = $s }
        $down = @($long | Where-Object { -not $svc.ContainsKey($_) -or $svc[$_].State -ne "running" })
        if ($down.Count) { Bad ("沒有在執行的服務：{0}" -f ($down -join "、")) } else { Ok "9 個服務都在執行" }
        $failedOneShot = @("configurator", "create-site" | Where-Object { $svc.ContainsKey($_) -and $svc[$_].State -eq "exited" -and [int]$svc[$_].ExitCode -ne 0 })
        if ($failedOneShot.Count -and $Fix) {
            # 多半是全部服務同時重新啟動時資料庫還沒好；重新執行一次啟動設定
            Say "…" "重新執行啟動設定（$($failedOneShot -join '、')）"
            Invoke-Quiet { docker compose up -d create-site } | Out-Null
            Wait-NilaOneShot -Service "create-site" -Minutes 15 | Out-Null
            $svc = @{}
            foreach ($s in Get-Services) { $svc[$s.Service] = $s }
        }
        foreach ($one in "configurator", "create-site") {
            if ($svc.ContainsKey($one) -and $svc[$one].State -eq "exited" -and [int]$svc[$one].ExitCode -ne 0) {
                Bad "啟動設定（$one）失敗，結束代碼 $($svc[$one].ExitCode)：請看 docker compose logs $one"
            }
        }
    } finally { Pop-Location }
}

# 4. 上次備份
$statePath = Join-Path $InstallDir "last-backup.json"
if (Test-Path $statePath) {
    $b = Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $when = [datetime]::ParseExact($b.time, "yyyy-MM-dd HH:mm:ss", $null)
    $hours = [math]::Round(((Get-Date) - $when).TotalHours, 1)
    if (-not $b.ok) { Bad "上次備份失敗（$($b.time)）：$($b.error)" }
    elseif ($hours -gt $MaxBackupHours) { Bad "已經 $hours 小時沒有備份（上次 $($b.time)）。請確認每天自動備份的排程與電腦在備份時間有開著" }
    else { Ok "上次備份：$($b.time)（$($b.size_mb) MB）" }
    if ($b.ok) {
        if (-not $b.copy_to) { Warn "備份沒有複製到第二個地方（雲端資料夾）。登記排程時請加上 -CopyTo" }
        elseif (-not (Test-Path ([IO.Path]::Combine($b.copy_to, (Split-Path $b.dir -Leaf))))) { Bad "第二個地方找不到這份備份：$($b.copy_to)（雲端資料夾是否還在？）" }
        else { Ok "第二個地方也有：$($b.copy_to)" }
    }
} else {
    Bad "還沒有備份紀錄。請執行 backup-nila.ps1，並用 -RegisterDaily 登記每天自動備份"
}

# 5. 還原演練（建議每個月一次）
$drillPath = Join-Path $InstallDir "last-drill.json"
if (Test-Path $drillPath) {
    $d = Get-Content $drillPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $days = [math]::Floor(((Get-Date) - [datetime]::ParseExact($d.time, "yyyy-MM-dd HH:mm:ss", $null)).TotalDays)
    if (-not $d.ok) { Bad "上次還原演練失敗（$($d.time)）：請換一份備份再執行 drill-nila.ps1" }
    elseif ($days -gt $MaxDrillDays) { Warn "已經 $days 天沒有做還原演練，建議執行 drill-nila.ps1" }
    else { Ok "上次還原演練成功：$($d.time)" }
} else {
    Warn "還沒有做過還原演練，建議執行 drill-nila.ps1（每個月一次）"
}

# 6. 磁碟空間
$free = Get-NilaFreeGB -Path $InstallDir
if ($null -eq $free) { Warn "讀不到磁碟空間" }
elseif ($free -lt $MinFreeGB) { Bad "磁碟只剩 $free GB（建議至少 $MinFreeGB GB）。請清理檔案；備份資料夾只會保留最近 30 份" }
else { Ok "磁碟剩餘 $free GB" }

# 7. 自動排程（只有 Windows）
if ($env:OS -eq "Windows_NT") {
    foreach ($t in @(@("NilaBackup", "每天自動備份", "backup-nila.ps1 -RegisterDaily"), @("NilaStart", "登入後自動啟動", "check-nila.ps1 -RegisterStartup"))) {
        $name = $t[0]
        if ((Invoke-Quiet { schtasks /Query /TN $name }) -eq 0) { Ok "已登記$($t[1])（$($t[0])）" } else { Warn "還沒有登記$($t[1])：請執行 $($t[2])" }
    }
}

if ($failures.Count) { Say "==" ("有 {0} 個問題需要處理" -f $failures.Count) "Red" }
elseif ($warnings.Count) { Say "==" "系統正常（有 $($warnings.Count) 個建議）" "Yellow" }
else { Say "==" "全部正常" "Green" }

# 紀錄（保留最後 2000 行）：自動排程執行時看不到畫面，從這個檔案查
try {
    $old = @(); if (Test-Path $logPath) { $old = @(Get-Content $logPath -Encoding UTF8 | Select-Object -Last 2000) }
    [IO.File]::WriteAllLines($logPath, [string[]]($old + $log), (New-Object System.Text.UTF8Encoding $false))
} catch { }
if ($failures.Count) { exit 1 }
