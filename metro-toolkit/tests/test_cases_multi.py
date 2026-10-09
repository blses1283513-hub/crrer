"""Multi-issue cases, the case builder, your own templates and the real-workflow case types: every issue kind works
alone and combined, answers follow the data, perfect answers score 100, model messages cover their checklist, and
reports / the cross study / the page handle all of it."""

import re
from pathlib import Path

import pytest

from metro_toolkit import cases, guide
from metro_toolkit.cases import compose, custom

PH = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


@pytest.fixture(autouse=True)
def _local_store(tmp_path, monkeypatch):
    monkeypatch.setenv("METRO_CASES_PATH", str(tmp_path / "cases"))


def perfect(case):
    return {q.key: (q.accepted()[0] if q.kind == "single" else list(q.correct)) for q in case.questions}


def check_case(case):
    """Every question answerable, perfect = 100, the model message covers its own checklist, texts complete."""
    assert case.questions and abs(sum(q.weight for q in case.questions) - 100) < 1e-6
    for q in case.questions:
        assert all(c in q.options for c in q.accepted()), q.key
        if q.kind == "single":
            assert len(q.options) >= 2
    assert cases.score(case, perfect(case))["total"] == 100
    for lg in ("zh", "en"):
        for key in ("title", "brief", "model_message", "explanation"):
            assert case.text(key, lg).strip() and "{" not in case.text(key, lg), (key, lg)
        assert all(ok for _, ok in cases.message_checklist(case, case.text("model_message", lg), lg)), lg
    assert case.evidence and case.guide


# --------------------------------------------------------------------------- new charts and real-workflow types
NEW_CHARTS = {"defect_counts": "insp_nuisance_recipe", "review_pareto": "insp_nuisance_recipe",
              "adder_compare": "insp_split_vs_baseline", "bin_corr": "ye_bin_metro_corr"}


@pytest.mark.parametrize("key", sorted(NEW_CHARTS))
def test_new_chart_templates_use_only_provided_values(key):
    c = cases.generate(cases.make_id(NEW_CHARTS[key], "basic", 3))
    facts = next(f for k, f in c.guide if k == key)
    entry = guide.charts()[key]
    texts = [entry[s][lg] for s in ("axes", "what", "read", "record") for lg in ("zh", "en")]
    texts += [entry["action"][s][lg] for s in ("good", "watch", "act") for lg in ("zh", "en")]
    texts += [entry["roles"][r][lg] for r in entry["roles"] for lg in ("zh", "en")]
    texts += [i[lg] for i in entry["legend"] for lg in ("zh", "en")]
    used = {m for t in texts for m in PH.findall(t)}
    assert used <= set(facts.v) | {"finding", "status"}, used - set(facts.v)
    assert "{" not in guide.text(entry["roles"]["RDA"], "en", facts)


def test_real_workflow_answers_follow_the_data():
    seen = {}
    for seed in range(1, 13):
        c = cases.generate(f"insp_split_vs_baseline-A-{seed:05d}")
        v = c.v
        if c.correct["cause"] == "C_INCOMING":
            assert v["prev_ratio"] >= 1.5 and v["adder_ratio"] < 1.3
        else:
            assert c.correct["cause"] == "C_SPLIT" and v["adder_ratio"] >= 1.5 and v["prev_ratio"] < 1.3
        seen.setdefault("split", set()).add(c.correct["cause"])
        r = cases.generate(f"fa_request_recess-I-{seed:05d}")
        assert r.v["routine_max"] < r.v["usl"]  # routine sampling always looks fine
        assert (r.correct["cause"] == "C_SAMPLING_GAP") == (r.v["n_out"] > 0)
        seen.setdefault("recess", set()).add(r.correct["cause"])
        y = cases.generate(f"ye_bin_metro_corr-B-{seed:05d}")
        assert (y.correct["cause"] == "C_PARAM_DRIVES") == (abs(y.v["best_r"]) >= 0.7)
        assert y.correct["cause"] == "C_PARAM_DRIVES" or abs(y.v["best_r"]) < 0.3
        seen.setdefault("bin", set()).add(y.correct["cause"])
    assert all(len(s) == 2 for s in seen.values()), seen  # both outcomes occur
    shares = {lv: cases.generate(cases.make_id("insp_nuisance_recipe", lv, 4)).v["nonvisible_share"] for lv in cases.LEVELS}
    assert shares["basic"] > shares["intermediate"] > shares["advanced"] >= 50
    assert cases.generate("insp_nuisance_recipe-B-00004").v["n_maxout"] >= 2


