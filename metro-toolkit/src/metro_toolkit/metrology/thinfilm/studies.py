"""Recipe-development studies a metrology applications engineer runs before release.

thickness_sensitivity      signal change per nm vs thickness, reflectometry vs SE
                           -> when does a technique run out of sensitivity?
thickness_n_correlation    correlation between thickness and n when both float
                           -> below what thickness must n be fixed?
underlayer_error_transfer  bias in the floated layer per nm error in a fixed layer
                           -> how good must the underlayer pre-measurement be?
                           (chi2 does NOT reveal this error; the fit stays "good")
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .fitting import FitParameter, fit, simulate_reflectometry, simulate_se
from .materials import Cauchy
from .tmm import Stack, ellipsometry, ncs, reflectance


def _signal(stack, wl, technique, angles):
    if technique == "reflectometry":
        return reflectance(stack, wl)
    return np.concatenate([np.concatenate(ncs(*ellipsometry(stack, wl, a))) for a in angles])


def thickness_sensitivity(stack: Stack, layer: int, thicknesses, wavelength_nm,
                          technique: str = "reflectometry", angles=(70.0,), step_nm: float = 0.05,
                          noise: float = 1e-3) -> pd.DataFrame:
    """RMS signal change per nm of thickness, divided by the signal noise (SNR per nm).

    The 1-sigma thickness precision is roughly 1 / (SNR_per_nm * sqrt(n_points)).
    """
    rows = []
    for t in thicknesses:
        th = stack.thicknesses.copy()
        th[layer] = t
        lo, hi = th.copy(), th.copy()
        lo[layer], hi[layer] = max(t - step_nm, 0.0), t + step_nm
        d = (_signal(stack.copy_with(hi), wavelength_nm, technique, angles)
             - _signal(stack.copy_with(lo), wavelength_nm, technique, angles)) / (hi[layer] - lo[layer])
        rms = float(np.sqrt(np.mean(d**2)))
        rows.append({"thickness_nm": t, "rms_signal_per_nm": rms, "snr_per_nm": rms / noise,
                     "est_precision_nm": noise / (rms * np.sqrt(d.size)) if rms > 0 else np.inf})
    return pd.DataFrame(rows)


def thickness_n_correlation(thicknesses, wavelength_nm, technique: str = "se", angles=(65.0, 70.0, 75.0),
                            A: float = 1.46, B: float = 0.0035, substrate=None, seed: int = 0) -> pd.DataFrame:
    """Float thickness and Cauchy A together on a single film; report |corr(t, A)| and errors."""
    from .materials import builtin_library

    sub = substrate or builtin_library()["Si"]
    rows = []
    for t in thicknesses:
        from .tmm import Layer

        truth = Stack([Layer(Cauchy(name="film", A=A, B=B), t)], sub)
        meas = (simulate_se(truth, wavelength_nm, angles, 0.02, 0.04, rng=seed) if technique == "se"
                else simulate_reflectometry(truth, wavelength_nm, 0.002, rng=seed))
        start = Stack([Layer(Cauchy(name="film", A=1.5, B=B), t)], sub)
        res = fit(start, meas, [FitParameter(0, "thickness", (max(t * 0.5, 0.1), t * 1.5 + 2)),
                                FitParameter(0, "A", (1.3, 1.8))])
        rows.append({"thickness_nm": t, "corr_t_n": float(abs(res.correlation[0, 1])),
                     "t_error_nm": res.values["L0.thickness"] - t, "t_stderr_nm": res.stderr["L0.thickness"],
                     "A_error": res.values["L0.A"] - A, "A_stderr": res.stderr["L0.A"]})
    return pd.DataFrame(rows)


def underlayer_error_transfer(stack: Stack, recipe: dict, float_layer: int, fixed_layer: int,
                              errors_nm=(-0.3, -0.15, 0.0, 0.15, 0.3), wavelength_nm=None) -> pd.DataFrame:
    """True fixed-layer thickness differs from the value assumed in the recipe by ``error``."""
    wl = wavelength_nm if wavelength_nm is not None else np.linspace(250, 1000, 151)
    rows = []
    for e in errors_nm:
        th = stack.thicknesses.copy()
        th[fixed_layer] += e
        truth = stack.copy_with(th)
        meas = (simulate_se(truth, wl, recipe.get("angles_deg", (65, 70, 75)), 0.02, 0.04, rng=1)
                if recipe.get("technique") == "se" else simulate_reflectometry(truth, wl, 0.002, rng=1))
        lo, hi = 0.0, max(stack.thicknesses[float_layer] * 3, 5.0)
        res = fit(stack, meas, [FitParameter(float_layer, bounds=(lo, hi))])
        lab = f"L{float_layer}.thickness"
        rows.append({"underlayer_error_nm": e, "floated_bias_nm": res.values[lab] - stack.thicknesses[float_layer],
                     "reported_stderr_nm": res.stderr[lab], "chi2_red": res.chi2_red})
    df = pd.DataFrame(rows)
    df.attrs["transfer_coefficient"] = float(np.polyfit(df.underlayer_error_nm, df.floated_bias_nm, 1)[0])
    return df
