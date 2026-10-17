# Registration / Overlay Metrology and Wafer-to-Wafer Bonding Alignment Metrology (tree node: "Registration (Reg, overlay)", Photo-litho)

Scope note: public sources only, current as of Oct 2026. Vendor numbers are marketing or conference figures measured on chosen stacks. Treat them as typical values, not specs. Figures older than about 2020 are marked [OLDER].

## Q1. SEM-Reg (e-beam overlay, eOVL, after-etch in-device overlay): principle, why slower, why used, and the learner's claims

### Takeaway
SEM overlay images the real device features (in-die, on-device, at design-rule pitch), usually after etch (AEI/FI). It is used to measure and correct the non-zero offset (NZO) between optical after-develop (ADI) target overlay and true device overlay. It runs on CD-SEM or high-voltage (HV) SEM platforms. It is slow and costly next to *optical* overlay, so fabs sample it rarely. The learner's "slower than CD-SEM" is muddled: SEM-Reg usually runs *on* a CD-SEM or HV-SEM. The right comparison is "much slower than optical overlay".

### Cited Findings
- Principle and use: optical overlay at DI (after develop) on targets is measured every lot or most lots. SEM-based FI (after etch) metrology is done "on-device in-die as-etched on an infrequent basis". The DI-FI difference is called NZO and is fed back as an offset to the DI run-to-run loop. — [SemiEngineering/KLA 2018](https://semiengineering.com/high-volume-manufacturing-device-overlay-process-control/)
- In that study the FI data came from a "CD SEM on the device structure", while DI used Archer 500 on AIM targets (DRAM BLC/SCC layers). The sampling was 2265 points per wafer, 25 per field. For SCC, only Y overlay was available at FI "due to the device structure". — [SemiEngineering/KLA 2018](https://semiengineering.com/high-volume-manufacturing-device-overlay-process-control/)
- Why SEM is used only on a limited basis: "throughput, cost, lack of material transparency, and inability to rework" (the wafer is already etched). — [SemiEngineering/KLA 2018](https://semiengineering.com/high-volume-manufacturing-device-overlay-process-control/)
- NZO is updated from low-frequency FI data. The DI-minus-FI delta is computed point-by-point or by model interpolation, then smoothed with WMA or EWMA before it compensates the DI APC loop. NZO was found mostly static between change points. — [SemiEngineering/KLA 2018](https://semiengineering.com/high-volume-manufacturing-device-overlay-process-control/)
- AEI overlay with a CD-SEM is done "in order to measure in-cell, on-device, and at design rule", typically "every few weeks". The same source says CD-SEM has "relatively low throughput… limited layer transparency, poor precision compared to optical methods, are often destructive to the measured pattern". — [SemiEngineering 2018, in-cell overlay](https://semiengineering.com/in-cell-overlay-metrology-by-using-optical-metrology-tool); contradicted in part by [SemiEngineering 2017 (RLSO)](https://semiengineering.com/improving-optical-overlay-and-measurement), which calls random-located SEM overlay "accurate and non-destructive" with "sub-nm precision" and says e-beam is "the only technology with resolution high enough to generate overlay data from the complex small devices".
- In-device SEM overlay on a 28 nm logic VIA layer was used to show the NZO gap. It also gives denser overlay distributions that enable high-order scanner correction (CSTIC 2025). — [IEEE Xplore 11017840](https://ieeexplore.ieee.org/document/11017840)
- Buried layers: high-voltage SEM (KLA eSL10 HV-SEM) was used for AEI overlay because secondary electrons from HV-SEM detect buried structures (2021). — [SPIE 11611](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/11611/116112M/Imaging-based-overlay-metrology-optimized-by-HV-SEM-in-3D/10.1117/12.2583609.full)
- Hitachi CV7300 is an in-line HV CD-SEM at 60 kV. It is marketed for "high speed and high precision overlay measurements for the advanced DRAM and Logic device", with about 20% throughput gain over the prior model. — [Hitachi High-Tech CV7300](https://www.hitachi-hightech.com/global/en/products/semiconductor-manufacturing/cd-sem/metrology-solution/semi-cv7300.html)
- ASML/HMI eP5 XLE does high-throughput e-beam metrology: 12k-pixel large field of view, "5~30x throughput vs. conventional CD-SEM", SE and BSE detectors, landing energy tuned for penetration depth. It showed overlay of DRAM bit line to active after etch at 30 keV (2023). Voltage-contrast-based overlay matched SEM overlay within <1 nm offset. — [eBeam Initiative / ASML 2023](http://www.ebeam.org/docs/2023-02-28-ebeam-initiative-yu-cao-final.pdf)
- IRDS 2024 notes CD-SEM-based overlay is "starting to gain acceptance for some roles". It also says tight DRAM/NVM overlay budgets call for alternatives such as high-voltage SEM and scatterometry. — [IRDS 2024 Metrology (NIST copy)](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=959302)
- ASML says YieldStar after-etch metrology inspects device structures "with more accuracy and higher measuring speeds than our competitors' scanning electron microscope (SEM) solutions". — [ASML, measuring accuracy](https://www.asml.com/en/en/technology/lithography-principles/measuring-accuracy)

### Inferences
- "Pattern after Dry Etch": VERIFIED. SEM-Reg is mainly an AEI/FI technique, though SEM can also measure ADI on resist with shrink risk. "Not integrated with tool": VERIFIED by practice (standalone SEM). No source states it explicitly.
- "Slower than CD-SEM": CORRECTED. SEM overlay runs on CD-SEM or HV-SEM tools. It is much slower per site and per wafer than *optical* overlay, which is why it is sampled every few weeks or on a few lots. Per site, it can take longer than a single CD measurement because it may need high landing energy, larger FOV or multiple images to see top and buried layers. That last point is an inference; I found no public time-per-site comparison.
- Destructiveness is disputed. At AEI on hard materials SEM is usually treated as non-destructive. At ADI on resist, beam-induced shrink or damage is a known risk.

### Gaps
- I found no public, current figure for SEM overlay precision (nm, 3σ) or sites per hour on 2024-2026 tools.

## Q2. Reg-DBO (diffraction-based overlay, µDBO, SCOL)

### Takeaway
DBO measures overlay from the intensity asymmetry between +1 and −1 diffraction orders of stacked grating-over-grating targets with built-in ±bias. It is non-imaging, non-contact and non-destructive. The ADI version can be track-integrated (ASML YieldStar), so "not integrated" is only partly true. KLA's DBO flavour is SCOL / ATL. Typical published TMU is sub-0.5 nm on small (4-10 µm) targets. Sampling is many sites per wafer on dedicated targets (scribe or small in-die). Newer tools also measure on-device after etch.

### Cited Findings
- Principle: a µDBO target has overlapping grating pairs. A small shift between the gratings changes the diffracted intensity. "Multiple grating-pairs with different intentional overlay bias" let overlay be found from the measured intensities. A µDBO target has four grating pairs, two per direction, biased ±d (d = 20 nm in the example). "By measuring both gratings pairs, the measurement can be made independent of the stack." — [ARCNL/ASML, J. Micro/Nanopattern. 2022](https://ir.arcnl.nl/pub/269/00216publishedVersion.pdf)
- µDBO can be read from **dark-field images** of the +1 and −1 orders: integrate intensity per biased grating, compute the asymmetry, then overlay. Multi-wavelength µDBO reached "accuracy levels in the subnanometer range even in the presence of process variations". — [ARCNL 2022](https://ir.arcnl.nl/pub/269/00216publishedVersion.pdf)
- KLA SCOL "uses angle-resolved **pupil imaging** for overlay analysis", with tunable-laser and multi-wavelength illumination. — [Technion CRIS](https://cris.technion.ac.il/en/publications/enhancement-of-overlay-metrology-accuracy-by-multi-wavelength-sca). KLA patents describe both "scatterometry overlay based on pupil-plane images of diffraction orders" and image-based (field-plane) scatterometry that needs a sensitive camera. — [US 12,716,837 (2026)](https://patents.justia.com/patent/12716837); [US 11,428,642](https://www.freepatentsonline.com/11428642.html)
- KLA ATL100 (Accurate Tunable Laser): scatterometry-based overlay for ≤7 nm nodes. Tunable laser with 1 nm wavelength resolution plus real-time "Homing". Supports "in-die and small pitch" SCOL targets. — [KLA metrology page (mirror)](https://microsense.net/press-releases); [KLA metrology](https://www.kla.com/products/chip-manufacturing/metrology). The Archer and ATL series are still listed in KLA's 2026 annual report. — [KLA Annual Report 2026](https://ir.kla.com/sec-filings/annual-reports/content/0001193125-26-397978/0001193125-26-397978.pdf)
- YieldStar precision: targets as small as 4×4 µm²; "TMU < 0.33 nm for 6 × 6 µm²" with "MAM time < 60 ms". µDBO was demonstrated down to 10×10 µm² for in-die use [OLDER, ~2013-2018, aggregated abstracts]. — [science.gov topic page](https://www.science.gov/topicpages/d/diffraction+based+overlay)
- DBO on double-patterning LFLE: dynamic precision <0.2 nm, TMU <0.5 nm, mean TIS <0.1 nm [OLDER, ~2011]. — [InTech chapter](https://cdn.intechopen.com/pdfs/24510/InTech-Diffraction_based_overlay_metrology_for_double_patterning_technologies.pdf)
- Integration: YieldStar 380G (ADI overlay + focus) is "available in track-integrated and standalone versions", with continuous wavelength 425-885 nm selectable to 1 nm. — [ASML YieldStar 380G](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-380g). ASML: "By integrating our solution into the production line (or 'track')…" — [ASML](https://www.asml.com/en/en/technology/lithography-principles/measuring-accuracy). YieldStar 500 is a standalone ADI overlay tool on a TWINSCAN stage. YieldStar 1385/1390 are standalone post-etch tools. — [ASML products](https://www.asml.com/en/en/products/metrology-and-inspection-systems)
- DBO (YieldStar) and IBO (Archer) "compete" at 28/14 nm (aggregated abstract). — [science.gov](https://www.science.gov/topicpages/d/diffraction+based+overlay)

### Inferences
- "Non-destructive, no contact": VERIFIED. "Not integrated": CORRECTED. ADI DBO is often track-integrated (YieldStar); standalone versions exist too. "Measures multiple sites on wafer and on test structures": VERIFIED. Main use is dedicated µDBO/SCOL targets in scribe or small in-die areas; in-device after etch is a newer extension (see Q5).
- On pupil vs field plane: classic DBO/SCOL works in the pupil (angle-resolved) plane. µDBO on small targets is usually read in the dark-field image (field) plane, but the signal is still diffraction-order intensity asymmetry, not an edge-position image.

### Gaps
- Current (2024-2026) YieldStar 385/390 or ATL TMU/MAM specs are not public. Treat the 0.33 nm TMU figure as an older typical value.

## Q3. Reg-IBO (image-based overlay; KLA Archer)

### Takeaway
IBO is bright-field optical microscopy of a target. It measures the centre-of-symmetry offset between current-layer and previous-layer features in the image (field) plane. Targets: box-in-box (BiB), frame-in-frame, AIM-family gratings. It is non-contact and non-destructive, measures test structures, and multi-layer targets are standard. Modern Archer tools add tunable wavelength and reach scatterometry-class throughput. Published TMU went from about 2 nm (2005) to sub-1 nm (2010s). Current specs are not public.

### Cited Findings
- KLA Archer 750 (2020): imaging-based overlay with "wave tuning", a custom filter of best wavelength and bandwidth, at 10 nm resolution. A "color per layer" mode improves SNR on thin EUV resist and opaque films. Productivity is "previously seen only with scatterometry-based overlay systems". rAIM targets improve device-target correlation. — [KLA press release 2020](https://ir.kla.com/news-events/press-releases/detail/24/kla-introduces-new-ic-metrology-systems); [KLA Korea page](https://www.kla.com/ko/archer-spectrashape-metrology); [EE Times 2020](https://www.eetimes.com/overlay-metrology-challenges-for-advanced-memory-ics)
- Archer 800 is listed as the current IBO system, with rAIM and "improved correlation between target and device overlay errors". — [KLA metrology page (mirror)](https://microsense.net/press-releases)
- Multi-layer: Archer 500 (2012) introduced "a new, multi-layer design for the overlay metrology target… numerous combinations of intra- and inter-layer overlay data from the same target image". — [KLA 2012](https://ir.kla.com/news-events/press-releases/detail/204/kla-tencor-announces-new-archer-500-overlay-metrology). YieldStar DBO also does multi-layer targets (YS350). — [science.gov](https://www.science.gov/topicpages/d/diffraction+based+overlay)
- In-die IBO: Archer 300 LCM (2010) added "very tiny metrology targets placed within the die itself, instead of only in the areas between die" [OLDER]. — [KLA 2010](https://ir.kla.com/news-events/press-releases/detail/269/kla-tencor-launches-the-archertm-300-lcm-overlay)
- Historic figures [OLDER]: Archer AIM+ TMU 2.1 nm. Archer XT+ is box-in-box compatible, up to 180 wafers/h (2005). — [EE Times 2005](https://www.eetimes.com/kla-tencor-rolls-new-overlay-metrology-tool). Archer 200 TIS 0.8 nm, with a SCOL option at TMU 0.7 nm but lower throughput (2008). — [Semiconductor Digest 2008](https://sst.semiconductor-digest.com/2008/06/kla-tencor-announces-archer-200-overlay-metrology-system). "Most advanced IBO tools are operating at TMU levels under 1nm" (~2011). — [InTech](https://cdn.intechopen.com/pdfs/24510/InTech-Diffraction_based_overlay_metrology_for_double_patterning_technologies.pdf)
- IBO limitation: classic IBO targets sit outside the chip and are about two orders of magnitude larger than cell features. They have "shown deviations from the actual device overlay error within the die" [OLDER 2009]. — [Optics Express 2009](https://opg.optica.org/oe/viewmedia.cfm?uri=oe-17-23-21336&html=true)
- 3D NAND IBO challenges: >100 layer pairs, thick opaque hard masks, high topography, wafer stress. DRAM overlay budget is "approaching the sub-2 nm threshold". — [EE Times 2020](https://www.eetimes.com/overlay-metrology-challenges-for-advanced-memory-ics)

### Inferences
- "Non-destructive, no contact": VERIFIED. "Measures on test structure": VERIFIED. "Able to measure multiple layers": VERIFIED, but not unique to IBO, since DBO also has multi-layer targets.
- IBO tools such as the Archer are generally standalone. I found no source for a track-integrated IBO product.

### Gaps
- No public precision/TMU/throughput spec for Archer 750/800.

## Q4. Reg-AIM: is "AIM = box-in-box" correct? Target types

### Takeaway
CORRECTED. AIM (Advanced Imaging Metrology) is KLA's grating-style imaging target, introduced in 2003 to *replace* box-in-box. Both are imaging (IBO) targets, read on the same Archer tools. AIM uses segmented gratings rather than solid box edges, which is denser, more CMP-robust and better correlated to device. The AIM family grew into µAIM, ProAIM, rAIM, DAIM and AIMid. Saying AIM is "for critical layers" is reasonable: grating targets were introduced for advanced/critical layers. BiB is still supported and used.

### Cited Findings
- 2003 Archer AIM uses "a grating style overlay target". "Current overlay metrology methods use test structures called box-in-box targets, which are built into the scribe lines." At 65 nm those no longer correlate to device conditions (lens aberration, defocus) and are "highly susceptible to degradation from CMP". "Instead of the traditional box-in-box, Archer AIM utilizes grating style targets [that] are denser and more robust." — [EDN 2003](https://www.edn.com/kla-tencors-archer-takes-aim)
- "Advanced imaging metrology targets where the box structures were replaced by gratings" gave "a big improvement in metrology precision and robustness". — [ARCNL/ASML 2022](https://ir.arcnl.nl/pub/269/00216publishedVersion.pdf)
- Grating marks cut TMU by about 40% versus BiB in a Motorola/KLA study [OLDER 2003]. — [NXP/Motorola SPIE 2003](https://www.nxp.com/docs/en/white-paper/SPIE_2003_MICROLITHOGRAPHY_JA.pdf)
- Grating targets are "more robust to chemical mechanical planarization (CMP) processing than box-in-box targets". The Archer XT+ was the box-in-box-compatible variant [OLDER 2005]. — [EE Times 2005](https://www.eetimes.com/kla-tencor-rolls-new-overlay-metrology-tool)
- Target family:
  - µAIM: about 10 µm², can go in-chip (2008). — [Semiconductor Digest 2008](https://sst.semiconductor-digest.com/2008/06/kla-tencor-announces-archer-200-overlay-metrology-system); [KLA 2008](https://ir.kla.com/news-events/press-releases/detail/323/kla-tencor-launches-new-archer-200-overlay-metrology-system)
  - ProAIM: more resilient to process variation, better target-device correlation (2017). — [KLA 2017](https://ir.kla.com/news-events/press-releases/detail/106/kla-tencor-introduces-new-metrology-systems-for)
  - rAIM: "robust AIM", grating-over-grating layout. On production wafers it gave +15% ADI-IBO to AEI-SEM correlation, −10% residuals, −25% TMU. — [EE Times 2020](https://www.eetimes.com/overlay-metrology-challenges-for-advanced-memory-ics)
  - DAIM: diagonal AIM, with tilted lines for DRAM extreme-dipole layers. — [EE Times 2020](https://www.eetimes.com/overlay-metrology-challenges-for-advanced-memory-ics)
  - AIMid and BiB: both used in the scribe line for W2W bonding overlay. — [SPIE 12955 2024](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/12955/129551Q/Advanced-processing-control-for-wafer-to-wafer-hybrid-bonding/10.1117/12.3010036.full)

### Inferences
- Learner's correct mental model: BiB, frame-in-frame and AIM are all IBO targets. AIM is the grating-based successor to BiB, not the same thing. "Reg-AIM" and "Reg-IBO" are not separate techniques. AIM is a target design measured by IBO tools, so the tree should put AIM *under* IBO as a target type.
- "Blossom" targets: I found no public source in this pass. Leave them out or mark them UNRESOLVED.

### Gaps
- Blossom target details are unverified. "AIM" expanding to "Advanced Imaging Metrology" is supported indirectly by the ARCNL wording; no KLA page in this pass spells it out.

## Q5. Optical in-die / in-device overlay: 0.7 nm precision? "Uses pupil images, but actual optical microscope image"?

### Takeaway
Commercial optical in-device overlay is diffraction-based (scatterometry): ASML YieldStar 1375F/1385/1390 IDM, after etch, standalone, with ML trained on reticle training marks. It does not produce a resolved microscope image of device features, which are far below optical resolution. Overlay comes from pupil-plane, angle-resolved diffraction asymmetry. The learner's "uses pupil images" is right. "Actual optical microscope image" is CORRECTED, though tools may also record a field image for navigation and ROI. A 0.7 nm precision figure is plausible, even conservative, for modern optical overlay. Speed versus SEM, standalone and non-destructive are VERIFIED.

### Cited Findings
- YieldStar 1385: "standalone optical wafer metrology system for post-etch overlay". "Considerably faster than scanning electron microscope (SEM) solutions." "Novel data science techniques are used to extract in-device overlay measurements with nanometer-level accuracy." It measures "multiple layers at once, either through in-device chip features or small, dedicated metrology targets embedded in the chip design." — [ASML YieldStar 1385](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-1385)
- YieldStar 1375F was the "first YieldStar… to offer measurements within the chip itself". It uses "diffraction from chip structures themselves or small targets placed within the chip design" and ML "in combination with specifically designed training marks on the reticle". — [ASML YieldStar 1375F](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-1375f). YieldStar 1390 is the successor, with a brighter source and in-device tilt and CD. — [ASML YieldStar 1390](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-1390)
- YieldStar is "a diffraction-based optical metrology system". — [ASML](https://www.asml.com/en/en/technology/lithography-principles/measuring-accuracy)
- "Modern optical OVL tools collect wavelength resolved field and pupil images", and "symmetric-pupil behavior at AEI" is analysed. Keywords include "diffraction-based overlay, in-device overlay" (SPIE 2026). — [SPIE 13981 (2026)](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/13981/3092351/Beyond-overlay-additional-parameters-extracted-from-overlay-metrology-measurements/10.1117/12.3092351.full). "Pupil images from DBO metrology" are used as the raw signal. — [ResearchGate 2023](https://www.researchgate.net/publication/375788768_Diffraction-Based_Overlay_Metrology_with_Optical_Convolution_Layer)
- SK hynix DRAM: YieldStar IDM after-etch device overlay allowed "dramatically increased overlay metrology sampling at affordable throughputs". This enabled higher-order corrections toward "sub-2nm on device overlay" (2020). — [SPIE 11325](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/11325/2552028/Improving-after-etch-overlay-performance-using-high-density-in-device/10.1117/12.2552028.full)
- Spectroscopic ellipsometry with ML (model-less and model-based) has also shown after-etch in-cell on-device overlay. — [SemiEngineering 2018](https://semiengineering.com/in-cell-overlay-metrology-by-using-optical-metrology-tool)
- Precision context: µDBO TMU <0.33 nm on 6×6 µm targets [OLDER]. — [science.gov](https://www.science.gov/topicpages/d/diffraction+based+overlay). SCOL TMU 0.7 nm as early as 2008 [OLDER]. — [Semiconductor Digest 2008](https://sst.semiconductor-digest.com/2008/06/kla-tencor-announces-archer-200-overlay-metrology-system)

### Inferences
- "Precision 0.7 nm": VERIFIED as plausible. Optical overlay precision and TMU have been sub-nm since about 2008-2013. 0.7 nm is a reasonable typical in-device AEI figure; ADI target-based precision is often better (≤0.3 nm). In-device-specific public precision numbers were not found.
- "Measures product wafer directly on die structure with equivalent pattern": VERIFIED with nuance. It measures device structures *or* small in-die targets. "Equivalent pattern" fits the reticle training marks and device-like in-die targets.
- "Much faster than SEM-Reg; standalone; non-destructive": VERIFIED (ASML).
- It is an AEI technique. It complements ADI target metrology and SEM, and it addresses NZO with dense sampling.

### Gaps
- No public spec for in-device precision or TMU, MAM time, or wafers per hour for YieldStar 1385/1390.

## Q6. Wafer-to-wafer bonding alignment / post-bond overlay metrology (face-to-face, NAND CBA)

### Takeaway
Post-bond overlay is measured through the silicon with IR (SWIR) reflection microscopy. This is image-based overlay on dedicated scribe-line targets (AIMid or box-in-box) formed with the Cu pad layer. So "principle same as IBO" and "measures Reg boxes, not die structures" are VERIFIED. The "~15 nm precision" is CORRECTED. Published dedicated tools (KLA irArcher 007) report about 1 nm TMU on production wafers. Generic IR microscopes are older and coarser (1σ repeatability <100 nm per IRDS). Overlay *values* achieved by bonding are about 40-100 nm, and bonder alignment accuracy is sub-50 nm. "Not integrated" is true for standalone IR overlay tools. Bonders do offer in-situ alignment verification modules.

### Cited Findings
- Kioxia CBA (CMOS directly Bonded to Array): "mark patterns for overlay inspection are formed at the time of Cu pad formation, and after wafers are bonded… the overlay accuracy between substrates is measured". Visible-light tools "cannot measure the overlay before Si grind", so Kioxia and KLA developed "an Image Based Overlay (IBO) metrology tool… a reflection-based microscope using Short Wavelength Infrared (SWIR) with multiple spectral bands". Post-bond vs post-grind overlay correlation was about 0.99, good enough for APC with shorter turnaround (SPIE 2024, Goto et al.). — [KIOXIA 2024](https://www.kioxia.com/en-jp/rd/technology/topics/topics-68.html)
- irArcher 007 is the "dedicated W2W post-bonding (pre-grinding) OVL metrology tool… reflection-based microscope using SWIR". It does TIS control per site. Targets are AIMid and box-in-box, "placed in different locations in the bonded wafers scribe line". Overlay is measured "between targets located on either side of the bonding interface". Inner-to-outer target distance is up to 5 µm. TMU and matching "must meet typically 10% of the OPO budget". It handles "hundreds of microns of warpage". The dominant 3σ term was symmetric magnification (runout), which correlated with post-bond shape (3D NAND, SPIE 2024). — [SPIE 12955 129551Q](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/12955/129551Q/Advanced-processing-control-for-wafer-to-wafer-hybrid-bonding/10.1117/12.3010036.full)
- irArcher 007 on CIS W2W production wafers: "TMU of 1 nm on production wafers, with TIS values comparable to the current best-in-class metrology tool for single wafer OVL", HVM-suitable throughput. It addresses the "sub-50 nm OVL challenge in sub-micron pitch" bonding (ECTC 2023). — [IEEE ECTC 2023](https://ieeexplore.ieee.org/document/10195808)
- IRDS 2024: IR microscopy measures "alignment fiducials at the interface of the bonded wafer pairs". Si is transparent in IR through 775 µm. Tools use broadband halogen or 1310 nm laser. "1 sigma repeatability of less than 0.1 µm", Rayleigh resolution about 0.5 µm. Metal layers can block measurement in hybrid bonding. — [IRDS 2024 Metrology](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=959302); same text in [ITRS 2015](https://www.semiconductors.org/wp-content/uploads/2018/06/2_2015-ITRS-2.0-Metrology.pdf) [repeatability figure is OLDER and carried forward].
- 3D NAND post-bond overlay studied with irArcher 007 plus PWG wafer shape. "High warpage wafers can induce stress… poor overlay" (SPIE 2025). — [SPIE 13426](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/13426/134262U/Shape-induced-overlay-for-wafer-to-wafer-hybrid-bonding/10.1117/12.3049615.full)
- Bond overlay magnitudes and budget:
  - EVG GEMINI FB / SmartView NT3: "face-to-face bond aligner with sub-50-nm wafer-to-wafer alignment accuracy". It has "in-situ measurements-based alignment feedback" and an "alignment verification module". — [EVG brochure 2026](https://www.evgroup.com/fileadmin/media/products/bonding/Fusion_and_Hybrid_Bonding/gemini-fb/EVG_Gemini_FB___Bondscale_Brochure_26_01.pdf); [EVG GEMINI FB](https://www.evgroup.com/products/bonding/fusion-and-hybrid-bonding-systems/gemini-fb)
  - Imec/EVG (May 2026): 200 nm pitch W2W hybrid bonding, Cu pad-to-pad post-bond overlay vector <40 nm for 100% of dies. — [imec](https://www.imec-int.com/en/press/imec-and-ev-group-demonstrate-wafer-wafer-hybrid-bonding-200nm-interconnect-pitch-and-record)
  - About 50 nm bonding overlay over 12 continuous wafer pairs (ECTC 2023 bonder paper). — [IEEE 10195620](https://ieeexplore.ieee.org/document/10195620)
  - EVG (Hybrid Bonding Symposium 2026): free bond about 100 nm, bond optimisation about 50 nm, litho pre-compensation CPE6 about 10 nm and CPE33 about 3 nm. "1 µm bow ≈ 1 nm OV". Bond overlay is modelled with 4 parameters (Tx, Ty, rotation, scale) plus residuals. — [EVG/imec HBS 2026](https://attend.ieee.org/hbs/wp-content/uploads/sites/692/2026-2-6-Alexeev.pdf)
- Post-bond lithography to a pre-bond layer needs sub-5 nm OPO. 2.8 nm (m3σ) was shown after one rework with 38-parameter CPE on a TEL-bonded wafer (SPIE 2026). — [SPIE 13981 139810M](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/13981/139810M/Characterization-and-mitigation-of-wafer-bonding-induced-distortions-to-enable/10.1117/12.3088567.full)
- EVG40 D2W (2025) is a dedicated die-to-wafer overlay metrology tool: up to 2800 points in 4 min, dual-layer measurement. Legacy W2W tools use "move-acquire-measure", which "exceed[s] the measurement precision while lacking the throughput" for D2W. — [EVG 2025](https://www.evgroup.com/company/news/detail/ev-group-achieves-breakthrough-in-hybrid-bonding-overlay-control-for-chiplet-integration); [PRNewswire](https://www.prnewswire.com/news-releases/ev-group-achieves-breakthrough-in-hybrid-bonding-overlay-control-for-chiplet-integration-302548776.html)

### Inferences
- "IR alignment": VERIFIED. SWIR through Si, at the bonded interface. "Principle same as Reg-IBO": VERIFIED. It is an IBO microscope in SWIR, reading AIM-type or BiB targets.
- "Precision ~15 nm": CORRECTED. Public data for the dedicated HVM tool show about 1 nm TMU. 15 nm would be about 15-40% of a 40-100 nm bond overlay budget, which breaks the "TMU ≈10% of OPO budget" rule cited above. 15 nm may be a figure from an older or generic IR microscope, or a bonder-internal verification. It could also be a confusion with the bond overlay result. The origin of the learner's figure is UNRESOLVED.
- "Non-destructive, no contact": VERIFIED. "Can measure product wafer or patterned short-loop wafer": VERIFIED. Production wafers are shown in ECTC 2023 and SPIE 2024; test vehicles appear in imec and SPIE work. "Cannot measure directly on die structure, measures Reg boxes": VERIFIED. Targets are scribe-line AIMid/BiB; Cu/metal blocks IR and device pads are not overlay targets.
- "Not integrated": VERIFIED for standalone IR metrology tools (irArcher). Note that bonders include alignment verification and in-situ feedback modules.
- Terminology: "wafer-to-wafer alignment" can mean the bonder's pre-bond alignment, which on SmartView is face-to-face optical, not IR through-wafer. It can also mean post-bond overlay metrology, which is IR IBO. The tree node describes the latter.

### Gaps
- Kioxia SPIE 2024 TMU figures not retrieved. No public info on Xtacking (YMTC) or Samsung/SK hynix bonding metrology tool choice. No public irArcher throughput number.

## Q7. Cross-cutting metrics and concepts: TMU, TIS, precision, ADI vs AEI, NZO, location, overlay modelling

### Takeaway
Overlay is reported as x/y vectors per site, then modelled into scanner correctables and residuals. Quality is judged by precision, TIS, tool matching and TMU. The rule of thumb is metrology TMU at about 10-20% of the overlay budget. ADI target overlay drives every-lot APC. AEI overlay (SEM or in-device optical) measures the target-to-device and litho-to-etch bias (NZO), which is fed back as an offset.

### Cited Findings
- TIS: measure at 0° and 180° wafer rotation; TIS = [OVL(0°) + OVL(180°)]/2. TMU = √(TIS3σ² + precision² + OMF² + matching²), per axis. "Mean TIS can be calibrated and therefore is not included" [OLDER 2003, still standard]. — [NXP/Motorola SPIE 2003](https://www.nxp.com/docs/en/white-paper/SPIE_2003_MICROLITHOGRAPHY_JA.pdf); [Sullivan, AIP](https://pubs.aip.org/aip/acp/article-pdf/449/1/502/11535840/502_1_online.pdf)
- ITRS-style TMU = √(dynamic precision² + (3σ TIS)² + tool matching²). If 20% of the process budget goes to metrology, the 32 nm node gave 1.2 nm (single patterning) and 0.22 nm (DPT) [OLDER]. — [InTech](https://cdn.intechopen.com/pdfs/24510/InTech-Diffraction_based_overlay_metrology_for_double_patterning_technologies.pdf)
- IRDS 2024: precision alone misses bias variation, so TMU is used on a representative sample set. Fleet Matching Precision (FMP) extends this to a tool fleet. EPE (edge placement error) combines CD, overlay and LER. — [IRDS 2024](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=959302)
- TMU and matching typically ≤10% of OPO budget. — [SPIE 12955 2024](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/12955/129551Q/Advanced-processing-control-for-wafer-to-wafer-hybrid-bonding/10.1117/12.3010036.full)
- DRAM/NVM overlay budget is 20-25% of device half-pitch. — [ITRS 2015](https://www.semiconductors.org/wp-content/uploads/2018/06/2_2015-ITRS-2.0-Metrology.pdf). DRAM device overlay budget is sub-2 nm. — [EE Times 2020](https://www.eetimes.com/overlay-metrology-challenges-for-advanced-memory-ics); [SPIE 11325](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/11325/2552028/Improving-after-etch-overlay-performance-using-high-density-in-device/10.1117/12.2552028.full)
- ADI vs AEI and NZO: "systematic deviation between optical ADI and AEI OVL, known as non-zero offset (NZO)". — [IEEE CSTIC 2025](https://ieeexplore.ieee.org/document/11017840). Accuracy issues include the ADI-AEI bias and the overlay difference between target and device. Precision alone does not ensure accuracy; different measurement conditions can give different overlay maps. — [SemiEngineering 2017](https://semiengineering.com/accuracy-in-optical-overlay-metrology). Quality metrics such as Qmerit flag NZO change points. — [SemiEngineering 2018](https://semiengineering.com/high-volume-manufacturing-device-overlay-process-control/)
- Location: classic BiB and AIM sit in the scribe line. µAIM and µDBO are small enough for in-die placement. In-device measures the device itself. — [EDN 2003](https://www.edn.com/kla-tencors-archer-takes-aim); [KLA 2008](https://ir.kla.com/news-events/press-releases/detail/323/kla-tencor-launches-new-archer-200-overlay-metrology-system); [ASML 1385](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-1385)
- Modelling: the usual ten correction parameters are wafer translation Tx/Ty, wafer magnification (scale) Mx/My, wafer rotation Rx/Ry (rotation and non-orthogonality), plus field magnification and field rotation. Residuals are "the part of the measured overlay differences that cannot be accounted for" by the model. — [EP 2620976 A1](https://data.epo.org/publication-server/rest/v1.0/publication-dates/20130731/patents/EP2620976NWA1/document.pdf)
- Errors split into interfield/grid terms (translation, scale, wafer rotation, orthogonality) and intrafield terms (translation, isotropic magnification, reticle rotation, asymmetric magnification and rotation). — [US20060238761A1](https://patents.google.com/patent/US20060238761A1/en)
- "In the past, a 6-parameter (linear) intra-field correction model was sufficient… Today, the correction potential per field can be up to 38-parameters." APC corrections come from overlay measurements of earlier lots. — [Zeiss/SPIE 2019](https://asset-downloads.zeiss.com/catalogs/download/smt/e3adcdad-6d01-4878-883f-c018b452ea38/vol11148pt20191114811.pdf). High-order models use CPE (corrections per exposure) and HOPC. — [YouTube lecture 2023](https://www.youtube.com/watch?v=AmKUNuN-ugE); [SPIE PM 2026 abstract (CPE33)](https://spie.org/photomask-technology/presentation/Virtual-metrology-for-improving-overlay-control-capability-in-high-NA/14272-51)

### Inferences
- For learners, the reported quantities are:
  - raw x/y overlay vectors per site;
  - |mean|+3σ per wafer, the usual summary;
  - modelled correctables (Tx, Ty, scale, rotation, orthogonality, field mag/rot, CPE), which go back to the scanner via APC;
  - residuals, the unmodelled part;
  - tool-quality metrics: precision, TIS, TIS3σ, matching, TMU, Qmerit.

### Gaps
- No single public 2024-2026 table of on-product overlay requirements per logic node. The IRDS lithography tables were not retrieved.

## Q8. Claim-by-claim verdicts (learner's notes)

### Takeaway
The tree is mostly right on non-destructive/standalone attributes. It needs four structural fixes:
1. AIM is a grating target measured by IBO, not a separate technique and not box-in-box.
2. DBO is often track-integrated.
3. In-die optical overlay is diffraction/pupil-based, not a microscope image of the device.
4. W2W IR overlay precision is about 1 nm TMU on modern dedicated tools, not about 15 nm.

### Cited Findings
- SEM-Reg "pattern after dry etch": VERIFIED. — [SemiEngineering 2018](https://semiengineering.com/high-volume-manufacturing-device-overlay-process-control/)
- SEM-Reg "not integrated": VERIFIED by inference (standalone CD-SEM/HV-SEM). — [Hitachi CV7300](https://www.hitachi-hightech.com/global/en/products/semiconductor-manufacturing/cd-sem/metrology-solution/semi-cv7300.html)
- SEM-Reg "slower than CD-SEM": CORRECTED to "runs on CD-SEM/HV-SEM; far slower and lower-sampling than optical overlay". — [SemiEngineering 2018](https://semiengineering.com/high-volume-manufacturing-device-overlay-process-control/); [ASML](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-1385)
- DBO "non-destructive, no contact": VERIFIED. "Not integrated": CORRECTED, since YieldStar ADI tools come in track-integrated and standalone versions. "Multiple sites, test structures": VERIFIED. — [ASML 380G](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-380g); [ARCNL 2022](https://ir.arcnl.nl/pub/269/00216publishedVersion.pdf)
- IBO "non-destructive, no contact, test structure, multiple layers": VERIFIED. Multi-layer targets exist for both IBO and DBO. — [KLA 2012](https://ir.kla.com/news-events/press-releases/detail/204/kla-tencor-announces-new-archer-500-overlay-metrology)
- AIM "box-in-box": CORRECTED. AIM is the grating-style imaging target that replaced BiB. AIM "for critical layer": broadly VERIFIED, since it was introduced for advanced-node control; BiB is still supported. — [EDN 2003](https://www.edn.com/kla-tencors-archer-takes-aim); [EE Times 2005](https://www.eetimes.com/kla-tencor-rolls-new-overlay-metrology-tool)
- In-die optical "precision 0.7 nm": VERIFIED as plausible. Sub-nm TMU has been public since 2008; no in-device-specific public number exists. — [Semiconductor Digest 2008](https://sst.semiconductor-digest.com/2008/06/kla-tencor-announces-archer-200-overlay-metrology-system); [science.gov](https://www.science.gov/topicpages/d/diffraction+based+overlay)
- In-die optical "measures product wafer on die/equivalent pattern; much faster than SEM; standalone; non-destructive": VERIFIED. — [ASML 1385](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-1385); [ASML 1375F](https://www.asml.com/en/products/metrology-and-inspection-systems/yieldstar-1375f)
- In-die optical "uses pupil images, but actual optical microscope image": CORRECTED. Overlay comes from pupil-plane diffraction asymmetry. Tools may also record field images, but device features are not resolved in a microscope image. — [SPIE 2026](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/13981/3092351/Beyond-overlay-additional-parameters-extracted-from-overlay-metrology-measurements/10.1117/12.3092351.full); [ASML](https://www.asml.com/en/en/technology/lithography-principles/measuring-accuracy)
- W2W "IR alignment": VERIFIED. "Principle same as IBO": VERIFIED. — [KIOXIA](https://www.kioxia.com/en-jp/rd/technology/topics/topics-68.html)
- W2W "precision ~15 nm": CORRECTED to about 1 nm TMU (irArcher 007, production CIS). The older generic IR figure is 1σ <100 nm. — [ECTC 2023](https://ieeexplore.ieee.org/document/10195808); [IRDS 2024](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=959302)
- W2W "non-destructive; product or short-loop wafers; measures Reg targets not die structures; not integrated": VERIFIED. Bonders do have in-situ verification modules. — [SPIE 12955](https://www.spiedigitallibrary.org/conference-proceedings-of-spie/12955/129551Q/Advanced-processing-control-for-wafer-to-wafer-hybrid-bonding/10.1117/12.3010036.full); [EVG](https://www.evgroup.com/products/bonding/fusion-and-hybrid-bonding-systems/gemini-fb)

### Inferences
- Suggested tree restructure under "Registration (overlay)":
  - Optical IBO (targets: BiB / frame-in-frame / AIM family), ADI, scribe or in-die.
  - Optical DBO/SCOL (µDBO / SCOL targets), ADI, track-integrated or standalone.
  - Optical in-device DBO, AEI, standalone.
  - e-beam overlay (CD-SEM / HV-SEM), AEI, in-device, low sampling.
  - IR IBO for bonded wafer pairs (AIMid / BiB in scribe), post-bond pre-grind.

### Gaps
- Where the learner's 15 nm and 0.7 nm figures came from (which tool or fab) is unknown.
