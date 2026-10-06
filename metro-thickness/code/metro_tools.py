"""
metro_tools.py — vendor-agnostic analysis helpers for film-thickness metrology.

Companion code for the notes in metro-thickness/. Everything here is generic
textbook math; replace limits, site maps and rules with your site's official
definitions before using results for manufacturing decisions.

Sections
  1. Basic statistics, uniformity, capability
  2. SPC rules (Western Electric / Nelson subset), EWMA, CUSUM
  3. Gauge R&R (crossed ANOVA method)
  4. Tool matching (paired bias, Deming regression)
  5. Wafer-map helpers (polar site maps, radial / Zernike-like fit)
  6. Thin-film optics (Fresnel, transfer-matrix reflectance, ellipsometry Psi/Delta)
  7. Simple single-layer thickness fit
  8. Process helpers (etch rate, CMP removal, ALD GPC, Deal-Grove)

Run `python metro_tools.py` to execute the self-test / demo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# 1. Basic statistics, uniformity, capability
# ---------------------------------------------------------------------------


def describe(x):
    """Mean, sample std (ddof=1), min, max, range for a 1-D array."""
    x = np.asarray(x, dtype=float)
    return {
        "n": int(x.size),
        "mean": float(x.mean()),
        "std": float(x.std(ddof=1)) if x.size > 1 else float("nan"),
        "min": float(x.min()),
        "max": float(x.max()),
        "range": float(x.max() - x.min()),
    }


def uniformity(x, kind="range_half"):
    """Within-wafer non-uniformity in percent.

    kind:
      "range_half" : (max-min)/(2*mean)*100   (common 'half-range' definition)
      "range"      : (max-min)/mean*100
      "1sigma"     : std/mean*100             (CV)
      "3sigma"     : 3*std/mean*100
    Always report which definition you used.
    """
    d = describe(x)
    if kind == "range_half":
        return d["range"] / (2 * d["mean"]) * 100
    if kind == "range":
        return d["range"] / d["mean"] * 100
    if kind == "1sigma":
        return d["std"] / d["mean"] * 100
    if kind == "3sigma":
        return 3 * d["std"] / d["mean"] * 100
    raise ValueError(kind)


def capability(x, lsl=None, usl=None, sigma=None):
    """Cp, Cpk (or one-sided Cpu/Cpl). If sigma is None, uses sample std
    (that is then strictly Pp/Ppk-style 'overall' capability)."""
    x = np.asarray(x, dtype=float)
    mu = float(x.mean())
    s = float(x.std(ddof=1)) if sigma is None else float(sigma)
    out = {"mean": mu, "sigma": s}
    if usl is not None:
        out["Cpu"] = (usl - mu) / (3 * s)
    if lsl is not None:
        out["Cpl"] = (mu - lsl) / (3 * s)
    if usl is not None and lsl is not None:
        out["Cp"] = (usl - lsl) / (6 * s)
        out["Cpk"] = min(out["Cpu"], out["Cpl"])
    else:
        out["Cpk"] = out.get("Cpu", out.get("Cpl"))
    return out


def cpk_ci(cpk, n, conf=0.95):
    """Approximate two-sided CI for Cpk (Bissell 1990 normal approximation)."""
    from scipy.stats import norm

    z = norm.ppf(1 - (1 - conf) / 2)
    se = math.sqrt(1 / (9 * n) + cpk**2 / (2 * (n - 1)))
    return float(cpk - z * se), float(cpk + z * se)


def expected_ppm_out(mu, sigma, lsl=None, usl=None):
    """Expected parts-per-million outside spec under a normal model."""
    from scipy.stats import norm

    p = 0.0
    if lsl is not None:
        p += norm.cdf((lsl - mu) / sigma)
    if usl is not None:
        p += norm.sf((usl - mu) / sigma)
    return p * 1e6


def nested_variance(df, value="thickness", levels=("lot_id", "wafer_id")):
    """Simple hierarchical variance split: lot -> wafer -> site (residual).

    Uses method-of-moments on group means; adequate for a first look.
    Returns dict of variance components (may be clipped at 0).
    """
    lot, wafer = levels
    site_var = df.groupby([lot, wafer])[value].var(ddof=1).mean()
    wafer_means = df.groupby([lot, wafer])[value].mean()
    n_site = df.groupby([lot, wafer])[value].size().mean()
    wafer_var = wafer_means.groupby(level=0).var(ddof=1).mean() - site_var / n_site
    lot_means = wafer_means.groupby(level=0).mean()
    n_wafer = wafer_means.groupby(level=0).size().mean()
    lot_var = lot_means.var(ddof=1) - wafer_means.groupby(level=0).var(ddof=1).mean() / n_wafer
    return {
        "lot": max(lot_var, 0.0),
        "wafer": max(wafer_var, 0.0),
        "site(+meas)": site_var,
    }


# ---------------------------------------------------------------------------
# 2. SPC rules, EWMA, CUSUM
# ---------------------------------------------------------------------------


def spc_rules(x, center, sigma):
    """Return {rule_name: [indices where rule fires]} for common run rules.

    Rules (Western Electric 1-4 + Nelson 5-6 subset):
      R1  1 point beyond 3 sigma
      R2  2 of 3 consecutive beyond 2 sigma, same side
      R3  4 of 5 consecutive beyond 1 sigma, same side
      R4  8 consecutive on same side of center
      R5  6 consecutive steadily increasing or decreasing (trend)
      R6  15 consecutive within 1 sigma (stratification / limits too wide)
    """
    z = (np.asarray(x, float) - center) / sigma
    n = len(z)
    hits = {k: [] for k in ("R1", "R2", "R3", "R4", "R5", "R6")}
    for i in range(n):
        if abs(z[i]) > 3:
            hits["R1"].append(i)
        if i >= 2:
            w = z[i - 2 : i + 1]
            if (w > 2).sum() >= 2 or (w < -2).sum() >= 2:
                hits["R2"].append(i)
        if i >= 4:
            w = z[i - 4 : i + 1]
            if (w > 1).sum() >= 4 or (w < -1).sum() >= 4:
                hits["R3"].append(i)
        if i >= 7:
            w = z[i - 7 : i + 1]
            if (w > 0).all() or (w < 0).all():
                hits["R4"].append(i)
        if i >= 5:
            d = np.diff(z[i - 5 : i + 1])
            if (d > 0).all() or (d < 0).all():
                hits["R5"].append(i)
        if i >= 14:
            if (np.abs(z[i - 14 : i + 1]) < 1).all():
                hits["R6"].append(i)
    return hits


def ewma(x, center, sigma, lam=0.2, L=3.0):
    """EWMA statistic and time-varying control limits.

    z_i = lam*x_i + (1-lam)*z_{i-1},  z_0 = center
    limits = center +/- L*sigma*sqrt(lam/(2-lam)*(1-(1-lam)^(2i)))
    Good for detecting small sustained shifts (~0.5-1.5 sigma).
    """
    x = np.asarray(x, float)
    z = np.empty_like(x)
    prev = center
    for i, xi in enumerate(x):
        prev = lam * xi + (1 - lam) * prev
        z[i] = prev
    i = np.arange(1, len(x) + 1)
    w = L * sigma * np.sqrt(lam / (2 - lam) * (1 - (1 - lam) ** (2 * i)))
    return z, center - w, center + w, np.where((z > center + w) | (z < center - w))[0]


def cusum(x, center, sigma, k=0.5, h=5.0):
    """Tabular CUSUM. k, h in sigma units. Returns (C+, C-, alarm indices)."""
    x = (np.asarray(x, float) - center) / sigma
    cp = np.zeros_like(x)
    cm = np.zeros_like(x)
    for i, xi in enumerate(x):
        cp[i] = max(0.0, xi - k + (cp[i - 1] if i else 0.0))
        cm[i] = max(0.0, -xi - k + (cm[i - 1] if i else 0.0))
    return cp, cm, np.where((cp > h) | (cm > h))[0]


# ---------------------------------------------------------------------------
# 3. Gauge R&R — crossed two-way ANOVA (parts x operators/tools x repeats)
# ---------------------------------------------------------------------------


@dataclass
class GRRResult:
    repeatability: float  # sigma
    reproducibility: float  # sigma
    grr: float  # sigma
    part: float  # sigma
    total: float  # sigma
    pct_grr_total: float  # % of total variation (sigma ratio)
    pt_ratio: float | None  # % of tolerance, 6*sigma_grr/(USL-LSL)
    ndc: float  # number of distinct categories


def gauge_rr(y, lsl=None, usl=None, k=6.0):
    """y: array shaped (parts, appraisers, repeats).

    'Appraiser' in metrology is usually a tool, a load/unload cycle, or a day.
    Returns sigma components and the usual acceptance metrics.
    """
    y = np.asarray(y, float)
    p, o, r = y.shape
    gm = y.mean()
    mp = y.mean(axis=(1, 2))
    mo = y.mean(axis=(0, 2))
    mpo = y.mean(axis=2)
    ss_p = o * r * ((mp - gm) ** 2).sum()
    ss_o = p * r * ((mo - gm) ** 2).sum()
    ss_po = r * ((mpo - mp[:, None] - mo[None, :] + gm) ** 2).sum()
    ss_e = ((y - mpo[:, :, None]) ** 2).sum()
    ms_p = ss_p / (p - 1)
    ms_o = ss_o / (o - 1)
    ms_po = ss_po / ((p - 1) * (o - 1))
    ms_e = ss_e / (p * o * (r - 1))
    var_e = ms_e
    var_po = max((ms_po - ms_e) / r, 0.0)
    var_o = max((ms_o - ms_po) / (p * r), 0.0)
    var_p = max((ms_p - ms_po) / (o * r), 0.0)
    var_rep = var_o + var_po
    var_grr = var_e + var_rep
    var_tot = var_grr + var_p
    s = math.sqrt
    pt = None
    if lsl is not None and usl is not None:
        pt = k * s(var_grr) / (usl - lsl) * 100
    return GRRResult(
        repeatability=s(var_e),
        reproducibility=s(var_rep),
        grr=s(var_grr),
        part=s(var_p),
        total=s(var_tot),
        pct_grr_total=s(var_grr) / s(var_tot) * 100,
        pt_ratio=pt,
        ndc=1.41 * s(var_p) / s(var_grr) if var_grr > 0 else float("inf"),
    )


# ---------------------------------------------------------------------------
# 4. Tool matching
# ---------------------------------------------------------------------------


def paired_bias(a, b):
    """Mean and std of paired differences a-b, with 95% CI of the mean bias."""
    from scipy.stats import t

    d = np.asarray(a, float) - np.asarray(b, float)
    n = d.size
    m, s = float(d.mean()), float(d.std(ddof=1))
    half = t.ppf(0.975, n - 1) * s / math.sqrt(n)
    return {"bias": m, "sd_diff": s, "ci95": (m - half, m + half), "n": n}


def deming(x, y, delta=1.0):
    """Deming (errors-in-variables) regression y = b0 + b1*x.

    delta = var(err_y)/var(err_x). delta=1 -> orthogonal regression.
    Use when BOTH tools have measurement noise (ordinary least squares
    biases the slope toward 0 in that case).
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    mx, my = x.mean(), y.mean()
    sxx = ((x - mx) ** 2).mean()
    syy = ((y - my) ** 2).mean()
    sxy = ((x - mx) * (y - my)).mean()
    b1 = (syy - delta * sxx + math.sqrt((syy - delta * sxx) ** 2 + 4 * delta * sxy**2)) / (2 * sxy)
    b0 = my - b1 * mx
    return float(b0), float(b1)


