"""匯入腳本 seed_skus.py 的自動測試：以模擬的 InvenTree API 驗證。

執行：python -m unittest discover -s tests/seed -v
只使用 Python 標準函式庫。
"""

import csv
import http.server
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.parse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEED_DIR = os.path.join(ROOT, "inventree-seed")
SCRIPT = os.path.join(SEED_DIR, "seed_skus.py")
CONFIG = os.path.join(SEED_DIR, "config.example.json")
TOKEN = "test-token"

spec = importlib.util.spec_from_file_location("seed_skus", SCRIPT)
seed_skus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_skus)


class MockInvenTree:
    """記憶體中的最小 InvenTree API，涵蓋 seed_skus.py 用到的端點。"""

    COLLECTIONS = {
        "/api/stock/location/": "location",
        "/api/part/category/": "category",
        "/api/part/": "part",
        "/api/parameter/template/": "param_template",
        "/api/parameter/": "parameter",
        "/api/user/owner/": "owner",
    }

    def __init__(self, groups=("company-A", "company-B", "company-C")):
        self.db = {k: [] for k in self.COLLECTIONS.values()}
        for i, g in enumerate(groups, 1):
            self.db["owner"].append({"pk": i, "name": g, "label": "group"})
        self.next_pk = 100
        self.requests = []
        self.fail_on = None  # (method, path) → 回傳 400

    def handle(self, method, raw_path, body, headers):
        self.requests.append((method, raw_path))
        if headers.get("Authorization") != f"Token {TOKEN}":
            return 401, {"detail": "Authentication credentials were not provided."}
        url = urllib.parse.urlparse(raw_path)
        path, query = url.path, dict(urllib.parse.parse_qsl(url.query))
        if self.fail_on and self.fail_on == (method, path):
            return 400, {"detail": "simulated failure"}

        for prefix, name in sorted(self.COLLECTIONS.items(), key=lambda kv: -len(kv[0])):
            if path == prefix:
                rows = self.db[name]
                if method == "GET":
                    return 200, [r for r in rows if self._match(r, query)]
                if method == "POST":
                    obj = dict(body)
                    obj["pk"] = self.next_pk
                    self.next_pk += 1
                    obj.setdefault("parent", None)
                    rows.append(obj)
                    return 201, obj
            if path.startswith(prefix) and method == "PATCH":
                pk = int(path[len(prefix):].strip("/"))
                obj = next(r for r in self.db[name] if r["pk"] == pk)
                obj.update(body)
                return 200, obj
        return 404, {"detail": "not mocked: " + path}

    @staticmethod
    def _match(row, query):
        for k, v in query.items():
            if k in ("limit", "offset"):
                continue
            if k == "search":
                hay = " ".join(str(row.get(f, "")) for f in ("name", "IPN"))
                if v.lower() not in hay.lower():
                    return False
            elif str(row.get(k)) != v:
                return False
        return True

    # 統計
    def parts(self, template=None):
        rows = self.db["part"]
        if template is None:
            return rows
        return [p for p in rows if bool(p.get("is_template")) == template]


class Handler(http.server.BaseHTTPRequestHandler):
    mock = None

    def log_message(self, *args):
        pass

    def _do(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length)) if length else None
        code, data = self.mock.handle(self.command, self.path, body, self.headers)
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    do_GET = do_POST = do_PATCH = _do


