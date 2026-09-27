---
name: lin-debate
description: This skill should be used when a lin-hsiu-hau-mentor output ends with a "## 結論草稿" block, or the user says 「開辯論」 or 「重新辯論」. It checks the Lin brain's conclusion index for a reusable card, and otherwise runs a 4-critic debate (Skeptic, Bridge auditor, Practitioner, Field insider) with the main thread as judge, then stores the outcome as an archive record, a conclusion card, an index line, and at most one insight-queue line. Conclusion points only — never for ordinary teaching turns.
---

# lin-debate — conclusion debate for the Lin brain

Paths: `L = C:\Users\Ande\Desktop\NTHU\aa\M_Lectrues\lin-study`. Role prompts: `references/roles/`.
You (main thread) are the **judge**: you never argue a side.

**Main thread:** before dispatching `lin-hsiu-hau-mentor` on any topic, run Step 0's grep of `memory/index.md` first; on an Exact hit answer from the card and do not dispatch.

## Step 0 — Index check (always first)
1. Extract 3–6 keywords from the question. `grep -i` each against `L/memory/index.md`.
2. Route:
   - **Exact:** same question, `conf: high`, recheck not passed → the proposer (or you) must state in one line why the new question is the same. If that line holds: answer from the card, update `used:`, tell the user "reused C### (date)". **Stop — no debate.** If it can't be stated: treat as Related.
   - **Related** (or exact but medium/low, or exact at high confidence whose recheck date has passed): read matched cards; debate only the **delta** (what the new draft adds or changes). Pass cards to the proposer as the starting point.
   - **None:** full debate.
   - 「重新辯論」 → full debate regardless.

## Step 1 — Draft
Use the `## 結論草稿` block from the mentor's output. If absent (manual 「開辯論」), dispatch `lin-hsiu-hau-mentor` asking for its conclusion with the block. Keep its agent ID for Step 3.

## Step 2 — Critique (4 in parallel, one message)
Dispatch four `general-purpose` agents with the prompts in `references/roles/{skeptic,bridge-auditor,practitioner,field-insider}.md`, filling `{QUESTION}`, `{DRAFT}` (full block + supporting text), `{SCOPE}` = "full" or "delta only: <delta>". Critics never see each other.
**Filter:** discard any objection lacking a concrete failure case. Keep ≤3 per role.
**Severity (all roles):** fatal = the conclusion flips · major = the conclusion needs a scope limit · minor = wording/polish.

## Step 3 — Revision
Continue the same proposer (SendMessage to its agent ID; load SendMessage via ToolSearch if deferred) with the surviving objections, numbered. If that agent is no longer reachable, dispatch a fresh `lin-hsiu-hau-mentor` with the question + its draft pasted inline + the objections. Instruction: "For each objection: CONCEDE (revise the conclusion) or REFUTE (evidence or derivation). Then output a revised ## 結論草稿 block."

## Step 4 — Optional round 2 (max)
Only if a **fatal** objection was refuted: send that refutation to the critic role that raised it (fresh dispatch, same role prompt + refutation). If it still stands with a concrete case → mark open. Then stop.

## Step 5 — Judge & record
Confidence: **high** = no open major/fatal · **medium** = open majors only · **low** = any open fatal.
**Revision text is unreviewed:** any claim, number, or threshold that first appears in the proposer's revision (not in the draft the critics saw) counts as unreviewed. Final confidence = min(rule result, the proposer's own self-rated confidence), and is capped at medium unless round 2 re-checks the revised claims.
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
Per `L/debates/00-review-log.md` rules: promote patterns (G2–G5 + G-K + budget via `L/memory/efficiency-ledger.md`; **G-K kernel check** = the pattern is derivable (not a slogan), falsifiable, consistent with depth-first (D0), and stated as a tool, not a conclusion; kernel M-moves additionally need G1), merge same-question cards, drop cards unused 90 days and not high, and if 5 debates changed no conclusion, report that the trigger scope should be cut. **Fidelity guard:** if G-moves would outnumber kernel M-moves after a promotion, stop and run a fidelity audit (zero-context subagent traces each G-move to the kernel, as in the 2026-07-04 audit) before admitting it. Log one row.

## Standing rule
If the user disputes a card's conclusion, set that card to `confidence: medium` immediately (index line too), so it can never be reused without a debate.

## Report to the user
Final conclusion · confidence · open objections (one line each) · record link · card ID · "route: full/delta/reused".
