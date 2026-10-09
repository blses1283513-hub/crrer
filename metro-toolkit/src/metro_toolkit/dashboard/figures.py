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
                                                      font=dict(size=14)), height=height,
                      hoverlabel=dict(align="left", bgcolor=viz.SURFACE, bordercolor=viz.AXIS, namelength=-1,
                                      font=dict(color=viz.INK, size=12)))
    fig.update_xaxes(title_text=xlab)  # text only: title=... would also reset the black axis-name font from viz
    fig.update_yaxes(title_text=ylab)
    return fig


# --------------------------------------------------------------------------- film stack
def fit_hover(wl, ym, yf, name: str, unit: str = "") -> list[str]:
    """Tooltip for each measured point: model value, residual and its size against the typical misfit (RMS)."""
    wl, ym, yf = (np.asarray(a, float) for a in (wl, ym, yf))
    res = ym - yf
    rms = float(np.sqrt(np.mean(res**2))) or 1e-12
    out = []
    for i in range(len(wl)):
        z = res[i] / rms
        head = [f"<b>λ {wl[i]:.0f} nm</b>", f"measured 量測 {name} = <b>{ym[i]:.4f}</b>{unit}", f"model 模型 {yf[i]:.4f}{unit}",
                f"residual 殘差 {res[i]:+.4f}{unit} = {z:+.1f} × RMS ({rms:.3g})"]
        if abs(z) > 3:
            out.append(hover_card(head, "watch", "離模型較遠 off the model",
                                  [(f"殘差是整條曲線典型誤差（RMS）的 {abs(z):.1f} 倍（> 3 倍）",
                                    f"the residual is {abs(z):.1f}× the curve's typical misfit (RMS), above 3×")],
                                  ("看是一整段波長都偏（模型問題：固定層、n,k）還是只有這一點（雜訊、離群值）",
                                   "check whether a whole wavelength band is off (a model problem: fixed layer, n,k) or just this point (noise, an outlier)")))
        else:
            out.append(hover_card(head, "good", "貼合 on the curve",
                                  [(f"殘差 = 量測 − 模型 = {res[i]:+.4f}，只有 RMS 的 {abs(z):.1f} 倍（< 3 倍）：隨機雜訊等級",
                                    f"residual = measured − model = {res[i]:+.4f}, only {abs(z):.1f}× RMS (< 3×): random-noise level")]))
    return out


def model_hover(wl, yf, name: str, unit: str = "") -> list[str]:
    return [hover_card([f"<b>λ {float(w):.0f} nm</b>", f"model fit 模型 {name} = <b>{float(y):.4f}</b>{unit}"], None, "模型曲線 model fit",
                       [("好的擬合：量測點隨機散在曲線兩側；一整段在同一側 = 模型有系統性偏差（χ² 不一定會警示，尤其是固定的底層）",
                         "a good fit has the measured points scattered randomly on both sides; a whole band on one side means a "
                         "systematic model error (χ² may not warn, especially about a wrong fixed layer)")])
            for w, y in zip(wl, yf)]


