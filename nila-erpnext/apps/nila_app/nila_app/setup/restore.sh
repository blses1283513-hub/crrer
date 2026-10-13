#!/usr/bin/env bash
# 還原（由 restore-nila.ps1 以 docker compose run --rm restore 執行）。
# 讀取 sites/restore/ 中的一組備份：*-database.sql.gz（必要）、*-files.tar、*-private-files.tar、*-site_config_backup.json
# 1. 把網站的資料庫換成備份的內容（會覆蓋目前資料）
# 2. 還原上傳的檔案
# 3. 沿用備份的加密金鑰（換電腦還原時，已儲存的密碼與 API 金鑰才能解開）
# 密碼由環境變數 DB_PASSWORD 提供（來自 .env），不出現在指令中。
set -euo pipefail
cd /home/frappe/frappe-bench
DIR=sites/restore
site="${SITE_NAME:?}"

shopt -s nullglob
fail() { echo "NILA_RESTORE_ERROR $*" >&2; exit 2; }
only() {  # 每種檔案最多一個；超過一個就停止，避免混用不同時間的備份
  local label="$1"; shift
  [ "$#" -le 1 ] || fail "有多個 $label，請只放一組備份"
  printf '%s' "${1:-}"
}
pubs=()
for f in "$DIR"/*-files.tar; do [[ "$f" == *-private-files.tar ]] || pubs+=("$f"); done
db=$(only '*-database.sql.gz' "$DIR"/*-database.sql.gz)
pub=$(only '*-files.tar' "${pubs[@]}")
priv=$(only '*-private-files.tar' "$DIR"/*-private-files.tar)
conf=$(only '*-site_config_backup.json' "$DIR"/*-site_config_backup.json)
[ -n "$db" ] || fail "找不到 *-database.sql.gz"
[ -d "sites/$site" ] || fail "網站 $site 不存在，請先完成安裝"

args=("$db" --db-root-username root --db-root-password "$DB_PASSWORD" --force)
[ -n "$pub" ] && args+=(--with-public-files "$pub")
[ -n "$priv" ] && args+=(--with-private-files "$priv")

echo "還原資料庫：$(basename "$db")"
bench --site "$site" restore "${args[@]}"

if [ -n "$conf" ]; then
  key=$(env/bin/python -c "import json,sys; print(json.load(open(sys.argv[1])).get('encryption_key',''))" "$conf")
  if [ -n "$key" ]; then
    bench --site "$site" set-config encryption_key "$key" >/dev/null
    echo "已沿用備份的加密金鑰"
  fi
fi

bench --site "$site" migrate
bench --site "$site" clear-cache
echo "NILA_RESTORE_OK"
