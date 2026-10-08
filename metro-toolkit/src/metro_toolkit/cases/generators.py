"""Case generators: realistic, randomised situations with one known cause.

Each generator takes (rng, level) and returns a dict:
    v         values for the brief / explanation / model-message templates in cases.yaml
    evidence  list of evidence items the Case study page draws (same charts as the other pages)
    guide     list of (chart key, Facts): the reading panels shown after you answer
    answer    optional overrides of the correct options (e.g. when the brief says the measurement
              was already verified, the right first action is no longer "verify the measurement")

level: basic (large, clear signal) | intermediate | advanced (subtle signal, fewer hints).
Everything is synthetic. Numbers are illustrative, not any fab's recipe or spec.
"""

from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from ..analysis import process_capability, spc_by_group, wafer_summary
from ..config import load_stack, load_yaml, wavelengths
from ..guide import insights as gi

SCALE = {"basic": 1.0, "intermediate": 0.65, "advanced": 0.42}
T0 = pd.Timestamp("2026-09-01 06:00")

# realistic parameter families for SPC / wafer cases: (parameter, unit, target, wafer sigma, local sigma, tools)
FAMILIES = [
    ("gate_ox_thk", "nm", 3.00, 0.012, 0.010, ["RTP01", "RTP02"]),
    ("hk_thk", "nm", 5.00, 0.025, 0.020, ["ALD01", "ALD02"]),
    ("tin_thk", "nm", 10.0, 0.10, 0.06, ["CVD01", "CVD02"]),
    ("ild_thk", "nm", 300.0, 2.0, 1.5, ["CMP01", "CMP02"]),
    ("pad_ox_thk", "nm", 10.0, 0.08, 0.05, ["FUR01", "FUR02"]),
]


def _family(rng):
    return FAMILIES[int(rng.integers(len(FAMILIES)))]


def _chambers(tools):
    return [f"{t}-{c}" for t in tools for c in "AB"]


def _fmt(x, nd=3):
    return float(np.round(x, nd))


# --------------------------------------------------------------------------- SPC data
def _spc_table(rng, fam, n=120, event=None):
    """Wafer-level SPC data in time order. event = dict(kind, chamber, start, mag) in units of wafer sigma
    (shift / drift per point / metro offset / nu increase in % points)."""
    param, unit, target, sig, loc, tools = fam
    chambers = _chambers(tools)
    offset = {c: rng.normal(0, 0.3 * sig) for c in chambers}
    rows = []
    for i in range(n):
        ch = chambers[int(rng.integers(len(chambers)))]
        lot = i // 2
        metro = "FT01" if lot % 2 == 0 else "FT02"
        mean = target + offset[ch] + rng.normal(0, sig)
        nu = 100 * loc / target * (1 + 0.15 * rng.normal())
        if event and i >= event["start"]:
            if event["kind"] == "shift" and ch == event["chamber"]:
                mean += event["mag"] * sig
            elif event["kind"] == "drift" and ch == event["chamber"]:
                mean += event["mag"] * sig * (i - event["start"])
            elif event["kind"] == "metro" and metro == event["chamber"]:
                mean += event["mag"] * sig
            elif event["kind"] == "nu" and ch == event["chamber"]:
                nu += event["mag"] * 100 * loc / target
            elif event["kind"] == "spike" and i == event["start"]:
                mean += event["mag"] * sig
        std = nu / 100 * mean
        rows.append({"lot_id": f"L{lot + 1:04d}", "wafer_id": f"L{lot + 1:04d}.{int(rng.integers(1, 26)):02d}",
                     "tool_id": ch.split("-")[0], "chamber_id": ch, "metro_tool_id": metro, "parameter": param,
                     "timestamp": T0 + pd.Timedelta(hours=1.5 * i), "mean": mean, "std": std,
                     "min": mean - 1.7 * std, "max": mean + 1.7 * std, "n_sites": 13, "nu_1sigma_pct": nu,
                     "range": 3.4 * std})
    return pd.DataFrame(rows)


def _spc_evidence(wafers, group, stat, param, lsl, usl, chart="IMR", phase1=20, title=None):
    charts = spc_by_group(wafers, group, stat, chart, phase1)
    cap = None
    if stat == "mean" and lsl is not None:
        cap = [{group: g, **process_capability(gw["mean"], lsl, usl)} for g, gw in wafers.groupby(group)]
    facts = gi.spc(charts, wafers, group, stat, chart, param, cap, lsl, usl)
    ev = {"kind": "spc", "wafers": wafers, "group": group, "stat": stat, "chart": chart, "phase1": phase1,
          "param": param, "lsl": lsl, "usl": usl, "title": title}
    return ev, facts


def _spec(fam, k=4.0):
    _, _, target, sig, _, _ = fam
    return _fmt(target - k * sig, 4), _fmt(target + k * sig, 4)


def _verified(rng, level):
    """In some intermediate / advanced cases the brief says the measurement was already double-checked."""
    return bool(level != "basic" and rng.random() < 0.5)


VERIFIED_TEXT = {True: {"zh": "量測端已確認：同片在參考機台重測結果一致、量測機台監控片正常。",
                        "en": "Metrology has already checked: the same wafer re-measured on the reference tool agrees, and the "
                              "metrology tool's monitor wafer is normal."},
                 False: {"zh": "目前還沒有人重測或確認量測。", "en": "Nobody has re-measured or checked the measurement yet."}}


