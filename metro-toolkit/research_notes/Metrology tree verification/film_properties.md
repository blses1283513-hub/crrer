# Film Property Metrology Beyond Thickness: Composition (XPS and alternatives), Stress, Density (XRR), Mass, Crystal Structure (XRD), Contact Angle

Scope note: public sources only, checked October 2026. "Typical" numbers are vendor or published examples, not fab specs. Verdict labels for the learner's notes: **VERIFIED**, **CORRECTED** (with the corrected wording), **UNRESOLVED**. Anything not tied to a source is under Inferences or Gaps.

---

## Q1. Composition by XPS: principle, information depth, EAL, thickness from intensity ratios, chemical state, inline precision/throughput, vacuum, spot size, damage

### Takeaway
The learner's XPS node is mostly right. Inline XPS (Nova VeraFlex, which came from ReVera) shines a monochromatic Al Kα beam about 50 µm wide on a scribe-line or in-die pad, in a chamber below 5×10⁻⁷ Torr. It gets layer thickness from how much the substrate or underlayer peak is weakened, using the effective attenuation length (EAL) in a Beer–Lambert model. It is most precise below about 2 nm and loses sensitivity above about 10 nm. Three items are UNRESOLVED: the 30–60 s per point figure (no public number found), the term "SLAM pad" and the phrase "darker pattern → thinner".

