"""Wafer-level pipeline: per-site spectra -> fitted thickness map.

Mirrors a production recipe: the first site gets a full global search; later
sites are seeded from the previous result and searched within a window, which
is both faster and robust as long as the window exceeds the expected
within-wafer range. Sites whose fit quality is poor are flagged instead of
silently reported.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .fitting import FitParameter, fit, simulate_reflectometry, simulate_se
from .tmm import Stack


def simulate_site_spectra(stack: Stack, recipe: dict, site_thickness: np.ndarray, wavelength_nm,
                          layer: int = 0, noise: float | None = None, seed: int = 0):
    """Create one synthetic measurement per site with the given true thickness of ``layer``."""
    rng = np.random.default_rng(seed)
    out = []
    for t in site_thickness:
        th = stack.thicknesses.copy()
        th[layer] = t
        s = stack.copy_with(thicknesses=th)
        if recipe.get("technique", "reflectometry") == "se":
            out.append(simulate_se(s, wavelength_nm, recipe.get("angles_deg", (65, 70, 75)),
                                   psi_noise=noise if noise is not None else 0.02,
                                   delta_noise=2 * (noise if noise is not None else 0.02), rng=rng))
        else:
            out.append(simulate_reflectometry(s, wavelength_nm, noise=noise if noise is not None else 0.002, rng=rng))
    return out


def fit_sites(stack: Stack, params: list[FitParameter], measurements, window_nm: float = 15.0,
              chi2_flag: float = 3.0) -> pd.DataFrame:
    """Fit every site. Returns one row per site with values, stderr, chi2_red and a quality flag."""
    rows, seed_vals = [], None
    for i, meas in enumerate(measurements):
        if seed_vals is None:
            res = fit(stack, meas, params)
        else:
            local = [
                FitParameter(fp.layer, fp.target,
                             (max(fp.bounds[0], v - window_nm), min(fp.bounds[1], v + window_nm)) if fp.target == "thickness" else fp.bounds,
                             initial=v)
                for fp, v in zip(params, seed_vals)
            ]
            res = fit(stack, meas, local, n_starts=3)
            res_labels = [fp.label for fp in params]
            res.values = dict(zip(res_labels, res.values.values()))
            res.stderr = dict(zip(res_labels, res.stderr.values()))
        seed_vals = list(res.values.values())
        row = {"site": i + 1, "chi2_red": res.chi2_red, "fit_ok": bool(res.success and res.chi2_red < chi2_flag)}
        for lab in res.values:
            row[lab] = res.values[lab]
            row[lab + "_stderr"] = res.stderr[lab]
        rows.append(row)
    return pd.DataFrame(rows)
