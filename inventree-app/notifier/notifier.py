#!/usr/bin/env python3
"""庫存管理系統：通知服務。

在 InvenTree 旁邊執行的小型服務，負責三件事：
  1. 從 InvenTree 的庫存異動紀錄（stock tracking）與零件資料，找出該通知的事件：
       - 別家公司或無公司歸屬的帳號（例如管理員）把庫存調進／調出你的公司庫位
       - 大量（>= large_qty）或歸零的異常操作
       - 低庫存
  2. 依使用者所屬的公司群組，只把「與該公司有關」的事件給他（superuser 預設看全部）。
  3. 保存每個人的已讀紀錄（跨電腦、跨瀏覽器共用）。

身分驗證：不另設帳號。收到請求時，把使用者自己的登入憑證（Cookie / Authorization）轉給
InvenTree 的 /api/user/me/，InvenTree 說他是誰就是誰。本服務不儲存任何憑證。

事件的產生是「被動」的：有人開著 App 輪詢時才向 InvenTree 讀取新的異動紀錄，並依序處理。
異動紀錄保存在 InvenTree，所以沒人開著的期間不會漏掉，下次有人開啟時會補上。

只依賴 Python 標準函式庫。
"""

import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# InvenTree 1.5.6 StockHistoryCode
T_CREATED = 1
T_COUNT, T_ADD, T_REMOVE, T_RETURNED = 10, 11, 12, 15
T_MOVE, T_SPLIT_FROM, T_SPLIT_CHILD = 20, 40, 42
T_RECEIVED, T_RETURN_ORDER, T_RETURNED_CUSTOMER = 70, 80, 105
MOVE_TYPES = (T_MOVE, T_SPLIT_FROM)
LOCATION_ONLY_TYPES = (T_COUNT, T_RETURNED, T_RECEIVED, T_RETURN_ORDER, T_RETURNED_CUSTOMER)

KIND_ORDER = ["zero", "large", "transfer_out", "transfer_in"]
KIND_ZH = {"zero": "歸零", "large": "大量", "transfer_out": "調出", "transfer_in": "調進", "low_stock": "低庫存"}
ACTION_ZH = {T_REMOVE: "移除", T_ADD: "新增", T_COUNT: "盤點", T_MOVE: "轉移", T_SPLIT_FROM: "轉移"}
REQUIRED_HEADER = ("X-Requested-With", "inventory-helper")

DEFAULT_CONFIG = {
    "companies": [],
    "large_qty": 100,
    "superuser_sees_all": True,
    "min_process_interval_s": 5,
    "low_stock_cache_s": 20,
    "identity_cache_s": 30,
    "retention_days": 60,
    "max_events": 500,
    "max_feed_items": 100,
}


def log(*args):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *args, file=sys.stderr, flush=True)


class UpstreamError(Exception):
    """向 InvenTree 讀取資料失敗。status 為 HTTP 狀態碼，連線失敗時為 0。"""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class Identity:
    def __init__(self, username, groups, is_superuser):
        self.username = username
        self.groups = set(groups)
        self.is_superuser = bool(is_superuser)


# ---------------------------------------------------------------- InvenTree 用戶端

