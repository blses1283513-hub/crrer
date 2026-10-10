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

if ($script:failed) { Write-Host "$script:failed 項失敗" -ForegroundColor Red; exit 1 }
Write-Host "全部通過" -ForegroundColor Green
