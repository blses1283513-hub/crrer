# Eudic (歐路詞典) study files

210 Metro AE terms in Traditional Chinese (Taiwan fab usage). Each term has a translation, a one-line
explanation, and an example sentence with its translation, tagged by tool.

| Tool | Terms | Vocabulary list (A) | Custom dictionary (B) |
|---|---|---|---|
| metro-toolkit | 154 | `out/vocab_metro-toolkit.csv` | `out/dict_metro-toolkit.txt` |
| SemiYield | 68 | `out/vocab_semiyield.csv` | `out/dict_semiyield.txt` |
| WaferLens | 70 | `out/vocab_waferlens.csv` | `out/dict_waferlens.txt` |
| sem-toolkit | 60 | `out/vocab_sem-toolkit.csv` | `out/dict_sem-toolkit.txt` |
| **All (deduplicated)** | 210 | `out/vocab_all.csv` | `out/dict_all.txt` |

Terms shared by several tools appear in each of those files.

> The file formats follow Eudic's documentation and common user guides (word,definition CSV for the
> vocabulary list; `word@HTML` lines for the dictionary editor). They were checked for encoding and
> structure but **not imported into the Eudic app here**. If one route fails, try the other, or the
> fallback word list `out/words_<tool>.txt`.

## A. Vocabulary list (生詞本): review cards

1. Open https://my.eudic.net and sign in with your Eudic account.
2. Go to **生詞本 → 導入生詞本** (Import).
3. Upload `vocab_<tool>.csv` (columns: term, then 釋義｜說明｜例句｜譯文). Create one 生詞本 per tool if you want
   separate review lists.
4. If the import only accepts words, upload `words_<tool>.txt` instead (one term per line); Eudic then
   fills in its own dictionary definitions.
5. Sync the app on your phone or PC; the list appears under 生詞筆記.

If Chinese shows as garbled text: open the file in Notepad → 另存新檔 → encoding **UTF-8** (or **UTF-8 with BOM**) → re-upload.

## B. Custom dictionary (自訂詞庫): lookup with example sentences

1. Download the free **詞庫編輯器** from https://www.eudic.net/eudic/builder.aspx (Windows).
2. Choose source format **自定義文本 (txt)**, select `dict_<tool>.txt` (`term@HTML`, one entry per line).
3. Build the dictionary, then add the generated file in Eudic: **設定 → 詞典管理 → 匯入/新增本地詞庫**.
4. Looking up an English term shows your entry; looking up the Chinese term (e.g. `膜厚`) points back to
   the English one.

## Adding or editing terms

Edit `glossary.yaml` (one block per term), then rebuild:

```powershell
python -m metro_toolkit.eudic --check    # validate
python -m metro_toolkit.eudic            # rewrite out/
```
