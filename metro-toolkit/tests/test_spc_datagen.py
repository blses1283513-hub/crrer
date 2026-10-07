import numpy as np
import pytest

from metro_toolkit.analysis import control_chart, process_capability, spc_by_group, wafer_summary, western_electric
from metro_toolkit.datagen import Excursion, ThicknessSimConfig, simulate_thickness
from metro_toolkit.schema import validate


def test_imr_limits_from_moving_range():
    x = np.array([10.0, 11.0, 10.0, 11.0, 10.0])
    ch = control_chart(x, "IMR")
    assert ch.sigma == pytest.approx(1.0 / 1.128)
    assert ch.ucl[0] == pytest.approx(10.4 + 3 / 1.128)


def test_western_electric_rules():
    z = np.zeros(20)
    z[5] = 3.5  # rule 1
    z[10:18] = 0.5  # rule 4 run
    v = western_electric(z, 0.0, 1.0)
    assert (5, 1) in {(i, r) for i, r, _ in v}
    assert any(r == 4 and i == 17 for i, r, _ in v)


def test_ewma_detects_small_shift_faster_than_shewhart():
    """Average run length after a 1-sigma shift: EWMA << Shewhart rule 1 (Montgomery ch. 9)."""
    def run_length(chart):
        hits = chart.out_of_control[chart.out_of_control >= 50]
        return (hits.min() - 50) if hits.size else 100

    ewma, imr = [], []
    for seed in range(40):
        rng = np.random.default_rng(seed)
        x = np.r_[rng.normal(0, 1, 50), rng.normal(1.0, 1, 100)]
        ewma.append(run_length(control_chart(x, "EWMA", phase1=50)))
        imr.append(run_length(control_chart(x, "IMR", phase1=50, rules=(1,))))
    assert np.mean(ewma) < 0.5 * np.mean(imr)


def test_ewma_in_control_false_alarm_rate():
    alarms = sum(control_chart(np.random.default_rng(s).normal(0, 1, 50), "EWMA").out_of_control.size > 0
                 for s in range(300))
    assert alarms / 300 < 0.10


def test_capability():
    rng = np.random.default_rng(1)
    c = process_capability(rng.normal(100, 0.5, 5000), 98.5, 101.5)
    assert c["Pp"] == pytest.approx(1.0, rel=0.05)
    assert c["Ppk"] <= c["Pp"]


def test_simulated_data_schema_and_detection():
    cfg = ThicknessSimConfig(n_lots=40, excursions=[Excursion("DEP01-B", 20, 4, "shift", 1.2)])
    df, truth = simulate_thickness(cfg)
    assert validate(df) == []
    assert set(df.chamber_id) == {"DEP01-A", "DEP01-B", "DEP02-A", "DEP02-B"}
    w = wafer_summary(df)
    chart = spc_by_group(w)["DEP01-B"]
    sub = w[w.chamber_id == "DEP01-B"].sort_values("timestamp").reset_index(drop=True)
    inj = set(sub.index[sub.wafer_id.isin(truth.wafer_id)])
    flagged = {i for i, r, _ in chart.violations if r in (1, 2)}
    assert len(inj & flagged) >= len(inj) - 1


def test_schema_reports_missing_columns():
    df, _ = simulate_thickness(ThicknessSimConfig(n_lots=2))
    assert any("lot_id" in p for p in validate(df.drop(columns="lot_id")))
