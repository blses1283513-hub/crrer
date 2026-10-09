"""Shared chart styling (matplotlib for reports, plotly for the dashboard).

Palette: the validated default from the dataviz method (categorical slots in
fixed order, single-hue blue sequential ramp, blue<->red diverging with a gray
midpoint, reserved status colours). Colour follows the entity: a chamber keeps
its slot no matter which subset is plotted.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
DIVERGING = ["#1c5cab", "#6da7ec", "#f0efec", "#ec8a8a", "#b22b2b"]

CMAP_SEQ = LinearSegmentedColormap.from_list("metro_seq", SEQ_BLUE)
CMAP_DIV = LinearSegmentedColormap.from_list("metro_div", DIVERGING)


def color_map(entities) -> dict:
    """Stable entity -> colour assignment (sorted names, fixed slot order, max 8)."""
    names = sorted(set(entities))
    if len(names) > len(SERIES):
        raise ValueError("more than 8 series: fold into 'Other' or use small multiples")
    return {n: SERIES[i] for i, n in enumerate(names)}


def apply_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_2,
        "axes.titlecolor": INK,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.labelsize": 9,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "lines.linewidth": 2.0,
        "lines.markersize": 5,
        "legend.frameon": False,
        "legend.fontsize": 8,
        "font.family": "sans-serif",
        "font.size": 9,
        "text.color": INK,
    })


def wafer_map(ax, X, Y, Z, sites=None, radius_mm=150.0, title="", unit="nm", diverging_center=None):
    """Contour wafer map. Sequential blue for magnitude; diverging when a centre (target) is given."""
    if diverging_center is None:
        cmap, vmin, vmax = CMAP_SEQ, np.nanmin(Z), np.nanmax(Z)
    else:
        span = np.nanmax(np.abs(Z - diverging_center))
        cmap, vmin, vmax = CMAP_DIV, diverging_center - span, diverging_center + span
    cf = ax.contourf(X, Y, Z, levels=14, cmap=cmap, vmin=vmin, vmax=vmax)
    ax.add_patch(plt.Circle((0, 0), radius_mm, fill=False, color=AXIS, linewidth=1.0))
    if sites is not None:
        ax.scatter(sites[0], sites[1], s=9, c=SURFACE, edgecolors=INK_2, linewidths=0.6, zorder=3)
    ax.set_aspect("equal")
    ax.set_xlim(-radius_mm * 1.05, radius_mm * 1.05)
    ax.set_ylim(-radius_mm * 1.05, radius_mm * 1.05)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("y (mm)")
    ax.grid(False)
    ax.set_title(title)
    cb = plt.colorbar(cf, ax=ax, shrink=0.85)
    cb.set_label(unit, color=INK_2)
    cb.outline.set_visible(False)
    return cf


# plotly ------------------------------------------------------------------- #

PLOTLY_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK, size=12),
    # axis names are the most important text on a chart: full ink, never the muted grey of the tick labels
    xaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED),
               title=dict(font=dict(color=INK, size=13))),
    yaxis=dict(gridcolor=GRID, linecolor=AXIS, zeroline=False, tickfont=dict(color=MUTED),
               title=dict(font=dict(color=INK, size=13))),
    margin=dict(l=50, r=20, t=80, b=45),
    hovermode="closest",
    legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
)
PLOTLY_SEQ = [[i / (len(SEQ_BLUE) - 1), c] for i, c in enumerate(SEQ_BLUE)]
PLOTLY_DIV = [[i / (len(DIVERGING) - 1), c] for i, c in enumerate(DIVERGING)]
