"""Wafer-map pattern features and classifier, scored against the fab simulator's answer key."""

import numpy as np
import pytest

from metro_toolkit.datagen.fab import die_grid, load_fab_config, simulate_fab
from metro_toolkit.wafer.patterns import GridGeometry, PatternClassifier, evaluate, fail_vector, feature_table, map_features

CFG = load_fab_config()
GRID = die_grid(CFG["wafer_radius_mm"], CFG["edge_exclusion_mm"], CFG["die_mm"])
GEO = GridGeometry.from_grid(GRID, CFG["die_mm"])


def test_features_on_hand_made_maps():
    x, y, rho = GEO.x, GEO.y, GEO.rho
    edge = map_features((rho > 0.88).astype(float), GEO)
    center = map_features((rho < 0.3).astype(float), GEO)
    line = map_features((np.abs(y - 5) < 6).astype(float), GEO)
    blob = map_features((np.hypot(x - 60, y + 40) < 20).astype(float), GEO)
    assert edge["ring_4"] > 3 and edge["edge_center"] > 2
    assert center["ring_0"] > 3 and center["edge_center"] < -2
    assert line["line_score"] > 8 and line["line_vs_peak"] > 0.5 > blob["line_vs_peak"]  # elongated vs compact
    assert blob["peak_score"] > line["peak_score"] and blob["neighbour_ratio"] > 3
    rng = np.random.default_rng(0)
    rand = [map_features((rng.random(x.size) < 0.1).astype(float), GEO)["neighbour_ratio"] for _ in range(20)]
    assert 0.85 < np.mean(rand) < 1.15  # random -> about 1 (single maps are noisy: ~60 failing dies)
    assert map_features(np.zeros(x.size), GEO)["fail_rate"] == 0


def test_fail_vector_uses_defect_code_only():
    assert fail_vector("..DGD.").tolist() == [0, 0, 1, 0, 1, 0]
    assert fail_vector("..DGD.", codes="DG").sum() == 3


def test_pattern_mix_default_unchanged_and_zoo_has_all_patterns():
    zoo = simulate_fab(CFG, "pattern_zoo", n_lots=20)
    assert set(zoo.wafers["defect_pattern"]) == {"random", "scratch", "cluster", "center", "edge_ring"}
    base = simulate_fab(CFG, "baseline", n_lots=20)
    assert set(base.wafers["defect_pattern"]) <= {"random", "scratch", "cluster"}


def test_classifier_learns_patterns_on_unseen_wafers():
    train = simulate_fab(CFG, "pattern_zoo", n_lots=30, seed=11)
    test = simulate_fab(CFG, "pattern_zoo", n_lots=30, seed=12)
    ftr, fte = feature_table(train.dies, GEO), feature_table(test.dies, GEO)
    label = lambda r, f: r.wafers.set_index("wafer_id").loc[f["wafer_id"], "defect_pattern"].to_numpy()
    clf = PatternClassifier().fit(ftr, label(train, ftr))
    ev = evaluate(label(test, fte), clf.predict(fte))
    assert ev["accuracy"] > 0.8  # chance (always "random") would be ~0.4
    recall = ev["per_class"].set_index("pattern")["recall"]
    assert recall["edge_ring"] > 0.9 and recall["center"] > 0.9 and recall["scratch"] > 0.7
    assert ev["confusion"].to_numpy().sum() == len(fte)
    conf = clf.confidence(fte)
    assert ((conf >= 0) & (conf <= 1)).all()


def test_evaluate_counts():
    ev = evaluate(["random", "scratch", "scratch"], ["random", "scratch", "random"])
    assert ev["accuracy"] == pytest.approx(2 / 3)
    assert ev["confusion"].loc["scratch", "random"] == 1
    assert ev["per_class"].set_index("pattern").loc["scratch", "recall"] == 0.5
