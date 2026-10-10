"""瀏覽器測試用：啟動『模擬 InvenTree』＋『真正的通知服務』，並提供控制介面讓測試製造事件。

啟動後在 stdout 印出一行 JSON：{"notifier_port":…, "ctl_port":…, "ids":{…}}，之後持續執行。
控制：POST http://127.0.0.1:<ctl_port>/ctl  {"op": "remove", "args": ["a-wh", "bigA", 150]}
      其中 args 裡的字串若是 ids 內的名稱（itemA、bigA、locB…）會自動換成實際編號。
"""

import importlib.util
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from inventree_sim import InvenTreeSim, serve  # noqa: E402

spec = importlib.util.spec_from_file_location("notifier", os.path.join(ROOT, "inventree-app", "notifier", "notifier.py"))
notifier_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notifier_mod)


def build():
    sim = InvenTreeSim()
    ids = {}
    ids["locA"], ids["locA2"] = sim.add_location("A 公司/主倉"), sim.add_location("A 公司/備貨區")
    ids["locB"], ids["locC"] = sim.add_location("B 公司/主倉"), sim.add_location("C 公司/主倉")
    partA = sim.add_part("A-P01-S1-XL", minimum_stock=50)
    ids["itemA"] = sim.add_item(partA, ids["locA"], 80)
    ids["bigA"] = sim.add_item(sim.add_part("A-P02"), ids["locA"], 1000)
    ids["bigB"] = sim.add_item(sim.add_part("B-P02"), ids["locB"], 1000)
    for name, groups, sup in [("a-wh", ["company-A", "role-warehouse"], False), ("a-wh2", ["company-A"], False),
                              ("b-wh", ["company-B"], False), ("c-wh", ["company-C"], False), ("root", [], True)]:
        sim.add_user(name, groups, sup)
    return sim, ids


def main():
    sim, ids = build()
    sim_server, sim_url = serve(sim)
    with open(os.path.join(ROOT, "inventree-app", "notifier", "config.example.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.update({"min_process_interval_s": 0, "low_stock_cache_s": 0, "identity_cache_s": 0})
    state = os.path.join(tempfile.mkdtemp(prefix="notifier-test-"), "state.json")
    notifier = notifier_mod.Notifier(cfg, notifier_mod.InvenTreeClient(sim_url), notifier_mod.StateStore(state))
    nsrv = ThreadingHTTPServer(("127.0.0.1", 0), notifier_mod.make_handler(notifier))
    threading.Thread(target=nsrv.serve_forever, daemon=True).start()

    class Ctl(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            args = [ids.get(a, a) if isinstance(a, str) else a for a in body.get("args", [])]
            try:
                result = getattr(sim, body["op"])(*args)
                out, code = {"ok": True, "result": result if isinstance(result, (int, str, type(None))) else None}, 200
            except Exception as e:  # noqa: BLE001
                out, code = {"ok": False, "error": repr(e)}, 400
            raw = json.dumps(out).encode()
            self.send_response(code)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    ctl = ThreadingHTTPServer(("127.0.0.1", 0), Ctl)
    threading.Thread(target=ctl.serve_forever, daemon=True).start()
    print(json.dumps({"notifier_port": nsrv.server_address[1], "ctl_port": ctl.server_address[1], "ids": ids}), flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
