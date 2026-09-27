---
tags: [Lin-Hsiu-Hau, study-program, week-09-10]
created: 2026-09-27
papers: [1011.5098, 1411.6473, 2310.11839]
theme: 跨界回歸（演化動力學兩篇）＋ 現有語錄庫最新一篇（多晶反鐵磁 Néel tensor）
provenance: 依跨域大腦目標，curriculum.md 於 2026-09-27 把 W09–W10 提前；1005.4335 / 2211.15278 已於 W03 讀畢，本次只讀新篇
---

# Week 09–10 — 跨界回歸與「沒有群可破的序參量」

**動機**：W03 已證明 M1–M11 在生態學與神經科學兩個最遠域「點得著」。W09–W10 補回演化動力學支線剩下的兩篇（此支線的 M9/M10 原型論文），並讀完既有語錄庫中最新一篇（2310.11839，多晶反鐵磁自旋電子學）——三篇合起來測試：招式庫在「回到熟悉支線深挖」與「讀最新一篇工程化應用論文」兩種情境下，還會不會裂開或需要新增。

---

## 論文 1 · Quasispecies 變分擬設（1011.5098, Tu/Huang/Lin/Chen 2010）

**問題**：Eigen 1971 準物種模型的誤差閾值（error threshold）——突變率超過此界，天擇失效，準物種瓦解。2^L 維非線性方程組，直接解不可行。

**樞紐（雙招）**：
1. 規範變換把非線性複製子方程線性化成「虛時薛丁格方程」：Ψᵢ(t)=√fᵢxᵢ(t)e^{W(t)}，Ẇ=φ（M9 換表象）。
2. 只保留每個 Hamming 距離殼層的全對稱態，把指數多的突變態壓成 2×2 矩陣對角化（M2 一副骨架多具身體）。

**驗證**：χ 指標自報崩壞區（M5 二次審問的更銳利版本——指標本身在超過閾值時發散，等於自帶失效警報）；精確數值對角化證實只有兩個對稱態靠近閾值（驗證截斷本身，不只驗證答案）；r→1 極限對照 Crow-Kimura 連續模型。

**招式判定**：M1 ✅(對照精確解/連續極限) M2 ✅✅(樞紐本身) M3 ✅(閾值=邊界現象) M4 ✅(H_ij 一行) M5 ✅(χ 自報崩壞) M6 ✅(u_c L=ln(f_M/f)) M7 未見明確跨界計價 M8 ✅(誠實承認犧牲精確性換簡單) M9 ✅✅(樞紐本身) M10 弱/不算 M11 弱/不算。**候選新招式：無**——兩個最強候選都已歸位 M9/M2。

**框架句**：「The success of the variational approach relies on the fact that there are only two active states near the phase transition, verified by the exact diagonalization.」

---

## 論文 2 · 漲落誘導耗散（1411.6473, Lu/Chen/Lin/Chen 2014）

**問題**：生態系統的確定性複製子方程預測穩定振盪共存，但生物多樣性照樣崩潰。剝除掉所有具名外部災害後問：族群數是離散整數這件事本身，夠不夠導致滅絕？

**樞紐**：把「離散隨機過程何時觸底」換成「單一純量指標 χ 的等值線幾何」——雜訊是各向同性的，但等值線是凸的，導致等機率跳躍點在低 χ 側掃過的相空間面積比高 χ 側大，產生確定性方向的漂移 ⟨Δχ⟩=−½κ|∇χ|σ²（M11 把動力學變成幾何，M9 換表象到 χ）。

**驗證**：解析公式 vs 直接隨機模擬逐點比對；明講兩個近似假設，並在假設違反的區域（region B）誠實展示不吻合（M5+M8 教科書級範例）；二階矩 ⟨Δχ²⟩ 獨立推導做交叉檢查；無雜訊極限退回確定性複製子方程（極限自洽檢查）。

**招式判定**：M1–M11 全數 ✅（M9/M10/M11 是骨幹：換表象到 χ → 積掉離散跳躍過程保留雜訊關聯 → 讀等值線曲率的幾何）。**候選新招式：無。**

**框架句**：「The dissipation is determined by the geometric structure of contours in the phase space.」／三步口號：「discreteness induces fluctuations, fluctuations spawn dissipations and dissipative dynamics leads to extinction.」

---

## 論文 3 · Néel Tensor Torque（2310.11839, Yang/Chen/Tseng/Kuo/Lin/Lai 2023）——語錄庫最新一篇

**問題**：多晶反鐵磁（IrMn 等，工業界 SOT/MRAM 實際用的材料）沒有長程序、局部自旋常非共線——既有的 Néel 向量理論（要求共線長程序）和第一性原理計算（要求週期性）都用不上。選題動機是一個**實驗異常**：Pt/Co/IrMn 元件在撤掉對稱破缺的外加場後，仍保持固定極性切換——不是先驗地挑一個「無序反鐵磁」的抽象題目，是「排除交換偏壓後，既有理論解釋不了的真實反常，且材料是工業標準品」。

**樞紐（候選新招式）**：把無序、非週期性的自旋組態直接當隨機變數，借用機器學習的線性因子模型（PCA），用其一階矩（殘餘自旋向量）與二階矩（協方差張量，即「Néel 張量」）定義結構——**不是換一個更好的表象去看已定義好的物件（M9），是在沒有對稱群可分類的地方，用統計推斷本身生出一個序參量**。逐字：「the polycrystalline AFM... does not have a long-ranged spin order, rendering the first-principles calculations somewhat restrictive」→「one can resort to the linear factor model utilized in stochastic data analysis within machine learning」。

**驗證**：(1) 訓練場翻轉→極性翻轉的正負號規則，兩個獨立元件上驗證；(2) XMLD 光譜獨立實驗模態交叉驗證；(3) 理想四面體構型精確計算張量=0（Eq. S14），與「只有真實不完美疇才會被訓練」一致，本身是精確可解極限自檢（M1）；(4) 加熱抹除→反向再訓練→極性再翻轉，排除是固化的製程假象；(5) 事先明確排除面內交換偏壓這個competing explanation。

**招式判定**：M2 ✅ M3 ✅(殘餘自旋定域於界面) M4 ✅(U_N=½λ_N M⃗·N⃡·M⃗) M5 ✅(質疑自己「為何這麼容易被訓練」) M6 ✅✅(P=±1 正負號規則直接對數據) M7 ✅✅(明講借自機器學習，且警告 PCA≠ICA 的具體誤用) M8 ✅(明講尚未做的 3D XMLD 掃描、留給未來的反向耦合) M9 ✅(Néel 向量結構性看不見非共線構型) M10 不算 M11 ✅✅(把磁矩球面上的力矩場分類成鞍點/中性平衡的幾何問題，dumbbell/donut/dough 形狀)。

**框架句**：「The field-like torque originates from the magnetization interaction with a vector..., while the Slonczewski torque is due to its interaction with a tensor... Is a similar phenomenon possible at the FM/AFM interface? Yes.」——可教的通用啟發：已知效應是「A 與向量 B 互動」時，系統性地問「A 是否也與某個張量互動」，再去找那個缺失的張量耦合的物理實現。

---

## 候選新招式 ·「換群為統計：無群可破時，用統計推斷生序參量」（未編號，依 W03 慣例：未通過前不佔招式編號）

- **一句話**：卡住不是換表象看已定義的物件（M9），是在沒有對稱群、沒有長程序可分類的地方，改問「有沒有一個統計量（系綜的低階矩）能在沒有群的地方定義出序參量」。
- **與現有招式的關係**：M9 假設「結構已存在，換個變數就顯形」；此候選處理的是「結構的存在條件」本身——目標系統沒有可破的對稱群，因此傳統 Landau/對稱分類完全無用武之地。
- **G1 溯源**：2310.11839，「one can resort to the linear factor model utilized in stochastic data analysis within machine learning」+「does not have a long-ranged spin order, rendering the first-principles calculations somewhat restrictive」。
- **G2 新穎**：具體情境——學生問「我的系統沒有長程序、沒有對稱群，但有穩定可操縱效應，怎麼定義序參量？」M9 只會說「換個表象」，但換到哪個表象？M9 沒有答案，因為根本沒有已知的物件可換。此候選具名指導：「用系綜的均值/協方差當序參量，不用不可約表示」。
- **G3 行為差異（BLIND G3-B）**：見下方 scorecard。
- **G4 可證偽**：若林秀豪的跨域論文中出現「面對無序、無對稱群系統時，仍堅持先找/假設一個對稱群再分類」，這條候選就被證偽。
- **G5 回歸**：見下方 scorecard（P01/P06 as control）。

**判定：REJECTED（G3 FAIL — inert）。** 盲測 B 臂拿到候選後，答案與 A 臂收斂到同一構造（複本重疊序參量 q，Edwards-Anderson 型），且 B 臂自己列出的招式清單完全不含候選——候選未產生任何可追溯的具名差異，被既有 M9（換表象）+M10（積掉保留印記）組合完整涵蓋。招式庫維持 M1–M11。詳見 [[W09-10-scorecard]]。

## 週結論（META）

三篇合起來的頭條：**M1–M11 在演化動力學支線內部（1011.5098, 1411.6473）完全點得著、無裂開**——這條支線本來就是 M9/M10 的原型論文，回頭讀不意外地印證。**真正的訊號在第三篇**：2310.11839 是招式庫建立後（2026-07-04）最新的一篇，它逼出了一個 M9 覆蓋不到的候選——不是「換表象」，是「無群可破時換統計」。這與跨域大腦目標一致：招式庫要能處理「結構存在」與「結構存在的前提條件消失」兩種不同的卡點。
