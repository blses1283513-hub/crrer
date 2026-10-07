"""Model-based thickness (and optical constant) extraction.

Thin-film metrology is an inverse problem: a measured spectrum is compared with
a stack model, and the free parameters (thickness, sometimes n/k model
coefficients) are adjusted until model and data agree. Three things matter in
practice, and this module makes each explicit:

1. Global search first. Interference makes the cost function periodic in
   thickness (period ~ lambda / 2n), so a local optimiser started at the wrong
   fringe converges to a wrong-but-plausible thickness. We scan a grid, keep the
   best few basins, then refine each with Levenberg-Marquardt-style least squares.
2. Goodness of fit. ``chi2_red`` ~ 1 means the residual is consistent with the
   stated measurement noise; >> 1 means the model (stack, n/k) is wrong.
3. Parameter uncertainty and correlation. For very thin films thickness and n
   are strongly correlated (|r| -> 1): you cannot float both. The correlation
   matrix tells you when to fix n.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

from .tmm import Stack, ellipsometry, ncs, reflectance


# --------------------------------------------------------------------------- #
# Data containers                                                             #
# --------------------------------------------------------------------------- #


@dataclass
class Measurement:
    """A measured spectrum.

    kind = 'reflectance': ``data = {'R': array}`` at ``aoi_deg`` (default normal incidence)
    kind = 'se':          ``data = {angle: (psi_deg, delta_deg), ...}``
    ``sigma`` is the 1-sigma noise of the fitted quantity (R, or N/C/S).
    """

    wavelength_nm: np.ndarray
    kind: str
    data: dict
    sigma: float = 1e-3
    aoi_deg: float = 0.0

    def __post_init__(self):
        if self.kind not in ("reflectance", "se"):
            raise ValueError("kind must be 'reflectance' or 'se'")
        self.wavelength_nm = np.asarray(self.wavelength_nm, float)


@dataclass
class FitParameter:
    """One free parameter: ``target='thickness'`` or a material model attribute (e.g. 'A')."""

    layer: int
    target: str = "thickness"
    bounds: tuple[float, float] = (0.0, 1000.0)
    initial: float | None = None

    @property
    def label(self) -> str:
        return f"L{self.layer}.{self.target}"


@dataclass
class FitResult:
    values: dict[str, float]
    stderr: dict[str, float]
    correlation: np.ndarray
    labels: list[str]
    chi2_red: float
    rmse: float
    success: bool
    stack: Stack
    n_points: int
    candidates: list[tuple[float, list[float]]] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"stack     : {self.stack.describe()}", f"chi2_red  : {self.chi2_red:.3f}"]
        for lab in self.labels:
            lines.append(f"{lab:<12}: {self.values[lab]:.4f} +/- {self.stderr[lab]:.4f}")
        if len(self.labels) > 1:
            lines.append("correlation:\n" + np.array2string(self.correlation, precision=3))
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Forward simulation of measurements (for synthetic data and tests)           #
# --------------------------------------------------------------------------- #


def simulate_reflectometry(stack, wavelength_nm, noise=0.0, aoi_deg=0.0, rng=None) -> Measurement:
    rng = np.random.default_rng(rng)
    R = reflectance(stack, wavelength_nm, aoi_deg)
    if noise:
        R = R + rng.normal(0.0, noise, R.shape)
    return Measurement(wavelength_nm, "reflectance", {"R": R}, sigma=max(noise, 1e-4), aoi_deg=aoi_deg)


def simulate_se(stack, wavelength_nm, angles=(65.0, 70.0, 75.0), psi_noise=0.0, delta_noise=0.0, rng=None):
    rng = np.random.default_rng(rng)
    data = {}
    for a in angles:
        psi, delta = ellipsometry(stack, wavelength_nm, a)
        if psi_noise:
            psi = psi + rng.normal(0.0, psi_noise, psi.shape)
        if delta_noise:
            delta = delta + rng.normal(0.0, delta_noise, delta.shape)
        data[float(a)] = (psi, delta)
    # propagate Psi/Delta noise to N/C/S (dN ~ 2 sin2Psi dPsi <= 2 dPsi)
    sigma = 2.0 * np.deg2rad(max(psi_noise, delta_noise / 2.0, 0.005))
    return Measurement(wavelength_nm, "se", data, sigma=sigma)


# --------------------------------------------------------------------------- #
# Fitting                                                                     #
# --------------------------------------------------------------------------- #


def _apply(stack: Stack, params: list[FitParameter], p: np.ndarray) -> Stack:
    thicknesses = stack.thicknesses.copy()
    materials = [None] * len(stack.layers)
    for fp, value in zip(params, p):
        if fp.target == "thickness":
            thicknesses[fp.layer] = value
        else:
            base = materials[fp.layer] or stack.layers[fp.layer].material
            materials[fp.layer] = base.with_params(**{fp.target: value})
    return stack.copy_with(thicknesses=thicknesses, materials=materials)


def _residual_fn(stack, meas: Measurement, params):
    wl = meas.wavelength_nm
    if meas.kind == "reflectance":
        target = meas.data["R"]

        def res(p):
            return (reflectance(_apply(stack, params, p), wl, meas.aoi_deg) - target) / meas.sigma

    else:
        targets = {a: np.concatenate(ncs(*pd)) for a, pd in meas.data.items()}

        def res(p):
            s = _apply(stack, params, p)
            parts = [np.concatenate(ncs(*ellipsometry(s, wl, a))) - t for a, t in targets.items()]
            return np.concatenate(parts) / meas.sigma

    return res


def _grid(params: list[FitParameter], x0: np.ndarray, n_random: int, rng) -> np.ndarray:
    thick_idx = [i for i, fp in enumerate(params) if fp.target == "thickness"]
    if not thick_idx:
        return x0[None, :]
    if len(thick_idx) == 1:
        i = thick_idx[0]
        lo, hi = params[i].bounds
        # ~0.5 nm steps resolve fringes down to lambda/2n ~ 50 nm periods
        n = int(np.clip((hi - lo) / 0.5, 50, 4000))
        pts = np.repeat(x0[None, :], n, axis=0)
        pts[:, i] = np.linspace(lo, hi, n)
        return pts
    if len(thick_idx) == 2:
        i, j = thick_idx
        gi = np.linspace(*params[i].bounds, 60)
        gj = np.linspace(*params[j].bounds, 60)
        pts = np.repeat(x0[None, :], gi.size * gj.size, axis=0)
        GI, GJ = np.meshgrid(gi, gj, indexing="ij")
        pts[:, i], pts[:, j] = GI.ravel(), GJ.ravel()
        return pts
    pts = np.repeat(x0[None, :], n_random, axis=0)
    for i in thick_idx:
        pts[:, i] = rng.uniform(*params[i].bounds, n_random)
    return pts


def fit(
    stack: Stack,
    measurement: Measurement,
    params: list[FitParameter],
    n_starts: int = 5,
    n_random: int = 400,
    global_search: bool = True,
    seed: int = 0,
) -> FitResult:
    """Fit ``params`` of ``stack`` to ``measurement``.

    The stack's current values are the starting point for parameters whose
    ``initial`` is None. Returns a :class:`FitResult` with values, 1-sigma
    standard errors (scaled by sqrt(chi2_red)), and the correlation matrix.
    """
    rng = np.random.default_rng(seed)
    res_fn = _residual_fn(stack, measurement, params)

    x0 = []
    for fp in params:
        if fp.initial is not None:
            x0.append(fp.initial)
        elif fp.target == "thickness":
            x0.append(stack.layers[fp.layer].thickness_nm)
        else:
            x0.append(getattr(stack.layers[fp.layer].material, fp.target))
    x0 = np.array(x0, float)
    lo = np.array([fp.bounds[0] for fp in params], float)
    hi = np.array([fp.bounds[1] for fp in params], float)
    x0 = np.clip(x0, lo, hi)

    # 1) global scan
    if global_search:
        grid = _grid(params, x0, n_random, rng)
        costs = np.array([np.sum(res_fn(p) ** 2) for p in grid])
        order = np.argsort(costs)
        starts, seen = [], []
        span = np.where(hi > lo, hi - lo, 1.0)
        for k in order:  # keep distinct basins only
            if all(np.max(np.abs(grid[k] - s) / span) > 0.02 for s in seen):
                starts.append(grid[k])
                seen.append(grid[k])
            if len(starts) >= n_starts:
                break
        starts.append(x0)
    else:
        starts = [x0]

    # 2) local refinement of each basin
    best, candidates = None, []
    for s in starts:
        r = least_squares(res_fn, np.clip(s, lo, hi), bounds=(lo, hi), method="trf", x_scale="jac")
        candidates.append((float(2 * r.cost), r.x.tolist()))
        if best is None or r.cost < best.cost:
            best = r

    # 3) statistics
    m, p = best.fun.size, best.x.size
    dof = max(m - p, 1)
    chi2_red = float(2 * best.cost / dof)
    J = best.jac
    try:
        cov = np.linalg.pinv(J.T @ J) * max(chi2_red, 1e-12)
    except np.linalg.LinAlgError:  # pragma: no cover
        cov = np.full((p, p), np.nan)
    std = np.sqrt(np.clip(np.diag(cov), 0, None))
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = cov / np.outer(std, std)
    labels = [fp.label for fp in params]
    return FitResult(
        values=dict(zip(labels, best.x.tolist())),
        stderr=dict(zip(labels, std.tolist())),
        correlation=corr,
        labels=labels,
        chi2_red=chi2_red,
        rmse=float(np.sqrt(np.mean((best.fun * measurement.sigma) ** 2))),
        success=bool(best.success),
        stack=_apply(stack, params, best.x),
        n_points=m,
        candidates=sorted(candidates),
    )


def fit_thickness(stack: Stack, measurement: Measurement, layer: int = 0, bounds=(0.0, 1000.0)) -> FitResult:
    """Convenience: float only one layer's thickness."""
    return fit(stack, measurement, [FitParameter(layer=layer, bounds=bounds)])
