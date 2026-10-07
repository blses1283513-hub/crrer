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
  4. SemiYield's own dashboard/app.py is then executed unchanged.

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
from spec_limits import generator_targets, number_format, suggest  # noqa: E402

RULES_FILE = Path(os.environ.get("SEMIYIELD_GUIDE_FILE", HERE / "explanations.yaml"))
WIDGETS = ("slider", "number_input", "selectbox", "radio", "metric", "button", "file_uploader",
           "checkbox", "text_input", "subheader")
QUIET = {"subheader"}  # never reported as "missing" (most headers need no tooltip)


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


def feature_text(name: str, long: bool = True) -> str | None:
    f = getattr(st, "_sy_rules", {}).get("features", {}).get(name)
    if not f:
        return None
    head = f"**{name}** {f['zh']}" + (f"（{f['unit']}）" if f.get("unit") else "")
    return f"{head}：{f['note']}" if long else f"{f['zh']}：{f['note']}"


# --------------------------------------------------------------------------- #
# Widget tooltips                                                             #
# --------------------------------------------------------------------------- #


def _arg(args, kwargs, pos, name):
    if name in kwargs:
        return kwargs[name]
    return args[pos] if len(args) > pos else None


def _label(kind, args, kwargs):
    return _arg(args, kwargs, 0, "body" if kind == "subheader" else "label")


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
        return str(r["help"]).strip()
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


def _spec_for_spc():
    ctx = st._sy_ctx
    param = ctx.get("spc_param")
    if not param:
        return None
    if ctx.get("spec_param") != param:
        values = _spc_values(param)
        if values is None:
            return None
        targets = None if ctx.get("data_source") == "Upload CSV" else generator_targets()
        ctx["spec"], ctx["spec_param"] = suggest(param, values, targets), param
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


def _call(kind, orig, dg, args, kwargs):
    """Shared wrapper body for module-level (dg=None) and container (dg=self) calls."""
    label = _label(kind, args, kwargs)
    sug = None
    if kind == "number_input" and label in ("USL", "LSL") and kwargs.get("help") is None:
        sug = _apply_spec(label, kwargs)
    if kwargs.get("help") is None:
        h = _widget_help(kind, args, kwargs)
        if h:
            kwargs["help"] = h
        elif isinstance(label, str) and kind not in QUIET:
            st._sy_cov["widgets_missing"].add(label)

    result = orig(dg, *args, **kwargs) if dg is not None else orig(*args, **kwargs)

    target = dg if dg is not None else st
    if label == "Parameter to chart" and kind == "selectbox":
        st._sy_ctx["spc_param"] = result
        note = feature_text(str(result))
        if note:
            target.caption(note)
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
    fig.update_layout(hoverlabel=dict(align="left", bgcolor="#ffffff", bordercolor="#c3c2b7",
                                      font=dict(color="#0b0b0b", size=12)))
    param = m.groupdict().get("param") if m else None
    note = (feature_text(param, long=False) or "") if param else ""
    for tr in fig.data:
        for spec in rule.get("traces", []):
            if re.search(spec["name"], tr.name or ""):
                tr.hovertemplate = spec["hover"].strip().replace("[[param]]", param or "").replace("[[note]]", note)
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
        hover = spec["hover"].strip()
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
            return cls_orig(self, figure_or_data, *args, **kwargs)

        cls_wrapper._sy_guide = True
        DeltaGenerator.plotly_chart = cls_wrapper

    mod_orig = st.plotly_chart
    if not getattr(mod_orig, "_sy_guide", False):

        def mod_wrapper(figure_or_data, *args, **kwargs):
            try:
                _decorate(figure_or_data)
            except Exception as exc:
                st._sy_cov["errors"].append(f"{type(exc).__name__}: {exc}")
            return mod_orig(figure_or_data, *args, **kwargs)

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
    sys.path.insert(0, str(sy_dir))
    _install_widget_patches()
    _install_chart_patches()

    runpy.run_path(str(sy_dir / "dashboard" / "app.py"), run_name="__main__")

    cov = st._sy_cov
    with st.sidebar:
        with st.expander("Metro 說明覆蓋率 (guide coverage)"):
            st.caption(f"SemiYield：{sy_dir}")
            st.write(f"圖表（已有專屬說明）：{len(cov['charts_matched'])}；一般 x/y 提示：{len(cov['charts_generic'])}")
            if cov["widgets_missing"]:
                st.write("尚無說明的輸入欄位：", ", ".join(sorted(cov["widgets_missing"])))
            for msg in cov["errors"]:
                st.warning(msg)


main()
