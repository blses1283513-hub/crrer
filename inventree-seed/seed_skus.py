#!/usr/bin/env python3
"""依「公司 × 產品 × 樣式 × 尺寸」在 InvenTree 建立主資料（預設 3×10×5×3 = 450 SKU）。

建立順序（有相依性）：
  1. 庫位樹：公司（頂層，擁有者＝公司群組）→ 主倉
  2. 零件分類：公司
  3. 參數模板：Style、Size（含 choices）
  4. 產品模板（is_template）
  5. 變體（variant_of → 產品模板）
  6. 每個變體寫入 Style、Size 參數

可重複執行：以名稱／IPN 查詢，已存在就沿用，不重複建立。

用法：
  python3 seed_skus.py --config config.json --dry-run          # 只產出計畫 CSV，不連線
  INVENTREE_URL=http://host:8000 INVENTREE_TOKEN=xxx \
  python3 seed_skus.py --config config.json                    # 實際寫入

只依賴 Python 標準函式庫。
"""

import argparse
import csv
import fnmatch
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# InvenTree 1.2 起參數改為通用模型，端點從 /api/part/parameter/... 移到 /api/parameter/...
# 若你的版本不同，請在站台的 /api/ 頁面或對端點送 OPTIONS 確認後修改這裡。
ENDPOINTS = {
    "location": "/api/stock/location/",
    "category": "/api/part/category/",
    "part": "/api/part/",
    "param_template": "/api/parameter/template/",
    "parameter": "/api/parameter/",
    "owner": "/api/user/owner/",
}
PARAM_MODEL_TYPE = "part"


# ---------- 計畫產生（不需連線） ----------

def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    for key in ("companies", "products_per_company", "styles", "sizes"):
        if key not in cfg:
            sys.exit(f"config 缺少欄位：{key}")
    return cfg


def product_code(i):
    return f"P{i:02d}"


def load_removed(path):
    """讀取 manage_parts.py 記錄的已刪除料號（可含 * 萬用字元）。檔案不存在就是沒有。"""
    try:
        with open(path, encoding="utf-8-sig") as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as e:
        sys.exit(f"無法讀取已刪除零件清單 {path}：{e}")
    return [r["ipn"] for r in data.get("removed", []) if r.get("ipn")]


def is_removed(ipn, removed):
    return any(fnmatch.fnmatchcase(ipn, pat) for pat in removed)


def build_plan(cfg, removed=()):
    """回傳 (templates, variants)。templates 每個產品一筆，variants 每個 SKU 一筆。
    removed：已被刪除的料號（可含萬用字元），不會再被建立；產品底下的變體全被排除時，產品範本也一併略過。"""
    names = cfg.get("product_names", {})
    templates, variants = [], []
    for co in cfg["companies"]:
        for i in range(1, cfg["products_per_company"] + 1):
            pcode = product_code(i)
            tpl_ipn = f"{co['code']}-{pcode}"
            pname = names.get(tpl_ipn, f"{co['code']} 產品{pcode}")
            templates.append({"company": co["code"], "ipn": tpl_ipn, "name": pname})
            for st in cfg["styles"]:
                for size in cfg["sizes"]:
                    variants.append({
                        "company": co["code"],
                        "template_ipn": tpl_ipn,
                        "ipn": f"{tpl_ipn}-{st['code']}-{size}",
                        "name": f"{pname} / {st['name']} / {size}",
                        "style": st["code"],
                        "size": size,
                        "minimum_stock": cfg.get("default_minimum_stock", 0),
                    })
    if removed:
        variants = [v for v in variants if not is_removed(v["ipn"], removed) and not is_removed(v["template_ipn"], removed)]
        alive = {v["template_ipn"] for v in variants}
        templates = [t for t in templates if t["ipn"] in alive]
    ipns = [v["ipn"] for v in variants] + [t["ipn"] for t in templates]
    dup = {x for x in ipns if ipns.count(x) > 1}
    if dup:
        sys.exit(f"料號重複，請檢查代碼設定：{sorted(dup)[:5]}")
    return templates, variants


def write_plan_csv(variants, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(variants[0].keys()))
        w.writeheader()
        w.writerows(variants)


# ---------- API 用戶端 ----------

class Api:
    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _req(self, method, path, params=None, body=None):
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            sys.exit(f"API 錯誤 {e.code} {method} {path}：{detail}")

    def list(self, key, **params):
        res = self._req("GET", ENDPOINTS[key], params=params)
        # 有分頁時回傳 {"results": [...]}，無分頁時直接是 list
        return res["results"] if isinstance(res, dict) else res

    def create(self, key, body):
        return self._req("POST", ENDPOINTS[key], body=body)

    def patch(self, key, pk, body):
        return self._req("PATCH", f"{ENDPOINTS[key]}{pk}/", body=body)


def find_one(items, **match):
    for it in items:
        if all(str(it.get(k)) == str(v) for k, v in match.items()):
            return it
    return None


def get_or_create(api, key, lookup, body, search_params):
    """先查詢（伺服器端篩選後再於本地精確比對），找不到才建立。回傳 (物件, 是否新建)。"""
    found = find_one(api.list(key, **search_params), **lookup)
    if found:
        return found, False
    return api.create(key, body), True


# ---------- 實際寫入 ----------

