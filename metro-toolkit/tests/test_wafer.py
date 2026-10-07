import numpy as np
import pytest

from metro_toolkit.wafer import interpolate_map, sampling_plan, uniformity_metrics, zernike_decompose
from metro_toolkit.wafer.uniformity import ZERNIKE_TERMS, center_to_edge


@pytest.mark.parametrize("plan,n", [("1", 1), ("5", 5), ("9", 9), ("13", 13), ("25", 25), ("49", 49)])
def test_plan_sizes_and_edge_exclusion(plan, n):
    sp = sampling_plan(plan)
    assert len(sp) == n and sp.site.tolist() == list(range(1, n + 1))
    assert sp.r_mm.max() <= 147.0 + 1e-9
    assert sp.attrs["r_eff_mm"] == 147.0


def test_uniformity_formulas():
    m = uniformity_metrics([99.0, 100.0, 101.0, 100.0])
    assert m["mean"] == 100.0
    assert m["nu_1sigma_pct"] == pytest.approx(100 * np.std([99, 100, 101, 100], ddof=1) / 100)
    assert m["range_pct"] == pytest.approx(2.0)
    assert m["half_range_pct"] == pytest.approx(1.0)


def test_zernike_recovers_signature():
    sp = sampling_plan("49")
    rho, th = np.hypot(sp.x_mm, sp.y_mm) / 147.0, np.arctan2(sp.y_mm, sp.x_mm)
    truth = {"piston": 100.0, "tilt_x": 0.3, "tilt_y": -0.2, "bowl": -0.5, "edge_roll": -0.1}
    v = sum(c * ZERNIKE_TERMS[k](rho, th) for k, c in truth.items())
    zk = zernike_decompose(sp.x_mm, sp.y_mm, v, radius_mm=147.0)
    for k, c in truth.items():
        assert zk["coefficients"][k] == pytest.approx(c, abs=1e-9)
    assert zk["r2"] == pytest.approx(1.0)


def test_center_to_edge_sign():
    sp = sampling_plan("49")
    v = 100 - (sp.r_mm / 147.0) ** 2
    assert center_to_edge(sp.x_mm, sp.y_mm, v) == pytest.approx(-1.0, abs=0.05)


def test_interpolated_map_masks_outside():
    sp = sampling_plan("25")
    X, Y, Z = interpolate_map(sp.x_mm, sp.y_mm, 100 + 0 * sp.x_mm, radius_mm=147.0, grid=41)
    assert np.isnan(Z[0, 0]) and np.nanmax(np.abs(Z - 100)) < 1e-6
