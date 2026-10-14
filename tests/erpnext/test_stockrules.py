"""庫存規則（stockrules.py）的單元測試：狀態、補貨建議、訂單分配與調撥建議。不需要 ERPNext。"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "nila-erpnext" / "apps" / "nila_app"))

from nila_app import stockrules as R  # noqa: E402

HQ, A, B = "總公司", "分公司A", "分公司B"


def line(key, item="X", wh=HQ, qty=1, order=None):
    return {"key": key, "order": order or key, "item": item, "warehouse": wh, "qty": qty}


class TestStates(unittest.TestCase):
    def test_cell(self):
        self.assertEqual([R.cell_state(q) for q in (-1, 0, 0.0, 1, 2.0)], [R.NEGATIVE, R.OUT, R.OUT, R.OK, R.OK])

    def test_total(self):
        self.assertEqual(R.total_state(-2, 10), R.NEGATIVE)
        self.assertEqual(R.total_state(0, 10), R.OUT)
        self.assertEqual(R.total_state(9, 10), R.LOW)
        self.assertEqual(R.total_state(10, 10), R.OK)
        self.assertEqual(R.total_state(1, 0), R.OK, "沒有補貨目標就不算低庫存")

    def test_num(self):
        self.assertEqual((R.num(3.0), R.num(None), R.num(1.5)), (3, 0, 1.5))
        self.assertIsInstance(R.num(3.0), int)


class TestReplenish(unittest.TestCase):
    def test_client_example(self):
        """客戶範例：總公司 2＋分公司 1 − 訂單 5 ＝ −2，目標 10 → 補 12。"""
        projected = (2 - 5) + 1
        self.assertEqual(projected, -2)
        self.assertEqual(R.replenish_qty(10, projected, "上架"), 12)

    def test_rules(self):
        self.assertEqual(R.replenish_qty(10, 10, "上架"), 0)
        self.assertEqual(R.replenish_qty(10, 15, "上架"), 0)
        self.assertEqual(R.replenish_qty(10, 3, "停售"), 7, "停售仍列入補貨")
        self.assertEqual(R.replenish_qty(10, 3, "停產"), 0, "停產不補")
        self.assertEqual(R.replenish_qty(0, -5, "上架"), 0, "沒設目標不補")
        self.assertEqual(R.replenish_qty(None, -5, "上架"), 0)
        self.assertEqual(R.replenish_qty(10, 2.5, "上架"), 8)


class TestAllocate(unittest.TestCase):
    def test_client_example_transfer_then_purchase(self):
        """總公司 2、分公司A 1、訂單 5 從總公司出 → 現貨 2、從分公司A 調 1、還缺 2 要叫貨。"""
        res, tr = R.allocate([line("SO1", qty=5)], {("X", HQ): 2, ("X", A): 1}, sources=[HQ, A, B])
        r = res["SO1"]
        self.assertEqual((r["stock"], r["transfer"], r["short"]), (2, 1, 2))
        self.assertEqual(r["sources"], [(A, 1)])
        self.assertEqual(tr, [{"item": "X", "from": A, "to": HQ, "qty": 1, "order": "SO1"}])
        self.assertEqual(R.order_status([r]), R.NEED_PURCHASE)

    def test_first_come_first_served(self):
        res, _ = R.allocate([line("SO1", qty=2), line("SO2", qty=2)], {("X", HQ): 3}, sources=[HQ])
        self.assertEqual((res["SO1"]["stock"], res["SO1"]["short"]), (2, 0))
        self.assertEqual((res["SO2"]["stock"], res["SO2"]["short"]), (1, 1))

    def test_branch_ship_from(self):
        """分公司出貨：用分公司自己的庫存，不夠才從總公司調。"""
        res, tr = R.allocate([line("SO1", wh=A, qty=3)], {("X", A): 1, ("X", HQ): 5}, sources=[HQ, A])
        self.assertEqual((res["SO1"]["stock"], res["SO1"]["transfer"]), (1, 2))
        self.assertEqual(tr[0]["from"], HQ)
        self.assertEqual(R.order_status(res.values()), R.NEED_TRANSFER)

    def test_branch_orders_keep_their_own_stock(self):
        """分公司自己的訂單先用自己的庫存，剩下的才能調給總公司。"""
        res, tr = R.allocate([line("SO1", qty=2), line("SO2", wh=A, qty=2)], {("X", A): 3}, sources=[HQ, A])
        self.assertEqual(res["SO2"]["stock"], 2)
        self.assertEqual((res["SO1"]["transfer"], res["SO1"]["short"]), (1, 1))

    def test_largest_source_first(self):
        res, tr = R.allocate([line("SO1", qty=4)], {("X", A): 1, ("X", B): 3}, sources=[HQ, A, B])
        self.assertEqual(res["SO1"]["sources"], [(B, 3), (A, 1)])

    def test_transit_counts_before_transfer(self):
        res, tr = R.allocate([line("SO1", qty=2)], {("X", A): 5}, transit={("X", HQ): 2}, sources=[HQ, A])
        self.assertEqual((res["SO1"]["transit"], res["SO1"]["transfer"]), (2, 0))
        self.assertEqual(tr, [])
        self.assertEqual(R.order_status(res.values()), R.NEED_TRANSFER)

    def test_incoming_purchase(self):
        res, _ = R.allocate([line("SO1", qty=3)], {("X", HQ): 1}, incoming={("X", HQ): 5}, sources=[HQ])
        self.assertEqual((res["SO1"]["stock"], res["SO1"]["ordered"], res["SO1"]["short"]), (1, 2, 0))
        self.assertEqual(R.order_status(res.values()), R.ORDERED)

    def test_incoming_at_other_warehouse(self):
        res, _ = R.allocate([line("SO1", wh=A, qty=1)], {}, incoming={("X", HQ): 5}, sources=[HQ, A])
        self.assertEqual((res["SO1"]["ordered"], res["SO1"]["short"]), (1, 0))

    def test_negative_stock_is_zero_available(self):
        res, tr = R.allocate([line("SO1", qty=1)], {("X", HQ): -3, ("X", A): -1}, sources=[HQ, A])
        self.assertEqual((res["SO1"]["stock"], res["SO1"]["short"]), (0, 1))
        self.assertEqual(tr, [])

    def test_ready_and_delivered(self):
        res, _ = R.allocate([line("SO1", qty=1), line("L2", order="SO1", item="Y", qty=2)],
                            {("X", HQ): 1, ("Y", HQ): 2}, sources=[HQ])
        self.assertEqual(R.order_status(res.values()), R.READY)
        self.assertEqual(R.order_status([], fully_delivered=True), R.DELIVERED)

    def test_group_transfers(self):
        _, tr = R.allocate([line("SO1", qty=2), line("SO2", qty=1)], {("X", A): 5}, sources=[HQ, A])
        self.assertEqual(R.group_transfers(tr), [{"from": A, "to": HQ, "item": "X", "qty": 3, "orders": ["SO1", "SO2"]}])


if __name__ == "__main__":
    unittest.main()
