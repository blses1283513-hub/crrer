#!/usr/bin/env python3
"""職務分級：建立公司群組與職務群組、設定各角色權限、替使用者加入群組。

權限模型（InvenTree）：
  * 使用者的權限 = 所屬所有群組的『聯集』。
  * 『公司群組』company-A/B/C：庫位擁有權（由 seed_skus.py 設定）決定能修改哪家公司的庫存；本身只給檢視。
  * 『職務群組』role-*：決定能做什麼動作（見 roles.json）。
  * 修改自家公司庫存 = 屬於該公司群組 + 屬於一個有『庫存新增／修改』的職務群組。
  * 此腳本不會碰 superuser / staff 旗標，也不會建立或刪除管理員。

子命令：
  show      不連線，顯示 roles.json 的權限矩陣
  apply     建立群組並設定權限（會先列出變更並要求確認）
  audit     唯讀稽核：superuser/staff 人數、沒有群組的使用者、各群組成員
  add-user  建立使用者、設定密碼並加入群組（不需要郵件伺服器）

用法：
  python3 setup_roles.py show
  INVENTREE_URL=http://localhost INVENTREE_TOKEN=xxx python3 setup_roles.py apply --config config.json
  INVENTREE_URL=... INVENTREE_TOKEN=... python3 setup_roles.py add-user a-wh --groups company-A,role-warehouse

只依賴 Python 標準函式庫。
"""

import argparse
import getpass
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIONS = ["view", "add", "change", "delete"]
ACTION_ZH = {"view": "檢視", "add": "新增", "change": "修改", "delete": "刪除"}

# InvenTree 1.5.6 的角色（ruleset）名稱與中文
RULESET_ZH = {
    "admin": "管理（可指派權限）", "part_category": "零件分類", "part": "零件", "bom": "物料清單",
    "stock_location": "庫位", "stock": "庫存項目", "build": "生產單", "purchase_order": "採購單",
    "sales_order": "銷售單", "return_order": "退貨單", "transfer_order": "轉移單",
}

ENDPOINTS = {
    "group": "/api/user/group/",
    "ruleset": "/api/user/ruleset/",
    "user": "/api/user/",
}


# ---------- 設定讀取與驗證 ----------

def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        hint = "（請先複製 config.example.json 為 config.json）" if what == "公司設定" else ""
        sys.exit(f"找不到{what}：{path}{hint}")
    except json.JSONDecodeError as e:
        sys.exit(f"{what}不是有效的 JSON：{path}（第 {e.lineno} 行）")


def validate_permissions(where, perms):
    for ruleset, actions in perms.items():
        if ruleset not in RULESET_ZH:
            sys.exit(f"{where}：未知的角色「{ruleset}」。可用：{', '.join(RULESET_ZH)}")
        bad = [a for a in actions if a not in ACTIONS]
        if bad:
            sys.exit(f"{where}：角色 {ruleset} 有未知的動作 {bad}。可用：{ACTIONS}")


def build_targets(config, roles):
    """回傳 [(群組名稱, 標籤, {ruleset: set(動作)})]，公司群組在前、職務群組在後。"""
    targets = []
    base = roles.get("company_group_permissions", {})
    validate_permissions("company_group_permissions", base)
    for co in config.get("companies", []):
        targets.append((co["owner_group"], f"{co['name']}（公司群組）", {k: set(v) for k, v in base.items()}))
    seen = {t[0] for t in targets}
    for tier in roles.get("tiers", []):
        name = tier["group"]
        if name in seen:
            sys.exit(f"群組名稱重複：{name}")
        seen.add(name)
        validate_permissions(f"職務 {name}", tier["permissions"])
        targets.append((name, tier.get("label", name), {k: set(v) for k, v in tier["permissions"].items()}))
    if not targets:
        sys.exit("沒有任何要建立的群組，請檢查 config.json 與 roles.json。")
    return targets


def fmt_actions(actions):
    return "＋".join(ACTION_ZH[a] for a in ACTIONS if a in actions) or "無"


