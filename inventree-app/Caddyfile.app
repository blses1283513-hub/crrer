# 庫存管理系統 App 專用的 Caddyfile
# 以 InvenTree 1.5.6 官方 contrib/container/Caddyfile（MIT 授權）為基礎，修改處標記「[App]」：
#   1. 網站位址改為 http://（接受任何主機名稱的 80 埠連線），讓本機 localhost 與區網其他電腦用 IP 都能連
#   2. 新增 /app/*：App 外框頁、內建中文操作助手、圖示、用戶端捷徑腳本
#   3. 根路徑 / 自動導向 /app/
#   4. 允許同源嵌入（X-Frame-Options: SAMEORIGIN），讓 App 外框能載入 InvenTree
#   5. 新增 /notify/*：轉給通知服務（inventree-notifier）
# 由 docker-compose.override.yml 掛載，取代官方 Caddyfile；官方檔案本身不修改。

(log_common) {
	log {
		output file /var/log/caddy/{args[0]}.access.log
	}
}

(cors-headers) {
	header Allow GET,HEAD,OPTIONS
	header Access-Control-Allow-Origin *
	header Access-Control-Allow-Methods GET,HEAD,OPTIONS
	header Access-Control-Allow-Headers Authorization,Content-Type,User-Agent,traceparent

	@cors_preflight{args[0]} method OPTIONS

	handle @cors_preflight{args[0]} {
		respond "" 204
	}
}

:9090 {
	handle /api/system/health/* {
		reverse_proxy {$INVENTREE_SERVER:"http://inventree-server:8000"}
	}

	handle {
		respond 404
	}
}

# [App] 接受所有主機名稱（localhost、區網 IP）
http:// {
	import log_common inventree

	encode gzip

	request_body {
		max_size 100MB
	}

	# [App] 允許同源嵌入，覆蓋伺服器預設的 DENY（> 表示在上游回應後才套用）
	header >X-Frame-Options "SAMEORIGIN"

	# [App] 根路徑導向 App
	@root path /
	redir @root /app/ 302

	# [App] App 外框與操作助手（不需登入即可載入外框，登入仍由 InvenTree 處理）
	handle_path /app/* {
		root * /var/www/app
		header Cache-Control "no-cache"
		file_server
	}

	# [App] 通知服務（依使用者所屬公司提供通知；已讀紀錄存在伺服器）
	handle /notify/* {
		reverse_proxy {$INVENTREE_NOTIFIER:"http://inventree-notifier:8090"}
	}

	handle_path /static/* {
		import cors-headers static

		root * /var/www/static
		file_server
	}

	handle_path /media/* {
		import cors-headers media

		root * /var/www/media
		file_server

		header Content-Disposition attachment

		forward_auth {$INVENTREE_SERVER:"http://inventree-server:8000"} {
			uri /auth/
		}
	}

	reverse_proxy {$INVENTREE_SERVER:"http://inventree-server:8000"}
}
