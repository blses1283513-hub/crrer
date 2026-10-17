"""Case generators built on the metrology map: fit quality (GOF), implant sheet-resistance monitors and choosing a
measurement technique.

Same contract as generators.py: (rng, level) -> {v, evidence, guide, answer}; every type has more than one outcome
and the data decides it. All synthetic: generic fab practice, no real lots, products, tools or recipes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..guide import insights as gi
from .generators import SCALE, T0, _fmt, _lot, _spc_evidence


def _bi(zh: str, en: str) -> dict:
    return {"zh": zh, "en": en}


# --------------------------------------------------------------------------- a fit with low GOF
def film_gof_reject(rng, level):
    """A new reflectometry recipe reports a GOF under its limit. Either the model lacks a layer that is really on the
    wafer (a thin nitride cap), or the thickness search window excludes the real thickness, so the fit lands on the
    wrong fringe order (a 2000 Å oxide read near 1000 Å)."""
    from ..config import load_stack, load_yaml, wavelengths
    from ..metrology.thinfilm import FitParameter, Layer, fit, simulate_reflectometry
    from ..config import material_library

    cfg = load_yaml("films.yaml")
    stack, _ = load_stack("thermal_oxide_100", cfg)
    lib = material_library(cfg)
    wl = wavelengths(cfg)
    kind = "layer" if rng.random() < 0.55 else "order"
    limit = 0.995
    for _ in range(30):
        if kind == "layer":
            nominal = float(rng.uniform(90, 130))
            cap = float(rng.uniform(*{"basic": (9, 12), "intermediate": (7, 9), "advanced": (5.5, 7)}[level]))
            truth = type(stack)(layers=[Layer(lib["Si3N4"], cap), Layer(lib["SiO2"], nominal)], substrate=stack.substrate,
                                ambient=stack.ambient, name="truth")
            params = [FitParameter(0, bounds=(1, 1500))]
            model = stack.copy_with([nominal])
        else:
            nominal = float(rng.uniform(190, 215))
            cap = 0.0
            truth = stack.copy_with([nominal])
            centre = nominal / 2
            params = [FitParameter(0, initial=centre, bounds=(centre - 40, centre + 40))]  # window excludes the real film
            model = stack.copy_with([centre])
        meas = simulate_reflectometry(truth, wl, noise=0.002, rng=int(rng.integers(1e6)))
        res = fit(model, meas, params)
        if res.gof < limit - {"basic": 0.02, "intermediate": 0.008, "advanced": 0.002}[level]:
            break
    fitted = res.values["L0.thickness"]
    rows = [{"parameter": "L0.thickness", "true": np.nan if kind == "layer" else nominal, "fitted": fitted,
             "± 1σ": res.stderr["L0.thickness"], "error": np.nan if kind == "layer" else fitted - nominal}]
    facts = gi.stack_fit(res, rows, "reflectometry", [])
    table = pd.DataFrame([{"item": "GOF", "value": f"{res.gof:.4f}  (recipe limit {limit})"},
                          {"item": "reduced χ²", "value": f"{res.chi2_red:.1f}"},
                          {"item": "fitted thickness 擬合厚度", "value": f"{fitted:.1f} nm"},
                          {"item": "nominal 標稱厚度", "value": f"{nominal:.0f} nm"},
                          {"item": "search window 搜尋範圍", "value": f"{params[0].bounds[0]:.0f}–{params[0].bounds[1]:.0f} nm"}])
    v = {"gof": _fmt(res.gof, 4), "limit": limit, "chi2": _fmt(res.chi2_red, 1), "fitted": _fmt(fitted, 1),
         "nominal": _fmt(nominal, 0), "lo": _fmt(params[0].bounds[0], 0), "hi": _fmt(params[0].bounds[1], 0),
         "ratio": _fmt(fitted / nominal, 2),
         "verdict": (_bi("殘差有固定的結構，改變厚度也消不掉；擬合厚度接近標稱：模型少了一層真的存在的膜（例如很薄的氮化矽 cap）",
                         "the residual has a structure no thickness change removes, and the fitted thickness is near nominal: the "
                         "model is missing a layer that is really on the wafer (e.g. a thin nitride cap)") if kind == "layer" else
                     _bi(f"擬合厚度只有標稱的 {fitted / nominal:.2f} 倍，而且真正的厚度不在搜尋範圍（{params[0].bounds[0]:.0f}–"
                         f"{params[0].bounds[1]:.0f} nm）內：擬合落在錯的干涉級數",
                         f"the fitted thickness is only {fitted / nominal:.2f}× nominal and the real thickness lies outside the "
                         f"search window ({params[0].bounds[0]:.0f}–{params[0].bounds[1]:.0f} nm): the fit landed on the wrong "
                         "fringe order")),
         "ask": (_bi("不要發行這個 recipe：把缺的那層（含 n、k）加進模型，重新擬合，並用參考量測（例如 TEM 或 SE）驗證",
                     "do not release the recipe: add the missing layer (with its n, k) to the model, refit, and validate against "
                     "a reference measurement (e.g. TEM or SE)") if kind == "layer" else
                 _bi("把厚度搜尋範圍放寬到涵蓋標稱值（或用全域搜尋）、修正初始值，重新擬合後用參考量測確認；修正前不要用這些讀值",
                     "widen the thickness search window to cover the nominal value (or use a global search), correct the starting "
                     "value, refit and confirm with a reference; do not use these readings until then"))}
    answer = ({"cause": "C_MISSING_LAYER", "action": "A_ADD_LAYER", "decision": "D_RECIPE_NOT_READY"} if kind == "layer" else
              {"cause": "C_WRONG_ORDER", "action": "A_WIDEN_SEARCH", "decision": "D_RECIPE_FIX"})
    ev = {"kind": "fit", "technique": "reflectometry", "wl": wl, "meas": meas, "res": res, "angles": None,
          "table": pd.DataFrame([{"parameter": r["parameter"], "fitted": r["fitted"], "± 1σ": r["± 1σ"]} for r in rows]),
          "notes": _bi(f"recipe 模型：單層 SiO₂ on Si；GOF 接受標準 ≥ {limit}（這個 recipe 自己訂的）",
                       f"Recipe model: single SiO₂ layer on Si; GOF acceptance ≥ {limit} (set by this recipe)")}
    return {"v": v, "answer": answer,
            "evidence": [ev, {"kind": "table", "table": table, "title": "擬合結果 · fit result"}],
            "guide": [("stack_reflectance", facts)]}


# --------------------------------------------------------------------------- implant sheet-resistance monitor
IMPLANTERS = ["IMP01", "IMP02", "IMP03"]
ANNEALS = ["RTA01", "RTA02"]


def implant_rs_monitor(rng, level):
    """Daily implant monitor wafers: sheet resistance after anneal (Rs) and the pre-anneal thermal-wave signal (TW).
    Either one implanter's dose drifted (Rs and TW move on that implanter only, on both anneal tools), or one anneal
    tool lost activation (Rs moves on every implanter's monitors annealed there; TW is normal)."""
    kind = "dose" if rng.random() < 0.55 else "anneal"
    bad_imp = str(rng.choice(IMPLANTERS))
    bad_rta = str(rng.choice(ANNEALS))
    shift = {"basic": 0.045, "intermediate": 0.032, "advanced": 0.024}[level] * rng.uniform(0.9, 1.1)
    start = int(rng.integers(16, 22))
    rows = []
    for day in range(30):
        for imp in IMPLANTERS:
            rta = ANNEALS[int(rng.integers(2))]
            rs = 120.0 * (1 + rng.normal(0, 0.004))
            tw = 640.0 * (1 + rng.normal(0, 0.004))
            if day >= start and kind == "dose" and imp == bad_imp:
                rs *= 1 + shift          # less dose -> higher Rs (sensitivity about 1 at low dose)
                tw *= 1 - 0.8 * shift    # less damage -> lower thermal-wave signal
            if day >= start and kind == "anneal" and rta == bad_rta:
                rs *= 1 + shift          # less activation -> higher Rs; the as-implanted TW cannot see it
            lot = f"M{day + 1:03d}{imp[-1]}"
            rows.append({"lot_id": lot, "wafer_id": f"{lot}.01", "tool_id": imp, "chamber_id": imp, "anneal_tool": rta,
                         "metro_tool_id": "RS01", "parameter": "sheet_res", "timestamp": T0 + pd.Timedelta(hours=8 * day + 2 * IMPLANTERS.index(imp)),
                         "mean": rs, "std": rs * 0.006, "nu_1sigma_pct": 0.6, "tw": tw})
    w = pd.DataFrame(rows)
    lsl, usl = 120.0 * 0.95, 120.0 * 1.05
    ev1, f1 = _spc_evidence(w, "chamber_id", "mean", "sheet_res", lsl, usl, title="Rs 依佈植機分組 · by implanter")
    ev2, f2 = _spc_evidence(w, "anneal_tool", "mean", "sheet_res", lsl, usl, title="Rs 依退火機台分組 · by anneal tool")
    tw = w.assign(mean=w["tw"], std=w["tw"] * 0.004)
    ev3, f3 = _spc_evidence(tw, "chamber_id", "mean", "thermal_wave", None, None, title="退火前 thermal-wave 依佈植機 · pre-anneal thermal-wave by implanter")
    late = w[w.index >= w.index[w["timestamp"] >= T0 + pd.Timedelta(hours=8 * start)].min()]
    by_imp = late.groupby("chamber_id")["mean"].mean() / 120 - 1
    by_rta = late.groupby("anneal_tool")["mean"].mean() / 120 - 1
    tw_late = late.groupby("chamber_id")["tw"].mean() / 640 - 1
    v = {"bad_imp": bad_imp, "bad_rta": bad_rta, "start_day": start + 1, "shift_pct": _fmt(100 * shift, 1),
         "imp_shift": _fmt(100 * float(by_imp.max()), 1), "imp_worst": str(by_imp.idxmax()),
         "rta_shift": _fmt(100 * float(by_rta.max()), 1), "rta_worst": str(by_rta.idxmax()),
         "tw_shift": _fmt(100 * float(tw_late.abs().max()), 1),
         "key": bad_imp if kind == "dose" else bad_rta,
         "ask": (_bi(f"請 EE hold {bad_imp} 並檢查劑量量測（Faraday cup、beam current），用監控片重新 qual；兩台退火機都正常",
                     f"please hold {bad_imp} and have EE check its dosimetry (Faraday cup, beam current), then re-qualify it with "
                     "monitor wafers; both anneal tools are fine") if kind == "dose" else
                 _bi(f"請 EE 檢查 {bad_rta} 的溫度校正、燈管／分區與 recipe，並重新退火一片監控片確認；佈植機不用動",
                     f"please have EE check {bad_rta}'s temperature calibration, lamps / zones and recipe, and re-anneal a monitor "
                     "to confirm; leave the implanters alone")),
         "verdict": (_bi(f"只有 {bad_imp} 的監控片 Rs 上升約 {100 * shift:.1f}%，兩台退火機都一樣，而且退火前的 thermal-wave 也在 {bad_imp} 下降：是 {bad_imp} 的劑量偏移",
                         f"only {bad_imp}'s monitors rose about {100 * shift:.1f}% in Rs, on both anneal tools, and the pre-anneal "
                         f"thermal-wave also dropped on {bad_imp}: a dose drift on {bad_imp}") if kind == "dose" else
                     _bi(f"三台佈植機在 {bad_rta} 退火的監控片 Rs 都上升約 {100 * shift:.1f}%，退火前的 thermal-wave 全部正常：是 {bad_rta} 的活化（退火）問題，佈植機沒事",
                         f"monitors from all three implanters annealed in {bad_rta} rose about {100 * shift:.1f}% in Rs, while the "
                         f"pre-anneal thermal-wave is normal everywhere: an activation (anneal) problem on {bad_rta}; the implanters "
                         "are fine"))}
    answer = ({"cause": "C_DOSE_DRIFT", "action": "A_IMPLANTER_CHECK", "decision": "D_HOLD", "notify": ["EE", "PE", "PIE_YE"]}
              if kind == "dose" else
              {"cause": "C_ANNEAL_DRIFT", "action": "A_ANNEAL_CHECK", "decision": "D_HOLD", "notify": ["EE", "PE", "PIE_YE"]})
    return {"v": v, "answer": answer, "evidence": [ev1, ev2, ev3],
            "guide": [("spc_chart", f1), ("spc_chart", f2), ("spc_chart", f3)]}


TECH_GENERATORS = {"film_gof_reject": film_gof_reject, "implant_rs_monitor": implant_rs_monitor}
