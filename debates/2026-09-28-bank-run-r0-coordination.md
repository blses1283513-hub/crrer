---
question: 銀行擠兌能不能用傳染病的 R0 門檻來描述？2023 年矽谷銀行擠兌的「R0」大概多少，這個類比在哪裡會斷？
route: full
confidence: medium
card: C006
---

## Final answer
**不適合用 R0 描述門檻；R0 只能當「傳得多快」的比喻。擠兌是協調賽局：基本面一跌破臨界值，所有人同時跳到「搶先提領」的均衡。**

- SVB 的速度：3/9 一天流出逾 $40B，約四分之一存款，隔天預期再 $100B [1][4]；對照 Wachovia 2008 約 8 天流出 $10B [2]。R 值無法從這些資料識別，所以不給。
- 類比在三處斷掉：存戶是策略互補（別人領，我更該領），不是被動感染；沒有康復；全額存款保障是直接移除壞均衡，所以 2023/3/12 宣布後擠兌立刻停，而不是慢慢降溫。
- 真正的門檻工具是 global games：基本面低於 θ* 才會擠兌。社群媒體 [3] 改變的是「均衡跳躍」的速度，不是門檻位置。
- 可每天監看的指標：高度相關的未保險存款 ÷ 當日可動用流動性。比值 >1 即高風險，SVB 約九成存款未受保險 [2]。

## Final conclusion
- 主張: 銀行擠兌的門檻是協調賽局（global games）的基本面臨界值，不是 R0>1；R0 只可比喻傳播速度，SVB 資料無法識別 R 值。
- 推理步驟: 1. 擠兌 = 策略互補的雙重均衡 2. global games 給唯一門檻 θ* 3. 存款保障移除壞均衡，解釋 3/12 後立即止擠兌 4. 社群媒體加快均衡跳躍 5. 脆弱度比值作為每日門檻
- 因子分類: relevant: 未保險且相關的存款、可動用流動性、基本面雜訊 / marginal: 社群媒體速度 / irrelevant: 分行數
- 使用招式: M9, M3, M6
- 跨域橋接: 擠兌 ↔ SIR · 未映射: 策略互補、康復 · 斷點: 均衡跳躍 vs 漸進爆發；保險移除均衡而非降低傳播率
- 自評信心: medium

**Confidence: medium** (unreviewed-revision rule: 脆弱度比值 >1 為高風險的具體門檻未經其他 critic 複審)

## Objection ledger
| # | role | objection | severity | outcome (conceded/refuted/open) |
|---|---|---|---|---|
| O1 | Skeptic | R 需要世代間隔與逐代新增人數；手上只有一條日總量曲線和一個「隔天預期」數字，同一條曲線可由 R=1.5 配短世代、或 R=5 配長世代產生。這個 2–3 是無法識別的參數，寫進結論會被當成測量值。 | major | conceded — 撤下 R≈2–3，改用可觀測的流出速度：一天流出約四分之一存款。 |
| O2 | Bridge auditor | Diamond–Dybvig 擠兌是協調賽局的雙重均衡：只要預期別人會領，自己先領就是最適；它是整體跳到壞均衡（fold 式跳躍），不是 R>1 的漸進爆發。存款全額保障移除的是壞均衡本身，而不是降低傳播率——2023/3/12 宣布全額保障後擠兌立刻停止，這用「疫苗降低易感者」解釋不了速度。 | fatal | conceded — 核心機制改為協調賽局與均衡跳躍，R0 降為速度比喻。 |
| O3 | Bridge auditor | SIR 有康復與免疫；擠兌沒有對應物，領走的錢不會「康復」回來，而且提領者的報酬取決於別人是否提領（策略互補），感染者的健康不取決於別人是否感染。 | major | conceded — 映射表標出無康復、策略互補兩項未映射。 |
| O4 | Practitioner | 監理機關要的是「哪家銀行現在脆弱」的門檻。SVB 約九成存款未受保險、集中在同一產業網路 [2]；草稿沒有把這種結構變成可每天計算的指標。 | major | conceded — 加入脆弱度比值：高度相關的未保險存款 ÷ 當日可動用流動性（含貼現窗口額度），>1 即高風險。 |
| O5 | Field insider | 金融學處理擠兌門檻的原生工具是 global games（Morris–Shin 1998；Goldstein–Pauzner 2005）：在基本面有雜訊時，雙重均衡收斂成唯一門檻 θ*，基本面低於 θ* 就擠兌。草稿用流行病模型重新發明了一個較差的門檻。 | major | conceded — 門檻改用 global games 的基本面臨界值 θ*。 |

## Draft → final diff
- 撤下 R≈2–3 的估算 (O1)
- 核心機制改為協調賽局與均衡跳躍，R0 降為速度比喻 (O2)
- 映射表標出策略互補、無康復兩項未映射 (O3)
- 加入每日可算的脆弱度比值 (O4)
- 門檻改用 global games 的 θ* (O5)

## Open objections
（無）
- unreviewed: 脆弱度比值 >1 為高風險的具體門檻未經其他 critic 複審

