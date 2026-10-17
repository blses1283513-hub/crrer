# Optical Thin-Film Metrology (Reflectometry, Ellipsometry, GOF, n & k, Reflectance after PVD)

Scope: verify and expand the learner's metrology-tree nodes for spectroscopic reflectometry (SR), spectroscopic ellipsometry (SE), the GOF KPI, the optical constants n and k, and reflectance/reflectivity on PVD metal films. Each learner claim is tagged VERIFIED / CORRECTED / UNRESOLVED. Numbers are typical published or vendor values, and they depend on the tool, the film stack and the recipe. Research date: Oct 2026.

### Claim verdict summary (quick reference for the report writer)

| # | Learner claim | Verdict | Corrected / qualified statement |
|---|---|---|---|
| 1 | Reflectometry principle = interference of incident + reflected light | CORRECTED (wording) | The interference is between light reflected from the top surface and light reflected from each lower interface (film/substrate), not between the incident and reflected beams. The measured quantity is reflected intensity divided by incident intensity, as a function of wavelength. |
| 2 | Reflectometry: film thickness > 1000 Å | CORRECTED | Thickness-only SR works from about 1–15 nm (UV/visible tools) up to tens or hundreds of µm. About 500–2000 Å is the typical minimum only when n and k must also be fitted. "> 1000 Å" is a rule of thumb for where SR is strongest (it also matches a 2026 metrology-institute comparison). It is not a hard limit. |
| 3 | Reflectometry: beam size ≥ 40 µm | UNRESOLVED / tool-specific | Spot sizes range from a few µm (microspot) through 25–50 µm (production small-spot tools) to 0.5 mm–1 cm (benchtop). 40 µm is plausible for one fab tool, but it is not a property of the technique. |
| 4 | Ellipsometry measures films < 1000 Å | CORRECTED | SE measures from sub-nm to a few µm (up to tens of µm in the IR). It is the preferred method below ~100 nm and especially below ~10 nm, but it is not limited to thin films. |
| 5 | Ellipsometry beam ~45 µm | UNRESOLVED / tool-specific | Production SE spots are typically 25–50 µm. Oblique incidence stretches the spot into an ellipse (for example a 1 mm beam becomes 1 × 3 mm at 70°). |
| 6 | Ellipsometry uses polarization to get thickness and refractive index | VERIFIED | It also gives k, roughness and composition through a model. For films under ~10 nm, t and n are correlated, so n is usually fixed. |
| 7 | Stacked structures can be measured (by SE) | VERIFIED, but not unique to SE | SR can also measure multilayer stacks. |
| 8 | GOF < 0.9 not acceptable, GOF > 0.95 acceptable | CORRECTED → recipe-specific | No universal threshold exists. The GOF scale and its limits depend on vendor and recipe, and a high GOF does not prove accuracy. |
| 9 | "2000 Å oxide ~ 1000 Å oxide?" | UNRESOLVED | Most likely refers to fit ambiguity, where a local minimum gives a wrong thickness that still fits reasonably. See Q3. |
| 10 | n = refractive index, k = extinction coefficient = absorption through film | VERIFIED (refine) | α = 4πk/λ, and intensity decays as I = I₀·exp(−αz). |
| 11 | n, k measured by ellipsometry | VERIFIED, not exclusive | Reflectometry can also fit n and k when the film is thick enough (≥ ~50 nm). |
| 12 | Diffusion/CVD films are transparent | CORRECTED (partly) | SiO₂ and Si₃N₄ are transparent over most of the visible band. Poly-Si/a-Si, TiN and metals absorb. Transparency depends on the wavelength band. |
| 13 | Reflectance = E_ref / E_in | CORRECTED | Reflectance = reflected power (intensity) / incident power, which equals \|r\|², where r = E_ref/E_in is the field-amplitude reflection coefficient. |
| 14 | Reflectivity tells roughness: 0.8 smooth, 0.5 rough | CORRECTED → relative/tool-specific | Reflectance falls with rms roughness σ roughly as exp[−(4πσ/λ)²]. It also depends on the metal, wavelength, grain size, oxide/contamination and thickness. 0.8 and 0.5 are at best local recipe limits. |

---

## Q1. Thickness ranges of SR vs SE: is ">1000 Å reflectometry / <1000 Å ellipsometry" fair? What decides which to use?

### Takeaway
Both techniques cover overlapping ranges from about 1 nm to many µm. The 1000 Å split is an oversimplification but a usable rule of thumb. SE has clearly lower uncertainty and much higher sensitivity for thin films (below ~100–500 nm, and especially below 10 nm). SR's many interference fringes make it strong for thick films (> ~1000 nm). The choice depends on thickness, whether n and k must be fitted, stack complexity, spot and throughput needs, and t–n correlation in ultra-thin films.

