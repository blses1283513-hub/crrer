"""抽獎資格規則。純邏輯，不需要 ERPNext，可單獨測試。

- 條件可以任意組合（全部都要符合）：累計消費金額、消費次數、單筆最高金額、買過指定款式、買過指定甲型。
- 名額：每人 1 個、每滿 X 元 1 個（可設上限）、每 N 次消費 1 個（可設上限）。
- 消費＝門市銷售扣掉退貨、退款（和消費報表同一個計算）；官網訂單不算。系統只判斷資格，不抽籤。
"""

import math

RULE_TYPES = {
    "累計消費金額": "net",      # 期間內淨額（扣退款）至少多少元
    "消費次數": "orders",       # 期間內消費至少幾次（不含退貨單）
    "單筆最高金額": "max_single",  # 期間內至少有一筆消費達到多少元
    "買過指定款式": "styles",   # 值＝款式編號（多個用逗號分隔，買過其中一個即可）
    "買過指定甲型": "shapes",   # 值＝甲型名稱（多個用逗號分隔）
}
NUMERIC = {"net", "orders", "max_single"}
PER_PERSON, PER_AMOUNT, PER_ORDERS = "每人 1 個名額", "每滿 X 元 1 個名額", "每 N 次消費 1 個名額"
MODES = [PER_PERSON, PER_AMOUNT, PER_ORDERS]


class LotteryError(ValueError):
    pass


def clean_rules(rules, mode, unit=None, cap=None):
    """檢查並整理規則。回傳 ([(key, 值)], mode, unit, cap)；有錯丟出 LotteryError（列出全部錯誤）。"""
    errors, out = [], []
    for i, r in enumerate(rules or [], start=1):
        kind = (r.get("rule_type") or "").strip()
        raw = str(r.get("value") if r.get("value") is not None else "").strip()
        key = RULE_TYPES.get(kind)
        if not key:
            errors.append(f"第 {i} 條：條件種類不正確（{kind or '空白'}）")
            continue
        if key in NUMERIC:
            try:
                val = float(raw.replace(",", ""))
            except ValueError:
                errors.append(f"第 {i} 條：{kind}要填數字")
                continue
            if val < 0 or (key == "orders" and val != int(val)):
                errors.append(f"第 {i} 條：{kind}必須是 0 以上{'的整數' if key == 'orders' else ''}")
                continue
            out.append((key, val))
        else:
            vals = {v.strip() for v in raw.replace("，", ",").split(",") if v.strip()}
            if not vals:
                errors.append(f"第 {i} 條：{kind}要填{'款式編號' if key == 'styles' else '甲型名稱'}")
                continue
            out.append((key, vals))
    if mode not in MODES:
        errors.append("名額計算方式不正確")
    unit = float(unit or 0)
    cap = int(cap or 0)
    if mode in (PER_AMOUNT, PER_ORDERS) and unit <= 0:
        errors.append("「每滿 X 元」或「每 N 次」要填大於 0 的數字")
    if mode == PER_ORDERS and unit != int(unit):
        errors.append("「每 N 次」要填整數")
    if cap < 0:
        errors.append("名額上限不可小於 0")
    if errors:
        raise LotteryError("；".join(errors))
    return out, mode, unit, cap


def qualifies(stats, rules):
    """stats：{"orders", "net", "max_single", "styles": set, "shapes": set}。全部條件都符合才算。"""
    if stats.get("orders", 0) <= 0:
        return False  # 期間內沒有消費（只有退貨）不算
    for key, val in rules:
        if key in NUMERIC:
            if (stats.get(key) or 0) < val:
                return False
        elif not (set(stats.get(key) or ()) & val):
            return False
    return True


def entries(stats, mode, unit=0, cap=0):
    if mode == PER_PERSON:
        n = 1
    elif mode == PER_AMOUNT:
        n = math.floor(max(0, stats.get("net") or 0) / unit)
    else:
        n = math.floor((stats.get("orders") or 0) / unit)
    return min(n, cap) if cap else n


def evaluate(all_stats, rules, mode, unit=0, cap=0):
    """回傳符合資格的名單 [{"customer", "entries", ...stats}]，依名額、淨額由多到少排序。名額 0 的不列入。"""
    out = []
    for customer, st in all_stats.items():
        if not qualifies(st, rules):
            continue
        n = entries(st, mode, unit, cap)
        if n > 0:
            out.append({"customer": customer, "entries": n, "orders": st.get("orders", 0), "net": st.get("net", 0),
                        "max_single": st.get("max_single", 0)})
    out.sort(key=lambda r: (-r["entries"], -r["net"], r["customer"]))
    return out


def describe(rules, mode, unit=0, cap=0):
    """規則的文字說明（存在名單快照上，日後可以知道當時用什麼條件）。"""
    names = {v: k for k, v in RULE_TYPES.items()}
    parts = []
    for key, val in rules:
        if key in NUMERIC:
            unit_txt = "次" if key == "orders" else "元"
            parts.append(f"{names[key]}至少 {val:g} {unit_txt}")
        else:
            parts.append(f"{names[key]}：{'、'.join(sorted(val))}")
    cond = "；".join(parts) or "期間內有消費"
    if mode == PER_PERSON:
        m = "每人 1 個名額"
    elif mode == PER_AMOUNT:
        m = f"每滿 {unit:g} 元 1 個名額"
    else:
        m = f"每 {unit:g} 次消費 1 個名額"
    if cap and mode != PER_PERSON:
        m += f"（每人最多 {cap} 個）"
    return f"條件：{cond}。名額：{m}。"
