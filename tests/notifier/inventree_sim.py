"""模擬 InvenTree 1.5.6 的庫存與異動紀錄（依原始碼 stock/models.py 的行為）。

操作（move / split_move / remove / add / count / ...）會像真的一樣產生異動紀錄，
紀錄的欄位與 deltas 內容與 InvenTree 一致：
  - 完整搬移 STOCK_MOVE(20)：deltas {quantity: 搬移量, location: 新庫位}，沒有來源庫位
  - 部分搬移：子項 SPLIT_FROM_PARENT(40)：deltas {stockitem: 父項, quantity}；父項 SPLIT_CHILD_ITEM(42)
  - 移除 STOCK_REMOVE(12)：deltas {removed, quantity(剩餘)}
  - 新增 STOCK_ADD(11)：deltas {added, quantity(結果)}
  - 盤點 STOCK_COUNT(10)：deltas {quantity(盤點數)}
"""

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlparse


class InvenTreeSim:
    def __init__(self):
        self.locations = {}   # pk -> pathstring
        self.parts = {}       # pk -> dict
        self.categories = {}
        self.items = {}       # pk -> {pk, part, location, quantity}
        self.tracking = []    # 依 pk 遞增
        self.users = {}       # username -> {"pk", "groups": [..], "superuser": bool}
        self.sessions = {}    # cookie 值 -> username
        self.groups = {}      # name -> [username]
        self._pk = 100
        self.requests = []
        self.fail = {}        # 路徑前綴 -> HTTP 狀態碼（模擬故障）
        self.deny_track_for = set()   # 這些使用者讀不到異動紀錄（403）
        self.time = 0

    # ---- 建立資料
    def pk(self):
        self._pk += 1
        return self._pk

    def add_location(self, path):
        pk = self.pk()
        self.locations[pk] = path
        return pk

    def add_part(self, ipn, name=None, category=None, minimum_stock=0, is_template=False, active=True):
        pk = self.pk()
        self.parts[pk] = {"pk": pk, "IPN": ipn, "name": name or ipn, "full_name": name or ipn, "category": category,
                          "minimum_stock": minimum_stock, "is_template": is_template, "active": active}
        return pk

    def add_item(self, part, location, quantity):
        pk = self.pk()
        self.items[pk] = {"pk": pk, "part": part, "location": location, "quantity": quantity}
        return pk

    def add_user(self, username, groups=(), superuser=False):
        self.users[username] = {"pk": self.pk(), "groups": list(groups), "superuser": superuser}
        self.sessions[f"sess-{username}"] = username
        for g in groups:
            self.groups.setdefault(g, []).append(username)

    def cookie(self, username):
        return f"sessionid=sess-{username}"

    # ---- 產生異動紀錄
    def _track(self, item, ttype, user, deltas, notes="", part=None):
        self.time += 1
        entry = {"pk": self.pk(), "item": item, "part": part if part is not None else (self.items[item]["part"] if item in self.items else None),
                 "date": f"2026-10-10T12:{self.time // 60:02d}:{self.time % 60:02d}Z", "deltas": deltas, "label": "", "notes": notes,
                 "tracking_type": ttype, "user": self.users[user]["pk"], "user_detail": {"pk": self.users[user]["pk"], "username": user}}
        self.tracking.append(entry)
        return entry

    def move(self, user, item, dest, notes=""):
        it = self.items[item]
        it["location"] = dest
        self._track(item, 20, user, {"quantity": float(it["quantity"]), "location": dest}, notes)

    def split_move(self, user, item, qty, dest, notes=""):
        src = self.items[item]
        assert qty < src["quantity"]
        child = self.pk()
        self.items[child] = {"pk": child, "part": src["part"], "location": dest, "quantity": qty}
        src["quantity"] -= qty
        self._track(child, 40, user, {"stockitem": item, "quantity": float(qty)}, notes)
        self._track(item, 42, user, {"removed": float(qty), "quantity": float(src["quantity"]), "stockitem": child}, notes)
        return child

    def remove(self, user, item, qty, notes=""):
        it = self.items[item]
        q = min(qty, it["quantity"])
        it["quantity"] -= q
        self._track(item, 12, user, {"removed": float(q), "quantity": float(it["quantity"])}, notes)

    def add(self, user, item, qty, notes=""):
        it = self.items[item]
        it["quantity"] += qty
        self._track(item, 11, user, {"added": float(qty), "quantity": float(it["quantity"])}, notes)

    def count(self, user, item, qty, notes=""):
        self.items[item]["quantity"] = qty
        self._track(item, 10, user, {"quantity": float(qty)}, notes)

    def create(self, user, part, location, qty):
        item = self.add_item(part, location, qty)
        self._track(item, 1, user, {})
        return item

    # ---- HTTP
    def total_in_stock(self, part_pk):
        return sum(i["quantity"] for i in self.items.values() if i["part"] == part_pk)

    def handle(self, method, path, query, headers):
        self.requests.append((method, path, headers.get("Host")))
        for prefix, code in self.fail.items():
            if path.startswith(prefix):
                return code, {"detail": "simulated"}
        cookie = headers.get("Cookie", "")
        m = re.search(r"sessionid=([^;]+)", cookie)
        username = self.sessions.get(m.group(1)) if m else None
        if headers.get("Authorization", "").startswith("Token "):
            username = self.sessions.get("sess-" + headers["Authorization"][6:])
        if not username:
            return 401, {"detail": "Authentication credentials were not provided."}
        user = self.users[username]

        def page(rows):
            limit = int(query.get("limit", 0) or 0)
            offset = int(query.get("offset", 0) or 0)
            if not limit:
                return rows
            part = rows[offset:offset + limit]
            return {"count": len(rows), "next": "more" if offset + limit < len(rows) else None, "results": part}

        if path == "/api/user/me/":
            return 200, {"pk": user["pk"], "username": username, "is_superuser": user["superuser"],
                         "groups": [{"pk": 1, "name": g} for g in user["groups"]]}
        if path == "/api/user/group/":
            return 200, page([{"pk": i, "name": g, "users": [{"username": u} for u in us]}
                              for i, (g, us) in enumerate(self.groups.items(), 1)])
        if path == "/api/stock/location/":
            return 200, page([{"pk": k, "name": v.split("/")[-1], "pathstring": v} for k, v in self.locations.items()])
        if path == "/api/stock/":
            return 200, page([dict(i) for i in self.items.values()])
        if path == "/api/stock/track/":
            if username in self.deny_track_for:
                return 403, {"detail": "no permission"}
            rows = sorted(self.tracking, key=lambda e: -e["pk"]) if query.get("ordering") == "-pk" else list(self.tracking)
            out = []
            for e in rows:
                e = dict(e)
                if e["item"] in self.items:
                    e["item_detail"] = {"pk": e["item"], "location": self.items[e["item"]]["location"]}
                p = self.parts.get(e["part"])
                if p:
                    e["part_detail"] = {"pk": p["pk"], "IPN": p["IPN"], "full_name": p["full_name"]}
                out.append(e)
            return 200, page(out)
        if path == "/api/part/category/":
            return 200, page([{"pk": k, "name": v} for k, v in self.categories.items()])
        m = re.fullmatch(r"/api/part/(\d+)/", path)
        if m:
            p = self.parts.get(int(m.group(1)))
            return (200, dict(p)) if p else (404, {})
        if path == "/api/part/":
            rows = []
            for p in self.parts.values():
                total = self.total_in_stock(p["pk"])
                if query.get("low_stock") == "true" and not (total < p["minimum_stock"]):
                    continue
                if query.get("active") == "true" and not p["active"]:
                    continue
                rows.append({**p, "total_in_stock": total})
            return 200, page(rows)
        return 404, {"detail": "not mocked " + path}


def serve(sim):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urlparse(self.path)
            code, data = sim.handle("GET", u.path, dict(parse_qsl(u.query)), self.headers)
            raw = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"
