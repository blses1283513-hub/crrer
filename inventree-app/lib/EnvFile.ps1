# .env 檔案編輯工具（setup-server.ps1 使用，並由 tests/powershell 自動測試）
# Set-EnvContent：在文字中設定 KEY=VALUE。已有「未註解」的同名設定就取代第一個，沒有就附加在最後。
# 註解行（#KEY=...）不會被改動；保留原本的換行格式（LF 或 CRLF）。

function Set-EnvContent {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyString()][string]$Text,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Settings
    )
    $nl = if ($Text.Contains("`r`n")) { "`r`n" } else { "`n" }
    foreach ($kv in $Settings.GetEnumerator()) {
        $line = "$($kv.Key)=$($kv.Value)"
        $re = [regex]("(?m)^" + [regex]::Escape($kv.Key) + "=[^\r\n]*")
        if ($re.IsMatch($Text)) {
            $evaluator = [System.Text.RegularExpressions.MatchEvaluator] { param($m) $line }.GetNewClosure()
            $Text = $re.Replace($Text, $evaluator, 1)
        } else {
            $Text = $Text.TrimEnd() + $nl + $line + $nl
        }
    }
    return $Text
}

function Set-EnvFile {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][System.Collections.IDictionary]$Settings
    )
    $text = [IO.File]::ReadAllText($Path)
    $new = Set-EnvContent -Text $text -Settings $Settings
    [IO.File]::WriteAllText($Path, $new, (New-Object System.Text.UTF8Encoding $false))
}

# Get-EnvValues：讀取 .env 的 KEY=VALUE（略過註解；去掉前後引號），回傳 Hashtable。
function Get-EnvValues {
    param([Parameter(Mandatory = $true)][string]$Path)
    $values = @{}
    foreach ($line in [IO.File]::ReadAllLines($Path)) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') {
            $values[$Matches[1]] = $Matches[2].Trim('"', "'")
        }
    }
    return $values
}
