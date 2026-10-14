"""門市與會員規則：手機號碼、購物車、退貨與退款上限、5 個層級的權限。純邏輯，不需要 ERPNext，可單獨測試。"""

import re

# ---------- 5 個層級（P6 的帳號管理也用這裡） ----------

ADMIN, MANAGER, HQ_STAFF, STORE_LEAD, STORE_STAFF = "妮菈管理員", "妮菈營運主管", "妮菈總公司作業", "妮菈門市店長", "妮菈門市店員"
LEVELS = [ADMIN, MANAGER, HQ_STAFF, STORE_LEAD, STORE_STAFF]
STORE_LEVELS = {STORE_LEAD, STORE_STAFF}  # 只能看、只能操作自己的門市

ALL = set(LEVELS)
CAPS = {
    "store_sale": ALL,                               # 門市銷售
    "store_return": {ADMIN, MANAGER, STORE_LEAD},     # 退貨、退款
    "price_override": {ADMIN, MANAGER, STORE_LEAD},   # 單筆改價、打折
    "member": ALL,                                    # 會員查詢、新增
    "member_merge": {ADMIN, MANAGER},                 # 合併會員
    "sales_report": {ADMIN, MANAGER, STORE_LEAD},     # 消費報表
    "barcode": {ADMIN, MANAGER, HQ_STAFF, STORE_LEAD},
}


def can(cap, roles, user=None):
    """roles：使用者的角色。Administrator 與 System Manager（系統最高權限）一律可以。"""
    roles = set(roles or ())
    if user == "Administrator" or "System Manager" in roles:
        return True
    return bool(CAPS[cap] & roles)


def store_scoped(roles, user=None):
    """只有門市層級（店長、店員）、又沒有更高層級的帳號，才限定在自己的門市。"""
    roles = set(roles or ())
    if user == "Administrator" or "System Manager" in roles or roles & {ADMIN, MANAGER, HQ_STAFF}:
        return False
    return bool(roles & STORE_LEVELS)


# ---------- 會員手機 ----------

class RetailError(ValueError):
    pass


def normalize_phone(raw):
    """統一手機號碼格式：去掉空白、橫線、括號；+886 / 886 開頭改成 0。回傳 09xxxxxxxx，格式不對丟出 RetailError。"""
    s = re.sub(r"[\s\-().]", "", str(raw or ""))
    if s.startswith("+886"):
        s = "0" + s[4:].lstrip("0")
    elif s.startswith("886") and len(s) == 12:
        s = "0" + s[3:]
    if not re.fullmatch(r"09\d{8}", s):
        raise RetailError(f"手機號碼格式不正確：{raw or '空白'}（例：0912345678）")
    return s


# ---------- 購物車 ----------

def merge_cart(lines):
    """同一個料號、同一個單價的列合併數量；檢查數量是正整數。回傳 [{item, qty, rate}]。"""
    out, errors = {}, []
    for i, ln in enumerate(lines or [], start=1):
        item = str(ln.get("item") or "").strip().upper()
        try:
            qty = float(ln.get("qty"))
        except (TypeError, ValueError):
            qty = 0
        if not item:
            errors.append(f"第 {i} 行沒有料號")
            continue
        if qty <= 0 or qty != int(qty):
            errors.append(f"{item}：數量必須是正整數")
            continue
        rate = ln.get("rate")
        rate = None if rate in (None, "") else float(rate)
        if rate is not None and rate < 0:
            errors.append(f"{item}：單價不可小於 0")
            continue
        key = (item, rate)
        if key in out:
            out[key]["qty"] += int(qty)
        else:
            out[key] = {"item": item, "qty": int(qty), "rate": rate}
    if errors:
        raise RetailError("；".join(errors))
    if not out:
        raise RetailError("沒有商品")
    return list(out.values())


# ---------- 退貨、退款 ----------

GOODS, REFUND_ONLY = "goods", "refund"


def plan_return(sold, mode, requests):
    """檢查退貨或退款，回傳每一行要建立的退貨明細 [{row, item, qty, rate, amount}]。

    sold：{原銷售明細代碼: {"item", "qty"（原數量）, "rate"（原單價）, "returned"（已退數量）}}
    mode：goods＝退貨（商品退回門市庫存，可只退部分金額）；refund＝只退款（商品不退回，視同處理掉 1 件）
    requests：[{"row", "qty", "amount"（退款金額，空白＝全額）}]
    部分退款只扣退款金額（Q9）：退款金額不可超過該行可退的金額。
    """
    if mode not in (GOODS, REFUND_ONLY):
        raise RetailError("退貨方式不正確")
    out, errors = [], []
    for r in requests or []:
        row = sold.get(r.get("row"))
        if not row:
            errors.append("找不到原銷售明細")
            continue
        left = int(row["qty"]) - int(row.get("returned") or 0)
        qty = 1 if mode == REFUND_ONLY else int(float(r.get("qty") or 0))
        if qty <= 0:
            continue
        if qty > left:
            errors.append(f"{row['item']}：最多只能再退 {left} 件")
            continue
        full = round(qty * float(row["rate"]), 2)
        amount = full if r.get("amount") in (None, "") else round(float(r["amount"]), 2)
        if amount < 0 or amount > full:
            errors.append(f"{row['item']}：退款金額必須在 0 到 {full:g} 之間")
            continue
        out.append({"row": r["row"], "item": row["item"], "qty": qty, "rate": round(amount / qty, 4), "amount": amount})
    if errors:
        raise RetailError("；".join(errors))
    if not out:
        raise RetailError("沒有要退的項目")
    return out
