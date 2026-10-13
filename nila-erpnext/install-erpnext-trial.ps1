# 妮菈穿戴甲：ERPNext 16 試用版一鍵安裝（Windows PowerShell）
# 安裝 ERPNext、完成初次設定（公司、台灣、新台幣、繁體中文），並匯入範例款式、期初庫存與「−2 → 補 12」的訂單情境。
# 只供試用；資料放在 Docker 的資料卷中，與原本的 InvenTree 完全分開（埠號 8080，不影響 InvenTree 的 80 埠）。
#
# 用法（在 nila-erpnext 資料夾中）：
#   powershell -ExecutionPolicy Bypass -File .\install-erpnext-trial.ps1
#   powershell -ExecutionPolicy Bypass -File .\install-erpnext-trial.ps1 -InstallDir D:\nila-erpnext-trial -Port 8081
# 中途失敗時，直接再執行一次即可（會沿用已設定的密碼，已建立的資料不會重複建立）。
param(
    [string]$InstallDir = (Join-Path $HOME "nila-erpnext-trial"),
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$here = $PSScriptRoot
$utf8NoBom = New-Object System.Text.UTF8Encoding $false

Write-Host "== 妮菈穿戴甲：ERPNext 16 試用版安裝 ==" -ForegroundColor Cyan

# ---------- 檢查 ----------
foreach ($f in @("docker-compose.yml", "seed/seed_trial.py", "seed/verify_trial.py", "seed/sample-skus.csv", "seed/shapes.csv", "seed/terms.csv")) {
    if (-not (Test-Path (Join-Path $here $f))) { throw "缺少 $f，請下載完整的 nila-erpnext 資料夾。" }
}
try { docker version --format '{{.Server.Version}}' | Out-Null } catch { throw "找不到執行中的 Docker。請先啟動 Docker Desktop（右下角鯨魚圖示不再轉動）再執行。" }
if ($LASTEXITCODE -ne 0) { throw "找不到執行中的 Docker。請先啟動 Docker Desktop 再執行。" }

$envPath = Join-Path $InstallDir ".env"
$resume = Test-Path $envPath
$portBusy = $false
try { $portBusy = [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) } catch { }
if ($portBusy -and -not $resume) { throw "埠 $Port 已被其他程式使用。請改用其他埠，例如：-Port 8081" }

# 映像約 7 GB（下載約 1.4 GB），加上資料庫，建議至少 15 GB 可用空間
$sysDrive = if ($env:SystemDrive) { $env:SystemDrive.TrimEnd(":") } else { (Get-Location).Drive.Name }
$drive = Get-PSDrive $sysDrive
if ($drive.Free -lt 15GB) { Write-Host ("⚠ {0} 槽只剩 {1:N1} GB，ERPNext 映像約 7 GB，建議至少 15 GB。" -f $drive.Name, ($drive.Free / 1GB)) -ForegroundColor Yellow }
$mem = 0
try { $mem = [int64](docker info --format '{{.MemTotal}}') } catch { }
if ($mem -gt 0 -and $mem -lt 4GB) { Write-Host ("⚠ Docker 可用記憶體只有 {0:N1} GB，ERPNext 建議至少 4 GB（Docker Desktop → Settings → Resources）。" -f ($mem / 1GB)) -ForegroundColor Yellow }

# ---------- 密碼 ----------
if (-not $resume) {
    Write-Host ""
    Write-Host "請設定試用版管理員（Administrator）的密碼：至少 8 個字元，不可包含單引號 '。"
    $p1 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host "管理員密碼" -AsSecureString)))
    $p2 = [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host "再輸入一次" -AsSecureString)))
    if ($p1 -ne $p2) { throw "兩次輸入的密碼不同，請重新執行。" }
    if ($p1.Length -lt 8 -or $p1.Contains("'")) { throw "密碼至少 8 個字元，且不可包含單引號 '。請重新執行。" }
    $dbPass = [guid]::NewGuid().ToString("N")
}

# ---------- 列出變更，等待確認 ----------
Write-Host ""
Write-Host "將進行以下動作（安裝位置：$InstallDir）：" -ForegroundColor Yellow
if ($resume) { Write-Host "  · 偵測到先前的安裝設定，沿用原本的密碼與埠號，從中斷處繼續" }
else {
    Write-Host "  1. 建立資料夾並寫入 .env（管理員密碼、隨機產生的資料庫密碼、埠號 $Port）"
}
Write-Host "  2. 複製 docker-compose.yml 與範例資料"
Write-Host "  3. 下載 ERPNext 16（約 1.4 GB，第一次需要 5–20 分鐘）並啟動；建立網站約 3–5 分鐘"
Write-Host "  4. 完成初次設定：公司「妮菈穿戴甲（試用）」、台灣、新台幣、台北時區、繁體中文"
Write-Host "  5. 匯入範例：3 種甲型、10 個款式、72 個規格、5 個公司倉庫與在途倉、期初庫存、用語修正"
Write-Host "  6. 建立情境：官網訂單 5 件 0001-LT-M（總公司 2、分公司A 1）→ 應顯示建議補貨 12"
Write-Host "  原本的 InvenTree 不受影響。"
Write-Host ""
$ok = Read-Host "確定執行？(Y/N)"
if ($ok -notmatch '^[Yy]') { Write-Host "已取消，未做任何變更。"; exit 0 }

