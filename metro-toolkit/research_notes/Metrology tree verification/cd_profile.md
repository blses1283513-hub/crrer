# CD and Profile Metrology: CD-SEM, OCD, IR-CD, CD-SAXS, and Profile (trench depth / SWA / CMP)

Scope note: public sources only. Vendor numbers are marketing or conference figures for specific structures, so treat them as *typical/best case*, not guaranteed specs. Where a source does not say whether a number is 1σ or 3σ, that is flagged. Research date: Oct 2026. Older figures are dated inline.

---

## Q1. CD-SEM: principle, what it measures, precision, damage, integration, use

### Takeaway
The CD-SEM is a top-down, low-landing-energy (about 300–800 eV) SEM that measures CD, LER/LWR and contact holes directly from images, with no model needed. It is the standard tool for litho ADI CD and AEI CD. Repeatability is about 1% of the measured CD (3σ), and best cases on EUV resist are about 0.05–0.13 nm. It is an in-line standalone vacuum tool, not integrated into process tools. It is the *least* non-destructive of the in-line CD tools, because of resist shrinkage, charging, contamination, and local damage from high-kV beams. SE images give surface topography. BSE images (especially at high kV) give trench/hole bottoms and buried-layer overlay.

### Cited Findings
**Principle and what it measures**
- CD-SEMs use low electron landing energy (typically 300 eV to 800 eV), high-efficiency through-lens secondary-electron detectors and fast, accurate stages. They give top-down images of linewidth, edge roughness and contact holes, and can give 3D information if the beam is tilted. — [Orji et al., Nature Electronics 2018 (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- Top performance is limited mainly by drift, vibration, beam damage, charging and contamination, not by the electron optics. Measurements can be made SI-traceable using calibrated samples or displacement interferometry. — [Orji et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- Model-based (Monte Carlo) SEM analysis agrees with TEM cross-section profiles to < 1 nm on 10 nm FinFET structures. — [Orji et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- CD-SEMs measure CD after litho, to calibrate the scanner/process before etch, and after etch, to correlate intended pattern with result. This gives a litho–etch feedback loop. — [Applied Materials VeritySEM 10 release](https://ir.appliedmaterials.com/node/26166/pdf)
- AMAT calls the CD-SEM "the ruler of the fab" and says it produces "the most precise sub-nanometer measurements" and feeds scanners. (This is a vendor claim.) — [AMAT VeritySEM 20 page](https://www.appliedmaterials.com/us/en/product-library/veritysem-20-cd-metrology.html)
- Design-based metrology (DBM) automates recipe setup from layout and extracts 2D contours for comparison with GDS. — [IRDS 2024 Metrology](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- CD-SEM is a line-of-sight technique and cannot see re-entrant profiles. That limit is a key reason OCD took off. — [SemiEngineering 2023 (Onto's N. Keller)](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices)

**SE vs BSE, and high voltage**
- Hitachi CV5000 (30 kV, 2017) detects SE and BSE. It measures the bottoms of deep trenches and contact holes (> 3 µm deep, using high-energy BSE) and does overlay on actual device patterns *through insulator films*, with ≤ 0.3 nm accuracy and repeatability. — [Hitachi Review 2017](https://www.hitachihyoron.com/rev/archive/2017/r2017_04/eG02/index.html)
- Hitachi CV7300 is an "in-line measurement system" with 60 kV acceleration. It targets HAR deep-hole and trench-bottom CD for 3D NAND beyond 200 layers and high-precision overlay for DRAM and logic. — [Hitachi CV7300](https://www.hitachi-hightech.com/global/en/products/semiconductor-manufacturing/cd-sem/metrology-solution/semi-cv7300.html)
- AMAT VeritySEM 5i (2015) combined BSE imaging (via-in-trench bottom CD, 3D NAND bottom CD at aspect ratio ≥ 60:1) with a tilted beam (FinFET sidewall, fin and gate height). VeritySEM 10 uses BSE for deep structures in GAA and 3D NAND. — [AMAT 2015 release](https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-unveils-breakthrough-e-beam-metrology-tool); [AMAT VeritySEM 10](https://ir.appliedmaterials.com/node/26166/pdf)
- High-energy SEM (> 10 keV) with low-loss BSE detection images HAR bottoms, "although such beams cause known local electrical damage at the measurement site". The industry is reconsidering using it on non-electrical targets (scatterometry gratings, kerf features, sacrificial die). — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)

**Precision**
- "The CD-SEM has a measurement repeatability of about 1% of the measurement dimension in 3σ." Accuracy is adjusted with a calibrated standard (Standard Microscale). — [Hitachi High-Tech knowledge page](https://www.hitachi-hightech.com/global/en/knowledge/semiconductor/room/manufacturing/accuracy-precision.html)
- On EUV resist (Hitachi, 2023): repeatability was 0.07 nm at 300 V and 0.13 nm at 100 V. A charge-suppression scan ("SP scan") gave 0.05 nm at 100 V. The sigma convention is not stated on the slide. — [Hitachi, EUVL Workshop 2023](https://euvlitho.com/2023/P73.pdf)
- Hitachi CG7300 claims tool-to-tool matching "down to the atomic size level", about 10% better than the previous model. — [Hitachi CG7300](https://www.hitachi-hightech.com/global/en/products/semiconductor-manufacturing/cd-sem/metrology-solution/semi-cg7300.html)
- Older roadmap targets: ITRS 2007 listed wafer CD metrology tool uncertainty (3σ, P/T = 0.2) for isolated gate lines falling from 0.52 nm to 0.21 nm across the 2007–2015 roadmap columns. *This is an old figure.* It is a plausible origin of a "0.25 nm" number. — [ITRS 2007 Metrology](https://www.semiconductors.org/wp-content/uploads/2018/08/2007Metrology.pdf)

**Destructiveness (shrinkage, charging)**
- EUV resist shrinks under e-beam irradiation, and the effect grows as resist gets thinner and tighter. Low landing voltage reduces shrinkage but hurts repeatability because charging makes edge peaks unstable. — [Hitachi EUVL 2023](https://euvlitho.com/2023/P73.pdf)
- 193 nm resist shrinkage must be minimized. NIST found shorter pixel dwell (about 0.8 µs) reduces shrinkage. — [NIST CD-SEM parameters](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=822538)
- Repeated CD-SEM measurements shrink resist roughly exponentially. — [SPIE 8681 (2013)](https://proceedings.spiedigitallibrary.org/conference-proceedings-of-spie/8681/868128/Quantitative-CD-SEM-resist-shrinkage-study-and-its-application-for/10.1117/12.2011244.full)
- With High-NA EUV's thinner resists, the CD-SEM needs low landing energy "to minimize interactions with the delicate High-NA photoresist". — [AMAT VeritySEM 10](https://ir.appliedmaterials.com/node/26166/pdf)

**Throughput and integration**
- NIST describes SEMs as having "very high throughput" (relative to 3D-AFM). The SEM is "the main instrument used for in line process control" for CD. Its size measurement can depend on material properties and on proximity to other features. — [NIST 3D-AFM review 2019](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=918090)
- OCD is "considerably faster than CD-SEM" and gives sidewall angle and height in one measurement. (Educational site, secondary source.) — [halbleiter.org](https://www.halbleiter.org/en/metrology/cdsem)
- Integrated metrology platforms (mounted on CMP and etch tools for wafer-to-wafer APC) are optical (OCD/thin film), e.g., Nova i570 and Onto IMPULSE+. — [Nova Integrated Metrology](https://www.novami.com/nova-product-category/integrated-metrology); [Onto IMPULSE+](https://ontoinnovation.com/products/impulse/)

### Inferences
- "Precision 0.25 nm" is a reasonable round number for older or typical conditions. It should be restated as "about 1% of CD (3σ); modern tools reach about 0.05–0.15 nm repeatability on favourable targets; always state 1σ vs 3σ and static vs dynamic". For a 20 nm line, 1% (3σ) is about 0.2 nm, which is consistent with 0.25 nm.
- CD-SEMs are in-line (in the fab, on the metrology bay, measuring product wafers) but are standalone vacuum tools. They are not "integrated metrology" bolted onto a process tool. That role is filled by optical OCD and film tools.
- When to choose an alternative: when you need a buried or re-entrant profile, SWA, height or depth (use OCD or IR-CD); when you need high sampling or wafer-to-wafer control (use integrated OCD); when resist shrinkage is unacceptable; or for HAR > ~60:1 bottoms (use high-kV BSE CD-SEM, IR-CD or CD-SAXS).

### Gaps
- No public, vendor-neutral CD-SEM throughput figure (wafers/hr or sites/hr) was found. Do not quote a number without a source.
- No public source explicitly says "CD-SEMs are never integrated into process tools". This is inferred from the vendor portfolios above.

---

## Q2. OCD (optical scatterometry): principle, location, precision, speed, integration

### Takeaway
OCD is model-based, non-imaging, non-contact optical metrology. Broadband polarized reflectometry or ellipsometry spectra from a periodic target are fitted to RCWA simulations (or ML models) to extract CD (top/mid/bottom), height/depth, SWA, film thicknesses and other parameters, often 10 or more at once, on product wafers. Targets are periodic scribe pads (typically about 30–100 µm) or in-die arrays. Precision is sub-nm / "angstrom-level". It is faster than CD-SEM and is available both as standalone in-line tools and as integrated metrology on etch and CMP tools. Its main weaknesses are parameter correlation (non-unique fits) and dependence on reference metrology for accuracy.

### Cited Findings
- Scatterometry (OCD) "combines reflectometry or ellipsometry with electromagnetic simulations to measure dimensions of features in periodic structures". Unlike AFM it is non-contact. Its value is its "inline potential" for process control. — [NIST traceable scatterometry, 2011](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=908506)
- OCD determines CD "over a relatively large region: typically a spot size of 20 µm to 50 µm" and depends on comparing measured and modeled signatures. *(2007 figure.)* — [NIST 2007](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=32593)
- OCD is a non-imaging technique giving sub-nm model-based measurement of CDs, overlay and n,k of arrayed structures. Fitting is an inverse problem without a unique solution (e.g., Δh and Δw can alter scattering similarly). Ten or more parameters are now modeled. — [Orji et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- Orji Table 1: scatterometry advantages are "non-scanning (i.e. fast); non-destructive; in-line compatibility". Limitations are "inapplicable to isolated lines; spot size should underfill line arrays". Improvements needed are "spot size; target area reduction for more in-die placement; hybridization". Some tools use spot sizes of about 10 µm. — [Orji et al. preprint (NIST)](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=926234)
- IRDS 2024: "Since scatterometry currently makes measurements on special test structures, other CD metrology techniques (such as SEM, AFM, or TEM) may be employed to establish a correlation between CD and the shape of the scatterometry structure and CDs of the circuit." Models are calibrated with periodic verification against SEM and CD-AFM. — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- IRDS 2024: scatterometry "routinely provides line shape metrology and statistically valid average values for large numbers of features". It is used for contacts, vias and complex features with up to about 10 parameters. For GAA it is "one of the best-potential solutions for non-destructive, precise, accurate, and highly productive metrology". Scatterometry-based dose/focus extraction reaches about 1% (3σ) dose and about 10 nm (3σ) focus. — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- Scribe-line metrology targets of 50 × 50 µm are used for BEOL OCD (Nova Prism: polarized spectral reflectometry plus spectral interferometry). — [Nova/IBM SPIE 2025](https://www.novami.com/wp-content/uploads/2025/04/13426-33-stefan-schoeche-beol-dimensional-characterization-using-scatterometry-v3.pdf)
- The industry is driving toward in-die and fully integrated device metrology "rather than going through a dedicated metrology target in the scribe line", because scribe proxies and active areas can differ. — [Nova/IBM SPIE 2022](https://www.novami.com/wp-content/uploads/2023/04/120530s-vertical-travelling-scatterometry-for-metrology-on-fully-integrated-devices-ibm-nova-spie-2022.pdf)
- Onto (2023): OCD is non-destructive, takes less than a second per measurement, offers "angstrom level repeatability", and can measure tens of parameters at once. An 8 × 10 µm spot with < 4 s per site is quoted for SiC metal stacks. — [Onto, Compound Semiconductor 2023](https://ontoinnovation.com/wp-content/uploads/2025/08/The-road-to-SiC-process-control_CS-Mag_Oct23.pdf)
- Integrated metrology: Nova i570 HP is integrated with process tools for wafer-to-wafer APC on CMP and etch, and claims the "highest throughput in the market supporting the newest and fastest CMP polishers". Onto IMPULSE+ is integrated or standalone for CMP. — [Nova brochure 2022](https://www.novami.com/wp-content/uploads/2023/05/nova-brochure-dimentional-metrology-2022-compressed-1.pdf); [Nova i570 HP 2026](https://www.novami.com/wp-content/uploads/2026/02/dmd-all.pdf); [Onto IMPULSE+](https://ontoinnovation.com/products/impulse/)
- ITRS roadmaps have listed "scatterometry on track" (integrated into the litho track) since the 45 nm node. *(Old, 2007/2009.)* — [ITRS 2009 Metrology](https://www.semiconductors.org/wp-content/uploads/2018/09/Metrology.pdf)
- A standalone OCD example is KLA SpectraShape 10K/11K, which measures CD and 3D shape after etch and CMP (FinFET, multi-patterning, 3D NAND channel-hole bow). — [KLA 2017 via EDN](https://www.edn.com/kla-tencor-introduces-new-metrology-systems-for-leading-edge-integrated-circuit-device-technologies); [KLA 2020](https://ir.kla.com/news-events/press-releases/detail/24/kla-introduces-new-ic-metrology-systems)
- Onto Atlas V targets "buried features, not visible by CD-SEM". — [Onto Atlas V](https://ontoinnovation.com/products/atlas-v-system/)
- Accuracy vs reference: in NIST's traceable scatterometry vs CD-AFM comparison, widths at 20% height differed by about 4 nm, while mid-CD agreed within about 0.5 nm. — [NIST 2011](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=908506)
- Hybridizing OCD with AFM commonly improves top width by up to 4 nm. Offsets between tools exist, e.g., 2.7 nm mid-CD between CD-AFM and EUV scatterometry. — [Orji et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- Integrated scatterometry for poly-Si etch (2002) measured trench depth, wall angle, top and bottom CD and agreed with AFM and XSEM (e.g., PR thickness: SCD 396 nm, XSEM 390 nm, AFM 396 nm). *(Old example.)* — [AVS PEUG 2002](https://nccavs-usergroups.avs.org/wp-content/uploads/PAG2002/PEUG_01_2002_Metrology.pdf)

### Inferences
- "Usually not directly measured on wafer" should be CORRECTED. OCD *is* measured on the product wafer, either on dedicated periodic targets in the scribe line or on in-die periodic arrays. It is not direct imaging: it is indirect, model-based measurement. The learner probably meant "indirect" or "on a test structure, not the actual circuit feature".
- Precision 0.05–0.12 nm sits inside the public "angstrom-level / sub-nm" claims. No vendor-neutral source confirms those exact numbers.
- When to choose an alternative: isolated or non-periodic features, or local CDU/LER (use CD-SEM); HAR > ~50–80:1 or opaque stacks (use IR-CD or CD-SAXS); when the model has unresolved correlations (hybridize with CD-SEM, AFM or CD-SAXS).

### Gaps
- No public source found for the specific "0.05–0.12 nm" OCD precision range or its sigma convention. It is UNRESOLVED as a number.
- No independent wafers/hour figure for modern standalone OCD was found. Only vendor qualitative claims and old (2003) figures of > 150–200 WPH for Nanometrics combined film/OCD tools are available. — [Semiconductor Digest 2003](https://sst.semiconductor-digest.com/2003/09/nanometrics-unveils-metrology-tools)

---

## Q3. IR-CD (mid-infrared scatterometry): principle, HAR use, speed, integration

### Takeaway
IR-CD is OCD (Mueller-matrix ellipsometry plus RCWA-type modeling) moved to the mid-IR (about 5–10.5 µm). There, SiO2 and Si3N4 have absorption features and light penetrates deep HAR arrays. This allows z-profile (CD vs depth, bow), nitride recess and tungsten recess measurement in 3D NAND channel holes and slits up to about 80:1, measured on-device (in-die arrays). It is a standalone in-line, non-contact, non-destructive tool. Public sources claim HVM speed "comparable to OCD". No public source confirms that it is "slower than OCD".

### Cited Findings
- Onto Aspect is described as an "in-line, non-destructive infrared optical critical dimension (IRCD) system measuring Z-dimension profiling of high aspect ratio structures", aimed at 3D NAND and 3D DRAM. — [Onto Aspect](https://ontoinnovation.com/products/aspect-system)
- Conventional UV–NIR OCD (190 nm–1.7 µm) is well established. Mid-IR spectroscopic ellipsometry adds CD and profile of HAR holes: channel holes up to 60:1 and hardmask holes up to 25:1. — [Onto / Semiconductor Digest 2021](https://ontoinnovation.com/resources/mid-infrared-optical-metrology-for-high-aspect-ratio-holes-in-3d-nand-memory-manufacturing)
- IRCD uses 5.0–10.5 µm light because SiO2 and Si3N4 are nearly transparent in UV–NIR, giving little sensitivity there. Like OCD it relies on Mueller-matrix spectral response. "To meet the needs of HVM, IRCD needs to capture within-wafer and wafer-to-wafer variation at a processing speed that is comparable to OCD systems." — [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices)
- Onto and Micron reported short-term precision of 1.3% (3σ) for first- and second-tier channel-hole CD and nitride recess, with good correlation to destructive reference CDs. Tungsten recess after W etch was measured through surface plasmon polariton coupling on design-rule-matched slit pitch. Angstrom-level sensitivity is claimed, and it is usually better at higher aspect ratio. — [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices); [Keller et al., SPIE 12053 (2022)](https://doi.org/10.1117/12.2618035)
- In the 2020 first customer qualification, 3D NAND channel holes were about 100 nm in diameter and up to 8,000 nm deep (80:1). Onto called it "the industry's first in-line solution for metrology of high aspect ratio features at high-volume manufacturing speeds". — [Onto 2020 release](https://investors.ontoinnovation.com/news/news-details/2020/Product-News-Onto-Innovation-Announces-First-Customer-Qualification-of-New-Aspect-IRCD-System/default.aspx)
- Onto positioned IR-CD as an alternative to "slower, and more costly, X-ray technology" and destructive methods for aspect ratios > 80:1. (Vendor claim.) — [Onto 2020 suite release](https://s24.q4cdn.com/480160064/files/doc_news/Product-News-Onto-Innovation-Announces-Suite-of-Three-New-Metrology-Systems-for-Complete-Critical-Dimension-Process-Control-2020.pdf)
- IRCD and CD-SAXS "appear to be closest to in-line, nondestructive production use", with off-line accuracy verification by FIB-SEM or TEM. — [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices)

### Inferences
- IR-CD measures large in-die device arrays ("on-device"; "large arrays of 80:1 holes in a single measurement"). This matches the learner's location note: product-wafer live die array, or a scribe test structure.
- "Slower than OCD" is UNRESOLVED. It is plausible for some recipes, since IR sources and detectors are weaker, but the vendor position is near-OCD speed. "Not integrated with tool" is VERIFIED in practice: only standalone versions were found.
- When to choose IR-CD: dielectric HAR etch (channel hole, slit, hardmask), recess steps, and when UV–VIS OCD loses sensitivity with depth. When to choose CD-SAXS instead: tilt or center-line shift, very small features, metal-opaque stacks, or as an accuracy reference.

### Gaps
- No public IR-CD throughput figure (s/site or WPH) was found.
- No public evidence of an integrated (on-process-tool) IR-CD product was found as of 2026.
- No non-Onto IR-CD product source was found in this search. Other vendors may offer IR channels but this was not confirmed.

---

## Q4. CD-SAXS / X-ray CD: principle, accuracy, throughput, fab status, correlation

### Takeaway
CD-SAXS is transmission small-angle X-ray scattering (> ~15–17 keV, through the full wafer) from periodic arrays, measured at multiple incidence and azimuth angles. Fitting the diffraction orders gives the average 3D shape: CD vs depth, height, SWA, pitch and pitch walk, LER/LWR, hole tilt. It is non-destructive, non-contact, works through optically opaque layers, and is SI-traceable. Signal scales with electron-density contrast and height², so it is strong for HAR memory and weak for thin logic. It is commercial in-line (standalone) for 3D NAND and DRAM, e.g., KLA Axion T2000 (2022), at minutes per site. Accuracy is checked against FIB-SEM, TEM and 3D tomography, and correlated with CD-SEM. It is itself used to calibrate OCD.

### Cited Findings
- CD-SAXS is variable-angle transmission SAXS: essentially single-crystal diffraction where the lattice is the pattern period. The average shape comes from inverse iterative fitting. It needs > 17 keV X-rays and low divergence. Smaller features scatter to larger angles, making them easier to resolve. It measures SWA, linewidth, pitch and roughness. Its "primary limitation" is compact-source brightness, giving long measurement times. It is SI-traceable. — [Orji et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- Advantages: it can measure optically opaque materials (metals, a-C hardmasks), and the result is an average over millions of devices. Arrays should be ≥ 50 µm. In 2018 it was "rarely used in the fab due to the long characterisation time". *(Superseded for HAR memory, see below.)* — [Orji et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- IRDS 2024: SAXS measures CD, height, pitch, multiple-patterning errors, LER and average cross-section. Contrast comes from electron density. Signal scales with height², so HAR memory scatters orders of magnitude more strongly than logic. Modeling is lighter than RCWA, allowing real-time regression. Logic in-line use needs < 1 min with a < 100 µm spot, which requires better sources. For 3D NAND and DRAM, "commercially available in-line tools have recently been introduced to the fab". — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- GI-SAXS (grazing incidence) has a cm-long footprint and is much faster than transmission CD-SAXS. CD-SAXS and GI-SAXS can hybridize with OCD for buried or opaque layers. — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- NIST review (2023): it took about 20 years to reach the market because lab source brightness was lacking. Microfocus rotating-anode and liquid-metal-jet sources raised brightness by almost 10×. Dense tall arrays let lab sources do "in-fab measurements in minutes". — [Kline et al., JM3 2023 (NIST review)](https://www.spiedigitallibrary.org/journals/journal-of-micro-nanopatterning-materials-and-metrology/volume-22/issue-3/031206/Review-of-the-key-milestones-in-the-development-of-critical/10.1117/1.JMM.22.3.031206.full)
- NIST describes CDSAXS as commercialized for 3D NAND contact holes, with potential for GAA nanosheets and TSVs. — [NIST CDSAXS project](https://www.nist.gov/programs-projects/critical-dimension-small-angle-x-ray-scattering-cdsaxs-next-generation-line)
- Precision example (2008): static repeatability of 50 repeats gave CD 3σ = 0.1 nm, and LWR 3σ = 0.4 nm and 0.3 nm for 10 s and 20 s acquisitions. The same work was quantitatively comparing CD-SAXS to top-down CD-SEM. *(Old, research setup.)* — [NIST 2008](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=853580)
- KLA Axion T2000 (Dec 2022) is a transmission CD-SAXS system with a high-flux source, a vertical wafer and a multi-angle/azimuth stage. It handles HAR structures of 100:1 or more and measures width, shape and tilt top to bottom. It is aimed at inline monitoring and post-PM etch tool qualification, to "reduce dependence on ... destructive measurement methods such as FIB-SEM, TEM and cross-section SEM". — [KLA release](https://ir.kla.com/news-events/press-releases/detail/447/kla-launches-revolutionary-x-ray-metrology-system); [Axion fact sheet](https://pdf.directindustry.com/pdf/kla-corporation/axion-t2000/113449-1041363.html); [Metrology News](https://metrology.news/revolutionary-x-ray-metrology-system-launched-for-advanced-memory-chip-inspection)
- Rigaku: "a few minutes" per measurement gives depth-resolved CD with sub-nm sensitivity, plus depth, SWA and overlay shift. Transmission geometry suits depths > 1 µm (3D NAND, DRAM). Reflection geometry suits a few nm to about 200 nm (FinFET, GAA, CFET). — [Rigaku CD-SAXS](https://rigaku.com/resources/techniques/critical-dimension-saxs)
- SemiEngineering reports about 15 keV photons, used for HAR hole tilt and to calibrate OCD. It needs multiple angles, giving longer measurement time and higher CoO than OCD and CD-SEM. Bruker showed XCD vs FIB-SEM CD correlation. Hole tilt and center-line shift are measured in-line. — [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices); [Gin et al., JM3 2023](https://doi.org/10.1117/1.JMM.22.3.031205)
- Correlation practice (2025): CD-SAXS within-spot uniformity was studied against mass CD-SEM and 3D tomography to correlate the CD-SAXS signal with local variation. — [Jang et al., JM3 24(3) 034004, 2025](https://www.spiedigitallibrary.org/journals/journal-of-micro-nanopatterning-materials-and-metrology/volume-24/issue-3/034004/Study-of-critical-dimension-small-angle-X-ray-scattering-within/10.1117/1.JMM.24.3.034004.full)
- Tool-to-tool bias example: a 0.8 nm CD difference on 13 nm lines between CD-SAXS and model-based library SEM. — [Orji et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- IRDS: CD-SAXS is "the only technique currently viewed as having the capability to measure features less than 5 nm" for FinFET, nanowire and DSA. The limitation is source brightness. — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)

### Inferences
- "Must be correlated with CD-SEM to ensure accuracy" should be CORRECTED. CD-SAXS is a physics-based, SI-traceable method and is used as a reference to calibrate OCD. Its accuracy is typically verified against destructive references (FIB-SEM, TEM, 3D tomography). CD-SEM correlation is common for top CD and local-variation context, but it is not the accuracy anchor.
- Throughput ranking (typical): OCD ≳ IR-CD > CD-SEM (per site) > CD-SAXS (minutes per site) > 3D-AFM. CD-SAXS is chosen for accuracy, opaque stacks and tilt, not for sampling density.
- Note the energy discrepancy: "> 17 keV" (Orji) vs "15 keV" (SemiEngineering). Both are in the hard X-ray range needed to transmit about 0.7–0.8 mm of Si.

### Gaps
- No public per-site time or precision spec for KLA Axion or Bruker in-fab tools was found. "Minutes" is the best public statement.
- X-ray dose effects on devices or resist for CD-SAXS were not covered in the sources found. It is described as non-destructive throughout.

---

## Q5. Profile metrology (trench depth, SWA, recess, dishing/erosion): which techniques, which are inline

### Takeaway
The learner's tree lists no technique for profile. The answer is a family. **Inline, non-destructive:** OCD (standalone and integrated on etch/CMP), IR-CD (HAR), CD-SAXS (HAR memory), tilt-beam and high-kV BSE CD-SEM (top-down proxies for bottom CD, sidewall and height), and automated AFM / atomic force profilers (etch depth, dishing, erosion, step height). **Near-line:** stylus profilometers (dishing, erosion, step height on larger features). **Offline reference, destructive:** cross-section SEM, FIB-SEM and TEM. **Offline reference, non-destructive but slow:** CD-AFM / 3D-AFM.

### Cited Findings
- IRDS 2024: "Tilt beam CD-SEM, comparison of line scan intensity variation versus line scans from a golden wafer, scatterometry, CD-AFM, dual beam ... and triple beam ... have all been applied to line shape measurement. The sidewall angle has been proposed as the key process variable." — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- IRDS 2024: AFMs are "taking a larger share of action for inline metrology", offer 3D measurement insensitive to material, and multi-head, tiltable and multi-probe systems are filling throughput gaps. Dual-beam FIB is "now commonly used in-line" (locally destructive). — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- Bruker InSight AFP (atomic force profiler) is described as an inline CMP-profiling and etch-depth system measuring directly in the active area of dies, "without relying on test keys or models". It claims 260–340 sites/hr, up to 50 WPH, 0.3 nm long-term stability, and NIST-traceable results. DTMode etch depth has < 10 s MAM time. — [Bruker InSight AFP](https://www.bruker.com/en/products-and-solutions/semiconductor-solutions/automated-afm-and-cipt-systems/insight-afp.html)
- Bruker InSight 300 measures post-CMP dishing at 3σ = 0.14 nm and erosion at 3σ = 0.32 nm. DTMode handles trench and via depths from tens of nm to > 10 µm. — [Bruker InSight 300](https://www.bruker.com/en/products-and-solutions/semiconductor-solutions/automated-afm-and-cipt-systems/insight-300.html)
- Stylus profiler (Dektak XTL, 2014) is described as a cost-effective 300 mm solution for step height, CMP dishing, erosion and roll-off. *(Old.)* — [ASM International 2014](https://www.asminternational.org/bruker-stylus-profiler-enables-300-mm-wafer-analysis)
- SEMI AUX036 (2025) CMP metrology gap table lists AFM as *in line* for patterned-wafer dishing, erosion, step height and roughness, with a "gap" because of limited scan area. Optical interferometry is in line for thickness. — [SEMI AUX036-0825](https://www.semi.org/sites/semi.org/files/2025-09/AUX036-00-0825.pdf)
- Nova (SEMI 2021): scribe pads do not represent in-die dishing and erosion. The alternatives are "destructive (TEM) or slow (in-line AFM)". The solution was ML combining integrated-metrology OCD signal with AFM labels, for every-wafer in-die dishing and erosion. — [Nova, SEMI 2021](https://www.semi.org/sites/semi.org/files/2021-11/03%20Ovadia%20Ilgayev%20Nova.pdf)
- 3D-AFM / CD-AFM is a reference tool for CD calibration "because of high accuracy and atomic resolution without sample damage ... but it is very slow". In-line 3D-AFM (Park NX-3DM) measured fin CD, height and sidewall roughness, verified by TEM. — [ECS 2016](https://iopscience.iop.org/article/10.1149/MA2016-02/30/1950/meta)
- The NIST/SEMATECH CD-AFM Reference Measurement System achieved standard uncertainty (k = 1) of about 0.2% for pitch, 0.4% for step height, and 1 nm for linewidth (reduced from 5 nm using HRTEM-calibrated SCCDRM). *(2005, old.)* 3D-AFM uncertainty is < 1 nm for nanowire-type parameters. — [NIST 2005](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=32108); [Orji et al. 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/)
- Reference chain: calibrate 3D-AFM SWA against TEM or XS-SEM on a cross-sectioned subset, then use 3D-AFM-characterized wafers to evaluate faster inline tools. The ITRS 2016 uncertainty spec was 0.3° SWA, 0.5 nm fin height and 0.9 nm gate height. — [NIST 3D-AFM 2019](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=918090)
- IRDS: reference metrology (lab TEM, CD-AFM) "must have a precision that matches or exceeds in-line CD tools". Industry uses total measurement uncertainty (TMU) because precision on golden wafers misses bias variation. — [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- FIB-SEM and TEM serve as off-line accuracy verification for IR-CD and CD-SAXS in 3D NAND. — [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices)

### Inferences
- Suggested tree fix for the "Profile (Dry Etch, CMP)" node:
  - Dry etch: OCD (inline/integrated), IR-CD (HAR), CD-SAXS (HAR), tilt and BSE CD-SEM, AFM etch depth (inline). Reference: XS-SEM, FIB-SEM, TEM, CD-AFM.
  - CMP: integrated OCD or film tools (scribe pads plus ML in-die), AFP/AFM for dishing, erosion and step height (inline), stylus profiler (near-line, larger features). Reference: TEM or XS-SEM.
- "Inline" vs "integrated": OCD is the only family with widely deployed *integrated* (on-process-tool) versions. AFM, CD-SEM, IR-CD and CD-SAXS are in-line standalone.

### Gaps
- No public data on stylus-profilometer use at advanced nodes in 2026. Its role is likely limited to larger features and packaging, but this is unconfirmed.

---

## Q6. Claim-by-claim verdicts on the learner's notes

### Takeaway
Most notes are directionally right. Four need correction: CD-SEM "most non-destructive" (it is the least), OCD "not measured on wafer" (it is on-wafer but indirect, on periodic targets), CD-SAXS "must correlate with CD-SEM" (TEM/FIB-SEM are the accuracy anchors and CD-SAXS is itself a reference), and the empty Profile node.

### Cited Findings
| Node / claim | Verdict | Corrected statement / note | Source |
|---|---|---|---|
| CD-SEM precision 0.25 nm | CORRECTED (refine) | Repeatability is about 1% of CD (3σ); about 0.05–0.13 nm on EUV resist in 2023 (sigma not stated). Always state σ type. 0.25 nm matches old ITRS-era 3σ targets. | [Hitachi](https://www.hitachi-hightech.com/global/en/knowledge/semiconductor/room/manufacturing/accuracy-precision.html); [Hitachi 2023](https://euvlitho.com/2023/P73.pdf); [ITRS 2007](https://www.semiconductors.org/wp-content/uploads/2018/08/2007Metrology.pdf) |
| CD-SEM "can measure directly" | VERIFIED | Direct top-down imaging; no model is needed for top CD (model-based SEM is optional for 3D). | [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/) |
| CD-SEM "not integrated with process tool" | VERIFIED (with nuance) | It is in-line standalone, not integrated. Integrated metrology is optical. | [Hitachi CV7300](https://www.hitachi-hightech.com/global/en/products/semiconductor-manufacturing/cd-sem/metrology-solution/semi-cv7300.html); [Nova IM](https://www.novami.com/nova-product-category/integrated-metrology) |
| CD-SEM "most non-destructive" | CORRECTED | Practically non-destructive but the *least* so among CD tools: e-beam resist shrinkage, charging, contamination, and local electrical damage at high kV. OCD and IR-CD are optical with no known damage; CD-SAXS is described as non-destructive. | [Hitachi 2023](https://euvlitho.com/2023/P73.pdf); [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/); [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf) |
| SE = surface topography | VERIFIED | Low-kV SE through-lens detection is the standard CD imaging mode. | [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/) |
| BSE = underlying layers (overlay type) | VERIFIED (expand) | High-kV BSE images HAR trench and hole bottoms and buried overlay through insulator films (≤ 0.3 nm overlay repeatability, 2017). "Slant" measurements are a separate *tilt-beam* capability. | [Hitachi Review 2017](https://www.hitachihyoron.com/rev/archive/2017/r2017_04/eG02/index.html); [AMAT 2015](https://ir.appliedmaterials.com/news-releases/news-release-details/applied-materials-unveils-breakthrough-e-beam-metrology-tool) |
| OCD precision 0.05–0.12 nm | UNRESOLVED | Public sources say "angstrom-level repeatability" / sub-nm. No vendor-neutral source for the exact range was found. | [Onto 2023](https://ontoinnovation.com/wp-content/uploads/2025/08/The-road-to-SiC-process-control_CS-Mag_Oct23.pdf); [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/) |
| OCD better precision and faster than CD-SEM | VERIFIED for speed; precision is "typically comparable-to-better for array-averaged CD" | OCD averages thousands of features, so its precision on average CD is high. CD-SEM is still needed for local CDU and LER. | [halbleiter.org](https://www.halbleiter.org/en/metrology/cdsem); [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf) |
| OCD no contact, non-destructive | VERIFIED | — | [NIST 2011](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=908506); [Orji preprint](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=926234) |
| OCD "usually not directly measured on wafer" | CORRECTED | It is measured on the wafer, on periodic targets (scribe pads about 50 µm, or in-die arrays). It is *indirect* (model-based), not imaging. | [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf); [Nova 2025](https://www.novami.com/wp-content/uploads/2025/04/13426-33-stefan-schoeche-beol-dimensional-characterization-using-scatterometry-v3.pdf) |
| OCD multiple layers; solves CD, trench, SWA | VERIFIED | Ten or more parameters, including film thicknesses and n,k. | [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/) |
| OCD integration (not in notes) | ADD | OCD exists as integrated metrology on CMP, etch and litho track. | [Nova](https://www.novami.com/wp-content/uploads/2026/02/dmd-all.pdf); [ITRS 2009](https://www.semiconductors.org/wp-content/uploads/2018/09/Metrology.pdf) |
| IR-CD for high aspect ratio | VERIFIED | 3D NAND channel holes and slits up to about 80:1; mid-IR 5–10.5 µm. | [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices) |
| IR-CD non-contact | VERIFIED | Also non-destructive. | [Onto Aspect](https://ontoinnovation.com/products/aspect-system) |
| IR-CD slower than OCD | UNRESOLVED | Vendor claims HVM speed comparable to OCD. No public spec found. | [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices); [Onto 2020](https://investors.ontoinnovation.com/news/news-details/2020/Product-News-Onto-Innovation-Announces-First-Customer-Qualification-of-New-Aspect-IRCD-System/default.aspx) |
| IR-CD not integrated with tool | VERIFIED (no integrated product found) | It is in-line standalone. | [Onto Aspect](https://ontoinnovation.com/products/aspect-system) |
| Location: live die array or scribe test structure | VERIFIED | Both are used. The trend is toward in-die and on-device. | [Nova/IBM 2022](https://www.novami.com/wp-content/uploads/2023/04/120530s-vertical-travelling-scatterometry-for-metrology-on-fully-integrated-devices-ibm-nova-spie-2022.pdf); [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices) |
| CD-SAXS layer dependent | VERIFIED (clarify) | Signal depends on electron-density contrast and height², so it is strong for HAR memory and weak for thin logic layers. | [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf) |
| CD-SAXS non-destructive | VERIFIED | — | [KLA Axion](https://ir.kla.com/news-events/press-releases/detail/447/kla-launches-revolutionary-x-ray-metrology-system) |
| CD-SAXS not integrated with process tool | VERIFIED | It is in-line standalone (Axion T2000). | [KLA Axion](https://ir.kla.com/news-events/press-releases/detail/447/kla-launches-revolutionary-x-ray-metrology-system) |
| CD-SAXS measures CD, trench, SWA | VERIFIED (expand) | Also pitch and pitch walk, LER/LWR, and hole tilt / center-line shift. | [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/); [Gin 2023](https://doi.org/10.1117/1.JMM.22.3.031205) |
| CD-SAXS must correlate with CD-SEM for accuracy | CORRECTED | Accuracy is verified against FIB-SEM, TEM and tomography. CD-SAXS is SI-traceable and used to calibrate OCD. CD-SEM correlation is common practice, not the accuracy anchor. | [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices); [Jang 2025](https://www.spiedigitallibrary.org/journals/journal-of-micro-nanopatterning-materials-and-metrology/volume-24/issue-3/034004/Study-of-critical-dimension-small-angle-X-ray-scattering-within/10.1117/1.JMM.24.3.034004.full); [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/) |
| Profile: "OCD and CD-SAXS solve trench/SWA" | VERIFIED but incomplete | Add IR-CD, tilt and BSE CD-SEM, inline AFM/AFP, stylus profiler, and XS-SEM, FIB-SEM, TEM and CD-AFM references. | See Q5 |

### Inferences
- Teaching point: "in-line" (in the fab flow, on product wafers) ≠ "integrated" (physically inside a process tool) ≠ "in-situ" (during processing). The learner's notes conflate the first two.

### Gaps
- See the UNRESOLVED rows: the OCD numeric precision range and IR-CD relative speed.

---

## Q7. Relations between tools

### Takeaway
OCD is faster than CD-SEM and gives profile and buried information, but needs a model and a periodic target. CD-SEM gives local, direct, top-down CD and roughness. IR-CD extends OCD to deep dielectric HAR stacks at similar (claimed) speed. CD-SAXS is slower and costlier but more physically direct and opaque-capable, and serves as a reference or hybrid partner. Hybrid metrology (OCD + CD-SEM, AFM or SAXS) is the standard way to break OCD parameter correlations.

### Cited Findings
- OCD vs CD-SEM: OCD is non-scanning and fast but needs arrays. CD-SEM gives local and global info with sub-nm accuracy but suffers drift and beam damage. — [Orji preprint Table 1](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=926234)
- Hybrid: CD-SEM, AFM and CD-SAXS inputs constrain OCD fits. Combinations include CD-SAXS + SEM, SEM + OCD, and AFM + SEM. Typical OCD top-width improvement with AFM is up to 4 nm. — [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/); [IRDS 2024](https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MET.pdf)
- NIST Bayesian hybrid example (about 17 nm lines): SEM-only CD uncertainty was 0.44 nm. OCD-only uncertainties were 0.60 nm (CD), 0.72 nm (top), 1.33 nm (bottom) and 0.51 nm (height). Combining them reduced uncertainties to about 0.26–0.60 nm. — [NIST hybrid metrology 2014](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=915846)
- IR-CD vs OCD: OCD uses UV–NIR, where SiO2 and Si3N4 are transparent. IR-CD uses mid-IR absorption to sense deep profile and recess. It is "taking over where conventional OCD left off". — [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices)
- IR-CD vs CD-SAXS: CD-SAXS has higher CoO and longer measurement time (multiple angles). Vendors position IR-CD as faster than X-ray (vendor claim). — [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices); [Onto 2020](https://s24.q4cdn.com/480160064/files/doc_news/Product-News-Onto-Innovation-Announces-Suite-of-Three-New-Metrology-Systems-for-Complete-Critical-Dimension-Process-Control-2020.pdf)
- CD-SAXS vs CD-SEM: they measure different things (an array average of 3D shape vs local top-down edges). There is a 0.8 nm bias example on 13 nm lines. CD-SAXS has been compared against CD-SEM since at least 2008 and against mass CD-SEM in 2025. — [Orji 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC6605074/); [NIST 2008](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=853580); [Jang 2025](https://www.spiedigitallibrary.org/journals/journal-of-micro-nanopatterning-materials-and-metrology/volume-24/issue-3/034004/Study-of-critical-dimension-small-angle-X-ray-scattering-within/10.1117/1.JMM.24.3.034004.full)
- Typical process steps: CD-SEM is used at litho ADI and etch AEI. OCD is used after etch, CMP and other steps (SpectraShape), with integrated versions on CMP and etch. IR-CD is used at 3D NAND channel-hole etch, hardmask etch and W recess. CD-SAXS is used at 3D NAND and DRAM HAR etch, including post-PM etch qualification. AFP is used for CMP dishing, erosion and etch depth. — [AMAT](https://ir.appliedmaterials.com/node/26166/pdf); [KLA 2017](https://www.edn.com/kla-tencor-introduces-new-metrology-systems-for-leading-edge-integrated-circuit-device-technologies); [SemiEngineering 2023](https://semiengineering.com/how-metrology-tools-stack-up-in-3d-nand-devices); [Axion fact sheet](https://pdf.directindustry.com/pdf/kla-corporation/axion-t2000/113449-1041363.html); [Bruker AFP](https://www.bruker.com/en/products-and-solutions/semiconductor-solutions/automated-afm-and-cipt-systems/insight-afp.html)

### Inferences
- Simple chooser for training:
  - Periodic array, need speed or profile → OCD.
  - Deep dielectric HAR → IR-CD.
  - Opaque, very small, tilt, or accuracy anchor → CD-SAXS.
  - Local CD, LER, OPC or contours, non-periodic features → CD-SEM.
  - Depth, dishing or erosion without a model → AFM/AFP.
  - Final truth → XS-SEM, FIB-SEM or TEM, with CD-AFM for non-destructive reference.

### Gaps
- No vendor-neutral, same-structure benchmark comparing throughput and precision of all four techniques side by side was found.
