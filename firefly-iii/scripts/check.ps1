# Firefly III 安裝檢查（唯讀，不會修改任何東西）
# 在 firefly-iii 資料夾開啟 PowerShell 後執行：
#   powershell -ExecutionPolicy Bypass -File scripts\check.ps1
$ErrorActionPreference = 'Continue'
$fail = 0
function Ok($m)   { Write-Host "[OK]   $m" -ForegroundColor Green }
function Bad($m)  { Write-Host "[FAIL] $m" -ForegroundColor Red; $script:fail++ }
function Info($m) { Write-Host "[INFO] $m" -ForegroundColor Cyan }

# 1. Docker
if (Get-Command docker -ErrorAction SilentlyContinue) {
  docker info *> $null
  if ($LASTEXITCODE -eq 0) { Ok 'Docker 已安裝且正在執行' }
  else { Bad 'Docker 已安裝但沒有執行 -> 請先開啟 Docker Desktop' }
} else { Bad '找不到 docker -> 請安裝 Docker Desktop for Windows' }

# 2. 設定檔
foreach ($f in '.env', '.db.env', '.importer.env') {
  if (-not (Test-Path $f)) { Bad "缺少 $f -> 請從 $f.example 複製" ; continue }
  $text = Get-Content $f -Raw
  if ($text -match 'REPLACE_WITH') { Bad "$f 還有 REPLACE_WITH 占位字串沒改" }
  else { Ok "$f 已填寫" }
}
if (Test-Path '.env') {
  $env_ = Get-Content '.env'
  $key  = ($env_ | Where-Object { $_ -match '^APP_KEY=' }) -replace '^APP_KEY=', ''
  $tok  = ($env_ | Where-Object { $_ -match '^STATIC_CRON_TOKEN=' }) -replace '^STATIC_CRON_TOKEN=', ''
  if ($key.Length -eq 32) { Ok 'APP_KEY 長度正確 (32)' } else { Bad "APP_KEY 必須剛好 32 字元（目前 $($key.Length)）" }
  if ($tok.Length -eq 32) { Ok 'STATIC_CRON_TOKEN 長度正確 (32)' } else { Bad "STATIC_CRON_TOKEN 必須剛好 32 字元（目前 $($tok.Length)）" }
  $dbp  = ($env_ | Where-Object { $_ -match '^DB_PASSWORD=' }) -replace '^DB_PASSWORD=', ''
  if (Test-Path '.db.env') {
    $mp = ((Get-Content '.db.env') | Where-Object { $_ -match '^MYSQL_PASSWORD=' }) -replace '^MYSQL_PASSWORD=', ''
    if ($dbp -eq $mp -and $dbp) { Ok '.env 與 .db.env 的資料庫密碼一致' } else { Bad '.env 的 DB_PASSWORD 與 .db.env 的 MYSQL_PASSWORD 不一致' }
  }
}
if (Test-Path '.importer.env') {
  $t = ((Get-Content '.importer.env') | Where-Object { $_ -match '^FIREFLY_III_ACCESS_TOKEN=' }) -replace '^FIREFLY_III_ACCESS_TOKEN=', ''
  if ($t) { Ok '匯入工具的存取權杖已填寫' } else { Info '匯入工具的存取權杖還沒填（README 第 2 步第 7 項；匯入 CSV 前必填）' }
}

# 3. 容器
$running = @()
if (Get-Command docker -ErrorAction SilentlyContinue) { $running = docker ps --format '{{.Names}}' 2>$null }
foreach ($c in 'firefly_iii_core', 'firefly_iii_db', 'firefly_iii_importer', 'firefly_iii_cron') {
  if ($running -contains $c) { Ok "容器執行中：$c" } else { Bad "容器沒有執行：$c -> docker compose up -d" }
}

# 4. 網頁是否回應
foreach ($p in @(@(8080, 'Firefly III'), @(8081, '匯入工具'))) {
  try {
    $r = Invoke-WebRequest -Uri "http://localhost:$($p[0])" -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 5
    Ok "$($p[1]) 在 http://localhost:$($p[0]) 有回應 (HTTP $($r.StatusCode))"
  } catch { Bad "$($p[1]) 在 http://localhost:$($p[0]) 沒有回應：$($_.Exception.Message)" }
}

# 5. 區網位址（手機在家用）
$ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
  Where-Object { $_.IPAddress -match '^(192\.168|10\.|172\.(1[6-9]|2\d|3[01]))\.' -and $_.InterfaceAlias -notmatch 'vEthernet|WSL|Loopback' }
foreach ($i in $ips) { Info "手機（同一個 Wi-Fi）可試：http://$($i.IPAddress):8080" }
$ts = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -match '^100\.' }
foreach ($i in $ts) { Info "Tailscale 位址（外出用）：http://$($i.IPAddress):8080" }

Write-Host ''
if ($fail -eq 0) { Write-Host '全部檢查通過（電腦端）。手機端請照 README 的「安裝檢查清單」確認。' -ForegroundColor Green }
else { Write-Host "有 $fail 項失敗，請依 [FAIL] 的提示處理後重新執行。" -ForegroundColor Red; exit 1 }
