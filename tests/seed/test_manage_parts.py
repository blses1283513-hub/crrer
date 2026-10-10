"""零件整理腳本 manage_parts.py 的自動測試（模擬 InvenTree 1.5.6 的刪除規則），
以及它與匯入腳本 seed_skus.py 的相容性（已刪除的零件不會被建回來）。

執行：python -m unittest discover -s tests/seed -v
"""

import contextlib
import csv
import http.server
import importlib.util
import io
import json
import os
import re
import tempfile
import threading
import unittest
import urllib.parse
from argparse import Namespace
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SEED_DIR = os.path.join(ROOT, "inventree-seed")
TOKEN = "admin-token"


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SEED_DIR, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


manage = load("manage_parts")
seed = load("seed_skus")


class MockParts:
    """依 InvenTree 1.5.6 的規則：啟用中的零件不能刪；刪除零件會連帶刪掉它的庫存與異動紀錄；
    刪除範本時變體的 variant_of 變成空白。"""

    def __init__(self):
        self.parts, self.tracking = {}, []
        self.so_lines, self.supplier_parts, self.po_lines = [], [], []
        self.requests, self.next = [], 100
        self.hide_order_endpoints = False
        self.forbid = False
        self.delete_error = None

    def part(self, ipn, active=True, stock=0, template=False, variant_of=None, **extra):
        self.next += 1
        p = {"pk": self.next, "IPN": ipn, "name": ipn, "full_name": ipn, "active": active, "is_template": template,
             "variant_of": variant_of, "locked": False, "total_in_stock": stock, "in_stock": stock, "ordering": 0,
             "building": 0, "allocated_to_sales_orders": 0, "allocated_to_build_orders": 0}
        p.update(extra)
        self.parts[p["pk"]] = p
        return p

    def track(self, part, user="a-wh", ttype=12):
        self.next += 1
        self.tracking.append({"pk": self.next, "part": part["pk"], "date": "2026-10-10T10:00:00Z", "label": "Stock manually removed",
                              "deltas": {"removed": 5}, "notes": "測試", "user_detail": {"username": user}, "tracking_type": ttype})

    def writes(self):
        return [r for r in self.requests if r[0] in ("PATCH", "DELETE", "POST")]

    def handle(self, method, path, query, body, headers):
        self.requests.append((method, path))
        if headers.get("Authorization") != f"Token {TOKEN}" or self.forbid and method != "GET":
            return 403, {"detail": "You do not have permission to perform this action."}
        page = lambda rows: {"count": len(rows), "next": None, "results": rows}
        if path == "/api/part/" and method == "GET":
            rows = list(self.parts.values())
            if query.get("active") == "true":
                rows = [p for p in rows if p["active"]]
            if query.get("active") == "false":
                rows = [p for p in rows if not p["active"]]
            return 200, page(rows)
        m = re.fullmatch(r"/api/part/(\d+)/", path)
        if m:
            pk = int(m.group(1))
            if pk not in self.parts:
                return 404, {}
            if method == "PATCH":
                self.parts[pk].update(body)
                return 200, self.parts[pk]
            if method == "DELETE":
                if self.delete_error:
                    return 400, {"detail": self.delete_error}
                if self.parts[pk]["active"]:
                    return 400, {"non_field_errors": ["Cannot delete this part as it is still active"]}
                for p in self.parts.values():
                    if p["variant_of"] == pk:
                        p["variant_of"] = None
                self.tracking = [t for t in self.tracking if t["part"] != pk]
                del self.parts[pk]
                return 204, None
        if path == "/api/stock/track/":
            part = query.get("part")
            return 200, page([t for t in self.tracking if not part or str(t["part"]) == part])
        if self.hide_order_endpoints and (path.startswith("/api/order/") or path == "/api/company/part/"):
            return 404, {}
        if path == "/api/company/part/":
            return 200, page([sp for sp in self.supplier_parts if str(sp["part"]) == query.get("part")])
        if path == "/api/order/so-line/":
            return 200, page([x for x in self.so_lines if str(x["part"]) == query.get("part")])
        if path == "/api/order/po-line/":
            return 200, page([x for x in self.po_lines if str(x["part"]) == query.get("part")])
        return 404, {"detail": "not mocked " + path}


