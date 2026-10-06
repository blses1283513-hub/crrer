---
tags: [metro-thickness, references, learning-path]
chapters: [36, "App C", "App D"]
created: 2026-10-06
---

# 27 · References and Learning Path（參考資料與學習路徑）

← [[26 Glossary]] · back to [[00 - Metro Thickness Hub]]

## Sources cited in the booklet
- Micron Careers — F16 Metrology Application Engineer (job-scope example: ellipsometry/scatterometry modeling, XRF, surface profiling, SWR, new process/equipment recipe setup): https://careers.micron.com/careers/job/43257321-f16-metrology-application-engineer-miaoli-county-miaoli-county-taiwan
- Onto Innovation — Atlas V / Atlas III+ (OCD & thin film), IMPULSE (CMP/film process control), EPI thickness/composition metrology: https://ontoinnovation.com/products/
- Nova — product overview: https://www.novameasuring.com/products/products-overview

> Vendor pages are technology examples, not confirmation of the tools installed at any specific fab.

## Standard textbooks and references (for self-study)
| Topic | Reference |
|---|---|
| Ellipsometry | H. Fujiwara, *Spectroscopic Ellipsometry: Principles and Applications* (Wiley) |
| Ellipsometry | H. G. Tompkins & E. A. Irene (eds.), *Handbook of Ellipsometry* |
| Thin-film optics | O. S. Heavens, *Optical Properties of Thin Solid Films*; M. Born & E. Wolf, *Principles of Optics* |
| Dispersion | G. E. Jellison & F. A. Modine, "Parameterization of the optical functions of amorphous materials in the interband region," *Appl. Phys. Lett.* 69 (1996) — Tauc–Lorentz |
| Semiconductor process | S. Wolf & R. N. Tauber, *Silicon Processing for the VLSI Era*; J. D. Plummer et al., *Silicon VLSI Technology* |
| Oxidation | B. E. Deal & A. S. Grove, *J. Appl. Phys.* 36, 3770 (1965) |
| Metrology overview | D. K. Schroder, *Semiconductor Material and Device Characterization* (Wiley) |
| X-ray | M. Yasaka, "X-ray thin-film measurement techniques V: X-ray reflectivity measurement," *Rigaku Journal* 26(2), 2010 |
| SPC | D. C. Montgomery, *Introduction to Statistical Quality Control* |
| MSA | AIAG, *Measurement Systems Analysis* reference manual |
| DOE | D. C. Montgomery, *Design and Analysis of Experiments* |
| Statistics handbook | NIST/SEMATECH *e-Handbook of Statistical Methods* (free online) |
| Roadmap | IRDS — *Metrology* chapter (International Roadmap for Devices and Systems) |

## Appendix D — Learning sequence with time budget

| Phase | Topics | Suggested time | Proof of learning |
|---|---|---|---|
| 1 Fundamentals | FEOL/MOL/BEOL, deposition, etch, CMP, litho, stacks | 2 weeks | Draw a full transistor/memory-cell flow with films |
| 2 Optical metrology | Reflection, Fresnel, interference, polarization, SE, n/k, multilayers | 3 weeks | Run `metro_tools.py`; simulate R(λ) & Ψ/Δ for your stacks |
| 3 Statistics | Distributions, SPC, Cp/Cpk, GR&R, correlation, DOE | 2 weeks | Re-derive the GR&R ANOVA by hand on a small dataset |
| 4 Applications | Recipe dev, matching, calibration, model robustness, NPI, RCA, communication | ongoing | Lead one excursion with a written report |
| 5 Automation | Python/pandas, wafer maps, SPC automation, regression, anomaly detection | ongoing | Automated daily summary script |

## Appendix C — Tool-specific modules to build next
Status tracker for future deep-dive notes:

| # | Module | Status | Seed note |
|---|---|---|---|
| 1 | Ellipsometer architecture | ☐ | [[05 Ellipsometry]] |
| 2 | Reflectometer architecture | ☐ | [[04 Reflectometry]] |
| 3 | OCD/scatterometer architecture | ☐ | [[06 OCD Scatterometry]] |
| 4 | XRF architecture | ☐ | [[07 XRR XRF FTIR Profilometry]] |
| 5 | XRR architecture | ☐ | [[07 XRR XRF FTIR Profilometry]] |
| 6 | FTIR film/EPI | ☐ | [[07 XRR XRF FTIR Profilometry]] |
| 7 | Profilometer | ☐ | [[07 XRR XRF FTIR Profilometry]] |
| 8 | Film-stack modeling | ◐ | [[08 Film Stack and Dispersion Models]] |
| 9 | n/k dispersion models | ◐ | [[08 Film Stack and Dispersion Models]] |
| 10 | Recipe parameter sensitivity | ◐ | [[09 Recipe Development]] |
| 11 | Reference wafer design | ☐ | [[14 Calibration and Drift]] |
| 12 | Matching studies | ◐ | [[13 Tool-to-Tool Matching]] |
| 13 | GR&R / capability | ◐ | [[12 MSA and Gauge R&R]] |
| 14 | SPC reaction plans | ◐ | [[19 NPI and Recipe Qualification]] |
| 15 | Wafer map spatial analysis | ◐ | [[10 Sampling Wafer Maps and Uniformity]] |
| 16–18 | ALD / CVD / PVD correlation | ◐ | [[02 Process Modules]] |
| 19 | Etch remaining film | ◐ | [[18 Excursion Case Studies]] |
| 20 | CMP thickness | ◐ | [[18 Excursion Case Studies]] |
| 21 | Litho/resist thickness | ☐ | [[02 Process Modules]] |
| 22 | NPI qualification | ◐ | [[19 NPI and Recipe Qualification]] |
| 23 | Remote support | ◐ | [[20 Remote Fab Support]] |
| 24 | Python automation | ◐ | [[21 Python Toolkit]] |
| 25 | JMP templates | ◐ | [[22 JMP SPC Workflow]] |
| 26 | RCA casebook | ◐ | [[18 Excursion Case Studies]] |

☐ not started · ◐ foundation written · ● complete
