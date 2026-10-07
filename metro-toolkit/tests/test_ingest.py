"""Data import: readers, column guessing, units, both layouts, SECOM, checks, saving, and the dashboard."""

import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from metro_toolkit.ingest import (
    ImportSpec, build_long, detect_layout, excel_sheets, guess_mapping, guess_unit, list_datasets, list_profiles,
    load_dataset, load_profile, parameter_table, quality_report, read_secom, read_table, save_dataset, save_profile,
    spec_table, wafer_table,
)

SITES = [(0, 0), (70, 0), (-70, 0), (0, 70), (0, -70), (140, 0), (-140, 0), (0, 140), (0, -140)]


def messy_long(n_lots=4, wafers=5, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for lot in range(n_lots):
        for w in range(1, wafers + 1):
            for site, (x, y) in enumerate(SITES, 1):
                rows.append({"Lot ID": f"A{lot:03d}", "WaferID": f"A{lot:03d}-{w:02d}",
                             "Meas Time": pd.Timestamp("2026-09-01") + pd.Timedelta(hours=lot * 6 + w),
                             "EQP": f"CVD0{1 + lot % 2}", "Chamber": "A" if w % 2 else "B", "Item": "OX_THK",
                             "Result": 1000 + rng.normal(0, 8) - 20 * (x * x + y * y) / 140 ** 2, "Unit": "A",
                             "Site No": site, "X (mm)": x, "Y (mm)": y, "Spec Low": 970, "Spec High": 1030})
    df = pd.DataFrame(rows)
    df["Result"] = df["Result"].astype(object)
    df.loc[5, "Result"] = "---"
    df.loc[11, "Result"] = np.nan
    return pd.concat([df, df.iloc[[3]]], ignore_index=True)  # one duplicate


def wide_table(n=30, seed=1) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "批號": np.repeat([f"L{i}" for i in range(n // 2)], 2), "晶圓": [f"W{i:03d}" for i in range(n)],
        "日期": pd.date_range("2026-08-01", periods=n, freq="D").strftime("%Y/%m/%d"),
        "THK_A": rng.normal(1200, 10, n), "CD_nm": rng.normal(45, 0.5, n), "RS": rng.normal(75, 1, n),
        "row_index": np.arange(n)})


def auto(raw):
    m = guess_mapping(raw.columns)
    layout = detect_layout(m)
    return ImportSpec(layout, m, parameter_table(raw, m, layout).to_dict("records"))


# ---------------------------------------------------------------- readers
def test_reads_excel_big5_semicolon_and_whitespace(tmp_path):
    messy_long().to_excel(tmp_path / "a.xlsx", index=False, sheet_name="THK")
    assert excel_sheets(tmp_path / "a.xlsx") == ["THK"]
    assert len(read_table(tmp_path / "a.xlsx")) == 181

    wide_table().to_csv(tmp_path / "b.csv", index=False, encoding="cp950")
    b = read_table(tmp_path / "b.csv")
    assert b.attrs["encoding"] in ("cp950", "big5") and "批號" in b.columns

    wide_table().to_csv(tmp_path / "c.csv", index=False, sep=";")
    assert read_table(tmp_path / "c.csv").attrs["delimiter"] == ";"

    np.savetxt(tmp_path / "d.data", np.ones((5, 4)))
    d = read_table(tmp_path / "d.data")
    assert d.shape == (5, 4) and d.attrs["delimiter"] == "whitespace"


def test_secom_reader(tmp_path):
    rng = np.random.default_rng(2)
    x = rng.normal(0, 1, (40, 12))
    x[rng.random(x.shape) < 0.05] = np.nan
    (tmp_path / "secom.data").write_text("\n".join(" ".join("NaN" if np.isnan(v) else f"{v:.4f}" for v in r) for r in x))
    labels = [f'{1 if i % 7 == 0 else -1} "{(pd.Timestamp("2008-07-19 11:55") + pd.Timedelta(hours=9 * i)):%d/%m/%Y %H:%M:%S}"'
              for i in range(40)]
    (tmp_path / "labels.data").write_text("\n".join(labels))
    df = read_secom(tmp_path / "secom.data", tmp_path / "labels.data")
    assert len(df) == 40 and df["fail"].sum() == 6 and df["timestamp"].notna().all()
    assert df["timestamp"].iloc[0] == pd.Timestamp("2008-07-19 11:55")
    assert "sensor_012" in df.columns
    with pytest.raises(ValueError):
        (tmp_path / "short.data").write_text("\n".join(labels[:10]))
        read_secom(tmp_path / "secom.data", tmp_path / "short.data")


# ---------------------------------------------------------------- mapping
def test_guess_mapping_and_units():
    m = guess_mapping(messy_long().columns)
    assert m["lot_id"] == "Lot ID" and m["wafer_id"] == "WaferID" and m["timestamp"] == "Meas Time"
    assert m["x"] == "X (mm)" and m["tool_id"] == "EQP" and m["lsl"] == "Spec Low"
    assert detect_layout(m) == "long"
    w = guess_mapping(wide_table().columns)
    assert w == {"timestamp": "日期", "lot_id": "批號", "wafer_id": "晶圓"} and detect_layout(w) == "wide"
    assert [guess_unit(c) for c in ("THK_A", "CD (nm)", "Depth_um", "RS", "AREA")] == ["Å", "nm", "µm", "", ""]


def test_wide_parameter_table_excludes_counters():
    pt = parameter_table(wide_table(), guess_mapping(wide_table().columns), "wide")
    assert list(pt["source"]) == ["THK_A", "CD_nm", "RS"]
    seq = wide_table().assign(seq=np.arange(30)).rename(columns={"seq": "Seq"})
    pt2 = parameter_table(seq, guess_mapping(seq.columns), "wide")
    assert not pt2.set_index("source").loc["Seq", "include"]  # strictly increasing integers look like a counter


# ---------------------------------------------------------------- conversion + checks
def test_long_conversion_units_specs_and_report():
    raw = messy_long()
    long, notes = build_long(raw, auto(raw))
    assert long["unit"].unique().tolist() == ["nm"]
    assert long["value"].between(95, 102).all()  # Å -> nm
    assert spec_table(long) == {"OX_THK": {"lsl": 97.0, "usl": 103.0}}
    assert len(long) == 181 - 2  # '---' and blank removed
    rep = quality_report(long, notes)
    msgs = " ".join(i["message"] for i in rep["issues"])
    assert "重複" in msgs and "非數值" in msgs and "nm" in msgs
    assert rep["summary"]["wafers"] == 20 and rep["summary"]["has_site_xy"]


def test_wide_conversion_and_wafer_table():
    raw = wide_table().drop(columns=["晶圓"])
    long, notes = build_long(raw, auto(raw))
    assert long["wafer_id"].str.startswith("W0").all()
    assert any("晶圓編號" in n["message"] for n in notes)
    assert set(long["parameter"]) == {"THK_A", "CD_nm", "RS"}
    assert long.loc[long.parameter == "THK_A", "value"].mean() == pytest.approx(120, abs=1)
    wt = wafer_table(long)
    assert len(wt) == 30 and {"lot_sequence", "wafer_sequence", "THK_A", "RS"} <= set(wt.columns)
    assert wt["lot_sequence"].max() == 14


def test_errors_are_reported():
    raw = messy_long()
    spec = auto(raw)
    spec.mapping.pop("wafer_id")
    with pytest.raises(ValueError):
        build_long(raw, spec)
    bad = messy_long().assign(**{"Spec Low": 1100})
    rep = quality_report(*build_long(bad, auto(bad)))
    assert any(i["level"] == "error" and "規格" in i["message"] for i in rep["issues"])
    mixed = messy_long()
    mixed.loc[:20, "Unit"] = "um"
    s = auto(mixed)
    s.to_nm = False
    rep = quality_report(*build_long(mixed, s))
    assert any(i["level"] == "error" and "單位" in i["message"] for i in rep["issues"])


# ---------------------------------------------------------------- storage
def test_save_and_load_roundtrip(tmp_path):
    raw = messy_long()
    spec = auto(raw)
    long, _ = build_long(raw, spec)
    paths = save_dataset("Fab A / OX run", long, tmp_path)
    assert paths["long"].name == "Fab_A_OX_run.csv" and paths["wafer"].exists()
    assert json.loads(paths["specs"].read_text(encoding="utf-8"))["OX_THK"]["usl"] == 103.0
    assert list_datasets(tmp_path) == ["Fab_A_OX_run"]
    back = load_dataset("Fab_A_OX_run", tmp_path)
    assert len(back) == len(long) and pd.api.types.is_datetime64_any_dtype(back["timestamp"])
    save_profile("CVD export", spec, tmp_path)
    assert list_profiles(tmp_path) == ["CVD_export"]
    assert load_profile("CVD_export", tmp_path).mapping == spec.mapping


# ---------------------------------------------------------------- dashboard on imported data
def _dashboard(tmp_path, monkeypatch, dataset):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path))
    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=120)
    at.session_state["dataset"] = dataset
    return at


