"""Case study practice: random, realistic Metro AE situations with one known cause, scored answers and a debrief.

A case ID such as ``spc_chamber_shift-I-04217`` (type, level B/I/A, seed) always regenerates the same case.
Texts (brief, options, explanation, model message, message checklist) live in cases.yaml; data comes from
generators.py, which reuses the toolkit's simulators so the charts are the same as on the other pages.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from ..guide import Facts, fill, meta
from .generators import GENERATORS

HERE = Path(__file__).resolve().parent
LEVELS = ("basic", "intermediate", "advanced")
LEVEL_CODE = {"basic": "B", "intermediate": "I", "advanced": "A"}
WEIGHTS = {"cause": 40, "action": 25, "decision": 20, "notify": 15}


@lru_cache(maxsize=None)
def library() -> dict:
    return yaml.safe_load((HERE / "cases.yaml").read_text(encoding="utf-8"))


def case_types(domain: str | None = None) -> list[str]:
    return [k for k, c in library()["cases"].items() if domain in (None, c["domain"])]


def make_id(case_type: str, level: str, seed: int) -> str:
    return f"{case_type}-{LEVEL_CODE[level]}-{seed:05d}"


def parse_id(case_id: str) -> tuple[str, str, int]:
    case_type, code, seed = case_id.strip().rsplit("-", 2)
    level = {v: k for k, v in LEVEL_CODE.items()}[code.upper()]
    if case_type not in library()["cases"]:
        raise ValueError(f"unknown case type {case_type}")
    return case_type, level, int(seed)


@dataclass
class Case:
    id: str
    type: str
    level: str
    spec: dict  # the cases.yaml entry
    v: dict
    evidence: list
    guide: list
    correct: dict  # cause, action, decision (option ids) and notify (role list)
    options: dict = field(default_factory=dict)  # question -> option ids in display order

    @property
    def facts(self) -> Facts:
        return Facts(v=self.v)

    def text(self, key: str, lang: str) -> str:
        entry = self.spec.get(key)
        return fill(entry.get(lang), self.facts, lang) if entry else ""

    def option_text(self, question: str, option: str, lang: str) -> str:
        return option_label(question, option, lang)


def option_label(question: str, option: str, lang: str) -> str:
    """Text of an answer option (cause / action / decision) in one language."""
    pool = {"cause": "causes", "action": "actions", "decision": "decisions"}[question]
    return library()["pools"][pool][option][lang]


def generate(case_id: str) -> Case:
    case_type, level, seed = parse_id(case_id)
    spec = library()["cases"][case_type]
    rng = np.random.default_rng(seed)
    out = GENERATORS[case_type](rng, level)
    correct = {"cause": spec["cause"], "action": spec["action"], "decision": spec["decision"],
               "notify": list(spec.get("notify", []))}
    correct.update(out.get("answer", {}))
    order = np.random.default_rng(seed + 1)
    options = {}
    for q in ("cause", "action", "decision"):
        ids = list(dict.fromkeys(spec[f"{q}_options"] + [correct[q]]))
        options[q] = [ids[i] for i in order.permutation(len(ids))]
    return Case(case_id, case_type, level, spec, out["v"], out["evidence"], out["guide"], correct, options)


def random_case(seed: int | None = None, domain: str | None = None, level: str | None = None) -> Case:
    rng = np.random.default_rng(seed)
    types = case_types(domain)
    case_type = types[int(rng.integers(len(types)))]
    level = level or LEVELS[int(rng.integers(3))]
    return generate(make_id(case_type, level, int(rng.integers(0, 100000))))


def score(case: Case, answers: dict) -> dict:
    """answers: cause, action, decision (option ids) and notify (list of role keys)."""
    rows, total = {}, 0.0
    for q in ("cause", "action", "decision"):
        ok = answers.get(q) == case.correct[q]
        pts = WEIGHTS[q] if ok else 0
        rows[q] = {"ok": ok, "points": pts, "max": WEIGHTS[q], "answer": answers.get(q), "correct": case.correct[q]}
        total += pts
    mine, right = set(answers.get("notify") or []), set(case.correct["notify"])
    jac = 1.0 if not mine and not right else len(mine & right) / len(mine | right)
    rows["notify"] = {"ok": jac == 1.0, "points": round(WEIGHTS["notify"] * jac, 1), "max": WEIGHTS["notify"],
                      "missing": sorted(right - mine), "extra": sorted(mine - right), "correct": sorted(right)}
    total += rows["notify"]["points"]
    return {"questions": rows, "total": round(total, 1)}


def message_checklist(case: Case, message: str, lang: str) -> list[tuple[str, bool]]:
    """Which key points of a good message the free text covers (case-insensitive keyword match)."""
    text = (message or "").lower()
    out = []
    for kp in case.spec.get("keypoints", []):
        tokens = [fill(t, case.facts, lang).lower() for t in kp.get("any", [])]
        ok = any(t and t != "—" and t in text for t in tokens)
        out.append((kp[lang], ok))
    return out


def role_name(role: str, lang: str) -> str:
    return meta()["roles"][role][lang]


def report_markdown(case: Case, answers: dict, result: dict, message: str, lang: str = "zh",
                    past: pd.DataFrame | None = None) -> str:
    """A study-log entry: situation, your answers vs the model answers, why, your message vs the model message,
    what a good message covers, score history (``past`` = earlier attempts) and, for every evidence chart, the
    insight, the next step and a ready message for every role. ``lang``: "zh", "en" or "both"."""
    from ..guide import STATUSES, charts, text

    langs = ["zh", "en"] if lang == "both" else [lang]
    main = langs[0]
    L = (lambda zh, en: f"{zh} · {en}" if lang == "both" else (zh if lang == "zh" else en))  # headings
    B = (lambda f: "\n\n".join(f(lg) for lg in langs))  # one block per language

    def opt(q, o, lg):
        return case.option_text(q, o, lg) if o else "—"

    status = meta()["status"]
    q_name = {"cause": L("根本原因", "Root cause"), "action": L("第一步處置", "First action"),
              "decision": L("產品／結論處置", "Disposition / decision")}
    lines = [f"# {L('案例', 'Case')} {case.id}: {B(lambda lg: case.text('title', lg)).replace(chr(10) * 2, ' · ')}", "",
             f"*{datetime.now():%Y-%m-%d %H:%M}* · {L('難度', 'Level')} {case.level} · "
             f"{L('分數', 'Score')} **{result['total']:.0f} / 100**", "",
             f"## {L('狀況', 'Situation')}", "", B(lambda lg: case.text("brief", lg)), "",
             f"## {L('你的判斷 vs 標準答案', 'Your answers vs the model answers')}", ""]
    for q in ("cause", "action", "decision"):
        r = result["questions"][q]
        mine = " / ".join(opt(q, r["answer"], lg) for lg in langs)
        lines.append(f"- **{q_name[q]}** {'✓' if r['ok'] else '✗'} {L('你', 'You')}: {mine}" +
                     ("" if r["ok"] else f"  \n  {L('標準答案', 'Model answer')}: "
                                         + " / ".join(opt(q, r["correct"], lg) for lg in langs)))
    n = result["questions"]["notify"]
    names = (lambda roles: ", ".join(" / ".join(role_name(r, lg) for lg in langs) for r in roles))
    lines.append(f"- **{L('通知對象', 'Who to notify')}** {'✓' if n['ok'] else '△'} "
                 f"{L('應通知', 'Should notify')}: {names(n['correct']) or L('不需升級（e-log 記錄即可）', 'no escalation (e-log only)')}"
                 + (f"; {L('漏了', 'missed')}: {names(n['missing'])}" if n["missing"] else "")
                 + (f"; {L('多了', 'extra')}: {names(n['extra'])}" if n["extra"] else ""))
    target = case.spec["message_role"]
    lines += ["", f"## {L('為什麼', 'Why')}", "", B(lambda lg: case.text("explanation", lg)), "",
              f"## {L('給', 'Message to')} {names([target])}", "",
              f"**{L('你寫的', 'Yours')}**", "", f"> {message.strip() or '—'}", "",
              f"**{L('範例', 'Model message')}**", "", B(lambda lg: f"> {case.text('model_message', lg)}"), "",
              f"### {L('好訊息的要點', 'What a good message covers')}", ""]
    for lg in langs:
        for item, ok in message_checklist(case, message, lg):
            lines.append(f"- {'✓' if ok else '✗'} {item}")

    # score history: earlier attempts plus this one
    lines += ["", f"## {L('分數紀錄', 'Score history')}", ""]
    rows = [] if past is None or not len(past) else past.to_dict("records")
    rows.append({"time": f"{datetime.now():%Y-%m-%d %H:%M}", "case": case.id, "type": case.type,
                 "domain": case.spec["domain"], "level": case.level, "score": result["total"]})
    hist = pd.DataFrame(rows)
    lines += [f"- {L('案例數', 'Cases')}: {len(hist)} · {L('平均', 'Mean')}: {hist['score'].mean():.0f} · "
              f"{L('最近 5 次', 'Last 5')}: {hist['score'].tail(5).mean():.0f}", "",
              f"| {L('範圍', 'Area')} | {L('次數', 'Count')} | {L('平均', 'Mean')} |", "| --- | ---: | ---: |"]
    for dom, g in hist.groupby("domain", sort=True):
        dname = " / ".join(library()["domains"].get(dom, {}).get(lg, dom) for lg in langs)
        lines.append(f"| {dname} | {len(g)} | {g['score'].mean():.0f} |")
    same = hist[hist["type"] == case.type]
    lines += ["", f"**{L('同類型案例', 'This case type')}** ({len(same)})", ""]
    lines += [f"- {r['time']} · {r['case']} · {r['level']} · {r['score']:.0f}" for r in same.to_dict("records")]

    # every evidence chart: insight, action, who to tell (same text as the chart's guide panel)
    lines += ["", f"## {L('每張圖：洞察、處置、跟誰說', 'Every chart: insight, action, who to tell')}"]
    roles = meta()["roles"]
    for key, facts in case.guide:
        c = charts().get(key)
        if c is None:
            continue
        stl = status.get(facts.status, {})
        lines += ["", f"### {B(lambda lg: text(c.get('title'), lg)).replace(chr(10) * 2, ' · ')}", "",
                  f"**{L('狀態', 'Status')}**: {stl.get('icon', '')} {' / '.join(stl.get(lg, facts.status) for lg in langs)}", "",
                  f"#### {L('代表什麼與洞察', 'Insight')}", "",
                  f"**{L('這張圖代表什麼', 'What it shows')}**", "", B(lambda lg: text(c.get("what"), lg, facts)), "",
                  f"**{L('怎麼判讀', 'How to read it (good vs bad)')}**", "", B(lambda lg: text(c.get("read"), lg, facts)), ""]
        if facts.zh or facts.en:
            lines += [f"**{L('這份資料的判讀', 'What this data says')}**", ""]
            for lg in langs:
                lines += [f"- {x}" for x in (facts.zh if lg == "zh" else facts.en)]
            lines.append("")
        lines += [f"#### {L('下一步', 'Action')}", ""]
        for s_ in [facts.status] + [x for x in STATUSES if x != facts.status]:
            act = c.get("action", {}).get(s_)
            if act:
                here = f" ← {L('目前狀態', 'current')}" if s_ == facts.status else ""
                lines += [f"**{status[s_]['icon']} {' / '.join(status[s_][lg] for lg in langs)}**{here}", "",
                          B(lambda lg: text(act, lg, facts)), ""]
        if c.get("record"):
            lines += [f"**{L('記錄（e-log / SPC comment）', 'What to record (e-log / SPC comment)')}**", ""]
            lines.append("\n>\n".join(f"> {text(c['record'], lg, facts)}" for lg in langs))
            lines.append("")
        lines += [f"#### {L('跟誰說', 'Who to tell')}", ""]
        for rk, r in roles.items():
            msg = c.get("roles", {}).get(rk)
            if msg:
                lines += [f"**{' / '.join(r[lg] for lg in langs)}**", ""]
                lines.append("\n>\n".join(f"> {text(msg, lg, facts)}" for lg in langs))
                lines.append("")
    lines += ["", "---", L("合成練習資料；實際處置以所屬晶圓廠的 OCAP 與簽核流程為準。",
                           "Synthetic practice data; in real work follow your fab's OCAP and sign-off rules.")]
    return "\n".join(lines)


def cases_dir(folder: Path | None = None) -> Path:
    import os

    from ..config import ROOT

    # data/ is git-ignored: your study log stays on this PC (METRO_CASES_PATH moves it)
    path = Path(folder or os.environ.get("METRO_CASES_PATH", ROOT / "data" / "cases"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def attempt_detail(case: Case, result: dict, message: str = "") -> dict:
    """Per-question results kept in the study log, for the cross study of all your attempts."""
    q = result["questions"]
    return {"cause_ok": q["cause"]["ok"], "action_ok": q["action"]["ok"], "decision_ok": q["decision"]["ok"],
            "notify_pts": q["notify"]["points"] / q["notify"]["max"], "missing": q["notify"]["missing"],
            "extra": q["notify"]["extra"], "wrong": {k: [q[k]["correct"], q[k]["answer"]] for k in ("cause", "action", "decision")
                                                      if not q[k]["ok"] and q[k]["answer"]},  # [model, yours]
            "msg_missed": [i for i, (_, ok) in enumerate(message_checklist(case, message, "en")) if not ok]}


def save_attempt(case: Case, result: dict, md: str, folder: Path | None = None, message: str = "") -> Path:
    """Every attempt gets its own file (<case id>_<date-time>.md) and a line in history.jsonl."""
    folder = cases_dir(folder)
    now = datetime.now()
    path = folder / f"{case.id}_{now:%Y%m%d-%H%M%S}.md"
    k = 2
    while path.exists():  # two saves within the same second
        path = folder / f"{case.id}_{now:%Y%m%d-%H%M%S}-{k}.md"
        k += 1
    path.write_text(md, encoding="utf-8")
    with open(folder / "history.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"time": f"{now:%Y-%m-%d %H:%M}", "case": case.id, "type": case.type,
                             "domain": case.spec["domain"], "level": case.level, "score": result["total"],
                             "file": path.name, **attempt_detail(case, result, message)},
                            ensure_ascii=False) + "\n")
    return path


def history(folder: Path | None = None) -> pd.DataFrame:
    path = cases_dir(folder) / "history.jsonl"
    if not path.exists():
        return pd.DataFrame(columns=["time", "case", "type", "domain", "level", "score"])
    return pd.DataFrame([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


# --------------------------------------------------------------------------- browsing and cross study
_REPORT = re.compile(r"^(?P<id>[a-z_]+-[BIA]-\d{5})(?:_(?P<ts>\d{8}-\d{6})(?:-\d+)?)?\.md$")
_SCORE = re.compile(r"\*\*(\d+(?:\.\d+)?) / 100\*\*")


def list_reports(folder: Path | None = None) -> pd.DataFrame:
    """Every saved report in the study-log folder, newest first (older <case id>.md files included)."""
    folder = cases_dir(folder)
    hist = history(folder)
    by_file = {r["file"]: r for r in hist.to_dict("records") if isinstance(r.get("file"), str)}
    rows = []
    for path in folder.glob("*.md"):
        m = _REPORT.match(path.name)
        if not m:
            continue
        try:
            case_type, level, _ = parse_id(m["id"])
        except (ValueError, KeyError):
            continue
        h = by_file.get(path.name, {})
        if m["ts"]:
            when = datetime.strptime(m["ts"], "%Y%m%d-%H%M%S")
        else:
            when = datetime.fromtimestamp(path.stat().st_mtime)
        score = h.get("score")
        if score is None:
            found = _SCORE.search(path.read_text(encoding="utf-8"))
            score = float(found.group(1)) if found else float("nan")
        rows.append({"time": when, "case": m["id"], "type": case_type, "domain": library()["cases"][case_type]["domain"],
                     "level": level, "score": float(score), "file": path.name, "path": str(path)})
    cols = ["time", "case", "type", "domain", "level", "score", "file", "path"]
    return pd.DataFrame(rows, columns=cols).sort_values("time", ascending=False, ignore_index=True)


def search_reports(reports: pd.DataFrame, text: str) -> pd.DataFrame:
    """Reports whose Markdown contains the text (case-insensitive)."""
    text = (text or "").strip().lower()
    if not text or reports.empty:
        return reports
    hit = [text in Path(p).read_text(encoding="utf-8").lower() for p in reports["path"]]
    return reports[hit]


QUESTIONS = ("cause", "action", "decision", "notify")


def study_profile(hist: pd.DataFrame) -> dict:
    """Cross study of all attempts: where the points are lost.

    by_domain / by_type: attempts and mean score (types never tried are listed with 0 attempts);
    by_question: accuracy per question per domain (attempts saved with detail only);
    missed_roles / extra_roles, wrong answers (chosen option per correct one) and message points missed most."""
    from collections import Counter

    lib = library()
    hist = hist.copy() if hist is not None else pd.DataFrame()
    types = pd.DataFrame([{"type": k, "domain": c["domain"]} for k, c in lib["cases"].items()])
    if len(hist):
        g = hist.groupby("type")["score"]
        types = types.merge(g.agg(attempts="count", mean="mean").reset_index(), on="type", how="left")
        last = hist.groupby("type")["score"].apply(lambda s_: s_.tail(3).mean()).rename("recent")
        types = types.merge(last.reset_index(), on="type", how="left")
        lvl = hist.groupby("type")["level"].last().rename("last_level")
        types = types.merge(lvl.reset_index(), on="type", how="left")
    for c in ("attempts", "mean", "recent", "last_level"):
        if c not in types:
            types[c] = None
    types["attempts"] = types["attempts"].fillna(0).astype(int)
    by_domain = types.groupby("domain").apply(
        lambda d: pd.Series({"attempts": int(d["attempts"].sum()),
                             "mean": (d["mean"] * d["attempts"]).sum() / d["attempts"].sum() if d["attempts"].sum() else None,
                             "tried": int((d["attempts"] > 0).sum()), "types": len(d)}), include_groups=False)
    detail = hist[hist["cause_ok"].notna()] if "cause_ok" in hist else hist.iloc[0:0]
    if len(detail):
        acc = detail.assign(cause=detail["cause_ok"].astype(float), action=detail["action_ok"].astype(float),
                            decision=detail["decision_ok"].astype(float), notify=detail["notify_pts"].astype(float))
        by_question = acc.groupby("domain")[list(QUESTIONS)].mean() * 100
        by_question.loc["all"] = acc[list(QUESTIONS)].mean() * 100
    else:
        by_question = pd.DataFrame(columns=list(QUESTIONS))
    missed, extra, wrong, msg = Counter(), Counter(), Counter(), Counter()
    for r in detail.to_dict("records"):
        missed.update(r.get("missing") or [])
        extra.update(r.get("extra") or [])
        spec = lib["cases"].get(r["type"], {})
        for q, (model, chosen) in (r.get("wrong") or {}).items():
            wrong[(q, model, chosen)] += 1
        for i in r.get("msg_missed") or []:
            if i < len(spec.get("keypoints", [])):
                msg[(r["type"], i)] += 1
    return {"by_type": types, "by_domain": by_domain, "by_question": by_question, "n_detail": len(detail),
            "missed_roles": missed, "extra_roles": extra, "wrong": wrong, "msg_missed": msg}


def focus_weights(profile: dict) -> pd.Series:
    """How often each case type should come up when practising weak spots: types with low recent scores most,
    other types in a weak area next, types never tried after that, mastered types (recent score near 100) rarely."""
    t = profile["by_type"].set_index("type")
    recent = t["recent"].astype(float)
    w = (3.0 * (1.0 - recent / 100.0)).clip(lower=0.05)
    w[t["attempts"] == 0] = 0.35
    dom_mean = profile["by_domain"]["mean"].astype(float)
    boost = t["domain"].map(1.0 + (1.0 - dom_mean / 100.0)).fillna(1.0)  # untried area: no boost
    w = w * boost
    return w / w.sum()


def focus_level(profile: dict, case_type: str) -> str:
    """Step up a level after a good recent score (>= 85), down after a poor one (< 50)."""
    t = profile["by_type"].set_index("type").loc[case_type]
    if not t["attempts"] or not isinstance(t["last_level"], str):
        return "basic"
    i = LEVELS.index(t["last_level"])
    if t["recent"] >= 85:
        i = min(i + 1, len(LEVELS) - 1)
    elif t["recent"] < 50:
        i = max(i - 1, 0)
    return LEVELS[i]


def focus_case(hist: pd.DataFrame, seed: int | None = None, level: str | None = None) -> Case:
    """A random case aimed at your weak spots (see focus_weights / focus_level)."""
    rng = np.random.default_rng(seed)
    prof = study_profile(hist)
    w = focus_weights(prof)
    case_type = str(rng.choice(w.index.to_numpy(), p=w.to_numpy()))
    return generate(make_id(case_type, level or focus_level(prof, case_type), int(rng.integers(0, 100000))))