class InvenTreeClient:
    def __init__(self, base_url, default_host="localhost", timeout=15):
        self.base = base_url.rstrip("/")
        self.default_host = default_host
        self.timeout = timeout

    def get(self, path, params, auth):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        headers = {"Accept": "application/json", "Host": auth.get("host") or self.default_host}
        for key in ("cookie", "authorization"):
            if auth.get(key):
                headers[key.capitalize()] = auth[key]
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read() or b"null")
        except urllib.error.HTTPError as e:
            raise UpstreamError(e.code, f"InvenTree 回應 {e.code}：{path}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise UpstreamError(0, f"連不到 InvenTree：{getattr(e, 'reason', e)}")
        except ValueError:
            raise UpstreamError(502, f"InvenTree 回傳的不是 JSON：{path}")

    def get_all(self, path, params, auth, page=200, max_rows=20000):
        rows, offset = [], 0
        while True:
            res = self.get(path, {**params, "limit": page, "offset": offset}, auth)
            if isinstance(res, list):
                return res
            batch = res.get("results", [])
            rows += batch
            if not res.get("next") or not batch or len(rows) >= max_rows:
                return rows
            offset += len(batch)


# ---------------------------------------------------------------- 狀態儲存

def empty_state():
    return {"version": 1, "initialized": False, "cursor": 0, "item_loc": {}, "events": [], "users": {}}


class StateStore:
    """以單一 JSON 檔保存狀態。寫入使用暫存檔再改名，避免寫到一半當機而毀損。"""

    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self.state = self._load()

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "events" not in data:
                raise ValueError("格式不正確")
            base = empty_state()
            base.update(data)
            return base
        except FileNotFoundError:
            return empty_state()
        except (ValueError, OSError) as e:
            backup = f"{self.path}.corrupt-{time.strftime('%Y%m%d-%H%M%S')}"
            try:
                os.replace(self.path, backup)
                log(f"狀態檔損毀（{e}），已改名為 {backup}，將重新開始（不會產生歷史通知）")
            except OSError:
                log(f"狀態檔損毀（{e}），且無法備份，將重新開始")
            return empty_state()

    def save(self):
        with self.lock:
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False)
            os.replace(tmp, self.path)


def parse_time(text):
    try:
        t = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ---------------------------------------------------------------- 核心邏輯

