---
tags: [metro-thickness, matching, fleet]
chapters: [16]
created: 2026-10-06
---

# 13 · Tool-to-Tool Matching（機台間匹配）

← [[12 MSA and Gauge R&R]] · next → [[14 Calibration and Drift]]

## Why it matters
Production lots are dispatched to whichever qualified Metro tool is free. Tool bias therefore becomes **apparent process variation**, and with APC it becomes **real process variation** (see [[01 Role and Manufacturing Loop]]).

## Reference wafer example — do not jump to conclusions

| Tool | Thickness |
|---|---:|
| A | 20.02 nm |
| B | 20.08 nm |
| C | 20.71 nm |

Before declaring C bad: maybe A and B share the same (wrong) calibration standard, or C was recently recalibrated correctly. Matching tells you **consistency**; only reference/standards tell you **accuracy**.

## Investigation ladder (order matters — cheapest first)

1. Same reference wafer, same **site coordinates**, same orientation
2. Same **recipe version** (diff the recipe)
3. Same **model / n,k library version**
4. Calibration status & last calibration date
5. **Raw signal** comparison — overlay spectra/Ψ-Δ from both tools on the same site. If raw differs → hardware/calibration. If raw matches but output differs → recipe/model/software.
6. Hardware state: lamp hours, AOI, focus, spot size
7. Maintenance history — what changed just before the bias appeared?

## Matching statistics

**Paired bias:** $Bias_{A-B}=\overline{x_A-x_B}$ with a 95 % CI $\pm t_{0.975,n-1}\,s_d/\sqrt n$. Pair by *site*, not by wafer mean.

**Offset + slope (errors-in-variables):** both tools have noise → OLS underestimates slope. Use **Deming** or orthogonal regression:

$$T_B=b_0+b_1T_A$$

Demo (`deming()` in code): simulated $T_B=1.02T_A+0.10$ over 10–50 nm → recovered b₀ = 0.09, b₁ = 1.02. The paired mean bias was −0.70 nm with s_d = 0.27 nm — **the large s_d is the giveaway that the bias is thickness-dependent**: a single offset correction would leave ±0.4 nm errors at the range ends.

**Bland–Altman plot:** difference (A−B) vs mean ((A+B)/2). A sloped cloud = slope mismatch; funnel shape = noise differs between tools.

## Dependencies to check

| Dependence | How to see it | Typical cause |
|---|---|---|
| Offset | Constant difference | Calibration, reference offset, contamination on reference |
| Slope / range | Difference grows with d | Wavelength scale, AOI, n/k handling |
| Site | Difference varies by site | Spot size/pad spill, stage/focus |
| Wafer map | Pattern in difference map | Stage tilt, orientation, site mapping |
| Time | Difference trends | One tool drifting |
| Product/layer | Only certain stacks | Model sensitivity to hardware differences |

## Matching specification
Usually expressed relative to precision or tolerance (e.g., bias ≤ a fraction of the spec window, or a TMU-style combined metric: $TMU=\sqrt{\sigma^2_{precision}+\sigma^2_{matching}+\ldots}$). The value is site policy — ask for it ([[24 Onboarding Plan and Skill Matrix]] questions).

## Fixing a mismatch — preferred order
1. Fix the root cause (hardware, calibration, recipe sync).
2. Re-calibrate against traceable standards.
3. Only then, if the residual is a stable, understood offset: apply a **tool-specific offset/slope correction** under change control — documented, time-limited, and monitored. Corrections hide future drift if left unmanaged.

Next: [[14 Calibration and Drift]].
