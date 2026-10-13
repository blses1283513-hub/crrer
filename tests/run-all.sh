#!/usr/bin/env bash
# 一次執行全部自動測試（本機或 CI）。
#   目前只包含妮菈 ERPNext 試用版的測試（InvenTree 相關程式已移除，見 archive/inventree/）。
set -uo pipefail
cd "$(dirname "$0")"
status=0
step() { echo; echo "===== $1 ====="; shift; "$@" || { echo "✗ 失敗：$*"; status=1; }; }

step "妮菈 ERPNext 試用版（Python）" python3 -m unittest discover -s erpnext

echo
if [ $status -eq 0 ]; then echo "✅ 全部通過"; else echo "❌ 有測試失敗"; fi
exit $status
