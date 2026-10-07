"""Crossed Gauge R&R by two-way ANOVA (AIAG MSA 4th edition method).

In a metrology context the "operators" are usually tools, chambers of a
multi-head tool, or independent load/unload sessions; the "parts" are wafers
or sites that span the process range.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats


def gauge_rr(
    df: pd.DataFrame,
    part: str = "part",
    operator: str = "operator",
    value: str = "value",
    lsl: float | None = None,
    usl: float | None = None,
    k: float = 6.0,
    alpha_interaction: float = 0.05,
    accept_pct: float = 10.0,
    marginal_pct: float = 30.0,
) -> dict:
    """Return variance components, %StudyVar, %Tolerance (P/T), ndc and a verdict.

    Requires a balanced design: every part measured by every operator r times.
    The part x operator interaction is pooled into repeatability when its
    p-value exceeds ``alpha_interaction`` (Minitab default behaviour).
    """
    counts = df.groupby([part, operator])[value].size()
    if counts.nunique() != 1:
        raise ValueError("gauge_rr needs a balanced design (same replicate count in every cell)")
    p, o, r = df[part].nunique(), df[operator].nunique(), int(counts.iloc[0])
    if r < 2:
        raise ValueError("need at least 2 replicates per part/operator")

    y = df[value].to_numpy(float)
    grand = y.mean()
    m_p = df.groupby(part)[value].mean()
    m_o = df.groupby(operator)[value].mean()
    m_po = df.groupby([part, operator])[value].mean()

    ss_p = o * r * np.sum((m_p - grand) ** 2)
    ss_o = p * r * np.sum((m_o - grand) ** 2)
    cell = m_po.reset_index(name="m")
    inter = cell["m"] - cell[part].map(m_p) - cell[operator].map(m_o) + grand
    ss_po = r * np.sum(inter**2)
    ss_e = np.sum((df[value] - pd.MultiIndex.from_frame(df[[part, operator]]).map(m_po)) ** 2)

    df_p, df_o, df_po, df_e = p - 1, o - 1, (p - 1) * (o - 1), p * o * (r - 1)
    ms_p, ms_o, ms_e = ss_p / df_p, ss_o / max(df_o, 1), ss_e / df_e
    ms_po = ss_po / max(df_po, 1)
    f_po = ms_po / ms_e if ms_e > 0 else np.inf
    p_po = float(stats.f.sf(f_po, df_po, df_e)) if df_po > 0 else 1.0

    pooled = p_po > alpha_interaction
    if pooled:
        ms_err = (ss_po + ss_e) / (df_po + df_e)
        var_e, var_po = ms_err, 0.0
        var_o = max((ms_o - ms_err) / (p * r), 0.0)
        var_p = max((ms_p - ms_err) / (o * r), 0.0)
    else:
        var_e = ms_e
        var_po = max((ms_po - ms_e) / r, 0.0)
        var_o = max((ms_o - ms_po) / (p * r), 0.0)
        var_p = max((ms_p - ms_po) / (o * r), 0.0)

    var_reprod = var_o + var_po
    var_grr = var_e + var_reprod
    var_total = var_grr + var_p
    comp = {
        "repeatability": var_e,
        "reproducibility": var_reprod,
        "operator": var_o,
        "part_x_operator": var_po,
        "gauge_rr": var_grr,
        "part_to_part": var_p,
        "total": var_total,
    }
    sd = {kk: math.sqrt(v) for kk, v in comp.items()}
    pct_sv = {kk: 100.0 * sd[kk] / sd["total"] if sd["total"] else np.nan for kk in comp}
    out = {
        "design": {"parts": p, "operators": o, "replicates": r},
        "variance": comp,
        "std": sd,
        "pct_study_var": pct_sv,
        "interaction_p_value": p_po,
        "interaction_pooled": pooled,
        "ndc": int(math.floor(1.41 * sd["part_to_part"] / sd["gauge_rr"])) if sd["gauge_rr"] else np.inf,
        "k": k,
    }
    if lsl is not None and usl is not None:
        tol = usl - lsl
        out["pct_tolerance"] = {kk: 100.0 * k * sd[kk] / tol for kk in ("repeatability", "reproducibility", "gauge_rr")}
        headline = out["pct_tolerance"]["gauge_rr"]
    else:
        headline = pct_sv["gauge_rr"]
    out["headline_pct"] = headline
    out["verdict"] = "acceptable" if headline < accept_pct else "marginal" if headline < marginal_pct else "unacceptable"
    return out
