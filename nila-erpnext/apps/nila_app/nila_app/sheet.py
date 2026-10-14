"""商品試算表（SKU 清單）的匯入檢查。純邏輯，不需要 ERPNext，可單獨測試。

一列＝一個規格。欄位以客戶的 SKU 清單為準：
    SKU 編碼｜款式編號｜款式名稱｜甲型｜尺寸｜商品狀態｜成本｜官網售價｜實體售價｜補貨目標｜總公司｜分公司A…
- SKU 編碼由系統產生，匯入時可留空；有填的話會檢查是否與「款式編號-甲型縮寫-尺寸」一致。
- 款式編號留空：同一個款式名稱的列視為同一個新款式，建立時自動編號。
- 款式的名稱、狀態、成本、售價在同款每一列都要一樣。
- 各公司欄位是期初庫存，只用在新的規格；已經存在的規格不會改庫存（請用盤點），會列出提醒。
"""

from nila_app.catalog import CODE_RE, STATUSES

COL_SKU = "SKU 編碼"
COL_CODE = "款式編號"
COL_NAME = "款式名稱"
COL_SHAPE = "甲型"
COL_SIZE = "尺寸"
COL_STATUS = "商品狀態"
COL_COST = "成本"
COL_WEB = "官網售價"
COL_STORE = "實體售價"
COL_TARGET = "補貨目標"
COLUMNS = [COL_SKU, COL_CODE, COL_NAME, COL_SHAPE, COL_SIZE, COL_STATUS, COL_COST, COL_WEB, COL_STORE, COL_TARGET]
REQUIRED = [COL_CODE, COL_NAME, COL_SHAPE, COL_SIZE]
STYLE_VALUES = [(COL_NAME, "name"), (COL_STATUS, "status"), (COL_COST, "cost"), (COL_WEB, "web_price"), (COL_STORE, "store_price")]
MAX_ERRORS = 200


def headers(warehouses):
    return COLUMNS + list(warehouses)


def _text(v):
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _num(v):
    """空白回傳 None；不是 0 以上的數字丟出 ValueError。"""
    t = _text(v).replace(",", "")
    if t == "":
        return None
    n = float(t)
    if n != n or n < 0:  # NaN 或負數
        raise ValueError
    return n


def _int(v):
    n = _num(v)
    if n is not None and not n.is_integer():
        raise ValueError
    return None if n is None else int(n)


def parse_csv(content):
    """讀 CSV（bytes 或文字）。Excel 存的 CSV 可能是 UTF-8（含或不含 BOM）或繁體中文 Windows 的 Big5（cp950）。"""
    import csv
    import io

    if isinstance(content, bytes):
        for enc in ("utf-8-sig", "cp950"):
            try:
                content = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("無法辨識 CSV 的文字編碼，請改存成 Excel（.xlsx）或 UTF-8 的 CSV")
    return [row for row in csv.reader(io.StringIO(content.lstrip("\ufeff")))]


def rows_from_table(table):
    """把試算表（第一列是標題）轉成 [(列號, {欄名: 值})]，略過整列空白。"""
    if not table:
        return [], []
    head = [_text(h).lstrip("\ufeff") for h in table[0]]
    out = []
    for i, raw in enumerate(table[1:], start=2):
        row = {h: (raw[j] if j < len(raw) else None) for j, h in enumerate(head) if h}
        if any(_text(v) for v in row.values()):
            out.append((i, row))
    return head, out


