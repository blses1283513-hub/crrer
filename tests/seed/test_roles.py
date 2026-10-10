"""職務分級腳本 setup_roles.py 的自動測試：以模擬的 InvenTree 使用者 API 驗證，
並對 roles.json 的『權限政策』加上防呆測試（避免日後誤改變成過大的權限）。

執行：python -m unittest discover -s tests/seed -v
"""

import contextlib
import http.server
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import threading
import unittest
from argparse import Namespace
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEED_DIR = os.path.join(ROOT, "inventree-seed")
SCRIPT = os.path.join(SEED_DIR, "setup_roles.py")
CONFIG = os.path.join(SEED_DIR, "config.example.json")
ROLES = os.path.join(SEED_DIR, "roles.json")
TOKEN = "admin-token"

spec = importlib.util.spec_from_file_location("setup_roles", SCRIPT)
setup_roles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup_roles)

RULESETS = ["admin", "part_category", "part", "bom", "stock_location", "stock", "build",
            "purchase_order", "sales_order", "return_order", "transfer_order"]


class MockUsers:
    """記憶體中的最小使用者／群組／權限 API。"""

    def __init__(self):
        self.groups, self.rulesets, self.users = [], [], []
        self.passwords = {}
        self.next_pk = 10
        self.requests = []
        self.ignore_group_ids_on_create = False
        self.reject_password = None

    def pk(self):
        self.next_pk += 1
        return self.next_pk

    def add_group(self, name, **perms):
        g = {"pk": self.pk(), "name": name}
        self.groups.append(g)
        for r in RULESETS:
            rs = {"pk": self.pk(), "name": r, "label": r, "group": g["pk"],
                  "can_view": False, "can_add": False, "can_change": False, "can_delete": False}
            for a in perms.get(r, []):
                rs[f"can_{a}"] = True
            self.rulesets.append(rs)
        return g

    def add_user(self, username, groups=(), **flags):
        u = {"pk": self.pk(), "username": username, "email": "", "first_name": "", "last_name": "",
             "is_superuser": False, "is_staff": False, "is_active": True, "group_ids": [g["pk"] for g in groups]}
        u.update(flags)
        self.users.append(u)
        return u

    def user_out(self, u):
        out = {k: v for k, v in u.items() if k != "group_ids"}
        out["groups"] = [{"pk": g["pk"], "name": g["name"]} for g in self.groups if g["pk"] in u["group_ids"]]
        return out

    def writes(self):
        return [r for r in self.requests if r[0] != "GET"]

    def handle(self, method, path, query, body, headers):
        self.requests.append((method, path))
        if headers.get("Authorization") != f"Token {TOKEN}":
            return 403, {"detail": "You do not have permission to perform this action."}
        page = lambda rows: {"count": len(rows), "next": None, "results": rows}

        if path == "/api/user/group/":
            if method == "GET":
                s = query.get("search", "").lower()
                return 200, page([g for g in self.groups if s in g["name"].lower()])
            if method == "POST":
                if any(g["name"] == body["name"] for g in self.groups):
                    return 400, {"name": ["group with this name already exists."]}
                return 201, self.add_group(body["name"])
        if path == "/api/user/ruleset/" and method == "GET":
            rows = [r for r in self.rulesets if "group" not in query or str(r["group"]) == query["group"]]
            return 200, page(rows)
        m = re.fullmatch(r"/api/user/ruleset/(\d+)/", path)
        if m and method == "PATCH":
            rs = next(r for r in self.rulesets if r["pk"] == int(m.group(1)))
            rs.update({k: v for k, v in body.items() if k.startswith("can_")})
            return 200, rs
        if path == "/api/user/" and method == "GET":
            s = query.get("search", "").lower()
            return 200, page([self.user_out(u) for u in self.users if s in u["username"].lower()])
        if path == "/api/user/" and method == "POST":
            u = self.add_user(body["username"], email=body.get("email", ""))
            if not self.ignore_group_ids_on_create:
                u["group_ids"] = list(body.get("group_ids", []))
            return 201, self.user_out(u)
        m = re.fullmatch(r"/api/user/(\d+)/set-password/", path)
        if m and method == "PATCH":
            if body.get("password") == self.reject_password:
                return 400, {"password": ["This password is too common."]}
            self.passwords[int(m.group(1))] = body["password"]
            return 200, {}
        m = re.fullmatch(r"/api/user/(\d+)/", path)
        if m:
            u = next(x for x in self.users if x["pk"] == int(m.group(1)))
            if method == "PATCH":
                u["group_ids"] = list(body.get("group_ids", u["group_ids"]))
            return 200, self.user_out(u)
        return 404, {"detail": "not mocked: " + path}


