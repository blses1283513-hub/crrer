"""Tool-to-tool (and chamber-to-chamber) matching.

Two questions, answered separately:
1. Offset: is the mean difference practically zero? Use an equivalence test
   (TOST): the 90% CI of the mean paired difference must sit inside
   +/- offset_spec. A plain t-test "p > 0.05" does NOT prove matching.
2. Slope: do the tools track each other across the range? Deming regression
   (both tools have noise, so ordinary least squares would bias the slope).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


def deming_regression(x, y, delta: float = 1.0) -> tuple[float, float]:
    """Deming fit y = a + b x; delta = var(err_y) / var(err_x). Returns (slope, intercept)."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    sxx, syy = np.mean((x - mx) ** 2), np.mean((y - my) ** 2)
    sxy = np.mean((x - mx) * (y - my))
    if sxy == 0:
        return np.nan, np.nan
    b = (syy - delta * sxx + np.sqrt((syy - delta * sxx) ** 2 + 4 * delta * sxy**2)) / (2 * sxy)
    return float(b), float(my - b * mx)


def tool_matching(reference, candidate, offset_spec: float, slope_tol: float = 0.02, alpha: float = 0.05) -> dict:
    """Paired comparison of the same wafers/sites measured on two tools."""
    ref, cand = np.asarray(reference, float), np.asarray(candidate, float)
    d = cand - ref
    n = d.size
    mean, sd = float(d.mean()), float(d.std(ddof=1))
    se = sd / np.sqrt(n)
    tcrit = stats.t.ppf(1 - alpha, n - 1)  # TOST at alpha -> (1-2 alpha) CI
    ci = (mean - tcrit * se, mean + tcrit * se)
    p_lower = stats.t.sf((mean + offset_spec) / se, n - 1)
    p_upper = stats.t.cdf((mean - offset_spec) / se, n - 1)
    slope, intercept = deming_regression(ref, cand)
    equivalent = bool(ci[0] > -offset_spec and ci[1] < offset_spec)
    slope_ok = bool(abs(slope - 1.0) <= slope_tol) if np.isfinite(slope) else False
    return {
        "n": n,
        "mean_offset": mean,
        "sd_difference": sd,
        "ci_90": ci,
        "tost_p_value": float(max(p_lower, p_upper)),
        "paired_t_p_value": float(stats.ttest_rel(cand, ref).pvalue),
        "offset_equivalent": equivalent,
        "deming_slope": slope,
        "deming_intercept": intercept,
        "slope_ok": slope_ok,
        "matched": equivalent and slope_ok,
        "offset_spec": offset_spec,
    }


def fleet_matching(
    df: pd.DataFrame, tool="tool_id", key=("wafer_id", "site"), value="value",
    reference: str | None = None, offset_spec: float = 0.3, slope_tol: float = 0.02,
) -> pd.DataFrame:
    """Compare every tool to a reference tool (or to the fleet median per key)."""
    key = list(key)
    wide = df.pivot_table(index=key, columns=tool, values=value, aggfunc="mean").dropna()
    ref = wide[reference] if reference else wide.median(axis=1)
    rows = []
    for t in wide.columns:
        if t == reference:
            continue
        res = tool_matching(ref, wide[t], offset_spec, slope_tol)
        rows.append({"tool": t, **{kk: res[kk] for kk in (
            "n", "mean_offset", "sd_difference", "deming_slope", "offset_equivalent", "slope_ok", "matched")}})
    return pd.DataFrame(rows)
