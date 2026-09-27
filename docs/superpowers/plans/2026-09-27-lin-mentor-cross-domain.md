# Lin Mentor Cross-Domain Brain — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the `lin-hsiu-hau-mentor` agent into a measurable cross-field "brain": a cross-field test set with sourced answer notes, a slimmer agent, a 4-critic debate skill at conclusion points, and outcome storage that grows sharper, not larger.

**Architecture:** All artifacts are Markdown files. The agent (`~/.claude/agents/`) keeps only the thinking core; procedures move to `lin-study/protocols/`. A new skill `lin-debate` (`~/.claude/skills/`) runs in the main conversation, dispatches role subagents, judges, and writes to a three-level store (`lin-study/memory/` index + cards, `lin-study/debates/` archive). "Tests" are shell checks (existence, grep, byte counts) plus blind subagent runs graded against user-approved answer notes.

**Tech Stack:** Markdown, Git Bash (`grep`, `sed`, `wc`, `cp`, `diff`), Claude Code Agent / SendMessage tools, WebSearch/WebFetch (Field insider only).

**Spec:** `C:\Users\Ande\Desktop\NTHU\aa\docs\superpowers\specs\2026-09-27-lin-mentor-cross-domain-design.md`

## Global Constraints

- Vault root `V` = `C:\Users\Ande\Desktop\NTHU\aa` (Git Bash: `/c/Users/Ande/Desktop/NTHU/aa`). `L` = `$V/M_Lectrues/lin-study`. Agent file `A` = `~/.claude/agents/lin-hsiu-hau-mentor.md`.
- The vault is **not a git repo**. Instead of commits: back up to `$L/_backup-2026-09-27/` before editing, and log each finished task in `$L/_backup-2026-09-27/CHANGELOG.md`.
- Core size is measured in **bytes** (`wc -c`). Caps: agent body (below front matter) ≤ **11,500** bytes (was 17,560); Hub ≤ **50 lines** and ≤ **4,000** bytes (was 46 lines / 3,399 bytes); moves (M + G) ≤ **15**.
- Kernel moves (M-series) need Lin-paper provenance (G1). Grown moves (G-series) enter via G2–G5 + budget + G-K kernel check; source recorded, not required to be Lin.
- Debate runs **only at conclusion points** (closing a classic question, finishing teaching material, any cross-field claim, promoting a move) or on 「開辯論」. Max 2 rounds. 4 critics every time.
- Exact high-confidence card hit (not past recheck) → answer from card, **no debate**. 「重新辯論」 forces a full debate.
- Politics probes ask about mechanisms and observables only, never which side is right.
- Grader notes: every required item needs a published source (URL/DOI) or is marked `unsourced` and excluded from scoring. **No X-probe run before the user writes `approved: YYYY-MM-DD` in the grader-notes front matter.**
- Hard safety rules stay inline in the agent: no voice synthesis/playback; never invent citations; news = verified public professional facts only.
- Language of vault notes: Chinese with English technical terms (match existing notes).

---

## File map

| File | Responsibility | Task |
|---|---|---|
| `$L/_backup-2026-09-27/` | pre-change copies + CHANGELOG | 1 |
| `$L/00 - Lin Thinking Hub.md` | boot note; M1–M11 fix; links to new areas | 1, 10 |
| `$L/deployment-lessons.md` | M1–M11 fix (line 9) | 1 |
| `$L/protocols/{news-update,dashboard,weekly-study,corpus-refresh,teaching-material}.md` | procedures moved out of the agent, verbatim | 2 |
| `A` | slimmed thinking core + routing + conclusion block | 3 (M7 line: 9) |
| `$L/verification/probe-bank.md` | + X01–X12 | 4 |
| `$L/memory/{index.md, insights-queue.md, efficiency-ledger.md, cards/}` | outcome storage | 4 |
| `$L/debates/00-review-log.md` | debate archive + review log | 4 |
| `$L/verification/probe-grader-notes.md` | sourced answer notes, user-approved | 5 |
| `$L/verification/X-baseline-2026-09.md` | baseline + debate comparison | 6, 8 |
| `~/.claude/skills/lin-debate/SKILL.md` + `references/roles/*.md` | debate orchestration + 4 role prompts | 7 |
| `$L/verification/W-X-scorecard.md` | bridge-audit gate results | 9 |
| `$L/moves/M07 誠實計價的跨界.md` | + sub-tactic only if gates pass | 9 |
| `$L/curriculum.md` | W09–W10 next | 10 |
| memory `lin-hsiu-hau-mentor-agent.md` + `MEMORY.md` | durable record of new structure | 10 |

---

### Task 1: Backups + stale M1–M10 references

**Files:**
- Create: `$L/_backup-2026-09-27/` (copies), `$L/_backup-2026-09-27/CHANGELOG.md`
- Modify: `$L/00 - Lin Thinking Hub.md:11`, `:32`; `A:48`; `$L/deployment-lessons.md:9`

**Interfaces:**
- Produces: backup copies used by Task 2 (verbatim line extraction) and Task 3 (regression "old" arm).

- [ ] **Step 1: Write the failing check**

```bash
L="/c/Users/Ande/Desktop/NTHU/aa/M_Lectrues/lin-study"; A=~/.claude/agents/lin-hsiu-hau-mentor.md
grep -c "M1–M10" "$L/00 - Lin Thinking Hub.md" "$A" "$L/deployment-lessons.md"
```

- [ ] **Step 2: Run it — expect FAIL (non-zero counts)**

Expected: `Hub:2`, `agent:1`, `deployment-lessons:1`.

- [ ] **Step 3: Back up, then fix**

```bash
L="/c/Users/Ande/Desktop/NTHU/aa/M_Lectrues/lin-study"; A=~/.claude/agents/lin-hsiu-hau-mentor.md; B="$L/_backup-2026-09-27"
mkdir -p "$B"
cp "$A" "$B/lin-hsiu-hau-mentor.md"
cp "$L/00 - Lin Thinking Hub.md" "$L/curriculum.md" "$L/deployment-lessons.md" "$L/verification/probe-bank.md" "$L/moves/M07 誠實計價的跨界.md" "$B/"
printf '# CHANGELOG 2026-09-27 — Lin mentor cross-domain build\n\n' > "$B/CHANGELOG.md"
sed -i 's/M1–M10/M1–M11/g' "$L/00 - Lin Thinking Hub.md" "$L/deployment-lessons.md"
sed -i '48s/(M1–M10)/(M1–M11)/' "$A"
echo "- Task 1: backups; M1–M10 → M1–M11 in Hub (2x), agent:48, deployment-lessons:9" >> "$B/CHANGELOG.md"
```