class Handler(http.server.BaseHTTPRequestHandler):
    mock = None

    def log_message(self, *a):
        pass

    def _do(self):
        from urllib.parse import urlparse, parse_qsl
        u = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length)) if length else None
        code, data = self.mock.handle(self.command, u.path, dict(parse_qsl(u.query)), body, self.headers)
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    do_GET = do_POST = do_PATCH = _do


class RolesTestCase(unittest.TestCase):
    def setUp(self):
        self.m = MockUsers()
        Handler.mock = self.m
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.env = mock.patch.dict(os.environ, {"INVENTREE_URL": f"http://127.0.0.1:{self.server.server_address[1]}",
                                                "INVENTREE_TOKEN": TOKEN})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()

    def run_cmd(self, fn, stdin="y\n", **kw):
        opts = dict(config=CONFIG, roles=ROLES, dry_run=False, yes=False)
        opts.update(kw)
        args = Namespace(**opts)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch("builtins.input", side_effect=lambda *_: stdin.strip()):
            fn(args)
        return out.getvalue()

    def perms_of(self, group_name):
        g = next(g for g in self.m.groups if g["name"] == group_name)
        return {r["name"]: {a for a in ("view", "add", "change", "delete") if r[f"can_{a}"]}
                for r in self.m.rulesets if r["group"] == g["pk"]}


class ApplyTests(RolesTestCase):
    def test_apply_creates_company_and_role_groups_with_exact_permissions(self):
        out = self.run_cmd(setup_roles.cmd_apply)
        names = {g["name"] for g in self.m.groups}
        self.assertEqual(names, {"company-A", "company-B", "company-C",
                                 "role-manager", "role-warehouse", "role-sales", "role-viewer"})
        self.assertIn("驗證通過", out)
        wh = self.perms_of("role-warehouse")
        self.assertEqual(wh["stock"], {"view", "add", "change"})
        self.assertEqual(wh["sales_order"], {"view"})
        self.assertEqual(wh["admin"], set(), "未列出的角色必須全部關閉")
        self.assertEqual(self.perms_of("company-A")["stock"], {"view"})

    def test_apply_is_idempotent(self):
        self.run_cmd(setup_roles.cmd_apply)
        before = len(self.m.writes())
        out = self.run_cmd(setup_roles.cmd_apply)
        self.assertEqual(len(self.m.writes()), before, "第二次執行不可再寫入")
        self.assertIn("已是目標狀態", out)

    def test_existing_group_with_excess_permissions_is_corrected_and_reported(self):
        self.m.add_group("role-viewer", stock=["view", "add", "change", "delete"], admin=["view", "add", "change", "delete"])
        out = self.run_cmd(setup_roles.cmd_apply)
        self.assertEqual(self.perms_of("role-viewer")["stock"], {"view"})
        self.assertEqual(self.perms_of("role-viewer")["admin"], set())
        self.assertRegex(out, r"庫存項目\s+檢視＋新增＋修改＋刪除 → 檢視")

    def test_dry_run_and_cancel_write_nothing(self):
        self.run_cmd(setup_roles.cmd_apply, dry_run=True)
        self.assertEqual(self.m.writes(), [])
        out = self.run_cmd(setup_roles.cmd_apply, stdin="n\n")
        self.assertEqual(self.m.writes(), [])
        self.assertIn("已取消", out)

    def test_wrong_token_gives_hint(self):
        with mock.patch.dict(os.environ, {"INVENTREE_TOKEN": "bad"}):
            with self.assertRaises(SystemExit) as cm:
                self.run_cmd(setup_roles.cmd_apply)
        self.assertIn("403", str(cm.exception))
        self.assertIn("token", str(cm.exception))

    def test_requires_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit) as cm:
                self.run_cmd(setup_roles.cmd_apply)
        self.assertIn("INVENTREE_TOKEN", str(cm.exception))


