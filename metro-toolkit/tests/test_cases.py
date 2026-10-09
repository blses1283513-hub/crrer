"""Case study practice: every case type generates at every level with a reachable correct answer, the data really
shows the intended situation, scoring and reports work, and the page runs end to end."""

import re
from pathlib import Path

import pytest

from metro_toolkit import cases
from metro_toolkit.guide import meta

PH = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
LIB = cases.library()


@pytest.mark.parametrize("case_type", sorted(LIB["cases"]))
def test_every_case_type_generates_completely(case_type):
    spec = LIB["cases"][case_type]
    pools = LIB["pools"]
    for q, pool in (("cause", "causes"), ("action", "actions"), ("decision", "decisions")):
        assert all(o in pools[pool] for o in spec[f"{q}_options"] + [spec[q]]), q
    assert set(spec["notify"]) <= set(meta()["roles"]) and spec["message_role"] in meta()["roles"]
    for level in cases.LEVELS:
        c = cases.generate(cases.make_id(case_type, level, 7))
        for q in ("cause", "action", "decision"):
            assert c.correct[q] in c.options[q] and len(c.options[q]) >= 3
        texts = [spec[k][lg] for k in ("title", "brief", "model_message", "explanation") for lg in ("zh", "en")]
        texts += [t for kp in spec["keypoints"] for t in kp["any"]]
        assert {m for t in texts for m in PH.findall(t)} <= set(c.v), level
        for lg in ("zh", "en"):
            for k in ("brief", "model_message", "explanation"):
                assert "{" not in c.text(k, lg) and c.text(k, lg).strip()
        assert c.evidence and c.guide
        assert not re.search(r"micron|美光", str(spec), re.I)


def test_ids_are_reproducible():
    cid = cases.make_id("spc_chamber_shift", "intermediate", 4217)
    assert cid == "spc_chamber_shift-I-04217" and cases.parse_id(cid) == ("spc_chamber_shift", "intermediate", 4217)
    a, b = cases.generate(cid), cases.generate(cid)
    assert a.v == b.v and a.options == b.options and a.correct == b.correct
    with pytest.raises(ValueError):
        cases.parse_id("no_such_case-B-00001")
    r = cases.random_case(3, domain="msa", level="advanced")
    assert r.spec["domain"] == "msa" and r.level == "advanced"


def test_cases_show_the_intended_situation():
    g = lambda cid: cases.generate(cid)  # noqa: E731
    c = g("spc_cpk_off_center-B-00001")
    assert c.guide[0][1].status == "watch" and c.v["cp"] > c.v["cpk"] and 1.0 <= c.v["cpk"] < 1.33
    c = g("spc_false_alarm-B-00002")
    assert c.guide[0][1].v["n_ooc"] == 1
    c = g("spc_chamber_shift-B-00003")
    assert c.v["chamber"] in c.guide[0][1].v["groups_ooc"]
    c = g("msa_narrow_parts-B-00004")
    assert c.v["grr"] > 30 and c.v["pt"] < 10
    c = g("msa_repeatability-B-00005")
    assert c.v["repeat"] > c.v["reprod"] and c.v["grr"] > 30
    c = g("msa_reproducibility-B-00005")
    assert c.v["reprod"] > c.v["repeat"]
    for seed in range(1, 8):
        c = g(f"study_technique_choice-I-{seed:05d}")
        thin = c.v["t0"] < 10
        assert (c.correct["cause"] == "C_TECH_REFL") == thin
        assert (c.v["pt_r"] > 30) == thin and c.v["pt_s"] < 10
    c = g("doe_curvature_missed-B-00006")
    assert c.v["curv_p"] < 0.05
    c = g("doe_edge_optimum-B-00007")
    assert c.v["t_best"] in (pytest.approx(c.v["t_low"], abs=1.0), pytest.approx(c.v["t_high"], abs=1.0))
    c = g("wafer_bad_site-B-00008")
    assert abs(c.v["site_value"] - c.v["neighbour_mean"]) > 0.6 * c.v["range"]  # one site dominates the range
    c = g("fab_metro_offset-B-00009")
    assert c.v["impact"] == 0.0
    c = g("fab_particle_event-B-00010")
    assert c.v["impact"] < 0
    for cid in ("fab_chamber_excursion-B-00001", "fab_chamber_excursion-A-00006"):
        c = g(cid)  # pushed away from the window centre: a real but not absurd yield loss
        assert -12 <= c.v["impact"] <= -2 and c.v["chamber"] in c.guide[0][1].v["groups_ooc"]


