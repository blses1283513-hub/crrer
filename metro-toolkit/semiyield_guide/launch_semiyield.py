"""Run SemiYield's dashboard with hover explanations added (SemiYield itself is not modified).

    # from metro-toolkit\\ , using SemiYield's own environment:
    <semiyield>\\.venv\\Scripts\\python.exe -m streamlit run semiyield_guide\\launch_semiyield.py

How it works
  1. Streamlit input widgets (slider, selectbox, ...) and metric cards get a "?" tooltip (`help=`)
     when their label matches an entry in explanations.yaml.
  2. Plotly charts get a hover text on each data point (and on reference lines such as UCL/CL/LCL)
     when the figure title matches a `charts` entry; other charts get a generic "x / y" hover.
  3. SemiYield's own dashboard/app.py is then executed unchanged.

Where is SemiYield?  Set SEMIYIELD_DIR, or keep it next to the crrer folder
(…\\projects\\semiyield and …\\projects\\crrer), or run from inside the SemiYield folder.
Needs only: streamlit, plotly, numpy, pyyaml (pip install pyyaml if missing).
"""

from __future__ import annotations

import os
import re
import runpy
import sys
from pathlib import Path

import streamlit as st

HERE = Path(__file__).resolve().parent
RULES_FILE = Path(os.environ.get("SEMIYIELD_GUIDE_FILE", HERE / "explanations.yaml"))
WIDGETS = ("slider", "number_input", "selectbox", "radio", "metric", "button", "file_uploader", "checkbox")


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


# --------------------------------------------------------------------------- #
# Widget tooltips                                                             #
# --------------------------------------------------------------------------- #


def _arg(args, kwargs, pos, name):
    if name in kwargs:
        return kwargs[name]
    return args[pos] if len(args) > pos else None


def _widget_help(kind: str, args, kwargs) -> str | None:
    rules = getattr(st, "_sy_rules", {}).get("widgets", [])
    label = _arg(args, kwargs, 0, "label")
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
        if "options" in r and options is not None and list(r["options"]) != options:
            continue
        if "options" in r and options is None:
            continue
        if "min" in r and (lo is None or float(r["min"]) != float(lo)):
            continue
        if "max" in r and (hi is None or float(r["max"]) != float(hi)):
            continue
        return str(r["help"]).strip()
    return None


def _install_widget_patches() -> None:
    from streamlit.delta_generator import DeltaGenerator

    for kind in WIDGETS:
        cls_orig = getattr(DeltaGenerator, kind)
        if not getattr(cls_orig, "_sy_guide", False):

            def make_cls(orig, kind=kind):
                def wrapper(self, *args, **kwargs):
                    if kwargs.get("help") is None:
                        h = _widget_help(kind, args, kwargs)
                        label = _arg(args, kwargs, 0, "label")
                        if h:
                            kwargs["help"] = h
                        elif isinstance(label, str):
                            st._sy_cov["widgets_missing"].add(label)
                    return orig(self, *args, **kwargs)

                wrapper._sy_guide = True
                return wrapper

            setattr(DeltaGenerator, kind, make_cls(cls_orig))

        mod_orig = getattr(st, kind)
        if not getattr(mod_orig, "_sy_guide", False):

            def make_mod(orig, kind=kind):
                def wrapper(*args, **kwargs):
                    if kwargs.get("help") is None:
                        h = _widget_help(kind, args, kwargs)
                        label = _arg(args, kwargs, 0, "label")
                        if h:
                            kwargs["help"] = h
                        elif isinstance(label, str):
                            st._sy_cov["widgets_missing"].add(label)
                    return orig(*args, **kwargs)

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
    import plotly.graph_objects as go

    rules = getattr(st, "_sy_rules", {}).get("charts", [])
    title = (fig.layout.title.text or "") if fig.layout.title else ""
    rule = next((r for r in rules if re.search(r["match"], title)), None)
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
    main = [tr for tr in fig.data if tr.type == "scatter"]
    for tr in main:
        for spec in rule.get("traces", []):
            if re.search(spec["name"], tr.name or ""):
                tr.hovertemplate = spec["hover"].strip()
                if spec.get("status_marker"):
                    colors = getattr(getattr(tr, "marker", None), "color", None)
                    if colors is not None and not isinstance(colors, str):
                        tr.customdata = [
                            "⚠ 違反規則 (violation)" if c == "red" else "✓ 在管制內 (in control)" for c in colors
                        ]
                break

    anchor = next((t for t in main if t.x is not None and len(t.x) > 1), None)
    if anchor is None:
        return
    import numpy as np

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
    _install_widget_patches()
    _install_chart_patches()

    sys.path.insert(0, str(sy_dir))
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
