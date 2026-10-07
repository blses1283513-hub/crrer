"""Realistic synthetic fab with an answer key (config/fab_sim.yaml).

    python -m metro_toolkit.datagen.fab --scenario mixed            # simulate + save as dataset "sim_mixed"
    python -m metro_toolkit.datagen.fab --scenario baseline --lots 40 --semiyield-names

What makes it more realistic than a plain random generator
  * every wafer goes through a route of steps on real-looking tools/chambers, with chamber offsets,
    drift between preventive maintenance (PM), and per-chamber spatial signatures
  * metrology only sees sampled wafers and sites, through metrology tools with their own noise
  * yield is computed die by die: a die fails when its local value leaves the step's device window
    (parametric) or when it catches a killer defect (clustered: negative binomial, spatial patterns)
  * electrical test and yield exist for every wafer, metrology for 5 of 25

The answer key records every injected event (what, where, when, which wafers, how big, yield impact),
the true per-wafer values before metrology error, and the true yield loss by cause.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..config import load_yaml
from ..wafer.sampling import sampling_plan

DEFECT_CODE = "D"
SEMIYIELD_NAMES = {"gate_ox_thk": "gate_oxide_thickness", "wl_cd_etch": "poly_cd", "rs_ohm_sq": "metal_resistance"}


@dataclass
class FabResult:
    long: pd.DataFrame          # standard long table: metrology + inline defects + e-test + yield
    wafers: pd.DataFrame        # answer key per wafer: chambers, true means, defect density, pattern, yield, loss by cause
    events: pd.DataFrame        # answer key per injected event
    dies: pd.DataFrame          # die map per wafer: one character per die ('.' pass, else the fail cause code)
    grid: dict                  # die centres (mm) and size
    drivers: pd.DataFrame       # true yield loss by cause, largest first
    scenario: str
    config: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Geometry                                                                    #
# --------------------------------------------------------------------------- #


def die_grid(radius_mm: float, edge_exclusion_mm: float, die_mm) -> dict:
    """Centres of full dies that fit inside the usable radius."""
    w, h = die_mm
    r = radius_mm - edge_exclusion_mm
    nx, ny = int(2 * r // w) + 2, int(2 * r // h) + 2
    xs = (np.arange(nx) - (nx - 1) / 2) * w
    ys = (np.arange(ny) - (ny - 1) / 2) * h
    X, Y = np.meshgrid(xs, ys)
    corners = [np.hypot(X + dx * w / 2, Y + dy * h / 2) for dx in (-1, 1) for dy in (-1, 1)]
    inside = np.all([c <= r for c in corners], axis=0)
    return {"x": X[inside], "y": Y[inside], "die_mm": [w, h], "r_eff": r}


def signature_field(sig: dict, x, y, r_eff: float):
    """Spatial signature. bowl = edge minus centre; tilt = value at the right edge; edge_roll = extra
    change at the edge, confined to the outer 15% of the radius."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    rho2 = (x * x + y * y) / r_eff**2
    rho = np.sqrt(rho2)
    return (sig.get("bowl", 0.0) * (rho2 - 0.5) + sig.get("tilt", 0.0) * x / r_eff
            + sig.get("edge_roll", 0.0) * np.clip((rho - 0.85) / 0.15, 0.0, None) ** 2)


def defect_weight(pattern: str, x, y, r_eff: float, rng) -> np.ndarray:
    """Relative killer-defect density per die for a spatial pattern (mean ~ 1 over the wafer)."""
    rho = np.hypot(x, y) / r_eff
    if pattern == "edge_ring":
        w = np.exp(-(1.0 - rho) / 0.06)
    elif pattern == "center":
        w = np.exp(-(rho**2) / 0.08)
    elif pattern == "scratch":
        ang = rng.uniform(0, np.pi)
        off = rng.uniform(-0.4, 0.4) * r_eff
        dist = np.abs(-np.sin(ang) * x + np.cos(ang) * y - off)
        w = (dist < 7.0).astype(float) + 1e-3
    elif pattern == "cluster":
        cx, cy = rng.uniform(-0.6, 0.6, 2) * r_eff
        w = np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * 18.0**2))
    else:
        return np.ones_like(rho)
    return w / w.mean()


# --------------------------------------------------------------------------- #
# Simulation                                                                  #
# --------------------------------------------------------------------------- #


def load_fab_config(path: str | Path | None = None) -> dict:
    if path is None:
        return load_yaml("fab_sim.yaml")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _active(ev: dict, lot: int) -> bool:
    return ev["start_lot"] <= lot < ev["start_lot"] + ev.get("n_lots", 10**9)


