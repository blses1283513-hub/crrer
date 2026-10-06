---
tags: [metro-thickness, XRR, XRF, FTIR, profilometry]
chapters: [8]
created: 2026-10-06
---

# 07 · XRR, XRF, FTIR and Profilometry

← [[06 OCD Scatterometry]] · next → [[08 Film Stack and Dispersion Models]]

## 8.1 XRR — X-ray Reflectometry（X 光反射率）

**Physics.** For X-rays the refractive index is slightly below 1: $n=1-\delta+i\beta$, with $\delta\propto\rho_e\lambda^2$ (electron density). Total external reflection occurs below the **critical angle** $\theta_c\approx\sqrt{2\delta}$; for Si with Cu Kα (λ = 0.154 nm), θc ≈ 0.22°. The critical angle gives **density**.

**Kiessig fringes（Kiessig 干涉條紋）.** Above θc, interference between the top and bottom interfaces gives oscillations with period

$$\Delta\theta\approx\frac{\lambda}{2d}\quad(\theta\gg\theta_c)$$

e.g. d = 20 nm, Cu Kα → Δθ ≈ 0.0039 rad ≈ 0.22°. Thickness from the fringe period is nearly model-independent — that's why XRR is a **reference method** for optical models.

**Roughness.** Interface roughness σ damps reflectivity (Névot–Croce factor ≈ $\exp(-2k_zk_z'\sigma^2)$); fringes decay faster at high angle.

**Fitting.** Parratt recursion over layers (d, ρ, σ per layer). Low-contrast interfaces (e.g. SiO₂ on Si: similar density) give weak fringes; high-Z on low-Z (HfO₂ on SiO₂) give strong fringes.

**Limits:** needs smooth, laterally uniform films over a large (mm-scale) footprint; slow; thick films (> ~200–300 nm) give fringes too fine to resolve.

## 8.2 XRF — X-ray Fluorescence（X 光螢光）

Primary X-rays eject core electrons; the atom emits element-characteristic lines (e.g., Ti Kα 4.51 keV, Cu Kα 8.05 keV, Hf Lα 7.90 keV).

Intensity for a film of mass thickness $m=\rho t$:

$$ I = I_\infty\left[1-e^{-\mu^* m}\right],\qquad \mu^*=\frac{\mu(E_0)}{\sin\psi_{in}}+\frac{\mu(E_f)}{\sin\psi_{out}} $$

- Thin-film regime ($\mu^*m\ll1$): $I\approx I_\infty\mu^*m$ — **linear in mass thickness**.
- Thick: saturates at $I_\infty$ (infinite thickness).
- **XRF gives mass per area, not thickness.** $t=m/\rho$ → a density change (e.g., porous vs dense TiN, different PVD condition) reads as a thickness change. Calibrate with standards or XRR density.
- Substrate fluorescence attenuation by the film can measure films whose own lines are unusable.
- Composition: ratio of lines (e.g. Ti/N not accessible for N — light elements are weak; use other techniques).

**Use cases:** barrier/liner (Ta, TaN, Ti, TiN), seed Cu, Co, W, high-k (Hf, Zr), dopant-in-film content.

## 8.3 FTIR / IR metrology（傅立葉轉換紅外光譜）

- **Epi thickness:** interference fringes in IR reflectance arise because heavily doped substrate has free-carrier-modified n (Drude); the lightly doped epi on top is the "film". Standard method in industry (ASTM F95 historically). Thickness from fringe spacing/FFT, refined with model including the transition region.
- **Composition:** BPSG boron/phosphorus wt%, Si–H / N–H bond content in PECVD SiN (relates to n, stress, and etch rate), carbon in low-k films.
- Carrier concentration / doping profiles in some configurations.

## 8.4 Profilometry and AFM（輪廓儀 / 原子力顯微鏡）

$$ d\approx\Delta z = z_{film}-z_{substrate} $$

| Method | Resolution | Notes |
|---|---|---|
| Stylus profiler | ~nm vertical | Contact force can deform soft films; tip radius convolves features |
| AFM | sub-nm vertical | Small scan area; tip shape; good for dishing/erosion, roughness |
| White-light interferometry | sub-nm vertical | Non-contact; transparent films cause phase errors |

**Use as reference:** etch a step (masked etch or lift-off) in a blanket film, measure step with AFM, compare to optical model thickness → validates the n/k + model combination. Caveats: the etch must stop exactly at the substrate (over-etch into Si adds height), and surface layers differ between etched and protected areas.

## Choosing a reference for validation

| Optical result to validate | Best reference |
|---|---|
| Single blanket dielectric 2–100 nm | XRR + TEM spot check |
| Ultrathin high-k + interfacial layer | TEM (EELS) + XRR + XPS |
| Metal liner | XRF (with standards) + TEM |
| Patterned remaining film | XSEM/TEM on cross-section, OCD splits |
| Thick dielectric (µm) | XSEM, profilometer step |

Next: [[08 Film Stack and Dispersion Models]].
