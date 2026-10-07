"""Within-wafer uniformity metrics and spatial signature decomposition.

Uniformity definitions differ between fabs and tool vendors, so report which one
you use. All three common ones are returned:

    nu_1sigma_pct     = 100 * std / mean               (most common for thickness)
    range_pct         = 100 * (max - min) / mean
    half_range_pct    = 100 * (max - min) / (2 * mean) ("+/- %" convention)

Zernike decomposition turns a site map into a few physically meaningful numbers
(the "signature"): piston = mean, tilt = left/right or top/bottom gradient
(gas flow, chuck tilt), bowl/defocus = centre-to-edge (temperature, plasma
density), astigmatism = saddle, spherical = edge roll-off / ring.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.interpolate import RBFInterpolator

ZERNIKE_TERMS = {
    "piston": lambda rho, th: np.ones_like(rho),
    "tilt_x": lambda rho, th: rho * np.cos(th),
    "tilt_y": lambda rho, th: rho * np.sin(th),
    "bowl": lambda rho, th: 2 * rho**2 - 1,
    "astig_0": lambda rho, th: rho**2 * np.cos(2 * th),
    "astig_45": lambda rho, th: rho**2 * np.sin(2 * th),
    "edge_roll": lambda rho, th: 6 * rho**4 - 6 * rho**2 + 1,
}


def uniformity_metrics(values) -> dict[str, float]:
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    mean, std = float(v.mean()), float(v.std(ddof=1)) if v.size > 1 else 0.0
    vmin, vmax = float(v.min()), float(v.max())
    return {
        "n_sites": int(v.size),
        "mean": mean,
        "std": std,
        "min": vmin,
        "max": vmax,
        "range": vmax - vmin,
        "nu_1sigma_pct": 100.0 * std / mean if mean else np.nan,
        "range_pct": 100.0 * (vmax - vmin) / mean if mean else np.nan,
        "half_range_pct": 100.0 * (vmax - vmin) / (2.0 * mean) if mean else np.nan,
    }


def center_to_edge(x_mm, y_mm, values, edge_frac: float = 0.9, r_eff_mm: float | None = None) -> float:
    """Mean of sites beyond ``edge_frac * R`` minus the mean of the centre-most site(s)."""
    x, y, v = (np.asarray(a, float) for a in (x_mm, y_mm, values))
    r = np.hypot(x, y)
    r_eff = r_eff_mm or r.max()
    centre = v[r <= r.min() + 1e-6].mean()
    edge = v[r >= edge_frac * r_eff]
    return float(edge.mean() - centre) if edge.size else np.nan


def radial_profile(x_mm, y_mm, values, n_bins: int = 6) -> pd.DataFrame:
    x, y, v = (np.asarray(a, float) for a in (x_mm, y_mm, values))
    r = np.hypot(x, y)
    edges = np.linspace(0, r.max() + 1e-9, n_bins + 1)
    idx = np.clip(np.digitize(r, edges) - 1, 0, n_bins - 1)
    df = pd.DataFrame({"r_bin": idx, "r_mm": r, "value": v})
    out = df.groupby("r_bin").agg(r_mm=("r_mm", "mean"), mean=("value", "mean"), std=("value", "std"), n=("value", "size"))
    return out.reset_index(drop=True)


def zernike_decompose(x_mm, y_mm, values, radius_mm: float | None = None, terms=None) -> dict:
    """Least-squares fit of low-order Zernike terms. Coefficients are in data units.

    The number of terms is capped at n_sites - 2 so a sparse plan is not over-fitted.
    """
    x, y, v = (np.asarray(a, float) for a in (x_mm, y_mm, values))
    radius = radius_mm or max(np.hypot(x, y).max(), 1e-9)
    rho, th = np.hypot(x, y) / radius, np.arctan2(y, x)
    names = list(terms or ZERNIKE_TERMS)[: max(1, v.size - 2)]
    A = np.column_stack([ZERNIKE_TERMS[n](rho, th) for n in names])
    coef, *_ = np.linalg.lstsq(A, v, rcond=None)
    fitted = A @ coef
    resid = v - fitted
    ss_tot = np.sum((v - v.mean()) ** 2)
    return {
        "coefficients": dict(zip(names, coef.tolist())),
        "fitted": fitted,
        "residual_std": float(resid.std(ddof=min(len(names), v.size - 1))) if v.size > len(names) else 0.0,
        "r2": float(1 - np.sum(resid**2) / ss_tot) if ss_tot > 0 else 1.0,
        "radius_mm": radius,
    }


def interpolate_map(x_mm, y_mm, values, radius_mm: float, grid: int = 121, smoothing: float = 0.0):
    """Thin-plate-spline interpolation of a site map onto a square grid (NaN outside the wafer)."""
    pts = np.column_stack([x_mm, y_mm]).astype(float)
    rbf = RBFInterpolator(pts, np.asarray(values, float), kernel="thin_plate_spline", smoothing=smoothing)
    g = np.linspace(-radius_mm, radius_mm, grid)
    X, Y = np.meshgrid(g, g)
    Z = rbf(np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    Z[np.hypot(X, Y) > radius_mm] = np.nan
    return X, Y, Z
