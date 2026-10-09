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
from metro_toolkit.datagen.answer_key import CHART_SETUPS, compare_charts, compare_drivers, score_detection, spc_flags  # noqa: E402
from metro_toolkit.datagen.fab import load_fab_config, load_truth, save_fab, simulate_fab  # noqa: E402
from metro_toolkit.doe import (  # noqa: E402
    curvature_test,
    desirability,
    evaluate_recipe,
    fit_model,
    load_processes,
    make_design,
    optimize,
    overall,
    run_experiments,
    run_sheet,
    to_coded,
    to_real,
    true_optimum,
)
from metro_toolkit.metrology.thinfilm import fit, simulate_reflectometry, simulate_se  # noqa: E402
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
from metro_toolkit.dashboard.figures import (  # noqa: E402
    CAUSE_COLOR,
    CAUSE_NAME,
    bland_altman_figure,
    die_map_figure,
    doe_contour_figure,
    fit_figures,
    grr_figure,
    layout,
    legend_line,
    pareto_figure,
    radial_figure,
    sensitivity_figure,
    spc_figure,
    tn_figure,
    wafer_map_figure,
    yield_trend_figure,
    zernike_figure,
)
from metro_toolkit.guide import insights as gi  # noqa: E402
from metro_toolkit.guide.render import H, explain, language_switch  # noqa: E402
from metro_toolkit.ingest.mapping import LONG_ONLY  # noqa: E402
from metro_toolkit.schema import validate  # noqa: E402
from metro_toolkit.wafer import radial_profile, uniformity_metrics, zernike_decompose  # noqa: E402
from metro_toolkit.wafer.patterns import (  # noqa: E402
    PATTERN_TEXT,
    GridGeometry,
    PatternClassifier,
    evaluate,
    fail_vector,
    feature_table,
)

st.set_page_config(page_title="metro-toolkit", layout="wide")



def col_help(df: pd.DataFrame, keys: dict) -> dict:
    """column_config giving table columns a "?" explanation: {column: guide key}."""
    return {c: st.column_config.Column(help=H(k)) for c, k in keys.items() if c in df.columns and H(k)}



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
    choice = st.sidebar.selectbox("資料來源 Data source", options, index=index, help=H("data.source"), key=f"data_source_{active}")
    if choice == SAMPLE:
        st.session_state.pop("dataset", None)
        return sample_data()
    if choice.startswith("匯入："):
        name = choice.split("：", 1)[1]
        st.session_state["dataset"] = name
        return load_dataset(name)
    up = st.sidebar.file_uploader("Measurement CSV (standard schema)", type="csv", help=H("data.upload_standard"), key="data_upload_std")
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
    fmt = st.radio("檔案格式", ["CSV / Excel", "SECOM（secom.data + secom_labels.data）"], horizontal=True,
                   help=H("import.format"), key="import_format")
    if fmt.startswith("CSV"):
        up = st.file_uploader("上傳量測資料（CSV、TXT、Excel）", type=["csv", "txt", "tsv", "xlsx", "xlsm", "xls", "data"],
                              help=H("import.upload"), key="import_upload")
        if up is None:
            st.markdown(
                "支援兩種表格：\n"
                "- **每列一個量測值**（long）：要有 *量測項目* 與 *數值* 欄，最好有量測點座標 X/Y → 可畫晶圓圖\n"
                "- **每列一片晶圓**（wide）：每個參數一欄，例如機台匯出的摘要表 → SPC、能力分析、良率\n\n"
                "欄位名稱不必相同，下一步會自動猜測對應，你再確認。")
            return
        sheet = None
        if up.name.lower().endswith((".xlsx", ".xlsm", ".xls")):
            sheet = st.selectbox("工作表 Sheet", excel_sheets(up), help=H("import.sheet"), key=f"import_sheet_{up.name}")
        raw = read_table(up, up.name, sheet)
        default_name = Path(up.name).stem
    else:
        c1, c2 = st.columns(2)
        d = c1.file_uploader("secom.data", type=["data", "txt"], help=H("import.secom_data"), key="import_secom_data")
        lab = c2.file_uploader("secom_labels.data", type=["data", "txt"], help=H("import.secom_labels"), key="import_secom_labels")
        if d is None or lab is None:
            st.markdown("UCI SECOM 是真實晶圓廠的公開資料（1567 筆 × 590 個感測器，含合格／失效標籤）。"
                        "下載：https://archive.ics.uci.edu/dataset/179/secom ，解壓後上傳這兩個檔案。")
            return
        raw = read_secom(d, lab)
        default_name = "secom"
    st.caption(f"{len(raw)} 列 × {raw.shape[1]} 欄 · 文字編碼 {raw.attrs.get('encoding')} · 分隔符號 {raw.attrs.get('delimiter')}")
    st.dataframe(raw.head(15), hide_index=True)

    profiles = list_profiles()
    prof = st.selectbox("套用已儲存的欄位對應設定（profile）", ["（自動判斷）"] + profiles, help=H("import.profile"), key="import_profile")
    saved = load_profile(prof) if prof != "（自動判斷）" else None
    guess = {k: v for k, v in (saved.mapping if saved else guess_mapping(raw.columns)).items() if v in raw.columns}
    layout0 = saved.layout if saved else detect_layout(guess)

    st.subheader("1. 表格格式")
    layout = st.radio("每一列代表什麼？", ["long", "wide"], index=0 if layout0 == "long" else 1, horizontal=True,
                      format_func={"long": "一個量測值（long）", "wide": "一片晶圓（wide）"}.get, help=H("import.layout"), key=f"import_layout_{default_name}_{prof}")

    st.subheader("2. 欄位對應")
    st.caption("已自動猜測，請確認或修改。沒有的欄位選「（無）」。")
    fields = [f for f in FIELDS if layout == "long" or f not in LONG_ONLY]
    cols = st.columns(3)
    mapping = {}
    for i, f in enumerate(fields):
        options = ["（無）"] + list(raw.columns)
        cur = guess.get(f)
        sel = cols[i % 3].selectbox(f"{f}（{FIELDS[f][0]}）", options, index=options.index(cur) if cur in options else 0,
                                    key=f"map_{layout}_{f}", help=H(f"field.{f}"))
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
    st.caption("參數表 Parameter table", help=H("import.params_table"))
    edited = st.data_editor(
        table, hide_index=True, key=f"params_{layout}_{len(table)}",
        column_config={
            "source": st.column_config.TextColumn("原始名稱", disabled=True),
            "name": st.column_config.TextColumn("名稱（可改名）"),
            "unit": st.column_config.TextColumn("單位", help="長度單位寫 nm、Å（或 A）、µm（或 um）即可自動換算"),
            "include": st.column_config.CheckboxColumn("匯入"),
        })
    to_nm = st.checkbox("長度單位（Å、µm）自動換算成 nm", value=saved.to_nm if saved else True, help=H("import.to_nm"), key=f"import_to_nm_{prof}")
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
    k[0].metric("資料列", f"{sm['rows']:,}", help=H("import.m_rows"))
    k[1].metric("批 lots", sm["lots"], help=H("import.m_lots"))
    k[2].metric("晶圓 wafers", sm["wafers"], help=H("import.m_wafers"))
    k[3].metric("參數", sm["parameters"], help=H("import.m_params"))
    k[4].metric("每片量測點", f"{sm['sites_per_wafer']:.0f}", help=H("import.m_sites"))
    st.caption(f"時間範圍：{sm['time_span']}")
    for issue in rep["issues"]:
        {"error": st.error, "warning": st.warning, "info": st.info}[issue["level"]](issue["message"])
    with st.expander("轉換後的標準表格（前 20 列）"):
        st.dataframe(long_df.head(20), hide_index=True)

    st.subheader("5. 儲存並使用")
    has_error = any(i["level"] == "error" for i in rep["issues"])
    c1, c2 = st.columns(2)
    name = c1.text_input("資料集名稱", value=default_name, help=H("import.name"), key=f"import_name_{default_name}")
    keep_profile = c2.checkbox("同時儲存欄位對應設定（profile）", value=True, help=H("import.keep_profile"), key="import_keep_profile")
    profile_name = c2.text_input("設定名稱", value=prof if saved else default_name, disabled=not keep_profile,
                                 help=H("import.profile_name"), key=f"import_profile_name_{default_name}_{prof}")
    if st.button("儲存並使用", type="primary", disabled=has_error, help=H("import.save"), key="import_save"):
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
    name = st.selectbox("Stack (config/films.yaml)", list(cfg["stacks"]), help=H("stack.select"), key="stack_select")
    stack, recipe = load_stack(name, cfg)
    st.caption(recipe.get("description", ""))
    wl = wavelengths(cfg)

    cols = st.columns(len(stack.layers) + 1)
    true_t = []
    for i, layer in enumerate(stack.layers):
        t0 = layer.thickness_nm
        true_t.append(cols[i].number_input(f"True L{i} {layer.name} (nm)", 0.0, 2000.0, float(t0), step=max(t0 / 50, 0.05),
                                           format="%.2f", help=H("stack.true_thickness"), key=f"stack_true_{name}_{i}"))
    technique = cols[-1].radio("Technique", ["reflectometry", "se"], index=0 if recipe.get("technique") != "se" else 1,
                               help=H("stack.technique"), key=f"stack_technique_{name}")
    truth = stack.copy_with(true_t)

    c1, c2 = st.columns(2)
    if technique == "reflectometry":
        noise = c1.slider("Reflectance noise (1σ)", 0.0, 0.01, 0.002, 0.0005, format="%.4f", help=H("stack.noise_r"), key="stack_noise_r")
        meas = simulate_reflectometry(truth, wl, noise=noise, rng=1)
    else:
        noise = c1.slider("Ψ noise (deg, 1σ); Δ noise = 2x", 0.0, 0.2, 0.02, 0.01, help=H("stack.noise_se"), key="stack_noise_se")
        angles = recipe.get("angles_deg", [65, 70, 75])
        meas = simulate_se(truth, wl, angles, noise, 2 * noise, rng=1)
    float_n = c2.checkbox("Also float n of the top layer (Cauchy A)", value=False, help=H("stack.float_n"), key="stack_float_n")

    params = list(recipe["fit_params"])
    if float_n and hasattr(stack.layers[0].material, "A"):
        from metro_toolkit.metrology.thinfilm import FitParameter

        a0 = stack.layers[0].material.A
        params.append(FitParameter(0, "A", (a0 - 0.3, a0 + 0.3)))
    elif float_n:
        st.warning("Top layer is not a Cauchy material; n is not floated.")

    with st.spinner("Fitting..."):
        res = fit(stack, meas, params)

    figs = fit_figures(technique, wl, meas, res.stack, angles if technique != "reflectometry" else None)
    for col, fig in zip(st.columns(len(figs)), figs):
        col.plotly_chart(fig, width="stretch")

    rows = []
    for lab in res.labels:
        layer = int(lab[1:].split(".")[0])
        tgt = lab.split(".")[1]
        truth_val = true_t[layer] if tgt == "thickness" else getattr(stack.layers[layer].material, tgt)
        rows.append({"parameter": lab, "true": truth_val, "fitted": res.values[lab], "± 1σ": res.stderr[lab],
                     "error": res.values[lab] - truth_val})
    m1, m2 = st.columns([2, 1])
    fit_tab = pd.DataFrame(rows)
    m1.dataframe(fit_tab.style.format(precision=4), hide_index=True, width="stretch",
                 column_config=col_help(fit_tab, {"parameter": "stack.col.parameter", "true": "stack.col.true",
                                                  "fitted": "stack.col.fitted", "± 1σ": "stack.col.sigma",
                                                  "error": "stack.col.error"}))
    m2.metric("reduced χ²", f"{res.chi2_red:.2f}", help=H("stack.chi2"))
    if len(res.labels) > 1:
        m2.caption("Parameter correlation", help=H("stack.corr"))
        m2.dataframe(pd.DataFrame(res.correlation, index=res.labels, columns=res.labels).style.format(precision=3))
    fixed_changed = [i for i, l in enumerate(stack.layers)
                     if i not in {p.layer for p in params} and abs(true_t[i] - l.thickness_nm) > 1e-9]
    if fixed_changed:
        st.info(f"Layer(s) {fixed_changed} differ from the recipe's fixed value: watch the floated-layer error "
                "while χ² stays low. Fit statistics do not reveal a wrong fixed layer.")
    explain("stack_reflectance" if technique == "reflectometry" else "stack_se",
            gi.stack_fit(res, rows, technique, fixed_changed))


