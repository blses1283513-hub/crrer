"""Chart and parameter guide: what every control and chart means, in Metro AE language (繁中 + English).

meta.yaml       roles (who gets a message) and status labels (good / watch / act)
params_*.yaml   one entry per control / KPI tile / table column (definition, typical values, effect, traps)
charts_*.yaml   one entry per chart: legend items, axes, what it shows, how to read it, action by status,
                what to record, and a ready-to-send message for each role
insights.py   reads the data behind a chart and returns Facts (status + findings with real numbers)
render.py     Streamlit widgets: help text lookup and the "how to read this chart" panel

Templates in charts.yaml use {placeholders}; {finding} and {status} always exist, chart-specific values
come from Facts.v. A missing value renders as "—" instead of failing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
LANGS = ("zh", "en")
STATUSES = ("good", "watch", "act")
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass
class Facts:
    """What the data behind one chart says. status: good | watch | act."""

    status: str = "good"
    zh: list[str] = field(default_factory=list)  # findings, one sentence each
    en: list[str] = field(default_factory=list)
    v: dict = field(default_factory=dict)  # template values: scalar, or {"zh": ..., "en": ...}

    def add(self, zh: str, en: str) -> Facts:
        self.zh.append(zh)
        self.en.append(en)
        return self

    def worse(self, status: str) -> Facts:
        """Raise the status (never lower it)."""
        if STATUSES.index(status) > STATUSES.index(self.status):
            self.status = status
        return self


@lru_cache(maxsize=None)
def _load(name: str) -> dict:
    return yaml.safe_load((HERE / name).read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=None)
def _merged(prefix: str, section: str) -> dict:
    out: dict = {}
    for path in sorted(HERE.glob(f"{prefix}_*.yaml")):
        part = _load(path.name).get(section) or {}
        dup = set(out) & set(part)
        if dup:
            raise ValueError(f"{path.name}: duplicate keys {sorted(dup)}")
        out.update(part)
    return out


def params() -> dict:
    return _merged("params", "params")


def charts() -> dict:
    return _merged("charts", "charts")


def meta() -> dict:
    """Roles and status labels."""
    return _load("meta.yaml")


def reload() -> None:
    _load.cache_clear()
    _merged.cache_clear()


def help_text(key: str, lang: str = "both") -> str | None:
    """Tooltip text for a control: zh, en, or both (zh first)."""
    p = params().get(key)
    if not p:
        return None
    parts = [p[k].strip() for k in (LANGS if lang == "both" else (lang,)) if p.get(k)]
    return "\n\n---\n\n".join(parts) if parts else None


class _Safe(dict):
    def __missing__(self, key):
        return "—"


def _num(x):
    if x is None:
        return "—"
    if isinstance(x, float):
        if x != x:  # nan
            return "—"
        return f"{x:.4g}"
    return x


def fill(template: str | None, facts: Facts | None, lang: str) -> str:
    """Fill a template with facts in one language."""
    if not template:
        return ""
    values = _Safe()
    if facts is not None:
        for k, val in facts.v.items():
            values[k] = _num(val.get(lang, val.get("zh")) if isinstance(val, dict) else val)
        lines = facts.zh if lang == "zh" else facts.en
        values["finding"] = ("；" if lang == "zh" else "; ").join(lines) if lines else "—"
        st = meta()["status"].get(facts.status, {})
        values["status"] = f"{st.get('icon', '')} {st.get(lang, facts.status)}".strip()
    return _PLACEHOLDER.sub(lambda m: str(values[m.group(1)]), template).strip()  # other braces stay as text


def text(entry: dict | None, lang: str, facts: Facts | None = None) -> str:
    """entry = {"zh": ..., "en": ...} -> filled text in one language."""
    if not entry:
        return ""
    return fill(entry.get(lang), facts, lang)
