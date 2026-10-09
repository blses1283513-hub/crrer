"""Yield-analysis, split, weekly-KPI and unclassifiable-defect cases: the right answer follows the data, every outcome
occurs, the numbers obey the rules the guide and the hover cards state, the charts explain every point, and the
cases work in mixes and on the page."""

import math
import re
from pathlib import Path

import pytest

from metro_toolkit import cases, guide
from metro_toolkit.cases import compose
from metro_toolkit.dashboard import figures as F

PH = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
NEW = ["ye_inline_probe_corr", "split_confounded", "split_zone_decision", "kpi_dly_trend", "insp_unclassified_defect"]
CHARTS = {"probe_overlay": "ye_inline_probe_corr", "capture_kill": "ye_inline_probe_corr", "split_check": "split_confounded",
          "zone_yield": "split_zone_decision", "dly_trend": "kpi_dly_trend", "level_pass": "kpi_dly_trend",
          "layer_repeat": "insp_unclassified_defect"}


@pytest.fixture(autouse=True)
def _local_store(tmp_path, monkeypatch):
    monkeypatch.setenv("METRO_CASES_PATH", str(tmp_path / "cases"))


def _perfect(c):
    return {q.key: (q.accepted()[0] if q.kind == "single" else list(q.correct)) for q in c.questions}


def _guide(c):
    return dict(c.guide)


@pytest.mark.parametrize("case_type", NEW)
def test_new_types_are_complete_at_every_level(case_type):
    for level in cases.LEVELS:
        for seed in (1, 2):
            c = cases.generate(cases.make_id(case_type, level, seed))
            assert cases.score(c, _perfect(c))["total"] == 100
            for lg in ("zh", "en"):
                for key in ("title", "brief", "model_message", "explanation"):
                    assert c.text(key, lg).strip() and "{" not in c.text(key, lg), (key, lg)
                assert all(ok for _, ok in cases.message_checklist(c, c.text("model_message", lg), lg)), lg
            assert c.evidence and c.guide and c.spec["domain"] in cases.library()["domains"]
            assert not re.search(r"micron|美光", str(c.spec), re.I)


def test_inline_probe_answer_follows_capture_rates():
    seen = set()
    for seed in range(12):
        c = cases.generate(f"ye_inline_probe_corr-I-{seed:05d}")
        v, f = c.v, _guide(c)["capture_kill"]
        if c.correct["cause"] == "C_INSP_BLIND":
            assert v["cap1"] < 30 and v["cap2"] >= 60 and v["best_step"] == v["s2"] and f.status == "act"
        else:
            assert c.correct["cause"] == "C_KILLER_SOURCE" and v["cap1"] >= 60 and v["best_step"] == v["s1"] and f.status == "good"
        # the expected gain is Y = exp(-D·A·KR) from the best step, and it cannot exceed the fails it explains
        assert v["gain"] == pytest.approx(100 * (1 - math.exp(-v["d_best"] * v["area"] * v["kr_best"])), abs=0.15)
        assert 0 < v["gain"] <= v["fail_pct"]
        seen.add(c.correct["cause"])
    assert seen == {"C_INSP_BLIND", "C_KILLER_SOURCE"}


def test_split_answers_follow_the_setup_check():
    seen = set()
    for seed in range(30):
        c = cases.generate(f"split_confounded-A-{seed:05d}")
        v, f = c.v, _guide(c)["split_check"]
        cause = c.correct["cause"]
        if cause == "C_CONFOUNDED":
            assert v["fem_b"] - v["fem_por"] >= 3 and v["delta_all"] <= -1.5 and abs(v["delta_nom"]) < 0.8
        elif cause == "C_SPLIT_MISSET":
            assert v["n_misrun"] == 8 and abs(v["d_setting"]) < 0.8
        else:
            assert cause == "C_SPLIT_VALID" and v["n_misrun"] == 0 and v["delta_nom"] >= 1.5 and f.status == "good"
        assert (c.correct["decision"] == "D_INCONCLUSIVE") == (cause != "C_SPLIT_VALID") == (f.status == "act")
        seen.add(cause)
    assert seen == {"C_CONFOUNDED", "C_SPLIT_MISSET", "C_SPLIT_VALID"}


