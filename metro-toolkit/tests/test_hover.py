"""Hover explanations on every chart: each point gets the same card (what it is, a verdict with the rule and the numbers,
the next step), the verdicts follow the thresholds the charts' status lines use, and no line is wide enough to be clipped."""

import re

import numpy as np
import pandas as pd
import pytest

from metro_toolkit import cases
from metro_toolkit.dashboard import figures as F

ICONS = ("🟢", "🟡", "🔴", "ℹ️")


def width(line: str) -> int:
    plain = re.sub(r"<[^>]+>", "", line.replace("&nbsp;", " "))
    return sum(F._cells(c) for c in plain)


def cards(fig):
    """All tooltip strings of a figure's traces (heatmap cells included)."""
    out = []
    for tr in fig.data:
        cd = getattr(tr, "customdata", None)
        if cd is None:
            continue
        flat = np.asarray(cd, dtype=object).ravel()
        out += [c for c in flat if isinstance(c, str) and "─────────" in c]
    return out


def assert_cards_are_well_formed(fig):
    found = cards(fig)
    assert found, "no tooltip cards"
    for card in found:
        lines = card.split("<br>")
        sep = lines.index("─────────")
        assert any(i in lines[sep + 1] for i in ICONS), lines[sep + 1]  # verdict line right under the rule
        assert sep >= 2  # at least a name and a number above it
        assert max(width(ln) for ln in lines) <= 84, max(lines, key=width)  # short enough not to be clipped
    for tr in fig.data:
        arr = np.asarray(getattr(tr, "customdata", None), dtype=object).ravel() if getattr(tr, "customdata", None) is not None else []
        if len(arr) and isinstance(arr[0], str):
            assert tr.hovertemplate == F.card_template()


# --------------------------------------------------------------------------- every chart builds well-formed cards
def case_figures(cid):
    c = cases.generate(cid)
    figs = []
    for ev in c.evidence:
        k = ev["kind"]
        if k == "wafer":
            p, u = F.quantity(ev["w"])
            figs += [F.wafer_map_figure(ev["w"], ev["um"], "absolute", "t"), F.wafer_map_figure(ev["w"], ev["um"], "deviation", "t"),
                     F.zernike_figure(ev["zk"], p, u), F.radial_figure(ev["rp"], p, u)]
        elif k == "fit":
            figs += F.fit_figures(ev["technique"], ev["wl"], ev["meas"], ev["res"].stack, ev.get("angles"))
        elif k == "grr":
            figs.append(F.grr_figure(ev["g"]))
        elif k == "matching":
            figs.append(F.bland_altman_figure(ev["wide"], ev["spec"]))
        elif k == "sensitivity":
            figs.append(F.sensitivity_figure(ev["r"], ev["s"]))
        elif k == "doe":
            figs.append(F.pareto_figure(ev["fit"], "t"))
        elif k == "defect_counts":
            figs.append(F.defect_counts_figure(ev["counts"], ev["maxout"], "t"))
        elif k == "review_pareto":
            figs.append(F.review_pareto_figure(ev["classes"]))
        elif k == "adders":
            figs.append(F.adders_figure(ev["table"]))
        elif k == "bin_corr":
            figs.append(F.bin_corr_figure(ev["table"], ev["params"], ev["bin"]))
        elif k == "yield_trend":
            figs.append(F.yield_trend_figure(ev["w"]))
        elif k == "die_map":
            figs.append(F.die_map_figure(ev["codes"], ev["gx"], ev["gy"], ev["r_eff"], "t"))
    return figs


@pytest.mark.parametrize("cid", ["wafer_edge_roll-B-00003", "stack_wrong_underlayer-B-00002", "msa_repeatability-B-00005",
                                 "msa_matching-B-00004", "study_technique_choice-B-00001", "doe_curvature_missed-B-00006",
                                 "insp_nuisance_recipe-B-00003", "insp_split_vs_baseline-B-00002", "ye_bin_metro_corr-B-00001",
                                 "fab_chamber_excursion-B-00001"])
