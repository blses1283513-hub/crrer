---
tags: [metro-thickness, equations, cheat-sheet]
chapters: [34]
created: 2026-10-06
---

# 25 · Core Equations — Cheat Sheet（核心公式速查）

← [[24 Onboarding Plan and Skill Matrix]] · next → [[26 Glossary]]

## Optics
| Name | Equation | Note |
|---|---|---|
| Snell | $n_0\sin\theta_0=n_j\sin\theta_j$ | complex n allowed |
| Fresnel s | $r_s=\frac{n_i\cos\theta_i-n_j\cos\theta_j}{n_i\cos\theta_i+n_j\cos\theta_j}$ | |
| Fresnel p | $r_p=\frac{n_j\cos\theta_i-n_i\cos\theta_j}{n_j\cos\theta_i+n_i\cos\theta_j}$ | |
| Single film | $r=\frac{r_{01}+r_{12}e^{2i\beta}}{1+r_{01}r_{12}e^{2i\beta}}$, $\beta=\frac{2\pi}{\lambda}n_1d\cos\theta_1$ | |
| Interference | $2nd\cos\theta=m\lambda$ | extrema condition (ignoring interface phase) |
| Fringe thickness | $d\approx\frac{\lambda_1\lambda_2}{2n(\lambda_1-\lambda_2)}$ | adjacent extrema |
| Complex index | $\tilde n=n+ik$, $\varepsilon=\tilde n^2$ | |
| Absorption | $\alpha=4\pi k/\lambda$ | |
| Ellipsometry | $\rho=r_p/r_s=\tan\Psi e^{i\Delta}$ | |
| Brewster | $\tan\theta_B=n_2/n_1$ | Si ≈ 75.5° @633 nm |
| Cauchy | $n=A+B/\lambda^2+C/\lambda^4$ | |
| Bruggeman EMA | $\sum f_i\frac{\varepsilon_i-\varepsilon}{\varepsilon_i+2\varepsilon}=0$ | |
| Resist swing period | $\Delta T=\lambda/(2n)$ | |

## X-ray
| Name | Equation |
|---|---|
| X-ray index | $n=1-\delta+i\beta$ |
| Critical angle | $\theta_c\approx\sqrt{2\delta}$ |
| Kiessig period | $\Delta\theta\approx\lambda/(2d)$ |
| XRF thin-film | $I\approx I_\infty\mu^*\rho t$ (thin), $I=I_\infty(1-e^{-\mu^*\rho t})$ |

## Process
| Name | Equation |
|---|---|
| ALD | $d\approx N\cdot GPC$ |
| CVD rate | $1/R=1/k_s+1/h_g$, $k_s=k_0e^{-E_a/k_BT}$ |
| Deal–Grove | $x^2+Ax=B(t+\tau)$ |
| Etch rate | $ER=(d_{before}-d_{after})/t$ |
| Δ uncertainty | $\sigma_\Delta^2=\sigma_0^2+\sigma_1^2-2\rho\sigma_0\sigma_1$ |
| CMP (Preston) | $RR=K_pPV$ |
| CMP removal | $R=T_{pre}-T_{post}$; $t=(T_{pre}-T_{target})/RR$ |
| Sheet resistance | $R_s=\rho/t$ |
| Oxide capacitance | $C_{ox}=\varepsilon_{ox}/t_{ox}$ |

## Statistics
| Name | Equation |
|---|---|
| Mean | $\bar x=\frac1N\sum x_i$ |
| Sample std | $s=\sqrt{\frac1{N-1}\sum(x_i-\bar x)^2}$ |
| Uniformity (half-range) | $\frac{T_{max}-T_{min}}{2T_{mean}}\times100\%$ |
| Uniformity (CV) | $\sigma/\mu\times100\%$ |
| Cp | $(USL-LSL)/6\sigma$ |
| Cpk | $\min\left(\frac{USL-\mu}{3\sigma},\frac{\mu-LSL}{3\sigma}\right)$ |
| Cpk SE (Bissell) | $\sqrt{\frac1{9n}+\frac{C_{pk}^2}{2(n-1)}}$ |
| Variance sum | $\sigma^2_{obs}=\sigma^2_{proc}+\sigma^2_{meas}$ |
| P/T | $6\sigma_{meas}/(USL-LSL)$ |
| ndc | $1.41\,\sigma_{part}/\sigma_{meas}$ |
| Bias | $Bias_{A-B}=\bar x_A-\bar x_B$ |
| Correlation | $r=\frac{\sum(x_i-\bar x)(y_i-\bar y)}{\sqrt{\sum(x_i-\bar x)^2\sum(y_i-\bar y)^2}}$ |
| EWMA | $z_i=\lambda x_i+(1-\lambda)z_{i-1}$ |
| CUSUM | $C_i^+=\max(0,x_i-\mu_0-k+C_{i-1}^+)$ |
| Weighted LSQ | $\chi^2=\sum\frac{(S_{meas}-S_{model}(\theta))^2}{\sigma_i^2}$ |
| Reduced χ² | $\chi^2_\nu=\chi^2/(N-P)$ |
| Parameter covariance | $C=(J^TWJ)^{-1}$ |
| Robust sigma | $\hat\sigma=1.4826\cdot MAD$ |

Next: [[26 Glossary]].
