# 以自動輸入執行 install-erpnext-trial.ps1（供自動測試使用；真實使用時由人輸入密碼並確認）
# 以同名函式取代 Read-Host：依序回答「管理員密碼、再輸入一次、確定執行」；續裝時只回答「確定執行」
# 用法：pwsh -File tests/erpnext/Run-TrialInstall.ps1 -InstallDir <資料夾> -Password <密碼> [-Resume]
param([Parameter(Mandatory = $true)][string]$InstallDir, [string]$Password = 'Pa$$ "w0rd x', [switch]$Resume)
$global:answers = [System.Collections.Queue]::new()
if (-not $Resume) { $global:answers.Enqueue($Password); $global:answers.Enqueue($Password) }
$global:answers.Enqueue('Y')
function global:Read-Host {
    param([string]$Prompt, [switch]$AsSecureString)
    $v = $global:answers.Dequeue()
    Write-Host "$Prompt> (自動輸入)"
    if ($AsSecureString) { return (ConvertTo-SecureString $v -AsPlainText -Force) }
    return $v
}
& (Join-Path $PSScriptRoot "../../nila-erpnext/install-erpnext-trial.ps1") -InstallDir $InstallDir
if (-not $?) { exit 1 }
