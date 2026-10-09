"""Comments on wrong answers, the follow-up block and the Claude tutor: every option and role has its why-text, case
notes never contradict a possible right answer, comments quote the case's own data, follow-up notes and retries reach
the report, the study log and the cross study, and the tutor sends the right request (tested with a fake client: no
API key, no cost)."""

import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from metro_toolkit import cases
from metro_toolkit.cases import compose, tutor, why
from metro_toolkit.guide import meta

PH = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
LIB = cases.library()
FAST = [t for t in LIB["cases"] if not t.startswith("fab_")]  # the fab simulator is slow: sampled less below


@pytest.fixture(autouse=True)
def _local_store(tmp_path, monkeypatch):
    monkeypatch.setenv("METRO_CASES_PATH", str(tmp_path / "cases"))


def test_every_option_and_role_has_a_why_text():
    opts = why.texts()["options"]
    for pool in ("causes", "actions", "decisions"):
        for o in LIB["pools"][pool]:
            for lg in ("zh", "en"):
                assert why.when_text(o, lg).strip(), (o, lg)
                if pool == "causes":
                    assert why.looks_text(o, lg).strip(), (o, lg)
    assert set(opts) <= {o for p in LIB["pools"].values() for o in p}
    for r in meta()["roles"]:
        for need in (True, False):
            assert why.role_text(r, need, "zh").strip() and why.role_text(r, need, "en").strip()
    flat = [t for e in opts.values() for f in e.values() for t in f.values()]
    flat += [t for e in why.texts()["roles"].values() for f in e.values() for t in f.values()]
    assert not any("{" in t or "}" in t for t in flat) and not re.search(r"micron|美光", str(why.texts()), re.I)


def _possible(case_type: str, seeds) -> tuple[dict, set]:
    right = {q: set() for q in ("cause", "action", "decision")}
    keys = set()
    for lv in cases.LEVELS:
        for s in seeds:
            c = cases.generate(cases.make_id(case_type, lv, s))
            keys |= set(c.v)
            for q in right:
                right[q].add(c.correct[q])
    return right, keys


@pytest.mark.parametrize("case_type", sorted(LIB["cases"]))
def test_case_notes_never_contradict_a_right_answer(case_type):
    entry = why.texts()["cases"].get(case_type)
    assert entry and entry["check_first"]["zh"].strip() and entry["check_first"]["en"].strip()
    right, keys = _possible(case_type, range(8) if case_type in FAST else range(2))
    spec = LIB["cases"][case_type]
    for option, text in (entry.get("notes") or {}).items():
        q = option[0]
        qname = {"C": "cause", "A": "action", "D": "decision"}[q]
        assert option not in right[qname], f"{option} can be the right {qname} of {case_type}"
        assert option in spec[f"{qname}_options"] or option in right[qname]
        for lg in ("zh", "en"):
            assert set(PH.findall(text[lg])) <= keys, (option, lg)
    for lg in ("zh", "en"):
        assert set(PH.findall(entry["check_first"][lg])) <= keys


def _answer(c, wrong_q=("cause",)):
    ans = {k: c.correct[k] for k in ("cause", "action", "decision")} | {"notify": list(c.correct["notify"])}
    for q in wrong_q:
        ans[q] = next(o for o in c.options[q] if o != c.correct[q])
    return ans


def test_comment_explains_the_wrong_choice_with_the_case_data():
    c = cases.generate("spc_chamber_shift-B-00003")
    ans = _answer(c) | {"notify": ["EE", "RDA"]}
    r = cases.score(c, ans)
    items = why.comments(c, r)
    assert {i["key"] for i in items} == {"cause", "notify"}
    cause = next(i for i in items if i["key"] == "cause")
    for lg, words in (("en", ("You chose", "When this is the right answer", "Model answer", "What this data shows",
                              "The deciding chart")), ("zh", ("你選了", "這個答案在什麼時候才對", "標準答案", "這份資料顯示"))):
        text = "\n".join(why.comment_lines(c, cause, lg))
        assert all(w in text for w in words), (lg, text)
        assert c.v["chamber"] in text  # the chart findings quote this case's chamber
    roles = "\n".join(why.comment_lines(c, next(i for i in items if i["key"] == "notify"), "en"))
    assert "Missed" in roles and "Extra" in roles and "RDA" in roles
    perfect = cases.score(c, _answer(c, ()))
    assert why.comments(c, perfect) == [] and why.report_section(c, perfect, ["zh", "en"]) == []
    qa = why.followup_answers(c, cause, "en")
    assert [q for q, _ in qa][0].startswith("Why isn't it") and all(a.strip() for _, a in qa)
    assert any("check first" in q for q, _ in qa) and any("look like" in q for q, _ in qa)


def test_separate_handover_comments_use_each_problem_and_priority():
    ct = compose.save_settings({"mode": "separate", "types": ["spc_false_alarm", "spc_chamber_shift"]})
    c = cases.generate(cases.make_id(ct, "basic", 0))
    ans = {q.key: (q.accepted()[0] if q.kind == "single" else list(q.correct)) for q in c.questions}
    pri = c.question("priority")
    ans["priority"] = next(o for o in pri.options if o not in pri.accepted())
    p1 = c.question("p1_cause")
    ans["p1_cause"] = next(o for o in p1.options if o not in p1.accepted())
    items = {i["key"]: i for i in why.comments(c, cases.score(c, ans))}
    assert set(items) == {"priority", "p1_cause"}
    text = "\n".join(why.comment_lines(c, items["priority"], "en"))
    assert "urgency" in text.lower() and "product at risk" in text
    sub = cases.generate(c.spec["parts"][0])
    assert why.findings(sub, "en")[0] in "\n".join(why.comment_lines(c, items["p1_cause"], "en"))


