"""Wafer-map (die map) spatial pattern recognition.

Readable features from the failing dies of one wafer, then a nearest-centroid classifier trained on
labelled maps (e.g. from the fab simulator's answer key). Numpy only. Wafers with very few failing dies
are called "random": in a real fab most wafers have no pattern, and a shape drawn from 8 dies is noise.

Features (all relative to the wafer's own fail rate, so a dirty wafer and a clean wafer with the same
shape look alike):
    fail_rate        fraction of failing dies
    ring_0..ring_4   fail rate in 5 radial rings (centre -> edge) / overall fail rate
    edge_center      log ratio of outer-ring to inner-disc fail rate
    line_score       best straight band (any angle, 14 mm wide) fail rate / overall   -> scratch
    peak_score       best 25 mm neighbourhood fail rate / overall                      -> cluster / centre
    line_vs_peak     log(line_score / peak_score): > 0 elongated (scratch), < 0 compact (cluster)
    neighbour_ratio  P(neighbour fails | die fails) / overall fail rate  (1 = random, > 1 = clustered)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

PATTERNS = ["random", "edge_ring", "center", "scratch", "cluster"]
RING_EDGES = [0.0, 0.35, 0.6, 0.8, 0.9, 1.01]
FEATURES = ["fail_rate"] + [f"ring_{i}" for i in range(len(RING_EDGES) - 1)] + [
    "edge_center", "line_score", "peak_score", "line_vs_peak", "neighbour_ratio"]
PATTERN_TEXT = {
    "random": "隨機：沒有空間結構，看整體缺陷密度",
    "edge_ring": "邊緣環：外圈特別多，常見於邊緣製程 / 斜面 (bevel) / 夾持問題",
    "center": "中心：中間特別多，常見於噴頭 / 旋塗中心 / 中心溫度問題",
    "scratch": "刮痕：一條直線，常見於機械手臂 / CMP 刮傷",
    "cluster": "群聚：一團，常見於局部微粒 / 液滴",
}


class GridGeometry:
    """Pre-computed geometry for one die grid (shared by all wafers of a product)."""

    def __init__(self, x, y, r_eff: float, die_mm=(10.0, 10.0)):
        self.x, self.y = np.asarray(x, float), np.asarray(y, float)
        self.r_eff = float(r_eff)
        self.rho = np.hypot(self.x, self.y) / self.r_eff
        self.ring = np.digitize(self.rho, RING_EDGES[1:-1])
        dist = np.hypot(self.x[:, None] - self.x[None, :], self.y[:, None] - self.y[None, :])
        self.near = (dist <= 25.0).astype(float)  # 25 mm neighbourhood (cluster / centre peak)
        self.near_n = self.near.sum(axis=1)
        pitch = min(die_mm) * 1.01
        self.adj = ((dist > 0) & (dist <= pitch * 1.5)).astype(float)  # 8-neighbourhood
        bands = []
        for ang in np.deg2rad(np.arange(0, 180, 5)):
            d = -np.sin(ang) * self.x + np.cos(ang) * self.y
            for off in np.arange(-0.6, 0.61, 0.05) * self.r_eff:
                m = np.abs(d - off) < 7.0
                if m.sum() >= 12:
                    bands.append(m)
        self.bands = np.array(bands, dtype=float)
        self.band_n = self.bands.sum(axis=1)

    @classmethod
    def from_grid(cls, grid: dict, die_mm=(10.0, 10.0)) -> GridGeometry:
        return cls(grid["x"], grid["y"], grid["r_eff"], die_mm)


def fail_vector(die_map: str, codes: str = "D") -> np.ndarray:
    """1 for dies whose code is in ``codes`` (default: killer defects only), else 0."""
    return np.fromiter((c in codes for c in die_map), dtype=float, count=len(die_map))


def map_features(fails: np.ndarray, geo: GridGeometry) -> dict:
    f = np.asarray(fails, float)
    p = f.mean()
    out = {"fail_rate": p}
    if p == 0:
        return {**out, **{k: 1.0 for k in FEATURES[1:]}, "edge_center": 0.0, "line_vs_peak": 0.0}
    for i in range(len(RING_EDGES) - 1):
        sel = geo.ring == i
        out[f"ring_{i}"] = f[sel].mean() / p if sel.any() else 1.0
    eps = 0.5 / len(f)
    out["edge_center"] = float(np.log((f[geo.rho >= 0.8].mean() + eps) / (f[geo.rho < 0.6].mean() + eps)))
    out["line_score"] = float((geo.bands @ f / geo.band_n).max() / p)
    out["peak_score"] = float((geo.near @ f / geo.near_n).max() / p)
    out["line_vs_peak"] = float(np.log(out["line_score"] / out["peak_score"]))
    nb = geo.adj @ f
    out["neighbour_ratio"] = float((nb[f > 0] / geo.adj.sum(axis=1)[f > 0]).mean() / p)
    return out


def feature_table(dies: pd.DataFrame, geo: GridGeometry, codes: str = "D") -> pd.DataFrame:
    """One feature row per wafer from a die-map table (columns wafer_id, map)."""
    rows = []
    for w, m in zip(dies["wafer_id"], dies["map"]):
        f = fail_vector(m, codes)
        rows.append({"wafer_id": w, "n_fail": int(f.sum()), **map_features(f, geo)})
    return pd.DataFrame(rows, columns=["wafer_id", "n_fail"] + FEATURES)


LOG_FREE = {"edge_center", "line_vs_peak"}  # already log ratios (can be negative)


def _transform(X: np.ndarray, names) -> np.ndarray:
    """Ratios are skewed; compare them on a log scale."""
    X = X.copy()
    for j, n in enumerate(names):
        if n not in LOG_FREE:
            X[:, j] = np.log(np.clip(X[:, j], 1e-4, None) + 0.05)
    return X


@dataclass
class PatternClassifier:
    """Nearest centroid on standardised log features (simple, explainable, no extra dependency)."""

    classes: list = field(default_factory=list)
    centroids: np.ndarray | None = None
    mean: np.ndarray | None = None
    scale: np.ndarray | None = None
    features: list = field(default_factory=lambda: [f for f in FEATURES if f != "fail_rate"])
    min_defects: int = 16  # fewer failing dies than this -> "random": too little evidence to call a shape

    def fit(self, feats: pd.DataFrame, labels) -> PatternClassifier:
        Z = _transform(feats[self.features].to_numpy(float), self.features)
        self.mean, self.scale = Z.mean(axis=0), Z.std(axis=0) + 1e-9
        Z = (Z - self.mean) / self.scale
        labels = np.asarray(labels)
        self.classes = [c for c in PATTERNS if c in set(labels)] + sorted(set(labels) - set(PATTERNS))
        self.centroids = np.array([Z[labels == c].mean(axis=0) for c in self.classes])
        return self

    def distances(self, feats: pd.DataFrame) -> np.ndarray:
        Z = (_transform(feats[self.features].to_numpy(float), self.features) - self.mean) / self.scale
        return np.sqrt(((Z[:, None, :] - self.centroids[None, :, :]) ** 2).sum(axis=2))

    def predict(self, feats: pd.DataFrame) -> np.ndarray:
        pred = np.array(self.classes)[self.distances(feats).argmin(axis=1)]
        if "n_fail" in feats and "random" in self.classes:
            pred[feats["n_fail"].to_numpy() < self.min_defects] = "random"
        return pred

    def confidence(self, feats: pd.DataFrame) -> np.ndarray:
        """Margin between the best and second-best class (0 = a coin flip)."""
        d = np.sort(self.distances(feats), axis=1)
        return (d[:, 1] - d[:, 0]) / (d[:, 1] + 1e-9)


def evaluate(true, pred, classes=None) -> dict:
    """Confusion matrix (rows = truth, columns = prediction), accuracy, recall/precision per class."""
    true, pred = np.asarray(true), np.asarray(pred)
    classes = classes or [c for c in PATTERNS if c in set(true) | set(pred)]
    cm = pd.crosstab(pd.Categorical(true, classes), pd.Categorical(pred, classes), dropna=False)
    cm.index.name, cm.columns.name = "truth", "predicted"
    diag = np.diag(cm.to_numpy())
    rows, cols = cm.sum(axis=1).to_numpy(), cm.sum(axis=0).to_numpy()
    recall = np.where(rows > 0, diag / np.maximum(rows, 1), np.nan)  # nan: class absent / never predicted
    precision = np.where(cols > 0, diag / np.maximum(cols, 1), np.nan)
    return {"confusion": cm, "accuracy": float((true == pred).mean()),
            "per_class": pd.DataFrame({"pattern": classes, "n": cm.sum(axis=1).to_numpy(),
                                       "recall": recall, "precision": precision})}
