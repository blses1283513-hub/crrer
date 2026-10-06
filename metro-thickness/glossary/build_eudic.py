"""
build_eudic.py — export terms.json for the Eudic (歐路詞典) app.

Outputs in ./eudic/:
  MetroThickness.mdx        custom MDict dictionary (import into Eudic's dictionary library)
  MetroThickness.txt        the MDX source text (re-pack or inspect)
  metro-terms-wordlist.txt  one headword per line (import into Eudic's vocabulary book, 生詞本)
  metro-terms.csv           term, Chinese, English definition, Chinese definition, related, note

Run:  pip install mdict-utils && python build_eudic.py
"""
import csv
import html
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "eudic"
OUT.mkdir(exist_ok=True)

terms = json.loads((HERE / "terms.json").read_text(encoding="utf-8"))
lookup = {}
for t in terms:
    lookup[t["term"].lower()] = t["term"]
    for a in t["alt"]:
        lookup[a.lower()] = t["term"]

# Inline styles only: Eudic renders MDX entries as HTML, external CSS needs an MDD file.
S_HEAD = "font-size:1.15em;font-weight:600;color:#2b3590"
S_ZH = "font-size:1.05em;margin-left:8px;color:#333"
S_ALT = "color:#777;font-size:0.85em;margin:2px 0 6px"
S_DEF = "margin:4px 0"
S_LBL = "display:inline-block;min-width:2.2em;color:#fff;background:#3a45b0;border-radius:3px;padding:0 4px;margin-right:6px;font-size:0.8em;text-align:center"
S_REL = "margin:6px 0 2px;font-size:0.92em"
S_SRC = "color:#888;font-size:0.8em;margin-top:6px"


def entry_html(t):
    alts = ", ".join(html.escape(a) for a in t["alt"])
    rel_parts = []
    for r in t["rel"]:
        target = lookup.get(r.lower())
        if target:
            rel_parts.append(f'<a href="entry://{html.escape(target)}">{html.escape(r)}</a>')
        else:
            rel_parts.append(html.escape(r))
    return (
        f'<div style="font-family:sans-serif;line-height:1.5">'
        f'<span style="{S_HEAD}">{html.escape(t["term"])}</span>'
        f'<span style="{S_ZH}">{html.escape(t["zh"])}</span>'
        + (f'<div style="{S_ALT}">also: {alts}</div>' if alts else "")
        + f'<div style="{S_DEF}"><span style="{S_LBL}">EN</span>{html.escape(t["en"])}</div>'
        f'<div style="{S_DEF}"><span style="{S_LBL}">中</span>{html.escape(t["zhdef"])}</div>'
        f'<div style="{S_REL}"><b>Related 相關詞:</b> {" · ".join(rel_parts)}</div>'
        f'<div style="{S_SRC}">Metro Thickness Tools Book · {html.escape(t["note"])}</div>'
        f"</div>"
    )


lines = []
seen = set()
for t in terms:
    lines += [t["term"], entry_html(t), "</>"]
    seen.add(t["term"].lower())
for t in terms:
    for a in t["alt"]:
        if a.lower() in seen:
            continue
        seen.add(a.lower())
        lines += [a, f"@@@LINK={t['term']}", "</>"]

src = OUT / "MetroThickness.txt"
src.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
(OUT / "title.html").write_text("Metro Thickness 膜厚量測術語", encoding="utf-8")
(OUT / "description.html").write_text(
    f"{len(terms)} thin-film metrology terms with Chinese, short EN/中 definitions and related words. "
    "Vendor-agnostic study glossary.",
    encoding="utf-8",
)
mdx = OUT / "MetroThickness.mdx"
if mdx.exists():
    mdx.unlink()
subprocess.run(
    ["mdict", "--title", str(OUT / "title.html"), "--description", str(OUT / "description.html"),
     "-a", str(src), str(mdx)],
    check=True,
)

(OUT / "metro-terms-wordlist.txt").write_text("\n".join(t["term"] for t in terms) + "\n", encoding="utf-8")
with open(OUT / "metro-terms.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh)
    w.writerow(["term", "chinese", "definition_en", "definition_zh", "related", "aliases", "note"])
    for t in terms:
        w.writerow([t["term"], t["zh"], t["en"], t["zhdef"], "; ".join(t["rel"]), "; ".join(t["alt"]), t["note"]])

print(f"{len(terms)} entries, {len(seen) - len(terms)} alias links -> {mdx.name}")