def test_followup_reaches_report_log_and_cross_study(tmp_path):
    c = cases.generate("wafer_tilt-B-00003")
    ans = _answer(c)
    r = cases.score(c, ans)
    fu = {"note": "I thought the tilt was an edge ring", "retry_of": None,
          "chat": [{"role": "user", "content": "Why not the edge ring?"}, {"role": "assistant", "content": "Because…"}]}
    md = cases.report_markdown(c, ans, r, "msg", "both", followup=fu)
    for s in ("Why your wrong answers don't fit", "When this is the right answer", "What I thought",
              "I thought the tilt was an edge ring", "Why not the edge ring?", "Claude"):
        assert s in md, s
    cases.save_attempt(c, r, md, tmp_path, message="msg", followup=fu)
    again = cases.generate("wafer_tilt-B-00077")
    r2 = cases.score(again, _answer(again, ()))
    cases.save_attempt(again, r2, "x", tmp_path, followup={"retry_of": c.id})
    h = cases.history(tmp_path)
    assert h.iloc[0]["followup"] == fu["note"] and h.iloc[0]["tutor_turns"] == 1 and h.iloc[1]["retry_of"] == c.id
    prof = cases.study_profile(h)
    assert prof["notes"][0]["note"] == fu["note"] and prof["notes"][0]["retry_score"] == 100
    assert prof["retries"] == [{"case": again.id, "retry_of": c.id, "score": 100, "before": r["total"]}]


# --------------------------------------------------------------------------- the tutor (fake client: no key, no cost)
class FakeStream:
    def __init__(self, chunks, stop):
        self.chunks, self.stop = chunks, stop

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    @property
    def text_stream(self):
        return iter(self.chunks)

    def get_final_message(self):
        return SimpleNamespace(stop_reason=self.stop)


class FakeClient:
    def __init__(self, chunks=("Because ", "only one chamber moved."), stop="end_turn"):
        self.calls, self.chunks, self.stop = [], chunks, stop
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kw):
        self.calls.append(kw)
        return FakeStream(self.chunks, self.stop)


def test_tutor_request_and_guard():
    c = cases.generate("spc_chamber_shift-B-00003")
    ans = _answer(c)
    r = cases.score(c, ans)
    system = tutor.system_prompt(c, ans, r, "both")
    assert c.text("brief", "en") in system and "WRONG" in system and "RIGHT" in system
    assert "When this is the right answer" in system and "Traditional Chinese first" in system
    fake = FakeClient()
    out = "".join(tutor.ask(system, [{"role": "user", "content": "Why not metrology?"}], client=fake))
    assert out == "Because only one chamber moved."
    kw = fake.calls[0]
    assert kw["model"] == "claude-opus-5-5" and kw["fallbacks"] == "default"
    assert kw["betas"] == ["server-side-fallback-2026-07-01"] and kw["output_config"] == {"effort": "medium"}
    assert kw["system"][0]["cache_control"] == {"type": "ephemeral"} and kw["messages"][-1]["content"] == "Why not metrology?"
    declined = "".join(tutor.ask(system, [{"role": "user", "content": "x"}], client=FakeClient((), "refusal")))
    assert "declined" in declined
    assert tutor.guard("Why is this Micron lot different?") and tutor.guard("這是公司機密資料嗎") and tutor.guard("  ")
    assert tutor.guard("Why isn't it a metrology offset?") is None


def test_followup_block_and_tutor_on_the_page(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    fake = FakeClient()
    monkeypatch.setattr(tutor, "make_client", lambda key=None: fake)
    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path / "imp"))
    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=300)
    at.run()
    at.sidebar.radio(key="nav_page").set_value("Case study 案例練習").run()
    cid = "spc_chamber_shift-B-00003"
    at.text_input(key="case_replay_id").set_value(cid).run()
    [b for b in at.button if b.key == "case_replay"][0].click().run()
    c = cases.generate(cid)
    ans = _answer(c)
    for q in ("cause", "action", "decision"):
        at.radio(key=f"q_{q}_{cid}").set_value(ans[q])
    at.multiselect(key=f"q_notify_{cid}").set_value(ans["notify"])
    at.text_area(key=f"q_msg_{cid}").set_value("ok")
    [b for b in at.button if "Submit" in b.label][0].click().run()
    assert not at.exception
    assert any("When this is the right answer" in m.value for m in at.markdown)
    assert any(e.label.startswith("❓") for e in at.expander)
    at.text_area(key=f"fu_note_{cid}").set_value("I thought it was the gauge")
    at.text_area(key=f"tutor_q_{cid}_0").set_value("Why not a metrology offset?")
    [b for b in at.button if b.key == f"tutor_ask_{cid}"][0].click().run()
    assert not at.exception and fake.calls and "Why not a metrology offset?" in str(fake.calls[0]["messages"])
    assert any("only one chamber moved" in m.value for m in at.markdown)
    [b for b in at.button if b.key == f"case_save_{cid}"][0].click().run()
    md = sorted((tmp_path / "cases").glob(f"{cid}_*.md"))[-1].read_text(encoding="utf-8")
    assert "I thought it was the gauge" in md and "Why not a metrology offset?" in md and "only one chamber moved" in md
    [b for b in at.button if b.key == f"fu_retry_{cid}"][0].click().run()
    new = at.session_state["case_id"]
    assert new != cid and new.startswith("spc_chamber_shift-B-") and not at.exception
