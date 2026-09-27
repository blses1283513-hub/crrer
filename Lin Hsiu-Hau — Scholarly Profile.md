---
tags: [Lin-Hsiu-Hau, scholarly-profile, mentor-agent, methodology, NTHU]
created: 2026-07-04
updated: 2026-07-04
purpose: Grounding corpus for the lin-hsiu-hau-mentor agent — publication record + distilled research methodology
maintained-by: lin-hsiu-hau-mentor agent (trigger phrase 「優化指導員」)
---

# Lin Hsiu-Hau (林秀豪) — Scholarly Profile & Methodology Distillation

## 1. Metrics (Google Scholar, checked 2026-07-04)

- Total citations 2,515 · h-index 19 · i10-index 33 · ~80 papers
- Research interests (self-declared): statistical physics, materials science, neurophysics
- PhD: UC Santa Barbara → NTHU at 30, full professor at 38

## 2. Top-Cited Works

| Paper | Venue, Year | Citations |
|---|---|---|
| Theory of diluted magnetic semiconductor ferromagnetism | PRL 2000 | 403 |
| Exact SO(8) symmetry in the weakly-interacting two-leg ladder | PRB 1998 | 257 |
| Manipulating exchange bias by spin–orbit torque | Nature Materials 2019 | 236 |
| N-chain Hubbard model in weak coupling | PRB 1997 | 209 |
| Resonant multilead point-contact tunneling | PRB 1999 | 161 |
| Enhanced ferromagnetism in Zn₁₋ₓCoₓO by Cu doping | APL 2004 | 159 |
| Ground-state properties of nanographite with zigzag edges | PRB 2003 | 129 |

## 3. Research Lines (arXiv corpus, ~50 papers)

1. **Ladders & correlated electrons** — N-chain Hubbard (1997), SO(8) ladder (cond-mat/9801285), anomalous scaling (cond-mat/0010011), RG potential flow (cond-mat/0306159, cond-mat/0508660), hierarchy of relevant couplings (0911.0166), RG exponents for SC phases (1111.4373)
2. **Magnetism & spintronics** — DMS ferromagnetism trilogy (cond-mat/0001320, /0010471, Curie-limit /0010036), spin-wave softening & relaxation (2005–06), non-collinear/spiral exchange (2006), SOT engineering (1510.00836), SOT-MRAM (1706.01639), zero-field SOT switching (1911.01785), Néel tensor torque (2310.11839)
3. **Graphene / CNT edge physics** — zigzag nanographite (cond-mat/0303159), flat-band ferromagnetism (cond-mat/0410654, 0901.4387), relativistic edge magnon (0901.4567), Klein-Gordon edge magnons (1107.1102), quantized CNT edge moment (1007.1050), SO(6) Gross-Neveu in zigzag CNT (0901.4097)
4. **Superconductivity** — interband pair-hopping in multiband SC (1107.1796), anomalous isotope effect in Fe-based SC (1112.4326), Andreev edge states as pairing-symmetry probe (0901.4570, 0911.0175)
5. **Quantum transport & Berry phase** — Berry phases of classical trajectories at hard walls (cond-mat/0106393), semiclassical quantization for quantum dots (cond-mat/0303329), spin-resolved QPC transport (1710.00496)
6. **Evolutionary dynamics** — quasispecies variational ansatz (1011.5098, deep-read W09), discreteness enervates biodiversity (1005.4335), fluctuation-induced dissipation (1411.6473, deep-read W09)
7. **Neurophysics & information** — U(1) dynamics in neuronal activities (2109.12608), Sparse Edge Encoder for visual recognition (2211.15278)
8. **Post-2023 (journal versions, no new arXiv preprint found — Scholar check 2026-09-27)** — Néel tensor torque in polycrystalline antiferromagnets, journal version of 2310.11839 (Advanced Materials, DOI 10.1002/adma.202506462, 2026); "A statistical-field approach to electron transport in semiconductor nanodevices" (Nature Reviews Electrical Engineering 2, 614–620, 2025)

## 4. Methodology Distillation — his recurring reasoning moves

**M1. Compute where control exists; let RG reveal universality.** Start in weak coupling where the calculation is honest, then flow. The reward is *emergent symmetry* — SO(8) in ladders, SO(6) Gross-Neveu in CNTs — simplicity that appears at low energy rather than being assumed. Teaching form: pick the corner of the problem you can solve exactly; trust the flow to expose what is universal.

**M2. One skeleton, many bodies.** The two-leg-ladder machinery is ported intact: ladders → carbon nanotubes → graphene nanoribbons → iron pnictides. His career instantiates his own advice: secure a footing in one tool, then cross material families with it. Teaching form: master one method to the bone before touring applications.

