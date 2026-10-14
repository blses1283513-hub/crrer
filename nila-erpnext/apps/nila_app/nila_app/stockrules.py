"""庫存規則：庫存狀態、全公司合計、補貨建議、訂單分配與調撥建議。純邏輯，不需要 ERPNext，可單獨測試。

庫存表（P2）、補貨（P3）、訂單調度（P4）都用這裡的規則，同一個規格在三個畫面上的數字一定一致。

名詞：
- 實際庫存：倉庫裡現在有的數量（可以是負數，例如門市賣超過帳上數量）。
- 預計庫存：實際 ＋ 已叫貨未入庫 ＋ 補貨單未叫貨 − 訂單已預留（ERPNext 的 projected_qty）。
- 全公司合計：總公司、各分公司與在途倉加總。
"""

import math

from nila_app.catalog import NO_REPLENISH_STATUSES

NEGATIVE, OUT, LOW, OK = "負庫存", "缺貨", "低庫存", "正常"
STATES = [NEGATIVE, OUT, LOW, OK]

# 訂單的出貨狀態
READY, NEED_TRANSFER, ORDERED, NEED_PURCHASE, DELIVERED = "可出貨", "待調撥", "已叫貨", "待叫貨", "已出貨"
DISPATCH_STATUSES = [READY, NEED_TRANSFER, ORDERED, NEED_PURCHASE, DELIVERED]


def num(x):
    """資料庫的數量是小數（例如 3.0），顯示與比較時轉成整數；真的有小數就保留。"""
    x = float(x or 0)
    return int(x) if x == int(x) else x


def cell_state(qty):
    """單一倉庫的格子：負庫存、缺貨、正常（各公司不設低庫存門檻）。"""
    qty = num(qty)
    if qty < 0:
        return NEGATIVE
    if qty == 0:
        return OUT
    return OK


def total_state(qty, target):
    """全公司合計：再加上「低於補貨目標＝低庫存」。"""
    state = cell_state(qty)
    if state == OK and target and num(qty) < target:
        return LOW
    return state


def replenish_qty(target, projected_total, status):
    """建議補貨數＝補貨目標 − 全公司預計庫存；停產、沒設目標的不補。

    例：總公司 2＋分公司 1 − 訂單 5 ＝ −2，目標 10 → 補 12。
    """
    if status in NO_REPLENISH_STATUSES or not target or target <= 0:
        return 0
    return max(0, math.ceil(target - float(projected_total or 0)))


def allocate(lines, actual, transit=None, incoming=None, sources=()):
    """依先後順序把庫存分配給訂單明細，算出每一行怎麼出貨，以及需要哪些調撥。

    lines：未出貨的訂單明細，已依先後排序，每行 {"key", "order", "item", "warehouse", "qty"}（qty＝還沒出貨的數量）。
    actual：{(料號, 倉庫): 實際庫存}。
    transit：{(料號, 目的倉庫): 在途、還沒入庫的數量}。
    incoming：{(料號, 倉庫): 已叫貨（採購單）還沒到貨的數量}。
    sources：可以調出貨的倉庫（總公司與分公司，不含在途倉）。

    每一行依序用：出貨倉現有庫存 → 寄往出貨倉的在途 → 其他倉庫剩餘的庫存（調撥，從剩最多的倉庫調）
    → 已叫貨未到貨 → 還缺的就要叫貨。
    回傳 (results, transfers)：
      results {key: {"stock", "transit", "transfer", "ordered", "short", "sources": [(倉庫, 數量)]}}
      transfers [{"item", "from", "to", "qty", "order"}]
    """
    free = {k: max(0, num(v)) for k, v in actual.items()}
    on_way = {k: max(0, num(v)) for k, v in (transit or {}).items()}
    bought = {k: max(0, num(v)) for k, v in (incoming or {}).items()}
    order = {w: i for i, w in enumerate(sources)}
    results, pending = {}, []

    def take(pool, key, need):
        got = min(need, pool.get(key, 0))
        if got > 0:
            pool[key] -= got
        return max(0, got)

    # 第一輪：每一行先用自己出貨倉的庫存與在途，先來先用
    for ln in lines:
        key = (ln["item"], ln["warehouse"])
        need = num(ln["qty"])
        r = {"stock": 0, "transit": 0, "transfer": 0, "ordered": 0, "short": 0, "sources": []}
        r["stock"] = take(free, key, need)
        need -= r["stock"]
        r["transit"] = take(on_way, key, need)
        need -= r["transit"]
        results[ln["key"]] = r
        if need > 0:
            pending.append((ln, need))

    # 第二輪：還缺的，從其他倉庫剩下的庫存調撥；再不夠看已叫貨；最後才是要叫貨
    transfers = []
    for ln, need in pending:
        r = results[ln["key"]]
        item, to = ln["item"], ln["warehouse"]
        for src in sorted((w for w in sources if w != to), key=lambda w: (-free.get((item, w), 0), order[w])):
            if need <= 0:
                break
            got = take(free, (item, src), need)
            if got:
                need -= got
                r["transfer"] += got
                r["sources"].append((src, got))
                transfers.append({"item": item, "from": src, "to": to, "qty": got, "order": ln["order"]})
        for wh in [to, *(w for w in sorted({k[1] for k in bought if k[0] == item}) if w != to)]:
            if need <= 0:
                break
            got = take(bought, (item, wh), need)
            r["ordered"] += got
            need -= got
        r["short"] = need
    return results, transfers


def order_status(line_results, fully_delivered=False):
    """訂單的出貨狀態：全部有現貨＝可出貨；有缺而且要叫貨＝待叫貨；已叫貨在路上＝已叫貨；其餘靠調撥或在途＝待調撥。"""
    if fully_delivered:
        return DELIVERED
    rs = list(line_results)
    if any(r["short"] > 0 for r in rs):
        return NEED_PURCHASE
    if any(r["ordered"] > 0 for r in rs):
        return ORDERED
    if any(r["transit"] > 0 or r["transfer"] > 0 for r in rs):
        return NEED_TRANSFER
    return READY


def group_transfers(transfers):
    """把調撥建議依（調出倉、調入倉、料號）合併，列出是為了哪些訂單。"""
    merged = {}
    for t in transfers:
        k = (t["from"], t["to"], t["item"])
        m = merged.setdefault(k, {"from": t["from"], "to": t["to"], "item": t["item"], "qty": 0, "orders": []})
        m["qty"] += t["qty"]
        if t["order"] and t["order"] not in m["orders"]:
            m["orders"].append(t["order"])
    return sorted(merged.values(), key=lambda m: (m["from"], m["to"], m["item"]))
