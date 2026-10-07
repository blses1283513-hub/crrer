"""End-to-end thin-film demo report.

    python -m metro_toolkit.demo                 # full report -> reports/demo/
    python -m metro_toolkit.demo --quick         # smaller studies, ~30 s
    python -m metro_toolkit.demo --write-sample  # also refresh data/sample/*.csv

Sections
  1. Optics: reflectance spectra and the fit landscape (why global search)
  2. Recipe development: sensitivity, t-n correlation, underlayer error transfer
  3. Wafer: per-site spectra -> fitted 49-point map -> uniformity + signature
  4. Fab data: per-chamber SPC on synthetic lots with an injected excursion
  5. MSA: GR&R, static/dynamic repeatability, stability, tool matching
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from . import viz
from .analysis import process_capability, spc_by_group, wafer_summary
from .config import data_dir, load_stack, load_yaml, report_dir, wavelengths
from .datagen import (
    Excursion,
    ThicknessSimConfig,
    grr_study,
    matching_study,
    repeatability_study,
    simulate_thickness,
    stability_series,
)
from .metrology.thinfilm import fit, fit_sites, reflectance, simulate_reflectometry, simulate_site_spectra
from .metrology.thinfilm.fitting import _residual_fn
from .metrology.thinfilm.studies import thickness_n_correlation, thickness_sensitivity, underlayer_error_transfer
from .msa import dynamic_repeatability, fleet_matching, gauge_rr, long_term_stability, static_repeatability
from .wafer import interpolate_map, sampling_plan, uniformity_metrics, zernike_decompose

plt = viz.plt


def _md_table(df: pd.DataFrame, floatfmt: str = "{:.4g}") -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, row in df.iterrows():
        cells = [floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def section_optics(out: Path, md: list[str]):
    wl = wavelengths()
    stack, recipe = load_stack("thermal_oxide_100")
    fig, ax = plt.subplots(figsize=(7.5, 4))
    for i, t in enumerate([20, 100, 300]):
        R = reflectance(stack.copy_with([t]), wl)
        ax.plot(wl, R, color=viz.SERIES[i], label=f"SiO2 {t} nm on Si")
        ax.annotate(f"{t} nm", (wl[-1], R[-1]), xytext=(4, 0), textcoords="offset points",
                    color=viz.INK_2, fontsize=8, va="center")
    ax.plot(wl, reflectance(stack.copy_with([0.0]), wl), color=viz.MUTED, linewidth=1.2, label="bare Si")
    ax.set(xlabel="wavelength (nm)", ylabel="reflectance", title="Normal-incidence reflectance, SiO2 on Si")
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out / "01_reflectance_spectra.png", dpi=150)
    plt.close(fig)

    # Narrow visible band + thick film = many fringes = many local minima.
    wl_vis = np.linspace(450, 750, 121)
    t_true = 742.0
    truth = stack.copy_with([t_true])
    meas = simulate_reflectometry(truth, wl_vis, noise=0.002, rng=1)
    res_fn = _residual_fn(stack, meas, recipe["fit_params"])
    grid = np.linspace(1, 1500, 3000)
    cost = np.array([np.sum(res_fn(np.array([t])) ** 2) for t in grid]) / (wl_vis.size - 1)
    result = fit(stack, meas, recipe["fit_params"])
    local = fit(stack.copy_with([530.0]), meas, recipe["fit_params"], global_search=False)
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.semilogy(grid, cost, color=viz.SERIES[0], linewidth=1.2)
    t_fit, t_loc = result.values["L0.thickness"], local.values["L0.thickness"]
    ax.axvline(t_fit, color=viz.INK_2, linewidth=1)
    ax.annotate(f"global minimum {t_fit:.1f} nm", (t_fit, cost.min()), xytext=(8, 4), textcoords="offset points",
                fontsize=8, color=viz.INK)
    ax.scatter([t_loc], [local.chi2_red], s=40, facecolors="none", edgecolors=viz.STATUS["critical"], linewidths=1.5, zorder=4)
    ax.annotate(f"local fit from 530 nm -> {t_loc:.1f} nm", (t_loc, local.chi2_red), xytext=(-70, -24),
                textcoords="offset points", fontsize=8, color=viz.INK)
    ax.set(xlabel="trial thickness (nm)", ylabel="reduced chi-square (log)",
           title="Fit landscape, 450-750 nm reflectometer: scan globally, then refine")
    fig.tight_layout()
    fig.savefig(out / "02_fit_landscape.png", dpi=150)
    plt.close(fig)

    md += [
        "## 1. Optics and fitting",
        "![reflectance](01_reflectance_spectra.png)",
        "![landscape](02_fit_landscape.png)",
        f"Thick oxide ({t_true:.0f} nm) on a narrow-band (450-750 nm) reflectometer: global fit "
        f"**{t_fit:.2f} ± {result.stderr['L0.thickness']:.2f} nm** (chi2_red {result.chi2_red:.2f}). A local optimiser "
        f"started at 530 nm stops at {t_loc:.1f} nm (chi2_red {local.chi2_red:.0f}). More fringes = more traps; "
        "the toolkit scans the whole range first. A wide UV-NIR band (250-1000 nm) removes most of them.",
        "",
    ]


def section_recipe(out: Path, md: list[str], quick: bool):
    wl = np.linspace(250, 1000, 151)
    stack, _ = load_stack("gate_oxide_thin")
    ts = [1, 2, 3, 5, 10, 20, 50, 100] if not quick else [1, 3, 10, 50, 100]
    refl = thickness_sensitivity(stack, 0, ts, wl, "reflectometry", noise=0.002)
    se = thickness_sensitivity(stack, 0, ts, wl, "se", angles=(65, 70, 75), noise=0.0007)
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.loglog(refl.thickness_nm, refl.est_precision_nm, "o-", color=viz.SERIES[0], label="reflectometry (normal incidence)")
    ax.loglog(se.thickness_nm, se.est_precision_nm, "o-", color=viz.SERIES[1], label="SE, 65/70/75 deg")
    ax.set(xlabel="SiO2 thickness (nm)", ylabel="estimated 1-sigma precision (nm)",
           title="Technique choice: SE keeps sub-angstrom precision on thin films")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "03_sensitivity.png", dpi=150)
    plt.close(fig)

    corr = thickness_n_correlation([2, 5, 10, 50, 200] if not quick else [2, 10, 100], wl)
    stack_hk, recipe_hk = load_stack("highk_on_il")
    transfer = underlayer_error_transfer(stack_hk, recipe_hk, 0, 1, wavelength_nm=wl)

    md += [
        "## 2. Recipe development studies",
        "![sensitivity](03_sensitivity.png)",
        "**Floating n and thickness together** (single Cauchy film, SE). The thinner the film, the less the data "
        "constrains n (A_stderr grows) and the closer |corr(t, n)| gets to 1: fix n for thin films.",
        "",
        _md_table(corr[["thickness_nm", "corr_t_n", "t_stderr_nm", "A_stderr"]]),
        "",
        "**Underlayer error transfer** (HfO2 floated on a fixed 1.0 nm SiO2 IL). "
        f"Transfer coefficient **{transfer.attrs['transfer_coefficient']:.2f} nm/nm**: most of any IL error "
        "lands in the HfO2 result while chi2 stays below 1 (no alarm) and the reported stderr stays tiny. "
        "Fit statistics cannot catch model errors; a separate IL pre-measurement can.",
        "",
        _md_table(transfer),
        "",
    ]


def section_wafer(out: Path, md: list[str]):
    stack, recipe = load_stack("thermal_oxide_100")
    sites = sampling_plan("49")
    r_eff = sites.attrs["r_eff_mm"]
    rho = sites.r_mm.to_numpy() / r_eff
    th = np.deg2rad(sites.theta_deg.to_numpy())
    true_t = 100.0 - 0.9 * rho**2 + 0.25 * rho * np.cos(th) - 0.35 * np.clip(rho - 0.85, 0, None) / 0.15
    t0 = time.time()
    meas = simulate_site_spectra(stack, recipe, true_t, wavelengths(), seed=5)
    fits = fit_sites(stack, recipe["fit_params"], meas)
    elapsed = time.time() - t0
    fitted = fits["L0.thickness"].to_numpy()
    um = uniformity_metrics(fitted)
    zk = zernike_decompose(sites.x_mm, sites.y_mm, fitted, radius_mm=r_eff)
    X, Y, Z = interpolate_map(sites.x_mm, sites.y_mm, fitted, radius_mm=r_eff)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    viz.wafer_map(axes[0], X, Y, Z, (sites.x_mm, sites.y_mm), r_eff,
                  title=f"Fitted thickness, 49 pt   mean {um['mean']:.2f} nm, 1σ {um['nu_1sigma_pct']:.2f}%")
    coef = {k: v for k, v in zk["coefficients"].items() if k != "piston"}
    axes[1].barh(list(coef), list(coef.values()), color=viz.SERIES[0], height=0.55)
    axes[1].axvline(0, color=viz.AXIS, linewidth=1)
    axes[1].invert_yaxis()
    axes[1].set(xlabel="Zernike coefficient (nm)", title="Spatial signature")
    fig.tight_layout()
    fig.savefig(out / "04_wafer_map.png", dpi=150)
    plt.close(fig)

    err = fitted - true_t
    md += [
        "## 3. Wafer: spectra → thickness map",
        "![wafer](04_wafer_map.png)",
        f"49 simulated reflectance spectra fitted in {elapsed:.1f} s (first site global, others seeded). "
        f"Fit error vs truth: mean {err.mean():+.3f} nm, max |err| {np.abs(err).max():.3f} nm; "
        f"{int((~fits.fit_ok).sum())} sites flagged.",
        "",
        _md_table(pd.DataFrame([{k: um[k] for k in ("mean", "std", "range", "nu_1sigma_pct", "range_pct", "half_range_pct")}])),
        "",
        "Signature: negative **bowl** = thinner edge (centre-to-edge temperature or flow), "
        "**tilt_x** = left-right gradient, **edge_roll** = extra roll-off in the outer ring.",
        "",
    ]


def _spc_grid(wafers, value, title, ylabel, path, colors, truth_wafers):
    """2x2 small multiples, one I chart per chamber. Returns {chamber: (hits, injected, other_flags)}."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), sharey=True)
    detected = {}
    for ax, (ch, chart) in zip(axes.ravel(), spc_by_group(wafers, "chamber_id", value).items()):
        sub = wafers[wafers.chamber_id == ch].sort_values("timestamp").reset_index(drop=True)
        x = np.arange(len(sub))
        ax.plot(x, chart.statistic, color=colors[ch], linewidth=1.2, marker="o", markersize=3)
        ax.axhline(chart.cl, color=viz.INK_2, linewidth=1)
        ax.plot(x, chart.ucl, color=viz.STATUS["critical"], linewidth=1, label="3σ limits")
        ax.plot(x, chart.lcl, color=viz.STATUS["critical"], linewidth=1)
        r1 = sorted({i for i, rule, _ in chart.violations if rule in (1, 2)})
        if r1:
            ax.scatter(r1, chart.statistic[r1], s=40, facecolors="none", edgecolors=viz.STATUS["critical"],
                       linewidths=1.5, zorder=4, label="WE rule 1/2 violation")
        inj = [i for i, w in enumerate(sub.wafer_id) if w in truth_wafers]
        if inj:
            ax.axvspan(min(inj) - 0.5, max(inj) + 0.5, color=viz.GRID, zorder=0, label="injected excursion")
        detected[ch] = (len(set(r1) & set(inj)), len(inj), len(set(r1) - set(inj)))
        ax.set_title(f"{ch}  {title}")
        ax.set_xlabel("wafer sequence")
        ax.legend(loc="upper left")
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return detected


