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
from metro_toolkit.config import data_dir, import_dir, load_stack, load_yaml, wavelengths  # noqa: E402
from metro_toolkit.datagen import ThicknessSimConfig, grr_study, matching_study, simulate_thickness  # noqa: E402
from metro_toolkit.datagen.answer_key import compare_drivers, score_detection, spc_flags  # noqa: E402
from metro_toolkit.datagen.fab import load_fab_config, load_truth, save_fab, simulate_fab  # noqa: E402
from metro_toolkit.metrology.thinfilm import (  # noqa: E402
    ellipsometry,
    fit,
    reflectance,
    simulate_reflectometry,
    simulate_se,
)
from metro_toolkit.metrology.thinfilm.studies import thickness_n_correlation, thickness_sensitivity  # noqa: E402
from metro_toolkit.msa import fleet_matching, gauge_rr  # noqa: E402
from metro_toolkit.ingest import (  # noqa: E402
    FIELDS,
    ImportSpec,
    build_long,
    detect_layout,
    excel_sheets,
    guess_mapping,
    list_datasets,
    list_profiles,
    load_dataset,
    load_profile,
    parameter_table,
    quality_report,
    read_secom,
    read_table,
    save_dataset,
    save_profile,
)
from metro_toolkit.ingest.mapping import LONG_ONLY  # noqa: E402
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


SAMPLE = "合成範例資料 (synthetic sample)"
UPLOAD = "上傳標準格式 CSV"


def get_data() -> pd.DataFrame | None:
    """Data source for the analysis pages: synthetic sample, an imported dataset, or a standard CSV."""
    imported = list_datasets()
    options = [SAMPLE] + [f"匯入：{n}" for n in imported] + [UPLOAD]
    active = st.session_state.get("dataset")
    index = options.index(f"匯入：{active}") if active and f"匯入：{active}" in options else 0
    choice = st.sidebar.selectbox("資料來源 Data source", options, index=index,
                                  help="在 **Data import** 頁面匯入自己的檔案後，會出現在這個清單。")
    if choice == SAMPLE:
        st.session_state.pop("dataset", None)
        return sample_data()
    if choice.startswith("匯入："):
        name = choice.split("：", 1)[1]
        st.session_state["dataset"] = name
        return load_dataset(name)
    up = st.sidebar.file_uploader("Measurement CSV (standard schema)", type="csv")
    if up is None:
        st.sidebar.caption("請上傳已是標準欄位名稱的 CSV；其他格式請用 Data import 頁面。")
        return None
    df = pd.read_csv(up)
    problems = validate(df)
    if problems:
        st.error("Data problems:\n- " + "\n- ".join(problems) + "\n\n請改用 **Data import** 頁面對應欄位。")
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


# --------------------------------------------------------------------------- #
# Pages                                                                       #
# --------------------------------------------------------------------------- #


