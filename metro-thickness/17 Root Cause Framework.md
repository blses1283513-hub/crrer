---
tags: [metro-thickness, RCA, troubleshooting]
chapters: [20]
created: 2026-10-06
---

# 17 · Root-Cause Analysis Framework（根本原因分析架構）

← [[16 Process Correlation and DOE]] · next → [[18 Excursion Case Studies]]

## Four buckets

| Bucket | Members | First evidence to pull |
|---|---|---|
| **Process** | T, P, gas/precursor flow, RF, time, cycles, recipe step, surface condition | Recipe log, FDC sensor traces, recipe revision history |
| **Equipment** | Chamber state, wear, sensor drift, gas delivery, RF, vacuum, thermal, PM | PM log, RF-hours/clean counters, alarms |
| **Metro** | Calibration, source, detector, alignment, focus, stage, recipe, model, n/k, data processing | Monitor wafer chart, raw spectra, recipe/model diff, second tool |
| **Material** | Composition, density, roughness, crystallinity, porosity, stress, interface | n/k trend, GOF trend, XRR density, upstream changes (incoming wafer, precursor lot) |

## Signature → first hypotheses

| Signature | First hypotheses | Fast discriminator |
|---|---|---|
| All wafers shift | Process mean shift or Metro bias | Reference wafer + second Metro tool |
| One chamber shifts | Chamber/equipment | Compare chambers same day, same Metro tool |
| One Metro tool shifts | Measurement system | Same wafers on other tools |
| Gradual drift | Aging, contamination, calibration | Correlate with counters (lamp h, RF h, pad h) |
| Sudden step | Maintenance, recipe, material lot | Timeline overlay of change events |
| Center-edge changes | Process spatial distribution or site-map | Check site map/orientation; chamber hardware |
| Single local defect | Wafer condition / measurement artifact | Re-measure; image the site |
| Multiple layers shift together | Common Metro factor or common upstream | Did unrelated layers on same Metro tool shift? |
| Fit residual worsens | Model / stack / n,k | Residual-vs-λ plot; n,k trend |

## Structured methods（結構化方法）

**Is / Is-Not（是/不是分析, Kepner–Tregoe）** — the most useful single tool for Metro excursions:

| Dimension | IS | IS NOT | Distinction → clue |
|---|---|---|---|
| What layer | SiN cap | Other layers on the same Metro tool | Not a common Metro hardware issue |
| Which chamber | B | A, C | Chamber B specific |
| Which Metro tool | M1 and M2 | — | Not Metro-tool specific |
| Where on wafer | Center | Edge | Spatial → gas/thermal/plasma |
| When first | Lot 37, Tue 14:00 | Before Tue | What changed Tue? → PM on B at 11:00 |

**Fishbone / 6M（魚骨圖: Man, Machine, Method, Material, Measurement, Mother-nature/Environment）** — use to brainstorm, not to conclude.

**5 Whys（五個為什麼）** — once a direct cause is confirmed, drill to the systemic cause (why did the PM checklist miss it?).

**8D / CAPA** — formal problem-solving record: containment, root cause, corrective, preventive, verification.

**Timeline overlay** — single highest-value plot: thickness vs time with vertical lines for every PM, recipe change, Metro calibration, material lot change.

## Golden rules
1. **First answer "Is it real?"** before chasing process causes.
2. Form **competing hypotheses** and seek evidence that *disproves* each.
3. A hypothesis must explain **all** IS/IS-NOT facts, not just the striking one.
4. Verify by **turning the cause on/off** if possible (revert the change, re-run).
5. Close the loop: monitor recovery lots with the same trusted measurement.

Next: [[18 Excursion Case Studies]].
