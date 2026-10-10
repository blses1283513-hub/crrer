# PowerShell 腳本的自動檢查（Linux/macOS 的 pwsh 或 Windows 皆可執行）
# 1. 所有 .ps1 語法正確
# 2. 含中文的 .ps1 都有 UTF-8 BOM（Windows PowerShell 5.1 沒有 BOM 會把中文讀錯）
# 3. .env 編輯邏輯：對官方 1.5.6 .env 正確、可重複執行、保留註解與其他設定、支援 CRLF
# 執行：pwsh -NoProfile -File tests/powershell/Test-Scripts.ps1
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$script:failed = 0
function Check([bool]$cond, [string]$name) {
    if ($cond) { Write-Host "ok   $name" } else { Write-Host "FAIL $name" -ForegroundColor Red; $script:failed++ }
}

$scripts = Get-ChildItem -Path $root -Recurse -Filter *.ps1 | Where-Object { $_.FullName -notmatch '[\\/](node_modules|\.git)[\\/]' -and $_.FullName -notmatch '_backup-' }
Check ($scripts.Count -ge 7) "找到 PowerShell 腳本（$($scripts.Count) 個）"
foreach ($f in $scripts) {
    $tok = $null; $err = $null
    [System.Management.Automation.Language.Parser]::ParseFile($f.FullName, [ref]$tok, [ref]$err) | Out-Null
    Check ($err.Count -eq 0) "語法：$($f.Name) $(($err | ForEach-Object { "L$($_.Extent.StartLineNumber) $($_.Message)" }) -join '; ')"
    $bytes = [IO.File]::ReadAllBytes($f.FullName)
    $hasBom = $bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
    $hasNonAscii = [bool]($bytes | Where-Object { $_ -gt 127 } | Select-Object -First 1)
    Check ((-not $hasNonAscii) -or $hasBom) "UTF-8 BOM：$($f.Name)"
}

. (Join-Path $root "inventree-app/lib/EnvFile.ps1")
$fixture = [IO.File]::ReadAllText((Join-Path $root "tests/fixtures/inventree-1.5.6/.env"))
$settings = [ordered]@{
    "INVENTREE_SITE_URL"        = '"http://192.168.1.20"'
    "INVENTREE_ALLOWED_HOSTS"   = '"192.168.1.20,localhost,127.0.0.1"'
    "INVENTREE_TRUSTED_ORIGINS" = '"http://192.168.1.20,http://localhost,http://127.0.0.1"'
    "INVENTREE_LANGUAGE"        = "zh-hant"
}
$once = Set-EnvContent -Text $fixture -Settings $settings
$twice = Set-EnvContent -Text $once -Settings $settings
Check ($once -eq $twice) ".env：重複執行結果相同"
foreach ($kv in $settings.GetEnumerator()) {
    $n = ([regex]::Matches($once, "(?m)^$([regex]::Escape($kv.Key))=")).Count
    Check ($n -eq 1) ".env：$($kv.Key) 只出現一次（實際 $n）"
    Check ($once -match "(?m)^$([regex]::Escape($kv.Key))=$([regex]::Escape($kv.Value))\s*$") ".env：$($kv.Key) 值正確"
}
Check ($once -match '(?m)^#INVENTREE_SITE_URL="http://inventree.localhost"') ".env：註解的範例行保持不變"
$strip = { param($t) ($t -split "`r?`n" | Where-Object { $_ -notmatch '^(INVENTREE_SITE_URL|INVENTREE_ALLOWED_HOSTS|INVENTREE_TRUSTED_ORIGINS|INVENTREE_LANGUAGE)=' -and $_ -ne '' }) -join "`n" }
Check ((& $strip $fixture) -eq (& $strip $once)) ".env：其他設定完全不變"