# ---------------------------------------------------------------------------
# 5. Wafer-map helpers
# ---------------------------------------------------------------------------


def polar_sitemap(rings=(0, 8, 16, 24), radius_mm=147.0):
    """Generate a ring-based site map. Default 1+8+16+24 = 49 sites over a
    300 mm wafer with 3 mm edge exclusion (r_max=147 mm). Returns (x, y)."""
    xs, ys = [], []
    n_rings = len(rings) - 1
    for i, n in enumerate(rings):
        if n == 0:
            xs.append(0.0)
            ys.append(0.0)
            continue
        r = radius_mm * i / n_rings
        th = np.linspace(0, 2 * np.pi, n, endpoint=False)
        xs.extend(r * np.cos(th))
        ys.extend(r * np.sin(th))
    return np.array(xs), np.array(ys)


def radial_fit(x, y, t, order=2, radius_mm=150.0):
    """Fit t = a0 + a1*rho^2 + a2*rho^4 ... (rho = r/R). Returns coeffs, residual.

    a1 > 0 -> edge-thick (bowl), a1 < 0 -> center-thick (dome).
    Residual after the radial fit holds azimuthal / local structure.
    """
    rho2 = (np.hypot(x, y) / radius_mm) ** 2
    A = np.vstack([rho2**k for k in range(order + 1)]).T
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    return coef, t - A @ coef


