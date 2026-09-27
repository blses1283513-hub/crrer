tags: [Lin-Hsiu-Hau, debate-round2, X10, skeptic]
created: 2026-09-27
question: 股市崩盤像相變/臨界現象，所以可以用臨界指數預測崩盤時間吧？
scope: delta only — claims/numbers/thresholds/operational definitions/causal statements in the REVISION (X10-revision.md) not present in the ORIGINAL draft (X10.md)

---

## New claims in REVISION not in ORIGINAL (numbered)

1. Branching ratio λ may be non-stationary as t→t_c, contaminating ω and t_c estimates — promoted to a **fourth, independent** falsifying reason (alongside no-ensemble, parameter degeneracy, need-for-out-of-sample-test), explicitly framed as "even if the other three were refuted, this one alone still holds."
2. Premature termination is reframed as having two distinct mechanisms: **endogenous** (herding-network stochastic collapse, theory-consistent) vs **exogenous** (circuit breakers / margin calls / central-bank intervention triggered at fixed thresholds); fits must first separate samples by circuit-breaker regime (e.g., pre/post-1987 US circuit breakers) before claiming an endogenous LPPL signal.
3. t_c is a **one-sided, non-repeatable** event (post-crash the system is a new dynamical realization), unlike T_c which is **bidirectionally, repeatedly approachable** — the correspondence table must add an "approachability" column marking this asymmetry.
4. m↔β is only a **formal/nominal analogy**: β derives from spontaneous symmetry breaking + universality class (independent of measurement method); m is a bare fitting exponent on price itself with no independent physical definition. This must be labeled at first table presentation, not deferred to §3.
5. New **operational criterion** for "super-exponential vs exponential+noise": a likelihood-ratio test comparing pure exponential growth (GBM+drift) against the LPPL skeleton, with a pre-registered significance threshold (e.g., p<0.01).
6. The "protected" claim that herding-driven super-exponential acceleration recurs before crashes is **downgraded to an unverified hypothesis**, because supporting evidence is entirely hindsight-fitted — no blind, pre-registered comparison of crash-group vs non-crash-group super-exponential incidence rates has ever been run.
7. Concrete **executable thresholds** for the calibration/Brier-score test: N ≥ 15 independent historical bubbles; out-of-sample Brier score improvement ≥ 10% relative to a constant-hazard-rate baseline; the t_c-fitting cutoff window must be pre-registered before testing.
8. The fitting cutoff date must be **strictly frozen to a point before the actual crash** and must not be shifted later using hindsight knowledge of the true crash date — tied explicitly to the Feigenbaum vs. Sornette–Johansen (2001) data-window dispute (Feigenbaum removed the last pre-crash year; Sornette–Johansen call this a methodological error for a near-critical-point analysis).
9. Specific citation-content claim + verification-status update: Sornette & Johansen (2001, *Quantitative Finance* 1(4), 452–471, **arXiv:cond-mat/0106520**) is described as a direct rebuttal to Feigenbaum, and this arXiv ID is reported as **cross-verified against the abstract by a reviewer this round** (JLS 2000 and the Phillips series remain unverified).
10. New independent corroborating citation claim: mainstream econometric bubble-detection tools (**Phillips–Wu–Yu 2011; Phillips–Shi–Yu SADF/GSADF 2015**), unrelated to critical-phenomena physics, are said to **independently converge** on the same conclusion — detecting "explosive persistence," not a precise crash time.
11. The hierarchical-lattice/RG cross-domain bridge claim ("是同一件事") is walked back to "**same mathematical form only**" — financial λ is backward-inferred from the same single fit with no independently measured, forward-derivable, falsifiable branching structure (unlike the lattice model), so it cannot be used for forward prediction or independent validation.
12. Revised conclusion **splits confidence**: claim (a) "cannot predict precise date" now rated medium-high (four independent reasons said to converge); claim (b) "usable as a probabilistic risk gauge" now rated low, pending the unresolved fatal objection. A new explicit claim asserts the (a)-chain and (b)-chain of evidence are **logically independent** of each other.

---