class SeedTests(unittest.TestCase):
    def setUp(self):
        self.mock = MockInvenTree()
        Handler.mock = self.mock
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.api = seed_skus.Api(f"http://127.0.0.1:{self.server.server_address[1]}", TOKEN)
        self.cfg = seed_skus.load_config(CONFIG)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def run_seed(self):
        templates, variants = seed_skus.build_plan(self.cfg)
        return seed_skus.seed(self.api, self.cfg, templates, variants)

    # ---------- 計畫 ----------
    def test_plan_counts_and_ipn_format(self):
        templates, variants = seed_skus.build_plan(self.cfg)
        self.assertEqual(len(templates), 30)
        self.assertEqual(len(variants), 450)
        ipns = [v["ipn"] for v in variants]
        self.assertEqual(len(set(ipns)), 450, "料號不可重複")
        self.assertIn("A-P03-S2-XL", ipns)
        self.assertRegex(variants[0]["ipn"], r"^[ABC]-P\d{2}-S\d-(XL|L|M)$")

    def test_duplicate_codes_are_rejected(self):
        cfg = dict(self.cfg, styles=[{"code": "S1", "name": "x"}, {"code": "S1", "name": "y"}])
        with self.assertRaises(SystemExit):
            seed_skus.build_plan(cfg)

    def test_dry_run_cli_writes_plan_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "plan.csv")
            env = {k: v for k, v in os.environ.items() if not k.startswith("INVENTREE_")}
            r = subprocess.run([sys.executable, "-I", SCRIPT, "--config", CONFIG, "--dry-run", "--plan-csv", out],
                               capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(out, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 450)

    def test_cli_requires_url_and_token(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("INVENTREE_")}
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, "-I", SCRIPT, "--config", CONFIG, "--plan-csv", os.path.join(d, "p.csv")],
                               capture_output=True, text=True, env=env, timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("INVENTREE_TOKEN", r.stderr)

    # ---------- 寫入 ----------
    def test_seed_creates_everything(self):
        self.run_seed()
        db = self.mock.db
        self.assertEqual(len(self.mock.parts(template=True)), 30)
        self.assertEqual(len(self.mock.parts(template=False)), 450)
        self.assertEqual(len(db["category"]), 3)
        self.assertEqual(len(db["location"]), 6, "3 個公司頂層庫位 + 3 個主倉")
        self.assertEqual({t["name"] for t in db["param_template"]}, {"Style", "Size"})
        self.assertEqual(len(db["parameter"]), 900, "每個 SKU 兩個參數")

        size_tpl = next(t for t in db["param_template"] if t["name"] == "Size")
        self.assertEqual(size_tpl["choices"], "XL,L,M")

    def test_variants_link_to_templates_and_have_min_stock(self):
        self.run_seed()
        templates = {p["pk"]: p for p in self.mock.parts(template=True)}
        for v in self.mock.parts(template=False):
            tpl = templates[v["variant_of"]]
            self.assertTrue(v["IPN"].startswith(tpl["IPN"] + "-"), v["IPN"])
            self.assertEqual(v["minimum_stock"], self.cfg["default_minimum_stock"])

    def test_company_locations_owned_by_company_group(self):
        self.run_seed()
        owners = {o["pk"]: o["name"] for o in self.mock.db["owner"]}
        tops = [l for l in self.mock.db["location"] if l["parent"] is None]
        self.assertEqual(len(tops), 3)
        for co in self.cfg["companies"]:
            loc = next(l for l in tops if l["name"] == co["name"])
            self.assertEqual(owners[loc["owner"]], co["owner_group"], "公司頂層庫位的擁有者必須是該公司群組")

    def test_seed_is_idempotent(self):
        self.run_seed()
        before = {k: len(v) for k, v in self.mock.db.items()}
        stats = self.run_seed()
        after = {k: len(v) for k, v in self.mock.db.items()}
        self.assertEqual(before, after, "重複執行不可新增任何資料")
        self.assertEqual(stats["created"], 0)

    def test_missing_owner_group_stops_before_creating_parts(self):
        self.mock.db["owner"] = [o for o in self.mock.db["owner"] if o["name"] != "company-B"]
        with self.assertRaises(SystemExit) as cm:
            self.run_seed()
        self.assertIn("company-B", str(cm.exception))
        writes = [r for r in self.mock.requests if r[0] != "GET"]
        self.assertEqual(writes, [], "群組缺少時不應寫入任何資料")

    def test_api_error_stops_with_message(self):
        self.mock.fail_on = ("POST", "/api/part/")
        with self.assertRaises(SystemExit) as cm:
            self.run_seed()
        self.assertIn("400", str(cm.exception))

    def test_wrong_token_is_reported(self):
        api = seed_skus.Api(self.api.base, "wrong")
        templates, variants = seed_skus.build_plan(self.cfg)
        with self.assertRaises(SystemExit) as cm:
            seed_skus.seed(api, self.cfg, templates, variants)
        self.assertIn("401", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
