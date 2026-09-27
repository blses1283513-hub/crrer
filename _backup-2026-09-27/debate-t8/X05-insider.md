OBJECTION 1
- type: factual
- target step: 「疫苗量產放大的黑盒」段落：「回饋迴路：一批發酵/純化 → 送檢 → 數週後才知道這批"好不好"…」；以及後段「秒級線上學習這件事本身…疫苗的關鍵 assay 是週級，這代表"線上學習"在生物端物理上不成立」
- failure case: 這個斷點把整個生物端回饋迴路的速度上限，等同於「離線放行 assay（potency/immunogenicity/sterility）」的速度，但商業 GMP 生產早已部署即時 PAT（Raman 光譜等）做製程內（in-process）CQA/CPP 監控：已開文獻顯示 Raman 在 500 L CHO 細胞培養槽中每 2 小時取樣一次、在 15 L 回饋控制槽中每 6 分鐘取樣一次，且「from laboratory scale to GMP production」都在用，FDA 2004 PAT 框架與後續 FDA/EMA/日本自 2009 年起的指引都支持「continuous real time quality assurance」。也就是說，「線上學習」在生物端並非物理上不成立——培養階段的製程參數迴路可以是分鐘級，真正卡住的只是「放行決策」這一段的週級 assay。把兩者混為一談，會讓「不能搬」的結論過度延伸到「連線上監控都不能搬」，但實際上可搬的範圍比草稿講的大。
- source: https://pmc.ncbi.nlm.nih.gov/articles/PMC5233728/
- severity: major
- would resolve it: 把「回饋迴路頻率」拆成兩層分開計價——(a) 製程內 CPP/CQA 監控頻率（PAT 已可達分鐘級，可搬）與 (b) 批次放行決策頻率（potency/sterility 仍是週級，不可搬）；草稿目前的量級差距（10^4–10^5 倍）只對 (b) 成立，對 (a) 不成立，應分別標注。

OBJECTION 2
- type: missing-field-knowledge
- target step: 開場「疫苗量產放大的黑盒」把「疫苗」當單一黑盒處理（培養基、生物反應器條件、細胞株漂移、代謝異質性…）
- failure case: 疫苗製造平台之間的失敗機制差異，本身就是 relevant 因子，草稿卻把它壓進單一黑盒。以 mRNA 疫苗為例：核心 mRNA 合成反應（IVT，體外轉錄）本身只需約 7 天、且是無細胞（cell-free）酵素反應，瓶頸其實在 DNA 模板製備（最長可達一個月），這與草稿假設的「細胞株漂移、代謝異質性」（活細胞培養/發酵特有的失敗模式）機制完全不同。換句話說，「不能搬」的具體原因（生物噪聲、細胞株漂移）對 mRNA 平台的適用性遠低於對傳統活細胞培養（蛋白次單位、去活化疫苗）平台，草稿的黑盒定義沒有先做平台分流，會讓後面「relevant 因子」的判斷對不同疫苗技術平台其實不是等價適用的。
- source: https://cepi.net/pushing-mrna-vaccine-development-timelines-new-speeds
- severity: major
- would resolve it: 在「定義兩邊黑盒」這一步先按疫苗生產平台分流（mRNA/IVT 無細胞 vs. 活細胞培養/發酵 vs. 蛋白次單位純化），再分別套用「哪些能搬、哪些不能」的四個 relevant 因子，而不是用單一疫苗黑盒代表全部平台。

OBJECTION 3
- type: jargon
- target step: 「跨域物理橋接」兩個表格與其後的「深談」段落，例如「Abrikosov-Gorkov pair-breaking」「pair-breaking 截面」「相位相干性、恢復長度」「RG 流向固定點」「臨界指數」
- failure case: 這篇文件實際要回答的讀者是關心半導體良率工程或疫苗製程放大的人（產業/法規/製程背景），不是凝態物理背景。「pair-breaking 截面」「RG 流固定點」「臨界指數」這些詞對這群讀者是不可解的術語，而且這兩個橋接段落最終也沒有改變「能搬/不能搬」的具體結論——結論仍是分流表裡列的四個 relevant 因子。留著這兩段等於用物理黑話包裝一個本可以用工程語言講完的結論，增加閱讀成本但沒有增加可操作資訊。
- source: none
- severity: minor
- would resolve it: 把「跨域物理橋接」兩段改寫成工程語言版本（例如：「良率模型 vs 生物失效模型」只講「外生獨立顆粒 vs 內生批次相關噪聲」的差異，不必引入超導序參量或 RG 語言），或明確標註「本段為附加類比，非結論依據，物理背景讀者可跳過」。
