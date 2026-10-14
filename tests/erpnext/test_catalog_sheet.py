"""商品規則（catalog.py）與試算表匯入檢查（sheet.py）的單元測試。不需要 ERPNext。"""

import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "nila-erpnext"
sys.path.insert(0, str(ROOT / "apps" / "nila_app"))

from nila_app import catalog as C  # noqa: E402
from nila_app import sheet as S  # noqa: E402

SHAPES = {"長梯": "LT", "短梯": "ST", "長橢圓": "LO"}
SIZES = ["XS", "S", "M", "L"]
WHS = ["總公司", "分公司A", "分公司B", "分公司C", "分公司D"]
HEAD = S.headers(WHS)


def row(code="", name="櫻花", shape="長梯", size="XS", status="上架", cost=80, web=390, store=350, target=10, stock=(), sku=""):
    stock = list(stock) + [""] * (len(WHS) - len(stock))
    return [sku, code, name, shape, size, status, cost, web, store, target, *stock]


def plan(rows, existing=None, head=HEAD):
    return S.plan_import([head, *rows], SHAPES, SIZES, WHS, existing or {"styles": {}, "codes": []})


def existing_style():
    return {"styles": {"0001": {"name": "櫻花", "status": "上架", "cost": 80.0, "web_price": 390.0, "store_price": 350.0,
                                "variants": {("長梯", "XS"): {"code": "0001-LT-XS", "target": 10},
                                             ("長梯", "S"): {"code": "0001-LT-S", "target": 10}}}},
            "codes": ["0001-LT-XS", "0001-LT-S"]}


class TestCatalog(unittest.TestCase):
    def test_next_code(self):
        self.assertEqual(C.next_style_code([]), "0001")
        self.assertEqual(C.next_style_code(["0001", "0009", "A12", "B"]), "0010")
        self.assertEqual(C.next_style_code(["9999"]), "10000")

    def test_clean_style_orders_cells_and_targets(self):
        s = C.clean_style({"name": " 櫻花 ", "cost": "80", "web_price": 390, "store_price": 350,
                           "cells": [{"shape": "短梯", "size": "M"}, {"shape": "長梯", "size": "S"}, {"shape": "長梯", "size": "XS"},
                                     {"shape": "長梯", "size": "XS"}],
                           "targets": {"長梯": "12"}}, list(SHAPES), SIZES)
        self.assertEqual(s["name"], "櫻花")
        self.assertEqual(s["cells"], [("長梯", "XS"), ("長梯", "S"), ("短梯", "M")])
        self.assertEqual(s["targets"], {"長梯": 12, "短梯": 0})
        self.assertEqual(s["status"], "上架")

    def test_clean_style_lists_all_errors(self):
        with self.assertRaises(C.CatalogError) as e:
            C.clean_style({"code": "00-1", "name": "", "cost": -1, "web_price": "x", "status": "下架",
                           "cells": [{"shape": "方形", "size": "XS"}], "targets": {}}, list(SHAPES), SIZES)
        msg = str(e.exception)
        for part in ["款式編號只能", "款式名稱必填", "成本不可小於 0", "官網售價必須是數字", "實體售價必填", "商品狀態必須是", "沒有這個甲型：方形", "至少要勾選"]:
            self.assertIn(part, msg)

    def test_bad_target(self):
        with self.assertRaises(C.CatalogError) as e:
            C.clean_style({"name": "a", "cost": 1, "web_price": 1, "store_price": 1,
                           "cells": [{"shape": "長梯", "size": "XS"}], "targets": {"長梯": "1.5"}}, list(SHAPES), SIZES)
        self.assertIn("補貨目標必須是 0 以上的整數", str(e.exception))

    def test_variant_name(self):
        self.assertEqual(C.variant_name("櫻花", "長梯", "XS"), "櫻花-長梯-XS")


