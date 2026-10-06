#!/bin/sh
# Firefly III 備份：資料庫 + 上傳附件。
# 用法（在 firefly-iii/ 目錄下執行）：sh scripts/backup.sh
# 輸出到 backups/<日期>/，此目錄已被 .gitignore 排除。
set -eu

DIR="backups/$(date +%Y-%m-%d)"
mkdir -p "$DIR"

# 資料庫：在 db 容器內用 .db.env 的帳密匯出
docker compose exec -T db sh -c \
  'exec mariadb-dump --single-transaction -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"' \
  | gzip > "$DIR/firefly-db.sql.gz"

# 上傳的附件（收據照片等）
docker compose exec -T app tar -czf - -C /var/www/html/storage upload \
  > "$DIR/firefly-upload.tar.gz"

# 設定檔（含密碼，請存放在安全的位置）
cp .env .db.env .importer.env "$DIR/" 2>/dev/null || true

echo "備份完成：$DIR"
ls -lh "$DIR"
