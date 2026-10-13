"""妮菈 ERPNext 試用版：範例試算表讀取與補貨計算的單元測試（不需要 ERPNext）。

寫入 ERPNext 的部分由 .github/workflows/nila-erpnext-trial.yml 在真正的 ERPNext 16 上端對端測試。
"""

import csv
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

SEED = Path(__file__).resolve().parents[2] / "nila-erpnext" / "seed"
spec = importlib.util.spec_from_file_location("seed_trial", SEED / "seed_trial.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

HEADER = M.FIXED_COLUMNS + ["總公司", "分公司A"]


def write_csv(rows, header=HEADER):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return path


def row(sku="", code="0001", name="裸紗", shape="長梯", size="XS", status="上架", cost="180", web="590", store="650", target="10", hq="2", a="1"):
    return [sku, code, name, shape, size, status, cost, web, store, target, hq, a]


SHAPES = {"長梯": "LT", "短梯": "ST"}


class TestSampleFiles(unittest.TestCase):
    def test_sample_sheet_parses(self):
        shapes = M.read_shapes(SEED / "shapes.csv")
        self.assertEqual(shapes, {"長梯": "LT", "短梯": "ST", "長橢圓": "LO"})
        companies, styles, skus = M.read_sheet(SEED / "sample-skus.csv", shapes)
        self.assertEqual(companies, ["總公司", "分公司A", "分公司B", "分公司C", "分公司D"])
        self.assertEqual(len(styles), 10)
        self.assertEqual(len(skus), 72)
        scenario = next(s for s in skus if s["sku"] == M.SCENARIO_SKU)
        self.assertEqual(dict(scenario["stock"]), {"總公司": 2, "分公司A": 1, "分公司B": 0, "分公司C": 0, "分公司D": 0})
        self.assertEqual(scenario["target"], 10)
        self.assertEqual({s["status"] for s in styles.values()}, {"上架", "停售", "停產"})

    def test_terms_file(self):
        with open(SEED / "terms.csv", encoding="utf-8-sig") as f:
            terms = {r["英文原文"]: r["繁體中文"] for r in csv.DictReader(f)}
        self.assertEqual(terms["Projected Qty"], "預計庫存")
        self.assertEqual(terms["Item"], "商品")


class TestSkuCode(unittest.TestCase):
    def test_rule_matches_erpnext_variant_code(self):
        # ERPNext make_variant_item_code：範本編號 + "-" + 各屬性縮寫（依屬性順序）
        self.assertEqual(M.sku_code("0001", "LT", "XS"), "0001-LT-XS")

    def test_given_code_must_match_rule(self):
        with self.assertRaisesRegex(M.SheetError, "與規則產生的"):
            M.read_sheet(write_csv([row(sku="A001-AL-XS")]), SHAPES)

    def test_blank_code_is_generated(self):
        _, _, skus = M.read_sheet(write_csv([row(), row(shape="短梯", size="L")]), SHAPES)
        self.assertEqual([s["sku"] for s in skus], ["0001-LT-XS", "0001-ST-L"])


class TestSheetValidation(unittest.TestCase):
    def bad(self, rows, msg, header=HEADER):
        with self.assertRaisesRegex(M.SheetError, msg):
            M.read_sheet(write_csv(rows, header), SHAPES)

    def test_header_order(self):
        self.bad([row()], "前幾欄必須依序", header=["款式編號"] + HEADER[1:])

    def test_hq_first(self):
        self.bad([row()], "第一欄必須是「總公司」", header=M.FIXED_COLUMNS + ["分公司A", "總公司"])

    def test_duplicate_company(self):
        self.bad([row()], "不可空白或重複", header=M.FIXED_COLUMNS + ["總公司", "總公司"])

    def test_unknown_shape_size_status(self):
        self.bad([row(shape="方型")], "不在甲型清單")
        self.bad([row(size="XL")], "XS/S/M/L")
        self.bad([row(status="下架")], "上架/停售/停產")

    def test_style_level_fields_must_agree(self):
        self.bad([row(), row(size="S", web="600")], "web_price")
        self.bad([row(), row(size="S", status="停售")], "status")

    def test_duplicate_sku(self):
        self.bad([row(), row()], "重複")

    def test_numbers(self):
        self.bad([row(hq="-1")], "不能是負數")
        self.bad([row(hq="1.5")], "整數")
        self.bad([row(target="abc")], "不是數字")

    def test_style_code_ascii(self):
        self.bad([row(code="零一")], "只能是英文字母或數字")

    def test_empty(self):
        self.bad([], "沒有任何規格")

    def test_blank_stock_is_zero_and_blank_rows_skipped(self):
        _, _, skus = M.read_sheet(write_csv([row(hq="", a=""), [""] * len(HEADER)]), SHAPES)
        self.assertEqual(len(skus), 1)
        self.assertEqual(dict(skus[0]["stock"]), {"總公司": 0, "分公司A": 0})


class TestShapes(unittest.TestCase):
    def write(self, rows):
        return write_csv(rows, header=["甲型", "縮寫"])

    def test_abbr_rules(self):
        for bad in ("lt", "L", "LONG", "L1", "長"):
            with self.assertRaises(M.SheetError, msg=bad):
                M.read_shapes(self.write([["長梯", bad]]))

    def test_duplicates(self):
        with self.assertRaisesRegex(M.SheetError, "重複"):
            M.read_shapes(self.write([["長梯", "LT"], ["短梯", "LT"]]))


class TestReorder(unittest.TestCase):
    def test_client_example(self):
        # 客戶 Q1：總公司 2、分公司 1、訂單 5 → 總公司預計 −3、分公司 +1 → 全公司 −2 → 目標 10 補 12
        self.assertEqual(M.reorder_suggestion(10, {"總公司": -3, "分公司A": 1}), (-2, 12))

    def test_no_negative_suggestion(self):
        self.assertEqual(M.reorder_suggestion(10, {"總公司": 15}), (15, 0))

    def test_transit_counts(self):
        self.assertEqual(M.reorder_suggestion(10, {"總公司": -3, "在途": 1}), (-2, 12))


if __name__ == "__main__":
    unittest.main()