def fit_figures(technique: str, wl, meas, fitted_stack, angles=None) -> list[go.Figure]:
    """Reflectance (one figure) or Ψ and Δ at the middle angle (two figures): measured vs model fit."""
    from metro_toolkit.metrology.thinfilm import ellipsometry, reflectance

    if technique == "reflectometry":
        fig = go.Figure()
        rf = reflectance(fitted_stack, wl)
        fig.add_scatter(x=wl, y=meas.data["R"], mode="markers", name="measured 量測", marker=dict(size=4, color=viz.SERIES[0]),
                        customdata=fit_hover(wl, meas.data["R"], rf, "R"), hovertemplate=card_template())
        fig.add_scatter(x=wl, y=rf, mode="lines", name="model fit 模型擬合", line=dict(color=viz.SERIES[1], width=2),
                        customdata=model_hover(wl, rf, "R"), hovertemplate=card_template())
        return [layout(fig, "Reflectance: measured vs fitted model", "波長 wavelength (nm)", "反射率 reflectance R (0–1)")]
    a = float(angles[len(angles) // 2])
    psi_m, delta_m = meas.data[a]
    psi_f, delta_f = ellipsometry(fitted_stack, wl, a)
    figs = []
    for ym, yf, lab in ((psi_m, psi_f, "Ψ"), (delta_m, delta_f, "Δ")):
        fig = go.Figure([
            go.Scatter(x=wl, y=ym, mode="markers", name="measured 量測", marker=dict(size=4, color=viz.SERIES[0]),
                       customdata=fit_hover(wl, ym, yf, lab, "°"), hovertemplate=card_template()),
            go.Scatter(x=wl, y=yf, mode="lines", name="model fit 模型擬合", line=dict(color=viz.SERIES[1]),
                       customdata=model_hover(wl, yf, lab, "°"), hovertemplate=card_template())])
        figs.append(layout(fig, f"{lab} at {a:.0f}°", "波長 wavelength (nm)", f"{lab} 橢偏角 (deg)"))
    return figs


# --------------------------------------------------------------------------- wafer map
def site_hover(w: pd.DataFrame, um: dict, unit: str) -> list[str]:
    """Tooltip for each measured site: where it is, how far from the wafer mean, and whether it is an outlier."""
    vals = w.value.to_numpy(float)
    n = len(vals)
    mean, sd = float(um["mean"]), float(np.std(vals, ddof=1)) if n > 1 else 0.0
    r = np.hypot(w.x, w.y).to_numpy(float)
    R = float(r.max()) or 1.0
    lsl = float(w["lsl"].dropna().median()) if "lsl" in w and w["lsl"].notna().any() else np.nan
    usl = float(w["usl"].dropna().median()) if "usl" in w and w["usl"].notna().any() else np.nan
    u = f" {unit}" if unit else ""
    sites = list(w["site"]) if "site" in w else list(range(1, n + 1))
    out = []
    for i in range(n):
        others = np.delete(vals, i)
        mo, so = float(others.mean()), float(others.std(ddof=1)) if len(others) > 1 else 0.0
        zl = (vals[i] - mo) / so if so > 0 else 0.0
        dev = vals[i] - mean
        zone = "邊緣 edge" if r[i] >= 0.8 * R else "中心 centre" if r[i] <= 0.3 * R else "中間 mid"
        head = [f"<b>site {sites[i]}</b> · x {w.x.iloc[i]:.0f}, y {w.y.iloc[i]:.0f} mm", f"r = {r[i]:.0f} mm（{zone}）",
                f"value <b>{vals[i]:.4g}</b>{u}", f"離晶圓平均 vs wafer mean {dev:+.4g}{u}（{dev / sd if sd else 0:+.1f}σ of sites）"]
        oos = np.isfinite(lsl) and np.isfinite(usl) and (vals[i] < lsl or vals[i] > usl)
        if oos:
            out.append(hover_card(head, "act", "超出規格 out of spec",
                                  [(f"{vals[i]:.4g} 在規格 {lsl:.4g}–{usl:.4g}{u} 之外", f"{vals[i]:.4g} is outside the spec {lsl:.4g}–{usl:.4g}{u}")],
                                  ("先確認這個點（量測），再依 OCAP 做 disposition", "verify the site first, then disposition per the OCAP")))
        elif abs(zl) > 3:
            out.append(hover_card(head, "act", "單點離群 single-site outlier",
                                  [(f"和其他 {n - 1} 點比 z = {zl:+.1f}（> 3）：其他點平均 {mo:.4g}、σ {so:.3g}",
                                    f"against the other {n - 1} sites z = {zl:+.1f} (> 3): they average {mo:.4g}, σ {so:.3g}")],
                                  ("先查這個點（微粒、pattern recognition、對焦）再判斷是不是製程形狀",
                                   "check this site (particle, pattern recognition, focus) before calling it a process shape")))
        elif abs(zl) > 2:
            out.append(hover_card(head, "watch", "偏離 unusual",
                                  [(f"和其他點比 z = {zl:+.1f}（2–3 之間）", f"against the other sites z = {zl:+.1f} (between 2 and 3)")]))
        else:
            out.append(hover_card(head, "good", "正常 typical",
                                  [(f"和其他點比 z = {zl:+.1f}（< 2）：符合整片的形狀", f"against the other sites z = {zl:+.1f} (< 2): consistent with the wafer's shape")]))
    return out


def wafer_map_figure(w: pd.DataFrame, um: dict, mode: str, title: str) -> go.Figure:
    r_eff = float(np.hypot(w.x, w.y).max())
    unit0 = str(w.unit.iloc[0]) if "unit" in w and len(w) else ""
    X, Y, Z = interpolate_map(w.x, w.y, w.value, radius_mm=r_eff, grid=101)
    if mode.startswith("absolute"):
        zz, cs, zmid = Z, viz.PLOTLY_SEQ, None
    else:
        zz, cs, zmid = Z - um["mean"], viz.PLOTLY_DIV, 0.0
    what = "離平均 deviation from the mean" if zmid == 0.0 else "value"
    fig = go.Figure(go.Contour(x=X[0], y=Y[:, 0], z=zz, colorscale=cs, zmid=zmid, ncontours=16,
                               contours=dict(showlines=False), colorbar=dict(title=unit0),
                               hovertemplate=f"x %{{x:.0f}} mm, y %{{y:.0f}} mm<br>內插 interpolated {what} %{{z:.4g}} {unit0}"
                                             "<br>─────────<br><b>ℹ️ 內插值 interpolated</b><br>• 這是量測點之間的估計，不是量測值；"
                                             "要看真實量測請把滑鼠移到白色圓點"
                                             "<br><i>an estimate between sites, not a measurement; hover a white dot for a real "
                                             "measurement</i><extra></extra>"))
    fig.add_scatter(x=w.x, y=w.y, mode="markers", marker=dict(size=7, color=viz.SURFACE, line=dict(color=viz.INK_2, width=1)),
                    customdata=site_hover(w, um, unit0), hovertemplate=card_template(), name="sites 量測點")
    fig.add_shape(type="circle", x0=-r_eff, y0=-r_eff, x1=r_eff, y1=r_eff, line=dict(color=viz.AXIS))
    legend_line(fig, "wafer edge 晶圓邊緣", viz.AXIS)
    fig = layout(fig, title, "x (mm)", "y (mm)", 520)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def zernike_hover(zk: dict, unit: str) -> list[str]:
    from metro_toolkit.guide.insights import SIGNATURE

    coef = {kk: v for kk, v in zk["coefficients"].items() if kk != "piston"}
    tot = sum(c * c for c in coef.values()) or 1.0
    u = f" {unit}" if unit else ""
    out = []
    for term, c in coef.items():
        share = 100 * c * c / tot
        zh, en = SIGNATURE.get(term, (term, term))
        head = [f"<b>{term}</b>", f"coefficient 係數 <b>{c:+.4g}</b>{u}", f"佔 share of Σ係數² = {share:.0f}%"]
        rule = (f"佔比 = 係數² ÷ 各項係數平方和（不含 piston = 平均值）= {share:.0f}%；≥ 50% 視為這片晶圓的主導形狀",
                f"share = coefficient² ÷ the sum of squared coefficients (piston, the mean, excluded) = {share:.0f}%; "
                "50% or more is treated as the wafer's dominant shape")
        if share >= 50:
            out.append(hover_card(head, "watch", "主導的形狀 dominant shape", [rule, (zh, en)],
                                  ("對照晶圓圖確認形狀，再查對應的硬體", "confirm the shape on the wafer map, then check the matching hardware")))
        else:
            out.append(hover_card(head, None, "次要的項 minor term", [rule, (zh, en)]))
    return out


def zernike_figure(zk: dict, param: str = "", unit: str = "") -> go.Figure:
    coef = {kk: v for kk, v in zk["coefficients"].items() if kk != "piston"}
    fig = go.Figure(go.Bar(x=list(coef.values()), y=list(coef), orientation="h", marker_color=viz.SERIES[0],
                           name="Zernike coefficient 係數", customdata=zernike_hover(zk, unit), hovertemplate=card_template()))
    fig.update_yaxes(autorange="reversed")
    xlab = with_unit(f"{param} Zernike 係數 coefficient" if param else "Zernike 係數 coefficient", unit)
    return layout(fig, f"Spatial signature (R² {zk['r2']:.2f})", xlab, "空間項 Zernike term", 260)


def radial_hover(rp: pd.DataFrame, unit: str) -> list[str]:
    u = f" {unit}" if unit else ""
    med = float(rp["std"].median() or 0)
    means = rp["mean"].to_numpy(float)
    out = []
    for i in range(len(rp)):
        head = [f"<b>r ≈ {rp.r_mm.iloc[i]:.0f} mm</b>", f"ring mean 環平均 <b>{means[i]:.4g}</b>{u} ± {float(rp['std'].iloc[i] or 0):.3g}",
                f"與中心環差 vs centre ring {means[i] - means[0]:+.4g}{u}"]
        if i:
            head.append(f"與前一環差 vs previous ring {means[i] - means[i - 1]:+.4g}{u}")
        if i == len(rp) - 1 and i >= 1:
            roll = means[i] - means[i - 1]
            if abs(roll) > 2 * med:
                out.append(hover_card(head, "watch", "邊緣滾降 edge roll-off",
                                      [(f"最外圈比前一圈差 {roll:+.4g}{u}，超過 2 × 各環典型雜訊（{2 * med:.3g}）",
                                        f"the outermost ring differs from the previous ring by {roll:+.4g}{u}, more than 2 × the "
                                        f"typical ring noise ({2 * med:.3g})")],
                                      ("查邊緣環（edge / focus ring）、邊緣排除區附近的製程", "check the edge / focus ring and the edge-exclusion processes")))
            else:
                out.append(hover_card(head, "good", "邊緣正常 edge normal",
                                      [(f"最外圈比前一圈只差 {roll:+.4g}{u}，沒超過 2 × 各環典型雜訊（{2 * med:.3g}）",
                                        f"the outermost ring differs from the previous ring by only {roll:+.4g}{u}, within 2 × the typical "
                                        f"ring noise ({2 * med:.3g})")]))
        else:
            out.append(hover_card(head, None, "環平均 ring mean",
                                  [("每一圈是距中心相同半徑的所有量測點的平均；誤差線 = ±1σ。圈與圈之間的差就是徑向形狀（碗形、邊緣滾降）",
                                    "each ring averages all sites at the same distance from the centre; the error bar is ±1σ. "
                                    "Differences between rings are the radial shape (bowl, edge roll-off)")]))
    return out


def radial_figure(rp: pd.DataFrame, param: str = "", unit: str = "") -> go.Figure:
    fig = go.Figure(go.Scatter(x=rp.r_mm, y=rp["mean"], mode="lines+markers", line=dict(color=viz.SERIES[0]),
                               name="ring mean ±1σ 環平均 ±1σ", error_y=dict(array=rp["std"].fillna(0), color=viz.MUTED),
                               customdata=radial_hover(rp, unit), hovertemplate=card_template()))
    fig.update_layout(showlegend=True)
    ylab = with_unit(f"{param} 環平均 ring mean" if param else "ring mean 環平均", unit)
    return layout(fig, "Radial profile", "距晶圓中心 radius from centre (mm)", ylab, 260)


# --------------------------------------------------------------------------- SPC
LIMIT_NAME = {"IMR": "UCL / LCL 管制界限 (±3σ)", "EWMA": "UCL / LCL EWMA 界限", "CUSUM": "±h 決策界限 decision interval"}
STAT_LABEL = {"mean": "wafer mean", "nu_1sigma_pct": "1σ %", "range": "range"}


STAT_AXIS = {"mean": ("wafer mean 晶圓平均", True), "nu_1sigma_pct": ("within-wafer 1σ 片內不均勻度", False),
             "range": ("within-wafer range 片內全距", True)}  # (name, in the parameter's unit?)


RULE_WINDOW = {2: 3, 3: 5, 4: 8, 5: 6, 6: 15, 7: 14, 8: 8}  # points each Western Electric / Nelson rule looks at


def _cells(ch: str) -> int:
    """Display width of a character: CJK counts double."""
    return 2 if ord(ch) > 0x2E7F else 1


def wrap_hover(text: str, width: int = 58, indent: str = "") -> str:
    """Break a sentence into short lines (<br>) so a tooltip stays narrow enough not to be clipped by the chart edge.
    Breaks at a space when there is one, otherwise after any character (Chinese text has no spaces)."""
    lines, cur, w, last_space = [], "", 0, -1
    for ch in text:
        if w + _cells(ch) > width and cur:
            if last_space > 0:
                lines.append(cur[:last_space])
                cur = cur[last_space + 1:]
            else:
                lines.append(cur)
                cur = ""
            w = sum(_cells(c) for c in cur)
            last_space = cur.rfind(" ")
        cur += ch
        w += _cells(ch)
        if ch == " ":
            last_space = len(cur) - 1
    lines.append(cur)
    return f"<br>{indent}".join(x for x in lines if x.strip() or len(lines) == 1)


VERDICT = {"good": ("🟢", "正常 normal"), "watch": ("🟡", "注意 watch"), "act": ("🔴", "需處理 act"), None: ("ℹ️", "")}
TXT_W = 56  # tooltip text width in display cells (Chinese counts double)


def hover_card(head: list[str], verdict: str | None = None, label: str = "", reasons=(), nxt=None) -> str:
    """The tooltip every chart uses: what the point is (head lines), a verdict (🟢 / 🟡 / 🔴, or ℹ️ for neutral facts)
    with its label, the reasons with the numbers behind the rule (中文, English), and the next step (中文, English).
    The verdict thresholds are the ones the chart's own status line (guide/insights.py) uses."""
    icon, default = VERDICT[verdict]
    body = [f"<b>{icon} {label or default}</b>".replace("  </b>", "</b>")]
    for zh, en in reasons:
        body += [wrap_hover(f"• {zh}", TXT_W, "&nbsp;&nbsp;"), f"<i>{wrap_hover(en, TXT_W + 6)}</i>"]
    if nxt:
        body += [f"<i>→ {wrap_hover(nxt[0], TXT_W)}</i>", f"<i>{wrap_hover(nxt[1], TXT_W + 6)}</i>"]
    return "<br>".join(list(head) + ["─────────"] + body)


def card_template() -> str:
    return "%{customdata}<extra></extra>"


def _zs(z, i: int, w: int) -> str:
    return ", ".join(f"{v:+.1f}" for v in z[max(0, i - w + 1): i + 1])


def ooc_reasons(ch, i: int, z) -> list[tuple[str, str]]:
    """Why point i is out of control, as (中文, English) sentences with the numbers behind each rule.
    i is the LAST point of the pattern a rule looks at (that is the point the chart marks)."""
    from metro_toolkit.analysis.spc import RULE_TEXT

    out = []
    if ch.chart_type == "EWMA":
        v = float(ch.statistic[i])
        lim = float(ch.ucl[i] if v > ch.cl else ch.lcl[i])
        return [(f"EWMA 值 {v:.4g} {'高於上' if v > ch.cl else '低於下'}限 {lim:.4g}（EWMA 的界限前幾點較窄，之後趨於穩定）",
                 f"the EWMA value {v:.4g} is {'above the upper' if v > ch.cl else 'below the lower'} limit {lim:.4g} "
                 "(EWMA limits are narrower over the first points, then settle)")]
    if ch.chart_type == "CUSUM":
        v, h = float(ch.statistic[i]), float(ch.ucl[i])
        return [(f"累積和 {v:+.4g} 超出決策區間 ±h = ±{h:.4g}（{h / ch.sigma:.1f}σ）：單點離 CL 不遠，但連續同方向的偏差一直累積",
                 f"the cumulative sum {v:+.4g} is beyond the decision interval ±h = ±{h:.4g} ({h / ch.sigma:.1f}σ): no single "
                 "point is far from the CL, but small deviations in one direction have been adding up")]
    for _, rule, _ in (v for v in ch.violations if v[0] == i):
        w = RULE_WINDOW.get(rule, 1)
        zs = _zs(z, i, w)
        win = z[max(0, i - w + 1): i + 1]
        up = (win > 0).sum() >= (win < 0).sum()
        side_zh, side_en = ("上", "above") if up else ("下", "below")
        if rule == 1:
            out.append((f"WE1 規則 1：這一點離中心線 {z[i]:+.2f}σ，超出 ±3σ 管制界限（UCL / LCL）",
                        f"WE1: this point is {z[i]:+.2f}σ from the centre line, beyond the ±3σ control limits (UCL / LCL)"))
        elif rule == 2:
            n = int((win > 2).sum() if up else (win < -2).sum())
            out.append((f"WE2 規則 2：最近 3 點（z = {zs}）有 {n} 點在 CL {side_zh}方超過 2σ", f"WE2: {n} of the last 3 points "
                        f"(z = {zs}) are more than 2σ {side_en} the CL"))
        elif rule == 3:
            n = int((win > 1).sum() if up else (win < -1).sum())
            out.append((f"WE3 規則 3：最近 5 點（z = {zs}）有 {n} 點在 CL {side_zh}方超過 1σ", f"WE3: {n} of the last 5 points "
                        f"(z = {zs}) are more than 1σ {side_en} the CL"))
        elif rule == 4:
            out.append((f"WE4 規則 4：最近 8 點（z = {zs}）全都在 CL {side_zh}方：平均值已經移到一邊",
                        f"WE4: the last 8 points (z = {zs}) are all {side_en} the CL: the mean has moved to one side"))
        else:
            out.append((f"規則 {rule}：{RULE_TEXT[rule]}（最近 {w} 點 z = {zs}）", f"Rule {rule}: {RULE_TEXT[rule]} "
                        f"(last {w} points, z = {zs})"))
    return out


def spc_hover(ch, sw: pd.DataFrame, z, quantity: str, unit: str) -> list[str]:
    """One hover text per point: its value, distance from the centre line, limits and the OOC verdict with the reason."""
    u = f" {unit}" if unit else ""
    hit = {int(i) for i in ch.out_of_control}
    texts = []
    for i in range(len(ch.statistic)):
        v = float(ch.statistic[i])
        wid = str(sw.wafer_id.iloc[i]) if "wafer_id" in sw and i < len(sw) else f"#{i + 1}"
        when = pd.Timestamp(sw.timestamp.iloc[i]).strftime("%Y-%m-%d %H:%M") if i < len(sw) else ""
        head = [f"<b>{wid}</b> · {when}", f"{quantity}: <b>{v:.4f}</b>{u}"]
        if ch.chart_type == "IMR":
            head.append(f"離 CL {z[i]:+.2f}σ · from the CL {ch.cl:.4g}")
        head.append(f"UCL {ch.ucl[i]:.4f} / LCL {ch.lcl[i]:.4f}")
        if i in hit:
            texts.append(hover_card(head, "act", "OOC 違規 · out of control", ooc_reasons(ch, i, z),
                                    ("先確認量測，再依 OCAP", "verify the measurement first, then follow the OCAP")))
        else:
            if ch.chart_type == "IMR":
                why = (f"離 CL 只有 {abs(z[i]):.2f}σ（< 3σ），且這一點沒有觸發規則 WE1–WE4",
                       f"only {abs(z[i]):.2f}σ from the CL (< 3σ) and no rule WE1–WE4 fires at this point")
            elif ch.chart_type == "EWMA":
                why = (f"EWMA 值在界限之內（{ch.lcl[i]:.4g} … {ch.ucl[i]:.4g}）",
                       f"the EWMA value is inside its limits ({ch.lcl[i]:.4g} … {ch.ucl[i]:.4g})")
            else:
                why = (f"累積和在 ±h 之內（h = {ch.ucl[i]:.4g}）", f"the cumulative sum is inside ±h (h = {ch.ucl[i]:.4g})")
            texts.append(hover_card(head, "good", "正常 in control", [why]))
    return texts


def spc_figure(group, sw: pd.DataFrame, ch, stat: str, color: str, phase1: int, param: str = "",
               unit: str = "") -> go.Figure:
    """One control chart: points, limits, CL, end of Phase I, OOC rings. sw = this group's wafers in time order."""
    x = sw.timestamp
    z = (np.asarray(ch.statistic) - ch.cl) / ch.sigma if ch.sigma > 0 else np.zeros(len(sw))
    fig = go.Figure()
    sname, in_unit0 = STAT_AXIS.get(stat, (stat, False))
    quantity = f"{param} {sname}" if param else sname
    hover = spc_hover(ch, sw, z, quantity, unit if in_unit0 else "%" if stat == "nu_1sigma_pct" else "")
    fig.add_scatter(x=x, y=ch.statistic, mode="lines+markers", name=f"{group} {STAT_LABEL.get(stat, stat)}",
                    line=dict(color=color, width=1.5), marker=dict(size=5), customdata=hover,
                    hovertemplate="%{customdata}<extra></extra>")
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
                        customdata=[hover[int(i)] for i in ooc], hovertemplate="%{customdata}<extra></extra>")
    name, in_unit = STAT_AXIS.get(stat, (stat, False))
    ylab = f"{param} · {name}" if param else name
    ylab = with_unit(ylab, unit if in_unit else "%" if stat == "nu_1sigma_pct" else "")
    fig.update_layout(hoverlabel=dict(align="left", bgcolor=viz.SURFACE, bordercolor=viz.AXIS, namelength=-1,
                                      font=dict(color=viz.INK, size=12)))
    return layout(fig, f"{group}  {ch.chart_type}", "量測時間 measurement time", ylab, 340)


# --------------------------------------------------------------------------- MSA
GRR_TEXT = {"repeatability": ("重複性：同一台機台、同一個人重複量測同一個點的雜訊（對焦、光源、stage）",
                              "repeatability: noise when one tool measures the same site again and again (focus, lamp, stage)"),
            "reproducibility": ("再現性：機台之間（或操作者之間）的差異（calibration、recipe 不同）",
                                "reproducibility: the difference between tools (or operators) (calibration, recipe mismatch)"),
            "gauge_rr": ("Gauge R&R = 重複性 + 再現性，量測系統自己的總變異", "Gauge R&R = repeatability + reproducibility, the "
                         "measurement system's own total variation")}


def grr_hover(g: dict, comps: list[str]) -> list[str]:
    sv, pt = g["pct_study_var"], g.get("pct_tolerance", {})
    out = []
    for c in comps:
        v = sv[c]
        head = [f"<b>{c}</b>", f"佔研究變異 share of study variation <b>{v:.1f}%</b>"]
        if c in pt and pt[c] == pt[c]:
            head.append(f"佔公差 P/T = {pt[c]:.1f}%")
        if c == "part_to_part":
            out.append(hover_card(head, None, "產品本身的變異 part-to-part",
                                  [(f"這是真實的晶圓／產品差異，希望遠大於量測變異；ndc = {g['ndc']}（≥ 5 才分得出足夠的產品差異）",
                                    f"real wafer-to-wafer variation, which should be much larger than the gauge's; ndc = {g['ndc']} "
                                    "(5 or more is needed to resolve enough product classes)")]))
            continue
        rule = (f"判斷：< 10% 可接受、10–30% 邊緣（看用途與 P/T）、> 30% 不可接受；這一項 = {v:.1f}%",
                f"rule: < 10% acceptable, 10–30% marginal (judge by use and P/T), > 30% unacceptable; this one is {v:.1f}%")
        text = [rule, GRR_TEXT[c]]
        if v >= 30:
            out.append(hover_card(head, "act", "不可接受 unacceptable", text,
                                  ("暫停用這個量測系統做 SPC／放行判定，先修好再重做 GR&R",
                                   "stop using this gauge for SPC / release decisions; fix it and redo the GR&R")))
        elif v >= 10:
            out.append(hover_card(head, "watch", "邊緣 marginal", text,
                                  ("用 P/T 判斷是否夠用；有改善空間就先處理主要來源", "judge by P/T whether it is good enough; tackle the main source if it can be improved")))
        else:
            out.append(hover_card(head, "good", "可接受 acceptable", text))
    return out


def grr_figure(g: dict) -> go.Figure:
    comps = ["repeatability", "reproducibility", "gauge_rr", "part_to_part"]
    fig = go.Figure(go.Bar(x=[g["pct_study_var"][c] for c in comps], y=comps, orientation="h", marker_color=viz.SERIES[0],
                           name="% study variation 研究變異 %", text=[f"{g['pct_study_var'][c]:.1f}%" for c in comps],
                           textposition="outside", customdata=grr_hover(g, comps), hovertemplate=card_template()))
    fig.add_vline(x=10, line=dict(color=viz.STATUS["good"], width=1))
    fig.add_vline(x=30, line=dict(color=viz.STATUS["critical"], width=1))
    legend_line(fig, "10% acceptable 可接受", viz.STATUS["good"], width=1)
    legend_line(fig, "30% unacceptable 不可接受", viz.STATUS["critical"], width=1)
    fig.update_yaxes(autorange="reversed")
    return layout(fig, "Variance components (10% / 30% guides)", "佔研究變異 % of study variation", "變異來源 source", 320)


def ba_hover(wide: pd.DataFrame, spec_off: float, ref: str, cand: str) -> list[str]:
    diff = (wide[cand] - wide[ref]).to_numpy(float)
    mean = float(diff.mean())
    out = []
    for i in range(len(wide)):
        head = [f"<b>{wide.wafer_id.iloc[i]}</b> · site {wide.site.iloc[i]}", f"{ref} {wide[ref].iloc[i]:.3f} nm · {cand} {wide[cand].iloc[i]:.3f} nm",
                f"差值 difference {cand} − {ref} = <b>{diff[i]:+.3f}</b> nm"]
        inside = abs(diff[i]) <= spec_off
        why = [(f"這個點的差值 {diff[i]:+.3f} nm {'在' if inside else '超出'} ±{spec_off:g} nm 匹配規格{'之內' if inside else ''}",
                f"this site's difference {diff[i]:+.3f} nm is {'inside' if inside else 'outside'} the ±{spec_off:g} nm matching spec"),
               (f"但機台是否匹配看的是平均偏差（{mean:+.3f} nm）與斜率，不是單一點；單點有雜訊",
                f"but matching is judged on the mean offset ({mean:+.3f} nm) and the slope, not on a single site, which is noisy")]
        out.append(hover_card(head, "good" if inside else "watch", "在規格內 inside" if inside else "超出規格 outside", why))
    return out


def bland_altman_figure(wide: pd.DataFrame, spec_off: float, ref: str = "FT01", cand: str = "FT02") -> go.Figure:
    diff = wide[cand] - wide[ref]
    fig = go.Figure(go.Scatter(x=wide[ref], y=diff, mode="markers", marker=dict(size=6, color=viz.SERIES[0]),
                               name="site difference 各點差值", customdata=ba_hover(wide, spec_off, ref, cand),
                               hovertemplate=card_template()))
    for y in (-spec_off, spec_off):
        fig.add_hline(y=y, line=dict(color=viz.STATUS["critical"], width=1))
    fig.add_hline(y=float(diff.mean()), line=dict(color=viz.INK_2, width=1, dash="dash"))
    legend_line(fig, "±matching spec 匹配規格", viz.STATUS["critical"], width=1)
    legend_line(fig, f"mean offset 平均偏差 = {diff.mean():+.3f} nm", viz.INK_2, dash="dash", width=1)
    return layout(fig, f"Bland-Altman: {cand} − {ref} vs {ref} (red = matching spec)", f"{ref} (nm)", "difference (nm)")


# --------------------------------------------------------------------------- recipe studies
def sensitivity_hover(a: pd.DataFrame, b: pd.DataFrame, name: str, other: str) -> list[str]:
    out = []
    for t, p in zip(a.thickness_nm, a.est_precision_nm):
        po = float(np.interp(np.log(t), np.log(b.thickness_nm), b.est_precision_nm))
        head = [f"<b>{name}</b>", f"膜厚 thickness {t:g} nm", f"估計 1σ 精度 precision <b>{p:.3g}</b> nm", f"{other} 同厚度 {po:.3g} nm（相差 {max(p, po) / max(min(p, po), 1e-12):.1f} 倍 apart）"]
        rule = (f"判斷：1σ 精度 < 0.05 nm 才算夠用（本工具的門檻）；這個點 = {p:.3g} nm",
                f"rule: a 1σ precision below 0.05 nm is good enough (this tool's threshold); this point = {p:.3g} nm")
        if p < 0.05:
            out.append(hover_card(head, "good", "夠用 good enough", [rule]))
        else:
            out.append(hover_card(head, "watch", "精度不足 not precise enough", [rule],
                                  ("這個厚度請改用精度更好的技術（超薄膜用 SE），或換 recipe 後重做 GR&R",
                                   "use the more precise technique at this thickness (SE for ultra-thin films) or change the recipe and redo the GR&R")))
    return out


def sensitivity_figure(r: pd.DataFrame, s: pd.DataFrame) -> go.Figure:
    fig = go.Figure([go.Scatter(x=r.thickness_nm, y=r.est_precision_nm, name="reflectometry 反射儀",
                                line=dict(color=viz.SERIES[0]), mode="lines+markers",
                                customdata=sensitivity_hover(r, s, "reflectometry 反射儀", "SE"), hovertemplate=card_template()),
                     go.Scatter(x=s.thickness_nm, y=s.est_precision_nm, name="SE 65/70/75° 橢偏儀",
                                line=dict(color=viz.SERIES[1]), mode="lines+markers",
                                customdata=sensitivity_hover(s, r, "SE 橢偏儀", "反射儀 reflectometry"), hovertemplate=card_template())])
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return layout(fig, "Estimated 1σ precision vs SiO2 thickness", "SiO2 膜厚 thickness (nm)", "1σ 量測精度 precision (nm)")


def tn_hover(c: pd.DataFrame, limit: float = 0.01) -> list[str]:
    out = []
    for t, e in zip(c.thickness_nm, c.A_stderr):
        head = [f"膜厚 thickness <b>{t:g} nm</b>", f"σ(A) = <b>{e:.3g}</b>（n 的不確定度 uncertainty of n）"]
        rule = (f"判斷：σ(A) > {limit} 代表同時浮動 n 與厚度時，n 抓不準（和厚度高度相關）；這個點 = {e:.3g}",
                f"rule: σ(A) > {limit} means n cannot be pinned down when floated with thickness (they are highly correlated); "
                f"this point = {e:.3g}")
        if e > limit:
            out.append(hover_card(head, "watch", "n 抓不準 n poorly determined", [rule],
                                  ("這個厚度請固定 n（用厚膜或參考片量好的 n,k）", "fix n at this thickness (use n,k measured on a thick film or reference wafer)")))
        else:
            out.append(hover_card(head, "good", "可以浮動 n n can be floated", [rule]))
    return out


def tn_figure(c: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(x=c.thickness_nm, y=c.A_stderr, mode="lines+markers", line=dict(color=viz.SERIES[0]),
                               name="σ(A) when n is floated 浮動 n 的不確定度", customdata=tn_hover(c),
                               hovertemplate=card_template()))
    fig.add_hline(y=0.01, line=dict(color=viz.STATUS["critical"], width=1, dash="dash"))
    legend_line(fig, "0.01 reference limit 參考門檻", viz.STATUS["critical"], dash="dash", width=1)
    fig.update_xaxes(type="log")
    fig.update_yaxes(type="log")
    return layout(fig, "Uncertainty of n (Cauchy A) when floated with thickness", "膜厚 thickness (nm)",
                  "σ(A)：n（Cauchy A）的不確定度 uncertainty of n")


# --------------------------------------------------------------------------- DOE
def pareto_hover(part: pd.DataFrame, t_crit) -> list[str]:
    out = []
    for _, r in part.iterrows():
        head = [f"<b>{r['term']}</b>", f"係數 coefficient {r['coef']:+.4g}", f"|t| = <b>{abs(r['t']):.2f}</b> · p = {r['p']:.3g}"]
        thr = f"|t| 要超過 {t_crit:.2f} 才達 p = 0.05" if t_crit else "p < 0.05 才算顯著"
        thr_en = f"|t| must exceed {t_crit:.2f} for p = 0.05" if t_crit else "significant when p < 0.05"
        rule = (f"判斷：|t| = |係數| ÷ 標準誤；{thr}；這一項 p = {r['p']:.3g}", f"rule: |t| = |coefficient| ÷ standard error; {thr_en}; this term p = {r['p']:.3g}")
        if r["p"] < 0.05:
            out.append(hover_card(head, "good", "顯著 significant", [rule],
                                  ("保留在模型裡，並確認它的方向與大小合理", "keep it in the model and check its direction and size make sense")))
        else:
            out.append(hover_card(head, None, "不顯著 not significant", [rule],
                                  ("和雜訊分不開；先別當成有效因子，可考慮從模型移除或加重複再看",
                                   "indistinguishable from noise; do not treat it as an effect yet; consider dropping it or adding replicates")))
    return out


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
                    customdata=pareto_hover(part, t_crit), hovertemplate=card_template())
    fig.update_yaxes(categoryorder="array", categoryarray=list(tab["term"]))
    fig.update_layout(barmode="overlay")
    if t_crit:
        fig.add_vline(x=t_crit, line=dict(color=viz.INK_2, dash="dash", width=1))
        legend_line(fig, f"p = 0.05 threshold 門檻 (|t| = {t_crit:.2f})", viz.INK_2, dash="dash", width=1)
    fig = layout(fig, title, "|t|（標準化效應 standardised effect）", "模型項 model term", max(320, 26 * len(tab) + 190))
    fig.update_layout(margin=dict(t=125))  # three legend rows sit between the title and the plot
    return fig