def test_verified_measurement_changes_the_first_action():
    seen = set()
    for seed in range(30):
        c = cases.generate(f"spc_chamber_shift-A-{seed:05d}")
        verified = "已確認" in c.text("brief", "zh")
        assert c.correct["action"] == ("A_HOLD_INHIBIT" if verified else "A_VERIFY")
        seen.add(verified)
    assert seen == {True, False}


def test_scoring_and_checklist():
    c = cases.generate("spc_metro_offset-I-01234")
    perfect = {k: c.correct[k] for k in ("cause", "action", "decision")} | {"notify": c.correct["notify"]}
    assert cases.score(c, perfect)["total"] == 100
    half = dict(perfect, notify=c.correct["notify"][:1])
    r = cases.score(c, half)
    assert r["questions"]["notify"]["points"] == pytest.approx(15 / len(c.correct["notify"]), abs=0.1)
    assert cases.score(c, dict(perfect, cause="C_DRIFT"))["total"] == 60
    quiet = cases.generate("spc_false_alarm-B-00002")
    assert quiet.correct["notify"] == [] and cases.score(quiet, {"notify": []})["questions"]["notify"]["points"] == 15
    good = c.text("model_message", "zh")
    assert all(ok for _, ok in cases.message_checklist(c, good, "zh"))
    assert not any(ok for _, ok in cases.message_checklist(c, "ok", "zh"))


def test_report_and_history(tmp_path):
    c = cases.generate("wafer_edge_roll-B-00007")
    answers = {"cause": c.correct["cause"], "action": "A_RECORD", "decision": c.correct["decision"], "notify": ["EE"]}
    result = cases.score(c, answers)
    md = cases.report_markdown(c, answers, result, "edge ring 磨耗", "zh")
    assert c.id in md and "為什麼" in md and "✗" in md and "合成練習資料" in md
    for head in ("好訊息的要點", "分數紀錄", "代表什麼與洞察", "這份資料的判讀", "下一步", "跟誰說", "目前狀態"):
        assert head in md, head
    assert all(cases.role_name(r, "zh") in md for r in meta()["roles"])  # a message for every role
    assert "{" not in md.split("## 每張圖")[1]  # every template filled with the case's numbers
    first = cases.save_attempt(c, result, md, tmp_path)
    second = cases.save_attempt(c, result, md, tmp_path)
    assert first.exists() and second.exists() and first != second  # one file per attempt
    hist = cases.history(tmp_path)
    assert len(hist) == 2 and hist["score"].iloc[0] == result["total"] and hist["file"].iloc[1] == second.name
    md2 = cases.report_markdown(c, answers, result, "", "zh", past=hist)
    assert "案例數: 3" in md2 and md2.count(c.id) >= 4
    en = cases.report_markdown(c, answers, result, "", "en")
    assert "Why" in en and "Who to tell" in en and "Score history" in en and "為什麼" not in en
    both = cases.report_markdown(c, answers, result, "", "both")
    assert "為什麼 · Why" in both and "Insight" in both and c.text("model_message", "en") in both


def test_case_study_page(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path / "imp"))
    monkeypatch.setenv("METRO_CASES_PATH", str(tmp_path / "cases"))
    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=300)
    at.run()
    at.sidebar.radio(key="nav_page").set_value("Case study 案例練習").run()
    [b for b in at.button if b.key == "case_new"][0].click().run()
    assert not at.exception and at.session_state["case_id"]
    cid = "spc_chamber_shift-B-00003"
    at.text_input(key="case_replay_id").set_value(cid).run()
    [b for b in at.button if b.key == "case_replay"][0].click().run()
    c = cases.generate(cid)
    for q in ("cause", "action", "decision"):
        at.radio(key=f"q_{q}_{cid}").set_value(c.correct[q])
    at.multiselect(key=f"q_notify_{cid}").set_value(c.correct["notify"])
    at.text_area(key=f"q_msg_{cid}").set_value(c.text("model_message", "zh"))
    [b for b in at.button if "Submit" in b.label][0].click().run()
    assert not at.exception
    assert [m.value for m in at.metric if m.label.startswith("總分")] == ["100 / 100"]
    assert any("怎麼讀這張圖" in e.label for e in at.expander)
    [b for b in at.button if b.key == f"case_save_{cid}"][0].click().run()
    [b for b in at.button if b.key == f"case_save_{cid}"][0].click().run()  # saving again: a second file
    files = sorted((tmp_path / "cases").glob(f"{cid}_*.md"))
    assert len(files) == 2 and not at.exception
    for f in files:  # the same attempt is counted once, never twice, in the score history
        md = f.read_text(encoding="utf-8")
        assert "案例數 · Cases: 1" in md and "跟誰說 · Who to tell" in md


