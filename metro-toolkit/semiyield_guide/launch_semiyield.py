"""Run SemiYield's dashboard with hover explanations added (SemiYield itself is not modified).

    # from SemiYield's folder, using SemiYield's own environment:
    .venv\\Scripts\\python.exe -m streamlit run ..\\crrer\\metro-toolkit\\semiyield_guide\\launch_semiyield.py

How it works
  1. Inputs, metric cards and section headers get a "?" tooltip (`help=`) when their label matches
     an entry in explanations.yaml (or a process-parameter name in its `features` list).
  2. Plotly charts get hover text on each data point (and on reference lines such as UCL/CL/LCL)
     when the figure title matches a `charts` entry; other charts get a generic "x / y" hover.
  3. On the SPC page, USL / LSL start from reliable suggested values (spec_limits.py) instead of
     the data's 0.5 / 99.5 percentiles; the method is shown under the boxes and can be overridden.
  4. Under every chart: a status line read from the chart's own data and a "📖 How to read this chart" panel
     (legend, what it shows, next step, ready-to-send messages per role), from metro-toolkit's guide
     (src/metro_toolkit/guide, charts_semiyield.yaml). Language: sidebar "說明語言 Guide language".
  5. SemiYield's own dashboard/app.py is then executed unchanged.

Where is SemiYield?  Set SEMIYIELD_DIR, or keep it next to the crrer folder
(…\\projects\\semiyield and …\\projects\\crrer), or run from inside the SemiYield folder.
Needs only: streamlit, plotly, numpy, pandas, pyyaml (pip install pyyaml if missing).
"""

from __future__ import annotations

import os
import re
import runpy
import sys
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "src"))  # metro_toolkit.guide (needs only pyyaml + numpy)
from spec_limits import COUNTERS, SpecSuggestion, baseline_stats, generator_targets, number_format, suggest  # noqa: E402

RULES_FILE = Path(os.environ.get("SEMIYIELD_GUIDE_FILE", HERE / "explanations.yaml"))
IMPORT_DIR = Path(os.environ.get("METRO_IMPORT_PATH", HERE.parent / "data" / "imported"))
YIELD_FEATURES = ("gate_oxide_thickness", "poly_cd", "implant_dose", "anneal_temp", "metal_resistance",
                  "contact_resistance", "etch_rate", "deposition_unif", "defect_density")
WIDGETS = ("slider", "number_input", "selectbox", "radio", "metric", "button", "file_uploader",
           "checkbox", "text_input", "subheader", "title")
QUIET = {"subheader", "title"}  # never reported as "missing" (most headers need no tooltip)
INPUTS = {"slider", "number_input", "selectbox", "radio", "button", "file_uploader", "checkbox", "text_input"}


# --------------------------------------------------------------------------- #
# Locate SemiYield and load the explanations                                   #
# --------------------------------------------------------------------------- #


def find_semiyield() -> Path | None:
    candidates = []
    if os.environ.get("SEMIYIELD_DIR"):
        candidates.append(Path(os.environ["SEMIYIELD_DIR"]))
    candidates += [HERE.parents[1] / "semiyield", HERE.parents[2] / "semiyield", Path.cwd(), Path.cwd().parent / "semiyield"]
    for c in candidates:
        if (c / "dashboard" / "app.py").exists():
            return c.resolve()
    return None