def page_wafer(df):
    st.header("Wafer map & uniformity")
    if df is None:
        return
    if "x" not in df or df["x"].isna().all():
        st.info("這份資料沒有量測點座標（每片只有一個值），無法畫晶圓圖。請到 **SPC** 頁面分析。")
        return
    df = df[df["x"].notna() & df["y"].notna()]
    param = st.selectbox("Parameter", sorted(df.parameter.unique()), help=H("wafer.param"), key="wafer_param")
    sub = df[df.parameter == param]
    wafers = wafer_summary(sub)
    wafer = st.selectbox("Wafer (worst NU first)", wafers.sort_values("nu_1sigma_pct", ascending=False).wafer_id,
                         help=H("wafer.select"), key=f"wafer_pick_{param}")
    w = sub[sub.wafer_id == wafer]
    um = uniformity_metrics(w.value)
    r_eff = float(np.hypot(w.x, w.y).max())
    k = st.columns(5)
    k[0].metric("mean", f"{um['mean']:.3f}", help=H("wafer.mean"))
    k[1].metric("1σ NU", f"{um['nu_1sigma_pct']:.3f} %", help=H("wafer.nu"))
    k[2].metric("range", f"{um['range']:.3f}", help=H("wafer.range"))
    k[3].metric("(max−min)/2·mean", f"{um['half_range_pct']:.3f} %", help=H("wafer.half_range"))
    k[4].metric("sites", um["n_sites"], help=H("wafer.sites"))

    mode = st.radio("Colour scale", ["absolute (sequential)", "deviation from mean (diverging)"], horizontal=True,
                    help=H("wafer.colour"), key="wafer_colour")
    fig = wafer_map_figure(w, um, mode, f"{wafer}  ({w.chamber_id.iloc[0] if 'chamber_id' in w else ''})")
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(fig, width="stretch")
    zk = zernike_decompose(w.x, w.y, w.value, radius_mm=r_eff)
    rp = radial_profile(w.x, w.y, w.value)
    facts = gi.wafer_page(w, um, wafers, zk, rp, param)
    explain("wafer_map", facts["wafer_map"], where=c1)

    c2.plotly_chart(zernike_figure(zk), width="stretch")
    explain("wafer_zernike", facts["wafer_zernike"], where=c2)
    c2.plotly_chart(radial_figure(rp), width="stretch")
    explain("wafer_radial", facts["wafer_radial"], where=c2)


def page_spc(df):
    st.header("SPC by chamber")
    if df is None:
        return
    param = st.selectbox("Parameter", sorted(df.parameter.unique()), key="spc_param", help=H("spc.param"))
    sub = df[df.parameter == param]
    wafers = wafer_summary(sub)
    stat = st.radio("Statistic", ["mean", "nu_1sigma_pct", "range"], horizontal=True, help=H("spc.stat"),
                    format_func={"mean": "wafer mean", "nu_1sigma_pct": "within-wafer 1σ %", "range": "range"}.get, key="spc_stat")
    groups = [c for c in ("chamber_id", "tool_id", "metro_tool_id") if c in wafers]
    if not groups:
        wafers["all wafers"] = "all"
        groups = ["all wafers"]
    group = st.radio("Group by", groups, horizontal=True, help=H("spc.group"), key=f"spc_group_{'_'.join(groups)}")
    ctype = st.radio("Chart", ["IMR", "EWMA", "CUSUM"], horizontal=True, key="chart_type", help=H("spc.chart"))
    phase1 = st.slider("Phase I points (baseline for limits)", 5, 60, 20, help=H("spc.phase1"), key="spc_phase1")
    colors = viz.color_map(wafers[group]) if wafers[group].nunique() <= len(viz.SERIES) else {
        g: viz.SERIES[0] for g in wafers[group].unique()}
    charts = spc_by_group(wafers, group, stat, ctype, phase1)
    cols = st.columns(2)
    summary = []
    for i, (g, ch) in enumerate(charts.items()):
        sw = wafers[wafers[group] == g].sort_values("timestamp")
        cols[i % 2].plotly_chart(spc_figure(g, sw, ch, stat, colors[g], phase1), width="stretch")
        ooc = ch.out_of_control
        summary.append({group: g, "points": len(ch.statistic), "violations": int(ooc.size), "CL": ch.cl, "σ short-term": ch.sigma})
    sm = pd.DataFrame(summary)
    st.dataframe(sm.style.format(precision=4), hide_index=True,
                 column_config=col_help(sm, {"points": "spc.col.points", "violations": "spc.col.violations",
                                             "CL": "spc.col.cl", "σ short-term": "spc.col.sigma"}))
    cap, lsl, usl = None, None, None
    if stat == "mean" and {"lsl", "usl"} <= set(sub.columns) and sub.lsl.notna().any() and sub.usl.notna().any():
        lsl, usl = float(sub.lsl.dropna().median()), float(sub.usl.dropna().median())
        cap = [{group: g, **process_capability(gw["mean"], lsl, usl)} for g, gw in wafers.groupby(group)]
        st.subheader(f"Capability (LSL {lsl}, USL {usl})")
        ct = pd.DataFrame(cap)
        st.dataframe(ct.style.format(precision=3), hide_index=True,
                     column_config=col_help(ct, {c: f"cap.{c}" for c in ("mean", "sigma_within", "sigma_overall",
                                                                          "Cp", "Cpk", "Pp", "Ppk")}))
    explain("spc_chart", gi.spc(charts, wafers, group, stat, ctype, param, cap, lsl, usl))


