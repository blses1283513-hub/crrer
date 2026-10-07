"""Suggested USL / LSL for SemiYield's SPC page (hybrid method).

Why: SemiYield's default spec limits are the 0.5 / 99.5 percentiles of the plotted data. Specs that
are derived from the data always hug the data, so Cp ≈ 0.9 no matter how good or bad the process is.

Hybrid method (in order):
  1. Counters (lot_sequence, wafer_sequence) are not process parameters: no spec.
  2. Parameters with a yield window in SemiYield's own yield model (gate_oxide_thickness, poly_cd,
     contact_resistance): nominal target ± 3σ, the window where its parametric yield starts to drop.
  3. Everything else, from the data's baseline (the first 20% of rows = earliest lots, before drift
     and equipment ageing build up): baseline median ± 4·σ_short-term, σ_short-term = mean|Δx| / 1.128
     (moving range). That makes Cp = 1.33 at baseline, so later drift shows up as falling Cpk.
  4. One-sided parameters keep only the meaningful limit; the other one is the physical bound:
       smaller-is-better (deposition_unif, defect_density, wafer_map_std): LSL = 0
       bigger-is-better  (yield, wafer_map_mean):                          USL = 1
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

COUNTERS = {"lot_sequence", "wafer_sequence"}
YIELD_WINDOW = {"gate_oxide_thickness", "poly_cd", "contact_resistance"}
SMALLER_IS_BETTER = {"deposition_unif": 0.0, "defect_density": 0.0, "wafer_map_std": 0.0}
BIGGER_IS_BETTER = {"yield": 1.0, "wafer_map_mean": 1.0}
D2 = 1.128


@dataclass
class SpecSuggestion:
    param: str
    lsl: float | None
    usl: float | None
    kind: str  # two-sided | upper-only | lower-only | not-process
    method: str  # short label (zh)
    detail: str  # explanation with numbers (zh, Markdown)
    center: float | None = None
    sigma: float | None = None
    n_baseline: int = 0


def generator_targets() -> dict | None:
    """SemiYield's nominal process targets, or None if SemiYield is not importable."""
    try:
        from semiyield.datagen.fab_generator import _PROCESS_TARGETS  # noqa: PLC0415

        return dict(_PROCESS_TARGETS)
    except Exception:
        return None


def baseline_stats(values, baseline_frac: float = 0.2, min_points: int = 30):
    """Median and short-term sigma of the earliest part of the series (assumed time-ordered)."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = int(min(x.size, max(min_points, round(baseline_frac * x.size))))
    b = x[:n]
    center = float(np.median(b))
    sigma = float(np.mean(np.abs(np.diff(b))) / D2) if b.size > 1 else 0.0
    return center, sigma, n


def _fmt(v: float) -> str:
    return f"{v:.4g}"


def suggest(param: str, values, targets: dict | None = None, k: float = 4.0, yield_k: float = 3.0,
            baseline_frac: float = 0.2) -> SpecSuggestion:
    if param in COUNTERS:
        return SpecSuggestion(param, None, None, "not-process", "非製程參數",
                              f"`{param}` 只是序號（一直遞增），不是製程參數，沒有規格；請改選真正的製程參數。")

    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size < 10:
        return SpecSuggestion(param, None, None, "insufficient", "資料不足",
                              f"`{param}` 有效數值少於 10 筆，無法估計規格。")

    if targets and param in YIELD_WINDOW and param in targets:
        t, s = float(targets[param]["mean"]), float(targets[param]["sigma"])
        lsl, usl = t - yield_k * s, t + yield_k * s
        return SpecSuggestion(
            param, lsl, usl, "two-sided", "SemiYield 良率模型的規格窗",
            f"目標 {_fmt(t)} ± {yield_k:g}σ（σ = {_fmt(s)}）→ LSL {_fmt(lsl)}、USL {_fmt(usl)}。"
            f"這正是 SemiYield 良率模型開始扣良率的範圍，所以此規格與良率一致；"
            f"以此規格設計 Cp ≈ 1.0，代表這個合成製程本來就只是「勉強可用」。",
            center=t, sigma=s,
        )

    center, sigma, n = baseline_stats(values, baseline_frac)
    base = (f"基準期 = 最早的 {n} 筆資料（約前 {baseline_frac:.0%} 的 lot，尚未累積漂移與老化）："
            f"中位數 {_fmt(center)}，短期 σ（移動全距 / 1.128）{_fmt(sigma)}。")
    if param in SMALLER_IS_BETTER:
        usl = center + k * sigma
        lsl = SMALLER_IS_BETTER[param]
        return SpecSuggestion(param, lsl, usl, "upper-only", "單邊規格（越小越好）",
                              base + f" USL = 中位數 + {k:g}σ = {_fmt(usl)}；LSL 設為物理下限 {lsl:g}。"
                              f"單邊參數只看 Cpk（上側），Cp 不適用。", center, sigma, n)
    if param in BIGGER_IS_BETTER:
        lsl = max(center - k * sigma, 0.0)
        usl = BIGGER_IS_BETTER[param]
        note = ("良率是「結果」指標而非製程參數：此 LSL 代表基準期的良率水準，之後低於它通常表示機台老化或缺陷增加。"
                if param == "yield" else "")
        return SpecSuggestion(param, lsl, usl, "lower-only", "單邊規格（越大越好）",
                              base + f" LSL = 中位數 − {k:g}σ = {_fmt(lsl)}；USL 設為物理上限 {usl:g}。"
                              f"單邊參數只看 Cpk（下側），Cp 不適用。" + note, center, sigma, n)
    lsl, usl = center - k * sigma, center + k * sigma
    return SpecSuggestion(param, lsl, usl, "two-sided", "資料基準期 ± 4σ",
                          base + f" 規格 = 中位數 ± {k:g}σ → LSL {_fmt(lsl)}、USL {_fmt(usl)}"
                          f"（基準期 Cp = 1.33；之後若漂移，Cpk 會下降）。", center, sigma, n)


def number_format(lsl: float | None, usl: float | None, sigma: float | None):
    """(format, step) for st.number_input so tiny or huge values display sensibly."""
    vals = [abs(v) for v in (lsl, usl) if v is not None]
    big = max(vals) if vals else 1.0
    if big >= 1e5 or (0 < big < 1e-3):
        step = (sigma or big * 1e-3) / 10
        return "%.4e", float(step)
    ref = sigma if sigma and sigma > 0 else (big or 1.0) / 100
    decimals = int(min(6, max(2, -np.floor(np.log10(ref)) + 2)))
    return f"%.{decimals}f", float(10.0 ** -decimals)