def load_rules() -> dict:
    import yaml

    with open(RULES_FILE, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def guide_lang() -> str:
    return st.session_state.get("guide_lang", "both")


def bilingual(zh: str | None, en: str | None, sep: str = "\n\n---\n\n") -> str | None:
    """zh / en / both, following the sidebar language switch (falls back to whichever exists)."""
    lang = guide_lang()
    zh, en = (zh or "").strip() or None, (en or "").strip() or None
    if lang == "zh" or not en:
        return zh or en
    if lang == "en" or not zh:
        return en or zh
    return zh + sep + en


def feature_text(name: str, long: bool = True) -> str | None:
    f = getattr(st, "_sy_rules", {}).get("features", {}).get(name)
    if not f:
        return None
    head = f"**{name}** {f['zh']}" + (f"（{f['unit']}）" if f.get("unit") else "")
    zh = f"{head}：{f['note']}" if long else f"{f['zh']}：{f['note']}"
    en = None
    if f.get("en") and f.get("note_en"):
        unit_en = f.get("unit_en") or re.sub(r"[\u4e00-\u9fff]", "", str(f.get("unit") or "")).strip()
        unit = f" ({unit_en})" if unit_en else ""
        en = f"**{name}** {f['en']}{unit}: {f['note_en']}" if long else f"{f['en']}: {f['note_en']}"
    return bilingual(zh, en, sep="\n\n" if long else " / ")


# --------------------------------------------------------------------------- #
# Widget tooltips                                                             #
# --------------------------------------------------------------------------- #


def _arg(args, kwargs, pos, name):
    if name in kwargs:
        return kwargs[name]
    return args[pos] if len(args) > pos else None


def _label(kind, args, kwargs):
    return _arg(args, kwargs, 0, "body" if kind in ("subheader", "title") else "label")


def _widget_help(kind: str, args, kwargs) -> str | None:
    rules = getattr(st, "_sy_rules", {}).get("widgets", [])
    label = _label(kind, args, kwargs)
    if not isinstance(label, str):
        return None
    options = lo = hi = None
    if kind in ("selectbox", "radio"):
        options = _arg(args, kwargs, 1, "options")
        options = list(options) if options is not None else None
    elif kind == "slider":
        lo, hi = _arg(args, kwargs, 1, "min_value"), _arg(args, kwargs, 2, "max_value")
    for r in rules:
        if r.get("label") != label:
            continue
        if "kind" in r and r["kind"] != kind:
            continue
        if "options" in r and (options is None or list(r["options"]) != options):
            continue
        if "min" in r and (lo is None or float(r["min"]) != float(lo)):
            continue
        if "max" in r and (hi is None or float(r["max"]) != float(hi)):
            continue
        return bilingual(str(r["help"]), r.get("help_en"))
    if kind in ("number_input", "metric"):  # Yield Prediction inputs are named after process parameters
        return feature_text(label)
    return None


# ---- SPC spec limits ------------------------------------------------------- #


def _spc_values(param: str):
    import pandas as pd

    ctx = st._sy_ctx
    if ctx.get("data_source") == "Upload CSV":
        up = ctx.get("upload")
        if up is None:
            return None
        up.seek(0)
        df = pd.read_csv(up)
        up.seek(0)
    else:
        df = st.session_state.get("fab_df")
    if df is None or param not in df:
        return None
    return df[param].to_numpy()


def using_import() -> bool:
    """True while SemiYield's data table is the dataset loaded from metro-toolkit's Data import."""
    df = st.session_state.get("fab_df")
    return df is not None and id(df) == st.session_state.get("metro_import_id")


def _imported_spec(param: str, values):
    rec = (st.session_state.get("metro_import_specs") or {}).get(param)
    if not rec or (rec.get("lsl") is None and rec.get("usl") is None):
        return None
    _, sigma, _ = baseline_stats(values)
    lsl, usl = rec.get("lsl"), rec.get("usl")
    kind = "two-sided" if lsl is not None and usl is not None else ("upper-only" if usl is not None else "lower-only")
    lsl = lsl if lsl is not None else 0.0
    usl = usl if usl is not None else 1.0
    return SpecSuggestion(param, float(lsl), float(usl), kind, "匯入資料中的規格",
                          f"這份匯入資料本身帶有規格：LSL {lsl:.4g}、USL {usl:.4g}"
                          + (f"、目標 {rec['target']:.4g}" if rec.get("target") is not None else "") + "。",
                          center=rec.get("target"), sigma=sigma)


def _spec_for_spc():
    ctx = st._sy_ctx
    param = ctx.get("spc_param")
    if not param:
        return None
    if ctx.get("spec_param") != param:
        values = _spc_values(param)
        if values is None:
            return None
        external = ctx.get("data_source") == "Upload CSV" or using_import()
        spec = _imported_spec(param, values) if using_import() else None
        ctx["spec"] = spec or suggest(param, values, None if external else generator_targets())
        ctx["spec_param"] = param
    return ctx["spec"]


def _apply_spec(label: str, kwargs: dict):
    """Replace the default USL/LSL with the suggested value; return the suggestion (or None)."""
    sug = _spec_for_spc()
    if sug is None:
        return None
    if sug.lsl is not None:
        kwargs["value"] = float(sug.usl if label == "USL" else sug.lsl)
        fmt, step = number_format(sug.lsl, sug.usl, sug.sigma)
        kwargs.setdefault("format", fmt)
        kwargs.setdefault("step", step)
        kwargs["help"] = (f"**{label}（建議值）**：{sug.method}\n\n{sug.detail}\n\n"
                          "這是起始建議值，可以直接改成你的實際規格。")
    else:
        kwargs["help"] = f"**{label}**：{sug.detail}"
    return sug


def is_counter(name) -> bool:
    """Row counters / IDs are not process parameters (also catches typical columns in uploaded CSVs)."""
    n = str(name).lower()
    return n in COUNTERS or n.endswith(("_sequence", "_id", "_index")) or n in ("index", "unnamed: 0", "id")


def _drop_counters(args, kwargs):
    """Remove counter columns from the SPC parameter list so the page opens on a real parameter."""
    if "options" in kwargs:
        options = list(kwargs["options"])
    elif len(args) > 1:
        options = list(args[1])
    else:
        return args, kwargs, []
    keep = [o for o in options if not is_counter(o)]
    if not keep or len(keep) == len(options):
        return args, kwargs, []
    removed = [o for o in options if is_counter(o)]
    if "options" in kwargs:
        kwargs["options"] = keep
    else:
        args = (args[0], keep, *args[2:])
    return args, kwargs, removed


def _available_trend_params(args, kwargs):
    """Data Generator trend chart lists fixed SemiYield names; keep only columns the imported data has."""
    df = st.session_state.get("fab_df")
    options = list(kwargs["options"]) if "options" in kwargs else list(args[1]) if len(args) > 1 else []
    keep = [o for o in options if o in df.columns]
    if not keep:
        keep = [c for c in df.select_dtypes("number").columns if not is_counter(c)]
    if "options" in kwargs:
        kwargs["options"] = keep
    else:
        args = (args[0], keep, *args[2:])
    return args, kwargs


def _import_panel() -> None:
    """Sidebar panel: load a dataset saved by metro-toolkit's Data import page into SemiYield."""
    import json

    import pandas as pd

    files = sorted(IMPORT_DIR.glob("*_wafer.csv")) if IMPORT_DIR.exists() else []
    active = st.session_state.get("metro_import") if using_import() else None
    with st.expander("metro-toolkit 匯入資料 (your data)", expanded=bool(active)):
        if not files:
            st.caption(f"尚無匯入資料。到 metro-toolkit 的 **Data import** 頁面匯入後會出現在這裡（資料夾：{IMPORT_DIR}）。")
            return
        names = [f.name[: -len("_wafer.csv")] for f in files]
        synthetic = "（SemiYield 產生的合成資料）"
        options = [synthetic] + names
        choice = st.selectbox("資料集", options, index=options.index(active) if active in options else 0,
                              help="載入後，SemiYield 的 SPC Dashboard 與 Yield Prediction 會使用這份資料。")
        if st.button("載入這份資料" if choice != synthetic else "改回合成資料"):
            if choice == synthetic:
                st.session_state.fab_df = None
                for k in ("metro_import", "metro_import_id", "metro_import_specs"):
                    st.session_state.pop(k, None)
            else:
                df = pd.read_csv(IMPORT_DIR / f"{choice}_wafer.csv")
                spec_file = IMPORT_DIR / f"{choice}_specs.json"
                st.session_state.fab_df = df
                st.session_state.pop("fab_gen", None)  # SemiYield's synthetic wafer-map generator does not apply
                st.session_state["metro_import"] = choice
                st.session_state["metro_import_id"] = id(df)
                st.session_state["metro_import_specs"] = (
                    json.loads(spec_file.read_text(encoding="utf-8")) if spec_file.exists() else {})
            st.rerun()
        if active:
            df = st.session_state.fab_df
            st.success(f"使用中：{active}（{len(df)} 片晶圓、{df['lot_id'].nunique()} 批）")
            feats = [c for c in YIELD_FEATURES if c in df.columns]
            if "yield" not in df.columns or not feats:
                st.caption("Yield Prediction 需要 `yield` 欄與至少一個 SemiYield 參數名稱；目前只能用 SPC。")


def _apply_yield_fix() -> bool:
    try:
        from semiyield.models import ensemble  # noqa: PLC0415
        from yield_fix import apply  # noqa: PLC0415
    except Exception as exc:  # sklearn missing etc.: the page will report it itself
        st._sy_cov["errors"].append(f"yield fix not applied: {type(exc).__name__}: {exc}")
        return False
    apply(ensemble.YieldEnsemble)
    return True


def _stable_key(kind, args, kwargs) -> str:
    """A widget's identity normally includes its help text, so switching the guide language would reset it.
    A key built from everything except the help keeps the user's choices (same label + same options/range/default
    -> same key; repeated identical widgets get an occurrence number)."""
    import hashlib

    sig = repr((kind, args, sorted((k, v) for k, v in kwargs.items() if k not in ("help", "on_change", "on_click"))))
    h = hashlib.md5(sig.encode("utf-8", "replace")).hexdigest()[:12]
    count = st._sy_keys.get(h, 0)
    st._sy_keys[h] = count + 1
    return f"sy_{kind}_{h}_{count}"


def _call(kind, orig, dg, args, kwargs):
    """Shared wrapper body for module-level (dg=None) and container (dg=self) calls."""
    label = _label(kind, args, kwargs)
    sug = None
    removed = []
    if kind == "selectbox" and label == "Parameter to chart":
        args, kwargs, removed = _drop_counters(args, kwargs)
    if kind == "selectbox" and label == "Parameter" and using_import():
        args, kwargs = _available_trend_params(args, kwargs)
    if kind == "button" and label == "Train Ensemble Model" and using_import():
        df = st.session_state.get("fab_df")
        feats = [c for c in YIELD_FEATURES if c in df.columns]
        if "yield" not in df.columns or not feats:
            kwargs["disabled"] = True
            (dg if dg is not None else st).warning(
                "匯入的資料缺少 Yield Prediction 需要的欄位：需要 `yield`，以及至少一個參數名稱："
                + "、".join(YIELD_FEATURES) + "。請在 metro-toolkit 的 Data import 頁面把欄位改成這些名稱後重新匯入。")
    if kind == "number_input" and label in ("USL", "LSL") and kwargs.get("help") is None:
        sug = _apply_spec(label, kwargs)
    if kwargs.get("help") is None:
        h = _widget_help(kind, args, kwargs)
        if h:
            kwargs["help"] = h
        elif isinstance(label, str) and kind not in QUIET:
            st._sy_cov["widgets_missing"].add(label)

    if kind in INPUTS and kwargs.get("key") is None and hasattr(st, "_sy_keys"):
        kwargs["key"] = _stable_key(kind, args, {k: v for k, v in kwargs.items() if k != "key"})
    result = orig(dg, *args, **kwargs) if dg is not None else orig(*args, **kwargs)

    target = dg if dg is not None else st
    if kind == "title" and label == "Yield Prediction":
        if _apply_yield_fix():
            target.caption("Metro 修正已啟用：集成模型改用「非負、總和為 1」的權重，並在選定權重後用全部訓練資料重新訓練"
                           "（測試集不變）。原本的權重會放大預測的良率下降，使 R² 變成負值。游標停在 R2 的 ? 看說明。")
    if label == "Parameter to chart" and kind == "selectbox":
        st._sy_ctx["spc_param"] = result
        note = feature_text(str(result))
        if note:
            target.caption(note)
        if removed:
            target.caption("已從清單移除序號欄位（不是製程參數）：" + "、".join(map(str, removed)))
    elif label == "Data source" and kind == "radio":
        st._sy_ctx["data_source"] = result
    elif label == "Upload process data CSV" and kind == "file_uploader":
        st._sy_ctx["upload"] = result
    elif sug is not None and label == "USL":
        target.caption(f"建議規格：{sug.method}（游標停在 ? 看計算方式）")
    return result


def _install_widget_patches() -> None:
    from streamlit.delta_generator import DeltaGenerator

    for kind in WIDGETS:
        cls_orig = getattr(DeltaGenerator, kind)
        if not getattr(cls_orig, "_sy_guide", False):

            def make_cls(orig, kind=kind):
                def wrapper(self, *args, **kwargs):
                    return _call(kind, orig, self, args, kwargs)

                wrapper._sy_guide = True
                return wrapper

            setattr(DeltaGenerator, kind, make_cls(cls_orig))

        mod_orig = getattr(st, kind)
        if not getattr(mod_orig, "_sy_guide", False):

            def make_mod(orig, kind=kind):
                def wrapper(*args, **kwargs):
                    return _call(kind, orig, None, args, kwargs)

                wrapper._sy_guide = True
                return wrapper

            setattr(st, kind, make_mod(mod_orig))


# --------------------------------------------------------------------------- #
# Chart hover text                                                            #
# --------------------------------------------------------------------------- #


def _numbers(values):
    import numpy as np

    try:
        return np.asarray(values, dtype=float)
    except (TypeError, ValueError):
        return np.array([])


def _axis_title(axis) -> str:
    text = getattr(getattr(axis, "title", None), "text", None)
    return text or ""


def _hover(spec: dict, param: str = "", name: str | None = None) -> str:
    """Hover text in the chosen language (both = zh, a blank line, then en); [[note]] in each language."""
    f = getattr(st, "_sy_rules", {}).get("features", {}).get(name or "") or {}
    zh = spec["hover"].strip().replace("[[param]]", param).replace("[[note]]", f"{f.get('zh', '')}：{f.get('note', '')}" if f else "")
    en = (spec.get("hover_en") or "").strip().replace("[[param]]", param).replace(
        "[[note]]", f"{f.get('en', '')}: {f.get('note_en', '')}" if f.get("en") else "")
    lang = guide_lang()
    if lang == "en" and en:
        return en
    if lang == "both" and en:
        return zh.replace("<extra></extra>", "") + "<br><br>" + en
    return zh


# legend entries for reference lines that SemiYield draws as shapes (shapes have no legend of their own)
LINE_LEGEND = [(r"^CL$", "CL 中心線 (center line)"), (r"^UCL$", "UCL / LCL 管制界限 (±3σ control limits)"),
               (r"^Background", "Background 背景濃度 (substrate doping)"), (r"^xj=", "xj 接面深度 (junction depth)")]


def _add_legends(fig) -> None:
    import plotly.graph_objects as go

    shapes = list(fig.layout.shapes or [])
    for ann in list(fig.layout.annotations or []):
        name = next((n for pat, n in LINE_LEGEND if re.search(pat, ann.text or "")), None)
        if name is None:
            continue
        horiz = "domain" in str(ann.xref or "")
        shape = next((sh for sh in shapes if (horiz and sh.y0 == ann.y) or (not horiz and sh.x0 == ann.x)), None)
        line = shape.line if shape is not None else None
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=name, hoverinfo="skip", showlegend=True,
                                 line=dict(color=getattr(line, "color", None) or "#52514e",
                                           dash=getattr(line, "dash", None) or "solid", width=1.5)))
    for tr in list(fig.data):
        colors = getattr(getattr(tr, "marker", None), "color", None)
        if colors is not None and not isinstance(colors, str) and "red" in list(colors):
            fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="WE violation 違規點", hoverinfo="skip",
                                     marker=dict(color="red", size=8)))
            tr.showlegend = True
            break
    fig.update_layout(showlegend=True)


