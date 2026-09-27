---
tags: [Lin-Hsiu-Hau, study-program, verification]
created: 2026-07-04
purpose: 檢查每週研讀是否「真的」更新了思維路線（reasoning moves），而非只是累積筆記
principle: 一套無法失敗的驗證流程等於沒有驗證。本流程必須能判「本週無更新」。
---

# 思維更新驗證流程 (Thinking-Update Verification Protocol)

## 0. 這套流程在防什麼

失敗模式 = **學習劇場 (learning theater)**：筆記變多、M 編號變多，但導師的實際推理沒有改變。
症狀：招式互相是換句話說（M-inflation）；「新招式」引不出任何不同的回答；引用是捏造的；舊招式悄悄壞掉。

驗證單位 = 一個 **reasoning move (M-number)** 或其精煉。
一週的合法結果有三種，**NO-CHANGE 是正常且誠實的**：
- **UPDATED** — 新增 ≥1 個通過全部關卡的招式
- **REFINED** — 沒有新招式，但既有招式的邊界/措辭被證據改進
- **NO-CHANGE** — 三篇沒讀出可通過關卡的新思維（合法，不是失敗）

## 1. 五道關卡（每道 PASS/FAIL，可客觀判定）

候選招式要進永久記憶，須**全數通過**。任一 FAIL → 該候選退回（降級為 REFINE 或丟棄）。

| 關卡 | 判定問題 | FAIL 的意義 |
|---|---|---|
| **G1 溯源 Provenance** | 候選是否附「本週實際讀過的論文」中的逐字引句 ＋ arXiv ID？ | 捏造風險——無出處的洞見不算 |
| **G2 新穎 Novelty (反重複)** | 能否舉出一個具體情境，使此招式給出的指導**不同於現有每一個 M**？ | 只是換句話說 → 應併入既有招式而非新增 |
| **G3 行為差異 Behavioral delta（核心）** | 取一道保留題 (held-out probe)：導師「只用舊招式」與「加上新招式」的回答是否**實質不同、且新版更好**？ | 回答相同 → 招式是 inert 惰性的，退回 |
| **G4 可證偽 Falsifiability** | 能否說出「什麼證據會證明這不是林的思路」？ | 說不出 → 這不是觀察，是套套邏輯 |
| **G5 回歸 Regression** | 重跑 2 道舊 probe，舊招式是否仍正確觸發、未被新招式覆蓋壞？ | 舊能力退化 |

G3 是心臟。沒有 G3，這整套只是記帳。

## 2. G3 怎麼跑 — **盲測雙臂設計 (G3-B，2026-07-04 起為標準)**

自我評分有盲點（同一個模型自問自答自判）。標準做法改為 subagent 盲測：

1. 從 `probe-bank.md` 取一道新鮮 probe。
2. **A 臂（盲 baseline）**：派一個 subagent，只給它「舊招式 M1..M(n−1) 的一行版＋probe」。**不給**候選招式、不給本週論文、明令禁止讀任何檔案與使用工具。
3. **B 臂**：另一個 subagent，同樣條件但拿 M1..M(n)（含候選招式）。兩臂**平行、互不可見**。
4. **主線只當裁判**：比對兩臂回答，判定 B 臂是否含有「可追溯到候選招式、且 A 臂沒有」的**具名**指導。
   - B 臂多出的內容若只是措辭差異或與候選招式無關 → G3 FAIL。
   - A、B 臂在其餘部分應大致相似（都拿同樣的舊招式）——若整體差異巨大，判定無效，換 probe 重跑。
5. probe 用完即燒毀（標 [used]＋日期＋結果）。probe bank 持續補題。
6. 裁判判定連同兩臂關鍵句**逐字記入 scorecard**，供日後抽查。

> 舊版（主線自比 baseline/post）保留為 G3-A，只允許在 subagent 不可用時作為降級方案，且 scorecard 須標注「G3-A degraded」。

### G3-B 首次驗證運行（回溯測 M10）
2026-07-04 · Probe P06「mean-field 解很漂亮該不該直接發表」：
- A 臂（M1–M9）：Ginzburg 漲落、極限檢查、指紋設計、換表象——全部圍繞鞍點**周圍**審查。
- B 臂（M1–M10）：上述之外獨有「若模型中有可精確解的雙線性部分，把它精確積掉，保留遲滯記憶效應，別用靜態平均替代」。
- 裁判：具名差異成立且可追溯到 M10 → **PASS**。兩臂其餘部分相似 → 測試有效。

## 3. 反作弊 meta-check（每 4 週一次）

流程本身也會腐化，故設後設檢查：
- **拒絕率 Rejection rate**：若累計候選招式的拒絕率 = 0%，關卡是橡皮圖章 → 收緊 G2/G3。目標：預期**有些週 NO-CHANGE、有些候選被拒**。
- **反向 probe**：隨機取一道 probe，刻意**不靠任何新招式**盡力答好。若答得一樣好 → 那些招式沒加值 → 檢討。
- **招式總數健檢**：M 的數量若每週 +2 無上限,幾乎必有重複。> 15 個招式時強制做一次合併審查。
- **溯源抽查**：隨機抽 2 個既有 M，回原論文確認引句真實存在（防止記憶漂移/幻覺）。

## 4. 每週流程（納入 curriculum 週期）

```
讀 3 篇全文
  → 寫 Week-XX 框架筆記（F 級觀察）
  → 對每個候選 M 跑 G1–G5
  → 填 Week-XX-scorecard.md（每關卡 PASS/FAIL ＋ 證據）
  → 判 verdict: UPDATED / REFINED / NO-CHANGE
  → 僅通過者寫入 Scholarly Profile §4 ＋ mentor agent Reasoning Moves
  → 每 4 週跑一次 §3 meta-check，結果記在本檔 §6
```

## 5. 驗證報告格式（每週 scorecard 用）

```
THINKING-UPDATE SCORECARD — Week XX
Papers: <arXiv IDs>
Candidate moves: <list>

Per candidate:
  G1 Provenance:   PASS/FAIL  — <quote + arXiv ID>
  G2 Novelty:      PASS/FAIL  — <discriminating situation vs closest existing M>
  G3 Behavioral:   PASS/FAIL  — <probe id; named baseline gap → post fix>
  G4 Falsifiable:  PASS/FAIL  — <what would disprove>
  G5 Regression:   PASS/FAIL  — <2 old probes still fire>

Verdict: UPDATED (+N moves) / REFINED / NO-CHANGE
Written to: profile §4? agent? (Y/N)
```

## 6. Meta-check 紀錄
- （每 4 週追加一筆：拒絕率、反向 probe 結果、招式總數、溯源抽查）

## 7. 續讀與觸發
- 每週：「本週研讀」→ 讀下一週 → 跑本流程 → 填 scorecard。
- 招式庫與流程狀態的權威來源：本檔 ＋ [[curriculum]] ＋ `../Lin Hsiu-Hau — Scholarly Profile.md` §4。
