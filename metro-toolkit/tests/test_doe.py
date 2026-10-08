"""DOE designs, response-surface fit, desirability optimiser and the virtual tools' answer key."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from metro_toolkit.doe import (
    box_behnken,
    central_composite,
    curvature_test,
    desirability,
    evaluate_recipe,
    fit_model,
    fractional,
    full_factorial,
    load_processes,
    make_design,
    optimize,
    run_experiments,
    run_sheet,
    to_coded,
    to_real,
    true_optimum,
)

PROCS = load_processes()


def test_design_structure():
    ff = full_factorial(3)
    assert ff.shape == (8, 3) and (ff.T @ ff == 8 * np.eye(3)).all()  # orthogonal
    assert ff[:2, 0].tolist() == [-1, 1]  # standard order: A changes fastest
    assert full_factorial(2, 3).shape == (9, 2)
    frac, info = fractional(4)
    assert frac.shape == (8, 4) and info["resolution"] == 4
    assert np.allclose(frac[:, 3], frac[:, 0] * frac[:, 1] * frac[:, 2])  # D = ABC
    assert info["aliases"]["AB"] == ["CD"]
    _, info5 = fractional(6)
    assert info5["resolution"] == 4 and "ABCE" in info5["defining_relation"]
    ccd = central_composite(3, "rotatable", center=4)
    assert ccd.shape == (8 + 6 + 4, 3) and np.isclose(np.abs(ccd).max(), 8 ** 0.25)
    assert np.abs(central_composite(3, "face")).max() == 1
    bbd = box_behnken(3, center=3)
    assert bbd.shape == (15, 3) and not (np.abs(bbd).sum(axis=1) == 3).any()  # no corners


def test_run_sheet_and_coding():
    f = {"a": {"low": 10, "high": 20}, "b": {"low": 0.5, "high": 4.0}}
    d, _ = make_design("full2", 2, center=2)
    sheet = run_sheet(d, f, replicates=2, seed=3)
    assert len(sheet) == 12 and sorted(sheet["run_order"]) == list(range(1, 13))
    assert set(sheet["a"]) == {10, 15, 20} and (sheet["point"] == "center").sum() == 4
    real = to_real(np.array([[-1, 1], [0, 0]]), f)
    assert real.tolist() == [[10, 4.0], [15, 2.25]]
    assert np.allclose(to_coded(real, f), [[-1, 1], [0, 0]])


def test_fit_recovers_known_surface():
    d = central_composite(3, "face", center=5)
    coded = pd.DataFrame(d, columns=["A", "B", "C"])
    rng = np.random.default_rng(0)
    y = 10 + 2 * d[:, 0] - 1 * d[:, 1] + 0.5 * d[:, 0] * d[:, 2] + 1.5 * d[:, 1] ** 2 + rng.normal(0, 0.05, len(d))
    fit = fit_model(coded, y, "y", "quadratic")
    c = fit.table.set_index("term")["coef"]
    assert c["A"] == pytest.approx(2, abs=0.05) and c["B"] == pytest.approx(-1, abs=0.05)
    assert c["A × C"] == pytest.approx(0.5, abs=0.05) and c["B²"] == pytest.approx(1.5, abs=0.1)
    p = fit.table.set_index("term")["p"]
    assert p["A"] < 1e-6 and p["C"] > 0.01
    assert fit.r2_adj > 0.99 and fit.r2_pred > 0.95 and not fit.warnings
    assert fit.predict(np.array([[1, 0, 0]]))[0] == pytest.approx(12, abs=0.1)


def test_two_level_design_cannot_resolve_curvature():
    d, _ = make_design("full2", 2, center=4)
    coded = pd.DataFrame(d, columns=["A", "B"])
    y = 5 + d[:, 0] + 2 * d[:, 0] ** 2 + np.random.default_rng(1).normal(0, 0.02, len(d))
    fit = fit_model(coded, y, "y", "quadratic")
    assert fit.curvature_unresolved and not any("²" in t for t in fit.table["term"])
    curv = curvature_test(coded, y)
    assert curv["difference"] == pytest.approx(2, abs=0.1) and curv["p"] < 0.001
    few = fit_model(coded.iloc[:4], y[:4], "y", "interaction")  # 4 runs, 4 terms
    assert few.dof == 0 and any("不夠" in w for w in few.warnings)


def test_desirability():
    tgt = {"goal": "target", "target": 5, "tol": 0.2}
    assert desirability([5, 5.1, 5.3], tgt).tolist() == pytest.approx([1, 0.5, 0])
    mn = {"goal": "minimize", "best": 1, "worst": 3}
    assert desirability([0.5, 2, 4], mn).tolist() == pytest.approx([1, 0.5, 0])


def test_optimizer_finds_known_optimum():
    goals = {"y": {"goal": "target", "target": 0.5, "tol": 1.0}, "z": {"goal": "minimize", "best": 0, "worst": 2}}
    pred = lambda c: pd.DataFrame({"y": c[:, 0], "z": (c[:, 1] - 0.3) ** 2})  # noqa: E731
    best = optimize(pred, 2, goals)
    assert best["coded"] == pytest.approx([0.5, 0.3], abs=0.01) and best["D"] > 0.99


@pytest.mark.parametrize("proc_key", list(PROCS))
def test_ccd_doe_gets_close_to_true_optimum(proc_key):
    proc = PROCS[proc_key]
    names = list(proc["factors"])
    truth = true_optimum(proc)
    assert truth["D"] > 0.8  # the answer key itself is a good, feasible recipe
    d, _ = make_design("ccd", len(names), center=4)
    res = run_experiments(proc, run_sheet(d, proc["factors"], 1, seed=3), seed=5)
    coded = pd.DataFrame(to_coded(res[names].to_numpy(float), proc["factors"]), columns=names)
    fits = {r: fit_model(coded, res[r], r) for r in proc["responses"]}
    pred = lambda c: pd.DataFrame({r: f.predict(pd.DataFrame(c, columns=names)) for r, f in fits.items()})  # noqa: E731
    best = optimize(pred, len(names), proc["responses"])
    recipe = dict(zip(names, to_real(best["coded"][None, :], proc["factors"])[0]))
    mine = evaluate_recipe(proc, recipe)
    assert mine["D"] > 0.6 * truth["D"]
    assert abs(mine["responses"]["thickness"] - proc["responses"]["thickness"]["target"]) < \
        proc["responses"]["thickness"]["tol"]


def test_virtual_physics_directions():
    ald = PROCS["ald_hk"]
    base = {"cycles": 50, "temp_c": 285, "purge_s": 3.0}
    t = lambda **kw: evaluate_recipe(ald, {**base, **kw})["responses"]  # noqa: E731
    assert t(cycles=60)["thickness"] == pytest.approx(1.2 * t()["thickness"], rel=1e-6)  # linear in cycles
    assert t(purge_s=0.5)["thickness"] > t()["thickness"] and t(purge_s=0.5)["nu_pct"] > t()["nu_pct"]  # parasitic CVD
    assert t(temp_c=240)["nu_pct"] > t()["nu_pct"]  # outside the ALD window
    cvd = PROCS["cvd_tin"]
    c = lambda **kw: evaluate_recipe(cvd, {"time_s": 80, "temp_c": 575, "pressure_torr": 5.0, **kw})["responses"]  # noqa: E731
    assert c(temp_c=650)["thickness"] > c()["thickness"]  # Arrhenius
    assert c(temp_c=650, pressure_torr=10)["thickness"] > c(temp_c=650)["thickness"]  # transport limited: pressure


def test_doe_dashboard_page():
    from streamlit.testing.v1 import AppTest

    app = Path(__file__).resolve().parents[1] / "src" / "metro_toolkit" / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=300)
    at.run()
    at.sidebar.radio[0].set_value("DOE / recipe").run()
    [b for b in at.button if b.label == "在虛擬機台上執行"][0].click().run()
    assert not at.exception
    labels = [m.label for m in at.metric]
    assert "R²" in labels and any(lab.startswith("預測整體滿意度") for lab in labels)
    [b for b in at.button if b.label == "在建議配方跑確認實驗"][0].click().run()
    assert not at.exception and any(m.label.startswith("你的配方真實滿意度") for m in at.metric)