def seed(api, cfg, templates, variants):
    stats = {"created": 0, "existing": 0}

    def tally(created):
        stats["created" if created else "existing"] += 1

    # 擁有者：群組需事先在管理後台建立。先全部檢查完，任何一個缺少就在寫入前停止。
    owners = api.list("owner")
    owner_of = {}
    missing = []
    for co in cfg["companies"]:
        owner = find_one(owners, name=co["owner_group"], label="group") or \
            find_one(owners, name=co["owner_group"])
        if owner:
            owner_of[co["code"]] = owner
        else:
            missing.append(co["owner_group"])
    if missing:
        sys.exit(f"找不到擁有者群組：{'、'.join(missing)}。請先在管理後台建立群組，未寫入任何資料。")

    company_loc, company_cat = {}, {}
    for co in cfg["companies"]:
        owner = owner_of[co["code"]]

        top, c = get_or_create(
            api, "location",
            {"name": co["name"], "parent": None},
            {"name": co["name"], "description": f"{co['name']} 頂層庫位", "owner": owner["pk"]},
            {"name": co["name"]},
        )
        tally(c)
        if top.get("owner") != owner["pk"]:
            api.patch("location", top["pk"], {"owner": owner["pk"]})

        wh, c = get_or_create(
            api, "location",
            {"name": cfg.get("warehouse_name", "主倉"), "parent": top["pk"]},
            {"name": cfg.get("warehouse_name", "主倉"), "parent": top["pk"]},
            {"parent": top["pk"]},
        )
        tally(c)
        company_loc[co["code"]] = wh["pk"]

        cat, c = get_or_create(
            api, "category",
            {"name": co["name"], "parent": None},
            {"name": co["name"], "description": f"{co['name']} 產品"},
            {"name": co["name"]},
        )
        tally(c)
        company_cat[co["code"]] = cat["pk"]

    # 參數模板
    style_tpl, c = get_or_create(
        api, "param_template", {"name": "Style"},
        {"name": "Style", "model_type": PARAM_MODEL_TYPE,
         "choices": ",".join(s["code"] for s in cfg["styles"])},
        {"search": "Style"},
    )
    tally(c)
    size_tpl, c = get_or_create(
        api, "param_template", {"name": "Size"},
        {"name": "Size", "model_type": PARAM_MODEL_TYPE, "choices": ",".join(cfg["sizes"])},
        {"search": "Size"},
    )
    tally(c)

    # 產品模板
    tpl_pk = {}
    for t in templates:
        part, c = get_or_create(
            api, "part", {"IPN": t["ipn"]},
            {"name": t["name"], "IPN": t["ipn"], "category": company_cat[t["company"]],
             "is_template": True, "salable": True, "purchaseable": True,
             "default_location": company_loc[t["company"]]},
            {"search": t["ipn"]},
        )
        tally(c)
        tpl_pk[t["ipn"]] = part["pk"]

    # 變體 + 參數
    for n, v in enumerate(variants, 1):
        part, c = get_or_create(
            api, "part", {"IPN": v["ipn"]},
            {"name": v["name"], "IPN": v["ipn"], "category": company_cat[v["company"]],
             "variant_of": tpl_pk[v["template_ipn"]], "salable": True, "purchaseable": True,
             "minimum_stock": v["minimum_stock"],
             "default_location": company_loc[v["company"]]},
            {"search": v["ipn"]},
        )
        tally(c)
        existing = api.list("parameter", model_type=PARAM_MODEL_TYPE, model_id=part["pk"])
        for tpl, value in ((style_tpl, v["style"]), (size_tpl, v["size"])):
            if not find_one(existing, template=tpl["pk"]):
                api.create("parameter", {"template": tpl["pk"], "data": value,
                                         "model_type": PARAM_MODEL_TYPE, "model_id": part["pk"]})
                stats["created"] += 1
        if n % 50 == 0:
            print(f"  變體進度 {n}/{len(variants)}")

    return stats


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--dry-run", action="store_true", help="只輸出計畫 CSV，不連線")
    ap.add_argument("--plan-csv", default="sku_plan.csv")
    ap.add_argument("--removed", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "removed_parts.json"),
                    help="已刪除零件清單（manage_parts.py delete 會自動記錄），清單中的料號不會再被建立")
    args = ap.parse_args()

    cfg = load_config(args.config)
    removed = load_removed(args.removed)
    full_templates, full_variants = build_plan(cfg)
    templates, variants = build_plan(cfg, removed)
    write_plan_csv(variants, args.plan_csv)
    print(f"計畫：{len(cfg['companies'])} 公司，{len(templates)} 產品模板，"
          f"{len(variants)} 個 SKU → 已輸出 {args.plan_csv}")
    if removed:
        print(f"已略過 {len(full_variants) - len(variants)} 個 SKU、{len(full_templates) - len(templates)} 個產品"
              f"（依 {args.removed} 的已刪除清單）")

    if args.dry_run:
        return

    url, token = os.environ.get("INVENTREE_URL"), os.environ.get("INVENTREE_TOKEN")
    if not url or not token:
        sys.exit("請設定環境變數 INVENTREE_URL 與 INVENTREE_TOKEN（或加 --dry-run）。")
    stats = seed(Api(url, token), cfg, templates, variants)
    print(f"完成：新建 {stats['created']} 筆，沿用既有 {stats['existing']} 筆。")


if __name__ == "__main__":
    main()
