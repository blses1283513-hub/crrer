"""Plotly chart builders shared by the dashboard pages and the Case study page.

Every visual element gets a legend entry (shapes such as limit lines get a legend-only trace) and a hover text;
colours follow viz (fixed categorical slots, single-hue sequential, blue–red diverging, reserved status colours).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import t as t_dist

from metro_toolkit import viz
from metro_toolkit.wafer import interpolate_map

CAUSE_COLOR = {".": viz.GRID, **{c: viz.SERIES[i] for i, c in enumerate("DGKTCI")}}  # fixed: colour follows the cause
CAUSE_NAME = {".": "pass 良品", "D": "defect 缺陷", "G": "gate_ox_thk 閘極氧化層超窗", "K": "hk_thk high-k 厚度超窗",
              "T": "tin_thk TiN 厚度超窗", "C": "wl_cd_etch 字元線蝕刻 CD 超窗", "I": "ild_thk ILD 厚度超窗"}


def unit_of(param: str, df: pd.DataFrame | None = None) -> str:
    """Unit of a measured parameter: from the data's own unit column, else the fab-simulator step of that name,
    else a guess from the name (…_nm, …_pct)."""
    if df is not None and "unit" in df.columns:
        col = df.loc[df["parameter"] == param, "unit"] if "parameter" in df.columns else df["unit"]
        col = col.dropna()
        if len(col) and str(col.iloc[0]).strip():
            return str(col.iloc[0])
    try:
        from metro_toolkit.datagen.fab import load_fab_config

        for step in load_fab_config()["steps"]:
            if step["parameter"] == param:
                return step["unit"]
    except Exception:  # noqa: BLE001 - a missing config must never break a chart
        pass
    if param == "defect_density":
        return "1/cm²"
    if param.endswith("_nm") or param.endswith("_thk") or param.startswith("wl_cd"):
        return "nm"
    return {"pct": "%", "mv": "mV"}.get(param.rsplit("_", 1)[-1], "")


def quantity(w: pd.DataFrame) -> tuple[str, str]:
    """(parameter, unit) of a site-level wafer table."""
    param = str(w["parameter"].iloc[0]) if "parameter" in w.columns and len(w) else ""
    return param, unit_of(param, w) if param else ""


def with_unit(name: str, unit: str) -> str:
    return f"{name} ({unit})" if unit else name


def legend_line(fig: go.Figure, name: str, color: str, dash: str = "solid", width: float = 1.5) -> None:
    """Legend entry for a reference line drawn as a shape (shapes have no legend of their own)."""
    fig.add_scatter(x=[None], y=[None], mode="lines", name=name, line=dict(color=color, dash=dash, width=width),
                    hoverinfo="skip")


def legend_marker(fig: go.Figure, name: str, color: str, symbol: str = "square", size: int = 10, line=None) -> None:
    fig.add_scatter(x=[None], y=[None], mode="markers", name=name, hoverinfo="skip",
                    marker=dict(symbol=symbol, size=size, color=color, line=line or dict(width=0)))


def layout(fig: go.Figure, title: str, xlab: str, ylab: str, height: int = 380) -> go.Figure:
    fig.update_layout(**viz.PLOTLY_LAYOUT, title=dict(text=title, x=0, y=0.97, yanchor="top", yref="container",
                                                      font=dict(size=14)), height=height)
    fig.update_xaxes(title_text=xlab)  # text only: title=... would also reset the black axis-name font from viz
    fig.update_yaxes(title_text=ylab)
    return fig


# --------------------------------------------------------------------------- film stack
def fit_figures(technique: str, wl, meas, fitted_stack, angles=None) -> list[go.Figure]:
    """Reflectance (one figure) or Ψ and Δ at the middle angle (two figures): measured vs model fit."""
    from metro_toolkit.metrology.thinfilm import ellipsometry, reflectance

    if technique == "reflectometry":
        fig = go.Figure()
        fig.add_scatter(x=wl, y=meas.data["R"], mode="markers", name="measured 量測", marker=dict(size=4, color=viz.SERIES[0]),
                        hovertemplate="measured 量測<br>λ %{x:.0f} nm<br>R = %{y:.4f}<extra></extra>")
        fig.add_scatter(x=wl, y=reflectance(fitted_stack, wl), mode="lines", name="model fit 模型擬合",
                        line=dict(color=viz.SERIES[1], width=2),
                        hovertemplate="model fit 模型擬合<br>λ %{x:.0f} nm<br>R = %{y:.4f}<extra></extra>")
        return [layout(fig, "Reflectance: measured vs fitted model", "波長 wavelength (nm)", "反射率 reflectance R (0–1)")]
    a = float(angles[len(angles) // 2])
    psi_m, delta_m = meas.data[a]
    psi_f, delta_f = ellipsometry(fitted_stack, wl, a)
    figs = []
    for ym, yf, lab in ((psi_m, psi_f, "Ψ"), (delta_m, delta_f, "Δ")):
        fig = go.Figure([
            go.Scatter(x=wl, y=ym, mode="markers", name="measured 量測", marker=dict(size=4, color=viz.SERIES[0]),
                       hovertemplate=f"measured 量測<br>λ %{{x:.0f}} nm<br>{lab} = %{{y:.3f}}°<extra></extra>"),
            go.Scatter(x=wl, y=yf, mode="lines", name="model fit 模型擬合", line=dict(color=viz.SERIES[1]),
                       hovertemplate=f"model fit 模型擬合<br>λ %{{x:.0f}} nm<br>{lab} = %{{y:.3f}}°<extra></extra>")])
        figs.append(layout(fig, f"{lab} at {a:.0f}°", "波長 wavelength (nm)", f"{lab} 橢偏角 (deg)"))
    return figs


# --------------------------------------------------------------------------- wafer map
def wafer_map_figure(w: pd.DataFrame, um: dict, mode: str, title: str) -> go.Figure:
    r_eff = float(np.hypot(w.x, w.y).max())
    X, Y, Z = interpolate_map(w.x, w.y, w.value, radius_mm=r_eff, grid=101)
    if mode.startswith("absolute"):
        zz, cs, zmid = Z, viz.PLOTLY_SEQ, None
    else:
        zz, cs, zmid = Z - um["mean"], viz.PLOTLY_DIV, 0.0
    fig = go.Figure(go.Contour(x=X[0], y=Y[:, 0], z=zz, colorscale=cs, zmid=zmid, ncontours=16,
                               contours=dict(showlines=False), colorbar=dict(title=w.unit.iloc[0] if "unit" in w else "")))
    fig.add_scatter(x=w.x, y=w.y, mode="markers", marker=dict(size=7, color=viz.SURFACE, line=dict(color=viz.INK_2, width=1)),
                    text=[f"site {s}: {v:.3f}" for s, v in zip(w.get("site", range(len(w))), w.value)], hoverinfo="text",
                    name="sites 量測點")
    fig.add_shape(type="circle", x0=-r_eff, y0=-r_eff, x1=r_eff, y1=r_eff, line=dict(color=viz.AXIS))
    legend_line(fig, "wafer edge 晶圓邊緣", viz.AXIS)
    fig = layout(fig, title, "x (mm)", "y (mm)", 520)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def zernike_figure(zk: dict, param: str = "", unit: str = "") -> go.Figure:
    coef = {kk: v for kk, v in zk["coefficients"].items() if kk != "piston"}
    fig = go.Figure(go.Bar(x=list(coef.values()), y=list(coef), orientation="h", marker_color=viz.SERIES[0],
                           name="Zernike coefficient 係數",
                           hovertemplate="%{y}: %{x:+.4g}<extra>Zernike coefficient 係數</extra>"))
    fig.update_yaxes(autorange="reversed")
    xlab = with_unit(f"{param} Zernike 係數 coefficient" if param else "Zernike 係數 coefficient", unit)
    return layout(fig, f"Spatial signature (R² {zk['r2']:.2f})", xlab, "空間項 Zernike term", 260)


def radial_figure(rp: pd.DataFrame, param: str = "", unit: str = "") -> go.Figure:
    fig = go.Figure(go.Scatter(x=rp.r_mm, y=rp["mean"], mode="lines+markers", line=dict(color=viz.SERIES[0]),
                               name="ring mean ±1σ 環平均 ±1σ", error_y=dict(array=rp["std"].fillna(0), color=viz.MUTED),
                               hovertemplate="r ≈ %{x:.0f} mm<br>ring mean 環平均 %{y:.4g}<extra></extra>"))
    fig.update_layout(showlegend=True)
    ylab = with_unit(f"{param} 環平均 ring mean" if param else "ring mean 環平均", unit)
    return layout(fig, "Radial profile", "距晶圓中心 radius from centre (mm)", ylab, 260)


# --------------------------------------------------------------------------- SPC
LIMIT_NAME = {"IMR": "UCL / LCL 管制界限 (±3σ)", "EWMA": "UCL / LCL EWMA 界限", "CUSUM": "±h 決策界限 decision interval"}
STAT_LABEL = {"mean": "wafer mean", "nu_1sigma_pct": "1σ %", "range": "range"}


STAT_AXIS = {"mean": ("wafer mean 晶圓平均", True), "nu_1sigma_pct": ("within-wafer 1σ 片內不均勻度", False),
             "range": ("within-wafer range 片內全距", True)}  # (name, in the parameter's unit?)


def spc_figure(group, sw: pd.DataFrame, ch, stat: str, color: str, phase1: int, param: str = "",
               unit: str = "") -> go.Figure:
    """One control chart: points, limits, CL, end of Phase I, OOC rings. sw = this group's wafers in time order."""
    x = sw.timestamp
    z = (np.asarray(ch.statistic) - ch.cl) / ch.sigma if ch.sigma > 0 else np.zeros(len(sw))
    fig = go.Figure()
    fig.add_scatter(x=x, y=ch.statistic, mode="lines+markers", name=f"{group} {STAT_LABEL.get(stat, stat)}",
                    line=dict(color=color, width=1.5), marker=dict(size=5),
                    customdata=np.column_stack([sw.wafer_id, z]),
                    hovertemplate="%{customdata[0]}<br>%{y:.4f}<br>" +
                                  ("偏離 CL %{customdata[1]:+.1f}σ<extra></extra>" if ch.chart_type == "IMR" else "<extra></extra>"))
    fig.add_scatter(x=x, y=ch.ucl, mode="lines", name=LIMIT_NAME[ch.chart_type], line=dict(color=viz.STATUS["critical"], width=1),
                    hovertemplate="UCL %{y:.4f}<extra></extra>")
    fig.add_scatter(x=x, y=ch.lcl, mode="lines", showlegend=False, line=dict(color=viz.STATUS["critical"], width=1),
                    hovertemplate="LCL %{y:.4f}<extra></extra>")
    if ch.chart_type != "CUSUM":
        fig.add_hline(y=ch.cl, line=dict(color=viz.INK_2, width=1))
        legend_line(fig, f"CL 中心線 = {ch.cl:.4g}", viz.INK_2, width=1)
    k1 = min(phase1, len(sw)) - 1
    if 0 <= k1 < len(sw) - 1:
        fig.add_vline(x=x.iloc[k1], line=dict(color=viz.MUTED, dash="dash", width=1))
        legend_line(fig, "Phase I 結束 end of baseline", viz.MUTED, dash="dash", width=1)
    ooc = ch.out_of_control
    if ooc.size:
        fig.add_scatter(x=x.iloc[ooc], y=ch.statistic[ooc], mode="markers", name="OOC 違規點",
                        marker=dict(size=11, color="rgba(0,0,0,0)", line=dict(color=viz.STATUS["critical"], width=2)),
                        hovertemplate="OOC 違規點<br>%{y:.4f}<extra></extra>")
    name, in_unit = STAT_AXIS.get(stat, (stat, False))
    ylab = f"{param} · {name}" if param else name
    ylab = with_unit(ylab, unit if in_unit else "%" if stat == "nu_1sigma_pct" else "")
    return layout(fig, f"{group}  {ch.chart_type}", "量測時間 measurement time", ylab, 340)


