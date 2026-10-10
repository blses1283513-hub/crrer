"""通知服務 notifier.py 的自動測試：以模擬的 InvenTree（依 1.5.6 原始碼的異動紀錄格式）驗證。

執行：python -m unittest discover -s tests/notifier -v
"""

import importlib.util
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from inventree_sim import InvenTreeSim, serve  # noqa: E402

spec = importlib.util.spec_from_file_location("notifier", os.path.join(ROOT, "inventree-app", "notifier", "notifier.py"))
notifier_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notifier_mod)

with open(os.path.join(ROOT, "inventree-app", "notifier", "config.example.json"), encoding="utf-8") as _f:
    EXAMPLE_CONFIG = json.load(_f)


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


class Base(unittest.TestCase):
    config_override = {}

    def setUp(self):
        self.sim = InvenTreeSim()
        self.server, self.url = serve(self.sim)
        self.tmp = tempfile.TemporaryDirectory()
        self.state_path = os.path.join(self.tmp.name, "state.json")
        self.clock = FakeClock()
        self.n = self.make_notifier()

        s = self.sim
        self.locA, self.locA2 = s.add_location("A 公司/主倉"), s.add_location("A 公司/備貨區")
        self.locB, self.locC = s.add_location("B 公司/主倉"), s.add_location("C 公司/主倉")
        self.locX = s.add_location("外部倉/架1")
        self.partA = s.add_part("A-P01-S1-XL", minimum_stock=50)
        self.partB = s.add_part("B-P01-S1-XL", minimum_stock=50)
        # 一般庫存 80 件（< 大量門檻 100）；另備『大量用』的庫存放在不同零件，避免影響低庫存判斷
        self.itemA = s.add_item(self.partA, self.locA, 80)
        self.itemB = s.add_item(self.partB, self.locB, 80)
        self.bigA = s.add_item(s.add_part("A-P02"), self.locA, 1000)
        self.bigB = s.add_item(s.add_part("B-P02"), self.locB, 1000)
        for name, groups, sup in [("a-wh", ["company-A", "role-warehouse"], False), ("a-wh2", ["company-A"], False),
                                  ("b-wh", ["company-B"], False), ("b-wh2", ["company-B"], False), ("c-wh", ["company-C"], False),
                                  ("root", [], True), ("loner", [], False)]:
            s.add_user(name, groups, sup)
        self.init()

    def make_notifier(self):
        cfg = {**EXAMPLE_CONFIG, "min_process_interval_s": 0, "low_stock_cache_s": 0, **self.config_override}
        client = notifier_mod.InvenTreeClient(self.url)
        return notifier_mod.Notifier(cfg, client, notifier_mod.StateStore(self.state_path), clock=self.clock)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def auth(self, user):
        return {"cookie": self.sim.cookie(user), "authorization": "", "host": "localhost"}

    def init(self):
        self.n.feed(self.auth("a-wh"))

    def feed(self, user):
        self.clock.advance(1)
        return self.n.feed(self.auth(user))

    def events(self, user):
        return [i for i in self.feed(user)["items"] if i["kind"] != "low_stock"]

    def lows(self, user):
        return [i for i in self.feed(user)["items"] if i["kind"] == "low_stock"]