def page_msa():
    st.header("Measurement system analysis")
    lim = load_yaml("limits.yaml")
    spec = lim["parameters"]["ox_thickness_nm"]
    st.subheader("Gauge R&R (synthetic study, or upload part/operator/value CSV)")
    up = st.file_uploader("GR&R CSV with columns part, operator, value", type="csv", key="grr", help=H("msa.upload"))
    if up is not None:
        data = pd.read_csv(up)
    else:
        c = st.columns(3)
        rep = c[0].slider("repeatability σ (nm)", 0.01, 0.3, 0.05, 0.01, help=H("msa.repeat_sigma"), key="msa_rep")
        op = c[1].slider("tool-to-tool σ (nm)", 0.0, 0.3, 0.03, 0.01, help=H("msa.tool_sigma"), key="msa_tool")
        part = c[2].slider("part spread σ (nm)", 0.1, 3.0, 1.0, 0.1, help=H("msa.part_sigma"), key="msa_part")
        data = grr_study(repeat_sigma=rep, operator_sigma=op, part_sigma=part)
    c = st.columns(2)
    lsl = c[0].number_input("LSL", value=float(spec["lsl"]), help=H("msa.lsl"), key="msa_lsl")
    usl = c[1].number_input("USL", value=float(spec["usl"]), help=H("msa.usl"), key="msa_usl")
    g = gauge_rr(data, lsl=lsl, usl=usl, k=lim["msa"]["grr_k"])
    k = st.columns(4)
    k[0].metric("%GRR (study var)", f"{g['pct_study_var']['gauge_rr']:.1f} %", help=H("msa.grr"))
    k[1].metric("P/T", f"{g['pct_tolerance']['gauge_rr']:.1f} %", help=H("msa.pt"))
    k[2].metric("ndc", g["ndc"], help=H("msa.ndc"))
    k[3].metric("verdict", g["verdict"], help=H("msa.verdict"))
    st.plotly_chart(grr_figure(g), width="stretch")
    explain("msa_grr", gi.msa_grr(g))

    st.subheader("Tool matching")
    c = st.columns(2)
    off = c[0].slider("true offset of FT02 (nm)", -0.5, 0.5, 0.1, 0.01, help=H("msa.offset"), key="msa_offset")
    slope = c[1].slider("true slope of FT02", 0.95, 1.05, 1.0, 0.005, help=H("msa.slope"), key="msa_slope")
    mdf = matching_study(offset=off, slope=slope)
    res = fleet_matching(mdf, reference="FT01", offset_spec=lim["msa"]["matching_offset_spec"],
                         slope_tol=lim["msa"]["matching_slope_tol"])
    st.dataframe(res.style.format(precision=4), hide_index=True,
                 column_config=col_help(res, {c: f"msa.col.{c}" for c in res.columns}))
    wide = mdf.pivot_table(index=["wafer_id", "site"], columns="tool_id", values="value").reset_index()
    st.plotly_chart(bland_altman_figure(wide, lim["msa"]["matching_offset_spec"]), width="stretch")
    explain("msa_matching", gi.msa_matching(res, lim["msa"]["matching_offset_spec"], lim["msa"]["matching_slope_tol"]))


def page_studies():
    st.header("Recipe development studies")
    wl = np.linspace(250, 1000, 151)
    stack, _ = load_stack("gate_oxide_thin", films_cfg())
    ts = [1, 2, 3, 5, 10, 20, 50, 100, 200]
    if st.button("Run sensitivity study (reflectometry vs SE)", help=H("study.sensitivity_run"), key="study_sens_run"):
        r = thickness_sensitivity(stack, 0, ts, wl, "reflectometry", noise=0.002)
        s = thickness_sensitivity(stack, 0, ts, wl, "se", angles=(65, 70, 75), noise=0.0007)
        st.session_state["study_sens"] = (r, s)
    if "study_sens" in st.session_state:
        r, s = st.session_state["study_sens"]
        st.plotly_chart(sensitivity_figure(r, s), width="stretch")
        explain("study_sensitivity", gi.study_sensitivity(r, s))
    if st.button("Run thickness / n correlation study (~5 s)", help=H("study.tn_run"), key="study_tn_run"):
        st.session_state["study_tn"] = thickness_n_correlation([2, 5, 10, 25, 50, 100, 200], wl)
    if "study_tn" in st.session_state:
        c = st.session_state["study_tn"]
        st.plotly_chart(tn_figure(c), width="stretch")
        st.dataframe(c.style.format(precision=4), hide_index=True,
                     column_config=col_help(c, {col: f"study.col.{col}" for col in c.columns}))
        explain("study_tn", gi.study_tn(c))

DESIGNS = {"full2": "2 水準全因子 (2^k) + 中心點", "fractional": "部分因子 2^(k-p) + 中心點",
           "ccd": "中心合成 CCD（可估彎曲）", "bbd": "Box-Behnken（可估彎曲、不跑角落）", "full3": "3 水準全因子 3^k"}
CUSTOM = "我的 DOE 結果（上傳 CSV）"


def _goal_inputs(goals: dict, key: str) -> dict:
    """Editable optimisation goals per response."""
    out = {}
    cols = st.columns(len(goals))
    for c, (r, g) in zip(cols, goals.items()):
        with c:
            st.markdown(f"**{r}** ({g.get('unit', '')})")
            kind = st.selectbox("目標", ["target", "minimize", "maximize"], key=f"{key}_{r}_goal", help=H("doe.goal"),
                                index=["target", "minimize", "maximize"].index(g["goal"]),
                                format_func={"target": "打到目標值", "minimize": "越小越好", "maximize": "越大越好"}.get)
            new = {"goal": kind, "unit": g.get("unit", "")}
            if kind == "target":
                new["target"] = st.number_input("目標值", value=float(g.get("target", 0.0)), key=f"{key}_{r}_t", format="%.4g",
                                                help=H("doe.target"))
                new["tol"] = st.number_input("容許 ±", value=float(g.get("tol", 1.0)), min_value=1e-9, key=f"{key}_{r}_tol",
                                             format="%.4g", help=H("doe.tol"))
            else:
                new["best"] = st.number_input("最佳（d = 1）", value=float(g.get("best", 0.0)), key=f"{key}_{r}_b", format="%.4g",
                                              help=H("doe.best"))
                new["worst"] = st.number_input("不可接受（d = 0）", value=float(g.get("worst", 1.0)), key=f"{key}_{r}_w",
                                               format="%.4g", help=H("doe.worst"))
            new["weight"] = st.slider("權重", 0.1, 3.0, float(g.get("weight", 1.0)), 0.1, key=f"{key}_{r}_wt",
                                      help=H("doe.weight"))
            out[r] = new
    return out



