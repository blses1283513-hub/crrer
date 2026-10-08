"""Realistic fab simulator + answer key: physics, injected events, counterfactual impact, scoring, saving."""

import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from metro_toolkit.datagen.answer_key import CHART_SETUPS, compare_charts, compare_drivers, score_detection, spc_flags
from metro_toolkit.datagen.fab import load_fab_config, load_truth, save_fab, simulate_fab
from metro_toolkit.ingest import list_datasets, load_dataset, quality_report

CFG = load_fab_config()


@pytest.fixture(scope="module")
def baseline():
    return simulate_fab(CFG, "baseline", n_lots=40)


def test_reproducible_and_realistic_baseline(baseline):
    again = simulate_fab(CFG, "baseline", n_lots=40)
    assert np.allclose(again.wafers["yield"], baseline.wafers["yield"])
    w = baseline.wafers
    assert 0.85 < w["yield"].mean() < 0.95 and w["yield"].std() > 0.02  # realistic level and spread
    assert 500 < len(baseline.grid["x"]) < 700  # ~1 cm² dies on 300 mm
    assert np.hypot(baseline.grid["x"], baseline.grid["y"]).max() < 147
    assert baseline.drivers.iloc[0]["cause"] == "defect_density"
    assert (baseline.drivers["yield_loss_pct"] > 0).sum() >= 4  # several real causes, not just one
    assert len(baseline.events) == 0
    assert (w["yield"] == w["yield_without_events"]).all()


def test_metrology_sampling_and_etest(baseline):
    long = baseline.long
    meas = long[long.parameter == "gate_ox_thk"]
    assert meas["wafer_id"].nunique() == 40 * 5  # 5 of 25 wafers measured
    assert meas.groupby("wafer_id").size().eq(13).all()  # 13-point plan
    assert long[long.parameter == "yield"]["wafer_id"].nunique() == 40 * 25  # yield for every wafer
    vt = long[long.parameter == "vt_mv"].set_index("wafer_id")["value"]
    tox = baseline.wafers.set_index("wafer_id")["true_gate_ox_thk"]
    assert np.corrcoef(vt.loc[tox.index], tox)[0, 1] > 0.5  # physics: thicker oxide -> higher Vt
    assert not any(i["level"] == "error" for i in quality_report(long)["issues"])


def test_metrology_offset_changes_measurement_not_product(baseline):
    r = simulate_fab(CFG, "metrology_offset", n_lots=40)
    assert np.allclose(r.wafers["yield"], baseline.wafers["yield"])  # product identical
    assert r.events.iloc[0]["yield_impact"] == 0.0 and not r.events.iloc[0]["affects_product"]
    ids = set(r.events.iloc[0]["wafer_ids"].split(";"))
    m = r.long[r.long.parameter == "gate_ox_thk"].groupby("wafer_id")["value"].mean()
    b = baseline.long[baseline.long.parameter == "gate_ox_thk"].groupby("wafer_id")["value"].mean()
    diff = (m - b).loc[sorted(ids)]
    assert diff.mean() == pytest.approx(0.030, abs=0.004)


def test_physical_events_have_negative_true_impact():
    r = simulate_fab(CFG, "mixed")
    ev = r.events.set_index("type")
    for t in ("shift", "drift", "defects", "bowl"):
        assert ev.loc[t, "yield_impact"] < -0.03, t
    assert ev.loc["metro_offset", "yield_impact"] == 0.0
    shift_ids = ev.loc["shift", "wafer_ids"].split(";")
    w = r.wafers.set_index("wafer_id").loc[shift_ids]
    assert (w["yield"] <= w["yield_without_events"]).all()


def test_recipe_change_propagates_to_etched_cd():
    base = simulate_fab(CFG, "baseline", n_lots=60)
    rc = simulate_fab(CFG, "recipe_change", n_lots=60)
    late = base.wafers["lot_index"] >= 45
    d_litho = (rc.wafers.loc[late, "true_wl_cd_litho"] - base.wafers.loc[late, "true_wl_cd_litho"]).mean()
    d_etch = (rc.wafers.loc[late, "true_wl_cd_etch"] - base.wafers.loc[late, "true_wl_cd_etch"]).mean()
    assert d_litho == pytest.approx(0.35, abs=0.01) and d_etch == pytest.approx(0.35, abs=0.01)