def _process_answer(verified):
    return {"action": "A_HOLD_INHIBIT" if verified else "A_VERIFY"}


def spc_chamber_shift(rng, level):
    fam = _family(rng)
    ch = _chambers(fam[5])[int(rng.integers(4))]
    mag = float(rng.choice([-1, 1])) * rng.uniform(2.6, 3.4) * SCALE[level] / 0.85
    start = int(rng.integers(70, 95))
    w = _spc_table(rng, fam, event={"kind": "shift", "chamber": ch, "start": start, "mag": mag})
    lsl, usl = _spec(fam)
    ev, facts = _spc_evidence(w, "chamber_id", "mean", fam[0], lsl, usl)
    ver = _verified(rng, level)
    first = w[(w.index >= start) & (w.chamber_id == ch)].iloc[0]
    v = {"param": fam[0], "unit": fam[1], "chamber": ch, "tool": ch.split("-")[0], "shift": _fmt(mag * fam[3], 4),
         "shift_sigma": _fmt(abs(mag), 2), "start_wafer": first.wafer_id, "start_time": str(first.timestamp)[:16],
         "verified": VERIFIED_TEXT[ver], "lsl": lsl, "usl": usl}
    return {"v": v, "evidence": [ev], "guide": [("spc_chart", facts)], "answer": _process_answer(ver)}


def spc_slow_drift(rng, level):
    fam = _family(rng)
    ch = _chambers(fam[5])[int(rng.integers(4))]
    slope = float(rng.choice([-1, 1])) * rng.uniform(0.10, 0.14) * SCALE[level]
    start = int(rng.integers(40, 60))
    w = _spc_table(rng, fam, event={"kind": "drift", "chamber": ch, "start": start, "mag": slope})
    lsl, usl = _spec(fam)
    ev, facts = _spc_evidence(w, "chamber_id", "mean", fam[0], lsl, usl, chart="EWMA")
    days = int(rng.integers(24, 34))
    v = {"param": fam[0], "unit": fam[1], "chamber": ch, "tool": ch.split("-")[0],
         "drift_total": _fmt(slope * fam[3] * (len(w) - 1 - start), 4),
         "pm_days": days, "pm_cycle": 30, "lsl": lsl, "usl": usl}
    return {"v": v, "evidence": [ev], "guide": [("spc_chart", facts)]}


def spc_metro_offset(rng, level):
    fam = _family(rng)
    metro = str(rng.choice(["FT01", "FT02"]))
    mag = float(rng.choice([-1, 1])) * rng.uniform(2.4, 3.2) * SCALE[level] / 0.85
    start = int(rng.integers(60, 85))
    w = _spc_table(rng, fam, event={"kind": "metro", "chamber": metro, "start": start, "mag": mag})
    lsl, usl = _spec(fam)
    ev1, f1 = _spc_evidence(w, "chamber_id", "mean", fam[0], lsl, usl, title="依 chamber 分組 · grouped by chamber")
    ev2, f2 = _spc_evidence(w, "metro_tool_id", "mean", fam[0], lsl, usl, title="依量測機台分組 · grouped by metrology tool")
    v = {"param": fam[0], "unit": fam[1], "metro": metro, "offset": _fmt(mag * fam[3], 4), "offset_sigma": _fmt(abs(mag), 2),
         "n_chambers": 4, "lsl": lsl, "usl": usl}
    return {"v": v, "evidence": [ev1, ev2], "guide": [("spc_chart", f2), ("spc_chart", f1)]}


def spc_uniformity_only(rng, level):
    fam = _family(rng)
    ch = _chambers(fam[5])[int(rng.integers(4))]
    mag = rng.uniform(2.2, 2.8) * SCALE[level] / 0.8
    start = int(rng.integers(70, 95))
    w = _spc_table(rng, fam, event={"kind": "nu", "chamber": ch, "start": start, "mag": mag})
    lsl, usl = _spec(fam)
    ev1, f1 = _spc_evidence(w, "chamber_id", "mean", fam[0], lsl, usl, title="晶圓平均值 · wafer mean")
    ev2, f2 = _spc_evidence(w, "chamber_id", "nu_1sigma_pct", fam[0], None, None, title="片內 1σ % · within-wafer 1σ %")
    nu0 = 100 * fam[4] / fam[2]
    v = {"param": fam[0], "unit": fam[1], "chamber": ch, "tool": ch.split("-")[0], "nu_before": _fmt(nu0, 3),
         "nu_after": _fmt(nu0 * (1 + mag), 3)}
    return {"v": v, "evidence": [ev1, ev2], "guide": [("spc_chart", f2), ("spc_chart", f1)]}


