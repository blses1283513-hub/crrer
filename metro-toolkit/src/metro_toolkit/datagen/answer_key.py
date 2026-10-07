"""Score analysis results against a simulation's answer key.

score_detection   Did SPC flag the injected events? How many measured wafers late? How many false alarms?
                  Events whose wafers were never measured are reported as "not observable" (a sampling
                  blind spot, not a failure of SPC).
true_drivers      Real yield loss by cause (from the die maps), to compare with SHAP / correlation rankings.
compare_drivers   Rank agreement between a model's ranking and the truth.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..analysis.spc import control_chart, wafer_summary


def spc_flags(long_df: pd.DataFrame, chart: str = "IMR", rules=(1, 2), stats=("mean", "nu_1sigma_pct"),
              phase1: int = 20, group: str = "chamber_id", parameters=None) -> pd.DataFrame:
    """Run per-group control charts like an engineer would; return one row per flagged wafer point."""
    rows = []
    for param, sub in long_df.groupby("parameter"):
        if parameters is not None and param not in parameters:
            continue
        wafers = wafer_summary(sub)
        grp = group if group in wafers and wafers[group].nunique() > 1 and \
            not wafers[group].astype(str).eq("(n/a)").all() else None
        for stat in stats:
            if stat == "nu_1sigma_pct" and wafers["n_sites"].max() <= 1:
                continue
            groups = wafers.groupby(grp) if grp else [("all", wafers)]
            for g, gw in groups:
                gw = gw.sort_values("timestamp")
                y = gw[stat].to_numpy(float)
                if len(y) < 8 or not np.isfinite(y).all():
                    continue
                ch = control_chart(y, chart, phase1=min(phase1, len(y)), rules=rules)
                for i in sorted({v[0] for v in ch.violations}):
                    rows.append({"parameter": param, "stat": stat, "group": g, "wafer_id": gw["wafer_id"].iloc[i],
                                 "timestamp": gw["timestamp"].iloc[i]})
    return pd.DataFrame(rows, columns=["parameter", "stat", "group", "wafer_id", "timestamp"])


def score_detection(flags: pd.DataFrame, events: pd.DataFrame, long_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Per-event detection table + overall summary (detected, delay, false-alarm rate)."""
    points = long_df.groupby("parameter")["wafer_id"].apply(lambda s: list(dict.fromkeys(s)))
    time_of = long_df.groupby(["parameter", "wafer_id"])["timestamp"].min()
    flagged = {p: set(g["wafer_id"]) for p, g in flags.groupby("parameter")} if len(flags) else {}
    by_stat = flags.groupby(["parameter", "wafer_id"])["stat"].agg(lambda s: ", ".join(sorted(set(s)))) if len(flags) else {}

    rows, explained = [], {}
    for _, e in events.iterrows():
        ids = set(str(e["wafer_ids"]).split(";")) - {""}
        params = [p for p in str(e["parameters"]).split(";") if p in points.index]
        best = None
        for p in params:
            seen = [w for w in points[p] if w in ids]
            explained.setdefault(p, set()).update(seen)
            if not seen:
                continue
            seen.sort(key=lambda w: time_of[(p, w)])
            hits = [i for i, w in enumerate(seen) if w in flagged.get(p, set())]
            cand = {"parameter": p, "observable": len(seen), "detected": bool(hits),
                    "delay_wafers": hits[0] if hits else None,
                    "caught_by": by_stat.get((p, seen[hits[0]]), "") if hits else ""}
            if best is None or (cand["detected"] and (not best["detected"] or cand["delay_wafers"] < best["delay_wafers"])):
                best = cand
        if best is None:
            best = {"parameter": ";".join(params), "observable": 0, "detected": False, "delay_wafers": None, "caught_by": ""}
        status = "not observable (no measured wafer)" if best["observable"] == 0 else (
            "detected" if best["detected"] else "missed")
        rows.append({"id": e["id"], "type": e["type"], "where": e["where"], "lots": f"{e['start_lot']}–{e['end_lot']}",
                     **best, "status": status, "yield_impact_pct": 100 * float(e["yield_impact"]),
                     "affects_product": bool(e["affects_product"])})
    table = pd.DataFrame(rows)

    n_points = sum(len(v) for v in points)
    false = sum(len(f - explained.get(p, set())) for p, f in flagged.items())
    observable = table[table["observable"] > 0] if len(table) else table
    summary = {
        "events": len(table),
        "observable": int(len(observable)),
        "detected": int(observable["detected"].sum()) if len(observable) else 0,
        "median_delay_wafers": float(observable["delay_wafers"].dropna().median()) if len(observable) and observable["detected"].any() else None,
        "flagged_points": int(sum(len(v) for v in flagged.values())),
        "false_alarms": int(false),
        "false_alarm_rate_pct": 100.0 * false / n_points if n_points else 0.0,
    }
    return table, summary


def true_drivers(truth_wafers: pd.DataFrame, drivers: pd.DataFrame | None = None) -> pd.DataFrame:
    if drivers is not None:
        return drivers.reset_index(drop=True)
    loss = {c[5:]: 100 * truth_wafers[c].mean() for c in truth_wafers.columns if c.startswith("loss_")}
    return pd.DataFrame({"code": list(loss), "yield_loss_pct": list(loss.values())}).sort_values(
        "yield_loss_pct", ascending=False).reset_index(drop=True)


def compare_drivers(model_ranking: list[str], drivers: pd.DataFrame, top_k: int = 3) -> dict:
    """How well a model's feature ranking matches the true yield-loss ranking (only causes with loss > 0)."""
    truth = [c for c, v in zip(drivers["cause"], drivers["yield_loss_pct"]) if v > 0]
    common = [c for c in model_ranking if c in truth]
    if len(common) < 2:
        return {"top1_match": bool(common and truth and common[0] == truth[0]), "spearman": None,
                "top_k_overlap": len(set(model_ranking[:top_k]) & set(truth[:top_k])), "truth": truth}
    rm = {c: i for i, c in enumerate(common)}
    rt = {c: i for i, c in enumerate([c for c in truth if c in common])}
    d2 = sum((rm[c] - rt[c]) ** 2 for c in common)
    n = len(common)
    return {"top1_match": common[0] == truth[0], "spearman": 1 - 6 * d2 / (n * (n * n - 1)),
            "top_k_overlap": len(set(model_ranking[:top_k]) & set(truth[:top_k])), "truth": truth}