def test_particle_event_raises_inline_defects_with_edge_ring():
    r = simulate_fab(CFG, "particle_event")
    ids = set(r.events.iloc[0]["wafer_ids"].split(";"))
    w = r.wafers
    hit = w["wafer_id"].isin(ids)
    assert w.loc[hit, "defect_density_true"].mean() > 3 * w.loc[~hit, "defect_density_true"].mean()
    assert (w.loc[hit, "defect_pattern"] == "edge_ring").all()
    dies = r.dies.set_index("wafer_id").loc[sorted(ids), "map"]
    gx, gy = np.array(r.grid["x"]), np.array(r.grid["y"])
    edge = np.hypot(gx, gy) > 0.85 * r.grid["r_eff"]
    fails = np.array([[c == "D" for c in m] for m in dies])
    assert fails[:, edge].mean() > 3 * fails[:, ~edge].mean()


def test_bowl_event_visible_in_within_wafer_sigma_not_mean():
    r = simulate_fab(CFG, "edge_bowl")
    flags = spc_flags(r.long, stats=("mean", "nu_1sigma_pct"), parameters=["wl_cd_etch"])
    table, _ = score_detection(flags, r.events, r.long)
    assert table.iloc[0]["status"] == "detected" and "nu_1sigma_pct" in table.iloc[0]["caught_by"]


def test_score_detection_on_hand_made_case():
    ts = pd.date_range("2026-01-01", periods=6, freq="h")
    long = pd.DataFrame({"parameter": "p", "wafer_id": [f"W{i}" for i in range(6)], "timestamp": ts, "value": 1.0})
    events = pd.DataFrame([{"id": "E1", "type": "shift", "where": "X", "start_lot": 0, "end_lot": 1, "parameters": "p",
                            "wafer_ids": "W2;W3;W4", "yield_impact": -0.1, "affects_product": True},
                           {"id": "E2", "type": "bowl", "where": "Y", "start_lot": 0, "end_lot": 1, "parameters": "p",
                            "wafer_ids": "Z9", "yield_impact": -0.1, "affects_product": True}])
    flags = pd.DataFrame({"parameter": "p", "stat": "mean", "group": "all", "wafer_id": ["W0", "W3"], "timestamp": ts[:2]})
    table, summ = score_detection(flags, events, long)
    e1, e2 = table.set_index("id").loc["E1"], table.set_index("id").loc["E2"]
    assert e1["detected"] and e1["delay_wafers"] == 1 and e1["observable"] == 3
    assert e2["status"].startswith("not observable")
    assert summ == {"events": 2, "observable": 1, "detected": 1, "median_delay_wafers": 1.0, "flagged_points": 2,
                    "false_alarms": 1, "false_alarm_rate_pct": pytest.approx(100 / 6)}


def test_ewma_catches_slow_drift_sooner_than_imr():
    r = simulate_fab(CFG, "slow_drift")
    summ, delays = compare_charts(r.long, r.events)
    assert list(summ["setup"]) == list(CHART_SETUPS) and len(delays) == len(CHART_SETUPS)
    d = delays.set_index("setup")["delay_wafers"]
    assert d["EWMA λ=0.2"] < d["I-MR rule 1"] / 3  # small sustained drift: EWMA's strength
    fa = summ.set_index("setup")["false_alarm_rate_pct"]
    assert fa["I-MR rule 1"] < fa["I-MR WE 1-4"] and fa["I-MR rule 1"] < fa["CUSUM k=0.5 h=5"]  # the price of speed


def test_chart_options_reach_control_chart():
    r = simulate_fab(CFG, "slow_drift", n_lots=40)
    loose = spc_flags(r.long, "EWMA", parameters=["hk_thk"], chart_opts={"ewma_lambda": 0.2, "L": 3.0})
    tight = spc_flags(r.long, "EWMA", parameters=["hk_thk"], chart_opts={"ewma_lambda": 0.2, "L": 2.0})
    assert len(tight) > len(loose)


