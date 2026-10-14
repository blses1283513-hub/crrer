"""SHOPLINE 官網訂單同步（P7）。對應規則在 shoplinerules.py。

- 設定（只有管理員）：商店代號、API 金鑰（只存在系統裡，畫面只顯示最後 4 碼）、同步間隔、從何時開始匯入。預設關閉。
- 每分鐘檢查一次，到了設定的間隔就向 SHOPLINE 查詢「這段時間有更新的訂單」（GET /v1/orders，updated_after）；
  每筆訂單依 SHOPLINE 訂單 ID 只處理一次（重複查到也不會重複建立）。
- 官網訂單 → 銷售訂單（官網散客、銷售管道「官網」、從總公司出貨）；取消或全額退款 → 還沒出貨的自動取消。
- 對不到料號等情況放進「待處理」，在「SHOPLINE 官網訂單」頁面處理：修正後「重新處理」，或「標記已人工處理」。
"""

import json
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import frappe
from frappe import _

from nila_app import perms, stock
from nila_app import shoplinerules as S

SETTINGS = "Nila SHOPLINE Settings"
LOG = "Nila SHOPLINE Order"
WEB_CUSTOMER = "官網散客"
WEB_CHANNEL = "官網"
WEB_PRICE_LIST = "官網售價"
LOCK = "nila_shopline_sync"
MAX_PAGES = 200  # 單次最多查 1 萬筆（50 筆 × 200 頁），避免設定錯誤時跑不停
OVERLAP = timedelta(minutes=2)  # 每次往前多查 2 分鐘，避免邊界上的訂單漏掉（重複查到不會重複建立）
TIMEOUT = 30


# ---------- 連線 ----------

def base_url():
    # 測試時可在 site_config 設定 nila_shopline_base_url 指向模擬的 SHOPLINE
    return (frappe.conf.get("nila_shopline_base_url") or S.BASE_URL).rstrip("/")


def _token():
    from frappe.utils.password import get_decrypted_password

    try:
        return get_decrypted_password(SETTINGS, SETTINGS, "token", raise_exception=False) or ""
    except Exception:
        # 換電腦還原時加密金鑰不同，舊的金鑰解不開：請重新輸入
        return ""


class Client:
    def __init__(self, token, handle=None):
        if not token:
            raise S.ShoplineError("還沒有設定 API 金鑰")
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/json",
                        "User-Agent": handle or "nila-erpnext"}

    def get(self, path, params=None, tries=5):
        import requests

        for attempt in range(tries):
            try:
                r = requests.get(base_url() + path, params=params, headers=self.headers, timeout=TIMEOUT)
            except requests.RequestException as e:
                if attempt == tries - 1:
                    raise S.ShoplineError(f"連不到 SHOPLINE：{e.__class__.__name__}") from e
                time.sleep(2 ** attempt)
                continue
            if r.status_code == 429 or r.status_code >= 500:  # 超過每秒 20 次或 SHOPLINE 暫時有問題：稍等再試
                if attempt == tries - 1:
                    raise S.ShoplineError(f"SHOPLINE 暫時無法回應（HTTP {r.status_code}），稍後會自動再試")
                time.sleep(float(r.headers.get("Retry-After") or 2 ** attempt))
                continue
            if r.status_code in (401, 403):
                raise S.ShoplineError(f"API 金鑰無效、已過期或沒有權限（HTTP {r.status_code}），請到 SHOPLINE 後台確認")
            if r.status_code != 200:
                raise S.ShoplineError(f"SHOPLINE 回應錯誤（HTTP {r.status_code}）：{r.text[:200]}")
            try:
                return r.json()
            except ValueError as e:
                raise S.ShoplineError("SHOPLINE 回應的資料格式不正確") from e


def _client():
    return Client(_token(), frappe.db.get_single_value(SETTINGS, "handle"))


# ---------- 設定頁 ----------

def _now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _tz():
    return ZoneInfo(frappe.utils.get_system_timezone() or "Asia/Taipei")


def _local_to_utc(value):
    dt = frappe.utils.get_datetime(value)
    return dt.replace(tzinfo=_tz()).astimezone(timezone.utc).replace(tzinfo=None)


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _local_date(value):
    dt = _parse_iso(value)
    if not dt:
        return frappe.utils.nowdate()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_tz()).date().isoformat()