# --------------------------------------------------------------------------- MSA
def grr_figure(g: dict) -> go.Figure:
    comps = ["repeatability", "reproducibility", "gauge_rr", "part_to_part"]
    fig = go.Figure(go.Bar(x=[g["pct_study_var"][c] for c in comps], y=comps, orientation="h", marker_color=viz.SERIES[0],
                           name="% study variation 研究變異 %", text=[f"{g['pct_study_var'][c]:.1f}%" for c in comps],
                           textposition="outside", hovertemplate="%{y}: %{x:.1f}% of study variation<extra></extra>"))
    fig.add_vline(x=10, line=dict(color=viz.STATUS["good"], width=1))
    fig.add_vline(x=30, line=dict(color=viz.STATUS["critical"], width=1))
    legend_line(fig, "10% acceptable 可接受", viz.STATUS["good"], width=1)
    legend_line(fig, "30% unacceptable 不可接受", viz.STATUS["critical"], width=1)
    fig.update_yaxes(autorange="reversed")
    return layout(fig, "Variance components (10% / 30% guides)", "佔研究變異 % of study variation", "變異來源 source", 320)


def bland_altman_figure(wide: pd.DataFrame, spec_off: float, ref: str = "FT01", cand: str = "FT02") -> go.Figure:
    diff = wide[cand] - wide[ref]
    fig = go.Figure(go.Scatter(x=wide[ref], y=diff, mode="markers", marker=dict(size=6, color=viz.SERIES[0]),
                               name="site difference 各點差值", customdata=np.column_stack([wide.wafer_id, wide.site]),
                               hovertemplate=f"%{{customdata[0]}} site %{{customdata[1]}}<br>{ref} %{{x:.3f}} nm<br>"
                                             f"{cand} − {ref} = %{{y:+.3f}} nm<extra></extra>"))
    for y in (-spec_off, spec_off):
        fig.add_hline(y=y, line=dict(color=viz.STATUS["critical"], width=1))
    fig.add_hline(y=float(diff.mean()), line=dict(color=viz.INK_2, width=1, dash="dash"))
    legend_line(fig, "±matching spec 匹配規格", viz.STATUS["critical"], width=1)
    legend_line(fig, f"mean offset 平均偏差 = {diff.mean():+.3f} nm", viz.INK_2, dash="dash", width=1)
    return layout(fig, f"Bland-Altman: {cand} − {ref} vs {ref} (red = matching spec)", f"{ref} (nm)", "difference (nm)")