class TestPlanImport(unittest.TestCase):
    def test_new_styles_group_by_code_or_name(self):
        r = plan([row(name="櫻花", size="XS", stock=(5, 1)), row(name="櫻花", size="S"),
                  row(name="裸紗", shape="短梯", size="M", stock=(0, 0, 3)),
                  row(code="0100", name="星空", size="L", stock=(2,))])
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["counts"], {"new_styles": 3, "updated_styles": 0, "new_variants": 4, "updated_variants": 0,
                                       "unchanged_variants": 0, "stock_entries": 4, "stock_qty": 11})
        names = [(s["code"], s["name"], len(s["variants"])) for s in r["styles"]]
        self.assertEqual(names, [("", "櫻花", 2), ("", "裸紗", 1), ("0100", "星空", 1)])
        self.assertEqual(r["styles"][0]["variants"][0]["stock"], {"總公司": 5, "分公司A": 1})

    def test_existing_style_update_and_stock_ignored(self):
        r = plan([row(code="0001", size="XS", store=380, target=12, stock=(9,)),
                  row(code="0001", size="S", store=380, target=""),
                  row(code="0001", size="M", store=380, stock=(4,))], existing_style())
        self.assertEqual(r["errors"], [])
        c = r["counts"]
        self.assertEqual((c["updated_styles"], c["new_variants"], c["updated_variants"], c["unchanged_variants"], c["stock_qty"]),
                         (1, 1, 1, 1, 4))
        s = r["styles"][0]
        self.assertTrue(s["changed"])
        self.assertEqual(s["store_price"], 380)
        xs, sm = s["variants"][0], s["variants"][1]
        self.assertEqual((xs["target"], xs["stock"]), (12, {}))
        self.assertEqual(sm["target"], 10, "空白的補貨目標保留原值")
        self.assertTrue(any("已存在的規格不會匯入庫存" in w and "0001-LT-XS" in w for w in r["warnings"]))

    def test_existing_style_blank_values_kept(self):
        r = plan([row(code="0001", name="", status="", cost="", web="", store="", size="XS", target=10)], existing_style())
        self.assertEqual(r["errors"], [])
        s = r["styles"][0]
        self.assertEqual((s["name"], s["status"], s["cost"], s["changed"]), ("櫻花", "上架", 80.0, False))
        self.assertEqual(r["counts"]["unchanged_variants"], 1)

    def test_errors(self):
        r = plan([
            row(code="0001-X"),                         # 2 編號格式
            row(code="0001-LT-XS".replace("-", "") ),   # 3 合法
            row(code="", name=""),                      # 4 兩者皆空
            row(name="A", shape="方形"),                 # 5
            row(name="A", size="XXL"),                  # 6
            row(name="B", cost=-1),                     # 7
            row(name="C", target=1.5),                  # 8
            row(name="D", stock=("x",)),                # 9
            row(name="E", status="下架"),                # 10
            row(name="F", web=""),                      # 11 新款式售價必填
            row(name="G"), row(name="G"),               # 12, 13 重複
            row(code="0200", name="H", store=300), row(code="0200", name="H", store=320, size="S"),  # 14 不一致
            row(code="0300", name="I", sku="0300-ST-XS"),  # 16 SKU 不符
        ], {"styles": {}, "codes": ["0001LTXS"]})
        e = "\n".join(r["errors"])
        for part in ["第 2 列：款式編號只能", "第 3 列：0001LTXS 已經是其他商品的料號", "第 4 列：款式編號與款式名稱至少要填一個",
                     "第 5 列：沒有這個甲型：方形", "第 6 列：沒有這個尺寸：XXL", "第 7 列：成本必須是 0 以上的數字",
                     "第 8 列：補貨目標必須是 0 以上的整數", "第 9 列：總公司的庫存必須是", "第 10 列：商品狀態必須是",
                     "第 11 列：新款式的官網售價必填", "第 13 列：款式 G 的 長梯 XS 重複", "實體售價在各列不一致",
                     "第 16 列：SKU 編碼 0300-ST-XS 與款式編號、甲型、尺寸不符"]:
            self.assertIn(part, e)

    def test_missing_columns_and_unknown(self):
        r = plan([["a"]], head=["款式名稱", "備註"])
        self.assertIn("缺少欄位：款式編號、甲型、尺寸", r["errors"][0])
        self.assertIn("備註", r["warnings"][0])

    def test_name_reused_warning(self):
        r = plan([row(name="櫻花")], existing_style())
        self.assertEqual(r["errors"], [])
        self.assertTrue(any("已存在（編號 0001）" in w for w in r["warnings"]))

    def test_excel_number_types(self):
        r = plan([row(code=1.0, name="數字款", target=12.0, stock=(3.0,), cost="1,200")])
        self.assertEqual(r["errors"], [])
        s = r["styles"][0]
        self.assertEqual((s["code"], s["cost"], s["variants"][0]["target"], s["variants"][0]["stock"]), ("1", 1200.0, 12, {"總公司": 3}))

    def test_lowercase_size_and_blank_rows(self):
        r = plan([row(name="a", size="xs"), [""] * len(HEAD), [None] * 3])
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["counts"]["new_variants"], 1)

    def test_empty(self):
        self.assertIn("試算表沒有資料", plan([])["errors"][0])

    def test_sample_sheet_is_importable(self):
        with open(ROOT / "seed" / "sample-skus.csv", encoding="utf-8-sig") as f:
            table = list(csv.reader(f))
        r = S.plan_import(table, SHAPES, SIZES, WHS, {"styles": {}, "codes": []})
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["counts"]["new_styles"], 10)
        self.assertEqual(r["counts"]["new_variants"], 72)

    def test_csv_encodings(self):
        text = "SKU 編碼,款式編號,款式名稱,甲型,尺寸\n,,櫻花,長梯,XS\n"
        for raw in [text.encode("utf-8"), "\ufeff".encode("utf-8") + text.encode("utf-8"), text.encode("cp950")]:
            table = S.parse_csv(raw)
            self.assertEqual(table[0][:3], ["SKU 編碼", "款式編號", "款式名稱"])
            self.assertEqual(table[1][2], "櫻花")
        with self.assertRaises(ValueError):
            S.parse_csv(b"\xff\xfe\x00\x81\x00")

    def test_bom_in_header_cell(self):
        r = plan([row(name="a")], head=["\ufeffSKU 編碼", *HEAD[1:]])
        self.assertEqual((r["errors"], r["warnings"]), ([], []))

    def test_export_roundtrip(self):
        ex = existing_style()
        out = S.export_rows(ex["styles"], list(SHAPES), SIZES, WHS, {"0001-LT-S": {"分公司A": 4}})
        self.assertEqual(out[0], HEAD)
        self.assertEqual([r[0] for r in out[1:]], ["0001-LT-XS", "0001-LT-S"])
        self.assertEqual(out[2][-5:], [0, 4, 0, 0, 0])
        r = S.plan_import(out, SHAPES, SIZES, WHS, ex)
        self.assertEqual(r["errors"], [])
        self.assertEqual(r["counts"]["unchanged_variants"], 2, "匯出後直接匯入不會有變更")
        self.assertEqual(r["counts"]["updated_styles"], 0)


if __name__ == "__main__":
    unittest.main()