### Cited Findings
**Technique ranges (typical)**
- J.A. Woollam: "Ellipsometry is typically used for films whose thickness ranges from sub-nanometers to a few microns". Above several tens of µm, thickness non-uniformity and depolarisation become limits. — [J.A. Woollam, Thin Film Thickness](https://www.jawoollam.com/resources/ellipsometry-tutorial/thin-film-thickness); [Woollam tutorial PDF](https://www.chem.purdue.edu/ric/docs/Gaertner-Ellipsometer-Handout-2---JAWoollamCo-Ellipsometry-Tutorial.pdf)
- Woollam tutorial Fig. 12: for three thin oxides on Si, ellipsometric Delta is highly sensitive to nm-scale films, while the reflected intensity barely changes. — [Woollam tutorial PDF](https://www.chem.purdue.edu/ric/docs/Gaertner-Ellipsometer-Handout-2---JAWoollamCo-Ellipsometry-Tutorial.pdf)
- KLA Filmetrics F20 reflectometer family: thickness range depends on wavelength band ("film stack dependent"):
  - F20 (380–1050 nm): 15 nm – 70 µm
  - F20-UV (190–1100 nm): 1 nm – 40 µm
  - F20-UVX (190–1700 nm): 1 nm – 250 µm
  - F20-NIR: 100 nm – 250 µm
  - F3-sX: 10 µm – 3 mm
  
  — [KLA Filmetrics F20](http://kla.com/products/instruments/thin-film-reflectometers/filmetrics-f20)
- Filmetrics, "Taking the mystery out of thin-film measurement": the minimum single-film thickness measurable by spectral reflectance is 10–300 Å, depending on film and wavelength range. If optical constants are also measured, the minimum rises to 500–2000 Å "unless minimal parameterization models can be used". — [Filmetrics technote](https://sites.science.oregonstate.edu/~tatej/TateLabWiki/lib/exe/fetch.php?media=opticalspectrometers%3Afilmetrix_ref_technote.pdf)
- Older F20 datasheet:
  - Thickness only: F20-UV 30 Å–20 µm; F20 150 Å–50 µm; F20-NIR 1000 Å–250 µm
  - Thickness with n & k: 500 Å–5 µm (UV); 1000 Å–5 µm (visible); 3000 Å–10 µm (NIR)
  
  — [F20 datasheet (Univ. Arizona copy)](https://cores.arizona.edu/sites/default/files/attachments-service/f20_application_sheet.pdf)
- University facilities list the F20-UVX as 1 nm–250 µm thickness with a "minimum thickness to measure n and k is 50 nm" and a 1.5 mm spot. — [GMU Nanofab](https://nff.gmu.edu/filmetrics-f20-uvx-thin-film-measurement-system); [AMOLF](https://amolf.nl/thin-film-analyzer-filmetrics-f20-uvx)
- F20 manual troubleshooting: no oscillations appear in the reflectance spectrum when the film is very thin (<200 Å). For very thin films, fitting many properties gives "several different answers". — [Filmetrics F20 manual](http://sites.science.oregonstate.edu/~tatej/TateLabWiki/lib/exe/fetch.php?media=manuals%3Afilmetrics_f20_manual.pdf)
- Tencor patent (single-wavelength reflectance): at 400 nm, reflectance of SiO₂ on Si changes only ~0.005 per 100 Å for the first 100 Å of oxide, and ~0.06/100 Å at 200–400 Å. At 253.6 nm the change is ~0.05/100 Å, so shorter (UV) wavelengths raise thin-film sensitivity. — [US 4,899,055 (Tencor)](https://patents.justia.com/patent/4899055)
- Bruker (vendor of both techniques): "Ellipsometry excels at the measurement of very thin films. Reflectometry is better suited to measure thicker films." Bruker states SE can resolve layers "down to less than one angstrom". — [Bruker ellipsometry tutorial](https://www.bruker.com/de/products-and-solutions/test-and-measurement/ellipsometers-and-reflectometers/what-is-ellipsometry.html)
- Bruker production tool ranges:
  - FilmTek 6000 PAR-SE (combined SE + multi-angle reflectometry): 0 Å – 150 µm, 190–1700 nm, 50 µm spot (25 µm microspot)
  - Reflectometer-only FilmTek models: 5 nm – 350 µm or 5 nm – 2000 µm
  
  — [Bruker Ellipsometry & Reflectometry Systems](https://www.bruker.com/en/products-and-solutions/test-and-measurement/ellipsometers-and-reflectometers.html?campaign=FilmTek%20Google%20Ads%202025&content&device=c&keyword=reflectometer&medium=cpc_search_FilmTek&s_kwcid=AL!14677!3!651195485235!e!!g!!reflectometer&source=146801103493)
- NBS (now NIST) 1963: the lower thickness limit for ellipsometry is "at least an order of magnitude smaller" than for interferometry, and "only ellipsometry will give the index of refraction of films of unknown thickness". — [McCrackin et al., J. Res. NBS 67A (1963)](https://nvlpubs.nist.gov/nistpubs/jres/067/4/v67.n04.a12.pdf)

**Head-to-head metrology-institute comparison (2026)**
- Rastgou et al., *Metrologia* (2026): compared SE (192–1000 nm) and SR (370–830 nm) on SiO₂/Si and Al₂O₃/Si from 10 nm to 2000 nm. The two agree within uncertainty across the whole range. "Ellipsometry provides measurements with smaller uncertainties for layer thicknesses below 500 nm, while reflectometry uncertainties are smaller with thicker layers", because stronger oscillations in thick-film reflectance carry more information. "Reflectometry demonstrates its strengths… for films thicker than 1000 nm". — [Rastgou et al., Metrologia 2026](https://iopscience.iop.org/article/10.1088/1681-7575/ae3964)
- Same study, expanded uncertainties (U, nm):

  | Nominal film | SE value ± U | SR value ± U |
  |---|---|---|
  | 10 nm SiO₂ | 9.7 ± 1.7 | 11.3 ± 3.2 |
  | 103 nm | 104.0 ± 1.9 | 102.6 ± 3.2 |
  | 512 nm | 515.4 ± 3.5 | 515.3 ± 6.0 |
  | 1000 nm | 1007.2 ± 8.8 | 1003.6 ± 6.8 |
  | 2000 nm | 2011.8 ± 17.1 | 2006.0 ± 8.0 |

  For thick layers, SE uncertainty was dominated by model-related factors. — [Rastgou et al., Metrologia 2026](https://iopscience.iop.org/article/10.1088/1681-7575/ae3964)

**Thickness–index correlation in ultra-thin films (a key selection factor)**
- "It is difficult, and often considered impossible, to determine both thickness and refractive index from ultra-thin films where the thickness is less than about 10 nm… due to strong correlation between the thickness (d) and index". — [Hilfiker et al. (Woollam/OSTI), 2018](https://www.osti.gov/servlets/purl/1438647)
- HORIBA: for ultra-thin layers "a strong correlation exists between film thickness and optical constants". The chosen n strongly influences the thickness result and can make it inaccurate. — [HORIBA AN SE28](https://www.horiba.com/fileadmin/uploads/Scientific/Documents/TFilm/AN_SE28.pdf)
- NBS 1963: when n is known, thickness can be determined accurately even for very thin films. Index is determined less accurately as the film gets thinner. — [McCrackin et al. 1963](https://nvlpubs.nist.gov/nistpubs/jres/67a/jresv67an4p363_a1b.pdf)
- Unambiguous simultaneous (n, k, d) determination is "typically confined for films with a thickness of more than 10 nm". Special methods (anisotropic substrates, immersion ellipsometry) can break the correlation. — [arXiv 2502.21241](https://arxiv.org/html/2502.21241v1); [JVSTA 2024 immersion ellipsometry](https://pubs.aip.org/avs/jva/article/42/5/053401/3304588/Immersion-ellipsometry-for-the-uncorrelated)
- Bruker markets combined SE + multi-angle reflectometry because "combining reflectometry and ellipsometry removes ambiguity that single techniques cannot". — [Bruker knowledge pack](https://www.bruker.com/de/products-and-solutions/test-and-measurement/ellipsometers-and-reflectometers/resource-library/knowledge-pack-thin-films-characterization.html)

### Inferences
- A fair training statement: "Use SE when films are thin (≲100 nm, and certainly ≲10 nm), when n and k must be found, or when the stack is complex or multilayer. Use SR (normal incidence, faster, simpler, often smaller spot) for thicker transparent films and high-throughput or integrated monitoring. The ~1000 Å boundary is a fab convention, not a physical limit." Several fab tools (KLA, Onto, Bruker) combine SE and normal-incidence reflectometry in one head.
- The learner's thresholds probably came from a specific fab's recipe allocation. Teach them as "typical local practice".
- For ultra-thin films (gate oxide, high-k, native oxide), production recipes normally fix n (or the dispersion model) and float only thickness. This is the practical answer to t–n correlation.

### Gaps
- No public KLA SpectraFilm/Aleris specification sheet with thickness range or spot size was found. Leading-edge fab tool specifications are mostly not public.

---

## Q2. Spot sizes, precision, throughput; integrated vs standalone metrology

### Takeaway
Production small-spot film tools typically use 25–50 µm spots, so they can measure in ~50 µm scribe-line pads. Benchtop reflectometers use spots of mm size. Leading production SE quotes sub-0.1 Å (1σ) repeatability on thin oxide and about 1 s per site. Integrated metrology (Nova i500/i570, Onto IMPULSE) sits inside CMP/etch tools for wafer-to-wafer APC at polisher throughput (≳100 wph).

### Cited Findings
- Bruker FilmTek 2000 PAR-SE production specifications:
  - Spot size 25–50 µm (normal incidence and 70°); range 0 Å–150 µm
  - Thickness accuracy ±1.0 Å on NIST-traceable oxide 100 Å–1 µm
  - Precision (1σ): oxide/Si 0–1000 Å t = 0.03 Å; 1000 Å t,n = 0.2 Å / 0.0001; nitride/Si 200–10,000 Å t = 0.02%
  - Measurement time <1 s per site
  
  — [Bruker FilmTek 2000 PAR-SE](https://www.bruker.com/de/products-and-solutions/test-and-measurement/ellipsometers-and-reflectometers/filmtek-2000-par-se.html)
- FilmTek 2000 PAR-SE Robotic: "<2 s per site", 0.03 Å (1σ) for 0–1000 Å oxide. Applications include ONO stacks, high-k/low-k, poly/a-Si and SiGe (including %Ge composition). — [Bruker Robotic](https://www.bruker.com/en/products-and-solutions/test-and-measurement/ellipsometers-and-reflectometers/filmtek-2000-par-se-robotic.html)
- FilmTek 6000 PAR-SE: 50 µm spot standard, 25 µm microspot available. — [Bruker systems page](https://www.bruker.com/en/products-and-solutions/test-and-measurement/ellipsometers-and-reflectometers.html?campaign=FilmTek%20Google%20Ads%202025&content&device=c&keyword=reflectometer&medium=cpc_search_FilmTek&s_kwcid=AL!14677!3!651195485235!e!!g!!reflectometer&source=146801103493)
- Benchtop reflectometers use much larger spots: F20 adjustable 500 µm to 1 cm; facility F20s ~1.5 mm. — [F20 datasheet](https://cores.arizona.edu/sites/default/files/attachments-service/f20_application_sheet.pdf); [ASU F20 SOP](https://cores.research.asu.edu/wp-content/uploads/2026/06/F20-Filmetrics-SOP_REV-D.pdf)
- F20 precision 1–2 Å (1σ of 100 readings on 500 nm SiO₂ over 20 days); accuracy the greater of 0.4% or 10 Å. — [F20 datasheet](https://cores.arizona.edu/sites/default/files/attachments-service/f20_application_sheet.pdf)
- Oblique-incidence spot elongation: a single-wavelength ellipsometer with a 1 mm beam gives a "1 × 3 mm on wafer @ 70°" spot. — [UIC Gaertner L116S300](https://rrc.uic.edu/wp-content/uploads/sites/112/2020/02/Gaertner_Ellipsometer.pdf)
- SE repeatability at a national-lab level: 0.01 nm standard deviation on PTB SiO₂ standards (0.02 nm on a 5.7 nm standard). — [Rastgou et al., Metrologia 2026](https://iopscience.iop.org/article/10.1088/1681-7575/ae3964)
- Requirement context (NIST, ITRS-era): gate-dielectric process tolerance was projected at ±4% (3σ), "less than 0.1 nm for 2 nm films", with measurement requirements "a factor of ten smaller still". — [NIST NSTI-Nanotech 2004](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=31539)
- NIST 1999: the knowledge base to control complex gate-dielectric thickness by in-line ellipsometry "at the 0.1 Å level" was not yet in hand. Fabs were moving to SE for high-k and complex dielectrics. — [NIST IR 5851 (1999)](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nistir5851r1999.pdf); [NIST conference report 1998](https://nvlpubs.nist.gov/nistpubs/jres/103/4/j34ce-bel.pdf)
- KLA SpectraFilm LD10 (2015): laser-driven plasma light source for high-precision thin multilayer stacks (FinFET), and an IR subsystem for thick 3D NAND stacks. KLA claims a "significant increase in throughput" over the previous Aleris platform. — [KLA press release 2015](https://ir.kla.com/news-events/press-releases/detail/144/kla-tencor-extends-its-5d-patterning-control-solution)
- Onto Atlas V: dual-channel optics with DUV 4×4 Mueller-matrix SE plus DUV polarized normal-incidence reflectometer, for OCD and thin film. Atlas G6 (2025) adds a "smaller optical spot size" for direct on-device DRAM-cell measurement. — [Onto Atlas V](https://ontoinnovation.com/products/atlas-v-system/); [Onto Atlas G6 PR 2025](https://www.businesswire.com/news/home/20250909090035/en/Onto-Innovation-Launches-Next-Generation-OCD-Metrology-Platform-to-Enable-Process-Control-for-Advanced-AI-Devices)
- Integrated metrology (IM):
  - Nova i500 "sets industry standard for CMP process control with thousands of deployments" and is "compatible with all CMP polishers".
  - Its throughput is aimed at polishers "planned to exceed throughputs of around 100 wafers per hour".
  - Onto IMPULSE+ is an integrated/standalone film metrology system for CMP APC feedback.
  - Onto describes feed-forward from standalone film/OCD tools to IM.
  
  — [Nova i500](https://www.novami.com/nova-product/nova-i500); [Nova 6-K 2011](https://www.sec.gov/Archives/edgar/data/1109345/000114420411039444/v228056_6k.htm); [Onto IMPULSE+](https://ontoinnovation.com/products/impulse/); [Onto solutions](https://ontoinnovation.com/solutions)
- Nova (SEMICON Europa 2021): scribe-line based residue control can be insufficient because pattern density differs between scribe and in-die. IM is moving to in-die measurement for wafer-to-wafer control. — [Nova, Innovations in Integrated Metrology](https://www.semi.org/sites/semi.org/files/2021-11/03%20Ovadia%20Ilgayev%20Nova.pdf)
- Nova's IM tools use normal-incidence spectral reflectometry (patented NI-SR). — [Nova 6-K 2008](https://www.sec.gov/Archives/edgar/data/1109345/000117891308001861/zk85542.htm)

### Inferences
- The learner's 40 µm / 45 µm beam sizes are consistent with typical 25–50 µm production small-spot heads. Teach them as "our tool's spot", not as a law. The measurement pad must be larger than the spot plus stage/pattern-recognition error, which is why pads of about 50 × 50 µm or larger are common.
- Standalone tools give more channels (SE + SR, DUV–IR), more sites and a reference/model-development role. IM gives every-wafer feedback and feed-forward (APC) with less data per wafer.

### Gaps
- No public datasheet found for KLA SpectraFilm/Aleris or Onto IMPULSE spot size, precision or throughput. Nova i500 public pages give no spot size.
- No public source found giving standard scribe-line pad dimensions (the commonly cited "50 × 50 µm box" remains unsourced here).

---

## Q3. GOF: definition, thresholds, meaning of low GOF, relation to χ²/MSE, and why a good GOF ≠ accuracy

### Takeaway
"GOF" is a vendor-specific fit-quality number. On many reflectometer and production tools it is scaled 0–1 (or 0–100%), with 1 meaning a perfect match between measured and modeled spectra. SE software from Woollam and others usually reports MSE or χ² instead, where lower is better and no 0–1 scale exists. The 0.9/0.95 thresholds are not universal; they are recipe and fab spec limits. A low GOF flags a wrong model or bad data. A high GOF does not guarantee accuracy, because of correlated or fixed parameters, local minima and wrong fixed n&k.

### Cited Findings
- General definition: "Typically, a parameter known as goodness of fit (GOF) indicates how well the simulation matches the measurement (0–100 %)." — [halbleiter.org, Metrology](https://www.halbleiter.org/en/metrology/metrology)
- Patent (OCD/scatterometry): GOF "is a measure of deviation between the measured spectrum and its theoretical prediction" and is used "to ensure the quality of the obtained CD data". The patent tunes n/k of a BARC film to improve the fit, showing that wrong n&k degrades GOF. — [US 7,580,129](https://patents.justia.com/patent/7580129)
- Filmetrics: example output "SiO₂ = 172.63 nm, Goodness of fit = 0.99996" (good fits on a simple oxide approach 1). — [Umeå F10-RT-UVX instructions](https://webbarkiv.umu.se/2024-09-29_00-30/contentassets/9f8c0a0dda844a09b42336a77868b84e/filmetrics-f10-rt-uvx.pdf)
- Filmetrics FILMeasure (older manual): fit quality was given as a "Fitting Error", "a normalized average RMS difference between the measured and calculated spectra". A good thickness + n,k measurement is "in the neighborhood of 0.01 or less". Default convergence criterion is 0.005. "The actual value… is quite dependent upon the type of measurement being made." — [Filmetrics F20 manual](http://sites.science.oregonstate.edu/~tatej/TateLabWiki/lib/exe/fetch.php?media=manuals%3Afilmetrics_f20_manual.pdf)
- Facility SOPs instruct users to select or deselect fit parameters (D, n, k, roughness) "to improve the Goodness of Fit (GOF) value". Filmetrics F50 can map GOF across the wafer. — [ASU F20 SOP](https://cores.research.asu.edu/wp-content/uploads/2026/06/F20-Filmetrics-SOP_REV-D.pdf); [UCSB F50 SOP](https://wiki.nanofab.ucsb.edu/wiki/Filmetrics_F50_-_Operating_Procedure)
- Ellipsometry fit metric: "An estimator, like the Mean Squared Error (MSE), is used to quantify the difference between curves. The unknown parameters are allowed to vary until the minimum MSE is reached." — [J.A. Woollam, Data Analysis](https://www.jawoollam.com/resources/ellipsometry-tutorial/ellipsometry-data-analysis)
- Woollam-style MSE formula: MSE = sqrt[1/(p−q) Σ((Ψexp−Ψcal)² + (Δexp−Δcal)²)] × 1000, where p = number of data points and q = number of fit parameters. One paper calls "MSE below 20" typically required. A university SOP says "MSE < 4 for really good fits". So the thresholds differ even for the same metric. — [arXiv 2412.05618](https://arxiv.org/pdf/2412.05618); [TU Graz M-2000 SOP](http://lampz.tugraz.at/~hadley/semi/ch9/instruments/ellipsometer/ellipsometer.php)
- Local minima: the MSE-versus-thickness curve for a transparent film on Si has multiple local minima. The global minimum was 749 nm; a local minimum near 0.45 µm is a wrong answer the regression can fall into, depending on the starting thickness. — [Woollam Data Analysis](https://www.jawoollam.com/resources/ellipsometry-tutorial/ellipsometry-data-analysis)
- Filmetrics: FILMeasure searches for the best thickness within about 1000 Å of the initial guess. If the initial guess is far off, a thickness-constrained search cannot find the right answer ("Case #2: maxima and minima do not match"). Grid/Fourier search finds the right fringe order. The n,k solve is correct only if the initial thickness is "within about ½ wavelength". — [Filmetrics F20 manual](http://sites.science.oregonstate.edu/~tatej/TateLabWiki/lib/exe/fetch.php?media=manuals%3Afilmetrics_f20_manual.pdf)
- Causes of poor fit, per Filmetrics:
  1. Layers missing from the model
  2. Very inaccurate initial thickness guesses
  3. Optical constants far from the real ones
  4. Film properties not modeled (roughness, non-uniformity, graded interface, which also kill interference)
  5. For thick films, an index mismatch makes calculated and measured fringes "walk off"
  
  — [Filmetrics F20 manual](http://sites.science.oregonstate.edu/~tatej/TateLabWiki/lib/exe/fetch.php?media=manuals%3Afilmetrics_f20_manual.pdf)
- Good fit but wrong answer: "Several different answers, or one unreasonable answer, are found when measuring thickness and optical constants, although a good match is found between the measured and calculated reflectance spectra. This normally occurs when a large number of properties are being measured on a very thin film." — [Filmetrics F20 manual](http://sites.science.oregonstate.edu/~tatej/TateLabWiki/lib/exe/fetch.php?media=manuals%3Afilmetrics_f20_manual.pdf)
- Parameter correlation means variation in d or n "leads to very similar changes in the measured ellipsometric parameters". Fits report 90% confidence limits on each parameter; for example, a 5.30 ± 0.03 nm thickness with an index of 1.47638 ± 0.0002. — [Hilfiker et al. 2018](https://www.osti.gov/servlets/purl/1438647)
- Woollam: "Thickness measurements are not independent of the optical constants". Both affect the phase delay. — [Woollam tutorial PDF](https://www.chem.purdue.edu/ric/docs/Gaertner-Ellipsometer-Handout-2---JAWoollamCo-Ellipsometry-Tutorial.pdf)
- Accuracy needs the right model, the instrument and the sample considered together. Woollam (NIST workshop) emphasised "selection of material structure model and goodness-of-fit criteria". — [NIST conference report 1998](https://nvlpubs.nist.gov/nistpubs/jres/103/4/j34ce-bel.pdf)
- Model accuracy can dominate uncertainty. For thick SiO₂, SE combined uncertainty "notably exceeds" the reference-standard uncertainty because of "model-related factors". — [Rastgou et al., Metrologia 2026](https://iopscience.iop.org/article/10.1088/1681-7575/ae3964)

### Inferences
- Verdict on 0.9/0.95: CORRECTED. These are plausible local recipe limits on a 0–1 scale tool. Typical simple oxide-on-Si fits on Filmetrics-type tools reach 0.999+, so 0.95 can be lenient for simple films and strict for complex patterned stacks. Fabs set GOF limits per recipe and layer, usually from baseline data (for example, a lower limit below the normal GOF distribution of good wafers). Teach: "GOF threshold = recipe spec; compare against that recipe's baseline GOF, never a universal number."
- GOF scales differ by vendor. Some 0–1 GOFs behave like R² (1 − residual/total variance); others are 1 − normalized χ² or a proprietary normalisation. GOF values from different tool types are therefore not comparable. For SE, χ²/MSE is the usual metric, and lower is better.
- Interpretation of "2000 Å oxide ~ 1000 Å oxide?" (UNRESOLVED; most likely meaning): the fit can converge to a wrong local minimum or fringe order, giving a thickness far from the truth with a mediocre-to-decent GOF. Another possibility is a too-narrow thickness search window around a wrong initial guess. Filmetrics documents a default search within ~1000 Å of the initial guess, which would match a 1000 Å vs 2000 Å confusion. The key point: always check that the result is physically reasonable (process target, neighbouring sites, trend), not just the GOF. A second possible meaning: the GOF on a 1000 Å vs 2000 Å oxide recipe naturally differs, so one threshold cannot fit all recipes.
- Low-GOF checklist for trainees:
  - Wrong or missing layer (native oxide, interfacial layer, residue)
  - Wrong fixed n&k or dispersion model
  - Roughness or graded interface
  - Non-uniformity or thickness gradient within the spot
  - Spot on pattern or edge (pad misalignment, pattern recognition failure)
  - Backside reflection on transparent substrates
  - Contamination or wet wafer
  - Lamp/baseline/reference problems (Filmetrics SOP: re-do the baseline if GOF drops on a known sample)
- High-GOF-but-wrong traps: correlated t & n in ultra-thin films; parameters fixed at wrong values (the fit compensates by shifting thickness); local minimum. Always check the parameter confidence limits and the correlation matrix where the software provides them.

### Gaps
- No public vendor document found that gives the exact GOF formula for KLA (SpectraFilm/Aleris), Onto (Atlas/IMPULSE) or Nova. These are proprietary.
- No public source found stating "GOF > 0.95 acceptable / < 0.9 reject" as an industry standard. No SEMI standard defining GOF was found.

---

## Q4. n and k: definitions, α = 4πk/λ, dispersion models, transparent vs absorbing films

### Takeaway
Complex refractive index Ñ = n + ik (HORIBA writes N = n − ik; the sign convention varies). n sets phase velocity (c/v), and k sets absorption: α = 4πk/λ, I(z) = I₀e^(−αz). n and k depend on wavelength, are Kramers–Kronig linked, and are described by dispersion models with few parameters: Cauchy/Sellmeier for transparent ranges, and Lorentz / Tauc–Lorentz / Cody–Lorentz / Forouhi–Bloomer for absorbing or amorphous films. Whether a film counts as "transparent" depends on the wavelength band measured.

### Cited Findings
- HORIBA: n is the ratio of the speed of light in vacuum to that in the material. k "is related to the absorption loss". Together they form the complex index N = n − ik. — [HORIBA SE basics](https://www.horiba.com/usa/scientific/technologies/spectroscopic-ellipsometry/spectroscopic-ellipsometry/)
- Woollam: k "describes the loss of wave energy to the material" and relates to the absorption coefficient α (α = 4πk/λ). Light loses intensity per Beer's law, so "the extinction coefficient relates how quickly light vanishes in a material." — [Woollam, Light and Materials](https://www.jawoollam.com/resources/ellipsometry-tutorial/light-and-materials)
- Woollam: absorption (k > 0) occurs in the UV from electronic transitions, and in the IR from molecular or phonon vibration or free carriers. n and k shapes "are mathematically coupled through Kramers-Kronig consistency." — [Woollam, Light and Materials](https://www.jawoollam.com/resources/ellipsometry-tutorial/light-and-materials)
- Woollam: Cauchy (A + B/λ² + C/λ⁴) is used for transparent materials but "is not constrained by KK consistency and can produce unphysical dispersion". Sellmeier enforces KK consistency. Absorbing regions use oscillator models (Lorentz, Harmonic, Gaussian). Tauc–Lorentz and Cody–Lorentz add a bandgap term. — [Woollam, Optical Constants](https://www.jawoollam.com/resources/ellipsometry-tutorial/optical-constants)
- HORIBA: "Cauchy Transparent" works best for materials with no absorption in the visible (normal dispersion, n decreasing with λ). "Cauchy Absorbing" adds a k expression for weakly absorbing materials. — [HORIBA Cauchy technote](https://www.horiba.com/fileadmin/uploads/Scientific/Downloads/OpticalSchool_CN/TN/ellipsometer/Cauchy_and_related_empirical_dispersion_Formulae_for_Transparent_Materials.pdf); [HORIBA Cauchy page](https://www.horiba.com/usa/scientific/technologies/spectroscopic-ellipsometry/cauchy-dispersion-module)
- Tauc–Lorentz (Jellison & Modine) and Cody–Lorentz (Ferlauto) are the standard parameterisations for amorphous materials, combining a Lorentz oscillator with a Tauc or Cody band edge (Eg). — [ScienceDirect TSF 2015](https://www.sciencedirect.com/science/article/abs/pii/S0040609015007014)
- Forouhi–Bloomer n(E), k(E) for amorphous and crystalline materials have five physically meaningful parameters including Eg. Cauchy and Sellmeier "are only useful for non-absorbing films where k = 0". — [Wikipedia: n and k of thin film materials](https://en.wikipedia.org/wiki/Refractive_index_and_extinction_coefficient_of_thin_film_materials)
- Dispersion models reduce the number of free parameters compared with fitting n,k at every wavelength. — [Woollam tutorial PDF](https://www.chem.purdue.edu/ric/docs/Gaertner-Ellipsometer-Handout-2---JAWoollamCo-Ellipsometry-Tutorial.pdf)
- Example values: SiO₂ n falls from ~1.57 in the UV to ~1.47 at 1000 nm (thermal oxide). Fitted SiO₂ n differed from the Herzinger literature values by only 1 × 10⁻⁵, so reflectometry can use literature n for thermal oxide. — [Rastgou et al., Metrologia 2026](https://iopscience.iop.org/article/10.1088/1681-7575/ae3964)
- Reflectometers also fit n and k. Filmetrics: oscillation amplitude is set by n and k of film and substrate. Thickness can be fit alone if n,k are given, but "n and k can not be measured without also measuring thickness" unless thickness is very well known. — [Filmetrics F20 manual](http://sites.science.oregonstate.edu/~tatej/TateLabWiki/lib/exe/fetch.php?media=manuals%3Afilmetrics_f20_manual.pdf)
- Filmetrics F20-UVX on facility sites: commonly analysed films include "oxides, nitrides, resist, poly silicon"; films must be "optically smooth". — [AMOLF](https://amolf.nl/thin-film-analyzer-filmetrics-f20-uvx)
- Ellipsometry has been used to characterise high-k HfO₂ optical properties and annealing effects (NIST). — [NIST, Cho et al. APL 2002](https://www.nist.gov/publications/spectroscopic-ellipsometry-characterization-high-k-dielectric-hfo2-thin-films-and-high)

### Inferences
- Learner's node, corrected:
  - "Diffusion (thermal oxide) and most dielectric CVD films (SiO₂, TEOS, Si₃N₄, SiON) are transparent (k ≈ 0) over the visible, so they are modeled with Cauchy/Sellmeier.
  - Absorbing films such as poly-Si/a-Si, SiGe, TiN, W and other metals, and many films in the DUV (Si₃N₄ and high-k near their band edges) need oscillator models (Tauc–Lorentz, Cody–Lorentz, Lorentz/Drude for metals).
  - "Transparent" is always relative to the measured wavelength band."
  
  The specific band-edge values for Si₃N₄ and poly-Si are background knowledge, not independently sourced here.
- k is not simply "how much light is absorbed through the film". k is a material property. The absorbed fraction also depends on thickness, through α = 4πk/λ and Beer's law. Absorption depth = 1/α = λ/(4πk).
- Both SE and SR can measure n and k. SE is more robust for thin films, but neither is exclusively the "n&k tool".

### Gaps
- No single primary source gathered here gives a curated table of the transparency windows (band edges) of common fab films. Fujiwara's textbook and the Tompkins & Irene handbook would be the references, but they were not accessible online.

---

## Q5. Reflectance vs reflectivity; reflectance on PVD metals as a roughness/grain monitor; is "0.8 smooth / 0.5 rough" real?

### Takeaway
Reflectance = reflected/incident radiant flux (power), between 0 and 1, measured on a specific sample. Reflectivity is the intrinsic (thick-sample) value, though fabs use the two words interchangeably. On PVD metals, specular reflectance mainly indicates surface roughness and morphology (grain size, hillocks, deposition temperature), plus composition, oxidation and contamination, and thickness for very thin metals. It is a relative, recipe-specific monitor. The physics (Bennett–Porteus) shows that reflectance depends on rms roughness relative to the wavelength and on the metal's own reflectivity. So "0.8 = smooth, 0.5 = rough" is not a universal rule. Direct roughness measurement uses AFM, scatter/haze (TIS), or XRR.

### Cited Findings
**Terminology**
- NBS Monograph 160: "Reflectance is the ratio of reflected to incident flux… may have values only in the interval 0 to 1." — [Nicodemus et al., NBS Monograph 160](https://nvlpubs.nist.gov/nistpubs/Legacy/MONO/nbsmonograph160.pdf)
- "Reflectance is a measured value for a particular specimen and wavelength, while reflectivity is the intrinsic property of the bulk material. In engineering practice the terms are often used interchangeably." — [IEEE Technology Navigator](https://technav.ieee.org/topic/reflectivity)
- Per CIE, reflectivity applies to thick objects; for thin layers, internal reflections make reflectance vary with thickness. Reflectance = \|r\|², where r (the Fresnel reflection coefficient) is the ratio of reflected to incident electric field. — [Wikipedia, Reflectance](https://en.wikipedia.org/wiki/Reflectance)
- The 2026 Metrologia paper defines reflectometry as measuring "the intensity ratio of reflected light to incident light". — [Rastgou et al., Metrologia 2026](https://iopscience.iop.org/article/10.1088/1681-7575/ae3964)

**Roughness physics**
- Bennett & Porteus (JOSA 1961): expressions relate rms roughness to specular reflectance at normal incidence, valid when rms roughness ≪ λ. "If light of a sufficiently long wavelength is used, the decrease in measured specular reflectance due to surface roughness is a function only of the root mean square height." — [Bennett & Porteus, JOSA 51, 123 (1961)](https://opg.optica.org/abstract.cfm?URI=josa-51-2-123)
- The standard form is Rs = R0·exp[−(4πσ cosθi/λ)²], with Rs specular and R0 total reflectance. For very smooth surfaces Rs/R0 ≈ 1, and total integrated scatter (TIS) is easier to measure. — [IMEKO 2000, scatterometry of machined surfaces](https://www.imeko.org/publications/wc-2000/IMEKO-WC-2000-TC14-P383.pdf); [NBS IR 73-219, Eight techniques for optical roughness measurement](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nbsir73-219.pdf)
- TIS was defined by Bennett & Porteus. The exponential relationship (Davies 1954) assumes rms ≪ λ and Gaussian statistics. TIS is normalised by total reflected power, so low reflectance does not bias the roughness. — [Stover & Staats, The Scatter Works](http://thescatterworks.com/wp-content/uploads/TI-and-FS-measuremnets.pdf)
- With increasing roughness, specular intensity falls and diffuse scatter rises (energy conservation). Above a roughness-to-wavelength ratio of ~0.2, no specular beam remains. — [Fraunhofer IOF, light scattering regimes](https://www.iof.fraunhofer.de/content/dam/iof/de/documents/Publikationen/Fachbeitraege/Modeling%20of%20light%20scattering%20in%20different%20regimes%20of%20surface%20roughness.pdf)
- Aluminium and beryllium mirrors can be "inherently high scatterers, regardless of how smooth they were", because of material inhomogeneity. Scatter is not purely topographic. — [NIST, Measuring interfacial roughness by polarized optical scattering](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=841926)
- For aluminium in the VUV, native alumina overlayer losses dominate, and roughness gives "additional" reflectance reduction. Grain size and rms roughness were tabulated alongside reflectance. — [MDPI Coatings 2023](https://www.mdpi.com/2079-6412/13/1/122)

**Metal reflectance levels and the PVD link**
- Clean pure aluminium reflects >90% of visible light. Rolled foil total reflectivity is ~86% in the visible; the bright side has higher specular and the matte side higher diffuse reflectance. — [Lindseth 1999](https://www.sciencedirect.com/science/article/abs/pii/S0143816600000105)
- Sputtered Al mirrors (50 nm, rms <1 nm by AFM) have high reflectivity; Si wafer reflectivity is only 0.30–0.40 above 400 nm. Au overtakes Al above 600 nm. — [arXiv 2305.17980](https://arxiv.org/html/2305.17980v1)
- UMC patent: Al deposited by PVD at 40–50 °C has reflectivity ~0.925 at ~380 nm. Conventional hot PVD (380–500 °C) gives crystallised grains and an abrupt reflectivity drop near 380 nm. This links PVD temperature and grain structure to reflectivity. — [US 7,462,560 (UMC)](https://patents.justia.com/patent/7462560)
- DC magnetron Al: higher sputtering power "improves the thin film's reflectance and sheet resistance; however, it also increases the formation of hillocks and surface roughness". Films from extrusion targets showed more hillocks and higher AFM roughness (5.1 nm). — [Materials Transactions 2025](https://www.jstage.jst.go.jp/article/matertrans/66/7/66_MT-MB2024013/_html/-char/en)
- 2026 summary of an Al thin-film study: the two thickest films (197 and 280 nm) reflected >90% of visible light. The researchers attribute the high reflectance to low surface roughness, not to grain orientation. — [Advent Research Materials, Sept 2026](https://www.advent-rm.com/en-gb/articles/2026/september/aluminium-thin-films-how-grain-growth-affects-ref) (secondary summary of a university study)
- Sputtered Al/Si (1% Si) on Si can show non-uniform reflectivity with a "marbled texture" from milky flakes, a visual and optical defect signature. — [Gentile et al., TSF 2016](https://www.sciencedirect.com/science/article/abs/pii/S0040609016302346)
- AFM is used as the reference rms roughness method (resolution limit ~0.25 nm on oxidised Si in one study). — [arXiv 2305.17980](https://arxiv.org/html/2305.17980v1)
- XRR gives thickness, density and interface roughness of thin layers (for example ALD HfO₂). Fraunhofer IPMS lists XRR and KLA Surfscan SP3 among 300 mm analytics. — [Fraunhofer IPMS 300 mm analytics](https://www.ipms.fraunhofer.de/content/dam/ipms/en/products/cnt/300%20mm%20Wafer%20Analytics%20and%20Metrology.pdf); [Imashuku 2025 XRS](https://analyticalsciencejournals.onlinelibrary.wiley.com/doi/10.1002/xrs.3499?af=R)

### Inferences
- Worked numbers from Bennett–Porteus at λ = 480 nm (calculated here, not sourced):
  - σ = 5 nm gives Rs/R0 ≈ 0.98
  - σ = 20 nm gives ≈ 0.76
  - σ = 30 nm gives ≈ 0.54
  
  For an Al film with intrinsic R ≈ 0.9, a fall to 0.5 implies roughly 25–30 nm rms roughness, or large hillocks, oxidation or contamination. That is plausible for a badly rough or hot AlCu film but not a fixed rule.
- Metals differ in intrinsic reflectance: Al >0.9 in the visible, Cu and Au lower in the blue, refractory metals and TiN lower still. So a single 0.8/0.5 scale cannot apply across metals or wavelengths. The learner's numbers are best taught as "example spec limits for one recipe (probably AlCu at one wavelength)". Many fabs report reflectivity relative to a bare-Si reference or as % of a reference, but no public source was found for that convention.
- What PVD reflectance monitors (training list):
  - Surface roughness and grain size or texture, which depend on deposition temperature, power and pressure
  - Hillock or whisker formation after anneal
  - Composition and alloying (e.g. Cu/Si in Al)
  - Oxidation or contamination (low base vacuum, outgassing)
  - Thickness of very thin, semi-transparent metals (< ~ a few tens of nm)
  
  It is fast and non-contact, good for SPC trending and tool matching, but indirect.
- Direct or complementary roughness measures: AFM (rms/Ra over µm fields); light-scatter haze (Surfscan-type tools, TIS); XRR (interface roughness); SEM/EBSD for grain size; sheet resistance (Rs) for thickness and grain.
- Correct the learner's formula: R = I_ref/I_in (intensity or power ratio). E_ref/E_in is the amplitude reflection coefficient r, and R = |r|².

### Gaps
- No public fab or vendor document found that defines a standard "reflectivity relative to Si" monitor for AlCu PVD, gives typical spec values, or ties 0.8/0.5 to specific roughness values. The learner's numbers remain UNRESOLVED as anything more than local example limits.
- Specific production reflectivity-monitor tools and wavelengths (historical Tencor/Prometrix-type reflectometers, KLA Surfscan haze channels) were not documented in accessible public sources during this search.
