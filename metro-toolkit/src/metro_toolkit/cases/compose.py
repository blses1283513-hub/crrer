"""Multi-issue cases: several problems at once, as on a real shift.

* linked: 1-3 issues from issues.yaml injected into ONE fab-simulator run, so they share the SPC charts, the yield
  trend and the die maps and can hide each other (e.g. a real chamber shift under a metrology-tool offset).
  Questions: which causes are present (select all), the most urgent first action, which issue to handle first,
  the disposition, who to notify, and one message.
* separate: 2-3 unrelated single-situation cases in one handover. Questions: cause / action / decision for each
  problem, which to handle first, who to notify, and a handover summary.

``mix-<L>-<seed>`` draws a random linked or separate case from the seed; ``build_<hash>-<L>-00000`` replays the
settings you chose in the case builder (saved on this PC in data/cases/built/<type>.json).
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

from ..analysis import wafer_summary
from ..guide import Facts, fill
from . import (QUESTION_LABEL, QUESTION_PROMPT, Case, Question, case_types, cases_dir, generate, library,
               make_id, role_name, type_info)
from .generators import _fab, _fab_yield, _spc_evidence

HERE = Path(__file__).resolve().parent
SIZES = ("small", "medium", "large")
SIZE_BY_LEVEL = {"basic": ("large",), "intermediate": ("medium", "large"), "advanced": ("small", "medium")}
URGENCY_BY_DECISION = {"D_HOLD": 3, "D_ROUTE_REF": 3, "D_NO_CONVERT": 2, "D_GAUGE_NOT_OK": 2, "D_RECIPE_FIX": 2,
                       "D_REMEASURE_RELEASE": 2, "D_RELEASE_WATCH": 2, "D_NO_HOLD_COUNTS": 2, "D_CONFIRM_SOURCE": 2,
                       "D_SPLIT_CONFIRM": 2, "D_RETARGET": 1, "D_RECIPE_NOT_READY": 1, "D_MODEL_NOT_READY": 1,
                       "D_RECIPE_OK": 1, "D_GAUGE_OK": 1, "D_RELEASE": 1, "D_RELEASE_PROCESS": 1, "D_NO_METRO_ACTION": 1}
URGENCY_TEXT = {3: {"zh": "產品正在受影響，要先止血（hold／隔離）", "en": "product is at risk right now, so contain it first (hold / isolate)"},
                2: {"zh": "今天要處理，但產品沒有立即風險", "en": "it needs action today, but product is not at immediate risk"},
                1: {"zh": "可以排程處理，不影響產品", "en": "it can be scheduled; product is not affected"}}
STAT_NAME = {"mean": "wafer mean 晶圓平均", "nu_1sigma_pct": "1σ % 片內不均勻度"}
GROUP_NAME = {"chamber_id": "依 chamber 分組 · by chamber", "metro_tool_id": "依量測機台分組 · by metrology tool"}


@lru_cache(maxsize=None)
def issue_kinds() -> dict:
    return yaml.safe_load((HERE / "issues.yaml").read_text(encoding="utf-8"))["kinds"]


@lru_cache(maxsize=None)
def _fab_cfg() -> dict:
    from ..datagen.fab import load_fab_config

    return load_fab_config()


def step_info(step: str) -> dict:
    return next(s for s in _fab_cfg()["steps"] if s["name"] == step)


def where_choices(kind: str, step: str) -> list[str]:
    k, cfg = issue_kinds()[kind], _fab_cfg()
    if k["where"] == "all":
        return ["all"]
    if k["where"] == "metro":
        return list(cfg["metro_tools"])
    if k["where"] == "tool":
        return list(step_info(cfg["defects"]["inspection_step"])["tools"])
    s = step_info(step)
    return [f"{t}-{chr(65 + c)}" for t, n in s["tools"].items() for c in range(n)]


def urgency_of(case: Case) -> int:
    """3 / 2 / 1. When the data changed the right decision (e.g. "not the cause" -> release), it follows that decision."""
    decision = case.correct.get("decision")
    if decision != case.spec.get("decision") and decision in URGENCY_BY_DECISION:
        return URGENCY_BY_DECISION[decision]
    return int(case.spec.get("urgency") or URGENCY_BY_DECISION.get(decision, 2))


@lru_cache(maxsize=32)
def _sub_case(case_id: str) -> Case:
    return generate(case_id)


def _sub_ids(types: list[str], level: str, seed: int) -> list[str]:
    return [make_id(t, level, (seed * 7 + 131 * (i + 1)) % 100000) for i, t in enumerate(types)]


def built_path(case_type: str) -> Path:
    return cases_dir() / "built" / f"{case_type}.json"


def save_settings(settings: dict) -> str:
    """Store builder settings on this PC; returns the case type (build_<hash>) that replays them."""
    raw = json.dumps(settings, sort_keys=True, ensure_ascii=False)
    case_type = "build_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    path = built_path(case_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw, encoding="utf-8")
    return case_type


def validate_settings(settings: dict) -> None:
    if settings.get("mode") == "linked":
        issues = settings.get("issues") or []
        if not 1 <= len(issues) <= 3:
            raise ValueError("a linked case has 1-3 issues")
        for it in issues:
            if it["kind"] not in issue_kinds():
                raise ValueError(f"unknown issue kind {it['kind']}")
            if it["step"] not in issue_kinds()[it["kind"]]["steps"]:
                raise ValueError(f"{it['kind']} cannot be put on {it['step']}")
            if it["where"] not in where_choices(it["kind"], it["step"]):
                raise ValueError(f"{it['where']} is not a valid place for {it['kind']} on {it['step']}")
            if it["size"] not in SIZES:
                raise ValueError(f"size must be one of {SIZES}")
    elif settings.get("mode") == "separate":
        types = settings.get("types") or []
        if not 2 <= len(types) <= 3:
            raise ValueError("a separate case has 2-3 problems")
        unknown = [t for t in types if t not in case_types()]
        if unknown:
            raise ValueError(f"unknown case types {unknown}")
    else:
        raise ValueError("mode must be linked or separate")


# --------------------------------------------------------------------------- random mixes
def random_settings(level: str, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    kinds = issue_kinds()
    if rng.random() < 0.55:
        n = 3 if level == "advanced" and rng.random() < 0.5 else 2
        names = list(kinds)
        for _ in range(100):  # one clearly most urgent issue, so "handle first" has one answer
            pick = [str(k) for k in rng.choice(names, n, replace=False)]
            urg = sorted((kinds[k]["urgency"] for k in pick), reverse=True)
            if urg[0] > urg[1]:
                break
        issues, used = [], set()
        for k in pick:
            for _ in range(20):
                step = str(rng.choice(kinds[k]["steps"]))
                where = str(rng.choice(where_choices(k, step)))
                if (step, where) not in used or kinds[k]["where"] == "metro":
                    break
            used.add((step, where))
            issues.append({"kind": k, "step": step, "where": where, "size": str(rng.choice(SIZE_BY_LEVEL[level])),
                           "start_lot": int(rng.integers(14, 30)), "sign": int(rng.choice([-1, 1]))})
        return {"mode": "linked", "issues": issues}
    types = [t for t in library()["cases"]]
    n = 3 if level == "advanced" and rng.random() < 0.5 else 2
    for _ in range(100):  # different areas, at most one slow fab case, and one clearly most urgent item
        pick = [str(t) for t in rng.choice(types, n, replace=False)]
        doms = {library()["cases"][t]["domain"] for t in pick}
        if len(doms) < n or sum(t.startswith("fab_") for t in pick) > 1:
            continue
        urg = sorted((urgency_of(_sub_case(i)) for i in _sub_ids(pick, level, seed)), reverse=True)
        if urg[0] > urg[1]:
            break
    return {"mode": "separate", "types": pick}


def generate_composite(case_id: str, case_type: str, level: str, seed: int) -> Case:
    if case_type == "mix":
        settings = random_settings(level, seed)
    else:
        settings = json.loads(built_path(case_type).read_text(encoding="utf-8"))
    validate_settings(settings)
    if settings["mode"] == "linked":
        return linked_case(case_id, case_type, level, seed, settings["issues"])
    return separate_case(case_id, case_type, level, seed, settings["types"])


# --------------------------------------------------------------------------- linked: one fab run, several issues
def make_event(issue: dict) -> tuple[dict, float]:
    """The fab-simulator event for one issue, and its size in the parameter's unit (for the texts)."""
    k = issue_kinds()[issue["kind"]]
    s = step_info(issue["step"])
    mult = k["size"][issue["size"]]
    sign = float(issue.get("sign", 1))
    ev = {"type": k["event"], "step": issue["step"], "where": issue["where"], "start_lot": int(issue["start_lot"]),
          "n_lots": int(k["n_lots"])}
    if k["event"] in ("shift", "recipe", "metro_offset"):
        ev["magnitude"] = sign * mult * s["sigma_wafer"]
        shown = abs(ev["magnitude"])
    elif k["event"] == "drift":
        ev["magnitude"] = sign * mult * s["sigma_wafer"] / k["n_lots"]
        shown = mult * s["sigma_wafer"]
    elif k["event"] == "bowl":
        ev["magnitude"] = mult * s["sigma_local"]
        shown = ev["magnitude"]
    else:  # defects
        ev["magnitude"] = mult
        ev["pattern"] = k.get("pattern", "edge_ring")
        shown = mult
    return ev, float(np.round(shown, 4))