class RoutingTests(Base):
    def test_history_before_first_start_does_not_notify(self):
        sim = InvenTreeSim()
        server, url = serve(sim)
        try:
            la, lb = sim.add_location("A 公司/主倉"), sim.add_location("B 公司/主倉")
            part = sim.add_part("A-P09", minimum_stock=0)
            item = sim.add_item(part, la, 10)
            sim.add_user("a-wh", ["company-A"])
            sim.add_user("b-wh", ["company-B"])
            sim.move("a-wh", item, lb)          # 啟動前就發生的事
            n = notifier_mod.Notifier({**EXAMPLE_CONFIG, "min_process_interval_s": 0}, notifier_mod.InvenTreeClient(url),
                                      notifier_mod.StateStore(os.path.join(self.tmp.name, "other.json")), clock=self.clock)
            self.assertEqual(n.feed({"cookie": sim.cookie("b-wh"), "host": "localhost"})["items"], [])
        finally:
            server.shutdown()

    def test_other_company_moving_into_my_company_notifies_only_that_company(self):
        self.sim.move("a-wh", self.itemA, self.locB)
        ev = self.events("b-wh")
        self.assertEqual(len(ev), 1)
        self.assertEqual(ev[0]["kind"], "transfer_in")
        self.assertIn("調進 B 公司", ev[0]["title"])
        self.assertIn("A 公司 的 a-wh", ev[0]["title"])
        self.assertEqual(self.events("a-wh2"), [], "操作人的公司不通知（自己人調的）")
        self.assertEqual(self.events("a-wh"), [], "操作人自己不通知")
        self.assertEqual(self.events("c-wh"), [], "無關的公司不通知")

    def test_other_company_moving_out_of_my_company_notifies_me(self):
        self.sim.move("b-wh", self.itemA, self.locB)   # B 的人把 A 庫位裡的庫存搬走
        ev = self.events("a-wh2")
        self.assertEqual([e["kind"] for e in ev], ["transfer_out"])
        self.assertIn("從 A 公司 調出", ev[0]["title"])
        self.assertEqual(self.events("b-wh"), [])

    def test_colleagues_of_the_actor_are_not_told_about_their_own_companys_moves(self):
        self.sim.move("b-wh", self.itemA, self.locB)       # B 公司的人自己把 A 的庫存調進 B：B 同事不必被通知
        self.assertEqual(self.events("b-wh2"), [], "調進方就是操作人的公司，不通知")
        self.assertEqual([e["kind"] for e in self.events("a-wh2")], ["transfer_out"], "被調出的 A 公司要知道")
        self.sim.move("a-wh", self.itemB, self.locA)       # A 公司的人把 B 的庫存調到 A
        self.assertEqual([e["kind"] for e in self.events("a-wh2")][:1], ["transfer_out"], "A 同事只看到先前那筆調出，不會多出自己人的調進")
        self.assertEqual(len([e for e in self.events("a-wh2")]), 1)
        self.assertEqual([e["kind"] for e in self.events("b-wh2")], ["transfer_out"], "B 的庫存被 A 的人調出，B 同事要知道")

    def test_superuser_move_notifies_both_sides_and_is_labelled(self):
        self.sim.move("root", self.itemA, self.locB)
        a, b = self.events("a-wh"), self.events("b-wh")
        self.assertEqual([e["kind"] for e in a], ["transfer_out"])
        self.assertEqual([e["kind"] for e in b], ["transfer_in"])
        self.assertIn("無公司歸屬，可能是管理員", a[0]["title"])
        self.assertEqual(self.events("c-wh"), [])
        self.assertEqual(self.events("root"), [], "自己的操作不通知自己")

    def test_account_without_company_group_is_flagged_not_trusted(self):
        self.sim.move("loner", self.itemA, self.locB)
        self.assertEqual([e["kind"] for e in self.events("a-wh")], ["transfer_out"])

    def test_move_within_company_makes_no_event(self):
        self.sim.move("a-wh", self.itemA, self.locA2)
        for u in ("a-wh2", "b-wh", "root"):
            self.assertEqual(self.events(u), [], u)

    def test_partial_move_makes_one_event_per_side_with_source_from_parent(self):
        self.sim.split_move("root", self.itemA, 30, self.locB)
        a, b = self.events("a-wh"), self.events("b-wh")
        self.assertEqual(len(self.n.store.state["events"]), 1, "42 號（父項扣除）不可重複產生事件")
        self.assertEqual([e["kind"] for e in a], ["transfer_out"])
        self.assertEqual([e["kind"] for e in b], ["transfer_in"])
        self.assertIn("30 件", b[0]["title"])
        self.assertIn("A 公司/主倉 → B 公司/主倉", b[0]["detail"])

    def test_item_created_after_start_has_known_source_when_moved(self):
        new_item = self.sim.create("a-wh", self.partA, self.locA, 40)
        self.feed("a-wh2")                            # 服務已看到建立紀錄
        self.sim.move("b-wh", new_item, self.locB)
        self.assertEqual([e["kind"] for e in self.events("a-wh2")], ["transfer_out"])

    def test_created_then_moved_before_processing_does_not_guess_a_wrong_source(self):
        """已知限制：建立與搬移都發生在服務處理之前，來源無從得知；只通知收件那一方，且不可誤判。"""
        new_item = self.sim.create("a-wh", self.partA, self.locA, 40)
        self.sim.move("b-wh", new_item, self.locB)
        self.assertEqual(self.events("a-wh2"), [])
        self.assertEqual(self.events("c-wh"), [])

    def test_move_to_outside_location_still_tells_the_source_company(self):
        self.sim.move("root", self.itemA, self.locX)
        self.assertEqual([e["kind"] for e in self.events("a-wh2")], ["transfer_out"])
        self.assertEqual(self.events("b-wh"), [])

    def test_move_chain_uses_updated_location_as_source(self):
        self.sim.move("a-wh", self.itemA, self.locB)    # A → B（B 收到）
        self.sim.move("c-wh", self.itemA, self.locC)    # B → C：來源應是 B，不是 A
        b = self.events("b-wh")
        self.assertEqual(sorted(e["kind"] for e in b), ["transfer_in", "transfer_out"])
        self.assertEqual([e["kind"] for e in self.events("a-wh2")], [], "A 公司已不是來源")


