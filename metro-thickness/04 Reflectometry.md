---
tags: [metro-thickness, optics, reflectometry]
chapters: [5]
created: 2026-10-06
---

# 04 · Reflectometry（反射光譜量測）

← [[03 Metrology Technology Map]] · next → [[05 Ellipsometry]]

## 5.1 Physics from first principles

### Fresnel coefficients（菲涅耳係數）
At an interface i→j (complex index $\tilde n=n+ik$, angles from Snell's law $n_i\sin\theta_i=n_j\sin\theta_j$):

$$ r_s=\frac{n_i\cos\theta_i-n_j\cos\theta_j}{n_i\cos\theta_i+n_j\cos\theta_j},\qquad
   r_p=\frac{n_j\cos\theta_i-n_i\cos\theta_j}{n_j\cos\theta_i+n_i\cos\theta_j} $$

At normal incidence: $R=\left|\frac{n_i-n_j}{n_i+n_j}\right|^2$. Air/Si at 633 nm (n≈3.88): R ≈ 35 %.

### Single film（單層膜 Airy 公式）

$$ r=\frac{r_{01}+r_{12}e^{2i\beta}}{1+r_{01}r_{12}e^{2i\beta}},\qquad \beta=\frac{2\pi}{\lambda}\,n_1 d\cos\theta_1 $$

R(λ) oscillates; maxima/minima occur when the round-trip phase $2\beta$ changes by 2π — the booklet's $2nd\cos\theta=m\lambda$ (plus interface phase shifts).

### Thickness from fringe spacing（由干涉條紋間距估厚）
Between adjacent extrema at wavelengths λ₁ > λ₂ (normal incidence, n ~ constant):

$$ d\approx\frac{\lambda_1\lambda_2}{2n(\lambda_1-\lambda_2)} $$

Equivalently, fringes are periodic in wavenumber $\nu=1/\lambda$ with period $\Delta\nu = 1/(2nd)$ → **FFT of R(ν)** gives d directly for thick films (> ~1 µm). This is also how you get a starting guess and avoid fringe-order ambiguity.

Worked example: extrema at 600 and 500 nm in a SiO₂ film (n≈1.46): d ≈ 600·500/(2·1.46·100) ≈ 1.03 µm.

### Why thin films are hard for reflectometry
For d ≪ λ/(4n) there is less than one fringe in the window. R changes only weakly (∝ d² in the leading term for a transparent film on a substrate where the d-linear term is small), and **n and d become strongly correlated** — only an "optical thickness" like $(n^2-1)d$ is well determined. Remedies: shorter wavelengths (DUV), multiple angles, polarization, or switching to SE (phase information).

## 5.2 Signal path and what can go wrong

| Stage | Health check | Failure signature |
|---|---|---|
| Source（光源: deuterium/halogen/Xe）| Lamp intensity & hours | Noisy short-λ end, gradual drift as lamp ages |
| Optics / spectrometer | Wavelength calibration (lamp lines), stray light | Fringe position error → thickness bias ∝ d |
| Reference | Bare-Si reference measurement for absolute R | Absolute R wrong → n/k error, thin-film bias |
| Focus | Auto-focus repeatability | Intensity drop, NA change → angle spread error |
| Detector | Dark current, linearity, saturation | Clipped peaks, non-linear R |
| Pattern recognition | Correct pad found | Wrong-structure measurement: random site outliers |

**Absolute reflectance** requires calibrating against a known reference (e.g., bare Si with a known native oxide). The native oxide on the reference (~1–2 nm) and any **contamination growth** on it propagate into every measurement — classic source of slow drift.

## 5.3 Recipe-level knobs — and why each matters

| Knob | Trade-off |
|---|---|
| Wavelength range | DUV adds thin-film sensitivity but needs stable DUV source; IR helps thick films/penetration |
| Angle of incidence (if variable) | Oblique adds polarization contrast |
| Spot size | Small → fits pads; large → better SNR, averages roughness |
| Focus offset | Defocus tolerance vs. pad edge contamination |
| Number of sites | Information vs. throughput |
| Fit parameters & bounds | Freedom vs. correlation; bounds hide problems if hit |
| Wavelength weighting / exclusion | Exclude noisy ends or absorption regions — but document it |

## Demonstration (code)

`code/metro_tools.py` simulates a 100 nm SiO₂ film on Si with 0.2 % reflectance noise, then fits it:

```text
fit d = 100.02 nm  (1-sigma ~ 0.039 nm)
```

The fit uses a **coarse grid search first** to avoid local minima at the wrong fringe order, then a local refine — mirror this logic when debugging production "thickness jumps by ~λ/(2n)" problems, which are often **fringe-order hops**（干涉級次跳躍）.

Next: [[05 Ellipsometry]].
