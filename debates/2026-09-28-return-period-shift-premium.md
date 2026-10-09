---
question: 如果「百年一遇」的暴雨變成「二十年一遇」，在極值統計上代表什麼？颱風險保費合理上漲幅度大約是多少？
route: full
confidence: high
card: C011
---

## Final answer
**若百年一遇真的變成二十年一遇，每年發生機率從 1% 變 5%，30 年內至少遇到一次的機率從約 26% 升到約 79% [4]。保費不會跟著漲 5 倍：只算尾端的下界約 +40% 到 +120%，實際可能更高。**

- 這是條件式情境：IPCC 全球平均只到「十年一遇變成 1.3 倍頻繁」[1]；台灣多數測站的重現值確實在上升 [3]，但各地需各自估。
- 下界算法：純保費 = 年期望損失。若百年一遇那一層占期望損失的 10–30%，該層頻率 ×5，總期望損失變成 1.4–2.2 倍。
- 為什麼可能更高：暖化通常讓整個極值分布往上移，連小型事件都更頻繁；保險公司還要為 200 年一遇的極端年份持有資本，尾端變肥時這筆成本漲得更快。
- 實務定價用巨災模型；上面的分層只是量級檢查。

## Final conclusion
- 主張: 百年一遇變二十年一遇＝年超越機率 ×5（30 年至少一次 26%→79%）；颱風洪水險保費的只算尾端下界為 +40%~+120%，整體分布上移與資本成本會使實際漲幅更高，且此情境需逐站驗證。
- 推理步驟: 1. p=1/T 與 30 年累積機率 2. EAL 分層下界 3. 分布位置上移 → 更高 4. 資本成本項 5. 情境逐站驗證、定價用巨災模型
- 因子分類: relevant: 尾端層占比、分布是否整體上移、資本成本 / marginal: 30 年累積機率 / irrelevant: 颱風命名
- 使用招式: M1, M6, M4, M5
- 跨域橋接: none
- 自評信心: medium

**Confidence: high**

## Objection ledger
| # | role | objection | severity | outcome (conceded/refuted/open) |
|---|---|---|---|---|
| O1 | Skeptic | 暖化通常使整個極值分布（GEV 的位置參數）往上移，不只尾端變肥：二年一遇、十年一遇的事件也會更頻繁 [1][3]。只改尾端層算出的 EAL 增幅是下界，實際可能更高。 | major | conceded — 把 +40~120% 改標為「只算尾端的下界」，並說明整體分布上移時會更高。 |
| O2 | Skeptic | 草稿雖說 100→20 是假設，卻在第一句給出確定的保費區間，讀者會以為台灣已經發生。IPCC 的全球平均變化遠小於 5 倍 [1]。 | minor | conceded — 首句改為條件式：「若真的變成二十年一遇……」。 |
| O3 | Practitioner | 保險公司定價不只看 EAL，還要為極端年份持有資本（例如 200 年一遇的可能最大損失）。尾端變肥時，資本成本的增幅可能大於 EAL 的增幅，實際保費漲幅會被低估。 | major | conceded — 保費拆成三項；尾端變肥時資本成本上升，所以總保費漲幅可能高於 EAL 漲幅。 |
| O4 | Field insider | 業界的原生工具是巨災模型（hazard × vulnerability × exposure）加上非定態極值分析；手算分層只適合當量級檢查。 | minor | conceded — 註明分層法是量級檢查，實際定價用巨災模型。 |

## Draft → final diff
- 保費區間改標為只算尾端的下界 (O1)
- 首句改為條件式 (O2)
- 保費拆成純保費、資本成本、費用 (O3)
- 註明分層為量級檢查 (O4)

## Open objections
（無）