def doe_contour_figure(x, y, z, show: str, xa: str, ya: str, runs: pd.DataFrame, recipe: dict, title: str) -> go.Figure:
    zarr = np.asarray(z, float)
    guide_d = ("<br>• D 越接近 1 越好：1 = 所有目標都達成，0 = 至少一個目標沒達成；≥ 0.8 好、0.6–0.8 有些取捨、< 0.6 取捨明顯"
               "<br><i>D closer to 1 is better: 1 = every goal met, 0 = at least one goal missed; ≥ 0.8 good, 0.6–0.8 some "
               "trade-off, < 0.6 a clear trade-off</i>") if show == "D" else ""
    fig = go.Figure(go.Contour(x=x, y=y, z=z, colorscale=viz.PLOTLY_SEQ, contours=dict(showlabels=True, labelfont=dict(size=10)),
                               colorbar=dict(title=show), hovertemplate=f"{xa} %{{x:.3g}}<br>{ya} %{{y:.3g}}<br>模型預測 predicted "
                                                                        f"{show} <b>%{{z:.3g}}</b><br>─────────<br><b>ℹ️ 模型預測 "
                                                                        f"model prediction</b><br>• 這是模型在這個設定的預測，不是實測值"
                                                                        f"<br><i>the model's prediction at this setting, not a measurement</i>"
                                                                        f"{guide_d}<extra></extra>"))
    fig.add_scatter(x=runs[xa], y=runs[ya], mode="markers", name="design runs 實驗點",
                    marker=dict(size=8, color=viz.SURFACE, line=dict(color=viz.INK, width=1.5)),
                    customdata=[hover_card([f"<b>design run 實驗點 #{i + 1}</b>", f"{xa} {a:.4g} · {ya} {b:.4g}"], None, "實測的實驗點 a real run",
                                           [("這是實驗設計裡真的跑過的點；等高線是用這些點擬合出來的模型",
                                             "this is a run that was actually made; the contours are a model fitted to such runs")])
                                for i, (a, b) in enumerate(zip(runs[xa], runs[ya]))], hovertemplate=card_template())
    ix, iy = int(np.abs(np.asarray(x) - recipe[xa]).argmin()), int(np.abs(np.asarray(y) - recipe[ya]).argmin())
    zr = float(zarr[iy, ix]) if zarr.ndim == 2 else float("nan")
    fig.add_scatter(x=[recipe[xa]], y=[recipe[ya]], mode="markers", name="suggested recipe 建議配方",
                    marker=dict(size=14, symbol="star", color=viz.SERIES[1], line=dict(color=viz.SURFACE, width=2)),
                    customdata=[hover_card([f"<b>suggested recipe 建議配方</b>", f"{xa} {recipe[xa]:.4g} · {ya} {recipe[ya]:.4g}",
                                            f"模型預測 predicted {show} {zr:.3g}"], None, "模型選的最佳點 the model's optimum",
                                           [("這是在實驗範圍內讓整體目標最好的設定（預測值）；要用確認實驗驗證，不能直接當成量產配方",
                                             "the setting that best meets the goals inside the tested range (a prediction); confirm it with "
                                             "runs before treating it as a production recipe")])],
                    hovertemplate=card_template())
    return layout(fig, title, xa, ya, 480)