# ---------- 1–2. 檔案 ----------
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
if (-not $resume) {
    # 值以單引號包住：Docker Compose 照字面讀取，密碼中的 $ " 空白 都不會被解析
    $envText = "ADMIN_PASSWORD='$p1'`nDB_ROOT_PASSWORD='$dbPass'`nHTTP_PORT=$Port`n"
    [IO.File]::WriteAllText($envPath, $envText, $utf8NoBom)
    $p1 = $null; $p2 = $null
}
Copy-Item (Join-Path $here "docker-compose.yml") $InstallDir -Force
$seedDir = Join-Path $InstallDir "seed"
New-Item -ItemType Directory -Force -Path $seedDir | Out-Null
Copy-Item (Join-Path $here "seed/*") $seedDir -Force
$Port = [int](((Get-Content $envPath) | Where-Object { $_ -match '^HTTP_PORT=' }) -replace '^HTTP_PORT=', '')
Write-Host "✓ 設定與檔案已放置"

# ---------- 3. 下載與啟動 ----------
Push-Location $InstallDir
try {
    Write-Host "下載並啟動 ERPNext（第一次較久，請耐心等候）…"
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw "啟動失敗。若訊息含「429 Too Many Requests」，代表 Docker Hub 暫時限制下載次數，等 30 分鐘後再執行一次即可。" }

    $deadline = (Get-Date).AddMinutes(25)
    do {
        Start-Sleep -Seconds 10
        $state = (docker compose ps -a create-site --format '{{.State}} {{.ExitCode}}') | Select-Object -First 1
        Write-Host ("  建立網站中… {0}" -f $state)
    } until (($state -match '^exited') -or (Get-Date) -gt $deadline)
    if ($state -notmatch '^exited 0') {
        docker compose logs --tail 30 create-site
        throw "建立網站失敗或逾時（$state）。請把上方訊息交給協助的人；修正後可直接再執行本腳本。"
    }

    $deadline = (Get-Date).AddMinutes(5)
    do {
        Start-Sleep -Seconds 3
        try { $pong = (Invoke-WebRequest "http://localhost:$Port/api/method/ping" -UseBasicParsing -TimeoutSec 5).Content -match 'pong' } catch { $pong = $false }
    } until ($pong -or (Get-Date) -gt $deadline)
    if (-not $pong) { throw "ERPNext 沒有回應。請執行 docker compose ps 與 docker compose logs --tail 50 backend 查看。" }
    Write-Host "✓ ERPNext 已啟動"

    # ---------- 4–6. 初次設定與範例資料（在 ERPNext 容器內執行，不需要電腦上的 Python） ----------
    Write-Host "初次設定與匯入範例資料（約 1–3 分鐘）…"
    docker compose cp seed/. backend:/tmp/nila-seed
    if ($LASTEXITCODE -ne 0) { throw "無法把範例資料複製到容器。" }
    docker compose exec -T -w /home/frappe/frappe-bench/sites backend /home/frappe/frappe-bench/env/bin/python /tmp/nila-seed/seed_trial.py --site frontend --csv /tmp/nila-seed/sample-skus.csv --shapes /tmp/nila-seed/shapes.csv --terms /tmp/nila-seed/terms.csv
    if ($LASTEXITCODE -ne 0) { throw "匯入範例資料失敗（見上方訊息）。修正後可直接再執行本腳本，已建立的資料不會重複。" }
} finally { Pop-Location }

Write-Host ""
Write-Host "完成！" -ForegroundColor Green
Write-Host "  網址：http://localhost:$Port"
Write-Host "  帳號：Administrator　密碼：你剛才設定的密碼"
Write-Host "  下一步：照 nila-erpnext\trial-checklist.md 操作。"
Write-Host "  自動驗證 13 項功能（會建立測試單據，只需做一次）：powershell -ExecutionPolicy Bypass -File .\verify-erpnext-trial.ps1"
Write-Host "  停止：在 $InstallDir 執行 docker compose stop　　完全移除（資料會消失）：docker compose down -v"
try { Start-Process "http://localhost:$Port" } catch { }
