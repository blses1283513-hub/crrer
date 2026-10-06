---
tags: [metro-thickness, practice, interview]
created: 2026-10-06
---

# Practice Questions with Worked Answers（練習題與解答）

← [[00 - Metro Thickness Hub]]

Try each one before opening the answer. Levels: ★ fundamentals · ★★ working · ★★★ strong.

---

### Q1 ★ — Reflectometry fringe thickness
A SiO₂ film (n = 1.46) shows adjacent reflectance maxima at 640 nm and 520 nm at normal incidence. Estimate d.

> [!answer]- Answer
> $d\approx\frac{\lambda_1\lambda_2}{2n(\lambda_1-\lambda_2)}=\frac{640\cdot520}{2\cdot1.46\cdot120}\approx 950\text{ nm}$.

### Q2 ★ — Cpk
Mean 50.3 nm, σ 0.4 nm, spec 48–52 nm. Cp? Cpk? Which side limits?

> [!answer]- Answer
> Cp = 4/(6·0.4) = 1.67. Cpu = (52−50.3)/1.2 = 1.42; Cpl = (50.3−48)/1.2 = 1.92. Cpk = 1.42, limited by USL. Re-centering to 50.0 would raise Cpk to 1.67.

### Q3 ★ — Uniformity definitions
Sites: 99.0, 100.0, 101.5, 100.5, 99.5 nm. Give half-range and 1σ uniformity.

> [!answer]- Answer
> Mean 100.1; range 2.5 → half-range 1.25 %. s = 0.962 → CV 0.96 %. Same wafer, different numbers: always state the definition.

### Q4 ★★ — Gauge capability
σ_meas = 0.08 nm; spec 20 ± 1 nm. P/T? Is the gauge adequate? What if the spec tightens to ±0.3 nm?

> [!answer]- Answer
> P/T = 6·0.08/2 = 24 % → conditional. At ±0.3 nm: 6·0.08/0.6 = 80 % → unacceptable; need a better recipe/technique (e.g., SE instead of reflectometry, more averaging, tighter model).

### Q5 ★★ — Measurement error and observed capability
True process σ = 0.10 nm, σ_meas = 0.06 nm. Observed σ? By what fraction is Cpk under-reported?

> [!answer]- Answer
> σ_obs = √(0.01+0.0036) = 0.1166 nm → observed Cpk is 0.10/0.1166 = 0.86 of true, i.e., 14 % low.

### Q6 ★★ — ALD diagnosis
Target 15 nm, GPC 0.1 nm/cycle (150 cycles). A d-vs-N short-loop gives: 50 cy → 5.8 nm, 100 cy → 10.8 nm, 150 cy → 15.8 nm. Before, the same loop gave 5.0/10.0/15.0. Process or interface?

> [!answer]- Answer
> Slope unchanged (0.10 nm/cy); intercept moved +0.8 nm → nucleation/interface (e.g., thicker interfacial oxide from a pre-clean change) or a model change in how the IL is handled — not a GPC/temperature change. Check pre-clean/queue time and model revision.

### Q7 ★★ — Etch-rate uncertainty
Pre 200.0 ± 0.5 nm, post 120.0 ± 0.5 nm (1σ each), t = 100 s. ER and σ_ER for (a) independent errors (b) correlated with ρ = 0.9.

> [!answer]- Answer
> ER = 0.80 nm/s. (a) σ_Δ = 0.707 nm → σ_ER = 0.0071 nm/s. (b) σ_Δ² = 0.25+0.25−2·0.9·0.25 = 0.05 → σ_Δ = 0.224 → σ_ER = 0.0022 nm/s. Site-matched, same-tool measurement pays off.

### Q8 ★★ — Tool matching
On 10 reference wafers spanning 10–100 nm, Tool B − Tool A difference goes from +0.05 nm at 10 nm to +0.50 nm at 100 nm. What correction structure? What hardware cause would you check first?