- [ ] **Step 4: Run the check — expect PASS**

```bash
grep -c "M1–M10" "$L/00 - Lin Thinking Hub.md" "$A" "$L/deployment-lessons.md"   # all :0
diff -q "$B/lin-hsiu-hau-mentor.md" "$A"                                            # differs (line 48 only)
diff "$B/lin-hsiu-hau-mentor.md" "$A" | grep -c '^<'                                # 1
```

---

### Task 2: Move procedures into `protocols/` (verbatim)

**Files:**
- Create: `$L/protocols/news-update.md`, `dashboard.md`, `weekly-study.md`, `corpus-refresh.md`, `teaching-material.md`

**Interfaces:**
- Consumes: `$B/lin-hsiu-hau-mentor.md` line numbers (verified 2026-09-27): Dashboard 103–104 · Industry Watch 106–111 · Weekly Study 113–114 · Verification 116–123 · Corpus-Refresh 125–128 · Teaching-Material 130–136.
- Produces: 5 files whose paths Task 3's routing table references exactly.

- [ ] **Step 1: Write the failing check**

```bash
L="/c/Users/Ande/Desktop/NTHU/aa/M_Lectrues/lin-study"
for f in news-update dashboard weekly-study corpus-refresh teaching-material; do test -s "$L/protocols/$f.md" && echo "ok $f" || echo "MISSING $f"; done
```

- [ ] **Step 2: Run it — expect 5× MISSING**

- [ ] **Step 3: Extract**

```bash
L="/c/Users/Ande/Desktop/NTHU/aa/M_Lectrues/lin-study"; B="$L/_backup-2026-09-27/lin-hsiu-hau-mentor.md"; P="$L/protocols"; mkdir -p "$P"
hdr(){ printf -- '---\ntags: [Lin-Hsiu-Hau, protocol]\nmoved-from: ~/.claude/agents/lin-hsiu-hau-mentor.md (2026-09-27, verbatim)\ntrigger: %s\n---\n\n' "$1"; }
{ hdr "「更新林教授動態」";        sed -n 106,111p "$B"; } > "$P/news-update.md"
{ hdr "dashboard questions";       sed -n 103,104p "$B"; } > "$P/dashboard.md"
{ hdr "「本週研讀」/「繼續研讀林秀豪」"; sed -n 113,114p "$B"; echo; sed -n 116,123p "$B"; } > "$P/weekly-study.md"
{ hdr "「優化指導員」";            sed -n 125,128p "$B"; } > "$P/corpus-refresh.md"
{ hdr "做成教材 / teaching material"; sed -n 130,136p "$B"; } > "$P/teaching-material.md"
echo "- Task 2: protocols/ created (5 files, verbatim from agent 103–136)" >> "$L/_backup-2026-09-27/CHANGELOG.md"
```

- [ ] **Step 4: Run the checks — expect PASS**

```bash
for f in news-update dashboard weekly-study corpus-refresh teaching-material; do test -s "$P/$f.md" && echo "ok $f"; done
grep -l "lin-news.js" "$P/news-update.md"
grep -l "G3 Behavioral delta" "$P/weekly-study.md"
grep -l "export.arxiv.org" "$P/corpus-refresh.md"
grep -l "Mandatory reader test" "$P/teaching-material.md"
grep -l "voice/audio feature was deliberately removed" "$P/dashboard.md"
```
Expected: 5× `ok`, and each grep prints its file path.

---

### Task 3: Slim the agent + regression check

**Files:**
- Modify (rebuild): `A`
- Create: `$L/_backup-2026-09-27/regression-P01-P06.md`

**Interfaces:**
- Consumes: `$B/lin-hsiu-hau-mentor.md` (verbatim ranges: front matter 1–44 · worldview 54–71 · moves header+M1–M11 72–85 · session protocol 90–96 · language+output 97–102); `protocols/*.md` from Task 2.
- Produces: the `## 結論草稿` block format that Task 7's skill parses — exact field labels: `主張`, `推理步驟`, `因子分類`, `使用招式`, `跨域橋接`, `自評信心`.

- [ ] **Step 1: Write the failing check**

```bash
A=~/.claude/agents/lin-hsiu-hau-mentor.md
body_bytes(){ awk 'f>=2{print} /^---$/{f++}' "$1" | wc -c; }
echo "body bytes: $(body_bytes "$A") (cap 11500)"
for s in "## 結論草稿" "protocols/news-update.md" "Relevance filter" "No audio playback"; do grep -qF "$s" "$A" && echo "has: $s" || echo "LACKS: $s"; done
```

- [ ] **Step 2: Run it — expect FAIL**: body ≈ 17,5xx bytes; 4× `LACKS`.

- [ ] **Step 3: Write the new-section fragments**

Create `$L/_backup-2026-09-27/frag-identity-boot.md` with exactly:

```markdown
You are a thinking mentor modeled on Prof. Lin Hsiu-Hau (林秀豪), Distinguished Professor of Physics at NTHU — statistical field theorist, condensed matter physicist, National Excellent Teacher Award winner, famous for replacing thick textbooks with 10 handwritten classic questions per semester. You teach ANY subject — physics, industry, culture, politics, biology — the way he enters a new field.

**Boot sequence:** read ONE file first: `C:\Users\Ande\Desktop\NTHU\aa\M_Lectrues\lin-study\00 - Lin Thinking Hub.md` (one-line moves M1–M11, teaching loop, links). Open deeper notes only when needed:
- A move fires → its branch note `lin-study/moves/Mxx *.md` (grown moves: `Gxx *.md`).
- Citing his research → `M_Lectrues\Lin Hsiu-Hau — Scholarly Profile.md` (real arXiv IDs; never invent citations).
- His lecturing voice/quotes → `M_Lectrues\Lecture Notes - Quantum Scattering & Dirac Equation.md`.
- A procedure is triggered → the file in the Routing table below.
Physics topics covered there: read and cite. Other subjects: transfer the method, not the content.

```

Create `$L/_backup-2026-09-27/frag-d0-relevance.md` with exactly:

```markdown
**D0 (supreme guardrail, overrides every procedure):** depth-first — nothing licenses breadth; a field drilled beats two fields surveyed. Ask "what can I cut" before "what can I add"; build a question's instrument only while drilling it. Curriculum-design lessons D1–D9: `lin-study/deployment-lessons.md` (read when designing the 10 questions for a new field).

**Relevance filter (before drilling any real-world question):** sort every factor — **relevant** (changes the conclusion or the action → drill), **marginal** (changes confidence only → one sentence), **irrelevant** (name once, then drop). Depth goes to relevant factors only; this is D0, not a breach of it.

```

Create `$L/_backup-2026-09-27/frag-conclusion-routing.md` with exactly:

```markdown
**Conclusion points:** when you close a classic question, finish teaching material, make any claim that combines fields, or propose a new/refined move, end your output with this block (field labels exact):

## 結論草稿
- 主張: <one-sentence claim>
- 推理步驟: <numbered steps>
- 因子分類: relevant: … / marginal: … / irrelevant: …
- 使用招式: <M/G numbers>
- 跨域橋接: <for each bridge: mapping · unmapped items · break point; or "none">
- 自評信心: high | medium | low

The main conversation runs the `lin-debate` skill on this block. You cannot start subagents; never simulate the debate yourself. Ordinary Socratic steps, derivations in progress and ☆ homework exchanges get no block.

**Routing (open the file only when triggered; paths under `C:\Users\Ande\Desktop\NTHU\aa\M_Lectrues\lin-study\`):**
| Trigger | File |
|---|---|
| 「更新林教授動態」 | `protocols/news-update.md` |
| 「本週研讀」/「繼續研讀林秀豪」 | `protocols/weekly-study.md` (+ `verification/protocol.md`) |
| 「優化指導員」 | `protocols/corpus-refresh.md` |
| 做成教材 / teaching material | `protocols/teaching-material.md` |
| dashboard questions | `protocols/dashboard.md` |

```

Create `$L/_backup-2026-09-27/frag-boundaries.md` with exactly:

```markdown

**Boundaries (hard rules, always in force):**
- You are a persona modeled on public teaching materials and the user's own lecture notes; if asked for Prof. Lin's personal opinions not in the notes, say the real professor's view is unknown and give your best reasoning in his spirit, clearly labeled.
- Never invent citations; every paper needs an arXiv ID or DOI.
- No audio playback or voice synthesis of Prof. Lin (removed 2026-07-04 at the user's request; do not reintroduce).
- News: only publicly verifiable professional facts with a source URL; anything unverified gets `verified: false` + 待查證; never collect personal/private information.
- Depth over coverage: if the student asks for a broad survey, push back once and offer the 10-classic-questions alternative.
```

- [ ] **Step 4: Assemble the new agent**

```bash
L="/c/Users/Ande/Desktop/NTHU/aa/M_Lectrues/lin-study"; B="$L/_backup-2026-09-27"; O="$B/lin-hsiu-hau-mentor.md"; A=~/.claude/agents/lin-hsiu-hau-mentor.md
{ sed -n 1,44p "$O"
  cat "$B/frag-identity-boot.md"
  sed -n 54,71p "$O"
  sed -n 72,85p "$O"
  cat "$B/frag-d0-relevance.md"
  sed -n 90,96p "$O"
  cat "$B/frag-conclusion-routing.md"
  sed -n 97,102p "$O"
  cat "$B/frag-boundaries.md"
} > "$A.new" && mv "$A.new" "$A"
sed -i 's/(M1–M10)/(M1–M11)/' "$A"   # no-op safety if the O copy predates Task 1
```

- [ ] **Step 5: Run the Step 1 check — expect PASS**

Expected: body bytes ≤ 11,500; 4× `has:`. Also:

```bash
grep -c "^- \*\*M[0-9]" "$A"          # 11
grep -c "Industry Watch Protocol\|Teaching-Material Production Protocol" "$A"   # 0
head -3 "$A"                          # front matter intact: ---, name: lin-hsiu-hau-mentor, description...
```
If body bytes > 11,500: shorten `frag-conclusion-routing.md` prose (never the M-lines or worldview) and re-assemble.

- [ ] **Step 6: Regression — blind run P01 and P06 on old vs new text (4 subagents, parallel)**

Dispatch 4 `general-purpose` agents in one message. Prompt template (fill `<BODY>` with the agent body — old = `awk 'f>=2{print} /^---$/{f++}' "$O"`, new = same on `$A` — and `<PROBE>`):

```
You are playing the mentor defined below. You have NO tools: do not read files, search, or run commands; answer only from this text.
=== MENTOR DEFINITION ===
<BODY>
=== END ===
Student question: <PROBE>
Answer as the mentor, in the student's language, ≤400 words.
```
Probes (verbatim from probe-bank): P01 「我有一維雙原子鏈的 tight-binding 哈密頓量，卡在判斷它拓不拓撲。給我方向。」 · P06 「我的模型 mean-field 解看起來很漂亮，該不該就這樣寫進論文？」

Pass criteria (judge = main thread): P01 answer (old and new) names a representation change such as writing H(k)=d(k)·σ and checking the winding of d(k). P06 answer (old and new) names integrating out the exactly solvable/bilinear sector while keeping its retarded memory (not a static average). Record verbatim key sentences + verdict in `$B/regression-P01-P06.md`.
**If new fails where old passes:** restore `cp "$O" "$A"`, find which dropped text carried the move, add it back to a fragment, re-assemble, re-run.

- [ ] **Step 7: Log**

```bash
echo "- Task 3: agent slimmed to $(awk 'f>=2{print} /^---$/{f++}' "$A" | wc -c) body bytes; regression P01/P06 → see regression-P01-P06.md" >> "$B/CHANGELOG.md"
```

---

### Task 4: X-probes + storage skeleton

**Files:**
- Modify: `$L/verification/probe-bank.md` (append)
- Create: `$L/memory/index.md`, `$L/memory/insights-queue.md`, `$L/memory/efficiency-ledger.md`, `$L/memory/cards/.keep`, `$L/debates/00-review-log.md`

**Interfaces:**
- Produces: probe IDs X01–X12; index line format and card format (used by Task 7 skill and Task 8); ledger columns (used by Tasks 6, 8, 9).

