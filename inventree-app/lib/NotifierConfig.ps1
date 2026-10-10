# 通知服務設定檔產生工具（setup-server.ps1 使用，並由 tests/powershell 自動測試）
# New-NotifierConfigJson：以匯入腳本的公司設定（inventree-seed\config.json）為準，產生通知服務的設定。
#   - 公司（companies）一律依匯入設定重新產生：code 用於判斷料號屬於哪間公司、group 是公司群組
#   - 若已有既存的通知設定，保留其他欄位（例如自行調整的 large_qty），只更新公司
# 輸出為 JSON 字串；請以「無 BOM 的 UTF-8」寫檔（Write-Utf8NoBom）。

function New-NotifierConfigJson {
    param(
        [Parameter(Mandatory = $true)][string]$SeedConfigPath,
        [Parameter(Mandatory = $true)][string]$TemplatePath,
        [string]$ExistingPath
    )
    $seed = Get-Content -Raw -Encoding UTF8 -Path $SeedConfigPath | ConvertFrom-Json
    if (-not $seed.companies -or @($seed.companies).Count -eq 0) { throw "$SeedConfigPath 沒有任何公司（companies）。" }
    $companies = @($seed.companies | ForEach-Object {
        if (-not $_.code -or -not $_.name -or -not $_.owner_group) { throw "$SeedConfigPath 的公司需要 code、name、owner_group。" }
        [ordered]@{ code = [string]$_.code; name = [string]$_.name; group = [string]$_.owner_group }
    })
    $source = if ($ExistingPath -and (Test-Path $ExistingPath)) { $ExistingPath } else { $TemplatePath }
    $cfg = Get-Content -Raw -Encoding UTF8 -Path $source | ConvertFrom-Json
    $cfg | Add-Member -NotePropertyName companies -NotePropertyValue $companies -Force
    return ($cfg | ConvertTo-Json -Depth 6)
}

function Write-Utf8NoBom {
    param([Parameter(Mandatory = $true)][string]$Path, [Parameter(Mandatory = $true)][string]$Text)
    [IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding $false))
}