def tilt_fit(x, y, t):
    """Plane fit t = c0 + cx*x + cy*y. Large |c| -> left-right/top-bottom tilt
    (gas inlet side, chuck tilt, wafer off-centre)."""
    A = np.vstack([np.ones_like(x), x, y]).T
    coef, *_ = np.linalg.lstsq(A, t, rcond=None)
    return coef, t - A @ coef


# ---------------------------------------------------------------------------
# 6. Thin-film optics
# ---------------------------------------------------------------------------


def snell_cos(n0, theta0, nj):
    """cos(theta_j) in layer j (complex-safe)."""
    s = n0 * np.sin(theta0) / nj
    return np.sqrt(1 - s**2 + 0j)


def fresnel(ni, nj, ci, cj):
    """Fresnel amplitude coefficients (s, p) at interface i->j."""
    rs = (ni * ci - nj * cj) / (ni * ci + nj * cj)
    rp = (nj * ci - ni * cj) / (nj * ci + ni * cj)
    return rs, rp


def stack_r(wl_nm, n_list, d_list, theta0_deg=0.0):
    """Complex reflection coefficients (rs, rp) of a multilayer.

    n_list : [n_ambient, n_layer1, ..., n_substrate] (complex n+ik allowed;
             each entry scalar or array over wavelength)
    d_list : [d_layer1, ...] in nm (len = len(n_list)-2)
    Uses the recursive (Airy) formula from the substrate upward.
    Convention: n_complex = n + i k, phase exp(+2i*beta).
    """
    wl = np.asarray(wl_nm, float)
    th0 = np.deg2rad(theta0_deg)
    n = [np.broadcast_to(np.asarray(nn, complex), wl.shape) for nn in n_list]
    c = [snell_cos(n[0], th0, nn) for nn in n]
    rs, rp = fresnel(n[-2], n[-1], c[-2], c[-1])
    for j in range(len(n) - 2, 0, -1):
        beta = 2 * np.pi * d_list[j - 1] * n[j] * c[j] / wl
        e = np.exp(2j * beta)
        r01s, r01p = fresnel(n[j - 1], n[j], c[j - 1], c[j])
        rs = (r01s + rs * e) / (1 + r01s * rs * e)
        rp = (r01p + rp * e) / (1 + r01p * rp * e)
    return rs, rp