def page_import():
    st.header("Data import 資料匯入")
    st.info(f"🔒 匯入的資料只會存在這台電腦：`{import_dir()}`（已排除在 git 之外，不會上傳 GitHub）。"
            "公司資料請只在公司允許的電腦上使用。")
    fmt = st.radio("檔案格式", ["CSV / Excel", "SECOM（secom.data + secom_labels.data）"], horizontal=True)
    if fmt.startswith("CSV"):
        up = st.file_uploader("上傳量測資料（CSV、TXT、Excel）", type=["csv", "txt", "tsv", "xlsx", "xlsm", "xls", "data"])
        if up is None:
            st.markdown(
                "支援兩種表格：\n"
                "- **每列一個量測值**（long）：要有 *量測項目* 與 *數值* 欄，最好有量測點座標 X/Y → 可畫晶圓圖\n"
                "- **每列一片晶圓**（wide）：每個參數一欄，例如機台匯出的摘要表 → SPC、能力分析、良率\n\n"
                "欄位名稱不必相同，下一步會自動猜測對應，你再確認。")
            return
        sheet = None
        if up.name.lower().endswith((".xlsx", ".xlsm", ".xls")):
            sheet = st.selectbox("工作表 Sheet", excel_sheets(up))
        raw = read_table(up, up.name, sheet)
        default_name = Path(up.name).stem
    else:
        c1, c2 = st.columns(2)
        d = c1.file_uploader("secom.data", type=["data", "txt"])
        lab = c2.file_uploader("secom_labels.data", type=["data", "txt"])
        if d is None or lab is None:
            st.markdown("UCI SECOM 是真實晶圓廠的公開資料（1567 筆 × 590 個感測器，含合格／失效標籤）。"
                        "下載：https://archive.ics.uci.edu/dataset/179/secom ，解壓後上傳這兩個檔案。")
            return
        raw = read_secom(d, lab)
        default_name = "secom"
    st.caption(f"{len(raw)} 列 × {raw.shape[1]} 欄 · 文字編碼 {raw.attrs.get('encoding')} · 分隔符號 {raw.attrs.get('delimiter')}")
    st.dataframe(raw.head(15), hide_index=True)

    profiles = list_profiles()
    prof = st.selectbox("套用已儲存的欄位對應設定（profile）", ["（自動判斷）"] + profiles,
                        help="同一台機台或同一種匯出格式，第一次對應好並儲存，下次選它即可。")
    saved = load_profile(prof) if prof != "（自動判斷）" else None
    guess = {k: v for k, v in (saved.mapping if saved else guess_mapping(raw.columns)).items() if v in raw.columns}
    layout0 = saved.layout if saved else detect_layout(guess)

    st.subheader("1. 表格格式")
    layout = st.radio("每一列代表什麼？", ["long", "wide"], index=0 if layout0 == "long" else 1, horizontal=True,
                      format_func={"long": "一個量測值（long）", "wide": "一片晶圓（wide）"}.get)

    st.subheader("2. 欄位對應")
    st.caption("已自動猜測，請確認或修改。沒有的欄位選「（無）」。")
    fields = [f for f in FIELDS if layout == "long" or f not in LONG_ONLY]
    cols = st.columns(3)
    mapping = {}
    for i, f in enumerate(fields):
        options = ["（無）"] + list(raw.columns)
        cur = guess.get(f)
        sel = cols[i % 3].selectbox(f"{f}（{FIELDS[f][0]}）", options, index=options.index(cur) if cur in options else 0,
                                    key=f"map_{layout}_{f}")
        if sel != "（無）":
            mapping[f] = sel
    used = list(mapping.values())
    if len(used) != len(set(used)):
        st.error("同一個欄位被對應到兩個項目，請修正。")
        return
    if layout == "long" and not {"parameter", "value", "wafer_id"} <= set(mapping):
        st.warning("long 格式至少需要對應 **parameter（量測項目）**、**value（數值）**、**wafer_id（晶圓編號）**。")
        return

    st.subheader("3. 參數")
    table = parameter_table(raw, mapping, layout)
    if saved:
        prev = {p["source"]: p for p in saved.parameters}
        for i, r in table.iterrows():
            if r["source"] in prev:
                for k in ("name", "unit", "include"):
                    table.at[i, k] = prev[r["source"]].get(k, r[k])
    edited = st.data_editor(
        table, hide_index=True, key=f"params_{layout}_{len(table)}",
        column_config={
            "source": st.column_config.TextColumn("原始名稱", disabled=True),
            "name": st.column_config.TextColumn("名稱（可改名）"),
            "unit": st.column_config.TextColumn("單位", help="長度單位寫 nm、Å（或 A）、µm（或 um）即可自動換算"),
            "include": st.column_config.CheckboxColumn("匯入"),
        })
    to_nm = st.checkbox("長度單位（Å、µm）自動換算成 nm", value=saved.to_nm if saved else True)
    st.caption("若要在 SemiYield 的 Yield Prediction 使用，請把良率欄位命名為 `yield`，製程參數可改名為 "
               "`gate_oxide_thickness`、`poly_cd`、`implant_dose`、`anneal_temp`、`metal_resistance`、"
               "`contact_resistance`、`etch_rate`、`deposition_unif`、`defect_density`。")

    spec = ImportSpec(layout, mapping, edited.to_dict("records"), to_nm)
    try:
        long_df, notes = build_long(raw, spec)
    except ValueError as exc:
        st.error(str(exc))
        return
    rep = quality_report(long_df, notes)

    st.subheader("4. 檢查報告")
    sm = rep["summary"]
    k = st.columns(5)
    k[0].metric("資料列", f"{sm['rows']:,}")
    k[1].metric("批 lots", sm["lots"])
    k[2].metric("晶圓 wafers", sm["wafers"])
    k[3].metric("參數", sm["parameters"])
    k[4].metric("每片量測點", f"{sm['sites_per_wafer']:.0f}")
    st.caption(f"時間範圍：{sm['time_span']}")
    for issue in rep["issues"]:
        {"error": st.error, "warning": st.warning, "info": st.info}[issue["level"]](issue["message"])
    with st.expander("轉換後的標準表格（前 20 列）"):
        st.dataframe(long_df.head(20), hide_index=True)

    st.subheader("5. 儲存並使用")
    has_error = any(i["level"] == "error" for i in rep["issues"])
    c1, c2 = st.columns(2)
    name = c1.text_input("資料集名稱", value=default_name)
    keep_profile = c2.checkbox("同時儲存欄位對應設定（profile）", value=True)
    profile_name = c2.text_input("設定名稱", value=prof if saved else default_name, disabled=not keep_profile)
    if st.button("儲存並使用", type="primary", disabled=has_error):
        paths = save_dataset(name, long_df)
        if keep_profile:
            save_profile(profile_name, spec)
        st.session_state["dataset"] = Path(paths["long"]).stem
        st.success(f"已儲存 `{paths['long'].name}`。左側「資料來源」已切換到這份資料，可到 Wafer map / SPC 頁面分析；"
                   "SemiYield 的 launcher 也可以載入它。")
    if has_error:
        st.caption("請先修正紅色錯誤再儲存。")


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
    if "x" not in df or df["x"].isna().all():
        st.info("這份資料沒有量測點座標（每片只有一個值），無法畫晶圓圖。請到 **SPC** 頁面分析。")
        return
    df = df[df["x"].notna() & df["y"].notna()]
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
    groups = [c for c in ("chamber_id", "tool_id", "metro_tool_id") if c in wafers]
    if not groups:
        wafers["all wafers"] = "all"
        groups = ["all wafers"]
    group = st.radio("Group by", groups, horizontal=True)
    ctype = st.radio("Chart", ["IMR", "EWMA", "CUSUM"], horizontal=True, key="chart_type")
    phase1 = st.slider("Phase I points (baseline for limits)", 5, 60, 20)
    colors = viz.color_map(wafers[group]) if wafers[group].nunique() <= len(viz.SERIES) else {
        g: viz.SERIES[0] for g in wafers[group].unique()}
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
    if stat == "mean" and {"lsl", "usl"} <= set(sub.columns) and sub.lsl.notna().any() and sub.usl.notna().any():
        lsl, usl = float(sub.lsl.dropna().median()), float(sub.usl.dropna().median())
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

