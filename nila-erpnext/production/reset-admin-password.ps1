# 妮菈穿戴甲正式版：忘記最高管理員（Administrator）密碼時，重新設定密碼
# 只能在「安裝系統的那台電腦」上執行（需要能操作 Docker），所以別人無法從網路上用這個方法改密碼。
# 其他帳號忘記密碼：請管理員到「妮菈 → 帳號管理 → 重設密碼」，不需要這個腳本。
#
# 用法：powershell -ExecutionPolicy Bypass -File .\reset-admin-password.ps1
param(
    [string]$InstallDir = (Split-Path $PSScriptRoot -Parent),
    [string]$User = "Administrator"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "lib/NilaCommon.ps1")
$prodDir = Join-Path $InstallDir "production"
if (-not (Test-Path (Join-Path $prodDir "docker-compose.yml"))) { throw "在 $prodDir 找不到正式版，請用 -InstallDir 指定安裝位置。" }
Assert-Docker
$envValues = Get-NilaEnv -Path (Join-Path $prodDir ".env")
$site = $envValues["SITE_NAME"]; if (-not $site) { $site = "nila" }
$port = [int]$envValues["HTTP_PORT"]; if (-not $port) { $port = 8090 }

function Read-Plain([string]$prompt) {
    $sec = Read-Host $prompt -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
}

Write-Host "== 重新設定 $User 的密碼 ==" -ForegroundColor Cyan
Write-Host "密碼至少 10 個字，混合英文大小寫、數字或符號（輸入時畫面不會顯示）。"
$pw = Read-Plain "新密碼"
if ($pw.Length -lt 10) { throw "密碼太短（至少 10 個字），沒有變更。" }
if ((Read-Plain "再輸入一次") -cne $pw) { throw "兩次輸入的密碼不一樣，沒有變更。" }

Push-Location $prodDir
try {
    # 密碼經環境變數傳進容器，不會出現在指令或紀錄中
    $env:NILA_NEW_PASSWORD = $pw
    $env:NILA_RESET_USER = $User
    $out = (docker compose exec -T -e NILA_NEW_PASSWORD -e NILA_RESET_USER backend bench --site $site execute nila_app.setup.admin.reset_password) | Out-String
} finally {
    Remove-Item Env:NILA_NEW_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:NILA_RESET_USER -ErrorAction SilentlyContinue
    $pw = $null
    Pop-Location
}
if ($out -notmatch 'NILA_PASSWORD_OK') { throw "變更失敗：$out" }
Write-Host "✓ 已重新設定 $User 的密碼（帳號也確認為啟用，輸錯太多次的鎖定已解除）。請用新密碼登入：http://localhost:$port" -ForegroundColor Green
