---
tags: [metro-thickness, remote-support, communication]
chapters: [26]
created: 2026-10-06
---

# 20 · Remote Fab Support Workflow（遠端廠區支援流程）

← [[19 NPI and Recipe Qualification]] · next → [[21 Python Toolkit]]

## 14-step disciplined response — with the question each step answers

| # | Step | Question |
|---|---|---|
| 1 | Confirm symptom | What exactly is abnormal (value, rule, chart)? |
| 2 | Affected layer | One layer or several? |
| 3 | Affected tool/chamber | Process chamber? Metro tool? |
| 4 | Time history | When did it start; step or drift? |
| 5 | Wafer maps | Spatial signature? |
| 6 | Raw Metro data | Spectrum/GOF/n changes? |
| 7 | Reference/control wafer | Is the Metro tool healthy? |
| 8 | Recipe/model revision | Any change around onset? |
| 9 | Process parameters | FDC/sensor changes? |
| 10 | Equipment history | PM, parts, alarms? |
| 11 | Competing hypotheses | At least 2–3, incl. "Metro artifact" |
| 12 | Verify with evidence | Which data would disprove each? |
| 13 | Recommend action | Containment + fix + owner |
| 14 | Monitor recovery | Which charts/lots confirm recovery? |

## Remote-specific practices
- **Time zones:** write the hand-off so the local team can act without a call. Include lot IDs, tool IDs, chart links, timestamps in a single unambiguous time zone (state it).
- **Data access:** know in advance what you can see remotely (SPC, raw spectra, recipe diffs, FDC). Ask for screenshots of what you can't.
- **Request precise actions:** "Measure wafer 07 of lot X on M2 with recipe R rev 5 at the 49-pt map" — not "please re-check".
- **Escalation:** know the severity tiers and who to page.

## Communication template（溝通範本）— with a filled example

| Section | Example |
|---|---|
| **Observation** | Thickness increased by 0.8 nm on Chamber B (SiN cap, recipe rev 12). |
| **Evidence** | Present on 3 consecutive lots (L37–L39) since Tue 14:00 UTC; strongest at wafer center (radial a₁ from 0.0 to −0.6 nm). Chambers A/C unchanged on the same Metro tool. |
| **Hypothesis** | Spatial and chamber-specific signature is more consistent with a Chamber B process change (showerhead or heater) than Metro variation. |
| **Verification** | Control wafer on M1 and M2 within baseline (Δ < 0.05 nm). GOF and n unchanged. Chamber B PM completed Tue 11:00. |
| **Action** | Equipment: inspect Chamber B showerhead install & heater zone calibration from PM. Process: hold B or reduce to monitor-only until verified. |
| **Monitoring** | Control wafer daily; 49-pt maps on next 3 lots from B; close when a₁ returns to baseline ±0.1 nm. |
| **Uncertainty** | Not yet excluded: incoming film difference on L37–L39 (same upstream tool); checking. |

Adding the **Uncertainty** line builds credibility — state what is not yet known.

Next: [[21 Python Toolkit]].
