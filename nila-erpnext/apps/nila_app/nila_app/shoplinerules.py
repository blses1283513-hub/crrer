"""SHOPLINE 官網訂單 → ERPNext 的對應規則（P7）。純邏輯，不需要 ERPNext，可單獨測試。

依 SHOPLINE Open API（GET /v1/orders）的欄位：
- status：temp（暫存）、pending（處理中）、confirmed（已確認）、completed（已完成）、cancelled（已取消）、removed（已刪除）
- order_payment.status：pending、failed、expired、completed、refunding、refunded
- created_by：openapi、admin、shop、shop_crm、pos、sc、mc、import；type：general、preorder、return、exchange
- subtotal_items[]：item_type（Product、AddonProduct、Gift、CustomProduct）、sku、quantity、
  item_price（單價）、total（單價 × 數量）、discounted_total（扣掉折扣後）；金額是 {cents, dollars, ...}

規則：
- 官網訂單建立「銷售訂單」（客戶：官網散客、銷售管道：官網），總公司缺貨也照樣建立，由訂單調度處理。
- SHOPLINE 的 SKU 必須等於 ERPNext 的商品料號（例如 0001-LT-XS）；有對不到的就放進「待處理」，不建立訂單。
- 已取消、已刪除或已全額退款：還沒出貨的銷售訂單自動取消；已經出貨的放進「待處理」，請人工處理退貨。
- SHOPLINE 門市 POS 的訂單預設不匯入（門市銷售在妮菈系統做）；退貨、換貨單放進「待處理」。
- 建立後官網又修改了商品或數量：放進「待處理」，請人工確認（不自動改已送出的訂單）。
"""

import hashlib

BASE_URL = "https://open.shopline.io/v1"
PER_PAGE = 50
OPEN_STATUSES = {"pending", "confirmed", "completed"}
GONE_STATUSES = {"cancelled", "removed"}
SKIP_STATUSES = {"temp"}
REFUNDED = {"refunded"}
LINE_TYPES = {"Product", "AddonProduct", "Gift"}  # CustomProduct（自訂商品）沒有 SKU，不匯入
MANUAL_TYPES = {"return", "exchange"}

# 紀錄的狀態
CREATED, CANCELLED, PENDING, SKIPPED, HANDLED = "已建立訂單", "已取消訂單", "待處理", "略過", "已人工處理"
STATES = [CREATED, CANCELLED, PENDING, SKIPPED, HANDLED]

# 動作
CREATE, CANCEL, MARK_PENDING, SKIP, NOTHING = "create", "cancel", "pending", "skip", "nothing"

STATUS_LABELS = {"temp": "暫存", "pending": "處理中", "confirmed": "已確認", "completed": "已完成",
                 "cancelled": "已取消", "removed": "已刪除"}
PAYMENT_LABELS = {"pending": "未付款", "failed": "付款失敗", "expired": "付款逾期", "completed": "已付款",
                  "refunding": "退款中", "refunded": "已退款"}


class ShoplineError(Exception):
    pass


def money(m):
    """SHOPLINE 金額 {cents, dollars, ...} → 數字（以 dollars 為準；新台幣 cents 與 dollars 相同）。"""
    if m is None:
        return None
    if isinstance(m, (int, float)):
        return float(m)
    if isinstance(m, dict):
        for k in ("dollars", "cents"):
            if m.get(k) is not None:
                try:
                    return float(m[k])
                except (TypeError, ValueError):
                    return None
    return None


def order_lines(order):
    """訂單明細 → ([{"sku", "qty", "rate", "title"}], [錯誤])。同一個 SKU 合併；單價用扣掉折扣後的金額 ÷ 數量。"""
    merged, errors = {}, []
    for it in order.get("subtotal_items") or []:
        kind = it.get("item_type") or "Product"
        if kind not in LINE_TYPES:
            continue
        title = _title(it)
        sku = str(it.get("sku") or "").strip().upper()
        try:
            qty = float(it.get("quantity") or 0)
        except (TypeError, ValueError):
            qty = 0
        if not sku:
            errors.append(f"「{title}」沒有 SKU")
            continue
        if qty <= 0:
            continue
        amount = next((v for v in (money(it.get("discounted_total")), money(it.get("total"))) if v is not None), None)
        if amount is None:
            amount = (money(it.get("item_price")) or money(it.get("price")) or 0) * qty
        row = merged.setdefault(sku, {"sku": sku, "qty": 0, "amount": 0.0, "title": title})
        row["qty"] += qty
        row["amount"] += amount
    lines = []
    for row in merged.values():
        q = row["qty"]
        lines.append({"sku": row["sku"], "qty": int(q) if q == int(q) else q,
                      "rate": round(row["amount"] / q, 2) if q else 0, "title": row["title"]})
    return lines, errors


def _title(it):
    t = it.get("title_translations") or {}
    if isinstance(t, dict):
        for k in ("zh-hant", "zh-TW", "zh_tw", "en"):
            if t.get(k):
                return t[k]
        for v in t.values():
            if v:
                return v
    return str(it.get("sku") or it.get("id") or "")