class AbnormalOperationTests(Base):
    def test_large_remove_notifies_company_colleagues_but_not_actor(self):
        self.sim.remove("a-wh", self.bigA, 150)
        ev = self.events("a-wh2")
        self.assertEqual([e["kind"] for e in ev], ["large"])
        self.assertEqual(ev[0]["severity"], "danger")
        self.assertIn("大量移除", ev[0]["title"])
        self.assertEqual(self.events("a-wh"), [])
        self.assertEqual(self.events("b-wh"), [])

    def test_threshold_boundary_99_vs_100(self):
        self.sim.remove("a-wh", self.bigA, 99)
        self.assertEqual(self.events("a-wh2"), [])
        self.sim.remove("a-wh", self.bigA, 100)
        self.assertEqual([e["kind"] for e in self.events("a-wh2")], ["large"])

    def test_remove_to_zero_is_flagged(self):
        small = self.sim.add_item(self.partA, self.locA, 20)
        self.sim.remove("a-wh", small, 20)
        ev = self.events("a-wh2")
        self.assertEqual([e["kind"] for e in ev], ["zero"])
        self.assertIn("庫存歸零", ev[0]["title"])

    def test_count_zero_and_count_large(self):
        self.sim.count("a-wh", self.bigA, 0)
        self.assertEqual([e["kind"] for e in self.events("a-wh2")], ["zero"])
        self.sim.count("a-wh", self.bigA, 250)
        self.assertEqual(sorted(e["kind"] for e in self.events("a-wh2")), ["large", "zero"])

    def test_large_add(self):
        self.sim.add("a-wh", self.bigA, 300)
        self.assertEqual([e["kind"] for e in self.events("a-wh2")], ["large"])

    def test_large_transfer_flags_both_companies_even_for_own_company_actor(self):
        self.sim.move("a-wh", self.bigA, self.locB)    # 1000 件
        a, b = self.events("a-wh2"), self.events("b-wh")
        self.assertEqual([e["kind"] for e in a], ["large"], "A 的同事要知道大量調出")
        self.assertEqual(b[0]["kind"], "large")
        self.assertEqual(sorted(b[0]["tags"]), sorted(["大量", "調進"]))

    def test_small_adjustments_are_quiet(self):
        self.sim.remove("a-wh", self.itemA, 5)
        self.sim.add("a-wh", self.itemA, 5)
        self.sim.count("a-wh", self.itemA, 60)
        self.assertEqual(self.events("a-wh2"), [])

    def test_superuser_sees_everything_except_own_actions(self):
        self.sim.remove("a-wh", self.bigA, 150)
        self.sim.remove("b-wh", self.bigB, 150)
        self.assertEqual(len(self.events("root")), 2)
        self.sim.remove("root", self.bigA, 150)
        self.assertEqual(len(self.events("root")), 2, "root 自己的操作不算")

    def test_superuser_sees_all_can_be_disabled(self):
        self.n.cfg["superuser_sees_all"] = False
        self.sim.remove("a-wh", self.bigA, 150)
        self.assertEqual(self.events("root"), [])


