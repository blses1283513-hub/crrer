"""Polar wafer sampling plans (1/5/9/13/25/49 points by default, from sampling.yaml)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def sampling_plan(
    name: str | int = "49",
    cfg: dict | None = None,
    wafer_diameter_mm: float | None = None,
    edge_exclusion_mm: float | None = None,
) -> pd.DataFrame:
    """Return site coordinates: columns site, x_mm, y_mm, r_mm, theta_deg, ring.

    Site 1 is the centre; rings are numbered outward. Coordinates are in mm with
    the wafer centre at (0, 0); theta = 0 is +x (notch convention is tool-specific).
    """
    if cfg is None:
        from ..config import load_yaml

        cfg = load_yaml("sampling.yaml")
    diameter = wafer_diameter_mm or cfg.get("wafer_diameter_mm", 300)
    ee = cfg.get("edge_exclusion_mm", 3) if edge_exclusion_mm is None else edge_exclusion_mm
    r_eff = diameter / 2.0 - ee
    rings = cfg["plans"][str(name)]

    rows = []
    for ring_no, ring in enumerate(rings):
        n, r = int(ring["n"]), float(ring["r_frac"]) * r_eff
        phase = float(ring.get("phase_deg", 0.0))
        for i in range(n):
            theta = phase + 360.0 * i / n if n > 1 else 0.0
            t = np.deg2rad(theta)
            rows.append((r * np.cos(t), r * np.sin(t), r, theta % 360.0, ring_no))
    df = pd.DataFrame(rows, columns=["x_mm", "y_mm", "r_mm", "theta_deg", "ring"])
    df.insert(0, "site", np.arange(1, len(df) + 1))
    df.attrs.update(r_eff_mm=r_eff, wafer_radius_mm=diameter / 2.0, edge_exclusion_mm=ee, plan=str(name))
    return df.round({"x_mm": 3, "y_mm": 3, "r_mm": 3, "theta_deg": 3})