# --------------------------------------------------------------------------- recipe studies
def sensitivity_figure(r: pd.DataFrame, s: pd.DataFrame) -> go.Figure:
    fig = go.Figure([go.Scatter(x=r.thickness_nm, y=r.est_precision_nm, name="reflectometry 反射儀",
                                line=dict(color=viz.SERIES[0]), mode="lines+markers",
                                hovertemplate="reflectometry 反射儀<br>%{x:g} nm → 1σ %{y:.3g} nm<extra></extra>"),
                     go.Scatter(x=s.thickness_nm, y=s.est_precision_nm, name="SE 65/70/75° 橢偏儀",
                                line=dict(color=viz.SERIES[1]), mode="lines+markers",
                                hovertemplate="SE 橢偏儀<br>%{x:g} nm → 1σ %{y:.3g} nm<extra></extra>")])
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return layout(fig, "Estimated 1σ precision vs SiO2 thickness", "SiO2 膜厚 thickness (nm)", "1σ 量測精度 precision (nm)")


def tn_figure(c: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(x=c.thickness_nm, y=c.A_stderr, mode="lines+markers", line=dict(color=viz.SERIES[0]),
                               name="σ(A) when n is floated 浮動 n 的不確定度",
                               hovertemplate="%{x:g} nm → σ(A) = %{y:.3g}<extra></extra>"))
    fig.add_hline(y=0.01, line=dict(color=viz.STATUS["critical"], width=1, dash="dash"))
    legend_line(fig, "0.01 reference limit 參考門檻", viz.STATUS["critical"], dash="dash", width=1)
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return layout(fig, "Uncertainty of n (Cauchy A) when floated with thickness", "膜厚 thickness (nm)",
                  "σ(A)：n（Cauchy A）的不確定度 uncertainty of n")