> [!answer]- Answer
> A slope (~0.5 %) with near-zero offset: $T_B\approx1.005T_A$. A pure offset correction would fail. Thickness-proportional error → check wavelength calibration (fringe positions scale with d) and n/k library differences; for SE also AOI.

### Q9 ★★ — Drift discrimination
Thin-oxide (3 nm) monitor reads +0.25 nm over 4 weeks on all three Metro tools equally; thick-oxide (100 nm) monitor is flat. Diagnosis?

> [!answer]- Answer
> Common to all tools and only visible on the thin film → the monitor wafer is collecting surface contamination (AMC), not tool drift. Clean/desorb per procedure, model an ambient layer, re-baseline.

### Q10 ★★ — SPC design
Wafer-mean chart limits were computed from site-to-site σ (0.10 nm) while the wafer mean of 49 sites varies lot-to-lot with σ = 0.05 nm. What will happen?

> [!answer]- Answer
> Limits based on σ_site/√49 ≈ 0.014 nm would be far too narrow vs the real 0.05 nm wafer-mean variation → constant false alarms. Use the σ of the plotted statistic (wafer means) from a stable period.

### Q11 ★★★ — Ellipsometry ultrathin
Why can't you float both n and d for a 1.5 nm oxide? What do you do?

> [!answer]- Answer
> In the ultrathin limit Ψ/Δ depend on d and n through essentially one combination; the Jacobian columns are nearly parallel (correlation ≈ 1). Fix n from thick-film characterization (or literature for thermal SiO₂) and fit d; account for ambient contamination layer; validate with XRR/TEM.

### Q12 ★★★ — Correlated parameters in ON stack
In an SiO₂/SiN/Si stack model, d_SiO₂ and d_SiN have correlation −0.95. Production shows d_SiO₂ +0.4 nm and d_SiN −0.4 nm on one lot. Real?

> [!answer]- Answer
> Probably not real: an anti-correlated pair moving equal and opposite is the signature of parameter trade-off. Check total stack thickness (better determined), GOF, residual; measure pre-SiN oxide (feed-forward) to fix d_SiO₂; validate with TEM if it matters.

### Q13 ★★★ — XRF vs optical disagreement
TiN liner: XRF says −5 %, optical says flat. Explain both possibilities.

> [!answer]- Answer
> XRF measures mass/area (Ti atoms). (1) Density dropped with constant thickness (e.g., more porous film, O incorporation) → XRF down, optical thickness flat (but n/k would shift). (2) True thickness drop that optics misses because the optical model's n/k absorbed the change. Resolve with XRR (density + thickness) and n/k trend.

### Q14 ★★★ — Excursion communication
Write the 6-line update for: Chamber C post-CMP thickness +12 nm edge-only, two lots, after head rebuild; reference wafer fine.

> [!answer]- Answer
> **Observation:** Post-CMP oxide +12 nm at edge ring (r > 135 mm) on Chamber C, lots X/Y. **Evidence:** Center/mid unchanged; other chambers normal; started after head rebuild (date/time). **Hypothesis:** Edge-zone pressure or retaining-ring change from rebuild → edge under-polish. **Verification:** Metro reference wafer and second tool within baseline; same site map version. **Action:** Equipment to verify head zone calibration/retaining-ring; consider edge-zone pressure adjust after verification; hold C to monitor wafers. **Monitoring:** Radial profile on next 3 lots; close when edge ring Δ < 2 nm. **Uncertain:** Pad change at same time not yet excluded.

### Q15 ★★★ — Design a recipe validation
A new 8 nm HfO₂ on 1 nm SiO₂ IL. List the validation plan.

> [!answer]- Answer
> Splits: HfO₂ 5/8/11 nm × IL 0.7/1.0/1.3 nm; TL dispersion for HfO₂ from multi-sample fit; IL fixed vs fitted study (correlation); XRR (total + density) and TEM on corners; static/dynamic repeat; GR&R across tools; split tracking slope ≈1; GOF across wafer incl. edge; nuisance test (anneal-induced crystallization shifting n); SPC + OCAP.

---
More scenarios → [[18 Excursion Case Studies]].
