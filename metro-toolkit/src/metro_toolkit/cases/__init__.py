"""Case study practice: random, realistic Metro AE situations with one known cause, scored answers and a debrief.

A case ID such as ``spc_chamber_shift-I-04217`` (type, level B/I/A, seed) always regenerates the same case.
Texts (brief, options, explanation, model message, message checklist) live in cases.yaml; data comes from
generators.py, which reuses the toolkit's simulators so the charts are the same as on the other pages.
"""

from __future__ import annotations

import json
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


def report_markdown(case: Case, answers: dict, result: dict, message: str, lang: str = "zh") -> str:
    """A study-log entry: brief, your answers vs the model answers, explanation, messages, checklist."""
    L = (lambda zh, en: zh if lang == "zh" else en)
    q_name = {"cause": L("根本原因", "Root cause"), "action": L("第一步處置", "First action"),
              "decision": L("產品／結論處置", "Disposition / decision")}
    lines = [f"# {L('案例', 'Case')} {case.id}: {case.text('title', lang)}", "",
             f"*{datetime.now():%Y-%m-%d %H:%M}* · {L('難度', 'Level')} {case.level} · "
             f"{L('分數', 'Score')} **{result['total']:.0f} / 100**", "",
             f"## {L('狀況', 'Situation')}", "", case.text("brief", lang), "", f"## {L('你的判斷 vs 標準答案', 'Your answers vs the model answers')}", ""]
    for q in ("cause", "action", "decision"):
        r = result["questions"][q]
        mine = case.option_text(q, r["answer"], lang) if r["answer"] else "—"
        lines.append(f"- **{q_name[q]}** {'✓' if r['ok'] else '✗'} {L('你', 'You')}: {mine}" +
                     ("" if r["ok"] else f"  \n  {L('標準答案', 'Model answer')}: {case.option_text(q, r['correct'], lang)}"))
    n = result["questions"]["notify"]
    lines.append(f"- **{L('通知對象', 'Who to notify')}** {'✓' if n['ok'] else '△'} "
                 f"{L('應通知', 'Should notify')}: {', '.join(role_name(r, lang) for r in n['correct']) or L('不需升級（e-log 記錄即可）', 'no escalation (e-log only)')}"
                 + (f"; {L('漏了', 'missed')}: {', '.join(role_name(r, lang) for r in n['missing'])}" if n["missing"] else "")
                 + (f"; {L('多了', 'extra')}: {', '.join(role_name(r, lang) for r in n['extra'])}" if n["extra"] else ""))
    lines += ["", f"## {L('為什麼', 'Why')}", "", case.text("explanation", lang), "",
              f"## {L('給', 'Message to')} {role_name(case.spec['message_role'], lang)}", "",
              f"**{L('你寫的', 'Yours')}**", "", f"> {message.strip() or '—'}", "",
              f"**{L('範例', 'Model message')}**", "", f"> {case.text('model_message', lang)}", ""]
    for item, ok in message_checklist(case, message, lang):
        lines.append(f"- {'✓' if ok else '✗'} {item}")
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


def save_attempt(case: Case, result: dict, md: str, folder: Path | None = None) -> Path:
    folder = cases_dir(folder)
    path = folder / f"{case.id}.md"
    path.write_text(md, encoding="utf-8")
    with open(folder / "history.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"time": f"{datetime.now():%Y-%m-%d %H:%M}", "case": case.id, "type": case.type,
                             "domain": case.spec["domain"], "level": case.level, "score": result["total"]},
                            ensure_ascii=False) + "\n")
    return path


def history(folder: Path | None = None) -> pd.DataFrame:
    path = cases_dir(folder) / "history.jsonl"
    if not path.exists():
        return pd.DataFrame(columns=["time", "case", "type", "domain", "level", "score"])
    return pd.DataFrame([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])
