"""The metrology map: which technique measures what, and which one fits a measurement need.

metrology_tree.yaml follows the learner's tree, parameter -> metrology category -> tool -> characteristics, with every
tool's facts researched and sourced (research_notes/Metrology tree verification/). Each tool lists the toolkit pages
that simulate it, and every original note is kept with its verdict (verified / corrected / unresolved).

choose() is the "Which technique?" helper: for one parameter and your constraints it ranks the candidate tools and
says why the others drop out. It reads only the structured fields (thickness range, film type, location, contact,
destructiveness, integration, speed), so its answers stay consistent with the tool cards.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
LOCATIONS = ("in_die", "scribe", "blanket")
SPEED = {"fast": 0, "medium": 1, "slow": 2}
DESTRUCTIVE = {"no": 0, "slight": 1, "yes": 2}


def available() -> bool:
    return (HERE / "metrology_tree.yaml").exists()


@lru_cache(maxsize=None)
def tree() -> dict:
    if not available():
        return {}
    return yaml.safe_load((HERE / "metrology_tree.yaml").read_text(encoding="utf-8")) or {}


def tools() -> dict:
    return tree().get("tools", {})


def parameters() -> dict:
    """parameter id -> {name, what, processes, category, groups}."""
    out = {}
    for cat in tree().get("categories", []):
        for p in cat.get("parameters", []):
            out[p["id"]] = {**p, "category": cat["id"]}
    return out


def tools_for(parameter: str) -> list[str]:
    """Every tool that measures this parameter (from all its metrology categories), in tree order."""
    seen = []
    for g in parameters().get(parameter, {}).get("groups", []):
        for t in g.get("tools", []):
            if t not in seen:
                seen.append(t)
    return seen


def parameters_of(tool: str) -> list[str]:
    return [pid for pid in parameters() if tool in tools_for(pid)]


def search(text: str, lang: str = "en") -> list[str]:
    """Tool ids whose name, principle, measures, strengths, limits or notes contain the text (case-insensitive)."""
    q = (text or "").strip().lower()
    if not q:
        return list(tools())
    hits = []
    for tid, t in tools().items():
        blob = " ".join(str(v) for v in t.values()).lower()
        if q in blob or q in tid:
            hits.append(tid)
    return hits


def claims() -> list[dict]:
    """Every original note with its verdict: [{tool, claim, verdict, fix, source}]."""
    out = []
    for tid, t in tools().items():
        for n in t.get("notes", []) or []:
            out.append({"tool": tid, **n})
    for p in parameters().values():
        for n in p.get("notes", []) or []:
            out.append({"tool": p["id"], **n})
    return out


def _bi(zh: str, en: str) -> dict:
    return {"zh": zh, "en": en}


def choose(parameter: str, thickness_nm: float | None = None, film: str | None = None, location: str | None = None,
           non_destructive: bool = False, no_contact: bool = False, inline: bool = False,
           fast: bool = False) -> tuple[list[dict], list[dict]]:
    """Rank the tools for a parameter under your constraints.

    film: transparent | absorbing | metal | conductive (None = any). location: in_die | scribe | blanket.
    Returns (fits, excluded): fits = [{tool, score, why: [{zh, en}]}] best first; excluded = [{tool, why: [{zh, en}]}].
    """
    fits, excluded = [], []
    for tid in tools_for(parameter):
        t = tools().get(tid, {})
        why_not, why = [], []
        rng = t.get("thickness_nm")
        if thickness_nm is not None and rng:
            lo, hi = rng
            if not lo <= thickness_nm <= hi:
                why_not.append(_bi(f"厚度範圍約 {lo:g}–{hi:g} nm，{thickness_nm:g} nm 不在範圍內",
                                   f"thickness range is about {lo:g}–{hi:g} nm; {thickness_nm:g} nm is outside it"))
            else:
                why.append(_bi(f"{thickness_nm:g} nm 在範圍內（約 {lo:g}–{hi:g} nm）", f"{thickness_nm:g} nm is in range (about {lo:g}–{hi:g} nm)"))
        films = t.get("film") or ["any"]
        if film and "any" not in films and film not in films:
            why_not.append(_bi(f"不適用於這種膜（適用：{'、'.join(films)}）", f"not for this film type (works on: {', '.join(films)})"))
        locs = t.get("location") or []
        if location and locs and location not in locs:
            why_not.append(_bi(f"不在這個位置量測（可量：{'、'.join(locs)}）", f"does not measure at this location (measures: {', '.join(locs)})"))
        elif location and location in locs:
            why.append(_bi("可以在這個位置量測", "measures at this location"))
        if non_destructive and DESTRUCTIVE.get(str(t.get("destructive", "no")), 0) >= 2:
            why_not.append(_bi("會破壞樣品", "destructive"))
        if no_contact and t.get("contact"):
            why_not.append(_bi("需要接觸晶圓", "touches the wafer"))
        integ = t.get("inline") or []
        integ = integ if isinstance(integ, list) else [integ]
        if inline and integ and not ({"inline", "integrated"} & set(integ)):
            why_not.append(_bi("只在實驗室／離線使用", "lab / offline only"))
        if why_not:
            excluded.append({"tool": tid, "why": why_not})
            continue
        score = 0.0
        if fast:
            score -= SPEED.get(str(t.get("speed", "medium")), 1)
            if t.get("speed") == "fast":
                why.append(_bi("速度快", "fast"))
        score -= 0.5 * DESTRUCTIVE.get(str(t.get("destructive", "no")), 0)
        if t.get("destructive") == "slight":
            why.append(_bi("輕微影響樣品（例如電子束），要注意", "slight sample impact (e.g. e-beam); keep in mind"))
        if "integrated" in integ:
            score += 0.3
        if t.get("reference"):
            score -= 1.0  # reference / lab metrology: used to check the others, not for routine monitoring
            why.append(_bi("參考量測（用來校準其他量測，不是例行監控）", "reference metrology (used to anchor others, not routine monitoring)"))
        fits.append({"tool": tid, "score": score, "why": why})
    fits.sort(key=lambda f: -f["score"])
    return fits, excluded


__all__ = ["available", "choose", "claims", "parameters", "parameters_of", "search", "tools", "tools_for", "tree"]
