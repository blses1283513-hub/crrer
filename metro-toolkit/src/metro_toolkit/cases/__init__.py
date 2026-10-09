"""Case study practice: random, realistic Metro AE situations with known causes, scored answers and a debrief.

A case ID ``<type>-<level B/I/A>-<seed>`` always regenerates the same case. Types:
  * the case types in cases.yaml (texts) + generators.py (data), e.g. ``spc_chamber_shift-I-04217``;
  * ``mix``: a random multi-issue case (compose.py), e.g. ``mix-A-00042``;
  * ``build_<hash>``: a case made in the case builder; its settings are saved on this PC (data/cases/built/);
  * ``my_<name>``: your own case template, saved on this PC (data/cases/custom/, custom.py).
Every case carries a list of questions (single choice, multiple choice or roles to notify), so scoring, the
answer form, the debrief, the saved report and the cross study work the same way for all of them.
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
CATEGORY_POOL = {"cause": "causes", "action": "actions", "decision": "decisions"}
QUESTION_LABEL = {"cause": {"zh": "根本原因", "en": "Root cause"}, "action": {"zh": "第一步處置", "en": "First action"},
                  "decision": {"zh": "產品／結論處置", "en": "Disposition / decision"},
                  "notify": {"zh": "通知對象", "en": "Who to notify"}, "priority": {"zh": "先處理哪一個", "en": "Handle first"},
                  "causes": {"zh": "有哪些原因（可複選）", "en": "Which causes are present (select all)"}}
QUESTION_PROMPT = {"cause": {"zh": "根本原因最可能是？", "en": "Most likely root cause?"},
                   "action": {"zh": "第一步要做什麼？", "en": "First action?"},
                   "decision": {"zh": "產品／結論怎麼處置？", "en": "Disposition / decision?"},
                   "notify": {"zh": "要通知誰？（可複選；不需升級就不選）", "en": "Who to notify? (none = e-log only)"}}


@lru_cache(maxsize=None)
def library() -> dict:
    return yaml.safe_load((HERE / "cases.yaml").read_text(encoding="utf-8"))


def custom_types() -> dict:
    """Your own case templates (my_<name>) as library-style entries; read fresh so edits show at once."""
    from .custom import load_templates

    return load_templates()


def case_types(domain: str | None = None) -> list[str]:
    """Single-situation case types (built in + your own templates), optionally of one domain."""
    out = [k for k, c in library()["cases"].items() if domain in (None, c["domain"])]
    if domain in (None, "custom"):
        out += list(custom_types())
    return out


def type_info(case_type: str) -> dict:
    """domain and title of any case type, including mixes, built cases and your own templates."""
    if case_type in library()["cases"]:
        c = library()["cases"][case_type]
        return {"domain": c["domain"], "title": c["title"]}
    if case_type == "mix":
        return {"domain": "mix", "title": {"zh": "多重問題（隨機組合）", "en": "Multi-issue (random mix)"}}
    if case_type.startswith("build_"):
        return {"domain": "mix", "title": {"zh": "自建案例", "en": "Built case"}}
    if case_type.startswith("my_"):
        t = custom_types().get(case_type)
        return {"domain": "custom", "title": t["title"] if t else {"zh": case_type, "en": case_type}}
    return {"domain": "?", "title": {"zh": case_type, "en": case_type}}


def make_id(case_type: str, level: str, seed: int) -> str:
    return f"{case_type}-{LEVEL_CODE[level]}-{seed:05d}"


def known_type(case_type: str) -> bool:
    if case_type in library()["cases"] or case_type == "mix":
        return True
    if case_type.startswith("build_"):
        from .compose import built_path

        return built_path(case_type).exists()
    return case_type.startswith("my_") and case_type in custom_types()


def parse_id(case_id: str) -> tuple[str, str, int]:
    case_type, code, seed = case_id.strip().rsplit("-", 2)
    level = {v: k for k, v in LEVEL_CODE.items()}[code.upper()]
    if not known_type(case_type):
        raise ValueError(f"unknown case type {case_type}")
    return case_type, level, int(seed)


def option_label(question: str, option: str, lang: str) -> str:
    """Text of a pool answer option (cause / action / decision) in one language."""
    return library()["pools"][CATEGORY_POOL[question]][option][lang]


@dataclass
class Question:
    """One question of a case. kind: single (one choice) | multi (select all that apply) | roles (who to notify).
    correct: an option id, or a list of accepted ids for single; the list of right options for multi / roles.
    category (cause | action | decision | priority | notify) groups questions in the cross study."""

    key: str
    kind: str
    category: str
    label: dict
    options: list
    correct: object
    weight: float
    labels: dict = field(default_factory=dict)  # option id -> {zh, en} for options that are not in a pool
    group: dict | None = None  # heading {zh, en}: the problem this question belongs to (multi-problem handovers)
    prompt: dict | None = None  # the question as asked in the form

    def accepted(self) -> list:
        return list(self.correct) if isinstance(self.correct, (list, tuple)) else [self.correct]

    def option_text(self, option, lang: str) -> str:
        if option in self.labels:
            return self.labels[option][lang]
        if self.kind == "roles":
            return role_name(option, lang)
        pool = library()["pools"].get(CATEGORY_POOL.get(self.category, ""), {})
        return pool[option][lang] if option in pool else str(option)


def standard_questions(correct: dict, options: dict, labels: dict | None = None) -> list[Question]:
    """The four questions of a single-situation case: cause, action, decision (one choice each) and who to notify."""
    labels = labels or {}
    qs = [Question(q, "single", q, QUESTION_LABEL[q], options[q], correct[q], WEIGHTS[q],
                   {o: labels[o] for o in options[q] if o in labels}, prompt=QUESTION_PROMPT[q])
          for q in ("cause", "action", "decision")]
    qs.append(Question("notify", "roles", "notify", QUESTION_LABEL["notify"], list(meta()["roles"]),
                       list(correct.get("notify", [])), WEIGHTS["notify"], prompt=QUESTION_PROMPT["notify"]))
    return qs


@dataclass
class Case:
    id: str
    type: str
    level: str
    spec: dict  # the cases.yaml entry (or the composed / template texts)
    v: dict
    evidence: list
    guide: list
    correct: dict  # question key -> correct option(s)
    options: dict = field(default_factory=dict)  # question key -> option ids in display order
    questions: list = field(default_factory=list)

    @property
    def facts(self) -> Facts:
        return Facts(v=self.v)

    def text(self, key: str, lang: str) -> str:
        entry = self.spec.get(key)
        return fill(entry.get(lang), self.facts, lang) if entry else ""

    def question(self, key: str) -> Question | None:
        return next((q for q in self.questions if q.key == key), None)

    def option_text(self, question: str, option: str, lang: str) -> str:
        q = self.question(question)
        return q.option_text(option, lang) if q else option_label(question, option, lang)


def shuffled_options(spec: dict, correct: dict, seed: int) -> dict:
    order = np.random.default_rng(seed + 1)
    options = {}
    for q in ("cause", "action", "decision"):
        ids = list(dict.fromkeys(spec[f"{q}_options"] + [correct[q]]))
        options[q] = [ids[i] for i in order.permutation(len(ids))]
    return options


def generate(case_id: str) -> Case:
    case_type, level, seed = parse_id(case_id)
    if case_type == "mix" or case_type.startswith("build_"):
        from .compose import generate_composite

        return generate_composite(case_id, case_type, level, seed)
    if case_type.startswith("my_"):
        from .custom import generate_custom

        return generate_custom(case_id, case_type, level, seed)
    spec = library()["cases"][case_type]
    out = GENERATORS[case_type](np.random.default_rng(seed), level)
    correct = {"cause": spec["cause"], "action": spec["action"], "decision": spec["decision"],
               "notify": list(spec.get("notify", []))}
    correct.update(out.get("answer", {}))
    options = shuffled_options(spec, correct, seed)
    return Case(case_id, case_type, level, spec, out["v"], out["evidence"], out["guide"], correct, options,
                standard_questions(correct, options))


def random_id(seed: int | None = None, domain: str | None = None, level: str | None = None) -> str:
    """ID of a random single-situation case (cheap: the case is generated only when it is opened)."""
    rng = np.random.default_rng(seed)
    types = case_types(domain)
    case_type = types[int(rng.integers(len(types)))]
    level = level or LEVELS[int(rng.integers(3))]
    return make_id(case_type, level, int(rng.integers(0, 100000)))


def random_case(seed: int | None = None, domain: str | None = None, level: str | None = None) -> Case:
    return generate(random_id(seed, domain, level))


def mix_id(seed: int | None = None, level: str | None = None) -> str:
    """ID of a random multi-issue case (linked or separate, decided by the seed)."""
    rng = np.random.default_rng(seed)
    level = level or LEVELS[int(rng.integers(3))]
    return make_id("mix", level, int(rng.integers(0, 100000)))


def score(case: Case, answers: dict) -> dict:
    """answers: question key -> option id (single) or list (multi / roles)."""
    rows, total = {}, 0.0
    for q in case.questions:
        a = answers.get(q.key)
        if q.kind == "single":
            ok = a is not None and a in q.accepted()
            pts = q.weight if ok else 0
            rows[q.key] = {"ok": ok, "points": pts, "max": q.weight, "answer": a, "correct": q.accepted()[0],
                           "accepted": q.accepted(), "category": q.category, "kind": q.kind}
        else:
            mine, right = set(a or []), set(q.correct)
            jac = 1.0 if not mine and not right else len(mine & right) / len(mine | right)
            pts = round(q.weight * jac, 1)
            rows[q.key] = {"ok": jac == 1.0, "points": pts, "max": q.weight, "answer": sorted(mine),
                           "missing": sorted(right - mine), "extra": sorted(mine - right), "correct": sorted(right),
                           "category": q.category, "kind": q.kind}
        total += pts
    return {"questions": rows, "total": round(total, 1)}


def message_checklist(case: Case, message: str, lang: str) -> list[tuple[str, bool]]:
    """Which key points of a good message the free text covers (case-insensitive keyword match).
    A key point with ``order`` (token lists, one per problem) and ``top`` (indices) is met when the problem the message
    mentions first is one of the most urgent ones."""
    text = (message or "").lower()
    fmt = library().get("formats", {}).get(case.spec.get("message_format") or "")
    for sec in (fmt or {}).get("sections", []):  # the pre-filled bracketed headings do not count as content
        for label in (f"{sec['zh']} {sec['en']}", sec["zh"], sec["en"]):
            for wrap in ("【{}】", "[{}]"):
                text = text.replace(wrap.format(label).lower(), " ")
    out = []
    for kp in case.spec.get("keypoints", []):
        if "order" in kp:
            first = []
            for i, toks in enumerate(kp["order"]):
                hits = [text.find(t.lower()) for t in toks if t]
                hits = [h for h in hits if h >= 0]
                if hits:
                    first.append((min(hits), i))
            out.append((kp[lang], bool(first) and min(first)[1] in kp["top"]))
            continue
        tokens = [fill(t, case.facts, lang).lower() for t in kp.get("any", [])]
        ok = any(t and t != "—" and t in text for t in tokens)
        out.append((kp[lang], ok))
    return out


def message_template(case: Case, langs: list[str]) -> str:
    """The answer box pre-filled with the headings of the case's report format (empty if it has none)."""
    fmt = library().get("formats", {}).get(case.spec.get("message_format") or "")
    if not fmt:
        return ""
    heads = [" ".join(sec[lg] for lg in langs) for sec in fmt["sections"]]
    return "\n\n".join(f"【{h}】" for h in heads) + "\n"