# --------------------------------------------------------------------------- fab simulator
def yield_hover(lot_y: pd.DataFrame, med: float, mad: float) -> list[str]:
    alert = med - 3 * mad
    out = []
    for _, r in lot_y.iterrows():
        y = float(r["yield"])
        z = (y - med) / mad if mad > 0 else 0.0
        head = [f"<b>{r['lot_id']}</b>（lot index {int(r['lot_index'])}）", f"lot 平均良率 mean yield <b>{100 * y:.1f}%</b>",
                f"中位數 median {100 * med:.1f}% · 警戒線 alert {100 * alert:.1f}%", f"離中位數 {z:+.1f} 個穩健 σ（σ = 1.4826 × MAD）"]
        rule = (f"判斷：低於 median − 3 × 穩健 σ（{100 * alert:.1f}%）就是良率 excursion；這批 {100 * y:.1f}%",
                f"rule: below median − 3 × robust σ ({100 * alert:.1f}%) is a yield excursion; this lot is {100 * y:.1f}%")
        if y < alert:
            out.append(hover_card(head, "act", "良率 excursion", [rule],
                                  ("做 commonality：這批每一站走過的機台／chamber／時間，找共同點，再看 die map",
                                   "run commonality: the tool / chamber / time at every step this lot used, then open the die map")))
        elif z < -2:
            out.append(hover_card(head, "watch", "偏低 low", [(f"比中位數低 {abs(z):.1f} 個穩健 σ，還沒到警戒線", f"{abs(z):.1f} robust σ below the median, not yet at the alert line")]))
        else:
            out.append(hover_card(head, "good", "正常 normal", [(f"離中位數 {z:+.1f} 個穩健 σ，高於警戒線", f"{z:+.1f} robust σ from the median, above the alert line")]))
    return out


def yield_trend_figure(w: pd.DataFrame) -> go.Figure:
    lot_y = w.groupby(["lot_index", "lot_id"])["yield"].mean().reset_index()
    med = float(lot_y["yield"].median())
    mad = 1.4826 * float((lot_y["yield"] - med).abs().median()) or float(lot_y["yield"].std())
    fig = go.Figure(go.Scatter(x=lot_y["lot_index"], y=100 * lot_y["yield"], mode="lines+markers", name="lot mean yield 每批平均良率",
                               line=dict(color=viz.SERIES[0], width=1.5), marker=dict(size=5),
                               customdata=yield_hover(lot_y, med, mad), hovertemplate=card_template()))
    fig.add_hline(y=100 * med, line=dict(color=viz.INK_2, width=1))
    fig.add_hline(y=100 * (med - 3 * mad), line=dict(color=viz.STATUS["critical"], width=1, dash="dash"))
    legend_line(fig, f"median 中位數 = {100 * med:.1f}%", viz.INK_2, width=1)
    legend_line(fig, f"median − 3σ alert 警戒線 = {100 * (med - 3 * mad):.1f}%", viz.STATUS["critical"], dash="dash", width=1)
    return layout(fig, "每批平均良率（所有晶圓都有電測與良率）", "批次序號 lot index（D0001 = 0）", "每批平均良率 lot mean yield (%)", 340)


def cause_rules() -> dict:
    """code -> (parameter, unit, low, high) of the device window each parametric fail code stands for."""
    try:
        from metro_toolkit.datagen.fab import load_fab_config

        return {s["code"]: (s["parameter"], s["unit"], *s["window"]) for s in load_fab_config()["steps"] if s.get("window")}
    except Exception:  # noqa: BLE001 - never let a missing config break a chart
        return {}


def die_hover(codes_sel: np.ndarray, code: str, x, y, r_eff: float) -> list[str]:
    rules = cause_rules()
    out = []
    for xi, yi in zip(x, y):
        r = float(np.hypot(xi, yi))
        zone = "邊緣 edge" if r >= 0.85 * r_eff else "中心 centre" if r <= 0.3 * r_eff else "中間 mid"
        head = [f"<b>die</b> x {xi:.0f}, y {yi:.0f} mm", f"距中心 r = {r:.0f} mm（{zone}）"]
        if code == ".":
            out.append(hover_card(head, "good", "良品 pass", [("這顆晶粒通過所有元件窗口檢查，也沒有 killer defect",
                                                          "this die passed every device-window check and has no killer defect")]))
        elif code == "D":
            out.append(hover_card(head, "act", "缺陷失效 defect fail",
                                  [("判斷：這顆晶粒被 killer defect 打到（缺陷密度隨機＋群聚，在 sort 才知道）",
                                    "rule: a killer defect landed on this die (random plus clustered defect density, known at sort)"),
                                   ("看整片的空間圖樣：外圈環、中心群、刮痕、群聚各指向不同來源",
                                    "read the wafer-wide pattern: an edge ring, centre cluster, scratch or cluster each points to a different source")],
                                  ("缺陷類型要靠 review／SEM 才確定", "the defect type needs review / SEM to confirm")))
        elif code in rules:
            p, u, lo, hi = rules[code]
            out.append(hover_card(head, "act", f"{p} 超窗 out of window",
                                  [(f"判斷：這顆晶粒的局部 {p} 落在元件窗口 {lo:g}–{hi:g} {u} 之外（parametric fail）",
                                    f"rule: this die's local {p} fell outside its device window {lo:g}–{hi:g} {u} (a parametric fail)"),
                                   ("整片或整個 chamber 的平均值偏移，會讓很多晶粒同時超窗；只有一小塊超窗則看片內形狀",
                                    "a shifted wafer or chamber mean pushes many dies out of the window together; only a patch out of the window "
                                    "points to the within-wafer shape")],
                                  ("回到該站的 SPC 與晶圓圖，看是哪個 chamber、什麼時候開始", "go back to that step's SPC and wafer map: which chamber, since when")))
        else:
            out.append(hover_card(head, "act", CAUSE_NAME.get(code, code), []))
    return out


