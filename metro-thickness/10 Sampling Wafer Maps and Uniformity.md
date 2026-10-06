---
tags: [metro-thickness, sampling, wafer-map, uniformity]
chapters: [12, 13]
created: 2026-10-06
---

# 10 · Sampling, Wafer Maps and Uniformity（取樣、晶圓圖與均勻性）

← [[09 Recipe Development]] · next → [[11 Statistics SPC and Capability]]

## 12. Sampling strategies

| Plan | Sites (typical) | Use |
|---|---|---|
| Center only | 1 | Fast monitor; blind to uniformity |
| 5-point (center + 4 at ~½–⅔ R) | 5 | Quick tool monitor |
| 9 / 13-point | 9–13 | Production standard for many layers |
| **Polar 49-point** (1 + 8 + 16 + 24 rings) | 49 | Qualification, uniformity, chamber matching |
| Dense radial (line scan) | 50–200 | CMP/etch zone tuning; edge roll-off |
| Grid / full-map | 100s | Development, root cause |
| Device-specific in-die | Product dependent | OCD, patterned CTQs |

Design considerations:
- **Edge exclusion（邊緣排除）**: e.g., 3 mm on 300 mm wafers, but many excursions start at the edge — keep at least one ring near the exclusion boundary.
- **Radial coverage vs azimuthal coverage**: most chamber physics is radial; azimuthal sampling catches tilt, pins, inlet asymmetry.
- **Same sites pre/post** for delta measurements (etch, CMP).
- **Wafer-level vs lot-level sampling**: how many wafers per lot, which slots (first/last in a batch furnace!), how many lots per day. Use nested-variance results to decide: if lot-to-lot variance dominates, measure more lots, fewer sites.
- **Dynamic sampling**: increase sampling after alarms/PMs, reduce on long stable periods (site policy).

$$ \text{Information}\;\longleftrightarrow\;\text{Throughput (WPH)} $$

## Data schema (long format, one row per site)

```text
lot_id, wafer_id, slot, tool_id, chamber_id, metro_tool_id, metro_recipe_id, recipe_rev,
site_id, x_mm, y_mm, r_mm (derived), theta_deg (derived),
thickness, n_633, gof, flag_bound_hit,
process_recipe, process_timestamp, metro_timestamp, pm_counter, rf_hours
```

Long format makes `groupby` (pandas) / `By` (JMP) analysis trivial; derived polar coordinates make radial analysis trivial.

## 13. Thickness uniformity definitions

| Name | Formula | Note |
|---|---|---|
| Half-range（半全距）| $\frac{T_{max}-T_{min}}{2T_{mean}}\times100\%$ | Sensitive to single outliers |
| Range | $\frac{T_{max}-T_{min}}{T_{mean}}\times100\%$ | 2× half-range |
| 1σ (CV) | $\frac{\sigma}{\mu}\times100\%$ | Robust-ish, depends on site count |
| 3σ | $\frac{3\sigma}{\mu}\times100\%$ | 3× the CV |

The same wafer can read "1 %" in one definition and "3 %" in another. **Always state the definition, site plan and edge exclusion.**

Worked example (booklet data 20.01, 19.98, 20.04, 20.02, 20.07, 19.99): mean 20.018, σ 0.0331, range 0.09 → half-range 0.22 %, CV 0.17 %, 3σ 0.50 %.

## Decomposing a wafer map（晶圓圖分解）

Fit simple basis functions and look at the coefficients over time:

1. **Mean** (offset)
2. **Tilt**: $T=c_0+c_xx+c_yy$ → direction and magnitude of linear gradient
3. **Radial (bowl/dome)**: $T=a_0+a_1\rho^2+a_2\rho^4$, ρ = r/R. $a_1<0$ dome (center thick), $a_1>0$ bowl (edge thick)
4. **Residual**: azimuthal/local structure
   (Zernike polynomials generalize this — same orthogonal basis optics uses for wavefronts.)

Trending $c_x, c_y, a_1, a_2$ per chamber turns "the maps look different" into **numbers you can SPC**. Helper functions: `tilt_fit`, `radial_fit`, `polar_sitemap` in `code/metro_tools.py`.

## Spatial signatures → hypotheses (expanded)

| Signature | Process hypotheses | Metro hypotheses |
|---|---|---|
| Center high / edge low (dome) | Center-heavy showerhead flow, center-hot heater, plasma density peak, CMP center-slow | Edge sites off-pad; edge spot clipping |
| Edge high / center low (bowl) | Edge ring/focus ring, edge-hot, gas edge flow, CMP retaining-ring | Edge sites on different structure |
| Linear tilt | Inlet/exhaust asymmetry, wafer off-center in chamber, chuck tilt | Stage tilt/focus gradient (rare) |
| Ring at fixed radius | Heater zone boundary, CMP head zone boundary | Site map ring changed |
| Notch-side only | Wafer orientation-related hardware (notch aligner, lift pins) | Map rotated (wafer-recognition) |
| Isolated site | Particle, defect, scratch | Pattern-recognition miss, wrong die |

> A map generates hypotheses; it does not prove root cause. Confirm with chamber sensors, cross-chamber comparison, and controlled experiments.

Next: [[11 Statistics SPC and Capability]].