def test_zone_split_decision_uses_the_die_weighted_net():
    seen = set()
    for seed in range(12):
        c = cases.generate(f"split_zone_decision-B-{seed:05d}")
        v = c.v
        weighted = (v["d_c"] * v["share_c"] + v["d_m"] * v["share_m"] + v["d_e"] * v["share_e"]) / 100
        assert weighted == pytest.approx(v["net"], abs=0.1) and v["d_e"] < 0 < v["d_c"]
        if c.correct["cause"] == "C_NET_GAIN":
            assert v["net"] > 2 * v["net_se"] and c.correct["decision"] == "D_ADOPT_SPLIT"
        else:
            assert abs(v["net"]) < 2 * v["net_se"] and c.correct["decision"] == "D_KEEP_POR"
        seen.add(c.correct["cause"])
    assert seen == {"C_NET_GAIN", "C_ZONE_CANCEL"}


def test_kpi_red_week_has_one_clear_driver():
    seen = set()
    for seed in range(15):
        c = cases.generate(f"kpi_dly_trend-I-{seed:05d}")
        g = _guide(c)
        d, lv = g["dly_trend"], g["level_pass"]
        assert d.status == "act" and c.v["dly_latest"] < c.v["goal"]
        cause = c.correct["cause"]
        if cause == "C_PROBE_LAG":  # the density peaked before the fix and is back; no level is dropping
            assert d.v["dens_peak"] > 1.8 * d.v["dens_base"] and d.v["dens_latest"] < 1.3 * d.v["dens_base"] and lv.status == "good"
            lots = c.evidence[2]["table"]
            assert (lots["process week"] <= c.v["fix_week"]).all()  # every lot probed this week was made before the fix
        elif cause == "C_OUTLIER_WAFERS":  # without the flagged wafers the week is on goal
            assert c.v["dly_ex"] >= c.v["goal"] and lv.status == "good" and c.v["xlot"] in set(c.evidence[2]["table"]["lot"])
        else:
            assert cause == "C_LEVEL_SYSTEMATIC" and lv.status == "act" and lv.v["worst_level"] == c.v["level"]
            assert d.v["sys_latest"] > d.v["sys_base"] + 1 and d.v["dens_peak"] < 1.8 * d.v["dens_base"]
        seen.add(cause)
    assert seen == {"C_PROBE_LAG", "C_OUTLIER_WAFERS", "C_LEVEL_SYSTEMATIC"}


def test_unclassified_defect_is_decided_by_the_next_layer():
    seen = set()
    for seed in range(12):
        c = cases.generate(f"insp_unclassified_defect-A-{seed:05d}")
        f = _guide(c)["layer_repeat"]
        if c.correct["cause"] == "C_SUBSURFACE":
            assert c.v["repeat_pct"] >= 50 and f.status == "act" and c.correct["decision"] == "D_FLAG_TRACK"
        else:
            assert c.v["repeat_pct"] < 15 and f.status == "good" and c.correct["decision"] == "D_RELEASE"
        seen.add(c.correct["cause"])
    assert seen == {"C_SUBSURFACE", "C_SURFACE_ARTIFACT"}


@pytest.mark.parametrize("key", sorted(CHARTS))
def test_guide_entries_use_only_provided_values(key):
    c = cases.generate(cases.make_id(CHARTS[key], "basic", 3))
    facts = _guide(c)[key]
    entry = guide.charts()[key]
    texts = [entry[s][lg] for s in ("axes", "what", "read", "record") for lg in ("zh", "en")]
    texts += [entry["action"][s][lg] for s in ("good", "watch", "act") for lg in ("zh", "en")]
    texts += [entry["roles"][r][lg] for r in entry["roles"] for lg in ("zh", "en")]
    texts += [i[lg] for i in entry["legend"] for lg in ("zh", "en")]
    used = {m for t in texts for m in PH.findall(t)}
    assert used <= set(facts.v) | {"finding", "status"}, used - set(facts.v)
    for r in entry["roles"]:
        assert "{" not in guide.text(entry["roles"][r], "en", facts)


def _cards(fig):
    return [c for tr in fig.data if tr.customdata is not None for c in tr.customdata]


def test_every_point_of_the_new_charts_has_a_card():
    for cid in ("ye_inline_probe_corr-B-00001", "split_confounded-B-00011", "split_zone_decision-A-00003",
                "kpi_dly_trend-B-00003", "insp_unclassified_defect-B-00005"):
        c = cases.generate(cid)
        for ev in c.evidence:
            k = ev["kind"]
            fig = {"probe_overlay": lambda: F.probe_overlay_figure(ev["dies"], ev["defects"], ev["steps"], ev["bin"]),
                   "capture_kill": lambda: F.capture_kill_figure(ev["table"], ev["monitor"]),
                   "split_check": lambda: F.split_check_figure(ev["table"]),
                   "zone_yield": lambda: F.zone_yield_figure(ev["table"], ev["net"], ev["net_se"]),
                   "dly_trend": lambda: F.dly_trend_figure(ev["w"], ev["goal"], ev.get("fix_week")),
                   "level_pass": lambda: F.level_pass_figure(ev["lv"]),
                   "layer_repeat": lambda: F.layer_repeat_figure(ev["d1"], ev["d2"], ev["radius"], ev["layers"])}.get(k)
            if fig is None:
                continue
            fig = fig()
            for tr in fig.data:
                if tr.x is not None and tr.x[0] is not None and tr.hoverinfo != "skip":
                    assert tr.customdata is not None and len(tr.customdata) == len(tr.x), (k, tr.name)
                    assert tr.hovertemplate == F.card_template()
            assert all("─────────" in t for t in _cards(fig)), k


