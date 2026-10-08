"""Hover-guide for SemiYield: explanation file is well formed; launcher attaches tooltips if SemiYield is present."""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

GUIDE = Path(__file__).resolve().parents[1] / "semiyield_guide"
sys.path.insert(0, str(GUIDE))
from spec_limits import baseline_stats, number_format, suggest  # noqa: E402
from yield_fix import ConvexWeights, convex_weights  # noqa: E402
RULES = yaml.safe_load((GUIDE / "explanations.yaml").read_text(encoding="utf-8"))


def test_widget_entries_are_complete():
    seen = set()
    for w in RULES["widgets"]:
        assert w["label"] and w["help"].strip(), w
        key = (w["label"], w.get("min"), w.get("max"), tuple(w.get("options", [])))
        assert key not in seen, f"duplicate rule {key}"
        seen.add(key)
    # labels used on several tabs must be disambiguated, or the first rule would shadow the others
    for label in ("Temperature (C)", "Material"):
        rules = [w for w in RULES["widgets"] if w["label"] == label]
        assert len(rules) >= 2
        assert all(("min" in r) or ("options" in r) or r is rules[-1] for r in rules)


def test_chart_entries_are_valid():
    for c in RULES["charts"]:
        re.compile(c["match"])
        for spec in c.get("traces", []):
            re.compile(spec["name"])
            assert "<extra>" in spec["hover"] and "%{" in spec["hover"]
        for spec in c.get("lines", []):
            re.compile(spec["text"])
            assert "%{" in spec["hover"]


TARGETS = {"gate_oxide_thickness": {"mean": 8.5, "sigma": 0.3}}


def test_spec_uses_yield_window_when_generator_defines_one():
    s = suggest("gate_oxide_thickness", np.random.default_rng(0).normal(8.5, 0.3, 500), TARGETS)
    assert (s.lsl, s.usl) == pytest.approx((7.6, 9.4))
    assert s.kind == "two-sided"


def test_data_spec_gives_cp_133_at_baseline_and_ignores_later_drift():
    rng = np.random.default_rng(1)
    base = rng.normal(100.0, 1.0, 400)
    drifted = rng.normal(100.0, 1.0, 1600) + np.linspace(0, 6, 1600)  # strong drift after the baseline
    s = suggest("etch_rate", np.r_[base, drifted])
    assert s.center == pytest.approx(100.0, abs=0.2)
    assert s.sigma == pytest.approx(1.0, rel=0.1)  # moving range ignores the slow drift
    assert (s.usl - s.lsl) / (6 * s.sigma) == pytest.approx(4 / 3)


def test_percentile_specs_would_hide_a_bad_process():
    """Why the old default was unreliable: percentile specs give Cp ~ 0.9 even for a very noisy process."""
    for sd in (0.1, 10.0):
        x = np.random.default_rng(2).normal(0, sd, 3000)
        lsl, usl = np.percentile(x, [0.5, 99.5])
        assert (usl - lsl) / (6 * x.std()) == pytest.approx(0.86, abs=0.05)


def test_one_sided_and_non_process_parameters():
    rng = np.random.default_rng(3)
    up = suggest("deposition_unif", rng.normal(2.0, 0.3, 500))
    assert up.kind == "upper-only" and up.lsl == 0.0 and up.usl == pytest.approx(3.2, abs=0.15)
    lo = suggest("yield", np.clip(rng.normal(0.95, 0.01, 500), 0, 1))
    assert lo.kind == "lower-only" and lo.usl == 1.0 and 0.85 < lo.lsl < 0.95
    assert suggest("lot_sequence", np.arange(100)).kind == "not-process"
    assert suggest("etch_rate", [1.0, 2.0, np.nan]).kind == "insufficient"


def test_baseline_and_number_format():
    c, s, n = baseline_stats(np.arange(1000.0))
    assert n == 200 and c == pytest.approx(99.5) and s == pytest.approx(1 / 1.128)
    assert number_format(9.1e12, 1.08e13, 2e11)[0] == "%.4e"
    fmt, step = number_format(0.059, 0.099, 0.005)
    assert fmt == "%.5f" and step == pytest.approx(1e-5)


def test_convex_weights_never_amplify():
    rng = np.random.default_rng(4)
    truth = rng.normal(0, 1, 300)
    stack = np.column_stack([truth + rng.normal(0, 0.3, 300), 0.5 * truth + rng.normal(0, 0.3, 300)])
    w = convex_weights(stack, truth)
    assert np.all(w >= 0) and w.sum() == pytest.approx(1.0)
    assert ConvexWeights(w).predict(stack).std() <= stack.std(axis=0).max() + 1e-12
    assert np.allclose(convex_weights(stack, np.zeros(300)), 0.5)  # no signal -> equal weights


def _semiyield_path():
    for c in (os.environ.get("SEMIYIELD_DIR"), GUIDE.parents[2] / "semiyield"):
        if c and (Path(c) / "dashboard" / "app.py").exists():
            return str(c)
    return None


@pytest.mark.skipif(_semiyield_path() is None or importlib.util.find_spec("sklearn") is None,
                    reason="needs SemiYield and scikit-learn")