def test_report_formats_prefill_and_do_not_count_as_content():
    c = cases.generate("fa_request_recess-B-00002")
    tpl = cases.message_template(c, ["zh", "en"])
    assert "【量測結果 Metrology results】" in tpl
    assert not any(ok for _, ok in cases.message_checklist(c, tpl, "en"))


# --------------------------------------------------------------------------- linked issues, builder
@pytest.mark.parametrize("kind", sorted(compose.issue_kinds()))
def test_every_issue_kind_alone(kind):
    k = compose.issue_kinds()[kind]
    step = k["steps"][0]
    settings = {"mode": "linked", "issues": [{"kind": kind, "step": step, "where": compose.where_choices(kind, step)[0],
                                              "size": "large", "start_lot": 20, "sign": 1}]}
    t = compose.save_settings(settings)
    c = cases.generate(cases.make_id(t, "intermediate", 0))
    check_case(c)
    assert c.correct["causes"] == [k["cause"]] and c.question("priority") is None
    assert [q.weight for q in c.questions] == [40, 25, 20, 15]
    if kind == "metro_offset":  # shown by chamber first, then by metrology tool
        groups = [e["group"] for e in c.evidence if e["kind"] == "spc"]
        assert groups == ["chamber_id", "metro_tool_id"]


def test_linked_issues_hide_each_other_and_priority_is_by_urgency():
    settings = {"mode": "linked", "issues": [
        {"kind": "metro_offset", "step": "GATE_OX", "where": "FT02", "size": "large", "start_lot": 18, "sign": 1},
        {"kind": "shift", "step": "GATE_OX", "where": "RTP01-B", "size": "large", "start_lot": 24, "sign": 1}]}
    c = cases.generate(cases.make_id(compose.save_settings(settings), "advanced", 0))
    check_case(c)
    assert set(c.correct["causes"]) == {"C_METRO_OFFSET", "C_CHAMBER_SHIFT"}
    assert c.correct["priority"] == ["I2"] and c.correct["action"] == ["A_VERIFY"]  # the shift risks product
    assert "量測機台偏差會讓很多 chamber 一起 OOC" in c.text("explanation", "zh")
    half = dict(perfect(c), causes=["C_CHAMBER_SHIFT"])
    assert cases.score(c, half)["questions"]["causes"]["points"] == 15  # half the causes, half the points
    # the same settings always build the same case type and replay the same data
    assert compose.save_settings(settings) == c.type


def test_builder_validation():
    bad = [{"mode": "linked", "issues": []},
           {"mode": "linked", "issues": [{"kind": "shift", "step": "WL_LITHO", "where": "x", "size": "large", "start_lot": 1}]},
           {"mode": "linked", "issues": [{"kind": "shift", "step": "GATE_OX", "where": "FT01", "size": "large", "start_lot": 1}]},
           {"mode": "separate", "types": ["spc_chamber_shift"]},
           {"mode": "nope"}]
    for s in bad:
        with pytest.raises(ValueError):
            compose.validate_settings(s)
    with pytest.raises(ValueError):
        cases.parse_id("build_deadbeef-B-00000")  # not built on this PC


def test_random_mixes():
    modes = set()
    for lv in cases.LEVELS:
        for seed in range(1, 6):
            c = cases.generate(cases.make_id("mix", lv, seed))
            check_case(c)
            modes.add(c.spec["settings"]["mode"])
            pri = c.question("priority")
            assert pri is not None and len(pri.accepted()) == 1  # one clear first item
            if c.spec["settings"]["mode"] == "separate":
                assert c.spec["message_format"] == "handover" and len(c.spec["parts"]) >= 2
                assert any(e["kind"] == "header" for e in c.evidence)
    assert modes == {"linked", "separate"}
    a, b = cases.generate("mix-I-00003"), cases.generate("mix-I-00003")
    assert a.correct == b.correct and a.text("brief", "en") == b.text("brief", "en")


def test_separate_handover_scoring_per_problem():
    t = compose.save_settings({"mode": "separate", "types": ["spc_false_alarm", "msa_matching", "insp_nuisance_recipe"]})
    c = cases.generate(cases.make_id(t, "basic", 0))
    check_case(c)
    assert [q.key for q in c.questions][:3] == ["p1_cause", "p1_action", "p1_decision"]
    urg = [compose.urgency_of(cases.generate(pid)) for pid in c.spec["parts"]]
    assert c.correct["priority"] == [f"P{i + 1}" for i, u in enumerate(urg) if u == max(urg)]
    wrong_first = dict(perfect(c), p1_cause=next(o for o in c.options["p1_cause"] if o != c.correct["p1_cause"]))
    assert cases.score(c, wrong_first)["total"] == pytest.approx(100 - 35 / 3, abs=0.1)


# --------------------------------------------------------------------------- your own templates
TPL = {"base": "spc_chamber_shift", "title": {"zh": "夜班 chamber 偏移（我的版本）", "en": ""},
       "brief": {"zh": "{chamber} 的 {param} 從 {start_wafer} 起偏移。{verified}", "en": ""},
       "cause": "C_CHAMBER_SHIFT", "cause_options": ["C_DRIFT", "C_METRO_OFFSET"],
       "action": "U_ACTION", "action_options": ["A_RECORD", "A_RETARGET"],
       "options": {"U_ACTION": {"zh": "先打給值班 EE 確認警報紀錄", "en": "Call the on-duty EE to check the alarm log first"}},
       "decision": "D_HOLD", "decision_options": ["D_RELEASE", "D_SCRAP"], "notify": ["EE", "PE"],
       "message_role": "EE", "message_format": "swr",
       "model_message": {"zh": "【問題／目的】{chamber} 偏移 {shift} {unit}，請查 PM", "en": ""},
       "keypoints": [{"zh": "指出 chamber", "en": "Names the chamber", "any": ["{chamber}"]}],
       "explanation": {"zh": "單一 chamber 偏移。", "en": "A single-chamber shift."}, "urgency": 3}


def test_custom_template_round_trip():
    t = custom.save_template(TPL)
    assert t in cases.case_types("custom") and cases.type_info(t)["domain"] == "custom"
    c = cases.generate(cases.make_id(t, "intermediate", 11))
    check_case(c)
    assert c.option_text("action", "U_ACTION", "en").startswith("Call the on-duty EE")
    assert custom.unknown_placeholders(custom.validate_template(TPL)) == []
    assert custom.unknown_placeholders(custom.validate_template({**TPL, "brief": {"zh": "{nope}", "en": ""}})) == ["nope"]
    t2 = custom.save_template(TPL)  # same title: a new file, never an overwrite
    assert t2 != t and len(custom.load_templates()) == 2
    assert custom.save_template({**TPL, "urgency": 1}, t.removeprefix("my_"), replace=True) == t
    assert custom.load_templates()[t]["urgency"] == 1
    assert custom.delete_template(t2) and t2 not in cases.case_types()
    with pytest.raises(ValueError):
        cases.parse_id(cases.make_id(t2, "basic", 1))


@pytest.mark.parametrize("change, msg", [({"cause_options": ["C_DRIFT"]}, "wrong options"),
                                         ({"message_role": "CEO"}, "message_role"),
                                         ({"base": "nope"}, "base"),
                                         ({"title": {"zh": "", "en": ""}}, "title"),
                                         ({"action": "U_ACTION", "options": {}}, "action")])
