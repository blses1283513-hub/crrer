"""The metrology map: the merged tree is complete and consistent, the "Which technique?" chooser follows the tool
facts, GOF is reported by the thin-film fit, the two technique cases behave, and the pages render."""

import re
from pathlib import Path

import numpy as np
import pytest

from metro_toolkit import cases
from metro_toolkit.cases import tutor
from metro_toolkit.guide import metrology as mt

APP = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"


def test_tree_merges_and_every_reference_is_defined():
    assert mt.available() and len(mt._files()) == 4
    params, tools = mt.parameters(), mt.tools()
    assert {"cd", "profile", "registration", "thickness", "optical", "composition", "stress",
            "dopant-concentration", "implant-damage"} <= set(params)
    for pid in params:
        assert mt.tools_for(pid), pid
        assert set(mt.tools_for(pid)) <= set(tools), pid
    for tid, t in tools.items():
        assert mt.parameters_of(tid), f"{tid} measures nothing"
        for f in ("principle", "strengths", "limits"):
            assert t.get(f, {}).get("zh") and t.get(f, {}).get("en"), (tid, f)
        assert str(t.get("destructive", "no")) in mt.DESTRUCTIVE
        assert set(t.get("location") or []) <= set(mt.LOCATIONS), tid
        if t.get("thickness_nm"):
            lo, hi = t["thickness_nm"]
            assert 0 < lo < hi, tid
    cats = {c["id"] for c in mt.tree()["categories"]}
    for r in mt.tree()["relations"]:
        assert {r.get("from"), r.get("to")} <= set(tools) | set(params) | cats, r


def test_notes_carry_verdicts_and_no_company_names():
    cl = mt.claims()
    assert len(cl) >= 100
    assert {c["verdict"] for c in cl} <= {"verified", "corrected", "unresolved"}
    assert all(c.get("claim") for c in cl)
    assert all(c["fix"].get("zh") and c["fix"].get("en") for c in cl if c["verdict"] != "verified" and c.get("fix"))
    assert not re.search(r"micron|美光", str(mt.tree()), re.I)


def test_chooser_follows_the_tool_facts():
    fits, out = mt.choose("thickness", 500, "metal")
    kept = {f["tool"] for f in fits}
    assert {"eddy-current", "xrf"} <= kept and not {"reflectometry", "ellipsometry", "xrr", "xps"} & kept
    fits, out = mt.choose("thickness", 100, "transparent", no_contact=True)
    assert "four-point-probe" not in {f["tool"] for f in fits}
    assert any(e["tool"] == "four-point-probe" and any("touches" in w["en"] for w in e["why"]) for e in out)
    fits, _ = mt.choose("thickness", 2, "transparent")
    assert "ellipsometry" in {f["tool"] for f in fits}
    fits, _ = mt.choose("cd", non_destructive=True, inline=True)
    assert "xsem-tem" not in {f["tool"] for f in fits}
    # every candidate is either kept or excluded with a reason
    for pid in mt.parameters():
        fits, out = mt.choose(pid, 50, "transparent", "in_die", True, True, True, True)
        assert {f["tool"] for f in fits} | {e["tool"] for e in out} == set(mt.tools_for(pid))
        assert all(e["why"] for e in out)
    assert mt.search("stoney") == ["wafer-curvature"] or "wafer-curvature" in mt.search("stoney")


def test_fit_reports_gof():
    from metro_toolkit.metrology.thinfilm.fitting import _gof

    assert _gof(np.array([1.0, 2.0, 3.0]), np.zeros(3)) == pytest.approx(1.0)
    assert _gof(np.array([1.0, 2.0, 3.0]), np.array([1.0, -1.0, 0.0])) == pytest.approx(0.0)
    c = cases.generate("film_gof_reject-B-00002")
    assert 0 <= c.v["gof"] < c.v["limit"] <= 1  # the rejected fit falls below the recipe limit


@pytest.mark.parametrize("case_type", ["film_gof_reject", "implant_rs_monitor"])
def test_technique_cases_follow_their_variant(case_type):
    seen = set()
    for lv in cases.LEVELS:
        for s in range(10):
            c = cases.generate(cases.make_id(case_type, lv, s))
            assert c.correct["cause"] in c.options["cause"] and c.correct["action"] in c.options["action"]
            seen.add(c.correct["cause"])
    expect = {"film_gof_reject": {"C_MISSING_LAYER", "C_WRONG_ORDER"},
              "implant_rs_monitor": {"C_DOSE_DRIFT", "C_ANNEAL_DRIFT"}}[case_type]
    assert seen == expect


def test_tutor_knows_the_techniques():
    c = cases.generate("film_gof_reject-B-00001")
    ans = {k: c.correct[k] for k in ("cause", "action", "decision")} | {"notify": list(c.correct["notify"]), "message": ""}
    system = tutor.system_prompt(c, ans, cases.score(c, ans), "en")
    assert "<techniques>" in system and "thickness: Reflectometry, Ellipsometry" in system


def test_metrology_page_renders():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP), default_timeout=300)
    at.run()
    at.sidebar.radio(key="nav_page").set_value("量測地圖 Metrology map").run()
    assert not at.exception
    assert len(at.tabs) >= 4
    at.sidebar.radio(key="nav_page").set_value("Recipe studies").run()
    assert not at.exception
    assert any("thickness technique" in e.label for e in at.expander)