- [ ] **Step 1: Failing check**

```bash
L="/c/Users/Ande/Desktop/NTHU/aa/M_Lectrues/lin-study"
grep -c "^- \*\*X[0-9][0-9]" "$L/verification/probe-bank.md"; ls "$L/memory" "$L/debates" 2>&1 | head -3
```
Expected: `0`, and "No such file or directory".

- [ ] **Step 2: Append probes** — append exactly this to `probe-bank.md`:

```markdown

## 跨域 probes (X-series, 2026-09-27)

> 用途：測量「跨領域組合」能力。規則同上：用過即標 [used]。政治題只問機制與可觀測量，不問立場。評分依 `probe-grader-notes.md`（須使用者核可後才能用）。
> 分組：**baseline**＝X01, X03, X05, X07, X10, X11（Task 6 使用即燒）；**held-out**＝X02, X04, X06, X08, X09, X12（留給 G3）。

### 單域遷移 (transfer)
- **X01 文化** — 為什麼有些節慶習俗能跨世代存活，有些在一代內就消失？
- **X02 娛樂** — 一個劇種（例如韓國復仇劇）爆紅後，為什麼幾年內就退燒？怎麼分辨是題材疲乏還是平台演算法改變？
- **X03 政治** — 多黨聯合政府為什麼有的撐滿任期、有的幾個月就垮？要看哪些可觀測量才能判斷一個聯盟穩不穩？
- **X04 生物** — 醫院停用某種抗生素後，抗藥菌為什麼不一定會消失？

### 雙域橋接 (bridge)
- **X05 半導體×生物** — 晶圓廠的良率學習（yield learning）方法能不能搬去加速疫苗量產放大？哪些能搬、哪些不能？
- **X06 半導體×政治** — 半導體供應鏈的「單點瓶頸」分析，能不能拿來評估一國的出口管制會不會奏效？
- **X07 娛樂×經濟** — 串流平台的內容投資像不像創投的冪律報酬？這個類比能推出什麼可檢驗的預測？
- **X08 文化×演化** — 把語言/迷因傳播當成演化（複製–變異–選擇）來分析，什麼時候有解釋力、什麼時候只是換詞？
- **X09 政治×網路** — 城市之間互相模仿政策，能不能用網路上的傳染模型描述？模型要測到什麼才算數？

### 假橋陷阱 (trap — 最佳答案要指出類比在哪裡斷)
- **X10** — 股市崩盤像相變/臨界現象，所以可以用臨界指數預測崩盤時間吧？
- **X11** — 輿論兩極化就像鐵磁體的自發對稱破缺，所以只要加一個「外場」（政府宣導）就能把它對齊，對吧？
- **X12** — DRAM 要定期 refresh 防止電荷流失，就像人要複習防止遺忘，所以最佳複習間隔可以用 DRAM retention 分佈來算？
```

- [ ] **Step 3: Create storage files** — exact contents:

`$L/memory/index.md`:
```markdown
---
purpose: 結論索引（hot tier）— 每張卡一行；主線以關鍵字 grep，不整檔讀入
cap: 60 lines of entries
line-format: "- C### · kw: k1, k2, k3 · <一句主張> · conf: high|medium|low · used: YYYY-MM-DD · recheck: YYYY-MM-DD|none · [[cards/C###]]"
---

# Lin Brain — Conclusion Index

```

`$L/memory/insights-queue.md`:
```markdown
---
purpose: 思考模式候選佇列 — 每場辯論至多一行；啟動時不載入；每 5 場辯論 review 時競爭升格（G 候選或 D 候選）
line-format: "- YYYY-MM-DD · from [[debates/<record>]] · G|D candidate · <one-line pattern stated as a tool, not a conclusion>"
---

# Insights Queue

```

`$L/memory/efficiency-ledger.md`:
```markdown
---
purpose: 核心大小 vs 測驗分數帳本 — 核心變更只在「分數升且大小不增」或「分數同且大小減」時接受
core: agent body bytes (below front matter) + Hub bytes
caps: agent body ≤11500 · Hub ≤50 lines & ≤4000 bytes · moves ≤15
---

# Efficiency Ledger

| date | change | agent body B | Hub B | core B | probe set | score | verdict |
|---|---|---|---|---|---|---|---|
```

`$L/debates/00-review-log.md`:
```markdown
---
purpose: 辯論存檔目錄（cold tier）＋每 5 場 review 紀錄。啟動時不載入。
review-rule: 每 5 場 — (1) 重複 ≥3 次的反對模式與 insights-queue 競爭升格（G2–G5+G-K+預算）；(2) 同題卡片合併；(3) 90 天未用且非 high 的卡移出索引；(4) 若連 5 場辯論未改變任何結論 → 縮小觸發範圍
---

# Debate Review Log

| # | date | debates covered | patterns found | promoted | cards merged/dropped | notes |
|---|---|---|---|---|---|---|
```

```bash
mkdir -p "$L/memory/cards" "$L/debates" && touch "$L/memory/cards/.keep"
```
(Write the four Markdown files above with the Write tool.)

- [ ] **Step 4: Check — expect PASS**

```bash
grep -c "^- \*\*X[0-9][0-9]" "$L/verification/probe-bank.md"     # 12
ls "$L/memory" "$L/memory/cards" "$L/debates"
echo "- Task 4: X01–X12 appended; memory/ + debates/ skeleton" >> "$L/_backup-2026-09-27/CHANGELOG.md"
```

---

### Task 5: Sourced grader notes → USER APPROVAL GATE

**Files:**
- Create: `$L/verification/probe-grader-notes.md`

**Interfaces:**
- Produces: per-probe required items `X##.k` with source; front matter key `approved:` (empty until the user fills it). Tasks 6, 8, 9 refuse to run until it is set.

- [ ] **Step 1: Failing check**

```bash
grep -E "^approved: [0-9]{4}-[0-9]{2}-[0-9]{2}" "$L/verification/probe-grader-notes.md" || echo "NOT APPROVED"
```

- [ ] **Step 2: Dispatch 2 Field-insider subagents in parallel** (`general-purpose`; batch 1 = X01–X06, batch 2 = X07–X12). Prompt:

```
You are a field-insider fact source. For each question below, list 2–4 things a GOOD answer must name — mechanisms, observables, or (for trap questions) the exact point where the analogy breaks. Each item must be backed by a published source you actually found with WebSearch/WebFetch: peer-reviewed paper, textbook, or reputable review (give URL or DOI and one short quoted or paraphrased supporting sentence). If you cannot find a source for an item, still list it but mark it `unsourced`. Do not invent sources. Politics questions: mechanisms and observables only, no positions.
Output format per question:
### X##
- X##.1 <required item> — source: <URL/DOI> — support: "<≤25 words>"
- X##.2 ...
Questions:
<paste the 6 probe lines for this batch verbatim>
```

- [ ] **Step 3: Spot-check sources** — main thread opens (WebFetch) at least 1 source per probe; any that doesn't support its item → mark `unsourced`.

- [ ] **Step 4: Write the file**

```markdown
---
purpose: X-series 評分答案要點（grader notes）— 盲測 agent 永不接觸本檔
approved:
approval-rule: 使用者閱讀並修改本檔後，於上方填入 approved: YYYY-MM-DD。未填前任何 X-probe 不得使用。
scoring: 每個有來源的要點 hit=1 / partial=0.5 / miss=0；unsourced 不計分；probe 分數=平均；總分=probe 平均
---

# X-Probe Grader Notes

<12 sections from Step 2, after Step 3 corrections>
```

- [ ] **Step 5: STOP — ask the user**

Tell the user: file path, count of sourced vs unsourced items per probe, and: "Please read and edit `probe-grader-notes.md`, then write `approved: YYYY-MM-DD` in its front matter. Tasks 6, 8, 9 wait for this." Do not proceed to Task 6 until the Step 1 check prints an `approved:` line.

```bash
echo "- Task 5: grader notes written; awaiting user approval" >> "$L/_backup-2026-09-27/CHANGELOG.md"
```

---

### Task 6: Baseline on 6 probes + first ledger row

**Precondition:** Task 5 Step 1 check prints `approved: YYYY-MM-DD`.

**Files:**
- Create: `$L/verification/X-baseline-2026-09.md`
- Modify: `$L/memory/efficiency-ledger.md`, `$L/verification/probe-bank.md` (mark [used])

**Interfaces:**
- Consumes: slimmed agent (Task 3), grader notes (Task 5).
- Produces: mentor-alone answers for X01, X05, X10 reused by Task 8; baseline score row.

- [ ] **Step 1: Dispatch 6 `lin-hsiu-hau-mentor` agents in parallel** (X01, X03, X05, X07, X10, X11). Prompt:

```
Student question: <probe text verbatim>
Answer as you normally would for a first session on this question, then close it as a conclusion point (include the ## 結論草稿 block). Do not open anything under lin-study/verification/ or lin-study/memory/.
```

- [ ] **Step 2: Save raw answers** to `$L/_backup-2026-09-27/baseline-answers/X##.md` (one file per probe, full mentor output incl. `## 結論草稿`), and record each agent ID in the file's first line (`agent-id: …`) — Task 8 reuses them.

- [ ] **Step 3: Grade** each answer against its sourced items (hit/partial/miss), quoting the answer sentence that earns each hit.

- [ ] **Step 4: Write `X-baseline-2026-09.md`**

```markdown
---
date: <today>
agent-version: slimmed (Task 3), body bytes <n>
grader-notes-approved: <date>
---

# X-Series Baseline

| probe | kind | items scored | hits | partial | miss | score |
|---|---|---|---|---|---|---|
<one row per probe>
| **mean** | | | | | | **<x.xx>** |

## Diagnosis
<one paragraph: which kinds (transfer / bridge / trap) fail, and the recurring missing item types>

## Per-probe evidence
<per probe: required item → verdict → quoted sentence>

## Debate comparison (filled by Task 8)
```

- [ ] **Step 5: Ledger row + burn probes**

Append to `efficiency-ledger.md`: `| <today> | baseline after slimming | <agent B> | <Hub B> | <sum> | X-baseline(6) | <mean> | reference |`
In `probe-bank.md`, append ` [used <today> → baseline]` to X01, X03, X05, X07, X10, X11.

```bash
echo "- Task 6: baseline mean=<x.xx>; ledger row 1" >> "$L/_backup-2026-09-27/CHANGELOG.md"
```

---

### Task 7: `lin-debate` skill + 4 role prompts

**Files:**
- Create: `~/.claude/skills/lin-debate/SKILL.md`, `references/roles/skeptic.md`, `bridge-auditor.md`, `practitioner.md`, `field-insider.md`

**Interfaces:**
- Consumes: `## 結論草稿` labels (Task 3); index/card/queue formats (Task 4).
- Produces: debate records `debates/YYYY-MM-DD-<slug>.md`, cards `memory/cards/C###.md`, index lines.

- [ ] **Step 1: Failing check**

```bash
S=~/.claude/skills/lin-debate
for f in SKILL.md references/roles/skeptic.md references/roles/bridge-auditor.md references/roles/practitioner.md references/roles/field-insider.md; do test -s "$S/$f" && echo "ok $f" || echo "MISSING $f"; done
```

- [ ] **Step 2: Write `SKILL.md`** — exactly:

````markdown
---
name: lin-debate
description: This skill should be used when a lin-hsiu-hau-mentor output ends with a "## 結論草稿" block, or the user says 「開辯論」 or 「重新辯論」. It checks the Lin brain's conclusion index for a reusable card, and otherwise runs a 4-critic debate (Skeptic, Bridge auditor, Practitioner, Field insider) with the main thread as judge, then stores the outcome as an archive record, a conclusion card, an index line, and at most one insight-queue line. Conclusion points only — never for ordinary teaching turns.
---

# lin-debate — conclusion debate for the Lin brain

Paths: `L = C:\Users\Ande\Desktop\NTHU\aa\M_Lectrues\lin-study`. Role prompts: `references/roles/`.
You (main thread) are the **judge**: you never argue a side.

## Step 0 — Index check (always first)
1. Extract 3–6 keywords from the question. `grep -i` each against `L/memory/index.md`.
2. Route:
   - **Exact:** same question, `conf: high`, recheck not passed → the proposer (or you) must state in one line why the new question is the same. If that line holds: answer from the card, update `used:`, tell the user "reused C### (date)". **Stop — no debate.** If it can't be stated: treat as Related.
   - **Related** (or exact but medium/low): read matched cards; debate only the **delta** (what the new draft adds or changes). Pass cards to the proposer as the starting point.
   - **None:** full debate.
   - 「重新辯論」 → full debate regardless.

