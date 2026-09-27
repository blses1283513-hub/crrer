OBJECTION 1
- type: wasted-depth
- target step: "缺陷密度模型 Y=exp(-D0·A) ↔ Abrikosov-Gorkov pair-breaking...一旦你想往動力學（相干長度、臨界指數）推,就斷了"（橋接一）
- failure case: 這段換算並未新增任何會改變「哪些工具能搬/哪些不能搬」清單的資訊——SPC/DOE/PCA 能搬、Poisson/Murphy 模型不能搬的判斷在「直接回答」段落已經獨立成立。拿掉超導類比，決策者要做的事（用 SPC 監控 CQA、不要套 Poisson 良率公式）完全不變。
- severity: major
- would resolve it: 若能指出這段類比帶出了一個「直接回答」段落沒有的新可搬工具或新斷點，就保留；否則 cut。

OBJECTION 2
- type: wasted-depth
- target step: "每一輪「量測缺陷圖→調製程→再量測」↔ 一步 RG 迭代...同一個幾何圖像,兩邊迭代預算差了兩三個數量級"（橋接二）
- failure case: 實質內容（迭代預算差 2–3 個數量級）已在推理步驟(4) 用白話講過一次（回饋迴路 10^4–10^5 倍）。RG 語言沒有再產生新的可測數字或新的行動項，只是換一種說法重講同一件事——對要決定「該不該投資良率學習法」的人，讀不讀這段結論不變。
- severity: major
- would resolve it: 若 RG 框架能導出一個獨立於「回饋迴路頻率差距」的新可觀測量（例如流向固定點所需的最少批數的具體估計式），才值得留；否則 cut，只留數量級數字。

OBJECTION 3
- type: untestable
- target step: "自評信心: medium（跨半導體/生物製程兩個產業的具體工程細節，本人非該領域一線工程師，框架與量級判斷有把握，但生物製程的量化細節需要業界資料驗證）"
- failure case: 沒有寫出「業界資料」具體指什麼、要看到什麼數字才會把信心從 medium 調到 high 或調到 low。決策者無法用這句話決定現在能不能先按「能搬清單」動手，還是要等驗證。
- severity: minor
- would resolve it: 明確寫出門檻，例如「若能取得 ≥3 家藥廠的批次失敗變異度歷史資料，且變異源以批次相關（非隨機顆粒式）為主，信心調高到 high；若拿不到這類資料，維持 medium 且不建議先投資 SPC 導入」。