def fingerprint(lines):
    """訂單內容（SKU 與數量）的指紋：建立訂單後官網又修改時可以發現。"""
    key = "|".join(f"{ln['sku']}x{ln['qty']}" for ln in sorted(lines, key=lambda x: x["sku"]))
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def summary(order):
    """紀錄用的基本資料。"""
    pay = (order.get("order_payment") or {}).get("status")
    return {"shopline_id": str(order.get("id") or ""), "order_number": str(order.get("order_number") or ""),
            "status": order.get("status") or "", "payment_status": pay or "",
            "customer_name": order.get("customer_name") or "", "total": money(order.get("total")),
            "created_at": order.get("created_at") or "", "updated_at": order.get("updated_at") or ""}


def plan(order, known_skus, existing=None, exclude_pos=True):
    """決定這筆官網訂單要做什麼。

    known_skus：ERPNext 可用的商品料號（大寫）。
    existing：之前處理過的紀錄 {"state", "sales_order", "so_docstatus", "delivered", "fingerprint"}，沒有就是 None。
    回傳 {"action", "state", "message", "lines"}。
    """
    existing = existing or {}
    status = order.get("status") or ""
    pay = (order.get("order_payment") or {}).get("status") or ""
    so = existing.get("sales_order")
    so_open = bool(so) and existing.get("so_docstatus") == 1
    lines, errors = order_lines(order)

    def out(action, state, message="", lns=None):
        return {"action": action, "state": state, "message": message, "lines": lns or []}

    if exclude_pos and order.get("created_by") == "pos":
        return out(SKIP, SKIPPED, "SHOPLINE 門市 POS 的訂單（門市銷售在妮菈系統處理）")
    if (order.get("type") or "general") in MANUAL_TYPES:
        if existing.get("state") in (HANDLED, PENDING):
            return out(NOTHING, existing["state"], existing.get("message", ""))
        return out(MARK_PENDING, PENDING, "官網退貨／換貨單，請人工處理")

    gone = status in GONE_STATUSES or pay in REFUNDED
    if gone:
        why = "已全額退款" if pay in REFUNDED and status not in GONE_STATUSES else f"官網訂單{STATUS_LABELS.get(status, status)}"
        if so_open:
            if existing.get("delivered"):
                if existing.get("state") == HANDLED:
                    return out(NOTHING, HANDLED, existing.get("message", ""))
                return out(MARK_PENDING, PENDING, f"{why}，但銷售訂單 {so} 已經出貨，請人工處理退貨")
            return out(CANCEL, CANCELLED, f"{why}，自動取消銷售訂單 {so}")
        if so and existing.get("so_docstatus") == 2:
            return out(NOTHING, CANCELLED, existing.get("message") or f"{why}（銷售訂單 {so} 已取消）")
        if existing.get("state") == HANDLED:
            return out(NOTHING, HANDLED, existing.get("message", ""))
        return out(SKIP, SKIPPED, f"{why}，不建立訂單")

    if status in SKIP_STATUSES or status not in OPEN_STATUSES:
        return out(SKIP, SKIPPED, f"官網訂單狀態「{STATUS_LABELS.get(status, status or '空白')}」，還不需要建立")

    if so:
        if existing.get("so_docstatus") == 2:
            # 系統裡的訂單被人取消了，官網卻還是有效的：請人工確認
            if existing.get("state") == HANDLED:
                return out(NOTHING, HANDLED, existing.get("message", ""))
            return out(MARK_PENDING, PENDING, f"銷售訂單 {so} 已在系統取消，但官網訂單仍有效，請人工確認")
        # 人工處理後會把指紋更新成當時的內容，之後再改才會又放進待處理
        if existing.get("fingerprint") and lines and not errors and fingerprint(lines) != existing["fingerprint"]:
            return out(MARK_PENDING, PENDING, f"官網修改了商品或數量，銷售訂單 {so} 沒有自動修改，請人工確認", lines)
        return out(NOTHING, existing.get("state") or CREATED, existing.get("message", ""))

    if existing.get("state") == HANDLED:
        return out(NOTHING, HANDLED, existing.get("message", ""))
    unknown = sorted({ln["sku"] for ln in lines} - set(known_skus))
    if unknown:
        errors.append("找不到這些料號：" + "、".join(unknown))
    if errors:
        return out(MARK_PENDING, PENDING, "；".join(errors) + "（請在 SHOPLINE 把 SKU 改成系統的料號，或在系統新增商品後按「重新處理」）", lines)
    if not lines:
        return out(MARK_PENDING, PENDING, "訂單沒有可以匯入的商品")
    return out(CREATE, CREATED, "", lines)


def utc_text(dt):
    """datetime（UTC）→ SHOPLINE 查詢格式 YYYY-MM-DD HH:MM:SS。"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def mask(token):
    """畫面上只顯示金鑰的最後 4 碼。"""
    token = str(token or "")
    if not token:
        return ""
    return "•" * 8 + token[-4:] if len(token) > 8 else "•" * 8