def role_name(role: str, lang: str) -> str:
    return meta()["roles"][role][lang]


def report_markdown(case: Case, answers: dict, result: dict, message: str, lang: str = "zh",
                    past: pd.DataFrame | None = None) -> str:
    """A study-log entry: situation, your answers vs the model answers, why, your message vs the model message,
    what a good message covers, score history (``past`` = earlier attempts) and, for every evidence chart, the
    insight, the next step and a ready message for every role. ``lang``: "zh", "en" or "both"."""
    from ..guide import STATUSES, charts, text

    langs = ["zh", "en"] if lang == "both" else [lang]
    L = (lambda zh, en: f"{zh} · {en}" if lang == "both" else (zh if lang == "zh" else en))  # headings
    B = (lambda f: "\n\n".join(f(lg) for lg in langs))  # one block per language

    status = meta()["status"]
    names = (lambda roles: ", ".join(" / ".join(role_name(r, lg) for lg in langs) for r in roles))
    lines = [f"# {L('案例', 'Case')} {case.id}: {B(lambda lg: case.text('title', lg)).replace(chr(10) * 2, ' · ')}", "",
             f"*{datetime.now():%Y-%m-%d %H:%M}* · {L('難度', 'Level')} {case.level} · "
             f"{L('分數', 'Score')} **{result['total']:.0f} / 100**", "",
             f"## {L('狀況', 'Situation')}", "", B(lambda lg: case.text("brief", lg)), "",
             f"## {L('你的判斷 vs 標準答案', 'Your answers vs the model answers')}", ""]
    group = None
    for q in case.questions:
        r = result["questions"][q.key]
        if q.group and q.group != group:
            group = q.group
            lines += ["", f"**{' / '.join(q.group[lg] for lg in langs)}**", ""]
        head = f"- **{' / '.join(q.label[lg] for lg in langs)}**"
        if q.kind == "single":
            mine = " / ".join(q.option_text(r["answer"], lg) for lg in langs) if r["answer"] else "—"
            model = " / ".join(q.option_text(r["correct"], lg) for lg in langs)
            lines.append(f"{head} {'✓' if r['ok'] else '✗'} {L('你', 'You')}: {mine}"
                         + ("" if r["ok"] else f"  \n  {L('標準答案', 'Model answer')}: {model}"))
        else:
            txt = (lambda opts: ", ".join(" / ".join(q.option_text(o, lg) for lg in langs) for o in opts))
            none = L("不需升級（e-log 記錄即可）", "no escalation (e-log only)") if q.kind == "roles" else "—"
            lines.append(f"{head} {'✓' if r['ok'] else '△'} {L('應選', 'Should be')}: {txt(r['correct']) or none}"
                         + (f"; {L('漏了', 'missed')}: {txt(r['missing'])}" if r["missing"] else "")
                         + (f"; {L('多了', 'extra')}: {txt(r['extra'])}" if r["extra"] else ""))
    quote = (lambda t: "\n".join(f"> {ln}" if ln.strip() else ">" for ln in t.strip().splitlines()) or "> —")
    target = case.spec["message_role"]
    lines += ["", f"## {L('為什麼', 'Why')}", "", B(lambda lg: case.text("explanation", lg)), "",
              f"## {L('給', 'Message to')} {names([target])}", "",
              f"**{L('你寫的', 'Yours')}**", "", quote(message or ""), "",
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
    """Per-question results kept in the study log, for the cross study of all your attempts.
    cat: share of points per category (cause / action / decision / priority / notify); missing / extra: roles;
    wrong: {question: [model, yours, category]} for pool options; msg_missed: message points not covered."""
    cat, missing, extra, wrong = {}, [], [], {}
    for q in case.questions:
        r = result["questions"][q.key]
        got, mx = cat.get(q.category, (0.0, 0.0))
        cat[q.category] = (got + r["points"], mx + r["max"])
        if q.kind == "roles":
            missing += r["missing"]
            extra += r["extra"]
        elif q.kind == "single" and not r["ok"] and r["answer"] and q.category in CATEGORY_POOL \
                and r["answer"] not in q.labels and r["correct"] not in q.labels:
            wrong[q.key] = [r["correct"], r["answer"], q.category]
    checklist = zip(message_checklist(case, message, "zh"), message_checklist(case, message, "en"))
    return {"cat": {k: round(g / m, 3) for k, (g, m) in cat.items() if m}, "missing": missing, "extra": extra,
            "wrong": wrong, "msg_missed": [{"zh": z[0], "en": e[0]} for z, e in checklist if not e[1]]}


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
_REPORT = re.compile(r"^(?P<id>[a-z0-9_]+-[BIA]-\d{5})(?:_(?P<ts>\d{8}-\d{6})(?:-\d+)?)?\.md$")
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
        rows.append({"time": when, "case": m["id"], "type": case_type, "domain": type_info(case_type)["domain"],
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


QUESTIONS = ("cause", "action", "decision", "priority", "notify")


def _row_cats(r: dict) -> dict | None:
    """Per-category score share of one log line (older lines stored cause_ok / action_ok / ... instead)."""
    if isinstance(r.get("cat"), dict):
        return r["cat"]
    if r.get("cause_ok") is None or (isinstance(r.get("cause_ok"), float) and np.isnan(r["cause_ok"])):
        return None
    return {"cause": float(r["cause_ok"]), "action": float(r["action_ok"]), "decision": float(r["decision_ok"]),
            "notify": float(r["notify_pts"])}


def _row_msg_missed(r: dict) -> list[dict]:
    items = r.get("msg_missed") or []
    out = []
    for it in items:
        if isinstance(it, dict):
            out.append(it)
        else:  # older lines: index into the case type's keypoints
            kps = library()["cases"].get(r.get("type"), {}).get("keypoints", [])
            if isinstance(it, int) and it < len(kps):
                out.append({"zh": kps[it]["zh"], "en": kps[it]["en"]})
    return out


def study_profile(hist: pd.DataFrame) -> dict:
    """Cross study of all attempts: where the points are lost.

    by_type: attempts, mean and recent score per single-situation case type (types never tried: 0 attempts);
    by_domain: attempts and mean per area (multi-issue cases count as "mix", your own templates as "custom");
    by_question: score share per question category per area (attempts saved with detail only);
    missed_roles / extra_roles, wrong answers (chosen option per model answer) and message points missed most."""
    from collections import Counter

    lib = library()
    hist = hist.copy() if hist is not None else pd.DataFrame()
    types = pd.DataFrame([{"type": k, "domain": type_info(k)["domain"]} for k in case_types()])
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
    domains = list(lib["domains"])
    rows = []
    for d in domains:
        t = types[types["domain"] == d]
        h = hist[hist["domain"] == d] if len(hist) else hist
        if d in ("mix", "custom") and not len(h) and not len(t):
            continue
        rows.append({"domain": d, "attempts": len(h), "mean": float(h["score"].mean()) if len(h) else None,
                     "tried": int((t["attempts"] > 0).sum()), "types": len(t)})
    by_domain = pd.DataFrame(rows).set_index("domain")
    recs = hist.to_dict("records") if len(hist) else []
    detail = [(r, _row_cats(r)) for r in recs]
    detail = [(r, c) for r, c in detail if c]
    if detail:
        acc = pd.DataFrame([{"domain": r["domain"], **{k: c.get(k) for k in QUESTIONS}} for r, c in detail])
        acc[list(QUESTIONS)] = acc[list(QUESTIONS)].astype(float)
        by_question = acc.groupby("domain")[list(QUESTIONS)].mean() * 100
        by_question.loc["all"] = acc[list(QUESTIONS)].mean() * 100
        by_question = by_question.dropna(axis=1, how="all")
    else:
        by_question = pd.DataFrame(columns=list(QUESTIONS))
    missed, extra, wrong, msg = Counter(), Counter(), Counter(), Counter()
    for r, _ in detail:
        missed.update(r.get("missing") or [])
        extra.update(r.get("extra") or [])
        for q, val in (r.get("wrong") or {}).items():
            model, chosen = val[0], val[1]
            wrong[(val[2] if len(val) > 2 else q, model, chosen)] += 1
        for it in _row_msg_missed(r):
            msg[(r.get("type"), it["zh"], it["en"])] += 1
    return {"by_type": types, "by_domain": by_domain, "by_question": by_question, "n_detail": len(detail),
            "missed_roles": missed, "extra_roles": extra, "wrong": wrong, "msg_missed": msg}


UNTRIED_POOL = 4.5  # total weight of the types in never-tried areas (0.35 each for up to 13 of them)


def focus_weights(profile: dict) -> pd.Series:
    """How often each case type should come up when practising weak spots: types with low recent scores most,
    other types in a weak area next, types never tried after that, mastered types (recent score near 100) rarely.
    Types in areas you have never tried share at most UNTRIED_POOL of weight between them, so new areas added to the
    library do not crowd out your weak areas."""
    t = profile["by_type"].set_index("type")
    recent = t["recent"].astype(float)
    w = (3.0 * (1.0 - recent / 100.0)).clip(lower=0.05)
    untried = t["attempts"] == 0
    tried_dom = set(t.loc[~untried, "domain"])
    new_area = untried & ~t["domain"].isin(tried_dom)
    w[untried] = 0.35
    w[new_area] = min(0.35, UNTRIED_POOL / max(int(new_area.sum()), 1))
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


def focus_id(hist: pd.DataFrame, seed: int | None = None, level: str | None = None) -> str:
    """ID of a random case aimed at your weak spots (see focus_weights / focus_level)."""
    rng = np.random.default_rng(seed)
    prof = study_profile(hist)
    w = focus_weights(prof)
    case_type = str(rng.choice(w.index.to_numpy(), p=w.to_numpy()))
    return make_id(case_type, level or focus_level(prof, case_type), int(rng.integers(0, 100000)))


def focus_case(hist: pd.DataFrame, seed: int | None = None, level: str | None = None) -> Case:
    return generate(focus_id(hist, seed, level))
