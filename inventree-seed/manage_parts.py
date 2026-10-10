#!/usr/bin/env python3
"""零件整理：查看、停用（可還原）、還原、永久刪除不需要的零件，附多層安全檢查。

為什麼需要這個工具（InvenTree 1.5.6 原始碼的行為）：
  * 啟用中的零件不能刪除，必須先停用。
  * 刪除零件會『連帶永久刪除它所有的庫存項目與全部異動紀錄（時間、操作人）』，無法復原。
  * 刪除範本零件時，底下的變體不會被刪，而是變成沒有範本的獨立零件。
  * 本專案的職務設定沒有任何人有刪除權限，所以只有 superuser 能刪除。
所以建議的做法是：先「停用」（retire）——零件與紀錄都留著、不會再出現在快速調貨與低庫存通知，
隨時可以「還原」；確定真的不需要才「刪除」（delete），且刪除前會自動匯出零件與異動紀錄。

子命令：
  list     查看符合條件的零件（唯讀）
  retire   停用（可還原）
  restore  還原為啟用
  delete   永久刪除（需先停用、庫存為 0、沒有訂單紀錄；會先匯出紀錄、要求輸入確認）

選擇零件（至少要指定一種；不提供「全部」）：
  --ipn A-P03-S5-XL        料號（可重複）
  --glob "A-P03-S5-*"      萬用字元（可重複）
  --file 清單.txt          每行一個料號或萬用字元

用法：
  INVENTREE_URL=http://localhost INVENTREE_TOKEN=xxx python3 manage_parts.py list --glob "A-P03-*"
  ... python3 manage_parts.py retire --glob "A-P03-S5-*"
  ... python3 manage_parts.py delete --glob "A-P03-S5-*"      # 先 retire；delete 會再次確認

只依賴 Python 標準函式庫。
"""

import argparse
import csv
import fnmatch
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REMOVED = os.path.join(HERE, "removed_parts.json")
BACKUP_NOTICE = "刪除前請先備份（在安裝資料夾執行 backup.ps1）。"


# ---------- API ----------

class Api:
    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Token {token}", "Content-Type": "application/json", "Accept": "application/json"}

    def _req(self, method, path, params=None, body=None, tolerate=()):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            if e.code in tolerate:
                return None
            detail = e.read().decode(errors="replace")[:400]
            hint = ""
            if e.code in (401, 403):
                hint = "（請確認 token 屬於 superuser 帳號；一般職務沒有刪除權限）"
            sys.exit(f"API 錯誤 {e.code} {method} {path}{hint}：{detail}")
        except urllib.error.URLError as e:
            sys.exit(f"連不到 {self.base}：{e.reason}。請確認系統已啟動，且 INVENTREE_URL 正確。")

    def list(self, path, **params):
        out, offset = [], 0
        while True:
            res = self._req("GET", path, params={**params, "limit": 200, "offset": offset})
            if isinstance(res, list):
                return res
            out += res.get("results", [])
            if not res.get("next") or not res.get("results"):
                return out
            offset += len(res["results"])

    def count(self, path, **params):
        """回傳符合筆數；端點不存在時回傳 None（無法確認）。"""
        res = self._req("GET", path, params={**params, "limit": 1}, tolerate=(404,))
        if res is None:
            return None
        return len(res) if isinstance(res, list) else res.get("count", len(res.get("results", [])))

    def patch(self, path, body):
        return self._req("PATCH", path, body=body)

    def delete(self, path):
        return self._req("DELETE", path)


# ---------- 選擇零件 ----------