def spc_cpk_off_center(rng, level):
    """In control, but centred off target: Cpk 1.0-1.33 while Cp is comfortable. Redrawn until the data says exactly
    that (no chance OOC point, lowest Cpk in the watch band), so the case has one clean signal."""
    fam = _family(rng)
    param, unit, target, sig, loc, tools = fam
    k = rng.uniform(5.0, 5.6)
    lsl, usl = _fmt(target - k * sig, 4), _fmt(target + k * sig, 4)
    for _ in range(40):
        w = _spc_table(rng, fam)
        off = float(rng.choice([-1, 1])) * rng.uniform(1.6, 2.2) * sig * (1.25 - 0.25 * SCALE[level])
        w["mean"] += off
        ev, facts = _spc_evidence(w, "chamber_id", "mean", param, lsl, usl)
        if facts.status == "watch" and facts.v["n_ooc"] == 0:
            break
    cap = process_capability(w["mean"], lsl, usl)
    v = {"param": param, "unit": unit, "target": target, "mean": _fmt(w["mean"].mean(), 4), "offset": _fmt(off, 4),
         "cp": _fmt(cap["Cp"], 2), "cpk": _fmt(cap["Cpk"], 2), "lsl": lsl, "usl": usl}
    return {"v": v, "evidence": [ev], "guide": [("spc_chart", facts)]}


def spc_false_alarm(rng, level):
    """One isolated WE1 point in an otherwise quiet process (redrawn until it is the only flag)."""
    fam = _family(rng)
    lsl, usl = _spec(fam)
    for _ in range(40):
        start = int(rng.integers(100, 117))
        mag = float(rng.choice([-1, 1])) * rng.uniform(3.4, 3.9)
        w = _spc_table(rng, fam, event={"kind": "spike", "chamber": None, "start": start, "mag": mag})
        ev, facts = _spc_evidence(w, "chamber_id", "mean", fam[0], lsl, usl)
        if facts.v["n_ooc"] == 1:
            break
    spike = w.iloc[start]
    remeasured = bool(level != "basic" and rng.random() < 0.6)
    v = {"param": fam[0], "unit": fam[1], "chamber": spike.chamber_id, "wafer": spike.wafer_id,
         "value": _fmt(spike["mean"], 4), "z": _fmt(abs(mag), 1),
         "remeasure": ({"zh": f"已重測：同片重測值回到 {_fmt(spike['mean'] - mag * fam[3] * 0.95, 4)} {fam[1]}（接近 CL）。",
                        "en": f"Already re-measured: the same wafer now reads {_fmt(spike['mean'] - mag * fam[3] * 0.95, 4)} "
                              f"{fam[1]} (near the CL)."} if remeasured else
                       {"zh": "還沒有重測。", "en": "It has not been re-measured yet."})}
    answer = {"action": "A_RECORD", "decision": "D_RELEASE"} if remeasured else {}
    return {"v": v, "evidence": [ev], "guide": [("spc_chart", facts)], "answer": answer}


# --------------------------------------------------------------------------- wafer maps
def _wafer_sites(rng, fam, sig: dict, outlier=None, wafer_id="W", chamber="X"):
    from ..datagen.fab import signature_field
    from ..wafer.sampling import sampling_plan

    param, unit, target, _, loc, _ = fam
    plan = sampling_plan("49", load_yaml("sampling.yaml"))
    x, y = plan["x_mm"].to_numpy(float), plan["y_mm"].to_numpy(float)
    r_eff = float(np.hypot(x, y).max())
    vals = target + signature_field(sig, x, y, r_eff) + rng.normal(0, loc, len(x))
    if outlier is not None:
        vals[outlier[0]] += outlier[1]
    lsl, usl = target - 6 * loc, target + 6 * loc
    return pd.DataFrame({"wafer_id": wafer_id, "chamber_id": chamber, "parameter": param, "site": plan["site"],
                         "x": x, "y": y, "value": vals, "unit": unit, "lsl": lsl, "usl": usl,
                         "timestamp": T0, "lot_id": wafer_id.split(".")[0], "tool_id": chamber.split("-")[0]})


def _wafer_case(rng, level, sig_case, outlier_k=None):
    fam = _family(rng)
    loc = fam[4]
    chambers = _chambers(fam[5])
    ch = chambers[int(rng.integers(4))]
    base = {"bowl": 0.6 * loc, "edge_roll": -0.4 * loc}
    fleet = [_wafer_sites(rng, fam, {k: v * (1 + 0.2 * rng.normal()) for k, v in base.items()},
                          wafer_id=f"L{100 + i:04d}.{int(rng.integers(1, 26)):02d}", chamber=chambers[i % 4]) for i in range(24)]
    sig = dict(base)
    for k, v in sig_case.items():
        sig[k] = sig.get(k, 0.0) + v * loc
    wid = f"L{125:04d}.{int(rng.integers(1, 26)):02d}"
    outlier = None
    if outlier_k:
        site = int(rng.integers(9, 25))  # an inner-ring site, not the edge
        outlier = (site, float(rng.choice([-1, 1])) * outlier_k * loc)
    w = _wafer_sites(rng, fam, sig, outlier, wafer_id=wid, chamber=ch)
    allw = pd.concat(fleet + [w], ignore_index=True)
    return fam, ch, w, wafer_summary(allw), outlier


def _wafer_evidence(w, wafers, param):
    from ..wafer import radial_profile, uniformity_metrics, zernike_decompose

    um = uniformity_metrics(w.value)
    r_eff = float(np.hypot(w.x, w.y).max())
    zk = zernike_decompose(w.x, w.y, w.value, radius_mm=r_eff)
    rp = radial_profile(w.x, w.y, w.value)
    facts = gi.wafer_page(w, um, wafers, zk, rp, param)
    ev = {"kind": "wafer", "w": w, "um": um, "zk": zk, "rp": rp}
    return ev, facts, um


