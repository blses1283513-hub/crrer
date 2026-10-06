---
tags: [metro-thickness, modeling, dispersion, film-stack]
chapters: [9]
created: 2026-10-06
---

# 08 · Film Stack and Optical Model Construction（膜堆疊與光學模型建構）

← [[07 XRR XRF FTIR Profilometry]] · next → [[09 Recipe Development]]

## 9.1 Write the real stack — including the "invisible" layers

```text
Ambient (air)
├── (contamination / adsorbed layer, 0.1–1 nm — matters for thin films)
├── SiN            ← CTQ
├── (SiON transition?)
├── SiO₂
├── Poly-Si        (grain structure → EMA c-Si/a-Si/void)
├── (native/interfacial oxide 0.5–1.5 nm)
└── Si substrate
```

Sources for the true stack: process flow / route sheet, upstream module owners, TEM cross-section, XPS depth profile. **Ask "what is between each pair of layers?"** — interfacial oxides, intermixing, nitrided interfaces, silicide.

## Dispersion models（色散模型）

| Model | Formula (core) | Use for |
|---|---|---|
| **Cauchy** | $n=A+\frac{B}{\lambda^2}+\frac{C}{\lambda^4}$, k≈0 (or Urbach tail) | Transparent dielectrics in transparent range (SiO₂, resists) |
| **Sellmeier** | $n^2=1+\sum\frac{A_j\lambda^2}{\lambda^2-\lambda_j^2}$ | Transparent materials, physically better extrapolation |
| **Tauc–Lorentz** (Jellison–Modine) | ε₂ = Lorentz oscillator × Tauc gap for E>E_g, 0 below; ε₁ via Kramers–Kronig | Amorphous semiconductors/dielectrics with band gap: a-Si, SiN, high-k (HfO₂), TiO₂ |
| **Cody–Lorentz** | Like TL with Urbach tail below gap | Films with sub-gap absorption |
| **Lorentz / harmonic oscillators** | $\varepsilon=\varepsilon_\infty+\sum\frac{A_jE_j^2}{E_j^2-E^2-i\Gamma_jE}$ | General absorbing materials, IR phonons |
| **Drude** | $\varepsilon=\varepsilon_\infty-\frac{\omega_p^2}{\omega^2+i\Gamma\omega}$ | Metals (TiN, thin metals), free carriers (doped Si in IR) |
| **B-spline / point-by-point** | Free-form, KK-constrained | Characterization (not production — too many parameters) |
| **EMA (Bruggeman)** | $\sum_i f_i\frac{\varepsilon_i-\varepsilon}{\varepsilon_i+2\varepsilon}=0$ | Mixtures: roughness (50 % film/50 % void), poly-Si, porosity, interfacial mixing |

**Kramers–Kronig consistency（KK 一致性）:** n and k are not independent; physical models (TL, Lorentz, Drude) are KK-consistent by construction. A free-form n,k pair that violates KK may fit one sample but fails on others.

## Representative optical constants at 633 nm (illustrative only)

| Material | n | k | Notes |
|---|---|---|---|
| Thermal SiO₂ | 1.457 | 0 | Very stable reference |
| LPCVD Si₃N₄ | ~2.00 | ~0 | PECVD 1.85–2.1, Si-rich higher |
| ALD Al₂O₃ | ~1.64 | 0 | Depends on T, H content |
| HfO₂ | ~1.9–2.1 | 0 | Crystalline phase raises n slightly |
| c-Si | 3.88 | 0.02 | k rises steeply in UV |
| a-Si | ~4.2–4.6 | ~0.5–1.0 | Depends on H content |
| TiN | metallic (Drude) | — | Opaque above ~40 nm |

Use your site's validated libraries; these values only build intuition.

## 9.2 Model mistakes to recognize immediately

| Mistake | Symptom | Fix |
|---|---|---|
| Wrong layer order | Plausible GOF on nominal, poor across splits; parameters drift unphysically | Re-derive stack from route; compare with TEM |
| Missing interfacial layer | Top-layer thickness offset vs XRR/TEM; residual structure in UV | Add fixed/constrained IL |
| Wrong n/k | Thickness bias proportional to d; GOF degrades on thicker samples | Re-characterize on thick blanket film, multi-sample analysis |
| Too many free parameters | High correlation, large parameter scatter, values at bounds | Fix/constrain; fit only CTQ + 1–2 nuisance |
| Ignoring roughness | Thickness slightly high/low, UV residual | EMA roughness layer (constrain from AFM) |
| Ignoring backside reflection (transparent substrate) | Depolarization, wiggles | Model incoherent backside or use backside-roughened substrate |
| Ignoring non-uniformity within spot | Depolarization, fringe damping on thick films | Thickness non-uniformity / bandwidth model |

### Multi-sample analysis（多樣品聯合分析）
Fit several wafers of **different thicknesses** simultaneously with **shared n,k** and individual d. Different thicknesses decorrelate n from d because the interference phase depends on n·d while the amplitude/dispersion depends on n alone. This is the standard way to build a robust n/k library.

### Constrain-or-fit heuristic

```text
Known & stable           → fix
Critical unknown (CTQ)   → fit
Correlated with CTQ      → characterize separately, then fix or feed forward
Weakly sensitive         → fix to characterized value; monitor GOF
Physically bounded       → constrain with realistic bounds; alarm on bound hit
```

Next: [[09 Recipe Development]].