def read_patterns(args):
    pats = list(args.ipn or []) + list(args.glob or [])
    if args.file:
        try:
            with open(args.file, encoding="utf-8-sig") as f:
                pats += [ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
        except OSError as e:
            sys.exit(f"無法讀取清單檔 {args.file}：{e}")
    return pats


def select_parts(api, patterns, status="all", require_pattern=True):
    if require_pattern and not patterns:
        sys.exit("請指定要處理的零件：--ipn、--glob 或 --file（為了安全，不提供「全部」）。")
    params = {}
    if status == "active":
        params["active"] = "true"
    elif status == "inactive":
        params["active"] = "false"
    parts = api.list("/api/part/", **params)
    if status == "all":
        api.all_parts = parts           # 完整清單，供刪除前檢查「範本底下還有哪些變體」使用
    if not patterns:
        return sorted(parts, key=lambda p: p.get("IPN") or "")
    chosen = [p for p in parts if any(fnmatch.fnmatchcase(p.get("IPN") or "", pat) for pat in patterns)]
    return sorted(chosen, key=lambda p: p.get("IPN") or "")


def fmt(n):
    if n is None:
        return "?"
    return str(int(n)) if float(n) == int(n) else f"{n:g}"


def describe(p):
    kind = "範本" if p.get("is_template") else ("變體" if p.get("variant_of") else "零件")
    state = "啟用" if p.get("active") else "已停用"
    stock = p.get("total_in_stock", p.get("in_stock"))
    return f"{p.get('IPN') or '(無料號)':<22} {kind:<3} {state:<4} 庫存 {fmt(stock):>6}  {p.get('full_name') or p.get('name') or ''}"


# ---------- 刪除前檢查 ----------

def check_delete(api, p, selected_pks):
    """回傳這個零件不能刪除的原因清單（空＝可以刪）與警告清單。"""
    blocked, warn = [], []
    if p.get("active"):
        blocked.append("仍在啟用中，請先執行 retire 停用")
    if p.get("locked"):
        blocked.append("零件已鎖定（PART_ENABLE_LOCKING）")

    stock = p.get("total_in_stock", p.get("in_stock"))
    if stock is None:
        warn.append("讀不到庫存數量")
    elif float(stock) != 0:
        blocked.append(f"還有庫存 {fmt(stock)}（刪除會連庫存一起消失；請先處理掉庫存）")

    if p.get("is_template"):
        variants = [v for v in getattr(api, "all_parts", []) if v.get("variant_of") == p["pk"] and v["pk"] not in selected_pks]
        if variants:
            blocked.append(f"是範本，底下還有 {len(variants)} 個變體不在這次刪除範圍（刪了它們會變成獨立零件）。"
                           "請一併選取變體，或先處理變體")

    so = api.count("/api/order/so-line/", part=p["pk"])
    if so is None:
        warn.append("無法確認銷售單明細")
    elif so:
        blocked.append(f"有 {so} 筆銷售單明細（出貨紀錄會受影響）")
    n_sp = api.count("/api/company/part/", part=p["pk"])
    po_total = 0
    if n_sp is None:
        warn.append("無法確認採購單明細")
    elif n_sp:
        for sp in api.list("/api/company/part/", part=p["pk"]):
            n = api.count("/api/order/po-line/", part=sp["pk"])
            if n is None:
                warn.append("無法確認採購單明細")
                break
            po_total += n
    if po_total:
        blocked.append(f"有 {po_total} 筆採購單明細（進貨紀錄會受影響）")
    for key, label in (("ordering", "採購中"), ("building", "生產中"), ("allocated_to_sales_orders", "已分配給銷售單"),
                       ("allocated_to_build_orders", "已分配給生產單")):
        v = p.get(key)
        if v not in (None, 0, 0.0, "0", "0.0") and float(v) != 0:
            blocked.append(f"{label}：{fmt(v)}")
    return blocked, warn


# ---------- 刪除前匯出 ----------

def export_before_delete(api, parts, outdir):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "parts.json"), "w", encoding="utf-8") as f:
        json.dump(parts, f, ensure_ascii=False, indent=2)
    pks = {p["pk"] for p in parts}
    ipn = {p["pk"]: p.get("IPN") or "" for p in parts}
    rows = []
    for p in parts:
        rows += api.list("/api/stock/track/", part=p["pk"], user_detail="true")
    path = os.path.join(outdir, "stock-history.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["時間", "操作人", "料號", "動作", "異動內容", "備註"])
        for r in rows:
            part_pk = r.get("part")
            if pks and part_pk not in pks:
                continue
            w.writerow([r.get("date", ""), (r.get("user_detail") or {}).get("username", r.get("user", "")), ipn.get(part_pk, ""),
                        r.get("label", ""), json.dumps(r.get("deltas") or {}, ensure_ascii=False), r.get("notes") or ""])
    return len(rows)


def record_removed(path, ipns, who="manage_parts.py"):
    """記下已刪除的料號，讓匯入腳本（seed_skus.py）不會再把它們建回來。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {"removed": []}
    have = {r["ipn"] for r in data.get("removed", [])}
    for i in ipns:
        if i not in have:
            data["removed"].append({"ipn": i, "removed_at": time.strftime("%Y-%m-%d %H:%M:%S"), "by": who})
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------- 子命令 ----------

def make_api():
    url, token = os.environ.get("INVENTREE_URL"), os.environ.get("INVENTREE_TOKEN")
    if not url or not token:
        sys.exit("請設定環境變數 INVENTREE_URL 與 INVENTREE_TOKEN。")
    return Api(url, token)


def confirm(prompt, assume_yes):
    return True if assume_yes else input(prompt).strip().lower() in ("y", "yes")


def cmd_list(args):
    api = make_api()
    parts = select_parts(api, read_patterns(args), status=args.status, require_pattern=False)
    for p in parts:
        print(describe(p))
    active = sum(1 for p in parts if p.get("active"))
    print(f"\n共 {len(parts)} 筆（啟用 {active}、已停用 {len(parts) - active}）")


def set_active(args, active):
    api = make_api()
    word = "還原為啟用" if active else "停用"
    parts = select_parts(api, read_patterns(args), status="inactive" if active else "active")
    if not parts:
        print(f"沒有符合且需要{word}的零件。")
        return
    print(f"將{word}以下 {len(parts)} 個零件（零件、庫存與異動紀錄都保留，隨時可反向操作）：")
    for p in parts:
        print("  " + describe(p))
    if args.dry_run:
        print("（--dry-run：未寫入）")
        return
    if not confirm("確定執行？(Y/N) ", args.yes):
        print("已取消，未做任何變更。")
        return
    for p in parts:
        api.patch(f"/api/part/{p['pk']}/", {"active": active})
    print(f"完成：已{word} {len(parts)} 個零件。")


def cmd_retire(args):
    set_active(args, False)


def cmd_restore(args):
    set_active(args, True)


def cmd_delete(args):
    api = make_api()
    parts = select_parts(api, read_patterns(args))
    if not parts:
        print("沒有符合的零件。")
        return
    selected = {p["pk"] for p in parts}
    ok, bad = [], []
    for p in parts:
        blocked, warn = check_delete(api, p, selected)
        (bad if blocked else ok).append((p, blocked, warn))

    print(f"符合的零件共 {len(parts)} 個：可刪除 {len(ok)}、不可刪除 {len(bad)}\n")
    for p, blocked, _ in bad:
        print(f"✘ {describe(p)}")
        for b in blocked:
            print(f"      - {b}")
    for p, _, warn in ok:
        print(f"✔ {describe(p)}" + (f"　⚠️ {'；'.join(warn)}" if warn else ""))
    if not ok:
        print("\n沒有可以刪除的零件。需要的話先用 retire 停用，或先處理上面列出的原因。")
        return
    if any(w for _, _, w in ok) and not args.ignore_warnings:
        sys.exit("\n有無法確認的項目（⚠️）。請先到網頁確認該零件沒有訂單，再加上 --ignore-warnings 重新執行。")

    print("\n⚠️ 永久刪除會一併刪除這些零件的『庫存項目與全部異動紀錄』，無法復原。")
    print("   刪除前會先匯出零件資料與異動紀錄到資料夾；" + BACKUP_NOTICE)
    if args.dry_run:
        print("（--dry-run：未刪除任何東西）")
        return
    todo = sorted((p for p, _, _ in ok), key=lambda p: 0 if p.get("variant_of") else 1)   # 變體先刪，最後才刪範本
    if not args.yes:
        typed = input(f"要永久刪除以上 {len(todo)} 個零件，請輸入數字 {len(todo)} 確認：").strip()
        if typed != str(len(todo)):
            print("輸入不符，已取消，未做任何變更。")
            return
        if input("你已經備份過了嗎？(Y/N) ").strip().lower() not in ("y", "yes"):
            print("已取消。請先備份再執行。")
            return

    outdir = os.path.join(args.export_dir, "deleted-parts-" + time.strftime("%Y%m%d-%H%M%S"))
    n = export_before_delete(api, todo, outdir)
    print(f"已匯出 {len(todo)} 個零件與 {n} 筆異動紀錄 → {outdir}")

    deleted = []
    for p in todo:
        # 單筆失敗（例如伺服器的其他限制）要如實回報，不能默默略過
        api.delete(f"/api/part/{p['pk']}/")
        deleted.append(p["IPN"])
    record_removed(args.removed_file, [i for i in deleted if i])
    print(f"完成：已刪除 {len(deleted)} 個零件。")
    print(f"已記錄到 {args.removed_file}：之後執行 seed_skus.py 不會再把這些料號建回來。")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def selectors(s):
        s.add_argument("--ipn", action="append", help="料號（可重複）")
        s.add_argument("--glob", action="append", help='萬用字元，例如 "A-P03-S5-*"（可重複）')
        s.add_argument("--file", help="清單檔，每行一個料號或萬用字元")

    s = sub.add_parser("list", help="查看零件（唯讀）")
    selectors(s)
    s.add_argument("--status", choices=["all", "active", "inactive"], default="all")
    s.set_defaults(fn=cmd_list)
    for name, fn, helptext in (("retire", cmd_retire, "停用（可還原）"), ("restore", cmd_restore, "還原為啟用")):
        s = sub.add_parser(name, help=helptext)
        selectors(s)
        s.add_argument("--dry-run", action="store_true")
        s.add_argument("--yes", action="store_true", help="略過確認（自動化用）")
        s.set_defaults(fn=fn)
    s = sub.add_parser("delete", help="永久刪除（會連庫存與異動紀錄一起刪）")
    selectors(s)
    s.add_argument("--dry-run", action="store_true", help="只列出檢查結果，不刪除")
    s.add_argument("--yes", action="store_true", help="略過互動確認（自動化／測試用；仍會做全部安全檢查與匯出）")
    s.add_argument("--ignore-warnings", action="store_true", help="略過『無法確認』類警告")
    s.add_argument("--export-dir", default=os.getcwd(), help="匯出資料夾的位置（預設為目前資料夾）")
    s.add_argument("--removed-file", default=DEFAULT_REMOVED, help="記錄已刪除料號的檔案（供 seed_skus.py 排除）")
    s.set_defaults(fn=cmd_delete)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