def _wafer_generic(rng, level, sig_case, outlier_k=None):
    fam, ch, w, wafers, outlier = _wafer_case(rng, level, sig_case, outlier_k)
    ev, facts, um = _wafer_evidence(w, wafers, fam[0])
    v = {"param": fam[0], "unit": fam[1], "chamber": ch, "tool": ch.split("-")[0], "wafer": w.wafer_id.iloc[0],
         "nu": _fmt(um["nu_1sigma_pct"], 3), "nu_median": _fmt(float(wafers["nu_1sigma_pct"].median()), 3),
         "range": _fmt(um["range"], 4)}
    guide = [("wafer_map", facts["wafer_map"]), ("wafer_zernike", facts["wafer_zernike"]), ("wafer_radial", facts["wafer_radial"])]
    return fam, w, v, ev, guide, outlier


def wafer_edge_roll(rng, level):
    k = rng.uniform(9, 12) * SCALE[level]
    fam, w, v, ev, guide, _ = _wafer_generic(rng, level, {"edge_roll": -k})
    ver = _verified(rng, level)
    v.update({"rf_hours": int(rng.integers(820, 980)), "ring_life": 1000, "verified": VERIFIED_TEXT[ver]})
    return {"v": v, "evidence": [ev], "guide": guide, "answer": {"action": "A_EE_HW" if ver else "A_VERIFY"}}


def wafer_tilt(rng, level):
    k = rng.uniform(7, 9) * SCALE[level]
    fam, _, v, ev, guide, _ = _wafer_generic(rng, level, {"tilt": float(rng.choice([-1, 1])) * k})
    ver = _verified(rng, level)
    v.update({"verified": VERIFIED_TEXT[ver]})
    return {"v": v, "evidence": [ev], "guide": guide, "answer": {"action": "A_EE_HW" if ver else "A_VERIFY"}}


def wafer_bad_site(rng, level):
    k = rng.uniform(12, 15) * SCALE[level]
    fam, w, v, ev, guide, outlier = _wafer_generic(rng, level, {}, outlier_k=k)
    site = int(w.site.iloc[outlier[0]])
    v.update({"site": site, "site_value": _fmt(float(w.value.iloc[outlier[0]]), 4),
              "neighbour_mean": _fmt(float(w.value.drop(w.index[outlier[0]]).mean()), 4)})
    return {"v": v, "evidence": [ev], "guide": guide}


def wafer_bowl_after_pm(rng, level):
    k = float(rng.choice([-1, 1])) * rng.uniform(8, 11) * SCALE[level]
    fam, w, v, ev, guide, _ = _wafer_generic(rng, level, {"bowl": k})
    ver = _verified(rng, level)
    v.update({"pm_part": {"zh": "噴頭（showerhead）", "en": "showerhead"} if fam[0] != "ild_thk" else
              {"zh": "研磨頭／保持環（head / retaining ring）", "en": "polishing head / retaining ring"},
              "verified": VERIFIED_TEXT[ver]})
    return {"v": v, "evidence": [ev], "guide": guide, "answer": {"action": "A_EE_HW" if ver else "A_VERIFY"}}


# --------------------------------------------------------------------------- film stack
def _fit_rows(res, true_vals):
    return [{"parameter": lab, "true": true_vals.get(lab, np.nan), "fitted": res.values[lab], "± 1σ": res.stderr[lab],
             "error": res.values[lab] - true_vals.get(lab, np.nan)} for lab in res.labels]


def stack_wrong_underlayer(rng, level):
    from ..metrology.thinfilm import fit, simulate_se

    cfg = load_yaml("films.yaml")
    stack, recipe = load_stack("highk_on_il", cfg)
    wl = wavelengths(cfg)
    d_il = float(rng.choice([-1, 1])) * rng.uniform(0.45, 0.6) * SCALE[level]
    t_hf = rng.uniform(2.8, 3.2)
    truth = stack.copy_with([t_hf, 1.0 + d_il])
    meas = simulate_se(truth, wl, recipe["angles_deg"], 0.02, 0.04, rng=int(rng.integers(1e6)))
    res = fit(stack, meas, recipe["fit_params"])
    rows = _fit_rows(res, {"L0.thickness": t_hf})
    facts = gi.stack_fit(res, rows, "se", [1])
    tem = t_hf + rng.normal(0, 0.03)
    v = {"fitted": _fmt(res.values["L0.thickness"], 3), "tem": _fmt(tem, 2), "diff": _fmt(res.values["L0.thickness"] - tem, 2),
         "chi2": _fmt(res.chi2_red, 2), "il_recipe": 1.0, "il_true": _fmt(1.0 + d_il, 2), "d_il": _fmt(d_il, 2)}
    ev = {"kind": "fit", "technique": "se", "wl": wl, "meas": meas, "res": res, "angles": recipe["angles_deg"],
          "table": pd.DataFrame([{"parameter": r["parameter"], "fitted": r["fitted"], "± 1σ": r["± 1σ"]} for r in rows]),
          "notes": {"zh": "recipe 固定層：IL（SiO₂）= 1.0 nm（來自 3 個月前的參考片）", "en": "Recipe fixed layer: IL (SiO₂) = 1.0 nm "
                    "(from a reference wafer three months ago)"}}
    return {"v": v, "evidence": [ev], "guide": [("stack_se", facts)]}


