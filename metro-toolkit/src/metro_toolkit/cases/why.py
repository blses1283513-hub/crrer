"""Why a wrong answer does not fit: comments for the debrief, the saved report and the follow-up block.

why_options.yaml   for every pool option: ``when`` it is the right answer (the evidence that points to it) and, for
                   causes, what the charts would ``look`` like if it were the cause; for every role: when it ``need``s
                   to be told and when it can be ``skip``ped. Generic: no placeholders, true in every case.
why_cases.yaml     per case type: ``check_first`` (the one chart or number to look at first next time) and ``notes``
                   (sharper "why not here" texts for common mix-ups; {placeholders} = that case type's values). A note is
                   only shown when its option is not a right answer of the case.

A comment = what you chose · when that is right · why not here (note, if any) · what this data shows (the chart
findings with their numbers) · the model answer and when it is right · the deciding chart.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from ..guide import charts, fill, meta
from . import Case, role_name

HERE = Path(__file__).resolve().parent
ORDER = {"act": 0, "watch": 1, "good": 2}


@lru_cache(maxsize=None)
def texts() -> dict:
    out = {"options": {}, "roles": {}, "cases": {}}
    for name in ("why_options.yaml", "why_cases.yaml"):
        path = HERE / name
        if path.exists():
            for k, v in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).items():
                out.setdefault(k, {}).update(v or {})
    return out


def when_text(option: str, lang: str) -> str:
    return ((texts()["options"].get(option) or {}).get("when") or {}).get(lang, "")


def looks_text(option: str, lang: str) -> str:
    return ((texts()["options"].get(option) or {}).get("looks") or {}).get(lang, "")


def role_text(role: str, need: bool, lang: str) -> str:
    return ((texts()["roles"].get(role) or {}).get("need" if need else "skip") or {}).get(lang, "")


def _sub(case: Case, key: str) -> Case:
    """The single-situation case a question belongs to (a problem of a separate handover, or the case itself)."""
    parts = case.spec.get("parts")
    if parts and key[:1] == "p" and "_" in key:
        from .compose import _sub_case

        try:
            return _sub_case(parts[int(key[1:key.index("_")]) - 1])
        except (ValueError, IndexError):
            return case
    return case


def case_note(case: Case, option: str, lang: str) -> str:
    entry = (texts()["cases"].get(case.type) or {}).get("notes", {}).get(option)
    return fill(entry.get(lang), case.facts, lang) if entry else ""


def check_first(case: Case, lang: str) -> str:
    entry = (texts()["cases"].get(case.type) or {}).get("check_first")
    return fill(entry.get(lang), case.facts, lang) if entry else ""


def findings(case: Case, lang: str, n: int = 3) -> list[str]:
    """What the data says, most serious chart first (the same sentences as the chart panels)."""
    out = []
    for _, f in sorted(case.guide, key=lambda kf: ORDER.get(kf[1].status, 3)):
        for line in (f.zh if lang == "zh" else f.en):
            if line not in out:
                out.append(line)
    return out[:n]


def deciding_chart(case: Case, lang: str) -> str:
    if not case.guide:
        return ""
    key, _ = sorted(case.guide, key=lambda kf: ORDER.get(kf[1].status, 3))[0]
    title = (charts().get(key) or {}).get("title") or {}
    return title.get(lang, key)


def _opt(case: Case, q, option: str, lang: str) -> str:
    return q.option_text(option, lang)


def comments(case: Case, result: dict) -> list[dict]:
    """One entry per wrong (or partly wrong) question: {key, kind, label, group, chosen, correct, missing, extra}."""
    out = []
    for q in case.questions:
        r = result["questions"][q.key]
        if r["ok"]:
            continue
        if q.kind == "single":
            out.append({"key": q.key, "kind": "single", "q": q, "chosen": r["answer"], "correct": r["accepted"]})
        else:
            out.append({"key": q.key, "kind": q.kind, "q": q, "missing": r["missing"], "extra": r["extra"],
                        "correct": r["correct"]})
    return out


def comment_lines(case: Case, c: dict, lang: str) -> list[str]:
    """The comment on one wrong question, as short lines (Markdown) in one language."""
    zh = lang == "zh"
    q, sub = c["q"], _sub(case, c["key"])
    lines = []
    if c["kind"] == "single":
        chosen = c["chosen"]
        if chosen is None:
            lines.append("你沒有作答。" if zh else "You left this unanswered.")
        elif q.category == "priority":
            from .compose import URGENCY_TEXT, urgency_of

            parts = case.spec.get("parts") or []
            try:
                mine = urgency_of(_sub(case, f"{chosen.lower()}_x")) if parts else None
            except (ValueError, IndexError):
                mine = None
            top = urgency_of(_sub(case, f"{c['correct'][0].lower()}_x")) if parts else None
            lines.append(f"**你選了** {_opt(case, q, chosen, lang)}" if zh else f"**You chose** {_opt(case, q, chosen, lang)}")
            if mine is not None and top is not None:
                lines.append(f"它的緊急程度：{URGENCY_TEXT[mine][lang]}；最緊急的那件：{URGENCY_TEXT[top][lang]}。" if zh else
                             f"Its urgency: {URGENCY_TEXT[mine][lang]}; the most urgent item: {URGENCY_TEXT[top][lang]}.")
            lines.append("規則：產品正在受影響的先處理（先止血），可以排程的最後。" if zh else
                         "Rule: whatever puts product at risk right now goes first (contain it); anything that can be scheduled goes last.")
        else:
            lines.append(f"**你選了** {_opt(case, q, chosen, lang)}" if zh else f"**You chose** {_opt(case, q, chosen, lang)}")
            w = when_text(chosen, lang)
            if w:
                lines.append(f"**這個答案在什麼時候才對：** {w}" if zh else f"**When this is the right answer:** {w}")
            note = case_note(sub, chosen, lang) if chosen not in c["correct"] else ""
            if note:
                lines.append(f"**為什麼這裡不是：** {note}" if zh else f"**Why not here:** {note}")
            right = c["correct"][0]
            lines.append(f"**標準答案** {_opt(case, q, right, lang)}" if zh else f"**Model answer** {_opt(case, q, right, lang)}")
            w = when_text(right, lang)
            if w:
                lines.append(f"**它對的條件：** {w}" if zh else f"**When that one is right:** {w}")
    elif c["kind"] == "roles":
        for r in c["missing"]:
            t = role_text(r, True, lang)
            lines.append(f"**漏了 {role_name(r, lang)}：** {t}" if zh else f"**Missed {role_name(r, lang)}:** {t}")
        for r in c["extra"]:
            t = role_text(r, False, lang)
            lines.append(f"**多了 {role_name(r, lang)}：** {t}" if zh else f"**Extra {role_name(r, lang)}:** {t}")
    else:  # multi: select all causes present
        for o in c["extra"]:
            w = when_text(o, lang)
            lines.append((f"**你多選了** {_opt(case, q, o, lang)}：這個原因要有這些證據才成立：{w}" if zh else
                          f"**You added** {_opt(case, q, o, lang)}: that cause needs this evidence: {w}"))
        for o in c["missing"]:
            w = looks_text(o, lang) or when_text(o, lang)
            lines.append((f"**你漏了** {_opt(case, q, o, lang)}：它在圖上的樣子：{w}" if zh else
                          f"**You missed** {_opt(case, q, o, lang)}: how it shows on the charts: {w}"))
    data = findings(sub, lang)
    if data:
        lines.append(("**這份資料顯示：** " if zh else "**What this data shows:** ") + ("；" if zh else "; ").join(data))
    chart = deciding_chart(sub, lang)
    if chart and c["kind"] != "roles":
        lines.append((f"**關鍵的圖：** {chart}" if zh else f"**The deciding chart:** {chart}"))
    return lines


def followup_answers(case: Case, c: dict, lang: str) -> list[tuple[str, str]]:
    """Ready follow-up questions for one wrong single answer, with answers: why not X, what X would look like, what to
    check first next time."""
    if c["kind"] != "single" or not c["chosen"] or c["q"].category == "priority":
        return []
    zh = lang == "zh"
    q, sub, x = c["q"], _sub(case, c["key"]), c["chosen"]
    name = _opt(case, q, x, lang)
    why = [case_note(sub, x, lang), when_text(x, lang) and ((f"這個答案要成立需要：{when_text(x, lang)}" if zh else
                                                            f"For it to be right you would need: {when_text(x, lang)}"))]
    why.append(("這份資料實際顯示：" if zh else "What this data actually shows: ") + ("；" if zh else "; ").join(findings(sub, lang)))
    out = [(f"為什麼不是「{name}」？" if zh else f"Why isn't it \"{name}\"?", "\n\n".join(t for t in why if t))]
    look = looks_text(x, lang) if q.category == "cause" else ""
    if look:
        out.append((f"如果真的是「{name}」，圖會長什麼樣？" if zh else f"What would the charts look like if it were \"{name}\"?", look))
    first = check_first(sub, lang)
    if first:
        out.append(("下次遇到類似狀況，先檢查什麼？" if zh else "What should I check first next time?", first))
    return out


def report_section(case: Case, result: dict, langs: list[str]) -> list[str]:
    """Markdown lines for the saved report: a comment on every wrong answer."""
    items = comments(case, result)
    if not items:
        return []
    both = len(langs) > 1
    lines = ["", "## " + ("你的錯誤答案為什麼不對 · Why your wrong answers don't fit" if both else
                          "你的錯誤答案為什麼不對" if langs[0] == "zh" else "Why your wrong answers don't fit"), ""]
    for c in items:
        lines += [f"### {' / '.join(c['q'].label[lg] for lg in langs)}" + (f" ({' / '.join(c['q'].group[lg] for lg in langs)})"
                                                                            if c["q"].group else ""), ""]
        for lg in langs:
            lines += [f"- {ln}" for ln in comment_lines(case, c, lg)]
            lines.append("")
    return lines


__all__ = ["check_first", "comment_lines", "comments", "deciding_chart", "findings", "followup_answers", "looks_text",
           "report_section", "role_text", "texts", "when_text"]
