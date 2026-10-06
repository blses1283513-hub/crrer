---
tags: [metro-thickness, hub, MOC, metrology]
created: 2026-10-06
source: "Metro Thickness Application Engineering — Technical Tools Book v1.0 (booklet)"
purpose: Expanded knowledge base for a Thickness Metrology Applications Engineer — one note per booklet chapter group
---

# 00 · Metro Thickness Hub — 膜厚量測應用工程知識庫

> Vendor-agnostic. Exact tools, specs, sampling plans and control rules are site-specific; confirm them on site. All numbers in these notes are illustrative.

## Map of contents

| Note | Booklet chapters | Core idea |
|---|---|---|
| [[01 Role and Manufacturing Loop]] | 1–2 | You own the trustworthiness of a number; Metro bias becomes process bias via APC |
| [[02 Process Modules]] | 3 | Rate-limiting physics → spatial signature (ALD window, CVD regimes, Deal–Grove, Preston, swing curve) |
| [[03 Metrology Technology Map]] | 4 | Which technique for which film; hybrid metrology |
| [[04 Reflectometry]] | 5 | Fresnel/Airy, fringe thickness, thin-film limit, fringe-order hops |
| [[05 Ellipsometry]] | 6 | Ψ/Δ, ~0.3°/Å sensitivity, parameter correlation via covariance |
| [[06 OCD Scatterometry]] | 7 | RCWA, library vs regression, identifiability |
| [[07 XRR XRF FTIR Profilometry]] | 8 | Kiessig fringes, critical angle, XRF = mass thickness, epi FTIR, AFM steps |
| [[08 Film Stack and Dispersion Models]] | 9 | Real stack incl. IL/ambient; Cauchy, TL, Drude, EMA; multi-sample analysis |
| [[09 Recipe Development]] | 10–11 | 12 recipe blocks, exit criteria, sensitivity math, output translation |
| [[10 Sampling Wafer Maps and Uniformity]] | 12–13 | Site plans, data schema, uniformity definitions, map decomposition |
| [[11 Statistics SPC and Capability]] | 14 | Nested variance, charts, run rules, EWMA/CUSUM, Cpk CI |
| [[12 MSA and Gauge R&R]] | 15 | Static/dynamic repeat, ANOVA GR&R, P/T, ndc, guard-banding |
| [[13 Tool-to-Tool Matching]] | 16 | Investigation ladder, Deming regression, Bland–Altman |
| [[14 Calibration and Drift]] | 17 | Calibration items, drift sources, monitor-wafer contamination trap |
| [[15 Residuals Fit Quality and Model Risk]] | 18 | Reduced χ², residual patterns, systematic-uncertainty budget |
| [[16 Process Correlation and DOE]] | 19 | Correlation traps, DOE for Metro split tracking |
| [[17 Root Cause Framework]] | 20 | Four buckets, signature table, IS/IS-NOT, timeline overlay |
| [[18 Excursion Case Studies]] | 21–24 | 7 worked cases incl. ALD d-vs-N, CVD sigma, etch Δ uncertainty, CMP |
| [[19 NPI and Recipe Qualification]] | 25 | Stage deliverables, qualification evidence, OCAP |
| [[20 Remote Fab Support]] | 26 | 14-step response, filled communication template |
| [[21 Python Toolkit]] | 27 | Tested library `code/metro_tools.py` + worked example with charts |
| [[22 JMP SPC Workflow]] | 28 | JMP platforms per analysis step |
| [[23 Daily Work and Failure Modes]] | 29–30 | Morning checklist, first-hour triage, failure → fast check |
| [[24 Onboarding Plan and Skill Matrix]] | 31–33 | 30/60/90 with deliverables, manager questions, self-assessment |
| [[25 Core Equations]] | 34 | One-page equation sheet |
| [[26 Glossary]] | 35 | English–中文 glossary |
| [[27 References and Learning Path]] | 36, App C–D | Textbooks, learning phases, module tracker |
| [[practice-questions]] | — | 15 graded problems with worked answers |

## Appendix A — One-minute mental model

```text
PROCESS → FILM → SIGNAL → MODEL → THICKNESS → MAP → STATISTICS → SPC → CAUSE → ACTION
```
**Which box is actually failing?** (Per-box symptoms: [[01 Role and Manufacturing Loop]].)

## Appendix B — Five checks for any thickness excursion

| # | Check | Question | Separates |
|---|---|---|---|
| 1 | Reference | Is the control/reference wafer also abnormal? | Metro vs not-Metro |
| 2 | Replication | Does another qualified Metro tool agree? | One tool vs real film |
| 3 | Spatial | Center, edge, radial, azimuthal, local? | Process physics / site artifact |
| 4 | Time | Random, gradual, or step? | Aging vs event |
| 5 | Process link | Which parameter changed at the same time? | Process / equipment / material |

## Code
- `code/metro_tools.py`: run `python metro_tools.py` for the self-test.
- `code/example_wafer_analysis.py`: generates `code/out/` (CSV + 3 charts).

## Technical dictionary
- `glossary/terms.json`: 207 terms (中文, EN/中 short definitions, related words), the source for the study guide's hover popups.
- `glossary/eudic/MetroThickness.mdx`: custom Eudic (歐路詞典) dictionary; import steps in `glossary/README.md`.

## Final principle
"I know how the tool works" → "…how the recipe converts signal to thickness" → "…whether the measurement is trustworthy" → "…how the map relates to process physics" → "…the likely root cause" → "I can recommend and verify corrective action."
That is the difference between **operating a metrology tool** and being a **Metro Applications Engineer**.