def stack_float_n_thin(rng, level):
    from ..metrology.thinfilm import FitParameter, fit, simulate_reflectometry

    cfg = load_yaml("films.yaml")
    stack, recipe = load_stack("highk_on_il", cfg)
    wl = wavelengths(cfg)
    t = rng.uniform(1.8, 2.6) if level != "advanced" else rng.uniform(2.6, 3.4)
    truth = stack.copy_with([t, 1.0])
    a0 = stack.layers[0].material.A
    p_float = [FitParameter(0, bounds=(0, 15)), FitParameter(0, "A", (a0 - 0.3, a0 + 0.3))]
    p_fixed = [FitParameter(0, bounds=(0, 15))]
    rows, first = [], None
    for k in range(6):
        meas = simulate_reflectometry(truth, wl, noise=0.002, rng=int(rng.integers(1e6)))
        rf = fit(stack, meas, p_float)
        rx = fit(stack, meas, p_fixed)
        first = first or (rf, meas)
        rows.append({"repeat": k + 1, "thickness, n floated": rf.values["L0.thickness"], "n (Cauchy A) floated": rf.values["L0.A"],
                     "thickness, n fixed": rx.values["L0.thickness"]})
    tab = pd.DataFrame(rows)
    rf, meas = first
    facts = gi.stack_fit(rf, _fit_rows(rf, {"L0.thickness": t, "L0.A": a0}), "reflectometry", [])
    v = {"t": _fmt(t, 2), "sd_float": _fmt(tab["thickness, n floated"].std(ddof=1), 3),
         "sd_fixed": _fmt(tab["thickness, n fixed"].std(ddof=1), 4), "corr": _fmt(abs(np.asarray(rf.correlation)[0, 1]), 3)}
    ev = {"kind": "fit", "technique": "reflectometry", "wl": wl, "meas": meas, "res": rf, "angles": None,
          "table": tab, "corr": rf}
    return {"v": v, "evidence": [ev], "guide": [("stack_reflectance", facts)]}


# --------------------------------------------------------------------------- MSA
def _grr_case(rng, rep, op, part, spec=(98.5, 101.5)):
    from ..datagen import grr_study
    from ..msa import gauge_rr

    data = grr_study(repeat_sigma=rep, operator_sigma=op, part_sigma=part, seed=int(rng.integers(1e6)))
    g = gauge_rr(data, lsl=spec[0], usl=spec[1], k=load_yaml("limits.yaml")["msa"]["grr_k"])
    return data, g


def _grr_v(g):
    sv = g["pct_study_var"]
    return {"grr": _fmt(sv["gauge_rr"], 1), "pt": _fmt(g["pct_tolerance"]["gauge_rr"], 1), "ndc": int(g["ndc"]),
            "repeat": _fmt(sv["repeatability"], 1), "reprod": _fmt(sv["reproducibility"], 1), "verdict": g["verdict"]}


def msa_repeatability(rng, level):
    rep = rng.uniform(0.45, 0.55) * (0.62 + 0.38 * SCALE[level]) / 1.0
    data, g = _grr_case(rng, rep, 0.03, 1.0)
    v = _grr_v(g) | {"tool": str(rng.choice(["FT01", "FT02", "FT03"]))}
    return {"v": v, "evidence": [{"kind": "grr", "g": g, "data": data}], "guide": [("msa_grr", gi.msa_grr(g))]}


def msa_reproducibility(rng, level):
    op = rng.uniform(0.45, 0.55) * (0.62 + 0.38 * SCALE[level])
    data, g = _grr_case(rng, 0.05, op, 1.0)
    bias = data.groupby("operator")["value"].mean()
    v = _grr_v(g) | {"worst_tool": str((bias - bias.median()).abs().idxmax()),
                     "tool_spread": _fmt(float(bias.max() - bias.min()), 3)}
    return {"v": v, "evidence": [{"kind": "grr", "g": g, "data": data}], "guide": [("msa_grr", gi.msa_grr(g))]}


def msa_narrow_parts(rng, level):
    data, g = _grr_case(rng, 0.03, 0.01, rng.uniform(0.04, 0.06))
    part_range = data.groupby("part")["value"].mean()
    v = _grr_v(g) | {"part_range": _fmt(float(part_range.max() - part_range.min()), 3), "tol": 3.0}
    return {"v": v, "evidence": [{"kind": "grr", "g": g, "data": data}], "guide": [("msa_grr", gi.msa_grr(g))]}


