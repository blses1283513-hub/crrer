"""Build Eudic (歐路詞典) study files from docs/eudic/glossary.yaml.

    python -m metro_toolkit.eudic            # writes docs/eudic/out/
    python -m metro_toolkit.eudic --check    # validate the glossary only

Outputs, per tool (metro-toolkit, semiyield, waferlens, sem-toolkit) and combined (all):

A. Vocabulary list (生詞本) for my.eudic.net -> 導入生詞本
   vocab_<tool>.csv   two columns: term, definition (zh | note | example | translation)
   words_<tool>.txt   one term per line (fallback if the CSV import only takes words)

B. Custom dictionary (自訂詞庫) for Eudic's 詞庫編輯器
   dict_<tool>.txt    term@HTML, one entry per line; also Chinese headwords that
                      point back to the English term, so you can look up both ways

All files are UTF-8 with Windows (CRLF) line endings.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
from pathlib import Path

import yaml

from .config import ROOT

GLOSSARY = ROOT / "docs" / "eudic" / "glossary.yaml"
OUT_DIR = ROOT / "docs" / "eudic" / "out"
TOOLS = {"mt": "metro-toolkit", "sy": "semiyield", "wl": "waferlens", "st": "sem-toolkit"}
FIELDS = ("en", "zh", "note", "ex", "ex_zh", "tools")


def load_glossary(path: Path = GLOSSARY) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["terms"]


def check(terms: list[dict]) -> list[str]:
    """Return problems: missing fields, unknown tools, duplicates, characters that break the formats."""
    problems, seen = [], set()
    for i, t in enumerate(terms):
        tag = t.get("en", f"#{i}")
        for f in FIELDS:
            if not t.get(f):
                problems.append(f"{tag}: missing '{f}'")
        for tool in t.get("tools", []):
            if tool not in TOOLS:
                problems.append(f"{tag}: unknown tool '{tool}'")
        key = str(t.get("en", "")).lower()
        if key in seen:
            problems.append(f"{tag}: duplicate term")
        seen.add(key)
        for f in FIELDS[:-1]:
            v = str(t.get(f, ""))
            if "\n" in v or "\r" in v:
                problems.append(f"{tag}: newline in '{f}'")
        if "@" in str(t.get("en", "")) or "@" in str(t.get("zh", "")):
            problems.append(f"{tag}: '@' in headword breaks the dictionary format")
    return problems


def zh_headword(zh: str) -> str:
    """Main Chinese term without the bracketed part: '量測（計量）' -> '量測'."""
    return re.split(r"[（(]", zh, maxsplit=1)[0].strip()


def definition_line(t: dict) -> str:
    return f"{t['zh']}｜{t['note']}｜例：{t['ex']}｜譯：{t['ex_zh']}"


def entry_html(t: dict) -> str:
    e = html.escape
    tools = ", ".join(TOOLS[k] for k in t["tools"])
    return (
        f"<b>{e(t['en'])}</b>　<span style=\"color:#1c5cab\">{e(t['zh'])}</span><br>"
        f"{e(t['note'])}<br>"
        f"<i>{e(t['ex'])}</i><br>{e(t['ex_zh'])}<br>"
        f"<span style=\"color:#898781;font-size:smaller\">{e(tools)}</span>"
    )


def build(terms: list[dict], out_dir: Path = OUT_DIR) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    groups = {name: [t for t in terms if key in t["tools"]] for key, name in TOOLS.items()}
    groups["all"] = list(terms)
    counts = {}
    for name, items in groups.items():
        items = sorted(items, key=lambda t: t["en"].lower())
        counts[name] = len(items)
        with open(out_dir / f"vocab_{name}.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\r\n")
            for t in items:
                w.writerow([t["en"], definition_line(t)])
        with open(out_dir / f"words_{name}.txt", "w", encoding="utf-8", newline="\r\n") as fh:
            fh.write("\n".join(t["en"] for t in items) + "\n")

        entries: dict[str, str] = {t["en"]: entry_html(t) for t in items}
        reverse: dict[str, list[str]] = {}
        for t in items:
            reverse.setdefault(zh_headword(t["zh"]), []).append(t["en"])
        for zh, ens in reverse.items():
            if zh and zh not in entries:
                entries[zh] = "<br>".join(f"→ <b>{html.escape(en)}</b>" for en in ens)
        with open(out_dir / f"dict_{name}.txt", "w", encoding="utf-8", newline="\r\n") as fh:
            for head, body in entries.items():
                fh.write(f"{head}@{body}\n")
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glossary", type=Path, default=GLOSSARY)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--check", action="store_true", help="validate only, write nothing")
    args = ap.parse_args(argv)
    terms = load_glossary(args.glossary)
    problems = check(terms)
    if problems:
        raise SystemExit("glossary problems:\n  " + "\n  ".join(problems))
    if args.check:
        print(f"OK: {len(terms)} terms")
        return
    for name, n in build(terms, args.out).items():
        print(f"  {name:<14} {n:>4} terms")
    print(f"written to {args.out}")


if __name__ == "__main__":
    main()