class Notifier:
    def __init__(self, config, client, store, clock=time.time):
        self.cfg = {**DEFAULT_CONFIG, **config}
        self.client = client
        self.store = store
        self.clock = clock
        self.companies = self.cfg["companies"]
        self.group_to_company = {c["group"]: c["name"] for c in self.companies}
        self.lock = threading.RLock()
        self.warnings = []
        self._last_process = 0.0
        self._locations = {}          # pk -> {"path":..., "company":...}
        self._locations_ts = 0.0
        self._parts = {}              # pk -> {"ipn":..., "name":...}
        self._actor_cache = (0.0, {})  # (時間, {username: set(company)})
        self._low_cache = (0.0, [])
        self._identity_cache = {}

    # ---- 身分
    def identify(self, auth):
        key = hashlib.sha256(f"{auth.get('cookie', '')}|{auth.get('authorization', '')}".encode()).hexdigest()
        now = self.clock()
        hit = self._identity_cache.get(key)
        if hit and now - hit[0] < self.cfg["identity_cache_s"]:
            return hit[1]
        me = self.client.get("/api/user/me/", {}, auth)
        if not isinstance(me, dict) or not me.get("username"):
            raise UpstreamError(401, "未登入")
        ident = Identity(me["username"], [g.get("name") for g in me.get("groups", []) if isinstance(g, dict)],
                         me.get("is_superuser"))
        self._identity_cache = {k: v for k, v in self._identity_cache.items() if now - v[0] < self.cfg["identity_cache_s"]}
        self._identity_cache[key] = (now, ident)
        return ident

    def companies_of(self, ident):
        return sorted({self.group_to_company[g] for g in ident.groups if g in self.group_to_company})

    def visible_companies(self, ident):
        if ident.is_superuser and self.cfg["superuser_sees_all"]:
            return {c["name"] for c in self.companies}
        return set(self.companies_of(ident))

    # ---- 查詢與快取
    def _refresh_locations(self, auth):
        rows = self.client.get_all("/api/stock/location/", {}, auth)
        self._locations = {}
        for r in rows:
            path = r.get("pathstring") or r.get("name") or ""
            top = path.split("/")[0]
            company = top if top in self.group_to_company.values() else None
            self._locations[r["pk"]] = {"path": path, "company": company}
        self._locations_ts = self.clock()

    def location(self, pk, auth):
        if pk is None:
            return None
        if pk not in self._locations and (self._locations_ts == 0 or self.clock() - self._locations_ts > 2):
            self._refresh_locations(auth)   # 遇到沒看過的庫位才重新讀取（2 秒內不重複）
        return self._locations.get(pk)

    def part_info(self, entry, auth):
        detail = entry.get("part_detail") or {}
        pk = entry.get("part") or detail.get("pk")
        if detail.get("IPN") or detail.get("full_name") or detail.get("name"):
            info = {"ipn": detail.get("IPN") or "", "name": detail.get("full_name") or detail.get("name") or ""}
            if pk:
                self._parts[pk] = info
            return info
        if pk in self._parts:
            return self._parts[pk]
        if pk:
            try:
                p = self.client.get(f"/api/part/{pk}/", {}, auth)
                info = {"ipn": p.get("IPN") or "", "name": p.get("full_name") or p.get("name") or ""}
            except UpstreamError:
                info = {"ipn": "", "name": f"零件 #{pk}"}
            self._parts[pk] = info
            return info
        return {"ipn": "", "name": "未知零件"}

    def actor_companies(self, auth):
        ts, cache = self._actor_cache
        if self.clock() - ts < 60 and cache is not None:
            return cache
        groups = self.client.get_all("/api/user/group/", {"user_detail": "true", "role_detail": "false",
                                                           "permission_detail": "false"}, auth)
        mapping = {}
        for g in groups:
            company = self.group_to_company.get(g.get("name"))
            if not company:
                continue
            for u in g.get("users") or []:
                mapping.setdefault(u.get("username"), set()).add(company)
        self._actor_cache = (self.clock(), mapping)
        return mapping

    # ---- 異動紀錄 → 事件
    def process(self, auth):
        """讀取新的異動紀錄並處理。節流：min_process_interval_s 內不重複讀取。"""
        with self.lock:
            st = self.store.state
            now = self.clock()
            if st["initialized"] and now - self._last_process < self.cfg["min_process_interval_s"]:
                return
            self._last_process = now
            try:
                if not st["initialized"]:
                    self._initialize(auth)
                else:
                    self._process_new(auth)
                self.warnings = []
            except UpstreamError as e:
                if e.status in (401, 403):
                    self.warnings = ["目前登入的帳號沒有讀取庫存異動的權限，無法更新通知。"]
                else:
                    self.warnings = [f"暫時無法向 InvenTree 讀取最新異動（{e}），稍後會自動重試。"]
                log("process 失敗：", e)

    def _initialize(self, auth):
        newest = self.client.get("/api/stock/track/", {"ordering": "-pk", "limit": 1}, auth)
        rows = newest if isinstance(newest, list) else newest.get("results", [])
        cursor = rows[0]["pk"] if rows else 0
        items = self.client.get_all("/api/stock/", {}, auth)
        st = self.store.state
        st["item_loc"] = {str(i["pk"]): i.get("location") for i in items}
        st["cursor"] = cursor
        st["initialized"] = True
        self.store.save()
        log(f"初始化完成：從異動紀錄 #{cursor} 之後開始通知；追蹤 {len(items)} 筆庫存位置")

    def _fetch_new_entries(self, auth):
        """回傳 (新的紀錄（由舊到新）, 目前最新一筆的編號)。"""
        cursor = self.store.state["cursor"]
        found, offset, newest = [], 0, None
        while True:
            res = self.client.get("/api/stock/track/", {"ordering": "-pk", "limit": 100, "offset": offset,
                                                        "item_detail": "true", "part_detail": "true",
                                                        "user_detail": "true"}, auth)
            rows = res if isinstance(res, list) else res.get("results", [])
            if newest is None:
                newest = rows[0]["pk"] if rows else 0
            fresh = [r for r in rows if r["pk"] > cursor]
            found += fresh
            if len(fresh) < len(rows) or not rows or isinstance(res, list) or not res.get("next") or len(found) >= 5000:
                break
            offset += len(rows)
        return sorted(found, key=lambda r: r["pk"]), newest

    def _process_new(self, auth):
        entries, newest = self._fetch_new_entries(auth)
        if newest < self.store.state["cursor"]:
            # 資料庫被還原到較舊的時間點：舊的進度已無意義，重新開始（事件與已讀進度一併清掉，使用者記錄保留）
            log(f"偵測到資料庫回到較舊的狀態（最新 #{newest} < 進度 #{self.store.state['cursor']}），重新初始化")
            st = self.store.state
            st["events"] = []
            for u in st["users"].values():
                u["read_up_to"], u["read"] = 0, []
            self._initialize(auth)
            return
        if not entries:
            return
        actors = self.actor_companies(auth)   # 失敗就整批不處理，游標不前進
        st = self.store.state
        # 每個庫存在這一批裡最後一次『位置變更』的編號：建立紀錄若早於它，item_detail 的位置已不是建立時的位置
        self._last_move = {}
        for e in entries:
            if e.get("item") is not None and (e.get("deltas") or {}).get("location") is not None:
                self._last_move[e["item"]] = e["pk"]
        for e in entries:
            try:
                self._handle(e, actors, auth)
            except UpstreamError:
                raise
            except Exception as ex:   # 單筆資料異常不可拖垮整批
                log(f"略過無法解析的異動紀錄 #{e.get('pk')}：{ex!r}")
            st["cursor"] = e["pk"]
        self._prune()
        self.store.save()

    def _loc_of_item(self, item_pk, entry, auth):
        item_loc = self.store.state["item_loc"]
        if item_pk is not None and str(item_pk) in item_loc:
            return item_loc[str(item_pk)]
        detail = entry.get("item_detail") or {}
        if detail.get("location") is not None:
            return detail["location"]
        return None

    def _handle(self, e, actors, auth):
        st = self.store.state
        t = e.get("tracking_type")
        d = e.get("deltas") or {}
        item = e.get("item")
        item_loc = st["item_loc"]
        large = self.cfg["large_qty"]
        user = (e.get("user_detail") or {}).get("username") or (str(e["user"]) if e.get("user") else "")
        targets = {}

        def add(company, kind):
            if company:
                targets.setdefault(company, [])
                if kind not in targets[company]:
                    targets[company].append(kind)

        dest = d.get("location")
        src = None
        amount = None
        result_qty = d.get("quantity") if t in (T_REMOVE, T_ADD, T_COUNT) else None
        loc_for_adjust = None

        if t == T_MOVE:
            src = item_loc.get(str(item)) if item is not None else None
            amount = d.get("quantity")
        elif t == T_SPLIT_FROM:
            src = item_loc.get(str(d.get("stockitem")))
            amount = d.get("quantity")
            if dest is None:
                dest = (e.get("item_detail") or {}).get("location")
                if dest is None and item is not None:
                    dest = item_loc.get(str(item))
        elif t in (T_REMOVE, T_ADD, T_COUNT):
            loc_for_adjust = self._loc_of_item(item, e, auth)
            amount = d.get({T_REMOVE: "removed", T_ADD: "added"}.get(t, "quantity"))

        actor_companies = actors.get(user, set())
        is_move = t in MOVE_TYPES and dest is not None and src != dest
        loc_dest = self.location(dest, auth) if dest is not None else None
        loc_src = self.location(src, auth) if src is not None else None
        loc_adj = self.location(loc_for_adjust, auth) if loc_for_adjust is not None else None
        dc = loc_dest["company"] if loc_dest else None
        sc = loc_src["company"] if loc_src else None
        ac = loc_adj["company"] if loc_adj else None

        if is_move:
            if dc and dc != sc and dc not in actor_companies:
                add(dc, "transfer_in")
            if sc and sc != dc and sc not in actor_companies:
                add(sc, "transfer_out")
            if amount is not None and amount >= large:
                add(dc, "large")
                add(sc, "large")
        elif t in (T_REMOVE, T_ADD, T_COUNT):
            if t != T_COUNT and amount is not None and amount >= large:
                add(ac, "large")
            if t == T_COUNT and result_qty is not None and result_qty >= large:
                add(ac, "large")
            if t in (T_REMOVE, T_COUNT) and result_qty is not None and result_qty == 0:
                add(ac, "zero")

        # 更新庫存位置表（無論是否產生事件）
        if item is not None and dest is not None and (t in MOVE_TYPES or t in LOCATION_ONLY_TYPES):
            item_loc[str(item)] = dest
        elif t == T_CREATED and item is not None and str(item) not in item_loc \
                and getattr(self, "_last_move", {}).get(item, 0) < e["pk"]:
            created_at = (e.get("item_detail") or {}).get("location")
            if created_at is not None:
                item_loc[str(item)] = created_at   # 新建立的庫存：記下初始位置，之後調出才知道來源

        if not targets:
            return
        part = self.part_info(e, auth)
        if actor_companies:
            label = f"{'、'.join(sorted(actor_companies))} 的 {user}"
        else:
            label = f"{user or '系統'}（無公司歸屬，可能是管理員）"
        st["events"].append({
            "id": e["pk"], "time": e.get("date"), "actor": user, "actor_label": label,
            "type": t, "action": ACTION_ZH.get(t, "異動"), "ipn": part["ipn"], "part_name": part["name"],
            "qty": amount, "result_qty": result_qty,
            "src_path": loc_src["path"] if loc_src else None, "dest_path": loc_dest["path"] if loc_dest else None,
            "loc_path": loc_adj["path"] if loc_adj else None,
            "src_company": sc, "dest_company": dc, "notes": e.get("notes") or "",
            "targets": targets,
        })

    def _prune(self):
        st = self.store.state
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.cfg["retention_days"])
        events = [ev for ev in st["events"] if (parse_time(ev.get("time")) or datetime.now(timezone.utc)) >= cutoff]
        st["events"] = events[-self.cfg["max_events"]:]

    # ---- 低庫存
    def low_stock(self, auth):
        ts, cache = self._low_cache
        if self.clock() - ts < self.cfg["low_stock_cache_s"]:
            return cache
        parts = self.client.get_all("/api/part/", {"low_stock": "true"}, auth)
        cats = None
        out = []
        for p in parts:
            if p.get("is_template"):
                continue
            ipn = p.get("IPN") or ""
            company = None
            for c in self.companies:
                if ipn.startswith(c.get("code", "\0") + "-"):
                    company = c["name"]
            if company is None and p.get("category") is not None:
                if cats is None:
                    cats = {c["pk"]: c.get("name") for c in self.client.get_all("/api/part/category/", {}, auth)}
                name = (cats.get(p["category"]) or "").split("/")[0]
                company = name if name in self.group_to_company.values() else None
            qty = p.get("total_in_stock", p.get("in_stock"))
            if company is None or qty is None:
                continue
            out.append({"pk": p["pk"], "ipn": ipn, "name": p.get("full_name") or p.get("name") or "",
                        "company": company, "qty": float(qty), "min": float(p.get("minimum_stock") or 0)})
        self._low_cache = (self.clock(), out)
        return out

    # ---- 已讀
    def _user_state(self, username):
        users = self.store.state["users"]
        return users.setdefault(username, {"read_up_to": 0, "read": [], "low_ack": {}})

    # ---- 提供給使用者的內容
    def feed(self, auth):
        ident = self.identify(auth)
        self.process(auth)
        warnings = list(self.warnings)
        visible = self.visible_companies(ident)
        with self.lock:
            us = self._user_state(ident.username)
            items = []
            try:
                lows = [x for x in self.low_stock(auth) if x["company"] in visible]
                low_ok = True
            except UpstreamError as e:
                lows, low_ok = [], False
                warnings.append(f"暫時無法讀取低庫存資料（{e}）。")
            if low_ok:
                current = {str(x["pk"]) for x in lows}
                for k in [k for k in us["low_ack"] if k not in current]:
                    del us["low_ack"][k]   # 已補貨：下次再低於標準時重新通知
            for x in lows:
                ack = us["low_ack"].get(str(x["pk"]))
                unread = ack is None or x["qty"] < ack
                items.append({"id": f"low:{x['pk']}", "kind": "low_stock", "severity": "warn", "read": not unread,
                              "time": None, "company": x["company"], "tags": [KIND_ZH["low_stock"]],
                              "title": f"📉 低庫存：{x['ipn']} 現有 {fmt(x['qty'])}，最低標準 {fmt(x['min'])}",
                              "detail": f"{x['name']}（{x['company']}）"})
            events = []
            for ev in reversed(self.store.state["events"]):
                if ev["actor"] == ident.username:
                    continue   # 自己的操作不通知自己
                mine = {c: k for c, k in ev["targets"].items() if c in visible}
                if not mine:
                    continue
                kinds = sorted({k for ks in mine.values() for k in ks}, key=KIND_ORDER.index)
                read = ev["id"] <= us["read_up_to"] or ev["id"] in us["read"]
                events.append(self._render_event(ev, kinds, read))
                if len(events) >= self.cfg["max_feed_items"]:
                    break
            items += events
        unread = sum(1 for i in items if not i["read"])
        return {"ok": True, "user": {"name": ident.username, "companies": self.companies_of(ident),
                                     "superuser": ident.is_superuser, "sees": sorted(visible)},
                "unread": unread, "items": items, "warnings": warnings,
                "server_time": datetime.now(timezone.utc).isoformat()}

    def _render_event(self, ev, kinds, read):
        primary = kinds[0]
        ipn, qty = ev["ipn"] or ev["part_name"], fmt(ev["qty"])
        where = ev["loc_path"] or ev["dest_path"] or ev["src_path"] or ""
        if primary == "zero":
            title = f"⚠️ 庫存歸零：{ipn} 在 {where}（{ev['actor_label']}{ev['action']}）"
        elif primary == "large":
            title = f"⚠️ 大量{ev['action']}：{ipn} {qty} 件（{ev['actor_label']}）"
        elif primary == "transfer_out":
            title = f"📤 {ev['actor_label']} 把 {qty} 件 {ipn} 從 {ev['src_company']} 調出"
        else:
            title = f"📥 {ev['actor_label']} 把 {qty} 件 {ipn} 調進 {ev['dest_company']}"
        parts = []
        if ev["src_path"] or ev["dest_path"]:
            parts.append(f"{ev['src_path'] or '來源未知'} → {ev['dest_path'] or '未知'}")
        elif where:
            parts.append(where)
        if ev["result_qty"] is not None and ev["type"] in (T_REMOVE, T_ADD, T_COUNT):
            parts.append(f"操作後剩 {fmt(ev['result_qty'])} 件")
        if ev["notes"]:
            parts.append(f"備註：{ev['notes']}")
        severity = "danger" if primary in ("zero", "large") else "warn"
        return {"id": str(ev["id"]), "kind": primary, "severity": severity, "read": read, "time": ev["time"],
                "company": sorted(ev["targets"])[0], "tags": [KIND_ZH[k] for k in kinds],
                "title": title, "detail": "　".join(parts)}

    def mark_read(self, auth, ids=None, all_=False, up_to=None):
        """標示已讀。all_ 搭配 up_to（使用者畫面上看到的最新事件編號）：只標到那一筆，
        在他看到之後才進來的事件仍維持未讀。沒有提供 up_to 時，先處理最新異動，再標到目前最新一筆。"""
        ident = self.identify(auth)
        visible = self.visible_companies(ident)
        if all_ and not isinstance(up_to, int):
            self.process(auth)
        with self.lock:
            us = self._user_state(ident.username)
            if all_:
                known = max([ev["id"] for ev in self.store.state["events"]] + [self.store.state["cursor"]])
                bound = known if not isinstance(up_to, int) else max(0, min(up_to, known))
                us["read_up_to"] = max(us["read_up_to"], bound)
                us["read"] = [n for n in us["read"] if n > us["read_up_to"]]
                try:
                    for x in self.low_stock(auth):
                        if x["company"] in visible:
                            us["low_ack"][str(x["pk"])] = x["qty"]
                except UpstreamError:
                    pass   # 低庫存暫時讀不到時，仍然完成事件的已讀
            else:
                for raw in ids or []:
                    raw = str(raw)
                    if raw.startswith("low:"):
                        pk = raw[4:]
                        try:
                            for x in self.low_stock(auth):
                                if str(x["pk"]) == pk and x["company"] in visible:
                                    us["low_ack"][pk] = x["qty"]
                        except UpstreamError:
                            pass
                    elif raw.isdigit():
                        n = int(raw)
                        if n > us["read_up_to"] and n not in us["read"]:
                            us["read"].append(n)
                us["read"] = [n for n in us["read"] if n > us["read_up_to"]][-1000:]
            self.store.save()
        return {"ok": True}