def _spc_view(res, param: str, group: str, stat: str, chart: str):
    sub = res.long[res.long.parameter == param]
    wafers = wafer_summary(sub)
    lsl = usl = None
    if stat == "mean" and sub.lsl.notna().any():
        lsl, usl = float(sub.lsl.dropna().median()), float(sub.usl.dropna().median())
    title = f"{param} · {STAT_NAME.get(stat, stat)} · {GROUP_NAME.get(group, group)}"
    return _spc_evidence(wafers, group, stat, param, lsl, usl, chart=chart, title=title)


def _views(issue: dict, param: str) -> list[tuple]:
    k = issue_kinds()[issue["kind"]]
    if k["event"] == "metro_offset":  # what everyone sees first (by chamber), then the view that explains it
        return [(param, "chamber_id", "mean", "IMR"), (param, "metro_tool_id", "mean", "IMR")]
    if k["event"] == "bowl":
        return [(param, "chamber_id", "mean", "IMR"), (param, "chamber_id", "nu_1sigma_pct", "IMR")]
    return [(param, k["group"], k["stat"], k["chart"])]


def _pick_options(rng, correct: list, pool: list, n_total: int) -> list:
    extra = [o for o in dict.fromkeys(pool) if o not in correct]
    rng.shuffle(extra)
    opts = list(dict.fromkeys(correct)) + extra[:max(n_total - len(set(correct)), 0)]
    return [opts[i] for i in rng.permutation(len(opts))]