def section_fab(out: Path, md: list[str], write_sample: bool):
    lim = load_yaml("limits.yaml")["parameters"]["ox_thickness_nm"]
    cfg = ThicknessSimConfig(target=lim["target"], lsl=lim["lsl"], usl=lim["usl"],
                             excursions=[Excursion("DEP01-B", 30, 4, "shift", 1.0), Excursion("DEP02-A", 44, 3, "bowl", -2.0)])
    df, truth = simulate_thickness(cfg)
    if write_sample:
        dd = data_dir()
        dd.mkdir(parents=True, exist_ok=True)
        df.to_csv(dd / "thickness_sites.csv", index=False)
        truth.to_csv(dd / "thickness_excursions_truth.csv", index=False)
    wafers = wafer_summary(df)
    colors = viz.color_map(wafers.chamber_id)
    truth_wafers = set(truth.wafer_id)

    detected = _spc_grid(wafers, "mean", "wafer-mean I chart", "thickness (nm)", out / "05_spc_by_chamber.png",
                         colors, truth_wafers)
    det_nu = _spc_grid(wafers, "nu_1sigma_pct", "within-wafer 1σ % I chart", "NU 1σ (%)",
                       out / "05b_spc_uniformity.png", colors, truth_wafers)
    detected = {ch: (detected[ch][0] + det_nu[ch][0], detected[ch][1], detected[ch][2] + det_nu[ch][2]) for ch in detected}

    nu = wafers.groupby("chamber_id")["nu_1sigma_pct"].agg(["mean", "max"]).reset_index()
    cap = pd.DataFrame([{"chamber": ch, **{k: v for k, v in process_capability(g["mean"], lim["lsl"], lim["usl"]).items()
                                         if k in ("mean", "Cpk", "Ppk")}} for ch, g in wafers.groupby("chamber_id")])
    det = pd.DataFrame([{"chamber": ch, "excursion wafers flagged": f"{a}/{b}", "other rule 1/2 flags": c}
                        for ch, (a, b, c) in detected.items()])
    md += [
        "## 4. Fab data: SPC by chamber",
        f"Synthetic data: {df.lot_id.nunique()} lots, {len(wafers)} measured wafers, {len(df)} site rows, "
        "2 deposition tools x 2 chambers. Injected: +1.0 nm shift on DEP01-B, -2 nm bowl on DEP02-A.",
        "![spc](05_spc_by_chamber.png)",
        _md_table(det),
        "",
        "The bowl excursion barely moves the wafer **mean**; it shows up on the within-wafer 1σ % chart. "
        "Always chart both (the table counts flags from either chart):",
        "![spc-nu](05b_spc_uniformity.png)",
        "",
        _md_table(nu.rename(columns={"mean": "mean NU 1σ %", "max": "max NU 1σ %"})),
        "",
        _md_table(cap),
        "",
    ]