def _hit(ev: dict, tool: str, chamber: str) -> bool:
    return ev["where"] in ("all", tool, chamber)


def simulate_fab(cfg: dict | None = None, scenario: str = "mixed", n_lots: int | None = None,
                 seed: int | None = None) -> FabResult:
    cfg = dict(cfg or load_fab_config())
    if scenario not in cfg["scenarios"]:
        raise ValueError(f"unknown scenario '{scenario}'; choose from {list(cfg['scenarios'])}")
    events = [dict(e, id=f"E{i + 1}") for i, e in enumerate(cfg["scenarios"][scenario] or [])]
    rng = np.random.default_rng(cfg["seed"] if seed is None else seed)
    n_lots = int(n_lots or cfg["n_lots"])
    n_wafers = int(cfg["wafers_per_lot"])
    measured = set(cfg["measured_slots"])
    steps = cfg["steps"]
    step_by_name = {s["name"]: s for s in steps}
    grid = die_grid(cfg["wafer_radius_mm"], cfg["edge_exclusion_mm"], cfg["die_mm"])
    dx, dy, r_eff = grid["x"], grid["y"], grid["r_eff"]
    die_area_cm2 = cfg["die_mm"][0] * cfg["die_mm"][1] / 100.0
    sampling_cfg = load_yaml("sampling.yaml")
    plans = {s["name"]: sampling_plan(s.get("plan", "13"), sampling_cfg) for s in steps}
    metro_tools = list(cfg["metro_tools"])
    t0 = pd.Timestamp(cfg["start"])

    # chamber state
    chambers, state = {}, {}
    for s in steps:
        names = [(t, f"{t}-{chr(65 + c)}") for t, n in s["tools"].items() for c in range(n)]
        chambers[s["name"]] = names
        base = s.get("signature", {})
        for t, ch in names:
            jit = {k: v + rng.normal(0, 0.3 * abs(v) + 1e-12) for k, v in base.items()}
            state[(s["name"], ch)] = {"offset": rng.normal(0, s.get("chamber_offset_sigma", 0.0)), "sig": jit,
                                      "age": int(rng.integers(0, s.get("pm_every_lots", 10**6)))}

    cols = {k: [] for k in ("timestamp", "product", "lot_id", "wafer_id", "slot", "process_step", "tool_id",
                            "chamber_id", "metro_tool_id", "parameter", "value", "unit", "site", "x", "y",
                            "lsl", "usl")}
    wafer_rows, die_rows = [], []
    affected = {e["id"]: [] for e in events}
    codes = [s["code"] for s in steps if s.get("window")] + [DEFECT_CODE]

    def emit(ts, lot_id, wafer_id, slot, step, tool, ch, metro, param, values, unit, sites, lsl, usl):
        n = len(values)
        for k, v in (("timestamp", ts), ("product", cfg["product"]), ("lot_id", lot_id), ("wafer_id", wafer_id),
                     ("slot", slot), ("process_step", step), ("tool_id", tool), ("chamber_id", ch),
                     ("metro_tool_id", metro), ("parameter", param), ("unit", unit), ("lsl", lsl), ("usl", usl)):
            cols[k].extend([v] * n)
        cols["value"].extend(np.round(values, 5))
        if sites is None:
            cols["site"].extend([1] * n)
            cols["x"].extend([np.nan] * n)
            cols["y"].extend([np.nan] * n)
        else:
            cols["site"].extend(sites["site"].tolist())
            cols["x"].extend(sites["x_mm"].tolist())
            cols["y"].extend(sites["y_mm"].tolist())

    for lot in range(n_lots):
        lot_id = f"D{lot + 1:04d}"
        t_lot = t0 + pd.Timedelta(hours=lot * cfg["hours_between_lots"])
        metro = metro_tools[lot % len(metro_tools)]
        tool_of = {}
        for s in steps:
            tools = list(s["tools"])
            tool_of[s["name"]] = tools[(lot + rng.integers(0, 2)) % len(tools)]
            for t, ch in chambers[s["name"]]:
                if t == tool_of[s["name"]]:
                    st_ = state[(s["name"], ch)]
                    st_["age"] = (st_["age"] + 1) % s.get("pm_every_lots", 10**6)

        for slot in range(1, n_wafers + 1):
            wafer_id = f"{lot_id}.{slot:02d}"
            is_measured = slot in measured
            fail = np.full(dx.size, "", dtype=object)
            fail_cf = np.zeros(dx.size, bool)  # counterfactual: the same wafer without any injected event
            row = {"lot_id": lot_id, "wafer_id": wafer_id, "slot": slot, "lot_index": lot,
                   "timestamp": t_lot, "measured": is_measured, "metro_tool_id": metro}
            true_mean, die_vals, site_cache, die_cf = {}, {}, {}, {}
            for si, s in enumerate(steps):
                name, tool = s["name"], tool_of[s["name"]]
                tool_ch = [c for t, c in chambers[name] if t == tool]
                ch = tool_ch[(slot - 1) % len(tool_ch)]
                st_ = state[(name, ch)]
                mean = s["target"] + st_["offset"] + s.get("drift_per_lot", 0.0) * st_["age"] + rng.normal(0, s["sigma_wafer"])
                sig = dict(st_["sig"])
                mean_cf, sig_cf = mean, dict(sig)
                metro_shift = 0.0
                for e in events:
                    if e.get("step") != name or not _active(e, lot):
                        continue
                    if e["type"] in ("shift", "recipe") and _hit(e, tool, ch):
                        mean += e["magnitude"]
                    elif e["type"] == "drift" and _hit(e, tool, ch):
                        mean += e["magnitude"] * (lot - e["start_lot"] + 1)
                    elif e["type"] == "bowl" and _hit(e, tool, ch):
                        sig["bowl"] = sig.get("bowl", 0.0) + e["magnitude"]
                    elif e["type"] == "metro_offset" and e["where"] in ("all", metro):
                        metro_shift += e["magnitude"]
                        if is_measured:
                            affected[e["id"]].append(wafer_id)
                        continue
                    else:
                        continue
                    if e["type"] != "metro_offset":
                        affected[e["id"]].append(wafer_id)

                noise = rng.normal(0, s["sigma_local"], dx.size)
                vals = mean + signature_field(sig, dx, dy, r_eff) + noise
                vals_cf = mean_cf + signature_field(sig_cf, dx, dy, r_eff) + noise
                sp = plans[name]
                svals = mean + signature_field(sig, sp["x_mm"], sp["y_mm"], r_eff) + rng.normal(0, s["sigma_local"], len(sp))
                if s.get("from_step"):  # etched CD inherits the litho CD deviation at the same location
                    up = step_by_name[s["from_step"]]
                    vals = vals + (die_vals[up["name"]] - up["target"])
                    vals_cf = vals_cf + (die_cf[up["name"]] - up["target"])
                    svals = svals + (site_cache[up["name"]] - up["target"])
                    mean = mean + (true_mean[up["parameter"]] - up["target"])
                die_vals[name], site_cache[name], die_cf[name] = vals, svals, vals_cf
                true_mean[s["parameter"]] = float(mean)
                row[f"{name}_chamber"] = ch
                row[f"true_{s['parameter']}"] = float(np.mean(vals))
                if s.get("window"):
                    lo, hi = s["window"]
                    bad = ((vals < lo) | (vals > hi)) & (fail == "")
                    fail[bad] = s["code"]
                    fail_cf |= (vals_cf < lo) | (vals_cf > hi)

                if is_measured:
                    noise = s["sigma_local"] * cfg.get("metro_noise_ratio", 0.4)
                    meas = svals + cfg["metro_tools"][metro] + metro_shift + rng.normal(0, noise, len(sp))
                    lsl, usl = s.get("spec") or s.get("window") or (np.nan, np.nan)
                    ts = t_lot + pd.Timedelta(hours=si * 2, minutes=2 * slot)
                    emit(ts, lot_id, wafer_id, slot, name, tool, ch, metro, s["parameter"], meas, s["unit"], sp, lsl, usl)

            # killer defects: clustered (gamma-mixed Poisson = negative binomial) with spatial patterns
            dcfg = cfg["defects"]
            d_w = dcfg["d0_per_cm2"] * rng.gamma(dcfg["cluster_alpha"], 1.0 / dcfg["cluster_alpha"])
            lam = np.full(dx.size, d_w * die_area_cm2)
            lam_cf = None
            pattern = "random"
            u = rng.random()
            if u < 0.02:
                pattern = "scratch"
            elif u < 0.05:
                pattern = "cluster"
            if pattern != "random":
                lam = lam + 3.0 * d_w * die_area_cm2 * defect_weight(pattern, dx, dy, r_eff, rng)
            insp = step_by_name.get(dcfg.get("inspection_step", ""), steps[0])
            insp_tool = tool_of[insp["name"]]
            insp_ch = row.get(f"{insp['name']}_chamber", "")
            for e in events:
                if e["type"] == "defects" and _active(e, lot) and _hit(e, insp_tool, insp_ch):
                    lam_cf = lam.copy() if lam_cf is None else lam_cf
                    pattern = e.get("pattern", "random")
                    lam = lam + (e["magnitude"] - 1.0) * d_w * die_area_cm2 * defect_weight(pattern, dx, dy, r_eff, rng)
                    affected[e["id"]].append(wafer_id)
            draw = rng.random(dx.size)
            killed = draw < 1.0 - np.exp(-lam)
            fail[killed & (fail == "")] = DEFECT_CODE
            fail_cf |= draw < 1.0 - np.exp(-(lam if lam_cf is None else lam_cf))
            eff_d = float(lam.sum() / (dx.size * die_area_cm2))

            yld = float(np.mean(fail == ""))
            row.update({"defect_density_true": eff_d, "defect_pattern": pattern, "yield": yld,
                        "yield_without_events": float(np.mean(~fail_cf))})
            for c in codes:
                row[f"loss_{c}"] = float(np.mean(fail == c))
            wafer_rows.append(row)
            die_rows.append({"wafer_id": wafer_id, "map": "".join(c or "." for c in fail)})

            # inline inspection (measured wafers), e-test and yield (all wafers)
            t_end = t_lot + pd.Timedelta(hours=len(steps) * 2 + 24)
            if is_measured:
                area = dx.size * die_area_cm2
                dd = rng.poisson(eff_d * area) / area
                emit(t_lot + pd.Timedelta(hours=8, minutes=2 * slot), lot_id, wafer_id, slot, insp["name"],
                     insp_tool, insp_ch, "INSP01", "defect_density", [dd], "1/cm²", None, np.nan, np.nan)
            et = cfg["etest"]
            vt = et["vt_mv"]
            vt_val = vt["base"] + vt["slope_per_unit"] * (true_mean[vt["from"]] - vt["at"]) + rng.normal(0, vt["noise"])
            rs = et["rs_ohm_sq"]
            rs_val = rs["rho_uohm_cm"] * 1e-6 / (true_mean[rs["from"]] * 1e-7) * (1 + rng.normal(0, rs["noise_frac"]))
            emit(t_end, lot_id, wafer_id, slot, "ETEST", "ET01", "", "", "vt_mv", [vt_val], vt["unit"], None, np.nan, np.nan)
            emit(t_end, lot_id, wafer_id, slot, "ETEST", "ET01", "", "", "rs_ohm_sq", [rs_val], rs["unit"], None, np.nan, np.nan)
            emit(t_end + pd.Timedelta(hours=12), lot_id, wafer_id, slot, "SORT", "PRB01", "", "", "yield", [yld], "",
                 None, np.nan, np.nan)

    long = pd.DataFrame(cols)
    for c in ("tool_id", "chamber_id", "metro_tool_id"):
        long[c] = long[c].replace("", "(n/a)")
    long = long.sort_values("timestamp", kind="stable").reset_index(drop=True)
    wafers = pd.DataFrame(wafer_rows)

    ev_rows = []
    param_of = {s["name"]: s["parameter"] for s in steps}
    physical = {e["id"]: set(affected[e["id"]]) for e in events if e["type"] != "metro_offset"}
    for e in events:
        ids = sorted(set(affected[e["id"]]))
        params = ["defect_density", "yield"] if e["type"] == "defects" else [param_of[e["step"]]]
        if e["type"] == "recipe" and e["step"] == "WL_LITHO":
            params.append("wl_cd_etch")
        hit = wafers["wafer_id"].isin(ids)
        # true (counterfactual) impact: the same wafers simulated with identical random draws but no events,
        # measured on wafers that no other product-affecting event touched (falls back to all if none)
        others = set().union(*[v for k, v in physical.items() if k != e["id"]]) if len(physical) > 1 or (
            physical and e["id"] not in physical) else set()
        excl = hit & ~wafers["wafer_id"].isin(others)
        use = excl if excl.any() else hit
        impact = float((wafers.loc[use, "yield"] - wafers.loc[use, "yield_without_events"]).mean()) if use.any() else 0.0
        ev_rows.append({
            "id": e["id"], "type": e["type"], "step": e.get("step"), "parameters": ";".join(params),
            "where": e["where"], "start_lot": e["start_lot"], "end_lot": e["start_lot"] + e.get("n_lots", n_lots) - 1,
            "magnitude": e["magnitude"], "pattern": e.get("pattern", ""), "n_wafers": len(ids),
            "n_measured": int(wafers.loc[hit, "measured"].sum()), "yield_impact": impact,
            "affects_product": e["type"] != "metro_offset", "wafer_ids": ";".join(ids)})
    events_df = pd.DataFrame(ev_rows, columns=["id", "type", "step", "parameters", "where", "start_lot", "end_lot",
                                               "magnitude", "pattern", "n_wafers", "n_measured", "yield_impact",
                                               "affects_product", "wafer_ids"])

    cause_names = {s["code"]: s["parameter"] for s in steps if s.get("window")}
    cause_names[DEFECT_CODE] = "defect_density"
    drivers = pd.DataFrame([{"code": c, "cause": cause_names[c], "yield_loss_pct": 100 * wafers[f"loss_{c}"].mean()}
                            for c in codes]).sort_values("yield_loss_pct", ascending=False).reset_index(drop=True)
    grid_out = {"x": dx.tolist(), "y": dy.tolist(), "die_mm": list(cfg["die_mm"]), "r_eff": r_eff}
    return FabResult(long, wafers, events_df, pd.DataFrame(die_rows), grid_out, drivers, scenario,
                     {k: cfg[k] for k in ("seed", "n_lots", "wafers_per_lot", "measured_slots", "die_mm")} | {"n_lots": n_lots})


