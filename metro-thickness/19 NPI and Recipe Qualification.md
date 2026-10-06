---
tags: [metro-thickness, NPI, qualification]
chapters: [25]
created: 2026-10-06
---

# 19 · NPI / New Recipe Qualification（新產品／新配方導入驗證）

← [[18 Excursion Case Studies]] · next → [[20 Remote Fab Support]]

## Flow with deliverables

| Stage | Deliverable |
|---|---|
| New process | Process description, expected stack, thickness range, window |
| Define CTQ | CTQ list, target, LSL/USL, required detection limit |
| Select technology | Sensitivity study, technology rationale ([[03 Metrology Technology Map]]) |
| Reference samples | Split matrix (thickness ± window, composition corners), reference plan (TEM/XRR/AFM) |
| Develop recipe | Stack model, n/k library entries, fit strategy, site map ([[09 Recipe Development]]) |
| Correlation | Slope/offset/R² vs reference; split tracking |
| Repeatability | Static & dynamic repeat; P/T |
| Reproducibility | Multi-day; GR&R report ([[12 MSA and Gauge R&R]]) |
| Tool matching | All qualified tools; offset/slope ([[13 Tool-to-Tool Matching]]) |
| Manufacturing qual | Throughput, PR robustness on real product, edge sites, data flow to MES/SPC |
| SPC implementation | Charts, limits (initial → re-calculated after N points), reaction plan (OCAP) |

## Qualification questions with suggested evidence

| Question | Evidence |
|---|---|
| **Accuracy** — agrees with reference? | Reference correlation plot; bias with CI; systematic-uncertainty budget |
| **Precision** — random variation small? | P/T, σ_static, σ_dynamic |
| **Sensitivity** — resolves minimum meaningful shift? | Split tracking; σ_meas ≤ shift/3 |
| **Robustness** — valid across process variation? | GOF and parameter sanity at window corners; nuisance perturbation test |
| **Throughput** — fits takt time? | s/wafer × sampling plan vs capacity |
| **Matching** — tools comparable? | Matching report, all tools |

## Common NPI pitfalls
- Reference samples only at nominal → model fits nominal, fails at corners.
- n/k library from a different process condition (e.g., another chamber type).
- Site map built on test wafer layout, product reticle differs.
- Initial SPC limits from too few points → false alarms; recalculate after stabilization.
- No owner for the n/k library after hand-off.

## OCAP — Out-of-Control Action Plan（失控處置計畫）
A short decision flow attached to each chart: what the operator/technician does on each rule violation (re-measure, measure reference wafer, hold lot, notify engineer), and what the engineer checks first. Write it during NPI, not after the first excursion.

Next: [[20 Remote Fab Support]].
