"""Guess how an export's columns map to the toolkit's standard fields, and which layout it uses.

Layouts
  long : one row per measurement (columns parameter + value), usually with site x / y -> wafer maps + SPC
  wide : one row per wafer, one column per parameter (e.g. a tool summary or SECOM) -> SPC, yield
"""

from __future__ import annotations

import re

import pandas as pd

FIELDS: dict[str, tuple[str, list[str]]] = {
    "timestamp": ("量測時間", ["timestamp", "time", "date", "datetime", "date_time", "meas_time", "measure_time",
                              "start_time", "time_stamp", "時間", "日期"]),
    "lot_id": ("批號", ["lot_id", "lot", "lotid", "lot_no", "lotno", "lot_number", "lot_name", "批號"]),
    "wafer_id": ("晶圓編號", ["wafer_id", "wafer", "waferid", "wafer_no", "waferno", "wfr", "wfr_id", "wafer_name",
                             "substrate_id", "晶圓"]),
    "slot": ("槽位", ["slot", "slot_no", "slot_id", "slotno"]),
    "parameter": ("量測項目", ["parameter", "param", "item", "measure_item", "meas_item", "parameter_name",
                              "param_name", "measurement_name", "項目"]),
    "value": ("數值", ["value", "val", "result", "meas_value", "measured_value", "measurement", "數值"]),
    "unit": ("單位", ["unit", "units", "uom", "單位"]),
    "site": ("量測點編號", ["site", "site_id", "site_no", "siteno", "point", "point_no", "pt", "pt_no"]),
    "x": ("X 座標 (mm)", ["x", "x_mm", "site_x", "x_pos", "xpos", "x_coord", "x_position", "pos_x"]),
    "y": ("Y 座標 (mm)", ["y", "y_mm", "site_y", "y_pos", "ypos", "y_coord", "y_position", "pos_y"]),
    "tool_id": ("製程機台", ["tool_id", "tool", "eqp", "eqp_id", "equipment", "equipment_id", "entity", "機台"]),
    "chamber_id": ("腔體", ["chamber_id", "chamber", "ch", "chamber_name", "pm", "腔體"]),
    "metro_tool_id": ("量測機台", ["metro_tool_id", "metro_tool", "meas_tool", "metrology_tool", "metro_eqp"]),
    "recipe_id": ("Recipe", ["recipe_id", "recipe", "rcp", "recipe_name"]),
    "process_step": ("製程站點", ["process_step", "step", "operation", "oper", "layer", "站點"]),
    "product": ("產品", ["product", "part", "part_id", "device", "product_id"]),
    "target": ("目標值", ["target", "tgt", "nominal"]),
    "lsl": ("規格下限", ["lsl", "spec_low", "low_spec", "lower_spec", "spec_lo"]),
    "usl": ("規格上限", ["usl", "spec_high", "high_spec", "upper_spec", "spec_hi"]),
}
LONG_ONLY = ("parameter", "value", "unit", "site", "x", "y", "target", "lsl", "usl")
ID_FIELDS = ("timestamp", "lot_id", "wafer_id", "slot", "tool_id", "chamber_id", "metro_tool_id", "recipe_id",
             "process_step", "product")

UNIT_PATTERNS = [
    ("Å", r"(^|[_\s(\[])(a|å|ang|angstrom)s?[)\]]?$"),
    ("nm", r"(^|[_\s(\[])nm[)\]]?$"),
    ("µm", r"(^|[_\s(\[])(um|µm|micron)s?[)\]]?$"),
]
LENGTH_TO_NM = {"nm": 1.0, "Å": 0.1, "µm": 1000.0}


def normalise(name: str) -> str:
    s = re.sub(r"[\(\[].*?[\)\]]", "", str(name)).strip().lower()  # drop "(mm)" style suffixes
    return re.sub(r"[\s\-\.]+", "_", s).strip("_")


def guess_mapping(columns) -> dict[str, str]:
    """Return {standard field: source column} for columns whose name matches a known alias."""
    used, mapping = set(), {}
    norm = {c: normalise(c) for c in columns}
    for field, (_, aliases) in FIELDS.items():
        for col, n in norm.items():
            if col not in used and n in aliases:
                mapping[field] = col
                used.add(col)
                break
    return mapping


def detect_layout(mapping: dict[str, str]) -> str:
    return "long" if {"parameter", "value"} <= set(mapping) else "wide"


def guess_unit(column: str) -> str:
    n = str(column).strip().lower()
    for unit, pattern in UNIT_PATTERNS:
        if re.search(pattern, n):
            return unit
    return ""


def is_counter_name(name) -> bool:
    n = normalise(name)
    return n in ("lot_sequence", "wafer_sequence", "index", "unnamed:_0", "unnamed_0", "id", "row", "no") or \
        n.endswith(("_sequence", "_index"))


def candidate_parameters(df: pd.DataFrame, mapping: dict[str, str]) -> list[str]:
    """Wide layout: numeric columns that are not mapped to an ID field and are not counters."""
    mapped = set(mapping.values())
    out = []
    for c in df.columns:
        if c in mapped or is_counter_name(c):
            continue
        numeric = pd.to_numeric(df[c], errors="coerce")
        if numeric.notna().mean() >= 0.5:
            out.append(c)
    return out


def parameter_table(df: pd.DataFrame, mapping: dict[str, str], layout: str) -> pd.DataFrame:
    """Editable table: one row per parameter with suggested name, unit and include flag."""
    if layout == "long":
        names = [str(v) for v in pd.unique(df[mapping["parameter"]].dropna())]
        unit_col = mapping.get("unit")
        units = {}
        if unit_col:
            first = df.dropna(subset=[mapping["parameter"]]).groupby(mapping["parameter"])[unit_col].first()
            units = {str(k): str(v) for k, v in first.items() if pd.notna(v)}
        rows = [{"source": n, "name": n, "unit": units.get(n, guess_unit(n)), "include": True} for n in names]
    else:
        params = candidate_parameters(df, mapping)
        rows = []
        for c in params:
            values = pd.to_numeric(df[c], errors="coerce")
            counter = bool(values.dropna().is_monotonic_increasing and values.dropna().nunique() == values.notna().sum()
                           and (values.dropna() % 1 == 0).all() and len(values.dropna()) > 20)
            rows.append({"source": c, "name": re.sub(r"[\(\[].*?[\)\]]", "", c).strip() or c,
                         "unit": guess_unit(c), "include": not counter})
    return pd.DataFrame(rows, columns=["source", "name", "unit", "include"])
