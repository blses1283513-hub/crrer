# 妮菈穿戴甲：ERPNext 16 試用版功能自動驗證（安裝完成後執行一次）
# 實際操作 13 項功能並判定通過與否：在途調撥、叫貨後不重複建議、出貨、實際庫存不變負、條碼、修改紀錄、
# 依倉庫限制權限、會員合併、用語修正。會建立名稱含 NILA-TRIAL-VERIFY 的測試單據（只在試用版）。
# 用法：powershell -ExecutionPolicy Bypass -File .\verify-erpnext-trial.ps1 [-InstallDir C:\Users\你\nila-erpnext-trial]
param([string]$InstallDir = (Join-Path $HOME "nila-erpnext-trial"))

$ErrorActionPreference = "Stop"
if (-not (Test-Path (Join-Path $InstallDir "docker-compose.yml"))) { throw "在 $InstallDir 找不到試用版，請先執行 install-erpnext-trial.ps1。" }
Push-Location $InstallDir
try {
    docker compose cp (Join-Path $PSScriptRoot "seed/verify_trial.py") backend:/tmp/nila-verify_trial.py
    if ($LASTEXITCODE -ne 0) { throw "無法複製驗證程式到容器，請確認試用版正在執行（docker compose ps）。" }
    docker compose exec -T -w /home/frappe/frappe-bench/sites backend /home/frappe/frappe-bench/env/bin/python /tmp/nila-verify_trial.py --site frontend
    if ($LASTEXITCODE -eq 0) { Write-Host "全部通過" -ForegroundColor Green }
    else { Write-Host "有項目未通過，請把上方結果交給協助的人。" -ForegroundColor Yellow }
} finally { Pop-Location }
