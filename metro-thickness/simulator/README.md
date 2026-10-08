# DRAM Thickness Metro Simulator

Extension of the DRAM Metro Simulator artifact with the Metro Thickness Tools Book.
Hub: [[00 - Metro Thickness Hub]]

| Path | Content |
|---|---|
| `src/base.html` | Original DRAM Metro Simulator source (M2/M4/M5/M6, engine, state) |
| `src/thick-engine.js` | Pure physics/statistics: Airy/TMM optics, Ψ/Δ, Levenberg–Marquardt fit, Parratt XRR, XRF, ALD map, step coverage, leakage, pipeline into the DRAM engine, SPC/GR&R/Deming |
| `src/t1-optics.js` … `npi.js` | New modules T1 optics lab (+GOF), T2 ALD wafer map + coverage + 3D, T3 SPC/gauge/matching/APC, T4 excursion triage (11 cases), NPI scorecard |
| `src/ext-engine.js` | GOF, reflectometry vs SE precision across thickness, FFT thickness, Stoney stress, overlay 8-term model, CD-SEM linescan/threshold/PR, grating OCD (zeroth-order EMA, TE/TM) fit |
| `src/proc-engine.js` | Pre/post rate maps and selectivity, resist swing curve and etch budget, PVD reflectivity vs roughness, contact angle, BPSG and poly dopant |
| `src/p0-map.js`, `t10-prepost.js`, `t11-resist.js` | P0 process→measurement map with calculators, T10 pre/post (dry etch, CMP, wet), T11 resist thickness |
| `src/t1b-range.js`, `t5-slam.js` … `t9-stress.js` | T1b thickness range & n/k, T5 SLAM scribe-line marks, T6 CD-SEM, T7 overlay, T8 dry-etch OCD, T9 film stress |
| `src/terms.js` | Hover term popups fed by `../glossary/terms.json` |
| `build.py` | Patches base.html (each patch asserts its anchor) and bundles everything → `dist/` |
| `test/engine.test.js`, `test/ext.test.js`, `test/proc.test.js` | `node test/*.test.js`: checks against Wolfram (reflectance, Ψ/Δ, XRR, Stoney, EMA, overlay) and `code/metro_tools.py` |

Rebuild: `python build.py`. Numbers marked 🔴 in the page are illustrative.