def reflectance(wl_nm, n_list, d_list, theta0_deg=0.0):
    rs, rp = stack_r(wl_nm, n_list, d_list, theta0_deg)
    return 0.5 * (abs(rs) ** 2 + abs(rp) ** 2)


def psi_delta(wl_nm, n_list, d_list, theta0_deg=70.0):
    """Ellipsometric angles in degrees: rho = rp/rs = tan(Psi) exp(i Delta)."""
    rs, rp = stack_r(wl_nm, n_list, d_list, theta0_deg)
    rho = rp / rs
    return np.degrees(np.arctan(np.abs(rho))), np.degrees(np.angle(rho)) % 360


def cauchy(wl_nm, A, B=0.0, C=0.0):
    """n(lambda) = A + B/lambda^2 + C/lambda^4, lambda in micrometres."""
    l = np.asarray(wl_nm, float) / 1000.0
    return A + B / l**2 + C / l**4


# Rough, illustrative optical constants (NOT production values)
def n_sio2(wl_nm):
    return cauchy(wl_nm, 1.448, 0.00356)  # ~1.457 at 633 nm


def n_si3n4(wl_nm):
    return cauchy(wl_nm, 1.98, 0.0156)  # ~2.02 at 633 nm (LPCVD-like)


def n_si(wl_nm):
    """Very rough crystalline-Si n+ik for 400-1000 nm (smooth approximation of
    tabulated data; good enough for demos, not for recipes)."""
    l = np.asarray(wl_nm, float) / 1000.0
    n = 3.42 + 0.155 / l**2 - 0.0035 / l**4
    k = np.clip(0.0055 * (0.633 / l) ** 6.5, 0, None)
    return n + 1j * k