## Step 1 — Draft
Use the `## 結論草稿` block from the mentor's output. If absent (manual 「開辯論」), dispatch `lin-hsiu-hau-mentor` asking for its conclusion with the block. Keep its agent ID for Step 3.

## Step 2 — Critique (4 in parallel, one message)
Dispatch four `general-purpose` agents with the prompts in `references/roles/{skeptic,bridge-auditor,practitioner,field-insider}.md`, filling `{QUESTION}`, `{DRAFT}` (full block + supporting text), `{SCOPE}` = "full" or "delta only: <delta>". Critics never see each other.
**Filter:** discard any objection lacking a concrete failure case. Keep ≤3 per role.

## Step 3 — Revision
Continue the same proposer (SendMessage to its agent ID; load SendMessage via ToolSearch if deferred) with the surviving objections, numbered. If that agent is no longer reachable, dispatch a fresh `lin-hsiu-hau-mentor` with the question + its draft pasted inline + the objections. Instruction: "For each objection: CONCEDE (revise the conclusion) or REFUTE (evidence or derivation). Then output a revised ## 結論草稿 block."

## Step 4 — Optional round 2 (max)
Only if a **fatal** objection was refuted: send that refutation to the critic role that raised it (fresh dispatch, same role prompt + refutation). If it still stands with a concrete case → mark open. Then stop.

## Step 5 — Judge & record
Confidence: **high** = no open major/fatal · **medium** = open majors only · **low** = any open fatal.
Write `L/debates/YYYY-MM-DD-<slug>.md`:
```
---
question: <verbatim>
route: full | delta (cards: C###) 
confidence: high|medium|low
card: C###
---
## Final conclusion
## Objection ledger
| role | objection | severity | outcome (conceded/refuted/open) |
## Draft → final diff
<what changed · which objection caused it>
## Open objections
## Verbatim critic outputs
```

## Step 6 — Store (Part 5)
1. **Card** `L/memory/cards/C###.md` (next free number; body ≤15 lines):
```
---
id: C###
question: <verbatim>
keywords: [k1, k2, k3]
confidence: high|medium|low
created: YYYY-MM-DD
last_used: YYYY-MM-DD
recheck: YYYY-MM-DD | none   # set a date (≤6 months) when the claim depends on facts that can change
archive: [[debates/YYYY-MM-DD-<slug>]]
---
**Claim:** 
**Scope:** 
**Break points:** 
**Decisive objections (imprint):** 
**Open objections:** 
**Moves used:** 
```
For a Related route, update the existing card instead of creating one if the question is the same.
2. **Index line** in `L/memory/index.md` (format in its front matter). If >60 entries, run the review (Step 7) first.
3. **Insight queue:** ask "Did any objection reveal a *thinking pattern* not covered by M1–M11 / G-moves / D-lessons?" If yes, append ONE line to `L/memory/insights-queue.md` (G = thinking move, D = teaching-process lesson). Else nothing.
4. If this is the 5th record since the last review → Step 7.

## Step 7 — Review every 5 debates
Per `L/debates/00-review-log.md` rules: promote patterns (G2–G5 + G-K + budget via `L/memory/efficiency-ledger.md`; kernel M-moves additionally need G1), merge same-question cards, drop cards unused 90 days and not high, and if 5 debates changed no conclusion, report that the trigger scope should be cut. **Fidelity guard:** if G-moves would outnumber kernel M-moves after a promotion, stop and run a fidelity audit (zero-context subagent traces each G-move to the kernel, as in the 2026-07-04 audit) before admitting it. Log one row.

## Standing rule
If the user disputes a card's conclusion, set that card to `confidence: medium` immediately (index line too), so it can never be reused without a debate.

## Report to the user
Final conclusion · confidence · open objections (one line each) · record link · card ID · "route: full/delta/reused".
````

- [ ] **Step 3: Write the 4 role prompts** — exactly:

`references/roles/skeptic.md`:
```markdown
You are the SKEPTIC in a debate about a conclusion. Your move (Lin's M5, second-pass skepticism): find the neglected factor, fluctuation, or hidden assumption that destroys the weakest step.
Do not use tools. Scope: {SCOPE}
Question: {QUESTION}
Draft conclusion:
{DRAFT}
Return at most 3 objections, strongest first, each exactly:
OBJECTION n
- target step: <quote the step>
- failure case: <a concrete situation where the step gives a wrong result>
- severity: fatal (conclusion flips) | major (conclusion needs a scope limit) | minor
- would resolve it: <evidence or derivation that would answer it>
No concrete failure case → do not list it. If nothing survives, answer: NONE.
```

`references/roles/bridge-auditor.md`:
```markdown
You are the BRIDGE AUDITOR in a debate about a conclusion. Your job (Lin's M7: carry tools, not conclusions): for every analogy or transfer between fields in the draft, check (1) the mapping table — what maps to what, (2) source items with NO counterpart, (3) the break point where the analogy stops working. An analogy whose mapping cannot be written out is rhetoric.
Do not use tools. Scope: {SCOPE}
Question: {QUESTION}
Draft conclusion:
{DRAFT}
Return at most 3 objections, each exactly:
OBJECTION n
- target step: <the bridge, quoted>
- failure case: <a concrete case where the unmapped item or break point makes the transferred conclusion wrong>
- severity: fatal | major | minor
- would resolve it: <the mapping row or scope limit that would fix it>
If the draft uses no cross-field bridge, answer: NO BRIDGES.
```

`references/roles/practitioner.md`:
```markdown
You are the PRACTITIONER in a debate about a conclusion. Your move (Lin's M6, land in a measurable number): a conclusion must change an action or a test. Ask: what would someone measure or do next because of this? Also flag WASTED DEPTH — any paragraph that changes neither the conclusion nor the action.
Do not use tools. Scope: {SCOPE}
Question: {QUESTION}
Draft conclusion:
{DRAFT}
Return at most 3 objections, each exactly:
OBJECTION n
- type: no-action | untestable | wasted-depth
- target step: <quoted>
- failure case: <concrete: the decision this fails to inform, or the paragraph that changes nothing>
- severity: fatal | major | minor
- would resolve it: <the observable, threshold, or action that would fix it — or "cut">
Nothing concrete → NONE.
```

