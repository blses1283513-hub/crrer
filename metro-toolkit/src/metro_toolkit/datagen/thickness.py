"""Synthetic thin-film thickness data for practice without fab data.

Ideas borrowed from WaferLens (MIT, simulate/measurements.py: sampled wafers x
sites, radial profile, chamber bias) and SemiYield (MIT, datagen: lot drift,
equipment ageing). Written fresh; see NOTICE.md.

What is simulated (all configurable):
* chamber static offset and spatial signature (bowl, tilt, edge roll-off)
* deposition-rate drift with chamber age, reset at each PM (saw-tooth)
* wafer-to-wafer noise and site-level metrology noise
* injected excursions with a ground-truth table, so you can score detection

Output follows the toolkit's standard long schema (one row per site):
timestamp, product, technology, lot_id, wafer_id, slot, process_step, tool_id,
chamber_id, recipe_id, metro_tool_id, parameter, value, unit, site, x, y,
target, lsl, usl
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..wafer.sampling import sampling_plan
from ..wafer.uniformity import ZERNIKE_TERMS


@dataclass
class Excursion:
    chamber_id: str
    start_lot: int
    n_lots: int
    kind: str = "shift"  # 'shift' (nm) | 'bowl' (nm of centre-to-edge) | 'noise' (x site noise)
    magnitude: float = 1.0


@dataclass
class ThicknessSimConfig:
    parameter: str = "ox_thickness_nm"
    unit: str = "nm"
    target: float = 100.0
    lsl: float = 98.5
    usl: float = 101.5
    product: str = "DRAM-DEMO"
    technology: str = "1-gamma-demo"
    process_step: str = "OX_DEP"
    recipe_id: str = "OX100_V1"
    tools: dict[str, int] = field(default_factory=lambda: {"DEP01": 2, "DEP02": 2})
    metro_tools: tuple[str, ...] = ("FT01", "FT02")
    n_lots: int = 60
    wafers_per_lot: int = 25
    sampled_wafers: tuple[int, ...] = (1, 6, 13, 18, 25)  # mix of odd/even slots -> both chambers
    plan: str = "49"
    start: str = "2026-09-01 06:00"
    hours_between_lots: float = 4.0
    chamber_offset_sigma: float = 0.35
    bowl_mean: float = -0.8  # nm, negative = thinner at edge
    bowl_sigma: float = 0.25
    tilt_sigma: float = 0.15
    edge_roll: float = -0.25
    drift_per_lot: float = -0.012  # nm per lot through a chamber since PM
    pm_every_lots: int = 25
    wafer_sigma: float = 0.20
    site_sigma: float = 0.12  # metrology + local process noise
    metro_offsets: dict[str, float] = field(default_factory=lambda: {"FT01": 0.0, "FT02": 0.08})
    excursions: list[Excursion] = field(default_factory=list)
    seed: int = 7


def simulate_thickness(cfg: ThicknessSimConfig | None = None, sampling_cfg: dict | None = None):
    """Return (site_df, truth_df). truth_df lists injected excursions per affected wafer."""
    cfg = cfg or ThicknessSimConfig()
    rng = np.random.default_rng(cfg.seed)
    sites = sampling_plan(cfg.plan, sampling_cfg)
    radius = sites.attrs["r_eff_mm"]
    rho = sites["r_mm"].to_numpy() / radius
    th = np.deg2rad(sites["theta_deg"].to_numpy())
    z_bowl = ZERNIKE_TERMS["bowl"](rho, th)
    z_edge = ZERNIKE_TERMS["edge_roll"](rho, th)

    chambers = [(t, f"{t}-{chr(65 + c)}") for t, n in cfg.tools.items() for c in range(n)]
    sig = {
        ch: {
            "offset": rng.normal(0, cfg.chamber_offset_sigma),
            "bowl": rng.normal(cfg.bowl_mean, cfg.bowl_sigma),
            "tx": rng.normal(0, cfg.tilt_sigma),
            "ty": rng.normal(0, cfg.tilt_sigma),
            "age": int(rng.integers(0, cfg.pm_every_lots)),
        }
        for _, ch in chambers
    }

    t0 = pd.Timestamp(cfg.start)
    tool_names = list(cfg.tools)
    rows, truth = [], []
    for lot_no in range(cfg.n_lots):
        tool = tool_names[lot_no % len(tool_names)]
        tool_ch = [ch for t, ch in chambers if t == tool]
        lot_id = f"L{lot_no + 1:04d}"
        lot_time = t0 + pd.Timedelta(hours=lot_no * cfg.hours_between_lots + rng.uniform(0, 1))
        metro = cfg.metro_tools[lot_no % len(cfg.metro_tools)]
        for ch in tool_ch:  # each chamber sees the lot once -> ages by one lot
            sig[ch]["age"] = (sig[ch]["age"] + 1) % cfg.pm_every_lots
        for slot in cfg.sampled_wafers:
            ch = tool_ch[(slot - 1) % len(tool_ch)]
            s = sig[ch]
            wafer_mean = cfg.target + s["offset"] + cfg.drift_per_lot * s["age"] + rng.normal(0, cfg.wafer_sigma)
            bowl, site_sigma = s["bowl"], cfg.site_sigma
            for ex in cfg.excursions:
                if ex.chamber_id == ch and ex.start_lot <= lot_no < ex.start_lot + ex.n_lots:
                    if ex.kind == "shift":
                        wafer_mean += ex.magnitude
                    elif ex.kind == "bowl":
                        bowl += ex.magnitude
                    elif ex.kind == "noise":
                        site_sigma *= ex.magnitude
                    truth.append({"lot_id": lot_id, "wafer_id": f"{lot_id}.{slot:02d}", "chamber_id": ch,
                                  "kind": ex.kind, "magnitude": ex.magnitude})
            # bowl coefficient expressed as centre-to-edge delta: Z4 spans -1..+1 -> /2
            profile = (bowl / 2.0) * z_bowl + cfg.edge_roll * z_edge / 2.0 + s["tx"] * rho * np.cos(th) + s["ty"] * rho * np.sin(th)
            values = wafer_mean + profile - profile.mean() + rng.normal(0, site_sigma, rho.size) + cfg.metro_offsets.get(metro, 0.0)
            ts = lot_time + pd.Timedelta(minutes=3 * slot)
            for k in range(rho.size):
                rows.append((
                    ts, cfg.product, cfg.technology, lot_id, f"{lot_id}.{slot:02d}", slot, cfg.process_step, tool, ch,
                    cfg.recipe_id, metro, cfg.parameter, round(float(values[k]), 4), cfg.unit,
                    int(sites["site"].iat[k]), float(sites["x_mm"].iat[k]), float(sites["y_mm"].iat[k]),
                    cfg.target, cfg.lsl, cfg.usl,
                ))
    cols = ["timestamp", "product", "technology", "lot_id", "wafer_id", "slot", "process_step", "tool_id",
            "chamber_id", "recipe_id", "metro_tool_id", "parameter", "value", "unit", "site", "x", "y",
            "target", "lsl", "usl"]
    truth_df = pd.DataFrame(truth, columns=["lot_id", "wafer_id", "chamber_id", "kind", "magnitude"]).drop_duplicates()
    return pd.DataFrame(rows, columns=cols), truth_df


# --------------------------------------------------------------------------- #
# MSA study generators                                                        #
# --------------------------------------------------------------------------- #


def grr_study(n_parts=10, operators=("FT01", "FT02", "FT03"), n_reps=3, part_center=100.0,
              part_sigma=1.0, repeat_sigma=0.05, operator_sigma=0.03, seed=11) -> pd.DataFrame:
    """Crossed GR&R: wafers spanning the process range, measured on each tool n_reps times."""
    rng = np.random.default_rng(seed)
    parts = part_center + rng.normal(0, part_sigma, n_parts)
    bias = {o: rng.normal(0, operator_sigma) for o in operators}
    rows = [
        {"part": f"W{p + 1:02d}", "operator": o, "rep": r + 1, "value": parts[p] + bias[o] + rng.normal(0, repeat_sigma)}
        for p in range(n_parts) for o in operators for r in range(n_reps)
    ]
    return pd.DataFrame(rows)


def repeatability_study(n_sites=5, n_cycles=10, n_repeats=3, true_values=None, static_sigma=0.03,
                        load_sigma=0.04, seed=12) -> pd.DataFrame:
    """Static repeats nested in load/unload cycles at several sites."""
    rng = np.random.default_rng(seed)
    true_values = true_values if true_values is not None else 100.0 + rng.normal(0, 0.5, n_sites)
    rows = []
    for c in range(n_cycles):
        load = rng.normal(0, load_sigma, n_sites)
        for s in range(n_sites):
            for r in range(n_repeats):
                rows.append({"cycle": c + 1, "site": s + 1, "repeat": r + 1,
                             "value": true_values[s] + load[s] + rng.normal(0, static_sigma)})
    return pd.DataFrame(rows)


def stability_series(days=45, per_day=2, mean=100.0, sigma=0.04, drift_per_day=0.0,
                     start="2026-08-15 08:00", seed=13) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = days * per_day
    ts = pd.Timestamp(start) + pd.to_timedelta(np.arange(n) * 24 / per_day, unit="h")
    d = np.arange(n) / per_day
    return pd.DataFrame({"timestamp": ts, "value": mean + drift_per_day * d + rng.normal(0, sigma, n)})


def matching_study(n_wafers=5, plan_sites=49, offset=0.10, slope=1.0, sigma=0.04, seed=14) -> pd.DataFrame:
    """The same wafers/sites measured on a reference and a candidate tool (long format)."""
    rng = np.random.default_rng(seed)
    rows = []
    for w in range(n_wafers):
        truth = 95.0 + 2.5 * w + rng.normal(0, 0.6, plan_sites)
        for tool, (a, b) in {"FT01": (0.0, 1.0), "FT02": (offset, slope)}.items():
            meas = a + b * truth + rng.normal(0, sigma, plan_sites)
            rows += [{"tool_id": tool, "wafer_id": f"M{w + 1:02d}", "site": s + 1, "value": v} for s, v in enumerate(meas)]
    return pd.DataFrame(rows)
