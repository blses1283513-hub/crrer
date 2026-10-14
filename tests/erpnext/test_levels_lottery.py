"""5 個層級（levels.py）與抽獎規則（lotteryrules.py）的單元測試。不需要 ERPNext。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "nila-erpnext" / "apps" / "nila_app"))

from nila_app import levels as L  # noqa: E402
from nila_app import lotteryrules as T  # noqa: E402


class TestLevels(unittest.TestCase):
    def test_matrix_matches_agreed_table(self):
        """和確認過的分工表一致。"""
        expect = {
            L.ADMIN: {"accounts", "cost_view", "item_manage", "replenish_manage", "lottery", "store_return"},
            L.MANAGER: {"cost_view", "item_manage", "replenish_manage", "lottery", "member_merge", "sales_report"},
            L.HQ_STAFF: {"dispatch", "transfer_create", "transfer_receive", "replenish_view", "stock_view", "store_sale"},
            L.STORE_LEAD: {"store_sale", "store_return", "price_override", "sales_report", "transfer_receive", "stock_view"},
            L.STORE_STAFF: {"store_sale", "member", "stock_view"},
        }
        deny = {
            L.MANAGER: {"accounts"},
            L.HQ_STAFF: {"cost_view", "item_manage", "replenish_manage", "accounts", "lottery", "sales_report", "store_return"},
            L.STORE_LEAD: {"cost_view", "item_manage", "replenish_view", "dispatch", "transfer_create", "member_merge", "accounts"},
            L.STORE_STAFF: {"store_return", "price_override", "sales_report", "cost_view", "replenish_view", "transfer_receive",
                            "barcode", "accounts"},
        }
        for level, caps in expect.items():
            for cap in caps:
                self.assertTrue(L.has_cap(cap, [level]), f"{level} 應該可以 {cap}")
        for level, caps in deny.items():
            for cap in caps:
                self.assertFalse(L.has_cap(cap, [level]), f"{level} 不應該可以 {cap}")
        self.assertTrue(all(L.has_cap(c, [], user="Administrator") for c in L.CAPS))

    def test_bundles(self):
        self.assertIn("System Manager", L.BUNDLES[L.ADMIN])
        self.assertNotIn("System Manager", L.BUNDLES[L.MANAGER], "營運主管不能管理帳號與系統設定")
        self.assertEqual(L.BUNDLES[L.STORE_STAFF], [], "店員只用妮菈的頁面")
        for lv in (L.HQ_STAFF, L.STORE_LEAD, L.STORE_STAFF):
            self.assertFalse(set(L.BUNDLES[lv]) & set(L.COST_ROLES), f"{lv} 不能有可看成本的角色")
        for lv in (L.ADMIN, L.MANAGER):
            self.assertIn(lv, L.COST_ROLES)

    def test_level_and_roles(self):
        self.assertEqual(L.level_of(["Stock User", L.STORE_LEAD, L.STORE_STAFF]), L.STORE_LEAD)
        self.assertIsNone(L.level_of(["Stock User"]))
        add, remove = L.plan_roles(L.STORE_STAFF, [L.STORE_LEAD, "Stock User", "Blogger"])
        self.assertEqual((add, remove), ([L.STORE_STAFF], sorted([L.STORE_LEAD, "Stock User"])), "非妮菈管理的角色保留")
        add, remove = L.plan_roles(L.HQ_STAFF, [])
        self.assertEqual(add, sorted([L.HQ_STAFF, "Stock User", "Sales User"]))

    def test_check_account(self):
        stores = {"A": "分公司A"}
        ok = {"full_name": "小美", "username": "may.a", "level": L.STORE_STAFF, "stores": ["A"]}
        self.assertEqual(L.check_account(ok, stores), [])
        errs = L.check_account({"full_name": "", "username": "1ab", "level": L.STORE_LEAD, "stores": []}, stores)
        self.assertTrue(any("姓名必填" in e for e in errs) and any("帳號必須是" in e for e in errs)
                        and any("至少要選一間門市" in e for e in errs), errs)
        self.assertTrue(any("已經有人使用" in e for e in L.check_account(ok, stores, {"may.a"})))
        self.assertTrue(any("沒有這些門市" in e for e in L.check_account(dict(ok, stores=["X"]), stores)))
        self.assertEqual(L.check_account(dict(ok, level=L.HQ_STAFF, stores=[]), stores), [], "總公司層級不用選門市")


def st(orders=1, net=0, max_single=0, styles=(), shapes=()):
    return {"orders": orders, "net": net, "max_single": max_single, "styles": set(styles), "shapes": set(shapes)}


class TestLottery(unittest.TestCase):
    def test_clean_and_errors(self):
        rules, mode, unit, cap = T.clean_rules([{"rule_type": "累計消費金額", "value": "3,000"},
                                                {"rule_type": "買過指定款式", "value": "0001，0002"}], T.PER_AMOUNT, 1000, 5)
        self.assertEqual(rules, [("net", 3000.0), ("styles", {"0001", "0002"})])
        with self.assertRaises(T.LotteryError) as e:
            T.clean_rules([{"rule_type": "身高", "value": 1}, {"rule_type": "消費次數", "value": "1.5"},
                           {"rule_type": "累計消費金額", "value": "abc"}, {"rule_type": "買過指定甲型", "value": " "}],
                          T.PER_AMOUNT, 0, -1)
        for part in ["第 1 條：條件種類不正確", "第 2 條：消費次數必須是 0 以上的整數", "第 3 條：累計消費金額要填數字",
                     "第 4 條：買過指定甲型要填甲型名稱", "要填大於 0 的數字", "名額上限不可小於 0"]:
            self.assertIn(part, str(e.exception))

    def test_and_conditions(self):
        rules, *_ = T.clean_rules([{"rule_type": "累計消費金額", "value": 3000}, {"rule_type": "消費次數", "value": 2},
                                   {"rule_type": "買過指定甲型", "value": "長梯"}], T.PER_PERSON)
        self.assertTrue(T.qualifies(st(2, 3000, shapes=["長梯", "短梯"]), rules))
        self.assertFalse(T.qualifies(st(1, 5000, shapes=["長梯"]), rules), "次數不夠")
        self.assertFalse(T.qualifies(st(3, 2999, shapes=["長梯"]), rules), "金額差 1 元")
        self.assertFalse(T.qualifies(st(3, 5000, shapes=["短梯"]), rules), "沒買過指定甲型")
        self.assertFalse(T.qualifies(st(0, 0), []), "只有退貨、沒有消費不算")
        self.assertTrue(T.qualifies(st(1, 1), []), "沒有條件＝期間內有消費")

    def test_entries(self):
        self.assertEqual(T.entries(st(net=3500), T.PER_AMOUNT, 1000), 3)
        self.assertEqual(T.entries(st(net=9900), T.PER_AMOUNT, 1000, cap=5), 5)
        self.assertEqual(T.entries(st(net=-100), T.PER_AMOUNT, 1000), 0)
        self.assertEqual(T.entries(st(orders=7), T.PER_ORDERS, 3), 2)
        self.assertEqual(T.entries(st(net=99999), T.PER_PERSON), 1)

    def test_evaluate_and_describe(self):
        rules, mode, unit, cap = T.clean_rules([{"rule_type": "單筆最高金額", "value": 1000}], T.PER_AMOUNT, 1000, 3)
        out = T.evaluate({"A": st(1, 1500, 1500), "B": st(2, 5200, 2000), "C": st(3, 900, 900), "D": st(1, 1000, 1000)},
                         rules, mode, unit, cap)
        self.assertEqual([(r["customer"], r["entries"]) for r in out], [("B", 3), ("A", 1), ("D", 1)])
        self.assertEqual(T.describe(rules, mode, unit, cap), "條件：單筆最高金額至少 1000 元。名額：每滿 1000 元 1 個名額（每人最多 3 個）。")
        self.assertEqual(T.describe([], T.PER_PERSON), "條件：期間內有消費。名額：每人 1 個名額。")


if __name__ == "__main__":
    unittest.main()
