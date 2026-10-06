---
tags: [metro-thickness, fitting, residuals, model-risk]
chapters: [18]
created: 2026-10-06
---

# 15 · Residuals, Fit Quality and Model Risk（殘差、擬合品質與模型風險）

← [[14 Calibration and Drift]] · next → [[16 Process Correlation and DOE]]

## Definitions

Residual: $r_i=S_{meas,i}-S_{model,i}(\hat\theta)$

Weighted objective: $\chi^2(\theta)=\sum_i\frac{[S_{meas,i}-S_{model,i}(\theta)]^2}{\sigma_i^2}$

Reduced chi-square: $\chi^2_\nu=\chi^2/(N-P)$ (N data points, P free parameters).
- $\chi^2_\nu\approx1$: model explains the data to within noise (if σ_i are honest).
- $\chi^2_\nu\gg1$: model error (systematic) or σ underestimated.
- $\chi^2_\nu\ll1$: σ overestimated, or overfitting.

Vendor GOF metrics vary (e.g., normalized "GOF" in 0–1, or MSE for SE). Learn exactly how your platform defines it and what normal values are **per recipe** — absolute GOF thresholds don't transfer between recipes.

## Reading residuals（判讀殘差）

| Residual pattern | Likely cause |
|---|---|
| White noise, no structure | Good model |
| Oscillation with the same period as fringes | Thickness or n slightly off; wrong n dispersion; fringe-order error |
| Growing at short wavelength (UV) | Missing roughness/interface layer; absorption (k) not modeled; contamination layer |
| Growing at long wavelength | Substrate/backside reflection, IR absorption, wavelength calibration |
| Localized feature at fixed λ | Absorption band / critical point not in dispersion model; lamp line artifact |
| Offset in Ψ or Δ across all λ | Angle-of-incidence or polarizer calibration error |
| Damped fringes in data vs model | Thickness non-uniformity within spot, bandwidth, depolarization |

**Plot residuals vs wavelength for a set of wafers (nominal + splits + edge sites).** A structure that appears on all wafers is a model/calibration issue; one that appears only on edge sites points to edge film physics or spot clipping.

## Parameter uncertainty and model risk

- Statistical uncertainty: $\sigma_{\theta_j}=\sqrt{C_{jj}}$ with $C=(J^TWJ)^{-1}\chi^2_\nu$.
- **Systematic (model) error is usually larger than statistical error**, and covariance matrices do not show it.
- Estimate model sensitivity by perturbation: vary each fixed parameter by its realistic uncertainty (e.g., n_SiN ±0.01, IL ±0.2 nm), refit, record Δd_CTQ. Root-sum-square the contributions → systematic uncertainty budget.

| Fixed parameter | Realistic uncertainty | Δd_CTQ | Comment |
|---|---|---|---|
| n_SiN @633 | ±0.01 | e.g. ±0.25 nm on 50 nm | dominant for thick nitride |
| IL thickness | ±0.2 nm | ~±0.2 nm | 1:1 trade with CTQ if optically similar |
| Roughness | ±0.3 nm | ±0.1 nm | |
| AOI | ±0.05° | ±0.05 nm | |
*(Fill with your own numbers — the table structure is the deliverable.)*

## Key principle — expanded

> Good fit quality is necessary but not sufficient.

A wrong model with enough free parameters can fit any one spectrum. **Validation must use information the fit didn't see**: reference metrology, known standards, deliberately different samples (splits), different tools, and time stability. Each validation type catches a different failure:

| Validation | Catches |
|---|---|
| Reference (TEM/XRR/AFM) | Absolute bias, wrong n/k |
| Standards | Calibration error |
| SEM/profile correlation | OCD geometry ambiguity |
| Electrical correlation | Device-relevant inconsistencies |
| Process splits / DOE | Slope ≠ 1, correlated parameter trade-offs |
| Cross-tool | Hardware-dependent model sensitivity |
| Time stability | Drift, contamination, aging |

## Production guardrails
- GOF threshold per recipe + **GOF trend chart** (GOF degrading slowly is an early warning of process composition drift).
- Bound-hit flag on every floating parameter.
- Monitor "nuisance" parameters (roughness, IL, n) in SPC even if not CTQ — they often move first.
- Store raw spectra for re-analysis — essential for post-mortems and model updates.

Next: [[16 Process Correlation and DOE]].