def _explain(fig, where) -> None:
    """Status line + "how to read this chart" panel under a SemiYield chart."""
    try:
        from metro_toolkit.guide.insights_semiyield import facts
        from metro_toolkit.guide.render import explain
    except ImportError as exc:
        st._sy_cov["errors"].append(f"guide unavailable: {exc}")
        return
    key, f = facts(fig)
    if key:
        explain(key, f, where=where)


def _decorate(fig) -> None:
    import numpy as np
    import plotly.graph_objects as go

    rules = getattr(st, "_sy_rules", {}).get("charts", [])
    title = (fig.layout.title.text or "") if fig.layout.title else ""
    rule, m = None, None
    for r in rules:
        m = re.search(r["match"], title)
        if m:
            rule = r
            break
    xt, yt = _axis_title(fig.layout.xaxis), _axis_title(fig.layout.yaxis)

    if rule is None:
        st._sy_cov["charts_generic"].append(title or "(untitled)")
        for tr in fig.data:
            if tr.type in ("scatter", "bar") and not tr.hovertemplate:
                tr.hovertemplate = f"<b>{yt or 'y'}</b> = %{{y}}<br>{xt or 'x'} = %{{x}}<extra>{tr.name or ''}</extra>"
        return

    st._sy_cov["charts_matched"].append(title)
    _add_legends(fig)
    fig.update_layout(hoverlabel=dict(align="left", bgcolor="#ffffff", bordercolor="#c3c2b7",
                                      font=dict(color="#0b0b0b", size=12)))
    param = m.groupdict().get("param") if m else None
    for tr in fig.data:
        for spec in rule.get("traces", []):
            if re.search(spec["name"], tr.name or ""):
                tr.hovertemplate = _hover(spec, param or "", param)
                if spec.get("status_marker"):
                    colors = getattr(getattr(tr, "marker", None), "color", None)
                    if colors is not None and not isinstance(colors, str):
                        tr.customdata = [
                            "⚠ 違反規則 (violation)" if c == "red" else "✓ 在管制內 (in control)" for c in colors
                        ]
                if spec.get("customdata") == "feature_y" and tr.y is not None:
                    tr.customdata = [feature_text(str(v), long=False) or "" for v in tr.y]
                break

    main = [tr for tr in fig.data if tr.type == "scatter"]
    anchor = next((t for t in main if t.x is not None and len(t.x) > 1), None)
    if anchor is None:
        return
    ax = _numbers(anchor.x)
    ay = _numbers(anchor.y)
    log_y = (fig.layout.yaxis.type or "") == "log"
    for ann in list(fig.layout.annotations or []):
        spec = next((s for s in rule.get("lines", []) if re.search(s["text"], ann.text or "")), None)
        if spec is None:
            continue
        hover = _hover(spec)
        if "domain" in str(ann.xref or ""):  # horizontal line: value in ann.y
            if ann.y is None:
                continue
            fig.add_trace(go.Scatter(x=ax, y=np.full(ax.size, float(ann.y)), mode="markers", name=ann.text,
                                     marker=dict(size=14, opacity=0), hovertemplate=hover, showlegend=False))
        else:  # vertical line: value in ann.x
            if ann.x is None:
                continue
            pos = ay[np.isfinite(ay) & (ay > 0)] if log_y else ay[np.isfinite(ay)]
            if pos.size == 0:
                continue
            ys = np.geomspace(pos.min(), pos.max(), 25) if log_y else np.linspace(pos.min(), pos.max(), 25)
            fig.add_trace(go.Scatter(x=np.full(ys.size, float(ann.x)), y=ys, mode="markers", name=ann.text,
                                     marker=dict(size=14, opacity=0), hovertemplate=hover, showlegend=False))


