---
date: 2026-09-27
agent-version: slimmed (Task 3), body bytes 11137; run as general-purpose emulation reading the agent file (agent type not yet registered at run time)
grader-notes-approved: 2026-09-27
grader: independent subagent (opus)
---

# X-Series Baseline

| probe | kind | items scored | hits | partial | miss | score |
|---|---|---|---|---|---|---|
| X01 | transfer | 2 | 0 | 1 | 1 | 0.25 |
| X03 | transfer | 3 | 3 | 0 | 0 | 1.00 |
| X05 | bridge | 4 | 3 | 1 | 0 | 0.88 |
| X07 | bridge | 2 | 0 | 2 | 0 | 0.50 |
| X10 | trap | 2 | 2 | 0 | 0 | 1.00 |
| X11 | trap | 4 | 0 | 4 | 0 | 0.50 |
| **mean** | | | | | | **0.69** |

(X05 exact = 0.875; overall exact = 4.125 / 6 = 0.6875.)

## Diagnosis
No kind fails as a whole: kind means are transfer 0.63, bridge 0.69, trap 0.75. Each kind has one strong probe and one weak probe. The split follows item type, not probe kind. The answers hit rubric items that are generic structural critiques a physicist can derive alone: the attributes-vs-events hazard model, ideological range, "process = product", misuse of the Poisson yield model, no universality class across crashes, and degenerate LPPL fits. They miss or only partly hit items that need specific empirical findings from the target field: CREDs/costly signaling and minimal counterintuitiveness (X01), AngelList power-law numbers and the concentration-vs-diversification prescription (X07), and the Ising-opinion-model results on history/update-scheme dependence, committed agents and tipping-site fields (X11). In X05 the answer also names the wrong time constant (assay feedback speed instead of capacity scale-up / tech-transfer lead time). The recurring gap is the target field's own named literature mechanisms. The mentor replaces them with a condensed-matter derivation that is internally coherent but was not checked against that field's evidence, and none of the six answers did a literature check.

## Per-probe evidence
### X01
- X01.1 — excluded (unsourced)
- X01.2 — partial — "4. 代價訊號：為什麼「刻意昂貴」的儀式反而長壽" (named only as a queued future question; no credibility or group-commitment mechanism)
- X01.3 — miss — "—"
- Beyond rubric: splits the custom into a calendar "shell" and a replaceable "filling", which separates true extinction from content replacement. Also treats channel redundancy k as the control variable, which is close to the excluded X01.1.
- Biggest error: says cultural depth and meaning are "幾乎無關" to survival. This is asserted, not tested, and it rules out the content-level transmission biases (CREDs, MCI) that the rubric treats as causal.

### X03
- X03.1 — hit — "結構決定基線、事件決定跳躍的比例風險模型"
- X03.2 — hit — "意識形態範圍越寬,基線風險率越高"
- X03.3 — excluded (unsourced)
- X03.4 — hit — "E(t) = 事件屬性…經濟衝擊…醜聞、外交危機"
- Beyond rubric: handles right-censoring of full-term cabinets, uses a constant-hazard null as baseline, and separates a fragile base rate from a large shock as two different failure diagnoses.
- Biggest error: says "德國自 1949 年後只有兩次成功倒閣紀錄". Only one constructive no-confidence vote has succeeded (1982); the 1972 attempt failed. The "兩頭厚" duration-distribution claim is also stated without evidence.

### X05
- X05.1 — hit — "統計工具骨架（SPC、DOE/QbD…）可以搬"
- X05.2 — hit — "生物藥是「process = product」…要重新驗證"
- X05.3 — partial — "關鍵 assay 是週級…一年只跑幾十批" (a time-constant argument, but for assay feedback, not the 2–3 mo vs 9–12 mo capacity / tech-transfer lead time or tacit knowledge)
- X05.4 — hit — "把 Y=exp(-D0A) 套到生物良率上是形式借用"
- Beyond rubric: points out that QbD (ICH Q8) is a transfer that has already happened, gives a falsifiable PAT+SPC pilot, and names statistical power at tens of batches per year as a hard limit.
- Biggest error: frames the fab learning loop as "秒級" and "一天可以跑完好幾輪", a 10^4–10^5× gap. End-of-line yield learning is bounded by wafer cycle time (weeks to months), so the claimed gap is overstated by orders of magnitude.