def _bi_join(parts: list[dict], sep_zh: str, sep_en: str) -> dict:
    return {"zh": sep_zh.join(p["zh"] for p in parts), "en": sep_en.join(p["en"] for p in parts)}


def linked_case(case_id: str, case_type: str, level: str, seed: int, issues: list[dict]) -> Case:
    kinds = issue_kinds()
    rng = np.random.default_rng(seed)
    built = [make_event(it) for it in issues]
    cfg, res = _fab(rng, [e for e, _ in built], n_lots=48, seed=int(rng.integers(1e6)))
    impacts = list(res.events["yield_impact"])

    # per-issue texts
    rows = []
    for i, (it, (ev, shown)) in enumerate(zip(issues, built)):
        k = kinds[it["kind"]]
        s = step_info(it["step"])
        param = k.get("param") or s["parameter"]
        v = {"param": param, "unit": "" if k["event"] == "defects" else s["unit"], "where": it["where"], "step": it["step"],
             "start": f"D{int(it['start_lot']) + 1:04d}", "size": shown, "impact": float(np.round(100 * impacts[i], 2))}
        f = Facts(v=v)
        t = {key: {lg: fill(k[key][lg], f, lg) for lg in ("zh", "en")} for key in ("symptom", "finding", "ask", "why")}
        rows.append({"id": f"I{i + 1}", "kind": it["kind"], "k": k, "v": v, "param": param, **t,
                     "keywords": [fill(w, f, "en") for w in k.get("keywords", [])]})

    # evidence: each distinct SPC view once, then yield trend and the worst die map
    evidence, guide, seen = [], [], set()
    for r, it in zip(rows, issues):
        for view in _views(it, r["param"]):
            if view in seen:
                continue
            seen.add(view)
            ev, facts = _spc_view(res, *view)
            evidence.append(ev)
            guide.append(("spc_chart", facts))
    yev, yguide, worst = _fab_yield(res, cfg, by="impact")
    lost = float(np.round(100 * (worst["yield_without_events"] - worst["yield"]), 1))
    evidence += yev
    guide += yguide
    mean_yield = float(np.round(100 * res.wafers["yield"].mean(), 1))

    # answers
    top_u = max(r["k"]["urgency"] for r in rows)
    top = [r for r in rows if r["k"]["urgency"] == top_u]
    causes = list(dict.fromkeys(r["k"]["cause"] for r in rows))
    all_causes = [kk["cause"] for kk in kinds.values()] + ["C_RANDOM", "C_OFF_TARGET", "C_EDGE_RING"]
    actions = list(dict.fromkeys(r["k"]["action"] for r in top))
    decisions = list(dict.fromkeys(r["k"]["decision"] for r in top))
    roles_all = ["RDA", "PE", "EE", "PIE_YE", "MGR_QE"]
    notify = [x for x in roles_all if any(x in r["k"]["notify"] for r in rows)]
    labels_pri = {r["id"]: {"zh": f"({r['id'][1:]}) {r['symptom']['zh']}", "en": f"({r['id'][1:]}) {r['symptom']['en']}"}
                  for r in rows}
    qs = [Question("causes", "multi", "cause", QUESTION_LABEL["causes"],
                   _pick_options(rng, causes, all_causes, min(len(causes) + 3, 6)), causes, 30,
                   prompt={"zh": "有哪些原因同時存在？（可複選）", "en": "Which causes are present? (select all)"}),
          Question("action", "single", "action", QUESTION_LABEL["action"],
                   _pick_options(rng, actions, [r["k"]["action"] for r in rows] + ["A_RECORD", "A_RETARGET", "A_PM"], 5),
                   actions, 20, prompt={"zh": "最緊急的那件事，第一步要做什麼？", "en": "First action on the most urgent issue?"}),
          Question("priority", "single", "priority", QUESTION_LABEL["priority"], [r["id"] for r in rows],
                   [r["id"] for r in top], 10, labels=labels_pri,
                   prompt={"zh": "先處理哪一個訊號？", "en": "Which signal do you handle first?"})]
    if len(rows) == 1:  # a single built issue: no ranking question
        qs = [qs[0], qs[1]]
        qs[0].weight, qs[1].weight = 40, 25
    qs += [Question("decision", "single", "decision", QUESTION_LABEL["decision"],
                    _pick_options(rng, decisions, [r["k"]["decision"] for r in rows] + ["D_RELEASE", "D_SCRAP", "D_RETARGET"], 4),
                    decisions, 20 if len(rows) == 1 else 25, prompt=QUESTION_PROMPT["decision"]),
           Question("notify", "roles", "notify", QUESTION_LABEL["notify"], roles_all, notify, 15,
                    prompt=QUESTION_PROMPT["notify"])]

    # texts
    lead = top[0]
    role = lead["k"]["message_role"]
    n = len(rows)
    title = _bi_join([r["k"]["label"] for r in rows], " + ", " + ")
    title = {"zh": ("多重訊號：" if n > 1 else "") + title["zh"], "en": ("Multiple signals: " if n > 1 else "") + title["en"]}
    brief = {"zh": ("【交接】以下訊號同時出現，請判斷有哪些原因、先處理哪一個：\n" if n > 1 else "【交接】")
             + "\n".join(f"({r['id'][1:]}) {r['symptom']['zh']}" for r in rows)
             + f"\n良率：平均 {mean_yield}%；受影響最大的晶圓 {worst.wafer_id} 良率 {100 * worst['yield']:.1f}%"
               f"（比沒有這些事件時少了 {lost} 個百分點）。目前還沒有人重測或確認量測。",
             "en": ("[Handover] These signals appeared at the same time; decide which causes are present and what to "
                    "handle first:\n" if n > 1 else "[Handover] ")
             + "\n".join(f"({r['id'][1:]}) {r['symptom']['en']}" for r in rows)
             + f"\nYield: mean {mean_yield}%; the most affected wafer {worst.wafer_id} is at {100 * worst['yield']:.1f}% "
               f"({lost} points below what it would be without these events). Nobody has re-measured or checked the "
               "measurement yet."}
    first = {"zh": f"先處理：{lead['k']['label']['zh']}，因為{URGENCY_TEXT[top_u]['zh']}。" if n > 1 else "",
             "en": f"First: the {lead['k']['label']['en'].lower()}, because {URGENCY_TEXT[top_u]['en']}." if n > 1 else ""}
    model = {"zh": (f"【多重訊號釐清】這次有 {n} 個彼此獨立的問題，要分開處理：\n" if n > 1 else "")
             + "\n".join(f"({r['id'][1:]}) {r['finding']['zh']} → {r['ask']['zh']}" for r in rows) + ("\n" + first["zh"] if n > 1 else ""),
             "en": (f"[Separating the signals] There are {n} independent problems to handle separately:\n" if n > 1 else "")
             + "\n".join(f"({r['id'][1:]}) {r['finding']['en']} → {r['ask']['en']}" for r in rows) + ("\n" + first["en"] if n > 1 else "")}
    mask = any(r["kind"] == "metro_offset" for r in rows) and n > 1
    explanation = {"zh": "\n".join(f"• {r['k']['label']['zh']}：{r['why']['zh']}。{r['finding']['zh']}。" for r in rows)
                   + (f"\n{first['zh']}" if n > 1 else "")
                   + ("\n注意：量測機台偏差會讓很多 chamber 一起 OOC，可能蓋住真正的單一 chamber 問題；依量測機台分組、"
                      "再依 chamber 分組，並對照良率（量測偏差不會改變良率），才能把兩者分開。" if mask else ""),
                   "en": "\n".join(f"• {r['k']['label']['en']}: {r['why']['en']}. {r['finding']['en']}." for r in rows)
                   + (f"\n{first['en']}" if n > 1 else "")
                   + ("\nNote: a metrology-tool offset makes many chambers OOC at once and can hide a real single-chamber "
                      "problem; group by metrology tool, then by chamber, and check yield (a metrology offset never "
                      "changes yield) to separate the two." if mask else "")}
    keypoints = [{"zh": f"指出{r['k']['label']['zh']}（{r['v']['where']}）", "en": f"Names the {r['k']['label']['en'].lower()} ({r['v']['where']})",
                  "any": [w for w in r["keywords"] if w]} for r in rows]
    if n > 1:
        keypoints.append({"zh": "說明先處理哪一個", "en": "Says what comes first", "any": ["先", "first", "優先", "priority"]})
    spec = {"domain": "mix", "title": title, "brief": brief, "model_message": model, "explanation": explanation,
            "keypoints": keypoints, "message_role": role, "notify": notify, "urgency": top_u,
            "settings": {"mode": "linked", "issues": issues}}
    correct = {q.key: q.correct for q in qs}
    options = {q.key: q.options for q in qs}
    v = {"worst_wafer": worst.wafer_id, "worst_yield": float(np.round(100 * worst["yield"], 1)), "mean_yield": mean_yield}
    return Case(case_id, case_type, level, spec, v, evidence, guide, correct, options, qs)


