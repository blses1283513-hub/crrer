"""Standard long-format measurement schema and validation.

One row per measured site. Required columns let every module (SPC, wafer
maps, matching) consume the same table; optional columns enable tool/chamber
breakdowns. Map your fab export to these names once, in a loader, and keep
the analysis code unchanged.
"""

from __future__ import annotations

import pandas as pd

REQUIRED = ["timestamp", "lot_id", "wafer_id", "parameter", "value", "x", "y"]
OPTIONAL = ["product", "technology", "slot", "process_step", "tool_id", "chamber_id", "recipe_id",
            "metro_tool_id", "unit", "site", "target", "lsl", "usl"]


def validate(df: pd.DataFrame, max_radius_mm: float = 150.0) -> list[str]:
    """Return a list of human-readable problems (empty list = OK)."""
    problems = [f"missing required column '{c}'" for c in REQUIRED if c not in df.columns]
    if problems:
        return problems
    if df["value"].isna().any():
        problems.append(f"{int(df['value'].isna().sum())} rows with empty value")
    if not pd.api.types.is_numeric_dtype(df["value"]):
        problems.append("column 'value' is not numeric")
    if pd.to_datetime(df["timestamp"], errors="coerce").isna().any():
        problems.append("unparseable timestamps")
    r = (df["x"] ** 2 + df["y"] ** 2) ** 0.5
    if (r > max_radius_mm + 1e-6).any():
        problems.append(f"{int((r > max_radius_mm).sum())} sites outside the {max_radius_mm:.0f} mm wafer radius")
    key = ["wafer_id", "parameter"] + (["site"] if "site" in df.columns else ["x", "y"])
    dups = df.duplicated(key).sum()
    if dups:
        problems.append(f"{int(dups)} duplicate site measurements (same wafer/parameter/site)")
    return problems


def load_measurements(path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df
