# DRAM Thickness Metro Simulator

Extension of the DRAM Metro Simulator artifact with the Metro Thickness Tools Book.
Hub: [[00 - Metro Thickness Hub]]

| Path | Content |
|---|---|
| `src/base.html` | Original DRAM Metro Simulator source (M2/M4/M5/M6, engine, state) |
| `src/thick-engine.js` | Pure physics/statistics: Airy/TMM optics, Ψ/Δ, Levenberg–Marquardt fit, Parratt XRR, XRF, ALD map, step coverage, leakage, pipeline into the DRAM engine, SPC/GR&R/Deming |
| `src/t1-optics.js` … `npi.js` | New modules T1 optics lab, T2 ALD wafer map + coverage + 3D, T3 SPC/gauge/matching/APC, T4 excursion triage, NPI scorecard |
| `src/terms.js` | Hover term popups fed by `../glossary/terms.json` |
| `build.py` | Patches base.html (each patch asserts its anchor) and bundles everything → `dist/` |
| `test/engine.test.js` | `node test/engine.test.js`: checks against Wolfram and `code/metro_tools.py` |

Rebuild: `python build.py`. Numbers marked 🔴 in the page are illustrative.