def page_doe():
    st.header("DOE / 配方最佳化 Recipe optimizer")
    st.caption("設計實驗 → 在虛擬機台上跑（或上傳自己的結果）→ 建立回應曲面模型 → 找出同時滿足膜厚目標與均勻度的配方 → "
               "確認實驗 → 對答案。虛擬機台的物理與數字都是教科書等級的示意，不是任何公司的配方。")
    procs = load_processes()
    src = st.selectbox("製程", list(procs) + [CUSTOM], format_func=lambda k: procs[k]["title"] if k in procs else k,
                       help=H("doe.process"), key="doe_process")

    if src == CUSTOM:
        up = st.file_uploader("上傳 DOE 結果 CSV（每列一次實驗：因子欄位 + 回應欄位）", type="csv", key="doe_up",
                              help=H("doe.upload"))
        st.caption("檔案只在這次瀏覽中使用，不會存檔或上傳到 GitHub。")
        if up is None:
            return
        res = pd.read_csv(up)
        num = [c for c in res.columns if pd.api.types.is_numeric_dtype(res[c])]
        names = st.multiselect("因子欄位", num, default=num[: min(3, len(num))], help=H("doe.factor_cols"), key=f"doe_factor_cols_{len(num)}")
        resp = st.multiselect("回應欄位", [c for c in num if c not in names], default=[c for c in num if c not in names][:2],
                              help=H("doe.response_cols"), key=f"doe_resp_cols_{len(num)}")
        if len(names) < 1 or not resp:
            return
        factors = {n: {"low": float(res[n].min()), "high": float(res[n].max()), "unit": ""} for n in names}
        goals0 = {r: {"goal": "minimize", "best": float(res[r].min()), "worst": float(res[r].max()), "unit": ""} for r in resp}
        proc = None
    else:
        proc = procs[src]
        factors_all = proc["factors"]
        c1, c2, c3, c4, c5 = st.columns([2, 2, 1, 1, 1])
        names = c1.multiselect("要研究的因子（其他固定在中間值）", list(factors_all), default=list(factors_all), key=f"doe_f_{src}",
                               help=H("doe.factors"))
        if not names:
            return
        kinds = [k for k in DESIGNS if not (k == "bbd" and not 3 <= len(names) <= 5)
                 and not (k == "fractional" and len(names) < 3)]
        kind = c2.selectbox("設計", kinds, index=kinds.index("ccd"), format_func=DESIGNS.get, key="doe_kind",
                            help=H("doe.design"))
        center = c3.number_input("中心點", 0, 10, 4 if kind != "full3" else 0, key="doe_center", help=H("doe.center"))
        reps = c4.number_input("重複", 1, 4, 1, key="doe_reps", help=H("doe.reps"))
        seed = c5.number_input("seed", value=1, step=1, key="doe_seed", help=H("doe.seed"))
        factors = {n: factors_all[n] for n in names}
        coded, info = make_design(kind, len(names), int(center))
        sheet = run_sheet(coded, factors, int(reps), int(seed))
        st.markdown(f"**{len(sheet)} 次實驗**（隨機順序；`__coded` 欄是 -1…+1 的編碼值）")
        if info.get("resolution"):
            st.caption(f"解析度 Resolution {info['resolution']}；{info['defining_relation']}；混淆："
                       + "、".join(f"{k} = {' = '.join(v)}" for k, v in list(info["aliases"].items())[:8]))
        if kind == "ccd":
            st.caption("面心 CCD (α = 1)：軸點落在範圍邊界上，不會超出機台允許的設定。")
        c1, c2 = st.columns([3, 1])
        c1.caption("Run sheet 實驗表", help=H("doe.sheet"))
        c1.dataframe(sheet, hide_index=True, height=220)
        c2.download_button("下載 run sheet (CSV)", sheet.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"doe_{src}_{kind}.csv", mime="text/csv", help=H("doe.download"), key="doe_download")
        key = (src, tuple(names), kind, int(center), int(reps), int(seed))
        if c2.button("在虛擬機台上執行", type="primary", help=H("doe.run"), key="doe_run_btn"):
            st.session_state["doe_run"] = (key, run_experiments(proc, sheet, seed=int(seed) + 100))
        if st.session_state.get("doe_run", (None,))[0] != key:
            st.info("按「在虛擬機台上執行」得到量測結果（含機台的 run-to-run 雜訊）。")
            return
        res = st.session_state["doe_run"][1]
        resp = list(proc["responses"])
        goals0 = proc["responses"]
        res = res.copy()

    coded_df = pd.DataFrame(to_coded(res[names].to_numpy(float), factors), columns=names)
    st.subheader("模型 Model")
    order = st.radio("模型", ["linear", "interaction", "quadratic"], index=2, horizontal=True, key="doe_order", help=H("doe.model"),
                     format_func={"linear": "線性", "interaction": "線性 + 交互作用", "quadratic": "二次（含彎曲）"}.get)
    fits = {r: fit_model(coded_df, res[r], r, order) for r in resp}
    tabs = st.tabs(resp)
    for tab, r in zip(tabs, resp):
        f = fits[r]
        with tab:
            k = st.columns(4)
            k[0].metric("R²", f"{f.r2:.3f}", help=H("doe.r2"))
            k[1].metric("調整 R² adj", "—" if np.isnan(f.r2_adj) else f"{f.r2_adj:.3f}", help=H("doe.r2_adj"))
            k[2].metric("預測 R² pred", "—" if np.isnan(f.r2_pred) else f"{f.r2_pred:.3f}", help=H("doe.r2_pred"))
            k[3].metric("殘差 RMSE", "—" if np.isnan(f.rmse) else f"{f.rmse:.3g}", help=H("doe.rmse"))
            for w in f.warnings:
                st.warning(w)
            curv = curvature_test(coded_df, res[r])
            if curv and (order != "quadratic" or f.curvature_unresolved):  # model has no curvature: test for it
                msg = (f"中心點 vs 角落點差 {curv['difference']:.3g}（p = {curv['p']:.3g}）。"
                       + ("**有明顯彎曲**：線性模型會預測錯中間區域，請改用 CCD / Box-Behnken。" if curv["p"] < 0.05
                          else "沒有明顯彎曲。"))
                (st.error if curv["p"] < 0.05 else st.caption)(msg)
            c1, c2 = st.columns([3, 2])
            c1.plotly_chart(pareto_figure(f, f"{r}：哪些因子重要（藍 = p < 0.05）"), width="stretch")
            ft = f.table.round(4)
            c2.dataframe(ft, hide_index=True, column_config=col_help(ft, {c: f"doe.col.{c}" for c in ft.columns}))
            explain("doe_pareto", gi.doe_pareto(f, curv))

    st.subheader("最佳化 Optimize")
    goals = _goal_inputs(goals0, f"doe_goal_{src}")
    pred = lambda c: pd.DataFrame({r: fits[r].predict(pd.DataFrame(c, columns=names)) for r in resp})  # noqa: E731
    best = optimize(pred, len(names), goals)
    recipe = dict(zip(names, to_real(best["coded"][None, :], factors)[0]))
    k = st.columns(len(names) + 1)
    for c, n in zip(k, names):
        c.metric(f"{n} ({factors[n].get('unit', '')})", f"{recipe[n]:.4g}", help=H("doe.factor_setting"))
    k[-1].metric("預測整體滿意度 D", f"{best['D']:.2f}", help=H("doe.D"))
    st.caption("預測回應：" + "；".join(f"{r} = {v:.4g}" for r, v in best["responses"].items())
               + "。最佳化只在實驗範圍內搜尋（不外插）。")

    if len(names) >= 2:
        c1, c2, c3 = st.columns(3)
        xa = c1.selectbox("等高線 x", names, index=0, key="doe_cx", help=H("doe.contour_x"))
        ya = c2.selectbox("等高線 y", [n for n in names if n != xa], index=0, key="doe_cy", help=H("doe.contour_y"))
        show = c3.selectbox("顯示", ["D"] + resp, key="doe_cz", help=H("doe.contour_show"),
                            format_func=lambda v: "整體滿意度 D" if v == "D" else v)
        g = np.linspace(-1, 1, 61)
        gx, gy = np.meshgrid(g, g)
        pts = np.tile(best["coded"], (gx.size, 1))
        pts[:, names.index(xa)], pts[:, names.index(ya)] = gx.ravel(), gy.ravel()
        P = pred(pts)
        z = overall(P, goals) if show == "D" else P[show].to_numpy()
        rx = to_real(pts, factors)
        others = [n for n in names if n not in (xa, ya)]
        sub = "；其他因子固定在建議值 " + "、".join(f"{n} = {recipe[n]:.3g}" for n in others) if others else ""
        fig = doe_contour_figure(rx[:61, names.index(xa)], rx[::61, names.index(ya)], z.reshape(gx.shape), show, xa, ya, res,
                                 recipe, f"{'整體滿意度 D' if show == 'D' else show}（模型預測）{sub}")
        st.plotly_chart(fig, width="stretch")
    explain("doe_contour", gi.doe_contour(best, recipe, names, factors))

    if proc is None:
        return
    st.subheader("確認實驗與答案 Confirm & answer key")
    n_conf = st.slider("確認實驗片數", 1, 10, 3, key="doe_nconf", help=H("doe.n_conf"))
    if st.button("在建議配方跑確認實驗", help=H("doe.confirm"), key="doe_confirm_run"):
        conf_sheet = pd.DataFrame({n: [recipe[n]] * n_conf for n in names})
        fixed = {n: (f["low"] + f["high"]) / 2 for n, f in proc["factors"].items() if n not in names}
        st.session_state["doe_conf"] = (key, recipe, run_experiments(proc, conf_sheet, fixed, seed=int(seed) + 999))
    stored = st.session_state.get("doe_conf", (None,))
    if stored[0] == key and all(abs(stored[1][n] - recipe[n]) <= 1e-9 * max(1.0, abs(recipe[n])) for n in names):
        _, rec, conf = stored  # only while the suggested recipe is the one the wafers were run at
        rows = []
        for r in resp:
            m = conf[r].mean()
            ok = desirability([m], goals[r])[0] > 0
            rows.append({"回應": r, "預測": best["responses"][r], "確認平均": m, "確認標準差": conf[r].std(ddof=1),
                         "可接受": "✓" if ok else "✗"})
        conf_tab = pd.DataFrame(rows)
        st.dataframe(conf_tab.round(4), hide_index=True)
        st.caption("預測和確認差很多 → 模型在這一區不準（例如二次模型描述不了的物理），要在新的中心附近再做一次小 DOE。")
        explain("doe_confirm", gi.doe_confirm(conf_tab, fits))
    with st.expander("看答案 Answer key（真實的最佳配方）"):
        fixed = {n: (f["low"] + f["high"]) / 2 for n, f in proc["factors"].items() if n not in names}
        true_proc = dict(proc, responses=goals)
        opt = true_optimum(true_proc, names, fixed)
        mine = evaluate_recipe(true_proc, {**fixed, **recipe})
        c1, c2 = st.columns(2)
        c1.markdown("**真實最佳配方**（無雜訊的真實曲面）")
        c1.dataframe(pd.DataFrame({"factor": names, "最佳": [opt["settings"][n] for n in names],
                                   "你的建議": [recipe[n] for n in names]}).round(4), hide_index=True)
        c2.markdown("**真實回應**")
        c2.dataframe(pd.DataFrame({"response": resp, "最佳配方": [opt["responses"][r] for r in resp],
                                   "你的建議": [mine["responses"][r] for r in resp]}).round(4), hide_index=True)
        ratio = mine["D"] / opt["D"] if opt["D"] > 0 else float("nan")
        st.metric(f"你的配方真實滿意度（真實最佳 = {opt['D']:.2f}）", f"{mine['D']:.2f}", help=H("doe.true_D"))
        st.caption(f"= 真實最佳的 {100 * ratio:.0f} %。" if np.isfinite(ratio) else "")
        st.caption("虛擬機台的真實物理：" + (
            "ALD 溫度視窗外 GPC 上升（低溫凝結、高溫分解）；清洗太短會殘留前驅物 → 寄生 CVD → 變厚又不均勻；清洗越久越慢。"
            if proc["physics"] == "ald" else
            "低溫為反應控制（Arrhenius，加熱器溫度分布影響均勻度）；高溫變成質傳控制（受壓力限制，氣體沿晶圓耗盡 → 不均勻）。"))


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


SETUP_COLOR = {n: viz.SERIES[i] for i, n in enumerate(CHART_SETUPS)}  # fixed: colour follows the chart setup