def test_hover_verdicts_match_the_rules():
    c = cases.generate("ye_inline_probe_corr-B-00001")
    assert c.correct["cause"] == "C_INSP_BLIND"
    fig = F.capture_kill_figure(c.evidence[1]["table"], c.evidence[1]["monitor"])
    cap = fig.data[0].customdata
    assert "🔴" in cap[0] and "blind" in cap[0] and "🟢" in cap[1]  # monitor blind, the other step sees them
    s = cases.generate("split_confounded-B-00011")
    t = s.evidence[0]["table"]
    cards = dict(zip(t["wafer_id"], F.split_wafer_hover(t)))
    for _, r in t.iterrows():
        bad = r["planned"] != r["actual"] or r["fem"] != "nominal"
        assert ("🔴" in cards[r["wafer_id"]]) == bad
    w = cases.generate("kpi_dly_trend-B-00003").evidence[0]
    for (_, r), card in zip(w["w"].iterrows(), F.dly_hover(w["w"], w["goal"])):
        assert ("🔴" in card) == (r["dly"] < w["goal"])


def test_new_types_join_random_mixes_and_rank_by_urgency():
    assert set(NEW) <= set(cases.case_types())
    assert set(cases.case_types("yield")) == {"ye_inline_probe_corr", "split_confounded", "split_zone_decision", "kpi_dly_trend"}
    for d in ("D_SWITCH_MONITOR", "D_INCONCLUSIVE", "D_RED_ESCALATE", "D_FLAG_TRACK", "D_BASELINE_OK"):
        assert d in compose.URGENCY_BY_DECISION
    lag = next(cases.generate(f"kpi_dly_trend-B-{s:05d}") for s in range(20)
               if cases.generate(f"kpi_dly_trend-B-{s:05d}").correct["cause"] == "C_PROBE_LAG")
    assert compose.urgency_of(lag) == 1  # a fixed cause waiting for probe is not today's emergency
    settings = {"mode": "separate", "types": ["kpi_dly_trend", "spc_chamber_shift"]}
    compose.validate_settings(settings)
    ct = compose.save_settings(settings)
    mix = cases.generate(cases.make_id(ct, "basic", 0))
    assert cases.score(mix, _perfect(mix))["total"] == 100


def test_new_formats_prefill_headings():
    c = cases.generate("kpi_dly_trend-B-00001")
    tpl = cases.message_template(c, ["zh", "en"])
    assert "【主要原因 Main driver】" in tpl and not any(ok for _, ok in cases.message_checklist(c, tpl, "en"))
    s = cases.generate("split_confounded-B-00001")
    assert "【實驗檢查 Setup check】" in cases.message_template(s, ["zh", "en"])


def test_new_case_on_the_page(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path / "imp"))
    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=300)
    at.run()
    at.sidebar.radio(key="nav_page").set_value("Case study 案例練習").run()
    for cid in ("kpi_dly_trend-B-00003", "ye_inline_probe_corr-I-00002"):
        at.text_input(key="case_replay_id").set_value(cid).run()
        [b for b in at.button if b.key == "case_replay"][0].click().run()
        assert not at.exception
        c = cases.generate(cid)
        for q in ("cause", "action", "decision"):
            at.radio(key=f"q_{q}_{cid}").set_value(c.correct[q])
        at.multiselect(key=f"q_notify_{cid}").set_value(c.correct["notify"])
        at.text_area(key=f"q_msg_{cid}").set_value(c.text("model_message", "en"))
        [b for b in at.button if "Submit" in b.label][0].click().run()
        assert not at.exception
        assert [m.value for m in at.metric if m.label.startswith("總分")] == ["100 / 100"]
    at.selectbox(key="case_domain").set_value("yield").run()
    [b for b in at.button if b.key == "case_new"][0].click().run()
    assert not at.exception and at.session_state["case_id"].split("-")[0] in cases.case_types("yield")