## Live sources (connectors, fetched 2026-09-28)
[1] Federal Reserve, Review of the Supervision and Regulation of SVB (2023-04-27) — 3/9 流出逾 $40B，管理層預期 3/10 再流出 $100B；社群媒體與高度網路化、集中的存戶改變了擠兌速度 <https://www.federalreserve.gov/publications/files/svb-review-20230428.pdf>
[2] Fed Executive Summary — 相關性提領來自集中的創投與科技公司網路；Wachovia 2008 約 8 天流出 $10B <https://www.federalreserve.gov/publications/2023-April-SVB-Executive-Summary.htm>
[3] Cookson et al., Social Media as a Bank Run Catalyst (FDIC 研討會論文) — 推特上的存戶溝通助長擠兌 <https://www.fdic.gov/analysis/cfr/bank-research-conference/annual-22nd/papers/cookson-paper.pdf>
[4] Fortune 2023-03-11 — 單日 $42B <https://fortune.com/2023/03/11/silicon-valley-bank-run-42-billion-attempted-withdrawals-in-one-day>

## Draft (mentor, before critics)
**可以用 R0 描述，SVB 的 R0 大約 2–3；把 R0 壓到 1 以下（溝通與安撫）就能止住擠兌。**

- 映射：每位提領的存戶透過社群「感染」R 位存戶跟進；R0>1 就爆發。
- SVB 估算：3/9 單日流出逾 $40B，約占存款四分之一，隔天預期再 $100B [1][4]。以數小時為一個世代、流出量約每世代翻倍，R 約 2–3。
- 斷點：存款保險像疫苗，降低易感者比例。
- 對策：降低 R（安撫溝通、暫停提領）。

## 結論草稿
- 主張: 銀行擠兌可用 R0 門檻描述，SVB 的 R0 約 2–3，壓低 R0 即可止擠兌。
- 推理步驟: 1. 存戶 ↔ 易感者 2. 由流出速度估 R≈2–3 3. 存款保險 ↔ 疫苗 4. 對策為降低傳播率
- 因子分類: relevant: 傳播速度、未保險存款比例 / marginal: 社群媒體 / irrelevant: 分行數
- 使用招式: M9, M6
- 跨域橋接: 擠兌 ↔ SIR 傳染 · 未映射: 存戶的策略判斷 · 斷點: 未標出
- 自評信心: medium

## Critic outputs
### Skeptic
OBJECTION 1
- type: number
- target step: 由流出速度估 R≈2–3
- failure case: R 需要世代間隔與逐代新增人數；手上只有一條日總量曲線和一個「隔天預期」數字，同一條曲線可由 R=1.5 配短世代、或 R=5 配長世代產生。這個 2–3 是無法識別的參數，寫進結論會被當成測量值。
- severity: major
- would resolve it: 撤下 R 數值，改用可觀測量（小時級流出、社群貼文時序）描述速度。

### Bridge auditor
OBJECTION 1
- type: past-break-point
- target step: 對策為降低傳播率
- failure case: Diamond–Dybvig 擠兌是協調賽局的雙重均衡：只要預期別人會領，自己先領就是最適；它是整體跳到壞均衡（fold 式跳躍），不是 R>1 的漸進爆發。存款全額保障移除的是壞均衡本身，而不是降低傳播率——2023/3/12 宣布全額保障後擠兌立刻停止，這用「疫苗降低易感者」解釋不了速度。
- severity: fatal
- would resolve it: 把核心機制改成策略互補的協調賽局，R0 只保留為速度的比喻。
OBJECTION 2
- type: unmapped
- target step: 擠兌 ↔ SIR
- failure case: SIR 有康復與免疫；擠兌沒有對應物，領走的錢不會「康復」回來，而且提領者的報酬取決於別人是否提領（策略互補），感染者的健康不取決於別人是否感染。
- severity: major
- would resolve it: 在映射表標出這兩項未映射。

### Practitioner
OBJECTION 1
- type: missing-threshold
- target step: 對策
- failure case: 監理機關要的是「哪家銀行現在脆弱」的門檻。SVB 約九成存款未受保險、集中在同一產業網路 [2]；草稿沒有把這種結構變成可每天計算的指標。
- severity: major
- would resolve it: 給一個比值：集中且相關的未保險存款 / 當日可動用流動性。

### Field insider
OBJECTION 1
- type: reinvented-tool
- target step: R0 門檻
- failure case: 金融學處理擠兌門檻的原生工具是 global games（Morris–Shin 1998；Goldstein–Pauzner 2005）：在基本面有雜訊時，雙重均衡收斂成唯一門檻 θ*，基本面低於 θ* 就擠兌。草稿用流行病模型重新發明了一個較差的門檻。
- source: none
- severity: major
- would resolve it: 以 global games 門檻取代 R0 門檻。

## Process note
Run from Claude Code on 2026-09-28 following the app pipeline (index check → connector research → mentor draft → 4 critics → concede/refute revision → round 2 for refuted fatal → fixed confidence rule). The four critics were written in one session one after another, not as independent blind calls.