class LowStockTests(Base):
    def make_low(self):
        self.sim.items[self.itemA]["quantity"] = 30     # 直接降到 30（< 最低 50）

    def test_only_the_company_of_the_part_sees_low_stock(self):
        self.make_low()
        self.assertEqual(len(self.lows("a-wh2")), 1)
        self.assertIn("A-P01-S1-XL", self.lows("a-wh2")[0]["title"])
        self.assertEqual(self.lows("b-wh"), [])
        self.assertEqual(len(self.lows("root")), 1)

    def test_ack_hides_until_it_gets_worse_and_resets_after_restock(self):
        self.make_low()
        alert = self.lows("a-wh")[0]
        self.assertFalse(alert["read"])
        self.n.mark_read(self.auth("a-wh"), ids=[alert["id"]])
        self.assertTrue(self.lows("a-wh")[0]["read"])
        self.assertFalse(self.lows("a-wh2")[0]["read"], "別人的已讀不受影響")

        self.sim.items[self.itemA]["quantity"] = 20     # 更低 → 再次通知
        self.assertFalse(self.lows("a-wh")[0]["read"])
        self.n.mark_read(self.auth("a-wh"), ids=[alert["id"]])
        self.sim.items[self.itemA]["quantity"] = 200    # 補貨
        self.assertEqual(self.lows("a-wh"), [])
        self.sim.items[self.itemA]["quantity"] = 40     # 又低於標準 → 重新通知
        self.assertFalse(self.lows("a-wh")[0]["read"])

    def test_part_without_company_is_ignored_and_templates_skipped(self):
        stray = self.sim.add_part("ZZ-1", minimum_stock=99)
        tpl = self.sim.add_part("A-P01", minimum_stock=99, is_template=True)
        self.assertEqual(self.lows("root"), [])


