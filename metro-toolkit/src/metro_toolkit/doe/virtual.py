"""Virtual process tools (config/doe_processes.yaml): hidden true response surface + noise = answer key.

ald  thickness = GPC(T, purge) x cycles. Inside the ALD window GPC is flat; outside it rises (condensation
     at low T, precursor decomposition at high T). Too short a purge leaves precursor in the chamber ->
     parasitic CVD growth -> thicker and less uniform. Throughput: time = cycles x (pulse + 2 purges).
cvd  rate = 1 / (1/r_surface + 1/r_transport): Arrhenius at low T (reaction limited, heater profile shows
     up in NU), pressure limited at high T (transport limited, gas depletion across the wafer).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..config import load_yaml

K_B_EV = 8.617e-5


def load_processes() -> dict:
    return load_yaml("doe_processes.yaml")["processes"]


def _ald(s: dict, p: dict) -> dict:
    T, purge, cycles = s["temp_c"], s["purge_s"], s["cycles"]
    dt = (T - p["t_window_c"]) / 40.0
    cvd = p["cvd_frac"] * np.exp(-purge / p["purge_tau_s"])
    gpc = p["gpc_nm"] * (1 + p["t_curv"] * dt**2) * (1 + cvd)
    return {"thickness": gpc * cycles,
            "nu_pct": p["nu_base_pct"] + p["nu_temp"] * dt**2 + p["nu_cvd"] * cvd,
            "time_min": cycles * (p["pulse_s"] + 2 * purge) / 60.0}


def _cvd(s: dict, p: dict) -> dict:
    T, P, t = s["temp_c"] + 273.15, s["pressure_torr"], s["time_s"]
    rs = p["rs0_nm_s"] * np.exp(p["ea_ev"] / K_B_EV * (1 / (575 + 273.15) - 1 / T))
    rm = p["rm0_nm_s"] * (P / 5.0) ** p["p_exp"]
    rate = 1 / (1 / rs + 1 / rm)
    transport = rs / (rs + rm)  # 0 = reaction limited, 1 = transport limited
    return {"thickness": rate * t,
            "nu_pct": p["nu_base_pct"] + p["nu_transport"] * transport ** 2
            + p["nu_pressure"] * ((P - p["p_best_torr"]) / 5.0) ** 2
            + p["nu_temp"] * (1 - transport) * ((s["temp_c"] - 575) / 75.0) ** 2}


PHYSICS = {"ald": _ald, "cvd": _cvd}


def true_response(proc: dict, settings: pd.DataFrame | dict) -> pd.DataFrame:
    """Noise-free responses for real factor settings (DataFrame or dict of arrays/scalars)."""
    s = {k: np.asarray(settings[k], float) for k in proc["factors"]}
    out = PHYSICS[proc["physics"]](s, proc["params"])
    n = max(np.size(v) for v in s.values())
    return pd.DataFrame({k: np.broadcast_to(v, (n,)) for k, v in out.items()})


def run_experiments(proc: dict, sheet: pd.DataFrame, fixed: dict | None = None, seed: int = 0) -> pd.DataFrame:
    """'Run' the sheet on the virtual tool: true response + run-to-run noise. Factors not in the sheet
    are held at ``fixed`` (default: centre of their range)."""
    settings = {}
    for name, f in proc["factors"].items():
        if name in sheet:
            settings[name] = sheet[name].to_numpy(float)
        else:
            settings[name] = np.full(len(sheet), (fixed or {}).get(name, (f["low"] + f["high"]) / 2))
    truth = true_response(proc, settings)
    rng = np.random.default_rng(seed)
    out = sheet.copy()
    for r in truth.columns:
        sd = proc.get("noise", {}).get(r, 0.0)
        out[r] = np.round(truth[r].to_numpy() + rng.normal(0, sd, len(out)), 4)
    return out


def _full_settings(proc: dict, names: list[str], coded: np.ndarray, fixed: dict | None) -> dict:
    from .designs import to_real

    real = to_real(coded, {n: proc["factors"][n] for n in names})
    s = {}
    for name, f in proc["factors"].items():
        s[name] = real[:, names.index(name)] if name in names else np.full(
            len(coded), (fixed or {}).get(name, (f["low"] + f["high"]) / 2))
    return s


def true_optimum(proc: dict, names: list[str] | None = None, fixed: dict | None = None) -> dict:
    """Answer key: best recipe on the noise-free surface over the factors ``names`` (others held fixed)."""
    from .optimize import optimize

    names = names or list(proc["factors"])
    best = optimize(lambda c: true_response(proc, _full_settings(proc, names, c, fixed)), len(names),
                    proc["responses"])
    real = _full_settings(proc, names, best["coded"][None, :], fixed)
    best["settings"] = {k: float(v[0]) for k, v in real.items()}
    return best


def evaluate_recipe(proc: dict, settings: dict) -> dict:
    """True (noise-free) responses and desirability of a recipe - how good is it really?"""
    from .optimize import overall

    resp = true_response(proc, {k: [v] for k, v in settings.items()})
    return {"responses": resp.iloc[0].to_dict(), "D": float(overall(resp, proc["responses"])[0])}