def _counts():
    rows = frappe.db.sql(f"select state, count(*) n from `tab{LOG}` group by state", as_dict=True)
    return {r.state: r.n for r in rows}


@frappe.whitelist()
def get_settings():
    perms.require("shopline")
    s = frappe.get_single(SETTINGS)
    token = _token() if perms.can("shopline_settings") else ""
    return {
        "can_edit": perms.can("shopline_settings"),
        "enabled": s.enabled, "handle": s.handle or "", "interval": s.interval or 5, "exclude_pos": s.exclude_pos,
        "import_since": str(s.import_since or ""), "token_set": bool(token), "token_hint": S.mask(token), "merchant_name": s.merchant_name or "", "synced_until": s.synced_until or "",
        "last_run": str(s.last_run or "")[:16], "last_ok": str(s.last_ok or "")[:16], "last_result": s.last_result or "",
        "counts": _counts(), "states": S.STATES, "scheduler": not frappe.utils.scheduler.is_scheduler_disabled(),
    }


@frappe.whitelist()
def save_settings(data):
    """data = {enabled, handle, interval, exclude_pos, import_since, token（空白表示不改）}。"""
    perms.require("shopline_settings")
    data = frappe._dict(frappe.parse_json(data))
    s = frappe.get_single(SETTINGS)
    old_since = str(s.import_since or "")
    token = str(data.get("token") or "").strip()
    if token:
        s.token = token
    s.handle = str(data.get("handle") or "").strip()
    s.interval = frappe.utils.cint(data.get("interval")) or 5
    s.exclude_pos = 1 if frappe.utils.cint(data.get("exclude_pos")) else 0
    s.import_since = data.get("import_since") or None
    s.enabled = 1 if frappe.utils.cint(data.get("enabled")) else 0
    if s.enabled:
        if not token and not _token():
            frappe.throw(_("請先輸入 API 金鑰"))
        if not s.import_since:
            s.import_since = frappe.utils.now_datetime().replace(microsecond=0)  # 預設從現在開始，不匯入以前的訂單
    if str(s.import_since or "") != old_since:
        s.synced_until = ""  # 改了開始時間：從新的時間重新查（已處理的訂單不會重複建立）
    s.flags.ignore_permissions = True
    s.save()
    return get_settings()


@frappe.whitelist()
def test_connection(token=None, handle=None):
    """用輸入的（或已儲存的）金鑰呼叫 GET /v1/token/info，回傳商店名稱。成功時記下商店名稱；沒填商店代號時自動帶入。"""
    perms.require("shopline_settings")
    token = str(token or "").strip() or _token()
    handle = str(handle or "").strip() or frappe.db.get_single_value(SETTINGS, "handle")
    try:
        info = Client(token, handle).get("/token/info")
    except S.ShoplineError as e:
        return {"ok": False, "message": str(e)}
    merchant = (info or {}).get("merchant") or {}
    name = merchant.get("name") or merchant.get("handle") or ""
    if str(token) == _token():  # 只有測試已儲存的金鑰時才更新設定
        frappe.db.set_single_value(SETTINGS, "merchant_name", name)
        if not frappe.db.get_single_value(SETTINGS, "handle") and merchant.get("handle"):
            frappe.db.set_single_value(SETTINGS, "handle", merchant["handle"])
    return {"ok": True, "message": _("連線成功：{0}").format(name or _("（沒有商店名稱）")), "merchant": name,
            "handle": merchant.get("handle") or ""}


# ---------- 同步 ----------

def scheduled():
    """排程每分鐘呼叫：已啟用、而且距離上次同步超過設定的間隔才執行。"""
    if not frappe.db.get_single_value(SETTINGS, "enabled"):
        return
    interval = frappe.utils.cint(frappe.db.get_single_value(SETTINGS, "interval")) or 5
    last = frappe.db.get_single_value(SETTINGS, "last_run")
    if last and frappe.utils.now_datetime() < frappe.utils.get_datetime(last) + timedelta(minutes=interval) - timedelta(seconds=20):
        return
    sync()