def test_custom_template_validation(change, msg):
    with pytest.raises(ValueError, match=msg):
        custom.validate_template({**TPL, **change})


# --------------------------------------------------------------------------- reports and cross study
def test_reports_and_cross_study_handle_every_kind(tmp_path):
    folder = tmp_path / "log"
    t = custom.save_template(TPL)
    b = compose.save_settings({"mode": "linked", "issues": [
        {"kind": "drift", "step": "CAP_HK", "where": "ALD01-A", "size": "large", "start_lot": 12, "sign": 1},
        {"kind": "particles", "step": "TIN_DEP", "where": "CVD02", "size": "large", "start_lot": 30, "sign": 1}]})
    for cid in ("mix-B-00002", cases.make_id(b, "basic", 0), cases.make_id(t, "basic", 5), "ye_bin_metro_corr-I-00003"):
        c = cases.generate(cid)
        ans = perfect(c)
        first = c.questions[0]
        if first.kind == "single":
            ans[first.key] = next(o for o in first.options if o not in first.accepted())
        r = cases.score(c, ans)
        md = cases.report_markdown(c, ans, r, "", "both")
        assert c.id in md and "Who to tell" in md and "{" not in md.split("## 每張圖")[1]
        cases.save_attempt(c, r, md, folder, message="")
    rep = cases.list_reports(folder)
    assert len(rep) == 4 and set(rep["domain"]) >= {"mix", "custom", "request"}
    prof = cases.study_profile(cases.history(folder))
    assert prof["n_detail"] == 4 and "mix" in prof["by_domain"].index and "custom" in prof["by_domain"].index
    assert "priority" in prof["by_question"].columns
    assert prof["msg_missed"] and all(len(k) == 3 for k in prof["msg_missed"])
    assert cases.focus_weights(prof).sum() == pytest.approx(1) and t in cases.focus_weights(prof).index


# --------------------------------------------------------------------------- the page
def test_case_page_multi_builder_and_templates(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path / "imp"))
    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=300)
    at.run()
    at.sidebar.radio(key="nav_page").set_value("Case study 案例練習").run()
    [b for b in at.button if b.key == "case_mix"][0].click().run()
    cid = at.session_state["case_id"]
    assert not at.exception and cid.startswith("mix-")
    c = cases.generate(cid)
    for q in c.questions:
        w = at.radio(key=f"q_{q.key}_{cid}") if q.kind == "single" else at.multiselect(key=f"q_{q.key}_{cid}")
        w.set_value(q.accepted()[0] if q.kind == "single" else list(q.correct))
    at.text_area(key=f"q_msg_{cid}").set_value(c.text("model_message", "zh"))
    [b for b in at.button if "Submit" in b.label][0].click().run()
    assert not at.exception and [m.value for m in at.metric if m.label.startswith("總分")] == ["100 / 100"]
    [b for b in at.button if b.key == f"case_save_{cid}"][0].click().run()
    assert list((tmp_path / "cases").glob(f"{cid}_*.md"))

    # builder: two linked issues
    at.radio(key="cb_mode").set_value("linked").run()
    at.selectbox(key="cb_kind_0").set_value("metro_offset").run()
    at.selectbox(key="cb_kind_1").set_value("shift").run()
    [b for b in at.button if b.key == "cb_build"][0].click().run()
    assert not at.exception and at.session_state["case_id"].startswith("build_")
    assert len(list((tmp_path / "cases" / "built").glob("build_*.json"))) == 1

    # template: write, save, practise
    k = "tp___new__"
    at.text_input(key=f"{k}_title_zh").set_value("我的練習案例")
    at.text_area(key=f"{k}_brief_zh").set_value("{chamber} 偏移了")
    for q, wrong in (("cause", ["C_DRIFT", "C_METRO_OFFSET"]), ("action", ["A_RECORD", "A_RETARGET"]),
                     ("decision", ["D_RELEASE", "D_SCRAP"])):
        at.multiselect(key=f"{k}_{q}_wrong").set_value(wrong)
    at.text_area(key=f"{k}_model_zh").set_value("請查 {chamber}")
    at.text_area(key=f"{k}_why_zh").set_value("練習用")
    [b for b in at.button if b.key == f"{k}_save"][0].click().run()
    assert not at.exception and len(custom.load_templates()) == 1
    t = next(iter(custom.load_templates()))
    at.selectbox(key="tp_pick").set_value(t).run()
    [b for b in at.button if b.key == f"tp_{t}_play"][0].click().run()
    assert not at.exception and at.session_state["case_id"].startswith(t)

    # reports page lists the multi-issue report
    at.sidebar.radio(key="nav_page").set_value("My case reports 我的案例報告").run()
    assert not at.exception and [m.value for m in at.metric if m.label.startswith("報告數")] == ["1"]