def compare_view(summ_df: pd.DataFrame, delays: pd.DataFrame):
    """Speed-vs-false-alarm scatter, per-event delay bars and the summary table."""
    c1, c2 = st.columns(2)
    fig = go.Figure()
    for _, r in summ_df.iterrows():  # points can sit close together: legend + hover instead of direct labels
        delay = r["median_delay_wafers"]
        fig.add_scatter(x=[r["false_alarm_rate_pct"]], y=[delay], mode="markers", name=r["setup"],
                        marker=dict(size=12, color=SETUP_COLOR.get(r["setup"], viz.SERIES[0]),
                                    line=dict(color=viz.SURFACE, width=2)),
                        hovertemplate=f"{r['setup']}<br>誤警報 false alarms %{{x:.1f}}%<br>中位延遲 median delay %{{y}} 片"
                                      f"<br>抓到 detected {r['detected']}/{r['observable']}<extra></extra>")
    fig = layout(fig, "速度 vs 誤警報（越靠左下越好）", "誤警報率 false-alarm rate (%)", "中位延遲 median delay（片）", 480)
    fig.update_layout(margin=dict(t=120))
    fig.update_xaxes(rangemode="tozero")
    fig.update_yaxes(rangemode="tozero")
    c1.plotly_chart(fig, width="stretch")
    explain("fab_tradeoff", gi.fab_tradeoff(summ_df), where=c1)

    d = delays.copy()
    d["event"] = d["id"] + " " + d["type"]
    fig = go.Figure()
    for setup in summ_df["setup"]:
        sub = d[d["setup"] == setup]
        label = [("未抓到 missed" if st_ == "missed" else "量測不到 not observable") if pd.isna(dl) else f"{dl:.0f}"
                 for dl, st_ in zip(sub["delay_wafers"], sub["status"])]
        fig.add_bar(y=sub["event"], x=sub["delay_wafers"].fillna(0), orientation="h", name=setup,
                    text=label, textposition="outside", textfont=dict(color=viz.INK_2, size=10), cliponaxis=False,
                    marker_color=SETUP_COLOR.get(setup, viz.SERIES[0]), customdata=sub["status"],
                    hovertemplate=f"{setup}<br>%{{y}}: 延遲 delay %{{x}} 片<br>%{{customdata}}<extra></extra>")
    fig = layout(fig, "每個事件的偵測延遲（0 = 第一片受影響的量測晶圓就抓到）", "延遲 delay（片 measured wafers）", "", 480)
    fig.update_layout(margin=dict(t=120))
    fig.update_layout(barmode="group", bargap=0.2, bargroupgap=0.05, uniformtext=dict(minsize=10, mode="show"))
    fig.update_yaxes(autorange="reversed")
    c2.plotly_chart(fig, width="stretch")
    explain("fab_event_delay", gi.fab_event_delay(delays), where=c2)

    show = summ_df[["setup", "detected", "observable", "median_delay_wafers", "false_alarm_rate_pct", "flagged_points"]]
    st.dataframe(show.rename(columns={"setup": "設定", "detected": "抓到", "observable": "可觀測",
                                      "median_delay_wafers": "中位延遲(片)", "false_alarm_rate_pct": "誤警報 %",
                                      "flagged_points": "被標記點"}).round(1), hide_index=True)
    fast = summ_df.dropna(subset=["median_delay_wafers"])
    if len(fast):
        best = fast.sort_values(["median_delay_wafers", "false_alarm_rate_pct"]).iloc[0]
        quiet = summ_df.sort_values("false_alarm_rate_pct").iloc[0]
        st.caption(f"最快：**{best['setup']}**；最安靜：**{quiet['setup']}**。實務上要在「早一點發現」與"
                   "「少一點誤停機」之間取捨；小而持續的漂移通常是 EWMA / CUSUM 的強項，大的突跳 I-MR 就夠快。")


@st.cache_resource(show_spinner="訓練圖樣分類器（用另一組模擬晶圓）…")
def trained_classifier(seed: int):
    """Train on a separate pattern-rich simulation, so the scored dataset is never seen in training."""
    train = simulate_fab(load_fab_config(), "pattern_zoo", 40, seed + 1000)
    geo = GridGeometry.from_grid(train.grid, train.config["die_mm"])
    feats = feature_table(train.dies, geo)
    labels = train.wafers.set_index("wafer_id").loc[feats["wafer_id"], "defect_pattern"].to_numpy()
    return PatternClassifier().fit(feats, labels), geo


def pattern_section(truth: dict, seed: int, key: str):
    st.subheader("晶圓圖樣分類 Wafer-map patterns")
    st.caption("只看「缺陷」造成的失效晶粒，算出幾個看得懂的特徵（徑向分布、直線、群聚），再用另一組模擬晶圓訓練的"
               "最近中心分類器判斷圖樣，最後和答案比對。")
    min_def = st.slider("最少缺陷晶粒數（少於這個數就判為 random）", 0, 40, 16, key="pat_min", help=H("pat.min_defects"))
    run = st.button("分類並打分數", key="pat_run", help=H("pat.run"))
    if not run and st.session_state.get("pat_result", (None,))[0] != key:
        return
    clf, geo = trained_classifier(seed)
    if len(geo.x) != len(truth["grid"]["x"]):
        st.warning("這份資料的晶粒尺寸和訓練資料不同，無法分類。")
        return
    clf.min_defects = min_def
    if run or st.session_state.get("pat_result", (None,))[0] != key:
        feats = feature_table(truth["dies"], geo)
        pred = clf.predict(feats)
        conf = clf.confidence(feats)
        st.session_state["pat_result"] = (key, feats, pred, conf)
    _, feats, _, conf = st.session_state["pat_result"]
    pred = clf.predict(feats)  # cheap; follows the slider without recomputing features
    true = truth["wafers"].set_index("wafer_id").loc[feats["wafer_id"], "defect_pattern"].to_numpy()
    ev = evaluate(true, pred)

    k = st.columns(3)
    k[0].metric("正確率 accuracy", f"{100 * ev['accuracy']:.1f} %", help=H("pat.m_accuracy"))
    k[1].metric("有圖樣的晶圓", f"{int((true != 'random').sum())} / {len(true)}", help=H("pat.m_n_pattern"))
    nonrandom = true != "random"
    k[2].metric("有圖樣晶圓的召回", f"{100 * (pred[nonrandom] == true[nonrandom]).mean():.0f} %" if nonrandom.any() else "—",
                help=H("pat.m_recall"))

    c1, c2 = st.columns([3, 2])
    cm = ev["confusion"]
    pct = cm.div(cm.sum(axis=1).replace(0, 1), axis=0) * 100
    fig = go.Figure(go.Heatmap(z=pct.to_numpy(), x=list(cm.columns), y=list(cm.index), zmin=0, zmax=100,
                               colorscale=viz.PLOTLY_SEQ,
                               customdata=cm.to_numpy(), text=cm.to_numpy(), texttemplate="%{text}",
                               xgap=2, ygap=2, colorbar=dict(title="% of row"),
                               hovertemplate="真實 truth %{y} → 判為 predicted %{x}<br>%{customdata} 片 wafers"
                                             "（%{z:.0f}% of row）<extra></extra>"))
    fig = layout(fig, "混淆矩陣（列 = 真實，欄 = 判斷；數字 = 晶圓數）", "判斷 predicted", "真實 truth", 380)
    fig.update_yaxes(autorange="reversed")
    c1.plotly_chart(fig, width="stretch")
    pc = ev["per_class"].assign(recall=lambda d: (100 * d.recall).round(0), precision=lambda d: (100 * d.precision).round(0))
    c2.dataframe(pc, hide_index=True, column_config=col_help(pc, {c: f"pat.col.{c}" for c in pc.columns}))
    c2.markdown("\n".join(f"- **{p}**：{t}" for p, t in PATTERN_TEXT.items()))
    explain("fab_patterns", gi.fab_patterns(ev, true, pred, min_def), where=c1)

    wrong = feats["wafer_id"][pred != true].tolist()
    options = wrong or feats["wafer_id"].tolist()
    wid = st.selectbox("看晶圓的缺陷圖（判錯的在清單中）" if wrong else "看晶圓的缺陷圖", options, key="pat_wafer",
                       help=H("pat.wafer"))
    i = int(np.flatnonzero(feats["wafer_id"].to_numpy() == wid)[0])
    m = truth["dies"].set_index("wafer_id").loc[wid, "map"]
    f = fail_vector(m).astype(bool)
    fig = go.Figure()
    fig.add_scatter(x=geo.x[~f], y=geo.y[~f], mode="markers", name="other dies 其他晶粒", hoverinfo="skip",
                    marker=dict(symbol="square", size=9, color=viz.GRID))
    fig.add_scatter(x=geo.x[f], y=geo.y[f], mode="markers", name=f"defect fails 缺陷失效 ({f.sum()})",
                    marker=dict(symbol="square", size=9, color=CAUSE_COLOR["D"]),
                    hovertemplate="defect fail 缺陷失效<br>x %{x:.0f} mm, y %{y:.0f} mm<extra></extra>")
    r = geo.r_eff + 3
    fig.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r, line=dict(color=viz.AXIS))
    legend_line(fig, "wafer edge 晶圓邊緣", viz.AXIS)
    fig = layout(fig, f"{wid}  真實：{true[i]}  · 判斷：{pred[i]}  · 信心 {conf[i]:.2f}", "x (mm)", "y (mm)", 480)
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(fig, width="stretch")
    ft = feats.iloc[[i]].drop(columns="wafer_id").T.rename(columns={feats.index[i]: "value"}).round(3)
    ft.insert(0, "feature", ft.index)
    ft["說明 meaning"] = [(H(f"pat.feat.{n}") or "").split("\n")[0][:90] for n in ft["feature"]]
    c2.dataframe(ft, hide_index=True)
    c2.caption("line_score 高 → 刮痕；peak_score 高、neighbour_ratio 高 → 群聚；ring_4 / edge_center 高 → 邊緣環；"
               "ring_0 高 → 中心。缺陷很少的晶圓特徵很吵，容易被誤判。")
    explain("fab_defect_map", gi.fab_defect_map(wid, true[i], pred[i], float(conf[i]), int(f.sum())), where=c1)