def test_every_chart_in_the_cases_has_well_formed_cards(cid):
    figs = case_figures(cid)
    assert figs
    for fig in figs:
        assert_cards_are_well_formed(fig)


def test_synthetic_charts_have_cards():
    tn = F.tn_figure(pd.DataFrame({"thickness_nm": [2, 20, 200], "A_stderr": [0.5, 0.02, 0.001]}))
    assert_cards_are_well_formed(tn)
    h = pd.DataFrame({"attempt": [1, 2, 3], "case": ["a-B-00001", "b-I-00002", "c-A-00003"], "score": [30, 70, 95]})
    fig = F.go.Figure(F.go.Scatter(x=[1, 2, 3], y=h.score, customdata=F.attempt_hover(h), hovertemplate=F.card_template()))
    assert_cards_are_well_formed(fig)


# --------------------------------------------------------------------------- the verdicts follow the rules
def verdict_of(card: str) -> str:
    lines = card.split("<br>")
    return next(i for i in ICONS if i in lines[lines.index("─────────") + 1])


def test_wafer_sites_flag_outliers_and_oos():
    rng = np.random.default_rng(1)
    x, y = rng.uniform(-100, 100, 30), rng.uniform(-100, 100, 30)
    val = 3 + rng.normal(0, 0.01, 30)
    val[7] += 0.25  # one bad site
    w = pd.DataFrame({"x": x, "y": y, "value": val, "site": range(1, 31), "lsl": 2.9, "usl": 3.1})
    out = F.site_hover(w, {"mean": float(val.mean())}, "nm")
    assert verdict_of(out[7]) == "🔴" and "超出規格" in out[7]  # beyond the spec
    assert verdict_of(out[0]) == "🟢" and "typical" in out[0]
    w2 = w.assign(lsl=2.0, usl=4.0)  # spec far away: the same site is an outlier, not an OOS
    assert "單點離群" in F.site_hover(w2, {"mean": float(val.mean())}, "nm")[7]


def test_yield_trend_flags_the_excursion_lots():
    rows = [{"lot_index": i, "lot_id": f"D{i + 1:04d}", "yield": 0.9 + 0.005 * np.sin(i)} for i in range(40)]
    rows[30]["yield"] = 0.55
    lot_y = pd.DataFrame(rows)
    med = float(lot_y["yield"].median())
    mad = 1.4826 * float((lot_y["yield"] - med).abs().median())
    out = F.yield_hover(lot_y, med, mad)
    assert verdict_of(out[30]) == "🔴" and "良率 excursion" in out[30] and "commonality" in out[30]
    assert verdict_of(out[3]) == "🟢"


def test_grr_thresholds():
    g = {"pct_study_var": {"repeatability": 5.0, "reproducibility": 20.0, "gauge_rr": 40.0, "part_to_part": 99.0},
         "pct_tolerance": {"gauge_rr": 12.0}, "ndc": 3, "verdict": "x"}
    out = F.grr_hover(g, ["repeatability", "reproducibility", "gauge_rr", "part_to_part"])
    assert [verdict_of(c) for c in out] == ["🟢", "🟡", "🔴", "ℹ️"]
    assert "ndc = 3" in out[3] and "P/T = 12.0%" in out[2]


def test_zernike_dominant_and_radial_edge_roll():
    zk = {"coefficients": {"piston": 3.0, "tilt_x": 0.001, "tilt_y": 0.001, "bowl": 0.05, "astig_0": 0.002, "astig_45": 0.0, "edge_roll": 0.002}}
    out = F.zernike_hover(zk, "nm")
    names = list(k for k in zk["coefficients"] if k != "piston")
    assert verdict_of(out[names.index("bowl")]) == "🟡" and "主導" in out[names.index("bowl")]
    assert verdict_of(out[names.index("tilt_x")]) == "ℹ️"
    rp = pd.DataFrame({"r_mm": [0, 50, 100, 147], "mean": [3.0, 3.0, 3.0, 2.5], "std": [0.01, 0.01, 0.01, 0.01]})
    rad = F.radial_hover(rp, "nm")
    assert verdict_of(rad[-1]) == "🟡" and "edge roll-off" in rad[-1] and verdict_of(rad[0]) == "ℹ️"
    rp["mean"] = [3.0, 3.0, 3.0, 3.001]
    assert verdict_of(F.radial_hover(rp, "nm")[-1]) == "🟢"


