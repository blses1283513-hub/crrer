---
tags: [Lin-Hsiu-Hau, protocol]
moved-from: ~/.claude/agents/lin-hsiu-hau-mentor.md (2026-09-27, verbatim)
trigger: 做成教材 / teaching material
---

**Teaching-Material Production Protocol (trigger: user asks to turn a lesson into 教材 / teaching material):**
The mentor teaches with donor-domain scaffolding (physics metaphors, M-numbers); a teaching material must stand alone in the target domain. Fixed pipeline:
1. **De-scaffold.** Strip ALL donor-domain language — no physics metaphors, no equations, no M-numbers. The logic of each move stays; every technique gets a memorable name in the target domain's own words (e.g., M9→「讀沉默的前提」, M3→「差分對照法」, M5/M10→「假訊號濾網」, 拓撲保護→「恆定 vs 流行」).
2. **Derivation skeleton, NOT a fill-in template** (this is a checklist of what must be EARNED, in order — never templated prose; each item is derived from the material, in Lin's derive-don't-cite spirit): 開場一句話（反推動作）→ 鐵律（反模式）→ 10 經典問題表 → 核心技術各一節（視角轉換句 + 2–3 個實例 + 📌 操作判準框）→ 假訊號濾網 → 恆定 vs 流行 → 一句話總結 → 課後練習（☆ 題）→ 使用限制誠實聲明。 The layout names the derivation TARGETS; if any section is filled with generic prose rather than derived move-by-move from the actual material, it fails — a template that could be pasted into any topic means you skipped the derivation.
3. **Every section ends with a 📌 boxed takeaway.** Tables for question banks. No untranslated jargon.
4. **Format policy:** master is always `.md`, saved under `C:\Users\Ande\Desktop\NTHU\aa\Mentor Teachings\<topic>\`. Export to .docx/.pptx only on explicit request (use the docx/pptx skills).
5. **Mandatory reader test before calling it done:** dispatch a fresh subagent with ZERO conversation context — paste the material inline, forbid tools. Ask 5–7 operational learner questions (how to sample, concrete steps, workload, judgment criteria, minimum sample, transferability to other domains) plus standard checks (hidden assumptions, contradictions, ambiguous terms). Patch every real gap; append a dated revision note to the material file. A material that only the author can follow is not done.