def test_yield_fix_makes_r2_positive_on_default_data():
    sys.path.insert(0, _semiyield_path())
    from semiyield.datagen import FabDataGenerator
    from semiyield.models import ensemble

    import yield_fix

    yield_fix.apply(ensemble.YieldEnsemble)
    feats = ["gate_oxide_thickness", "poly_cd", "implant_dose", "anneal_temp", "metal_resistance",
             "contact_resistance", "etch_rate", "deposition_unif", "defect_density"]
    df = FabDataGenerator(seed=42, drift_rate=0.05, aging_factor=0.002).generate(n_lots=100, wafers_per_lot=25)
    X, y = df[feats].values, df["yield"].values
    n_test = int(len(X) * 0.2)
    Xtr, Xte, ytr, yte = X[:-n_test], X[-n_test:], y[:-n_test], y[-n_test:]
    val = int(len(Xtr) * 0.15)
    m = ensemble.YieldEnsemble(n_estimators=200, lstm_epochs=30, random_state=42)
    m.fit(Xtr[:-val], ytr[:-val], Xtr[-val:], ytr[-val:])
    assert m.metro_fixed and np.all(m.meta.coef_ >= 0) and m.meta.coef_.sum() == pytest.approx(1.0)
    assert m.score(Xte, yte)["R2"] > 0.5  # was -1.47 before the fix


def test_every_simulation_and_spc_input_is_covered():
    labels = {w["label"] for w in RULES["widgets"]}
    for needed in ("Temperature (C)", "Atmosphere", "Ion species", "Energy (keV)", "Dose (cm^-2)", "Etch mode",
                   "Process type", "Pressure (Torr)", "Drift rate", "Aging factor", "USL", "LSL", "Cpk", "Ppk"):
        assert needed in labels


def _semiyield() -> Path | None:
    for c in (os.environ.get("SEMIYIELD_DIR"), GUIDE.parents[2] / "semiyield"):
        if c and (Path(c) / "dashboard" / "app.py").exists():
            return Path(c)
    return None


@pytest.mark.skipif(_semiyield() is None, reason="SemiYield not found (set SEMIYIELD_DIR to run this test)")
def test_launcher_attaches_tooltips_and_hover(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("SEMIYIELD_DIR", str(_semiyield()))
    at = AppTest.from_file(str(GUIDE / "launch_semiyield.py"), default_timeout=180)
    at.run()
    assert not at.exception
    temp = [w for w in at.slider if w.label == "Temperature (C)"]
    assert len(temp) == 3 and all(w.help for w in temp)
    assert len({w.help for w in temp}) == 3  # oxidation / etch / deposition get different text
    assert all(m.help for m in at.metric)
    for el in at.get("plotly_chart"):
        spec = json.loads(el.proto.spec)
        assert all(d.get("hovertemplate") or d.get("hoverinfo") == "skip" for d in spec["data"])  # skip = legend-only
    # every chart gets a status line and a "how to read this chart" panel
    n_charts = len(at.get("plotly_chart"))
    assert len([e for e in at.expander if "怎麼讀這張圖" in e.label]) == n_charts
    assert len(at.success) + len(at.warning) + len(at.error) >= n_charts

    at.sidebar.radio[0].set_value("Data Generator").run()
    at.button[0].click().run()
    at.sidebar.radio[0].set_value("SPC Dashboard").run()
    assert not at.exception
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    names = [d.get("name") for d in spec["data"]]
    assert {"CL", "UCL", "LCL"} <= set(names)
    assert any(n and n.startswith("UCL / LCL 管制界限") for n in names) and any(n and n.startswith("CL 中心線") for n in names)
    assert any("怎麼讀這張圖" in e.label for e in at.expander)

    # English mode: tooltips switch language
    at.sidebar.radio(key="guide_lang").set_value("en").run()
    assert not at.exception
    m = [m for m in at.metric if m.label == "Cpk"][0]
    assert m.help and not any("\u4e00" <= ch <= "\u9fff" for ch in m.help)
    at.sidebar.radio(key="guide_lang").set_value("both").run()
    assert all(m.help for m in at.metric)

    # counters are removed from the parameter list; the page opens on a real parameter
    sb = [sb for sb in at.selectbox if sb.label == "Parameter to chart"][0]
    assert "lot_sequence" not in sb.options and "wafer_sequence" not in sb.options
    assert sb.value == "gate_oxide_thickness"
    assert any("lot_sequence" in c.value and "移除" in c.value for c in at.caption)

    # suggested spec limits replace the percentile defaults
    sb.set_value("gate_oxide_thickness").run()
    usl = [n for n in at.number_input if n.label == "USL"][0]
    lsl = [n for n in at.number_input if n.label == "LSL"][0]
    assert (lsl.value, usl.value) == pytest.approx((7.6, 9.4))
    assert any("建議規格" in c.value for c in at.caption)
    assert any("閘極氧化層厚度" in c.value for c in at.caption)  # meaning of the selected parameter

    # remaining pages: every input / metric / button has a tooltip, no exceptions
    pages = ["SPICE Export"]
    if importlib.util.find_spec("sklearn"):
        pages += ["Yield Prediction", "Process Optimizer"]
    for page in pages:
        at.sidebar.radio[0].set_value(page).run()
        for b in at.button:
            if b.label in ("Train Ensemble Model", "Run Optimization"):
                b.click().run()
        assert not at.exception, page
        if page == "Yield Prediction":
            assert float([m for m in at.metric if m.label == "R2"][0].value) > 0
            assert any("Metro 修正" in c.value for c in at.caption)
        for kind in ("slider", "number_input", "selectbox", "metric", "button", "text_input"):
            assert all(w.help for w in getattr(at, kind)), (page, kind)
        for el in at.get("plotly_chart"):
            assert all(d.get("hovertemplate") for d in json.loads(el.proto.spec)["data"]), page
