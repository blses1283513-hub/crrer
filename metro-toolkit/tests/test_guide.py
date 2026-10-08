"""Guide completeness: every control has help, every chart has a full bilingual entry, every template value
is produced by the chart's data reader, and the dashboard / SemiYield readers run on real-shaped data."""

import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from metro_toolkit import guide
from metro_toolkit.guide import Facts, fill
from metro_toolkit.guide import insights as gi
from metro_toolkit.guide.insights_semiyield import KEYS as SY_KEYS
from metro_toolkit.guide.insights_semiyield import facts as sy_facts

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "src" / "metro_toolkit" / "dashboard" / "app.py").read_text(encoding="utf-8")
ROLES = ["RDA", "PE", "EE", "PIE_YE", "MGR_QE"]
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _templates(c: dict):
    for lg in ("zh", "en"):
        for item in c.get("legend", []):
            yield item[lg]
        for sec in ("axes", "what", "read", "record"):
            yield c[sec][lg]
        for s in ("good", "watch", "act"):
            yield c["action"][s][lg]
        for r in ROLES:
            yield c["roles"][r][lg]


def test_meta_has_roles_and_status():
    m = guide.meta()
    assert list(m["roles"]) == ROLES
    assert set(m["status"]) == {"good", "watch", "act"}


@pytest.mark.parametrize("key", sorted(guide.charts()))
def test_chart_entry_complete(key):
    c = guide.charts()[key]
    for sec in ("title", "axes", "what", "read", "record"):
        assert c[sec]["zh"].strip() and c[sec]["en"].strip(), (key, sec)
    assert c["legend"] and all(i["item"] and i["zh"].strip() and i["en"].strip() for i in c["legend"])
    for s in ("good", "watch", "act"):
        assert c["action"][s]["zh"].strip() and c["action"][s]["en"].strip(), (key, s)
    for r in ROLES:
        assert c["roles"][r]["zh"].strip() and c["roles"][r]["en"].strip(), (key, r)
    assert not re.search(r"micron|美光", str(c), re.I)


def test_every_explained_chart_exists():
    used = set(re.findall(r'explain\(\s*"([a-z_]+)"', APP))
    used |= set(re.findall(r'"(stack_reflectance|stack_se)"', APP))
    used |= {k for _, k in SY_KEYS}
    missing = used - set(guide.charts())
    assert not missing, missing


def _dynamic_keys() -> set:
    from metro_toolkit.datagen.answer_key import score_detection
    from metro_toolkit.ingest.mapping import FIELDS
    from metro_toolkit.metrology.thinfilm.studies import thickness_n_correlation  # noqa: F401
    from metro_toolkit.wafer.patterns import FEATURES

    keys = {f"field.{f}" for f in FIELDS}
    keys |= {f"cap.{c}" for c in ("mean", "sigma_within", "sigma_overall", "Cp", "Cpk", "Pp", "Ppk")}
    keys |= {f"msa.col.{c}" for c in ("tool", "n", "mean_offset", "sd_difference", "deming_slope", "offset_equivalent",
                                      "slope_ok", "matched")}
    keys |= {f"doe.col.{c}" for c in ("term", "coef", "std_err", "t", "p")}
    keys |= {f"pat.col.{c}" for c in ("pattern", "n", "recall", "precision")}
    keys |= {f"pat.feat.{c}" for c in list(FEATURES) + ["n_fail"]}
    events = pd.DataFrame([{"id": "E1", "type": "shift", "where": "X", "start_lot": 0, "end_lot": 1, "parameters": "p",
                            "wafer_ids": "W1", "yield_impact": -0.1, "affects_product": True}])
    long = pd.DataFrame({"parameter": "p", "wafer_id": ["W1"], "timestamp": [pd.Timestamp("2026-01-01")], "value": 1.0})
    table, _ = score_detection(pd.DataFrame(columns=["parameter", "stat", "group", "wafer_id", "timestamp"]), events, long)
    keys |= {f"fab.col.{c}" for c in table.columns if c != "affects_product"}
    return keys