**M3. Edges are where the physics hides.** Zigzag edge magnetism, Berry phase per hard-wall reflection, Andreev *edge* states diagnosing bulk pairing symmetry, quantized edge moments. Bulk behavior is textbook; boundaries expose topology. Teaching form: test understanding at boundary/edge/degenerate cases — that is where hidden structure (and misunderstanding) shows.

**M4. Reduce to a one-line effective theory.** σ·B(k) for SSH, Klein-Gordon for edge magnons, Gross-Neveu for CNTs, Majorana representation for RG flow. A result is understood when the messy Hamiltonian collapses to a minimal field theory. Teaching form: after any derivation, demand the one-line effective description.

**M5. After mean-field, ask what fluctuations destroy.** "Limits on the Curie temperature" (cond-mat/0010036): mean-field says yes, collective modes say how far. Anomalous isotope effect from phonon dressing. Teaching form: every first-pass answer gets a second pass — which neglected fluctuation kills it?

**M6. Theory must land in a measurable number.** Half the corpus is with experimental groups (Nature Materials 2019 SOT/exchange bias, ZnCoO doping, CDW X-ray, (Eu,Sm)B₆). Teaching form: end every topic with "what experiment would falsify this?"

**M7. Cross fields with the same toolkit, honestly costed.** Statistical field theory → evolutionary dynamics → neuronal networks (U(1) phases from condensed matter into neural nets). His own crossing took "two months to start, nearly six years to publishable results." Quote: *"I like adventures, but I am not an idiot."* Teaching form: crossing over is encouraged, but the time constant is years, not weeks — and you bring your mastered tools with you.

**M8. Mentoring is honest triage.** He candidly told a student her physics-PhD odds and redirected her to evolutionary biology — successfully. Teaching form: assess the student's actual position frankly; redirect effort to where they can win.

**M9. Change to the representation where hidden structure becomes manifest.** (Deep-read W01, three papers, same move.) The intellectual work is the change of variables, not solving the equation. SO(8) is invisible in bare electrons but manifest after refermionization into Majoranas — *"abelian bosonization masks the full symmetry group."* DMS excitations are invisible in the bare Hamiltonian but appear in the effective action after integrating carriers. Neuronal firing-rate mechanism is invisible until the state is encoded as a complex phase z = r·e^{iφ}. Teaching form: when stuck, do not push harder on the current variables — ask "in what representation would this structure be obvious?" The physics is already there; the right coordinates reveal it.

**M10. Integrate out the exactly-solvable sector; keep its dynamic imprint.** (W01, DMS + SO(8).) Whatever you can treat exactly — a bilinear fermion bath, an RG flow to a fixed ray — integrate it out, but retain the *retarded, non-local* memory it leaves in the effective theory for what remains. DMS: *"since the Hamiltonian is bilinear in fermionic fields, we can integrate out the itinerant carriers,"* producing retarded ion-ion interactions "described here for the first time." Teaching form: split the problem into the part you can solve exactly and the part you care about; solve the first, and let its imprint dress the second — never discard it as a static average.

**M11. Turn dynamics into geometry.** (Deep-read W02: cond-mat/0306159, cond-mat/0508660, 0911.0166.) A tangled flow / dynamical system that resists trajectory-by-trajectory solution can be bounded by finding a monotone potential it descends: dV/dl ≤ 0 forbids chaos and limit cycles *by construction* — "eliminates chaos by topology, not approximation." The RG flow becomes "an overdamped particle searching for a potential minimum"; fixed rays (constant coupling ratios, hence emergent symmetry) fall out of the landscape geometry without integrating any trajectory. A representation change (M9: Majorana) is what makes the symmetrizing transform diagonal so the potential exists at all. Refinement of M1 (from 0911.0166): when many couplings look equally marginal, rank them by the *exponent* of their approach to the singular scale, g_i ~ G_i/(l_d−l)^{γ_i}, not by magnitude at one scale. Teaching form: don't solve the flow — find the monotone function that makes its fate geometric.

> M9, M10, M11 subsume/refine earlier moves: F3 (hunt the microscopically-independent quantity — SO(8) ratios independent of initial couplings, DMS stiffness independent of Jpd) sharpens **M1**; F4 (ask what the excitation spectrum / ordered state looks like, not merely whether it exists) sharpens **M5**. Full derivation: [[Week-01 — Emergent Symmetry, Mechanism, Cross-over]].

## 4b. 思維特點：招式跨域通用（W03 跨線壓力測試驗證）

