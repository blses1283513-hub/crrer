"""Your own case templates, saved only on this PC: data/cases/custom/<name>.yaml (data/ is git-ignored).

A template is your text on top of an existing data pattern: ``base`` names one of the built-in case types, whose
generator draws the evidence (charts) and provides the {placeholders} your brief and model message can quote.
You write the title, brief, the right answer and the wrong options for cause / action / decision (a pool option or
your own text), who to notify, the message role and format, a model message, a message checklist and an explanation.
The case type is ``my_<name>``; its IDs (``my_<name>-I-01234``) replay on this PC like any other case.

Write real-work situations without real lot IDs, product names, recipes or people's names: keep it a practice case.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import yaml

from . import Case, cases_dir, library, make_id, shuffled_options, standard_questions
from .generators import GENERATORS

QUESTIONS = ("cause", "action", "decision")
CUSTOM_ID = {"cause": "U_CAUSE", "action": "U_ACTION", "decision": "U_DECISION"}
ROLES = ("RDA", "PE", "EE", "PIE_YE", "MGR_QE")
_PH = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def templates_dir(folder: Path | None = None) -> Path:
    path = (Path(folder) if folder else cases_dir()) / "custom"
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")[:40]
    return s or "case"


def load_templates(folder: Path | None = None) -> dict:
    """{my_<name>: template} for every readable, valid template file."""
    out = {}
    for path in sorted(templates_dir(folder).glob("*.yaml")):
        try:
            tpl = validate_template(yaml.safe_load(path.read_text(encoding="utf-8")) or {})
        except (yaml.YAMLError, ValueError, KeyError, TypeError):
            continue
        out[f"my_{path.stem}"] = tpl
    return out


def base_types() -> list[str]:
    """Built-in case types a template can take its data from."""
    return list(library()["cases"])


def placeholders(base: str) -> dict:
    """The {values} a template on this base can quote, with an example value each."""
    from . import generate

    c = generate(make_id(base, "basic", 1))
    out = {}
    for k, v in c.v.items():
        out[k] = v.get("en") if isinstance(v, dict) else v
    return out


def _both(entry, name: str) -> dict:
    """{zh, en}: either may be written; the missing one is copied from the other."""
    entry = entry or {}
    zh, en = (entry.get("zh") or "").strip(), (entry.get("en") or "").strip()
    if not zh and not en:
        raise ValueError(f"{name}: write it in at least one language")
    return {"zh": zh or en, "en": en or zh}


def validate_template(tpl: dict) -> dict:
    """Check a template and fill in missing languages; returns the cleaned template (raises ValueError)."""
    lib = library()
    if tpl.get("base") not in lib["cases"]:
        raise ValueError("base: choose one of the built-in case types as the data pattern")
    out = {"base": tpl["base"]}
    for key in ("title", "brief", "model_message", "explanation"):
        out[key] = _both(tpl.get(key), key)
    opts = {}
    for q in QUESTIONS:
        pool = lib["pools"][{"cause": "causes", "action": "actions", "decision": "decisions"}[q]]
        right = tpl.get(q)
        if right == CUSTOM_ID[q]:
            opts[CUSTOM_ID[q]] = _both((tpl.get("options") or {}).get(CUSTOM_ID[q]), f"{q} (your own text)")
        elif right not in pool:
            raise ValueError(f"{q}: choose the right answer")
        wrong = [o for o in (tpl.get(f"{q}_options") or []) if o != right]
        if len(wrong) < 2:
            raise ValueError(f"{q}: choose at least 2 wrong options")
        if any(o not in pool for o in wrong):
            raise ValueError(f"{q}: unknown option in the wrong options")
        out[q], out[f"{q}_options"] = right, wrong
    out["options"] = opts
    notify = list(tpl.get("notify") or [])
    if any(r not in ROLES for r in notify):
        raise ValueError("notify: unknown role")
    out["notify"] = notify
    if tpl.get("message_role") not in ROLES:
        raise ValueError("message_role: choose who the message goes to")
    out["message_role"] = tpl["message_role"]
    fmt = tpl.get("message_format") or None
    if fmt and fmt not in lib.get("formats", {}):
        raise ValueError("message_format: unknown format")
    out["message_format"] = fmt
    kps = []
    for kp in tpl.get("keypoints") or []:
        words = [w.strip() for w in (kp.get("any") or []) if str(w).strip()]
        if not words or not ((kp.get("zh") or "").strip() or (kp.get("en") or "").strip()):
            continue
        kps.append({**_both(kp, "keypoint"), "any": words})
    out["keypoints"] = kps
    out["urgency"] = int(tpl.get("urgency") or 2)
    if out["urgency"] not in (1, 2, 3):
        raise ValueError("urgency: 1, 2 or 3")
    return out


def unknown_placeholders(tpl: dict) -> list[str]:
    """{names} used in the texts that the base data pattern does not provide (shown as — in the case)."""
    have = set(placeholders(tpl["base"]))
    used = set()
    for key in ("title", "brief", "model_message", "explanation"):
        for lg in ("zh", "en"):
            used |= set(_PH.findall(tpl[key][lg]))
    for kp in tpl.get("keypoints", []):
        for w in kp["any"]:
            used |= set(_PH.findall(w))
    return sorted(used - have)


def save_template(tpl: dict, name: str | None = None, folder: Path | None = None, replace: bool = False) -> str:
    """Validate and save; returns the case type my_<name>. A new template never overwrites another one (a suffix is
    added); replace=True saves over the template of that name (editing it)."""
    clean = validate_template(tpl)
    name = slugify(name or clean["title"]["en"])
    path = templates_dir(folder) / f"{name}.yaml"
    k = 2
    while path.exists() and not replace:
        path = templates_dir(folder) / f"{name}_{k}.yaml"
        k += 1
    name = path.stem
    path.write_text(yaml.safe_dump(clean, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")
    return f"my_{name}"


def delete_template(case_type: str, folder: Path | None = None) -> bool:
    path = templates_dir(folder) / f"{case_type.removeprefix('my_')}.yaml"
    if path.exists():
        path.unlink()
        return True
    return False


def template_stamp(case_type: str) -> float:
    """Modification time of a template file (so an edited template is not served from the page cache)."""
    path = templates_dir() / f"{case_type.removeprefix('my_')}.yaml"
    return path.stat().st_mtime if path.exists() else 0.0


def generate_custom(case_id: str, case_type: str, level: str, seed: int) -> Case:
    tpl = load_templates()[case_type]
    out = GENERATORS[tpl["base"]](np.random.default_rng(seed), level)
    spec = {**tpl, "domain": "custom"}
    correct = {q: tpl[q] for q in QUESTIONS} | {"notify": list(tpl["notify"])}
    options = shuffled_options(spec, correct, seed)
    labels = dict(tpl.get("options") or {})
    return Case(case_id, case_type, level, spec, out["v"], out["evidence"], out["guide"], correct, options,
                standard_questions(correct, options, labels))


__all__ = ["base_types", "delete_template", "generate_custom", "load_templates", "placeholders",
           "save_template", "slugify", "template_stamp", "templates_dir", "unknown_placeholders", "validate_template"]