class Handler(http.server.BaseHTTPRequestHandler):
    mock = None

    def log_message(self, *a):
        pass

    def _do(self):
        u = urllib.parse.urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length)) if length else None
        code, data = self.mock.handle(self.command, u.path, dict(urllib.parse.parse_qsl(u.query)), body, self.headers)
        raw = b"" if data is None else json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    do_GET = do_PATCH = do_DELETE = do_POST = _do


class Base(unittest.TestCase):
    def setUp(self):
        self.m = MockParts()
        Handler.mock = self.m
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.env = mock.patch.dict(os.environ, {"INVENTREE_URL": f"http://127.0.0.1:{self.server.server_address[1]}", "INVENTREE_TOKEN": TOKEN})
        self.env.start()
        self.tmp = tempfile.TemporaryDirectory()
        self.removed = os.path.join(self.tmp.name, "removed_parts.json")

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def run_cmd(self, fn, answers=(), **kw):
        opts = dict(ipn=None, glob=None, file=None, status="all", dry_run=False, yes=False, ignore_warnings=False,
                    export_dir=self.tmp.name, removed_file=self.removed)
        opts.update(kw)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch("builtins.input", side_effect=list(answers) + ["" ] * 5):
            fn(Namespace(**opts))
        return out.getvalue()

    def ipns(self):
        return sorted(p["IPN"] for p in self.m.parts.values())


class ListAndSelectTests(Base):
    def setUp(self):
        super().setUp()
        self.a = self.m.part("A-P03-S5-XL", active=False)
        self.b = self.m.part("A-P03-S1-XL")
        self.c = self.m.part("B-P01-S1-XL")

    def test_list_shows_state_and_filters(self):
        out = self.run_cmd(manage.cmd_list, glob=["A-P03-*"])
        self.assertIn("A-P03-S5-XL", out)
        self.assertIn("已停用", out)
        self.assertNotIn("B-P01", out)
        self.assertEqual(self.m.writes(), [], "list 是唯讀")
        out = self.run_cmd(manage.cmd_list, status="inactive")
        self.assertIn("A-P03-S5-XL", out)
        self.assertNotIn("A-P03-S1-XL", out)

    def test_destructive_commands_require_a_selector(self):
        for fn in (manage.cmd_retire, manage.cmd_restore, manage.cmd_delete):
            with self.assertRaises(SystemExit) as cm:
                self.run_cmd(fn)
            self.assertIn("不提供", str(cm.exception))
        self.assertEqual(self.m.writes(), [])

    def test_selectors_ipn_glob_and_file(self):
        path = os.path.join(self.tmp.name, "list.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# 要處理的零件\nB-P01-*\n\n")
        picked = manage.select_parts(manage.Api(os.environ["INVENTREE_URL"], TOKEN),
                                     manage.read_patterns(Namespace(ipn=["A-P03-S5-XL"], glob=["A-P03-S1-*"], file=path)))
        self.assertEqual([p["IPN"] for p in picked], ["A-P03-S1-XL", "A-P03-S5-XL", "B-P01-S1-XL"])

    def test_glob_is_case_sensitive_and_exact_not_substring(self):
        picked = manage.select_parts(manage.Api(os.environ["INVENTREE_URL"], TOKEN), ["a-p03-*", "A-P03"])
        self.assertEqual(picked, [], "不可用部分比對誤選到零件")


class RetireRestoreTests(Base):
    def setUp(self):
        super().setUp()
        self.p1 = self.m.part("A-P03-S5-XL")
        self.p2 = self.m.part("A-P03-S5-L")
        self.p3 = self.m.part("A-P01-S1-XL")

    def test_retire_only_touches_selected_active_parts_and_keeps_data(self):
        self.m.track(self.p1)
        self.run_cmd(manage.cmd_retire, glob=["A-P03-S5-*"], answers=["y"])
        self.assertFalse(self.m.parts[self.p1["pk"]]["active"])
        self.assertTrue(self.m.parts[self.p3["pk"]]["active"])
        self.assertEqual(len(self.m.tracking), 1, "停用不會動到異動紀錄")
        self.assertEqual(len(self.m.writes()), 2)

    def test_retire_is_idempotent_and_restore_reverses(self):
        self.run_cmd(manage.cmd_retire, glob=["A-P03-S5-*"], yes=True)
        before = len(self.m.writes())
        out = self.run_cmd(manage.cmd_retire, glob=["A-P03-S5-*"], yes=True)
        self.assertIn("沒有符合", out)
        self.assertEqual(len(self.m.writes()), before)
        self.run_cmd(manage.cmd_restore, glob=["A-P03-S5-*"], yes=True)
        self.assertTrue(all(self.m.parts[p["pk"]]["active"] for p in (self.p1, self.p2)))

    def test_dry_run_and_cancel_write_nothing(self):
        self.run_cmd(manage.cmd_retire, glob=["A-P03-*"], dry_run=True)
        self.run_cmd(manage.cmd_retire, glob=["A-P03-*"], answers=["n"])
        self.assertEqual(self.m.writes(), [])