## Live sources (connectors, fetched 2026-09-28)
[1] IOP Environ. Res.: Climate 2022（彙整 IPCC AR6）— 十年一遇降雨現在每 10 年發生 1.3 次、強 6.7%；升溫 2°C 時為 1.7 次、強 14% <https://iopscience.iop.org/article/10.1088/2752-5295/ac6e7d>
[2] IPCC AR6 WGI SPM — 重降雨頻率與強度自 1950 年代增加，人為暖化可能是主因；颱風伴隨的重降雨增加（高信心） <https://www.ipcc.ch/report/ar6/wg1/chapter/summary-for-policymakers>
[3] Chu et al.（台灣 21 站颱風季極端降雨趨勢）— 非定態極值分布顯示多數測站 2、20、100 年重現值上升 <https://cpaess.ucar.edu/sites/default/files/meetings/2016/extreme-precip/abstracts/Chu-Chen-Lin-abstract.pdf>
[4] Wolfram|Alpha：1−(1−1/20)^30 = 0.785 <https://www.wolframalpha.com/input?i=1-%281-1%2F20%29%5E30>

## Draft (mentor, before critics)
**年超越機率從 1% 變成 5%，是 5 倍；30 年房貸期間至少遇到一次的機率從約 26% 升到約 79% [4]。保費不該跟著漲 5 倍，合理幅度約 +40% 到 +120%。**

- 極值統計：重現期 T 與年超越機率 p 的關係是 $p=1/T$；30 年內至少一次的機率 $1-(1-p)^{30}$。
- 保費：純保費 = 年期望損失（EAL）。只有「百年一遇那一層」的頻率變 5 倍；若該層占 EAL 的 10–30%，EAL 變成 $0.7+0.3\times5=2.2$ 到 $0.9+0.1\times5=1.4$ 倍，即 +40% 到 +120%。
- 現況：IPCC 全球平均只到「十年一遇變 1.3 倍」[1]，所以 100→20 是一個假設情境，台灣各站需各自估 [3]。

## 結論草稿
- 主張: 百年一遇變二十年一遇代表年超越機率 ×5（30 年至少一次 26%→79%）；若只尾端改變，颱風洪水險純保費合理上漲約 +40% 到 +120%，而非 5 倍。
- 推理步驟: 1. p=1/T 2. 30 年累積機率 3. EAL 分層 4. 尾端層占比 10–30% → +40~120% 5. 情境需逐站驗證
- 因子分類: relevant: 尾端層占 EAL 比例、年超越機率 / marginal: 30 年累積機率 / irrelevant: 颱風命名
- 使用招式: M1, M6, M4
- 跨域橋接: none
- 自評信心: medium

## Critic outputs
### Skeptic
OBJECTION 1
- type: assumption
- target step: 只有百年一遇那一層改變
- failure case: 暖化通常使整個極值分布（GEV 的位置參數）往上移，不只尾端變肥：二年一遇、十年一遇的事件也會更頻繁 [1][3]。只改尾端層算出的 EAL 增幅是下界，實際可能更高。
- severity: major
- would resolve it: 改以整條重現值曲線平移重算，並把 +40~120% 標為下界。
OBJECTION 2
- type: number
- target step: 情境需逐站驗證
- failure case: 草稿雖說 100→20 是假設，卻在第一句給出確定的保費區間，讀者會以為台灣已經發生。IPCC 的全球平均變化遠小於 5 倍 [1]。
- severity: minor
- would resolve it: 第一句就標明這是條件式答案。

### Bridge auditor
NO OBJECTIONS

### Practitioner
OBJECTION 1
- type: missing-threshold
- target step: 純保費 = 年期望損失
- failure case: 保險公司定價不只看 EAL，還要為極端年份持有資本（例如 200 年一遇的可能最大損失）。尾端變肥時，資本成本的增幅可能大於 EAL 的增幅，實際保費漲幅會被低估。
- severity: major
- would resolve it: 把保費拆成純保費 + 資本成本 + 費用，說明資本項的方向。

### Field insider
OBJECTION 1
- type: reinvented-tool
- target step: EAL 分層
- failure case: 業界的原生工具是巨災模型（hazard × vulnerability × exposure）加上非定態極值分析；手算分層只適合當量級檢查。
- source: none
- severity: minor
- would resolve it: 註明分層只是量級估算。

## Process note
Run from Claude Code on 2026-09-28 following the app pipeline (index check → connector research → mentor draft → 4 critics → concede/refute revision → round 2 for refuted fatal → fixed confidence rule). The four critics were written in one session one after another, not as independent blind calls.
