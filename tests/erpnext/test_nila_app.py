"""nila_app（正式版客製功能）的單元測試：設定檔檢查、甲型縮寫保護、用語檔、還原程式的選檔邏輯。

寫入 ERPNext 的部分由 .github/workflows/nila-erpnext-production.yml 在真正的 ERPNext 16 上端對端測試。
"""

import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "nila-erpnext"
APP = ROOT / "apps" / "nila_app" / "nila_app"
spec = importlib.util.spec_from_file_location("nila_config", APP / "setup" / "config.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def good(**kw):
    cfg = {"company_name": "妮菈穿戴甲", "company_abbr": "NL", "hq": "總公司", "branches": ["分公司A", "分公司B"],
           "shapes": [{"name": "長梯", "abbr": "LT"}, {"name": "短梯", "abbr": "ST"}], "sizes": ["XS", "S", "M", "L"]}
    cfg.update(kw)
    return cfg


class TestConfig(unittest.TestCase):
    def test_example_config_is_valid(self):
        with open(ROOT / "production" / "nila-config.example.json", encoding="utf-8") as f:
            cfg = C.validate_config(json.load(f))
        self.assertEqual(cfg["hq"], "總公司")
        self.assertEqual([s["abbr"] for s in cfg["shapes"]], ["LT", "ST", "LO"])

    def test_defaults(self):
        cfg = C.validate_config({k: v for k, v in good().items() if k not in ("hq", "sizes")})
        self.assertEqual(cfg["hq"], "總公司")
        self.assertEqual(cfg["sizes"], ["XS", "S", "M", "L"])

    def bad(self, msg, **kw):
        with self.assertRaisesRegex(C.ConfigError, msg):
            C.validate_config(good(**kw))

    def test_errors(self):
        self.bad("company_name", company_name="")
        self.bad("company_abbr", company_abbr="nl")
        self.bad("company_abbr", company_abbr="N")
        self.bad("不可空白", branches=["分公司A", " "])
        self.bad("不可重複", branches=["總公司"])
        self.bad("不可重複", branches=[C.TRANSIT])
        self.bad("至少要有一種", shapes=[])
        self.bad("縮寫必須是", shapes=[{"name": "長梯", "abbr": "lt"}])
        self.bad("縮寫必須是", shapes=[{"name": "長梯", "abbr": "LONG"}])
        self.bad("重複", shapes=[{"name": "長梯", "abbr": "LT"}, {"name": "短梯", "abbr": "LT"}])
        self.bad("sizes", sizes=["XS", "XS"])
        self.bad("sizes", sizes=["xs"])

    def test_all_errors_reported_together(self):
        with self.assertRaises(C.ConfigError) as e:
            C.validate_config(good(company_name="", company_abbr="x", shapes=[]))
        self.assertGreaterEqual(str(e.exception).count("；"), 2)

    def test_not_object(self):
        with self.assertRaises(C.ConfigError):
            C.validate_config(["x"])

    def test_load_config(self):
        d = tempfile.mkdtemp()
        self.assertIsNone(C.load_config(d))
        Path(d, C.CONFIG_FILENAME).write_text(json.dumps(good(), ensure_ascii=False), encoding="utf-8-sig")
        self.assertEqual(C.load_config(d)["company_abbr"], "NL")
        Path(d, C.CONFIG_FILENAME).write_text("{oops", encoding="utf-8")
        with self.assertRaisesRegex(C.ConfigError, "不是正確的 JSON"):
            C.load_config(d)


class TestShapeProtection(unittest.TestCase):
    def test_new_shapes_only(self):
        new = C.check_shape_changes({"長梯": "LT"}, [{"name": "長梯", "abbr": "LT"}, {"name": "短梯", "abbr": "ST"}])
        self.assertEqual(new, [{"name": "短梯", "abbr": "ST"}])

    def test_abbr_cannot_change(self):
        with self.assertRaisesRegex(C.ConfigError, "不可改成"):
            C.check_shape_changes({"長梯": "LT"}, [{"name": "長梯", "abbr": "LG"}])

    def test_abbr_cannot_be_reused(self):
        with self.assertRaisesRegex(C.ConfigError, "已被甲型"):
            C.check_shape_changes({"長梯": "LT"}, [{"name": "長橢圓", "abbr": "LT"}])


class TestTerms(unittest.TestCase):
    def test_app_terms(self):
        terms = dict(C.read_terms(APP / "setup" / "terms.csv"))
        self.assertEqual(terms["Projected Qty"], "預計庫存")
        self.assertEqual(terms["Item"], "商品")


class TestAppFiles(unittest.TestCase):
    def test_hooks_and_version(self):
        hooks = (APP / "hooks.py").read_text(encoding="utf-8")
        self.assertIn('app_name = "nila_app"', hooks)
        self.assertIn('required_apps = ["erpnext"]', hooks)
        self.assertIn("nila_app.setup.install.after_install", hooks)
        self.assertRegex((APP / "__init__.py").read_text(encoding="utf-8"), r'__version__ = "\d+\.\d+\.\d+"')
        self.assertEqual((APP / "modules.txt").read_text(encoding="utf-8").split(), ["Nila"])

    def test_compose_references_existing_files(self):
        compose = (ROOT / "production" / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("nila_app/nila_app/setup/restore.sh", compose)
        self.assertTrue((APP / "setup" / "restore.sh").exists())
        self.assertIn("nila_app.setup.install.setup_site", compose)


@unittest.skipUnless(shutil.which("bash"), "需要 bash")
class TestRestoreScript(unittest.TestCase):
    """以假的 bench 執行 restore.sh，驗證選檔與參數（不需要 ERPNext）。"""

    def run_restore(self, files, config=None):
        root = Path(tempfile.mkdtemp())
        (root / "sites" / "restore").mkdir(parents=True)
        (root / "sites" / "nila").mkdir()
        for f in files:
            (root / "sites" / "restore" / f).write_text("x")
        if config is not None:
            (root / "sites" / "restore" / "20261013_1-nila-site_config_backup.json").write_text(json.dumps(config))
        log = root / "benchlog"
        fake = root / "bench"
        fake.write_text(f'#!/bin/bash\nprintf "[%s]" "$@" >> {log}; echo >> {log}\n')  # 每個參數各自加上中括號
        fake.chmod(0o755)
        script = (APP / "setup" / "restore.sh").read_text(encoding="utf-8")
        script = script.replace("cd /home/frappe/frappe-bench", f"cd {root}").replace("env/bin/python", "python3")
        (root / "r.sh").write_text(script)
        env = dict(os.environ, SITE_NAME="nila", DB_PASSWORD='p"w $x', PATH=f"{root}:{os.environ['PATH']}")
        p = subprocess.run(["bash", str(root / "r.sh")], capture_output=True, text=True, env=env)
        calls = log.read_text().splitlines() if log.exists() else []
        return p, calls

    def test_full_set(self):
        p, calls = self.run_restore(["20261013_1-nila-database.sql.gz", "20261013_1-nila-files.tar",
                                     "20261013_1-nila-private-files.tar"], config={"encryption_key": "abc="})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("NILA_RESTORE_OK", p.stdout)
        restore = calls[0]
        self.assertIn('[--db-root-password][p"w $x]', restore, "密碼是一個完整參數，不被 shell 拆開或解析")
        self.assertIn("[--with-public-files][sites/restore/20261013_1-nila-files.tar]", restore)
        self.assertIn("[--with-private-files][sites/restore/20261013_1-nila-private-files.tar]", restore)
        self.assertIn("[--site][nila][set-config][encryption_key][abc=]", calls)
        self.assertEqual(calls[-2:], ["[--site][nila][migrate]", "[--site][nila][clear-cache]"])

    def test_database_only(self):
        p, calls = self.run_restore(["20261013_1-nila-database.sql.gz"])
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("--with-public-files", calls[0])
        self.assertFalse(any("encryption_key" in c for c in calls))

    def test_two_sets_rejected(self):
        p, calls = self.run_restore(["20261013_1-nila-database.sql.gz", "20261014_1-nila-database.sql.gz"])
        self.assertEqual(p.returncode, 2)
        self.assertIn("有多個", p.stderr)
        self.assertEqual(calls, [])

    def test_missing_database(self):
        p, calls = self.run_restore(["20261013_1-nila-files.tar"])
        self.assertEqual(p.returncode, 2)
        self.assertIn("找不到", p.stderr)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
