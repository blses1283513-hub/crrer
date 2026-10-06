---
tags: [metro-thickness, calibration, drift, monitor-wafer]
chapters: [17]
created: 2026-10-06
---

# 14 · Calibration and Drift（校正與漂移）

← [[13 Tool-to-Tool Matching]] · next → [[15 Residuals Fit Quality and Model Risk]]

## What gets calibrated (optical tools, generic)

| Item | Method (generic) | If wrong |
|---|---|---|
| Wavelength scale | Emission lines of a calibration lamp (e.g., Hg/Ar) | Thickness error ∝ d (fringe position) |
| Absolute reflectance | Bare-Si reference with known native oxide | n/k and thin-film bias |
| Angle of incidence | Fit to known oxide standard | Ψ/Δ offset → offset or slope |
| Polarizer/compensator azimuth & retardance | Instrument self-calibration routines | Δ error, worst near 0/180° |
| Stage / focus | Height maps, focus repeatability | Site-dependent bias |
| X-ray: angle zero, intensity, energy | Standards, beam alignment | XRR fringe/critical angle errors; XRF intensity scale |

**Traceability（追溯性）:** standards (e.g., certified SiO₂-on-Si thickness standards from national labs such as NIST SRM series, or vendor-certified wafers) link the fleet to SI units. Know your standard's own uncertainty — you cannot be more accurate than your reference.

## Drift sources

| Source | Time signature | Discriminating clue |
|---|---|---|
| Light source aging | Slow, monotonic; jumps at lamp change | Intensity counter trend; short-λ noise grows |
| Detector response | Slow | Dark/gain checks |
| Alignment / focus | Steps after PM or crash | Site-dependent |
| Optical contamination | Slow | Intensity loss, UV first |
| Stage / chuck | Steps | Map-pattern differences |
| Temperature (lab / tool) | Daily cycles | Correlate with fab temperature log |
| Hardware replacement | Step | Maintenance record |
| Software/model revision | Step | Change log |
| **Monitor wafer itself changes** | Slow upward drift on thin films | See below |

### The monitor-wafer contamination trap（監控片污染陷阱）
Thin-oxide monitor/reference wafers adsorb airborne molecular contamination (hydrocarbons, water) over days–weeks. On a 2–10 nm oxide, a few Å of apparent growth is common. The Metro chart drifts up; every tool sees the same drift → it looks like "all tools drifting" or a process shift.
Countermeasures: model an ambient layer, periodic **desorption/cleaning** per site procedure (e.g., bake or UV/ozone), retire and re-qualify monitors on a schedule, and **use thicker films** (less relative sensitivity) for long-term stability monitors where possible.

## Drift signature and discrimination

```text
Thickness
20.8│                ●
20.6│             ●
20.4│          ●
20.2│       ●
20.0│● ● ●
    └────────────────── Time
```

| Observation | Conclusion |
|---|---|
| Reference wafer on the same tool also drifts | Metro (or reference wafer aging) suspect |
| Reference stable, product drifts | Process / sample / recipe suspect |
| Reference drifts on all tools equally | Reference wafer itself is changing |
| Reference drifts on one tool only | That tool |

Always follow the site's formal control-wafer procedure (frequency, limits, reaction plan).

## Post-PM qualification (typical sequence)
1. Hardware health checks (lamp intensity, focus, stage)
2. Calibration routines
3. Standards measurement (within certified uncertainty)
4. Monitor wafers (within control limits vs pre-PM baseline)
5. Matching check vs fleet golden tool on reference set
6. Release to production + heightened monitoring for N days

Next: [[15 Residuals Fit Quality and Model Risk]].
