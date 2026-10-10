# 管理看板外掛（plugins\mgmt_dashboard）的安裝工具：setup-server.ps1 與 enable-dashboard.ps1 共用，並由 tests/powershell 自動測試。
#
# InvenTree 1.5.6 載入外掛的方式（已對照原始碼）：
#   - 外掛資料夾：容器內 INVENTREE_PLUGIN_DIR = /home/inventree/data/plugins，也就是主機的 inventree-data\plugins
#   - .env 需 INVENTREE_PLUGINS_ENABLED=True；INVENTREE_PLUGINS_MANDATORY 列入本外掛後，每次啟動都會自動啟用
#   - 系統設定 ENABLE_PLUGINS_INTERFACE（介面整合）要開啟，儀表板才會向外掛要小工具
#   - 外掛的 JS 要複製到 static\plugins\mgmt-dashboard\ 才讀得到（copy_plugin_static_files）

$DashboardSlug = 'mgmt-dashboard'
$DashboardDirName = 'mgmt_dashboard'

# 回傳要寫入 .env 的設定；保留 INVENTREE_PLUGINS_MANDATORY 原有的其他外掛
function Get-DashboardEnvSettings {
    param([System.Collections.IDictionary]$Current = @{})
    $existing = @()
    if ($Current.Contains('INVENTREE_PLUGINS_MANDATORY') -and $Current['INVENTREE_PLUGINS_MANDATORY']) {
        $existing = @(([string]$Current['INVENTREE_PLUGINS_MANDATORY']).Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    if ($existing -notcontains $DashboardSlug) { $existing += $DashboardSlug }
    return [ordered]@{
        'INVENTREE_PLUGINS_ENABLED'   = 'True'
        'INVENTREE_PLUGINS_MANDATORY' = ($existing -join ',')
    }
}

# 由匯入設定（inventree-seed\config.json）或通知服務設定（notifier\config.json）產生外掛的公司清單
function New-DashboardCompaniesJson {
    param([Parameter(Mandatory = $true)][string]$ConfigPath)
    $cfg = Get-Content -Raw -Encoding UTF8 -Path $ConfigPath | ConvertFrom-Json
    $list = @($cfg.companies | Where-Object { $_ -and $_.name })
    if ($list.Count -eq 0) { throw "$ConfigPath 沒有任何公司（companies）。" }
    $companies = @($list | ForEach-Object { [ordered]@{ name = [string]$_.name; code = [string]$_.code } })
    return (ConvertTo-Json -InputObject ([ordered]@{ companies = $companies }) -Depth 4)
}

# 把外掛放到 inventree-data\plugins\mgmt_dashboard（覆蓋程式檔；companies.json 另外寫）
function Install-DashboardPluginFiles {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,   # 含 __init__.py 與 static\mgmt_dashboard.js 的資料夾
        [Parameter(Mandatory = $true)][string]$DataDir,
        [string]$CompaniesJson
    )
    foreach ($f in @('__init__.py', 'static\mgmt_dashboard.js')) {
        if (-not (Test-Path (Join-Path $SourceDir $f))) { throw "管理看板外掛缺少 $f（$SourceDir）。" }
    }
    $dest = Join-Path (Join-Path $DataDir 'plugins') $DashboardDirName
    New-Item -ItemType Directory -Force -Path (Join-Path $dest 'static') | Out-Null
    Copy-Item (Join-Path $SourceDir '__init__.py') (Join-Path $dest '__init__.py') -Force
    Copy-Item (Join-Path $SourceDir 'static\mgmt_dashboard.js') (Join-Path $dest 'static\mgmt_dashboard.js') -Force
    if ($CompaniesJson) {
        [IO.File]::WriteAllText((Join-Path $dest 'companies.json'), $CompaniesJson, (New-Object System.Text.UTF8Encoding $false))
    }
    return $dest
}

# 在 InvenTree 容器內執行的 Python（只用 ASCII，避免 Windows PowerShell 5.1 以系統字碼頁傳送時變成亂碼）
function Get-DashboardActivateScript {
    return @"
slug = '$DashboardSlug'
ok = True
try:
    from common.settings import set_global_setting, get_global_setting
    set_global_setting('ENABLE_PLUGINS_INTERFACE', True, None)
    print('MGMT_INTERFACE', get_global_setting('ENABLE_PLUGINS_INTERFACE'))
except Exception as e:
    ok = False
    print('MGMT_ERR interface', e)
try:
    from plugin import registry
    from plugin.models import PluginConfig
    cfg = PluginConfig.objects.filter(key=slug).first()
    if cfg is not None and not cfg.active:
        cfg.active = True
        cfg.save()
    plg = registry.get_plugin(slug)
    print('MGMT_FOUND', plg is not None, cfg is not None and cfg.active)
    ok = ok and plg is not None
except Exception as e:
    ok = False
    print('MGMT_ERR plugin', e)
try:
    import plugin.staticfiles as sf
    from django.contrib.staticfiles.storage import staticfiles_storage
    sf.copy_plugin_static_files(slug)
    exists = staticfiles_storage.exists('plugins/%s/mgmt_dashboard.js' % slug)
    print('MGMT_STATIC', exists)
    ok = ok and exists
except Exception as e:
    ok = False
    print('MGMT_ERR static', e)
print('MGMT_OK' if ok else 'MGMT_FAIL')
"@
}

# 解讀容器回傳的訊息：成功回傳 $null，失敗回傳中文原因
function Get-DashboardActivateProblem {
    param([AllowEmptyString()][string]$Output)
    if ($Output -match 'MGMT_OK') { return $null }
    if ($Output -match 'MGMT_FOUND False') {
        return "InvenTree 沒有載入管理看板外掛。請確認 .env 有 INVENTREE_PLUGINS_ENABLED=True，且 inventree-data\plugins\$DashboardDirName 存在，再執行 docker compose up -d。"
    }
    if ($Output -match 'MGMT_STATIC False') { return '外掛的 JS 沒有複製到 static 資料夾。' }
    if ($Output -match 'MGMT_ERR') { return '啟用過程發生錯誤（見上方訊息）。' }
    return '沒有收到 InvenTree 的回應，可能容器尚未就緒。'
}

# 在 inventree-server 容器內啟用介面整合、確認外掛已載入並複製 JS。回傳 $null 表示成功，否則為中文原因
function Invoke-DashboardActivate {
    param([Parameter(Mandatory = $true)][string]$InstallDir, [int]$Retries = 10)
    $code = Get-DashboardActivateScript
    # 由 --command 讀取標準輸入整段執行（參數不含空白與雙引號，Windows PowerShell 5.1 傳遞時不會被拆開）
    $runStdin = "--command=exec(__import__('sys').stdin.read())"
    $problem = '尚未執行'
    Push-Location $InstallDir
    try {
        for ($i = 1; $i -le $Retries; $i++) {
            $out = ($code | docker compose exec -T -w /home/inventree/src/backend/InvenTree inventree-server python3 manage.py shell $runStdin 2>&1 | Out-String)
            $problem = Get-DashboardActivateProblem -Output $out
            if (-not $problem) { return $null }
            if ($i -lt $Retries) { Start-Sleep -Seconds 6 }
        }
        Write-Host $out
        return $problem
    } finally { Pop-Location }
}
