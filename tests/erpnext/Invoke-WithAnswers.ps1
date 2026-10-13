# 以自動輸入執行互動式腳本（供自動測試使用；實際使用時由人輸入）
# 以同名函式取代 Read-Host：依序回答環境變數 NILA_ANSWERS 中的每一行；-AsSecureString 時轉成 SecureString
# 用法：NILA_ANSWERS=$'密碼\n密碼\nY' pwsh -File tests/erpnext/Invoke-WithAnswers.ps1 -Script <腳本> -InstallDir <資料夾> …
param(
    [Parameter(Mandatory = $true)][string]$Script,
    [Parameter(ValueFromRemainingArguments = $true)]$ScriptArgs
)
$global:answers = [System.Collections.Queue]::new()
if ($env:NILA_ANSWERS) { foreach ($a in ($env:NILA_ANSWERS -split "`n")) { $global:answers.Enqueue($a.TrimEnd("`r")) } }
function global:Read-Host {
    param([string]$Prompt, [switch]$AsSecureString)
    if ($global:answers.Count -eq 0) { throw "自動輸入已用完（提示：$Prompt）" }
    $v = $global:answers.Dequeue()
    Write-Host "$Prompt> (自動輸入)"
    if ($AsSecureString) { return (ConvertTo-SecureString $v -AsPlainText -Force) }
    return $v
}
$splat = @{}
for ($i = 0; $i -lt $ScriptArgs.Count; $i++) {
    $k = [string]$ScriptArgs[$i]
    if ($k.StartsWith('-')) {
        $name = $k.TrimStart('-').TrimEnd(':')
        if ($i + 1 -lt $ScriptArgs.Count -and -not ([string]$ScriptArgs[$i + 1]).StartsWith('-')) { $splat[$name] = $ScriptArgs[$i + 1]; $i++ }
        else { $splat[$name] = $true }
    }
}
& $Script @splat
if (-not $?) { exit 1 }
