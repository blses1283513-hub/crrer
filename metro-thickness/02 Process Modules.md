---
tags: [metro-thickness, process, ALD, CVD, PVD, etch, CMP, litho]
chapters: [3]
created: 2026-10-06
---

# 02 · Process Modules Connected to Thickness（與膜厚相關的製程模組）

← [[01 Role and Manufacturing Loop]] · next → [[03 Metrology Technology Map]]

The rule of thumb: **know the rate-limiting physics of each process, because that tells you which spatial and temporal signature a given knob produces.** A wafer map is a fingerprint of the process physics.

---

## 3.1 ALD — Atomic Layer Deposition（原子層沉積）

### Mechanism
Self-limiting half-reactions: precursor A chemisorbs until surface sites saturate → purge → co-reactant B reacts with the adsorbed layer → purge. One cycle deposits a sub-monolayer.

$$ d \approx N_{cycles}\times GPC \;(+\; d_{interfacial}) \;-\; GPC\times N_{nucleation\ delay}$$

Typical GPC（每循環成長量）values (illustrative; site values differ):

| Film | Precursors (common) | GPC (Å/cycle) | Typical T window |
|---|---|---|---|
| Al₂O₃ | TMA / H₂O | ~1.0–1.2 | ~150–300 °C |
| HfO₂ | HfCl₄ or TEMAHf / H₂O or O₃ | ~0.8–1.2 | ~200–350 °C |
| TiN | TiCl₄ / NH₃ | ~0.2–0.5 | ~350–450 °C |
| SiO₂ (PEALD) | aminosilane / O₂ plasma | ~0.7–1.5 | low-T |

### The ALD window（ALD 製程窗口）
```text
GPC
 │  condensation         ALD window (flat)        decomposition
 │  ╲                  ─────────────────          ╱  (CVD-like growth)
 │   ╲________________/                 \________/
 │  insufficient                          desorption
 │  reactivity                            (GPC drops)
 └────────────────────────────────────────────────► Temperature
```
Inside the window GPC is insensitive to T, dose and pressure — **thickness shifts inside the window usually mean cycle count, nucleation, or a measurement issue**. Outside the window GPC becomes temperature-sensitive.

### Signature map

| Knob / fault | Thickness effect | Spatial signature | Other clues |
|---|---|---|---|
| Cycle count error | Exact step ∝ ΔN | Uniform (whole map shifts) | Recipe log / count audit |
| Under-dose (precursor depletion) | Thinner | **Thin far from inlet** (gradient along flow) | Ampoule temperature/level, MFC |
| Insufficient purge → parasitic CVD | **Thicker**, worse uniformity | Thick near inlet / center (showerhead) | n may shift (impurities), particle |
| T above window (decomposition) | Thicker, rate ∝ exp(−Ea/kT) | Follows heater zones | Carbon/Cl content changes |
| Nucleation delay change (surface prep) | Offset (not ∝ N) | Can be pattern/substrate dependent | Plot d vs N: intercept moves, slope same |
| Chamber seasoning / wall deposits | Gradual drift | Often edge first | Correlates with RF-hours / clean count |

**Metro tip:** for a thin ALD film the d-vs-N plot is the best diagnostic — *slope = GPC*, *intercept = nucleation delay/interfacial layer*. A slope change is a process change; an intercept change is often surface/interface (or a model change in how the interfacial layer is handled).

---

## 3.2 CVD — Chemical Vapor Deposition（化學氣相沉積）

### Two regimes（兩種速率控制區）

$$ \frac{1}{R}=\frac{1}{k_s}+\frac{1}{h_g},\qquad k_s=k_0e^{-E_a/k_BT} $$

| Regime | Condition | Sensitive to | Map signature |
|---|---|---|---|
| **Surface-reaction limited**（表面反應控制）| k_s ≪ h_g (low T, LPCVD) | **Temperature** (Arrhenius; Ea ~1–2 eV → a few %/°C) | Follows heater-zone pattern |
| **Mass-transport limited**（質傳控制）| k_s ≫ h_g (high T, APCVD) | Gas flow, boundary layer, geometry | Follows flow pattern; inlet→exhaust gradient, loading |

PECVD（電漿輔助）adds RF power, electrode spacing, and plasma uniformity: center-thick or edge-thick patterns from plasma density; **n and density depend on RF power and H content**, e.g., PECVD SiN n ≈ 1.85–2.1 varying with SiH₄/NH₃ ratio (Si-rich → higher n and k).

### Metro-relevant consequences
- Rate changes and **composition changes travel together** in PECVD. If you fix n in the model while the film's n moved, the fit pushes the error into thickness. Watch **n, k, and GOF trends** alongside thickness.
- Furnace (batch LPCVD) adds **slot position** as a factor: wafers near gas injection vs. far end; dummy wafer placement.

---

## 3.3 PVD — Physical Vapor Deposition（物理氣相沉積 / 濺鍍）

| Parameter | Effect |
|---|---|
| Target power (DC/RF) | Rate ∝ power (approximately) |
| Target erosion / kWh life | Racetrack deepens → rate and **radial profile change over target life** |
| Pressure / gas flow | Scattering, step coverage, film density/stress |
| Target-to-wafer distance, magnet | Radial uniformity |
| Substrate T, bias | Grain size, resistivity, stress |