def show_matrix(targets):
    rulesets = [r for r in RULESET_ZH if any(r in t[2] for t in targets)]
    for name, label, perms in targets:
        print(f"\n■ {name}　{label}")
        for r in rulesets:
            if r in perms:
                print(f"    {RULESET_ZH[r]:<8} {fmt_actions(perms[r])}")
        print("    其他角色：全部關閉")


# ---------- API ----------

class Api:
    def __init__(self, base, token):
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Token {token}", "Content-Type": "application/json", "Accept": "application/json"}

    def _req(self, method, path, params=None, body=None):
        url = self.base + path + ("?" + urllib.parse.urlencode(params) if params else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=self.headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            hint = ""
            if e.code in (401, 403):
                hint = "（請確認 token 屬於管理員帳號，且尚未過期）"
            sys.exit(f"API 錯誤 {e.code} {method} {path}{hint}：{detail}")
        except urllib.error.URLError as e:
            sys.exit(f"連不到 {self.base}：{e.reason}。請確認系統已啟動，且 INVENTREE_URL 正確。")

    def list(self, key, **params):
        out, offset = [], 0
        while True:
            res = self._req("GET", ENDPOINTS[key], params={**params, "limit": 200, "offset": offset})
            if isinstance(res, list):
                return res
            out += res.get("results", [])
            if not res.get("next") or not res.get("results"):
                return out
            offset += len(res["results"])

    def get(self, path):
        return self._req("GET", path)

    def post(self, key, body):
        return self._req("POST", ENDPOINTS[key], body=body)

    def patch(self, path, body):
        return self._req("PATCH", path, body=body)


def current_actions(rs):
    return {a for a in ACTIONS if rs.get(f"can_{a}")}


def find_group(api, name):
    return next((g for g in api.list("group", search=name) if g.get("name") == name), None)


def read_state(api, targets):
    """讀取現況：每個目標群組是否存在、各角色目前的權限。"""
    state = []
    for name, label, perms in targets:
        group = find_group(api, name)
        rulesets = api.list("ruleset", group=group["pk"]) if group else []
        state.append({"name": name, "label": label, "perms": perms, "group": group, "rulesets": {r["name"]: r for r in rulesets}})
    return state


def plan_changes(state):
    """回傳要做的事：[(item, [(ruleset 名稱, 現有, 目標)])]。群組尚未建立時，現有視為『無』。"""
    plan = []
    for item in state:
        changes = []
        names = set(item["perms"]) | set(item["rulesets"])
        for r in sorted(names, key=lambda n: list(RULESET_ZH).index(n) if n in RULESET_ZH else 99):
            target = item["perms"].get(r, set())
            cur = current_actions(item["rulesets"][r]) if r in item["rulesets"] else set()
            if cur != target:
                changes.append((r, cur, target))
        plan.append((item, changes))
    return plan


def print_plan(plan):
    total = 0
    for item, changes in plan:
        status = "新建群組" if not item["group"] else ("無變更" if not changes else "更新權限")
        print(f"\n■ {item['name']}　{item['label']}　【{status}】")
        for r, cur, target in changes:
            total += 1
            danger = "　⚠️ 含刪除權限" if "delete" in target and "delete" not in cur else ""
            print(f"    {RULESET_ZH.get(r, r):<8} {fmt_actions(cur)} → {fmt_actions(target)}{danger}")
    return total


def warn_admin_role(plan):
    for item, _ in plan:
        if "admin" in item["perms"] and item["perms"]["admin"]:
            print(f"⚠️ 群組 {item['name']} 含「管理」角色：成員可指派他人權限（全系統，無法限定公司）。")


def apply_plan(api, plan):
    created = changed = 0
    for item, changes in plan:
        if not item["group"]:
            item["group"] = api.post("group", {"name": item["name"]})
            created += 1
        if not item["rulesets"]:
            item["rulesets"] = {r["name"]: r for r in api.list("ruleset", group=item["group"]["pk"])}
            if not item["rulesets"]:
                sys.exit(f"群組 {item['name']} 建立後找不到角色設定，請重新執行本腳本一次。")
        for r, cur, target in changes:
            rs = item["rulesets"].get(r)
            if not rs:
                sys.exit(f"群組 {item['name']} 沒有角色「{r}」，這個 InvenTree 版本可能不支援。")
            api.patch(f"{ENDPOINTS['ruleset']}{rs['pk']}/", {f"can_{a}": a in target for a in ACTIONS})
            changed += 1
    return created, changed


def confirm(prompt, assume_yes):
    if assume_yes:
        return True
    return input(prompt).strip().lower() in ("y", "yes")


# ---------- 子命令 ----------

def make_api(args):
    url, token = os.environ.get("INVENTREE_URL"), os.environ.get("INVENTREE_TOKEN")
    if not url or not token:
        sys.exit("請設定環境變數 INVENTREE_URL 與 INVENTREE_TOKEN。")
    return Api(url, token)


def load_targets(args):
    config = load_json(args.config, "公司設定")
    roles = load_json(args.roles, "職務設定")
    return build_targets(config, roles)


def cmd_show(args):
    show_matrix(load_targets(args))


def cmd_apply(args):
    targets = load_targets(args)
    api = make_api(args)
    state = read_state(api, targets)
    plan = plan_changes(state)
    print("將對 InvenTree 進行以下變更：")
    total = print_plan(plan)
    new_groups = sum(1 for item, _ in plan if not item["group"])
    warn_admin_role(plan)
    print(f"\n合計：新建群組 {new_groups} 個、權限變更 {total} 項。不會改動任何使用者與 superuser/staff 設定。")
    if args.dry_run:
        print("（--dry-run：只列出，未寫入）")
        return
    if not total and not new_groups:
        print("已是目標狀態，不需要變更。")
        return
    if not confirm("確定執行？(Y/N) ", args.yes):
        print("已取消，未做任何變更。")
        return
    created, changed = apply_plan(api, plan)
    # 寫入後重新讀取驗證
    left = sum(len(c) for _, c in plan_changes(read_state(api, targets)))
    print(f"\n完成：新建群組 {created} 個、更新權限 {changed} 項。")
    if left:
        sys.exit(f"驗證失敗：仍有 {left} 項權限與目標不符，請重新執行一次或到管理中心檢查。")
    print("驗證通過：所有群組權限與 roles.json 一致。")
    print("下一步：用 add-user 建立使用者，或在管理中心把使用者加入『公司群組＋職務群組』。")


def cmd_audit(args):
    api = make_api(args)
    users = api.list("user")
    supers = [u for u in users if u.get("is_superuser")]
    staff = [u for u in users if u.get("is_staff") and not u.get("is_superuser")]
    nogroup = [u for u in users if not u.get("is_superuser") and not u.get("groups")]
    inactive = [u for u in users if u.get("is_active") is False]
    print(f"使用者共 {len(users)} 人：superuser {len(supers)}、staff（非 superuser）{len(staff)}、已停用 {len(inactive)}")
    problems = 0
    if len(supers) > 2:
        problems += 1
        print(f"⚠️ superuser 有 {len(supers)} 人（建議 ≤ 2）：{', '.join(u['username'] for u in supers)}")
    if staff:
        print(f"ℹ️ staff 帳號：{', '.join(u['username'] for u in staff)}（可進管理後台，請確認有必要）")
    if nogroup:
        problems += 1
        print(f"⚠️ 沒有加入任何群組、因此沒有任何權限的帳號：{', '.join(u['username'] for u in nogroup)}")
    print("\n各使用者的群組：")
    for u in sorted(users, key=lambda x: x["username"]):
        tag = "（superuser）" if u.get("is_superuser") else ""
        names = ", ".join(g["name"] for g in u.get("groups", [])) or "—"
        print(f"  {u['username']:<16}{tag} {names}")
    # 沒有職務群組或沒有公司群組的一般使用者
    for u in users:
        if u.get("is_superuser"):
            continue
        names = {g["name"] for g in u.get("groups", [])}
        if names and not any(n.startswith("role-") for n in names):
            problems += 1
            print(f"⚠️ {u['username']} 只有公司群組、沒有職務群組：只能檢視，不能修改。")
    print("\n稽核結束。" + ("有需要注意的項目。" if problems else "未發現問題。"))


def cmd_add_user(args):
    api = make_api(args)
    wanted = [g.strip() for g in args.groups.split(",") if g.strip()]
    if not wanted:
        sys.exit("請用 --groups 指定至少一個群組，例如 --groups company-A,role-warehouse")
    group_ids = []
    for name in wanted:
        g = find_group(api, name)
        if not g:
            sys.exit(f"找不到群組「{name}」。請先執行 apply 建立群組。")
        group_ids.append(g["pk"])

    existing = [u for u in api.list("user", search=args.username) if u.get("username") == args.username]
    if existing:
        sys.exit(f"使用者 {args.username} 已存在。如要加入群組，請在管理中心操作，或使用不同帳號名稱。")

    password = os.environ.get("INVENTREE_NEW_USER_PASSWORD")
    if not password:
        password = getpass.getpass(f"為 {args.username} 設定密碼（輸入時不會顯示）：")
        if getpass.getpass("再輸入一次：") != password:
            sys.exit("兩次密碼不一致，已取消。")
    if not password:
        sys.exit("密碼不可為空。")

    print(f"將建立使用者 {args.username}，加入群組：{', '.join(wanted)}")
    if not confirm("確定執行？(Y/N) ", args.yes):
        print("已取消，未做任何變更。")
        return
    body = {"username": args.username, "email": args.email or "", "first_name": args.first_name or "",
            "last_name": args.last_name or "", "group_ids": group_ids}
    user = api.post("user", body)
    api.patch(f"{ENDPOINTS['user']}{user['pk']}/set-password/", {"password": password})
    fresh = api.get(f"{ENDPOINTS['user']}{user['pk']}/")
    have = {g["pk"] for g in fresh.get("groups", [])}
    missing = [n for n, pk in zip(wanted, group_ids) if pk not in have]
    if missing:
        # 建立時沒有套用群組的版本：補一次
        api.patch(f"{ENDPOINTS['user']}{user['pk']}/", {"group_ids": sorted(have | set(group_ids))})
        fresh = api.get(f"{ENDPOINTS['user']}{user['pk']}/")
        have = {g["pk"] for g in fresh.get("groups", [])}
        missing = [n for n, pk in zip(wanted, group_ids) if pk not in have]
    if missing:
        sys.exit(f"使用者已建立，但加入群組失敗：{', '.join(missing)}。請到管理中心手動加入。")
    print(f"完成：{args.username} 已建立並加入 {', '.join(wanted)}。請把帳號與密碼用安全的方式交給本人，並請對方登入後自行更改密碼。")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=os.path.join(HERE, "config.json"), help="公司設定（預設 config.json）")
    ap.add_argument("--roles", default=os.path.join(HERE, "roles.json"), help="職務設定（預設 roles.json）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show", help="顯示權限矩陣（不連線）")
    s.set_defaults(fn=cmd_show)
    s = sub.add_parser("apply", help="建立群組並設定權限")
    s.add_argument("--dry-run", action="store_true", help="只列出變更，不寫入")
    s.add_argument("--yes", action="store_true", help="略過確認（自動化用）")
    s.set_defaults(fn=cmd_apply)
    s = sub.add_parser("audit", help="唯讀稽核")
    s.set_defaults(fn=cmd_audit)
    s = sub.add_parser("add-user", help="建立使用者並加入群組")
    s.add_argument("username")
    s.add_argument("--groups", required=True, help="以逗號分隔，例如 company-A,role-warehouse")
    s.add_argument("--email")
    s.add_argument("--first-name")
    s.add_argument("--last-name")
    s.add_argument("--yes", action="store_true")
    s.set_defaults(fn=cmd_add_user)
    args = ap.parse_args()
    if args.cmd == "show" and not os.path.exists(args.config):
        args.config = os.path.join(HERE, "config.example.json")
    args.fn(args)


if __name__ == "__main__":
    main()