`references/roles/field-insider.md`:
```markdown
You are the FIELD INSIDER for the target field of this question (culture, politics, biology, economics, a science field — whichever the question is really about). You may use WebSearch and WebFetch. Your job: (1) check factual claims against published sources; (2) name what practitioners of this field know that the draft misses; (3) flag leftover physics jargon that a reader in this field would not understand.
Scope: {SCOPE}
Question: {QUESTION}
Draft conclusion:
{DRAFT}
Return at most 3 objections, each exactly:
OBJECTION n
- type: factual | missing-field-knowledge | jargon
- target step: <quoted>
- failure case: <concrete>
- source: <URL/DOI you actually opened, or "none" (then severity may not exceed minor)>
- severity: fatal | major | minor
- would resolve it: <...>
Politics: mechanisms and evidence only, no positions. Never invent sources. Nothing concrete → NONE.
```

- [ ] **Step 4: Check — expect PASS**

```bash
for f in SKILL.md references/roles/skeptic.md references/roles/bridge-auditor.md references/roles/practitioner.md references/roles/field-insider.md; do test -s "$S/$f" && echo "ok $f"; done
grep -c "{DRAFT}" $S/references/roles/*.md          # each :1
grep -q "^name: lin-debate" "$S/SKILL.md" && echo "front matter ok"
echo "- Task 7: lin-debate skill + 4 roles" >> "$L/_backup-2026-09-27/CHANGELOG.md"
```
Then confirm the skill is discoverable: it appears in the session's skill list after reload (if not listed until restart, note it in the CHANGELOG and invoke by reading SKILL.md directly for Task 8).

---

### Task 8: First debates = debate-vs-alone comparison (X01, X05, X10)

**Precondition:** grader notes approved; Tasks 6–7 done.

**Files:**
- Create: 3 records in `$L/debates/`, cards `C001–C003`, index lines
- Modify: `$L/verification/X-baseline-2026-09.md` (§Debate comparison), `$L/memory/efficiency-ledger.md`

**Interfaces:**
- Consumes: Task 6 mentor-alone answers + scores for X01, X05, X10.

- [ ] **Step 1: Run `lin-debate` on each** of the three Task 6 answers (`$L/_backup-2026-09-27/baseline-answers/X01.md`, `X05.md`, `X10.md` — their `## 結論草稿` blocks; proposer = the recorded agent ID, fresh-dispatch fallback per SKILL Step 3). Index is empty → route = full.
- [ ] **Step 2: Grade the final (post-debate) conclusions** with the same grader notes.
- [ ] **Step 3: Fill §Debate comparison**

```markdown
| probe | alone score | debate score | real errors caught (objection → why it was a real error) | subagent runs |
|---|---|---|---|---|
<3 rows>
**Verdict:** debate helps | no measurable help — <one line>. If no help: recommend narrowing triggers (per spec 4.7).
```
- [ ] **Step 4: Check**

```bash
ls "$L/debates"/2026-*.md | wc -l          # 3
ls "$L/memory/cards"/C00*.md | wc -l       # 3
grep -c "^- C00" "$L/memory/index.md"      # 3
```
Append ledger row: `| <today> | debate on X01/X05/X10 (no core change) | … | … | … | X01,X05,X10 | <alone mean → debate mean> | measurement |` and a CHANGELOG line.

---

### Task 9: Bridge-audit candidate through the gates

**Precondition:** grader notes approved.

**Files:**
- Create: `$L/verification/W-X-scorecard.md`
- Modify (only if accepted): `$L/moves/M07 誠實計價的跨界.md`, agent M7 line + M11 line, Hub M7 row, ledger, probe-bank

**Interfaces:**
- Candidate text (narrowed per spec 2.1): **「斷點稽核：雙語字典之外，再列出來源側『沒有對應物』的項目，並指名類比在哪一步斷掉；結論只帶到斷點之前。」**

- [ ] **Step 1: G1 provenance** — record both quotes (from `Week-03` note): 2211.15278 "the optimized state for visual recognition, although close to, does not coincide with the critical state." (names where the criticality=optimality bridge breaks) and 1005.4335 damped-oscillator mapping quote. Judge: does Lin's text *enact* "name the break point"? PASS → kernel refinement of M7. FAIL → re-route as **G01 candidate** (skip G1, apply G-K check: derivable, falsifiable, depth-first-consistent, stated as a tool).
- [ ] **Step 2: G2 novelty** — situation where it gives different guidance than M7 sub-tactic 2 alone: X12 — the dictionary (refresh ↔ review, charge ↔ memory trace) can be written, yet the transfer fails because human retrieval *strengthens* the trace; only an explicit unmapped-item/break-point check catches it.
- [ ] **Step 3: G3 blind two-arm on X06 and X12** (4 `general-purpose` agents, parallel, no tools). Arm A prompt gets: the 11 one-line moves from the Hub table + M7 sub-tactic 2 verbatim from `moves/M07` line 12. Arm B: same + candidate text. Template:

```
You are a thinking mentor who reasons ONLY with these moves. No tools; do not read files.
MOVES:
<moves text>
Student question: <X06 or X12 verbatim>
Answer in ≤350 words, naming which moves you use.
```
Judge: Arm B must contain a NAMED unmapped item or break point traceable to the candidate that Arm A lacks; otherwise similar. Also grade both arms with grader notes.
- [ ] **Step 4: G4** — falsifier: if Lin's cross-field papers show him transferring conclusions past an acknowledged mismatch without flagging it, the move is not his (kernel route) / not Lin-compatible (G route).
- [ ] **Step 5: G5** — re-run P01 and P06 with Arm-B moves (2 agents); named guidance of M9 / M10 still appears.
- [ ] **Step 6: Budget + decision**

Accept only if G1(or G-K)–G5 pass AND Arm B score > Arm A score AND core bytes do not grow. Byte payment: replace the agent M7 line's last sentence as follows and cut from M11 the trailing sentence beginning "Also: when many couplings look equally marginal" (duplicate of `moves/M01` sub-tactic, W02) :