def die_map_figure(codes: np.ndarray, gx, gy, r_eff: float, title: str) -> go.Figure:
    fig = go.Figure()
    for c in CAUSE_NAME:
        sel = codes == c
        if not sel.any():
            continue
        fig.add_scatter(x=gx[sel], y=gy[sel], mode="markers", name=f"{CAUSE_NAME[c]} ({sel.sum()})",
                        marker=dict(symbol="square", size=9, color=CAUSE_COLOR[c]),
                        customdata=die_hover(sel, c, gx[sel], gy[sel], r_eff), hovertemplate=card_template())
    r = r_eff + 3
    fig.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r, line=dict(color=viz.AXIS))
    legend_line(fig, "wafer edge 晶圓邊緣", viz.AXIS)
    fig = layout(fig, title, "x (mm)", "y (mm)", 520)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


# --------------------------------------------------------------------------- inline defect inspection / cross-role requests
GROUP_COLOR = {"split": viz.SERIES[0], "baseline": viz.SERIES[1], "lot": viz.SERIES[0]}
GROUP_NAME = {"split": "split", "baseline": "baseline", "lot": "inspected count 檢查數量"}


def counts_hover(g: pd.DataFrame, all_counts: pd.DataFrame, maxout: int, grp: str) -> list[str]:
    med = float(all_counts["count"].median())
    out = []
    for wid, n in zip(g["wafer_id"], g["count"]):
        n = int(n)
        head = [f"<b>{wid}</b>" + (f" · {grp}" if grp not in ("lot",) else ""), f"檢查數量 inspected count <b>{n:,}</b>",
                f"中位數 median {med:,.0f} · maxout {maxout:,}"]
        if n >= maxout:
            out.append(hover_card(head, "act", "碰到 maxout", [(f"數量 = 機台上限 {maxout:,}：機台停止計數，真實數量未知，這個數字只是下限，不能和別片直接比較",
                                                              f"the count equals the tool's limit {maxout:,}: the tool stopped counting, the true number is unknown and this is only "
                                                              "a floor that cannot be compared directly")],
                                  ("先做 review 換算真缺陷，再決定要不要 hold", "convert to real defects with a review before deciding to hold")))
        elif n > 3 * max(med, 1):
            out.append(hover_card(head, "watch", "遠高於中位數", [(f"是中位數的 {n / max(med, 1):.1f} 倍（> 3 倍）：先看這片的 wafer map 與 review 再下結論",
                                                              f"{n / max(med, 1):.1f}× the median (> 3×): look at this wafer's map and review before concluding")]))
        else:
            out.append(hover_card(head, "good", "正常範圍", [(f"是中位數的 {n / max(med, 1):.1f} 倍（≤ 3 倍），未達 maxout",
                                                          f"{n / max(med, 1):.1f}× the median (≤ 3×) and below the maxout")]))
    return out


def defect_counts_figure(counts: pd.DataFrame, maxout: int, title: str) -> go.Figure:
    """One bar per wafer (colour = split / baseline group), red dashed maxout line, grey median line."""
    fig = go.Figure()
    for grp, g in counts.groupby("group", sort=False):
        fig.add_bar(x=g["wafer_id"], y=g["count"], name=GROUP_NAME.get(grp, grp),
                    marker=dict(color=GROUP_COLOR.get(grp, viz.SERIES[0]), cornerradius=4),
                    customdata=counts_hover(g, counts, maxout, str(grp)), hovertemplate=card_template())
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


def review_hover(sel: pd.Series, total: float, nuisance: str, nv_pct: float) -> list[str]:
    out = []
    for cls, n in sel.items():
        head = [f"<b>{cls}</b>", f"review 到 {int(n)} 顆 = <b>{100 * n / max(total, 1):.1f}%</b>（共 {int(total)} 顆）"]
        if cls == nuisance:
            rule = (f"判斷：non-visible（review 看不到真缺陷）≥ 50% 是 nuisance 為主、25–50% 偏高；這次 {nv_pct:.0f}%",
                    f"rule: non-visible (nothing real at review) of 50% or more means mostly nuisance, 25–50% is high; this lot {nv_pct:.0f}%")
            if nv_pct >= 50:
                out.append(hover_card(head, "act", "nuisance 為主", [rule], ("先用 review 結果調整檢查 recipe，再用數量判斷", "tune the inspection recipe from the review data before judging by counts")))
            elif nv_pct >= 25:
                out.append(hover_card(head, "watch", "nuisance 偏高", [rule], ("比較數量前先用 review 換算真缺陷數", "convert counts to real defects with the review before comparing")))
            else:
                out.append(hover_card(head, "good", "nuisance 低", [rule]))
        else:
            out.append(hover_card(head, None, "真缺陷類別 real defect class",
                                  [("這一類是 review 看得到的真缺陷；比例最高的類別優先做 SEM／找來源",
                                    "a real defect class seen at review; the largest class goes first to SEM / source tracing")]))
    return out


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
                    customdata=review_hover(s[sel], float(s.sum()), nuisance, float(pct.get(nuisance, 0))),
                    hovertemplate=card_template())
    layout(fig, f"Review 分類 · {int(s.sum())} defects reviewed", "缺陷類別 class", "佔 review 比例 share (%)")
    fig.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    fig.update_xaxes(categoryorder="array", categoryarray=list(pct.index))
    fig.update_yaxes(range=[0, pct.max() * 1.18])
    return fig


def adders_hover(t: pd.DataFrame) -> tuple[list[str], list[str]]:
    base = t[t["group"] == "baseline"]
    bp = float(base["previous"].mean()) or 1.0
    ba = float((base["current"] - base["previous"]).clip(lower=0).mean()) or 1.0
    prev, cur = [], []
    for _, r in t.iterrows():
        add = int(max(r["current"] - r["previous"], 0))
        split = r["group"] == "split"
        head = [f"<b>{r['wafer_id']}</b> · {r['group']}", f"前層 previous {int(r['previous']):,} → 本層 this layer {int(r['current']):,}",
                f"adder（本層 − 前層）= <b>{add:,}</b>"]
        pr, ar = r["previous"] / bp, add / ba
        rule_p = (f"判斷：前層數量是 baseline 平均（{bp:,.0f}）的 {pr:.1f} 倍；≥ 1.5 倍代表缺陷在前層就多（incoming）",
                  f"rule: the previous-layer count is {pr:.1f}× the baseline average ({bp:,.0f}); 1.5× or more means the defects were already "
                  "there at the previous layer (incoming)")
        rule_a = (f"判斷：adder 是 baseline 平均（{ba:,.0f}）的 {ar:.1f} 倍；≥ 1.5 倍代表這一層自己多加了缺陷",
                  f"rule: the adders are {ar:.1f}× the baseline average ({ba:,.0f}); 1.5× or more means this layer added defects itself")
        if split and pr >= 1.5:
            prev.append(hover_card(head, "act", "前層就偏多 incoming", [rule_p], ("往前層與前層機台追來源，不能怪這一層的 split", "trace upstream to the previous layer and its tools; do not blame this layer's split")))
        else:
            prev.append(hover_card(head, "good" if split else None, "前層正常 previous layer normal" if split else "baseline 前層 baseline previous", [rule_p]))
        if split and ar >= 1.5:
            cur.append(hover_card(head, "act", "本層新增偏多 added here", [rule_a], ("review／SEM 這片的 adder，和 baseline 比對缺陷類型", "review / SEM this wafer's adders and compare the defect types with baseline")))
        else:
            cur.append(hover_card(head, "good" if split else None, "本層新增正常 adders normal" if split else "baseline 本層 baseline this layer", [rule_a]))
    return prev, cur


def adders_figure(t: pd.DataFrame) -> go.Figure:
    """Per wafer: previous-layer count (light blue) and this-layer count (blue); split | baseline separated."""
    t = pd.concat([t[t["group"] == "split"], t[t["group"] == "baseline"]])
    fig = go.Figure()
    prev_cards, cur_cards = adders_hover(t)
    fig.add_bar(x=t["wafer_id"], y=t["previous"], name="previous layer 前層數量", marker=dict(color=viz.SEQ_BLUE[1], cornerradius=4),
                customdata=prev_cards, hovertemplate=card_template())
    fig.add_bar(x=t["wafer_id"], y=t["current"], name="this layer 本層數量", marker=dict(color=viz.SERIES[0], cornerradius=4),
                customdata=cur_cards, hovertemplate=card_template())
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


def bin_hover(t: pd.DataFrame, p: str, r: float, bin_name: str) -> list[str]:
    b1, b0 = np.polyfit(t[p], t["bin_loss"], 1)
    mu, sd = float(t[p].mean()), float(t[p].std(ddof=1)) or 1.0
    out = []
    for _, row in t.iterrows():
        resid = float(row["bin_loss"] - (b0 + b1 * row[p]))
        head = [f"<b>{row['wafer_id']}</b>", f"{p} <b>{row[p]:.4g}</b>（{(row[p] - mu) / sd:+.1f}σ of wafers）", f"{bin_name} 損失 loss {row['bin_loss']:.1f}%",
                f"離趨勢線 vs the line {resid:+.1f} pp"]
        rule = (f"判斷：這個圖的 r = {r:+.2f}；|r| ≥ 0.7 強相關、0.4–0.7 中度、< 0.4 弱／沒有（相關不等於因果）",
                f"rule: this panel's r = {r:+.2f}; |r| ≥ 0.7 strong, 0.4–0.7 moderate, < 0.4 weak or none (correlation is not causation)")
        if abs(r) >= 0.7:
            out.append(hover_card(head, "act", "強相關 strong link", [rule], ("交給 YE／PE，用 split／DOE 確認機制再談調整 target", "hand to YE / PE and confirm the mechanism with a split / DOE before any re-target")))
        elif abs(r) >= 0.4:
            out.append(hover_card(head, "watch", "中度相關 moderate link", [rule], ("可能是部分原因或巧合，加更多晶圓確認", "a partial cause or chance; add more wafers to confirm")))
        else:
            out.append(hover_card(head, "good", "沒有明顯關聯 no clear link", [rule], ("這個量測參數不能解釋這個 bin，轉向 defect review／FA", "this metrology parameter does not explain the bin; move to defect review / FA")))
    return out


def bin_corr_figure(t: pd.DataFrame, params: list[str], bin_name: str) -> go.Figure:
    """Small multiples: bin loss vs each inline parameter, one dot per wafer, grey dashed least-squares line."""
    from plotly.subplots import make_subplots

    rs = {p: float(np.corrcoef(t[p], t["bin_loss"])[0, 1]) for p in params}
    fig = make_subplots(rows=1, cols=len(params), shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=[f"{p} · r = {rs[p]:+.2f}" for p in params])
    for i, p in enumerate(params, start=1):
        fig.add_scatter(x=t[p], y=t["bin_loss"], mode="markers", name="wafer 晶圓", showlegend=i == 1,
                        marker=dict(size=9, color=viz.SERIES[0], line=dict(color=viz.SURFACE, width=2)),
                        customdata=bin_hover(t, p, rs[p], bin_name), hovertemplate=card_template(), row=1, col=i)
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