# ---------------------------------------------------------------------------
# 7. Single-layer thickness fit (grid + local least squares)
# ---------------------------------------------------------------------------


def fit_single_layer(wl_nm, R_meas, n_film, n_sub, d_range=(1, 2000), theta0_deg=0.0):
    """Fit thickness of one transparent film on substrate from reflectance.

    Coarse grid search (avoids fringe-order local minima) + scipy refine.
    Returns d_best, chi2-like SSE, and the 1-sigma from the curvature.
    """
    from scipy.optimize import minimize_scalar

    def sse(d):
        Rm = reflectance(wl_nm, [1.0, n_film, n_sub], [d], theta0_deg)
        return float(((R_meas - Rm) ** 2).sum())

    grid = np.arange(d_range[0], d_range[1], 0.5)
    costs = np.array([sse(d) for d in grid])
    d0 = grid[np.argmin(costs)]
    res = minimize_scalar(sse, bounds=(max(d0 - 2, 0), d0 + 2), method="bounded")
    d = res.x
    h = 1e-3
    curv = (sse(d + h) - 2 * sse(d) + sse(d - h)) / h**2
    n_pts = len(wl_nm)
    s2 = res.fun / max(n_pts - 1, 1)
    sigma_d = math.sqrt(2 * s2 / curv) if curv > 0 else float("nan")
    return d, res.fun, sigma_d


# ---------------------------------------------------------------------------
# 8. Process helpers
# ---------------------------------------------------------------------------


def etch_rate(d_before, d_after, t_s, sd_before=0.0, sd_after=0.0, rho=0.0):
    """Etch rate and its 1-sigma. rho = correlation between pre/post errors
    (same site + same tool -> rho > 0 reduces the uncertainty of the delta)."""
    dd = d_before - d_after
    var = sd_before**2 + sd_after**2 - 2 * rho * sd_before * sd_after
    return dd / t_s, math.sqrt(max(var, 0.0)) / t_s


def cmp_time_feedforward(t_pre, t_target, removal_rate):
    """Polish time needed: (pre - target)/RR."""
    return (t_pre - t_target) / removal_rate


def ald_cycles(d_target, gpc, nucleation_delay_cycles=0):
    return math.ceil(d_target / gpc) + nucleation_delay_cycles


