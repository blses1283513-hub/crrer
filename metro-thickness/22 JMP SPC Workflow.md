---
tags: [metro-thickness, JMP, SPC]
chapters: [28]
created: 2026-10-06
---

# 22 · JMP / SPC Workflow

← [[21 Python Toolkit]] · next → [[23 Daily Work and Failure Modes]]

Menu paths are for recent JMP versions and may differ slightly by version.

| Step | JMP platform | What to look at |
|---|---|---|
| Import | File ▸ Open (CSV) / Database query | Column types: IDs = Nominal (character), thickness = Continuous, time = Date |
| Clean / classify | Tables ▸ Summary, Cols ▸ Recode, Exclude rows | Duplicates, re-measures, test wafers, GOF-failed sites |
| Distribution | Analyze ▸ Distribution | Shape, bimodality (mixture of chambers?), outliers, normal quantile plot |
| Graph Builder | Graph ▸ Graph Builder | Thickness vs time colored by chamber; **x_mm / y_mm with color = thickness** for wafer maps; Wrap by wafer |
| Control chart | Analyze ▸ Quality and Process ▸ Control Chart Builder | Subgroup = wafer; Phase = before/after PM; Tests (Western Electric) |
| By tool / chamber / recipe / lot | Use **By** or **Phase**, or drag to Group X/Y | Which group carries the shift? |
| By wafer position | Graph Builder with slot or ring | Batch furnace slot effects; edge vs center |
| Variance components | Analyze ▸ Quality and Process ▸ Variability / Attribute Gauge Chart | Nested lot/wafer/site; Gauge R&R (Crossed) |
| Matching | Analyze ▸ Specialized Modeling ▸ Matched Pairs; Fit Y by X ▸ Fit Orthogonal | Bias, slope; orthogonal = Deming |
| Correlation / Fit Model | Analyze ▸ Multivariate; Fit Model | Process parameters ↔ thickness; DOE analysis |
| Capability | Analyze ▸ Quality and Process ▸ Process Capability | Within vs overall sigma (Cpk vs Ppk) |
| Root cause | Combine: timeline + maps + IS/IS-NOT | — |

## Useful tricks
- **Local Data Filter** on a Graph Builder wafer map → click through wafers/lots quickly.
- **Column formula** for radius: `Sqrt(:x_mm^2 + :y_mm^2)`; for ring: `If(:r < 10, "C", :r < 110, "Mid", "Edge")`.
- **Save Script ▸ To Data Table** so the analysis re-runs on new data.
- **Tabulate** for a summary table by chamber × week.
- **Response Screening** (Analyze ▸ Screening) to scan many FDC parameters against thickness — then apply engineering judgement (multiplicity!).

## Dimensions to always try
Tool · Chamber · Metro tool · Recipe/revision · Lot · Wafer/slot · Site/ring · Date/time/shift · Film/layer · Process step · PM counter.

Next: [[23 Daily Work and Failure Modes]].