# --------------------------------------------------------------------------- separate: several problems, one handover
def separate_case(case_id: str, case_type: str, level: str, seed: int, types: list[str]) -> Case:
    subs = [_sub_case(i) for i in _sub_ids(types, level, seed)]
    n = len(subs)
    urg = [urgency_of(c) for c in subs]
    top_u = max(urg)
    top = [i for i, u in enumerate(urg) if u == top_u]
    heads = [{"zh": f"問題 {i + 1}：{c.text('title', 'zh')}", "en": f"Problem {i + 1}: {c.text('title', 'en')}"}
             for i, c in enumerate(subs)]
    qs = []
    for i, c in enumerate(subs):
        for q, w in (("cause", 35), ("action", 20), ("decision", 20)):
            src = c.question(q)
            qs.append(Question(f"p{i + 1}_{q}", "single", q, QUESTION_LABEL[q], list(src.options), src.correct, w / n,
                               labels=dict(src.labels), group=heads[i], prompt=QUESTION_PROMPT[q]))
    qs.append(Question("priority", "single", "priority", QUESTION_LABEL["priority"], [f"P{i + 1}" for i in range(n)],
                       [f"P{i + 1}" for i in top], 10, labels={f"P{i + 1}": heads[i] for i in range(n)},
                       prompt={"zh": "先處理哪一件？", "en": "Which do you handle first?"}))
    roles_all = ["RDA", "PE", "EE", "PIE_YE", "MGR_QE"]
    notify = [r for r in roles_all if any(r in c.correct.get("notify", []) for c in subs)]
    qs.append(Question("notify", "roles", "notify", QUESTION_LABEL["notify"], roles_all, notify, 15,
                       prompt=QUESTION_PROMPT["notify"]))

    evidence, guide = [], []
    for i, c in enumerate(subs):
        evidence.append({"kind": "header", "text": heads[i]})
        evidence += c.evidence
        guide += c.guide
    lead = subs[top[0]]

    def txt(c, key, lg):
        return c.text(key, lg)

    def opt(c, q, lg):
        return c.option_text(q, c.correct[q], lg)

    def gist(c, lg):  # the first sentence of the problem's own model message: its key facts
        m = c.text("model_message", lg).split("\n")[0]
        m = m.split("。")[0] if lg == "zh" else m.split(". ")[0]
        return m.rstrip("。. ")

    title = {"zh": f"交接：{n} 件事", "en": f"Handover: {n} items"}
    brief = {"zh": f"【交接】今天交接有 {n} 件事，請逐一判斷，並決定先處理哪一件：\n\n"
             + "\n\n".join(f"{h['zh']}\n{txt(c, 'brief', 'zh')}" for h, c in zip(heads, subs)),
             "en": f"[Handover] {n} items from the last shift; judge each one and decide which comes first:\n\n"
             + "\n\n".join(f"{h['en']}\n{txt(c, 'brief', 'en')}" for h, c in zip(heads, subs))}
    others = [i for i in range(n) if i != top[0]]
    model = {"zh": f"【先處理】{heads[top[0]]['zh']}（{URGENCY_TEXT[top_u]['zh']}）：{gist(lead, 'zh')}。第一步：{opt(lead, 'action', 'zh')}\n"
             + "【其他事項】" + "；".join(f"{heads[i]['zh']}：{gist(subs[i], 'zh')}。第一步：{opt(subs[i], 'action', 'zh')}"
                                     for i in others) + "\n"
             + "【已做】已通知：" + ("、".join(role_name(r, "zh") for r in notify) or "不需升級") + "\n"
             + "【需要決定】" + "；".join(f"{heads[i]['zh']}：{opt(subs[i], 'decision', 'zh')}" for i in range(n)),
             "en": f"[First] {heads[top[0]]['en']} ({URGENCY_TEXT[top_u]['en']}): {gist(lead, 'en')}. First step: "
                   f"{opt(lead, 'action', 'en')}\n"
             + "[Other items] " + "; ".join(f"{heads[i]['en']}: {gist(subs[i], 'en')}. First step: {opt(subs[i], 'action', 'en')}"
                                          for i in others) + "\n"
             + "[Done so far] Notified: " + (", ".join(role_name(r, "en") for r in notify) or "no escalation") + "\n"
             + "[Decisions needed] " + "; ".join(f"{heads[i]['en']}: {opt(subs[i], 'decision', 'en')}" for i in range(n))}
    explanation = {"zh": f"先處理 {heads[top[0]]['zh']}：{URGENCY_TEXT[top_u]['zh']}。\n\n"
                   + "\n\n".join(f"{h['zh']}（{c.id}）\n{txt(c, 'explanation', 'zh')}" for h, c in zip(heads, subs)),
                   "en": f"Handle {heads[top[0]]['en']} first: {URGENCY_TEXT[top_u]['en']}.\n\n"
                   + "\n\n".join(f"{h['en']} ({c.id})\n{txt(c, 'explanation', 'en')}" for h, c in zip(heads, subs))}
    keypoints, order = [], []
    for h, c in zip(heads, subs):
        kp = (c.spec.get("keypoints") or [{}])[0]
        tokens = [fill(t, c.facts, lg) for t in kp.get("any", []) for lg in ("zh", "en")]
        tokens += [c.text("title", "zh"), c.text("title", "en")]  # naming the item in the summary counts too
        tokens = [t for t in dict.fromkeys(tokens) if t and t != "—"]
        keypoints.append({"zh": f"{h['zh']}：{kp.get('zh', '')}", "en": f"{h['en']}: {kp.get('en', '')}", "any": tokens})
        order.append([h["zh"].split("：")[0], h["en"].split(":")[0]] + tokens)  # "問題 1" / "Problem 1" + its facts
    keypoints.append({"zh": "最緊急的那件寫在最前面", "en": "Puts the most urgent item first", "order": order, "top": top})
    spec = {"domain": "mix", "title": title, "brief": brief, "model_message": model, "explanation": explanation,
            "keypoints": keypoints, "message_role": "MGR_QE", "message_format": "handover", "notify": notify,
            "urgency": top_u, "settings": {"mode": "separate", "types": types}, "parts": [c.id for c in subs]}
    correct = {q.key: q.correct for q in qs}
    options = {q.key: q.options for q in qs}
    return Case(case_id, case_type, level, spec, {}, evidence, guide, correct, options, qs)


def describe_settings(settings: dict, lang: str = "en") -> str:
    """One line describing builder settings (for lists and the page)."""
    if settings.get("mode") == "linked":
        k = issue_kinds()
        return " + ".join(f"{k[i['kind']]['label'][lang]} ({i['step']} {i['where']}, {i['size']})" for i in settings["issues"])
    return " + ".join(type_info(t)["title"][lang] for t in settings.get("types", []))
