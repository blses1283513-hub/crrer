"""Response-surface model: least squares on coded factors with t-tests per term.

terms      "linear" (A, B, ...), "interaction" (+ A:B ...), "quadratic" (+ A^2 ...)
fit_model  coefficients, standard errors, t, p, R², adjusted R², predicted R² (PRESS), RMSE, warnings
           (too few runs, aliased terms, curvature that a 2-level design cannot see)
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats


def term_list(names: list[str], order: str = "quadratic") -> list[tuple]:
    terms = [()] + [(n,) for n in names]
    if order in ("interaction", "quadratic"):
        terms += list(itertools.combinations(names, 2))
    if order == "quadratic":
        terms += [(n, n) for n in names]
    return terms


def term_name(t: tuple) -> str:
    if not t:
        return "intercept"
    if len(t) == 2 and t[0] == t[1]:
        return f"{t[0]}²"
    return " × ".join(t)


def model_matrix(coded: pd.DataFrame, terms: list[tuple]) -> np.ndarray:
    cols = [np.ones(len(coded))]
    for t in terms[1:]:
        cols.append(np.prod([coded[n].to_numpy(float) for n in t], axis=0))
    return np.column_stack(cols)


@dataclass
class ModelFit:
    response: str
    factors: list
    terms: list
    coef: np.ndarray
    table: pd.DataFrame
    r2: float
    r2_adj: float
    r2_pred: float
    rmse: float
    dof: int
    warnings: list = field(default_factory=list)
    curvature_unresolved: bool = False  # the design cannot say which factor bends the response

    def predict(self, coded) -> np.ndarray:
        df = coded if isinstance(coded, pd.DataFrame) else pd.DataFrame(np.atleast_2d(coded), columns=self.factors)
        return model_matrix(df, self.terms) @ self.coef


def fit_model(coded: pd.DataFrame, y, response: str = "y", order: str = "quadratic") -> ModelFit:
    """Fit y on coded factors (columns of ``coded``). Drops quadratic terms the design cannot estimate."""
    names = list(coded.columns)
    y = np.asarray(y, float)
    ok = np.isfinite(y)
    coded, y = coded.loc[ok].reset_index(drop=True), y[ok]
    terms = term_list(names, order)
    warnings = []
    levels = {n: np.unique(np.round(coded[n], 6)).size for n in names}
    if order == "quadratic" and any(v < 3 for v in levels.values()):
        two = [n for n, v in levels.items() if v < 3]
        terms = [t for t in terms if not (len(t) == 2 and t[0] == t[1] and t[0] in two)]
        warnings.append(f"{', '.join(two)} 只有兩個水準，無法估計平方項（彎曲）；加中心點只能檢查有沒有彎曲。")
    X = model_matrix(coded, terms)
    sq = [j for j, t in enumerate(terms) if len(t) == 2 and t[0] == t[1]]
    curvature_unresolved = any(v < 3 for v in levels.values()) and order == "quadratic"
    if sq:
        base = [j for j in range(len(terms)) if j not in sq]
        if np.linalg.matrix_rank(X) - np.linalg.matrix_rank(X[:, base]) < len(sq):
            # e.g. 2-level factorial + centre points: all squares are the same column -> drop them all
            terms, X = [terms[j] for j in base], X[:, base]
            curvature_unresolved = True
            warnings.append("中心點只能看出「有沒有彎曲」，分不出是哪個因子造成的，所以模型不含平方項；"
                            "要估計彎曲請用 CCD 或 Box-Behnken。")
    rank = np.linalg.matrix_rank(X)
    if rank < X.shape[1]:
        warnings.append("有些項彼此混淆 (aliased)，無法分開估計；請改用較小的模型或更完整的設計。")
        keep = []
        for j in range(X.shape[1]):  # greedy: keep columns that add rank
            if np.linalg.matrix_rank(X[:, keep + [j]]) > len(keep):
                keep.append(j)
        terms = [terms[j] for j in keep]
        X = X[:, keep]
    n, p = X.shape
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    dof = n - p
    sse = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - sse / sst if sst > 0 else float("nan")
    if dof > 0:
        mse = sse / dof
        cov = mse * np.linalg.pinv(X.T @ X)
        se = np.sqrt(np.clip(np.diag(cov), 0, None))
        t = np.divide(coef, se, out=np.full_like(coef, np.nan), where=se > 0)
        pval = 2 * stats.t.sf(np.abs(t), dof)
        r2_adj = 1 - (sse / dof) / (sst / (n - 1)) if sst > 0 else float("nan")
        h = np.einsum("ij,jk,ik->i", X, np.linalg.pinv(X.T @ X), X)
        press = float(((resid / np.clip(1 - h, 1e-9, None)) ** 2).sum())
        r2_pred = 1 - press / sst if sst > 0 else float("nan")
        rmse = float(np.sqrt(mse))
    else:
        se = t = pval = np.full_like(coef, np.nan)
        r2_adj = r2_pred = rmse = float("nan")
        warnings.append("跑的次數不夠：參數和實驗次數一樣多，無法估計誤差與 p 值。請加中心點或重複。")
    table = pd.DataFrame({"term": [term_name(tt) for tt in terms], "coef": coef, "std_err": se, "t": t, "p": pval})
    return ModelFit(response, names, terms, coef, table, r2, r2_adj, r2_pred, rmse, dof, warnings,
                    curvature_unresolved)


def curvature_test(coded: pd.DataFrame, y) -> dict | None:
    """Centre points vs factorial points: is there curvature a linear model would miss?"""
    y = np.asarray(y, float)
    c = (coded.abs() < 1e-9).all(axis=1).to_numpy()
    f = (coded.abs().sub(1).abs() < 1e-9).all(axis=1).to_numpy()
    if c.sum() < 2 or f.sum() < 2:
        return None
    diff = y[f].mean() - y[c].mean()
    s = y[c].std(ddof=1)
    se = s * np.sqrt(1 / f.sum() + 1 / c.sum())
    if se <= 1e-12 * max(abs(y).max(), 1.0):  # noise-free response (e.g. computed process time): no t-test
        return {"difference": float(diff), "p": 0.0 if abs(diff) > 1e-9 * max(abs(y).max(), 1.0) else 1.0}
    t = diff / se
    return {"difference": float(diff), "p": float(2 * stats.t.sf(abs(t), c.sum() - 1))}
