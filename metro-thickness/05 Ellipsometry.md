---
tags: [metro-thickness, optics, ellipsometry]
chapters: [6]
created: 2026-10-06
---

# 05 · Spectroscopic Ellipsometry（光譜橢圓偏光術）

← [[04 Reflectometry]] · next → [[06 OCD Scatterometry]]

## 6.1 The measured quantity

$$ \rho=\frac{r_p}{r_s}=\tan\Psi\,e^{i\Delta} $$

- **Ψ (Psi)**: amplitude-ratio angle, $\tan\Psi=|r_p|/|r_s|$.
- **Δ (Delta)**: phase difference between p and s.
- Measured as a **ratio**, so the measurement is largely insensitive to absolute intensity (lamp drift) — a key advantage over reflectometry.
- Typical incidence 65–75°, near the substrate's Brewster angle (Si ≈ 75–76° in the visible), where $|r_p|$ is small and Δ changes fastest.

### Why ellipsometry is so sensitive to thin films
In the ultrathin limit (d ≪ λ), Δ shifts approximately linearly with d. For SiO₂ on Si at 70°, 633 nm, the companion code gives **|∂Δ/∂d| ≈ 0.30° per Å**. With Δ precision of ~0.01–0.02°, that is sub-0.1 Å repeatability — sub-atomic *precision*. *Accuracy* is another story (model, ambient layer).

**Ultrathin catch:** for d below a few nm, the film's n and d are almost fully correlated (only a product-like quantity is determined). Practice: **fix n (from thick-film calibration or literature) and fit d only.**

## 6.2 Optical constants

$$\tilde n=n+ik,\qquad \tilde\varepsilon=\varepsilon_1+i\varepsilon_2=\tilde n^2\;\Rightarrow\;\varepsilon_1=n^2-k^2,\;\varepsilon_2=2nk$$

Absorption coefficient: $\alpha=4\pi k/\lambda$; penetration depth $\delta_p=1/\alpha$. Example: Si at 400 nm, k≈0.4 → δp ≈ 80 nm; at 800 nm k≈0.005 → δp ≈ 13 µm. This is why poly-Si thickness is easier in the visible/NIR and why UV probes only the top of absorbing films.

Anisotropic films (some high-k, stressed or textured films, liquid-crystalline polymers) need **uniaxial** models (n_o, n_e). Dispersion models (Cauchy, Sellmeier, Tauc-Lorentz, Drude, EMA) are covered in [[08 Film Stack and Dispersion Models]].

## 6.3 Multilayer modeling and correlation

Example stack: Air / SiN / SiO₂ / Poly-Si / Si.

Parameter vector $\theta=[d_{SiN},d_{SiO_2},d_{Poly},n_i,k_i,\ldots]$.

### Correlation diagnosis（參數相關性診斷）
Linearize the model around the solution: Jacobian $J_{ij}=\partial S_i/\partial\theta_j$, weights $W=\mathrm{diag}(1/\sigma_i^2)$.

$$\mathrm{Cov}(\hat\theta)\approx (J^TWJ)^{-1},\qquad \mathrm{corr}_{jk}=\frac{C_{jk}}{\sqrt{C_{jj}C_{kk}}}$$

- |corr| > ~0.9: parameters trade off; one may need to be fixed or constrained.
- Large diagonal $C_{jj}$: the data hardly constrain θ_j (low sensitivity).
- Condition number of $J^TWJ$ ≫: ill-posed fit; small noise moves parameters a lot.

**Classic correlated pairs:**
- d_film ↔ n_film (thin transparent films)
- SiO₂ ↔ SiN thicknesses in ON stacks (similar dispersion in some ranges)
- Roughness/interface layer ↔ thickness of top layer
- SiGe Ge% ↔ SiGe thickness
- Poly-Si thickness ↔ poly-Si n/k (grain structure; use EMA of c-Si + a-Si + voids)

### Parameter classes the booklet lists — how to decide

| Class | Example | How chosen |
|---|---|---|
| Fixed | Si substrate n/k, ambient | Well known, stable |
| Calibrated | SiN n/k from a blanket monitor, tuned once per process | Characterized on thick/single-layer films |
| Fitted CTQ | d_SiN | The thing you report |
| Constrained | d_interfacial ∈ [0.5, 1.5] nm | Physically bounded |
| Uncertain | Roughness | Monitor; flag if it hits bounds |

## Instrument types (vendor-neutral)

| Configuration | Notes |
|---|---|
| Rotating analyzer (RAE) | Simple; poor Δ accuracy near 0°/180° |
| Rotating compensator (RCE) | Full Δ range, measures depolarization |
| Phase-modulated (PME) | Fast, precise; photoelastic modulator |
| Mueller-matrix / dual rotating compensator | Full 4×4 Mueller matrix; anisotropy, depolarization, OCD |

**Calibration items:** angle of incidence, polarizer/analyzer azimuths, compensator retardance, wavelength scale, window effects (if any). Usually checked with traceable SiO₂/Si standards (e.g., NIST ellipsometric thickness SRMs). See [[14 Calibration and Drift]].

## Practical checklist when SE thickness looks wrong
1. Is Δ near 0° or 180° where the hardware is least accurate?
2. Is the spot fully inside the pad (oblique elongation)?
3. Did the fit hit a parameter bound?
4. Is depolarization high (backside reflection on transparent substrates, thickness non-uniformity in the spot, roughness)?
5. Is the ambient/contamination layer accounted for on thin films?
6. Did the n/k library version change?

Next: [[06 OCD Scatterometry]].
