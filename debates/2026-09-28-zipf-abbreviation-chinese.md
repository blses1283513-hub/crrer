---
question: 為什麼每種語言的常用詞都比較短（Zipf 縮寫律）？中文這種幾乎單音節的語言是反例，還是用別的方式遵守同一條定律？
route: full
confidence: high
card: C007
---

## Final answer
**中文不是反例：以詞算，最常用的詞多是單音節，常用字的筆畫也較少。但「所有語言都在最佳化同一個成本」這句話說太滿了。**

- 定律本身很穩：近千種語言都成立 [1]，用語音時長量也成立 [2]。
- 中文在三個層次遵守：詞的音節數、語音時長、字形筆畫 [5]。結果取決於斷詞標準與語料，所以要寫明量測單位。
- 機制有兩個候選：效率最佳化 [3]，或「所有詞都被壓短、高頻詞較少被替換」的文化演化 [4]。兩者都能產生同一條負相關，而且實際相關性遠弱於 Shannon 最佳碼的預測。
- 分辨方法：看短而罕用的詞多不多，以及詞頻上升時詞是否跟著縮短（例如 information → info）。語境可預測度常比頻率更能預測詞長 [6]。

## Final conclusion
- 主張: 縮寫律是近乎普世的弱負相關，中文在詞長、時長與字形層次都遵守；但效率最佳化與無效率壓力的文化演化模型都能產生它，現有相關性不足以判定「同一成本函數」。
- 推理步驟: 1. 跨語言證據 2. 中文三層次量測 3. 兩機制皆可產生 4. 相關強度遠弱於 −log p 5. 以短罕用詞比例、歷時縮短、surprisal 區分
- 因子分類: relevant: 量測單位與語料、surprisal、機制區分觀測 / marginal: Shannon 推導 / irrelevant: 文字是否拼音
- 使用招式: M9, M3, M5
- 跨域橋接: 詞彙 ↔ Shannon 最佳碼 · 未映射: 音系限制、歷史累積 · 斷點: 只保留負相關方向，斜率遠弱於 −log p
- 自評信心: medium

**Confidence: high**

## Objection ledger
| # | role | objection | severity | outcome (conceded/refuted/open) |
|---|---|---|---|---|
| O1 | Skeptic | Morin 2024 的模型只假設「所有詞都受簡短壓力、高頻詞較少被替換」，完全不需要效率最佳化，就能產生縮寫律，並正確預測相關性普遍偏弱、且有很多短而罕用的詞 [4]。兩個模型都能產生同一條負相關，所以相關性本身不能證明「最小化同一成本」。 | fatal | conceded — 主張降為兩機制皆可產生；區分法：短而罕用詞的比例與歷時縮短速度是否隨頻率上升。 |
| O2 | Bridge auditor | Shannon 最佳碼給的是等式 ℓ=−log p；語言資料只給弱負相關 [4]。詞彙也不是設計者一次選定的前綴碼，而是受音系限制、歷史累積的系統。草稿把「方向一致」推成「就是最佳碼」，越過了斷點。 | major | conceded — 橋接只保留方向性，標明實際斜率遠小於最佳碼預測。 |
| O3 | Practitioner | 推導 −log p 不改變任何結論：不論是否最佳碼，「中文是否反例」的答案都由量測單位決定。 | minor | conceded — 推導縮為一句。 |
| O4 | Field insider | 中文詞長結果取決於斷詞標準與語料（書面 vs 口語、是否用字幕語料），而且語言學界已發現語境可預測度（surprisal）常比頻率更能預測詞長 [6]。草稿沒指定量測單位與語料，也漏掉 surprisal。 | major | conceded — 加入量測單位與語料條件，並把 surprisal 列為更強的預測因子。 |

## Draft → final diff
- 主張由「同一成本函數」降為兩機制皆可產生 (O1)
- Shannon 橋接只保留方向性 (O2)
- 推導縮為一句 (O3)
- 加入量測單位、語料條件與 surprisal (O4)

## Open objections
（無）