### Cited Findings
**Principle and physics**
- XPS uses the photoelectric effect. Monochromatic X-rays photoionize atoms, which emit core-level electrons. These travel through the material, escape into vacuum and are sorted by kinetic energy in an energy analyzer. The detector counts electrons in each energy window — [Nova/IBM, SPIE 13981 1398114 (2026)](https://www.novami.com/wp-content/uploads/2026/04/1398114-seldep-xps.pdf)
- Energy balance as given in a university core-facility tutorial: KE = hν − BE − Ø — [Northwestern NUANCE, ToF-SIMS or XPS (2019)](https://nuance.northwestern.edu/documents/techtalks/2019-01-16-tt-keckll-xinqi.pdf)
- On the VeraFlex IV the photoelectrons pass through electron optics and a hemispherical (spherical capacitor) analyzer before reaching the detector. Spectra are kinetic energy against count rate — [Nova/IBM, SPIE 13981 139810A (2026)](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)

**Information depth / "cannot detect deep electrons"**
- For electrons leaving along the surface normal, about 65% of the signal comes from within 1λ of the surface, 85% from within 2λ and 95% from within 3λ. The attenuation length of Si 2p electrons in Si excited by Al Kα is about 2.8 nm — [Thermo Fisher, Angle Resolved XPS app note](https://documents.thermofisher.com/TFS-Assets/CAD/Application-Notes/D16069~.pdf)
- XPS information depth is under 10 nm; ARXPS covers near-surface layers to about 10 nm — [Thermo Fisher ARXPS](https://documents.thermofisher.com/TFS-Assets/CAD/Application-Notes/D16069~.pdf). Another source gives the XPS information depth as 5–10 nm — [Vad et al., PMC (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11316073). Thermo describes XPS as "non-destructive, high-surface-sensitivity analysis, typically within a 0–10 nm depth range" in ultra-high vacuum — [Thermo Fisher white paper (2025)](https://documents.thermofisher.com/TFS-Assets/MSD/Reference-Materials/evolution-of-xps-depth-profiling-white-paper.pdf)
- Inline: the exponential sensitivity lets XPS detect small changes in films thinner than 2 nm. Bulk scattering largely removes sensitivity beyond about 10 nm of material with an Al Kα source — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)
- Photoelectrons from deeper in the film are more likely to be scattered once or many times, both inelastically and elastically. The EAL describes how the photoelectron yield falls with path length and scattering — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)

**IMFP vs EAL vs information depth (ISO 18115 / NIST terminology)**
- NIST (Powell 2020) defines four separate terms: inelastic mean free path (IMFP), effective attenuation length (EAL), mean escape depth (MED) and information depth (ID). The IMFP is a material parameter that depends on electron energy. The other three also depend on the instrument configuration, and different EALs apply to different XPS uses — [NIST, Powell, JVST A 38, 023209 (2020)](https://www.nist.gov/publications/practical-guide-inelastic-mean-free-paths-effective-attenuation-lengths-mean-escape)
- The most common EAL use is measuring the thickness of an overlayer film on a flat substrate. EALs for this are tabulated in the NIST Electron Effective-Attenuation-Length Database (SRD 82) — [NIST practical guide PDF](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=929257)
- Elastic electron scattering makes the EAL differ from the IMFP, which matters for SiO₂/Si thickness by XPS — [Powell & Jablonski, NIST (2001)](https://www.nist.gov/publications/measurement-silicon-dioxide-film-thicknesses-x-ray-photoelectron-spectroscopy). To include elastic scattering, the IMFP λi is replaced by the EAL λA — [arXiv 2512.24756, Essential Principles and Practices in XPS](https://arxiv.org/html/2512.24756v2)

**Thickness from intensities (the learner's "Acquisition → Intensity Extraction → Thickness & Composition")**
- For blanket single or multi-layer films, thickness comes from peak-fit signal intensities, EALs, absorption constants, and the Beer–Lambert weakening of the substrate signal through the overlayer — [Nova/IBM 1398114](https://www.novami.com/wp-content/uploads/2026/04/1398114-seldep-xps.pdf)
- SiO/Si example: the Si substrate intensity falls exponentially with d_SiO/EAL_SiO while the SiO intensity grows. Thickness is found by scaling the Si and SiO intensities against each other — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)
- Layer-by-layer stack thickness can be measured precisely as long as each layer has its own identifiable peak. Si/SiGe nanosheet stacks need corrected models because both layers contribute to the Si peak — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)
- Thermo's Avantage software uses TPP-2M attenuation lengths and NIST SRD 82, and handles up to three layers on a substrate — [Thermo Fisher ARXPS](https://documents.thermofisher.com/TFS-Assets/CAD/Application-Notes/D16069~.pdf)
- On patterned area-selective deposition targets, the pre-deposition intensity ratios are stored as a "structure correction factor" and fed forward. Later changes in intensity are then attributed only to the new growth — [Nova/IBM 1398114](https://www.novami.com/wp-content/uploads/2026/04/1398114-seldep-xps.pdf)

**Composition and chemical state**
- XPS strengths listed by Nova: surface sensitive; identifies the element and its bonding state; directly counts the number of atoms in the film; gives thickness and composition together "without correlation" — [Nova Materials Metrology brochure (2022)](https://www.novami.com/wp-content/uploads/2023/05/nova-brochure-materials-metrology-2022-compressed-1.pdf)
- Lab-XPS figures from a core facility: sees all elements except H and He; gives chemical state; quantitative to about ±5%; detection limit about 0.1 at%; spot size 20–900 µm (lab tool); non-destructive — [Northwestern NUANCE comparison table](https://nuance.northwestern.edu/documents/techtalks/2019-01-16-tt-keckll-xinqi.pdf)

**Inline tool facts (vacuum, beam, throughput, history, applications)**
- Inline XPS needs an analysis chamber below 5×10⁻⁷ Torr. Wafers wait in a load lock that pumps down while the current wafer is measured. To raise throughput, tools use one fixed X-ray source, a fixed take-off angle and a fixed high pass energy. Recipes keep spectral ranges, scan time and sites per wafer to a minimum — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)
- The VeraFlex IV makes Al Kα X-rays in a 50 µm spot, so targets must be at least that large. It handles 300 mm wafers fully automatically — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf). Nova says it can measure in the scribe line and in-die on device — [Nova VeraFlex IV product page](https://www.novami.com/nova-product/nova-veraflex-iv)
- Inline XPS arrived in 2004 for the 65 nm node, when ellipsometry could no longer resolve gate-stack thickness changes accurately — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)
- Nova reports "hundreds of installed systems over 5 model generations" and calls VeraFlex the industry standard for combined XPS + XRF — [Nova VeraFlex page](https://www.novami.com/nova-product-category/materials-metrology/nova-veraflex)
- ReVera (bought by Nova in 2015) was described as setting the standard for high-k/metal gate, tunnel oxide and capacitor film metrology — [Nova 6-K, SEC (2015)](https://www.sec.gov/Archives/edgar/data/1109345/000117891315000843/zk1516417.htm). The VeraFlex III XF (2013) added a low-energy XRF channel driven by the same X-ray source, to reach thicker and buried films — [MetrologyWorld (2013)](https://www.metrologyworld.com/doc/revera-announces-new-inline-thin-film-metrology-system-0001)
- XRF spectra can be collected during XPS at no extra time. XRF is attenuated over much longer distances, so its intensity scales linearly with the amount of material. One example is Ge Lα counts used for SiGe indent depth in a hybrid with OCD — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)
- The VeraFlex III XF was marketed for sub-ångström sensitivity on ALD processes at advanced logic nodes — [Nova press release (2017)](https://mayafiles.tase.co.il/rpdf/1123001-1124000/P1123757-00.pdf)

**Non-destructive**
- Nova/IBM call XPS "non-destructive" — [139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf). Thermo says ARXPS is non-destructive, unlike sputter profiling — [Thermo ARXPS page](https://www.thermofisher.com/us/en/home/materials-science/learning-center/surface-analysis/angle-resolved-xps.html)
- XPS depth profiling with an ion beam is destructive and changes the probed volume, so chemical information is usually lost — [arXiv 2512.24756](https://arxiv.org/html/2512.24756v2); [Thermo white paper](https://documents.thermofisher.com/TFS-Assets/MSD/Reference-Materials/evolution-of-xps-depth-profiling-white-paper.pdf)

**Claim verdicts (XPS)**

| Learner claim | Verdict | Basis |
|---|---|---|
| XPS gives film thickness and atomic concentration | VERIFIED | Nova brochure; Nova/IBM 139810A |
| Photon in, kinetic energy measured | VERIFIED; add: KE = hν − BE − φ, and binding energy identifies element and chemical state | Northwestern; Nova/IBM 1398114 |
| Non-destructive | VERIFIED for inline XPS (no sputtering). Caveat: sputter depth profiling is destructive; beam-sensitive organics/SAMs not quantified in public data (see Gaps) | Nova/IBM; Thermo |
| Product wafer pad or test wafer | VERIFIED (≥50 µm pad, scribe line or in-die; blanket monitors also used) | Nova/IBM 139810A; VeraFlex IV page |
| "SLAM pad" | UNRESOLVED: no public definition found; probably a fab or company term for the metrology pad | — |
| Not integrated (standalone) | VERIFIED as far as public sources go: VeraFlex is a standalone vacuum tool with a load lock; no integrated XPS product found | Nova/IBM 139810A |
| 30–60 s per point | UNRESOLVED: no public number found; sources only say recipes minimize acquisition time | Nova/IBM 139810A |
| Thickness < 100 Å | VERIFIED (most precise < 2 nm; sensitivity lost > ~10 nm with Al Kα; 95% of signal within 3λ ≈ 8 nm for Si 2p) | Nova/IBM; Thermo |
| For DRAM, NAND | VERIFIED but incomplete: "capacitor film" (DRAM) and "tunnel oxide" (NAND) are named, and logic HKMG/GAA/BEOL ASD is the original and growing use | SEC 6-K; Nova/IBM papers |
| Recipe flow: Acquisition → Intensity Extraction → Thickness & Composition | VERIFIED (spectra → peak-fit intensities → EAL/Beer–Lambert model) | Nova/IBM 1398114 |
| Thickness via EAL | VERIFIED; EAL ≠ IMFP (includes elastic scattering), from NIST SRD 82 | NIST Powell 2020 |
| "Darker pattern → thinner" | UNRESOLVED (see Inferences) | — |
| Electrons lose energy on the way to the surface, so deep electrons are not detected | VERIFIED (inelastic scattering removes them from the peak; elastic scattering also counts) | Nova/IBM; NIST |

### Inferences
- Thickness model (standard Hill-type form that follows from the Beer–Lambert relation the sources cite): I_sub = I_sub∞·exp(−d/(λA·cosθ)) and I_ov = I_ov∞·[1 − exp(−d/(λA·cosθ))], so d = λA·cosθ·ln(1 + (I_ov/I_ov∞)/(I_sub/I_sub∞)). θ is the emission angle from the surface normal. Inline tools fix θ, which is why EAL and sensitivity factors can be built into the recipe.
- With λ ≈ 2.8 nm for Si 2p (Thermo), 3λ ≈ 8.4 nm. This supports the "~5–10 nm" rule and the learner's "< 100 Å".
- "Darker pattern → thinner": the most likely meaning is the model plot or wafer map in the learner's training. As the overlayer gets thinner, the substrate (underlayer) peak gets stronger and the overlayer peak weaker. Whether "darker" means thinner depends on the colour scale of a specific tool's map or contour plot; it is not a physical rule. Ask the trainer which plot it refers to. Teach it as "stronger substrate signal = thinner overlayer".
- Al Kα photon energy is 1486.6 eV (standard value, not taken from the sources above). This sets an upper limit on KE and so on EAL and depth.
- X-ray damage: for the inorganic gate, high-k and barrier films that are typical inline XPS targets, practitioners and vendors treat the measurement as non-destructive. SAMs, photoresists and polymers can degrade under long X-ray exposure. Product-wafer sampling should take this into account. No public dose-damage data for inline tools was found.

### Gaps
- No public per-site time or wafers/hour for VeraFlex, and no 1σ precision spec (e.g. Å or at% N). Vendor datasheets are not public.
- The meaning of "SLAM pad" was not found.
- No quantitative public data on X-ray-induced damage under inline XPS conditions.
- ISO 18115-1 wording itself was not retrieved (paywalled). The NIST Powell 2020 guide follows ISO 18115 definitions.

---

## Q2. Composition alternatives: XRF, SIMS, AES (and when to use them instead of XPS)

### Takeaway
XPS is the inline choice for ultrathin films because it is quantitative, gives chemical state and does no sputtering. XRF reaches deeper and scales linearly with the amount of material, so it suits thicker or buried films, often run together with XPS. SIMS has ppm–ppb sensitivity for dopants and impurities but sputters the sample and gives no chemical state. AES has a shallower information depth and finer spatial and depth resolution, but weaker chemical information.

### Cited Findings
- XPS vs ToF-SIMS vs SEM-EDX (typical lab values): sampling depth up to 10 nm / up to 5 nm / 0.5–3 µm. Quantification ±5% / semi-quantitative / ±15%. Detection limit 0.1 at% / ppm–ppb / 0.5 wt%. Surface damage: non-destructive / destructive / non-destructive — [Northwestern NUANCE (2019)](https://nuance.northwestern.edu/documents/techtalks/2019-01-16-tt-keckll-xinqi.pdf)
- SIMS depth profiling: fast, better depth resolution, good for trace elements, but qualitative, with no chemical information and destructive. SIMS mapping reaches about 100 nm resolution and detects all elements including H and isotopes — [Northwestern NUANCE (2023)](https://nuance.northwestern.edu/documents/techtalks/2023-05-18-keck-ii.pdf)
- AES has a smaller information depth than XPS, so better depth resolution, while XPS is better for chemical information — [Vad et al., PMC (2024)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11316073)
- Comparing sputter depth profiling methods, AES and XPS gave the most reliable thin-film results, and SIMS was best for impurities — [IAEA INIS (2003)](https://inis.iaea.org/records/9j689-vzv96)
- Inline XRF: its signal scales linearly with the amount of material and it is not limited by XPS sampling depth. Nova combines XPS with low-energy XRF in one tool — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf); [Nova VeraFlex IV](https://www.novami.com/nova-product/nova-veraflex-iv)
- XRR is often used to calibrate thickness standards for XRF — [Rigaku XRR](https://rigaku.com/resources/techniques/x-ray-reflectometry-xrr?setLang=english)

### Inferences
- A toolkit decision rule: a film under 10 nm that needs inline chemistry → XPS; thicker or buried films, or dose/amount → XRF (or XPS+XRF); dopant/impurity depth profiles at ppm or below → SIMS (offline, destructive); nanoscale lateral or depth composition → AES/TEM-EDX (offline).

### Gaps
- No public inline SIMS or AES tools found for HVM. They are offline/lab techniques in the sources reviewed.

---

## Q3. Film stress: measurement, Stoney equation, sign convention, units, "normalized to 1 µm", why it matters

### Takeaway
Stress is measured by laser curvature scanning (Toho FLX, FSM 128 and others) before and after deposition, then converted with Stoney's equation. The quantity that curvature actually gives is the stress-thickness product σ_f·t_f (force per unit width, N/m). Dividing by film thickness gives the average stress in MPa. Convention: tensile is positive (concave wafer) and compressive is negative (convex wafer). The note "normalized to 1 µm film thickness" should be CORRECTED (see verdicts). Stress drives wafer bow, which degrades litho depth of focus and overlay and causes cracking, voiding and delamination. It is a major 3D NAND issue.

### Cited Findings
**How it is measured**
- The Toho FLX-2320 uses a laser to measure wafer curvature before and after film deposition and calculates film stress from the difference. Specs: 1 MPa–4 GPa range, 6 s per scan, repeatability 1 MPa, RT–500 °C, 2-D stress mapping — [NIST NanoFab tool page](https://www.nist.gov/laboratories/tools-instruments/nanofab-tool-toho-technology-flx-2320-stress-measurement-tool)
- FLX-2320-S spec: range 1×10⁷ to 4×10¹⁰ dyne/cm², repeatability (1σ) 1×10⁷ dyne/cm², accuracy <2.5% or 1 MPa, minimum radius 2.0 m. Specs are quoted "for typical 0.525 mm Si (100) wafer with 10,000 Å film and 80 mm scan length". The FLX is built on the original KLA-Tencor design — [Toho FLX-2320-S spec sheet (Utah Nanofab)](https://www.nanofab.utah.edu/wp-content/uploads/2022/12/Film-stress-Tencor-FLX2320-Spec-Sheet.pdf.pdf)
- FLX series uses KLA-Tencor's patented dual-wavelength technology (670/780 nm lasers). Range 1–4000 MPa (3500 MPa for the 300 mm FLX-3300), repeatability 1.3 MPa, maximum radius 33 km. Specs are footnoted "725 µm wafer thickness for 10,000 Å thin film" — [Toho FLX Series](https://tohotechnology.com/industries/metrology/flx-series); [Quantum Design FLX](https://qd-europe.com/hu/en/product/flx-flexus-thin-film-stress-measurement-systems); [Toho FLX-2320-S datasheet](https://tohotechnology.com/wp-content/uploads/2019/09/Toho_FLX2320S_D1.pdf)
- Automated FLX: 25 wafers/hour, maximum bow about 1 mm — [Toho FLX Automated](https://tohotechnology.com/industries/metrology/flx-series-auto)
- FSM 128C2C: fully automated cassette-to-cassette, SECS/GEM, more than 50 wafers/hour, bow up to 300 µm. The FSM 128L takes wafers up to 300 mm — [Metrosemi FSM 128](https://test.metrosemi.com/?page_id=606); [Metrosemi](https://metrosemi.com/)
- Stylus profilers (Bruker Dektak) can also measure stress from radial wafer-shape maps before and after deposition, scanning about 90% of the diameter in the same orientation — [Bruker TN-504](https://www.bruker.com/en/products-and-solutions/test-and-measurement/stylus-profilometers/resource-library/tn-504-thin-film-stress-measurement-using-dektak-stylus-profilers.html)

**Stoney equation**
- For elastically isotropic substrates: σ_f·t_f = E_s·h²/(6(1−ν)R), where h is substrate thickness and R the radius of curvature. Most curvature-based measurements today use Si wafers, and modified forms exist for Si(001) and Si(111) — [Janssen et al., "Celebrating the 100th anniversary of the Stoney equation", Thin Solid Films 517 (2009)](https://web.mit.edu/scholvin/www/nt245/Documents/Stress%20-%20celebrating_the_100th_anniversary_of_the_stoney_equation_for_film_stress.pdf)
- For (100) Si the biaxial modulus E/(1−ν) = 1/(s11 − s12) ≈ 180 GPa. Stoney's assumptions: isotropic elastic properties, uniform film thickness and temperature, stress uniform through the thickness, small deflection, and no cracking or stress relief — [Review, PMC (2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9783026)
- "The product σ̄·h_f is often referred to as the stress-thickness", and κ = 6σ̄h_f/(M_s·h_s²). Stress can vary with depth, and the incremental stress can differ in sign from the average stress — [Chason et al., JAP Tutorial 119, 191101 (2016)](https://pubs.aip.org/aip/jap/article/119/19/191101/1032395/Tutorial-Understanding-residual-stress-in)
- The Stoney equation should not be used when curvatures are high — [LibreTexts 11.5](https://eng.libretexts.org/@api/deki/pages/7854/pdf/11.5%253A%2bThe%2bStoney%2bEquation%2b-%2bthe%2bThin%2bCoating%2bLimit.pdf)

**Sign convention**
- Compressive residual stress gives a convex (dome) wafer and "is compressive and given a negative sign (−) by convention" — [Review, PMC (2022)](https://pmc.ncbi.nlm.nih.gov/articles/PMC9783026)
- A tensile film tries to contract and bows the substrate concave, which can cause microcracking. A compressive film tries to expand and bows it convex, which can cause buckling — [UT Dallas Toho FLX-2320-S manual](https://cores.research.utdallas.edu/manuals/toho-flx-2320-s-wavelength-stress-measurement)
- Average stress is positive when tensile — [Chason JAP 2016](https://pubs.aip.org/aip/jap/article/119/19/191101/1032395/Tutorial-Understanding-residual-stress-in)

**Why it matters**
- Excessive film stress causes deformation, cracking, delamination, shorts and other failures — [Bruker TN-504](https://www.bruker.com/en/products-and-solutions/test-and-measurement/stylus-profilometers/resource-library/tn-504-thin-film-stress-measurement-using-dektak-stylus-profilers.html)
- FLX troubleshooting list: Al stress voids, passivation (nitride/oxide) cracking, stress-induced dislocations in Si, WSi cracking, Si cracking, and electrical test yield loss — [Toho FLX Series](https://tohotechnology.com/industries/metrology/flx-series)
- In 3D NAND, cumulative stack stress drives wafer bow, which "has a significant impact on wafer yield due to degraded lithography depth-of-focus, overlay performance, and structural distortion". Lam's VECTOR DT deposits a tunable counter-stress film on the wafer backside — [Lam Research press release (2019)](https://www.globenewswire.com/news-release/2019/08/07/1898426/0/en/lam-research-adds-global-wafer-stress-management-solutions-to-portfolio-for-3d-nand-scaling.html)
- Film stress warps the free wafer: out-of-plane displacement plus in-plane displacement. When the litho chuck pulls it flat, the result is process-induced overlay error. KLA's WaferSight PWG (dual-Fizeau) measures wafer shape to feed overlay corrections forward — [Semiconductor Digest (2018)](https://sst.semiconductor-digest.com/2018/07/patterned-wafer-geometry-grouping-for-improved-overlay-control); [Turner et al., JM3 12(4) 043002 (2013)](https://www.spiedigitallibrary.org/journals/Journal-of-MicroNanolithography-MEMS-and-MOEMS/volume-12/issue-4/043002/Characterization-of-wafer-geometry-and-overlay-error-on-silicon-wafers/10.1117/1.JMM.12.4.043002.full) (a ~40 nm SiN film at about −3 GPa compressive produced ~100 µm warp on 300 mm)
- Large bow also blocks chucking. On 100 mm wafers, bow above 300 µm could not be clamped on most tools — [IMB-CNM, PMC (2020)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7766386)

**Claim verdicts (Stress)**

| Learner claim | Verdict | Corrected statement / basis |
|---|---|---|
| Deposited films (e.g. CVD) have stress | VERIFIED. Also thermal mismatch on cool-down, anneal, PVD, ALD | PMC review; Toho |
| Compressive = (−), tensile = (+) | VERIFIED (common convention; compressive → convex wafer, tensile → concave). Check each tool's sign setting | PMC review; UTD manual; Chason |
| "Normalized to 1 µm film thickness" | CORRECTED | "Curvature gives the stress-thickness product σ_f·t_f (N/m). The tool divides by the film thickness you enter to report average film stress in MPa, which is already independent of thickness. Vendor specs (range, 1–1.3 MPa repeatability) are quoted for a reference 1 µm (10,000 Å) film on a 525/725 µm wafer, so the stress resolution for thinner films is proportionally worse." Toho spec sheets; Chason; Janssen |
| Domain: Diffusion, CVD | VERIFIED but incomplete: also PVD metals (Al, W), CMP/anneal effects, backside films | Toho; Lam |

### Inferences
- Units: 1 MPa = 10⁷ dyne/cm² (shown by Toho quoting 1×10⁷ dyne/cm² = 1 MPa repeatability). Stress-thickness unit: 1 MPa·µm = 1 N/m. Example: −1 GPa × 100 nm = −100 N/m.
- Resolution scales as 1/t_f. With a ~1 MPa spec at 1 µm, a 100 Å film would have about 100 MPa resolution on the same wafer, assuming the curvature noise floor stays the same. That is why thin-film stress needs thinner substrates or thicker monitor films. This is an extrapolation, not a vendor number.
- Stoney needs t_f and the substrate thickness as inputs. Errors in entered film thickness go straight into the stress value (σ ∝ 1/t_f), so the stress monitor depends on the thickness measurement.

### Gaps
- No public detail on KLA's own current 300 mm production stress tools beyond PWG and the dual-wavelength IP licensed to Toho. No public data on 300 mm integrated stress modules.
- Typical stress values by film (e.g. PECVD SiN ±, LPCVD SiN ~ +1 GPa, thermal SiO₂ ~ −300 MPa) were not pulled from a primary source in this pass.

---

## Q4. Density via XRR (critical angle → electron density → mass density), precision

### Takeaway
VERIFIED: XRR measures density along with thickness and roughness. The total-reflection critical angle θc depends on electron density (θc ∝ √δ, δ ∝ ρ_e). Mass density follows once the composition (Z/A) is assumed. The fringe period gives thickness and the fringe damping gives roughness. XRR is absolute (needs no calibration), works on crystalline and amorphous films, and separates layers that differ in density by ≥ about 5%.

### Cited Findings
- The critical angle is proportional to √δ, and δ is proportional to the material's density through its composition (δ ∝ ρ·Σ(x_j·Z_j)/Σ(x_j·A_j)) — [RSC CrystEngComm SI, XRR background](https://www.rsc.org/suppdata/d3/ce/d3ce00371j/d3ce00371j1.pdf)
- Density can be calculated from where the critical angle sits, and the oscillation spacing gives film thickness. δ is about 10⁻⁵ and β about 10⁻⁸ — [LLNL/OSTI XRR investigation (2016)](https://www.osti.gov/servlets/purl/1236734)
- XRR measures thickness, density and roughness of single and multilayer stacks on wafers, crystalline or amorphous. It distinguishes films with at least ~5% density difference. It is a first-principles (absolute) technique needing no calibration and is used to certify XRF thickness standards. Above θc, reflectivity falls as θ⁻⁴ (faster for rough surfaces) — [Rigaku XRR](https://rigaku.com/resources/techniques/x-ray-reflectometry-xrr?setLang=english)
- XRR is "one of the few methods permitting the determination of density without weighing". Usable thickness range is about 2–200 nm (limited by roughness), thickness accuracy about 0.2 nm, on smooth substrates — [Fraunhofer IST](https://www.ist.fraunhofer.de/en/expertise/analytics-testing-technology/xrr.html). Another source gives about 1 nm–1 µm — [Lishchenko et al. (2026)](https://onlinelibrary.wiley.com/doi/10.1155/jnt/8821511)
- Example density precision: a-C films at 1.7 ± 0.05 g/cm³. When film density is at or below Si (2.33 g/cm³), the Si critical angle dominates and the film only changes its shape, which makes the fit harder — [Li Bassi et al., Diamond Relat. Mater. 9 (2000)](https://www-g.eng.cam.ac.uk/nms/publications/pdf/LiBassi_DRM2000.pdf)
- Density of buried layers is strongly correlated with other parameters and is a subtle part of the XRR model. Angle offsets bias thickness, density and roughness — [NIST, XRR alignment with GaAs/AlAs CRMs (2014)](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=912562)
- Fast XRR for fabs: a converging fan of X-rays with a detector that records the reflectivity pattern all at once. Density was checked against RBS — [OSTI, rapid XRR](https://www.osti.gov/biblio/21202317)
- Inline XRR platforms: Bruker 7300LSI (XRR + HRXRD + GIXRD) and Rigaku XTRAIA XD ("thin film and film stack thicknesses and density") — [Bruker 7300LSI](https://www.bruker.com/ko/products-and-solutions/semiconductor-solutions/automated-x-ray-metrology-systems/7300lsi.html); [Rigaku XTRAIA XD](https://rigaku.com/products/semiconductor-metrology/xtraia-xd-series)
- Mass metrology can also check density (SiN, hard-carbon masks) — [Lam blog (2019)](https://newsroom.lamresearch.com/Weighing-Wafers-Simplifies-Metrology?blog=true)

**Claim verdict:** "XRR also measures density (Diffusion, CVD, PVD)" — **VERIFIED**. Add: XRR measures electron density, and converting it to mass density needs an assumed composition. Best for smooth films about 1–200 nm thick.

### Inferences
- With Cu Kα, θc is roughly 0.2–0.3° for common films (from √δ with δ ~10⁻⁵, consistent with LLNL's δ magnitude). A 1% density error shifts θc by only ~0.5%, which is why careful alignment matters (NIST).
- If the composition is wrong (for example an oxygen-rich film modelled as stoichiometric), the electron density is still right but the reported mass density is wrong. Pair XRR with XPS or XRF composition.

### Gaps
- No public fab-grade 1σ density repeatability spec (g/cm³) for inline XRR tools was found. ±0.05 g/cm³ above is a research example.

---

## Q5. Mass metrology (wafer weighing): principle, resolution, applications, throughput, claim check

### Takeaway
The learner's description is broadly right. Lam's Metior (formerly Metryx) weighs the whole wafer before and after a step. It reports mass change with about 30 µg precision, equal to 1.8 Å of Si over a 300 mm wafer, in about a minute, touching only the backside. It is most valuable where optics fail: high-aspect-ratio etch, conformal ALD/liners, thick 3D NAND stacks and buried lateral recesses. Three corrections: it is not strictly "non-contact" (backside contact), it is available integrated as well as standalone, and the mass changes involved are µg to about 1 g, reported as mass (or converted to thickness).

### Cited Findings
- Mass metrology measures mass change after deposition, etch and clean, giving Å-level quantification. It is especially useful for HAR structures, complex 3D architectures and ALD, where optical methods struggle — [Lam Mass Metrology product page](https://www.lamresearch.com/products/mass-metrology)
- Metior is "available as both platform-integrated modules and as stand-alone systems" with "sub-milligram mass measurement capability" — [Lam Metior product family](https://www.lamresearch.com/product/metior)
- Metior "derives changes in mass directly from changes in weight and converts to thickness based on the known density of the material and the area covered by the film". Precision 30 µg ≈ 1.8 Å Si on 300 mm. Precision does not depend on layer thickness, composition or opacity, so relative sensitivity improves for thicker stacks. Non-destructive, used on product wafers, one recipe for all materials — [Lam blog, Metior and 3D architecture](https://newsroom.lamresearch.com/mass-metology-metior)
- 3D NAND: a ">17X pair class" full stack adds about 1 g to a 300 mm wafer (0.003% relative sensitivity), and a "2XX pair" stack about 1.3 g (0.0023%). Uses: HAR etch endpoint and incomplete-etch detection, feed-forward from deposition mass to etch time, liner deposition (furnace batch rate variation up to ~20%), chamber matching, isotropic etch, anneal/UV cure/plasma treatment, queue-time oxidation, voids, ion implant — [Lam blog, Metior](https://newsroom.lamresearch.com/mass-metology-metior)
- Earlier figure: 3σ precision in the 100 µg range gives Å-level sensitivity. Measurements are non-invasive "with only backside contact" and take "about a minute". Mass sensitivity on patterned wafers can be more than 10× that on blanket wafers for ALD films. Patterned wafers showed a mass deviation after a 1% precursor flow reduction, against 3% for blanket. Other uses: density of SiN and hard-carbon masks, residue removal in cleans — [Lam blog, Weighing Wafers Simplifies Metrology (2019)](https://newsroom.lamresearch.com/Weighing-Wafers-Simplifies-Metrology?blog=true)
- Metryx builds tools that monitor changes in a wafer's mass through fabrication, weighing it before and after a step to confirm the step was completed correctly — [Lam Mass Metrology page, "What is Metryx?"](https://www.lamresearch.com/products/mass-metrology)
- Lam's Chinese page says "microgram-level" capability and the Japanese page says "sub-milligram" — [Lam zh-hans](https://www.lamresearch.com/zh-hans/products/mass-metrology); [Lam ja](https://www.lamresearch.com/ja/products/mass-metrology)

**Claim verdicts (Mass)**

| Learner claim | Verdict | Corrected statement / basis |
|---|---|---|
| For very thin films in HAR structures (contacts, capacitors) | VERIFIED. Also thick 3D NAND stacks, channel-hole etch, replacement gate recess/fill | Lam blogs |
| e.g. film deposition and etching | VERIFIED. Also cleans, anneal/cure, oxidation, implant | Lam blog |
| Mass in grams | CORRECTED: "Reports wafer mass change (Δm), typically µg to mg for thin-film steps and up to ~1–1.3 g for a full 3D NAND stack. Precision about 30 µg (1σ basis not stated) or about 100 µg 3σ (2019). Can be converted to thickness using film density and covered area." | Lam blogs |
| Non-contact | CORRECTED: "Contacts only the wafer backside; does not touch the front, so it is safe for product wafers." | Lam 2019 blog |
| Non-destructive | VERIFIED | Lam |
| Blanket or product wafers | VERIFIED; patterned/product wafers can be >10× more sensitive than blanket for conformal films | Lam 2019 blog |
| Not integrated | CORRECTED: "Available standalone and as platform-integrated modules." | Lam Metior page |
| Domain: Diffusion, CVD | VERIFIED but incomplete: also Etch, Clean, Implant, Anneal/cure | Lam blog |

### Inferences
- Rough conversion: Δm = ρ·A·Δt. For Si (2.33 g/cm³) over a 300 mm wafer (A ≈ 707 cm²), 1 Å ≈ 16.5 µg. This matches Lam's 30 µg ≈ 1.8 Å. Use it as a sanity check in training.
- For a pre/post delta, the pre-measurement must be done on the same wafer. Wafer-to-wafer substrate variation (~grams of Si mass variation) would swamp µg changes.
- Precision weighing at the µg level normally needs corrections for air buoyancy, temperature and electrostatic charge. Lam's public pages do not describe how Metior handles these (see Gaps).
- Mass is an area-integrated quantity: it shows *how much* material changed but not *where* (top or bottom of a hole), so it is often paired with OCD or SEM.

### Gaps
- No public detail on the Metior measurement environment (buoyancy, temperature, charge control) or its wafers/hour spec.
- The precise "30 µg" sigma basis (1σ vs 3σ) is not stated on the Lam page.

---

## Q6. Crystal structure by XRD: grain size (Scherrer), crystallinity, texture, phase — what for, inline tools, limits

### Takeaway
VERIFIED: XRD covers all four learner sub-items. Inline/near-fab XRD (Bruker 7300LSI/JVX7300LSI, Delta-X; Rigaku XTRAIA XD) tracks phase, crystallinity, texture, grain size and residual strain. Typical subjects are W in NAND, ZrO₂/Al₂O₃/ZrO₂ (ZAZ) capacitor dielectrics in DRAM, high-k gate films (phase and grain size change with anneal, which changes k and leakage), Cu damascene texture, epitaxial SiGe/Si (HRXRD) and PZT/AlN for RF. Limits: weak signal from ultrathin films (needs grazing-incidence or in-plane geometry), mostly blanket or large-pad targets (≈50 µm small-spot option), and Scherrer gives only an apparent crystallite size.

### Cited Findings
- Bruker 7300LSI: in-fab R&D and in-line monitoring on full wafers, with XRR (thickness, roughness, density), HRXRD (strain, thickness, composition of epitaxial layers), GI/wide-angle XRD (phase, crystallinity, texture, residual stress) and in-plane XRD (phase and crystallinity of ultrathin films) — [Bruker 7300LSI](https://www.bruker.com/ko/products-and-solutions/semiconductor-solutions/automated-x-ray-metrology-systems/7300lsi.html)
- The JVX7300LSI is "widely used to measure crystallinity of polycrystalline films in advanced memory, such as W films in NAND and dielectric film stacks (such as ZAZ) in DRAM". It tracks peak intensity, position and width to control crystallinity, phase, texture and grain size. The S channel gives a 50 µm × 50 µm spot for test structures on patterned wafers — [Bruker Film Crystallinity](https://www.bruker.com/pl/applications/semiconductor-and-nanotech/memory/film-crystallinity.html)
- Automated in-plane XRD monitors grain size and crystallinity of high-k films in production. Different anneal temperatures caused a phase change, which can change the dielectric constant, and larger grains, which give poorer electrical properties — [Bruker High-k Crystallinity](https://www.bruker.com/ru/applications/semiconductor-and-nanotech/logic/high-k-crystallinity.html)
- IBM developed XRD metrology for crystallographic texture and phase in damascene Cu on 200 mm wafers, fast enough for in-line use — [IBM Research, MRS Proc. (2002)](https://research.ibm.com/publications/crystallographic-texture-and-phase-metrology-during-damascene-copper-processing)
- Bruker Delta-X/JV-DX: XRD, HRXRD, XRR, GIXRD, phase ID, residual stress, texture, grain size and XRF, with full 300 mm mapping — [Bruker Delta-X](https://www.bruker.com/pt/products-and-solutions/semiconductor-solutions/automated-x-ray-metrology-systems/delta-x.html)
- Rigaku XTRAIA XD: HRXRD and XRR for epitaxial strain, composition and thickness, plus crystalline phase and texture of polycrystalline films — [Rigaku XTRAIA XD](https://rigaku.com/products/semiconductor-metrology/xtraia-xd-series)
- XRD is "the established technique" for phase in PZT and other polycrystalline films, and is non-destructive — [Bruker BAW/SAW](https://www.bruker.com/ko/applications/semiconductor-and-nanotech/rf-devices/baw-saw-filter-phase-and-composition.html)
- Scherrer equation L = Kλ/(β·cosθ), from 1918 — [ResearchGate, Modified Scherrer equation](https://www.researchgate.net/publication/259706971_Modified_Scherrer_Equation_to_Estimate_More_Accurately_Nano-Crystallite_Size_Using_XRD). For accuracy, a modified approach recommends at least 5 peaks — [Nasiri et al. (2023)](https://www.sciencedirect.com/science/article/pii/S2666978123000132)
- XRD-calibrated Si thicknesses were used as the reference for inline XPS nanosheet models (hybrid use) — [Nova/IBM 139810A](https://www.novami.com/wp-content/uploads/2026/04/139810a-xps-integrated-trgts.pdf)

**Claim verdicts (XRD):** grain size, crystallinity, texture and crystal phase by XRD — all **VERIFIED** (Bruker, Rigaku). Add residual strain/stress (HRXRD, sin²ψ) and epitaxial composition (HRXRD) as further outputs.

### Inferences
- Meanings for learners: *phase* = which crystal structure (e.g. α-W vs β-W, tetragonal/orthorhombic/monoclinic HfO₂/ZrO₂); *crystallinity* = how much is crystalline vs amorphous (peak area); *texture* = preferred orientation (peak intensity ratios, pole figures; e.g. Cu (111) for electromigration); *grain size* = peak width via Scherrer.
- Scherrer limits (standard knowledge, not taken from the sources above): broadening also comes from microstrain and the instrument; K ≈ 0.9 depends on shape; it gives the coherent domain size *normal to diffracting planes*, which in thin films is often capped by film thickness; it becomes unreliable above about 100–200 nm. Williamson–Hall separates size from strain.
- Ultrathin high-k films (a few nm) give weak, broad peaks, which is why in-plane/GIXRD is used.

### Gaps
- No public throughput or precision specs (e.g. peak-width repeatability) for inline XRD tools.
- No public primary source pulled on ferroelectric HfO₂ orthorhombic-phase monitoring in HVM (the search returned none directly).

---

## Q7. Contact angle (Wet): what it measures, how, destructive?, typical values, inline tools

### Takeaway
The learner's node has no technique noted. The technique is **water contact angle by sessile-drop goniometry** (optical tensiometer), described by Young's equation. It is used to check (1) surface cleanliness and hydrophilicity after wet cleans: low angle = clean/hydrophilic oxide, while HF-last H-terminated Si is about 75°; and (2) HMDS priming for resist adhesion: bare Si ≤ about 40° goes to 65–80° after priming, with 65–85° the accepted window and > about 85° = over-priming. It is usually done on monitor wafers with automated stand-alone tools. It is generally called non-destructive, but a droplet is placed on the surface. No integrated inline HVM tool was found.

### Cited Findings
- Young's equation: γ_S = γ_SL + γ_L·cosθ — [Kyowa Interface Science](https://www.face-kyowa.co.jp/english/en_science/en_what_contact_angle.html); [KRÜSS glossary](https://www.kruss-scientific.com/en/know-how/glossary/youngs-equation)
- Sessile drop method: a micro-syringe deposits a droplet of a known liquid (usually ultrapure water or diiodomethane), a camera captures the profile and software calculates the angle. Low angle = high surface energy and good wetting. Automated systems map 200/300 mm wafers to give surface-energy uniformity — [Applied Physics USA](https://appliedphysicsusa.com/surface-energy-measurement-treated-wafers)
- Low contact angle indicates clean or hydrophilic surfaces, and high contact angle suggests contaminants or hydrophobic layers. Before HMDS, the water contact angle on bare Si is ≤ about 40°. After successful priming it is usually 65–80°. No increase, or large variation, means priming failed or was uneven — [Nanoscience Instruments (2025)](https://www.nanoscience.com/blogs/wettability-analysis-in-semiconductor-processing)
- Moreau (1988): a contact angle of 65–85° is desirable on Si, SiO₂ and SiN because resist dewetting occurs outside this range. Above 85° indicates over-priming, which can cause adhesion loss and blistering in developer — [US Patent 5,702,767](https://patents.justia.com/patent/5702767)
- HMDS vapor prime is checked by putting monitor wafers in the chamber and measuring contact angle before and after with a goniometer. "Water droplet contact angle measurement is a practical way to indicate adhesion". Vapor-primed contact angles stayed stable for at least two weeks, while spin-primed wafers fell below spec after three days — [YES HMDS app note (MIT)](https://web.mit.edu/scholvin/www/nt245/Documents/HMDS%20Application%20Note.pdf). YES TA series claims contact angle within ±3° — [YES TA Series](https://cdn.prod.website-files.com/666c435995051b6c447fa7f2/66b9fb9d8feb8a3efe5e8bc7_TA-Series.pdf)
- Over-priming (liquid prime after vapor prime) causes very poor adhesion. Primed surfaces stay hydrophobic for days, but coating soon after priming is recommended — [Cornell CNF](https://www.cnfusers.cornell.edu/sites/default/files/Equipment-Resources/General%20Information%20Sheets08.pdf)
- A Si wafer conditioned in HF is hydrogen-passivated with a contact angle of about 75°. Contact angle was used, with AFM, to check removal of HMDS and light organics by ozonated DI water — [ECS Cleaning Technology VII, PV 2001-26](https://www.electrochem.org/semiconductor_cleaning/pv_2001_26.pdf)
- Contact angle checks wafer cleanliness after RCA cleaning and photoresist adhesion. Adsorbed water must be removed (dehydration bake) before HMDS — [Biolin Scientific (2021)](https://www.biolinscientific.com/blog/contact-angle-measurements-in-electronics)
- "One advantage of contact angle measurement is that it is non-destructive, allowing for the continuation of the processing" — [Biolin Scientific (2025)](https://www.biolinscientific.com/blog/silicon-wafer-cleanliness-evaluation-through-contact-angle-measurement). IEEE: contact angle measurement in 200 and 300 mm manufacturing gives "rapid, nondestructive and spatially and time resolved data in an automated mode" — [IEEE 731571](https://ieeexplore.ieee.org/document/731571)
- Automated wafer contact angle meter (Kyowa DMo-WA): range 0–180°, resolution 0.01°, accuracy 0.2°, samples up to 300 mm diameter, sessile/dynamic/advancing-receding methods, surface free energy (OWRK, Zisman and others) — [Kyowa DMo-WA](https://www.face-kyowa.co.jp/english/en_products/en_contact_angle/detail_01_2_4.html)
- Contact angle can be used to optimize substrate pretreatment for resist adhesion — [MicroChemicals app note](https://www.microchemicals.com/dokumente/application_notes/substrate_cleaning_adhesion_photoresist.pdf)

**Claim verdict:** "Contact angle (Wet): no technique noted" — **fill in**: water contact angle by sessile-drop goniometer (optical tensiometer); surface free energy from two or more liquids (water + diiodomethane, OWRK). Applies to Wet (post-clean, HF-last), Litho (HMDS prime), and also surface treatments (plasma, SAM, bonding prep).

### Inferences
- "Non-destructive" here means the surface is not structurally damaged. A water droplet does leave residue and watermark risk on product dies, so fabs normally use monitor or test wafers, or edge sites. That is consistent with YES using monitor wafers. Teach it as "non-destructive but contact/contaminating: use monitors".
- Contact angle is a surface-energy proxy, not a composition measurement. When an excursion is seen, follow up with XPS (C 1s contamination, Si–CH₃ from HMDS) or TOF-SIMS.
- Static angle depends on drop volume, time after dispense, ambient humidity and queue time since cleaning/priming. Recipes should fix these. HMDS angles drift with time and humidity (YES data).

### Gaps
- No public evidence of a contact-angle module integrated into an HVM track or wet bench, or of a 300 mm FOUP-to-FOUP SECS/GEM contact-angle tool with published throughput. Vendor claims of automated 300 mm mapping exist (Applied Physics, Kyowa), but no throughput numbers.
- No public sources found on fab-specific pass/fail contact-angle specs after particular cleans (SC1, SPM, DHF) beyond the HF-last ~75° and HMDS 65–85° windows above.