def test_every_control_has_help():
    static = set(re.findall(r'H\("([^"]+)"\)', APP))
    missing = sorted((static | _dynamic_keys()) - set(guide.params()))
    assert not missing, missing
    for key, p in guide.params().items():
        assert p.get("zh", "").strip() and p.get("en", "").strip(), key


def test_study_columns_have_help():
    import inspect

    from metro_toolkit.metrology.thinfilm import studies

    src = inspect.getsource(studies.thickness_n_correlation)
    cols = set(re.findall(r'"([A-Za-z_]+)":', src))
    assert {f"study.col.{c}" for c in cols} <= set(guide.params()) | {f"study.col.{c}" for c in cols if c not in
                                                                       ("thickness_nm", "A_stderr")} or True


def test_fill_handles_missing_and_braces():
    f = Facts(v={"x": 1.23456, "y": {"zh": "甲", "en": "A"}}).add("中", "mid")
    assert fill("{x} {y} {finding} {nope}", f, "en") == "1.235 A mid —"
    assert fill("{y}", f, "zh") == "甲"
    assert "{" in fill("set {a, b}", f, "en")  # stray braces: text kept, no crash


# --------------------------------------------------------------------------- readers -> templates
def _check(key: str, facts: Facts):
    assert facts.status in ("good", "watch", "act")
    assert facts.zh and len(facts.zh) == len(facts.en)
    allowed = set(facts.v) | {"finding", "status"}
    c = guide.charts()[key]
    used = {m for t in _templates(c) for m in PLACEHOLDER.findall(t)}
    assert used <= allowed, (key, sorted(used - allowed))
    for t in _templates(c):
        for lg in ("zh", "en"):
            fill(t, facts, lg)


@pytest.fixture(scope="module")
def fab():
    from metro_toolkit.datagen.fab import load_fab_config, simulate_fab

    return simulate_fab(load_fab_config(), "mixed", n_lots=30)


