---
tags: [metro-thickness, OCD, scatterometry, RCWA]
chapters: [7]
created: 2026-10-06
---

# 06 · OCD / Scatterometry（光學關鍵尺寸／散射量測）

← [[05 Ellipsometry]] · next → [[07 XRR XRF FTIR Profilometry]]

## Concept
A periodic structure (grating) in a measurement box diffracts light. With pitch smaller than the wavelength, only the zeroth order propagates back; its spectrum (reflectance, SE Ψ/Δ, or full Mueller matrix, sometimes vs angle/azimuth) encodes the geometry. A parameterized profile model + an electromagnetic solver maps geometry → spectrum; regression maps spectrum → geometry.

Outputs: top/middle/bottom CD, height/depth, sidewall angle (SWA), footing, recess, remaining film under/over the grating, overlay (in specialized targets).

## Electromagnetic solver: RCWA（嚴格耦合波分析）
1. Slice the profile into layers with z-independent permittivity.
2. Expand ε(x) and fields in Fourier series (diffraction orders ±N).
3. Solve the eigenproblem per slice; match boundary conditions (S-matrix for stability).
4. Accuracy vs. speed: number of orders, number of slices, staircase approximation of slopes.
   Convergence check: increase orders until spectrum change ≪ noise. Too few orders → systematic model error that looks like a "profile" change.

## Library vs. real-time regression

| Approach | Pros | Cons |
|---|---|---|
| Pre-computed library（模型庫）| Fast in production | Grid resolution, interpolation error, must rebuild when model changes |
| Real-time regression | Flexible, exact solver | Compute cost, local minima |
| ML / hybrid | Fast inference, can learn from reference data | Extrapolation risk, needs labeled reference |

## Identifiability（可辨識性）— the core OCD risk
A good spectral fit does **not** imply the right geometry. With 10+ floating parameters, combinations can produce nearly identical spectra.

Tools to manage it:
- **Sensitivity analysis:** ∂S/∂p per parameter vs. noise — if a 1 nm change of p produces less signal than 3σ noise, p is not measurable.
- **Correlation matrix** (see [[05 Ellipsometry]]): fix or link correlated parameters (e.g., tie bottom-CD to top-CD via SWA).
- **Precision-to-sensitivity screening** before building the library.
- **Reference correlation:** CD-SEM (top CD), XSEM/TEM (profile), AFM (height), process splits (DOE with known focus/dose/etch-time deltas) — the slope of OCD vs reference must be ≈1 across the split range.
- **Hybrid metrology:** feed upstream film thickness (from blanket SE before patterning) or CD-SEM CD into the model.
- **Cross-wafer robustness:** good residuals on center *and* edge, and on wafers from the process-window corners, not just nominal.

## Typical OCD failure modes

| Symptom | Likely cause |
|---|---|
| Fit OK at nominal, poor on split wafers | Model too constrained / wrong profile shape |
| Parameter pinned at library bound | Process outside library range, or compensation for wrong fixed parameter |
| Two parameters move in lockstep across wafers | Correlation — not real process co-variation |
| Good OCD, poor match to XSEM in slope | Sensitivity insufficient, or fixed n/k of underlying film is off |
| Sudden shift after upstream change | Underlying film n/k or thickness changed but is fixed in model → feed-forward needed |

## Validation package for a new OCD model (checklist)
- [ ] Sensitivity & correlation report for all floating parameters
- [ ] Convergence check of RCWA settings
- [ ] Reference correlation: slope, offset, R², residual vs reference
- [ ] Process-split tracking (does OCD see the intentional deltas with the right sign and magnitude?)
- [ ] Static/dynamic repeatability, multi-tool matching
- [ ] Throughput within plan

Next: [[07 XRR XRF FTIR Profilometry]].
