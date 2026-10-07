"""Turn a mapped export into the toolkit's standard long table (one row per measurement)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .mapping import ID_FIELDS, LENGTH_TO_NM

STANDARD_ORDER = ["timestamp", "product", "lot_id", "wafer_id", "slot", "process_step", "tool_id", "chamber_id",
                  "recipe_id", "metro_tool_id", "parameter", "value", "unit", "site", "x", "y", "target", "lsl", "usl"]


@dataclass
class ImportSpec:
    layout: str  # "long" | "wide"
    mapping: dict[str, str]  # standard field -> source column
    parameters: list[dict] = field(default_factory=list)  # {source, name, unit, include}
    to_nm: bool = True  # convert Å / µm parameters to nm

    def to_dict(self) -> dict:
        return {"layout": self.layout, "mapping": dict(self.mapping), "parameters": list(self.parameters),
                "to_nm": bool(self.to_nm)}

    @classmethod
    def from_dict(cls, d: dict) -> ImportSpec:
        return cls(d["layout"], dict(d["mapping"]), list(d.get("parameters", [])), bool(d.get("to_nm", True)))


def build_long(raw: pd.DataFrame, spec: ImportSpec) -> tuple[pd.DataFrame, list[dict]]:
    """Return (standard long table, notes). Notes are {level, message} dicts for the check report."""
    notes: list[dict] = []
    m = {k: v for k, v in spec.mapping.items() if v}
    params = {str(p["source"]): p for p in spec.parameters}
    include = [s for s, p in params.items() if p.get("include", True)]
    if not include:
        raise ValueError("沒有選擇任何參數（parameters 表格中 include 全部未勾選）")

    if spec.layout == "long":
        if "parameter" not in m or "value" not in m:
            raise ValueError("long 格式需要對應「parameter」與「value」欄位")
        df = raw.rename(columns={v: k for k, v in m.items()})[list(m)].copy()
        df["parameter"] = df["parameter"].astype(str)
        df = df[df["parameter"].isin(include)]
    else:
        ids = [f for f in ID_FIELDS if f in m]
        id_df = raw[[m[f] for f in ids]].copy()
        id_df.columns = ids
        id_df["_row"] = np.arange(len(raw))
        values = raw[include].copy()
        values["_row"] = np.arange(len(raw))
        df = id_df.merge(values, on="_row").melt(id_vars=ids + ["_row"], var_name="parameter", value_name="value")

    # identifiers
    if "wafer_id" not in df:
        if spec.layout == "long":
            raise ValueError("long 格式需要對應「wafer_id」欄位（否則無法把量測點歸到晶圓）")
        df["wafer_id"] = [f"W{r + 1:05d}" for r in df["_row"]]
        notes.append({"level": "warning", "message": "沒有晶圓編號欄位：以資料列順序產生 W00001, W00002, …"})
    if "lot_id" not in df:
        df["lot_id"] = "LOT1"
        notes.append({"level": "warning", "message": "沒有批號欄位：全部歸為 LOT1"})
    for c in ("lot_id", "wafer_id", "tool_id", "chamber_id", "metro_tool_id", "recipe_id", "process_step", "product"):
        if c in df:
            df[c] = df[c].astype("string").fillna("(blank)")

    # time
    if "timestamp" in df:
        ts = pd.to_datetime(df["timestamp"], errors="coerce")
        bad = int(ts.isna().sum())
        if bad:
            notes.append({"level": "warning", "message": f"{bad} 筆時間無法解析，已移除這些列"})
        df["timestamp"] = ts
        df = df[ts.notna()]
    else:
        order = df["_row"] if "_row" in df else pd.Series(np.arange(len(df)), index=df.index)
        df["timestamp"] = pd.Timestamp("2000-01-01") + pd.to_timedelta(order, unit="m")
        notes.append({"level": "warning", "message": "沒有時間欄位：以資料列順序代替時間（SPC 依此順序）"})

    # values
    num = pd.to_numeric(df["value"], errors="coerce")
    bad = int((num.isna() & df["value"].notna()).sum())
    if bad:
        notes.append({"level": "warning", "message": f"{bad} 個非數值的儲存格（如 'N/A'、'---'）視為缺值"})
    df["value"] = num
    missing = int(df["value"].isna().sum())
    if missing:
        notes.append({"level": "info", "message": f"移除 {missing} 筆缺值（空白或非數值）"})
        df = df[df["value"].notna()]

    # names and units
    if spec.layout == "wide" or "unit" not in df:
        df["unit"] = df["parameter"].map(lambda s: params.get(s, {}).get("unit", "") or "")
    df["unit"] = df["unit"].fillna("").astype(str)
    if spec.to_nm:
        factor = df["unit"].map(lambda u: LENGTH_TO_NM.get(u.replace("A", "Å").replace("um", "µm"), np.nan))
        conv = factor.notna() & (factor != 1.0)
        if conv.any():
            df.loc[conv, "value"] = df.loc[conv, "value"] * factor[conv]
            for col in ("target", "lsl", "usl"):
                if col in df:
                    df.loc[conv, col] = pd.to_numeric(df.loc[conv, col], errors="coerce") * factor[conv]
            converted = sorted(set(df.loc[conv, "parameter"]))
            df.loc[conv, "unit"] = "nm"
            notes.append({"level": "info", "message": "單位換算成 nm：" + "、".join(converted)})
    df["parameter"] = df["parameter"].map(lambda s: str(params.get(s, {}).get("name") or s))

    # sites
    for c in ("x", "y", "target", "lsl", "usl"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "x" not in df or "y" not in df:
        df["x"], df["y"] = np.nan, np.nan
    if "site" not in df:
        df["site"] = df.groupby(["wafer_id", "parameter"]).cumcount() + 1

    df = df.drop(columns=[c for c in ("_row",) if c in df]).sort_values("timestamp", kind="stable")
    cols = [c for c in STANDARD_ORDER if c in df] + [c for c in df.columns if c not in STANDARD_ORDER]
    out = df[cols].reset_index(drop=True)
    out.attrs["layout"] = spec.layout
    return out, notes


def wafer_table(long_df: pd.DataFrame) -> pd.DataFrame:
    """One row per wafer, one column per parameter (wafer mean). Used by SemiYield's pages."""
    keys = ["lot_id", "wafer_id"]
    wide = long_df.pivot_table(index=keys, columns="parameter", values="value", aggfunc="mean").reset_index()
    wide.columns.name = None
    extra = long_df.groupby(keys).agg(
        timestamp=("timestamp", "min"),
        **{c: (c, "first") for c in ("tool_id", "chamber_id", "metro_tool_id") if c in long_df},
    ).reset_index()
    wide = extra.merge(wide, on=keys).sort_values("timestamp", kind="stable").reset_index(drop=True)
    lot_order = {lot: i for i, lot in enumerate(pd.unique(wide["lot_id"]))}
    wide.insert(2, "lot_sequence", wide["lot_id"].map(lot_order))
    wide.insert(3, "wafer_sequence", np.arange(len(wide)))
    return wide


def spec_table(long_df: pd.DataFrame) -> dict[str, dict]:
    """Per-parameter spec limits carried by the export (if lsl / usl / target were mapped)."""
    out = {}
    cols = [c for c in ("target", "lsl", "usl") if c in long_df]
    if not cols:
        return out
    for p, g in long_df.groupby("parameter"):
        rec = {c: float(g[c].dropna().median()) for c in cols if g[c].notna().any()}
        if rec.get("lsl") is not None or rec.get("usl") is not None:
            out[str(p)] = rec
    return out
