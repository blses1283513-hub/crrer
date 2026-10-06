"""
example_wafer_analysis.py — end-to-end worked example on synthetic data.

Scenario: two deposition chambers (A, B) for a 20 nm film, 30 lots, one wafer
per chamber per lot, 49-site polar map. Chamber B develops a centre-thick
(dome) signature from lot 20 after a PM.

Outputs (written next to this script, in ./out/):
  sites.csv            long-format site data (the recommended schema)
  wafer_summary.csv    one row per wafer: mean, sigma, uniformity, radial coeff
  wafer_map.png        site map of the last chamber-B wafer
  control_chart.png    I-chart of chamber-B wafer means + radial coefficient
  radial_profile.png   radial profile, chamber A vs B, last lot

Run:  python example_wafer_analysis.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from metro_tools import capability, ewma, polar_sitemap, radial_fit, spc_rules, uniformity

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)

# Palette (dataviz reference instance): categorical slots 1-2, sequential blue ramp
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SEQ = LinearSegmentedColormap.from_list(
    "seq_blue", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "text.color": INK,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
    }
)

# ---------------------------------------------------------------- data
rng = np.random.default_rng(42)
x, y = polar_sitemap()
r = np.hypot(x, y) / 150.0
rows = []
for lot in range(1, 31):
    for ch in ("A", "B"):
        lot_offset = rng.normal(0, 0.03)
        dome = -0.35 if (ch == "B" and lot >= 20) else 0.0
        t = 20.0 + lot_offset + dome * r**2 + 0.08 * r**4 + rng.normal(0, 0.02, x.size)
        for i in range(x.size):
            rows.append(
                dict(lot_id=f"L{lot:02d}", wafer_id=f"L{lot:02d}-{ch}", chamber_id=ch,
                     metro_tool_id="M1", site_id=i + 1, x_mm=round(x[i], 2), y_mm=round(y[i], 2),
                     thickness=round(t[i], 4))
            )
sites = pd.DataFrame(rows)
sites["r_mm"] = np.hypot(sites.x_mm, sites.y_mm)
sites.to_csv(OUT / "sites.csv", index=False)

# ---------------------------------------------------------------- per-wafer summary
def summarize(g):
    coef, _ = radial_fit(g.x_mm.values, g.y_mm.values, g.thickness.values)
    return pd.Series(
        dict(mean=g.thickness.mean(), sigma=g.thickness.std(ddof=1),
             unif_half_range=uniformity(g.thickness, "range_half"), radial_a1=coef[1])
    )

summary = sites.groupby(["lot_id", "chamber_id"]).apply(summarize, include_groups=False).reset_index()
summary.to_csv(OUT / "wafer_summary.csv", index=False)

b = summary[summary.chamber_id == "B"].reset_index(drop=True)
base = b.iloc[:15]
mu0, s0 = base["mean"].mean(), base["mean"].std(ddof=1)
a0, sa = base.radial_a1.mean(), base.radial_a1.std(ddof=1)

print("Chamber B baseline mean %.3f nm, sigma %.3f nm" % (mu0, s0))
print("Run-rule hits on wafer mean:", {k: v for k, v in spc_rules(b["mean"], mu0, s0).items() if v})
print("Run-rule hits on radial a1 :", {k: v[:3] for k, v in spc_rules(b.radial_a1, a0, sa).items() if v})
print("EWMA alarms on mean        :", ewma(b["mean"], mu0, s0)[3])
cap = capability(b["mean"], 19.5, 20.5)
print("Cpk chamber B wafer means (all lots): %.2f" % cap["Cpk"])
print(summary.groupby("chamber_id")[["mean", "sigma", "unif_half_range"]].mean().round(3))

# ---------------------------------------------------------------- wafer map
last = sites[sites.wafer_id == "L30-B"]
fig, ax = plt.subplots(figsize=(5.2, 4.6))
ax.add_patch(plt.Circle((0, 0), 150, fill=False, color=INK2, lw=1))
sc = ax.scatter(last.x_mm, last.y_mm, c=last.thickness, cmap=SEQ, s=260, edgecolors=SURFACE, linewidths=2)
for _, rw in last.iterrows():
    v = rw.thickness
    ax.text(rw.x_mm, rw.y_mm, f"{v:.2f}", ha="center", va="center", fontsize=6,
            color="white" if v > last.thickness.quantile(0.7) else INK)
ax.set_aspect("equal"); ax.set_xlim(-160, 160); ax.set_ylim(-160, 160)
ax.grid(False); ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_visible(False)
cb = fig.colorbar(sc, ax=ax, shrink=0.8); cb.set_label("Thickness (nm)")
ax.set_title("Wafer L30-B — centre-thick dome after PM", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "wafer_map.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- control chart (two panels, one axis each)
lots = np.arange(1, len(b) + 1)
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5.6), sharex=True)
for ax, series, c, s, label in ((ax1, b["mean"], mu0, s0, "Wafer mean (nm)"),
                                (ax2, b.radial_a1, a0, sa, "Radial coefficient a1 (nm)")):
    ax.plot(lots, series, color=BLUE, lw=2, marker="o", ms=4)
    for k, ls in ((0, "-"), (3, "--"), (-3, "--")):
        ax.axhline(c + k * s, color=INK2, lw=1, ls=ls)
    ax.text(lots[-1] + 0.4, c + 3 * s, "UCL", va="bottom", fontsize=8, color=INK2)
    ax.text(lots[-1] + 0.4, c - 3 * s, "LCL", va="top", fontsize=8, color=INK2)
    out = np.where(np.abs((series - c) / s) > 3)[0]
    if out.size:
        ax.scatter(lots[out], series.iloc[out], s=70, facecolors="none", edgecolors=ORANGE, linewidths=2, zorder=3)
    ax.axvline(19.5, color=GRID, lw=6, zorder=0)
    ax.set_ylabel(label)
ax1.set_title("Chamber B after PM (lot 20): mean drops AND radial shape alarms — shape says why", loc="left", fontsize=11)
ax2.set_xlabel("Lot")
fig.tight_layout(); fig.savefig(OUT / "control_chart.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- radial profile A vs B
fig, ax = plt.subplots(figsize=(7, 4))
for ch, col in (("A", BLUE), ("B", ORANGE)):
    w = sites[sites.wafer_id == f"L30-{ch}"]
    prof = w.groupby(w.r_mm.round(0)).thickness.mean()
    ax.plot(prof.index, prof.values, color=col, lw=2, marker="o", ms=5, label=f"Chamber {ch}")
    ax.text(prof.index[-1] + 3, prof.values[-1], f"Chamber {ch}", va="center", fontsize=9, color=INK)
ax.set_xlabel("Radius (mm)"); ax.set_ylabel("Ring-average thickness (nm)")
ax.set_xlim(-5, 175)
ax.legend(frameon=False, loc="lower left")
ax.set_title("Radial profile, lot 30", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "radial_profile.png", dpi=150); plt.close(fig)

print("Wrote:", sorted(p.name for p in OUT.iterdir()))