SCENARIO_TEXT = {
    "baseline": "正常生產：只有自然變異（chamber 差異、PM 之間的漂移、隨機缺陷）",
    "chamber_shift": "某個 chamber 突然偏移",
    "slow_drift": "某個 chamber 慢慢漂移",
    "metrology_offset": "某台量測機台有偏差（只影響量測值，不影響產品）",
    "particle_event": "微粒事件：缺陷暴增並有空間圖樣",
    "edge_bowl": "某個 chamber 的晶圓內分布改變（邊緣與中心差變大）",
    "recipe_change": "某站 recipe 改變，影響所有機台並傳到下一站",
    "mixed": "多個事件同時存在（綜合練習）",
}
CAUSE_LABEL = {".": "pass", "D": "defect", "G": "gate_ox_thk", "K": "hk_thk", "T": "tin_thk", "C": "wl_cd_etch",
               "I": "ild_thk"}
CAUSE_COLOR = {".": viz.GRID, **{c: viz.SERIES[i] for i, c in enumerate("DGKTCI")}}  # fixed: colour follows the cause


def page_fab():
    st.header("Fab simulator 模擬晶圓廠")
    st.caption("產生行為接近真實晶圓廠的資料，並保留「答案」。先用 Wafer map / SPC 頁面自己找問題，再回來對答案、打分數。")
    cfg = load_fab_config()
    c1, c2, c3 = st.columns([2, 1, 1])
    scenario = c1.selectbox("情境 Scenario", list(cfg["scenarios"]), index=list(cfg["scenarios"]).index("mixed"),
                            format_func=lambda k: f"{k} — {SCENARIO_TEXT.get(k, '')}")
    lots = c2.slider("批數 lots", 20, 120, int(cfg["n_lots"]), 5, help="每批 25 片；每批量測 5 片")
    seed = c3.number_input("亂數種子 seed", value=int(cfg["seed"]), step=1)
    c4, c5 = st.columns([2, 1])
    name = c4.text_input("資料集名稱", value=f"sim_{scenario}")
    sy = c5.checkbox("用 SemiYield 欄位名稱", value=False,
                     help="把 gate_ox_thk → gate_oxide_thickness、wl_cd_etch → poly_cd、rs_ohm_sq → metal_resistance，"
                          "讓 SemiYield 的 Yield Prediction 可以直接使用。")
    if st.button("產生並儲存", type="primary"):
        with st.spinner("模擬中…"):
            res = simulate_fab(cfg, scenario, lots, int(seed))
            paths = save_fab(res, name, semiyield_names=sy)
        st.session_state["dataset"] = paths["long"].stem
        st.success(f"已產生 {len(res.wafers)} 片晶圓並存成資料集 `{paths['long'].stem}`；左側資料來源已切換。"
                   "現在可以到 Wafer map / SPC 頁面找問題。")

    sims = [d for d in list_datasets() if load_truth(d) is not None]
    if not sims:
        st.info("還沒有模擬資料。選擇情境後按「產生並儲存」。")
        return
    active = st.session_state.get("dataset")
    pick = st.selectbox("檢視的模擬資料", sims, index=sims.index(active) if active in sims else 0)
    truth = load_truth(pick)
    w = truth["wafers"]
    long_df = load_dataset(pick)

    k = st.columns(5)
    k[0].metric("晶圓", f"{len(w):,}")
    k[1].metric("批", w["lot_id"].nunique())
    k[2].metric("平均良率", f"{100 * w['yield'].mean():.1f} %")
    k[3].metric("良率標準差", f"{100 * w['yield'].std():.1f} %")
    k[4].metric("注入事件", len(truth["events"]), help="細節在最下方「看答案」")

    lot_y = w.groupby("lot_index")["yield"].mean().reset_index()
    fig = go.Figure(go.Scatter(x=lot_y["lot_index"], y=100 * lot_y["yield"], mode="lines+markers",
                               line=dict(color=viz.SERIES[0], width=1.5), marker=dict(size=5),
                               hovertemplate="lot %{x}<br>平均良率 %{y:.1f}%<extra></extra>"))
    st.plotly_chart(layout(fig, "每批平均良率（所有晶圓都有電測與良率）", "lot", "yield (%)", 300), width="stretch")

    st.subheader("晶圓圖 Die map")
    order = w.sort_values("yield")["wafer_id"].tolist()
    wid = st.selectbox("晶圓（良率最低的在前）", order)
    m = truth["dies"].set_index("wafer_id").loc[wid, "map"]
    gx, gy = np.array(truth["grid"]["x"]), np.array(truth["grid"]["y"])
    codes = np.array(list(m))
    fig = go.Figure()
    present = [c for c in CAUSE_LABEL if (codes == c).any()]
    for c in present:
        sel = codes == c
        color = CAUSE_COLOR[c]
        fig.add_scatter(x=gx[sel], y=gy[sel], mode="markers", name=f"{CAUSE_LABEL[c]} ({sel.sum()})",
                        marker=dict(symbol="square", size=9, color=color),
                        hovertemplate=f"{CAUSE_LABEL[c]}<br>x %{{x:.0f}} mm, y %{{y:.0f}} mm<extra></extra>")
    r = truth["grid"]["r_eff"] + 3
    fig.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r, line=dict(color=viz.AXIS))
    row = w.set_index("wafer_id").loc[wid]
    fig = layout(fig, f"{wid}  良率 {100 * row['yield']:.1f}%  · 缺陷圖樣：{row['defect_pattern']}", "x (mm)", "y (mm)", 520)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, width="stretch")

    st.subheader("偵測打分數 Score my detection")
    st.caption("用你選的管制圖設定跑一次 SPC（每個參數、每個 chamber 分開），再和答案比對。")
    c1, c2, c3, c4 = st.columns(4)
    chart = c1.radio("管制圖", ["IMR", "EWMA", "CUSUM"], horizontal=True, key="fab_chart")
    rules = c2.multiselect("WE 規則", [1, 2, 3, 4], default=[1, 2], key="fab_rules")
    stats = c3.multiselect("統計量", ["mean", "nu_1sigma_pct"], default=["mean", "nu_1sigma_pct"], key="fab_stats",
                           format_func={"mean": "晶圓平均", "nu_1sigma_pct": "片內 1σ %"}.get)
    phase1 = c4.slider("Phase I 點數", 8, 40, 20, key="fab_phase1")
    if st.button("計算分數"):
        flags = spc_flags(long_df, chart, tuple(rules) or (1,), tuple(stats) or ("mean",), phase1)
        table, summ = score_detection(flags, truth["events"], long_df)
        st.session_state["fab_score"] = (pick, table, summ)
    if st.session_state.get("fab_score") and st.session_state["fab_score"][0] == pick:
        _, table, summ = st.session_state["fab_score"]
        k = st.columns(4)
        k[0].metric("抓到的事件", f"{summ['detected']} / {summ['observable']}",
                    help="可觀測 = 至少有一片受影響的晶圓被量測到")
        k[1].metric("中位延遲", "—" if summ["median_delay_wafers"] is None else f"{summ['median_delay_wafers']:.0f} 片",
                    help="事件開始後，第幾片被量測到的受影響晶圓才被標記（0 = 第一片就抓到）")
        k[2].metric("誤警報率", f"{summ['false_alarm_rate_pct']:.1f} %",
                    help="被標記、但不屬於任何注入事件的點。注意：PM 之間的自然漂移也會被標記，它是真實製程行為但不是注入事件。")
        k[3].metric("被標記的點", summ["flagged_points"])
        with st.expander("看每個事件的結果（會顯示答案）"):
            st.dataframe(table.drop(columns=["affects_product"]).round(2), hide_index=True)

    with st.expander("看答案 Answer key"):
        ev = truth["events"].drop(columns=["wafer_ids"]).copy()
        ev["yield_impact"] = (100 * ev["yield_impact"]).round(2)
        st.markdown("**注入的事件**（yield_impact = 與「同一批晶圓、同樣亂數但沒有事件」相比的良率差，%）")
        st.dataframe(ev.rename(columns={"yield_impact": "yield_impact_%"}), hide_index=True)
        drv = truth["drivers"]
        fig = go.Figure(go.Bar(x=drv["yield_loss_pct"], y=drv["cause"], orientation="h", marker_color=viz.SERIES[0],
                               hovertemplate="%{y}: 平均損失 %{x:.2f}% 良率<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(layout(fig, "真正的良率損失來源（拿來和 SHAP / 相關性排名比對）", "平均良率損失 (%)", "", 300),
                        width="stretch")
        st.caption("缺陷圖樣：" + "、".join(f"{k} {v}" for k, v in w["defect_pattern"].value_counts().items()))
        back = {b: a for a, b in (truth.get("renamed") or {}).items()}
        wt = long_df.assign(parameter=long_df["parameter"].replace(back)).pivot_table(
            index="wafer_id", columns="parameter", values="value", aggfunc="mean")
        causes = [c for c in drv["cause"] if c in wt.columns and c != "yield"]
        if "yield" in wt.columns and causes:
            corr = wt[causes + ["yield"]].corr(method="spearman")["yield"].drop("yield").abs().sort_values(ascending=False)
            cmp = compare_drivers(list(corr.index), drv)
            st.markdown(
                f"**簡單相關性排名 vs 真正原因**：相關性排名 {' > '.join(corr.index)}；"
                f"真正原因 {' > '.join(cmp['truth'])}。第一名{'相同' if cmp['top1_match'] else '不同'}"
                + (f"，排名相關 ρ = {cmp['spearman']:.2f}" if cmp["spearman"] is not None else "")
                + "。相關性只看量測過的晶圓與晶圓平均值，可能漏掉只在部分晶粒發生的問題。")
        if truth.get("semiyield_names"):
            st.caption("此資料集使用 SemiYield 欄位名稱：" + "、".join(f"{a} → {b}" for a, b in truth["renamed"].items()))


PAGES = {
    "Data import": lambda df: page_import(),
    "Fab simulator": lambda df: page_fab(),
    "Film stack & fit": lambda df: page_stack(),
    "Wafer map": page_wafer,
    "SPC": page_spc,
    "MSA": lambda df: page_msa(),
    "Recipe studies": lambda df: page_studies(),
}

st.sidebar.title("metro-toolkit")
st.sidebar.caption("Thin-film metrology analysis · synthetic sample or your own imported data")
choice = st.sidebar.radio("Page", list(PAGES))
data = get_data() if choice in ("Wafer map", "SPC") else None
PAGES[choice](data)