def test_compare_drivers():
    drivers = pd.DataFrame({"cause": ["d", "c", "k", "g", "t"], "yield_loss_pct": [6, 2, 1, 0.5, 0.0]})
    perfect = compare_drivers(["d", "c", "k", "g", "t"], drivers)
    assert perfect["top1_match"] and perfect["spearman"] == pytest.approx(1.0) and perfect["truth"] == ["d", "c", "k", "g"]
    wrong = compare_drivers(["g", "k", "c", "d"], drivers)
    assert not wrong["top1_match"] and wrong["spearman"] == pytest.approx(-1.0)


def test_save_load_and_semiyield_names(tmp_path, baseline):
    paths = save_fab(baseline, "sim base", tmp_path, semiyield_names=True)
    assert list_datasets(tmp_path) == ["sim_base"]  # answer-key files are not listed as datasets
    truth = load_truth("sim base", tmp_path)
    assert truth["semiyield_names"] and len(truth["wafers"]) == 1000 and "map" in truth["dies"]
    long = load_dataset("sim_base", tmp_path)
    assert {"gate_oxide_thickness", "poly_cd", "metal_resistance", "defect_density", "yield"} <= set(long.parameter)
    wafer = pd.read_csv(paths["wafer"])
    assert {"gate_oxide_thickness", "yield"} <= set(wafer.columns)
    assert load_truth("does not exist", tmp_path) is None


def _semiyield():
    for c in (os.environ.get("SEMIYIELD_DIR"), Path(__file__).resolve().parents[3] / "semiyield"):
        if c and (Path(c) / "dashboard" / "app.py").exists():
            return str(c)
    return None


@pytest.mark.skipif(_semiyield() is None or importlib.util.find_spec("sklearn") is None,
                    reason="needs SemiYield and scikit-learn")
def test_semiyield_yield_model_learns_simulated_fab(tmp_path):
    sys.path.insert(0, _semiyield())
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "semiyield_guide"))
    from semiyield.models import ensemble

    import yield_fix

    yield_fix.apply(ensemble.YieldEnsemble)
    res = simulate_fab(CFG, "baseline", n_lots=80)
    paths = save_fab(res, "sy", tmp_path, semiyield_names=True)
    df = pd.read_csv(paths["wafer"])
    feats = [c for c in ("gate_oxide_thickness", "poly_cd", "metal_resistance", "defect_density") if c in df]
    clean = df[feats + ["yield"]].dropna()
    X, y = clean[feats].values, clean["yield"].values
    n_test = int(len(X) * 0.2)
    Xtr, Xte, ytr, yte = X[:-n_test], X[-n_test:], y[:-n_test], y[-n_test:]
    val = int(len(Xtr) * 0.15)
    m = ensemble.YieldEnsemble(n_estimators=200, lstm_epochs=30, random_state=42)
    m.fit(Xtr[:-val], ytr[:-val], Xtr[-val:], ytr[-val:])
    # Realistic ceiling: much of the yield loss is random at die level, so even the TRUE defect density
    # explains only ~0.1-0.35 of the variance (seeds 1/7/2). The model must clearly beat "predict the mean".
    assert m.score(Xte, yte)["R2"] > 0.1


def test_fab_dashboard_page(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path))
    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=300)
    at.run()
    at.sidebar.radio[0].set_value("Fab simulator").run()
    [s for s in at.slider if s.label.startswith("批數")][0].set_value(30).run()
    [b for b in at.button if b.label == "產生並儲存"][0].click().run()
    [b for b in at.button if b.label == "計算分數"][0].click().run()
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels["晶圓"] == "750" and "/" in labels["抓到的事件"]
    [b for b in at.button if b.label == "分類並打分數"][0].click().run()
    assert not at.exception and any(m.label == "正確率 accuracy" for m in at.metric)
    [b for b in at.button if b.label == "比較管制圖"][0].click().run()
    assert not at.exception and len(at.dataframe) >= 1
    at.sidebar.radio[0].set_value("SPC").run()
    assert not at.exception and at.sidebar.selectbox[0].value == "匯入：sim_mixed"
