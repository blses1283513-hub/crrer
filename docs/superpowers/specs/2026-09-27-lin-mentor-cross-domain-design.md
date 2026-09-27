---
title: Lin mentor — cross-domain measurement, slimming, and debate group
date: 2026-09-27
status: draft — awaiting user review
scope: A (measure first) + C (slim agent) + debate group + outcome memory (Part 5); B (industry move series) deferred
owner-files:
  - ~/.claude/agents/lin-hsiu-hau-mentor.md
  - aa/M_Lectrues/lin-study/**
  - ~/.claude/skills/lin-debate/** (new)
---

# Lin mentor — cross-domain measurement, slimming, and debate group

## 1. Goal

Make the `lin-hsiu-hau-mentor` agent measurably good at **combining knowledge across fields** (industry, culture, entertainment, politics, biology), while keeping its thinking core grounded in Prof. Lin's publications. Every conclusion must survive a structured multi-role debate before it is accepted.

Success = four things are true after implementation:
1. We can **measure** cross-field performance (a held-out cross-field probe set exists and a baseline is recorded).
2. The agent file holds only the thinking core; procedures load on demand.
3. Conclusions pass through a ≥4-critic debate whose record shows what changed and what remains open.
4. Past conclusions are **reused** on similar topics instead of re-derived, and the core gets **sharper, not larger**: every core change is accepted only if it improves probe score per unit of core size.

## 2. Non-goals

- No industry move series (B) in this pass. Revisit after the baseline shows where the mentor fails.
- No new M-move by default. The analogy check enters as a *candidate refinement* of M7 and may be rejected.
- No debate on ordinary teaching turns (Socratic steps, derivations in progress).
- No loosening of D0 (depth-first). Breadth = more fields where the same moves are tested, not more content.

## 3. Evidence behind this design (state on 2026-09-27)

| Finding | Source |
|---|---|
| Probe bank is physics/ML only; 4 unused probes left (P03, P04, P05, P07) | `lin-study/verification/probe-bank.md` |
| M1–M11 held up intact in ecology and neuroscience | `lin-study/Week-03 — Cross-Line Generalization Test.md` |
| No step requires writing out an analogy's mapping and break point | agent file M7 one-liner (branch note M07 has the mapping table but not unmapped items or break point) |
| Use in other domains (K-drama material, Industry Radar) never feeds back into the moves | `deployment-lessons.md` (only one deployment), `industry-paper-study` memory |
| Paper program stalled after W03 (2026-07-04) | `lin-study/curriculum.md` |
| Stale "M1–M10" references although M11 exists | `00 - Lin Thinking Hub.md` heading + core-rule line; agent boot line |
| Agent file ~140 lines, mostly procedures | `lin-hsiu-hau-mentor.md` lines 103–137 |

---

## Part 1 — Cross-field probe set (X-series)

### 1.1 Probes

Append a new section `## 跨域 probes (X-series, 2026-09-27)` to `verification/probe-bank.md`. Politics probes ask about mechanisms only, never which side is right.

**Single-field transfer (4)**
- **X01 文化** — 為什麼有些節慶習俗能跨世代存活，有些在一代內就消失？
- **X02 娛樂** — 一個劇種（例如韓國復仇劇）爆紅後，為什麼幾年內就退燒？怎麼分辨是題材疲乏還是平台演算法改變？
- **X03 政治** — 多黨聯合政府為什麼有的撐滿任期、有的幾個月就垮？要看哪些可觀測量才能判斷一個聯盟穩不穩？
- **X04 生物** — 醫院停用某種抗生素後，抗藥菌為什麼不一定會消失？

**Two-field bridge (5)**
- **X05 半導體 × 生物** — 晶圓廠的良率學習（yield learning）方法能不能搬去加速疫苗量產放大？哪些能搬、哪些不能？
- **X06 半導體 × 政治** — 半導體供應鏈的「單點瓶頸」分析，能不能拿來評估一國的出口管制會不會奏效？
- **X07 娛樂 × 經濟** — 串流平台的內容投資像不像創投的冪律報酬？這個類比能推出什麼可檢驗的預測？
- **X08 文化 × 演化** — 把語言/迷因傳播當成演化（複製–變異–選擇）來分析，什麼時候有解釋力、什麼時候只是換詞？
- **X09 政治 × 網路** — 城市之間互相模仿政策，能不能用網路上的傳染模型描述？模型要測到什麼才算數？

**False-bridge trap (3)** — the best answer names where the analogy breaks
- **X10** — 股市崩盤像相變/臨界現象，所以可以用臨界指數預測崩盤時間吧？
- **X11** — 輿論兩極化就像鐵磁體的自發對稱破缺，所以只要加一個「外場」（政府宣導）就能把它對齊，對吧？
- **X12** — DRAM 要定期 refresh 防止電荷流失，就像人要複習防止遺忘，所以最佳複習間隔可以用 DRAM retention 分佈來算？

### 1.2 Grader notes

New file `verification/probe-grader-notes.md`: for each X-probe, 2–4 items a good answer must name (e.g. X12: retrieval strengthens human memory — the spacing effect — while a capacitor does not strengthen when refreshed, so the mapping breaks at the "reinforcement" step). Blind test agents never receive this file.

**Anti-circularity (decided 2026-09-27):** the grader notes are written by the same model whose answers they grade. Two guards, both required:
1. **Sourced:** a Field-insider subagent (WebSearch/WebFetch) backs every required item with a published source (paper, textbook, or reputable review) — URL or DOI in the note. Items with no source are marked `unsourced` and do not count in scoring.
2. **User approval gate:** the user reads and edits `probe-grader-notes.md` and marks it `approved: YYYY-MM-DD` in its front matter. No baseline or G3 run may use an X-probe before that mark exists.

### 1.3 Split and baseline

| Use | Probes |
|---|---|
| **Baseline now** (burned after use) | X01, X03, X05, X07, X10, X11 — two of each kind |
| **Held out** for future G3 tests | X02, X04, X06, X08, X09, X12 — includes 4 bridge/trap probes for Part 2 |

Baseline procedure: dispatch the current mentor (M1–M11, no debate) on each of the 6 baseline probes as a zero-tool subagent. Grade against grader notes: each required item = hit / partial / miss. Write `verification/X-baseline-2026-09.md` with per-probe scores and a one-paragraph diagnosis of where the mentor fails outside physics/ML.

---

## Part 2 — Analogy check + reading restart

### 2.1 Candidate refinement: bridge audit

> Before using any cross-field analogy, write a mapping table: source item → target item; list source items with **no** counterpart; name the **break point** where the analogy stops working. Carry the tool across, not the conclusion.

- **Provenance (G1):** 1005.4335 maps extinction onto a damped oscillator item by item (quote already recorded in the Week-03 note); M7's "carry tools, not conclusions".
- **Form:** refinement of M7, not a new M12. **Overlap found 2026-09-27:** `moves/M07` sub-tactic 2 「公開的雙語字典」 already requires a mapping table ("字典寫不出來的類比是修辭"). The candidate is therefore narrowed to the new part only: **list source items with no counterpart + name the break point**, and promote the dictionary requirement into the agent's M7 one-liner (today it lives only in the branch note). For G3, Arm A receives M7 *including* sub-tactic 2, so the test measures only the narrowed addition.
- **Gates:** full G1–G5 per `verification/protocol.md`. G3 runs blind two-arm on **X06** and **X12** (one bridge, one trap). G5 re-runs P01 and P06.
- **If G3 shows no named delta:** reject, record in a new `verification/W-X-scorecard.md`, verdict NO-CHANGE. No edits to M07.

### 2.2 Reading restart

Reorder `curriculum.md` so W09–W10 come next. Already read: 1005.4335, 2211.15278. Remaining new papers: **1011.5098, 1411.6473, 2310.11839** (+ Scholar check for newer work). This pass only reorders; the reading itself runs on the next 「本週研讀」.

### 2.3 Stale references

Change "M1–M10" → "M1–M11" in: Hub heading `## 招式庫 M1–M10`, Hub core-fidelity line "M1–M10 才是思考核心", agent boot line "(M1–M10)".

---

## Part 3 — Slim the agent

### 3.1 What moves where

| Stays in `lin-hsiu-hau-mentor.md` | Moves to `lin-study/protocols/` |
|---|---|
| Identity, boot sequence | `news-update.md` — Industry Watch Protocol |
| Worldview 1–8 | `weekly-study.md` — Weekly Study Program + pointer to `verification/protocol.md` |
| M1–M11 full text (thinking core — not shortened) | `corpus-refresh.md` — Corpus-Refresh Protocol |
| D0 as one line + pointer to `deployment-lessons.md` | `teaching-material.md` — Teaching-Material Production Protocol |
| Session protocol, language, output format | `dashboard.md` — dashboard note |
| Trigger → file routing table | (full D-lessons paragraph already lives in `deployment-lessons.md`) |
| **Safety rules, inline:** no voice synthesis/playback; news = verified public professional facts only; never invent citations; public-figure professional info only | — |
| Conclusion-block rule (see 4.5) | — |

Target: agent body 17,560 → ≤11,500 bytes (see 5.4 budget). Backup first: `lin-study/_backup-2026-09-27/lin-hsiu-hau-mentor.md`.

### 3.2 Regression check

- Blind-run **P01** and **P06** with the old agent text and the new agent text (zero-tool subagents). Pass = the named guidance recorded in the probe bank (P01 → M9 representation change; P06 → M10 integrate-out-keep-memory) appears in both.
- Trigger check: for each trigger (「更新林教授動態」「本週研讀」「優化指導員」「做成教材」), confirm the routing table points to an existing file.

---

## Part 4 — Debate group (`lin-debate` skill)

### 4.1 Why a skill, not the agent

A subagent cannot start its own subagents. The mentor, when dispatched, therefore cannot run a debate. The main thread runs the debate through the `lin-debate` skill and acts as judge.

### 4.2 Roles

| Role | Job | Rooted in | Tools |
|---|---|---|---|
| **Proposer** | Builds the conclusion with M1–M11, every step visible | the mentor agent | per agent |
| **Skeptic** | Attacks the weakest step: which ignored factor kills this? | M5 | none |
| **Bridge auditor** | For each cross-field analogy: mapping, unmapped items, break point | Part 2 bridge audit + M7 | none |
| **Practitioner** | What would you measure or do next? Rejects conclusions that change no action or test | M6 | none |
| **Field insider** | Speaks for the target field; fact-checks claims; flags leftover physics jargon | D1 + fact-checking | WebSearch, WebFetch |
| **Judge** (main thread) | Scores objections, writes the record; never argues | G3 judge rule | — |

All four critics run on every debate, including science-only topics (the insider then represents that science field).

### 4.3 Rounds (hard cap: 2)

1. **Draft** — the proposer's conclusion block (4.5).
2. **Critique** — the four critics run in parallel, blind to each other, draft pasted inline. Each returns ≤3 objections in this form: target step · concrete failure case · severity (fatal/major/minor) · what would resolve it. The judge discards objections without a concrete failure case.
3. **Revision** — continue the same proposer agent (SendMessage) with the surviving objections. For each: **concede** (change the conclusion) or **refute** (with evidence or derivation).
4. **Round 2 (last round)** — runs if a *fatal* objection was refuted (that critic re-checks the refutation) **or** the revision introduced new claims, numbers, or thresholds (Skeptic, plus Field insider for factual claims, re-check only those revised claims; decided 2026-09-27). Surviving objections are marked open. Then stop.

### 4.4 Record

Judge writes the full record to the archive `lin-study/debates/YYYY-MM-DD-<topic>.md`, then writes a conclusion card + index line + at most one insight-queue line (Part 5). The full record contains:
- Final conclusion
- Confidence: **high** (no open major/fatal) · **medium** (open majors only) · **low** (any open fatal); then take the minimum with the proposer's self-rating. Claims first introduced in the revision count as unreviewed unless round 2 re-checked them; if unreviewed, confidence is capped at medium (decided 2026-09-27).
- Objection ledger: role · objection · severity · conceded / refuted / open
- **Draft → final diff**: what changed and which objection caused it
- Open objections, carried forward

The final answer shown to the user includes the conclusion, confidence, and open objections, plus a link to the record.

### 4.5 When it runs

**Conclusion points only:**
1. Closing a classic question
2. Finishing teaching material (runs before the existing reader test)
3. Any claim that combines fields
4. Promoting a new or refined move (the G1–G5 gates still apply; the debate runs on the scorecard's conclusion)

Manual trigger: 「開辯論」. Not triggered by Socratic steps, derivations in progress, or ☆ homework exchanges.

Mechanism: the agent ends any conclusion-point output with a `## 結論草稿` block (claim · reasoning steps · relevant/marginal/irrelevant factor list (5.3) · moves used · cross-field bridges used · self-rated confidence). When the main thread sees this block, it invokes `lin-debate`. The skill's first step is the index check in 5.2, which may skip or narrow the debate.

### 4.6 Feedback loop

Every 5 debate records, run the review defined in 5.4: recurring objection patterns (same role, same kind of failure ≥3 times) and insight-queue items become candidate D-lessons or new held-out probes, subject to the budget rule. Log the review in `debates/00-review-log.md`.

### 4.7 Measuring whether debate helps

On 3 of the baseline probes (X01, X05, X10), compare mentor-alone (from 1.3) vs mentor + debate, graded against the same grader notes. Write the result into `verification/X-baseline-2026-09.md`. If the debate does not raise scores or catch at least one real error, record that honestly and revisit the trigger scope.

### 4.8 Skill files

```
~/.claude/skills/lin-debate/
├── SKILL.md                      # trigger, rounds, judge rules, record format
└── references/roles/
    ├── skeptic.md
    ├── bridge-auditor.md
    ├── practitioner.md
    └── field-insider.md
```

---

## Part 5 — Memory that gets sharper, not bigger

Grounding: Lin's RG practice — keep the relevant couplings, let irrelevant ones flow to zero (M1, M4); integrate out the detail but keep its imprint (M10).

### 5.1 Three storage levels

| Level | Content | Loaded when | Size limit |
|---|---|---|---|
| **Index** `lin-study/memory/index.md` | one line per card: `C###` · keywords · one-line claim · confidence · last used | searched (grep) at the start of every topic; never read in full | ≤60 lines |
| **Cards** `lin-study/memory/cards/C###.md` | claim · scope · break points · the 1–3 objections that changed the conclusion · open objections · moves used · recheck date (fact-dependent cards only) · link to archive record | only on an index hit | ≤15 lines each |
| **Archive** `lin-study/debates/*.md` | full debate records | never at start; only for audit or when a card is disputed | no limit |

### 5.2 Similar-topic routing (runs before any drilling)

Grep the index for the new topic's keywords, then:

| Match | Action |
|---|---|
| **Same question**, confidence high, recheck date not passed | Answer from the card. **No debate.** Say which card was reused and its date. Update "last used". |
| **Related question** (or same question at medium/low confidence, or at high confidence past its recheck date — decided 2026-09-27) | Load the matched cards as the starting point. Proposer states only what is new; critics debate only that delta. |
| **No match** | Full process (Part 4). |

「重新辯論」 forces a full debate regardless of match.

### 5.3 Relevance filter (stops real-world overthinking)

Before drilling, the proposer sorts every factor:
- **Relevant** — changes the conclusion or the action → drill.
- **Marginal** — changes confidence only → one sentence.
- **Irrelevant** — named in one line, then dropped.

The Practitioner gains an objection type **wasted depth**: any paragraph that changes no conclusion and no action. This is consistent with D0: depth goes to relevant factors.

The sorted factor list is part of the `## 結論草稿` block (4.5).

### 5.4 Learning without growing

**Two outputs per debate, kept separate:**
1. **Content** → a card (5.1).
2. **Thinking pattern** → at most one line in `lin-study/memory/insights-queue.md` (never loaded at start).

**Two-layer core: Lin's way as the kernel, grown moves on test results** (decided 2026-09-27):

| Layer | Content | Admission |
|---|---|---|
| **Kernel** | Lin's way of entering a new field: depth-first (D0), derive-don't-cite, carry tools not conclusions (M7), protected vs fragile, compute where control exists. Plus M1–M11. Primary sources for further kernel refinement: his cross-field papers (W03, W09, W10) | Lin papers only (G1 as today); changes rarely |
| **Grown moves (G-series)** | Any thinking pattern — from debates, other thinkers, industry research, field experts, or the user's corrections | G2–G5 + budget rule + **G-K kernel check**: the pattern must be derivable (not a slogan), falsifiable, and consistent with depth-first; it must be stated as a tool, not a conclusion. Source recorded in the move note; not required to be Lin |

- M- and G-moves share the same core budget (≤15 moves total, agent body ≤11,500 bytes).
- G-moves live in `lin-study/moves/G01 *.md` etc., listed in the Hub table with their source.
- D-lessons remain for curriculum-design lessons; a recurring debate pattern that is a *thinking* move becomes a G-candidate, one that is a *teaching-process* lesson becomes a D-candidate.
- Identity guard: the kernel governs how every move is applied, so the brain stays Lin's way of thinking even when a move's content comes from elsewhere. If G-moves ever outnumber kernel moves, run a fidelity audit (as done 2026-07-04) before admitting more.

**Budget rule (fixed-size core):**
- Core = agent body (below front matter) + Hub, **measured in bytes** (`wc -c`, a proxy for tokens; lines mislead because agent lines are long paragraphs). Caps: agent body ≤11,500 bytes (was 17,560 on 2026-09-27), Hub ≤50 lines and ≤4,000 bytes (was 3,399), moves ≤15.
- Any addition to the core must be paid for by a cut or merge of equal or greater size.
- A core change is accepted only if, on held-out probes, score **rises at equal or smaller size**, or **stays equal at smaller size**. Otherwise rejected.
- `lin-study/memory/efficiency-ledger.md` logs: date · core size (lines) · probe score · change · accepted/rejected. First row = state after Part 3 + baseline.

**Review every 5 debates:**
- Insight-queue items and recurring objection patterns compete; promotion follows G1–G5 + budget rule.
- Merge cards that answer the same question (keep the sharper one; the other's archive link moves over).
- Drop from the index any card unused for 90 days whose confidence is not high (card file stays; archive untouched).
- Check: if 5 consecutive debates changed no conclusion, cut the debate's trigger scope (8. Risks).

---

## 5. Files changed

| File | Change |
|---|---|
| `~/.claude/agents/lin-hsiu-hau-mentor.md` | slimmed; routing table; conclusion-block rule; M1–M11 fix (backup first) |
| `lin-study/00 - Lin Thinking Hub.md` | M1–M11 fix; links to X-series, protocols/, debates/, memory/ — must stay ≤50 lines (currently 46), so compress existing lines to fit |
| `lin-study/curriculum.md` | reorder W09–W10 next |
| `lin-study/verification/probe-bank.md` | append X01–X12 |
| `lin-study/moves/M07 誠實計價的跨界.md` + agent M7 line | bridge-audit sub-tactic **only if** G1–G5 pass |
| `lin-study/moves/G01…` (future) | G-series grown moves; none created in this pass — only the admission path (5.4) is set up |
| **New:** `verification/probe-grader-notes.md`, `verification/X-baseline-2026-09.md`, `verification/W-X-scorecard.md` | — |
| **New:** `lin-study/protocols/*.md` (5 files) | moved procedures |
| **New:** `lin-study/debates/` + `00-review-log.md` | debate archive |
| **New:** `lin-study/memory/index.md`, `memory/cards/`, `memory/insights-queue.md`, `memory/efficiency-ledger.md` | Part 5 storage |
| **New:** `~/.claude/skills/lin-debate/` | skill (index check → debate → card/index/queue write) + 4 role prompts |
| Memory `lin-hsiu-hau-mentor-agent.md` | record the new structure and the debate rule |

Untouched: Scholarly Profile, lecture notes, dashboard HTML, `lin-news.js`, Week-01–03 notes, existing scorecards, `industry-paper-study` skill.

## 6. Implementation order

1. Stale-reference fixes + backup (smallest, no risk)
2. Part 3 slimming + regression check (P01, P06)
3. Part 1 probes + sourced grader notes → **pause for user approval of grader notes** → baseline (6 runs); first efficiency-ledger row
4. Part 5 storage skeleton (index, cards/, queue, ledger — empty but formatted)
5. Part 4 skill + role prompts; first debates = the 4.7 comparison, which also produce the first 3 cards
6. Part 2 bridge-audit gates (G3 on X06, X12); if accepted, must satisfy the budget rule
7. Curriculum reorder, Hub links, memory update

## 7. Cost

| Step | Subagent runs (approx.) |
|---|---|
| Regression check | 4 |
| Grader-note sourcing (Field insider, 2 batches of 6) | 2 |
| Baseline | 6 |
| Debate comparison (3 probes × ~6) | 18 |
| Bridge-audit G3 + G5 | 6 |
| **Total** | **~36** |

After setup: ~6 runs per full debate; fewer for a delta debate (critics see only the new part); 0 runs on an exact high-confidence card hit.

## 8. Risks

- **Process overgrowth (D0).** The debate adds machinery. Guards: conclusion points only, 2-round cap, 4.7 measurement, and the rule that a debate that never changes a conclusion over 5 records gets its scope cut.
- **Critic theater.** Critics may produce generic objections. Guard: the judge discards any objection without a concrete failure case.
- **Judge bias.** The main thread both orchestrates and judges. Guard: the objection ledger is recorded verbatim, so it can be audited later.
- **Politics probes drifting into opinion.** Guard: probes and grader notes ask about mechanisms and observables only.
- **Slimming regressions.** Guard: backup + P01/P06 blind regression before continuing.
- **Wrong card reused.** An exact hit skips the debate, so a flawed high-confidence card propagates. Guards: skip only at high confidence; recheck dates on fact-dependent cards; 「重新辯論」 override; a card disputed by the user drops to medium confidence.
- **False "same question" match.** Keyword grep may match a question that differs in a decisive detail. Guard: on a hit, the proposer states in one line why the new question is the same; if it can't, route as "related" (delta debate).
- **Identity drift via G-moves.** Opening the core to non-Lin sources risks the brain turning into generic model reasoning under Lin's name. Guards: G-K kernel check; shared 15-move budget; fidelity audit when G-moves outnumber kernel moves.
- **Circular grading.** Guards: sourced grader notes + user approval gate (1.2).
- **Storage growth by the back door.** Cards are content, so they grow with topics. Guards: 60-line index cap, merge + 90-day drop at each review; the budget rule applies to the core only, and cards are never loaded unless matched.
