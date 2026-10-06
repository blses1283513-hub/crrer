---
tags: [metro-thickness, correlation, DOE]
chapters: [19]
created: 2026-10-06
---

# 16 · Process-to-Metrology Correlation and DOE（製程—量測相關性與實驗設計）

← [[15 Residuals Fit Quality and Model Risk]] · next → [[17 Root Cause Framework]]

$$\text{Process parameter}\rightarrow\text{Film property}\rightarrow\text{Metro signal}\rightarrow\text{Measured CTQ}$$

Every arrow has a transfer function. Example: ALD T ↑ → GPC ↑ (outside window) → d ↑ and n may shift → spectrum shifts → recipe reports d ↑ (and if n is fixed, part of the n change is mis-assigned to d).

## Correlation coefficient

$$r=\frac{\sum(x_i-\bar x)(y_i-\bar y)}{\sqrt{\sum(x_i-\bar x)^2\sum(y_i-\bar y)^2}}$$

Booklet example: T = 300…320 °C vs d = 19.4…20.4 nm → r ≈ 0.998, slope ≈ 0.05 nm/°C.

### Correlation traps（相關性陷阱）

| Trap | Example | Defense |
|---|---|---|
| Confounding（混淆）| Thickness and chamber temperature both trend with time since PM | Include time/PM counter in the model; DOE |
| Restricted range | Production T varies ±0.5 °C → r looks ~0 even though dT matters | Use designed splits beyond normal range |
| Outlier-driven r | One excursion wafer creates r = 0.8 | Plot first; robust (Spearman) correlation |
| Mixture of groups | Two chambers with different offsets create spurious correlation | Analyze within chamber (stratify) |
| Multiple testing | Scanning 500 FDC sensors guarantees some "significant" r | Correct for multiplicity; require physics |
| Reverse/common cause | Metro tool lab temperature drives both "sensor" and Metro | Think about mechanism |

> Correlation is evidence of association, not proof of causation.

## Design of Experiments（實驗設計）

| Design | Runs | Use |
|---|---|---|
| One-factor split | 3–5 levels | Sensitivity of one knob; Metro split-tracking check |
| 2^k full factorial | 2^k (+ center points) | Main effects + interactions, k ≤ 4 |
| 2^(k−p) fractional | fewer | Screening many factors (aliasing!) |
| Response surface (CCD, Box–Behnken) | ~15–30 | Optimize, curvature |
| Split-lot / split-wafer | — | Practical fab implementation |

Principles: **randomize** run order (break time confounding), **block** by day/chamber, **replicate** center points to estimate pure error, keep Metro constant (same tool, same recipe) during the DOE — or include it as a blocked factor.

### Metro-specific use of DOE
1. **Split tracking:** process team deliberately varies d (e.g., ±5 %, ±10 % deposition time). Metro must report the same deltas: slope ≈ 1 vs expected or vs reference.
2. **Nuisance robustness:** vary non-CTQ parameters (underlying film thickness, anneal) — CTQ should not move.
3. **Model discrimination:** run candidate models on the DOE; prefer the one whose fitted parameters follow the design structure (no spurious interactions).

Next: [[17 Root Cause Framework]].