# --------------------------------------------------------------------------- DOE
def pareto_figure(fit, title: str) -> go.Figure:
    tab = fit.table[fit.table["term"] != "intercept"].copy()
    tab["abs_t"] = tab["t"].abs()
    tab = tab.sort_values("abs_t")
    t_crit = float(t_dist.ppf(0.975, fit.dof)) if fit.dof > 0 else None
    sig = (tab["p"] < 0.05).to_numpy()
    fig = go.Figure()
    for mask, name, color in ((sig, "p < 0.05 significant 顯著", viz.SERIES[0]), (~sig, "p ≥ 0.05 not significant 不顯著", viz.AXIS)):
        part = tab[mask]
        fig.add_bar(x=part["abs_t"], y=part["term"], orientation="h", marker_color=color, name=name,
                    customdata=np.column_stack([part["coef"], part["p"]]) if len(part) else None,
                    hovertemplate="%{y}<br>|t| = %{x:.2f}<br>係數 coef %{customdata[0]:.4g}"
                                  "<br>p = %{customdata[1]:.3g}<extra></extra>")
    fig.update_yaxes(categoryorder="array", categoryarray=list(tab["term"]))
    fig.update_layout(barmode="overlay")
    if t_crit:
        fig.add_vline(x=t_crit, line=dict(color=viz.INK_2, dash="dash", width=1))
        legend_line(fig, f"p = 0.05 threshold 門檻 (|t| = {t_crit:.2f})", viz.INK_2, dash="dash", width=1)
    fig = layout(fig, title, "|t|（標準化效應 standardised effect）", "模型項 model term", max(320, 26 * len(tab) + 190))
    fig.update_layout(margin=dict(t=125))  # three legend rows sit between the title and the plot
    return fig


