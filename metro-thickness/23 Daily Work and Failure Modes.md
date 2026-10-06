---
tags: [metro-thickness, daily-work, troubleshooting]
chapters: [29, 30]
created: 2026-10-06
---

# 23 · Daily Work and Common Failure Modes（日常工作與常見失效模式）

← [[22 JMP SPC Workflow]] · next → [[24 Onboarding Plan and Skill Matrix]]

## 29. Five working modes — with a daily rhythm

| Mode | Trigger | Output |
|---|---|---|
| **A. Routine monitoring** | Every morning | SPC review notes; tool status; open actions |
| **B. Excursion** | Alarm / hold / phone call | Real-or-not verdict within hours; RCA thread |
| **C. Application development** | New film/process, model improvement | Recipe release package |
| **D. Tool matching** | New/repaired tool, PM, periodic audit | Matching report, release decision |
| **E. Cross-functional communication** | Meetings, hand-offs | Clear status: observation/evidence/hypothesis/action |

### A morning checklist (≈ 30 min)
- [ ] Monitor/reference wafer charts for every Metro tool you own (flat? within limits?)
- [ ] Overnight SPC violations on owned layers — triage each: Metro / process / data artifact
- [ ] GOF and n trend on key recipes (early warning)
- [ ] Tool states: down, PM, waiting for qualification
- [ ] Recipe changes made in the last 24 h (change log)
- [ ] Open action items: who owes what by when

### Excursion triage (first hour)
1. Reproduce the number (re-measure or second tool).
2. Reference wafer on the same tool.
3. Map + time signature.
4. Recipe/model change log.
5. Communicate preliminary verdict: *"Metro verified healthy; shift appears real, chamber B only, center-heavy; process team engaged."*

### Always ready to answer
What changed? When? Which tools/chambers? Which lots/wafers? What spatial pattern? What evidence? What remains uncertain? What action is recommended?

## 30. Failure modes and fast checks — expanded

| Symptom | Fast first checks | Then |
|---|---|---|
| All wafers shifted | Reference wafer, calibration | Second tool; recipe change log |
| One Metro tool shifted | Tool-to-tool on the same wafers | Raw-signal overlay; calibration; recent PM |
| One chamber shifted | Chamber/process history | FDC traces, PM, parts |
| Slow drift | Lamp/detector, contamination, process aging | Correlate with lamp hours, RF hours, pad life; monitor wafer contamination |
| Sudden step | Maintenance / recipe / material change | Timeline overlay |
| Residuals worsen | Film stack, model, n,k | Residual-vs-λ; n,k trend; upstream change |
| Map orientation changes | Site map, alignment, wafer orientation (notch) | Recipe diff; PR images |
| Edge-only change | Edge process + site definition | Edge exclusion; spot clipping on edge pads |
| Repeats disagree | Focus, alignment, repeatability | Static vs dynamic repeat; PR scores |
| Tools disagree | Matching, calibration, model version | Ladder in [[13 Tool-to-Tool Matching]] |
| Cpk drops, mean stable | Variation increased | Split within-wafer vs wafer-to-wafer σ |
| Mean stable, map worsens | Spatial uniformity problem | Radial/tilt coefficients |
| Thickness jumps by ~λ/(2n) | Fringe-order hop | Wider search range / better starting guess |
| Parameter at bound | Model can't explain data | Process out of range or wrong fixed parameter |
| GOF fails on few sites | Off-pad, particle, PR miss | Site images |
| Thin monitor slowly rising on all tools | Ambient contamination | Clean/desorb monitor; ambient layer |

Next: [[24 Onboarding Plan and Skill Matrix]].