def test_dashboard_pages_use_imported_long_data(tmp_path, monkeypatch):
    raw = messy_long(n_lots=6)
    save_dataset("ox", build_long(raw, auto(raw))[0], tmp_path)
    at = _dashboard(tmp_path, monkeypatch, "ox")
    at.run()
    for page in ("Wafer map", "SPC"):
        at.sidebar.radio[0].set_value(page).run()
        assert not at.exception, page
        assert at.sidebar.selectbox[0].value == "匯入：ox"
    assert at.get("plotly_chart")


def test_dashboard_wide_data_has_no_wafer_map_but_spc_works(tmp_path, monkeypatch):
    raw = wide_table()
    save_dataset("wide", build_long(raw, auto(raw))[0], tmp_path)
    at = _dashboard(tmp_path, monkeypatch, "wide")
    at.run()
    at.sidebar.radio[0].set_value("Wafer map").run()
    assert not at.exception and any("座標" in i.value for i in at.info)
    at.sidebar.radio[0].set_value("SPC").run()
    assert not at.exception and at.get("plotly_chart")


def test_import_page_renders(tmp_path, monkeypatch):
    at = _dashboard(tmp_path, monkeypatch, None)
    at.run()
    assert not at.exception and at.header[0].value.startswith("Data import")


# ---------------------------------------------------------------- SemiYield link
GUIDE = Path(__file__).resolve().parents[1] / "semiyield_guide"


