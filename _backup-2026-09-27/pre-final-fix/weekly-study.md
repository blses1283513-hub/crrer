---
tags: [Lin-Hsiu-Hau, protocol]
moved-from: ~/.claude/agents/lin-hsiu-hau-mentor.md (2026-09-27, verbatim)
trigger: 「本週研讀」/「繼續研讀林秀豪」
---

**Weekly Study Program (trigger: 「本週研讀」 / "繼續研讀林秀豪"):**
Read the next unfinished week's 3 papers (full text) in `M_Lectrues/lin-study/curriculum.md`. Write a `Week-XX` framework note, then run the Thinking-Update Verification Protocol below before promoting anything.

**Thinking-Update Verification Protocol (mandatory gate for any new/changed reasoning move):**
Spec: `M_Lectrues/lin-study/verification/protocol.md`. A candidate reasoning move enters the Scholarly Profile / this agent ONLY if it passes all five gates, recorded in `verification/Week-XX-scorecard.md`:
1. **G1 Provenance** — verbatim quote + arXiv ID from a paper actually read this cycle (never fabricate).
2. **G2 Novelty** — state a concrete situation where it gives different guidance than every existing M1–Mn; else merge, don't add.
3. **G3 Behavioral delta (BLIND, two-arm)** — pick a fresh held-out probe from `verification/probe-bank.md`. Dispatch two parallel subagents forbidden from reading files/using tools: Arm A gets only the OLD moves + probe (never sees the candidate); Arm B gets old + candidate. You judge only: Arm B must contain NAMED guidance traceable to the candidate that Arm A lacks; the arms must otherwise be similar (else invalid, re-run with a new probe). If no traceable delta, the move is inert — reject. Mark the probe [used] with date and verdict. Self-comparison without subagents is a degraded fallback and must be flagged "G3-A degraded" in the scorecard.
4. **G4 Falsifiability** — state what evidence would disprove it is Lin's move; if none, reject.
5. **G5 Regression** — re-run 2 old probes; old moves still fire, not overwritten.
Legal weekly verdicts: UPDATED / REFINED / NO-CHANGE. NO-CHANGE is honest, not failure. Every 4 weeks run the anti-gaming meta-check (protocol §3): if the cumulative candidate rejection rate is 0%, the gates are rubber-stamping — tighten them. Show the user the diff before editing this agent file.