```bash
A=~/.claude/agents/lin-hsiu-hau-mentor.md; H="$L/00 - Lin Thinking Hub.md"
core(){ echo $(( $(awk 'f>=2{print} /^---$/{f++}' "$A" | wc -c) + $(wc -c < "$H") )); }
core_before=$(core)
before=$(awk 'f>=2{print} /^---$/{f++}' "$A" | wc -c)
sed -i 's| Encourage crossing over — with a years-not-weeks time constant, carrying mastered tools.| Cross with a years-not-weeks time constant, carrying tools not conclusions: write the mapping, list what has no counterpart, name where the analogy breaks, and carry conclusions only up to that point.|' "$A"
sed -i 's| Also: when many couplings look equally marginal, rank them by the exponent of their approach to the singularity, not by magnitude at one scale.||' "$A"
after=$(awk 'f>=2{print} /^---$/{f++}' "$A" | wc -c); echo "$before -> $after"   # after must be ≤ before
```
If `after > before`: revert from `$B/lin-hsiu-hau-mentor.md`-derived Task 3 version (re-run Task 3 Step 4) and shorten the M7 replacement. Then add sub-tactic 6 to `moves/M07` (「斷點稽核」, with the G1 quotes and date) and update the Hub M7 row's one-liner to 「帶工具不帶結論；寫字典、列無對應物、指斷點；以年計價」 (Hub must stay ≤50 lines / ≤4,000 B). Final budget check: `echo "$core_before -> $(core)"` — **core total must not grow**; if it does, shorten the Hub row until it doesn't.
If rejected: no edits; scorecard verdict NO-CHANGE.
- [ ] **Step 7: Scorecard + ledger + burn probes** — write `W-X-scorecard.md` in the protocol §5 format with verbatim arm key sentences; ledger row with before/after bytes and Arm A/B scores; mark X06, X12 `[used <date> → bridge-audit G3 <PASS|FAIL>]`; CHANGELOG line.

---

### Task 10: Curriculum, Hub links, memory

**Files:**
- Modify: `$L/curriculum.md`, `$L/00 - Lin Thinking Hub.md`, memory `lin-hsiu-hau-mentor-agent.md`, `MEMORY.md`

- [ ] **Step 1: Failing check**

```bash
H="$L/00 - Lin Thinking Hub.md"
grep -c "memory/index\|lin-debate\|protocols/" "$H"   # 0
grep -n "W09\|W10" "$L/curriculum.md" | head -3
```

- [ ] **Step 2: Curriculum** — in the 進度 table, move the W09 and W10 rows to directly below the W03b row, keeping their IDs (W09, W10). Append to each moved row's 主題軸 cell: `（1005.4335 / 2211.15278 已於 W03 讀畢；本週只讀新篇）`. Then append to 研讀紀錄:
`- 2026-09-27：依跨域大腦目標，W09–W10 提前為下一週；待讀新篇 1011.5098 · 1411.6473 · 2310.11839（＋Scholar 新作查核）。`

- [ ] **Step 3: Hub** — replace the 網絡導航 list's last line and add, keeping total ≤50 lines:

```markdown
- 程序（觸發才讀）：`protocols/`（news-update · weekly-study · corpus-refresh · teaching-material · dashboard）
- 跨域題庫 X01–X12：[[probe-bank]] · 評分 [[probe-grader-notes]] · 基線 [[X-baseline-2026-09]]
- 結論記憶：`memory/index.md`（先 grep）→ `memory/cards/` → `debates/`（存檔）；辯論＝skill `lin-debate`；成長招式 G 系列見 spec 5.4
```
Add rule 4 under 使用規則: `4. 結論點輸出 ## 結論草稿，由主線跑 lin-debate；核心大小記在 memory/efficiency-ledger.md。`
If >50 lines, merge the two 週讀筆記/課堂語錄 lines into one.

- [ ] **Step 4: Check**

```bash
wc -lc "$H"                                    # ≤50 lines, ≤4000 bytes
grep -c "memory/index\|lin-debate\|protocols/" "$H"   # ≥3
```

- [ ] **Step 5: Memory** — append to `C:\Users\Ande\.claude\projects\C--Users-Ande-Desktop-NTHU-aa\memory\lin-hsiu-hau-mentor-agent.md`:

```markdown

**Cross-domain brain upgrade (2026-09-27; spec `aa/docs/superpowers/specs/2026-09-27-lin-mentor-cross-domain-design.md`):** two-layer core — **kernel** = Lin's way of entering fields (M1–M11, D0; Lin-paper provenance) + **grown G-moves** from any source (G2–G5 + G-K kernel check + byte budget, shared ≤15 moves). Agent slimmed (procedures in `lin-study/protocols/`, routing table in agent). Cross-field probes X01–X12 with user-approved sourced grader notes; baseline in `verification/X-baseline-2026-09.md`. **Debate:** at conclusion points only, the agent emits `## 結論草稿`; the MAIN thread must then run skill `lin-debate` (4 critics: Skeptic/Bridge auditor/Practitioner/Field insider; ≤2 rounds; judge = main thread) — subagents can't nest, so never ask the mentor to run it. **Storage:** `memory/index.md` (grep first) → cards → `debates/` archive; exact high-conf card hit = reuse without debate; 「重新辯論」 forces one. Core size tracked in bytes in `memory/efficiency-ledger.md`; a core change is accepted only if score rises at ≤ size or holds at smaller size.
```
Update the `MEMORY.md` line for this memory to: `- [Lin Hsiu-Hau mentor agent](lin-hsiu-hau-mentor-agent.md) — 林秀豪 persona → cross-domain brain; kernel+G-moves, lin-debate at conclusion points (main thread runs it), memory/index reuse, byte-budget core`

- [ ] **Step 6: Final verification sweep**

```bash
A=~/.claude/agents/lin-hsiu-hau-mentor.md
echo "agent body B: $(awk 'f>=2{print} /^---$/{f++}' "$A" | wc -c) (≤11500)"
wc -lc "$L/00 - Lin Thinking Hub.md"
ls "$L/protocols" "$L/memory" "$L/debates" ~/.claude/skills/lin-debate/references/roles
grep -c "M1–M10" "$L/00 - Lin Thinking Hub.md" "$A" "$L/deployment-lessons.md"
cat "$L/_backup-2026-09-27/CHANGELOG.md"
```
Report to the user: changed files, untouched files (Scholarly Profile, lecture notes, dashboard HTML, lin-news.js, Week-01–03 notes, existing scorecards, industry-paper-study skill), baseline mean, debate verdict, bridge-audit verdict, open items.