## SKEPTIC role output (objections restricted to the new claims above only)

OBJECTION 1
- target step: claim #1 — "λ在 t→t_c 附近可能非定態…併入第 3 節的『參數簡併』理由,升格為第四個獨立成立的否定證據…即使前三個理由某天都被反駁,這一條單獨也夠"
- failure case: run a Monte Carlo check — simulate LPPL price paths with a genuinely *constant* λ, but with the same short, noisy pre-crash fitting window used in real data. Estimation noise on a short window will itself produce apparent drift in the fitted λ(t) even when the true generating process has no non-stationarity at all. If that is what is driving the "non-stationary λ" observation in real fits, then item #1 is not a mechanism independent of item (b) parameter degeneracy/overfitting — it is the same small-sample estimation pathology counted twice. The "any one alone suffices" redundancy claim is exactly what breaks: two of the four "independent" pillars would in fact be correlated symptoms of one underlying weakness (short noisy windows), not four separable lines of evidence.
- severity: major
- would resolve it: a Monte Carlo/bootstrap study fitting LPPL to simulated series with a fixed, known λ under realistic pre-crash sample sizes and noise levels — if apparent λ non-stationarity appears even when the true λ is constant, items (b) and (1) must be merged into one reason, not counted as two independent ones.

OBJECTION 2
- target step: claim #7 — "$N\ge15$ 個獨立歷史泡沫、樣本外 Brier score 相對常數風險率基準線改善 $\ge10\%$…三者缺一視為未過測試"
- failure case: the population of well-documented, price-clean, consensus-labeled major bubbles is small (roughly 1929, 1987, 2000, 2008, 1990 Japan, 2015 China, a handful of others) and many of them are not statistically independent draws — 2008 propagated through correlated global markets, and several "separate" national bubbles shared the same macro liquidity cycle. Treating these as N≥15 *independent* samples for a Brier-score aggregate would violate the independence assumption the score's variance estimate relies on, so a test built exactly as specified either (i) cannot currently be run for lack of enough truly independent cases, or (ii) if forced to run on correlated cases labeled as independent, can produce a spuriously "passing" or "failing" Brier score due to shared error structure rather than genuine calibration skill.
- severity: major
- would resolve it: an explicit accounting of how many statistically independent (not merely chronologically distinct) bubble episodes actually exist in usable price data, plus a correlation-adjusted variance estimator for the aggregate Brier score (e.g., block bootstrap over correlated crisis clusters) before the N≥15/≥10% rule is treated as an executable, falsifiable test rather than an aspirational target.

OBJECTION 3
- target step: claim #10 — "SADF/GSADF…物理無關卻同樣得出『偵測爆炸持續性,而非精確報時』的結論,兩條獨立證據路徑收斂,反而加固而非削弱主結論"
- failure case: construct a smooth, purely super-exponential (non-log-periodic) synthetic bubble with no hierarchical herding structure, no discrete scale invariance, and no complex critical exponent at all. Such a series would still trigger a GSADF explosive-root rejection, because GSADF only tests "faster-than-a-given-null-process growth," not the specific LPPL apparatus (m, ω, λ, log-periodic oscillation). So GSADF "agreeing" that timing can't be pinned down corroborates only the trivial claim that nobody disputed (bubbles are hard to time), while being silent on — not convergent with — the paper's actual mechanistic content. Calling this a second "independent evidence path" for the critical-phenomena framing overstates what an orthogonal, mechanism-agnostic test can certify.
- severity: minor
- would resolve it: show that GSADF's explosive-root detections and LPPL's log-periodic parameter estimates are correlated across a shared sample in a way that discriminates LPPL-type bubbles from generic explosive-but-non-periodic ones — otherwise keep the SADF/GSADF citation as background risk-management context, not as convergent corroboration of the critical-phenomena mechanism.

NONE beyond these three survive the "concrete failure case" bar within scope — several other new claims (items #2, #3, #4, #6, #8, #9, #12) are self-conceded downgrades or added qualifiers that make the revision *more* conservative, not new exposure, so no further objection is listed against them under this round's scope.
