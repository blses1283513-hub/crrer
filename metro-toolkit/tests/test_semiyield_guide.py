"""Hover-guide for SemiYield: explanation file is well formed; launcher attaches tooltips if SemiYield is present."""

import json
import os
import re
from pathlib import Path

import pytest
import yaml

GUIDE = Path(__file__).resolve().parents[1] / "semiyield_guide"
RULES = yaml.safe_load((GUIDE / "explanations.yaml").read_text(encoding="utf-8"))


def test_widget_entries_are_complete():
    seen = set()
    for w in RULES["widgets"]:
        assert w["label"] and w["help"].strip(), w
        key = (w["label"], w.get("min"), w.get("max"), tuple(w.get("options", [])))
        assert key not in seen, f"duplicate rule {key}"
        seen.add(key)
    # labels used on several tabs must be disambiguated, or the first rule would shadow the others
    for label in ("Temperature (C)", "Material"):
        rules = [w for w in RULES["widgets"] if w["label"] == label]
        assert len(rules) >= 2
        assert all(("min" in r) or ("options" in r) or r is rules[-1] for r in rules)


def test_chart_entries_are_valid():
    for c in RULES["charts"]:
        re.compile(c["match"])
        for spec in c.get("traces", []):
            re.compile(spec["name"])
            assert "<extra>" in spec["hover"] and "%{" in spec["hover"]
        for spec in c.get("lines", []):
            re.compile(spec["text"])
            assert "%{" in spec["hover"]


def test_every_simulation_and_spc_input_is_covered():
    labels = {w["label"] for w in RULES["widgets"]}
    for needed in ("Temperature (C)", "Atmosphere", "Ion species", "Energy (keV)", "Dose (cm^-2)", "Etch mode",
                   "Process type", "Pressure (Torr)", "Drift rate", "Aging factor", "USL", "LSL", "Cpk", "Ppk"):
        assert needed in labels


def _semiyield() -> Path | None:
    for c in (os.environ.get("SEMIYIELD_DIR"), GUIDE.parents[2] / "semiyield"):
        if c and (Path(c) / "dashboard" / "app.py").exists():
            return Path(c)
    return None


@pytest.mark.skipif(_semiyield() is None, reason="SemiYield not found (set SEMIYIELD_DIR to run this test)")
def test_launcher_attaches_tooltips_and_hover(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("SEMIYIELD_DIR", str(_semiyield()))
    at = AppTest.from_file(str(GUIDE / "launch_semiyield.py"), default_timeout=180)
    at.run()
    assert not at.exception
    temp = [w for w in at.slider if w.label == "Temperature (C)"]
    assert len(temp) == 3 and all(w.help for w in temp)
    assert len({w.help for w in temp}) == 3  # oxidation / etch / deposition get different text
    assert all(m.help for m in at.metric)
    for el in at.get("plotly_chart"):
        spec = json.loads(el.proto.spec)
        assert all(d.get("hovertemplate") for d in spec["data"])

    at.sidebar.radio[0].set_value("Data Generator").run()
    at.button[0].click().run()
    at.sidebar.radio[0].set_value("SPC Dashboard").run()
    assert not at.exception
    spec = json.loads(at.get("plotly_chart")[0].proto.spec)
    names = [d.get("name") for d in spec["data"]]
    assert {"CL", "UCL", "LCL"} <= set(names)
    assert all(m.help for m in at.metric)
