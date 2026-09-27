---
tags: [Lin-Hsiu-Hau, verification, scorecard]
date: 2026-09-27
candidate: M7 refinement「斷點稽核」— 雙語字典之外，再列出來源側『沒有對應物』的項目，並指名類比在哪一步斷掉；結論只帶到斷點之前。
verdict: NO-CHANGE (candidate REJECTED — inert, subsumed by M7 sub-tactic 2)
---

# THINKING-UPDATE SCORECARD — W-X (bridge audit)

Papers (provenance): 2211.15278 · 1005.4335 (both read in W03)

| Gate | Result | Evidence |
|---|---|---|
| G1 Provenance | PASS (weak) | 2211.15278: "the optimized state for visual recognition, although close to, does not coincide with the critical state." — Lin names where the criticality=optimality bridge breaks. 1005.4335 maps extinction ↔ damped oscillator item by item. |
| G2 Novelty | PASS on paper | X12 situation: dictionary can be written (refresh↔review), yet the transfer fails at "reinforcement"; the candidate names that step explicitly. |
| **G3 Behavioral delta (blind, two-arm)** | **FAIL** | Arm A = M1–M11 one-liners + M7 sub-tactic 2 (雙語字典); Arm B = same + candidate. See below. |
| G4 Falsifiability | PASS | Would be falsified if Lin's cross-field papers transfer conclusions past an acknowledged mismatch without flagging it. |
| G5 Regression | PASS (vs control) | P01 (Arm B moves): M9 fires — "實空間→Bloch 向量 h(k)… 判斷 (hx,hy) 曲線是否繞原點，即纏繞數 w". P06 (Arm B moves): M10 did NOT fire; **control P06 with Arm A moves also did not fire M10** (used M5/M3/M4/M6) → not caused by the candidate. |

## G3 detail (judge = main thread)

**X12 (trap: DRAM refresh ↔ 複習)**
- Arm A (no candidate), key content: "DRAM cell leakage rate is a fixed hardware constant unaffected by refresh, whereas human memory decay rate is itself modified by each review (spacing effect)"; conclusion: metaphor yes, computational method no.
- Arm B (with candidate), key content: 「refresh 不改變被 refresh 對象的物理性質，只是恢復原值；複習卻改變記憶本身的衰減函數…從這一步起，結論不能再帶過去。」 Full text: `_backup-2026-09-27/g3-bridge-audit/X12-B.md`.
- Judgment: the decisive break point is named by BOTH arms. B adds structure ("結論只帶到斷點前", explicit transferable list), no new named guidance.

**X06 (bridge: 單點瓶頸 ↔ 出口管制)**
- Arm A: 「單點瓶頸分析能回答『誰卡住』，但單獨不足以回答『管制會不會奏效』」; lists 庫存囤貨、第三地轉運、逆向工程追趕、對手國補貼; M7: 「不能把它的結論（瓶頸存在=管制必然奏效）直接搬到政策評估上」.
- Arm B: 「瓶頸＝結構上不可替代的關鍵節點 … 管制槓桿＝對手切換成本 × 政治意願 × 時間貼現。這兩者不是同一個量」; break points: 替代供應鏈成熟速度、走私/灰色管道規模、**盟友執行一致性**.
- Judgment: same bottom line. Only unique item in B = 盟友執行一致性, not traceable to the candidate's wording. No named delta.

**Verdict:** G3 FAIL → candidate inert; the existing M7 sub-tactic 2 (「字典寫不出來的類比是修辭」) already produces break-point naming. Rubric grading of both arms not run: acceptance requires a named G3 delta first (spec 5.4), which is absent.

## Side finding (for the Hub, not a move change)
M10's **one-line** Hub form does not fire on P06 in either arm, while the full agent text does (Task 3 regression PASS 4/4). One-liners are what blind G3 arms receive → consider sharpening the Hub M10 line so future G3/G5 tests are not biased against M10.

## Meta
Rejection keeps the cumulative candidate rejection rate > 0 (protocol §3). No edits to `moves/M07`, the agent, or the Hub. Probes X06, X12 burned.

## Appendix — X12 Arm B verbatim
`_backup-2026-09-27/g3-bridge-audit/` holds X12-B.md and the exact Arm A/B move sets.