### X07
- X07.1 — excluded (unsourced)
- X07.2 — partial — "VC 冪律指數 ζ≈1–2 這個經驗值" (names the VC power law with a roughly compatible exponent; no AngelList data, no top-1% ≥22x, no index-beats-active result)
- X07.3 — excluded (unsourced)
- X07.4 — partial — "廣撒低成本首季 + 快速砍掉 + 對贏家追加" (follow-on concentration on winners gestures at tail betting, but "廣撒" leans toward the broad diversification the item rejects; P3 gives a static top-10% share, not a Gini trend over time)
- Beyond rubric: derives the tail exponent from Gibrat growth plus a reflecting barrier (ζ = −2μ/σ²), which turns "looks like a straight line" into a prior-locked exponent test. Also predicts a truncated power law from the subscriber ceiling.
- Biggest error: calls Gibrat plus a reflecting boundary the "已知的生成機制" of VC returns. That model comes from firm-size distributions and is not established for deal-level VC multiples. The "頭部 10–15%" and founder-signal claims are also unsourced.

### X10
- X10.1 — excluded (unsourced) — the answer's Deep remark ("沒有外部旋鈕,系統是自己把自己推向奇異點") covers it anyway
- X10.2 — hit — "沒有系綜平均,沒有普適類…並不收斂"
- X10.3 — hit — "不同的 (t_c,ω) 組合常常給出幾乎一樣好的殘差"
- X10.4 — excluded (unsourced)
- Beyond rubric: derives LPPL from no-arbitrage plus hazard compensation, reads t_c as a hazard-rate peak rather than a clock, and proposes calibration / Brier score across many bubbles as the fair test.
- Biggest error: the citation "Predicting Financial Crashes Using Discrete Scale Invariance" is attached to IJTAF 3(2) 219–255 (2000). That venue holds JLS "Crashes as critical points"; the DSI title is the 1999 *J. Risk* paper. The answer flagged its citations as unverified.

### X11
- X11.1 — partial — "路徑依賴/遲滯…不同歷史路徑是否導致不同" (path dependence is named, but framed as shared with ferromagnet hysteresis rather than as a break from state-function equilibrium; update-scheme dependence is absent)
- X11.2 — partial — "令每個 domain 感受到的有效場是 H_i = H + δ_i" (a quenched random field gestures at pre-existing individual bias; no explicit committed-agent asymmetry vs symmetric paramagnet)
- X11.3 — partial — "網絡異質性殺掉「乾淨對齊」" (same conclusion via reactance / negative coupling; no few-opposed-fields-at-tipping-sites mechanism and no competing propagandas)
- X11.4 — partial — "僅借用其定性圖像,不需要精確移植" (implies a tool analogy; never says there are no measurable universal exponents or that it is not a physical isomorphism)
- Beyond rubric: separates field (tilts the double well, forcing a single domain) from temperature (removes the double well). That is a sharp point about alignment vs depolarization. Also names the multi-issue to one-dimension collapse as the real open question and gives three falsification tests.
- Biggest error: presents coercive-field thresholds, Barkhausen-like jumps and "永久" remanent scars as social facts carried over from ferromagnets. These are model-dependent imports with no social evidence, which is the over-transfer this trap probe is built to catch.

## Debate comparison (filled by Task 8)

Post-debate answer = original baseline answer as amended by `scratchpad/sdd/t8/Xnn-revision.md`. Each post-debate answer was graded against the same sourced items and the same strictness as the baseline. Items marked unsourced were still excluded.

