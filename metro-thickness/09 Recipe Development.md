---
tags: [metro-thickness, recipe, development]
chapters: [10, 11]
created: 2026-10-06
---

# 09 · Recipe Development & Translating Tool Output（量測配方開發與輸出轉譯）

← [[08 Film Stack and Dispersion Models]] · next → [[10 Sampling Wafer Maps and Uniformity]]

## 10. Anatomy of a production recipe

| # | Block | Content | Typical failure |
|---|---|---|---|
| 1 | Measurement setup | Wavelength range, AOI, spot, integration time, averaging | Low SNR, saturation |
| 2 | Wafer recognition | Notch/flat, ID read, wafer size, layer | Wrong orientation → map rotated |
| 3 | Site coordinates | Die/pad coordinates, edge exclusion | Off-pad measurement on some products |
| 4 | Focus / alignment | Pattern recognition (PR) model, global & site alignment | PR failure on new layer contrast |
| 5 | Signal acquisition | Raw spectrum, reference correction | Lamp/reference drift |
| 6 | Film-stack model | Layers, order, interfaces | Missing layer |
| 7 | Optical constants | n/k library entries & versions | Library change not controlled |
| 8 | Fit parameters | Floats & starting values | Local minimum, fringe-order hop |
| 9 | Constraints | Bounds, links | Bound hits hide problems |
| 10 | Quality checks | GOF threshold, bound-hit flag, outlier rule | Thresholds too loose/tight |
| 11 | Data output | Parameter names, units, summary statistics | Name mismatch breaks SPC chart |
| 12 | SPC integration | Chart mapping, limits | Wrong chart, wrong subgroup |

**Version control:** every change to model, n/k, site map or GOF threshold gets a recipe revision, a change record, and a before/after comparison on reference wafers. Many "excursions" turn out to be uncontrolled recipe edits.

## The development loop — with exit criteria

| Stage | Exit criterion (example) |
|---|---|
| Define CTQ | CTQ, spec (LSL/USL), target, required sensitivity documented |
| Understand film/process | Stack, expected n/k range, process window agreed with module owner |
| Choose technology | Sensitivity analysis shows CTQ signal ≫ noise across range |
| Reference data | Splits covering ≥ process window ± margin; TEM/XRR on selected samples |
| Build model | Physically justified layers; dispersion models selected |
| Fit dev data | GOF acceptable across all splits, not just nominal |
| Residuals | No systematic structure ([[15 Residuals Fit Quality and Model Risk]]) |
| Sensitivity/correlation | CTQ correlation with nuisance < ~0.9; parameter uncertainty ≪ tolerance |
| Reference cross-check | Slope ≈ 1, offset understood, R² high across splits |
| Repeatability | P/T and %GRR targets met ([[12 MSA and Gauge R&R]]) |
| Uniformity | Wafer maps physically plausible; edge sites OK |
| Tool matching | Within matching spec on all qualified tools ([[13 Tool-to-Tool Matching]]) |
| Release | Change control, SPC set-up, owner sign-off |

### Sensitivity analysis — quick math
For CTQ p with spectral sensitivity $s_i=\partial S_i/\partial p$ and noise σ_i:

$$\sigma_p\approx\left(\sum_i\frac{s_i^2}{\sigma_i^2}\right)^{-1/2}\quad\text{(single free parameter)}$$

With other free parameters, use the full covariance $(J^TWJ)^{-1}$; correlation inflates σ_p. Compare σ_p with tolerance: target $6\sigma_p/(USL-LSL)\le 0.1$–0.3.

## What makes a strong manufacturing recipe — operational tests

| Attribute | Test |
|---|---|
| Sensitive to CTQ | DOE splits detected with correct sign/magnitude |
| Insensitive to nuisance | Vary nuisance (e.g., underlying layer ±5 %); CTQ moves < tolerance/10 |
| Stable over time | Monitor wafer flat over weeks; no GOF trend |
| Robust over process window | GOF and parameter sanity at window corners |
| Fast enough | Time per wafer × sampling plan ≤ capacity |
| Correlated to reference | Slope/offset/R² documented |
| Statistically capable | P/T, %GRR, ndc pass |
| Explainable | You can draw the stack and say why each parameter is fixed or fitted |

## 11. Tool output vs. what Process wants

| Level | Example | Who consumes it | Typical question |
|---|---|---|---|
| Raw signal | Intensity vs λ | Metro only | Is the hardware healthy? |
| Optical result | Ψ, Δ, R | Metro | Does the data look like the expected stack? |
| Model result | n, k, d, GOF | Metro | Is the fit trustworthy? |
| Manufacturing | Mean d | Process, SPC | Is the process centered? |
| Wafer | Uniformity, radial profile | Process, Equipment | Is the chamber uniform? |
| Statistical | Cpk, trend | Process, management | Is the process capable and stable? |
| Process | Deposition-rate drift | Process, APC | Which knob moved? |
| Device | Vt, C_ox, R_s, yield | PI, Yield | Does it matter for the product? |

The translation skill: **go both directions.** Up ("the spectrum shows a new feature at 300 nm → probably interfacial oxidation → thickness reads +0.3 nm but the CTQ film is unchanged") and down ("PI says Vt shifted +20 mV → which thickness would explain it? Is that within our measurement resolution?").

Next: [[10 Sampling Wafer Maps and Uniformity]].