class ReadStateTests(Base):
    def test_read_state_is_per_user_and_survives_restart(self):
        self.sim.remove("a-wh", self.bigA, 150)
        self.sim.remove("a-wh", self.bigA, 120)
        feed = self.feed("a-wh2")
        self.assertEqual(feed["unread"], 2)
        first = feed["items"][-1]["id"]
        self.n.mark_read(self.auth("a-wh2"), ids=[first])
        self.assertEqual(self.feed("a-wh2")["unread"], 1)
        self.assertEqual(self.feed("root")["unread"], 2, "別人的已讀狀態獨立")

        self.n = self.make_notifier()             # 模擬服務重啟（同一個狀態檔）；舊的實例不再使用
        self.assertEqual(self.n.feed(self.auth("a-wh2"))["unread"], 1)
        self.n.mark_read(self.auth("a-wh2"), all_=True)
        self.n = self.make_notifier()
        self.assertEqual(self.n.feed(self.auth("a-wh2"))["unread"], 0)
        self.sim.remove("a-wh", self.bigA, 110)
        self.assertEqual(self.feed("a-wh2")["unread"], 1, "全部已讀之後的新事件仍會通知")

    def test_same_user_on_two_computers_shares_read_state(self):
        self.sim.sessions["sess-a-wh2-laptop"] = "a-wh2"
        self.sim.remove("a-wh", self.bigA, 150)
        desk, laptop = self.auth("a-wh2"), {**self.auth("a-wh2"), "cookie": "sessionid=sess-a-wh2-laptop"}
        self.clock.advance(1)
        self.n.mark_read(desk, all_=True)
        self.clock.advance(1)
        self.assertEqual(self.n.feed(laptop)["unread"], 0)

    def test_mark_all_read_only_covers_what_the_user_saw(self):
        self.sim.remove("a-wh", self.bigA, 150)
        seen = self.feed("a-wh2")
        newest_seen = max(int(i["id"]) for i in seen["items"])
        self.sim.remove("a-wh", self.bigA, 120)       # 使用者按下「全部已讀」前一刻才進來的事件
        self.feed("b-wh")                             # 別人的輪詢已把它處理進伺服器
        self.n.mark_read(self.auth("a-wh2"), all_=True, up_to=newest_seen)
        after = self.feed("a-wh2")
        self.assertEqual(after["unread"], 1, "沒看過的事件不可被一起標成已讀")

    def test_mark_all_read_cannot_pre_read_future_events(self):
        self.n.mark_read(self.auth("a-wh2"), all_=True, up_to=10 ** 9)
        self.sim.remove("a-wh", self.bigA, 150)
        self.assertEqual(self.feed("a-wh2")["unread"], 1, "up_to 超過目前進度時不可預先把未來事件標為已讀")

    def test_mark_read_ignores_junk_and_is_idempotent(self):
        self.sim.remove("a-wh", self.bigA, 150)
        eid = self.feed("a-wh2")["items"][0]["id"]
        for _ in range(3):
            self.n.mark_read(self.auth("a-wh2"), ids=[eid, "abc", "low:999", "", None])
        self.assertEqual(self.n.store.state["users"]["a-wh2"]["read"].count(int(eid)), 1)


