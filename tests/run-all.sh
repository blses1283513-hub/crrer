#!/usr/bin/env bash
# 一次執行全部自動測試（本機或 CI）。
#   選用環境變數：CADDY_BIN（caddy 執行檔，有才跑 App 端對端測試）、PWSH（pwsh 路徑）
set -uo pipefail
cd "$(dirname "$0")"
status=0
step() { echo; echo "===== $1 ====="; shift; "$@" || { echo "✗ 失敗：$*"; status=1; }; }

step "匯入腳本（Python）" python3 -m unittest discover -s seed
step "安裝腳本 install.sh" bash install/test_install_sh.sh
if command -v "${PWSH:-pwsh}" >/dev/null 2>&1; then
  step "PowerShell 腳本" "${PWSH:-pwsh}" -NoProfile -File powershell/Test-Scripts.ps1
else
  echo; echo "（略過 PowerShell 測試：找不到 pwsh）"
fi
step "中文操作助手（瀏覽器）" node --test --test-concurrency=1 ui/*.test.js
step "App 端對端（Caddy＋瀏覽器）" node --test --test-concurrency=1 app/*.test.js

echo
if [ $status -eq 0 ]; then echo "✅ 全部通過"; else echo "❌ 有測試失敗"; fi
exit $status