# --------------------------------------------------------------------------- tooltips for the fab-page and study-log charts
# (the figures are assembled in app.py; these build their per-point cards)
def tradeoff_hover(r: pd.Series, summ: pd.DataFrame) -> str:
    fa, dl = float(r["false_alarm_rate_pct"]), r["median_delay_wafers"]
    best_fa = float(summ["false_alarm_rate_pct"].min())
    delays = pd.to_numeric(summ["median_delay_wafers"], errors="coerce")
    best_dl = float(delays.min()) if delays.notna().any() else float("nan")
    quiet = abs(fa - best_fa) < 1e-9
    fast = pd.notna(dl) and np.isfinite(best_dl) and abs(float(dl) - best_dl) < 1e-9
    head = [f"<b>{r['setup']}</b>", f"誤警報 false alarms <b>{fa:.1f}%</b>", f"中位延遲 median delay <b>{dl}</b> 片 wafers",
            f"抓到 detected {r['detected']}/{r['observable']}"]
    how = ("怎麼讀：越靠左下越好 = 誤警報少又抓得快；延遲是第一片受影響的量測晶圓到第一次警報之間隔了幾片",
           "how to read: closer to the bottom-left is better = few false alarms and fast detection; delay counts the measured wafers "
           "between the first affected one and the first alarm")
    if quiet and fast:
        return hover_card(head, "good", "兩項都最好 best on both", [how, ("誤警報最少、延遲也最短", "fewest false alarms and the shortest delay")])
    if quiet or fast:
        what = ("誤警報最少，但不是最快", "fewest false alarms, but not the fastest") if quiet else ("最快，但不是誤警報最少", "the fastest, but not the quietest")
        return hover_card(head, "watch", "有取捨 a trade-off", [how, what])
    return hover_card(head, None, "沒有最佳項 neither best", [how])


def delay_hover(setup: str, event: str, delay, status: str) -> str:
    head = [f"<b>{setup}</b>", f"事件 event {event}"]
    how = ("延遲 = 第一片受影響的量測晶圓之後，又過了幾片量測晶圓才第一次警報（0 = 第一片就抓到）",
           "delay = how many measured wafers passed after the first affected measured wafer before the first alarm (0 = caught at the first)")
    if status == "missed":
        return hover_card(head, "act", "未抓到 missed", [how, ("整段事件期間這個設定都沒有警報", "this setup never alarmed during the whole event")],
                          ("換統計量（例如 1σ % 或 EWMA）、提高抽樣，或加量測機台分組", "try another statistic (1σ % or EWMA), sample more, or group by metrology tool"))
    if pd.isna(delay):
        return hover_card(head, None, "量測不到 not observable",
                          [("這個事件沒有反映在量測資料裡（例如只影響良率、或沒有被抽樣到的晶圓）",
                            "this event leaves no trace in the metrology data (for example it only affects yield or hit unsampled wafers)")])
    d = int(delay)
    head.append(f"延遲 delay <b>{d}</b> 片")
    if d == 0:
        return hover_card(head, "good", "第一片就抓到 caught at once", [how])
    return hover_card(head, "watch", "有延遲 delayed", [how, (f"晚了 {d} 片量測晶圓，這段時間內有問題的晶圓已經流到後面", f"{d} measured wafers late, so affected wafers moved on in the meantime")],
                      ("提高抽樣頻率或改用對小偏移更敏感的圖（EWMA／CUSUM）", "sample more often or use a chart more sensitive to small shifts (EWMA / CUSUM)"))


def confusion_hover(cm: pd.DataFrame, pct: pd.DataFrame) -> list[list[str]]:
    out = []
    for i, truth in enumerate(cm.index):
        row = []
        for j, pred in enumerate(cm.columns):
            n, p = int(cm.iloc[i, j]), float(pct.iloc[i, j])
            head = [f"真實 truth <b>{truth}</b> → 判為 predicted <b>{pred}</b>", f"{n} 片 wafers（佔這一列 {p:.0f}%）"]
            how = ("怎麼讀：列 = 真實圖樣、欄 = 分類器的判斷；對角線是判對的，其他格是判錯（佔該列的比例就是召回／漏判）",
                   "how to read: rows are the true pattern and columns the classifier's call; the diagonal is right, other cells are errors "
                   "(the share of the row is recall / miss rate)")
            if truth == pred:
                row.append(hover_card(head, "good" if n else None, "判對 correct", [how, (f"{truth} 的晶圓有 {p:.0f}% 被判對（召回）", f"{p:.0f}% of the {truth} wafers were called right (recall)")]))
            elif n:
                row.append(hover_card(head, "watch" if p < 20 else "act", "判錯 misclassified",
                                      [how, (f"{n} 片真實是 {truth} 卻被判成 {pred}", f"{n} wafers that are really {truth} were called {pred}")],
                                      ("看這些晶圓的缺陷圖與特徵；缺陷很少的晶圓特徵很吵，容易誤判", "look at these wafers' defect maps and features; wafers with few defects have noisy features")))
            else:
                row.append(hover_card(head, None, "沒有 none", [how]))
        out.append(row)
    return out


def driver_hover(drv: pd.DataFrame) -> list[str]:
    tot = float(drv["yield_loss_pct"].sum()) or 1.0
    out = []
    for rank, (_, r) in enumerate(drv.reset_index(drop=True).iterrows(), start=1):
        v = float(r["yield_loss_pct"])
        out.append(hover_card([f"<b>{r['cause']}</b>", f"平均良率損失 mean yield loss <b>{v:.2f}</b> pp", f"佔總損失 share of the loss {100 * v / tot:.0f}%（第 {rank} 名 #{rank}）"],
                              None, "真實的損失來源 the true loss driver",
                              [("這是模擬器知道的真答案：把這個原因移除後，平均良率會多幾個百分點",
                                "this is the simulator's known truth: how many percentage points of yield come back if this cause is removed"),
                               ("拿來比對 SHAP／相關性排名：簡單相關性只看量測過的晶圓平均，可能漏掉只在部分晶粒發生的問題",
                                "compare it with a SHAP / correlation ranking: simple correlation sees only the measured wafers' means and can miss problems "
                                "that hit only some dies")]))
    return out


def score_band(score: float) -> tuple[str, str, tuple[str, str]]:
    """Same thresholds the weak-spot mode uses: >= 85 mastered, < 50 needs work."""
    if score >= 85:
        return "good", "掌握 mastered", ("≥ 85 分：之後 🎯 會把難度調高一級", "85 or more: 🎯 weak-spot mode raises the level")
    if score < 50:
        return "act", "需要加強 needs work", ("< 50 分：之後 🎯 會多出這類題並降一級難度", "below 50: 🎯 weak-spot mode gives more of these at a lower level")
    return "watch", "進步中 improving", ("50–85 分：再做幾次，看是哪一題在失分", "50–85: do a few more and check which question loses the points")


def attempt_hover(h: pd.DataFrame) -> list[str]:
    out = []
    for i, r in h.reset_index(drop=True).iterrows():
        verdict, label, (zh, en) = score_band(float(r["score"]))
        out.append(hover_card([f"<b>第 {i + 1} 次 attempt #{i + 1}</b>", f"{r['case']}", f"分數 score <b>{r['score']:.0f} / 100</b>"], verdict, label, [(zh, en)]))
    return out


def rolling_hover(h: pd.DataFrame, win: int = 5) -> list[str]:
    roll = h["score"].rolling(win, min_periods=1).mean()
    out = []
    for i, v in enumerate(roll):
        verdict, label, (zh, en) = score_band(float(v))
        n = min(i + 1, win)
        out.append(hover_card([f"<b>最近 {n} 次平均 rolling mean of the last {n}</b>", f"<b>{v:.0f}</b> / 100（到第 {i + 1} 次）"], verdict, label,
                              [("滾動平均把單次的運氣平均掉，看整體走向", "the rolling mean averages out single-attempt luck to show the trend"), (zh, en)]))
    return out


def area_hover(dom: pd.DataFrame, names: dict) -> list[str]:
    out = []
    for _, r in dom.iterrows():
        verdict, label, (zh, en) = score_band(float(r["mean"]))
        out.append(hover_card([f"<b>{names.get(r['domain'], r['domain'])}</b>", f"平均分數 mean score <b>{r['mean']:.0f}</b>", f"練過 attempts {int(r['attempts'])}"],
                              verdict, label, [(zh, en)]))
    return out


# --------------------------------------------------------------------------- yield analysis, splits and weekly KPIs
ZONE_TXT = {"centre": "中心 centre", "mid": "中間 middle", "edge": "邊緣 edge"}


def _zone(x, y, r_max: float = 147.0) -> str:
    r = float(np.hypot(x, y)) / r_max
    return "centre" if r < 0.5 else "edge" if r > 0.8 else "mid"


def probe_die_hover(dies: pd.DataFrame, defects: pd.DataFrame, steps: list[str], bin_name: str) -> list[str]:
    by_die = {s: defects[defects.step == s].groupby("die").size() for s in steps}
    out = []
    for i, r in dies.iterrows():
        on = {s: int(by_die[s].get(i, 0)) for s in steps}
        head = [f"<b>die</b> x {r.x:.0f}, y {r.y:.0f} mm · {ZONE_TXT[_zone(r.x, r.y)]}",
                f"probe：<b>{bin_name if r.fail else 'pass 通過'}</b>",
                "inline：" + "，".join(f"{s} {n} 顆" for s, n in on.items())]
        seen = [s for s, n in on.items() if n]
        if r.fail and seen:
            out.append(hover_card(head, "act", "inline 看得到 seen inline",
                                  [(f"失效晶粒上有 {'、'.join(seen)} 的缺陷：算進該站的 capture rate",
                                    f"the failing die carries a defect from {', '.join(seen)}: it counts toward that step's capture rate")]))
        elif r.fail:
            out.append(hover_card(head, "watch", "inline 沒看到 not seen inline",
                                  [("失效但兩站都沒有缺陷：檢查站看不到（capture 缺口），或是其他失效機制",
                                    "failing, but neither step shows a defect here: a capture gap, or another fail mechanism")]))
        elif seen:
            out.append(hover_card(head, None, "non-killer",
                                  [("有缺陷但晶粒通過：這顆缺陷沒有致命，會拉低該站的 kill ratio",
                                    "a defect, but the die passes: it did not kill, and it lowers that step's kill ratio")]))
        else:
            out.append(hover_card(head, "good", "通過、無缺陷 pass, clean", []))
    return out