def deal_grove(t_hr, B, B_over_A, tau_hr=0.0):
    """Oxide thickness (um): x^2 + A x = B (t + tau)."""
    A = B / B_over_A
    return (-A + math.sqrt(A**2 + 4 * B * (t_hr + tau_hr))) / 2


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    rng = np.random.default_rng(7)

    print("== 1. Stats / capability ==")
    data = np.array([20.01, 19.98, 20.04, 20.02, 20.07, 19.99])
    print({k: round(v, 4) for k, v in describe(data).items()})
    cap = capability(data, 19.5, 20.5)
    print({k: round(v, 3) for k, v in cap.items()})
    print("Cpk 95% CI (n=6):", tuple(round(v, 2) for v in cpk_ci(cap["Cpk"], 6)))
    print("Uniformity half-range %:", round(uniformity(data), 3))

    print("\n== 2. SPC: 0.8-sigma shift at sample 30 ==")
    x = np.r_[rng.normal(20, 0.05, 30), rng.normal(20.04, 0.05, 30)]
    hits = spc_rules(x, 20, 0.05)
    print({k: v[:3] for k, v in hits.items() if v})
    _, lo, hi, alarms = ewma(x, 20, 0.05)
    print("EWMA first alarm:", alarms[:1])
    _, _, cus = cusum(x, 20, 0.05)
    print("CUSUM first alarm:", cus[:1])

    print("\n== 3. Gauge R&R: 10 wafers x 3 tools x 3 repeats ==")
    parts = rng.normal(20, 0.3, 10)
    tool_bias = np.array([0.0, 0.02, -0.01])
    y = parts[:, None, None] + tool_bias[None, :, None] + rng.normal(0, 0.015, (10, 3, 3))
    g = gauge_rr(y, 19.0, 21.0)
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in g.__dict__.items()})

    print("\n== 4. Tool matching ==")
    true = np.linspace(10, 50, 12)
    A = true + rng.normal(0, 0.05, 12)
    B = 1.02 * true + 0.10 + rng.normal(0, 0.05, 12)
    print("paired bias A-B:", {k: (tuple(round(v, 3) for v in val) if isinstance(val, tuple) else round(val, 3)) for k, val in paired_bias(A, B).items()})
    print("Deming B = b0 + b1*A:", tuple(round(v, 3) for v in deming(A, B)))

    print("\n== 5. Wafer map: dome profile ==")
    xs, ys = polar_sitemap()
    t = 20 - 0.4 * (np.hypot(xs, ys) / 150) ** 2 + rng.normal(0, 0.02, xs.size)
    coef, resid = radial_fit(xs, ys, t)
    print("sites:", xs.size, "radial coef:", np.round(coef, 3), "resid sd:", round(resid.std(ddof=1), 3))

    print("\n== 6/7. Optics: 100 nm SiO2 on Si ==")
    wl = np.linspace(400, 900, 251)
    Rm = reflectance(wl, [1.0, n_sio2(wl), n_si(wl)], [100.0]) + rng.normal(0, 0.002, wl.size)
    d, sse, sd = fit_single_layer(wl, Rm, n_sio2(wl), n_si(wl), (1, 600))
    print(f"fit d = {d:.2f} nm  (1-sigma ~ {sd:.3f} nm), SSE = {sse:.2e}")
    psi, delta = psi_delta(np.array([633.0]), [1.0, n_sio2(633.0), n_si(633.0)], [2.0], 70)
    psi0, delta0 = psi_delta(np.array([633.0]), [1.0, n_sio2(633.0), n_si(633.0)], [0.0], 70)
    print(f"Delta sensitivity near 0-2 nm oxide @70deg/633nm: {(delta0[0]-delta[0])/20:.3f} deg per angstrom")

    print("\n== 8. Process helpers ==")
    er, er_sd = etch_rate(100.0, 62.0, 60.0, 0.3, 0.3, rho=0.8)
    print(f"etch rate {er:.3f} nm/s +/- {er_sd:.4f}")
    print("ALD cycles for 20 nm @ 0.10 nm/cy + 5 delay:", ald_cycles(20, 0.10, 5))
    print("CMP polish time (s):", cmp_time_feedforward(800, 500, 5.0))
    print("Deal-Grove dry O2 1000C 1 h (um):", round(deal_grove(1.0, 0.0117, 0.071, 0.37), 4))
