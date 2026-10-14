"""門市與會員規則（retailrules.py）的單元測試。不需要 ERPNext。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "nila-erpnext" / "apps" / "nila_app"))

from nila_app import retailrules as R  # noqa: E402


class TestRoles(unittest.TestCase):
    def test_caps(self):
        self.assertTrue(R.can("store_sale", [R.STORE_STAFF]))
        self.assertFalse(R.can("store_return", [R.STORE_STAFF]), "店員不能退貨")
        self.assertFalse(R.can("price_override", [R.STORE_STAFF]), "店員不能改價")
        self.assertTrue(R.can("price_override", [R.STORE_LEAD]))
        self.assertFalse(R.can("member_merge", [R.STORE_LEAD]))
        self.assertFalse(R.can("sales_report", [R.HQ_STAFF]))
        self.assertTrue(R.can("member_merge", ["System Manager"]))
        self.assertTrue(R.can("store_return", [], user="Administrator"))
        self.assertFalse(R.can("store_sale", ["Stock User"]), "沒有妮菈層級的帳號不能用門市銷售")

    def test_store_scope(self):
        self.assertTrue(R.store_scoped([R.STORE_STAFF]))
        self.assertTrue(R.store_scoped([R.STORE_LEAD, "Sales User"]))
        self.assertFalse(R.store_scoped([R.STORE_LEAD, R.MANAGER]), "有更高層級就不限門市")
        self.assertFalse(R.store_scoped([], user="Administrator"))
        self.assertFalse(R.store_scoped([R.HQ_STAFF]))


class TestPhone(unittest.TestCase):
    def test_normalize(self):
        for raw in ["0912345678", "0912-345-678", "0912 345 678", "+886912345678", "+886 0912 345 678", "886912345678", "(09)12345678"]:
            self.assertEqual(R.normalize_phone(raw), "0912345678", raw)

    def test_invalid(self):
        for raw in ["", None, "12345", "0212345678", "091234567", "09123456789", "abc"]:
            with self.assertRaises(R.RetailError, msg=raw):
                R.normalize_phone(raw)


class TestCart(unittest.TestCase):
    def test_merge(self):
        lines = R.merge_cart([{"item": "0001-lt-xs", "qty": 1}, {"item": "0001-LT-XS", "qty": "2"},
                              {"item": "0001-LT-XS", "qty": 1, "rate": 300}, {"item": "0002-LT-S", "qty": 1.0}])
        self.assertEqual(lines, [{"item": "0001-LT-XS", "qty": 3, "rate": None}, {"item": "0001-LT-XS", "qty": 1, "rate": 300.0},
                                 {"item": "0002-LT-S", "qty": 1, "rate": None}])

    def test_errors(self):
        with self.assertRaises(R.RetailError) as e:
            R.merge_cart([{"item": "", "qty": 1}, {"item": "A", "qty": 0}, {"item": "B", "qty": 1.5}, {"item": "C", "qty": 1, "rate": -1}])
        for part in ["第 1 行沒有料號", "A：數量必須是正整數", "B：數量必須是正整數", "C：單價不可小於 0"]:
            self.assertIn(part, str(e.exception))
        with self.assertRaisesRegex(R.RetailError, "沒有商品"):
            R.merge_cart([])


class TestReturns(unittest.TestCase):
    SOLD = {"r1": {"item": "A", "qty": 2, "rate": 350, "returned": 0}, "r2": {"item": "B", "qty": 1, "rate": 300, "returned": 1}}

    def test_goods_full_and_partial_refund(self):
        out = R.plan_return(self.SOLD, R.GOODS, [{"row": "r1", "qty": 2}])
        self.assertEqual(out, [{"row": "r1", "item": "A", "qty": 2, "rate": 350.0, "amount": 700.0}])
        out = R.plan_return(self.SOLD, R.GOODS, [{"row": "r1", "qty": 1, "amount": 100}])
        self.assertEqual((out[0]["qty"], out[0]["amount"], out[0]["rate"]), (1, 100.0, 100.0), "部分退款只退 100")

    def test_refund_only(self):
        out = R.plan_return(self.SOLD, R.REFUND_ONLY, [{"row": "r1", "qty": 5, "amount": 50}])
        self.assertEqual((out[0]["qty"], out[0]["amount"]), (1, 50.0), "只退款固定處理 1 件")

    def test_limits(self):
        with self.assertRaisesRegex(R.RetailError, "最多只能再退 2 件"):
            R.plan_return(self.SOLD, R.GOODS, [{"row": "r1", "qty": 3}])
        with self.assertRaisesRegex(R.RetailError, "最多只能再退 0 件"):
            R.plan_return(self.SOLD, R.GOODS, [{"row": "r2", "qty": 1}])
        with self.assertRaisesRegex(R.RetailError, "退款金額必須在 0 到 350"):
            R.plan_return(self.SOLD, R.GOODS, [{"row": "r1", "qty": 1, "amount": 351}])
        with self.assertRaisesRegex(R.RetailError, "沒有要退的項目"):
            R.plan_return(self.SOLD, R.GOODS, [{"row": "r1", "qty": 0}])
        with self.assertRaisesRegex(R.RetailError, "退貨方式不正確"):
            R.plan_return(self.SOLD, "x", [])


class TestMemberImport(unittest.TestCase):
    def test_plan(self):
        table = [["會員名單"], ["姓名", "手機", "備註"],
                 ["王小美", "0912-345-678"], ["李大華", 912000111.0], ["", ""], ["陳一", "+886 933 222 111"],
                 ["舊會員", "0955111222"], ["改名的人", "0955333444"]]
        out = R.plan_members(table, {"0955111222": "舊會員", "0955333444": "原本的名字"})
        self.assertEqual(out["errors"], [])
        self.assertEqual([(m["row"], m["name"], m["phone"]) for m in out["new"]],
                         [(3, "王小美", "0912345678"), (4, "李大華", "0912000111"), (6, "陳一", "0933222111")])
        self.assertEqual([m["phone"] for m in out["skipped"]], ["0955111222", "0955333444"])
        self.assertEqual(len(out["warnings"]), 1)
        self.assertIn("不會改成「改名的人」", out["warnings"][0])

    def test_errors(self):
        out = R.plan_members([["姓名", "電話"], ["", "0912345678"], ["甲", "12345"], ["乙", "0912000001"], ["丙", "0912-000-001"]], {})
        self.assertEqual(len(out["errors"]), 3, out["errors"])
        self.assertIn("第 2 列：姓名空白", out["errors"][0])
        self.assertIn("第 3 列（甲）", out["errors"][1])
        self.assertIn("和第 4 列重複", out["errors"][2])

    def test_missing_header(self):
        self.assertIn("找不到標題列", R.plan_members([["名字", "號碼"]], {})["errors"][0])


if __name__ == "__main__":
    unittest.main()