def test_fit_residual_card():
    wl = np.arange(400, 700, 10.0)
    yf = np.sin(wl / 50)
    ym = yf + np.random.default_rng(0).normal(0, 0.01, wl.size)
    ym[5] += 0.3  # a spike
    out = F.fit_hover(wl, ym, yf, "R")
    assert verdict_of(out[5]) == "🟡" and "off the model" in out[5] and verdict_of(out[0]) == "🟢"
    assert all("RMS" in c for c in out)


def test_sensitivity_and_tn_rules():
    r = pd.DataFrame({"thickness_nm": [1, 10, 100], "est_precision_nm": [0.2, 0.04, 0.01]})
    s = pd.DataFrame({"thickness_nm": [1, 10, 100], "est_precision_nm": [0.001, 0.001, 0.001]})
    out = F.sensitivity_hover(r, s, "reflectometry", "SE")
    assert [verdict_of(c) for c in out] == ["🟡", "🟢", "🟢"] and "0.05 nm" in out[0] and "SE" in out[0]
    tn = F.tn_hover(pd.DataFrame({"thickness_nm": [2, 200], "A_stderr": [0.5, 0.001]}))
    assert [verdict_of(c) for c in tn] == ["🟡", "🟢"]


def test_pareto_and_contour_text():
    tab = pd.DataFrame({"term": ["A", "B"], "coef": [1.5, 0.01], "t": [9.0, 0.3], "p": [0.001, 0.8]})
    out = F.pareto_hover(tab, 2.3)
    assert verdict_of(out[0]) == "🟢" and "significant" in out[0] and verdict_of(out[1]) == "ℹ️" and "2.30" in out[1]
    x, y = np.linspace(0, 1, 5), np.linspace(0, 1, 5)
    fig = F.doe_contour_figure(x, y, np.random.default_rng(0).uniform(0, 1, (5, 5)), "D", "cycles", "temp_c",
                               pd.DataFrame({"cycles": [0.2, 0.8], "temp_c": [0.3, 0.7]}), {"cycles": 0.5, "temp_c": 0.5}, "t")
    assert "D 越接近 1" in fig.data[0].hovertemplate and "not a measurement" in fig.data[0].hovertemplate
    assert_cards_are_well_formed(fig)
    star = next(tr for tr in fig.data if tr.name == "suggested recipe 建議配方")
    assert "predicted D" in star.customdata[0]


def test_die_map_causes_and_zones():
    codes = np.array([".", "D", "G", "T"])
    gx, gy = np.array([0.0, 10.0, 140.0, -20.0]), np.array([0.0, 5.0, 0.0, 30.0])
    fig = F.die_map_figure(codes, gx, gy, 150.0, "t")
    text = " ".join(c for c in cards(fig))
    assert "良品 pass" in text and "killer defect" in text and "gate_ox_thk" in text and "device window" in text and "邊緣 edge" in text


