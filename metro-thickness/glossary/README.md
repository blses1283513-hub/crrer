---
tags: [metro-thickness, glossary, eudic]
created: 2026-10-06
---

# Technical glossary and Eudic dictionary（技術詞彙與歐路詞典匯入）

← [[00 - Metro Thickness Hub]] · short glossary: [[26 Glossary]]

`terms.json` is the single source: 207 thin-film metrology terms, each with an English term, aliases, Chinese name, a one-line English definition, a one-line Chinese definition, related words and the note that explains it. It feeds two outputs:

1. **Hover popups in the study guide** (the published web page).
2. **Eudic files** in `eudic/`, rebuilt with `python build_eudic.py` (needs `pip install mdict-utils`).

| File | Use |
|---|---|
| `eudic/MetroThickness.mdx` | Custom MDict dictionary: 207 entries + 205 alias redirects (e.g. "SE" → Ellipsometry). Related words are clickable links between entries. |
| `eudic/metro-terms-wordlist.txt` | One headword per line, for Eudic's vocabulary book (生詞本) review. |
| `eudic/metro-terms.csv` | Full table (UTF-8 with BOM, opens in Excel); also usable for Anki or other flashcard apps. |
| `eudic/MetroThickness.txt` | MDX source text, for inspection or re-packing. |

## Importing into Eudic（匯入歐路詞典）

Menu names differ slightly between Eudic versions and platforms; look for the equivalent entries.

**Add the dictionary (all platforms)**
- *Windows / Mac:* Settings (設定) → Dictionary library (詞典庫 / 詞典管理) → Add local dictionary (添加本地詞典) → choose `MetroThickness.mdx`.
- *iPhone / Android:* Dictionary library (詞典庫) → Import (導入) → copy `MetroThickness.mdx` in via Wi-Fi transfer or the Files app.
- Move "Metro Thickness 膜厚量測術語" near the top of the dictionary order so it appears first in lookups.

**Hover lookup anywhere (desktop)**
- Turn on screen word capture (屏幕取詞) and choose a trigger (for example, hover + Ctrl). Pointing at "ellipsometry", "Cpk" or "XRR" in a PDF or browser then shows the technical entry above the general dictionaries.
- Screen capture usually grabs a single word. Multi-word terms are also stored under single-word aliases where possible (e.g. "Kiessig"), and you can always look up the full phrase in the search box.

**Vocabulary book (optional)**
- Vocabulary book (生詞本) → Import (導入) → `metro-terms-wordlist.txt`, then review with Eudic's flashcards.

## Editing
Add or correct entries in `terms.json` (keep `note` equal to an existing note name), then rerun `build_eudic.py` and rebuild the study guide.
