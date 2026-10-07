import numpy as np
import pandas as pd
import pytest

from metro_toolkit.datagen import grr_study, matching_study, repeatability_study, stability_series
from metro_toolkit.msa import (
    deming_regression, dynamic_repeatability, fleet_matching, gauge_rr, long_term_stability, static_repeatability,
    tool_matching,
)


def test_grr_recovers_variance_components():
    df = grr_study(n_parts=40, operators=("A", "B", "C", "D", "E"), n_reps=6, part_sigma=1.0,
                   repeat_sigma=0.1, operator_sigma=0.0, seed=1)
    g = gauge_rr(df, lsl=97, usl=103)
    assert g["std"]["repeatability"] == pytest.approx(0.1, rel=0.1)
    assert g["std"]["part_to_part"] == pytest.approx(1.0, rel=0.3)
    assert g["pct_tolerance"]["gauge_rr"] == pytest.approx(100 * 6 * g["std"]["gauge_rr"] / 6.0)
    assert g["pct_tolerance"]["gauge_rr"] == pytest.approx(10.0, abs=2.0)  # 6*0.1/6 = 10 %


def test_grr_textbook_anova_numbers():
    # 2 parts x 2 operators x 2 reps, hand-computed: SS_E = 0.5*4*... see below
    df = pd.DataFrame({"part": list("aaaabbbb"), "operator": list("xxyyxxyy"),
                       "value": [1.0, 1.2, 1.1, 1.3, 2.0, 2.2, 2.1, 2.3]})
    g = gauge_rr(df)
    # within-cell variance: each pair differs by 0.2 -> s^2 = 0.02
    assert g["variance"]["repeatability"] == pytest.approx(0.02 * 4 / 5, rel=1e-9)  # pooled with interaction (SS_PO=0)


def test_grr_requires_balance():
    df = grr_study().iloc[:-1]
    with pytest.raises(ValueError):
        gauge_rr(df)


def test_repeatability_split():
    df = repeatability_study(n_sites=8, n_cycles=30, n_repeats=5, static_sigma=0.03, load_sigma=0.04, seed=2)
    st = static_repeatability(df[df.cycle == 1])
    dy = dynamic_repeatability(df)
    assert dy["sigma_static"] == pytest.approx(0.03, rel=0.1)
    assert dy["sigma_load"] == pytest.approx(0.04, rel=0.2)
    assert dy["sigma_dynamic"] == pytest.approx(0.05, rel=0.15)
    assert st["three_sigma"] == pytest.approx(3 * st["sigma"])


def test_stability_drift_detection():
    assert long_term_stability(stability_series(drift_per_day=0.005))["significant_drift"]
    assert not long_term_stability(stability_series(drift_per_day=0.0, seed=21))["significant_drift"]


def test_deming_exact_without_noise():
    x = np.linspace(90, 110, 30)
    b, a = deming_regression(x, 0.5 + 1.01 * x)
    assert b == pytest.approx(1.01) and a == pytest.approx(0.5)


def test_tool_matching_equivalence():
    rng = np.random.default_rng(3)
    ref = 100 + rng.normal(0, 1, 200)
    ok = tool_matching(ref, ref + 0.05 + rng.normal(0, 0.05, 200), offset_spec=0.3)
    bad = tool_matching(ref, ref + 0.5 + rng.normal(0, 0.05, 200), offset_spec=0.3)
    assert ok["matched"] and not bad["matched"]


def test_fleet_matching_flags_offset_tool():
    res = fleet_matching(matching_study(offset=0.45), reference="FT01", offset_spec=0.3)
    assert not res.matched.iloc[0]
