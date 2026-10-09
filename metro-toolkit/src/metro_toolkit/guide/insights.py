"""Data-driven reading of each dashboard chart -> Facts (status + findings + template values).

Every function documents the Facts.v keys it fills; charts.yaml templates may use exactly those keys
(plus {finding} and {status}). Thresholds follow common fab practice and are stated in the findings,
so the reader can see why a status was given.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import Facts

# Zernike term -> (zh, en) physical reading
SIGNATURE = {
    "tilt_x": ("左右傾斜 tilt-x：一側厚一側薄，常見於加熱器／氣流偏一側、晶圓偏位、機台水平",
               "left-right tilt: one side thicker, typical of a heater or gas-flow imbalance, wafer offset or tool levelling"),
    "tilt_y": ("上下傾斜 tilt-y：notch 方向一側厚，常見於氣流方向性、晶圓放置偏移",
               "top-bottom tilt: thicker toward one side of the notch axis, typical of directional gas flow or placement"),
    "bowl": ("碗形 bowl：中心與邊緣差，常見於溫度分布、噴頭（showerhead）氣流、CMP 壓力分布",
             "bowl: centre vs edge difference, typical of temperature profile, showerhead flow or CMP pressure profile"),
    "astig_0": ("鞍形 astigmatism 0°：兩個方向相反，常見於夾持（chuck）、應力或兩向不對稱的氣流",
                "saddle (astigmatism 0°): opposite in two directions, typical of chucking, stress or 2-fold flow asymmetry"),
    "astig_45": ("鞍形 astigmatism 45°：同上，方向轉 45°", "saddle (astigmatism 45°): same as above, rotated 45°"),
    "edge_roll": ("球面項 edge roll（6ρ⁴−6ρ²+1）：中心與最外圈同向、約 0.7R 處反向，要和 bowl 一起看；"
                  "只在最外圈突變時常見於邊緣環（edge ring / focus ring）磨耗、斜面、邊緣排除區附近的製程",
                  "spherical term edge roll (6ρ⁴−6ρ²+1): centre and outer ring move together, opposite near 0.7R; read it "
                  "with bowl. A change confined to the outer ring is typical of edge/focus ring wear, bevel or edge-exclusion effects"),
}
STAT_NAME = {"mean": ("晶圓平均值", "wafer mean"), "nu_1sigma_pct": ("片內 1σ %（不均勻度）", "within-wafer 1σ % (non-uniformity)"),
             "range": ("片內全距", "within-wafer range")}


def _bi(zh, en) -> dict:
    return {"zh": zh, "en": en}


def _f(x, nd=3) -> str:
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{nd}g}"


# --------------------------------------------------------------------------- film stack fit
def stack_fit(res, rows: list[dict], technique: str, fixed_changed: list[int]) -> Facts:
    """v: technique, chi2, worst_param, worst_err, worst_sigma, err_sigma, max_corr, corr_pair, fixed_layers."""
    f = Facts()
    chi2 = float(res.chi2_red)
    worst = max(rows, key=lambda r: abs(r["error"]) / max(r["± 1σ"], 1e-12)) if rows else None
    err_sigma = abs(worst["error"]) / max(worst["± 1σ"], 1e-12) if worst else 0.0
    corr = np.asarray(res.correlation, float) if len(res.labels) > 1 else np.eye(1)  # one floated parameter: no pair
    off = np.abs(corr - np.eye(len(corr)))
    i, j = np.unravel_index(off.argmax(), off.shape)
    max_corr = float(off.max())
    f.v = {"technique": technique, "chi2": chi2, "worst_param": worst["parameter"] if worst else "—",
           "worst_err": worst["error"] if worst else 0.0, "worst_sigma": worst["± 1σ"] if worst else 0.0,
           "err_sigma": err_sigma, "max_corr": max_corr,
           "corr_pair": f"{res.labels[i]} / {res.labels[j]}" if len(res.labels) > 1 else "—",
           "fixed_layers": ", ".join(f"L{k}" for k in fixed_changed) or "—"}
    if chi2 > 3:
        f.worse("act").add(f"reduced χ² = {chi2:.2f}（> 3）：模型和量測光譜不吻合，膜厚數字不可信",
                           f"reduced χ² = {chi2:.2f} (> 3): the model does not reproduce the spectrum; do not trust the thickness")
    elif chi2 > 1.5:
        f.worse("watch").add(f"reduced χ² = {chi2:.2f}（1.5–3）：擬合尚可但有系統性殘差",
                             f"reduced χ² = {chi2:.2f} (1.5–3): acceptable but with systematic residuals")
    else:
        f.add(f"reduced χ² = {chi2:.2f}（≈ 1 表示殘差和雜訊同等級）", f"reduced χ² = {chi2:.2f} (≈ 1 means residuals match the noise)")
    if fixed_changed and err_sigma > 3:
        f.worse("act").add(
            f"固定層 {f.v['fixed_layers']} 與 recipe 不符：{f.v['worst_param']} 偏差 {worst['error']:+.3f}"
            f"（{err_sigma:.0f}σ），但 χ² 沒有警告 → 這是模型偏差，回報的 ±1σ 不包含它",
            f"Fixed layer {f.v['fixed_layers']} differs from the recipe: {f.v['worst_param']} is off by {worst['error']:+.3f} "
            f"({err_sigma:.0f}σ) while χ² raises no alarm; model bias is not inside the reported ±1σ")
    elif worst is not None:
        f.add(f"最大誤差 {f.v['worst_param']}：{worst['error']:+.4f}（{err_sigma:.1f}σ）",
              f"largest error {f.v['worst_param']}: {worst['error']:+.4f} ({err_sigma:.1f}σ)")
    if max_corr > 0.95:
        f.worse("watch").add(f"參數相關 |r| = {max_corr:.3f}（{f.v['corr_pair']}）：兩個參數互相抵換，不要同時浮動",
                             f"parameter correlation |r| = {max_corr:.3f} ({f.v['corr_pair']}): they trade off; do not float both")
    return f


# --------------------------------------------------------------------------- wafer map page
def wafer_page(w: pd.DataFrame, um: dict, all_wafers: pd.DataFrame, zk: dict, rp: pd.DataFrame, param: str) -> dict:
    """Facts for wafer_map, wafer_zernike, wafer_radial.
    v: wafer, chamber, param, unit, mean, nu, nu_median, nu_ratio, range, n_sites, n_oos, lsl, usl,
       sig_term, sig_text, sig_coef, sig_share, r2, center, edge, ce_diff, ce_pct, roll."""
    unit = str(w["unit"].iloc[0]) if "unit" in w and len(w) else ""
    chamber = str(w["chamber_id"].iloc[0]) if "chamber_id" in w and len(w) else "—"
    nu_med = float(all_wafers["nu_1sigma_pct"].median())
    ratio = um["nu_1sigma_pct"] / nu_med if nu_med > 0 else np.nan
    lsl = float(w["lsl"].dropna().median()) if "lsl" in w and w["lsl"].notna().any() else np.nan
    usl = float(w["usl"].dropna().median()) if "usl" in w and w["usl"].notna().any() else np.nan
    n_oos = int(((w["value"] < lsl) | (w["value"] > usl)).sum()) if np.isfinite(lsl) and np.isfinite(usl) else 0
    coef = {k: v for k, v in zk["coefficients"].items() if k != "piston"}
    tot = sum(c * c for c in coef.values()) or 1.0
    term = max(coef, key=lambda k: abs(coef[k])) if coef else "bowl"
    r = np.hypot(w["x"], w["y"])
    R = float(r.max()) or 1.0
    center = float(w.loc[r <= 0.3 * R, "value"].mean()) if (r <= 0.3 * R).any() else float(w["value"].iloc[r.argmin()])
    edge = float(w.loc[r >= 0.8 * R, "value"].mean()) if (r >= 0.8 * R).any() else np.nan
    roll = float(rp["mean"].iloc[-1] - rp["mean"].iloc[-2]) if len(rp) >= 2 else np.nan
    v = {"wafer": str(w["wafer_id"].iloc[0]), "chamber": chamber, "param": param, "unit": unit, "mean": um["mean"],
         "nu": um["nu_1sigma_pct"], "nu_median": nu_med, "nu_ratio": ratio, "range": um["range"], "n_sites": um["n_sites"],
         "n_oos": n_oos, "lsl": lsl, "usl": usl, "sig_term": term, "sig_text": _bi(*SIGNATURE.get(term, (term, term))),
         "sig_coef": coef.get(term, 0.0), "sig_share": 100 * coef.get(term, 0.0) ** 2 / tot, "r2": zk["r2"],
         "center": center, "edge": edge, "ce_diff": edge - center,
         "ce_pct": 100 * (edge - center) / um["mean"] if um["mean"] else np.nan, "roll": roll}

    m = Facts(v=v)
    if n_oos:
        m.worse("act").add(f"{n_oos} 個量測點超出規格（{_f(lsl)}–{_f(usl)} {unit}）→ OOS，需要 disposition",
                           f"{n_oos} site(s) out of spec ({_f(lsl)}–{_f(usl)} {unit}) → OOS, needs disposition")
    if np.isfinite(ratio) and ratio > 2:
        m.worse("act").add(f"片內不均勻度 1σ NU = {um['nu_1sigma_pct']:.3f}%，是全部晶圓中位數（{nu_med:.3f}%）的 {ratio:.1f} 倍",
                           f"within-wafer NU 1σ = {um['nu_1sigma_pct']:.3f}%, {ratio:.1f}× the fleet median ({nu_med:.3f}%)")
    elif np.isfinite(ratio) and ratio > 1.3:
        m.worse("watch").add(f"1σ NU = {um['nu_1sigma_pct']:.3f}%，高於中位數 {nu_med:.3f}%（{ratio:.1f} 倍）",
                             f"NU 1σ = {um['nu_1sigma_pct']:.3f}%, above the fleet median {nu_med:.3f}% ({ratio:.1f}×)")
    else:
        m.add(f"1σ NU = {um['nu_1sigma_pct']:.3f}%，與全部晶圓中位數 {nu_med:.3f}% 同等級",
              f"NU 1σ = {um['nu_1sigma_pct']:.3f}%, in line with the fleet median {nu_med:.3f}%")
    m.add(f"主要空間形狀：{SIGNATURE.get(term, (term,))[0]}", f"main spatial shape: {SIGNATURE.get(term, (term, term))[1]}")

    z = Facts(status=m.status, v=v)
    z.add(f"最大的 Zernike 項是 {term}（係數 {coef.get(term, 0):+.4g} {unit}，佔係數平方和 {v['sig_share']:.0f}%）",
          f"largest Zernike term is {term} (coefficient {coef.get(term, 0):+.4g} {unit}, {v['sig_share']:.0f}% of the summed "
          "squared coefficients)")
    z.add(f"低階 Zernike 解釋了 {100 * zk['r2']:.0f}% 的片內變異" + ("（形狀清楚，是系統性的機台／製程特徵）" if zk["r2"] > 0.6
                                                          else "（剩下的是局部或隨機變異）"),
          f"low-order Zernike explains {100 * zk['r2']:.0f}% of within-wafer variance" +
          (" (a clear, systematic tool/process signature)" if zk["r2"] > 0.6 else " (the rest is local or random)"))

    rr = Facts(status=m.status, v=v)
    if np.isfinite(v["ce_diff"]):
        rr.add(f"邊緣 − 中心 = {v['ce_diff']:+.4g} {unit}（{v['ce_pct']:+.2f}%）",
               f"edge − centre = {v['ce_diff']:+.4g} {unit} ({v['ce_pct']:+.2f}%)")
    if np.isfinite(roll):
        rr.add(f"最外圈相對前一圈變化 {roll:+.4g} {unit}" + ("（邊緣滾降 edge roll-off）" if abs(roll) > 2 * (rp['std'].median() or 0)
                                                     else ""),
               f"outermost ring vs the previous ring: {roll:+.4g} {unit}" +
               (" (edge roll-off)" if abs(roll) > 2 * (rp['std'].median() or 0) else ""))
    return {"wafer_map": m, "wafer_zernike": z, "wafer_radial": rr}


# --------------------------------------------------------------------------- SPC
def spc(charts: dict, wafers: pd.DataFrame, group: str, stat: str, ctype: str, param: str,
        cap: list[dict] | None = None, lsl=None, usl=None, recent: int = 5) -> Facts:
    """v: param, stat_name, chart, group_by, n_groups, groups_ooc, n_ooc, worst_group, first_wafer, first_time,
       latest_wafer, rules, shift_sigma, cpk_min, cpk_group, lsl, usl, n_points, recent_groups."""
    f = Facts()
    ooc_groups, rules, first, recent_hit, shifts = [], set(), None, [], {}
    n_ooc, n_points, latest = 0, 0, None
    for g, ch in charts.items():
        sw = wafers[wafers[group] == g].sort_values("timestamp").reset_index(drop=True)
        n_points += len(ch.statistic)
        if len(sw):
            latest = sw["wafer_id"].iloc[-1]
        idx = ch.out_of_control
        if ch.sigma > 0 and len(ch.statistic) >= 5:
            tail = np.asarray(ch.statistic[-recent:], float)
            shifts[g] = float((tail.mean() - ch.cl) / ch.sigma) if ch.chart_type == "IMR" else 0.0
        if idx.size:
            ooc_groups.append(str(g))
            n_ooc += int(idx.size)
            rules |= {v[1] for v in ch.violations}
            i0 = int(idx[0])
            if first is None or sw["timestamp"].iloc[i0] < first[1]:
                first = (sw["wafer_id"].iloc[i0], sw["timestamp"].iloc[i0], g)
            if idx.max() >= len(ch.statistic) - recent:
                recent_hit.append(str(g))
    worst = max(shifts, key=lambda k: abs(shifts[k])) if shifts else None
    cpk_min, cpk_group = np.nan, "—"
    if cap:
        c = min(cap, key=lambda r: r["Cpk"])
        cpk_min, cpk_group = float(c["Cpk"]), str(c[group])
    sz, se = STAT_NAME.get(stat, (stat, stat))
    f.v = {"param": param, "stat_name": _bi(sz, se), "chart": ctype, "group_by": group, "n_groups": len(charts),
           "groups_ooc": ", ".join(ooc_groups) or "—", "n_ooc": n_ooc,
           "worst_group": str(worst) if worst is not None else "—",
           "first_wafer": first[0] if first else "—", "first_time": str(first[1])[:16] if first else "—",
           "latest_wafer": latest or "—", "rules": ", ".join(f"WE{r}" for r in sorted(rules)) or "—",
           "shift_sigma": shifts.get(worst, 0.0) if worst is not None else 0.0, "cpk_min": cpk_min,
           "cpk_group": cpk_group, "lsl": lsl, "usl": usl, "n_points": n_points,
           "recent_groups": ", ".join(recent_hit) or "—"}
    if recent_hit:
        f.worse("act").add(f"{', '.join(recent_hit)} 在最近 {recent} 點內有 OOC（{f.v['rules']}）→ 依 OCAP 處理",
                           f"{', '.join(recent_hit)} went OOC within the last {recent} points ({f.v['rules']}) → follow the OCAP")
    elif ooc_groups:
        f.worse("watch").add(f"{', '.join(ooc_groups)} 歷史上有 {n_ooc} 個 OOC 點（最早 {f.v['first_wafer']}），最近 {recent} 點已回到管制內",
                             f"{', '.join(ooc_groups)} had {n_ooc} OOC point(s) in the past (first {f.v['first_wafer']}); "
                             f"the last {recent} points are back in control")
    else:
        f.add(f"{len(charts)} 個 {group} 都在管制內（{n_points} 點，無 WE 規則違規）",
              f"all {len(charts)} {group} groups are in control ({n_points} points, no WE rule violations)")
    if worst is not None and abs(f.v["shift_sigma"]) > 1:
        f.add(f"{worst} 最近 {recent} 點平均偏離中心線 {f.v['shift_sigma']:+.1f}σ",
              f"{worst}: last {recent} points average {f.v['shift_sigma']:+.1f}σ from the centre line")
    if np.isfinite(cpk_min):
        if cpk_min < 1.0:
            f.worse("act").add(f"最低 Cpk = {cpk_min:.2f}（{cpk_group}）< 1.0：製程能力不足，會產生 OOS",
                               f"lowest Cpk = {cpk_min:.2f} ({cpk_group}) < 1.0: not capable, OOS will occur")
        elif cpk_min < 1.33:
            f.worse("watch").add(f"最低 Cpk = {cpk_min:.2f}（{cpk_group}），低於一般要求 1.33",
                                 f"lowest Cpk = {cpk_min:.2f} ({cpk_group}), below the usual 1.33 requirement")
        else:
            f.add(f"所有 {group} 的 Cpk ≥ {cpk_min:.2f}（≥ 1.33）", f"all {group} groups have Cpk ≥ {cpk_min:.2f} (≥ 1.33)")
    return f


# --------------------------------------------------------------------------- MSA
def msa_grr(g: dict) -> Facts:
    """v: grr_sv, pt, ndc, verdict, repeat_sv, reprod_sv, dominant, part_sv."""
    sv, pt = g["pct_study_var"], g.get("pct_tolerance", {})
    dom = "repeatability" if sv["repeatability"] >= sv["reproducibility"] else "reproducibility"
    f = Facts(v={"grr_sv": sv["gauge_rr"], "pt": pt.get("gauge_rr", np.nan), "ndc": g["ndc"], "verdict": g["verdict"],
                 "repeat_sv": sv["repeatability"], "reprod_sv": sv["reproducibility"], "part_sv": sv["part_to_part"],
                 "dominant": _bi("重複性（同一機台重複量測的雜訊）" if dom == "repeatability" else "再現性（機台之間的差異）",
                                 "repeatability (noise of repeated measurements on one tool)" if dom == "repeatability"
                                 else "reproducibility (tool-to-tool difference)")})
    head = g.get("headline_pct", sv["gauge_rr"])
    if head >= 30:
        f.worse("act")
    elif head >= 10 or g["ndc"] < 5:
        f.worse("watch")
    f.add(f"%GRR = {sv['gauge_rr']:.1f}%（study var），P/T = {_f(pt.get('gauge_rr'), 3)}%，ndc = {g['ndc']} → {g['verdict']}",
          f"%GRR = {sv['gauge_rr']:.1f}% (study var), P/T = {_f(pt.get('gauge_rr'), 3)}%, ndc = {g['ndc']} → {g['verdict']}")
    f.add(f"量測變異主要來自 {f.v['dominant']['zh']}", f"measurement variation is dominated by {f.v['dominant']['en']}")
    if g["ndc"] < 5:
        f.add(f"ndc = {g['ndc']} < 5：量測系統分辨不出足夠的產品差異，不適合做 SPC／分 bin",
              f"ndc = {g['ndc']} < 5: the gauge cannot resolve enough part-to-part classes for SPC or sorting")
    return f


def msa_matching(res: pd.DataFrame, offset_spec: float, slope_tol: float) -> Facts:
    """v: tool, offset, spec, slope, slope_tol, sd_diff, verdict."""
    r = res.iloc[0]
    matched = bool(r["matched"])
    f = Facts(v={"tool": r["tool"], "offset": r["mean_offset"], "spec": offset_spec, "slope": r["deming_slope"],
                 "slope_tol": slope_tol, "sd_diff": r["sd_difference"],
                 "verdict": _bi("匹配 matched" if matched else "不匹配 not matched", "matched" if matched else "not matched")})
    if not matched:
        f.worse("act").add(
            f"{r['tool']} 對參考機台：平均偏差 {r['mean_offset']:+.3f} nm（規格 ±{offset_spec}），Deming 斜率 {r['deming_slope']:.4f}"
            f"（容許 1 ± {slope_tol}）→ 不匹配",
            f"{r['tool']} vs reference: mean offset {r['mean_offset']:+.3f} nm (spec ±{offset_spec}), Deming slope "
            f"{r['deming_slope']:.4f} (allowed 1 ± {slope_tol}) → not matched")
    else:
        if abs(r["mean_offset"]) > 0.5 * offset_spec:
            f.worse("watch")
        f.add(f"{r['tool']} 匹配：偏差 {r['mean_offset']:+.3f} nm 在 ±{offset_spec} 等價區間內（TOST），斜率 {r['deming_slope']:.4f}",
              f"{r['tool']} matched: offset {r['mean_offset']:+.3f} nm is inside the ±{offset_spec} equivalence margin (TOST), "
              f"slope {r['deming_slope']:.4f}")
    return f


# --------------------------------------------------------------------------- recipe studies
def study_sensitivity(r: pd.DataFrame, s: pd.DataFrame) -> Facts:
    """v: t_thin, prec_r_thin, prec_s_thin, ratio, t_ok (thinnest thickness where reflectometry < 0.05 nm)."""
    t0 = float(r["thickness_nm"].iloc[0])
    pr, ps = float(r["est_precision_nm"].iloc[0]), float(s["est_precision_nm"].iloc[0])
    ok = r.loc[r["est_precision_nm"] < 0.05, "thickness_nm"]
    f = Facts(v={"t_thin": t0, "prec_r_thin": pr, "prec_s_thin": ps, "ratio": pr / ps if ps > 0 else np.nan,
                 "t_ok": float(ok.iloc[0]) if len(ok) else np.nan})
    f.add(f"{t0:g} nm 時，反射儀精度 ≈ {pr:.3g} nm、SE ≈ {ps:.3g} nm（SE 好 {f.v['ratio']:.0f} 倍）",
          f"at {t0:g} nm: reflectometry ≈ {pr:.3g} nm, SE ≈ {ps:.3g} nm precision (SE {f.v['ratio']:.0f}× better)")
    if pr > 0.05:
        f.worse("watch").add(f"反射儀要到 ≥ {_f(f.v['t_ok'])} nm 才有 < 0.05 nm 精度 → 超薄膜（閘極氧化層、high-k）請用 SE",
                             f"reflectometry reaches < 0.05 nm only from {_f(f.v['t_ok'])} nm → use SE for ultra-thin films "
                             "(gate oxide, high-k)")
    return f


def study_tn(c: pd.DataFrame, limit: float = 0.01) -> Facts:
    """v: t_bad (largest thickness with σ(A) > limit), sA_thin, sA_thick, ratio, limit."""
    bad = c.loc[c["A_stderr"] > limit, "thickness_nm"]
    f = Facts(v={"t_bad": float(bad.max()) if len(bad) else np.nan, "sA_thin": float(c["A_stderr"].iloc[0]),
                 "sA_thick": float(c["A_stderr"].iloc[-1]), "limit": limit,
                 "ratio": float(c["A_stderr"].iloc[0] / c["A_stderr"].iloc[-1])})
    f.add(f"同時浮動 n 與厚度：{c['thickness_nm'].iloc[0]:g} nm 時 σ(A) = {f.v['sA_thin']:.3g}，"
          f"{c['thickness_nm'].iloc[-1]:g} nm 時 {f.v['sA_thick']:.3g}（差 {f.v['ratio']:.0f} 倍）",
          f"floating n with thickness: σ(A) = {f.v['sA_thin']:.3g} at {c['thickness_nm'].iloc[0]:g} nm vs "
          f"{f.v['sA_thick']:.3g} at {c['thickness_nm'].iloc[-1]:g} nm ({f.v['ratio']:.0f}× worse)")
    if len(bad):
        f.worse("watch").add(f"≤ {f.v['t_bad']:g} nm 時 σ(A) > {limit}：薄膜請固定 n（用厚膜或參考片量好的 n,k）",
                             f"σ(A) > {limit} up to {f.v['t_bad']:g} nm: fix n for thin films (use n,k measured on a thick "
                             "film or reference wafer)")
    return f


# --------------------------------------------------------------------------- DOE
def doe_pareto(fit, curv: dict | None) -> Facts:
    """v: response, sig_terms, n_sig, top_term, r2, r2_adj, r2_pred, gap, rmse, dof, curv_p."""
    t = fit.table[fit.table["term"] != "intercept"]
    sig = t[t["p"] < 0.05].assign(a=lambda d: d["t"].abs()).sort_values("a", ascending=False)
    gap = fit.r2_adj - fit.r2_pred if np.isfinite(fit.r2_pred) else np.nan
    f = Facts(v={"response": fit.response, "sig_terms": ", ".join(sig["term"]) or "—", "n_sig": len(sig),
                 "top_term": sig["term"].iloc[0] if len(sig) else "—", "r2": fit.r2, "r2_adj": fit.r2_adj,
                 "r2_pred": fit.r2_pred, "gap": gap, "rmse": fit.rmse, "dof": fit.dof,
                 "curv_p": curv["p"] if curv else np.nan})
    f.add(f"{fit.response}：顯著項（p < 0.05）{f.v['sig_terms']}；最重要 {f.v['top_term']}",
          f"{fit.response}: significant terms (p < 0.05) {f.v['sig_terms']}; strongest {f.v['top_term']}")
    if fit.dof <= 0 or not np.isfinite(fit.r2_pred) or fit.r2_pred < 0.5:
        f.worse("act").add(f"預測 R² = {_f(fit.r2_pred)}（< 0.5）：模型不能拿來預測新條件，不可用來決定配方",
                           f"predicted R² = {_f(fit.r2_pred)} (< 0.5): the model cannot predict new runs; do not set a recipe with it")
    elif np.isfinite(gap) and gap > 0.2:
        f.worse("watch").add(f"調整 R² 與預測 R² 差 {gap:.2f}：可能過度擬合，刪掉不顯著的項再看",
                             f"adjusted vs predicted R² differ by {gap:.2f}: possible over-fit; drop non-significant terms")
    else:
        f.add(f"R² = {fit.r2:.3f}、調整 R² = {fit.r2_adj:.3f}、預測 R² = {fit.r2_pred:.3f}：模型可用",
              f"R² = {fit.r2:.3f}, adjusted {fit.r2_adj:.3f}, predicted {fit.r2_pred:.3f}: the model is usable")
    if fit.curvature_unresolved and curv and curv["p"] < 0.05:
        f.worse("act").add(f"中心點顯示明顯彎曲（p = {curv['p']:.2g}），但這個設計無法估計 → 加軸點（擴成 CCD）",
                           f"centre points show significant curvature (p = {curv['p']:.2g}) that this design cannot model → "
                           "add axial points (augment to a CCD)")
    return f


def doe_contour(best: dict, recipe: dict, names: list[str], factors: dict) -> Facts:
    """v: D, recipe_txt, at_edge, pred_txt."""
    edge = [n for n, c in zip(names, best["coded"]) if abs(c) > 0.98]
    rtxt = ", ".join(f"{n} = {recipe[n]:.4g} {factors[n].get('unit', '')}".strip() for n in names)
    ptxt = ", ".join(f"{k} = {v:.4g}" for k, v in best["responses"].items())
    f = Facts(v={"D": best["D"], "recipe_txt": rtxt, "at_edge": ", ".join(edge) or "—", "pred_txt": ptxt})
    if best["D"] <= 0:
        f.worse("act").add("沒有任何配方能同時滿足所有目標（D = 0）→ 放寬目標或擴大實驗範圍",
                           "no recipe satisfies every goal (D = 0) → relax a goal or widen the experimental range")
    else:
        f.add(f"建議配方 {rtxt}；預測 {ptxt}；D = {best['D']:.2f}", f"suggested recipe {rtxt}; predicted {ptxt}; D = {best['D']:.2f}")
        if best["D"] < 0.6:
            f.worse("watch").add("D < 0.6：目標之間有明顯取捨", "D < 0.6: the goals clearly trade off")
    if edge:
        f.worse("watch").add(f"{', '.join(edge)} 落在實驗範圍邊界：真正最佳點可能在範圍外，下一輪往這個方向擴大",
                             f"{', '.join(edge)} sits on the edge of the tested range: the true optimum may lie outside; "
                             "extend the range that way next round")
    return f


def doe_confirm(rows: pd.DataFrame, fits: dict) -> Facts:
    """rows: 回應, 預測, 確認平均, 確認標準差, 可接受. v: n_bad, bad_resp, worst_resp, worst_dev, worst_rmse."""
    # noise-free responses (e.g. computed time) have RMSE ~ 0: judge them against 0.1 % of the value instead
    devs = {r["回應"]: (r["確認平均"] - r["預測"]) / max(fits[r["回應"]].rmse or 0.0, 1e-3 * abs(r["預測"]), 1e-12)
            for _, r in rows.iterrows()}
    worst = max(devs, key=lambda k: abs(devs[k]))
    bad = rows.loc[rows["可接受"] != "✓", "回應"].tolist()
    f = Facts(v={"n_bad": len(bad), "bad_resp": ", ".join(bad) or "—", "worst_resp": worst, "worst_dev": devs[worst],
                 "worst_rmse": fits[worst].rmse})
    if bad:
        f.worse("act").add(f"確認實驗中 {', '.join(bad)} 不可接受 → 不能發行此配方", f"{', '.join(bad)} not acceptable in the "
                           "confirmation runs → do not release this recipe")
    if abs(devs[worst]) > 2:
        f.worse("watch").add(f"{worst} 確認平均與預測差 {devs[worst]:+.1f} 倍模型 RMSE：模型在這一區不準",
                             f"{worst}: confirmation mean differs from the prediction by {devs[worst]:+.1f}× model RMSE: the "
                             "model is off in this region")
    if not bad and abs(devs[worst]) <= 2:
        f.add("所有回應的確認結果都在預測 ±2 RMSE 內且可接受 → 可進入 qual／發行流程",
              "every response confirms within ±2 RMSE of the prediction and is acceptable → proceed to qual / release")
    return f


# --------------------------------------------------------------------------- fab simulator
def fab_yield_trend(w: pd.DataFrame) -> Facts:
    """v: mean_yield, lot_sd, worst_lot, worst_yield, n_low, low_lots, change_pp."""
    lot = w.groupby(["lot_index", "lot_id"])["yield"].mean().reset_index().sort_values("lot_index")
    med = lot["yield"].median()
    mad = 1.4826 * (lot["yield"] - med).abs().median() or lot["yield"].std() or 1e-9
    low = lot[lot["yield"] < med - 3 * mad]
    n = max(len(lot) // 4, 1)
    change = 100 * (lot["yield"].tail(n).mean() - lot["yield"].head(n).mean())
    worst = lot.loc[lot["yield"].idxmin()]
    f = Facts(v={"mean_yield": 100 * w["yield"].mean(), "lot_sd": 100 * lot["yield"].std(), "worst_lot": worst["lot_id"],
                 "worst_yield": 100 * worst["yield"], "n_low": len(low), "low_lots": ", ".join(low["lot_id"]) or "—",
                 "change_pp": change})
    f.add(f"平均良率 {f.v['mean_yield']:.1f}%，批間標準差 {f.v['lot_sd']:.1f} 個百分點；最低 {worst['lot_id']}（{f.v['worst_yield']:.1f}%）",
          f"mean yield {f.v['mean_yield']:.1f}%, lot-to-lot sd {f.v['lot_sd']:.1f} pp; lowest {worst['lot_id']} ({f.v['worst_yield']:.1f}%)")
    if len(low):
        f.worse("act").add(f"{len(low)} 批低於中位數 − 3×穩健σ：{f.v['low_lots']} → 良率 excursion，做 commonality",
                           f"{len(low)} lot(s) below median − 3 robust σ: {f.v['low_lots']} → yield excursion, run commonality")
    if abs(change) > 2:
        f.worse("watch").add(f"最後 1/4 批與最前 1/4 批差 {change:+.1f} 個百分點：有趨勢", f"last quarter vs first quarter of lots: "
                             f"{change:+.1f} pp: a trend")
    return f


def fab_die_map(row: pd.Series, codes: np.ndarray, gx, gy, r_eff: float, w_all: pd.DataFrame,
                cause_label: dict, cause_step: dict) -> Facts:
    """v: wafer, yield, fleet_yield, main_cause, main_share, n_fail, edge_share, pattern, step, chamber."""
    fails = codes != "."
    n_fail = int(fails.sum())
    causes = pd.Series(codes[fails]).value_counts()
    main = causes.index[0] if len(causes) else "."
    edge = np.hypot(gx, gy) > 0.85 * r_eff
    step = cause_step.get(main, "—")
    chamber = row.get(f"{step}_chamber", "—") if step != "—" else "—"
    mu, sd = w_all["yield"].mean(), w_all["yield"].std()
    f = Facts(v={"wafer": row.name, "yield": 100 * row["yield"], "fleet_yield": 100 * mu, "main_cause": cause_label.get(main, main),
                 "main_share": 100 * causes.iloc[0] / n_fail if n_fail else 0.0, "n_fail": n_fail,
                 "edge_share": 100 * (fails & edge).sum() / n_fail if n_fail else 0.0,
                 "pattern": row.get("defect_pattern", "—"), "step": step, "chamber": chamber})
    if row["yield"] < mu - 2 * sd:
        f.worse("act")
    elif row["yield"] < mu - sd:
        f.worse("watch")
    f.add(f"{row.name} 良率 {f.v['yield']:.1f}%（全部平均 {f.v['fleet_yield']:.1f}%）；{n_fail} 顆失效，主因 {f.v['main_cause']}"
          f"（{f.v['main_share']:.0f}%，製程站 {step}，chamber {chamber}）",
          f"{row.name}: yield {f.v['yield']:.1f}% (fleet {f.v['fleet_yield']:.1f}%); {n_fail} failing dies, mainly {f.v['main_cause']} "
          f"({f.v['main_share']:.0f}%, step {step}, chamber {chamber})")
    f.add(f"{f.v['edge_share']:.0f}% 的失效在最外圈（r > 0.85R；面積約佔 28%）" + ("→ 邊緣型問題" if f.v["edge_share"] > 50 else ""),
          f"{f.v['edge_share']:.0f}% of failures sit in the outer ring (r > 0.85R, ~28% of the area)" +
          (" → an edge-type problem" if f.v["edge_share"] > 50 else ""))
    return f


def fab_patterns(ev: dict, true: np.ndarray, pred: np.ndarray, min_defects: int) -> Facts:
    """v: accuracy, n_pattern, recall_pattern, worst_class, worst_recall, false_calls, min_defects."""
    pc = ev["per_class"].dropna(subset=["recall"])
    pc = pc[pc["n"] > 0]
    worst = pc.sort_values("recall").iloc[0] if len(pc) else None
    nonrand = true != "random"
    false_calls = int(((true == "random") & (pred != "random")).sum())
    f = Facts(v={"accuracy": 100 * ev["accuracy"], "n_pattern": int(nonrand.sum()),
                 "recall_pattern": 100 * float((pred[nonrand] == true[nonrand]).mean()) if nonrand.any() else np.nan,
                 "worst_class": worst["pattern"] if worst is not None else "—",
                 "worst_recall": 100 * float(worst["recall"]) if worst is not None else np.nan,
                 "false_calls": false_calls, "min_defects": min_defects})
    acc = ev["accuracy"]
    f.worse("good" if acc >= 0.9 else "watch" if acc >= 0.75 else "act")
    f.add(f"正確率 {100 * acc:.1f}%；有圖樣晶圓 {f.v['n_pattern']} 片，召回 {_f(f.v['recall_pattern'])}%；最弱類別 {f.v['worst_class']}"
          f"（召回 {_f(f.v['worst_recall'])}%）",
          f"accuracy {100 * acc:.1f}%; {f.v['n_pattern']} patterned wafers, recall {_f(f.v['recall_pattern'])}%; weakest class "
          f"{f.v['worst_class']} (recall {_f(f.v['worst_recall'])}%)")
    f.add(f"{false_calls} 片其實是隨機缺陷卻被判成有圖樣（誤報，會浪費 FA 資源）",
          f"{false_calls} random wafers were called patterned (false calls waste FA capacity)")
    return f


def fab_defect_map(wid: str, true: str, pred: str, conf: float, n_fail: int) -> Facts:
    """v: wafer, true, pred, conf, n_fail, correct."""
    f = Facts(v={"wafer": wid, "true": true, "pred": pred, "conf": conf, "n_fail": n_fail,
                 "correct": _bi("正確" if pred == true else "錯誤", "correct" if pred == true else "wrong")})
    if pred != "random":
        f.worse("act" if conf >= 0.2 else "watch").add(
            f"判為 {pred}（信心 {conf:.2f}，{n_fail} 顆缺陷失效）：系統性空間圖樣 → 送 RDA／FA 並做機台 commonality",
            f"called {pred} (confidence {conf:.2f}, {n_fail} defect fails): a systematic spatial signature → send to RDA/FA "
            "and run tool commonality")
    else:
        f.add(f"判為 random（{n_fail} 顆缺陷失效）：沒有空間特徵，看整體缺陷密度趨勢即可",
              f"called random ({n_fail} defect fails): no spatial signature; follow the overall defect-density trend")
    f.add(f"答案是 {true} → 分類{f.v['correct']['zh']}", f"the answer is {true} → the call is {f.v['correct']['en']}")
    return f


def fab_tradeoff(summ: pd.DataFrame) -> Facts:
    """v: fastest, fastest_delay, quietest, quietest_fa, n_obs, best_all, best_all_fa."""
    obs = summ["observable"].max()
    full = summ[summ["detected"] == obs].sort_values("false_alarm_rate_pct")
    fast = summ.dropna(subset=["median_delay_wafers"]).sort_values(["median_delay_wafers", "false_alarm_rate_pct"])
    quiet = summ.sort_values("false_alarm_rate_pct").iloc[0]
    f = Facts(v={"fastest": fast["setup"].iloc[0] if len(fast) else "—",
                 "fastest_delay": float(fast["median_delay_wafers"].iloc[0]) if len(fast) else np.nan,
                 "quietest": quiet["setup"], "quietest_fa": float(quiet["false_alarm_rate_pct"]), "n_obs": int(obs),
                 "best_all": full["setup"].iloc[0] if len(full) else "—",
                 "best_all_fa": float(full["false_alarm_rate_pct"].iloc[0]) if len(full) else np.nan})
    if not len(full):
        f.worse("act").add("沒有任何設定抓到全部可觀測事件", "no setup catches every observable event")
    elif f.v["best_all_fa"] > 5:
        f.worse("watch").add(f"能抓到全部 {obs} 個事件的設定中，最安靜的是 {f.v['best_all']}，誤警報仍有 {f.v['best_all_fa']:.1f}%",
                             f"among setups that catch all {obs} events, the quietest is {f.v['best_all']} with "
                             f"{f.v['best_all_fa']:.1f}% false alarms")
    else:
        f.add(f"{f.v['best_all']} 抓到全部 {obs} 個事件，誤警報 {f.v['best_all_fa']:.1f}%", f"{f.v['best_all']} catches all {obs} "
              f"events with {f.v['best_all_fa']:.1f}% false alarms")
    f.add(f"最快 {f.v['fastest']}（中位延遲 {_f(f.v['fastest_delay'])} 片）；最安靜 {f.v['quietest']}（誤警報 {f.v['quietest_fa']:.1f}%）",
          f"fastest {f.v['fastest']} (median delay {_f(f.v['fastest_delay'])} wafers); quietest {f.v['quietest']} "
          f"({f.v['quietest_fa']:.1f}% false alarms)")
    return f


def fab_event_delay(delays: pd.DataFrame) -> Facts:
    """v: slowest_event, slowest_best, missed, unobservable."""
    d = delays.copy()
    d["event"] = d["id"] + " " + d["type"]
    best = d.groupby("event")["delay_wafers"].min()
    missed = [e for e, g in d.groupby("event") if (g["status"] == "missed").all()]
    unobs = [e for e, g in d.groupby("event") if g["status"].str.startswith("not observable").all()]
    caught = best.dropna()
    slow = caught.idxmax() if len(caught) else "—"
    f = Facts(v={"slowest_event": slow, "slowest_best": float(caught.max()) if len(caught) else np.nan,
                 "missed": ", ".join(missed) or "—", "unobservable": ", ".join(unobs) or "—"})
    if missed:
        f.worse("act").add(f"{', '.join(missed)} 所有設定都沒抓到", f"{', '.join(missed)} missed by every setup")
    if len(caught) and caught.max() > 10:
        f.worse("watch").add(f"{slow} 最快也要 {caught.max():.0f} 片量測晶圓才被抓到（> 10）→ 這段期間的產品都受影響",
                             f"{slow} needs at least {caught.max():.0f} measured wafers to be caught (> 10) → product in "
                             "between is exposed")
    if unobs:
        f.add(f"{', '.join(unobs)} 沒有被量測到（抽樣盲點）", f"{', '.join(unobs)} never measured (sampling blind spot)")
    if not missed and not (len(caught) and caught.max() > 10):
        f.add("每個事件都在 10 片量測晶圓內被至少一種設定抓到", "every event is caught within 10 measured wafers by at least one setup")
    return f


def fab_drivers(drv: pd.DataFrame, corr_rank: list[str] | None, cmp: dict | None) -> Facts:
    """v: top_cause, top_loss, total_loss, corr_top, top1_match, spearman."""
    top = drv.iloc[0]
    f = Facts(v={"top_cause": top["cause"], "top_loss": float(top["yield_loss_pct"]),
                 "total_loss": float(drv["yield_loss_pct"].sum()), "corr_top": corr_rank[0] if corr_rank else "—",
                 "top1_match": _bi("相同" if cmp and cmp["top1_match"] else "不同", "same" if cmp and cmp["top1_match"] else "different"),
                 "spearman": cmp["spearman"] if cmp and cmp["spearman"] is not None else np.nan})
    f.add(f"最大良率損失來源 {top['cause']}：平均 {top['yield_loss_pct']:.2f} 個百分點（全部 {f.v['total_loss']:.2f}）",
          f"largest yield-loss source {top['cause']}: {top['yield_loss_pct']:.2f} pp on average (all causes {f.v['total_loss']:.2f})")
    if top["yield_loss_pct"] > 5:
        f.worse("act")
    if cmp and not cmp["top1_match"]:
        f.worse("watch").add(f"簡單相關性排名第一的是 {f.v['corr_top']}，和真正原因不同 → 相關不等於因果，要用 DOE／分批驗證",
                             f"simple correlation ranks {f.v['corr_top']} first, not the true cause → correlation is not "
                             "causation; confirm with a split lot / DOE")
    return f


# --------------------------------------------------------------------------- inline defect inspection / cross-role requests
def defect_counts(counts: pd.DataFrame, maxout: int) -> Facts:
    """counts: wafer_id, count (and optional group). v: n_wafers, n_maxout, maxout, max_count, top_wafer, median_count."""
    top = counts.loc[counts["count"].idxmax()]
    hit = counts[counts["count"] >= maxout]
    f = Facts(v={"n_wafers": len(counts), "n_maxout": len(hit), "maxout": int(maxout), "max_count": int(top["count"]),
                 "top_wafer": top["wafer_id"], "median_count": int(counts["count"].median())})
    f.add(f"{len(counts)} 片檢查，中位數 {f.v['median_count']:,} 顆，最多 {top['wafer_id']}（{f.v['max_count']:,} 顆）",
          f"{len(counts)} wafers inspected, median {f.v['median_count']:,} defects, highest {top['wafer_id']} "
          f"({f.v['max_count']:,})")
    if len(hit):
        f.worse("act").add(f"{len(hit)} 片達到檢查機台上限 {maxout:,}（maxout）：實際數量未知，這些片的數字不能直接比較",
                           f"{len(hit)} wafer(s) hit the inspection maxout of {maxout:,}: the true count is unknown and "
                           "these numbers cannot be compared directly")
    elif f.v["max_count"] > 3 * max(f.v["median_count"], 1):
        f.worse("watch").add("有晶圓的數量超過中位數 3 倍：先看該片的 wafer map 與 review 再下結論",
                             "one wafer is above 3× the median: look at its map and review before concluding")
    return f


def review_pareto(classes: pd.Series, nuisance: str = "Non-visible") -> Facts:
    """classes: review counts per defect class (index = class). v: n_reviewed, top_class, top_share, nonvisible_share,
    real_share, n_classes."""
    s = classes.sort_values(ascending=False)
    n = int(s.sum())
    nv = 100 * float(s.get(nuisance, 0)) / max(n, 1)
    f = Facts(v={"n_reviewed": n, "top_class": s.index[0], "top_share": round(100 * float(s.iloc[0]) / max(n, 1)),
                 "nonvisible_share": round(nv), "real_share": round(100 - nv), "n_classes": int((s > 0).sum())})
    f.add(f"review {n} 顆，最多是 {s.index[0]}（{f.v['top_share']:.0f}%）；non-visible（看不到真缺陷）佔 {nv:.0f}%",
          f"{n} defects reviewed; top class {s.index[0]} ({f.v['top_share']:.0f}%); non-visible (no real defect seen) "
          f"{nv:.0f}%")
    if nv >= 50:
        f.worse("act").add("一半以上是 nuisance：檢查數量主要是雜訊，不能代表真缺陷，要先調整檢查 recipe",
                           "more than half is nuisance: the counts are mostly noise, not real defects; tune the "
                           "inspection recipe first")
    elif nv >= 25:
        f.worse("watch").add("nuisance 比例偏高：比較數量前先用 review 換算真缺陷數",
                             "a high nuisance share: convert counts to real defects with the review before comparing")
    return f


def adder_compare(t: pd.DataFrame) -> Facts:
    """t: wafer_id, group (split / baseline), previous, current. v: n_split, n_base, split_prev, base_prev,
    split_adders, base_adders, prev_ratio, adder_ratio, source."""
    t = t.assign(adders=(t["current"] - t["previous"]).clip(lower=0))
    g = t.groupby("group")[["previous", "adders"]].mean()
    sp, bp = float(g.loc["split", "previous"]), float(g.loc["baseline", "previous"])
    sa, ba = float(g.loc["split", "adders"]), float(g.loc["baseline", "adders"])
    pr, ar = sp / max(bp, 1.0), sa / max(ba, 1.0)
    src = ({"zh": "本層（split 條件本身）", "en": "this layer (the split condition itself)"} if ar >= 1.5 else
           {"zh": "前層帶進來（incoming）", "en": "the previous layer (incoming)"} if pr >= 1.5 else
           {"zh": "看不出差異", "en": "no clear difference"})
    f = Facts(v={"n_split": int((t["group"] == "split").sum()), "n_base": int((t["group"] == "baseline").sum()),
                 "split_prev": round(sp), "base_prev": round(bp), "split_adders": round(sa), "base_adders": round(ba),
                 "prev_ratio": round(pr, 1), "adder_ratio": round(ar, 1), "source": src})
    f.add(f"前層數量 split／baseline = {pr:.1f} 倍；本層 adder（本層 − 前層）split／baseline = {ar:.1f} 倍",
          f"previous-layer counts split / baseline = {pr:.1f}×; this-layer adders (current − previous) split / "
          f"baseline = {ar:.1f}×")
    if ar >= 1.5 or pr >= 1.5:
        f.worse("act").add(f"差異來源：{src['zh']}", f"the difference comes from {src['en']}")
    return f


def bin_corr(t: pd.DataFrame, params: list[str], bin_name: str) -> Facts:
    """t: wafer_id, bin_loss (%), one column per inline parameter. v: bin, n_wafers, best_param, best_r, second_param,
    second_r, worst_wafer, worst_loss."""
    r = {p: float(np.corrcoef(t[p], t["bin_loss"])[0, 1]) for p in params}
    order = sorted(r, key=lambda p: -abs(r[p]))
    worst = t.loc[t["bin_loss"].idxmax()]
    f = Facts(v={"bin": bin_name, "n_wafers": len(t), "best_param": order[0], "best_r": round(r[order[0]], 2),
                 "second_param": order[1] if len(order) > 1 else "—",
                 "second_r": round(r[order[1]], 2) if len(order) > 1 else None,
                 "worst_wafer": worst["wafer_id"], "worst_loss": round(float(worst["bin_loss"]), 1)})
    f.add(f"{bin_name} 損失與 {order[0]} 的相關係數 r = {r[order[0]]:+.2f}（{len(t)} 片）；最差 {worst['wafer_id']}"
          f"（{f.v['worst_loss']:.1f}%）",
          f"{bin_name} loss vs {order[0]}: r = {r[order[0]]:+.2f} ({len(t)} wafers); worst {worst['wafer_id']} "
          f"({f.v['worst_loss']:.1f}%)")
    if abs(r[order[0]]) >= 0.7:
        f.worse("act").add(f"{order[0]} 與 bin 損失強相關：很可能是驅動因子，要和 PE／YE 確認機制",
                           f"{order[0]} correlates strongly with the bin loss: a likely driver; confirm the mechanism "
                           "with PE / YE")
    elif abs(r[order[0]]) >= 0.4:
        f.worse("watch").add("只有中度相關：可能是部分原因或巧合，要加更多晶圓確認",
                             "only a moderate correlation: a partial cause or chance; add more wafers to confirm")
    return f


# --------------------------------------------------------------------------- yield analysis, splits and weekly KPIs
ZONE = {"centre": ("中心", "centre"), "mid": ("中間", "middle"), "edge": ("邊緣", "edge")}


def zone_of(r, r_max: float) -> np.ndarray:
    """centre (r < 0.5 R) | mid | edge (r > 0.8 R): the radial zones yield is usually split into."""
    r = np.asarray(r, float) / r_max
    return np.where(r < 0.5, "centre", np.where(r > 0.8, "edge", "mid"))


def probe_overlay(dies: pd.DataFrame, bin_name: str, r_max: float) -> Facts:
    """dies: x, y, fail (bool). v: bin, n_dies, n_fail, fail_pct, fail_zone, zone_pct."""
    fail = dies[dies["fail"]]
    zones = pd.Series(zone_of(np.hypot(fail.x, fail.y), r_max)).value_counts()
    share = zones / pd.Series(zone_of(np.hypot(dies.x, dies.y), r_max)).value_counts()  # fail rate per zone
    z = str(share.idxmax())
    f = Facts(v={"bin": bin_name, "n_dies": len(dies), "n_fail": len(fail), "fail_pct": round(100 * len(fail) / len(dies), 1),
                 "fail_zone": _bi(ZONE[z][0], ZONE[z][1]), "zone_pct": round(100 * float(zones.get(z, 0)) / max(len(fail), 1))})
    f.add(f"{bin_name} 失效 {len(fail)} 顆（{f.v['fail_pct']}%），失效率最高的是{ZONE[z][0]}區（佔失效 {f.v['zone_pct']}%）",
          f"{bin_name}: {len(fail)} failing dies ({f.v['fail_pct']}%); the highest fail rate is in the {ZONE[z][1]} zone "
          f"({f.v['zone_pct']}% of the fails)")
    if f.v["fail_pct"] >= 5:
        f.worse("act").add("失效率 ≥ 5%：要找出 inline 哪一站看得到這些失效", "fail rate of 5% or more: find which inline step sees these fails")
    elif f.v["fail_pct"] >= 2:
        f.worse("watch").add("失效率 2–5%：疊圖確認是否和 inline 缺陷有關", "fail rate 2–5%: overlay to check whether inline defects explain it")
    return f


def capture_kill(table: pd.DataFrame, monitor: str, area_cm2: float, n_dies: int) -> Facts:
    """table: step, defects, capture (% of fail dies with a defect of this step), kill_ratio (% adjusted for chance),
    chance (% of dies failing: a random defect lands on a fail die this often). Yield gain from the best-capturing step:
    Y = exp(-D * A * KR) with D = defects / (n_dies * A).
    v: monitor, mon_capture, mon_kr, best_step, best_capture, best_kr, chance, d_best, area, kr_best, gain."""
    t = table.set_index("step")
    best = str(t["capture"].idxmax())
    d = float(t.loc[best, "defects"]) / (n_dies * area_cm2)
    kr = float(t.loc[best, "kill_ratio"]) / 100
    gain = 100 * (1 - np.exp(-d * area_cm2 * kr))
    f = Facts(v={"monitor": monitor, "mon_capture": round(float(t.loc[monitor, "capture"])), "mon_kr": round(float(t.loc[monitor, "kill_ratio"])),
                 "best_step": best, "best_capture": round(float(t.loc[best, "capture"])), "best_kr": round(float(t.loc[best, "kill_ratio"])),
                 "chance": round(float(t["chance"].iloc[0]), 1), "d_best": round(d, 3), "area": area_cm2, "kr_best": round(kr, 2),
                 "gain": round(gain, 1)})
    for s, r in t.iterrows():
        f.add(f"{s}：capture rate {r['capture']:.0f}%、kill ratio {r['kill_ratio']:.0f}%（{int(r['defects'])} 顆）",
              f"{s}: capture rate {r['capture']:.0f}%, kill ratio {r['kill_ratio']:.0f}% ({int(r['defects'])} defects)")
    f.add(f"以 {best} 估計：Y = exp(−D·A·KR)，D = {d:.3f}/cm²、A = {area_cm2} cm²、KR = {kr:.2f} → 去除這些缺陷約回收 {gain:.1f} 個百分點",
          f"from {best}: Y = exp(−D·A·KR), D = {d:.3f}/cm², A = {area_cm2} cm², KR = {kr:.2f} → removing these defects returns "
          f"about {gain:.1f} percentage points")
    if f.v["mon_capture"] < 30:
        f.worse("act").add(f"目前的監控站 {monitor} capture rate < 30%：它看不到這些 killer，SPC 正常不代表沒問題",
                           f"the current monitor {monitor} has a capture rate below 30%: it cannot see these killers, so a clean "
                           "SPC proves nothing")
    elif f.v["mon_capture"] < 60:
        f.worse("watch").add("監控站 capture rate 30–60%：只看得到部分 killer", "monitor capture rate 30–60%: it sees only part of the killers")
    return f


def split_check(t: pd.DataFrame) -> Facts:
    """t: wafer_id, slot, planned (POR / B-low / B-high), actual (recipe in the run log), fem (nominal / off), yield.
    v: n_wafers, n_misrun, misrun_group, n_fem_off, fem_b, fem_por, delta_all, delta_nom, d_setting, source."""
    b_plan = t["planned"] != "POR"
    mis = t[t["planned"] != t["actual"]]
    off = t["fem"] != "nominal"
    nom = t[~off]
    delta_all = float(t.loc[b_plan, "yield"].mean() - t.loc[~b_plan, "yield"].mean())
    delta_nom = float(nom.loc[nom["actual"] != "POR", "yield"].mean() - nom.loc[nom["actual"] == "POR", "yield"].mean())
    d_set = float(t.loc[t["planned"] == "B-high", "yield"].mean() - t.loc[t["planned"] == "B-low", "yield"].mean())
    fem_b, fem_por = int((off & b_plan).sum()), int((off & ~b_plan).sum())
    confounded = abs(fem_b - fem_por) >= 3 and abs(delta_all - delta_nom) >= 1.2
    src = ({"zh": "split 設定錯誤（run log 與計畫不符）", "en": "the split was set up wrong (the run log does not match the plan)"} if len(mis) else
           {"zh": "第二個實驗（litho FEM）和 split 分組重疊（混淆）", "en": "a second experiment (litho FEM) overlaps the split groups (confounded)"}
           if confounded else {"zh": "實驗乾淨，結果可用", "en": "a clean experiment, the result can be used"})
    f = Facts(v={"n_wafers": len(t), "n_misrun": len(mis), "misrun_group": str(mis["planned"].iloc[0]) if len(mis) else "—",
                 "n_fem_off": int(off.sum()), "fem_b": fem_b, "fem_por": fem_por, "delta_all": round(delta_all, 1),
                 "delta_nom": round(delta_nom, 1), "d_setting": round(d_set, 1), "source": src})
    f.add(f"依計畫分組：B − POR = {delta_all:+.1f} pp；只看 FEM 標準條件、依實際 recipe：{delta_nom:+.1f} pp",
          f"by planned group: B − POR = {delta_all:+.1f} pp; nominal-FEM wafers only, by actual recipe: {delta_nom:+.1f} pp")
    if len(mis):
        f.worse("act").add(f"{len(mis)} 片計畫是 {f.v['misrun_group']}，run log 卻是別的 recipe：這組條件實際上沒有跑",
                           f"{len(mis)} wafers planned as {f.v['misrun_group']} ran another recipe per the run log: that condition "
                           "never actually ran")
    if confounded:
        f.worse("act").add(f"FEM 偏離條件的晶圓 B 組 {fem_b} 片、POR 組 {fem_por} 片：差異被第二個實驗混淆",
                           f"off-nominal FEM wafers: {fem_b} in B, {fem_por} in POR: the difference is confounded by the second experiment")
    return f


def zone_split(t: pd.DataFrame, net: float, net_se: float) -> Facts:
    """t: zone (centre / mid / edge), share (% of dies), por, b (mean yield %), delta, se (of the delta).
    v: d_c, d_m, d_e, se_e, share_c, share_m, share_e, net, net_se, worst_zone, best_zone."""
    t = t.set_index("zone")
    worst, best = str(t["delta"].idxmin()), str(t["delta"].idxmax())
    f = Facts(v={"d_c": round(float(t.loc["centre", "delta"]), 1), "d_m": round(float(t.loc["mid", "delta"]), 1),
                 "d_e": round(float(t.loc["edge", "delta"]), 1), "se_e": round(float(t.loc["edge", "se"]), 2),
                 "share_c": round(float(t.loc["centre", "share"])), "share_m": round(float(t.loc["mid", "share"])),
                 "share_e": round(float(t.loc["edge", "share"])), "net": round(net, 2), "net_se": round(net_se, 2),
                 "worst_zone": _bi(ZONE[worst][0], ZONE[worst][1]), "best_zone": _bi(ZONE[best][0], ZONE[best][1])})
    f.add(f"B − POR：中心 {f.v['d_c']:+} pp、中間 {f.v['d_m']:+} pp、邊緣 {f.v['d_e']:+} pp；依晶粒數加權淨效果 {net:+.2f} ± {net_se:.2f} pp",
          f"B − POR: centre {f.v['d_c']:+} pp, middle {f.v['d_m']:+} pp, edge {f.v['d_e']:+} pp; die-weighted net {net:+.2f} ± {net_se:.2f} pp")
    loses = float(t.loc[worst, "delta"]) < -2 * float(t.loc[worst, "se"])
    if net <= 2 * net_se:
        f.worse("act").add("淨效果沒有超過 2 個標準誤：某區的增益被另一區的損失抵消，看不出整體好處",
                           "the net effect is not beyond 2 standard errors: one zone's gain is cancelled by another's loss")
    elif loses:
        f.worse("watch").add(f"整體有增益，但{ZONE[worst][0]}區顯著變差：轉換時要追蹤這一區",
                             f"a net gain, but the {ZONE[worst][1]} zone is significantly worse: follow that zone up when converting")
    return f


def dly_trend(w: pd.DataFrame, goal: float, fix_week: str | None) -> Facts:
    """w (one row per week, time order): week, dly (% all wafers), dly_ex (% without flagged wafers), random_loss,
    sys_loss (pp), density (inline killer defects / cm² of lots PROCESSED that week).
    v: latest, dly_latest, dly_ex_latest, goal, n_red, red_weeks, rand_latest, sys_latest, rand_base, sys_base,
    dens_latest, dens_base, dens_peak, dens_peak_week, fix_week."""
    last = w.iloc[-1]
    base = w.iloc[:4]
    red = w[w["dly"] < goal]
    peak = w.loc[w["density"].idxmax()]
    f = Facts(v={"latest": last["week"], "dly_latest": round(float(last["dly"]), 1), "dly_ex_latest": round(float(last["dly_ex"]), 1),
                 "goal": goal, "n_red": len(red), "red_weeks": ", ".join(red["week"]) or "—",
                 "rand_latest": round(float(last["random_loss"]), 1), "sys_latest": round(float(last["sys_loss"]), 1),
                 "rand_base": round(float(base["random_loss"].mean()), 1), "sys_base": round(float(base["sys_loss"].mean()), 1),
                 "dens_latest": round(float(last["density"]), 3), "dens_base": round(float(base["density"].mean()), 3),
                 "dens_peak": round(float(peak["density"]), 3), "dens_peak_week": peak["week"], "fix_week": fix_week or "—"})
    f.add(f"{last['week']} DLY {f.v['dly_latest']}%（目標 {goal}%）；隨機缺陷損失 {f.v['rand_latest']} pp（基準 {f.v['rand_base']}）、"
          f"系統性損失 {f.v['sys_latest']} pp（基準 {f.v['sys_base']}）",
          f"{last['week']} DLY {f.v['dly_latest']}% (goal {goal}%); random-defect loss {f.v['rand_latest']} pp (baseline "
          f"{f.v['rand_base']}), systematic loss {f.v['sys_latest']} pp (baseline {f.v['sys_base']})")
    if abs(f.v["dly_ex_latest"] - f.v["dly_latest"]) >= 0.5:
        f.add(f"不含標記晶圓時 {f.v['dly_ex_latest']}%：差距來自少數晶圓", f"without the flagged wafers {f.v['dly_ex_latest']}%: a few wafers make the gap")
    if f.v["dens_peak"] > 1.8 * f.v["dens_base"]:
        f.add(f"inline killer 密度在製程週 {peak['week']} 達 {f.v['dens_peak']}/cm²（基準 {f.v['dens_base']}），最近 {f.v['dens_latest']}",
              f"inline killer density peaked at {f.v['dens_peak']}/cm² in process week {peak['week']} (baseline {f.v['dens_base']}); "
              f"latest {f.v['dens_latest']}")
    if last["dly"] < goal:
        f.worse("act").add(f"{last['week']} 低於目標（紅燈）；紅燈週：{f.v['red_weeks']}", f"{last['week']} is below goal (red); red weeks: {f.v['red_weeks']}")
    elif last["dly"] < goal + 0.5:
        f.worse("watch").add("離目標不到 0.5 pp", "within 0.5 pp of the goal")
    return f


def level_pass(lv: pd.DataFrame) -> Facts:
    """lv: week, level, mode (opens / shorts), pass_pct. Baseline = the first four weeks.
    v: worst_level, worst_mode, worst_drop, worst_latest, worst_base."""
    weeks = list(dict.fromkeys(lv["week"]))
    base = lv[lv["week"].isin(weeks[:4])].groupby(["level", "mode"])["pass_pct"].mean()
    last = lv[lv["week"] == weeks[-1]].set_index(["level", "mode"])["pass_pct"]
    drop = (base - last).sort_values(ascending=False)
    (lev, mode), d = drop.index[0], float(drop.iloc[0])
    f = Facts(v={"worst_level": lev, "worst_mode": mode, "worst_drop": round(d, 2), "worst_latest": round(float(last[(lev, mode)]), 2),
                 "worst_base": round(float(base[(lev, mode)]), 2)})
    f.add(f"下降最多：{lev} {mode} 通過率 {f.v['worst_base']}% → {f.v['worst_latest']}%（−{d:.2f} pp）",
          f"largest drop: {lev} {mode} passing {f.v['worst_base']}% → {f.v['worst_latest']}% (−{d:.2f} pp)")
    if d >= 1.0:
        f.worse("act").add(f"{lev} 的 {mode} 持續下降 ≥ 1 pp：系統性問題，要找該層 module", f"{lev} {mode} down by 1 pp or more: a systematic problem on that level's module")
    elif d >= 0.5:
        f.worse("watch").add("下降 0.5–1 pp：再追一週", "down 0.5–1 pp: watch one more week")
    return f


def layer_repeat(d1: pd.DataFrame, d2: pd.DataFrame, radius: float, cluster_loc: dict) -> Facts:
    """d1 / d2: x, y of defects at this layer / the next layer's inspection; d1 also has 'cluster' (bool).
    v: n1, n2, cluster_n, n_repeat, repeat_pct, radius, cluster_loc."""
    c = d1[d1["cluster"]]
    if len(d2) and len(c):
        dist = np.hypot(c.x.to_numpy()[:, None] - d2.x.to_numpy()[None, :], c.y.to_numpy()[:, None] - d2.y.to_numpy()[None, :])
        hit = int((dist.min(axis=1) <= radius).sum())
    else:
        hit = 0
    pct = round(100 * hit / max(len(c), 1))
    f = Facts(v={"n1": len(d1), "n2": len(d2), "cluster_n": len(c), "n_repeat": hit, "repeat_pct": pct, "radius": radius,
                 "cluster_loc": cluster_loc})
    f.add(f"本層 {len(d1)} 顆（cluster {len(c)} 顆，在{cluster_loc['zh']}）；其中 {hit} 顆（{pct}%）在下一層同位置（±{radius} mm）再出現",
          f"{len(d1)} defects at this layer ({len(c)} in the cluster at the {cluster_loc['en']}); {hit} of them ({pct}%) reappear at "
          f"the same place (±{radius} mm) at the next layer")
    if pct >= 50:
        f.worse("act").add("一半以上在下一層再出現：是真的實體缺陷（可能在表面下），SEM 俯視看不到不代表沒有",
                           "more than half reappear at the next layer: a real physical defect (possibly below the surface); "
                           "SEM top-down not seeing it does not mean it is not there")
    elif pct >= 15:
        f.worse("watch").add("部分再出現：再看一層或換 review 方式確認", "partly repeating: check one more layer or another review mode")
    return f
