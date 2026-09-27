---
tags: [Lin-Hsiu-Hau, study-program, verification, scorecard, week-02]
created: 2026-07-04
---

# THINKING-UPDATE SCORECARD — Week 02

Papers: cond-mat/0306159 · cond-mat/0508660 · 0911.0166（RG 方法論三篇）
Candidate moves: **M11**（把動力學變成幾何）、M12（冪次排序，候選）、M9 細化、M1 細化

---

## Candidate M11 — 把動力學變成幾何

- **G1 Provenance** — **PASS**. "eliminates chaos by topology, not approximation"（cond-mat/0508660）；"RG flows = trajectory of an overdamped particle searching for potential minimum"（cond-mat/0306159）；dV/dl = −(dh_i/dl)² ≤ 0。三篇本週實讀。
- **G2 Novelty** — **PASS**（與 M9 可組合非重複）。最近的是 M9（換表象）與 M4（一行有效理論）。判別情境：學生有一組耦合流 ODE、沒有對稱要顯、只想知道最終命運——M9 只說「換變數看結構」，不會叫你**找 Lyapunov/位勢函數**；M4 是塌縮 Hamiltonian（對象是靜態理論），M11 的對象是**流/動力學**。M11 常**用** M9 當子步驟（對稱化換表象讓位勢存在），是組合不是複製。
- **G3 Behavioral delta（盲測雙臂 G3-B）** — **PASS**. Probe「耦合非線性流會不會混沌」。
  - Arm A（M1–M10）：找不動點 → Jacobian 特徵值 → **沿軌跡算 λ_max 診斷**混沌（教科書路線）。
  - Arm B（+M11）：**造單調位勢 V、dV/dl ≤ 0 → 由構造排除混沌與極限環**；沿現有軌跡畫 V(l)；對稱化換表象。
  - 裁判：B 獨有「以幾何/單調函數約束、把混沌由構造排除」，A 只能「測 λ_max 事後診斷」。具名差異可追溯 M11。兩臂其餘（不動點/Jacobian/fixed ray）相似 → 測試有效。
- **G4 Falsifiability** — **PASS**. 若林的 RG 方法其實靠硬解軌跡或事後測量判混沌（而非「證位勢存在→單調→禁混沌」），則此招式不成立。實查三篇皆明確構造位勢並證單調 → 未被證偽。（招式在使用中亦可證偽：任一條 V 上升或出現閉軌 → 位勢假設被否證。）
- **G5 Regression** — **PASS**. 兩臂都仍正確觸發 M1（不動點線性化）與 M9（對稱化換表象）→ 舊招式未被 M11 覆蓋壞。

**M11 verdict: ACCEPT**

---

## M12（冪次排序）— 降級為 M1 細枝，不新增招式

- 內容：所有耦合都 marginal 時，用 g_i ~ G_i/(l_d−l)^{γ_i} 的**指數 γ_i** 排序關聯性（衝向奇異點越陡越關聯），不比當下量值（0911.0166）。
- **G2 判定：FAIL as standalone**。它是「哪些耦合關聯/主導」的判準，與 M1 的「普適性簽名 / 哪些耦合成長」同軸——舉不出與 M1 給出「不同大方向」的情境，只是把 M1 的排序判準講細。→ **併入 M1 as 細枝**，不佔新編號。（此即 D0＋反作弊：不是每個候選都升格，證明關卡有牙。）

---

## M9 細化（新戰術，非新招式）
- 新增戰術：**換到讓「所需的對稱化/變換」變對角的基底**（Majorana 使對稱化矩陣 L 對角，位勢才存在）。回寫 [[M09 換表象顯形]] 細枝。

---

## Week-02 Verdict: **UPDATED (+M11) + REFINED (M1, M9)**

- Written to Scholarly Profile §4 / Hub / agent：**Y**
- 招式庫：M1–M10 → **M1–M11**
- Probe consumed：W02-flow-probe（耦合非線性流命運）→ 標 [used]
- 誠實備註：本週**拒絕了 1 個候選（M12 降級）**，拒絕率非 0 → 呼應反作弊 meta-check，關卡未放水。
- D0 檢查：本週產出是「對 RG 方法的更深理解＋1 個驗證過的新招式」，非流程擴張 → 通過深度優先守門。
