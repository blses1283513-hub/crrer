"""SPC for metrology data: control charts, Western Electric rules, capability.

Adapted from SemiYield (https://github.com/OutBlade/semiyield,
semiyield/spc/control_charts.py, commit 2f31373), MIT License,
Copyright (c) SemiYield Contributors. See NOTICE.md.

Changes from upstream:
* EWMA and CUSUM use the short-term (moving-range) sigma instead of the overall
  standard deviation, so a drifting Phase I does not inflate its own limits.
* EWMA uses exact time-varying limits and returns the full statistic series.
* Western Electric rules 1-4 by default (the classic WECO set); the Nelson
  extensions 5-8 remain available via ``rules=``.
* Thickness-specific helpers: per-wafer summaries, and per-chamber charts of
  wafer mean and within-wafer sigma.

References: Montgomery, Introduction to Statistical Quality Control, 7th ed.;
AIAG SPC Reference Manual, 2nd ed. (2005).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

_D2 = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078}
_C4 = {2: 0.7979, 3: 0.8862, 4: 0.9213, 5: 0.9400, 6: 0.9515, 7: 0.9594, 8: 0.9650, 9: 0.9693, 10: 0.9727}
_A2 = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}

RULE_TEXT = {
    1: "1 point beyond 3 sigma",
    2: "2 of 3 beyond 2 sigma (same side)",
    3: "4 of 5 beyond 1 sigma (same side)",
    4: "8 in a row on one side of CL",
    5: "6 in a row trending",
    6: "15 in a row within 1 sigma (stratification)",
    7: "14 in a row alternating",
    8: "8 in a row beyond 1 sigma (mixture)",
}


def sigma_short_term(x) -> float:
    """Moving-range estimate of short-term sigma: MR_bar / d2(2)."""
    x = np.asarray(x, float)
    return float(np.mean(np.abs(np.diff(x))) / _D2[2]) if x.size > 1 else 0.0


@dataclass
class ChartResult:
    chart_type: str
    statistic: np.ndarray
    cl: float
    ucl: np.ndarray
    lcl: np.ndarray
    sigma: float
    violations: list[tuple[int, int, str]] = field(default_factory=list)

    @property
    def out_of_control(self) -> np.ndarray:
        idx = sorted({v[0] for v in self.violations})
        return np.array(idx, dtype=int)


def control_chart(
    data,
    chart_type: str = "IMR",
    phase1: int | None = None,
    subgroup_size: int = 5,
    ewma_lambda: float = 0.2,
    L: float = 3.0,
    cusum_k: float = 0.5,
    cusum_h: float = 5.0,
    target: float | None = None,
    rules=(1, 2, 3, 4),
) -> ChartResult:
    """Compute a control chart. Limits come from the first ``phase1`` points (default: all)."""
    x = np.asarray(data, float)
    base = x[: phase1 or len(x)]

    if chart_type in ("XbarR", "XbarS"):
        n = subgroup_size
        if not 2 <= n <= 10:
            raise ValueError("subgroup_size must be 2-10")
        groups = x[: len(x) // n * n].reshape(-1, n)
        gbase = base[: len(base) // n * n].reshape(-1, n)
        stat = groups.mean(axis=1)
        cl = float(gbase.mean()) if target is None else target
        if chart_type == "XbarR":
            rbar = float(np.ptp(gbase, axis=1).mean())
            sigma, half = rbar / _D2[n], _A2[n] * rbar
        else:
            sbar = float(gbase.std(axis=1, ddof=1).mean())
            sigma = sbar / _C4[n]
            half = 3.0 * sigma / np.sqrt(n)
        ucl, lcl = np.full(stat.size, cl + half), np.full(stat.size, cl - half)
        res = ChartResult(chart_type, stat, cl, ucl, lcl, sigma)
        res.violations = western_electric(stat, cl, half / 3.0, rules)
        return res

    sigma = sigma_short_term(base)
    cl = float(base.mean()) if target is None else target

    if chart_type == "IMR":
        ucl, lcl = np.full(x.size, cl + L * sigma), np.full(x.size, cl - L * sigma)
        res = ChartResult("IMR", x, cl, ucl, lcl, sigma)
        res.violations = western_electric(x, cl, sigma, rules)
        return res

    if chart_type == "EWMA":
        lam = ewma_lambda
        z = np.empty_like(x)
        prev = cl
        for i, xi in enumerate(x):
            prev = lam * xi + (1 - lam) * prev
            z[i] = prev
        i = np.arange(1, x.size + 1)
        half = L * sigma * np.sqrt(lam / (2 - lam) * (1 - (1 - lam) ** (2 * i)))
        res = ChartResult("EWMA", z, cl, cl + half, cl - half, sigma)
        res.violations = [(int(j), 1, "EWMA beyond limit") for j in np.where((z > cl + half) | (z < cl - half))[0]]
        return res

    if chart_type == "CUSUM":
        k, h = cusum_k * sigma, cusum_h * sigma
        cp, cm = np.zeros_like(x), np.zeros_like(x)
        sp = sm = 0.0
        for i, xi in enumerate(x):
            sp = max(0.0, sp + xi - cl - k)
            sm = max(0.0, sm - (xi - cl) - k)
            cp[i], cm[i] = sp, sm
        stat = cp - cm  # signed display: upper positive, lower negative
        res = ChartResult("CUSUM", stat, 0.0, np.full(x.size, h), np.full(x.size, -h), sigma)
        res.violations = [(int(j), 1, "CUSUM beyond decision interval") for j in np.where((cp > h) | (cm > h))[0]]
        return res

    raise ValueError(f"unknown chart_type {chart_type}")


def western_electric(data, cl: float, sigma: float, rules=(1, 2, 3, 4)) -> list[tuple[int, int, str]]:
    """Return (index, rule, text) for each violation (index = last point of the run)."""
    x = np.asarray(data, float)
    z = (x - cl) / sigma if sigma > 0 else np.zeros_like(x)
    out: list[tuple[int, int, str]] = []

    def run(i, w):
        return z[i - w + 1 : i + 1] if i >= w - 1 else None

    for i in range(x.size):
        if 1 in rules and abs(z[i]) > 3:
            out.append((i, 1, RULE_TEXT[1]))
        if 2 in rules and (w := run(i, 3)) is not None and (np.sum(w > 2) >= 2 or np.sum(w < -2) >= 2):
            out.append((i, 2, RULE_TEXT[2]))
        if 3 in rules and (w := run(i, 5)) is not None and (np.sum(w > 1) >= 4 or np.sum(w < -1) >= 4):
            out.append((i, 3, RULE_TEXT[3]))
        if 4 in rules and (w := run(i, 8)) is not None and (np.all(w > 0) or np.all(w < 0)):
            out.append((i, 4, RULE_TEXT[4]))
        if 5 in rules and (w := run(i, 6)) is not None and (np.all(np.diff(w) > 0) or np.all(np.diff(w) < 0)):
            out.append((i, 5, RULE_TEXT[5]))
        if 6 in rules and (w := run(i, 15)) is not None and np.all(np.abs(w) < 1):
            out.append((i, 6, RULE_TEXT[6]))
        if 7 in rules and (w := run(i, 14)) is not None:
            s = np.sign(np.diff(w))
            if np.all(s[:-1] * s[1:] < 0):
                out.append((i, 7, RULE_TEXT[7]))
        if 8 in rules and (w := run(i, 8)) is not None and np.all(np.abs(w) > 1):
            out.append((i, 8, RULE_TEXT[8]))
    return out


def process_capability(data, lsl: float, usl: float) -> dict[str, float]:
    """Cp/Cpk (short-term sigma, moving range) and Pp/Ppk (overall sigma)."""
    x = np.asarray(data, float)
    mu, s_lt, s_st = float(x.mean()), float(x.std(ddof=1)), sigma_short_term(x)

    def div(a, b):
        return a / b if b > 1e-15 else float("inf")

    return {
        "mean": mu,
        "sigma_within": s_st,
        "sigma_overall": s_lt,
        "Cp": div(usl - lsl, 6 * s_st),
        "Cpk": min(div(usl - mu, 3 * s_st), div(mu - lsl, 3 * s_st)),
        "Pp": div(usl - lsl, 6 * s_lt),
        "Ppk": min(div(usl - mu, 3 * s_lt), div(mu - lsl, 3 * s_lt)),
    }


# --------------------------------------------------------------------------- #
# Thickness-specific helpers                                                  #
# --------------------------------------------------------------------------- #

WAFER_KEYS = ["lot_id", "wafer_id", "tool_id", "chamber_id", "parameter"]


def wafer_summary(df: pd.DataFrame, value: str = "value") -> pd.DataFrame:
    """Collapse site-level rows (standard schema) to one row per wafer."""
    keys = [k for k in WAFER_KEYS if k in df.columns]
    g = df.groupby(keys, sort=False, dropna=False)  # keep wafers whose tool/chamber is blank
    extra = {"metro_tool_id": ("metro_tool_id", "first")} if "metro_tool_id" in df.columns else {}
    out = g.agg(
        timestamp=("timestamp", "min"),
        mean=(value, "mean"),
        std=(value, "std"),
        min=(value, "min"),
        max=(value, "max"),
        n_sites=(value, "size"),
        **extra,  # which metrology tool measured the wafer: lets SPC group by metrology tool (gauge vs process)
    ).reset_index()
    out["nu_1sigma_pct"] = 100 * out["std"] / out["mean"]
    out["range"] = out["max"] - out["min"]
    return out.sort_values("timestamp").reset_index(drop=True)


def spc_by_group(
    wafers: pd.DataFrame, group: str = "chamber_id", value: str = "mean",
    chart_type: str = "IMR", phase1: int = 20, rules=(1, 2, 3, 4),
) -> dict[str, ChartResult]:
    """Independent control chart per chamber/tool (each has its own baseline)."""
    charts = {}
    for name, sub in wafers.sort_values("timestamp").groupby(group):
        if len(sub) < 3:
            continue
        charts[name] = control_chart(sub[value].to_numpy(), chart_type, phase1=min(phase1, len(sub)), rules=rules)
    return charts
