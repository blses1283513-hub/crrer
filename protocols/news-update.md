---
tags: [Lin-Hsiu-Hau, protocol]
moved-from: ~/.claude/agents/lin-hsiu-hau-mentor.md (2026-09-27, verbatim)
trigger: 「更新林教授動態」
---

**Industry Watch Protocol (news updates):**
When asked to update Prof. Lin's news (e.g. "更新林教授動態"), do this:
1. WebSearch recent public information: queries like `林秀豪 清華 物理` / `"Hsiu-Hau Lin" NTHU` plus site-specific checks of phys.site.nthu.edu.tw, cosr.site.nthu.edu.tw, nthu-tsmc.site.nthu.edu.tw.
2. Edit `C:\Users\Ande\Desktop\NTHU\aa\M_Lectrues\lin-news.js`: keep the existing schema (`window.LIN_NEWS = { lastUpdated, items: [{date, title, body, source, verified, tag}] }`), update `lastUpdated` to today, add new items at the top, keep old items.
3. Verification rules are hard constraints: only record publicly verifiable facts with a source URL and `verified: true`; anything user-claimed or rumored gets `verified: false` and tag `待查證`. Known verified facts as of 2026-07-04: TSMC 專屬 JDP 教授 (nthu-tsmc.site.nthu.edu.tw), 2025 台灣物理學會物理教育傑出獎, 特聘教授 (物理系＋半導體研究學院). The user's claim that he is a TSMC "顧問" is NOT yet verified — official wording is JDP professor.
4. This is public-figure professional news only — do not collect or record personal/private information.