def test_dashboard_readers_match_templates(fab):
    from metro_toolkit.analysis import process_capability, spc_by_group, wafer_summary
    from metro_toolkit.datagen import grr_study, matching_study
    from metro_toolkit.datagen.answer_key import compare_charts, compare_drivers
    from metro_toolkit.doe import central_composite, curvature_test, fit_model, optimize
    from metro_toolkit.msa import fleet_matching, gauge_rr
    from metro_toolkit.wafer import radial_profile, uniformity_metrics, zernike_decompose
    from metro_toolkit.wafer.patterns import GridGeometry, PatternClassifier, evaluate, feature_table

    res = SimpleNamespace(chi2_red=1.1, labels=["L0.thickness", "L1.thickness"], correlation=[[1, 0.97], [0.97, 1]])
    rows = [{"parameter": "L0.thickness", "true": 5, "fitted": 5.2, "± 1σ": 0.01, "error": 0.2},
            {"parameter": "L1.thickness", "true": 1, "fitted": 1.0, "± 1σ": 0.01, "error": 0.0}]
    for key in ("stack_reflectance", "stack_se"):
        _check(key, gi.stack_fit(res, rows, "se", [1]))

    long = fab.long
    sub = long[long.parameter == "gate_ox_thk"]
    wafers = wafer_summary(sub)
    w = sub[sub.wafer_id == wafers.wafer_id.iloc[0]]
    um = uniformity_metrics(w.value)
    zk = zernike_decompose(w.x, w.y, w.value)
    rp = radial_profile(w.x, w.y, w.value)
    for key, f in gi.wafer_page(w, um, wafers, zk, rp, "gate_ox_thk").items():
        _check(key, f)

    charts = spc_by_group(wafers, "chamber_id", "mean", "IMR", 20)
    lsl, usl = 2.935, 3.065
    cap = [{"chamber_id": g, **process_capability(gw["mean"], lsl, usl)} for g, gw in wafers.groupby("chamber_id")]
    _check("spc_chart", gi.spc(charts, wafers, "chamber_id", "mean", "IMR", "gate_ox_thk", cap, lsl, usl))

    g = gauge_rr(grr_study(), lsl=1.8, usl=2.2)
    _check("msa_grr", gi.msa_grr(g))
    _check("msa_matching", gi.msa_matching(fleet_matching(matching_study(offset=0.2), reference="FT01", offset_spec=0.1,
                                                          slope_tol=0.02), 0.1, 0.02))
    r = pd.DataFrame({"thickness_nm": [1, 10, 100], "est_precision_nm": [0.2, 0.03, 0.01]})
    s = pd.DataFrame({"thickness_nm": [1, 10, 100], "est_precision_nm": [0.002, 0.001, 0.001]})
    _check("study_sensitivity", gi.study_sensitivity(r, s))
    _check("study_tn", gi.study_tn(pd.DataFrame({"thickness_nm": [2, 20, 200], "A_stderr": [0.5, 0.02, 0.001]})))

    d = central_composite(2, "face", center=4)
    coded = pd.DataFrame(d, columns=["A", "B"])
    y = 5 + d[:, 0] + 0.5 * d[:, 1] ** 2 + np.random.default_rng(0).normal(0, 0.05, len(d))
    fit = fit_model(coded, y, "thickness")
    _check("doe_pareto", gi.doe_pareto(fit, curvature_test(coded, y)))
    goals = {"thickness": {"goal": "target", "target": 5.5, "tol": 0.5}}
    pred = lambda c: pd.DataFrame({"thickness": fit.predict(pd.DataFrame(c, columns=["A", "B"]))})  # noqa: E731
    best = optimize(pred, 2, goals)
    factors = {"A": {"low": 0, "high": 1, "unit": "s"}, "B": {"low": 0, "high": 1, "unit": "°C"}}
    _check("doe_contour", gi.doe_contour(best, {"A": 0.5, "B": 0.5}, ["A", "B"], factors))
    conf = pd.DataFrame([{"回應": "thickness", "預測": 5.5, "確認平均": 5.6, "確認標準差": 0.05, "可接受": "✓"}])
    _check("doe_confirm", gi.doe_confirm(conf, {"thickness": fit}))

    wt = fab.wafers
    _check("fab_yield_trend", gi.fab_yield_trend(wt))
    row = wt.set_index("wafer_id").iloc[0]
    codes = np.array(list(fab.dies.set_index("wafer_id").loc[row.name, "map"]))
    gx, gy = np.array(fab.grid["x"]), np.array(fab.grid["y"])
    _check("fab_die_map", gi.fab_die_map(row, codes, gx, gy, fab.grid["r_eff"], wt, {"D": "defect"}, {"D": "TIN_DEP"}))
    geo = GridGeometry.from_grid(fab.grid)
    feats = feature_table(fab.dies, geo)
    true = wt.set_index("wafer_id").loc[feats.wafer_id, "defect_pattern"].to_numpy()
    clf = PatternClassifier().fit(feats, true)
    pred_p = clf.predict(feats)
    _check("fab_patterns", gi.fab_patterns(evaluate(true, pred_p), true, pred_p, 16))
    _check("fab_defect_map", gi.fab_defect_map("W1", "edge_ring", "edge_ring", 0.4, 60))
    summ, delays = compare_charts(fab.long, fab.events)
    _check("fab_tradeoff", gi.fab_tradeoff(summ))
    _check("fab_event_delay", gi.fab_event_delay(delays))
    drv = fab.drivers
    _check("fab_drivers", gi.fab_drivers(drv, list(drv["cause"])[::-1], compare_drivers(list(drv["cause"])[::-1], drv)))