@frappe.whitelist()
def sync_now():
    perms.require("shopline_settings")
    with perms.elevated():
        return sync(manual=True)


def sync(commit=True, manual=False, until=None):
    """查詢上次同步之後有更新的官網訂單並處理。同一時間只會有一個同步在跑。"""
    got = frappe.db.sql("select get_lock(%s, 0)", LOCK)[0][0]
    if not got:
        return {"ok": False, "message": _("另一個同步正在進行，請稍後再試")}
    try:
        return _sync(commit, until)
    finally:
        frappe.db.sql("select release_lock(%s)", LOCK)


def _sync(commit, until=None):
    s = frappe.get_single(SETTINGS)
    now = frappe.utils.now_datetime().replace(microsecond=0)
    until = until or _now_utc().replace(tzinfo=None)
    if s.synced_until:
        since = frappe.utils.get_datetime(s.synced_until) - OVERLAP
    elif s.import_since:
        since = _local_to_utc(s.import_since)
    else:
        since = until - timedelta(days=1)
    stats = {}
    try:
        client = _client()
        orders = _fetch(client, {"updated_after": S.utc_text(since), "updated_before": S.utc_text(until)})
        ctx = _context(s)
        for order in orders:
            state = process(order, ctx, commit=commit)
            stats[state] = stats.get(state, 0) + 1
    except S.ShoplineError as e:
        msg = _("失敗：{0}").format(e)
        _save_status(last_run=now, last_result=msg)
        if commit:
            frappe.db.commit()
        _notify_failure(msg)
        return {"ok": False, "message": msg}
    result = _("查到 {0} 筆有更新的訂單").format(sum(stats.values())) + (
        "：" + "、".join(f"{k} {v}" for k, v in stats.items()) if stats else "")
    _save_status(last_run=now, last_ok=now, synced_until=S.utc_text(until), last_result=result)
    if stats.get(S.PENDING):
        _notify(_("SHOPLINE 官網訂單有 {0} 筆待處理").format(_counts().get(S.PENDING, 0)))
    if commit:
        frappe.db.commit()
    return {"ok": True, "message": result, "stats": stats}


def _save_status(**values):
    for k, v in values.items():
        frappe.db.set_single_value(SETTINGS, k, v)


def _fetch(client, params):
    """依頁數查完所有符合的訂單（每頁 50 筆，依建立時間由舊到新）。"""
    out, page = [], 1
    while True:
        res = client.get("/orders", dict(params, per_page=S.PER_PAGE, page=page, sort_by="asc"))
        out += res.get("items") or []
        total = ((res.get("pagination") or {}).get("total_pages")) or 1
        if page >= total or not res.get("items"):
            return out
        page += 1
        if page > MAX_PAGES:
            raise S.ShoplineError(_("一次有超過 {0} 筆訂單，請把「從這個時間之後」設得晚一點").format(MAX_PAGES * S.PER_PAGE))


def _context(s=None):
    s = s or frappe.get_single(SETTINGS)
    items = frappe.get_all("Item", filters={"disabled": 0, "has_variants": 0}, pluck="name")
    return {"skus": {i.upper(): i for i in items}, "exclude_pos": bool(s.exclude_pos)}


def _existing(shopline_id):
    log = frappe.db.get_value(LOG, shopline_id, ["name", "state", "sales_order", "fingerprint", "message"], as_dict=True)
    if not log:
        so = frappe.db.get_value("Sales Order", {"nila_shopline_id": shopline_id, "docstatus": ["<", 2]}, "name")
        if not so:
            return None
        log = frappe._dict(state=S.CREATED, sales_order=so, fingerprint=None, message="")
    out = dict(log)
    if log.sales_order:
        so = frappe.db.get_value("Sales Order", log.sales_order, ["docstatus", "per_delivered"], as_dict=True)
        if so:
            out.update(so_docstatus=so.docstatus, delivered=(so.per_delivered or 0) > 0)
        else:
            out["sales_order"] = None
    return out