## Live sources (connectors, fetched 2026-09-28)
[1] Bentz & Ferrer-i-Cancho 2016, Zipf's law of abbreviation as a language universal — 986 種語言、1262 份文本全部呈負相關 <https://consensus.app/papers/details/1a82ad3cbec253d6bd6259aaa1aeadf3/>
[2] Petrini et al. 2023 Glottometrics — 以語音時長計，46 種語言、14 語系成立；詞長系統性低於隨機基線 <https://consensus.app/papers/details/db033deb88305ff5903d913c6cb5e4e4/>
[3] Kanwal et al. 2017 Cognition — 只有準確與效率兩種壓力並存時，人工語言實驗才出現縮寫律 <https://consensus.app/papers/details/367921f9529e53e1b136bffefb201846/>
[4] Morin & Sobchuk 2024 Topics in Cognitive Science — 不需效率壓力的文化演化模型也能產生縮寫律；預測相關性弱且異方差 <https://consensus.app/papers/details/a440064210da5aa098674e721f3ac6b1/>
[5] Koshevoy et al. 2023 Cognition — 27 種書寫系統中，越常用的字元越簡單 <https://consensus.app/papers/details/d42c42d1edb650bfa0a60c337cd9fdca/>
[6] Levshina 2021 Entropy — 語境資訊量（surprisal）常比頻率更能預測詞長 <https://consensus.app/papers/details/6f1df7ff1dcb53dea0464faa37e0cb33/>

## Draft (mentor, before critics)
**中文不是反例；縮寫律是最佳編碼的結果，所有語言都在最小化同一個「溝通成本」。**

- 證據：近千種語言都成立 [1]，連語音時長也成立 [2]。
- 機制（Shannon）：最佳碼長 $\ell_i\approx-\log_2 p_i$，常用詞自然較短；人工語言實驗顯示需要準確與效率兩種壓力 [3]。
- 中文：以「詞」而非「字」計，最常用的詞（的、是、我、不、了）多為單音節，罕用詞多為雙音節以上；字形也遵守，常用字筆畫較少 [5]。

## 結論草稿
- 主張: 縮寫律是所有語言最小化同一溝通成本函數的結果，中文在詞長與字形兩個層次都遵守。
- 推理步驟: 1. 跨語言證據 2. Shannon 碼長 −log p 3. 實驗顯示雙壓力 4. 中文以詞計仍成立 5. 字形層次也成立
- 因子分類: relevant: 頻率、詞長量測單位 / marginal: 字形複雜度 / irrelevant: 文字是否拼音
- 使用招式: M9, M4
- 跨域橋接: 詞彙 ↔ Shannon 最佳前綴碼 · 未映射: 無 · 斷點: 無
- 自評信心: high

## Critic outputs
### Skeptic
OBJECTION 1
- type: alternative
- target step: 所有語言最小化同一成本函數
- failure case: Morin 2024 的模型只假設「所有詞都受簡短壓力、高頻詞較少被替換」，完全不需要效率最佳化，就能產生縮寫律，並正確預測相關性普遍偏弱、且有很多短而罕用的詞 [4]。兩個模型都能產生同一條負相關，所以相關性本身不能證明「最小化同一成本」。
- severity: fatal
- would resolve it: 把主張降為「兩種機制皆可產生」，並給出能區分它們的觀測。

### Bridge auditor
OBJECTION 1
- type: past-break-point
- target step: Shannon 碼長 −log p
- failure case: Shannon 最佳碼給的是等式 ℓ=−log p；語言資料只給弱負相關 [4]。詞彙也不是設計者一次選定的前綴碼，而是受音系限制、歷史累積的系統。草稿把「方向一致」推成「就是最佳碼」，越過了斷點。
- severity: major
- would resolve it: 映射只保留方向（負相關），標出斜率遠弱於 −log p。

### Practitioner
OBJECTION 1
- type: wasted-depth
- target step: Shannon 推導
- failure case: 推導 −log p 不改變任何結論：不論是否最佳碼，「中文是否反例」的答案都由量測單位決定。
- severity: minor
- would resolve it: 縮到一句。

### Field insider
OBJECTION 1
- type: missing-field-knowledge
- target step: 中文以詞計仍成立
- failure case: 中文詞長結果取決於斷詞標準與語料（書面 vs 口語、是否用字幕語料），而且語言學界已發現語境可預測度（surprisal）常比頻率更能預測詞長 [6]。草稿沒指定量測單位與語料，也漏掉 surprisal。
- source: none
- severity: major
- would resolve it: 指定量測單位（音節、時長、筆畫）與語料，並把 surprisal 列為競爭預測因子。

## Process note
Run from Claude Code on 2026-09-28 following the app pipeline (index check → connector research → mentor draft → 4 critics → concede/refute revision → round 2 for refuted fatal → fixed confidence rule). The four critics were written in one session one after another, not as independent blind calls.