def apply_semiyield_names(long: pd.DataFrame) -> pd.DataFrame:
    out = long.copy()
    out["parameter"] = out["parameter"].replace(SEMIYIELD_NAMES)
    return out


def save_fab(result: FabResult, name: str, folder: Path | None = None, semiyield_names: bool = False) -> dict:
    """Save as an importable dataset (shows up in the dashboard and the SemiYield launcher) + answer key."""
    import json

    from ..ingest.store import safe_name, save_dataset

    long = apply_semiyield_names(result.long) if semiyield_names else result.long
    paths = save_dataset(name, long, folder)
    folder = paths["long"].parent
    n = safe_name(name)
    result.wafers.to_csv(folder / f"{n}_truth_wafers.csv", index=False)
    result.events.to_csv(folder / f"{n}_truth_events.csv", index=False)
    result.dies.to_csv(folder / f"{n}_dies.csv", index=False)
    meta = {"scenario": result.scenario, "config": result.config, "grid": result.grid,
            "drivers": result.drivers.to_dict("records"), "semiyield_names": semiyield_names,
            "renamed": SEMIYIELD_NAMES if semiyield_names else {}}
    (folder / f"{n}_truth.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    paths.update({k: folder / f"{n}_{k}" for k in ("truth_wafers.csv", "truth_events.csv", "dies.csv", "truth.json")})
    return paths


def load_truth(name: str, folder: Path | None = None) -> dict | None:
    """Answer key of a saved simulation, or None if the dataset was not simulated."""
    import json

    from ..config import import_dir
    from ..ingest.store import safe_name

    folder = folder or import_dir()
    n = safe_name(name)
    meta_path = folder / f"{n}_truth.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["wafers"] = pd.read_csv(folder / f"{n}_truth_wafers.csv")
    meta["events"] = pd.read_csv(folder / f"{n}_truth_events.csv").fillna({"wafer_ids": "", "pattern": ""})
    meta["dies"] = pd.read_csv(folder / f"{n}_dies.csv")
    meta["drivers"] = pd.DataFrame(meta["drivers"])
    return meta


def main(argv=None):
    cfg_all = load_fab_config()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", default="mixed", choices=list(cfg_all["scenarios"]))
    ap.add_argument("--lots", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--name", default=None, help="dataset name (default sim_<scenario>)")
    ap.add_argument("--semiyield-names", action="store_true", help="name columns for SemiYield's Yield Prediction")
    args = ap.parse_args(argv)
    res = simulate_fab(cfg_all, args.scenario, args.lots, args.seed)
    paths = save_fab(res, args.name or f"sim_{args.scenario}", semiyield_names=args.semiyield_names)
    w = res.wafers
    print(f"scenario {args.scenario}: {w['lot_id'].nunique()} lots, {len(w)} wafers, "
          f"yield mean {100 * w['yield'].mean():.1f}% (sd {100 * w['yield'].std():.1f}%), {len(res.events)} events")
    print(f"saved: {paths['long']}  (+ answer key files next to it)")


if __name__ == "__main__":
    main()