def _install_chart_patches() -> None:
    from streamlit.delta_generator import DeltaGenerator

    cls_orig = DeltaGenerator.plotly_chart
    if not getattr(cls_orig, "_sy_guide", False):

        def cls_wrapper(self, figure_or_data, *args, **kwargs):
            try:
                _decorate(figure_or_data)
            except Exception as exc:  # never break the app because of a tooltip
                st._sy_cov["errors"].append(f"{type(exc).__name__}: {exc}")
            out = cls_orig(self, figure_or_data, *args, **kwargs)
            try:
                _explain(figure_or_data, self)
            except Exception as exc:
                st._sy_cov["errors"].append(f"{type(exc).__name__}: {exc}")
            return out

        cls_wrapper._sy_guide = True
        DeltaGenerator.plotly_chart = cls_wrapper

    mod_orig = st.plotly_chart
    if not getattr(mod_orig, "_sy_guide", False):

        def mod_wrapper(figure_or_data, *args, **kwargs):
            try:
                _decorate(figure_or_data)
            except Exception as exc:
                st._sy_cov["errors"].append(f"{type(exc).__name__}: {exc}")
            out = mod_orig(figure_or_data, *args, **kwargs)
            try:
                _explain(figure_or_data, None)
            except Exception as exc:
                st._sy_cov["errors"].append(f"{type(exc).__name__}: {exc}")
            return out

        mod_wrapper._sy_guide = True
        st.plotly_chart = mod_wrapper