def probe_overlay_figure(dies: pd.DataFrame, defects: pd.DataFrame, steps: list[str], bin_name: str, title: str = "") -> go.Figure:
    """Probe fail map (red = fail dies) with each inline step's defects on top (open circle / cross)."""
    cards = probe_die_hover(dies, defects, steps, bin_name)
    fig = go.Figure()
    for fail, name, color in ((False, "pass 通過", viz.GRID), (True, f"{bin_name} 失效", viz.STATUS["critical"])):
        sel = (dies["fail"] == fail).to_numpy()
        fig.add_scatter(x=dies.x[sel], y=dies.y[sel], mode="markers", name=f"{name} ({int(sel.sum())})",
                        marker=dict(symbol="square", size=11, color=color, opacity=0.85 if fail else 1),
                        customdata=[c for c, s in zip(cards, sel) if s], hovertemplate=card_template())
    fail = dies["fail"].to_numpy()
    for s, sym, color in zip(steps, ("circle-open", "x-thin-open"), (viz.SERIES[0], viz.SERIES[1])):
        d = defects[defects.step == s]
        on = fail[d["die"].to_numpy()]
        cards_d = [hover_card([f"<b>{s}</b> defect", f"x {x:.1f}, y {y:.1f} mm"], "act" if o else None,
                              "落在失效晶粒 on a fail die" if o else "落在良品晶粒 on a passing die",
                              [("可能是 killer：和 probe 失效對上" if o else "沒有造成失效（或不是致命缺陷）",
                                "a candidate killer: it matches a probe fail" if o else "it did not cause a fail (not a killer here)")])
                   for x, y, o in zip(d.x, d.y, on)]
        fig.add_scatter(x=d.x, y=d.y, mode="markers", name=f"{s} defects ({len(d)})",
                        marker=dict(symbol=sym, size=8, color=color, line=dict(width=2, color=color)),
                        customdata=cards_d, hovertemplate=card_template())
    fig.add_shape(type="circle", x0=-150, y0=-150, x1=150, y1=150, line=dict(color=viz.AXIS))
    legend_line(fig, "wafer edge 晶圓邊緣", viz.AXIS)
    fig = layout(fig, title or f"{bin_name} 失效圖 + inline 缺陷", "x (mm)", "y (mm)", 560)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def capture_kill_hover(table: pd.DataFrame, monitor: str, what: str) -> list[str]:
    out = []
    for _, r in table.iterrows():
        tag = "（監控站 monitor）" if r["step"] == monitor else ""
        head = [f"<b>{r['step']}</b>{tag}", f"capture rate <b>{r['capture']:.0f}%</b> · kill ratio <b>{r['kill_ratio']:.0f}%</b>",
                f"{int(r['defects'])} 顆缺陷，{int(r['on fail dies'])} 顆落在失效晶粒"]
        if what == "capture":
            rule = (f"判斷：capture rate = 失效晶粒中有這站缺陷的比例；≥ 60% 看得到、30–60% 部分、< 30% 看不到；這站 {r['capture']:.0f}%",
                    f"rule: capture rate = share of failing dies carrying a defect from this step; 60% or more sees them, 30–60% "
                    f"partly, below 30% is blind; this step {r['capture']:.0f}%")
            v = "good" if r["capture"] >= 60 else "watch" if r["capture"] >= 30 else "act"
            label = {"good": "看得到 sees the killers", "watch": "只看到部分 partial", "act": "看不到 blind"}[v]
            nxt = (("這站的 SPC 不能證明沒問題：監控要移到看得到的那一站", "a clean SPC here proves nothing: monitor at the step that sees them")
                   if v == "act" and r["step"] == monitor else None)
            out.append(hover_card(head, v, label, [rule], nxt))
        else:
            rule = (f"判斷：kill ratio = 落在失效晶粒的缺陷比例，扣掉隨機落上的機率 {r['chance']:.1f}%；越高代表這站抓到的越是 killer",
                    f"rule: kill ratio = share of defects landing on failing dies, minus the {r['chance']:.1f}% chance of landing "
                    "there at random; higher means this step catches more killers")
            out.append(hover_card(head, None, "kill ratio", [rule]))
    return out


def capture_kill_figure(table: pd.DataFrame, monitor: str) -> go.Figure:
    names = [f"{s} (monitor 監控站)" if s == monitor else s for s in table["step"]]
    fig = go.Figure()
    fig.add_bar(x=names, y=table["capture"], name="capture rate 抓到的失效比例", marker=dict(color=viz.SERIES[0], cornerradius=4),
                text=[f"{v:.0f}%" for v in table["capture"]], textposition="outside",
                customdata=capture_kill_hover(table, monitor, "capture"), hovertemplate=card_template())
    fig.add_bar(x=names, y=table["kill_ratio"], name="kill ratio 致命比例", marker=dict(color=viz.SERIES[1], cornerradius=4),
                text=[f"{v:.0f}%" for v in table["kill_ratio"]], textposition="outside",
                customdata=capture_kill_hover(table, monitor, "kill"), hovertemplate=card_template())
    for y_, dash in ((60, "dot"), (30, "dash")):
        fig.add_hline(y=y_, line=dict(color=viz.MUTED, dash=dash, width=1.2))
    legend_line(fig, "capture 60%（看得到 sees them）", viz.MUTED, "dot")
    legend_line(fig, "capture 30%（以下看不到 blind below）", viz.MUTED, "dash")
    layout(fig, "各檢查站的 capture rate 與 kill ratio", "inline 檢查站 inspection step", "比例 share (%)", 380)
    fig.update_layout(barmode="group", bargap=0.35, legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    fig.update_yaxes(range=[0, 108])
    return fig


SPLIT_COLOR = {"POR": viz.SERIES[0], "B-low": viz.SERIES[1], "B-high": viz.SERIES[2]}


def split_wafer_hover(t: pd.DataFrame) -> list[str]:
    out = []
    for _, r in t.iterrows():
        head = [f"<b>{r['wafer_id']}</b>（slot {int(r['slot'])}）", f"良率 yield <b>{r['yield']:.1f}%</b>",
                f"計畫 planned {r['planned']} · run log {r['actual']} · FEM {r['fem']}"]
        if r["planned"] != r["actual"]:
            out.append(hover_card(head, "act", "沒照計畫跑 not run as planned",
                                  [(f"計畫是 {r['planned']}，run log 卻是 {r['actual']}：這片不能代表 {r['planned']}",
                                    f"planned {r['planned']} but the run log shows {r['actual']}: this wafer cannot stand for {r['planned']}")],
                                  ("依實際 recipe 分組；缺的那組要補跑", "group by the actual recipe; rerun the missing group")))
        elif r["fem"] != "nominal":
            out.append(hover_card(head, "act", "被另一個實驗影響 confounded",
                                  [("這片同時跑了 litho FEM 的偏離條件：良率差異可能來自 FEM，不是 split 條件",
                                    "this wafer also carried an off-nominal litho FEM cell: its yield may reflect the FEM, not the split")],
                                  ("比較 split 時排除這片（或兩組平衡）", "leave it out of the split comparison (or balance the groups)")))
        else:
            out.append(hover_card(head, "good", "乾淨 clean", [("照計畫跑、FEM 標準條件：可以用來比較", "ran as planned at nominal FEM: usable for the comparison")]))
    return out


def split_check_figure(t: pd.DataFrame, title: str = "") -> go.Figure:
    """Yield per wafer: colour = recipe actually run, circle = nominal FEM, x = off-nominal FEM, red ring = not run as planned."""
    cards = split_wafer_hover(t)
    fig = go.Figure()
    for g, color in SPLIT_COLOR.items():
        for fem, sym in (("nominal", "circle"), ("off", "x")):
            sel = ((t["actual"] == g) & (t["fem"] == fem)).to_numpy()
            if not sel.any():
                continue
            mis = (t["planned"] != t["actual"]).to_numpy()[sel]
            fig.add_scatter(x=t["slot"][sel], y=t["yield"][sel], mode="markers",
                            name=f"{g}" + (" · FEM off-nominal 偏離條件" if fem == "off" else ""),
                            marker=dict(symbol=sym, size=12, color=color,
                                        line=dict(width=[3 if m else 1 for m in mis],
                                                  color=[viz.STATUS["critical"] if m else viz.SURFACE for m in mis])),
                            customdata=[c for c, s in zip(cards, sel) if s], hovertemplate=card_template())
    if (t["planned"] != t["actual"]).any():
        legend_marker(fig, "紅框 = 沒照計畫跑 red ring = not run as planned", viz.SURFACE, "circle", 12,
                      dict(width=3, color=viz.STATUS["critical"]))
    for g, color in SPLIT_COLOR.items():
        m = t.loc[t["planned"] == g, "yield"].mean()
        if np.isfinite(m):
            fig.add_hline(y=m, line=dict(color=color, dash="dot", width=1))
    legend_line(fig, "各計畫組平均 planned-group mean", viz.MUTED, "dot", 1)
    layout(fig, title or "每片良率：顏色 = 實際 recipe，形狀 = FEM 條件", "slot", "良率 yield (%)", 420)
    fig.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0), margin=dict(t=110))
    return fig


def zone_hover(zt: pd.DataFrame, grp: str) -> list[str]:
    out = []
    for _, r in zt.iterrows():
        head = [f"<b>{ZONE_TXT[r['zone']]}</b> · {grp}", f"晶粒比例 die share {r['share']:.0f}%",
                f"POR {r['por']:.1f}% · B {r['b']:.1f}% · Δ <b>{r['delta']:+.1f} pp</b> ± {2 * r['se']:.1f}（2 SE）",
                f"加權貢獻 weighted {r['weighted']:+.2f} pp"]
        rule = ("判斷：|Δ| 超過 2 個標準誤才算真的差異；加權貢獻 = Δ × 晶粒比例，三區相加就是整片淨效果",
                "rule: a difference is real only beyond 2 standard errors; weighted = Δ × die share, and the three add up to the "
                "whole-wafer net")
        if r["delta"] > 2 * r["se"]:
            out.append(hover_card(head, "good", "B 較好 B better", [rule]))
        elif r["delta"] < -2 * r["se"]:
            out.append(hover_card(head, "act", "B 較差 B worse", [rule], ("轉換時要追蹤這一區，或先修好再轉", "follow this zone up when converting, or fix it first")))
        else:
            out.append(hover_card(head, None, "差異在雜訊內 within noise", [rule]))
    return out