# --------------------------------------------------------------------------- the example template
def test_template_names_are_cut_at_word_boundaries():
    assert custom.slugify("Night shift: gate-oxide chamber shift, yield dropping (example)") == "night_shift_gate_oxide_chamber_shift"
    assert custom.slugify("短中文標題") == "case" and custom.slugify("a" * 60) == "a" * 40


def test_example_template_is_valid_and_complete():
    ex = custom.EXAMPLE
    clean = custom.validate_template(ex)
    assert custom.unknown_placeholders(clean) == []  # every {value} exists in its data pattern
    assert clean["action"] == "U_ACTION" and ex["options"]["U_ACTION"]["zh"] and ex["options"]["U_ACTION"]["en"]
    t = custom.save_template(ex)
    for level in cases.LEVELS:
        c = cases.generate(cases.make_id(t, level, 3))
        check_case(c)
        assert "{" not in c.option_text("action", "U_ACTION", "en")  # own answer text is shown as written
    assert not re.search(r"micron|美光", str(ex), re.I)


def test_example_button_fills_the_form_and_saves(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path / "imp"))
    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=300)
    at.run()
    at.sidebar.radio(key="nav_page").set_value("Case study 案例練習").run()
    assert at.text_input(key="tp___new___title_zh").value == ""  # an empty form first
    [b for b in at.button if b.key == "tp_example"][0].click().run()
    k = f"tp___new___v{at.session_state['tp_ver']}"  # the fields are redrawn under new keys
    assert not at.exception and at.selectbox(key="tp_pick").value == "__new__"
    assert at.text_input(key=f"{k}_title_zh").value == custom.EXAMPLE["title"]["zh"]
    assert at.selectbox(key=f"{k}_base").value == "fab_chamber_excursion"
    assert at.selectbox(key=f"{k}_action").value == "U_ACTION"
    assert at.text_input(key=f"{k}_action_own_en").value == custom.EXAMPLE["options"]["U_ACTION"]["en"]
    assert at.multiselect(key=f"{k}_cause_wrong").value == custom.EXAMPLE["cause_options"]
    assert at.multiselect(key=f"{k}_notify").value == custom.EXAMPLE["notify"]
    at.text_input(key=f"{k}_title_zh").set_value("我改過的範例").run()  # edit it
    [b for b in at.button if b.key == f"{k}_save"][0].click().run()
    assert not at.exception and len(custom.load_templates()) == 1
    saved = next(iter(custom.load_templates().values()))
    assert saved["title"]["zh"] == "我改過的範例" and saved["base"] == "fab_chamber_excursion"
    assert at.selectbox(key="tp_pick").value == next(iter(custom.load_templates()))  # opens the saved template
    at.selectbox(key="tp_pick").set_value("__new__").run()  # a new template after saving starts blank again
    assert at.text_input(key=f"tp___new___v{at.session_state['tp_ver']}_title_zh").value == ""
