---
question: 動物的代謝率跟體重呈 3/4 次方標度（Kleiber 定律），公司越大創新越慢——能不能用同一套標度理論預測企業壽命？
route: full
confidence: high
card: C012
---

## Final answer
**不能。生物標度理論的前提在公司身上不存在，而且公司的死亡方式和生物不同：上市公司的死亡率與年齡幾乎無關，半衰期約十年 [1]。**

- 為什麼不能套：3/4 律來自充滿空間的輸送網路，公司沒有這種結構，連「公司的體重」該用營收還是員工都無法定義。
- 上市公司：死亡率近似常數，約每年 7%，10 年剩一半、20 年剩四分之一 [1]。但這個「死亡」包含被併購，不全是失敗。
- 全體企業不一樣：英國 1998 年成立的公司 15 年內死掉 90% [2]；風險在成立後 1–15 年最高 [4]，老公司也可能再上升 [3]。
- 要預測單一公司：用含規模、獲利、產業成長的存活模型。5 人以上的公司，隔年死亡機率約為小公司的一半 [2]。

## Final conclusion
- 主張: Kleiber 式標度理論不能預測企業壽命：推導前提在公司端不存在，上市公司死亡率近似常數（半衰期約十年、含併購），全體企業則呈年齡依賴的倒 U 風險；個體預測應用含共變數的存活模型。
- 推理步驟: 1. 3/4 律需空間填充網路 2. 公司無此前提 3. 上市公司常數死亡率（含併購） 4. 組織生態學的倒 U 風險 5. 個體用含共變數存活模型
- 因子分類: relevant: 死亡定義（破產/併購）、年齡依賴風險、規模與獲利 / marginal: 產業別 / irrelevant: 公司名稱
- 使用招式: M3, M5, M4
- 跨域橋接: 公司 ↔ 生物體 · 未映射: 空間填充網路、公司質量定義 · 斷點: 推導前提不存在，公司標度只能實證擬合
- 自評信心: high

**Confidence: high**

## Objection ledger
| # | role | objection | severity | outcome (conceded/refuted/open) |
|---|---|---|---|---|
| O1 | Skeptic | 該研究把併購也算成「死亡」[1]。被高價收購的成功公司和破產公司算同一種死亡，λ≈0.07 混了兩種完全相反的結局；用它預測「企業壽命」會把成功退場也當失敗。 | major | conceded — 註明 λ 含併購；預測「失敗」時要用破產風險，不能用總死亡率。 |
| O2 | Skeptic | 另一組資料顯示公司死亡率早期下降、20–30 年後依 Gompertz 上升，和人類死亡曲線形狀相似 [3]。「無老化」可能只是觀察窗或樣本（上市公司）的結果。 | major | conceded — 「無老化」限定為上市公司樣本；新創與全體企業另有倒 U 或 Gompertz 型態。 |
| O3 | Bridge auditor | 3/4 律的推導需要充滿空間、末端單元大小固定的分支網路；公司的「質量」該用營收、員工或資產並不確定，而且數位業務沒有空間填充限制。推導前提在公司端不存在，所以連「代謝 ↔ 營運支出」這個映射都沒有根據。 | major | conceded — 標明 3/4 律的推導前提在公司端不存在，公司的標度只能當實證擬合。 |
| O4 | Practitioner | 投資人或經營者要的是「這家公司」的風險，群體半衰期幫不上忙。現有的存活分析可以加入規模、獲利、產業成長等共變數 [2]，草稿沒提。 | minor | conceded — 加入：個體風險用含規模、獲利的存活模型；群體半衰期只作基線。 |
| O5 | Field insider | 組織生態學早有「新生負擔」與「青春期負擔」：死亡風險在成立後 1–15 年呈倒 U 型 [4]。這是研究企業死亡的原生理論，草稿直接從物理出發略過了。 | major | conceded — 改以組織生態學的年齡依賴風險為主框架，上市公司常數率只是其中一段。 |

## Draft → final diff
- 註明死亡率含併購 (O1)
- 「無老化」限定在上市公司樣本 (O2)
- 標明 3/4 律前提不存在 (O3)
- 個體風險改用含共變數存活模型 (O4)
- 改以組織生態學倒 U 風險為主框架 (O5)

## Open objections
（無）

