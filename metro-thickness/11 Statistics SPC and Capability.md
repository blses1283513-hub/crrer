---
tags: [metro-thickness, statistics, SPC, Cpk]
chapters: [14]
created: 2026-10-06
---

# 11 · Statistics, SPC, Cp and Cpk（統計製程管制與製程能力）

← [[10 Sampling Wafer Maps and Uniformity]] · next → [[12 MSA and Gauge R&R]]

## Basic statistics

$$\bar x=\frac1N\sum x_i,\qquad s=\sqrt{\frac{1}{N-1}\sum(x_i-\bar x)^2}$$

Robust alternatives for outlier-prone site data: median, MAD ($\hat\sigma\approx1.4826\cdot\text{MAD}$), IQR.

## Variance structure — what "sigma" means

Thickness data are **nested**: lot → wafer → site → repeat measurement.

$$\sigma^2_{total}=\sigma^2_{lot}+\sigma^2_{wafer}+\sigma^2_{site}+\sigma^2_{meas}$$

Which σ goes into a control chart or Cpk must match the decision:
- Chart of **wafer means**: variation = lot + wafer + (site+meas)/n_sites.
- Using site-level σ for limits on wafer means → limits too narrow → constant false alarms.
- `nested_variance()` in `code/metro_tools.py` gives a first-pass split.

## Control charts（管制圖）

| Chart | Plots | Use |
|---|---|---|
| X̄–R / X̄–S | Subgroup mean & range/std (e.g., sites in a wafer) | Wafer-level mean + within-wafer spread |
| I–MR | Individual + moving range | One value per wafer/lot (e.g., monitor wafer) |
| EWMA | Exponentially weighted mean | Small sustained shifts (0.5–1.5σ) |
| CUSUM | Cumulative deviation | Small shifts, fast detection |
| Multivariate (Hotelling T²) | Several correlated parameters | d + n + GOF jointly |

**Control limits ≠ spec limits.** Control limits come from the process's own stable history (±3σ of the plotted statistic); spec limits come from the product. A process can be in control and incapable, or capable and out of control.

### Run rules（判異規則）

| Rule | Condition | Typical meaning |
|---|---|---|
| R1 | 1 point beyond 3σ | Sudden large shift / outlier |
| R2 | 2 of 3 beyond 2σ (same side) | Medium shift |
| R3 | 4 of 5 beyond 1σ (same side) | Small shift |
| R4 | 8 in a row on one side | Mean shift |
| R5 | 6 in a row increasing/decreasing | Trend / drift |
| R6 | 15 in a row within 1σ | Limits too wide, stratified sampling (mixing streams) |

Each added rule raises the false-alarm rate. In the code demo, R3 fired *before* the real shift — a false alarm. **Run rules are evidence to investigate, not proof.**

### EWMA and CUSUM

$$z_i=\lambda x_i+(1-\lambda)z_{i-1},\quad \text{UCL/LCL}=\mu_0\pm L\sigma\sqrt{\tfrac{\lambda}{2-\lambda}\left[1-(1-\lambda)^{2i}\right]}$$

(λ ≈ 0.1–0.3, L ≈ 2.7–3.)

$$C_i^+=\max(0,\,x_i-\mu_0-k+C_{i-1}^+),\quad C_i^-=\max(0,\,\mu_0-k-x_i+C_{i-1}^-)$$

(k = 0.5σ, h = 4–5σ.)

## Capability（製程能力）

$$C_p=\frac{USL-LSL}{6\sigma},\qquad C_{pk}=\min\left(\frac{USL-\mu}{3\sigma},\frac{\mu-LSL}{3\sigma}\right)$$

- **Cp/Cpk** use within-subgroup (short-term) σ; **Pp/Ppk** use overall (long-term) σ. Ppk < Cpk means between-subgroup variation (drift, lot effects).
- Cp − Cpk measures off-centering.

| Cpk | Sigma distance to nearest spec | Approx. ppm out (one side, normal) |
|---|---|---|
| 1.00 | 3σ | 1350 |
| 1.33 | 4σ | 32 |
| 1.67 | 5σ | 0.3 |
| 2.00 | 6σ | 0.001 |

### Cpk has wide uncertainty with small n
Bissell approximation: $SE(\hat C_{pk})\approx\sqrt{\frac1{9n}+\frac{C_{pk}^2}{2(n-1)}}$.
For the booklet's 6-point example, Cpk = 4.85 but the 95 % CI is roughly **1.8 – 7.9** (computed by `cpk_ci`). Don't report Cpk from a handful of points without its interval.

### Measurement error inflates observed sigma

$$\sigma^2_{obs}=\sigma^2_{proc}+\sigma^2_{meas}\;\Rightarrow\;C_{pk,obs}<C_{pk,true}$$

If σ_meas = 0.5 σ_proc, observed σ is 12 % larger → Cpk reads ~11 % low. A poor gauge makes a good process look bad (and hides real shifts).

### Non-normal data
Thickness can be skewed (bounded processes, mixtures of chambers). Check the distribution first; if it's a **mixture** (two chambers), split it — capability of a mixture is meaningless. For truly non-normal data use percentile-based capability.

## SPC questions — and which tool answers each

| Question | Tool |
|---|---|
| Is the mean moving? | X̄ chart, EWMA, CUSUM |
| Is sigma increasing? | S/R chart, within-wafer σ chart |
| Trend? | R5, regression vs time/counter |
| Abrupt step? | R1/R4, change-point analysis |
| Distribution changing? | Histogram by period, normal quantile plot |
| Tool/chamber split? | Chart by chamber, ANOVA, box plots |
| Metro drifting? | Monitor/reference wafer chart on the same Metro tool |

Next: [[12 MSA and Gauge R&R]].
