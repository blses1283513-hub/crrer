---
tags: [Lin-Hsiu-Hau, study-program, verification, scorecard, week-01]
created: 2026-07-04
---

# THINKING-UPDATE SCORECARD — Week 01

Papers: cond-mat/9801285 · cond-mat/0001320 · 2109.12608
Candidate moves: **M9** (change representation to reveal hidden structure), **M10** (integrate out exactly-solvable sector, keep dynamic imprint)

---

## Candidate M9 — 換表象讓隱藏結構顯形

- **G1 Provenance** — **PASS**. 逐字引句 "abelian bosonization masks the full symmetry group" (cond-mat/9801285)；複變相位編碼 z=r·e^{iφ} (2109.12608)。兩篇實際讀過。
- **G2 Novelty** — **PASS (但標記與 M4 重疊)**. 最接近的是 M4「求一行有效理論」。判別情境：學生**已經有**一行有效理論，但寫在對稱隱形的變數裡——M4 判定「完成」，M9 說「繼續換變數直到對稱顯形」。動作不同（M4 看輸出，M9 看方法：在表象空間搜尋）。⚠️ 邊界仍窄，列入下次 meta-check 的合併審查候選。
- **G3 Behavioral delta** — **PASS**. Probe **P01**（雙原子鏈拓撲判定）。baseline (M1–M8) 推 RG/邊界態，繞路；+M9 直接指「H(k)=d(k)·σ，看 winding，拓撲在 site 基底隱形、在 Bloch 向量表象顯形」。具名差異：baseline 漏掉「先換表象再看」，M9 補上。
- **G4 Falsifiability** — **PASS**. 若能找到他的重要結果是**在 bare 變數裡直接看出結構、沒做關鍵變數變換**，則此招式不成立。實查三篇皆靠變數變換（refermionize／有效作用量／複相位），未被證偽。
- **G5 Regression** — **PASS**. 重跑 P07（三種近似哪個對）→ M1「在可控處計算」仍正確觸發；重跑 P05（醜定理）→ M4 仍觸發，未被 M9 吃掉。

**M9 verdict: ACCEPT** （附註：M9/M4 邊界待第 4 週合併審查）

---

## Candidate M10 — 積掉可解部分、保留動態印記

- **G1 Provenance** — **PASS**. 逐字引句 "since the Hamiltonian is bilinear in fermionic fields, we can integrate out the itinerant carriers"；"retarded and non-local character... described here for the first time" (cond-mat/0001320)。
- **G2 Novelty** — **PASS**. 最接近 M5（二次審問漲落）。判別情境：面對「把電子海取平均」，M5 只說「事後檢查哪個漲落殺掉答案」，不反對取平均這步；M10 說「別取平均——雙線性可精確積掉，保留推遲印記」。M10 管上游動作，M5 管下游檢查。不同。
- **G3 Behavioral delta** — **PASS**. Probe **P02**（磁性雜質＋電子海）。baseline 允許靜態平均代入；+M10 反對，改為精確積掉並保留非局域交互作用（否則退化成 RKKY，漏掉基本激發）。具名差異成立。
- **G4 Falsifiability** — **PASS**. 若他的 DMS 理論其實用的是靜態/mean-field 電子浴，則此招式不成立。實查：論文明確與 RKKY 靜態圖像對比並宣稱首次處理推遲交互作用 → 未被證偽。
- **G5 Regression** — **PASS**. P07 → M1 仍觸發；P06（漂亮 mean-field 該不該寫）→ M5 與 M10 同時且互補觸發（M10 說先別平均、M5 說若平均了要查漲落），無覆蓋衝突。

**M10 verdict: ACCEPT**

---

## Week-01 Verdict: **UPDATED (+2 moves: M9, M10)**

- Written to Scholarly Profile §4: **Y**
- Written to mentor agent Reasoning Moves: **Y**
- Probes consumed: P01, P02 → 標記 [used]
- ⚠️ Flag for Week-04 meta-check: M9/M4 邊界重疊，若之後未拉開差距則考慮合併為單一招式。
- 誠實備註：本週兩個候選都通過（拒絕率 0%）。這是可接受的（W01 刻意選生涯弧線三篇、訊號強），但**連續兩週 0% 拒絕就要懷疑關卡放水**。
