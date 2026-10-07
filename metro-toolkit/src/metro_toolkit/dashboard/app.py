"""metro-toolkit Streamlit dashboard (thin-film first).

Run from the metro-toolkit folder:
    streamlit run src/metro_toolkit/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # allow running without pip install

from metro_toolkit import viz  # noqa: E402
from metro_toolkit.analysis import process_capability, spc_by_group, wafer_summary  # noqa: E402
from metro_toolkit.config import data_dir, load_stack, load_yaml, wavelengths  # noqa: E402
from metro_toolkit.datagen import ThicknessSimConfig, grr_study, matching_study, simulate_thickness  # noqa: E402
from metro_toolkit.metrology.thinfilm import (  # noqa: E402
    ellipsometry,
    fit,
    reflectance,
    simulate_reflectometry,
    simulate_se,
)
from metro_toolkit.metrology.thinfilm.studies import thickness_n_correlation, thickness_sensitivity  # noqa: E402
from metro_toolkit.msa import fleet_matching, gauge_rr  # noqa: E402
from metro_toolkit.schema import validate  # noqa: E402
from metro_toolkit.wafer import interpolate_map, radial_profile, uniformity_metrics, zernike_decompose  # noqa: E402

st.set_page_config(page_title="metro-toolkit", layout="wide")


def layout(fig: go.Figure, title: str, xlab: str, ylab: str, height: int = 380) -> go.Figure:
    fig.update_layout(**viz.PLOTLY_LAYOUT, title=dict(text=title, x=0, y=0.97, yanchor="top", yref="container", font=dict(size=14)), height=height)
    fig.update_xaxes(title=xlab)
    fig.update_yaxes(title=ylab)
    return fig


@st.cache_data
def films_cfg():
    return load_yaml("films.yaml")


@st.cache_data
def sample_data() -> pd.DataFrame:
    path = data_dir() / "thickness_sites.csv"
    if path.exists():
        df = pd.read_csv(path)
    else:
        df, _ = simulate_thickness(ThicknessSimConfig())
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_data() -> pd.DataFrame | None:
    up = st.sidebar.file_uploader("Measurement CSV (standard schema)", type="csv")
    if up is None:
        st.sidebar.caption("Using synthetic sample data.")
        return sample_data()
    df = pd.read_csv(up)
    problems = validate(df)
    if problems:
        st.error("Data problems:\n- " + "\n- ".join(problems))
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


# --------------------------------------------------------------------------- #
# Pages                                                                       #
# --------------------------------------------------------------------------- #


def page_stack():
    st.header("Film stack & fit explorer")
    cfg = films_cfg()
    name = st.selectbox("Stack (config/films.yaml)", list(cfg["stacks"]))
    stack, recipe = load_stack(name, cfg)
    st.caption(recipe.get("description", ""))
    wl = wavelengths(cfg)

    cols = st.columns(len(stack.layers) + 1)
    true_t = []
    for i, layer in enumerate(stack.layers):
        t0 = layer.thickness_nm
        true_t.append(cols[i].number_input(f"True L{i} {layer.name} (nm)", 0.0, 2000.0, float(t0), step=max(t0 / 50, 0.05),
                                           format="%.2f"))
    technique = cols[-1].radio("Technique", ["reflectometry", "se"], index=0 if recipe.get("technique") != "se" else 1)
    truth = stack.copy_with(true_t)

    c1, c2 = st.columns(2)
    if technique == "reflectometry":
        noise = c1.slider("Reflectance noise (1σ)", 0.0, 0.01, 0.002, 0.0005, format="%.4f")
        meas = simulate_reflectometry(truth, wl, noise=noise, rng=1)
    else:
        noise = c1.slider("Ψ noise (deg, 1σ); Δ noise = 2x", 0.0, 0.2, 0.02, 0.01)
        angles = recipe.get("angles_deg", [65, 70, 75])
        meas = simulate_se(truth, wl, angles, noise, 2 * noise, rng=1)
    float_n = c2.checkbox("Also float n of the top layer (Cauchy A)", value=False,
                          help="Only possible if the top layer uses a Cauchy model (Al2O3, HfO2, ZrO2).")

    params = list(recipe["fit_params"])
    if float_n and hasattr(stack.layers[0].material, "A"):
        from metro_toolkit.metrology.thinfilm import FitParameter

        a0 = stack.layers[0].material.A
        params.append(FitParameter(0, "A", (a0 - 0.3, a0 + 0.3)))
    elif float_n:
        st.warning("Top layer is not a Cauchy material; n is not floated.")

    with st.spinner("Fitting..."):
        res = fit(stack, meas, params)

    fig = go.Figure()
    if technique == "reflectometry":
        fig.add_scatter(x=wl, y=meas.data["R"], mode="markers", name="measured", marker=dict(size=4, color=viz.SERIES[0]))
        fig.add_scatter(x=wl, y=reflectance(res.stack, wl), mode="lines", name="model fit", line=dict(color=viz.SERIES[1], width=2))
        st.plotly_chart(layout(fig, "Reflectance: measured vs fitted model", "wavelength (nm)", "R"), width="stretch")
    else:
        a = float(angles[len(angles) // 2])
        psi_m, delta_m = meas.data[a]
        psi_f, delta_f = ellipsometry(res.stack, wl, a)
        g1, g2 = st.columns(2)
        f1 = go.Figure([go.Scatter(x=wl, y=psi_m, mode="markers", name="measured", marker=dict(size=4, color=viz.SERIES[0])),
                        go.Scatter(x=wl, y=psi_f, mode="lines", name="fit", line=dict(color=viz.SERIES[1]))])
        f2 = go.Figure([go.Scatter(x=wl, y=delta_m, mode="markers", name="measured", marker=dict(size=4, color=viz.SERIES[0])),
                        go.Scatter(x=wl, y=delta_f, mode="lines", name="fit", line=dict(color=viz.SERIES[1]))])
        g1.plotly_chart(layout(f1, f"Ψ at {a:.0f}°", "wavelength (nm)", "Ψ (deg)"), width="stretch")
        g2.plotly_chart(layout(f2, f"Δ at {a:.0f}°", "wavelength (nm)", "Δ (deg)"), width="stretch")

    rows = []
    for lab in res.labels:
        layer = int(lab[1:].split(".")[0])
        tgt = lab.split(".")[1]
        truth_val = true_t[layer] if tgt == "thickness" else getattr(stack.layers[layer].material, tgt)
        rows.append({"parameter": lab, "true": truth_val, "fitted": res.values[lab], "± 1σ": res.stderr[lab],
                     "error": res.values[lab] - truth_val})
    m1, m2 = st.columns([2, 1])
    m1.dataframe(pd.DataFrame(rows).style.format(precision=4), hide_index=True, width="stretch")
    m2.metric("reduced χ²", f"{res.chi2_red:.2f}")
    if len(res.labels) > 1:
        m2.write("Parameter correlation")
        m2.dataframe(pd.DataFrame(res.correlation, index=res.labels, columns=res.labels).style.format(precision=3))
    fixed_changed = [i for i, l in enumerate(stack.layers)
                     if i not in {p.layer for p in params} and abs(true_t[i] - l.thickness_nm) > 1e-9]
    if fixed_changed:
        st.info(f"Layer(s) {fixed_changed} differ from the recipe's fixed value: watch the floated-layer error "
                "while χ² stays low. Fit statistics do not reveal a wrong fixed layer.")


def page_wafer(df):
    st.header("Wafer map & uniformity")
    if df is None:
        return
    param = st.selectbox("Parameter", sorted(df.parameter.unique()))
    sub = df[df.parameter == param]
    wafers = wafer_summary(sub)
    wafer = st.selectbox("Wafer (worst NU first)", wafers.sort_values("nu_1sigma_pct", ascending=False).wafer_id)
    w = sub[sub.wafer_id == wafer]
    um = uniformity_metrics(w.value)
    r_eff = float(np.hypot(w.x, w.y).max())
    k = st.columns(5)
    k[0].metric("mean", f"{um['mean']:.3f}")
    k[1].metric("1σ NU", f"{um['nu_1sigma_pct']:.3f} %")
    k[2].metric("range", f"{um['range']:.3f}")
    k[3].metric("(max−min)/2·mean", f"{um['half_range_pct']:.3f} %")
    k[4].metric("sites", um["n_sites"])

    mode = st.radio("Colour scale", ["absolute (sequential)", "deviation from mean (diverging)"], horizontal=True)
    X, Y, Z = interpolate_map(w.x, w.y, w.value, radius_mm=r_eff, grid=101)
    if mode.startswith("absolute"):
        zz, cs, zmid = Z, viz.PLOTLY_SEQ, None
    else:
        zz, cs, zmid = Z - um["mean"], viz.PLOTLY_DIV, 0.0
    fig = go.Figure(go.Contour(x=X[0], y=Y[:, 0], z=zz, colorscale=cs, zmid=zmid, ncontours=16,
                               contours=dict(showlines=False), colorbar=dict(title=w.unit.iloc[0] if "unit" in w else "")))
    fig.add_scatter(x=w.x, y=w.y, mode="markers", marker=dict(size=7, color=viz.SURFACE, line=dict(color=viz.INK_2, width=1)),
                    text=[f"site {s}: {v:.3f}" for s, v in zip(w.get("site", range(len(w))), w.value)], hoverinfo="text",
                    name="sites")
    fig.add_shape(type="circle", x0=-r_eff, y0=-r_eff, x1=r_eff, y1=r_eff, line=dict(color=viz.AXIS))
    fig = layout(fig, f"{wafer}  ({w.chamber_id.iloc[0] if 'chamber_id' in w else ''})", "x (mm)", "y (mm)", 520)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(fig, width="stretch")

    zk = zernike_decompose(w.x, w.y, w.value, radius_mm=r_eff)
    coef = {kk: v for kk, v in zk["coefficients"].items() if kk != "piston"}
    f2 = go.Figure(go.Bar(x=list(coef.values()), y=list(coef), orientation="h", marker_color=viz.SERIES[0]))
    f2.update_yaxes(autorange="reversed")
    c2.plotly_chart(layout(f2, f"Spatial signature (R² {zk['r2']:.2f})", "coefficient", "", 260), width="stretch")
    rp = radial_profile(w.x, w.y, w.value)
    f3 = go.Figure(go.Scatter(x=rp.r_mm, y=rp["mean"], mode="lines+markers", line=dict(color=viz.SERIES[0]),
                              error_y=dict(array=rp["std"].fillna(0), color=viz.MUTED)))
    c2.plotly_chart(layout(f3, "Radial profile", "radius (mm)", "value", 260), width="stretch")


def page_spc(df):
    st.header("SPC by chamber")
    if df is None:
        return
    param = st.selectbox("Parameter", sorted(df.parameter.unique()), key="spc_param")
    sub = df[df.parameter == param]
    wafers = wafer_summary(sub)
    stat = st.radio("Statistic", ["mean", "nu_1sigma_pct", "range"], horizontal=True,
                    format_func={"mean": "wafer mean", "nu_1sigma_pct": "within-wafer 1σ %", "range": "range"}.get)
    group = st.radio("Group by", [c for c in ("chamber_id", "tool_id", "metro_tool_id") if c in wafers], horizontal=True)
    ctype = st.radio("Chart", ["IMR", "EWMA", "CUSUM"], horizontal=True, key="chart_type")
    phase1 = st.slider("Phase I points (baseline for limits)", 5, 60, 20)
    colors = viz.color_map(wafers[group])
    charts = spc_by_group(wafers, group, stat, ctype, phase1)
    cols = st.columns(2)
    summary = []
    for i, (g, ch) in enumerate(charts.items()):
        sw = wafers[wafers[group] == g].sort_values("timestamp")
        x = sw.timestamp
        fig = go.Figure()
        fig.add_scatter(x=x, y=ch.statistic, mode="lines+markers", name=str(g), line=dict(color=colors[g], width=1.5),
                        marker=dict(size=5), text=sw.wafer_id, hovertemplate="%{text}<br>%{y:.4f}<extra></extra>")
        fig.add_scatter(x=x, y=ch.ucl, mode="lines", name="limits", line=dict(color=viz.STATUS["critical"], width=1))
        fig.add_scatter(x=x, y=ch.lcl, mode="lines", showlegend=False, line=dict(color=viz.STATUS["critical"], width=1))
        if ch.chart_type != "CUSUM":
            fig.add_hline(y=ch.cl, line=dict(color=viz.INK_2, width=1))
        ooc = ch.out_of_control
        if ooc.size:
            fig.add_scatter(x=x.iloc[ooc], y=ch.statistic[ooc], mode="markers", name="violation",
                            marker=dict(size=11, color="rgba(0,0,0,0)", line=dict(color=viz.STATUS["critical"], width=2)))
        cols[i % 2].plotly_chart(layout(fig, f"{g}  {ctype}", "time", stat, 320), width="stretch")
        summary.append({group: g, "points": len(ch.statistic), "violations": int(ooc.size), "CL": ch.cl, "σ short-term": ch.sigma})
    st.dataframe(pd.DataFrame(summary).style.format(precision=4), hide_index=True)
    if stat == "mean" and {"lsl", "usl"} <= set(sub.columns):
        lsl, usl = float(sub.lsl.iloc[0]), float(sub.usl.iloc[0])
        cap = [{group: g, **process_capability(gw["mean"], lsl, usl)} for g, gw in wafers.groupby(group)]
        st.subheader(f"Capability (LSL {lsl}, USL {usl})")
        st.dataframe(pd.DataFrame(cap).style.format(precision=3), hide_index=True)


def page_msa():
    st.header("Measurement system analysis")
    lim = load_yaml("limits.yaml")
    spec = lim["parameters"]["ox_thickness_nm"]
    st.subheader("Gauge R&R (synthetic study, or upload part/operator/value CSV)")
    up = st.file_uploader("GR&R CSV with columns part, operator, value", type="csv", key="grr")
    if up is not None:
        data = pd.read_csv(up)
    else:
        c = st.columns(3)
        rep = c[0].slider("repeatability σ (nm)", 0.01, 0.3, 0.05, 0.01)
        op = c[1].slider("tool-to-tool σ (nm)", 0.0, 0.3, 0.03, 0.01)
        part = c[2].slider("part spread σ (nm)", 0.1, 3.0, 1.0, 0.1)
        data = grr_study(repeat_sigma=rep, operator_sigma=op, part_sigma=part)
    c = st.columns(2)
    lsl = c[0].number_input("LSL", value=float(spec["lsl"]))
    usl = c[1].number_input("USL", value=float(spec["usl"]))
    g = gauge_rr(data, lsl=lsl, usl=usl, k=lim["msa"]["grr_k"])
    k = st.columns(4)
    k[0].metric("%GRR (study var)", f"{g['pct_study_var']['gauge_rr']:.1f} %")
    k[1].metric("P/T", f"{g['pct_tolerance']['gauge_rr']:.1f} %")
    k[2].metric("ndc", g["ndc"])
    k[3].metric("verdict", g["verdict"])
    comps = ["repeatability", "reproducibility", "gauge_rr", "part_to_part"]
    fig = go.Figure(go.Bar(x=[g["pct_study_var"][c] for c in comps], y=comps, orientation="h", marker_color=viz.SERIES[0],
                           text=[f"{g['pct_study_var'][c]:.1f}%" for c in comps], textposition="outside"))
    fig.add_vline(x=10, line=dict(color=viz.STATUS["good"], width=1))
    fig.add_vline(x=30, line=dict(color=viz.STATUS["critical"], width=1))
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(layout(fig, "Variance components (10% / 30% guides)", "% study variation", "", 300), width="stretch")

    st.subheader("Tool matching")
    c = st.columns(2)
    off = c[0].slider("true offset of FT02 (nm)", -0.5, 0.5, 0.1, 0.01)
    slope = c[1].slider("true slope of FT02", 0.95, 1.05, 1.0, 0.005)
    mdf = matching_study(offset=off, slope=slope)
    res = fleet_matching(mdf, reference="FT01", offset_spec=lim["msa"]["matching_offset_spec"],
                         slope_tol=lim["msa"]["matching_slope_tol"])
    st.dataframe(res.style.format(precision=4), hide_index=True)
    wide = mdf.pivot_table(index=["wafer_id", "site"], columns="tool_id", values="value").reset_index()
    fig = go.Figure(go.Scatter(x=wide.FT01, y=wide.FT02 - wide.FT01, mode="markers", marker=dict(size=6, color=viz.SERIES[0]),
                               name="site"))
    spec_off = lim["msa"]["matching_offset_spec"]
    for y in (-spec_off, spec_off):
        fig.add_hline(y=y, line=dict(color=viz.STATUS["critical"], width=1))
    st.plotly_chart(layout(fig, "Bland-Altman: FT02 − FT01 vs FT01 (red = matching spec)", "FT01 (nm)", "difference (nm)"),
                    width="stretch")


def page_studies():
    st.header("Recipe development studies")
    wl = np.linspace(250, 1000, 151)
    stack, _ = load_stack("gate_oxide_thin", films_cfg())
    ts = [1, 2, 3, 5, 10, 20, 50, 100, 200]
    if st.button("Run sensitivity study (reflectometry vs SE)"):
        r = thickness_sensitivity(stack, 0, ts, wl, "reflectometry", noise=0.002)
        s = thickness_sensitivity(stack, 0, ts, wl, "se", angles=(65, 70, 75), noise=0.0007)
        fig = go.Figure([go.Scatter(x=r.thickness_nm, y=r.est_precision_nm, name="reflectometry", line=dict(color=viz.SERIES[0])),
                         go.Scatter(x=s.thickness_nm, y=s.est_precision_nm, name="SE 65/70/75°", line=dict(color=viz.SERIES[1]))])
        fig.update_xaxes(type="log")
        fig.update_yaxes(type="log")
        st.plotly_chart(layout(fig, "Estimated 1σ precision vs SiO2 thickness", "thickness (nm)", "precision (nm)"),
                        width="stretch")
    if st.button("Run thickness / n correlation study (~5 s)"):
        c = thickness_n_correlation([2, 5, 10, 25, 50, 100, 200], wl)
        fig = go.Figure(go.Scatter(x=c.thickness_nm, y=c.A_stderr, mode="lines+markers", line=dict(color=viz.SERIES[0]),
                                   name="σ(n)"))
        fig.update_xaxes(type="log")
        fig.update_yaxes(type="log")
        st.plotly_chart(layout(fig, "Uncertainty of n (Cauchy A) when floated with thickness", "thickness (nm)", "σ(A)"),
                        width="stretch")
        st.dataframe(c.style.format(precision=4), hide_index=True)


PAGES = {
    "Film stack & fit": lambda df: page_stack(),
    "Wafer map": page_wafer,
    "SPC": page_spc,
    "MSA": lambda df: page_msa(),
    "Recipe studies": lambda df: page_studies(),
}

st.sidebar.title("metro-toolkit")
st.sidebar.caption("Thin-film metrology analysis · synthetic data only")
choice = st.sidebar.radio("Page", list(PAGES))
data = get_data() if choice in ("Wafer map", "SPC") else None
PAGES[choice](data)