def doe_contour_figure(x, y, z, show: str, xa: str, ya: str, runs: pd.DataFrame, recipe: dict, title: str) -> go.Figure:
    fig = go.Figure(go.Contour(x=x, y=y, z=z, colorscale=viz.PLOTLY_SEQ, contours=dict(showlabels=True, labelfont=dict(size=10)),
                               colorbar=dict(title=show), hovertemplate=f"{xa} %{{x:.3g}}<br>{ya} %{{y:.3g}}<br>"
                                                                        f"{show} %{{z:.3g}}<extra></extra>"))
    fig.add_scatter(x=runs[xa], y=runs[ya], mode="markers", name="design runs 實驗點",
                    marker=dict(size=8, color=viz.SURFACE, line=dict(color=viz.INK, width=1.5)),
                    hovertemplate=f"design run 實驗點<br>{xa} %{{x:.3g}}<br>{ya} %{{y:.3g}}<extra></extra>")
    fig.add_scatter(x=[recipe[xa]], y=[recipe[ya]], mode="markers", name="suggested recipe 建議配方",
                    marker=dict(size=14, symbol="star", color=viz.SERIES[1], line=dict(color=viz.SURFACE, width=2)),
                    hovertemplate="suggested recipe 建議配方<extra></extra>")
    return layout(fig, title, xa, ya, 480)


# --------------------------------------------------------------------------- fab simulator
def yield_trend_figure(w: pd.DataFrame) -> go.Figure:
    lot_y = w.groupby(["lot_index", "lot_id"])["yield"].mean().reset_index()
    med = float(lot_y["yield"].median())
    mad = 1.4826 * float((lot_y["yield"] - med).abs().median()) or float(lot_y["yield"].std())
    fig = go.Figure(go.Scatter(x=lot_y["lot_index"], y=100 * lot_y["yield"], mode="lines+markers", name="lot mean yield 每批平均良率",
                               line=dict(color=viz.SERIES[0], width=1.5), marker=dict(size=5), customdata=lot_y["lot_id"],
                               hovertemplate="%{customdata} (lot %{x})<br>平均良率 mean yield %{y:.1f}%<extra></extra>"))
    fig.add_hline(y=100 * med, line=dict(color=viz.INK_2, width=1))
    fig.add_hline(y=100 * (med - 3 * mad), line=dict(color=viz.STATUS["critical"], width=1, dash="dash"))
    legend_line(fig, f"median 中位數 = {100 * med:.1f}%", viz.INK_2, width=1)
    legend_line(fig, f"median − 3σ alert 警戒線 = {100 * (med - 3 * mad):.1f}%", viz.STATUS["critical"], dash="dash", width=1)
    return layout(fig, "每批平均良率（所有晶圓都有電測與良率）", "批次序號 lot index（D0001 = 0）", "每批平均良率 lot mean yield (%)", 340)


def die_map_figure(codes: np.ndarray, gx, gy, r_eff: float, title: str) -> go.Figure:
    fig = go.Figure()
    for c in CAUSE_NAME:
        sel = codes == c
        if not sel.any():
            continue
        fig.add_scatter(x=gx[sel], y=gy[sel], mode="markers", name=f"{CAUSE_NAME[c]} ({sel.sum()})",
                        marker=dict(symbol="square", size=9, color=CAUSE_COLOR[c]),
                        hovertemplate=f"{CAUSE_NAME[c]}<br>x %{{x:.0f}} mm, y %{{y:.0f}} mm<extra></extra>")
    r = r_eff + 3
    fig.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r, line=dict(color=viz.AXIS))
    legend_line(fig, "wafer edge 晶圓邊緣", viz.AXIS)
    fig = layout(fig, title, "x (mm)", "y (mm)", 520)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


# --------------------------------------------------------------------------- inline defect inspection / cross-role requests
GROUP_COLOR = {"split": viz.SERIES[0], "baseline": viz.SERIES[1], "lot": viz.SERIES[0]}
GROUP_NAME = {"split": "split", "baseline": "baseline", "lot": "inspected count 檢查數量"}


def defect_counts_figure(counts: pd.DataFrame, maxout: int, title: str) -> go.Figure:
    """One bar per wafer (colour = split / baseline group), red dashed maxout line, grey median line."""
    fig = go.Figure()
    for grp, g in counts.groupby("group", sort=False):
        fig.add_bar(x=g["wafer_id"], y=g["count"], name=GROUP_NAME.get(grp, grp),
                    marker=dict(color=GROUP_COLOR.get(grp, viz.SERIES[0]), cornerradius=4),
                    hovertemplate="%{x}<br>%{y:,} defects<extra>" + str(grp) + "</extra>")
    med = float(counts["count"].median())
    near = counts["count"].max() >= 0.3 * maxout  # far below the maxout, the line would flatten the bars
    if near:
        fig.add_hline(y=maxout, line=dict(color=viz.STATUS["critical"], dash="dash", width=1.5))
    fig.add_hline(y=med, line=dict(color=viz.MUTED, width=1.5))
    legend_line(fig, f"maxout 機台上限 = {maxout:,}" + ("" if near else "（遠高於圖上範圍 far above the chart）"),
                viz.STATUS["critical"], "dash")
    legend_line(fig, f"median 中位數 = {med:,.0f}", viz.MUTED)
    layout(fig, title, "晶圓 wafer", "缺陷數 defect count")
    fig.update_layout(bargap=0.25, legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    fig.update_yaxes(range=[0, (max(maxout, counts["count"].max()) if near else counts["count"].max()) * 1.1])
    return fig


def review_pareto_figure(classes: pd.Series, nuisance: str = "Non-visible") -> go.Figure:
    """Review classes high to low as % of reviewed defects: real classes blue, the non-visible (nuisance) class grey."""
    s = classes.sort_values(ascending=False)
    pct = 100 * s / max(s.sum(), 1)
    fig = go.Figure()
    for is_nv, name, color in ((False, "real defect classes 真缺陷類別", viz.SERIES[0]),
                               (True, f"{nuisance} (nuisance) 看不到真缺陷", viz.MUTED)):
        sel = (pct.index == nuisance) == is_nv
        fig.add_bar(x=list(pct.index[sel]), y=pct[sel], name=name, text=[f"{v:.0f}%" for v in pct[sel]],
                    textposition="outside", marker=dict(color=color, cornerradius=4),
                    customdata=s[sel].to_numpy(), hovertemplate="%{x}: %{y:.1f}% (%{customdata} defects)<extra></extra>")
    layout(fig, f"Review 分類 · {int(s.sum())} defects reviewed", "缺陷類別 class", "佔 review 比例 share (%)")
    fig.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    fig.update_xaxes(categoryorder="array", categoryarray=list(pct.index))
    fig.update_yaxes(range=[0, pct.max() * 1.18])
    return fig


def adders_figure(t: pd.DataFrame) -> go.Figure:
    """Per wafer: previous-layer count (light blue) and this-layer count (blue); split | baseline separated."""
    t = pd.concat([t[t["group"] == "split"], t[t["group"] == "baseline"]])
    fig = go.Figure()
    fig.add_bar(x=t["wafer_id"], y=t["previous"], name="previous layer 前層數量", marker=dict(color=viz.SEQ_BLUE[1], cornerradius=4),
                hovertemplate="%{x}<br>previous %{y:,}<extra></extra>")
    fig.add_bar(x=t["wafer_id"], y=t["current"], name="this layer 本層數量", marker=dict(color=viz.SERIES[0], cornerradius=4),
                customdata=(t["current"] - t["previous"]).to_numpy(),
                hovertemplate="%{x}<br>this layer %{y:,} · adders %{customdata:,}<extra></extra>")
    n_split = int((t["group"] == "split").sum())
    fig.add_vline(x=n_split - 0.5, line=dict(color=viz.MUTED, dash="dot", width=1.5))
    fig.add_annotation(x=(n_split - 1) / 2, y=1.0, yref="paper", text="split", showarrow=False, yanchor="bottom")
    fig.add_annotation(x=n_split + (len(t) - n_split - 1) / 2, y=1.0, yref="paper", text="baseline", showarrow=False,
                       yanchor="bottom")
    legend_line(fig, "split | baseline 分隔", viz.MUTED, "dot")
    layout(fig, "前層 vs 本層（adder = 本層 − 前層）· previous vs this layer", "晶圓 wafer", "缺陷數 defect count")
    fig.update_layout(barmode="group", bargap=0.25, legend=dict(orientation="h", y=1.08, yanchor="bottom", x=0),
                      margin=dict(t=110))
    return fig


def bin_corr_figure(t: pd.DataFrame, params: list[str], bin_name: str) -> go.Figure:
    """Small multiples: bin loss vs each inline parameter, one dot per wafer, grey dashed least-squares line."""
    from plotly.subplots import make_subplots

    rs = {p: float(np.corrcoef(t[p], t["bin_loss"])[0, 1]) for p in params}
    fig = make_subplots(rows=1, cols=len(params), shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=[f"{p} · r = {rs[p]:+.2f}" for p in params])
    for i, p in enumerate(params, start=1):
        fig.add_scatter(x=t[p], y=t["bin_loss"], mode="markers", name="wafer 晶圓", showlegend=i == 1,
                        marker=dict(size=9, color=viz.SERIES[0], line=dict(color=viz.SURFACE, width=2)),
                        customdata=t[["wafer_id"]], hovertemplate="%{customdata[0]}<br>" + p + " %{x:.4g}<br>loss %{y:.1f}%"
                                                                   "<extra></extra>", row=1, col=i)
        b1, b0 = np.polyfit(t[p], t["bin_loss"], 1)
        xs = np.linspace(t[p].min(), t[p].max(), 20)
        fig.add_scatter(x=xs, y=b0 + b1 * xs, mode="lines", name="least-squares line 最小平方線", showlegend=i == 1,
                        line=dict(color=viz.MUTED, dash="dash", width=1.5), hoverinfo="skip", row=1, col=i)
        fig.update_xaxes(title_text=p, row=1, col=i)
    layout(fig, f"{bin_name} 損失 vs inline 量測 · loss vs inline metrology", "", "bin 損失 loss (%)", height=360)
    for i in range(2, len(params) + 1):
        fig.update_yaxes(title_text="", row=1, col=i)
    fig.update_layout(legend=dict(orientation="h", y=1.12, yanchor="bottom", x=0), margin=dict(t=120))
    return fig
