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

if ($script:failed) { Write-Host "$script:failed 項失敗" -ForegroundColor Red; exit 1 }
Write-Host "全部通過" -ForegroundColor Green
