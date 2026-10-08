"""Streamlit side of the guide: language switch, control tooltips and the "how to read this chart" panel."""

from __future__ import annotations

import streamlit as st

from . import STATUSES, Facts, charts, help_text, meta, text

LANG_OPTIONS = {"both": "繁中 + English", "zh": "繁中", "en": "English"}
_SHOWN = {"good": "success", "watch": "warning", "act": "error"}  # icon + label always shown too


def lang() -> str:
    return st.session_state.get("guide_lang", "both")


def language_switch(where=None) -> str:
    """Sidebar selector for the explanation language (kept across pages)."""
    where = where or st.sidebar
    where.radio("說明語言 Guide language", list(LANG_OPTIONS), format_func=LANG_OPTIONS.get, key="guide_lang",
                horizontal=True, help=H("guide.language"))
    return lang()


def H(key: str) -> str | None:
    """Tooltip text for a control in the current language."""
    return help_text(key, lang())


def _langs():
    return ("zh", "en") if lang() == "both" else (lang(),)


def _bi(entry, facts=None, prefix: str = ""):
    """Write a {zh, en} entry in the chosen language(s)."""
    for lg in _langs():
        t = text(entry, lg, facts)
        if t:
            st.markdown((prefix + t) if lg == "zh" or lang() != "both" else f"*{prefix}{t}*")


def status_line(facts: Facts, where=None):
    """One visible line under a chart: status icon + label + the main finding."""
    m = meta()["status"].get(facts.status, {})
    parts = []
    for lg in _langs():
        lines = facts.zh if lg == "zh" else facts.en
        head = f"{m.get('icon', '')} **{m.get(lg, facts.status)}**"
        parts.append(head + (("：" if lg == "zh" else ": ") + lines[0] if lines else ""))
    getattr(where or st, _SHOWN.get(facts.status, "info"))("  \n".join(parts))


def explain(key: str, facts: Facts | None = None, where=None, inline: bool = False):
    """Status line + a 4-tab panel: legend & axes / what it shows / next step / who to tell.

    inline=True renders without an expander (for charts that already sit inside one)."""
    c = charts().get(key)
    if c is None:
        return
    host = where or st
    if facts is not None:
        status_line(facts, host)
    box = host.container() if inline else host.expander("📖 怎麼讀這張圖 · How to read this chart")
    with box:
        tabs = st.tabs(["圖例與座標 Legend", "代表什麼與洞察 Insight", "下一步 Action", "跟誰說 Who to tell"])
        with tabs[0]:
            for item in c.get("legend", []):
                st.markdown(f"**{item['item']}**")
                _bi(item, facts, prefix="")
            if c.get("axes"):
                st.markdown("**座標軸 Axes**")
                _bi(c["axes"], facts)
        with tabs[1]:
            st.markdown("**這張圖代表什麼 What it shows**")
            _bi(c.get("what"), facts)
            st.markdown("**怎麼判讀 How to read it (good vs bad)**")
            _bi(c.get("read"), facts)
            if facts is not None and (facts.zh or facts.en):
                st.markdown("**這份資料的判讀 What this data says**")
                for lg in _langs():
                    lines = facts.zh if lg == "zh" else facts.en
                    st.markdown("\n".join(f"- {s}" for s in lines) if lg == "zh" or lang() != "both"
                                else "\n".join(f"- *{s}*" for s in lines))
        with tabs[2]:
            current = facts.status if facts is not None else None
            labels = meta()["status"]
            for s in ([current] if current else []) + [s for s in STATUSES if s != current]:
                act = c.get("action", {}).get(s)
                if not act:
                    continue
                head = f"{labels[s]['icon']} **{labels[s]['zh']} · {labels[s]['en']}**"
                st.markdown(head + ("　← 目前狀態 current" if s == current else ""))
                _bi(act, facts)
            if c.get("record"):
                st.markdown("**記錄 What to record (e-log / SPC comment)**")
                for lg in _langs():
                    st.code(text(c["record"], lg, facts), language=None, wrap_lines=True)
        with tabs[3]:
            roles = meta()["roles"]
            for rk, r in roles.items():
                msg = c.get("roles", {}).get(rk)
                if not msg:
                    continue
                st.markdown(f"**{r['zh']} · {r['en']}**")
                st.caption(" / ".join(r.get(f"cares_{lg}", "") for lg in _langs()))
                for lg in _langs():
                    st.code(text(msg, lg, facts), language=None, wrap_lines=True)
