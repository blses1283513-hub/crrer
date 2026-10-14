"""款式與規格的規則。純邏輯，不需要 ERPNext，可單獨測試。

一個「款式」是 ERPNext 的商品範本（例：0001 櫻花），每個「甲型 × 尺寸」是一個規格（例：0001-LT-XS）。
成本、售價、商品狀態設在款式上，規格一律跟著款式；補貨目標依甲型設定，同甲型的各尺寸相同。
"""

import re

STATUSES = ["上架", "停售", "停產"]
# 不能接新訂單（官網、訂單調度）的狀態；門市仍可賣（出清庫存）
NO_ORDER_STATUSES = {"停售", "停產"}
# 不再補貨的狀態
NO_REPLENISH_STATUSES = {"停產"}

CODE_RE = re.compile(r"^[A-Za-z0-9]{1,20}$")
AUTO_CODE_DIGITS = 4


class CatalogError(ValueError):
    pass


def next_style_code(existing_codes):
    """下一個自動款式編號：現有純數字編號的最大值 + 1，補零到 4 位（0001、0002…；超過 9999 就是 10000）。"""
    numbers = [int(c) for c in existing_codes if isinstance(c, str) and c.isdigit()]
    return str(max(numbers, default=0) + 1).zfill(AUTO_CODE_DIGITS)


def variant_name(style_name, shape, size):
    return f"{style_name}-{shape}-{size}"


def _number(value, label, errors, required=True):
    if value in (None, ""):
        if required:
            errors.append(f"{label}必填")
        return None
    try:
        n = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label}必須是數字（目前：{value}）")
        return None
    if n < 0:
        errors.append(f"{label}不可小於 0")
        return None
    return n


def _target(value, label, errors):
    if value in (None, ""):
        return 0
    try:
        n = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label}必須是整數（目前：{value}）")
        return 0
    if n < 0 or n != int(n):
        errors.append(f"{label}必須是 0 以上的整數（目前：{value}）")
        return 0
    return int(n)


def clean_style(data, shapes, sizes, need_cells=True):
    """檢查「新增款式」的輸入，回傳整理後的資料；有錯就丟出 CatalogError（列出所有問題）。

    data: {code?, name, cost, web_price, store_price, status?, cells: [{shape, size}], targets: {甲型: 數量}}
    shapes、sizes: 系統中現有的甲型名稱與尺寸（依顯示順序）
    """
    errors = []
    code = str(data.get("code") or "").strip()
    if code and not CODE_RE.match(code):
        errors.append(f"款式編號只能是 1–20 個英文字母或數字（目前：{code}）")
    name = str(data.get("name") or "").strip()
    if not name:
        errors.append("款式名稱必填")
    elif len(name) > 100:
        errors.append("款式名稱不可超過 100 個字")
    cost = _number(data.get("cost"), "成本", errors)
    web = _number(data.get("web_price"), "官網售價", errors)
    store = _number(data.get("store_price"), "實體售價", errors)
    status = str(data.get("status") or "上架").strip()
    if status not in STATUSES:
        errors.append(f"商品狀態必須是 {'、'.join(STATUSES)} 其中之一（目前：{status}）")

    cells, seen = [], set()
    for c in data.get("cells") or []:
        shape, size = str(c.get("shape") or "").strip(), str(c.get("size") or "").strip()
        if shape not in shapes:
            errors.append(f"沒有這個甲型：{shape or '空白'}")
            continue
        if size not in sizes:
            errors.append(f"沒有這個尺寸：{size or '空白'}")
            continue
        if (shape, size) in seen:
            continue
        seen.add((shape, size))
        cells.append((shape, size))
    if need_cells and not cells:
        errors.append("至少要勾選一個甲型 × 尺寸")
    # 依系統中甲型、尺寸的順序排列，料號才會整齊
    cells.sort(key=lambda c: (shapes.index(c[0]), sizes.index(c[1])))

    targets = {}
    raw_targets = data.get("targets") or {}
    for shape in {s for s, _ in cells}:
        targets[shape] = _target(raw_targets.get(shape), f"「{shape}」的補貨目標", errors)

    if errors:
        raise CatalogError("；".join(errors))
    return {"code": code, "name": name, "cost": cost, "web_price": web, "store_price": store,
            "status": status, "cells": cells, "targets": targets}
