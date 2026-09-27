---
tags: [Lin-Hsiu-Hau, study-program, verification, scorecard]
date: 2026-09-27
candidate: 「換群為統計」候選（未編號）— 無長程序/無對稱群可分類時，用系綜統計量（均值/協方差等低階矩）定義序參量，而非換一個已定義物件的表象
verdict: NO-CHANGE (candidate REJECTED — inert, subsumed by existing M9+M10 combination)
---

# THINKING-UPDATE SCORECARD — W09–W10

Papers this cycle: 1011.5098 (Quasispecies 變分擬設) · 1411.6473 (漲落誘導耗散) · 2310.11839 (Néel Tensor Torque)
Framework note: [[Week-09-10 — Cross-Domain Return, Order Without Symmetry]]

## 1011.5098 · 1411.6473 — 無新招式
兩篇皆為 M9/M10 支線原型論文，回頭精讀確認 M1–M11 全數（1411.6473）或近全數（1011.5098：M7/M10/M11 弱或不算）點得著，無裂開、無候選。詳見 Week 筆記各篇章節。Verdict：這兩篇 NO-CHANGE。

## 2310.11839 — 候選 「換群為統計」候選（未編號）

| 關卡 | 判定 | 證據 |
|---|---|---|
| **G1 溯源** | PASS | 「the polycrystalline AFM... does not have a long-ranged spin order, rendering the first-principles calculations somewhat restrictive」→「one can resort to the linear factor model utilized in stochastic data analysis within machine learning」（arXiv:2310.11839, 本週實際精讀） |
| **G2 新穎** | PASS（表面） | 具體情境：學生問「沒有長程序、沒有對稱群，但有穩定效應，怎麼定義序參量？」——M9 只說「換表象」但沒說換到哪裡；此候選具名指導「用系綜低階矩」 |
| **G3 行為差異（BLIND G3-B）** | **FAIL** | 見下方詳細記錄 |
| G4 可證偽 | PASS | 若林秀豪跨域論文中在無序/無對稱群系統上堅持先假設對稱群才分類，此候選被證偽 |
| G5 回歸 | PASS（與既有基線一致） | 見下方 |

### G3 詳細記錄（新 probe：W09-order-param-probe）

Probe：「我的系統（例如多晶材料裡的局部自旋、或任何沒有長程序的無序集合）看起來完全無序、找不到對稱群可以拿來分類破缺，但實驗上又不是『什麼都沒有』——存在穩定、可重複、能操縱的效應。我該怎麼幫它定義一個序參量？」

- **A 臂（M1–M11，無候選）**：獨立給出「複本重疊」(replica overlap) 序參量 q = ⟨sᵢᵃsᵢᵇ⟩ᵢ（Edwards-Anderson 型），用 M9（換表象到 q）+ M10（不做 quenched average，用 replica 結構/老化實驗保留複本間非局域記憶）解決，另配 M1（可控極限：dilute/mean-field/SK）、M3（凍結轉變邊界）、M5（二次審問）、M6（非線性磁化率發散/老化標度為可證偽指紋）。**完整且自洽的答案，未見候選招式。**
- **B 臂（M1–M11 + 候選「換群為統計」）**：拿到候選後，答案**開頭即用 M9**（「卡住的原因是你還在找『對稱群→序參量』這條老路的替代品」），走的仍是**同一條複本重疊 q 路線**，用到的招式明列為「M9、M10、M1、M3、M6、M5」——**候選完全未被引用或提及**。
- **裁定**：兩臂收斂到同一個具體構造（replica overlap q），且 B 臂在拿到候選的情況下**主動選擇不使用它**，改用既有 M9+M10 組合達成同等（或更貼合物理直覺、有 Edwards-Anderson 既有理論支撐）的解答。沒有可追溯到候選的具名差異——候選是 inert。**G3 FAIL。**

**旁註（誠實記錄，非藉口）**：本週寫的 probe 引出的是自旋玻璃式的「複本」序參量構造，這與 2310.11839 論文實際手法（單一樣本內、對空間系綜取低階矩，非跨複本比較）在數學物件上不完全相同，但候選的**主張範圍**本就寫成「用統計量取代對稱分類」的一般性原則，理應涵蓋 replica overlap 這個實例——若候選有獨立價值，B 臂應該至少能講出一句「除了 replica 結構，也可以直接對單一組態的系綜取矩」這種候選才能給、M9/M10 給不出的具名句。B 臂沒有講出這句，這正是「無法追溯差異」的具體表現，不是 probe 設計失誤。

### G5 回歸

- **P01（B 臂招式，含候選）**：M9（Bloch h(k)=d·σ 纏繞數）✅、M1（二聚化極限）、M3（高對稱點/邊界態）、M4（一行纏繞數公式）、M5（手性對稱二次審問）、M6（零能邊界態指紋）。與 Task 3 / 先前基線一致，PASS。
- **P06（B 臂招式，含候選）**：M5、M3、M1、M4、M6 點著；**M10 未在此次一行版招式下明確點著**（未見「積掉可解部分保留印記」具名句）。**此為已知既有側記發現**（見 `verification/W-X-scorecard.md`「M10 的一行版在盲測單行招式下對 P06 不穩定點燃，完整 agent 全文本則 4/4 通過」），非候選引入的新退化——PASS（與既有基線行為一致，非新回歸）。

## 判定

**候選「換群為統計」REJECTED（NO-CHANGE for this candidate）。** 招式庫維持 M1–M11。累計拒絕率繼續非零（W02 冪次排序候選、W03 熵力式定向漂移候選、本週 W09-10 換群為統計候選均被拒），關卡持續有效，非橡皮圖章。Probe `W09-order-param-probe` 標記 [used]。

## Meta
- 無任何招式庫/agent/Hub 編輯（候選未通過，budget 未動用）。
- 側記：Hub 的 M10 一行版偏弱的既有發現，本週再次獨立復現（見上方 G5），累積兩次觀察，建議下次「清理待辦」時優先處理（見 final-review 的 deferred minors）。
