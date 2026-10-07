import numpy as np
import pytest

from metro_toolkit.config import load_stack
from metro_toolkit.metrology.thinfilm import (
    FitParameter, Layer, Stack, builtin_library, fit, fit_sites, simulate_reflectometry, simulate_se,
    simulate_site_spectra,
)
from metro_toolkit.metrology.thinfilm.studies import thickness_n_correlation, underlayer_error_transfer

LIB = builtin_library()
WL = np.linspace(250, 1000, 151)


def oxide(t):
    return Stack([Layer(LIB["SiO2"], t)], LIB["Si"])


def test_reflectometry_recovers_thickness_from_far_start():
    meas = simulate_reflectometry(oxide(342.0), WL, noise=0.002, rng=3)
    res = fit(oxide(60.0), meas, [FitParameter(0, bounds=(1, 1500))])
    assert res.values["L0.thickness"] == pytest.approx(342.0, abs=0.3)
    assert 0.5 < res.chi2_red < 2.0


def test_global_search_beats_local_only():
    meas = simulate_reflectometry(oxide(342.0), WL, noise=0.002, rng=3)
    params = [FitParameter(0, bounds=(1, 1500), initial=150.0)]
    good = fit(oxide(150.0), meas, params)
    local = fit(oxide(150.0), meas, params, global_search=False)
    assert good.chi2_red <= local.chi2_red + 1e-9
    assert abs(good.values["L0.thickness"] - 342.0) < 0.3


def test_se_thin_oxide():
    meas = simulate_se(oxide(1.8), WL, (65, 70, 75), 0.02, 0.04, rng=4)
    res = fit(oxide(5.0), meas, [FitParameter(0, bounds=(0, 20))])
    assert res.values["L0.thickness"] == pytest.approx(1.8, abs=0.01)


def test_two_layer_fit():
    stack, recipe = load_stack("nitride_on_oxide")
    truth = stack.copy_with([47.3, 8.6])
    meas = simulate_se(truth, WL, recipe["angles_deg"], 0.02, 0.04, rng=5)
    res = fit(stack, meas, recipe["fit_params"])
    assert res.values["L0.thickness"] == pytest.approx(47.3, abs=0.05)
    assert res.values["L1.thickness"] == pytest.approx(8.6, abs=0.05)


def test_reported_stderr_is_calibrated():
    errs, sds = [], []
    for seed in range(20):
        meas = simulate_reflectometry(oxide(120.0), WL, noise=0.003, rng=100 + seed)
        res = fit(oxide(120.0), meas, [FitParameter(0, bounds=(100, 140))], global_search=False)
        errs.append(res.values["L0.thickness"] - 120.0)
        sds.append(res.stderr["L0.thickness"])
    ratio = np.std(errs, ddof=1) / np.mean(sds)
    assert 0.5 < ratio < 2.0


def test_thin_film_thickness_n_correlation_is_high():
    df = thickness_n_correlation([3.0, 200.0], WL)
    assert df.corr_t_n.iloc[0] > 0.95
    assert df.A_stderr.iloc[0] > 20 * df.A_stderr.iloc[1]


def test_underlayer_error_transfers_without_chi2_alarm():
    stack, recipe = load_stack("highk_on_il")
    df = underlayer_error_transfer(stack, recipe, 0, 1, errors_nm=(-0.2, 0.0, 0.2), wavelength_nm=WL)
    assert df.attrs["transfer_coefficient"] > 0.5
    assert df.chi2_red.max() < 2.0


def test_site_pipeline():
    stack, recipe = load_stack("thermal_oxide_100")
    truth = np.array([100.0, 99.5, 99.0, 98.2, 100.4])
    meas = simulate_site_spectra(stack, recipe, truth, WL, seed=1)
    out = fit_sites(stack, recipe["fit_params"], meas)
    assert np.allclose(out["L0.thickness"], truth, atol=0.15)
    assert out.fit_ok.all()