## Live sources (connectors, fetched 2026-09-28)
[1] Daepp et al. 2015 J. R. Soc. Interface, The mortality of companies — 25,000+ 家北美上市公司（1950–2009）：死亡率近似常數、與公司年齡無關；半衰期約十年，不分產業 <https://consensus.app/papers/details/9d709058ffe250eb8f862a3d8bf2ddb5/>
[2] Anyadike-Danes & Hart 2018 J. Evolutionary Economics — 1998 年出生的 23.9 萬家英國公司，15 年內 90% 死亡；5 人以上公司隔年死亡機率約為小公司的一半 <https://consensus.app/papers/details/e0fe1e9d830c5595a351011613ff1b9d/>
[3] Richmond et al. 2022 Entropy — 公司死亡率早期雙曲下降，約 20–30 年後依 Gompertz 上升 <https://consensus.app/papers/details/cf44df1bc1445411a865663e34ef0f57/>
[4] Brüderl & Schüssler 1990 ASQ — 「青春期負擔」：死亡風險在成立後 1–15 年間呈倒 U 型 <https://consensus.app/papers/details/f1b63ad16ec45f84b972b8fe1e15cabb/>

## Draft (mentor, before critics)
**不能。生物壽命隨體重 $M^{1/4}$ 增加，是因為生物會「老化」；上市公司的死亡率卻和年齡無關，半衰期約十年 [1]。**

- 生物：代謝 $B\propto M^{3/4}$ 來自充滿空間的分支輸送網路；壽命 $\propto M^{1/4}$。
- 公司：死亡率近似常數，λ = ln2/10 ≈ 0.07/年，與年齡、產業無關 [1]。常數死亡率代表沒有老化，所以不會出現 $M^{1/4}$ 的壽命標度。
- 能預測的是群體：一批上市公司 10 年後約剩一半、20 年後約剩四分之一；不能預測單一公司。

## 結論草稿
- 主張: 生物標度理論不能預測企業壽命：上市公司死亡率近似常數（半衰期約十年、λ≈0.07/年），沒有老化，因此只能做群體存活預測。
- 推理步驟: 1. 生物 3/4 律與壽命 1/4 律 2. 上市公司常數死亡率 3. 常數死亡率 ↔ 無老化 4. 群體存活曲線 e^{−λt}
- 因子分類: relevant: 死亡率是否隨年齡改變 / marginal: 產業別 / irrelevant: 公司名稱
- 使用招式: M3, M5, M4
- 跨域橋接: 公司 ↔ 生物體（規模 ↔ 體重、營運支出 ↔ 代謝） · 未映射: 無 · 斷點: 公司死亡率不隨年齡上升
- 自評信心: medium

## Critic outputs
### Skeptic
OBJECTION 1
- type: bias
- target step: 上市公司常數死亡率
- failure case: 該研究把併購也算成「死亡」[1]。被高價收購的成功公司和破產公司算同一種死亡，λ≈0.07 混了兩種完全相反的結局；用它預測「企業壽命」會把成功退場也當失敗。
- severity: major
- would resolve it: 把死亡拆成破產與併購兩種風險分別報告。
OBJECTION 2
- type: evidence
- target step: 無老化
- failure case: 另一組資料顯示公司死亡率早期下降、20–30 年後依 Gompertz 上升，和人類死亡曲線形狀相似 [3]。「無老化」可能只是觀察窗或樣本（上市公司）的結果。
- severity: major
- would resolve it: 把「無老化」限定在上市公司與研究期間，並列出相反證據。

### Bridge auditor
OBJECTION 1
- type: unmapped
- target step: 規模 ↔ 體重
- failure case: 3/4 律的推導需要充滿空間、末端單元大小固定的分支網路；公司的「質量」該用營收、員工或資產並不確定，而且數位業務沒有空間填充限制。推導前提在公司端不存在，所以連「代謝 ↔ 營運支出」這個映射都沒有根據。
- severity: major
- would resolve it: 標出前提不存在，把公司端的任何標度指數都當作實證擬合而非推導。

### Practitioner
OBJECTION 1
- type: not-actionable
- target step: 群體存活曲線
- failure case: 投資人或經營者要的是「這家公司」的風險，群體半衰期幫不上忙。現有的存活分析可以加入規模、獲利、產業成長等共變數 [2]，草稿沒提。
- severity: minor
- would resolve it: 指出用含共變數的存活模型做個體風險。

### Field insider
OBJECTION 1
- type: missing-field-knowledge
- target step: 無老化
- failure case: 組織生態學早有「新生負擔」與「青春期負擔」：死亡風險在成立後 1–15 年呈倒 U 型 [4]。這是研究企業死亡的原生理論，草稿直接從物理出發略過了。
- source: none
- severity: major
- would resolve it: 以組織生態學的年齡依賴風險作為主框架。

## Process note
Run from Claude Code on 2026-09-28 following the app pipeline (index check → connector research → mentor draft → 4 critics → concede/refute revision → round 2 for refuted fatal → fixed confidence rule). The four critics were written in one session one after another, not as independent blind calls.