# --------------------------------------------------------------------------- #
# Main                                                                        #
# --------------------------------------------------------------------------- #


def main() -> None:
    sy_dir = find_semiyield()
    if sy_dir is None:
        st.error(
            "找不到 SemiYield。請設定環境變數 SEMIYIELD_DIR 指向 SemiYield 資料夾，"
            "或把 semiyield 與 crrer 放在同一個 projects 資料夾。\n\n"
            "SemiYield not found. Set SEMIYIELD_DIR to its folder."
        )
        st.stop()
    try:
        st._sy_rules = load_rules()
    except ImportError:
        st.error("缺少 pyyaml。請在 SemiYield 的環境執行：python -m pip install pyyaml")
        st.stop()
    st._sy_cov = {"widgets_missing": set(), "charts_matched": [], "charts_generic": [], "errors": []}
    st._sy_ctx = {}
    st._sy_keys = {}  # occurrence counter for _stable_key, reset every run
    sys.path.insert(0, str(sy_dir))
    _install_widget_patches()
    _install_chart_patches()

    runpy.run_path(str(sy_dir / "dashboard" / "app.py"), run_name="__main__")

    cov = st._sy_cov
    with st.sidebar:
        st.radio("說明語言 Guide language", ["both", "zh", "en"], key="guide_lang", horizontal=True,
                 format_func={"both": "繁中 + English", "zh": "繁中", "en": "English"}.get,
                 help="提示（?）、圖上的游標說明與每張圖下方的「怎麼讀這張圖」使用的語言。\n\n---\n\n"
                      "Language of the tooltips (?), chart hover text and the \"how to read this chart\" panels.")
        _import_panel()
        with st.expander("Metro 說明覆蓋率 (guide coverage)"):
            st.caption(f"SemiYield：{sy_dir}")
            st.write(f"圖表（已有專屬說明）：{len(cov['charts_matched'])}；一般 x/y 提示：{len(cov['charts_generic'])}")
            if cov["widgets_missing"]:
                st.write("尚無說明的輸入欄位：", ", ".join(sorted(cov["widgets_missing"])))
            for msg in cov["errors"]:
                st.warning(msg)


main()