def _semiyield():
    for c in (os.environ.get("SEMIYIELD_DIR"), GUIDE.parents[2] / "semiyield"):
        if c and (Path(c) / "dashboard" / "app.py").exists():
            return str(c)
    return None


@pytest.mark.skipif(_semiyield() is None, reason="SemiYield not found (set SEMIYIELD_DIR)")
def test_semiyield_launcher_loads_imported_data(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest

    rng = np.random.default_rng(5)
    n = 60
    raw = pd.DataFrame({"lot": np.repeat([f"L{i:02d}" for i in range(12)], 5), "wafer": [f"W{i:03d}" for i in range(n)],
                        "time": pd.date_range("2026-07-01", periods=n, freq="h"),
                        "gate_oxide_thickness": rng.normal(8.6, 0.2, n), "poly_cd": rng.normal(90, 2, n),
                        "yield": np.clip(rng.normal(0.92, 0.02, n), 0, 1)})
    long, _ = build_long(raw, auto(raw))
    long["lsl"], long["usl"] = np.where(long.parameter == "gate_oxide_thickness", 8.0, np.nan), \
        np.where(long.parameter == "gate_oxide_thickness", 9.2, np.nan)
    save_dataset("myfab", long, tmp_path)

    monkeypatch.setenv("METRO_IMPORT_PATH", str(tmp_path))
    monkeypatch.setenv("SEMIYIELD_DIR", _semiyield())
    at = AppTest.from_file(str(GUIDE / "launch_semiyield.py"), default_timeout=300)
    at.run()
    sel = [s for s in at.sidebar.selectbox if s.label == "資料集"][0]
    sel.set_value("myfab").run()
    [b for b in at.sidebar.button if b.label == "載入這份資料"][0].click().run()
    assert not at.exception
    assert any("使用中：myfab" in s.value for s in at.sidebar.success)

    at.sidebar.radio[0].set_value("SPC Dashboard").run()
    sb = [s for s in at.selectbox if s.label == "Parameter to chart"][0]
    assert sb.value == "gate_oxide_thickness" and "lot_sequence" not in sb.options
    usl = [x for x in at.number_input if x.label == "USL"][0]
    lsl = [x for x in at.number_input if x.label == "LSL"][0]
    assert (lsl.value, usl.value) == pytest.approx((8.0, 9.2))  # the spec carried by the import wins
    assert any("匯入資料中的規格" in c.value for c in at.caption)

    sb.set_value("poly_cd").run()  # no spec in the file -> data-based suggestion, not SemiYield's yield window
    assert "資料基準期" in [x for x in at.number_input if x.label == "USL"][0].help

    if importlib.util.find_spec("sklearn"):
        at.sidebar.radio[0].set_value("Yield Prediction").run()
        btn = [b for b in at.button if b.label == "Train Ensemble Model"][0]
        assert not btn.disabled
        btn.click().run()
        assert not at.exception
