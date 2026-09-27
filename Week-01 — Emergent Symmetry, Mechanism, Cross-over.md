---
tags: [Lin-Hsiu-Hau, study-program, week-01]
created: 2026-07-04
papers: [cond-mat/9801285, cond-mat/0001320, 2109.12608]
---

# Week 01 — 三篇全文精讀

讀法：每篇記 (a) 選題理由 (b) 樞紐思考移動 (c) 論證鏈 (d) 驗證/證偽 (e) 可教學框架句。

---

## 論文 1 · SO(8) Exact Symmetry in the Two-Leg Ladder
Lin, Balents, Fisher · cond-mat/9801285 (PRB 58, 1794, 1998) · 257 引用

**(a) 選題理由**：1D 通常可解但缺自旋能隙與配對；2D 太難；兩腿梯是「剛好夠複雜、又夠可控」的中間地帶，且對應真實材料（coupled-ladder 化合物、碳奈米管，交互作用 ∝ 1/半徑）。他挑的是可用弱耦合誠實計算、又能觸及 cuprate 物理的最小系統。

**(b) 樞紐移動**：*把對稱性從「假設」變成「被發現」*。路線是四步驟接力：
1. 弱耦合 RG：9 個邊際耦合的流方程 ∂ℓgᵢ = Aᵢⱼₖgⱼgₖ
2. 發現**特殊射線**：成長中耦合的比值趨近固定常數，**與初始強度無關**（普適的訊號）
3. Bose 化 + 場重定義（第四對 θ↔φ 對調）→ Hamiltonian 塌成極簡對稱形式
4. Re-fermionize → 8 個 Majorana 場 → 正是 SO(8) Gross-Neveu 模型（已知可積）

對稱性一直都在，只是「藏在非局域變數裡」；bare 電子基底看不到，Majorana 基底才顯形。

**(c) 論證鏈**：模型/Bose 化 → RG 流到特殊射線 → D-Mott 相 → refermionize 得 GN → 找出 SO(8)⊃SO(5)（對上 Zhang 統一磁性與超導的提案）→ 用 triality（N=8 獨有）與可積性抽出全部 52 個粒子態、束縛態、關聯函數 → 摻雜後仍可積，預測自旋能隙不連續跳變。

**(d) 驗證/證偽**：(i) 湧現的 SO(5) 對上獨立提出的 Zhang 對稱 → 一致性檢驗；(ii) triality 預測的 magnon–Cooper pair 束縛，早期 DMRG 已見；(iii) 可積性給出銳利譜峰的精確能量 m, √3m，可直接與結構因子比對。

**(e) 框架句**：
> "As is often the case, abelian bosonization masks the full symmetry group."
> "The Hamiltonian can be written locally in the 'fundamental' fermion variables, which are highly non-locally related to the bare electron operators."
> 比值「independent of the initial coupling strengths」= 普適性的簽名。

---

## 論文 2 · Theory of Diluted Magnetic Semiconductor Ferromagnetism
König, Lin, MacDonald · cond-mat/0001320 (PRL 84, 5628, 2000) · 403 引用（他最高引）

**(a) 選題理由**：(Ga,Mn)As 的 Tc 高得意外（>100 K），但既有理論只做到 mean-field / 靜態 RKKY，抓不到有序態的**基本激發**。他問的不是「有沒有鐵磁」而是「有序態長什麼樣、被什麼漲落限制」。

**(b) 樞紐移動**：*把可精確處理的自由度精確積掉，但保留它的動態印記*。載子在 Hamiltonian 中是雙線性 → 可嚴格積分 → 得到雜質自旋的有效作用量，帶**推遲、非局域**交互作用。這一步生出三支激發（Goldstone magnon／載子主導的光學支／Stoner 連續），全是 mean-field 看不到的。

**(c) 論證鏈**：反常高 Tc → mean-field 不足 → coherent-state 路徑積分（HP 玻色子＋費米載子）→ 積掉載子 → 有效作用量展到二階得色散 → 解析延拓得譜密度 → 自洽自旋波處理 Tc。

**(d) 驗證/證偽**：自旋剛度 ρ ∝ 1/(載子質量) 且**與交換耦合 Jpd 無關** —— 這與 mean-field 的 Tc 標度完全不同，是可判別的指紋。低溫 M(T)~T^{3/2}；Tc 處比熱有 ~5% 跳變（可量測）；光學支能隙 Δ(1−x) 在 RKKY 圖像中不存在。