class AddUserTests(RolesTestCase):
    def setUp(self):
        super().setUp()
        self.run_cmd(setup_roles.cmd_apply)

    def add(self, username="a-wh", groups="company-A,role-warehouse", password="Str0ng-Pass-123"):
        with mock.patch.dict(os.environ, {"INVENTREE_NEW_USER_PASSWORD": password}):
            return self.run_cmd(setup_roles.cmd_add_user, username=username, groups=groups, email="a@x.com",
                                first_name="", last_name="")

    def test_add_user_sets_password_and_groups_without_leaking_password(self):
        out = self.add()
        u = next(x for x in self.m.users if x["username"] == "a-wh")
        self.assertEqual({g["name"] for g in self.m.user_out(u)["groups"]}, {"company-A", "role-warehouse"})
        self.assertEqual(self.m.passwords[u["pk"]], "Str0ng-Pass-123")
        self.assertNotIn("Str0ng-Pass-123", out, "密碼不可出現在輸出中")

    def test_groups_are_applied_even_if_server_ignores_them_on_create(self):
        self.m.ignore_group_ids_on_create = True
        self.add()
        u = next(x for x in self.m.users if x["username"] == "a-wh")
        self.assertEqual(len(u["group_ids"]), 2)

    def test_duplicate_user_and_unknown_group_are_rejected(self):
        self.add()
        with self.assertRaises(SystemExit):
            self.add()
        with self.assertRaises(SystemExit) as cm:
            self.add(username="x", groups="company-Z")
        self.assertIn("company-Z", str(cm.exception))
        self.assertFalse(any(u["username"] == "x" for u in self.m.users), "群組不存在時不應建立使用者")

    def test_weak_password_error_is_surfaced(self):
        self.m.reject_password = "123"
        with self.assertRaises(SystemExit) as cm:
            self.add(password="123")
        self.assertIn("password", str(cm.exception))


class AuditTests(RolesTestCase):
    def test_audit_flags_risky_accounts(self):
        self.run_cmd(setup_roles.cmd_apply)
        grp = lambda n: next(g for g in self.m.groups if g["name"] == n)
        for n in ("root1", "root2", "root3"):
            self.m.add_user(n, is_superuser=True)
        self.m.add_user("nogroup")
        self.m.add_user("a-only", groups=[grp("company-A")])
        self.m.add_user("a-wh", groups=[grp("company-A"), grp("role-warehouse")])
        out = self.run_cmd(setup_roles.cmd_audit)
        self.assertIn("superuser 有 3 人", out)
        self.assertIn("nogroup", out)
        self.assertIn("a-only 只有公司群組", out)
        self.assertNotIn("a-wh 只有公司群組", out)

    def test_audit_is_read_only(self):
        self.m.add_user("u")
        self.run_cmd(setup_roles.cmd_audit)
        self.assertEqual(self.m.writes(), [])


class ConfigValidationTests(unittest.TestCase):
    def test_unknown_ruleset_and_action_are_rejected(self):
        for perms in ({"nonsense": ["view"]}, {"stock": ["explode"]}):
            with self.assertRaises(SystemExit):
                setup_roles.validate_permissions("t", perms)

    def test_show_runs_offline(self):
        r = subprocess.run([sys.executable, "-I", SCRIPT, "show"], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("role-warehouse", r.stdout)
        self.assertIn("company-A", r.stdout)


class PolicyTests(unittest.TestCase):
    """roles.json 的權限政策：寫成測試，避免日後誤改變成過大的權限。"""

    @classmethod
    def setUpClass(cls):
        with open(ROLES, encoding="utf-8") as f:
            cls.roles = json.load(f)
        cls.tiers = {t["group"]: t["permissions"] for t in cls.roles["tiers"]}
        cls.everything = [cls.roles["company_group_permissions"], *cls.tiers.values()]

    def test_nobody_can_delete(self):
        for perms in self.everything:
            for r, acts in perms.items():
                self.assertNotIn("delete", acts, f"{r} 不應有刪除權限（庫存錯誤請用盤點修正）")

    def test_nobody_gets_admin_role(self):
        for perms in self.everything:
            self.assertNotIn("admin", perms, "管理角色是全系統的，不應交給任何職務群組")

    def test_company_groups_are_view_only(self):
        for r, acts in self.roles["company_group_permissions"].items():
            self.assertEqual(set(acts), {"view"}, r)

    def test_only_manager_and_warehouse_can_modify_stock(self):
        # 庫存的移除／轉移／盤點是 POST，需要 stock 的 add 權限
        can = {g for g, p in self.tiers.items() if {"add", "change"} & set(p.get("stock", []))}
        self.assertEqual(can, {"role-manager", "role-warehouse"})

    def test_viewer_is_strictly_read_only(self):
        for r, acts in self.tiers["role-viewer"].items():
            self.assertEqual(set(acts), {"view"}, r)

    def test_sales_cannot_touch_stock_or_purchasing(self):
        sales = self.tiers["role-sales"]
        self.assertEqual(set(sales["stock"]), {"view"})
        self.assertEqual(set(sales["purchase_order"]), {"view"})
        self.assertTrue({"add", "change"} <= set(sales["sales_order"]))

    def test_company_group_names_match_seed_config(self):
        with open(CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        names = {t[0] for t in setup_roles.build_targets(cfg, self.roles)}
        for co in cfg["companies"]:
            self.assertIn(co["owner_group"], names, "公司群組必須與匯入腳本的擁有者群組一致")


if __name__ == "__main__":
    unittest.main()