def page_fab():
    st.header("Fab simulator 模擬晶圓廠")
    st.caption("產生行為接近真實晶圓廠的資料，並保留「答案」。先用 Wafer map / SPC 頁面自己找問題，再回來對答案、打分數。")
    cfg = load_fab_config()
    c1, c2, c3 = st.columns([2, 1, 1])
    scenario = c1.selectbox("情境 Scenario", list(cfg["scenarios"]), index=list(cfg["scenarios"]).index("mixed"),
                            format_func=lambda k: f"{k} — {SCENARIO_TEXT.get(k, '')}", help=H("fab.scenario"), key="fab_scenario")
    lots = c2.slider("批數 lots", 20, 120, int(cfg["n_lots"]), 5, help=H("fab.lots"), key="fab_lots")
    seed = c3.number_input("亂數種子 seed", value=int(cfg["seed"]), step=1, help=H("fab.seed"), key="fab_seed")
    c4, c5 = st.columns([2, 1])
    name = c4.text_input("資料集名稱", value=f"sim_{scenario}", help=H("fab.name"), key=f"fab_name_{scenario}")
    sy = c5.checkbox("用 SemiYield 欄位名稱", value=False, help=H("fab.sy_names"), key="fab_sy_names")
    if st.button("產生並儲存", type="primary", help=H("fab.generate"), key="fab_generate"):
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
    pick = st.selectbox("檢視的模擬資料", sims, index=sims.index(active) if active in sims else 0, help=H("fab.pick"), key=f"fab_pick_{active}")
    truth = load_truth(pick)
    w = truth["wafers"]
    long_df = load_dataset(pick)

    k = st.columns(5)
    k[0].metric("晶圓", f"{len(w):,}", help=H("fab.m_wafers"))
    k[1].metric("批", w["lot_id"].nunique(), help=H("fab.m_lots"))
    k[2].metric("平均良率", f"{100 * w['yield'].mean():.1f} %", help=H("fab.m_mean_yield"))
    k[3].metric("良率標準差", f"{100 * w['yield'].std():.1f} %", help=H("fab.m_yield_sd"))
    k[4].metric("注入事件", len(truth["events"]), help=H("fab.m_events"))

    st.plotly_chart(yield_trend_figure(w), width="stretch")
    explain("fab_yield_trend", gi.fab_yield_trend(w))

    st.subheader("晶圓圖 Die map")
    order = w.sort_values("yield")["wafer_id"].tolist()
    wid = st.selectbox("晶圓（良率最低的在前）", order, help=H("fab.wafer_select"), key=f"fab_wafer_{pick}")
    m = truth["dies"].set_index("wafer_id").loc[wid, "map"]
    gx, gy = np.array(truth["grid"]["x"]), np.array(truth["grid"]["y"])
    codes = np.array(list(m))
    row = w.set_index("wafer_id").loc[wid]
    fig = die_map_figure(codes, gx, gy, truth["grid"]["r_eff"],
                         f"{wid}  良率 {100 * row['yield']:.1f}%  · 缺陷圖樣：{row['defect_pattern']}")
    st.plotly_chart(fig, width="stretch")
    cause_step = {s_["code"]: s_["name"] for s_ in cfg["steps"]} | {"D": cfg["defects"].get("inspection_step", "—")}
    explain("fab_die_map", gi.fab_die_map(row, codes, gx, gy, truth["grid"]["r_eff"], w, CAUSE_NAME, cause_step))

    pattern_section(truth, int(seed), pick)

    st.subheader("偵測打分數 Score my detection")
    st.caption("用你選的管制圖設定跑一次 SPC（每個參數、每個 chamber 分開），再和答案比對。")
    c1, c2, c3, c4 = st.columns(4)
    chart = c1.radio("管制圖", ["IMR", "EWMA", "CUSUM"], horizontal=True, key="fab_chart", help=H("spc.chart"))
    rules = c2.multiselect("WE 規則", [1, 2, 3, 4], default=[1, 2], key="fab_rules", help=H("spc.rules"))
    stats = c3.multiselect("統計量", ["mean", "nu_1sigma_pct"], default=["mean", "nu_1sigma_pct"], key="fab_stats",
                           format_func={"mean": "晶圓平均", "nu_1sigma_pct": "片內 1σ %"}.get, help=H("spc.stat"))
    phase1 = c4.slider("Phase I 點數", 8, 40, 20, key="fab_phase1", help=H("spc.phase1"))
    opts = {}
    if chart == "EWMA":
        opts["ewma_lambda"] = st.slider("EWMA λ（越小越重視歷史、越能抓小漂移）", 0.05, 1.0, 0.2, 0.05, key="fab_lam",
                                        help=H("spc.ewma_lambda"))
    elif chart == "CUSUM":
        c1, c2 = st.columns(2)
        opts["cusum_k"] = c1.slider("CUSUM k（σ；要抓的偏移的一半）", 0.25, 1.5, 0.5, 0.25, key="fab_k", help=H("spc.cusum_k"))
        opts["cusum_h"] = c2.slider("CUSUM h（σ；決策界限）", 2.0, 8.0, 5.0, 0.5, key="fab_h", help=H("spc.cusum_h"))
    if chart != "IMR":
        st.caption("EWMA / CUSUM 有自己的判定規則，WE 規則只用在 I-MR。")
    if st.button("計算分數", help=H("fab.score"), key="fab_score_run"):
        flags = spc_flags(long_df, chart, tuple(rules) or (1,), tuple(stats) or ("mean",), phase1, chart_opts=opts)
        table, summ = score_detection(flags, truth["events"], long_df)
        st.session_state["fab_score"] = (pick, table, summ)
    if st.session_state.get("fab_score") and st.session_state["fab_score"][0] == pick:
        _, table, summ = st.session_state["fab_score"]
        k = st.columns(4)
        k[0].metric("抓到的事件", f"{summ['detected']} / {summ['observable']}", help=H("fab.m_detected"))
        k[1].metric("中位延遲", "—" if summ["median_delay_wafers"] is None else f"{summ['median_delay_wafers']:.0f} 片",
                    help=H("fab.m_delay"))
        k[2].metric("誤警報率", f"{summ['false_alarm_rate_pct']:.1f} %", help=H("fab.m_false_alarm"))
        k[3].metric("被標記的點", summ["flagged_points"], help=H("fab.m_flagged"))
        with st.expander("看每個事件的結果（會顯示答案）"):
            et = table.drop(columns=["affects_product"]).round(2)
            st.dataframe(et, hide_index=True, column_config=col_help(et, {c: f"fab.col.{c}" for c in et.columns}))

    st.subheader("管制圖比較 Compare charts")
    st.caption("同一份資料、同樣的統計量與 Phase I，用四種常見設定各跑一次：誰抓得快？誰誤警報多？"
               "（延遲 = 事件開始後第幾片被量測到的受影響晶圓才被標記）")
    if st.button("比較管制圖", help=H("fab.compare"), key="fab_compare_run"):
        with st.spinner("計算中…"):
            summ_df, delays = compare_charts(long_df, truth["events"], stats=tuple(stats) or ("mean",), phase1=phase1)
        st.session_state["fab_compare"] = (pick, summ_df, delays)
    if st.session_state.get("fab_compare") and st.session_state["fab_compare"][0] == pick:
        _, summ_df, delays = st.session_state["fab_compare"]
        compare_view(summ_df, delays)

    with st.expander("看答案 Answer key"):
        ev = truth["events"].drop(columns=["wafer_ids"]).copy()
        ev["yield_impact"] = (100 * ev["yield_impact"]).round(2)
        st.markdown("**注入的事件**（yield_impact = 與「同一批晶圓、同樣亂數但沒有事件」相比的良率差，%）")
        st.dataframe(ev.rename(columns={"yield_impact": "yield_impact_%"}), hide_index=True)
        drv = truth["drivers"]
        fig = go.Figure(go.Bar(x=drv["yield_loss_pct"], y=drv["cause"], orientation="h", marker_color=viz.SERIES[0],
                               name="true yield loss 真實良率損失",
                               hovertemplate="%{y}: 平均損失 mean loss %{x:.2f} pp<extra></extra>"))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(layout(fig, "真正的良率損失來源（拿來和 SHAP / 相關性排名比對）", "平均良率損失 mean yield loss (pp)", "", 300),
                        width="stretch")
        corr_rank, cmp = None, None
        st.caption("缺陷圖樣：" + "、".join(f"{k} {v}" for k, v in w["defect_pattern"].value_counts().items()))
        back = {b: a for a, b in (truth.get("renamed") or {}).items()}
        wt = long_df.assign(parameter=long_df["parameter"].replace(back)).pivot_table(
            index="wafer_id", columns="parameter", values="value", aggfunc="mean")
        causes = [c for c in drv["cause"] if c in wt.columns and c != "yield"]
        if "yield" in wt.columns and causes:
            corr = wt[causes + ["yield"]].corr(method="spearman")["yield"].drop("yield").abs().sort_values(ascending=False)
            cmp = compare_drivers(list(corr.index), drv)
            corr_rank = list(corr.index)
            st.markdown(
                f"**簡單相關性排名 vs 真正原因**：相關性排名 {' > '.join(corr.index)}；"
                f"真正原因 {' > '.join(cmp['truth'])}。第一名{'相同' if cmp['top1_match'] else '不同'}"
                + (f"，排名相關 ρ = {cmp['spearman']:.2f}" if cmp["spearman"] is not None else "")
                + "。相關性只看量測過的晶圓與晶圓平均值，可能漏掉只在部分晶粒發生的問題。")
        if truth.get("semiyield_names"):
            st.caption("此資料集使用 SemiYield 欄位名稱：" + "、".join(f"{a} → {b}" for a, b in truth["renamed"].items()))
        explain("fab_drivers", gi.fab_drivers(drv, corr_rank, cmp), inline=True)


# --------------------------------------------------------------------------- Case study
@st.cache_resource(max_entries=6, show_spinner="產生案例 Generating the case…")
def cached_case(case_id: str):
    from metro_toolkit import cases

    return cases.generate(case_id)


def bi(zh: str, en: str) -> str:
    """Text in the chosen guide language (both: zh then en in italics)."""
    from metro_toolkit.guide.render import lang

    return {"zh": zh, "en": en}.get(lang(), f"{zh}  \n*{en}*")


