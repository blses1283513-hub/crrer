"""Read SemiYield's Plotly figures (as drawn) -> chart key + Facts. Used by the SemiYield launcher.

Only plain numpy is needed, so it runs inside SemiYield's own environment.
"""

from __future__ import annotations

import re

import numpy as np

from . import Facts

KEYS = [  # (title regex, chart key in charts.yaml)
    (r"^Oxide Growth", "sy_oxide"),
    (r"^Growth Rate vs Time", "sy_oxide_rate"),
    (r"implant at", "sy_implant"),
    (r"etch rate vs temperature", "sy_etch_t"),
    (r"etch rate vs pressure", "sy_etch_p"),
    (r"growth rate vs temperature", "sy_deposition"),
    (r"lot mean over time", "sy_trend"),
    (r"^Local yield map", "sy_wafer_map"),
    (r"^I-MR Chart", "sy_imr"),
    (r"^Feature importance", "sy_shap"),
    (r"^Bayesian optimization convergence", "sy_bo"),
]


def chart_key(title: str) -> str | None:
    for pat, key in KEYS:
        if re.search(pat, title or ""):
            return key
    return None


def _arr(v):
    try:
        return np.asarray(v, float)
    except (TypeError, ValueError):
        return np.array([])


def _main(fig):
    for tr in fig.data:
        if getattr(tr, "y", None) is not None and len(tr.y) > 1 and (getattr(tr, "showlegend", None) is not False):
            return tr
    return fig.data[0] if fig.data else None


def _ann(fig, pattern):
    for a in fig.layout.annotations or []:
        if re.search(pattern, a.text or ""):
            return a
    return None


def facts(fig) -> tuple[str | None, Facts | None]:
    title = (fig.layout.title.text or "") if fig.layout.title else ""
    key = chart_key(title)
    if key is None:
        return None, None
    try:
        return key, _READERS[key](fig, title)
    except Exception:  # never break SemiYield because of a reading
        return key, None


def _oxide(fig, title):
    tr = _main(fig)
    x, y = _arr(tr.x), _arr(tr.y)
    m = re.search(r"(\d+)C, (\w+)", title)
    slope0 = (y[5] - y[0]) / (x[5] - x[0]) if len(x) > 5 else np.nan
    slope1 = (y[-1] - y[-6]) / (x[-1] - x[-6]) if len(x) > 5 else np.nan
    f = Facts(v={"temp": m.group(1) if m else "—", "atm": m.group(2) if m else "—", "t_end": x[-1], "x_end": y[-1],
                 "x0": y[0], "slow": slope0 / slope1 if slope1 > 0 else np.nan})
    f.add(f"{f.v['temp']} °C {f.v['atm']}：{x[-1]:.0f} 分鐘後 {y[-1]:.2f} nm（起始 {y[0]:.2f} nm）",
          f"{f.v['temp']} °C {f.v['atm']}: {y[-1]:.2f} nm after {x[-1]:.0f} min (start {y[0]:.2f} nm)")
    f.add(f"結尾的成長速率只有開始的 1/{f.v['slow']:.1f}（擴散限制，拋物線區）",
          f"growth rate at the end is 1/{f.v['slow']:.1f} of the start (diffusion-limited, parabolic regime)")
    return f


def _rate(fig, title):
    tr = _main(fig)
    y = _arr(tr.y)
    f = Facts(v={"r0": y[0], "r1": y[-1], "ratio": y[0] / y[-1] if y[-1] > 0 else np.nan})
    f.add(f"速率從 {y[0]:.3g} 降到 {y[-1]:.3g} nm/min（{f.v['ratio']:.1f} 倍）", f"rate falls from {y[0]:.3g} to {y[-1]:.3g} nm/min "
          f"({f.v['ratio']:.1f}×)")
    return f


def _implant(fig, title):
    tr = _main(fig)
    x, y = _arr(tr.x), _arr(tr.y)
    i = int(np.argmax(y))
    a = _ann(fig, r"^xj=")
    xj = float(re.search(r"([\d.]+)", a.text).group(1)) if a is not None else np.nan
    f = Facts(v={"rp": x[i], "peak": y[i], "xj": xj, "title": title})
    f.add(f"峰值濃度 {y[i]:.2e} cm⁻³ 在深度 {x[i]:.0f} nm（≈ Rp）", f"peak {y[i]:.2e} cm⁻³ at {x[i]:.0f} nm depth (≈ Rp)")
    if np.isfinite(xj):
        f.add(f"接面深度 xj = {xj:.1f} nm", f"junction depth xj = {xj:.1f} nm")
    else:
        f.worse("watch").add("沒有接面：劑量低於背景濃度", "no junction: the profile never exceeds the background doping")
    return f


