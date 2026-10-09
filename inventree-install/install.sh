#!/usr/bin/env bash
# InvenTree 一鍵安裝（macOS / Linux）
# 下載官方 Docker 安裝檔、設定版本與帳號密碼、初始化資料庫並啟動。
#
# 用法：
#   bash install.sh                       # 預設 1.5.6，安裝到 ~/inventree
#   VERSION=1.5.6 INSTALL_DIR=/opt/inventree bash install.sh
set -euo pipefail

VERSION="${VERSION:-1.5.6}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/inventree}"
SITE_URL="${SITE_URL:-http://localhost}"
BASE="https://raw.githubusercontent.com/inventree/InvenTree/$VERSION/contrib/container"

echo "== InvenTree $VERSION 安裝 =="

# 1. 檢查 Docker
if ! docker version >/dev/null 2>&1; then
  echo "找不到執行中的 Docker。請先安裝並啟動 Docker：https://docs.docker.com/get-docker/" >&2
  exit 1
fi

# 2. 建立安裝資料夾（已存在設定檔時不覆蓋）
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
if [ -f .env ]; then
  echo "$INSTALL_DIR 已有 .env，為避免覆蓋既有設定，已停止。若要重裝請換資料夾或手動備份後刪除。" >&2
  exit 1
fi

# 3. 下載官方檔案
for f in docker-compose.yml .env Caddyfile; do
  echo "下載 $f"
  curl -fsSL -o "$f" "$BASE/$f"
done

# 4. 設定 .env
read -rp "管理員帳號（例 admin）: " ADMIN_USER
read -rp "管理員 Email: " ADMIN_EMAIL
read -rsp "管理員密碼: " ADMIN_PASS; echo
# 值會以單引號寫入 .env（Docker Compose 照字面讀取，不展開 $），所以不能含單引號
for v in "$ADMIN_USER" "$ADMIN_EMAIL" "$ADMIN_PASS"; do
  if [ -z "$v" ] || [[ "$v" == *"'"* ]]; then
    echo "帳號、Email、密碼不可為空，也不可包含單引號 '。請重新執行。" >&2
    rm -f docker-compose.yml .env Caddyfile
    exit 1
  fi
done
DB_PASS="$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"

# 以環境變數傳值給 awk，避免密碼中的特殊字元被誤解
V_TAG="$VERSION" V_URL="$SITE_URL" V_DB="$DB_PASS" \
V_USER="$ADMIN_USER" V_PASS="$ADMIN_PASS" V_EMAIL="$ADMIN_EMAIL" \
awk '
  /^INVENTREE_TAG=/             { print "INVENTREE_TAG=" ENVIRON["V_TAG"]; next }
  /^INVENTREE_SITE_URL=/        { print "INVENTREE_SITE_URL=\"" ENVIRON["V_URL"] "\""; next }
  /^INVENTREE_DB_PASSWORD=/     { print "INVENTREE_DB_PASSWORD=" ENVIRON["V_DB"]; next }
  /^#INVENTREE_ADMIN_USER=/     { print "INVENTREE_ADMIN_USER='\''" ENVIRON["V_USER"] "'\''"; next }
  /^#INVENTREE_ADMIN_PASSWORD=/ { print "INVENTREE_ADMIN_PASSWORD='\''" ENVIRON["V_PASS"] "'\''"; next }
  /^#INVENTREE_ADMIN_EMAIL=/    { print "INVENTREE_ADMIN_EMAIL='\''" ENVIRON["V_EMAIL"] "'\''"; next }
  { print }
' .env > .env.tmp && mv .env.tmp .env
chmod 600 .env

# 5. 初始化（下載映像、建立資料庫、建立管理員）並啟動
echo "初始化資料庫（第一次需下載映像，約數分鐘）..."
docker compose run --rm inventree-server invoke update
docker compose up -d

echo
echo "完成！請用瀏覽器開啟 $SITE_URL ，以剛才的管理員帳號登入。"
echo "資料存放於：$INSTALL_DIR/inventree-data"
echo "停止：在 $INSTALL_DIR 執行 docker compose down"