def plan_import(table, shapes, sizes, warehouses, existing):
    """檢查試算表並算出要做的變更。

    shapes: {甲型名稱: 縮寫}；sizes: [XS, S, M, L]；warehouses: [總公司, 分公司A…]（欄名）
    existing: {"styles": {款式編號: {name, status, cost, web_price, store_price,
                                    variants: {(甲型, 尺寸): {code, target}}}},
               "codes": 其他已使用的料號（非款式）}
    回傳 {"errors", "warnings", "styles", "counts"}；有 errors 就不能匯入。
    """
    errors, warnings = [], []

    def err(row, msg):
        if len(errors) < MAX_ERRORS:
            errors.append(f"第 {row} 列：{msg}" if row else msg)

    head, rows = rows_from_table(table)
    missing = [c for c in REQUIRED if c not in head]
    if missing:
        err(0, f"缺少欄位：{'、'.join(missing)}（請用「下載範本」的格式）")
    unknown = [h for h in head if h and h not in COLUMNS and h not in warehouses]
    if unknown:
        warnings.append(f"不認得的欄位不會匯入：{'、'.join(unknown)}")
    stock_cols = [w for w in warehouses if w in head]
    if not rows and not missing:
        err(0, "試算表沒有資料")
    if missing:
        return {"errors": errors, "warnings": warnings, "styles": [], "counts": {}}

    ex_styles = existing.get("styles", {})
    other_codes = set(existing.get("codes", []))
    names_in_use = {}
    for code, s in ex_styles.items():
        names_in_use.setdefault(s["name"], code)

    groups = {}  # key -> {"code", "rows": [(列號, row)]}
    for n, row in rows:
        code = _text(row.get(COL_CODE))
        name = _text(row.get(COL_NAME))
        if code and not CODE_RE.match(code):
            err(n, f"款式編號只能是 1–20 個英文字母或數字（目前：{code}）")
            continue
        if code and code in other_codes:
            err(n, f"{code} 已經是其他商品的料號，不能當款式編號")
            continue
        if not code and not name:
            err(n, "款式編號與款式名稱至少要填一個")
            continue
        key = code or f"\0{name}"
        groups.setdefault(key, {"code": code, "rows": []})["rows"].append((n, row))

    styles = []
    counts = {"new_styles": 0, "updated_styles": 0, "new_variants": 0, "updated_variants": 0,
              "unchanged_variants": 0, "stock_entries": 0, "stock_qty": 0}
    skipped_stock = []
    for key, g in groups.items():
        code = g["code"]
        old = ex_styles.get(code) if code else None
        first_n = g["rows"][0][0]

        # 款式層級的值：同款每一列要一致
        vals = {}
        for col, field in STYLE_VALUES:
            seen = {}
            for n, row in g["rows"]:
                t = _text(row.get(col))
                if t != "":
                    seen.setdefault(t, n)
            if len(seen) > 1:
                err(first_n, f"款式 {code or _text(g['rows'][0][1].get(COL_NAME))} 的{col}在各列不一致（{'、'.join(seen)}）")
                continue
            vals[field] = next(iter(seen), "")
        style = {"code": code, "is_new": old is None, "changed": False, "row": first_n, "variants": []}
        style["name"] = vals.get("name") or (old or {}).get("name", "")
        if not style["name"]:
            err(first_n, "新款式的款式名稱必填")
        status = vals.get("status", "")
        if status and status not in STATUSES:
            err(first_n, f"商品狀態必須是 {'、'.join(STATUSES)} 其中之一（目前：{status}）")
        style["status"] = status or (old or {}).get("status") or "上架"
        for col, field in STYLE_VALUES[2:]:
            try:
                v = _num(vals.get(field))
            except ValueError:
                err(first_n, f"{col}必須是 0 以上的數字（目前：{vals.get(field)}）")
                v = None
            if v is None:
                if old is None:
                    err(first_n, f"新款式的{col}必填")
                v = (old or {}).get(field)
            style[field] = v
        if old is not None:
            style["changed"] = any(_differs(style[f], old.get(f)) for _, f in STYLE_VALUES)
        elif style["name"] in names_in_use:
            warnings.append(f"第 {first_n} 列：款式名稱「{style['name']}」已存在（編號 {names_in_use[style['name']]}），"
                            "沒填款式編號會建立另一個新款式")

        seen_cells = set()
        for n, row in g["rows"]:
            shape = _text(row.get(COL_SHAPE))
            size = _text(row.get(COL_SIZE)).upper()
            if shape not in shapes:
                err(n, f"沒有這個甲型：{shape or '空白'}（可用：{'、'.join(shapes)}）")
                continue
            if size not in sizes:
                err(n, f"沒有這個尺寸：{size or '空白'}（可用：{'、'.join(sizes)}）")
                continue
            if (shape, size) in seen_cells:
                err(n, f"款式 {code or style['name']} 的 {shape} {size} 重複")
                continue
            seen_cells.add((shape, size))
            sku = _text(row.get(COL_SKU))
            if sku and code and sku != f"{code}-{shapes[shape]}-{size}":
                err(n, f"SKU 編碼 {sku} 與款式編號、甲型、尺寸不符（應為 {code}-{shapes[shape]}-{size}）")
                continue
            try:
                target = _int(row.get(COL_TARGET))
            except ValueError:
                err(n, f"補貨目標必須是 0 以上的整數（目前：{_text(row.get(COL_TARGET))}）")
                continue
            stock, bad = {}, False
            for w in stock_cols:
                try:
                    q = _int(row.get(w))
                except ValueError:
                    err(n, f"{w}的庫存必須是 0 以上的整數（目前：{_text(row.get(w))}）")
                    bad = True
                    continue
                if q:
                    stock[w] = q
            if bad:
                continue
            ov = (old or {}).get("variants", {}).get((shape, size))
            v = {"shape": shape, "size": size, "row": n, "is_new": ov is None, "stock": {}}
            if ov is None:
                v["target"] = target or 0
                v["stock"] = stock
                v["changed"] = True
            else:
                v["code"] = ov["code"]
                v["target"] = (ov.get("target") or 0) if target is None else target
                v["changed"] = v["target"] != (ov.get("target") or 0)
                if stock:
                    skipped_stock.append(ov["code"])
            style["variants"].append(v)
        styles.append(style)

    if skipped_stock:
        shown = "、".join(skipped_stock[:10]) + (f" 等 {len(skipped_stock)} 個" if len(skipped_stock) > 10 else "")
        warnings.append(f"已存在的規格不會匯入庫存（請用盤點調整）：{shown}")

    for s in styles:
        if s["is_new"]:
            counts["new_styles"] += 1
        elif s["changed"]:
            counts["updated_styles"] += 1
        for v in s["variants"]:
            if v["is_new"]:
                counts["new_variants"] += 1
                counts["stock_qty"] += sum(v["stock"].values())
                counts["stock_entries"] += len(v["stock"])
            elif v["changed"]:
                counts["updated_variants"] += 1
            else:
                counts["unchanged_variants"] += 1
    if len(errors) >= MAX_ERRORS:
        errors.append(f"錯誤太多，只列出前 {MAX_ERRORS} 個")
    return {"errors": errors, "warnings": warnings, "styles": styles, "counts": counts}


def _differs(a, b):
    if isinstance(a, (int, float)) or isinstance(b, (int, float)):
        try:
            return float(a or 0) != float(b or 0)
        except (TypeError, ValueError):
            return True
    return (a or "") != (b or "")


def export_rows(styles, shapes, sizes, warehouses, stock):
    """匯出：每個規格一列，依款式編號、甲型、尺寸的順序。

    styles: {款式編號: {name, status, cost, web_price, store_price, variants: {(甲型, 尺寸): {code, target}}}}
    stock: {料號: {倉庫欄名: 數量}}
    """
    shape_order = {s: i for i, s in enumerate(shapes)}
    size_order = {s: i for i, s in enumerate(sizes)}
    out = [headers(warehouses)]
    for code in sorted(styles):
        s = styles[code]
        cells = sorted(s["variants"].items(), key=lambda kv: (shape_order.get(kv[0][0], 99), size_order.get(kv[0][1], 99), kv[0]))
        for (shape, size), v in cells:
            q = stock.get(v["code"], {})
            out.append([v["code"], code, s["name"], shape, size, s["status"], s["cost"], s["web_price"], s["store_price"],
                        v.get("target") or 0] + [q.get(w, 0) for w in warehouses])
    return out
