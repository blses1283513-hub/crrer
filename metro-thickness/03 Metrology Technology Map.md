---
tags: [metro-thickness, technology-selection]
chapters: [4]
created: 2026-10-06
---

# 03 · Metrology Technology Map（量測技術地圖）

← [[02 Process Modules]] · next → [[04 Reflectometry]]

## Expanded comparison

| Technology | Signal | Main outputs | Typical thickness range* | Strength | Main weakness |
|---|---|---|---|---|---|
| Spectral reflectometry（光譜反射）| R(λ), usually near-normal incidence | d, (n, k) | ~10 nm – tens of µm | Fast, small spot, simple | Weak for < ~10 nm; d–n correlation |
| Spectroscopic ellipsometry, SE（光譜橢偏）| Ψ(λ), Δ(λ) at oblique angle | d, n, k, multilayers | sub-nm – µm | Phase (Δ) gives Å-level sensitivity | Larger elongated spot at 65–75°; model-dependent |
| Mueller-matrix SE / OCD（散射量測）| Full polarization response of gratings | CD, height, SWA, film d | Patterned 3D | Non-destructive 3D profile | Model complexity, parameter correlation |
| XRR（X 光反射）| Specular X-ray reflectivity vs angle | d, density, roughness | ~1 – 200 nm | Model-light thickness (fringe period), density | Slow, large spot, needs smooth films |
| XRF（X 光螢光）| Characteristic fluorescence | Mass thickness, composition | ~0.1 nm – µm (element dependent) | Element-specific, metals, buried | Measures mass/area — needs density for d |
| FTIR / IR | IR reflection/absorption | Epi d, BPSG B/P %, H-bonds | µm-scale epi; composition | Chemistry sensitivity | Large spot, lower resolution |
| Stylus profiler / AFM（輪廓儀）| Surface height | Step height, dishing, roughness | nm – mm steps | Direct geometry | Contact/needs step, slow |
| CD-SEM / XSEM / TEM（電子顯微）| Electron image | CD, profile, cross-section d | nm | Direct imaging, reference | Destructive (X-section), slow, charging |
| Picosecond acoustics / laser ultrasonics | Acoustic echo time | Metal film d | ~nm – µm opaque metals | Opaque metal stacks | Needs sound velocity |
| 4-point probe（四點探針）| Sheet resistance | $t=\rho/R_s$ | Conductive films | Electrical relevance | ρ depends on t, contact |

\*Ranges are indicative of the technology class; actual capability is platform- and stack-specific.

## How to choose（選型邏輯）

```text
Is the film transparent in the tool's wavelength range?
├─ Yes ─ Is it < ~10 nm or multi-layer with thin layers? ── Yes → SE (Δ sensitivity)
│        │                                               └─ No → Reflectometry or SE
│        └─ Is it on a patterned structure (no blanket pad)? → OCD / Mueller-matrix SE
└─ No (metal/opaque)
         ├─ Need element-specific / buried metal? → XRF
         ├─ Need density/roughness, smooth film? → XRR
         ├─ Opaque metal stack thickness? → picosecond acoustics
         └─ Electrical relevance? → 4PP sheet resistance (+ XRF correlation)
Reference/validation: XSEM/TEM, XRR, AFM step, process splits
```

## Accuracy vs. precision — what each method is best for

| Need | Best class |
|---|---|
| In-line, every lot, high throughput | Reflectometry, SE, OCD, XRF |
| Absolute reference for model validation | TEM/XSEM (local), XRR (average, near-model-free period) |
| Composition | XRF, SE (with good dispersion model), FTIR, XPS (lab) |
| Patterned in-die | OCD, integrated optical, CD-SEM |

**Hybrid metrology（混合量測）:** feed a parameter from one technique as a fixed input to another (e.g., XRR density → SE model; CD-SEM CD → OCD model) to break correlations. This is a key idea in advanced nodes.

## Spot size and test structures（光斑與量測墊）

- Oblique incidence elongates the spot by $1/\cos\theta$ (≈ 2.9× at 70°).
- Measurement pads in scribe lines are typically tens of µm; the spot **plus** its tails must fit inside the pad, otherwise neighboring structures contaminate the signal ("pad spill-over"). A thickness that depends on *which* die/scribe you measure, or a tool-specific bias that correlates with spot size, is a pad-size problem until proven otherwise.

Next: [[04 Reflectometry]].
