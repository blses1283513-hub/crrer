"""庫存表（P2）：每款一個區塊，列＝各公司＋全公司合計（＋建議補貨），欄＝甲型 × 尺寸＋小計。

一次查出全部規格與庫存，再依篩選條件整理；畫面分頁顯示，匯出 Excel 則包含全部符合條件的款式。
"""

import frappe
from frappe import _

from nila_app import perms, stock
from nila_app.stockrules import NEGATIVE, OUT, LOW, cell_state, num, replenish_qty, total_state

MODES = {"actual": "actual_qty", "projected": "projected_qty"}


def _clean_filters(filters):
    f = frappe.parse_json(filters or {}) or {}
    return {
        "q": (f.get("q") or "").strip().lower(),
        "shape": f.get("shape") or None,
        "size": f.get("size") or None,
        "warehouse": f.get("warehouse") or None,
        "status": f.get("status") or None,
        "state": f.get("state") or None,
        "only_need": bool(frappe.utils.cint(f.get("only_need"))),
        "mode": f.get("mode") if f.get("mode") in MODES else "actual",
    }


def build(filters):
    """回傳 (符合條件的款式區塊清單, 倉庫清單)。"""
    f = _clean_filters(filters)
    field = MODES[f["mode"]]
    whs = stock.warehouses()
    # 門市層級只看自己的門市，也不顯示全公司合計與建議補貨（會透露其他門市的數字）
    own = {w["name"] for w in perms.allowed_stores()} if perms.scoped() else None
    if own is not None:
        whs = [w for w in whs if w["name"] in own]
    shapes, sizes = list(stock.shapes()), stock.sizes()
    styles = {s.name: s for s in frappe.get_all("Item", filters={"has_variants": 1, "disabled": 0},
                                                 fields=["name", "item_name", "nila_status"], order_by="name")}
    variants = {}
    for v in frappe.get_all("Item", filters={"variant_of": ["in", list(styles) or [""]], "disabled": 0},
                            fields=["name", "variant_of", "nila_shape", "nila_size", "nila_reorder_target", "nila_status"]):
        variants.setdefault(v.variant_of, []).append(v)
    bins = stock.bins()

    out = []
    for code, s in styles.items():
        if f["q"] and f["q"] not in code.lower() and f["q"] not in (s.item_name or "").lower():
            continue
        if f["status"] and s.nila_status != f["status"]:
            continue
        vs = [v for v in variants.get(code, [])
              if (not f["shape"] or v.nila_shape == f["shape"]) and (not f["size"] or v.nila_size == f["size"])]
        if not vs:
            continue
        block = _block(s, vs, whs, shapes, sizes, bins, field, f["warehouse"], own is None)
        if f["only_need"] and not block["need"]:
            continue
        if f["state"] and f["state"] not in block["states"]:
            continue
        out.append(block)
    return out, whs


def _block(s, vs, whs, shapes, sizes, bins, field, only_wh, company_rows=True):
    by_cell = {(v.nila_shape, v.nila_size): v for v in vs}
    cols = [{"shape": sh, "sizes": [{"size": sz, "item": by_cell[(sh, sz)].name if (sh, sz) in by_cell else None}
                                    for sz in sizes]}
            for sh in shapes if any((sh, sz) in by_cell for sz in sizes)]
    rows, totals, projected = [], {}, {}
    for w in whs:
        cells = {}
        for v in vs:
            b = bins.get(v.name, {}).get(w["name"], {})
            q = num(b.get(field))
            # 各公司只標負庫存；分公司大多是 0，全部標成缺貨會看不出真正的問題（缺貨、低庫存看合計列）
            cells[v.name] = {"q": q, "s": NEGATIVE if q < 0 else None}
            totals[v.name] = totals.get(v.name, 0) + q
            projected[v.name] = projected.get(v.name, 0) + num(b.get("projected_qty"))
        if w["transit"] and not any(c["q"] for c in cells.values()):
            continue  # 這款沒有在途的貨就不顯示在途列
        if only_wh and w["name"] != only_wh:
            continue
        rows.append({"label": w["label"], "warehouse": w["name"], "kind": "wh", "cells": cells,
                     "sum": sum(c["q"] for c in cells.values())})
    total_cells = {v.name: {"q": totals[v.name], "s": total_state(totals[v.name], v.nila_reorder_target)} for v in vs}
    total_sum = sum(totals.values())
    if not company_rows:
        states = {c["s"] for r in rows for c in r["cells"].values()}
        return {"code": s.name, "name": s.item_name, "status": s.nila_status, "columns": cols, "rows": rows,
                "need": 0, "states": sorted(states & {NEGATIVE})}
    rows.append({"label": _("全公司合計"), "warehouse": "", "kind": "total", "cells": total_cells, "sum": total_sum,
                 "sum_state": cell_state(total_sum) if total_sum <= 0 else None})
    need = {v.name: replenish_qty(v.nila_reorder_target, projected[v.name], v.nila_status) for v in vs}
    if any(need.values()):
        rows.append({"label": _("建議補貨"), "warehouse": "", "kind": "suggest",
                     "cells": {k: {"q": q or "", "s": None} for k, q in need.items()}, "sum": sum(need.values())})
    states = {c["s"] for c in total_cells.values()} | {c["s"] for r in rows if r["kind"] == "wh" for c in r["cells"].values()}
    return {"code": s.name, "name": s.item_name, "status": s.nila_status, "columns": cols, "rows": rows,
            "need": sum(need.values()), "states": sorted(states & {NEGATIVE, OUT, LOW})}


@frappe.whitelist()
def get_matrix(filters=None, start=0, page_length=20):
    perms.require("stock_view")
    blocks, whs = build(filters)
    start, page_length = frappe.utils.cint(start), frappe.utils.cint(page_length) or 20
    return {"styles": blocks[start:start + page_length], "total": len(blocks),
            "summary": {"need_styles": sum(1 for b in blocks if b["need"]), "need_qty": sum(b["need"] for b in blocks),
                        "negative": sum(1 for b in blocks if NEGATIVE in b["states"])}}


@frappe.whitelist()
def get_options():
    perms.require("stock_view")
    whs = stock.warehouses() if not perms.scoped() else perms.allowed_stores()
    return {"shapes": list(stock.shapes()), "sizes": stock.sizes(),
            "warehouses": [{"value": w["name"], "label": w["label"]} for w in whs],
            "caps": perms.caps("replenish_view", "cost_view"), "scoped": perms.scoped()}


@frappe.whitelist()
def export_matrix(filters=None):
    """匯出 Excel：每款每列（各公司、合計、建議補貨），欄＝全部甲型 × 尺寸。"""
    perms.require("stock_view")
    blocks, _whs = build(filters)
    shapes, sizes = list(stock.shapes()), stock.sizes()
    head = [_("款式編號"), _("款式名稱"), _("商品狀態"), _("公司")] + [f"{sh} {sz}" for sh in shapes for sz in sizes] + [_("小計")]
    rows = [head]
    for b in blocks:
        items = {(c["shape"], z["size"]): z["item"] for c in b["columns"] for z in c["sizes"]}
        for r in b["rows"]:
            cells = []
            for sh in shapes:
                for sz in sizes:
                    item = items.get((sh, sz))
                    cells.append(r["cells"][item]["q"] if item and item in r["cells"] else "")
            rows.append([b["code"], b["name"], b["status"], r["label"], *cells, r["sum"]])
    from frappe.utils.xlsxutils import build_xlsx_response

    build_xlsx_response(rows, f"nila-stock-{frappe.utils.nowdate()}")