最重要的一條關於林秀豪思維本質的刻畫（2026-07-04 W03 驗證）：**他的推理招式 M1–M11 不是凝態物理的專屬技巧，是域無關的統計場論之眼。** 把梯子/RG 提煉的招式拿去讀他兩條最遠的研究線——演化生態（1005.4335，離散性抹殺生物多樣性）與神經/ML（2211.15278，資訊最優化 vs 臨界）——M1/M3/M4/M5/M9/M10/M11 全部點得著、無一裂開：
- 生態：M5（1/N 漲落殺 mean-field 共存）、M11（β 純由相空間幾何、與生物參數無關）、M1（t/N 塌縮=普適簽名）。
- 神經：M9（「臨界是否必要」換成「哪些可觀測量各自最優」）、M4（互資訊=單一純量=協方差最大本徵值）、M5（質疑「臨界=最優」教條）。

**這是「一副骨架多具身體（M2）」在方法論層自身的最強證據**：他跨進生物、神經，靠的不是學新領域的知識，是把同一副統計場論的思考骨架搬過去。教學意涵：用這套招式教任何隨機/多體/資訊/最優化系統都成立，不限物理。

## 5. Sources

- Google Scholar profile: https://scholar.google.com/citations?user=aV9m2PQAAAAJ
- arXiv author query (export.arxiv.org API, "Hsiu-Hau Lin", 2026-07-04)
- Taipei Times feature (2020-01-29): https://www.taipeitimes.com/News/taiwan/archives/2020/01/29/2003730005
- NTHU Physics profile: https://phys.site.nthu.edu.tw/p/406-1335-58809,r3608.php?Lang=zh-tw
- Course source: [[Lecture Notes - Quantum Scattering & Dirac Equation]] (worldview preface + verbatim quotes)

## 6. Update Log

- 2026-07-04 — Initial profile: metrics, 7 research lines, moves M1–M8. Next refresh: re-run arXiv query + Scholar check, look for post-2023 papers (Néel tensor torque was latest found).
- 2026-07-04 — Study program W01 (full-text deep read of cond-mat/9801285, cond-mat/0001320, 2109.12608). Added moves **M9** (change representation to reveal hidden structure) and **M10** (integrate out exactly-solvable sector, keep dynamic imprint). Refined M1 (universality-signature) and M5 (excitation-spectrum-not-existence). Program queue: [[curriculum]].
- 2026-07-04 — Study program W02 (full-text deep read of cond-mat/0306159, cond-mat/0508660, 0911.0166; RG methodology). Added move **M11** (turn dynamics into geometry: monotone potential forbids chaos by construction), verified through blind two-arm G3-B ([[W02-scorecard]]). Refined M1 (rank marginal couplings by exponent of approach to singularity) and M9 (change to the basis where the symmetrizing transform is diagonal). Rejected candidate (exponent-ranking, folded into M1) — rejection rate non-zero, gates not rubber-stamping. Moves now M1–M11.
- 2026-07-04 (evening) — Study program W03, re-scoped from ladder papers to a **cross-line generalization test** (per D0: the moves were all ladder-derived; testing whether they generalize is higher-value depth than three more ladder papers). Deep-read 1005.4335 (evolutionary ecology) + 2211.15278 (neuro/ML). **META finding (§4b): M1/M3/M4/M5/M9/M10/M11 fire intact in both maximally-distant domains — the moves are domain-general, not ladder artifacts.** Candidate "entropic directed drift" rejected via blind G3-B (Arm A without it independently rebuilt the heterozygosity Lyapunov via M11 → redundant); folded into M11 as sub-tactic 6. Moves stay M1–M11. See [[Week-03 — Cross-Line Generalization Test]], [[W03-scorecard]]. Original ladder trio deferred to W03b. Next: W03b or W04 only when the move-set needs new ladder-end evidence.
- 2026-09-27 — Study program **W09–W10** (reordered ahead of W04–W08 per the cross-domain-brain goal). Deep-read 1011.5098 + 1411.6473 (evolutionary-dynamics-line originals for M9/M10; both fire M1–M11 near-fully, no candidate) and 2310.11839 (Néel tensor torque — most recent corpus paper, first read in full this cycle). 2310.11839 surfaced a real candidate — "replace symmetry-breaking with statistical inference where no group exists to break" (order parameter built from ensemble mean+covariance via a linear-factor-model/PCA import, for polycrystalline/non-periodic AFMs with no long-range order) — but blind G3-B **REJECTED** it: Arm B, given the candidate, answered with the identical M9+M10 replica-overlap construction as Arm A and never invoked the candidate. Moves stay **M1–M11**. Corpus-refresh side-check (Scholar/arXiv) found 2 post-2023 journal papers not yet in this profile (added to research line 8 above; no new arXiv preprints). See [[Week-09-10 — Cross-Domain Return, Order Without Symmetry]], [[W09-10-scorecard]].
