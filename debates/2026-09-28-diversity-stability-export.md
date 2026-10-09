---
question: 生態學的「多樣性–穩定性」理論（May 1972）能不能直接回答：一個國家的出口產業越多元，經濟就越穩定？
route: full
confidence: high
card: C010
---

## Final answer
**不能直接用 May 的理論回答。May 說的是「交互耦合越多越不穩」，出口多元的穩定作用卻來自「組合平均」。實證上多元只在起點很集中時明顯有效。**

- May 判準需要交互作用正負號隨機；產業之間多是同號的上下游互補，這個判準在經濟體中沒有直接意義。
- 真正該算的是：總波動變異數比 = ρ̄ + (1−ρ̄)/n，ρ̄ 是各產業衝擊的平均相關。ρ̄≥0.6 時，產業數從 5 增到 20，波動只從 0.68 降到 0.62。
- 實證：低度多元時有效，中高度後效果遞減 [1][2][3]；企業層級也只在部分情況有效 [5]。
- 對台灣這類電子業集中的經濟，關鍵不是「產業數」，而是新產業的衝擊能否和主力產業不相關，以及樞紐產業的份額（顆粒度）。

## Final conclusion
- 主張: May 的多樣性–穩定性判準不適用出口多元（號結構不同）；出口多元的穩定作用是組合平均，其效果由衝擊相關 ρ̄ 與樞紐份額決定，實證上只在低度多元時明顯。
- 推理步驟: 1. May 判準需隨機號矩陣 2. 經濟耦合為同號互補 3. 組合平均 Var 比 = ρ̄+(1−ρ̄)/n 4. 顆粒度使衝擊不平均 5. 實證遞減且需處理內生性
- 因子分類: relevant: 衝擊相關 ρ̄、樞紐份額、起始多元程度 / marginal: 產業數 / irrelevant: 出口目的地數量
- 使用招式: M9, M3, M4
- 跨域橋接: 生態群落 ↔ 出口產業 · 未映射: 隨機正負號、捕食關係 · 斷點: 經濟耦合為有結構的同號互補
- 自評信心: medium

**Confidence: high**

## Objection ledger
| # | role | objection | severity | outcome (conceded/refuted/open) |
|---|---|---|---|---|
| O1 | Skeptic | 多元與穩定的相關可能是反向因果：本來就穩定、富裕的國家才養得起多元產業。若不處理這點，「多元 → 穩定」的方向本身就未證實。 | major | conceded — 加註：Balavac 等以處理內生性的設定仍得到低度多元時有效 [1]；其餘相關研究只當方向性證據。 |
| O2 | Bridge auditor | May 假設交互作用的正負號隨機；產業間的投入產出關係大多是同號的互補（上游好、下游也好）。有結構的矩陣（例如捕食–被捕食型）會改變穩定判準，所以 σ√(SC) 在經濟體中沒有直接意義。 | major | conceded — 標明 May 判準需要隨機正負號，產業耦合改用有結構的生產網路分析。 |
| O3 | Practitioner | 政策制定者要知道：多加一個產業到底能降多少波動？1/n 只在衝擊完全獨立時成立；台灣這類電子業高度集中的經濟，產業衝擊高度相關，1/n 會嚴重高估效果。 | major | conceded — 改用 Var 比 = ρ̄ + (1−ρ̄)/n（ρ̄ 為平均兩兩相關）；ρ̄≥0.6 時，產業數從 5 增到 20 只把波動變異數從 0.68 降到 0.62。 |
| O4 | Field insider | 總體經濟學的原生工具是生產網路與顆粒假說：若網路有主導性的樞紐產業或巨型企業，個別衝擊不會平均掉（Acemoglu 等 2012；Gabaix 2011）。經濟複雜度指標（ECI）也是現成的多元化量尺 [4]。 | major | conceded — 加入顆粒度：樞紐產業或巨型企業的份額決定衝擊能否平均掉。 |

## Draft → final diff
- 加註內生性處理，其餘研究只當方向性證據 (O1)
- 標明 May 判準需隨機號矩陣 (O2)
- 以含相關性的變異公式取代 1/n (O3)
- 加入顆粒度與生產網路 (O4)

## Open objections
（無）