def section_msa(out: Path, md: list[str]):
    lim = load_yaml("limits.yaml")
    spec = lim["parameters"]["ox_thickness_nm"]
    m = lim["msa"]
    grr = gauge_rr(grr_study(), lsl=spec["lsl"], usl=spec["usl"], k=m["grr_k"],
                   accept_pct=m["grr_accept_pct"], marginal_pct=m["grr_marginal_pct"])
    rep = repeatability_study()
    st = static_repeatability(rep[rep.cycle == 1], lsl=spec["lsl"], usl=spec["usl"])
    dy = dynamic_repeatability(rep, lsl=spec["lsl"], usl=spec["usl"])
    stab = long_term_stability(stability_series(drift_per_day=0.002), lsl=spec["lsl"], usl=spec["usl"])
    mdf = matching_study(offset=0.10)
    match = fleet_matching(mdf, reference="FT01", offset_spec=m["matching_offset_spec"], slope_tol=m["matching_slope_tol"])

    comps = ["repeatability", "reproducibility", "gauge_rr", "part_to_part"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    vals = [grr["pct_study_var"][c] for c in comps]
    axes[0].barh(comps, vals, color=viz.SERIES[0], height=0.55)
    for y, v in enumerate(vals):
        axes[0].annotate(f"{v:.1f}%", (v, y), xytext=(4, 0), textcoords="offset points", va="center", fontsize=8)
    axes[0].axvline(10, color=viz.STATUS["good"], linewidth=1)
    axes[0].axvline(30, color=viz.STATUS["critical"], linewidth=1)
    for xg, lab in ((10, "10% acceptable"), (30, "30% limit")):
        axes[0].annotate(lab, (xg, -0.6), xytext=(3, 0), textcoords="offset points", fontsize=7, color=viz.INK_2)
    axes[0].invert_yaxis()
    axes[0].set(xlabel="% study variation", title=f"Gauge R&R  (P/T {grr['pct_tolerance']['gauge_rr']:.1f}%, ndc {grr['ndc']})")
    wide = mdf.pivot_table(index=["wafer_id", "site"], columns="tool_id", values="value")
    axes[1].scatter(wide["FT01"], wide["FT02"] - wide["FT01"], s=10, color=viz.SERIES[0], alpha=0.7)
    axes[1].axhline(0, color=viz.AXIS, linewidth=1)
    for sgn in (-1, 1):
        axes[1].axhline(sgn * m["matching_offset_spec"], color=viz.STATUS["critical"], linewidth=1)
    axes[1].axhline(match.mean_offset.iloc[0], color=viz.INK_2, linewidth=1.2)
    axes[1].set(xlabel="FT01 thickness (nm)", ylabel="FT02 − FT01 (nm)", title="Tool matching (Bland-Altman view)")
    fig.tight_layout()
    fig.savefig(out / "06_msa.png", dpi=150)
    plt.close(fig)

    prec = pd.DataFrame([
        {"metric": "static repeatability 1σ", "nm": st["sigma"], "P/T %": st["pt_pct"]},
        {"metric": "dynamic repeatability 1σ", "nm": dy["sigma_dynamic"], "P/T %": dy["pt_pct"]},
        {"metric": "  of which load/unload", "nm": dy["sigma_load"], "P/T %": float("nan")},
        {"metric": "long-term 1σ (45 d)", "nm": stab["sigma_total"], "P/T %": stab["pt_pct"]},
        {"metric": "GR&R 1σ", "nm": grr["std"]["gauge_rr"], "P/T %": grr["pct_tolerance"]["gauge_rr"]},
    ])
    md += [
        "## 5. Measurement system analysis",
        "![msa](06_msa.png)",
        _md_table(prec),
        "",
        f"GR&R verdict: **{grr['verdict']}** (interaction pooled: {grr['interaction_pooled']}). "
        f"Stability drift {stab['drift_per_day'] * 1000:.2f} pm/day, p = {stab['drift_p_value']:.2g} "
        f"({'significant: schedule a recalibration check' if stab['significant_drift'] else 'not significant'}).",
        "",
        _md_table(match),
        "",
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None, help="output directory (default: reports/demo)")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--write-sample", action="store_true", help="write synthetic CSVs to data/sample")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else report_dir() / "demo"
    out.mkdir(parents=True, exist_ok=True)
    viz.apply_style()

    md = ["# metro-toolkit thin-film demo report", "",
          "All data is synthetic. Generated by `python -m metro_toolkit.demo`.", ""]
    for name, fn in [("optics", lambda: section_optics(out, md)),
                     ("recipe", lambda: section_recipe(out, md, args.quick)),
                     ("wafer", lambda: section_wafer(out, md)),
                     ("fab", lambda: section_fab(out, md, args.write_sample)),
                     ("msa", lambda: section_msa(out, md))]:
        t = time.time()
        fn()
        print(f"  {name:<7} done in {time.time() - t:5.1f} s")
    (out / "report.md").write_text("\n".join(md), encoding="utf-8")
    print(f"report: {out / 'report.md'}")


if __name__ == "__main__":
    main()