def _etch_t(fig, title):
    tr = _main(fig)
    x, y = _arr(tr.x), _arr(tr.y)
    f = Facts(v={"t0": x[0], "t1": x[-1], "r0": y[0], "r1": y[-1], "ratio": y[-1] / y[0] if y[0] > 0 else np.nan,
                 "per10": 100 * ((y[-1] / y[0]) ** (10 / (x[-1] - x[0])) - 1) if y[0] > 0 and x[-1] > x[0] else np.nan})
    f.add(f"{x[0]:.0f}→{x[-1]:.0f} °C：速率 {y[0]:.1f}→{y[-1]:.1f} nm/min；每升 10 °C 約 +{f.v['per10']:.1f}%",
          f"{x[0]:.0f}→{x[-1]:.0f} °C: rate {y[0]:.1f}→{y[-1]:.1f} nm/min; about +{f.v['per10']:.1f}% per 10 °C")
    return f


def _etch_p(fig, title):
    tr = _main(fig)
    x, y = _arr(tr.x), _arr(tr.y)
    n = max(len(x) // 10, 2)
    s0 = (y[n] - y[0]) / (x[n] - x[0])
    s1 = (y[-1] - y[-n - 1]) / (x[-1] - x[-n - 1])
    f = Facts(v={"r_max": y.max(), "sat": 100 * (1 - s1 / s0) if s0 > 0 else np.nan})
    f.add(f"高壓端的斜率比低壓端小 {f.v['sat']:.0f}%（趨於飽和：表面被反應物佔滿）",
          f"the slope at high pressure is {f.v['sat']:.0f}% lower than at low pressure (saturating: surface sites are full)")
    if f.v["sat"] > 70:
        f.add("在飽和區操作：對壓力變動不敏感（製程窗口較穩）", "operating in saturation: insensitive to pressure drift (a robust window)")
    return f


def _dep(fig, title):
    tr = _main(fig)
    x, y = _arr(tr.x), _arr(tr.y)
    f = Facts(v={"r0": y[0], "r1": y[-1], "ratio": y[-1] / y[0] if y[0] > 0 else np.nan, "title": title})
    f.add(f"{x[0]:.0f}→{x[-1]:.0f} °C 速率增加 {f.v['ratio']:.1f} 倍", f"rate rises {f.v['ratio']:.1f}× from {x[0]:.0f} to {x[-1]:.0f} °C")
    return f


def _trend(fig, title):
    tr = _main(fig)
    x, y = _arr(tr.x), _arr(tr.y)
    param = re.match(r"(\S+)", title).group(1)
    slope = np.polyfit(x, y, 1)[0] if len(x) > 2 else 0.0
    sd = float(np.std(y, ddof=1)) if len(y) > 2 else np.nan
    drift = slope * (x[-1] - x[0])
    mr = np.abs(np.diff(y))
    sig = float(np.mean(mr) / 1.128) if len(mr) else np.nan
    f = Facts(v={"param": param, "drift": drift, "sd": sd, "drift_sigma": drift / sig if sig > 0 else np.nan,
                 "first": y[0], "last": y[-1]})
    if np.isfinite(f.v["drift_sigma"]) and abs(f.v["drift_sigma"]) > 3:
        f.worse("watch")
    f.add(f"{param} 從第一批到最後一批的趨勢變化 {drift:+.4g}（約 {f.v['drift_sigma']:+.1f} 倍短期 σ）",
          f"{param} trends by {drift:+.4g} from first to last lot (about {f.v['drift_sigma']:+.1f}× short-term σ)")
    return f


def _wmap(fig, title):
    z = np.asarray(fig.data[0].z, float)
    inside = z[z > 0]
    h, w = z.shape
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot(xx - (w - 1) / 2, yy - (h - 1) / 2) / (max(h, w) / 2)
    edge = z[(r > 0.75) & (z > 0)]
    center = z[(r < 0.35) & (z > 0)]
    f = Facts(v={"wafer": title.split(":")[-1].strip(), "mean": inside.mean() if inside.size else np.nan,
                 "min": inside.min() if inside.size else np.nan, "edge": edge.mean() if edge.size else np.nan,
                 "center": center.mean() if center.size else np.nan})
    if np.isfinite(f.v["edge"]) and np.isfinite(f.v["center"]) and f.v["center"] - f.v["edge"] > 0.1:
        f.worse("watch")
    f.add(f"{f.v['wafer']}：平均局部良率 {f.v['mean']:.2f}，最低 {f.v['min']:.2f}；中心 {f.v['center']:.2f} vs 邊緣 {f.v['edge']:.2f}",
          f"{f.v['wafer']}: mean local yield {f.v['mean']:.2f}, lowest {f.v['min']:.2f}; centre {f.v['center']:.2f} vs edge "
          f"{f.v['edge']:.2f}")
    return f


def _imr(fig, title):
    tr = _main(fig)
    y = _arr(tr.y)
    colors = list(getattr(tr.marker, "color", None) or [])
    viol = [i for i, c in enumerate(colors) if c == "red"]
    vals = {}
    for name in ("CL", "UCL", "LCL"):
        a = _ann(fig, rf"^{name}$")
        vals[name] = float(a.y) if a is not None and a.y is not None else np.nan
    param = title.split(":", 1)[-1].strip()
    sigma = (vals["UCL"] - vals["CL"]) / 3 if np.isfinite(vals["UCL"]) else np.nan
    recent = [i for i in viol if i >= len(y) - 5]
    f = Facts(v={"param": param, "n": len(y), "n_viol": len(viol), "first_viol": viol[0] if viol else "—",
                 "cl": vals["CL"], "ucl": vals["UCL"], "lcl": vals["LCL"], "sigma": sigma,
                 "last_z": (y[-1] - vals["CL"]) / sigma if sigma and sigma > 0 else np.nan})
    if recent:
        f.worse("act").add(f"最近 5 點中有 {len(recent)} 點違反 WE 規則 → 依 OCAP 處理", f"{len(recent)} of the last 5 points break a WE "
                           "rule → follow the OCAP")
    elif viol:
        f.worse("watch").add(f"{len(viol)} 個違規點（第一個在 #{viol[0]}），最近 5 點已回到管制內",
                             f"{len(viol)} violation(s) (first at #{viol[0]}); the last 5 points are back in control")
    else:
        f.add(f"{len(y)} 點全部在管制內", f"all {len(y)} points in control")
    f.add(f"CL = {vals['CL']:.4g}，UCL/LCL = {vals['UCL']:.4g} / {vals['LCL']:.4g}（±3σ，σ ≈ {sigma:.3g}）",
          f"CL = {vals['CL']:.4g}, UCL/LCL = {vals['UCL']:.4g} / {vals['LCL']:.4g} (±3σ, σ ≈ {sigma:.3g})")
    return f


def _shap(fig, title):
    tr = fig.data[0]
    x, y = _arr(tr.x), list(tr.y)
    order = np.argsort(-x)
    tot = x.sum() or 1.0
    f = Facts(v={"top": y[order[0]], "top_share": 100 * x[order[0]] / tot, "second": y[order[1]] if len(y) > 1 else "—"})
    f.add(f"最重要的參數是 {f.v['top']}（佔總 |SHAP| {f.v['top_share']:.0f}%），其次 {f.v['second']}",
          f"most important parameter: {f.v['top']} ({f.v['top_share']:.0f}% of total |SHAP|), then {f.v['second']}")
    f.add("SHAP 代表模型的關聯，不是因果：要用分批 split lot／DOE 確認", "SHAP shows model association, not causation: confirm with a "
          "split lot / DOE")
    return f


def _bo(fig, title):
    obs = next((t for t in fig.data if t.name == "Observations"), fig.data[0])
    y = _arr(obs.y)
    best = np.maximum.accumulate(y)
    i_best = int(np.argmax(y))
    gain = best[-1] - best[min(4, len(best) - 1)]
    f = Facts(v={"best": y.max(), "i_best": i_best, "n": len(y), "gain": gain,
                 "flat": len(y) - 1 - i_best})
    f.add(f"最佳良率 {y.max():.4f} 出現在第 {i_best} 次；之後 {f.v['flat']} 次沒有再改善",
          f"best yield {y.max():.4f} at iteration {i_best}; no improvement in the {f.v['flat']} iterations since")
    f.add(f"隨機起始點之後共改善 {gain:+.4f}", f"improvement after the random start points: {gain:+.4f}")
    if f.v["flat"] < 3:
        f.worse("watch").add("最佳值才剛出現，可能還沒收斂 → 多跑幾次", "the best point is recent; it may not have converged → run more iterations")
    return f


_READERS = {"sy_oxide": _oxide, "sy_oxide_rate": _rate, "sy_implant": _implant, "sy_etch_t": _etch_t, "sy_etch_p": _etch_p,
            "sy_deposition": _dep, "sy_trend": _trend, "sy_wafer_map": _wmap, "sy_imr": _imr, "sy_shap": _shap, "sy_bo": _bo}
