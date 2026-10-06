---
tags: [metro-thickness, case-study, excursion, ALD, CVD, etch, CMP]
chapters: [21, 22, 23, 24]
created: 2026-10-06
---

# 18 · Excursion Case Studies（異常案例研究）

← [[17 Root Cause Framework]] · next → [[19 NPI and Recipe Qualification]]

All numbers are illustrative. Each case follows: **symptom → is it real? → localize → hypotheses → evidence → action → verify.**

---

## Case 1 — Sudden +1 nm shift（突然 +1 nm 偏移）

Normal 19.9–20.1 nm (σ ≈ 0.05), new 21.0 nm → +20σ: an R1 alarm, not noise.

| Step | Action | If result A | If result B |
|---|---|---|---|
| 1 | Raw spectrum vs baseline | Spectrum shape changed → real film change or contamination | Spectrum same but output changed → recipe/model change |
| 2 | Measure same wafer on another qualified tool | Other tool also 21.0 → film is real (or common model) | Other tool 20.0 → Metro tool M1 |
| 3 | Run reference/control wafer | Abnormal → Metro | Normal → process/sample |
| 4 | Recipe/model revision check | Changed at the step time → recipe | No change |
| 5 | Chamber/process data | Cycle count/time/T change | — |
| 6 | Maintenance history | PM just before step | — |

**Quantitative sanity check:** +1 nm on 20 nm = +5 %. For ALD at 0.10 nm/cycle that is exactly +10 cycles; for CVD it's +5 % time or rate. A model change (e.g., interfacial layer fixed 1.0 → 0 nm) can also shift the top layer by ~1 nm with *no* spectrum change — check step 1 first.

---

## Case 2 — Center-to-edge pattern change（中心—邊緣分布改變）

Before: flat. After: center > edge (dome), mean nearly unchanged.

1. Quantify: radial coefficient a₁ went from ~0 to, e.g., −0.4 nm (dome). Trend a₁ by chamber.
2. Exclude Metro: same site map version? map rotated? edge sites on pad? A site-map change can fake a dome.
3. Process hypotheses: showerhead clogging/plugging pattern, heater zone failure, plasma (RF matching, electrode spacing), edge ring wear, wafer centering (would give tilt + dome).
4. Evidence: chamber sensor data (zone heater power, RF reflected power), PM records, other chambers.
5. Note: **Cpk may hold while uniformity fails** — wafer-mean charts miss this; within-wafer σ / radial coefficients catch it.

---

## Case 3 — One Metro tool reads +0.6 nm

A, B: 20.0 nm; C: 20.6 nm on the same reference wafer.

Ladder (see [[13 Tool-to-Tool Matching]]): same wafer & sites → recipe version → raw-signal overlay → calibration state → model/n,k version → standards → maintenance.

Typical outcomes:
- Raw Ψ/Δ differ by a constant offset → AOI/polarizer calibration on C.
- Raw identical, output differs → recipe/library not synchronized to C.
- Difference grows with thickness → wavelength calibration.
- Only some sites differ → focus/stage/spot.

---

## Case 4 — ALD thickness control（ALD 膜厚控制）

Target 20.0 nm, GPC 0.10 nm/cycle → N = 200. Measured 21.2 nm (+6 %).

| Candidate | Expected evidence | Quick test |
|---|---|---|
| Cycle count 212 | Recipe log shows 212 | Log audit |
| GPC +6 % (T above window) | Heater setpoint/reading high; n/impurity change | Temperature check, d-vs-N slope on a short loop |
| Precursor over-delivery | Usually no effect in window (self-limiting) | — (unless purge also short) |
| Insufficient purge → parasitic CVD | Thicker near inlet/center; worse uniformity; particles | Map signature + purge-time split |
| Pressure change | Purge efficiency ↓ | Pressure log |
| Surface condition (nucleation faster) | Offset, not ∝ N | d-vs-N intercept changes |
| Chamber history (post-clean first wafers) | First wafers after clean differ | Wafer sequence vs clean |
| Metro model | Spectrum unchanged but output changed; or n moved | Raw/model check; second tool |

**Efficient sequence (cheap → expensive):**
1. Cycle count and recipe revision
2. Temperature readings
3. Process sensor traces (pressure, valve timing)
4. Compare chambers same day
5. Reference/control wafer on Metro
6. Wafer map (signature)
7. Metro raw signal & model (n fit, GOF)
8. Independent reference (XRR/TEM)

**Decision table on the d-vs-N plot:**
- Slope ↑, intercept same → GPC changed (process chemistry / T / parasitic CVD)
- Slope same, intercept ↑ → nucleation / interface / model handling of IL
- Both same → look elsewhere (Metro, sampling)

---

## Case 5 — CVD: mean stable, sigma up（CVD：平均穩定、變異擴大）

The process may have **lost uniformity without a mean shift**. Cpk falls because σ rose, not because the mean moved.

Separate the sigma: within-wafer (map) vs wafer-to-wafer (sequence) vs lot-to-lot:
- **Within-wafer σ up** → gas distribution, temperature uniformity, wafer centering, plasma — check map coefficients.
- **Wafer-to-wafer σ up** → seasoning, first-wafer effect after idle, chamber clean cycle, slot position (batch furnace).
- **Measurement σ up** → repeatability check on the monitor; dynamic repeat; site PR issues.

> Mean and variation must be analyzed separately — they have different causes.

---

## Case 6 — Etch remaining thickness（蝕刻殘膜）

Pre d₀ = 100.0 nm, post d₁ = 62.0 nm, t = 60 s → ER = 0.633 nm/s.

Uncertainty: σ₀ = σ₁ = 0.3 nm.
- Independent errors (different tools/sites): σ_Δ = 0.42 nm → σ_ER = 0.0071 nm/s.
- Same tool + same site, correlated systematics ρ = 0.8: σ_Δ = 0.19 nm → σ_ER = 0.0032 nm/s.

Lesson: **site-matched, same-tool pre/post** halves the ER uncertainty here.

Watch-outs: pattern loading (blanket ≠ product ER), stop-layer consumption, post-etch surface modification (damaged/oxidized layer changes optical model), polymer residue.

---

## Case 7 — CMP removal and uniformity（CMP 研磨量與均勻性）

T_pre = 800 nm, target T_post = 500 nm, RR = 5 nm/s → feed-forward polish time = 60 s.

Problems seen by Metro:
- Post-CMP radial profile edge-thin → retaining ring / edge zone pressure; feed back to zone control.
- In-die erosion in dense arrays not visible on scribe pads → need in-die/OCD sites.
- Gradual RR decay with pad life → APC compensates; if Metro is biased, APC "compensates" wrongly.
- Dishing on wide lines → AFM/profiler reference.

Next: [[19 NPI and Recipe Qualification]].