def zone_yield_figure(zt: pd.DataFrame, net: float, net_se: float, title: str = "") -> go.Figure:
    labels = [f"{ZONE_TXT[z]}<br>{s:.0f}% dies" for z, s in zip(zt["zone"], zt["share"])]
    fig = go.Figure()
    for col, name, color in (("por", "POR", viz.SERIES[0]), ("b", "B", viz.SERIES[1])):
        fig.add_bar(x=labels, y=zt[col], name=name, marker=dict(color=color, cornerradius=4),
                    error_y=dict(type="data", array=list(zt["se"]), color=viz.INK_2, thickness=1.2) if col == "b" else None,
                    customdata=zone_hover(zt, name), hovertemplate=card_template())
    for x, d in zip(labels, zt["delta"]):
        fig.add_annotation(x=x, y=float(zt[["por", "b"]].max().max()) + 3, text=f"Δ {d:+.1f} pp", showarrow=False,
                           font=dict(color=viz.STATUS["critical"] if d < 0 else viz.INK))
    legend_line(fig, "誤差線 = ± 1 SE of Δ", viz.INK_2, width=1)
    lo = float(zt[["por", "b"]].min().min())
    layout(fig, title or f"各區良率 · 加權淨效果 net {net:+.2f} ± {net_se:.2f} pp", "區域 zone（晶粒比例 die share）", "良率 yield (%)", 400)
    fig.update_layout(barmode="group", bargap=0.3, legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
    fig.update_yaxes(range=[lo - 6, float(zt[["por", "b"]].max().max()) + 6])
    return fig


def dly_hover(w: pd.DataFrame, goal: float) -> list[str]:
    out = []
    for _, r in w.iterrows():
        head = [f"<b>{r['week']}</b>（probe week）", f"DLY <b>{r['dly']:.1f}%</b> · 目標 goal {goal:g}%"]
        if abs(r["dly_ex"] - r["dly"]) >= 0.3:
            head.append(f"不含標記晶圓 without flagged wafers {r['dly_ex']:.1f}%")
        rule = (f"判斷：低於目標 {goal:g}% 是紅燈；差距若只來自少數晶圓，要同時報告含與不含的數字",
                f"rule: below the {goal:g}% goal is red; if a few wafers make the gap, report the number with and without them")
        if r["dly"] < goal:
            out.append(hover_card(head, "act", "紅燈 red", [rule], ("先分辨：少數晶圓？隨機還是系統性？probe 延遲？", "sort it out first: a few wafers? random or systematic? probe lag?")))
        elif r["dly"] < goal + 0.5:
            out.append(hover_card(head, "watch", "接近目標 near goal", [rule]))
        else:
            out.append(hover_card(head, "good", "綠燈 green", [rule]))
    return out


def loss_hover(w: pd.DataFrame, col: str) -> list[str]:
    base = float(w[col].iloc[:4].mean())
    name = {"random_loss": ("隨機缺陷損失", "random-defect loss"), "sys_loss": ("系統性損失", "systematic loss")}[col]
    out = []
    for _, r in w.iterrows():
        d = float(r[col] - base)
        head = [f"<b>{r['week']}</b> · {name[0]} {name[1]}", f"<b>{r[col]:.2f} pp</b>（基準 baseline {base:.2f}，{d:+.2f}）"]
        rule = ("判斷：比前四週基準多 ≥ 0.8 pp 就是這一類損失在變大；隨機看 inline 密度，系統性看各層 opens／shorts",
                "rule: 0.8 pp or more above the first-four-week baseline means this kind of loss is growing; random follows the "
                "inline density, systematic shows in the per-level opens / shorts")
        v = "act" if d >= 0.8 else "watch" if d >= 0.4 else "good"
        out.append(hover_card(head, v, {"act": "變大 growing", "watch": "略增 slightly up", "good": "正常 normal"}[v], [rule]))
    return out


def density_hover(w: pd.DataFrame, fix_week: str | None) -> list[str]:
    base = float(w["density"].iloc[:4].mean())
    out = []
    for _, r in w.iterrows():
        k = r["density"] / base
        head = [f"<b>{r['week']}</b>（process week 製程週）", f"inline killer 密度 density <b>{r['density']:.3f}/cm²</b>（基準 {base:.3f}，{k:.1f}×）"]
        if fix_week and r["week"] == fix_week:
            head.append(f"修正週 fix week：{fix_week}")
        rule = ("判斷：> 1.8 × 基準是缺陷事件；這是領先指標，這週製造的 lot 約 3 週後才到 probe",
                "rule: above 1.8× baseline is a defect event; this is the leading indicator: lots processed this week reach "
                "probe about 3 weeks later")
        v = "act" if k > 1.8 else "watch" if k > 1.3 else "good"
        out.append(hover_card(head, v, {"act": "缺陷事件 event", "watch": "偏高 high", "good": "正常 normal"}[v], [rule]))
    return out


def dly_trend_figure(w: pd.DataFrame, goal: float, fix_week: str | None = None) -> go.Figure:
    """Row 1: DLY by probe week vs goal (red / green markers; dashed = without flagged wafers). Row 2: loss split into
    random and systematic. Row 3: inline killer density by process week (the leading indicator)."""
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.42, 0.29, 0.29],
                        subplot_titles=["DLY（probe 週）vs 目標", "損失拆解 loss split（probe 週）", "inline killer 密度（製程週）"])
    col = [viz.STATUS["critical"] if d < goal else viz.STATUS["good"] for d in w["dly"]]
    fig.add_scatter(x=w["week"], y=w["dly"], mode="lines+markers", name="DLY 所有晶圓 all wafers", line=dict(color=viz.INK_2, width=1.5),
                    marker=dict(size=10, color=col), customdata=dly_hover(w, goal), hovertemplate=card_template(), row=1, col=1)
    if (w["dly_ex"] - w["dly"]).abs().max() >= 0.3:
        fig.add_scatter(x=w["week"], y=w["dly_ex"], mode="lines", name="DLY 不含標記晶圓 without flagged wafers",
                        line=dict(color=viz.SERIES[0], dash="dash", width=1.5), hoverinfo="skip", row=1, col=1)
    fig.add_hline(y=goal, line=dict(color=viz.STATUS["critical"], dash="dash", width=1.2), row=1, col=1)
    legend_line(fig, f"goal 目標 = {goal:g}%", viz.STATUS["critical"], "dash")
    legend_marker(fig, "綠燈 green（≥ goal）", viz.STATUS["good"], "circle", 10)
    legend_marker(fig, "紅燈 red（< goal）", viz.STATUS["critical"], "circle", 10)
    for c, name, color in (("random_loss", "隨機缺陷損失 random loss", viz.SERIES[0]), ("sys_loss", "系統性損失 systematic loss", viz.SERIES[1])):
        fig.add_bar(x=w["week"], y=w[c], name=name, marker=dict(color=color), customdata=loss_hover(w, c),
                    hovertemplate=card_template(), row=2, col=1)
    base = float(w["density"].iloc[:4].mean())
    fig.add_scatter(x=w["week"], y=w["density"], mode="lines+markers", name="inline killer density 密度 (/cm²)",
                    line=dict(color=viz.SERIES[2], width=1.5), marker=dict(size=7), customdata=density_hover(w, fix_week),
                    hovertemplate=card_template(), row=3, col=1)
    fig.add_hline(y=1.8 * base, line=dict(color=viz.MUTED, dash="dot", width=1), row=3, col=1)
    legend_line(fig, "1.8 × 基準 baseline（事件線 event line）", viz.MUTED, "dot")
    if fix_week:
        fig.add_vline(x=fix_week, line=dict(color=viz.SERIES[2], dash="dash", width=1.5))
        legend_line(fig, f"修正 fix（{fix_week}）", viz.SERIES[2], "dash")
    layout(fig, "每週 defect-limited yield（DLY）", "", "", 680)
    fig.update_layout(barmode="stack", legend=dict(orientation="h", y=-0.08, yanchor="top", x=0), margin=dict(b=120))
    fig.update_yaxes(title_text="DLY (%)", row=1, col=1)
    fig.update_yaxes(title_text="損失 loss (pp)", row=2, col=1)
    fig.update_yaxes(title_text="密度 (/cm²)", row=3, col=1)
    fig.update_xaxes(title_text="週 week", row=3, col=1)
    return fig


def level_hover(g: pd.DataFrame, base: float, level: str, mode: str) -> list[str]:
    out = []
    for _, r in g.iterrows():
        d = base - float(r["pass_pct"])
        head = [f"<b>{level} {mode}</b> · {r['week']}", f"通過率 passing <b>{r['pass_pct']:.2f}%</b>（基準 baseline {base:.2f}%，−{max(d, 0):.2f} pp）"]
        rule = ("判斷：比前四週基準低 ≥ 1 pp 是系統性問題、0.5–1 pp 要追一週；只有一層掉 → 找該層的 module",
                "rule: 1 pp or more below the first-four-week baseline is a systematic problem, 0.5–1 pp needs another week; "
                "only one level dropping → look at that level's module")
        v = "act" if d >= 1.0 else "watch" if d >= 0.5 else "good"
        out.append(hover_card(head, v, {"act": "系統性下降 systematic drop", "watch": "略降 slightly down", "good": "正常 normal"}[v], [rule]))
    return out


def level_pass_figure(lv: pd.DataFrame) -> go.Figure:
    from plotly.subplots import make_subplots

    weeks = list(dict.fromkeys(lv["week"]))
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.05,
                        subplot_titles=["opens 斷路 通過率", "shorts 短路 通過率"])
    for j, mode in enumerate(("opens", "shorts"), start=1):
        for i, (level, g) in enumerate(lv[lv["mode"] == mode].groupby("level", sort=True)):
            base = float(g[g["week"].isin(weeks[:4])]["pass_pct"].mean())
            fig.add_scatter(x=g["week"], y=g["pass_pct"], mode="lines+markers", name=level, legendgroup=level, showlegend=j == 1,
                            line=dict(color=viz.SERIES[i], width=1.5), marker=dict(size=6),
                            customdata=level_hover(g, base, level, mode), hovertemplate=card_template(), row=1, col=j)
        fig.update_xaxes(title_text="probe 週 week", row=1, col=j)
    layout(fig, "各金屬層 opens／shorts 通過率", "", "通過率 passing (%)", 380)
    fig.update_yaxes(title_text="", row=1, col=2)
    fig.update_layout(legend=dict(orientation="h", y=1.12, yanchor="bottom", x=0), margin=dict(t=110))
    return fig


def layer_repeat_figure(d1: pd.DataFrame, d2: pd.DataFrame, radius: float, layers: list[str], title: str = "") -> go.Figure:
    """This layer's defects (blue circles) and the next layer's (orange crosses); hover says whether each one repeats."""
    def nearest(a, b):
        if not len(a) or not len(b):
            return np.full(len(a), np.inf)
        return np.hypot(a.x.to_numpy()[:, None] - b.x.to_numpy()[None, :], a.y.to_numpy()[:, None] - b.y.to_numpy()[None, :]).min(axis=1)

    n1, n2 = nearest(d1, d2), nearest(d2, d1)
    rule = (f"判斷：下一層 ±{radius} mm 內有缺陷 = 同位置再出現；cluster 一半以上再出現 → 真的實體缺陷",
            f"rule: a defect within ±{radius} mm at the other layer = it repeats; more than half of a cluster repeating → a real "
            "physical defect")
    c1 = [hover_card([f"<b>{layers[0]}</b> defect" + (" · cluster" if c else ""), f"x {x:.1f}, y {y:.1f} mm",
                      f"下一層最近的缺陷 nearest next-layer defect {d:.2f} mm" if np.isfinite(d) else "下一層沒有缺陷"],
                     "act" if d <= radius else None, "再出現 repeats" if d <= radius else "沒再出現 does not repeat", [rule])
          for x, y, c, d in zip(d1.x, d1.y, d1["cluster"], n1)]
    c2 = [hover_card([f"<b>{layers[1]}</b> defect", f"x {x:.1f}, y {y:.1f} mm", f"本層最近的缺陷 nearest earlier defect {d:.2f} mm"],
                     "act" if d <= radius else None, "同位置 same place as before" if d <= radius else "這層新出現 new at this layer", [rule])
          for x, y, d in zip(d2.x, d2.y, n2)]
    fig = go.Figure()
    fig.add_scatter(x=d1.x, y=d1.y, mode="markers", name=f"{layers[0]} ({len(d1)})", customdata=c1, hovertemplate=card_template(),
                    marker=dict(symbol="circle-open", size=9, color=viz.SERIES[0], line=dict(width=2)))
    fig.add_scatter(x=d2.x, y=d2.y, mode="markers", name=f"{layers[1]} ({len(d2)})", customdata=c2, hovertemplate=card_template(),
                    marker=dict(symbol="x-thin-open", size=8, color=viz.SERIES[1], line=dict(width=2, color=viz.SERIES[1])))
    fig.add_shape(type="circle", x0=-150, y0=-150, x1=150, y1=150, line=dict(color=viz.AXIS))
    legend_line(fig, "wafer edge 晶圓邊緣", viz.AXIS)
    fig = layout(fig, title or "本層 vs 下一層缺陷位置", "x (mm)", "y (mm)", 540)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig
