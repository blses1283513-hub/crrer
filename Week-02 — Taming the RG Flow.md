---
tags: [Lin-Hsiu-Hau, study-program, week-02]
created: 2026-07-04
papers: [cond-mat/0306159, cond-mat/0508660, 0911.0166]
theme: RG 方法論——把耦合非線性流馴服成可預測的幾何
---

# Week 02 — 馴服 RG 流

三篇都在回答同一個困惑：**準一維系統的 RG 流方程又多又非線性，照理該混沌，為什麼相圖卻簡單得出奇？** 林的答案分三步搭起來。

---

## 論文 1 · Potential Flow of RG（Majorana 表象）
cond-mat/0306159

**(a) 問題**：準一維梯子的 RG 流有一堆耦合四費米子項，耦合的非線性流方程「generically 會產生混沌流」，卻觀察到簡單相圖。矛盾。

**(b) 樞紐移動**：把耦合流**改寫成位勢流(potential flow)**：dh_i/dl = −∂V/∂h_i。要做到這步，需要一個把耦合係數對稱化的線性變換 L——**在原費米子基底裡「連證明它存不存在都非平凡」；換到 Majorana 表象，L 變成對角**（只是速度相關的縮放 r_i δ_ij）。這是 [[M09 換表象顯形]] 的極致示範：換對表象，難變換變成對角。

**(c) 論證鏈**：耦合非線性流 → 找對稱化變換 L → Majorana 分解使 L 對角 → 關鍵物理事實：弱耦合展開裡每個頂點只牽涉**成對的兩個費米速度**(即使四條能帶參與) → 這個「看似無用的特徵」保證位勢存在 → 一圈圖全部收進單一位勢 V。

**(d) 買到什麼**：位勢沿流**單調遞減** dV/dl = −(dh_i/dl)² ≤ 0 → **直接排除混沌與極限環**；流只能落到不動點或沿山谷/山脊奔向強耦合。幾何圖像：**過阻尼粒子在多維耦合空間裡找位勢極小**。

**(e) 框架句**：
> "This seemingly useless feature (pairwise velocities) turns out to be strong enough to guarantee the existence of the RG potential when re-expressed in Majorana fermions."
> "RG flows = trajectory of an overdamped particle searching for potential minimum."

---

## 論文 2 · RG Potential for Quasi-1D Systems
cond-mat/0508660

**(a) 問題（比論文1更進一步）**：不只證位勢存在，而是把「為什麼相圖簡單」變成一句話——**混沌被拓撲殺掉，不是被近似殺掉**。

**(b) 樞紐移動**：耦合經唯一(up to scaling)線性變換後，流變成**梯度下降**；定義性質是**單調性** dV/dl ≤ 0。單調的位勢**由構造上**禁止螺旋與循環。

**(c) 論證鏈**：交互作用寫成 SU(2)×U(1) 流的雙線性 → OPE 算一圈 → 縮放後成梯度流 → Majorana 證位勢存在非偶然 → V 沿軌跡守恆(只在不動點變) → 軌跡收斂到**固定射線**(耦合比值固定) → 對每條固定射線 bosonize，讀出哪個 sector 開能隙 → 相位。

**(d) 買到什麼**：固定射線 g_i(l) ~ G_i/(l_d−l) **自動**出現，不需數值積分每條軌跡；山谷/山脊直接顯示哪些耦合組合活到低能；**湧現對稱(SO(8))由位勢的幾何直接解釋**。

**(e) 框架句**：
> "The existence of the RG potential provides a natural explanation of the emergent symmetry enhancement."
> "This eliminates chaos by topology, not approximation."
> "The flows can be viewed as trajectories of a strongly overdamped particle in a conservative potential."

---

## 論文 3 · Hierarchy of Relevant Couplings
0911.0166

**(a) 問題**：當所有耦合都是 marginal(樹級標度維度=0)，「在某個尺度看誰的量值~1」這種判準**模稜兩可**。到底哪個耦合驅動物理？

**(b) 樞紐移動**：不比量值，**比逼近奇異點的冪次**。設 g_i(l) ≈ G_i/(l_d−l)^{γ_i}，用**指數 γ_i** 排序關聯性：γ=1 主導、3/4 次之、1/2 再次、0 無關。原理：γ 量的是「多陡地衝向奇異長度尺度 l_d」——衝得越陡越關聯。

**(c) 論證鏈**：數值積分早期亂、之後進入 scaling regime 服從冪律 → 用矩陣分解證所有耦合在同一個 l_d 發散(若不穩定流形上耦合矩陣正定) → 指數排序無歧義(不會有中間值打平) → 應用到兩腿梯，**判定一個號稱的相變其實是連續 crossover**，解決長年爭議。

**(d) 買到什麼**：8 個耦合壓成 4 個關聯階；最陡的那個(c22^σ, γ=1)**單獨決定**哪個自旋能隙打開；跨系統通用(鐵基、1D Hubbard)。

**(e) 框架句**：
> "It is rather subtle to tell which couplings are relevant... The exponents provide an alternative way to classify without any ambiguity."
> "A non-trivial connection between RG flows in the perturbative regime and those in the singular regime."

---

## 跨篇綜合 — W02 的框架

**F1（貫穿三篇）：把動力學變成幾何。** 面對「解不動的耦合非線性流」，不去硬解軌跡，而是找出**位勢/單調函數**把動力學關進一個地景裡——地景的形狀(單調性)反過來約束動力學(禁止混沌)。「by topology, not approximation」。這是**新招式候選 M11**。

**F2（三篇的共同引擎）：換對表象讓難變換變成對角/平凡。** Majorana 使對稱化變換 L 對角——這是 [[M09 換表象顯形]] 的再確認與細化：M9 的一個具體戰術是「換到讓所需變換變對角的基底」。→ 回寫 M9 細枝。

**F3：所有候選都 marginal 時，用『逼近奇異點的冪次』排序，不用量值。** 當一堆量在同一尺度看起來一樣大，判別器是**它們各自衝向臨界點的速率指數**，不是當下的值。→ 這細化 [[M01 在可控處計算]] 的「普適性簽名」：不只找不變量，還要**用漸近速率給競爭者排序**。（候選 M12，但傾向併入 M1，見 scorecard 判定。）

→ M11 走盲測(G3-B)；M12 傾向降級為 M1 細枝；M9 得一條新戰術。依 D0，寧可少加一個招式也不灌水。
