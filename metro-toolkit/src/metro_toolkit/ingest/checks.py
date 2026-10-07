"""Data-quality report for an imported table: what is wrong, what was fixed, what to watch."""

from __future__ import annotations

import numpy as np
import pandas as pd

LEVELS = ("error", "warning", "info")


def quality_report(long_df: pd.DataFrame, notes: list[dict] | None = None, max_radius_mm: float = 150.0,
                   min_wafers_for_spc: int = 10) -> dict:
    """Return {"summary": {...}, "issues": [{level, message}, ...]} (errors first)."""
    issues = list(notes or [])
    df = long_df
    n_wafers = df["wafer_id"].nunique()
    per_param = df.groupby("parameter")
    has_xy = df["x"].notna().any() and df["y"].notna().any()

    summary = {
        "rows": int(len(df)),
        "lots": int(df["lot_id"].nunique()),
        "wafers": int(n_wafers),
        "parameters": int(df["parameter"].nunique()),
        "sites_per_wafer": float(df.groupby(["wafer_id", "parameter"]).size().median()) if len(df) else 0.0,
        "time_span": f"{df['timestamp'].min():%Y-%m-%d} → {df['timestamp'].max():%Y-%m-%d}" if len(df) else "",
        "has_site_xy": bool(has_xy),
        "layout": df.attrs.get("layout", ""),
    }
    if not len(df):
        issues.append({"level": "error", "message": "轉換後沒有任何有效資料列"})
        return {"summary": summary, "issues": issues}

    key = ["wafer_id", "parameter", "site"]
    dups = int(df.duplicated(key).sum())
    if dups:
        issues.append({"level": "warning", "message": f"{dups} 筆重複量測（同晶圓、同參數、同量測點）；分析時會一起平均"})

    if has_xy:
        r = np.hypot(df["x"], df["y"])
        out = int((r > max_radius_mm + 1e-6).sum())
        if out:
            issues.append({"level": "warning", "message": f"{out} 個量測點超出 {max_radius_mm:.0f} mm 晶圓半徑：座標單位可能不是 mm，或原點不在晶圓中心"})
        if df["x"].isna().any() or df["y"].isna().any():
            issues.append({"level": "warning", "message": "部分量測點沒有座標，晶圓圖只會使用有座標的點"})
    else:
        issues.append({"level": "info", "message": "沒有量測點座標（每片只有一個值）：可做 SPC、能力分析；無法畫晶圓圖"})

    wafers_per_param = per_param["wafer_id"].nunique()
    few = wafers_per_param[wafers_per_param < min_wafers_for_spc]
    if len(few):
        issues.append({"level": "warning", "message": f"{len(few)} 個參數少於 {min_wafers_for_spc} 片晶圓，SPC 不可靠：" + "、".join(map(str, few.index[:8])) + ("…" if len(few) > 8 else "")})

    std = per_param["value"].std()
    const = std[(std == 0) | std.isna()].index
    if len(const) and n_wafers > 1:
        issues.append({"level": "warning", "message": f"{len(const)} 個參數的值完全不變（可能是設定值或錯誤欄位）：" + "、".join(map(str, const[:8])) + ("…" if len(const) > 8 else "")})

    if {"lsl", "usl"} <= set(df.columns):
        bad = df[(df["lsl"].notna()) & (df["usl"].notna()) & (df["lsl"] >= df["usl"])]
        if len(bad):
            issues.append({"level": "error", "message": f"{len(bad)} 列的規格下限 ≥ 上限，請檢查 LSL / USL 欄位對應"})

    units = df.groupby("parameter")["unit"].nunique()
    mixed = units[units > 1].index
    if len(mixed):
        issues.append({"level": "error", "message": "同一參數出現多種單位，請統一：" + "、".join(map(str, mixed[:8]))})

    if not issues or all(i["level"] == "info" for i in issues):
        issues.append({"level": "info", "message": "沒有發現需要處理的問題"})
    issues.sort(key=lambda i: LEVELS.index(i["level"]))
    return {"summary": summary, "issues": issues}