def msa_matching(rng, level):
    from ..datagen import matching_study
    from ..msa import fleet_matching

    lim = load_yaml("limits.yaml")["msa"]
    spec, tol = lim["matching_offset_spec"], lim["matching_slope_tol"]
    slope_case = bool(rng.random() < 0.4)
    if slope_case:
        slope, off = 1 + float(rng.choice([-1, 1])) * rng.uniform(0.045, 0.06) * (0.6 + 0.4 * SCALE[level]), 0.0
        off = -(slope - 1) * 100.0  # keep the mean offset small: the problem is proportional
    else:
        slope, off = 1.0, float(rng.choice([-1, 1])) * rng.uniform(1.8, 2.4) * spec * (0.55 + 0.45 * SCALE[level])
    mdf = matching_study(offset=off, slope=slope, seed=int(rng.integers(1e6)))
    res = fleet_matching(mdf, reference="FT01", offset_spec=spec, slope_tol=tol)
    wide = mdf.pivot_table(index=["wafer_id", "site"], columns="tool_id", values="value").reset_index()
    r = res.iloc[0]
    v = {"tool": "FT02", "offset": _fmt(float(r["mean_offset"]), 3), "spec": spec, "slope": _fmt(float(r["deming_slope"]), 4),
         "slope_tol": tol, "kind": {"zh": "比例偏差（斜率）" if slope_case else "固定偏差（offset）",
                                    "en": "proportional bias (slope)" if slope_case else "fixed offset"}}
    answer = {"cause": "C_SLOPE" if slope_case else "C_OFFSET"}
    return {"v": v, "evidence": [{"kind": "matching", "res": res, "wide": wide, "spec": spec}],
            "guide": [("msa_matching", gi.msa_matching(res, spec, tol))], "answer": answer}


# --------------------------------------------------------------------------- recipe studies
def study_technique_choice(rng, level):
    from ..metrology.thinfilm.studies import thickness_sensitivity

    cfg = load_yaml("films.yaml")
    stack, _ = load_stack("gate_oxide_thin", cfg)
    wl = np.linspace(250, 1000, 151)
    thin = bool(rng.random() < (0.85 if level == "basic" else 0.6))
    if thin:
        t0, tol = float(rng.choice([1.5, 2.0, 2.5, 3.0])), float(rng.choice([0.05, 0.08, 0.10]))
    else:
        t0, tol = float(rng.choice([80.0, 100.0, 150.0])), float(rng.choice([2.0, 3.0, 4.0]))
    ts = sorted({1, 2, 3, 5, 10, 20, 50, 100, 200, t0})
    r = thickness_sensitivity(stack, 0, ts, wl, "reflectometry", noise=0.002)
    s = thickness_sensitivity(stack, 0, ts, wl, "se", angles=(65, 70, 75), noise=0.0007)
    pr = float(r.loc[r.thickness_nm == t0, "est_precision_nm"].iloc[0])
    ps = float(s.loc[s.thickness_nm == t0, "est_precision_nm"].iloc[0])
    pt_r, pt_s = 100 * 6 * pr / (2 * tol), 100 * 6 * ps / (2 * tol)
    v = {"t0": t0, "tol": tol, "prec_r": _fmt(pr, 3), "prec_s": _fmt(ps, 4), "pt_r": _fmt(pt_r, 1), "pt_s": _fmt(pt_s, 2),
         "verdict": ({"zh": "反射儀不夠用，需改用 SE 並重新驗證", "en": "reflectometry is not good enough; move to SE and re-validate"}
                     if thin else {"zh": "反射儀足夠，可以沿用（做 GR&R 確認）", "en": "reflectometry is good enough and can stay (confirm with a GR&R)"})}
    answer = {} if thin else {"cause": "C_TECH_OK", "action": "A_KEEP_TECH", "decision": "D_RECIPE_OK"}
    table = pd.DataFrame([{"technique": "reflectometry 反射儀", "1σ precision (nm)": pr, "P/T (%)": pt_r},
                          {"technique": "SE 橢偏儀", "1σ precision (nm)": ps, "P/T (%)": pt_s}])
    return {"v": v, "evidence": [{"kind": "sensitivity", "r": r, "s": s, "table": table}],
            "guide": [("study_sensitivity", gi.study_sensitivity(r, s))], "answer": answer}


# --------------------------------------------------------------------------- DOE
def _doe_run(rng, proc, kind, center, names=None):
    from ..doe import fit_model, make_design, run_experiments, run_sheet, to_coded

    names = names or list(proc["factors"])
    factors = {n: proc["factors"][n] for n in names}
    coded, _ = make_design(kind, len(names), center)
    res = run_experiments(proc, run_sheet(coded, factors, 1, int(rng.integers(1e6))), seed=int(rng.integers(1e6)))
    cdf = pd.DataFrame(to_coded(res[names].to_numpy(float), factors), columns=names)
    return names, factors, res, cdf, fit_model


def doe_curvature_missed(rng, level):
    from ..doe import curvature_test, load_processes

    proc = load_processes()["ald_hk"]
    names, factors, res, cdf, fit_model = _doe_run(rng, proc, "full2", 4)
    resp = "nu_pct"
    fit = fit_model(cdf, res[resp], resp, "quadratic")
    curv = curvature_test(cdf, res[resp])
    v = {"response": resp, "n_runs": len(res), "curv_p": _fmt(curv["p"], 3) if curv else "—",
         "curv_diff": _fmt(curv["difference"], 3) if curv else "—", "r2_pred": _fmt(fit.r2_pred, 2)}
    return {"v": v, "evidence": [{"kind": "doe", "fit": fit, "curv": curv, "runs": res, "names": names}],
            "guide": [("doe_pareto", gi.doe_pareto(fit, curv))]}