## Live sources (connectors, fetched 2026-09-28)
[1] Balavac & Pugh 2016 Economic Systems — 25 個轉型經濟體：出口多元只在低度多元時降低開放帶來的產出波動 <https://consensus.app/papers/details/57bf1d9cd9cf593c806eebce30bb9557/>
[2] Lee & Zhang 2019 IMF Working Paper — 低所得國與小國：出口多元促進成長、降低波動 <https://consensus.app/papers/details/5150ec8edfbf559989ed496cb8b2d0ee/>
[3] Hesse 2008 World Bank — 多元化對成長的效果可能非線性，最先進經濟體反而專業化較佳 <https://consensus.app/papers/details/37ff3ad44345547a9a39a7ef93d20416/>
[4] Breitenbach et al. 2022 — 經濟複雜度（ECI）提高可降低高所得國的產出波動 <https://consensus.app/papers/details/1c11e0788bd4599a80d47aa9be00599c/>
[5] Čede et al. 2018 Review of World Economics — 企業層級：出口多元只在部分情況降低波動 <https://consensus.app/papers/details/2e545c1db0955f858f244a7553a15bad/>

## Draft (mentor, before critics)
**不能直接套用：May 的結果剛好相反——隨機系統越多元、耦合越強越不穩；出口多元的穩定作用來自「組合平均」，是另一個機制。**

- May（1972）：隨機群落矩陣只有在 $\sigma\sqrt{SC}<1$ 時穩定，物種數 S、連結度 C 越大越不穩。
- 出口多元：若各產業衝擊互相獨立，總波動變異數約 ∝ 1/n，多元自然降低波動，這是投資組合的平均效應。
- 實證：多元在低度時有效，中高度後效果遞減 [1][2][3]。
- 映射：S ↔ 出口產業數，C ↔ 產業間投入產出連結，σ ↔ 連結強度。

## 結論草稿
- 主張: May 的多樣性–穩定性理論不能直接回答出口多元問題；出口多元的穩定來自組合平均，且實證上只在低度多元時有效。
- 推理步驟: 1. May 判準 σ√(SC)<1 2. 組合平均使變異 ∝ 1/n 3. 兩機制方向相反 4. 實證為遞減效果
- 因子分類: relevant: 衝擊相關性、產業耦合 / marginal: 產業數 / irrelevant: 出口目的地數量
- 使用招式: M9, M3
- 跨域橋接: 生態群落 ↔ 出口產業體系（S、C、σ 對應） · 未映射: 無 · 斷點: 無
- 自評信心: medium

## Critic outputs
### Skeptic
OBJECTION 1
- type: alternative
- target step: 實證為遞減效果
- failure case: 多元與穩定的相關可能是反向因果：本來就穩定、富裕的國家才養得起多元產業。若不處理這點，「多元 → 穩定」的方向本身就未證實。
- severity: major
- would resolve it: 說明文獻如何處理內生性（工具變數），並把結論限定在有處理內生性的研究。

### Bridge auditor
OBJECTION 1
- type: mis-mapping
- target step: S、C、σ 對應
- failure case: May 假設交互作用的正負號隨機；產業間的投入產出關係大多是同號的互補（上游好、下游也好）。有結構的矩陣（例如捕食–被捕食型）會改變穩定判準，所以 σ√(SC) 在經濟體中沒有直接意義。
- severity: major
- would resolve it: 標明 May 判準只適用隨機號矩陣，經濟耦合要用有結構的網路模型。

### Practitioner
OBJECTION 1
- type: missing-threshold
- target step: 組合平均使變異 ∝ 1/n
- failure case: 政策制定者要知道：多加一個產業到底能降多少波動？1/n 只在衝擊完全獨立時成立；台灣這類電子業高度集中的經濟，產業衝擊高度相關，1/n 會嚴重高估效果。
- severity: major
- would resolve it: 給出含相關性的公式，並說明何時多元化幾乎無效。

### Field insider
OBJECTION 1
- type: missing-field-knowledge
- target step: 組合平均
- failure case: 總體經濟學的原生工具是生產網路與顆粒假說：若網路有主導性的樞紐產業或巨型企業，個別衝擊不會平均掉（Acemoglu 等 2012；Gabaix 2011）。經濟複雜度指標（ECI）也是現成的多元化量尺 [4]。
- source: none
- severity: major
- would resolve it: 以網路集中度與顆粒度取代單純產業數。

## Process note
Run from Claude Code on 2026-09-28 following the app pipeline (index check → connector research → mentor draft → 4 critics → concede/refute revision → round 2 for refuted fatal → fixed confidence rule). The four critics were written in one session one after another, not as independent blind calls.
