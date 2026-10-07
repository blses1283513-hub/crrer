"""Gauge precision: static / dynamic repeatability and long-term stability.

static   : N repeats on the same site without unloading (pure measurement noise)
dynamic  : the same site across load/unload cycles (adds wafer placement, focus,
           pattern recognition, and alignment errors)
stability: a reference/monitor wafer measured daily for weeks (adds drift, lamp
           ageing, calibration changes)

Precision is usually quoted as 3-sigma; P/T = k*sigma / (USL - LSL).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def _pooled_std(df: pd.DataFrame, group: str, value: str) -> tuple[float, int]:
    g = df.groupby(group)[value]
    var = g.var(ddof=1)
    n = g.size()
    dof = (n - 1).sum()
    return float(np.sqrt(((n - 1) * var).sum() / dof)), int(dof)


def _pt(sigma, lsl, usl, k):
    return 100.0 * k * sigma / (usl - lsl) if lsl is not None and usl is not None else None


def static_repeatability(df, site="site", value="value", lsl=None, usl=None, k=6.0) -> dict:
    """Pooled within-site sigma of back-to-back repeats (no unload)."""
    sigma, dof = _pooled_std(df, site, value)
    return {"sigma": sigma, "three_sigma": 3 * sigma, "dof": dof, "pt_pct": _pt(sigma, lsl, usl, k)}


def dynamic_repeatability(df, site="site", cycle="cycle", value="value", lsl=None, usl=None, k=6.0) -> dict:
    """Split precision into static and load/unload parts.

    ``df`` holds repeats within each load cycle (cycle column) at each site.
    sigma_dynamic^2 = sigma_static^2 + sigma_load^2.
    """
    static, _ = _pooled_std(df.assign(_g=df[site].astype(str) + "|" + df[cycle].astype(str)), "_g", value)
    cycle_means = df.groupby([site, cycle])[value].mean().reset_index()
    n_rep = df.groupby([site, cycle])[value].size().mean()
    between, _ = _pooled_std(cycle_means, site, value)
    # cycle means carry static/n_rep of within-cycle noise
    load_var = max(between**2 - static**2 / n_rep, 0.0)
    dynamic = float(np.sqrt(static**2 + load_var))
    return {
        "sigma_static": static,
        "sigma_load": float(np.sqrt(load_var)),
        "sigma_dynamic": dynamic,
        "three_sigma_dynamic": 3 * dynamic,
        "pt_pct": _pt(dynamic, lsl, usl, k),
    }


def long_term_stability(df, time="timestamp", value="value", lsl=None, usl=None, k=6.0, alpha=0.05) -> dict:
    """Trend test and sigma of a monitor-wafer series. Drift reported per day."""
    t = pd.to_datetime(df[time])
    days = (t - t.min()).dt.total_seconds().to_numpy() / 86400.0
    y = df[value].to_numpy(float)
    lr = stats.linregress(days, y)
    resid = y - (lr.intercept + lr.slope * days)
    sigma_total = float(y.std(ddof=1))
    return {
        "n": int(y.size),
        "span_days": float(days.max()),
        "mean": float(y.mean()),
        "sigma_total": sigma_total,
        "sigma_detrended": float(resid.std(ddof=2)),
        "drift_per_day": float(lr.slope),
        "drift_p_value": float(lr.pvalue),
        "significant_drift": bool(lr.pvalue < alpha),
        "pt_pct": _pt(sigma_total, lsl, usl, k),
    }