def process(order, ctx=None, commit=False):
    """處理一筆官網訂單，回傳處理結果（紀錄的狀態）。出錯時這一筆放進待處理，不影響其他訂單。"""
    ctx = ctx or _context()
    info = S.summary(order)
    sid = info["shopline_id"]
    if not sid:
        return S.SKIPPED
    existing = _existing(sid)
    frappe.db.savepoint("nila_shopline")
    try:
        p = S.plan(order, ctx["skus"].keys(), existing, ctx["exclude_pos"])
        so = (existing or {}).get("sales_order")
        fp = (existing or {}).get("fingerprint")
        if p["action"] == S.CREATE:
            so = _create_sales_order(order, p["lines"], ctx["skus"])
            fp = S.fingerprint(p["lines"])
            p["message"] = _("已建立銷售訂單 {0}").format(so)
        elif p["action"] == S.CANCEL:
            _cancel_sales_order(so)
        _write_log(info, p, so, fp)
    except Exception as e:
        frappe.db.rollback(save_point="nila_shopline")
        frappe.log_error(f"SHOPLINE 訂單 {info['order_number'] or sid}", frappe.get_traceback())
        msg = str(e) if isinstance(e, frappe.ValidationError) else e.__class__.__name__
        p = {"state": S.PENDING, "message": _("系統處理時發生錯誤：{0}（請看錯誤紀錄，修正後按「重新處理」）").format(
            frappe.utils.strip_html(msg)[:300]), "lines": S.order_lines(order)[0]}
        _write_log(info, p, (existing or {}).get("sales_order"), (existing or {}).get("fingerprint"))
    if commit:
        frappe.db.commit()
    return p["state"]


def _write_log(info, p, so, fp):
    sid = info["shopline_id"]
    doc = frappe.get_doc(LOG, sid) if frappe.db.exists(LOG, sid) else frappe.new_doc(LOG)
    doc.update({
        "shopline_id": sid, "order_number": info["order_number"], "state": p["state"], "sales_order": so,
        "message": p["message"], "status": S.STATUS_LABELS.get(info["status"], info["status"]),
        "payment_status": S.PAYMENT_LABELS.get(info["payment_status"], info["payment_status"]),
        "customer_name": info["customer_name"], "total": info["total"], "shopline_created": info["created_at"],
        "shopline_updated": info["updated_at"], "fingerprint": fp,
    })
    if p.get("lines"):
        doc.items_json = json.dumps(p["lines"], ensure_ascii=False)
    doc.flags.ignore_permissions = True
    doc.save() if not doc.is_new() else doc.insert()
    return doc


def _create_sales_order(order, lines, skus):
    sid = str(order["id"])
    dup = frappe.db.get_value("Sales Order", {"nila_shopline_id": sid, "docstatus": ["<", 2]}, "name")
    if dup:
        return dup
    hq = stock.hq_warehouse()
    if not hq:
        frappe.throw(_("找不到總公司倉庫"))
    day = _local_date(order.get("created_at"))
    number = str(order.get("order_number") or sid)
    doc = frappe.get_doc({
        "doctype": "Sales Order", "customer": WEB_CUSTOMER, "company": frappe.db.get_value("Warehouse", hq, "company"),
        "transaction_date": day, "delivery_date": day, "set_warehouse": hq, "selling_price_list": WEB_PRICE_LIST,
        "po_no": number, "nila_channel": WEB_CHANNEL, "nila_shopline_id": sid, "nila_shopline_number": number,
        "items": [{"item_code": skus[ln["sku"]], "qty": ln["qty"], "warehouse": hq, "delivery_date": day} for ln in lines],
    })
    doc.flags.nila_shopline = True  # 官網已經賣出：停售的商品也要建立（請在官網下架）
    doc.set_missing_values()
    for d, ln in zip(doc.items, lines):
        d.rate = ln["rate"]
    doc.calculate_taxes_and_totals()
    customer = (order.get("customer_name") or "").strip()
    total = S.money(order.get("total"))
    doc.remarks = _("SHOPLINE 官網訂單 {0}{1}{2}").format(
        number, f"，顧客：{customer}" if customer else "", f"，官網訂單金額（含運費）：{total:g}" if total is not None else "")
    doc.insert(ignore_permissions=True)
    doc.submit()
    return doc.name