$crlf = $fixture -replace "`r?`n", "`r`n"
$crlfOut = Set-EnvContent -Text $crlf -Settings $settings
Check (-not ($crlfOut -match "[^`r]`n")) ".env：CRLF 檔案維持 CRLF"
Check ($crlfOut -match "(?m)^INVENTREE_SITE_URL=`"http://192.168.1.20`"`r$") ".env：CRLF 取代後行尾正確"

$tmp = Join-Path ([IO.Path]::GetTempPath()) ("envtest-" + [guid]::NewGuid().ToString("N"))
[IO.File]::WriteAllText($tmp, $fixture)
Set-EnvFile -Path $tmp -Settings $settings
$bytes = [IO.File]::ReadAllBytes($tmp)
Check (-not ($bytes[0] -eq 0xEF)) ".env：寫回時不加 BOM（Docker Compose 才讀得到第一行）"
Remove-Item $tmp

# ---- 通知服務設定產生 ----
. (Join-Path $root "inventree-app/lib/NotifierConfig.ps1")
$seedCfg = Join-Path $root "inventree-seed/config.example.json"
$tpl = Join-Path $root "inventree-app/notifier/config.example.json"
$cfgText = New-NotifierConfigJson -SeedConfigPath $seedCfg -TemplatePath $tpl
$cfg = $cfgText | ConvertFrom-Json
Check (@($cfg.companies).Count -eq 3) "通知設定：3 間公司"
Check (($cfg.companies | ForEach-Object { "$($_.code)|$($_.name)|$($_.group)" }) -join ";" -eq "A|A 公司|company-A;B|B 公司|company-B;C|C 公司|company-C") "通知設定：公司、代碼、群組與匯入設定一致"
Check ($cfg.large_qty -eq 100) "通知設定：沿用範本的其他欄位"

$tmpDir = Join-Path ([IO.Path]::GetTempPath()) ("notifytest-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmpDir | Out-Null
$existing = Join-Path $tmpDir "config.json"
Write-Utf8NoBom -Path $existing -Text '{"companies":[{"code":"Z","name":"舊公司","group":"old"}],"large_qty":250,"superuser_sees_all":false}'
$again = New-NotifierConfigJson -SeedConfigPath $seedCfg -TemplatePath $tpl -ExistingPath $existing | ConvertFrom-Json
Check ($again.large_qty -eq 250 -and $again.superuser_sees_all -eq $false) "通知設定：重新產生時保留自行調整的欄位"
Check (@($again.companies).Count -eq 3 -and $again.companies[0].code -eq "A") "通知設定：公司一律依匯入設定更新"

$oneSeed = Join-Path $tmpDir "one.json"
Write-Utf8NoBom -Path $oneSeed -Text '{"companies":[{"code":"K","name":"K 公司","owner_group":"company-K"}]}'
$oneText = New-NotifierConfigJson -SeedConfigPath $oneSeed -TemplatePath $tpl
Check ($oneText -match '"companies":\s*\[') "通知設定：只有一間公司時仍輸出為陣列（PowerShell 5.1 容易變成物件）"

$out = Join-Path $tmpDir "out.json"
Write-Utf8NoBom -Path $out -Text $cfgText
$bytes = [IO.File]::ReadAllBytes($out)
Check ($bytes[0] -ne 0xEF) "通知設定：寫檔不含 BOM"
Check ([Text.Encoding]::UTF8.GetString($bytes).Contains("A 公司")) "通知設定：中文完整保留"
$py = @("python3", "python") | Where-Object { Get-Command $_ -ErrorAction SilentlyContinue } | Select-Object -First 1
if ($py) {
    & $py -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8-sig')); assert [c['group'] for c in d['companies']]==['company-A','company-B','company-C'], d" $out
    Check ($LASTEXITCODE -eq 0) "通知設定：Python 可讀取 PowerShell 產生的檔案"
} else { Write-Host "skip 找不到 Python，略過跨語言讀取檢查" }

$ev = Get-EnvValues -Path (Join-Path $root "tests/fixtures/inventree-1.5.6/.env")
Check ($ev["INVENTREE_WEB_PORT"] -eq "8000") "Get-EnvValues：讀到埠號"
Check ($ev["INVENTREE_SITE_URL"] -eq "http://localhost") "Get-EnvValues：去掉引號、忽略註解行"
Check (-not $ev.ContainsKey("#INVENTREE_ADMIN_USER")) "Get-EnvValues：不把註解行當設定"
Remove-Item $tmpDir -Recurse -Force

# ---- 管理看板外掛：.env、公司清單、放置檔案、容器內啟用 ----
. (Join-Path $root "inventree-app/lib/DashboardPlugin.ps1")
$d1 = Get-DashboardEnvSettings -Current @{}
Check ($d1["INVENTREE_PLUGINS_ENABLED"] -eq "True" -and $d1["INVENTREE_PLUGINS_MANDATORY"] -eq "mgmt-dashboard") "看板 .env：開啟外掛並設為必要外掛"
$d2 = Get-DashboardEnvSettings -Current @{ INVENTREE_PLUGINS_MANDATORY = "foo, bar" }
Check ($d2["INVENTREE_PLUGINS_MANDATORY"] -eq "foo,bar,mgmt-dashboard") "看板 .env：保留原有的必要外掛"
$d3 = Get-DashboardEnvSettings -Current @{ INVENTREE_PLUGINS_MANDATORY = "mgmt-dashboard,foo" }
Check ($d3["INVENTREE_PLUGINS_MANDATORY"] -eq "mgmt-dashboard,foo") "看板 .env：已列入時不重複"
$envOnce = Set-EnvContent -Text $fixture -Settings $d1
$envTwice = Set-EnvContent -Text $envOnce -Settings (Get-DashboardEnvSettings -Current @{ INVENTREE_PLUGINS_MANDATORY = "mgmt-dashboard" })
Check ($envOnce -eq $envTwice) "看板 .env：重複執行結果相同"
Check (([regex]::Matches($envOnce, '(?m)^INVENTREE_PLUGINS_ENABLED=')).Count -eq 1 -and $envOnce -match '(?m)^INVENTREE_PLUGINS_ENABLED=True\s*$') "看板 .env：取代官方 .env 原有的 INVENTREE_PLUGINS_ENABLED"

$dashTmp = Join-Path ([IO.Path]::GetTempPath()) ("dashtest-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $dashTmp | Out-Null
$cj = New-DashboardCompaniesJson -ConfigPath $seedCfg | ConvertFrom-Json
Check ((@($cj.companies) | ForEach-Object { "$($_.name)|$($_.code)" }) -join ";" -eq "A 公司|A;B 公司|B;C 公司|C") "看板公司清單：取自匯入設定"
$notifyCfg = Join-Path $dashTmp "notify.json"
Write-Utf8NoBom -Path $notifyCfg -Text '{"companies":[{"code":"K","name":"K 公司","group":"company-K"}],"large_qty":100}'
$oneDash = New-DashboardCompaniesJson -ConfigPath $notifyCfg
Check ($oneDash -match '"companies":\s*\[' -and $oneDash.Contains("K 公司")) "看板公司清單：通知設定也可用；一間公司仍為陣列"
$threw = $false; try { Write-Utf8NoBom -Path $notifyCfg -Text '{"companies":[]}'; New-DashboardCompaniesJson -ConfigPath $notifyCfg | Out-Null } catch { $threw = $true }
Check $threw "看板公司清單：沒有公司時停止"

$dataDir = Join-Path $dashTmp "inventree-data"
$pluginSrc = Join-Path $root "inventree-app/plugins/mgmt_dashboard"
$dest = Install-DashboardPluginFiles -SourceDir $pluginSrc -DataDir $dataDir -CompaniesJson $oneDash
Check ((Test-Path (Join-Path $dest "__init__.py")) -and (Test-Path (Join-Path $dest "static/mgmt_dashboard.js"))) "看板外掛：放到 inventree-data/plugins/mgmt_dashboard"
Check ((Split-Path $dest -Leaf) -eq "mgmt_dashboard" -and (Split-Path (Split-Path $dest -Parent) -Leaf) -eq "plugins") "看板外掛：資料夾位置與 InvenTree 的外掛資料夾一致"
$cbytes = [IO.File]::ReadAllBytes((Join-Path $dest "companies.json"))
Check ($cbytes[0] -ne 0xEF -and [Text.Encoding]::UTF8.GetString($cbytes).Contains("K 公司")) "看板外掛：companies.json 無 BOM、中文完整"
$threw = $false; try { Install-DashboardPluginFiles -SourceDir $dashTmp -DataDir $dataDir | Out-Null } catch { $threw = $true }
Check $threw "看板外掛：來源不完整時停止"
if ($py) {
    & $py -I -c "import json,sys; d=json.load(open(sys.argv[1],encoding='utf-8')); assert d['companies']==[{'name':'K 公司','code':'K'}], d" (Join-Path $dest "companies.json")
    Check ($LASTEXITCODE -eq 0) "看板外掛：Python 讀得到 PowerShell 產生的公司清單"
}

$code = Get-DashboardActivateScript
Check (-not ([Text.Encoding]::UTF8.GetBytes($code) | Where-Object { $_ -gt 127 } | Select-Object -First 1)) "看板啟用程式：只含 ASCII（PowerShell 5.1 傳送不會變亂碼）"
if ($py) {
    $codeFile = Join-Path $dashTmp "activate.py"
    [IO.File]::WriteAllText($codeFile, $code)
    & $py -I -c "import sys; compile(open(sys.argv[1]).read(), 'activate', 'exec')" $codeFile
    Check ($LASTEXITCODE -eq 0) "看板啟用程式：Python 語法正確"
}
Check ($null -eq (Get-DashboardActivateProblem -Output "MGMT_INTERFACE True`nMGMT_FOUND True True`nMGMT_STATIC True`nMGMT_OK")) "看板啟用結果：成功"
Check ((Get-DashboardActivateProblem -Output "MGMT_FOUND False False`nMGMT_FAIL") -match "沒有載入") "看板啟用結果：外掛未載入時說明原因"
Check ((Get-DashboardActivateProblem -Output "") -match "沒有收到") "看板啟用結果：沒有回應"

# 以替身 docker 驗證傳給容器的指令（參數不能含空白，程式由標準輸入傳入）
$global:dockerCalls = @()
function docker { $global:dockerCalls += , @{ args = @($args); stdin = (@($input) -join "`n") }; "MGMT_OK" }
$fakeInstall = Join-Path $dashTmp "inst"; New-Item -ItemType Directory -Path $fakeInstall | Out-Null
$res = Invoke-DashboardActivate -InstallDir $fakeInstall -Retries 1
Check ($null -eq $res) "看板啟用：成功時回傳 null"
$call = $global:dockerCalls[0]
Check (($call.args -join " ") -eq "compose exec -T -w /home/inventree/src/backend/InvenTree inventree-server python3 manage.py shell --command=exec(__import__('sys').stdin.read())") "看板啟用：在 inventree-server 以 manage.py shell 執行"
Check (-not ($call.args | Where-Object { $_ -match '\s|"' })) "看板啟用：每個參數都不含空白或雙引號"
Check ($call.stdin.Contains("set_global_setting('ENABLE_PLUGINS_INTERFACE', True, None)") -and $call.stdin.Contains("copy_plugin_static_files(slug)")) "看板啟用：程式由標準輸入傳入"

# enable-dashboard.ps1 端對端（替身 docker 與網路）：模擬已安裝好的主機
$inst = Join-Path $dashTmp "host"; New-Item -ItemType Directory -Path (Join-Path $inst "app"), (Join-Path $inst "notifier") -Force | Out-Null
Copy-Item (Join-Path $root "tests/fixtures/inventree-1.5.6/.env") (Join-Path $inst ".env")
Copy-Item (Join-Path $root "tests/fixtures/inventree-1.5.6/docker-compose.yml") $inst
Copy-Item (Join-Path $root "inventree-app/docker-compose.override.yml") $inst
Set-Content -Path (Join-Path $inst "Caddyfile.app") -Value "old caddy"
Set-Content -Path (Join-Path $inst "app/inventree-ui-helper.user.js") -Value "old helper"
Write-Utf8NoBom -Path (Join-Path $inst "notifier/config.json") -Text '{"companies":[{"code":"Q","name":"Q 公司","group":"company-Q"}]}'
$global:dockerCalls = @()
function Invoke-WebRequest { [pscustomobject]@{ StatusCode = 200 } }
function Start-Sleep { }
$global:LASTEXITCODE = 0
& (Join-Path $root "inventree-app/enable-dashboard.ps1") -InstallDir $inst -Yes | Out-Null
$envAfter = [IO.File]::ReadAllText((Join-Path $inst ".env"))
Check ($envAfter -match '(?m)^INVENTREE_PLUGINS_MANDATORY=mgmt-dashboard\s*$' -and $envAfter -match '(?m)^INVENTREE_PLUGINS_ENABLED=True\s*$') "enable-dashboard：.env 已設定"
Check (@(Get-ChildItem $inst -Force -Filter ".env.bak-*").Count -eq 1 -and @(Get-ChildItem $inst -Filter "Caddyfile.app.bak-*").Count -eq 1 -and @(Get-ChildItem (Join-Path $inst "app") -Filter "*.bak-*").Count -eq 1) "enable-dashboard：.env、Caddyfile.app、操作助手都有備份"
Check ([IO.File]::ReadAllText((Join-Path $inst "Caddyfile.app")).Contains('header /plugins/* Cache-Control "no-cache"')) "enable-dashboard：Caddyfile.app 已更新"
Check ([IO.File]::ReadAllText((Join-Path $inst "app/inventree-ui-helper.user.js")).Contains("TEXT_FIXES")) "enable-dashboard：操作助手已更新（翻譯修正）"
$instPlugin = Join-Path $inst "inventree-data/plugins/mgmt_dashboard"
Check ((Test-Path (Join-Path $instPlugin "static/mgmt_dashboard.js")) -and [IO.File]::ReadAllText((Join-Path $instPlugin "companies.json")).Contains("Q 公司")) "enable-dashboard：外掛已放置，公司清單取自通知設定"
$seq = ($global:dockerCalls | ForEach-Object { ($_.args | Select-Object -First 3) -join " " }) -join " | "
Check ($seq -eq "compose up -d | compose restart inventree-server | compose exec -T") "enable-dashboard：啟動 → 重新啟動 → 容器內啟用（實際 $seq）"
Check (($global:dockerCalls[1].args -join " ") -eq "compose restart inventree-server inventree-worker inventree-proxy") "enable-dashboard：重新啟動伺服器、背景工作與代理（套用外掛與 Caddyfile）"
Remove-Item function:docker, function:Invoke-WebRequest, function:Start-Sleep
Remove-Item $dashTmp -Recurse -Force

if ($script:failed) { Write-Host "$script:failed 項失敗" -ForegroundColor Red; exit 1 }
Write-Host "全部通過" -ForegroundColor Green
