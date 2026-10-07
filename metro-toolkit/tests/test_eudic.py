import csv

from metro_toolkit.eudic import TOOLS, build, check, load_glossary, zh_headword


def test_glossary_is_valid():
    terms = load_glossary()
    assert check(terms) == []
    assert len(terms) >= 150
    for key in TOOLS:
        assert sum(key in t["tools"] for t in terms) >= 40


def test_build_formats(tmp_path):
    terms = load_glossary()
    counts = build(terms, tmp_path)
    assert counts["all"] == len(terms)
    rows = list(csv.reader(open(tmp_path / "vocab_all.csv", encoding="utf-8", newline="")))
    assert len(rows) == len(terms) and all(len(r) == 2 for r in rows)
    raw = (tmp_path / "dict_all.txt").read_bytes()
    assert b"\r\n" in raw and not raw.startswith(b"\xef\xbb\xbf")
    lines = raw.decode("utf-8").split("\r\n")[:-1]
    assert all("@" in line and "\n" not in line for line in lines)
    heads = {line.split("@", 1)[0] for line in lines}
    assert "film thickness" in heads and "膜厚" in heads


def test_zh_headword():
    assert zh_headword("量測（計量）") == "量測"
    assert zh_headword("膜厚") == "膜厚"