def _cancel_sales_order(name):
    doc = frappe.get_doc("Sales Order", name)
    if doc.docstatus == 1:
        doc.flags.ignore_permissions = True
        doc.cancel()


def _notify(subject, link="/app/nila-shopline"):
    from nila_app import levels as L

    users = {"Administrator"} | set(frappe.get_all("Has Role", filters={
        "role": ["in", ["System Manager", L.ADMIN, L.MANAGER]], "parenttype": "User"}, pluck="parent"))
    for u in sorted(set(frappe.get_all("User", filters={"name": ["in", list(users)], "enabled": 1}, pluck="name"))):
        frappe.get_doc({"doctype": "Notification Log", "subject": subject, "for_user": u, "type": "Alert",
                        "link": link}).insert(ignore_permissions=True)


def _notify_failure(msg):
    """連續失敗時只在第一次通知（之後成功一次才會再通知）。"""
    last_ok = frappe.db.get_single_value(SETTINGS, "last_ok")
    key = "nila_shopline_failure_notified"
    if frappe.cache.get_value(key) == str(last_ok):
        return
    frappe.cache.set_value(key, str(last_ok))
    _notify(_("SHOPLINE 官網訂單同步{0}").format(msg))


# ---------- 官網訂單頁（待處理清單） ----------

@frappe.whitelist()
def list_orders(state=None, q=None, limit=100):
    perms.require("shopline")
    filters = {"state": state} if state else {}
    or_filters = None
    if q:
        q = f"%{str(q).strip()}%"
        or_filters = {"order_number": ["like", q], "customer_name": ["like", q], "sales_order": ["like", q], "message": ["like", q]}
    rows = frappe.get_all(LOG, filters=filters, or_filters=or_filters, fields=[
        "name", "order_number", "state", "sales_order", "message", "status", "payment_status", "customer_name", "total",
        "shopline_created", "items_json", "handled_by", "modified"], order_by="modified desc", limit=frappe.utils.cint(limit) or 100)
    for r in rows:
        r["items"] = json.loads(r.pop("items_json") or "[]")
        r["shopline_created"] = _local_text(r["shopline_created"])
    return {"rows": rows, "counts": _counts(), "can_edit": perms.can("shopline_settings")}


def _local_text(value):
    dt = _parse_iso(value)
    if not dt:
        return value or ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_tz()).strftime("%Y-%m-%d %H:%M")


@frappe.whitelist()
def retry(name):
    """重新向 SHOPLINE 查詢這筆訂單並處理（例如補上商品或改好 SKU 之後）。"""
    perms.require("shopline")
    if not frappe.db.exists(LOG, name):
        frappe.throw(_("找不到這筆官網訂單"))
    with perms.elevated():
        try:
            res = _client().get("/orders", {"order_ids[]": [name], "per_page": 1})
        except S.ShoplineError as e:
            frappe.throw(str(e))
        items = res.get("items") or []
        if not items:
            gone = name in ((res.get("error") or {}).get("gone") or [])
            frappe.throw(_("SHOPLINE 已封存這筆訂單，無法重新處理") if gone else _("SHOPLINE 找不到這筆訂單"))
        state = process(items[0])
    return frappe.db.get_value(LOG, name, ["state", "message", "sales_order"], as_dict=True) | {"result": state}


@frappe.whitelist()
def mark_handled(name, note=None):
    """待處理的訂單已經人工處理好：標記後不再提醒（官網之後又有變動時會重新判斷）。"""
    perms.require("shopline")
    doc = frappe.get_doc(LOG, name)
    if doc.state != S.PENDING:
        frappe.throw(_("只有待處理的訂單可以標記"))
    lines = json.loads(doc.items_json or "[]")
    doc.state = S.HANDLED
    doc.handled_by = frappe.session.user
    doc.message = _("人工處理：{0}").format(str(note or "").strip() or _("（沒有備註）")) + _("。原因：{0}").format(doc.message or "")
    if lines and doc.sales_order:
        doc.fingerprint = S.fingerprint(lines)  # 以目前官網的內容為準，之後再改才會又放進待處理
    doc.flags.ignore_permissions = True
    doc.save()
    return {"state": doc.state}