def _attempts(folder, wrong_spc=True):
    """Save four attempts: two SPC chamber-shift cases answered wrongly (cause, notify), two right ones."""
    for cid, bad in (("spc_chamber_shift-B-00001", wrong_spc), ("spc_chamber_shift-I-00002", wrong_spc),
                     ("wafer_tilt-B-00003", False), ("msa_matching-B-00004", False)):
        c = cases.generate(cid)
        ans = {k: c.correct[k] for k in ("cause", "action", "decision")} | {"notify": c.correct["notify"]}
        if bad:
            ans["cause"] = next(o for o in c.options["cause"] if o != c.correct["cause"])
            ans["notify"] = ["EE"]
        r = cases.score(c, ans)
        cases.save_attempt(c, r, cases.report_markdown(c, ans, r, "ok", "both"), folder, message="ok")


def test_list_reports_and_cross_study(tmp_path):
    _attempts(tmp_path)
    (tmp_path / "wafer_tilt-B-00009.md").write_text("# old save\n分數 **55 / 100**", encoding="utf-8")  # pre-detail
    (tmp_path / "notes.md").write_text("not a report", encoding="utf-8")
    rep = cases.list_reports(tmp_path)
    assert len(rep) == 5 and rep["time"].is_monotonic_decreasing
    assert rep.set_index("case").loc["wafer_tilt-B-00009", "score"] == 55
    assert set(cases.search_reports(rep, "OLD SAVE")["case"]) == {"wafer_tilt-B-00009"}

    hist = cases.history(tmp_path)
    prof = cases.study_profile(hist)
    assert prof["n_detail"] == 4
    assert prof["by_question"].loc["spc", "cause"] == 0 and prof["by_question"].loc["wafer", "cause"] == 100
    assert prof["missed_roles"] and ("cause", "C_CHAMBER_SHIFT") == next(iter(prof["wrong"]))[:2]
    assert prof["by_domain"].loc["film", "attempts"] == 0 and prof["msg_missed"]

    w = cases.focus_weights(prof)
    assert w.sum() == pytest.approx(1) and w.idxmax() == "spc_chamber_shift"
    assert w[[k for k in w.index if k.startswith("spc")]].sum() > 0.4  # the weak area gets the most practice
    assert w["wafer_tilt"] < w["stack_float_n_thin"]  # mastered < never tried
    assert cases.focus_level(prof, "spc_chamber_shift") == "basic"  # poor score: one level down from intermediate
    assert cases.focus_level(prof, "wafer_tilt") == "intermediate"  # good score: one level up
    assert cases.focus_case(hist, 5).id == cases.focus_case(hist, 5).id
    assert cases.study_profile(cases.history(tmp_path / "empty"))["n_detail"] == 0  # empty log works


def test_reports_page(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path / "imp"))
    monkeypatch.setenv("METRO_CASES_PATH", str(tmp_path / "cases"))
    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=300)
    at.run()
    at.sidebar.radio(key="nav_page").set_value("My case reports 我的案例報告").run()
    assert not at.exception and at.info  # nothing saved yet
    _attempts(tmp_path / "cases")
    at.run()
    assert not at.exception
    assert [m.value for m in at.metric if m.label.startswith("報告數")] == ["4"]
    assert any("最弱的範圍" in m.value for m in at.markdown)  # cross study recommendations
    at.text_input(key="rep_search").set_value("msa_matching").run()
    assert at.selectbox(key="rep_open").options == [next(o for o in at.selectbox(key="rep_open").options)]
    at.text_input(key="rep_search").set_value("").run()
    [b for b in at.button if b.key == "rep_retry"][0].click().run()
    assert at.sidebar.radio(key="nav_page").value == "Case study 案例練習" and not at.exception
    assert at.session_state["case_id"] in {f.split("_2")[0] for f in cases.list_reports(tmp_path / "cases")["file"]}
    at.sidebar.radio(key="nav_page").set_value("My case reports 我的案例報告").run()
    [b for b in at.button if b.key == "rep_focus"][0].click().run()
    assert at.sidebar.radio(key="nav_page").value == "Case study 案例練習" and not at.exception
    at.selectbox(key="case_domain").set_value("focus").run()
    [b for b in at.button if b.key == "case_new"][0].click().run()
    assert not at.exception and at.session_state["case_id"]
