# 妮菈穿戴甲正式版映像檔：官方 ERPNext 16 映像檔 + 我們的 nila_app
# 在客戶電腦上用 docker compose build 建置（不需要映像檔倉庫，建置時也不需要下載套件）。
# 建置內容（context）是 nila-erpnext 資料夾。
ARG ERPNEXT_IMAGE=frappe/erpnext:v16.50.0
FROM ${ERPNEXT_IMAGE}

USER frappe
WORKDIR /home/frappe/frappe-bench

COPY --chown=frappe:0 apps/nila_app apps/nila_app

# 以「可編輯安裝」的方式登記 nila_app（與映像檔中 erpnext 的登記方式相同：.pth＋dist-info），
# 再確認可以載入，有問題就讓建置失敗。
RUN set -e; \
    SP="$(env/bin/python -c 'import site; print(site.getsitepackages()[0])')"; \
    VER="$(env/bin/python -c 'import re; print(re.search(r"__version__ = \"(.+?)\"", open("apps/nila_app/nila_app/__init__.py").read()).group(1))')"; \
    echo /home/frappe/frappe-bench/apps/nila_app > "$SP/nila_app.pth"; \
    DI="$SP/nila_app-$VER.dist-info"; mkdir -p "$DI"; \
    printf 'Metadata-Version: 2.1\nName: nila_app\nVersion: %s\n' "$VER" > "$DI/METADATA"; \
    printf 'local\n' > "$DI/INSTALLER"; \
    printf '{"url":"file:///home/frappe/frappe-bench/apps/nila_app","dir_info":{"editable":true}}' > "$DI/direct_url.json"; \
    printf 'nila_app.pth,,\nnila_app-%s.dist-info/METADATA,,\nnila_app-%s.dist-info/RECORD,,\n' "$VER" "$VER" > "$DI/RECORD"; \
    env/bin/python -c "import nila_app.hooks, nila_app.setup.config, importlib.metadata as m; print('nila_app', m.version('nila_app'))"; \
    env/bin/python -m compileall -q apps/nila_app

LABEL org.opencontainers.image.title="nila-erpnext" \
      org.opencontainers.image.description="ERPNext 16 + nila_app（妮菈穿戴甲）"