**(e) 框架句**：
> "While the RKKY picture provides a realistic estimate of Tc, it completely fails as a theory of the ferromagnetic state."
> "The physics of the itinerant carriers is embedded in the effective action of the magnetic ions... responsible for the retarded and non-local character of the interactions, described here for the first time."
> 邏輯序：反常觀測 → 舊圖像不足 → 精確積掉載子、保留關聯 → 新激發湧現 → 剛度與耦合脫鉤 → 定量可證偽預測。

---

## 論文 3 · U(1) Dynamics in Neuronal Activities
Lin et al. · 2109.12608 (2021)

**(a) 選題理由**：rate model 把神經元壓成一個發放率純量，丟掉「輸入在發放週期的哪個相位到達」這個關鍵資訊。他問：發放率是否足以描述神經動力學？

**(b) 樞紐移動**：*帶著凝態工具跨界，找最小充分模型而非生物寫實*。把神經元態編碼成複變 z = r·e^{iφ}，借 Ginzburg-Landau 再加非平衡相位轉動：
| 物理量 | 神經意義 |
|---|---|
| r 振幅 | 發放振幅／膜電位包絡 |
| φ 相位 | 動作電位週期內的時間位置（φ=0 峰、φ=π 過極化谷） |
| U(1) 轉一圈 | 一個完整發放週期 |
| Ω(φ) 角速度 | 相位依賴的瞬時速率 |

**(c) 論證鏈**：HH 神經元的 mode-locking 平台（ν=n·ν_ac）暗示隱藏相位結構 → 從 HH 模擬數值抽出 Ω(φ)，發現非均勻轉動：φ≈π 的**瓶頸**（慢，限速）與 φ≈0 的**旋風**（快，無關）→ 用三次 Lyapunov 位能重建 HH 動作電位與增益曲線 → 三種經典分岔（SNIC／super/subcritical Hopf）統一為徑向 vs 相位不動點碰撞 → 網路層預測自發非同步發放（SAF）當 σ>σ_c。

**(d) 驗證/證偽**：發放率由瓶頸幾何決定（相位不再是率的導數，而是反過來）；相位依賴突觸效力（突觸在後神經元 φ≈π 時最有效）；SAF 相在特定連結強度出現，可在神經培養測試。

**(e) 框架句**：
> "The key is to grab the essential features... so that model building for different purposes can be facilitated."（最小充分模型）
> "The firing rate is dictated by the bottleneck."（率是相位幾何的結果，不是起點）
> "The broken U(1) symmetry is manifest. Therefore, SAF phase is anticipated."（對稱破缺 → 預測網路集體相）

---

## 本週跨篇綜合 — 三篇共享的底層動作

**核心框架 F1（貫穿三篇）：換到讓隱藏結構顯形的表象（representation）。**
- SO(8)：refermionize → Majorana 基底，對稱才 manifest（"bosonization masks the symmetry"）
- DMS：積掉載子 → 有效作用量表象，基本激發才現身
- U(1)：複變相位 z=re^{iφ} 表象，發放率的機制（瓶頸）才看得見
> 智力工作的重心不在「解方程」，而在「找到正確的變數變換」。物理都在，變數對了才看得見。

**核心框架 F2：把可精確處理的部分積掉，保留其動態印記。**
- DMS 積掉雙線性載子（嚴格）；SO(8) 積 RG 流到不動射線。剩下的有效理論帶著被積掉部分的推遲/非局域記憶。

**核心框架 F3：獵捕與微觀細節無關的量。**
- SO(8) 比值「與初始耦合無關」；DMS 剛度「與交換耦合無關」；U(1)「最小充分、非寫實」。
- 反覆尋找不依賴髒細節的普適量 —— 那才是物理。

**核心框架 F4：先問「有序態/激發長什麼樣」，而非「有沒有」。**
- DMS 不問有無鐵磁，問被什麼漲落限制；SO(8) 不止求基態，求完整粒子譜；U(1) 不止求發放，求相位幾何。存在性是入場券，激發結構才是論文。

→ F1、F2 蒸餾成新的 mentor 招式 M9、M10；F3 併入 M1、F4 併入 M5（見 Scholarly Profile 更新）。
