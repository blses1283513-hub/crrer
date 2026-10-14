"""SHOPLINE 官網訂單對應規則（shoplinerules.py）的單元測試。不需要 ERPNext。

訂單的欄位依 SHOPLINE Open API 文件（GET /v1/orders）。
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "nila-erpnext" / "apps" / "nila_app"))

from nila_app import shoplinerules as S  # noqa: E402


def m(v):
    return {"cents": v, "dollars": float(v), "currency_iso": "TWD", "currency_symbol": "NT$", "label": f"NT${v}"}


def item(sku, qty, price, kind="Product", total=None, discounted=None):
    it = {"id": f"i-{sku}", "item_type": kind, "sku": sku, "quantity": qty, "item_price": m(price),
          "total": m(total if total is not None else price * qty), "title_translations": {"zh-hant": f"商品{sku}"}}
    if discounted is not None:
        it["discounted_total"] = m(discounted)
    return it


def order(items, status="confirmed", pay="completed", **kw):
    o = {"id": "o1", "order_number": "20261014001", "status": status, "order_payment": {"status": pay},
         "created_by": "shop", "type": "general", "customer_name": "王小明", "total": m(800),
         "created_at": "2026-10-14T02:00:00.000+00:00", "updated_at": "2026-10-14T02:00:00.000+00:00",
         "subtotal_items": items}
    o.update(kw)
    return o


SKUS = {"0001-LT-XS", "0001-LT-S", "0002-ST-M"}


class TestLines(unittest.TestCase):
    def test_lines_merge_and_price(self):
        lines, errors = S.order_lines(order([item("0001-lt-xs", 1, 300), item("0001-LT-XS", 2, 300),
                                             item("0002-ST-M", 1, 500, discounted=450)]))
        self.assertEqual(errors, [])
        self.assertEqual(lines[0], {"sku": "0001-LT-XS", "qty": 3, "rate": 300, "title": "商品0001-lt-xs"})
        self.assertEqual(lines[1]["rate"], 450, "單價用扣掉折扣後的金額")

    def test_gift_kept_custom_skipped(self):
        lines, errors = S.order_lines(order([item("0001-LT-S", 1, 0, kind="Gift"), item("", 1, 100, kind="CustomProduct")]))
        self.assertEqual([(ln["sku"], ln["rate"]) for ln in lines], [("0001-LT-S", 0)])
        self.assertEqual(errors, [])

    def test_missing_sku(self):
        _lines, errors = S.order_lines(order([item("", 1, 100)]))
        self.assertEqual(len(errors), 1)
        self.assertIn("沒有 SKU", errors[0])

    def test_money(self):
        self.assertEqual(S.money(m(120)), 120)
        self.assertEqual(S.money({"cents": 5}), 5)
        self.assertIsNone(S.money(None))


class TestPlan(unittest.TestCase):
    def test_new_order_created(self):
        p = S.plan(order([item("0001-LT-XS", 2, 300)]), SKUS)
        self.assertEqual((p["action"], p["state"]), (S.CREATE, S.CREATED))
        self.assertEqual(p["lines"][0]["qty"], 2)

    def test_pending_and_completed_also_created(self):
        for status in ("pending", "completed"):
            self.assertEqual(S.plan(order([item("0001-LT-XS", 1, 300)], status=status, pay="pending"), SKUS)["action"], S.CREATE)

    def test_unknown_sku_goes_to_pending(self):
        p = S.plan(order([item("0001-LT-XS", 1, 300), item("9999-XX", 1, 300)]), SKUS)
        self.assertEqual((p["action"], p["state"]), (S.MARK_PENDING, S.PENDING))
        self.assertIn("9999-XX", p["message"])

    def test_temp_and_unknown_status_skipped(self):
        self.assertEqual(S.plan(order([item("0001-LT-XS", 1, 300)], status="temp"), SKUS)["action"], S.SKIP)

    def test_pos_excluded_by_default(self):
        o = order([item("0001-LT-XS", 1, 300)], created_by="pos")
        self.assertEqual(S.plan(o, SKUS)["action"], S.SKIP)
        self.assertEqual(S.plan(o, SKUS, exclude_pos=False)["action"], S.CREATE)

    def test_return_exchange_pending(self):
        p = S.plan(order([item("0001-LT-XS", 1, 300)], type="return"), SKUS)
        self.assertEqual(p["state"], S.PENDING)
        handled = S.plan(order([item("0001-LT-XS", 1, 300)], type="return"), SKUS, {"state": S.HANDLED})
        self.assertEqual(handled["action"], S.NOTHING)

    def test_cancelled_before_import_skipped(self):
        self.assertEqual(S.plan(order([item("0001-LT-XS", 1, 300)], status="cancelled"), SKUS)["action"], S.SKIP)

    def test_cancel_open_order(self):
        ex = {"state": S.CREATED, "sales_order": "SO-1", "so_docstatus": 1, "delivered": False}
        for o in (order([item("0001-LT-XS", 1, 300)], status="cancelled"),
                  order([item("0001-LT-XS", 1, 300)], status="removed"),
                  order([item("0001-LT-XS", 1, 300)], pay="refunded")):
            p = S.plan(o, SKUS, ex)
            self.assertEqual((p["action"], p["state"]), (S.CANCEL, S.CANCELLED), o["status"])

    def test_cancel_after_delivery_needs_person(self):
        ex = {"state": S.CREATED, "sales_order": "SO-1", "so_docstatus": 1, "delivered": True}
        p = S.plan(order([item("0001-LT-XS", 1, 300)], status="cancelled"), SKUS, ex)
        self.assertEqual((p["action"], p["state"]), (S.MARK_PENDING, S.PENDING))
        self.assertIn("已經出貨", p["message"])
        handled = S.plan(order([item("0001-LT-XS", 1, 300)], status="cancelled"), SKUS, dict(ex, state=S.HANDLED))
        self.assertEqual(handled["action"], S.NOTHING)

    def test_already_cancelled_nothing(self):
        ex = {"state": S.CANCELLED, "sales_order": "SO-1", "so_docstatus": 2}
        self.assertEqual(S.plan(order([item("0001-LT-XS", 1, 300)], status="cancelled"), SKUS, ex)["action"], S.NOTHING)

    def test_duplicate_not_created_again(self):
        lines, _ = S.order_lines(order([item("0001-LT-XS", 2, 300)]))
        ex = {"state": S.CREATED, "sales_order": "SO-1", "so_docstatus": 1, "fingerprint": S.fingerprint(lines)}
        p = S.plan(order([item("0001-LT-XS", 2, 300)], status="completed"), SKUS, ex)
        self.assertEqual((p["action"], p["state"]), (S.NOTHING, S.CREATED))

    def test_items_changed_after_import(self):
        lines, _ = S.order_lines(order([item("0001-LT-XS", 2, 300)]))
        ex = {"state": S.CREATED, "sales_order": "SO-1", "so_docstatus": 1, "fingerprint": S.fingerprint(lines)}
        p = S.plan(order([item("0001-LT-XS", 3, 300)]), SKUS, ex)
        self.assertEqual((p["action"], p["state"]), (S.MARK_PENDING, S.PENDING))
        # 人工處理後指紋更新成新的內容：之後同樣的內容不再提醒
        new_lines, _ = S.order_lines(order([item("0001-LT-XS", 3, 300)]))
        ex2 = dict(ex, state=S.HANDLED, fingerprint=S.fingerprint(new_lines))
        self.assertEqual(S.plan(order([item("0001-LT-XS", 3, 300)]), SKUS, ex2)["action"], S.NOTHING)

    def test_cancelled_in_erp_but_open_on_web(self):
        ex = {"state": S.CREATED, "sales_order": "SO-1", "so_docstatus": 2}
        self.assertEqual(S.plan(order([item("0001-LT-XS", 1, 300)]), SKUS, ex)["state"], S.PENDING)

    def test_pending_then_fixed(self):
        """待處理（料號錯）→ 補上商品後再處理就建立。"""
        ex = {"state": S.PENDING, "sales_order": None}
        self.assertEqual(S.plan(order([item("0003-LT-XS", 1, 300)]), SKUS | {"0003-LT-XS"}, ex)["action"], S.CREATE)

    def test_handled_pending_not_recreated(self):
        ex = {"state": S.HANDLED, "sales_order": None}
        self.assertEqual(S.plan(order([item("0001-LT-XS", 1, 300)]), SKUS, ex)["action"], S.NOTHING)


class TestHelpers(unittest.TestCase):
    def test_mask(self):
        self.assertEqual(S.mask(""), "")
        self.assertEqual(S.mask("abcdefghijkl1234"), "••••••••1234")
        self.assertNotIn("abc", S.mask("abcdefghijkl1234"))
        self.assertEqual(S.mask("short"), "••••••••")

    def test_summary(self):
        s = S.summary(order([]))
        self.assertEqual((s["shopline_id"], s["status"], s["payment_status"], s["total"]), ("o1", "confirmed", "completed", 800))


if __name__ == "__main__":
    unittest.main()