class DeleteSafetyTests(Base):
    def setUp(self):
        super().setUp()
        self.old = self.m.part("A-P03-S5-XL", active=False)
        self.m.track(self.old)

    def delete(self, answers=("1", "y"), **kw):
        return self.run_cmd(manage.cmd_delete, answers=answers, ipn=kw.pop("ipn", ["A-P03-S5-XL"]), **kw)

    def test_happy_path_exports_history_deletes_and_records_removal(self):
        out = self.delete()
        self.assertEqual(self.ipns(), [])
        self.assertIn("已刪除 1 個零件", out)
        folders = [d for d in os.listdir(self.tmp.name) if d.startswith("deleted-parts-")]
        self.assertEqual(len(folders), 1)
        with open(os.path.join(self.tmp.name, folders[0], "stock-history.csv"), encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[1][1:4], ["a-wh", "A-P03-S5-XL", "Stock manually removed"], "刪除前要先留下異動紀錄")
        with open(os.path.join(self.tmp.name, folders[0], "parts.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)[0]["IPN"], "A-P03-S5-XL")
        with open(self.removed, encoding="utf-8") as f:
            self.assertEqual([r["ipn"] for r in json.load(f)["removed"]], ["A-P03-S5-XL"])

    def test_active_part_is_never_deleted_by_the_tool(self):
        self.m.parts[self.old["pk"]]["active"] = True
        out = self.delete()
        self.assertIn("仍在啟用中", out)
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])
        self.assertEqual([r for r in self.m.requests if r[0] == "DELETE"], [], "不可只靠伺服器擋，工具自己要先擋")

    def test_part_with_stock_is_refused(self):
        self.m.parts[self.old["pk"]]["total_in_stock"] = 12
        out = self.delete()
        self.assertIn("還有庫存 12", out)
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])

    def test_order_lines_block_deletion(self):
        self.m.so_lines.append({"part": self.old["pk"]})
        self.assertIn("銷售單明細", self.delete())
        self.m.so_lines.clear()
        self.m.supplier_parts.append({"pk": 900, "part": self.old["pk"]})
        self.m.po_lines.append({"part": 900})
        self.assertIn("採購單明細", self.delete())
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])

    def test_open_orders_and_allocations_block_deletion(self):
        self.m.parts[self.old["pk"]]["ordering"] = 40
        self.assertIn("採購中", self.delete())
        self.m.parts[self.old["pk"]].update(ordering=0, allocated_to_sales_orders=3)
        self.assertIn("已分配給銷售單", self.delete())
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])

    def test_cannot_confirm_orders_means_stop_unless_explicitly_ignored(self):
        self.m.hide_order_endpoints = True
        with self.assertRaises(SystemExit) as cm:
            self.delete()
        self.assertIn("無法確認", str(cm.exception))
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])
        self.delete(ignore_warnings=True)
        self.assertEqual(self.ipns(), [])

    def test_template_with_outside_variants_is_refused(self):
        tpl = self.m.part("A-P03", active=False, template=True)
        self.m.part("A-P03-S1-XL", variant_of=tpl["pk"])
        out = self.delete(ipn=["A-P03"])
        self.assertIn("底下還有 1 個變體", out)
        self.assertIn("A-P03", self.ipns())

    def test_template_and_its_variants_together_delete_variants_first(self):
        tpl = self.m.part("A-P04", active=False, template=True)
        self.m.part("A-P04-S1-XL", active=False, variant_of=tpl["pk"])
        self.m.part("A-P04-S2-XL", active=False, variant_of=tpl["pk"])
        self.delete(glob=["A-P04*"], ipn=[], answers=("3", "y"))
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])
        order = [r[1] for r in self.m.requests if r[0] == "DELETE"]
        self.assertEqual(order[-1], f"/api/part/{tpl['pk']}/", "範本最後才刪")

    def test_wrong_confirmation_number_or_no_backup_deletes_nothing(self):
        self.delete(answers=("2", "y"))
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])
        self.delete(answers=("1", "n"))
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])
        self.assertEqual([d for d in os.listdir(self.tmp.name) if d.startswith("deleted-parts-")], [], "取消時也不留下匯出資料夾")
        self.assertFalse(os.path.exists(self.removed))

    def test_dry_run_reports_but_changes_nothing(self):
        out = self.delete(dry_run=True)
        self.assertIn("可刪除 1", out)
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])
        self.assertEqual(self.m.writes(), [])

    def test_only_selected_parts_are_deleted(self):
        keep = self.m.part("A-P03-S5-L", active=False)
        self.m.track(keep)
        self.delete()
        self.assertEqual(self.ipns(), ["A-P03-S5-L"])
        self.assertEqual(len(self.m.tracking), 1)

    def test_server_refusal_is_reported_not_swallowed(self):
        self.m.delete_error = "Cannot delete this part as it is locked"
        with self.assertRaises(SystemExit) as cm:
            self.delete()
        self.assertIn("locked", str(cm.exception))
        self.assertFalse(os.path.exists(self.removed), "沒刪成功就不可記錄為已刪除")

    def test_non_superuser_gets_a_clear_hint(self):
        self.m.forbid = True
        with self.assertRaises(SystemExit) as cm:
            self.delete()
        self.assertIn("superuser", str(cm.exception))
        self.assertEqual(self.ipns(), ["A-P03-S5-XL"])