def render_evidence(ev: dict, key: str):
    """Draw one evidence item of a case with the same charts as the other pages."""
    kind = ev["kind"]
    if ev.get("title"):
        st.markdown(f"**{ev['title']}**")
    if kind == "spc":
        wafers, group = ev["wafers"], ev["group"]
        charts = spc_by_group(wafers, group, ev["stat"], ev["chart"], ev["phase1"])
        colors = viz.color_map(wafers[group]) if wafers[group].nunique() <= len(viz.SERIES) else {
            g: viz.SERIES[0] for g in wafers[group].unique()}
        cols = st.columns(2)
        for i, (g, ch) in enumerate(charts.items()):
            sw = wafers[wafers[group] == g].sort_values("timestamp")
            cols[i % 2].plotly_chart(spc_figure(g, sw, ch, ev["stat"], colors[g], ev["phase1"]), width="stretch",
                                     key=f"{key}_spc_{i}")
        if ev["stat"] == "mean" and ev.get("lsl") is not None:
            cap = pd.DataFrame([{group: g, **process_capability(gw["mean"], ev["lsl"], ev["usl"])}
                                for g, gw in wafers.groupby(group)])
            st.caption(f"Capability (LSL {ev['lsl']}, USL {ev['usl']})")
            st.dataframe(cap.style.format(precision=3), hide_index=True,
                         column_config=col_help(cap, {c: f"cap.{c}" for c in cap.columns}))
    elif kind == "wafer":
        w, um = ev["w"], ev["um"]
        k = st.columns(4)
        k[0].metric("mean", f"{um['mean']:.4g}", help=H("wafer.mean"))
        k[1].metric("1σ NU", f"{um['nu_1sigma_pct']:.3f} %", help=H("wafer.nu"))
        k[2].metric("range", f"{um['range']:.4g}", help=H("wafer.range"))
        k[3].metric("sites", um["n_sites"], help=H("wafer.sites"))
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(wafer_map_figure(w, um, "absolute", f"{w.wafer_id.iloc[0]}  ({w.chamber_id.iloc[0]})"),
                        width="stretch", key=f"{key}_map")
        c2.plotly_chart(zernike_figure(ev["zk"]), width="stretch", key=f"{key}_zk")
        c2.plotly_chart(radial_figure(ev["rp"]), width="stretch", key=f"{key}_rp")
    elif kind == "fit":
        res = ev["res"]
        figs = fit_figures(ev["technique"], ev["wl"], ev["meas"], res.stack, ev.get("angles"))
        for i, (col, fig) in enumerate(zip(st.columns(len(figs)), figs)):
            col.plotly_chart(fig, width="stretch", key=f"{key}_fit_{i}")
        c1, c2 = st.columns([2, 1])
        c1.dataframe(ev["table"].style.format(precision=4), hide_index=True)
        c2.metric("reduced χ²", f"{res.chi2_red:.2f}", help=H("stack.chi2"))
        if len(res.labels) > 1:
            c2.caption("Parameter correlation", help=H("stack.corr"))
            c2.dataframe(pd.DataFrame(res.correlation, index=res.labels, columns=res.labels).style.format(precision=3))
        if ev.get("notes"):
            st.caption(bi(ev["notes"]["zh"], ev["notes"]["en"]))
    elif kind == "grr":
        g = ev["g"]
        k = st.columns(4)
        k[0].metric("%GRR (study var)", f"{g['pct_study_var']['gauge_rr']:.1f} %", help=H("msa.grr"))
        k[1].metric("P/T", f"{g['pct_tolerance']['gauge_rr']:.1f} %", help=H("msa.pt"))
        k[2].metric("ndc", g["ndc"], help=H("msa.ndc"))
        k[3].metric("verdict", g["verdict"], help=H("msa.verdict"))
        st.plotly_chart(grr_figure(g), width="stretch", key=f"{key}_grr")
    elif kind == "matching":
        res = ev["res"]
        st.dataframe(res.style.format(precision=4), hide_index=True,
                     column_config=col_help(res, {c: f"msa.col.{c}" for c in res.columns}))
        st.plotly_chart(bland_altman_figure(ev["wide"], ev["spec"]), width="stretch", key=f"{key}_ba")
    elif kind == "sensitivity":
        st.plotly_chart(sensitivity_figure(ev["r"], ev["s"]), width="stretch", key=f"{key}_sens")
        st.dataframe(ev["table"].style.format(precision=4), hide_index=True)
    elif kind == "doe":
        f = ev["fit"]
        k = st.columns(4)
        k[0].metric("R²", f"{f.r2:.3f}", help=H("doe.r2"))
        k[1].metric("調整 R² adj", "—" if np.isnan(f.r2_adj) else f"{f.r2_adj:.3f}", help=H("doe.r2_adj"))
        k[2].metric("預測 R² pred", "—" if np.isnan(f.r2_pred) else f"{f.r2_pred:.3f}", help=H("doe.r2_pred"))
        k[3].metric("殘差 RMSE", "—" if np.isnan(f.rmse) else f"{f.rmse:.3g}", help=H("doe.rmse"))
        for w_ in f.warnings:
            st.warning(w_)
        c1, c2 = st.columns([3, 2])
        c1.plotly_chart(pareto_figure(f, f"{f.response}：哪些因子重要（藍 = p < 0.05）"), width="stretch", key=f"{key}_par")
        c2.dataframe(f.table.round(4), hide_index=True)
        with st.expander("實驗表 Run sheet"):
            st.dataframe(ev["runs"], hide_index=True)
    elif kind == "doe_contour":
        names, factors, best, recipe = ev["names"], ev["factors"], ev["best"], ev["recipe"]
        pred = lambda c: pd.DataFrame({r: f.predict(pd.DataFrame(c, columns=names)) for r, f in ev["fits"].items()})  # noqa: E731
        xa, ya = "cycles", "temp_c"
        g = np.linspace(-1, 1, 61)
        gx, gy = np.meshgrid(g, g)
        pts = np.tile(best["coded"], (gx.size, 1))
        pts[:, names.index(xa)], pts[:, names.index(ya)] = gx.ravel(), gy.ravel()
        z = overall(pred(pts), ev["goals"])
        rx = to_real(pts, factors)
        k = st.columns(len(names) + 1)
        for c, n in zip(k, names):
            c.metric(f"{n} ({factors[n].get('unit', '')})", f"{recipe[n]:.4g}", help=H("doe.factor_setting"))
        k[-1].metric("預測整體滿意度 D", f"{best['D']:.2f}", help=H("doe.D"))
        st.plotly_chart(doe_contour_figure(rx[:61, names.index(xa)], rx[::61, names.index(ya)], z.reshape(gx.shape), "D",
                                           xa, ya, ev["runs"], recipe, "整體滿意度 D（模型預測）"), width="stretch",
                        key=f"{key}_ct")
    elif kind == "yield_trend":
        st.plotly_chart(yield_trend_figure(ev["w"]), width="stretch", key=f"{key}_yt")
    elif kind == "die_map":
        st.plotly_chart(die_map_figure(ev["codes"], ev["gx"], ev["gy"], ev["r_eff"], ev["title"]), width="stretch",
                        key=f"{key}_dm")


def page_case():
    from metro_toolkit import cases
    from metro_toolkit.guide.render import lang

    st.header("Case study 案例練習")
    st.caption(bi("隨機產生一個真實情境：先讀交接內容與資料，判斷原因、第一步處置、產品處置、要通知誰，並寫一則訊息；"
                  "送出後看標準答案、理由、各角色的範例訊息與分數。所有資料都是合成的練習資料。",
                  "A random, realistic situation: read the handover and the data, decide the cause, the first action, the "
                  "disposition and who to notify, and write one message; then see the model answers, the reasoning, model "
                  "messages for every role and your score. All data is synthetic practice data."))
    lib = cases.library()
    domains = ["all"] + list(lib["domains"])
    c1, c2, c3 = st.columns([2, 2, 1])
    domain = c1.selectbox("範圍 Domain", domains, key="case_domain", help=H("case.domain"),
                          format_func=lambda d: "全部 All" if d == "all" else bi(lib["domains"][d]["zh"], lib["domains"][d]["en"]).replace("  \n", " · "))
    level = c2.selectbox("難度 Level", ["random", *cases.LEVELS], key="case_level", help=H("case.level"),
                         format_func={"random": "隨機 random", "basic": "基礎 basic", "intermediate": "中級 intermediate",
                                      "advanced": "進階 advanced"}.get)
    c3.write("")
    if c3.button("🎲 隨機案例", type="primary", key="case_new", help=H("case.new")):
        case = cases.random_case(None, None if domain == "all" else domain, None if level == "random" else level)
        st.session_state["case_id"] = case.id
    with st.expander("用案例編號重練 · Replay a case by its ID"):
        rc1, rc2 = st.columns([3, 1])
        typed = rc1.text_input("案例編號 Case ID", key="case_replay_id", help=H("case.replay"),
                               placeholder="spc_chamber_shift-I-04217")
        if rc2.button("載入 Load", key="case_replay"):
            try:
                cases.parse_id(typed)
                st.session_state["case_id"] = typed.strip()
            except (ValueError, KeyError):
                st.error(bi("案例編號格式不對（例：spc_chamber_shift-I-04217）。", "Not a valid case ID (e.g. spc_chamber_shift-I-04217)."))

    cid = st.session_state.get("case_id")
    if not cid:
        st.info(bi(f"按「🎲 隨機案例」開始。共有 {len(lib['cases'])} 種案例、3 種難度，每次的數值、機台與時間都不同。",
                   f"Press 🎲 to start. There are {len(lib['cases'])} case types and 3 levels; numbers, tools and timing "
                   "change every time."))
        case_history()
        return
    case = cached_case(cid)
    dom = lib["domains"][case.spec["domain"]]
    st.subheader(bi(case.text("title", "zh"), case.text("title", "en")).replace("  \n", " · "))
    st.caption(f"{cid} · {bi(dom['zh'], dom['en']).replace('  ' + chr(10), ' · ')} · {case.level}")
    st.info(bi(case.text("brief", "zh"), case.text("brief", "en")))

    st.markdown("#### 證據 Evidence")
    for i, ev in enumerate(case.evidence):
        render_evidence(ev, f"case_{cid}_{i}")

    answers_key = f"case_answers_{cid}"
    st.markdown("#### 你的判斷 Your call")
    roles = list(lib_roles())
    with st.form(f"case_form_{cid}"):
        def opt_fmt(q):
            return lambda o: bi(case.option_text(q, o, "zh"), case.option_text(q, o, "en")).replace("  \n", " · ")

        cause = st.radio("1. 根本原因最可能是？ Most likely root cause?", case.options["cause"], index=None,
                         format_func=opt_fmt("cause"), key=f"q_cause_{cid}", help=H("case.q_cause"))
        action = st.radio("2. 第一步要做什麼？ First action?", case.options["action"], index=None,
                          format_func=opt_fmt("action"), key=f"q_action_{cid}", help=H("case.q_action"))
        decision = st.radio("3. 產品／結論怎麼處置？ Disposition / decision?", case.options["decision"], index=None,
                            format_func=opt_fmt("decision"), key=f"q_decision_{cid}", help=H("case.q_decision"))
        notify = st.multiselect("4. 要通知誰？（可複選；不需升級就不選） Who to notify? (none = e-log only)", roles,
                                key=f"q_notify_{cid}", help=H("case.q_notify"),
                                format_func=lambda r: cases.role_name(r, "zh" if lang() != "en" else "en"))
        target = case.spec["message_role"]
        message = st.text_area(f"5. 寫給 {cases.role_name(target, 'zh')} · {cases.role_name(target, 'en')} 的訊息 "
                               "Your message", key=f"q_msg_{cid}", height=140, help=H("case.message"))
        submitted = st.form_submit_button("送出並看答案 Submit and see the answers", type="primary", help=H("case.submit"))
    if submitted:
        if None in (cause, action, decision):
            st.warning(bi("請先回答 1–3 題。", "Please answer questions 1–3 first."))
        else:
            st.session_state[answers_key] = {"cause": cause, "action": action, "decision": decision,
                                             "notify": notify, "message": message}
            st.session_state[f"case_saved_{cid}"] = []  # a new attempt: nothing of it saved yet
    if answers_key in st.session_state:
        case_debrief(case, st.session_state[answers_key])