def doe_edge_optimum(rng, level):
    from ..doe import load_processes, optimize, to_real

    proc = copy.deepcopy(load_processes()["ald_hk"])
    low_side = bool(rng.random() < 0.5)
    shift = rng.uniform(35, 50) if level == "basic" else rng.uniform(20, 32)
    centre = proc["params"]["t_window_c"]
    proc["factors"]["temp_c"] = ({"low": centre - shift - 40, "high": centre - shift, "unit": "°C"} if low_side else
                                 {"low": centre + shift, "high": centre + shift + 40, "unit": "°C"})
    names, factors, res, cdf, fit_model = _doe_run(rng, proc, "ccd", 4)
    fits = {r: fit_model(cdf, res[r], r, "quadratic") for r in proc["responses"]}
    pred = lambda c: pd.DataFrame({r: f.predict(pd.DataFrame(c, columns=names)) for r, f in fits.items()})  # noqa: E731
    best = optimize(pred, len(names), proc["responses"])
    recipe = dict(zip(names, to_real(best["coded"][None, :], factors)[0]))
    v = {"t_low": factors["temp_c"]["low"], "t_high": factors["temp_c"]["high"], "t_best": _fmt(recipe["temp_c"], 1),
         "D": _fmt(best["D"], 2), "edge": {"zh": "下限" if low_side else "上限", "en": "low" if low_side else "high"}}
    return {"v": v, "evidence": [{"kind": "doe_contour", "fits": fits, "best": best, "recipe": recipe, "names": names,
                                  "factors": factors, "runs": res, "goals": proc["responses"]}],
            "guide": [("doe_contour", gi.doe_contour(best, recipe, names, factors)),
                      ("doe_pareto", gi.doe_pareto(fits["nu_pct"], None))]}


def doe_noisy(rng, level):
    from ..doe import load_processes

    proc = copy.deepcopy(load_processes()["cvd_tin"])
    factor = rng.uniform(5, 7) if level == "basic" else rng.uniform(3.5, 5)
    proc["noise"] = {k: v * factor for k, v in proc["noise"].items()}
    names, factors, res, cdf, fit_model = _doe_run(rng, proc, "ccd", 2)
    fit = fit_model(cdf, res["nu_pct"], "nu_pct", "quadratic")
    v = {"response": "nu_pct", "noise_x": _fmt(factor, 1), "r2_pred": _fmt(fit.r2_pred, 2), "rmse": _fmt(fit.rmse, 3),
         "n_runs": len(res)}
    return {"v": v, "evidence": [{"kind": "doe", "fit": fit, "curv": None, "runs": res, "names": names}],
            "guide": [("doe_pareto", gi.doe_pareto(fit, None))]}


# --------------------------------------------------------------------------- fab simulator
def _fab(rng, events, n_lots=48, seed=None):
    from ..datagen.fab import load_fab_config, simulate_fab

    cfg = copy.deepcopy(load_fab_config())
    cfg["scenarios"] = {"case": events}
    return cfg, simulate_fab(cfg, "case", n_lots, int(rng.integers(1e6)) if seed is None else seed)


def _fab_spc(res, param, group):
    sub = res.long[res.long.parameter == param]
    wafers = wafer_summary(sub)
    lsl = float(sub.lsl.dropna().median()) if sub.lsl.notna().any() else None
    usl = float(sub.usl.dropna().median()) if sub.usl.notna().any() else None
    return _spc_evidence(wafers, group, "mean", param, lsl, usl)


def _fab_yield(res, cfg):
    """Yield trend + die map of the worst wafer the event touched."""
    from ..dashboard.figures import CAUSE_NAME

    w = res.wafers
    hit = set(";".join(res.events["wafer_ids"]).split(";")) if len(res.events) else set()
    pool = w[w.wafer_id.isin(hit)] if hit else w
    row = pool.sort_values("yield").iloc[0]
    codes = np.array(list(res.dies.set_index("wafer_id").loc[row.wafer_id, "map"]))
    gx, gy = np.array(res.grid["x"]), np.array(res.grid["y"])
    cause_step = {s_["code"]: s_["name"] for s_ in cfg["steps"]} | {"D": cfg["defects"].get("inspection_step", "—")}
    die_f = gi.fab_die_map(w.set_index("wafer_id").loc[row.wafer_id], codes, gx, gy, res.grid["r_eff"], w, CAUSE_NAME,
                           cause_step)
    evs = [{"kind": "yield_trend", "w": w},
           {"kind": "die_map", "codes": codes, "gx": gx, "gy": gy, "r_eff": res.grid["r_eff"],
            "title": f"{row.wafer_id}  yield {100 * row['yield']:.1f}%"}]
    return evs, [("fab_yield_trend", gi.fab_yield_trend(w)), ("fab_die_map", die_f)], row


