"""網站設定檔（nila-config.json）的讀取與檢查。純邏輯，不需要 ERPNext，可單獨測試。

設定檔放在 bench 的 sites 資料夾（sites/nila-config.json），由安裝腳本產生，格式：
{
  "company_name": "妮菈穿戴甲",
  "company_abbr": "NL",
  "hq": "總公司",
  "branches": ["分公司A", "分公司B"],
  "shapes": [{"name": "長梯", "abbr": "LT"}],
  "sizes": ["XS", "S", "M", "L"]
}
"""

import csv
import json
import os

DEFAULT_SIZES = ["XS", "S", "M", "L"]
TRANSIT = "在途"
CONFIG_FILENAME = "nila-config.json"


class ConfigError(ValueError):
    pass


def _is_code(text, lo, hi):
    return isinstance(text, str) and text.isascii() and text.isalpha() and text.isupper() and lo <= len(text) <= hi


def validate_config(cfg):
    """檢查設定，回傳整理後的設定；有任何錯誤就丟出 ConfigError（列出所有問題）。"""
    if not isinstance(cfg, dict):
        raise ConfigError("設定檔必須是 JSON 物件")
    errors = []
    name = str(cfg.get("company_name") or "").strip()
    abbr = str(cfg.get("company_abbr") or "").strip()
    hq = str(cfg.get("hq") or "總公司").strip()
    if not name:
        errors.append("company_name（公司名稱）必填")
    if not _is_code(abbr, 2, 5):
        errors.append("company_abbr（公司縮寫）必須是 2–5 個大寫英文字母")
    branches = [str(b).strip() for b in (cfg.get("branches") or [])]
    names = [hq] + branches + [TRANSIT]
    if any(not b for b in branches):
        errors.append("branches（分公司）名稱不可空白")
    if len(set(names)) != len(names):
        errors.append(f"總公司、分公司與「{TRANSIT}」的名稱不可重複")
    if any(len(n) > 60 for n in names):
        errors.append("倉庫名稱不可超過 60 個字")
    shapes = cfg.get("shapes") or []
    if not shapes:
        errors.append("shapes（甲型）至少要有一種")
    seen_names, seen_abbr, clean_shapes = set(), set(), []
    for i, s in enumerate(shapes, start=1):
        sn = str((s or {}).get("name") or "").strip()
        sa = str((s or {}).get("abbr") or "").strip()
        if not sn or not _is_code(sa, 2, 3):
            errors.append(f"第 {i} 個甲型：名稱必填，縮寫必須是 2–3 個大寫英文字母（目前：{sn or '空白'} / {sa or '空白'}）")
            continue
        if sn in seen_names or sa in seen_abbr:
            errors.append(f"甲型「{sn}」或縮寫「{sa}」重複")
        seen_names.add(sn)
        seen_abbr.add(sa)
        clean_shapes.append({"name": sn, "abbr": sa})
    sizes = [str(x).strip() for x in (cfg.get("sizes") or DEFAULT_SIZES)]
    if not sizes or any(not _is_code(x, 1, 3) for x in sizes) or len(set(sizes)) != len(sizes):
        errors.append("sizes（尺寸）必須是不重複的大寫英文縮寫，例如 XS、S、M、L")
    if errors:
        raise ConfigError("；".join(errors))
    return {"company_name": name, "company_abbr": abbr, "hq": hq, "branches": branches,
            "shapes": clean_shapes, "sizes": sizes}


def load_config(sites_path):
    path = os.path.join(sites_path, CONFIG_FILENAME)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8-sig") as f:
        try:
            data = json.load(f)
        except ValueError as e:
            raise ConfigError(f"{CONFIG_FILENAME} 不是正確的 JSON：{e}")
    return validate_config(data)


def check_shape_changes(existing, wanted):
    """甲型縮寫是料號的一部分：已存在的甲型不可改縮寫。回傳要新增的甲型；有衝突就丟出 ConfigError。"""
    conflicts, new = [], []
    by_abbr = {a: n for n, a in existing.items()}
    for s in wanted:
        if s["name"] in existing:
            if existing[s["name"]] != s["abbr"]:
                conflicts.append(f"甲型「{s['name']}」已使用縮寫 {existing[s['name']]}，不可改成 {s['abbr']}（料號會改變）")
        elif s["abbr"] in by_abbr:
            conflicts.append(f"縮寫 {s['abbr']} 已被甲型「{by_abbr[s['abbr']]}」使用")
        else:
            new.append(s)
    if conflicts:
        raise ConfigError("；".join(conflicts))
    return new


def read_terms(path):
    """用語修正（英文原文 → 繁體中文）。"""
    terms = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            src, dst = (row.get("英文原文") or "").strip(), (row.get("繁體中文") or "").strip()
            if src and dst:
                terms.append((src, dst))
    return terms