class RobustnessTests(Base):
    def test_cursor_prevents_reprocessing_and_handles_many_entries(self):
        for _ in range(250):
            self.sim.remove("a-wh", self.bigA, 100) if self.sim.items[self.bigA]["quantity"] >= 100 else self.sim.add("a-wh", self.bigA, 500)
        self.feed("a-wh2")
        count = len(self.n.store.state["events"])
        self.assertGreater(count, 100, "超過一頁（100 筆）的新紀錄也要處理完")
        self.feed("a-wh2")
        self.feed("a-wh2")
        self.assertEqual(len(self.n.store.state["events"]), count)
        self.assertEqual(self.n.store.state["cursor"], self.sim.tracking[-1]["pk"])

    def test_upstream_failure_keeps_old_events_warns_and_catches_up_later(self):
        self.sim.remove("a-wh", self.bigA, 150)
        self.assertEqual(len(self.events("a-wh2")), 1)
        self.sim.fail["/api/stock/track/"] = 500
        self.sim.remove("a-wh", self.bigA, 130)
        feed = self.feed("a-wh2")
        self.assertEqual(len(feed["items"]), 1)
        self.assertTrue(feed["warnings"])
        self.sim.fail.clear()
        feed = self.feed("a-wh2")
        self.assertEqual(len(feed["items"]), 2, "恢復後要補上中斷期間的事件")
        self.assertEqual(feed["warnings"], [])

    def test_group_lookup_failure_does_not_advance_cursor(self):
        self.clock.advance(100)                  # 讓群組快取過期
        self.sim.fail["/api/user/group/"] = 500
        self.sim.move("a-wh", self.itemA, self.locA2)
        self.sim.move("root", self.itemA, self.locB)
        feed = self.feed("b-wh")
        self.assertEqual(feed["items"], [])
        self.assertTrue(feed["warnings"])
        self.sim.fail.clear()
        self.assertEqual([e["kind"] for e in self.events("b-wh")], ["transfer_in"], "之後要補處理，不可漏掉")

    def test_user_without_track_permission_gets_warning_not_crash(self):
        self.sim.deny_track_for.add("c-wh")
        self.sim.remove("a-wh", self.bigA, 150)
        feed = self.feed("c-wh")
        self.assertTrue(any("沒有讀取庫存異動的權限" in w for w in feed["warnings"]))
        self.assertEqual(len(self.events("a-wh2")), 1, "有權限的人讀取時仍會處理")

    def test_corrupt_state_file_is_backed_up_and_restarts_quietly(self):
        self.sim.remove("a-wh", self.bigA, 150)
        self.feed("a-wh2")
        with open(self.state_path, "w", encoding="utf-8") as f:
            f.write("{ 這不是 JSON")
        fresh = self.make_notifier()
        self.assertTrue(any(n.startswith("state.json.corrupt-") for n in os.listdir(self.tmp.name)))
        self.assertEqual(fresh.feed(self.auth("a-wh2"))["items"], [], "損毀後重新開始，不會把舊事件當新通知轟炸")

    def test_unreadable_entry_does_not_block_the_rest(self):
        self.sim.tracking.append({"pk": self.sim.pk(), "item": 999999, "part": None, "date": "x", "deltas": {"removed": "壞資料"},
                                  "label": "", "notes": "", "tracking_type": 12, "user": 1, "user_detail": {"username": "a-wh"}})
        self.sim.remove("a-wh", self.bigA, 150)
        self.assertEqual([e["kind"] for e in self.events("a-wh2")], ["large"])

    def test_database_rolled_back_to_older_state_reinitializes(self):
        self.sim.remove("a-wh", self.bigA, 150)
        self.assertEqual(len(self.events("a-wh2")), 1)
        self.n.mark_read(self.auth("a-wh2"), all_=True)
        # 模擬資料庫被還原到更早的時間點：異動紀錄編號回到比服務記錄的進度更小
        self.sim.tracking = []
        self.sim.items[self.bigA]["quantity"] = 1000
        self.assertEqual(self.feed("a-wh2")["items"], [], "舊事件已不存在於資料庫，應清掉")
        self.assertEqual(self.n.store.state["cursor"], 0)
        self.sim.remove("a-wh", self.bigA, 150)
        self.assertEqual(len(self.events("a-wh2")), 1, "重新初始化之後的新事件要能通知")
        self.assertEqual(self.feed("a-wh2")["unread"], 1, "已讀進度也要重設，否則新事件會被當成已讀")

    def test_retention_cap(self):
        self.n.cfg["max_events"] = 5
        for _ in range(8):
            self.sim.add("a-wh", self.bigA, 150)
        self.feed("a-wh2")
        self.assertEqual(len(self.n.store.state["events"]), 5)

    def test_events_do_not_leak_across_companies_in_feed_payload(self):
        self.sim.remove("b-wh", self.bigB, 150, notes="B 公司內部備註")
        raw = json.dumps(self.feed("a-wh2"), ensure_ascii=False)
        self.assertNotIn("B 公司內部備註", raw)
        self.assertNotIn("B-P01", raw)