def fab_chamber_excursion(rng, level):
    """A gate-oxide shift on one RTP chamber, pushed away from the device-window centre so it costs yield
    (a shift toward the centre would not be an excursion). The chamber's own offset + PM-age drift decides how
    close to the window it already runs, so a pilot run without the shift measures that baseline first; the
    shift then brings the chamber mean to a set distance from the centre (about a 2-10 point yield loss)."""
    ch = f"RTP0{int(rng.integers(1, 3))}-{str(rng.choice(['A', 'B']))}"
    start = int(rng.integers(26, 34))
    seed = int(rng.integers(1e6))  # same seed = same random draws, so the pilot and the case share the baseline
    min_shift = {"basic": 0.016, "intermediate": 0.012, "advanced": 0.010}[level]  # still visible on the chart
    dist = rng.uniform(*{"basic": (0.040, 0.043), "intermediate": (0.037, 0.041), "advanced": (0.035, 0.039)}[level])
    event = lambda m: [{"type": "shift", "step": "GATE_OX", "where": ch, "start_lot": start, "n_lots": 10,  # noqa: E731
                        "magnitude": m}]
    _, pilot = _fab(rng, event(0.0), seed=seed)
    hit = pilot.wafers.wafer_id.isin(pilot.events.iloc[0]["wafer_ids"].split(";"))
    target = (pilot.wafers.loc[hit, "true_gate_ox_thk"].mean() if hit.any() else 3.0) - 3.0
    sign = 1.0 if target >= 0 else -1.0
    mag = None
    for _ in range(3):
        new = sign * max(min_shift, dist - abs(target))
        if new == mag:
            break  # held at the minimum visible shift
        mag = new
        cfg, res = _fab(rng, event(mag), seed=seed)
        impact = res.events.iloc[0]["yield_impact"]
        if -0.11 <= impact <= -0.02:
            break
        dist += 0.003 if impact > -0.02 else -0.003
    ev, facts = _fab_spc(res, "gate_ox_thk", "chamber_id")
    evs, guide, row = _fab_yield(res, cfg)
    ver = _verified(rng, level)
    v = {"chamber": ch, "shift": _fmt(mag, 3), "start_lot": f"D{start + 1:04d}", "impact": _fmt(100 * res.events.iloc[0]["yield_impact"], 2),
         "worst_wafer": row.wafer_id, "worst_yield": _fmt(100 * row["yield"], 1), "verified": VERIFIED_TEXT[ver]}
    return {"v": v, "evidence": [ev] + evs, "guide": [("spc_chart", facts)] + guide, "answer": _process_answer(ver)}


def fab_particle_event(rng, level):
    tool = str(rng.choice(["CVD01", "CVD02"]))
    start = int(rng.integers(30, 40))
    mag = rng.uniform(5, 7) * (0.6 + 0.4 * SCALE[level])
    cfg, res = _fab(rng, [{"type": "defects", "step": "TIN_DEP", "where": tool, "start_lot": start, "n_lots": 4,
                           "magnitude": mag, "pattern": "edge_ring"}])
    ev, facts = _fab_spc(res, "defect_density", "chamber_id")
    evs, guide, row = _fab_yield(res, cfg)
    v = {"tool": tool, "start_lot": f"D{start + 1:04d}", "impact": _fmt(100 * res.events.iloc[0]["yield_impact"], 2),
         "worst_wafer": row.wafer_id, "worst_yield": _fmt(100 * row["yield"], 1)}
    return {"v": v, "evidence": evs + [ev], "guide": guide + [("spc_chart", facts)]}


def fab_metro_offset(rng, level):
    metro = str(rng.choice(["FT01", "FT02"]))
    start = int(rng.integers(20, 30))
    mag = float(rng.choice([-1, 1])) * rng.uniform(0.026, 0.034) * (0.6 + 0.4 * SCALE[level])
    cfg, res = _fab(rng, [{"type": "metro_offset", "step": "GATE_OX", "where": metro, "start_lot": start, "n_lots": 40,
                           "magnitude": mag}])
    ev1, f1 = _fab_spc(res, "gate_ox_thk", "chamber_id")
    ev1["title"] = "依 chamber 分組 · grouped by chamber"
    ev2, f2 = _fab_spc(res, "gate_ox_thk", "metro_tool_id")
    ev2["title"] = "依量測機台分組 · grouped by metrology tool"
    w = res.wafers
    v = {"metro": metro, "offset": _fmt(mag, 3), "start_lot": f"D{start + 1:04d}", "impact": _fmt(100 * res.events.iloc[0]["yield_impact"], 2),
         "yield": _fmt(100 * w["yield"].mean(), 1)}
    return {"v": v, "evidence": [ev1, ev2, {"kind": "yield_trend", "w": w}],
            "guide": [("spc_chart", f2), ("spc_chart", f1), ("fab_yield_trend", gi.fab_yield_trend(w))]}


GENERATORS = {
    "spc_chamber_shift": spc_chamber_shift, "spc_slow_drift": spc_slow_drift, "spc_metro_offset": spc_metro_offset,
    "spc_uniformity_only": spc_uniformity_only, "spc_cpk_off_center": spc_cpk_off_center, "spc_false_alarm": spc_false_alarm,
    "wafer_edge_roll": wafer_edge_roll, "wafer_tilt": wafer_tilt, "wafer_bad_site": wafer_bad_site,
    "wafer_bowl_after_pm": wafer_bowl_after_pm, "stack_wrong_underlayer": stack_wrong_underlayer,
    "stack_float_n_thin": stack_float_n_thin, "msa_repeatability": msa_repeatability,
    "msa_reproducibility": msa_reproducibility, "msa_narrow_parts": msa_narrow_parts, "msa_matching": msa_matching,
    "study_technique_choice": study_technique_choice, "doe_curvature_missed": doe_curvature_missed,
    "doe_edge_optimum": doe_edge_optimum, "doe_noisy": doe_noisy, "fab_chamber_excursion": fab_chamber_excursion,
    "fab_particle_event": fab_particle_event, "fab_metro_offset": fab_metro_offset,
}
