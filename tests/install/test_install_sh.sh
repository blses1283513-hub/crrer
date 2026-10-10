#!/usr/bin/env bash
# install.sh 的自動測試：以假的 docker 與 curl（不連網、不真的啟動容器）驗證 .env 設定流程。
# 執行：bash tests/install/test_install_sh.sh
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FIX="$ROOT/tests/fixtures/inventree-1.5.6"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
fail=0
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1"; fail=1; fi; }

# 假 docker：記錄呼叫
cat > "$WORK/bin/docker" <<'S'
#!/bin/sh
echo "docker $*" >> "$DOCKER_LOG"
exit 0
S
# 假 curl：依 URL 檔名從測試資料複製
cat > "$WORK/bin/curl" <<S
#!/bin/sh
out=""; url=""
while [ \$# -gt 0 ]; do case "\$1" in -o) out="\$2"; shift 2;; -*) shift;; *) url="\$1"; shift;; esac; done
cp "$FIX/\$(basename "\$url")" "\$out"
S
chmod +x "$WORK/bin/"*
export PATH="$WORK/bin:$PATH" DOCKER_LOG="$WORK/docker.log"

run() { printf '%s\n%s\n%s\n' "$1" "$2" "$3" | INSTALL_DIR="$4" bash "$ROOT/inventree-install/install.sh" > "$WORK/out.txt" 2>&1; }

# 1. 正常安裝：密碼含特殊字元必須原樣保存（單引號包住，Compose 不展開 $）
run admin 'me@example.com' 'S3cret!$&\1' "$WORK/a"; rc=$?
E="$WORK/a/.env"
check "正常安裝結束代碼為 0" '[ $rc -eq 0 ]'
check "版本固定為 1.5.6" 'grep -qx "INVENTREE_TAG=1.5.6" "$E"'
check "管理員帳號寫入" 'grep -qx "INVENTREE_ADMIN_USER='"'"'admin'"'"'" "$E"'
check "密碼原樣保存" 'grep -qxF "INVENTREE_ADMIN_PASSWORD='"'"'S3cret!\$&\\1'"'"'" "$E"'
check "資料庫密碼已改為隨機值" '! grep -qx "INVENTREE_DB_PASSWORD=pgpassword" "$E" && grep -qE "^INVENTREE_DB_PASSWORD=[0-9a-f]{32}$" "$E"'
check ".env 權限為 600" '[ "$(stat -c %a "$E")" = "600" ]'
check "有執行初始化與啟動" 'grep -q "compose run --rm inventree-server invoke update" "$DOCKER_LOG" && grep -q "compose up -d" "$DOCKER_LOG"'
check "其他設定與官方檔案相同" 'diff <(grep -vE "^#?INVENTREE_(TAG|SITE_URL|DB_PASSWORD|ADMIN_(USER|PASSWORD|EMAIL))=" "$FIX/.env") <(grep -vE "^#?INVENTREE_(TAG|SITE_URL|DB_PASSWORD|ADMIN_(USER|PASSWORD|EMAIL))=" "$E") >/dev/null'

# 2. 已安裝過的資料夾：不可覆蓋
cp "$E" "$WORK/env.before"
run x y z "$WORK/a"; rc=$?
check "重複安裝被拒絕" '[ $rc -ne 0 ] && grep -q "已有 .env" "$WORK/out.txt"'
check "既有 .env 未被改動" 'cmp -s "$E" "$WORK/env.before"'

# 3. 含單引號的密碼：拒絕並清掉下載的檔案
run admin 'me@example.com' "bad'pw" "$WORK/b"; rc=$?
check "含單引號的密碼被拒絕" '[ $rc -ne 0 ]'
check "拒絕後不留下半套檔案" '[ ! -e "$WORK/b/.env" ] && [ ! -e "$WORK/b/docker-compose.yml" ]'

# 4. 空白帳號：拒絕
run '' 'me@example.com' 'pw' "$WORK/c"; rc=$?
check "空白帳號被拒絕" '[ $rc -ne 0 ]'

exit $fail