class HttpTests(Base):
    def setUp(self):
        super().setUp()
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), notifier_mod.make_handler(self.n))
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.http.server_address[1]}"

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        super().tearDown()

    def call(self, method, path, user=None, body=None, headers=None, raw_cookie=None):
        h = dict(headers or {})
        if user:
            h["Cookie"] = self.sim.cookie(user)
        if raw_cookie:
            h["Cookie"] = raw_cookie
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read()), r.headers
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}"), e.headers

    def test_health_is_open_and_feed_requires_login(self):
        self.assertEqual(self.call("GET", "/notify/api/health")[0], 200)
        before = len(self.sim.requests)
        code, body, _ = self.call("GET", "/notify/api/feed")
        self.assertEqual(code, 401)
        self.assertEqual(body["error"], "not_authenticated")
        code, _, _ = self.call("GET", "/notify/api/feed", raw_cookie="sessionid=forged")
        self.assertEqual(code, 401)
        called = {r[1] for r in self.sim.requests[before:]}
        self.assertEqual(called, {"/api/user/me/"}, "未通過驗證前不可讀取任何其他資料")

    def test_feed_returns_user_scoped_json_without_cache(self):
        self.sim.remove("a-wh", self.bigA, 150)
        code, body, headers = self.call("GET", "/notify/api/feed", user="a-wh2")
        self.assertEqual(code, 200)
        self.assertEqual(body["user"]["companies"], ["A 公司"])
        self.assertEqual(body["unread"], 1)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_read_requires_marker_header_and_works_with_it(self):
        self.sim.remove("a-wh", self.bigA, 150)
        code, body, _ = self.call("POST", "/notify/api/read", user="a-wh2", body={"all": True})
        self.assertEqual(code, 400, "缺少 X-Requested-With 標頭（防跨站表單）要拒絕")
        code, _, _ = self.call("POST", "/notify/api/read", user="a-wh2", body={"all": True},
                               headers={"X-Requested-With": "inventory-helper"})
        self.assertEqual(code, 200)
        self.assertEqual(self.call("GET", "/notify/api/feed", user="a-wh2")[1]["unread"], 0)

    def test_bad_json_and_unknown_paths(self):
        req = urllib.request.Request(self.base + "/notify/api/read", data=b"{bad", method="POST",
                                     headers={"X-Requested-With": "inventory-helper", "Cookie": self.sim.cookie("a-wh")})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(cm.exception.code, 400)
        self.assertEqual(self.call("GET", "/notify/api/nothing", user="a-wh")[0], 404)

    def test_upstream_host_header_is_the_one_the_user_used(self):
        self.call("GET", "/notify/api/feed", user="c-wh", headers={"Host": "10.95.216.85"})
        self.assertIn("10.95.216.85", {r[2] for r in self.sim.requests if r[1] == "/api/user/me/"})

    def test_identity_lookup_is_cached(self):
        before = sum(1 for r in self.sim.requests if r[1] == "/api/user/me/")
        for _ in range(3):
            self.call("GET", "/notify/api/feed", user="a-wh2")
        self.assertEqual(sum(1 for r in self.sim.requests if r[1] == "/api/user/me/") - before, 1)

    def test_token_header_is_forwarded_for_api_clients(self):
        self.sim.sessions["sess-tok"] = "a-wh2"
        code, body, _ = self.call("GET", "/notify/api/feed", headers={"Authorization": "Token tok"})
        self.assertEqual((code, body["user"]["name"]), (200, "a-wh2"))

    def test_inventree_down_gives_502_not_crash(self):
        self.sim.fail["/api/user/me/"] = 503
        code, body, _ = self.call("GET", "/notify/api/feed", user="c-wh")
        self.assertEqual((code, body["error"]), (502, "upstream"))


class ConfigTests(unittest.TestCase):
    def test_example_config_is_valid_and_matches_seed_config(self):
        with open(os.path.join(ROOT, "inventree-seed", "config.example.json"), encoding="utf-8") as f:
            seed = json.load(f)
        cfg = notifier_mod.load_config(os.path.join(ROOT, "inventree-app", "notifier", "config.example.json"))
        self.assertEqual([(c["code"], c["name"], c["group"]) for c in cfg["companies"]],
                         [(c["code"], c["name"], c["owner_group"]) for c in seed["companies"]],
                         "通知服務的公司設定必須與匯入腳本一致")

    def test_config_without_companies_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "c.json")
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"companies": []}, f)
            with self.assertRaises(SystemExit):
                notifier_mod.load_config(p)


if __name__ == "__main__":
    unittest.main()