def lib_roles():
    from metro_toolkit.guide import meta

    return meta()["roles"]


def case_debrief(case, answers: dict):
    from metro_toolkit import cases
    from metro_toolkit.guide.render import _langs

    result = cases.score(case, answers)
    st.markdown("---")
    st.markdown("#### 答案與講評 Debrief")
    k = st.columns(5)
    k[0].metric("總分 Score", f"{result['total']:.0f} / 100", help=H("case.score"))
    names = {"cause": "原因 cause", "action": "第一步 action", "decision": "處置 decision", "notify": "通知 notify"}
    for col, q in zip(k[1:], ("cause", "action", "decision", "notify")):
        r = result["questions"][q]
        col.metric(f"{'✓' if r['ok'] else '✗'} {names[q]}", f"{r['points']:.0f} / {r['max']}")
    for q, title in (("cause", "根本原因 Root cause"), ("action", "第一步處置 First action"), ("decision", "處置 Disposition")):
        r = result["questions"][q]
        mark = "✓" if r["ok"] else "✗"
        st.markdown(f"**{mark} {title}**：" + bi(case.option_text(q, r["correct"], "zh"), case.option_text(q, r["correct"], "en"))
                    .replace("  \n", " · "))
    n = result["questions"]["notify"]
    right = ", ".join(cases.role_name(r, "zh") for r in n["correct"]) or "不需升級（e-log 記錄即可） no escalation, e-log only"
    extra = (f"；漏了 missed: {', '.join(cases.role_name(r, 'zh') for r in n['missing'])}" if n["missing"] else "") + \
            (f"；多了 extra: {', '.join(cases.role_name(r, 'zh') for r in n['extra'])}" if n["extra"] else "")
    st.markdown(f"**{'✓' if n['ok'] else '△'} 通知 Notify**：{right}{extra}")
    st.markdown("**為什麼 Why**")
    for lg in _langs():
        st.markdown(case.text("explanation", lg) if lg == "zh" or len(_langs()) == 1 else f"*{case.text('explanation', lg)}*")

    target = case.spec["message_role"]
    st.markdown(f"**給 {cases.role_name(target, 'zh')} 的訊息 · Message to {cases.role_name(target, 'en')}**")
    c1, c2 = st.columns(2)
    c1.caption("你寫的 Yours")
    c1.code(answers.get("message") or "—", language=None, wrap_lines=True)
    c2.caption("範例 Model message")
    for lg in _langs():
        c2.code(case.text("model_message", lg), language=None, wrap_lines=True)
    st.caption("好訊息的要點 What a good message covers")
    for lg in _langs():
        for item, ok in cases.message_checklist(case, answers.get("message", ""), lg):
            st.markdown(f"- {'✓' if ok else '✗'} {item}")

    st.markdown("**每張圖的完整讀圖說明、處置與各角色訊息 · Full chart reading, actions and messages for every role**")
    for key, facts in case.guide:
        explain(key, facts)

    langs = _langs()
    saved = st.session_state.setdefault(f"case_saved_{case.id}", [])  # this attempt's files, already in the log
    past = cases.history()
    if saved and "file" in past:
        past = past[~past["file"].isin(saved)]
    md = cases.report_markdown(case, answers, result, answers.get("message", ""),
                               "both" if len(langs) == 2 else langs[0], past=past)
    c1, c2 = st.columns(2)
    if c1.button("存到我的練習紀錄 Save to my study log", key=f"case_save_{case.id}", help=H("case.save")):
        path = cases.save_attempt(case, result, md)
        saved.append(path.name)
        c1.success(f"已存 Saved: `{path}`")
    c2.download_button("下載報告 Download report (.md)", md.encode("utf-8"), file_name=f"case_{case.id}.md",
                       mime="text/markdown", key=f"case_dl_{case.id}", help=H("case.download"))
    case_history()


def case_history():
    from metro_toolkit import cases

    hist = cases.history()
    if len(hist):
        with st.expander(f"我的練習紀錄 · My study log（{len(hist)}）"):
            k = st.columns(3)
            k[0].metric("案例數 Cases", len(hist))
            k[1].metric("平均分數 Mean score", f"{hist['score'].mean():.0f}")
            k[2].metric("最近 5 次 Last 5", f"{hist['score'].tail(5).mean():.0f}")
            st.dataframe(hist.groupby("domain")["score"].agg(["count", "mean"]).round(0))
            st.dataframe(hist.iloc[::-1], hide_index=True)


GUIDE_GROUPS = {"nav": "導覽 Navigation", "guide": "導覽 Navigation", "data": "資料來源 Data source",
                "import": "資料匯入 Data import", "field": "標準欄位 Standard fields", "stack": "Film stack & fit",
                "wafer": "Wafer map", "spc": "SPC 管制圖", "cap": "製程能力 Capability", "msa": "MSA 量測系統分析",
                "study": "Recipe studies", "doe": "DOE / recipe", "fab": "Fab simulator", "pat": "晶圓圖樣 Wafer patterns",
                "case": "Case study 案例練習"}


def page_guide():
    from metro_toolkit import guide

    st.header("Guide 參數與圖表說明")
    st.caption("每個控制項、指標與圖表的專業說明（Metro AE 用語），以及每張圖該怎麼讀、怎麼處理、要跟誰說。"
               "左側可切換說明語言。各頁面上的「?」與「📖 怎麼讀這張圖」用的是同一份內容。")
    q = st.text_input("搜尋 Search", placeholder="例如 EWMA、Cpk、Phase I、bowl、P/T …", help=H("guide.search"), key="guide_search").strip().lower()
    t1, t2, t3 = st.tabs(["參數 Parameters", "圖表 Charts", "角色與狀態 Roles & status"])
    with t1:
        params = guide.params()
        groups: dict = {}
        for key, entry in params.items():
            txt = (entry.get("zh", "") + " " + entry.get("en", "")).lower()
            if q and q not in key.lower() and q not in txt:
                continue
            groups.setdefault(GUIDE_GROUPS.get(key.split(".")[0], "其他 Other"), []).append(key)
        st.caption(f"{sum(len(v) for v in groups.values())} / {len(params)} 項")
        for g, keys in groups.items():
            with st.expander(f"{g}（{len(keys)}）", expanded=bool(q)):
                for key in keys:
                    st.markdown(f"`{key}`")
                    st.markdown(H(key) or "")
                    st.divider()
    with t2:
        charts_kb = guide.charts()
        shown = 0
        for key, c in charts_kb.items():
            blob = str(c).lower()
            if q and q not in key.lower() and q not in blob:
                continue
            shown += 1
            with st.expander(f"{c.get('page', '')} · {c['title']['zh']} · {c['title']['en']}", expanded=bool(q) and shown <= 3):
                explain(key, None, inline=True)
        st.caption(f"{shown} / {len(charts_kb)} 張圖")
    with t3:
        m = guide.meta()
        for r in m["roles"].values():
            st.markdown(f"**{r['zh']} · {r['en']}**  \n{r['cares_zh']}  \n*{r['cares_en']}*")
        for k, v in m["status"].items():
            st.markdown(f"{v['icon']} **{v['zh']} · {v['en']}**")


PAGES = {
    "Data import": lambda df: page_import(),
    "Fab simulator": lambda df: page_fab(),
    "Film stack & fit": lambda df: page_stack(),
    "Wafer map": page_wafer,
    "SPC": page_spc,
    "MSA": lambda df: page_msa(),
    "Recipe studies": lambda df: page_studies(),
    "DOE / recipe": lambda df: page_doe(),
    "Case study 案例練習": lambda df: page_case(),
    "Guide 參數與圖表說明": lambda df: page_guide(),
}

st.sidebar.title("metro-toolkit")
st.sidebar.caption("Thin-film metrology analysis · synthetic sample or your own imported data")
choice = st.sidebar.radio("Page", list(PAGES), help=H("nav.page"), key="nav_page")
language_switch()
data = get_data() if choice in ("Wafer map", "SPC") else None
PAGES[choice](data)
