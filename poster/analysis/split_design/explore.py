"""Exploratory figures for the split-design comparison (issue #20).

Several ways of showing the same metrics.csv, for Eli to choose from before a
poster figure is made. Drawn at poster column width with the poster style, so
text sizes are what would print. Written to <run>/figs/.
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from poster_style import COLUMN_WIDTH_IN, DPI, apply_style  # noqa: E402

# Leakiest first. Colours are the dataviz reference categorical order.
DESIGNS = [
    ("row", "80-20", "Random rows (naive 80/20)"),
    ("period", "-", "New month"),
    ("instrument", "-", "New instrument"),
    ("site", "-", "New site (OOI pixel)"),
    ("spacetime", "1deg_30d", "New 1° cell × 30 d"),
    ("region", "10deg", "New 10° region"),
]
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
DATASETS = [("argo", "all", "Argo only"), ("ooi", "all", "OOI only"), ("both", "all", "Argo + OOI")]


def summarise(m, metric):
    g = m.groupby(["dataset", "eval", "design", "variant", "depth_mid"])[metric]
    return g.agg(["mean", "min", "max"]).reset_index()


def sel(s, ds, ev, design, variant):
    return s[(s.dataset == ds) & (s["eval"] == ev) & (s.design == design) & (s.variant == variant)].sort_values(
        "depth_mid"
    )


def profile_lines(m, metric, out, xlabel, xlim=None):
    s = summarise(m, metric)
    fig, axs = plt.subplots(1, 3, figsize=(COLUMN_WIDTH_IN, 7.5), sharey=True)
    for ax, (ds, ev, title) in zip(axs, DATASETS):
        for (des, var, lab), c in zip(DESIGNS, COLORS):
            d = sel(s, ds, ev, des, var)
            if d.empty:
                continue
            ax.fill_betweenx(d.depth_mid, d["min"], d["max"], color=c, alpha=0.2, lw=0)
            ax.plot(d["mean"], d.depth_mid, color=c, lw=3, marker="o", ms=7, label=lab)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        if xlim:
            ax.set_xlim(*xlim)
        ax.grid(alpha=0.3)
    axs[0].invert_yaxis()
    axs[0].set_ylabel("Depth (m)")
    fig.legend(*axs[2].get_legend_handles_labels(), loc="outside lower center", ncol=2, frameon=False)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def heatmaps(m, out):
    s = summarise(m, "r2")
    fig, axs = plt.subplots(1, 3, figsize=(COLUMN_WIDTH_IN, 7.5), sharey=True)
    for ax, (ds, ev, title) in zip(axs, DATASETS):
        depths = sorted(s.depth_mid.unique())
        grid = np.full((len(depths), len(DESIGNS)), np.nan)
        for j, (des, var, _) in enumerate(DESIGNS):
            d = sel(s, ds, ev, des, var).set_index("depth_mid")["mean"]
            for i, z in enumerate(depths):
                grid[i, j] = d.get(z, np.nan)
        im = ax.imshow(grid, cmap="Blues", vmin=0, vmax=1, aspect="auto")
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                if np.isfinite(grid[i, j]):
                    ax.text(j, i, f"{grid[i, j]:.2f}", ha="center", va="center", fontsize=13,
                            color="white" if grid[i, j] > 0.6 else "black")
        ax.set_xticks(range(len(DESIGNS)), [str(k + 1) for k in range(len(DESIGNS))])
        ax.set_yticks(range(len(depths)), [f"{z - 5:g}–{z + 5:g}" for z in depths], fontsize=14)
        ax.set_title(title)
    axs[0].set_ylabel("Depth bin (m)")
    fig.colorbar(im, ax=axs, shrink=0.8, label="R²")
    fig.supxlabel("  ".join(f"{k + 1} {lab}" for k, (_, _, lab) in enumerate(DESIGNS)), fontsize=13)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def dot_summary(m, out):
    """Kai-style: one number per design, surface and depth-averaged."""
    s = summarise(m, "r2")
    fig, axs = plt.subplots(1, 2, figsize=(COLUMN_WIDTH_IN, 6), sharey=True)
    marks = {"argo": "o", "ooi": "s", "both": "D"}
    for ax, (title, f) in zip(
        axs, [("Surface (0–10 m)", lambda d: d[d.depth_mid == 5]["mean"]), ("Mean over depth bins", lambda d: d["mean"])]
    ):
        for j, (des, var, lab) in enumerate(DESIGNS):
            for k, (ds, ev, dlab) in enumerate(DATASETS):
                d = sel(s, ds, ev, des, var)
                if d.empty:
                    continue
                ax.plot(f(d).mean(), j + (k - 1) * 0.22, marks[ds], color=COLORS[j], ms=13,
                        mec="white", mew=1.5, label=dlab if j == 0 else None)
        ax.set_title(title)
        ax.set_xlabel("R²")
        ax.grid(axis="x", alpha=0.3)
    axs[0].set_yticks(range(len(DESIGNS)), [lab for _, _, lab in DESIGNS])
    axs[0].invert_yaxis()
    leg = [plt.Line2D([], [], marker=marks[ds], ls="", color="0.3", ms=12, label=dl) for ds, _, dl in DATASETS]
    fig.legend(handles=leg, loc="outside lower center", ncol=3, frameon=False)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def inflation(m, out):
    """How much the naive split overstates R², relative to each design."""
    s = summarise(m, "r2")
    fig, axs = plt.subplots(1, 3, figsize=(COLUMN_WIDTH_IN, 7.5), sharey=True, sharex=True)
    for ax, (ds, ev, title) in zip(axs, DATASETS):
        base = sel(s, ds, ev, "row", "80-20").set_index("depth_mid")["mean"]
        for (des, var, lab), c in list(zip(DESIGNS, COLORS))[1:]:
            d = sel(s, ds, ev, des, var).set_index("depth_mid")["mean"]
            if d.empty:
                continue
            gap = (base - d).dropna()
            ax.plot(gap.values, gap.index, color=c, lw=3, marker="o", ms=7, label=lab)
        ax.axvline(0, color="0.4", lw=1)
        ax.set_title(title)
        ax.set_xlabel("R² naive − R² design")
        ax.grid(alpha=0.3)
    axs[0].invert_yaxis()
    axs[0].set_ylabel("Depth (m)")
    fig.legend(*axs[2].get_legend_handles_labels(), loc="outside lower center", ncol=2, frameon=False)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def block_sweep(m, out):
    """Space-time block length: where does the leak stop?"""
    s = summarise(m, "r2")
    st = s[s.design == "spacetime"].copy()
    if st.empty:
        return
    st["days"] = st.variant.str.split("_").str[1].str.rstrip("d").astype(float)
    depths = [z for z in [5, 45, 105, 165] if z in set(st.depth_mid)]
    shades = ["#9ec5f4", "#5598e7", "#256abf", "#0d366b"]
    fig, axs = plt.subplots(1, 3, figsize=(COLUMN_WIDTH_IN, 6.5), sharey=True)
    for ax, (ds, ev, title) in zip(axs, DATASETS):
        for z, c in zip(depths, shades):
            d = st[(st.dataset == ds) & (st["eval"] == ev) & (st.depth_mid == z)].sort_values("days")
            ax.plot(d.days, d["mean"], color=c, lw=3, marker="o", ms=8, label=f"{z - 5}–{z + 5} m")
            r = sel(s, ds, ev, "row", "80-20")
            r = r[r.depth_mid == z]["mean"]
            if len(r):
                ax.plot([d.days.min() * 0.7], r, marker="<", color=c, ms=12, ls="")
        ax.set_xscale("log")
        ax.set_xticks([1, 10, 30, 90], ["1", "10", "30", "90"])
        ax.set_xlabel("Time block (days)")
        ax.set_title(title)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("R² (1° cell × block)")
    fig.legend(*axs[0].get_legend_handles_labels(), loc="outside lower center", ncol=4, frameon=False,
               title="◀ = naive random-row R²")
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def platform_view(m, out):
    """Does pooling Argo and OOI help or hurt each platform?"""
    s = summarise(m, "r2")
    picks = [("row", "80-20", "--"), ("spacetime", "1deg_30d", "-")]
    fig, axs = plt.subplots(1, 2, figsize=(COLUMN_WIDTH_IN, 7.5), sharey=True)
    for ax, plat in zip(axs, ["argo", "ooi"]):
        for (des, var, ls) in picks:
            lab = dict((d, l) for d, v, l in DESIGNS)[des]
            for (ds, ev, c, who) in [(plat, "all", "#2a78d6", f"trained on {plat.upper() if plat == 'ooi' else 'Argo'} only"),
                                     ("both", plat, "#eb6834", "trained on Argo + OOI")]:
                d = sel(s, ds, ev, des, var)
                ax.plot(d["mean"], d.depth_mid, color=c, ls=ls, lw=3, marker="o", ms=6, label=f"{who}, {lab}")
        ax.set_title(f"Scored on {'Argo' if plat == 'argo' else 'OOI'}")
        ax.set_xlabel("R²")
        ax.grid(alpha=0.3)
    axs[0].invert_yaxis()
    axs[0].set_ylabel("Depth (m)")
    fig.legend(*axs[0].get_legend_handles_labels(), loc="outside lower center", ncol=1, frameon=False, fontsize=18)
    fig.savefig(out, dpi=DPI)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    args = ap.parse_args()
    apply_style()
    m = pd.read_csv(args.run / "metrics.csv")
    figs = args.run / "figs"
    figs.mkdir(exist_ok=True)
    profile_lines(m, "r2", figs / "1_r2_by_depth.png", "R²")
    profile_lines(m, "rmse", figs / "1b_rmse_by_depth.png", "RMSE (log10 CHLA)")
    heatmaps(m, figs / "2_r2_heatmap.png")
    dot_summary(m, figs / "3_dot_summary.png")
    inflation(m, figs / "4_inflation.png")
    block_sweep(m, figs / "5_block_sweep.png")
    platform_view(m, figs / "6_platform_view.png")
    print("figures ->", figs)


if __name__ == "__main__":
    main()
