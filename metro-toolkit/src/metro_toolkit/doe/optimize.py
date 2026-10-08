"""Multi-response recipe optimisation with desirability functions (Derringer & Suich).

Each response gets a desirability d in [0, 1]:
    target    d = 1 - |y - target| / tol      (0 outside +-tol)
    minimize  d = (worst - y) / (worst - best) (1 at or below best, 0 at or above worst)
    maximize  d = (y - worst) / (best - worst)
Overall D = weighted geometric mean, so one unacceptable response makes the whole recipe unacceptable.
Search: grid over the coded box [-1, 1]^k (never extrapolate outside the tested range), then local refine.
"""

from __future__ import annotations

import itertools
from typing import Callable

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def desirability(y, goal: dict) -> np.ndarray:
    y = np.asarray(y, float)
    g = goal["goal"]
    if g == "target":
        d = 1 - np.abs(y - goal["target"]) / goal["tol"]
    elif g == "minimize":
        d = (goal["worst"] - y) / (goal["worst"] - goal["best"])
    elif g == "maximize":
        d = (y - goal["worst"]) / (goal["best"] - goal["worst"])
    else:
        raise ValueError(f"unknown goal {g}")
    return np.clip(d, 0.0, 1.0)


def overall(responses: pd.DataFrame, goals: dict) -> np.ndarray:
    used = [r for r in goals if r in responses]
    w = np.array([goals[r].get("weight", 1.0) for r in used])
    d = np.column_stack([desirability(responses[r], goals[r]) for r in used])
    return np.exp((np.log(np.clip(d, 1e-12, None)) * w).sum(axis=1) / w.sum()) * (d > 0).all(axis=1)


def optimize(predict: Callable[[np.ndarray], pd.DataFrame], k: int, goals: dict, grid: int | None = None,
             refine: int = 5) -> dict:
    """predict(coded n x k) -> DataFrame of responses. Returns best coded point, responses and D."""
    grid = grid or {1: 101, 2: 41, 3: 21, 4: 11}.get(k, 7)
    axis = np.linspace(-1, 1, grid)
    pts = np.array(list(itertools.product(axis, repeat=k)))
    D = overall(predict(pts), goals)
    best = pts[np.argsort(-D)[:refine]]

    def neg(x):
        return -overall(predict(x[None, :]), goals)[0]

    cands = [(pts[np.argmax(D)], D.max())]
    for x0 in best:
        res = minimize(neg, x0, method="L-BFGS-B", bounds=[(-1, 1)] * k)
        cands.append((res.x, -res.fun))
    x, d = max(cands, key=lambda c: c[1])
    return {"coded": np.asarray(x), "D": float(d), "responses": predict(np.asarray(x)[None, :]).iloc[0].to_dict()}
