#!/usr/bin/env bash
# 還原演練（由 drill-nila.ps1 以 docker compose run --rm drill 執行）：
# 把 sites/drill-restore/ 中的一組備份還原到臨時網站 nila-drill，檢查後刪除。正式網站完全不受影響。
# 臨時網站的排程停用（不會同步 SHOPLINE、不會寄通知），也不會出現在網頁上。
set -euo pipefail
cd /home/frappe/frappe-bench
DIR=sites/drill-restore
drill=nila-drill
root=(--db-root-username root --db-root-password "${DB_PASSWORD:?}")

fail() { echo "NILA_DRILL_ERROR $*" >&2; exit 2; }
drop_drill() {  # 刪除臨時網站（上次演練中斷時留下的也一起刪）
  if [ -d "sites/$drill" ]; then
    bench drop-site "$drill" "${root[@]}" --force --no-backup >/dev/null 2>&1 || true
  fi
  rm -rf "sites/$drill" archived_sites/"$drill"*
}
trap 'drop_drill; rm -rf "$DIR"' EXIT

shopt -s nullglob
dbs=("$DIR"/*-database.sql.gz)
[ "${#dbs[@]}" -eq 1 ] || fail "必須剛好有一個 *-database.sql.gz"
db="${dbs[0]}"
pub=""; priv=""; conf=""
for f in "$DIR"/*-files.tar; do [[ "$f" == *-private-files.tar ]] && priv="$f" || pub="$f"; done
for f in "$DIR"/*-site_config_backup.json; do conf="$f"; done

echo "1/5 檢查備份檔完整"
gzip -t "$db" || fail "資料庫備份檔損壞：$(basename "$db")"
[ -z "$pub" ] || tar -tf "$pub" >/dev/null || fail "檔案備份損壞：$(basename "$pub")"
[ -z "$priv" ] || tar -tf "$priv" >/dev/null || fail "檔案備份損壞：$(basename "$priv")"

echo "2/5 建立臨時網站"
drop_drill
bench new-site "$drill" "${root[@]}" --mariadb-user-host-login-scope='%' --admin-password "$(head -c 24 /dev/urandom | base64)" >/dev/null
bench --site "$drill" set-config -p pause_scheduler 1 >/dev/null
bench --site "$drill" set-config -p maintenance_mode 1 >/dev/null

echo "3/5 還原備份到臨時網站"
args=("$db" "${root[@]}" --force)
[ -n "$pub" ] && args+=(--with-public-files "$pub")
[ -n "$priv" ] && args+=(--with-private-files "$priv")
bench --site "$drill" restore "${args[@]}" >/dev/null
if [ -n "$conf" ]; then
  key=$(env/bin/python -c "import json,sys; print(json.load(open(sys.argv[1])).get('encryption_key',''))" "$conf")
  [ -z "$key" ] || bench --site "$drill" set-config encryption_key "$key" >/dev/null
fi

echo "4/5 升級資料庫結構（和真正還原相同）"
bench --site "$drill" migrate >/dev/null

echo "5/5 讀取還原後的資料"
bench --site "$drill" execute nila_app.setup.drill.report | grep '^NILA_DRILL_REPORT ' || fail "讀不到還原後的資料"
echo "NILA_DRILL_OK"
