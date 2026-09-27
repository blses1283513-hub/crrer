---
role: field-insider (round 2 re-check)
question: 股市崩盤像相變/臨界現象，所以可以用臨界指數預測崩盤時間吧？
scope: delta only — factual/empirical claims, citations, numbers or thresholds in the REVISION not present in the ORIGINAL draft
sources checked: WebSearch only (no verification/ subfolder opened)
---

## New factual claims in the REVISION (not in the original draft)

1. **Phillips–Wu–Yu (2011)**, *International Economic Review* 52(1):201–226, "Explosive Behavior in the 1990s Nasdaq: When Did Exuberance Escalate Asset Values?" — cited as an explosive-root/right-tailed unit-root bubble-detection method, independent of LPPL/critical-phenomena framework.
2. **Phillips–Shi–Yu (2015), GSADF**, *International Economic Review* 56(4):1043–1078, "Testing for Multiple Bubbles: Historical Episodes of Exuberance and Collapse in the S&P 500" — cited as the mainstream econometric alternative that "converges" with the LPPL conclusion.
3. Specific **arXiv ID for Sornette & Johansen (2001)**: arXiv:cond-mat/0106520 (the original draft cited the journal reference only, no arXiv ID).
4. **Feigenbaum critique content**, newly spelled out: Feigenbaum removed the last year of pre-1987-crash data (≈15% of the data, the segment closest to the critical point) and found the log-periodic signal no longer significant at 95% confidence; Sornette & Johansen's rebuttal is characterized as calling this a methodological error ("analyzing a critical-point phenomenon while cutting the data nearest the critical point") — i.e., a data-window / look-ahead-bias dispute.
5. Numeric verification threshold: **N ≥ 15** independent historical bubble samples required for the proposed calibration test.
6. Numeric verification threshold: out-of-sample **Brier-score improvement ≥ 10%** over a constant-risk-rate baseline.
7. Numeric verification threshold: **p < 0.01** significance level for a likelihood-ratio test distinguishing pure exponential growth (GBM+drift) from the LPPL/finite-time-singularity model.
8. Claim that US stock-market **circuit breakers (熔斷) post-date the 1987 crash**, used to argue 1987-onward fits need to separate endogenous herding dynamics from exogenous rule-triggered halts.
9. Meta-claim about citation-verification status itself: Sornette & Johansen (2001) is now marked as cross-checked against the arXiv abstract this round and "content matches"; Johansen–Ledoit–Sornette (2000) and the Phillips papers are marked as *not* checked this round, still pending user verification.

(Claims 5–7 are internally stipulated test-design thresholds, not assertions sourced from a published paper — flagged for completeness but not independently fact-checkable against a source.)

---

## Objections

OBJECTION 1
- type: missing-field-knowledge
- target step: "加一段明講 SADF/GSADF 是主流替代框架...兩條獨立證據路徑收斂,反而加固而非削弱主結論" (revision §7 / Insider O2 rebuttal)
- failure case: The revision presents Phillips–Shi–Yu (2015) GSADF as a clean, methodologically independent confirmation that only "detects explosive persistence, not a precise crash date." It omits that the SADF/GSADF test family has its own well-documented reliability problems under realistic financial data: substantial size distortion under leverage effects/(T)GARCH errors and under serially correlated innovations, and low power — one review reports over 40% of existing bubbles going undetected in a majority of tested scenarios. Citing GSADF as an unqualified second, independent line of convergent evidence overstates how clean that convergence is; a financial econometrician would immediately ask "under what data-generating process, and with what size/power, was this GSADF result obtained?"
- source: https://ideas.repec.org/p/cqe/wpaper/7819.html ("Sup-ADF-style bubble-detection methods under test" — documents size distortion under leverage effects/TGARCH and autocorrelated innovations, and power failures for flexible bubble shapes)
- severity: major
- would resolve it: Add one clause acknowledging GSADF's own documented size-distortion/power limitations (cite a methodological review), and reframe the "two independent paths converge" claim as "two imperfect methods both fail to deliver point predictions" rather than implying GSADF is a clean, unqualified confirmation.

OBJECTION 2
- type: factual
- target step: "它偵測的是「極端持續性的爆炸區間」,不是精確崩盤時間點" (revision §7, describing what Phillips–Wu–Yu / Phillips–Shi–Yu actually output)
- failure case: This understates what the cited papers themselves claim to do. Phillips–Wu–Yu (2011)'s own abstract states the method provides "date-stamping the origination and collapse of economic exuberance" — i.e., it does produce specific dates for both bubble start and bubble end, not merely a persistence interval. Phillips–Shi–Yu (2015) extends this date-stamping to multiple-bubble settings. The distinction the revision needs is not "interval vs. no date" but "retrospective date-stamping of a completed episode vs. a forward-looking prediction of one specific future date" — the current wording blurs exactly the axis the whole argument turns on.
- source: https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1468-2354.2010.00625.x (Phillips–Wu–Yu 2011 abstract: "date stamps the origination and collapse of economic exuberance")
- severity: minor
- would resolve it: Replace "偵測爆炸區間,不是精確時間點" with something like "GSADF/SADF 也做日期標定,但只能事後標定已完成的爆炸/崩解區間,不能在崩盤發生前就鎖定一個未來確切日期" — keeps the core point (no forward point-prediction) but stops mischaracterizing the tool's own stated output.

Politics/positions: n/a (finance/econometrics content only, mechanisms and evidence).