def test_defect_charts():
    counts = pd.DataFrame({"wafer_id": list("abcdef"), "count": [1000, 1100, 900, 1000, 100_000, 5000], "group": "lot"})
    out = F.counts_hover(counts, counts, 100_000, "lot")  # median 1050: 5000 is 4.8x it
    assert [verdict_of(c) for c in out] == ["🟢", "🟢", "🟢", "🟢", "🔴", "🟡"] and "maxout" in out[4] and "floor" in out[4]
    classes = pd.Series({"Non-visible": 80, "Particle": 12, "Scratch": 8})
    r = F.review_hover(classes[["Non-visible"]], 100.0, "Non-visible", 80.0)
    assert verdict_of(r[0]) == "🔴" and "nuisance" in r[0]
    assert verdict_of(F.review_hover(classes[["Non-visible"]], 100.0, "Non-visible", 30.0)[0]) == "🟡"
    assert verdict_of(F.review_hover(classes[["Particle"]], 100.0, "Non-visible", 80.0)[0]) == "ℹ️"
    t = pd.DataFrame({"wafer_id": list("abcdefgh"), "group": ["split"] * 4 + ["baseline"] * 4,
                      "previous": [1800, 1900, 1700, 1800, 600, 620, 580, 600], "current": [2100, 2200, 2000, 2100, 850, 870, 830, 850]})
    prev, cur = F.adders_hover(t)
    assert verdict_of(prev[0]) == "🔴" and "incoming" in prev[0] and verdict_of(cur[0]) == "🟢"  # incoming, not added here
    assert verdict_of(prev[5]) == "ℹ️" and "baseline" in prev[5]
    rng = np.random.default_rng(2)
    z = rng.normal(0, 1, 20)
    bt = pd.DataFrame({"wafer_id": [f"w{i}" for i in range(20)], "p1": z, "p2": rng.normal(0, 1, 20)})
    bt["bin_loss"] = 4 + 2 * z
    assert verdict_of(F.bin_hover(bt, "p1", 0.98, "Bin O")[0]) == "🔴" and verdict_of(F.bin_hover(bt, "p2", 0.05, "Bin O")[0]) == "🟢"


def test_fab_page_cards():
    summ = pd.DataFrame({"setup": ["a", "b", "c"], "false_alarm_rate_pct": [0.5, 2.0, 0.5], "median_delay_wafers": [4, 1, 1],
                         "detected": [3, 4, 4], "observable": [4, 4, 4]})
    verdicts = [verdict_of(F.tradeoff_hover(r, summ)) for _, r in summ.iterrows()]
    assert verdicts == ["🟡", "🟡", "🟢"]  # a: quietest only, b: fastest only, c: best on both
    assert verdict_of(F.delay_hover("a", "E1 shift", 0, "detected")) == "🟢"
    assert verdict_of(F.delay_hover("a", "E1 shift", 3, "detected")) == "🟡"
    assert verdict_of(F.delay_hover("a", "E1 shift", np.nan, "missed")) == "🔴"
    assert verdict_of(F.delay_hover("a", "E1 shift", np.nan, "unobservable")) == "ℹ️"
    cm = pd.DataFrame([[9, 1], [5, 5]], index=["edge_ring", "random"], columns=["edge_ring", "random"])
    grid = F.confusion_hover(cm, cm.div(cm.sum(axis=1), axis=0) * 100)
    assert verdict_of(grid[0][0]) == "🟢" and verdict_of(grid[1][0]) == "🔴" and verdict_of(grid[0][1]) == "🟡"  # a 10% miss is a watch, 50% of a row is an act
    drv = pd.DataFrame({"cause": ["gate_ox", "defects"], "yield_loss_pct": [6.0, 2.0]})
    assert "75%" in F.driver_hover(drv)[0] and verdict_of(F.driver_hover(drv)[1]) == "ℹ️"


def test_study_log_cards_use_the_weak_spot_thresholds():
    assert F.score_band(85)[0] == "good" and F.score_band(84.9)[0] == "watch" and F.score_band(50)[0] == "watch" and F.score_band(49)[0] == "act"
    prof = {"by_type": pd.DataFrame({"type": ["spc_chamber_shift"], "attempts": [3], "recent": [90.0], "last_level": ["basic"], "domain": ["spc"]})}
    assert cases.focus_level(prof, "spc_chamber_shift") == "intermediate"  # >= 85 steps the level up, as the card says
    prof["by_type"]["recent"] = 40.0
    prof["by_type"]["last_level"] = "intermediate"
    assert cases.focus_level(prof, "spc_chamber_shift") == "basic"  # < 50 steps it down
    h = pd.DataFrame({"case": ["x", "y"], "score": [40.0, 90.0]})
    assert [verdict_of(c) for c in F.attempt_hover(h)] == ["🔴", "🟢"] and len(F.rolling_hover(h)) == 2
    dom = pd.DataFrame({"domain": ["spc"], "mean": [60.0], "attempts": [4]})
    assert verdict_of(F.area_hover(dom, {"spc": "SPC"})[0]) == "🟡"