class SeedCompatibilityTests(unittest.TestCase):
    CFG = os.path.join(SEED_DIR, "config.example.json")

    def plan(self, removed=()):
        return seed.build_plan(seed.load_config(self.CFG), removed)

    def test_removed_skus_are_not_recreated(self):
        templates, variants = self.plan(["A-P03-S5-*"])
        ipns = {v["ipn"] for v in variants}
        self.assertEqual(len(variants), 450 - 3)
        self.assertNotIn("A-P03-S5-XL", ipns)
        self.assertIn("A-P03-S4-XL", ipns)
        self.assertEqual(len(templates), 30)

    def test_removed_product_drops_template_and_all_its_variants(self):
        templates, variants = self.plan(["A-P03"])
        self.assertEqual(len(templates), 29)
        self.assertEqual(len(variants), 450 - 15)
        self.assertFalse(any(v["template_ipn"] == "A-P03" for v in variants))

    def test_template_without_remaining_variants_is_dropped(self):
        templates, _ = self.plan([f"A-P03-S{i}-*" for i in range(1, 6)])
        self.assertNotIn("A-P03", {t["ipn"] for t in templates})

    def test_nothing_removed_by_default_and_missing_file_is_fine(self):
        self.assertEqual(len(self.plan()[1]), 450)
        self.assertEqual(seed.load_removed("/nonexistent/removed_parts.json"), [])

    def test_round_trip_manage_delete_then_seed_skips(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "removed_parts.json")
            manage.record_removed(path, ["A-P03-S5-XL", "A-P03-S5-L"])
            manage.record_removed(path, ["A-P03-S5-XL"])      # 重複記錄不會重複
            removed = seed.load_removed(path)
            self.assertEqual(sorted(removed), ["A-P03-S5-L", "A-P03-S5-XL"])
            _, variants = self.plan(removed)
            self.assertEqual(len(variants), 448)

    def test_corrupt_removed_file_stops_instead_of_recreating_everything(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "removed_parts.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{壞掉")
            with self.assertRaises(SystemExit):
                seed.load_removed(path)


class PolicyTests(unittest.TestCase):
    def test_only_superuser_can_delete_parts_by_design(self):
        """與職務設定一致：roles.json 中沒有任何群組有 delete，刪除零件只有 superuser 做得到。"""
        with open(os.path.join(SEED_DIR, "roles.json"), encoding="utf-8") as f:
            roles = json.load(f)
        for perms in [roles["company_group_permissions"], *[t["permissions"] for t in roles["tiers"]]]:
            for r, acts in perms.items():
                self.assertNotIn("delete", acts, r)


if __name__ == "__main__":
    unittest.main()
