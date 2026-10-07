"""Fix for SemiYield's YieldEnsemble stacking (applied at runtime; SemiYield's files are not changed).

Problem (found with SemiYield's default generated data, seed 42):
  The meta-learner is an unconstrained Ridge regression fitted on the validation slice only
  (the last 15% of the training rows). Yield is ~0.999 for 99% of wafers, so that slice holds just
  a couple of low-yield wafers. From so little signal Ridge learned weights like [-0.11, +1.76]:
  every predicted yield drop is amplified ~1.65x, and the test R² became -1.47 although each base
  model alone scored ~0.6 and a random forest trained on all training rows scored ~0.9.

Fix (standard stacking practice):
  1. Convex stacking weights: non-negative least squares on the validation predictions, normalised
     to sum to 1 (equal weights if the validation slice carries no signal). The ensemble can then
     never exaggerate its members.
  2. After the weights are chosen, refit the tree models on train + validation rows, so rare
     low-yield events in the validation slice are not thrown away. The test set is never touched.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import nnls


class ConvexWeights:
    """Drop-in replacement for the Ridge meta-learner: prediction = stack @ weights."""

    def __init__(self, weights):
        self.coef_ = np.asarray(weights, dtype=float)
        self.intercept_ = 0.0

    def predict(self, stack):
        return np.asarray(stack, dtype=float) @ self.coef_


def convex_weights(stack: np.ndarray, target: np.ndarray) -> np.ndarray:
    stack = np.asarray(stack, dtype=float)
    k = stack.shape[1]
    if np.std(target) < 1e-12:
        return np.full(k, 1.0 / k)
    w, _ = nnls(stack, np.asarray(target, dtype=float))
    return w / w.sum() if w.sum() > 0 else np.full(k, 1.0 / k)


def _fixed_fit(self, X_train, y_train, X_val, y_val):
    self._metro_original_fit(X_train, y_train, X_val, y_val)  # base models + scalers (+ LSTM)
    X_val_s = self.scaler_X.transform(self._to_2d(X_val))
    y_val_s = self.scaler_y.transform(np.asarray(y_val, float).reshape(-1, 1)).ravel()
    stack = self._stack_predict(X_val_s, X_val)
    self.meta = ConvexWeights(convex_weights(stack, y_val_s))

    X_all = np.vstack([self._to_2d(X_train), self._to_2d(X_val)])
    y_all = np.concatenate([np.asarray(y_train, float), np.asarray(y_val, float)])
    X_all_s = self.scaler_X.transform(X_all)
    y_all_s = self.scaler_y.transform(y_all.reshape(-1, 1)).ravel()
    self.rf.fit(X_all_s, y_all_s)
    self.xgb.fit(X_all_s, y_all_s)
    self.metro_fixed = True
    return self


def apply(yield_ensemble_cls) -> bool:
    """Patch YieldEnsemble.fit in place (works however the page imported the class). Idempotent."""
    if getattr(yield_ensemble_cls, "_metro_fixed_patch", False):
        return False
    yield_ensemble_cls._metro_original_fit = yield_ensemble_cls.fit
    yield_ensemble_cls.fit = _fixed_fit
    yield_ensemble_cls._metro_fixed_patch = True
    return True