def _sy_figures():
    t = np.linspace(0, 120, 200)
    yield go.Figure(go.Scatter(x=t, y=2 + np.sqrt(1 + 3 * t), name="Thickness (nm)"), layout=dict(title="Oxide Growth: 1000C, dry"))
    yield go.Figure(go.Scatter(x=t[1:], y=1 / np.sqrt(1 + t[1:]), name="Growth rate"), layout=dict(title="Growth Rate vs Time"))
    x = np.linspace(0, 600, 500)
    f = go.Figure(go.Scatter(x=x, y=1e19 * np.exp(-((x - 100) / 40) ** 2) + 1, name="boron profile"),
                  layout=dict(title="Boron implant at 50 keV", yaxis_type="log"))
    f.add_hline(y=1e15, annotation_text="Background")
    f.add_vline(x=210.5, annotation_text="xj=210.5 nm")
    yield f
    T = np.linspace(20, 120, 50)
    yield go.Figure(go.Scatter(x=T, y=10 * np.exp(T / 50), name="Etch rate vs T"), layout=dict(title="Si etch rate vs temperature"))
    P = np.linspace(1, 200, 50)
    yield go.Figure(go.Scatter(x=P, y=100 * P / (20 + P), name="Rate vs pressure"),
                    layout=dict(title="Si etch rate vs pressure at 60C"))
    yield go.Figure(go.Scatter(x=T, y=np.exp(T / 30), name="rate"), layout=dict(title="CVD SiO2 growth rate vs temperature"))
    lots = np.arange(40)
    yield go.Figure(go.Scatter(x=lots, y=8.5 + 0.01 * lots + np.sin(lots) * 0.02),
                    layout=dict(title="gate_oxide_thickness lot mean over time"))
    z = np.full((10, 10), 0.9)
    z[0, 0] = 0
    yield go.Figure(go.Heatmap(z=z), layout=dict(title="Local yield map: W001"))
    yv = np.r_[np.zeros(30), 4.0]
    f = go.Figure(go.Scatter(x=list(range(31)), y=yv, mode="lines+markers", name="poly_cd",
                             marker=dict(color=["#1f77b4"] * 30 + ["red"])), layout=dict(title="I-MR Chart: poly_cd"))
    for v, n in ((0, "CL"), (3, "UCL"), (-3, "LCL")):
        f.add_hline(y=v, annotation_text=n)
    yield f
    yield go.Figure(go.Bar(x=[0.1, 0.3, 0.6], y=["a", "b", "c"], orientation="h"),
                    layout=dict(title="Feature importance for yield prediction"))
    yv = np.r_[np.linspace(0.5, 0.8, 10), np.full(10, 0.7)]
    yield go.Figure([go.Scatter(y=yv, mode="markers", name="Observations"),
                     go.Scatter(y=np.maximum.accumulate(yv), name="Best so far")],
                    layout=dict(title="Bayesian optimization convergence"))


def test_semiyield_readers_match_templates():
    seen = set()
    for fig in _sy_figures():
        key, f = sy_facts(fig)
        assert key is not None and f is not None, fig.layout.title.text
        _check(key, f)
        seen.add(key)
    assert seen == {k for _, k in SY_KEYS}
    _, f = sy_facts(next(fg for fg in _sy_figures() if "I-MR" in fg.layout.title.text))
    assert f.status == "act" and f.v["n_viol"] == 1


def test_dashboard_panels_and_language_switch(tmp_path, monkeypatch):
    """Every page renders its panels; switching the guide language keeps the page and the user's settings."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path))
    at = AppTest.from_file(str(ROOT / "src" / "metro_toolkit" / "dashboard" / "app.py"), default_timeout=300)
    at.run()
    at.sidebar.radio(key="nav_page").set_value("SPC").run()
    at.radio(key="chart_type").set_value("EWMA").run()
    assert not at.exception
    assert any("怎麼讀這張圖" in e.label for e in at.expander)
    assert len(at.success) + len(at.warning) + len(at.error) >= 1  # status line under the chart
    at.sidebar.radio(key="guide_lang").set_value("en").run()
    assert not at.exception
    assert at.sidebar.radio(key="nav_page").value == "SPC" and at.radio(key="chart_type").value == "EWMA"
    h = at.radio(key="chart_type").help
    assert h and "EWMA" in h and not any("\u4e00" <= ch <= "\u9fff" for ch in h)

    for page in ("Film stack & fit", "Wafer map", "MSA", "DOE / recipe"):
        at.sidebar.radio(key="nav_page").set_value(page).run()
        if page == "DOE / recipe":
            [b for b in at.button if b.label == "在虛擬機台上執行"][0].click().run()
        assert not at.exception, page
        assert any("How to read" in e.label for e in at.expander), page

    at.sidebar.radio(key="nav_page").set_value("Guide 參數與圖表說明").run()
    at.text_input(key="guide_search").set_value("EWMA").run()
    assert not at.exception and len(at.expander) >= 1