| probe | alone score | debate score | real errors caught (objection → why it was a real error) | subagent runs |
|---|---|---|---|---|
| X01 | 0.25 | 0.50 | Insider O2 → costly-signaling rituals were misfiled as "marginal"; structural cost is a causal persistence factor (moves X01.2 to hit). Skeptic O1 → the k channels share demographic drivers, so a raw count overstates redundancy. Bridge O1 → the "irreversible extinction" wording contradicted the answer's own "deliberate revival" admission, and Josephson phase slips are not irreversible. Skeptic O3 → the shell/filling split was unfalsifiable after the fact. Insider O1 → the channel *type* (vertical/horizontal/oblique) matters, not only the count (this covers the excluded X01.1). | 5 |
| X05 | 0.88 | 0.88 | Bridge O1 → the D₀↔n_imp mapping ignored Anderson's theorem; non-magnetic disorder does not suppress T_c. Insider O1 → "online learning physically impossible" was false: commercial GMP runs Raman PAT at minute scale, so in-process monitoring is transferable and only release assays are slow. Insider O2 / Skeptic O3 → "vaccine" is not one black box: mRNA-LNP CQAs take hours to a day, and cell-line drift applies only to live-cell platforms. Skeptic O2 → SPC needs about 20–25 independent baseline subgroups, which contradicted the answer's own "tens of batches/yr". Skeptic O1 → the falsification test used a proxy signal whose correlation had not been validated. | 5 |
| X10 | 1.00 | 1.00 | Skeptic O1 → "super-exponential growth recurs before crashes" is hindsight selection; no blind crash vs non-crash comparison exists, so even the weak "risk dashboard" claim was unearned. Bridge O1 → t_c is one-sided and one-shot, while T_c can be approached repeatedly from both sides; the mapping table hid this. Bridge O2 → m↔β is formal only, since m has no order-parameter or symmetry-breaking origin. Insider O1 → the vague "long-running dispute" is really Feigenbaum vs Sornette–Johansen on the data window, and it carries straight into the proposed calibration test. Insider O2 → SADF/GSADF bubble tests were omitted. Skeptic O2 → exogenous stops (circuit breakers, margin calls) contaminate the fitted parameters. | 5 |

**Mean (these 3 probes):** alone 0.71 → debate 0.79 (exact 0.708 → 0.792). Total subagent runs: 15.

### Per-probe evidence — changed verdicts only
- X01.2 — partial → hit — "代價…作為誠實承諾訊號，能預測制度性存續延長" (revision Obj 7; costly signaling moved to relevant)
- No other rubric verdict changed. X01.3 (minimal counterintuitiveness) is still a miss. X05.3 (capacity / tech-transfer lead time of 2–3 mo vs 9–12 mo) is still partial: the revision re-splits the *feedback-loop* time constant (in-process vs release) but never addresses capacity scale-up lead time or tacit-knowledge transfer. X05.1/.2/.4 and X10.2/.3 remain hits.
- Unscored note: the revision's vertical/horizontal/oblique split (Insider O1) now covers the excluded X01.1.

**Verdict:** debate helps — modestly. The +0.08 mean comes entirely from one item (X01.2), where the Field-insider critic supplied the target-field literature the mentor lacked. X05 did not move and X10 was already at the ceiling.

**Worse or words-only:** X05 added about nine objections' worth of text without fixing its rubric gap (X05.3). Its new platform gap figures (10¹–10² for mRNA) are still anchored to the uncaught "秒級 fab loop" overstatement, and the new thresholds (R²≥0.7, ≥3 firms) are invented. X10 got worse in rigor on one point: an unverified *possibility* (λ non-stationary near t_c) was promoted to "第四個獨立成立的否定證據". Neither baseline "biggest error" was caught by the debate: the JLS citation title/venue mismatch in X10 is only re-flagged as "待查證", and the fab-loop overstatement in X05 is not addressed at all.