def fmt(n):
    if n is None:
        return "?"
    return str(int(n)) if float(n) == int(n) else f"{n:g}"


# ---------------------------------------------------------------- HTTP

def make_handler(notifier):
    class Handler(BaseHTTPRequestHandler):
        server_version = "inventory-notifier"

        def log_message(self, fmt_, *args):
            log(self.address_string(), fmt_ % args)

        def _auth(self):
            return {"cookie": self.headers.get("Cookie", ""), "authorization": self.headers.get("Authorization", ""),
                    "host": self.headers.get("Host", "")}

        def _send(self, code, data):
            raw = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _guard(self, fn):
            try:
                self._send(200, fn())
            except UpstreamError as e:
                if e.status in (401, 403):
                    self._send(401, {"ok": False, "error": "not_authenticated", "message": "請先登入 InvenTree。"})
                else:
                    self._send(502, {"ok": False, "error": "upstream", "message": str(e)})
            except Exception as e:  # noqa: BLE001
                log("未預期的錯誤：", repr(e))
                self._send(500, {"ok": False, "error": "internal", "message": "通知服務發生錯誤。"})

        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/notify/api/health":
                return self._send(200, {"ok": True})
            if path == "/notify/api/feed":
                return self._guard(lambda: notifier.feed(self._auth()))
            self._send(404, {"ok": False, "error": "not_found"})

        def do_POST(self):
            path = urllib.parse.urlparse(self.path).path
            if path != "/notify/api/read":
                return self._send(404, {"ok": False, "error": "not_found"})
            if self.headers.get(REQUIRED_HEADER[0]) != REQUIRED_HEADER[1]:
                return self._send(400, {"ok": False, "error": "bad_request", "message": "缺少必要的標頭。"})
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(min(length, 100000)) or b"{}")
            except ValueError:
                return self._send(400, {"ok": False, "error": "bad_json"})
            ids = body.get("ids") if isinstance(body.get("ids"), list) else []
            up_to = body.get("up_to") if isinstance(body.get("up_to"), int) and not isinstance(body.get("up_to"), bool) else None
            self._guard(lambda: notifier.mark_read(self._auth(), ids=ids, all_=bool(body.get("all")), up_to=up_to))

    return Handler


def load_config(path):
    try:
        with open(path, encoding="utf-8-sig") as f:   # 容許 Windows 工具寫入的 BOM
            cfg = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"無法讀取設定檔 {path}：{e}")
    for c in cfg.get("companies", []):
        if not c.get("name") or not c.get("group"):
            sys.exit("設定檔的 companies 每一筆都需要 name 與 group。")
    if not cfg.get("companies"):
        sys.exit("設定檔沒有任何公司（companies）。")
    return cfg


def main():
    config = load_config(os.environ.get("NOTIFIER_CONFIG", "/app/config.json"))
    client = InvenTreeClient(os.environ.get("NOTIFIER_INVENTREE_URL", "http://inventree-server:8000"))
    store = StateStore(os.environ.get("NOTIFIER_STATE", "/data/state.json"))
    notifier = Notifier(config, client, store)
    port = int(os.environ.get("NOTIFIER_PORT", "8090"))
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(notifier))
    log(f"通知服務啟動：port {port}，公司 {[c['name'] for c in notifier.companies]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
