---
tags: [metro-thickness, MSA, GRR, precision]
chapters: [15]
created: 2026-10-06
---

# 12 · Measurement System Analysis and Gauge R&R（量測系統分析）

← [[11 Statistics SPC and Capability]] · next → [[13 Tool-to-Tool Matching]]

$$\sigma^2_{observed}\approx\sigma^2_{process}+\sigma^2_{measurement},\qquad \sigma^2_{meas}=\sigma^2_{repeatability}+\sigma^2_{reproducibility}$$

## Components in a metrology context

| Component | Definition in a fab | How to measure |
|---|---|---|
| **Static repeatability**（靜態重複性）| Repeat N times without moving the wafer | 30× at one site |
| **Dynamic repeatability**（動態重複性）| Unload/reload between measurements (includes alignment, focus, PR) | 10–30 load cycles |
| **Reproducibility**（再現性）| Different days/operators/sessions on one tool | Repeat dynamic study over days |
| **Long-term stability** | Weeks–months on a monitor wafer | Daily monitor chart |
| **Tool-to-tool (matching)** | Same wafer on multiple tools | See [[13 Tool-to-Tool Matching]] |
| Site effect | Site-specific bias (pad edges, local non-uniformity) | Repeat at multiple sites |
| Recipe/model effect | Change with model/library version | Before/after comparison |

**Watch for measurement-induced change:** repeated measurement can alter the sample (resist shrink, UV-induced desorption/cleaning, charging, carbon deposition by e-beam). A "drift" during a repeatability study may be real sample change.

## Gauge R&R study design

- **Parts:** 5–10 wafers (or sites) spanning the process range — not all at nominal (otherwise %GRR of total variation looks terrible because part variation is tiny).
- **Appraisers:** in fab terms, tools, days, or load cycles.
- **Repeats:** 2–3+ per combination; randomize order.
- Analysis: **crossed two-way ANOVA** (parts × appraisers with interaction) → variance components.

$$\hat\sigma^2_{repeat}=MS_E,\quad \hat\sigma^2_{P\times O}=\frac{MS_{PO}-MS_E}{r},\quad \hat\sigma^2_{O}=\frac{MS_O-MS_{PO}}{pr},\quad \hat\sigma^2_{P}=\frac{MS_P-MS_{PO}}{or}$$

(negative estimates set to 0) — implemented in `gauge_rr()`.

## Acceptance metrics

| Metric | Formula | Common guideline |
|---|---|---|
| **P/T** (precision-to-tolerance)| $\frac{6\sigma_{meas}}{USL-LSL}$ (some use 5.15σ) | ≤ 10 % good, 10–30 % conditional, > 30 % not acceptable |
| %GRR of total variation | $\sigma_{meas}/\sigma_{total}$ | same bands |
| ndc (distinct categories) | $1.41\,\sigma_{part}/\sigma_{meas}$ | ≥ 5 |
| Precision/sensitivity | σ_meas vs smallest shift to detect | σ_meas ≤ shift/3 or better |

Guidelines are AIAG-style; **semiconductor sites define their own limits** (often tighter on P/T for critical layers). Use the site standard.

### Worked example (from `code/metro_tools.py` demo)
10 wafers (σ_part ≈ 0.25 nm), 3 tools with small biases, 3 repeats, σ_repeat 0.015 nm, spec 19–21 nm:

| Output | Value |
|---|---|
| σ_repeatability | 0.014 nm |
| σ_reproducibility (tool) | 0.017 nm |
| σ_GRR | 0.022 nm |
| P/T | 6.7 % |
| %GRR (of total) | 9.0 % |
| ndc | 15.7 |

Interpretation: acceptable; reproducibility (tool-to-tool bias) is the larger component → matching, not repeatability, is the improvement lever.

## Engineering objective
Measurement variation must be small relative to:
1. **Specification window** (P/T) — so disposition decisions are right.
2. **Process variation** (%GRR, ndc) — so SPC sees the process, not the gauge.
3. **The smallest process shift that matters** — so excursions are detected in time.

## Misclassification risk at the spec limit
If a wafer's true value is near USL, the probability of a wrong pass/fail is driven by σ_meas. **Guard-banding**（防護帶）: tighten acceptance limits by k·σ_meas to reduce false accepts — trade-off with false rejects.

Next: [[13 Tool-to-Tool Matching]].