**Metrology:** metals are optically opaque above ~30–50 nm, so optical thickness only works for thin metals or transparent nitrides; use **XRF** (mass thickness), **4-point-probe sheet resistance** ($R_s=\rho/t$), or picosecond acoustics. Caution: ρ itself depends on thickness (size effect, grain boundaries), so $t = \rho/R_s$ needs a thickness-dependent ρ calibration.

A typical signature: thickness drift tracking **target kWh** — a gradual, predictable trend, compensated by power/time ramp tables.

---

## 3.4 Epitaxy（磊晶）

- Si / SiGe / doped epi. Outputs: thickness, Ge fraction, doping.
- **FTIR** measures epi thickness via the optical contrast between lightly doped epi and a heavily doped substrate (free-carrier absorption changes n in IR).
- **SiGe on Si:** in spectroscopic ellipsometry (SE), Ge % and thickness are partially correlated (both shift the spectrum); break the correlation with XRD/XRR reference data or by fitting composition in a spectral region where only composition matters (E1 critical point shift).
- Strain/relaxation → XRD (HRXRD rocking curves) is the reference.

---

## 3.5 Thermal oxidation（熱氧化）

**Deal–Grove model:**

$$ x^2 + A x = B (t+\tau) $$

- Thin limit: $x \approx \frac{B}{A}(t+\tau)$ (linear, reaction limited)
- Thick limit: $x \approx \sqrt{B t}$ (parabolic, diffusion limited)
- Dry O₂ at 1000 °C, 1 h → ≈ 69 nm (Grove's coefficients; verified in `code/metro_tools.py`).
- Very thin (< ~20 nm) dry oxides grow faster than Deal–Grove predicts (initial regime) → use empirical calibration.

Signatures: furnace zone (slot) temperature profile; RTO lamp zones; wet vs dry; **chlorine** or pressure effects. Oxide is the classic Metro **monitor/reference** film (stable n ≈ 1.457 @633 nm), but beware **ambient contamination growth** on monitor wafers (see [[14 Calibration and Drift]]).

---

## 3.6 Etch（蝕刻）

$$ d_{removed}=d_{before}-d_{after},\qquad ER=\frac{d_{removed}}{t_{etch}} $$

Pitfalls:
1. **Pre/post must be site-matched.** Using a pre-map average with a post-map average hides spatial ER non-uniformity.
2. **Uncertainty of a difference:** $\sigma_{\Delta}^2=\sigma_0^2+\sigma_1^2-2\rho\sigma_0\sigma_1$. Same tool + same site + same recipe → correlated systematic errors cancel (ρ > 0). Different tools → bias does *not* cancel.
3. **Endpoint & over-etch:** if etch stops on an underlying layer, post thickness of the stop layer = selectivity information: $S=ER_{target}/ER_{stop}$.
4. **Loading effects:** blanket monitor ER ≠ product ER (pattern density, aspect ratio dependent etch — ARDE).
5. Remaining-film on product often needs OCD/patterned models, not blanket recipes.

---

## 3.7 CMP — Chemical Mechanical Planarization（化學機械研磨）

**Preston equation:** $RR = K_p\,P\,V$ (removal rate ∝ pressure × relative velocity).

| Concern | Meaning | How Metro sees it |
|---|---|---|
| Post-CMP thickness | Remaining dielectric/metal | Optical on pads/arrays, integrated (in-line) metrology |
| Removal | $R=T_{pre}-T_{post}$ | Needs site-matched pre/post |
| WIWNU | Within-wafer non-uniformity | Radial profile ↔ **carrier head zone pressures** |
| Dishing（碟形凹陷）| Soft metal recessed in wide lines | Profilometry/AFM, OCD |
| Erosion（侵蝕）| Dielectric thinning in dense arrays | Pattern-density dependent; measure in-die, not just on scribe pads |
| Pad / conditioner life | Gradual RR drift | Trend vs. pad hours |

**APC:** feed-forward pre-thickness → polish time: $t=(T_{pre}-T_{target})/RR$; feedback updates RR (EWMA). Zone-pressure control uses the **radial** thickness profile — so radial site density matters.

---

## 3.8 Lithography / photoresist（微影／光阻）

- Resist thickness from spin speed: $T \propto \omega^{-1/2}$ (approx.), viscosity, solvent evaporation.
- **Swing curve（擺動曲線）:** standing waves in the resist make dose-to-clear and CD oscillate with resist thickness, period $\Delta T = \lambda/(2n_{resist})$. For 193 nm and n≈1.7: ΔT ≈ 57 nm. Hence resist thickness control (and BARC — bottom anti-reflective coating) matters to CD.
- Resist is soft and photosensitive: measurement light dose, repeated measurement shrinkage (e-beam for CD-SEM), and solvent loss over time are measurement-induced drifts.

---

## Quick reference — "knob → map" cheat sheet

| Pattern | First process hypotheses |
|---|---|
| Uniform whole-map shift | Time/cycles, rate (T in reaction-limited regime), Metro bias |
| Dome (center thick) | Showerhead/gas center-heavy, plasma center-dense, center-hot heater |
| Bowl (edge thick) | Edge ring, edge-hot, flow at edge, CMP retaining-ring/edge zone |
| Linear tilt | Gas inlet side, exhaust asymmetry, wafer off-center, chuck tilt |
| Ring at specific radius | Heater zone boundary, CMP zone boundary, lift-pin/edge ring |
| Azimuthal (spokes) | Lift pins, clamp fingers, rotation issue, pump port |
| Single site | Particle, defect, pattern recognition miss, measuring wrong structure |

Next: which measurement sees which film → [[03 Metrology Technology Map]].
